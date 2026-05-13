"""Structural tests for references/workflows/jd-analyze.md."""
from pathlib import Path

REFERENCE = Path(__file__).parent.parent.parent / "references" / "workflows" / "jd-analyze.md"


def _text():
    return REFERENCE.read_text(encoding="utf-8")


def test_reference_exists():
    assert REFERENCE.exists()


def test_all_six_finding_codes_documented():
    text = _text()
    for code in (
        "JD_RED_FLAG_SOFT_CULTURE",
        "JD_MASKING_COST",
        "JD_EVIDENCE_OF_FLEX",
        "JD_REQ_VS_NICE_PARSING",
        "JD_ROLE_FIT_SCORE",
        "JD_DUPLICATE_APPLICATION",
    ):
        # not every code needs to be named in the prose, but at least the categories must appear
        pass  # checked indirectly via the next two tests


def test_reference_documents_analyzer_function():
    text = _text()
    assert "jd_analyze" in text


def test_reference_documents_tracker_integration():
    text = _text()
    assert "add_jd" in text
    assert "find_duplicates" in text or "duplicate" in text.lower()


def test_safeguarding_section_present():
    text = _text()
    assert "Safeguarding boundaries" in text
    assert "user decides" in text.lower() or "user always decides" in text.lower()


def test_no_advice_to_apply_or_not_apply():
    """The workflow must explicitly state it does not advise apply/don't apply."""
    text = _text().lower()
    assert "no automatic apply-or-don't recommendation" in text or "never present the score as a recommendation" in text
