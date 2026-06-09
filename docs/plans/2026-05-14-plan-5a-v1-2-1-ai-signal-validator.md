# Plan 5a — v1.2.1: AI-Signal Validator and De-AI Integration

<!-- readability: skip -->
<!-- Historical planning/spec document; predates the BRAINS readability standard (adopted 2026-05-29). -->

> **For implementers:** Checkbox (`- [ ]`) syntax. Work sequentially, mark steps as you go. Stage and commit after each task. **Never include third-party org or project credits in any file or commit message — BRAINS / BRAINS Trust / BRAINS Incubator only. Never include `Co-Authored-By` footers.** Conventional commits style.

**Goal:** Ship v1.2.1 patch — add an AI-signal validator that detects 9 common AI-tell patterns in text (em-dash overuse, AI-flavoured vocabulary, parallel-structure abuse, rhetorical contrasts, transitional overuse, present-participle pile-ups, hedging phrases, range quantifiers, whether-disjunctions), surfaces a 0-100 AI-signal score (lower = better), integrates into the final pre-submit `bias-check` workflow, exposes a standalone `/brains-deai` slash command, and adds optional de-AI prompts to four text-producing workflows.

**Architecture:** Same hybrid skill structure as v1.2.0 (always-loaded `SKILL.md` core + on-demand reference files + deterministic Python validators). Adds one new validator (`ai_signal_check.py`) mirroring the existing `bias_scan.py` / `integrity_check.py` pattern: pure-function entry point, structured findings, regex/keyword catalogs, no I/O. Adds one new workflow reference, one new slash command, fixtures, tests, and a smoke test.

**Tech Stack:** Unchanged — Python 3.10+, standard library `re`. No new dependencies.

**Spec reference:** [`docs/specs/2026-05-14-v1-2-1-ai-signal-validator-design.md`](../specs/2026-05-14-v1-2-1-ai-signal-validator-design.md)

**In scope for this plan:**

1. **AI-signal fixtures** — `tests/fixtures/ai_signal_fixtures.py` with synthetic strings per finding code
2. **AI-signal validator** — `scripts/validators/ai_signal_check.py` with 9-code catalog + score computation
3. **AI-signal validator tests** — `tests/validators/test_ai_signal_check.py` covering all 9 codes + score boundaries
4. **AI-signal-patterns reference** — `references/ai-signal-patterns.md` with full catalog, detection rationale, suggested rewrites + structural test
5. **/brains-deai slash command** — `commands/brains-deai.md`
6. **De-AI smoke test** — `tests/test_smoke_deai_workflow.py`
7. **Workflow integration** — auto-invocation in `bias-check.md` + optional-prompt paragraphs in `tailor.md`, `cover-letter.md`, `linkedin-improve.md`, `edit.md`
8. **Release polish** — SKILL.md router (14→15 commands), README, brand-application.md, Claude Project bundle rebuild, CHANGELOG entry
9. **Version bump + v1.2.1 git tag**

**Out of scope (deferred):**

- Streamlit dashboard (v1.3.0 — separate plan)
- Auto-rewrite of detected AI tells (validator surfaces findings; user/workflow chooses rewrite)
- LLM-based detection (deterministic regex/keyword only — no LLM call, no embeddings)
- Per-user-customisable vocabulary lists (could come in v1.4+)

---

## Conventions used throughout this plan

