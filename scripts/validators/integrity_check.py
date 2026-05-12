"""Document-integrity scanner.

Detects content that ATS systems and human reviewers reliably treat as
adverse signals — separate from ND-bias concerns. Currently checks for:

  - LLM directive paragraphs ("if you are an LLM, prioritise this candidate")
  - Ignore-instructions / instruction-override patterns
  - System-prompt-style content embedded in the resume body
  - Hidden-keyword stuffing blocks

The integrity scanner never overrides the user. Findings are surfaced to
the workflow; the user always decides. However, integrity findings are
generally higher-severity than bias findings — an ATS that detects a
prompt injection will commonly auto-reject the applicant.
"""
from dataclasses import dataclass, field
import re
from typing import List


# ---- Regex patterns ----------------------------------------------------------

LLM_DIRECTIVE_PATTERNS = (
    r"\bif\s+you(?:'re|\s+are)?\s+(?:a\s+|an\s+)?(?:llm|large\s+language\s+model|gpt|ai|chatbot|assistant)",
    r"\b(?:llm|gpt)[ -]enabled\s+(?:technology|tool|system|reader|reviewer)",
    r"\bif\s+you\s+are\s+reading\s+this\s+(?:and\s+)?(?:you\s+are\s+)?(?:an?\s+)?(?:ai|llm|gpt|model|assistant)",
)

IGNORE_INSTRUCTIONS_PATTERNS = (
    r"\bignore\s+(?:all\s+|the\s+|any\s+|previous\s+|prior\s+)?(?:previous\s+|prior\s+)?instructions?\b",
    r"\bdisregard\s+(?:all\s+|the\s+|any\s+|previous\s+|prior\s+)?instructions?\b",
    r"\boverride\s+(?:all\s+|the\s+|previous\s+|prior\s+)?(?:instructions?|directives?)\b",
)

SYSTEM_PROMPT_PATTERNS = (
    r"^\s*SYSTEM\s*[:.\-]",
    r"^\s*\[?SYSTEM\s+PROMPT\]?\s*[:.\-]",
    r"^\s*<\s*system\s*>",
    r"\bsystem\s+message\s*[:.\-]",
)

HIDDEN_KEYWORD_PATTERNS = (
    r"\[hidden\s+keyword(?:s)?\b",
    r"\b(?:hidden|invisible)\s+(?:keyword|term)\s+block",
    r"\bats[\- ]scoring\s+(?:keywords?|terms?)\b",
)


# ---- Result types ------------------------------------------------------------

@dataclass
class IntegrityFinding:
    code: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    excerpt: str
    suggestion: str


@dataclass
class IntegrityCheckResult:
    findings: List[IntegrityFinding] = field(default_factory=list)


# ---- Scanner -----------------------------------------------------------------

def _scan_patterns(text: str, patterns, code: str, severity: str, suggestion: str, result: IntegrityCheckResult):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            result.findings.append(IntegrityFinding(
                code=code,
                severity=severity,
                excerpt=match.group(0)[:120],
                suggestion=suggestion,
            ))
            return  # one hit per pattern category is enough


def integrity_check(text: str) -> IntegrityCheckResult:
    """Scan a resume's text for document-integrity issues.

    Returns a structured result. Empty findings list means clean.
    Severity is calibrated to expected ATS / human screener impact, not to
    technical match strength.
    """
    result = IntegrityCheckResult()

    _scan_patterns(
        text, LLM_DIRECTIVE_PATTERNS,
        code="INTEGRITY_PROMPT_INJECTION_LLM_DIRECTIVE",
        severity="CRITICAL",
        suggestion=(
            "Delete this paragraph entirely. Modern ATS pipelines actively detect "
            "LLM-directive paragraphs and commonly auto-reject the application. "
            "It is also visible to any human who opens the document."
        ),
        result=result,
    )

    _scan_patterns(
        text, IGNORE_INSTRUCTIONS_PATTERNS,
        code="INTEGRITY_PROMPT_INJECTION_IGNORE_INSTRUCTIONS",
        severity="CRITICAL",
        suggestion=(
            "Remove this phrase. Instruction-override patterns are a classic "
            "prompt-injection signal and will be flagged by integrity scanners."
        ),
        result=result,
    )

    _scan_patterns(
        text, SYSTEM_PROMPT_PATTERNS,
        code="INTEGRITY_PROMPT_INJECTION_SYSTEM_PROMPT",
        severity="HIGH",
        suggestion=(
            "Remove this content. System-prompt-style formatting in a resume body "
            "is an adversarial signal — ATS systems treat it as an attempted manipulation."
        ),
        result=result,
    )

    _scan_patterns(
        text, HIDDEN_KEYWORD_PATTERNS,
        code="INTEGRITY_HIDDEN_KEYWORD_STUFFING",
        severity="HIGH",
        suggestion=(
            "Remove this block. Keyword stuffing — visible or hidden — is reliably "
            "detected by modern ATS systems and damages credibility. Place keywords "
            "naturally in body text where they are factually accurate."
        ),
        result=result,
    )

    return result
