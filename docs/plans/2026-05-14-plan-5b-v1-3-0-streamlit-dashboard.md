# Plan 5b — v1.3.0: Streamlit Dashboard

> **For implementers:** Checkbox (`- [ ]`) syntax. Work sequentially, mark steps as you go. Stage and commit after each task. **Never include third-party org or project credits in any file or commit message — BRAINS / BRAINS Trust / BRAINS Incubator only. Never include `Co-Authored-By` footers.** Conventional commits style.

**Goal:** Ship v1.3.0 — a local Streamlit dashboard that surfaces the tracker, JD-analyzer, and AI-signal data the user has been building toward. Single-page top-tab layout matching the user's TSE Tools visual reference, BRAINS Incubator branded, seven tabs (Overview, Resumes, Cover Letters, JDs, Applications, Analytics, Pacing) plus a sidebar for profile editing.

**Architecture:** Adds a new `scripts/dashboard/` package consuming the v1.2.0 tracker public API and the v1.2.1 AI-signal validator. Read-only except for sidebar profile.json edits. `streamlit` + `plotly` added as required dependencies. Launch via new `brains-resume-dashboard` CLI entry registered in `pyproject.toml [project.scripts]`. Pure data-prep functions split into `scripts/dashboard/prep/` so they are unit-testable without Streamlit.

**Tech Stack:** Python 3.10+, `streamlit>=1.30.0`, `plotly>=5.18.0` (new), existing `python-docx`, `pdfplumber`, `reportlab`, `pyyaml`, `pytest`.

**Spec reference:** [`docs/specs/2026-05-14-v1-3-0-streamlit-dashboard-design.md`](../specs/2026-05-14-v1-3-0-streamlit-dashboard-design.md)

**In scope for this plan:**

1. **Dashboard package** — `scripts/dashboard/` with `app.py`, `launch.py`, `style.py`, `data.py`, `tabs/`, `prep/`
2. **Streamlit + Plotly dependencies** added to `pyproject.toml`
3. **`brains-resume-dashboard` CLI entry** registered via `[project.scripts]`
4. **`/brains-dashboard` slash command** that prints the launch command (does not spawn the subprocess)
5. **`.streamlit/config.toml`** with dark-theme baseline + headless server config
6. **`data.py`** cached wrappers over `scripts.tracker.query`
7. **Four `prep/` modules** (TDD): `funnel.py`, `sparkline.py`, `trends.py`, `idle_states.py`
8. **`style.py`** BRAINS Incubator CSS injection (consults `brains-brand` skill at implementation time)
9. **Seven tab modules** in `scripts/dashboard/tabs/` (Overview is the heaviest; others are similar in shape)
10. **Sidebar** with focus areas + healthy weekly rate + pacing_notes editor + global refresh
11. **`pacing_notes` schema addition** to `Profile` dataclass and `profile.py` read/write helpers
12. **Streamlit smoke test** (`test_app_import.py`) + `AppTest` happy-path test (`test_app_overview_render.py`)
13. **Release polish** — SKILL.md updates (tooling-notes + slash-command count 15 → 16), README "Launching the dashboard" section, `brand-application.md` row, `claude-project-setup.md` note, CHANGELOG v1.3.0 entry, Claude Project bundle rebuild, version bump 1.2.1 → 1.3.0, `v1.3.0` git tag

**Out of scope (deferred):**

- Inline outcome editing in the dashboard (still via `/brains-track update <id>` CLI)
- Auto-launch from Claude Code (slash command prints the command; user keeps terminal control)
- Multi-page navigation via `pages/` directory (single-page with `st.tabs` matches TSE Tools)
- Sibling skills (interview prep, salary negotiation)
- MCP server for Claude Desktop

---

## Conventions used throughout this plan

