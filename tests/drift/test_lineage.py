"""Lineage walking: parent skipping archived, baseline resolution, cycle guard."""
import pytest

from scripts.tracker.add import add_resume_version
from scripts.tracker.db import open_db


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


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

    add_resume_version(None, "hybrid", [], artifact_uid="PARENT",
                       for_candidate="Mathilda Gell")
    add_resume_version(None, "hybrid", [], artifact_uid="CHILD",
                       parent_uid="PARENT", for_candidate="Mathilda Gell")
    _insert_snapshot("PARENT", {"skills": ["A"]})
    out = get_parent_snapshot("CHILD")
    assert out == {"skills": ["A"]}


def test_get_parent_snapshot_skips_archived(fresh_db):
    from datetime import datetime
    from scripts.drift.lineage import get_parent_snapshot

    add_resume_version(None, "hybrid", [], artifact_uid="GRAND",
                       for_candidate="X")
    # Archive PARENT mid-chain.
    add_resume_version(None, "hybrid", [], artifact_uid="PARENT",
                       parent_uid="GRAND", for_candidate="X")
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
                       parent_uid="PARENT", for_candidate="X")
    _insert_snapshot("GRAND", {"skills": ["G"]})
    out = get_parent_snapshot("CHILD")
    # Skips archived PARENT, returns GRAND's snapshot.
    assert out == {"skills": ["G"]}


def test_get_parent_snapshot_returns_none_when_no_parent(fresh_db):
    from scripts.drift.lineage import get_parent_snapshot
    add_resume_version(None, "hybrid", [], artifact_uid="ORPHAN",
                       for_candidate="Z")
    assert get_parent_snapshot("ORPHAN") is None


def test_get_baseline_snapshot_returns_baseline(fresh_db):
    from scripts.drift.lineage import get_baseline_snapshot
    add_resume_version(None, "hybrid", [], artifact_uid="BL",
                       for_candidate="W")
    add_resume_version(None, "hybrid", [], artifact_uid="V2",
                       parent_uid="BL", for_candidate="W")
    _insert_snapshot("BL", {"skills": ["baseline"]})
    out = get_baseline_snapshot("V2")
    assert out == {"skills": ["baseline"]}


def test_get_baseline_snapshot_returns_none_when_no_baseline(fresh_db):
    from scripts.drift.lineage import get_baseline_snapshot
    add_resume_version(None, "hybrid", [], artifact_uid="ALONE",
                       for_candidate="Q", is_baseline=False)
    assert get_baseline_snapshot("ALONE") is None


def test_cycle_guard_caps_walk_at_100(fresh_db):
    """A malformed parent chain (cycle) returns None instead of infinite-looping."""
    from scripts.drift.lineage import get_parent_snapshot
    # Build a cycle: A -> B -> A.
    add_resume_version(None, "hybrid", [], artifact_uid="A", parent_uid="B",
                       for_candidate="C")
    add_resume_version(None, "hybrid", [], artifact_uid="B", parent_uid="A",
                       for_candidate="C")
    # No snapshots - walker should bail by depth 100, not infinite-loop.
    out = get_parent_snapshot("A")
    assert out is None
