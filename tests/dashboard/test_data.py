"""Tests for scripts/dashboard/data.py — the cached wrappers over tracker.query."""
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    """Each test gets an isolated empty tracker db."""
    # Clear caches before the test
    from scripts.dashboard.data import clear_all_caches
    clear_all_caches()

    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path / "test.db"


def test_cached_list_applications_delegates_to_query(fresh_db):
    from scripts.dashboard.data import cached_list_applications
    # Empty db -> empty list
    result = cached_list_applications()
    assert result == []


def test_cached_list_applications_returns_application_rows(fresh_db):
    from scripts.dashboard.data import cached_list_applications
    from scripts.tracker.add import add_application, add_jd, add_resume_version
    rv = add_resume_version(file_path=None, template="hybrid", focus_areas=[])
    jd = add_jd(
        source="paste", source_ref=None, company="Example Corp",
        role_title="Senior Engineer", raw_text="x", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    add_application(
        jd_id=jd, resume_version_id=rv, cover_letter_id=None,
        submitted_at=datetime.now(), channel="direct",
    )
    result = cached_list_applications()
    assert len(result) == 1
    assert result[0].company == "Example Corp"


def test_cached_weekly_summary_delegates(fresh_db):
    from scripts.dashboard.data import cached_weekly_summary
    summary = cached_weekly_summary()
    assert summary.applications_count == 0


def test_cached_efficacy_by_template_delegates(fresh_db):
    from scripts.dashboard.data import cached_efficacy_by_template
    result = cached_efficacy_by_template()
    assert result == []


def test_cached_find_duplicates_delegates(fresh_db):
    from scripts.dashboard.data import cached_find_duplicates
    result = cached_find_duplicates("Example Corp", "Senior Engineer")
    assert result == []


def test_clear_all_caches_function_exists():
    """data.py must expose a function that clears every cached wrapper at once."""
    from scripts.dashboard.data import clear_all_caches
    # Should be callable and not raise.
    clear_all_caches()
