"""Idempotent post-migration hooks.

Called by db.py::open_db after migrations apply. Each hook checks its own
preconditions and is safe to invoke on every connection open.
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from scripts.outputs.naming import split_candidate_name
from scripts.tracker.profile import get_profile_path


def run_b_backfill(conn: sqlite3.Connection) -> None:
    """Backfill candidates + candidate_id links the first time a v5-schema DB
    opens against a pre-B profile.json.

    Idempotency contract: this function may be called repeatedly. On a fully
    backfilled DB it is a no-op. On a partially backfilled DB it picks up
    where it left off.

    Drift-aware: `baseline_history` (added by v1.7.0 migration 0004) is
    backfilled alongside `resume_versions` / `cover_letters` so the v1.7.0
    baseline-promotion audit trail is also candidate-scoped.
    """
    # 1. Confirm schema is at v5+ (else: nothing to backfill).
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if "candidates" not in tables:
        return

    profile_path = get_profile_path()
    seed_id = _ensure_seed_candidate(conn, profile_path)

    # 2. Link rows with for_candidate set to a per-name candidate row.
    #    baseline_history is included — it carries a for_candidate column too.
    for table in ("resume_versions", "cover_letters", "baseline_history"):
        for row in conn.execute(
            f"SELECT id, for_candidate FROM {table} "
            f"WHERE candidate_id IS NULL AND for_candidate IS NOT NULL"
        ).fetchall():
            artifact_id, name = row
            cid = _find_or_create_candidate_by_name(conn, name)
            conn.execute(
                f"UPDATE {table} SET candidate_id=? WHERE id=?",
                (cid, artifact_id),
            )

    # 3. Link rows with NULL candidate_id (and NULL for_candidate) to seed.
    #    jds has no for_candidate column — all its NULL-candidate_id rows go
    #    to the seed. baseline_history with a NULL for_candidate (profile-holder
    #    scope promotions) also goes to the seed.
    if seed_id is not None:
        # Guard the single-baseline-per-candidate invariant: the partial unique
        # index ux_resume_versions_baseline_per_candidate forbids two
        # is_baseline=1 rows sharing a candidate_id. Orphan rows being merged
        # into the seed may include several is_baseline=1 rows (e.g. a legacy
        # DB with one baseline per for_candidate scope). Keep the oldest such
        # row as the seed's baseline and demote the rest before reassigning.
        _demote_extra_baselines_before_merge(conn, seed_id)
        for table in ("resume_versions", "cover_letters", "jds",
                      "baseline_history"):
            conn.execute(
                f"UPDATE {table} SET candidate_id=? "
                f"WHERE candidate_id IS NULL",
                (seed_id,),
            )
    conn.commit()


def _demote_extra_baselines_before_merge(conn: sqlite3.Connection,
                                         seed_id: int) -> None:
    """Ensure at most one is_baseline=1 resume_versions row will end up on the
    seed candidate after the step-3 bulk merge.

    Considers the seed's existing baseline plus every orphan (candidate_id
    IS NULL) is_baseline=1 non-archived row. The oldest of those keeps
    is_baseline=1; all others are demoted to is_baseline=0. This preserves the
    audit trail in baseline_history while satisfying the partial unique index.
    """
    candidates_for_baseline = conn.execute(
        """SELECT id, created_at FROM resume_versions
           WHERE is_baseline = 1 AND archived_at IS NULL
             AND (candidate_id IS NULL OR candidate_id = ?)
           ORDER BY created_at, id""",
        (seed_id,),
    ).fetchall()
    # Keep the first (oldest) row's baseline flag; demote any others.
    for row_id, _created_at in candidates_for_baseline[1:]:
        conn.execute(
            "UPDATE resume_versions SET is_baseline = 0 WHERE id = ?",
            (row_id,),
        )


def _ensure_seed_candidate(conn: sqlite3.Connection, profile_path: Path):
    """Resolve the seed candidate from profile.json.

    The "seed" is the profile holder — the implicit owner of every legacy
    artifact that was created before per-candidate scoping existed. It is
    derived ONLY from profile.json, never from an arbitrary candidates row:
    a candidate created by step-2 name matching is a *different person* and
    must not absorb the profile holder's orphan artifacts.

    Returns:
      - the active_candidate_id, if profile.json is already in trimmed shape;
      - a freshly created seed id, if profile.json still has legacy fields;
      - None, if there is no profile.json / no legacy identity to seed from.
    """
    if not profile_path.exists():
        return None
    try:
        data = json.loads(profile_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None

    # Already migrated: trimmed profile points at the seed directly.
    active_id = data.get("active_candidate_id")
    if active_id is not None:
        exists = conn.execute(
            "SELECT 1 FROM candidates WHERE id = ?", (active_id,)
        ).fetchone()
        if exists is not None:
            return active_id

    first = data.get("first_name")
    last = data.get("last_name")
    if not first or not last:
        return None
    focus_areas = (data or {}).get("focus_areas") or []
    healthy_rate = (data or {}).get("healthy_weekly_rate")
    pacing_notes = (data or {}).get("pacing_notes")
    log_handoffs = (data or {}).get("log_handoffs", True)

    cur = conn.execute(
        """INSERT INTO candidates
             (first_name, last_name, focus_areas, healthy_weekly_rate,
              pacing_notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (first, last, json.dumps(focus_areas), healthy_rate, pacing_notes,
         datetime.utcnow().isoformat() + "Z"),
    )
    seed_id = cur.lastrowid

    # Rewrite profile.json to trimmed shape.
    profile_path.write_text(
        json.dumps({
            "active_candidate_id": seed_id,
            "log_handoffs": log_handoffs,
        }, indent=2),
        encoding="utf-8",
    )
    return seed_id


def _find_or_create_candidate_by_name(conn: sqlite3.Connection, name: str) -> int:
    """Find a candidate by first+last name. Create one if missing.

    Uses split_candidate_name from outputs.naming. Multi-token first-name
    matches (e.g. 'Anne Marie') are recognised because the split groups
    middle tokens with the given name.
    """
    first, last = split_candidate_name(name)
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
        (first, last, datetime.utcnow().isoformat() + "Z"),
    )
    return cur.lastrowid
