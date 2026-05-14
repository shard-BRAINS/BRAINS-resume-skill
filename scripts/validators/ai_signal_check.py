"""AI-signal validator — detects common AI-tell patterns in produced text.

Mirrors the bias_scan / integrity_check pattern: pure function, structured
findings, regex/keyword catalogs. No I/O, no DB access, no network.

Nine finding codes detect: em-dash overuse, AI-flavoured vocabulary,
parallel-structure abuse (tricolons), rhetorical contrasts, transitional
overuse, present-participle pile-ups, hedging phrases, range quantifiers,
whether-disjunctions.

Score is 0-100 with LOWER being better (fewer AI tells). Score weights:
HIGH=20, MEDIUM=10, LOW=5. Capped at 100.

The validator never overrides the user. Findings are surfaced to the
workflow; the user always decides whether to rewrite.
"""
from dataclasses import dataclass, field
import re
from typing import List


# ---- Tunable thresholds ------------------------------------------------------

EMDASH_PER_200_WORDS_MEDIUM = 3.0
EMDASH_PER_200_WORDS_HIGH = 5.0

OVERUSED_VOCAB_HIGH_DISTINCT_HITS = 3
TRANSITIONAL_OVERUSE_HIGH_HITS = 4
TRICOLON_CLUSTER_WINDOW_CHARS = 300


# ---- Vocabulary catalog ------------------------------------------------------

AI_OVERUSED_VOCAB_TERMS = (
    "delve", "delving", "delved",
    "tapestry",
    "vibrant",
    "robust",
    "leverage", "leveraging",
    "navigate", "navigating",
    "embark", "embarking",
    "elevate", "elevating",
    "foster", "fostering",
    "cultivate", "cultivating",
    "harness", "harnessing",
    "myriad",
    "plethora",
    "underscore", "underscores",
    "showcase", "showcasing",
    "seamless", "seamlessly",
    "innovative",
    "comprehensive",
    "holistic",
)


# ---- Pattern catalog ---------------------------------------------------------

TRICOLON_PATTERN = re.compile(
    r"\b\w+\b\s*,\s*\b\w+\b\s*,?\s+and\s+\b\w+\b",
    re.IGNORECASE,
)

RHETORICAL_CONTRAST_PATTERNS = (
    re.compile(r"\bit['’]?s?\s+not\s+just\s+\w[^,.]*[,.—\-]+\s*it['’]?s\s+", re.IGNORECASE),
    re.compile(r"\bthis\s+is\s+not\s+just\s+\w[^,.]*[,.—\-]+", re.IGNORECASE),
    re.compile(r"\bnot\s+only\s+\w[^,.]*\s+but\s+also\b", re.IGNORECASE),
    re.compile(r"\b\w+\s+isn['’]?t\s+just\s+\w[^,.]*[,.—\-]+\s*it['’]?s\s+", re.IGNORECASE),
)

TRANSITIONAL_TERMS = ("furthermore", "moreover", "additionally", "in conclusion")

HEDGING_PATTERNS = (
    re.compile(r"\bit['’]?s?\s+worth\s+noting\b", re.IGNORECASE),
    re.compile(r"\bit['’]?s?\s+important\s+to\s+note\b", re.IGNORECASE),
    re.compile(r"\bit\s+should\s+be\s+noted\b", re.IGNORECASE),
    re.compile(r"\bit\s+bears\s+mentioning\b", re.IGNORECASE),
)

RANGE_QUANTIFIER_PATTERNS = (
    re.compile(r"\branging\s+from\b", re.IGNORECASE),
    re.compile(r"\bspanning\s+\w+\s+to\b", re.IGNORECASE),
    re.compile(r"\bfrom\s+\w+\s+all\s+the\s+way\s+to\b", re.IGNORECASE),
)

