"""Tests for the five hardcoded playbook definitions."""
import pytest

from scripts.playbooks.definitions import all_playbooks, get_playbook
from scripts.playbooks.models import STEP_KINDS


def test_five_playbooks_defined():
    keys = {pb.key for pb in all_playbooks()}
    assert keys == {
        "apply_to_job", "build_resume", "improve_resume",
        "refresh_linkedin", "career_change",
    }


def test_get_playbook_returns_match():
    pb = get_playbook("apply_to_job")
    assert pb.label == "Apply to a job"
    assert len(pb.steps) == 6


def test_get_playbook_unknown_key_raises():
    with pytest.raises(KeyError):
        get_playbook("does_not_exist")


def test_every_step_has_a_valid_kind():
    for pb in all_playbooks():
        for step in pb.steps:
            assert step.kind in STEP_KINDS


def test_handoff_steps_have_a_command():
    for pb in all_playbooks():
        for step in pb.steps:
            if step.kind == "handoff":
                assert step.command, f"{pb.key}/{step.key} missing command"


def test_in_dashboard_steps_have_no_predicate():
    """in_dashboard steps complete synchronously; they never carry a predicate."""
    for pb in all_playbooks():
        for step in pb.steps:
            if step.kind == "in_dashboard":
                assert step.predicate is None


def test_apply_to_job_step_keys_in_order():
    pb = get_playbook("apply_to_job")
    assert [s.key for s in pb.steps] == [
        "analyze_jd", "tailor_resume", "cover_letter",
        "final_check", "precheck", "submit_track",
    ]


def test_step_keys_unique_within_each_playbook():
    for pb in all_playbooks():
        keys = [s.key for s in pb.steps]
        assert len(keys) == len(set(keys)), f"duplicate step key in {pb.key}"
