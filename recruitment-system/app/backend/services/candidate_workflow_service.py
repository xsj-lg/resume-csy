from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..repositories.sqlite_helpers import connect_db
from ..utils.time_utils import utc_now_iso
from .candidate_domain_service import (
    DEFAULT_STAGE,
    INTERVIEW_STAGES,
    STAGE_STATUS_ENDED,
    STAGE_STATUS_PASSED,
    STAGE_STATUS_PENDING,
    current_active_stage,
    decode_stage_statuses,
    derive_interview_status,
    dump_stage_statuses,
    normalize_stage_name,
    stage_index,
    stage_status_template,
    validate_profile_payload,
    validate_round_payload,
    validate_stage_action_payload,
    validate_star_payload,
)
from .role_user_service import (
    ROLE_ADMINISTRATOR,
    ROLE_HIRING_MANAGER,
    ROLE_HR_SPECIALIST,
    ROLE_INTERVIEWER,
    get_user_by_id,
    user_department_scope,
    user_role_code,
)

ROLE_UPLOAD_ALLOWED = {ROLE_ADMINISTRATOR, ROLE_HR_SPECIALIST}
ROLE_DELETE_CANDIDATE_ALLOWED = {ROLE_ADMINISTRATOR, ROLE_HR_SPECIALIST}
ROLE_PROFILE_WRITE_ALLOWED = {ROLE_ADMINISTRATOR, ROLE_HR_SPECIALIST}
HR_ALLOWED_ROUND_STAGES = {"初筛"}
MANAGER_ALLOWED_ROUND_STAGES = {"二面", "HR面"}
MANAGER_DECISION_STAGES = {"二面", "HR面"}


def _candidate_service():
    from . import candidate_service

    return candidate_service


def parse_job_payload(raw_payload: str) -> dict[str, Any]:
    candidate_service = _candidate_service()
    return candidate_service.parse_job_payload(raw_payload)


def parse_candidate_filters(query: str) -> dict[str, str]:
    candidate_service = _candidate_service()
    return candidate_service.parse_candidate_filters(query)


def filter_candidates(
    items: list[dict[str, Any]],
    filters: dict[str, str],
) -> list[dict[str, Any]]:
    candidate_service = _candidate_service()
    return candidate_service.filter_candidates(items, filters)


def list_candidates() -> list[dict[str, Any]]:
    candidate_service = _candidate_service()
    return candidate_service.list_candidates()


def list_interview_calendar() -> list[dict[str, str]]:
    candidate_service = _candidate_service()
    return candidate_service.list_interview_calendar()


def sync_resumes_from_storage() -> dict[str, int]:
    candidate_service = _candidate_service()
    return candidate_service.sync_resumes_from_storage()


def resolve_resume_path(candidate_id: str) -> Path | None:
    candidate_service = _candidate_service()
    return candidate_service.resolve_resume_path(candidate_id)


def delete_candidate(candidate_id: str) -> bool:
    candidate_service = _candidate_service()
    return candidate_service.delete_candidate(candidate_id)


def create_candidate_from_upload(
    *,
    filename: str,
    content: bytes,
    candidate_name: str,
    uploaded_by: str,
    department_scope: str,
    job_id: str,
    job_code: str,
    job_title: str,
    job_payload: dict[str, Any],
) -> dict[str, Any]:
    candidate_service = _candidate_service()
    return candidate_service.create_candidate_from_upload(
        filename=filename,
        content=content,
        candidate_name=candidate_name,
        uploaded_by=uploaded_by,
        department_scope=department_scope,
        job_id=job_id,
        job_code=job_code,
        job_title=job_title,
        job_payload=job_payload,
    )


