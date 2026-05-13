# Workflow: JD Analyzer

**Purpose:** Analyse a job description for ND-relevant signals — soft-culture red flags, masking-cost markers, evidence of real flexibility, required-vs-nice-to-have parsing, role-fit scoring against the user's stored focus areas, and duplicate-application detection against the tracker.

This workflow surfaces signals; it never advises the user to apply or not apply. The user always decides.

---

## Trigger conditions

Start this workflow when:

- The user says "analyse this JD", "what do you make of this JD", "is this a good fit", or pastes a JD with any framing.
- The user provides a JD URL and asks for analysis.
- The user runs `/brains-jd-analyze`.

---

## Inputs

1. **JD text** — paste OR URL (URL parsed via `scripts/parsers/jd_url_fetch.py` from v1.0) OR a screenshot the user transcribes themselves.
2. **Company and role title** — used for duplicate-application detection. If not in the JD, ask.
3. **User's focus areas** — read from `~/.brains-resume/profile.json` via `scripts/tracker/profile.py:read_profile()`. If empty, prompt the user to set them.

---

## Procedure

**(a) Acquire JD text.**

If a URL is provided, fetch via the existing parser. If pasted, use as-is. If a screenshot, ask the user to transcribe (OCR is out of scope).

**(b) Confirm company + role title.**

```python
# Extract from JD or ask user explicitly
company = ...
role_title = ...
```

**(c) Load user's focus areas.**

```python
from scripts.tracker.profile import read_profile
profile = read_profile()
focus_areas = profile.focus_areas
if not focus_areas:
    # Ask user to set their focus areas now; offer to save via write_profile()
    ...
```

**(d) Run the analyzer.**

```python
from scripts.validators.jd_analyzer import jd_analyze

result = jd_analyze(
    jd_text=jd_text,
    focus_areas=focus_areas,
    company=company,
    role_title=role_title,
)
```

**(e) Present findings to the user.**

Group findings by category. For each finding:

- Show the code
- Show the severity
- Show the excerpt (what triggered the finding)
- Show the suggestion (what the user might do with this signal)

Frame the presentation as informational. The role-fit score is a number; surface it with its calibration ("scores above 70 suggest strong alignment; below 30 suggest mismatch worth examining"). Never present the score as a recommendation to apply or not apply.

Tone-divergence with the BRAINS coaching frame: this is internal coaching, not a verdict. The user holds the veto on every finding.

**(f) Offer to save the JD to the tracker.**

```python
from scripts.tracker.add import add_jd

jd_id = add_jd(
    source=source,  # 'paste' / 'url' / 'screenshot'
    source_ref=source_ref,  # URL if applicable
    company=company,
    role_title=role_title,
    raw_text=jd_text,
    analyzer_findings={...},  # serialised result
    focus_areas_required=result.required_list,
    focus_areas_nice=result.nice_list,
)
```

Ask the user before persisting. If declined, the analysis stays in chat only — nothing written to disk.

**(g) Offer the next workflow.**

Based on findings:

- High role-fit score, low red flags → suggest `brains-tailor` for this JD
- Low role-fit score → ask the user whether they want to proceed anyway or look for better-fit roles
- Duplicate application detected → confirm intent before any further work
- High masking-cost score → mention the disclosure workflow as relevant context

---

## Output artifacts

| File | Notes |
|---|---|
| (optional) `output/jd-analysis-YYYY-MM-DD-HHMMSS.md` | BRAINS coaching artifact — readable summary of the findings, saved only if the user requests |
| (optional) Tracker row in `jds` table | Saved only if the user opts in at step (f) |

---

## Safeguarding boundaries

- **No automatic apply-or-don't recommendation.** The analyzer surfaces signals; the user decides.
- **No persistence without explicit consent.** Steps (f) requires user opt-in before writing to the tracker.
- **Duplicate-application check requires existing tracker data.** Returns no finding if the tracker db doesn't exist yet — silent, not an error.
- **Focus areas are user-defined.** The skill never tells the user what their focus areas should be; it asks once and uses what they provide.
