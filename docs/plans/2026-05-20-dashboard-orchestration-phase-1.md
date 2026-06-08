# Dashboard Orchestration — Phase 1 (Engine + Data) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the playbook engine and its persistence — migration 0006, five playbook definitions, completion predicates, the `playbook_runs` CRUD, and the runner — with no UI.

**Architecture:** A new pure-Python `scripts/playbooks/` package. Playbook *definitions* are hardcoded dataclasses; playbook *progress* is rows in a new `playbook_runs` table. A runner evaluates a run's current step against a completion predicate (a read query on the existing tracker DB) and auto-advances. Migration 0006 also creates the `dashboard_layout` table, which Phase 2 will use.

**Tech Stack:** Python 3.14, SQLite (the existing tracker DB), pytest. No Streamlit, no LLM, no new dependencies.

**Reference:** `docs/specs/2026-05-20-dashboard-orchestration-design.md` (§4 playbook engine, §7.1 data model).

---

## File Structure

| File | Responsibility |
|------|----------------|
| `scripts/tracker/migrations/0006_dashboard_orchestration.py` | Schema migration: `dashboard_layout` + `playbook_runs` tables. |
| `scripts/playbooks/__init__.py` | Package marker. |
| `scripts/playbooks/models.py` | Dataclasses: `PlaybookStep`, `Playbook`, `PlaybookRun`. |
| `scripts/playbooks/predicates.py` | Completion-predicate functions `(conn, run) -> bool`. |
| `scripts/playbooks/definitions.py` | The five hardcoded playbooks + `get_playbook` / `all_playbooks`. |
| `scripts/playbooks/runs.py` | CRUD for the `playbook_runs` table. |
| `scripts/playbooks/runner.py` | `evaluate_run` — the auto-advance logic. |

Tests mirror the source under `tests/playbooks/` and `tests/tracker/migrations/`.

**Dependency order:** `models` ← `predicates` ← `definitions`; `models` ← `runs`; `definitions` + `runs` ← `runner`. Tasks below follow this order.

The venv interpreter is `c:\Brains_Resume_Skill\.venv\Scripts\python.exe`. Run all commands from `c:\Brains_Resume_Skill`.

---

## Task 1: Migration 0006 — `dashboard_layout` + `playbook_runs` tables

**Files:**
- Create: `scripts/tracker/migrations/0006_dashboard_orchestration.py`
- Test: `tests/tracker/migrations/test_0006_dashboard_orchestration.py`

- [ ] **Step 1: Write the failing test**

Create `tests/tracker/migrations/test_0006_dashboard_orchestration.py`:

```python
"""Tests for migration 0006 — dashboard_layout + playbook_runs tables."""
import pytest

from scripts.tracker.db import open_db


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_dashboard_layout_table_exists(isolated_db):
    conn = open_db()
    try:
        names = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "dashboard_layout" in names
    finally:
        conn.close()


def test_dashboard_layout_columns(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute(
            "PRAGMA table_info(dashboard_layout)")}
        assert {"id", "candidate_id", "widget_key", "position",
                "enabled", "created_at"} <= cols
    finally:
        conn.close()


def test_dashboard_layout_unique_constraint(isolated_db):
    """(candidate_id, widget_key) must be unique."""
    import sqlite3
    conn = open_db()
    try:
        conn.execute(
            "INSERT INTO candidates (first_name, last_name, created_at) "
            "VALUES ('A', 'B', '2026-01-01T00:00:00Z')")
        cid = conn.execute("SELECT id FROM candidates").fetchone()[0]
        conn.execute(
            "INSERT INTO dashboard_layout "
            "(candidate_id, widget_key, position, enabled, created_at) "
            "VALUES (?, 'worklist', 0, 1, '2026-01-01T00:00:00Z')", (cid,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO dashboard_layout "
                "(candidate_id, widget_key, position, enabled, created_at) "
                "VALUES (?, 'worklist', 1, 1, '2026-01-01T00:00:00Z')", (cid,))
    finally:
        conn.close()


def test_playbook_runs_table_exists(isolated_db):
    conn = open_db()
    try:
        names = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "playbook_runs" in names
    finally:
        conn.close()


def test_playbook_runs_columns(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute(
            "PRAGMA table_info(playbook_runs)")}
        assert {"id", "candidate_id", "playbook_key", "jd_id",
                "current_step", "status", "created_at", "updated_at",
                "completed_at"} <= cols
    finally:
        conn.close()


def test_playbook_runs_index_exists(isolated_db):
    conn = open_db()
    try:
        names = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'")}
        assert "idx_playbook_runs_candidate_status" in names
    finally:
        conn.close()


def test_migration_recorded(isolated_db):
    conn = open_db()
    try:
        versions = [row[0] for row in conn.execute(
            "SELECT version FROM migrations ORDER BY version")]
        assert 6 in versions
    finally:
        conn.close()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/migrations/test_0006_dashboard_orchestration.py -v`
