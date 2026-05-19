# Workflow: Tailor Resume to Job Description

**Purpose:** Customise an existing resume for a specific job description. Adjust the summary, reorder and emphasise bullets, and calibrate keyword density to JD requirements — all while respecting the user's disclosure stance and without violating saved career preferences.

---

## Trigger Conditions

Start this workflow when all of the following are true:

- The user has an existing resume (from a prior workflow or supplied directly).
- The user has a target job description — pasted, as a URL, or as a screenshot.
- The user wants a JD-customised version of that resume for submission or application.

---

## Inputs to Collect

Before beginning, confirm every input below:

1. **Existing resume** — accept DOCX, PDF, or pasted plain text.
2. **JD source** — accept one of:
   - Pasted plain text or markdown
   - URL: fetch and parse via `scripts/parsers/jd_url_fetch.py`
   - Screenshot: read directly; Claude can parse image text
3. **Company or recipient details** (optional) — carry any company name, team context, or culture signals through to the summary and match report.
4. **Disclosure stance** — carry over from the current session. If not established, ask before proceeding.
5. **Is this resume for the profile holder, or for someone else?** If for someone else, capture their full name (e.g., "Mathilda Gell"). The workflow otherwise proceeds normally — every reference to "the user" in subsequent steps applies to the named candidate. Pass the candidate name into the generator path (`make_artifact_path(..., for_candidate="<name>")`) and into the tracker insert (`add_resume_version(..., for_candidate="<name>")`) so the DOCX and the tracker row both record who the artifact is FOR. When the workflow runs for the profile holder, leave `for_candidate` unset.

---

## Procedure

**(a) Parse resume and JD content.**
Run `scripts/parsers/pdf_to_text.py` or `scripts/parsers/docx_to_text.py` on the resume as appropriate. If the JD was supplied as a URL, run `scripts/parsers/jd_url_fetch.py` to retrieve clean text. If pasted or screenshot, proceed directly.

**(b) Extract JD requirements.**
From the parsed JD, identify and record:
- **Must-haves:** mandatory qualifications, experience, and hard skills
- **Nice-to-haves:** preferred or bonus qualifications
- **Keywords:** technical terms, tools, methodologies, certifications
- **Role level and scope:** seniority signals, team size, decision-making authority
- **Culture signals:** mission language, values statements, ways of working

**(c) Cross-check JD requirements against saved career preferences.**
Compare extracted requirements against all memory entries before any further analysis. If the JD conflicts with a saved preference — for example, the role sits in an ecosystem the user has explicitly excluded — **stop immediately**. Surface the conflict and ask whether to abort or proceed with a documented exception. Never silently comply.

**(d) Score the resume against the JD.**
Produce a gap analysis across three dimensions:
- **Keyword coverage:** which JD keywords appear in the current resume, which are absent
- **Requirement alignment:** which must-haves and nice-to-haves are addressed by existing content
- **Narrative fit:** whether the summary and bullets match the seniority and focus of the role

Surface the gap analysis before proposing any edits.

**(e) Propose targeted edits.**
Based on the gap analysis, draft and present specific proposals:
- **Summary refresh:** reframe the opening statement to lead with the credentials and language most relevant to this role
- **Bullet reordering:** within each role, surface the most JD-relevant achievements first
- **Keyword integration:** where a JD keyword maps to work the user has genuinely done, propose placing it naturally in body text — never in an artificial keyword section, never where it would be factually inaccurate

For each proposal, state the original text, the proposed revision, and the JD requirement it addresses.

**(f) Walk the user through each proposed edit.**
Present one edit at a time. Prompt accept, reject, or modify. Record every decision; do not apply edits silently or in batches. If a proposal would be factually inaccurate for the user's actual experience, withdraw it — do not ask the user to accept a fabrication.

**(g) Run validators on the tailored content.**
With decisions recorded and the tailored text assembled, run:
- `scripts/validators/bias_scan.py` — flag ND-disclosure-relevant patterns not covered by the user's disclosure stance
- `scripts/validators/integrity_check.py` — check for prompt-injection patterns, structural anomalies, or data integrity warnings

