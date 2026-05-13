"""Structural tests for references/workflows/pre-application-check.md."""
from pathlib import Path

REFERENCE = Path(__file__).parent.parent.parent / "references" / "workflows" / "pre-application-check.md"


def _text():
    return REFERENCE.read_text(encoding="utf-8")


def test_reference_exists():
    assert REFERENCE.exists()


def test_six_questions_documented():
    text = _text()
    for q in ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6"):
        assert q in text


def test_never_blocks_submission_explicit():
    text = _text().lower()
    assert "never blocks submission" in text or "coaching, not gating" in text


def test_healthy_weekly_rate_is_user_defined():
    text = _text().lower()
    assert "healthy weekly rate is user-defined" in text or "user-defined" in text


def test_fit_or_pressure_recorded_verbatim():
    text = _text().lower()
    assert "verbatim" in text


def test_tracker_integration_documented():
    text = _text()
    assert "add_application" in text
    assert "weekly_summary" in text
    assert "find_duplicates" in text


def test_safeguarding_section_present():
    text = _text()
    assert "Safeguarding boundaries" in text
