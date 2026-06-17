"""Smoke test: disclosure preference propagates from save → downstream read.

The downstream workflow specs (tailor.md, cover-letter.md, review.md) all read
the candidate's landed disclosure strength via
`scripts.tracker.disclosure.get_latest_for_candidate(candidate_id)`. This test
covers the contract those specs depend on:

  1. A candidate with no session has no preference (returns None).
  2. After a session is recorded the latest landed_strength is readable.
  3. Recording a newer session shadows the older one (recency wins).
  4. The PDF/MD generator persists an artifact_uid that round-trips to the row.
  5. Archiving the latest session falls back to the prior non-archived one.

If any of these break, the downstream auto-apply behaviour silently breaks too.
"""
import pytest


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    return tmp_path


def test_disclosure_preference_propagates_end_to_end(isolated):
    from scripts.generators.disclosure_worksheet import generate
    from scripts.tracker import disclosure as disclosure_db
    from scripts.tracker.candidates import create_candidate

    cid = create_candidate("Matthew", "Gell", [], None, None)

    # 1. No session → no preference.
    assert disclosure_db.get_latest_for_candidate(cid) is None

    # 2. Record a non-disclosure session — the read picks it up.
    s1 = disclosure_db.create_session(
        candidate_id=cid,
        landed_strength="non-disclosure",
        target_employer="Acme Corp",
        factor_5="No — values not in play here",
        notes="Default position holds for this employer.",
    )
    latest = disclosure_db.get_latest_for_candidate(cid)
    assert latest is not None
    assert latest.id == s1
    assert latest.landed_strength == "non-disclosure"
    assert latest.target_employer == "Acme Corp"

    # 3. A newer session shadows the older one (recency wins).
    import time
    time.sleep(0.01)
    s2 = disclosure_db.create_session(
        candidate_id=cid,
        landed_strength="explicit",
        target_employer="Inclusive Co",
        factor_1="Yes — formal programme",
        factor_2="Yes — accessibility role",
        factor_3="Yes — ND-targeted recruiter channel",
        factor_5="Yes — values aligned",
    )
    latest = disclosure_db.get_latest_for_candidate(cid)
    assert latest.id == s2
    assert latest.landed_strength == "explicit"

    # 4. Generate a worksheet for the latest session; artifact_uid round-trips.
    md_path, pdf_path = generate(s2)
    assert md_path.exists() and pdf_path.exists()
    refreshed = disclosure_db.get_latest_for_candidate(cid)
    assert refreshed.artifact_uid is not None
    assert refreshed.artifact_uid in md_path.name
    assert refreshed.artifact_uid in pdf_path.name

    # 5. Archiving the latest session falls back to the prior one.
    disclosure_db.archive_session(s2)
    latest = disclosure_db.get_latest_for_candidate(cid)
    assert latest is not None
    assert latest.id == s1
    assert latest.landed_strength == "non-disclosure"


def test_undecided_session_signals_no_strong_preference(isolated):
    """The 'undecided' value is preserved and downstream workflows can detect it.

    The workflow specs treat 'undecided' the same as no session — surface that
    no preference is set and proceed without disclosure-driven changes.
    """
    from scripts.tracker import disclosure as disclosure_db
    from scripts.tracker.candidates import create_candidate

    cid = create_candidate("Sam", "Test", [], None, None)
    disclosure_db.create_session(
        candidate_id=cid,
        landed_strength="undecided",
        notes="Still thinking it through.",
    )
    latest = disclosure_db.get_latest_for_candidate(cid)
    assert latest is not None
    assert latest.landed_strength == "undecided"


def test_multi_candidate_preference_isolation(isolated):
    """Each candidate's preference is independent."""
    from scripts.tracker import disclosure as disclosure_db
    from scripts.tracker.candidates import create_candidate

    a = create_candidate("Alice", "A", [], None, None)
    b = create_candidate("Bob", "B", [], None, None)
    disclosure_db.create_session(candidate_id=a, landed_strength="explicit")
    disclosure_db.create_session(candidate_id=b, landed_strength="non-disclosure")
    assert disclosure_db.get_latest_for_candidate(a).landed_strength == "explicit"
    assert disclosure_db.get_latest_for_candidate(b).landed_strength == "non-disclosure"
