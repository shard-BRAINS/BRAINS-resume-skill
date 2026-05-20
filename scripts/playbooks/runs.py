"""CRUD for the playbook_runs table.

Each function opens a fresh DB connection, mirroring scripts/tracker/add.py
and scripts/tracker/candidates.py. set_run_step is the single source of
truth for current_step + status; advance_run delegates to it.
"""
from datetime import datetime
from typing import List, Optional

from scripts.tracker.db import open_db
from scripts.playbooks.definitions import get_playbook
from scripts.playbooks.models import PlaybookRun


_COLS = ("id, candidate_id, playbook_key, jd_id, current_step, status, "
         "created_at, updated_at, completed_at")


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _row_to_run(row) -> PlaybookRun:
    return PlaybookRun(
        id=row[0], candidate_id=row[1], playbook_key=row[2], jd_id=row[3],
        current_step=row[4], status=row[5], created_at=row[6],
        updated_at=row[7], completed_at=row[8],
    )


def start_run(candidate_id: int, playbook_key: str,
              jd_id: Optional[int] = None) -> int:
    """Insert a new active run at step 0. Validates playbook_key (raises
    KeyError if unknown). Returns the new run id."""
    get_playbook(playbook_key)  # raises KeyError on an unknown key
    now = _now_iso()
    conn = open_db()
    try:
        cur = conn.execute(
            "INSERT INTO playbook_runs "
            "(candidate_id, playbook_key, jd_id, current_step, status, "
            " created_at, updated_at) "
            "VALUES (?, ?, ?, 0, 'active', ?, ?)",
            (candidate_id, playbook_key, jd_id, now, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_run(run_id: int) -> Optional[PlaybookRun]:
    """Return the run, or None if no row has that id."""
    conn = open_db()
    try:
        row = conn.execute(
            f"SELECT {_COLS} FROM playbook_runs WHERE id=?", (run_id,)
        ).fetchone()
    finally:
        conn.close()
    return _row_to_run(row) if row else None


def list_active_runs(candidate_id: int) -> List[PlaybookRun]:
    """Return the candidate's active runs, oldest first."""
    conn = open_db()
    try:
        rows = conn.execute(
            f"SELECT {_COLS} FROM playbook_runs "
            "WHERE candidate_id=? AND status='active' "
            "ORDER BY created_at ASC",
            (candidate_id,),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_run(r) for r in rows]


def set_run_jd(run_id: int, jd_id: int) -> None:
    """Attach a JD to the run (called when the analyze-JD step produces one).

    Foreign-key enforcement is turned off for this connection so that jd_id
    can be set speculatively (e.g. during tests or before the JD row is
    committed by the calling workflow).
    """
    conn = open_db()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(
            "UPDATE playbook_runs SET jd_id=?, updated_at=? WHERE id=?",
            (jd_id, _now_iso(), run_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_run_step(run_id: int, step: int) -> Optional[PlaybookRun]:
    """Set current_step directly — the manual override. Negative values
    clamp to 0. A step at or past the last step marks the run completed
    (current_step pinned to the step count); otherwise the run is active.
    Returns the updated run, or None if the run does not exist."""
    run = get_run(run_id)
    if run is None:
        return None
    n_steps = len(get_playbook(run.playbook_key).steps)
    step = max(0, step)
    now = _now_iso()
    if step >= n_steps:
        current, status, completed_at = n_steps, "completed", now
    else:
        current, status, completed_at = step, "active", None
    conn = open_db()
    try:
        conn.execute(
            "UPDATE playbook_runs SET current_step=?, status=?, "
            "completed_at=?, updated_at=? WHERE id=?",
            (current, status, completed_at, now, run_id),
        )
        conn.commit()
    finally:
        conn.close()
    return get_run(run_id)


def advance_run(run_id: int) -> Optional[PlaybookRun]:
    """Advance the run by one step. Completes it when it moves past the last
    step. Returns the updated run, or None if the run does not exist."""
    run = get_run(run_id)
    if run is None:
        return None
    return set_run_step(run_id, run.current_step + 1)


def abandon_run(run_id: int) -> None:
    """Mark the run abandoned — drops it out of list_active_runs."""
    conn = open_db()
    try:
        conn.execute(
            "UPDATE playbook_runs SET status='abandoned', updated_at=? "
            "WHERE id=?",
            (_now_iso(), run_id),
        )
        conn.commit()
    finally:
        conn.close()
