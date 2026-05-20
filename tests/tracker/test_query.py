"""Tests for scripts/tracker/query.py — the read-side public API."""
from datetime import datetime, timedelta

import pytest

from scripts.tracker.add import (
    add_application, add_jd, add_resume_version, record_outcome,
)
from scripts.tracker.query import list_applications, find_duplicates


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    """Isolate BOTH the tracker DB and the profile.json paths to tmp_path.

    The candidate-scoping tests call set_active_candidate/get_active_candidate,
    which read+write profile.json — so the profile path must be isolated too.
    """
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path / "test.db"


@pytest.fixture
def fresh_db(isolated):
    """Each test gets an isolated empty db + an active candidate.

    Builds on `isolated` (both DB and profile paths isolated). Since every
    insert now defaults candidate_id to the active candidate, this fixture
    creates one and sets it active so pre-existing tests keep working without
    passing candidate_id explicitly.
    """
    from scripts.tracker.candidates import create_candidate, set_active_candidate

    cid = create_candidate("Matthew", "Gell", [], None, None)
    set_active_candidate(cid)
    return isolated


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


# --- Task 8: weekly_summary + efficacy_by_template tests ---


def test_weekly_summary_empty_db_returns_zero(fresh_db):
    from scripts.tracker.query import weekly_summary
    s = weekly_summary()
    assert s.applications_count == 0
    assert s.outcomes_by_type == {}
    assert s.pacing_vs_target is None


def test_weekly_summary_counts_last_7_days(fresh_db):
    from scripts.tracker.query import weekly_summary
    _make_app("Old Co", days_ago=10)  # outside window
    _make_app("New A", days_ago=2)
    _make_app("New B", days_ago=5)
    s = weekly_summary()
    assert s.applications_count == 2


def test_weekly_summary_outcomes_by_type(fresh_db):
    from scripts.tracker.query import weekly_summary
    a1 = _make_app("Co1", days_ago=1)
    a2 = _make_app("Co2", days_ago=2)
    record_outcome(a1, "callback", datetime.now())
    record_outcome(a2, "rejection", datetime.now())
    record_outcome(a2, "withdrew", datetime.now())  # only most-recent per app counted
    s = weekly_summary()
    # All 3 events are within the last week — we count each event, not per-app
    assert s.outcomes_by_type.get("callback", 0) == 1
    assert s.outcomes_by_type.get("rejection", 0) == 1
    assert s.outcomes_by_type.get("withdrew", 0) == 1


def test_weekly_summary_pacing_above_target(isolated):
    from scripts.tracker.query import weekly_summary
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    cid = create_candidate("Matthew", "Gell", [], 2, None)  # healthy_weekly_rate=2
    set_active_candidate(cid)
    _make_app("A"); _make_app("B"); _make_app("C")  # 3 in last week
    s = weekly_summary()
    assert s.pacing_vs_target == "above"


def test_weekly_summary_pacing_at_target(isolated):
    from scripts.tracker.query import weekly_summary
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    cid = create_candidate("Matthew", "Gell", [], 2, None)  # healthy_weekly_rate=2
    set_active_candidate(cid)
    _make_app("A"); _make_app("B")
    s = weekly_summary()
    assert s.pacing_vs_target == "at"


def test_weekly_summary_pacing_below_target(isolated):
    from scripts.tracker.query import weekly_summary
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    cid = create_candidate("Matthew", "Gell", [], 5, None)  # healthy_weekly_rate=5
    set_active_candidate(cid)
    _make_app("A")
    s = weekly_summary()
    assert s.pacing_vs_target == "below"


def test_weekly_summary_pacing_none_when_no_target(fresh_db):
    from scripts.tracker.query import weekly_summary
    _make_app("A")
    s = weekly_summary()
    assert s.pacing_vs_target is None


