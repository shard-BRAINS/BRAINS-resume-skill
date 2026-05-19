"""Migration 0003 — for_candidate text column on resume_versions and cover_letters.

Forward-only addition of two nullable text columns that record who the artifact
is FOR when that person is not the profile holder. Null preserves pre-0003
behaviour (artifact belongs to the profile holder).

See docs/plans/2026-05-19-multi-candidate-approach-c.md.
"""
import sqlite3


SCHEMA_SQL = """
ALTER TABLE resume_versions ADD COLUMN for_candidate TEXT;
ALTER TABLE cover_letters   ADD COLUMN for_candidate TEXT;
"""


def apply(conn: sqlite3.Connection) -> None:
    """Apply the for_candidate column additions."""
    conn.executescript(SCHEMA_SQL)
