# Disclosure Framework Polish (v2.3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the disclosure coaching flow from a one-off conversation that drops an unlinked PDF into `output/` into a persisted, candidate-linked decision with structured outcomes the rest of the skill can read. The coaching *conversation* keeps happening in Claude Code (it's already good there); the dashboard becomes the place where the outcome is recorded and history is visible.

**Architecture:** New `disclosure_sessions` SQLite table (migration 0008), a `scripts/tracker/disclosure.py` CRUD module following the `candidates.py` pattern, a disclosure-specific markdown template + PDF generator with traceable artifact UIDs that mirror the resume/cover-letter UID scheme, a rebuilt dashboard surface (record-outcome form + history panel), and read-side hooks in the three downstream skills (`brains-tailor`, `brains-cover-letter`, `brains-review`) that respect the candidate's landed preference and surface what was applied.

**Tech Stack:** Python 3.14, SQLite (existing tracker DB), Streamlit (existing dashboard), pytest. No new dependencies.

**References:**
- [references/disclosure-decision-tree.md](../../references/disclosure-decision-tree.md) — the framework itself (default position, six factors, three strengths). Source of truth for all coaching language.
- [references/workflows/disclosure.md](../../references/workflows/disclosure.md) — procedural steps (a)–(g) for the coaching turn. Needs step (h) added — persist to DB.
- [output/disclosure-worksheet-2026-05-12-135314.md](../../output/disclosure-worksheet-2026-05-12-135314.md) — exemplar of what a polished worksheet looks like; the new template mirrors its structure.
- Migration patterns: [0005_candidates_table.py](../../scripts/tracker/migrations/0005_candidates_table.py), [0007_candidate_intent.py](../../scripts/tracker/migrations/0007_candidate_intent.py).
- CRUD patterns: [scripts/tracker/candidates.py](../../scripts/tracker/candidates.py).

---

## File Structure

| File | Responsibility |
|------|----------------|
| `scripts/tracker/migrations/0008_disclosure_sessions.py` | Schema migration: `disclosure_sessions` table + partial unique index on `artifact_uid`. |
| `scripts/tracker/disclosure.py` | CRUD: `create_session`, `get_session`, `list_sessions_for_candidate`, `get_latest_for_candidate`, `update_landed_strength`. |
| `scripts/tracker/models.py` | Add `DisclosureSession` dataclass + `DISCLOSURE_STRENGTHS` tuple. |
| `templates/disclosure_worksheet.md` | Disclosure-specific template (factor table, reasoning, three-strength reference, practical-fork section, downstream talking points, restated safeguarding caveats). |
| `scripts/generators/disclosure_worksheet.py` | Render the worksheet from a `DisclosureSession` + render branded PDF via the existing `coaching_report_to_pdf.py` machinery. |
| `scripts/dashboard/workflows/disclosure.py` | Replace the 4-line stub. Two sections: "Record a disclosure session" form (six factors → suggested strength → save → optional artifact generation) and "Past sessions" history table for the active candidate. |
| `references/workflows/disclosure.md` | Add step (h): persist the session to the tracker via `scripts/tracker/disclosure.py` after the worksheet is offered. |
| `references/workflows/tailor.md`, `cover-letter.md`, `review.md` | Add a "read landed disclosure preference" step at the start; surface "applied your X preference: Y" in the output. |

Tests mirror the source under `tests/tracker/`, `tests/tracker/migrations/`, `tests/generators/`, and `tests/dashboard/workflows/`.

**Dependency order:** `models` ← `migrations/0008` ← `disclosure.py` ← `generators/disclosure_worksheet` ← `dashboard/workflows/disclosure` ← `references/workflows/*.md`.

---

## Data Model

```sql
CREATE TABLE disclosure_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    created_at TEXT NOT NULL,
    target_employer TEXT,
    target_role TEXT,
    factor_1 TEXT,   -- employer ND-affirming?
    factor_2 TEXT,   -- role ND-adjacent?
    factor_3 TEXT,   -- ND-screened channel?
    factor_4 TEXT,   -- application-stage accommodation needed?
    factor_5 TEXT,   -- values-driven regardless of bias risk?
    factor_6 TEXT,   -- professional advice received?
    landed_strength TEXT NOT NULL,  -- one of: non-disclosure | neutral | explicit | undecided
    notes TEXT,
    artifact_uid TEXT,
    archived_at TEXT
);

CREATE INDEX idx_disclosure_sessions_candidate_id
    ON disclosure_sessions(candidate_id);
CREATE UNIQUE INDEX ux_disclosure_sessions_artifact_uid
    ON disclosure_sessions(artifact_uid) WHERE artifact_uid IS NOT NULL;
```

