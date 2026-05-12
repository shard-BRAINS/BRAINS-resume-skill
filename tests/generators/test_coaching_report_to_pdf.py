"""Tests for the branded coaching-report PDF generator."""
from pathlib import Path
import pdfplumber
import pytest

from scripts.generators.coaching_report_to_pdf import render_coaching_report_pdf


def test_renders_pdf_with_provided_content(tmp_path):
    out = tmp_path / "report.pdf"
    render_coaching_report_pdf(
        out_path=out,
        title="Resume Coaching Report",
        resume_filename="alex_test_resume.docx",
        skill_version="0.1.0",
        executive_summary="Three items to address before submission.",
        ats_status="WARN",
        ats_findings="- Header contains contact info.",
        bias_findings="- Pattern 1: soft-skills vocabulary detected.",
        next_steps="- Move contact details into the body.",
        include_trust_footer=False,
        brand_mark_path=Path("assets") / "brains-mark-light-bg.png",
    )
    assert out.exists()
    assert out.stat().st_size > 0


def test_pdf_contains_expected_text(tmp_path):
    out = tmp_path / "report.pdf"
    render_coaching_report_pdf(
        out_path=out,
        title="Resume Coaching Report",
        resume_filename="alex_test_resume.docx",
        skill_version="0.1.0",
        executive_summary="Summary marker XYZ123.",
        ats_status="PASS",
        ats_findings="No issues detected.",
        bias_findings="No patterns detected.",
        next_steps="Resume is in good shape.",
        include_trust_footer=False,
        brand_mark_path=Path("assets") / "brains-mark-light-bg.png",
    )
    with pdfplumber.open(out) as pdf:
        all_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    assert "Resume Coaching Report" in all_text
    assert "Summary marker XYZ123" in all_text
    assert "Built by neurodivergent minds, for neurodivergent people." in all_text


def test_pdf_includes_trust_footer_when_requested(tmp_path):
    out = tmp_path / "report.pdf"
    render_coaching_report_pdf(
        out_path=out,
        title="Disclosure Worksheet",
        resume_filename="n/a",
        skill_version="0.1.0",
        executive_summary="Summary.",
        ats_status="N/A",
        ats_findings="N/A",
        bias_findings="N/A",
        next_steps="N/A",
        include_trust_footer=True,
        brand_mark_path=Path("assets") / "brains-mark-light-bg.png",
    )
    with pdfplumber.open(out) as pdf:
        all_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    assert "Disclosure guidance developed with BRAINS Trust safeguarding principles." in all_text
