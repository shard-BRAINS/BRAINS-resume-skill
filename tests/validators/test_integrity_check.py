"""Tests for the document-integrity validator.

Detects: prompt-injection paragraphs, instruction-override patterns,
system-prompt-style content, hidden-keyword stuffing blocks. All are
findings that ATS systems and human reviewers will treat as adverse signals,
independent of any ND-bias considerations.
"""
from scripts.validators.integrity_check import integrity_check
from tests.fixtures import integrity_fixtures as fx


def _codes(result):
    return [f.code for f in result.findings]


def test_llm_override_paragraph_detected():
    result = integrity_check(fx.INJECTION_LLM_OVERRIDE)
    assert "INTEGRITY_PROMPT_INJECTION_LLM_DIRECTIVE" in _codes(result)


def test_ignore_instructions_pattern_detected():
    result = integrity_check(fx.INJECTION_IGNORE_INSTRUCTIONS)
    assert "INTEGRITY_PROMPT_INJECTION_IGNORE_INSTRUCTIONS" in _codes(result)


def test_system_prompt_pattern_detected():
    result = integrity_check(fx.INJECTION_SYSTEM_PROMPT)
    assert "INTEGRITY_PROMPT_INJECTION_SYSTEM_PROMPT" in _codes(result)


def test_hidden_keyword_block_detected():
    result = integrity_check(fx.INJECTION_HIDDEN_KEYWORDS)
    assert "INTEGRITY_HIDDEN_KEYWORD_STUFFING" in _codes(result)


def test_clean_text_returns_no_findings():
    result = integrity_check(fx.CLEAN_RESUME_SNIPPET)
    assert result.findings == []


def test_result_includes_severity_and_excerpt():
    result = integrity_check(fx.INJECTION_LLM_OVERRIDE)
    finding = result.findings[0]
    assert hasattr(finding, "code")
    assert hasattr(finding, "severity")
    assert hasattr(finding, "excerpt")
    assert hasattr(finding, "suggestion")
    assert finding.severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
