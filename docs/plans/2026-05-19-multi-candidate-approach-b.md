# Multi-Candidate Support — Approach B (`candidates` table) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** Approach C must be merged first — this plan backfills `candidate_id` from the `for_candidate` text column that Approach C introduced. See `docs/plans/2026-05-19-multi-candidate-approach-c.md`.

**Goal:** Replace the single-profile model with a first-class `candidates` table so the skill can hold and switch between multiple full candidate profiles (each with their own name, focus areas, healthy weekly rate, and pacing notes), and so the dashboard can show per-candidate views.

**Architecture:** New `candidates` table; new `candidate_id INTEGER` FK column on `jds`, `resume_versions`, `cover_letters`. `profile.json` shrinks to `{active_candidate_id, log_handoffs}` — the existing per-user fields (`first_name`, `last_name`, `focus_areas`, `healthy_weekly_rate`, `pacing_notes`) migrate into the first `candidates` row. The dashboard sidebar grows a candidate picker; workflow cards drop the `for_candidate` text input in favour of the active candidate. A post-migration hook in `db.py` performs idempotent backfill the first time a 0004-or-later schema opens against a pre-B profile.json.

**Tech Stack:** Python 3.14, SQLite (forward-only migrations + idempotent post-migration backfill), python-docx, reportlab, pytest, Streamlit.

**Out of scope:**
- Removing the Approach C `for_candidate` columns. We keep them as a denormalized cache — cheap, useful for data export, and a tombstone of "what name was on the DOCX when this row was written". Approach C's column becomes a write-only side-channel after this plan lands; reads go through `candidate_id`.
- Multi-installation sync. Each install still has its own SQLite DB.
- Per-candidate output directories. `BRAINS_OUTPUTS_DIR` stays installation-wide; per-candidate scoping happens via JD folders, which are unique anyway.

**Pre-flight:**
- Approach C is merged to `main` and the `for_candidate` column is populated on at least one row in the user's local tracker (so the backfill path can be exercised on real data).
- Run the full suite once: all green on `main`.
- Back up `~/.brains-resume/tracker.db` and `~/.brains-resume/profile.json` before starting. The backfill is idempotent but the migration itself is forward-only.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `scripts/tracker/migrations/0004_candidates_table.py` | **create** | Create `candidates` table; add nullable `candidate_id INTEGER` FK to `jds`, `resume_versions`, `cover_letters`; add index on each |
| `scripts/tracker/db.py` | modify | After running migrations, call a new idempotent `_run_post_migration_hooks()` that triggers the B-backfill once |
| `scripts/tracker/_post_migration.py` | **create** | The idempotent backfill: read legacy `profile.json`, create the seed candidate row, link all artifacts to it (or to a new candidate by name from `for_candidate`), rewrite `profile.json` to the trimmed shape |
| `scripts/tracker/models.py` | modify | Add `Candidate` dataclass; trim `Profile` to `{active_candidate_id, log_handoffs}`; add `candidate_id: Optional[int] = None` to `ResumeVersion`, `CoverLetter`, `JD` |
| `scripts/tracker/candidates.py` | **create** | CRUD for the new table: `list_candidates`, `get_candidate(id)`, `create_candidate(...)`, `update_candidate(id, ...)`, `archive_candidate(id)`, `get_active_candidate()`, `set_active_candidate(id)` |
| `scripts/tracker/profile.py` | modify | `Profile` now holds `active_candidate_id` + `log_handoffs`; the legacy fields are removed from the dataclass but the *file* read supports both shapes for one release (backfill drops the legacy fields after migration) |
| `scripts/tracker/add.py` | modify | Every insert takes `candidate_id: Optional[int] = None` (defaults to active); for_candidate kept as a deprecated alias that resolves to candidate_id |
| `scripts/tracker/query.py` | modify | Every list/read filters by candidate (default = active); add `candidate_id=` filter arg; rewrite `list_artifacts_for_candidate(name)` to JOIN on `candidates.first_name`/`.last_name` |
| `scripts/outputs/io.py` | modify | `make_artifact_path` takes optional `candidate_id` (default = active); for_candidate accepted as alias resolved via lookup; filename + ArtifactMeta both stamped |
| `scripts/outputs/tagging.py` | modify | `ArtifactMeta` gains `candidate_id: int \| None`; persist as `BrainsCandidateId` (vt:i4); reader unchanged for `for_candidate` (back-compat with v1.6 DOCX) |
| `scripts/dashboard/sidebar.py` | modify | Replace the "first/last name" text inputs with a candidate picker (select existing candidate, switch active, "+ New" form, edit-fields form) |
| `scripts/dashboard/workflows/create.py` | modify | Drop the "For candidate" text input — use the active candidate by default; add a "Switch candidate" link that scrolls to the sidebar |
| `scripts/dashboard/workflows/edit.py` | modify | Same as create.py |
| `scripts/dashboard/workflows/tailor.py` | modify | Same as create.py |
| `scripts/dashboard/workflows/cover_letter.py` | modify | Same as create.py |
| `scripts/dashboard/tabs/overview.py` | modify | Read counts per active candidate, not globally |
| `scripts/dashboard/tabs/pacing.py` | modify | Use active candidate's `healthy_weekly_rate`, not profile.healthy_weekly_rate |
| `scripts/dashboard/tabs/applications.py` | modify | Scope listing by active candidate |
| `scripts/dashboard/tabs/resumes.py` | modify | Scope listing by active candidate |
| `scripts/dashboard/tabs/cover_letters.py` | modify | Scope listing by active candidate |
| `scripts/dashboard/tabs/jds.py` | modify | Scope listing by active candidate |
| `scripts/validators/jd_analyzer.py` | modify | Role-fit scoring uses active candidate's `focus_areas`, not profile.focus_areas |
| `references/workflows/create.md` | modify | Replace "For candidate" instruction with "Confirm the active candidate" instruction |
| `references/workflows/edit.md` | modify | Same |
| `references/workflows/tailor.md` | modify | Same |
| `references/workflows/cover-letter.md` | modify | Same |
| `tests/tracker/migrations/test_0004_candidates_table.py` | **create** | Schema-level migration tests |
| `tests/tracker/test_post_migration.py` | **create** | Backfill correctness: profile-holder + for_candidate populated + idempotency |
| `tests/tracker/test_candidates.py` | **create** | CRUD module unit tests |
| `tests/tracker/test_profile.py` | modify | Trimmed `Profile`; backwards-compat read of legacy shape |
| `tests/tracker/test_add.py` | modify | candidate_id default = active; explicit override works |
| `tests/tracker/test_query.py` | modify | Queries scope to active candidate |
| `tests/outputs/test_io.py` | modify | `make_artifact_path` uses active candidate for filename when no override |
| `tests/outputs/test_tagging.py` | modify | `BrainsCandidateId` round-trip; back-compat reading of pre-B DOCX |
| `tests/dashboard/test_app_import.py` | modify | Sidebar candidate picker imports cleanly |
| `tests/dashboard/test_app_overview_render.py` | modify | Overview tab scopes by active candidate |
| `tests/test_smoke_two_candidate_session.py` | **create** | End-to-end: create two candidates, switch active, render resumes for each, verify linkage |

---

## Task 1: Migration 0004 schema

**Files:**
- Create: `scripts/tracker/migrations/0004_candidates_table.py`
- Test: `tests/tracker/migrations/test_0004_candidates_table.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/tracker/migrations/test_0004_candidates_table.py
"""Tests for migration 0004 — candidates table + candidate_id columns."""
import pytest

from scripts.tracker.db import open_db


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_candidates_table_exists(isolated_db):
    conn = open_db()
    try:
        names = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "candidates" in names
    finally:
        conn.close()


def test_candidates_columns(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(candidates)")}
        assert {"id", "first_name", "last_name", "focus_areas",
                "healthy_weekly_rate", "pacing_notes",
                "created_at", "archived_at"} <= cols
    finally:
        conn.close()


def test_jds_has_candidate_id(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(jds)")}
        assert "candidate_id" in cols
    finally:
        conn.close()


def test_resume_versions_has_candidate_id(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(resume_versions)")}
        assert "candidate_id" in cols
    finally:
        conn.close()


def test_cover_letters_has_candidate_id(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(cover_letters)")}
        assert "candidate_id" in cols
    finally:
        conn.close()


def test_migration_recorded(isolated_db):
    conn = open_db()
    try:
        versions = [row[0] for row in conn.execute(
            "SELECT version FROM migrations ORDER BY version")]
        assert 4 in versions
    finally:
        conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/migrations/test_0004_candidates_table.py -v
```
Expected: 6 FAILs.

- [ ] **Step 3: Write the migration**

