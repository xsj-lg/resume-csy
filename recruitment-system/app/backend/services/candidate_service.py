#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sqlite3
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

from ..repositories.candidate_repository import (
    default_profile,
    default_round,
    get_candidate_file_by_id,
    get_candidate_file_by_original_filename,
    insert_profile_if_missing,
    list_candidate_file_rows,
    load_profile,
    load_rounds,
    parse_candidate_from_filename,
    profile_summaries,
    seed_candidate_profiles,
)
from ..repositories.sqlite_helpers import connect_db
from ..utils.time_utils import (
    now_ts as time_now_ts,
    today_date_tag as time_today_date_tag,
    today_dataset_dir as time_today_dataset_dir,
    utc_now_iso as time_utc_now_iso,
)
from .db_service import (
    has_column,
    has_table,
    init_db,
    migrate_candidate_file_inflow_date,
    migrate_candidate_id_to_uuid,
    migrate_candidate_identity,
    migrate_legacy_data,
    migrate_round_stage_names,
    migrate_stage_status_model,
    scan_all_pdf_files,
)
from .candidate_query_service import (
    candidate_map,
    filter_candidates,
    list_candidates,
    list_candidates_for_user,
    list_interview_calendar,
    list_interview_calendar_for_user,
    parse_candidate_filters,
)
from .candidate_command_service import (
    create_candidate_from_upload,
    delete_candidate,
    resolve_resume_path,
    sync_resumes_from_storage,
)
from .candidate_workflow_service import (
    can_access_candidate,
    can_delete_candidate,
    can_sync_resumes,
    can_transition_stage,
    can_upload_resume,
    can_write_profile,
    can_write_round,
    get_evaluation,
    resolve_profile_job_binding,
    save_evaluation,
    save_profile_only,
    save_round_only,
    save_star_only,
    transition_stage,
    visible_candidate_ids_for_user,
)
from .candidate_domain_service import (
    BASE_OPTIONS,
    DEFAULT_STAGE,
    EXPERIENCE_TYPES,
    FAILED_STATUS_BY_STAGE,
    HIRE_TYPES,
    INTERVIEW_STAGES,
    LEGACY_STAGE_MAP,
    SALARY_MODES,
    STAGE_STATUS_ENDED,
    STAGE_STATUS_PASSED,
    STAGE_STATUS_PENDING,
    STAGE_STATUS_VALUES,
    STATUS_PASSED,
    WAITING_STATUS_BY_STAGE,
    build_stage_statuses,
    current_active_stage,
    decode_stage_statuses,
    derive_interview_status,
    dump_stage_statuses,
    format_interview_datetime,
    normalize_stage_name,
    parse_interview_datetime,
    stage_index,
    stage_status_template,
    validate_profile_payload,
    validate_round_payload,
    validate_stage_action_payload,
    validate_star_payload,
)
from .llm_service import (
    call_llm_chat_stream,
    load_active_prompt,
    load_llm_runtime_config,
    parse_llm_json_response,
    public_llm_runtime_config,
    render_prompt_template,
    resolve_config_path,
    resolve_llm_api_key,
    safe_read_json,
)
from .job_service import (
    _normalize_job_template_item,
    can_manage_jobs,
    can_view_jobs,
    delete_job_score_table_version,
    get_job_score_table_preview,
    list_jobs_for_user,
    replace_jobs_from_client,
    upload_job_score_table,
)
from .role_user_service import (
    DEFAULT_NON_ADMIN_ROLE,
    ROLE_ADMINISTRATOR,
    ROLE_HIRING_MANAGER,
    ROLE_HR_SPECIALIST,
    ROLE_INTERVIEWER,
    change_password,
    clear_expired_sessions,
    create_session,
    create_user,
    delete_session,
    delete_user_sessions,
    get_current_user_by_session,
    get_user_by_id,
    get_user_by_username,
    hash_password,
    list_active_user_options,
    list_role_definitions,
    list_users,
    migrate_user_roles,
    normalize_department_scope,
    normalize_role_code,
    normalize_username,
    parse_bool_flag,
    reset_user_password,
    role_code_from_is_admin,
    role_name,
    sanitize_user_row,
    seed_default_admin,
    update_user,
    user_department_scope,
    user_is_admin,
    user_role_code,
    validate_change_password_payload,
    validate_login_payload,
    validate_user_payload,
    validate_user_update_payload,
    validate_username,
    verify_password,
)
from .resume_extract_service import (
    extract_and_store_resume_profile,
    extract_pdf_text,
    get_candidate_resume_text,
    trigger_resume_extract_for_candidate,
)
from .score_table_service import (
    ALLOWED_SCORE_TEMPLATE_EXTENSIONS,
    MAX_JOB_TEMPLATE_BYTES,
    _call_llm_score_table_preview,
    _rows_to_prompt_text,
    build_job_snapshot,
    build_score_items_from_templates,
    calculate_score_items_max_score,
    dedupe_score_items_for_prompt as _dedupe_score_items_for_prompt,
    format_score_table_for_prompt as _format_score_table_for_prompt,
    normalize_score_item,
    normalize_score_table_preview_payload as _normalize_score_table_preview_payload,
    parse_score_table_preview,
    sanitize_score_template_filename,
    score_to_float,
)
from .auto_score_service import (
    calculate_match_level,
    call_llm_auto_score,
    load_auto_score_by_candidate,
    normalize_llm_auto_score_output,
    normalize_llm_score_payload,
    save_auto_score,
    score_with_fallback_rules,
    trigger_auto_score_for_candidate,
)
from .operation_log_service import ensure_operation_log_table


ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATASET_ROOT_DIR = ROOT_DIR / "data" / "cv" / "ais"
JOB_TEMPLATE_ROOT_DIR = ROOT_DIR / "data" / "job_templates"
DB_PATH = ROOT_DIR / "data" / "recruitment.sqlite3"
STATIC_DIR = ROOT_DIR / "web"
DEFAULT_LLM_CONFIG_PATH = ROOT_DIR / "config" / "llm-config.json"
ENV_NAME_PATTERN = re.compile(r"^[A-Z_][A-Z0-9_]*$")
CHUNKED_JSON_RE = re.compile(r"\{[\s\S]*\}", re.DOTALL)
PHONE_PATTERN = re.compile(r"(?:\+?86[ -]?)?(1[3-9]\d{9})")
EMAIL_PATTERN = re.compile(r"[\w.-]+@[\w.-]+\.[A-Za-z]{2,6}")
SQLITE_LOCK_RETRY_ATTEMPTS = 8
SQLITE_LOCK_RETRY_DELAY_SECONDS = 0.15

