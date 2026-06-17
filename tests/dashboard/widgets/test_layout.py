"""Tests for dashboard_layout CRUD."""
import pytest

from scripts.tracker.candidates import create_candidate
from scripts.dashboard.widgets.layout import (
    get_saved_layout, save_layout, clear_layout,
)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_get_saved_layout_empty_when_none(isolated):
    cid = create_candidate("A", "B", [], None, None)
    assert get_saved_layout(cid) == []


def test_save_then_get_round_trip_preserves_order(isolated):
    cid = create_candidate("A", "B", [], None, None)
    save_layout(cid, [("worklist", True), ("tile_drift", False), ("quick_launch", True)])
    assert get_saved_layout(cid) == [
        ("worklist", True), ("tile_drift", False), ("quick_launch", True),
    ]


def test_save_layout_replaces_previous(isolated):
    cid = create_candidate("A", "B", [], None, None)
    save_layout(cid, [("worklist", True), ("tile_drift", True)])
    save_layout(cid, [("tile_pacing", False)])
    assert get_saved_layout(cid) == [("tile_pacing", False)]


def test_layout_is_per_candidate(isolated):
    a = create_candidate("A", "A", [], None, None)
    b = create_candidate("B", "B", [], None, None)
    save_layout(a, [("worklist", True)])
    save_layout(b, [("tile_drift", False)])
    assert get_saved_layout(a) == [("worklist", True)]
    assert get_saved_layout(b) == [("tile_drift", False)]


def test_clear_layout(isolated):
    cid = create_candidate("A", "B", [], None, None)
    save_layout(cid, [("worklist", True)])
    clear_layout(cid)
    assert get_saved_layout(cid) == []
