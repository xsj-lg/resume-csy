from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .llm_service import call_llm_chat_stream, parse_llm_json_response

MAX_JOB_TEMPLATE_BYTES = 8 * 1024 * 1024
ALLOWED_SCORE_TEMPLATE_EXTENSIONS = {".csv", ".xls", ".xlsx"}


def sanitize_score_template_filename(filename: str) -> str:
    normalized = Path((filename or "").replace("\\", "/")).name.strip()
    normalized = normalized.replace("\x00", "")
    if not normalized:
        raise ValueError("评分表文件名不能为空")
    suffix = Path(normalized).suffix.lower()
    if suffix not in ALLOWED_SCORE_TEMPLATE_EXTENSIONS:
        raise ValueError("评分表仅支持 .xlsx / .xls / .csv")
    return normalized


def _cell_ref_to_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    if not letters:
        return -1
    index = 0
    for ch in letters:
        index = index * 26 + (ord(ch) - ord("A") + 1)
    return index - 1


def _decode_bytes_with_fallback(content: bytes) -> str:
    for encoding in ("utf-8-sig", "gbk", "utf-16", "latin1"):
        try:
            text = content.decode(encoding)
            if text:
                return text
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _parse_delimited_rows(content: bytes, max_rows: int = 240, max_cols: int = 20) -> list[list[str]]:
    text = _decode_bytes_with_fallback(content)
    sample = text[:2048]
    delimiter = ","
    if "\t" in sample and sample.count("\t") >= sample.count(","):
        delimiter = "\t"
    elif ";" in sample and sample.count(";") > sample.count(","):
        delimiter = ";"
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows: list[list[str]] = []
    for row in reader:
        cleaned = [str(cell or "").strip() for cell in row[:max_cols]]
        if any(cleaned):
            rows.append(cleaned)
        if len(rows) >= max_rows:
            break
    return rows


def _parse_xlsx_rows(content: bytes, max_rows: int = 240, max_cols: int = 20) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
            for si in root.findall(f".//{namespace}si"):
                chunks: list[str] = []
                for node in si.findall(f".//{namespace}t"):
                    chunks.append(node.text or "")
                shared_strings.append("".join(chunks).strip())

        workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
        namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        rel_namespace = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
        first_sheet = workbook_root.find(f".//{namespace}sheet")
        if first_sheet is None:
            return []
        rel_id = first_sheet.attrib.get(f"{rel_namespace}id")
        if not rel_id:
            return []

        rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rels_namespace = "{http://schemas.openxmlformats.org/package/2006/relationships}"
        target = ""
        for rel in rels_root.findall(f".//{rels_namespace}Relationship"):
            if rel.attrib.get("Id") == rel_id:
                target = rel.attrib.get("Target", "")
                break
        if not target:
            return []
        if target.startswith("/"):
            sheet_path = target.lstrip("/")
        elif target.startswith("xl/"):
            sheet_path = target
        else:
            sheet_path = f"xl/{target}"
        if sheet_path not in archive.namelist():
            return []

        sheet_root = ET.fromstring(archive.read(sheet_path))
        rows: list[list[str]] = []
        for row_node in sheet_root.findall(f".//{namespace}row"):
            row_values = [""] * max_cols
            for cell in row_node.findall(f"{namespace}c"):
                ref = cell.attrib.get("r", "")
                col_index = _cell_ref_to_index(ref)
                if col_index < 0 or col_index >= max_cols:
                    continue
                value_node = cell.find(f"{namespace}v")
                text = (value_node.text or "").strip() if value_node is not None else ""
                if cell.attrib.get("t") == "s":
                    if text.isdigit():
                        shared_index = int(text)
                        if 0 <= shared_index < len(shared_strings):
                            text = shared_strings[shared_index]
                        else:
                            text = ""
                row_values[col_index] = text
            if any(cell for cell in row_values):
                rows.append(row_values)
            if len(rows) >= max_rows:
                break
        return rows


def _header_index_by_rules(headers: list[str], rules: list[str]) -> int:
    normalized_rules = [re.sub(r"\s+", "", str(rule or "")).casefold() for rule in rules if str(rule or "").strip()]
    for idx, header in enumerate(headers):
        normalized = re.sub(r"\s+", "", str(header or "")).casefold()
        if any(rule in normalized for rule in normalized_rules):
            return idx
    return -1


