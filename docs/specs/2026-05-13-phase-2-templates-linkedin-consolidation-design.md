# Phase 2 — Templates, LinkedIn Profile, and Consolidation — Design Specification

<!-- readability: skip -->
<!-- Historical planning/spec document; predates the BRAINS readability standard (adopted 2026-05-29). -->

**Version:** Draft v1
**Date:** 2026-05-13
**Status:** Awaiting user review
**Target release:** v1.1.0
**Builds on:** v1.0.2 (Plan 1 + Plan 2 — nine workflows shipped, install scripts, slash commands, Claude Project bundle)
**Brand routing:** Unchanged from v1 (BRAINS parent on user-facing surfaces; Incubator origin credit; Trust footer credit on disclosure surfaces)

---

## 1. Purpose

Extend the BRAINS Resume Skill with three capabilities deferred from v1:

1. A **template library** so users can choose a resume / cover-letter layout that fits their situation (career-change, gap-friendly, executive, etc.) rather than being locked to a single chronological layout.
2. A **LinkedIn profile improvement workflow** that takes the resume-skill's ND-bias-aware language framework and applies it to the parallel surface — a LinkedIn profile, where the audience (recruiter semantic + skill-tag search) and the formatting constraints (plain text, scannable About section) differ meaningfully from a resume.
3. A **resume + LinkedIn consolidation workflow** that detects narrative inconsistency between a user's two job-search surfaces and proposes unifications.

These three items were explicitly deferred in [Plan 2](../plans/2026-05-12-plan-2-complete-workflows-and-packaging.md) as "out of scope — Plan 3 / future." MCP server, sibling skills (interview prep, salary), and "creative" resume templates remain deferred.

## 2. Scope

### In scope for Phase 2 (v1.1.0)

1. **Resume template library** — 4 templates total: `chronological` (existing, moved into new structure), `functional`, `hybrid`, `executive`
2. **Cover-letter template library** — 2 templates total: `formal-business` (existing, moved), `modern-clean`
3. **Template selection reference** — `references/template-selection.md` mapping (career stage × role type × ND signals × industry norms) → recommended template, with explicit framing on the functional-template tradeoff
4. **Generator parameterisation** — `resume_to_docx.py`, `cover_letter_to_docx.py`, and their PDF counterparts accept a `template=` parameter; default value preserves existing behaviour so all v1 workflows continue working unchanged
5. **LinkedIn profile improvement workflow** — new reference `references/workflows/linkedin-improve.md`, new slash command `commands/brains-linkedin-improve.md`, output is markdown sections (Headline / About / Experience / Skills) copy-paste-ready into LinkedIn
6. **Consolidation workflow** — new reference `references/workflows/consolidate.md`, new slash command `commands/brains-consolidate.md`, new validator `scripts/validators/consolidation_check.py`, output is a read-only markdown report with three suggested resolutions per detected delta
7. **SKILL.md router update** — new workflows registered, template-selection reference linked
8. **README + CHANGELOG + Claude Project bundle** — slash-command cheat sheet updated, v1.1.0 entry, bundle rebuilt to include new files
9. **v1.1.0 tag** at release

### Out of scope for Phase 2 (deferred to Phase 3+)

- **MCP server for Claude Desktop** — distribution/integration concern, different category from features; ships as its own phase
- **"Creative" resume templates** (graphical layouts, two-column visual designs, colour blocks) — clash with ATS-safety + introduce ND-bias noise; not adding even one
- **Autonomous LinkedIn editing** — no API write path I'd want to depend on; output stays copy-paste
- **Interview prep skill** — always slated as a sibling skill, not part of resume skill
- **Salary negotiation skill** — same
- **Resume version management** (multi-variant file management) — still out of scope, as in v1
- **OCR of scanned-image PDFs** — still out of scope, as in v1
- **Live LinkedIn URL fetching** — still out of scope, as in v1 (auth + ToS)

### Decision ledger

