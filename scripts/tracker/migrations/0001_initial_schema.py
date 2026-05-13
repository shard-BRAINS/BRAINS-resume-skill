"""Migration 0001 — initial schema.

Creates the five entity tables: resume_versions, cover_letters, jds,
applications, outcomes. All tables have id (autoincrement PK), created_at
(ISO-8601 UTC timestamp), and archived_at (NULL = active, non-NULL = soft-
deleted) columns.

Foreign keys are enforced at runtime via PRAGMA foreign_keys = ON, set by
scripts/tracker/db.py:open_db().
"""
import sqlite3


SCHEMA_SQL = """
CREATE TABLE resume_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT,
    template TEXT NOT NULL,
    focus_areas TEXT NOT NULL,
    parent_id INTEGER,
    tagged_jd_id INTEGER,
    created_at TEXT NOT NULL,
    archived_at TEXT,
    FOREIGN KEY (parent_id) REFERENCES resume_versions(id),
    FOREIGN KEY (tagged_jd_id) REFERENCES jds(id)
);

CREATE TABLE jds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_ref TEXT,
    company TEXT NOT NULL,
    role_title TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    analyzer_findings TEXT NOT NULL,
    focus_areas_required TEXT NOT NULL,
    focus_areas_nice TEXT NOT NULL,
    created_at TEXT NOT NULL,
    archived_at TEXT
);

CREATE TABLE cover_letters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT,
    resume_version_id INTEGER NOT NULL,
    jd_id INTEGER NOT NULL,
    template TEXT NOT NULL,
    created_at TEXT NOT NULL,
    archived_at TEXT,
    FOREIGN KEY (resume_version_id) REFERENCES resume_versions(id),
    FOREIGN KEY (jd_id) REFERENCES jds(id)
);

CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jd_id INTEGER NOT NULL,
    resume_version_id INTEGER NOT NULL,
    cover_letter_id INTEGER,
    submitted_at TEXT NOT NULL,
    channel TEXT NOT NULL,
    agency_name TEXT,
    recruiter_contact TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    archived_at TEXT,
    FOREIGN KEY (jd_id) REFERENCES jds(id),
    FOREIGN KEY (resume_version_id) REFERENCES resume_versions(id),
    FOREIGN KEY (cover_letter_id) REFERENCES cover_letters(id)
);

CREATE TABLE outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    event_date TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    archived_at TEXT,
    FOREIGN KEY (application_id) REFERENCES applications(id)
);

CREATE INDEX idx_applications_jd_id ON applications(jd_id);
CREATE INDEX idx_outcomes_application_id ON outcomes(application_id);
CREATE INDEX idx_jds_company ON jds(company);
"""


def apply(conn: sqlite3.Connection) -> None:
    """Apply the initial schema. Called by db.py's migration runner."""
    conn.executescript(SCHEMA_SQL)
