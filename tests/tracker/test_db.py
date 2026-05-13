"""Tests for the tracker db connection + migration runner."""
import sqlite3
from pathlib import Path

import pytest

from scripts.tracker.db import open_db, get_db_path


def test_get_db_path_default_is_user_home(monkeypatch):
    """Without an override, the db path lives at ~/.brains-resume/tracker.db."""
    monkeypatch.delenv("BRAINS_TRACKER_DB_PATH", raising=False)
    path = get_db_path()
    assert path == Path.home() / ".brains-resume" / "tracker.db"


def test_get_db_path_honours_env_override(monkeypatch, tmp_path):
    override = tmp_path / "custom.db"
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(override))
    assert get_db_path() == override


def test_open_db_creates_file_in_user_chosen_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "subdir" / "test.db"))
    conn = open_db()
    try:
        assert (tmp_path / "subdir" / "test.db").exists()
    finally:
        conn.close()


def test_open_db_runs_migrations_on_first_open(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    conn = open_db()
    try:
        # migrations table must exist after first open
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'"
        )
        assert cur.fetchone() is not None
        # 0001 migration must be recorded
        cur = conn.execute("SELECT version FROM migrations ORDER BY version")
        versions = [row[0] for row in cur.fetchall()]
        assert 1 in versions
    finally:
        conn.close()


def test_open_db_does_not_rerun_applied_migrations(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    conn1 = open_db()
    cur = conn1.execute("SELECT COUNT(*) FROM migrations")
    first_count = cur.fetchone()[0]
    conn1.close()

    conn2 = open_db()
    cur = conn2.execute("SELECT COUNT(*) FROM migrations")
    second_count = cur.fetchone()[0]
    conn2.close()

    assert first_count == second_count


def test_open_db_returns_sqlite_connection(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    conn = open_db()
    try:
        assert isinstance(conn, sqlite3.Connection)
    finally:
        conn.close()


def test_open_db_enables_foreign_keys(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    conn = open_db()
    try:
        cur = conn.execute("PRAGMA foreign_keys")
        assert cur.fetchone()[0] == 1
    finally:
        conn.close()
