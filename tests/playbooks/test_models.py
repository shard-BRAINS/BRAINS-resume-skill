"""Tests for the playbook engine dataclasses."""
from scripts.playbooks.models import PlaybookStep, Playbook, PlaybookRun


def test_playbook_step_defaults():
    step = PlaybookStep(key="review", label="Review", kind="in_dashboard")
    assert step.command is None
    assert step.predicate is None


def test_playbook_step_with_handoff_fields():
    sentinel = lambda conn, run: True
    step = PlaybookStep(
        key="tailor_resume", label="Tailor", kind="handoff",
        command="tailor", predicate=sentinel,
    )
    assert step.kind == "handoff"
    assert step.command == "tailor"
    assert step.predicate is sentinel


def test_playbook_holds_ordered_steps():
    s1 = PlaybookStep(key="a", label="A", kind="in_dashboard")
    s2 = PlaybookStep(key="b", label="B", kind="handoff", command="edit")
    pb = Playbook(key="demo", label="Demo", steps=(s1, s2))
    assert pb.steps[0].key == "a"
    assert pb.steps[1].key == "b"
    assert len(pb.steps) == 2


def test_playbook_run_is_mutable_with_full_fields():
    run = PlaybookRun(
        id=1, candidate_id=2, playbook_key="apply_to_job", jd_id=7,
        current_step=3, status="active",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z", completed_at=None,
    )
    run.current_step = 4
    assert run.current_step == 4
