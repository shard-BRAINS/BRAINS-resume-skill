"""Structural tests for references/workflows/consolidate.md."""
from pathlib import Path

REFERENCE = Path(__file__).parent.parent.parent / "references" / "workflows" / "consolidate.md"


def _text():
    return REFERENCE.read_text(encoding="utf-8")


def test_reference_exists():
    assert REFERENCE.exists()


def test_all_five_finding_codes_documented():
    text = _text()
    for code in (
        "CONSOLIDATION_JOB_TITLE_MISMATCH",
        "CONSOLIDATION_DATE_INCONSISTENCY",
        "CONSOLIDATION_ACHIEVEMENT_ONLY_IN_RESUME",
        "CONSOLIDATION_ACHIEVEMENT_ONLY_IN_LINKEDIN",
        "CONSOLIDATION_TONE_DIVERGENCE",
    ):
        assert code in text, f"Finding code not documented: {code}"


def test_three_resolution_tags_documented():
    text = _text()
    for tag in ("RESUME-LEADING", "LINKEDIN-LEADING", "NEW-SYNTHESIS"):
        assert tag in text


def test_tone_divergence_explicitly_flagged_as_heuristic():
    text = _text().lower()
    assert "heuristic" in text
    # Within ~200 chars of the word, "tone" or "register" should also appear.


def test_read_only_handoff_pattern_documented():
    text = _text()
    assert "read-only" in text.lower()
    assert "/brains-edit" in text
    assert "/brains-linkedin-improve" in text
