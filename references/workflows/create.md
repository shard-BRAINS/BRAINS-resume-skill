# Workflow: Create Resume from Scratch

**Purpose:** Build a resume from the ground up through a structured interactive interview. For users who have no existing resume, or who want to start fresh rather than edit what they already have.

---

## Trigger Conditions

Start this workflow when any of the following are true:

- The user explicitly asks to build, write, or create a resume from scratch.
- The user says they have no existing resume to work from.
- The user declines to provide an existing document and wants to start fresh.
- The user has an existing resume but wants to discard it and rebuild from first principles.

---

## Inputs (Interactive Interview, One Section at a Time)

Do not ask for everything at once. Run one section of the interview, confirm the output with the user, then move to the next. The user can pause, resume, or skip any section at any time.

### Target Framing

Open with context-setting before collecting any personal details:

- What role type, industry, and seniority level is this resume targeting?
- Is this resume for a specific job posting, or for general applications?
- What is the user's **disclosure stance** — explicit ND disclosure, non-disclosure, or context-dependent? (Carry this forward; it governs language choices throughout.)
- What **identity-language preference** does the user have? (e.g., identity-first, person-first, or no explicit ND framing at all.)
- **Is this resume for the profile holder, or for someone else?** If for someone else, capture their full name (e.g., "Mathilda Gell"). The interview otherwise proceeds normally — every reference to "the user" in subsequent sections applies to the named candidate. Pass the candidate name into the generator path (`make_artifact_path(..., for_candidate="<name>")`) and into the tracker insert (`add_resume_version(..., for_candidate="<name>")`) so the DOCX and the tracker row both record who the artifact is FOR. When the workflow runs for the profile holder, leave `for_candidate` unset.

Record both answers. Do not proceed without them.

### Contact

Collect:

- Full name
- City and state (or city and country for non-US)
- Professional email address
- Optional: public profile link (e.g., LinkedIn, GitHub, portfolio)

**Privacy note:** If the user offers a full street address, flag it as a privacy risk and ask them to confirm before including it. Trim to city/state unless the user explicitly insists on more.

### Summary

Run 3-4 prompts to gather raw material, then draft a summary (2-4 sentences) for user review:

1. How would you describe your professional identity in a sentence or two? (Who you are as a practitioner.)
2. What are your two or three primary professional strengths?
3. What motivates you in your work — what kind of problems do you want to be solving?
4. Where are you heading? What does the next chapter look like?

Compose the summary from the user's own words. Do not invent descriptors they did not use. Present the draft and ask: keep, adjust, or skip?

### Experience

For each role, collect:

- Job title
- Employer name
- Start and end dates (month and year; "present" for current roles)
- 3-5 achievements

For each achievement, run the following structured prompts:

1. What did you do? (Action)
2. At what scale or scope? (Team size, budget, geographic reach, system volume — whatever is relevant.)
3. What was the measurable outcome?

Apply **Pattern 1 (concrete instances)** inline: if the user gives a vague claim ("improved processes"), prompt for a specific example before moving on.

Apply **Pattern 5 (full credit recovery)** inline: if the user hedges ("I helped with...", "I was part of..."), ask what their individual contribution was. Reframe with full credit only after the user confirms the solo-led framing is accurate.

Repeat for each role. End each role summary with a keep/adjust/skip confirmation.

### Education

For each credential, collect:

- Degree or qualification name
- Institution name
- Year completed (or expected year)
- Honours, distinctions, or relevant coursework (optional)

### Skills

Use structured prompts to avoid blank-slate overwhelm:

1. What technical tools, platforms, or languages do you use regularly?
2. What methodologies or frameworks shape how you work?
3. Do you hold any certifications or credentials relevant to your target role?
4. What languages do you work in professionally, and at what proficiency level?

Note **Pattern 4 (transferable-skills bridge)**: if the user has domain experience they do not want foregrounded, help them reframe those skills in product-agnostic, transferable terms. Do not discard the underlying competency — reframe it.

---

## Procedure

**(a) State the workflow framing before collecting any information.**
Tell the user: this is a paced, section-by-section process. Every output is a draft. They can pause, resume, or skip any section. Nothing is locked in until they say so.

**(b) Run each section of the interview in sequence.**
Follow the order above: Target Framing, Contact, Summary, Experience, Education, Skills. End each section with a brief summary of what was captured and a keep/adjust/skip prompt. Record every decision — do not carry forward anything the user did not explicitly confirm.

**(c) Assemble structured resume data.**
Once all sections are complete (or the user is satisfied with what they have), construct the structured data object:

```
{
  candidate_name,
  candidate_contact_line,
  summary,
  skills,
  experience,
  education
}
```

Include only content the user explicitly confirmed. The user-veto principle is absolute: anything skipped or declined is excluded without argument.

**(d) Run pre-flight validators.**
Before rendering, run both validators in order:

- `scripts/validators/bias_scan.py` — flags language patterns that may signal bias risk or undercut the user's positioning.
- `scripts/validators/integrity_check.py` — flags structural issues, data anomalies, or anything that would compromise the document's ATS readability.

If either surfaces CRITICAL findings, stop, surface them, and require explicit user confirmation before continuing.

**Template selection.** This workflow defaults to the `chronological` resume template. Before rendering the final output, walk the user through `references/template-selection.md` to decide whether `chronological`, `functional`, `hybrid`, or `executive` better fits their situation. Pass the chosen template name as the `template=` argument to the generator.

**(e) Render output files.**
Call `scripts/generators/resume_to_docx.py(data, output_docx)` and `scripts/generators/resume_to_pdf.py(data, output_pdf)`. Use the timestamped naming convention (see Output Artifacts below).

**(f) Save the interview transcript.**
Write the full interview transcript as a markdown file in the output directory. This is a BRAINS coaching artifact — it carries BRAINS branding and gives the user a record for future iterations. Include each section's questions, the user's raw answers, and the confirmed final text for each section.

---

## Output Artifacts

| File | Notes |
|---|---|
| `output/resume-YYYY-MM-DD-HHMMSS.docx` | Unbranded — the user's document |
| `output/resume-YYYY-MM-DD-HHMMSS.pdf` | Unbranded — the user's document |
| `output/resume-interview-transcript-YYYY-MM-DD-HHMMSS.md` | BRAINS coaching artifact — carries BRAINS branding |

---

## Boundaries and User Agency

These rules are non-negotiable:

- **Never invent content the user did not provide.** If a section is thin, ask a clarifying follow-up question. Plausible placeholders are not an acceptable substitute for real information.
- **Clarifying follow-ups beat placeholders.** A short, direct question produces better output than a confident fabrication.
- **The user-veto principle is absolute.** If the user says no, skip it, or leave it out — that decision stands without pushback.
- **Respect saved career preferences.** Memory entries take precedence over any in-session framing suggestion. If the user has a preference to avoid a specific ecosystem or role type, do not surface it as a strength or include it without flagging the conflict.
- **Trim full street addresses to city and state.** If the user insists on including more, record their explicit choice.
- **Never override disclosure stance.** If the user chose non-disclosure, do not introduce ND framing. If they chose explicit disclosure, do not strip it.
