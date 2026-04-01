from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote


def _candidate_service():
    from ..services import candidate_service

    return candidate_service


def list_candidate_file_rows(
    conn: sqlite3.Connection,
    *,
    include_inactive: bool = False,
) -> list[dict[str, Any]]:
    candidate_service = _candidate_service()
    where_sql = "" if include_inactive else "WHERE is_active = 1"
    rows = conn.execute(
        f"""
        SELECT candidate_id, candidate_name, original_filename, storage_rel_path,
               inflow_date, resume_parsed_text, resume_parser_payload_json, resume_parser_updated_at,
               uploaded_at, uploaded_by, is_active
        FROM candidate_files
        {where_sql}
        ORDER BY uploaded_at ASC
        """
    ).fetchall()
    return [
        {
            "candidate_id": row[0],
            "candidate_name": row[1],
            "original_filename": row[2],
            "storage_rel_path": row[3],
            "inflow_date": candidate_service.normalize_date_tag(row[4] or "")
            or candidate_service.infer_inflow_date_from_rel_path(row[3] or ""),
            "resume_parsed_text": row[5] or "",
            "resume_parser_payload_json": row[6] or "",
            "resume_parser_updated_at": row[7] or "",
            "uploaded_at": row[8],
            "uploaded_by": row[9],
            "is_active": int(row[10] or 0),
        }
        for row in rows
    ]


