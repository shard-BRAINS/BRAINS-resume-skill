"""Tests for playbook_runs CRUD."""
import pytest

from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.playbooks.runs import (
    start_run, get_run, list_active_runs, set_run_jd,
    set_run_step, advance_run, abandon_run,
)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_start_run_creates_active_run_at_step_zero(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    run_id = start_run(cid, "apply_to_job")
    run = get_run(run_id)
    assert run.candidate_id == cid
    assert run.playbook_key == "apply_to_job"
    assert run.current_step == 0
    assert run.status == "active"
    assert run.completed_at is None


def test_start_run_rejects_unknown_playbook(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    with pytest.raises(KeyError):
        start_run(cid, "not_a_playbook")


def test_get_run_returns_none_for_missing(isolated):
    create_candidate("A", "B", [], None, None)
    assert get_run(999) is None


def test_list_active_runs_excludes_completed_and_abandoned(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    active = start_run(cid, "apply_to_job")
    done = start_run(cid, "improve_resume")
    gone = start_run(cid, "career_change")
    abandon_run(gone)
    # Drive `done` to completion via set_run_step past the last step.
    set_run_step(done, 99)
    ids = {r.id for r in list_active_runs(cid)}
    assert ids == {active}


def test_set_run_jd(isolated):
    from scripts.tracker.add import add_jd
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    run_id = start_run(cid, "apply_to_job")
    set_run_jd(run_id, jd)
    assert get_run(run_id).jd_id == jd


def test_advance_run_increments_step(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    run_id = start_run(cid, "apply_to_job")
    advance_run(run_id)
    assert get_run(run_id).current_step == 1


def test_advance_past_last_step_completes_the_run(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    # career_change has exactly one step.
    run_id = start_run(cid, "career_change")
    run = advance_run(run_id)
    assert run.status == "completed"
    assert run.completed_at is not None
    assert run.current_step == 1


def test_set_run_step_can_go_backwards(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    run_id = start_run(cid, "apply_to_job")
    set_run_step(run_id, 3)
    assert get_run(run_id).current_step == 3
    set_run_step(run_id, 1)
    run = get_run(run_id)
    assert run.current_step == 1
    assert run.status == "active"


def test_set_run_step_clamps_negative_to_zero(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    run_id = start_run(cid, "apply_to_job")
    set_run_step(run_id, -5)
    assert get_run(run_id).current_step == 0


def test_abandon_run(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    run_id = start_run(cid, "apply_to_job")
    abandon_run(run_id)
    assert get_run(run_id).status == "abandoned"
