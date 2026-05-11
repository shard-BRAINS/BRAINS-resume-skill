# Plan 1 — Foundation & Review Workflow (v0.1.0)

> **For implementers:** This plan uses checkbox (`- [ ]`) syntax. Work through tasks sequentially, marking each step as you go. Stage and commit after each task unless a step says otherwise. Never include third-party org or project credits in any file or commit message — BRAINS / BRAINS Trust / BRAINS Incubator only.

**Goal:** Ship v0.1.0 of the BRAINS Resume Skill — a working Claude Code skill that ingests a PDF or DOCX resume, runs a deterministic ATS-safety check and pattern-matched ND-bias scan, and produces a BRAINS-branded coaching report. Establishes the architectural foundation that subsequent workflows plug into.

**Architecture:** Hybrid skill — small always-loaded `SKILL.md` core (router + cross-cutting ND-bias and disclosure principles + privacy contract) with on-demand workflow references and reference documents. Deterministic Python scripts handle file I/O and pattern matching. Generated user documents (resume, cover letter) are unbranded; generated coaching artifacts are BRAINS-branded.

**Tech Stack:** Python 3.10+, `python-docx`, `pdfplumber`, `reportlab`, `trafilatura`, `pyyaml`, `pytest`. Claude Code skill bundle format.

