"""Tests for the playbook runner (evaluate_run auto-advance)."""
import pytest

from scripts.tracker.add import add_jd, add_resume_version, add_cover_letter
from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.playbooks.runs import start_run, get_run, set_run_jd, set_run_step
from scripts.playbooks.runner import evaluate_run


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_evaluate_holds_on_in_dashboard_step(isolated):
    """Step 0 of apply_to_job is in_dashboard (no predicate) — evaluate_run
    must not advance it."""
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    run_id = start_run(cid, "apply_to_job")
    run = evaluate_run(run_id)
    assert run.current_step == 0


def test_evaluate_holds_when_predicate_unsatisfied(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    run_id = start_run(cid, "apply_to_job", jd_id=jd)
    set_run_step(run_id, 1)  # move onto tailor_resume (has a predicate)
    run = evaluate_run(run_id)
    assert run.current_step == 1  # no resume yet


def test_evaluate_advances_when_predicate_satisfied(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    run_id = start_run(cid, "apply_to_job", jd_id=jd)
    set_run_step(run_id, 1)  # tailor_resume
    add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    run = evaluate_run(run_id)
    assert run.current_step == 2  # advanced onto cover_letter


def test_evaluate_advances_through_multiple_satisfied_steps(isolated):
    """If both the resume and cover letter exist, evaluate_run advances
    through tailor_resume AND cover_letter, then stops at final_check
    (in_dashboard, no predicate)."""
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    rv = add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    add_cover_letter(None, rv, jd, "standard")
    run_id = start_run(cid, "apply_to_job", jd_id=jd)
    set_run_step(run_id, 1)  # tailor_resume
    run = evaluate_run(run_id)
    assert run.current_step == 3  # stopped at final_check


def test_evaluate_is_noop_on_completed_run(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    run_id = start_run(cid, "career_change")
    set_run_step(run_id, 99)  # complete it
    run = evaluate_run(run_id)
    assert run.status == "completed"


def test_evaluate_returns_none_for_missing_run(isolated):
    create_candidate("A", "B", [], None, None)
    assert evaluate_run(999) is None
