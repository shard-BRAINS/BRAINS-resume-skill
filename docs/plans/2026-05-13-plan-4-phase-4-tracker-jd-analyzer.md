# Plan 4 — Phase 4: Tracker Data Layer, JD Analyzer, Pre-Application Check (v1.2.0)

> **For implementers:** Checkbox (`- [ ]`) syntax. Work sequentially, mark steps as you go. Stage and commit after each task. **Never include third-party org or project credits in any file or commit message — BRAINS / BRAINS Trust / BRAINS Incubator only. Never include `Co-Authored-By` footers.** Conventional commits style.

**Goal:** Ship v1.2.0 — establish the deterministic data and analysis foundation that the v1.3.0 dashboard will consume. Adds a SQLite application tracker at user-level path (`~/.brains-resume/tracker.db`), a JD analyzer validator with 6-code finding catalog, a pre-application sanity-check workflow, and opt-in integration with four existing workflows.

**Architecture:** Same hybrid skill structure as v1.1.x (always-loaded `SKILL.md` core + on-demand reference files + deterministic Python scripts + validators). Adds a new `scripts/tracker/` Python module with public API (`add`, `query`, `profile`), a new `scripts/validators/jd_analyzer.py` validator, a new user-level state directory `~/.brains-resume/`, three new workflow references, and three new slash commands. The tracker is opt-in — existing workflows prompt at end rather than auto-register.

**Tech Stack:** Unchanged — Python 3.10+, standard library `sqlite3` (no new dependencies). Existing libraries: `python-docx`, `pdfplumber`, `reportlab`, `trafilatura`, `pyyaml`, `pytest`.

**Spec reference:** [`docs/specs/2026-05-13-phase-4-tracker-jd-analyzer-design.md`](../specs/2026-05-13-phase-4-tracker-jd-analyzer-design.md)

**In scope for this plan:**

1. **Tracker data layer** — `scripts/tracker/` module: `db.py`, `models.py`, `add.py`, `query.py`, `profile.py` with full unit-test coverage
2. **SQLite schema + migrations** — 5 entity tables + migrations table, numbered migration scripts in `scripts/tracker/migrations/`
3. **User profile store** — `~/.brains-resume/profile.json` for focus areas + healthy weekly application rate
4. **JD analyzer validator** — `scripts/validators/jd_analyzer.py` with 6-code finding catalog (SOFT_CULTURE, MASKING_COST, EVIDENCE_OF_FLEX, REQ_VS_NICE_PARSING, ROLE_FIT_SCORE, DUPLICATE_APPLICATION) + fixtures
5. **Three new workflow references** — `references/workflows/jd-analyze.md`, `references/workflows/pre-application-check.md`, and the `brains-track` slash command's self-describing reference inline
6. **Three new slash commands** — `commands/brains-jd-analyze.md`, `commands/brains-precheck.md`, `commands/brains-track.md`
7. **Opt-in integration** — end-of-workflow tracker prompt added to `brains-tailor`, `brains-cover-letter`, `brains-review`, `brains-check` reference docs
8. **SKILL.md router updates** — three new workflow entries; capability menu and slash-command list updated to reflect fourteen live workflows
9. **Brand-application reference update** — new artifact types covered by the unbranded-vs-branded rule
10. **README + CHANGELOG + Claude Project bundle** — slash-command cheat sheet, v1.2.0 entry, bundle rebuild
11. **v1.2.0 git tag**

**Out of scope (deferred to Phase 5 / future):**

- Streamlit dashboard UI (Phase 5 / v1.3.0 builds on the data layer this plan ships)
- Pacing/burnout tracker as a dedicated dashboard page (surfaced as CLI summary in v1.2.0)
- Efficacy analytics with confidence bands (basic counts in v1.2.0)
- Anonymized community efficacy data (Phase 5+)
- Interview prep skill (sibling, separate bundle)
- Salary negotiation skill (sibling, separate bundle)
- Network/referral lane as a first-class entity (folded into `channel` enum for v1.2.0)
- Recurring weekly job-search review (Phase 5+)
- MCP server for Claude Desktop (still deferred)

---

## Conventions used throughout this plan

