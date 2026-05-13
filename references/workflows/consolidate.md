# Workflow: Resume + LinkedIn Consolidation

**Purpose:** Detect narrative inconsistencies between a user's resume and LinkedIn profile and propose unifying resolutions. Recruiters routinely cross-check both surfaces; deltas (different titles for the same role, mismatched dates, achievements claimed in one but not the other, register differences) are read as either carelessness or evasion.

This workflow is **read-only** — it produces a coaching report. Actual fixes happen via the existing edit / linkedin-improve workflows. The user always chooses which resolution to apply.

---

## Trigger conditions

Start this workflow when any of the following are true:

- The user says "consolidate my resume and LinkedIn", "check my resume against my LinkedIn", "make sure these match", or any equivalent.
- The user has just completed a resume-edit or linkedin-improve workflow and asks to verify the other surface is aligned.
- The user runs `/brains-consolidate`.

---

## Inputs

1. **Resume** — DOCX or PDF. Parsed via `scripts/parsers/docx_to_text.py` or `scripts/parsers/pdf_to_text.py`. Text is then structured per role by Claude (see procedure step (b)).
2. **LinkedIn data** — either:
   - A LinkedIn ZIP export (parsed via `scripts/parsers/linkedin_zip.py`) — preferred, structured by default.
   - **OR** a markdown file produced by the `brains-linkedin-improve` workflow.
   - **OR** pasted LinkedIn sections.

If only one of the two inputs is available, ask the user to provide the other. The workflow does not run with one side.

---

## Finding codes

The validator surfaces five standardized finding codes:

- **`CONSOLIDATION_JOB_TITLE_MISMATCH`** — The job title differs between resume and LinkedIn.
- **`CONSOLIDATION_DATE_INCONSISTENCY`** — Start or end dates conflict.
- **`CONSOLIDATION_ACHIEVEMENT_ONLY_IN_RESUME`** — An achievement or bullet point appears only on the resume.
- **`CONSOLIDATION_ACHIEVEMENT_ONLY_IN_LINKEDIN`** — An achievement or bullet point appears only on LinkedIn.
- **`CONSOLIDATION_TONE_DIVERGENCE`** — The description register (formal vs. casual) differs significantly between the two surfaces. This is heuristic; see step (e) for tone-divergence framing.

---

## Procedure

**(a) Parse both inputs.**

```python
from scripts.parsers.docx_to_text import parse_docx_resume
from scripts.parsers.linkedin_zip import parse_linkedin_export

resume = parse_docx_resume(resume_path)
linkedin = parse_linkedin_export(linkedin_zip_path)
```

Surface the LinkedIn `skipped_files` list as in the linkedin-ingest workflow.

**(b) Extract structured positions from the resume.**

The LinkedIn parser already returns structured positions. The resume parser returns raw text. Claude does the structured extraction from the resume side — produce a list of position dicts shaped like:

```python
{
    "company": "Example Corp",
    "title": "Senior Engineer",
    "start_date": "2020-03",   # YYYY-MM if a month is present, YYYY otherwise
    "end_date": "2024-08",     # same format; "Present" treated as current year
    "bullets": ["First bullet text.", "Second bullet text."],
    "description": "A flowing-prose description of the role for tone analysis. "
                   "If the resume only has bullets, concatenate them here.",
}
```

Show the structured extraction to the user and confirm before proceeding. The extraction is informed; the user has the veto.

**(c) Convert the LinkedIn parser output into the same shape.**

The LinkedIn `positions` list typically contains fields like `Company Name`, `Title`, `Started On`, `Finished On`, `Description`. Map them:

```python
def _from_linkedin(pos):
    desc = pos.get("Description", "") or ""
    # Split the description into bullets if it contains line-breaks or "•"
    bullets = [b.strip() for b in re.split(r"[\n•]", desc) if b.strip()]
    return {
        "company": pos.get("Company Name", ""),
        "title": pos.get("Title", ""),
        "start_date": pos.get("Started On", ""),
        "end_date": pos.get("Finished On", "") or "Present",
        "bullets": bullets,
        "description": desc,
    }

linkedin_positions = [_from_linkedin(p) for p in linkedin["positions"]]
```

