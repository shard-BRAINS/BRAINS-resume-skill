# Dashboard Orchestration — Phase 3 (Resume-First Onboarding) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace cold candidate setup with resume-first onboarding — candidate creation collects only name + email, and a Home-tab onboarding surface gathers career intent once.

**Architecture:** Migration 0007 adds an `email` column and eleven career-intent columns to `candidates`. Candidate creation is trimmed to name + email. A new onboarding surface renders on the Home tab whenever the active candidate's `intent_collected_at` is null; it shows resume context and a short clarifying form that, on submit, writes the intent fields and stamps `intent_collected_at` — after which the surface disappears.

**Tech Stack:** Python 3.14, SQLite tracker, Streamlit, pytest. No new dependencies.

**Reference:** `docs/specs/2026-05-20-dashboard-orchestration-design.md` (§5 resume-first onboarding, §7.2 migration 0007). Phases 1 and 2 are merged to `main`.

---

## Design decisions locked for this plan

- **`email` column.** Spec §5 says creation collects name + email, but spec §7.2's column list omitted `email`. This plan adds `email TEXT` to migration 0007 alongside the intent columns. (Flagged as a spec gap, resolved here.)
- **Onboarding is a Home-tab surface, not a catalog widget.** It renders above the widget canvas when `intent_collected_at IS NULL`. It is a system surface — deliberately NOT in the customizable widget catalog (a user must not be able to hide their own incomplete-profile prompt).
- **State-driven, not event-driven.** The spec narrates "after the review, ask questions." Reviews leave no tracker row, so "after a review" is not detectable. Instead the surface is gated purely on `intent_collected_at`: it shows until intent is collected. This is faithful to the spec's intent (no cold questionnaire; profile completes as a byproduct) and robust.
- **"Resume-informed" = resume context shown, not auto-guessed.** The onboarding surface displays whether the candidate has a resume on file (and the latest one's facts, from `resume_versions`). It does NOT auto-guess enum values like `career_stage` — guessing career stage from free resume text is unreliable, and a wrong default is worse than a blank field. The user answers a short form with the resume context visible.
- **`create_candidate` gets a trailing optional `email` parameter** rather than a signature rewrite — this keeps the blast radius off the ~100 existing `create_candidate("A","B",[],None,None)` test call sites.
- **Intent is collected once.** Re-editing intent after `intent_collected_at` is set is out of scope for Phase 3 (the Edit-candidate expander still covers name/email/focus/rate/notes). Noted as a possible future follow-up.
- **Version bumps to 2.2.0.**

## File Structure

| File | Responsibility |
|------|----------------|
| `scripts/tracker/migrations/0007_candidate_intent.py` | Migration: `email` + 11 career-intent columns on `candidates`. |
| `scripts/tracker/models.py` | *Modify* — extend the `Candidate` dataclass with the 12 new fields. |
| `scripts/tracker/candidates.py` | *Modify* — read/write the new columns; `create_candidate` gains `email`; new `update_candidate_intent`. |
| `scripts/dashboard/widgets/onboarding.py` | The onboarding surface: `onboarding_needed`, `resume_context`, `render_onboarding`. |
| `scripts/dashboard/sidebar.py` | *Modify* — new-candidate form trimmed to name + email; Edit form gains email. |
| `scripts/dashboard/tabs/home.py` | *Modify* — render the onboarding surface above the canvas when needed. |
| `scripts/outputs/io.py`, `pyproject.toml`, `CHANGELOG.md` | *Modify* — version bump to 2.2.0. |

The venv interpreter is `c:\Brains_Resume_Skill\.venv\Scripts\python.exe`. Run all commands from `c:\Brains_Resume_Skill`.

---

## Task 1: Migration 0007 — email + career-intent columns

**Files:**
- Create: `scripts/tracker/migrations/0007_candidate_intent.py`
- Test: `tests/tracker/migrations/test_0007_candidate_intent.py`

- [ ] **Step 1: Write the failing test**

Create `tests/tracker/migrations/test_0007_candidate_intent.py`:

```python
"""Tests for migration 0007 — email + career-intent columns on candidates."""
import pytest

from scripts.tracker.db import open_db


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_candidates_has_all_intent_columns(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(candidates)")}
        assert {
            "email", "career_stage", "direction", "target_roles",
            "target_industries", "leadership_intent", "work_preferences",
            "location", "relocation_open", "role_priorities", "timeline",
            "intent_collected_at",
        } <= cols
    finally:
        conn.close()


def test_existing_columns_preserved(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(candidates)")}
        assert {"id", "first_name", "last_name", "focus_areas",
                "healthy_weekly_rate", "pacing_notes",
                "created_at", "archived_at"} <= cols
    finally:
        conn.close()


def test_intent_columns_default_null(isolated_db):
    """A new candidate has every intent column null until onboarding runs."""
    conn = open_db()
    try:
        conn.execute(
            "INSERT INTO candidates (first_name, last_name, created_at) "
            "VALUES ('A', 'B', '2026-01-01T00:00:00Z')")
        row = conn.execute(
            "SELECT email, career_stage, intent_collected_at FROM candidates"
        ).fetchone()
        assert row == (None, None, None)
    finally:
        conn.close()


def test_migration_recorded(isolated_db):
    conn = open_db()
    try:
        versions = [row[0] for row in conn.execute(
            "SELECT version FROM migrations ORDER BY version")]
        assert 7 in versions
    finally:
        conn.close()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/migrations/test_0007_candidate_intent.py -v`
Expected: FAIL — the columns do not exist; `7` is not in `migrations`.

- [ ] **Step 3: Write the migration**

Create `scripts/tracker/migrations/0007_candidate_intent.py`:

```python
"""Migration 0007 — career-intent columns on candidates.

Additive, schema-only. Adds an email column plus eleven nullable
career-intent columns populated by the resume-first onboarding surface
(Phase 3). Every column is nullable — an existing candidate stays valid
with all of them null.

See docs/specs/2026-05-20-dashboard-orchestration-design.md (Section 5, 7.2).
"""
import sqlite3


SCHEMA_SQL = """
ALTER TABLE candidates ADD COLUMN email TEXT;
ALTER TABLE candidates ADD COLUMN career_stage TEXT;
ALTER TABLE candidates ADD COLUMN direction TEXT;
ALTER TABLE candidates ADD COLUMN target_roles TEXT;
ALTER TABLE candidates ADD COLUMN target_industries TEXT;
ALTER TABLE candidates ADD COLUMN leadership_intent TEXT;
ALTER TABLE candidates ADD COLUMN work_preferences TEXT;
ALTER TABLE candidates ADD COLUMN location TEXT;
ALTER TABLE candidates ADD COLUMN relocation_open INTEGER;
ALTER TABLE candidates ADD COLUMN role_priorities TEXT;
ALTER TABLE candidates ADD COLUMN timeline TEXT;
ALTER TABLE candidates ADD COLUMN intent_collected_at TEXT;
"""


def apply(conn: sqlite3.Connection) -> None:
    """Add the email + career-intent columns to the candidates table."""
    conn.executescript(SCHEMA_SQL)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/migrations/test_0007_candidate_intent.py -v`
Expected: PASS — all 4 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/tracker/migrations/0007_candidate_intent.py tests/tracker/migrations/test_0007_candidate_intent.py
git commit -m "feat(tracker): migration 0007 — email + career-intent columns"
```

---

## Task 2: Candidate model + intent CRUD

**Files:**
- Modify: `scripts/tracker/models.py`
- Modify: `scripts/tracker/candidates.py`
- Test: `tests/tracker/test_candidate_intent.py`

- [ ] **Step 1: Write the failing test**

Create `tests/tracker/test_candidate_intent.py`:

```python
"""Tests for candidate email + career-intent CRUD."""
import pytest

from scripts.tracker.candidates import (
    create_candidate, get_candidate, update_candidate_intent,
)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_create_candidate_stores_email(isolated):
    cid = create_candidate("Mathilda", "Gell", [], None, None,
                           email="mathilda@example.com")
    assert get_candidate(cid).email == "mathilda@example.com"


def test_create_candidate_email_defaults_none(isolated):
    cid = create_candidate("A", "B", [], None, None)
    c = get_candidate(cid)
    assert c.email is None
    assert c.intent_collected_at is None
    assert c.career_stage is None
    assert c.target_roles == []


def test_update_candidate_intent_writes_fields(isolated):
    cid = create_candidate("A", "B", [], None, None)
    update_candidate_intent(
        cid,
        career_stage="student",
        direction="first_role",
        target_roles=["Retail assistant", "Barista"],
        target_industries=["Retail"],
        leadership_intent="maybe",
        work_preferences=["part_time", "casual"],
        location="Brisbane QLD",
        relocation_open=0,
        role_priorities="Flexible hours.",
        timeline="actively_applying",
    )
    c = get_candidate(cid)
    assert c.career_stage == "student"
    assert c.direction == "first_role"
    assert c.target_roles == ["Retail assistant", "Barista"]
    assert c.target_industries == ["Retail"]
    assert c.leadership_intent == "maybe"
    assert c.work_preferences == ["part_time", "casual"]
    assert c.location == "Brisbane QLD"
    assert c.relocation_open == 0
    assert c.role_priorities == "Flexible hours."
    assert c.timeline == "actively_applying"


def test_update_candidate_intent_stamps_collected_at(isolated):
    cid = create_candidate("A", "B", [], None, None)
    assert get_candidate(cid).intent_collected_at is None
    update_candidate_intent(cid, career_stage="mid")
    assert get_candidate(cid).intent_collected_at is not None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_candidate_intent.py -v`
Expected: FAIL — `create_candidate` has no `email` kwarg; `update_candidate_intent` does not exist.

- [ ] **Step 3: Extend the `Candidate` dataclass**

In `scripts/tracker/models.py`, change the import line `from dataclasses import dataclass` to:

```python
from dataclasses import dataclass, field
```

Then replace the entire `Candidate` dataclass with:

```python
@dataclass
class Candidate:
    id: Optional[int]
    first_name: str
    last_name: str
    focus_areas: List[str]
    healthy_weekly_rate: Optional[int]
    pacing_notes: Optional[str]
    created_at: str
    archived_at: Optional[str]
    email: Optional[str] = None
    career_stage: Optional[str] = None
    direction: Optional[str] = None
    target_roles: List[str] = field(default_factory=list)
    target_industries: List[str] = field(default_factory=list)
    leadership_intent: Optional[str] = None
    work_preferences: List[str] = field(default_factory=list)
    location: Optional[str] = None
    relocation_open: Optional[int] = None
    role_priorities: Optional[str] = None
    timeline: Optional[str] = None
    intent_collected_at: Optional[str] = None
```

- [ ] **Step 4: Update `candidates.py`**

In `scripts/tracker/candidates.py`:

(a) Replace the `_row_to_candidate` function with:

```python
_CANDIDATE_COLS = (
    "id, first_name, last_name, focus_areas, healthy_weekly_rate, "
    "pacing_notes, created_at, archived_at, email, career_stage, direction, "
    "target_roles, target_industries, leadership_intent, work_preferences, "
    "location, relocation_open, role_priorities, timeline, intent_collected_at"
)


def _row_to_candidate(row) -> Candidate:
    return Candidate(
        id=row[0], first_name=row[1], last_name=row[2],
        focus_areas=json.loads(row[3] or "[]"),
        healthy_weekly_rate=row[4], pacing_notes=row[5],
        created_at=row[6], archived_at=row[7],
        email=row[8], career_stage=row[9], direction=row[10],
        target_roles=json.loads(row[11] or "[]"),
        target_industries=json.loads(row[12] or "[]"),
        leadership_intent=row[13],
        work_preferences=json.loads(row[14] or "[]"),
        location=row[15], relocation_open=row[16],
        role_priorities=row[17], timeline=row[18],
        intent_collected_at=row[19],
    )
```

(b) Replace the `create_candidate` function with (adds the trailing `email` parameter):

```python
def create_candidate(
    first_name: str,
    last_name: str,
    focus_areas: List[str],
    healthy_weekly_rate: Optional[int],
    pacing_notes: Optional[str],
    email: Optional[str] = None,
) -> int:
    conn = open_db()
    try:
        cur = conn.execute(
            """INSERT INTO candidates
                 (first_name, last_name, focus_areas, healthy_weekly_rate,
                  pacing_notes, created_at, email)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (first_name, last_name, json.dumps(focus_areas),
             healthy_weekly_rate, pacing_notes, _now_iso(), email),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
```

(c) Replace the `get_candidate` function with (uses `_CANDIDATE_COLS`):

```python
def get_candidate(candidate_id: int) -> Optional[Candidate]:
    conn = open_db()
    try:
        row = conn.execute(
            f"SELECT {_CANDIDATE_COLS} FROM candidates WHERE id=?",
            (candidate_id,),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_candidate(row) if row else None
```

(d) Replace the `list_candidates` function with (uses `_CANDIDATE_COLS`):

```python
def list_candidates(include_archived: bool = False) -> List[Candidate]:
    conn = open_db()
    try:
        sql = f"SELECT {_CANDIDATE_COLS} FROM candidates"
        if not include_archived:
            sql += " WHERE archived_at IS NULL"
        sql += " ORDER BY created_at ASC"
        rows = conn.execute(sql).fetchall()
    finally:
        conn.close()
    return [_row_to_candidate(r) for r in rows]
```

(e) Add `email` to the partial-update `update_candidate` function — insert this block immediately after the existing `if pacing_notes is not None:` block, before `if not sets:`:

```python
    if email is not None:
        sets.append("email=?"); params.append(email)
```

And add `email: Optional[str] = None,` to the `update_candidate` signature (after the `pacing_notes` parameter).

(f) Append a new `update_candidate_intent` function at the end of the file:

```python
def update_candidate_intent(
    candidate_id: int,
    *,
    career_stage: Optional[str] = None,
    direction: Optional[str] = None,
    target_roles: Optional[List[str]] = None,
    target_industries: Optional[List[str]] = None,
    leadership_intent: Optional[str] = None,
    work_preferences: Optional[List[str]] = None,
    location: Optional[str] = None,
    relocation_open: Optional[int] = None,
    role_priorities: Optional[str] = None,
    timeline: Optional[str] = None,
) -> None:
    """Write the career-intent fields and stamp intent_collected_at.

    The onboarding form submits every field together, so this is a full
    write of the intent block (not a partial update). List fields are
    JSON-encoded; None lists become an empty JSON array.
    """
    conn = open_db()
    try:
        conn.execute(
            """UPDATE candidates SET
                 career_stage=?, direction=?, target_roles=?,
                 target_industries=?, leadership_intent=?, work_preferences=?,
                 location=?, relocation_open=?, role_priorities=?, timeline=?,
                 intent_collected_at=?
               WHERE id=?""",
            (
                career_stage, direction, json.dumps(target_roles or []),
                json.dumps(target_industries or []), leadership_intent,
                json.dumps(work_preferences or []), location, relocation_open,
                role_priorities, timeline, _now_iso(), candidate_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 5: Run the tests**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_candidate_intent.py tests/tracker/test_candidates.py tests/tracker/test_models.py -v`
Expected: the new tests pass; the existing `test_candidates.py` / `test_models.py` still pass (the dataclass change is additive with defaults; `create_candidate`'s new parameter is optional).

- [ ] **Step 6: Commit**

```bash
git add scripts/tracker/models.py scripts/tracker/candidates.py tests/tracker/test_candidate_intent.py
git commit -m "feat(tracker): candidate email + career-intent CRUD"
```

---

## Task 3: The onboarding surface

**Files:**
- Create: `scripts/dashboard/widgets/onboarding.py`
- Test: `tests/dashboard/widgets/test_onboarding.py`

- [ ] **Step 1: Write the failing test**

Create `tests/dashboard/widgets/test_onboarding.py`:

```python
"""Tests for the onboarding surface helpers."""
import pytest

from scripts.tracker.candidates import (
    create_candidate, get_candidate, update_candidate_intent,
)
from scripts.tracker.add import add_resume_version
from scripts.tracker.candidates import set_active_candidate
from scripts.dashboard.widgets.onboarding import (
    onboarding_needed, resume_context, render_onboarding,
    CAREER_STAGES, DIRECTIONS, TIMELINES,
)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_onboarding_needed_true_before_intent(isolated):
    cid = create_candidate("A", "B", [], None, None)
    assert onboarding_needed(get_candidate(cid)) is True


def test_onboarding_needed_false_after_intent(isolated):
    cid = create_candidate("A", "B", [], None, None)
    update_candidate_intent(cid, career_stage="mid")
    assert onboarding_needed(get_candidate(cid)) is False


def test_resume_context_no_resume(isolated):
    cid = create_candidate("A", "B", [], None, None)
    ctx = resume_context(cid)
    assert ctx["has_resume"] is False
    assert ctx["count"] == 0


def test_resume_context_with_resume(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    add_resume_version(None, "hybrid", [])
    ctx = resume_context(cid)
    assert ctx["has_resume"] is True
    assert ctx["count"] == 1
    assert ctx["latest_template"] == "hybrid"


def test_constants_are_nonempty_tuples():
    for const in (CAREER_STAGES, DIRECTIONS, TIMELINES):
        assert isinstance(const, tuple)
        assert len(const) > 0


def test_render_onboarding_is_callable():
    assert callable(render_onboarding)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_onboarding.py -v`
Expected: FAIL — `scripts.dashboard.widgets.onboarding` does not exist.

- [ ] **Step 3: Write the onboarding surface**

Create `scripts/dashboard/widgets/onboarding.py`:

```python
"""The resume-first onboarding surface.

Rendered on the Home tab whenever the active candidate's intent has not
been collected. Shows resume context and a short clarifying form; on submit
it writes the career-intent fields (which stamps intent_collected_at), and
the surface stops appearing.
"""
import streamlit as st

from scripts.tracker.candidates import update_candidate_intent
from scripts.tracker.db import open_db


CAREER_STAGES = (
    "student", "first_job", "early", "mid", "senior", "executive",
    "returning", "career_changer",
)
DIRECTIONS = ("grow", "leadership", "pivot", "first_role", "re_enter")
LEADERSHIP_INTENT = ("yes", "no", "maybe")
TIMELINES = ("actively_applying", "exploring", "passive")
WORK_PREFERENCES = (
    "remote", "hybrid", "onsite", "full_time", "part_time", "casual",
)


def onboarding_needed(candidate) -> bool:
    """True when the candidate has not completed the intent form yet."""
    return candidate.intent_collected_at is None


def resume_context(candidate_id: int) -> dict:
    """Return {has_resume, count, latest_template, latest_created_at} for the
    candidate's non-archived resumes — the 'resume-informed' context."""
    conn = open_db()
    try:
        rows = conn.execute(
            "SELECT template, created_at FROM resume_versions "
            "WHERE candidate_id=? AND archived_at IS NULL "
            "ORDER BY created_at DESC",
            (candidate_id,),
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        return {"has_resume": False, "count": 0,
                "latest_template": None, "latest_created_at": None}
    return {
        "has_resume": True,
        "count": len(rows),
        "latest_template": rows[0][0],
        "latest_created_at": rows[0][1],
    }


def render_onboarding(candidate) -> None:
    """Render the onboarding surface for a candidate whose intent is unset."""
    with st.container(border=True):
        st.markdown(f"### Finish setting up {candidate.first_name}'s profile")
        ctx = resume_context(candidate.id)
        if ctx["has_resume"]:
            st.caption(
                f"Resume on file: {ctx['count']} version(s), latest is a "
                f"'{ctx['latest_template']}' template. Answer a few questions "
                "below so playbooks and JD matching are tailored."
            )
        else:
            st.caption(
                "No resume on file yet — start the **Build a base resume** "
                "playbook above, or load one via the Resumes tab. You can "
                "also answer these questions now."
            )

        career_stage = st.selectbox(
            "Career stage", CAREER_STAGES, key="ob_career_stage")
        direction = st.selectbox(
            "Direction", DIRECTIONS, key="ob_direction")
        target_roles_raw = st.text_input(
            "Target roles (comma-separated)", key="ob_target_roles")
        target_industries_raw = st.text_input(
            "Target industries (comma-separated)", key="ob_target_industries")
        leadership_intent = st.radio(
            "Seeking a leadership / people-management role?",
            LEADERSHIP_INTENT, horizontal=True, key="ob_leadership")
        work_preferences = st.multiselect(
            "Work preferences", WORK_PREFERENCES, key="ob_work_prefs")
        location = st.text_input("Location", key="ob_location")
        relocation_open = st.checkbox(
            "Open to relocating", key="ob_relocation")
        role_priorities = st.text_area(
            "What matters to you in a role? (optional)", key="ob_priorities")
        timeline = st.selectbox(
            "Timeline", TIMELINES, key="ob_timeline")

        if st.button("Save & finish setup", key="ob_save"):
            update_candidate_intent(
                candidate.id,
                career_stage=career_stage,
                direction=direction,
                target_roles=[r.strip() for r in target_roles_raw.split(",")
                              if r.strip()],
                target_industries=[r.strip() for r in
                                   target_industries_raw.split(",")
                                   if r.strip()],
                leadership_intent=leadership_intent,
                work_preferences=work_preferences,
                location=location or None,
                relocation_open=1 if relocation_open else 0,
                role_priorities=role_priorities or None,
                timeline=timeline,
            )
            st.success("Profile complete. The dashboard is yours.")
            st.rerun()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_onboarding.py -v`
Expected: PASS — all 6 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/widgets/onboarding.py tests/dashboard/widgets/test_onboarding.py
git commit -m "feat(dashboard): resume-first onboarding surface"
```

---

## Task 4: Trim the new-candidate form to name + email

**Files:**
- Modify: `scripts/dashboard/sidebar.py`
- Test: (existing dashboard tests; see Step 3)

- [ ] **Step 1: Replace `_render_new_candidate_expander`**

In `scripts/dashboard/sidebar.py`, replace the entire `_render_new_candidate_expander` function with:

```python
def _render_new_candidate_expander() -> None:
    """Render the '+ New candidate' expander — name + email only.

    Career-intent fields are gathered later by the Home-tab onboarding
    surface; focus areas / pacing rate / notes are set via 'Edit selected'.
    """
    with st.expander("+ New candidate"):
        new_first = st.text_input("First name", key="new_first")
        new_last = st.text_input("Last name", key="new_last")
        new_email = st.text_input("Email", key="new_email")
        if st.button("Create candidate", key="new_candidate_create"):
            cid = create_candidate(
                first_name=new_first,
                last_name=new_last,
                focus_areas=[],
                healthy_weekly_rate=None,
                pacing_notes=None,
                email=new_email or None,
            )
            set_active_candidate(cid)
            clear_all_caches()
            st.rerun()
```

- [ ] **Step 2: Add email to the Edit-candidate expander**

In `scripts/dashboard/sidebar.py`, inside `_render_edit_candidate_expander`, add an email field. Immediately after the `edit_last = st.text_input(...)` block, insert:

```python
        edit_email = st.text_input(
            "Email", value=active.email or "", key="edit_email"
        )
```

And in the same function, change the `update_candidate(...)` call so it also passes `email=edit_email or None` — add that argument to the existing call's keyword arguments.

- [ ] **Step 3: Run the dashboard test suite and fix stale assertions**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard -q`

Inspect every failure. The likely category: a sidebar test (e.g. `tests/dashboard/test_sidebar_candidate_picker.py` or `tests/dashboard/test_name_modal_smoke.py`) that asserts on the now-removed "Focus areas" / "Healthy weekly rate" / "Pacing notes" inputs in the **new-candidate** expander. For each such failure, update the assertion to reflect the trimmed name+email form (the focus/rate/notes inputs still exist in the **Edit** expander — do not change those). If a test purely asserted removed widgets and has no meaningful replacement, update it to assert the new-candidate form has the First name / Last name / Email inputs.

Apply the minimal fix per failure. Do not change `create_candidate`'s behaviour.

- [ ] **Step 4: Confirm the dashboard suite is green**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard -q`
Expected: green.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/sidebar.py tests/dashboard
git commit -m "feat(dashboard): new-candidate form collects name + email only"
```

---

## Task 5: Wire the onboarding surface into the Home tab

**Files:**
- Modify: `scripts/dashboard/tabs/home.py`
- Test: `tests/dashboard/tabs/test_home_onboarding.py`

- [ ] **Step 1: Write the failing test**

Create `tests/dashboard/tabs/test_home_onboarding.py`:

```python
"""Tests for the Home tab's onboarding gate."""
from pathlib import Path

import pytest

APP_PATH = str(Path("scripts/dashboard/app.py").resolve())


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    from scripts.dashboard.data import clear_all_caches
    clear_all_caches()
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_home_module_references_onboarding(isolated):
    """home.py must wire in the onboarding surface."""
    src = Path("scripts/dashboard/tabs/home.py").read_text(encoding="utf-8")
    assert "onboarding" in src


def test_app_loads_with_uncollected_intent_candidate(isolated):
    """A candidate whose intent is unset must not break the Home render."""
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    assert not at.exception, f"App raised: {at.exception}"


def test_app_loads_with_collected_intent_candidate(isolated):
    from scripts.tracker.candidates import (
        create_candidate, set_active_candidate, update_candidate_intent,
    )
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    update_candidate_intent(cid, career_stage="mid")
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    assert not at.exception, f"App raised: {at.exception}"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/tabs/test_home_onboarding.py -v`
Expected: FAIL — `test_home_module_references_onboarding` fails (home.py has no onboarding wiring yet).

- [ ] **Step 3: Wire onboarding into `home.py`**

Replace the entire content of `scripts/dashboard/tabs/home.py` with:

```python
"""The Home tab — the customizable widget canvas.

When the active candidate has not completed onboarding, the resume-first
onboarding surface is rendered above the canvas. Otherwise the canvas
renders normally: all 'upper'-zone widgets, then all 'lower'-zone widgets.
A Customize expander edits the layout.
"""
import streamlit as st

from scripts.tracker.candidates import get_active_candidate
from scripts.dashboard.widgets.catalog import resolve_layout
from scripts.dashboard.widgets.layout import get_saved_layout
from scripts.dashboard.widgets.customize import render_customize
from scripts.dashboard.widgets.onboarding import onboarding_needed, render_onboarding


def effective_layout(candidate_id: int):
    """Return the resolved layout for a candidate — list of (Widget, enabled)."""
    return resolve_layout(get_saved_layout(candidate_id))


def render() -> None:
    """Render the Home tab."""
    active = get_active_candidate()
    if active is None:
        st.info("No active candidate. Select or create one in the sidebar.")
        return

    if onboarding_needed(active):
        render_onboarding(active)
        st.markdown("---")

    with st.expander("⚙ Customize"):
        render_customize(active)

    layout = effective_layout(active.id)
    upper = [w for w, en in layout if en and w.zone == "upper"]
    lower = [w for w, en in layout if en and w.zone == "lower"]

    for widget in upper:
        widget.render(active)
    if upper and lower:
        st.markdown("---")
    for widget in lower:
        widget.render(active)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/tabs/test_home_onboarding.py tests/dashboard/tabs/test_home_tab.py -v`
Expected: PASS — the new onboarding tests and the existing Home tab tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/tabs/home.py tests/dashboard/tabs/test_home_onboarding.py
git commit -m "feat(dashboard): Home tab renders the onboarding surface until intent is collected"
```

---

## Task 6: Version bump, CHANGELOG, full-suite green

**Files:**
- Modify: `scripts/outputs/io.py` (`_SKILL_VERSION`), `pyproject.toml`, `CHANGELOG.md`

- [ ] **Step 1: Run the full suite**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest -q`
Expected: all green. Investigate and fix any failure — Phase 3 is additive (a migration, additive dataclass fields, a new widget module, a trimmed form). The only existing tests that should need touching are stale sidebar assertions handled in Task 4. If something else fails, investigate before proceeding.

- [ ] **Step 2: Bump the version**

In `scripts/outputs/io.py`, change `_SKILL_VERSION = "2.1.0"` to `_SKILL_VERSION = "2.2.0"`.
In `pyproject.toml`, change the `version` field to `"2.2.0"`.
Read both files first to confirm the exact current text.

- [ ] **Step 3: Update CHANGELOG**

Add at the top of `CHANGELOG.md` (below the title, above the `## v2.1.0` entry), matching the existing heading style:

```markdown
## v2.2.0 — 2026-05-20

### Added
- **Resume-first onboarding** — creating a candidate now collects only name + email. A Home-tab onboarding surface gathers career intent (career stage, direction, target roles/industries, leadership intent, work preferences, location, timeline) once, then disappears.
- `candidates` table gains an `email` column and eleven career-intent columns (migration 0007).

### Changed
- The sidebar "+ New candidate" form is trimmed to name + email. Focus areas, pacing rate, and pacing notes are set via "Edit selected"; career intent via the onboarding surface.
```

Match the existing CHANGELOG date format if it differs from `2026-05-20`.

- [ ] **Step 4: Run the full suite once more**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest -q`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add scripts/outputs/io.py pyproject.toml CHANGELOG.md
git commit -m "chore: bump to v2.2.0 — resume-first onboarding"
```

---

## Acceptance Criteria

A. `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest -q` is green across the whole suite.

B. Migration 0007 adds `email` + eleven career-intent columns to `candidates`; version 7 is recorded; existing candidates remain valid with the new columns null.

C. Creating a candidate via the sidebar collects only First name / Last name / Email.

D. When the active candidate's `intent_collected_at` is null, the Home tab shows the onboarding surface above the canvas; submitting the clarifying form writes the intent fields, stamps `intent_collected_at`, and the surface no longer appears.

E. `resume_context` reports whether the candidate has a resume on file, surfaced in the onboarding copy.

---

## Out of Scope

- Re-editing career intent after `intent_collected_at` is set (the onboarding surface is one-shot; name/email/focus/rate/notes remain editable via "Edit selected").
- Auto-guessing enum values from resume text (deliberate — see Design decisions).
- The "what next after every playbook step" general pattern from spec §5 — the onboarding surface's own completion ("Profile complete") is the Phase-3 scope; a per-step "what next" is a possible future enhancement.

---

## Self-Review

**Spec coverage (§5, §7.2):** §7.2 intent columns + the §5 `email` requirement → migration 0007 (Task 1). §5 "creation collects only name + email" → Task 4. §5 onboarding surface + clarifying form → Task 3, wired in Task 5. §5 "resume-informed" → `resume_context` (Task 3). The intent fields' persistence → `update_candidate_intent` (Task 2). The one-shot gate (`intent_collected_at`) → Task 3's `onboarding_needed` + Task 5's wiring. Spec §5's narrative "after a review" is implemented as a state gate — documented under Design decisions. No §5/§7.2 requirement is unaddressed.

**Placeholder scan:** No "TBD"/"add validation"/"similar to Task N". Every code step is complete and literal. Task 4 Step 3 ("fix stale assertions") is a genuine investigation step with a concrete category and instruction, not a placeholder.

**Type consistency:** The `Candidate` dataclass field names (`email`, `career_stage`, `direction`, `target_roles`, `target_industries`, `leadership_intent`, `work_preferences`, `location`, `relocation_open`, `role_priorities`, `timeline`, `intent_collected_at`) are identical across `models.py`, the migration 0007 columns, `_CANDIDATE_COLS`, `_row_to_candidate`, `update_candidate_intent`'s parameters, and the onboarding form's `update_candidate_intent(...)` call. `create_candidate`'s new `email` parameter is trailing-optional and used consistently in `sidebar.py`. `onboarding_needed` / `resume_context` / `render_onboarding` are named identically at definition and call sites.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-20-dashboard-orchestration-phase-3.md`. Two execution options:

1. **Subagent-Driven (recommended)** — a fresh subagent per task, two-stage review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session with checkpoints.

Which approach?
