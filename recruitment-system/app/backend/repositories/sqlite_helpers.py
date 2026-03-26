from __future__ import annotations

import sqlite3
from pathlib import Path


def connect_db(db_path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.execute("PRAGMA busy_timeout = 30000")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.DatabaseError:
        # Keep default journal mode when WAL cannot be enabled.
        pass
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn
