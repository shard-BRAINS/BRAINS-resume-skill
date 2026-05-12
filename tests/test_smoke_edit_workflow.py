"""Smoke test for the deterministic portion of the edit workflow."""
from pathlib import Path

import pdfplumber

from scripts.parsers.docx_to_text import parse_docx_resume
from scripts.validators.ats_check import ats_check
from scripts.validators.bias_scan import bias_scan
from scripts.validators.integrity_check import integrity_check
from scripts.generators.resume_to_docx import render_resume_docx
from scripts.generators.resume_to_pdf import render_resume_pdf

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURE_DOCX = PROJECT_ROOT / "docs" / "testing" / "fixtures" / "synthetic_resume_basic.docx"


def test_edit_workflow_deterministic_pipeline(tmp_path):
    parsed = parse_docx_resume(FIXTURE_DOCX)
    assert parsed["raw_text"]

    ats = ats_check(FIXTURE_DOCX)
    bias = bias_scan(parsed["raw_text"])
    integrity = integrity_check(parsed["raw_text"])

    data = {
        "candidate_name": "Alex Test",
        "candidate_contact_line": "alex.test@example.invalid | Sample City",
        "summary": "Senior engineer with eight years of experience building data systems.",
        "skills": "Python, distributed systems, observability, mentoring",
        "experience": "Senior Engineer, Example Corp 2020 - Present\nBuilt ingestion pipeline.",
        "education": "BSc Computer Science, Example University, 2015",
    }

    out_docx = tmp_path / "resume.docx"
    out_pdf = tmp_path / "resume.pdf"
    render_resume_docx(data, out_docx)
    render_resume_pdf(data, out_pdf)

    assert out_docx.exists()
    assert out_pdf.exists()
    assert ats_check(out_docx).passed

    with pdfplumber.open(out_pdf) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    assert "BRAINS" not in text
