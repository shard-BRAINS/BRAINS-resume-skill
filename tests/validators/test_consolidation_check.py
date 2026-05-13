"""Tests for the consolidation validator.

Each test pairs resume + LinkedIn position lists with seeded deltas and
asserts the validator surfaces the expected finding code.
"""
from scripts.validators.consolidation_check import consolidation_check
from tests.fixtures import consolidation_fixtures as fx


def _codes(result):
    return [f.code for f in result.findings]


def test_clean_alignment_produces_no_findings():
    result = consolidation_check(fx.CLEAN_RESUME, fx.CLEAN_LINKEDIN)
    assert result.findings == []


def test_job_title_mismatch_detected():
    result = consolidation_check(fx.TITLE_MISMATCH_RESUME, fx.TITLE_MISMATCH_LINKEDIN)
    assert "CONSOLIDATION_JOB_TITLE_MISMATCH" in _codes(result)


def test_date_inconsistency_detected():
    result = consolidation_check(fx.DATE_MISMATCH_RESUME, fx.DATE_MISMATCH_LINKEDIN)
    assert "CONSOLIDATION_DATE_INCONSISTENCY" in _codes(result)


def test_achievement_only_in_resume_detected():
    result = consolidation_check(
        fx.ACHIEVEMENT_RESUME_ONLY_RESUME, fx.ACHIEVEMENT_RESUME_ONLY_LINKEDIN
    )
    assert "CONSOLIDATION_ACHIEVEMENT_ONLY_IN_RESUME" in _codes(result)


def test_achievement_only_in_linkedin_detected():
    result = consolidation_check(
        fx.ACHIEVEMENT_LINKEDIN_ONLY_RESUME, fx.ACHIEVEMENT_LINKEDIN_ONLY_LINKEDIN
    )
    assert "CONSOLIDATION_ACHIEVEMENT_ONLY_IN_LINKEDIN" in _codes(result)


def test_tone_divergence_detected():
    result = consolidation_check(fx.TONE_DIVERGENT_RESUME, fx.TONE_DIVERGENT_LINKEDIN)
    assert "CONSOLIDATION_TONE_DIVERGENCE" in _codes(result)


def test_finding_carries_role_context_and_excerpts():
    result = consolidation_check(fx.TITLE_MISMATCH_RESUME, fx.TITLE_MISMATCH_LINKEDIN)
    finding = result.findings[0]
    assert hasattr(finding, "code")
    assert hasattr(finding, "severity")
    assert hasattr(finding, "role_context")
    assert hasattr(finding, "resume_excerpt")
    assert hasattr(finding, "linkedin_excerpt")
    assert hasattr(finding, "suggested_resolutions")
    assert isinstance(finding.suggested_resolutions, list)
    assert len(finding.suggested_resolutions) == 3
    tags = {r["tag"] for r in finding.suggested_resolutions}
    assert tags == {"RESUME-LEADING", "LINKEDIN-LEADING", "NEW-SYNTHESIS"}


def test_unmatched_role_in_resume_does_not_crash():
    """If a role appears in resume but not LinkedIn, the validator skips it
    silently — that's a coverage gap, not an inconsistency finding."""
    resume = fx.CLEAN_RESUME + [{
        "company": "Unique Co",
        "title": "Engineer",
        "start_date": "2010-01",
        "end_date": "2014-12",
        "bullets": ["Did things."],
        "description": "Did things.",
    }]
    result = consolidation_check(resume, fx.CLEAN_LINKEDIN)
    # The clean role still matches cleanly; the unmatched role is ignored.
    assert result.findings == []
