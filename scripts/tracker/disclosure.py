"""CRUD for the disclosure_sessions table.

A disclosure session records one walk through the disclosure-decision
framework (default position, six factors, three strengths) — the user's
factor answers, the landed strength, and optionally a generated worksheet
artifact_uid.

The candidate's *current* disclosure preference is the most-recent
non-archived session. Downstream workflows (tailor, cover-letter, review)
read it via get_latest_for_candidate.

Follows the same shape as scripts/tracker/candidates.py — each top-level
function opens a fresh DB connection.
"""
from datetime import datetime
from typing import Optional

from scripts.tracker.db import open_db
from scripts.tracker.models import DISCLOSURE_STRENGTHS, DisclosureSession


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


_SESSION_COLS = (
    "id, candidate_id, created_at, target_employer, target_role, "
    "factor_1, factor_2, factor_3, factor_4, factor_5, factor_6, "
    "landed_strength, notes, artifact_uid, archived_at"
)


def _row_to_session(row) -> DisclosureSession:
    return DisclosureSession(
        id=row[0],
        candidate_id=row[1],
        created_at=row[2],
        target_employer=row[3],
        target_role=row[4],
        factor_1=row[5],
        factor_2=row[6],
        factor_3=row[7],
        factor_4=row[8],
        factor_5=row[9],
        factor_6=row[10],
        landed_strength=row[11],
        notes=row[12],
        artifact_uid=row[13],
        archived_at=row[14],
    )


def _validate_strength(landed_strength: str) -> None:
    if landed_strength not in DISCLOSURE_STRENGTHS:
        raise ValueError(
            f"landed_strength must be one of {DISCLOSURE_STRENGTHS}, "
            f"got {landed_strength!r}"
        )


def create_session(
    candidate_id: int,
    landed_strength: str,
    *,
    target_employer: Optional[str] = None,
    target_role: Optional[str] = None,
    factor_1: Optional[str] = None,
    factor_2: Optional[str] = None,
    factor_3: Optional[str] = None,
    factor_4: Optional[str] = None,
    factor_5: Optional[str] = None,
    factor_6: Optional[str] = None,
    notes: Optional[str] = None,
    artifact_uid: Optional[str] = None,
) -> int:
    """Insert a disclosure_sessions row, return the new id."""
    _validate_strength(landed_strength)
    conn = open_db()
    try:
        cur = conn.execute(
            """INSERT INTO disclosure_sessions
                 (candidate_id, created_at, target_employer, target_role,
                  factor_1, factor_2, factor_3, factor_4, factor_5, factor_6,
                  landed_strength, notes, artifact_uid)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate_id, _now_iso(), target_employer, target_role,
                factor_1, factor_2, factor_3, factor_4, factor_5, factor_6,
                landed_strength, notes, artifact_uid,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_session(session_id: int) -> Optional[DisclosureSession]:
    conn = open_db()
    try:
        row = conn.execute(
            f"SELECT {_SESSION_COLS} FROM disclosure_sessions WHERE id=?",
            (session_id,),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_session(row) if row else None


def list_sessions_for_candidate(
    candidate_id: int,
    include_archived: bool = False,
) -> list[DisclosureSession]:
    """Return all sessions for a candidate, most-recent first."""
    conn = open_db()
    try:
        sql = f"SELECT {_SESSION_COLS} FROM disclosure_sessions WHERE candidate_id=?"
        if not include_archived:
            sql += " AND archived_at IS NULL"
        sql += " ORDER BY created_at DESC, id DESC"
        rows = conn.execute(sql, (candidate_id,)).fetchall()
    finally:
        conn.close()
    return [_row_to_session(r) for r in rows]


def get_latest_for_candidate(candidate_id: int) -> Optional[DisclosureSession]:
    """Return the most-recent non-archived session for a candidate, or None.

    This is the read used by downstream auto-apply (tailor, cover-letter,
    review). If it returns None the candidate has no recorded preference
    and downstream workflows should leave content unchanged.
    """
    sessions = list_sessions_for_candidate(candidate_id, include_archived=False)
    return sessions[0] if sessions else None


def update_landed_strength(session_id: int, landed_strength: str) -> None:
    _validate_strength(landed_strength)
    conn = open_db()
    try:
        conn.execute(
            "UPDATE disclosure_sessions SET landed_strength=? WHERE id=?",
            (landed_strength, session_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_artifact_uid(session_id: int, artifact_uid: str) -> None:
    """Attach an artifact_uid to a session (after the worksheet is generated)."""
    conn = open_db()
    try:
        conn.execute(
            "UPDATE disclosure_sessions SET artifact_uid=? WHERE id=?",
            (artifact_uid, session_id),
        )
        conn.commit()
    finally:
        conn.close()


def archive_session(session_id: int) -> None:
    conn = open_db()
    try:
        conn.execute(
            "UPDATE disclosure_sessions SET archived_at=? WHERE id=?",
            (_now_iso(), session_id),
        )
        conn.commit()
    finally:
        conn.close()
