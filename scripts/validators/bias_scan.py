"""ND-bias deterministic scanner.

A regex/keyword backstop for the contextual review Claude performs. Catches
the patterns from references/nd-bias-patterns.md that are deterministically
detectable; flags the rest for review.

Confident-hit patterns (these produce ND_BIAS_Pn_<NAME> codes):
  1. Soft-skills-coded vocabulary
  2. Gap-explanation language on the resume
  6. Direct ND signal terms
  7. Indirect ND signal terms
  10. Mixed identity-first / person-first language

Needs-review patterns (these produce ND_BIAS_Pn_<NAME>_REVIEW codes):
  3. Short-tenure framing
  4. Hyperfocus / narrow expertise
  5. Modesty / under-claim
  8. Communication-warmth deficit
  9. Hyperbole mismatch / over-precision

The scanner never overrides the user. Findings are surfaced to the workflow;
the user always decides.
"""
from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import List


# ---- Pattern catalog (regex sources) -----------------------------------------

P1_SOFT_SKILLS_TERMS = (
    "passionate", "team player", "great communicator", "leadership presence",
    "thrive in fast-paced", "go-getter", "self-starter", "dynamic individual",
    "proactive", "synergy", "ninja", "rockstar", "guru", "wear many hats",
)

P2_GAP_PATTERNS = (
    r"career break to",
    r"career break for",
    r"took time off",
    r"returning to work",
    r"time away from work",
    r"period of unemployment",
    r"sabbatical to focus",
    r"break to focus on",
)

P6_DIRECT_ND_TERMS = (
    "autism", "autistic", "asd", "asperger", "aspie",
    "neurodivergent", "neurodiverse", "neurodiversity",
    "adhd", "add",
    "dyslexia", "dyslexic", "dyspraxia", "dyspraxic", "dyscalculia",
    "tourette",
    "executive function", "masking", "stimming", "sensory processing",
)

P7_INDIRECT_ND_TERMS = (
    "autism spectrum society", "autism society",
    "neurodiversity-affirming practitioner",
    "autistic pride",
    "adhd coach", "adhd advocacy",
    "neurodiversity in the workplace",
    "ambitious about autism",
)

P3_TENURE_LINE = re.compile(
    r"^\s*.+?,.+?,\s*(?P<start>\w{3}|\d{1,2})\s*(?P<start_year>\d{4})\s*[–\-—]\s*(?P<end>\w{3}|\d{1,2}|present)\s*(?P<end_year>\d{4})?",
    re.IGNORECASE | re.MULTILINE,
)

PERSON_FIRST_TERMS = ("person with ", "people with ", "individual with ", "individuals with ")
IDENTITY_FIRST_TERMS = ("autistic ", "neurodivergent ", "disabled ")


# ---- Result types ------------------------------------------------------------

@dataclass
class BiasFinding:
    pattern_code: str
    excerpt: str
    suggestion: str


@dataclass
class BiasScanResult:
    findings: List[BiasFinding] = field(default_factory=list)
    scanned_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


# ---- Scanner -----------------------------------------------------------------

