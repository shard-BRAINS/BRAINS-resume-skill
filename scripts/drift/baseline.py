"""Baseline promotion API.

promote_baseline(artifact_uid, reason) flips is_baseline in one transaction,
appends an audit row to baseline_history, and recomputes vs_baseline_score for
every non-archived resume in the candidate's scope.
"""
from __future__ import annotations

import json
from datetime import datetime

from scripts.drift.compute import compute_drift_score
from scripts.drift.lineage import _load_snapshot_facts
from scripts.tracker.db import open_db


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def promote_baseline(artifact_uid: str, reason: str) -> None:
    """Set the given artifact as the active baseline for its candidate scope.

    Single transaction:
      1. Resolve candidate scope (candidate_id) from the artifact_uid.
      2. UPDATE: clear is_baseline on any existing active baseline in scope.
      3. UPDATE: set is_baseline=1 on this artifact.
      4. INSERT into baseline_history (for_candidate, candidate_id, artifact_uid,
         promoted_at, reason). for_candidate is retained as a denormalized cache.
      5. Recompute vs_baseline_score for every non-archived row in scope:
         - The new baseline gets vs_baseline_score = NULL.
         - Every other row gets a fresh compute against the new baseline's snapshot.

    vs_parent_score is preserved (parent relationships don't shift on promotion).
    """
    conn = open_db()
    try:
        scope_row = conn.execute(
            "SELECT candidate_id, for_candidate FROM resume_versions "
            "WHERE artifact_uid=?",
            (artifact_uid,),
        ).fetchone()
        if scope_row is None:
            raise ValueError(f"No resume_versions row for artifact_uid={artifact_uid!r}")
        candidate_id = scope_row[0]
        for_candidate = scope_row[1]

        # Step 2: clear existing active baseline(s) in scope.
        conn.execute(
            "UPDATE resume_versions SET is_baseline=0 "
            "WHERE is_baseline=1 AND archived_at IS NULL "
            "  AND candidate_id = ?",
            (candidate_id,),
        )
        # Step 3: set is_baseline on target.
        conn.execute(
            "UPDATE resume_versions SET is_baseline=1 WHERE artifact_uid=?",
            (artifact_uid,),
        )
        # Step 4: audit row. for_candidate kept as a denormalized cache.
        conn.execute(
            "INSERT INTO baseline_history "
            "(for_candidate, candidate_id, artifact_uid, promoted_at, reason) "
            "VALUES (?, ?, ?, ?, ?)",
            (for_candidate, candidate_id, artifact_uid, _now_iso(), reason),
        )

        # Step 5: recompute vs_baseline_score for every non-archived row in scope.
        new_baseline_facts = _load_snapshot_facts(conn, artifact_uid)
        rows = conn.execute(
            "SELECT artifact_uid FROM resume_versions "
            "WHERE archived_at IS NULL "
            "  AND candidate_id = ?",
            (candidate_id,),
        ).fetchall()
        now = _now_iso()
        for (uid,) in rows:
            facts = _load_snapshot_facts(conn, uid)
            if facts is None:
                continue
            # vs_parent_score is unaffected by baseline promotion — preserve it.
            prev = conn.execute(
                "SELECT vs_parent_score FROM resume_drift_scores WHERE artifact_uid=?",
                (uid,),
            ).fetchone()
            vs_parent = prev[0] if prev else None
            if uid == artifact_uid:
                vs_baseline = None
            elif new_baseline_facts is not None:
                vs_baseline = json.dumps(
                    compute_drift_score(new_baseline_facts, facts)
                )
            else:
                vs_baseline = None
            conn.execute(
                "INSERT OR REPLACE INTO resume_drift_scores "
                "(artifact_uid, vs_parent_score, vs_baseline_score, computed_at) "
                "VALUES (?, ?, ?, ?)",
                (uid, vs_parent, vs_baseline, now),
            )
        conn.commit()
    finally:
        conn.close()
