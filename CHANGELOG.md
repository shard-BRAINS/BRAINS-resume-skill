# Changelog

All notable changes to the BRAINS Resume Skill are documented here.

The format follows Keep a Changelog conventions; the project follows semantic versioning.

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

## [1.2.0] — 2026-05-13

### Added
- **Application tracker** — SQLite store at `~/.brains-resume/tracker.db` with 5 entity tables (resume_versions, cover_letters, jds, applications, outcomes) and migrations support. Public Python API at `scripts/tracker/{add,query,profile}.py`. Opt-in — never created unless the user invokes a tracker workflow.
- **User profile store** — `~/.brains-resume/profile.json` holds focus areas and self-defined healthy weekly application rate. The skill never recommends a rate; it asks once and uses what the user provides.
- **JD analyzer validator** (`scripts/validators/jd_analyzer.py`) — six-code finding catalog: soft-culture red flags, masking-cost markers, evidence-of-real-flexibility, required-vs-nice parsing, role-fit scoring against user focus areas, duplicate-application detection against the tracker.
- **JD analyzer workflow** (`/brains-jd-analyze`) — surfaces ND-relevant signals in a JD; offers to persist to the tracker.
- **Pre-application sanity check workflow** (`/brains-precheck`) — six-question coaching pass before submission: duplicate check, findings recap, fit-or-pressure question, pacing check, cover-letter check, channel+agency. Never blocks submission.
- **Application tracker slash command** (`/brains-track`) — composite command with subcommands: `add`, `update`, `list`, `summary`, `focus-areas`, `healthy-rate`. All output is markdown rendered in chat.
- **Opt-in integration with existing workflows** — `brains-tailor`, `brains-cover-letter`, `brains-review`, `brains-check` now prompt at end-of-workflow to register the artifact in the tracker. Users who consistently decline never create the tracker db.
- **SQLite migration system** — numbered migration scripts in `scripts/tracker/migrations/`. Migration `0001_initial_schema` ships with v1.2.0; future schema changes follow the same pattern.
- **Test isolation via environment variables** — `BRAINS_TRACKER_DB_PATH` and `BRAINS_TRACKER_PROFILE_PATH` override the default paths for test fixtures.