def _detect_score_header_row(rows: list[list[str]], max_scan_rows: int = 10) -> int:
    expected_rules = [
        "评分维度",
        "维度",
        "评估点",
        "评分项",
        "评分标准",
        "标准",
        "分值",
        "得分",
        "score",
        "criterion",
    ]
    best_idx = 0
    best_hit = -1
    for row_index, row in enumerate(rows[:max_scan_rows]):
        normalized = [re.sub(r"\s+", "", str(cell or "")).casefold() for cell in row]
        hit = 0
        for rule in expected_rules:
            if any(rule in cell for cell in normalized):
                hit += 1
        if hit > best_hit:
            best_hit = hit
            best_idx = row_index
    return best_idx


def _row_cell(row: list[str], index: int) -> str:
    if 0 <= index < len(row):
        return str(row[index] or "").strip()
    return ""


def _strip_dimension_total(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"[\(（]\s*\d+(?:\.\d+)?\s*分\s*[\)）]\s*$", "", text)
    return text.strip()


def _extract_dimensions_from_sectioned_rows(headers: list[str], rows: list[list[str]]) -> list[dict[str, str]]:
    normalized_headers = [str(header or "").strip() for header in headers]
    dimension_idx = _header_index_by_rules(normalized_headers, ["评分维度", "维度", "dimension"])
    point_idx = _header_index_by_rules(normalized_headers, ["评估点", "评分项", "指标", "能力点", "项目", "point", "item"])
    criterion_idx = _header_index_by_rules(normalized_headers, ["评分标准", "标准", "要求", "criterion", "说明", "描述"])
    score_idx = _header_index_by_rules(normalized_headers, ["分值", "分数", "score"])
    if dimension_idx < 0 or criterion_idx < 0 or score_idx < 0 or point_idx >= 0:
        return []

    section_rows = 0
    item_rows = 0
    continuation_rows = 0
    for row in rows[:120]:
        dimension_value = _row_cell(row, dimension_idx)
        criterion = _row_cell(row, criterion_idx)
        score = _row_cell(row, score_idx)
        if dimension_value and not criterion and not score:
            section_rows += 1
        elif dimension_value and (criterion or score):
            item_rows += 1
        elif not dimension_value and (criterion or score):
            continuation_rows += 1
    if section_rows < 1 or item_rows < 1 or (item_rows + continuation_rows) < 2:
        return []

    out: list[dict[str, str]] = []
    current_dimension = ""
    current_point = ""
    for row in rows:
        dimension_value = _row_cell(row, dimension_idx)
        criterion = _row_cell(row, criterion_idx)
        score = _row_cell(row, score_idx)
        if dimension_value and not criterion and not score:
            current_dimension = _strip_dimension_total(dimension_value)
            current_point = ""
            continue
        if dimension_value:
            current_point = dimension_value
        if not criterion and not score:
            continue
        if not current_dimension or not current_point:
            continue
        out.append(
            {
                "dimension": current_dimension,
                "point": current_point,
                "criterion": criterion,
                "indicator": criterion or current_point,
                "score": score,
            }
        )
    return out


def _extract_dimensions_from_flat_rows(headers: list[str], rows: list[list[str]]) -> list[dict[str, str]]:
    normalized_headers = [str(header or "").strip() for header in headers]
    dimension_idx = _header_index_by_rules(normalized_headers, ["评分维度", "维度", "一级", "dimension"])
    point_idx = _header_index_by_rules(normalized_headers, ["评估点", "评分项", "指标", "能力点", "项目", "point", "item"])
    criterion_idx = _header_index_by_rules(normalized_headers, ["评分标准", "标准", "要求", "criterion"])
    score_idx = _header_index_by_rules(normalized_headers, ["分值", "分数", "score"])
    if criterion_idx < 0:
        criterion_idx = _header_index_by_rules(normalized_headers, ["说明", "描述"])
    out: list[dict[str, str]] = []
    current_dimension = ""
    current_point = ""
    for row in rows:
        raw_dimension = _row_cell(row, dimension_idx)
        raw_point = _row_cell(row, point_idx)
        criterion = _row_cell(row, criterion_idx)
        score = _row_cell(row, score_idx)
        if raw_dimension:
            current_dimension = raw_dimension
        if raw_point:
            current_point = raw_point
        elif raw_dimension and point_idx < 0:
            current_point = ""
        dimension = raw_dimension or current_dimension
        point = raw_point or current_point
        if not dimension and not point and not criterion and not score:
            continue
        out.append(
            {
                "dimension": dimension,
                "point": point,
                "criterion": criterion,
                "indicator": criterion,
                "score": score,
            }
        )
    return out