Expected: FAIL — the `dashboard_layout` / `playbook_runs` tables do not exist; `6` is not in `migrations`.

- [ ] **Step 3: Write the migration**

Create `scripts/tracker/migrations/0006_dashboard_orchestration.py`:

```python
"""Migration 0006 — dashboard orchestration tables.

Schema-only, additive, no backfill. Creates two tables:

- dashboard_layout: per-candidate widget canvas (which widgets, in what
  order, enabled or not). Consumed by Phase 2 (the widget canvas).
- playbook_runs: one row per playbook run; tracks current_step and status.

See docs/specs/2026-05-20-dashboard-orchestration-design.md (Section 7.1).
"""
import sqlite3


SCHEMA_SQL = """
CREATE TABLE dashboard_layout (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    widget_key TEXT NOT NULL,
    position INTEGER NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE(candidate_id, widget_key)
);

CREATE TABLE playbook_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    playbook_key TEXT NOT NULL,
    jd_id INTEGER REFERENCES jds(id),
    current_step INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX idx_playbook_runs_candidate_status
  ON playbook_runs(candidate_id, status);
"""


def apply(conn: sqlite3.Connection) -> None:
    """Create the dashboard_layout and playbook_runs tables."""
    conn.executescript(SCHEMA_SQL)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/migrations/test_0006_dashboard_orchestration.py -v`
Expected: PASS — all 7 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/tracker/migrations/0006_dashboard_orchestration.py tests/tracker/migrations/test_0006_dashboard_orchestration.py
git commit -m "feat(tracker): migration 0006 — dashboard_layout + playbook_runs tables"
```

---

## Task 2: Playbook data model

**Files:**
- Create: `scripts/playbooks/__init__.py`
- Create: `scripts/playbooks/models.py`
- Test: `tests/playbooks/test_models.py`

- [ ] **Step 1: Write the failing test**

Create `tests/playbooks/test_models.py`:

```python
"""Tests for the playbook engine dataclasses."""
from scripts.playbooks.models import PlaybookStep, Playbook, PlaybookRun


def test_playbook_step_defaults():
    step = PlaybookStep(key="review", label="Review", kind="in_dashboard")
    assert step.command is None
    assert step.predicate is None


def test_playbook_step_with_handoff_fields():
    sentinel = lambda conn, run: True
    step = PlaybookStep(
        key="tailor_resume", label="Tailor", kind="handoff",
        command="tailor", predicate=sentinel,
    )
    assert step.kind == "handoff"
    assert step.command == "tailor"
    assert step.predicate is sentinel


def test_playbook_holds_ordered_steps():
    s1 = PlaybookStep(key="a", label="A", kind="in_dashboard")
    s2 = PlaybookStep(key="b", label="B", kind="handoff", command="edit")
    pb = Playbook(key="demo", label="Demo", steps=(s1, s2))
    assert pb.steps[0].key == "a"
    assert pb.steps[1].key == "b"
    assert len(pb.steps) == 2


def test_playbook_run_is_mutable_with_full_fields():
    run = PlaybookRun(
        id=1, candidate_id=2, playbook_key="apply_to_job", jd_id=7,
        current_step=3, status="active",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z", completed_at=None,
    )
    run.current_step = 4
    assert run.current_step == 4
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/playbooks/test_models.py -v`
Expected: FAIL — `scripts.playbooks` does not exist.

- [ ] **Step 3: Create the package and model file**

Create `scripts/playbooks/__init__.py` (empty file):

```python
"""Playbook engine — guided multi-step journeys over the skill's functions."""
```

Create `scripts/playbooks/models.py`:

```python
"""Data types for the playbook engine.

PlaybookStep / Playbook are immutable definitions (hardcoded in
definitions.py). PlaybookRun is a mutable DTO mapping 1:1 to a
playbook_runs row.
"""
from dataclasses import dataclass
from typing import Callable, Optional, Tuple


# Valid values for PlaybookStep.kind.
STEP_KINDS = ("in_dashboard", "handoff")

# Valid values for PlaybookRun.status.
RUN_STATUSES = ("active", "completed", "abandoned")


@dataclass(frozen=True)
class PlaybookStep:
    """One step in a playbook.

    kind:
      - 'in_dashboard': the dashboard runs this itself (a pure-Python
        validator). Completion is synchronous; no predicate.
      - 'handoff': LLM work handed off to Claude Code.

    command:   for handoff steps, the brains command (e.g. 'tailor').
    predicate: a callable (conn, run) -> bool that returns True once the
               step's output exists. None means the step has no auto-detect
               signal and advances by manual override only.
    """
    key: str
    label: str
    kind: str
    command: Optional[str] = None
    predicate: Optional[Callable] = None


@dataclass(frozen=True)
class Playbook:
    """An ordered sequence of steps assembled from existing commands."""
    key: str
    label: str
    steps: Tuple[PlaybookStep, ...]


