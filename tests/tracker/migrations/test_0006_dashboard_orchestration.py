"""Tests for migration 0006 — dashboard_layout + playbook_runs tables."""
import pytest

from scripts.tracker.db import open_db


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_dashboard_layout_table_exists(isolated_db):
    conn = open_db()
    try:
        names = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "dashboard_layout" in names
    finally:
        conn.close()


def test_dashboard_layout_columns(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute(
            "PRAGMA table_info(dashboard_layout)")}
        assert {"id", "candidate_id", "widget_key", "position",
                "enabled", "created_at"} <= cols
    finally:
        conn.close()


def test_dashboard_layout_unique_constraint(isolated_db):
    """(candidate_id, widget_key) must be unique."""
    import sqlite3
    conn = open_db()
    try:
        conn.execute(
            "INSERT INTO candidates (first_name, last_name, created_at) "
            "VALUES ('A', 'B', '2026-01-01T00:00:00Z')")
        cid = conn.execute("SELECT id FROM candidates").fetchone()[0]
        conn.execute(
            "INSERT INTO dashboard_layout "
            "(candidate_id, widget_key, position, enabled, created_at) "
            "VALUES (?, 'worklist', 0, 1, '2026-01-01T00:00:00Z')", (cid,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO dashboard_layout "
                "(candidate_id, widget_key, position, enabled, created_at) "
                "VALUES (?, 'worklist', 1, 1, '2026-01-01T00:00:00Z')", (cid,))
    finally:
        conn.close()


def test_playbook_runs_table_exists(isolated_db):
    conn = open_db()
    try:
        names = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "playbook_runs" in names
    finally:
        conn.close()


def test_playbook_runs_columns(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute(
            "PRAGMA table_info(playbook_runs)")}
        assert {"id", "candidate_id", "playbook_key", "jd_id",
                "current_step", "status", "created_at", "updated_at",
                "completed_at"} <= cols
    finally:
        conn.close()


def test_playbook_runs_index_exists(isolated_db):
    conn = open_db()
    try:
        names = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'")}
        assert "idx_playbook_runs_candidate_status" in names
    finally:
        conn.close()


def test_migration_recorded(isolated_db):
    conn = open_db()
    try:
        versions = [row[0] for row in conn.execute(
            "SELECT version FROM migrations ORDER BY version")]
        assert 6 in versions
    finally:
        conn.close()