**Design notes:**
- Factor fields are `TEXT` rather than booleans because real answers include nuance ("conditional yes — employer/role dependent" from the May 2026 worksheet). Free text preserves that.
- `landed_strength` is required (`NOT NULL`) but admits `undecided` so a coaching session that didn't reach a decision can still be recorded.
- `artifact_uid` follows the existing scheme: nullable for sessions where no document was generated, partial-unique-index so old NULL rows don't collide.
- No `parent_uid` — disclosure sessions don't have a lineage relationship to each other; the candidate is the lineage.
- `archived_at` follows the standard soft-delete pattern used elsewhere in the schema.

**Suggestion algorithm (for the dashboard form, mirrors the coaching flow):**
- Count strong-yes answers across factors 1–3 and factor 5.
- 0 or 1 strong-yes → suggest **non-disclosure** (default).
- 2 → suggest **neutral signalling**.
- 3+ → suggest **explicit disclosure**.
- Factor 4 yes (need application-stage accommodation) bumps the suggestion one step up (non-disclosure → neutral → explicit) regardless of count, because participation requires some disclosure.
- Factor 6 yes (professional advice given) is informational — surfaced in the rationale but doesn't change the suggestion (the algorithm doesn't have the content of the advice).
- Always present as "the framework suggests X — you decide."

---

## Tasks

### Phase 1 — Data layer

- [ ] **Task 1** — Add `DisclosureSession` dataclass and `DISCLOSURE_STRENGTHS = ("non-disclosure", "neutral", "explicit", "undecided")` tuple to [scripts/tracker/models.py](../../scripts/tracker/models.py). Match the field order to the column order above.
- [ ] **Task 2** — Write [scripts/tracker/migrations/0008_disclosure_sessions.py](../../scripts/tracker/migrations/0008_disclosure_sessions.py) following the 0005/0007 patterns: `SCHEMA_SQL` module-level constant + `apply(conn)` function.
- [ ] **Task 3** — Write `tests/tracker/migrations/test_0008_disclosure_sessions.py`: table exists, FK to candidates works, partial unique index rejects duplicate non-null UIDs but allows multiple NULLs, `archived_at` defaults to NULL.
- [ ] **Task 4** — Write [scripts/tracker/disclosure.py](../../scripts/tracker/disclosure.py) — CRUD module:
  - `create_session(candidate_id, factors: dict, landed_strength, target_employer=None, target_role=None, notes=None, artifact_uid=None) -> int`
  - `get_session(session_id) -> Optional[DisclosureSession]`
  - `list_sessions_for_candidate(candidate_id, include_archived=False) -> List[DisclosureSession]`
  - `get_latest_for_candidate(candidate_id) -> Optional[DisclosureSession]` — returns the most-recent non-archived session
  - `update_landed_strength(session_id, landed_strength) -> None`
  - `archive_session(session_id) -> None`
- [ ] **Task 5** — Write `tests/tracker/test_disclosure.py`: round-trip create/get, list returns most-recent-first, `get_latest_for_candidate` excludes archived sessions, `update_landed_strength` validates against `DISCLOSURE_STRENGTHS`.

### Phase 2 — Artifact generation

- [ ] **Task 6** — Write [templates/disclosure_worksheet.md](../../templates/disclosure_worksheet.md). Sections, in order: title with candidate name + prepared date; boundary statements (verbatim from `references/workflows/disclosure.md`); summary paragraph; default position (verbatim); six-factor answers table; suggested strength with reasoning; three-strength reference; practical-fork section ("if your situation has nuance like the example below..."); downstream talking points (interview / post-offer / post-acceptance); recommended next steps; restated boundary statements; trust footer line. Use `{{PLACEHOLDER}}` tokens.
- [ ] **Task 7** — Write [scripts/generators/disclosure_worksheet.py](../../scripts/generators/disclosure_worksheet.py):
  - `render_markdown(session: DisclosureSession, candidate: Candidate) -> str` — substitute placeholders.
  - `render_pdf(markdown_path: Path, output_path: Path) -> None` — delegate to `coaching_report_to_pdf` with `include_trust_footer=True`.
  - `generate(session_id: int, output_dir: Path = Path("output")) -> tuple[Path, Path]` — high-level: load session + candidate, write `<candidate_slug>/disclosure-<artifact_uid>.md` and `.pdf`, return both paths. Generates a new `artifact_uid` if the session doesn't have one yet and persists it via `disclosure.set_artifact_uid`.
- [ ] **Task 8** — Write `tests/generators/test_disclosure_worksheet.py`: markdown render includes every required section verbatim; the safeguarding caveat appears at both top and bottom; PDF renders without exception; output paths follow the `<candidate>/disclosure-<uid>` convention.