def test_efficacy_by_template_groups_by_resume_template(fresh_db):
    from scripts.tracker.query import efficacy_by_template
    # Seed two apps with hybrid resumes, one with chronological
    rv1 = add_resume_version(file_path=None, template="hybrid", focus_areas=[])
    rv2 = add_resume_version(file_path=None, template="hybrid", focus_areas=[])
    rv3 = add_resume_version(file_path=None, template="chronological", focus_areas=[])
    jd_id = add_jd(
        source="paste", source_ref=None, company="X", role_title="Y",
        raw_text="z", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    a1 = add_application(jd_id=jd_id, resume_version_id=rv1,
                          cover_letter_id=None,
                          submitted_at=datetime.now(), channel="direct")
    a2 = add_application(jd_id=jd_id, resume_version_id=rv2,
                          cover_letter_id=None,
                          submitted_at=datetime.now(), channel="direct")
    a3 = add_application(jd_id=jd_id, resume_version_id=rv3,
                          cover_letter_id=None,
                          submitted_at=datetime.now(), channel="direct")
    record_outcome(a1, "callback", datetime.now())
    record_outcome(a2, "rejection", datetime.now())
    record_outcome(a3, "callback", datetime.now())

    rows = efficacy_by_template()
    by_template = {r.template: r for r in rows}
    assert by_template["hybrid"].submitted_count == 2
    assert by_template["hybrid"].callback_count == 1
    assert by_template["hybrid"].rejection_count == 1
    assert by_template["chronological"].submitted_count == 1
    assert by_template["chronological"].callback_count == 1


def test_efficacy_by_template_interview_count_aggregates(fresh_db):
    from scripts.tracker.query import efficacy_by_template
    rv = add_resume_version(file_path=None, template="hybrid", focus_areas=[])
    jd_id = add_jd(
        source="paste", source_ref=None, company="X", role_title="Y",
        raw_text="z", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    app_id = add_application(
        jd_id=jd_id, resume_version_id=rv, cover_letter_id=None,
        submitted_at=datetime.now(), channel="direct",
    )
    record_outcome(app_id, "phone_screen", datetime.now())
    record_outcome(app_id, "first_round", datetime.now())
    record_outcome(app_id, "second_round", datetime.now())
    rows = efficacy_by_template()
    assert rows[0].interview_count >= 3


# --- Task 12: get_artifact_by_uid lookup helper ---


def test_get_artifact_by_uid_finds_resume(fresh_db):
    from scripts.tracker.query import get_artifact_by_uid
    from scripts.tracker.models import ResumeVersion
    add_resume_version("/tmp/r.docx", "hybrid", [], artifact_uid="KX7M9Q")
    result = get_artifact_by_uid("KX7M9Q")
    assert isinstance(result, ResumeVersion)
    assert result.artifact_uid == "KX7M9Q"


def test_get_artifact_by_uid_finds_cover_letter(fresh_db):
    from scripts.tracker.query import get_artifact_by_uid
    from scripts.tracker.models import CoverLetter
    from scripts.tracker.add import add_cover_letter
    rv_id = add_resume_version("/tmp/r.docx", "hybrid", [])
    jd_id = add_jd("manual", None, "Acme", "Eng", "...", {}, [], [])
    add_cover_letter("/tmp/cl.docx", rv_id, jd_id, "formal-business",
                     artifact_uid="H8VR3W")
    result = get_artifact_by_uid("H8VR3W")
    assert isinstance(result, CoverLetter)
    assert result.artifact_uid == "H8VR3W"


def test_get_artifact_by_uid_returns_none_on_miss(fresh_db):
    from scripts.tracker.query import get_artifact_by_uid
    assert get_artifact_by_uid("ZZZZZZ") is None


# --- Task 4 (multi-candidate Approach C): for_candidate on read path ---


def test_get_artifact_by_uid_returns_for_candidate(fresh_db):
    from scripts.tracker.add import add_resume_version
    from scripts.tracker.query import get_artifact_by_uid

    rv_id = add_resume_version(
        None, "hybrid", [], artifact_uid="ABC123",
        for_candidate="Mathilda Gell",
    )
    row = get_artifact_by_uid("ABC123")
    assert row is not None
    assert row.for_candidate == "Mathilda Gell"


def test_list_artifacts_for_candidate(fresh_db):
    from scripts.tracker.add import add_resume_version
    from scripts.tracker.candidates import create_candidate
    from scripts.tracker.query import list_artifacts_for_candidate

    mathilda = create_candidate("Mathilda", "Gell", [], None, None)
    add_resume_version(None, "hybrid", [], candidate_id=mathilda)
    add_resume_version(None, "chronological", [], candidate_id=mathilda)
    add_resume_version(None, "chronological", [])  # active candidate (Matthew)
    rows = list_artifacts_for_candidate("Mathilda Gell")
    assert len(rows) == 2
    assert all(r.candidate_id == mathilda for r in rows)


def test_list_artifacts_for_candidate_empty_when_no_match(fresh_db):
    from scripts.tracker.query import list_artifacts_for_candidate
    assert list_artifacts_for_candidate("Nobody") == []


# --- Task 7 (multi-candidate Approach B): reads scope to active candidate ---


def test_list_jds_default_filters_to_active_candidate(isolated):
    from scripts.tracker.add import add_jd
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    from scripts.tracker.query import list_jds

    matthew = create_candidate("Matthew", "Gell", [], None, None)
    mathilda = create_candidate("Mathilda", "Gell", [], None, None)
    set_active_candidate(matthew)
    add_jd("manual", None, "Acme", "Eng", "...", {}, [], [])
    set_active_candidate(mathilda)
    add_jd("manual", None, "Big W", "Sales Asst", "...", {}, [], [])

    set_active_candidate(matthew)
    rows = list_jds()
    assert {r.company for r in rows} == {"Acme"}

    set_active_candidate(mathilda)
    rows = list_jds()
    assert {r.company for r in rows} == {"Big W"}


def test_list_jds_explicit_candidate_id_override(isolated):
    from scripts.tracker.add import add_jd
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    from scripts.tracker.query import list_jds

    matthew = create_candidate("Matthew", "Gell", [], None, None)
    mathilda = create_candidate("Mathilda", "Gell", [], None, None)
    set_active_candidate(matthew)
    add_jd("manual", None, "Acme", "Eng", "...", {}, [], [])
    set_active_candidate(mathilda)
    add_jd("manual", None, "Big W", "Sales Asst", "...", {}, [], [])

    rows_all = list_jds(candidate_id=0)
    assert {r.company for r in rows_all} == {"Acme", "Big W"}
