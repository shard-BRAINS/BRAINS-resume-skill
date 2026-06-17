"""Tests for scripts/tracker/disclosure.py."""
import time

import pytest


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


@pytest.fixture
def candidate_id(isolated):
    from scripts.tracker.candidates import create_candidate
    return create_candidate(
        first_name="Matthew", last_name="Gell",
        focus_areas=[], healthy_weekly_rate=None, pacing_notes=None,
    )


def test_create_and_get_session(candidate_id):
    from scripts.tracker.disclosure import create_session, get_session
    sid = create_session(
        candidate_id=candidate_id,
        landed_strength="neutral",
        target_employer="Acme Corp",
        target_role="Inclusive Design Lead",
        factor_1="Yes",
        factor_5="Conditional yes — employer-dependent",
        notes="First pass",
    )
    s = get_session(sid)
    assert s is not None
    assert s.candidate_id == candidate_id
    assert s.landed_strength == "neutral"
    assert s.target_employer == "Acme Corp"
    assert s.factor_1 == "Yes"
    assert s.factor_2 is None
    assert s.notes == "First pass"
    assert s.artifact_uid is None
    assert s.archived_at is None


def test_create_session_rejects_invalid_strength(candidate_id):
    from scripts.tracker.disclosure import create_session
    with pytest.raises(ValueError, match="landed_strength"):
        create_session(candidate_id=candidate_id, landed_strength="bogus")


def test_list_sessions_most_recent_first(candidate_id):
    from scripts.tracker.disclosure import create_session, list_sessions_for_candidate
    s1 = create_session(candidate_id=candidate_id, landed_strength="non-disclosure")
    time.sleep(0.01)
    s2 = create_session(candidate_id=candidate_id, landed_strength="neutral")
    time.sleep(0.01)
    s3 = create_session(candidate_id=candidate_id, landed_strength="explicit")
    rows = list_sessions_for_candidate(candidate_id)
    assert [r.id for r in rows] == [s3, s2, s1]


def test_list_excludes_archived_by_default(candidate_id):
    from scripts.tracker.disclosure import (
        create_session, archive_session, list_sessions_for_candidate,
    )
    s1 = create_session(candidate_id=candidate_id, landed_strength="non-disclosure")
    s2 = create_session(candidate_id=candidate_id, landed_strength="neutral")
    archive_session(s1)
    rows = list_sessions_for_candidate(candidate_id)
    assert [r.id for r in rows] == [s2]
    rows_all = list_sessions_for_candidate(candidate_id, include_archived=True)
    assert {r.id for r in rows_all} == {s1, s2}


def test_get_latest_returns_most_recent_non_archived(candidate_id):
    from scripts.tracker.disclosure import (
        create_session, archive_session, get_latest_for_candidate,
    )
    s1 = create_session(candidate_id=candidate_id, landed_strength="non-disclosure")
    time.sleep(0.01)
    s2 = create_session(candidate_id=candidate_id, landed_strength="explicit")
    latest = get_latest_for_candidate(candidate_id)
    assert latest.id == s2
    archive_session(s2)
    latest = get_latest_for_candidate(candidate_id)
    assert latest.id == s1


def test_get_latest_returns_none_when_no_sessions(candidate_id):
    from scripts.tracker.disclosure import get_latest_for_candidate
    assert get_latest_for_candidate(candidate_id) is None


def test_update_landed_strength(candidate_id):
    from scripts.tracker.disclosure import (
        create_session, update_landed_strength, get_session,
    )
    sid = create_session(candidate_id=candidate_id, landed_strength="undecided")
    update_landed_strength(sid, "explicit")
    assert get_session(sid).landed_strength == "explicit"


def test_update_landed_strength_validates(candidate_id):
    from scripts.tracker.disclosure import create_session, update_landed_strength
    sid = create_session(candidate_id=candidate_id, landed_strength="undecided")
    with pytest.raises(ValueError):
        update_landed_strength(sid, "yolo")


def test_set_artifact_uid(candidate_id):
    from scripts.tracker.disclosure import create_session, set_artifact_uid, get_session
    sid = create_session(candidate_id=candidate_id, landed_strength="neutral")
    set_artifact_uid(sid, "ds-deadbeef")
    assert get_session(sid).artifact_uid == "ds-deadbeef"


def test_sessions_isolated_by_candidate(isolated):
    from scripts.tracker.candidates import create_candidate
    from scripts.tracker.disclosure import (
        create_session, list_sessions_for_candidate,
    )
    a = create_candidate("Alice", "A", [], None, None)
    b = create_candidate("Bob", "B", [], None, None)
    create_session(candidate_id=a, landed_strength="explicit")
    create_session(candidate_id=b, landed_strength="non-disclosure")
    a_rows = list_sessions_for_candidate(a)
    b_rows = list_sessions_for_candidate(b)
    assert len(a_rows) == 1 and a_rows[0].landed_strength == "explicit"
    assert len(b_rows) == 1 and b_rows[0].landed_strength == "non-disclosure"
