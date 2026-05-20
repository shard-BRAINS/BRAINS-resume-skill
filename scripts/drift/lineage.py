"""Lineage walkers: parent (skipping archived), baseline, full candidate lineage.

All walkers cap at depth 100 (cycle defence) and skip archived rows.
"""
from __future__ import annotations

import json
from typing import Optional

from scripts.tracker.db import open_db


_DEPTH_CAP = 100


def _load_snapshot_facts(conn, artifact_uid: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT facts FROM resume_fact_snapshots WHERE artifact_uid=?",
        (artifact_uid,),
    ).fetchone()
    if row is None:
        return None
    try:
        return json.loads(row[0])
    except (json.JSONDecodeError, TypeError):
        return None


def _resolve_candidate_scope(conn, artifact_uid: str) -> dict:
    row = conn.execute(
        "SELECT for_candidate FROM resume_versions WHERE artifact_uid=?",
        (artifact_uid,),
    ).fetchone()
    if row is None:
        return {"for_candidate": None}
    return {"for_candidate": row[0]}


def get_parent_snapshot(artifact_uid: str) -> Optional[dict]:
    """Walk parent_uid chain, skipping archived rows, until a row with a
    fact snapshot is found. Returns None if none found within 100 hops.
    """
    conn = open_db()
    try:
        seen: set = set()
        current = artifact_uid
        for _ in range(_DEPTH_CAP):
            row = conn.execute(
                "SELECT parent_uid FROM resume_versions WHERE artifact_uid=?",
                (current,),
            ).fetchone()
            if row is None or row[0] is None:
                return None
            parent_uid = row[0]
            if parent_uid in seen:
                return None  # cycle detected
            seen.add(parent_uid)
            archived = conn.execute(
                "SELECT archived_at FROM resume_versions WHERE artifact_uid=?",
                (parent_uid,),
            ).fetchone()
            if archived is not None and archived[0] is not None:
                # Skip archived row; continue up.
                current = parent_uid
                continue
            facts = _load_snapshot_facts(conn, parent_uid)
            if facts is not None:
                return facts
            current = parent_uid
        return None
    finally:
        conn.close()


def get_baseline_snapshot(artifact_uid: str) -> Optional[dict]:
    """Find the active baseline row for this artifact's candidate scope and
    return its fact snapshot. Returns None if no active baseline or no snapshot.
    """
    conn = open_db()
    try:
        scope = _resolve_candidate_scope(conn, artifact_uid)
        for_candidate = scope["for_candidate"]
        row = conn.execute(
            """SELECT artifact_uid FROM resume_versions
               WHERE is_baseline = 1 AND archived_at IS NULL
                 AND ((? IS NULL AND for_candidate IS NULL) OR for_candidate = ?)
               LIMIT 1""",
            (for_candidate, for_candidate),
        ).fetchone()
        if row is None:
            return None
        return _load_snapshot_facts(conn, row[0])
    finally:
        conn.close()


def get_candidate_lineage(scope: dict) -> list:
    """Return all non-archived resume_versions rows for the given for_candidate
    scope, sorted by created_at ascending."""
    from scripts.tracker.models import ResumeVersion
    conn = open_db()
    try:
        for_candidate = scope.get("for_candidate")
        rows = conn.execute(
            """SELECT id, file_path, template, focus_areas, parent_id,
                      tagged_jd_id, created_at, archived_at, artifact_uid,
                      parent_uid, for_candidate
               FROM resume_versions
               WHERE archived_at IS NULL
                 AND ((? IS NULL AND for_candidate IS NULL) OR for_candidate = ?)
               ORDER BY created_at ASC""",
            (for_candidate, for_candidate),
        ).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        out.append(ResumeVersion(
            id=r[0], file_path=r[1], template=r[2],
            focus_areas=json.loads(r[3] or "[]"),
            parent_id=r[4], tagged_jd_id=r[5],
            created_at=r[6], archived_at=r[7],
            artifact_uid=r[8], parent_uid=r[9], for_candidate=r[10],
        ))
    return out
