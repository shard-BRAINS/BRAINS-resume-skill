"""Smoke test for the /brains-track slash command's underlying helpers.

Exercises add → record_outcome → query summary flow end-to-end.
"""
from datetime import datetime

from scripts.tracker.add import (
    add_application, add_jd, add_resume_version, record_outcome,
)
from scripts.tracker.query import (
    efficacy_by_template, list_applications, weekly_summary,
)


def test_track_smoke_full_lifecycle(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))

    # Seed two applications with different outcomes
    rv1 = add_resume_version(file_path=None, template="hybrid", focus_areas=[])
    rv2 = add_resume_version(file_path=None, template="chronological", focus_areas=[])
    jd_id = add_jd(
        source="paste", source_ref=None, company="X", role_title="Y",
        raw_text="z", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    app1 = add_application(
        jd_id=jd_id, resume_version_id=rv1, cover_letter_id=None,
        submitted_at=datetime.now(), channel="linkedin",
    )
    app2 = add_application(
        jd_id=jd_id, resume_version_id=rv2, cover_letter_id=None,
        submitted_at=datetime.now(), channel="direct",
    )
    record_outcome(app1, "callback", datetime.now())
    record_outcome(app2, "rejection", datetime.now())

    # /brains-track list
    rows = list_applications()
    assert len(rows) == 2

    # /brains-track summary
    s = weekly_summary()
    assert s.applications_count == 2
    assert s.outcomes_by_type.get("callback", 0) == 1
    assert s.outcomes_by_type.get("rejection", 0) == 1

    # efficacy_by_template (used by /brains-track summary)
    eff = efficacy_by_template()
    by_template = {r.template: r for r in eff}
    assert by_template["hybrid"].callback_count == 1
    assert by_template["chronological"].rejection_count == 1
