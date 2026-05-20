"""Migration 0004 — resume drift analytics schema.

Adds three tables and one column:
- resume_fact_snapshots: structured fact JSON per artifact_uid
- resume_drift_scores: vs_parent + vs_baseline JSON per artifact_uid
- baseline_history: audit log of baseline promotions
- resume_versions.is_baseline: which row is the active baseline per candidate

A partial unique index enforces "exactly one active baseline per candidate".
A backfill step sets is_baseline=1 on the oldest non-archived row per
for_candidate scope (including the implicit NULL scope = profile holder).

See docs/specs/2026-05-19-resume-drift-analytics-design.md.
"""
import sqlite3


SCHEMA_SQL = """
CREATE TABLE resume_fact_snapshots (
    artifact_uid    TEXT PRIMARY KEY,
    facts           TEXT NOT NULL,
    schema_version  INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL
);

CREATE TABLE resume_drift_scores (
    artifact_uid       TEXT PRIMARY KEY,
    vs_parent_score    TEXT,
    vs_baseline_score  TEXT,
    computed_at        TEXT NOT NULL
);

CREATE TABLE baseline_history (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    for_candidate  TEXT,
    artifact_uid   TEXT NOT NULL,
    promoted_at    TEXT NOT NULL,
    reason         TEXT
);

ALTER TABLE resume_versions ADD COLUMN is_baseline INTEGER NOT NULL DEFAULT 0;

CREATE UNIQUE INDEX ux_resume_versions_baseline_per_candidate
  ON resume_versions(COALESCE(for_candidate, ''))
  WHERE is_baseline = 1 AND archived_at IS NULL;
"""


def backfill_baselines(conn: sqlite3.Connection) -> None:
    """Set is_baseline=1 on the oldest non-archived row per for_candidate
    scope. Idempotent — re-runs are no-ops because the partial unique index
    blocks the second baseline insert per scope."""
    # Identify the oldest non-archived row per distinct for_candidate scope
    # (NULL counts as its own scope).
    rows = conn.execute(
        """
        SELECT id FROM resume_versions rv
        WHERE archived_at IS NULL
          AND created_at = (
              SELECT MIN(created_at) FROM resume_versions rv2
              WHERE rv2.archived_at IS NULL
                AND ((rv2.for_candidate IS NULL AND rv.for_candidate IS NULL)
                     OR rv2.for_candidate = rv.for_candidate)
          )
        """
    ).fetchall()
    target_ids = {r[0] for r in rows}
    for rid in target_ids:
        try:
            conn.execute(
                "UPDATE resume_versions SET is_baseline=1 WHERE id=?",
                (rid,),
            )
        except sqlite3.IntegrityError:
            # Already a baseline in this scope (idempotent re-run).
            pass
    conn.commit()


def apply(conn: sqlite3.Connection) -> None:
    """Apply schema then run the backfill."""
    conn.executescript(SCHEMA_SQL)
    backfill_baselines(conn)
