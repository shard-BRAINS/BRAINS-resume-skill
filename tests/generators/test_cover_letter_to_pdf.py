"""Tests for the cover-letter PDF generator."""
from pathlib import Path
import pdfplumber

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