- **Working directory:** `c:\Brains_Resume_Skill\`. All paths relative unless absolute is shown.
- **Tests live in:** `tests/` mirroring source structure. Dashboard tests in `tests/dashboard/`.
- **Python fixtures:** `tests/fixtures/*.py`.
- **Commit style:** conventional commits — `feat:`, `fix:`, `test:`, `docs:`, `build:`, `chore:`, `perf:`, `refactor:`. NEVER include `Co-Authored-By` footers (BRAINS-only attribution).
- **Identity-first language** throughout; no italics in body text; no third-party org or project proper-name references.
- **Testing rhythm:** write failing test → run to confirm failure → implement → run to confirm pass → commit. Don't skip the failure-confirmation step.
- **Virtual environment:** always work inside `.venv` — `.venv\Scripts\activate` (PowerShell) before running tests or scripts.
- **Streamlit testing constraint:** Most Streamlit-coupled UI code (tab modules) is not unit-testable in isolation; the `AppTest` smoke test in Task 19 provides happy-path coverage. Pure data-prep functions in `prep/` ARE fully unit-tested via TDD.

---

## Phase 1 — Foundation (Tasks 1-4)

The foundational scaffolding — dependencies, package skeleton, launch CLI, slash command. After Phase 1, the dashboard package exists and is launchable but renders only a placeholder. Subsequent phases fill in the data layer, styling, tabs, and sidebar.

---

## Task 1 — Pyproject deps + project-scripts entry

**Files:**

- Modify: `pyproject.toml`

### Steps

- [ ] **Step 1: Read pyproject.toml to find the existing dependencies section**

```powershell
.venv\Scripts\activate
Get-Content pyproject.toml
```

- [ ] **Step 2: Add streamlit and plotly to dependencies**

Find the `dependencies = [...]` block under `[project]`. Append two new entries:

```toml
dependencies = [
    "python-docx>=1.1.0",
    "pdfplumber>=0.11.0",
    "reportlab>=4.0.0",
    "trafilatura>=1.12.0",
    "pyyaml>=6.0",
    "streamlit>=1.30.0",
    "plotly>=5.18.0",
]
```

- [ ] **Step 3: Add the [project.scripts] entry**

After the `[project.optional-dependencies]` block (or anywhere after the main `[project]` table), add a new section:

```toml
[project.scripts]
brains-resume-dashboard = "scripts.dashboard.launch:main"
```

- [ ] **Step 4: Install the new dependencies**

```powershell
pip install -e ".[dev]"
```

Expected: streamlit and plotly install successfully. May take 1-2 minutes (streamlit has many transitive deps).

- [ ] **Step 5: Verify streamlit imports**

```powershell
python -c "import streamlit; import plotly; print('streamlit', streamlit.__version__); print('plotly', plotly.__version__)"
```

Expected: prints both version strings, exits 0.

- [ ] **Step 6: Run the existing suite to confirm no regressions**

```powershell
python -m pytest -q
```

Expected: 259 tests still pass (the new dependencies don't run any new tests yet).

- [ ] **Step 7: Commit**

```powershell
git add pyproject.toml
git commit -m "build: add streamlit and plotly dependencies for v1.3.0 dashboard"
```

---

## Task 2 — Dashboard package skeleton + Streamlit config

**Files:**

- Create: `scripts/dashboard/__init__.py`
- Create: `scripts/dashboard/app.py` (stub — full implementation comes in later phases)
- Create: `scripts/dashboard/tabs/__init__.py`
- Create: `scripts/dashboard/prep/__init__.py`
- Create: `.streamlit/config.toml`
- Create: `tests/dashboard/__init__.py`
- Create: `tests/dashboard/prep/__init__.py`

### Steps

- [ ] **Step 1: Create the dashboard package directories**

```powershell
New-Item -ItemType Directory -Path "scripts\dashboard" -Force
New-Item -ItemType Directory -Path "scripts\dashboard\tabs" -Force
New-Item -ItemType Directory -Path "scripts\dashboard\prep" -Force
New-Item -ItemType Directory -Path "tests\dashboard" -Force
New-Item -ItemType Directory -Path "tests\dashboard\prep" -Force
New-Item -ItemType Directory -Path ".streamlit" -Force
```

- [ ] **Step 2: Create the package init files**

Create `scripts/dashboard/__init__.py`:

```python
"""BRAINS Resume Skill — local Streamlit dashboard.

Reads from the v1.2.0 SQLite tracker via the scripts.tracker.query public API,
and from the v1.2.1 AI-signal validator. BRAINS Incubator branded. Read-only
except for sidebar profile.json edits (focus areas, healthy weekly rate,
pacing notes).
"""
```

Create `scripts/dashboard/tabs/__init__.py`:

```python
"""Per-tab modules for the dashboard.

Each module exposes a `render(container)` function that the main app.py
calls inside the matching st.tabs() block.
"""
```

Create `scripts/dashboard/prep/__init__.py`:

```python
"""Pure data-preparation functions for the dashboard.

These functions take query results in and return chart-ready data structures.
No Streamlit imports — fully unit-testable without the streamlit runtime.
"""
```

Create `tests/dashboard/__init__.py` and `tests/dashboard/prep/__init__.py` as empty files.

- [ ] **Step 3: Create the Streamlit config**

Create `.streamlit/config.toml`:

```toml
# BRAINS Resume Skill — Streamlit configuration.
# Dark-theme baseline; BRAINS Incubator colour accents applied via
# scripts/dashboard/style.py CSS injection.

[server]
headless = true
port = 8501

[browser]
gatherUsageStats = false

[theme]
base = "dark"
primaryColor = "#D99518"
backgroundColor = "#1A1A1A"
secondaryBackgroundColor = "#2D2D2D"
textColor = "#E8E8E8"
font = "sans serif"
```

- [ ] **Step 4: Create the app.py stub**

Create `scripts/dashboard/app.py`:

```python
"""Main Streamlit entry for the BRAINS Resume dashboard.

Run via the `brains-resume-dashboard` CLI entry point (see launch.py)
which invokes `streamlit run scripts/dashboard/app.py`.

This is the v1.3.0 stub — subsequent tasks fill in the data layer, styling,
seven tabs, and sidebar. For now, the app renders a title and a placeholder
message confirming the dashboard is reachable.
"""
import streamlit as st


def main() -> None:
    st.set_page_config(
        page_title="BRAINS Resume Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("BRAINS Resume Dashboard")
    st.caption("v1.3.0 — under construction")
    st.info(
        "Dashboard package skeleton is in place. Tab modules, sidebar, and "
        "data layer ship in later Plan 5b tasks."
    )


main()
```

(Note: Streamlit apps execute top-to-bottom on each render. The `main()` call at module bottom is intentional — not wrapped in `if __name__ == "__main__"` because Streamlit imports the module rather than running it directly.)

- [ ] **Step 5: Verify the package imports cleanly**

```powershell
python -c "from scripts.dashboard import app; print('OK')"
```

Expected: prints `OK` and exits 0. Streamlit's `set_page_config` will warn that it's called outside a Streamlit context — that's fine for the import-time check.

Actually since calling `main()` at module load will try to render — let's avoid that side-effect on import. Update `scripts/dashboard/app.py` to put the rendering inside `main()` but only call `main()` at the bottom when not under pytest:

Actually for Streamlit's expected behaviour, the call needs to happen on import. The Streamlit context is set up by `streamlit run` before the module is imported. For pytest import checks, the lack of Streamlit context just means the calls silently no-op or warn. The import itself succeeds.

So leave the structure as written. The Step 5 expectation is: prints `OK` (possibly with a Streamlit warning written to stderr — that's not a failure).

- [ ] **Step 6: Run the full suite to confirm no regressions**

```powershell
python -m pytest -q
```

Expected: 259 tests still pass.

- [ ] **Step 7: Commit**

```powershell
git add scripts/dashboard .streamlit tests/dashboard
git commit -m "feat: scaffold dashboard package and Streamlit config"
```

---

## Task 3 — Launch CLI

**Files:**

- Create: `scripts/dashboard/launch.py`

### Steps

- [ ] **Step 1: Write the launch CLI**

Create `scripts/dashboard/launch.py`:

```python
"""CLI entry point for the BRAINS Resume dashboard.

Registered in pyproject.toml [project.scripts] as `brains-resume-dashboard`.
After `pip install -e .`, the user runs the command from any terminal and
the dashboard launches on localhost:8501.

The launcher resolves the absolute path to app.py so the command works
regardless of the user's current working directory.
"""
import shutil
import subprocess
import sys
from pathlib import Path


APP_PATH = Path(__file__).parent / "app.py"


def main() -> int:
    """Launch the Streamlit dashboard. Returns the streamlit subprocess exit code."""
    if not APP_PATH.exists():
        sys.stderr.write(f"BRAINS Resume dashboard: app.py not found at {APP_PATH}\n")
        return 1

    streamlit_bin = shutil.which("streamlit")
    if streamlit_bin is None:
        sys.stderr.write(
            "BRAINS Resume dashboard: streamlit executable not on PATH. "
            "Reinstall the skill via `pip install -e .` to register dependencies.\n"
        )
        return 1

    print("BRAINS Resume Dashboard launching at http://localhost:8501")
    print("Press Ctrl+C in this terminal to stop the dashboard.")
    print()

    result = subprocess.run(
        [
            streamlit_bin,
            "run",
            str(APP_PATH),
            "--server.headless",
            "true",
            "--server.port",
            "8501",
        ]
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Verify the launcher script imports cleanly**

```powershell
python -c "from scripts.dashboard.launch import main; print(main.__doc__)"
```

Expected: prints the docstring of `main`, exits 0.

- [ ] **Step 3: Confirm `brains-resume-dashboard` is registered as a console script**

```powershell
Get-Command brains-resume-dashboard -ErrorAction SilentlyContinue
```

Expected: returns a command path (likely under `.venv\Scripts\`). If not found, reinstall:

```powershell
pip install -e ".[dev]"
```

Then re-check.

- [ ] **Step 4: Confirm the launcher does NOT auto-spawn streamlit on import**

```powershell
python -c "import scripts.dashboard.launch; print('imported without launching')"
```

Expected: prints `imported without launching` and exits immediately. No streamlit subprocess started.

- [ ] **Step 5: Run the full suite to confirm no regressions**

```powershell
python -m pytest -q
```

Expected: 259 tests still pass.

- [ ] **Step 6: Commit**

```powershell
git add scripts/dashboard/launch.py
git commit -m "feat: add brains-resume-dashboard CLI launcher"
```

---

## Task 4 — /brains-dashboard slash command

**Files:**

- Create: `commands/brains-dashboard.md`

### Steps

- [ ] **Step 1: Create the slash command file**

Create `commands/brains-dashboard.md`:

````markdown
---
description: Print the command to launch the BRAINS Resume dashboard in a browser
argument-hint: (no arguments)
---

Print the launch command for the BRAINS Resume dashboard. Do NOT attempt to spawn the streamlit subprocess from Claude Code — long-running processes are awkward for Claude Code to own, and the user keeps terminal control.

Output the following two lines verbatim:

```
Run: brains-resume-dashboard
Then open: http://localhost:8501
```

The dashboard runs entirely on localhost. Port 8501 is the Streamlit default. The user stops the dashboard by pressing Ctrl+C in the terminal where `brains-resume-dashboard` is running.

If the user reports that `brains-resume-dashboard` is not found on PATH, suggest:

```
pip install -e .
```

from the project root to register the CLI entry. The entry is declared in `pyproject.toml` under `[project.scripts]` as `brains-resume-dashboard = "scripts.dashboard.launch:main"`.
````

- [ ] **Step 2: Run the full suite to confirm no regressions**

```powershell
python -m pytest -q
```

Expected: 259 tests still pass.

- [ ] **Step 3: Commit**

```powershell
git add commands/brains-dashboard.md
git commit -m "feat: add brains-dashboard slash command"
```

---

## Phase 2 — Data layer + prep functions (Tasks 5-9)

`data.py` is the cached interface to `scripts.tracker.query`. The four `prep/` modules are pure functions that take query results and produce chart-ready data structures. Phase 2 has the most unit-test coverage of any phase — the prep functions are where the dashboard's analytical logic lives.

---

## Task 5 — data.py cached wrappers + tests

**Files:**

- Create: `scripts/dashboard/data.py`
- Create: `tests/dashboard/test_data.py`

### Steps

- [ ] **Step 1: Write the failing tests**

Create `tests/dashboard/test_data.py`:

```python
"""Tests for scripts/dashboard/data.py — the cached wrappers over tracker.query."""
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    """Each test gets an isolated empty tracker db."""
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path / "test.db"


def test_cached_list_applications_delegates_to_query(fresh_db):
    from scripts.dashboard.data import cached_list_applications
    # Empty db -> empty list
    result = cached_list_applications()
    assert result == []


def test_cached_list_applications_returns_application_rows(fresh_db):
    from scripts.dashboard.data import cached_list_applications
    from scripts.tracker.add import add_application, add_jd, add_resume_version
    rv = add_resume_version(file_path=None, template="hybrid", focus_areas=[])
    jd = add_jd(
        source="paste", source_ref=None, company="Example Corp",
        role_title="Senior Engineer", raw_text="x", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    add_application(
        jd_id=jd, resume_version_id=rv, cover_letter_id=None,
        submitted_at=datetime.now(), channel="direct",
    )
    result = cached_list_applications()
    assert len(result) == 1
    assert result[0].company == "Example Corp"


def test_cached_weekly_summary_delegates(fresh_db):
    from scripts.dashboard.data import cached_weekly_summary
    summary = cached_weekly_summary()
    assert summary.applications_count == 0


def test_cached_efficacy_by_template_delegates(fresh_db):
    from scripts.dashboard.data import cached_efficacy_by_template
    result = cached_efficacy_by_template()
    assert result == []


def test_cached_find_duplicates_delegates(fresh_db):
    from scripts.dashboard.data import cached_find_duplicates
    result = cached_find_duplicates("Example Corp", "Senior Engineer")
    assert result == []


def test_clear_all_caches_function_exists():
    """data.py must expose a function that clears every cached wrapper at once."""
    from scripts.dashboard.data import clear_all_caches
    # Should be callable and not raise.
    clear_all_caches()
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/dashboard/test_data.py -v
```

Expected: ImportError on `scripts.dashboard.data`.

- [ ] **Step 3: Write the implementation**

Create `scripts/dashboard/data.py`:

```python
"""Cached query wrappers for the dashboard.

Each function wraps a corresponding function in scripts.tracker.query with
@st.cache_data(ttl=60). Tabs import from here, never directly from
scripts.tracker.query. Manual refresh per tab calls .clear() on the matching
wrapper; clear_all_caches() flushes everything (used by the sidebar global
refresh button).

Profile reads/writes are NOT cached — they go directly through
scripts.tracker.profile because the values are rarely-changed and freshness
matters more than cache hit rate.
"""
from datetime import datetime
from typing import List, Optional

import streamlit as st

from scripts.tracker import query as _query
from scripts.tracker.models import EfficacyRow, WeeklySummary
from scripts.tracker.query import ApplicationRow


@st.cache_data(ttl=60)
def cached_list_applications(
    company: Optional[str] = None,
    since: Optional[datetime] = None,
    status: Optional[str] = None,
) -> List[ApplicationRow]:
    """Return active applications, filtered by criteria. Cached for 60s."""
    return _query.list_applications(company=company, since=since, status=status)


@st.cache_data(ttl=60)
def cached_weekly_summary(now: Optional[datetime] = None) -> WeeklySummary:
    """Return the last-7-days summary with pacing comparison."""
    return _query.weekly_summary(now=now)


@st.cache_data(ttl=60)
def cached_efficacy_by_template() -> List[EfficacyRow]:
    """Return per-template efficacy aggregations."""
    return _query.efficacy_by_template()


@st.cache_data(ttl=60)
def cached_find_duplicates(
    company: str,
    role_title: str,
    within_days: int = 60,
) -> List[ApplicationRow]:
    """Return applications to the same company+role within the window."""
    return _query.find_duplicates(company, role_title, within_days=within_days)


def clear_all_caches() -> None:
    """Clear every cached wrapper at once. Called by the sidebar global refresh."""
    cached_list_applications.clear()
    cached_weekly_summary.clear()
    cached_efficacy_by_template.clear()
    cached_find_duplicates.clear()
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/dashboard/test_data.py -v
```

Expected: 6 tests pass.

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 265 tests pass (259 + 6).

- [ ] **Step 6: Commit**

```powershell
git add scripts/dashboard/data.py tests/dashboard/test_data.py
git commit -m "feat: add dashboard data.py cached query wrappers"
```

---

## Task 6 — prep/funnel.py (TDD)

**Files:**

- Create: `scripts/dashboard/prep/funnel.py`
- Create: `tests/dashboard/prep/test_funnel.py`

### Steps

- [ ] **Step 1: Write the failing tests**

Create `tests/dashboard/prep/test_funnel.py`:

```python
"""Tests for scripts/dashboard/prep/funnel.py — funnel-chart data computation."""
from scripts.dashboard.prep.funnel import compute_funnel_data


def _row(latest_outcome=None):
    """Small ApplicationRow stand-in for testing."""
    class _Row:
        pass
    r = _Row()
    r.latest_outcome = latest_outcome
    return r


def test_empty_input_returns_zero_funnel():
    data = compute_funnel_data([])
    assert data["Applications"] == 0
    assert data["Callbacks"] == 0
    assert data["Interviews"] == 0
    assert data["Offers"] == 0
    assert data["Rejections"] == 0


def test_application_counted():
    data = compute_funnel_data([_row()])
    assert data["Applications"] == 1
    assert data["Callbacks"] == 0


def test_callback_counted():
    data = compute_funnel_data([_row(latest_outcome="callback")])
    assert data["Applications"] == 1
    assert data["Callbacks"] == 1


def test_interview_events_count_as_interview_stage():
    rows = [
        _row(latest_outcome="phone_screen"),
        _row(latest_outcome="first_round"),
        _row(latest_outcome="second_round"),
        _row(latest_outcome="take_home"),
    ]
    data = compute_funnel_data(rows)
    assert data["Applications"] == 4
    assert data["Interviews"] == 4


def test_offer_counted():
    data = compute_funnel_data([_row(latest_outcome="offer")])
    assert data["Applications"] == 1
    assert data["Offers"] == 1


def test_rejection_counted():
    data = compute_funnel_data([_row(latest_outcome="rejection")])
    assert data["Applications"] == 1
    assert data["Rejections"] == 1


def test_ghosted_and_withdrew_not_counted_in_funnel_advance_stages():
    """Ghosted/withdrew are terminal but don't advance the funnel."""
    rows = [
        _row(latest_outcome="ghosted"),
        _row(latest_outcome="withdrew"),
    ]
    data = compute_funnel_data(rows)
    assert data["Applications"] == 2
    assert data["Callbacks"] == 0
    assert data["Interviews"] == 0
    assert data["Offers"] == 0
    assert data["Rejections"] == 0


def test_funnel_data_keys_in_expected_order():
    """The returned dict should iterate in funnel-stage order for chart rendering."""
    data = compute_funnel_data([])
    assert list(data.keys()) == [
        "Applications", "Callbacks", "Interviews", "Offers", "Rejections",
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/dashboard/prep/test_funnel.py -v
```

Expected: ImportError on `scripts.dashboard.prep.funnel`.

- [ ] **Step 3: Write the implementation**

Create `scripts/dashboard/prep/funnel.py`:

```python
"""Funnel-chart data computation for the Overview tab.

Counts applications and the stages they have advanced to. Each application
contributes once to "Applications". An application with a callback event
contributes to "Callbacks". Interview events (phone_screen / first_round /
second_round / take_home) contribute to "Interviews". Offers and rejections
are terminal categories. Ghosted/withdrew are terminal but don't advance.

Pure function — no Streamlit imports, no I/O.
"""
from typing import List


INTERVIEW_EVENT_TYPES = {"phone_screen", "first_round", "second_round", "take_home"}


def compute_funnel_data(rows: List) -> dict:
    """Aggregate ApplicationRow objects into funnel-stage counts.

    Returns a dict with keys in funnel order: Applications, Callbacks,
    Interviews, Offers, Rejections.
    """
    counts = {
        "Applications": len(rows),
        "Callbacks": 0,
        "Interviews": 0,
        "Offers": 0,
        "Rejections": 0,
    }
    for r in rows:
        outcome = getattr(r, "latest_outcome", None)
        if outcome == "callback":
            counts["Callbacks"] += 1
        elif outcome in INTERVIEW_EVENT_TYPES:
            counts["Interviews"] += 1
        elif outcome == "offer":
            counts["Offers"] += 1
        elif outcome == "rejection":
            counts["Rejections"] += 1
    return counts
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/dashboard/prep/test_funnel.py -v
```

Expected: 8 tests pass.

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 273 tests pass (265 + 8).

- [ ] **Step 6: Commit**

```powershell
git add scripts/dashboard/prep/funnel.py tests/dashboard/prep/test_funnel.py
git commit -m "feat: add prep/funnel.py funnel-data computation"
```

---

## Task 7 — prep/sparkline.py (TDD)

**Files:**

- Create: `scripts/dashboard/prep/sparkline.py`
- Create: `tests/dashboard/prep/test_sparkline.py`

### Steps

- [ ] **Step 1: Write the failing tests**

Create `tests/dashboard/prep/test_sparkline.py`:

```python
"""Tests for scripts/dashboard/prep/sparkline.py — sparkline data preparation."""
from datetime import date, datetime, timedelta

from scripts.dashboard.prep.sparkline import (
    applications_per_week_8w,
    callback_rate_rolling_30d,
)


def _row(submitted_at, latest_outcome=None):
    class _Row:
        pass
    r = _Row()
    r.submitted_at = submitted_at.isoformat() if hasattr(submitted_at, "isoformat") else submitted_at
    r.latest_outcome = latest_outcome
    return r


def test_applications_per_week_empty_returns_8_zeros():
    data = applications_per_week_8w([], now=datetime(2026, 5, 14))
    assert len(data) == 8
    assert all(d["count"] == 0 for d in data)


def test_applications_per_week_distributes_by_week():
    now = datetime(2026, 5, 14)
    rows = [
        _row(now - timedelta(days=2)),   # this week
        _row(now - timedelta(days=8)),   # 1 week ago
        _row(now - timedelta(days=10)),  # 1-2 weeks ago
        _row(now - timedelta(days=60)),  # outside 8w window
    ]
    data = applications_per_week_8w(rows, now=now)
    counts = [d["count"] for d in data]
    # Most recent week should have the count-of-2-days-ago application
    assert counts[-1] >= 1


def test_applications_per_week_includes_week_starting_dates():
    data = applications_per_week_8w([], now=datetime(2026, 5, 14))
    for entry in data:
        assert "week_starting" in entry
        # Each week_starting should be 7 days apart
    for i in range(len(data) - 1):
        d1 = date.fromisoformat(data[i]["week_starting"])
        d2 = date.fromisoformat(data[i + 1]["week_starting"])
        assert (d2 - d1).days == 7


def test_callback_rate_empty_returns_empty_series():
    data = callback_rate_rolling_30d([], now=datetime(2026, 5, 14))
    assert data == []


def test_callback_rate_with_callbacks():
    now = datetime(2026, 5, 14)
    rows = [
        _row(now - timedelta(days=5), latest_outcome="callback"),
        _row(now - timedelta(days=10), latest_outcome="callback"),
        _row(now - timedelta(days=20)),  # no callback
        _row(now - timedelta(days=80)),  # outside window
    ]
    data = callback_rate_rolling_30d(rows, now=now)
    # Should produce a series of {date, rate} entries
    assert len(data) > 0
    for entry in data:
        assert "date" in entry
        assert "rate" in entry
        assert 0.0 <= entry["rate"] <= 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/dashboard/prep/test_sparkline.py -v
```

Expected: ImportError on `scripts.dashboard.prep.sparkline`.

- [ ] **Step 3: Write the implementation**

Create `scripts/dashboard/prep/sparkline.py`:

```python
"""Sparkline-data preparation for the Overview tab.

Three sparkline cards on Overview:
  - AI-signal trend over last 30 days (not in this module — requires resume
    versions + ai_signal_check; computed separately at Overview render time)
  - Applications per week, last 8 weeks
  - Callback rate rolling 30-day, last 90 days

These functions are pure — they take ApplicationRow lists in and return
chart-ready dicts/lists out. No Streamlit imports.
"""
from datetime import date, datetime, timedelta
from typing import List


def applications_per_week_8w(rows: List, now: datetime = None) -> List[dict]:
    """Bucket rows by week for the last 8 weeks.

    Returns a list of 8 dicts: [{week_starting: "YYYY-MM-DD", count: N}, ...]
    Order: oldest week first, most recent week last (for chart left-to-right).
    """
    if now is None:
        now = datetime.now()
    # Find the Monday of the current week
    today = now.date()
    days_since_monday = today.weekday()
    this_monday = today - timedelta(days=days_since_monday)
    # 8 weeks back from the current Monday
    weeks = [
        this_monday - timedelta(days=7 * (7 - i))
        for i in range(8)
    ]
    # Initialise counts
    by_week = {w.isoformat(): 0 for w in weeks}
    for r in rows:
        submitted_str = getattr(r, "submitted_at", "")
        if not submitted_str:
            continue
        try:
            submitted = datetime.fromisoformat(submitted_str).date()
        except (ValueError, TypeError):
            continue
        # Which Monday-week does this row belong to?
        row_monday = submitted - timedelta(days=submitted.weekday())
        key = row_monday.isoformat()
        if key in by_week:
            by_week[key] += 1
    return [{"week_starting": w.isoformat(), "count": by_week[w.isoformat()]} for w in weeks]


def callback_rate_rolling_30d(rows: List, now: datetime = None) -> List[dict]:
    """Rolling 30-day callback rate over the last 90 days.

    For each day in the last 90: rate = (callbacks in prior 30d) / (apps in prior 30d).
    Returns [] if no applications in the 90-day window.
    """
    if now is None:
        now = datetime.now()
    today = now.date()
    window_start = today - timedelta(days=90)

    # Gather rows in the 120-day window (so 30d-prior at window_start works)
    extended_window_start = window_start - timedelta(days=30)
    relevant = []
    for r in rows:
        submitted_str = getattr(r, "submitted_at", "")
        if not submitted_str:
            continue
        try:
            submitted = datetime.fromisoformat(submitted_str).date()
        except (ValueError, TypeError):
            continue
        if submitted >= extended_window_start:
            relevant.append((submitted, getattr(r, "latest_outcome", None)))

    if not relevant:
        return []

    series = []
    for i in range(90):
        day = window_start + timedelta(days=i)
        prior_30_start = day - timedelta(days=30)
        apps = [s for s, _ in relevant if prior_30_start <= s < day]
        if not apps:
            continue
        callbacks = sum(1 for s, o in relevant if prior_30_start <= s < day and o == "callback")
        rate = callbacks / len(apps)
        series.append({"date": day.isoformat(), "rate": rate})
    return series
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/dashboard/prep/test_sparkline.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 278 tests pass (273 + 5).

- [ ] **Step 6: Commit**

```powershell
git add scripts/dashboard/prep/sparkline.py tests/dashboard/prep/test_sparkline.py
git commit -m "feat: add prep/sparkline.py — applications-per-week and callback-rate trends"
```

---

## Task 8 — prep/trends.py (TDD)

**Files:**

- Create: `scripts/dashboard/prep/trends.py`
- Create: `tests/dashboard/prep/test_trends.py`

### Steps

- [ ] **Step 1: Write the failing tests**

Create `tests/dashboard/prep/test_trends.py`:

```python
"""Tests for scripts/dashboard/prep/trends.py — weekly aggregation helpers."""
from datetime import datetime, timedelta

from scripts.dashboard.prep.trends import (
    applications_this_week_count,
    callback_count_last_n_days,
    interview_count_last_n_days,
)


def _row(submitted_at=None, latest_outcome=None):
    class _Row:
        pass
    r = _Row()
    r.submitted_at = submitted_at.isoformat() if submitted_at and hasattr(submitted_at, "isoformat") else submitted_at
    r.latest_outcome = latest_outcome
    return r


def test_applications_this_week_zero_on_empty_input():
    now = datetime(2026, 5, 14)
    assert applications_this_week_count([], now=now) == 0


def test_applications_this_week_counts_rows_in_last_7_days():
    now = datetime(2026, 5, 14)
    rows = [
        _row(submitted_at=now - timedelta(days=1)),
        _row(submitted_at=now - timedelta(days=3)),
        _row(submitted_at=now - timedelta(days=10)),  # outside window
    ]
    assert applications_this_week_count(rows, now=now) == 2


def test_callback_count_last_30d():
    now = datetime(2026, 5, 14)
    rows = [
        _row(submitted_at=now - timedelta(days=5), latest_outcome="callback"),
        _row(submitted_at=now - timedelta(days=10), latest_outcome="callback"),
        _row(submitted_at=now - timedelta(days=15), latest_outcome="rejection"),
        _row(submitted_at=now - timedelta(days=40), latest_outcome="callback"),  # outside
    ]
    assert callback_count_last_n_days(rows, days=30, now=now) == 2


def test_interview_count_aggregates_interview_event_types():
    now = datetime(2026, 5, 14)
    rows = [
        _row(submitted_at=now - timedelta(days=5), latest_outcome="phone_screen"),
        _row(submitted_at=now - timedelta(days=5), latest_outcome="first_round"),
        _row(submitted_at=now - timedelta(days=5), latest_outcome="second_round"),
        _row(submitted_at=now - timedelta(days=5), latest_outcome="take_home"),
        _row(submitted_at=now - timedelta(days=5), latest_outcome="callback"),  # not interview
        _row(submitted_at=now - timedelta(days=5), latest_outcome="offer"),     # not interview
    ]
    assert interview_count_last_n_days(rows, days=30, now=now) == 4
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/dashboard/prep/test_trends.py -v
```

Expected: ImportError on `scripts.dashboard.prep.trends`.

- [ ] **Step 3: Write the implementation**

Create `scripts/dashboard/prep/trends.py`:

```python
"""Weekly/rolling aggregation helpers for the Overview tab tiles.

Each function takes a list of ApplicationRow objects and a `now` timestamp,
returns a scalar count. Pure — no Streamlit imports, no I/O.
"""
from datetime import datetime, timedelta
from typing import List


INTERVIEW_EVENT_TYPES = {"phone_screen", "first_round", "second_round", "take_home"}


def _row_submitted_within(row, days: int, now: datetime) -> bool:
    submitted_str = getattr(row, "submitted_at", "")
    if not submitted_str:
        return False
    try:
        submitted = datetime.fromisoformat(submitted_str)
    except (ValueError, TypeError):
        return False
    return submitted >= now - timedelta(days=days)


def applications_this_week_count(rows: List, now: datetime = None) -> int:
    """Count rows submitted in the last 7 days."""
    if now is None:
        now = datetime.now()
    return sum(1 for r in rows if _row_submitted_within(r, 7, now))


def callback_count_last_n_days(rows: List, days: int = 30, now: datetime = None) -> int:
    """Count rows submitted in the last N days with latest_outcome == 'callback'."""
    if now is None:
        now = datetime.now()
    return sum(
        1 for r in rows
        if _row_submitted_within(r, days, now)
        and getattr(r, "latest_outcome", None) == "callback"
    )


def interview_count_last_n_days(rows: List, days: int = 30, now: datetime = None) -> int:
    """Count rows in the last N days whose latest_outcome is an interview event."""
    if now is None:
        now = datetime.now()
    return sum(
        1 for r in rows
        if _row_submitted_within(r, days, now)
        and getattr(r, "latest_outcome", None) in INTERVIEW_EVENT_TYPES
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/dashboard/prep/test_trends.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 282 tests pass (278 + 4).

- [ ] **Step 6: Commit**

```powershell
git add scripts/dashboard/prep/trends.py tests/dashboard/prep/test_trends.py
git commit -m "feat: add prep/trends.py — weekly aggregation helpers"
```

---

## Task 9 — prep/idle_states.py (TDD)

**Files:**

- Create: `scripts/dashboard/prep/idle_states.py`
- Create: `tests/dashboard/prep/test_idle_states.py`

### Steps

- [ ] **Step 1: Write the failing tests**

Create `tests/dashboard/prep/test_idle_states.py`:

```python
"""Tests for scripts/dashboard/prep/idle_states.py — "no anomalies today" callout detection."""
from datetime import datetime, timedelta

from scripts.dashboard.prep.idle_states import (
    detect_idle_states,
)


def _row(submitted_at=None, latest_outcome=None):
    class _Row:
        pass
    r = _Row()
    r.submitted_at = submitted_at.isoformat() if submitted_at and hasattr(submitted_at, "isoformat") else submitted_at
    r.latest_outcome = latest_outcome
    return r


def test_no_applications_this_week_returns_callout():
    now = datetime(2026, 5, 14)
    # Old applications outside the 7d window
    rows = [_row(submitted_at=now - timedelta(days=30), latest_outcome="callback")]
    callouts = detect_idle_states(rows, now=now)
    assert any("No applications submitted this week" in c for c in callouts)


def test_applications_this_week_suppresses_no_applications_callout():
    now = datetime(2026, 5, 14)
    rows = [_row(submitted_at=now - timedelta(days=2))]
    callouts = detect_idle_states(rows, now=now)
    assert not any("No applications submitted this week" in c for c in callouts)


def test_all_terminal_outcomes_returns_no_pending_callout():
    now = datetime(2026, 5, 14)
    rows = [
        _row(submitted_at=now - timedelta(days=30), latest_outcome="offer"),
        _row(submitted_at=now - timedelta(days=30), latest_outcome="rejection"),
        _row(submitted_at=now - timedelta(days=30), latest_outcome="withdrew"),
    ]
    callouts = detect_idle_states(rows, now=now)
    assert any("No pending outcomes" in c for c in callouts)


def test_some_pending_outcomes_suppresses_no_pending_callout():
    now = datetime(2026, 5, 14)
    rows = [
        _row(submitted_at=now - timedelta(days=30), latest_outcome="offer"),
        _row(submitted_at=now - timedelta(days=10), latest_outcome=None),  # pending
    ]
    callouts = detect_idle_states(rows, now=now)
    assert not any("No pending outcomes" in c for c in callouts)


def test_empty_rows_returns_no_applications_callout():
    now = datetime(2026, 5, 14)
    callouts = detect_idle_states([], now=now)
    assert any("No applications submitted this week" in c for c in callouts)


def test_callouts_returned_as_list_of_strings():
    callouts = detect_idle_states([], now=datetime(2026, 5, 14))
    assert isinstance(callouts, list)
    for c in callouts:
        assert isinstance(c, str)
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/dashboard/prep/test_idle_states.py -v
```

Expected: ImportError on `scripts.dashboard.prep.idle_states`.

- [ ] **Step 3: Write the implementation**

Create `scripts/dashboard/prep/idle_states.py`:

```python
"""Idle-state callout detection for the Overview tab.

When the user has no current activity to report, surface a positive callout
rather than an empty void. Three callout types:

  1. "No applications submitted this week" — when 0 applications in last 7 days
  2. "No pending outcomes — every application has been responded to" — when
     every non-archived application has a terminal outcome
  3. (Future) "AI-signal score consistently low" — would require resume-version
     scoring across history; deferred until Overview tab can pass that data in

Returns a list of strings; render order is the order of this list.
"""
from datetime import datetime, timedelta
from typing import List


TERMINAL_OUTCOMES = {"offer", "rejection", "withdrew", "ghosted"}


def _row_submitted_within(row, days: int, now: datetime) -> bool:
    submitted_str = getattr(row, "submitted_at", "")
    if not submitted_str:
        return False
    try:
        submitted = datetime.fromisoformat(submitted_str)
    except (ValueError, TypeError):
        return False
    return submitted >= now - timedelta(days=days)


def detect_idle_states(rows: List, now: datetime = None) -> List[str]:
    """Return callout strings for whichever idle states currently apply."""
    if now is None:
        now = datetime.now()
    callouts: List[str] = []

    # Callout 1: no applications this week
    if not any(_row_submitted_within(r, 7, now) for r in rows):
        callouts.append(
            "No applications submitted this week — sensory-bandwidth respected."
        )

    # Callout 2: no pending outcomes
    if rows:
        all_terminal = all(
            getattr(r, "latest_outcome", None) in TERMINAL_OUTCOMES
            for r in rows
        )
        if all_terminal:
            callouts.append(
                "No pending outcomes — every application has been responded to."
            )

    return callouts
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/dashboard/prep/test_idle_states.py -v
```

Expected: 6 tests pass.

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 288 tests pass (282 + 6).

- [ ] **Step 6: Commit**

```powershell
git add scripts/dashboard/prep/idle_states.py tests/dashboard/prep/test_idle_states.py
git commit -m "feat: add prep/idle_states.py — positive idle-state callout detection"
```

---

## Phase 3 — Style + tabs (Tasks 10-17)

Phase 3 builds the visible dashboard. Task 10 establishes the visual identity. Tasks 11-17 build the seven tabs. The Overview tab (Task 11) is the heaviest — it combines tiles, sparklines, funnel, idle-state callouts, and twin side-by-side panels.

---

## Task 10 — style.py CSS injection (BRAINS Incubator branding)

**Files:**

- Create: `scripts/dashboard/style.py`

### Steps

- [ ] **Step 1: Consult the brains-brand skill for BRAINS Incubator specs**

At implementation time, invoke the `brains-brand` skill via the Skill tool to retrieve current Incubator-specific specs. The skill is the authoritative source. Note any deltas between BRAINS parent and BRAINS Incubator brand (typically: same Gold Deep `#D99518`, same typography, but Incubator may have a distinct mark variant or footer credit line).

For this plan: write the implementation against the documented BRAINS brand spec (Gold Deep, Atkinson Hyperlegible, dark base). The implementer adjusts to Incubator-specific tweaks based on the brand-skill output.

- [ ] **Step 2: Write the implementation**

Create `scripts/dashboard/style.py`:

```python
"""BRAINS Incubator branding for the Streamlit dashboard.

Applied via CSS injection at app startup by calling inject_brand_css() once
from app.py. References the brand spec documented in
references/brand-application.md.

At implementation time, the brains-brand skill was consulted for the
current BRAINS Incubator spec. The values below match that spec; update
this module if the spec changes in future.
"""
import streamlit as st


# ---- Brand constants ---------------------------------------------------------

GOLD_DEEP = "#D99518"
BG_DARK = "#1A1A1A"
BG_PANEL = "#2D2D2D"
TEXT_PRIMARY = "#E8E8E8"
TEXT_MUTED = "#A0A0A0"
ACCENT_POSITIVE = "#7ABA7A"  # subdued green for callbacks
ACCENT_WARNING = "#E0A040"   # amber for pacing-above-target
ACCENT_NEGATIVE = "#C76060"  # subdued red for rejections


BRAND_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Inter:wght@700&display=swap');

html, body, [class*="css"]  {{
    font-family: 'Atkinson Hyperlegible', sans-serif;
}}

h1, h2, h3, h4, h5, h6 {{
    font-family: 'Inter', sans-serif;
    color: {GOLD_DEEP};
}}

/* Streamlit tab styling — top nav bar */
.stTabs [data-baseweb="tab-list"] {{
    border-bottom: 2px solid {GOLD_DEEP};
    background-color: {BG_DARK};
}}
.stTabs [data-baseweb="tab"] {{
    color: {TEXT_PRIMARY};
    background-color: transparent;
    font-weight: 700;
}}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    color: {GOLD_DEEP};
    border-bottom: 3px solid {GOLD_DEEP};
}}

