# BRAINS Resume Skill — Claude Project setup

The BRAINS Resume Skill works in two environments:

- **Claude Code (CLI)** — full functionality, including local Python scripts (parsers, validators, generators). This is the primary distribution.
- **Claude.ai Projects (web)** — the conversational workflows (review, disclosure, edit, tailor, cover letter, create, career-change, bias-check) work, but the local Python scripts do not run in claude.ai. Deterministic checks (ATS-safety, ND-bias regex, integrity) operate as Claude-side judgments rather than script outputs.

This guide explains the Claude Project setup.

## What you get in a Claude Project

- All nine workflows are usable conversationally
- The full ND-bias pattern catalog (10 families) is loaded as project knowledge
- The disclosure decision framework is loaded
- The brand-application rules are loaded
- The coaching-report markdown template is loaded

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
5. Add each `references/workflows/*.md` file as project knowledge.
6. Add `templates/coaching_report.md` as project knowledge.

## Using the Project

Once set up, just talk to Claude in the Project — `Please review my resume:` followed by the resume text. Claude will follow the same workflows as in Claude Code, surfacing the same findings, with the same safeguarding boundaries.

The Claude Project version is reliable for the conversational workflows but does not produce file artifacts. If you want a clean DOCX/PDF output, install the full skill in Claude Code (see the project README).

---

Built by neurodivergent minds, for neurodivergent people.
