# BRAINS Resume Skill

A Claude Code skill that helps neurodivergent and autistic people review, create, customise, and tailor resumes and cover letters — with cross-cutting awareness of the bias patterns that cause neurodivergent candidates to be filtered out by automated screening systems and human reviewers.

**An Incubator project from BRAINS — built by neurodivergent minds, for neurodivergent people.**

---

## Status

**v2.3.0** — disclosure framework polish. Disclosure-coaching outcomes are now first-class, candidate-linked records: persisted to the tracker DB, surfaced in the dashboard, and read by downstream workflows (tailor, cover-letter, review) so your landed disclosure preference is applied consistently.

Earlier v2.x milestones: **v2.0** added first-class multi-candidate support (one tracker DB, many candidates, sidebar picker); **v2.1** rebuilt the dashboard as an orchestration hub with a customizable Home widget canvas + five guided playbooks; **v2.2** introduced resume-first onboarding (name + email to start, career intent collected once via the Home surface).

---

## What it does

- **Resume review** — analyses an existing resume, flags ND-bias risks and ATS formatting issues, and produces a plain-language coaching report. **(live)**
- **Disclosure coaching** — guided decision framework for whether, when, and how to disclose neurodivergent identity. Outcomes are persisted per candidate and respected by downstream workflows. **(live)**
- **Create resume from scratch** — builds a resume from user-provided context via a structured interview. **(live)**
- **Edit / customise an existing resume** — improves a resume without targeting a specific job description. **(live)**
- **Tailor to a job description** — customises a resume to a specific role, with keyword coverage reporting. Reads and applies your landed disclosure preference. **(live)**
- **Generate a matching cover letter** — drafts a three-paragraph cover letter calibrated to the tailored resume and JD. Reads and applies your landed disclosure preference. **(live)**
- **LinkedIn export ingestion** — parses a LinkedIn ZIP export as source material for create or edit workflows; third-party PII auto-excluded. **(live)**
- **Career-change translation** — translates experience from one domain into another with an explicit skills-bridge. **(live)**
- **Bias-aware ATS final check** — pre-submit pass on a final resume and cover letter against ATS and ND-bias rules. **(live)**
- **Multi-candidate support** — one local install can support multiple candidate records (e.g. coaching others, household setups). Each candidate has their own JDs, resumes, tracker rows, and disclosure history. Switch via the dashboard sidebar. **(live, v2.0)**
- **Dashboard orchestration** — the local Streamlit dashboard is a customizable widget canvas with five guided playbooks (Apply to a job, Build a base resume, Improve a resume, Refresh LinkedIn, Career change). **(live, v2.1)**

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

The skill includes a local application tracker stored at `~/.brains-resume/tracker.db` (SQLite). It is created on first use; everything stays on your machine — no telemetry, no outbound network.

The tracker carries:

- **Candidates** — name, email, focus areas, healthy weekly rate, career-intent profile (v2.0+)
- **Resume versions** — focus-area tags, tailored-from lineage, drift snapshots
- **Job descriptions** — analyzer findings, per-JD output folders
- **Cover letters** — linked to resume + JD
- **Applications** — channel, agency, recruiter contact
- **Outcomes** — callback, interview, offer, rejection, etc.
- **Disclosure sessions** — six-factor answers, landed strength, worksheet artifact UID (v2.3+)
- **Playbook runs** — guided journey progress, step-by-step state (v2.1+)

From these you can query:

- This-week pacing vs your self-defined healthy weekly application rate
- Per-template efficacy (which template + JD combinations are converting)
- Open applications by company or recency
- Duplicate-application detection (prevents accidental re-application)
- The active candidate's landed disclosure preference (downstream workflows respect this automatically)

Use `/brains-track summary` for a pipeline view, `/brains-track update <id> <event-type>` to log outcomes as they happen, and `/brains-track healthy-rate` to set the application pace that fits your sensory bandwidth — the skill never tells you what that number should be.

---

## Launching the dashboard

After `pip install -e .` (which registers the `brains-resume-dashboard` CLI entry), launch from any terminal:

```
brains-resume-dashboard
```

The dashboard opens at `http://localhost:8501`. Press Ctrl+C in the launch terminal to stop it.

