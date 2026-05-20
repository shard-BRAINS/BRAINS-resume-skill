"""Lineage walking: parent skipping archived, baseline resolution, cycle guard."""
import pytest

from scripts.tracker.add import add_resume_version
from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.tracker.db import open_db


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


def _make_candidate(first="Mathilda", last="Gell"):
    """Create a candidate and make it active; return its id."""
    cid = create_candidate(first, last, [], None, None)
    set_active_candidate(cid)
    return cid


def _insert_snapshot(artifact_uid: str, facts: dict):
    import json
    from datetime import datetime
    conn = open_db()
    try:
        conn.execute(
            "INSERT INTO resume_fact_snapshots (artifact_uid, facts, created_at) "
            "VALUES (?, ?, ?)",
            (artifact_uid, json.dumps(facts), datetime.utcnow().isoformat() + "Z"),
        )
        conn.commit()
    finally:
        conn.close()


def test_get_parent_snapshot_returns_parent(fresh_db):
    from scripts.drift.lineage import get_parent_snapshot

    cid = _make_candidate()
    add_resume_version(None, "hybrid", [], artifact_uid="PARENT",
                       candidate_id=cid)
    add_resume_version(None, "hybrid", [], artifact_uid="CHILD",
                       parent_uid="PARENT", candidate_id=cid)
    _insert_snapshot("PARENT", {"skills": ["A"]})
    out = get_parent_snapshot("CHILD")
    assert out == {"skills": ["A"]}


def test_get_parent_snapshot_skips_archived(fresh_db):
    from datetime import datetime
    from scripts.drift.lineage import get_parent_snapshot

    cid = _make_candidate()
    add_resume_version(None, "hybrid", [], artifact_uid="GRAND",
                       candidate_id=cid)
    # Archive PARENT mid-chain.
    add_resume_version(None, "hybrid", [], artifact_uid="PARENT",
                       parent_uid="GRAND", candidate_id=cid)
    conn = open_db()
    try:
        conn.execute(
            "UPDATE resume_versions SET archived_at=? WHERE artifact_uid=?",
            (datetime.utcnow().isoformat() + "Z", "PARENT"),
        )
        conn.commit()
    finally:
        conn.close()
    add_resume_version(None, "hybrid", [], artifact_uid="CHILD",
                       parent_uid="PARENT", candidate_id=cid)
    _insert_snapshot("GRAND", {"skills": ["G"]})
    out = get_parent_snapshot("CHILD")
    # Skips archived PARENT, returns GRAND's snapshot.
    assert out == {"skills": ["G"]}


def test_get_parent_snapshot_returns_none_when_no_parent(fresh_db):
    from scripts.drift.lineage import get_parent_snapshot
    cid = _make_candidate()
    add_resume_version(None, "hybrid", [], artifact_uid="ORPHAN",
                       candidate_id=cid)
    assert get_parent_snapshot("ORPHAN") is None


def test_get_baseline_snapshot_returns_baseline(fresh_db):
    from scripts.drift.lineage import get_baseline_snapshot
    cid = _make_candidate()
    add_resume_version(None, "hybrid", [], artifact_uid="BL",
                       candidate_id=cid)
    add_resume_version(None, "hybrid", [], artifact_uid="V2",
                       parent_uid="BL", candidate_id=cid)
    _insert_snapshot("BL", {"skills": ["baseline"]})
    out = get_baseline_snapshot("V2")
    assert out == {"skills": ["baseline"]}


def test_get_baseline_snapshot_returns_none_when_no_baseline(fresh_db):
    from scripts.drift.lineage import get_baseline_snapshot
    cid = _make_candidate()
    add_resume_version(None, "hybrid", [], artifact_uid="ALONE",
                       candidate_id=cid, is_baseline=False)
    assert get_baseline_snapshot("ALONE") is None


def test_get_baseline_snapshot_scoped_to_candidate(fresh_db):
    """Baseline resolution must scope by candidate_id, not leak across candidates."""
    from scripts.drift.lineage import get_baseline_snapshot
    cid_a = create_candidate("Alice", "A", [], None, None)
    cid_b = create_candidate("Bob", "B", [], None, None)
    # Candidate A: baseline + derivative.
    add_resume_version(None, "hybrid", [], artifact_uid="A_BL", candidate_id=cid_a)
    add_resume_version(None, "hybrid", [], artifact_uid="A_V2",
                       parent_uid="A_BL", candidate_id=cid_a)
    _insert_snapshot("A_BL", {"skills": ["alice"]})
    # Candidate B: its own baseline with a different snapshot.
    add_resume_version(None, "hybrid", [], artifact_uid="B_BL", candidate_id=cid_b)
    _insert_snapshot("B_BL", {"skills": ["bob"]})
    # A_V2 must resolve to A's baseline only.
    assert get_baseline_snapshot("A_V2") == {"skills": ["alice"]}


def test_get_candidate_lineage_scoped_to_candidate(fresh_db):
    """get_candidate_lineage must only return rows for the given candidate_id."""
    from scripts.drift.lineage import get_candidate_lineage
    cid_a = create_candidate("Alice", "A", [], None, None)
    cid_b = create_candidate("Bob", "B", [], None, None)
    add_resume_version(None, "hybrid", [], artifact_uid="A1", candidate_id=cid_a)
    add_resume_version(None, "hybrid", [], artifact_uid="A2",
                       parent_uid="A1", candidate_id=cid_a)
    add_resume_version(None, "hybrid", [], artifact_uid="B1", candidate_id=cid_b)
    lineage = get_candidate_lineage({"candidate_id": cid_a})
    uids = {rv.artifact_uid for rv in lineage}
    assert uids == {"A1", "A2"}


def test_cycle_guard_caps_walk_at_100(fresh_db):
    """A malformed parent chain (cycle) returns None instead of infinite-looping."""
    from scripts.drift.lineage import get_parent_snapshot
    cid = _make_candidate()
    # Build a cycle: A -> B -> A.
    add_resume_version(None, "hybrid", [], artifact_uid="A", parent_uid="B",
                       candidate_id=cid)
    add_resume_version(None, "hybrid", [], artifact_uid="B", parent_uid="A",
                       candidate_id=cid)
    # No snapshots - walker should bail by depth 100, not infinite-loop.
    out = get_parent_snapshot("A")
    assert out is None