@dataclass
class PlaybookRun:
    """A single run of a playbook — maps 1:1 to a playbook_runs row."""
    id: Optional[int]
    candidate_id: int
    playbook_key: str
    jd_id: Optional[int]
    current_step: int
    status: str
    created_at: str
    updated_at: str
    completed_at: Optional[str]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/playbooks/test_models.py -v`
Expected: PASS — all 4 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/playbooks/__init__.py scripts/playbooks/models.py tests/playbooks/test_models.py
git commit -m "feat(playbooks): PlaybookStep / Playbook / PlaybookRun dataclasses"
```

---

## Task 3: Completion predicates

**Files:**
- Create: `scripts/playbooks/predicates.py`
- Test: `tests/playbooks/test_predicates.py`

Predicates are pure read queries on the tracker DB. Four are needed:
`resume_tagged_to_jd`, `cover_letter_for_jd`, `application_for_jd`,
`resume_created_after_run`.

- [ ] **Step 1: Write the failing test**

Create `tests/playbooks/test_predicates.py`:

```python
"""Tests for playbook completion predicates."""
from datetime import datetime

import pytest

from scripts.tracker.db import open_db
from scripts.tracker.add import (
    add_jd, add_resume_version, add_cover_letter, add_application,
)
from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.playbooks.models import PlaybookRun
from scripts.playbooks import predicates as P


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def _run(candidate_id, jd_id=None, created_at="2026-01-01T00:00:00Z"):
    return PlaybookRun(
        id=1, candidate_id=candidate_id, playbook_key="apply_to_job",
        jd_id=jd_id, current_step=0, status="active",
        created_at=created_at, updated_at=created_at, completed_at=None,
    )


def test_resume_tagged_to_jd_false_when_none(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    conn = open_db()
    try:
        assert P.resume_tagged_to_jd(conn, _run(cid, jd)) is False
    finally:
        conn.close()


def test_resume_tagged_to_jd_true_when_present(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    conn = open_db()
    try:
        assert P.resume_tagged_to_jd(conn, _run(cid, jd)) is True
    finally:
        conn.close()


def test_resume_tagged_to_jd_false_when_jd_id_none(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    conn = open_db()
    try:
        assert P.resume_tagged_to_jd(conn, _run(cid, None)) is False
    finally:
        conn.close()


def test_cover_letter_for_jd(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    rv = add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    conn = open_db()
    try:
        assert P.cover_letter_for_jd(conn, _run(cid, jd)) is False
    finally:
        conn.close()
    add_cover_letter(None, rv, jd, "standard")
    conn = open_db()
    try:
        assert P.cover_letter_for_jd(conn, _run(cid, jd)) is True
    finally:
        conn.close()


def test_application_for_jd(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    rv = add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    conn = open_db()
    try:
        assert P.application_for_jd(conn, _run(cid, jd)) is False
    finally:
        conn.close()
    add_application(jd, rv, None, datetime(2026, 2, 1), "direct")
    conn = open_db()
    try:
        assert P.application_for_jd(conn, _run(cid, jd)) is True
    finally:
        conn.close()


def test_resume_created_after_run(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    # A resume created BEFORE the run start time must not count.
    add_resume_version(None, "hybrid", [])
    future_run = _run(cid, created_at="2099-01-01T00:00:00Z")
    past_run = _run(cid, created_at="2000-01-01T00:00:00Z")
    conn = open_db()
    try:
        assert P.resume_created_after_run(conn, future_run) is False
        assert P.resume_created_after_run(conn, past_run) is True
    finally:
        conn.close()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/playbooks/test_predicates.py -v`
Expected: FAIL — `scripts.playbooks.predicates` does not exist.

- [ ] **Step 3: Write the predicates**

Create `scripts/playbooks/predicates.py`:

