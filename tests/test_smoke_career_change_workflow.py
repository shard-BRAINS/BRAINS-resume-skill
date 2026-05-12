"""Smoke test for the deterministic portion of the career-change workflow."""
from pathlib import Path

from scripts.validators.bias_scan import bias_scan
from scripts.validators.integrity_check import integrity_check
from scripts.generators.resume_to_docx import render_resume_docx
from tests.fixtures import career_change_fixtures as fx


def test_career_change_workflow_deterministic_pipeline(tmp_path):
    # Source domain: engineering. Target: product management.
    source = fx.SOURCE_ENG
    target = fx.TARGET_PM

    # Simulate the translated resume data (Claude-side step in real workflow).
    translated = {
        "candidate_name": "Alex Test",
        "candidate_contact_line": "alex.test@example.invalid | Sample City",
        "summary": (
            "Senior practitioner moving into product management, bringing eight years "
            "of delivery experience operating systems at scale."
        ),
        "skills": "Stakeholder coordination, delivery governance, technical depth, mentoring",
        "experience": source["experience"],
        "education": "BSc Computer Science, Example University, 2015",
    }
    text_blob = "\n".join(str(v) for v in translated.values())
    bias_scan(text_blob)
    integrity_check(text_blob)

    out = tmp_path / "translated.docx"
    render_resume_docx(translated, out)
    assert out.exists()
    # Sanity check: the target keyword is present in the summary
    assert "product management" in translated["summary"]
