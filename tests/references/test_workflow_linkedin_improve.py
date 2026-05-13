"""Structural tests for references/workflows/linkedin-improve.md."""
from pathlib import Path

REFERENCE = Path(__file__).parent.parent.parent / "references" / "workflows" / "linkedin-improve.md"


def _text():
    return REFERENCE.read_text(encoding="utf-8")


def test_reference_exists():
    assert REFERENCE.exists()


def test_linkedin_character_limits_documented():
    text = _text()
    assert "220" in text  # Headline limit
    assert "2,600" in text or "2600" in text  # About limit
    assert "2,000" in text or "2000" in text  # Experience entry limit


def test_three_paragraph_about_structure_documented():
    text = _text()
    assert "Hook" in text
    assert "Proof" in text
    assert "CTA" in text


def test_reference_documents_validator_use():
    text = _text()
    assert "bias_scan" in text
    assert "integrity_check" in text


def test_safeguarding_section_present():
    text = _text()
    assert "Safeguarding boundaries" in text
    lower_text = text.lower()
    assert "no linkedin api write access" in lower_text
