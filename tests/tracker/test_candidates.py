"""Tests for scripts/tracker/candidates.py."""
import pytest


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_create_and_get_candidate(isolated):
    from scripts.tracker.candidates import create_candidate, get_candidate
    cid = create_candidate(
        first_name="Mathilda", last_name="Gell",
        focus_areas=["retail"], healthy_weekly_rate=2, pacing_notes=None,
    )
    c = get_candidate(cid)
    assert c is not None
    assert c.first_name == "Mathilda"
    assert c.last_name == "Gell"
    assert c.focus_areas == ["retail"]


def test_list_candidates_excludes_archived(isolated):
    from scripts.tracker.candidates import (
        create_candidate, archive_candidate, list_candidates,
    )
    cid1 = create_candidate("Matthew", "Gell", [], None, None)
    cid2 = create_candidate("Mathilda", "Gell", [], None, None)
    archive_candidate(cid1)
    rows = list_candidates()
    assert [c.id for c in rows] == [cid2]


def test_set_and_get_active_candidate(isolated):
    from scripts.tracker.candidates import (
        create_candidate, set_active_candidate, get_active_candidate,
    )
    cid = create_candidate("Matthew", "Gell", [], None, None)
    set_active_candidate(cid)
    active = get_active_candidate()
    assert active is not None
    assert active.id == cid


def test_get_active_candidate_returns_none_when_unset(isolated):
    from scripts.tracker.candidates import get_active_candidate
    assert get_active_candidate() is None


def test_update_candidate(isolated):
    from scripts.tracker.candidates import (
        create_candidate, update_candidate, get_candidate,
    )
    cid = create_candidate("Matthew", "Gell", [], None, None)
    update_candidate(cid, focus_areas=["data eng"], healthy_weekly_rate=5)
    c = get_candidate(cid)
    assert c.focus_areas == ["data eng"]
    assert c.healthy_weekly_rate == 5
