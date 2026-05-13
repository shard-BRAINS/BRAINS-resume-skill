# v1.2.1 — AI-Signal Validator and De-AI Integration — Design Specification

**Version:** Draft v1
**Date:** 2026-05-14
**Status:** Awaiting user review
**Target release:** v1.2.1 (patch)
**Builds on:** v1.2.0 (tracker data layer, JD analyzer, pre-application check shipped)
**Successor:** Phase 5 / v1.3.0 — Streamlit dashboard (separate spec; consumes the AI-signal score this release ships)

---

## 1. Purpose

Strip AI-tell signals from text the skill produces (resume content, cover letters, LinkedIn profile output). The motivation is practical:

- AI-detection tools (GPTZero, Pangram, Originality.ai) are now used by a non-trivial subset of recruiters and ATS systems
- Even without detection tools, human reviewers increasingly recognise AI-tell patterns and read them as inauthenticity
- The skill currently has no defence against producing AI-sounding text — every workflow that emits prose risks dropping these signals

This release adds a deterministic validator that detects nine common AI-tell categories, surfaces them as structured findings (mirroring `bias_scan` and `integrity_check`), and integrates the validator into the final pre-submit `bias-check` workflow and as a standalone slash command. It also surfaces the score as a quality metric that the v1.3.0 dashboard will consume.

## 2. Scope

### In scope for v1.2.1

1. **AI-signal validator** — `scripts/validators/ai_signal_check.py` with 9-code finding catalog and 0-100 AI-signal score
2. **AI-signal-patterns reference** — `references/ai-signal-patterns.md` with full catalog, detection rationale, suggested rewrites
3. **De-AI standalone slash command** — `commands/brains-deai.md`
4. **AI-signal fixtures** — `tests/fixtures/ai_signal_fixtures.py` with seeded text strings per finding code
5. **AI-signal tests** — `tests/validators/test_ai_signal_check.py`
6. **Integration into existing workflows** — `bias-check.md` (auto), plus optional prompts in `tailor.md`, `cover-letter.md`, `linkedin-improve.md`, `edit.md`
7. **SKILL.md router** — add the new slash command; bump command count 14 → 15
8. **README, brand-application, CHANGELOG, Claude Project bundle, v1.2.1 tag**

### Out of scope (deferred to v1.3.0 or later)

- Streamlit dashboard (v1.3.0)
- Auto-rewrite of detected AI tells (the validator surfaces findings; the user or workflow chooses the rewrite)
- LLM-based detection (deterministic regex/keyword catalog only — no LLM call, no embeddings)
- Per-user-customisable vocabulary lists (could come in v1.4+)
- Time-series trending of AI-signal scores across a user's resume history (dashboard concern, v1.3.0)

### Decision ledger

| # | Decision | Choice | Rationale |
|---|---|---|---|
| AI-Q1 | Detection approach | Deterministic regex + keyword catalogs | Same pattern as existing validators; no LLM dependency; fast; auditable |
| AI-Q2 | Score direction | Lower = better (fewer AI tells) | Matches user mental model; the goal is to reduce signals |
| AI-Q3 | Score formula | `min(100, sum(severity_weight))` where HIGH=20, MEDIUM=10, LOW=5 | Calibrated so a clean resume scores 0; a mildly AI-flavoured one scores 10-30; a heavily AI-generated one scores 50+ |
| AI-Q4 | Integration model | Auto in `bias-check`, optional in 4 text-producing workflows, standalone via `/brains-deai` | Final-submit gate is the hard checkpoint; earlier workflows produce drafts where some AI vocabulary may be intentional |
| AI-Q5 | Em-dash threshold | More than 1 em-dash per 200 words triggers HIGH | Humans use em-dashes sparingly; AI averages 3-5× human rate. Calibrated against typical resume lengths (400-1500 words) |
| AI-Q6 | Vocabulary list source | Hand-curated list of 18 high-signal terms | Avoids the false-positive problem of large auto-generated lists; covers the well-documented AI lexicon (delve, tapestry, leverage, robust, navigate, etc.) |
| AI-Q7 | Custom vocab override | Not in scope for v1.2.1 | YAGNI for first release; can add `profile.json` field later if user feedback warrants |
| AI-Q8 | Output-only scanning | Yes — only scans skill-produced text | The validator is not used to detect AI in user-pasted input (that would be inappropriate paranoia) |

## 3. Architecture

Same pattern as the three existing validators (`ats_check.py`, `bias_scan.py`, `integrity_check.py`, `jd_analyzer.py`):

- Pure-function entry point: `ai_signal_check(text: str) -> AiSignalCheckResult`
- Structured findings via dataclass
- No I/O, no DB access, no network
- Regex/keyword catalogs at module top, easy to audit and extend

### File additions

```
scripts/validators/
└── ai_signal_check.py              # NEW — 9-code catalog + score

references/
└── ai-signal-patterns.md           # NEW — full catalog with examples + rewrites

commands/
└── brains-deai.md                  # NEW standalone slash command

tests/fixtures/
└── ai_signal_fixtures.py           # NEW — synthetic strings per finding code

tests/validators/
└── test_ai_signal_check.py         # NEW
```