| # | Decision | Choice | Rationale |
|---|---|---|---|
| P2-Q1 | Phase 2 scope | Templates + LinkedIn profile workflow + consolidation workflow; MCP deferred to Phase 3 | Feature wave with shared "applying v1 framework to broader job-search surface" theme; MCP is distribution, different category |
| P2-Q2 | Number of resume templates | 4 (chronological, functional, hybrid, executive) | Covers the realistic career-stage matrix without explosion; "creative" excluded for ATS-safety + ND-bias reasons |
| P2-Q3 | Number of cover-letter templates | 2 (formal-business, modern-clean) | Two contexts in practice: traditional/regulated vs. tech/startup; more variants is YAGNI |
| P2-Q4 | Functional template inclusion despite recruiter-skepticism tradeoff | Include, with explicit framing in `template-selection.md` | Genuinely useful for career-changers and gap-friendly framing; the tradeoff is real but the user-agency answer is "inform, don't withhold" |
| P2-Q5 | LinkedIn profile output format | Markdown sections (copy-paste ready) | LinkedIn doesn't render rich text in most fields; no API write path worth depending on |
| P2-Q6 | LinkedIn profile workflow input | Reuse existing `linkedin_zip.py` ZIP ingest + accept pasted profile sections as alt input | Reuses v1 infrastructure; pasted alt-input covers the "I don't want to download a ZIP" case |
| P2-Q7 | Consolidation workflow operating mode | Read-only report + optional handoff to `brains-edit` / `brains-linkedin-improve` for fixes | Cross-document autonomous editing is risky and removes user agency; report-then-handoff is the conservative pattern |
| P2-Q8 | Consolidation deltas detected | Job title mismatches, date inconsistencies, achievements present in one doc but not the other, narrative-tone divergence | Covers the practical inconsistencies recruiters notice; more sophisticated checks (skill-keyword coverage) deferred |
| P2-Q9 | Template generator backward compatibility | New `template=` parameter on generators; default preserves existing chronological / formal-business behaviour | v1 workflows must continue working unchanged after upgrade |
| P2-Q10 | Brand on new artifacts | Same rule as v1: resumes and cover letters unbranded; LinkedIn profile output unbranded; consolidation report branded (it's an internal coaching artifact) | Unbranded vs. branded rule from v1 extends cleanly to all new artifact types |
| P2-Q11 | Privacy stance for LinkedIn profile workflow | Same six guardrails as v1 ingestion (output-dir default, .gitignore, one-time notice, connections excluded, no persistence, no telemetry) | No new privacy surface introduced |

## 3. Architecture overview

Same hybrid skill structure as v1: always-loaded `SKILL.md` core + on-demand reference files + deterministic Python scripts + validators.

**New directories:**

- `templates/resume/` — DOCX templates (chronological, functional, hybrid, executive)
- `templates/cover-letter/` — DOCX templates (formal-business, modern-clean)

**Migration of existing templates:**

- Existing `resume_chronological.docx` → `templates/resume/chronological.docx`
- Existing `cover_letter.docx` → `templates/cover-letter/formal-business.docx`
- Generator code updated to read from new paths; default `template=` value preserves current selection so v1 workflows are unaffected

**New components:**

```text
templates/
├── resume/
│   ├── chronological.docx       # moved from existing
│   ├── functional.docx          # NEW
│   ├── hybrid.docx              # NEW
│   └── executive.docx           # NEW
└── cover-letter/
    ├── formal-business.docx     # moved from existing
    └── modern-clean.docx        # NEW

references/
├── template-selection.md        # NEW — decision tree + ND framing
└── workflows/
    ├── linkedin-improve.md      # NEW
    └── consolidate.md           # NEW

commands/
├── brains-linkedin-improve.md   # NEW slash command
└── brains-consolidate.md        # NEW slash command

scripts/
└── validators/
    └── consolidation_check.py   # NEW validator
```

**Updated components:**

- `SKILL.md` — router gets two new workflow entries + template-selection reference link
- `scripts/generators/resume_to_docx.py` — accepts `template=` parameter
- `scripts/generators/resume_to_pdf.py` — accepts `template=` parameter (or derives from DOCX layout)
- `scripts/generators/cover_letter_to_docx.py` — accepts `template=` parameter
- `scripts/generators/cover_letter_to_pdf.py` — accepts `template=` parameter
- `README.md` — slash-command cheat-sheet updated; template-selection section added
- `CHANGELOG.md` — v1.1.0 entry
- `scripts/packaging/build_project_bundle.py` — includes new directories/files in the bundle

## 4. Template library detail

### 4.1 Resume templates

All templates are **strictly ATS-safe**:

- Single-column layout (no tables, no text boxes, no columns)
- Body font Aptos or Calibri 11pt (heading 13-14pt, name 16-18pt)
- No graphics, no colour fills, no decorative borders
- Word-style heading hierarchy (Heading 1 / Heading 2) so DOCX parsers detect structure
- Identity-first language throughout in placeholder text
- 1" margins minimum (0.75" acceptable on executive 2-page variant)

