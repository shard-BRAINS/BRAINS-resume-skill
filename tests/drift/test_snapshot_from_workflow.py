"""Tests for facts_from_workflow_data (pure transform, no I/O)."""
import pytest

from scripts.drift.snapshot_from_workflow import facts_from_workflow_data


SAMPLE_WORKFLOW_DATA = {
    "candidate_name": "Mathilda Gell",
    "candidate_contact_line": "Rochedale, QLD  ·  0433 814 874  ·  mathilda@malin.com.au",
    "summary": "Grade 10 student at Redeemer Lutheran College.",
    "skills": (
        "• Customer engagement\n"
        "• Public speaking\n"
        "• Team leadership"
    ),
    "experience": (
        "Holiday Work — Faith Christian Distance Education\n"
        "Brisbane, QLD  ·  January 2026\n"
        "• Worked 5 to 6 days preparing enrolment material.\n"
        "• Packed and organised enrolment packs."
    ),
    "education": (
        "Redeemer Lutheran College — Rochedale, QLD\n"
        "Currently in Grade 10  ·  Expected to complete Year 12 in 2028"
    ),
}


def test_identity_parsed_from_contact_line():
    facts = facts_from_workflow_data(SAMPLE_WORKFLOW_DATA)
    assert facts["identity"]["name"] == "Mathilda Gell"
    assert facts["identity"]["location"] == "Rochedale, QLD"
    assert facts["identity"]["phone"] == "0433 814 874"
    assert facts["identity"]["email"] == "mathilda@malin.com.au"


def test_skills_parsed_as_list_of_strings():
    facts = facts_from_workflow_data(SAMPLE_WORKFLOW_DATA)
    assert facts["skills"] == [
        "Customer engagement",
        "Public speaking",
        "Team leadership",
    ]


def test_experience_parsed_into_entries():
    facts = facts_from_workflow_data(SAMPLE_WORKFLOW_DATA)
    assert len(facts["experience"]) == 1
    e = facts["experience"][0]
    assert e["entry_id"] == "exp-1"
    assert e["employer"] == "Faith Christian Distance Education"
    assert e["title"] == "Holiday Work"
    assert e["start_date"] == "2026-01"
    assert e["end_date"] == "2026-01"
    assert e["location"] == "Brisbane, QLD"
    assert "Worked 5 to 6 days preparing enrolment material." in e["key_points"]


def test_education_parsed_into_entries():
    facts = facts_from_workflow_data(SAMPLE_WORKFLOW_DATA)
    assert len(facts["education"]) == 1
    ed = facts["education"][0]
    assert ed["entry_id"] == "edu-1"
    assert ed["institution"] == "Redeemer Lutheran College"
    assert "Grade 10" in ed["qualification"]


def test_uncaptured_classes_are_null_not_empty_list():
    """Workflow doesn't ask for hobbies/languages/publications/portfolio_links;
    they must be null (skipped in drift compute) not [] (treated as removed)."""
    facts = facts_from_workflow_data(SAMPLE_WORKFLOW_DATA)
    for cls in ("hobbies", "languages", "publications", "portfolio_links"):
        assert facts[cls] is None, f"{cls} must be null, not {facts[cls]!r}"


def test_certifications_and_achievements_inconsistent_workflow_returns_null():
    """When the workflow doesn't surface certifications or standalone_achievements
    as their own sections, the transform returns null for those classes too."""
    facts = facts_from_workflow_data(SAMPLE_WORKFLOW_DATA)
    # Sample data has neither — both null.
    assert facts["certifications"] is None
    assert facts["standalone_achievements"] is None


def test_schema_version_is_1():
    facts = facts_from_workflow_data(SAMPLE_WORKFLOW_DATA)
    # schema_version lives on the snapshot row, not in the facts dict — but
    # the transform exposes it via a constant for the writer to pick up.
    from scripts.drift.snapshot_from_workflow import SCHEMA_VERSION
    assert SCHEMA_VERSION == 1