def _extract_dimensions_from_preview(headers: list[str], rows: list[list[str]]) -> list[dict[str, str]]:
    return _extract_dimensions_from_sectioned_rows(headers, rows) or _extract_dimensions_from_flat_rows(headers, rows)


def _build_score_table_preview(rows: list[list[str]], note: str = "") -> dict[str, Any]:
    if not rows:
        return {
            "headers": [],
            "rows": [],
            "dimensions": [],
            "note": note or "评分表为空，未识别到有效内容。",
            "source": "fallback",
        }

    header_index = _detect_score_header_row(rows)
    headers = [str(cell or "").strip() for cell in rows[header_index][:12]]
    data_rows_source = rows[header_index + 1 :]
    data_rows = [
        [str(cell or "").strip() for cell in row[:12]]
        for row in data_rows_source
        if any(str(cell or "").strip() for cell in row)
    ]
    sample_rows = data_rows[:6]
    dimensions = _extract_dimensions_from_preview(headers, data_rows[:120])
    sectioned_dimensions = _extract_dimensions_from_sectioned_rows(headers, data_rows[:120])

    if not note:
        note = "已按规则解析评分表预览。"
        if sectioned_dimensions:
            note = "已按分段评分表规则解析预览。"
    if not dimensions:
        note = "未识别到明确评分结构，请检查评分表表头或内容格式。"
    return {
        "headers": headers,
        "rows": sample_rows,
        "dimensions": dimensions,
        "note": note,
        "source": "rules",
    }


def _extract_score_table_rows(content: bytes, filename: str) -> list[list[str]]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        return _parse_delimited_rows(content)
    if suffix == ".xlsx":
        return _parse_xlsx_rows(content)
    return _parse_delimited_rows(content)


def _rows_to_prompt_text(rows: list[list[str]], max_lines: int = 40) -> str:
    if not rows:
        return ""
    lines: list[str] = []
    for row in rows[:max_lines]:
        lines.append("\t".join(str(cell or "").strip() for cell in row[:20]))
    return "\n".join(lines).strip()


def normalize_score_table_preview_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    headers_raw = raw_payload.get("headers")
    rows_raw = raw_payload.get("rows")
    dimensions_raw = raw_payload.get("dimensions")
    note = str(raw_payload.get("note", "")).strip()

    headers = [str(item or "").strip() for item in headers_raw[:12]] if isinstance(headers_raw, list) else []
    rows: list[list[str]] = []
    if isinstance(rows_raw, list):
        for row in rows_raw[:6]:
            if not isinstance(row, list):
                continue
            rows.append([str(cell or "").strip() for cell in row[:12]])

    dimensions: list[dict[str, str]] = []
    if isinstance(dimensions_raw, list):
        for item in dimensions_raw[:500]:
            if not isinstance(item, dict):
                continue
            dimension = str(item.get("dimension", "")).strip()
            point = str(item.get("point", "")).strip()
            criterion = str(item.get("criterion", "")).strip()
            indicator = str(item.get("indicator", "")).strip()
            score = str(item.get("score", "")).strip()
            if not dimension:
                continue
            if not point and "：" in criterion:
                point = criterion.split("：", 1)[0].strip()
            if not indicator:
                indicator = criterion
            dimensions.append(
                {
                    "dimension": dimension,
                    "point": point,
                    "criterion": criterion,
                    "indicator": indicator,
                    "score": score,
                }
            )

    if not dimensions and headers and rows:
        dimensions = _extract_dimensions_from_preview(headers, rows)

    source = str(raw_payload.get("source", "")).strip().lower()
    if source not in {"rules", "fallback", "llm"}:
        source = "rules"
    if not note:
        note = "已解析评分表预览。"
    return {
        "headers": headers,
        "rows": rows,
        "dimensions": dimensions,
        "note": note,
        "source": source,
    }


