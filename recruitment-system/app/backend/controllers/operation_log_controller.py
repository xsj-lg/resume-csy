from __future__ import annotations

from http import HTTPStatus
from typing import Any
from urllib.parse import unquote

from ..services.recruitment_service import (
    can_view_operation_logs,
    export_operation_logs,
    get_operation_log,
    list_operation_logs,
    parse_operation_log_filters,
)


def handle_get_operation_log_routes(handler: Any, parsed: Any, path: str, user: dict[str, Any]) -> bool:
    if path == "/api/operation-logs/export":
        if not can_view_operation_logs(user):
            handler._send_forbidden("operation_logs_forbidden")
            return True
        filters = parse_operation_log_filters(parsed.query)
        export_format = filters.get("format") or "json"
        filename, content_type, body = export_operation_logs(filters, export_format=export_format)
        handler._send_bytes(
            body,
            content_type=content_type,
            headers=[("Content-Disposition", f'attachment; filename="{filename}"')],
        )
        return True

    if path == "/api/operation-logs":
        if not can_view_operation_logs(user):
            handler._send_forbidden("operation_logs_forbidden")
            return True
        filters = parse_operation_log_filters(parsed.query)
        items = list_operation_logs(filters)
        handler._send_json(
            {
                "items": items,
                "total_count": len(items),
                "filters": filters,
            }
        )
        return True

    if path.startswith("/api/operation-logs/"):
        if not can_view_operation_logs(user):
            handler._send_forbidden("operation_logs_forbidden")
            return True
        log_id = unquote(path.removeprefix("/api/operation-logs/")).strip()
        item = get_operation_log(log_id)
        if item is None:
            handler._send_json({"error": "operation log not found"}, status=HTTPStatus.NOT_FOUND)
            return True
        handler._send_json({"item": item})
        return True

    return False
