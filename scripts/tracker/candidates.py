"""CRUD for the candidates table.

Each top-level function opens a fresh DB connection. The active candidate
is stored in profile.json's active_candidate_id field; this module is the
single read/write path for that pointer.
"""
import json
from datetime import datetime
from typing import List, Optional

from scripts.tracker.db import open_db
from scripts.tracker.models import Candidate, Profile
from scripts.tracker.profile import read_profile, write_profile


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


_CANDIDATE_COLS = (
    "id, first_name, last_name, focus_areas, healthy_weekly_rate, "
    "pacing_notes, created_at, archived_at, email, career_stage, direction, "
    "target_roles, target_industries, leadership_intent, work_preferences, "
    "location, relocation_open, role_priorities, timeline, intent_collected_at"
)


def _row_to_candidate(row) -> Candidate:
    return Candidate(
        id=row[0], first_name=row[1], last_name=row[2],
        focus_areas=json.loads(row[3] or "[]"),
        healthy_weekly_rate=row[4], pacing_notes=row[5],
        created_at=row[6], archived_at=row[7],
        email=row[8], career_stage=row[9], direction=row[10],
        target_roles=json.loads(row[11] or "[]"),
        target_industries=json.loads(row[12] or "[]"),
        leadership_intent=row[13],
        work_preferences=json.loads(row[14] or "[]"),
        location=row[15], relocation_open=row[16],
        role_priorities=row[17], timeline=row[18],
        intent_collected_at=row[19],
    )


def create_candidate(
    first_name: str,
    last_name: str,
    focus_areas: List[str],
    healthy_weekly_rate: Optional[int],
    pacing_notes: Optional[str],
    email: Optional[str] = None,
) -> int:
    conn = open_db()
    try:
        cur = conn.execute(
            """INSERT INTO candidates
                 (first_name, last_name, focus_areas, healthy_weekly_rate,
                  pacing_notes, created_at, email)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (first_name, last_name, json.dumps(focus_areas),
             healthy_weekly_rate, pacing_notes, _now_iso(), email),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_candidate(candidate_id: int) -> Optional[Candidate]:
    conn = open_db()
    try:
        row = conn.execute(
            f"SELECT {_CANDIDATE_COLS} FROM candidates WHERE id=?",
            (candidate_id,),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_candidate(row) if row else None


def list_candidates(include_archived: bool = False) -> List[Candidate]:
    conn = open_db()
    try:
        sql = f"SELECT {_CANDIDATE_COLS} FROM candidates"
        if not include_archived:
            sql += " WHERE archived_at IS NULL"
        sql += " ORDER BY created_at ASC"
        rows = conn.execute(sql).fetchall()
    finally:
        conn.close()
    return [_row_to_candidate(r) for r in rows]


def update_candidate(
    candidate_id: int,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    focus_areas: Optional[List[str]] = None,
    healthy_weekly_rate: Optional[int] = None,
    pacing_notes: Optional[str] = None,
    email: Optional[str] = None,
) -> None:
    """Partial update. Only fields provided as non-None are changed.

    Note: passing None means 'do not change'. To explicitly clear
    healthy_weekly_rate or pacing_notes, set them via direct SQL
    (out of scope for this helper).
    """
    sets, params = [], []
    if first_name is not None:
        sets.append("first_name=?"); params.append(first_name)
    if last_name is not None:
        sets.append("last_name=?"); params.append(last_name)
    if focus_areas is not None:
        sets.append("focus_areas=?"); params.append(json.dumps(focus_areas))
    if healthy_weekly_rate is not None:
        sets.append("healthy_weekly_rate=?"); params.append(healthy_weekly_rate)
    if pacing_notes is not None:
        sets.append("pacing_notes=?"); params.append(pacing_notes)
    if email is not None:
        sets.append("email=?"); params.append(email)
    if not sets:
        return
    params.append(candidate_id)
    conn = open_db()
    try:
        conn.execute(f"UPDATE candidates SET {', '.join(sets)} WHERE id=?", params)
        conn.commit()
    finally:
        conn.close()


def archive_candidate(candidate_id: int) -> None:
    conn = open_db()
    try:
        conn.execute(
            "UPDATE candidates SET archived_at=? WHERE id=?",
            (_now_iso(), candidate_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_active_candidate(candidate_id: int) -> None:
    profile = read_profile()
    write_profile(Profile(
        active_candidate_id=candidate_id,
        log_handoffs=profile.log_handoffs,
    ))


def get_active_candidate() -> Optional[Candidate]:
    profile = read_profile()
    if profile.active_candidate_id is None:
        return None
    return get_candidate(profile.active_candidate_id)


def find_or_create_by_name(name: str) -> int:
    """Find a candidate by free-text name; create with empty focus areas if missing."""
    from scripts.outputs.naming import split_candidate_name
    from scripts.tracker.db import open_db
    first, last = split_candidate_name(name)
    conn = open_db()
    try:
        row = conn.execute(
            """SELECT id FROM candidates
               WHERE first_name=? AND last_name=? AND archived_at IS NULL
               ORDER BY id LIMIT 1""",
            (first, last),
        ).fetchone()
        if row is not None:
            return row[0]
        cur = conn.execute(
            """INSERT INTO candidates
                 (first_name, last_name, focus_areas, healthy_weekly_rate,
                  pacing_notes, created_at)
               VALUES (?, ?, '[]', NULL, NULL, ?)""",
            (first, last, _now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_candidate_intent(
    candidate_id: int,
    *,
    career_stage: Optional[str] = None,
    direction: Optional[str] = None,
    target_roles: Optional[List[str]] = None,
    target_industries: Optional[List[str]] = None,
    leadership_intent: Optional[str] = None,
    work_preferences: Optional[List[str]] = None,
    location: Optional[str] = None,
    relocation_open: Optional[int] = None,
    role_priorities: Optional[str] = None,
    timeline: Optional[str] = None,
) -> None:
    """Write the career-intent fields and stamp intent_collected_at.

    The onboarding form submits every field together, so this is a full
    write of the intent block (not a partial update). List fields are
    JSON-encoded; None lists become an empty JSON array.
    """
    conn = open_db()
    try:
        conn.execute(
            """UPDATE candidates SET
                 career_stage=?, direction=?, target_roles=?,
                 target_industries=?, leadership_intent=?, work_preferences=?,
                 location=?, relocation_open=?, role_priorities=?, timeline=?,
                 intent_collected_at=?
               WHERE id=?""",
            (
                career_stage, direction, json.dumps(target_roles or []),
                json.dumps(target_industries or []), leadership_intent,
                json.dumps(work_preferences or []), location, relocation_open,
                role_priorities, timeline, _now_iso(), candidate_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()