/* Metric tile styling */
[data-testid="stMetricValue"] {{
    color: {TEXT_PRIMARY};
    font-family: 'Inter', sans-serif;
}}
[data-testid="stMetricDelta"] {{
    color: {GOLD_DEEP};
}}
[data-testid="stMetricLabel"] {{
    color: {TEXT_MUTED};
    font-family: 'Atkinson Hyperlegible', sans-serif;
}}

/* Sidebar styling */
[data-testid="stSidebar"] {{
    background-color: {BG_PANEL};
    border-right: 1px solid {GOLD_DEEP};
}}

/* Buttons — Gold Deep primary */
.stButton button {{
    background-color: {BG_PANEL};
    color: {GOLD_DEEP};
    border: 1px solid {GOLD_DEEP};
}}
.stButton button:hover {{
    background-color: {GOLD_DEEP};
    color: {BG_DARK};
}}

/* Success callouts — Gold Deep instead of default green */
[data-testid="stAlert"][data-baseweb="notification"][kind="success"] {{
    background-color: rgba(217, 149, 24, 0.15);
    border-left: 4px solid {GOLD_DEEP};
}}

/* DataFrame styling */
[data-testid="stDataFrame"] {{
    background-color: {BG_PANEL};
}}
</style>
"""


def inject_brand_css() -> None:
    """Inject BRAINS Incubator CSS. Call once at app startup."""
    st.markdown(BRAND_CSS, unsafe_allow_html=True)


def footer() -> None:
    """Render the BRAINS Incubator origin-credit footer."""
    st.markdown(
        "<div style='text-align:center; color:#A0A0A0; font-size:0.85em; padding-top:2em;'>"
        "BRAINS Incubator · Built by neurodivergent minds, for neurodivergent people."
        "</div>",
        unsafe_allow_html=True,
    )
```

- [ ] **Step 3: Verify the style module imports cleanly**

```powershell
python -c "from scripts.dashboard.style import inject_brand_css, footer, GOLD_DEEP; print('Gold Deep:', GOLD_DEEP)"
```

Expected: prints `Gold Deep: #D99518`, exits 0.

- [ ] **Step 4: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 288 tests still pass (style.py has no tests of its own — visual styling is verified via the AppTest in Task 19).

- [ ] **Step 5: Commit**

```powershell
git add scripts/dashboard/style.py
git commit -m "feat: add BRAINS Incubator branding CSS injection for dashboard"
```

---

## Task 11 — Overview tab

**Files:**

- Create: `scripts/dashboard/tabs/overview.py`

The heaviest tab module. Combines all four prep functions, plotly funnel chart, summary tile row, sparkline cards, idle-state callouts, and twin side-by-side panels.

### Steps

- [ ] **Step 1: Write the implementation**

Create `scripts/dashboard/tabs/overview.py`:

```python
"""Overview tab — the dashboard's landing page.