def _call_llm_score_table_preview(
    *,
    runtime: dict[str, Any],
    filename: str,
    table_text: str,
) -> tuple[dict[str, Any], str]:
    if not bool(runtime.get("enabled", False)):
        return {}, "LLM 未启用"
    model = str(runtime.get("model", "")).strip()
    if not model:
        return {}, "LLM 配置不完整"
    if not table_text:
        return {}, "评分表内容为空"

    system_prompt = (
        "你是招聘评分表结构化解析器。"
        "输出必须是 JSON 对象，字段为 headers(rows 的表头数组)、rows、"
        "dimensions(数组，元素含 dimension/criterion/score 字段)、note(字符串)。"
        "禁止输出解释性文本。"
    )
    user_prompt = (
        f"文件名: {filename}\n"
        "请解析以下评分表文本，提取用于前端预览的数据结构。\n"
        "如果字段缺失，返回空字符串或空数组。\n"
        "评分表文本如下:\n"
        f"{table_text[:12000]}"
    )
    content, reasoning_content, stream_error = call_llm_chat_stream(
        runtime=runtime,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=min(int(runtime.get("max_tokens", 2048) or 2048), 1200),
        enable_thinking=True,
    )
    if stream_error:
        return {}, stream_error

    parsed = parse_llm_json_response(str(content or ""))
    if not parsed and reasoning_content:
        parsed = parse_llm_json_response(reasoning_content)
    if not parsed:
        return {}, "LLM 返回内容不是有效 JSON"
    return normalize_score_table_preview_payload(parsed), ""


def parse_score_table_preview(content: bytes, filename: str) -> dict[str, Any]:
    safe_filename = sanitize_score_template_filename(filename)
    size = len(content or b"")
    if size <= 0:
        raise ValueError("评分表文件不能为空")
    if size > MAX_JOB_TEMPLATE_BYTES:
        raise ValueError("评分表文件过大（最大 8MB）")

    rows = _extract_score_table_rows(content, safe_filename)
    return _build_score_table_preview(rows)


def score_to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return 0.0
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return 0.0
    try:
        return float(match.group(0))
    except ValueError:
        return 0.0


def normalize_score_item(raw_item: dict[str, Any]) -> dict[str, Any]:
    dimension = str(raw_item.get("dimension", "") or raw_item.get("dimension_name", "")).strip()
    criterion = str(raw_item.get("criterion", "") or raw_item.get("selected_standard", "")).strip()
    point = str(raw_item.get("point", "") or raw_item.get("item_name", "")).strip()
    indicator = str(raw_item.get("indicator", "") or criterion).strip()
    if not point and "：" in criterion:
        point = criterion.split("：", 1)[0].strip()
    if not point and ":" in criterion:
        point = criterion.split(":", 1)[0].strip()
    if not indicator:
        indicator = criterion
    score_text = str(raw_item.get("score", "") or raw_item.get("item_score", "")).strip()
    return {
        "dimension": dimension,
        "point": point,
        "criterion": criterion,
        "indicator": indicator,
        "score": score_text,
        "score_value": max(score_to_float(score_text), 0.0),
    }


def calculate_score_items_max_score(score_items: list[dict[str, Any]]) -> float:
    point_max_scores: dict[tuple[str, str], float] = {}
    for item in score_items:
        dimension = str(item.get("dimension", "")).strip() or "未命名维度"
        point = str(item.get("point", "")).strip() or str(item.get("criterion", "")).strip() or "未命名评估点"
        point_key = (dimension, point)
        point_max_scores[point_key] = max(
            point_max_scores.get(point_key, 0.0),
            max(float(item.get("score_value", 0.0) or 0.0), 0.0),
        )
    return sum(point_max_scores.values())


def _normalize_scoring_text_key(value: Any) -> str:
    text = str(value or "").strip().casefold()
    if not text:
        return ""
    return re.sub(r"[\s\-_，。；、,:：/\\|（）()\[\]{}【】<>\"'`]+", "", text)


def dedupe_score_items_for_prompt(score_items_raw: Any) -> list[dict[str, Any]]:
    if not isinstance(score_items_raw, list):
        return []
    deduped: list[dict[str, Any]] = []
    seen_aliases: dict[tuple[str, str, float], set[str]] = {}
    for raw_item in score_items_raw:
        if not isinstance(raw_item, dict):
            continue
        item = normalize_score_item(raw_item)
        dimension = str(item.get("dimension", "")).strip() or "未命名维度"
        point = str(item.get("point", "")).strip() or str(item.get("criterion", "")).strip() or "未命名评估点"
        criterion = str(item.get("criterion", "")).strip()
        indicator = str(item.get("indicator", "")).strip() or criterion
        score_value = round(max(score_to_float(item.get("score_value", item.get("score", 0))), 0.0), 2)
        score_text = str(item.get("score", "")).strip() or str(score_value)
        alias_keys = {
            _normalize_scoring_text_key(criterion),
            _normalize_scoring_text_key(indicator),
        }
        alias_keys.discard("")
        point_key = (dimension, point, score_value)
        point_seen = seen_aliases.setdefault(point_key, set())
        if alias_keys and point_seen.intersection(alias_keys):
            continue
        if not alias_keys:
            fallback_key = _normalize_scoring_text_key(f"{dimension}|{point}|{score_text}")
            if fallback_key and fallback_key in point_seen:
                continue
            if fallback_key:
                alias_keys.add(fallback_key)
        point_seen.update(alias_keys)
        deduped.append(
            {
                "dimension": dimension,
                "point": point,
                "criterion": criterion,
                "indicator": indicator,
                "score": score_text,
                "score_value": score_value,
            }
        )
    return deduped


