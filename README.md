# BRAINS Resume Skill

A Claude Code skill that helps neurodivergent and autistic people review, create, customise, and tailor resumes and cover letters — with cross-cutting awareness of the bias patterns that cause neurodivergent candidates to be filtered out by automated screening systems and human reviewers.

**An Incubator project from BRAINS — built by neurodivergent minds, for neurodivergent people.**

---

## Status

v1.3.0 — adds the local Streamlit dashboard; fourteen workflows live (dashboard and de-AI are tools, not workflows).

---

## What it does

- **Resume review** — analyses an existing resume, flags ND-bias risks and ATS formatting issues, and produces a plain-language coaching report. **(live)**
- **Disclosure coaching** — guided decision framework for whether, when, and how to disclose neurodivergent identity at each stage of the hiring process. **(live)**
- **Create resume from scratch** — builds a resume from user-provided context via a structured interview. **(live)**
- **Edit / customise an existing resume** — improves a resume without targeting a specific job description. **(live)**
- **Tailor to a job description** — customises a resume to a specific role, with keyword coverage reporting. **(live)**
- **Generate a matching cover letter** — drafts a three-paragraph cover letter calibrated to the tailored resume and JD. **(live)**
- **LinkedIn export ingestion** — parses a LinkedIn ZIP export as source material for create or edit workflows; third-party PII auto-excluded. **(live)**
- **Career-change translation** — translates experience from one domain into another with an explicit skills-bridge. **(live)**
- **Bias-aware ATS final check** — pre-submit pass on a final resume and cover letter against ATS and ND-bias rules. **(live)**

---

## Install

### One-line installers (recommended)

**Windows (Command Prompt or PowerShell):**
```
.\install\install.cmd
```

This wrapper handles PowerShell's default execution policy automatically — no system setting changed. If you'd rather invoke PowerShell directly, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\install\install.ps1
```

**macOS / Linux:**
```bash
bash install/install.sh
```

### Manual install (fallback)

```bash
# 1. Clone into your working area
git clone https://github.com/shard-brains/brains-resume-skill.git

# 2. Enter the directory
cd brains-resume-skill

# 3. Create a virtual environment
python -m venv .venv

# 4. Activate it
#    Windows:
.venv\Scripts\activate
#    macOS / Linux:
source .venv/bin/activate

# 5. Install the project and dev dependencies
pip install -e ".[dev]"
```

**Install the skill bundle for Claude Code** — copy or symlink:

```bash
# Copy (most users)
cp -r . ~/.claude/skills/brains-resume/

# Symlink (edits take effect immediately)
ln -s "$(pwd)" ~/.claude/skills/brains-resume
```

Windows — directory junction:
```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\brains-resume" -Target (Get-Location).Path
```

---

## Slash commands

| Command | Description |
|---|---|
| `/brains-review [path]` | Audit a resume for ND-bias, ATS-safety, and integrity issues |
| `/brains-disclosure` | Walk through the disclosure-decision framework |
| `/brains-edit [path]` | Apply review recommendations; produces a clean ATS-safe rewrite |
| `/brains-tailor [resume] [jd]` | Tailor a resume to a specific job description |
| `/brains-cover-letter [resume] [jd]` | Generate a matched cover letter |
| `/brains-create` | Build a resume from scratch via interactive interview |
| `/brains-linkedin [zip-path]` | Ingest a LinkedIn export (third-party PII auto-excluded) |
| `/brains-linkedin-improve` | Rewrite a LinkedIn profile (Headline / About / Experience / Skills) using the ND-aware framework |
| `/brains-consolidate` | Detect inconsistencies between a resume and a LinkedIn profile and propose resolutions |
| `/brains-career-change [target]` | Translate experience to a new domain |
| `/brains-check [resume] [letter]` | Final pre-submit ATS + bias + integrity pass |
| `/brains-jd-analyze [jd]` | Analyse a job description for ND-relevant signals (red flags, masking cost, evidence of flex, role-fit score) |
| `/brains-precheck [resume] [jd]` | Six-question coaching pass before submitting an application; registers it in the tracker |
| `/brains-deai` | Scan resume / cover-letter / LinkedIn text for AI-tell signals; surfaces a 0-100 AI-signal score and rewrite suggestions |
| `/brains-dashboard` | Print the command to launch the local Streamlit dashboard in a browser |
| `/brains-track [command]` | Manage the application tracker — add applications, log outcomes, view pipeline summary |

---

## Choosing a template

The skill ships four resume templates and two cover-letter templates. All are ATS-safe; the choice is about narrative shape:

| Resume template | Best for |
|---|---|
| `chronological` (default) | Linear career history with recent relevant experience |
| `functional` | Career-changers, employment gaps, skills-led story |
| `hybrid` | Career pivots with relevant transferable skills |
| `executive` | Senior roles, 15+ years experience, board / leadership framing |

| Cover-letter template | Best for |
|---|---|
| `formal-business` (default) | Traditional industries, regulated sectors |
| `modern-clean` | Tech / startup contexts |

The skill walks the user through template selection during the create / edit / tailor workflows. See `references/template-selection.md` for the full decision tree, including the ND framing on the functional-template tradeoff.

---

## Tracking applications

The skill includes an opt-in application tracker stored locally at `~/.brains-resume/tracker.db` (SQLite). The tracker is created on first use; if you never run `/brains-track` or `/brains-precheck`, the database is never created.

The tracker carries:

- Resume versions (with focus-area tags and tailored-from lineage)
- Job descriptions (with analyzer findings)
- Cover letters (linked to resume + JD)
- Applications (with channel, agency, recruiter contact)
- Outcomes (callback, interview, offer, rejection, etc.)

From these you can query:

- This-week pacing vs your self-defined healthy weekly application rate
- Per-template efficacy (which template + JD combinations are converting)
- Open applications by company or recency
- Duplicate-application detection (prevents accidental re-application)

Use `/brains-track summary` for a pipeline view, `/brains-track update <id> <event-type>` to log outcomes as they happen, and `/brains-track healthy-rate` to set the application pace that fits your sensory bandwidth — the skill never tells you what that number should be.

The dashboard UI for these views ships in v1.3.0; for v1.2.0, all queries are surfaced as markdown tables in chat.

---

## Launching the dashboard

The skill ships a local Streamlit dashboard from v1.3.0. After `pip install -e .` (which registers the `brains-resume-dashboard` CLI entry), launch from any terminal:

```
brains-resume-dashboard
```

The dashboard opens at `http://localhost:8501`. Press Ctrl+C in the launch terminal to stop it.

