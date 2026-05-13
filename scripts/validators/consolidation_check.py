"""Resume + LinkedIn consolidation validator.

Compares position-level data extracted from a resume against position data
parsed from a LinkedIn export and surfaces narrative inconsistencies:

  - CONSOLIDATION_JOB_TITLE_MISMATCH       (severity: MEDIUM)
  - CONSOLIDATION_DATE_INCONSISTENCY       (severity: MEDIUM)
  - CONSOLIDATION_ACHIEVEMENT_ONLY_IN_RESUME    (severity: LOW)
  - CONSOLIDATION_ACHIEVEMENT_ONLY_IN_LINKEDIN  (severity: LOW)
  - CONSOLIDATION_TONE_DIVERGENCE          (severity: LOW — heuristic)

Each finding carries three suggested resolutions (resume-leading,
linkedin-leading, new-synthesis). The user chooses.

Read-only: this validator never edits either document.
"""
from dataclasses import dataclass, field
from difflib import SequenceMatcher
import re
from typing import List, Dict, Optional


# --- Result types -------------------------------------------------------------

# Resolutions are dicts {"tag": ..., "text": ...} rather than a dataclass —
# the dict shape matches the markdown-report rendering directly and keeps
# the type surface narrow.


@dataclass
class ConsolidationFinding:
    code: str
    severity: str
    role_context: str  # human-readable identifier of the role being compared
    resume_excerpt: str
    linkedin_excerpt: str
    suggested_resolutions: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class ConsolidationCheckResult:
    findings: List[ConsolidationFinding] = field(default_factory=list)


# --- Matching helpers ---------------------------------------------------------

def _normalise_company(name: str) -> str:
    """Lower-case + strip common corporate suffixes for fuzzy company match."""
    n = (name or "").lower().strip()
    for suffix in (" inc.", " inc", " corp.", " corp", " corporation",
                   " ltd.", " ltd", " limited", " llc", " gmbh"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]
    return n.strip()


def _similar(a: str, b: str) -> float:
    """Return a 0-1 similarity ratio for two strings."""
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def _dates_overlap(r_start: str, r_end: str, l_start: str, l_end: str) -> bool:
    """Both date pairs are YYYY-MM strings (or YYYY). Return True if the
    intervals overlap at the year level — the same-role match is permissive.
    Differences within the overlap window are surfaced as DATE_INCONSISTENCY."""
    def year(s):
        return int((s or "0000")[:4])
    r_s, r_e = year(r_start), year(r_end) or 9999
    l_s, l_e = year(l_start), year(l_end) or 9999
    return r_s <= l_e and l_s <= r_e


def _match_roles(resume_positions, linkedin_positions):
    """Yield (resume_pos, linkedin_pos) pairs that refer to the same role.

    Match heuristic: normalised company name similarity >= 0.85 AND date
    intervals overlap at the year level.
    """
    used = set()
    for r in resume_positions:
        r_company = _normalise_company(r.get("company"))
        for idx, l in enumerate(linkedin_positions):
            if idx in used:
                continue
            if _similar(r_company, _normalise_company(l.get("company"))) < 0.85:
                continue
            if not _dates_overlap(
                r.get("start_date", ""), r.get("end_date", ""),
                l.get("start_date", ""), l.get("end_date", ""),
            ):
                continue
            used.add(idx)
            yield r, l
            break


# --- Bullet-similarity for ACHIEVEMENT_ONLY_IN_* ------------------------------

BULLET_SIMILARITY_THRESHOLD = 0.55  # tuned for paraphrase tolerance


def _bullet_matches_any(bullet: str, candidates: List[str]) -> bool:
    return any(_similar(bullet, c) >= BULLET_SIMILARITY_THRESHOLD for c in candidates)


# --- Tone divergence heuristic ------------------------------------------------

FORMAL_TOKENS = (
    "directed", "achieved", "delivered", "implemented", "established",
    "architected", "demonstrated", "measurable", "across", "throughout",
)
CASUAL_TOKENS = (
    "spent", "turned out", "got there", "stuff", "things", "good times",
    "a lot of", "kind of", "sort of", "way", "way bigger",
)


def _formality_score(text: str) -> int:
    """Crude lexical formality score. Positive = formal-leaning; negative = casual."""
    if not text:
        return 0
    t = text.lower()
    formal_hits = sum(1 for tok in FORMAL_TOKENS if tok in t)
    casual_hits = sum(1 for tok in CASUAL_TOKENS if tok in t)
    return formal_hits - casual_hits


def _tone_diverges(resume_desc: str, linkedin_desc: str) -> bool:
    """True if the two descriptions read as substantially different register.

    Heuristic — flagged as such in suggestion text. The user always decides.
    """
    return abs(_formality_score(resume_desc) - _formality_score(linkedin_desc)) >= 3


# --- Suggested-resolution generator -------------------------------------------

def _three_resolutions(resume_value: str, linkedin_value: str, kind: str):
    """Produce the resume-leading / linkedin-leading / new-synthesis triple."""
    return [
        {"tag": "RESUME-LEADING",
         "text": f"Adopt the resume version on both surfaces: {resume_value!r}."},
        {"tag": "LINKEDIN-LEADING",
         "text": f"Adopt the LinkedIn version on both surfaces: {linkedin_value!r}."},
        {"tag": "NEW-SYNTHESIS",
         "text": f"Write a new {kind} that unifies the strongest elements of both. "
                 f"This typically requires a manual rewrite — the validator does not "
                 f"auto-generate it."},
    ]


