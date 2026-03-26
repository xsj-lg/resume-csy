from __future__ import annotations

from http import HTTPStatus
from typing import Any

from ..services.recruitment_service import STATIC_DIR, utc_now_iso


def handle_public_get(handler: Any, path: str) -> bool:
    if path == "/api/healthz":
        handler._send_json({"ok": True, "time": utc_now_iso()})
        return True

    if path == "/":
        handler._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        return True

    if path == "/login":
        handler._send_file(STATIC_DIR / "login.html", "text/html; charset=utf-8")
        return True

    if path == "/users":
        handler._send_file(STATIC_DIR / "users.html", "text/html; charset=utf-8")
        return True

    if path == "/jobs":
        handler._send_file(STATIC_DIR / "jobs.html", "text/html; charset=utf-8")
        return True

    if path.startswith("/static/"):
        local_path = path.removeprefix("/static/")
        file_path = (STATIC_DIR / local_path).resolve()
        if file_path.parent != STATIC_DIR.resolve():
            handler._send_json({"error": "invalid static path"}, status=HTTPStatus.BAD_REQUEST)
            return True

        content_type = "text/plain; charset=utf-8"
        if file_path.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif file_path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif file_path.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        handler._send_file(file_path, content_type)
        return True

    return False

