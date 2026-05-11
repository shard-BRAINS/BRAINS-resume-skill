# Disclosure Coaching Workflow

> **This workflow does NOT provide individual legal advice, does NOT diagnose, and does NOT replace professional advice from an employment advocate, disability-rights lawyer, or clinician. State this at the start and at the end of every disclosure interaction.**

---

## Trigger conditions

This workflow activates when:

- The user explicitly asks for disclosure coaching or help deciding whether to disclose on a resume or cover letter, **OR**
- Any other workflow detects content matching ND-bias patterns 6 or 7 (direct or indirect ND signals, per `references/nd-bias-patterns.md`).

---

## Inputs to collect

Gather the following before beginning. All items are optional.

- **Target employer** — name, sector, or a brief description of the organisation (optional)
- **Role title** — the position being applied for (optional)
- **Situation summary** — in the user's own words: what is prompting the disclosure question right now
- **Prior disclosure preference** — if the session has already surfaced a preference, carry it forward without asking the user to repeat themselves

---

## Procedure

**(a) Load the decision framework.**
Load `references/disclosure-decision-tree.md` in full before beginning. All coaching language, factor questions, and disclosure-strength definitions must come from that document. Do not paraphrase the default position or the safeguarding caveat.

**(b) Open the conversation with the default position and safeguarding caveat.**
State both of the following verbatim at the start of the coaching conversation, before any questions are asked:

- **Default position:** "The starting point in this framework is not to disclose neurodivergent identity on the resume itself."
- **Safeguarding caveat:** "This is general guidance, not legal or medical advice. For specific decisions about your application, accommodation, or disclosure, consult an employment advocate, disability-rights lawyer, or — where relevant — a clinician."

**(c) Walk the user through the six factors as plain questions.**
Present each factor as a plain, non-leading question. Do not bundle factors. Record the user's answer before moving to the next. The six factors are:

1. Is the employer ND-affirming in concrete, formal-programme terms?
2. Is the role itself disability-, accessibility-, or ND-affirming-adjacent?
3. Are you applying through a channel that already screens for ND inclusion?
4. Do you need an accommodation at the application stage itself?
5. Are you values-driven to disclose regardless of bias risk?
6. Has an employment advocate or disability-rights lawyer advised disclosure in your specific case?

**(d) Suggest a disclosure strength — framed as a suggestion, not a decision.**
Based on the pattern of answers, suggest one of the three disclosure strengths from the framework: **non-disclosure**, **neutral signalling**, or **explicit disclosure**. Frame the suggestion explicitly as a suggestion. Use language such as: "Based on what you've shared, the framework points toward [X]. This is a suggestion — you decide." Always preserve the user's veto. If the user indicates a different preference, accept it without challenge and proceed from there.

**(e) Offer a worksheet artifact.**
After the factor review and suggestion, offer to produce a worksheet that summarises the conversation. Ask: "Would you like a written summary of this conversation — the factors you considered and the position you landed on — as a document you can keep?"

**(f) If the user accepts the worksheet offer: generate and render the document.**
Generate the worksheet as a markdown document using the coaching-report template structure (`templates/coaching_report.md`, added in Task 17). Render to a branded PDF via `scripts/generators/coaching_report_to_pdf.py` (Task 18) with `include_trust_footer=True` so that the BRAINS Trust safeguarding-credit line appears in the footer of the rendered document.

Save outputs to:
- `output/disclosure-worksheet-YYYY-MM-DD-HHMMSS.md`
- `output/disclosure-worksheet-YYYY-MM-DD-HHMMSS.pdf`

**(g) Close by offering to continue.**
Offer to continue into the resume-review or resume-edit workflow. Pass any surfaced disclosure preference forward as context.

---

## Output artifacts

| Artifact | Path pattern |
|---|---|
| Worksheet (markdown) | `output/disclosure-worksheet-YYYY-MM-DD-HHMMSS.md` |
| Worksheet (branded PDF) | `output/disclosure-worksheet-YYYY-MM-DD-HHMMSS.pdf` |

The PDF is rendered with `include_trust_footer=True`. The BRAINS Trust safeguarding-credit line must appear in the footer.

---

## Boundaries

This workflow does NOT:

- Provide individual legal advice
- Diagnose any condition
- Replace professional advice from an employment advocate, disability-rights lawyer, or clinician

**State all three negations verbatim at the start AND at the end of every disclosure interaction.**