```python
# scripts/tracker/migrations/0004_candidates_table.py
"""Migration 0004 — candidates table + candidate_id FK columns.

Schema-only. Backfill is performed by scripts.tracker._post_migration.run_b_backfill,
which db.py invokes after migrations apply.

See docs/plans/2026-05-19-multi-candidate-approach-b.md.
"""
import sqlite3


SCHEMA_SQL = """
CREATE TABLE candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    focus_areas TEXT NOT NULL DEFAULT '[]',
    healthy_weekly_rate INTEGER,
    pacing_notes TEXT,
    created_at TEXT NOT NULL,
    archived_at TEXT
);

ALTER TABLE jds             ADD COLUMN candidate_id INTEGER REFERENCES candidates(id);
ALTER TABLE resume_versions ADD COLUMN candidate_id INTEGER REFERENCES candidates(id);
ALTER TABLE cover_letters   ADD COLUMN candidate_id INTEGER REFERENCES candidates(id);

CREATE INDEX idx_jds_candidate_id             ON jds(candidate_id);
CREATE INDEX idx_resume_versions_candidate_id ON resume_versions(candidate_id);
CREATE INDEX idx_cover_letters_candidate_id   ON cover_letters(candidate_id);
"""


def apply(conn: sqlite3.Connection) -> None:
    """Apply the candidates schema. Backfill runs separately."""
    conn.executescript(SCHEMA_SQL)
```

- [ ] **Step 4: Run test to verify it passes**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/migrations/test_0004_candidates_table.py -v
```
Expected: all PASS.

- [ ] **Step 5: Run the full tracker test suite (regressions)**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker -q
```
Expected: all green. (Some pre-existing tests may need to drop `archived_at IS NULL` assumptions if the new index changes plan ordering — fix inline if so.)

- [ ] **Step 6: Commit**

```bash
git add scripts/tracker/migrations/0004_candidates_table.py tests/tracker/migrations/test_0004_candidates_table.py
git commit -m "feat(tracker): migration 0004 adds candidates table + candidate_id FKs"
```

---

## Task 2: `Candidate` model + trimmed `Profile`

**Files:**
- Modify: `scripts/tracker/models.py` (add Candidate; trim Profile; add candidate_id to JD/ResumeVersion/CoverLetter)
- Test: `tests/tracker/test_models.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/tracker/test_models.py`:

```python
def test_candidate_dataclass_minimal():
    from scripts.tracker.models import Candidate
    c = Candidate(
        id=1, first_name="Mathilda", last_name="Gell",
        focus_areas=["retail"], healthy_weekly_rate=2,
        pacing_notes=None,
        created_at="2026-05-19T00:00:00Z", archived_at=None,
    )
    assert c.first_name == "Mathilda"


def test_profile_holds_active_candidate_id():
    from scripts.tracker.models import Profile
    p = Profile(active_candidate_id=1, log_handoffs=True)
    assert p.active_candidate_id == 1
    assert p.log_handoffs is True


def test_profile_default_no_active_candidate():
    from scripts.tracker.models import Profile
    p = Profile()
    assert p.active_candidate_id is None
    assert p.log_handoffs is True  # documented default


def test_resume_version_carries_candidate_id():
    from scripts.tracker.models import ResumeVersion
    rv = ResumeVersion(
        id=1, file_path=None, template="hybrid", focus_areas=[],
        parent_id=None, tagged_jd_id=None,
        created_at="2026-05-19T00:00:00Z", archived_at=None,
        candidate_id=2,
    )
    assert rv.candidate_id == 2


def test_jd_carries_candidate_id():
    from scripts.tracker.models import JD
    jd = JD(
        id=1, source="manual", source_ref=None,
        company="Acme", role_title="Eng", raw_text="...",
        analyzer_findings={}, focus_areas_required=[], focus_areas_nice=[],
        created_at="2026-05-19T00:00:00Z", archived_at=None,
        candidate_id=1,
    )
    assert jd.candidate_id == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_models.py -v -k "candidate"
```
Expected: 5 FAILs.

- [ ] **Step 3: Update `scripts/tracker/models.py`**

a. Add the `Candidate` dataclass after the existing `ResumeVersion` block (and before `Application`):

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
```

b. Add `candidate_id: Optional[int] = None` to `ResumeVersion`, `CoverLetter`, and `JD` (alongside the existing `artifact_uid` / `parent_uid` defaults).

c. Replace `Profile`:

```python
@dataclass
class Profile:
    active_candidate_id: Optional[int] = None
    log_handoffs: bool = True
```

- [ ] **Step 4: Run tests to verify they pass**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_models.py -v
```
Expected: all new PASS. The legacy-shape test (`test_profile_holds_first_last_name`, if present) will now FAIL — delete that test, Task 4 covers the file-level back-compat.

- [ ] **Step 5: Commit**

```bash
git add scripts/tracker/models.py tests/tracker/test_models.py
git commit -m "feat(tracker): Candidate dataclass + trim Profile to active_candidate_id"
```

---

## Task 3: `scripts/tracker/candidates.py` CRUD

**Files:**
- Create: `scripts/tracker/candidates.py`
- Test: `tests/tracker/test_candidates.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/tracker/test_candidates.py
"""Tests for scripts/tracker/candidates.py."""
import pytest


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_create_and_get_candidate(isolated):
    from scripts.tracker.candidates import create_candidate, get_candidate
    cid = create_candidate(
        first_name="Mathilda", last_name="Gell",
        focus_areas=["retail"], healthy_weekly_rate=2, pacing_notes=None,
    )
    c = get_candidate(cid)
    assert c is not None
    assert c.first_name == "Mathilda"
    assert c.last_name == "Gell"
    assert c.focus_areas == ["retail"]


def test_list_candidates_excludes_archived(isolated):
    from scripts.tracker.candidates import (
        create_candidate, archive_candidate, list_candidates,
    )
    cid1 = create_candidate("Matthew", "Gell", [], None, None)
    cid2 = create_candidate("Mathilda", "Gell", [], None, None)
    archive_candidate(cid1)
    rows = list_candidates()
    assert [c.id for c in rows] == [cid2]


def test_set_and_get_active_candidate(isolated):
    from scripts.tracker.candidates import (
        create_candidate, set_active_candidate, get_active_candidate,
    )
    cid = create_candidate("Matthew", "Gell", [], None, None)
    set_active_candidate(cid)
    active = get_active_candidate()
    assert active is not None
    assert active.id == cid


def test_get_active_candidate_returns_none_when_unset(isolated):
    from scripts.tracker.candidates import get_active_candidate
    assert get_active_candidate() is None


def test_update_candidate(isolated):
    from scripts.tracker.candidates import (
        create_candidate, update_candidate, get_candidate,
    )
    cid = create_candidate("Matthew", "Gell", [], None, None)
    update_candidate(cid, focus_areas=["data eng"], healthy_weekly_rate=5)
    c = get_candidate(cid)
    assert c.focus_areas == ["data eng"]
    assert c.healthy_weekly_rate == 5
```

- [ ] **Step 2: Run tests to verify they fail**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_candidates.py -v
```
Expected: 5 FAILs — ImportError.

- [ ] **Step 3: Implement the CRUD module**

```python
# scripts/tracker/candidates.py
"""CRUD for the candidates table.

Each top-level function opens a fresh DB connection. The active candidate
is stored in profile.json's active_candidate_id field; this module is the
single read/write path for that pointer.
"""
import json
from datetime import datetime
from typing import List, Optional

from scripts.tracker.db import open_db
from scripts.tracker.models import Candidate, Profile
from scripts.tracker.profile import read_profile, write_profile


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _row_to_candidate(row) -> Candidate:
    return Candidate(
        id=row[0], first_name=row[1], last_name=row[2],
        focus_areas=json.loads(row[3] or "[]"),
        healthy_weekly_rate=row[4], pacing_notes=row[5],
        created_at=row[6], archived_at=row[7],
    )


