from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from ..repositories.sqlite_helpers import connect_db
from ..utils.time_utils import utc_now_iso


def _candidate_service():
    from . import candidate_service

    return candidate_service


def extract_pdf_text(file_path: Path) -> str:
    from pypdf import PdfReader  # type: ignore

    try:
        reader = PdfReader(str(file_path))
        parts: list[str] = []
        for page in reader.pages:
            text = (page.extract_text() or "").strip()
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
    except Exception:
        try:
            content = file_path.read_bytes()
        except OSError:
            return ""
        text = content.decode("utf-8", errors="ignore")
        if text.strip():
            return text.strip()
        return content.decode("latin-1", errors="ignore").strip()


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
               experience_type, graduation_year, work_years
        FROM candidate_profiles
        WHERE candidate_id = ?
        """,
        (candidate_id,),
    ).fetchone()
    if row is None:
        return
    basic = structured_payload.get("basic", {}) if isinstance(structured_payload.get("basic"), dict) else {}
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
            json.dumps(structured_payload, ensure_ascii=False, separators=(",", ":")),
            "success",
            "llm",
            model_name,
            "",
            now,
            now,
            candidate_id,
        ),
    )


def trigger_resume_extract_for_candidate(candidate_id: str) -> dict[str, Any]:
    candidate_service = _candidate_service()
    with connect_db(candidate_service.DB_PATH) as conn:
        candidate_service.seed_candidate_profiles(conn)
        conn.commit()
        profile = candidate_service.load_profile(conn, candidate_id)
        file_row = candidate_service.get_candidate_file_by_id(conn, candidate_id)
        if profile is None or file_row is None or int(file_row.get("is_active", 0)) != 1:
            raise ValueError("candidate not found")

        file_path = candidate_service.resolve_storage_path(str(file_row.get("storage_rel_path", "")))
        if file_path is None or not file_path.exists():
            raise ValueError("候选人简历文件不存在")
        try:
            resume_text = extract_pdf_text(file_path)
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
    "normalize_resume_structured_payload",
    "extract_and_store_resume_profile",
    "trigger_resume_extract_for_candidate",
]
