<!-- markdownlint-disable-file MD041 MD001 -->
<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/shard-BRAINS/.github/main/profile/brand-mark-dark-bg.png">
  <img alt="BRAINS" src="https://raw.githubusercontent.com/shard-BRAINS/.github/main/profile/brand-mark-light-bg.png" width="220">
</picture>

# BRAINS Resume Skill

### A neurodivergence-aware résumé, cover-letter, and LinkedIn toolkit

<br />

[![Version](https://img.shields.io/badge/version-v1.5.0-D99518?style=for-the-badge&labelColor=0A0A0A)](CHANGELOG.md)
[![Status](https://img.shields.io/badge/status-shipped-D99518?style=for-the-badge&labelColor=0A0A0A)](STATUS.yml)
[![BRAINS Certified Gold](https://img.shields.io/badge/BRAINS%20Certified-Gold-D99518?style=for-the-badge&labelColor=0A0A0A)](https://github.com/shard-BRAINS/BRAINS-template-repo)
[![Licence](https://img.shields.io/badge/licence-MIT-0A0A0A?style=for-the-badge&labelColor=D99518)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Community-5865F2?style=for-the-badge&logo=discord&logoColor=FFFFFF&labelColor=0A0A0A)](https://discord.gg/BEmTXXscBr)
[![Bluesky](https://img.shields.io/badge/Bluesky-%40brainscertified.com-D99518?style=for-the-badge&logo=bluesky&logoColor=FFFFFF&labelColor=0A0A0A)](https://bsky.app/profile/brainscertified.com)
[![Incubator](https://img.shields.io/badge/BRAINS-Incubator-4DA8FF?style=for-the-badge&labelColor=0A0A0A)](https://github.com/shard-BRAINS)

<br />

<a href="https://github.com/shard-BRAINS/BRAINS-template-repo" title="Meets the BRAINS standard floor"><img src="https://raw.githubusercontent.com/shard-BRAINS/BRAINS-template-repo/main/assets/badges/brains-certified-gold.svg" alt="BRAINS Certified — Gold Standard" height="86"></a>

<br />

[Install ↓](#install) &nbsp;·&nbsp; [Workflows ↓](#workflows) &nbsp;·&nbsp; [Dashboard ↓](#dashboard) &nbsp;·&nbsp; [Privacy ↓](#privacy)

</div>

---

<!-- readability: target grade 8 (public copy) -->

A Claude Code skill for neurodivergent job-seekers. It helps you review, write, edit, and tailor résumés and cover letters. It also spots bias patterns that screen out ND candidates — in software, and in human review.

> **Reliable, affirming, inclusive.**

**An Incubator project from [BRAINS](https://github.com/shard-BRAINS) — built by neurodivergent minds, for neurodivergent people.**

---

## Status

| | |
|---|---|
| **Current** | ![v1.5](https://img.shields.io/badge/-v1.5.0%20shipped-D99518?style=flat-square&labelColor=0A0A0A) per-JD output folders, traceable artifact UIDs |
| **In flight** | ![v1.6](https://img.shields.io/badge/-v1.6%20in%20progress-7A7A7A?style=flat-square&labelColor=0A0A0A) disclosure framework polish · target 2026-07-15 |

For the full version history, see [CHANGELOG.md](CHANGELOG.md).

---

## What it does

| Workflow | Status |
|---|---|
| **Résumé review** — checks an existing résumé. Flags ND-bias risks and ATS issues. Returns a plain-language coaching report. | ![live](https://img.shields.io/badge/-live-D99518?style=flat-square&labelColor=0A0A0A) |
| **Disclosure coaching** — guided decision framework. Covers whether, when, and how to share neurodivergent identity at each hiring stage. | ![live](https://img.shields.io/badge/-live-D99518?style=flat-square&labelColor=0A0A0A) |
| **Create from scratch** — builds a résumé via a structured interview. | ![live](https://img.shields.io/badge/-live-D99518?style=flat-square&labelColor=0A0A0A) |
| **Edit / customise** — improves a résumé without targeting a specific job. | ![live](https://img.shields.io/badge/-live-D99518?style=flat-square&labelColor=0A0A0A) |
| **Tailor to a JD** — adapts a résumé to a specific role. Reports keyword coverage. | ![live](https://img.shields.io/badge/-live-D99518?style=flat-square&labelColor=0A0A0A) |
| **Cover letter** — drafts a three-paragraph cover letter to match the tailored résumé and JD. | ![live](https://img.shields.io/badge/-live-D99518?style=flat-square&labelColor=0A0A0A) |
| **LinkedIn ingestion** — reads a LinkedIn ZIP export. Auto-skips third-party PII. | ![live](https://img.shields.io/badge/-live-D99518?style=flat-square&labelColor=0A0A0A) |
| **Career-change translation** — translates experience from one domain into another. Builds a clear skills-bridge. | ![live](https://img.shields.io/badge/-live-D99518?style=flat-square&labelColor=0A0A0A) |
| **Pre-submit check** — ATS, ND-bias, and integrity pass on a final résumé and cover letter. | ![live](https://img.shields.io/badge/-live-D99518?style=flat-square&labelColor=0A0A0A) |

---

## Workflow shape

```mermaid
flowchart TD
    INPUT([your résumé<br/>OR job description<br/>OR LinkedIn export])

    REVIEW[<b>Review &amp; coach</b><br/>brains-review · brains-disclosure]:::bucket
    AUTHOR[<b>Author</b><br/>brains-create · brains-edit · brains-tailor<br/>brains-cover-letter · brains-career-change]:::bucket
    QUALITY[<b>Quality &amp; ATS</b><br/>brains-jd-analyze · brains-precheck<br/>brains-check · brains-deai]:::bucket
    LINKEDIN[<b>LinkedIn</b><br/>brains-linkedin · brains-linkedin-improve<br/>brains-consolidate]:::bucket
    TRACK[<b>Track &amp; observe</b><br/>brains-track · brains-dashboard]:::bucket

    INPUT --> REVIEW
    INPUT --> AUTHOR
    INPUT --> LINKEDIN
    AUTHOR --> QUALITY
    QUALITY --> TRACK
    AUTHOR --> TRACK
    LINKEDIN --> TRACK

    classDef bucket fill:#FFFFFF,stroke:#D99518,stroke-width:2px,color:#0A0A0A
```

---

## Install

### One-line installers (recommended)

**Windows** (Command Prompt or PowerShell):

```text
.\install\install.cmd
```

The wrapper handles the default PowerShell execution policy. No system setting is changed. To call PowerShell directly:

```powershell
powershell -ExecutionPolicy Bypass -File .\install\install.ps1
```

**macOS / Linux:**

```bash
bash install/install.sh
```

### Manual install (fallback)

```bash
# 1. Clone
git clone https://github.com/shard-BRAINS/BRAINS-resume-skill.git
cd BRAINS-resume-skill

# 2. Create + activate a virtual environment
python -m venv .venv
#    Windows:
.venv\Scripts\activate
#    macOS / Linux:
source .venv/bin/activate

# 3. Install with dev dependencies
pip install -e ".[dev]"
```

**Install the skill bundle for Claude Code** — copy or symlink:

```bash
# Copy (most users)
cp -r . ~/.claude/skills/brains-resume/

# Symlink (edits take effect right away)
ln -s "$(pwd)" ~/.claude/skills/brains-resume
```

**Windows directory junction:**

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\brains-resume" -Target (Get-Location).Path
```

---

## Workflows

| Command | What it does |
|---|---|
| `/brains-review [path]` | Audit a résumé for ND-bias, ATS-safety, and integrity issues |
| `/brains-disclosure` | Walk through the disclosure-decision framework |
| `/brains-create` | Build a résumé from scratch via interactive interview |
| `/brains-edit [path]` | Apply review notes; produce a clean ATS-safe rewrite |
| `/brains-tailor [résumé] [jd]` | Tailor a résumé to a specific job description |
| `/brains-cover-letter [résumé] [jd]` | Generate a matched cover letter |
| `/brains-career-change [target]` | Translate experience into a new domain |
| `/brains-jd-analyze [jd]` | Analyse a job description for ND-relevant signals (red flags, masking cost, evidence of flex, role-fit score) |
| `/brains-precheck [résumé] [jd]` | Six-question coaching pass before submit. Registers the application in the tracker. |
| `/brains-check [résumé] [letter]` | Final pre-submit ATS, bias, and integrity pass |
| `/brains-deai` | Scan résumé / cover letter / LinkedIn text for AI-tell signals. 0–100 score with rewrite hints. |
| `/brains-linkedin [zip-path]` | Read a LinkedIn export. Third-party PII is auto-excluded. |
| `/brains-linkedin-improve` | Rewrite a LinkedIn profile (Headline / About / Experience / Skills) using the ND-aware framework |
| `/brains-consolidate` | Spot gaps between a résumé and a LinkedIn profile. Propose fixes. |
| `/brains-track [command]` | Manage the application tracker — add, log outcomes, view pipeline |
| `/brains-dashboard` | Launch the local Streamlit dashboard in a browser |

---

## Choosing a template

The skill ships **four résumé templates** and **two cover-letter templates**. All are ATS-safe. The choice is about narrative shape.

| Résumé template | Best for |
|---|---|
| `chronological` (default) | Linear career history with recent relevant experience |
| `functional` | Career-changers, employment gaps, skills-led story |
| `hybrid` | Career pivots with relevant transferable skills |
| `executive` | Senior roles, 15+ years experience, board / leadership framing |

| Cover-letter template | Best for |
|---|---|
| `formal-business` (default) | Traditional industries, regulated sectors |
| `modern-clean` | Tech / startup contexts |

The skill walks you through template choice during create, edit, or tailor. See `references/template-selection.md` for the full decision tree.

---

## Tracking applications

The tracker is **opt-in**. It stores data in a local SQLite file at `~/.brains-resume/tracker.db`. The file is built the first time you use it. If you never run `/brains-track` or `/brains-precheck`, no file is built.

The tracker holds:

- Résumé versions (with focus-area tags and tailored-from lineage)
- Job descriptions (with analyzer findings)
- Cover letters (linked to résumé + JD)
- Applications (with channel, agency, recruiter contact)
- Outcomes (callback, interview, offer, rejection, etc.)

From these you can ask:

- This-week pace vs your healthy weekly rate
- Per-template results — which template and JD pairs convert
- Open applications by company or by date
- Repeat-application checks — stop accidental re-apply

Use `/brains-track summary` for a pipeline view. Use `/brains-track update <id> <event-type>` to log outcomes. Use `/brains-track healthy-rate` to set the pace that suits you. The skill never tells you what that number should be.

---

## Dashboard

The skill ships a local **Streamlit dashboard**. After `pip install -e .`, launch from any terminal:

```text
brains-resume-dashboard
```

Opens at `http://localhost:8501`. Press **Ctrl+C** to stop.

### What you get

- **Overview** — pipeline funnel, summary tiles, sparkline trends, idle-state callouts, pending-callbacks panel
- **Résumés / Cover Letters / JDs** — tagged tables with focus areas, an AI-signal score per text, links to source files
- **Applications** — table filtered by company, channel, status, or date
- **Analytics** — results by template and channel
- **Pacing** — this-week count vs your self-defined healthy weekly rate. Includes a sensory-load notes journal.
- **Workflows** — every slash command as a card. Grouped into Résumé, JD & application, LinkedIn & coaching.
- **Inline action buttons** on Résumés, Cover Letters, JDs, and Applications — pick a row, run the workflow
- **In-dashboard validators** — de-AI scan, JD analyze, tracker CRUD, consolidation diff hand-off, final composite check, review preview. No Claude Code round-trip.
- **Clipboard hand-off** for LLM-heavy commands — click *"Copy /brains-X"* and paste into Claude Code. Optional audit log at `~/.brains-resume/handoffs/`.

The dashboard uses Incubator Blue with Gold Deep accents. Body text is Atkinson Hyperlegible. The theme is dark. It runs on localhost only. No telemetry. No outbound network. You can edit your profile and log outcomes. Everything else is read-only.

---

## Output organisation

All résumés and cover letters from the skill land in:

```text
~/.brains-resume/outputs/<JD-folder>/
```

…with a fixed filename pattern. See [`SKILL.md`](SKILL.md) § File organization for the full convention.

---

## Claude Desktop / claude.ai

A ready-to-import Claude Project bundle is at:

```text
dist/brains-resume-claude-project.zip
```

Full setup instructions: [`docs/claude-project-setup.md`](docs/claude-project-setup.md).

---

## Usage

### Résumé review

Paste or attach your résumé and ask Claude to review it:

```text
Review my résumé for ND-bias risks and ATS issues.
```

Or paste your résumé content. The skill picks the review workflow by default when it sees résumé content.

### Disclosure coaching

```text
I'm applying for a role and I'm not sure whether to disclose that I'm autistic. Can you walk me through the decision?
```

The skill runs the full disclosure framework. It covers factors, timing, and follow-up talking points. It returns a worksheet you can refer back to.

### All other workflows

Use the slash commands listed above. Or describe your goal in plain language. The skill router picks the right workflow for you.

---

## Privacy

**Six rules we do not bend. No setting changes them.**

1. Output files go to a folder you choose (default `./output/` in your working directory). Nothing is written into the skill bundle.
2. The skill ships a `.gitignore` template that excludes the output folder and common résumé filenames. This stops you from committing private content by accident.
3. On first use per session, the skill shows a plain-language notice. Your résumé content is processed by Claude within that session only.
4. The LinkedIn ZIP parser extracts only your own data. It skips `Connections.csv`, `messages.csv`, `Invitations.csv`, and any file with data about other people. It logs which files it skipped.
5. The skill keeps no data between sessions. Disclosure choice, employer details, salary expectations, and all résumé content are session-only.
6. No telemetry. No analytics. No phone-home.

---

## Contributing

We welcome help. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) first. It covers identity-first language, the code of conduct, and how to propose new features or new bias rules.

Want to pitch a project to the BRAINS Incubator? Email **[info@brainscertified.com](mailto:info@brainscertified.com?subject=Incubator%20application%20%E2%80%94%20%5Byour%20name%5D)**. See the [org page](https://github.com/shard-BRAINS) for the form.

---

## Licence

MIT — see [LICENSE](LICENSE).

---

<div align="center">

<br />

**AI that works for every mind.**

<br />

[![Made by](https://img.shields.io/badge/built%20by-neurodivergent%20minds-0A0A0A?style=for-the-badge&labelColor=D99518)](https://github.com/shard-BRAINS)

</div>
