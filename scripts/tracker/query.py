"""Read-side public API for the tracker.

These helpers all return dataclasses or lists of dataclasses defined in
scripts/tracker/models.py. SQL lives only here (and in db.py / migrations).
Consumers must never construct SQL themselves.
"""
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import List, Optional

from scripts.tracker.db import get_db_path, open_db
from scripts.tracker.models import WeeklySummary, EfficacyRow, ResumeVersion, CoverLetter
from scripts.tracker.profile import read_profile


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


# --- Task 8: weekly_summary + efficacy_by_template ----

INTERVIEW_EVENT_TYPES = {"phone_screen", "first_round", "second_round", "take_home"}


def weekly_summary(now: Optional[datetime] = None) -> WeeklySummary:
    """Return a summary of the last 7 days: application count, outcomes by
    type, and pacing vs the user's healthy_weekly_rate (if set)."""
    if now is None:
        now = datetime.now()
    week_ago = now - timedelta(days=7)

    if not get_db_path().exists():
        return WeeklySummary(
            week_starting=week_ago.date().isoformat(),
            applications_count=0,
            outcomes_by_type={},
            pacing_vs_target=None,
        )

    conn = open_db()
    try:
        app_count = conn.execute(
            "SELECT COUNT(*) FROM applications "
            "WHERE archived_at IS NULL AND submitted_at >= ?",
            (week_ago.isoformat(),),
        ).fetchone()[0]

        outcome_rows = conn.execute(
            "SELECT event_type, COUNT(*) FROM outcomes "
            "WHERE archived_at IS NULL AND event_date >= ? "
            "GROUP BY event_type",
            (week_ago.isoformat(),),
        ).fetchall()
        outcomes_by_type = {row[0]: row[1] for row in outcome_rows}
    finally:
        conn.close()

    target = read_profile().healthy_weekly_rate
    if target is None:
        pacing = None
    elif app_count > target:
        pacing = "above"
    elif app_count == target:
        pacing = "at"
    else:
        pacing = "below"

    return WeeklySummary(
        week_starting=week_ago.date().isoformat(),
        applications_count=app_count,
        outcomes_by_type=outcomes_by_type,
        pacing_vs_target=pacing,
    )


def efficacy_by_template() -> List[EfficacyRow]:
    """Return per-template counts of submitted/callback/interview/offer/rejection.

    Each application contributes once to each event-type count it has produced.
    An application with phone_screen + first_round + offer contributes:
      - submitted_count: 1
      - interview_count: 2 (phone_screen + first_round)
      - offer_count: 1
    """
    if not get_db_path().exists():
        return []

    conn = open_db()
    try:
        rows = conn.execute(
            """
            SELECT rv.template,
                   a.id,
                   (SELECT GROUP_CONCAT(event_type, ',')
                    FROM outcomes
                    WHERE application_id = a.id AND archived_at IS NULL)
                   AS event_types
            FROM applications a
            JOIN resume_versions rv ON rv.id = a.resume_version_id
            WHERE a.archived_at IS NULL
            """
        ).fetchall()
    finally:
        conn.close()

    by_template: dict = defaultdict(lambda: {
        "submitted": 0, "callback": 0, "interview": 0,
        "offer": 0, "rejection": 0,
    })
    for template, _app_id, event_csv in rows:
        bucket = by_template[template]
        bucket["submitted"] += 1
        if not event_csv:
            continue
        events = event_csv.split(",")
        for ev in events:
            if ev == "callback":
                bucket["callback"] += 1
            elif ev in INTERVIEW_EVENT_TYPES:
                bucket["interview"] += 1
            elif ev == "offer":
                bucket["offer"] += 1
            elif ev == "rejection":
                bucket["rejection"] += 1

    return [
        EfficacyRow(
            template=template,
            submitted_count=counts["submitted"],
            callback_count=counts["callback"],
            interview_count=counts["interview"],
            offer_count=counts["offer"],
            rejection_count=counts["rejection"],
        )
        for template, counts in sorted(by_template.items())
    ]


def get_artifact_by_uid(uid: str) -> ResumeVersion | CoverLetter | None:
    """Look up an artifact by its 6-char Crockford-base32 UID across
    both resume_versions and cover_letters. Returns None if not found.
    """
    conn = open_db()
    try:
        row = conn.execute(
            """SELECT id, file_path, template, focus_areas, parent_id,
                      tagged_jd_id, created_at, archived_at,
                      artifact_uid, parent_uid, for_candidate
               FROM resume_versions WHERE artifact_uid = ?""",
            (uid,),
        ).fetchone()
        if row:
            return ResumeVersion(
                id=row[0],
                file_path=row[1],
                template=row[2],
                focus_areas=json.loads(row[3]),
                parent_id=row[4],
                tagged_jd_id=row[5],
                created_at=row[6],
                archived_at=row[7],
                artifact_uid=row[8],
                parent_uid=row[9],
                for_candidate=row[10],
            )
        row = conn.execute(
            """SELECT id, file_path, resume_version_id, jd_id, template,
                      created_at, archived_at, artifact_uid, parent_uid,
                      for_candidate
               FROM cover_letters WHERE artifact_uid = ?""",
            (uid,),
        ).fetchone()
        if row:
            return CoverLetter(
                id=row[0],
                file_path=row[1],
                resume_version_id=row[2],
                jd_id=row[3],
                template=row[4],
                created_at=row[5],
                archived_at=row[6],
                artifact_uid=row[7],
                parent_uid=row[8],
                for_candidate=row[9],
            )
        return None
    finally:
        conn.close()


def list_artifacts_for_candidate(name: str) -> list:
    """Return all resume_versions + cover_letters whose for_candidate matches name."""
    conn = open_db()
    try:
        results: list = []
        for row in conn.execute(
            """SELECT id, file_path, template, focus_areas, parent_id, tagged_jd_id,
                      created_at, archived_at, artifact_uid, parent_uid, for_candidate
               FROM resume_versions WHERE for_candidate = ? AND archived_at IS NULL
               ORDER BY created_at DESC""",
            (name,),
        ):
            results.append(ResumeVersion(
                id=row[0], file_path=row[1], template=row[2],
                focus_areas=json.loads(row[3] or "[]"),
                parent_id=row[4], tagged_jd_id=row[5],
                created_at=row[6], archived_at=row[7],
                artifact_uid=row[8], parent_uid=row[9],
                for_candidate=row[10],
            ))
        for row in conn.execute(
            """SELECT id, file_path, resume_version_id, jd_id, template,
                      created_at, archived_at, artifact_uid, parent_uid, for_candidate
               FROM cover_letters WHERE for_candidate = ? AND archived_at IS NULL
               ORDER BY created_at DESC""",
            (name,),
        ):
            results.append(CoverLetter(
                id=row[0], file_path=row[1], resume_version_id=row[2],
                jd_id=row[3], template=row[4],
                created_at=row[5], archived_at=row[6],
                artifact_uid=row[7], parent_uid=row[8],
                for_candidate=row[9],
            ))
        return results
    finally:
        conn.close()
