"""Tests for the tile widgets' pure helpers."""
import pytest

from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.tracker.add import add_jd, add_resume_version
from scripts.dashboard.widgets.tiles import (
    pacing_summary, library_counts, drift_tile_summary,
    render_tile_pacing, render_tile_drift, render_tile_library_counts,
    render_tile_recent_outcomes,
)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    from scripts.dashboard.data import clear_all_caches
    clear_all_caches()
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_pacing_summary_no_target(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    s = pacing_summary(cid)
    assert s["this_week"] == 0
    assert s["target"] is None


def test_pacing_summary_with_target(isolated):
    cid = create_candidate("A", "B", [], 3, None)
    set_active_candidate(cid)
    assert pacing_summary(cid)["target"] == 3


def test_library_counts(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    add_resume_version(None, "hybrid", [])
    counts = library_counts(cid)
    assert counts["resumes"] == 1
    assert counts["jds"] == 1
    assert counts["cover_letters"] == 0


def test_drift_tile_summary_empty(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    s = drift_tile_summary({"candidate_id": cid})
    assert s["headline_pct"] is None
    assert s["count"] == 0


def test_tile_render_fns_are_callable():
    for fn in (render_tile_pacing, render_tile_drift,
               render_tile_library_counts, render_tile_recent_outcomes):
        assert callable(fn)