Top-to-bottom:
  1. Summary tile row (Applications / Callbacks / Interviews / Offers / Pacing)
  2. Mini sparkline cards (Apps-per-week, Callback rate trend)
  3. Idle-state callouts when applicable
  4. Plotly funnel chart
  5. Twin side-by-side panels (Pending callbacks, Recent interview activity)
"""
from datetime import datetime, timedelta

import plotly.graph_objects as go
import streamlit as st

from scripts.dashboard.data import (
    cached_list_applications,
    cached_weekly_summary,
)
from scripts.dashboard.prep.funnel import compute_funnel_data
from scripts.dashboard.prep.idle_states import detect_idle_states
from scripts.dashboard.prep.sparkline import (
    applications_per_week_8w,
    callback_rate_rolling_30d,
)
from scripts.dashboard.prep.trends import (
    applications_this_week_count,
    callback_count_last_n_days,
    interview_count_last_n_days,
)
from scripts.dashboard.style import GOLD_DEEP
from scripts.tracker.profile import read_profile


INTERVIEW_EVENT_TYPES = {"phone_screen", "first_round", "second_round", "take_home"}
TERMINAL_OUTCOMES = {"offer", "rejection", "withdrew"}


def render() -> None:
    """Render the Overview tab content."""
    if st.button("↻ Refresh", key="overview_refresh"):
        cached_list_applications.clear()
        cached_weekly_summary.clear()

    rows = cached_list_applications()
    weekly = cached_weekly_summary()
    profile = read_profile()
    now = datetime.now()

    _render_summary_tiles(rows, weekly, profile, now)
    st.markdown("---")
    _render_sparkline_cards(rows, now)
    st.markdown("---")
    _render_idle_states(rows, now)
    _render_funnel(rows)
    st.markdown("---")
    _render_twin_panels(rows, now)


def _render_summary_tiles(rows, weekly, profile, now) -> None:
    """Five-tile row: Applications / Callbacks / Interviews / Offers / Pacing."""
    total_apps = len(rows)
    callbacks_lifetime = sum(1 for r in rows if r.latest_outcome == "callback")
    callbacks_last_30 = callback_count_last_n_days(rows, days=30, now=now)
    interviews_last_30 = interview_count_last_n_days(rows, days=30, now=now)
    offers_lifetime = sum(1 for r in rows if r.latest_outcome == "offer")
    apps_this_week = applications_this_week_count(rows, now=now)

    callback_rate = (callbacks_lifetime / total_apps * 100) if total_apps else 0
    interview_rate = (
        sum(1 for r in rows if r.latest_outcome in INTERVIEW_EVENT_TYPES)
        / total_apps * 100
    ) if total_apps else 0

    target = profile.healthy_weekly_rate
    pacing_label = f"{apps_this_week}"
    if target is not None:
        pacing_label = f"{apps_this_week} / {target}"
        delta = apps_this_week - target
        pacing_delta = f"{delta:+d} vs target"
    else:
        pacing_delta = "no target set"

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric(label="Applications", value=total_apps, delta=f"{apps_this_week} this week")
    col2.metric(
        label="Callbacks",
        value=callbacks_lifetime,
        delta=f"{callback_rate:.0f}% rate",
    )
    col3.metric(
        label="Interviews",
        value=interviews_last_30,
        delta=f"{interview_rate:.0f}% rate",
    )
    col4.metric(label="Offers", value=offers_lifetime)
    col5.metric(label="Pacing (this week)", value=pacing_label, delta=pacing_delta)


def _render_sparkline_cards(rows, now) -> None:
    """Two sparkline cards: apps-per-week, callback-rate trend."""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Applications per week (last 8 weeks)**")
        data = applications_per_week_8w(rows, now=now)
        fig = go.Figure(
            go.Bar(
                x=[d["week_starting"] for d in data],
                y=[d["count"] for d in data],
                marker_color=GOLD_DEEP,
            )
        )
        fig.update_layout(
            height=140,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**Callback rate (rolling 30d)**")
        data = callback_rate_rolling_30d(rows, now=now)
        if not data:
            st.caption("Not enough data yet — submit more applications to see a trend.")
        else:
            fig = go.Figure(
                go.Scatter(
                    x=[d["date"] for d in data],
                    y=[d["rate"] for d in data],
                    mode="lines",
                    line=dict(color=GOLD_DEEP, width=2),
                )
            )
            fig.update_layout(
                height=140,
                margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)


def _render_idle_states(rows, now) -> None:
    callouts = detect_idle_states(rows, now=now)
    for c in callouts:
        st.success(c)


def _render_funnel(rows) -> None:
    st.subheader("Application funnel")
    data = compute_funnel_data(rows)
    fig = go.Figure(
        go.Funnel(
            y=list(data.keys()),
            x=list(data.values()),
            marker={"color": [GOLD_DEEP, GOLD_DEEP, GOLD_DEEP, GOLD_DEEP, "#5A3A3A"]},
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_twin_panels(rows, now) -> None:
    """Pending callbacks (left) and Recent interview activity (right)."""
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Pending callbacks")
        cutoff = now - timedelta(days=30)
        pending = [
            r for r in rows
            if datetime.fromisoformat(r.submitted_at) >= cutoff
            and r.latest_outcome is None
        ]
        if not pending:
            st.caption("Nothing pending in the last 30 days.")
        else:
            for r in pending[:10]:
                days_since = (now - datetime.fromisoformat(r.submitted_at)).days
                st.markdown(
                    f"**{r.company}** — {r.role_title} · {days_since}d ago · {r.channel}"
                )

    with col_right:
        st.subheader("Recent interview activity")
        recent_cutoff = now - timedelta(days=14)
        recent = [
            r for r in rows
            if r.latest_outcome in INTERVIEW_EVENT_TYPES
        ]
        if not recent:
            st.caption("No interview events in the last 14 days.")
        else:
            for r in recent[:10]:
                st.markdown(
                    f"**{r.company}** — {r.role_title} · {r.latest_outcome}"
                )
```

- [ ] **Step 2: Verify the module imports cleanly**

```powershell
python -c "from scripts.dashboard.tabs.overview import render; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 288 tests still pass (Overview tab has no unit tests — covered by the AppTest in Task 19).

- [ ] **Step 4: Commit**

```powershell
git add scripts/dashboard/tabs/overview.py
git commit -m "feat: add Overview tab — tiles, sparklines, funnel, idle-states, twin panels"
```

---

## Task 12 — Resumes tab

**Files:**

- Create: `scripts/dashboard/tabs/resumes.py`

### Steps

- [ ] **Step 1: Write the implementation**

Create `scripts/dashboard/tabs/resumes.py`:

```python
"""Resumes tab — table of resume versions with focus areas + AI-signal score.

