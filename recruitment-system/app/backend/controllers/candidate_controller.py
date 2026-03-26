from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any
from urllib.parse import unquote

from ..services.recruitment_service import (
    ROLE_INTERVIEWER,
    can_access_candidate,
    can_delete_candidate,
    can_sync_resumes,
    can_transition_stage,
    can_upload_resume,
    can_write_profile,
    can_write_round,
    create_candidate_from_upload,
    delete_candidate,
    filter_candidates,
    get_evaluation,
    list_candidates_for_user,
    list_interview_calendar_for_user,
    parse_candidate_filters,
    parse_job_payload,
    resolve_resume_path,
    RESULT_FAILED,
    RESULT_SUCCESS,
    record_operation_log_from_request,
    save_evaluation,
    save_profile_only,
    save_round_only,
    save_star_only,
    sync_resumes_from_storage,
    transition_stage,
    trigger_auto_score_for_candidate,
    trigger_resume_extract_for_candidate,
    user_role_code,
    validate_stage_action_payload,
    validate_star_payload,
)


def _candidate_name_from_evaluation(item: dict[str, Any] | None) -> str:
    if not isinstance(item, dict):
        return ""
    profile = item.get("profile")
    if isinstance(profile, dict):
        return str(profile.get("candidate_name", "")).strip()
    return ""


def _format_upload_date(date_text: str) -> str:
    text = str(date_text or "").strip()
    digits = text.replace("-", "")
    if len(digits) != 8 or not digits.isdigit():
        return ""
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"


def _collect_upload_date_options(items: list[dict[str, Any]]) -> list[str]:
    dates = {
        formatted
        for formatted in (_format_upload_date(item.get("inflow_date", "")) for item in items)
        if formatted
    }
    return sorted(dates, reverse=True)


def _summarize_upload_date_distribution(items: list[dict[str, Any]], limit: int = 8) -> list[str]:
    counts: dict[str, int] = {}
    for item in items:
        formatted = _format_upload_date(str(item.get("inflow_date", "")))
        if not formatted:
            continue
        counts[formatted] = counts.get(formatted, 0) + 1
    ordered = sorted(counts.items(), reverse=True)
    return [f"{date_text}:{count}" for date_text, count in ordered[:limit]]


def _log_candidate_list_debug(
    *,
    user: dict[str, Any],
    raw_query: str,
    filters: dict[str, str],
    all_items: list[dict[str, Any]],
    filtered_items: list[dict[str, Any]],
    upload_dates: list[str],
) -> None:
    if not any(
        str(filters.get(key, "")).strip()
        for key in ("upload_date", "upload_date_from", "upload_date_to")
    ):
        return
    user_id = str(user.get("id", "")).strip()
    username = str(user.get("username", "")).strip()
    role_code = user_role_code(user)
    print(
        "[candidate list] "
        f"user_id='{user_id}' username='{username}' role='{role_code}' "
        f"raw_query='{raw_query}' "
        f"upload_date='{filters.get('upload_date', '')}' "
        f"upload_date_from='{filters.get('upload_date_from', '')}' "
        f"upload_date_to='{filters.get('upload_date_to', '')}' "
        f"visible_count={len(all_items)} filtered_count={len(filtered_items)} "
        f"upload_date_option_count={len(upload_dates)} "
        f"upload_date_option_sample={upload_dates[:8]} "
        f"visible_date_distribution={_summarize_upload_date_distribution(all_items)}"
    )


def handle_get_candidate_routes(handler: Any, parsed: Any, path: str, user: dict[str, Any]) -> bool:
    if path == "/api/candidates":
        all_items = list_candidates_for_user(user)
        filters = parse_candidate_filters(parsed.query)
        filtered_items = filter_candidates(all_items, filters)
        upload_dates = _collect_upload_date_options(all_items)
        _log_candidate_list_debug(
            user=user,
            raw_query=parsed.query,
            filters=filters,
            all_items=all_items,
            filtered_items=filtered_items,
            upload_dates=upload_dates,
        )
        handler._send_json(
            {
                "items": filtered_items,
                "total_count": len(all_items),
                "filtered_count": len(filtered_items),
                "filters": filters,
                "upload_dates": upload_dates,
            }
        )
        return True

    if path == "/api/interview-calendar":
        handler._send_json({"items": list_interview_calendar_for_user(user)})
        return True

    if path.startswith("/api/evaluations/"):
        candidate_id = unquote(path.removeprefix("/api/evaluations/"))
        if not can_access_candidate(user, candidate_id):
            handler._send_forbidden("candidate_forbidden")
            return True
        evaluation = get_evaluation(candidate_id)
        if evaluation is None:
            handler._send_json({"error": "candidate not found"}, status=HTTPStatus.NOT_FOUND)
            return True
        handler._send_json({"item": evaluation})
        return True

    if path.startswith("/api/resumes/"):
        candidate_id = unquote(path.removeprefix("/api/resumes/")).strip()
        if not can_access_candidate(user, candidate_id):
            handler._send_forbidden("candidate_forbidden")
            return True
        file_path = resolve_resume_path(candidate_id)
        if file_path is None:
            handler._send_json({"error": "candidate not found"}, status=HTTPStatus.NOT_FOUND)
            return True
        handler._send_file(file_path, "application/pdf")
        return True

    return False


