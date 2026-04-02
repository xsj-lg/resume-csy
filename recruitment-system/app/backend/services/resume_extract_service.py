from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .llm_service import resolve_config_path, safe_read_json
from ..repositories.sqlite_helpers import connect_db
from ..utils.time_utils import utc_now_iso

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_RESUME_PARSER_CONFIG_PATH = ROOT_DIR / "config" / "pdf-parser-config.json"
DEFAULT_RESUME_PARSER_URL = "http://127.0.0.1:7642/ais/parser/syncParseFile"
DEFAULT_RESUME_PARSER_TIMEOUT_SECONDS = 30.0
DEFAULT_RESUME_PARSER_FALLBACK_ENABLED = True


def _candidate_service():
    from . import candidate_service

    return candidate_service


def _parse_resume_parser_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().casefold()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _load_resume_parser_runtime() -> dict[str, Any]:
    config_path = resolve_config_path(
        os.environ.get("RESUME_APP_PDF_PARSER_CONFIG_PATH", ""),
        DEFAULT_RESUME_PARSER_CONFIG_PATH,
    )
    config, error = safe_read_json(config_path)
    runtime: dict[str, Any] = {
        "parser_url": DEFAULT_RESUME_PARSER_URL,
        "timeout_seconds": DEFAULT_RESUME_PARSER_TIMEOUT_SECONDS,
        "fallback_enabled": DEFAULT_RESUME_PARSER_FALLBACK_ENABLED,
        "source": "default",
        "config_path": str(config_path),
        "warning": error,
    }
    if not error:
        parser_url = str(
            config.get(
                "service_url",
                config.get("parser_url", config.get("url", DEFAULT_RESUME_PARSER_URL)),
            )
            or ""
        ).strip()
        if parser_url:
            runtime["parser_url"] = parser_url
        runtime["fallback_enabled"] = _parse_resume_parser_bool(
            config.get("fallback_enabled", DEFAULT_RESUME_PARSER_FALLBACK_ENABLED),
            DEFAULT_RESUME_PARSER_FALLBACK_ENABLED,
        )
        runtime["source"] = "file"
        timeout_raw = config.get("timeout_seconds", config.get("parser_timeout_seconds", DEFAULT_RESUME_PARSER_TIMEOUT_SECONDS))
        try:
            timeout_seconds = float(timeout_raw or DEFAULT_RESUME_PARSER_TIMEOUT_SECONDS)
        except (TypeError, ValueError):
            timeout_seconds = DEFAULT_RESUME_PARSER_TIMEOUT_SECONDS
        if timeout_seconds > 0:
            runtime["timeout_seconds"] = timeout_seconds

    parser_url_override = str(os.environ.get("RESUME_APP_PDF_PARSER_URL", "") or "").strip()
    if parser_url_override:
        runtime["parser_url"] = parser_url_override
        runtime["source"] = "env"
    try:
        timeout_seconds = float(
            os.environ.get("RESUME_APP_PDF_PARSER_TIMEOUT_SECONDS", str(runtime["timeout_seconds"]))
            or runtime["timeout_seconds"]
        )
    except (TypeError, ValueError):
        timeout_seconds = float(runtime["timeout_seconds"])
    if timeout_seconds <= 0:
        timeout_seconds = DEFAULT_RESUME_PARSER_TIMEOUT_SECONDS
    runtime["timeout_seconds"] = timeout_seconds
    fallback_override = os.environ.get("RESUME_APP_PDF_PARSER_FALLBACK_ENABLED", "")
    if str(fallback_override or "").strip():
        runtime["fallback_enabled"] = _parse_resume_parser_bool(
            fallback_override,
            bool(runtime["fallback_enabled"]),
        )
        runtime["source"] = "env"
    return runtime