Data source: SELECT * FROM resume_versions via a small helper in this file
that opens the tracker db directly. (The tracker.query module does not yet
expose a list_resume_versions helper; rather than adding one, we do a tight
read-only query here. Future refactor could promote it into tracker.query.)
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from scripts.tracker.db import open_db


def render() -> None:
    if st.button("↻ Refresh", key="resumes_refresh"):
        st.rerun()

    rows = _list_resume_versions()

    if not rows:
        st.info(
            "No resume versions tracked yet. Run a workflow that opts in to "
            "tracking (e.g. `/brains-tailor` followed by registering the output)."
        )
        return

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "file_path": st.column_config.TextColumn("File", width="medium"),
            "template": st.column_config.TextColumn("Template", width="small"),
            "focus_areas": st.column_config.TextColumn("Focus Areas", width="medium"),
            "ai_signal_score": st.column_config.NumberColumn(
                "AI-signal", help="Lower is better. 0-9 clean, 30+ worth a rewrite.",
                width="small",
            ),
            "parent_id": st.column_config.NumberColumn("Parent", width="small"),
            "tagged_jd_id": st.column_config.NumberColumn("JD", width="small"),
            "created_at": st.column_config.TextColumn("Created", width="small"),
        },
        hide_index=True,
    )

    st.caption(f"Showing {len(df)} resume versions.")


def _list_resume_versions() -> list:
    """Read-only direct query for resume versions + computed AI-signal score."""
    import json

    from scripts.validators.ai_signal_check import ai_signal_check

    conn = open_db()
    try:
        cur = conn.execute(
            """
            SELECT id, file_path, template, focus_areas, parent_id,
                   tagged_jd_id, created_at
            FROM resume_versions
            WHERE archived_at IS NULL
            ORDER BY created_at DESC
            """
        )
        rows = []
        for row in cur.fetchall():
            focus_areas_list = json.loads(row[3]) if row[3] else []
            # AI-signal score requires the resume text — for now we skip the
            # score column when file is absent. A future refactor could
            # extract text via docx_to_text / pdf_to_text. For v1.3.0, leave
            # ai_signal_score as None when text isn't available.
            score = None
            if row[1] and Path(row[1]).exists():
                file_path = Path(row[1])
                if file_path.suffix == ".docx":
                    try:
                        from scripts.parsers.docx_to_text import parse_docx_resume
                        text = parse_docx_resume(file_path).get("raw_text", "")
                        if text:
                            score = ai_signal_check(text).score
                    except Exception:
                        score = None
            rows.append({
                "id": row[0],
                "file_path": row[1] or "(no file)",
                "template": row[2],
                "focus_areas": ", ".join(focus_areas_list),
                "ai_signal_score": score,
                "parent_id": row[4],
                "tagged_jd_id": row[5],
                "created_at": row[6][:10] if row[6] else "",
            })
    finally:
        conn.close()
    return rows
```

- [ ] **Step 2: Verify the module imports cleanly**

```powershell
python -c "from scripts.dashboard.tabs.resumes import render; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Commit**

```powershell
git add scripts/dashboard/tabs/resumes.py
git commit -m "feat: add Resumes tab with focus-area tags and AI-signal score"
```

---

## Task 13 — Cover Letters tab

**Files:**

- Create: `scripts/dashboard/tabs/cover_letters.py`

### Steps

- [ ] **Step 1: Write the implementation**

Create `scripts/dashboard/tabs/cover_letters.py`:

```python
"""Cover Letters tab — table of cover letter versions linked to resumes + JDs."""
from pathlib import Path

import pandas as pd
import streamlit as st

from scripts.tracker.db import open_db


def render() -> None:
    if st.button("↻ Refresh", key="cl_refresh"):
        st.rerun()

    rows = _list_cover_letters()

    if not rows:
        st.info(
            "No cover letters tracked yet. Run `/brains-cover-letter` and "
            "opt in to tracking at the end of the workflow."
        )
        return

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "file_path": st.column_config.TextColumn("File", width="medium"),
            "template": st.column_config.TextColumn("Template", width="small"),
            "resume_version_id": st.column_config.NumberColumn("Resume", width="small"),
            "jd_company": st.column_config.TextColumn("Company", width="small"),
            "jd_role_title": st.column_config.TextColumn("Role", width="medium"),
            "ai_signal_score": st.column_config.NumberColumn(
                "AI-signal", help="Lower is better.", width="small",
            ),
            "created_at": st.column_config.TextColumn("Created", width="small"),
        },
        hide_index=True,
    )

    st.caption(f"Showing {len(df)} cover letters.")


def _list_cover_letters() -> list:
    from scripts.validators.ai_signal_check import ai_signal_check

    conn = open_db()
    try:
        cur = conn.execute(
            """
            SELECT cl.id, cl.file_path, cl.template, cl.resume_version_id,
                   cl.jd_id, j.company, j.role_title, cl.created_at
            FROM cover_letters cl
            JOIN jds j ON j.id = cl.jd_id
            WHERE cl.archived_at IS NULL
            ORDER BY cl.created_at DESC
            """
        )
        rows = []
        for row in cur.fetchall():
            score = None
            if row[1] and Path(row[1]).exists():
                file_path = Path(row[1])
                if file_path.suffix == ".docx":
                    try:
                        from scripts.parsers.docx_to_text import parse_docx_resume
                        text = parse_docx_resume(file_path).get("raw_text", "")
                        if text:
                            score = ai_signal_check(text).score
                    except Exception:
                        score = None
            rows.append({
                "id": row[0],
                "file_path": row[1] or "(no file)",
                "template": row[2],
                "resume_version_id": row[3],
                "jd_company": row[5],
                "jd_role_title": row[6],
                "ai_signal_score": score,
                "created_at": row[7][:10] if row[7] else "",
            })
    finally:
        conn.close()
    return rows
```

