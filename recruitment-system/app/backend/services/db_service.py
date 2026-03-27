from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

from ..repositories.sqlite_helpers import connect_db
from .operation_log_service import ensure_operation_log_table


def _candidate_service():
    from . import candidate_service

    return candidate_service


def has_table(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def has_column(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def init_db() -> None:
    candidate_service = _candidate_service()
    candidate_service.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    candidate_service.DATASET_ROOT_DIR.mkdir(parents=True, exist_ok=True)
    candidate_service.JOB_TEMPLATE_ROOT_DIR.mkdir(parents=True, exist_ok=True)
    with connect_db(candidate_service.DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candidate_files (
                candidate_id TEXT PRIMARY KEY,
                candidate_name TEXT NOT NULL,
                original_filename TEXT NOT NULL UNIQUE,
                storage_rel_path TEXT NOT NULL UNIQUE,
                inflow_date TEXT NOT NULL DEFAULT '',
                resume_parsed_text TEXT NOT NULL DEFAULT '',
                resume_parser_payload_json TEXT NOT NULL DEFAULT '',
                resume_parser_updated_at TEXT NOT NULL DEFAULT '',
                uploaded_at TEXT NOT NULL,
                uploaded_by TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_candidate_files_original_filename_nocase
            ON candidate_files(original_filename COLLATE NOCASE)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candidate_profiles (
                candidate_id TEXT PRIMARY KEY,
                base_location TEXT NOT NULL,
                salary_mode TEXT NOT NULL,
                salary_range TEXT NOT NULL,
                experience_type TEXT NOT NULL,
                graduation_year TEXT NOT NULL,
                work_years TEXT NOT NULL,
                hire_type TEXT NOT NULL,
                preset_position TEXT NOT NULL,
                highest_education TEXT NOT NULL,
                school_name TEXT NOT NULL,
                applied_position TEXT NOT NULL,
                department_scope TEXT NOT NULL DEFAULT '',
                job_ref_id TEXT NOT NULL DEFAULT '',
                job_id TEXT NOT NULL DEFAULT '',
                job_code TEXT NOT NULL DEFAULT '',
                job_title TEXT NOT NULL DEFAULT '',
                job_snapshot_json TEXT NOT NULL DEFAULT '',
                resume_structured_json TEXT NOT NULL DEFAULT '{}',
                resume_extract_status TEXT NOT NULL DEFAULT '',
                resume_extract_source TEXT NOT NULL DEFAULT '',
                resume_extract_model TEXT NOT NULL DEFAULT '',
                resume_extract_error TEXT NOT NULL DEFAULT '',
                resume_extract_updated_at TEXT NOT NULL DEFAULT '',
                current_stage TEXT NOT NULL,
                stage_closed_from TEXT NOT NULL,
                stage_status_json TEXT NOT NULL,
                is_starred INTEGER NOT NULL DEFAULT 0,
                terminated_at TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interview_round_notes (
                candidate_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                interview_time TEXT NOT NULL,
                interviewer_user_id TEXT NOT NULL DEFAULT '',
                planned_questions TEXT NOT NULL,
                interview_review TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (candidate_id, stage)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                is_admin INTEGER NOT NULL DEFAULT 0,
                role_code TEXT NOT NULL DEFAULT 'hr_specialist',
                department_scope TEXT NOT NULL DEFAULT '',
                must_change_password INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candidate_auto_scores (
                score_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                score_source TEXT NOT NULL,
                score_status TEXT NOT NULL,
                model_name TEXT NOT NULL DEFAULT '',
                prompt_id TEXT NOT NULL DEFAULT '',
                total_score REAL NOT NULL DEFAULT 0,
                max_score REAL NOT NULL DEFAULT 0,
                match_level TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                risk_flags_json TEXT NOT NULL DEFAULT '[]',
                dimension_scores_json TEXT NOT NULL DEFAULT '[]',
                error_message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                job_code TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                department TEXT NOT NULL,
                headcount INTEGER NOT NULL DEFAULT 1,
                location TEXT NOT NULL DEFAULT '',
                recruiter_user_id TEXT NOT NULL DEFAULT '',
                hiring_manager_user_id TEXT NOT NULL DEFAULT '',
                jd TEXT NOT NULL DEFAULT '',
                requirements TEXT NOT NULL DEFAULT '',
                process_json TEXT NOT NULL DEFAULT '{}',
                criteria_json TEXT NOT NULL DEFAULT '{}',
                templates_json TEXT NOT NULL DEFAULT '[]',
                active_template_version INTEGER NOT NULL DEFAULT 0,
                score_table_storage_rel_path TEXT NOT NULL DEFAULT '',
                auto_score_enabled INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'open',
                logs_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                closed_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_jobs_updated_at
            ON jobs(updated_at DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_candidate_auto_scores_candidate_created
            ON candidate_auto_scores(candidate_id, created_at DESC)
            """
        )
        ensure_operation_log_table(conn)
        if not has_column(conn, "candidate_profiles", "stage_status_json"):
            conn.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN stage_status_json TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_profiles", "is_starred"):
            conn.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN is_starred INTEGER NOT NULL DEFAULT 0"
            )
        if not has_column(conn, "candidate_profiles", "terminated_at"):
            conn.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN terminated_at TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_profiles", "department_scope"):
            conn.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN department_scope TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_profiles", "job_ref_id"):
            conn.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN job_ref_id TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_profiles", "job_id"):
            conn.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN job_id TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_profiles", "job_code"):
            conn.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN job_code TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_profiles", "job_title"):
            conn.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN job_title TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_profiles", "job_snapshot_json"):
            conn.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN job_snapshot_json TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_profiles", "resume_structured_json"):
            conn.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN resume_structured_json TEXT NOT NULL DEFAULT '{}'"
            )
        if not has_column(conn, "candidate_profiles", "resume_extract_status"):
            conn.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN resume_extract_status TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_profiles", "resume_extract_source"):
            conn.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN resume_extract_source TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_profiles", "resume_extract_model"):
            conn.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN resume_extract_model TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_profiles", "resume_extract_error"):
            conn.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN resume_extract_error TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_profiles", "resume_extract_updated_at"):
            conn.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN resume_extract_updated_at TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "interview_round_notes", "interviewer_user_id"):
            conn.execute(
                "ALTER TABLE interview_round_notes ADD COLUMN interviewer_user_id TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_files", "inflow_date"):
            conn.execute(
                "ALTER TABLE candidate_files ADD COLUMN inflow_date TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_files", "resume_parsed_text"):
            conn.execute(
                "ALTER TABLE candidate_files ADD COLUMN resume_parsed_text TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_files", "resume_parser_payload_json"):
            conn.execute(
                "ALTER TABLE candidate_files ADD COLUMN resume_parser_payload_json TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "candidate_files", "resume_parser_updated_at"):
            conn.execute(
                "ALTER TABLE candidate_files ADD COLUMN resume_parser_updated_at TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "users", "role_code"):
            conn.execute("ALTER TABLE users ADD COLUMN role_code TEXT NOT NULL DEFAULT ''")
        if not has_column(conn, "users", "department_scope"):
            conn.execute(
                "ALTER TABLE users ADD COLUMN department_scope TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "jobs", "score_table_storage_rel_path"):
            conn.execute(
                "ALTER TABLE jobs ADD COLUMN score_table_storage_rel_path TEXT NOT NULL DEFAULT ''"
            )
        if not has_column(conn, "jobs", "logs_json"):
            conn.execute("ALTER TABLE jobs ADD COLUMN logs_json TEXT NOT NULL DEFAULT '[]'")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_candidate_profiles_job_ref_id
            ON candidate_profiles(job_ref_id)
            """
        )
        conn.execute(
            """
            UPDATE candidate_profiles
            SET job_ref_id = job_id
            WHERE (job_ref_id = '' OR job_ref_id IS NULL) AND job_id != ''
            """
        )

        migrate_legacy_data(conn)
        migrate_candidate_id_to_uuid(conn)
        migrate_candidate_file_inflow_date(conn)
        migrate_stage_status_model(conn)
        migrate_round_stage_names(conn)
        candidate_service.migrate_user_roles(conn)
        candidate_service.seed_candidate_profiles(conn)
        candidate_service.seed_default_admin(conn)
        candidate_service.clear_expired_sessions(conn)
        conn.commit()


def migrate_legacy_data(conn: sqlite3.Connection) -> None:
    candidate_service = _candidate_service()
    if not has_table(conn, "candidate_evaluations"):
        return

    rows = conn.execute(
        """
        SELECT candidate_id, base_location, salary_mode, salary_range, experience_type,
               graduation_year, work_years, hire_type, preset_position, manual_comment,
               updated_at
        FROM candidate_evaluations
        """
    ).fetchall()

    for row in rows:
        conn.execute(
            """
            INSERT OR IGNORE INTO candidate_profiles (
                candidate_id, base_location, salary_mode, salary_range,
                experience_type, graduation_year, work_years, hire_type,
                preset_position, highest_education, school_name, applied_position,
                department_scope, job_id, job_code, job_title, job_snapshot_json,
                current_stage, stage_closed_from, stage_status_json, is_starred,
                terminated_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                row[5],
                row[6],
                row[7],
                row[8],
                "未知",
                "未知",
                row[8],
                "",
                "",
                "",
                row[8],
                "",
                candidate_service.DEFAULT_STAGE,
                "",
                candidate_service.dump_stage_statuses(candidate_service.stage_status_template()),
                0,
                "",
                row[10] or candidate_service.utc_now_iso(),
            ),
        )

        manual_comment = (row[9] or "").strip()
        if manual_comment:
            conn.execute(
                """
                INSERT OR IGNORE INTO interview_round_notes (
                    candidate_id, stage, interview_time, interviewer_user_id,
                    planned_questions, interview_review, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row[0],
                    candidate_service.DEFAULT_STAGE,
                    "",
                    "",
                    "",
                    manual_comment,
                    row[10] or candidate_service.utc_now_iso(),
                ),
            )


def scan_all_pdf_files() -> list[Path]:
    candidate_service = _candidate_service()
    if not candidate_service.DATASET_ROOT_DIR.exists():
        return []
    return sorted(
        [path for path in candidate_service.DATASET_ROOT_DIR.rglob("*.pdf") if path.is_file()],
        key=lambda path: path.as_posix(),
    )


def migrate_candidate_identity(conn: sqlite3.Connection, old_id: str, new_id: str) -> None:
    if not old_id or not new_id or old_id == new_id:
        return

    old_profile = conn.execute(
        """
        SELECT candidate_id, base_location, salary_mode, salary_range,
               experience_type, graduation_year, work_years, hire_type,
               preset_position, highest_education, school_name, applied_position,
               current_stage, stage_closed_from, stage_status_json, is_starred,
               terminated_at, updated_at
        FROM candidate_profiles
        WHERE candidate_id = ?
        """,
        (old_id,),
    ).fetchone()
    if old_profile is not None:
        conn.execute("DELETE FROM candidate_profiles WHERE candidate_id = ?", (new_id,))
        conn.execute(
            "UPDATE candidate_profiles SET candidate_id = ? WHERE candidate_id = ?",
            (new_id, old_id),
        )

    old_rounds = conn.execute(
        """
        SELECT stage, interview_time, interviewer_user_id,
               planned_questions, interview_review, updated_at
        FROM interview_round_notes
        WHERE candidate_id = ?
        """,
        (old_id,),
    ).fetchall()
    for row in old_rounds:
        conn.execute(
            """
            INSERT INTO interview_round_notes (
                candidate_id, stage, interview_time, interviewer_user_id,
                planned_questions, interview_review, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(candidate_id, stage) DO UPDATE SET
                interview_time = excluded.interview_time,
                interviewer_user_id = excluded.interviewer_user_id,
                planned_questions = excluded.planned_questions,
                interview_review = excluded.interview_review,
                updated_at = excluded.updated_at
            """,
            (new_id, row[0], row[1], row[2], row[3], row[4], row[5]),
        )
    conn.execute("DELETE FROM interview_round_notes WHERE candidate_id = ?", (old_id,))


def migrate_candidate_id_to_uuid(conn: sqlite3.Connection) -> None:
    candidate_service = _candidate_service()
    rows = conn.execute(
        """
        SELECT candidate_id, original_filename
        FROM candidate_files
        """
    ).fetchall()
    filename_to_candidate_id: dict[str, str] = {
        (row[1] or "").strip().lower(): row[0] for row in rows if row[1]
    }
    known_candidate_ids = {row[0] for row in rows}

    for pdf in scan_all_pdf_files():
        try:
            rel_path = pdf.relative_to(candidate_service.DATASET_ROOT_DIR).as_posix()
        except ValueError:
            continue
        inferred_inflow_date = candidate_service.infer_inflow_date_from_rel_path(rel_path)
        original_filename = pdf.name
        filename_key = original_filename.lower()
        existing_id = filename_to_candidate_id.get(filename_key, "")
        if existing_id:
            if not candidate_service.is_uuid_candidate_id(existing_id):
                new_candidate_id = uuid.uuid4().hex
                while new_candidate_id in known_candidate_ids:
                    new_candidate_id = uuid.uuid4().hex
                migrate_candidate_identity(conn, existing_id, new_candidate_id)
                conn.execute(
                    """
                    UPDATE candidate_files
                    SET candidate_id = ?, storage_rel_path = ?, inflow_date = ?
                    WHERE candidate_id = ?
                    """,
                    (new_candidate_id, rel_path, inferred_inflow_date, existing_id),
                )
                known_candidate_ids.discard(existing_id)
                known_candidate_ids.add(new_candidate_id)
                filename_to_candidate_id[filename_key] = new_candidate_id
            else:
                migrate_candidate_identity(conn, original_filename, existing_id)
                conn.execute(
                    """
                    UPDATE candidate_files
                    SET storage_rel_path = ?, inflow_date = ?
                    WHERE candidate_id = ?
                    """,
                    (rel_path, inferred_inflow_date, existing_id),
                )
            continue

        candidate_id = uuid.uuid4().hex
        while candidate_id in known_candidate_ids:
            candidate_id = uuid.uuid4().hex
        parsed = candidate_service.parse_candidate_from_filename(
            original_filename,
            candidate_id=candidate_id,
        )
        conn.execute(
            """
            INSERT INTO candidate_files (
                candidate_id, candidate_name, original_filename, storage_rel_path,
                inflow_date, uploaded_at, uploaded_by, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, '', 1)
            """,
            (
                candidate_id,
                parsed["name"],
                original_filename,
                rel_path,
                inferred_inflow_date,
                candidate_service.utc_now_iso(),
            ),
        )
        migrate_candidate_identity(conn, original_filename, candidate_id)
        filename_to_candidate_id[filename_key] = candidate_id
        known_candidate_ids.add(candidate_id)


def migrate_candidate_file_inflow_date(conn: sqlite3.Connection) -> None:
    candidate_service = _candidate_service()
    rows = conn.execute(
        """
        SELECT candidate_id, storage_rel_path, inflow_date
        FROM candidate_files
        """
    ).fetchall()
    for row in rows:
        candidate_id = row[0]
        storage_rel_path = row[1] or ""
        existing_inflow_date = row[2] or ""
        normalized_existing = candidate_service.normalize_date_tag(existing_inflow_date)
        normalized_inflow_date = normalized_existing or candidate_service.infer_inflow_date_from_rel_path(
            storage_rel_path,
            fallback=normalized_existing,
        )
        if normalized_inflow_date == normalized_existing:
            continue
        conn.execute(
            "UPDATE candidate_files SET inflow_date = ? WHERE candidate_id = ?",
            (normalized_inflow_date, candidate_id),
        )


def migrate_stage_status_model(conn: sqlite3.Connection) -> None:
    candidate_service = _candidate_service()
    rows = conn.execute(
        """
        SELECT candidate_id, current_stage, stage_closed_from, stage_status_json
        FROM candidate_profiles
        """
    ).fetchall()

    for row in rows:
        candidate_id = row[0]
        statuses, normalized_current, normalized_closed = candidate_service.decode_stage_statuses(
            row[3] or "",
            row[1] or "",
            row[2] or "",
        )
        conn.execute(
            """
            UPDATE candidate_profiles
            SET current_stage = ?, stage_closed_from = ?, stage_status_json = ?
            WHERE candidate_id = ?
            """,
            (
                normalized_current,
                normalized_closed,
                candidate_service.dump_stage_statuses(statuses),
                candidate_id,
            ),
        )


def migrate_round_stage_names(conn: sqlite3.Connection) -> None:
    candidate_service = _candidate_service()
    rows = conn.execute(
        """
        SELECT candidate_id, stage, interview_time, interviewer_user_id,
               planned_questions, interview_review, updated_at
        FROM interview_round_notes
        """
    ).fetchall()

    for row in rows:
        candidate_id, stage = row[0], row[1]
        normalized_stage = candidate_service.normalize_stage_name(stage)
        if not normalized_stage:
            conn.execute(
                "DELETE FROM interview_round_notes WHERE candidate_id = ? AND stage = ?",
                (candidate_id, stage),
            )
            continue

        if normalized_stage != stage:
            conn.execute(
                """
                INSERT INTO interview_round_notes (
                    candidate_id, stage, interview_time, interviewer_user_id,
                    planned_questions, interview_review, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(candidate_id, stage) DO UPDATE SET
                    interview_time = excluded.interview_time,
                    interviewer_user_id = excluded.interviewer_user_id,
                    planned_questions = excluded.planned_questions,
                    interview_review = excluded.interview_review,
                    updated_at = excluded.updated_at
                """,
                (candidate_id, normalized_stage, row[2], row[3], row[4], row[5], row[6]),
            )
            conn.execute(
                "DELETE FROM interview_round_notes WHERE candidate_id = ? AND stage = ?",
                (candidate_id, stage),
            )


__all__ = [
    "has_table",
    "has_column",
    "init_db",
    "migrate_legacy_data",
    "scan_all_pdf_files",
    "migrate_candidate_identity",
    "migrate_candidate_id_to_uuid",
    "migrate_candidate_file_inflow_date",
    "migrate_stage_status_model",
    "migrate_round_stage_names",
]
