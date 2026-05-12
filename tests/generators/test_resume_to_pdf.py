"""Tests for the resume PDF generator."""
from pathlib import Path
import pdfplumber

from scripts.generators.resume_to_pdf import render_resume_pdf


SAMPLE_RESUME_DATA = {
    "candidate_name": "Alex Test",
    "candidate_contact_line": "alex.test@example.invalid | Sample City",
    "summary": "Senior engineer with eight years of experience building data systems.",
    "skills": "Python, distributed systems, observability, mentoring",
    "experience": (
        "Senior Engineer, Example Corp 2020 - Present\n"
        "Built ingestion pipeline processing 50M events daily."
    ),
    "education": "BSc Computer Science, Example University, 2015",
}


def test_render_writes_pdf(tmp_path):
    out = tmp_path / "resume.pdf"
    render_resume_pdf(SAMPLE_RESUME_DATA, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_pdf_contains_provided_content(tmp_path):
    out = tmp_path / "resume.pdf"
    render_resume_pdf(SAMPLE_RESUME_DATA, out)
    with pdfplumber.open(out) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    assert "Alex Test" in text
    assert "Senior engineer" in text
    assert "Example Corp" in text


def test_pdf_contains_no_brains_branding(tmp_path):
    """The user-submission resume PDF must be UNBRANDED."""
    out = tmp_path / "resume.pdf"
    render_resume_pdf(SAMPLE_RESUME_DATA, out)
    with pdfplumber.open(out) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    forbidden = (
        "BRAINS",
        "Built by neurodivergent minds, for neurodivergent people.",
        "AI that works for every mind.",
        "BRAINS Trust",
        "BRAINS Incubator",
    )
    for phrase in forbidden:
        assert phrase not in text, f"Brand leak detected: {phrase!r} in resume PDF"