def format_score_table_for_prompt(score_items_raw: Any) -> dict[str, Any]:
    score_items = dedupe_score_items_for_prompt(score_items_raw)
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for item in score_items:
        dimension = str(item.get("dimension", "")).strip() or "未命名维度"
        point = str(item.get("point", "")).strip() or "未命名评估点"
        grouped.setdefault(dimension, {}).setdefault(point, []).append(item)

    dimensions: list[dict[str, Any]] = []
    for dimension_name, point_groups in grouped.items():
        points: list[dict[str, Any]] = []
        dimension_max = 0.0
        for point_name, items in point_groups.items():
            sorted_items = sorted(
                items,
                key=lambda current: float(current.get("score_value", 0.0) or 0.0),
                reverse=True,
            )
            point_max = max(
                (max(float(current.get("score_value", 0.0) or 0.0), 0.0) for current in sorted_items),
                default=0.0,
            )
            dimension_max += point_max
            points.append(
                {
                    "point": point_name,
                    "point_max": round(point_max, 2),
                    "criteria": [
                        {
                            "criterion": str(current.get("criterion", "")).strip(),
                            "indicator": str(current.get("indicator", "")).strip(),
                            "score_value": round(max(float(current.get("score_value", 0.0) or 0.0), 0.0), 2),
                        }
                        for current in sorted_items
                    ],
                }
            )
        points.sort(key=lambda current: str(current.get("point", "")).strip())
        dimensions.append(
            {
                "dimension": dimension_name,
                "dimension_max": round(dimension_max, 2),
                "points": points,
            }
        )
    dimensions.sort(key=lambda current: str(current.get("dimension", "")).strip())
    max_score = round(calculate_score_items_max_score(score_items), 2)
    return {
        "max_score": max_score,
        "item_count": len(score_items),
        "dimensions": dimensions,
    }


def build_score_items_from_templates(job_payload: dict[str, Any]) -> list[dict[str, Any]]:
    templates = job_payload.get("templates")
    if not isinstance(templates, list):
        return []
    active_version_raw = job_payload.get("active_template_version")
    active_version = str(active_version_raw).strip() if active_version_raw is not None else ""
    selected_templates = templates
    if active_version:
        selected_templates = [
            item
            for item in templates
            if isinstance(item, dict) and str(item.get("version_no", "")).strip() == active_version
        ] or templates
    out: list[dict[str, Any]] = []
    for template in selected_templates:
        if not isinstance(template, dict):
            continue
        dimensions = template.get("dimensions")
        if not isinstance(dimensions, list):
            continue
        for raw_item in dimensions:
            if not isinstance(raw_item, dict):
                continue
            item = normalize_score_item(raw_item)
            if not item["dimension"]:
                continue
            out.append(item)
    return out


def build_job_snapshot(
    *,
    job_payload: dict[str, Any],
    department_scope: str,
    job_id: str,
    job_code: str,
    job_title: str,
) -> dict[str, Any]:
    score_items = build_score_items_from_templates(job_payload)
    max_score = calculate_score_items_max_score(score_items)
    return {
        "job_id": job_id,
        "job_code": job_code,
        "job_title": job_title,
        "department_scope": department_scope,
        "jd": str(job_payload.get("jd", "")).strip(),
        "requirements": str(job_payload.get("requirements", "")).strip(),
        "criteria": job_payload.get("criteria") if isinstance(job_payload.get("criteria"), dict) else {},
        "auto_score_enabled": bool(job_payload.get("auto_score_enabled", False)),
        "score_table_version": str(job_payload.get("active_template_version", "")).strip(),
        "score_items": score_items,
        "score_table_json": format_score_table_for_prompt(score_items),
        "score_table_max_score": round(max_score, 2),
    }
