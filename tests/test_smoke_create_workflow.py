"""Smoke test for the deterministic portion of the create-from-scratch workflow."""
from pathlib import Path

from scripts.validators.bias_scan import bias_scan
from scripts.validators.integrity_check import integrity_check
from scripts.generators.resume_to_docx import render_resume_docx
from scripts.generators.resume_to_pdf import render_resume_pdf


def test_create_workflow_deterministic_pipeline(tmp_path):
    # Simulate the assembled data from an interview.
    data = {
        "candidate_name": "Alex Test",
        "candidate_contact_line": "alex.test@example.invalid | Sample City",
        "summary": "Engineer with eight years of experience in data systems.",
        "skills": "Python, distributed systems, mentoring",
        "experience": "Senior Engineer, Example Corp 2020 - Present\nBuilt ingestion pipeline.",
        "education": "BSc Computer Science, Example University, 2015",
    }

    # Pre-flight validators on the assembled text.
    text_blob = "\n".join(str(v) for v in data.values())
    bias_scan(text_blob)
    integrity_check(text_blob)

    out_docx = tmp_path / "created.docx"
    out_pdf = tmp_path / "created.pdf"
    render_resume_docx(data, out_docx)
    render_resume_pdf(data, out_pdf)

    assert out_docx.exists()
    assert out_pdf.exists()
