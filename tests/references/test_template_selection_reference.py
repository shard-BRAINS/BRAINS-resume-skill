"""Structural tests for references/template-selection.md.

Verifies that the reference includes all four resume templates and both
cover-letter templates, the decision tree exists, and the ND-framing
section contains both pro and con language for the functional template.
"""
from pathlib import Path

REFERENCE = Path(__file__).parent.parent.parent / "references" / "template-selection.md"


def _text():
    return REFERENCE.read_text(encoding="utf-8")


def test_reference_exists():
    assert REFERENCE.exists()


def test_all_four_resume_templates_named():
    text = _text()
    for name in ("chronological", "functional", "hybrid", "executive"):
        assert f"`{name}`" in text, f"Template name not surfaced: {name}"


def test_both_cover_letter_templates_named():
    text = _text()
    for name in ("formal-business", "modern-clean"):
        assert f"`{name}`" in text, f"Cover-letter template name not surfaced: {name}"


def test_decision_tree_section_exists():
    text = _text()
    assert "Decision tree" in text
    # All four leading questions should appear
    for q in ("Q1", "Q2", "Q3", "Q4"):
        assert q in text


def test_nd_framing_section_present_with_both_pro_and_con_language():
    """ND framing must surface BOTH the genuine usefulness of the functional
    template AND the recruiter-skepticism tradeoff — never one-sided."""
    text = _text()
    assert "ND framing" in text or "functional-template tradeoff" in text
    assert "genuinely useful" in text.lower()  # pro language
    assert "hiding something" in text.lower()  # con language
    assert "hybrid" in text.lower()  # middle path explicitly named


def test_worked_examples_present():
    text = _text()
    assert "Example 1" in text
    assert "Example 2" in text
    assert "Example 3" in text


WORKFLOWS_THAT_MUST_CROSS_REFERENCE = (
    "create.md",
    "edit.md",
    "tailor.md",
    "cover-letter.md",
)


def test_workflow_files_cross_reference_template_selection():
    workflows_dir = REFERENCE.parent / "workflows"
    for fname in WORKFLOWS_THAT_MUST_CROSS_REFERENCE:
        text = (workflows_dir / fname).read_text(encoding="utf-8")
        assert "template-selection.md" in text, (
            f"{fname} does not cross-reference references/template-selection.md"
        )