# --- Main validator -----------------------------------------------------------

def consolidation_check(
    resume_positions: List[dict],
    linkedin_positions: List[dict],
) -> ConsolidationCheckResult:
    """Compare resume and LinkedIn position lists and surface inconsistencies.

    Each position dict expects keys: company, title, start_date (YYYY-MM or
    YYYY), end_date (same), bullets (list[str]), description (str).
    """
    result = ConsolidationCheckResult()

    for r, l in _match_roles(resume_positions, linkedin_positions):
        role_context = f"{r.get('company', '')} ({r.get('start_date', '')} – {r.get('end_date', '')})"

        # 1. Title mismatch
        if _similar(r.get("title", ""), l.get("title", "")) < 0.85:
            result.findings.append(ConsolidationFinding(
                code="CONSOLIDATION_JOB_TITLE_MISMATCH",
                severity="MEDIUM",
                role_context=role_context,
                resume_excerpt=r.get("title", ""),
                linkedin_excerpt=l.get("title", ""),
                suggested_resolutions=_three_resolutions(
                    r.get("title", ""), l.get("title", ""), "title"
                ),
            ))

        # 2. Date inconsistency — start or end month differs while same role
        if r.get("start_date", "") != l.get("start_date", ""):
            result.findings.append(ConsolidationFinding(
                code="CONSOLIDATION_DATE_INCONSISTENCY",
                severity="MEDIUM",
                role_context=role_context,
                resume_excerpt=f"Start: {r.get('start_date', '')}",
                linkedin_excerpt=f"Start: {l.get('start_date', '')}",
                suggested_resolutions=_three_resolutions(
                    r.get("start_date", ""), l.get("start_date", ""), "start date"
                ),
            ))
        elif r.get("end_date", "") != l.get("end_date", ""):
            result.findings.append(ConsolidationFinding(
                code="CONSOLIDATION_DATE_INCONSISTENCY",
                severity="MEDIUM",
                role_context=role_context,
                resume_excerpt=f"End: {r.get('end_date', '')}",
                linkedin_excerpt=f"End: {l.get('end_date', '')}",
                suggested_resolutions=_three_resolutions(
                    r.get("end_date", ""), l.get("end_date", ""), "end date"
                ),
            ))

        # 3. Achievement only on resume
        r_bullets = r.get("bullets", []) or []
        l_bullets = l.get("bullets", []) or []
        for b in r_bullets:
            if not _bullet_matches_any(b, l_bullets):
                result.findings.append(ConsolidationFinding(
                    code="CONSOLIDATION_ACHIEVEMENT_ONLY_IN_RESUME",
                    severity="LOW",
                    role_context=role_context,
                    resume_excerpt=b,
                    linkedin_excerpt="(not present)",
                    suggested_resolutions=[
                        {"tag": "RESUME-LEADING",
                         "text": f"Add this bullet to the LinkedIn role: {b!r}."},
                        {"tag": "LINKEDIN-LEADING",
                         "text": f"Drop the bullet from the resume — the LinkedIn version omits it for a reason the user knows best."},
                        {"tag": "NEW-SYNTHESIS",
                         "text": "Rephrase the bullet for LinkedIn's audience (recruiter scan, "
                                 "scrolling-on-mobile context) and add a tightened version there."},
                    ],
                ))

        # 4. Achievement only on LinkedIn
        for b in l_bullets:
            if not _bullet_matches_any(b, r_bullets):
                result.findings.append(ConsolidationFinding(
                    code="CONSOLIDATION_ACHIEVEMENT_ONLY_IN_LINKEDIN",
                    severity="LOW",
                    role_context=role_context,
                    resume_excerpt="(not present)",
                    linkedin_excerpt=b,
                    suggested_resolutions=[
                        {"tag": "RESUME-LEADING",
                         "text": "Drop the bullet from LinkedIn — the resume version omits it."},
                        {"tag": "LINKEDIN-LEADING",
                         "text": f"Add this bullet to the resume role: {b!r}."},
                        {"tag": "NEW-SYNTHESIS",
                         "text": "Rephrase the bullet for the resume audience (achievement-led, "
                                 "metric-anchored) and add a tightened version there."},
                    ],
                ))

        # 5. Tone divergence
        if _tone_diverges(r.get("description", ""), l.get("description", "")):
            result.findings.append(ConsolidationFinding(
                code="CONSOLIDATION_TONE_DIVERGENCE",
                severity="LOW",
                role_context=role_context,
                resume_excerpt=(r.get("description", "") or "")[:140],
                linkedin_excerpt=(l.get("description", "") or "")[:140],
                suggested_resolutions=[
                    {"tag": "RESUME-LEADING",
                     "text": "Carry the resume's formal/quantitative register over to LinkedIn — "
                             "match the resume's specificity in narrative form on LinkedIn."},
                    {"tag": "LINKEDIN-LEADING",
                     "text": "Carry the LinkedIn's conversational register over to the resume — "
                             "tighten where needed but preserve the voice."},
                    {"tag": "NEW-SYNTHESIS",
                     "text": "Pick a target register for each surface deliberately. Resume: formal, "
                             "metric-anchored. LinkedIn: first-person, scannable proof. The two "
                             "registers can both be intentional; they should not be accidental."},
                ],
            ))

    return result