def get_candidate_file_by_id(conn: sqlite3.Connection, candidate_id: str) -> dict[str, Any] | None:
    candidate_service = _candidate_service()
    row = conn.execute(
        """
        SELECT candidate_id, candidate_name, original_filename, storage_rel_path,
               inflow_date, resume_parsed_text, resume_parser_payload_json, resume_parser_updated_at,
               uploaded_at, uploaded_by, is_active
        FROM candidate_files
        WHERE candidate_id = ?
        """,
        (candidate_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "candidate_id": row[0],
        "candidate_name": row[1],
        "original_filename": row[2],
        "storage_rel_path": row[3],
        "inflow_date": candidate_service.normalize_date_tag(row[4] or "")
        or candidate_service.infer_inflow_date_from_rel_path(row[3] or ""),
        "resume_parsed_text": row[5] or "",
        "resume_parser_payload_json": row[6] or "",
        "resume_parser_updated_at": row[7] or "",
        "uploaded_at": row[8],
        "uploaded_by": row[9],
        "is_active": int(row[10] or 0),
    }


def get_candidate_file_by_original_filename(
    conn: sqlite3.Connection,
    original_filename: str,
) -> dict[str, Any] | None:
    candidate_service = _candidate_service()
    row = conn.execute(
        """
        SELECT candidate_id, candidate_name, original_filename, storage_rel_path,
               inflow_date, resume_parsed_text, resume_parser_payload_json, resume_parser_updated_at,
               uploaded_at, uploaded_by, is_active
        FROM candidate_files
        WHERE original_filename = ? COLLATE NOCASE
        """,
        (original_filename,),
    ).fetchone()
    if row is None:
        return None
    return {
        "candidate_id": row[0],
        "candidate_name": row[1],
        "original_filename": row[2],
        "storage_rel_path": row[3],
        "inflow_date": candidate_service.normalize_date_tag(row[4] or "")
        or candidate_service.infer_inflow_date_from_rel_path(row[3] or ""),
        "resume_parsed_text": row[5] or "",
        "resume_parser_payload_json": row[6] or "",
        "resume_parser_updated_at": row[7] or "",
        "uploaded_at": row[8],
        "uploaded_by": row[9],
        "is_active": int(row[10] or 0),
    }


def parse_education(stem: str) -> str:
    match = re.search(r"(博士|硕士|本科|专科)", stem)
    return match.group(1) if match else "未知"


def parse_school(stem: str) -> str:
    _ = stem
    return "未知"


def parse_candidate_from_filename(
    filename: str,
    *,
    candidate_id: str = "",
    candidate_name_override: str = "",
) -> dict[str, Any]:
    candidate_service = _candidate_service()
    stem = Path(filename).stem
    role_match = re.search(r"【([^】]+)】", stem)
    role_raw = role_match.group(1) if role_match else ""
    role = role_raw.split("_")[0] if role_raw else "未知岗位"

    base_guess = "北京"
    if "_" in role_raw:
        tail = role_raw.split("_", 1)[1].strip()
        if tail in candidate_service.BASE_OPTIONS:
            base_guess = tail

    tail_text = stem[role_match.end() :].strip() if role_match else stem
    tail_text = re.split(r"（|\(", tail_text, maxsplit=1)[0].strip()
    name = tail_text.split()[0] if tail_text else stem

    is_fresh = "应届生" in stem
    grad_year_match = re.search(r"(\d{2})年应届生", stem)
    graduation_year = f"20{grad_year_match.group(1)}" if grad_year_match else ""

    work_match = re.search(r"(\d+年(?:以内)?)", stem)
    work_years = "" if is_fresh else (work_match.group(1) if work_match else "")

    hire_type = "实习" if "实习" in role_raw or "实习" in stem else "正式"

    candidate_name = (candidate_name_override or "").strip() or name
    candidate_key = (candidate_id or "").strip() or filename
    return {
        "candidate_id": candidate_key,
        "filename": filename,
        "name": candidate_name,
        "role": role,
        "raw_role": role_raw,
        "base_guess": base_guess,
        "experience_type_guess": "应届生" if is_fresh else "已工作",
        "graduation_year_guess": graduation_year,
        "work_years_guess": work_years,
        "hire_type_guess": hire_type,
        "preset_position_guess": role,
        "highest_education_guess": parse_education(stem),
        "school_name_guess": parse_school(stem),
        "applied_position_guess": role,
        "pdf_url": f"/api/resumes/{quote(candidate_key)}",
    }


def default_profile(candidate: dict[str, Any]) -> dict[str, Any]:
    candidate_service = _candidate_service()
    inferred_scope = candidate_service.infer_department_scope(
        candidate.get("applied_position_guess", ""),
        candidate.get("preset_position_guess", ""),
    )
    return {
        "candidate_id": candidate["candidate_id"],
        "base_location": candidate["base_guess"],
        "salary_mode": "月薪",
        "salary_range": "",
        "experience_type": candidate["experience_type_guess"],
        "graduation_year": candidate["graduation_year_guess"],
        "work_years": candidate["work_years_guess"],
        "hire_type": candidate["hire_type_guess"],
        "preset_position": candidate["preset_position_guess"],
        "highest_education": candidate["highest_education_guess"],
        "school_name": candidate["school_name_guess"],
        "applied_position": candidate["applied_position_guess"],
        "department_scope": inferred_scope,
        "job_ref_id": "",
        "job_id": "",
        "job_code": "",
        "job_title": "",
        "job_snapshot_json": "",
        "resume_structured_json": "{}",
        "resume_extract_status": "",
        "resume_extract_source": "",
        "resume_extract_model": "",
        "resume_extract_error": "",
        "resume_extract_updated_at": "",
        "current_stage": candidate_service.DEFAULT_STAGE,
        "stage_closed_from": "",
        "stage_statuses": candidate_service.stage_status_template(),
        "is_starred": 0,
        "terminated_at": "",
        "updated_at": "",
    }


def default_round(stage: str) -> dict[str, Any]:
    return {
        "stage": stage,
        "interview_time": "",
        "interviewer_user_id": "",
        "interviewer_name": "",
        "interviewer_role_name": "",
        "planned_questions": "",
        "interview_review": "",
        "updated_at": "",
    }


def insert_profile_if_missing(conn: sqlite3.Connection, profile: dict[str, Any]) -> None:
    candidate_service = _candidate_service()
    candidate_service.execute_sql_with_retry(
        conn,
        """
        INSERT OR IGNORE INTO candidate_profiles (
            candidate_id, base_location, salary_mode, salary_range,
            experience_type, graduation_year, work_years, hire_type,
            preset_position, highest_education, school_name, applied_position,
            department_scope, job_ref_id, job_id, job_code, job_title, job_snapshot_json,
            current_stage, stage_closed_from, stage_status_json, is_starred,
            terminated_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            profile["candidate_id"],
            profile["base_location"],
            profile["salary_mode"],
            profile["salary_range"],
            profile["experience_type"],
            profile["graduation_year"],
            profile["work_years"],
            profile["hire_type"],
            profile["preset_position"],
            profile["highest_education"],
            profile["school_name"],
            profile["applied_position"],
            profile.get("department_scope", ""),
            profile.get("job_ref_id", profile.get("job_id", "")),
            profile.get("job_id", ""),
            profile.get("job_code", ""),
            profile.get("job_title", ""),
            profile.get("job_snapshot_json", ""),
            profile["current_stage"],
            profile["stage_closed_from"],
            candidate_service.dump_stage_statuses(profile["stage_statuses"]),
            profile["is_starred"],
            profile["terminated_at"],
            candidate_service.utc_now_iso(),
        ),
    )


def seed_candidate_profiles(conn: sqlite3.Connection) -> None:
    for item in list_candidate_file_rows(conn):
        parsed = parse_candidate_from_filename(
            item["original_filename"],
            candidate_id=item["candidate_id"],
            candidate_name_override=item["candidate_name"],
        )
        profile = default_profile(parsed)
        insert_profile_if_missing(conn, profile)


def profile_summaries(conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    candidate_service = _candidate_service()
    rows = conn.execute(
        """
        SELECT candidate_id, experience_type, graduation_year, work_years,
               highest_education, school_name, current_stage, stage_closed_from,
               stage_status_json, applied_position, department_scope,
               job_ref_id, job_id, job_code, job_title, is_starred, terminated_at
        FROM candidate_profiles
        """
    ).fetchall()

    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        statuses, current_stage, stage_closed_from = candidate_service.decode_stage_statuses(
            row[8] or "",
            row[6] or "",
            row[7] or "",
        )
        out[row[0]] = {
            "experience_type": row[1],
            "graduation_year": row[2],
            "work_years": row[3],
            "highest_education": row[4],
            "school_name": row[5],
            "current_stage": current_stage,
            "stage_closed_from": stage_closed_from,
            "stage_status_json": candidate_service.dump_stage_statuses(statuses),
            "applied_position": row[9],
            "department_scope": candidate_service.normalize_department_scope(row[10] or ""),
            "job_id": row[11] or row[12] or "",
            "job_code": row[13] or "",
            "job_title": row[14] or "",
            "is_starred": int(row[15] or 0),
            "terminated_at": row[16] or "",
        }
    return out


def _build_snapshot_from_linked_job(
    *,
    job_id: str,
    job_code: str,
    job_title: str,
    department_scope: str,
    jd: str,
    requirements: str,
    process_json: str,
    criteria_json: str,
    templates_json: str,
    active_template_version: Any,
    auto_score_enabled: Any,
) -> str:
    candidate_service = _candidate_service()
    templates_raw = candidate_service.json_loads_or_empty_list(str(templates_json or "[]"))
    templates = [candidate_service._normalize_job_template_item(item) for item in templates_raw]
    templates = [item for item in templates if item is not None]
    templates.sort(key=lambda item: int(item["version_no"]))
    try:
        active_version = max(int(active_template_version or 0), 0)
    except (TypeError, ValueError):
        active_version = 0
    available_versions = {int(item["version_no"]) for item in templates}
    if active_version not in available_versions:
        active_version = max(available_versions) if available_versions else 0

    job_payload = {
        "jd": str(jd or "").strip(),
        "requirements": str(requirements or "").strip(),
        "criteria": candidate_service.json_loads_or_empty_object(str(criteria_json or "{}")),
        "process": candidate_service.json_loads_or_empty_object(str(process_json or "{}")),
        "templates": templates,
        "active_template_version": active_version,
        "auto_score_enabled": int(auto_score_enabled or 0) == 1,
    }
    snapshot = candidate_service.build_job_snapshot(
        job_payload=job_payload,
        department_scope=candidate_service.normalize_department_scope(department_scope),
        job_id=str(job_id or "").strip(),
        job_code=str(job_code or "").strip(),
        job_title=str(job_title or "").strip(),
    )
    snapshot["templates"] = templates
    return candidate_service.json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))


def load_profile(conn: sqlite3.Connection, candidate_id: str) -> dict[str, Any] | None:
    candidate_service = _candidate_service()
    row = conn.execute(
        """
        SELECT cp.candidate_id, cp.base_location, cp.salary_mode, cp.salary_range,
               cp.experience_type, cp.graduation_year, cp.work_years, cp.hire_type,
               cp.preset_position, cp.highest_education, cp.school_name, cp.applied_position,
               cp.department_scope, cp.job_ref_id, cp.job_id, cp.job_code, cp.job_title, cp.job_snapshot_json,
               cp.resume_structured_json, cp.resume_extract_status, cp.resume_extract_source,
               cp.resume_extract_model, cp.resume_extract_error, cp.resume_extract_updated_at,
               cp.current_stage, cp.stage_closed_from, cp.stage_status_json, cp.is_starred,
               cp.terminated_at, cp.updated_at,
               j.job_id, j.job_code, j.title, j.department, j.jd, j.requirements,
               j.process_json, j.criteria_json, j.templates_json, j.active_template_version, j.auto_score_enabled
        FROM candidate_profiles cp
        LEFT JOIN jobs j
          ON j.job_id = COALESCE(NULLIF(cp.job_ref_id, ''), NULLIF(cp.job_id, ''))
        WHERE cp.candidate_id = ?
        """,
        (candidate_id,),
    ).fetchone()

    if row is None:
        return None

    linked_job_id = str(row[30] or "").strip()
    bound_job_id = str(row[13] or "").strip() or str(row[14] or "").strip()
    job_id = linked_job_id or bound_job_id
    job_code = str(row[31] or "").strip() or str(row[15] or "").strip()
    job_title = str(row[32] or "").strip() or str(row[16] or "").strip()
    job_snapshot_json = str(row[17] or "").strip()
    if linked_job_id:
        job_snapshot_json = _build_snapshot_from_linked_job(
            job_id=linked_job_id,
            job_code=job_code,
            job_title=job_title,
            department_scope=str(row[12] or ""),
            jd=str(row[34] or ""),
            requirements=str(row[35] or ""),
            process_json=str(row[36] or "{}"),
            criteria_json=str(row[37] or "{}"),
            templates_json=str(row[38] or "[]"),
            active_template_version=row[39] or 0,
            auto_score_enabled=row[40] or 0,
        )
    resume_structured_json = str(row[18] or "").strip()
    resume_structured = candidate_service.json_loads_or_empty_object(resume_structured_json)

    statuses, current_stage, stage_closed_from = candidate_service.decode_stage_statuses(
        row[26] or "",
        row[24] or "",
        row[25] or "",
    )
    interview_status = candidate_service.derive_interview_status(current_stage, stage_closed_from, statuses)

    return {
        "candidate_id": row[0],
        "base_location": row[1],
        "salary_mode": row[2],
        "salary_range": row[3],
        "experience_type": row[4],
        "graduation_year": row[5],
        "work_years": row[6],
        "hire_type": row[7],
        "preset_position": row[8],
        "highest_education": row[9],
        "school_name": row[10],
        "applied_position": row[11],
        "department_scope": candidate_service.normalize_department_scope(row[12] or ""),
        "job_id": job_id,
        "job_code": job_code,
        "job_title": job_title,
        "job_snapshot_json": job_snapshot_json,
        "resume_structured_json": resume_structured_json,
        "resume_structured": resume_structured,
        "resume_extract_status": str(row[19] or "").strip(),
        "resume_extract_source": str(row[20] or "").strip(),
        "resume_extract_model": str(row[21] or "").strip(),
        "resume_extract_error": str(row[22] or "").strip(),
        "resume_extract_updated_at": str(row[23] or "").strip(),
        "current_stage": current_stage,
        "stage_closed_from": stage_closed_from,
        "stage_statuses": statuses,
        "interview_status": interview_status,
        "is_starred": int(row[27] or 0),
        "terminated_at": row[28] or "",
        "updated_at": row[29],
    }


def load_rounds(conn: sqlite3.Connection, candidate_id: str) -> dict[str, dict[str, Any]]:
    candidate_service = _candidate_service()
    rows = conn.execute(
        """
        SELECT stage, interview_time, interviewer_user_id,
               planned_questions, interview_review, updated_at
        FROM interview_round_notes
        WHERE candidate_id = ?
        """,
        (candidate_id,),
    ).fetchall()

    user_name_rows = conn.execute(
        "SELECT id, display_name, username, role_code, is_admin FROM users"
    ).fetchall()
    user_display_map = {
        row[0]: (row[1] or row[2] or "") for row in user_name_rows
    }
    user_role_map = {
        row[0]: candidate_service.role_name(
            candidate_service.normalize_role_code(str(row[3] or ""))
            or candidate_service.role_code_from_is_admin(int(row[4] or 0))
        )
        for row in user_name_rows
    }

    rounds = {stage: default_round(stage) for stage in candidate_service.INTERVIEW_STAGES}
    for row in rows:
        stage = candidate_service.normalize_stage_name(row[0])
        if stage not in rounds:
            continue
        interviewer_user_id = row[2] or ""
        rounds[stage] = {
            "stage": stage,
            "interview_time": row[1],
            "interviewer_user_id": interviewer_user_id,
            "interviewer_name": user_display_map.get(interviewer_user_id, ""),
            "interviewer_role_name": user_role_map.get(interviewer_user_id, ""),
            "planned_questions": row[3],
            "interview_review": row[4],
            "updated_at": row[5],
        }
    return rounds


__all__ = [
    "default_profile",
    "default_round",
    "get_candidate_file_by_id",
    "get_candidate_file_by_original_filename",
    "insert_profile_if_missing",
    "list_candidate_file_rows",
    "load_profile",
    "load_rounds",
    "parse_candidate_from_filename",
    "profile_summaries",
    "seed_candidate_profiles",
]
