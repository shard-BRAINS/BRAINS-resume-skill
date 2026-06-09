# BRAINS Resume Skill — Design Specification

<!-- readability: skip -->
<!-- Historical planning/spec document; predates the BRAINS readability standard (adopted 2026-05-29). -->

**Version:** Draft v1
**Date:** 2026-05-11
**Status:** Awaiting user review
**Brand routing:** BRAINS parent (user-facing surfaces) · BRAINS Incubator (origin credit) · BRAINS Trust (footer credit on disclosure-coaching surfaces)
**Distribution intent:** Community release via shard-brains GitHub organisation, non-commercial

---

## 1. Purpose

A Claude Code skill that helps neurodivergent and autistic users review, edit, create, customise, and tailor resumes and cover letters — with cross-cutting awareness of the bias patterns that cause neurodivergent applicants to be filtered out by automated screening systems and human reviewers.

The skill exists because:

- Mainstream resume-writing guidance is built around neurotypical communication norms (hyperbolic warmth, "soft skills" coded language, narrative continuity) that disadvantage candidates who write more literally, precisely, or with employment patterns shaped by burnout, late diagnosis, or environment mismatch.
- Existing resume tooling treats ATS optimisation and bias mitigation as separate concerns. For neurodivergent users they are deeply entangled, and treating them together is the differentiator.
- BRAINS exists to hold AI systems accountable to neuro-affirming standards. A resume skill is a direct application of that mission to the everyday lives of neurodivergent adults navigating employment systems known to harm them.

## 2. Scope

### In scope for v1 (nine workflows)

1. **Resume review** — analyse an existing resume, flag bias and ATS risks, produce a coaching report
2. **Resume create-from-scratch** — build a resume from user-provided context via interactive interview
3. **Resume edit / customise** — improve an existing resume without tailoring to a specific job description
4. **Tailor to job description** — customise a resume to a specific JD
5. **Cover letter generation** — produce a matched cover letter
6. **LinkedIn ingestion** — parse a LinkedIn ZIP export or pasted profile content as source material
7. **Career-change translator** — translate experience from one domain into another
8. **Bias-aware ATS check** — final pre-submit pass on resume and cover letter
9. **Disclosure coaching** — guided framework for deciding whether, when, and how to disclose neurodivergence

### Out of scope for v1

- Interview preparation (large enough to be a sibling skill)
- Salary negotiation
- LinkedIn profile editing (vs. ingestion)
- Reference list building
- Offer comparison
- Portfolio case study writing
- Resume version management (file/multiple-variant management)
- OCR of scanned-image PDFs
- Live URL fetching of LinkedIn profiles (auth and ToS issues)
- Multiple resume templates (one chronological template ships in v1)

### Decision ledger

| # | Decision | Choice | Rationale |
|---|---|---|---|
| Q1 | Delivery format | Claude Code skill + supporting Python scripts | Bias and coaching work belongs in a skill; deterministic file handling (PDF/DOCX/LinkedIn ZIP) belongs in scripts |
| Q2 | Disclosure stance | **D — Hybrid**: affirmative-framing default with explicit disclosure option per resume | Respects user agency, makes the bias-minimised path the easy path, treats disclosure as a first-class option |
| Q3 | V1 scope | Nine workflows above; six items parked for v2 | Single coherent user journey, cross-cutting bias-awareness applies uniformly |
| Q4 | Brand routing | BRAINS parent on user-facing surfaces; Incubator origin credit; Trust footer credit on disclosure surfaces | Flagship public release under parent brand; Incubator is the prototype home; Trust credit where the safeguarding remit genuinely applies |
| Q5 | Input formats | PDF + DOCX + paste + LinkedIn ZIP + pasted-LinkedIn + JD paste + JD URL + JD screenshot + interactive interview | Covers the realistic surface; LinkedIn ZIP is the only non-trivial build but high-value |
| Q6 | Output formats and branding-on-outputs | Unbranded resume / cover letter; branded coaching reports; one chronological template in v1 | Brand on submitted documents would be inappropriate; coaching reports are user-facing internal artifacts where brand makes sense |
| Q7 | Privacy stance | All six guardrails (output-dir default, .gitignore, one-time notice, LinkedIn connections excluded, no persistence, no telemetry) | Standard hygienic defaults; LinkedIn-connections exclusion is the non-obvious safeguarding-critical item |
| Q8 | Repo, naming, license | Org `shard-brains`, repo `brains-resume-skill`, skill name `brains-resume`, MIT licence, private initially | Matches user's directory naming, BRAINS-aligned, release-ready from day one |
| Arch | Internal architecture | **Approach 3 — Hybrid**: lean always-loaded core + on-demand workflow references | Cross-cutting ND-bias awareness lives in always-loaded core (cannot be skipped); workflow detail is lazy-loaded; mirrors the existing `brains-brand` skill structure |

