from __future__ import annotations

import json
import sqlite3
from http import HTTPStatus
from typing import Any
from urllib.parse import unquote

from ..services.recruitment_service import (
    RESULT_FAILED,
    RESULT_SUCCESS,
    create_user,
    list_active_user_options,
    list_role_definitions,
    list_users,
    public_llm_runtime_config,
    record_operation_log_from_request,
    reset_user_password,
    update_user,
    user_is_admin,
)


def handle_get_user_role_routes(handler: Any, path: str, user: dict[str, Any]) -> bool:
    if path == "/api/roles/definitions":
        handler._send_json({"items": list_role_definitions()})
        return True

    if path == "/api/users":
        if not user_is_admin(user):
            handler._send_forbidden("admin_only")
            return True
        handler._send_json({"items": list_users()})
        return True

    if path == "/api/users/options":
        handler._send_json({"items": list_active_user_options()})
        return True

    if path == "/api/settings/llm-config":
        if not user_is_admin(user):
            handler._send_forbidden("admin_only")
            return True
        handler._send_json({"item": public_llm_runtime_config()})
        return True

    return False


def handle_put_user_role_routes(handler: Any, path: str, user: dict[str, Any]) -> bool:
    if not path.startswith("/api/users/"):
        return False
    if not user_is_admin(user):
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="用户与权限",
            operation_type="update",
            biz_object_type="user",
            biz_object_id=unquote(path.removeprefix("/api/users/")),
            operation_result=RESULT_FAILED,
            remark="admin_only",
        )
        handler._send_forbidden("admin_only")
        return True
    user_id = unquote(path.removeprefix("/api/users/"))
    try:
        payload = handler._parse_json_body()
        updated_user = update_user(user_id, payload, user["id"])
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="用户与权限",
            operation_type="update",
            biz_object_type="user",
            biz_object_id=str(updated_user.get("id", "")),
            biz_object_name=str(updated_user.get("display_name", "") or updated_user.get("username", "")),
            operation_result=RESULT_SUCCESS,
            remark="更新用户信息",
            extra_context={"role_code": updated_user.get("role_code", ""), "department_scope": updated_user.get("department_scope", "")},
        )
        handler._send_json({"item": updated_user})
        return True
    except json.JSONDecodeError:
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="用户与权限",
            operation_type="update",
            biz_object_type="user",
            biz_object_id=user_id,
            operation_result=RESULT_FAILED,
            remark="invalid json",
        )
        handler._send_json({"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
        return True
    except ValueError as exc:
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="用户与权限",
            operation_type="update",
            biz_object_type="user",
            biz_object_id=user_id,
            operation_result=RESULT_FAILED,
            remark=str(exc),
        )
        handler._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        return True


def handle_post_user_role_routes(handler: Any, path: str, user: dict[str, Any]) -> bool:
    if path == "/api/users":
        if not user_is_admin(user):
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="用户与权限",
                operation_type="create",
                biz_object_type="user",
                operation_result=RESULT_FAILED,
                remark="admin_only",
            )
            handler._send_forbidden("admin_only")
            return True
        try:
            payload = handler._parse_json_body()
            created = create_user(payload)
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="用户与权限",
                operation_type="create",
                biz_object_type="user",
                biz_object_id=str(created.get("id", "")),
                biz_object_name=str(created.get("display_name", "") or created.get("username", "")),
                operation_result=RESULT_SUCCESS,
                remark="创建用户",
                extra_context={"role_code": created.get("role_code", ""), "department_scope": created.get("department_scope", "")},
            )
            handler._send_json({"item": created})
            return True
        except json.JSONDecodeError:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="用户与权限",
                operation_type="create",
                biz_object_type="user",
                operation_result=RESULT_FAILED,
                remark="invalid json",
            )
            handler._send_json({"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
            return True
        except ValueError as exc:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="用户与权限",
                operation_type="create",
                biz_object_type="user",
                biz_object_name=str(payload.get("username", "")).strip() if isinstance(payload, dict) else "",
                operation_result=RESULT_FAILED,
                remark=str(exc),
            )
            handler._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return True

    if path.startswith("/api/users/") and path.endswith("/reset-password"):
        if not user_is_admin(user):
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="用户与权限",
                operation_type="reset_password",
                biz_object_type="user",
                biz_object_id=unquote(path.removeprefix("/api/users/").removesuffix("/reset-password")),
                operation_result=RESULT_FAILED,
                remark="admin_only",
            )
            handler._send_forbidden("admin_only")
            return True
        user_id = unquote(path.removeprefix("/api/users/").removesuffix("/reset-password"))
        try:
            payload = handler._parse_json_body()
            new_password = str(payload.get("new_password", "")).strip()
            updated = reset_user_password(user_id, new_password)
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="用户与权限",
                operation_type="reset_password",
                biz_object_type="user",
                biz_object_id=str(updated.get("id", "")),
                biz_object_name=str(updated.get("display_name", "") or updated.get("username", "")),
                operation_result=RESULT_SUCCESS,
                remark="管理员重置用户密码",
            )
            handler._send_json({"item": updated})
            return True
        except json.JSONDecodeError:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="用户与权限",
                operation_type="reset_password",
                biz_object_type="user",
                biz_object_id=user_id,
                operation_result=RESULT_FAILED,
                remark="invalid json",
            )
            handler._send_json({"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
            return True
        except ValueError as exc:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="用户与权限",
                operation_type="reset_password",
                biz_object_type="user",
                biz_object_id=user_id,
                operation_result=RESULT_FAILED,
                remark=str(exc),
            )
            handler._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return True

    return False
