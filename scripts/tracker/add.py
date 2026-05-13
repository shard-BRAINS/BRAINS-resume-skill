"""Insert-side public API for the tracker.

Each function opens a db connection, inserts a row (with timestamp), commits,
closes, and returns the new row id. Foreign-key violations raise sqlite3.IntegrityError.
"""
import json
from datetime import datetime
from typing import List, Optional

from scripts.tracker.db import open_db


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def add_resume_version(
    file_path: Optional[str],
    template: str,
    focus_areas: List[str],
    parent_id: Optional[int] = None,
    tagged_jd_id: Optional[int] = None,
) -> int:
    """Insert a resume_versions row, return the new id."""
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO resume_versions
                (file_path, template, focus_areas, parent_id, tagged_jd_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                file_path,
                template,
                json.dumps(focus_areas),
                parent_id,
                tagged_jd_id,
                _now_iso(),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def add_jd(
    source: str,
    source_ref: Optional[str],
    company: str,
    role_title: str,
    raw_text: str,
    analyzer_findings: dict,
    focus_areas_required: List[str],
    focus_areas_nice: List[str],
) -> int:
    """Insert a jds row, return the new id."""
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO jds
                (source, source_ref, company, role_title, raw_text,
                 analyzer_findings, focus_areas_required, focus_areas_nice,
                 created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source,
                source_ref,
                company,
                role_title,
                raw_text,
                json.dumps(analyzer_findings),
                json.dumps(focus_areas_required),
                json.dumps(focus_areas_nice),
                _now_iso(),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
