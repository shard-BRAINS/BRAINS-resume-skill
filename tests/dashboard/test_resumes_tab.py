"""Resumes tab row builder includes drift columns."""
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


def test_row_builder_includes_drift_columns(fresh_db):
    from scripts.dashboard.tabs.resumes import _build_resume_rows

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

    rows = _build_resume_rows({"candidate_id": cid})
    by_uid = {r["artifact_uid"]: r for r in rows}

    # Baseline row: both drift values are '—' (None mapped to display dash).
    assert by_uid["BL"]["drift_vs_parent"] is None
    assert by_uid["BL"]["drift_vs_baseline"] is None
    # V2: skills 0→1 of 2 → 50%; identity etc unchanged.
    assert by_uid["V2"]["drift_vs_parent"] is not None
    assert by_uid["V2"]["drift_vs_baseline"] is not None
    assert by_uid["V2"]["headline_changes_vs_baseline"]  # at least one entry