## 3. Bundle structure

The development directory `c:\Brains_Resume_Skill\` **is** the skill bundle. No separation between dev and the deliverable. When the user is ready to install, the bundle is copied or symlinked to `~/.claude/skills/brains-resume/`.

```text
c:\Brains_Resume_Skill\
├── SKILL.md                          # Always-loaded core (router + cross-cutting principles)
├── README.md                         # Public-facing
├── LICENSE                           # MIT
├── CONTRIBUTING.md
├── CHANGELOG.md
├── .gitignore                        # Excludes output/, common resume filenames, .venv/, __pycache__/
├── requirements.txt
├── pyproject.toml
│
├── references/
│   ├── workflows/                    # On-demand workflow instructions
│   │   ├── review.md
│   │   ├── create.md
│   │   ├── edit.md
│   │   ├── tailor.md
│   │   ├── cover-letter.md
│   │   ├── linkedin-ingest.md
│   │   ├── career-change.md
│   │   ├── bias-check.md
│   │   └── disclosure.md
│   ├── nd-bias-patterns.md           # Full catalog of ND-bias triggers + mitigations
│   ├── ats-rules.md                  # ATS formatting do/don'ts
│   ├── language-do-dont.md           # ND-affirmative phrasing table
│   ├── disclosure-decision-tree.md   # Full decision framework
│   ├── resume-anatomy.md             # Section-by-section guidance, ND-aware
│   └── brand-application.md          # When/how the brand applies to outputs
│
├── scripts/
│   ├── parsers/
│   │   ├── pdf_to_text.py
│   │   ├── docx_to_text.py
│   │   ├── linkedin_zip.py
│   │   └── jd_url_fetch.py
│   ├── generators/
│   │   ├── resume_to_docx.py
│   │   ├── resume_to_pdf.py
│   │   ├── cover_letter_to_docx.py
│   │   └── coaching_report_to_pdf.py
│   └── validators/
│       ├── ats_check.py
│       └── bias_scan.py
│
├── templates/
│   ├── resume_chronological.docx
│   ├── cover_letter.docx
│   └── coaching_report.md
│
├── assets/
│   ├── brains-mark-light-bg.png
│   └── brains-mark-dark-bg.png
│
├── tests/                            # pytest suite
│
├── docs/
│   ├── specs/                        # Design docs (this file)
│   ├── plans/                        # Implementation plans
│   └── testing/
│       └── fixtures/                 # Synthetic test fixtures, no real PII
│
└── output/                           # User-generated artifacts — gitignored
```

## 4. SKILL.md — always-loaded core

Approximate sections, all kept tight. Target: 300–450 lines.

1. **Frontmatter** — `name: brains-resume`, `description` (trigger criteria so Claude knows when to invoke), `version`, `license`
2. **What this skill does** — 2-3 sentences
3. **Workflow router** — table mapping user intents to workflow reference files
4. **ND-bias principles (cross-cutting)** — 10 summary bullets that mirror the ten pattern families in §5 (full catalog lives in `references/nd-bias-patterns.md`; the SKILL.md version is the always-loaded summary)
5. **Disclosure stance framework (cross-cutting)** — short summary of the hybrid default, pointer to the full decision tree
6. **BRAINS branding rules summary** — on-outputs rules: branded coaching artifacts, unbranded submitted documents, pointer to `references/brand-application.md`
7. **Privacy contract** — the six guarantees from the privacy decision
8. **First-use behaviour** — what the skill does on first invocation per session: greet, show capability menu, offer to start a workflow

The cross-cutting principles in items 4 and 5 are always loaded so they cannot be skipped by any workflow. This is the design's answer to the prior-art gap: bias-awareness as an architectural property, not a per-workflow reminder.

## 5. ND-bias framework

Lives in `references/nd-bias-patterns.md` and is consulted by every workflow.

### The ten pattern families

Each catalog entry has four fields: **trigger** (detection), **why it's biased**, **mitigation** (what to suggest), **user-veto note** (the skill never overrides — the user always decides).

1. **Soft-skills-coded vocabulary** — "team player", "passionate", "great communicator", "leadership presence", "thrive in fast-paced environments." Reframe as concrete instances: claim + measurable outcome.
2. **Employment-gap framing** — never apologise-on-the-page. Gaps stay unexplained on the resume itself. The skill prepares interview talking points separately.
3. **Short-tenure framing** — emphasise per-role achievement density over time-served. Group genuinely short engagements as contract or project work where truthful.
4. **Hyperfocus / narrow-expertise framing** — explicitly bridge deep-domain to transferable competencies. Avoid the "single-track" resume read.
5. **Modesty / under-claim** — recover full credit for genuinely solo work where the user has under-claimed. Never inflate.
6. **Direct ND signal terms** — "autism", "ASD", "autistic", "neurodivergent", "ADHD", named ND advocacy organisations, diagnosis-adjacent terminology ("executive function", "masking", "stimming"). Flag, offer neutral reframe, user vetoes if disclosure is the chosen stance.
7. **Indirect ND signal terms** — ND-affiliated employers, volunteer roles at ND organisations, ND-focused certifications. Same handling, lower confidence.
8. **Communication-warmth deficit** — autistic-typical literal and precise writing can read as cold. Add 1–2 warmth signals in the summary or cover letter that do not undermine specificity.
9. **Hyperbole mismatch** — avoidance of hyperbole, or over-precision that reads pedantic. Calibrate per sentence.
10. **Identity-language preference** — user's identity-first vs. person-first preference set once and respected throughout. Default identity-first per BRAINS brand.

## 6. Disclosure decision framework

Lives in `references/disclosure-decision-tree.md`. A guided worksheet, not a calculator.

### Five sections

1. **The default position** — do not disclose on the resume. Three-line legal note: accommodations are protected separately under disability law; resume disclosure cannot be retracted; interview and post-offer disclosure points have stronger legal protection.
2. **Factors that may shift the default toward disclosure** — six plain questions:
   - Is the employer ND-affirming in formal-program terms, not marketing copy?
   - Is the role accessibility or ND-affirming-adjacent itself?
   - Is the user applying via a recruiting channel that already screens for ND inclusion?
   - Does the user need an accommodation at application stage?
   - Is the user values-driven to disclose regardless of bias risk?
   - Has the user consulted an advocate?
3. **Three disclosure strengths** — non-disclosure, neutral signalling (e.g., "accessibility-aware UX research"), explicit disclosure. The skill works at any of the three; user picks per resume.
4. **Talking points for downstream disclosure** — interview, post-offer, post-acceptance. Brief scripts.
5. **Safeguarding caveat (top and bottom of the document)** — general guidance, not legal or medical advice; consult an employment advocate, disability-rights lawyer, or where relevant a clinician for specific decisions.

BRAINS Trust footer credit applies to this document and to any disclosure worksheet produced for a user.

## 7. The nine workflows

Each workflow lives in its own on-demand reference file.

### Build workflows

**Create-from-scratch** (`references/workflows/create.md`)
Trigger: user has no usable existing resume.
Inputs: interactive interview (target roles, work history, education, projects, skills, achievements, gaps, disclosure stance).
Steps: gather → consolidate → propose summary + bullets → ND-bias scan → user review → render.
Outputs: ATS-safe resume (DOCX + PDF + plain text) + reusable interview-transcript markdown.

**Edit / customise** (`references/workflows/edit.md`)
Trigger: user has a resume, wants improvements but no JD-specific tailoring.
Inputs: existing resume (PDF / DOCX / paste).
Steps: parse → identify weak spots → propose changes with rationale → user accepts or rejects each → render.
Outputs: revised resume + change-log markdown.

**LinkedIn ingestion** (`references/workflows/linkedin-ingest.md`)
Trigger: user provides LinkedIn ZIP export or pasted profile content.
Inputs: LinkedIn ZIP path or pasted profile text.
Steps: parse ZIP (strips `Connections.csv` and all third-party PII before returning, logs what was skipped) → normalise → user confirms relevance → feeds into create or edit.
Outputs: intermediate structured-profile markdown.

**Career-change translator** (`references/workflows/career-change.md`)
Trigger: user wants to pivot domain.
Inputs: existing resume + target domain / role.
Steps: analyse for transferable skills (special focus on hyperfocus → general-competency bridge per pattern #4) → research target-domain expectations → produce translation map → user reviews → render.
Outputs: translated resume + a skills-bridge markdown explaining each translation.

### Apply workflows

**Tailor to JD** (`references/workflows/tailor.md`)
Trigger: user has a target JD.
Inputs: existing resume + JD (paste / URL / screenshot).
Steps: extract JD requirements and keywords → score resume against them → propose targeted edits → ND-bias scan → user review → render.
Outputs: tailored resume + match report (what changed, keyword coverage, gaps to address in the cover letter).

**Cover letter** (`references/workflows/cover-letter.md`)
Trigger: user wants a letter to accompany a resume.
Inputs: tailored resume + JD + optional personal hook.
Steps: draft 3-paragraph structure (hook → fit → close) → calibrate warmth-vs-specificity (pattern #8) → reconcile with disclosure stance → ND-bias scan → user review → render.
Outputs: cover letter (DOCX + PDF + plain text).

### Audit workflows

**Resume review** (`references/workflows/review.md`)
Trigger: user wants a critique with no edits performed.
Inputs: existing resume.
Steps: parse → full ND-bias scan → ATS check via `scripts/validators/ats_check.py` → bullet-quality scoring → findings summary.
Outputs: branded BRAINS coaching report (markdown + optional PDF).

**Bias-aware ATS check** (`references/workflows/bias-check.md`)
Trigger: pre-submit final pass.
Inputs: final draft resume + cover letter.
Steps: ATS validator → ND-bias validator → disclosure-stance consistency check → red-flag report.
Outputs: pass/flag report with specific issues and one-line fix suggestions.

### Cross-cutting workflow

**Disclosure coaching** (`references/workflows/disclosure.md`)
Trigger: user explicitly asks, or any other workflow detects disclosure-relevant content (e.g., ND signal terms in a draft).
Inputs: target employer (optional), role, user's situation and preferences.
Steps: run the decision tree → produce the worksheet → optional downstream talking points (interview, post-offer).
Outputs: branded disclosure worksheet (markdown + optional PDF) with BRAINS Trust footer credit.

Each workflow ends by offering the user the natural next step. The skill is menu-driven internally but conversational externally.

## 8. Scripts

Python 3.10+. Five dependencies, all pure-Python, all cross-platform.

### Parsers (`scripts/parsers/`)

- **`pdf_to_text.py`** — `pdfplumber` for text extraction with section-structure heuristics. No OCR.
- **`docx_to_text.py`** — `python-docx` with section markers.
- **`linkedin_zip.py`** — unzips a LinkedIn export, parses Profile, Positions, Education, Skills, Languages, Certifications, Projects, Publications CSVs. Explicitly skips `Connections.csv`, `messages.csv`, and any other third-party-PII files. Logs skipped files so the user sees the safeguarding behaviour. Returns normalised JSON.
- **`jd_url_fetch.py`** — `trafilatura` for boilerplate-stripped JD text extraction. Returns clear error on anti-bot block so the user can fall back to paste or screenshot.

### Generators (`scripts/generators/`)

- **`resume_to_docx.py`** — structured resume JSON + template → ATS-safe DOCX via `python-docx`. Single-column, no tables, no text boxes, Calibri or Arial 11pt, no headers/footers carrying critical info.
- **`resume_to_pdf.py`** — generates PDF directly from the same structured data via `reportlab`, not via DOCX → PDF. Avoids the MS-Word dependency, works portably.
- **`cover_letter_to_docx.py`** — same discipline, simpler structure.
- **`coaching_report_to_pdf.py`** — markdown coaching reports → branded PDF via `reportlab`. Embeds Atkinson Hyperlegible (body) + Inter (headings). Applies Gold Deep `#D99518` for headings on white. Includes the BRAINS mark from `assets/`. Applies BRAINS Trust footer credit on disclosure-worksheet outputs specifically.