def visible_candidate_ids_for_user(user: dict[str, Any] | None) -> set[str] | None:
    role_code = user_role_code(user)
    if role_code == ROLE_ADMINISTRATOR:
        return None
    if not user:
        return set()

    user_id = str(user.get("id", "")).strip()
    if not user_id:
        return set()

    candidate_service = _candidate_service()
    with connect_db(candidate_service.DB_PATH) as conn:
        if role_code == ROLE_HR_SPECIALIST:
            rows = conn.execute(
                """
                SELECT candidate_id
                FROM candidate_files
                WHERE is_active = 1 AND uploaded_by = ?
                """,
                (user_id,),
            ).fetchall()
            return {str(row[0]) for row in rows}

        if role_code == ROLE_INTERVIEWER:
            rows = conn.execute(
                """
                SELECT DISTINCT candidate_id
                FROM interview_round_notes
                WHERE interviewer_user_id = ?
                """,
                (user_id,),
            ).fetchall()
            return {str(row[0]) for row in rows}

        if role_code == ROLE_HIRING_MANAGER:
            department_scope = user_department_scope(user)
            if not department_scope:
                return set()
            rows = conn.execute(
                """
                SELECT cp.candidate_id, cp.department_scope, cp.applied_position, cp.preset_position
                FROM candidate_profiles cp
                JOIN candidate_files cf ON cf.candidate_id = cp.candidate_id
                WHERE cf.is_active = 1
                """
            ).fetchall()
            visible_ids: set[str] = set()
            for row in rows:
                candidate_id = str(row[0] or "")
                if not candidate_id:
                    continue
                candidate_scope = normalize_department_scope(str(row[1] or ""))
                if not candidate_scope:
                    candidate_scope = candidate_service.infer_department_scope(str(row[2] or ""), str(row[3] or ""))
                if candidate_scope == department_scope:
                    visible_ids.add(candidate_id)
            return visible_ids

    return set()


def can_access_candidate(user: dict[str, Any] | None, candidate_id: str) -> bool:
    visible_ids = visible_candidate_ids_for_user(user)
    if visible_ids is None:
        return True
    return candidate_id in visible_ids


def list_candidates_for_user(user: dict[str, Any] | None) -> list[dict[str, Any]]:
    candidate_service = _candidate_service()
    return candidate_service.list_candidates_for_user(user)


def list_interview_calendar_for_user(user: dict[str, Any] | None) -> list[dict[str, str]]:
    candidate_service = _candidate_service()
    return candidate_service.list_interview_calendar_for_user(user)


def can_upload_resume(user: dict[str, Any] | None) -> bool:
    return user_role_code(user) in ROLE_UPLOAD_ALLOWED


def can_sync_resumes(user: dict[str, Any] | None) -> bool:
    return user_role_code(user) in ROLE_UPLOAD_ALLOWED


def can_delete_candidate(user: dict[str, Any] | None, candidate_id: str) -> bool:
    role_code = user_role_code(user)
    if role_code not in ROLE_DELETE_CANDIDATE_ALLOWED:
        return False
    return can_access_candidate(user, candidate_id)


def can_write_profile(user: dict[str, Any] | None, candidate_id: str) -> bool:
    role_code = user_role_code(user)
    if role_code not in ROLE_PROFILE_WRITE_ALLOWED:
        return False
    return can_access_candidate(user, candidate_id)


def can_transition_stage(
    user: dict[str, Any] | None,
    candidate_id: str,
    action: str,
) -> tuple[bool, str]:
    candidate_service = _candidate_service()
    role_code = user_role_code(user)
    if not can_access_candidate(user, candidate_id):
        return False, "candidate_forbidden"
    if role_code in {ROLE_ADMINISTRATOR, ROLE_HR_SPECIALIST}:
        return True, ""
    if role_code != ROLE_HIRING_MANAGER:
        return False, "stage_transition_forbidden"

    with connect_db(candidate_service.DB_PATH) as conn:
        profile = candidate_service.load_profile(conn, candidate_id)
    if profile is None:
        return False, "candidate_not_found"
    current_stage = normalize_stage_name(str(profile.get("current_stage", ""))) or DEFAULT_STAGE
    if current_stage not in MANAGER_DECISION_STAGES:
        return False, "manager_stage_forbidden"
    if action == "reset":
        return False, "manager_action_forbidden"
    return True, ""


