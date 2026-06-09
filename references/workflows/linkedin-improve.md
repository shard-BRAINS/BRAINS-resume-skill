# Workflow: LinkedIn Profile Improvement

**Purpose:** Rewrite a user's LinkedIn profile (Headline, About, Experience entries, Skills) applying the ND-aware language framework. The audience and formatting constraints differ meaningfully from a resume — this workflow exists because resume-tuning rules do not translate cleanly to LinkedIn.

This is a parallel surface to the resume, not a substitute. A user who has run the resume-review or edit workflows should run this one next to bring their LinkedIn presentation into alignment.

---

## Differences from the resume workflows

| Dimension | Resume | LinkedIn profile |
|---|---|---|
| Audience search mechanism | ATS keyword extraction | Recruiter semantic search + structured Skills tags |
| Reading context | Single-document review by a screener | Scrolling-on-mobile dominant; often scanned in seconds |
| Formatting affordance | Full rich text, multi-page | Plain text, character-limited per field, no rich formatting |
| Tone calibration | Formal, achievement-led | Conversational hook + scannable proof |
| Editing surface | DOCX/PDF file the user submits | LinkedIn web/app fields the user pastes into manually |

The output of this workflow is **markdown-formatted text ready to be copy-pasted into LinkedIn**. The skill does not edit LinkedIn directly.

---

## Trigger conditions

Start this workflow when any of the following are true:

- The user says "improve my LinkedIn", "rewrite my LinkedIn profile", "update my LinkedIn", "make my LinkedIn match my resume", or any equivalent phrasing.
- The user has just completed the resume-review or edit workflow and asks for the equivalent treatment on their LinkedIn.
- The user runs `/brains-linkedin-improve`.

---

## Inputs

1. **LinkedIn profile content** — accept either:
   - A LinkedIn ZIP export (parsed via `scripts/parsers/linkedin_zip.py`). Apply the safeguarding rules from the linkedin-ingest workflow: surface the `skipped_files` list, never read third-party-PII files.
   - **OR** pasted profile sections — the user pastes their current Headline / About / Experience / Skills as raw text.

2. **Target role or career focus** — one or two sentences. Used to bias the rewrite toward the right keyword and skill-tag emphasis.

3. **Disclosure stance** — carry forward the session's disclosure stance (affirmative framing default; neutral-signalling or explicit-disclosure if the user has set one). Apply consistently to the LinkedIn rewrite the same way the resume workflows do.

---

## Procedure

**(a) Receive and structure the existing profile.**

If a ZIP was provided, call `parse_linkedin_export(path)` and surface the `skipped_files` list to the user. If pasted text was provided, parse it into the four standard sections (Headline / About / Experience / Skills) — ask the user to confirm the segmentation if any section is ambiguous.

**(b) Run the ND-bias scanner and integrity scanner on the existing profile text.**

```python
from scripts.validators.bias_scan import bias_scan
from scripts.validators.integrity_check import integrity_check

bias = bias_scan(existing_profile_text)
integ = integrity_check(existing_profile_text)
```

Surface the findings. These inform the rewrite — the rewrite should resolve every CRITICAL or HIGH integrity finding and address every bias finding the user agrees with.

**(c) Rewrite each section.**

Apply the language rules from `references/language-do-dont.md` and the bias-pattern guidance from `references/nd-bias-patterns.md`. Respect the user's disclosure stance.

**Headline (max 220 characters):**

- One sentence. Lead with the role or domain, not with a generic descriptor.
- Include 2-3 high-value keywords that match the target-role search query.
- No soft-skills vocabulary ("passionate", "team player", etc. — bias-scan Pattern 1).
- Identity-first language by default; switch to person-first if the user has set that preference.

**About (max 2,600 characters; aim for ~1,500 for scannability):**

- Three paragraphs maximum.
  - **Paragraph 1 — Hook:** one specific, evidenced opening line. No generic openers ("I'm a passionate professional with X years of experience…"). Lead with the most concrete claim.
  - **Paragraph 2 — Proof:** two or three concrete achievements with measurable outcomes. This is the resume-summary content reframed for narrative reading rather than bullet scanning.
  - **Paragraph 3 — CTA:** one line on what the user is currently building, looking for, or open to. Direct, not coy.
