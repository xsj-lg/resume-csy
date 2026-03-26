from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from ..repositories.sqlite_helpers import connect_db
from ..services.recruitment_service import (
    DB_PATH,
    RESULT_FAILED,
    RESULT_SUCCESS,
    SESSION_TTL_SECONDS,
    change_password,
    clear_expired_sessions,
    create_session,
    delete_session,
    get_current_user_by_session,
    get_user_by_username,
    record_operation_log,
    record_operation_log_from_request,
    validate_change_password_payload,
    validate_login_payload,
    verify_password,
)


def handle_get_auth_me(handler: Any, path: str, user: dict[str, Any]) -> bool:
    if path != "/api/auth/me":
        return False
    handler._send_json({"item": user})
    return True


def handle_put_change_password(handler: Any, path: str, user: dict[str, Any]) -> bool:
    if path != "/api/auth/change-password":
        return False
    try:
        payload = handler._parse_json_body()
        cleaned, error = validate_change_password_payload(payload)
        if cleaned is None:
            record_operation_log_from_request(
                handler,
                user=user,
                operation_module="用户与权限",
                operation_type="change_password",
                biz_object_type="user",
                biz_object_id=str(user.get("id", "")),
                biz_object_name=str(user.get("display_name", "") or user.get("username", "")),
                operation_result=RESULT_FAILED,
                remark=error,
            )
            handler._send_json({"error": error}, status=HTTPStatus.BAD_REQUEST)
            return True
        updated_user = change_password(
            user["id"],
            cleaned["old_password"],
            cleaned["new_password"],
        )
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="用户与权限",
            operation_type="change_password",
            biz_object_type="user",
            biz_object_id=str(updated_user.get("id", "")),
            biz_object_name=str(updated_user.get("display_name", "") or updated_user.get("username", "")),
            operation_result=RESULT_SUCCESS,
            remark="用户修改本人密码",
        )
        handler._send_json({"item": updated_user})
        return True
    except json.JSONDecodeError:
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="用户与权限",
            operation_type="change_password",
            biz_object_type="user",
            biz_object_id=str(user.get("id", "")),
            biz_object_name=str(user.get("display_name", "") or user.get("username", "")),
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
            operation_type="change_password",
            biz_object_type="user",
            biz_object_id=str(user.get("id", "")),
            biz_object_name=str(user.get("display_name", "") or user.get("username", "")),
            operation_result=RESULT_FAILED,
            remark=str(exc),
        )
        handler._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        return True


def handle_post_login(handler: Any, path: str) -> bool:
    if path != "/api/auth/login":
        return False
    try:
        payload = handler._parse_json_body()
        cleaned, error = validate_login_payload(payload)
        if cleaned is None:
            record_operation_log(
                operation_module="系统使用",
                operation_type="login",
                biz_object_type="session",
                biz_object_name=str(payload.get("username", "")).strip() if isinstance(payload, dict) else "",
                operator_name=str(payload.get("username", "")).strip() if isinstance(payload, dict) else "",
                operation_result=RESULT_FAILED,
                client_ip=str(getattr(handler, "client_address", ("",))[0] or ""),
                request_source=str(handler.headers.get("Referer", "") or "/login"),
                remark=error,
            )
            handler._send_json({"error": error}, status=HTTPStatus.BAD_REQUEST)
            return True

        with connect_db(DB_PATH) as conn:
            clear_expired_sessions(conn)
            account = get_user_by_username(conn, cleaned["username"])
            if (
                account is None
                or int(account.get("is_active", 0)) != 1
                or not verify_password(cleaned["password"], account.get("password_hash", ""))
            ):
                record_operation_log(
                    operation_module="系统使用",
                    operation_type="login",
                    biz_object_type="session",
                    biz_object_name=cleaned["username"],
                    operator_name=cleaned["username"],
                    operation_result=RESULT_FAILED,
                    client_ip=str(getattr(handler, "client_address", ("",))[0] or ""),
                    request_source=str(handler.headers.get("Referer", "") or "/login"),
                    remark="用户名或密码错误",
                )
                handler._send_json({"error": "用户名或密码错误"}, status=HTTPStatus.UNAUTHORIZED)
                return True
            token, _ = create_session(conn, account["id"])
            conn.commit()

        user = get_current_user_by_session(token)
        if user is None:
            record_operation_log(
                operation_module="系统使用",
                operation_type="login",
                biz_object_type="session",
                biz_object_name=cleaned["username"],
                operator_name=cleaned["username"],
                operation_result=RESULT_FAILED,
                client_ip=str(getattr(handler, "client_address", ("",))[0] or ""),
                request_source=str(handler.headers.get("Referer", "") or "/login"),
                remark="登录失败",
            )
            handler._send_json({"error": "登录失败"}, status=HTTPStatus.UNAUTHORIZED)
            return True
        record_operation_log_from_request(
            handler,
            user=user,
            operation_module="系统使用",
            operation_type="login",
            biz_object_type="session",
            biz_object_id=token,
            biz_object_name=str(user.get("display_name", "") or user.get("username", "")),
            operation_result=RESULT_SUCCESS,
            remark="用户登录成功",
        )
        handler._send_json(
            {"item": user},
            headers=handler._cookie_headers(token=token, max_age=SESSION_TTL_SECONDS),
        )
        return True
    except json.JSONDecodeError:
        record_operation_log(
            operation_module="系统使用",
            operation_type="login",
            biz_object_type="session",
            operation_result=RESULT_FAILED,
            client_ip=str(getattr(handler, "client_address", ("",))[0] or ""),
            request_source=str(handler.headers.get("Referer", "") or "/login"),
            remark="invalid json",
        )
        handler._send_json({"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
        return True


def handle_post_logout(handler: Any, path: str, session_token: str) -> bool:
    if path != "/api/auth/logout":
        return False
    current_user = get_current_user_by_session(session_token)
    with connect_db(DB_PATH) as conn:
        delete_session(conn, session_token)
        conn.commit()
    if current_user is not None:
        record_operation_log_from_request(
            handler,
            user=current_user,
            operation_module="系统使用",
            operation_type="logout",
            biz_object_type="session",
            biz_object_id=session_token,
            biz_object_name=str(current_user.get("display_name", "") or current_user.get("username", "")),
            operation_result=RESULT_SUCCESS,
            remark="用户退出登录",
        )
    handler._send_json(
        {"ok": True},
        headers=handler._cookie_headers(token="", max_age=0),
    )
    return True