### What you get (v2.x)

Eight tabs. **Home** is a customizable widget canvas — playbook cards, in-progress runs, computed next-actions worklist, pipeline mini-board, pacing / drift / library-count tiles, quick-launch, recent outcomes. Customize mode lets each candidate add, remove, and reorder widgets; the layout persists per candidate.

- **Home** — the orchestration surface (widget canvas + playbooks)
- **Resumes / Cover Letters / JDs** — tagged tables with focus areas, AI-signal score per text artifact, links to source files; inline action buttons per row
- **Applications** — filterable table by company / channel / status / date
- **Analytics** — efficacy by template and channel
- **Pacing** — this-week count vs your self-defined healthy weekly rate, sensory-load notes journal
- **Drift** — baseline-vs-current resume diff with per-candidate scoping
- **Disclosure** — record disclosure-coaching outcomes against the active candidate, view past sessions, generate branded worksheets (v2.3)

### Multi-candidate

The sidebar exposes a candidate picker. One install supports many candidate records — every tab scopes to the active candidate, every JD / resume / disclosure session lives under that candidate's record. Switch any time from the sidebar; nothing leaks across.

### How the dashboard talks to Claude Code

- **Validator-backed commands run in-dashboard** — de-AI scan, JD analyze, tracker CRUD, disclosure recording, consolidation diff, final composite check, review preview. No Claude Code roundtrip.
- **LLM-heavy commands hand off via clipboard** — click "Copy /brains-X" → paste into Claude Code chat. Optional audit log at `~/.brains-resume/handoffs/`.

The dashboard is BRAINS Incubator branded (Incubator Blue accents with Gold Deep callouts, Atkinson Hyperlegible font, dark theme) and runs entirely on localhost.

Read-only for resume / cover letter / JD *content* — mutable state is the candidate record, the tracker (outcomes), the disclosure_sessions table, and the per-candidate Home layout.

---

## Output organization

All resumes and cover letters produced by the skill land in
`~/.brains-resume/outputs/<JD-folder>/` with a deterministic filename
pattern. See `SKILL.md` § File organization for the full convention.

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

The skill runs the full disclosure decision framework — covering factors, timing, and downstream talking points — and produces a branded worksheet (markdown + PDF) under `~/.brains-resume/outputs/disclosure/<candidate>/`. From v2.3, the landed strength is recorded against the active candidate's tracker row, and subsequent `/brains-tailor`, `/brains-cover-letter`, and `/brains-review` runs read it and apply it (strip / preserve / flag identity language per your stance), surfacing what they changed so you can see and override. Update or replace your stance any time from the dashboard's Disclosure tab.

### All other workflows

Use the slash commands listed above, or describe your goal in plain language — the skill router will select the right workflow automatically.

---

## Privacy

Six unconditional guarantees — no configuration option overrides them:

1. Output artifacts go to a user-chosen output directory (default `~/.brains-resume/outputs/`, overridable via `BRAINS_OUTPUTS_DIR`). Nothing is written into the skill bundle.
2. The skill ships with a `.gitignore` template that excludes the output folder and common resume filenames, so you do not accidentally commit private content to version control.
3. On first use per session, the skill shows a plain-language notice about how your resume content is processed by Claude.
4. The LinkedIn ZIP parser extracts only your own data. It explicitly skips `Connections.csv`, `messages.csv`, `Invitations.csv`, and any file containing data about other people. It logs which files it skipped.
5. **All persisted state stays local.** The tracker DB (`~/.brains-resume/tracker.db`) holds candidates, JDs, resume versions, applications, outcomes, and disclosure sessions. Output artifacts (resumes, cover letters, disclosure worksheets) live under `~/.brains-resume/outputs/`. None of this is ever sent anywhere — it stays on your machine. Resume *content* sent through Claude during a workflow is processed within that conversation only and is not stored by the skill outside the tracker rows you explicitly create.
6. No telemetry, no analytics, no phone-home.

---

## Contributing

Contributions are welcome. Please read `CONTRIBUTING.md` before opening a pull request — it covers identity-first language requirements, the code of conduct, and how to propose new features or changes to the ND-bias catalog.

---

## Licence

MIT — see LICENSE

---

*AI that works for every mind.*