- First-person voice. Use "I" pronouns naturally — LinkedIn About sections are written in first person, unlike most resumes.
- No more than one warmth signal per paragraph. Warmth without specificity reads hollow; specificity without warmth reads cold.

**Experience entries (max ~2,000 characters per role):**

- Lead each role with a one-line role-summary sentence (what the role actually was — not just the title), then 3-5 achievement bullets.
- Achievement bullets follow the same pattern as resume bullets: action verb → specific action → measurable outcome.
- LinkedIn does not render bullet characters — use plain text. A line break per bullet is sufficient.

**Skills (target 25-30 tags):**

- LinkedIn supports up to 50 skill tags. Aim for 25-30 — enough density for semantic search to surface the profile without diluting the strongest signals.
- Order by relevance to the target role; the first 5 are the most visible.
- Include both hard skills (named technologies, frameworks, certifications, methodologies) and skill tags that match common recruiter search terms for the target role.

**(d) Run the validators on the rewritten output.**

```python
from scripts.validators.bias_scan import bias_scan
from scripts.validators.integrity_check import integrity_check

rewritten = headline + "\n\n" + about_text + "\n\n" + experience_text + "\n\n" + skills_text
bias_after = bias_scan(rewritten)
integ_after = integrity_check(rewritten)
```

The rewritten output must have:

- No CRITICAL or HIGH integrity findings.
- No remaining ND_BIAS_P1_SOFT_SKILLS or ND_BIAS_P5_UNDER_CLAIM hits unless the user explicitly preserved the language.

**(e) Save the output as a markdown artifact.**

Write to `output/linkedin-profile-YYYY-MM-DD-HHMMSS.md` with this structure:

```markdown
# LinkedIn Profile Rewrite

**Prepared:** {date}
**Target role / focus:** {target}
**Disclosure stance:** {stance}

> Copy each section into the matching LinkedIn field. LinkedIn does not render markdown — these are plain-text sections labelled for paste convenience.

---

## Headline (paste into LinkedIn → Headline field)

{rewritten headline}

**Characters:** {n} / 220
**Rationale:** {one line on why this framing}

---

## About (paste into LinkedIn → About field)

{rewritten about}

**Characters:** {n} / 2600
**Rationale:** {one line}

---

## Experience — {company}, {title}, {dates}

{rewritten experience entry}

**Characters:** {n} / 2000
**Rationale:** {one line}

(Repeat per role)

---

## Skills (paste into LinkedIn → Skills section; LinkedIn limit is 50, this list contains {n})

- {skill 1}
- {skill 2}
- ...

**Rationale:** {one line on the selection logic}

---

## Original profile (for comparison)

{original headline}
{original about}
{original experience}
{original skills list}
```

This artifact carries BRAINS coaching branding — it is an internal coaching artifact, not a submission-ready document. (The branding rule from `references/brand-application.md` covers this: the LinkedIn rewrite output itself, intended for LinkedIn paste, is plain unbranded text within the artifact; the markdown wrapper that documents the coaching session carries the BRAINS coaching frame.)

**(f) Offer next steps.**

- Offer the consolidation workflow (`/brains-consolidate`) if the user also has a resume, to check that the rewritten LinkedIn and the resume tell a coherent story.
- Offer to iterate on any section the user wants to redirect.

**De-AI check (optional).** Before saving the final output, optionally run the AI-signal validator:

```python
from scripts.validators.ai_signal_check import ai_signal_check
score = ai_signal_check(produced_text).score
```

If the score is above 30, surface the top three findings with rewrite suggestions and offer to revise. The user can decline — this is coaching, not gating. See `references/ai-signal-patterns.md` for the full pattern catalog.

---

## Output artifacts

| File | Notes |
|---|---|
| `output/linkedin-profile-YYYY-MM-DD-HHMMSS.md` | BRAINS coaching artifact — copy-paste-ready rewrite + original for comparison |

---

## Safeguarding boundaries

- **No LinkedIn API write access.** The skill produces a markdown artifact. The user pastes the rewritten sections into LinkedIn themselves.
- **Third-party PII guard inherited from `linkedin_zip.py`.** Connections, messages, invitations, reactions, comments, likes — all skipped at the parser level. The skipped-files list is surfaced exactly as in the linkedin-ingest workflow.
- **Character limits are LinkedIn-defined, not optional.** The Headline cuts off at 220 characters; About at 2,600; Experience at 2,000. The rewrite must fit within those limits, not just attempt to.
