from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from ..repositories.sqlite_helpers import connect_db
from .auto_score_service import *  # noqa: F401,F403
from .candidate_service import (  # noqa: F401
    DB_PATH,
    DATASET_ROOT_DIR,
    JOB_TEMPLATE_ROOT_DIR,
    MAX_UPLOAD_BYTES,
    ROOT_DIR,
    STATIC_DIR,
    export_resume_results_for_user,
    filter_candidates,
    get_resume_result_summary_for_user,
    guess_resume_content_type,
    list_candidates_for_user,
    list_interview_calendar_for_user,
    now_ts,
    parse_candidate_filters,
    parse_resume_result_filters,
    utc_now_iso,
)
from .candidate_workflow_service import *  # noqa: F401,F403
from .db_service import *  # noqa: F401,F403
from .job_service import *  # noqa: F401,F403
from .llm_service import *  # noqa: F401,F403
from .operation_log_service import *  # noqa: F401,F403
from .resume_extract_service import *  # noqa: F401,F403
from .role_user_service import *  # noqa: F401,F403
from .score_table_service import *  # noqa: F401,F403
