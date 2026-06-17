# Dashboard Orchestration — Phase 2 (Widget Canvas) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dashboard's flat Overview + Workflows tabs with a single customizable widget-canvas **Home** tab, backed by the Phase-1 playbook engine.

**Architecture:** A new `scripts/dashboard/widgets/` package. Each widget is a render function `(candidate) -> None` plus, where it has non-trivial logic, a pure testable helper. A catalog registers all widgets; `dashboard_layout` (migration 0006, already shipped) persists each candidate's enabled/ordered set. The Home tab resolves the saved layout against the catalog and renders the enabled widgets; a Customize mode edits it. The Overview and Workflows tabs are removed.

**Tech Stack:** Python 3.14, Streamlit, SQLite tracker, pytest (`streamlit.testing.v1.AppTest` for UI smoke tests). No new dependencies.

**Reference:** `docs/specs/2026-05-20-dashboard-orchestration-design.md` (§6 widget canvas, §8 navigation). Phase 1 (`scripts/playbooks/`) is merged to `main`.

---

## Design decisions locked for this plan

- **Widget render contract:** every widget exposes `render(candidate)` where `candidate` is the active `Candidate` (never `None` — the Home tab guards first). Widgets render inside their own `st.container(border=True)`.
- **Two zones:** `upper` (playbooks + in-progress) and `lower` (reporting/worklist/pipeline/quick-launch). The Home renders all enabled `upper` widgets, then all enabled `lower` widgets.
- **`layout.py` is pure DB CRUD** — it knows nothing about the catalog (avoids a circular import). The catalog's `resolve_layout()` reconciles a saved layout against the current catalog.
- **Overview content not in the §6.1 catalog is dropped** (the application funnel, the two sparkline cards, idle-state callouts, the pending-callbacks / recent-interview twin panels). The `worklist` widget supersedes the *intent* of idle-states and pending-callbacks; `tile_recent_outcomes` covers recent activity; the Analytics tab still holds efficacy analysis. This is deliberate, not an oversight — flagged here so the final reviewer and the user can react.
- **Version bumps to 2.1.0** — Phase 2 is the first user-visible phase of the redesign.

## File Structure

| File | Responsibility |
|------|----------------|
| `scripts/dashboard/widgets/__init__.py` | Package marker. |
| `scripts/dashboard/widgets/layout.py` | `dashboard_layout` table CRUD: `get_saved_layout`, `save_layout`, `clear_layout`. |
| `scripts/dashboard/widgets/playbook_widgets.py` | The 5 playbook-card widgets + the `in_progress_runs` widget. Wires the Phase-1 engine. |
| `scripts/dashboard/widgets/worklist.py` | `compute_worklist` (pure) + the `worklist` widget. |
| `scripts/dashboard/widgets/pipeline.py` | `classify_pipeline` (pure) + the `pipeline_mini` widget. |
| `scripts/dashboard/widgets/tiles.py` | `tile_pacing`, `tile_drift`, `tile_library_counts`, `tile_recent_outcomes` + their pure helpers. |
| `scripts/dashboard/widgets/quick_launch.py` | The `quick_launch` widget (standalone workflows). |
| `scripts/dashboard/widgets/catalog.py` | `Widget` dataclass, `WIDGET_CATALOG`, `get_widget`, `resolve_layout`. |
| `scripts/dashboard/widgets/customize.py` | The Customize-mode editor. |
| `scripts/dashboard/tabs/home.py` | The new Home tab. |
| `scripts/dashboard/app.py` | *Modify* — 9 tabs → 8; Home replaces Overview + Workflows. |
| `scripts/dashboard/tabs/overview.py`, `tabs/workflows.py` | *Delete.* |

**Dependency order:** `layout` (standalone) → widget modules (`playbook_widgets`, `worklist`, `pipeline`, `tiles`, `quick_launch`) → `catalog` (imports the widget render fns) → `home` + `customize` (import `layout` + `catalog`) → `app.py`.

The venv interpreter is `c:\Brains_Resume_Skill\.venv\Scripts\python.exe`. Run all commands from `c:\Brains_Resume_Skill`.

---

## Task 1: `dashboard_layout` CRUD

**Files:**
- Create: `scripts/dashboard/widgets/__init__.py`, `scripts/dashboard/widgets/layout.py`
- Test: `tests/dashboard/widgets/__init__.py`, `tests/dashboard/widgets/test_layout.py`

- [ ] **Step 1: Write the failing test**

Create `tests/dashboard/widgets/__init__.py` (empty file). Create `tests/dashboard/widgets/test_layout.py`:

```python
"""Tests for dashboard_layout CRUD."""
import pytest

from scripts.tracker.candidates import create_candidate
from scripts.dashboard.widgets.layout import (
    get_saved_layout, save_layout, clear_layout,
)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_get_saved_layout_empty_when_none(isolated):
    cid = create_candidate("A", "B", [], None, None)
    assert get_saved_layout(cid) == []


def test_save_then_get_round_trip_preserves_order(isolated):
    cid = create_candidate("A", "B", [], None, None)
    save_layout(cid, [("worklist", True), ("tile_drift", False), ("quick_launch", True)])
    assert get_saved_layout(cid) == [
        ("worklist", True), ("tile_drift", False), ("quick_launch", True),
    ]


def test_save_layout_replaces_previous(isolated):
    cid = create_candidate("A", "B", [], None, None)
    save_layout(cid, [("worklist", True), ("tile_drift", True)])
    save_layout(cid, [("tile_pacing", False)])
    assert get_saved_layout(cid) == [("tile_pacing", False)]


def test_layout_is_per_candidate(isolated):
    a = create_candidate("A", "A", [], None, None)
    b = create_candidate("B", "B", [], None, None)
    save_layout(a, [("worklist", True)])
    save_layout(b, [("tile_drift", False)])
    assert get_saved_layout(a) == [("worklist", True)]
    assert get_saved_layout(b) == [("tile_drift", False)]


def test_clear_layout(isolated):
    cid = create_candidate("A", "B", [], None, None)
    save_layout(cid, [("worklist", True)])
    clear_layout(cid)
    assert get_saved_layout(cid) == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_layout.py -v`
Expected: FAIL — `scripts.dashboard.widgets.layout` does not exist.

- [ ] **Step 3: Write the package marker and the CRUD module**

Create `scripts/dashboard/widgets/__init__.py`:

```python
"""Dashboard widget canvas — registry, layout persistence, and widgets."""
```

Create `scripts/dashboard/widgets/layout.py`:

