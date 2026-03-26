from __future__ import annotations

import json
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..services.recruitment_service import (
    MAX_UPLOAD_BYTES,
    SESSION_COOKIE_NAME,
    get_current_user_by_session,
    init_db,
)
from .auth_controller import (
    handle_get_auth_me,
    handle_post_login,
    handle_post_logout,
    handle_put_change_password,
)
from .candidate_controller import (
    handle_delete_candidate_routes,
    handle_get_candidate_routes,
    handle_post_candidate_routes,
    handle_put_candidate_routes,
)
from .job_controller import (
    handle_delete_job_routes,
    handle_get_job_routes,
    handle_post_job_routes,
    handle_put_job_routes,
)
from .operation_log_controller import handle_get_operation_log_routes
from .system_controller import handle_public_get
from .user_role_controller import (
    handle_get_user_role_routes,
    handle_post_user_role_routes,
    handle_put_user_role_routes,
)


class ResumeHandler(BaseHTTPRequestHandler):
    server_version = "ResumeScreeningHTTP/0.2"

    def _send_json(
        self,
        payload: dict[str, Any],
        status: int = HTTPStatus.OK,
        headers: list[tuple[str, str]] | None = None,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if headers:
            for key, value in headers:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)
            return
        content = path.read_bytes()
        self._send_bytes(content, content_type=content_type)

    def _send_bytes(
        self,
        content: bytes,
        *,
        content_type: str,
        status: int = HTTPStatus.OK,
        headers: list[tuple[str, str]] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        if headers:
            for key, value in headers:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _parse_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length)
        return json.loads(raw.decode("utf-8"))

    def _parse_multipart_form(self) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
        content_type = self.headers.get("Content-Type", "")
        boundary_match = re.search(r'boundary="?([^";]+)"?', content_type)
        if not content_type.startswith("multipart/form-data") or not boundary_match:
            raise ValueError("invalid multipart content-type")

        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return {}, {}
        if content_length > MAX_UPLOAD_BYTES:
            raise ValueError("上传文件过大")

        raw = self.rfile.read(content_length)
        boundary = ("--" + boundary_match.group(1)).encode("utf-8")
        parts = raw.split(boundary)

        fields: dict[str, str] = {}
        files: dict[str, dict[str, Any]] = {}
        for part in parts:
            if not part or part in {b"--", b"--\r\n", b"\r\n"}:
                continue
            chunk = part
            if chunk.startswith(b"\r\n"):
                chunk = chunk[2:]
            if chunk.endswith(b"\r\n"):
                chunk = chunk[:-2]
            if chunk.endswith(b"--"):
                chunk = chunk[:-2]

            header_blob, sep, body = chunk.partition(b"\r\n\r\n")
            if not sep:
                continue

            headers: dict[str, str] = {}
            for line in header_blob.decode("utf-8", errors="ignore").split("\r\n"):
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

            disposition = headers.get("content-disposition", "")
            name_match = re.search(r'name="([^"]+)"', disposition)
            if not name_match:
                continue
            field_name = name_match.group(1)
            filename_match = re.search(r'filename="([^"]*)"', disposition)
            if filename_match and filename_match.group(1):
                files[field_name] = {
                    "filename": filename_match.group(1),
                    "content": body,
                    "content_type": headers.get("content-type", ""),
                }
            else:
                fields[field_name] = body.decode("utf-8", errors="ignore").strip()

        return fields, files

    def _cookie_headers(self, token: str = "", max_age: int | None = None) -> list[tuple[str, str]]:
        parts = [f"{SESSION_COOKIE_NAME}={token}", "Path=/", "HttpOnly", "SameSite=Lax"]
        if max_age is not None:
            parts.append(f"Max-Age={max_age}")
        return [("Set-Cookie", "; ".join(parts))]

    def _parse_cookies(self) -> dict[str, str]:
        header = self.headers.get("Cookie", "")
        out: dict[str, str] = {}
        if not header:
            return out
        for item in header.split(";"):
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            out[key.strip()] = value.strip()
        return out

    def _session_token(self) -> str:
        return self._parse_cookies().get(SESSION_COOKIE_NAME, "")

    def _current_user(self) -> dict[str, Any] | None:
        return get_current_user_by_session(self._session_token())

    def _send_unauthorized(self) -> None:
        self._send_json({"error": "unauthorized"}, status=HTTPStatus.UNAUTHORIZED)

    def _send_forbidden(self, message: str = "forbidden") -> None:
        self._send_json({"error": message}, status=HTTPStatus.FORBIDDEN)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if handle_public_get(self, path):
            return

        if not path.startswith("/api/"):
            self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)
            return

        user = self._current_user()
        if user is None:
            self._send_unauthorized()
            return

        if int(user.get("must_change_password", 0)) == 1 and path not in {"/api/auth/me"}:
            self._send_forbidden("must_change_password")
            return

        if handle_get_auth_me(self, path, user):
            return
        if handle_get_user_role_routes(self, path, user):
            return
        if handle_get_operation_log_routes(self, parsed, path, user):
            return
        if handle_get_job_routes(self, path, user):
            return
        if handle_get_candidate_routes(self, parsed, path, user):
            return

        self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)

    def do_PUT(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        _ = parsed

        user = self._current_user()
        if user is None:
            self._send_unauthorized()
            return

        if handle_put_change_password(self, path, user):
            return

        if int(user.get("must_change_password", 0)) == 1:
            self._send_forbidden("must_change_password")
            return

        if handle_put_user_role_routes(self, path, user):
            return
        if handle_put_candidate_routes(self, path, user):
            return
        if handle_put_job_routes(self, path, user):
            return

        self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        _ = parsed

        user = self._current_user()
        if user is None:
            self._send_unauthorized()
            return

        if int(user.get("must_change_password", 0)) == 1:
            self._send_forbidden("must_change_password")
            return

        if handle_delete_job_routes(self, path, user):
            return
        if handle_delete_candidate_routes(self, path, user):
            return

        self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        _ = parsed

        if handle_post_login(self, path):
            return

        user = self._current_user()
        if user is None:
            self._send_unauthorized()
            return

        if handle_post_logout(self, path, self._session_token()):
            return

        if int(user.get("must_change_password", 0)) == 1:
            self._send_forbidden("must_change_password")
            return

        if handle_post_candidate_routes(self, path, user):
            return
        if handle_post_user_role_routes(self, path, user):
            return
        if handle_post_job_routes(self, path, user):
            return

        self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)


def run() -> None:
    init_db()
    host = os.environ.get("RESUME_APP_HOST", "127.0.0.1")
    port = int(os.environ.get("RESUME_APP_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), ResumeHandler)
    print(f"Resume screening app running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