UUID32_PATTERN = re.compile(r"^[0-9a-f]{32}$")
DATE_TAG_PATTERN = re.compile(r"^\d{8}$")
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

ROLE_UPLOAD_ALLOWED = {ROLE_ADMINISTRATOR, ROLE_HR_SPECIALIST}
ROLE_DELETE_CANDIDATE_ALLOWED = {ROLE_ADMINISTRATOR, ROLE_HR_SPECIALIST}
ROLE_PROFILE_WRITE_ALLOWED = {ROLE_ADMINISTRATOR, ROLE_HR_SPECIALIST}
HR_ALLOWED_ROUND_STAGES = {"初筛"}
MANAGER_ALLOWED_ROUND_STAGES = {"二面", "HR面"}
MANAGER_DECISION_STAGES = {"二面", "HR面"}


def infer_department_scope(applied_position: str, preset_position: str) -> str:
    text = f"{applied_position or ''} {preset_position or ''}".strip()
    if not text:
        return ""
    if "销售" in text:
        return "销售部"
    if "算法" in text:
        return "算法部"
    if "项目" in text:
        return "项目部"
    if "人事" in text or "hr" in text.lower():
        return "人事部"
    if "研发" in text or "开发" in text:
        return "研发部"
    return ""


def today_dataset_dir() -> Path:
    return time_today_dataset_dir(DATASET_ROOT_DIR)


def today_date_tag() -> str:
    return time_today_date_tag()


def is_uuid_candidate_id(value: str) -> bool:
    return bool(UUID32_PATTERN.fullmatch((value or "").strip().lower()))


def normalize_date_tag(value: str) -> str:
    text = (value or "").strip()
    if not DATE_TAG_PATTERN.fullmatch(text):
        return ""
    try:
        datetime.strptime(text, "%Y%m%d")
    except ValueError:
        return ""
    return text


def infer_inflow_date_from_rel_path(storage_rel_path: str, fallback: str = "") -> str:
    parts = Path((storage_rel_path or "").strip()).parts
    if parts:
        parsed = normalize_date_tag(parts[0])
        if parsed:
            return parsed
    return normalize_date_tag(fallback) or today_date_tag()


def sanitize_uploaded_filename(filename: str) -> str:
    normalized = Path((filename or "").replace("\\", "/")).name.strip()
    normalized = normalized.replace("\x00", "")
    if not normalized:
        raise ValueError("文件名不能为空")
    if not normalized.lower().endswith(".pdf"):
        raise ValueError("仅支持上传 PDF 文件")
    return normalized


def resolve_storage_path(storage_rel_path: str) -> Path | None:
    rel_path = (storage_rel_path or "").strip()
    if not rel_path:
        return None
    root = DATASET_ROOT_DIR.resolve()
    file_path = (DATASET_ROOT_DIR / rel_path).resolve()
    try:
        file_path.relative_to(root)
    except ValueError:
        return None
    if file_path.suffix.lower() != ".pdf":
        return None
    return file_path


def resolve_job_template_path(storage_rel_path: str) -> Path | None:
    rel_path = (storage_rel_path or "").strip()
    if not rel_path:
        return None
    root = JOB_TEMPLATE_ROOT_DIR.resolve()
    file_path = (JOB_TEMPLATE_ROOT_DIR / rel_path).resolve()
    try:
        file_path.relative_to(root)
    except ValueError:
        return None
    if file_path.suffix.lower() not in ALLOWED_SCORE_TEMPLATE_EXTENSIONS:
        return None
    return file_path


def ensure_pdf_content(content: bytes) -> None:
    if not content:
        raise ValueError("上传文件为空")
    if not content.startswith(b"%PDF-"):
        raise ValueError("文件内容不是有效 PDF")



def utc_now_iso() -> str:
    return time_utc_now_iso()


def now_ts() -> int:
    return time_now_ts()


def _is_database_locked_error(exc: Exception) -> bool:
    return isinstance(exc, sqlite3.OperationalError) and "database is locked" in str(exc).lower()


def execute_sql_with_retry(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
    *,
    retries: int = SQLITE_LOCK_RETRY_ATTEMPTS,
    base_delay_seconds: float = SQLITE_LOCK_RETRY_DELAY_SECONDS,
) -> sqlite3.Cursor:
    attempt = 0
    while True:
        try:
            return conn.execute(sql, params)
        except sqlite3.OperationalError as exc:
            if not _is_database_locked_error(exc) or attempt >= retries:
                raise
            time.sleep(base_delay_seconds * (attempt + 1))
            attempt += 1


def json_loads_or_empty_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def json_loads_or_empty_list(raw: str) -> list[Any]:
    text = (raw or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def json_dumps_compact(value: Any, default: str) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return default


def parse_job_payload(raw_payload: str) -> dict[str, Any]:
    parsed = json_loads_or_empty_object(raw_payload)
    return parsed if isinstance(parsed, dict) else {}




