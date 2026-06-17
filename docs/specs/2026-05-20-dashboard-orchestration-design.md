# Dashboard Orchestration Redesign — Design Spec

**Date:** 2026-05-20
**Status:** Approved (brainstorm) — pending implementation plan
**Target version:** v2.1.0 (phased)

---

## 1. Goal

Re-architect the BRAINS Resume dashboard from a flat, nine-tab reporting tool into an
**orchestration hub**: a customizable widget-canvas home, backed by a *playbook engine*
that sequences the skill's functions into guided journeys with auto-tracked progress.
The command prompt (Claude Code) becomes a hidden execution engine, not a destination.

## 2. Background & motivation

The skill is robust and broad — 16 commands, a SQLite tracker, a Streamlit dashboard
(v1.3 → v2.0). But the functions are presented as a flat menu: nine reporting tabs and
eight workflow cards with no notion of "what do I do next." The dashboard already holds
the database and runs the pure-Python validators in-browser; what remains
"command-prompt-driven" is the LLM work (interview, generation, rewrites), reached today
by copying a slash command to the clipboard and pasting it into Claude Code.

This redesign keeps that handoff but reframes it: the dashboard sequences the steps,
tracks progress, pre-fills context, and reports — so the handoff feels like a single
"Continue" inside a guided journey.

### Decisions locked during brainstorming

- **Execution model:** Orchestration hub. LLM steps still hand off to Claude Code; the
  dashboard orchestrates. No Claude API integration, no per-use cost. (Rejected:
  API-in-dashboard; hybrid.)
- **Home screen:** Guided Playbooks as the primary model, rendered as a customizable
  widget canvas. (Rejected as *primary*: pipeline board; next-action worklist — both
  retained as widgets.)
- **Widget canvas:** Configurable add / remove / reorder via a Customize mode, native
  Streamlit, no literal drag-and-drop. Layout persists per candidate. (Rejected:
  `streamlit-elements` drag-and-drop; re-platforming off Streamlit.)
- **Step tracking:** Auto-detect step completion from the tracker DB, with a manual
  override always available. (Rejected: manual-only; auto-only.)
- **Onboarding:** Resume-first. No upfront questionnaire. (Rejected: standalone intake
  form; intake interview handoff; minimal-then-progressive as a standalone feature.)

## 3. Architecture

Three layers, each independently testable:

1. **Playbook engine** — pure-Python, no Streamlit, no LLM. Playbook definitions, a
   runner, and completion predicates. Bulk of the unit tests.
2. **Widget canvas** — Streamlit. The new Home tab: a grid of widgets with a Customize
   mode.
3. **State** — the existing SQLite tracker, extended with new tables/columns. No new
   database.

The existing tabs remain as deep drill-down views. The new **Home** tab is the default
landing surface — the orchestration layer sits *on top of* the existing tabs.

## 4. The playbook engine

### 4.1 Playbooks

A **playbook** is an ordered list of steps. Five playbooks ship, all assembled from
existing commands:

| `playbook_key`     | Steps |
|--------------------|-------|
| `apply_to_job`     | analyze JD → tailor resume *(or create if no base resume)* → cover letter → final check → pre-check → submit & track |
| `build_resume`     | interview/create → review → edit → final check |
| `improve_resume`   | review → edit → final check / de-AI |
| `refresh_linkedin` | ingest export → consolidate vs resume → rewrite profile |
| `career_change`    | translate experience → *(feeds into `apply_to_job` or `build_resume`)* |

Playbook *definitions* are hardcoded Python — one module per playbook. Playbook
*progress* is stored in the DB. (Rejected: data-driven definitions in the DB — no
requirement for user-authored playbooks; YAGNI.)

Functions not in a playbook — standalone JD-analyze, the tracker, disclosure coaching,
a standalone de-AI scan — remain available as individual widget cards (quick-launch).

### 4.2 Step model

Each step has a **kind**:

- **`in_dashboard`** — the dashboard runs it itself (the pure-Python validators: review,
  check, de-AI scan). Completion is known synchronously the moment it runs; no polling.
- **`handoff`** — LLM work that hands off to Claude Code (create, tailor, cover letter,
  edit, consolidate, LinkedIn rewrite). Completion is detected by a **predicate**.

### 4.3 Completion predicates

A predicate is a query against the tracker DB that returns true when the step's output
exists. Examples:

- "analyze JD" → a `jds` row exists for this candidate / this JD.
- "tailor resume" → a `resume_versions` row tagged to this `jd_id` exists.
- "cover letter" → a `cover_letters` row for that resume + JD exists.
- "submit & track" → an `applications` row for this JD exists.

