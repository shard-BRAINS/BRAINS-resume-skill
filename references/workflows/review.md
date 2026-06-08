# Resume Review Workflow

---

## Trigger conditions

This workflow activates when:

- The user asks for a resume review, critique, or audit, **OR**
- The user provides a resume but does not explicitly request edits or rewrites

---

## Inputs to collect

Gather the following before beginning. Mark each item clearly as received or pending.

- **The resume** — PDF, DOCX, or pasted plain text
- **Disclosure stance preference** — read from the tracker first; only ask if no session exists.

  ```python
  from scripts.tracker import disclosure as disclosure_db
  from scripts.tracker.candidates import get_active_candidate

  active = get_active_candidate()
  latest = disclosure_db.get_latest_for_candidate(active.id) if active else None
  ```

  - If `latest` is **None** or `latest.landed_strength == "undecided"`: no
    preference on file — ask, and point the user at
    `references/disclosure-decision-tree.md` if they want to think it
    through. Offer to run `/brains-disclosure` first.
  - If `latest.landed_strength` is set: surface it back to the user so
    they can confirm or override. *"You previously recorded a
    {landed_strength} preference on {created_at[:10]} — I'll flag any
    content inconsistent with it. Override?"* Review never silently
    edits; it flags only.
- **Language preference** — identity-first (e.g. "autistic engineer") or person-first (e.g. "engineer with autism"). BRAINS defaults to identity-first; user preference overrides

---

## Procedure

**(a) Parse the file if a file was provided.**
If the input is a `.pdf` file, run `scripts/parsers/pdf_to_text.py` to extract plain text and structural metadata. If the input is a `.docx` file, run `scripts/parsers/docx_to_text.py`. If the resume was pasted as plain text, skip this step and proceed directly to (b) with the pasted content.

**(b) Run the ATS check.**
If the input is a `.docx` file (original or parsed), run `scripts/validators/ats_check.py`. If the input was a PDF or pasted text, mark the ATS check as `"unavailable for PDF — recommend submitting in DOCX where possible"` and skip.

**(c) Run the deterministic bias scan.**
Run `scripts/validators/bias_scan.py` on the extracted text. The scanner detects pattern matches for Patterns 1, 2, 6, 7, and 10 from `references/nd-bias-patterns.md`. Record all flags and the matched text that triggered each flag.

**(d) Perform contextual review for the remaining patterns.**
Patterns 3, 4, 5, 8, and 9 require human-level judgment that the validator cannot supply by keyword matching alone. Review the document for:
- **Pattern 3** — consecutive short tenures without contract or fixed-term context
- **Pattern 4** — hyperfocus clustering: a single domain token appearing four or more times in close proximity
- **Pattern 5** — modesty or under-claim: passive constructions on work that appears to have been candidate-led
- **Pattern 8** — communication-warmth deficit in the summary section
- **Pattern 9** — hyperbole mismatch: flat affect throughout, or decimal-precision metrics appearing in warmth contexts

Record findings alongside severity assessment (low / medium / high) for each pattern triggered.

**(e) Cross-reference detected issues against mitigations.**
For every flag raised in (c) and (d), consult `references/nd-bias-patterns.md` for the corresponding mitigation guidance. Note which mitigations apply and whether they require a user decision before they can be acted on.

**(f) Score each resume bullet.**
For every bullet point in the experience and skills sections, assign three scores:
- **Specificity** — does the bullet describe a concrete action or outcome?
- **Measurability** — is there a quantifiable result or scope signal?
- **ND-bias risk** — low, medium, or high, based on (c) and (d) findings

**(g) Score the summary section.**
Evaluate the summary or profile paragraph against the warmth-vs-specificity calibration defined in Pattern 8. Note whether the section reads as too cold (warmth deficit), appropriately balanced, or mismatched in register (Pattern 9 concern).

**(h) Compile findings into the coaching report template.**
Structure the full output using `templates/coaching_report.md` (added in Task 17). All section headings, finding formats, and user-veto language must follow the template. Every finding must be accompanied by the corresponding user-veto statement: the user may accept, modify, or dismiss any recommendation at any time.

If a disclosure preference was loaded in the Inputs step, include a "Disclosure preference applied" line at the top of the findings section. Example: *"Applied your non-disclosure preference (recorded 2026-06-08) — flagged: 'autism advocacy' wording in role 2 (inconsistent with non-disclosure stance)."* Review only flags — the user decides whether to act.

**(i) Render to branded PDF.**
Run `scripts/generators/coaching_report_to_pdf.py` with `include_trust_footer=False`. Coaching reports use the standard origin-phrase footer only. The BRAINS Trust footer is reserved for disclosure worksheets; it must not appear on review outputs.

**(j) Application tracker (opt-in).**
After surfacing the review findings, ask the user: "Register this resume version in the application tracker? (yes — saves the resume version with its current focus areas; no — coaching report stays in chat only)". If yes, call `scripts/tracker/add.py:add_resume_version` with the file path, template, and focus areas the user confirms.

---

## Output artifacts

| Artifact | Path pattern |
|---|---|
| Coaching report (markdown) | `output/coaching-report-YYYY-MM-DD-HHMMSS.md` |
| Coaching report (branded PDF) | `output/coaching-report-YYYY-MM-DD-HHMMSS.pdf` |

The PDF is rendered with `include_trust_footer=False`. The BRAINS Trust safeguarding-credit line must **not** appear in the footer of review outputs.

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

## Next steps — offer at end of report

At the close of every review report, offer to move into an edit workflow to apply specific recommendations.

**For v0.1.0:** The edit workflow does not yet exist. State explicitly: "The edit workflow ships in v0.5 (Plan 2). For v0.1.0, the review report identifies issues; applying the recommendations is a manual step or a job for a future skill version."

---

## Bias of the review itself

This workflow is a pattern-aware analysis. State both of the following explicitly in every report:

- **Scope boundary:** This review identifies patterns associated with documented screener and ATS bias. It cannot guarantee the user will or will not be filtered from any specific process. Hiring outcomes depend on factors outside this tool's visibility.
- **User agency:** Every recommendation in this report is a suggestion. The user's judgment on their own document, their target role, and their preferred framing is absolute. Any recommendation may be vetoed at any time, for any reason, without explanation.

These statements are not optional footer language. They belong in the body of the report, visible before the first finding.
