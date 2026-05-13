"""Tests for scripts/validators/jd_analyzer.py — the JD finding catalog."""
from scripts.validators.jd_analyzer import jd_analyze
from tests.fixtures import jd_analyzer_fixtures as fx


def _codes(result):
    return [f.code for f in result.findings]


def test_red_flag_heavy_jd_produces_soft_culture_finding():
    r = jd_analyze(fx.RED_FLAG_HEAVY_JD)
    assert "JD_RED_FLAG_SOFT_CULTURE" in _codes(r)


def test_red_flag_heavy_jd_high_severity_cluster():
    """Multiple red-flag hits should produce HIGH severity (3+ hits)."""
    r = jd_analyze(fx.RED_FLAG_HEAVY_JD)
    rf_findings = [f for f in r.findings if f.code == "JD_RED_FLAG_SOFT_CULTURE"]
    assert any(f.severity == "HIGH" for f in rf_findings)


def test_masking_cost_heavy_jd_produces_finding():
    r = jd_analyze(fx.MASKING_COST_HEAVY_JD)
    assert "JD_MASKING_COST" in _codes(r)


def test_evidence_of_flex_heavy_jd_produces_finding():
    r = jd_analyze(fx.EVIDENCE_OF_FLEX_HEAVY_JD)
    assert "JD_EVIDENCE_OF_FLEX" in _codes(r)


def test_clean_neutral_jd_has_no_red_flags_or_masking_cost():
    r = jd_analyze(fx.CLEAN_NEUTRAL_JD)
    codes = _codes(r)
    assert "JD_RED_FLAG_SOFT_CULTURE" not in codes
    assert "JD_MASKING_COST" not in codes


def test_finding_carries_excerpt_and_suggestion():
    r = jd_analyze(fx.RED_FLAG_HEAVY_JD)
    finding = r.findings[0]
    assert hasattr(finding, "code")
    assert hasattr(finding, "severity")
    assert hasattr(finding, "excerpt")
    assert hasattr(finding, "suggestion")
    assert finding.severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "POSITIVE")


def test_mixed_jd_produces_some_of_each():
    """The mixed JD should show both a soft-culture hit (passionate, fast-paced)
    and an evidence-of-flex hit (async, hybrid policy)."""
    r = jd_analyze(fx.MIXED_JD)
    codes = _codes(r)
    assert "JD_RED_FLAG_SOFT_CULTURE" in codes
    assert "JD_EVIDENCE_OF_FLEX" in codes
