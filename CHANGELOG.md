# Changelog

All notable changes to the BRAINS Resume Skill are documented here.

The format follows Keep a Changelog conventions; the project follows semantic versioning.

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
