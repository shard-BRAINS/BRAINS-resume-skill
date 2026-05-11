"""Tests for the ND-bias deterministic scanner.

Every one of the 10 patterns in references/nd-bias-patterns.md must be detectable
either as a confident hit (patterns 1, 2, 6, 7, 10) or as a 'needs-review' flag
(patterns 3, 4, 5, 8, 9).
"""
from scripts.validators.bias_scan import bias_scan
from tests.fixtures import bias_fixtures as fx


def _pattern_codes(result):
    return [f.pattern_code for f in result.findings]


def test_pattern_1_soft_skills_coded_vocabulary():
    result = bias_scan(fx.PATTERN_1_SOFT_SKILLS)
    assert "ND_BIAS_P1_SOFT_SKILLS" in _pattern_codes(result)


def test_pattern_2_gap_explanation_on_resume():
    result = bias_scan(fx.PATTERN_2_GAP_EXPLANATION)
    assert "ND_BIAS_P2_GAP_EXPLANATION" in _pattern_codes(result)


def test_pattern_3_short_tenures_flagged_for_review():
    result = bias_scan(fx.PATTERN_3_SHORT_TENURES)
    assert "ND_BIAS_P3_SHORT_TENURES_REVIEW" in _pattern_codes(result)


def test_pattern_4_hyperfocus_flagged_for_review():
    result = bias_scan(fx.PATTERN_4_HYPERFOCUS)
    assert "ND_BIAS_P4_HYPERFOCUS_REVIEW" in _pattern_codes(result)


def test_pattern_5_under_claim_flagged_for_review():
    result = bias_scan(fx.PATTERN_5_UNDER_CLAIM)
    assert "ND_BIAS_P5_UNDER_CLAIM_REVIEW" in _pattern_codes(result)


def test_pattern_6_direct_nd_signal_terms():
    result = bias_scan(fx.PATTERN_6_DIRECT_ND)
    assert "ND_BIAS_P6_DIRECT_SIGNAL" in _pattern_codes(result)


def test_pattern_7_indirect_nd_signal_terms():
    result = bias_scan(fx.PATTERN_7_INDIRECT_ND)
    assert "ND_BIAS_P7_INDIRECT_SIGNAL" in _pattern_codes(result)


def test_pattern_8_no_warmth_flagged_for_review():
    result = bias_scan(fx.PATTERN_8_NO_WARMTH)
    assert "ND_BIAS_P8_NO_WARMTH_REVIEW" in _pattern_codes(result)


def test_pattern_9_over_precision_flagged_for_review():
    result = bias_scan(fx.PATTERN_9_OVER_PRECISION)
    assert "ND_BIAS_P9_OVER_PRECISION_REVIEW" in _pattern_codes(result)


def test_pattern_10_mixed_identity_language():
    result = bias_scan(fx.PATTERN_10_MIXED_IDENTITY)
    assert "ND_BIAS_P10_MIXED_IDENTITY" in _pattern_codes(result)


def test_clean_text_returns_no_findings():
    clean = (
        "Software engineer with eight years of experience. Built ingestion pipeline "
        "processing 50 million events daily. Reduced query latency 40 percent."
    )
    result = bias_scan(clean)
    confident = [f for f in result.findings if not f.pattern_code.endswith("_REVIEW")]
    assert confident == []
