"""Insert-side public API for the tracker.

Each function opens a db connection, inserts a row (with timestamp), commits,
closes, and returns the new row id. Foreign-key violations raise sqlite3.IntegrityError.
"""
import json
from datetime import datetime
from typing import List, Optional

from scripts.tracker.db import open_db
from scripts.tracker.models import APPLICATION_CHANNELS, OUTCOME_EVENT_TYPES


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def add_resume_version(
    file_path: Optional[str],
    template: str,
    focus_areas: List[str],
    parent_id: Optional[int] = None,
    tagged_jd_id: Optional[int] = None,
    artifact_uid: Optional[str] = None,
    parent_uid: Optional[str] = None,
    for_candidate: Optional[str] = None,
    is_baseline: Optional[bool] = None,
) -> int:
    """Insert a resume_versions row, return the new id.

    is_baseline:
      - None (default): auto — set to 1 if this is the first non-archived row
        in this for_candidate scope, else 0.
      - True / False: explicit override; the caller controls the flag.
    """
    conn = open_db()
    try:
        if is_baseline is None:
            existing = conn.execute(
                "SELECT COUNT(*) FROM resume_versions "
                "WHERE archived_at IS NULL AND "
                "((? IS NULL AND for_candidate IS NULL) OR for_candidate = ?)",
                (for_candidate, for_candidate),
            ).fetchone()[0]
            resolved_baseline = 1 if existing == 0 else 0
        else:
            resolved_baseline = 1 if is_baseline else 0

        cur = conn.execute(
            """
            INSERT INTO resume_versions
                (file_path, template, focus_areas, parent_id, tagged_jd_id,
                 created_at, artifact_uid, parent_uid, for_candidate,
                 is_baseline)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_path, template, json.dumps(focus_areas),
                parent_id, tagged_jd_id, _now_iso(),
                artifact_uid, parent_uid, for_candidate,
                resolved_baseline,
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
    folder_path: Optional[str] = None,
) -> int:
    """Insert a jds row, return the new id."""
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO jds
                (source, source_ref, company, role_title, raw_text,
                 analyzer_findings, focus_areas_required, focus_areas_nice,
                 created_at, folder_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                folder_path,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def add_cover_letter(
    file_path: Optional[str],
    resume_version_id: int,
    jd_id: int,
    template: str,
    artifact_uid: Optional[str] = None,
    parent_uid: Optional[str] = None,
    for_candidate: Optional[str] = None,
) -> int:
    """Insert a cover_letters row, return the new id."""
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO cover_letters
                (file_path, resume_version_id, jd_id, template, created_at,
                 artifact_uid, parent_uid, for_candidate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (file_path, resume_version_id, jd_id, template, _now_iso(),
             artifact_uid, parent_uid, for_candidate),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def add_application(
    jd_id: int,
    resume_version_id: int,
    cover_letter_id: Optional[int],
    submitted_at: datetime,
    channel: str,
    agency_name: Optional[str] = None,
    recruiter_contact: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    """Insert an applications row, return the new id."""
    if channel not in APPLICATION_CHANNELS:
        raise ValueError(
            f"Unknown channel {channel!r}. Valid: {', '.join(APPLICATION_CHANNELS)}"
        )
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO applications
                (jd_id, resume_version_id, cover_letter_id, submitted_at,
                 channel, agency_name, recruiter_contact, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                jd_id, resume_version_id, cover_letter_id,
                submitted_at.isoformat(),
                channel, agency_name, recruiter_contact, notes,
                _now_iso(),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def record_outcome(
    application_id: int,
    event_type: str,
    event_date: datetime,
    notes: Optional[str] = None,
) -> int:
    """Insert an outcomes row, return the new id."""
    if event_type not in OUTCOME_EVENT_TYPES:
        raise ValueError(
            f"Unknown event_type {event_type!r}. Valid: {', '.join(OUTCOME_EVENT_TYPES)}"
        )
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO outcomes
                (application_id, event_type, event_date, notes, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                application_id, event_type, event_date.isoformat(),
                notes, _now_iso(),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
