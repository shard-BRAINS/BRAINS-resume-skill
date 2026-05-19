"""Tests for migration 0002_artifact_uids."""
import sqlite3

import pytest

from scripts.tracker.db import open_db


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path / "test.db"


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def test_0002_adds_artifact_uid_to_resume_versions(fresh_db):
    conn = open_db()
    try:
        assert "artifact_uid" in _columns(conn, "resume_versions")
        assert "parent_uid" in _columns(conn, "resume_versions")
    finally:
        conn.close()


def test_0002_adds_artifact_uid_to_cover_letters(fresh_db):
    conn = open_db()
    try:
        assert "artifact_uid" in _columns(conn, "cover_letters")
        assert "parent_uid" in _columns(conn, "cover_letters")
    finally:
        conn.close()


def test_0002_adds_folder_path_to_jds(fresh_db):
    conn = open_db()
    try:
        assert "folder_path" in _columns(conn, "jds")
    finally:
        conn.close()


def test_0002_unique_index_on_resume_artifact_uid_allows_nulls(fresh_db):
    """The partial unique index must allow multiple NULL artifact_uids
    (pre-v1.5.0 rows) without raising."""
    conn = open_db()
    try:
        # Insert two resume rows with NULL artifact_uid — must not collide.
        for _ in range(2):
            conn.execute(
                """INSERT INTO resume_versions
                   (file_path, template, focus_areas, created_at, artifact_uid)
                   VALUES (?, ?, ?, ?, ?)""",
                ("/tmp/r.docx", "hybrid", "[]", "2026-05-18T00:00:00Z", None),
            )
        conn.commit()
        count = conn.execute(
            "SELECT COUNT(*) FROM resume_versions WHERE artifact_uid IS NULL"
        ).fetchone()[0]
        assert count == 2
    finally:
        conn.close()


def test_0002_unique_index_rejects_duplicate_non_null(fresh_db):
    conn = open_db()
    try:
        conn.execute(
            """INSERT INTO resume_versions
               (file_path, template, focus_areas, created_at, artifact_uid)
               VALUES (?, ?, ?, ?, ?)""",
            ("/tmp/a.docx", "hybrid", "[]", "2026-05-18T00:00:00Z", "KX7M9Q"),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO resume_versions
                   (file_path, template, focus_areas, created_at, artifact_uid)
                   VALUES (?, ?, ?, ?, ?)""",
                ("/tmp/b.docx", "hybrid", "[]", "2026-05-18T00:00:00Z", "KX7M9Q"),
            )
            conn.commit()
    finally:
        conn.close()


def test_0002_idempotent_on_reopen(fresh_db):
    open_db().close()
    # Reopening must not error from "column already exists".
    conn = open_db()
    try:
        applied = conn.execute(
            "SELECT version FROM migrations WHERE version = 2"
        ).fetchone()
        assert applied is not None
    finally:
        conn.close()
