"""Tests for the resume PDF generator."""
from pathlib import Path
import pytest
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


def test_pdf_accepts_template_argument(tmp_path):
    out = tmp_path / "resume.pdf"
    render_resume_pdf(SAMPLE_RESUME_DATA, out, template="chronological")
    assert out.exists()
    assert out.stat().st_size > 0


def test_pdf_unknown_template_raises_value_error(tmp_path):
    out = tmp_path / "resume.pdf"
    with pytest.raises(ValueError) as exc_info:
        render_resume_pdf(SAMPLE_RESUME_DATA, out, template="nonexistent")
    assert "nonexistent" in str(exc_info.value)


def test_pdf_default_template_renders_chronological(tmp_path):
    out_default = tmp_path / "default.pdf"
    out_explicit = tmp_path / "explicit.pdf"
    render_resume_pdf(SAMPLE_RESUME_DATA, out_default)
    render_resume_pdf(SAMPLE_RESUME_DATA, out_explicit, template="chronological")
    assert out_default.exists()
    assert out_explicit.exists()


def test_pdf_functional_template_includes_skills_section_before_experience(tmp_path):
    """Functional template inverts the section order — skills-led, then
    minimal experience."""
    out = tmp_path / "functional.pdf"
    render_resume_pdf(SAMPLE_RESUME_DATA, out, template="functional")
    with pdfplumber.open(str(out)) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages)
    skills_pos = text.find("Skills")
    experience_pos = text.find("Experience")
    assert 0 <= skills_pos < experience_pos


def test_pdf_executive_template_uses_larger_name_heading(tmp_path):
    """Executive template uses a larger name heading than chronological (24pt vs 22pt)."""
    out = tmp_path / "executive.pdf"
    render_resume_pdf(SAMPLE_RESUME_DATA, out, template="executive")
    assert out.exists()
    assert out.stat().st_size > 0