Stop on any CRITICAL finding and require explicit user sign-off before continuing.

**Template selection.** This workflow defaults to the `chronological` resume template. Before rendering the final output, walk the user through `references/template-selection.md` to decide whether `chronological`, `functional`, `hybrid`, or `executive` better fits their situation. Pass the chosen template name as the `template=` argument to the generator. Tailoring may justify switching templates — e.g. a career-pivot tailor often justifies switching from `chronological` to `hybrid`.

**(h) Render output files.**
Call `scripts/generators/resume_to_docx.py` and `scripts/generators/resume_to_pdf.py` with the finalised tailored content. Apply the timestamped naming convention (see Output Artifacts below).

**(i) Produce a JD match report.**
Write a match report markdown file capturing:
- **Changes made:** each accepted edit, keyed to the JD requirement it addressed
- **Keyword coverage before and after:** side-by-side count of JD keywords present in the original vs. tailored resume
- **Remaining gaps:** must-haves or nice-to-haves not addressed in the resume, flagged for potential handling in a cover letter

The match report is a BRAINS coaching artifact and carries BRAINS branding. The submitted resume documents do not.

**(j) Offer the cover-letter workflow.**
Present the option to move directly into the cover-letter workflow, using the remaining gaps from the match report as the brief.

**(k) Application tracker (opt-in).**
After saving the tailored resume, ask the user: "Track this in the application tracker? (yes runs the pre-application sanity check; later registers it without the check; no skips tracking entirely)". If yes, invoke the `pre-application-check.md` workflow with the resume's metadata. If later, call `scripts/tracker/add.py:add_resume_version` (and the related helpers) silently without going through the precheck questions. If no, no tracker writes occur.

**De-AI check (optional).** Before saving the final output, optionally run the AI-signal validator:

```python
from scripts.validators.ai_signal_check import ai_signal_check
score = ai_signal_check(produced_text).score
```

If the score is above 30, surface the top three findings with rewrite suggestions and offer to revise. The user can decline — this is coaching, not gating. See `references/ai-signal-patterns.md` for the full pattern catalog.

---

## Output Artifacts

| File | Notes |
|---|---|
| `output/resume-tailored-{slug}-YYYY-MM-DD-HHMMSS.docx` | Unbranded — the user's submitted document |
| `output/resume-tailored-{slug}-YYYY-MM-DD-HHMMSS.pdf` | Unbranded — the user's submitted document |
| `output/tailor-match-report-{slug}-YYYY-MM-DD-HHMMSS.md` | BRAINS coaching artifact — carries BRAINS branding |

`{slug}` is a kebab-case fragment derived from the JD title and company name (e.g., `senior-engineer-example-corp`). Strip or replace all characters that are not alphanumeric or hyphens.

---

### File organization (v1.5.0+)

The dashboard reserves the output path before invoking this command. The
handoff payload contains the absolute path to write to. Do NOT pick your
own filename. After saving the DOCX, call:

    from scripts.outputs.io import finalize_docx
    from scripts.outputs.tagging import ArtifactMeta
    finalize_docx(target_path, meta)

then record the row via the appropriate `tracker.add_*` call, passing the
`artifact_uid` and `parent_uid` from the handoff payload.

---

## Boundaries

These rules are non-negotiable:

- **Never fabricate experience.** If the user has not done the work, the keyword does not go in and the bullet does not get written.
- **Never apply keywords where factually inaccurate.** Keyword density surfaces genuine fit; it is not a vehicle for misrepresentation.
- **Surface career-preference conflicts; never comply silently.** Any conflict with a memory entry stops the workflow at step (c).
- **Never override disclosure stance.** Explicit disclosure: do not strip ND signals. Non-disclosure: do not introduce them.
- **User-veto principle.** No edit proposed in step (e) is applied without explicit acceptance in step (f).
- **Submitted documents remain unbranded.** The DOCX and PDF carry no BRAINS identity. The match report is a coaching artifact and may carry the brand.
