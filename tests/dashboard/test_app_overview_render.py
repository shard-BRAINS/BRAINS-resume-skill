"""AppTest happy-path: the Overview tab renders without exceptions.

Uses streamlit.testing.v1.AppTest to drive a synthetic Streamlit session.
Empty tracker db -> the app should render with "No applications" / idle-state
callouts rather than crashing.
"""
from pathlib import Path

import pytest

APP_PATH = Path(__file__).parent.parent.parent / "scripts" / "dashboard" / "app.py"


@pytest.fixture
def empty_tracker(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    return tmp_path


def test_app_loads_overview_tab_with_empty_db(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=10)
    # App should render without exceptions
    assert not at.exception, f"App raised: {at.exception}"


def test_app_renders_title(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=10)
    # Find the title element
    titles = [t.value for t in at.title]
    assert "BRAINS Resume Dashboard" in titles


def test_overview_includes_drift_trajectory_tile(monkeypatch, tmp_path):
    """Overview renders a drift trajectory tile reading from drift_trajectory_last_n."""
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))

    from scripts.drift.compute import write_snapshot_and_compute_drift
    from scripts.tracker.add import add_resume_version
    from scripts.tracker.candidates import create_candidate, set_active_candidate

    cid = create_candidate("Matthew", "Gell", [], None, None)
    set_active_candidate(cid)

    facts = {
        "identity": {"name": "Matthew Gell", "location": "X",
                     "email": "m@x", "phone": "0"},
        "experience": [], "education": [], "skills": ["A"],
        "certifications": None, "standalone_achievements": None,
        "hobbies": None, "languages": None, "publications": None,
        "portfolio_links": None,
    }
    add_resume_version(None, "hybrid", [], artifact_uid="BL", candidate_id=cid)
    write_snapshot_and_compute_drift("BL", facts)
    add_resume_version(None, "hybrid", [], artifact_uid="V2", parent_uid="BL",
                       candidate_id=cid)
    write_snapshot_and_compute_drift("V2", {**facts, "skills": ["A", "B"]})

    from scripts.dashboard.tabs.overview import _drift_tile_summary
    summary = _drift_tile_summary({"candidate_id": cid})
    # The most-recent (V2) drift, plus sparkline series.
    assert summary["headline_pct"] is not None
    assert isinstance(summary["sparkline"], list)
    assert len(summary["sparkline"]) >= 1


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_overview_counts_scope_to_active_candidate(isolated):
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    from scripts.tracker.add import add_jd

    matthew = create_candidate("Matthew", "Gell", [], None, None)
    mathilda = create_candidate("Mathilda", "Gell", [], None, None)
    set_active_candidate(matthew)
    add_jd("manual", None, "Acme", "Eng", "...", {}, [], [])

    set_active_candidate(mathilda)
    from scripts.dashboard.tabs.overview import _summary_counts
    counts = _summary_counts()
    assert counts["jds"] == 0

    set_active_candidate(matthew)
    counts = _summary_counts()
    assert counts["jds"] == 1
