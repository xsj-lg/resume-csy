from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from ..repositories.sqlite_helpers import connect_db
from ..utils.time_utils import today_date_tag as time_today_date_tag, utc_now_iso
from .role_user_service import (
    ROLE_ADMINISTRATOR,
    ROLE_HIRING_MANAGER,
    ROLE_HR_SPECIALIST,
    normalize_department_scope,
    user_department_scope,
    user_role_code,
)
from .score_table_service import (
    ALLOWED_SCORE_TEMPLATE_EXTENSIONS,
    MAX_JOB_TEMPLATE_BYTES,
    normalize_score_table_preview_payload,
    parse_score_table_preview,
    sanitize_score_template_filename,
)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
JOB_TEMPLATE_ROOT_DIR = ROOT_DIR / "data" / "job_templates"
DB_PATH = ROOT_DIR / "data" / "recruitment.sqlite3"

INTERVIEW_STAGES = ["初筛", "一面", "二面", "HR面"]
JOB_STATUS_OPEN = "open"
JOB_STATUS_CLOSED = "closed"
JOB_STATUS_VALUES = {JOB_STATUS_OPEN, JOB_STATUS_CLOSED}


def _json_loads_or_empty_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_loads_or_empty_list(raw: str) -> list[Any]:
    text = (raw or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _json_dumps_compact(value: Any, default: str) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return default


def _resolve_job_template_path(storage_rel_path: str) -> Path | None:
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


def can_view_jobs(user: dict[str, Any] | None) -> bool:
    return user_role_code(user) in {ROLE_ADMINISTRATOR, ROLE_HR_SPECIALIST, ROLE_HIRING_MANAGER}


def can_manage_jobs(user: dict[str, Any] | None) -> bool:
    return user_role_code(user) in {ROLE_ADMINISTRATOR, ROLE_HR_SPECIALIST}


def _normalize_job_dimension_item(raw_item: Any) -> dict[str, str] | None:
    if not isinstance(raw_item, dict):
        return None
    dimension = str(raw_item.get("dimension", "")).strip()
    point = str(raw_item.get("point", "")).strip()
    criterion = str(raw_item.get("criterion", "")).strip()
    indicator = str(raw_item.get("indicator", "")).strip()
    score = str(raw_item.get("score", "")).strip()
    if not point and "：" in criterion:
        point = criterion.split("：", 1)[0].strip()
    if not indicator:
        indicator = criterion
    if not dimension and not point and not criterion and not score:
        return None
    return {
        "dimension": dimension,
        "point": point,
        "criterion": criterion,
        "indicator": indicator,
        "score": score,
    }


def _normalize_job_template_item(raw_item: Any) -> dict[str, Any] | None:
    if not isinstance(raw_item, dict):
        return None
    try:
        version_no = max(int(raw_item.get("version_no", 0) or 0), 0)
    except (TypeError, ValueError):
        version_no = 0
    if version_no <= 0:
        return None
    preview_raw = raw_item.get("preview")
    preview = (
        normalize_score_table_preview_payload(preview_raw)
        if isinstance(preview_raw, dict)
        else {"headers": [], "rows": [], "dimensions": [], "note": "", "source": "fallback"}
    )
    dimensions_raw = raw_item.get("dimensions")
    if isinstance(dimensions_raw, list):
        dimensions = [_normalize_job_dimension_item(item) for item in dimensions_raw]
        dimensions = [item for item in dimensions if item is not None]
    else:
        dimensions = [_normalize_job_dimension_item(item) for item in preview.get("dimensions", [])]
        dimensions = [item for item in dimensions if item is not None]
    if dimensions and not preview.get("dimensions"):
        preview["dimensions"] = dimensions
    return {
        "template_id": str(raw_item.get("template_id", "")).strip() or f"tpl_{uuid.uuid4().hex}",
        "version_no": version_no,
        "filename": str(raw_item.get("filename", "")).strip(),
        "size": max(int(raw_item.get("size", 0) or 0), 0),
        "uploaded_at": str(raw_item.get("uploaded_at", "")).strip(),
        "uploaded_by": str(raw_item.get("uploaded_by", "")).strip(),
        "storage_rel_path": str(raw_item.get("storage_rel_path", "")).strip(),
        "preview": preview,
        "dimensions": dimensions,
    }


def _normalize_job_log_item(raw_item: Any) -> dict[str, str] | None:
    if not isinstance(raw_item, dict):
        return None
    action = str(raw_item.get("action", "")).strip()
    at = str(raw_item.get("at", "")).strip()
    if not action and not at:
        return None
    return {
        "log_id": str(raw_item.get("log_id", "")).strip() or f"log_{uuid.uuid4().hex}",
        "at": at or utc_now_iso(),
        "action": action,
        "operator": str(raw_item.get("operator", "")).strip(),
        "detail": str(raw_item.get("detail", "")).strip(),
    }


def _append_job_log(job: dict[str, Any], *, action: str, operator: str, detail: str = "") -> None:
    logs = job.get("logs")
    if not isinstance(logs, list):
        logs = []
    logs.append(
        {
            "log_id": f"log_{uuid.uuid4().hex}",
            "at": utc_now_iso(),
            "action": str(action or "").strip(),
            "operator": str(operator or "").strip(),
            "detail": str(detail or "").strip(),
        }
    )
    job["logs"] = logs[-300:]


def _normalize_job_payload(raw_item: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    now = utc_now_iso()
    existing = existing or {}

    raw_id = str(raw_item.get("job_id", "")).strip()
    job_id = raw_id or str(existing.get("job_id", "")).strip() or f"job_{uuid.uuid4().hex}"
    job_code = str(raw_item.get("job_code", "")).strip() or str(existing.get("job_code", "")).strip()
    title = str(raw_item.get("title", "")).strip()
    department = normalize_department_scope(str(raw_item.get("department", "")).strip())
    location = str(raw_item.get("location", "")).strip()
    recruiter_user_id = str(raw_item.get("recruiter_user_id", "")).strip()
    hiring_manager_user_id = str(raw_item.get("hiring_manager_user_id", "")).strip()
    jd = str(raw_item.get("jd", "")).strip()
    requirements = str(raw_item.get("requirements", "")).strip()
    try:
        headcount = int(raw_item.get("headcount", 1) or 1)
    except (TypeError, ValueError):
        headcount = 1
    headcount = max(headcount, 1)
    raw_status = str(raw_item.get("status", "")).strip().lower()
    status = raw_status if raw_status in JOB_STATUS_VALUES else str(existing.get("status", JOB_STATUS_OPEN))
    if status not in JOB_STATUS_VALUES:
        status = JOB_STATUS_OPEN

    process_raw = raw_item.get("process")
    process = process_raw if isinstance(process_raw, dict) else {}
    process = {stage: str(process.get(stage, "")).strip() for stage in INTERVIEW_STAGES}
    criteria_raw = raw_item.get("criteria")
    criteria_input = criteria_raw if isinstance(criteria_raw, dict) else {}
    criteria = {
        "education": str(criteria_input.get("education", "")).strip(),
        "major": str(criteria_input.get("major", "")).strip(),
        "skills": str(criteria_input.get("skills", "")).strip(),
        "project_experience": str(criteria_input.get("project_experience", "")).strip(),
    }

    templates_raw = raw_item.get("templates")
    templates = [_normalize_job_template_item(item) for item in templates_raw] if isinstance(templates_raw, list) else []
    templates = [item for item in templates if item is not None]
    templates.sort(key=lambda item: int(item["version_no"]))

    try:
        active_template_version = int(raw_item.get("active_template_version", 0) or 0)
    except (TypeError, ValueError):
        active_template_version = 0
    available_versions = {int(item["version_no"]) for item in templates}
    if active_template_version not in available_versions:
        active_template_version = max(available_versions) if available_versions else 0

    active_template = next((item for item in templates if int(item["version_no"]) == int(active_template_version)), None)
    active_template_path = str((active_template or {}).get("storage_rel_path", "")).strip()
    raw_storage_path = str(raw_item.get("score_table_storage_rel_path", "")).strip()
    score_table_storage_rel_path = active_template_path or raw_storage_path

    logs_raw = raw_item.get("logs")
    logs = [_normalize_job_log_item(item) for item in logs_raw] if isinstance(logs_raw, list) else []
    logs = [item for item in logs if item is not None][-300:]

    created_at = str(raw_item.get("created_at", "")).strip() or str(existing.get("created_at", "")).strip() or now
    updated_at = str(raw_item.get("updated_at", "")).strip() or now
    closed_at = str(raw_item.get("closed_at", "")).strip() or str(existing.get("closed_at", "")).strip()
    if status == JOB_STATUS_CLOSED and not closed_at:
        closed_at = now
    if status == JOB_STATUS_OPEN:
        closed_at = ""

    return {
        "job_id": job_id,
        "job_code": job_code,
        "title": title,
        "department": department,
        "headcount": headcount,
        "location": location,
        "recruiter_user_id": recruiter_user_id,
        "hiring_manager_user_id": hiring_manager_user_id,
        "jd": jd,
        "requirements": requirements,
        "process": process,
        "criteria": criteria,
        "templates": templates,
        "active_template_version": active_template_version,
        "score_table_storage_rel_path": score_table_storage_rel_path,
        "auto_score_enabled": bool(raw_item.get("auto_score_enabled", False)),
        "status": status,
        "logs": logs,
        "created_at": created_at,
        "updated_at": updated_at,
        "closed_at": closed_at,
    }


def _row_to_job_dict(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    process = _json_loads_or_empty_object(str(row[10] or ""))
    criteria = _json_loads_or_empty_object(str(row[11] or ""))
    templates = _json_loads_or_empty_list(str(row[12] or "[]"))
    logs = _json_loads_or_empty_list(str(row[17] or "[]"))
    return _normalize_job_payload(
        {
            "job_id": row[0] or "",
            "job_code": row[1] or "",
            "title": row[2] or "",
            "department": row[3] or "",
            "headcount": int(row[4] or 1),
            "location": row[5] or "",
            "recruiter_user_id": row[6] or "",
            "hiring_manager_user_id": row[7] or "",
            "jd": row[8] or "",
            "requirements": row[9] or "",
            "process": process,
            "criteria": criteria,
            "templates": templates,
            "active_template_version": int(row[13] or 0),
            "score_table_storage_rel_path": row[14] or "",
            "auto_score_enabled": int(row[15] or 0) == 1,
            "status": row[16] or JOB_STATUS_OPEN,
            "logs": logs,
            "created_at": row[18] or "",
            "updated_at": row[19] or "",
            "closed_at": row[20] or "",
        }
    )


def _upsert_job(conn: sqlite3.Connection, item: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO jobs (
            job_id, job_code, title, department, headcount, location,
            recruiter_user_id, hiring_manager_user_id, jd, requirements,
            process_json, criteria_json, templates_json, active_template_version,
            score_table_storage_rel_path, auto_score_enabled, status, logs_json,
            created_at, updated_at, closed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            job_code = excluded.job_code,
            title = excluded.title,
            department = excluded.department,
            headcount = excluded.headcount,
            location = excluded.location,
            recruiter_user_id = excluded.recruiter_user_id,
            hiring_manager_user_id = excluded.hiring_manager_user_id,
            jd = excluded.jd,
            requirements = excluded.requirements,
            process_json = excluded.process_json,
            criteria_json = excluded.criteria_json,
            templates_json = excluded.templates_json,
            active_template_version = excluded.active_template_version,
            score_table_storage_rel_path = excluded.score_table_storage_rel_path,
            auto_score_enabled = excluded.auto_score_enabled,
            status = excluded.status,
            logs_json = excluded.logs_json,
            updated_at = excluded.updated_at,
            closed_at = excluded.closed_at
        """,
        (
            item["job_id"],
            item["job_code"],
            item["title"],
            item["department"],
            int(item["headcount"]),
            item["location"],
            item["recruiter_user_id"],
            item["hiring_manager_user_id"],
            item["jd"],
            item["requirements"],
            _json_dumps_compact(item["process"], "{}"),
            _json_dumps_compact(item["criteria"], "{}"),
            _json_dumps_compact(item["templates"], "[]"),
            int(item["active_template_version"]),
            item["score_table_storage_rel_path"],
            1 if bool(item["auto_score_enabled"]) else 0,
            item["status"],
            _json_dumps_compact(item["logs"], "[]"),
            item["created_at"],
            item["updated_at"],
            item["closed_at"],
        ),
    )


def _load_job_by_id(conn: sqlite3.Connection, job_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT job_id, job_code, title, department, headcount, location,
               recruiter_user_id, hiring_manager_user_id, jd, requirements,
               process_json, criteria_json, templates_json, active_template_version,
               score_table_storage_rel_path, auto_score_enabled, status, logs_json,
               created_at, updated_at, closed_at
        FROM jobs
        WHERE job_id = ?
        """,
        (job_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_job_dict(row)


def list_jobs_for_user(user: dict[str, Any] | None) -> list[dict[str, Any]]:
    with connect_db(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT job_id, job_code, title, department, headcount, location,
                   recruiter_user_id, hiring_manager_user_id, jd, requirements,
                   process_json, criteria_json, templates_json, active_template_version,
                   score_table_storage_rel_path, auto_score_enabled, status, logs_json,
                   created_at, updated_at, closed_at
            FROM jobs
            ORDER BY datetime(updated_at) DESC, datetime(created_at) DESC
            """
        ).fetchall()
    items = [_row_to_job_dict(row) for row in rows]
    role_code = user_role_code(user)
    if role_code == ROLE_HIRING_MANAGER:
        scope = user_department_scope(user)
        if not scope:
            return []
        return [item for item in items if normalize_department_scope(str(item.get("department", ""))) == scope]
    return items


def replace_jobs_from_client(items: list[Any]) -> list[dict[str, Any]]:
    normalized_items: list[dict[str, Any]] = []
    with connect_db(DB_PATH) as conn:
        for raw in items:
            if not isinstance(raw, dict):
                continue
            existing = _load_job_by_id(conn, str(raw.get("job_id", "")).strip()) if raw.get("job_id") else None
            normalized = _normalize_job_payload(raw, existing=existing)
            _upsert_job(conn, normalized)
            normalized_items.append(normalized)
        conn.commit()
    return normalized_items


def upload_job_score_table(
    *,
    job_id: str,
    filename: str,
    content: bytes,
    uploaded_by: str,
    operator_name: str,
) -> dict[str, Any]:
    normalized_job_id = str(job_id or "").strip()
    if not normalized_job_id:
        raise ValueError("job_id 不能为空")
    safe_filename = sanitize_score_template_filename(filename)
    if len(content or b"") <= 0:
        raise ValueError("评分表文件不能为空")
    if len(content or b"") > MAX_JOB_TEMPLATE_BYTES:
        raise ValueError("评分表文件过大（最大 8MB）")

    preview = parse_score_table_preview(content, safe_filename)

    job_dir = (JOB_TEMPLATE_ROOT_DIR / normalized_job_id).resolve()
    root = JOB_TEMPLATE_ROOT_DIR.resolve()
    try:
        job_dir.relative_to(root)
    except ValueError:
        raise ValueError("非法岗位路径")
    job_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{time_today_date_tag()}_{uuid.uuid4().hex[:8]}_{safe_filename}"
    target_path = (job_dir / stored_filename).resolve()
    try:
        target_path.relative_to(root)
    except ValueError:
        raise ValueError("非法评分表存储路径")
    target_path.write_bytes(content)
    storage_rel_path = target_path.relative_to(JOB_TEMPLATE_ROOT_DIR).as_posix()

    with connect_db(DB_PATH) as conn:
        existing = _load_job_by_id(conn, normalized_job_id)
        if existing is None:
            raise ValueError("job not found")
        templates = existing.get("templates")
        templates_list = templates if isinstance(templates, list) else []
        max_version = max(
            (int(item.get("version_no", 0) or 0) for item in templates_list if isinstance(item, dict)),
            default=0,
        )
        version_no = max_version + 1
        template_item = {
            "template_id": f"tpl_{uuid.uuid4().hex}",
            "version_no": version_no,
            "filename": safe_filename,
            "size": len(content or b""),
            "uploaded_at": utc_now_iso(),
            "uploaded_by": str(uploaded_by or "").strip(),
            "storage_rel_path": storage_rel_path,
            "preview": preview,
            "dimensions": preview.get("dimensions", []),
        }
        templates_list = templates_list + [template_item]
        existing["templates"] = templates_list
        if int(existing.get("active_template_version", 0) or 0) <= 0:
            existing["active_template_version"] = version_no
            existing["score_table_storage_rel_path"] = storage_rel_path
        else:
            active_version = int(existing.get("active_template_version", 0) or 0)
            active_template = next(
                (item for item in templates_list if int(item.get("version_no", 0) or 0) == active_version),
                None,
            )
            existing["score_table_storage_rel_path"] = str((active_template or {}).get("storage_rel_path", "")).strip()
        existing["updated_at"] = utc_now_iso()
        _append_job_log(existing, action="评分表上传", operator=operator_name, detail=f"上传 V{version_no}：{safe_filename}")
        normalized = _normalize_job_payload(existing, existing=existing)
        _upsert_job(conn, normalized)
        conn.commit()
        return normalized


def _delete_job_template_file(storage_rel_path: str) -> None:
    file_path = _resolve_job_template_path(storage_rel_path)
    if file_path is None:
        return

    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        return

    template_root = JOB_TEMPLATE_ROOT_DIR.resolve()
    parent = file_path.parent
    if parent == template_root:
        return
    try:
        parent.relative_to(template_root)
        if not any(parent.iterdir()):
            parent.rmdir()
    except (ValueError, OSError):
        return


def delete_job_score_table_version(
    *,
    job_id: str,
    version_no: str,
    operator_name: str,
) -> dict[str, Any]:
    normalized_job_id = str(job_id or "").strip()
    if not normalized_job_id:
        raise ValueError("job_id 不能为空")
    try:
        normalized_version_no = int(str(version_no or "").strip())
    except (TypeError, ValueError):
        normalized_version_no = 0
    if normalized_version_no <= 0:
        raise ValueError("version_no 非法")

    removed_storage_rel_path = ""
    removed_filename = ""
    with connect_db(DB_PATH) as conn:
        existing = _load_job_by_id(conn, normalized_job_id)
        if existing is None:
            raise ValueError("job not found")

        templates = existing.get("templates")
        templates_list = templates if isinstance(templates, list) else []
        target_template = next(
            (item for item in templates_list if int(item.get("version_no", 0) or 0) == normalized_version_no),
            None,
        )
        if not isinstance(target_template, dict):
            raise ValueError("template version not found")

        removed_storage_rel_path = str(target_template.get("storage_rel_path", "")).strip()
        removed_filename = str(target_template.get("filename", "")).strip()
        remaining_templates = [
            item for item in templates_list if int(item.get("version_no", 0) or 0) != normalized_version_no
        ]
        available_versions = [int(item.get("version_no", 0) or 0) for item in remaining_templates if isinstance(item, dict)]
        available_versions = [value for value in available_versions if value > 0]

        previous_active_version = int(existing.get("active_template_version", 0) or 0)
        if previous_active_version == normalized_version_no:
            next_active_version = max(available_versions) if available_versions else 0
        elif previous_active_version in available_versions:
            next_active_version = previous_active_version
        else:
            next_active_version = max(available_versions) if available_versions else 0

        next_active_template = next(
            (item for item in remaining_templates if int(item.get("version_no", 0) or 0) == next_active_version),
            None,
        )
        existing["templates"] = remaining_templates
        existing["active_template_version"] = next_active_version
        existing["score_table_storage_rel_path"] = str((next_active_template or {}).get("storage_rel_path", "")).strip()
        if next_active_version <= 0:
            existing["auto_score_enabled"] = False

        detail = f"删除 V{normalized_version_no}：{removed_filename or '未命名文件'}"
        if previous_active_version == normalized_version_no:
            if next_active_version > 0:
                detail = f"{detail}；生效版本切换到 V{next_active_version}"
            else:
                detail = f"{detail}；当前无生效版本，已关闭自动评分"
        _append_job_log(existing, action="评分表版本删除", operator=operator_name, detail=detail)
        existing["updated_at"] = utc_now_iso()

        normalized = _normalize_job_payload(existing, existing=existing)
        _upsert_job(conn, normalized)
        conn.commit()

    if removed_storage_rel_path:
        _delete_job_template_file(removed_storage_rel_path)
    return normalized


def get_job_score_table_preview(job_id: str) -> dict[str, Any]:
    normalized_job_id = str(job_id or "").strip()
    if not normalized_job_id:
        raise ValueError("job_id 不能为空")
    with connect_db(DB_PATH) as conn:
        item = _load_job_by_id(conn, normalized_job_id)
    if item is None:
        raise ValueError("job not found")
    active_version = int(item.get("active_template_version", 0) or 0)
    templates = item.get("templates")
    templates_list = templates if isinstance(templates, list) else []
    active_template = next((tpl for tpl in templates_list if int(tpl.get("version_no", 0) or 0) == active_version), None)
    preview = active_template.get("preview") if isinstance(active_template, dict) else None
    return {
        "job_id": item.get("job_id", ""),
        "active_template_version": active_version,
        "score_table_storage_rel_path": str(item.get("score_table_storage_rel_path", "") or ""),
        "template": active_template if isinstance(active_template, dict) else None,
        "preview": (
            preview
            if isinstance(preview, dict)
            else {"headers": [], "rows": [], "dimensions": [], "note": "暂无评分表预览"}
        ),
    }

