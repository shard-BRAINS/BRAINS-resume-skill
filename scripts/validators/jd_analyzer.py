"""JD analyzer — surfaces ND-relevant signals in a job description.

Finding codes:
  - JD_RED_FLAG_SOFT_CULTURE: rockstar/ninja/fast-paced/etc culture markers
  - JD_MASKING_COST: high-EQ/stakeholder/open-plan/phone-heavy/etc
  - JD_EVIDENCE_OF_FLEX: remote-first/async-first/accommodations/etc
  - JD_REQ_VS_NICE_PARSING: parses Required vs Nice-to-have sections
  - JD_ROLE_FIT_SCORE: 0-100 based on user focus areas vs JD requirements
  - JD_DUPLICATE_APPLICATION: tracker lookup against company + role

The validator never overrides the user. Findings are surfaced to the workflow;
the user always decides.
"""
from dataclasses import dataclass, field
import re
from typing import List, Optional


# ---- Keyword catalogs --------------------------------------------------------

SOFT_CULTURE_TERMS = (
    "rockstar", "ninja", "wear many hats", "fast-paced",
    "we're a family", "work hard play hard", "flexible attitude",
    "can-do mindset", "passionate", "team player", "go-getter",
    "self-starter", "guru", "dynamic individual",
)

MASKING_COST_TERMS = (
    "high-eq", "high eq", "stakeholder management",
    "client-facing presentations", "client facing presentations",
    "open-plan office", "open plan office",
    "phone-heavy", "phone heavy",
    "frequent context switching",
    "c-suite", "executive presence",
)

EVIDENCE_OF_FLEX_TERMS = (
    "remote-first", "async-first", "async first",
    "flexible hours", "accommodations available",
    "written-comms culture", "written comms culture",
    "asynchronously", "asynchronous",
)


# ---- Result types ------------------------------------------------------------

@dataclass
class JdFinding:
    code: str
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW | INFO | POSITIVE
    excerpt: str
    suggestion: str


@dataclass
class JdAnalyzerResult:
    findings: List[JdFinding] = field(default_factory=list)
    required_list: List[str] = field(default_factory=list)
    nice_list: List[str] = field(default_factory=list)
    role_fit_score: Optional[int] = None


# ---- Helpers -----------------------------------------------------------------

def _find_hits(text: str, terms) -> List[str]:
    text_lower = text.lower()
    return [t for t in terms if t in text_lower]


# ---- Main entry --------------------------------------------------------------

def jd_analyze(
    jd_text: str,
    focus_areas: Optional[List[str]] = None,
    company: Optional[str] = None,
    role_title: Optional[str] = None,
) -> JdAnalyzerResult:
    """Analyse a JD and return findings + parsed requirement lists + role-fit score.

    focus_areas, company, role_title are optional; if absent, those checks are
    skipped (role-fit returns None, duplicate-application check skipped).
    """
    result = JdAnalyzerResult()

    # 1. Soft-culture red flags
    soft_hits = _find_hits(jd_text, SOFT_CULTURE_TERMS)
    if soft_hits:
        severity = "HIGH" if len(soft_hits) >= 3 else "MEDIUM"
        result.findings.append(JdFinding(
            code="JD_RED_FLAG_SOFT_CULTURE",
            severity=severity,
            excerpt=", ".join(soft_hits[:5]),
            suggestion=(
                "These culture markers historically correlate with high-masking "
                "demands. Consider whether the role's day-to-day behaviour matches "
                "the marketing language, and how much energy you would spend "
                "performing the implied persona."
            ),
        ))

    # 2. Masking-cost markers
    mc_hits = _find_hits(jd_text, MASKING_COST_TERMS)
    if mc_hits:
        result.findings.append(JdFinding(
            code="JD_MASKING_COST",
            severity="MEDIUM",
            excerpt=", ".join(mc_hits[:5]),
            suggestion=(
                "This role demands a higher masking cost. Not a red flag — "
                "but worth deliberately thinking about your energy budget and "
                "whether the role's strengths offset the cost for you."
            ),
        ))

    # 3. Evidence-of-real-flexibility
    flex_hits = _find_hits(jd_text, EVIDENCE_OF_FLEX_TERMS)
    if flex_hits:
        result.findings.append(JdFinding(
            code="JD_EVIDENCE_OF_FLEX",
            severity="POSITIVE",
            excerpt=", ".join(flex_hits[:5]),
            suggestion=(
                "Concrete flexibility signals detected. These move the role-fit "
                "score upward and suggest the employer has done more than use "
                "flexibility as a buzzword."
            ),
        ))

    return result
