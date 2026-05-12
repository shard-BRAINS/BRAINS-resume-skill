"""Tests for the cover-letter DOCX generator."""
from pathlib import Path

import pytest

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


def test_render_accepts_template_argument(tmp_path):
    out = tmp_path / "cover_letter.docx"
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out, template="formal-business")
    assert out.exists()


def test_unknown_template_raises_value_error(tmp_path):
    out = tmp_path / "cover_letter.docx"
    with pytest.raises(ValueError) as exc_info:
        render_cover_letter_docx(SAMPLE_LETTER_DATA, out, template="nonexistent")
    assert "nonexistent" in str(exc_info.value)
    assert "formal-business" in str(exc_info.value)


def test_default_template_unchanged_behaviour(tmp_path):
    out_default = tmp_path / "default.docx"
    out_explicit = tmp_path / "explicit.docx"
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out_default)
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out_explicit, template="formal-business")
    from docx import Document
    text_d = "\n".join(p.text for p in Document(str(out_default)).paragraphs)
    text_e = "\n".join(p.text for p in Document(str(out_explicit)).paragraphs)
    assert text_d == text_e  # byte-equivalent rendering for the same data
