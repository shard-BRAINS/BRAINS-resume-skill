# Workflow: Pre-Application Sanity Check

**Purpose:** A six-question coaching pass before the user submits an application. The workflow registers the application in the tracker. It never blocks submission — every question can be answered, deferred, or skipped.

This is coaching, not gating. The user always submits or doesn't.

---

## Trigger conditions

- The user runs `/brains-precheck`.
- The user has just completed `brains-tailor` or `brains-cover-letter` and opted in to the tracker prompt at end-of-workflow.

---

## Inputs

1. **JD** — either a tracker `jd_id` from a previous `/brains-jd-analyze` run, or a freshly pasted JD analysed inline.
2. **Resume version** — either a tracker `resume_version_id` or a file path to a recently produced DOCX/PDF.
3. **Cover letter** — same: tracker id, or file path, or null if not used.
4. **User's focus areas + healthy weekly rate** — read from `~/.brains-resume/profile.json`.

---

## Procedure

Ask the six questions one per turn. Take answers verbatim; record them in the tracker.

**Q1 — Duplicate check.**

```python
from scripts.tracker.query import find_duplicates

duplicates = find_duplicates(company, role_title)
if duplicates:
    most_recent = duplicates[0]
    # Ask the user:
    #   "You applied to {company} as {role_title} on {date}. Continue?"
    # If user proceeds, record `duplicate_acknowledged: True` in notes.
```

If no duplicates, skip this question silently.

**Q2 — JD findings recap.**

If the JD has analyzer findings (either freshly run or carried forward from `brains-jd-analyze`), summarise them in one sentence:

> "Quick recap of the JD findings: {N} soft-culture red flags, {M} masking-cost markers, {K} evidence-of-flex signals, role-fit score {S}/100. Want to review before submitting?"

If the user opts to review, repeat the analyzer's per-finding suggestions. Record `findings_acknowledged: True | declined` in notes.

**Q3 — Fit-or-pressure.**

> "Are you applying because the role genuinely fits, or because you feel pressure to apply somewhere this week? One-line answer."

Record the verbatim answer in the application's `notes` field. Do not judge or argue with the answer — record it and move on.

**Q4 — Pacing check.**

```python
from scripts.tracker.query import weekly_summary
from scripts.tracker.profile import read_profile, write_profile
from scripts.tracker.models import Profile

summary = weekly_summary()
profile = read_profile()
```

If `profile.healthy_weekly_rate` is None, ask once:

> "What's your healthy weekly application rate? (a number — applications per week you can sustain without burnout)"

Save the answer via `write_profile(Profile(focus_areas=profile.focus_areas, healthy_weekly_rate=N))`.

Then:

```python
if summary.pacing_vs_target == "above":
    # "You've submitted {summary.applications_count} applications in the last 7 days.
    #  Your stated healthy rate is {profile.healthy_weekly_rate}/week. Continue?"
elif summary.pacing_vs_target == "at":
    # "You're at your healthy weekly rate this week. Continue or pause?"
elif summary.pacing_vs_target == "below":
    # No prompt needed — under target is fine.
    pass
```

Record `pacing: above | at | below_target` in notes.

**Q5 — Cover letter check.**

If `cover_letter_id` is null and the channel typically expects one (`channel` in `('linkedin', 'agency', 'direct')` for most industries), ask:

> "This application doesn't have a cover letter attached. Most {channel} applications expect one. Add one now?"

If the user skips, record `cover_letter_omitted_deliberately: True` in notes. Offer the `brains-cover-letter` workflow if they want one.

**Q6 — Channel + agency.**

> "How are you submitting? (linkedin / agency / direct / referral / other)"

If the answer is `agency`, also ask for the agency name. Record in `applications.channel` and `applications.agency_name`.

---

## Output

Add a row to the `applications` table via `scripts/tracker/add.py:add_application`. The six question answers are JSON-encoded sub-fields inside `notes`:

```json
{
  "duplicate_acknowledged": true,
  "findings_acknowledged": "declined",
  "fit_or_pressure": "Genuine fit — this is the role I have been waiting for.",
  "pacing": "above",
  "cover_letter_omitted_deliberately": false
}
```

Surface the application id to the user for later outcome logging:

> "Application #N registered for {company} / {role}. To log outcomes later: `/brains-track update {N} <event-type>`."

---

## Output artifacts

| File | Notes |
|---|---|
| Tracker row in `applications` table | BRAINS coaching artifact (the row's `notes` field contains the user's verbatim answers) |
| (optional) `output/precheck-summary-YYYY-MM-DD-HHMMSS.md` | Saved only if the user requests |

---

## Safeguarding boundaries

- **Never blocks submission.** Every question can be answered, deferred, or skipped. The user always submits or doesn't.
- **The healthy weekly rate is user-defined.** The skill never recommends a number; it asks once and uses what the user provides.
- **The fit-or-pressure answer is recorded verbatim, not judged.** Don't argue with the user or suggest they should not apply.
- **Tracker-write only after Q6.** If the user abandons the workflow mid-flow, nothing is persisted.
