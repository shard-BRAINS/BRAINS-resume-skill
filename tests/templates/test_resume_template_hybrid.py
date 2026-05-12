"""Validate the hybrid resume template is ATS-safe."""
from pathlib import Path

from scripts.validators.ats_check import ats_check

TEMPLATE = Path(__file__).parent.parent.parent / "templates" / "resume" / "hybrid.docx"


def test_template_exists():
    assert TEMPLATE.exists(), f"Template missing: {TEMPLATE}"


def test_template_passes_ats_check():
    result = ats_check(TEMPLATE)
    assert result.passed, f"Failures: {[f.code for f in result.failures]}"


def test_template_has_key_skills_heading_before_experience():
    """Hybrid layout puts Key Skills before Experience."""
    from docx import Document
    doc = Document(str(TEMPLATE))
    flat = "\n".join(p.text for p in doc.paragraphs)
    skills_pos = flat.find("Key Skills")
    experience_pos = flat.find("Experience")
    assert 0 <= skills_pos < experience_pos
