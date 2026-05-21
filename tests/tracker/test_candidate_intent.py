"""Tests for candidate email + career-intent CRUD."""
import pytest

from scripts.tracker.candidates import (
    create_candidate, get_candidate, update_candidate_intent,
)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_create_candidate_stores_email(isolated):
    cid = create_candidate("Mathilda", "Gell", [], None, None,
                           email="mathilda@example.com")
    assert get_candidate(cid).email == "mathilda@example.com"


def test_create_candidate_email_defaults_none(isolated):
    cid = create_candidate("A", "B", [], None, None)
    c = get_candidate(cid)
    assert c.email is None
    assert c.intent_collected_at is None
    assert c.career_stage is None
    assert c.target_roles == []


def test_update_candidate_intent_writes_fields(isolated):
    cid = create_candidate("A", "B", [], None, None)
    update_candidate_intent(
        cid,
        career_stage="student",
        direction="first_role",
        target_roles=["Retail assistant", "Barista"],
        target_industries=["Retail"],
        leadership_intent="maybe",
        work_preferences=["part_time", "casual"],
        location="Brisbane QLD",
        relocation_open=0,
        role_priorities="Flexible hours.",
        timeline="actively_applying",
    )
    c = get_candidate(cid)
    assert c.career_stage == "student"
    assert c.direction == "first_role"
    assert c.target_roles == ["Retail assistant", "Barista"]
    assert c.target_industries == ["Retail"]
    assert c.leadership_intent == "maybe"
    assert c.work_preferences == ["part_time", "casual"]
    assert c.location == "Brisbane QLD"
    assert c.relocation_open == 0
    assert c.role_priorities == "Flexible hours."
    assert c.timeline == "actively_applying"


def test_update_candidate_intent_stamps_collected_at(isolated):
    cid = create_candidate("A", "B", [], None, None)
    assert get_candidate(cid).intent_collected_at is None
    update_candidate_intent(cid, career_stage="mid")
    assert get_candidate(cid).intent_collected_at is not None
