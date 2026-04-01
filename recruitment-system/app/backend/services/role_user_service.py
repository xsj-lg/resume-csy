from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from pathlib import Path
from typing import Any

from ..repositories.sqlite_helpers import connect_db
from ..utils.time_utils import now_ts, utc_now_iso

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = ROOT_DIR / "data" / "recruitment.sqlite3"

SESSION_COOKIE_NAME = "RS_SESSION"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_DISPLAY_NAME = "系统管理员"
DEFAULT_ADMIN_PASSWORD = os.environ.get("RESUME_APP_ADMIN_PASSWORD", "admin123456")

ROLE_ADMINISTRATOR = "administrator"
ROLE_HR_SPECIALIST = "hr_specialist"
ROLE_PERSONNEL_MANAGER = "personnel_manager"
ROLE_ENGINEERING_MANAGER = "engineering_manager"
ROLE_ALGORITHM_MANAGER = "algorithm_manager"
DEFAULT_NON_ADMIN_ROLE = ROLE_HR_SPECIALIST

DEPARTMENT_SCOPES = {"销售部", "研发部", "算法部", "项目部", "人事部"}
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")

ROLE_CODE_ALIASES = {
    "admin": ROLE_ADMINISTRATOR,
    "administrator": ROLE_ADMINISTRATOR,
    "hr": ROLE_HR_SPECIALIST,
    "hr_specialist": ROLE_HR_SPECIALIST,
    "personnel_manager": ROLE_PERSONNEL_MANAGER,
    "hr_manager": ROLE_PERSONNEL_MANAGER,
    "engineering_manager": ROLE_ENGINEERING_MANAGER,
    "rd_manager": ROLE_ENGINEERING_MANAGER,
    "dev_manager": ROLE_ENGINEERING_MANAGER,
    "algorithm_manager": ROLE_ALGORITHM_MANAGER,
    "algo_manager": ROLE_ALGORITHM_MANAGER,
    "interviewer": ROLE_ENGINEERING_MANAGER,
    "hiring_manager": ROLE_PERSONNEL_MANAGER,
}
ROLE_DEFINITIONS: dict[str, dict[str, Any]] = {
    ROLE_ADMINISTRATOR: {
        "role_code": ROLE_ADMINISTRATOR,
        "role_name": "管理员",
        "responsibilities": ["管理系统用户", "分配角色权限", "查看全部岗位和候选人", "查看系统日志"],
        "permission_features": ["全部菜单可见", "可新增/编辑/禁用用户", "可配置角色", "可查看所有操作记录"],
    },
    ROLE_HR_SPECIALIST: {
        "role_code": ROLE_HR_SPECIALIST,
        "role_name": "HR / 招聘专员",
        "responsibilities": ["创建岗位", "上传简历", "初筛候选人", "推进流程", "安排面试", "查看各轮反馈"],
        "permission_features": [
            "可查看自己负责岗位下的所有候选人",
            "可修改候选人流程状态",
            "可录入初筛意见和评分",
            "可查看面试评价",
            "一般不可修改系统权限配置",
        ],
    },
    ROLE_PERSONNEL_MANAGER: {
        "role_code": ROLE_PERSONNEL_MANAGER,
        "role_name": "人事经理",
        "responsibilities": ["查看全部候选人", "负责 HR 面评价", "参与流程决策"],
        "permission_features": ["可查看全部候选人", "可填写 HR 面评价", "不可管理系统用户", "不可上传简历"],
    },
    ROLE_ENGINEERING_MANAGER: {
        "role_code": ROLE_ENGINEERING_MANAGER,
        "role_name": "研发经理",
        "responsibilities": ["查看被分配到一面或二面的候选人", "填写自己负责轮次的面评"],
        "permission_features": ["只能看一面/二面任一阶段指派给自己的候选人", "只能填写自己负责的一面/二面面评", "不可管理用户与岗位"],
    },
    ROLE_ALGORITHM_MANAGER: {
        "role_code": ROLE_ALGORITHM_MANAGER,
        "role_name": "算法经理",
        "responsibilities": ["查看被分配到一面或二面的候选人", "填写自己负责轮次的面评"],
        "permission_features": ["只能看一面/二面任一阶段指派给自己的候选人", "只能填写自己负责的一面/二面面评", "不可管理用户与岗位"],
    },
}
ROLE_ORDER = [
    ROLE_ADMINISTRATOR,
    ROLE_HR_SPECIALIST,
    ROLE_PERSONNEL_MANAGER,
    ROLE_ENGINEERING_MANAGER,
    ROLE_ALGORITHM_MANAGER,
]


