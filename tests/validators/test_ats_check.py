"""Tests for the ATS-safety validator."""
from pathlib import Path

from scripts.validators.ats_check import ats_check, AtsCheckResult

FIXTURES = Path(__file__).parent.parent.parent / "docs" / "testing" / "fixtures"


def test_clean_docx_passes():
    result = ats_check(FIXTURES / "ats_clean.docx")
    assert isinstance(result, AtsCheckResult)
    assert result.passed is True
    assert result.failures == []


def test_table_is_detected_as_failure():
    result = ats_check(FIXTURES / "ats_with_table.docx")
    assert result.passed is False
    failure_codes = [f.code for f in result.failures]
    assert "TABLE_PRESENT" in failure_codes


def test_header_with_critical_info_is_warned():
    result = ats_check(FIXTURES / "ats_with_header.docx")
    warning_codes = [w.code for w in result.warnings]
    failure_codes = [f.code for f in result.failures]
    assert "CRITICAL_INFO_IN_HEADER" in (warning_codes + failure_codes)


def test_result_includes_pass_warn_fail_counts():
    result = ats_check(FIXTURES / "ats_clean.docx")
    assert hasattr(result, "passed")
    assert hasattr(result, "warnings")
    assert hasattr(result, "failures")
