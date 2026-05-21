"""CRUD for the dashboard_layout table (per-candidate widget canvas).

Pure DB access — this module deliberately knows nothing about the widget
catalog. Reconciling a saved layout against the catalog is catalog.py's job.
The dashboard_layout table was created by migration 0006 (Phase 1).
"""
from datetime import datetime
from typing import List, Tuple

from scripts.tracker.db import open_db


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def get_saved_layout(candidate_id: int) -> List[Tuple[str, bool]]:
    """Return the candidate's saved layout as an ordered list of
    (widget_key, enabled). Empty list when the candidate has no saved rows."""
    conn = open_db()
    try:
        rows = conn.execute(
            "SELECT widget_key, enabled FROM dashboard_layout "
            "WHERE candidate_id=? ORDER BY position ASC",
            (candidate_id,),
        ).fetchall()
    finally:
        conn.close()
    return [(r[0], bool(r[1])) for r in rows]


def save_layout(candidate_id: int, entries: List[Tuple[str, bool]]) -> None:
    """Replace the candidate's layout with `entries` (ordered list of
    (widget_key, enabled)). Position is the list index."""
    now = _now_iso()
    conn = open_db()
    try:
        conn.execute(
            "DELETE FROM dashboard_layout WHERE candidate_id=?", (candidate_id,)
        )
        conn.executemany(
            "INSERT INTO dashboard_layout "
            "(candidate_id, widget_key, position, enabled, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (candidate_id, key, pos, 1 if enabled else 0, now)
                for pos, (key, enabled) in enumerate(entries)
            ],
        )
        conn.commit()
    finally:
        conn.close()


def clear_layout(candidate_id: int) -> None:
    """Delete the candidate's saved layout — the Home tab then falls back to
    the catalog default."""
    conn = open_db()
    try:
        conn.execute(
            "DELETE FROM dashboard_layout WHERE candidate_id=?", (candidate_id,)
        )
        conn.commit()
    finally:
        conn.close()