def _build_resume_parser_request_body(file_path: Path) -> tuple[bytes, str]:
    candidate_service = _candidate_service()
    content = file_path.read_bytes()
    upload_filename = file_path.name.replace('"', "") or "resume.bin"
    content_type = candidate_service.guess_resume_content_type(upload_filename)
    boundary = f"----ResumeAppBoundary{uuid.uuid4().hex}"
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{upload_filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    footer = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return header + content + footer, boundary


def _request_resume_parser_payload(file_path: Path, runtime: dict[str, Any]) -> dict[str, Any]:
    parser_url = str(runtime.get("parser_url", DEFAULT_RESUME_PARSER_URL) or "").strip() or DEFAULT_RESUME_PARSER_URL
    timeout_seconds = float(runtime.get("timeout_seconds", DEFAULT_RESUME_PARSER_TIMEOUT_SECONDS) or DEFAULT_RESUME_PARSER_TIMEOUT_SECONDS)
    body, boundary = _build_resume_parser_request_body(file_path)
    request = Request(
        parser_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read()
    except HTTPError as exc:
        error_body = ""
        try:
            error_body = exc.read().decode("utf-8", errors="ignore").strip()
        except Exception:
            error_body = ""
        raise ValueError(f"PDF 解析服务返回异常状态 {exc.code}: {error_body or exc.reason}") from exc
    except URLError as exc:
        raise ValueError(f"PDF 解析服务不可达: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ValueError("PDF 解析服务请求超时") from exc

    try:
        parsed = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("PDF 解析服务返回的不是合法 JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("PDF 解析服务返回结构非法")
    return parsed


def _build_resume_parser_service_payload(raw_payload: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    payload = dict(raw_payload)
    payload["_resume_parser_meta"] = {
        "source": "service",
        "config_path": str(runtime.get("config_path", "")),
        "runtime_source": str(runtime.get("source", "")),
    }
    return payload


def _build_resume_parser_fallback_payload(
    *,
    parser_error: str,
    fallback_tool: str,
    resume_text: str,
    runtime: dict[str, Any],
) -> dict[str, Any]:
    return {
        "text": resume_text,
        "_resume_parser_meta": {
            "source": "legacy_fallback",
            "fallback_tool": fallback_tool,
            "parser_error": parser_error,
            "config_path": str(runtime.get("config_path", "")),
            "runtime_source": str(runtime.get("source", "")),
        },
    }


def _parse_pdf_text_with_payload(file_path: Path, runtime: dict[str, Any]) -> tuple[dict[str, Any], str]:
    raw_payload = _request_resume_parser_payload(file_path, runtime)
    extracted_text = _extract_text_from_parser_payload(raw_payload)
    if extracted_text:
        return _build_resume_parser_service_payload(raw_payload, runtime), extracted_text
    raise ValueError("PDF 解析服务返回结果为空")


def _extract_pdf_text_with_legacy_tools(file_path: Path) -> tuple[str, str]:
    errors: list[str] = []
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(file_path))
        parts: list[str] = []
        for page in reader.pages:
            text = (page.extract_text() or "").strip()
            if text:
                parts.append(text)
        extracted_text = "\n".join(parts).strip()
        if extracted_text:
            return extracted_text, "pypdf"
        errors.append("pypdf 结果为空")
    except Exception as exc:
        errors.append(f"pypdf 失败: {exc}")

    try:
        content = file_path.read_bytes()
    except OSError as exc:
        errors.append(f"读取文件失败: {exc}")
        raise ValueError("；".join(errors)) from exc

    utf8_text = content.decode("utf-8", errors="ignore").strip()
    if utf8_text:
        return utf8_text, "byte_decode_utf8"
    latin1_text = content.decode("latin-1", errors="ignore").strip()
    if latin1_text:
        return latin1_text, "byte_decode_latin1"
    errors.append("字节解码结果为空")
    raise ValueError("；".join(errors))


def parse_resume_file(file_path: Path) -> tuple[dict[str, Any], str]:
    runtime = _load_resume_parser_runtime()
    candidate_service = _candidate_service()
    is_image_file = candidate_service.is_image_resume_filename(file_path.name)
    try:
        return _parse_pdf_text_with_payload(file_path, runtime)
    except Exception as parser_exc:
        if is_image_file:
            raise ValueError(f"图片解析失败: {parser_exc}") from parser_exc
        if not bool(runtime.get("fallback_enabled", DEFAULT_RESUME_PARSER_FALLBACK_ENABLED)):
            raise
        legacy_text, legacy_tool = _extract_pdf_text_with_legacy_tools(file_path)
        return (
            _build_resume_parser_fallback_payload(
                parser_error=str(parser_exc),
                fallback_tool=legacy_tool,
                resume_text=legacy_text,
                runtime=runtime,
            ),
            legacy_text,
        )


def _extract_text_from_parser_paragraph(paragraph: Any) -> str:
    if not isinstance(paragraph, dict):
        return ""
    text_para = paragraph.get("textPara")
    if not isinstance(text_para, dict):
        return ""
    content = re.sub(r"\s+", " ", str(text_para.get("content", "") or "").strip())
    if not content:
        return ""
    content = re.sub(r"^(?:(?:[0-9A-Za-z_~\-]{1,4}\s+){3,}[0-9A-Za-z_~\-]{0,4})", "", content).strip()
    content = re.sub(r"(?:(?:[0-9A-Za-z_~\-]{1,4}\s+){3,}[0-9A-Za-z_~\-]{0,4})$", "", content).strip()
    if not content:
        return ""
    compact_ascii = re.sub(r"\s+", "", content)
    if re.fullmatch(r"[0-9A-Za-z_~\-\s]{4,}", content) and (
        " " in content or "_" in content or "~" in content or len(compact_ascii) >= 10
    ):
        return ""
    return content


def _extract_text_from_parser_payload(raw_payload: dict[str, Any]) -> str:
    meta = raw_payload.get("_resume_parser_meta")
    if isinstance(meta, dict) and str(meta.get("source", "")).strip() == "legacy_fallback":
        return str(raw_payload.get("text", "") or "").strip()
    pages = raw_payload.get("pages")
    if not isinstance(pages, list):
        return ""

    page_texts: list[str] = []
    seen_global: set[str] = set()
    for page in pages:
        if not isinstance(page, dict):
            continue
        paragraphs = page.get("paragraphs")
        if not isinstance(paragraphs, list):
            continue
        page_lines: list[str] = []
        for paragraph in paragraphs:
            text = _extract_text_from_parser_paragraph(paragraph)
            if not text or text in seen_global:
                continue
            seen_global.add(text)
            page_lines.append(text)
        if page_lines:
            page_texts.append("\n".join(page_lines))
    return "\n\n".join(page_texts).strip()


def extract_pdf_text(file_path: Path) -> str:
    _, extracted_text = parse_resume_file(file_path)
    return extracted_text


def _decode_cached_resume_parser_payload(raw_payload_json: str) -> dict[str, Any]:
    text = str(raw_payload_json or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _store_candidate_resume_cache(
    conn: sqlite3.Connection,
    *,
    candidate_id: str,
    raw_payload: dict[str, Any],
    resume_text: str,
) -> None:
    candidate_service = _candidate_service()
    now = utc_now_iso()
    candidate_service.execute_sql_with_retry(
        conn,
        """
        UPDATE candidate_files
        SET resume_parsed_text = ?, resume_parser_payload_json = ?, resume_parser_updated_at = ?
        WHERE candidate_id = ?
        """,
        (
            resume_text,
            json.dumps(raw_payload, ensure_ascii=False, separators=(",", ":")),
            now,
            candidate_id,
        ),
    )


def get_candidate_resume_text(
    conn: sqlite3.Connection,
    *,
    candidate_id: str,
    force_refresh: bool = False,
) -> str:
    candidate_service = _candidate_service()
    file_row = candidate_service.get_candidate_file_by_id(conn, candidate_id)
    if file_row is None or int(file_row.get("is_active", 0)) != 1:
        raise ValueError("candidate not found")

    cached_text = str(file_row.get("resume_parsed_text", "") or "").strip()
    if not force_refresh and cached_text:
        return cached_text

    cached_payload = _decode_cached_resume_parser_payload(str(file_row.get("resume_parser_payload_json", "") or ""))
    if not force_refresh and cached_payload:
        cached_payload_text = _extract_text_from_parser_payload(cached_payload)
        if cached_payload_text:
            if cached_payload_text != cached_text:
                _store_candidate_resume_cache(
                    conn,
                    candidate_id=candidate_id,
                    raw_payload=cached_payload,
                    resume_text=cached_payload_text,
                )
            return cached_payload_text

    file_path = candidate_service.resolve_storage_path(str(file_row.get("storage_rel_path", "")).strip())
    if file_path is None or not file_path.exists():
        if cached_text:
            return cached_text
        raise ValueError("候选人简历文件不存在且数据库无可用解析缓存")

    raw_payload, resume_text = parse_resume_file(file_path)
    _store_candidate_resume_cache(
        conn,
        candidate_id=candidate_id,
        raw_payload=raw_payload,
        resume_text=resume_text,
    )
    return resume_text


def _normalize_resume_text_items(raw_items: Any, *, limit: int = 20) -> list[str]:
    values: list[Any]
    if isinstance(raw_items, list):
        values = raw_items
    elif isinstance(raw_items, str):
        values = [part for part in re.split(r"[\n;，；、]+", raw_items) if part.strip()]
    else:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def _read_resume_structured_text(
    raw_item: dict[str, Any],
    key: str,
    aliases: dict[str, list[str]] | None = None,
) -> str:
    current_aliases = aliases or {}
    value = str(raw_item.get(key, "")).strip()
    if value:
        return value
    for alias_key in current_aliases.get(key, []):
        value = str(raw_item.get(alias_key, "")).strip()
        if value:
            return value
    return ""


def _read_resume_structured_list(
    raw_item: dict[str, Any],
    key: str,
    aliases: dict[str, list[str]] | None = None,
    *,
    limit: int = 12,
) -> list[str]:
    current_aliases = aliases or {}
    values = _normalize_resume_text_items(raw_item.get(key), limit=limit)
    if values:
        return values
    for alias_key in current_aliases.get(key, []):
        values = _normalize_resume_text_items(raw_item.get(alias_key), limit=limit)
        if values:
            return values
    return []


def _normalize_resume_structured_section_items(
    raw_items: Any,
    *,
    keys: list[str],
    aliases: dict[str, list[str]] | None = None,
    list_keys: list[str] | None = None,
    list_aliases: dict[str, list[str]] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    if not isinstance(raw_items, list):
        return []
    out: list[dict[str, Any]] = []
    item_list_keys = list_keys or []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        item: dict[str, Any] = {}
        for key in keys:
            item[key] = _read_resume_structured_text(raw_item, key, aliases)
        for list_key in item_list_keys:
            item[list_key] = _read_resume_structured_list(raw_item, list_key, list_aliases, limit=12)
        if any((str(item.get(key, "")).strip() for key in keys)) or any((item.get(list_key) for list_key in item_list_keys)):
            out.append(item)
        if len(out) >= limit:
            break
    return out


def normalize_resume_structured_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    candidate_service = _candidate_service()
    basic_raw = raw_payload.get("basic")
    basic_raw = basic_raw if isinstance(basic_raw, dict) else {}
    basic = {
        "name": str(basic_raw.get("name", raw_payload.get("name", ""))).strip(),
        "phone": str(basic_raw.get("phone", raw_payload.get("phone", ""))).strip(),
        "email": str(basic_raw.get("email", raw_payload.get("email", ""))).strip(),
        "location": str(basic_raw.get("location", raw_payload.get("location", ""))).strip(),
        "target_position": str(basic_raw.get("target_position", raw_payload.get("target_position", ""))).strip(),
        "highest_education": str(basic_raw.get("highest_education", raw_payload.get("highest_education", ""))).strip(),
        "school_name": str(basic_raw.get("school_name", raw_payload.get("school_name", ""))).strip(),
        "major": str(basic_raw.get("major", raw_payload.get("major", ""))).strip(),
        "experience_type": str(basic_raw.get("experience_type", raw_payload.get("experience_type", ""))).strip(),
        "graduation_year": str(basic_raw.get("graduation_year", raw_payload.get("graduation_year", ""))).strip(),
        "work_years": str(basic_raw.get("work_years", raw_payload.get("work_years", ""))).strip(),
    }
    if basic["experience_type"] not in candidate_service.EXPERIENCE_TYPES:
        basic["experience_type"] = ""

    education_aliases = {
        "start": ["start_date", "start_time", "from", "begin", "begin_date"],
        "end": ["end_date", "end_time", "to", "finish", "until", "end_at"],
        "summary": ["description", "desc", "detail", "details", "content"],
    }
    work_aliases = {
        "title": ["position", "role", "job_title"],
        "start": ["start_date", "start_time", "from", "begin", "begin_date"],
        "end": ["end_date", "end_time", "to", "finish", "until", "end_at"],
        "summary": ["description", "desc", "detail", "details", "content"],
    }
    project_aliases = {
        "name": ["project_name", "project", "project_title"],
        "start": ["start_date", "start_time", "from", "begin", "begin_date"],
        "end": ["end_date", "end_time", "to", "finish", "until", "end_at"],
        "summary": ["description", "desc", "detail", "details", "content"],
    }
    project_list_aliases = {"tech_stack": ["tech", "techs", "technology", "technologies", "stack"]}
    scoring_evidence_keys = [
        "academic_performance",
        "programming_language",
        "algorithm_data_structure",
        "development_tools",
        "technical_breadth",
        "project_depth",
        "code_quality",
        "testing_quality",
        "documentation",
        "learning_ability",
        "communication_collaboration",
        "initiative",
        "logic_expression",
    ]
    scoring_evidence_raw = raw_payload.get("scoring_evidence")
    scoring_evidence_obj = scoring_evidence_raw if isinstance(scoring_evidence_raw, dict) else {}
    scoring_evidence = {
        key: _normalize_resume_text_items(scoring_evidence_obj.get(key, raw_payload.get(key, [])), limit=10)
        for key in scoring_evidence_keys
    }

    return {
        "basic": basic,
        "skills": _normalize_resume_text_items(raw_payload.get("skills"), limit=30),
        "certificates": _normalize_resume_text_items(raw_payload.get("certificates"), limit=20),
        "summary": str(raw_payload.get("summary", "")).strip(),
        "scoring_evidence": scoring_evidence,
        "education": _normalize_resume_structured_section_items(
            raw_payload.get("education"),
            keys=["school", "degree", "major", "start", "end", "summary"],
            aliases=education_aliases,
            limit=20,
        ),
        "work_experience": _normalize_resume_structured_section_items(
            raw_payload.get("work_experience"),
            keys=["company", "title", "start", "end", "summary"],
            aliases=work_aliases,
            limit=30,
        ),
        "project_experience": _normalize_resume_structured_section_items(
            raw_payload.get("project_experience"),
            keys=["name", "role", "start", "end", "summary"],
            aliases=project_aliases,
            list_keys=["tech_stack"],
            list_aliases=project_list_aliases,
            limit=30,
        ),
    }


def _call_llm_resume_profile_extract(
    *,
    runtime: dict[str, Any],
    filename: str,
    candidate_name: str,
    resume_text: str,
) -> tuple[dict[str, Any], str]:
    candidate_service = _candidate_service()
    if not bool(runtime.get("enabled", False)):
        return {}, "LLM 未启用"
    model = str(runtime.get("model", "")).strip()
    if not model:
        return {}, "LLM 配置不完整"
    resume_body = str(resume_text or "").strip()
    if not resume_body:
        return {}, "简历文本为空"

    system_prompt = (
        "你是中文招聘简历信息抽取器。"
        "请将简历抽取为结构化 JSON，不要输出解释文本。"
        "输出字段必须包含：basic, education, work_experience, project_experience, skills, certificates, summary, scoring_evidence。"
        "basic 字段包含：name, phone, email, location, target_position, highest_education, school_name, major, "
        "experience_type(应届生/已工作), graduation_year, work_years。"
        "scoring_evidence 字段包含以下 key，值均为字符串数组："
        "academic_performance, programming_language, algorithm_data_structure, development_tools, technical_breadth, "
        "project_depth, code_quality, testing_quality, documentation, learning_ability, communication_collaboration, "
        "initiative, logic_expression。"
        "抽取时优先保留可用于评分判定的明确事实证据。"
        "禁止编造不存在的信息，缺失时返回空字符串或空数组。"
    )
    user_prompt = (
        f"候选人文件名：{filename}\n"
        f"候选人名称（如果已有）：{candidate_name}\n"
        "请严格按 JSON 输出，未知字段用空字符串，列表字段未知用空数组。\n"
        "简历文本如下：\n"
        f"{resume_body[:18000]}"
    )
    content, reasoning_content, stream_error = candidate_service.call_llm_chat_stream(
        runtime=runtime,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=int(runtime.get("max_tokens", 2048) or 2048),
        enable_thinking=False,
    )
    if stream_error:
        return {}, stream_error

    parsed = candidate_service.parse_llm_json_response(str(content or ""))
    if not parsed and reasoning_content:
        parsed = candidate_service.parse_llm_json_response(reasoning_content)
    if not parsed:
        return {}, "LLM 返回内容不是有效 JSON"
    return normalize_resume_structured_payload(parsed), ""


def _merge_resume_profile_field(existing: str, extracted: str) -> str:
    clean_existing = str(existing or "").strip()
    clean_extracted = str(extracted or "").strip()
    if clean_extracted:
        return clean_extracted
    return clean_existing


def _normalize_candidate_name_for_merge(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    normalized = text.casefold()
    if normalized in {"未知", "未提供", "未填写", "不详", "无", "none", "null", "n/a", "na", "姓名", "候选人"}:
        return ""
    return text


def _merge_resume_candidate_name(existing: Any, extracted: Any) -> str:
    merged_extracted = _normalize_candidate_name_for_merge(extracted)
    if merged_extracted:
        return merged_extracted
    return str(existing or "").strip()


def _merge_resume_text_field(existing: Any, extracted: Any) -> str:
    return _merge_resume_profile_field(str(existing or ""), str(extracted or ""))


def _merge_resume_list_field(existing: Any, extracted: Any, *, limit: int) -> list[str]:
    extracted_values = _normalize_resume_text_items(extracted, limit=limit)
    if extracted_values:
        return extracted_values
    return _normalize_resume_text_items(existing, limit=limit)


def _merge_resume_structured_payload(
    existing_payload: dict[str, Any],
    extracted_payload: dict[str, Any],
) -> dict[str, Any]:
    normalized_existing = normalize_resume_structured_payload(existing_payload)
    normalized_extracted = normalize_resume_structured_payload(extracted_payload)

    existing_basic_raw = normalized_existing.get("basic")
    existing_basic = existing_basic_raw if isinstance(existing_basic_raw, dict) else {}
    extracted_basic_raw = normalized_extracted.get("basic")
    extracted_basic = extracted_basic_raw if isinstance(extracted_basic_raw, dict) else {}
    merged_basic = {
        key: _merge_resume_text_field(existing_basic.get(key, ""), extracted_basic.get(key, ""))
        for key in [
            "name",
            "phone",
            "email",
            "location",
            "target_position",
            "highest_education",
            "school_name",
            "major",
            "experience_type",
            "graduation_year",
            "work_years",
        ]
    }

    merged_scoring_evidence: dict[str, list[str]] = {}
    existing_scoring_raw = normalized_existing.get("scoring_evidence")
    existing_scoring = existing_scoring_raw if isinstance(existing_scoring_raw, dict) else {}
    extracted_scoring_raw = normalized_extracted.get("scoring_evidence")
    extracted_scoring = extracted_scoring_raw if isinstance(extracted_scoring_raw, dict) else {}
    for key in [
        "academic_performance",
        "programming_language",
        "algorithm_data_structure",
        "development_tools",
        "technical_breadth",
        "project_depth",
        "code_quality",
        "testing_quality",
        "documentation",
        "learning_ability",
        "communication_collaboration",
        "initiative",
        "logic_expression",
    ]:
        merged_scoring_evidence[key] = _merge_resume_list_field(
            existing_scoring.get(key, []),
            extracted_scoring.get(key, []),
            limit=10,
        )

    merged_payload = {
        "basic": merged_basic,
        "skills": _merge_resume_list_field(normalized_existing.get("skills"), normalized_extracted.get("skills"), limit=30),
        "certificates": _merge_resume_list_field(
            normalized_existing.get("certificates"),
            normalized_extracted.get("certificates"),
            limit=20,
        ),
        "summary": _merge_resume_text_field(
            normalized_existing.get("summary", "") or existing_payload.get("basic_snippet", ""),
            normalized_extracted.get("summary", ""),
        ),
        "scoring_evidence": merged_scoring_evidence,
        "education": (
            normalized_extracted.get("education")
            if isinstance(normalized_extracted.get("education"), list) and normalized_extracted.get("education")
            else normalized_existing.get("education", [])
        ),
        "work_experience": (
            normalized_extracted.get("work_experience")
            if isinstance(normalized_extracted.get("work_experience"), list) and normalized_extracted.get("work_experience")
            else normalized_existing.get("work_experience", [])
        ),
        "project_experience": (
            normalized_extracted.get("project_experience")
            if isinstance(normalized_extracted.get("project_experience"), list) and normalized_extracted.get("project_experience")
            else normalized_existing.get("project_experience", [])
        ),
        "basic_snippet": _merge_resume_text_field(existing_payload.get("basic_snippet", ""), extracted_payload.get("basic_snippet", "")),
        "basic_contact_phone": _merge_resume_text_field(
            existing_payload.get("basic_contact_phone", ""),
            merged_basic.get("phone", ""),
        ),
        "basic_contact_email": _merge_resume_text_field(
            existing_payload.get("basic_contact_email", ""),
            merged_basic.get("email", ""),
        ),
    }
    return merged_payload


def extract_and_store_resume_profile(
    conn: sqlite3.Connection,
    *,
    candidate_id: str,
    filename: str,
    candidate_name: str,
    resume_text: str,
) -> None:
    candidate_service = _candidate_service()
    now = utc_now_iso()
    runtime = candidate_service.load_llm_runtime_config()
    model_name = str(runtime.get("model", "")).strip()
    structured_payload, extract_error = _call_llm_resume_profile_extract(
        runtime=runtime,
        filename=filename,
        candidate_name=candidate_name,
        resume_text=resume_text,
    )
    if not structured_payload:
        conn.execute(
            """
            UPDATE candidate_profiles
            SET resume_extract_status = ?, resume_extract_source = ?, resume_extract_model = ?,
                resume_extract_error = ?, resume_extract_updated_at = ?, updated_at = ?
            WHERE candidate_id = ?
            """,
            ("failed", "llm", model_name, extract_error, now, now, candidate_id),
        )
        return

    row = conn.execute(
        """
        SELECT highest_education, school_name, applied_position, preset_position,
               experience_type, graduation_year, work_years, resume_structured_json
        FROM candidate_profiles
        WHERE candidate_id = ?
        """,
        (candidate_id,),
    ).fetchone()
    if row is None:
        return
    existing_structured_payload = candidate_service.json_loads_or_empty_object(str(row[7] or "").strip())
    merged_structured_payload = _merge_resume_structured_payload(existing_structured_payload, structured_payload)
    basic = (
        merged_structured_payload.get("basic", {})
        if isinstance(merged_structured_payload.get("basic"), dict)
        else {}
    )
    merged_candidate_name = _merge_resume_candidate_name(candidate_name, basic.get("name", ""))
    if not merged_candidate_name:
        merged_candidate_name = Path(str(filename or "").strip()).stem or "未命名候选人"
    basic["name"] = merged_candidate_name
    merged_structured_payload["basic"] = basic
    highest_education = _merge_resume_profile_field(str(row[0] or ""), str(basic.get("highest_education", "")))
    school_name = _merge_resume_profile_field(str(row[1] or ""), str(basic.get("school_name", "")))
    applied_position = _merge_resume_profile_field(str(row[2] or ""), str(basic.get("target_position", "")))
    preset_position = _merge_resume_profile_field(str(row[3] or ""), str(basic.get("target_position", "")))
    experience_type = str(row[4] or "").strip()
    extracted_experience_type = str(basic.get("experience_type", "")).strip()
    if extracted_experience_type in candidate_service.EXPERIENCE_TYPES:
        experience_type = extracted_experience_type
    graduation_year = _merge_resume_profile_field(str(row[5] or ""), str(basic.get("graduation_year", "")))
    work_years = _merge_resume_profile_field(str(row[6] or ""), str(basic.get("work_years", "")))
    if experience_type == "应届生":
        work_years = ""
    if experience_type == "已工作":
        graduation_year = ""

    conn.execute(
        """
        UPDATE candidate_profiles
        SET highest_education = ?, school_name = ?, applied_position = ?, preset_position = ?,
            experience_type = ?, graduation_year = ?, work_years = ?,
            resume_structured_json = ?, resume_extract_status = ?, resume_extract_source = ?, resume_extract_model = ?,
            resume_extract_error = ?, resume_extract_updated_at = ?, updated_at = ?
        WHERE candidate_id = ?
        """,
        (
            highest_education or "未知",
            school_name or "未知",
            applied_position,
            preset_position,
            experience_type if experience_type in candidate_service.EXPERIENCE_TYPES else str(row[4] or "应届生"),
            graduation_year,
            work_years,
            json.dumps(merged_structured_payload, ensure_ascii=False, separators=(",", ":")),
            "success",
            "llm",
            model_name,
            "",
            now,
            now,
            candidate_id,
        ),
    )
    conn.execute(
        """
        UPDATE candidate_files
        SET candidate_name = ?
        WHERE candidate_id = ?
        """,
        (merged_candidate_name, candidate_id),
    )


def trigger_resume_extract_for_candidate(candidate_id: str, *, force_refresh: bool = False) -> dict[str, Any]:
    candidate_service = _candidate_service()
    with connect_db(candidate_service.DB_PATH) as conn:
        candidate_service.seed_candidate_profiles(conn)
        conn.commit()
        profile = candidate_service.load_profile(conn, candidate_id)
        file_row = candidate_service.get_candidate_file_by_id(conn, candidate_id)
        if profile is None or file_row is None or int(file_row.get("is_active", 0)) != 1:
            raise ValueError("candidate not found")
        try:
            resume_text = get_candidate_resume_text(conn, candidate_id=candidate_id, force_refresh=force_refresh)
            extract_and_store_resume_profile(
                conn,
                candidate_id=candidate_id,
                filename=str(file_row.get("original_filename", "")).strip(),
                candidate_name=str(file_row.get("candidate_name", "")).strip(),
                resume_text=resume_text,
            )
        except Exception as exc:
            now = utc_now_iso()
            runtime = candidate_service.load_llm_runtime_config()
            model_name = str(runtime.get("model", "")).strip()
            conn.execute(
                """
                UPDATE candidate_profiles
                SET resume_extract_status = ?, resume_extract_source = ?, resume_extract_model = ?,
                    resume_extract_error = ?, resume_extract_updated_at = ?, updated_at = ?
                WHERE candidate_id = ?
                """,
                (
                    "failed",
                    "llm",
                    model_name,
                    f"提取异常: {exc}",
                    now,
                    now,
                    candidate_id,
                ),
            )

        updated_profile = candidate_service.load_profile(conn, candidate_id)
        conn.commit()
    if updated_profile is None:
        raise ValueError("candidate not found")
    return updated_profile


__all__ = [
    "extract_pdf_text",
    "parse_resume_file",
    "get_candidate_resume_text",
    "normalize_resume_structured_payload",
    "extract_and_store_resume_profile",
    "trigger_resume_extract_for_candidate",
]
