from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote

from ..repositories.candidate_repository import (
    default_profile,
    get_candidate_file_by_id,
    get_candidate_file_by_original_filename,
    insert_profile_if_missing,
    list_candidate_file_rows,
    parse_candidate_from_filename,
    seed_candidate_profiles,
)
from ..repositories.sqlite_helpers import connect_db


def _candidate_service():
    from . import candidate_service

    return candidate_service


def sync_resumes_from_storage() -> dict[str, int]:
    candidate_service = _candidate_service()
    with connect_db(candidate_service.DB_PATH) as conn:
        before_files = list_candidate_file_rows(conn, include_inactive=True)
        before_filename_set = {str(row["original_filename"]).strip().lower() for row in before_files}
        scanned_pdf_count = len(candidate_service.scan_all_pdf_files())
        candidate_service.migrate_candidate_id_to_uuid(conn)
        candidate_service.migrate_candidate_file_inflow_date(conn)
        seed_candidate_profiles(conn)
        after_files = list_candidate_file_rows(conn, include_inactive=True)
        after_filename_set = {str(row["original_filename"]).strip().lower() for row in after_files}
        conn.commit()

    added_count = len(after_filename_set - before_filename_set)
    return {
        "scanned_pdf_count": scanned_pdf_count,
        "added_count": added_count,
        "candidate_count": len(after_files),
    }


def resolve_resume_path(candidate_id: str) -> Path | None:
    candidate_service = _candidate_service()
    with connect_db(candidate_service.DB_PATH) as conn:
        file_row = get_candidate_file_by_id(conn, candidate_id)
    if file_row is None or int(file_row.get("is_active", 0)) != 1:
        return None
    return candidate_service.resolve_storage_path(str(file_row.get("storage_rel_path", "")))


def delete_candidate(candidate_id: str) -> bool:
    candidate_service = _candidate_service()
    if not candidate_id:
        return False

    file_path: Path | None = None
    with connect_db(candidate_service.DB_PATH) as conn:
        file_row = get_candidate_file_by_id(conn, candidate_id)
        if file_row is None or int(file_row.get("is_active", 0)) != 1:
            return False
        file_path = candidate_service.resolve_storage_path(str(file_row.get("storage_rel_path", "")))

        if file_path is not None and file_path.exists():
            try:
                file_path.unlink()
            except OSError as exc:
                raise ValueError("删除本地简历文件失败") from exc

        conn.execute("DELETE FROM interview_round_notes WHERE candidate_id = ?", (candidate_id,))
        conn.execute("DELETE FROM candidate_auto_scores WHERE candidate_id = ?", (candidate_id,))
        conn.execute("DELETE FROM candidate_profiles WHERE candidate_id = ?", (candidate_id,))
        conn.execute("DELETE FROM candidate_files WHERE candidate_id = ?", (candidate_id,))
        conn.commit()

    if file_path is not None:
        dataset_root = candidate_service.DATASET_ROOT_DIR.resolve()
        parent = file_path.parent
        if parent != dataset_root:
            try:
                parent.relative_to(dataset_root)
                if not any(parent.iterdir()):
                    parent.rmdir()
            except (ValueError, OSError):
                pass
    return True


