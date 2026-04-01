from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Any
from urllib.parse import parse_qs

from ..repositories.candidate_repository import (
    list_candidate_file_rows,
    load_rounds,
    parse_candidate_from_filename,
    profile_summaries,
    seed_candidate_profiles,
)
from ..repositories.sqlite_helpers import connect_db
from ..utils.time_utils import utc_now_iso


def _candidate_service():
    from . import candidate_service

    return candidate_service


def _candidate_workflow_service():
    from . import candidate_workflow_service

    return candidate_workflow_service


def calc_duration_tag(experience_type: str, graduation_year: str, work_years: str) -> str:
    if experience_type == "应届生":
        return f"{graduation_year}毕业" if graduation_year else "未知"
    return work_years or "未知"


def list_future_interview_schedule(
    conn,
) -> tuple[dict[str, str], list[dict[str, str]]]:
    candidate_service = _candidate_service()
    rows = conn.execute(
        """
        SELECT candidate_id, stage, interview_time
        FROM interview_round_notes
        """
    ).fetchall()

    nearest_by_candidate: dict[str, tuple[float, str]] = {}
    future_entries: list[tuple[float, str, str, str]] = []
    now_ts = datetime.now().timestamp()
    for row in rows:
        candidate_id = row[0]
        stage = candidate_service.normalize_stage_name(row[1])
        interview_time = (row[2] or "").strip()
        if not candidate_id or not stage or not interview_time:
            continue
        dt = candidate_service.parse_interview_datetime(interview_time)
        if dt is None:
            continue
        ts = dt.timestamp()
        if ts <= now_ts:
            continue

        current_nearest = nearest_by_candidate.get(candidate_id)
        if current_nearest is None or ts < current_nearest[0]:
            nearest_by_candidate[candidate_id] = (ts, interview_time)
        future_entries.append((ts, candidate_id, stage, interview_time))

    future_entries.sort(key=lambda item: item[0])
    nearest_times = {candidate_id: item[1] for candidate_id, item in nearest_by_candidate.items()}
    future_items = [
        {
            "candidate_id": candidate_id,
            "stage": stage,
            "interview_time": interview_time,
            "interview_time_display": candidate_service.format_interview_datetime(interview_time),
        }
        for _, candidate_id, stage, interview_time in future_entries
    ]
    return nearest_times, future_items


def _first_query_value(params: dict[str, list[str]], keys: tuple[str, ...]) -> str:
    for key in keys:
        values = params.get(key, [])
        if values:
            return str(values[0] or "").strip()
    return ""


def _parse_float_bound(value: str) -> float | None:
    try:
        return float(str(value or "").strip())
    except (ValueError, TypeError):
        return None


