"""Tests for migration 0007 — email + career-intent columns on candidates."""
import pytest

from scripts.tracker.db import open_db


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_candidates_has_all_intent_columns(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(candidates)")}
        assert {
            "email", "career_stage", "direction", "target_roles",
            "target_industries", "leadership_intent", "work_preferences",
            "location", "relocation_open", "role_priorities", "timeline",
            "intent_collected_at",
        } <= cols
    finally:
        conn.close()


def test_existing_columns_preserved(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(candidates)")}
        assert {"id", "first_name", "last_name", "focus_areas",
                "healthy_weekly_rate", "pacing_notes",
                "created_at", "archived_at"} <= cols
    finally:
        conn.close()


def test_intent_columns_default_null(isolated_db):
    """A new candidate has every intent column null until onboarding runs."""
    conn = open_db()
    try:
        conn.execute(
            "INSERT INTO candidates (first_name, last_name, created_at) "
            "VALUES ('A', 'B', '2026-01-01T00:00:00Z')")
        row = conn.execute(
            "SELECT email, career_stage, intent_collected_at FROM candidates"
        ).fetchone()
        assert row == (None, None, None)
    finally:
        conn.close()


def test_migration_recorded(isolated_db):
    conn = open_db()
    try:
        versions = [row[0] for row in conn.execute(
            "SELECT version FROM migrations ORDER BY version")]
        assert 7 in versions
    finally:
        conn.close()