### Updates

- `references/workflows/bias-check.md` — add ai_signal_check invocation step + finding presentation
- `references/workflows/tailor.md`, `cover-letter.md`, `linkedin-improve.md`, `edit.md` — add optional "run de-AI pass before saving?" prompt paragraph
- `SKILL.md` — frontmatter `version: 1.2.1`; tooling-notes section gets ai_signal_check entry; slash-command list 14 → 15
- `references/brand-application.md` — new artifact type (ai-signal check report) covered by unbranded-vs-branded rule (BRAINS-branded — internal coaching artifact)
- `README.md` — slash-command list entry
- `pyproject.toml` — version 1.2.0 → 1.2.1
- `CHANGELOG.md` — v1.2.1 entry
- `docs/claude-project-setup.md` — workflow count + new reference doc
- Claude Project bundle rebuild

## 4. Finding catalog detail

### 4.1 The 9 codes

| Code | Description | Detection | Severity |
|---|---|---|---|
| `AI_EMDASH_OVERUSE` | More than 1 em-dash per 200 words | Count `—` characters; divide by `word_count / 200`; flag if ratio > 1 | HIGH (if ratio > 2), MEDIUM (if 1-2) |
| `AI_OVERUSED_VOCAB` | Hits from curated 18-word AI-lexicon list | Case-insensitive substring match | HIGH (3+ distinct hits), MEDIUM (1-2 distinct hits) |
| `AI_TRICOLON_OVERUSE` | Two or more "X, Y, and Z" parallel structures within 300 chars | Regex for `\w+, \w+,? and \w+`; cluster detection | MEDIUM |
| `AI_RHETORICAL_CONTRAST` | "It's not just X — it's Y" / "Not only X but also Y" / "X isn't just Y, it's Z" | Multi-pattern regex | HIGH |
| `AI_TRANSITIONAL_OVERUSE` | "In conclusion", "Furthermore", "Moreover", "Additionally" appearing 2+ times in same document | Keyword count | MEDIUM (2-3 hits), HIGH (4+) |
| `AI_PRESENT_PARTICIPLE_PILEUP` | Three or more consecutive bullets starting with `-ing` verbs | Bullet-line regex with sequential-pattern detection | MEDIUM |
| `AI_HEDGING_PHRASE` | "It's worth noting", "It's important to note", "It should be noted", "It bears mentioning" | Keyword match | LOW |
| `AI_RANGE_QUANTIFIER` | "ranging from X to Y", "spanning X to Y", "from X all the way to Y" without specific numeric bounds | Regex match | LOW |
| `AI_WHETHER_DISJUNCTION` | "Whether you're X or Y", "Whether you need X or Y" | Regex match | LOW |

### 4.2 Vocabulary list (AI_OVERUSED_VOCAB)

Curated list of 18 terms, drawn from documented AI-output lexicons. Calibrated so common resume vocabulary (`led`, `built`, `shipped`, `delivered`, `reduced`) does NOT match — only the AI-distinctive registers do.

```python
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
```

Each conjugation listed separately so the validator catches "delving into X" as readily as "delve into X."

### 4.3 Score calculation

```python
def _severity_weight(severity: str) -> int:
    return {"HIGH": 20, "MEDIUM": 10, "LOW": 5}.get(severity, 0)

def _compute_score(findings: list) -> int:
    return min(100, sum(_severity_weight(f.severity) for f in findings))
```

Lower is better. Anchor points:

- **0-9** — clean, no detectable AI tells
- **10-29** — mild traces, almost certainly fine for human review
- **30-49** — moderate AI flavour, worth a rewrite pass
- **50-79** — heavy AI signal, would likely trigger detection tools
- **80-100** — saturated, unambiguously AI-generated to most readers

### 4.4 Public API

```python
# scripts/validators/ai_signal_check.py

@dataclass
class AiSignalFinding:
    code: str
    severity: str  # HIGH | MEDIUM | LOW
    excerpt: str
    suggestion: str

@dataclass
class AiSignalCheckResult:
    findings: List[AiSignalFinding]
    score: int  # 0-100, lower = better

def ai_signal_check(text: str) -> AiSignalCheckResult:
    """Scan text for AI-tell signals. Returns structured findings + score."""
```

## 5. Integration

### 5.1 Auto-invocation in `bias-check`

The final pre-submit pass adds `ai_signal_check` alongside `ats_check`, `bias_scan`, and `integrity_check`. Workflow reference updated to:

1. Run ats_check on the DOCX
2. Extract text via `docx_to_text` or `pdf_to_text`
3. Run `bias_scan(text)`, `integrity_check(text)`, **`ai_signal_check(text)` (NEW)**
4. Compile findings into the coaching report

Findings presented with category prefix so the user sees them grouped. AI-signal score surfaced numerically: "AI-signal score: 18/100 (mild traces — likely fine)."

