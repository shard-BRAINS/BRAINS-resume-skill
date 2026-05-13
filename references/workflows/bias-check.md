# Bias-Aware ATS Final-Check Workflow

**Purpose:** Pre-submit verification gate. Run this as the last pass before the user submits a resume (and optionally a cover letter) to a role. This workflow is also offered automatically at the end of every create, edit, tailor, and cover-letter workflow.

---

## Trigger

- The user has a final draft resume and wants confirmation it is ready to submit.
- An optional cover letter may accompany the resume.
- Offered automatically at the close of any other BRAINS document workflow.

---

## Inputs

- **Resume** — DOCX preferred; PDF acceptable.
- **Cover letter** (optional) — DOCX or PDF.
- **User's disclosure stance** — carry from the active session (set during create or tailor; default to neutral if not established).

---

## Procedure

**(a) Parse documents**

Run the appropriate parser on each submitted file:

- `scripts/parsers/docx_to_text.py` for DOCX files
- `scripts/parsers/pdf_to_text.py` for PDF files

Extract clean plain text for all downstream checks. If parsing fails, halt and report the failure before continuing.

**(b) ATS validation (DOCX only)**

Run `scripts/validators/ats_check.py` against the DOCX resume (and cover letter DOCX if provided).

Surface the full PASS/FAIL result with all findings — tables, text boxes, unsupported fonts, non-standard characters, and column layouts that break ATS parsers.

If the input is PDF-only, note that the ATS structural check cannot run and flag this as a warning: **submit DOCX to ATS portals wherever possible.**

**(c) Integrity check**

Run `scripts/validators/integrity_check.py` on the extracted plain text from all submitted documents.

Surface every finding. Treat any CRITICAL finding as an immediate blocker — prompt injection text, instruction overrides, and hidden keyword blocks disqualify the document from submission until resolved.

**(d) Bias scan**

Run `scripts/validators/bias_scan.py` on the extracted text.

Surface all findings calibrated to the user's current disclosure stance (from Inputs). The bias scan checks for protected-attribute language, identity markers, and phrasing patterns that introduce unnecessary risk.

**(e) Disclosure-stance consistency check**

If the user's disclosure stance is non-disclosure or neutral signalling, scan the output of step (d) for residual P6 or P7 hits (protected attribute categories 6 and 7 per `references/workflows/disclosure.md`).

Flag any P6/P7 language that survived prior editing — these must be resolved before submission if the user has chosen not to disclose.

**(f) Length and structure sanity check**

- **Resume:** typically 1-2 pages. Flag if the parsed content clearly exceeds two pages in standard formatting.
- **Cover letter:** one page maximum. Flag if it exceeds this.
- **Section ordering:** verify that major sections follow the sequence defined in `references/resume-anatomy.md`. Flag any section that is missing or out of order for the target role type.

**(g) Compile the report**

Aggregate all findings from steps (a)-(f) into a prioritised pass / fail / warn report. Each finding gets a one-line fix suggestion. Order findings: CRITICAL blockers first, FAIL items second, WARN items third, PASS confirmations last.

**(h) Application tracker (opt-in).**
After the bias-check passes, ask the user: "Run the pre-application sanity check and register this in the tracker? (yes runs the precheck workflow; no submits without registering)". If yes, invoke `pre-application-check.md`.

---

## Output Artifacts

- `output/pre-submit-check-YYYY-MM-DD-HHMMSS.md` — BRAINS coaching artifact in Markdown, containing the full findings report with fix suggestions.
- `output/pre-submit-check-YYYY-MM-DD-HHMMSS.pdf` (optional) — branded PDF version; generate with `scripts/generators/coaching_report_to_pdf.py::render_from_markdown`.

---

## Result Framing

**All checks pass**
"Ready to submit. Final verifications passed." — Follow with a concise checklist of what was verified.

**Warnings present, no failures**
"Submittable with the noted considerations." — Follow with a prioritised list of warnings and optional fixes.

**One or more failures**
"Not ready to submit." — Lead with the specific blockers and required actions (for example: prompt injection detected in resume body, ATS table present in DOCX, brand or platform reference in submission artifact).