- [ ] **Step 2: Verify the module imports cleanly**

```powershell
python -c "from scripts.dashboard.tabs.cover_letters import render; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Commit**

```powershell
git add scripts/dashboard/tabs/cover_letters.py
git commit -m "feat: add Cover Letters tab with resume + JD linkage"
```

---

## Task 14 — JDs tab

**Files:**

- Create: `scripts/dashboard/tabs/jds.py`

### Steps

- [ ] **Step 1: Write the implementation**

Create `scripts/dashboard/tabs/jds.py`:

```python
"""JDs tab — table of analyzed job descriptions with findings."""
import json

import pandas as pd
import streamlit as st

from scripts.tracker.db import open_db


def render() -> None:
    if st.button("↻ Refresh", key="jds_refresh"):
        st.rerun()

    rows = _list_jds()

    if not rows:
        st.info(
            "No JDs tracked yet. Run `/brains-jd-analyze` and opt in to "
            "saving the JD to the tracker at the end of the workflow."
        )
        return

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "company": st.column_config.TextColumn("Company", width="medium"),
            "role_title": st.column_config.TextColumn("Role", width="medium"),
            "source": st.column_config.TextColumn("Source", width="small"),
            "finding_count": st.column_config.NumberColumn("Findings", width="small"),
            "role_fit_score": st.column_config.NumberColumn(
                "Fit",
                help="0-100. Higher is better. Computed against user's focus areas.",
                width="small",
            ),
            "created_at": st.column_config.TextColumn("Saved", width="small"),
        },
        hide_index=True,
    )

    selected_id = st.selectbox(
        "Show findings for JD:",
        options=[None] + [r["id"] for r in rows],
        format_func=lambda x: "(select a JD)" if x is None else f"#{x}",
    )
    if selected_id is not None:
        _render_findings_for_jd(selected_id, rows)


def _list_jds() -> list:
    conn = open_db()
    try:
        cur = conn.execute(
            """
            SELECT id, company, role_title, source,
                   analyzer_findings, created_at
            FROM jds
            WHERE archived_at IS NULL
            ORDER BY created_at DESC
            """
        )
        rows = []
        for row in cur.fetchall():
            findings = json.loads(row[4]) if row[4] else {}
            finding_count = (
                len(findings.get("findings", []))
                if isinstance(findings, dict) else 0
            )
            role_fit_score = (
                findings.get("role_fit_score")
                if isinstance(findings, dict) else None
            )
            rows.append({
                "id": row[0],
                "company": row[1],
                "role_title": row[2],
                "source": row[3],
                "finding_count": finding_count,
                "role_fit_score": role_fit_score,
                "created_at": row[5][:10] if row[5] else "",
                "_analyzer_findings": findings,
            })
    finally:
        conn.close()
    return rows


def _render_findings_for_jd(jd_id: int, rows: list) -> None:
    """Render the analyzer findings for the selected JD as an expander stack."""
    jd_row = next((r for r in rows if r["id"] == jd_id), None)
    if jd_row is None:
        return
    findings_dict = jd_row.get("_analyzer_findings", {})
    findings = findings_dict.get("findings", []) if isinstance(findings_dict, dict) else []

    st.markdown(f"### Findings for #{jd_id} — {jd_row['company']} / {jd_row['role_title']}")
    if not findings:
        st.caption("No structured findings recorded for this JD.")
        return

    for f in findings:
        with st.expander(f"**{f.get('code', 'finding')}** ({f.get('severity', '?')})"):
            st.write(f.get("suggestion", ""))
            if f.get("excerpt"):
                st.code(f["excerpt"], language=None)

    st.caption(
        "See `references/jd-analyzer.md` (workflow doc) for finding-code definitions."
    )
```

- [ ] **Step 2: Verify the module imports cleanly**

```powershell
python -c "from scripts.dashboard.tabs.jds import render; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Commit**

```powershell
git add scripts/dashboard/tabs/jds.py
git commit -m "feat: add JDs tab with finding expanders"
```

---

## Task 15 — Applications tab

**Files:**

- Create: `scripts/dashboard/tabs/applications.py`

### Steps

- [ ] **Step 1: Write the implementation**

Create `scripts/dashboard/tabs/applications.py`:

```python
"""Applications tab — sortable table of applications with filters."""
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from scripts.dashboard.data import cached_list_applications


def render() -> None:
    if st.button("↻ Refresh", key="apps_refresh"):
        cached_list_applications.clear()

    # Filter row
    filt_col1, filt_col2, filt_col3, filt_col4 = st.columns([2, 1, 1, 1])
    with filt_col1:
        company_filter = st.text_input(
            "Company filter",
            placeholder="leave blank for all",
            key="apps_company_filter",
        )
    with filt_col2:
        status_filter = st.selectbox(
            "Status", options=["all", "open", "closed"], index=0, key="apps_status_filter",
        )
    with filt_col3:
        days_filter = st.number_input(
            "Submitted in last N days",
            min_value=0, max_value=3650, value=365,
            key="apps_days_filter",
        )
    with filt_col4:
        channel_filter = st.selectbox(
            "Channel",
            options=["all", "linkedin", "agency", "direct", "referral", "other"],
            index=0,
            key="apps_channel_filter",
        )

    since = datetime.now() - timedelta(days=days_filter) if days_filter > 0 else None
    rows = cached_list_applications(
        company=company_filter if company_filter else None,
        since=since,
        status=status_filter if status_filter != "all" else None,
    )

    if channel_filter != "all":
        rows = [r for r in rows if r.channel == channel_filter]

    if not rows:
        st.info("No applications match the current filters.")
        return

    now = datetime.now()
    df = pd.DataFrame([
        {
            "id": r.id,
            "company": r.company,
            "role": r.role_title,
            "submitted": r.submitted_at[:10] if r.submitted_at else "",
            "channel": r.channel,
            "agency": r.agency_name or "",
            "resume_id": r.resume_version_id,
            "cover_letter_id": r.cover_letter_id,
            "latest_outcome": r.latest_outcome or "(pending)",
            "days_since": _days_since(r.submitted_at, now),
        }
        for r in rows
    ])

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "company": st.column_config.TextColumn("Company", width="medium"),
            "role": st.column_config.TextColumn("Role", width="medium"),
            "submitted": st.column_config.TextColumn("Submitted", width="small"),
            "channel": st.column_config.TextColumn("Channel", width="small"),
            "agency": st.column_config.TextColumn("Agency", width="small"),
            "resume_id": st.column_config.NumberColumn("Resume", width="small"),
            "cover_letter_id": st.column_config.NumberColumn("CL", width="small"),
            "latest_outcome": st.column_config.TextColumn("Outcome", width="small"),
            "days_since": st.column_config.NumberColumn("Days", width="small"),
        },
        hide_index=True,
    )
    st.caption(
        f"Showing {len(df)} applications. To log an outcome: "
        "`/brains-track update <id> <event-type>` in your terminal."
    )


def _days_since(submitted_at: str, now: datetime) -> int:
    if not submitted_at:
        return 0
    try:
        return (now - datetime.fromisoformat(submitted_at)).days
    except (ValueError, TypeError):
        return 0
```

- [ ] **Step 2: Verify the module imports cleanly**

```powershell
python -c "from scripts.dashboard.tabs.applications import render; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Commit**

```powershell
git add scripts/dashboard/tabs/applications.py
git commit -m "feat: add Applications tab with filterable table"
```

---

## Task 16 — Analytics tab

**Files:**

- Create: `scripts/dashboard/tabs/analytics.py`

### Steps

- [ ] **Step 1: Write the implementation**

Create `scripts/dashboard/tabs/analytics.py`:

```python
"""Analytics tab — efficacy charts by template and channel."""
import pandas as pd
import plotly.express as px
import streamlit as st

from scripts.dashboard.data import (
    cached_efficacy_by_template,
    cached_list_applications,
)
from scripts.dashboard.style import GOLD_DEEP


def render() -> None:
    if st.button("↻ Refresh", key="analytics_refresh"):
        cached_efficacy_by_template.clear()
        cached_list_applications.clear()

    st.subheader("Efficacy by template")
    _render_efficacy_by_template()

    st.markdown("---")
    st.subheader("Efficacy by channel")
    _render_efficacy_by_channel()


def _render_efficacy_by_template() -> None:
    rows = cached_efficacy_by_template()
    if not rows:
        st.info("No data yet — register applications via `/brains-precheck` or `/brains-track add`.")
        return

    df = pd.DataFrame([
        {
            "template": r.template,
            "submitted": r.submitted_count,
            "callbacks": r.callback_count,
            "interviews": r.interview_count,
            "offers": r.offer_count,
            "rejections": r.rejection_count,
        }
        for r in rows
    ])

    fig = px.bar(
        df.melt(id_vars="template", var_name="stage", value_name="count"),
        x="template", y="count", color="stage",
        barmode="group",
        color_discrete_sequence=[GOLD_DEEP, "#7ABA7A", "#5A8FE8", "#A070C0", "#C76060"],
    )
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_efficacy_by_channel() -> None:
    """Aggregate applications by channel + outcome class for a stacked-bar view."""
    rows = cached_list_applications()
    if not rows:
        st.caption("No applications to analyze yet.")
        return

    interview_types = {"phone_screen", "first_round", "second_round", "take_home"}
    counts: dict = {}
    for r in rows:
        ch = r.channel
        bucket = counts.setdefault(ch, {"submitted": 0, "callbacks": 0,
                                       "interviews": 0, "offers": 0,
                                       "rejections": 0})
        bucket["submitted"] += 1
        if r.latest_outcome == "callback":
            bucket["callbacks"] += 1
        elif r.latest_outcome in interview_types:
            bucket["interviews"] += 1
        elif r.latest_outcome == "offer":
            bucket["offers"] += 1
        elif r.latest_outcome == "rejection":
            bucket["rejections"] += 1

    df = pd.DataFrame([{"channel": ch, **vals} for ch, vals in counts.items()])

    fig = px.bar(
        df.melt(id_vars="channel", var_name="stage", value_name="count"),
        x="channel", y="count", color="stage",
        barmode="group",
        color_discrete_sequence=[GOLD_DEEP, "#7ABA7A", "#5A8FE8", "#A070C0", "#C76060"],
    )
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
```

- [ ] **Step 2: Verify the module imports cleanly**

```powershell
python -c "from scripts.dashboard.tabs.analytics import render; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Commit**

```powershell
git add scripts/dashboard/tabs/analytics.py
git commit -m "feat: add Analytics tab with efficacy-by-template and -channel charts"
```

---

## Task 17 — Pacing tab + pacing_notes profile schema addition

**Files:**

- Create: `scripts/dashboard/tabs/pacing.py`
- Modify: `scripts/tracker/models.py` (add `pacing_notes` field to `Profile`)
- Modify: `scripts/tracker/profile.py` (read/write the new field)
- Modify: `tests/tracker/test_models.py` (test the new field default)
- Modify: `tests/tracker/test_profile.py` (test round-trip for `pacing_notes`)

### Steps

- [ ] **Step 1: Extend the Profile dataclass**

In `scripts/tracker/models.py`, find the `Profile` dataclass and add the new field:

```python
@dataclass
class Profile:
    focus_areas: List[str] = field(default_factory=list)
    healthy_weekly_rate: Optional[int] = None
    pacing_notes: Optional[str] = None
```

- [ ] **Step 2: Extend the profile read/write helpers**

In `scripts/tracker/profile.py`, update `read_profile` and `write_profile`:

```python
def read_profile() -> Profile:
    """Read the profile file. Missing file or corrupt JSON both return empty Profile."""
    path = get_profile_path()
    if not path.exists():
        return Profile()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Profile()
    return Profile(
        focus_areas=list(data.get("focus_areas", []) or []),
        healthy_weekly_rate=data.get("healthy_weekly_rate"),
        pacing_notes=data.get("pacing_notes"),
    )


def write_profile(profile: Profile) -> None:
    """Write the profile to disk. Creates parent directory if needed."""
    path = get_profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "focus_areas": profile.focus_areas,
                "healthy_weekly_rate": profile.healthy_weekly_rate,
                "pacing_notes": profile.pacing_notes,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
```

- [ ] **Step 3: Add tests for the new field**

Append to `tests/tracker/test_models.py`:

```python
def test_profile_default_pacing_notes_is_none():
    p = Profile()
    assert p.pacing_notes is None
```

Append to `tests/tracker/test_profile.py`:

```python
def test_pacing_notes_round_trip(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    write_profile(Profile(
        focus_areas=["python"], healthy_weekly_rate=3,
        pacing_notes="Felt overwhelming this week.",
    ))
    p = read_profile()
    assert p.pacing_notes == "Felt overwhelming this week."


def test_pacing_notes_backward_compat_missing_field(monkeypatch, tmp_path):
    """Old profile.json files without pacing_notes should still read cleanly."""
    path = tmp_path / "p.json"
    path.write_text('{"focus_areas": ["x"], "healthy_weekly_rate": 5}', encoding="utf-8")
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(path))
    p = read_profile()
    assert p.pacing_notes is None
    assert p.focus_areas == ["x"]
    assert p.healthy_weekly_rate == 5
```

- [ ] **Step 4: Run the profile + models tests**

```powershell
python -m pytest tests/tracker/test_models.py tests/tracker/test_profile.py -v
```

Expected: all tests pass (existing + 3 new = 16 total in those two files).

- [ ] **Step 5: Write the Pacing tab**

Create `scripts/dashboard/tabs/pacing.py`:

```python
"""Pacing tab — applications-this-week vs healthy rate + sensory-load notes."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scripts.dashboard.data import cached_list_applications
from scripts.dashboard.prep.sparkline import applications_per_week_8w
from scripts.dashboard.prep.trends import applications_this_week_count
from scripts.dashboard.style import GOLD_DEEP
from scripts.tracker.profile import read_profile


def render() -> None:
    if st.button("↻ Refresh", key="pacing_refresh"):
        cached_list_applications.clear()

    rows = cached_list_applications()
    profile = read_profile()
    apps_this_week = applications_this_week_count(rows)
    target = profile.healthy_weekly_rate

    # Tile: this-week count vs target
    col1, col2 = st.columns(2)
    col1.metric(
        "This week",
        f"{apps_this_week}" + (f" / {target}" if target is not None else ""),
        delta=(f"{apps_this_week - target:+d} vs target") if target is not None else None,
    )
    col2.metric(
        "Healthy weekly rate",
        f"{target}" if target is not None else "(not set)",
    )

    # Status banner
    st.markdown("---")
    if target is None:
        st.warning(
            "**No healthy weekly rate set.** Set one in the sidebar — the skill never "
            "recommends a number; you choose what your sensory bandwidth can sustain."
        )
    elif apps_this_week > target:
        st.warning(
            f"**{apps_this_week} applications this week — above your stated healthy "
            f"rate of {target}/week.** Consider pausing. No shame in slowing down."
        )
    elif apps_this_week == target:
        st.info(f"**At your healthy rate this week** ({apps_this_week} of {target}).")
    else:
        st.success(
            f"**Under your healthy rate this week** ({apps_this_week} of {target}). "
            "Bandwidth available if you want to use it."
        )

    # 8-week pacing trend
    st.markdown("---")
    st.subheader("8-week pacing trend")
    weekly_data = applications_per_week_8w(rows)
    df = pd.DataFrame(weekly_data)
    fig = go.Figure(
        go.Bar(
            x=df["week_starting"],
            y=df["count"],
            marker_color=GOLD_DEEP,
        )
    )
    if target is not None:
        fig.add_hline(
            y=target, line_dash="dash",
            line_color="#E0A040",
            annotation_text=f"target ({target}/wk)", annotation_position="right",
        )
    fig.update_layout(
        height=240,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Week starting",
        yaxis_title="Applications",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Sensory-load notes — read-only in this tab; edited from sidebar
    st.markdown("---")
    st.subheader("Sensory-load notes")
    if profile.pacing_notes:
        st.markdown(profile.pacing_notes)
    else:
        st.caption(
            "Edit your sensory-load notes in the sidebar. Track what's been "
            "overwhelming and what's been sustainable across weeks."
        )
```

- [ ] **Step 6: Verify the Pacing tab imports cleanly**

```powershell
python -c "from scripts.dashboard.tabs.pacing import render; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 7: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 291 tests pass (288 + 3 new from the Profile schema additions).

- [ ] **Step 8: Commit**

```powershell
git add scripts/dashboard/tabs/pacing.py scripts/tracker/models.py scripts/tracker/profile.py tests/tracker/test_models.py tests/tracker/test_profile.py
git commit -m "feat: add Pacing tab and pacing_notes profile schema field"
```

---

## Phase 4 — Sidebar + smoke test (Tasks 18-19)

---

## Task 18 — Sidebar + app.py wiring

**Files:**

- Modify: `scripts/dashboard/app.py`
- Create: `scripts/dashboard/sidebar.py`

### Steps

- [ ] **Step 1: Write the sidebar module**

Create `scripts/dashboard/sidebar.py`:

```python
"""Persistent sidebar — focus areas, healthy weekly rate, pacing notes, refresh."""
import subprocess

import streamlit as st

from scripts.dashboard.data import clear_all_caches
from scripts.dashboard.style import footer
from scripts.tracker.models import Profile
from scripts.tracker.profile import read_profile, write_profile


def render_sidebar() -> None:
    """Render the persistent sidebar. Called once from app.py before tabs."""
    with st.sidebar:
        st.markdown("### BRAINS Resume")
        st.markdown("*Dashboard*")
        st.markdown("---")

        profile = read_profile()

        # Focus areas
        st.markdown("**Focus areas**")
        focus_text = st.text_area(
            "Comma-separated",
            value=", ".join(profile.focus_areas),
            key="sidebar_focus_areas",
            label_visibility="collapsed",
        )

        # Healthy weekly rate
        st.markdown("**Healthy weekly rate**")
        rate = st.number_input(
            "Applications per week",
            min_value=0, max_value=100,
            value=profile.healthy_weekly_rate or 0,
            key="sidebar_rate",
            label_visibility="collapsed",
        )

        # Pacing notes
        st.markdown("**Sensory-load notes**")
        pacing_notes = st.text_area(
            "What's been overwhelming or sustainable",
            value=profile.pacing_notes or "",
            key="sidebar_pacing_notes",
            label_visibility="collapsed",
            height=120,
        )

        if st.button("Save profile", key="sidebar_save"):
            new_focus = [
                t.strip() for t in focus_text.split(",") if t.strip()
            ]
            new_rate = rate if rate > 0 else None
            new_notes = pacing_notes.strip() if pacing_notes.strip() else None
            write_profile(Profile(
                focus_areas=new_focus,
                healthy_weekly_rate=new_rate,
                pacing_notes=new_notes,
            ))
            clear_all_caches()
            st.success("Profile saved.")
            st.rerun()

        st.markdown("---")
        if st.button("↻ Refresh all", key="sidebar_refresh_all"):
            clear_all_caches()
            st.rerun()

        st.markdown("---")
        st.caption(f"v1.3.0 · {_git_sha()}")
        footer()


def _git_sha() -> str:
    """Return the short git SHA of the current HEAD, or 'unknown' on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        pass
    return "unknown"
```

- [ ] **Step 2: Replace app.py with the full implementation**

Replace `scripts/dashboard/app.py` (the stub from Task 2) with:

```python
"""Main Streamlit entry for the BRAINS Resume dashboard.

Run via the `brains-resume-dashboard` CLI entry point (see launch.py)
which invokes `streamlit run scripts/dashboard/app.py`.

Single-page top-tab layout matching the user's TSE Tools visual reference.
Seven tabs: Overview, Resumes, Cover Letters, JDs, Applications, Analytics,
Pacing. Persistent sidebar for profile editing. BRAINS Incubator branded.
"""
import streamlit as st

from scripts.dashboard.sidebar import render_sidebar
from scripts.dashboard.style import inject_brand_css
from scripts.dashboard.tabs import (
    analytics,
    applications,
    cover_letters,
    jds,
    overview,
    pacing,
    resumes,
)


def main() -> None:
    st.set_page_config(
        page_title="BRAINS Resume Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_brand_css()
    render_sidebar()

    st.title("BRAINS Resume Dashboard")

    tabs = st.tabs([
        "Overview",
        "Resumes",
        "Cover Letters",
        "JDs",
        "Applications",
        "Analytics",
        "Pacing",
    ])

    with tabs[0]:
        overview.render()
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


main()
```

- [ ] **Step 3: Verify the app module imports cleanly**

```powershell
python -c "from scripts.dashboard import app; print('OK')"
```

Expected: prints `OK` (Streamlit warnings about being outside a Streamlit context are fine).

- [ ] **Step 4: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 291 tests still pass.

- [ ] **Step 5: Commit**

```powershell
git add scripts/dashboard/sidebar.py scripts/dashboard/app.py
git commit -m "feat: wire up sidebar and seven-tab layout in dashboard app"
```

---

## Task 19 — Streamlit smoke import + AppTest happy-path

**Files:**

- Create: `tests/dashboard/test_app_import.py`
- Create: `tests/dashboard/test_app_overview_render.py`

### Steps

- [ ] **Step 1: Write the smoke import test**

Create `tests/dashboard/test_app_import.py`:

```python
"""Smoke test: the dashboard app module imports without errors.

Catches missing-module errors, import-cycle issues, and syntax errors.
Does NOT render the app — that's what test_app_overview_render.py does.
"""


def test_app_module_imports():
    # Importing the module triggers Streamlit's set_page_config and main() call.
    # Without a Streamlit runtime context, these calls warn but do not raise.
    import scripts.dashboard.app  # noqa: F401


def test_all_tab_modules_import():
    from scripts.dashboard.tabs import (  # noqa: F401
        analytics, applications, cover_letters, jds, overview, pacing, resumes,
    )


def test_sidebar_module_imports():
    from scripts.dashboard.sidebar import render_sidebar  # noqa: F401


def test_style_module_imports():
    from scripts.dashboard.style import inject_brand_css, footer  # noqa: F401
```

- [ ] **Step 2: Write the AppTest happy-path test**

Create `tests/dashboard/test_app_overview_render.py`:

```python
"""AppTest happy-path: the Overview tab renders without exceptions.