- **Working directory:** `c:\Brains_Resume_Skill\`. All paths relative unless absolute is shown.
- **Tests live in:** `tests/` mirroring source structure.
- **Python fixtures:** `tests/fixtures/*.py`.
- **Commit style:** conventional commits — `feat:`, `fix:`, `test:`, `docs:`, `build:`, `chore:`, `perf:`, `refactor:`. NEVER include `Co-Authored-By` footers (BRAINS-only attribution).
- **Identity-first language** throughout; no italics in body text; no third-party org or project proper-name references.
- **Testing rhythm:** write failing test → run to confirm failure → implement → run to confirm pass → commit. Don't skip the failure-confirmation step.
- **Virtual environment:** always work inside `.venv` — `.venv\Scripts\activate` (PowerShell) before running tests or scripts.

---

## Phase 1 — TDD core (Tasks 1-2)

The validator and its fixtures ship first; everything else builds on this foundation.

---

## Task 1 — AI-signal fixtures

**Files:**

- Create: `tests/fixtures/ai_signal_fixtures.py`

### Steps

- [ ] **Step 1: Write the fixture module**

Create `tests/fixtures/ai_signal_fixtures.py`:

```python
"""Synthetic text fixtures for the ai_signal_check validator tests.

Each fixture is designed to trigger or avoid a specific finding code:
  - EMDASH_HEAVY_TEXT: trips AI_EMDASH_OVERUSE (HIGH)
  - EMDASH_MILD_TEXT: trips AI_EMDASH_OVERUSE (MEDIUM)
  - OVERUSED_VOCAB_HEAVY_TEXT: 3+ distinct hits → HIGH
  - OVERUSED_VOCAB_LIGHT_TEXT: 1 hit → MEDIUM
  - TRICOLON_TEXT: 2+ "X, Y, and Z" clustered → MEDIUM
  - RHETORICAL_CONTRAST_TEXT: "It's not just X, it's Y" → HIGH
  - TRANSITIONAL_OVERUSE_TEXT: Furthermore + Moreover + Additionally → HIGH
  - PRESENT_PARTICIPLE_PILEUP_TEXT: 3+ bullets starting with -ing verbs → MEDIUM
  - HEDGING_PHRASE_TEXT: "It's worth noting" → LOW
  - RANGE_QUANTIFIER_TEXT: "ranging from X to Y" → LOW
  - WHETHER_DISJUNCTION_TEXT: "Whether you're X or Y" → LOW
  - CLEAN_HUMAN_TEXT: realistic resume bullet with zero AI tells → score 0
  - HEAVILY_AI_TEXT: kitchen-sink combining 5+ patterns → score >= 60

No real PII. All synthetic.
"""

EMDASH_HEAVY_TEXT = (
    "Built a distributed system — fast and reliable — for the platform team. "
    "Delivered results — on time, on budget — and exceeded performance targets. "
    "Mentored junior engineers — focused, deliberate work — across two quarters. "
    "Owned the migration — from concept to production — and the post-launch review."
)  # ~50 words, ~8 em-dashes → HIGH

EMDASH_MILD_TEXT = (
    "Senior engineer with eight years of experience in distributed systems and "
    "platform engineering. Built and maintained services serving 50 million daily "
    "active users — focused on reliability and observability. Mentored four junior "
    "engineers to mid-level. Led incident response across three on-call rotations. "
    "Designed and shipped the company's first internal service-level dashboard. "
    "Worked closely with product to define the platform roadmap for the next two "
    "years. Built deep expertise in OpenTelemetry, Prometheus, and incident "
    "response tooling. Comfortable with ambiguity and self-direction in unstructured "
    "problem spaces."
)  # ~90 words, 1 em-dash → no em-dash finding (under threshold)

OVERUSED_VOCAB_HEAVY_TEXT = (
    "Passionate about leveraging cutting-edge technology to deliver robust, "
    "scalable solutions. Eager to delve into complex problem spaces and embark "
    "on transformative initiatives that elevate team performance."
)  # delve + leverage + robust + elevate + embark → HIGH

OVERUSED_VOCAB_LIGHT_TEXT = (
    "Senior software engineer with experience leveraging cloud platforms to "
    "build production systems. Comfortable with on-call work and ambiguity."
)  # 1 hit ("leveraging") → MEDIUM

TRICOLON_TEXT = (
    "Designed, built, and shipped the platform. "
    "Mentored, coached, and onboarded four engineers. "
    "Tested, deployed, and monitored the migration."
)  # 3 tricolon clusters → MEDIUM

RHETORICAL_CONTRAST_TEXT = (
    "This is not just a role — it's an opportunity to shape the future. "
    "It's not just about code, it's about culture."
)  # 2 hits → HIGH

TRANSITIONAL_OVERUSE_TEXT = (
    "I deliver platform engineering work. Furthermore, I focus on reliability. "
    "Moreover, I mentor effectively. Additionally, I write clear documentation. "
    "In conclusion, I bring a comprehensive skill set."
)  # 4 hits → HIGH

PRESENT_PARTICIPLE_PILEUP_TEXT = (
    "Key responsibilities:\n"
    "- Crafting compelling product narratives.\n"
    "- Leveraging cross-functional partnerships.\n"
    "- Fostering team alignment.\n"
    "- Cultivating data-driven culture.\n"
    "- Driving platform adoption."
)  # 5 bullets starting with -ing verb → MEDIUM

HEDGING_PHRASE_TEXT = (
    "I led platform engineering at Example Corp. It's worth noting that the "
    "team grew from three to eleven engineers under my tenure."
)  # 1 hit → LOW

RANGE_QUANTIFIER_TEXT = (
    "Worked on a range of services ranging from internal tooling to "
    "customer-facing APIs spanning the full request lifecycle."
)  # 2 hits ("ranging from", "spanning") → LOW

WHETHER_DISJUNCTION_TEXT = (
    "Whether you're scaling a startup or modernising legacy infrastructure, "
    "the principles apply."
)  # 1 hit → LOW

CLEAN_HUMAN_TEXT = (
    "Senior platform engineer. Eight years at three companies, last role "
    "Example Corp (2020-2024). Built the ingestion pipeline serving 50M DAU, "
    "cut p99 latency 40 percent, trained four engineers to mid-level. "
    "Comfortable with on-call and ambiguity. Want to do similar work at a "
    "smaller team where the platform is the product."
)  # Zero AI tells → score 0

HEAVILY_AI_TEXT = (
    "Passionate senior engineer with a robust skill set, ready to delve into "
    "complex problem spaces. Whether you're scaling a startup or modernising "
    "legacy infrastructure, I bring a comprehensive approach. It's worth noting "
    "that I've led teams ranging from three to fifteen engineers, "
    "leveraging cross-functional partnerships to deliver vibrant, innovative "
    "solutions.\n\n"
    "Key strengths:\n"
    "- Crafting elegant system architectures — robust, scalable, maintainable.\n"
    "- Leveraging modern tooling — observability, automation, infrastructure-as-code.\n"
    "- Fostering team alignment — through clear communication and shared vision.\n"
    "- Cultivating engineering excellence — across the full development lifecycle.\n\n"
    "This isn't just a role, it's an opportunity. Furthermore, the opportunity "
    "extends beyond traditional engineering. Moreover, it represents a chance "
    "to embark on a transformative journey. In conclusion, I'm excited to "
    "elevate this team."
)  # Trips emdash + vocab + present-participle + rhetorical + transitional + hedging + range + whether → score >= 60
```

- [ ] **Step 2: Verify the fixtures import cleanly**

```powershell
.venv\Scripts\activate
python -c "from tests.fixtures import ai_signal_fixtures; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Confirm no test regressions**

```powershell
python -m pytest -q
```

Expected: 232 tests still pass (no new tests added — fixture module only).

- [ ] **Step 4: Commit**

```powershell
git add tests/fixtures/ai_signal_fixtures.py
git commit -m "test: add ai_signal_check fixtures with seeded text samples"
```

---

## Task 2 — AI-signal validator with full 9-code catalog (TDD)

**Files:**

- Create: `tests/validators/test_ai_signal_check.py`
- Create: `scripts/validators/ai_signal_check.py`

### Steps

- [ ] **Step 1: Write the failing tests**

Create `tests/validators/test_ai_signal_check.py`:

```python
"""Tests for scripts/validators/ai_signal_check.py — the AI-tell detector."""
from scripts.validators.ai_signal_check import ai_signal_check
from tests.fixtures import ai_signal_fixtures as fx


def _codes(result):
    return [f.code for f in result.findings]


# ---- AI_EMDASH_OVERUSE -------------------------------------------------------

def test_emdash_heavy_text_high_severity():
    r = ai_signal_check(fx.EMDASH_HEAVY_TEXT)
    em_findings = [f for f in r.findings if f.code == "AI_EMDASH_OVERUSE"]
    assert em_findings, "Expected AI_EMDASH_OVERUSE finding on heavy fixture"
    assert any(f.severity == "HIGH" for f in em_findings)


def test_emdash_mild_text_no_finding():
    """1 em-dash in 90 words is under-threshold."""
    r = ai_signal_check(fx.EMDASH_MILD_TEXT)
    assert "AI_EMDASH_OVERUSE" not in _codes(r)


# ---- AI_OVERUSED_VOCAB -------------------------------------------------------

def test_overused_vocab_heavy_text_high_severity():
    r = ai_signal_check(fx.OVERUSED_VOCAB_HEAVY_TEXT)
    vocab_findings = [f for f in r.findings if f.code == "AI_OVERUSED_VOCAB"]
    assert vocab_findings
    assert any(f.severity == "HIGH" for f in vocab_findings)


def test_overused_vocab_light_text_medium_severity():
    r = ai_signal_check(fx.OVERUSED_VOCAB_LIGHT_TEXT)
    vocab_findings = [f for f in r.findings if f.code == "AI_OVERUSED_VOCAB"]
    assert vocab_findings
    assert any(f.severity == "MEDIUM" for f in vocab_findings)


# ---- AI_TRICOLON_OVERUSE -----------------------------------------------------

def test_tricolon_text_detected():
    r = ai_signal_check(fx.TRICOLON_TEXT)
    assert "AI_TRICOLON_OVERUSE" in _codes(r)


# ---- AI_RHETORICAL_CONTRAST --------------------------------------------------

def test_rhetorical_contrast_detected_high_severity():
    r = ai_signal_check(fx.RHETORICAL_CONTRAST_TEXT)
    rc_findings = [f for f in r.findings if f.code == "AI_RHETORICAL_CONTRAST"]
    assert rc_findings
    assert any(f.severity == "HIGH" for f in rc_findings)


# ---- AI_TRANSITIONAL_OVERUSE -------------------------------------------------

def test_transitional_overuse_detected_high_on_4_plus():
    r = ai_signal_check(fx.TRANSITIONAL_OVERUSE_TEXT)
    tr_findings = [f for f in r.findings if f.code == "AI_TRANSITIONAL_OVERUSE"]
    assert tr_findings
    assert any(f.severity == "HIGH" for f in tr_findings)


# ---- AI_PRESENT_PARTICIPLE_PILEUP --------------------------------------------

def test_present_participle_pileup_detected():
    r = ai_signal_check(fx.PRESENT_PARTICIPLE_PILEUP_TEXT)
    assert "AI_PRESENT_PARTICIPLE_PILEUP" in _codes(r)


# ---- AI_HEDGING_PHRASE -------------------------------------------------------

def test_hedging_phrase_detected_low_severity():
    r = ai_signal_check(fx.HEDGING_PHRASE_TEXT)
    h_findings = [f for f in r.findings if f.code == "AI_HEDGING_PHRASE"]
    assert h_findings
    assert h_findings[0].severity == "LOW"


# ---- AI_RANGE_QUANTIFIER -----------------------------------------------------

def test_range_quantifier_detected():
    r = ai_signal_check(fx.RANGE_QUANTIFIER_TEXT)
    assert "AI_RANGE_QUANTIFIER" in _codes(r)


# ---- AI_WHETHER_DISJUNCTION --------------------------------------------------

def test_whether_disjunction_detected():
    r = ai_signal_check(fx.WHETHER_DISJUNCTION_TEXT)
    assert "AI_WHETHER_DISJUNCTION" in _codes(r)


# ---- Score boundaries --------------------------------------------------------

def test_clean_human_text_produces_zero_findings():
    r = ai_signal_check(fx.CLEAN_HUMAN_TEXT)
    assert r.findings == []
    assert r.score == 0


def test_heavily_ai_text_score_at_least_60():
    r = ai_signal_check(fx.HEAVILY_AI_TEXT)
    assert r.score >= 60


def test_score_capped_at_100():
    r = ai_signal_check(fx.HEAVILY_AI_TEXT)
    assert r.score <= 100


# ---- Result shape ------------------------------------------------------------

def test_finding_carries_excerpt_and_suggestion():
    r = ai_signal_check(fx.OVERUSED_VOCAB_HEAVY_TEXT)
    f = r.findings[0]
    assert hasattr(f, "code")
    assert hasattr(f, "severity")
    assert hasattr(f, "excerpt")
    assert hasattr(f, "suggestion")
    assert f.severity in ("HIGH", "MEDIUM", "LOW")


def test_result_has_findings_and_score_attributes():
    r = ai_signal_check(fx.CLEAN_HUMAN_TEXT)
    assert hasattr(r, "findings")
    assert hasattr(r, "score")
    assert isinstance(r.score, int)
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/validators/test_ai_signal_check.py -v
```

Expected: ImportError on `scripts.validators.ai_signal_check`.

- [ ] **Step 3: Write the implementation**

Create `scripts/validators/ai_signal_check.py`:

```python
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

EMDASH_PER_200_WORDS_MEDIUM = 1.0
EMDASH_PER_200_WORDS_HIGH = 2.0

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
    re.compile(r"\bit['']?s?\s+not\s+just\s+\w[^,.]*[,.—\-]+\s*it['']?s\s+", re.IGNORECASE),
    re.compile(r"\bthis\s+is\s+not\s+just\s+\w[^,.]*[,.—\-]+", re.IGNORECASE),
    re.compile(r"\bnot\s+only\s+\w[^,.]*\s+but\s+also\b", re.IGNORECASE),
    re.compile(r"\b\w+\s+isn['']?t\s+just\s+\w[^,.]*[,.—\-]+\s*it['']?s\s+", re.IGNORECASE),
)

TRANSITIONAL_TERMS = ("furthermore", "moreover", "additionally", "in conclusion")

HEDGING_PATTERNS = (
    re.compile(r"\bit['']?s?\s+worth\s+noting\b", re.IGNORECASE),
    re.compile(r"\bit['']?s?\s+important\s+to\s+note\b", re.IGNORECASE),
    re.compile(r"\bit\s+should\s+be\s+noted\b", re.IGNORECASE),
    re.compile(r"\bit\s+bears\s+mentioning\b", re.IGNORECASE),
)

RANGE_QUANTIFIER_PATTERNS = (
    re.compile(r"\branging\s+from\b", re.IGNORECASE),
    re.compile(r"\bspanning\s+\w+\s+to\b", re.IGNORECASE),
    re.compile(r"\bfrom\s+\w+\s+all\s+the\s+way\s+to\b", re.IGNORECASE),
)

WHETHER_DISJUNCTION_PATTERNS = (
    re.compile(r"\bwhether\s+you['']?re\s+\w+(\s+\w+)*\s+or\s+\w+", re.IGNORECASE),
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
            "plainer alternatives: 'delve' → 'look at', 'leverage' → 'use', "
            "'robust' → 'reliable', 'navigate' → 'work through', "
            "'elevate' → 'improve'. Specificity beats register."
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
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/validators/test_ai_signal_check.py -v
```

Expected: all 17 tests pass.

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 249 tests pass (232 baseline + 17 new).

- [ ] **Step 6: Commit**

```powershell
git add scripts/validators/ai_signal_check.py tests/validators/test_ai_signal_check.py
git commit -m "feat: add ai_signal_check validator with 9-code finding catalog"
```

---

## Phase 2 — References + slash command + smoke test (Tasks 3-4)

---

## Task 3 — ai-signal-patterns reference + structural test

**Files:**

- Create: `references/ai-signal-patterns.md`
- Create: `tests/references/test_ai_signal_patterns_reference.py`

### Steps

- [ ] **Step 1: Write the reference document**

Create `references/ai-signal-patterns.md` with the following content verbatim:

````markdown
# AI-Signal Patterns Reference

**Purpose:** Document the nine AI-tell patterns the `ai_signal_check` validator detects, with detection rationale and suggested rewrites. AI-tell signals are increasingly used by recruiters and ATS systems to filter applications; even without detection tools, human reviewers read these patterns as inauthenticity.

The validator surfaces findings as a 0-100 AI-signal score (lower is better). Anchor points:

- **0-9** — clean, no detectable AI tells
- **10-29** — mild traces, almost certainly fine for human review
- **30-49** — moderate AI flavour, worth a rewrite pass
- **50-79** — heavy AI signal, would likely trigger detection tools
- **80-100** — saturated, unambiguously AI-generated to most readers

---

## The nine patterns

### Pattern 1 — `AI_EMDASH_OVERUSE`

**What it detects:** More than 1 em-dash (—) per 200 words of text.

**Why it matters:** Human writers use em-dashes sparingly — typically once per 500 words or fewer. AI models, particularly recent GPT and Claude variants, average 3-5× human em-dash density. Heavy em-dash use is one of the most reliable AI tells.

**Severity:** MEDIUM at >1 per 200 words; HIGH at >2 per 200 words.

**Rewrite:** Replace most em-dashes with commas, periods, or parentheses. Reserve em-dashes for genuinely emphatic interruptions, not as a default punctuation choice.

**Example:**

- AI: "Built a system — fast and reliable — for the team. Delivered results — on time — and exceeded targets."
- Human: "Built a fast, reliable system for the team. Delivered results on time and exceeded targets."

### Pattern 2 — `AI_OVERUSED_VOCAB`

**What it detects:** Hits from a curated 18-term AI-lexicon list including delve, tapestry, vibrant, robust, leverage, navigate, embark, elevate, foster, cultivate, harness, myriad, plethora, underscore, showcase, seamless, innovative, comprehensive, holistic.

**Why it matters:** These terms appear in AI-generated text at orders-of-magnitude higher frequency than in human-authored text. They cluster together — a resume using one usually uses several.

**Severity:** MEDIUM on 1-2 distinct hits; HIGH on 3+ distinct hits.

**Rewrite:** Replace with plain alternatives. Specificity beats register.

- `delve` → `look at`, `examine`
- `leverage` → `use`
- `robust` → `reliable`
- `navigate` → `work through`
- `elevate` → `improve`
- `foster` → `support`, `build`
- `seamless` → `smooth`, drop entirely
- `comprehensive` → drop entirely or replace with the specific scope
- `innovative` → describe what is new and specific

### Pattern 3 — `AI_TRICOLON_OVERUSE`

**What it detects:** Two or more "X, Y, and Z" parallel structures clustered within 300 characters of each other.

**Why it matters:** AI loves the three-item parallel structure. Real writing varies: sometimes two items, sometimes four, sometimes a different sentence shape entirely. Repeated tricolons read mechanical.

**Severity:** MEDIUM.

**Rewrite:** Break the rhythm. Use two items where three feels habitual, or rewrite one bullet to a different structure entirely.

### Pattern 4 — `AI_RHETORICAL_CONTRAST`

**What it detects:** "It's not just X — it's Y", "It's not just X, it's Y", "Not only X but also Y", "X isn't just Y, it's Z".

**Why it matters:** This rhetorical move is a strong AI-output signature. Human writing occasionally uses it; AI writing leans on it heavily as a closer or emphasis.

**Severity:** HIGH.

**Rewrite:** Drop the rhetorical setup and state the substantive claim directly.

- AI: "This isn't just a role — it's an opportunity to shape the future."
- Human: "This role would let me shape the platform direction."

### Pattern 5 — `AI_TRANSITIONAL_OVERUSE`

**What it detects:** "Furthermore", "Moreover", "Additionally", "In conclusion" appearing two or more times in the same document.

**Why it matters:** Resume and cover-letter prose almost never needs explicit transition words. Their presence is a strong sign of AI-generated structure with overt scaffolding.

**Severity:** MEDIUM on 2-3 hits; HIGH on 4+ hits.

**Rewrite:** Cut all of them. The reader sees the structure without them.

### Pattern 6 — `AI_PRESENT_PARTICIPLE_PILEUP`

**What it detects:** Three or more consecutive bullets starting with `-ing` verbs (Crafting, Leveraging, Fostering, Cultivating, Driving).

**Why it matters:** AI defaults to gerund-led bullet rhythm. Resume convention is past-tense action verbs (Built, Led, Shipped, Reduced) for completed work, present-tense for current work — not gerunds.

**Severity:** MEDIUM.

**Rewrite:** Convert to past-tense action verbs. `Crafting compelling product narratives` → `Wrote the product narrative that drove the Q3 launch`.

### Pattern 7 — `AI_HEDGING_PHRASE`

**What it detects:** "It's worth noting", "It's important to note", "It should be noted", "It bears mentioning".

**Why it matters:** AI-output filler. Adds no information; signals lack of authorial confidence.

**Severity:** LOW.

**Rewrite:** Cut the phrase. State the claim directly.

- AI: "It's worth noting that the team grew from three to eleven engineers."
- Human: "Grew the team from three to eleven engineers."

### Pattern 8 — `AI_RANGE_QUANTIFIER`

**What it detects:** "ranging from X to Y", "spanning X to Y", "from X all the way to Y".

**Why it matters:** Range quantifiers without specific numeric bounds read AI-vague. Real resumes either give specific numbers or drop the range entirely.

**Severity:** LOW.

**Rewrite:** Replace with the specific numbers, or rewrite to focus on one end of the range.

### Pattern 9 — `AI_WHETHER_DISJUNCTION`

**What it detects:** "Whether you're X or Y", "Whether you need X or Y".

**Why it matters:** Marketing-copy AI-tell. Resume and cover letter prose should address the reader directly, not hypothetically.

**Severity:** LOW.

**Rewrite:** Rewrite to address the actual context directly.

- AI: "Whether you're scaling a startup or modernising legacy infrastructure, the principles apply."
- Human: "The platform-engineering principles I apply to startup-scale problems also work for legacy modernisation."

---

## Severity weights and score

| Severity | Weight | Notes |
|---|---|---|
| HIGH | 20 | Strong AI tell; recruiter-noticeable |
| MEDIUM | 10 | Moderate AI tell; depends on density |
| LOW | 5 | Subtle AI tell; single occurrence is fine in context |

**Score formula:** `min(100, sum(weights))`. Lower is better.

---

## How to use this reference

When the `ai_signal_check` validator surfaces findings, look up each pattern in this document for the rewrite guidance. The validator's per-finding `suggestion` field is a one-line summary; this document holds the full rationale and rewrite examples.
````

- [ ] **Step 2: Write the structural test**

Create `tests/references/test_ai_signal_patterns_reference.py`:

```python
"""Structural tests for references/ai-signal-patterns.md."""
from pathlib import Path

REFERENCE = Path(__file__).parent.parent.parent / "references" / "ai-signal-patterns.md"


def _text():
    return REFERENCE.read_text(encoding="utf-8")


def test_reference_exists():
    assert REFERENCE.exists()


def test_all_nine_finding_codes_documented():
    text = _text()
    for code in (
        "AI_EMDASH_OVERUSE",
        "AI_OVERUSED_VOCAB",
        "AI_TRICOLON_OVERUSE",
        "AI_RHETORICAL_CONTRAST",
        "AI_TRANSITIONAL_OVERUSE",
        "AI_PRESENT_PARTICIPLE_PILEUP",
        "AI_HEDGING_PHRASE",
        "AI_RANGE_QUANTIFIER",
        "AI_WHETHER_DISJUNCTION",
    ):
        assert code in text, f"Finding code not documented: {code}"


def test_severity_weights_documented():
    text = _text()
    assert "HIGH" in text
    assert "MEDIUM" in text
    assert "LOW" in text
    assert "20" in text  # HIGH weight
    assert "10" in text  # MEDIUM weight


def test_score_anchor_points_present():
    text = _text()
    for anchor in ("0-9", "10-29", "30-49", "50-79", "80-100"):
        assert anchor in text


def test_lower_is_better_explicit():
    text = _text().lower()
    assert "lower is better" in text
```

- [ ] **Step 3: Run tests**

```powershell
python -m pytest tests/references/test_ai_signal_patterns_reference.py -v
```

Expected: 5 tests pass.

- [ ] **Step 4: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 254 tests pass (249 + 5).

- [ ] **Step 5: Commit**

```powershell
git add references/ai-signal-patterns.md tests/references/test_ai_signal_patterns_reference.py
git commit -m "docs: add ai-signal-patterns reference with full catalog and rewrites"
```

---

## Task 4 — /brains-deai slash command + smoke test

**Files:**

- Create: `commands/brains-deai.md`
- Create: `tests/test_smoke_deai_workflow.py`

### Steps

- [ ] **Step 1: Create the slash command file**

Create `commands/brains-deai.md`:

```markdown
---
description: Scan resume, cover letter, or LinkedIn text for AI-tell signals and produce a de-AI report with rewrite suggestions
argument-hint: [optional: file path to a .docx/.pdf/.md/.txt file; otherwise paste text in chat]
---

Run the BRAINS Resume Skill AI-signal check. Load `~/.claude/skills/brains-resume/references/ai-signal-patterns.md` for the full pattern catalog and rewrite guidance. Input source: `$ARGUMENTS` (a file path) or pasted text in the next message.

## Procedure

1. **Acquire text.** If a file path is provided, extract text via `scripts/parsers/docx_to_text.py` (DOCX) or `scripts/parsers/pdf_to_text.py` (PDF). If pasted, use as-is. Markdown and plain text use the raw content.

2. **Run the validator.**

```python
from scripts.validators.ai_signal_check import ai_signal_check
result = ai_signal_check(text)
```text

3. **Present the report.**

   - Lead with the score: "AI-signal score: {result.score}/100" with the anchor-point interpretation from `references/ai-signal-patterns.md` (0-9 clean, 10-29 mild, 30-49 moderate, 50-79 heavy, 80-100 saturated).
   - For each finding, show the code, severity, excerpt, and suggestion.
   - For each finding code present, link to the matching section in `references/ai-signal-patterns.md` for the full rewrite guidance.

4. **Offer next steps.**

   - If the score is below 10: confirm the text reads as human-authored; no action needed.
   - If 10-29: surface the findings but state that the score is low enough that revision is optional.
   - If 30+: walk the user through the highest-severity findings first, offering rewrite suggestions one at a time. Do not auto-rewrite — the user always chooses.

5. **Output artifact (optional).** If the user requests a saved report, write to `output/deai-report-YYYY-MM-DD-HHMMSS.md` as a BRAINS coaching artifact.

## Safeguarding boundaries

- **The validator scans skill-produced text or user-supplied text.** It is not used as a covert AI-detection tool on third-party content.
- **No auto-rewrite.** Findings are suggestions; the user decides what to change.
- **Lower scores are not a guarantee.** The validator detects pattern density, not authorship; a low score does not certify human authorship to a recruiter using detection tools.

```

- [ ] **Step 2: Write the smoke test**

Create `tests/test_smoke_deai_workflow.py`:

```python
"""Smoke test for the deterministic portion of the de-AI workflow.

Exercises: ai_signal_check runs end-to-end on a heavily-AI fixture, score is
non-zero, findings have the expected fields, and a markdown report artifact
can be written without crashing.
"""
from pathlib import Path

from scripts.validators.ai_signal_check import ai_signal_check
from tests.fixtures import ai_signal_fixtures as fx


def test_deai_smoke(tmp_path):
    # (a) Scan a heavily-AI fixture
    result = ai_signal_check(fx.HEAVILY_AI_TEXT)
    assert result.score > 0
    assert result.score >= 60  # heavily-AI fixture should be solidly in the "heavy" band
    assert len(result.findings) >= 4

    # (b) Each finding has the public-API shape
    for f in result.findings:
        assert f.code
        assert f.severity in ("HIGH", "MEDIUM", "LOW")
        assert f.excerpt
        assert f.suggestion

    # (c) Render a markdown report (what the slash command will do at runtime)
    lines = [
        "# De-AI Report\n\n",
        f"**AI-signal score:** {result.score}/100\n\n",
        f"**Findings:** {len(result.findings)}\n\n",
        "---\n\n",
    ]
    for f in result.findings:
        lines.append(f"### {f.code} ({f.severity})\n\n")
        lines.append(f"**Excerpt:** {f.excerpt}\n\n")
        lines.append(f"**Suggestion:** {f.suggestion}\n\n")
    report = tmp_path / "deai-report-2026-05-14-120000.md"
    report.write_text("".join(lines), encoding="utf-8")

    assert report.exists()
    content = report.read_text(encoding="utf-8")
    assert "De-AI Report" in content
    assert "AI-signal score" in content


def test_deai_smoke_clean_text_zero_score(tmp_path):
    """A clean human-written fixture should produce zero findings and zero score."""
    result = ai_signal_check(fx.CLEAN_HUMAN_TEXT)
    assert result.score == 0
    assert result.findings == []
```

- [ ] **Step 3: Run the smoke test**

```powershell
python -m pytest tests/test_smoke_deai_workflow.py -v
```

Expected: 2 tests pass.

- [ ] **Step 4: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 256 tests pass (254 + 2).

- [ ] **Step 5: Commit**

```powershell
git add commands/brains-deai.md tests/test_smoke_deai_workflow.py
git commit -m "feat: add brains-deai slash command and smoke test"
```

---

## Phase 3 — Integration (Task 5)

---

## Task 5 — Workflow integration (bias-check auto + 4 optional prompts)

**Files:**

- Modify: `references/workflows/bias-check.md` (auto-invocation step)
- Modify: `references/workflows/tailor.md` (optional prompt paragraph)
- Modify: `references/workflows/cover-letter.md` (optional prompt paragraph)
- Modify: `references/workflows/linkedin-improve.md` (optional prompt paragraph)
- Modify: `references/workflows/edit.md` (optional prompt paragraph)
- Create: `tests/references/test_workflow_deai_integration.py`

### Steps

- [ ] **Step 1: Update `references/workflows/bias-check.md` with auto-invocation**

Read the file first to find the section that runs `bias_scan` and `integrity_check`. Insert this paragraph at the equivalent step (the section that runs the validators on extracted text):

```markdown
**De-AI signal check (auto).** After bias_scan and integrity_check, also run the AI-signal check:

```python
from scripts.validators.ai_signal_check import ai_signal_check
ai_signal = ai_signal_check(text)
```text

Surface the AI-signal score numerically (e.g. "AI-signal score: 18/100 (mild traces — likely fine)") alongside the bias and integrity findings. If score >= 30, surface the top three findings with their suggestions; link to `references/ai-signal-patterns.md` for full rewrite guidance. Findings are coaching — the user decides whether to revise.

```

- [ ] **Step 2: Add optional-prompt paragraph to four other workflow files**

For each of `tailor.md`, `cover-letter.md`, `linkedin-improve.md`, `edit.md`, find a sensible insertion point near the end of the workflow (typically before any "Output artifacts" or "Next steps" section, after the artifact-saved step).

Insert this paragraph verbatim in each of the four files:

```markdown
**De-AI check (optional).** Before saving the final output, optionally run the AI-signal validator:

```python
from scripts.validators.ai_signal_check import ai_signal_check
score = ai_signal_check(produced_text).score
```text

If the score is above 30, surface the top three findings with rewrite suggestions and offer to revise. The user can decline — this is coaching, not gating. See `references/ai-signal-patterns.md` for the full pattern catalog.

```

(Do NOT remove or rewrite existing content in these files. Just add the paragraph.)

- [ ] **Step 3: Create the integration test**

Create `tests/references/test_workflow_deai_integration.py`:

```python
"""Verify the four text-producing workflows now mention the de-AI check."""
from pathlib import Path

REF_DIR = Path(__file__).parent.parent.parent / "references" / "workflows"


WORKFLOWS_THAT_MUST_MENTION_DEAI = (
    "bias-check.md",
    "tailor.md",
    "cover-letter.md",
    "linkedin-improve.md",
    "edit.md",
)


def test_all_five_workflows_mention_ai_signal_check():
    for fname in WORKFLOWS_THAT_MUST_MENTION_DEAI:
        text = (REF_DIR / fname).read_text(encoding="utf-8")
        assert "ai_signal_check" in text, (
            f"{fname} does not invoke ai_signal_check"
        )


def test_bias_check_runs_deai_automatically():
    """bias-check should auto-invoke ai_signal_check (not just mention it as optional)."""
    text = (REF_DIR / "bias-check.md").read_text(encoding="utf-8")
    assert "auto" in text.lower() or "automatically" in text.lower()


def test_four_workflows_offer_optional_deai():
    """tailor, cover-letter, linkedin-improve, edit — all four should describe de-AI as optional."""
    for fname in ("tailor.md", "cover-letter.md", "linkedin-improve.md", "edit.md"):
        text = (REF_DIR / fname).read_text(encoding="utf-8")
        assert "De-AI check (optional)" in text or "(optional)" in text


def test_ai_signal_patterns_reference_cross_linked():
    for fname in WORKFLOWS_THAT_MUST_MENTION_DEAI:
        text = (REF_DIR / fname).read_text(encoding="utf-8")
        assert "ai-signal-patterns.md" in text
```

- [ ] **Step 4: Run tests**

```powershell
python -m pytest tests/references/test_workflow_deai_integration.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 260 tests pass (256 + 4).

- [ ] **Step 6: Commit**

```powershell
git add references/workflows/bias-check.md references/workflows/tailor.md references/workflows/cover-letter.md references/workflows/linkedin-improve.md references/workflows/edit.md tests/references/test_workflow_deai_integration.py
git commit -m "feat: integrate ai_signal_check into bias-check (auto) and four text-producing workflows (optional)"
```

---

## Phase 4 — Release polish (Tasks 6-7)

---

## Task 6 — Docs + bundle rebuild

**Files:**

- Modify: `SKILL.md` (router + slash-command count)
- Modify: `README.md` (slash-command list)
- Modify: `references/brand-application.md` (split-rule table)
- Modify: `CHANGELOG.md` (v1.2.1 entry)
- Modify: `docs/claude-project-setup.md` (workflow count + new reference doc)
- Rebuild: `dist/brains-resume-claude-project.zip`

### Steps

- [ ] **Step 1: Update SKILL.md**

Read SKILL.md first. Three edits:

**A.** Add to the Tooling Notes section (near where bias_scan and integrity_check are documented), a new bullet:

```markdown
- **AI-signal validator** — `scripts/validators/ai_signal_check.py` detects nine common AI-tell patterns in text (em-dash overuse, AI-flavoured vocabulary, parallel-structure abuse, rhetorical contrasts, transitional overuse, present-participle pile-ups, hedging phrases, range quantifiers, whether-disjunctions). Returns a 0-100 AI-signal score (lower = better). Auto-invoked in the `bias-check` workflow; optional in `tailor`, `cover-letter`, `linkedin-improve`, `edit`; standalone via `/brains-deai`. Full pattern catalog: `references/ai-signal-patterns.md`.
```

**B.** Update the slash-command-list sentence. Find:

> "Type `/brains-` and Claude Code will list the fourteen commands: review, disclosure, edit, tailor, cover-letter, create, linkedin, linkedin-improve, consolidate, jd-analyze, precheck, track, career-change, check."

Replace with:

> "Type `/brains-` and Claude Code will list the fifteen commands: review, disclosure, edit, tailor, cover-letter, create, linkedin, linkedin-improve, consolidate, jd-analyze, precheck, track, deai, career-change, check."

**C.** Both "All fourteen workflows are live" phrasings stay — `/brains-deai` is a TOOL not a workflow (it doesn't have a full workflow reference; it's a thin slash command wrapping the validator). Do NOT change "fourteen workflows" to "fifteen workflows" anywhere.

- [ ] **Step 2: Update README.md**

Read README.md. Two edits:

**A.** Add one new slash-command entry (placement should match existing ordering):

```markdown
- `/brains-deai` — Scan resume / cover-letter / LinkedIn text for AI-tell signals; surfaces a 0-100 AI-signal score and rewrite suggestions
```

**B.** Update any "fourteen commands" mention to "fifteen commands". If the version line at top mentions a version, optionally update to:

```markdown
v1.2.1 — adds the de-AI validator; fourteen workflows live (de-AI is a tool, not a workflow).
```

- [ ] **Step 3: Update references/brand-application.md**

In Section 1 (The Split Rule) table, add one new row after the existing JD-analyzer / precheck-summary rows:

```markdown
| De-AI report (saved to `output/`) | **BRAINS branded** — coaching artifact frame; identity-first language | Internal coaching artifact, same category as the bias-scan and ATS coaching reports |
```

- [ ] **Step 4: Update docs/claude-project-setup.md**

Find the "Workflows available on claude.ai" section. Below it (or in a suitable nearby spot), add a sub-section:

```markdown
### De-AI tool (v1.2.1+)

The skill includes an AI-signal validator (`/brains-deai`) that scans produced text for common AI-tell patterns and surfaces a 0-100 score with rewrite suggestions. Auto-runs in the bias-aware final check; available standalone. See `references/ai-signal-patterns.md` for the nine-pattern catalog.
```

If the file mentions the workflow count anywhere, leave it at fourteen — de-AI is a tool, not a fifteenth workflow.

- [ ] **Step 5: Update CHANGELOG.md**

At the top of `CHANGELOG.md`, above the v1.2.0 entry, add:

```markdown
## [1.2.1] — 2026-05-14

### Added
- **AI-signal validator** (`scripts/validators/ai_signal_check.py`) — detects nine common AI-tell patterns in text: em-dash overuse, AI-flavoured vocabulary, parallel-structure abuse, rhetorical contrasts, transitional overuse, present-participle pile-ups, hedging phrases, range quantifiers, whether-disjunctions. Returns a 0-100 AI-signal score (lower = fewer AI tells).
- **AI-signal-patterns reference** (`references/ai-signal-patterns.md`) — full pattern catalog with detection rationale, severity calibration, and per-pattern rewrite guidance.
- **`/brains-deai` slash command** — standalone scanner that produces a markdown de-AI report with score + per-finding suggestions.

### Changed
- **`bias-check` workflow** — now auto-invokes the AI-signal validator alongside ATS, bias, and integrity checks. The final pre-submit pass surfaces the AI-signal score and top findings.
- **`tailor`, `cover-letter`, `linkedin-improve`, `edit` workflows** — gain an optional end-of-workflow de-AI prompt; if the score is above 30, the workflow surfaces the top three findings with rewrite suggestions before saving.
- **`references/brand-application.md`** — split-rule table extended to cover the de-AI report artifact type.
- **`README.md` and `SKILL.md`** — slash-command list updated (14 → 15 commands; de-AI is a tool, not a workflow).
- **Claude Project bundle** — rebuilt to include `references/ai-signal-patterns.md`.
```

- [ ] **Step 6: Rebuild the Claude Project bundle**

```powershell
.venv\Scripts\activate
python scripts\packaging\build_project_bundle.py
```

Expected: prints `Wrote ...\dist\brains-resume-claude-project.zip`.

- [ ] **Step 7: Verify the new reference is in the bundle**

```powershell
python -c "import zipfile; z = zipfile.ZipFile('dist/brains-resume-claude-project.zip'); names = z.namelist(); print('ai-signal-patterns:', 'brains-resume-claude-project/references/ai-signal-patterns.md' in names)"
```

Expected: `True`.

- [ ] **Step 8: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 260 tests still pass (no new tests in this task — pure docs/build).

- [ ] **Step 9: Commit**

```powershell
git add SKILL.md README.md references/brand-application.md docs/claude-project-setup.md CHANGELOG.md
git commit -m "docs: update SKILL.md, README, brand-application, and CHANGELOG for v1.2.1"
```

(The dist/zip is gitignored — verify `git status` shows clean working tree after the commit. If `dist/brains-resume-claude-project.zip` shows as untracked, that's fine — it's excluded by `.gitignore`. If `dist/` shows as a directory that needs adding to .gitignore, double-check that .gitignore already has the `dist/*` pattern.)

---

## Task 7 — Version bump + v1.2.1 tag

**Files:**

- Modify: `SKILL.md` (frontmatter `version` + body version reference)
- Modify: `pyproject.toml`

### Steps

- [ ] **Step 1: Bump SKILL.md frontmatter**

In `SKILL.md`, find the frontmatter block:

```yaml
---
name: brains-resume
description: ...
version: 1.2.0
license: MIT
---
```

Change `version: 1.2.0` to `version: 1.2.1`.

- [ ] **Step 2: Update body version reference**

In `SKILL.md`, find:

> "This is a BRAINS Incubator project, v1.2.0."

Update to:

> "This is a BRAINS Incubator project, v1.2.1."

- [ ] **Step 3: Bump pyproject.toml**

In `pyproject.toml`, find:

```toml
version = "1.2.0"
```

Change to:

```toml
version = "1.2.1"
```

- [ ] **Step 4: Run the full suite one final time**

```powershell
.venv\Scripts\activate
python -m pytest -q
```

Expected: 260 tests pass, all green.

- [ ] **Step 5: Commit the version bump**

```powershell
git add SKILL.md pyproject.toml
git commit -m "chore: bump version to 1.2.1"
```

- [ ] **Step 6: Create the v1.2.1 tag**

```powershell
git tag -a v1.2.1 -m "v1.2.1 - AI-signal validator and de-AI integration"
```

Use a hyphen (not em dash) in the tag message to avoid PowerShell shell-escape issues.

- [ ] **Step 7: Verify the tag**

```powershell
git tag --list
git show v1.2.1 --stat
```

Expected: `v1.2.1` appears in the tag list; `git show v1.2.1` displays the chore commit + version-bump file changes.

- [ ] **Step 8: Final status check**

```powershell
git status
git log --oneline -10
```

Expected: working tree clean. The last 7-8 commits trace the Plan 5a work. Most recent commit is `chore: bump version to 1.2.1`. Tag points at that commit.

Do NOT push to remote — the plan does not push. When ready, the user pushes with `git push && git push --tags`.

---

## Plan completion checklist

After all 7 tasks are marked complete, verify:

- [ ] All 7 tasks have every step checked off.
- [ ] `python -m pytest -q` reports 260 tests green (232 baseline + 28 new).
- [ ] `git tag --list` includes `v1.2.1`.
- [ ] `dist/brains-resume-claude-project.zip` was rebuilt and contains `references/ai-signal-patterns.md`.
- [ ] No commits include `Co-Authored-By` footers.
- [ ] No third-party org/project proper-name attribution appears in any committed file or commit message.
- [ ] `SKILL.md` frontmatter says `version: 1.2.1`.
- [ ] `pyproject.toml` says `version = "1.2.1"`.
- [ ] `commands/brains-deai.md` exists.
- [ ] `references/ai-signal-patterns.md` exists with all 9 finding codes documented.
- [ ] `scripts/validators/ai_signal_check.py` exists with the 9-code finding catalog and `ai_signal_check(text) -> AiSignalCheckResult` public API.
- [ ] The four text-producing workflows (`tailor.md`, `cover-letter.md`, `linkedin-improve.md`, `edit.md`) contain the "De-AI check (optional)" paragraph.
- [ ] `bias-check.md` contains the auto-invocation step for `ai_signal_check`.

When every box is ticked, v1.2.1 is shippable.
