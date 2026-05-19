"""Tests for the cover-letter DOCX generator."""
from pathlib import Path

import pytest

from scripts.generators.cover_letter_to_docx import render_cover_letter_docx
from scripts.outputs.tagging import ArtifactMeta, read_artifact_meta
from scripts.validators.ats_check import ats_check


SAMPLE_LETTER_DATA = {
    "candidate_name": "Alex Test",
    "candidate_contact_line": "alex.test@example.invalid | Sample City",
    "letter_date": "12 May 2026",
    "recipient_name": "Hiring Manager",
    "recipient_title": "",
    "recipient_company": "Example Corp",
    "salutation": "Hiring Team",
    "hook_paragraph": "I am writing to express my interest in the Senior Engineer role at Example Corp.",
    "fit_paragraph": "With eight years of experience in distributed systems, I bring proven delivery against measurable outcomes.",
    "close_paragraph": "I would welcome the chance to discuss how my background aligns with your team's goals.",
}


def test_render_writes_docx(tmp_path):
    out = tmp_path / "cover_letter.docx"
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out)
    assert out.exists()


def test_rendered_docx_contains_expected_content(tmp_path):
    out = tmp_path / "cover_letter.docx"
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out)
    from docx import Document
    doc = Document(str(out))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Alex Test" in text
    assert "Example Corp" in text
    assert "Senior Engineer" in text
    assert "Sincerely" in text


def test_rendered_docx_has_no_unfilled_placeholders(tmp_path):
    out = tmp_path / "cover_letter.docx"
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out)
    from docx import Document
    doc = Document(str(out))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "{{" not in text


def test_rendered_docx_passes_ats_check(tmp_path):
    out = tmp_path / "cover_letter.docx"
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out)
    result = ats_check(out)
    assert result.passed


def test_render_accepts_template_argument(tmp_path):
    out = tmp_path / "cover_letter.docx"
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out, template="formal-business")
    assert out.exists()


def test_unknown_template_raises_value_error(tmp_path):
    out = tmp_path / "cover_letter.docx"
    with pytest.raises(ValueError) as exc_info:
        render_cover_letter_docx(SAMPLE_LETTER_DATA, out, template="nonexistent")
    assert "nonexistent" in str(exc_info.value)
    assert "formal-business" in str(exc_info.value)


def test_default_template_unchanged_behaviour(tmp_path):
    out_default = tmp_path / "default.docx"
    out_explicit = tmp_path / "explicit.docx"
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out_default)
    render_cover_letter_docx(SAMPLE_LETTER_DATA, out_explicit, template="formal-business")
    from docx import Document
    text_d = "\n".join(p.text for p in Document(str(out_default)).paragraphs)
    text_e = "\n".join(p.text for p in Document(str(out_explicit)).paragraphs)
    assert text_d == text_e  # byte-equivalent rendering for the same data


def test_render_cover_letter_docx_with_meta(tmp_path):
    """With artifact_meta provided, custom properties are embedded in the DOCX."""
    out = tmp_path / "cl.docx"
    meta = ArtifactMeta(
        artifact_uid="H8VR3W",
        artifact_kind="cover-letter",
        jd_id=42,
        parent_uid="KX7M9Q",
        created_at="2026-05-19T10:00:00Z",
        skill_version="1.5.0",
    )
    render_cover_letter_docx(
        data={"candidate_name": "M Gell", "body": "Dear hiring manager"},
        out_path=out,
        template="formal-business",
        artifact_meta=meta,
    )
    loaded = read_artifact_meta(out)
    assert loaded == meta
