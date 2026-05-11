"""Tests for the DOCX resume parser."""
from pathlib import Path
import pytest

from scripts.parsers.docx_to_text import parse_docx_resume

FIXTURE = Path(__file__).parent.parent.parent / "docs" / "testing" / "fixtures" / "synthetic_resume_basic.docx"


def test_parser_returns_dict_with_required_keys():
    result = parse_docx_resume(FIXTURE)
    assert isinstance(result, dict)
    for key in ("raw_text", "sections", "paragraph_count"):
        assert key in result


def test_parser_extracts_known_content():
    result = parse_docx_resume(FIXTURE)
    assert "Alex Test" in result["raw_text"]
    assert "Software engineer" in result["raw_text"]


def test_parser_detects_summary_and_experience_sections():
    result = parse_docx_resume(FIXTURE)
    keys_lower = [k.lower() for k in result["sections"].keys()]
    assert "summary" in keys_lower
    assert "experience" in keys_lower


def test_parser_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        parse_docx_resume(Path("does_not_exist.docx"))
