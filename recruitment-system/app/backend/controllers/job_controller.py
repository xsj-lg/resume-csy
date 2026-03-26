from __future__ import annotations

import json
import sqlite3
from http import HTTPStatus
from typing import Any
from urllib.parse import unquote

from ..services.recruitment_service import (
    can_manage_jobs,
    can_view_jobs,
    delete_job_score_table_version,
    get_job_score_table_preview,
    list_jobs_for_user,
    parse_score_table_preview,
    record_operation_log_from_request,
    replace_jobs_from_client,
    RESULT_FAILED,
    RESULT_SUCCESS,
    upload_job_score_table,
)


def handle_get_job_routes(handler: Any, path: str, user: dict[str, Any]) -> bool:
    if path == "/api/jobs":
        if not can_view_jobs(user):
            handler._send_forbidden("jobs_forbidden")
            return True
        handler._send_json({"items": list_jobs_for_user(user)})
        return True

    if path.startswith("/api/jobs/") and path.endswith("/score-table/preview"):
        if not can_view_jobs(user):
            handler._send_forbidden("jobs_forbidden")
            return True
        job_id = unquote(path.removeprefix("/api/jobs/").removesuffix("/score-table/preview")).strip()
        try:
            visible_ids = {str(item.get("job_id", "")) for item in list_jobs_for_user(user)}
            if job_id not in visible_ids:
                handler._send_forbidden("job_forbidden")
                return True
            item = get_job_score_table_preview(job_id)
            handler._send_json({"item": item})
            return True
        except ValueError as exc:
            message = str(exc)
            status = HTTPStatus.BAD_REQUEST
            if message == "job not found":
                status = HTTPStatus.NOT_FOUND
            handler._send_json({"error": message}, status=status)
            return True

    return False


def handle_put_job_routes(handler: Any, path: str, user: dict[str, Any]) -> bool:
    if path != "/api/jobs/bulk":
        return False
    if not can_manage_jobs(user):
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="岗位管理",
            operation_type="bulk_save",
            biz_object_type="job",
            operation_result=RESULT_FAILED,
            remark="jobs_forbidden",
        )
        handler._send_forbidden("jobs_forbidden")
        return True
    try:
        payload = handler._parse_json_body()
        items = payload.get("items")
        if not isinstance(items, list):
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="岗位管理",
                operation_type="bulk_save",
                biz_object_type="job",
                operation_result=RESULT_FAILED,
                remark="items 必须为数组",
            )
            handler._send_json({"error": "items 必须为数组"}, status=HTTPStatus.BAD_REQUEST)
            return True
        saved_items = replace_jobs_from_client(items)
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="岗位管理",
            operation_type="bulk_save",
            biz_object_type="job",
            operation_result=RESULT_SUCCESS,
            remark=f"批量保存岗位 {len(saved_items)} 条",
            extra_context={"saved_count": len(saved_items)},
        )
        handler._send_json({"items": list_jobs_for_user(user)})
        return True
    except json.JSONDecodeError:
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="岗位管理",
            operation_type="bulk_save",
            biz_object_type="job",
            operation_result=RESULT_FAILED,
            remark="invalid json",
        )
        handler._send_json({"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
        return True
    except sqlite3.IntegrityError as exc:
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="岗位管理",
            operation_type="bulk_save",
            biz_object_type="job",
            operation_result=RESULT_FAILED,
            remark=f"岗位编码冲突: {exc}",
        )
        handler._send_json({"error": f"岗位编码冲突: {exc}"}, status=HTTPStatus.BAD_REQUEST)
        return True
    except ValueError as exc:
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="岗位管理",
            operation_type="bulk_save",
            biz_object_type="job",
            operation_result=RESULT_FAILED,
            remark=str(exc),
        )
        handler._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        return True