def bias_scan(text: str) -> BiasScanResult:
    """Run the deterministic ND-bias scan on a string of resume text."""
    result = BiasScanResult()
    text_lower = text.lower()

    # P1: Soft-skills-coded vocabulary
    for term in P1_SOFT_SKILLS_TERMS:
        if term in text_lower:
            result.findings.append(BiasFinding(
                pattern_code="ND_BIAS_P1_SOFT_SKILLS",
                excerpt=term,
                suggestion="Replace with a concrete instance and measurable outcome (see nd-bias-patterns.md §1).",
            ))

    # P2: Gap explanation on resume
    for pat in P2_GAP_PATTERNS:
        if re.search(pat, text_lower):
            result.findings.append(BiasFinding(
                pattern_code="ND_BIAS_P2_GAP_EXPLANATION",
                excerpt=pat,
                suggestion="Remove the explanation. Leave the gap unexplained on the resume; prepare interview talking points separately (see nd-bias-patterns.md §2).",
            ))

    # P3: Short tenures — heuristic. If 2+ roles under ~18 months show up in
    # date format, flag for review.
    tenure_matches = list(P3_TENURE_LINE.finditer(text))
    short_count = 0
    for m in tenure_matches:
        start_year = m.group("start_year")
        end_year = m.group("end_year")
        if start_year and end_year and end_year.isdigit() and start_year.isdigit():
            if int(end_year) - int(start_year) <= 1:
                short_count += 1
    if short_count >= 2:
        result.findings.append(BiasFinding(
            pattern_code="ND_BIAS_P3_SHORT_TENURES_REVIEW",
            excerpt=f"{short_count} short tenures detected",
            suggestion="Consider grouping genuinely short engagements as contract/project work. See nd-bias-patterns.md §3.",
        ))

    # P4: Hyperfocus — repeated mention of the same domain term clustered tightly.
    # Heuristic: any single non-stopword token appearing >=4 times in a single
    # paragraph (text under 500 chars).
    if len(text) <= 500:
        tokens = re.findall(r"[A-Za-z]{4,}", text_lower)
        counts: dict = {}
        for tok in tokens:
            counts[tok] = counts.get(tok, 0) + 1
        if any(c >= 4 for c in counts.values()):
            result.findings.append(BiasFinding(
                pattern_code="ND_BIAS_P4_HYPERFOCUS_REVIEW",
                excerpt="Repeated domain term clustering",
                suggestion="Bridge deep-domain expertise to transferable competencies. See nd-bias-patterns.md §4.",
            ))

    # P5: Under-claim — passive credit-sharing phrases.
    P5_UNDER_TERMS = ("was part of", "helped with", "contributed to", "assisted with", "supported the")
    if any(t in text_lower for t in P5_UNDER_TERMS):
        result.findings.append(BiasFinding(
            pattern_code="ND_BIAS_P5_UNDER_CLAIM_REVIEW",
            excerpt="Credit-sharing language detected",
            suggestion="If the work was genuinely solo, recover full credit. See nd-bias-patterns.md §5.",
        ))

    # P6: Direct ND signal terms
    for term in P6_DIRECT_ND_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", text_lower):
            result.findings.append(BiasFinding(
                pattern_code="ND_BIAS_P6_DIRECT_SIGNAL",
                excerpt=term,
                suggestion="Direct ND signal detected. If non-disclosure is the chosen stance, replace or remove. See nd-bias-patterns.md §6.",
            ))

    # P7: Indirect ND signal terms
    for term in P7_INDIRECT_ND_TERMS:
        if term in text_lower:
            result.findings.append(BiasFinding(
                pattern_code="ND_BIAS_P7_INDIRECT_SIGNAL",
                excerpt=term,
                suggestion="Indirect ND signal detected. If non-disclosure is the chosen stance, consider a neutral reframe. See nd-bias-patterns.md §7.",
            ))

    # P8: Communication-warmth deficit — heuristic: text under 400 chars with
    # zero first-person pronouns and zero value/motivation tokens.
    if len(text) <= 400:
        first_person = bool(re.search(r"\b(i|we|my|our)\b", text_lower))
        warmth_tokens = ("care", "believe", "value", "love", "enjoy", "drawn to", "motivated")
        warmth = any(t in text_lower for t in warmth_tokens)
        if not first_person and not warmth and len(text) >= 50:
            result.findings.append(BiasFinding(
                pattern_code="ND_BIAS_P8_NO_WARMTH_REVIEW",
                excerpt="No first-person or warmth signals in short passage",
                suggestion="Consider adding one warmth signal (without sacrificing specificity). See nd-bias-patterns.md §8.",
            ))

    # P9: Over-precision — decimal in a context where one wouldn't expect it.
    if re.search(r"\d+\.\d+%", text):
        result.findings.append(BiasFinding(
            pattern_code="ND_BIAS_P9_OVER_PRECISION_REVIEW",
            excerpt="Decimal-precision percentage detected",
            suggestion="Calibrate precision to context. Decimal-precision percentages in summaries often read pedantic. See nd-bias-patterns.md §9.",
        ))

    # P10: Mixed identity-first / person-first
    has_identity = any(t in text_lower for t in IDENTITY_FIRST_TERMS)
    has_person_first = any(t in text_lower for t in PERSON_FIRST_TERMS)
    if has_identity and has_person_first:
        result.findings.append(BiasFinding(
            pattern_code="ND_BIAS_P10_MIXED_IDENTITY",
            excerpt="Mixed identity-first and person-first language",
            suggestion="Pick one and use it consistently per user preference. Default identity-first. See nd-bias-patterns.md §10.",
        ))

    return result