def _parse_date_bound(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    digits_only = text.replace("-", "").replace("/", "")
    if len(digits_only) == 8 and digits_only.isdigit():
        try:
            return datetime.strptime(digits_only, "%Y%m%d").date()
        except ValueError:
            pass
    normalized = text.replace(" ", "T")
    if len(normalized) == 10 and normalized.count("-") == 2:
        try:
            return datetime.strptime(normalized, "%Y-%m-%d").date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        try:
            return datetime.fromisoformat(normalized[:19]).date()
        except ValueError:
            return None


def _has_upload_date_filters(filters: dict[str, str]) -> bool:
    return any(
        str(filters.get(key, "")).strip()
        for key in ("upload_date", "upload_date_from", "upload_date_to")
    )


def _log_upload_date_filter_debug(
    filters: dict[str, str],
    *,
    upload_exact: date | None,
    upload_from: date | None,
    upload_to: date | None,
    input_count: int,
    output_count: int,
    invalid_inflow_count: int,
    invalid_inflow_examples: list[str],
) -> None:
    if not _has_upload_date_filters(filters):
        return
    raw_exact = str(filters.get("upload_date", "")).strip()
    raw_from = str(filters.get("upload_date_from", "")).strip()
    raw_to = str(filters.get("upload_date_to", "")).strip()
    print(
        "[candidate date filter] "
        f"raw_exact='{raw_exact}' raw_from='{raw_from}' raw_to='{raw_to}' "
        f"parsed_exact='{upload_exact.isoformat() if upload_exact else ''}' "
        f"parsed_from='{upload_from.isoformat() if upload_from else ''}' "
        f"parsed_to='{upload_to.isoformat() if upload_to else ''}' "
        f"input_count={input_count} output_count={output_count} "
        f"invalid_inflow_count={invalid_inflow_count} "
        f"invalid_inflow_examples={invalid_inflow_examples}"
    )


def parse_candidate_filters(query: str) -> dict[str, str]:
    candidate_service = _candidate_service()
    params = parse_qs(query, keep_blank_values=True)
    name_keyword = _first_query_value(params, ("candidate_name", "name"))
    position_keyword = _first_query_value(params, ("applied_position", "position", "role"))
    department_scope = candidate_service.normalize_department_scope(
        _first_query_value(params, ("department_scope", "department", "departmentScope"))
    )
    position_exact = _first_query_value(
        params,
        ("applied_position_exact", "position_exact", "role_exact"),
    )
    position_match = _first_query_value(
        params,
        ("applied_position_match", "position_match", "role_match"),
    ).lower()

    if position_exact:
        position_keyword = position_exact
        position_match = "exact"
    elif position_match not in {"exact", "fuzzy"}:
        position_match = "fuzzy"

    stage_status = _first_query_value(
        params,
        ("stage_status", "status", "interview_status"),
    )
    school = _first_query_value(params, ("school", "school_tag"))
    education = _first_query_value(params, ("education", "education_tag"))
    upload_date = _first_query_value(params, ("upload_date",))
    upload_date_from = _first_query_value(
        params,
        ("uploaded_from", "upload_date_from", "inflow_date_from"),
    )
    upload_date_to = _first_query_value(
        params,
        ("uploaded_to", "upload_date_to", "inflow_date_to"),
    )
    duration = _first_query_value(params, ("duration", "work_years", "duration_tag"))
    score_min = _first_query_value(params, ("score_min", "scoreFrom"))
    score_max = _first_query_value(params, ("score_max", "scoreTo"))

    return {
        "candidate_name": name_keyword,
        "applied_position": position_keyword,
        "position_match": position_match,
        "department_scope": department_scope,
        "stage_status": stage_status,
        "school": school,
        "education": education,
        "duration": duration,
        "score_min": score_min,
        "score_max": score_max,
        "upload_date_from": upload_date_from,
        "upload_date_to": upload_date_to,
        "upload_date": upload_date,
    }


def normalize_filter_text(value: str) -> str:
    return " ".join((value or "").strip().split()).casefold()


def filter_candidates(
    items: list[dict[str, Any]],
    filters: dict[str, str],
) -> list[dict[str, Any]]:
    candidate_service = _candidate_service()
    name_keyword = normalize_filter_text(filters.get("candidate_name", ""))
    position_keyword = normalize_filter_text(filters.get("applied_position", ""))
    department_scope = candidate_service.normalize_department_scope(filters.get("department_scope", ""))
    position_match = filters.get("position_match", "fuzzy")
    if position_match not in {"exact", "fuzzy"}:
        position_match = "fuzzy"
    stage_status_filter = normalize_filter_text(filters.get("stage_status", ""))
    school_filter = normalize_filter_text(filters.get("school", ""))
    education_filter = normalize_filter_text(filters.get("education", ""))
    duration_filter = normalize_filter_text(filters.get("duration", ""))
    score_min = _parse_float_bound(filters.get("score_min", ""))
    score_max = _parse_float_bound(filters.get("score_max", ""))
    upload_exact = _parse_date_bound(filters.get("upload_date", ""))
    upload_from = _parse_date_bound(filters.get("upload_date_from", ""))
    upload_to = _parse_date_bound(filters.get("upload_date_to", ""))
    if upload_exact:
        upload_from = upload_exact
        upload_to = upload_exact
    has_upload_filters = _has_upload_date_filters(filters)

    if (
        not name_keyword
        and not position_keyword
        and not department_scope
        and not stage_status_filter
        and not school_filter
        and not education_filter
        and not duration_filter
        and score_min is None
        and score_max is None
        and upload_from is None
        and upload_to is None
    ):
        return items

    filtered: list[dict[str, Any]] = []
    invalid_inflow_count = 0
    invalid_inflow_examples: list[str] = []
    for item in items:
        candidate_name = normalize_filter_text(str(item.get("name", "")))
        if name_keyword and name_keyword not in candidate_name:
            continue

        if position_keyword:
            position_values = [
                normalize_filter_text(str(item.get("applied_position", ""))),
                normalize_filter_text(str(item.get("role", ""))),
            ]
            if position_match == "exact":
                matched = any(value and value == position_keyword for value in position_values)
            else:
                matched = any(value and position_keyword in value for value in position_values)
            if not matched:
                continue

        if department_scope:
            item_scope = candidate_service.normalize_department_scope(str(item.get("department_scope", "")))
            if item_scope != department_scope:
                continue

        if stage_status_filter:
            stage_value = normalize_filter_text(str(item.get("interview_status", "")))
            if stage_status_filter not in stage_value:
                continue

        if school_filter:
            school_value = normalize_filter_text(str(item.get("school_tag", "")))
            if school_filter not in school_value:
                continue

        if education_filter:
            education_value = normalize_filter_text(str(item.get("education_tag", "")))
            if education_filter not in education_value:
                continue

        if duration_filter:
            duration_value = normalize_filter_text(str(item.get("duration_tag", "")))
            if duration_filter not in duration_value:
                continue

        total_score = item.get("score_total")
        if score_min is not None and (total_score is None or total_score < score_min):
            continue
        if score_max is not None and (total_score is None or total_score > score_max):
            continue

        if upload_from or upload_to:
            inflow_date = _parse_date_bound(str(item.get("inflow_date", "")))
            if inflow_date is None:
                invalid_inflow_count += 1
                raw_inflow_date = str(item.get("inflow_date", "")).strip()
                if raw_inflow_date and raw_inflow_date not in invalid_inflow_examples:
                    invalid_inflow_examples.append(raw_inflow_date)
                    invalid_inflow_examples = invalid_inflow_examples[:5]
                continue
            if upload_from and inflow_date < upload_from:
                continue
            if upload_to and inflow_date > upload_to:
                continue

        filtered.append(item)

    if has_upload_filters:
        _log_upload_date_filter_debug(
            filters,
            upload_exact=upload_exact,
            upload_from=upload_from,
            upload_to=upload_to,
            input_count=len(items),
            output_count=len(filtered),
            invalid_inflow_count=invalid_inflow_count,
            invalid_inflow_examples=invalid_inflow_examples,
        )
    return filtered


def list_candidates() -> list[dict[str, Any]]:
    candidate_service = _candidate_service()
    auto_score_map: dict[str, dict[str, Any]] = {}
    with connect_db(candidate_service.DB_PATH) as conn:
        seed_candidate_profiles(conn)
        file_rows = list_candidate_file_rows(conn)
        summaries = profile_summaries(conn)
        nearest_times, _ = list_future_interview_schedule(conn)
        score_rows = conn.execute(
            """
            SELECT candidate_id, total_score, max_score, match_level
            FROM candidate_auto_scores
            ORDER BY candidate_id, created_at DESC
            """
        ).fetchall()
        conn.commit()

    for row in score_rows:
        candidate_id = str(row[0] or "").strip()
        if not candidate_id or candidate_id in auto_score_map:
            continue
        auto_score_map[candidate_id] = {
            "total_score": row[1],
            "max_score": row[2],
            "match_level": str(row[3] or "").strip(),
        }

    items: list[dict[str, Any]] = []
    for file_row in file_rows:
        parsed = parse_candidate_from_filename(
            file_row["original_filename"],
            candidate_id=file_row["candidate_id"],
            candidate_name_override=file_row["candidate_name"],
        )
        summary = summaries.get(parsed["candidate_id"], {})

        experience_type = summary.get("experience_type") or parsed["experience_type_guess"]
        graduation_year = summary.get("graduation_year") or parsed["graduation_year_guess"]
        work_years = summary.get("work_years") or parsed["work_years_guess"]
        highest_education = summary.get("highest_education") or parsed["highest_education_guess"]
        school_name = summary.get("school_name") or parsed["school_name_guess"]
        current_stage = summary.get("current_stage") or candidate_service.DEFAULT_STAGE
        stage_closed_from = summary.get("stage_closed_from") or ""
        statuses, current_stage, stage_closed_from = candidate_service.decode_stage_statuses(
            summary.get("stage_status_json") or "",
            current_stage,
            stage_closed_from,
        )
        applied_position = summary.get("applied_position") or parsed["applied_position_guess"]
        department_scope = candidate_service.normalize_department_scope(summary.get("department_scope", ""))
        if not department_scope:
            department_scope = candidate_service.infer_department_scope(applied_position, parsed["role"])
        job_id = str(summary.get("job_id", "") or "")
        job_code = str(summary.get("job_code", "") or "")
        job_title = str(summary.get("job_title", "") or "")
        applied_position_text = (
            f"申请岗位:{job_title}（{job_code}）"
            if job_title and job_code
            else (f"申请岗位:{job_title}" if job_title else f"申请岗位:{applied_position or '未知'}")
        )
        interview_status = candidate_service.derive_interview_status(current_stage, stage_closed_from, statuses)

        score_record = auto_score_map.get(parsed["candidate_id"])
        score_total = (
            float(score_record.get("total_score") or 0)
            if score_record and score_record.get("total_score") is not None
            else None
        )
        score_max = (
            float(score_record.get("max_score") or 0)
            if score_record and score_record.get("max_score") is not None
            else None
        )
        score_level = score_record.get("match_level", "") if score_record else ""

        items.append(
            {
                "candidate_id": parsed["candidate_id"],
                "filename": parsed["filename"],
                "name": parsed["name"],
                "role": parsed["role"],
                "applied_position": applied_position,
                "pdf_url": parsed["pdf_url"],
                "inflow_date": file_row.get("inflow_date", ""),
                "experience_tag": experience_type,
                "duration_tag": calc_duration_tag(experience_type, graduation_year, work_years),
                "education_tag": highest_education or "未知",
                "school_tag": school_name or "未知",
                "stage_tag": interview_status,
                "interview_status": interview_status,
                "applied_position_text": applied_position_text,
                "department_scope": department_scope,
                "job_id": job_id,
                "job_code": job_code,
                "job_title": job_title,
                "is_starred": int(summary.get("is_starred", 0)),
                "terminated_at": summary.get("terminated_at", ""),
                "nearest_interview_time": nearest_times.get(parsed["candidate_id"], ""),
                "score_total": score_total,
                "score_max": score_max,
                "score_level": score_level,
            }
        )

    return items


def candidate_map() -> dict[str, dict[str, Any]]:
    return {item["candidate_id"]: item for item in list_candidates()}


def list_candidates_for_user(user: dict[str, Any] | None) -> list[dict[str, Any]]:
    workflow_service = _candidate_workflow_service()
    items = list_candidates()
    visible_ids = workflow_service.visible_candidate_ids_for_user(user)
    if visible_ids is None:
        return items
    return [item for item in items if str(item.get("candidate_id", "")) in visible_ids]


def list_interview_calendar() -> list[dict[str, str]]:
    candidate_service = _candidate_service()
    candidates = list_candidates()
    name_map = {item["candidate_id"]: item["name"] for item in candidates}
    filename_map = {item["candidate_id"]: item.get("filename", "") for item in candidates}

    with connect_db(candidate_service.DB_PATH) as conn:
        seed_candidate_profiles(conn)
        _, future_items = list_future_interview_schedule(conn)
        conn.commit()

    items: list[dict[str, str]] = []
    for entry in future_items:
        candidate_id = entry["candidate_id"]
        name = name_map.get(candidate_id)
        if not name:
            fallback_filename = filename_map.get(candidate_id, "")
            if fallback_filename:
                name = parse_candidate_from_filename(
                    fallback_filename,
                    candidate_id=candidate_id,
                ).get("name", candidate_id)
            else:
                name = candidate_id
        stage = entry["stage"]
        display_time = entry["interview_time_display"]
        items.append(
            {
                "candidate_id": candidate_id,
                "candidate_name": name,
                "stage": stage,
                "interview_time": entry["interview_time"],
                "interview_time_display": display_time,
                "text": f"{name}-{stage}-{display_time}",
            }
        )
    return items


def list_interview_calendar_for_user(user: dict[str, Any] | None) -> list[dict[str, str]]:
    workflow_service = _candidate_workflow_service()
    items = list_interview_calendar()
    visible_ids = workflow_service.visible_candidate_ids_for_user(user)
    if visible_ids is None:
        return items
    return [item for item in items if str(item.get("candidate_id", "")) in visible_ids]


def parse_resume_result_filters(query: str) -> dict[str, str]:
    params = parse_qs(query or "", keep_blank_values=True)
    return {
        "uploaded_from": _first_query_value(params, ("uploaded_from", "upload_date_from", "date_from")),
        "uploaded_to": _first_query_value(params, ("uploaded_to", "upload_date_to", "date_to")),
    }


def _parse_datetime_bound(value: str, *, is_end: bool) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    parsed_date = _parse_date_bound(text)
    if parsed_date is not None:
        if is_end:
            return datetime.combine(parsed_date, datetime.max.time()).replace(microsecond=999999)
        return datetime.combine(parsed_date, datetime.min.time())
    normalized = text.replace(" ", "T")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def _parse_uploaded_at(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def _build_resume_result_row(
    *,
    file_row: dict[str, Any],
    summary: dict[str, Any],
    rounds: dict[str, dict[str, Any]],
    auto_score: dict[str, Any] | None,
) -> dict[str, Any]:
    candidate_service = _candidate_service()
    current_stage = summary.get("current_stage") or candidate_service.DEFAULT_STAGE
    stage_closed_from = summary.get("stage_closed_from") or ""
    statuses, current_stage, stage_closed_from = candidate_service.decode_stage_statuses(
        summary.get("stage_status_json") or "",
        current_stage,
        stage_closed_from,
    )
    current_status = candidate_service.derive_interview_status(current_stage, stage_closed_from, statuses)
    active_stage = (
        candidate_service.normalize_stage_name(current_stage)
        if current_status.startswith("待")
        else ""
    )
    return {
        "candidate_id": str(file_row.get("candidate_id", "")).strip(),
        "uploaded_at": str(file_row.get("uploaded_at", "")).strip(),
        "candidate_name": str(file_row.get("candidate_name", "")).strip(),
        "current_status": current_status,
        "active_stage": active_stage,
        "screening_interviewer": str(rounds.get("初筛", {}).get("interviewer_name", "")).strip(),
        "first_interviewer": str(rounds.get("一面", {}).get("interviewer_name", "")).strip(),
        "second_interviewer": str(rounds.get("二面", {}).get("interviewer_name", "")).strip(),
        "hr_interviewer": str(rounds.get("HR面", {}).get("interviewer_name", "")).strip(),
        "ai_score": auto_score.get("total_score") if isinstance(auto_score, dict) else None,
        "ai_score_summary": str((auto_score or {}).get("summary", "")).strip(),
    }


def list_resume_result_rows_for_user(
    user: dict[str, Any] | None,
    filters: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    workflow_service = _candidate_workflow_service()
    candidate_service = _candidate_service()
    normalized = filters or {}
    uploaded_from = _parse_datetime_bound(normalized.get("uploaded_from", ""), is_end=False)
    uploaded_to = _parse_datetime_bound(normalized.get("uploaded_to", ""), is_end=True)
    visible_ids = workflow_service.visible_candidate_ids_for_user(user)

    with connect_db(candidate_service.DB_PATH) as conn:
        seed_candidate_profiles(conn)
        file_rows = list_candidate_file_rows(conn)
        summaries = profile_summaries(conn)
        score_rows = conn.execute(
            """
            SELECT candidate_id, total_score, summary
            FROM candidate_auto_scores
            ORDER BY candidate_id, created_at DESC
            """
        ).fetchall()

        auto_score_map: dict[str, dict[str, Any]] = {}
        for row in score_rows:
            candidate_id = str(row[0] or "").strip()
            if not candidate_id or candidate_id in auto_score_map:
                continue
            auto_score_map[candidate_id] = {
                "total_score": row[1],
                "summary": str(row[2] or "").strip(),
            }

        items: list[dict[str, Any]] = []
        for file_row in file_rows:
            candidate_id = str(file_row.get("candidate_id", "")).strip()
            if not candidate_id:
                continue
            if visible_ids is not None and candidate_id not in visible_ids:
                continue

            uploaded_at = _parse_uploaded_at(file_row.get("uploaded_at", ""))
            if uploaded_from and (uploaded_at is None or uploaded_at < uploaded_from):
                continue
            if uploaded_to and (uploaded_at is None or uploaded_at > uploaded_to):
                continue

            rounds = load_rounds(conn, candidate_id)
            items.append(
                _build_resume_result_row(
                    file_row=file_row,
                    summary=summaries.get(candidate_id, {}),
                    rounds=rounds,
                    auto_score=auto_score_map.get(candidate_id),
                )
            )

        conn.commit()
    return sorted(items, key=lambda item: item.get("uploaded_at", ""), reverse=True)


def get_resume_result_summary_for_user(
    user: dict[str, Any] | None,
    filters: dict[str, str] | None = None,
) -> dict[str, Any]:
    candidate_service = _candidate_service()
    items = list_resume_result_rows_for_user(user, filters)
    stage_counts = {stage: 0 for stage in candidate_service.INTERVIEW_STAGES}
    passed_count = 0
    failed_count = 0
    for item in items:
        status = str(item.get("current_status", "")).strip()
        if status == candidate_service.STATUS_PASSED:
            passed_count += 1
        elif status.startswith("未通过"):
            failed_count += 1
        active_stage = str(item.get("active_stage", "")).strip()
        if active_stage in stage_counts:
            stage_counts[active_stage] += 1
    return {
        "total_count": len(items),
        "finished_count": passed_count + failed_count,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "stage_counts": stage_counts,
        "filters": filters or {},
    }


def export_resume_results_for_user(
    user: dict[str, Any] | None,
    filters: dict[str, str] | None = None,
) -> tuple[str, str, bytes]:
    items = list_resume_result_rows_for_user(user, filters)
    timestamp = utc_now_iso().replace(":", "-")
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "简历上传时间",
            "简历人员",
            "初筛面试人",
            "一面面试人",
            "二面面试人",
            "HR面面试人",
            "当前简历状态",
            "AI自动评分",
            "AI自动评分详细描述",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item.get("uploaded_at", ""),
                item.get("candidate_name", ""),
                item.get("screening_interviewer", ""),
                item.get("first_interviewer", ""),
                item.get("second_interviewer", ""),
                item.get("hr_interviewer", ""),
                item.get("current_status", ""),
                item.get("ai_score", ""),
                item.get("ai_score_summary", ""),
            ]
        )
    return (
        f"resume-results-{timestamp}.csv",
        "text/csv; charset=utf-8",
        buffer.getvalue().encode("utf-8-sig"),
    )


__all__ = [
    "candidate_map",
    "filter_candidates",
    "export_resume_results_for_user",
    "get_resume_result_summary_for_user",
    "list_candidates",
    "list_candidates_for_user",
    "list_future_interview_schedule",
    "list_interview_calendar",
    "list_interview_calendar_for_user",
    "list_resume_result_rows_for_user",
    "normalize_filter_text",
    "parse_candidate_filters",
    "parse_resume_result_filters",
]