### 5.2 Optional prompt in 4 text-producing workflows

`tailor.md`, `cover-letter.md`, `linkedin-improve.md`, `edit.md` each gain a single end-of-workflow paragraph:

> **De-AI check (optional).** Before saving the final output, optionally run `ai_signal_check` on the produced text. If the score is above 30, surface the top 3 findings with rewrite suggestions and offer to revise. The user can decline; this is coaching, not gating.

### 5.3 Standalone `/brains-deai` slash command

`commands/brains-deai.md`:

```yaml
---
description: Scan a resume, cover letter, or LinkedIn text for AI-tell signals and produce a de-AI report
argument-hint: [optional: file path; otherwise paste text]
---
```

Workflow: load text → run `ai_signal_check` → render report with score + per-finding suggestions. No new reference file needed beyond `ai-signal-patterns.md` (which the slash command body links to for the rewrite catalog).

## 6. Testing

Same TDD discipline as Plan 4.

### 6.1 Fixtures (`tests/fixtures/ai_signal_fixtures.py`)

One synthetic string per finding code, designed to trigger exactly that finding:

- `EMDASH_HEAVY_TEXT` — 5 em-dashes in 300 words → HIGH
- `OVERUSED_VOCAB_TEXT` — uses "delve", "tapestry", "robust" → HIGH (3 distinct hits)
- `OVERUSED_VOCAB_LIGHT_TEXT` — uses "leverage" once → MEDIUM
- `TRICOLON_TEXT` — three "X, Y, and Z" structures clustered
- `RHETORICAL_CONTRAST_TEXT` — "It's not just X, it's Y" twice
- `TRANSITIONAL_OVERUSE_TEXT` — "Furthermore" + "Moreover" + "Additionally"
- `PRESENT_PARTICIPLE_PILEUP_TEXT` — 4 bullets starting with `-ing` verbs
- `HEDGING_PHRASE_TEXT` — "It's worth noting" + "It's important to note"
- `RANGE_QUANTIFIER_TEXT` — "ranging from X to Y"
- `WHETHER_DISJUNCTION_TEXT` — "Whether you're X or Y"
- `CLEAN_HUMAN_TEXT` — typical resume bullet that should produce zero findings
- `HEAVILY_AI_TEXT` — kitchen-sink combining 5+ patterns → score ≥ 60

### 6.2 Tests (`tests/validators/test_ai_signal_check.py`)

One test per finding code (asserts the code fires on the matching fixture, does not fire on clean text), plus:

- `test_clean_human_text_produces_zero_findings`
- `test_score_is_zero_on_clean_text`
- `test_score_is_high_on_heavily_ai_text`
- `test_findings_carry_excerpt_and_suggestion`

Plus a `tests/test_smoke_deai_workflow.py` end-to-end smoke test that scans a fixture and writes a markdown report.

Expected test count delta: ~15-18 new tests. Suite goes from 232 → ~250.

## 7. Privacy and brand

Privacy unchanged — validator is pure-function, no I/O, no network. Findings are returned to the caller; persistence depends entirely on the calling workflow.

Brand-application rule extended in §1 split-rule table:

| New artifact | Branded? |
|---|---|
| AI-signal-check report (saved to `output/`) | BRAINS-branded — coaching artifact, same category as bias-scan reports |
| In-chat AI-signal score display | BRAINS coaching frame |

## 8. Release plan

Single tag at end: **v1.2.1**.

- All 232 existing tests stay green
- ~15-18 new tests
- CHANGELOG v1.2.1 entry under "Added" + "Changed" headings
- README updated with the new slash command
- `references/brand-application.md` extended
- Claude Project bundle rebuilt to include `references/ai-signal-patterns.md`
- `v1.2.1` git tag

## 9. Implementation phasing

The implementation plan (separate document, produced via `writing-plans`) will sequence as:

1. **AI-signal fixtures + validator + tests** (TDD core)
2. **References (`ai-signal-patterns.md`) + slash command + smoke test**
3. **Integration** — update `bias-check.md` (auto) + 4 optional-prompt workflow refs
4. **Release polish** — SKILL.md router, README, brand-application, CHANGELOG, bundle, version bump, tag

Estimated **7 tasks** across these four implementation phases. Comparable in size to a typical patch release.

---

**Points worth a second look during spec review:**

- The **em-dash threshold (1 per 200 words)** may be too aggressive for some writing styles. Implementation should expose it as a module-level constant so it can be tuned without code surgery if the user finds it noisy.
- The **18-word vocabulary list** is opinionated. If you'd like additions or removals (e.g. you'd argue "robust" or "comprehensive" is acceptable in technical resume contexts), say so before the plan ships.
- The **integration in 4 text-producing workflows** is optional-prompt, not auto. If you'd rather make it auto everywhere, easy change. I chose optional because drafts in `tailor`/`edit` sometimes need rough text the user will refine, and the final-submit gate (`bias-check`) is the hard checkpoint.
