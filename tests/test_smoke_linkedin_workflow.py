"""Smoke test for the deterministic portion of the LinkedIn-ingest workflow."""
from pathlib import Path

from scripts.parsers.linkedin_zip import parse_linkedin_export

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURE_ZIP = PROJECT_ROOT / "docs" / "testing" / "fixtures" / "synthetic_linkedin_export.zip"


def test_linkedin_workflow_deterministic_pipeline():
    result = parse_linkedin_export(FIXTURE_ZIP)
    # Profile data extracted
    assert result["profile"].get("First Name") == "Alex"
    # Positions extracted
    assert len(result["positions"]) >= 1
    # Skills extracted
    assert "Python" in result["skills"]
    # Safeguarding: third-party PII files skipped
    assert "Connections.csv" in result["skipped_files"]
    assert "messages.csv" in result["skipped_files"]
    assert "Invitations.csv" in result["skipped_files"]
