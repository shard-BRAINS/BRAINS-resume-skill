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
from scripts.tracker.models import (
    WeeklySummary, EfficacyRow, ResumeVersion, CoverLetter, JD,
)


# --- Candidate scoping --------------------------------------------------------

def _scope_candidate_clause(candidate_id):
    """Return (WHERE-fragment, params) for the candidate scope.

    None  -> filter by active candidate (or no filter if none set)
    0     -> no filter (all candidates)
    int>0 -> filter by that candidate
    """
    if candidate_id == 0:
        return ("", ())
    if candidate_id is None:
        from scripts.tracker.candidates import get_active_candidate
        active = get_active_candidate()
        if active is None:
            return ("", ())  # no active candidate: behave like 0 for read paths
        candidate_id = active.id
    return ("candidate_id = ?", (candidate_id,))


def _resolve_scope_candidate_id(candidate_id):
    """Resolve a candidate scope to a concrete id (or None for 'all').

    Mirrors `_scope_candidate_clause` but yields an id rather than a SQL
    fragment — used where the column name must be table-qualified inside
    a JOIN (e.g. `j.candidate_id`).

    Returns:
        None  -> no filter (all candidates), for the 0 sentinel or when no
                 active candidate is set.
        int   -> the candidate id to filter by.
    """
    if candidate_id == 0:
        return None
    if candidate_id is None:
        from scripts.tracker.candidates import get_active_candidate
        active = get_active_candidate()
        return active.id if active is not None else None
    return candidate_id


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
    candidate_id: Optional[int] = None,
) -> List[ApplicationRow]:
    """Return active applications (archived_at IS NULL), filtered by criteria.

    status:
        - None or 'all' — no filter
        - 'open' — applications with no rejection/offer/withdrew outcome yet
        - 'closed' — applications with a terminal outcome

    candidate_id (scoped via the JD that the application targets):
        - None — the active candidate (no filter if none set)
        - 0    — all candidates
        - int  — that candidate
    """
    scope_cid = _resolve_scope_candidate_id(candidate_id)
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
        if scope_cid is not None:
            sql += " AND j.candidate_id = ?"
            params.append(scope_cid)
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


def list_jds(candidate_id: Optional[int] = None) -> List[JD]:
    """Return active JDs (archived_at IS NULL), scoped to a candidate.

    candidate_id:
        - None — the active candidate (no filter if none set)
        - 0    — all candidates
        - int  — that candidate

    Gracefully returns [] when the db file doesn't exist (tracker never used).
    """
    if not get_db_path().exists():
        return []
    scope_sql, scope_params = _scope_candidate_clause(candidate_id)
    conn = open_db()
    try:
        sql = """SELECT id, source, source_ref, company, role_title, raw_text,
                        analyzer_findings, focus_areas_required,
                        focus_areas_nice, created_at, archived_at,
                        folder_path, candidate_id
                 FROM jds
                 WHERE archived_at IS NULL"""
        if scope_sql:
            sql += f" AND {scope_sql}"
        sql += " ORDER BY created_at DESC"
        rows = conn.execute(sql, scope_params).fetchall()
    finally:
        conn.close()
    return [
        JD(
            id=r[0], source=r[1], source_ref=r[2], company=r[3],
            role_title=r[4], raw_text=r[5],
            analyzer_findings=json.loads(r[6] or "{}"),
            focus_areas_required=json.loads(r[7] or "[]"),
            focus_areas_nice=json.loads(r[8] or "[]"),
            created_at=r[9], archived_at=r[10],
            folder_path=r[11], candidate_id=r[12],
        )
        for r in rows
    ]


# --- Task 8: weekly_summary + efficacy_by_template ----

INTERVIEW_EVENT_TYPES = {"phone_screen", "first_round", "second_round", "take_home"}