WHETHER_DISJUNCTION_PATTERNS = (
    re.compile(r"\bwhether\s+you['’]?re\s+\w+(\s+\w+)*\s+or\s+\w+", re.IGNORECASE),
    re.compile(r"\bwhether\s+you\s+need\s+\w+(\s+\w+)*\s+or\s+\w+", re.IGNORECASE),
)

BULLET_LINE_PATTERN = re.compile(r"^\s*[-*•]\s+(\S+)", re.MULTILINE)
ING_VERB_PATTERN = re.compile(r"^[A-Z][a-z]*ing\b")


# ---- Result types ------------------------------------------------------------

@dataclass
class AiSignalFinding:
    code: str
    severity: str  # HIGH | MEDIUM | LOW
    excerpt: str
    suggestion: str


@dataclass
class AiSignalCheckResult:
    findings: List[AiSignalFinding] = field(default_factory=list)
    score: int = 0


# ---- Helpers -----------------------------------------------------------------

def _severity_weight(severity: str) -> int:
    return {"HIGH": 20, "MEDIUM": 10, "LOW": 5}.get(severity, 0)


def _word_count(text: str) -> int:
    return max(1, len(text.split()))


# ---- Detection functions -----------------------------------------------------

def _check_emdash(text: str):
    em_count = text.count("—")
    if em_count == 0:
        return None
    per_200 = em_count * 200 / _word_count(text)
    if per_200 >= EMDASH_PER_200_WORDS_HIGH:
        severity = "HIGH"
    elif per_200 >= EMDASH_PER_200_WORDS_MEDIUM:
        severity = "MEDIUM"
    else:
        return None
    return AiSignalFinding(
        code="AI_EMDASH_OVERUSE",
        severity=severity,
        excerpt=f"{em_count} em-dashes in {_word_count(text)} words",
        suggestion=(
            "Em-dashes are an AI-output tell when used heavily. Replace most "
            "with commas, periods, or parentheses. Humans use em-dashes "
            "sparingly (around 1 per 500 words)."
        ),
    )


def _check_overused_vocab(text: str):
    text_lower = text.lower()
    distinct_hits = set()
    for term in AI_OVERUSED_VOCAB_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", text_lower):
            distinct_hits.add(term)
    if not distinct_hits:
        return None
    severity = "HIGH" if len(distinct_hits) >= OVERUSED_VOCAB_HIGH_DISTINCT_HITS else "MEDIUM"
    return AiSignalFinding(
        code="AI_OVERUSED_VOCAB",
        severity=severity,
        excerpt=", ".join(sorted(distinct_hits)[:5]),
        suggestion=(
            "These terms are characteristic of AI-generated text. Replace with "
            "plainer alternatives: 'delve' -> 'look at', 'leverage' -> 'use', "
            "'robust' -> 'reliable', 'navigate' -> 'work through', "
            "'elevate' -> 'improve'. Specificity beats register."
        ),
    )


def _check_tricolon(text: str):
    matches = list(TRICOLON_PATTERN.finditer(text))
    if len(matches) < 2:
        return None
    # Cluster detection: are any 2 matches within the window?
    clustered = False
    for i in range(len(matches) - 1):
        if matches[i + 1].start() - matches[i].end() <= TRICOLON_CLUSTER_WINDOW_CHARS:
            clustered = True
            break
    if not clustered:
        return None
    excerpt = matches[0].group(0)[:80]
    return AiSignalFinding(
        code="AI_TRICOLON_OVERUSE",
        severity="MEDIUM",
        excerpt=excerpt,
        suggestion=(
            "AI overuses 'X, Y, and Z' parallel structures. Break the rhythm: "
            "use two items where three feels mechanical, or vary the sentence "
            "shape between adjacent bullets."
        ),
    )


def _check_rhetorical_contrast(text: str):
    for pat in RHETORICAL_CONTRAST_PATTERNS:
        m = pat.search(text)
        if m:
            return AiSignalFinding(
                code="AI_RHETORICAL_CONTRAST",
                severity="HIGH",
                excerpt=m.group(0)[:120],
                suggestion=(
                    "'It's not just X, it's Y' is a strong AI-tell. Drop the "
                    "rhetorical setup and state the substantive claim directly."
                ),
            )
    return None


