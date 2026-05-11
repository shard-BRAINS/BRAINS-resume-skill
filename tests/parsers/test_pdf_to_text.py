"""Tests for the PDF resume parser."""
from pathlib import Path
import pytest

from scripts.parsers.pdf_to_text import parse_pdf_resume

FIXTURE = Path(__file__).parent.parent.parent / "docs" / "testing" / "fixtures" / "synthetic_resume_basic.pdf"


def test_parser_returns_dict_with_required_keys():
    result = parse_pdf_resume(FIXTURE)
    assert isinstance(result, dict)
    for key in ("raw_text", "sections", "page_count"):
        assert key in result, f"Missing key: {key}"


def test_parser_extracts_known_content():
    result = parse_pdf_resume(FIXTURE)
    assert "Alex Test" in result["raw_text"]
    assert "Software engineer" in result["raw_text"]
    assert "Example Corp" in result["raw_text"]


def test_parser_detects_summary_section():
    result = parse_pdf_resume(FIXTURE)
    assert "summary" in [s.lower() for s in result["sections"].keys()]


def test_parser_detects_experience_section():
    result = parse_pdf_resume(FIXTURE)
    assert "experience" in [s.lower() for s in result["sections"].keys()]


def test_parser_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        parse_pdf_resume(Path("does_not_exist.pdf"))
