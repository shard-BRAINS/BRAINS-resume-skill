"""Migration 0006 — dashboard orchestration tables.

Schema-only, additive, no backfill. Creates two tables:

- dashboard_layout: per-candidate widget canvas (which widgets, in what
  order, enabled or not). Consumed by Phase 2 (the widget canvas).
- playbook_runs: one row per playbook run; tracks current_step and status.

See docs/specs/2026-05-20-dashboard-orchestration-design.md (Section 7.1).
"""
import sqlite3


SCHEMA_SQL = """
CREATE TABLE dashboard_layout (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    widget_key TEXT NOT NULL,
    position INTEGER NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE(candidate_id, widget_key)
);

CREATE TABLE playbook_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    playbook_key TEXT NOT NULL,
    jd_id INTEGER REFERENCES jds(id),
    current_step INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX idx_playbook_runs_candidate_status
  ON playbook_runs(candidate_id, status);
"""


def apply(conn: sqlite3.Connection) -> None:
    """Create the dashboard_layout and playbook_runs tables."""
    conn.executescript(SCHEMA_SQL)
