"""Tests for scripts/tracker/query.py — the read-side public API."""
from datetime import datetime, timedelta

import pytest

from scripts.tracker.add import (
    add_application, add_jd, add_resume_version, record_outcome,
)
from scripts.tracker.query import list_applications, find_duplicates


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path / "test.db"


def _make_app(company, days_ago=0, role="Engineer", channel="direct"):
    """Helper: seed an application for the given company submitted N days ago."""
    rv_id = add_resume_version(
        file_path=None, template="chronological", focus_areas=[],
    )
    jd_id = add_jd(
        source="paste", source_ref=None, company=company,
        role_title=role, raw_text="x", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    when = datetime.now() - timedelta(days=days_ago)
    return add_application(
        jd_id=jd_id, resume_version_id=rv_id, cover_letter_id=None,
        submitted_at=when, channel=channel,
    )


def test_list_applications_empty(fresh_db):
    rows = list_applications()
    assert rows == []


def test_list_applications_returns_all_by_default(fresh_db):
    _make_app("Example Corp")
    _make_app("Sample Industries")
    rows = list_applications()
    assert len(rows) == 2


def test_list_applications_filter_by_company(fresh_db):
    _make_app("Example Corp")
    _make_app("Sample Industries")
    _make_app("Example Corp", role="Designer")
    rows = list_applications(company="Example Corp")
    assert len(rows) == 2
    for r in rows:
        assert r.company == "Example Corp"


def test_list_applications_filter_by_since(fresh_db):
    _make_app("Old Co", days_ago=30)
    _make_app("New Co", days_ago=2)
    cutoff = datetime.now() - timedelta(days=7)
    rows = list_applications(since=cutoff)
    assert len(rows) == 1
    assert rows[0].company == "New Co"


def test_list_applications_each_row_has_basic_fields(fresh_db):
    _make_app("Test Co", role="Senior Engineer", channel="agency")
    rows = list_applications()
    r = rows[0]
    assert r.company == "Test Co"
    assert r.role_title == "Senior Engineer"
    assert r.channel == "agency"
    assert hasattr(r, "id")
    assert hasattr(r, "submitted_at")
    assert hasattr(r, "latest_outcome")  # event_type or None


def test_list_applications_latest_outcome_populated(fresh_db):
    app_id = _make_app("Test Co")
    record_outcome(app_id, "acknowledged", datetime.now())
    record_outcome(app_id, "callback", datetime.now())
    rows = list_applications()
    assert rows[0].latest_outcome == "callback"


def test_list_applications_excludes_archived(fresh_db):
    # No public archive API yet, but list_applications must respect archived_at IS NULL.
    from scripts.tracker.db import open_db
    _make_app("Live Co")
    archived_id = _make_app("Archived Co")
    conn = open_db()
    try:
        conn.execute(
            "UPDATE applications SET archived_at = ? WHERE id = ?",
            ("2026-05-13T00:00:00Z", archived_id),
        )
        conn.commit()
    finally:
        conn.close()
    rows = list_applications()
    assert {r.company for r in rows} == {"Live Co"}


def test_find_duplicates_missing_db_returns_empty(monkeypatch, tmp_path):
    """If the db file doesn't exist (tracker never used), return empty list, no crash."""
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "never_created.db"))
    result = find_duplicates("Example Corp", "Senior Engineer")
    assert result == []


def test_find_duplicates_returns_recent_match(fresh_db):
    _make_app("Example Corp", role="Senior Engineer", days_ago=5)
    result = find_duplicates("Example Corp", "Senior Engineer")
    assert len(result) == 1


def test_find_duplicates_excludes_outside_window(fresh_db):
    _make_app("Example Corp", role="Senior Engineer", days_ago=90)
    result = find_duplicates("Example Corp", "Senior Engineer", within_days=60)
    assert result == []


def test_find_duplicates_case_insensitive_company(fresh_db):
    _make_app("Example Corp", role="Senior Engineer", days_ago=5)
    result = find_duplicates("example corp", "Senior Engineer")
    assert len(result) == 1