def normalize_role_code(value: str) -> str:
    key = (value or "").strip().lower()
    return ROLE_CODE_ALIASES.get(key, "")


def role_code_from_is_admin(is_admin: int) -> str:
    return ROLE_ADMINISTRATOR if int(is_admin) == 1 else DEFAULT_NON_ADMIN_ROLE


def role_name(role_code: str) -> str:
    normalized = normalize_role_code(role_code)
    if normalized:
        return str(ROLE_DEFINITIONS[normalized]["role_name"])
    return ""


def user_role_code(user: dict[str, Any] | None) -> str:
    if not user:
        return ""
    normalized = normalize_role_code(str(user.get("role_code", "")))
    if normalized:
        return normalized
    return role_code_from_is_admin(int(user.get("is_admin", 0)))


def user_is_admin(user: dict[str, Any] | None) -> bool:
    return user_role_code(user) == ROLE_ADMINISTRATOR


def can_export_resume_results(user: dict[str, Any] | None) -> bool:
    role_code = user_role_code(user)
    return role_code in {ROLE_ADMINISTRATOR, ROLE_PERSONNEL_MANAGER}


def list_role_definitions() -> list[dict[str, Any]]:
    return [ROLE_DEFINITIONS[role_code].copy() for role_code in ROLE_ORDER]


def normalize_department_scope(value: str) -> str:
    text = (value or "").strip()
    return text if text in DEPARTMENT_SCOPES else ""


def user_department_scope(user: dict[str, Any] | None) -> str:
    if not user:
        return ""
    return normalize_department_scope(str(user.get("department_scope", "")))


def parse_bool_flag(
    value: Any,
    *,
    default: bool,
    field_name: str,
) -> tuple[int | None, str]:
    if value is None:
        return (1 if default else 0), ""
    if isinstance(value, bool):
        return (1 if value else 0), ""
    if isinstance(value, int):
        if value in {0, 1}:
            return value, ""
        return None, f"{field_name} 必须为布尔值或 0/1"
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true"}:
            return 1, ""
        if text in {"0", "false"}:
            return 0, ""
    return None, f"{field_name} 必须为布尔值或 0/1"


def normalize_username(value: str) -> str:
    return (value or "").strip().lower()


def validate_username(value: str) -> bool:
    return bool(USERNAME_PATTERN.fullmatch(normalize_username(value)))


def hash_password(password: str) -> str:
    password_bytes = (password or "").encode("utf-8")
    salt = secrets.token_bytes(16)
    iterations = 200000
    digest = hashlib.pbkdf2_hmac("sha256", password_bytes, salt, iterations)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${iterations}${salt_b64}${digest_b64}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_b64, digest_b64 = encoded.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    try:
        iterations = int(iterations_text)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(digest_b64.encode("ascii"))
    except (ValueError, TypeError):
        return False
    password_bytes = (password or "").encode("utf-8")
    actual = hashlib.pbkdf2_hmac("sha256", password_bytes, salt, iterations)
    return hmac.compare_digest(actual, expected)


def seed_default_admin(conn: sqlite3.Connection) -> None:
    count_row = conn.execute("SELECT COUNT(1) FROM users").fetchone()
    if count_row and int(count_row[0]) > 0:
        return

    now = utc_now_iso()
    conn.execute(
        """
        INSERT INTO users (
            id, username, display_name, password_hash, is_active, is_admin,
            role_code, department_scope, must_change_password, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 1, 1, ?, '', 1, ?, ?)
        """,
        (
            secrets.token_hex(16),
            DEFAULT_ADMIN_USERNAME,
            DEFAULT_ADMIN_DISPLAY_NAME,
            hash_password(DEFAULT_ADMIN_PASSWORD),
            ROLE_ADMINISTRATOR,
            now,
            now,
        ),
    )