def create_candidate(
    first_name: str,
    last_name: str,
    focus_areas: List[str],
    healthy_weekly_rate: Optional[int],
    pacing_notes: Optional[str],
) -> int:
    conn = open_db()
    try:
        cur = conn.execute(
            """INSERT INTO candidates
                 (first_name, last_name, focus_areas, healthy_weekly_rate,
                  pacing_notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (first_name, last_name, json.dumps(focus_areas),
             healthy_weekly_rate, pacing_notes, _now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_candidate(candidate_id: int) -> Optional[Candidate]:
    conn = open_db()
    try:
        row = conn.execute(
            """SELECT id, first_name, last_name, focus_areas,
                      healthy_weekly_rate, pacing_notes,
                      created_at, archived_at
               FROM candidates WHERE id=?""",
            (candidate_id,),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_candidate(row) if row else None


def list_candidates(include_archived: bool = False) -> List[Candidate]:
    conn = open_db()
    try:
        sql = """SELECT id, first_name, last_name, focus_areas,
                        healthy_weekly_rate, pacing_notes,
                        created_at, archived_at
                 FROM candidates"""
        if not include_archived:
            sql += " WHERE archived_at IS NULL"
        sql += " ORDER BY created_at ASC"
        rows = conn.execute(sql).fetchall()
    finally:
        conn.close()
    return [_row_to_candidate(r) for r in rows]


def update_candidate(
    candidate_id: int,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    focus_areas: Optional[List[str]] = None,
    healthy_weekly_rate: Optional[int] = None,
    pacing_notes: Optional[str] = None,
) -> None:
    """Partial update. Only fields provided as non-None are changed.

    Note: passing None means 'do not change'. To explicitly clear
    healthy_weekly_rate or pacing_notes, set them via direct SQL
    (out of scope for this helper).
    """
    sets, params = [], []
    if first_name is not None:
        sets.append("first_name=?"); params.append(first_name)
    if last_name is not None:
        sets.append("last_name=?"); params.append(last_name)
    if focus_areas is not None:
        sets.append("focus_areas=?"); params.append(json.dumps(focus_areas))
    if healthy_weekly_rate is not None:
        sets.append("healthy_weekly_rate=?"); params.append(healthy_weekly_rate)
    if pacing_notes is not None:
        sets.append("pacing_notes=?"); params.append(pacing_notes)
    if not sets:
        return
    params.append(candidate_id)
    conn = open_db()
    try:
        conn.execute(f"UPDATE candidates SET {', '.join(sets)} WHERE id=?", params)
        conn.commit()
    finally:
        conn.close()


def archive_candidate(candidate_id: int) -> None:
    conn = open_db()
    try:
        conn.execute(
            "UPDATE candidates SET archived_at=? WHERE id=?",
            (_now_iso(), candidate_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_active_candidate(candidate_id: int) -> None:
    profile = read_profile()
    write_profile(Profile(
        active_candidate_id=candidate_id,
        log_handoffs=profile.log_handoffs,
    ))


def get_active_candidate() -> Optional[Candidate]:
    profile = read_profile()
    if profile.active_candidate_id is None:
        return None
    return get_candidate(profile.active_candidate_id)
```

- [ ] **Step 4: Run tests to verify they pass**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_candidates.py -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/tracker/candidates.py tests/tracker/test_candidates.py
git commit -m "feat(tracker): candidates CRUD module + active-candidate accessor"
```

---

## Task 4: Trimmed `profile.py` with legacy-read back-compat

**Files:**
- Modify: `scripts/tracker/profile.py`
- Test: `tests/tracker/test_profile.py`

Goal: `read_profile()` returns the trimmed `Profile` dataclass. If the JSON file on disk has the legacy shape (first_name/last_name/focus_areas/etc), those fields are *ignored* by `read_profile` — they are consumed by the backfill hook only. `write_profile` always writes the trimmed shape.

- [ ] **Step 1: Update the failing tests**

In `tests/tracker/test_profile.py`, replace the legacy-shape tests with:

```python
def test_read_profile_trimmed_shape(tmp_path, monkeypatch):
    """A profile.json in the post-B trimmed shape reads cleanly."""
    p = tmp_path / "profile.json"
    p.write_text('{"active_candidate_id": 5, "log_handoffs": false}', encoding="utf-8")
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(p))

    from scripts.tracker.profile import read_profile
    prof = read_profile()
    assert prof.active_candidate_id == 5
    assert prof.log_handoffs is False


def test_read_profile_legacy_shape_returns_empty(tmp_path, monkeypatch):
    """A profile.json in the pre-B legacy shape reads as an empty Profile.

    The legacy fields (first_name/last_name/focus_areas/...) are not on the
    new Profile dataclass; they are consumed by the backfill hook only.
    """
    p = tmp_path / "profile.json"
    p.write_text(
        '{"first_name": "Matthew", "last_name": "Gell",'
        ' "focus_areas": ["data eng"], "healthy_weekly_rate": 5,'
        ' "log_handoffs": true}',
        encoding="utf-8",
    )
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(p))

    from scripts.tracker.profile import read_profile
    prof = read_profile()
    assert prof.active_candidate_id is None
    assert prof.log_handoffs is True


def test_write_profile_writes_trimmed_shape(tmp_path, monkeypatch):
    from scripts.tracker.profile import write_profile
    from scripts.tracker.models import Profile

    p = tmp_path / "profile.json"
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(p))
    write_profile(Profile(active_candidate_id=7, log_handoffs=False))

    import json
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data == {"active_candidate_id": 7, "log_handoffs": False}
```

- [ ] **Step 2: Run tests to verify they fail**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_profile.py -v
```
Expected: FAILs — current code uses the legacy dataclass shape.

- [ ] **Step 3: Update `scripts/tracker/profile.py`**

Replace the body of the file with:

```python
"""Read/write helpers for ~/.brains-resume/profile.json (post-B trimmed shape).

The profile now holds two fields only: the pointer to the active candidate
and the log_handoffs UI preference. Per-candidate data (name, focus areas,
healthy weekly rate, pacing notes) lives in the candidates table.

Backwards-compat: a legacy-shape file (with first_name/focus_areas/etc) is
read as an empty Profile. The legacy fields are NOT lost — they are consumed
by scripts.tracker._post_migration.run_b_backfill when the schema reaches v4.
"""
import json
import os
from pathlib import Path

from scripts.tracker.models import Profile


DEFAULT_PROFILE_PATH = Path.home() / ".brains-resume" / "profile.json"


def get_profile_path() -> Path:
    override = os.environ.get("BRAINS_TRACKER_PROFILE_PATH")
    if override:
        return Path(override)
    return DEFAULT_PROFILE_PATH


def read_profile() -> Profile:
    path = get_profile_path()
    if not path.exists():
        return Profile()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Profile()
    if not isinstance(data, dict):
        return Profile()
    return Profile(
        active_candidate_id=data.get("active_candidate_id"),
        log_handoffs=data.get("log_handoffs", True),
    )


def write_profile(profile: Profile) -> None:
    path = get_profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "active_candidate_id": profile.active_candidate_id,
                "log_handoffs": profile.log_handoffs,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_profile.py -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/tracker/profile.py tests/tracker/test_profile.py
git commit -m "feat(tracker): Profile trimmed to {active_candidate_id, log_handoffs}"
```

---

## Task 5: Idempotent backfill hook

**Files:**
- Create: `scripts/tracker/_post_migration.py`
- Modify: `scripts/tracker/db.py`
- Test: `tests/tracker/test_post_migration.py`

Goal: after migrations run, `db.py` calls `run_b_backfill(conn)`. The hook is idempotent — it inspects state, performs the backfill only if needed, and is safe to call on every `open_db()` (so a partially-completed install converges).

The backfill, when needed:
1. Reads `profile.json` directly (without going through `read_profile()`, so it sees legacy fields).
2. If `candidates` table is empty AND legacy `first_name` is present in the JSON: inserts a seed candidate from those fields.
3. For each row in `resume_versions` / `cover_letters` with `candidate_id IS NULL`: if `for_candidate` is set, find or create a candidate by name and link; otherwise link to the seed candidate.
4. For each row in `jds` with `candidate_id IS NULL`: link to the seed candidate.
5. Sets `active_candidate_id` in `profile.json` to the seed candidate's id; rewrites `profile.json` to the trimmed shape (dropping legacy fields).

- [ ] **Step 1: Write the failing tests**

```python
# tests/tracker/test_post_migration.py
"""Tests for the B-migration backfill hook."""
import json

import pytest


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def _write_legacy_profile(path, **fields):
    payload = {
        "first_name": "Matthew", "last_name": "Gell",
        "focus_areas": ["data eng"], "healthy_weekly_rate": 5,
        "pacing_notes": None, "log_handoffs": True,
    }
    payload.update(fields)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_backfill_creates_seed_candidate_from_legacy_profile(isolated):
    _write_legacy_profile(isolated / "profile.json")
    from scripts.tracker.db import open_db
    conn = open_db()  # this should run the backfill
    try:
        rows = conn.execute(
            "SELECT first_name, last_name, focus_areas, healthy_weekly_rate "
            "FROM candidates"
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0][0] == "Matthew"
    assert rows[0][1] == "Gell"
    assert json.loads(rows[0][2]) == ["data eng"]
    assert rows[0][3] == 5


def test_backfill_sets_active_candidate_in_profile_json(isolated):
    _write_legacy_profile(isolated / "profile.json")
    from scripts.tracker.db import open_db
    open_db().close()
    data = json.loads((isolated / "profile.json").read_text(encoding="utf-8"))
    assert data.get("active_candidate_id") is not None
    # Legacy fields are dropped from the file after backfill.
    assert "first_name" not in data
    assert "focus_areas" not in data


def test_backfill_links_existing_artifacts_to_seed_candidate(isolated):
    """Pre-existing artifacts (from a v1.5/1.6 install) get linked."""
    _write_legacy_profile(isolated / "profile.json")
    from scripts.tracker.db import open_db
    # First open: schema only, no backfill possible if profile.json hasn't been
    # written yet — but profile.json IS written above, so backfill should
    # complete on first open. To exercise the link-existing-artifacts path,
    # we insert artifacts via raw SQL BEFORE first open.
    # Workaround: open once to apply schema, insert artifacts, then re-open to
    # trigger backfill. Implementation may guard against repeated runs — that's
    # tested below.
    conn = open_db()
    try:
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at) "
            "VALUES ('chronological', '[]', '2026-05-01T00:00:00Z')"
        )
        conn.commit()
    finally:
        conn.close()
    # Reopen — backfill should run if it hasn't already, OR re-link the
    # newly-inserted row. Test the post-condition either way.
    conn = open_db()
    try:
        rv = conn.execute(
            "SELECT candidate_id FROM resume_versions"
        ).fetchone()
        active_id = conn.execute(
            "SELECT id FROM candidates LIMIT 1"
        ).fetchone()[0]
    finally:
        conn.close()
    assert rv[0] == active_id


def test_backfill_assigns_distinct_candidate_for_for_candidate_rows(isolated):
    _write_legacy_profile(isolated / "profile.json")
    from scripts.tracker.db import open_db
    conn = open_db()  # creates schema and seed candidate
    try:
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, for_candidate, created_at) "
            "VALUES ('hybrid', '[]', 'Mathilda Gell', '2026-05-19T00:00:00Z')"
        )
        conn.commit()
    finally:
        conn.close()
    conn = open_db()  # second open re-runs backfill, picking up the new row
    try:
        candidates = conn.execute(
            "SELECT first_name, last_name FROM candidates ORDER BY id"
        ).fetchall()
        rv = conn.execute(
            "SELECT candidate_id, for_candidate FROM resume_versions"
        ).fetchone()
        mathilda_id = conn.execute(
            "SELECT id FROM candidates WHERE first_name='Mathilda'"
        ).fetchone()
    finally:
        conn.close()
    names = {(c[0], c[1]) for c in candidates}
    assert ("Matthew", "Gell") in names
    assert ("Mathilda", "Gell") in names
    assert mathilda_id is not None
    assert rv[0] == mathilda_id[0]
    assert rv[1] == "Mathilda Gell"  # for_candidate cache preserved


def test_backfill_is_idempotent(isolated):
    _write_legacy_profile(isolated / "profile.json")
    from scripts.tracker.db import open_db
    open_db().close()
    open_db().close()
    open_db().close()
    conn = open_db()
    try:
        count = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    finally:
        conn.close()
    assert count == 1  # one seed candidate, not three
```

- [ ] **Step 2: Run tests to verify they fail**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_post_migration.py -v
```
Expected: 5 FAILs — module doesn't exist; db.py doesn't call it.

- [ ] **Step 3: Implement the hook**

```python
# scripts/tracker/_post_migration.py
"""Idempotent post-migration hooks.

Called by db.py::open_db after migrations apply. Each hook checks its own
preconditions and is safe to invoke on every connection open.
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from scripts.outputs.naming import split_candidate_name
from scripts.tracker.profile import get_profile_path


def run_b_backfill(conn: sqlite3.Connection) -> None:
    """Backfill candidates + candidate_id links the first time a v4-schema DB
    opens against a pre-B profile.json.

    Idempotency contract: this function may be called repeatedly. On a fully
    backfilled DB it is a no-op. On a partially backfilled DB it picks up
    where it left off.
    """
    # 1. Confirm schema is at v4+ (else: nothing to backfill).
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if "candidates" not in tables:
        return

    profile_path = get_profile_path()
    seed_id = _ensure_seed_candidate(conn, profile_path)

    # 2. Link rows with for_candidate set to a per-name candidate row.
    for table in ("resume_versions", "cover_letters"):
        for row in conn.execute(
            f"SELECT id, for_candidate FROM {table} "
            f"WHERE candidate_id IS NULL AND for_candidate IS NOT NULL"
        ).fetchall():
            artifact_id, name = row
            cid = _find_or_create_candidate_by_name(conn, name)
            conn.execute(
                f"UPDATE {table} SET candidate_id=? WHERE id=?",
                (cid, artifact_id),
            )

    # 3. Link rows with NULL candidate_id (and NULL for_candidate) to seed.
    if seed_id is not None:
        for table in ("resume_versions", "cover_letters", "jds"):
            conn.execute(
                f"UPDATE {table} SET candidate_id=? "
                f"WHERE candidate_id IS NULL",
                (seed_id,),
            )
    conn.commit()


def _ensure_seed_candidate(conn: sqlite3.Connection, profile_path: Path):
    """If candidates table is empty and profile.json has legacy fields,
    create a seed candidate and set it as active. Returns the seed id, or
    the existing active candidate id, or None if no seed could be created.
    """
    seed_row = conn.execute(
        "SELECT id FROM candidates ORDER BY id LIMIT 1"
    ).fetchone()
    if seed_row is not None:
        return seed_row[0]

    if not profile_path.exists():
        return None
    try:
        data = json.loads(profile_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    first = (data or {}).get("first_name")
    last = (data or {}).get("last_name")
    if not first or not last:
        return None
    focus_areas = (data or {}).get("focus_areas") or []
    healthy_rate = (data or {}).get("healthy_weekly_rate")
    pacing_notes = (data or {}).get("pacing_notes")
    log_handoffs = (data or {}).get("log_handoffs", True)

    cur = conn.execute(
        """INSERT INTO candidates
             (first_name, last_name, focus_areas, healthy_weekly_rate,
              pacing_notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (first, last, json.dumps(focus_areas), healthy_rate, pacing_notes,
         datetime.utcnow().isoformat() + "Z"),
    )
    seed_id = cur.lastrowid

    # Rewrite profile.json to trimmed shape.
    profile_path.write_text(
        json.dumps({
            "active_candidate_id": seed_id,
            "log_handoffs": log_handoffs,
        }, indent=2),
        encoding="utf-8",
    )
    return seed_id


def _find_or_create_candidate_by_name(conn: sqlite3.Connection, name: str) -> int:
    """Find a candidate by first+last name. Create one if missing.

    Uses split_candidate_name from outputs.naming. Multi-token first-name
    matches (e.g. 'Anne Marie') are recognised because the split groups
    middle tokens with the given name.
    """
    first, last = split_candidate_name(name)
    row = conn.execute(
        """SELECT id FROM candidates
           WHERE first_name=? AND last_name=? AND archived_at IS NULL
           ORDER BY id LIMIT 1""",
        (first, last),
    ).fetchone()
    if row is not None:
        return row[0]
    cur = conn.execute(
        """INSERT INTO candidates
             (first_name, last_name, focus_areas, healthy_weekly_rate,
              pacing_notes, created_at)
           VALUES (?, ?, '[]', NULL, NULL, ?)""",
        (first, last, datetime.utcnow().isoformat() + "Z"),
    )
    return cur.lastrowid
```

- [ ] **Step 4: Wire the hook into `db.py`**

In `scripts/tracker/db.py`, add to the bottom of `open_db()`:

```python
def open_db() -> sqlite3.Connection:
    """Open (creating if needed) the tracker db, run pending migrations,
    apply post-migration backfill hooks, enable foreign keys, return the
    connection."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    _ensure_migrations_table(conn)
    _run_pending_migrations(conn)
    _run_post_migration_hooks(conn)
    return conn


def _run_post_migration_hooks(conn: sqlite3.Connection) -> None:
    """Idempotent post-migration backfill. Safe to run on every open."""
    from scripts.tracker._post_migration import run_b_backfill
    run_b_backfill(conn)
```

- [ ] **Step 5: Run tests to verify they pass**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_post_migration.py -v
```
Expected: all 5 PASS. Run the full tracker suite too:

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker -q
```
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add scripts/tracker/_post_migration.py scripts/tracker/db.py tests/tracker/test_post_migration.py
git commit -m "feat(tracker): idempotent post-migration backfill for candidates table"
```

---

## Task 6: `add.py` — candidate_id default = active

**Files:**
- Modify: `scripts/tracker/add.py`
- Test: `tests/tracker/test_add.py`

Goal: every insert function takes `candidate_id: Optional[int] = None`. When `None`, the function looks up the active candidate via `get_active_candidate()` and uses that id. If neither is available, raises `NoActiveCandidateError`. The `for_candidate` parameter remains accepted but is now derived from the candidate row when not explicitly provided.

- [ ] **Step 1: Write the failing test**

Append to `tests/tracker/test_add.py`:

```python
def test_add_resume_version_defaults_to_active_candidate(isolated):
    from scripts.tracker.add import add_resume_version
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    from scripts.tracker.db import open_db

    cid = create_candidate("Matthew", "Gell", [], None, None)
    set_active_candidate(cid)
    rv_id = add_resume_version(None, "hybrid", [])
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT candidate_id FROM resume_versions WHERE id=?", (rv_id,)
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == cid


def test_add_resume_version_explicit_candidate_id(isolated):
    from scripts.tracker.add import add_resume_version
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    from scripts.tracker.db import open_db

    active = create_candidate("Matthew", "Gell", [], None, None)
    other  = create_candidate("Mathilda", "Gell", [], None, None)
    set_active_candidate(active)
    rv_id = add_resume_version(None, "hybrid", [], candidate_id=other)
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT candidate_id FROM resume_versions WHERE id=?", (rv_id,)
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == other


def test_add_resume_version_no_active_no_override_raises(isolated):
    from scripts.tracker.add import add_resume_version, NoActiveCandidateError
    with pytest.raises(NoActiveCandidateError):
        add_resume_version(None, "hybrid", [])
```

- [ ] **Step 2: Run tests to verify they fail**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_add.py -v -k candidate
```
Expected: 3 FAILs.

- [ ] **Step 3: Update `scripts/tracker/add.py`**

Add at top of file:

```python
class NoActiveCandidateError(Exception):
    """Raised when an insert has no candidate_id override AND no active candidate is set."""


def _resolve_candidate_id(candidate_id: Optional[int]) -> int:
    if candidate_id is not None:
        return candidate_id
    from scripts.tracker.candidates import get_active_candidate
    active = get_active_candidate()
    if active is None:
        raise NoActiveCandidateError(
            "No active candidate is set. Pass candidate_id explicitly or "
            "select a candidate in the dashboard sidebar."
        )
    return active.id
```

Update `add_resume_version`, `add_jd`, `add_cover_letter` to accept `candidate_id: Optional[int] = None`, call `_resolve_candidate_id` at the top, and include `candidate_id` in the INSERT column list. (Pattern is identical for all three; show one and replicate.)

For example, the updated `add_resume_version`:

```python
def add_resume_version(
    file_path: Optional[str],
    template: str,
    focus_areas: List[str],
    parent_id: Optional[int] = None,
    tagged_jd_id: Optional[int] = None,
    artifact_uid: Optional[str] = None,
    parent_uid: Optional[str] = None,
    for_candidate: Optional[str] = None,
    candidate_id: Optional[int] = None,
) -> int:
    """Insert a resume_versions row, return the new id."""
    resolved_cid = _resolve_candidate_id(candidate_id)
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO resume_versions
                (file_path, template, focus_areas, parent_id, tagged_jd_id,
                 created_at, artifact_uid, parent_uid, for_candidate,
                 candidate_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (file_path, template, json.dumps(focus_areas), parent_id,
             tagged_jd_id, _now_iso(), artifact_uid, parent_uid,
             for_candidate, resolved_cid),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
```

Apply the same pattern to `add_jd` and `add_cover_letter`. `add_application` and `record_outcome` do not need a `candidate_id` — they inherit candidate scoping via their FK to `applications.jd_id` → `jds.candidate_id`. (Confirm this is sufficient for query scoping in Task 7.)

- [ ] **Step 4: Run tests to verify they pass**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_add.py -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/tracker/add.py tests/tracker/test_add.py
git commit -m "feat(tracker): inserts default candidate_id to active candidate"
```

---

## Task 7: `query.py` — scope reads to active candidate

**Files:**
- Modify: `scripts/tracker/query.py`
- Test: `tests/tracker/test_query.py`

Goal: every list-style read function takes an optional `candidate_id: Optional[int] = None` argument. When `None`, the function resolves to the active candidate. When an integer is provided, it overrides. When `0` is passed (sentinel), the function returns rows for ALL candidates (used by data-export paths). The existing `list_artifacts_for_candidate(name)` keeps its name-based signature but now JOINs on `candidates` for accuracy.

- [ ] **Step 1: Write failing tests**

Append to `tests/tracker/test_query.py`:

```python
def test_list_jds_default_filters_to_active_candidate(isolated):
    from scripts.tracker.add import add_jd
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    from scripts.tracker.query import list_jds

    matthew = create_candidate("Matthew", "Gell", [], None, None)
    mathilda = create_candidate("Mathilda", "Gell", [], None, None)
    set_active_candidate(matthew)
    add_jd("manual", None, "Acme", "Eng", "...", {}, [], [])
    set_active_candidate(mathilda)
    add_jd("manual", None, "Big W", "Sales Asst", "...", {}, [], [])

    set_active_candidate(matthew)
    rows = list_jds()
    assert {r.company for r in rows} == {"Acme"}

    set_active_candidate(mathilda)
    rows = list_jds()
    assert {r.company for r in rows} == {"Big W"}


def test_list_jds_explicit_candidate_id_override(isolated):
    from scripts.tracker.add import add_jd
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    from scripts.tracker.query import list_jds

    matthew = create_candidate("Matthew", "Gell", [], None, None)
    mathilda = create_candidate("Mathilda", "Gell", [], None, None)
    set_active_candidate(matthew)
    add_jd("manual", None, "Acme", "Eng", "...", {}, [], [])
    set_active_candidate(mathilda)
    add_jd("manual", None, "Big W", "Sales Asst", "...", {}, [], [])

    rows_all = list_jds(candidate_id=0)
    assert {r.company for r in rows_all} == {"Acme", "Big W"}
```

(Adapt assertion names to whatever the actual `list_jds` returns — the existing module determines whether it's `JD` dataclasses or rows. Mirror that.)

- [ ] **Step 2: Run tests to verify they fail**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_query.py -v -k candidate
```
Expected: FAILs.

- [ ] **Step 3: Update `scripts/tracker/query.py`**

a. Add at the top of the file:

```python
def _scope_candidate_clause(candidate_id: Optional[int]) -> tuple[str, tuple]:
    """Return (WHERE-fragment, params) for the candidate scope.

    None  -> filter by active candidate (raises if none set)
    0     -> no filter (all candidates)
    int>0 -> filter by that candidate
    """
    if candidate_id == 0:
        return ("", ())
    if candidate_id is None:
        from scripts.tracker.candidates import get_active_candidate
        active = get_active_candidate()
        if active is None:
            return ("", ())  # no active candidate: behave like 0 for read paths
        candidate_id = active.id
    return ("candidate_id = ?", (candidate_id,))
```

b. For each list/get function that currently does `SELECT * FROM <table>`, add `candidate_id: Optional[int] = None` and weave in the scope clause.

c. Rewrite `list_artifacts_for_candidate(name)` to JOIN:

```python
def list_artifacts_for_candidate(name: str) -> list:
    """Return all resume_versions + cover_letters whose candidate matches the name.

    Matches by candidate first+last name (split via outputs.naming.split_candidate_name).
    """
    from scripts.outputs.naming import split_candidate_name
    from scripts.tracker.models import ResumeVersion, CoverLetter
    first, last = split_candidate_name(name)
    conn = open_db()
    try:
        results = []
        for row in conn.execute(
            """SELECT rv.id, rv.file_path, rv.template, rv.focus_areas,
                      rv.parent_id, rv.tagged_jd_id, rv.created_at,
                      rv.archived_at, rv.artifact_uid, rv.parent_uid,
                      rv.for_candidate, rv.candidate_id
               FROM resume_versions rv
               JOIN candidates c ON c.id = rv.candidate_id
               WHERE c.first_name = ? AND c.last_name = ?
                 AND rv.archived_at IS NULL
               ORDER BY rv.created_at DESC""",
            (first, last),
        ):
            import json as _json
            results.append(ResumeVersion(
                id=row[0], file_path=row[1], template=row[2],
                focus_areas=_json.loads(row[3] or "[]"),
                parent_id=row[4], tagged_jd_id=row[5],
                created_at=row[6], archived_at=row[7],
                artifact_uid=row[8], parent_uid=row[9],
                for_candidate=row[10], candidate_id=row[11],
            ))
        # Same JOIN pattern for cover_letters.
        for row in conn.execute(
            """SELECT cl.id, cl.file_path, cl.resume_version_id, cl.jd_id,
                      cl.template, cl.created_at, cl.archived_at,
                      cl.artifact_uid, cl.parent_uid, cl.for_candidate,
                      cl.candidate_id
               FROM cover_letters cl
               JOIN candidates c ON c.id = cl.candidate_id
               WHERE c.first_name = ? AND c.last_name = ?
                 AND cl.archived_at IS NULL
               ORDER BY cl.created_at DESC""",
            (first, last),
        ):
            results.append(CoverLetter(
                id=row[0], file_path=row[1], resume_version_id=row[2],
                jd_id=row[3], template=row[4],
                created_at=row[5], archived_at=row[6],
                artifact_uid=row[7], parent_uid=row[8],
                for_candidate=row[9], candidate_id=row[10],
            ))
        return results
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker -q
```
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add scripts/tracker/query.py tests/tracker/test_query.py
git commit -m "feat(tracker): queries scope to active candidate; JOIN-based name lookup"
```

---

## Task 8: `make_artifact_path` resolves to candidate name via candidate_id

**Files:**
- Modify: `scripts/outputs/io.py`
- Test: `tests/outputs/test_io.py`

Goal: `make_artifact_path` no longer reads `profile.first_name` — it looks up the active candidate's name via `get_active_candidate()`. Accepts optional `candidate_id` override. Keeps `for_candidate` as a back-compat alias that resolves to a candidate row by name (creates one if missing — same logic as the post-migration hook's `_find_or_create_candidate_by_name`, exposed via `candidates.py` as a public helper).

- [ ] **Step 1: Add a public helper to candidates.py**

```python
def find_or_create_by_name(name: str) -> int:
    """Find a candidate by free-text name; create with empty focus areas if missing."""
    from scripts.outputs.naming import split_candidate_name
    from scripts.tracker.db import open_db
    first, last = split_candidate_name(name)
    conn = open_db()
    try:
        row = conn.execute(
            """SELECT id FROM candidates
               WHERE first_name=? AND last_name=? AND archived_at IS NULL
               ORDER BY id LIMIT 1""",
            (first, last),
        ).fetchone()
        if row is not None:
            return row[0]
        cur = conn.execute(
            """INSERT INTO candidates
                 (first_name, last_name, focus_areas, healthy_weekly_rate,
                  pacing_notes, created_at)
               VALUES (?, ?, '[]', NULL, NULL, ?)""",
            (first, last, _now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
```

Add a unit test for it in `tests/tracker/test_candidates.py` mirroring the post_migration test.

- [ ] **Step 2: Write the failing io.py test**

Append to `tests/outputs/test_io.py`:

```python
def test_make_artifact_path_uses_active_candidate_name(isolated):
    from scripts.outputs.io import make_artifact_path
    from scripts.tracker.add import add_jd
    from scripts.tracker.candidates import create_candidate, set_active_candidate

    cid = create_candidate("Mathilda", "Gell", [], None, None)
    set_active_candidate(cid)
    jd_id = add_jd("manual", None, "Acme", "Eng", "...", {}, [], [])

    path, meta = make_artifact_path(jd_id, "resume")
    assert "Mathilda" in path.name
    assert "Gell" in path.name
    assert meta.candidate_id == cid


def test_make_artifact_path_explicit_candidate_id_override(isolated):
    from scripts.outputs.io import make_artifact_path
    from scripts.tracker.add import add_jd
    from scripts.tracker.candidates import create_candidate, set_active_candidate

    matthew = create_candidate("Matthew", "Gell", [], None, None)
    mathilda = create_candidate("Mathilda", "Gell", [], None, None)
    set_active_candidate(matthew)
    jd_id = add_jd("manual", None, "Acme", "Eng", "...", {}, [], [])

    path, meta = make_artifact_path(jd_id, "resume", candidate_id=mathilda)
    assert "Mathilda" in path.name
    assert meta.candidate_id == mathilda


def test_make_artifact_path_for_candidate_alias_resolves_to_candidate_id(isolated):
    """v1.6 callers passing for_candidate still work; we resolve it to candidate_id."""
    from scripts.outputs.io import make_artifact_path
    from scripts.tracker.add import add_jd
    from scripts.tracker.candidates import create_candidate, set_active_candidate

    cid = create_candidate("Matthew", "Gell", [], None, None)
    set_active_candidate(cid)
    jd_id = add_jd("manual", None, "Acme", "Eng", "...", {}, [], [])

    path, meta = make_artifact_path(
        jd_id, "resume", for_candidate="Mathilda Gell",
    )
    assert "Mathilda" in path.name
    assert meta.for_candidate == "Mathilda Gell"
    assert meta.candidate_id is not None
    assert meta.candidate_id != cid  # not Matthew
```

- [ ] **Step 3: Run tests to verify they fail**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/outputs/test_io.py -v -k candidate
```
Expected: 3 FAILs.

- [ ] **Step 4: Update `make_artifact_path`**

Replace the function in `scripts/outputs/io.py`:

```python
def make_artifact_path(
    jd_id: int,
    kind: Literal["resume", "cover-letter"],
    parent_uid: str | None = None,
    for_candidate: str | None = None,
    candidate_id: int | None = None,
) -> tuple[Path, ArtifactMeta]:
    """Reserve a new artifact path + UID within the JD folder.

    Resolution order for the candidate whose name appears in the filename:
      1. explicit candidate_id (if provided)
      2. for_candidate name (resolved to candidate_id via find_or_create_by_name)
      3. active candidate from profile.json
      4. raises NoActiveCandidateError if none of the above resolves
    """
    from scripts.tracker.candidates import (
        get_active_candidate, get_candidate, find_or_create_by_name,
    )

    if candidate_id is None and for_candidate:
        candidate_id = find_or_create_by_name(for_candidate)
    if candidate_id is None:
        active = get_active_candidate()
        if active is None:
            from scripts.tracker.add import NoActiveCandidateError
            raise NoActiveCandidateError(
                "No active candidate set. Pass candidate_id, for_candidate, "
                "or select a candidate in the dashboard sidebar."
            )
        candidate_id = active.id

    candidate = get_candidate(candidate_id)
    if candidate is None:
        raise ValueError(f"No candidate row with id={candidate_id}")

    folder = ensure_jd_folder(jd_id)
    today = _date.today()
    for _ in range(_MAX_UID_RETRIES):
        uid = new_uid()
        if find_artifact_by_uid(uid) is None:
            break
    else:
        raise UIDCollisionError(
            f"5 consecutive UID generations all collided."
        )
    filename = artifact_filename(
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        kind=kind, created_date=today, uid=uid,
    )
    path = folder / filename
    meta = ArtifactMeta(
        artifact_uid=uid,
        artifact_kind=kind,
        jd_id=jd_id,
        parent_uid=parent_uid,
        created_at=datetime.utcnow().isoformat() + "Z",
        skill_version=_SKILL_VERSION,
        for_candidate=for_candidate,
        candidate_id=candidate_id,
    )
    return path, meta
```

Note: This drops the `read_profile().first_name` path entirely; the old `ProfileNameMissingError` is no longer raised by this function. The existing dashboard workflow code that catches `ProfileNameMissingError` must be updated in Task 11.

- [ ] **Step 5: Run tests to verify they pass**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/outputs/test_io.py -v
```
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/outputs/io.py scripts/tracker/candidates.py tests/outputs/test_io.py tests/tracker/test_candidates.py
git commit -m "feat(outputs): make_artifact_path resolves candidate via candidate_id"
```

---

## Task 9: `ArtifactMeta` + `BrainsCandidateId` DOCX custom property

**Files:**
- Modify: `scripts/outputs/tagging.py`
- Test: `tests/outputs/test_tagging.py`

Mirror Task 6 of Plan C exactly, but for `candidate_id: int | None = None` persisted as `BrainsCandidateId` (vt:i4, stored as `"0"` when `None`).

- [ ] **Step 1: Append failing tests** (mirroring `test_for_candidate_roundtrips_through_docx` from Plan C with `candidate_id` instead).

- [ ] **Step 2: Run tests to verify they fail.**

- [ ] **Step 3: Update `ArtifactMeta`, `_meta_to_property_dict`, and `read_artifact_meta`** to add `BrainsCandidateId` (vt:i4) handling. Reader maps `"0"` → `None`; pre-B DOCX files (which have no `BrainsCandidateId` property) read as `candidate_id=None`.

- [ ] **Step 4: Run tests to verify they pass.**

- [ ] **Step 5: Commit:**

```bash
git add scripts/outputs/tagging.py tests/outputs/test_tagging.py
git commit -m "feat(outputs): ArtifactMeta + DOCX gain BrainsCandidateId custom property"
```

---

## Task 10: Dashboard sidebar candidate picker

**Files:**
- Modify: `scripts/dashboard/sidebar.py`
- Test: `tests/dashboard/test_app_import.py` (smoke); add focused tests in a new `tests/dashboard/test_sidebar_candidate_picker.py`

Goal: the sidebar replaces the first/last-name text inputs with:
1. A `st.selectbox` listing all non-archived candidates (showing `First Last`), with the active one pre-selected.
2. A "+ New candidate" expander that prompts for first/last/focus-areas/healthy-rate/pacing-notes and creates a row via `candidates.create_candidate(...)`.
3. An "Edit selected" expander for editing the selected candidate's focus areas / healthy rate / pacing notes.
4. Selecting a candidate from the dropdown calls `set_active_candidate(...)` and triggers `st.rerun()`.

- [ ] **Step 1: Write a smoke test**

```python
# tests/dashboard/test_sidebar_candidate_picker.py
"""Sidebar candidate picker — wiring + active-candidate persistence."""
import pytest


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def test_sidebar_module_imports_with_candidate_picker(isolated):
    """Smoke: the rewritten sidebar imports without error."""
    import importlib
    from scripts.dashboard import sidebar
    importlib.reload(sidebar)
    assert hasattr(sidebar, "render")


def test_picker_pre_selects_active_candidate(isolated, monkeypatch):
    """When an active candidate is set, the picker's default index points to it."""
    from scripts.tracker.candidates import create_candidate, set_active_candidate

    a = create_candidate("Matthew", "Gell", [], None, None)
    b = create_candidate("Mathilda", "Gell", [], None, None)
    set_active_candidate(b)

    from scripts.dashboard.sidebar import _resolve_picker_default_index
    candidates_in_order = [a, b]  # ids only matter for ordering
    idx = _resolve_picker_default_index(candidates_in_order, active_id=b)
    assert idx == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/test_sidebar_candidate_picker.py -v
```
Expected: FAILs — sidebar module doesn't have `_resolve_picker_default_index`.

- [ ] **Step 3: Rewrite sidebar.py**

The exact rewrite depends on the current sidebar layout. The key changes:

a. Remove the `st.text_input("First name")` / `st.text_input("Last name")` / `st.text_input("Focus areas")` widgets that currently read/write `Profile.first_name` etc.

b. Add at the top of `render()`:

```python
from scripts.tracker.candidates import (
    list_candidates, create_candidate, update_candidate,
    set_active_candidate, get_active_candidate,
)

candidates = list_candidates()
active = get_active_candidate()
labels = [f"{c.first_name} {c.last_name}".strip() for c in candidates]
default_idx = _resolve_picker_default_index(candidates, active.id if active else None)
selection = st.sidebar.selectbox(
    "Candidate", options=labels, index=default_idx,
    key="sidebar_candidate_picker",
)
if selection:
    chosen = candidates[labels.index(selection)]
    if active is None or chosen.id != active.id:
        set_active_candidate(chosen.id)
        st.rerun()
```

c. Extract a pure helper for testability:

```python
def _resolve_picker_default_index(candidates: list, active_id) -> int:
    if not candidates:
        return 0
    if active_id is None:
        return 0
    for i, c in enumerate(candidates):
        if c.id == active_id:
            return i
    return 0
```

d. Add the "+ New candidate" expander:

```python
with st.sidebar.expander("+ New candidate"):
    new_first = st.text_input("First name", key="new_first")
    new_last = st.text_input("Last name", key="new_last")
    new_focus_raw = st.text_area("Focus areas (one per line)", key="new_focus")
    new_rate = st.number_input("Healthy weekly rate", min_value=0, step=1, key="new_rate")
    new_notes = st.text_area("Pacing notes (optional)", key="new_notes")
    if st.button("Create candidate"):
        focus = [line.strip() for line in (new_focus_raw or "").splitlines() if line.strip()]
        cid = create_candidate(
            first_name=new_first, last_name=new_last,
            focus_areas=focus,
            healthy_weekly_rate=int(new_rate) if new_rate else None,
            pacing_notes=new_notes or None,
        )
        set_active_candidate(cid)
        st.rerun()
```

e. Add an "Edit selected" expander mirroring the New form but pre-populated and calling `update_candidate(active.id, ...)`.

- [ ] **Step 4: Run tests to verify they pass**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/test_sidebar_candidate_picker.py tests/dashboard/test_app_import.py -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/sidebar.py tests/dashboard/test_sidebar_candidate_picker.py
git commit -m "feat(dashboard): sidebar candidate picker replaces name inputs"
```

---

## Task 11: Workflow cards drop `for_candidate` input; use active candidate

**Files:**
- Modify: `scripts/dashboard/workflows/create.py`, `edit.py`, `tailor.py`, `cover_letter.py`
- Test: `tests/dashboard/test_workflows_card.py`

For each workflow card:

1. Remove the `st.text_input("For candidate (optional)")` introduced by Plan C.
2. Remove the `_resolve_target(for_candidate=...)` parameter — replace with a call that reads the active candidate.
3. Drop the `ProfileNameMissingError` catch (no longer raised by `make_artifact_path` — Task 8 removed that path). Replace with a `NoActiveCandidateError` catch that points the user to the sidebar.
4. Add a "Switch candidate" caption that names the currently active candidate so users know who the resume will be FOR.

- [ ] **Step 1: Update tests**

Modify the tests added in Task 9 of Plan C: instead of asserting `captured["for_candidate"]`, assert that `make_artifact_path` was called without a `for_candidate` kwarg and that the resulting `meta.candidate_id` matches the active candidate set via `set_active_candidate(...)` in the test setup.

- [ ] **Step 2: Run tests to verify they fail.**

- [ ] **Step 3: Update each workflow file** per the four changes listed above. The active-candidate caption goes in the card body before the handoff button:

```python
active = get_active_candidate()
if active is None:
    st.error("No active candidate. Select or create one in the sidebar.")
    return
st.caption(f"This resume will be for: **{active.first_name} {active.last_name}**.")
```

- [ ] **Step 4: Run tests to verify they pass.**

- [ ] **Step 5: Commit:**

```bash
git add scripts/dashboard/workflows/create.py scripts/dashboard/workflows/edit.py scripts/dashboard/workflows/tailor.py scripts/dashboard/workflows/cover_letter.py tests/dashboard/test_workflows_card.py
git commit -m "feat(dashboard): workflows use active candidate; drop for_candidate input"
```

---

## Task 12: Dashboard tabs scope to active candidate

**Files:**
- Modify: `scripts/dashboard/tabs/overview.py`, `tabs/pacing.py`, `tabs/applications.py`, `tabs/resumes.py`, `tabs/cover_letters.py`, `tabs/jds.py`
- Modify: `scripts/validators/jd_analyzer.py`
- Test: `tests/dashboard/test_app_overview_render.py`, add focused tests

Goal: every tab that currently runs an unscoped query gains a per-candidate scope. The JD analyzer's role-fit scoring uses the active candidate's `focus_areas`.

- [ ] **Step 1: Write a smoke test**

Add to `tests/dashboard/test_app_overview_render.py` (or a new file):

```python
def test_overview_counts_scope_to_active_candidate(isolated):
    from scripts.tracker.candidates import create_candidate, set_active_candidate
    from scripts.tracker.add import add_jd

    matthew = create_candidate("Matthew", "Gell", [], None, None)
    mathilda = create_candidate("Mathilda", "Gell", [], None, None)
    set_active_candidate(matthew)
    add_jd("manual", None, "Acme", "Eng", "...", {}, [], [])

    set_active_candidate(mathilda)
    # Importing the overview tab should now show 0 JDs for Mathilda.
    from scripts.dashboard.tabs.overview import _summary_counts
    counts = _summary_counts()
    assert counts["jds"] == 0

    set_active_candidate(matthew)
    counts = _summary_counts()
    assert counts["jds"] == 1
```

(If `_summary_counts` doesn't exist as a pure helper, extract it from the existing tab code so it's testable in isolation.)

- [ ] **Step 2: Run tests to verify they fail.**

- [ ] **Step 3: Update each tab to call `query.list_jds(...)` / `query.list_resumes(...)` etc with the default-active scope** (these now scope automatically per Task 7). The tabs need no candidate_id argument — they just call the unchanged-signature functions and trust default scoping.

Also: in `scripts/dashboard/tabs/pacing.py`, replace `profile.healthy_weekly_rate` reads with `get_active_candidate().healthy_weekly_rate`. Same pattern for `pacing_notes`.

- [ ] **Step 4: Update the JD analyzer**

In `scripts/validators/jd_analyzer.py`, replace `read_profile().focus_areas` with:

```python
from scripts.tracker.candidates import get_active_candidate
active = get_active_candidate()
focus = active.focus_areas if active else []
```

- [ ] **Step 5: Run tests to verify they pass.**

- [ ] **Step 6: Commit:**

```bash
git add scripts/dashboard/tabs scripts/validators/jd_analyzer.py tests/dashboard/test_app_overview_render.py
git commit -m "feat(dashboard): tabs + JD analyzer scope to active candidate"
```

---

## Task 13: Workflow docs

**Files:**
- Modify: `references/workflows/create.md`, `edit.md`, `tailor.md`, `cover-letter.md`

- [ ] **Step 1: For each doc**, replace the "Is this resume for someone else?" sub-step (added by Plan C) with:

> **Q. Confirm the active candidate.**
>
> Read the active candidate from `scripts.tracker.candidates.get_active_candidate()`. State the candidate's name explicitly: *"This interview will produce a resume for **{first} {last}**."* If the user expected someone else, instruct them to switch via the dashboard sidebar before proceeding. Do not proceed until the candidate is confirmed.

- [ ] **Step 2: Verify reference tests pass:**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/references -q
```

- [ ] **Step 3: Commit:**

```bash
git add references/workflows/create.md references/workflows/edit.md references/workflows/tailor.md references/workflows/cover-letter.md
git commit -m "docs(workflows): replace for_candidate prompt with active-candidate confirmation"
```

---

## Task 14: End-to-end smoke + version bump + CHANGELOG

**Files:**
- Create: `tests/test_smoke_two_candidate_session.py`
- Modify: `scripts/outputs/io.py` (`_SKILL_VERSION = "2.0.0"`)
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Write the smoke test**

```python
"""End-to-end: two candidates in one installation."""
from pathlib import Path

import pytest

from scripts.generators.resume_to_docx import render_resume_docx
from scripts.outputs.io import make_artifact_path, finalize_docx
from scripts.outputs.tagging import read_artifact_meta
from scripts.tracker.add import add_jd, add_resume_version
from scripts.tracker.candidates import create_candidate, set_active_candidate, get_active_candidate
from scripts.tracker.query import list_jds, list_artifacts_for_candidate


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    return tmp_path


def _data(name): return {
    "candidate_name": name,
    "candidate_contact_line": "Somewhere, AU",
    "summary": "Test.", "skills": "Test.",
    "experience": "Role", "education": "School",
}


def test_two_candidate_session_end_to_end(isolated):
    matthew = create_candidate("Matthew", "Gell", ["data eng"], 5, None)
    mathilda = create_candidate("Mathilda", "Gell", ["retail"], 2, None)

    # Matthew's path
    set_active_candidate(matthew)
    jd1 = add_jd("manual", None, "Acme", "Sr Eng", "...", {}, [], [])
    path1, meta1 = make_artifact_path(jd1, "resume")
    render_resume_docx(_data("Matthew Gell"), path1, template="hybrid")
    finalize_docx(path1, meta1)
    add_resume_version(
        file_path=str(path1), template="hybrid", focus_areas=[],
        tagged_jd_id=jd1, artifact_uid=meta1.artifact_uid,
    )

    # Mathilda's path
    set_active_candidate(mathilda)
    jd2 = add_jd("manual", None, "Big W", "Sales Assistant", "...", {}, [], [])
    path2, meta2 = make_artifact_path(jd2, "resume")
    render_resume_docx(_data("Mathilda Gell"), path2, template="hybrid")
    finalize_docx(path2, meta2)
    add_resume_version(
        file_path=str(path2), template="hybrid", focus_areas=[],
        tagged_jd_id=jd2, artifact_uid=meta2.artifact_uid,
    )

    # Filenames distinct
    assert "Matthew" in path1.name
    assert "Mathilda" in path2.name

    # DOCX custom-property round-trip
    m1 = read_artifact_meta(path1)
    m2 = read_artifact_meta(path2)
    assert m1.candidate_id == matthew
    assert m2.candidate_id == mathilda

    # Tab-scope behaviour
    set_active_candidate(matthew)
    assert {jd.company for jd in list_jds()} == {"Acme"}
    set_active_candidate(mathilda)
    assert {jd.company for jd in list_jds()} == {"Big W"}

    # Name lookup
    rows = list_artifacts_for_candidate("Mathilda Gell")
    assert len(rows) == 1
    assert rows[0].candidate_id == mathilda
```

- [ ] **Step 2: Run the test**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/test_smoke_two_candidate_session.py -v
```
Expected: PASS.

- [ ] **Step 3: Run the full suite**

```
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest -q
```
Expected: all green.

- [ ] **Step 4: Bump version**

In `scripts/outputs/io.py`, change `_SKILL_VERSION = "1.6.0"` to `_SKILL_VERSION = "2.0.0"`.

- [ ] **Step 5: Update CHANGELOG**

Add at the top of `CHANGELOG.md`:

```markdown
## v2.0.0 — 2026-XX-XX

### Breaking
- `Profile` dataclass is trimmed to `{active_candidate_id, log_handoffs}`. Per-user fields (first_name, last_name, focus_areas, healthy_weekly_rate, pacing_notes) now live on the `Candidate` row pointed to by `active_candidate_id`.
- `make_artifact_path` no longer raises `ProfileNameMissingError`; instead raises `NoActiveCandidateError` when no candidate is selected.

### Added
- `candidates` table (migration 0004) — first-class multi-candidate support.
- `scripts.tracker.candidates` module — CRUD + active-candidate accessor.
- Dashboard sidebar candidate picker; per-tab scoping; JD analyzer scoped to active candidate's focus areas.
- DOCX custom property `BrainsCandidateId` records the candidate row id.

### Migration
- Existing v1.5/1.6 installs are migrated automatically on first `open_db()` after upgrade:
  - The seed candidate is created from the legacy profile.json fields.
  - All existing resumes, cover letters, and JDs are linked to the seed candidate.
  - Rows with `for_candidate` populated (v1.6+) link to a per-name candidate created on first read.
  - profile.json is rewritten to the trimmed shape; legacy fields are dropped.
- The Approach-C `for_candidate` columns are RETAINED as a denormalized cache for data export and provenance.
```

- [ ] **Step 6: Commit**

```bash
git add scripts/outputs/io.py CHANGELOG.md tests/test_smoke_two_candidate_session.py
git commit -m "feat: v2.0.0 — first-class multi-candidate support (Approach B)"
```

---

## Acceptance Criteria

A. `pytest -q` is green across the full suite.

B. A v1.6 install upgraded to v2.0 opens cleanly: the seed candidate is created from `profile.json`, all existing JDs / resumes / cover letters are linked to it, and `profile.json` is rewritten without legacy fields.

C. Creating a second candidate ("Mathilda Gell") in the dashboard sidebar, switching active, and running `/brains-create` produces a DOCX with `BrainsCandidateId` matching her row id and `Mathilda_Gell_*` in the filename.

D. Switching the active candidate via the sidebar updates which JDs / resumes / cover letters appear in every tab; nothing leaks across candidates.

E. The JD analyzer's role-fit score uses the active candidate's focus areas, not a global profile field.

F. The pre-existing `V9MQZX` resume (Mathilda's resume in `c:\Brains_Resume_Skill\output\`) is re-tagged with `BrainsCandidateId` matching Mathilda's row id by running:

```python
from scripts.outputs.tagging import read_artifact_meta, write_artifact_meta
from scripts.tracker.candidates import find_or_create_by_name
meta = read_artifact_meta(path)
meta.candidate_id = find_or_create_by_name("Mathilda Gell")
write_artifact_meta(path, meta)
```

---

## Self-Review

**Spec coverage:** every architectural element from the memory entry maps to a task — candidates table (Task 1), Candidate dataclass (Task 2), CRUD module (Task 3), profile.json trim (Task 4), backfill (Task 5), candidate-aware inserts (Task 6), candidate-aware reads (Task 7), filename construction via candidate row (Task 8), DOCX BrainsCandidateId (Task 9), sidebar picker (Task 10), workflow cards (Task 11), per-tab scope + JD analyzer (Task 12), doc updates (Task 13), end-to-end + versioning (Task 14). No gap.

**Placeholder scan:** Tasks 9 and 11 reference "mirror Task X of Plan Y" — that is acceptable per the writing-plans skill's guidance on cross-references when the pattern is precisely defined in the referenced task. Task 9 specifies the exact additions (`BrainsCandidateId` vt:i4, "0"→None mapping); Task 11 specifies the exact four changes per file. No vague language remains.

**Type consistency:** `candidate_id: Optional[int] = None` is the field signature for the dataclass attribute. `candidate_id: int | None = None` is used in `make_artifact_path` and `ArtifactMeta` to match the existing module's style (`int | None`). `find_or_create_by_name(name: str) -> int` returns the candidate id consistently in both `_post_migration.py` and `candidates.py` (the production version is the candidates.py one; the post-migration variant is a private helper that does the same thing during backfill).

**Migration ordering risk:** Task 4 trims `Profile` BEFORE Task 5 wires the backfill hook. If a developer runs the suite after Task 4 but before Task 5, profile.json reads will discard legacy fields. The backfill hook reads `profile.json` directly via `json.loads()` (not through `read_profile`), so it survives the dataclass change. Confirmed this is safe.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-19-multi-candidate-approach-b.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, two-stage review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in the current session using executing-plans, batch execution with checkpoints.

Which approach?
