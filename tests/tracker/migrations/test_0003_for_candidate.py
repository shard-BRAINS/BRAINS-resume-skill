"""Tests for migration 0003 — for_candidate columns."""
import sqlite3

import pytest

from scripts.tracker.db import open_db


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


def test_resume_versions_has_for_candidate_column(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(resume_versions)")}
        assert "for_candidate" in cols
    finally:
        conn.close()


def test_cover_letters_has_for_candidate_column(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(cover_letters)")}
        assert "for_candidate" in cols
    finally:
        conn.close()


def test_for_candidate_is_nullable(isolated_db):
    """A pre-existing-style insert without for_candidate must still succeed."""
    conn = open_db()
    try:
        conn.execute(
            """INSERT INTO resume_versions
                 (template, focus_areas, created_at)
               VALUES ('chronological', '[]', '2026-05-19T00:00:00Z')"""
        )
        conn.commit()
        row = conn.execute(
            "SELECT for_candidate FROM resume_versions"
        ).fetchone()
        assert row[0] is None
    finally:
        conn.close()


def test_migration_recorded_in_migrations_table(isolated_db):
    conn = open_db()
    try:
        versions = [row[0] for row in conn.execute("SELECT version FROM migrations ORDER BY version")]
        assert 3 in versions
    finally:
        conn.close()