### Phase 3 — Dashboard surface

- [ ] **Task 9** — Rewrite [scripts/dashboard/workflows/disclosure.py](../../scripts/dashboard/workflows/disclosure.py). Three sections, vertically stacked:
  1. **Header + safeguarding caveat** — verbatim from the workflow spec, displayed every time the page loads.
  2. **Record a session form** — six text inputs (one per factor, with the factor question as the label, ~3 lines tall each); employer/role inputs; "Suggested strength" derived live from the inputs using the algorithm above; landed-strength select (defaults to suggestion, user can override); notes textarea; "Save session" button → calls `disclosure.create_session`; "Save + generate worksheet" button → also calls `disclosure_worksheet.generate` and offers the PDF for download.
  3. **Past sessions panel** — table of all non-archived sessions for the active candidate, columns: `created_at`, `target_employer`, `target_role`, `landed_strength`, `worksheet?` (link if `artifact_uid` set), `archive` action.
- [ ] **Task 10** — Write `tests/dashboard/workflows/test_disclosure.py`: form submission inserts a row; suggestion logic returns the expected strength for representative input combinations; history panel filters by active candidate; archive action soft-deletes only the targeted row.

### Phase 4 — Workflow integration

- [ ] **Task 11** — Update [references/workflows/disclosure.md](../../references/workflows/disclosure.md). Add step (h) **after** step (f) (worksheet generation) and **before** step (g) (continue offer):
  - **(h) Persist the session to the tracker.** Call `scripts.tracker.disclosure.create_session(...)` with the candidate's `candidate_id`, the six factor answers, the landed strength, the target employer/role, and any notes. If a worksheet was generated in step (f), pass its `artifact_uid`. Surface to the user: "Your disclosure session has been recorded against your candidate record. The next time you run a resume tailor or review, your landed preference will be applied — and you can see it in the dashboard's Disclosure tab."
- [ ] **Task 12** — Update [references/workflows/tailor.md](../../references/workflows/tailor.md), [references/workflows/cover-letter.md](../../references/workflows/cover-letter.md) (if it exists), and [references/workflows/review.md](../../references/workflows/review.md). At the start of each, read `disclosure.get_latest_for_candidate(active_candidate_id)`. Behaviour by `landed_strength`:
  - **non-disclosure** — strip explicit ND identity references during tailor/edit; flag any during review. Surface: "Applied your non-disclosure preference (recorded YYYY-MM-DD) — removed/flagged: [list]."
  - **neutral** — preserve neutral-signalling language (the framework's reframed competency framing); flag explicit identity language. Surface: "Applied your neutral-signalling preference — kept: [list], flagged: [list]."
  - **explicit** — preserve identity language; do nothing extra. Surface: "Your explicit-disclosure preference is on file — no changes needed."
  - **undecided** or no session — proceed as currently, no preference applied. Surface nothing.
- [ ] **Task 13** — Write `tests/workflows/test_disclosure_preference_propagation.py` (integration): create a candidate, record a `non-disclosure` session, run the tailor workflow on a resume containing explicit ND identity language, assert the output strips/flags the identity content and the "applied your X preference" line appears.

### Phase 5 — Wrap

- [ ] **Task 14** — Update [STATUS.yml](../../STATUS.yml): `current_milestone: v2.3`, mark workstream `RL` complete, refresh `notes`, drop the disclosure backlog item.
- [ ] **Task 15** — Update [CHANGELOG.md](../../CHANGELOG.md) (if present) with v2.3 entry.
- [ ] **Task 16** — Manual smoke: create a candidate, run `/brains-disclosure` end-to-end, check the row in the DB, check the worksheet PDF renders, run `/brains-tailor` and confirm the preference banner appears.

---

## Out of Scope

- Rebuilding the LLM coaching turn inside Streamlit. The conversation stays in Claude Code; the dashboard records outcomes.
- Versioning or diffing disclosure sessions over time. List view is enough — if the user changes their mind, they record a new session.
- Multi-candidate disclosure preference sync. Each candidate has their own sessions, period.
- Disclosure-stance enforcement at the **review** stage beyond flagging. Review is read-only; the user decides whether to act.
- A separate "disclosure history" output folder convention. Worksheets live under the existing per-candidate output folder structure introduced in v1.5.

---

## Verification

Before claiming done:
- `pytest tests/tracker/ tests/generators/ tests/dashboard/workflows/test_disclosure.py tests/workflows/test_disclosure_preference_propagation.py` — all green.
- Full test suite — no regressions.
- Manual run-through of Task 16 — happy path works.
- Dashboard's Disclosure tab no longer says "open Claude Code to start the coaching turn."
- A fresh candidate with no session sees the form; a candidate with sessions sees both the form and the history.
