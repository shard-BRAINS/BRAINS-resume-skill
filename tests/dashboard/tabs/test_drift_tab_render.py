"""Drift tab — lineage strip, per-fact-class table, field-level diff."""
import json

import pytest

from scripts.drift.compute import write_snapshot_and_compute_drift
from scripts.tracker.add import add_resume_version
from scripts.tracker.candidates import create_candidate, set_active_candidate


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def _seed() -> int:
    """Create + activate a candidate, seed a baseline + derivative. Returns cid."""
    cid = create_candidate("X", "Candidate", [], None, None)
    set_active_candidate(cid)
    facts = {
        "identity": {"name": "X", "location": "Y", "email": "x@y", "phone": "0"},
        "experience": [], "education": [], "skills": ["A"],
        "certifications": None, "standalone_achievements": None,
        "hobbies": None, "languages": None, "publications": None,
        "portfolio_links": None,
    }
    add_resume_version(None, "hybrid", [], artifact_uid="BL", candidate_id=cid)
    write_snapshot_and_compute_drift("BL", facts)
    add_resume_version(None, "hybrid", [], artifact_uid="V2",
                       parent_uid="BL", candidate_id=cid)
    write_snapshot_and_compute_drift("V2", {**facts, "skills": ["A", "B"]})
    return cid


def test_lineage_data_for_strip(fresh_db):
    from scripts.dashboard.tabs.drift import _lineage_data
    cid = _seed()
    data = _lineage_data({"candidate_id": cid})
    assert data["baseline_uid"] == "BL"
    assert [n["artifact_uid"] for n in data["nodes"]] == ["BL", "V2"]
    assert data["nodes"][0]["is_baseline"] is True
    assert data["nodes"][1]["is_baseline"] is False


def test_selected_summary(fresh_db):
    from scripts.dashboard.tabs.drift import _selected_summary
    _seed()
    summary = _selected_summary("V2")
    assert summary["artifact_uid"] == "V2"
    assert summary["vs_parent_overall_pct"] is not None
    assert summary["vs_baseline_overall_pct"] is not None
    assert "skills" in summary["per_class_table"]


def test_field_level_changes_list(fresh_db):
    from scripts.dashboard.tabs.drift import _field_level_changes
    _seed()
    out = _field_level_changes("V2")
    # vs_baseline: skills [A] → [A,B] → set diff (added=["B"]).
    assert any("skill" in line.lower() and "B" in line for line in out)
