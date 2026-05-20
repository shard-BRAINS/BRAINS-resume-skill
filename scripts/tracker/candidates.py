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


def _row_to_candidate(row) -> Candidate:
    return Candidate(
        id=row[0], first_name=row[1], last_name=row[2],
        focus_areas=json.loads(row[3] or "[]"),
        healthy_weekly_rate=row[4], pacing_notes=row[5],
        created_at=row[6], archived_at=row[7],
    )


def create_candidate(
    first_name: str,
    last_name: str,
    focus_areas: List[str],
    healthy_weekly_rate: Optional[int],
    pacing_notes: Optional[str],
) -> int:
    conn = open_db()
    try:
        cur = conn.execute(
            """INSERT INTO candidates
                 (first_name, last_name, focus_areas, healthy_weekly_rate,
                  pacing_notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (first_name, last_name, json.dumps(focus_areas),
             healthy_weekly_rate, pacing_notes, _now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_candidate(candidate_id: int) -> Optional[Candidate]:
    conn = open_db()
    try:
        row = conn.execute(
            """SELECT id, first_name, last_name, focus_areas,
                      healthy_weekly_rate, pacing_notes,
                      created_at, archived_at
               FROM candidates WHERE id=?""",
            (candidate_id,),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_candidate(row) if row else None


def list_candidates(include_archived: bool = False) -> List[Candidate]:
    conn = open_db()
    try:
        sql = """SELECT id, first_name, last_name, focus_areas,
                        healthy_weekly_rate, pacing_notes,
                        created_at, archived_at
                 FROM candidates"""
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
