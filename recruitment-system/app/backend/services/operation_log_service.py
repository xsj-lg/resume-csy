from __future__ import annotations

import csv
import io
import json
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from ..repositories.sqlite_helpers import connect_db
from ..utils.time_utils import utc_now_iso
from .role_user_service import user_is_admin

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = ROOT_DIR / "data" / "recruitment.sqlite3"

RESULT_SUCCESS = "success"
RESULT_FAILED = "failed"

REQUEST_SOURCE_LABELS = {
    "/": "工作台",
    "/jobs": "岗位管理页",
    "/users": "用户管理页",
    "/login": "登录页",
    "/static/operations.html": "操作记录页",
}


def _json_dumps(value: Any, default: str) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return default


def _json_loads(raw: str, default: Any) -> Any:
    text = str(raw or "").strip()
    if not text:
        return default
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return default
    return parsed


def ensure_operation_log_table(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS operation_logs (
            log_id TEXT PRIMARY KEY,
            operation_module TEXT NOT NULL,
            operation_type TEXT NOT NULL,
            biz_object_type TEXT NOT NULL,
            biz_object_id TEXT NOT NULL DEFAULT '',
            biz_object_name TEXT NOT NULL DEFAULT '',
            operator_user_id TEXT NOT NULL DEFAULT '',
            operator_name TEXT NOT NULL DEFAULT '',
            operated_at TEXT NOT NULL,
            operation_result TEXT NOT NULL DEFAULT '',
            client_ip TEXT NOT NULL DEFAULT '',
            request_source TEXT NOT NULL DEFAULT '',
            remark TEXT NOT NULL DEFAULT '',
            extra_context_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operation_logs_operated_at
        ON operation_logs(operated_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operation_logs_operator_user_id
        ON operation_logs(operator_user_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operation_logs_module_type
        ON operation_logs(operation_module, operation_type)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operation_logs_object
        ON operation_logs(biz_object_type, biz_object_id)
        """
    )


def _row_to_operation_log(row: Any) -> dict[str, Any]:
    return {
        "log_id": str(row[0] or "").strip(),
        "operation_module": str(row[1] or "").strip(),
        "operation_type": str(row[2] or "").strip(),
        "biz_object_type": str(row[3] or "").strip(),
        "biz_object_id": str(row[4] or "").strip(),
        "biz_object_name": str(row[5] or "").strip(),
        "operator_user_id": str(row[6] or "").strip(),
        "operator_name": str(row[7] or "").strip(),
        "operated_at": str(row[8] or "").strip(),
        "operation_result": str(row[9] or "").strip(),
        "client_ip": str(row[10] or "").strip(),
        "request_source": str(row[11] or "").strip(),
        "remark": str(row[12] or "").strip(),
        "extra_context": _json_loads(str(row[13] or "{}"), {}),
    }


def client_ip_from_handler(handler: Any) -> str:
    forwarded = str(handler.headers.get("X-Forwarded-For", "")).strip()
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    client_address = getattr(handler, "client_address", None)
    if isinstance(client_address, tuple) and client_address:
        return str(client_address[0] or "").strip()
    return ""


def request_source_from_handler(handler: Any) -> str:
    referer = str(handler.headers.get("Referer", "")).strip()
    if referer:
        path = urlparse(referer).path or ""
        if path in REQUEST_SOURCE_LABELS:
            return REQUEST_SOURCE_LABELS[path]
        if path:
            return path
    path = str(getattr(handler, "path", "") or "").strip()
    if path in REQUEST_SOURCE_LABELS:
        return REQUEST_SOURCE_LABELS[path]
    return path or "unknown"


def record_operation_log(
    *,
    operation_module: str,
    operation_type: str,
    biz_object_type: str,
    biz_object_id: str = "",
    biz_object_name: str = "",
    operator_user_id: str = "",
    operator_name: str = "",
    operation_result: str = RESULT_SUCCESS,
    client_ip: str = "",
    request_source: str = "",
    remark: str = "",
    extra_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    log_id = f"log_{uuid.uuid4().hex}"
    operated_at = utc_now_iso()
    item = {
        "log_id": log_id,
        "operation_module": str(operation_module or "").strip(),
        "operation_type": str(operation_type or "").strip(),
        "biz_object_type": str(biz_object_type or "").strip(),
        "biz_object_id": str(biz_object_id or "").strip(),
        "biz_object_name": str(biz_object_name or "").strip(),
        "operator_user_id": str(operator_user_id or "").strip(),
        "operator_name": str(operator_name or "").strip(),
        "operated_at": operated_at,
        "operation_result": str(operation_result or "").strip() or RESULT_SUCCESS,
        "client_ip": str(client_ip or "").strip(),
        "request_source": str(request_source or "").strip(),
        "remark": str(remark or "").strip(),
        "extra_context": extra_context if isinstance(extra_context, dict) else {},
    }
    with connect_db(DB_PATH) as conn:
        ensure_operation_log_table(conn)
        conn.execute(
            """
            INSERT INTO operation_logs (
                log_id, operation_module, operation_type, biz_object_type,
                biz_object_id, biz_object_name, operator_user_id, operator_name,
                operated_at, operation_result, client_ip, request_source,
                remark, extra_context_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["log_id"],
                item["operation_module"],
                item["operation_type"],
                item["biz_object_type"],
                item["biz_object_id"],
                item["biz_object_name"],
                item["operator_user_id"],
                item["operator_name"],
                item["operated_at"],
                item["operation_result"],
                item["client_ip"],
                item["request_source"],
                item["remark"],
                _json_dumps(item["extra_context"], "{}"),
                operated_at,
            ),
        )
        conn.commit()
    return item


def record_operation_log_from_request(
    handler: Any,
    *,
    user: dict[str, Any] | None,
    operation_module: str,
    operation_type: str,
    biz_object_type: str,
    biz_object_id: str = "",
    biz_object_name: str = "",
    operation_result: str = RESULT_SUCCESS,
    remark: str = "",
    extra_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return record_operation_log(
        operation_module=operation_module,
        operation_type=operation_type,
        biz_object_type=biz_object_type,
        biz_object_id=biz_object_id,
        biz_object_name=biz_object_name,
        operator_user_id=str((user or {}).get("id", "")).strip(),
        operator_name=str((user or {}).get("display_name", "") or (user or {}).get("username", "")).strip(),
        operation_result=operation_result,
        client_ip=client_ip_from_handler(handler),
        request_source=request_source_from_handler(handler),
        remark=remark,
        extra_context=extra_context,
    )


def can_view_operation_logs(user: dict[str, Any] | None) -> bool:
    return user_is_admin(user)


def parse_operation_log_filters(query: str) -> dict[str, str]:
    params = parse_qs(query or "", keep_blank_values=False)

    def _pick(key: str) -> str:
        return str((params.get(key) or [""])[0] or "").strip()

    return {
        "keyword": _pick("keyword"),
        "module": _pick("module"),
        "operation_type": _pick("operation_type"),
        "operator_user_id": _pick("operator_user_id"),
        "operator_name": _pick("operator_name"),
        "biz_object_type": _pick("biz_object_type"),
        "biz_object_id": _pick("biz_object_id"),
        "biz_object_name": _pick("biz_object_name"),
        "operation_result": _pick("operation_result"),
        "request_source": _pick("request_source"),
        "operated_from": _pick("operated_from"),
        "operated_to": _pick("operated_to"),
        "format": _pick("format").lower(),
    }


def list_operation_logs(filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
    normalized = filters or {}
    where: list[str] = []
    values: list[str] = []

    keyword = str(normalized.get("keyword", "")).strip()
    if keyword:
        where.append(
            """
            (
                log_id LIKE ? OR biz_object_id LIKE ? OR biz_object_name LIKE ? OR
                operator_user_id LIKE ? OR operator_name LIKE ? OR remark LIKE ? OR
                operation_module LIKE ? OR operation_type LIKE ? OR request_source LIKE ?
            )
            """
        )
        like = f"%{keyword}%"
        values.extend([like] * 9)
    if normalized.get("module"):
        where.append("operation_module = ?")
        values.append(str(normalized["module"]))
    if normalized.get("operation_type"):
        where.append("operation_type = ?")
        values.append(str(normalized["operation_type"]))
    if normalized.get("operator_user_id"):
        where.append("operator_user_id = ?")
        values.append(str(normalized["operator_user_id"]))
    if normalized.get("operator_name"):
        where.append("operator_name = ?")
        values.append(str(normalized["operator_name"]))
    if normalized.get("biz_object_type"):
        where.append("biz_object_type = ?")
        values.append(str(normalized["biz_object_type"]))
    if normalized.get("biz_object_id"):
        where.append("biz_object_id = ?")
        values.append(str(normalized["biz_object_id"]))
    if normalized.get("biz_object_name"):
        where.append("biz_object_name = ?")
        values.append(str(normalized["biz_object_name"]))
    if normalized.get("operation_result"):
        where.append("operation_result = ?")
        values.append(str(normalized["operation_result"]))
    if normalized.get("request_source"):
        where.append("request_source = ?")
        values.append(str(normalized["request_source"]))
    if normalized.get("operated_from"):
        where.append("date(operated_at) >= date(?)")
        values.append(str(normalized["operated_from"]))
    if normalized.get("operated_to"):
        where.append("date(operated_at) <= date(?)")
        values.append(str(normalized["operated_to"]))

    sql = """
        SELECT log_id, operation_module, operation_type, biz_object_type,
               biz_object_id, biz_object_name, operator_user_id, operator_name,
               operated_at, operation_result, client_ip, request_source,
               remark, extra_context_json
        FROM operation_logs
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY datetime(operated_at) DESC, created_at DESC, log_id DESC"

    with connect_db(DB_PATH) as conn:
        ensure_operation_log_table(conn)
        rows = conn.execute(sql, tuple(values)).fetchall()
        conn.commit()
    return [_row_to_operation_log(row) for row in rows]


def get_operation_log(log_id: str) -> dict[str, Any] | None:
    normalized = str(log_id or "").strip()
    if not normalized:
        return None
    with connect_db(DB_PATH) as conn:
        ensure_operation_log_table(conn)
        row = conn.execute(
            """
            SELECT log_id, operation_module, operation_type, biz_object_type,
                   biz_object_id, biz_object_name, operator_user_id, operator_name,
                   operated_at, operation_result, client_ip, request_source,
                   remark, extra_context_json
            FROM operation_logs
            WHERE log_id = ?
            """,
            (normalized,),
        ).fetchone()
        conn.commit()
    if row is None:
        return None
    return _row_to_operation_log(row)


def export_operation_logs(filters: dict[str, str] | None = None, export_format: str = "json") -> tuple[str, str, bytes]:
    items = list_operation_logs(filters or {})
    fmt = (export_format or "json").strip().lower()
    timestamp = utc_now_iso().replace(":", "-")
    if fmt == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        header = [
            "log_id",
            "operation_module",
            "operation_type",
            "biz_object_type",
            "biz_object_id",
            "biz_object_name",
            "operator_user_id",
            "operator_name",
            "operated_at",
            "operation_result",
            "client_ip",
            "request_source",
            "remark",
            "extra_context_json",
        ]
        writer.writerow(header)
        for item in items:
            writer.writerow(
                [
                    item["log_id"],
                    item["operation_module"],
                    item["operation_type"],
                    item["biz_object_type"],
                    item["biz_object_id"],
                    item["biz_object_name"],
                    item["operator_user_id"],
                    item["operator_name"],
                    item["operated_at"],
                    item["operation_result"],
                    item["client_ip"],
                    item["request_source"],
                    item["remark"],
                    json.dumps(item["extra_context"], ensure_ascii=False),
                ]
            )
        return (
            f"operation-logs-{timestamp}.csv",
            "text/csv; charset=utf-8",
            buffer.getvalue().encode("utf-8"),
        )

    return (
        f"operation-logs-{timestamp}.json",
        "application/json; charset=utf-8",
        json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8"),
    )