Uses streamlit.testing.v1.AppTest to drive a synthetic Streamlit session.
Empty tracker db -> the app should render with "No applications" / idle-state
callouts rather than crashing.
"""
from pathlib import Path

import pytest

APP_PATH = Path(__file__).parent.parent.parent / "scripts" / "dashboard" / "app.py"


@pytest.fixture
def empty_tracker(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    return tmp_path


def test_app_loads_overview_tab_with_empty_db(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=10)
    # App should render without exceptions
    assert not at.exception, f"App raised: {at.exception}"


def test_app_renders_title(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=10)
    # Find the title element
    titles = [t.value for t in at.title]
    assert "BRAINS Resume Dashboard" in titles
```

- [ ] **Step 3: Run the smoke tests**

```powershell
python -m pytest tests/dashboard/test_app_import.py tests/dashboard/test_app_overview_render.py -v
```

Expected: 6 tests pass (4 import tests + 2 AppTest tests).

Note: `AppTest` requires Streamlit >= 1.30. If the AppTest tests fail with API errors, that's likely a Streamlit version mismatch — confirm `streamlit --version` reports 1.30+.

- [ ] **Step 4: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 297 tests pass (291 + 6).

- [ ] **Step 5: Commit**

```powershell
git add tests/dashboard/test_app_import.py tests/dashboard/test_app_overview_render.py
git commit -m "test: add dashboard smoke tests (import + AppTest happy-path)"
```

---

## Phase 5 — Release polish (Tasks 20-23)

---

## Task 20 — Docs updates (SKILL.md, README, brand-application, claude-project-setup)

**Files:**

- Modify: `SKILL.md`
- Modify: `README.md`
- Modify: `references/brand-application.md`
- Modify: `docs/claude-project-setup.md`

### Steps

- [ ] **Step 1: Update SKILL.md**

Three edits in `SKILL.md`:

**A.** Add to the Tooling Notes section a new bullet:

```markdown
- **Local Streamlit dashboard** — `scripts/dashboard/` package launches via `brains-resume-dashboard` (registered in `pyproject.toml [project.scripts]`). BRAINS Incubator branded, single-page top-tab layout with seven tabs (Overview, Resumes, Cover Letters, JDs, Applications, Analytics, Pacing) plus a persistent sidebar for profile editing. Read-only except for sidebar profile.json edits. Available from v1.3.0 onward.
```

**B.** Update the slash-command-list sentence. Find:

> "Type `/brains-` and Claude Code will list the fifteen commands: review, disclosure, edit, tailor, cover-letter, create, linkedin, linkedin-improve, consolidate, jd-analyze, precheck, track, deai, career-change, check."

Replace with:

> "Type `/brains-` and Claude Code will list the sixteen commands: review, disclosure, edit, tailor, cover-letter, create, linkedin, linkedin-improve, consolidate, jd-analyze, precheck, track, deai, dashboard, career-change, check."

**C.** Leave "fourteen workflows" phrasing unchanged — the dashboard is a tool, not a workflow.

- [ ] **Step 2: Update README.md**

**A.** Add a new slash-command entry:

```markdown
- `/brains-dashboard` — Print the command to launch the local Streamlit dashboard in a browser
```

**B.** Add a new "Launching the dashboard" section after "Tracking applications":

```markdown
## Launching the dashboard

The skill ships a local Streamlit dashboard from v1.3.0. After `pip install -e .` (which registers the `brains-resume-dashboard` CLI entry), launch from any terminal:

```
brains-resume-dashboard
```

The dashboard opens at `http://localhost:8501`. Press Ctrl+C in the launch terminal to stop it.

What you get:
- **Overview** — pipeline funnel, summary tiles, sparkline trends, idle-state callouts, pending-callbacks panel
- **Resumes / Cover Letters / JDs** — tagged tables with focus areas, AI-signal score per text artifact, links to source files
- **Applications** — filterable table by company / channel / status / date
- **Analytics** — efficacy by template and channel
- **Pacing** — this-week count vs your self-defined healthy weekly rate, with sensory-load notes journal

The dashboard is BRAINS Incubator branded (Gold Deep accents, Atkinson Hyperlegible font, dark theme) and runs entirely on localhost — no telemetry, no outbound network.

Read-only except for the sidebar profile editor (focus areas, healthy weekly rate, pacing notes). Application outcomes are still logged via `/brains-track update <id> <event>` in your terminal.
```

**C.** Update any "fifteen commands" mention to "sixteen commands".

- [ ] **Step 3: Update references/brand-application.md**

In Section 1 (Split Rule) table, add one new row after the de-AI report row:

```markdown
| Streamlit dashboard UI (`brains-resume-dashboard`) | **BRAINS Incubator branded** — Gold Deep accents, Atkinson Hyperlegible body, BRAINS mark in sidebar, identity-first language throughout | Internal coaching surface; renders the user's own data, no external audience |
```

- [ ] **Step 4: Update docs/claude-project-setup.md**

Add a new sub-section after the de-AI tool entry:

```markdown
### Dashboard (v1.3.0+)

The skill includes a local Streamlit dashboard accessible via `brains-resume-dashboard` after install. It is **Claude-Code-only** — claude.ai cannot run Streamlit, and the dashboard depends on the local SQLite tracker file under `~/.brains-resume/`. See the README's "Launching the dashboard" section for details.
```

- [ ] **Step 5: Run the full suite to confirm no regressions**

```powershell
python -m pytest -q
```

Expected: 297 tests still pass.

- [ ] **Step 6: Commit**

```powershell
git add SKILL.md README.md references/brand-application.md docs/claude-project-setup.md
git commit -m "docs: update SKILL.md, README, brand-application, and Claude Project guide for v1.3.0"
```

---

## Task 21 — CHANGELOG entry + Claude Project bundle rebuild

**Files:**

- Modify: `CHANGELOG.md`
- Rebuild: `dist/brains-resume-claude-project.zip` (gitignored, not committed)

### Steps

- [ ] **Step 1: Add the v1.3.0 CHANGELOG entry**

At the top of `CHANGELOG.md`, above the v1.2.1 entry, add:

```markdown
## [1.3.0] — 2026-05-14

### Added
- **Local Streamlit dashboard** (`brains-resume-dashboard`) — BRAINS Incubator branded, single-page top-tab layout. Seven tabs: Overview (funnel + summary tiles + sparklines + idle-state callouts + twin panels), Resumes, Cover Letters, JDs, Applications, Analytics, Pacing. Persistent sidebar for editing focus areas, healthy weekly rate, and sensory-load notes.
- **`scripts/dashboard/` package** — `app.py`, `launch.py` (CLI entry), `style.py` (BRAINS Incubator CSS), `data.py` (cached query wrappers), `sidebar.py`, plus `tabs/` and `prep/` submodules.
- **`brains-resume-dashboard` CLI entry** — registered via `pyproject.toml [project.scripts]`. After `pip install -e .` the command launches the dashboard from any terminal.
- **`/brains-dashboard` slash command** — prints the launch command (does not spawn the subprocess from Claude Code).
- **`.streamlit/config.toml`** — dark-theme baseline, headless server config, telemetry disabled.
- **Four pure prep modules** — `prep/funnel.py`, `prep/sparkline.py`, `prep/trends.py`, `prep/idle_states.py`. Fully unit-tested without Streamlit dependency.
- **`pacing_notes` field on `Profile` dataclass** — optional sensory-load notes journal, persisted to `profile.json`, editable from the sidebar.
- **Streamlit + Plotly** added to `pyproject.toml` `dependencies` (required, not optional).

### Changed
- **`SKILL.md` and `README.md`** — slash-command list updated (15 → 16 commands; dashboard is a tool, not a workflow); new "Launching the dashboard" section in README.
- **`references/brand-application.md`** — split-rule table extended for the dashboard UI artifact type.
- **`docs/claude-project-setup.md`** — note that the dashboard is Claude-Code-only.
```

- [ ] **Step 2: Rebuild the Claude Project bundle**

```powershell
.venv\Scripts\activate
python scripts\packaging\build_project_bundle.py
```

Expected: prints `Wrote ...\dist\brains-resume-claude-project.zip`. The dashboard scripts do NOT ship in the Claude Project bundle (the bundle is for claude.ai users who can't run Python locally).

- [ ] **Step 3: Verify the bundle still contains the v1.2.1 ai-signal-patterns reference**

```powershell
python -c "import zipfile; z = zipfile.ZipFile('dist/brains-resume-claude-project.zip'); names = z.namelist(); print('ai-signal-patterns:', 'brains-resume-claude-project/references/ai-signal-patterns.md' in names)"
```

Expected: `True`.

- [ ] **Step 4: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 297 tests still pass.

- [ ] **Step 5: Commit (do NOT commit the dist/zip — gitignored)**

```powershell
git add CHANGELOG.md
git commit -m "docs: add v1.3.0 CHANGELOG entry"
git status
```

`git status` should show clean working tree afterwards. The `dist/brains-resume-claude-project.zip` is gitignored and won't appear.

---

## Task 22 — Version bump

**Files:**

- Modify: `SKILL.md` (frontmatter `version` + body version reference)
- Modify: `pyproject.toml`

### Steps

- [ ] **Step 1: Bump SKILL.md frontmatter**

In `SKILL.md`, find:

```yaml
version: 1.2.1
```

Change to:

```yaml
version: 1.3.0
```

- [ ] **Step 2: Update body version reference**

In `SKILL.md`, find:

> "This is a BRAINS Incubator project, v1.2.1."

Update to:

> "This is a BRAINS Incubator project, v1.3.0."

- [ ] **Step 3: Bump pyproject.toml**

In `pyproject.toml`, find:

```toml
version = "1.2.1"
```

Change to:

```toml
version = "1.3.0"
```

- [ ] **Step 4: Run the full suite one final time**

```powershell
python -m pytest -q
```

Expected: 297 tests pass, all green.

- [ ] **Step 5: Commit the version bump**

```powershell
git add SKILL.md pyproject.toml
git commit -m "chore: bump version to 1.3.0"
```

---

## Task 23 — v1.3.0 git tag

### Steps

- [ ] **Step 1: Create the v1.3.0 tag**

```powershell
git tag -a v1.3.0 -m "v1.3.0 - Local Streamlit dashboard (BRAINS Incubator branded)"
```

Use a hyphen, not em dash, in the tag message to avoid PowerShell shell-escape issues.

- [ ] **Step 2: Verify the tag**

```powershell
git tag --list
git show v1.3.0 --stat
```

Expected: `v1.3.0` appears in the tag list; `git show v1.3.0` displays the chore commit + the SKILL.md/pyproject.toml changes.

- [ ] **Step 3: Final status check**

```powershell
git status
git log --oneline -10
```

Expected: working tree clean. The last ~22 commits trace Plan 5b work. Most recent commit is `chore: bump version to 1.3.0`. Tag points at that commit.

Do NOT push to remote — the plan does not push. When ready, the user pushes with `git push && git push --tags`.

---

## Plan completion checklist

After all 23 tasks are marked complete, verify:

- [ ] All 23 tasks have every step checked off.
- [ ] `python -m pytest -q` reports 297 tests green (259 baseline + 38 new).
- [ ] `git tag --list` includes `v1.3.0`.
- [ ] `dist/brains-resume-claude-project.zip` was rebuilt and still contains the v1.2.1 references.
- [ ] No commits include `Co-Authored-By` footers.
- [ ] No third-party org/project proper-name attribution appears in any committed file or commit message.
- [ ] `SKILL.md` frontmatter says `version: 1.3.0`.
- [ ] `pyproject.toml` says `version = "1.3.0"` and includes `streamlit`, `plotly`, and the `brains-resume-dashboard` `[project.scripts]` entry.
- [ ] `commands/brains-dashboard.md` exists.
- [ ] `scripts/dashboard/` package exists with `app.py`, `launch.py`, `style.py`, `data.py`, `sidebar.py`, plus `tabs/` (7 modules) and `prep/` (4 modules).
- [ ] `.streamlit/config.toml` exists with dark-theme baseline.
- [ ] `brains-resume-dashboard` runs from any terminal and launches Streamlit on localhost:8501.
- [ ] AppTest happy-path test passes — Overview tab renders without exceptions on an empty database.

When every box is ticked, v1.3.0 is shippable.
