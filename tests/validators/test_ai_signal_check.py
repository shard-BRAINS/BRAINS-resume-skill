"""Tests for scripts/validators/ai_signal_check.py — the AI-tell detector."""
from scripts.validators.ai_signal_check import ai_signal_check
from tests.fixtures import ai_signal_fixtures as fx


def _codes(result):
    return [f.code for f in result.findings]


# ---- AI_EMDASH_OVERUSE -------------------------------------------------------

def test_emdash_heavy_text_high_severity():
    r = ai_signal_check(fx.EMDASH_HEAVY_TEXT)
    em_findings = [f for f in r.findings if f.code == "AI_EMDASH_OVERUSE"]
    assert em_findings, "Expected AI_EMDASH_OVERUSE finding on heavy fixture"
    assert any(f.severity == "HIGH" for f in em_findings)


def test_emdash_mild_text_no_finding():
    """1 em-dash in 90 words is under-threshold."""
    r = ai_signal_check(fx.EMDASH_MILD_TEXT)
    assert "AI_EMDASH_OVERUSE" not in _codes(r)


# ---- AI_OVERUSED_VOCAB -------------------------------------------------------

def test_overused_vocab_heavy_text_high_severity():
    r = ai_signal_check(fx.OVERUSED_VOCAB_HEAVY_TEXT)
    vocab_findings = [f for f in r.findings if f.code == "AI_OVERUSED_VOCAB"]
    assert vocab_findings
    assert any(f.severity == "HIGH" for f in vocab_findings)


def test_overused_vocab_light_text_medium_severity():
    r = ai_signal_check(fx.OVERUSED_VOCAB_LIGHT_TEXT)
    vocab_findings = [f for f in r.findings if f.code == "AI_OVERUSED_VOCAB"]
    assert vocab_findings
    assert any(f.severity == "MEDIUM" for f in vocab_findings)


# ---- AI_TRICOLON_OVERUSE -----------------------------------------------------

def test_tricolon_text_detected():
    r = ai_signal_check(fx.TRICOLON_TEXT)
    assert "AI_TRICOLON_OVERUSE" in _codes(r)


# ---- AI_RHETORICAL_CONTRAST --------------------------------------------------

def test_rhetorical_contrast_detected_high_severity():
    r = ai_signal_check(fx.RHETORICAL_CONTRAST_TEXT)
    rc_findings = [f for f in r.findings if f.code == "AI_RHETORICAL_CONTRAST"]
    assert rc_findings
    assert any(f.severity == "HIGH" for f in rc_findings)


# ---- AI_TRANSITIONAL_OVERUSE -------------------------------------------------

def test_transitional_overuse_detected_high_on_4_plus():
    r = ai_signal_check(fx.TRANSITIONAL_OVERUSE_TEXT)
    tr_findings = [f for f in r.findings if f.code == "AI_TRANSITIONAL_OVERUSE"]
    assert tr_findings
    assert any(f.severity == "HIGH" for f in tr_findings)


# ---- AI_PRESENT_PARTICIPLE_PILEUP --------------------------------------------

def test_present_participle_pileup_detected():
    r = ai_signal_check(fx.PRESENT_PARTICIPLE_PILEUP_TEXT)
    assert "AI_PRESENT_PARTICIPLE_PILEUP" in _codes(r)


# ---- AI_HEDGING_PHRASE -------------------------------------------------------

def test_hedging_phrase_detected_low_severity():
    r = ai_signal_check(fx.HEDGING_PHRASE_TEXT)
    h_findings = [f for f in r.findings if f.code == "AI_HEDGING_PHRASE"]
    assert h_findings
    assert h_findings[0].severity == "LOW"


# ---- AI_RANGE_QUANTIFIER -----------------------------------------------------

def test_range_quantifier_detected():
    r = ai_signal_check(fx.RANGE_QUANTIFIER_TEXT)
    assert "AI_RANGE_QUANTIFIER" in _codes(r)


# ---- AI_WHETHER_DISJUNCTION --------------------------------------------------

def test_whether_disjunction_detected():
    r = ai_signal_check(fx.WHETHER_DISJUNCTION_TEXT)
    assert "AI_WHETHER_DISJUNCTION" in _codes(r)


# ---- Score boundaries --------------------------------------------------------

def test_clean_human_text_produces_zero_findings():
    r = ai_signal_check(fx.CLEAN_HUMAN_TEXT)
    assert r.findings == []
    assert r.score == 0


def test_heavily_ai_text_score_at_least_60():
    r = ai_signal_check(fx.HEAVILY_AI_TEXT)
    assert r.score >= 60


def test_score_capped_at_100():
    r = ai_signal_check(fx.HEAVILY_AI_TEXT)
    assert r.score <= 100


# ---- Result shape ------------------------------------------------------------

def test_finding_carries_excerpt_and_suggestion():
    r = ai_signal_check(fx.OVERUSED_VOCAB_HEAVY_TEXT)
    f = r.findings[0]
    assert hasattr(f, "code")
    assert hasattr(f, "severity")
    assert hasattr(f, "excerpt")
    assert hasattr(f, "suggestion")
    assert f.severity in ("HIGH", "MEDIUM", "LOW")


def test_result_has_findings_and_score_attributes():
    r = ai_signal_check(fx.CLEAN_HUMAN_TEXT)
    assert hasattr(r, "findings")
    assert hasattr(r, "score")
    assert isinstance(r.score, int)