| Template | Best for | Structure |
|---|---|---|
| `chronological` | Linear career history, recent relevant experience | Header → Summary → Experience (reverse-chron) → Education → Skills |
| `functional` | Career-changers, employment gaps, skills-led story | Header → Summary → Skills-grouped achievements (3-4 skill clusters) → Experience (titles + dates only) → Education |
| `hybrid` | Career pivots with relevant transferable skills | Header → Summary → Key skills (3-5 bullets) → Experience (reverse-chron with skill tags) → Education |
| `executive` | Senior roles, 15+ years experience, board/leadership framing | Header → Executive summary → Career highlights (achievement-led) → Experience → Education → Board / advisory (optional) — 2-page allowance |

**ND framing in `template-selection.md`:** The functional template can help career-changers and people with gap-friendly framing needs, but recruiters historically interpret functional layouts as "hiding something." The reference documents this tradeoff explicitly and suggests the hybrid template as a middle path where the user wants skills-led framing without the recruiter penalty.

### 4.2 Cover-letter templates

| Template | Best for | Structure |
|---|---|---|
| `formal-business` | Traditional industries, regulated sectors, formal applications | Letterhead → Date → Recipient address → Salutation → 3-4 paragraphs → Sign-off |
| `modern-clean` | Tech / startup contexts where formal letterhead reads as stiff | Minimal header (name + contact) → Salutation → 3 paragraphs → Sign-off — less typographic weight, more whitespace |

Both remain single-column, no decorative elements, Aptos/Calibri 11pt body.

### 4.3 Template selection reference

`references/template-selection.md` contains:

1. **Decision tree** — interactive question flow (career stage → role type → industry norms → ND signals) → recommended template
2. **Template comparison table** — capabilities, tradeoffs, recruiter perception notes
3. **ND-specific framing** — the functional-vs-recruiter-perception tradeoff covered head-on; the hybrid as middle-path; explicit "you decide, here's what we know" tone
4. **Worked examples** — 3-4 synthetic cases showing template selection given a fictional user profile

### 4.4 Generator parameterisation

```python
# resume_to_docx.py — current signature
def resume_to_docx(structured_data: dict, output_path: Path) -> Path: ...

# resume_to_docx.py — new signature
def resume_to_docx(
    structured_data: dict,
    output_path: Path,
    template: str = "chronological",  # NEW — backward-compatible default
) -> Path: ...
```

Same pattern for `resume_to_pdf`, `cover_letter_to_docx`, `cover_letter_to_pdf`. The `template` parameter resolves to a path under `templates/resume/{template}.docx` or `templates/cover-letter/{template}.docx`. Unknown template names raise `ValueError` with the list of valid values.

## 5. LinkedIn profile improvement workflow

### 5.1 Purpose

Take an existing LinkedIn profile and produce a rewritten version optimised for:

