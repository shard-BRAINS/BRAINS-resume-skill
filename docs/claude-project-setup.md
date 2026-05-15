# BRAINS Resume Skill — Claude Project setup

The BRAINS Resume Skill works in two environments:

- **Claude Code (CLI)** — full functionality, including local Python scripts (parsers, validators, generators). This is the primary distribution.
- **Claude.ai Projects (web)** — the conversational workflows (review, disclosure, edit, tailor, cover letter, create, JD analysis, pre-check, career-change, bias-check) work, but the local Python scripts do not run in claude.ai. Deterministic checks (ATS-safety, ND-bias regex, integrity) operate as Claude-side judgments rather than script outputs. The application tracker requires local file persistence and is Claude-Code-only.

This guide explains the Claude Project setup.

## What you get in a Claude Project

- All fourteen workflows are usable conversationally (including JD analysis, pre-check, and career-change)
- The full ND-bias pattern catalog (10 families) is loaded as project knowledge
- The disclosure decision framework is loaded
- The brand-application rules are loaded
- The coaching-report markdown template is loaded
- Template selection guidance (4 resume templates, 2 cover-letter templates) for the create/edit/tailor workflows

## Workflows available on claude.ai

1. Resume review
2. Disclosure coaching
3. Create resume from scratch
4. Edit / customise an existing resume
5. Tailor resume to a specific job description
6. Generate a matching cover letter
7. LinkedIn export ingestion
8. LinkedIn profile improvement (new in v1.1.0)
9. Resume + LinkedIn consolidation (new in v1.1.0)
10. Career-change translation
11. Bias-aware ATS final check
12. JD analyzer (new in v1.2.0)
13. Pre-application sanity check (new in v1.2.0)
14. Application tracker (new in v1.2.0 — CLI-only in this version; dashboard in v1.3.0)

See `references/template-selection.md` for the full decision tree guiding template choice (4 resume templates, 2 cover-letter templates) in the create/edit/tailor workflows.

### De-AI tool (v1.2.1+)

The skill includes an AI-signal validator (`/brains-deai`) that scans produced text for common AI-tell patterns and surfaces a 0-100 score with rewrite suggestions. Auto-runs in the bias-aware final check; available standalone. See `references/ai-signal-patterns.md` for the nine-pattern catalog.

### Dashboard (v1.3.0+)

The skill includes a local Streamlit dashboard accessible via `brains-resume-dashboard` after install. It is **Claude-Code-only** — claude.ai cannot run Streamlit, and the dashboard depends on the local SQLite tracker file under `~/.brains-resume/`. See the README's "Launching the dashboard" section for details.

From v1.4.0, the dashboard also exposes every slash command via a Workflows tab and inline action buttons — see the README's "What's new in v1.4.0" subsection for details.

## What is different from Claude Code

| Feature | Claude Code | Claude Project |
|---|---|---|
| File-based input | Yes (PDF/DOCX paths) | No — paste resume text |
| ATS-safety validator | Deterministic Python script | Claude-side judgment against the same rules |
| ND-bias scanner | Deterministic regex backstop | Claude-side judgment against the same catalog |
| Integrity check | Deterministic regex | Claude-side judgment |
| DOCX/PDF output | Yes (generators produce files) | Markdown text only — copy/paste into Word |
| Slash commands | Yes (/brains-review etc.) | No — invoke by natural language |
| LinkedIn ZIP ingestion | Yes (with PII exclusion) | Paste relevant CSV contents manually |
| Application tracker (`/brains-track`, SQLite at `~/.brains-resume/`) | Yes — full functionality | No — claude.ai cannot persist local files; the tracker is Claude-Code-only |

## Setting up the Project

1. Open claude.ai and create a new Project.
2. Name it "BRAINS Resume Skill" (or similar).
3. In the Project's custom instructions, paste the contents of `SKILL.md` (skip the YAML frontmatter — paste from "What this skill does" onwards).
4. Add the contents of each `references/*.md` file as project knowledge documents:
   - `nd-bias-patterns.md` (highest priority — the ten-pattern catalog)
   - `disclosure-decision-tree.md`
   - `ats-rules.md`
   - `language-do-dont.md`
   - `resume-anatomy.md`
   - `brand-application.md`
   - `template-selection.md` (decision tree for resume and cover-letter templates)
5. Add each `references/workflows/*.md` file as project knowledge.
6. Add `templates/coaching_report.md` as project knowledge.

## Using the Project

Once set up, just talk to Claude in the Project — `Please review my resume:` followed by the resume text. Claude will follow the same workflows as in Claude Code, surfacing the same findings, with the same safeguarding boundaries.

The Claude Project version is reliable for the conversational workflows but does not produce file artifacts. If you want a clean DOCX/PDF output, install the full skill in Claude Code (see the project README).

---

Built by neurodivergent minds, for neurodivergent people.