**(d) Run the validator.**

```python
from scripts.validators.consolidation_check import consolidation_check

result = consolidation_check(resume_positions, linkedin_positions)
```

The validator returns a `ConsolidationCheckResult` with a `findings` list. Each finding has a `code`, `severity`, `role_context`, `resume_excerpt`, `linkedin_excerpt`, and `suggested_resolutions` (a list of three resolutions tagged `RESUME-LEADING`, `LINKEDIN-LEADING`, `NEW-SYNTHESIS`).

**(e) Present findings to the user.**

Group findings by role. For each role with any finding, render a side-by-side comparison:

| Aspect | Resume | LinkedIn |
|---|---|---|
| Title | {resume title} | {linkedin title} |
| Dates | {resume dates} | {linkedin dates} |
| Achievements | {resume bullets} | {linkedin bullets} |
| Description register | (formal / casual / neutral) | (formal / casual / neutral) |

Below each comparison, list the findings raised for that role with the three resolutions per finding. The user picks per-finding which resolution to apply.

**Important framing:** The tone-divergence finding (`CONSOLIDATION_TONE_DIVERGENCE`) is heuristic. State this explicitly when presenting it — the validator surfaces a register difference as a signal, not as a definitive judgement, and the user may have intentional reasons for the two surfaces sounding different.

**(f) Save the consolidation report.**

Write to `output/consolidation-report-YYYY-MM-DD-HHMMSS.md` with this structure:

```markdown
# Resume + LinkedIn Consolidation Report

**Prepared:** {date}
**Resume:** {resume filename}
**LinkedIn source:** {ZIP filename or pasted source description}

---

## Summary

- Roles compared: {n}
- Findings raised: {n}
  - Title mismatches: {n}
  - Date inconsistencies: {n}
  - Achievement-only-in-resume: {n}
  - Achievement-only-in-LinkedIn: {n}
  - Tone divergence (heuristic): {n}

---

## Per-role findings

### {Company} ({dates})

{side-by-side table}

**Findings:**

- **{finding code}** ({severity}): {role context}
  - Resume: {resume excerpt}
  - LinkedIn: {linkedin excerpt}
  - Suggested resolutions:
    - [RESUME-LEADING] {text}
    - [LINKEDIN-LEADING] {text}
    - [NEW-SYNTHESIS] {text}

(Repeat per role)

---

## Next steps

When you decide which resolutions to apply:

- For fixes on the **resume side**, run `/brains-edit` with the current resume.
- For fixes on the **LinkedIn side**, run `/brains-linkedin-improve` with the current profile.
- For aligned re-tailoring (you also want both surfaces optimised for a new target role), run `/brains-tailor` first on the resume, then `/brains-linkedin-improve`.

This report is read-only. The skill does not apply resolutions automatically.
```

This artifact carries BRAINS coaching branding — it is an internal coaching artifact, not a submitted document.

**(g) Offer next steps.**

Based on the user's resolution choices, offer the relevant fix workflow. Do not auto-launch; ask first.

---

## Output artifacts

| File | Notes |
|---|---|
| `output/consolidation-report-YYYY-MM-DD-HHMMSS.md` | BRAINS coaching artifact — read-only report; user chooses which resolutions to apply |

---

## Safeguarding boundaries

- **Read-only on cross-document edits.** The validator surfaces deltas. It never edits either document. Fixes happen via the existing edit / linkedin-improve workflows after the user chooses.
- **Tone-divergence is heuristic.** Always state this when presenting tone-divergence findings. The user may have intentional reasons for register differences between the two surfaces.
- **Third-party PII guard inherited from `linkedin_zip.py`.** Connections, messages, invitations, reactions, comments, likes — all skipped at the parser level.
- **The structured extraction from the resume is confirmed by the user.** Step (b) is not a silent step — the user sees the extraction and can correct it before findings are computed.