```python
"""Completion predicates for playbook handoff steps.

Each predicate is a pure read: (conn, run) -> bool. It returns True once the
step's output artifact exists in the tracker DB. The runner calls these to
decide whether to auto-advance a run.
"""
import sqlite3

from scripts.playbooks.models import PlaybookRun


def resume_tagged_to_jd(conn: sqlite3.Connection, run: PlaybookRun) -> bool:
    """True when a non-archived resume is tagged to the run's JD."""
    if run.jd_id is None:
        return False
    row = conn.execute(
        "SELECT 1 FROM resume_versions "
        "WHERE tagged_jd_id = ? AND archived_at IS NULL LIMIT 1",
        (run.jd_id,),
    ).fetchone()
    return row is not None


def cover_letter_for_jd(conn: sqlite3.Connection, run: PlaybookRun) -> bool:
    """True when a non-archived cover letter exists for the run's JD."""
    if run.jd_id is None:
        return False
    row = conn.execute(
        "SELECT 1 FROM cover_letters "
        "WHERE jd_id = ? AND archived_at IS NULL LIMIT 1",
        (run.jd_id,),
    ).fetchone()
    return row is not None


def application_for_jd(conn: sqlite3.Connection, run: PlaybookRun) -> bool:
    """True when an application has been registered for the run's JD."""
    if run.jd_id is None:
        return False
    row = conn.execute(
        "SELECT 1 FROM applications WHERE jd_id = ? LIMIT 1",
        (run.jd_id,),
    ).fetchone()
    return row is not None


def resume_created_after_run(conn: sqlite3.Connection, run: PlaybookRun) -> bool:
    """True when a non-archived resume for the candidate was created after
    the run started. Used by non-JD playbooks (e.g. build_resume) where the
    output is 'a new resume' rather than 'a resume tagged to a JD'."""
    row = conn.execute(
        "SELECT 1 FROM resume_versions "
        "WHERE candidate_id = ? AND archived_at IS NULL "
        "AND created_at > ? LIMIT 1",
        (run.candidate_id, run.created_at),
    ).fetchone()
    return row is not None
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/playbooks/test_predicates.py -v`
Expected: PASS — all 6 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/playbooks/predicates.py tests/playbooks/test_predicates.py
git commit -m "feat(playbooks): completion predicates for handoff steps"
```

---

## Task 4: The five playbook definitions

**Files:**
- Create: `scripts/playbooks/definitions.py`
- Test: `tests/playbooks/test_definitions.py`

- [ ] **Step 1: Write the failing test**

Create `tests/playbooks/test_definitions.py`:

```python
"""Tests for the five hardcoded playbook definitions."""
import pytest

from scripts.playbooks.definitions import all_playbooks, get_playbook
from scripts.playbooks.models import STEP_KINDS


def test_five_playbooks_defined():
    keys = {pb.key for pb in all_playbooks()}
    assert keys == {
        "apply_to_job", "build_resume", "improve_resume",
        "refresh_linkedin", "career_change",
    }


def test_get_playbook_returns_match():
    pb = get_playbook("apply_to_job")
    assert pb.label == "Apply to a job"
    assert len(pb.steps) == 6


def test_get_playbook_unknown_key_raises():
    with pytest.raises(KeyError):
        get_playbook("does_not_exist")


def test_every_step_has_a_valid_kind():
    for pb in all_playbooks():
        for step in pb.steps:
            assert step.kind in STEP_KINDS


def test_handoff_steps_have_a_command():
    for pb in all_playbooks():
        for step in pb.steps:
            if step.kind == "handoff":
                assert step.command, f"{pb.key}/{step.key} missing command"


def test_in_dashboard_steps_have_no_predicate():
    """in_dashboard steps complete synchronously; they never carry a predicate."""
    for pb in all_playbooks():
        for step in pb.steps:
            if step.kind == "in_dashboard":
                assert step.predicate is None


def test_apply_to_job_step_keys_in_order():
    pb = get_playbook("apply_to_job")
    assert [s.key for s in pb.steps] == [
        "analyze_jd", "tailor_resume", "cover_letter",
        "final_check", "precheck", "submit_track",
    ]


def test_step_keys_unique_within_each_playbook():
    for pb in all_playbooks():
        keys = [s.key for s in pb.steps]
        assert len(keys) == len(set(keys)), f"duplicate step key in {pb.key}"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/playbooks/test_definitions.py -v`
Expected: FAIL — `scripts.playbooks.definitions` does not exist.

- [ ] **Step 3: Write the definitions**

Create `scripts/playbooks/definitions.py`:

```python
"""The five hardcoded playbook definitions.

A playbook is an ordered list of steps assembled from existing brains
commands. Definitions are immutable; runtime progress lives in playbook_runs.

Step completion:
  - 'in_dashboard' steps run in the dashboard and complete synchronously
    (no predicate).
  - 'handoff' steps with a predicate auto-advance when the predicate passes.
  - 'handoff' steps without a predicate (e.g. a coaching conversation that
    leaves no artifact) advance by manual override only.
"""
from scripts.playbooks.models import Playbook, PlaybookStep
from scripts.playbooks import predicates as P


APPLY_TO_JOB = Playbook(
    key="apply_to_job",
    label="Apply to a job",
    steps=(
        PlaybookStep("analyze_jd", "Analyze the JD", "in_dashboard"),
        PlaybookStep("tailor_resume", "Tailor the resume", "handoff",
                     command="tailor", predicate=P.resume_tagged_to_jd),
        PlaybookStep("cover_letter", "Write the cover letter", "handoff",
                     command="cover-letter", predicate=P.cover_letter_for_jd),
        PlaybookStep("final_check", "Final pre-submit check", "in_dashboard"),
        PlaybookStep("precheck", "Pre-application coaching", "handoff",
                     command="precheck"),
        PlaybookStep("submit_track", "Submit & track", "handoff",
                     command="track", predicate=P.application_for_jd),
    ),
)