def create_candidate_from_upload(
    *,
    filename: str,
    content: bytes,
    candidate_name: str,
    uploaded_by: str,
    department_scope: str,
    job_id: str,
    job_code: str,
    job_title: str,
    job_payload: dict[str, Any],
) -> dict[str, Any]:
    candidate_service = _candidate_service()
    safe_filename = candidate_service.sanitize_uploaded_filename(filename)
    candidate_service.ensure_resume_content(safe_filename, content)
    final_name = (candidate_name or "").strip() or Path(safe_filename).stem
    if not final_name:
        final_name = "未命名候选人"
    normalized_scope = candidate_service.normalize_department_scope(department_scope)
    if not normalized_scope:
        raise ValueError("department_scope 非法，必须为销售部/研发部/算法部/项目部/人事部")
    normalized_job_id = (job_id or "").strip()
    normalized_job_title = (job_title or "").strip()
    if not normalized_job_id:
        raise ValueError("job_id 不能为空")
    if not normalized_job_title:
        raise ValueError("job_title 不能为空")
    snapshot = candidate_service.build_job_snapshot(
        job_payload=job_payload,
        department_scope=normalized_scope,
        job_id=normalized_job_id,
        job_code=(job_code or "").strip(),
        job_title=normalized_job_title,
    )

    target_dir = candidate_service.today_dataset_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = (target_dir / safe_filename).resolve()
    root = candidate_service.DATASET_ROOT_DIR.resolve()
    try:
        target_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("上传路径非法") from exc

    if target_path.exists():
        raise ValueError("同名文件已存在，已拒绝上传")

    candidate_id = uuid.uuid4().hex
    relative_path = target_path.relative_to(candidate_service.DATASET_ROOT_DIR).as_posix()
    inflow_date = candidate_service.infer_inflow_date_from_rel_path(
        relative_path,
        fallback=candidate_service.today_date_tag(),
    )
    resume_text = ""
    resume_parser_payload: dict[str, Any] = {}
    resume_parser_updated_at = ""

    try:
        target_path.write_bytes(content)
        try:
            resume_parser_payload, resume_text = candidate_service.parse_resume_file(target_path)
            resume_parser_updated_at = candidate_service.utc_now_iso()
        except Exception as exc:
            if candidate_service.is_image_resume_filename(safe_filename):
                raise ValueError(f"解析失败: {exc}") from exc
            print(f"[upload parse] skipped for {safe_filename}: {exc}")
    except Exception as exc:
        try:
            target_path.unlink(missing_ok=True)
        except OSError:
            pass
        if isinstance(exc, OSError):
            raise ValueError("保存文件失败") from exc
        raise

    try:
        with connect_db(candidate_service.DB_PATH) as conn:
            existing = get_candidate_file_by_original_filename(conn, safe_filename)
            if existing is not None:
                raise ValueError("同名文件已存在，已拒绝上传")

            candidate_service.execute_sql_with_retry(
                conn,
                """
                INSERT INTO candidate_files (
                    candidate_id, candidate_name, original_filename, storage_rel_path,
                    inflow_date, resume_parsed_text, resume_parser_payload_json,
                    resume_parser_updated_at, uploaded_at, uploaded_by, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    candidate_id,
                    final_name,
                    safe_filename,
                    relative_path,
                    inflow_date,
                    resume_text,
                    (
                        json.dumps(resume_parser_payload, ensure_ascii=False, separators=(",", ":"))
                        if resume_parser_payload
                        else ""
                    ),
                    resume_parser_updated_at,
                    candidate_service.utc_now_iso(),
                    uploaded_by,
                ),
            )
            parsed = parse_candidate_from_filename(
                safe_filename,
                candidate_id=candidate_id,
                candidate_name_override=final_name,
            )
            profile = default_profile(parsed)
            profile["department_scope"] = normalized_scope
            profile["job_ref_id"] = normalized_job_id
            profile["job_id"] = normalized_job_id
            profile["job_code"] = (job_code or "").strip()
            profile["job_title"] = normalized_job_title
            profile["job_snapshot_json"] = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
            if normalized_job_title:
                profile["applied_position"] = normalized_job_title
                profile["preset_position"] = normalized_job_title
            insert_profile_if_missing(conn, profile)
            conn.commit()
    except Exception:
        try:
            target_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    if resume_text:
        try:
            _store_basic_resume_info(candidate_id, resume_text)
        except Exception as exc:
            print(f"[basic extract] failed for {candidate_id}: {exc}")
    _set_resume_extract_pending(candidate_id)
    _schedule_async_resume_tasks(candidate_id, bool(snapshot.get("auto_score_enabled", False)))

    return {
        "candidate_id": candidate_id,
        "candidate_name": final_name,
        "filename": safe_filename,
        "storage_rel_path": relative_path,
        "inflow_date": inflow_date,
        "pdf_url": f"/api/resumes/{quote(candidate_id)}",
        "department_scope": normalized_scope,
        "job_id": normalized_job_id,
        "job_code": (job_code or "").strip(),
        "job_title": normalized_job_title,
        "job_snapshot": snapshot,
        "resume_snippet": resume_text[:320] if resume_text else "",
    }


def _set_resume_extract_pending(candidate_id: str) -> None:
    candidate_service = _candidate_service()
    now = candidate_service.utc_now_iso()
    with connect_db(candidate_service.DB_PATH) as conn:
        candidate_service.execute_sql_with_retry(
            conn,
            """
            UPDATE candidate_profiles
            SET resume_extract_status = ?, resume_extract_source = ?, resume_extract_model = ?,
                resume_extract_error = ?, resume_extract_updated_at = ?, updated_at = ?
            WHERE candidate_id = ?
            """,
            ("queued", "system", "", "", now, now, candidate_id),
        )
        conn.commit()


def _schedule_async_resume_tasks(candidate_id: str, auto_score_enabled: bool) -> None:
    candidate_service = _candidate_service()

    def _worker() -> None:
        try:
            candidate_service.trigger_resume_extract_for_candidate(candidate_id)
        except Exception as exc:
            print(f"[async] resume extract failed for {candidate_id}: {exc}")
        if not auto_score_enabled:
            return
        try:
            candidate_service.trigger_auto_score_for_candidate(candidate_id)
        except Exception as exc:
            print(f"[async] auto score failed for {candidate_id}: {exc}")

    threading.Thread(target=_worker, daemon=True).start()


def _build_resume_snippet(resume_text: str, length: int = 320) -> str:
    cleaned = " ".join(str(resume_text or "").replace("\n", " ").split())
    return cleaned[:length]


def _extract_contact_from_text(text: str) -> tuple[str, str]:
    candidate_service = _candidate_service()
    phone_match = candidate_service.PHONE_PATTERN.search(text or "")
    email_match = candidate_service.EMAIL_PATTERN.search(text or "")
    phone = phone_match.group(1) if phone_match else ""
    email = email_match.group(0) if email_match else ""
    return phone, email


def _store_basic_resume_info(candidate_id: str, resume_text: str) -> None:
    candidate_service = _candidate_service()
    snippet = _build_resume_snippet(resume_text)
    phone, email = _extract_contact_from_text(resume_text)
    now = candidate_service.utc_now_iso()
    with connect_db(candidate_service.DB_PATH) as conn:
        row = conn.execute(
            "SELECT resume_structured_json FROM candidate_profiles WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
        structured = candidate_service.json_loads_or_empty_object(row[0] if row else "")
        basic_raw = structured.get("basic")
        basic = basic_raw if isinstance(basic_raw, dict) else {}
        if phone:
            basic["phone"] = phone
        elif not str(basic.get("phone", "")).strip():
            basic["phone"] = str(structured.get("basic_contact_phone", "")).strip()
        if email:
            basic["email"] = email
        elif not str(basic.get("email", "")).strip():
            basic["email"] = str(structured.get("basic_contact_email", "")).strip()
        structured["basic"] = basic
        if snippet and not str(structured.get("summary", "")).strip():
            structured["summary"] = snippet
        structured["basic_snippet"] = snippet
        structured["basic_contact_phone"] = phone
        structured["basic_contact_email"] = email
        conn.execute(
            """
            UPDATE candidate_profiles
            SET resume_structured_json = ?, updated_at = ?
            WHERE candidate_id = ?
            """,
            (
                json.dumps(structured, ensure_ascii=False, separators=(",", ":")),
                now,
                candidate_id,
            ),
        )
        conn.commit()


__all__ = [
    "create_candidate_from_upload",
    "delete_candidate",
    "resolve_resume_path",
    "sync_resumes_from_storage",
]
