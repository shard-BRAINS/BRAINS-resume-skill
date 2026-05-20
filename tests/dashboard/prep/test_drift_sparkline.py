"""Drift trajectory sparkline prep."""
import json

import pytest

from scripts.drift.compute import write_snapshot_and_compute_drift
from scripts.tracker.add import add_resume_version
from scripts.tracker.db import open_db


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


def _seed_lineage():
    """Baseline + 3 derivatives with increasing drift on skills."""
    skills_list = [["A"], ["A", "B"], ["A", "B", "C"], ["A", "B", "C", "D"]]
    facts_template = {
        "identity": {"name": "X", "location": "Y", "email": "x@y", "phone": "0"},
        "experience": [], "education": [], "skills": ["A"],
        "certifications": None, "standalone_achievements": None,
        "hobbies": None, "languages": None, "publications": None,
        "portfolio_links": None,
    }
    uids = ["BL", "V2", "V3", "V4"]
    parents = [None, "BL", "V2", "V3"]
    for uid, parent, sk in zip(uids, parents, skills_list):
        add_resume_version(None, "hybrid", [], artifact_uid=uid,
                           parent_uid=parent, for_candidate="Test")
        write_snapshot_and_compute_drift(uid, {**facts_template, "skills": sk})
    return uids


def test_returns_n_most_recent(fresh_db):
    from scripts.dashboard.prep.drift_sparkline import drift_trajectory_last_n
    _seed_lineage()
    out = drift_trajectory_last_n({"for_candidate": "Test"}, n=3)
    assert len(out) == 3
    # Most-recent path — V2, V3, V4.
    assert [p["artifact_uid"] for p in out] == ["V2", "V3", "V4"]


def test_returns_all_when_fewer_than_n(fresh_db):
    from scripts.dashboard.prep.drift_sparkline import drift_trajectory_last_n
    _seed_lineage()
    out = drift_trajectory_last_n({"for_candidate": "Test"}, n=20)
    assert len(out) == 4
    assert out[0]["artifact_uid"] == "BL"
    assert out[0]["overall_pct"] is None  # baseline has no vs_baseline


def test_overall_pct_increases_with_drift(fresh_db):
    from scripts.dashboard.prep.drift_sparkline import drift_trajectory_last_n
    _seed_lineage()
    out = drift_trajectory_last_n({"for_candidate": "Test"}, n=4)
    # Skips baseline (overall_pct is None there); pct should increase across derivatives.
    pcts = [p["overall_pct"] for p in out if p["overall_pct"] is not None]
    assert pcts == sorted(pcts)


def test_empty_lineage_returns_empty(fresh_db):
    from scripts.dashboard.prep.drift_sparkline import drift_trajectory_last_n
    assert drift_trajectory_last_n({"for_candidate": "Nobody"}, n=12) == []