def weekly_summary(
    now: Optional[datetime] = None,
    candidate_id: Optional[int] = None,
) -> WeeklySummary:
    """Return a summary of the last 7 days: application count, outcomes by
    type, and pacing vs the candidate's healthy_weekly_rate (if set).

    candidate_id (scoped via the JD that each application targets):
        - None — the active candidate (no filter if none set)
        - 0    — all candidates
        - int  — that candidate

    The pacing target is the resolved candidate's healthy_weekly_rate. When
    the scope is 'all candidates' (0) or no active candidate is set, there is
    no single target, so pacing is None.
    """
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

    scope_cid = _resolve_scope_candidate_id(candidate_id)

    conn = open_db()
    try:
        app_sql = (
            "SELECT COUNT(*) FROM applications a "
            "JOIN jds j ON j.id = a.jd_id "
            "WHERE a.archived_at IS NULL AND a.submitted_at >= ?"
        )
        app_params: list = [week_ago.isoformat()]
        if scope_cid is not None:
            app_sql += " AND j.candidate_id = ?"
            app_params.append(scope_cid)
        app_count = conn.execute(app_sql, app_params).fetchone()[0]

        outcome_sql = (
            "SELECT o.event_type, COUNT(*) FROM outcomes o "
            "JOIN applications a ON a.id = o.application_id "
            "JOIN jds j ON j.id = a.jd_id "
            "WHERE o.archived_at IS NULL AND o.event_date >= ?"
        )
        outcome_params: list = [week_ago.isoformat()]
        if scope_cid is not None:
            outcome_sql += " AND j.candidate_id = ?"
            outcome_params.append(scope_cid)
        outcome_sql += " GROUP BY o.event_type"
        outcome_rows = conn.execute(outcome_sql, outcome_params).fetchall()
        outcomes_by_type = {row[0]: row[1] for row in outcome_rows}
    finally:
        conn.close()

    # Pacing target lives on the candidate. Only meaningful for a single
    # resolved candidate; 'all candidates' has no single target.
    target = None
    if scope_cid is not None:
        from scripts.tracker.candidates import get_candidate
        candidate = get_candidate(scope_cid)
        if candidate is not None:
            target = candidate.healthy_weekly_rate

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


def efficacy_by_template(candidate_id: Optional[int] = None) -> List[EfficacyRow]:
    """Return per-template counts of submitted/callback/interview/offer/rejection.

    Each application contributes once to each event-type count it has produced.
    An application with phone_screen + first_round + offer contributes:
      - submitted_count: 1
      - interview_count: 2 (phone_screen + first_round)
      - offer_count: 1

    candidate_id (scoped via the JD that each application targets):
        - None — the active candidate (no filter if none set)
        - 0    — all candidates
        - int  — that candidate
    """
    if not get_db_path().exists():
        return []

    scope_cid = _resolve_scope_candidate_id(candidate_id)
    conn = open_db()
    try:
        sql = """
            SELECT rv.template,
                   a.id,
                   (SELECT GROUP_CONCAT(event_type, ',')
                    FROM outcomes
                    WHERE application_id = a.id AND archived_at IS NULL)
                   AS event_types
            FROM applications a
            JOIN resume_versions rv ON rv.id = a.resume_version_id
            JOIN jds j ON j.id = a.jd_id
            WHERE a.archived_at IS NULL
        """
        params: list = []
        if scope_cid is not None:
            sql += " AND j.candidate_id = ?"
            params.append(scope_cid)
        rows = conn.execute(sql, params).fetchall()
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
    """Return all resume_versions + cover_letters whose candidate matches the name.

    Matches by candidate first+last name (split via outputs.naming.split_candidate_name)
    JOINed on the candidates table.
    """
    from scripts.outputs.naming import split_candidate_name
    first, last = split_candidate_name(name)
    conn = open_db()
    try:
        results: list = []
        for row in conn.execute(
            """SELECT rv.id, rv.file_path, rv.template, rv.focus_areas,
                      rv.parent_id, rv.tagged_jd_id, rv.created_at,
                      rv.archived_at, rv.artifact_uid, rv.parent_uid,
                      rv.for_candidate, rv.candidate_id
               FROM resume_versions rv
               JOIN candidates c ON c.id = rv.candidate_id
               WHERE c.first_name = ? AND c.last_name = ?
                 AND rv.archived_at IS NULL
               ORDER BY rv.created_at DESC""",
            (first, last),
        ):
            results.append(ResumeVersion(
                id=row[0], file_path=row[1], template=row[2],
                focus_areas=json.loads(row[3] or "[]"),
                parent_id=row[4], tagged_jd_id=row[5],
                created_at=row[6], archived_at=row[7],
                artifact_uid=row[8], parent_uid=row[9],
                for_candidate=row[10], candidate_id=row[11],
            ))
        for row in conn.execute(
            """SELECT cl.id, cl.file_path, cl.resume_version_id, cl.jd_id,
                      cl.template, cl.created_at, cl.archived_at,
                      cl.artifact_uid, cl.parent_uid, cl.for_candidate,
                      cl.candidate_id
               FROM cover_letters cl
               JOIN candidates c ON c.id = cl.candidate_id
               WHERE c.first_name = ? AND c.last_name = ?
                 AND cl.archived_at IS NULL
               ORDER BY cl.created_at DESC""",
            (first, last),
        ):
            results.append(CoverLetter(
                id=row[0], file_path=row[1], resume_version_id=row[2],
                jd_id=row[3], template=row[4],
                created_at=row[5], archived_at=row[6],
                artifact_uid=row[7], parent_uid=row[8],
                for_candidate=row[9], candidate_id=row[10],
            ))
        return results
    finally:
        conn.close()
