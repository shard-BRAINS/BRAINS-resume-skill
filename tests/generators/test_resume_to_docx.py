"""Tests for the resume DOCX generator."""
from pathlib import Path
import pytest

from scripts.generators.resume_to_docx import render_resume_docx
from scripts.validators.ats_check import ats_check


SAMPLE_RESUME_DATA = {
    "candidate_name": "Alex Test",
    "candidate_contact_line": "alex.test@example.invalid | Sample City",
    "summary": "Senior engineer with eight years of experience.",
    "skills": "Python, distributed systems, observability, mentoring",
    "experience": (
        "Senior Engineer, Example Corp 2020 - Present\n"
        "Built ingestion pipeline processing 50M events daily.\n\n"
        "Software Engineer, Sample Industries 2017 - 2019\n"
        "Backend services for an e-commerce platform."
    ),
    "education": "BSc Computer Science, Example University, 2015",
}


def test_render_writes_docx(tmp_path):
    out = tmp_path / "resume.docx"
    render_resume_docx(SAMPLE_RESUME_DATA, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_rendered_docx_contains_provided_content(tmp_path):
    out = tmp_path / "resume.docx"
    render_resume_docx(SAMPLE_RESUME_DATA, out)
    from docx import Document
    doc = Document(str(out))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Alex Test" in text
    assert "Senior engineer" in text
    assert "Example Corp" in text
    assert "BSc Computer Science" in text


def test_rendered_docx_has_no_unfilled_placeholders(tmp_path):
    out = tmp_path / "resume.docx"
    render_resume_docx(SAMPLE_RESUME_DATA, out)
    from docx import Document
    doc = Document(str(out))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "{{" not in text, "Template placeholder leaked into rendered output"


def test_rendered_docx_passes_ats_check(tmp_path):
    out = tmp_path / "resume.docx"
    render_resume_docx(SAMPLE_RESUME_DATA, out)
    result = ats_check(out)
    assert result.passed, f"Failures: {[f.code for f in result.failures]}"


def test_renders_to_user_chosen_directory(tmp_path):
    subdir = tmp_path / "myoutput"
    out = subdir / "resume.docx"
    render_resume_docx(SAMPLE_RESUME_DATA, out)
    assert out.exists()
    assert subdir.exists()