- **Recruiter semantic + skill-tag search** (different from resume ATS — LinkedIn uses semantic match plus the structured Skills section)
- **Scannable About section** (3-paragraph max: hook → proof → CTA)
- **ND-aware language** (same Do/Don't rules as resume; same identity-first principle)
- **Plain-text formatting** (LinkedIn doesn't render markdown, bold, italics in most fields)

This is meaningfully different from the resume workflow because the audience scans LinkedIn differently (less time per profile, scrolling-on-mobile dominant), the search mechanism is different (semantic + skill tags vs. ATS keyword extraction), and the formatting affordances are different (no rich text, character limits on most fields).

### 5.2 Inputs

1. **LinkedIn ZIP export** — reuses `scripts/parsers/linkedin_zip.py` from v1; same six privacy guardrails
2. **Pasted profile sections** — alternative input for users who don't want to download a ZIP; user pastes Headline / About / Experience / Skills as raw text

### 5.3 Outputs

A markdown file (saved to `output/linkedin-profile-YYYY-MM-DD-HHMMSS.md`) with sections labelled for copy-paste into LinkedIn:

- **Headline** (220 char max — LinkedIn limit)
- **About** (2,600 char max — LinkedIn limit; aimed at ~1,500 for scannability)
- **Experience** — per-role rewrites (each ≤ ~2,000 chars)
- **Skills** — recommended skill tags (LinkedIn supports up to 50; aim for 25-30)

Each section includes:

- The rewritten text
- A one-line rationale (why this framing)
- Character count vs. LinkedIn limit
- The original text (for comparison)

### 5.4 Slash command

`commands/brains-linkedin-improve.md` — same shape as other workflow slash commands; routes to `references/workflows/linkedin-improve.md`.

## 6. Consolidation workflow

### 6.1 Purpose

When a user has both a resume and a LinkedIn profile, recruiters often check both. Inconsistencies (different job titles for the same role, mismatched dates, achievements claimed in one but not the other, formal vs. casual tone) are read as either carelessness or evasion.

This workflow detects those inconsistencies and proposes resolutions.

### 6.2 Inputs

1. **Existing resume** — DOCX or PDF (reuses v1 resume parsers)
2. **LinkedIn data** — either a ZIP export (via `linkedin_zip.py`) or a markdown file produced by the `brains-linkedin-improve` workflow

### 6.3 Detection — `consolidation_check.py` validator

Returns a list of findings, each with code, severity, role context, resume excerpt, LinkedIn excerpt, and three suggested resolutions:

| Finding code | Detects |
|---|---|
| `CONSOLIDATION_JOB_TITLE_MISMATCH` | Same employer + overlapping dates, but title differs (e.g. "Senior Engineer" vs. "Engineering Lead") |
| `CONSOLIDATION_DATE_INCONSISTENCY` | Start/end month differs between resume and LinkedIn for the same role |
| `CONSOLIDATION_ACHIEVEMENT_ONLY_IN_RESUME` | Bullet present in resume role description but absent from LinkedIn role description |
| `CONSOLIDATION_ACHIEVEMENT_ONLY_IN_LINKEDIN` | Bullet present in LinkedIn role description but absent from resume role description |
| `CONSOLIDATION_TONE_DIVERGENCE` | Same role described in formal/quantitative language in one doc and casual/narrative in the other |

### 6.4 Output

A markdown consolidation report (saved to `output/consolidation-report-YYYY-MM-DD-HHMMSS.md`) with:

- Summary count of findings per type
- Per-role side-by-side diffs
- Per-finding: three suggested resolutions tagged `[RESUME-LEADING]`, `[LINKEDIN-LEADING]`, `[NEW-SYNTHESIS]`
- A "next steps" footer suggesting `brains-edit` for the resume side and `brains-linkedin-improve` for the LinkedIn side

The report is **read-only**. No autonomous cross-document edits.

### 6.5 Slash command

`commands/brains-consolidate.md` — same shape as other workflow slash commands.

## 7. SKILL.md router updates

Two new workflow entries in the router section:

```markdown
## LinkedIn profile improvement
Use when the user wants to improve their LinkedIn profile (Headline / About /
Experience / Skills) using the same ND-aware framework as the resume workflows.
Output is copy-paste-ready markdown, not a DOCX/PDF.
Reference: references/workflows/linkedin-improve.md
Command: /brains-linkedin-improve

## Resume + LinkedIn consolidation
Use when the user has both a resume and a LinkedIn profile and wants to detect
and resolve narrative inconsistencies between them. Output is a read-only report;
fixes happen via brains-edit (resume) and brains-linkedin-improve (LinkedIn).
Reference: references/workflows/consolidate.md
Command: /brains-consolidate
```

Template-selection cross-reference added to the existing `brains-create`, `brains-edit`, `brains-tailor`, and `brains-cover-letter` workflows, pointing to `references/template-selection.md`.

## 8. Testing

Same TDD discipline as Plan 2.

### 8.1 Template testing

- **DOCX template structure tests** — each template parses with `python-docx`, has expected named styles (Heading 1, Heading 2, Normal), passes the integrity scan
- **ATS round-trip tests** — render a fixture resume into each template, then parse it back via the v1 resume parser, assert that all sections (Header / Summary / Experience / Education / Skills) are recovered correctly
- **Generator parameter tests** — `template="hybrid"` produces a DOCX whose underlying template-file hash matches `templates/resume/hybrid.docx`; unknown template names raise `ValueError`
- **Default-template backward-compatibility test** — calling the generator without a `template` argument produces the same output as v1.0.2 for a fixed input fixture

### 8.2 Template-selection reference testing

- **Decision-tree completeness test** — every leaf in the tree references a real template name
- **ND-framing presence test** — the functional-template tradeoff section exists and contains both pro and con language (so we don't slip into a one-sided pitch in future edits)

### 8.3 LinkedIn profile workflow testing

- **Synthetic-ZIP golden-file test** — synthetic LinkedIn export ZIP (reuse v1 fixture) → expected markdown output sections
- **Pasted-input parsing test** — pasted Headline / About / Experience text correctly segmented into sections
- **Character-limit tests** — generated Headline ≤ 220 chars; About ≤ 2,600 chars; per-Experience entry ≤ 2,000 chars
- **ND-bias scan on output** — generated markdown passes `bias_scan.py` with no high-severity findings
- **Integrity scan on output** — passes `integrity_check.py` with no findings

### 8.4 Consolidation validator testing

Per-finding-code unit tests using synthetic resume + synthetic LinkedIn data with seeded deltas:

- `CONSOLIDATION_JOB_TITLE_MISMATCH` — same employer + dates, title differs → finding raised
- `CONSOLIDATION_DATE_INCONSISTENCY` — start month differs by 1 → finding raised
- `CONSOLIDATION_ACHIEVEMENT_ONLY_IN_RESUME` — bullet in resume, absent in LinkedIn → finding raised
- `CONSOLIDATION_ACHIEVEMENT_ONLY_IN_LINKEDIN` — bullet in LinkedIn, absent in resume → finding raised
- `CONSOLIDATION_TONE_DIVERGENCE` — formal in one, casual in other → finding raised
- Clean alignment test — matched resume + LinkedIn → no findings

### 8.5 End-to-end smoke tests

One happy-path smoke test per new workflow:

- `test_linkedin_improve_smoke` — synthetic LinkedIn ZIP → markdown output file exists, contains expected sections, passes validators
- `test_consolidation_smoke` — synthetic resume + synthetic LinkedIn ZIP with one seeded delta → consolidation report file exists, contains the expected finding code and three resolution suggestions
- `test_template_variant_smoke` — for each of the 4 resume templates and 2 cover-letter templates, generator produces a valid DOCX that opens without error and contains the input content

## 9. Privacy and brand

### 9.1 Privacy

No new privacy surface. The LinkedIn profile workflow reuses `linkedin_zip.py` with the same six guardrails. The consolidation workflow reads resume + LinkedIn data, holds nothing in memory beyond the session, writes the report to the same `output/` directory (gitignored), no telemetry.

### 9.2 Brand-on-output rule extension

| New artifact | Branded? | Why |
|---|---|---|
| Resume DOCX/PDF — any template | Unbranded | Same rule as v1 — submitted document |
| Cover letter DOCX/PDF — any template | Unbranded | Same |
| LinkedIn profile improvement markdown output | Unbranded | Goes onto LinkedIn — third-party surface where BRAINS branding would be inappropriate |
| Consolidation report markdown | Branded | Internal coaching artifact — same category as the existing review coaching report |

`references/brand-application.md` updated to reflect these decisions.

## 10. Release plan

Single release tag at end of phase: **v1.1.0**.

- All tests green (existing v1.0.2 suite + new Phase 2 tests)
- All smoke tests green
- CHANGELOG.md v1.1.0 entry covering: 6 new templates (4 resume + 2 cover-letter), 2 new workflows (LinkedIn-improve, consolidate), 1 new validator (consolidation_check), generator parameterisation, template-selection reference
- README.md updated: install instructions unchanged; slash-command cheat sheet adds 2 commands; new "Choosing a template" section linking to `references/template-selection.md`
- Claude Project bundle rebuilt to include new directories and files
- v1.1.0 git tag

## 11. Implementation phasing

The implementation plan (separate document, to be produced via `writing-plans` skill) will sequence the work to keep the test suite green at each commit:

**Recommended phase order inside the plan:**

1. **Template infrastructure first** — move existing templates into new directory structure, parameterise generators, ship the 4 new resume templates + 1 new cover-letter template, write `template-selection.md`, update existing workflows to surface template choice. This is the foundation; everything else builds on it.
2. **LinkedIn profile workflow next** — new validator pieces, reference, slash command, smoke test
3. **Consolidation workflow last** — depends on stable resume parser + stable LinkedIn ingest output format, both of which the prior steps will have stressed
4. **Release polish** — SKILL.md router, README, CHANGELOG, bundle rebuild, v1.1.0 tag

The implementation plan will break each step into TDD tasks with checkbox tracking, matching the Plan 2 format.

---

**Points worth a second look during spec review:**

- The **tone-divergence** finding code in the consolidation validator is the fuzziest of the five — it's heuristic by nature (lexical-formality scoring + sentence-length variance), and the implementation plan should treat it as best-effort with explicit caveats in the report output.
- The **template-selection ND-framing** on the functional-template tradeoff has to land as "you decide, here's what we know" — not as a discouragement disguised as information. The implementation plan should include a review pass on the language of that section specifically.
- The **achievement-matching heuristic** for the `ACHIEVEMENT_ONLY_IN_*` finding codes will need a similarity threshold (likely fuzzy string match + semantic overlap); exact-match would over-fire on legitimate paraphrases. Implementation plan to define the threshold and include unit-test fixtures across the range.