def handle_post_job_routes(handler: Any, path: str, user: dict[str, Any]) -> bool:
    if path == "/api/jobs/score-table/preview":
        if not can_manage_jobs(user):
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="评分表管理",
                operation_type="preview",
                biz_object_type="score_table",
                operation_result=RESULT_FAILED,
                remark="jobs_forbidden",
            )
            handler._send_forbidden("jobs_forbidden")
            return True
        try:
            _, files = handler._parse_multipart_form()
            file_info = files.get("file")
            if not file_info:
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="评分表管理",
                    operation_type="preview",
                    biz_object_type="score_table",
                    operation_result=RESULT_FAILED,
                    remark="请选择评分表文件",
                )
                handler._send_json({"error": "请选择评分表文件"}, status=HTTPStatus.BAD_REQUEST)
                return True
            preview = parse_score_table_preview(
                bytes(file_info.get("content", b"")),
                str(file_info.get("filename", "")),
            )
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="评分表管理",
                operation_type="preview",
                biz_object_type="score_table",
                biz_object_name=str(file_info.get("filename", "")),
                operation_result=RESULT_SUCCESS,
                remark="评分表预览成功",
            )
            handler._send_json({"item": preview}, status=HTTPStatus.OK)
            return True
        except ValueError as exc:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="评分表管理",
                operation_type="preview",
                biz_object_type="score_table",
                operation_result=RESULT_FAILED,
                remark=str(exc),
            )
            handler._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return True

    if path.startswith("/api/jobs/") and path.endswith("/score-table"):
        if not can_manage_jobs(user):
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="评分表管理",
                operation_type="upload",
                biz_object_type="job",
                biz_object_id=unquote(path.removeprefix("/api/jobs/").removesuffix("/score-table")).strip(),
                operation_result=RESULT_FAILED,
                remark="jobs_forbidden",
            )
            handler._send_forbidden("jobs_forbidden")
            return True
        job_id = unquote(path.removeprefix("/api/jobs/").removesuffix("/score-table")).strip()
        try:
            _, files = handler._parse_multipart_form()
            file_info = files.get("file")
            if not file_info:
                record_operation_log_from_request(
                    handler,
                    user=user,
                    operation_module="评分表管理",
                    operation_type="upload",
                    biz_object_type="job",
                    biz_object_id=job_id,
                    operation_result=RESULT_FAILED,
                    remark="请选择评分表文件",
                )
                handler._send_json({"error": "请选择评分表文件"}, status=HTTPStatus.BAD_REQUEST)
                return True
            item = upload_job_score_table(
                job_id=job_id,
                filename=str(file_info.get("filename", "")),
                content=bytes(file_info.get("content", b"")),
                uploaded_by=str(user.get("id", "")),
                operator_name=str(user.get("display_name", "") or user.get("username", "")),
            )
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="评分表管理",
                operation_type="upload",
                biz_object_type="job",
                biz_object_id=str(item.get("job_id", "")),
                biz_object_name=str(item.get("title", "") or item.get("job_code", "")),
                operation_result=RESULT_SUCCESS,
                remark=f"上传评分表：{str(file_info.get('filename', ''))}",
            )
            handler._send_json({"item": item}, status=HTTPStatus.OK)
            return True
        except ValueError as exc:
            message = str(exc)
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="评分表管理",
                operation_type="upload",
                biz_object_type="job",
                biz_object_id=job_id,
                operation_result=RESULT_FAILED,
                remark=message,
            )
            status = HTTPStatus.BAD_REQUEST
            if message == "job not found":
                status = HTTPStatus.NOT_FOUND
            handler._send_json({"error": message}, status=status)
            return True

    return False


def handle_delete_job_routes(handler: Any, path: str, user: dict[str, Any]) -> bool:
    if not (path.startswith("/api/jobs/") and "/score-table/" in path):
        return False
    if not can_manage_jobs(user):
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="评分表管理",
            operation_type="delete",
            biz_object_type="job",
            operation_result=RESULT_FAILED,
            remark="jobs_forbidden",
        )
        handler._send_forbidden("jobs_forbidden")
        return True
    tail = path.removeprefix("/api/jobs/")
    job_part, sep, version_part = tail.partition("/score-table/")
    if not sep:
        handler._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)
        return True
    job_id = unquote(job_part).strip()
    version_no = unquote(version_part).strip()
    try:
        item = delete_job_score_table_version(
            job_id=job_id,
            version_no=version_no,
            operator_name=str(user.get("display_name", "") or user.get("username", "")),
        )
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="评分表管理",
            operation_type="delete",
            biz_object_type="job",
            biz_object_id=str(item.get("job_id", "")),
            biz_object_name=str(item.get("title", "") or item.get("job_code", "")),
            operation_result=RESULT_SUCCESS,
            remark=f"删除评分表版本 V{version_no}",
        )
        handler._send_json({"item": item}, status=HTTPStatus.OK)
        return True
    except ValueError as exc:
        message = str(exc)
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="评分表管理",
            operation_type="delete",
            biz_object_type="job",
            biz_object_id=job_id,
            operation_result=RESULT_FAILED,
            remark=message,
        )
        status = HTTPStatus.BAD_REQUEST
        if message in {"job not found", "template version not found"}:
            status = HTTPStatus.NOT_FOUND
        handler._send_json({"error": message}, status=status)
        return True
