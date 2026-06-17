"""Baseline promotion: single-baseline invariant, audit log, recompute trigger."""
import json

import pytest

from scripts.drift.compute import write_snapshot_and_compute_drift
from scripts.tracker.add import add_resume_version
from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.tracker.db import open_db


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


def _seed():
    """Build a baseline + 2 derivatives for a fresh candidate. Returns the id."""
    cid = create_candidate("Test", "Candidate", [], None, None)
    set_active_candidate(cid)

    facts_base = {
        "identity": {"name": "X", "location": "Q", "email": "x@y", "phone": "0"},
        "experience": [], "education": [], "skills": ["A"],
        "certifications": None, "standalone_achievements": None,
        "hobbies": None, "languages": None, "publications": None,
        "portfolio_links": None,
    }
    facts_v2 = {**facts_base, "skills": ["A", "B"]}
    facts_v3 = {**facts_base, "skills": ["A", "B", "C"]}

    add_resume_version(None, "hybrid", [], artifact_uid="BL", candidate_id=cid)
    write_snapshot_and_compute_drift("BL", facts_base)

    add_resume_version(None, "hybrid", [], artifact_uid="V2",
                       parent_uid="BL", candidate_id=cid)
    write_snapshot_and_compute_drift("V2", facts_v2)

    add_resume_version(None, "hybrid", [], artifact_uid="V3",
                       parent_uid="V2", candidate_id=cid)
    write_snapshot_and_compute_drift("V3", facts_v3)
    return cid


def test_promote_flips_is_baseline(fresh_db):
    from scripts.drift.baseline import promote_baseline
    cid = _seed()
    promote_baseline("V2", reason="Test promotion")
    conn = open_db()
    try:
        rows = dict(conn.execute(
            "SELECT artifact_uid, is_baseline FROM resume_versions "
            "WHERE candidate_id=?", (cid,),
        ).fetchall())
    finally:
        conn.close()
    assert rows["BL"] == 0
    assert rows["V2"] == 1
    assert rows["V3"] == 0


def test_promote_appends_history_row(fresh_db):
    from scripts.drift.baseline import promote_baseline
    cid = _seed()
    promote_baseline("V2", reason="Real-life change")
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT candidate_id, artifact_uid, reason "
            "FROM baseline_history WHERE artifact_uid='V2'"
        ).fetchone()
    finally:
        conn.close()
    # candidate_id is written to baseline_history (non-null, == the candidate).
    assert row[0] == cid
    assert row[0] is not None
    assert row[1] == "V2"
    assert row[2] == "Real-life change"


def test_promote_scoped_to_candidate(fresh_db):
    """promote_baseline must not clear or recompute another candidate's rows."""
    from scripts.drift.baseline import promote_baseline
    cid_a = _seed()
    # A second candidate with its own baseline.
    cid_b = create_candidate("Other", "Person", [], None, None)
    set_active_candidate(cid_b)
    add_resume_version(None, "hybrid", [], artifact_uid="B_BL", candidate_id=cid_b)
    # Promote V2 within candidate A's scope.
    promote_baseline("V2", reason="x")
    conn = open_db()
    try:
        b_baseline = conn.execute(
            "SELECT is_baseline FROM resume_versions WHERE artifact_uid='B_BL'"
        ).fetchone()[0]
        hist_b = conn.execute(
            "SELECT COUNT(*) FROM baseline_history WHERE candidate_id=?", (cid_b,),
        ).fetchone()[0]
    finally:
        conn.close()
    # Candidate B's baseline untouched, no spurious history rows for B.
    assert b_baseline == 1
    assert hist_b == 0


def test_promote_recomputes_vs_baseline_for_descendants(fresh_db):
    """After promoting V2, V3's vs_baseline_score should be recomputed against V2."""
    from scripts.drift.baseline import promote_baseline
    _seed()
    # V3 vs_baseline_score before promotion (computed against BL: skills A vs A,B,C = 100%).
    promote_baseline("V2", reason="x")
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT vs_baseline_score FROM resume_drift_scores WHERE artifact_uid='V3'"
        ).fetchone()
    finally:
        conn.close()
    score = json.loads(row[0])
    # V3 vs V2: skills A,B vs A,B,C -> 1 added of 3 = ~33%.
    assert score["skills"]["pct"] == pytest.approx(33.333333, abs=0.01)


def test_promote_sets_promoted_baseline_to_null_drift(fresh_db):
    """The newly-promoted baseline's own vs_baseline_score becomes null."""
    from scripts.drift.baseline import promote_baseline
    _seed()
    promote_baseline("V2", reason="x")
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT vs_baseline_score FROM resume_drift_scores WHERE artifact_uid='V2'"
        ).fetchone()
    finally:
        conn.close()
    assert row[0] is None