def handle_put_candidate_routes(handler: Any, path: str, user: dict[str, Any]) -> bool:
    if path.startswith("/api/evaluations/") and path.endswith("/profile"):
        candidate_id = unquote(path.removeprefix("/api/evaluations/").removesuffix("/profile"))
        if not can_write_profile(user, candidate_id):
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人管理",
                operation_type="update_profile",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark="profile_forbidden",
            )
            handler._send_forbidden("profile_forbidden")
            return True
        try:
            payload = handler._parse_json_body()
            saved = save_profile_only(candidate_id, payload)
            if saved is None:
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="候选人管理",
                    operation_type="update_profile",
                    biz_object_type="candidate",
                    biz_object_id=candidate_id,
                    operation_result=RESULT_FAILED,
                    remark="candidate not found",
                )
                handler._send_json({"error": "candidate not found"}, status=HTTPStatus.NOT_FOUND)
                return True
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人管理",
                operation_type="update_profile",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                biz_object_name=_candidate_name_from_evaluation(saved),
                operation_result=RESULT_SUCCESS,
                remark="保存候选人通用信息",
            )
            handler._send_json({"item": saved})
            return True
        except json.JSONDecodeError:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人管理",
                operation_type="update_profile",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark="invalid json",
            )
            handler._send_json({"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
            return True
        except ValueError as exc:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人管理",
                operation_type="update_profile",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark=str(exc),
            )
            handler._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return True

    if path.startswith("/api/evaluations/") and path.endswith("/star"):
        candidate_id = unquote(path.removeprefix("/api/evaluations/").removesuffix("/star"))
        if not can_write_profile(user, candidate_id):
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人管理",
                operation_type="star",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark="star_forbidden",
            )
            handler._send_forbidden("star_forbidden")
            return True
        try:
            payload = handler._parse_json_body()
            is_starred, error = validate_star_payload(payload)
            if is_starred is None:
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="候选人管理",
                    operation_type="star",
                    biz_object_type="candidate",
                    biz_object_id=candidate_id,
                    operation_result=RESULT_FAILED,
                    remark=error,
                )
                handler._send_json({"error": error}, status=HTTPStatus.BAD_REQUEST)
                return True
            saved = save_star_only(candidate_id, is_starred)
            if saved is None:
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="候选人管理",
                    operation_type="star",
                    biz_object_type="candidate",
                    biz_object_id=candidate_id,
                    operation_result=RESULT_FAILED,
                    remark="candidate not found",
                )
                handler._send_json({"error": "candidate not found"}, status=HTTPStatus.NOT_FOUND)
                return True
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人管理",
                operation_type="star",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                biz_object_name=_candidate_name_from_evaluation(saved),
                operation_result=RESULT_SUCCESS,
                remark="更新候选人星标状态",
                extra_context={"is_starred": int(is_starred)},
            )
            handler._send_json({"item": saved})
            return True
        except json.JSONDecodeError:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人管理",
                operation_type="star",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark="invalid json",
            )
            handler._send_json({"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
            return True
        except ValueError as exc:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人管理",
                operation_type="star",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark=str(exc),
            )
            handler._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return True

    if path.startswith("/api/evaluations/") and path.endswith("/round"):
        candidate_id = unquote(path.removeprefix("/api/evaluations/").removesuffix("/round"))
        try:
            payload = handler._parse_json_body()
            stage = str(payload.get("stage", "")).strip()
            allowed, reason = can_write_round(user, candidate_id, stage)
            if not allowed:
                if reason == "invalid_stage":
                    record_operation_log_from_request(
                        handler,
                        user=user,
                        operation_module="候选人管理",
                        operation_type="save_round",
                        biz_object_type="candidate",
                        biz_object_id=candidate_id,
                        operation_result=RESULT_FAILED,
                        remark="round.stage 非法",
                    )
                    handler._send_json({"error": "round.stage 非法"}, status=HTTPStatus.BAD_REQUEST)
                    return True
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="候选人管理",
                    operation_type="save_round",
                    biz_object_type="candidate",
                    biz_object_id=candidate_id,
                    operation_result=RESULT_FAILED,
                    remark=reason or "round_forbidden",
                )
                handler._send_forbidden(reason or "round_forbidden")
                return True
            if user_role_code(user) == ROLE_INTERVIEWER:
                payload["interviewer_user_id"] = str(user.get("id", "")).strip()
            saved = save_round_only(candidate_id, payload)
            if saved is None:
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="候选人管理",
                    operation_type="save_round",
                    biz_object_type="candidate",
                    biz_object_id=candidate_id,
                    operation_result=RESULT_FAILED,
                    remark="candidate not found",
                )
                handler._send_json({"error": "candidate not found"}, status=HTTPStatus.NOT_FOUND)
                return True
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人管理",
                operation_type="save_round",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                biz_object_name=_candidate_name_from_evaluation(saved),
                operation_result=RESULT_SUCCESS,
                remark=f"保存轮次面评：{stage}",
            )
            handler._send_json({"item": saved})
            return True
        except json.JSONDecodeError:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人管理",
                operation_type="save_round",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark="invalid json",
            )
            handler._send_json({"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
            return True
        except ValueError as exc:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人管理",
                operation_type="save_round",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark=str(exc),
            )
            handler._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return True

    if path.startswith("/api/evaluations/"):
        candidate_id = unquote(path.removeprefix("/api/evaluations/"))
        try:
            payload = handler._parse_json_body()
            round_payload = payload.get("round") or {}
            if not can_write_profile(user, candidate_id):
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="候选人管理",
                    operation_type="save_evaluation",
                    biz_object_type="candidate",
                    biz_object_id=candidate_id,
                    operation_result=RESULT_FAILED,
                    remark="profile_forbidden",
                )
                handler._send_forbidden("profile_forbidden")
                return True
            stage = str(round_payload.get("stage", "")).strip()
            allowed, reason = can_write_round(user, candidate_id, stage)
            if not allowed:
                if reason == "invalid_stage":
                    record_operation_log_from_request(
                        handler,
                        user=user,
                        operation_module="候选人管理",
                        operation_type="save_evaluation",
                        biz_object_type="candidate",
                        biz_object_id=candidate_id,
                        operation_result=RESULT_FAILED,
                        remark="round.stage 非法",
                    )
                    handler._send_json({"error": "round.stage 非法"}, status=HTTPStatus.BAD_REQUEST)
                    return True
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="候选人管理",
                    operation_type="save_evaluation",
                    biz_object_type="candidate",
                    biz_object_id=candidate_id,
                    operation_result=RESULT_FAILED,
                    remark=reason or "round_forbidden",
                )
                handler._send_forbidden(reason or "round_forbidden")
                return True
            if user_role_code(user) == ROLE_INTERVIEWER:
                round_payload["interviewer_user_id"] = str(user.get("id", "")).strip()
                payload["round"] = round_payload
            saved = save_evaluation(candidate_id, payload)
            if saved is None:
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="候选人管理",
                    operation_type="save_evaluation",
                    biz_object_type="candidate",
                    biz_object_id=candidate_id,
                    operation_result=RESULT_FAILED,
                    remark="candidate not found",
                )
                handler._send_json({"error": "candidate not found"}, status=HTTPStatus.NOT_FOUND)
                return True
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人管理",
                operation_type="save_evaluation",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                biz_object_name=_candidate_name_from_evaluation(saved),
                operation_result=RESULT_SUCCESS,
                remark="保存候选人完整评估",
            )
            handler._send_json({"item": saved})
            return True
        except json.JSONDecodeError:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人管理",
                operation_type="save_evaluation",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark="invalid json",
            )
            handler._send_json({"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
            return True
        except ValueError as exc:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人管理",
                operation_type="save_evaluation",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark=str(exc),
            )
            handler._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return True

    return False


def handle_post_candidate_routes(handler: Any, path: str, user: dict[str, Any]) -> bool:
    if path == "/api/resumes/upload":
        if not can_upload_resume(user):
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人导入",
                operation_type="upload",
                biz_object_type="candidate_file",
                operation_result=RESULT_FAILED,
                remark="upload_forbidden",
            )
            handler._send_forbidden("upload_forbidden")
            return True
        try:
            fields, files = handler._parse_multipart_form()
            file_info = files.get("file")
            if not file_info:
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="候选人导入",
                    operation_type="upload",
                    biz_object_type="candidate_file",
                    operation_result=RESULT_FAILED,
                    remark="请上传 PDF 文件",
                )
                handler._send_json({"error": "请上传 PDF 文件"}, status=HTTPStatus.BAD_REQUEST)
                return True
            job_payload_raw = str(fields.get("job_payload", "") or "").strip()
            job_payload = parse_job_payload(job_payload_raw)
            created = create_candidate_from_upload(
                filename=str(file_info.get("filename", "")),
                content=bytes(file_info.get("content", b"")),
                candidate_name=str(fields.get("candidate_name", "")),
                uploaded_by=str(user.get("id", "")),
                department_scope=str(fields.get("department_scope", "")),
                job_id=str(fields.get("job_id", "")),
                job_code=str(fields.get("job_code", "")),
                job_title=str(fields.get("job_title", "")),
                job_payload=job_payload,
            )
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人导入",
                operation_type="upload",
                biz_object_type="candidate",
                biz_object_id=str(created.get("candidate_id", "")),
                biz_object_name=str(created.get("candidate_name", "")),
                operation_result=RESULT_SUCCESS,
                remark=f"上传简历：{str(file_info.get('filename', ''))}",
            )
            handler._send_json({"item": created}, status=HTTPStatus.CREATED)
            return True
        except ValueError as exc:
            message = str(exc)
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人导入",
                operation_type="upload",
                biz_object_type="candidate_file",
                operation_result=RESULT_FAILED,
                remark=message,
            )
            status = HTTPStatus.BAD_REQUEST
            if "同名文件" in message:
                status = HTTPStatus.CONFLICT
            if "过大" in message:
                status = HTTPStatus.REQUEST_ENTITY_TOO_LARGE
            handler._send_json({"error": message}, status=status)
            return True

    if path == "/api/resumes/sync":
        if not can_sync_resumes(user):
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人导入",
                operation_type="sync",
                biz_object_type="candidate_file",
                operation_result=RESULT_FAILED,
                remark="sync_forbidden",
            )
            handler._send_forbidden("sync_forbidden")
            return True
        result = sync_resumes_from_storage()
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="候选人导入",
            operation_type="sync",
            biz_object_type="candidate_file",
            operation_result=RESULT_SUCCESS,
            remark=f"同步目录完成，新增 {int(result.get('added_count', 0))} 份",
            extra_context=result,
        )
        handler._send_json({"item": result})
        return True

    if path.startswith("/api/evaluations/") and path.endswith("/auto-score"):
        candidate_id = unquote(path.removeprefix("/api/evaluations/").removesuffix("/auto-score"))
        if not can_write_profile(user, candidate_id):
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="自动评分",
                operation_type="trigger",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark="profile_forbidden",
            )
            handler._send_forbidden("profile_forbidden")
            return True
        try:
            score = trigger_auto_score_for_candidate(candidate_id)
            evaluation = get_evaluation(candidate_id)
            if evaluation is None:
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="自动评分",
                    operation_type="trigger",
                    biz_object_type="candidate",
                    biz_object_id=candidate_id,
                    operation_result=RESULT_FAILED,
                    remark="candidate not found",
                )
                handler._send_json({"error": "candidate not found"}, status=HTTPStatus.NOT_FOUND)
                return True
            evaluation["auto_score"] = score
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="自动评分",
                operation_type="trigger",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                biz_object_name=_candidate_name_from_evaluation(evaluation),
                operation_result=RESULT_SUCCESS,
                remark="手动触发自动评分",
            )
            handler._send_json({"item": evaluation})
            return True
        except ValueError as exc:
            message = str(exc)
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="自动评分",
                operation_type="trigger",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark=message,
            )
            status = HTTPStatus.BAD_REQUEST
            if message == "candidate not found":
                status = HTTPStatus.NOT_FOUND
            handler._send_json({"error": message}, status=status)
            return True

    if path.startswith("/api/evaluations/") and path.endswith("/resume-extract"):
        candidate_id = unquote(path.removeprefix("/api/evaluations/").removesuffix("/resume-extract"))
        if not can_write_profile(user, candidate_id):
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="简历抽取",
                operation_type="trigger",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark="profile_forbidden",
            )
            handler._send_forbidden("profile_forbidden")
            return True
        try:
            trigger_resume_extract_for_candidate(candidate_id)
            evaluation = get_evaluation(candidate_id)
            if evaluation is None:
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="简历抽取",
                    operation_type="trigger",
                    biz_object_type="candidate",
                    biz_object_id=candidate_id,
                    operation_result=RESULT_FAILED,
                    remark="candidate not found",
                )
                handler._send_json({"error": "candidate not found"}, status=HTTPStatus.NOT_FOUND)
                return True
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="简历抽取",
                operation_type="trigger",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                biz_object_name=_candidate_name_from_evaluation(evaluation),
                operation_result=RESULT_SUCCESS,
                remark="手动触发简历结构化抽取",
            )
            handler._send_json({"item": evaluation})
            return True
        except ValueError as exc:
            message = str(exc)
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="简历抽取",
                operation_type="trigger",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark=message,
            )
            status = HTTPStatus.BAD_REQUEST
            if message == "candidate not found":
                status = HTTPStatus.NOT_FOUND
            handler._send_json({"error": message}, status=status)
            return True

    if path.startswith("/api/evaluations/") and path.endswith("/stage"):
        candidate_id = unquote(path.removeprefix("/api/evaluations/").removesuffix("/stage"))
        try:
            payload = handler._parse_json_body()
            action, error = validate_stage_action_payload(payload)
            if action is None:
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="流程流转",
                    operation_type="transition",
                    biz_object_type="candidate",
                    biz_object_id=candidate_id,
                    operation_result=RESULT_FAILED,
                    remark=error,
                )
                handler._send_json({"error": error}, status=HTTPStatus.BAD_REQUEST)
                return True
            allowed, reason = can_transition_stage(user, candidate_id, action)
            if not allowed:
                if reason == "candidate_not_found":
                    record_operation_log_from_request(
                        handler,
                        user=user,
                        operation_module="流程流转",
                        operation_type="transition",
                        biz_object_type="candidate",
                        biz_object_id=candidate_id,
                        operation_result=RESULT_FAILED,
                        remark="candidate not found",
                    )
                    handler._send_json({"error": "candidate not found"}, status=HTTPStatus.NOT_FOUND)
                    return True
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="流程流转",
                    operation_type="transition",
                    biz_object_type="candidate",
                    biz_object_id=candidate_id,
                    operation_result=RESULT_FAILED,
                    remark=reason or "stage_transition_forbidden",
                )
                handler._send_forbidden(reason or "stage_transition_forbidden")
                return True
            saved = transition_stage(candidate_id, action)
            if saved is None:
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="流程流转",
                    operation_type="transition",
                    biz_object_type="candidate",
                    biz_object_id=candidate_id,
                    operation_result=RESULT_FAILED,
                    remark="candidate not found",
                )
                handler._send_json({"error": "candidate not found"}, status=HTTPStatus.NOT_FOUND)
                return True
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="流程流转",
                operation_type="transition",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                biz_object_name=_candidate_name_from_evaluation(saved),
                operation_result=RESULT_SUCCESS,
                remark=f"候选人流程动作：{action}",
                extra_context={"action": action},
            )
            handler._send_json({"item": saved})
            return True
        except json.JSONDecodeError:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="流程流转",
                operation_type="transition",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark="invalid json",
            )
            handler._send_json({"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
            return True
        except ValueError as exc:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="流程流转",
                operation_type="transition",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark=str(exc),
            )
            handler._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return True

    return False


def handle_delete_candidate_routes(handler: Any, path: str, user: dict[str, Any]) -> bool:
    if not path.startswith("/api/candidates/"):
        return False
    candidate_id = unquote(path.removeprefix("/api/candidates/")).strip()
    if not can_delete_candidate(user, candidate_id):
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="候选人管理",
            operation_type="delete",
            biz_object_type="candidate",
            biz_object_id=candidate_id,
            operation_result=RESULT_FAILED,
            remark="delete_forbidden",
        )
        handler._send_forbidden("delete_forbidden")
        return True
    try:
        deleted = delete_candidate(candidate_id)
        if not deleted:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="候选人管理",
                operation_type="delete",
                biz_object_type="candidate",
                biz_object_id=candidate_id,
                operation_result=RESULT_FAILED,
                remark="candidate not found",
            )
            handler._send_json({"error": "candidate not found"}, status=HTTPStatus.NOT_FOUND)
            return True
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="候选人管理",
            operation_type="delete",
            biz_object_type="candidate",
            biz_object_id=candidate_id,
            operation_result=RESULT_SUCCESS,
            remark="删除候选人",
        )
        handler._send_json({"ok": True})
        return True
    except ValueError as exc:
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="候选人管理",
            operation_type="delete",
            biz_object_type="candidate",
            biz_object_id=candidate_id,
            operation_result=RESULT_FAILED,
            remark=str(exc),
        )
        handler._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        return True