### Validators (`scripts/validators/`)

- **`ats_check.py`** — deterministic checks on a generated DOCX: tables, text boxes, multi-column layout, critical-info-in-header/footer, non-standard fonts, embedded images. Returns structured PASS/WARN/FAIL.
- **`bias_scan.py`** — regex and keyword backstop against the ND-bias pattern catalog. Not the full review (that is Claude's contextual job) — the deterministic safety net that catches obvious triggers even if the prompt-side review misses them.

### Dependencies (`requirements.txt`)

- `python-docx`
- `pdfplumber`
- `reportlab`
- `trafilatura`
- `pyyaml`

## 9. Output templates

- **`templates/resume_chronological.docx`** — single column, Calibri or Arial 11pt, clear section headers, no tables. The one v1 template.
- **`templates/cover_letter.docx`** — formal business letter layout, same font discipline.
- **`templates/coaching_report.md`** — markdown skeleton with BRAINS header banner placeholder; sections for Summary, ND-bias findings, ATS findings, Recommendations, Footer.

## 10. Testing strategy

Three layers, in increasing realism.

### Layer 1 — script unit tests

Per-parser, per-generator, per-validator. Synthetic inputs only. **No real PII ever in test data.** Fixtures live in `docs/testing/fixtures/`. Each fixture is a hand-built synthetic resume that injects specific issues (e.g., `gap-2yr.json`, `short-tenures.json`, `nd-signal-direct.json`).

### Layer 2 — bias-pattern coverage tests

For each of the ten ND-bias patterns in the catalog, at least one fixture must trigger it and `bias_scan.py` must detect it. This guarantees the deterministic backstop has ground truth and the catalog stays honest as it evolves.

### Layer 3 — workflow smoke tests

For each of the nine workflows, one happy-path scenario that runs end-to-end from synthetic input to expected artifacts, with validators passing. Run manually before cutting v0.1.0 → v1.0.0.

## 11. Privacy contract (user-facing)

The six guarantees, stated plainly in the README and in the skill's first-use notice:

1. Output artifacts go to a user-chosen output directory (default `./output/` in the user's working directory), never into the skill bundle.
2. The skill ships with a `.gitignore` template that excludes the output folder and common resume filenames so users do not accidentally commit PII.
3. On first use per session, the skill shows a short, plain-language notice that resume content is processed by Claude / Anthropic in that session.
4. The LinkedIn ZIP parser extracts only the user's own data and explicitly skips `Connections.csv` and any other file with third-party PII the user has no consent to process. Recommend deleting the ZIP after parsing.
5. The skill itself does not persist user data: disclosure-stance choice, employer details, salary expectations and anything sensitive are ephemeral to the session.
6. No telemetry, no analytics, no phone-home.

## 12. Repo layout and release readiness

Release-ready from day one. The `private → public` switch is a GitHub settings toggle, not a rewrite.

- `README.md` — title, one-line description, **"An Incubator project from BRAINS — built by neurodivergent minds, for neurodivergent people."** (protected origin phrase, verbatim), what it does in nine sentences, install, usage by workflow, privacy contract, contributing pointer, MIT licence, footer: **"AI that works for every mind."** (protected positioning phrase, verbatim).
- `LICENSE` — MIT, single copyright holder `BRAINS` (no third-party project references).
- `CONTRIBUTING.md` — BRAINS-aligned, identity-first language, code of conduct pointer, no third-party project mentions.
- `CHANGELOG.md` — semver, starting at v0.1.0.

### Versioning

- **v0.1.0** — first complete bundle, dev-tested only.
- **v1.0.0** — when at least one BRAINS community member outside the original author has run all nine workflows with realistic input and the smoke tests pass.

## 13. Brand application in practice

| Surface | Brand treatment |
|---|---|
| README, CONTRIBUTING, CHANGELOG | BRAINS parent, community-comms tone, Incubator origin credit |
| Skill internal docs (`references/*.md`, `SKILL.md`) | BRAINS parent, community-comms tone |
| Generated resumes (DOCX / PDF / text) | Unbranded — user's professional document |
| Generated cover letters | Unbranded — same reason |
| Coaching reports (markdown + PDF) | BRAINS branded. Gold Deep `#D99518` headings on white. Mark in header. Identity-first language throughout. |
| Disclosure worksheets | BRAINS branded + BRAINS Trust footer credit: *"Disclosure guidance developed with BRAINS Trust safeguarding principles."* |

Protected phrases used verbatim or not at all, per BRAINS brand rules. Never paraphrased.

## 14. Constraints and non-negotiables

- All development work confined to `c:\Brains_Resume_Skill\`. No scattering of artifacts elsewhere on the local machine.
- No references to any other organisation, repository, project, or third-party tool in any code, documentation, comment, or commit message. BRAINS / BRAINS Incubator / BRAINS Trust credit only.
- No online git activity until the user explicitly authorises it.
- Identity-first language by default; person-first when the user requests it.
- Never use puzzle-piece imagery or deficit-framing language (per BRAINS brand rules).
- Never use AI-generated images of people.
- No telemetry or phone-home.

## 15. Open questions

None at design time. All eight clarifying questions and the architecture decision are resolved (see Decision Ledger in §2).

---

*This specification is a design document. Implementation planning is the next phase.*
