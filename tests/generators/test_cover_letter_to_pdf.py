"""Tests for the cover-letter PDF generator."""
from pathlib import Path

import pdfplumber
import pytest

from scripts.generators.cover_letter_to_pdf import render_cover_letter_pdf


SAMPLE_LETTER_DATA = {
    "candidate_name": "Alex Test",
    "candidate_contact_line": "alex.test@example.invalid | Sample City",
    "letter_date": "12 May 2026",
    "recipient_name": "Hiring Manager",
    "recipient_title": "",
    "recipient_company": "Example Corp",
    "salutation": "Hiring Team",
    "hook_paragraph": "I am writing about the Senior Engineer role at Example Corp.",
    "fit_paragraph": "Eight years in distributed systems; measurable delivery.",
    "close_paragraph": "Happy to discuss further.",
}


def test_renders_pdf(tmp_path):
    out = tmp_path / "letter.pdf"
    render_cover_letter_pdf(SAMPLE_LETTER_DATA, out)
    assert out.exists()


def test_pdf_contains_expected_content(tmp_path):
    out = tmp_path / "letter.pdf"
    render_cover_letter_pdf(SAMPLE_LETTER_DATA, out)
    with pdfplumber.open(out) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    assert "Alex Test" in text
    assert "Example Corp" in text
    assert "Sincerely" in text


def test_pdf_contains_no_brains_branding(tmp_path):
    out = tmp_path / "letter.pdf"
    render_cover_letter_pdf(SAMPLE_LETTER_DATA, out)
    with pdfplumber.open(out) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    forbidden = ("BRAINS", "Built by neurodivergent minds, for neurodivergent people.",
                 "AI that works for every mind.", "BRAINS Trust", "BRAINS Incubator")
    for phrase in forbidden:
        assert phrase not in text, f"Brand leak: {phrase}"


def test_pdf_accepts_template_argument(tmp_path):
    out = tmp_path / "cover_letter.pdf"
    render_cover_letter_pdf(SAMPLE_LETTER_DATA, out, template="formal-business")
    assert out.exists()


def test_pdf_unknown_template_raises_value_error(tmp_path):
    out = tmp_path / "cover_letter.pdf"
    with pytest.raises(ValueError) as exc_info:
        render_cover_letter_pdf(SAMPLE_LETTER_DATA, out, template="nonexistent")
    assert "nonexistent" in str(exc_info.value)


def test_pdf_default_template_unchanged(tmp_path):
    out_default = tmp_path / "default.pdf"
    out_explicit = tmp_path / "explicit.pdf"
    render_cover_letter_pdf(SAMPLE_LETTER_DATA, out_default)
    render_cover_letter_pdf(SAMPLE_LETTER_DATA, out_explicit, template="formal-business")
    assert out_default.exists()
    assert out_explicit.exists()


def test_pdf_modern_clean_template_renders(tmp_path):
    out = tmp_path / "modern.pdf"
    render_cover_letter_pdf(SAMPLE_LETTER_DATA, out, template="modern-clean")
    assert out.exists()
    assert out.stat().st_size > 0
