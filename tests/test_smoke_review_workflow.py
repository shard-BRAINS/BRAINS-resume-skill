"""Smoke test for the deterministic portion of the resume-review workflow.

This test verifies that the parsers, validators, and coaching-report generator
compose end-to-end without errors. It does not test the contextual Claude review
portions (patterns 3, 4, 5, 8, 9) — those need a live model.
"""
from pathlib import Path

import pdfplumber

from scripts.parsers.docx_to_text import parse_docx_resume
from scripts.validators.ats_check import ats_check
from scripts.validators.bias_scan import bias_scan
from scripts.generators.coaching_report_to_pdf import render_coaching_report_pdf

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURE_DOCX = PROJECT_ROOT / "docs" / "testing" / "fixtures" / "synthetic_resume_basic.docx"
BRAND_MARK = PROJECT_ROOT / "assets" / "brains-mark-light-bg.png"


def test_review_workflow_runs_end_to_end(tmp_path):
    # Parse the resume.
    parsed = parse_docx_resume(FIXTURE_DOCX)
    assert parsed["raw_text"], "Parser returned empty text"

    # Run validators.
    ats = ats_check(FIXTURE_DOCX)
    bias = bias_scan(parsed["raw_text"])

    # Compose findings text.
    ats_status = "PASS" if ats.passed else "FAIL"
    ats_findings = (
        "No issues detected."
        if not (ats.failures or ats.warnings)
        else "\n".join(f"- {f.code}: {f.message}" for f in ats.failures + ats.warnings)
    )
    bias_findings = (
        "No patterns detected."
        if not bias.findings
        else "\n".join(f"- {f.pattern_code}: {f.suggestion}" for f in bias.findings)
    )

    # Render the report.
    out = tmp_path / "smoke_review.pdf"
    render_coaching_report_pdf(
        out_path=out,
        title="Resume Coaching Report",
        resume_filename=FIXTURE_DOCX.name,
        skill_version="0.1.0",
        executive_summary="Smoke-test summary.",
        ats_status=ats_status,
        ats_findings=ats_findings,
        bias_findings=bias_findings,
        next_steps="- (smoke test placeholder)",
        include_trust_footer=False,
        brand_mark_path=BRAND_MARK,
    )

    # Verify the PDF was written and contains expected branded content.
    assert out.exists()
    with pdfplumber.open(out) as pdf:
        all_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    assert "Built by neurodivergent minds, for neurodivergent people." in all_text
    assert "Resume Coaching Report" in all_text