BUILD_RESUME = Playbook(
    key="build_resume",
    label="Build a base resume",
    steps=(
        PlaybookStep("create", "Interview & build", "handoff",
                     command="create", predicate=P.resume_created_after_run),
        PlaybookStep("review", "Review", "in_dashboard"),
        PlaybookStep("edit", "Apply edits", "handoff", command="edit"),
        PlaybookStep("final_check", "Final check", "in_dashboard"),
    ),
)

IMPROVE_RESUME = Playbook(
    key="improve_resume",
    label="Improve a resume",
    steps=(
        PlaybookStep("review", "Review", "in_dashboard"),
        PlaybookStep("edit", "Apply edits", "handoff", command="edit"),
        PlaybookStep("final_check", "Final check / de-AI", "in_dashboard"),
    ),
)

REFRESH_LINKEDIN = Playbook(
    key="refresh_linkedin",
    label="Refresh LinkedIn",
    steps=(
        PlaybookStep("ingest", "Ingest LinkedIn export", "handoff",
                     command="linkedin"),
        PlaybookStep("consolidate", "Consolidate vs resume", "handoff",
                     command="consolidate"),
        PlaybookStep("rewrite", "Rewrite the profile", "handoff",
                     command="linkedin-improve"),
    ),
)

CAREER_CHANGE = Playbook(
    key="career_change",
    label="Career change",
    steps=(
        PlaybookStep("translate", "Translate experience", "handoff",
                     command="career-change"),
    ),
)

ALL_PLAYBOOKS = (
    APPLY_TO_JOB, BUILD_RESUME, IMPROVE_RESUME, REFRESH_LINKEDIN, CAREER_CHANGE,
)

_BY_KEY = {pb.key: pb for pb in ALL_PLAYBOOKS}


def all_playbooks():
    """Return all five playbooks in display order."""
    return ALL_PLAYBOOKS


def get_playbook(key: str) -> Playbook:
    """Return the playbook with the given key. Raises KeyError if unknown."""
    if key not in _BY_KEY:
        raise KeyError(f"Unknown playbook: {key!r}")
    return _BY_KEY[key]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/playbooks/test_definitions.py -v`
Expected: PASS — all 8 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/playbooks/definitions.py tests/playbooks/test_definitions.py
git commit -m "feat(playbooks): the five playbook definitions"
```

---

## Task 5: `playbook_runs` CRUD

**Files:**
- Create: `scripts/playbooks/runs.py`
- Test: `tests/playbooks/test_runs.py`

- [ ] **Step 1: Write the failing test**

Create `tests/playbooks/test_runs.py`:

```python
"""Tests for playbook_runs CRUD."""
import pytest

from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.playbooks.runs import (
    start_run, get_run, list_active_runs, set_run_jd,
    set_run_step, advance_run, abandon_run,
)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_start_run_creates_active_run_at_step_zero(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    run_id = start_run(cid, "apply_to_job")
    run = get_run(run_id)
    assert run.candidate_id == cid
    assert run.playbook_key == "apply_to_job"
    assert run.current_step == 0
    assert run.status == "active"
    assert run.completed_at is None


def test_start_run_rejects_unknown_playbook(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    with pytest.raises(KeyError):
        start_run(cid, "not_a_playbook")


def test_get_run_returns_none_for_missing(isolated):
    create_candidate("A", "B", [], None, None)
    assert get_run(999) is None


def test_list_active_runs_excludes_completed_and_abandoned(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    active = start_run(cid, "apply_to_job")
    done = start_run(cid, "improve_resume")
    gone = start_run(cid, "career_change")
    abandon_run(gone)
    # Drive `done` to completion via set_run_step past the last step.
    set_run_step(done, 99)
    ids = {r.id for r in list_active_runs(cid)}
    assert ids == {active}


def test_set_run_jd(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    run_id = start_run(cid, "apply_to_job")
    set_run_jd(run_id, 42)
    assert get_run(run_id).jd_id == 42


def test_advance_run_increments_step(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    run_id = start_run(cid, "apply_to_job")
    advance_run(run_id)
    assert get_run(run_id).current_step == 1


def test_advance_past_last_step_completes_the_run(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    # career_change has exactly one step.
    run_id = start_run(cid, "career_change")
    run = advance_run(run_id)
    assert run.status == "completed"
    assert run.completed_at is not None
    assert run.current_step == 1


def test_set_run_step_can_go_backwards(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    run_id = start_run(cid, "apply_to_job")
    set_run_step(run_id, 3)
    assert get_run(run_id).current_step == 3
    set_run_step(run_id, 1)
    run = get_run(run_id)
    assert run.current_step == 1
    assert run.status == "active"


def test_set_run_step_clamps_negative_to_zero(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    run_id = start_run(cid, "apply_to_job")
    set_run_step(run_id, -5)
    assert get_run(run_id).current_step == 0


def test_abandon_run(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    run_id = start_run(cid, "apply_to_job")
    abandon_run(run_id)
    assert get_run(run_id).status == "abandoned"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/playbooks/test_runs.py -v`
