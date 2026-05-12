"""Tests for the cover-letter DOCX generator."""
from pathlib import Path

from scripts.generators.cover_letter_to_docx import render_cover_letter_docx
from scripts.validators.ats_check import ats_check


SAMPLE_LETTER_DATA = {
    "candidate_name": "Alex Test",
    "candidate_contact_line": "alex.test@example.invalid | Sample City",
    "letter_date": "12 May 2026",
    "recipient_name": "Hiring Manager",
    "recipient_title": "",
    "recipient_company": "Example Corp",
    "salutation": "Hiring Team",
    "hook_paragraph": "I am writing to express my interest in the Senior Engineer role at Example Corp.",
    "fit_paragraph": "With eight years of experience in distributed systems, I bring proven delivery against measurable outcomes.",
    "close_paragraph": "I would welcome the chance to discuss how my background aligns with your team's goals.",
}


def test_render_writes_docx(tmp_path):
    out = tmp_path / "cover_letter.docx"
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out)
    assert out.exists()


def test_rendered_docx_contains_expected_content(tmp_path):
    out = tmp_path / "cover_letter.docx"
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out)
    from docx import Document
    doc = Document(str(out))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Alex Test" in text
    assert "Example Corp" in text
    assert "Senior Engineer" in text
    assert "Sincerely" in text


def test_rendered_docx_has_no_unfilled_placeholders(tmp_path):
    out = tmp_path / "cover_letter.docx"
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out)
    from docx import Document
    doc = Document(str(out))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "{{" not in text


def test_rendered_docx_passes_ats_check(tmp_path):
    out = tmp_path / "cover_letter.docx"
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out)
    result = ats_check(out)
    assert result.passed