```python
"""CRUD for the dashboard_layout table (per-candidate widget canvas).

Pure DB access — this module deliberately knows nothing about the widget
catalog. Reconciling a saved layout against the catalog is catalog.py's job.
The dashboard_layout table was created by migration 0006 (Phase 1).
"""
from datetime import datetime
from typing import List, Tuple

from scripts.tracker.db import open_db


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def get_saved_layout(candidate_id: int) -> List[Tuple[str, bool]]:
    """Return the candidate's saved layout as an ordered list of
    (widget_key, enabled). Empty list when the candidate has no saved rows."""
    conn = open_db()
    try:
        rows = conn.execute(
            "SELECT widget_key, enabled FROM dashboard_layout "
            "WHERE candidate_id=? ORDER BY position ASC",
            (candidate_id,),
        ).fetchall()
    finally:
        conn.close()
    return [(r[0], bool(r[1])) for r in rows]


def save_layout(candidate_id: int, entries: List[Tuple[str, bool]]) -> None:
    """Replace the candidate's layout with `entries` (ordered list of
    (widget_key, enabled)). Position is the list index."""
    now = _now_iso()
    conn = open_db()
    try:
        conn.execute(
            "DELETE FROM dashboard_layout WHERE candidate_id=?", (candidate_id,)
        )
        conn.executemany(
            "INSERT INTO dashboard_layout "
            "(candidate_id, widget_key, position, enabled, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (candidate_id, key, pos, 1 if enabled else 0, now)
                for pos, (key, enabled) in enumerate(entries)
            ],
        )
        conn.commit()
    finally:
        conn.close()


def clear_layout(candidate_id: int) -> None:
    """Delete the candidate's saved layout — the Home tab then falls back to
    the catalog default."""
    conn = open_db()
    try:
        conn.execute(
            "DELETE FROM dashboard_layout WHERE candidate_id=?", (candidate_id,)
        )
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_layout.py -v`
Expected: PASS — all 5 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/widgets/__init__.py scripts/dashboard/widgets/layout.py tests/dashboard/widgets/__init__.py tests/dashboard/widgets/test_layout.py
git commit -m "feat(dashboard): dashboard_layout CRUD"
```

---

## Task 2: Playbook widgets

**Files:**
- Create: `scripts/dashboard/widgets/playbook_widgets.py`
- Test: `tests/dashboard/widgets/test_playbook_widgets.py`

Six widgets: one card per playbook (5) and `in_progress_runs`. The card "Start" button calls `scripts.playbooks.runs.start_run`; the in-progress widget lists `list_active_runs`, calls `evaluate_run` to auto-advance, and offers Continue (handoff) / Mark-done / Abandon.

- [ ] **Step 1: Write the failing test**

Create `tests/dashboard/widgets/test_playbook_widgets.py`:

```python
"""Tests for playbook widgets — focus on the pure helper."""
import pytest

from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.playbooks.runs import start_run
from scripts.dashboard.widgets.playbook_widgets import (
    active_run_rows, make_playbook_card_renderer, render_in_progress_runs,
)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_active_run_rows_empty(isolated):
    cid = create_candidate("A", "B", [], None, None)
    assert active_run_rows(cid) == []


