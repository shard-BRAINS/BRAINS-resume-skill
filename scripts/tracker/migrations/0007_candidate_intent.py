"""Migration 0007 — career-intent columns on candidates.

Additive, schema-only. Adds an email column plus eleven nullable
career-intent columns populated by the resume-first onboarding surface
(Phase 3). Every column is nullable — an existing candidate stays valid
with all of them null.

See docs/specs/2026-05-20-dashboard-orchestration-design.md (Section 5, 7.2).
"""
import sqlite3


SCHEMA_SQL = """
ALTER TABLE candidates ADD COLUMN email TEXT;
ALTER TABLE candidates ADD COLUMN career_stage TEXT;
ALTER TABLE candidates ADD COLUMN direction TEXT;
ALTER TABLE candidates ADD COLUMN target_roles TEXT;
ALTER TABLE candidates ADD COLUMN target_industries TEXT;
ALTER TABLE candidates ADD COLUMN leadership_intent TEXT;
ALTER TABLE candidates ADD COLUMN work_preferences TEXT;
ALTER TABLE candidates ADD COLUMN location TEXT;
ALTER TABLE candidates ADD COLUMN relocation_open INTEGER;
ALTER TABLE candidates ADD COLUMN role_priorities TEXT;
ALTER TABLE candidates ADD COLUMN timeline TEXT;
ALTER TABLE candidates ADD COLUMN intent_collected_at TEXT;
"""


def apply(conn: sqlite3.Connection) -> None:
    """Add the email + career-intent columns to the candidates table."""
    conn.executescript(SCHEMA_SQL)