def _check_transitional_overuse(text: str):
    text_lower = text.lower()
    hits = sum(text_lower.count(term) for term in TRANSITIONAL_TERMS)
    if hits < 2:
        return None
    severity = "HIGH" if hits >= TRANSITIONAL_OVERUSE_HIGH_HITS else "MEDIUM"
    return AiSignalFinding(
        code="AI_TRANSITIONAL_OVERUSE",
        severity=severity,
        excerpt=f"{hits} transitional phrases (furthermore/moreover/additionally/in conclusion)",
        suggestion=(
            "Resume and cover-letter prose rarely needs explicit transition "
            "words. Cut 'Furthermore', 'Moreover', 'Additionally', "
            "'In conclusion'. The reader sees the structure without them."
        ),
    )


def _check_present_participle_pileup(text: str):
    bullets = BULLET_LINE_PATTERN.findall(text)
    if len(bullets) < 3:
        return None
    # Find any run of 3+ consecutive bullets starting with -ing verbs
    run = 0
    max_run = 0
    for first_word in bullets:
        if ING_VERB_PATTERN.match(first_word):
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    if max_run < 3:
        return None
    return AiSignalFinding(
        code="AI_PRESENT_PARTICIPLE_PILEUP",
        severity="MEDIUM",
        excerpt=f"{max_run} consecutive bullets starting with -ing verbs",
        suggestion=(
            "Bullets that all open with -ing verbs (Crafting, Leveraging, "
            "Fostering) are a signature AI rhythm. Use past-tense action "
            "verbs (Built, Led, Shipped, Reduced) for resume bullets."
        ),
    )


def _check_hedging(text: str):
    for pat in HEDGING_PATTERNS:
        m = pat.search(text)
        if m:
            return AiSignalFinding(
                code="AI_HEDGING_PHRASE",
                severity="LOW",
                excerpt=m.group(0),
                suggestion=(
                    "'It's worth noting' / 'It's important to note' are AI "
                    "filler. Cut the phrase and state the claim directly."
                ),
            )
    return None


def _check_range_quantifier(text: str):
    for pat in RANGE_QUANTIFIER_PATTERNS:
        m = pat.search(text)
        if m:
            return AiSignalFinding(
                code="AI_RANGE_QUANTIFIER",
                severity="LOW",
                excerpt=m.group(0),
                suggestion=(
                    "'Ranging from X to Y' / 'spanning X to Y' read AI-vague. "
                    "Use specific numbers or drop the range."
                ),
            )
    return None


def _check_whether_disjunction(text: str):
    for pat in WHETHER_DISJUNCTION_PATTERNS:
        m = pat.search(text)
        if m:
            return AiSignalFinding(
                code="AI_WHETHER_DISJUNCTION",
                severity="LOW",
                excerpt=m.group(0)[:120],
                suggestion=(
                    "'Whether you're X or Y' is a marketing-copy AI tell. "
                    "Address the reader directly rather than hypothetically."
                ),
            )
    return None


# ---- Main entry --------------------------------------------------------------

def ai_signal_check(text: str) -> AiSignalCheckResult:
    """Scan text for AI-tell signals. Returns findings + 0-100 score (lower=better)."""
    result = AiSignalCheckResult()
    checks = (
        _check_emdash,
        _check_overused_vocab,
        _check_tricolon,
        _check_rhetorical_contrast,
        _check_transitional_overuse,
        _check_present_participle_pileup,
        _check_hedging,
        _check_range_quantifier,
        _check_whether_disjunction,
    )
    for check in checks:
        finding = check(text)
        if finding is not None:
            result.findings.append(finding)
    result.score = min(100, sum(_severity_weight(f.severity) for f in result.findings))
    return result
