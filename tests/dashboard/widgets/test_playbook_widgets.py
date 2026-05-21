"""Tests for playbook widgets — focus on the pure helper."""
import pytest

from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.playbooks.runs import start_run
from scripts.dashboard.widgets.playbook_widgets import (
    active_run_rows, make_playbook_card_renderer, render_in_progress_runs,
)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_active_run_rows_empty(isolated):
    cid = create_candidate("A", "B", [], None, None)
    assert active_run_rows(cid) == []


def test_active_run_rows_describes_a_run(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    start_run(cid, "apply_to_job")
    rows = active_run_rows(cid)
    assert len(rows) == 1
    row = rows[0]
    assert row["playbook_label"] == "Apply to a job"
    assert row["step_number"] == 1          # 1-based for display
    assert row["total_steps"] == 6
    assert row["step_label"] == "Analyze the JD"
    assert row["status"] == "active"


def test_make_playbook_card_renderer_returns_callable(isolated):
    fn = make_playbook_card_renderer("build_resume")
    assert callable(fn)


def test_render_in_progress_runs_is_callable(isolated):
    assert callable(render_in_progress_runs)