def clear_expired_sessions(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("DELETE FROM user_sessions WHERE expires_at <= ?", (now_ts(),))
    except sqlite3.OperationalError as exc:
        if "locked" in str(exc).lower():
            return
        raise


def sanitize_user_row(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    role_code = normalize_role_code(str(row[5]))
    if not role_code:
        role_code = role_code_from_is_admin(int(row[4]))
    department_scope = normalize_department_scope(str(row[6]))
    return {
        "id": row[0],
        "username": row[1],
        "display_name": row[2],
        "is_active": int(row[3]),
        "is_admin": int(row[4]),
        "role_code": role_code,
        "role_name": role_name(role_code),
        "department_scope": department_scope,
        "must_change_password": int(row[7]),
        "updated_at": row[8],
    }


def list_users() -> list[dict[str, Any]]:
    with connect_db(DB_PATH) as conn:
        clear_expired_sessions(conn)
        rows = conn.execute(
            """
            SELECT id, username, display_name, is_active, is_admin, role_code, department_scope, must_change_password, updated_at
            FROM users
            ORDER BY username ASC
            """
        ).fetchall()
        conn.commit()
    return [sanitize_user_row(row) for row in rows]


def list_active_user_options() -> list[dict[str, Any]]:
    with connect_db(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT id, username, display_name, is_admin, role_code, department_scope
            FROM users
            WHERE is_active = 1
            ORDER BY username ASC
            """
        ).fetchall()
    return [
        {
            "id": row[0],
            "username": row[1],
            "display_name": row[2],
            "label": f"{row[2]} ({row[1]})",
            "role_code": normalize_role_code(str(row[4])) or role_code_from_is_admin(int(row[3])),
            "role_name": role_name(normalize_role_code(str(row[4])) or role_code_from_is_admin(int(row[3]))),
            "department_scope": normalize_department_scope(str(row[5])),
        }
        for row in rows
    ]


def get_user_by_id(conn: sqlite3.Connection, user_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id, username, display_name, password_hash, is_active, is_admin, role_code, department_scope, must_change_password, updated_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "username": row[1],
        "display_name": row[2],
        "password_hash": row[3],
        "is_active": int(row[4]),
        "is_admin": int(row[5]),
        "role_code": normalize_role_code(str(row[6])) or role_code_from_is_admin(int(row[5])),
        "department_scope": normalize_department_scope(str(row[7])),
        "must_change_password": int(row[8]),
        "updated_at": row[9],
    }


def get_user_by_username(conn: sqlite3.Connection, username: str) -> dict[str, Any] | None:
    normalized = normalize_username(username)
    row = conn.execute(
        """
        SELECT id, username, display_name, password_hash, is_active, is_admin, role_code, department_scope, must_change_password, updated_at
        FROM users
        WHERE username = ?
        """,
        (normalized,),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "username": row[1],
        "display_name": row[2],
        "password_hash": row[3],
        "is_active": int(row[4]),
        "is_admin": int(row[5]),
        "role_code": normalize_role_code(str(row[6])) or role_code_from_is_admin(int(row[5])),
        "department_scope": normalize_department_scope(str(row[7])),
        "must_change_password": int(row[8]),
        "updated_at": row[9],
    }


def create_session(conn: sqlite3.Connection, user_id: str) -> tuple[str, int]:
    token = secrets.token_urlsafe(32)
    expires_at = now_ts() + SESSION_TTL_SECONDS
    conn.execute(
        """
        INSERT INTO user_sessions (session_token, user_id, expires_at, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (token, user_id, expires_at, utc_now_iso()),
    )
    return token, expires_at


def delete_session(conn: sqlite3.Connection, token: str) -> None:
    conn.execute("DELETE FROM user_sessions WHERE session_token = ?", (token,))


def delete_user_sessions(conn: sqlite3.Connection, user_id: str) -> None:
    conn.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))


def get_current_user_by_session(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    with connect_db(DB_PATH) as conn:
        clear_expired_sessions(conn)
        row = conn.execute(
            """
            SELECT u.id, u.username, u.display_name, u.is_active, u.is_admin, u.role_code, u.department_scope, u.must_change_password, u.updated_at
            FROM user_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.session_token = ? AND s.expires_at > ?
            """,
            (token, now_ts()),
        ).fetchone()
        conn.commit()
    if row is None:
        return None
    user = sanitize_user_row(row)
    if user["is_active"] != 1:
        return None
    return user


def validate_user_payload(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    username = normalize_username(str(payload.get("username", "")))
    display_name = str(payload.get("display_name", "")).strip()
    password = str(payload.get("password", "")).strip()
    parsed_is_admin, is_admin_error = parse_bool_flag(payload.get("is_admin"), default=False, field_name="is_admin")
    if parsed_is_admin is None:
        return None, is_admin_error
    raw_role_code = str(payload.get("role_code", "")).strip()
    role_code = normalize_role_code(raw_role_code)
    if raw_role_code and not role_code:
        return None, "role_code 不合法"
    if not role_code:
        role_code = role_code_from_is_admin(parsed_is_admin)
    is_admin = 1 if role_code == ROLE_ADMINISTRATOR else 0
    department_scope = normalize_department_scope(str(payload.get("department_scope", "")).strip())

    if not validate_username(username):
        return None, "username 需为 3-32 位字母数字或 ._- 组合"
    if not display_name:
        return None, "display_name 不能为空"
    if len(password) < 8:
        return None, "password 至少 8 位"
    if role_code not in ROLE_DEFINITIONS:
        return None, "role_code 不合法"
    return {
        "username": username,
        "display_name": display_name,
        "password": password,
        "is_admin": is_admin,
        "role_code": role_code,
        "department_scope": department_scope,
    }, ""


def validate_user_update_payload(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    display_name = str(payload.get("display_name", "")).strip()
    parsed_is_admin, is_admin_error = parse_bool_flag(payload.get("is_admin"), default=False, field_name="is_admin")
    if parsed_is_admin is None:
        return None, is_admin_error
    parsed_is_active, is_active_error = parse_bool_flag(payload.get("is_active"), default=True, field_name="is_active")
    if parsed_is_active is None:
        return None, is_active_error
    raw_role_code = str(payload.get("role_code", "")).strip()
    role_code = normalize_role_code(raw_role_code)
    if raw_role_code and not role_code:
        return None, "role_code 不合法"
    if not role_code:
        role_code = role_code_from_is_admin(parsed_is_admin)
    department_scope = normalize_department_scope(str(payload.get("department_scope", "")).strip())
    if not display_name:
        return None, "display_name 不能为空"
    if role_code not in ROLE_DEFINITIONS:
        return None, "role_code 不合法"
    return {
        "display_name": display_name,
        "is_active": parsed_is_active,
        "is_admin": 1 if role_code == ROLE_ADMINISTRATOR else 0,
        "role_code": role_code,
        "department_scope": department_scope,
    }, ""


def create_user(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned, error = validate_user_payload(payload)
    if cleaned is None:
        raise ValueError(error)

    with connect_db(DB_PATH) as conn:
        existing = get_user_by_username(conn, cleaned["username"])
        if existing is not None:
            raise ValueError("username 已存在")
        now = utc_now_iso()
        user_id = secrets.token_hex(16)
        conn.execute(
            """
            INSERT INTO users (
                id, username, display_name, password_hash, is_active, is_admin,
                role_code, department_scope, must_change_password, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, 1, ?, ?)
            """,
            (
                user_id,
                cleaned["username"],
                cleaned["display_name"],
                hash_password(cleaned["password"]),
                cleaned["is_admin"],
                cleaned["role_code"],
                cleaned["department_scope"],
                now,
                now,
            ),
        )
        user = get_user_by_id(conn, user_id)
        conn.commit()
    if user is None:
        raise ValueError("创建用户失败")
    return sanitize_user_row(
        (
            user["id"],
            user["username"],
            user["display_name"],
            user["is_active"],
            user["is_admin"],
            user["role_code"],
            user["department_scope"],
            user["must_change_password"],
            user["updated_at"],
        )
    )


def update_user(user_id: str, payload: dict[str, Any], actor_user_id: str) -> dict[str, Any]:
    cleaned, error = validate_user_update_payload(payload)
    if cleaned is None:
        raise ValueError(error)

    with connect_db(DB_PATH) as conn:
        target = get_user_by_id(conn, user_id)
        if target is None:
            raise ValueError("user 不存在")
        if user_id == actor_user_id and cleaned["is_active"] == 0:
            raise ValueError("不能禁用当前登录用户")

        conn.execute(
            """
            UPDATE users
            SET display_name = ?, is_active = ?, is_admin = ?, role_code = ?, department_scope = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                cleaned["display_name"],
                cleaned["is_active"],
                cleaned["is_admin"],
                cleaned["role_code"],
                cleaned["department_scope"],
                utc_now_iso(),
                user_id,
            ),
        )
        if cleaned["is_active"] == 0:
            delete_user_sessions(conn, user_id)
        updated = get_user_by_id(conn, user_id)
        conn.commit()

    if updated is None:
        raise ValueError("更新用户失败")
    return sanitize_user_row(
        (
            updated["id"],
            updated["username"],
            updated["display_name"],
            updated["is_active"],
            updated["is_admin"],
            updated["role_code"],
            updated["department_scope"],
            updated["must_change_password"],
            updated["updated_at"],
        )
    )


def reset_user_password(user_id: str, new_password: str) -> dict[str, Any]:
    password = (new_password or "").strip()
    if len(password) < 8:
        raise ValueError("password 至少 8 位")

    with connect_db(DB_PATH) as conn:
        target = get_user_by_id(conn, user_id)
        if target is None:
            raise ValueError("user 不存在")
        conn.execute(
            """
            UPDATE users
            SET password_hash = ?, must_change_password = 1, updated_at = ?
            WHERE id = ?
            """,
            (hash_password(password), utc_now_iso(), user_id),
        )
        delete_user_sessions(conn, user_id)
        updated = get_user_by_id(conn, user_id)
        conn.commit()

    if updated is None:
        raise ValueError("重置密码失败")
    return sanitize_user_row(
        (
            updated["id"],
            updated["username"],
            updated["display_name"],
            updated["is_active"],
            updated["is_admin"],
            updated["role_code"],
            updated["department_scope"],
            updated["must_change_password"],
            updated["updated_at"],
        )
    )


def change_password(user_id: str, old_password: str, new_password: str) -> dict[str, Any]:
    new_value = (new_password or "").strip()
    if len(new_value) < 8:
        raise ValueError("新密码至少 8 位")

    with connect_db(DB_PATH) as conn:
        user = get_user_by_id(conn, user_id)
        if user is None:
            raise ValueError("user 不存在")
        if not verify_password(old_password, user["password_hash"]):
            raise ValueError("旧密码错误")
        conn.execute(
            """
            UPDATE users
            SET password_hash = ?, must_change_password = 0, updated_at = ?
            WHERE id = ?
            """,
            (hash_password(new_value), utc_now_iso(), user_id),
        )
        updated = get_user_by_id(conn, user_id)
        conn.commit()

    if updated is None:
        raise ValueError("修改密码失败")
    return sanitize_user_row(
        (
            updated["id"],
            updated["username"],
            updated["display_name"],
            updated["is_active"],
            updated["is_admin"],
            updated["role_code"],
            updated["department_scope"],
            updated["must_change_password"],
            updated["updated_at"],
        )
    )


def migrate_legacy_role_code(raw_role_code: str, raw_department_scope: str, is_admin: int) -> str:
    normalized = normalize_role_code(str(raw_role_code))
    department_scope = normalize_department_scope(str(raw_department_scope))
    if normalized:
        if normalized == ROLE_PERSONNEL_MANAGER and department_scope == "研发部":
            return ROLE_ENGINEERING_MANAGER
        if normalized == ROLE_PERSONNEL_MANAGER and department_scope == "算法部":
            return ROLE_ALGORITHM_MANAGER
        return normalized
    if int(is_admin) == 1:
        return ROLE_ADMINISTRATOR
    legacy_role = str(raw_role_code or "").strip().lower()
    if legacy_role == "hiring_manager":
        if department_scope == "研发部":
            return ROLE_ENGINEERING_MANAGER
        if department_scope == "算法部":
            return ROLE_ALGORITHM_MANAGER
        if department_scope == "人事部":
            return ROLE_PERSONNEL_MANAGER
        return ROLE_PERSONNEL_MANAGER
    if legacy_role == "interviewer":
        if department_scope == "算法部":
            return ROLE_ALGORITHM_MANAGER
        return ROLE_ENGINEERING_MANAGER
    return role_code_from_is_admin(int(is_admin))


def migrate_user_roles(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT id, is_admin, role_code, department_scope FROM users").fetchall()
    for user_id, is_admin, raw_role_code, raw_department_scope in rows:
        next_role_code = migrate_legacy_role_code(str(raw_role_code), str(raw_department_scope), int(is_admin))
        next_is_admin = 1 if next_role_code == ROLE_ADMINISTRATOR else 0
        next_department_scope = normalize_department_scope(str(raw_department_scope))

        if (
            next_role_code != str(raw_role_code or "")
            or next_is_admin != int(is_admin)
            or next_department_scope != str(raw_department_scope or "")
        ):
            conn.execute(
                """
                UPDATE users
                SET role_code = ?, is_admin = ?, department_scope = ?, updated_at = ?
                WHERE id = ?
                """,
                (next_role_code, next_is_admin, next_department_scope, utc_now_iso(), user_id),
            )


def validate_login_payload(payload: dict[str, Any]) -> tuple[dict[str, str] | None, str]:
    username = normalize_username(str(payload.get("username", "")))
    password = str(payload.get("password", ""))
    if not username or not password:
        return None, "username 和 password 不能为空"
    return {"username": username, "password": password}, ""


def validate_change_password_payload(payload: dict[str, Any]) -> tuple[dict[str, str] | None, str]:
    old_password = str(payload.get("old_password", ""))
    new_password = str(payload.get("new_password", ""))
    if not old_password or not new_password:
        return None, "old_password 和 new_password 不能为空"
    return {"old_password": old_password, "new_password": new_password}, ""