Expected: FAIL — `scripts.playbooks.runs` does not exist.

- [ ] **Step 3: Write the CRUD module**

Create `scripts/playbooks/runs.py`:

```python
"""CRUD for the playbook_runs table.

Each function opens a fresh DB connection, mirroring scripts/tracker/add.py
and scripts/tracker/candidates.py. set_run_step is the single source of
truth for current_step + status; advance_run delegates to it.
"""
from datetime import datetime
from typing import List, Optional

from scripts.tracker.db import open_db
from scripts.playbooks.definitions import get_playbook
from scripts.playbooks.models import PlaybookRun


_COLS = ("id, candidate_id, playbook_key, jd_id, current_step, status, "
         "created_at, updated_at, completed_at")


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _row_to_run(row) -> PlaybookRun:
    return PlaybookRun(
        id=row[0], candidate_id=row[1], playbook_key=row[2], jd_id=row[3],
        current_step=row[4], status=row[5], created_at=row[6],
        updated_at=row[7], completed_at=row[8],
    )


def start_run(candidate_id: int, playbook_key: str,
              jd_id: Optional[int] = None) -> int:
    """Insert a new active run at step 0. Validates playbook_key (raises
    KeyError if unknown). Returns the new run id."""
    get_playbook(playbook_key)  # raises KeyError on an unknown key
    now = _now_iso()
    conn = open_db()
    try:
        cur = conn.execute(
            "INSERT INTO playbook_runs "
            "(candidate_id, playbook_key, jd_id, current_step, status, "
            " created_at, updated_at) "
            "VALUES (?, ?, ?, 0, 'active', ?, ?)",
            (candidate_id, playbook_key, jd_id, now, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_run(run_id: int) -> Optional[PlaybookRun]:
    """Return the run, or None if no row has that id."""
    conn = open_db()
    try:
        row = conn.execute(
            f"SELECT {_COLS} FROM playbook_runs WHERE id=?", (run_id,)
        ).fetchone()
    finally:
        conn.close()
    return _row_to_run(row) if row else None


def list_active_runs(candidate_id: int) -> List[PlaybookRun]:
    """Return the candidate's active runs, oldest first."""
    conn = open_db()
    try:
        rows = conn.execute(
            f"SELECT {_COLS} FROM playbook_runs "
            "WHERE candidate_id=? AND status='active' "
            "ORDER BY created_at ASC",
            (candidate_id,),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_run(r) for r in rows]


def set_run_jd(run_id: int, jd_id: int) -> None:
    """Attach a JD to the run (called when the analyze-JD step produces one)."""
    conn = open_db()
    try:
        conn.execute(
            "UPDATE playbook_runs SET jd_id=?, updated_at=? WHERE id=?",
            (jd_id, _now_iso(), run_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_run_step(run_id: int, step: int) -> Optional[PlaybookRun]:
    """Set current_step directly — the manual override. Negative values
    clamp to 0. A step at or past the last step marks the run completed
    (current_step pinned to the step count); otherwise the run is active.
    Returns the updated run, or None if the run does not exist."""
    run = get_run(run_id)
    if run is None:
        return None
    n_steps = len(get_playbook(run.playbook_key).steps)
    step = max(0, step)
    now = _now_iso()
    if step >= n_steps:
        current, status, completed_at = n_steps, "completed", now
    else:
        current, status, completed_at = step, "active", None
    conn = open_db()
    try:
        conn.execute(
            "UPDATE playbook_runs SET current_step=?, status=?, "
            "completed_at=?, updated_at=? WHERE id=?",
            (current, status, completed_at, now, run_id),
        )
        conn.commit()
    finally:
        conn.close()
    return get_run(run_id)


def advance_run(run_id: int) -> Optional[PlaybookRun]:
    """Advance the run by one step. Completes it when it moves past the last
    step. Returns the updated run, or None if the run does not exist."""
    run = get_run(run_id)
    if run is None:
        return None
    return set_run_step(run_id, run.current_step + 1)


def abandon_run(run_id: int) -> None:
    """Mark the run abandoned — drops it out of list_active_runs."""
    conn = open_db()
    try:
        conn.execute(
            "UPDATE playbook_runs SET status='abandoned', updated_at=? "
            "WHERE id=?",
            (_now_iso(), run_id),
        )
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/playbooks/test_runs.py -v`
Expected: PASS — all 10 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/playbooks/runs.py tests/playbooks/test_runs.py
git commit -m "feat(playbooks): playbook_runs CRUD"
```

---

## Task 6: The runner

**Files:**
- Create: `scripts/playbooks/runner.py`
- Test: `tests/playbooks/test_runner.py`

- [ ] **Step 1: Write the failing test**

Create `tests/playbooks/test_runner.py`:

```python
"""Tests for the playbook runner (evaluate_run auto-advance)."""
import pytest

