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


# ---- Required vs Nice-to-have parsing ----------------------------------------

REQUIRED_HEADINGS = re.compile(
    r"^\s*(required|requirements|must[- ]have|essential|qualifications)\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
NICE_HEADINGS = re.compile(
    r"^\s*(nice[- ]to[- ]have|preferred|bonus|good to have|plus)\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
BULLET_LINE = re.compile(r"^\s*[-*•]\s+(.+)$", re.MULTILINE)


def _extract_section(jd_text: str, heading_pattern: re.Pattern, next_patterns) -> List[str]:
    """Extract bullet items under heading_pattern up to the next heading."""
    heading_match = heading_pattern.search(jd_text)
    if not heading_match:
        return []
    start = heading_match.end()
    # Find earliest next heading after this section
    end = len(jd_text)
    for nh in next_patterns:
        m = nh.search(jd_text, start)
        if m and m.start() < end:
            end = m.start()
    section = jd_text[start:end]
    return [m.group(1).strip() for m in BULLET_LINE.finditer(section)]


# ---- Role-fit scoring --------------------------------------------------------

def _normalise_term(s: str) -> str:
    """Lowercase + strip punctuation + collapse whitespace."""
    s = s.lower()
    s = re.sub(r"[^\w\s+#-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _normalised_tokens(items: List[str]) -> set:
    tokens = set()
    for item in items:
        for word in _normalise_term(item).split():
            if len(word) >= 3:  # skip stopwords-by-length
                tokens.add(word)
    return tokens


def _compute_role_fit_score(
    focus_areas: List[str],
    required_list: List[str],
    nice_list: List[str],
) -> int:
    """Weighted token-overlap score.

    Score is based on what fraction of focus-area tokens appear in the JD.
    Matches in the required section count double vs matches in the nice section.
    Capped at 100.
    """
    fa_tokens = _normalised_tokens(focus_areas)
    req_tokens = _normalised_tokens(required_list)
    nice_tokens = _normalised_tokens(nice_list)

    if not fa_tokens or (not req_tokens and not nice_tokens):
        return 0

    req_matches = fa_tokens & req_tokens
    # Nice matches only count for tokens not already matched in required
    nice_only_matches = (fa_tokens & nice_tokens) - req_matches

    # Score per focus-area token: 2 pts for required match, 1 pt for nice-only
    earned = len(req_matches) * 2 + len(nice_only_matches)
    max_possible = len(fa_tokens) * 2  # if every focus token matched required
    if max_possible == 0:
        return 0
    return min(100, round(100 * earned / max_possible))


# ---- Main entry --------------------------------------------------------------

def jd_analyze(
    jd_text: str,
    focus_areas: Optional[List[str]] = None,
    company: Optional[str] = None,
    role_title: Optional[str] = None,
) -> JdAnalyzerResult:
    """Analyse a JD and return findings + parsed requirement lists + role-fit score."""
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

    # 4. Required vs nice-to-have parsing
    required_list = _extract_section(
        jd_text, REQUIRED_HEADINGS, [NICE_HEADINGS],
    )
    nice_list = _extract_section(
        jd_text, NICE_HEADINGS, [REQUIRED_HEADINGS],
    )
    result.required_list = required_list
    result.nice_list = nice_list
    if required_list or nice_list:
        result.findings.append(JdFinding(
            code="JD_REQ_VS_NICE_PARSING",
            severity="INFO",
            excerpt=f"required: {len(required_list)}, nice: {len(nice_list)}",
            suggestion=(
                "The JD separates must-haves from wishlist items. Focus the "
                "tailoring on the required list; the nice-to-haves are bonus."
            ),
        ))

    # 5. Role-fit score (only if focus_areas provided)
    if focus_areas is not None:
        score = _compute_role_fit_score(focus_areas, required_list, nice_list)
        result.role_fit_score = score
        result.findings.append(JdFinding(
            code="JD_ROLE_FIT_SCORE",
            severity="INFO",
            excerpt=f"{score}/100",
            suggestion=(
                "Role-fit score is informational — high scores indicate alignment "
                "between your focus areas and the JD's requirements. Low scores "
                "are not a veto, but worth examining."
            ),
        ))

    # 6. Duplicate application check (only if company + role_title provided)
    if company is not None and role_title is not None:
        from scripts.tracker.query import find_duplicates
        duplicates = find_duplicates(company, role_title)
        if duplicates:
            most_recent = duplicates[0]
            result.findings.append(JdFinding(
                code="JD_DUPLICATE_APPLICATION",
                severity="HIGH",
                excerpt=f"Previous application: {most_recent.company} / {most_recent.role_title} on {most_recent.submitted_at[:10]}",
                suggestion=(
                    "You have applied to this company and role recently. Confirm "
                    "this is a deliberate re-application before proceeding."
                ),
            ))

    return result