For non-JD playbooks (e.g. `build_resume`), predicates bound their query by the run's
`created_at` (e.g. "a `resume_versions` row for this candidate created after the run
started").

`in_dashboard` steps need no predicate — the dashboard executed them.

### 4.4 The runner

On each render, for an active run: evaluate the current step's predicate. If true, bump
`current_step`; if it was the last step, set `status = 'completed'`. A manual override is
always shown — "I've done this" advances, "not yet" holds. Auto-vs-manual completion is
transient UI feedback, not persisted.

### 4.5 Run context — the "seamless Continue"

A run carries `candidate_id` and (for `apply_to_job`) `jd_id`. Each step's handoff
command is **pre-built from that context** — step 3's "cover letter" handoff already has
the resume path and JD id baked in. The user never re-enters anything; they click
Continue. Artifact UIDs are *not* stored on the run — the tracker DB is the source of
truth and predicates/pre-fill re-derive them.

A run is keyed by `(candidate, playbook, optional jd_id)` — so "Apply to Big W" and
"Apply to Coles" are separate, parallel runs.

## 5. Resume-first onboarding

No upfront questionnaire. Onboarding rides on the candidate's first real piece of work.

1. **Create candidate** — collects only **name + email**. The candidate row starts
   nearly empty.
2. **Has a resume:** the candidate loads their first resume → **review runs**
   (the in-dashboard validators + a parse of the resume's actual content: history,
   skills, education, years of experience).
3. **Clarifying questions** — *after* the review, a short in-dashboard mini-form asks
   only the gap the resume cannot show: direction, focus, leadership intent, timeline,
   work preferences, location. Values are **pre-guessed from the parsed resume** (e.g.
   career stage inferred from years of experience) for the user to confirm or correct.
   No LLM needed.
4. **"What next"** — the candidate is offered the aligned next steps (Edit to apply the
   review recommendations · Tailor to a job · Build a cover letter) **or** "go to the
   dashboard and pick."
5. **No-resume branch** (e.g. a student building a first resume): the candidate goes
   straight into the `build_resume` playbook. The create/interview already collects
   history, skills, and intent — the profile populates as a byproduct.

The "what next" screen is a **general pattern**: every playbook step ends by suggesting
the recommended next step *and* offering the dashboard.

The career-intent fields collected in step 3 are stored as new columns on the
`candidates` table (see §7.2). They personalize playbook recommendations and pre-fill
playbook context (target roles feed the JD analyzer; leadership intent tells tailoring
to foreground people-management evidence).

**Excluded from intake** (privacy / relevance): age or date of birth, neurodivergence
diagnosis (routed to the existing `/brains-disclosure` consent flow, never collected
casually), salary history, protected characteristics.

## 6. The widget canvas (the new Home)

The Home tab is a grid of **widgets** in two zones.

### 6.1 Widget catalog

| `widget_key`            | Zone   | Description |
|-------------------------|--------|-------------|
| `in_progress_runs`      | upper  | Active playbook runs with a one-click Continue |
| `playbook_apply`        | upper  | "Apply to a job" playbook card |
| `playbook_build`        | upper  | "Build a base resume" playbook card |
| `playbook_improve`      | upper  | "Improve a resume" playbook card |
| `playbook_linkedin`     | upper  | "Refresh LinkedIn" playbook card |
| `playbook_career_change`| upper  | "Career change" playbook card |
| `worklist`              | lower  | Computed next-actions list with one-click jumps |
| `pipeline_mini`         | lower  | Applications across stages; click a card → its checklist |
| `tile_pacing`           | lower  | Weekly rate vs target |
| `tile_drift`            | lower  | Drift sparkline |
| `tile_library_counts`   | lower  | Resume / cover-letter / JD counts |
| `quick_launch`          | lower  | Standalone functions: JD-analyze, de-AI scan, disclosure |
| `tile_recent_outcomes`  | lower  | *(available to add; off by default)* recent application outcomes |

Each widget is a small self-contained render function.

### 6.2 Customize mode

The ⚙ Customize control opens a panel: per-widget enable/disable toggles and
move-up / move-down reordering. The resulting layout is **saved per candidate**, so
different candidates can have different Home layouts. A sensible **default layout**
ships, so a new candidate never sees a blank canvas.

### 6.3 Constraint (YAGNI)

Widgets are not arbitrarily resizable; there is no free-form pixel placement. The layout
is an ordered, enabled/disabled list rendered into a tidy responsive grid. This is what
keeps the canvas robust in Streamlit.

## 7. Data model

### 7.1 Migration `0006_dashboard_orchestration.py`

Forward-only, auto-discovered. New empty tables — no backfill.

**`dashboard_layout`** — per-candidate widget canvas

```
id            INTEGER PRIMARY KEY
candidate_id  INTEGER NOT NULL          -- FK candidates(id)
widget_key    TEXT    NOT NULL          -- e.g. 'worklist', 'playbook_apply'
position      INTEGER NOT NULL
enabled       INTEGER NOT NULL DEFAULT 1
created_at    TEXT    NOT NULL
UNIQUE(candidate_id, widget_key)
```

No rows for a candidate → render the default layout. Customize mode writes these rows.
A row with a `widget_key` absent from the current catalog is skipped silently.

**`playbook_runs`** — one row per playbook run

```
id            INTEGER PRIMARY KEY
candidate_id  INTEGER NOT NULL          -- FK candidates(id)
playbook_key  TEXT    NOT NULL          -- 'apply_to_job' | 'build_resume' | ...
jd_id         INTEGER NULL              -- FK jds(id); set for apply_to_job runs
current_step  INTEGER NOT NULL DEFAULT 0
status        TEXT    NOT NULL DEFAULT 'active'   -- 'active'|'completed'|'abandoned'
created_at    TEXT    NOT NULL
updated_at    TEXT    NOT NULL
completed_at  TEXT    NULL
```

Index on `(candidate_id, status)`.

### 7.2 Migration `0007_candidate_intent.py`

Forward-only. Adds nullable career-intent columns to `candidates` (populated by the
onboarding clarifying form, §5 step 3):

```
career_stage       TEXT    NULL   -- student|first_job|early|mid|senior|executive|returning|career_changer
direction          TEXT    NULL   -- grow|leadership|pivot|first_role|re_enter
target_roles       TEXT    NULL   -- JSON list
target_industries  TEXT    NULL   -- JSON list
leadership_intent  TEXT    NULL   -- yes|no|maybe
work_preferences   TEXT    NULL   -- JSON: location mode + employment type
location           TEXT    NULL
relocation_open    INTEGER NULL
role_priorities    TEXT    NULL   -- free text: "what matters in a role"
timeline           TEXT    NULL   -- actively_applying|exploring|passive
intent_collected_at TEXT   NULL   -- null until the clarifying form is completed
```

All nullable — an existing candidate is valid with every field null.

## 8. Navigation / IA changes

The new Home absorbs two existing tabs:

- The **Overview** tab (summary tiles) → becomes reporting widgets on Home.
- The **Workflows** tab (eight workflow cards) → becomes the playbook cards +
  quick-launch widget on Home.

Result: **nine tabs → eight** — Home, Resumes, Cover Letters, JDs, Applications,
Analytics, Pacing, Drift. The seven non-Home tabs remain as deep drill-down views;
worklist items and pipeline cards jump into them. Standalone workflow cards stay
reachable individually via quick-launch — power users are not forced through playbooks.

## 9. Error handling

- A completion predicate that raises → treated as "not complete," logged; the manual
  override is shown. The canvas never crashes on a bad predicate.
- A `dashboard_layout` row with an unknown `widget_key` → skipped silently. Empty
  layout → default layout.
- No active candidate → the existing candidate-guard pattern (consistent with the v2.0
  per-tab guards).
- A run whose `jd_id` was deleted or whose candidate was archived → shown as abandoned;
  joins are guarded.
- A handoff step Claude Code never completes → the run waits at that step; the manual
  override and an "abandon run" control prevent a permanently stuck state.
- Migrations 0006/0007 are additive; failure rolls back the transaction (consistent with
  the existing migration pattern).

## 10. Testing strategy

- **Playbook engine** — pure-Python, no Streamlit. Unit-test playbook definitions, the
  runner's advance logic, and every completion predicate against a seeded in-memory
  tracker DB. Matches the `tests/tracker` / `tests/drift` style. This is the bulk of the
  new tests.
- **Migrations 0006 / 0007** — table- and column-shape tests, like
  `tests/tracker/migrations/test_0005_candidates_table.py`.
- **Widget canvas + widgets** — the existing `AppTest` smoke-test approach in
  `tests/dashboard`: render Home, assert widgets appear, assert Customize toggles
  add/remove/reorder.
- **Onboarding** — test the resume parse → pre-guess heuristics, and the clarifying form
  writing intent columns.

## 11. Phasing

Three independently shippable phases, each producing working, tested software:

1. **Phase 1 — Engine + data.** Migration 0006, the five playbook definitions, the
   runner, completion predicates, `playbook_runs`. No UI. Fully unit-tested.
2. **Phase 2 — Widget canvas Home.** The new Home tab, widget catalog, default layout,
   Customize mode, `dashboard_layout`. Wires the playbook engine into the In-progress and
   playbook-card widgets. Merges away the Overview and Workflows tabs.
3. **Phase 3 — Resume-first onboarding.** Migration 0007, name+email-only candidate
   creation, the post-review clarifying form with resume-informed pre-guessing, the
   "what next" hand-off pattern.

## 12. Out of scope / YAGNI

- No Claude API integration; the LLM handoff to Claude Code stays.
- No literal drag-and-drop; no widget resizing or free-form placement.
- No user-authored playbooks; the five definitions are hardcoded.
- No new database; the existing SQLite tracker is extended.
- No collection of sensitive intake data (see §5).
- The `for_candidate` text columns and other v2.0 structures are untouched.

## 13. Success criteria

- Opening the dashboard lands on the Home widget canvas with a working default layout.
- Starting a playbook creates a `playbook_runs` row; completing a handoff step
  auto-advances the run (verified by predicate), with a working manual override.
- Customize mode adds/removes/reorders widgets and the layout survives a restart,
  per candidate.
- Creating a candidate collects only name + email; the first resume's review is followed
  by the clarifying form; intent columns are populated.
- The full test suite is green; the Overview and Workflows tabs are gone, replaced by
  Home.
