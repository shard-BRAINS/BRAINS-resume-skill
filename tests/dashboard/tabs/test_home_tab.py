"""Tests for the Home tab."""
import pytest

from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.dashboard.tabs.home import effective_layout


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_effective_layout_default_when_no_saved(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    layout = effective_layout(cid)
    # default: every catalog widget present; playbooks enabled
    keys = {w.key for w, _ in layout}
    assert "playbook_apply" in keys
    assert ("tile_recent_outcomes" in keys)
    enabled = {w.key for w, en in layout if en}
    assert "playbook_apply" in enabled
    assert "tile_recent_outcomes" not in enabled


def test_effective_layout_reflects_saved(isolated):
    from scripts.dashboard.widgets.layout import save_layout
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    save_layout(cid, [("worklist", False)])
    layout = effective_layout(cid)
    by_key = {w.key: en for w, en in layout}
    assert by_key["worklist"] is False
