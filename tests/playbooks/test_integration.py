"""End-to-end: a full apply_to_job playbook run.

Simulates the dashboard: in_dashboard steps are advanced by hand (the
dashboard would run them itself); handoff steps auto-advance via evaluate_run
once their artifact lands in the tracker DB.
"""
from datetime import datetime

import pytest

from scripts.tracker.add import (
    add_jd, add_resume_version, add_cover_letter, add_application,
)
from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.playbooks.runs import (
    start_run, get_run, set_run_jd, set_run_step, advance_run,
)
from scripts.playbooks.runner import evaluate_run


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_full_apply_to_job_run(isolated):
    cid = create_candidate("Mathilda", "Gell", [], None, None)
    set_active_candidate(cid)

    # Start the run. Step 0 = analyze_jd (in_dashboard).
    run_id = start_run(cid, "apply_to_job")
    assert get_run(run_id).current_step == 0

    # Dashboard runs the JD analyzer -> a jd row, and records it on the run,
    # then advances past the in_dashboard step.
    jd = add_jd("manual", None, "Big W", "Sales Assistant", "x", {}, [], [])
    set_run_jd(run_id, jd)
    advance_run(run_id)                       # -> step 1 tailor_resume
    assert evaluate_run(run_id).current_step == 1   # no resume yet

    # Handoff: tailoring produces a resume tagged to the JD.
    rv = add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    assert evaluate_run(run_id).current_step == 2   # -> cover_letter

    # Handoff: the cover letter lands.
    add_cover_letter(None, rv, jd, "standard")
    assert evaluate_run(run_id).current_step == 3   # -> final_check (in_dashboard)

    # Dashboard runs the final check, then advances.
    advance_run(run_id)                       # -> step 4 precheck
    assert evaluate_run(run_id).current_step == 4   # precheck has no predicate

    # precheck is a manual-only handoff step.
    advance_run(run_id)                       # -> step 5 submit_track
    assert evaluate_run(run_id).current_step == 5   # no application yet

    # Handoff: the application is registered -> the run completes.
    add_application(jd, rv, None, datetime(2026, 2, 1), "direct")
    final = evaluate_run(run_id)
    assert final.status == "completed"
    assert final.completed_at is not None