What you get:
- **Overview** — pipeline funnel, summary tiles, sparkline trends, idle-state callouts, pending-callbacks panel
- **Resumes / Cover Letters / JDs** — tagged tables with focus areas, AI-signal score per text artifact, links to source files
- **Applications** — filterable table by company / channel / status / date
- **Analytics** — efficacy by template and channel
- **Pacing** — this-week count vs your self-defined healthy weekly rate, with sensory-load notes journal

The dashboard is BRAINS Incubator branded (Incubator Blue accents with Gold Deep delta callouts, Atkinson Hyperlegible font, dark theme) and runs entirely on localhost — no telemetry, no outbound network.

Read-only except for the sidebar profile editor (focus areas, healthy weekly rate, pacing notes). Application outcomes are still logged via `/brains-track update <id> <event>` in your terminal.

---

## Claude Desktop / claude.ai

A ready-to-import Claude Project bundle is available at:

```
dist/brains-resume-claude-project.zip
```

Full setup instructions are in [`docs/claude-project-setup.md`](docs/claude-project-setup.md).

---

## Usage

### Resume review

Paste or attach your resume and ask Claude to review it:

```
Review my resume for ND-bias risks and ATS issues.
```

or simply paste your resume content — the skill defaults to a review workflow when it receives resume content.

### Disclosure coaching

```
I'm applying for a role and I'm not sure whether to disclose that I'm autistic. Can you walk me through the decision?
```

The skill runs the full disclosure decision framework — covering factors, timing, and downstream talking points — and produces a worksheet you can refer back to.

### All other workflows

Use the slash commands listed above, or describe your goal in plain language — the skill router will select the right workflow automatically.

---

## Privacy

Six unconditional guarantees — no configuration option overrides them:

1. Output artifacts go to a user-chosen output directory (default `./output/` in your working directory). Nothing is written into the skill bundle.
2. The skill ships with a `.gitignore` template that excludes the output folder and common resume filenames, so you do not accidentally commit private content to version control.
3. On first use per session, the skill shows a plain-language notice that your resume content is processed by Claude within that session only.
4. The LinkedIn ZIP parser extracts only your own data. It explicitly skips `Connections.csv`, `messages.csv`, `Invitations.csv`, and any file containing data about other people. It logs which files it skipped.
5. The skill does not persist data between sessions. Disclosure-stance choice, employer details, salary expectations, and all resume content are ephemeral to the session.
6. No telemetry, no analytics, no phone-home.

---

## Contributing

Contributions are welcome. Please read `CONTRIBUTING.md` before opening a pull request — it covers identity-first language requirements, the code of conduct, and how to propose new features or changes to the ND-bias catalog.

---

## Licence

MIT — see LICENSE

---

*AI that works for every mind.*
