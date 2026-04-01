from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .role_user_service import normalize_department_scope

BASE_OPTIONS = {"北京", "深圳"}
SALARY_MODES = {"月薪", "年包"}
EXPERIENCE_TYPES = {"应届生", "已工作"}
HIRE_TYPES = {"实习", "正式"}
INTERVIEW_STAGES = ["初筛", "一面", "二面", "HR面"]
DEFAULT_STAGE = INTERVIEW_STAGES[0]
WAITING_STATUS_BY_STAGE = {
    "初筛": "待初筛",
    "一面": "待一面",
    "二面": "待二面",
    "HR面": "待HR面",
}
STATUS_PASSED = "通过"
FAILED_STATUS_BY_STAGE = {
    "初筛": "未通过初筛",
    "一面": "未通过一面",
    "二面": "未通过二面",
    "HR面": "未通过HR面",
}
STAGE_STATUS_PENDING = "pending"
STAGE_STATUS_PASSED = "passed"
STAGE_STATUS_ENDED = "ended"
STAGE_STATUS_VALUES = {
    STAGE_STATUS_PENDING,
    STAGE_STATUS_PASSED,
    STAGE_STATUS_ENDED,
}
LEGACY_STAGE_MAP = {
    "初筛": "初筛",
    "待初筛": "初筛",
    "一面": "一面",
    "待一面": "一面",
    "二面": "二面",
    "待二面": "二面",
    "HR面": "HR面",
    "待HR面": "HR面",
    "终面": "HR面",
    "待终面": "HR面",
    "已结束": "",
    "已通过": "",
}


def stage_index(stage: str) -> int:
    try:
        return INTERVIEW_STAGES.index(stage)
    except ValueError:
        return -1


def normalize_stage_name(stage: str) -> str:
    value = (stage or "").strip()
    if value in INTERVIEW_STAGES:
        return value
    if value in LEGACY_STAGE_MAP:
        return LEGACY_STAGE_MAP[value]
    return ""


def stage_status_template() -> dict[str, str]:
    return {stage: STAGE_STATUS_PENDING for stage in INTERVIEW_STAGES}


def build_stage_statuses(
    current_stage: str,
    stage_closed_from: str,
) -> tuple[dict[str, str], str, str]:
    current = normalize_stage_name(current_stage) or DEFAULT_STAGE
    closed_from = normalize_stage_name(stage_closed_from)
    statuses = stage_status_template()

    if closed_from:
        closed_idx = stage_index(closed_from)
        for stage in INTERVIEW_STAGES:
            idx = stage_index(stage)
            if idx < closed_idx:
                statuses[stage] = STAGE_STATUS_PASSED
            elif idx == closed_idx:
                statuses[stage] = STAGE_STATUS_ENDED
            else:
                statuses[stage] = STAGE_STATUS_PENDING
        return statuses, closed_from, closed_from

    current_idx = stage_index(current)
    for stage in INTERVIEW_STAGES:
        idx = stage_index(stage)
        statuses[stage] = STAGE_STATUS_PASSED if idx < current_idx else STAGE_STATUS_PENDING

    return statuses, current, ""


def decode_stage_statuses(
    raw_json: str,
    current_stage: str,
    stage_closed_from: str,
) -> tuple[dict[str, str], str, str]:
    current = normalize_stage_name(current_stage) or DEFAULT_STAGE
    closed_from = normalize_stage_name(stage_closed_from)
    statuses = stage_status_template()

    parsed: Any = None
    if raw_json:
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            parsed = None

    parsed_stage_keys: set[str] = set()
    if isinstance(parsed, dict):
        for key, value in parsed.items():
            stage = normalize_stage_name(str(key))
            if not stage:
                continue
            parsed_stage_keys.add(stage)
            status = str(value).strip()
            if status in STAGE_STATUS_VALUES:
                statuses[stage] = status

    if not parsed_stage_keys:
        return build_stage_statuses(current, closed_from)
    if "初筛" not in parsed_stage_keys and any(stage in parsed_stage_keys for stage in INTERVIEW_STAGES[1:]):
        statuses["初筛"] = STAGE_STATUS_PASSED

    ended_stages = [stage for stage in INTERVIEW_STAGES if statuses[stage] == STAGE_STATUS_ENDED]
    if ended_stages:
        ended_stage = ended_stages[0]
        ended_idx = stage_index(ended_stage)
        for stage in INTERVIEW_STAGES:
            idx = stage_index(stage)
            if idx < ended_idx and statuses[stage] == STAGE_STATUS_PENDING:
                statuses[stage] = STAGE_STATUS_PASSED
            if idx > ended_idx:
                statuses[stage] = STAGE_STATUS_PENDING
        return statuses, ended_stage, ended_stage

    pending_stages = [stage for stage in INTERVIEW_STAGES if statuses[stage] == STAGE_STATUS_PENDING]
    if pending_stages:
        current = pending_stages[0]
    elif all(statuses[stage] == STAGE_STATUS_PASSED for stage in INTERVIEW_STAGES):
        current = INTERVIEW_STAGES[-1]
    else:
        statuses, current, closed_from = build_stage_statuses(current, closed_from)

    if closed_from:
        statuses, current, closed_from = build_stage_statuses(current, closed_from)

    return statuses, current, closed_from


