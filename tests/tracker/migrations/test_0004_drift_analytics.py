"""Tests for migration 0004 — drift analytics schema + backfill."""
import pytest

from scripts.tracker.db import open_db


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


def test_resume_fact_snapshots_table_exists(fresh_db):
    conn = open_db()
    try:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "resume_fact_snapshots" in names
    finally:
        conn.close()


def test_resume_drift_scores_table_exists(fresh_db):
    conn = open_db()
    try:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "resume_drift_scores" in names
    finally:
        conn.close()


def test_baseline_history_table_exists(fresh_db):
    conn = open_db()
    try:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "baseline_history" in names
    finally:
        conn.close()


def test_is_baseline_column_present_and_defaults_zero(fresh_db):
    conn = open_db()
    try:
        cols = {r[1]: r for r in conn.execute("PRAGMA table_info(resume_versions)")}
        assert "is_baseline" in cols
        # cid, name, type, notnull, dflt_value, pk
        col = cols["is_baseline"]
        assert col[2] == "INTEGER"
        assert col[3] == 1  # NOT NULL
        assert col[4] == "0"  # default
    finally:
        conn.close()


def test_partial_unique_index_allows_multiple_non_baselines(fresh_db):
    """Only is_baseline=1 rows are subject to the uniqueness constraint."""
    conn = open_db()
    try:
        # Two rows for the same for_candidate, both is_baseline=0 — fine.
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate, is_baseline) "
            "VALUES ('hybrid', '[]', '2026-05-01T00:00:00Z', 'Alice Example', 0)"
        )
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate, is_baseline) "
            "VALUES ('hybrid', '[]', '2026-05-02T00:00:00Z', 'Alice Example', 0)"
        )
        conn.commit()
    finally:
        conn.close()


def test_partial_unique_index_blocks_two_active_baselines(fresh_db):
    """Two is_baseline=1 rows for the same candidate (both active) must fail."""
    import sqlite3
    conn = open_db()
    try:
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate, is_baseline) "
            "VALUES ('hybrid', '[]', '2026-05-01T00:00:00Z', 'Alice Example', 1)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate, is_baseline) "
                "VALUES ('hybrid', '[]', '2026-05-02T00:00:00Z', 'Alice Example', 1)"
            )
            conn.commit()
    finally:
        conn.close()


def test_partial_unique_index_blocks_two_active_baselines_null_scope(fresh_db):
    """Two is_baseline=1 rows for the NULL (profile-holder) scope must fail."""
    import sqlite3
    conn = open_db()
    try:
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate, is_baseline) "
            "VALUES ('hybrid', '[]', '2026-05-01T00:00:00Z', NULL, 1)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate, is_baseline) "
                "VALUES ('hybrid', '[]', '2026-05-02T00:00:00Z', NULL, 1)"
            )
            conn.commit()
    finally:
        conn.close()


def test_partial_unique_index_ignores_archived(fresh_db):
    """An archived is_baseline=1 row does not block a new active is_baseline=1 row."""
    conn = open_db()
    try:
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, archived_at, for_candidate, is_baseline) "
            "VALUES ('hybrid', '[]', '2026-05-01T00:00:00Z', '2026-05-02T00:00:00Z', 'Alice Example', 1)"
        )
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate, is_baseline) "
            "VALUES ('hybrid', '[]', '2026-05-03T00:00:00Z', 'Alice Example', 1)"
        )
        conn.commit()
    finally:
        conn.close()


def test_backfill_marks_oldest_per_candidate_as_baseline(fresh_db):
    """Pre-existing rows: the oldest non-archived row per for_candidate gets is_baseline=1."""
    conn = open_db()
    # Roll back the migration baseline so we can simulate pre-0004 rows.
    # Insert two candidate scopes, two rows each, varying created_at.
    try:
        # NULL for_candidate scope
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate) "
            "VALUES ('hybrid', '[]', '2026-04-01T00:00:00Z', NULL)"
        )
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate) "
            "VALUES ('hybrid', '[]', '2026-04-15T00:00:00Z', NULL)"
        )
        # Named scope
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate) "
            "VALUES ('hybrid', '[]', '2026-04-10T00:00:00Z', 'Bob Example')"
        )
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate) "
            "VALUES ('hybrid', '[]', '2026-04-20T00:00:00Z', 'Bob Example')"
        )
        conn.commit()
    finally:
        conn.close()
    # Re-run the migration's backfill explicitly by calling the helper.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_mig4",
        r"c:\Brains_Resume_Skill\scripts\tracker\migrations\0004_drift_analytics.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    conn = open_db()
    try:
        mod.backfill_baselines(conn)
        rows = conn.execute(
            "SELECT for_candidate, created_at, is_baseline FROM resume_versions ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    # Two rows per scope, oldest of each is baseline.
    by_scope_first = {}
    for fc, ts, bl in rows:
        key = fc or "<null>"
        by_scope_first.setdefault(key, []).append((ts, bl))
    for scope, entries in by_scope_first.items():
        entries.sort()
        assert entries[0][1] == 1, f"oldest row for {scope!r} should be is_baseline=1"
        for _, bl in entries[1:]:
            assert bl == 0
