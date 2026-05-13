"""Smoke test for the deterministic portion of the pre-application check.

Exercises: tracker lookup, profile read, weekly_summary, add_application, all
working end-to-end on a clean fixture-driven scenario.
"""
from datetime import datetime, timedelta

from scripts.tracker.add import (
    add_application, add_jd, add_resume_version,
)
from scripts.tracker.models import Profile
from scripts.tracker.profile import write_profile
from scripts.tracker.query import find_duplicates, weekly_summary


def test_precheck_smoke_no_duplicates_no_pacing(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))

    # Q1: no duplicates yet
    assert find_duplicates("Example Corp", "Senior Engineer") == []

    # Q4 setup: no healthy rate yet → pacing returns None
    assert weekly_summary().pacing_vs_target is None

    # Q4 follow-up: user sets healthy rate
    write_profile(Profile(focus_areas=["python"], healthy_weekly_rate=3))

    # Q6: register the application
    rv = add_resume_version(file_path="/tmp/r.docx", template="hybrid", focus_areas=["python"])
    jd_id = add_jd(
        source="paste", source_ref=None,
        company="Example Corp", role_title="Senior Engineer",
        raw_text="JD text", analyzer_findings={},
        focus_areas_required=["python"], focus_areas_nice=[],
    )
    app_id = add_application(
        jd_id=jd_id, resume_version_id=rv, cover_letter_id=None,
        submitted_at=datetime.now(), channel="direct",
        notes='{"fit_or_pressure": "genuine fit"}',
    )
    assert app_id > 0

    # Subsequent precheck for the SAME company + role would now flag a duplicate
    assert len(find_duplicates("Example Corp", "Senior Engineer")) == 1
