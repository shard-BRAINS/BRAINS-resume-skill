"""Migration 0005 — candidates table + candidate_id FK columns.

Schema-only. Backfill is performed by scripts.tracker._post_migration.run_b_backfill,
which db.py invokes after migrations apply.

This migration is drift-aware: v1.7.0 (migration 0004) added the
`baseline_history` table and the partial unique index
`ux_resume_versions_baseline_per_candidate` scoped on `COALESCE(for_candidate, '')`.
This migration adds `candidate_id` to `baseline_history` and rebuilds that index
on `candidate_id` so the single-baseline-per-candidate invariant tracks the new
scoping key.

See docs/plans/2026-05-19-multi-candidate-approach-b.md.
"""
import sqlite3


SCHEMA_SQL = """
CREATE TABLE candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    focus_areas TEXT NOT NULL DEFAULT '[]',
    healthy_weekly_rate INTEGER,
    pacing_notes TEXT,
    created_at TEXT NOT NULL,
    archived_at TEXT
);

ALTER TABLE jds              ADD COLUMN candidate_id INTEGER REFERENCES candidates(id);
ALTER TABLE resume_versions  ADD COLUMN candidate_id INTEGER REFERENCES candidates(id);
ALTER TABLE cover_letters    ADD COLUMN candidate_id INTEGER REFERENCES candidates(id);
ALTER TABLE baseline_history ADD COLUMN candidate_id INTEGER REFERENCES candidates(id);

CREATE INDEX idx_jds_candidate_id              ON jds(candidate_id);
CREATE INDEX idx_resume_versions_candidate_id  ON resume_versions(candidate_id);
CREATE INDEX idx_cover_letters_candidate_id    ON cover_letters(candidate_id);
CREATE INDEX idx_baseline_history_candidate_id ON baseline_history(candidate_id);

DROP INDEX ux_resume_versions_baseline_per_candidate;
CREATE UNIQUE INDEX ux_resume_versions_baseline_per_candidate
  ON resume_versions(candidate_id)
  WHERE is_baseline = 1 AND archived_at IS NULL;
"""


def apply(conn: sqlite3.Connection) -> None:
    """Apply the candidates schema. Backfill runs separately.

    Note: immediately after this migration every resume_versions.candidate_id
    is NULL, so the rebuilt partial unique index enforces nothing yet (SQLite
    treats each NULL as distinct). The post-migration backfill (Task 5)
    populates candidate_id; if the backfill ever tried to set two is_baseline=1
    rows for one candidate the index would reject it — a useful safety net.
    """
    conn.executescript(SCHEMA_SQL)
