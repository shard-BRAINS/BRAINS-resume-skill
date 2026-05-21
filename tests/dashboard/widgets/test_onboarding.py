"""Tests for the onboarding surface helpers."""
import pytest

from scripts.tracker.candidates import (
    create_candidate, get_candidate, update_candidate_intent,
)
from scripts.tracker.add import add_resume_version
from scripts.tracker.candidates import set_active_candidate
from scripts.dashboard.widgets.onboarding import (
    onboarding_needed, resume_context, render_onboarding,
    CAREER_STAGES, DIRECTIONS, TIMELINES,
)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_onboarding_needed_true_before_intent(isolated):
    cid = create_candidate("A", "B", [], None, None)
    assert onboarding_needed(get_candidate(cid)) is True


def test_onboarding_needed_false_after_intent(isolated):
    cid = create_candidate("A", "B", [], None, None)
    update_candidate_intent(cid, career_stage="mid")
    assert onboarding_needed(get_candidate(cid)) is False


def test_resume_context_no_resume(isolated):
    cid = create_candidate("A", "B", [], None, None)
    ctx = resume_context(cid)
    assert ctx["has_resume"] is False
    assert ctx["count"] == 0


def test_resume_context_with_resume(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    add_resume_version(None, "hybrid", [])
    ctx = resume_context(cid)
    assert ctx["has_resume"] is True
    assert ctx["count"] == 1
    assert ctx["latest_template"] == "hybrid"


def test_constants_are_nonempty_tuples():
    for const in (CAREER_STAGES, DIRECTIONS, TIMELINES):
        assert isinstance(const, tuple)
        assert len(const) > 0


def test_render_onboarding_is_callable():
    assert callable(render_onboarding)
