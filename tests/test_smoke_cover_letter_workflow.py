"""Smoke test for the deterministic portion of the cover-letter workflow."""
from pathlib import Path

import pdfplumber

from scripts.validators.bias_scan import bias_scan
from scripts.validators.integrity_check import integrity_check
from scripts.generators.cover_letter_to_docx import render_cover_letter_docx
from scripts.generators.cover_letter_to_pdf import render_cover_letter_pdf


def test_cover_letter_workflow_deterministic_pipeline(tmp_path):
    letter = {
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
    text_blob = " ".join(str(v) for v in letter.values())
    bias_scan(text_blob)
    integrity_check(text_blob)

    out_docx = tmp_path / "letter.docx"
    out_pdf = tmp_path / "letter.pdf"
    render_cover_letter_docx(letter, out_docx)
    render_cover_letter_pdf(letter, out_pdf)

    assert out_docx.exists()
    assert out_pdf.exists()

    # Verify cover letter PDF is unbranded
    with pdfplumber.open(out_pdf) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    assert "BRAINS" not in text
    assert "Built by neurodivergent minds" not in text