**In scope for this plan:**
- Project skeleton, dependencies, licence, contribution guide
- All foundational reference documents (nd-bias patterns, ATS rules, language do/don't, resume anatomy, disclosure decision tree, brand application)
- Two parsers: PDF, DOCX
- Two validators: ATS-safety, ND-bias scan
- Coaching report markdown template + branded PDF generator
- `SKILL.md` always-loaded core
- Review + Disclosure workflow references
- End-to-end smoke test on a synthetic resume
- `README.md`, `CHANGELOG.md`, v0.1.0 tag

**Out of scope (deferred to Plan 2):**
- create-from-scratch, edit, tailor, cover-letter, linkedin-ingest, career-change, bias-aware-ATS-check workflows
- `resume_to_docx.py`, `resume_to_pdf.py`, `cover_letter_to_docx.py` generators
- `linkedin_zip.py`, `jd_url_fetch.py` parsers
- Chronological resume DOCX template, cover letter DOCX template
- v1.0.0 release

---

## Conventions used throughout this plan

- **Working directory:** `c:\Brains_Resume_Skill\` (all paths are relative to this unless absolute is shown).
- **Tests live in:** `tests/` mirroring the source structure (e.g., `tests/parsers/test_pdf_to_text.py`).
- **Fixtures live in:** `docs/testing/fixtures/` (synthetic only — never real PII).
- **Commit style:** conventional commits — `feat:`, `fix:`, `test:`, `docs:`, `build:`, `chore:`. Never include `Co-Authored-By` footers (BRAINS-only attribution constraint).
- **Identity-first language** throughout all content unless explicitly noted otherwise.
- **No third-party project/org references** in any file or commit message.

---

## Task 1 — Initialise Python project metadata

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`

### Steps

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "brains-resume"
version = "0.1.0"
description = "BRAINS Resume Skill — neurodivergent-aware resume review and bias mitigation. A BRAINS Incubator project."
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [
    { name = "BRAINS" }
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "python-docx>=1.1.0",
    "pdfplumber>=0.11.0",
    "reportlab>=4.0.0",
    "trafilatura>=1.12.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["scripts*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v"
```

- [ ] **Step 2: Create `requirements.txt`**

```
python-docx>=1.1.0
pdfplumber>=0.11.0
reportlab>=4.0.0
trafilatura>=1.12.0
pyyaml>=6.0
```

- [ ] **Step 3: Create `requirements-dev.txt`**

```
-r requirements.txt
pytest>=8.0.0
pytest-cov>=5.0.0
```

- [ ] **Step 4: Verify install works**

From `c:\Brains_Resume_Skill\`:
```
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```
Expected: all packages install successfully, and `scripts` is editable-installed so test imports resolve.

- [ ] **Step 5: Commit**

```
git add pyproject.toml requirements.txt requirements-dev.txt
git commit -m "build: add Python project metadata and pin dependencies"
```

---

## Task 2 — Add LICENSE and contribution guide

**Files:**
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`

### Steps

- [ ] **Step 1: Create `LICENSE`** (MIT, copyright BRAINS only)

```
MIT License

Copyright (c) 2026 BRAINS

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Create `CONTRIBUTING.md`** (BRAINS-aligned, identity-first, plain-language)

```markdown
# Contributing to the BRAINS Resume Skill

This project is part of the BRAINS Incubator — a space for community projects from neurodivergent minds, for neurodivergent people. Contributions are welcome from anyone whose work moves the skill closer to that goal.

## Before you contribute

- Read the design specification in `docs/specs/`. It captures every architectural and ethical decision and the reasons behind them. New work should align with it (or argue for changing it).
- Identity-first language is the default ("autistic person," not "person with autism"). Follow an individual's stated preference when they tell you theirs.
- Never use deficit framing in default copy. Never use puzzle-piece imagery. Never use AI-generated images of people.
- Outputs the user submits to employers (resumes, cover letters) stay unbranded. Outputs the user reads as coaching (review reports, disclosure worksheets) carry BRAINS branding.

## How to contribute

1. Open an issue describing the change you have in mind before writing code.
2. Branch from `main`. Keep the branch focused on one concern.
3. Match the conventional-commits style in commit messages (`feat:`, `fix:`, `docs:`, `test:`, `build:`, `chore:`).
4. Run the test suite (`pytest`) before opening a pull request. New features need new tests. The ten-pattern ND-bias coverage rule applies — `bias_scan.py` must detect every pattern in the catalog.
5. Never include third-party project, organisation, or platform credits in code, documentation, or commit messages. BRAINS / BRAINS Trust / BRAINS Incubator attribution only.

## What we are looking for

- New bias patterns observed in real (anonymised) examples, with proposed mitigations
- ATS rule updates as recruiter-tech evolves
- Language do/don't entries from lived experience
- Workflow improvements that reduce friction for users navigating burnout or executive-function load
- Translations and localisations

## What we are not looking for

- Removal or watering-down of the safeguarding caveats in the disclosure framework
- Branding on user-submitted documents
- Telemetry, analytics, or any data exfiltration

— Built by neurodivergent minds, for neurodivergent people.
```

- [ ] **Step 3: Commit**

```
git add LICENSE CONTRIBUTING.md
git commit -m "docs: add MIT licence and BRAINS-aligned contribution guide"
```

---

## Task 3 — Create directory skeleton

**Files:**
- Create directories: `references/`, `references/workflows/`, `scripts/`, `scripts/parsers/`, `scripts/generators/`, `scripts/validators/`, `templates/`, `assets/`, `tests/`, `tests/parsers/`, `tests/validators/`, `tests/generators/`, `tests/fixtures/`, `docs/testing/`, `docs/testing/fixtures/`
- Create empty `__init__.py` files where needed for Python imports

### Steps

- [ ] **Step 1: Create all directories**

Using PowerShell from `c:\Brains_Resume_Skill\`:
```powershell
$dirs = @(
    "references", "references\workflows",
    "scripts", "scripts\parsers", "scripts\generators", "scripts\validators",
    "templates", "assets",
    "tests", "tests\parsers", "tests\validators", "tests\generators", "tests\fixtures",
    "docs\testing", "docs\testing\fixtures"
)
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
```

- [ ] **Step 2: Create `__init__.py` files** so Python can import scripts cleanly

Create empty file at each of:
- `scripts/__init__.py`
- `scripts/parsers/__init__.py`
- `scripts/generators/__init__.py`
- `scripts/validators/__init__.py`
- `tests/__init__.py`
- `tests/parsers/__init__.py`
- `tests/validators/__init__.py`
- `tests/generators/__init__.py`

Each file is empty — zero bytes is fine. PowerShell one-liner:
```powershell
$inits = @(
    "scripts\__init__.py", "scripts\parsers\__init__.py",
    "scripts\generators\__init__.py", "scripts\validators\__init__.py",
    "tests\__init__.py", "tests\parsers\__init__.py",
    "tests\validators\__init__.py", "tests\generators\__init__.py",
    "tests\fixtures\__init__.py"
)
foreach ($f in $inits) { New-Item -ItemType File -Force -Path $f | Out-Null }
```

- [ ] **Step 3: Verify with `git status`**

Expected output: all new directories listed under untracked files, with `__init__.py` inside each Python package directory.

- [ ] **Step 4: Commit**

```
git add scripts/ tests/
git commit -m "chore: create directory skeleton and Python package markers"
```

(Note: `references/`, `templates/`, `assets/`, `docs/testing/fixtures/` will get committed when their content is added in later tasks.)

---

## Task 4 — Import BRAINS brand assets

**Files:**
- Create: `assets/brains-mark-light-bg.png` (copy from BRAINS brand skill)
- Create: `assets/brains-mark-dark-bg.png` (copy from BRAINS brand skill)

### Steps

- [ ] **Step 1: Copy brand marks**

The two PNG files live at `C:\Users\matth\.claude\skills\brains-brand\assets\brains-mark-light-bg-v1.png` and `C:\Users\matth\.claude\skills\brains-brand\assets\brains-mark-dark-bg-v1.png`.

From `c:\Brains_Resume_Skill\`:
```powershell
Copy-Item "C:\Users\matth\.claude\skills\brains-brand\assets\brains-mark-light-bg-v1.png" "assets\brains-mark-light-bg.png"
Copy-Item "C:\Users\matth\.claude\skills\brains-brand\assets\brains-mark-dark-bg-v1.png" "assets\brains-mark-dark-bg.png"
```

(We drop the `-v1` suffix; if the brand updates, we re-import.)

- [ ] **Step 2: Verify files copied and are valid PNGs**

```powershell
Get-Item assets\brains-mark-*.png | Select-Object Name, Length
```
Expected: both files listed with non-zero size.

- [ ] **Step 3: Commit**

```
git add assets/
git commit -m "feat: import BRAINS brand marks for coaching report branding"
```

---

## Task 5 — Write `references/language-do-dont.md`

**Files:**
- Create: `references/language-do-dont.md`

This is a content document. The implementer writes the full prose; the structure below is the contract.

### Document contract

**Purpose stated at the top:** This document is consulted by every workflow when proposing wording. It does not enforce — it informs. User preference always wins. Identity-first by default, person-first when the user specifies.

**Required sections, in order:**

1. **How to use this document** (1 paragraph) — pointer to use it as guidance, not enforcement
2. **The do / don't table** — three columns: `Don't use`, `Do use instead`, `Why`. Minimum 25 paired entries covering:
   - Deficit framing pairs (e.g., `suffers from autism` → `is autistic` — pathologising language)
   - Person-first defaults that ignore identity-first preference (e.g., `person with autism` → `autistic person` — community preference)
   - Hyperbolic soft-skills pairs (e.g., `passionate about X` → `[concrete instance + outcome]` — bias-coded vagueness)
   - Functional-deficit labels (e.g., `high-functioning` → omit or rephrase contextually — the term is harmful)
   - "Special needs" framings → `accessibility needs` or omit
   - Gendered language pairs (e.g., `chairman` → `chair` or `chairperson`)
   - Ableist idioms (e.g., `tone-deaf approach` → `out-of-touch approach`)
3. **Edge cases** (2-3 paragraphs) —
   - When the user themself uses the "Don't" column to describe themselves
   - When an organisation's official name uses outdated language
   - When a job description uses biased terms and the user is mirroring them strategically
4. **What this document does not do** (1 paragraph) — explicitly not a slur list, not exhaustive, not legal language guidance

### Steps

- [ ] **Step 1: Write the document content**

Draft per the contract above. Target 600-1000 words. Use markdown tables for the do/don't pairs. Reference identity-first as default with the BRAINS brand standard.

- [ ] **Step 2: Verify the table has at least 25 entries**

Count rows in the do/don't table. If fewer than 25, add more.

- [ ] **Step 3: Commit**

```
git add references/language-do-dont.md
git commit -m "docs: add ND-affirmative language do/don't reference"
```

---

## Task 6 — Write `references/ats-rules.md`

**Files:**
- Create: `references/ats-rules.md`

### Document contract

**Purpose:** Consulted by the ATS check workflow and by the bias-aware ATS check (Plan 2). Captures what ATS systems can and can't parse reliably, presented as concrete rules with reasons.

**Required sections, in order:**

1. **What an ATS is and isn't** (2 paragraphs) — applicant tracking system: a parser + keyword scorer; not a human reader; behaviour varies by vendor but failure modes are consistent
2. **The hard rules** (rules that pass/fail an ATS) — bulleted list:
   - Single-column layout only
   - No tables, no text boxes, no shapes containing text
   - No images carrying critical content (names, dates, contact)
   - No headers/footers carrying critical content (name, contact, location)
   - Standard fonts (Calibri, Arial, Times New Roman, Helvetica, Georgia, Cambria, Garamond)
   - Body text 10–12 pt
   - Standard section headings (`Experience`, `Education`, `Skills`, not `Things I have done`)
   - Plain `.docx` or `.pdf` only; never `.pages`, `.odt`, or scanned images
3. **The soft rules** (rules that hurt ATS scoring but don't fail it) — bulleted:
   - Bullet points use simple characters (`-`, `•`); never decorative dingbats
   - Date formats `MMM YYYY` or `MM/YYYY`, consistent throughout
   - Job titles match common industry terminology where truthful
   - Keywords from the JD appear in the resume body, not stuffed in invisible whitespace
4. **The dignity rule** (1 paragraph) — keyword stuffing, white-text-on-white, font-size-1 hidden text are not just dishonest, they are also reliably detected by modern ATS and will harm the application
5. **Cross-reference to bias check** — pointer to `nd-bias-patterns.md` for the ND-specific layer

### Steps

- [ ] **Step 1: Write the document content**

Target 500-900 words. Use markdown tables where it helps comparison.

- [ ] **Step 2: Verify all four sections are present and the hard-rules list covers everything that `ats_check.py` (Task 15) needs to validate against**

Cross-check: each item the validator will programmatically check must have a corresponding rule here.

- [ ] **Step 3: Commit**

```
git add references/ats-rules.md
git commit -m "docs: add ATS formatting rules reference"
```

---

## Task 7 — Write `references/nd-bias-patterns.md`

**Files:**
- Create: `references/nd-bias-patterns.md`

This is the most important reference document in the bundle. It is the source of truth for both Claude's contextual review and the deterministic `bias_scan.py` validator.

### Document contract

**Required structure:**

1. **Header section** — purpose, how to use, the user-veto principle (the catalog never overrides; the user always decides)
2. **The ten pattern families** — one section per family, each with the exact same four-field structure:
   - **Trigger:** a precise description of what to detect (regex-able where possible)
   - **Why it's biased:** 2-3 sentences citing the bias mechanism (ATS, human screener, or both)
   - **Mitigation:** what to suggest instead, with at least one before/after example
   - **User-veto note:** the standard disclaimer that user disclosure stance overrides

**The ten families (must be present, in this order):**

1. **Soft-skills-coded vocabulary**
   - Trigger words include: `passionate`, `team player`, `great communicator`, `leadership presence`, `thrive in fast-paced environments`, `go-getter`, `self-starter`, `dynamic`, `proactive`, `synergy`
2. **Employment-gap framing**
   - Trigger: any phrase explaining a gap on the resume itself (`Career break to focus on...`, `Took time off for...`, `Returning to work after...`)
3. **Short-tenure framing**
   - Trigger: roles under 18 months in chronological listing without project/contract context
4. **Hyperfocus / narrow-expertise framing**
   - Trigger: resume content showing extreme depth in one domain with no transferable-skills bridge
5. **Modesty / under-claim**
   - Trigger: passive constructions and credit-sharing language for genuinely solo work (`Was part of a team that...`, `Helped with...`, `Contributed to...`)
6. **Direct ND signal terms**
   - Trigger words (case-insensitive): `autism`, `autistic`, `ASD`, `Asperger`, `aspie`, `neurodivergent`, `neurodiverse`, `ADHD`, `ADD`, `dyslexia`, `dyspraxia`, `dyscalculia`, `Tourette`, `executive function`, `masking`, `stimming`, `sensory processing`
7. **Indirect ND signal terms**
   - Trigger: known ND advocacy organisation names, ND-affiliated volunteer roles, ND-focused certification names (catalog at least 10 examples but explicitly mark the list as illustrative not exhaustive)
8. **Communication-warmth deficit**
   - Trigger: heuristic — summary paragraph with 0 first-person warmth signals (no `I`, `we`, no values statements, no motivation reference)
9. **Hyperbole mismatch**
   - Trigger: either total absence of hyperbole anywhere, or over-precision in a place where warmth-signal expected (resume summary, cover letter opening)
10. **Identity-language preference**
    - Trigger: mixed person-first and identity-first language in the same document
    - Mitigation: pick one consistently per user preference; default identity-first

3. **Pattern-to-validator mapping** (table at the end) — three columns: `Pattern #`, `Detectable by bias_scan.py` (yes/no/partial), `Claude-side review required` (yes/no). Patterns 1, 2, 6, 7, 10 are fully detectable by regex/keyword. Patterns 3, 4, 5, 8, 9 require contextual review.

### Steps

- [ ] **Step 1: Write the document content**

Target 1500-2500 words. Each pattern family gets a 100-250 word section. Include real before/after examples for each.

- [ ] **Step 2: Cross-check trigger coverage**

For patterns 1, 2, 6, 7, 10, confirm the trigger list is specific enough that `bias_scan.py` (Task 16) can regex-match each. If not, sharpen the triggers.

- [ ] **Step 3: Verify the user-veto note appears in every pattern section**

Search for the disclaimer phrase; should appear at least 10 times.

- [ ] **Step 4: Commit**

```
git add references/nd-bias-patterns.md
git commit -m "docs: add ND-bias pattern catalog (10 families)"
```

---

## Task 8 — Write `references/resume-anatomy.md`

**Files:**
- Create: `references/resume-anatomy.md`

### Document contract

**Purpose:** Section-by-section guidance on what a good resume looks like, with ND-aware framing on each section. Minimal v1 — the create-from-scratch and edit workflows (Plan 2) will expand it.

**Required sections, in order:**

1. **Resume sections in order** — header → summary → experience → education → skills → optional (projects, publications, certifications). Note: chronological format is the v1 default because it ATS-scores best.
2. **For each section, four bullets:**
   - What it must include
   - What it should not include
   - The ND-aware lens (which bias patterns from `nd-bias-patterns.md` are most likely to surface here)
   - A short example (2-4 lines) of a section done well

### Steps

- [ ] **Step 1: Write the document content**

Target 800-1200 words. Examples must be synthetic — no real PII.

- [ ] **Step 2: Commit**

```
git add references/resume-anatomy.md
git commit -m "docs: add ND-aware resume anatomy reference"
```

---

## Task 9 — Write `references/brand-application.md`

**Files:**
- Create: `references/brand-application.md`

### Document contract

**Purpose:** Operational reference for when and how BRAINS branding applies to outputs the skill produces. Consulted by the coaching report generator and by the SKILL.md branding-rules summary.

**Required content:**

1. **The split rule** (1 short section) — branded vs unbranded by surface, in the same table format used in the design spec §13.
2. **Branded coaching report styling** (specifics needed by `coaching_report_to_pdf.py`):
   - Header: BRAINS mark (`assets/brains-mark-light-bg.png`) top-left, 36 pt height, with 24 pt margin
   - Body font: Atkinson Hyperlegible Regular, 11 pt, line height 1.5
   - Heading font: Inter Bold, 18 pt for h1, 14 pt for h2, 12 pt for h3
   - Heading colour: Gold Deep `#D99518` on white
   - Body colour: `#1A1A1A` on white
   - Page margins: 0.75 inch all sides
   - Footer: small grey `Built by neurodivergent minds, for neurodivergent people.` (protected origin phrase, verbatim) centred, 9 pt
3. **Disclosure-worksheet additional rule** — disclosure worksheets get a BRAINS Trust footer credit line *above* the standard footer: `Disclosure guidance developed with BRAINS Trust safeguarding principles.` 9 pt italic — wait, italics are non-negotiable for the brand, so this must be **bold** or in a different weight, not italic. **Correct rule:** `Disclosure guidance developed with BRAINS Trust safeguarding principles.` in 9 pt Atkinson Hyperlegible Medium (not italic).
4. **What never gets branded** — generated resumes (DOCX/PDF/text), generated cover letters, anything the user submits to an employer

### Steps

- [ ] **Step 1: Write the document content**

Target 400-700 words. The PDF generator implementation in Task 18 reads its styling parameters from this document — keep specifics precise.

- [ ] **Step 2: Commit**

```
git add references/brand-application.md
git commit -m "docs: add brand application reference for coaching outputs"
```

---

## Task 10 — Write `references/disclosure-decision-tree.md`

**Files:**
- Create: `references/disclosure-decision-tree.md`

### Document contract

**Purpose:** The user-facing framework for the disclosure decision. Cross-referenced by SKILL.md and rendered into branded worksheets by the disclosure workflow.

**Required structure (matches §6 of the design spec):**

1. **The hard safeguarding caveat at the top** — bold/prominent, plain language: this is general guidance, not legal or medical advice; for specific decisions consult an employment advocate, disability-rights lawyer, or where relevant a clinician
2. **The default position** — do not disclose on the resume, with the three-line legal note about accommodation protection, irretractability, stronger post-offer protection
3. **Six factors that may shift the default** — each as a plain-language question with 1-2 sentence guidance on what the answer implies
4. **The three disclosure strengths** — non-disclosure, neutral signalling, explicit disclosure, with example sentences for each
5. **Talking points for downstream disclosure** — short scripts for interview, post-offer, post-acceptance contexts
6. **The hard safeguarding caveat at the bottom** — same caveat as the top, repeated
7. **BRAINS Trust footer credit line** — verbatim text the generator will render: `Disclosure guidance developed with BRAINS Trust safeguarding principles.`

### Steps

- [ ] **Step 1: Write the document content**

Target 1200-1800 words. The safeguarding caveat MUST appear at top and bottom — verify before commit.

- [ ] **Step 2: Verify the BRAINS Trust footer line appears verbatim**

The string `Disclosure guidance developed with BRAINS Trust safeguarding principles.` must appear at least once. The generator copies it from this document.

- [ ] **Step 3: Commit**

```
git add references/disclosure-decision-tree.md
git commit -m "docs: add disclosure decision framework with safeguarding caveats"
```

---

## Task 11 — Write `references/workflows/disclosure.md`

**Files:**
- Create: `references/workflows/disclosure.md`

### Document contract

**Purpose:** Instructions Claude follows when running the disclosure-coaching workflow. Loaded on demand.

**Required content:**

1. **Trigger conditions** — user explicitly asks for disclosure coaching, OR any other workflow detects content matching ND-bias patterns 6 or 7 (direct or indirect ND signals)
2. **Inputs to collect** — target employer (optional), role title (optional), user's situation summary, user's prior disclosure preference if known from session
3. **Step-by-step procedure**:
   - a. Load `references/disclosure-decision-tree.md`
   - b. State the default position and the safeguarding caveat at the start
   - c. Walk the user through each of the six factors as plain questions; record answers
   - d. Based on answers, suggest one of the three disclosure strengths (non-disclosure / neutral signalling / explicit) — explicitly framed as a suggestion, not a decision
   - e. Offer to produce a worksheet artifact summarising the conversation
   - f. If user accepts, generate worksheet markdown via the coaching-report template structure and render to branded PDF via `coaching_report_to_pdf.py` with the BRAINS Trust footer flag set
   - g. End by offering to continue into the review or edit workflow if applicable
4. **Output artifacts:**
   - `output/disclosure-worksheet-YYYY-MM-DD-HHMMSS.md`
   - `output/disclosure-worksheet-YYYY-MM-DD-HHMMSS.pdf` (branded, with Trust footer credit)
5. **Boundaries** — what this workflow does NOT do: it does not advise on individual legal cases, it does not diagnose, it does not replace professional advice. State this verbatim once at start and once at end of every disclosure interaction.

### Steps

- [ ] **Step 1: Write the workflow file**

Target 400-700 words.

- [ ] **Step 2: Commit**

```
git add references/workflows/disclosure.md
git commit -m "docs: add disclosure-coaching workflow reference"
```

---

## Task 12 — Write `references/workflows/review.md`

**Files:**
- Create: `references/workflows/review.md`

### Document contract

**Purpose:** Instructions Claude follows when running the resume-review workflow.

**Required content:**

1. **Trigger conditions** — user asks for a resume review / critique / audit; user provides a resume but does not request edits
2. **Inputs to collect**:
   - The resume itself (PDF, DOCX, or pasted text)
   - User's disclosure stance preference if not already set this session
   - User's identity-first vs person-first language preference
3. **Step-by-step procedure:**
   - a. If PDF or DOCX file: run the appropriate parser (`scripts/parsers/pdf_to_text.py` or `scripts/parsers/docx_to_text.py`) to extract text and structure
   - b. Run `scripts/validators/ats_check.py` on the file (DOCX only — PDFs flagged as "ATS check unavailable for PDF, recommend DOCX submission")
   - c. Run `scripts/validators/bias_scan.py` on the extracted text — get deterministic pattern matches for patterns 1, 2, 6, 7, 10
   - d. Perform contextual review for patterns 3, 4, 5, 8, 9 (which require human-level judgement)
   - e. Cross-reference detected issues against `references/nd-bias-patterns.md` mitigations
   - f. Score each bullet for: specificity, measurability, ND-bias risk (low/med/high)
   - g. Score the summary section against the warmth-vs-specificity calibration (pattern #8)
   - h. Compile findings into `templates/coaching_report.md` structure
   - i. Render to branded PDF via `coaching_report_to_pdf.py`
4. **Output artifacts:**
   - `output/coaching-report-YYYY-MM-DD-HHMMSS.md`
   - `output/coaching-report-YYYY-MM-DD-HHMMSS.pdf` (branded)
5. **Next-step offer** — at end of report, the skill offers to invoke the edit workflow to apply specific recommendations (deferred to Plan 2 — for v0.1.0, state that "edit workflow ships in v0.5")
6. **Bias of the review itself** — explicit boundary: this review is a pattern-aware analysis; it cannot guarantee the user will or will not be filtered out; user agency over every recommendation is absolute

### Steps

- [ ] **Step 1: Write the workflow file**

Target 500-800 words.

- [ ] **Step 2: Commit**

```
git add references/workflows/review.md
git commit -m "docs: add resume-review workflow reference"
```

---

## Task 13 — Implement `scripts/parsers/pdf_to_text.py` (TDD)

**Files:**
- Create: `docs/testing/fixtures/synthetic_resume_basic.pdf` (synthetic test fixture)
- Create: `tests/parsers/test_pdf_to_text.py`
- Create: `scripts/parsers/pdf_to_text.py`

### Steps

- [ ] **Step 1: Generate the synthetic PDF fixture**

A small reportlab script to create a synthetic resume PDF with known content. Save the generator script as `docs/testing/fixtures/_make_synthetic_resume_basic.py`:

```python
"""Generate a synthetic resume PDF for testing. Run once; commit the resulting PDF.
NO REAL PII — all content is fictional and deliberately innocuous."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from pathlib import Path

styles = getSampleStyleSheet()
fixture_path = Path(__file__).parent / "synthetic_resume_basic.pdf"

doc = SimpleDocTemplate(str(fixture_path), pagesize=letter)
story = [
    Paragraph("Alex Test", styles["Title"]),
    Paragraph("alex.test@example.invalid · +0 0000 000000", styles["Normal"]),
    Spacer(1, 12),
    Paragraph("<b>Summary</b>", styles["Heading2"]),
    Paragraph("Software engineer with eight years of experience building data systems.", styles["Normal"]),
    Spacer(1, 12),
    Paragraph("<b>Experience</b>", styles["Heading2"]),
    Paragraph("<b>Senior Engineer</b>, Example Corp · 2020 — Present", styles["Normal"]),
    Paragraph("Built ingestion pipeline processing 50M events daily.", styles["Normal"]),
]
doc.build(story)
print(f"Wrote {fixture_path}")
```

Run it once from `c:\Brains_Resume_Skill\`:
```
.venv\Scripts\activate
python docs\testing\fixtures\_make_synthetic_resume_basic.py
```

Expected: `docs/testing/fixtures/synthetic_resume_basic.pdf` exists.

- [ ] **Step 2: Write the failing test**

Create `tests/parsers/test_pdf_to_text.py`:

```python
"""Tests for the PDF resume parser."""
from pathlib import Path
import pytest

from scripts.parsers.pdf_to_text import parse_pdf_resume

FIXTURE = Path(__file__).parent.parent.parent / "docs" / "testing" / "fixtures" / "synthetic_resume_basic.pdf"


def test_parser_returns_dict_with_required_keys():
    result = parse_pdf_resume(FIXTURE)
    assert isinstance(result, dict)
    for key in ("raw_text", "sections", "page_count"):
        assert key in result, f"Missing key: {key}"


def test_parser_extracts_known_content():
    result = parse_pdf_resume(FIXTURE)
    assert "Alex Test" in result["raw_text"]
    assert "Software engineer" in result["raw_text"]
    assert "Example Corp" in result["raw_text"]


def test_parser_detects_summary_section():
    result = parse_pdf_resume(FIXTURE)
    assert "summary" in [s.lower() for s in result["sections"].keys()]


def test_parser_detects_experience_section():
    result = parse_pdf_resume(FIXTURE)
    assert "experience" in [s.lower() for s in result["sections"].keys()]


def test_parser_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        parse_pdf_resume(Path("does_not_exist.pdf"))
```

- [ ] **Step 3: Run test to verify it fails**

```
pytest tests/parsers/test_pdf_to_text.py -v
```
Expected: all tests FAIL with `ModuleNotFoundError: No module named 'scripts.parsers.pdf_to_text'` or `ImportError`.

- [ ] **Step 4: Write the minimal implementation**

Create `scripts/parsers/pdf_to_text.py`:

```python
"""PDF resume parser.

Extracts text and detects section structure from a resume PDF using pdfplumber.
Returns a dict with raw text, detected sections, and page count.

No OCR support — scanned-image PDFs are out of scope for v1.
"""
from pathlib import Path
from typing import Union

import pdfplumber

# Section heading vocabulary the parser recognises.
SECTION_KEYWORDS = {
    "summary", "profile", "objective", "about",
    "experience", "employment", "work history", "professional experience",
    "education", "academic", "qualifications",
    "skills", "technical skills", "competencies",
    "projects", "publications", "certifications", "languages",
    "achievements", "awards", "interests", "volunteer",
}


def parse_pdf_resume(path: Union[str, Path]) -> dict:
    """Parse a resume PDF and return structured content.

    Parameters
    ----------
    path : str or Path
        Path to a PDF file.

    Returns
    -------
    dict
        Keys: ``raw_text`` (str), ``sections`` (dict[str, str]), ``page_count`` (int).

    Raises
    ------
    FileNotFoundError
        If the PDF file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    with pdfplumber.open(path) as pdf:
        page_count = len(pdf.pages)
        raw_text_parts = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            raw_text_parts.append(text)
    raw_text = "\n".join(raw_text_parts)

    sections = _split_sections(raw_text)
    return {
        "raw_text": raw_text,
        "sections": sections,
        "page_count": page_count,
    }


def _split_sections(raw_text: str) -> dict:
    """Heuristic section splitter — looks for short lines that match the
    section-keyword vocabulary and treats them as headings."""
    sections: dict = {}
    current_heading = "_preamble"
    current_lines: list = []

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            current_lines.append(line)
            continue
        # Heading heuristic: short line (<=40 chars), matches a keyword.
        if len(stripped) <= 40:
            lower = stripped.lower().rstrip(":")
            if lower in SECTION_KEYWORDS:
                # Flush current section.
                if current_lines:
                    sections[current_heading] = "\n".join(current_lines).strip()
                current_heading = lower
                current_lines = []
                continue
        current_lines.append(line)

    if current_lines:
        sections[current_heading] = "\n".join(current_lines).strip()

    return sections
```

- [ ] **Step 5: Run tests to verify they pass**

```
pytest tests/parsers/test_pdf_to_text.py -v
```
Expected: all 5 tests PASS.

- [ ] **Step 6: Commit**

```
git add scripts/parsers/pdf_to_text.py tests/parsers/test_pdf_to_text.py docs/testing/fixtures/_make_synthetic_resume_basic.py docs/testing/fixtures/synthetic_resume_basic.pdf
git commit -m "feat: add PDF resume parser with section detection"
```

---

## Task 14 — Implement `scripts/parsers/docx_to_text.py` (TDD)

**Files:**
- Create: `docs/testing/fixtures/_make_synthetic_resume_basic_docx.py` (fixture generator)
- Create: `docs/testing/fixtures/synthetic_resume_basic.docx` (generated)
- Create: `tests/parsers/test_docx_to_text.py`
- Create: `scripts/parsers/docx_to_text.py`

### Steps

- [ ] **Step 1: Generate the synthetic DOCX fixture**

Create `docs/testing/fixtures/_make_synthetic_resume_basic_docx.py`:

```python
"""Generate a synthetic resume DOCX for testing. Run once; commit the resulting DOCX.
NO REAL PII — all content is fictional and innocuous."""
from pathlib import Path
from docx import Document

fixture_path = Path(__file__).parent / "synthetic_resume_basic.docx"

doc = Document()
doc.add_heading("Alex Test", level=0)
doc.add_paragraph("alex.test@example.invalid · +0 0000 000000")
doc.add_heading("Summary", level=1)
doc.add_paragraph("Software engineer with eight years of experience building data systems.")
doc.add_heading("Experience", level=1)
doc.add_paragraph("Senior Engineer, Example Corp · 2020 — Present")
doc.add_paragraph("Built ingestion pipeline processing 50M events daily.")
doc.add_heading("Education", level=1)
doc.add_paragraph("BSc Computer Science, Example University, 2015")
doc.save(str(fixture_path))
print(f"Wrote {fixture_path}")
```

Run once:
```
python docs\testing\fixtures\_make_synthetic_resume_basic_docx.py
```

- [ ] **Step 2: Write the failing test**

Create `tests/parsers/test_docx_to_text.py`:

```python
"""Tests for the DOCX resume parser."""
from pathlib import Path
import pytest

from scripts.parsers.docx_to_text import parse_docx_resume

FIXTURE = Path(__file__).parent.parent.parent / "docs" / "testing" / "fixtures" / "synthetic_resume_basic.docx"


def test_parser_returns_dict_with_required_keys():
    result = parse_docx_resume(FIXTURE)
    assert isinstance(result, dict)
    for key in ("raw_text", "sections", "paragraph_count"):
        assert key in result


def test_parser_extracts_known_content():
    result = parse_docx_resume(FIXTURE)
    assert "Alex Test" in result["raw_text"]
    assert "Software engineer" in result["raw_text"]


def test_parser_detects_summary_and_experience_sections():
    result = parse_docx_resume(FIXTURE)
    keys_lower = [k.lower() for k in result["sections"].keys()]
    assert "summary" in keys_lower
    assert "experience" in keys_lower


def test_parser_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        parse_docx_resume(Path("does_not_exist.docx"))
```

- [ ] **Step 3: Run test to verify it fails**

```
pytest tests/parsers/test_docx_to_text.py -v
```
Expected: ImportError / ModuleNotFoundError.

- [ ] **Step 4: Write the minimal implementation**

Create `scripts/parsers/docx_to_text.py`:

```python
"""DOCX resume parser.

Extracts text and detects section structure from a resume DOCX using python-docx.
Returns a dict with raw text, detected sections, and paragraph count.
"""
from pathlib import Path
from typing import Union

from docx import Document

SECTION_KEYWORDS = {
    "summary", "profile", "objective", "about",
    "experience", "employment", "work history", "professional experience",
    "education", "academic", "qualifications",
    "skills", "technical skills", "competencies",
    "projects", "publications", "certifications", "languages",
    "achievements", "awards", "interests", "volunteer",
}


def parse_docx_resume(path: Union[str, Path]) -> dict:
    """Parse a resume DOCX and return structured content.

    Parameters
    ----------
    path : str or Path
        Path to a DOCX file.

    Returns
    -------
    dict
        Keys: ``raw_text`` (str), ``sections`` (dict[str, str]), ``paragraph_count`` (int).

    Raises
    ------
    FileNotFoundError
        If the DOCX file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"DOCX not found: {path}")

    doc = Document(str(path))
    raw_text_parts: list = []
    sections: dict = {}
    current_heading = "_preamble"
    current_lines: list = []

    for paragraph in doc.paragraphs:
        text = paragraph.text
        raw_text_parts.append(text)
        # Detect heading: either Word heading style, OR short line matching keyword.
        style_name = (paragraph.style.name or "").lower()
        is_heading = style_name.startswith("heading") or style_name == "title"
        looks_like_heading = (
            len(text.strip()) <= 40
            and text.strip().lower().rstrip(":") in SECTION_KEYWORDS
        )
        if (is_heading and text.strip().lower().rstrip(":") in SECTION_KEYWORDS) or looks_like_heading:
            if current_lines:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = text.strip().lower().rstrip(":")
            current_lines = []
        else:
            current_lines.append(text)

    if current_lines:
        sections[current_heading] = "\n".join(current_lines).strip()

    return {
        "raw_text": "\n".join(raw_text_parts),
        "sections": sections,
        "paragraph_count": len(doc.paragraphs),
    }
```

- [ ] **Step 5: Run tests to verify they pass**

```
pytest tests/parsers/test_docx_to_text.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 6: Commit**

```
git add scripts/parsers/docx_to_text.py tests/parsers/test_docx_to_text.py docs/testing/fixtures/_make_synthetic_resume_basic_docx.py docs/testing/fixtures/synthetic_resume_basic.docx
git commit -m "feat: add DOCX resume parser with section detection"
```

---

## Task 15 — Implement `scripts/validators/ats_check.py` (TDD)

**Files:**
- Create: `docs/testing/fixtures/_make_ats_fixtures.py`
- Create: `docs/testing/fixtures/ats_clean.docx`
- Create: `docs/testing/fixtures/ats_with_table.docx`
- Create: `docs/testing/fixtures/ats_with_header.docx`
- Create: `tests/validators/test_ats_check.py`
- Create: `scripts/validators/ats_check.py`

### Steps

- [ ] **Step 1: Generate three ATS test fixtures**

Create `docs/testing/fixtures/_make_ats_fixtures.py`:

```python
"""Generate ATS-check fixtures: a clean DOCX, one with a table, one with a header."""
from pathlib import Path
from docx import Document
from docx.shared import Pt

here = Path(__file__).parent

# ats_clean.docx — should PASS all checks
doc = Document()
doc.add_heading("Alex Test", level=0)
doc.add_paragraph("alex.test@example.invalid")
doc.add_heading("Summary", level=1)
doc.add_paragraph("Software engineer.")
doc.add_heading("Experience", level=1)
doc.add_paragraph("Senior Engineer, Example Corp, 2020 — Present.")
doc.save(str(here / "ats_clean.docx"))

# ats_with_table.docx — should FAIL the no-tables check
doc = Document()
doc.add_heading("Alex Test", level=0)
table = doc.add_table(rows=2, cols=2)
table.cell(0, 0).text = "Skill"
table.cell(0, 1).text = "Years"
table.cell(1, 0).text = "Python"
table.cell(1, 1).text = "8"
doc.save(str(here / "ats_with_table.docx"))

# ats_with_header.docx — should FAIL the critical-info-in-header check
doc = Document()
section = doc.sections[0]
header = section.header
header.paragraphs[0].text = "Alex Test · alex.test@example.invalid · +0 0000 000000"
doc.add_heading("Summary", level=1)
doc.add_paragraph("Software engineer.")
doc.save(str(here / "ats_with_header.docx"))

print("Wrote three ATS fixtures.")
```

Run once:
```
python docs\testing\fixtures\_make_ats_fixtures.py
```

- [ ] **Step 2: Write the failing tests**

Create `tests/validators/test_ats_check.py`:

```python
"""Tests for the ATS-safety validator."""
from pathlib import Path

from scripts.validators.ats_check import ats_check, AtsCheckResult

FIXTURES = Path(__file__).parent.parent.parent / "docs" / "testing" / "fixtures"


def test_clean_docx_passes():
    result = ats_check(FIXTURES / "ats_clean.docx")
    assert isinstance(result, AtsCheckResult)
    assert result.passed is True
    assert result.failures == []


def test_table_is_detected_as_failure():
    result = ats_check(FIXTURES / "ats_with_table.docx")
    assert result.passed is False
    failure_codes = [f.code for f in result.failures]
    assert "TABLE_PRESENT" in failure_codes


def test_header_with_critical_info_is_warned():
    result = ats_check(FIXTURES / "ats_with_header.docx")
    warning_codes = [w.code for w in result.warnings]
    failure_codes = [f.code for f in result.failures]
    assert "CRITICAL_INFO_IN_HEADER" in (warning_codes + failure_codes)


def test_result_includes_pass_warn_fail_counts():
    result = ats_check(FIXTURES / "ats_clean.docx")
    assert hasattr(result, "passed")
    assert hasattr(result, "warnings")
    assert hasattr(result, "failures")
```

- [ ] **Step 3: Run tests to verify they fail**

```
pytest tests/validators/test_ats_check.py -v
```
Expected: ImportError.

- [ ] **Step 4: Write the implementation**

Create `scripts/validators/ats_check.py`:

```python
"""Deterministic ATS-safety checks for a DOCX resume.

Reads the ATS hard rules from ``references/ats-rules.md`` and verifies a DOCX
file conforms to them. Returns a structured result with ``passed`` flag,
``warnings`` and ``failures`` lists.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union

from docx import Document


@dataclass
class AtsFinding:
    code: str
    message: str


@dataclass
class AtsCheckResult:
    passed: bool
    failures: List[AtsFinding] = field(default_factory=list)
    warnings: List[AtsFinding] = field(default_factory=list)


# Keywords suggesting critical contact info in header/footer.
CRITICAL_INFO_TOKENS = ("@", "+", "phone", "email")


def ats_check(path: Union[str, Path]) -> AtsCheckResult:
    """Run ATS-safety checks on a DOCX resume."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"DOCX not found: {path}")

    doc = Document(str(path))
    failures: List[AtsFinding] = []
    warnings: List[AtsFinding] = []

    # Hard rule: no tables.
    if doc.tables:
        failures.append(AtsFinding(
            code="TABLE_PRESENT",
            message=f"Document contains {len(doc.tables)} table(s). ATS parsers cannot reliably read tables.",
        ))

    # Hard rule: no critical info in headers or footers.
    for section in doc.sections:
        for hf in (section.header, section.footer):
            text = " ".join(p.text for p in hf.paragraphs).strip()
            if text and any(token in text.lower() for token in CRITICAL_INFO_TOKENS):
                failures.append(AtsFinding(
                    code="CRITICAL_INFO_IN_HEADER",
                    message=(
                        f"Header/footer contains contact-like info: {text!r}. "
                        "Many ATS parsers ignore headers and footers — move contact info into the body."
                    ),
                ))

    # Soft rule: text-box / shape presence is harder to detect via python-docx alone.
    # For v0.1 we accept this gap and document it.

    passed = len(failures) == 0
    return AtsCheckResult(passed=passed, failures=failures, warnings=warnings)
```

- [ ] **Step 5: Run tests to verify they pass**

```
pytest tests/validators/test_ats_check.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 6: Commit**

```
git add scripts/validators/ats_check.py tests/validators/test_ats_check.py docs/testing/fixtures/_make_ats_fixtures.py docs/testing/fixtures/ats_*.docx
git commit -m "feat: add deterministic ATS-safety validator for DOCX"
```

---

## Task 16 — Implement `scripts/validators/bias_scan.py` (TDD) — ten-pattern coverage

**Files:**
- Create: `tests/fixtures/bias_fixtures.py` (Python module with fixture text strings)
- Create: `tests/validators/test_bias_scan.py`
- Create: `scripts/validators/bias_scan.py`

This is a critical task — it must cover **all 10 ND-bias patterns** from `references/nd-bias-patterns.md`. Patterns 1, 2, 6, 7, 10 must be detected deterministically. Patterns 3, 4, 5, 8, 9 are partial-coverage; the validator returns a "needs Claude review" flag for those.

### Steps

- [ ] **Step 1: Create fixture-text module**

Create `tests/fixtures/bias_fixtures.py`:

```python
"""Fixture text strings for the bias scanner — one per pattern.

Each fixture is a small piece of synthetic resume text that should
trigger exactly one pattern. NO REAL PII.
"""

PATTERN_1_SOFT_SKILLS = (
    "Passionate self-starter who thrives in fast-paced environments and brings "
    "synergy to every project."
)

PATTERN_2_GAP_EXPLANATION = (
    "2021 — 2022: Career break to focus on personal health and recovery."
)

PATTERN_3_SHORT_TENURES = (
    "Junior Engineer, Company A, Jan 2023 — Aug 2023\n"
    "Associate Engineer, Company B, Sep 2023 — Mar 2024\n"
    "Engineer, Company C, Apr 2024 — Oct 2024"
)

PATTERN_4_HYPERFOCUS = (
    "Deep expertise in PostgreSQL query optimisation, PostgreSQL replication, "
    "PostgreSQL extensions, PostgreSQL internals, PostgreSQL performance tuning."
)

PATTERN_5_UNDER_CLAIM = (
    "Was part of a team that contributed to the redesign. Helped with the migration."
)

PATTERN_6_DIRECT_ND = (
    "Volunteer mentor with Autism Spectrum Society. Active in ADHD advocacy."
)

PATTERN_7_INDIRECT_ND = (
    "Certified Neurodiversity-Affirming Practitioner. Speaker at Autistic Pride conference."
)

PATTERN_8_NO_WARMTH = (
    "Engineer. Eight years experience. Delivered systems. Reduced latency."
)

PATTERN_9_OVER_PRECISION = (
    "Reduced p99 latency by 47.3% over a rolling 14-day window measured at the load balancer."
)

PATTERN_10_MIXED_IDENTITY = (
    "Autistic engineer with a person with ADHD background. Identity-first speaker, "
    "person with disabilities advocate."
)
```

- [ ] **Step 2: Write the failing tests (one per pattern, 10 tests minimum)**

Create `tests/validators/test_bias_scan.py`:

```python
"""Tests for the ND-bias deterministic scanner.

Every one of the 10 patterns in references/nd-bias-patterns.md must be detectable
either as a confident hit (patterns 1, 2, 6, 7, 10) or as a 'needs-review' flag
(patterns 3, 4, 5, 8, 9).
"""
from scripts.validators.bias_scan import bias_scan
from tests.fixtures import bias_fixtures as fx


def _pattern_codes(result):
    return [f.pattern_code for f in result.findings]


def test_pattern_1_soft_skills_coded_vocabulary():
    result = bias_scan(fx.PATTERN_1_SOFT_SKILLS)
    assert "ND_BIAS_P1_SOFT_SKILLS" in _pattern_codes(result)


def test_pattern_2_gap_explanation_on_resume():
    result = bias_scan(fx.PATTERN_2_GAP_EXPLANATION)
    assert "ND_BIAS_P2_GAP_EXPLANATION" in _pattern_codes(result)


def test_pattern_3_short_tenures_flagged_for_review():
    result = bias_scan(fx.PATTERN_3_SHORT_TENURES)
    assert "ND_BIAS_P3_SHORT_TENURES_REVIEW" in _pattern_codes(result)


def test_pattern_4_hyperfocus_flagged_for_review():
    result = bias_scan(fx.PATTERN_4_HYPERFOCUS)
    assert "ND_BIAS_P4_HYPERFOCUS_REVIEW" in _pattern_codes(result)


def test_pattern_5_under_claim_flagged_for_review():
    result = bias_scan(fx.PATTERN_5_UNDER_CLAIM)
    assert "ND_BIAS_P5_UNDER_CLAIM_REVIEW" in _pattern_codes(result)


def test_pattern_6_direct_nd_signal_terms():
    result = bias_scan(fx.PATTERN_6_DIRECT_ND)
    assert "ND_BIAS_P6_DIRECT_SIGNAL" in _pattern_codes(result)


def test_pattern_7_indirect_nd_signal_terms():
    result = bias_scan(fx.PATTERN_7_INDIRECT_ND)
    assert "ND_BIAS_P7_INDIRECT_SIGNAL" in _pattern_codes(result)


def test_pattern_8_no_warmth_flagged_for_review():
    result = bias_scan(fx.PATTERN_8_NO_WARMTH)
    assert "ND_BIAS_P8_NO_WARMTH_REVIEW" in _pattern_codes(result)


def test_pattern_9_over_precision_flagged_for_review():
    result = bias_scan(fx.PATTERN_9_OVER_PRECISION)
    assert "ND_BIAS_P9_OVER_PRECISION_REVIEW" in _pattern_codes(result)


def test_pattern_10_mixed_identity_language():
    result = bias_scan(fx.PATTERN_10_MIXED_IDENTITY)
    assert "ND_BIAS_P10_MIXED_IDENTITY" in _pattern_codes(result)


def test_clean_text_returns_no_findings():
    clean = (
        "Software engineer with eight years of experience. Built ingestion pipeline "
        "processing 50 million events daily. Reduced query latency 40 percent."
    )
    result = bias_scan(clean)
    confident = [f for f in result.findings if not f.pattern_code.endswith("_REVIEW")]
    assert confident == []
```

- [ ] **Step 3: Run tests to verify they fail**

```
pytest tests/validators/test_bias_scan.py -v
```
Expected: ImportError.

- [ ] **Step 4: Write the implementation**

Create `scripts/validators/bias_scan.py`:

```python
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
    if re.search(r"\b\d+\.\d+%\b", text):
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
```

- [ ] **Step 5: Run tests to verify they pass**

```
pytest tests/validators/test_bias_scan.py -v
```
Expected: all 11 tests PASS.

- [ ] **Step 6: Commit**

```
git add scripts/validators/bias_scan.py tests/validators/test_bias_scan.py tests/fixtures/bias_fixtures.py
git commit -m "feat: add ND-bias deterministic scanner covering all 10 patterns"
```

---

## Task 17 — Create `templates/coaching_report.md`

**Files:**
- Create: `templates/coaching_report.md`

### Document contract

A markdown skeleton with placeholder substitution markers. The coaching report generator (Task 18) fills these in.

### Steps

- [ ] **Step 1: Write the template**

Create `templates/coaching_report.md`:

```markdown
# {{REPORT_TITLE}}

**Prepared:** {{REPORT_DATE}}
**Resume reviewed:** {{RESUME_FILENAME}}
**Reviewer:** BRAINS Resume Skill (v{{SKILL_VERSION}})

---

## Summary

{{EXECUTIVE_SUMMARY}}

## ATS-safety findings

**Status:** {{ATS_STATUS}}

{{ATS_FINDINGS}}

## ND-bias findings

The following patterns were detected. Each finding is a suggestion, never a directive — your judgement always wins.

{{BIAS_FINDINGS}}

## Recommended next steps

{{NEXT_STEPS}}

---

{{TRUST_FOOTER_LINE}}

Built by neurodivergent minds, for neurodivergent people.
```

Placeholders the generator must fill:
- `{{REPORT_TITLE}}` — e.g., "Resume Coaching Report"
- `{{REPORT_DATE}}` — ISO date
- `{{RESUME_FILENAME}}` — basename of input file
- `{{SKILL_VERSION}}` — from pyproject.toml
- `{{EXECUTIVE_SUMMARY}}` — Claude-written summary
- `{{ATS_STATUS}}` — "PASS" / "WARN" / "FAIL"
- `{{ATS_FINDINGS}}` — markdown list of findings or "No issues detected."
- `{{BIAS_FINDINGS}}` — markdown list grouped by pattern
- `{{NEXT_STEPS}}` — Claude-suggested next steps
- `{{TRUST_FOOTER_LINE}}` — present on disclosure worksheets only; blank otherwise

- [ ] **Step 2: Commit**

```
git add templates/coaching_report.md
git commit -m "feat: add coaching report markdown template"
```

---

## Task 18 — Implement `scripts/generators/coaching_report_to_pdf.py` (TDD)

**Files:**
- Create: `tests/generators/test_coaching_report_to_pdf.py`
- Create: `scripts/generators/coaching_report_to_pdf.py`

### Steps

- [ ] **Step 1: Write the failing test**

Create `tests/generators/test_coaching_report_to_pdf.py`:

```python
"""Tests for the branded coaching-report PDF generator."""
from pathlib import Path
import pdfplumber
import pytest

from scripts.generators.coaching_report_to_pdf import render_coaching_report_pdf


def test_renders_pdf_with_provided_content(tmp_path):
    out = tmp_path / "report.pdf"
    render_coaching_report_pdf(
        out_path=out,
        title="Resume Coaching Report",
        resume_filename="alex_test_resume.docx",
        skill_version="0.1.0",
        executive_summary="Three items to address before submission.",
        ats_status="WARN",
        ats_findings="- Header contains contact info.",
        bias_findings="- Pattern 1: soft-skills vocabulary detected.",
        next_steps="- Move contact details into the body.",
        include_trust_footer=False,
        brand_mark_path=Path("assets") / "brains-mark-light-bg.png",
    )
    assert out.exists()
    assert out.stat().st_size > 0


def test_pdf_contains_expected_text(tmp_path):
    out = tmp_path / "report.pdf"
    render_coaching_report_pdf(
        out_path=out,
        title="Resume Coaching Report",
        resume_filename="alex_test_resume.docx",
        skill_version="0.1.0",
        executive_summary="Summary marker XYZ123.",
        ats_status="PASS",
        ats_findings="No issues detected.",
        bias_findings="No patterns detected.",
        next_steps="Resume is in good shape.",
        include_trust_footer=False,
        brand_mark_path=Path("assets") / "brains-mark-light-bg.png",
    )
    with pdfplumber.open(out) as pdf:
        all_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    assert "Resume Coaching Report" in all_text
    assert "Summary marker XYZ123" in all_text
    assert "Built by neurodivergent minds, for neurodivergent people." in all_text


def test_pdf_includes_trust_footer_when_requested(tmp_path):
    out = tmp_path / "report.pdf"
    render_coaching_report_pdf(
        out_path=out,
        title="Disclosure Worksheet",
        resume_filename="n/a",
        skill_version="0.1.0",
        executive_summary="Summary.",
        ats_status="N/A",
        ats_findings="N/A",
        bias_findings="N/A",
        next_steps="N/A",
        include_trust_footer=True,
        brand_mark_path=Path("assets") / "brains-mark-light-bg.png",
    )
    with pdfplumber.open(out) as pdf:
        all_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    assert "Disclosure guidance developed with BRAINS Trust safeguarding principles." in all_text
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/generators/test_coaching_report_to_pdf.py -v
```
Expected: ImportError.

- [ ] **Step 3: Write the implementation**

Create `scripts/generators/coaching_report_to_pdf.py`:

```python
"""Render a branded BRAINS coaching report PDF.

Reads styling parameters from references/brand-application.md:
- Body: Atkinson Hyperlegible (falls back to Helvetica if font not installed)
- Headings: Inter Bold (falls back to Helvetica-Bold)
- Heading colour: Gold Deep #D99518 on white
- BRAINS mark top-left header
- Footer with the protected origin phrase, verbatim
- Optional BRAINS Trust safeguarding-credit line above the footer
"""
from pathlib import Path
from typing import Union

from reportlab.lib.colors import HexColor, black, grey
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
)


GOLD_DEEP = HexColor("#D99518")
BODY_COLOUR = HexColor("#1A1A1A")
ORIGIN_PHRASE = "Built by neurodivergent minds, for neurodivergent people."
TRUST_FOOTER = "Disclosure guidance developed with BRAINS Trust safeguarding principles."


def _make_styles():
    h1 = ParagraphStyle(
        name="H1",
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=GOLD_DEEP,
        spaceAfter=12,
    )
    h2 = ParagraphStyle(
        name="H2",
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=GOLD_DEEP,
        spaceAfter=10,
        spaceBefore=14,
    )
    body = ParagraphStyle(
        name="Body",
        fontName="Helvetica",
        fontSize=11,
        textColor=BODY_COLOUR,
        leading=16,
    )
    meta = ParagraphStyle(
        name="Meta",
        fontName="Helvetica",
        fontSize=9,
        textColor=grey,
    )
    footer = ParagraphStyle(
        name="Footer",
        fontName="Helvetica",
        fontSize=9,
        textColor=grey,
        alignment=1,  # centre
    )
    return h1, h2, body, meta, footer


def render_coaching_report_pdf(
    out_path: Union[str, Path],
    title: str,
    resume_filename: str,
    skill_version: str,
    executive_summary: str,
    ats_status: str,
    ats_findings: str,
    bias_findings: str,
    next_steps: str,
    include_trust_footer: bool,
    brand_mark_path: Union[str, Path],
) -> Path:
    """Render a BRAINS-branded coaching report PDF.

    Parameters
    ----------
    out_path : path
        Where to write the PDF.
    title : str
    resume_filename : str
    skill_version : str
    executive_summary : str
    ats_status : str
    ats_findings : str
    bias_findings : str
    next_steps : str
    include_trust_footer : bool
        If True, render the BRAINS Trust safeguarding credit line above the standard footer.
        Used for disclosure worksheets.
    brand_mark_path : path
        Path to the BRAINS mark PNG to place top-left.
    """
    out_path = Path(out_path)
    brand_mark_path = Path(brand_mark_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    h1, h2, body, meta, footer = _make_styles()

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    story = []

    if brand_mark_path.exists():
        story.append(Image(str(brand_mark_path), width=1.2 * inch, height=0.5 * inch))
        story.append(Spacer(1, 12))

    story.append(Paragraph(title, h1))
    story.append(Paragraph(f"Resume reviewed: {resume_filename}", meta))
    story.append(Paragraph(f"BRAINS Resume Skill v{skill_version}", meta))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Summary", h2))
    story.append(Paragraph(executive_summary, body))

    story.append(Paragraph("ATS-safety findings", h2))
    story.append(Paragraph(f"Status: <b>{ats_status}</b>", body))
    story.append(Spacer(1, 6))
    for line in ats_findings.splitlines():
        if line.strip():
            story.append(Paragraph(line, body))

    story.append(Paragraph("ND-bias findings", h2))
    for line in bias_findings.splitlines():
        if line.strip():
            story.append(Paragraph(line, body))

    story.append(Paragraph("Recommended next steps", h2))
    for line in next_steps.splitlines():
        if line.strip():
            story.append(Paragraph(line, body))

    story.append(Spacer(1, 24))

    if include_trust_footer:
        story.append(Paragraph(TRUST_FOOTER, footer))
        story.append(Spacer(1, 6))

    story.append(Paragraph(ORIGIN_PHRASE, footer))

    doc.build(story)
    return out_path
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/generators/test_coaching_report_to_pdf.py -v
```
Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```
git add scripts/generators/coaching_report_to_pdf.py tests/generators/test_coaching_report_to_pdf.py
git commit -m "feat: add branded BRAINS coaching report PDF generator"
```

---

## Task 19 — Write `SKILL.md` (the always-loaded core)

**Files:**
- Create: `SKILL.md`

### Document contract

This is the entrypoint to the skill. Claude loads this on every invocation. Keep it lean — target 300-450 lines.

**Required sections, in order:**

1. **YAML frontmatter:**
```yaml
---
name: brains-resume
description: Use when a user asks for help reviewing, editing, creating, customising, or tailoring a resume or cover letter — particularly when neurodivergence-aware bias mitigation matters. Handles resume review, ATS-safety checks, ND-bias scanning, disclosure decision coaching, LinkedIn ingestion, and career-change translation. A BRAINS Incubator project.
version: 0.1.0
license: MIT
---
```

2. **What this skill does** — 2-3 sentence intro

3. **Workflow router** — markdown table mapping intent → workflow reference file:

| User intent | Load workflow file |
|---|---|
| Review my resume / critique my resume / audit my resume | `references/workflows/review.md` |
| Help me decide whether/how to disclose my neurodivergence | `references/workflows/disclosure.md` |
| (Other workflows ship in v0.5+) | — |

4. **ND-bias principles (cross-cutting — always loaded)** — 10 summary bullets, one per pattern family. State the user-veto principle explicitly.

5. **Disclosure stance framework (cross-cutting)** — short summary of the hybrid default: affirmative framing as the bias-minimised easy path, explicit disclosure as a respected first-class option. Pointer to `references/disclosure-decision-tree.md` for the full framework. Include the safeguarding caveat verbatim.

6. **BRAINS branding rules summary** — the on-outputs rules in 6 lines:
   - Branded: coaching reports, disclosure worksheets
   - Unbranded: resumes and cover letters submitted to employers
   - Identity-first language by default
   - Never puzzle-piece imagery, never AI-generated images of people, never deficit framing in defaults
   - Pointer to `references/brand-application.md`

7. **Privacy contract** — the six guarantees verbatim from the design spec §11

8. **First-use behaviour** — what to do on the first invocation in a session:
   - Greet briefly
   - Show the capability menu (the 9 workflows; for v0.1.0, only review and disclosure are live — the rest say "ships in v0.5")
   - Show the one-time privacy notice
   - Offer to start a workflow

9. **Tooling notes** — pointer that scripts live in `scripts/`, run with the project venv

### Steps

- [ ] **Step 1: Write `SKILL.md`** per the contract

Target 300-450 lines.

- [ ] **Step 2: Verify all 9 capabilities are listed in the menu**

Even though only 2 are live in v0.1.0, the menu shows all 9 (with "ships in v0.5" tags for the 7 not yet implemented) so users know what's coming.

- [ ] **Step 3: Verify the 10 ND-bias bullets in §4 match the 10 families in `references/nd-bias-patterns.md`**

One-for-one mapping.

- [ ] **Step 4: Verify the safeguarding caveat appears in §5**

Verbatim from the design spec §6: "general guidance, not legal or medical advice; consult an employment advocate, disability-rights lawyer, or where relevant a clinician."

- [ ] **Step 5: Commit**

```
git add SKILL.md
git commit -m "feat: add always-loaded SKILL.md core with router and cross-cutting principles"
```

---

## Task 20 — End-to-end smoke test for the review workflow

**Files:**
- Create: `tests/test_smoke_review_workflow.py`

### Steps

- [ ] **Step 1: Write the smoke test**

This test runs the deterministic portions of the review workflow end-to-end on the synthetic DOCX fixture. It doesn't test the Claude-contextual portions (those need a live model). It does verify that all the deterministic pieces compose cleanly.

Create `tests/test_smoke_review_workflow.py`:

```python
"""Smoke test for the deterministic portion of the resume-review workflow.

This test verifies that the parsers, validators, and coaching-report generator
compose end-to-end without errors. It does not test the contextual Claude review
portions (patterns 3, 4, 5, 8, 9) — those need a live model.
"""
from pathlib import Path

import pdfplumber

from scripts.parsers.docx_to_text import parse_docx_resume
from scripts.validators.ats_check import ats_check
from scripts.validators.bias_scan import bias_scan
from scripts.generators.coaching_report_to_pdf import render_coaching_report_pdf

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURE_DOCX = PROJECT_ROOT / "docs" / "testing" / "fixtures" / "synthetic_resume_basic.docx"
BRAND_MARK = PROJECT_ROOT / "assets" / "brains-mark-light-bg.png"


def test_review_workflow_runs_end_to_end(tmp_path):
    # Parse the resume.
    parsed = parse_docx_resume(FIXTURE_DOCX)
    assert parsed["raw_text"], "Parser returned empty text"

    # Run validators.
    ats = ats_check(FIXTURE_DOCX)
    bias = bias_scan(parsed["raw_text"])

    # Compose findings text.
    ats_status = "PASS" if ats.passed else "FAIL"
    ats_findings = (
        "No issues detected."
        if not (ats.failures or ats.warnings)
        else "\n".join(f"- {f.code}: {f.message}" for f in ats.failures + ats.warnings)
    )
    bias_findings = (
        "No patterns detected."
        if not bias.findings
        else "\n".join(f"- {f.pattern_code}: {f.suggestion}" for f in bias.findings)
    )

    # Render the report.
    out = tmp_path / "smoke_review.pdf"
    render_coaching_report_pdf(
        out_path=out,
        title="Resume Coaching Report",
        resume_filename=FIXTURE_DOCX.name,
        skill_version="0.1.0",
        executive_summary="Smoke-test summary.",
        ats_status=ats_status,
        ats_findings=ats_findings,
        bias_findings=bias_findings,
        next_steps="- (smoke test placeholder)",
        include_trust_footer=False,
        brand_mark_path=BRAND_MARK,
    )

    # Verify the PDF was written and contains expected branded content.
    assert out.exists()
    with pdfplumber.open(out) as pdf:
        all_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    assert "Built by neurodivergent minds, for neurodivergent people." in all_text
    assert "Resume Coaching Report" in all_text
```

- [ ] **Step 2: Run the smoke test**

```
pytest tests/test_smoke_review_workflow.py -v
```
Expected: PASS.

- [ ] **Step 3: Run the entire test suite to make sure nothing regressed**

```
pytest -v
```
Expected: all tests across all files PASS.

- [ ] **Step 4: Commit**

```
git add tests/test_smoke_review_workflow.py
git commit -m "test: add end-to-end smoke test for review workflow"
```

---

## Task 21 — Write `README.md`

**Files:**
- Create: `README.md`

### Document contract

**Required sections, in order:**

1. **Title:** `# BRAINS Resume Skill`
2. **One-line description** matching SKILL.md frontmatter
3. **Origin credit line:** `**An Incubator project from BRAINS — built by neurodivergent minds, for neurodivergent people.**` (uses two protected phrases verbatim; render in bold)
4. **What it does** — one-sentence summary of each of the 9 workflows. For v0.1.0, mark 7 as "ships in v0.5".
5. **Install** — clone, `pip install -e .`, and either copy or symlink the bundle to `~/.claude/skills/brains-resume/`
6. **Usage** — one short example for each live workflow (review, disclosure)
7. **Privacy** — the six guarantees verbatim from the design spec §11
8. **Status** — `v0.1.0 — foundation and resume-review workflow live. All other workflows ship in v0.5 (Plan 2).`
9. **Contributing** — pointer to `CONTRIBUTING.md`
10. **Licence** — `MIT — see LICENSE`
11. **Footer:** `*AI that works for every mind.*` (protected positioning phrase, verbatim, render italic only if rendering allows italics — otherwise plain. Markdown renders `*...*` as italic — that's a display concern, not a body-text accessibility concern. The brand rule is about italics in continuous body text; a footer tagline is fine.)

### Steps

- [ ] **Step 1: Write `README.md`** per the contract

Target 400-600 words. No third-party project references anywhere.

- [ ] **Step 2: Verify protected phrases are used verbatim**

Grep for:
- "Built by neurodivergent minds, for neurodivergent people."
- "AI that works for every mind."
- "An Incubator project from BRAINS"

Each should appear at least once, exactly as written.

- [ ] **Step 3: Verify no third-party project, organisation, or platform names appear**

Search for common third-party names that might have slipped in. None should appear.

- [ ] **Step 4: Commit**

```
git add README.md
git commit -m "docs: add README with usage, privacy, and Incubator origin credit"
```

---

## Task 22 — Write `CHANGELOG.md` and tag v0.1.0

**Files:**
- Create: `CHANGELOG.md`

### Steps

- [ ] **Step 1: Write `CHANGELOG.md`**

```markdown
# Changelog

All notable changes to the BRAINS Resume Skill are documented here.

The format follows Keep a Changelog conventions; the project follows semantic versioning.

## [0.1.0] — 2026-05-11

### Added

- Project skeleton, dependencies (`python-docx`, `pdfplumber`, `reportlab`, `trafilatura`, `pyyaml`), pytest configuration
- Always-loaded `SKILL.md` core with workflow router, ND-bias principles, disclosure stance framework, privacy contract, and first-use behaviour
- Foundational reference documents:
  - `references/nd-bias-patterns.md` — ten-pattern ND-bias catalog
  - `references/disclosure-decision-tree.md` — disclosure framework with safeguarding caveats
  - `references/language-do-dont.md` — ND-affirmative phrasing reference
  - `references/ats-rules.md` — ATS formatting rules
  - `references/resume-anatomy.md` — section-by-section ND-aware guidance
  - `references/brand-application.md` — when and how the brand applies to outputs
- Workflow references for `review` and `disclosure`
- PDF and DOCX resume parsers with section detection
- Deterministic ATS-safety validator
- Deterministic ND-bias scanner covering all ten pattern families
- Branded coaching report PDF generator (with optional BRAINS Trust safeguarding footer for disclosure worksheets)
- BRAINS brand marks imported into `assets/`
- End-to-end smoke test for the review workflow
- MIT licence, contribution guide, README

### Not yet shipped (planned for v0.5 in Plan 2)

- Resume create-from-scratch, edit, tailor-to-job-description workflows
- Cover-letter generation workflow
- LinkedIn ingestion workflow (with safeguarded `Connections.csv` exclusion)
- Career-change translator workflow
- Bias-aware ATS check workflow
- Resume-DOCX and resume-PDF generators
- Cover-letter DOCX generator
- Job-description URL parser
- Chronological resume DOCX template
- Cover letter DOCX template
```

- [ ] **Step 2: Commit and tag**

```
git add CHANGELOG.md
git commit -m "docs: add changelog for v0.1.0"
git tag -a v0.1.0 -m "v0.1.0 — foundation and review workflow"
```

- [ ] **Step 3: Verify the tag**

```
git tag -l
git log --oneline --decorate
```
Expected: `v0.1.0` appears in tag list and on the most recent commit.

- [ ] **Step 4: Final verification — run the entire test suite once more**

```
pytest -v
```
Expected: every test PASSES.

---

## Plan complete

At this point the bundle contains:
- A working Claude Code skill (`SKILL.md` + on-demand references + scripts + assets)
- Two functional workflows (review + disclosure) with end-to-end smoke coverage
- The full ten-pattern ND-bias scanning catalog with deterministic coverage
- Branded BRAINS coaching report generation
- Release-ready repo with README, CHANGELOG, LICENSE, CONTRIBUTING

**Next:** Plan 2 will add the remaining seven workflows (create, edit, tailor, cover-letter, LinkedIn-ingest, career-change, bias-aware-ATS-check), the resume / cover-letter generators, and finalise v1.0.0.

---

*End of Plan 1.*
