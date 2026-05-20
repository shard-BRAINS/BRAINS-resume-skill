"""Tests for the B-migration backfill hook."""
import json

import pytest


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def _write_legacy_profile(path, **fields):
    payload = {
        "first_name": "Matthew", "last_name": "Gell",
        "focus_areas": ["data eng"], "healthy_weekly_rate": 5,
        "pacing_notes": None, "log_handoffs": True,
    }
    payload.update(fields)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_backfill_creates_seed_candidate_from_legacy_profile(isolated):
    _write_legacy_profile(isolated / "profile.json")
    from scripts.tracker.db import open_db
    conn = open_db()  # this should run the backfill
    try:
        rows = conn.execute(
            "SELECT first_name, last_name, focus_areas, healthy_weekly_rate "
            "FROM candidates"
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0][0] == "Matthew"
    assert rows[0][1] == "Gell"
    assert json.loads(rows[0][2]) == ["data eng"]
    assert rows[0][3] == 5


def test_backfill_sets_active_candidate_in_profile_json(isolated):
    _write_legacy_profile(isolated / "profile.json")
    from scripts.tracker.db import open_db
    open_db().close()
    data = json.loads((isolated / "profile.json").read_text(encoding="utf-8"))
    assert data.get("active_candidate_id") is not None
    assert "first_name" not in data
    assert "focus_areas" not in data


def test_backfill_links_existing_artifacts_to_seed_candidate(isolated):
    """Pre-existing artifacts (from a v1.5/1.6 install) get linked."""
    _write_legacy_profile(isolated / "profile.json")
    from scripts.tracker.db import open_db
    conn = open_db()
    try:
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at) "
            "VALUES ('chronological', '[]', '2026-05-01T00:00:00Z')"
        )
        conn.commit()
    finally:
        conn.close()
    conn = open_db()
    try:
        rv = conn.execute(
            "SELECT candidate_id FROM resume_versions"
        ).fetchone()
        active_id = conn.execute(
            "SELECT id FROM candidates LIMIT 1"
        ).fetchone()[0]
    finally:
        conn.close()
    assert rv[0] == active_id


def test_backfill_assigns_distinct_candidate_for_for_candidate_rows(isolated):
    _write_legacy_profile(isolated / "profile.json")
    from scripts.tracker.db import open_db
    conn = open_db()  # creates schema and seed candidate
    try:
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, for_candidate, created_at) "
            "VALUES ('hybrid', '[]', 'Mathilda Gell', '2026-05-19T00:00:00Z')"
        )
        conn.commit()
    finally:
        conn.close()
    conn = open_db()  # second open re-runs backfill, picking up the new row
    try:
        candidates = conn.execute(
            "SELECT first_name, last_name FROM candidates ORDER BY id"
        ).fetchall()
        rv = conn.execute(
            "SELECT candidate_id, for_candidate FROM resume_versions"
        ).fetchone()
        mathilda_id = conn.execute(
            "SELECT id FROM candidates WHERE first_name='Mathilda'"
        ).fetchone()
    finally:
        conn.close()
    names = {(c[0], c[1]) for c in candidates}
    assert ("Matthew", "Gell") in names
    assert ("Mathilda", "Gell") in names
    assert mathilda_id is not None
    assert rv[0] == mathilda_id[0]
    assert rv[1] == "Mathilda Gell"  # for_candidate cache preserved


def test_backfill_is_idempotent(isolated):
    _write_legacy_profile(isolated / "profile.json")
    from scripts.tracker.db import open_db
    open_db().close()
    open_db().close()
    open_db().close()
    conn = open_db()
    try:
        count = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    finally:
        conn.close()
    assert count == 1  # one seed candidate, not three
