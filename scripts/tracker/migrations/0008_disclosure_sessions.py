"""Migration 0008 — disclosure_sessions table.

Adds a new table that records the outcome of a disclosure-coaching session:
the six framework-factor answers, a landed disclosure strength (non-disclosure
/ neutral / explicit / undecided), optional target employer/role, optional
free-text notes, and an optional artifact_uid linking to a generated worksheet.

See docs/plans/2026-06-08-disclosure-framework-polish.md (Phase 1).
"""
import sqlite3


SCHEMA_SQL = """
CREATE TABLE disclosure_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    created_at TEXT NOT NULL,
    target_employer TEXT,
    target_role TEXT,
    factor_1 TEXT,
    factor_2 TEXT,
    factor_3 TEXT,
    factor_4 TEXT,
    factor_5 TEXT,
    factor_6 TEXT,
    landed_strength TEXT NOT NULL,
    notes TEXT,
    artifact_uid TEXT,
    archived_at TEXT
);

CREATE INDEX idx_disclosure_sessions_candidate_id
    ON disclosure_sessions(candidate_id);

CREATE UNIQUE INDEX ux_disclosure_sessions_artifact_uid
    ON disclosure_sessions(artifact_uid) WHERE artifact_uid IS NOT NULL;
"""


def apply(conn: sqlite3.Connection) -> None:
    """Create the disclosure_sessions table + supporting indexes."""
    conn.executescript(SCHEMA_SQL)
