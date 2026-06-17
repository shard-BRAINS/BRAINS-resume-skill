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
Use the disclosure-specific generator added in v2.3:

```python
from scripts.generators.disclosure_worksheet import generate
md_path, pdf_path = generate(session_id)
```

The generator writes the worksheet markdown + branded PDF under
`<outputs>/disclosure/<candidate-slug>/disclosure-YYYY-MM-DD-<uid>.{md,pdf}`,
assigns an `artifact_uid` to the session row, and renders the PDF with
`include_trust_footer=True` so the BRAINS Trust safeguarding-credit line
appears in the footer.

**(g) Persist the session to the tracker.**
Record the session against the active candidate via the v2.3 disclosure
CRUD module:

```python
from scripts.tracker import disclosure as disclosure_db
from scripts.tracker.candidates import get_active_candidate

candidate = get_active_candidate()
session_id = disclosure_db.create_session(
    candidate_id=candidate.id,
    landed_strength=landed_strength,   # 'non-disclosure' | 'neutral' | 'explicit' | 'undecided'
    target_employer=target_employer,    # optional
    target_role=target_role,            # optional
    factor_1=factor_1_answer,           # the user's verbatim answer
    factor_2=factor_2_answer,
    factor_3=factor_3_answer,
    factor_4=factor_4_answer,
    factor_5=factor_5_answer,
    factor_6=factor_6_answer,
    notes=notes,                        # optional reasoning / caveats
)
```

If a worksheet was generated in step (f), `generate()` already attached
its `artifact_uid` to the row — do not write it twice.

Surface to the user: *"Your disclosure session has been recorded against
your candidate record. The next time you run a resume tailor, review, or
cover-letter workflow, your landed preference will be applied — and you
can see and change it in the dashboard's Disclosure tab."*

**(h) Close by offering to continue.**
Offer to continue into the resume-review or resume-edit workflow. Pass
the saved session's `landed_strength` forward as context so the next
workflow does not need to re-ask.

---

## Output artifacts

| Artifact | Path pattern |
|---|---|
| `disclosure_sessions` row (DB) | tracker.db — keyed to active candidate, surfaced in dashboard Disclosure tab |
| Worksheet (markdown) | `<outputs>/disclosure/<candidate-slug>/disclosure-YYYY-MM-DD-<uid>.md` |
| Worksheet (branded PDF) | `<outputs>/disclosure/<candidate-slug>/disclosure-YYYY-MM-DD-<uid>.pdf` |

`<outputs>` resolves to `~/.brains-resume/outputs/` by default (overridable via the `BRAINS_OUTPUTS_DIR` env var). The PDF is rendered with `include_trust_footer=True`. The BRAINS Trust safeguarding-credit line must appear in the footer.

---

## Boundaries

This workflow does NOT:

- Provide individual legal advice
- Diagnose any condition
- Replace professional advice from an employment advocate, disability-rights lawyer, or clinician

**State all three negations verbatim at the start AND at the end of every disclosure interaction.**