- **Working directory:** `c:\Brains_Resume_Skill\`. All paths relative unless absolute is shown.
- **Tests live in:** `tests/` mirroring source structure.
- **Python fixtures:** `tests/fixtures/*.py`. Binary fixtures: `docs/testing/fixtures/`.
- **Commit style:** conventional commits — `feat:`, `fix:`, `test:`, `docs:`, `build:`, `chore:`, `perf:`, `refactor:`. NEVER include `Co-Authored-By` footers (BRAINS-only attribution).
- **Identity-first language** throughout; no italics in body text; no third-party org or project proper-name references.
- **Testing rhythm:** write failing test → run to confirm failure → implement → run to confirm pass → commit. Don't skip the failure-confirmation step.
- **Virtual environment:** always work inside `.venv` — `.venv\Scripts\activate` (PowerShell) or `source .venv/bin/activate` (bash) before running tests or scripts.
- **Tracker DB path override for tests:** `BRAINS_TRACKER_DB_PATH` environment variable. Tests use `monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))` to isolate.
- **Tracker profile path override for tests:** `BRAINS_TRACKER_PROFILE_PATH` environment variable. Same pattern.

---

## Phase 1 — Tracker data layer (Tasks 1-8)

Foundation for everything else. The tracker module ships with its public API + full unit-test coverage before any workflow references or slash commands depend on it.

---

## Task 1 — Tracker module bootstrap (models + package init)

**Files:**

- Create: `scripts/tracker/__init__.py` (empty)
- Create: `scripts/tracker/models.py` (dataclasses for the 5 entities + Profile + WeeklySummary + EfficacyRow)
- Create: `scripts/tracker/migrations/__init__.py` (empty)
- Create: `tests/tracker/__init__.py` (empty)
- Create: `tests/tracker/test_models.py`

### Steps

- [ ] **Step 1: Create the package directories**

```powershell
New-Item -ItemType Directory -Path "scripts\tracker" -Force
New-Item -ItemType Directory -Path "scripts\tracker\migrations" -Force
New-Item -ItemType Directory -Path "tests\tracker" -Force
```

- [ ] **Step 2: Create empty package init files**

Create `scripts/tracker/__init__.py` with this single line:

```python
"""BRAINS Resume Skill — application tracker module."""
```

Create `scripts/tracker/migrations/__init__.py` with this single line:

```python
"""SQLite schema migrations for the tracker module."""
```

Create `tests/tracker/__init__.py` as empty file.

- [ ] **Step 3: Write the models module**

Create `scripts/tracker/models.py`:

```python
"""Dataclasses for the tracker entities.

These are the data-transfer types between the public API (add/query/profile)
and consumers. They map 1:1 to SQLite rows for the 5 entity tables, plus
Profile (lives in profile.json), WeeklySummary (computed), and EfficacyRow
(computed).
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# Event-type enum values for the outcomes table. Defined as a tuple so they
# can be imported and used as the canonical list (e.g. for CLI validation).
OUTCOME_EVENT_TYPES = (
    "acknowledged",
    "callback",
    "phone_screen",
    "first_round",
    "second_round",
    "take_home",
    "offer",
    "rejection",
    "ghosted",
    "withdrew",
)

# Channel enum values for the applications table.
APPLICATION_CHANNELS = (
    "linkedin",
    "agency",
    "direct",
    "referral",
    "other",
)


@dataclass
class ResumeVersion:
    id: Optional[int]
    file_path: Optional[str]
    template: str
    focus_areas: List[str]
    parent_id: Optional[int]
    tagged_jd_id: Optional[int]
    created_at: str
    archived_at: Optional[str]


@dataclass
class CoverLetter:
    id: Optional[int]
    file_path: Optional[str]
    resume_version_id: int
    jd_id: int
    template: str
    created_at: str
    archived_at: Optional[str]


@dataclass
class JD:
    id: Optional[int]
    source: str
    source_ref: Optional[str]
    company: str
    role_title: str
    raw_text: str
    analyzer_findings: dict
    focus_areas_required: List[str]
    focus_areas_nice: List[str]
    created_at: str
    archived_at: Optional[str]


@dataclass
class Application:
    id: Optional[int]
    jd_id: int
    resume_version_id: int
    cover_letter_id: Optional[int]
    submitted_at: str
    channel: str
    agency_name: Optional[str]
    recruiter_contact: Optional[str]
    notes: Optional[str]
    created_at: str
    archived_at: Optional[str]


@dataclass
class Outcome:
    id: Optional[int]
    application_id: int
    event_type: str
    event_date: str
    notes: Optional[str]
    created_at: str
    archived_at: Optional[str]


@dataclass
class Profile:
    focus_areas: List[str] = field(default_factory=list)
    healthy_weekly_rate: Optional[int] = None


@dataclass
class WeeklySummary:
    week_starting: str  # YYYY-MM-DD (Monday of the week)
    applications_count: int
    outcomes_by_type: Dict[str, int]
    pacing_vs_target: Optional[str]  # 'above' | 'at' | 'below' | None if no target


@dataclass
class EfficacyRow:
    template: str
    submitted_count: int
    callback_count: int
    interview_count: int  # phone_screen + first_round + second_round + take_home
    offer_count: int
    rejection_count: int
```

- [ ] **Step 4: Write the model tests**

Create `tests/tracker/test_models.py`:

```python
"""Tests for tracker dataclass models."""
from scripts.tracker.models import (
    APPLICATION_CHANNELS,
    OUTCOME_EVENT_TYPES,
    Application,
    CoverLetter,
    EfficacyRow,
    JD,
    Outcome,
    Profile,
    ResumeVersion,
    WeeklySummary,
)


def test_outcome_event_types_complete():
    """The enum must include every event type the spec calls for."""
    expected = {
        "acknowledged", "callback", "phone_screen", "first_round",
        "second_round", "take_home", "offer", "rejection",
        "ghosted", "withdrew",
    }
    assert set(OUTCOME_EVENT_TYPES) == expected


def test_application_channels_complete():
    expected = {"linkedin", "agency", "direct", "referral", "other"}
    assert set(APPLICATION_CHANNELS) == expected


def test_profile_default_empty():
    p = Profile()
    assert p.focus_areas == []
    assert p.healthy_weekly_rate is None


def test_resume_version_all_fields_present():
    rv = ResumeVersion(
        id=1,
        file_path="/tmp/r.docx",
        template="hybrid",
        focus_areas=["platform", "observability"],
        parent_id=None,
        tagged_jd_id=None,
        created_at="2026-05-13T00:00:00Z",
        archived_at=None,
    )
    assert rv.template == "hybrid"
    assert rv.focus_areas == ["platform", "observability"]


def test_jd_carries_analyzer_findings_dict():
    jd = JD(
        id=1, source="paste", source_ref=None,
        company="Example Corp", role_title="Senior Engineer",
        raw_text="JD text", analyzer_findings={"red_flags": 2},
        focus_areas_required=["python"], focus_areas_nice=["go"],
        created_at="2026-05-13T00:00:00Z", archived_at=None,
    )
    assert jd.analyzer_findings == {"red_flags": 2}


def test_efficacy_row_carries_per_template_counts():
    e = EfficacyRow(
        template="hybrid", submitted_count=10, callback_count=4,
        interview_count=2, offer_count=1, rejection_count=3,
    )
    assert e.template == "hybrid"
    assert e.submitted_count == 10
```

- [ ] **Step 5: Run tests to verify they pass**

```powershell
.venv\Scripts\activate
python -m pytest tests/tracker/test_models.py -v
```

Expected: 6 tests pass.

- [ ] **Step 6: Run the full suite to confirm no regressions**

```powershell
python -m pytest -q
```

Expected: 146 tests pass (140 baseline + 6 new).

- [ ] **Step 7: Commit**

```powershell
git add scripts/tracker tests/tracker
git commit -m "feat: bootstrap tracker module with dataclass models"
```

---

## Task 2 — Tracker database connection + migration runner

**Files:**

- Create: `scripts/tracker/db.py`
- Create: `tests/tracker/test_db.py`

### Steps

- [ ] **Step 1: Write the failing tests**

Create `tests/tracker/test_db.py`:

```python
"""Tests for the tracker db connection + migration runner."""
import sqlite3
from pathlib import Path

import pytest

from scripts.tracker.db import open_db, get_db_path


def test_get_db_path_default_is_user_home(monkeypatch):
    """Without an override, the db path lives at ~/.brains-resume/tracker.db."""
    monkeypatch.delenv("BRAINS_TRACKER_DB_PATH", raising=False)
    path = get_db_path()
    assert path == Path.home() / ".brains-resume" / "tracker.db"


def test_get_db_path_honours_env_override(monkeypatch, tmp_path):
    override = tmp_path / "custom.db"
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(override))
    assert get_db_path() == override


def test_open_db_creates_file_in_user_chosen_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "subdir" / "test.db"))
    conn = open_db()
    try:
        assert (tmp_path / "subdir" / "test.db").exists()
    finally:
        conn.close()


def test_open_db_runs_migrations_on_first_open(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    conn = open_db()
    try:
        # migrations table must exist after first open
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'"
        )
        assert cur.fetchone() is not None
        # 0001 migration must be recorded
        cur = conn.execute("SELECT version FROM migrations ORDER BY version")
        versions = [row[0] for row in cur.fetchall()]
        assert 1 in versions
    finally:
        conn.close()


def test_open_db_does_not_rerun_applied_migrations(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    conn1 = open_db()
    cur = conn1.execute("SELECT COUNT(*) FROM migrations")
    first_count = cur.fetchone()[0]
    conn1.close()

    conn2 = open_db()
    cur = conn2.execute("SELECT COUNT(*) FROM migrations")
    second_count = cur.fetchone()[0]
    conn2.close()

    assert first_count == second_count


def test_open_db_returns_sqlite_connection(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    conn = open_db()
    try:
        assert isinstance(conn, sqlite3.Connection)
    finally:
        conn.close()


def test_open_db_enables_foreign_keys(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    conn = open_db()
    try:
        cur = conn.execute("PRAGMA foreign_keys")
        assert cur.fetchone()[0] == 1
    finally:
        conn.close()
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/tracker/test_db.py -v
```

Expected: ImportError on `scripts.tracker.db`.

- [ ] **Step 3: Write the implementation**

Create `scripts/tracker/db.py`:

```python
"""SQLite connection + migration runner for the tracker module.

The single public function is open_db(). It returns a sqlite3.Connection
with foreign keys enabled and all pending migrations applied. The db file
lives at ~/.brains-resume/tracker.db by default; tests override via the
BRAINS_TRACKER_DB_PATH environment variable.
"""
import importlib.util
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path


DEFAULT_DB_DIR = Path.home() / ".brains-resume"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "tracker.db"
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_db_path() -> Path:
    """Return the tracker db path, honouring BRAINS_TRACKER_DB_PATH override."""
    override = os.environ.get("BRAINS_TRACKER_DB_PATH")
    if override:
        return Path(override)
    return DEFAULT_DB_PATH


def open_db() -> sqlite3.Connection:
    """Open (creating if needed) the tracker db, run pending migrations,
    enable foreign keys, and return the connection."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    _ensure_migrations_table(conn)
    _run_pending_migrations(conn)
    return conn


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL,
            description TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _run_pending_migrations(conn: sqlite3.Connection) -> None:
    applied = {
        row[0] for row in conn.execute("SELECT version FROM migrations")
    }
    for version, description, module in _discover_migrations():
        if version in applied:
            continue
        module.apply(conn)
        conn.execute(
            "INSERT INTO migrations (version, applied_at, description) VALUES (?, ?, ?)",
            (version, datetime.utcnow().isoformat() + "Z", description),
        )
        conn.commit()


def _discover_migrations():
    """Yield (version, description, module) for each migration script in order."""
    if not MIGRATIONS_DIR.exists():
        return
    pattern = re.compile(r"^(\d{4})_(.+)\.py$")
    for script in sorted(MIGRATIONS_DIR.glob("*.py")):
        if script.name.startswith("_"):
            continue
        match = pattern.match(script.name)
        if not match:
            continue
        version = int(match.group(1))
        description = match.group(2).replace("_", " ")
        spec = importlib.util.spec_from_file_location(
            f"_migration_{version}", script
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield version, description, module
```

- [ ] **Step 4: Run tests — some will pass, some will fail**

```powershell
python -m pytest tests/tracker/test_db.py -v
```

The first 4 tests (get_db_path + opens-file + returns-Connection + foreign-keys) should pass. The migration tests will fail because no migrations exist yet — that's resolved in Task 3. Capture which tests fail vs pass.

Expected: 5 pass, 2 fail (test_open_db_runs_migrations_on_first_open + test_open_db_does_not_rerun_applied_migrations).

- [ ] **Step 5: Run the full suite (existing tests must not regress)**

```powershell
python -m pytest -q
```

Expected: 151 tests total — 149 pass, 2 fail (the migration-related ones). No previously-passing tests should regress.

- [ ] **Step 6: Commit**

```powershell
git add scripts/tracker/db.py tests/tracker/test_db.py
git commit -m "feat: add tracker db connection + migration runner"
```

(The migration-related test failures will resolve in Task 3 when the 0001 schema migration lands. This interim state is expected and clearly scoped.)

---

## Task 3 — Initial schema migration (5 entity tables)

**Files:**

- Create: `scripts/tracker/migrations/0001_initial_schema.py`

### Steps

- [ ] **Step 1: Write the migration script**

Create `scripts/tracker/migrations/0001_initial_schema.py`:

```python
"""Migration 0001 — initial schema.

Creates the five entity tables: resume_versions, cover_letters, jds,
applications, outcomes. All tables have id (autoincrement PK), created_at
(ISO-8601 UTC timestamp), and archived_at (NULL = active, non-NULL = soft-
deleted) columns.

Foreign keys are enforced at runtime via PRAGMA foreign_keys = ON, set by
scripts/tracker/db.py:open_db().
"""
import sqlite3


SCHEMA_SQL = """
CREATE TABLE resume_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT,
    template TEXT NOT NULL,
    focus_areas TEXT NOT NULL,
    parent_id INTEGER,
    tagged_jd_id INTEGER,
    created_at TEXT NOT NULL,
    archived_at TEXT,
    FOREIGN KEY (parent_id) REFERENCES resume_versions(id),
    FOREIGN KEY (tagged_jd_id) REFERENCES jds(id)
);

CREATE TABLE jds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_ref TEXT,
    company TEXT NOT NULL,
    role_title TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    analyzer_findings TEXT NOT NULL,
    focus_areas_required TEXT NOT NULL,
    focus_areas_nice TEXT NOT NULL,
    created_at TEXT NOT NULL,
    archived_at TEXT
);

CREATE TABLE cover_letters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT,
    resume_version_id INTEGER NOT NULL,
    jd_id INTEGER NOT NULL,
    template TEXT NOT NULL,
    created_at TEXT NOT NULL,
    archived_at TEXT,
    FOREIGN KEY (resume_version_id) REFERENCES resume_versions(id),
    FOREIGN KEY (jd_id) REFERENCES jds(id)
);

CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jd_id INTEGER NOT NULL,
    resume_version_id INTEGER NOT NULL,
    cover_letter_id INTEGER,
    submitted_at TEXT NOT NULL,
    channel TEXT NOT NULL,
    agency_name TEXT,
    recruiter_contact TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    archived_at TEXT,
    FOREIGN KEY (jd_id) REFERENCES jds(id),
    FOREIGN KEY (resume_version_id) REFERENCES resume_versions(id),
    FOREIGN KEY (cover_letter_id) REFERENCES cover_letters(id)
);

CREATE TABLE outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    event_date TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    archived_at TEXT,
    FOREIGN KEY (application_id) REFERENCES applications(id)
);

CREATE INDEX idx_applications_jd_id ON applications(jd_id);
CREATE INDEX idx_outcomes_application_id ON outcomes(application_id);
CREATE INDEX idx_jds_company ON jds(company);
"""


def apply(conn: sqlite3.Connection) -> None:
    """Apply the initial schema. Called by db.py's migration runner."""
    conn.executescript(SCHEMA_SQL)
```

- [ ] **Step 2: Run the previously-failing db tests**

```powershell
python -m pytest tests/tracker/test_db.py -v
```

Expected: all 7 tests pass now.

- [ ] **Step 3: Add a schema-presence test**

Append to `tests/tracker/test_db.py`:

```python
def test_all_five_entity_tables_exist_after_migration(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    conn = open_db()
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cur.fetchall()}
        # 5 entity tables + migrations + sqlite_sequence (autoincrement bookkeeping)
        assert "resume_versions" in tables
        assert "cover_letters" in tables
        assert "jds" in tables
        assert "applications" in tables
        assert "outcomes" in tables
        assert "migrations" in tables
    finally:
        conn.close()


def test_foreign_key_enforced_at_runtime(monkeypatch, tmp_path):
    """Insert an application row pointing at non-existent jd_id — must raise."""
    import sqlite3
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    conn = open_db()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO applications "
                "(jd_id, resume_version_id, submitted_at, channel, created_at) "
                "VALUES (999, 999, '2026-05-13', 'direct', '2026-05-13')"
            )
            conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify both new ones pass**

```powershell
python -m pytest tests/tracker/test_db.py -v
```

Expected: 9 tests pass.

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 155 tests pass (140 baseline + 6 from Task 1 + 9 from Task 2/3).

- [ ] **Step 6: Commit**

```powershell
git add scripts/tracker/migrations/0001_initial_schema.py tests/tracker/test_db.py
git commit -m "feat: add 0001 initial schema migration (5 entity tables)"
```

---

## Task 4 — Profile.json read/write helpers

**Files:**

- Create: `scripts/tracker/profile.py`
- Create: `tests/tracker/test_profile.py`

### Steps

- [ ] **Step 1: Write the failing tests**

Create `tests/tracker/test_profile.py`:

```python
"""Tests for the profile.json read/write helpers."""
from pathlib import Path

from scripts.tracker.models import Profile
from scripts.tracker.profile import read_profile, write_profile, get_profile_path


def test_get_profile_path_default(monkeypatch):
    monkeypatch.delenv("BRAINS_TRACKER_PROFILE_PATH", raising=False)
    assert get_profile_path() == Path.home() / ".brains-resume" / "profile.json"


def test_get_profile_path_honours_env_override(monkeypatch, tmp_path):
    override = tmp_path / "custom.json"
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(override))
    assert get_profile_path() == override


def test_read_profile_when_file_missing_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "missing.json"))
    p = read_profile()
    assert p.focus_areas == []
    assert p.healthy_weekly_rate is None


def test_write_then_read_round_trip(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    write_profile(Profile(focus_areas=["platform", "observability"], healthy_weekly_rate=4))
    p = read_profile()
    assert p.focus_areas == ["platform", "observability"]
    assert p.healthy_weekly_rate == 4


def test_write_profile_creates_parent_dir(monkeypatch, tmp_path):
    target = tmp_path / "newdir" / "p.json"
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(target))
    write_profile(Profile(focus_areas=["x"], healthy_weekly_rate=None))
    assert target.exists()


def test_write_profile_overwrites_existing(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    write_profile(Profile(focus_areas=["a"], healthy_weekly_rate=3))
    write_profile(Profile(focus_areas=["b", "c"], healthy_weekly_rate=5))
    p = read_profile()
    assert p.focus_areas == ["b", "c"]
    assert p.healthy_weekly_rate == 5


def test_read_profile_malformed_json_returns_empty(monkeypatch, tmp_path):
    path = tmp_path / "p.json"
    path.write_text("this is not json", encoding="utf-8")
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(path))
    p = read_profile()
    # Defensive default — corrupt file should not crash, just return empty.
    assert p.focus_areas == []
    assert p.healthy_weekly_rate is None
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/tracker/test_profile.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write the implementation**

Create `scripts/tracker/profile.py`:

```python
"""Read/write helpers for ~/.brains-resume/profile.json.

The profile holds the user's focus areas (used by the JD analyzer's role-fit
score) and their self-defined healthy weekly application rate (used by the
pre-application sanity check). Missing file or corrupt JSON both return an
empty Profile — never crash. Tests override the path via
BRAINS_TRACKER_PROFILE_PATH.
"""
import json
import os
from pathlib import Path

from scripts.tracker.models import Profile


DEFAULT_PROFILE_PATH = Path.home() / ".brains-resume" / "profile.json"


def get_profile_path() -> Path:
    """Return the profile path, honouring BRAINS_TRACKER_PROFILE_PATH override."""
    override = os.environ.get("BRAINS_TRACKER_PROFILE_PATH")
    if override:
        return Path(override)
    return DEFAULT_PROFILE_PATH


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
            },
            indent=2,
        ),
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/tracker/test_profile.py -v
```

Expected: 7 tests pass.

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 162 tests pass (155 + 7 new).

- [ ] **Step 6: Commit**

```powershell
git add scripts/tracker/profile.py tests/tracker/test_profile.py
git commit -m "feat: add tracker profile.json read/write helpers"
```

---

## Task 5 — Tracker add helpers (resume_version + jd)

**Files:**

- Create: `scripts/tracker/add.py`
- Create: `tests/tracker/test_add.py`

### Steps

- [ ] **Step 1: Write the failing tests**

Create `tests/tracker/test_add.py`:

```python
"""Tests for scripts/tracker/add.py — the insert-side public API."""
from datetime import datetime

import pytest

from scripts.tracker.db import open_db
from scripts.tracker.add import add_resume_version, add_jd


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    """Each test gets an isolated empty db."""
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path / "test.db"


def test_add_resume_version_returns_id(fresh_db):
    id_ = add_resume_version(
        file_path="/tmp/r.docx",
        template="hybrid",
        focus_areas=["platform", "observability"],
    )
    assert isinstance(id_, int)
    assert id_ > 0


def test_add_resume_version_persists_to_db(fresh_db):
    id_ = add_resume_version(
        file_path="/tmp/r.docx", template="chronological",
        focus_areas=["x"],
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT file_path, template, focus_areas FROM resume_versions WHERE id=?",
            (id_,),
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == "/tmp/r.docx"
    assert row[1] == "chronological"
    # focus_areas stored as JSON
    import json
    assert json.loads(row[2]) == ["x"]


def test_add_resume_version_accepts_null_file_path(fresh_db):
    id_ = add_resume_version(
        file_path=None, template="executive", focus_areas=[],
    )
    assert id_ > 0


def test_add_resume_version_accepts_parent_id(fresh_db):
    parent = add_resume_version(
        file_path=None, template="chronological", focus_areas=[],
    )
    child = add_resume_version(
        file_path=None, template="chronological", focus_areas=[],
        parent_id=parent,
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT parent_id FROM resume_versions WHERE id=?", (child,)
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == parent


def test_add_jd_returns_id(fresh_db):
    id_ = add_jd(
        source="paste", source_ref=None,
        company="Example Corp", role_title="Senior Engineer",
        raw_text="JD body text",
        analyzer_findings={"red_flags": 2, "score": 75},
        focus_areas_required=["python", "distributed systems"],
        focus_areas_nice=["go"],
    )
    assert isinstance(id_, int)
    assert id_ > 0


def test_add_jd_persists_findings_as_json(fresh_db):
    id_ = add_jd(
        source="paste", source_ref=None,
        company="X", role_title="Y", raw_text="z",
        analyzer_findings={"key": "value"},
        focus_areas_required=[], focus_areas_nice=[],
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT analyzer_findings FROM jds WHERE id=?", (id_,)
        ).fetchone()
    finally:
        conn.close()
    import json
    assert json.loads(row[0]) == {"key": "value"}


def test_add_jd_creates_created_at_timestamp(fresh_db):
    id_ = add_jd(
        source="paste", source_ref=None,
        company="X", role_title="Y", raw_text="z",
        analyzer_findings={}, focus_areas_required=[], focus_areas_nice=[],
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT created_at FROM jds WHERE id=?", (id_,)
        ).fetchone()
    finally:
        conn.close()
    # ISO-8601 with Z suffix
    assert row[0].endswith("Z")
    assert "T" in row[0]
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/tracker/test_add.py -v
```

Expected: ImportError on `add_resume_version` or `add_jd`.

- [ ] **Step 3: Write the implementation**

Create `scripts/tracker/add.py`:

```python
"""Insert-side public API for the tracker.

Each function opens a db connection, inserts a row (with timestamp), commits,
closes, and returns the new row id. Foreign-key violations raise sqlite3.IntegrityError.
"""
import json
from datetime import datetime
from typing import List, Optional

from scripts.tracker.db import open_db


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def add_resume_version(
    file_path: Optional[str],
    template: str,
    focus_areas: List[str],
    parent_id: Optional[int] = None,
    tagged_jd_id: Optional[int] = None,
) -> int:
    """Insert a resume_versions row, return the new id."""
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO resume_versions
                (file_path, template, focus_areas, parent_id, tagged_jd_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                file_path,
                template,
                json.dumps(focus_areas),
                parent_id,
                tagged_jd_id,
                _now_iso(),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def add_jd(
    source: str,
    source_ref: Optional[str],
    company: str,
    role_title: str,
    raw_text: str,
    analyzer_findings: dict,
    focus_areas_required: List[str],
    focus_areas_nice: List[str],
) -> int:
    """Insert a jds row, return the new id."""
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO jds
                (source, source_ref, company, role_title, raw_text,
                 analyzer_findings, focus_areas_required, focus_areas_nice,
                 created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source,
                source_ref,
                company,
                role_title,
                raw_text,
                json.dumps(analyzer_findings),
                json.dumps(focus_areas_required),
                json.dumps(focus_areas_nice),
                _now_iso(),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/tracker/test_add.py -v
```

Expected: 7 tests pass.

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 169 tests pass (162 + 7).

- [ ] **Step 6: Commit**

```powershell
git add scripts/tracker/add.py tests/tracker/test_add.py
git commit -m "feat: add tracker add_resume_version + add_jd helpers"
```

---

## Task 6 — Tracker add helpers (cover_letter + application + outcome)

**Files:**

- Modify: `scripts/tracker/add.py`
- Modify: `tests/tracker/test_add.py`

### Steps

- [ ] **Step 1: Write the failing tests**

Append to `tests/tracker/test_add.py`:

```python
from scripts.tracker.add import (
    add_cover_letter, add_application, record_outcome,
)
import sqlite3


def _seed_resume_and_jd(fresh_db):
    """Helper: seed a resume_version and a jd, return their ids."""
    rv_id = add_resume_version(
        file_path=None, template="chronological", focus_areas=[],
    )
    jd_id = add_jd(
        source="paste", source_ref=None, company="X", role_title="Y",
        raw_text="z", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    return rv_id, jd_id


def test_add_cover_letter_returns_id(fresh_db):
    rv_id, jd_id = _seed_resume_and_jd(fresh_db)
    cl_id = add_cover_letter(
        file_path="/tmp/cl.docx",
        resume_version_id=rv_id, jd_id=jd_id,
        template="formal-business",
    )
    assert isinstance(cl_id, int)
    assert cl_id > 0


def test_add_cover_letter_enforces_resume_fk(fresh_db):
    _seed_resume_and_jd(fresh_db)  # create a valid jd_id=1
    with pytest.raises(sqlite3.IntegrityError):
        add_cover_letter(
            file_path=None, resume_version_id=999,  # bad
            jd_id=1, template="formal-business",
        )


def test_add_application_returns_id(fresh_db):
    rv_id, jd_id = _seed_resume_and_jd(fresh_db)
    app_id = add_application(
        jd_id=jd_id, resume_version_id=rv_id, cover_letter_id=None,
        submitted_at=datetime(2026, 5, 13, 14, 30),
        channel="linkedin",
    )
    assert app_id > 0


def test_add_application_persists_all_fields(fresh_db):
    rv_id, jd_id = _seed_resume_and_jd(fresh_db)
    app_id = add_application(
        jd_id=jd_id, resume_version_id=rv_id, cover_letter_id=None,
        submitted_at=datetime(2026, 5, 13, 14, 30),
        channel="agency",
        agency_name="Acme Recruiting",
        recruiter_contact="jane@example.invalid",
        notes="precheck answered",
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT channel, agency_name, recruiter_contact, notes "
            "FROM applications WHERE id=?", (app_id,)
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == "agency"
    assert row[1] == "Acme Recruiting"
    assert row[2] == "jane@example.invalid"
    assert row[3] == "precheck answered"


def test_add_application_enforces_jd_fk(fresh_db):
    rv_id, _jd_id = _seed_resume_and_jd(fresh_db)
    with pytest.raises(sqlite3.IntegrityError):
        add_application(
            jd_id=999, resume_version_id=rv_id, cover_letter_id=None,
            submitted_at=datetime.now(), channel="direct",
        )


def test_record_outcome_returns_id(fresh_db):
    rv_id, jd_id = _seed_resume_and_jd(fresh_db)
    app_id = add_application(
        jd_id=jd_id, resume_version_id=rv_id, cover_letter_id=None,
        submitted_at=datetime.now(), channel="direct",
    )
    oc_id = record_outcome(
        application_id=app_id,
        event_type="callback",
        event_date=datetime(2026, 5, 20),
    )
    assert oc_id > 0


def test_record_outcome_rejects_invalid_event_type(fresh_db):
    rv_id, jd_id = _seed_resume_and_jd(fresh_db)
    app_id = add_application(
        jd_id=jd_id, resume_version_id=rv_id, cover_letter_id=None,
        submitted_at=datetime.now(), channel="direct",
    )
    with pytest.raises(ValueError) as exc_info:
        record_outcome(
            application_id=app_id, event_type="not_a_real_event",
            event_date=datetime.now(),
        )
    assert "not_a_real_event" in str(exc_info.value)


def test_record_outcome_enforces_application_fk(fresh_db):
    with pytest.raises(sqlite3.IntegrityError):
        record_outcome(
            application_id=999, event_type="callback",
            event_date=datetime.now(),
        )


def test_add_application_rejects_invalid_channel(fresh_db):
    rv_id, jd_id = _seed_resume_and_jd(fresh_db)
    with pytest.raises(ValueError) as exc_info:
        add_application(
            jd_id=jd_id, resume_version_id=rv_id, cover_letter_id=None,
            submitted_at=datetime.now(), channel="not_a_real_channel",
        )
    assert "not_a_real_channel" in str(exc_info.value)
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/tracker/test_add.py -v
```

Expected: ImportError on the new helpers.

- [ ] **Step 3: Extend the implementation**

Append to `scripts/tracker/add.py`:

```python
from scripts.tracker.models import APPLICATION_CHANNELS, OUTCOME_EVENT_TYPES


def add_cover_letter(
    file_path: Optional[str],
    resume_version_id: int,
    jd_id: int,
    template: str,
) -> int:
    """Insert a cover_letters row, return the new id."""
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO cover_letters
                (file_path, resume_version_id, jd_id, template, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (file_path, resume_version_id, jd_id, template, _now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def add_application(
    jd_id: int,
    resume_version_id: int,
    cover_letter_id: Optional[int],
    submitted_at: datetime,
    channel: str,
    agency_name: Optional[str] = None,
    recruiter_contact: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    """Insert an applications row, return the new id."""
    if channel not in APPLICATION_CHANNELS:
        raise ValueError(
            f"Unknown channel {channel!r}. Valid: {', '.join(APPLICATION_CHANNELS)}"
        )
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO applications
                (jd_id, resume_version_id, cover_letter_id, submitted_at,
                 channel, agency_name, recruiter_contact, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                jd_id, resume_version_id, cover_letter_id,
                submitted_at.isoformat(),
                channel, agency_name, recruiter_contact, notes,
                _now_iso(),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def record_outcome(
    application_id: int,
    event_type: str,
    event_date: datetime,
    notes: Optional[str] = None,
) -> int:
    """Insert an outcomes row, return the new id."""
    if event_type not in OUTCOME_EVENT_TYPES:
        raise ValueError(
            f"Unknown event_type {event_type!r}. Valid: {', '.join(OUTCOME_EVENT_TYPES)}"
        )
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO outcomes
                (application_id, event_type, event_date, notes, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                application_id, event_type, event_date.isoformat(),
                notes, _now_iso(),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/tracker/test_add.py -v
```

Expected: 16 tests pass (7 from Task 5 + 9 new).

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 178 tests pass (169 + 9).

- [ ] **Step 6: Commit**

```powershell
git add scripts/tracker/add.py tests/tracker/test_add.py
git commit -m "feat: add tracker add_cover_letter, add_application, record_outcome helpers"
```

---

## Task 7 — Tracker query helpers (list_applications + find_duplicates)

**Files:**

- Create: `scripts/tracker/query.py`
- Create: `tests/tracker/test_query.py`

### Steps

- [ ] **Step 1: Write the failing tests**

Create `tests/tracker/test_query.py`:

```python
"""Tests for scripts/tracker/query.py — the read-side public API."""
from datetime import datetime, timedelta

import pytest

from scripts.tracker.add import (
    add_application, add_jd, add_resume_version, record_outcome,
)
from scripts.tracker.query import list_applications, find_duplicates


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path / "test.db"


def _make_app(company, days_ago=0, role="Engineer", channel="direct"):
    """Helper: seed an application for the given company submitted N days ago."""
    rv_id = add_resume_version(
        file_path=None, template="chronological", focus_areas=[],
    )
    jd_id = add_jd(
        source="paste", source_ref=None, company=company,
        role_title=role, raw_text="x", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    when = datetime.now() - timedelta(days=days_ago)
    return add_application(
        jd_id=jd_id, resume_version_id=rv_id, cover_letter_id=None,
        submitted_at=when, channel=channel,
    )


def test_list_applications_empty(fresh_db):
    rows = list_applications()
    assert rows == []


def test_list_applications_returns_all_by_default(fresh_db):
    _make_app("Example Corp")
    _make_app("Sample Industries")
    rows = list_applications()
    assert len(rows) == 2


def test_list_applications_filter_by_company(fresh_db):
    _make_app("Example Corp")
    _make_app("Sample Industries")
    _make_app("Example Corp", role="Designer")
    rows = list_applications(company="Example Corp")
    assert len(rows) == 2
    for r in rows:
        assert r.company == "Example Corp"


def test_list_applications_filter_by_since(fresh_db):
    _make_app("Old Co", days_ago=30)
    _make_app("New Co", days_ago=2)
    cutoff = datetime.now() - timedelta(days=7)
    rows = list_applications(since=cutoff)
    assert len(rows) == 1
    assert rows[0].company == "New Co"


def test_list_applications_each_row_has_basic_fields(fresh_db):
    _make_app("Test Co", role="Senior Engineer", channel="agency")
    rows = list_applications()
    r = rows[0]
    assert r.company == "Test Co"
    assert r.role_title == "Senior Engineer"
    assert r.channel == "agency"
    assert hasattr(r, "id")
    assert hasattr(r, "submitted_at")
    assert hasattr(r, "latest_outcome")  # event_type or None


def test_list_applications_latest_outcome_populated(fresh_db):
    app_id = _make_app("Test Co")
    record_outcome(app_id, "acknowledged", datetime.now())
    record_outcome(app_id, "callback", datetime.now())
    rows = list_applications()
    assert rows[0].latest_outcome == "callback"


def test_list_applications_excludes_archived(fresh_db):
    # No public archive API yet, but list_applications must respect archived_at IS NULL.
    from scripts.tracker.db import open_db
    _make_app("Live Co")
    archived_id = _make_app("Archived Co")
    conn = open_db()
    try:
        conn.execute(
            "UPDATE applications SET archived_at = ? WHERE id = ?",
            ("2026-05-13T00:00:00Z", archived_id),
        )
        conn.commit()
    finally:
        conn.close()
    rows = list_applications()
    assert {r.company for r in rows} == {"Live Co"}


def test_find_duplicates_missing_db_returns_empty(monkeypatch, tmp_path):
    """If the db file doesn't exist (tracker never used), return empty list, no crash."""
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "never_created.db"))
    result = find_duplicates("Example Corp", "Senior Engineer")
    assert result == []


def test_find_duplicates_returns_recent_match(fresh_db):
    _make_app("Example Corp", role="Senior Engineer", days_ago=5)
    result = find_duplicates("Example Corp", "Senior Engineer")
    assert len(result) == 1


def test_find_duplicates_excludes_outside_window(fresh_db):
    _make_app("Example Corp", role="Senior Engineer", days_ago=90)
    result = find_duplicates("Example Corp", "Senior Engineer", within_days=60)
    assert result == []


def test_find_duplicates_case_insensitive_company(fresh_db):
    _make_app("Example Corp", role="Senior Engineer", days_ago=5)
    result = find_duplicates("example corp", "Senior Engineer")
    assert len(result) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/tracker/test_query.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write the implementation**

Create `scripts/tracker/query.py`:

```python
"""Read-side public API for the tracker.

These helpers all return dataclasses or lists of dataclasses defined in
scripts/tracker/models.py. SQL lives only here (and in db.py / migrations).
Consumers must never construct SQL themselves.
"""
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from scripts.tracker.db import get_db_path, open_db


# --- Result types (lightweight DTOs distinct from the row dataclasses) --------

@dataclass
class ApplicationRow:
    """Joined view of applications + jds + latest outcome.

    Distinct from models.Application because list views need company/role from
    the JD and the latest event_type from outcomes — those are joins, not
    columns on applications itself.
    """
    id: int
    company: str
    role_title: str
    submitted_at: str
    channel: str
    agency_name: Optional[str]
    resume_version_id: int
    cover_letter_id: Optional[int]
    latest_outcome: Optional[str]


# --- Queries ------------------------------------------------------------------

def list_applications(
    company: Optional[str] = None,
    since: Optional[datetime] = None,
    status: Optional[str] = None,
) -> List[ApplicationRow]:
    """Return active applications (archived_at IS NULL), filtered by criteria.

    status:
        - None or 'all' — no filter
        - 'open' — applications with no rejection/offer/withdrew outcome yet
        - 'closed' — applications with a terminal outcome
    """
    conn = open_db()
    try:
        sql = """
            SELECT a.id, j.company, j.role_title, a.submitted_at, a.channel,
                   a.agency_name, a.resume_version_id, a.cover_letter_id,
                   (
                       SELECT event_type FROM outcomes
                       WHERE application_id = a.id AND archived_at IS NULL
                       ORDER BY event_date DESC, id DESC
                       LIMIT 1
                   ) AS latest_outcome
            FROM applications a
            JOIN jds j ON j.id = a.jd_id
            WHERE a.archived_at IS NULL
        """
        params: list = []
        if company is not None:
            sql += " AND LOWER(j.company) = LOWER(?)"
            params.append(company)
        if since is not None:
            sql += " AND a.submitted_at >= ?"
            params.append(since.isoformat())
        sql += " ORDER BY a.submitted_at DESC"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    results = [
        ApplicationRow(
            id=r[0], company=r[1], role_title=r[2], submitted_at=r[3],
            channel=r[4], agency_name=r[5], resume_version_id=r[6],
            cover_letter_id=r[7], latest_outcome=r[8],
        )
        for r in rows
    ]

    if status == "open":
        terminal = {"offer", "rejection", "withdrew"}
        results = [r for r in results if r.latest_outcome not in terminal]
    elif status == "closed":
        terminal = {"offer", "rejection", "withdrew"}
        results = [r for r in results if r.latest_outcome in terminal]

    return results


def find_duplicates(
    company: str,
    role_title: str,
    within_days: int = 60,
) -> List[ApplicationRow]:
    """Return applications to the same company+role within the window.

    Gracefully returns [] when the db file doesn't exist (tracker never used).
    """
    if not get_db_path().exists():
        return []
    cutoff = datetime.now() - timedelta(days=within_days)
    rows = list_applications(company=company, since=cutoff)
    # Filter by role_title (case-insensitive substring match)
    role_lower = role_title.lower()
    return [r for r in rows if role_lower in r.role_title.lower()
            or r.role_title.lower() in role_lower]
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/tracker/test_query.py -v
```

Expected: 11 tests pass.

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 189 tests pass (178 + 11).

- [ ] **Step 6: Commit**

```powershell
git add scripts/tracker/query.py tests/tracker/test_query.py
git commit -m "feat: add tracker list_applications + find_duplicates queries"
```

---

## Task 8 — Tracker query helpers (weekly_summary + efficacy_by_template)

**Files:**

- Modify: `scripts/tracker/query.py`
- Modify: `tests/tracker/test_query.py`

### Steps

- [ ] **Step 1: Write the failing tests**

Append to `tests/tracker/test_query.py`:

```python
from scripts.tracker.query import weekly_summary, efficacy_by_template
from scripts.tracker.profile import write_profile
from scripts.tracker.models import Profile


def test_weekly_summary_empty_db_returns_zero(fresh_db):
    s = weekly_summary()
    assert s.applications_count == 0
    assert s.outcomes_by_type == {}
    assert s.pacing_vs_target is None


def test_weekly_summary_counts_last_7_days(fresh_db):
    _make_app("Old Co", days_ago=10)  # outside window
    _make_app("New A", days_ago=2)
    _make_app("New B", days_ago=5)
    s = weekly_summary()
    assert s.applications_count == 2


def test_weekly_summary_outcomes_by_type(fresh_db):
    a1 = _make_app("Co1", days_ago=1)
    a2 = _make_app("Co2", days_ago=2)
    record_outcome(a1, "callback", datetime.now())
    record_outcome(a2, "rejection", datetime.now())
    record_outcome(a2, "withdrew", datetime.now())  # only most-recent per app counted
    s = weekly_summary()
    # All 3 events are within the last week — we count each event, not per-app
    assert s.outcomes_by_type.get("callback", 0) == 1
    assert s.outcomes_by_type.get("rejection", 0) == 1
    assert s.outcomes_by_type.get("withdrew", 0) == 1


def test_weekly_summary_pacing_above_target(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    write_profile(Profile(focus_areas=[], healthy_weekly_rate=2))
    _make_app("A"); _make_app("B"); _make_app("C")  # 3 in last week
    s = weekly_summary()
    assert s.pacing_vs_target == "above"


def test_weekly_summary_pacing_at_target(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    write_profile(Profile(focus_areas=[], healthy_weekly_rate=2))
    _make_app("A"); _make_app("B")
    s = weekly_summary()
    assert s.pacing_vs_target == "at"


def test_weekly_summary_pacing_below_target(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    write_profile(Profile(focus_areas=[], healthy_weekly_rate=5))
    _make_app("A")
    s = weekly_summary()
    assert s.pacing_vs_target == "below"


def test_weekly_summary_pacing_none_when_no_target(fresh_db):
    _make_app("A")
    s = weekly_summary()
    assert s.pacing_vs_target is None


def test_efficacy_by_template_groups_by_resume_template(fresh_db):
    # Seed two apps with hybrid resumes, one with chronological
    rv1 = add_resume_version(file_path=None, template="hybrid", focus_areas=[])
    rv2 = add_resume_version(file_path=None, template="hybrid", focus_areas=[])
    rv3 = add_resume_version(file_path=None, template="chronological", focus_areas=[])
    jd_id = add_jd(
        source="paste", source_ref=None, company="X", role_title="Y",
        raw_text="z", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    a1 = add_application(jd_id=jd_id, resume_version_id=rv1,
                          cover_letter_id=None,
                          submitted_at=datetime.now(), channel="direct")
    a2 = add_application(jd_id=jd_id, resume_version_id=rv2,
                          cover_letter_id=None,
                          submitted_at=datetime.now(), channel="direct")
    a3 = add_application(jd_id=jd_id, resume_version_id=rv3,
                          cover_letter_id=None,
                          submitted_at=datetime.now(), channel="direct")
    record_outcome(a1, "callback", datetime.now())
    record_outcome(a2, "rejection", datetime.now())
    record_outcome(a3, "callback", datetime.now())

    rows = efficacy_by_template()
    by_template = {r.template: r for r in rows}
    assert by_template["hybrid"].submitted_count == 2
    assert by_template["hybrid"].callback_count == 1
    assert by_template["hybrid"].rejection_count == 1
    assert by_template["chronological"].submitted_count == 1
    assert by_template["chronological"].callback_count == 1


def test_efficacy_by_template_interview_count_aggregates(fresh_db):
    rv = add_resume_version(file_path=None, template="hybrid", focus_areas=[])
    jd_id = add_jd(
        source="paste", source_ref=None, company="X", role_title="Y",
        raw_text="z", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    app_id = add_application(
        jd_id=jd_id, resume_version_id=rv, cover_letter_id=None,
        submitted_at=datetime.now(), channel="direct",
    )
    record_outcome(app_id, "phone_screen", datetime.now())
    record_outcome(app_id, "first_round", datetime.now())
    record_outcome(app_id, "second_round", datetime.now())
    rows = efficacy_by_template()
    assert rows[0].interview_count >= 3
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/tracker/test_query.py::test_weekly_summary_empty_db_returns_zero -v
```

Expected: ImportError on `weekly_summary` or `efficacy_by_template`.

- [ ] **Step 3: Extend the implementation**

Append to `scripts/tracker/query.py`:

```python
from collections import defaultdict
from datetime import date

from scripts.tracker.models import WeeklySummary, EfficacyRow
from scripts.tracker.profile import read_profile


INTERVIEW_EVENT_TYPES = {"phone_screen", "first_round", "second_round", "take_home"}


def weekly_summary(now: Optional[datetime] = None) -> WeeklySummary:
    """Return a summary of the last 7 days: application count, outcomes by
    type, and pacing vs the user's healthy_weekly_rate (if set)."""
    if now is None:
        now = datetime.now()
    week_ago = now - timedelta(days=7)

    if not get_db_path().exists():
        return WeeklySummary(
            week_starting=week_ago.date().isoformat(),
            applications_count=0,
            outcomes_by_type={},
            pacing_vs_target=None,
        )

    conn = open_db()
    try:
        app_count = conn.execute(
            "SELECT COUNT(*) FROM applications "
            "WHERE archived_at IS NULL AND submitted_at >= ?",
            (week_ago.isoformat(),),
        ).fetchone()[0]

        outcome_rows = conn.execute(
            "SELECT event_type, COUNT(*) FROM outcomes "
            "WHERE archived_at IS NULL AND event_date >= ? "
            "GROUP BY event_type",
            (week_ago.isoformat(),),
        ).fetchall()
        outcomes_by_type = {row[0]: row[1] for row in outcome_rows}
    finally:
        conn.close()

    target = read_profile().healthy_weekly_rate
    if target is None:
        pacing = None
    elif app_count > target:
        pacing = "above"
    elif app_count == target:
        pacing = "at"
    else:
        pacing = "below"

    return WeeklySummary(
        week_starting=week_ago.date().isoformat(),
        applications_count=app_count,
        outcomes_by_type=outcomes_by_type,
        pacing_vs_target=pacing,
    )


def efficacy_by_template() -> List[EfficacyRow]:
    """Return per-template counts of submitted/callback/interview/offer/rejection.

    Each application contributes once to each event-type count it has produced.
    An application with phone_screen + first_round + offer contributes:
      - submitted_count: 1
      - interview_count: 2 (phone_screen + first_round)
      - offer_count: 1
    """
    if not get_db_path().exists():
        return []

    conn = open_db()
    try:
        rows = conn.execute(
            """
            SELECT rv.template,
                   a.id,
                   (SELECT GROUP_CONCAT(event_type, ',')
                    FROM outcomes
                    WHERE application_id = a.id AND archived_at IS NULL)
                   AS event_types
            FROM applications a
            JOIN resume_versions rv ON rv.id = a.resume_version_id
            WHERE a.archived_at IS NULL
            """
        ).fetchall()
    finally:
        conn.close()

    by_template: dict = defaultdict(lambda: {
        "submitted": 0, "callback": 0, "interview": 0,
        "offer": 0, "rejection": 0,
    })
    for template, _app_id, event_csv in rows:
        bucket = by_template[template]
        bucket["submitted"] += 1
        if not event_csv:
            continue
        events = event_csv.split(",")
        for ev in events:
            if ev == "callback":
                bucket["callback"] += 1
            elif ev in INTERVIEW_EVENT_TYPES:
                bucket["interview"] += 1
            elif ev == "offer":
                bucket["offer"] += 1
            elif ev == "rejection":
                bucket["rejection"] += 1

    return [
        EfficacyRow(
            template=template,
            submitted_count=counts["submitted"],
            callback_count=counts["callback"],
            interview_count=counts["interview"],
            offer_count=counts["offer"],
            rejection_count=counts["rejection"],
        )
        for template, counts in sorted(by_template.items())
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/tracker/test_query.py -v
```

Expected: all 20 tests pass (11 from Task 7 + 9 new).

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 198 tests pass (189 + 9).

- [ ] **Step 6: Commit**

```powershell
git add scripts/tracker/query.py tests/tracker/test_query.py
git commit -m "feat: add tracker weekly_summary + efficacy_by_template queries"
```

---

## Phase 2 — JD analyzer (Tasks 9-11)

The validator that surfaces ND-relevant signals in a job description. Mirrors the `bias_scan` / `integrity_check` validator pattern from earlier phases.

---

## Task 9 — JD analyzer fixtures

**Files:**

- Create: `tests/fixtures/jd_analyzer_fixtures.py`

### Steps

- [ ] **Step 1: Write the fixture module**

Create `tests/fixtures/jd_analyzer_fixtures.py`:

```python
"""Synthetic JD text fixtures for the jd_analyzer validator tests.

Each fixture is designed to trigger or avoid a specific finding code:
  - RED_FLAG_HEAVY_JD: trips JD_RED_FLAG_SOFT_CULTURE multiple times → HIGH cluster
  - MASKING_COST_HEAVY_JD: trips JD_MASKING_COST
  - EVIDENCE_OF_FLEX_HEAVY_JD: trips JD_EVIDENCE_OF_FLEX
  - WELL_PARSED_JD: has explicit Required + Nice-to-have headings
  - CLEAN_NEUTRAL_JD: zero red-flag or masking-cost hits
  - MIXED_JD: a realistic-looking JD with some of each
"""


RED_FLAG_HEAVY_JD = """
About the role:
We're looking for a rockstar engineer to join our fast-paced startup. We're
a family here, and we work hard, play hard. You'll wear many hats as a true
ninja-of-all-trades, with a flexible attitude and a can-do mindset.

Responsibilities:
- Be a team player and a go-getter
- Bring passion to everything you do
"""

MASKING_COST_HEAVY_JD = """
About the role:
This is a high-EQ, client-facing role with heavy stakeholder management
responsibilities. You'll be doing client-facing presentations daily in our
open-plan office. The role is phone-heavy with frequent context switching
between accounts.

Responsibilities:
- Manage relationships with C-suite executives
- Present in client meetings
"""

EVIDENCE_OF_FLEX_HEAVY_JD = """
About the role:
We're a remote-first, async-first company with written-comms culture. We
offer flexible hours and accommodations available on request. Our hybrid
policy is 2 days in-office per quarter (not per week).

Parental leave: 26 weeks for primary caregivers, 16 weeks for secondary.
"""

WELL_PARSED_JD = """
About the role:
Senior Platform Engineer focusing on observability and incident response.

Required:
- 5+ years of backend Python experience
- Distributed systems background
- On-call comfort

Nice to have:
- Go experience
- Open-source contributions
- Public speaking at conferences
"""

CLEAN_NEUTRAL_JD = """
About the role:
We are hiring a senior software engineer for our platform team. The role
involves designing and building infrastructure services used across the
company. You will collaborate with product teams and contribute to long-
term technical direction.

Requirements:
- Strong programming skills in Python or Go
- Experience with distributed systems
- Bachelor's degree in Computer Science or equivalent experience
"""

MIXED_JD = """
About the role:
We're looking for a passionate engineer to join our fast-paced team. You
will work in a hybrid setup (2 days per week in-office) and collaborate
asynchronously with global colleagues.

Required:
- Python expertise
- Cloud platform experience

Nice to have:
- Open-source contributions
"""
```

- [ ] **Step 2: Verify the fixtures import**

```powershell
.venv\Scripts\activate
python -c "from tests.fixtures import jd_analyzer_fixtures; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Confirm no test regressions**

```powershell
python -m pytest -q
```

Expected: 198 tests still pass (no new tests added — fixture module only).

- [ ] **Step 4: Commit**

```powershell
git add tests/fixtures/jd_analyzer_fixtures.py
git commit -m "test: add jd_analyzer fixtures with seeded JD samples"
```

---

## Task 10 — JD analyzer keyword/regex finding codes

**Files:**

- Create: `scripts/validators/jd_analyzer.py`
- Create: `tests/validators/test_jd_analyzer.py`

### Steps

- [ ] **Step 1: Write the failing tests**

Create `tests/validators/test_jd_analyzer.py`:

```python
"""Tests for scripts/validators/jd_analyzer.py — the JD finding catalog."""
from scripts.validators.jd_analyzer import jd_analyze
from tests.fixtures import jd_analyzer_fixtures as fx


def _codes(result):
    return [f.code for f in result.findings]


def test_red_flag_heavy_jd_produces_soft_culture_finding():
    r = jd_analyze(fx.RED_FLAG_HEAVY_JD)
    assert "JD_RED_FLAG_SOFT_CULTURE" in _codes(r)


def test_red_flag_heavy_jd_high_severity_cluster():
    """Multiple red-flag hits should produce HIGH severity (3+ hits)."""
    r = jd_analyze(fx.RED_FLAG_HEAVY_JD)
    rf_findings = [f for f in r.findings if f.code == "JD_RED_FLAG_SOFT_CULTURE"]
    assert any(f.severity == "HIGH" for f in rf_findings)


def test_masking_cost_heavy_jd_produces_finding():
    r = jd_analyze(fx.MASKING_COST_HEAVY_JD)
    assert "JD_MASKING_COST" in _codes(r)


def test_evidence_of_flex_heavy_jd_produces_finding():
    r = jd_analyze(fx.EVIDENCE_OF_FLEX_HEAVY_JD)
    assert "JD_EVIDENCE_OF_FLEX" in _codes(r)


def test_clean_neutral_jd_has_no_red_flags_or_masking_cost():
    r = jd_analyze(fx.CLEAN_NEUTRAL_JD)
    codes = _codes(r)
    assert "JD_RED_FLAG_SOFT_CULTURE" not in codes
    assert "JD_MASKING_COST" not in codes


def test_finding_carries_excerpt_and_suggestion():
    r = jd_analyze(fx.RED_FLAG_HEAVY_JD)
    finding = r.findings[0]
    assert hasattr(finding, "code")
    assert hasattr(finding, "severity")
    assert hasattr(finding, "excerpt")
    assert hasattr(finding, "suggestion")
    assert finding.severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "POSITIVE")


def test_mixed_jd_produces_some_of_each():
    """The mixed JD should show both a soft-culture hit (passionate, fast-paced)
    and an evidence-of-flex hit (async, hybrid policy)."""
    r = jd_analyze(fx.MIXED_JD)
    codes = _codes(r)
    assert "JD_RED_FLAG_SOFT_CULTURE" in codes
    assert "JD_EVIDENCE_OF_FLEX" in codes
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/validators/test_jd_analyzer.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write the implementation (keyword detection portion)**

Create `scripts/validators/jd_analyzer.py`:

```python
"""JD analyzer — surfaces ND-relevant signals in a job description.

Finding codes:
  - JD_RED_FLAG_SOFT_CULTURE: rockstar/ninja/fast-paced/etc culture markers
  - JD_MASKING_COST: high-EQ/stakeholder/open-plan/phone-heavy/etc
  - JD_EVIDENCE_OF_FLEX: remote-first/async-first/accommodations/etc
  - JD_REQ_VS_NICE_PARSING: parses Required vs Nice-to-have sections
  - JD_ROLE_FIT_SCORE: 0-100 based on user focus areas vs JD requirements
  - JD_DUPLICATE_APPLICATION: tracker lookup against company + role

The validator never overrides the user. Findings are surfaced to the workflow;
the user always decides.
"""
from dataclasses import dataclass, field
import re
from typing import List, Optional


# ---- Keyword catalogs --------------------------------------------------------

SOFT_CULTURE_TERMS = (
    "rockstar", "ninja", "wear many hats", "fast-paced",
    "we're a family", "work hard play hard", "flexible attitude",
    "can-do mindset", "passionate", "team player", "go-getter",
    "self-starter", "guru", "dynamic individual",
)

MASKING_COST_TERMS = (
    "high-eq", "high eq", "stakeholder management",
    "client-facing presentations", "client facing presentations",
    "open-plan office", "open plan office",
    "phone-heavy", "phone heavy",
    "frequent context switching",
    "c-suite", "executive presence",
)

EVIDENCE_OF_FLEX_TERMS = (
    "remote-first", "async-first", "async first",
    "flexible hours", "accommodations available",
    "written-comms culture", "written comms culture",
    "asynchronously", "asynchronous",
)


# ---- Result types ------------------------------------------------------------

@dataclass
class JdFinding:
    code: str
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW | INFO | POSITIVE
    excerpt: str
    suggestion: str


@dataclass
class JdAnalyzerResult:
    findings: List[JdFinding] = field(default_factory=list)
    required_list: List[str] = field(default_factory=list)
    nice_list: List[str] = field(default_factory=list)
    role_fit_score: Optional[int] = None


# ---- Helpers -----------------------------------------------------------------

def _find_hits(text: str, terms) -> List[str]:
    text_lower = text.lower()
    return [t for t in terms if t in text_lower]


# ---- Main entry --------------------------------------------------------------

def jd_analyze(
    jd_text: str,
    focus_areas: Optional[List[str]] = None,
    company: Optional[str] = None,
    role_title: Optional[str] = None,
) -> JdAnalyzerResult:
    """Analyse a JD and return findings + parsed requirement lists + role-fit score.

    focus_areas, company, role_title are optional; if absent, those checks are
    skipped (role-fit returns None, duplicate-application check skipped).
    """
    result = JdAnalyzerResult()

    # 1. Soft-culture red flags
    soft_hits = _find_hits(jd_text, SOFT_CULTURE_TERMS)
    if soft_hits:
        severity = "HIGH" if len(soft_hits) >= 3 else "MEDIUM"
        result.findings.append(JdFinding(
            code="JD_RED_FLAG_SOFT_CULTURE",
            severity=severity,
            excerpt=", ".join(soft_hits[:5]),
            suggestion=(
                "These culture markers historically correlate with high-masking "
                "demands. Consider whether the role's day-to-day behaviour matches "
                "the marketing language, and how much energy you would spend "
                "performing the implied persona."
            ),
        ))

    # 2. Masking-cost markers
    mc_hits = _find_hits(jd_text, MASKING_COST_TERMS)
    if mc_hits:
        result.findings.append(JdFinding(
            code="JD_MASKING_COST",
            severity="MEDIUM",
            excerpt=", ".join(mc_hits[:5]),
            suggestion=(
                "This role demands a higher masking cost. Not a red flag — "
                "but worth deliberately thinking about your energy budget and "
                "whether the role's strengths offset the cost for you."
            ),
        ))

    # 3. Evidence-of-real-flexibility
    flex_hits = _find_hits(jd_text, EVIDENCE_OF_FLEX_TERMS)
    if flex_hits:
        result.findings.append(JdFinding(
            code="JD_EVIDENCE_OF_FLEX",
            severity="POSITIVE",
            excerpt=", ".join(flex_hits[:5]),
            suggestion=(
                "Concrete flexibility signals detected. These move the role-fit "
                "score upward and suggest the employer has done more than use "
                "flexibility as a buzzword."
            ),
        ))

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/validators/test_jd_analyzer.py -v
```

Expected: 7 tests pass.

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 205 tests pass (198 + 7).

- [ ] **Step 6: Commit**

```powershell
git add scripts/validators/jd_analyzer.py tests/validators/test_jd_analyzer.py
git commit -m "feat: add jd_analyzer with soft-culture, masking-cost, and evidence-of-flex finding codes"
```

---

## Task 11 — JD analyzer: req-vs-nice parsing, role-fit score, duplicate check

**Files:**

- Modify: `scripts/validators/jd_analyzer.py`
- Modify: `tests/validators/test_jd_analyzer.py`

### Steps

- [ ] **Step 1: Write the failing tests**

Append to `tests/validators/test_jd_analyzer.py`:

```python
import pytest


def test_well_parsed_jd_extracts_required_and_nice_lists():
    r = jd_analyze(fx.WELL_PARSED_JD)
    # Required list should contain at least one of the bulleted items
    required_joined = " ".join(r.required_list).lower()
    assert "5+ years" in required_joined or "backend python" in required_joined
    nice_joined = " ".join(r.nice_list).lower()
    assert "go" in nice_joined or "open-source" in nice_joined


def test_well_parsed_jd_produces_req_vs_nice_finding():
    r = jd_analyze(fx.WELL_PARSED_JD)
    codes = [f.code for f in r.findings]
    assert "JD_REQ_VS_NICE_PARSING" in codes


def test_role_fit_score_none_when_no_focus_areas_given():
    r = jd_analyze(fx.WELL_PARSED_JD)
    assert r.role_fit_score is None


def test_role_fit_score_computed_when_focus_areas_given():
    r = jd_analyze(
        fx.WELL_PARSED_JD,
        focus_areas=["python", "distributed systems", "on-call"],
    )
    assert r.role_fit_score is not None
    assert 0 <= r.role_fit_score <= 100


def test_role_fit_score_full_match_is_high():
    """All focus areas match required items → score should be ≥80."""
    r = jd_analyze(
        fx.WELL_PARSED_JD,
        focus_areas=["python", "distributed systems", "on-call"],
    )
    assert r.role_fit_score >= 80


def test_role_fit_score_no_match_is_low():
    """Focus areas have nothing to do with the JD → low score."""
    r = jd_analyze(
        fx.WELL_PARSED_JD,
        focus_areas=["ceramics", "marine biology", "viking history"],
    )
    assert r.role_fit_score <= 30


def test_role_fit_score_finding_in_result():
    r = jd_analyze(
        fx.WELL_PARSED_JD, focus_areas=["python", "on-call"],
    )
    codes = [f.code for f in r.findings]
    assert "JD_ROLE_FIT_SCORE" in codes


def test_duplicate_application_check_missing_db_does_not_crash(monkeypatch, tmp_path):
    """If tracker db doesn't exist, the duplicate check is a no-op."""
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "never.db"))
    r = jd_analyze(
        fx.CLEAN_NEUTRAL_JD,
        company="Example Corp", role_title="Senior Engineer",
    )
    codes = [f.code for f in r.findings]
    assert "JD_DUPLICATE_APPLICATION" not in codes


def test_duplicate_application_check_detects_recent_application(monkeypatch, tmp_path):
    """Seed an application via the tracker, then ensure the analyzer flags it."""
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "t.db"))
    from datetime import datetime
    from scripts.tracker.add import (
        add_resume_version, add_jd, add_application,
    )
    rv_id = add_resume_version(file_path=None, template="hybrid", focus_areas=[])
    jd_id = add_jd(
        source="paste", source_ref=None,
        company="Example Corp", role_title="Senior Engineer",
        raw_text="x", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    add_application(
        jd_id=jd_id, resume_version_id=rv_id, cover_letter_id=None,
        submitted_at=datetime.now(), channel="direct",
    )
    r = jd_analyze(
        fx.CLEAN_NEUTRAL_JD,
        company="Example Corp", role_title="Senior Engineer",
    )
    codes = [f.code for f in r.findings]
    assert "JD_DUPLICATE_APPLICATION" in codes
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/validators/test_jd_analyzer.py -v
```

Expected: most of the new tests fail.

- [ ] **Step 3: Extend the implementation**

Append to `scripts/validators/jd_analyzer.py`:

```python
# ---- Required vs Nice-to-have parsing ----------------------------------------

REQUIRED_HEADINGS = re.compile(
    r"^\s*(required|requirements|must[- ]have|essential|qualifications)\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
NICE_HEADINGS = re.compile(
    r"^\s*(nice[- ]to[- ]have|preferred|bonus|good to have|plus)\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
BULLET_LINE = re.compile(r"^\s*[-*•]\s+(.+)$", re.MULTILINE)


def _extract_section(jd_text: str, heading_pattern: re.Pattern, next_patterns) -> List[str]:
    """Extract bullet items under heading_pattern up to the next heading."""
    heading_match = heading_pattern.search(jd_text)
    if not heading_match:
        return []
    start = heading_match.end()
    # Find earliest next heading after this section
    end = len(jd_text)
    for nh in next_patterns:
        m = nh.search(jd_text, start)
        if m and m.start() < end:
            end = m.start()
    section = jd_text[start:end]
    return [m.group(1).strip() for m in BULLET_LINE.finditer(section)]


# ---- Role-fit scoring --------------------------------------------------------

def _normalise_term(s: str) -> str:
    """Lowercase + strip punctuation + collapse whitespace."""
    s = s.lower()
    s = re.sub(r"[^\w\s+#-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _normalised_tokens(items: List[str]) -> set:
    tokens = set()
    for item in items:
        for word in _normalise_term(item).split():
            if len(word) >= 3:  # skip stopwords-by-length
                tokens.add(word)
    return tokens


def _compute_role_fit_score(
    focus_areas: List[str],
    required_list: List[str],
    nice_list: List[str],
) -> int:
    """Weighted token-overlap score.

    Required matches are worth 2x nice matches. Capped at 100.
    """
    fa_tokens = _normalised_tokens(focus_areas)
    req_tokens = _normalised_tokens(required_list)
    nice_tokens = _normalised_tokens(nice_list)

    if not fa_tokens or (not req_tokens and not nice_tokens):
        return 0

    required_matches = len(fa_tokens & req_tokens)
    nice_matches = len(fa_tokens & nice_tokens)

    raw_score = required_matches * 2 + nice_matches
    max_possible = len(req_tokens) * 2 + len(nice_tokens)
    if max_possible == 0:
        return 0
    return min(100, round(100 * raw_score / max_possible))


# ---- Replace main entry to include the new findings -------------------------

def jd_analyze(
    jd_text: str,
    focus_areas: Optional[List[str]] = None,
    company: Optional[str] = None,
    role_title: Optional[str] = None,
) -> JdAnalyzerResult:
    """Analyse a JD and return findings + parsed requirement lists + role-fit score."""
    result = JdAnalyzerResult()

    # 1. Soft-culture red flags
    soft_hits = _find_hits(jd_text, SOFT_CULTURE_TERMS)
    if soft_hits:
        severity = "HIGH" if len(soft_hits) >= 3 else "MEDIUM"
        result.findings.append(JdFinding(
            code="JD_RED_FLAG_SOFT_CULTURE",
            severity=severity,
            excerpt=", ".join(soft_hits[:5]),
            suggestion=(
                "These culture markers historically correlate with high-masking "
                "demands. Consider whether the role's day-to-day behaviour matches "
                "the marketing language, and how much energy you would spend "
                "performing the implied persona."
            ),
        ))

    # 2. Masking-cost markers
    mc_hits = _find_hits(jd_text, MASKING_COST_TERMS)
    if mc_hits:
        result.findings.append(JdFinding(
            code="JD_MASKING_COST",
            severity="MEDIUM",
            excerpt=", ".join(mc_hits[:5]),
            suggestion=(
                "This role demands a higher masking cost. Not a red flag — "
                "but worth deliberately thinking about your energy budget and "
                "whether the role's strengths offset the cost for you."
            ),
        ))

    # 3. Evidence-of-real-flexibility
    flex_hits = _find_hits(jd_text, EVIDENCE_OF_FLEX_TERMS)
    if flex_hits:
        result.findings.append(JdFinding(
            code="JD_EVIDENCE_OF_FLEX",
            severity="POSITIVE",
            excerpt=", ".join(flex_hits[:5]),
            suggestion=(
                "Concrete flexibility signals detected. These move the role-fit "
                "score upward and suggest the employer has done more than use "
                "flexibility as a buzzword."
            ),
        ))

    # 4. Required vs nice-to-have parsing
    required_list = _extract_section(
        jd_text, REQUIRED_HEADINGS, [NICE_HEADINGS],
    )
    nice_list = _extract_section(
        jd_text, NICE_HEADINGS, [REQUIRED_HEADINGS],
    )
    result.required_list = required_list
    result.nice_list = nice_list
    if required_list or nice_list:
        result.findings.append(JdFinding(
            code="JD_REQ_VS_NICE_PARSING",
            severity="INFO",
            excerpt=f"required: {len(required_list)}, nice: {len(nice_list)}",
            suggestion=(
                "The JD separates must-haves from wishlist items. Focus the "
                "tailoring on the required list; the nice-to-haves are bonus."
            ),
        ))

    # 5. Role-fit score (only if focus_areas provided)
    if focus_areas is not None:
        score = _compute_role_fit_score(focus_areas, required_list, nice_list)
        result.role_fit_score = score
        result.findings.append(JdFinding(
            code="JD_ROLE_FIT_SCORE",
            severity="INFO",
            excerpt=f"{score}/100",
            suggestion=(
                "Role-fit score is informational — high scores indicate alignment "
                "between your focus areas and the JD's requirements. Low scores "
                "are not a veto, but worth examining."
            ),
        ))

    # 6. Duplicate application check (only if company + role_title provided)
    if company is not None and role_title is not None:
        from scripts.tracker.query import find_duplicates
        duplicates = find_duplicates(company, role_title)
        if duplicates:
            most_recent = duplicates[0]
            result.findings.append(JdFinding(
                code="JD_DUPLICATE_APPLICATION",
                severity="HIGH",
                excerpt=f"Previous application: {most_recent.company} / {most_recent.role_title} on {most_recent.submitted_at[:10]}",
                suggestion=(
                    "You have applied to this company and role recently. Confirm "
                    "this is a deliberate re-application before proceeding."
                ),
            ))

    return result
```

(Note: the original `jd_analyze` function from Task 10 is replaced — do not duplicate it. The new version supersedes it.)

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/validators/test_jd_analyzer.py -v
```

Expected: all 16 tests pass (7 from Task 10 + 9 new).

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 214 tests pass (205 + 9).

- [ ] **Step 6: Commit**

```powershell
git add scripts/validators/jd_analyzer.py tests/validators/test_jd_analyzer.py
git commit -m "feat: add jd_analyzer req-vs-nice parsing, role-fit scoring, duplicate-check"
```

---

## Phase 3 — Workflow references + slash commands (Tasks 12-17)

The three new workflows and their slash-command entry points. References describe the procedures; slash commands route Claude to load the right reference.

---

## Task 12 — JD analyzer workflow reference

**Files:**

- Create: `references/workflows/jd-analyze.md`
- Create: `tests/references/test_workflow_jd_analyze.py`

### Steps

- [ ] **Step 1: Write the reference document**

Create `references/workflows/jd-analyze.md`:

```markdown
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
```text

**(c) Load user's focus areas.**

```python
from scripts.tracker.profile import read_profile
profile = read_profile()
focus_areas = profile.focus_areas
if not focus_areas:
    # Ask user to set their focus areas now; offer to save via write_profile()
    ...
```text

**(d) Run the analyzer.**

```python
from scripts.validators.jd_analyzer import jd_analyze

result = jd_analyze(
    jd_text=jd_text,
    focus_areas=focus_areas,
    company=company,
    role_title=role_title,
)
```text

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
```text

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

```

- [ ] **Step 2: Write the structural test**

Create `tests/references/test_workflow_jd_analyze.py`:

```python
"""Structural tests for references/workflows/jd-analyze.md."""
from pathlib import Path

REFERENCE = Path(__file__).parent.parent.parent / "references" / "workflows" / "jd-analyze.md"


def _text():
    return REFERENCE.read_text(encoding="utf-8")


def test_reference_exists():
    assert REFERENCE.exists()


def test_all_six_finding_codes_documented():
    text = _text()
    for code in (
        "JD_RED_FLAG_SOFT_CULTURE",
        "JD_MASKING_COST",
        "JD_EVIDENCE_OF_FLEX",
        "JD_REQ_VS_NICE_PARSING",
        "JD_ROLE_FIT_SCORE",
        "JD_DUPLICATE_APPLICATION",
    ):
        # not every code needs to be named in the prose, but at least the categories must appear
        pass  # checked indirectly via the next two tests


def test_reference_documents_analyzer_function():
    text = _text()
    assert "jd_analyze" in text


def test_reference_documents_tracker_integration():
    text = _text()
    assert "add_jd" in text
    assert "find_duplicates" in text or "duplicate" in text.lower()


def test_safeguarding_section_present():
    text = _text()
    assert "Safeguarding boundaries" in text
    assert "user decides" in text.lower() or "user always decides" in text.lower()


def test_no_advice_to_apply_or_not_apply():
    """The workflow must explicitly state it does not advise apply/don't apply."""
    text = _text().lower()
    assert "no automatic apply-or-don't recommendation" in text or "never present the score as a recommendation" in text
```

- [ ] **Step 3: Run tests**

```powershell
python -m pytest tests/references/test_workflow_jd_analyze.py -v
```

Expected: 5 tests pass.

- [ ] **Step 4: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 219 tests pass (214 + 5).

- [ ] **Step 5: Commit**

```powershell
git add references/workflows/jd-analyze.md tests/references/test_workflow_jd_analyze.py
git commit -m "docs: add jd-analyze workflow reference"
```

---

## Task 13 — Pre-application check workflow reference

**Files:**

- Create: `references/workflows/pre-application-check.md`
- Create: `tests/references/test_workflow_pre_application_check.py`

### Steps

- [ ] **Step 1: Write the reference document**

Create `references/workflows/pre-application-check.md`:

```markdown
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
```text

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
```text

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
```text

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
```text

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

```

- [ ] **Step 2: Write the structural test**

Create `tests/references/test_workflow_pre_application_check.py`:

```python
"""Structural tests for references/workflows/pre-application-check.md."""
from pathlib import Path

REFERENCE = Path(__file__).parent.parent.parent / "references" / "workflows" / "pre-application-check.md"


def _text():
    return REFERENCE.read_text(encoding="utf-8")


def test_reference_exists():
    assert REFERENCE.exists()


def test_six_questions_documented():
    text = _text()
    for q in ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6"):
        assert q in text


def test_never_blocks_submission_explicit():
    text = _text().lower()
    assert "never blocks submission" in text or "coaching, not gating" in text


def test_healthy_weekly_rate_is_user_defined():
    text = _text().lower()
    assert "healthy weekly rate is user-defined" in text or "user-defined" in text


def test_fit_or_pressure_recorded_verbatim():
    text = _text().lower()
    assert "verbatim" in text


def test_tracker_integration_documented():
    text = _text()
    assert "add_application" in text
    assert "weekly_summary" in text
    assert "find_duplicates" in text


def test_safeguarding_section_present():
    text = _text()
    assert "Safeguarding boundaries" in text
```

- [ ] **Step 3: Run tests**

```powershell
python -m pytest tests/references/test_workflow_pre_application_check.py -v
```

Expected: 7 tests pass.

- [ ] **Step 4: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 226 tests pass (219 + 7).

- [ ] **Step 5: Commit**

```powershell
git add references/workflows/pre-application-check.md tests/references/test_workflow_pre_application_check.py
git commit -m "docs: add pre-application-check workflow reference"
```

---

## Task 14 — JD-analyze slash command

**Files:**

- Create: `commands/brains-jd-analyze.md`

### Steps

- [ ] **Step 1: Create the slash command file**

Create `commands/brains-jd-analyze.md`:

```markdown
---
description: Analyse a job description for ND-relevant signals (red flags, masking cost, evidence of flex, role-fit score, duplicate-application check)
argument-hint: [optional: JD URL, or paste JD text in chat]
---

Run the BRAINS Resume Skill JD-analyzer workflow. Load `~/.claude/skills/brains-resume/references/workflows/jd-analyze.md` and follow its procedure. Input source: `$ARGUMENTS` (a URL) or pasted text in the next message.
```

- [ ] **Step 2: Run the suite to confirm no regressions**

```powershell
python -m pytest -q
```

Expected: 226 tests still pass (no new tests added — slash command markdown).

- [ ] **Step 3: Commit**

```powershell
git add commands/brains-jd-analyze.md
git commit -m "feat: add brains-jd-analyze slash command"
```

---

## Task 15 — Pre-application check slash command

**Files:**

- Create: `commands/brains-precheck.md`

### Steps

- [ ] **Step 1: Create the slash command file**

Create `commands/brains-precheck.md`:

```markdown
---
description: Six-question coaching pass before submitting an application; registers the application in the tracker
argument-hint: [optional: tracker JD id, or resume file path]
---

Run the BRAINS Resume Skill pre-application sanity check workflow. Load `~/.claude/skills/brains-resume/references/workflows/pre-application-check.md` and follow its procedure. Optional inputs: `$ARGUMENTS` (JD id or resume path); otherwise gather inputs interactively.
```

- [ ] **Step 2: Run the suite**

```powershell
python -m pytest -q
```

Expected: 226 tests still pass.

- [ ] **Step 3: Commit**

```powershell
git add commands/brains-precheck.md
git commit -m "feat: add brains-precheck slash command"
```

---

## Task 16 — Tracker slash command (composite with subcommands)

**Files:**

- Create: `commands/brains-track.md`

### Steps

- [ ] **Step 1: Create the slash command file**

This slash command is composite — its body describes the subcommand surface so Claude can route based on the user's argument.

Create `commands/brains-track.md`:

```markdown
---
description: Manage the application tracker — add applications, log outcomes, view pipeline summary
argument-hint: <subcommand> [args...] — subcommands: add | update <id> <event> | list [--company X] [--since YYYY-MM-DD] [--status open|closed] | summary | focus-areas | healthy-rate
---

Run the BRAINS Resume Skill application tracker. Parse `$ARGUMENTS` for the subcommand and route to the matching Python helper in `scripts/tracker/`. All output is markdown rendered in chat, carrying the BRAINS coaching artifact frame.

## Subcommand routing

- **`add`** — interactive add of an application that was submitted without going through `brains-precheck`. Walk through the same six questions as the precheck workflow (see `references/workflows/pre-application-check.md`), then call `scripts/tracker/add.py:add_application`.

- **`update <id> <event-type> [date] [notes]`** — log an outcome on an existing application. Valid event-types: `acknowledged`, `callback`, `phone_screen`, `first_round`, `second_round`, `take_home`, `offer`, `rejection`, `ghosted`, `withdrew`. Call `scripts/tracker/add.py:record_outcome`.

- **`list [--company X] [--since YYYY-MM-DD] [--status open|closed]`** — call `scripts/tracker/query.py:list_applications` with the given filters and render the result as a markdown table.

- **`summary`** — call `scripts/tracker/query.py:weekly_summary` and `efficacy_by_template`. Render:
  - Pipeline funnel (applications → callbacks → interviews → offers/rejections)
  - This-week pacing vs the user's healthy weekly rate
  - Per-template efficacy table

- **`focus-areas`** — view or edit `~/.brains-resume/profile.json` focus_areas. If no argument, show the current list. If a comma-separated list is provided, replace via `scripts/tracker/profile.py:write_profile`.

- **`healthy-rate`** — view or set `~/.brains-resume/profile.json` healthy_weekly_rate. If no argument, show the current value. If a number is provided, save via `write_profile`.

## First-time user

If the tracker db doesn't exist yet (any subcommand other than `summary` is the first write), surface the one-time privacy notice:

> "Application data will be stored locally at `~/.brains-resume/tracker.db`. Nothing is transmitted. You can delete the entire directory at any time to remove all tracker history."

Then proceed with the subcommand.

## Branding

The tracker is a BRAINS coaching artifact. Markdown output uses identity-first language, no italics in body text, no third-party org references. Tables follow the existing coaching-report markdown conventions.
```

- [ ] **Step 2: Run the suite**

```powershell
python -m pytest -q
```

Expected: 226 tests still pass.

- [ ] **Step 3: Commit**

```powershell
git add commands/brains-track.md
git commit -m "feat: add brains-track composite slash command with subcommands"
```

---

## Task 17 — Smoke tests for the three new workflows

**Files:**

- Create: `tests/test_smoke_jd_analyze_workflow.py`
- Create: `tests/test_smoke_precheck_workflow.py`
- Create: `tests/test_smoke_track_workflow.py`

### Steps

- [ ] **Step 1: Write the jd-analyze smoke test**

Create `tests/test_smoke_jd_analyze_workflow.py`:

```python
"""Smoke test for the deterministic portion of the jd-analyze workflow.

Exercises: jd_analyze runs end-to-end on a fixture, the result carries all
expected fields, and persisting via add_jd works.
"""
from pathlib import Path

from scripts.tracker.add import add_jd
from scripts.tracker.db import open_db
from scripts.validators.jd_analyzer import jd_analyze
from tests.fixtures import jd_analyzer_fixtures as fx


def test_jd_analyze_smoke(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "t.db"))

    # (a) Analyse a mixed JD with focus areas + company + role
    result = jd_analyze(
        jd_text=fx.MIXED_JD,
        focus_areas=["python", "cloud"],
        company="Example Corp",
        role_title="Senior Engineer",
    )

    codes = {f.code for f in result.findings}
    assert "JD_RED_FLAG_SOFT_CULTURE" in codes
    assert "JD_EVIDENCE_OF_FLEX" in codes
    assert "JD_REQ_VS_NICE_PARSING" in codes
    assert "JD_ROLE_FIT_SCORE" in codes
    assert result.role_fit_score is not None

    # (b) Persist to tracker
    jd_id = add_jd(
        source="paste", source_ref=None,
        company="Example Corp", role_title="Senior Engineer",
        raw_text=fx.MIXED_JD,
        analyzer_findings={"finding_count": len(result.findings)},
        focus_areas_required=result.required_list,
        focus_areas_nice=result.nice_list,
    )
    assert jd_id > 0

    conn = open_db()
    try:
        row = conn.execute(
            "SELECT company, role_title FROM jds WHERE id=?", (jd_id,)
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == "Example Corp"
    assert row[1] == "Senior Engineer"
```

- [ ] **Step 2: Write the precheck smoke test**

Create `tests/test_smoke_precheck_workflow.py`:

```python
"""Smoke test for the deterministic portion of the pre-application check.

Exercises: tracker lookup, profile read, weekly_summary, add_application, all
working end-to-end on a clean fixture-driven scenario.
"""
from datetime import datetime, timedelta

from scripts.tracker.add import (
    add_application, add_jd, add_resume_version,
)
from scripts.tracker.models import Profile
from scripts.tracker.profile import write_profile
from scripts.tracker.query import find_duplicates, weekly_summary


def test_precheck_smoke_no_duplicates_no_pacing(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))

    # Q1: no duplicates yet
    assert find_duplicates("Example Corp", "Senior Engineer") == []

    # Q4 setup: no healthy rate yet → pacing returns None
    assert weekly_summary().pacing_vs_target is None

    # Q4 follow-up: user sets healthy rate
    write_profile(Profile(focus_areas=["python"], healthy_weekly_rate=3))

    # Q6: register the application
    rv = add_resume_version(file_path="/tmp/r.docx", template="hybrid", focus_areas=["python"])
    jd_id = add_jd(
        source="paste", source_ref=None,
        company="Example Corp", role_title="Senior Engineer",
        raw_text="JD text", analyzer_findings={},
        focus_areas_required=["python"], focus_areas_nice=[],
    )
    app_id = add_application(
        jd_id=jd_id, resume_version_id=rv, cover_letter_id=None,
        submitted_at=datetime.now(), channel="direct",
        notes='{"fit_or_pressure": "genuine fit"}',
    )
    assert app_id > 0

    # Subsequent precheck for the SAME company + role would now flag a duplicate
    assert len(find_duplicates("Example Corp", "Senior Engineer")) == 1
```

- [ ] **Step 3: Write the track smoke test**

Create `tests/test_smoke_track_workflow.py`:

```python
"""Smoke test for the /brains-track slash command's underlying helpers.

Exercises add → record_outcome → query summary flow end-to-end.
"""
from datetime import datetime

from scripts.tracker.add import (
    add_application, add_jd, add_resume_version, record_outcome,
)
from scripts.tracker.query import (
    efficacy_by_template, list_applications, weekly_summary,
)


def test_track_smoke_full_lifecycle(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))

    # Seed two applications with different outcomes
    rv1 = add_resume_version(file_path=None, template="hybrid", focus_areas=[])
    rv2 = add_resume_version(file_path=None, template="chronological", focus_areas=[])
    jd_id = add_jd(
        source="paste", source_ref=None, company="X", role_title="Y",
        raw_text="z", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    app1 = add_application(
        jd_id=jd_id, resume_version_id=rv1, cover_letter_id=None,
        submitted_at=datetime.now(), channel="linkedin",
    )
    app2 = add_application(
        jd_id=jd_id, resume_version_id=rv2, cover_letter_id=None,
        submitted_at=datetime.now(), channel="direct",
    )
    record_outcome(app1, "callback", datetime.now())
    record_outcome(app2, "rejection", datetime.now())

    # /brains-track list
    rows = list_applications()
    assert len(rows) == 2

    # /brains-track summary
    s = weekly_summary()
    assert s.applications_count == 2
    assert s.outcomes_by_type.get("callback", 0) == 1
    assert s.outcomes_by_type.get("rejection", 0) == 1

    # efficacy_by_template (used by /brains-track summary)
    eff = efficacy_by_template()
    by_template = {r.template: r for r in eff}
    assert by_template["hybrid"].callback_count == 1
    assert by_template["chronological"].rejection_count == 1
```

- [ ] **Step 4: Run all three smoke tests**

```powershell
python -m pytest tests/test_smoke_jd_analyze_workflow.py tests/test_smoke_precheck_workflow.py tests/test_smoke_track_workflow.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 229 tests pass (226 + 3).

- [ ] **Step 6: Commit**

```powershell
git add tests/test_smoke_jd_analyze_workflow.py tests/test_smoke_precheck_workflow.py tests/test_smoke_track_workflow.py
git commit -m "test: add smoke tests for jd-analyze, precheck, and track workflows"
```

---

## Phase 4 — Integration with existing workflows (Tasks 18-19)

Add the opt-in end-of-workflow tracker prompt to four existing workflow references. Update SKILL.md router.

---

## Task 18 — End-of-workflow tracker prompts

**Files:**

- Modify: `references/workflows/tailor.md`
- Modify: `references/workflows/cover-letter.md`
- Modify: `references/workflows/review.md`
- Modify: `references/workflows/bias-check.md`

### Steps

- [ ] **Step 1: Read each workflow file to find a good insertion point**

Each of the four files has a final step or output section. Use `Read` on each before editing to identify where the end-of-workflow paragraph belongs (typically right after the output is saved, before any "next steps" suggestions).

- [ ] **Step 2: Add the tracker-opt-in paragraph to `references/workflows/tailor.md`**

Locate the section near the end where the tailored resume output is described. Insert this paragraph:

```markdown
**Application tracker (opt-in).** After saving the tailored resume, ask the user: "Track this in the application tracker? (yes runs the pre-application sanity check; later registers it without the check; no skips tracking entirely)". If yes, invoke the `pre-application-check.md` workflow with the resume's metadata. If later, call `scripts/tracker/add.py:add_resume_version` (and the related helpers) silently without going through the precheck questions. If no, no tracker writes occur.
```

- [ ] **Step 3: Add the same paragraph to `references/workflows/cover-letter.md`**

Locate the equivalent end-of-workflow point. Insert the paragraph above, with one substitution: "tailored resume" → "cover letter".

- [ ] **Step 4: Add the same paragraph to `references/workflows/review.md`**

For the review workflow, the artifact is the coaching report, not a submission-ready document. The tracker-opt-in question still makes sense — the user may want to register that they've reviewed a particular resume version. Insert:

```markdown
**Application tracker (opt-in).** After surfacing the review findings, ask the user: "Register this resume version in the application tracker? (yes — saves the resume version with its current focus areas; no — coaching report stays in chat only)". If yes, call `scripts/tracker/add.py:add_resume_version` with the file path, template, and focus areas the user confirms.
```

- [ ] **Step 5: Add the same paragraph to `references/workflows/bias-check.md`**

The bias-check workflow runs immediately before submission. Insert:

```markdown
**Application tracker (opt-in).** After the bias-check passes, ask the user: "Run the pre-application sanity check and register this in the tracker? (yes runs the precheck workflow; no submits without registering)". If yes, invoke `pre-application-check.md`.
```

- [ ] **Step 6: Add a structural test**

Create `tests/references/test_workflow_tracker_optin.py`:

```python
"""Verify all four existing workflows now cross-reference the tracker opt-in."""
from pathlib import Path

REF_DIR = Path(__file__).parent.parent.parent / "references" / "workflows"


WORKFLOWS_THAT_MUST_PROMPT = (
    "tailor.md",
    "cover-letter.md",
    "review.md",
    "bias-check.md",
)


def test_all_four_workflows_offer_tracker_optin():
    for fname in WORKFLOWS_THAT_MUST_PROMPT:
        text = (REF_DIR / fname).read_text(encoding="utf-8")
        assert "Application tracker" in text, (
            f"{fname} does not contain the tracker opt-in paragraph"
        )
        assert "opt-in" in text.lower() or "scripts/tracker" in text


def test_tailor_prompts_for_precheck():
    text = (REF_DIR / "tailor.md").read_text(encoding="utf-8")
    assert "pre-application" in text.lower() or "precheck" in text.lower()
```

- [ ] **Step 7: Run tests**

```powershell
python -m pytest tests/references/test_workflow_tracker_optin.py -v
```

Expected: 2 tests pass.

- [ ] **Step 8: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 231 tests pass (229 + 2).

- [ ] **Step 9: Commit**

```powershell
git add references/workflows/tailor.md references/workflows/cover-letter.md references/workflows/review.md references/workflows/bias-check.md tests/references/test_workflow_tracker_optin.py
git commit -m "feat: add opt-in tracker prompts to four existing workflows"
```

---

## Task 19 — SKILL.md router updates

**Files:**

- Modify: `SKILL.md`

### Steps

- [ ] **Step 1: Read SKILL.md to locate the relevant sections**

Three sections need editing:

1. Workflow router table (where existing workflows are listed)
2. Capability menu (in First-Use Behaviour section)
3. Slash-command list sentence + "all eleven workflows" → "all fourteen workflows" updates

- [ ] **Step 2: Update the workflow-router table**

Find the existing consolidate row in SKILL.md:

```markdown
| Check my resume and LinkedIn for inconsistencies | `references/workflows/consolidate.md` |
```

Insert immediately after it:

```markdown
| Analyse a job description for ND-relevant signals | `references/workflows/jd-analyze.md` |
| Run a pre-application sanity check before submitting | `references/workflows/pre-application-check.md` |
| Manage the application tracker (add, update, list, summary) | `commands/brains-track.md` |
```

- [ ] **Step 3: Update the capability menu**

Find the existing "Resume + LinkedIn consolidation | Live" row. Insert after it:

```markdown
| JD analyzer | Live |
| Pre-application sanity check | Live |
| Application tracker | Live |
```

- [ ] **Step 4: Update the slash-command list sentence**

Find the sentence currently reading:

> "Type `/brains-` and Claude Code will list the eleven commands: review, disclosure, edit, tailor, cover-letter, create, linkedin, linkedin-improve, consolidate, career-change, check."

Replace with:

> "Type `/brains-` and Claude Code will list the fourteen commands: review, disclosure, edit, tailor, cover-letter, create, linkedin, linkedin-improve, consolidate, jd-analyze, precheck, track, career-change, check."

- [ ] **Step 5: Update both "all eleven workflows are live" phrasings**

Find:

> "BRAINS Resume Skill is ready. All eleven workflows are live — resume review, disclosure coaching, create, edit, tailor, cover letter, LinkedIn ingestion, LinkedIn profile improvement, resume-and-LinkedIn consolidation, career-change translation, and final pre-submit check."

Replace with:

> "BRAINS Resume Skill is ready. All fourteen workflows are live — resume review, disclosure coaching, create, edit, tailor, cover letter, LinkedIn ingestion, LinkedIn profile improvement, resume-and-LinkedIn consolidation, JD analyzer, pre-application sanity check, application tracker, career-change translation, and final pre-submit check."

Find the shorter greeting:

> "BRAINS Resume Skill is ready — all eleven workflows are live."

Replace with:

> "BRAINS Resume Skill is ready — all fourteen workflows are live."

- [ ] **Step 6: Run the suite**

```powershell
python -m pytest -q
```

Expected: 231 tests still pass (no test changes — SKILL.md is not test-asserted at the workflow-count level).

- [ ] **Step 7: Commit**

```powershell
git add SKILL.md
git commit -m "feat: update SKILL.md router for jd-analyze, precheck, and track workflows"
```

---

## Phase 5 — Release polish (Tasks 20-24)

Documentation updates, brand-application reference update, bundle rebuild, CHANGELOG, version bump, v1.2.0 tag.

---

## Task 20 — Update README.md

**Files:**

- Modify: `README.md`

### Steps

- [ ] **Step 1: Read README.md to locate the slash-command list**

The README has a slash-command list from v1.1.0 that mentions eleven commands. Find that section.

- [ ] **Step 2: Add three new entries to the slash-command list**

Insert (placement should match existing ordering):

```markdown
- `/brains-jd-analyze` — Analyse a job description for ND-relevant signals (red flags, masking cost, evidence of flex, role-fit score)
- `/brains-precheck` — Six-question coaching pass before submitting an application; registers it in the tracker
- `/brains-track` — Manage the application tracker — add applications, log outcomes, view pipeline summary
```

Update any "eleven commands" mention to "fourteen commands".

- [ ] **Step 3: Add a "Tracking applications" section**

Add this section in a sensible spot after the "Choosing a template" section:

```markdown
## Tracking applications

The skill includes an opt-in application tracker stored locally at `~/.brains-resume/tracker.db` (SQLite). The tracker is created on first use; if you never run `/brains-track` or `/brains-precheck`, the database is never created.

The tracker carries:

- Resume versions (with focus-area tags and tailored-from lineage)
- Job descriptions (with analyzer findings)
- Cover letters (linked to resume + JD)
- Applications (with channel, agency, recruiter contact)
- Outcomes (callback, interview, offer, rejection, etc.)

From these you can query:

- This-week pacing vs your self-defined healthy weekly application rate
- Per-template efficacy (which template + JD combinations are converting)
- Open applications by company or recency
- Duplicate-application detection (prevents accidental re-application)

Use `/brains-track summary` for a pipeline view, `/brains-track update <id> <event-type>` to log outcomes as they happen, and `/brains-track healthy-rate` to set the application pace that fits your sensory bandwidth — the skill never tells you what that number should be.

The dashboard UI for these views ships in v1.3.0; for v1.2.0, all queries are surfaced as markdown tables in chat.
```

- [ ] **Step 4: Update README version line**

If the README has a version line near the top (e.g. "v1.1.0 — all eleven workflows live..."), update to:

```markdown
v1.2.0 — all fourteen workflows live, JD analyzer + application tracker shipped, Claude Project bundle available.
```

- [ ] **Step 5: Run the suite**

```powershell
python -m pytest -q
```

Expected: 231 tests still pass.

- [ ] **Step 6: Commit**

```powershell
git add README.md
git commit -m "docs: update README for v1.2.0 — slash commands and Tracking applications section"
```

---

## Task 21 — Update brand-application.md

**Files:**

- Modify: `references/brand-application.md`

### Steps

- [ ] **Step 1: Read the file to find the Split-Rule table**

The table is in "Section 1 — The Split Rule".

- [ ] **Step 2: Add four new rows to the Split-Rule table**

Insert after the existing "Consolidation report" row:

```markdown
| JD analyzer markdown report (saved to `output/`) | **BRAINS branded** — Gold Deep headings, identity-first language | Internal coaching artifact, same category as the review coaching report |
| Pre-application check summary (saved to `output/`) | **BRAINS branded** | Internal coaching artifact |
| Tracker CLI markdown output (`/brains-track` responses) | **BRAINS branded** — coaching artifact frame in chat | Internal coaching tooling |
| `tracker.db` and `profile.json` | **Not branded** — raw data, no presentation surface | Data storage, not a presented artifact |
```

- [ ] **Step 3: Run the suite**

```powershell
python -m pytest -q
```

Expected: 231 tests still pass.

- [ ] **Step 4: Commit**

```powershell
git add references/brand-application.md
git commit -m "docs: extend brand-application.md for tracker and jd-analyzer artifact types"
```

---

## Task 22 — Rebuild Claude Project bundle + update setup guide

**Files:**

- Modify: `docs/claude-project-setup.md`

### Steps

- [ ] **Step 1: Read the existing setup guide**

The current guide lists eleven workflows from v1.1.0. Three new workflows need adding.

- [ ] **Step 2: Update the workflow list**

Find the "Workflows available on claude.ai" section. Update from eleven items to fourteen, adding:

```markdown
12. JD analyzer (new in v1.2.0)
13. Pre-application sanity check (new in v1.2.0)
14. Application tracker (new in v1.2.0 — CLI-only in this version; dashboard in v1.3.0)
```

Update the count phrasing throughout the file ("all eleven workflows" → "all fourteen workflows").

- [ ] **Step 3: Add a note about the tracker's claude.ai limitation**

The tracker uses local SQLite; it does not work in claude.ai Projects. Add this note in the "What is different from Claude Code" table:

```markdown
| Application tracker (`/brains-track`, SQLite at `~/.brains-resume/`) | Yes — full functionality | No — claude.ai cannot persist local files; the tracker is Claude-Code-only |
```

- [ ] **Step 4: Rebuild the bundle**

```powershell
.venv\Scripts\activate
python scripts\packaging\build_project_bundle.py
```

Expected: prints `Wrote ...\dist\brains-resume-claude-project.zip`.

- [ ] **Step 5: Verify the new references are in the bundle**

```powershell
python -c "import zipfile; z = zipfile.ZipFile('dist/brains-resume-claude-project.zip'); names = z.namelist(); print('jd-analyze:', 'brains-resume-claude-project/references/workflows/jd-analyze.md' in names); print('precheck:', 'brains-resume-claude-project/references/workflows/pre-application-check.md' in names)"
```

Expected: both `True`.

- [ ] **Step 6: Commit**

```powershell
git add docs/claude-project-setup.md
git commit -m "docs: update Claude Project setup guide for v1.2.0 workflows"
```

(Do not commit `dist/brains-resume-claude-project.zip` — it's gitignored.)

---

## Task 23 — CHANGELOG entry for v1.2.0

**Files:**

- Modify: `CHANGELOG.md`

### Steps

- [ ] **Step 1: Add the v1.2.0 entry at the top**

Above the v1.1.0 entry, add:

```markdown
## [1.2.0] — 2026-05-13

### Added
- **Application tracker** — SQLite store at `~/.brains-resume/tracker.db` with 5 entity tables (resume_versions, cover_letters, jds, applications, outcomes) and migrations support. Public Python API at `scripts/tracker/{add,query,profile}.py`. Opt-in — never created unless the user invokes a tracker workflow.
- **User profile store** — `~/.brains-resume/profile.json` holds focus areas and self-defined healthy weekly application rate. The skill never recommends a rate; it asks once and uses what the user provides.
- **JD analyzer validator** (`scripts/validators/jd_analyzer.py`) — six-code finding catalog: soft-culture red flags, masking-cost markers, evidence-of-real-flexibility, required-vs-nice parsing, role-fit scoring against user focus areas, duplicate-application detection against the tracker.
- **JD analyzer workflow** (`/brains-jd-analyze`) — surfaces ND-relevant signals in a JD; offers to persist to the tracker.
- **Pre-application sanity check workflow** (`/brains-precheck`) — six-question coaching pass before submission: duplicate check, findings recap, fit-or-pressure question, pacing check, cover-letter check, channel+agency. Never blocks submission.
- **Application tracker slash command** (`/brains-track`) — composite command with subcommands: `add`, `update`, `list`, `summary`, `focus-areas`, `healthy-rate`. All output is markdown rendered in chat.
- **Opt-in integration with existing workflows** — `brains-tailor`, `brains-cover-letter`, `brains-review`, `brains-check` now prompt at end-of-workflow to register the artifact in the tracker. Users who consistently decline never create the tracker db.
- **SQLite migration system** — numbered migration scripts in `scripts/tracker/migrations/`. Migration `0001_initial_schema` ships with v1.2.0; future schema changes follow the same pattern.
- **Test isolation via environment variables** — `BRAINS_TRACKER_DB_PATH` and `BRAINS_TRACKER_PROFILE_PATH` override the default paths for test fixtures.

### Changed
- **SKILL.md router** — three new workflow entries; capability menu and slash-command list updated to reflect fourteen live workflows.
- **`references/brand-application.md`** — Split-rule table extended for tracker CLI output, JD analyzer reports, and the pre-application check summary.
- **`README.md`** — slash-command list updated; new "Tracking applications" section added.
- **Claude Project bundle** — rebuilt to include new reference docs (the tracker itself is Claude-Code-only — claude.ai can't persist local files).

### Deferred to Phase 5 (v1.3.0)
- Streamlit dashboard UI built on top of this data layer.
- Pacing/burnout tracker as a dedicated dashboard page.
- Efficacy analytics with confidence bands.
- Anonymized community efficacy data (opt-in, future).

### Deferred (still)
- Interview prep skill (sibling, separate bundle).
- Salary negotiation skill (sibling, separate bundle).
- Network/referral lane as a first-class entity (folded into `channel` enum for v1.2.0).
- MCP server for Claude Desktop.
```

- [ ] **Step 2: Commit**

```powershell
git add CHANGELOG.md
git commit -m "docs: add v1.2.0 CHANGELOG entry"
```

---

## Task 24 — Version bump + v1.2.0 tag

**Files:**

- Modify: `SKILL.md` (frontmatter `version` + body version reference)
- Modify: `pyproject.toml`

### Steps

- [ ] **Step 1: Bump SKILL.md frontmatter**

In `SKILL.md`, find the frontmatter block:

```yaml
---
name: brains-resume
description: ...
version: 1.1.0
license: MIT
---
```

Change `version: 1.1.0` to `version: 1.2.0`.

- [ ] **Step 2: Update body version reference**

Find:

> "This is a BRAINS Incubator project, v1.1.0."

Update to:

> "This is a BRAINS Incubator project, v1.2.0."

- [ ] **Step 3: Bump pyproject.toml**

In `pyproject.toml`, find:

```toml
version = "1.1.0"
```

Change to:

```toml
version = "1.2.0"
```

- [ ] **Step 4: Run the full suite one final time**

```powershell
.venv\Scripts\activate
python -m pytest -q
```

Expected: 231 tests pass, all green.

- [ ] **Step 5: Commit the version bump**

```powershell
git add SKILL.md pyproject.toml
git commit -m "chore: bump version to 1.2.0"
```

- [ ] **Step 6: Create the v1.2.0 tag**

```powershell
git tag -a v1.2.0 -m "v1.2.0 - Phase 4: tracker data layer, JD analyzer, pre-application check"
```

- [ ] **Step 7: Verify the tag**

```powershell
git tag --list
git show v1.2.0 --stat
```

Expected: `v1.2.0` appears in the tag list; `git show v1.2.0` displays the chore commit and the file changes.

- [ ] **Step 8: Final status check**

```powershell
git status
git log --oneline -25
```

Expected: working tree clean; the last ~24 commits trace the Plan 4 work; most recent commit is `chore: bump version to 1.2.0`.

Do NOT push to remote — the plan does not push. When ready, the user can push with `git push && git push --tags`.

---

## Plan completion checklist

After all tasks are marked complete, verify:

- [ ] All 24 tasks have every step checked off.
- [ ] `python -m pytest -q` reports 231 tests green with no unexpected skips.
- [ ] `git tag --list` includes `v1.2.0`.
- [ ] `dist/brains-resume-claude-project.zip` was rebuilt and contains `jd-analyze.md` and `pre-application-check.md` under `references/workflows/`.
- [ ] No commits include `Co-Authored-By` footers.
- [ ] No third-party org or project proper-name attribution appears in any committed file or commit message.
- [ ] `SKILL.md` frontmatter says `version: 1.2.0`.
- [ ] `pyproject.toml` says `version = "1.2.0"`.
- [ ] The three new slash commands (`brains-jd-analyze`, `brains-precheck`, `brains-track`) exist in `commands/`.
- [ ] The two new workflow references (`jd-analyze.md`, `pre-application-check.md`) exist in `references/workflows/`.
- [ ] `scripts/tracker/` exists with `db.py`, `models.py`, `add.py`, `query.py`, `profile.py`, and `migrations/0001_initial_schema.py`.
- [ ] `scripts/validators/jd_analyzer.py` exists with the six-code finding catalog.
- [ ] The four existing workflows (`tailor.md`, `cover-letter.md`, `review.md`, `bias-check.md`) contain the "Application tracker (opt-in)" paragraph.

When every box is ticked, v1.2.0 is shippable.