def test_active_run_rows_describes_a_run(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    start_run(cid, "apply_to_job")
    rows = active_run_rows(cid)
    assert len(rows) == 1
    row = rows[0]
    assert row["playbook_label"] == "Apply to a job"
    assert row["step_number"] == 1          # 1-based for display
    assert row["total_steps"] == 6
    assert row["step_label"] == "Analyze the JD"
    assert row["status"] == "active"


def test_make_playbook_card_renderer_returns_callable(isolated):
    fn = make_playbook_card_renderer("build_resume")
    assert callable(fn)


def test_render_in_progress_runs_is_callable(isolated):
    assert callable(render_in_progress_runs)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_playbook_widgets.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Write the playbook widgets**

Create `scripts/dashboard/widgets/playbook_widgets.py`:

```python
"""Playbook widgets — the 5 playbook cards and the in-progress-runs widget.

Wires the Phase-1 playbook engine (scripts/playbooks/) into the canvas.
"""
import streamlit as st

from scripts.dashboard.handoff import handoff
from scripts.playbooks.definitions import get_playbook
from scripts.playbooks.runs import (
    start_run, list_active_runs, advance_run, abandon_run,
)
from scripts.playbooks.runner import evaluate_run


def active_run_rows(candidate_id: int) -> list[dict]:
    """Pure helper: describe each active run for display. Evaluates each run
    first (auto-advance), then returns display dicts."""
    rows = []
    for run in list_active_runs(candidate_id):
        evaluate_run(run.id)
    for run in list_active_runs(candidate_id):
        playbook = get_playbook(run.playbook_key)
        idx = min(run.current_step, len(playbook.steps) - 1)
        step = playbook.steps[idx]
        rows.append({
            "run_id": run.id,
            "playbook_label": playbook.label,
            "step_number": run.current_step + 1,
            "total_steps": len(playbook.steps),
            "step_label": step.label,
            "step_kind": step.kind,
            "step_command": step.command,
            "status": run.status,
        })
    return rows


def make_playbook_card_renderer(playbook_key: str):
    """Return a render(candidate) function for one playbook card."""
    def _render(candidate) -> None:
        playbook = get_playbook(playbook_key)
        with st.container(border=True):
            st.markdown(f"**{playbook.label}**")
            st.caption(" → ".join(s.label for s in playbook.steps))
            if st.button("Start", key=f"pb_start_{playbook_key}"):
                start_run(candidate.id, playbook_key)
                st.rerun()
    return _render


def render_in_progress_runs(candidate) -> None:
    """The in_progress_runs widget — active playbook runs with actions."""
    with st.container(border=True):
        st.markdown("**In progress**")
        rows = active_run_rows(candidate.id)
        if not rows:
            st.caption("No playbook in progress. Start one from a card above.")
            return
        for row in rows:
            st.markdown(
                f"{row['playbook_label']} — step {row['step_number']} of "
                f"{row['total_steps']}: *{row['step_label']}*"
            )
            cols = st.columns(3)
            with cols[0]:
                if row["step_command"]:
                    if st.button("Continue", key=f"pb_cont_{row['run_id']}"):
                        handoff(row["step_command"],
                                note=f"Playbook step: {row['step_label']}")
                else:
                    st.caption("in-dashboard step")
            with cols[1]:
                if st.button("Mark done →", key=f"pb_done_{row['run_id']}"):
                    advance_run(row["run_id"])
                    st.rerun()
            with cols[2]:
                if st.button("Abandon", key=f"pb_abandon_{row['run_id']}"):
                    abandon_run(row["run_id"])
                    st.rerun()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_playbook_widgets.py -v`
Expected: PASS — all 4 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/widgets/playbook_widgets.py tests/dashboard/widgets/test_playbook_widgets.py
git commit -m "feat(dashboard): playbook card + in-progress widgets"
```

---

## Task 3: Worklist widget

**Files:**
- Create: `scripts/dashboard/widgets/worklist.py`
- Test: `tests/dashboard/widgets/test_worklist.py`

`compute_worklist(candidate_id)` returns a prioritized list of next-action items from three concrete rules: active playbook runs, stale applications (submitted > 7 days ago, no outcome), and below-target pacing.

- [ ] **Step 1: Write the failing test**

Create `tests/dashboard/widgets/test_worklist.py`:

```python
"""Tests for the worklist widget's pure helper."""
from datetime import datetime, timedelta

import pytest

from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.tracker.add import add_jd, add_resume_version, add_application
from scripts.playbooks.runs import start_run
from scripts.dashboard.widgets.worklist import compute_worklist


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_empty_worklist(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    assert compute_worklist(cid) == []


def test_active_run_produces_a_worklist_item(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    start_run(cid, "apply_to_job")
    items = compute_worklist(cid)
    assert any("Apply to a job" in it["text"] for it in items)


def test_stale_application_produces_an_item(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    rv = add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    add_application(jd, rv, None, datetime.now() - timedelta(days=10), "direct")
    items = compute_worklist(cid)
    assert any("Acme" in it["text"] for it in items)


def test_every_item_has_text_and_severity(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    start_run(cid, "build_resume")
    for it in compute_worklist(cid):
        assert it["text"]
        assert it["severity"] in ("high", "medium", "low")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_worklist.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Write the worklist widget**

Create `scripts/dashboard/widgets/worklist.py`:

```python
"""The worklist widget — a computed 'what to do next' list.

compute_worklist applies three concrete rules against the tracker DB:
  1. active playbook runs            -> "Continue: <playbook>"   (high)
  2. applications submitted > 7 days ago with no outcome  (medium)
  3. below-target weekly pacing                            (low)
"""
from datetime import datetime, timedelta

import streamlit as st

from scripts.dashboard.data import cached_list_applications
from scripts.playbooks.definitions import get_playbook
from scripts.playbooks.runs import list_active_runs


_SEVERITY_DOT = {"high": "🔴", "medium": "🟠", "low": "🟡"}


def compute_worklist(candidate_id: int) -> list[dict]:
    """Return prioritized next-action items: list of
    {severity, text} dicts, high severity first."""
    items: list[dict] = []

    for run in list_active_runs(candidate_id):
        playbook = get_playbook(run.playbook_key)
        items.append({
            "severity": "high",
            "text": f"Continue: {playbook.label} "
                    f"(step {run.current_step + 1} of {len(playbook.steps)})",
        })

    rows = cached_list_applications()
    cutoff = datetime.now() - timedelta(days=7)
    for r in rows:
        if r.latest_outcome is None and datetime.fromisoformat(r.submitted_at) < cutoff:
            days = (datetime.now() - datetime.fromisoformat(r.submitted_at)).days
            items.append({
                "severity": "medium",
                "text": f"{r.company} — {days} days, no response",
            })

    from scripts.dashboard.data import cached_weekly_summary
    weekly = cached_weekly_summary()
    if weekly.pacing_vs_target == "below":
        items.append({
            "severity": "low",
            "text": f"Pacing — {weekly.applications_count} applications this week",
        })

    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda it: order[it["severity"]])
    return items


def render_worklist(candidate) -> None:
    """The worklist widget."""
    with st.container(border=True):
        st.markdown("**Next actions**")
        items = compute_worklist(candidate.id)
        if not items:
            st.caption("Nothing needs attention right now.")
            return
        for it in items:
            st.markdown(f"{_SEVERITY_DOT[it['severity']]} {it['text']}")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_worklist.py -v`
Expected: PASS — all 4 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/widgets/worklist.py tests/dashboard/widgets/test_worklist.py
git commit -m "feat(dashboard): worklist widget"
```

---

## Task 4: Pipeline widget

**Files:**
- Create: `scripts/dashboard/widgets/pipeline.py`
- Test: `tests/dashboard/widgets/test_pipeline.py`

`classify_pipeline(candidate_id)` buckets each of the candidate's JDs into one of five stages by which artifacts exist.

- [ ] **Step 1: Write the failing test**

Create `tests/dashboard/widgets/test_pipeline.py`:

```python
"""Tests for the pipeline widget's pure helper."""
from datetime import datetime

import pytest

from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.tracker.add import (
    add_jd, add_resume_version, add_cover_letter, add_application,
)
from scripts.dashboard.widgets.pipeline import classify_pipeline, PIPELINE_STAGES


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_stages_constant():
    assert PIPELINE_STAGES == ("Lead", "Tailoring", "Docs ready", "Submitted", "Outcome")


def test_empty_pipeline_has_all_stages(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    result = classify_pipeline(cid)
    assert set(result.keys()) == set(PIPELINE_STAGES)
    assert all(v == [] for v in result.values())


def test_jd_only_is_a_lead(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    add_jd("manual", None, "Coles", "Retail", "x", {}, [], [])
    assert [c["company"] for c in classify_pipeline(cid)["Lead"]] == ["Coles"]


def test_jd_with_resume_is_tailoring(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Big W", "Sales", "x", {}, [], [])
    add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    assert [c["company"] for c in classify_pipeline(cid)["Tailoring"]] == ["Big W"]


def test_application_is_submitted(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    jd = add_jd("manual", None, "Kmart", "Floor", "x", {}, [], [])
    rv = add_resume_version(None, "hybrid", [], tagged_jd_id=jd)
    add_application(jd, rv, None, datetime(2026, 2, 1), "direct")
    assert [c["company"] for c in classify_pipeline(cid)["Submitted"]] == ["Kmart"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_pipeline.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Write the pipeline widget**

Create `scripts/dashboard/widgets/pipeline.py`:

```python
"""The pipeline_mini widget — each JD as a card across five stages.

Stage of a JD, by which artifacts exist (latest-wins):
  application + terminal outcome      -> Outcome
  application                         -> Submitted
  cover letter                        -> Docs ready
  resume tagged to the JD             -> Tailoring
  nothing yet                         -> Lead
"""
import streamlit as st

from scripts.tracker.db import open_db


PIPELINE_STAGES = ("Lead", "Tailoring", "Docs ready", "Submitted", "Outcome")
_TERMINAL = ("offer", "rejection", "withdrew")


def classify_pipeline(candidate_id: int) -> dict:
    """Return {stage: [ {jd_id, company, role_title}, ... ]} for the
    candidate's non-archived JDs."""
    result: dict = {stage: [] for stage in PIPELINE_STAGES}
    conn = open_db()
    try:
        jds = conn.execute(
            "SELECT id, company, role_title FROM jds "
            "WHERE candidate_id=? AND archived_at IS NULL ORDER BY created_at ASC",
            (candidate_id,),
        ).fetchall()
        for jd_id, company, role_title in jds:
            card = {"jd_id": jd_id, "company": company, "role_title": role_title}
            app = conn.execute(
                "SELECT id FROM applications WHERE jd_id=? LIMIT 1", (jd_id,)
            ).fetchone()
            if app is not None:
                outcome = conn.execute(
                    "SELECT event_type FROM outcomes WHERE application_id=? "
                    "ORDER BY event_date DESC LIMIT 1",
                    (app[0],),
                ).fetchone()
                if outcome is not None and outcome[0] in _TERMINAL:
                    result["Outcome"].append(card)
                else:
                    result["Submitted"].append(card)
                continue
            has_cl = conn.execute(
                "SELECT 1 FROM cover_letters WHERE jd_id=? AND archived_at IS NULL "
                "LIMIT 1", (jd_id,)
            ).fetchone()
            if has_cl is not None:
                result["Docs ready"].append(card)
                continue
            has_resume = conn.execute(
                "SELECT 1 FROM resume_versions WHERE tagged_jd_id=? "
                "AND archived_at IS NULL LIMIT 1", (jd_id,)
            ).fetchone()
            if has_resume is not None:
                result["Tailoring"].append(card)
            else:
                result["Lead"].append(card)
    finally:
        conn.close()
    return result


def render_pipeline(candidate) -> None:
    """The pipeline_mini widget."""
    with st.container(border=True):
        st.markdown("**Pipeline**")
        board = classify_pipeline(candidate.id)
        cols = st.columns(len(PIPELINE_STAGES))
        for col, stage in zip(cols, PIPELINE_STAGES):
            with col:
                st.caption(f"{stage} ({len(board[stage])})")
                for card in board[stage][:5]:
                    st.markdown(f"- {card['company']}")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_pipeline.py -v`
Expected: PASS — all 5 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/widgets/pipeline.py tests/dashboard/widgets/test_pipeline.py
git commit -m "feat(dashboard): pipeline mini-board widget"
```

---

## Task 5: Tile widgets

**Files:**
- Create: `scripts/dashboard/widgets/tiles.py`
- Test: `tests/dashboard/widgets/test_tiles.py`

Four widgets: `tile_pacing`, `tile_drift`, `tile_library_counts`, `tile_recent_outcomes`. The drift logic is relocated here from the soon-to-be-deleted `overview.py`.

- [ ] **Step 1: Write the failing test**

Create `tests/dashboard/widgets/test_tiles.py`:

```python
"""Tests for the tile widgets' pure helpers."""
import pytest

from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.tracker.add import add_jd, add_resume_version
from scripts.dashboard.widgets.tiles import (
    pacing_summary, library_counts, drift_tile_summary,
    render_tile_pacing, render_tile_drift, render_tile_library_counts,
    render_tile_recent_outcomes,
)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_pacing_summary_no_target(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    s = pacing_summary(cid)
    assert s["this_week"] == 0
    assert s["target"] is None


def test_pacing_summary_with_target(isolated):
    cid = create_candidate("A", "B", [], 3, None)
    set_active_candidate(cid)
    assert pacing_summary(cid)["target"] == 3


def test_library_counts(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    add_jd("manual", None, "Acme", "Eng", "x", {}, [], [])
    add_resume_version(None, "hybrid", [])
    counts = library_counts(cid)
    assert counts["resumes"] == 1
    assert counts["jds"] == 1
    assert counts["cover_letters"] == 0


def test_drift_tile_summary_empty(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    s = drift_tile_summary({"candidate_id": cid})
    assert s["headline_pct"] is None
    assert s["count"] == 0


def test_tile_render_fns_are_callable():
    for fn in (render_tile_pacing, render_tile_drift,
               render_tile_library_counts, render_tile_recent_outcomes):
        assert callable(fn)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_tiles.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Write the tile widgets**

Create `scripts/dashboard/widgets/tiles.py`:

```python
"""Reporting tile widgets: pacing, drift, library counts, recent outcomes.

drift_tile_summary / render_tile_drift are relocated from the deleted
overview.py (their behaviour is unchanged).
"""
import json

import streamlit as st

from scripts.dashboard.data import cached_list_applications, cached_weekly_summary
from scripts.dashboard.prep.trends import applications_this_week_count
from scripts.tracker.candidates import get_candidate
from scripts.tracker.db import open_db


# ---- pacing -----------------------------------------------------------------

def pacing_summary(candidate_id: int) -> dict:
    """Return {this_week, target} for the active candidate's pacing."""
    candidate = get_candidate(candidate_id)
    rows = cached_list_applications()
    return {
        "this_week": applications_this_week_count(rows),
        "target": candidate.healthy_weekly_rate if candidate else None,
    }


def render_tile_pacing(candidate) -> None:
    with st.container(border=True):
        s = pacing_summary(candidate.id)
        value = str(s["this_week"])
        if s["target"] is not None:
            value = f"{s['this_week']} / {s['target']}"
        st.metric("Pacing (this week)", value)


# ---- library counts ---------------------------------------------------------

def library_counts(candidate_id: int) -> dict:
    """Return {resumes, cover_letters, jds} counts for the candidate."""
    conn = open_db()
    try:
        def _count(table):
            return conn.execute(
                f"SELECT COUNT(*) FROM {table} "
                "WHERE candidate_id=? AND archived_at IS NULL",
                (candidate_id,),
            ).fetchone()[0]
        return {
            "resumes": _count("resume_versions"),
            "cover_letters": _count("cover_letters"),
            "jds": _count("jds"),
        }
    finally:
        conn.close()


def render_tile_library_counts(candidate) -> None:
    with st.container(border=True):
        st.markdown("**Library**")
        c = library_counts(candidate.id)
        cols = st.columns(3)
        cols[0].metric("Resumes", c["resumes"])
        cols[1].metric("Cover letters", c["cover_letters"])
        cols[2].metric("JDs", c["jds"])


# ---- drift ------------------------------------------------------------------

def drift_tile_summary(scope: dict) -> dict:
    """Return {headline_pct, sparkline, headline_changes, count} for the
    drift trajectory tile. Relocated verbatim from overview._drift_tile_summary."""
    from scripts.dashboard.prep.drift_sparkline import drift_trajectory_last_n

    points = drift_trajectory_last_n(scope, n=12)
    if not points:
        return {"headline_pct": None, "sparkline": [], "headline_changes": [], "count": 0}
    latest = points[-1]
    headline_pct = latest["overall_pct"]
    sparkline = [p["overall_pct"] for p in points]
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT vs_baseline_score FROM resume_drift_scores WHERE artifact_uid=?",
            (latest["artifact_uid"],),
        ).fetchone()
    finally:
        conn.close()
    headline_changes = []
    if row and row[0]:
        try:
            headline_changes = json.loads(row[0]).get("headline_changes", [])
        except json.JSONDecodeError:
            pass
    return {
        "headline_pct": headline_pct,
        "sparkline": sparkline,
        "headline_changes": headline_changes,
        "count": len(points),
    }


def render_tile_drift(candidate) -> None:
    with st.container(border=True):
        st.caption("Drift from baseline · active candidate")
        summary = drift_tile_summary({"candidate_id": candidate.id})
        if summary["headline_pct"] is None:
            st.markdown("**—**")
            st.caption("No baseline yet")
            return
        st.markdown(f"**{summary['headline_pct']:.1f}%**")
        if summary["sparkline"]:
            import pandas as pd
            st.line_chart(
                pd.DataFrame({"drift": [v if v is not None else 0.0
                                        for v in summary["sparkline"]]}),
                height=60, use_container_width=True,
            )
        if summary["headline_changes"]:
            st.caption(summary["headline_changes"][0])


# ---- recent outcomes --------------------------------------------------------

def render_tile_recent_outcomes(candidate) -> None:
    with st.container(border=True):
        st.markdown("**Recent outcomes**")
        rows = [r for r in cached_list_applications() if r.latest_outcome]
        if not rows:
            st.caption("No outcomes logged yet.")
            return
        for r in rows[:6]:
            st.markdown(f"- **{r.company}** — {r.latest_outcome}")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_tiles.py -v`
Expected: PASS — all 5 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/widgets/tiles.py tests/dashboard/widgets/test_tiles.py
git commit -m "feat(dashboard): pacing / drift / library-counts / recent-outcomes tiles"
```

---

## Task 6: Quick-launch widget

**Files:**
- Create: `scripts/dashboard/widgets/quick_launch.py`
- Test: `tests/dashboard/widgets/test_quick_launch.py`

A widget with expanders for the standalone (non-playbook) workflows: JD-analyze, de-AI, disclosure, track.

- [ ] **Step 1: Write the failing test**

Create `tests/dashboard/widgets/test_quick_launch.py`:

```python
"""Tests for the quick-launch widget."""
from scripts.dashboard.widgets.quick_launch import render_quick_launch, QUICK_LAUNCH_WORKFLOWS


def test_quick_launch_workflow_list():
    slugs = {w[0] for w in QUICK_LAUNCH_WORKFLOWS}
    assert slugs == {"jd_analyze", "deai", "disclosure", "track"}


def test_render_quick_launch_is_callable():
    assert callable(render_quick_launch)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_quick_launch.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Write the quick-launch widget**

Create `scripts/dashboard/widgets/quick_launch.py`:

```python
"""The quick_launch widget — standalone workflows not part of any playbook.

Each entry reuses an existing workflow module's render(file_path, key_prefix).
"""
import streamlit as st

from scripts.dashboard.workflows import deai, disclosure, jd_analyze, track


# (slug, label, module)
QUICK_LAUNCH_WORKFLOWS = (
    ("jd_analyze", "Analyze a JD", jd_analyze),
    ("deai", "De-AI scan", deai),
    ("disclosure", "Disclosure coaching", disclosure),
    ("track", "Application tracker", track),
)


def render_quick_launch(candidate) -> None:
    """The quick_launch widget."""
    with st.container(border=True):
        st.markdown("**Quick launch**")
        for slug, label, module in QUICK_LAUNCH_WORKFLOWS:
            with st.expander(label):
                module.render(file_path=None, key_prefix=f"ql_{slug}")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_quick_launch.py -v`
Expected: PASS — both tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/widgets/quick_launch.py tests/dashboard/widgets/test_quick_launch.py
git commit -m "feat(dashboard): quick-launch widget"
```

---

## Task 7: Widget catalog + layout resolution

**Files:**
- Create: `scripts/dashboard/widgets/catalog.py`
- Test: `tests/dashboard/widgets/test_catalog.py`

The catalog registers all 13 widgets and reconciles a saved layout against the current widget set.

- [ ] **Step 1: Write the failing test**

Create `tests/dashboard/widgets/test_catalog.py`:

```python
"""Tests for the widget catalog and layout resolution."""
import pytest

from scripts.dashboard.widgets.catalog import (
    Widget, WIDGET_CATALOG, get_widget, resolve_layout,
)


def test_catalog_has_expected_widgets():
    keys = {w.key for w in WIDGET_CATALOG}
    assert keys == {
        "in_progress_runs",
        "playbook_apply", "playbook_build", "playbook_improve",
        "playbook_linkedin", "playbook_career_change",
        "worklist", "pipeline_mini",
        "tile_pacing", "tile_drift", "tile_library_counts",
        "quick_launch", "tile_recent_outcomes",
    }


def test_every_widget_has_valid_fields():
    for w in WIDGET_CATALOG:
        assert w.zone in ("upper", "lower")
        assert callable(w.render)
        assert w.label


def test_recent_outcomes_is_off_by_default():
    assert get_widget("tile_recent_outcomes").default_enabled is False


def test_playbook_widgets_default_on():
    assert get_widget("playbook_apply").default_enabled is True


def test_get_widget_unknown_raises():
    with pytest.raises(KeyError):
        get_widget("nope")


def test_resolve_layout_empty_returns_full_catalog_defaults():
    resolved = resolve_layout([])
    assert len(resolved) == len(WIDGET_CATALOG)
    by_key = {w.key: enabled for w, enabled in resolved}
    assert by_key["playbook_apply"] is True
    assert by_key["tile_recent_outcomes"] is False


def test_resolve_layout_honours_saved_order_and_enabled():
    resolved = resolve_layout([("worklist", False), ("tile_drift", True)])
    assert resolved[0][0].key == "worklist"
    assert resolved[0][1] is False
    assert resolved[1][0].key == "tile_drift"
    # widgets absent from the saved layout are appended with their defaults
    assert len(resolved) == len(WIDGET_CATALOG)


def test_resolve_layout_drops_unknown_keys():
    resolved = resolve_layout([("removed_widget", True), ("worklist", True)])
    assert all(w.key != "removed_widget" for w, _ in resolved)
    assert resolved[0][0].key == "worklist"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_catalog.py -v`
Expected: FAIL — `scripts.dashboard.widgets.catalog` does not exist.

- [ ] **Step 3: Write the catalog**

Create `scripts/dashboard/widgets/catalog.py`:

```python
"""The widget catalog — registers every widget and resolves saved layouts.

A Widget bundles display metadata with its render callable. WIDGET_CATALOG
order is the default display order. resolve_layout reconciles a candidate's
saved layout (from layout.py) against the current catalog.
"""
from dataclasses import dataclass
from typing import Callable, List, Tuple

from scripts.dashboard.widgets.playbook_widgets import (
    make_playbook_card_renderer, render_in_progress_runs,
)
from scripts.dashboard.widgets.worklist import render_worklist
from scripts.dashboard.widgets.pipeline import render_pipeline
from scripts.dashboard.widgets.tiles import (
    render_tile_pacing, render_tile_drift, render_tile_library_counts,
    render_tile_recent_outcomes,
)
from scripts.dashboard.widgets.quick_launch import render_quick_launch


@dataclass(frozen=True)
class Widget:
    """A canvas widget: display metadata + its render callable.

    render: a function (candidate) -> None.
    zone:   'upper' (playbooks/in-progress) or 'lower' (reporting).
    """
    key: str
    label: str
    zone: str
    default_enabled: bool
    render: Callable


WIDGET_CATALOG: Tuple[Widget, ...] = (
    Widget("in_progress_runs", "In progress", "upper", True,
           render_in_progress_runs),
    Widget("playbook_apply", "Apply to a job", "upper", True,
           make_playbook_card_renderer("apply_to_job")),
    Widget("playbook_build", "Build a base resume", "upper", True,
           make_playbook_card_renderer("build_resume")),
    Widget("playbook_improve", "Improve a resume", "upper", True,
           make_playbook_card_renderer("improve_resume")),
    Widget("playbook_linkedin", "Refresh LinkedIn", "upper", True,
           make_playbook_card_renderer("refresh_linkedin")),
    Widget("playbook_career_change", "Career change", "upper", True,
           make_playbook_card_renderer("career_change")),
    Widget("worklist", "Next actions", "lower", True, render_worklist),
    Widget("pipeline_mini", "Pipeline", "lower", True, render_pipeline),
    Widget("tile_pacing", "Pacing", "lower", True, render_tile_pacing),
    Widget("tile_drift", "Drift", "lower", True, render_tile_drift),
    Widget("tile_library_counts", "Library", "lower", True,
           render_tile_library_counts),
    Widget("quick_launch", "Quick launch", "lower", True, render_quick_launch),
    Widget("tile_recent_outcomes", "Recent outcomes", "lower", False,
           render_tile_recent_outcomes),
)

_BY_KEY = {w.key: w for w in WIDGET_CATALOG}


def get_widget(key: str) -> Widget:
    """Return the widget with the given key. Raises KeyError if unknown."""
    if key not in _BY_KEY:
        raise KeyError(f"Unknown widget: {key!r}")
    return _BY_KEY[key]


def resolve_layout(saved: List[Tuple[str, bool]]) -> List[Tuple[Widget, bool]]:
    """Reconcile a saved layout against the current catalog.

    - Known saved widgets keep their saved order and enabled flag.
    - Unknown saved keys are dropped.
    - Catalog widgets absent from the saved layout are appended in catalog
      order with their default_enabled flag.
    An empty saved layout therefore yields the full catalog with defaults.
    """
    result: List[Tuple[Widget, bool]] = []
    seen: set = set()
    for key, enabled in saved:
        if key in _BY_KEY and key not in seen:
            result.append((_BY_KEY[key], enabled))
            seen.add(key)
    for w in WIDGET_CATALOG:
        if w.key not in seen:
            result.append((w, w.default_enabled))
            seen.add(w.key)
    return result
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_catalog.py -v`
Expected: PASS — all 8 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/widgets/catalog.py tests/dashboard/widgets/test_catalog.py
git commit -m "feat(dashboard): widget catalog + layout resolution"
```

---

## Task 8: The Home tab

**Files:**
- Create: `scripts/dashboard/tabs/home.py`
- Test: `tests/dashboard/tabs/test_home_tab.py`

The Home tab resolves the active candidate's layout and renders the enabled widgets, upper zone then lower zone.

- [ ] **Step 1: Write the failing test**

Create `tests/dashboard/tabs/test_home_tab.py`:

```python
"""Tests for the Home tab."""
import pytest

from scripts.tracker.candidates import create_candidate, set_active_candidate
from scripts.dashboard.tabs.home import effective_layout


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_effective_layout_default_when_no_saved(isolated):
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    layout = effective_layout(cid)
    # default: every catalog widget present; playbooks enabled
    keys = {w.key for w, _ in layout}
    assert "playbook_apply" in keys
    assert ("tile_recent_outcomes" in keys)
    enabled = {w.key for w, en in layout if en}
    assert "playbook_apply" in enabled
    assert "tile_recent_outcomes" not in enabled


def test_effective_layout_reflects_saved(isolated):
    from scripts.dashboard.widgets.layout import save_layout
    cid = create_candidate("A", "B", [], None, None)
    set_active_candidate(cid)
    save_layout(cid, [("worklist", False)])
    layout = effective_layout(cid)
    by_key = {w.key: en for w, en in layout}
    assert by_key["worklist"] is False
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/tabs/test_home_tab.py -v`
Expected: FAIL — `scripts.dashboard.tabs.home` does not exist.

- [ ] **Step 3: Write the Home tab**

Create `scripts/dashboard/tabs/home.py`:

```python
"""The Home tab — the customizable widget canvas.

Resolves the active candidate's saved layout against the catalog and renders
the enabled widgets: all 'upper'-zone widgets first, then all 'lower'-zone
widgets. A Customize expander edits the layout.
"""
import streamlit as st

from scripts.tracker.candidates import get_active_candidate
from scripts.dashboard.widgets.catalog import resolve_layout
from scripts.dashboard.widgets.layout import get_saved_layout
from scripts.dashboard.widgets.customize import render_customize


def effective_layout(candidate_id: int):
    """Return the resolved layout for a candidate — list of (Widget, enabled)."""
    return resolve_layout(get_saved_layout(candidate_id))


def render() -> None:
    """Render the Home tab."""
    active = get_active_candidate()
    if active is None:
        st.info("No active candidate. Select or create one in the sidebar.")
        return

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

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/tabs/test_home_tab.py -v`
Expected: PASS — both tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/tabs/home.py tests/dashboard/tabs/test_home_tab.py
git commit -m "feat(dashboard): Home tab — widget canvas"
```

---

## Task 9: Customize mode

**Files:**
- Create: `scripts/dashboard/widgets/customize.py`
- Test: `tests/dashboard/widgets/test_customize.py`

The Customize editor: per-widget enable toggle + move-up / move-down, persisted via `save_layout`. The reordering math is a pure helper.

- [ ] **Step 1: Write the failing test**

Create `tests/dashboard/widgets/test_customize.py`:

```python
"""Tests for the Customize-mode reorder helper."""
from scripts.dashboard.widgets.customize import move_entry, render_customize


def test_move_entry_up():
    entries = [("a", True), ("b", True), ("c", True)]
    assert move_entry(entries, 1, "up") == [("b", True), ("a", True), ("c", True)]


def test_move_entry_down():
    entries = [("a", True), ("b", True), ("c", True)]
    assert move_entry(entries, 1, "down") == [("a", True), ("c", True), ("b", True)]


def test_move_entry_up_at_top_is_noop():
    entries = [("a", True), ("b", True)]
    assert move_entry(entries, 0, "up") == [("a", True), ("b", True)]


def test_move_entry_down_at_bottom_is_noop():
    entries = [("a", True), ("b", True)]
    assert move_entry(entries, 1, "down") == [("a", True), ("b", True)]


def test_move_entry_does_not_mutate_input():
    entries = [("a", True), ("b", True)]
    move_entry(entries, 1, "up")
    assert entries == [("a", True), ("b", True)]


def test_render_customize_is_callable():
    assert callable(render_customize)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_customize.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Write the Customize editor**

Create `scripts/dashboard/widgets/customize.py`:

```python
"""Customize mode — edit which widgets show on the Home canvas and in what
order. Persists via layout.save_layout; reset via layout.clear_layout.
"""
from typing import List, Tuple

import streamlit as st

from scripts.dashboard.widgets.catalog import resolve_layout
from scripts.dashboard.widgets.layout import (
    get_saved_layout, save_layout, clear_layout,
)


def move_entry(entries: List[Tuple[str, bool]], index: int,
               direction: str) -> List[Tuple[str, bool]]:
    """Return a new list with the entry at `index` moved one slot up or down.
    Out-of-range moves are a no-op. Does not mutate the input."""
    result = list(entries)
    if direction == "up" and index > 0:
        result[index - 1], result[index] = result[index], result[index - 1]
    elif direction == "down" and index < len(result) - 1:
        result[index + 1], result[index] = result[index], result[index + 1]
    return result


def render_customize(candidate) -> None:
    """Render the Customize editor for the active candidate."""
    st.caption("Toggle widgets on/off and reorder them. Saved per candidate.")
    resolved = resolve_layout(get_saved_layout(candidate.id))
    entries: List[Tuple[str, bool]] = [(w.key, en) for w, en in resolved]
    labels = {w.key: w.label for w, _ in resolved}

    for idx, (key, enabled) in enumerate(entries):
        cols = st.columns([3, 1, 1])
        with cols[0]:
            new_enabled = st.checkbox(
                labels.get(key, key), value=enabled, key=f"cz_en_{key}"
            )
            if new_enabled != enabled:
                save_layout(candidate.id,
                            [(k, new_enabled if k == key else e)
                             for k, e in entries])
                st.rerun()
        with cols[1]:
            if st.button("↑", key=f"cz_up_{key}") and idx > 0:
                save_layout(candidate.id, move_entry(entries, idx, "up"))
                st.rerun()
        with cols[2]:
            if st.button("↓", key=f"cz_dn_{key}") and idx < len(entries) - 1:
                save_layout(candidate.id, move_entry(entries, idx, "down"))
                st.rerun()

    if st.button("Reset to default", key="cz_reset"):
        clear_layout(candidate.id)
        st.rerun()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/widgets/test_customize.py -v`
Expected: PASS — all 6 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/widgets/customize.py tests/dashboard/widgets/test_customize.py
git commit -m "feat(dashboard): Customize mode — add/remove/reorder widgets"
```

---

## Task 10: Rewire app.py — Home replaces Overview + Workflows

**Files:**
- Modify: `scripts/dashboard/app.py`
- Delete: `scripts/dashboard/tabs/overview.py`, `scripts/dashboard/tabs/workflows.py`
- Delete: `tests/dashboard/test_app_overview_render.py`, `tests/dashboard/test_app_workflows_tab.py`
- Test: `tests/dashboard/test_app_home.py`

- [ ] **Step 1: Write the failing test**

Create `tests/dashboard/test_app_home.py`:

```python
"""Tests for the rewired app — Home replaces Overview + Workflows."""
from pathlib import Path

import pytest

APP_PATH = str(Path("scripts/dashboard/app.py").resolve())


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_app_loads_without_exception(isolated):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    assert not at.exception, f"App raised: {at.exception}"


def test_app_has_eight_tabs_with_home_first(isolated):
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    create_candidate("A", "B", [], None, None)
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=20)
    assert not at.exception
    # The app source no longer references the removed tabs.
    src = Path(APP_PATH).read_text(encoding="utf-8")
    assert "home" in src
    assert "overview" not in src
    assert "workflows" not in src


def test_overview_and_workflows_modules_are_gone():
    assert not Path("scripts/dashboard/tabs/overview.py").exists()
    assert not Path("scripts/dashboard/tabs/workflows.py").exists()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/test_app_home.py -v`
Expected: FAIL — `app.py` still wires `overview`/`workflows`; the modules still exist.

- [ ] **Step 3: Rewire `app.py`**

Replace the entire content of `scripts/dashboard/app.py` with:

```python
"""Main Streamlit entry for the BRAINS Resume dashboard.

Run via the `brains-resume-dashboard` CLI entry point (see launch.py)
which invokes `streamlit run scripts/dashboard/app.py`.

Eight-tab layout. The Home tab is a customizable widget canvas
(orchestration hub); the other seven are deep drill-down views.
BRAINS Incubator branded.
"""
import streamlit as st

from scripts.dashboard.sidebar import render_sidebar
from scripts.dashboard.style import inject_brand_css
from scripts.dashboard.tabs import (
    analytics,
    applications,
    cover_letters,
    drift as drift_tab,
    home,
    jds,
    pacing,
    resumes,
)
from scripts.tracker.candidates import list_candidates


def require_candidate() -> None:
    """If no candidate exists yet, surface a one-shot modal directing the
    user to create their first candidate via the sidebar."""
    from streamlit.runtime.scriptrunner import get_script_run_ctx

    if get_script_run_ctx() is None:
        return
    if list_candidates():
        return

    @st.dialog("Create a candidate to continue")
    def _candidate_modal():
        st.write(
            "BRAINS Resume organises every artifact under a candidate. "
            "Use the **+ New candidate** expander in the sidebar to create "
            "your first one."
        )
        st.info("Open the sidebar on the left and expand **+ New candidate**.")

    _candidate_modal()


def main() -> None:
    st.set_page_config(
        page_title="BRAINS Resume Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_brand_css()
    render_sidebar()
    require_candidate()

    st.title("BRAINS Resume Dashboard")

    tabs = st.tabs([
        "Home",
        "Resumes",
        "Cover Letters",
        "JDs",
        "Applications",
        "Analytics",
        "Pacing",
        "Drift",
    ])

    with tabs[0]:
        home.render()
    with tabs[1]:
        resumes.render()
    with tabs[2]:
        cover_letters.render()
    with tabs[3]:
        jds.render()
    with tabs[4]:
        applications.render()
    with tabs[5]:
        analytics.render()
    with tabs[6]:
        pacing.render()
    with tabs[7]:
        drift_tab.render()


main()
```

- [ ] **Step 4: Delete the obsolete tab modules and their tests**

```bash
git rm scripts/dashboard/tabs/overview.py scripts/dashboard/tabs/workflows.py tests/dashboard/test_app_overview_render.py tests/dashboard/test_app_workflows_tab.py
```

- [ ] **Step 5: Find and fix any remaining references**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard -q`

Inspect every failure. Expected categories and fixes:
- Any test importing `scripts.dashboard.tabs.overview` or `tabs.workflows` — if the test is purely about removed functionality, delete it; if it tests a helper that was *relocated* (e.g. `_drift_tile_summary` is now `scripts.dashboard.widgets.tiles.drift_tile_summary`), update the import.
- Any non-test module importing `overview`/`workflows` — grep with `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -c "import subprocess"` is not needed; instead run a project-wide search for the strings `tabs.overview`, `tabs import` and `render_drift_tile`. The drift tile's only consumer was `overview.py` itself; if any other module imported `overview.render_drift_tile`, repoint it to `scripts.dashboard.widgets.tiles.render_tile_drift`.

Apply the minimal fix for each. Do not re-add removed functionality.

- [ ] **Step 6: Run the dashboard test suite**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard -q`
Expected: green (the new Home/widget tests pass; the obsolete Overview/Workflows tests are gone).

- [ ] **Step 7: Commit**

```bash
git add scripts/dashboard/app.py tests/dashboard/test_app_home.py
git add -A scripts/dashboard/tabs tests/dashboard
git commit -m "feat(dashboard): Home tab replaces Overview + Workflows; 9 tabs -> 8"
```

---

## Task 11: Version bump, CHANGELOG, full-suite green

**Files:**
- Modify: `scripts/outputs/io.py` (`_SKILL_VERSION`), `pyproject.toml`, `CHANGELOG.md`

- [ ] **Step 1: Run the full suite**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest -q`
Expected: all green. Investigate and fix any failure outside the dashboard tree (Phase 2 is dashboard-only and additive aside from the two deleted tabs; nothing else should break). If a failure is a genuine pre-existing issue unrelated to Phase 2, report it rather than masking it.

- [ ] **Step 2: Bump the version**

In `scripts/outputs/io.py`, change `_SKILL_VERSION = "2.0.0"` to `_SKILL_VERSION = "2.1.0"`.
In `pyproject.toml`, change the `version` field to `"2.1.0"`.

- [ ] **Step 3: Update CHANGELOG**

Add at the top of `CHANGELOG.md` (below the title line, above the `## v2.0.0` entry), matching the existing heading style:

```markdown
## v2.1.0 — 2026-05-20

### Added
- **Dashboard orchestration** — the dashboard is now an orchestration hub. A new **Home** tab is a customizable widget canvas: playbook cards, an in-progress-runs tracker, a computed next-actions worklist, a pipeline mini-board, reporting tiles, and a quick-launch panel.
- **Playbook engine** (shipped internally in the v2.1 line): five guided journeys — Apply to a job, Build a base resume, Improve a resume, Refresh LinkedIn, Career change — with auto-detected step progress (`scripts/playbooks/`, migration 0006).
- **Customize mode** — each candidate can add, remove, and reorder Home widgets; the layout persists per candidate.

### Changed
- The dashboard has eight tabs (was nine): the **Overview** and **Workflows** tabs are removed — their content is absorbed into the Home widget canvas.

### Removed
- The Overview tab's application-funnel chart, weekly sparkline cards, idle-state callouts, and pending/recent twin panels. The next-actions worklist and the recent-outcomes tile cover the same need; efficacy analysis remains on the Analytics tab.
```

- [ ] **Step 4: Run the full suite once more**

Run: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest -q`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add scripts/outputs/io.py pyproject.toml CHANGELOG.md
git commit -m "chore: bump to v2.1.0 — dashboard orchestration"
```

---

## Acceptance Criteria

A. `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest -q` is green across the whole suite.

B. Launching the dashboard lands on a **Home** tab; the tab bar has eight tabs; there is no Overview or Workflows tab.

C. The Home canvas renders the playbook cards, the in-progress widget, the worklist, the pipeline mini-board, and the reporting tiles from the default layout.

D. Starting a playbook from a card creates a `playbook_runs` row; the in-progress widget shows it and auto-advances handoff steps as artifacts land (Phase-1 behaviour, surfaced in the UI).

E. Customize mode toggles widgets on/off and reorders them; the layout persists per candidate across a dashboard restart (it is stored in `dashboard_layout`).

F. `scripts/dashboard/tabs/overview.py` and `tabs/workflows.py` no longer exist; nothing imports them.

---

## Out of Scope (Phase 3)

- Resume-first onboarding, the post-review clarifying form, migration 0007 (`candidate` intent columns) — Phase 3.
- Restoring the funnel/sparkline visualizations as opt-in widgets — only if the user requests it after seeing Phase 2.

---

## Self-Review

**Spec coverage (§6, §8):** §6.1 widget catalog → all 13 widgets across Tasks 2-6, registered in Task 7. §6.2 Customize mode (toggle + reorder, per-candidate persistence) → Task 9 + Task 1's `dashboard_layout` CRUD. §6.3 constraint (ordered list, no free-form placement) → the catalog/zone model, Task 7-8. §8 navigation (9 tabs → 8, Home absorbs Overview + Workflows, deep tabs remain) → Task 10. The playbook engine wiring (spec §4, Phase 1) → Task 2. Drift tile relocation → Task 5. The §8 "data-model addition" (intent columns) is explicitly Phase 3, not here.

**Placeholder scan:** No "TBD"/"add error handling"/"similar to Task N". Every code and test block is complete and literal. Task 10 Step 5 ("find remaining references") is a genuine investigation step with concrete instructions and a named fallback target (`render_tile_drift`), not a placeholder.

**Type consistency:** The widget render contract `render(candidate) -> None` is uniform across `playbook_widgets`, `worklist`, `pipeline`, `tiles`, `quick_launch`, and the `Widget.render` field. `get_saved_layout`/`save_layout` exchange `list[tuple[str, bool]]` consistently across `layout.py`, `catalog.resolve_layout`, `home.effective_layout`, and `customize.py`. `resolve_layout` returns `list[tuple[Widget, bool]]` consistently. `make_playbook_card_renderer` returns a `(candidate)->None` callable matching the contract. Playbook keys (`apply_to_job` etc.) and widget keys (`playbook_apply` etc.) are used identically in `catalog.py` and the tests.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-20-dashboard-orchestration-phase-2.md`. Two execution options:

1. **Subagent-Driven (recommended)** — a fresh subagent per task, two-stage review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session with checkpoints.

Which approach?
