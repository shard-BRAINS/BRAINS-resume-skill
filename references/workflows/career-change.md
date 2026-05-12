# Workflow: Career-Change Translator

**Purpose:** Translate existing experience into the vocabulary, framing, and competencies of a new target domain. Particularly important for ND users pivoting after burnout or environment mismatch — the goal is reframing what the user already has, not inventing what they don't.

---

## Trigger Conditions

Start this workflow when any of the following are true:

- The user describes wanting to change career direction: different industry, different role type, or different specialty.
- The user makes an explicit ask such as "I want to move from X to Y, how do I reframe my resume for Y?"
- The user says "I'm pivoting", "I want to break into [domain]", "how do I position my background for [target]", or similar.
- A tailor-to-JD request surfaces a significant domain gap — consider offering this workflow as a prerequisite.

---

## Inputs to Collect

Before beginning, confirm all inputs:

1. **Existing resume** — accept DOCX, PDF, pasted plain text, or LinkedIn-ingested data from a prior ingest session.
2. **Target domain description** — the industry, role type, and seniority level the user is aiming for. **Must respect saved career preferences.** If the user has a saved "no [X] roles" memory entry (for example, the user's explicit preference to avoid the SAP ecosystem), never propose [X] as a target and never include it in any forward-looking framing. Cross-check before proceeding.
3. **Target JD (optional)** — if the user has a specific posting in mind, this becomes a tailor-plus-career-change hybrid. Process the skills-translation map first, then run the tailor workflow on the result.

---

## Step-by-Step Procedure

**(a) Parse the resume.**
Run `scripts/parsers/pdf_to_text.py` for PDF input or `scripts/parsers/docx_to_text.py` for DOCX input. If the user has pasted plain text or has LinkedIn-ingested data available, proceed directly with that structured content.

**(b) Cross-check the target domain against saved career preferences.**
Before any translation work begins, verify that the target domain does not conflict with any saved preference (e.g. "no SAP ecosystem roles", "no [industry] roles"). If a conflict exists — including a partial overlap such as a role type that sits inside a blocked ecosystem — **stop and confirm** with the user before continuing. Do not assume the conflict is acceptable. Do not proceed without explicit sign-off.

**(c) Identify transferable skills.**
Map the user's deep-domain competencies to target-domain general competencies. The aim is to surface what travels — not to inflate or invent. Work from the parsed resume and the user's stated history. Example translations:

- "[Deep-domain] delivery governance" → "enterprise software delivery governance"
- "ISO 19011 audit lead" → "process-quality audit lead, transferable to any regulated industry"
- "Change management in [specific platform] rollouts" → "enterprise change management and stakeholder engagement"

Flag competencies that are domain-specific and unlikely to transfer cleanly — the user needs to know what gaps exist.

**(d) Research target-domain expectations.**
Identify typical role titles, must-have competencies, common phrasing, and level signals for the target domain. Use general training knowledge. Do not fabricate industry data — if a claim about target-domain norms is uncertain, say so explicitly rather than stating it as fact.

**(e) Produce the skills-translation map and surface for user review.**
For each existing skill, role, or certification in the user's resume, state its target-domain equivalent or transferable framing. Present this as a structured map before any resume editing begins. The user reviews and accepts, rejects, or modifies each translation. The user-veto principle is absolute: no translation is applied without explicit acceptance.

**(f) Rebuild the resume with accepted translations.**
With the accepted translation map in hand, walk through the resume rebuild via the edit workflow:

- **Summary refresh** — rewrite the professional summary to speak the target domain's language and lead with the most transferable seniority signals.
- **Experience reframing** — rewrite bullet points to use target-domain vocabulary and highlight transferable impact. Do not change what happened; change how it is described.
- **Skills section restructure** — reorganise or rename skill categories to match target-domain conventions. Remove or reframe items that read as domain-specific liabilities in the new context.

**(g) Render output files.**
Call `scripts/generators/resume_to_docx.py` and `scripts/generators/resume_to_pdf.py` with the rebuilt resume data. Use standard timestamped naming (see Output Artifacts below).

---

## Output Artifacts

| File | Notes |
|---|---|
| `output/skills-bridge-{target-slug}-YYYY-MM-DD-HHMMSS.md` | BRAINS coaching artifact — the accepted translation map. Carries BRAINS branding. |
| `output/resume-YYYY-MM-DD-HHMMSS.docx` | Unbranded — the user's document |
| `output/resume-YYYY-MM-DD-HHMMSS.pdf` | Unbranded — the user's document |
| `output/resume-changelog-YYYY-MM-DD-HHMMSS.md` | BRAINS coaching artifact — edit decisions record |

---

## Boundaries

These rules are non-negotiable:

- **Never invent target-domain experience the user does not have.** Career change is reframing of existing experience, not fabrication of new experience.
- **Never propose targets that conflict with saved career preferences.** The user's explicit preferences — for example, an explicit preference to avoid the SAP ecosystem — must be honoured without exception. Target proposals must avoid that domain entirely.
- **Never apply a translation the user did not explicitly accept.** The user-veto principle is absolute at every step.
- **Never state uncertain target-domain norms as facts.** If research confidence is low, say so.
- **ND context:** For users pivoting after burnout or environment mismatch, the translation process may surface work history the user wants to frame carefully. Follow the user's lead on what to emphasise and what to de-emphasise. Do not push for completeness over the user's stated framing goals.
