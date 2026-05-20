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

    Reconciliation order matters. The partial unique index
    `ux_resume_versions_baseline_per_candidate` forbids two is_baseline=1
    (non-archived) rows from sharing a candidate_id. Migration 0004's per-scope
    drift backfill can leave several is_baseline=1 rows that all resolve to ONE
    candidate (e.g. the profile holder's name also used as a for_candidate
    value). To avoid an IntegrityError mid-UPDATE, we:

      1. Compute the {row_id: target_candidate_id} mapping for every
         candidate_id IS NULL row across all four tables WITHOUT issuing any
         UPDATE.
      2. Demote extra resume_versions baselines so each target candidate ends
         up with at most one is_baseline=1 row.
      3. Only then issue the candidate_id UPDATEs.

    The whole body runs inside a single transaction: a partial failure rolls
    back so the DB is left at its pre-hook state, never half-migrated.
    """
    # 1. Confirm schema is at v5+ (else: nothing to backfill).
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if "candidates" not in tables:
        return

    profile_path = get_profile_path()

    try:
        seed_id = _ensure_seed_candidate(conn, profile_path)

        # 2. Compute the candidate_id mapping for every unlinked row WITHOUT
        #    touching the DB yet. mapping[table] = {row_id: target_candidate_id}.
        mapping = {}
        for table in ("resume_versions", "cover_letters", "jds",
                      "baseline_history"):
            mapping[table] = _compute_candidate_mapping(conn, table, seed_id)

        # 3. Reconcile the single-baseline-per-candidate invariant for
        #    resume_versions BEFORE assigning candidate_id. is_baseline only
        #    exists on resume_versions; the other three tables cannot collide
        #    on the partial unique index, so their UPDATEs are unconstrained.
        _demote_extra_baselines_for_mapping(conn, mapping["resume_versions"])

        # 4. Issue the candidate_id UPDATEs. With at most one is_baseline=1 row
        #    per target candidate, these cannot violate the partial unique
        #    index.
        for table, row_to_cid in mapping.items():
            for row_id, cid in row_to_cid.items():
                conn.execute(
                    f"UPDATE {table} SET candidate_id=? WHERE id=?",
                    (cid, row_id),
                )

        conn.commit()
    except Exception:
        # A partial failure must not wedge the DB. Roll back to pre-hook state.
        conn.rollback()
        raise


def _compute_candidate_mapping(conn: sqlite3.Connection, table: str,
                               seed_id) -> dict:
    """Return {row_id: target_candidate_id} for every candidate_id IS NULL row
    in ``table``, WITHOUT issuing any UPDATE.

    Rows with a for_candidate value resolve to a per-name candidate (created if
    needed). Rows without one fall back to the seed candidate. ``jds`` has no
    for_candidate column, so all of its unlinked rows go to the seed.

    Returns an empty dict when there is nothing to link (idempotent no-op) or
    when there is no seed and no for_candidate value to resolve against.
    """
    has_for_candidate = table != "jds"
    if has_for_candidate:
        rows = conn.execute(
            f"SELECT id, for_candidate FROM {table} WHERE candidate_id IS NULL"
        ).fetchall()
    else:
        rows = [(r[0], None) for r in conn.execute(
            f"SELECT id FROM {table} WHERE candidate_id IS NULL").fetchall()]

    result = {}
    for row_id, name in rows:
        if name:
            result[row_id] = _find_or_create_candidate_by_name(conn, name)
        elif seed_id is not None:
            result[row_id] = seed_id
        # else: no for_candidate and no seed — leave the row unlinked.
    return result


def _demote_extra_baselines_for_mapping(conn: sqlite3.Connection,
                                        rv_mapping: dict) -> None:
    """Ensure each target candidate ends up with at most one is_baseline=1
    (non-archived) resume_versions row after ``rv_mapping`` is applied.

    For every target candidate that would receive one or more is_baseline=1
    rows, count the is_baseline=1 non-archived rows ALREADY linked to that
    candidate plus the incoming ones. If the combined total exceeds one, keep
    the oldest row (ORDER BY created_at, id) at is_baseline=1 and demote the
    rest to is_baseline=0.

    Considering rows already at the target candidate matters: the seed
    candidate may already own a baseline, and the merge could bring another.

    baseline_history is the audit trail and is left untouched by this demote.
    """
    # Group incoming row ids by the candidate they will be assigned to.
    incoming_by_cid = {}
    for row_id, cid in rv_mapping.items():
        incoming_by_cid.setdefault(cid, []).append(row_id)

    for cid, incoming_ids in incoming_by_cid.items():
        # is_baseline=1 non-archived rows ALREADY linked to this candidate.
        existing = conn.execute(
            """SELECT id, created_at FROM resume_versions
               WHERE candidate_id = ? AND is_baseline = 1
                 AND archived_at IS NULL""",
            (cid,),
        ).fetchall()
        # is_baseline=1 non-archived rows among the incoming (still NULL) rows.
        placeholders = ",".join("?" * len(incoming_ids))
        incoming = conn.execute(
            f"""SELECT id, created_at FROM resume_versions
                WHERE id IN ({placeholders})
                  AND is_baseline = 1 AND archived_at IS NULL""",
            incoming_ids,
        ).fetchall()

        baseline_rows = list(existing) + list(incoming)
        if len(baseline_rows) <= 1:
            continue
        # Keep the oldest across BOTH sets; demote every other baseline row.
        baseline_rows.sort(key=lambda r: (r[1], r[0]))
        for row_id, _created_at in baseline_rows[1:]:
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