### Changed
- **SKILL.md router** — three new workflow entries; capability menu and slash-command list updated to reflect fourteen live workflows.
- **`references/brand-application.md`** — Split-rule table extended for tracker CLI output, JD analyzer reports, and the pre-application check summary.
- **`README.md`** — slash-command list updated; new "Tracking applications" section added.
- **Claude Project bundle** — rebuilt to include new reference docs (the tracker itself is Claude-Code-only — claude.ai can't persist local files).

### Deferred to Phase 5 (v1.3.0)
- Streamlit dashboard UI built on top of this data layer.
- Pacing/burnout tracker as a dedicated dashboard page.
- Efficacy analytics with confidence bands.
- Anonymized community efficacy data (opt-in, future).

### Deferred (still)
- Interview prep skill (sibling, separate bundle).
- Salary negotiation skill (sibling, separate bundle).
- Network/referral lane as a first-class entity (folded into `channel` enum for v1.2.0).
- MCP server for Claude Desktop.

## [1.1.0] — 2026-05-13

### Added
- **Resume template library** — four templates total: `chronological` (existing, moved into `templates/resume/`), `functional` (new), `hybrid` (new), `executive` (new). All ATS-safe.
- **Cover-letter template library** — two templates total: `formal-business` (existing, moved into `templates/cover-letter/`), `modern-clean` (new).
- **Generator parameterisation** — `resume_to_docx`, `resume_to_pdf`, `cover_letter_to_docx`, and `cover_letter_to_pdf` now accept a `template=` keyword argument. Defaults preserve v1.0.x behaviour.
- **Template-selection reference** (`references/template-selection.md`) — decision tree, comparison tables, and ND framing on the functional-template recruiter-skepticism tradeoff with `hybrid` as the recommended middle path.
- **LinkedIn profile improvement workflow** (`/brains-linkedin-improve`) — rewrites Headline / About / Experience / Skills using the ND-aware framework, with character limits respected and copy-paste-ready markdown output.
- **Resume + LinkedIn consolidation workflow** (`/brains-consolidate`) — detects narrative inconsistencies between resume and LinkedIn (job title mismatches, date inconsistencies, achievement-only-in-X, tone divergence) and proposes three resolutions per finding (resume-leading, linkedin-leading, new synthesis). Read-only report; fixes via existing `/brains-edit` and `/brains-linkedin-improve` workflows.
- **New validator** — `scripts/validators/consolidation_check.py` with five finding codes covering the deltas the consolidation workflow surfaces.

### Changed
- **Template directory layout** — `templates/resume_chronological.docx` moved to `templates/resume/chronological.docx`. `templates/cover_letter.docx` moved to `templates/cover-letter/formal-business.docx`. Template-generator scripts under `scripts/packaging/` renamed to match the new layout.
- **SKILL.md router** — two new workflow entries; capability menu and slash-command list updated to reflect eleven live workflows.
- **`references/brand-application.md`** — Split-rule table extended to cover new artifact types (LinkedIn profile rewrite output and consolidation report).
- **`README.md`** — slash-command list updated; new "Choosing a template" section added.
- **Claude Project bundle** — rebuilt to include new reference docs.

### Deferred to Phase 3
- MCP server for Claude Desktop.
- Creative / graphical resume templates (excluded for ATS-safety + ND-bias reasons).
- Autonomous LinkedIn editing.
- Sibling skills (interview prep, salary negotiation).

## [1.0.0] — 2026-05-12

### Added

- Seven new workflows live: create-from-scratch, edit/customise, tailor-to-JD, cover-letter generation, LinkedIn ingestion (with strict third-party-PII exclusion), career-change translator, bias-aware ATS final check
- New `integrity_check.py` validator: prompt-injection, instruction-override, system-prompt, and hidden-keyword-stuffing detection
- Hardened DOCX parser: detects sections via Word heading styles, bold/large-font runs, and keyword vocabulary
- New `render_from_markdown` entrypoint on coaching-report PDF generator (eliminates the inline-substitution bug surfaced in v0.1.x testing)
- Resume DOCX/PDF generators (unbranded) and ATS-safe chronological template
- Cover-letter DOCX/PDF generators (unbranded) and template
- LinkedIn ZIP parser with strict `Connections.csv` / `messages.csv` / `Invitations.csv` exclusion
- Job-description URL fetcher
- One-line installers for Windows (`install.ps1`) and macOS/Linux (`install.sh`)
- Slash commands for every workflow (`/brains-review`, `/brains-disclosure`, `/brains-edit`, `/brains-tailor`, `/brains-cover-letter`, `/brains-create`, `/brains-linkedin`, `/brains-career-change`, `/brains-check`)
- Claude Project bundle (`dist/brains-resume-claude-project.zip`) for claude.ai users; setup guide in `docs/claude-project-setup.md`
- End-to-end smoke tests for every workflow (83 tests total)

### Fixed

- Brand-mark distortion in coaching report PDFs (preserves natural aspect ratio)
- Stale `scripts/bias_scan.py` paths in `SKILL.md` (now `scripts/validators/bias_scan.py`)
- `BiasFinding` field-name documentation drift in `SKILL.md`

### Deprecated (not yet removed)

- `datetime.utcnow()` usage in `bias_scan.py` will be replaced with `datetime.now(timezone.utc)` in a future release

### Not yet shipped (planned for v1.5 / Plan 3)

- Template library / multiple visual variants
- LinkedIn profile review and improvement workflow
- Full LinkedIn + resume consolidation
- MCP server for Claude Desktop
- Interview prep skill (sibling)
- Salary negotiation skill (sibling)

## [0.1.0] — 2026-05-12

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