def can_write_round(
    user: dict[str, Any] | None,
    candidate_id: str,
    stage: str,
) -> tuple[bool, str]:
    candidate_service = _candidate_service()
    role_code = user_role_code(user)
    if not can_access_candidate(user, candidate_id):
        return False, "candidate_forbidden"

    normalized_stage = normalize_stage_name(stage)
    if not normalized_stage:
        return False, "invalid_stage"

    if role_code == ROLE_ADMINISTRATOR:
        return True, ""

    if role_code == ROLE_HR_SPECIALIST:
        if normalized_stage not in HR_ALLOWED_ROUND_STAGES:
            return False, "hr_round_forbidden"
        return True, ""

    if role_code == ROLE_HIRING_MANAGER:
        if normalized_stage not in MANAGER_ALLOWED_ROUND_STAGES:
            return False, "manager_round_forbidden"
        return True, ""

    if role_code != ROLE_INTERVIEWER:
        return False, "round_forbidden"

    user_id = str(user.get("id", "")).strip() if user else ""
    with connect_db(candidate_service.DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT interviewer_user_id
            FROM interview_round_notes
            WHERE candidate_id = ? AND stage = ?
            """,
            (candidate_id, normalized_stage),
        ).fetchone()
    if row is None:
        return False, "interviewer_not_assigned"
    if str(row[0] or "").strip() != user_id:
        return False, "interviewer_not_assigned"
    return True, ""


def get_evaluation(candidate_id: str) -> dict[str, Any] | None:
    candidate_service = _candidate_service()
    candidates = candidate_service.candidate_map()
    if candidate_id not in candidates:
        return None

    with connect_db(candidate_service.DB_PATH) as conn:
        candidate_service.seed_candidate_profiles(conn)
        conn.commit()
        profile = candidate_service.load_profile(conn, candidate_id)
        file_row = candidate_service.get_candidate_file_by_id(conn, candidate_id)
        if (
            profile is not None
            and file_row is not None
            and int(file_row.get("is_active", 0)) == 1
            and not candidate_service.json_loads_or_empty_object(str(profile.get("resume_structured_json", "")).strip())
            and str(profile.get("resume_extract_status", "")).strip() not in {"success", "failed"}
        ):
            file_path = candidate_service.resolve_storage_path(str(file_row.get("storage_rel_path", "")))
            if file_path is not None and file_path.exists():
                try:
                    resume_text = candidate_service.extract_pdf_text(file_path)
                    candidate_service.extract_and_store_resume_profile(
                        conn,
                        candidate_id=candidate_id,
                        filename=str(file_row.get("original_filename", "")).strip(),
                        candidate_name=str(file_row.get("candidate_name", "")).strip(),
                        resume_text=resume_text,
                    )
                    profile = candidate_service.load_profile(conn, candidate_id)
                except Exception as exc:
                    now = utc_now_iso()
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
                            "",
                            f"提取异常: {exc}",
                            now,
                            now,
                            candidate_id,
                        ),
                    )
                    profile = candidate_service.load_profile(conn, candidate_id)
        rounds = candidate_service.load_rounds(conn, candidate_id)
        auto_score = candidate_service.load_auto_score_by_candidate(conn, candidate_id)
        conn.commit()

    if profile is None:
        candidate = candidates.get(candidate_id, {})
        fallback = candidate_service.parse_candidate_from_filename(
            str(candidate.get("filename", "")),
            candidate_id=candidate_id,
            candidate_name_override=str(candidate.get("name", "")),
        )
        profile = candidate_service.default_profile(fallback)
    statuses, current_stage, stage_closed_from = decode_stage_statuses(
        dump_stage_statuses(profile.get("stage_statuses", stage_status_template())),
        profile.get("current_stage", ""),
        profile.get("stage_closed_from", ""),
    )
    profile["stage_statuses"] = statuses
    profile["current_stage"] = current_stage
    profile["stage_closed_from"] = stage_closed_from
    profile["interview_status"] = derive_interview_status(current_stage, stage_closed_from, statuses)
    profile["is_starred"] = int(profile.get("is_starred", 0))
    profile["terminated_at"] = profile.get("terminated_at", "")
    candidate_name = str(candidates.get(candidate_id, {}).get("name", "")).strip()
    profile["candidate_name"] = candidate_name or "未命名候选人"
    job_snapshot = candidate_service.json_loads_or_empty_object(str(profile.get("job_snapshot_json", "")).strip())

    return {
        "candidate_id": candidate_id,
        "profile": profile,
        "rounds": rounds,
        "job_snapshot": job_snapshot,
        "auto_score": auto_score,
    }


def resolve_profile_job_binding(
    *,
    payload: dict[str, Any],
    existing_profile: dict[str, Any] | None,
    department_scope: str,
) -> tuple[str, str, str, str]:
    candidate_service = _candidate_service()
    existing_job_id = str((existing_profile or {}).get("job_id", "") or "").strip()
    existing_job_code = str((existing_profile or {}).get("job_code", "")).strip()
    existing_job_title = str((existing_profile or {}).get("job_title", "")).strip()
    existing_snapshot_json = str((existing_profile or {}).get("job_snapshot_json", "")).strip()

    raw_job_id = str(payload.get("job_id", "")).strip()
    raw_job_code = str(payload.get("job_code", "")).strip()
    raw_job_title = str(payload.get("job_title", "")).strip()
    raw_job_payload_any = payload.get("job_payload")
    if isinstance(raw_job_payload_any, dict):
        raw_job_payload = raw_job_payload_any
    else:
        raw_job_payload_text = str(raw_job_payload_any or "").strip()
        raw_job_payload = parse_job_payload(raw_job_payload_text) if raw_job_payload_text else {}

    has_job_binding_update = bool(raw_job_id or raw_job_code or raw_job_title or raw_job_payload)
    if not has_job_binding_update:
        return existing_job_id, existing_job_code, existing_job_title, existing_snapshot_json

    if not raw_job_id:
        raise ValueError("job_id 不能为空")
    if not raw_job_title:
        raise ValueError("job_title 不能为空")

    snapshot = candidate_service.build_job_snapshot(
        job_payload=raw_job_payload,
        department_scope=department_scope,
        job_id=raw_job_id,
        job_code=raw_job_code,
        job_title=raw_job_title,
    )
    snapshot_json = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
    return raw_job_id, raw_job_code, raw_job_title, snapshot_json


def transition_stage(candidate_id: str, action: str) -> dict[str, Any] | None:
    candidate_service = _candidate_service()
    candidates = candidate_service.candidate_map()
    if candidate_id not in candidates:
        return None

    now = utc_now_iso()
    with connect_db(candidate_service.DB_PATH) as conn:
        candidate_service.seed_candidate_profiles(conn)
        profile = candidate_service.load_profile(conn, candidate_id)
        if profile is None:
            return None

        if action == "reset":
            statuses = stage_status_template()
            new_current = DEFAULT_STAGE
            new_closed_from = ""
            new_terminated_at = ""
        else:
            statuses = dict(profile.get("stage_statuses", stage_status_template()))
            closed_from = profile.get("stage_closed_from", "")
            if closed_from:
                raise ValueError(f"面试已在{closed_from}结束，不能继续流转")

            if all(statuses.get(stage) == STAGE_STATUS_PASSED for stage in INTERVIEW_STAGES):
                raise ValueError("当前候选人流程已通过全部阶段")

            active_stage = current_active_stage(statuses, profile.get("current_stage", DEFAULT_STAGE))
            active_idx = stage_index(active_stage)
            if active_idx < 0:
                active_stage = DEFAULT_STAGE
                active_idx = 0

            if action == "next":
                statuses[active_stage] = STAGE_STATUS_PASSED
                next_stage = ""
                for stage in INTERVIEW_STAGES[active_idx + 1 :]:
                    if statuses.get(stage) == STAGE_STATUS_PENDING:
                        next_stage = stage
                        break
                new_current = next_stage or INTERVIEW_STAGES[-1]
                new_closed_from = ""
                new_terminated_at = ""
            else:
                for stage in INTERVIEW_STAGES[:active_idx]:
                    if statuses.get(stage) == STAGE_STATUS_PENDING:
                        statuses[stage] = STAGE_STATUS_PASSED
                statuses[active_stage] = STAGE_STATUS_ENDED
                for stage in INTERVIEW_STAGES[active_idx + 1 :]:
                    statuses[stage] = STAGE_STATUS_PENDING
                new_current = active_stage
                new_closed_from = active_stage
                new_terminated_at = now

        conn.execute(
            """
            UPDATE candidate_profiles
            SET current_stage = ?, stage_closed_from = ?, stage_status_json = ?,
                terminated_at = ?, updated_at = ?
            WHERE candidate_id = ?
            """,
            (
                new_current,
                new_closed_from,
                dump_stage_statuses(statuses),
                new_terminated_at,
                now,
                candidate_id,
            ),
        )
        conn.commit()

    return get_evaluation(candidate_id)


def save_profile_only(candidate_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    candidate_service = _candidate_service()
    candidates = candidate_service.candidate_map()
    if candidate_id not in candidates:
        return None

    profile, error = validate_profile_payload(payload)
    if profile is None:
        raise ValueError(error)

    now = utc_now_iso()
    with connect_db(candidate_service.DB_PATH) as conn:
        candidate_service.seed_candidate_profiles(conn)
        file_row = candidate_service.get_candidate_file_by_id(conn, candidate_id)
        if file_row is None or int(file_row.get("is_active", 0)) != 1:
            return None
        candidate_name = str(payload.get("candidate_name", "")).strip()
        if not candidate_name:
            candidate_name = str(file_row.get("candidate_name", "")).strip()
        if not candidate_name:
            candidate_name = Path(str(file_row.get("original_filename", "")).strip()).stem
        if not candidate_name:
            candidate_name = "未命名候选人"

        conn.execute(
            """
            UPDATE candidate_files
            SET candidate_name = ?
            WHERE candidate_id = ?
            """,
            (candidate_name, candidate_id),
        )

        existing_profile = candidate_service.load_profile(conn, candidate_id)
        statuses = (
            existing_profile.get("stage_statuses", stage_status_template())
            if existing_profile
            else stage_status_template()
        )
        current_stage = existing_profile.get("current_stage", DEFAULT_STAGE) if existing_profile else DEFAULT_STAGE
        stage_closed_from = existing_profile.get("stage_closed_from", "") if existing_profile else ""
        is_starred = int(existing_profile.get("is_starred", 0)) if existing_profile else 0
        terminated_at = existing_profile.get("terminated_at", "") if existing_profile else ""
        department_scope = profile["department_scope"] or (
            existing_profile.get("department_scope", "") if existing_profile else ""
        )
        if not department_scope:
            department_scope = candidate_service.infer_department_scope(
                profile.get("applied_position", ""),
                profile.get("preset_position", ""),
            )
        job_id, job_code, job_title, job_snapshot_json = resolve_profile_job_binding(
            payload=payload,
            existing_profile=existing_profile,
            department_scope=department_scope,
        )
        job_ref_id = job_id

        conn.execute(
            """
            INSERT INTO candidate_profiles (
                candidate_id, base_location, salary_mode, salary_range,
                experience_type, graduation_year, work_years, hire_type,
                preset_position, highest_education, school_name, applied_position,
                department_scope, job_ref_id, job_id, job_code, job_title, job_snapshot_json,
                current_stage, stage_closed_from, stage_status_json, is_starred,
                terminated_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(candidate_id) DO UPDATE SET
                base_location = excluded.base_location,
                salary_mode = excluded.salary_mode,
                salary_range = excluded.salary_range,
                experience_type = excluded.experience_type,
                graduation_year = excluded.graduation_year,
                work_years = excluded.work_years,
                hire_type = excluded.hire_type,
                preset_position = excluded.preset_position,
                highest_education = excluded.highest_education,
                school_name = excluded.school_name,
                applied_position = excluded.applied_position,
                department_scope = excluded.department_scope,
                job_ref_id = excluded.job_ref_id,
                job_id = excluded.job_id,
                job_code = excluded.job_code,
                job_title = excluded.job_title,
                job_snapshot_json = excluded.job_snapshot_json,
                current_stage = excluded.current_stage,
                stage_closed_from = excluded.stage_closed_from,
                stage_status_json = excluded.stage_status_json,
                is_starred = excluded.is_starred,
                terminated_at = excluded.terminated_at,
                updated_at = excluded.updated_at
            """,
            (
                candidate_id,
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
                department_scope,
                job_ref_id,
                job_id,
                job_code,
                job_title,
                job_snapshot_json,
                current_stage,
                stage_closed_from,
                dump_stage_statuses(statuses),
                is_starred,
                terminated_at,
                now,
            ),
        )
        conn.commit()

    return get_evaluation(candidate_id)


def save_round_only(candidate_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    candidate_service = _candidate_service()
    candidates = candidate_service.candidate_map()
    if candidate_id not in candidates:
        return None

    round_data, error = validate_round_payload(payload)
    if round_data is None:
        raise ValueError(error)

    now = utc_now_iso()
    with connect_db(candidate_service.DB_PATH) as conn:
        candidate_service.seed_candidate_profiles(conn)
        interviewer_user_id = round_data["interviewer_user_id"]
        if interviewer_user_id:
            user = get_user_by_id(conn, interviewer_user_id)
            if user is None or int(user.get("is_active", 0)) != 1:
                raise ValueError("interviewer_user_id 非法或用户不可用")
        conn.execute(
            """
            INSERT INTO interview_round_notes (
                candidate_id, stage, interview_time, interviewer_user_id,
                planned_questions, interview_review, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(candidate_id, stage) DO UPDATE SET
                interview_time = excluded.interview_time,
                interviewer_user_id = excluded.interviewer_user_id,
                planned_questions = excluded.planned_questions,
                interview_review = excluded.interview_review,
                updated_at = excluded.updated_at
            """,
            (
                candidate_id,
                round_data["stage"],
                round_data["interview_time"],
                interviewer_user_id,
                round_data["planned_questions"],
                round_data["interview_review"],
                now,
            ),
        )
        conn.commit()

    return get_evaluation(candidate_id)


def save_star_only(candidate_id: str, is_starred: int) -> dict[str, Any] | None:
    candidate_service = _candidate_service()
    candidates = candidate_service.candidate_map()
    if candidate_id not in candidates:
        return None

    now = utc_now_iso()
    with connect_db(candidate_service.DB_PATH) as conn:
        candidate_service.seed_candidate_profiles(conn)
        conn.execute(
            """
            UPDATE candidate_profiles
            SET is_starred = ?, updated_at = ?
            WHERE candidate_id = ?
            """,
            (1 if is_starred else 0, now, candidate_id),
        )
        conn.commit()

    return get_evaluation(candidate_id)


def save_evaluation(candidate_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    candidate_service = _candidate_service()
    candidates = candidate_service.candidate_map()
    if candidate_id not in candidates:
        return None

    profile_payload = payload.get("profile") or {}
    round_payload = payload.get("round") or {}
    if not profile_payload:
        raise ValueError("profile 不能为空")
    if not round_payload:
        raise ValueError("round 不能为空")

    save_profile_only(candidate_id, profile_payload)
    return save_round_only(candidate_id, round_payload)


__all__ = [
    "parse_job_payload",
    "parse_candidate_filters",
    "filter_candidates",
    "list_candidates",
    "list_candidates_for_user",
    "list_interview_calendar",
    "list_interview_calendar_for_user",
    "get_evaluation",
    "can_access_candidate",
    "can_upload_resume",
    "can_sync_resumes",
    "can_delete_candidate",
    "can_write_profile",
    "can_transition_stage",
    "can_write_round",
    "sync_resumes_from_storage",
    "validate_profile_payload",
    "validate_round_payload",
    "validate_stage_action_payload",
    "validate_star_payload",
    "transition_stage",
    "save_profile_only",
    "save_round_only",
    "save_star_only",
    "save_evaluation",
    "resolve_resume_path",
    "delete_candidate",
    "create_candidate_from_upload",
]
