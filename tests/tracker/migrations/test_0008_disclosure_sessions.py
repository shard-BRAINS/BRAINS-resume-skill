"""Tests for migration 0008 — disclosure_sessions table."""
import sqlite3

import pytest

from scripts.tracker.db import open_db


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def _seed_candidate(conn) -> int:
    cur = conn.execute(
        "INSERT INTO candidates (first_name, last_name, created_at) "
        "VALUES ('A', 'B', '2026-01-01T00:00:00Z')"
    )
    return cur.lastrowid


def test_disclosure_sessions_table_exists(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(disclosure_sessions)")}
        assert cols == {
            "id", "candidate_id", "created_at",
            "target_employer", "target_role",
            "factor_1", "factor_2", "factor_3",
            "factor_4", "factor_5", "factor_6",
            "landed_strength", "notes", "artifact_uid", "archived_at",
        }
    finally:
        conn.close()


def test_fk_to_candidates(isolated_db):
    conn = open_db()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO disclosure_sessions "
                "(candidate_id, created_at, landed_strength) "
                "VALUES (?, ?, ?)",
                (9999, "2026-06-08T00:00:00Z", "non-disclosure"),
            )
    finally:
        conn.close()


def test_landed_strength_required(isolated_db):
    conn = open_db()
    try:
        cid = _seed_candidate(conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO disclosure_sessions (candidate_id, created_at) "
                "VALUES (?, ?)",
                (cid, "2026-06-08T00:00:00Z"),
            )
    finally:
        conn.close()


def test_artifact_uid_unique_when_set(isolated_db):
    conn = open_db()
    try:
        cid = _seed_candidate(conn)
        conn.execute(
            "INSERT INTO disclosure_sessions "
            "(candidate_id, created_at, landed_strength, artifact_uid) "
            "VALUES (?, ?, ?, ?)",
            (cid, "2026-06-08T00:00:00Z", "neutral", "ds-abc123"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO disclosure_sessions "
                "(candidate_id, created_at, landed_strength, artifact_uid) "
                "VALUES (?, ?, ?, ?)",
                (cid, "2026-06-08T00:00:01Z", "neutral", "ds-abc123"),
            )
    finally:
        conn.close()


def test_multiple_null_artifact_uids_allowed(isolated_db):
    """Partial unique index permits many NULL artifact_uids."""
    conn = open_db()
    try:
        cid = _seed_candidate(conn)
        for i in range(3):
            conn.execute(
                "INSERT INTO disclosure_sessions "
                "(candidate_id, created_at, landed_strength) "
                "VALUES (?, ?, ?)",
                (cid, f"2026-06-08T00:00:0{i}Z", "non-disclosure"),
            )
        count = conn.execute(
            "SELECT COUNT(*) FROM disclosure_sessions WHERE artifact_uid IS NULL"
        ).fetchone()[0]
        assert count == 3
    finally:
        conn.close()


def test_archived_at_defaults_null(isolated_db):
    conn = open_db()
    try:
        cid = _seed_candidate(conn)
        conn.execute(
            "INSERT INTO disclosure_sessions "
            "(candidate_id, created_at, landed_strength) "
            "VALUES (?, ?, ?)",
            (cid, "2026-06-08T00:00:00Z", "neutral"),
        )
        row = conn.execute(
            "SELECT archived_at FROM disclosure_sessions"
        ).fetchone()
        assert row[0] is None
    finally:
        conn.close()


def test_migration_recorded(isolated_db):
    conn = open_db()
    try:
        versions = [
            row[0] for row in conn.execute("SELECT version FROM migrations ORDER BY version")
        ]
        assert 8 in versions
    finally:
        conn.close()
