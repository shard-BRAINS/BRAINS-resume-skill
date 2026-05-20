"""Tests for migration 0005 — candidates table + candidate_id columns."""
import pytest

from scripts.tracker.db import open_db


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_candidates_table_exists(isolated_db):
    conn = open_db()
    try:
        names = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "candidates" in names
    finally:
        conn.close()


def test_candidates_columns(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(candidates)")}
        assert {"id", "first_name", "last_name", "focus_areas",
                "healthy_weekly_rate", "pacing_notes",
                "created_at", "archived_at"} <= cols
    finally:
        conn.close()


def test_jds_has_candidate_id(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(jds)")}
        assert "candidate_id" in cols
    finally:
        conn.close()


def test_resume_versions_has_candidate_id(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(resume_versions)")}
        assert "candidate_id" in cols
    finally:
        conn.close()


def test_cover_letters_has_candidate_id(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(cover_letters)")}
        assert "candidate_id" in cols
    finally:
        conn.close()


def test_baseline_history_has_candidate_id(isolated_db):
    """v1.7.0's baseline_history table gets candidate_id too."""
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(baseline_history)")}
        assert "candidate_id" in cols
    finally:
        conn.close()


def test_baseline_index_rebuilt_on_candidate_id(isolated_db):
    """The is_baseline partial unique index is now scoped on candidate_id."""
    conn = open_db()
    try:
        sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' "
            "AND name='ux_resume_versions_baseline_per_candidate'"
        ).fetchone()
        assert sql is not None
        assert "candidate_id" in sql[0]
        assert "for_candidate" not in sql[0]
    finally:
        conn.close()


def test_migration_recorded(isolated_db):
    conn = open_db()
    try:
        versions = [row[0] for row in conn.execute(
            "SELECT version FROM migrations ORDER BY version")]
        assert 5 in versions
    finally:
        conn.close()
