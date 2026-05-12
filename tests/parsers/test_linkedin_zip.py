"""Tests for the LinkedIn ZIP parser.

Critical safeguarding requirement: the parser MUST skip files containing
third-party PII (Connections.csv, messages.csv, Invitations.csv) and MUST
log which files were skipped so the user sees the behaviour.
"""
from pathlib import Path
import pytest

from scripts.parsers.linkedin_zip import parse_linkedin_export

FIXTURE = Path(__file__).parent.parent.parent / "docs" / "testing" / "fixtures" / "synthetic_linkedin_export.zip"


def test_parser_returns_structured_dict():
    result = parse_linkedin_export(FIXTURE)
    assert isinstance(result, dict)
    for key in ("profile", "positions", "education", "skills",
                "certifications", "projects", "publications", "languages",
                "skipped_files"):
        assert key in result, f"Missing key: {key}"


def test_profile_extracted():
    result = parse_linkedin_export(FIXTURE)
    profile = result["profile"]
    assert profile.get("First Name") == "Alex"
    assert profile.get("Last Name") == "Test"
    assert "Eight years" in profile.get("Summary", "")


def test_positions_extracted_as_list():
    result = parse_linkedin_export(FIXTURE)
    assert isinstance(result["positions"], list)
    assert len(result["positions"]) == 2
    titles = [p.get("Title") for p in result["positions"]]
    assert "Senior Engineer" in titles
    assert "Software Engineer" in titles


def test_education_extracted():
    result = parse_linkedin_export(FIXTURE)
    assert len(result["education"]) == 1
    assert result["education"][0].get("School Name") == "Example University"


def test_skills_extracted_as_list_of_strings():
    result = parse_linkedin_export(FIXTURE)
    assert "Python" in result["skills"]
    assert "Distributed Systems" in result["skills"]


def test_connections_csv_is_skipped():
    result = parse_linkedin_export(FIXTURE)
    skipped = result["skipped_files"]
    assert "Connections.csv" in skipped


def test_messages_csv_is_skipped():
    result = parse_linkedin_export(FIXTURE)
    assert "messages.csv" in result["skipped_files"]


def test_invitations_csv_is_skipped():
    result = parse_linkedin_export(FIXTURE)
    assert "Invitations.csv" in result["skipped_files"]


def test_parser_raises_on_missing_zip():
    with pytest.raises(FileNotFoundError):
        parse_linkedin_export(Path("does_not_exist.zip"))


def test_parser_raises_on_non_zip_file(tmp_path):
    not_a_zip = tmp_path / "fake.zip"
    not_a_zip.write_text("not a zip", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_linkedin_export(not_a_zip)
