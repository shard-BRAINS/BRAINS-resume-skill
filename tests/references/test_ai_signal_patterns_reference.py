"""Structural tests for references/ai-signal-patterns.md."""
from pathlib import Path

REFERENCE = Path(__file__).parent.parent.parent / "references" / "ai-signal-patterns.md"


def _text():
    return REFERENCE.read_text(encoding="utf-8")


def test_reference_exists():
    assert REFERENCE.exists()


def test_all_nine_finding_codes_documented():
    text = _text()
    for code in (
        "AI_EMDASH_OVERUSE",
        "AI_OVERUSED_VOCAB",
        "AI_TRICOLON_OVERUSE",
        "AI_RHETORICAL_CONTRAST",
        "AI_TRANSITIONAL_OVERUSE",
        "AI_PRESENT_PARTICIPLE_PILEUP",
        "AI_HEDGING_PHRASE",
        "AI_RANGE_QUANTIFIER",
        "AI_WHETHER_DISJUNCTION",
    ):
        assert code in text, f"Finding code not documented: {code}"


def test_severity_weights_documented():
    text = _text()
    assert "HIGH" in text
    assert "MEDIUM" in text
    assert "LOW" in text
    assert "20" in text  # HIGH weight
    assert "10" in text  # MEDIUM weight


def test_score_anchor_points_present():
    text = _text()
    for anchor in ("0-9", "10-29", "30-49", "50-79", "80-100"):
        assert anchor in text


def test_lower_is_better_explicit():
    text = _text().lower()
    assert "lower is better" in text