from scripts.tracker.add import add_jd, add_resume_version, add_cover_letter
from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.playbooks.runs import start_run, get_run, set_run_jd, set_run_step
from scripts.playbooks.runner import evaluate_run


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_evaluate_holds_on_in_dashboard_step(isolated):
    """Step 0 of apply_to_job is in_dashboard (no predicate) — evaluate_run
    must not advance it."""
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    run_id = start_run(cid, "apply_to_job")
    run = evaluate_run(run_id)
    assert run.current_step == 0


def test_evaluate_holds_when_predicate_unsatisfied(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    run_id = start_run(cid, "apply_to_job", jd_id=jd)
    set_run_step(run_id, 1)  # move onto tailor_resume (has a predicate)
    run = evaluate_run(run_id)
    assert run.current_step == 1  # no resume yet


def test_evaluate_advances_when_predicate_satisfied(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    run_id = start_run(cid, "apply_to_job", jd_id=jd)
    set_run_step(run_id, 1)  # tailor_resume
    add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    run = evaluate_run(run_id)
    assert run.current_step == 2  # advanced onto cover_letter


def test_evaluate_advances_through_multiple_satisfied_steps(isolated):
    """If both the resume and cover letter exist, evaluate_run advances
    through tailor_resume AND cover_letter, then stops at final_check
    (in_dashboard, no predicate)."""
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    rv = add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    add_cover_letter(None, rv, jd, "standard")
    run_id = start_run(cid, "apply_to_job", jd_id=jd)
    set_run_step(run_id, 1)  # tailor_resume
    run = evaluate_run(run_id)
    assert run.current_step == 3  # stopped at final_check


def test_evaluate_is_noop_on_completed_run(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    run_id = start_run(cid, "career_change")
    set_run_step(run_id, 99)  # complete it
    run = evaluate_run(run_id)
    assert run.status == "completed"


def test_evaluate_returns_none_for_missing_run(isolated):
    create_candidate("A", "B", [], None, None)
    assert evaluate_run(999) is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/playbooks/test_runner.py -v`
Expected: FAIL — `scripts.playbooks.runner` does not exist.

- [ ] **Step 3: Write the runner**

Create `scripts/playbooks/runner.py`:

```python
"""The playbook runner.

evaluate_run inspects a run's current step. If the step carries a completion
predicate and the predicate passes, the run advances — looping so that
several handoff steps completed between two dashboard renders all settle in
one call. It stops at the first step that is in_dashboard, manual-only, or
not yet complete. The manual override (runs.set_run_step) is always
available regardless.
"""
import sqlite3
from typing import Optional

from scripts.tracker.db import open_db
from scripts.playbooks.definitions import get_playbook
from scripts.playbooks.models import PlaybookRun
from scripts.playbooks.runs import get_run, advance_run


def evaluate_run(run_id: int) -> Optional[PlaybookRun]:
    """Auto-advance a run as far as its completion predicates allow.

    Returns the (possibly advanced) run, or None if the run does not exist.
    A predicate that raises sqlite3.Error is treated as 'not complete' so a
    bad predicate never crashes the caller.
    """
    run = get_run(run_id)
    if run is None or run.status != "active":
        return run

    while run.status == "active":
        playbook = get_playbook(run.playbook_key)
        if run.current_step >= len(playbook.steps):
            break
        step = playbook.steps[run.current_step]
        if step.predicate is None:
            break  # in_dashboard or manual-only — stop auto-advancing
        conn = open_db()
        try:
            try:
                done = bool(step.predicate(conn, run))
            except sqlite3.Error:
                done = False
        finally:
            conn.close()
        if not done:
            break
        run = advance_run(run.id)

    return run
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/playbooks/test_runner.py -v`
Expected: PASS — all 6 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/playbooks/runner.py tests/playbooks/test_runner.py
git commit -m "feat(playbooks): the runner — predicate-driven auto-advance"
```

---

## Task 7: End-to-end integration test

**Files:**
- Test: `tests/playbooks/test_integration.py`

This task adds no new source — it proves the whole engine works together by
driving a full `apply_to_job` run from start to completion.

- [ ] **Step 1: Write the integration test**

Create `tests/playbooks/test_integration.py`:

```python
"""End-to-end: a full apply_to_job playbook run.

Simulates the dashboard: in_dashboard steps are advanced by hand (the
dashboard would run them itself); handoff steps auto-advance via evaluate_run
once their artifact lands in the tracker DB.
"""
from datetime import datetime

import pytest

from scripts.tracker.add import (
    add_jd, add_resume_version, add_cover_letter, add_application,
)
from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.playbooks.runs import (
    start_run, get_run, set_run_jd, set_run_step, advance_run,
)
from scripts.playbooks.runner import evaluate_run


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_full_apply_to_job_run(isolated):
    cid = create_candidate("Mathilda", "Gell", [], None, None)
    set_active_candidate(cid)

    # Start the run. Step 0 = analyze_jd (in_dashboard).
    run_id = start_run(cid, "apply_to_job")
    assert get_run(run_id).current_step == 0

    # Dashboard runs the JD analyzer -> a jd row, and records it on the run,
    # then advances past the in_dashboard step.
    jd = add_jd("manual", None, "Big W", "Sales Assistant", "x", {}, [], [])
    set_run_jd(run_id, jd)
    advance_run(run_id)                       # -> step 1 tailor_resume
    assert evaluate_run(run_id).current_step == 1   # no resume yet

    # Handoff: tailoring produces a resume tagged to the JD.
    rv = add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    assert evaluate_run(run_id).current_step == 2   # -> cover_letter

    # Handoff: the cover letter lands.
    add_cover_letter(None, rv, jd, "standard")
    assert evaluate_run(run_id).current_step == 3   # -> final_check (in_dashboard)

    # Dashboard runs the final check, then advances.
    advance_run(run_id)                       # -> step 4 precheck
    assert evaluate_run(run_id).current_step == 4   # precheck has no predicate

    # precheck is a manual-only handoff step.
    advance_run(run_id)                       # -> step 5 submit_track
    assert evaluate_run(run_id).current_step == 5   # no application yet

    # Handoff: the application is registered -> the run completes.
    add_application(jd, rv, None, datetime(2026, 2, 1), "direct")
    final = evaluate_run(run_id)
    assert final.status == "completed"
    assert final.completed_at is not None
```

- [ ] **Step 2: Run the integration test**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/playbooks/test_integration.py -v`
Expected: PASS.

- [ ] **Step 3: Run the full suite to confirm no regressions**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest -q`
Expected: all green — the existing 578 tests plus the new playbook + migration tests. Phase 1 is purely additive; nothing existing should break.

- [ ] **Step 4: Commit**

```bash
git add tests/playbooks/test_integration.py
git commit -m "test(playbooks): end-to-end apply_to_job run integration test"
```

---

## Acceptance Criteria

A. `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest -q` is green across the whole suite.

B. Migration 0006 creates `dashboard_layout` and `playbook_runs`; opening a fresh DB records migration version 6.

C. `scripts/playbooks/` exposes: the five playbook definitions; `start_run` / `get_run` / `list_active_runs` / `set_run_jd` / `set_run_step` / `advance_run` / `abandon_run`; and `evaluate_run`.

D. A full `apply_to_job` run advances through its handoff steps automatically as the tailored resume, cover letter, and application appear in the tracker DB, and is marked `completed` at the end.

E. No Streamlit, no LLM, no new third-party dependency was added. No existing file outside `scripts/tracker/migrations/` and the test tree was modified.

---

## Out of Scope (deferred to later phases)

- The `dashboard_layout` table is *created* here but its CRUD and UI land in Phase 2.
- The widget canvas, the new Home tab, and merging away the Overview/Workflows tabs — Phase 2.
- Resume-first onboarding and migration 0007 — Phase 3.
- Version bump and CHANGELOG — deferred to Phase 2, the first user-visible phase.

---

## Self-Review

**Spec coverage (spec §4, §7.1):** §7.1 `dashboard_layout` + `playbook_runs` → Task 1. §4.1 five playbooks → Task 4. §4.2 step kinds (`in_dashboard` / `handoff`) → `PlaybookStep.kind` in Task 2, enforced by Task 4 tests. §4.3 completion predicates → Task 3. §4.4 the runner (auto-advance + the loop) → Task 6; the manual override is `set_run_step` in Task 5. §4.5 run context (`candidate_id`, `jd_id`) → `PlaybookRun` + `start_run`/`set_run_jd`. The §9 error case "a predicate that raises is treated as not-complete" → `evaluate_run`'s `except sqlite3.Error`. No Phase-1 spec requirement is unaddressed.

**Placeholder scan:** No "TBD"/"add error handling"/"similar to Task N" — every code and test block is complete and literal.

**Type consistency:** `PlaybookRun` field names (`candidate_id`, `playbook_key`, `jd_id`, `current_step`, `status`, `created_at`, `updated_at`, `completed_at`) are identical across `models.py`, the `playbook_runs` columns, `_row_to_run`, and `_COLS`. Predicate signature `(conn, run) -> bool` is consistent between `predicates.py`, the `PlaybookStep.predicate` type, and `runner.py`'s call site. `get_playbook` / `all_playbooks` / `start_run` / `get_run` / `list_active_runs` / `set_run_jd` / `set_run_step` / `advance_run` / `abandon_run` / `evaluate_run` are named identically at every definition and call site.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-20-dashboard-orchestration-phase-1.md`. Two execution options:

1. **Subagent-Driven (recommended)** — a fresh subagent per task, two-stage review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session with checkpoints.

Which approach?