def dump_stage_statuses(statuses: dict[str, str]) -> str:
    normalized = stage_status_template()
    for stage in INTERVIEW_STAGES:
        value = statuses.get(stage, STAGE_STATUS_PENDING)
        normalized[stage] = value if value in STAGE_STATUS_VALUES else STAGE_STATUS_PENDING
    return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))


def parse_interview_datetime(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def format_interview_datetime(value: str) -> str:
    dt = parse_interview_datetime(value)
    if dt is None:
        return (value or "").strip()
    local_dt = dt.astimezone() if dt.tzinfo else dt
    return local_dt.strftime("%Y-%m-%d %H:%M")


def derive_interview_status(
    current_stage: str,
    stage_closed_from: str,
    statuses: dict[str, str],
) -> str:
    ended_stage = normalize_stage_name(stage_closed_from)
    if not ended_stage:
        ended_stage = next(
            (stage for stage in INTERVIEW_STAGES if statuses.get(stage) == STAGE_STATUS_ENDED),
            "",
        )
    if ended_stage:
        return FAILED_STATUS_BY_STAGE.get(ended_stage, f"未通过{ended_stage}")
    if all(statuses.get(stage) == STAGE_STATUS_PASSED for stage in INTERVIEW_STAGES):
        return STATUS_PASSED

    stage = normalize_stage_name(current_stage)
    if not stage or statuses.get(stage) != STAGE_STATUS_PENDING:
        stage = next(
            (current for current in INTERVIEW_STAGES if statuses.get(current) == STAGE_STATUS_PENDING),
            DEFAULT_STAGE,
        )
    return WAITING_STATUS_BY_STAGE.get(stage, WAITING_STATUS_BY_STAGE[DEFAULT_STAGE])


def validate_profile_payload(payload: dict[str, Any]) -> tuple[dict[str, str] | None, str]:
    raw_department_scope = str(payload.get("department_scope", "")).strip()
    cleaned = {
        "base_location": str(payload.get("base_location", "")).strip(),
        "salary_mode": str(payload.get("salary_mode", "")).strip(),
        "salary_range": str(payload.get("salary_range", "")).strip(),
        "experience_type": str(payload.get("experience_type", "")).strip(),
        "graduation_year": str(payload.get("graduation_year", "")).strip(),
        "work_years": str(payload.get("work_years", "")).strip(),
        "hire_type": str(payload.get("hire_type", "")).strip(),
        "preset_position": str(payload.get("preset_position", "")).strip(),
        "highest_education": str(payload.get("highest_education", "")).strip(),
        "school_name": str(payload.get("school_name", "")).strip(),
        "applied_position": str(payload.get("applied_position", "")).strip(),
        "department_scope": normalize_department_scope(raw_department_scope),
    }

    if cleaned["base_location"] not in BASE_OPTIONS:
        return None, "base_location 必须为 北京 或 深圳"
    if cleaned["salary_mode"] not in SALARY_MODES:
        return None, "salary_mode 必须为 月薪 或 年包"
    if cleaned["salary_range"] and "-" not in cleaned["salary_range"]:
        return None, "salary_range 需为区间值，例如 30k-40k"
    if cleaned["experience_type"] not in EXPERIENCE_TYPES:
        return None, "experience_type 必须为 应届生 或 已工作"
    if cleaned["experience_type"] == "应届生" and not cleaned["graduation_year"]:
        return None, "应届生必须填写 graduation_year"
    if cleaned["experience_type"] == "已工作" and not cleaned["work_years"]:
        return None, "已工作候选人必须填写 work_years"
    if cleaned["hire_type"] not in HIRE_TYPES:
        return None, "hire_type 必须为 实习 或 正式"
    if not cleaned["preset_position"]:
        return None, "preset_position 不能为空"
    if not cleaned["highest_education"]:
        cleaned["highest_education"] = "未知"
    if not cleaned["school_name"]:
        cleaned["school_name"] = "未知"
    if not cleaned["applied_position"]:
        return None, "applied_position 不能为空"
    if raw_department_scope and not cleaned["department_scope"]:
        return None, "department_scope 非法，必须为销售部/研发部/算法部/项目部/人事部"

    if cleaned["experience_type"] == "应届生":
        cleaned["work_years"] = ""
    else:
        cleaned["graduation_year"] = ""

    return cleaned, ""


def validate_round_payload(payload: dict[str, Any]) -> tuple[dict[str, str] | None, str]:
    cleaned = {
        "stage": str(payload.get("stage", "")).strip(),
        "interview_time": str(payload.get("interview_time", "")).strip(),
        "interviewer_user_id": str(payload.get("interviewer_user_id", "")).strip(),
        "planned_questions": str(payload.get("planned_questions", "")).strip(),
        "interview_review": str(payload.get("interview_review", "")).strip(),
    }

    if cleaned["stage"] not in INTERVIEW_STAGES:
        return None, "round.stage 非法"

    return cleaned, ""


def validate_stage_action_payload(payload: dict[str, Any]) -> tuple[str | None, str]:
    action = str(payload.get("action", "")).strip()
    if action not in {"next", "end", "reset"}:
        return None, "action 必须为 next 或 end 或 reset"
    return action, ""


def validate_next_round_payload(
    payload: dict[str, Any],
    *,
    expected_stage: str,
) -> tuple[dict[str, str] | None, str]:
    round_payload, error = validate_round_payload(payload)
    if round_payload is None:
        return None, error
    if round_payload["stage"] != expected_stage:
        return None, "next_round.stage 非法"
    if not round_payload["interview_time"]:
        return None, "next_round.interview_time 不能为空"
    if not round_payload["interviewer_user_id"]:
        return None, "next_round.interviewer_user_id 不能为空"
    return round_payload, ""


def validate_star_payload(payload: dict[str, Any]) -> tuple[int | None, str]:
    raw = payload.get("is_starred")
    if isinstance(raw, bool):
        return (1 if raw else 0), ""
    if isinstance(raw, int) and raw in (0, 1):
        return raw, ""
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in {"1", "true"}:
            return 1, ""
        if value in {"0", "false"}:
            return 0, ""
    return None, "is_starred 必须为布尔值或 0/1"


def current_active_stage(statuses: dict[str, str], current_stage: str) -> str:
    normalized_current = normalize_stage_name(current_stage)
    if normalized_current and statuses.get(normalized_current) == STAGE_STATUS_PENDING:
        return normalized_current
    for stage in INTERVIEW_STAGES:
        if statuses.get(stage) == STAGE_STATUS_PENDING:
            return stage
    return INTERVIEW_STAGES[-1]


__all__ = [
    "BASE_OPTIONS",
    "SALARY_MODES",
    "EXPERIENCE_TYPES",
    "HIRE_TYPES",
    "INTERVIEW_STAGES",
    "DEFAULT_STAGE",
    "WAITING_STATUS_BY_STAGE",
    "STATUS_PASSED",
    "FAILED_STATUS_BY_STAGE",
    "STAGE_STATUS_PENDING",
    "STAGE_STATUS_PASSED",
    "STAGE_STATUS_ENDED",
    "STAGE_STATUS_VALUES",
    "LEGACY_STAGE_MAP",
    "stage_index",
    "normalize_stage_name",
    "stage_status_template",
    "build_stage_statuses",
    "decode_stage_statuses",
    "dump_stage_statuses",
    "parse_interview_datetime",
    "format_interview_datetime",
    "derive_interview_status",
    "validate_profile_payload",
    "validate_round_payload",
    "validate_stage_action_payload",
    "validate_next_round_payload",
    "validate_star_payload",
    "current_active_stage",
]
