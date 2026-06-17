"""Integration: write_snapshot_and_compute_drift persists snapshot + scores."""
import json

import pytest

from scripts.tracker.add import add_resume_version
from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.tracker.db import open_db


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


def _make_candidate(first="Test", last="Candidate"):
    """Create a candidate and make it active; return its id."""
    cid = create_candidate(first, last, [], None, None)
    set_active_candidate(cid)
    return cid


SAMPLE_FACTS = {
    "identity": {"name": "X", "location": "Y", "email": "x@y", "phone": "0"},
    "experience": [], "education": [], "skills": [],
    "certifications": None, "standalone_achievements": None,
    "hobbies": None, "languages": None, "publications": None,
    "portfolio_links": None,
}


def test_writes_snapshot_row(fresh_db):
    from scripts.drift.compute import write_snapshot_and_compute_drift

    cid = _make_candidate()
    add_resume_version(None, "hybrid", [], artifact_uid="ABC",
                       candidate_id=cid)
    write_snapshot_and_compute_drift("ABC", SAMPLE_FACTS)

    conn = open_db()
    try:
        row = conn.execute(
            "SELECT facts, schema_version FROM resume_fact_snapshots "
            "WHERE artifact_uid=?", ("ABC",),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert json.loads(row[0]) == SAMPLE_FACTS
    assert row[1] == 1


def test_baseline_writes_null_drift_scores(fresh_db):
    """The baseline row has no parent and IS the baseline — both scores null."""
    from scripts.drift.compute import write_snapshot_and_compute_drift

    cid = _make_candidate()
    add_resume_version(None, "hybrid", [], artifact_uid="BL",
                       candidate_id=cid)
    write_snapshot_and_compute_drift("BL", SAMPLE_FACTS)

    conn = open_db()
    try:
        row = conn.execute(
            "SELECT vs_parent_score, vs_baseline_score "
            "FROM resume_drift_scores WHERE artifact_uid=?", ("BL",),
        ).fetchone()
    finally:
        conn.close()
    assert row[0] is None
    assert row[1] is None


def test_derivative_writes_both_scores(fresh_db):
    """A child of the baseline: both vs_parent and vs_baseline computed."""
    from scripts.drift.compute import write_snapshot_and_compute_drift

    cid = _make_candidate()
    add_resume_version(None, "hybrid", [], artifact_uid="BL",
                       candidate_id=cid)
    write_snapshot_and_compute_drift("BL", SAMPLE_FACTS)

    add_resume_version(None, "hybrid", [], artifact_uid="CHILD",
                       parent_uid="BL", candidate_id=cid)
    child_facts = {**SAMPLE_FACTS,
                   "identity": {**SAMPLE_FACTS["identity"], "location": "Z"}}
    write_snapshot_and_compute_drift("CHILD", child_facts)

    conn = open_db()
    try:
        row = conn.execute(
            "SELECT vs_parent_score, vs_baseline_score "
            "FROM resume_drift_scores WHERE artifact_uid=?", ("CHILD",),
        ).fetchone()
    finally:
        conn.close()
    parent_score = json.loads(row[0])
    baseline_score = json.loads(row[1])
    assert parent_score["identity"]["pct"] == 25.0
    assert baseline_score["identity"]["pct"] == 25.0


def test_idempotent_on_resave(fresh_db):
    """Calling write twice for the same UID overwrites cleanly (no duplicate rows)."""
    from scripts.drift.compute import write_snapshot_and_compute_drift

    cid = _make_candidate()
    add_resume_version(None, "hybrid", [], artifact_uid="ABC",
                       candidate_id=cid)
    write_snapshot_and_compute_drift("ABC", SAMPLE_FACTS)
    write_snapshot_and_compute_drift("ABC", SAMPLE_FACTS)

    conn = open_db()
    try:
        n_snap = conn.execute(
            "SELECT COUNT(*) FROM resume_fact_snapshots WHERE artifact_uid=?",
            ("ABC",),
        ).fetchone()[0]
        n_score = conn.execute(
            "SELECT COUNT(*) FROM resume_drift_scores WHERE artifact_uid=?",
            ("ABC",),
        ).fetchone()[0]
    finally:
        conn.close()
    assert n_snap == 1
    assert n_score == 1
