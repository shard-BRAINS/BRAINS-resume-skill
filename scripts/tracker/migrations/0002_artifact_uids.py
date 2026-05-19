"""Migration 0002 — artifact_uid + parent_uid + folder_path.

Forward-only addition of three new columns:

- resume_versions.artifact_uid  TEXT (UNIQUE where not null)
- resume_versions.parent_uid    TEXT (nullable)
- cover_letters.artifact_uid    TEXT (UNIQUE where not null)
- cover_letters.parent_uid      TEXT (nullable)
- jds.folder_path               TEXT (nullable)

Partial unique indexes (WHERE artifact_uid IS NOT NULL) let pre-v1.5.0
rows keep NULL without colliding with each other while preventing
duplicate non-null UIDs going forward.
"""
import sqlite3


SCHEMA_SQL = """
ALTER TABLE resume_versions ADD COLUMN artifact_uid TEXT;
ALTER TABLE resume_versions ADD COLUMN parent_uid TEXT;
ALTER TABLE cover_letters ADD COLUMN artifact_uid TEXT;
ALTER TABLE cover_letters ADD COLUMN parent_uid TEXT;
ALTER TABLE jds ADD COLUMN folder_path TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS ux_resume_versions_artifact_uid
    ON resume_versions(artifact_uid) WHERE artifact_uid IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_cover_letters_artifact_uid
    ON cover_letters(artifact_uid) WHERE artifact_uid IS NOT NULL;
"""


def apply(conn: sqlite3.Connection) -> None:
    """Apply the artifact-uid schema additions."""
    conn.executescript(SCHEMA_SQL)
