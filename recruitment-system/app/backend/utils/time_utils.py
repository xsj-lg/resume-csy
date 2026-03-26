from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_ts() -> int:
    return int(time.time())


def today_date_tag() -> str:
    return datetime.now().strftime("%Y%m%d")


def today_dataset_dir(dataset_root_dir: Path) -> Path:
    return dataset_root_dir / today_date_tag()
