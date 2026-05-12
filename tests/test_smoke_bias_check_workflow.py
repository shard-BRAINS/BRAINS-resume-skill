"""Smoke test for the deterministic portion of the bias-aware ATS check workflow."""
from pathlib import Path

from scripts.parsers.docx_to_text import parse_docx_resume
from scripts.validators.ats_check import ats_check
from scripts.validators.bias_scan import bias_scan
from scripts.validators.integrity_check import integrity_check
from scripts.generators.coaching_report_to_pdf import render_from_markdown

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURE_DOCX = PROJECT_ROOT / "docs" / "testing" / "fixtures" / "synthetic_resume_basic.docx"
BRAND_MARK = PROJECT_ROOT / "assets" / "brains-mark-light-bg.png"


def test_bias_check_workflow_deterministic_pipeline(tmp_path):
    parsed = parse_docx_resume(FIXTURE_DOCX)
    assert parsed["raw_text"]

    ats = ats_check(FIXTURE_DOCX)
    bias = bias_scan(parsed["raw_text"])
    integrity = integrity_check(parsed["raw_text"])

    # Compose the pre-submit-check report markdown
    md = tmp_path / "pre-submit-check.md"
    md.write_text(
        "# Pre-Submit Check Report\n\n"
        "**Prepared:** 2026-05-12\n"
        "**Resume reviewed:** synthetic_resume_basic.docx\n"
        "**Reviewer:** BRAINS Resume Skill (v1.0.0)\n\n"
        "---\n\n"
        "## Summary\n\n"
        f"ATS pass: {ats.passed}. Bias findings: {len(bias.findings)}. "
        f"Integrity findings: {len(integrity.findings)}.\n\n"
        "## ATS-safety findings\n\n"
        f"**Status:** {'PASS' if ats.passed else 'FAIL'}\n\n"
        "No critical structural issues detected in this fixture.\n\n"
        "## ND-bias findings\n\n"
        f"{len(bias.findings)} pattern hits.\n\n"
        "## Recommended next steps\n\n"
        "Synthetic fixture; no real submission to prepare.\n",
        encoding="utf-8",
    )

    out_pdf = tmp_path / "pre-submit-check.pdf"
    render_from_markdown(
        md_path=md,
        out_path=out_pdf,
        brand_mark_path=BRAND_MARK,
        include_trust_footer=False,
    )
    assert out_pdf.exists()
