# BRAINS Resume Skill

A Claude Code skill that helps neurodivergent and autistic people review, create, customise, and tailor resumes and cover letters — with cross-cutting awareness of the bias patterns that cause neurodivergent candidates to be filtered out by automated screening systems and human reviewers.

**An Incubator project from BRAINS — built by neurodivergent minds, for neurodivergent people.**

---

## What it does

- **Resume review** — analyses an existing resume, flags ND-bias risks and ATS formatting issues, and produces a plain-language coaching report. **(live)**
- **Disclosure coaching** — guided decision framework for whether, when, and how to disclose neurodivergent identity at each stage of the hiring process. **(live)**
- **Create resume from scratch** — builds a resume from user-provided context via a structured interview. (ships in v0.5)
- **Edit / customise an existing resume** — improves a resume without targeting a specific job description. (ships in v0.5)
- **Tailor to a job description** — customises a resume to a specific role, with keyword coverage reporting. (ships in v0.5)
- **Generate a matching cover letter** — drafts a three-paragraph cover letter calibrated to the tailored resume and JD. (ships in v0.5)
- **LinkedIn export ingestion** — parses a LinkedIn ZIP export as source material for create or edit workflows. (ships in v0.5)
- **Career-change translation** — translates experience from one domain into another with an explicit skills-bridge. (ships in v0.5)
- **Bias-aware ATS final check** — pre-submit pass on a final resume and cover letter against ATS and ND-bias rules. (ships in v0.5)

---

## Install

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

## Usage

### Resume review (live)

Paste or attach your resume and ask Claude to review it:

```
Review my resume for ND-bias risks and ATS issues.
```

or simply paste your resume content — the skill defaults to a review workflow when it receives resume content.

### Disclosure coaching (live)

```
I'm applying for a role and I'm not sure whether to disclose that I'm autistic. Can you walk me through the decision?
```

The skill runs the full disclosure decision framework — covering factors, timing, and downstream talking points — and produces a worksheet you can refer back to.

### Other capabilities

Create from scratch, edit, tailor, cover letter, LinkedIn ingestion, career-change translation, and bias-aware ATS check all ship in v0.5.

---

## Privacy

Six unconditional guarantees — no configuration option overrides them:

1. Output artifacts go to a user-chosen output directory (default `./output/` in your working directory). Nothing is written into the skill bundle.
2. The skill ships with a `.gitignore` template that excludes the output folder and common resume filenames, so you do not accidentally commit private content to version control.
3. On first use per session, the skill shows a plain-language notice that your resume content is processed by Claude within that session only.
4. The LinkedIn ZIP parser (shipping in v0.5) extracts only your own data. It explicitly skips `Connections.csv` and any file containing data about other people. It logs which files it skipped.
5. The skill does not persist data between sessions. Disclosure-stance choice, employer details, salary expectations, and all resume content are ephemeral to the session.
6. No telemetry, no analytics, no phone-home.

---

## Status

v0.1.0 — foundation and resume-review workflow live. All other workflows ship in v0.5 (Plan 2 of the build).

---

## Contributing

Contributions are welcome. Please read `CONTRIBUTING.md` before opening a pull request — it covers identity-first language requirements, the code of conduct, and how to propose new features or changes to the ND-bias catalog.

---

## Licence

MIT — see LICENSE

---

*AI that works for every mind.*
