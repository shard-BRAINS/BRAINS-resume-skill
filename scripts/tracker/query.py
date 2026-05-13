"""Read-side public API for the tracker.

These helpers all return dataclasses or lists of dataclasses defined in
scripts/tracker/models.py. SQL lives only here (and in db.py / migrations).
Consumers must never construct SQL themselves.
"""
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from scripts.tracker.db import get_db_path, open_db


# --- Result types (lightweight DTOs distinct from the row dataclasses) --------

@dataclass
class ApplicationRow:
    """Joined view of applications + jds + latest outcome.

    Distinct from models.Application because list views need company/role from
    the JD and the latest event_type from outcomes — those are joins, not
    columns on applications itself.
    """
    id: int
    company: str
    role_title: str
    submitted_at: str
    channel: str
    agency_name: Optional[str]
    resume_version_id: int
    cover_letter_id: Optional[int]
    latest_outcome: Optional[str]


# --- Queries ------------------------------------------------------------------

def list_applications(
    company: Optional[str] = None,
    since: Optional[datetime] = None,
    status: Optional[str] = None,
) -> List[ApplicationRow]:
    """Return active applications (archived_at IS NULL), filtered by criteria.

    status:
        - None or 'all' — no filter
        - 'open' — applications with no rejection/offer/withdrew outcome yet
        - 'closed' — applications with a terminal outcome
    """
    conn = open_db()
    try:
        sql = """
            SELECT a.id, j.company, j.role_title, a.submitted_at, a.channel,
                   a.agency_name, a.resume_version_id, a.cover_letter_id,
                   (
                       SELECT event_type FROM outcomes
                       WHERE application_id = a.id AND archived_at IS NULL
                       ORDER BY event_date DESC, id DESC
                       LIMIT 1
                   ) AS latest_outcome
            FROM applications a
            JOIN jds j ON j.id = a.jd_id
            WHERE a.archived_at IS NULL
        """
        params: list = []
        if company is not None:
            sql += " AND LOWER(j.company) = LOWER(?)"
            params.append(company)
        if since is not None:
            sql += " AND a.submitted_at >= ?"
            params.append(since.isoformat())
        sql += " ORDER BY a.submitted_at DESC"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    results = [
        ApplicationRow(
            id=r[0], company=r[1], role_title=r[2], submitted_at=r[3],
            channel=r[4], agency_name=r[5], resume_version_id=r[6],
            cover_letter_id=r[7], latest_outcome=r[8],
        )
        for r in rows
    ]

    if status == "open":
        terminal = {"offer", "rejection", "withdrew"}
        results = [r for r in results if r.latest_outcome not in terminal]
    elif status == "closed":
        terminal = {"offer", "rejection", "withdrew"}
        results = [r for r in results if r.latest_outcome in terminal]

    return results


def find_duplicates(
    company: str,
    role_title: str,
    within_days: int = 60,
) -> List[ApplicationRow]:
    """Return applications to the same company+role within the window.

    Gracefully returns [] when the db file doesn't exist (tracker never used).
    """
    if not get_db_path().exists():
        return []
    cutoff = datetime.now() - timedelta(days=within_days)
    rows = list_applications(company=company, since=cutoff)
    # Filter by role_title (case-insensitive substring match)
    role_lower = role_title.lower()
    return [r for r in rows if role_lower in r.role_title.lower()
            or r.role_title.lower() in role_lower]
