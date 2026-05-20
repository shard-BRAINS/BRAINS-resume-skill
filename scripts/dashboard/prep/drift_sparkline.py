"""Drift trajectory data prep for the Overview tile.

Pure function — returns a chart-ready list of {artifact_uid, created_at,
overall_pct} ordered oldest first. Streamlit/visualisation code reads it
directly without further transformation.
"""
from __future__ import annotations

import json

from scripts.drift.lineage import get_candidate_lineage
from scripts.tracker.db import open_db


def drift_trajectory_last_n(scope: dict, n: int = 12) -> list[dict]:
    """Return the last N non-archived resumes in the scope, with overall_pct."""
    lineage = get_candidate_lineage(scope)
    if not lineage:
        return []
    # Take the last n; sort oldest-first within that window.
    window = lineage[-n:]
    uids = [v.artifact_uid for v in window]
    placeholders = ",".join("?" * len(uids))
    conn = open_db()
    try:
        rows = conn.execute(
            f"SELECT artifact_uid, vs_baseline_score "
            f"FROM resume_drift_scores WHERE artifact_uid IN ({placeholders})",
            uids,
        ).fetchall()
    finally:
        conn.close()
    score_by_uid: dict = {}
    for uid, vs_baseline in rows:
        if vs_baseline is None:
            score_by_uid[uid] = None
        else:
            try:
                score_by_uid[uid] = json.loads(vs_baseline).get("overall_pct")
            except json.JSONDecodeError:
                score_by_uid[uid] = None
    return [
        {
            "artifact_uid": v.artifact_uid,
            "created_at": v.created_at,
            "overall_pct": score_by_uid.get(v.artifact_uid),
        }
        for v in window
    ]
