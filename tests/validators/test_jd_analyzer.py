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


import pytest


def test_well_parsed_jd_extracts_required_and_nice_lists():
    r = jd_analyze(fx.WELL_PARSED_JD)
    # Required list should contain at least one of the bulleted items
    required_joined = " ".join(r.required_list).lower()
    assert "5+ years" in required_joined or "backend python" in required_joined
    nice_joined = " ".join(r.nice_list).lower()
    assert "go" in nice_joined or "open-source" in nice_joined


def test_well_parsed_jd_produces_req_vs_nice_finding():
    r = jd_analyze(fx.WELL_PARSED_JD)
    codes = [f.code for f in r.findings]
    assert "JD_REQ_VS_NICE_PARSING" in codes


def test_role_fit_score_none_when_no_focus_areas_given():
    r = jd_analyze(fx.WELL_PARSED_JD)
    assert r.role_fit_score is None


def test_role_fit_score_computed_when_focus_areas_given():
    r = jd_analyze(
        fx.WELL_PARSED_JD,
        focus_areas=["python", "distributed systems", "on-call"],
    )
    assert r.role_fit_score is not None
    assert 0 <= r.role_fit_score <= 100


def test_role_fit_score_full_match_is_high():
    """All focus areas match required items → score should be ≥80."""
    r = jd_analyze(
        fx.WELL_PARSED_JD,
        focus_areas=["python", "distributed systems", "on-call"],
    )
    assert r.role_fit_score >= 80


def test_role_fit_score_no_match_is_low():
    """Focus areas have nothing to do with the JD → low score."""
    r = jd_analyze(
        fx.WELL_PARSED_JD,
        focus_areas=["ceramics", "marine biology", "viking history"],
    )
    assert r.role_fit_score <= 30


def test_role_fit_score_finding_in_result():
    r = jd_analyze(
        fx.WELL_PARSED_JD, focus_areas=["python", "on-call"],
    )
    codes = [f.code for f in r.findings]
    assert "JD_ROLE_FIT_SCORE" in codes


def test_duplicate_application_check_missing_db_does_not_crash(monkeypatch, tmp_path):
    """If tracker db doesn't exist, the duplicate check is a no-op."""
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "never.db"))
    r = jd_analyze(
        fx.CLEAN_NEUTRAL_JD,
        company="Example Corp", role_title="Senior Engineer",
    )
    codes = [f.code for f in r.findings]
    assert "JD_DUPLICATE_APPLICATION" not in codes


def test_duplicate_application_check_detects_recent_application(monkeypatch, tmp_path):
    """Seed an application via the tracker, then ensure the analyzer flags it."""
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    from datetime import datetime
    from scripts.tracker.add import (
        add_resume_version, add_jd, add_application,
    )
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    cid = create_candidate("Example", "Candidate", [], None, None)
    set_active_candidate(cid)
    rv_id = add_resume_version(file_path=None, template="hybrid", focus_areas=[])
    jd_id = add_jd(
        source="paste", source_ref=None,
        company="Example Corp", role_title="Senior Engineer",
        raw_text="x", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    add_application(
        jd_id=jd_id, resume_version_id=rv_id, cover_letter_id=None,
        submitted_at=datetime.now(), channel="direct",
    )
    r = jd_analyze(
        fx.CLEAN_NEUTRAL_JD,
        company="Example Corp", role_title="Senior Engineer",
    )
    codes = [f.code for f in r.findings]
    assert "JD_DUPLICATE_APPLICATION" in codes
