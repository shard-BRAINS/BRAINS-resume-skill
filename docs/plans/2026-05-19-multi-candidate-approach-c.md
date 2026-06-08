# Multi-Candidate Support — Approach C (`for_candidate` field) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional free-text `for_candidate` field that lets a single BRAINS Resume Skill installation generate and track resumes/cover letters for people other than the profile holder — without touching the single-profile model.

**Architecture:** A new `for_candidate TEXT` column on `resume_versions` and `cover_letters`. Carries through the data model as far as the DOCX custom properties so artifacts are self-describing. Where it is set, it supersedes the profile name for filename construction. Where it is `NULL`, behaviour is identical to today. Approach B (the eventual `candidates` table) backfills `candidate_id` from this string column row by row. See `docs/plans/2026-05-19-multi-candidate-approach-b.md` for that future migration.

**Tech Stack:** Python 3.14, SQLite (forward-only migrations), python-docx, reportlab, pytest, Streamlit.

**Out of scope:**

- PDF custom-property metadata. PDFs are derived; UIDs live in the DOCX. Separate ticket.
- Per-candidate focus areas / healthy rates. Those move with Approach B.
- Untracked-but-UID-stamped renderer convenience wrapper. Separate ticket.
- Dashboard candidate picker dropdown of historical names. The text input is enough for C.

**Pre-flight:**

- Confirm `c:\Brains_Resume_Skill\.venv` is the active venv: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -V` → `Python 3.14.x`.
- Run the full suite once before starting to capture a clean baseline: `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests -q` (from the skill root: `C:\Users\matth\.claude\skills\brains-resume`). All tests should pass on `main` before any work begins.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `scripts/tracker/migrations/0003_for_candidate.py` | **create** | Add `for_candidate TEXT` columns to `resume_versions` and `cover_letters` |
| `scripts/tracker/models.py` | modify | Add `for_candidate: Optional[str] = None` to `ResumeVersion` and `CoverLetter` dataclasses |
| `scripts/tracker/add.py` | modify | `add_resume_version` and `add_cover_letter` accept `for_candidate` and persist it |
| `scripts/tracker/query.py` | modify | Reading helpers return `for_candidate`; new `list_artifacts_for_candidate(name)` helper |
| `scripts/outputs/naming.py` | modify | Add `split_candidate_name(full_name: str) -> tuple[str, str]` helper |
| `scripts/outputs/tagging.py` | modify | Add `for_candidate` field to `ArtifactMeta`; persist as `BrainsForCandidate` custom property |
| `scripts/outputs/io.py` | modify | `make_artifact_path` accepts `for_candidate` override; uses it for filename construction when set |
| `scripts/dashboard/workflows/create.py` | modify | Add a "for candidate (optional)" text input; pass through to `make_artifact_path` and `ArtifactMeta` |
| `scripts/dashboard/workflows/edit.py` | modify | Same input as create.py for edit-flow handoff |
| `scripts/dashboard/workflows/tailor.py` | modify | Same input as create.py for tailor-flow handoff |
| `scripts/dashboard/workflows/cover_letter.py` | modify | Same input as create.py for cover-letter-flow handoff |
| `references/workflows/create.md` | modify | Document the new "Target Framing" sub-step that asks "Is this resume for someone other than the profile holder?" |
| `references/workflows/edit.md` | modify | Same documentation update |
| `references/workflows/tailor.md` | modify | Same documentation update |
| `tests/tracker/migrations/test_0003_for_candidate.py` | **create** | Migration applies cleanly; columns exist; NULL is valid; pre-existing rows survive |
| `tests/tracker/test_models.py` | modify | `for_candidate` is in dataclass; defaults to `None` |
| `tests/tracker/test_add.py` | modify | `add_resume_version` / `add_cover_letter` persist `for_candidate`; default is `NULL` |
| `tests/tracker/test_query.py` | modify | Reading helpers include `for_candidate`; new `list_artifacts_for_candidate` works |
| `tests/outputs/test_naming.py` | modify | `split_candidate_name` covers single, multi-word, hyphenated, whitespace, empty |
| `tests/outputs/test_tagging.py` | modify | `BrainsForCandidate` round-trips through DOCX custom properties; backwards-compatible with files that pre-date C |
| `tests/outputs/test_io.py` | modify | `make_artifact_path` with `for_candidate` produces a filename derived from the candidate, not the profile |
| `tests/test_smoke_multi_candidate.py` | **create** | End-to-end: profile-holder resume + Mathilda resume in the same library, both have distinct UIDs and correct filenames |

---

## Task 1: Migration 0003 — `for_candidate` columns

**Files:**

- Create: `scripts/tracker/migrations/0003_for_candidate.py`
- Test: `tests/tracker/migrations/test_0003_for_candidate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/tracker/migrations/test_0003_for_candidate.py
"""Tests for migration 0003 — for_candidate columns."""
import sqlite3

import pytest

from scripts.tracker.db import open_db


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


def test_resume_versions_has_for_candidate_column(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(resume_versions)")}
        assert "for_candidate" in cols
    finally:
        conn.close()


def test_cover_letters_has_for_candidate_column(isolated_db):
    conn = open_db()
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(cover_letters)")}
        assert "for_candidate" in cols
    finally:
        conn.close()


def test_for_candidate_is_nullable(isolated_db):
    """A pre-existing-style insert without for_candidate must still succeed."""
    conn = open_db()
    try:
        conn.execute(
            """INSERT INTO resume_versions
                 (template, focus_areas, created_at)
               VALUES ('chronological', '[]', '2026-05-19T00:00:00Z')"""
        )
        conn.commit()
        row = conn.execute(
            "SELECT for_candidate FROM resume_versions"
        ).fetchone()
        assert row[0] is None
    finally:
        conn.close()


def test_migration_recorded_in_migrations_table(isolated_db):
    conn = open_db()
    try:
        versions = [row[0] for row in conn.execute("SELECT version FROM migrations ORDER BY version")]
        assert 3 in versions
    finally:
        conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

```text
cd C:\Users\matth\.claude\skills\brains-resume
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/migrations/test_0003_for_candidate.py -v
```

Expected: 4 FAILs — column doesn't exist; migration 3 not recorded.

- [ ] **Step 3: Write the migration**

```python
# scripts/tracker/migrations/0003_for_candidate.py
"""Migration 0003 — for_candidate text column on resume_versions and cover_letters.

Forward-only addition of two nullable text columns that record who the artifact
is FOR when that person is not the profile holder. Null preserves pre-0003
behaviour (artifact belongs to the profile holder).

See docs/plans/2026-05-19-multi-candidate-approach-c.md.
"""
import sqlite3


SCHEMA_SQL = """
ALTER TABLE resume_versions ADD COLUMN for_candidate TEXT;
ALTER TABLE cover_letters   ADD COLUMN for_candidate TEXT;
"""


def apply(conn: sqlite3.Connection) -> None:
    """Apply the for_candidate column additions."""
    conn.executescript(SCHEMA_SQL)
```

- [ ] **Step 4: Run test to verify it passes**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/migrations/test_0003_for_candidate.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Run the full tracker test suite to check for regressions**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker -q
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add scripts/tracker/migrations/0003_for_candidate.py tests/tracker/migrations/test_0003_for_candidate.py
git commit -m "feat(tracker): migration 0003 adds for_candidate columns"
```

---

## Task 2: Extend dataclasses

**Files:**

- Modify: `scripts/tracker/models.py:38-49` (`ResumeVersion`) and `:52-62` (`CoverLetter`)
- Test: `tests/tracker/test_models.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/tracker/test_models.py`:

```python
def test_resume_version_has_for_candidate_default_none():
    from scripts.tracker.models import ResumeVersion
    rv = ResumeVersion(
        id=1, file_path=None, template="chronological", focus_areas=[],
        parent_id=None, tagged_jd_id=None,
        created_at="2026-05-19T00:00:00Z", archived_at=None,
    )
    assert rv.for_candidate is None


def test_resume_version_accepts_for_candidate():
    from scripts.tracker.models import ResumeVersion
    rv = ResumeVersion(
        id=1, file_path=None, template="chronological", focus_areas=[],
        parent_id=None, tagged_jd_id=None,
        created_at="2026-05-19T00:00:00Z", archived_at=None,
        for_candidate="Mathilda Gell",
    )
    assert rv.for_candidate == "Mathilda Gell"


def test_cover_letter_has_for_candidate_default_none():
    from scripts.tracker.models import CoverLetter
    cl = CoverLetter(
        id=1, file_path=None, resume_version_id=1, jd_id=1,
        template="formal-business",
        created_at="2026-05-19T00:00:00Z", archived_at=None,
    )
    assert cl.for_candidate is None
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_models.py -v -k for_candidate
```

Expected: 3 FAILs — AttributeError or unexpected-keyword-argument.

- [ ] **Step 3: Update the dataclasses**

In `scripts/tracker/models.py`, edit `ResumeVersion` and `CoverLetter`:

```python
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
    artifact_uid: Optional[str] = None
    parent_uid: Optional[str] = None
    for_candidate: Optional[str] = None


@dataclass
class CoverLetter:
    id: Optional[int]
    file_path: Optional[str]
    resume_version_id: int
    jd_id: int
    template: str
    created_at: str
    archived_at: Optional[str]
    artifact_uid: Optional[str] = None
    parent_uid: Optional[str] = None
    for_candidate: Optional[str] = None
```

- [ ] **Step 4: Run test to verify it passes**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_models.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/tracker/models.py tests/tracker/test_models.py
git commit -m "feat(tracker): for_candidate field on ResumeVersion + CoverLetter dataclasses"
```

---

## Task 3: Persist `for_candidate` through `add_resume_version` / `add_cover_letter`

**Files:**

- Modify: `scripts/tracker/add.py:18-51` (`add_resume_version`) and `:95-119` (`add_cover_letter`)
- Test: `tests/tracker/test_add.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/tracker/test_add.py`:

```python
def test_add_resume_version_persists_for_candidate(isolated):
    from scripts.tracker.add import add_resume_version
    from scripts.tracker.db import open_db

    rv_id = add_resume_version(
        file_path=None, template="hybrid", focus_areas=[],
        for_candidate="Mathilda Gell",
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT for_candidate FROM resume_versions WHERE id=?", (rv_id,),
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == "Mathilda Gell"


def test_add_resume_version_defaults_for_candidate_to_null(isolated):
    from scripts.tracker.add import add_resume_version
    from scripts.tracker.db import open_db

    rv_id = add_resume_version(
        file_path=None, template="hybrid", focus_areas=[],
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT for_candidate FROM resume_versions WHERE id=?", (rv_id,),
        ).fetchone()
    finally:
        conn.close()
    assert row[0] is None


def test_add_cover_letter_persists_for_candidate(isolated):
    from scripts.tracker.add import add_resume_version, add_jd, add_cover_letter
    from scripts.tracker.db import open_db

    jd_id = add_jd("manual", None, "Acme", "Eng", "...", {}, [], [])
    rv_id = add_resume_version(None, "chronological", [])
    cl_id = add_cover_letter(
        file_path=None, resume_version_id=rv_id, jd_id=jd_id,
        template="formal-business", for_candidate="Mathilda Gell",
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT for_candidate FROM cover_letters WHERE id=?", (cl_id,),
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == "Mathilda Gell"
```

(Reuses the `isolated` fixture already defined in `tests/tracker/test_add.py`.)

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_add.py -v -k for_candidate
```

Expected: 3 FAILs — unexpected-keyword-argument.

- [ ] **Step 3: Update `add_resume_version`**

In `scripts/tracker/add.py`, replace `add_resume_version`:

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
) -> int:
    """Insert a resume_versions row, return the new id."""
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO resume_versions
                (file_path, template, focus_areas, parent_id, tagged_jd_id,
                 created_at, artifact_uid, parent_uid, for_candidate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_path,
                template,
                json.dumps(focus_areas),
                parent_id,
                tagged_jd_id,
                _now_iso(),
                artifact_uid,
                parent_uid,
                for_candidate,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
```

- [ ] **Step 4: Update `add_cover_letter`**

In `scripts/tracker/add.py`, replace `add_cover_letter`:

```python
def add_cover_letter(
    file_path: Optional[str],
    resume_version_id: int,
    jd_id: int,
    template: str,
    artifact_uid: Optional[str] = None,
    parent_uid: Optional[str] = None,
    for_candidate: Optional[str] = None,
) -> int:
    """Insert a cover_letters row, return the new id."""
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO cover_letters
                (file_path, resume_version_id, jd_id, template, created_at,
                 artifact_uid, parent_uid, for_candidate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (file_path, resume_version_id, jd_id, template, _now_iso(),
             artifact_uid, parent_uid, for_candidate),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
```

- [ ] **Step 5: Run test to verify it passes**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_add.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/tracker/add.py tests/tracker/test_add.py
git commit -m "feat(tracker): add_resume_version + add_cover_letter accept for_candidate"
```

---

## Task 4: Read-side support in `query.py`

**Files:**

- Modify: `scripts/tracker/query.py`
- Test: `tests/tracker/test_query.py`

Goal: `get_artifact_by_uid` and any helpers that hydrate `ResumeVersion` / `CoverLetter` populate `for_candidate`. Add a new `list_artifacts_for_candidate(name)` helper.

- [ ] **Step 1: Inspect the current query module**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_query.py -q
```

Expected: all PASS currently. Open `scripts/tracker/query.py` and identify every place that constructs `ResumeVersion(...)` or `CoverLetter(...)`. Each constructor needs `for_candidate=` added to its kwargs and the corresponding column added to its `SELECT` list.

- [ ] **Step 2: Write failing tests**

Append to `tests/tracker/test_query.py`:

```python
def test_get_artifact_by_uid_returns_for_candidate(isolated):
    from scripts.tracker.add import add_resume_version
    from scripts.tracker.query import get_artifact_by_uid

    rv_id = add_resume_version(
        None, "hybrid", [], artifact_uid="ABC123",
        for_candidate="Mathilda Gell",
    )
    row = get_artifact_by_uid("ABC123")
    assert row is not None
    assert row.for_candidate == "Mathilda Gell"


def test_list_artifacts_for_candidate(isolated):
    from scripts.tracker.add import add_resume_version
    from scripts.tracker.query import list_artifacts_for_candidate

    add_resume_version(None, "hybrid", [], for_candidate="Mathilda Gell")
    add_resume_version(None, "chronological", [], for_candidate="Mathilda Gell")
    add_resume_version(None, "chronological", [])  # profile holder, NULL
    rows = list_artifacts_for_candidate("Mathilda Gell")
    assert len(rows) == 2
    assert all(r.for_candidate == "Mathilda Gell" for r in rows)


def test_list_artifacts_for_candidate_empty_when_no_match(isolated):
    from scripts.tracker.query import list_artifacts_for_candidate
    assert list_artifacts_for_candidate("Nobody") == []
```

- [ ] **Step 3: Run tests to verify they fail**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_query.py -v -k "for_candidate or list_artifacts"
```

Expected: 3 FAILs — `list_artifacts_for_candidate` undefined; `for_candidate` not on returned dataclass.

- [ ] **Step 4: Update `get_artifact_by_uid` and add the list helper**

In `scripts/tracker/query.py`:

a. For every `SELECT` that hydrates a `ResumeVersion`, add `for_candidate` to the column list and pass it as `for_candidate=row[N]` to the dataclass constructor.

b. Same for every `SELECT` that hydrates a `CoverLetter`.

c. Append at the bottom of the file:

```python
def list_artifacts_for_candidate(name: str) -> list:
    """Return all resume_versions + cover_letters whose for_candidate matches name."""
    from scripts.tracker.models import ResumeVersion, CoverLetter
    conn = open_db()
    try:
        results = []
        for row in conn.execute(
            """SELECT id, file_path, template, focus_areas, parent_id, tagged_jd_id,
                      created_at, archived_at, artifact_uid, parent_uid, for_candidate
               FROM resume_versions WHERE for_candidate = ? AND archived_at IS NULL
               ORDER BY created_at DESC""",
            (name,),
        ):
            import json as _json
            results.append(ResumeVersion(
                id=row[0], file_path=row[1], template=row[2],
                focus_areas=_json.loads(row[3] or "[]"),
                parent_id=row[4], tagged_jd_id=row[5],
                created_at=row[6], archived_at=row[7],
                artifact_uid=row[8], parent_uid=row[9],
                for_candidate=row[10],
            ))
        for row in conn.execute(
            """SELECT id, file_path, resume_version_id, jd_id, template,
                      created_at, archived_at, artifact_uid, parent_uid, for_candidate
               FROM cover_letters WHERE for_candidate = ? AND archived_at IS NULL
               ORDER BY created_at DESC""",
            (name,),
        ):
            results.append(CoverLetter(
                id=row[0], file_path=row[1], resume_version_id=row[2],
                jd_id=row[3], template=row[4],
                created_at=row[5], archived_at=row[6],
                artifact_uid=row[7], parent_uid=row[8],
                for_candidate=row[9],
            ))
        return results
    finally:
        conn.close()
```

- [ ] **Step 5: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker -v
```

Expected: all green, including any pre-existing query tests.

- [ ] **Step 6: Commit**

```bash
git add scripts/tracker/query.py tests/tracker/test_query.py
git commit -m "feat(tracker): query helpers expose for_candidate + list_artifacts_for_candidate"
```

---

## Task 5: `split_candidate_name` helper

**Files:**

- Modify: `scripts/outputs/naming.py`
- Test: `tests/outputs/test_naming.py`

Goal: turn a free-text candidate name like `"Mathilda Gell"` or `"Anne-Marie O'Brien"` or `"Cher"` into a `(first, last)` tuple usable by `artifact_filename`. Single-word names get `last=""`.

- [ ] **Step 1: Write the failing test**

Append to `tests/outputs/test_naming.py`:

```python
def test_split_candidate_name_two_tokens():
    from scripts.outputs.naming import split_candidate_name
    assert split_candidate_name("Mathilda Gell") == ("Mathilda", "Gell")


def test_split_candidate_name_three_or_more_tokens_joins_middle_into_first():
    from scripts.outputs.naming import split_candidate_name
    # First name takes all but the last token. Keeps middle names with the given name.
    assert split_candidate_name("Anne Marie O'Brien") == ("Anne Marie", "O'Brien")


def test_split_candidate_name_hyphenated_surname_preserved():
    from scripts.outputs.naming import split_candidate_name
    assert split_candidate_name("Sam Smith-Jones") == ("Sam", "Smith-Jones")


def test_split_candidate_name_single_token_returns_empty_last():
    from scripts.outputs.naming import split_candidate_name
    assert split_candidate_name("Cher") == ("Cher", "")


def test_split_candidate_name_collapses_internal_whitespace():
    from scripts.outputs.naming import split_candidate_name
    assert split_candidate_name("Mathilda   Gell") == ("Mathilda", "Gell")


def test_split_candidate_name_empty_returns_empty_pair():
    from scripts.outputs.naming import split_candidate_name
    assert split_candidate_name("") == ("", "")
    assert split_candidate_name("   ") == ("", "")
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/outputs/test_naming.py -v -k split_candidate
```

Expected: 6 FAILs — ImportError.

- [ ] **Step 3: Add the helper**

Append to `scripts/outputs/naming.py`:

```python
def split_candidate_name(full_name: str) -> tuple[str, str]:
    """Split a free-text candidate name into (first, last) for filename construction.

    - Two or more tokens: last token is the surname, everything before is the given-name part.
    - Single token: returned as first with empty last.
    - Empty / whitespace-only: returned as ("", "").
    - Internal whitespace runs collapse to single spaces.
    """
    tokens = (full_name or "").split()
    if not tokens:
        return ("", "")
    if len(tokens) == 1:
        return (tokens[0], "")
    return (" ".join(tokens[:-1]), tokens[-1])
```

- [ ] **Step 4: Run test to verify it passes**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/outputs/test_naming.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/outputs/naming.py tests/outputs/test_naming.py
git commit -m "feat(outputs): split_candidate_name helper for free-text candidate names"
```

---

## Task 6: `BrainsForCandidate` custom property on the DOCX

**Files:**

- Modify: `scripts/outputs/tagging.py:56-79` (`ArtifactMeta`, `_meta_to_property_dict`) and `:195-219` (`read_artifact_meta`)
- Test: `tests/outputs/test_tagging.py`

Goal: `ArtifactMeta` gains `for_candidate: str | None = None`. The DOCX persists it as `BrainsForCandidate` (vt:lpwstr). The reader round-trips empty-string back to `None`. Files written by pre-C versions of the skill read as `for_candidate=None`.

- [ ] **Step 1: Write the failing test**

Append to `tests/outputs/test_tagging.py`:

```python
def test_artifact_meta_has_for_candidate_default_none():
    from scripts.outputs.tagging import ArtifactMeta
    m = ArtifactMeta(
        artifact_uid="ABC123", artifact_kind="resume",
        jd_id=None, parent_uid=None,
        created_at="2026-05-19T00:00:00Z", skill_version="1.5.0",
    )
    assert m.for_candidate is None


def test_for_candidate_roundtrips_through_docx(tmp_path):
    """Write a DOCX with for_candidate set, read it back."""
    from docx import Document
    from scripts.outputs.tagging import ArtifactMeta, write_artifact_meta, read_artifact_meta

    docx_path = tmp_path / "test.docx"
    Document().save(str(docx_path))

    meta = ArtifactMeta(
        artifact_uid="ABC123", artifact_kind="resume",
        jd_id=None, parent_uid=None,
        created_at="2026-05-19T00:00:00Z", skill_version="1.5.0",
        for_candidate="Mathilda Gell",
    )
    write_artifact_meta(docx_path, meta)
    roundtrip = read_artifact_meta(docx_path)
    assert roundtrip.for_candidate == "Mathilda Gell"


def test_for_candidate_absent_reads_as_none(tmp_path):
    """A DOCX written without for_candidate must read as None (forward-compat)."""
    from docx import Document
    from scripts.outputs.tagging import ArtifactMeta, write_artifact_meta, read_artifact_meta

    docx_path = tmp_path / "test.docx"
    Document().save(str(docx_path))

    meta = ArtifactMeta(
        artifact_uid="ABC123", artifact_kind="resume",
        jd_id=None, parent_uid=None,
        created_at="2026-05-19T00:00:00Z", skill_version="1.5.0",
        # for_candidate omitted
    )
    write_artifact_meta(docx_path, meta)
    roundtrip = read_artifact_meta(docx_path)
    assert roundtrip.for_candidate is None
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/outputs/test_tagging.py -v -k for_candidate
```

Expected: 3 FAILs.

- [ ] **Step 3: Extend `ArtifactMeta`**

In `scripts/outputs/tagging.py`, replace the `ArtifactMeta` dataclass:

```python
@dataclass
class ArtifactMeta:
    artifact_uid: str
    artifact_kind: Literal["resume", "cover-letter"]
    jd_id: int | None
    parent_uid: str | None
    created_at: str
    skill_version: str
    for_candidate: str | None = None
```

- [ ] **Step 4: Extend `_meta_to_property_dict`**

Replace `_meta_to_property_dict` in the same file:

```python
def _meta_to_property_dict(meta: ArtifactMeta) -> dict[str, tuple[str, str]]:
    """Convert ArtifactMeta into {name: (vt_type, string_value)} entries."""
    return {
        "BrainsArtifactId":    ("lpwstr", meta.artifact_uid),
        "BrainsArtifactKind":  ("lpwstr", meta.artifact_kind),
        "BrainsJDId":          ("i4",     str(meta.jd_id if meta.jd_id is not None else 0)),
        "BrainsParentId":      ("lpwstr", meta.parent_uid if meta.parent_uid is not None else ""),
        "BrainsCreatedAt":     ("lpwstr", meta.created_at),
        "BrainsSkillVersion":  ("lpwstr", meta.skill_version),
        "BrainsForCandidate":  ("lpwstr", meta.for_candidate if meta.for_candidate is not None else ""),
    }
```

- [ ] **Step 5: Extend `read_artifact_meta`**

Replace `read_artifact_meta` in the same file:

```python
def read_artifact_meta(docx_path: Path | str) -> ArtifactMeta | None:
    """Read the artifact metadata from a DOCX. Returns None if no
    BrainsArtifactId custom property is present.

    The reader converts placeholder values back to None:
    - BrainsJDId == "0" or absent -> jd_id = None
    - BrainsParentId == "" or absent -> parent_uid = None
    - BrainsForCandidate == "" or absent -> for_candidate = None
    """
    props = _read_custom_properties_raw(docx_path)
    if "BrainsArtifactId" not in props:
        return None
    jd_id_raw = props.get("BrainsJDId", "0")
    try:
        jd_id_int = int(jd_id_raw)
    except (ValueError, TypeError):
        jd_id_int = 0
    parent_raw = props.get("BrainsParentId", "")
    for_candidate_raw = props.get("BrainsForCandidate", "")
    return ArtifactMeta(
        artifact_uid=props["BrainsArtifactId"],
        artifact_kind=props.get("BrainsArtifactKind", ""),
        jd_id=jd_id_int if jd_id_int else None,
        parent_uid=parent_raw if parent_raw else None,
        created_at=props.get("BrainsCreatedAt", ""),
        skill_version=props.get("BrainsSkillVersion", ""),
        for_candidate=for_candidate_raw if for_candidate_raw else None,
    )
```

- [ ] **Step 6: Run test to verify it passes**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/outputs/test_tagging.py -v
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/outputs/tagging.py tests/outputs/test_tagging.py
git commit -m "feat(outputs): ArtifactMeta + DOCX gain BrainsForCandidate custom property"
```

---

## Task 7: `make_artifact_path` accepts `for_candidate` override

**Files:**

- Modify: `scripts/outputs/io.py:101-148` (`make_artifact_path`)
- Test: `tests/outputs/test_io.py`

Goal: when `for_candidate` is passed, the filename is derived from the candidate name (via `split_candidate_name`), and the returned `ArtifactMeta` carries `for_candidate=<name>`. When `for_candidate` is `None`, behaviour is unchanged.

- [ ] **Step 1: Write the failing test**

Append to `tests/outputs/test_io.py`:

```python
def test_make_artifact_path_for_candidate_uses_candidate_name_in_filename(isolated):
    """Override candidate name supersedes profile name for filename construction."""
    from scripts.outputs.io import make_artifact_path
    from scripts.tracker.profile import write_profile
    from scripts.tracker.models import Profile
    from scripts.tracker.add import add_jd

    write_profile(Profile(first_name="Matthew", last_name="Gell"))
    jd_id = add_jd("manual", None, "Acme", "Sales Assistant", "...", {}, [], [])

    path, meta = make_artifact_path(
        jd_id, "resume", parent_uid=None,
        for_candidate="Mathilda Gell",
    )
    assert "Mathilda" in path.name
    assert "Gell" in path.name
    assert "Matthew" not in path.name
    assert meta.for_candidate == "Mathilda Gell"


def test_make_artifact_path_no_override_uses_profile_name(isolated):
    """No override: behaviour is unchanged from pre-C."""
    from scripts.outputs.io import make_artifact_path
    from scripts.tracker.profile import write_profile
    from scripts.tracker.models import Profile
    from scripts.tracker.add import add_jd

    write_profile(Profile(first_name="Matthew", last_name="Gell"))
    jd_id = add_jd("manual", None, "Acme", "Senior Eng", "...", {}, [], [])

    path, meta = make_artifact_path(jd_id, "resume", parent_uid=None)
    assert "Matthew" in path.name
    assert "Gell" in path.name
    assert meta.for_candidate is None


def test_make_artifact_path_single_token_candidate_name(isolated):
    """Single-token candidate names (Cher, Madonna) still produce a valid filename."""
    from scripts.outputs.io import make_artifact_path
    from scripts.tracker.profile import write_profile
    from scripts.tracker.models import Profile
    from scripts.tracker.add import add_jd

    write_profile(Profile(first_name="Matthew", last_name="Gell"))
    jd_id = add_jd("manual", None, "Acme", "Eng", "...", {}, [], [])

    path, meta = make_artifact_path(
        jd_id, "resume", parent_uid=None, for_candidate="Cher",
    )
    assert "Cher" in path.name
    assert meta.for_candidate == "Cher"
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/outputs/test_io.py -v -k for_candidate
```

Expected: 3 FAILs — unexpected-keyword-argument and missing assertion.

- [ ] **Step 3: Update `make_artifact_path`**

Replace `make_artifact_path` in `scripts/outputs/io.py`:

```python
def make_artifact_path(
    jd_id: int,
    kind: Literal["resume", "cover-letter"],
    parent_uid: str | None = None,
    for_candidate: str | None = None,
) -> tuple[Path, ArtifactMeta]:
    """Reserve a new artifact path + UID within the JD folder.

    Does NOT write the tracker row (the workflow does that after the
    generator succeeds). The caller passes the returned ArtifactMeta
    into the generator or to finalize_docx after save.

    If `for_candidate` is provided, it supersedes the profile name for
    filename construction and is stamped onto the returned ArtifactMeta
    so the DOCX records who the artifact is FOR. When None, the profile
    name is used (pre-C behaviour).

    Raises ProfileNameMissingError if first_name or last_name is unset
    AND no for_candidate override is provided.
    """
    from scripts.outputs.naming import split_candidate_name

    if for_candidate:
        first_name, last_name = split_candidate_name(for_candidate)
    else:
        profile = read_profile()
        if not profile.first_name or not profile.last_name:
            raise ProfileNameMissingError(
                "Profile is missing first_name or last_name. "
                "Set them in the dashboard sidebar, or pass for_candidate explicitly."
            )
        first_name, last_name = profile.first_name, profile.last_name

    folder = ensure_jd_folder(jd_id)
    today = _date.today()
    for _ in range(_MAX_UID_RETRIES):
        uid = new_uid()
        if find_artifact_by_uid(uid) is None:
            break
    else:
        raise UIDCollisionError(
            f"5 consecutive UID generations all collided. "
            f"Database may be saturated; investigate."
        )
    filename = artifact_filename(
        first_name=first_name,
        last_name=last_name,
        kind=kind,
        created_date=today,
        uid=uid,
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
    )
    return path, meta
```

- [ ] **Step 4: Run test to verify it passes**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/outputs/test_io.py -v
```

Expected: all PASS, including pre-existing tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/outputs/io.py tests/outputs/test_io.py
git commit -m "feat(outputs): make_artifact_path accepts for_candidate override"
```

---

## Task 8: Dashboard workflow cards surface the candidate input

**Files:**

- Modify: `scripts/dashboard/workflows/create.py`
- Test: `tests/dashboard/test_workflows_card.py` (extend if it covers create; otherwise add a new dashboard test)

Goal: each workflow card that calls `make_artifact_path` gains a `st.text_input("For candidate (optional — leave blank for yourself)")` that pipes its value into `make_artifact_path(..., for_candidate=...)` and the `ArtifactMeta`.

- [ ] **Step 1: Write a smoke test**

Add to `tests/dashboard/test_workflows_card.py`:

```python
def test_create_workflow_passes_for_candidate_to_artifact_meta(monkeypatch, tmp_path):
    """When the user fills the for_candidate text input, it lands on ArtifactMeta."""
    from scripts.dashboard.workflows import create as create_mod
    from scripts.outputs.tagging import ArtifactMeta

    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))

    from scripts.tracker.profile import write_profile
    from scripts.tracker.models import Profile
    write_profile(Profile(first_name="Matthew", last_name="Gell"))

    captured = {}
    def fake_make_artifact_path(jd_id, kind, parent_uid=None, for_candidate=None):
        captured["for_candidate"] = for_candidate
        path = tmp_path / "fake.docx"
        meta = ArtifactMeta(
            artifact_uid="ABC123", artifact_kind=kind,
            jd_id=jd_id, parent_uid=parent_uid,
            created_at="2026-05-19T00:00:00Z", skill_version="1.5.0",
            for_candidate=for_candidate,
        )
        return path, meta

    monkeypatch.setattr(create_mod, "make_artifact_path", fake_make_artifact_path)
    # Invoke whatever helper the card uses to resolve a target; assertion below.
    # See create.py:_resolve_target — a unit helper extracted in Step 3.
    target_path, meta = create_mod._resolve_target(
        jd_id=1, for_candidate="Mathilda Gell",
    )
    assert captured["for_candidate"] == "Mathilda Gell"
    assert meta.for_candidate == "Mathilda Gell"
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/test_workflows_card.py -v -k for_candidate
```

Expected: FAIL — `create_mod._resolve_target` doesn't exist.

- [ ] **Step 3: Refactor `create.py` to extract `_resolve_target` and wire the text input**

Replace `scripts/dashboard/workflows/create.py` body with:

```python
"""/brains-create — interactive interview to build a resume from scratch."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st

from scripts.dashboard.workflows._card import handoff_button
from scripts.outputs.io import (
    make_artifact_path,
    get_outputs_root,
    ProfileNameMissingError,
)
from scripts.outputs.naming import artifact_filename, new_uid, split_candidate_name
from scripts.outputs.tagging import ArtifactMeta
from scripts.tracker.profile import read_profile


def _resolve_target(
    jd_id: int,
    for_candidate: Optional[str] = None,
) -> Tuple[Path, ArtifactMeta]:
    """Compute the output path + ArtifactMeta for a /brains-create run.

    If jd_id > 0: anchor to that JD's folder via make_artifact_path.
    If jd_id == 0: write to the _library directory using profile name (or
    for_candidate override, when provided).
    Raises ProfileNameMissingError when no candidate name is available.
    """
    for_candidate = (for_candidate or "").strip() or None

    if jd_id:
        return make_artifact_path(
            int(jd_id), "resume",
            parent_uid=None,
            for_candidate=for_candidate,
        )

    if for_candidate:
        first_name, last_name = split_candidate_name(for_candidate)
    else:
        profile = read_profile()
        if not profile.first_name or not profile.last_name:
            raise ProfileNameMissingError(
                "Profile is missing first_name or last_name. "
                "Set them in the sidebar, or fill 'For candidate' above."
            )
        first_name, last_name = profile.first_name, profile.last_name

    library = get_outputs_root() / "_library"
    library.mkdir(parents=True, exist_ok=True)
    uid = new_uid()
    target_path = library / artifact_filename(
        first_name=first_name, last_name=last_name,
        kind="resume", created_date=date.today(), uid=uid,
    )
    meta = ArtifactMeta(
        artifact_uid=uid, artifact_kind="resume",
        jd_id=None, parent_uid=None,
        created_at=datetime.utcnow().isoformat() + "Z",
        skill_version="1.5.0",
        for_candidate=for_candidate,
    )
    return target_path, meta


def render(file_path: Optional[Path] = None, key_prefix: str = "create") -> None:
    st.markdown("**Create a resume from scratch.**")
    st.caption("Claude Code walks through a structured interview — pace yourself, use breaks freely.")
    jd_id = st.number_input(
        "JD id (optional — leave at 0 to save in _library)", min_value=0, step=1,
        key=f"{key_prefix}_jd_id",
    )
    for_candidate = st.text_input(
        "For candidate (optional — leave blank for yourself)",
        key=f"{key_prefix}_for_candidate",
        help="If you're building a resume for someone else, enter their name here.",
    )
    try:
        target_path, meta = _resolve_target(int(jd_id), for_candidate)
    except ProfileNameMissingError as e:
        st.error(str(e))
        return
    except Exception as exc:
        st.warning(f"Could not resolve output path: {exc}")
        return

    st.caption(f"Output will land at: `{target_path}`")
    handoff_button(
        "create",
        [str(target_path), meta.artifact_uid],
        note=(
            "Open Claude Code; paste this command to start the interview. "
            "After save, call `scripts.outputs.io.finalize_docx(target_path, meta)` "
            "and register the new resume in the tracker with `for_candidate` set "
            "to the same value if provided."
        ),
        key=f"{key_prefix}_btn",
    )
```

- [ ] **Step 4: Run test to verify it passes**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/test_workflows_card.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/workflows/create.py tests/dashboard/test_workflows_card.py
git commit -m "feat(dashboard): /brains-create surfaces for_candidate text input"
```

---

## Task 9: Repeat Task 8 pattern for edit, tailor, cover_letter

**Files:**

- Modify: `scripts/dashboard/workflows/edit.py`, `scripts/dashboard/workflows/tailor.py`, `scripts/dashboard/workflows/cover_letter.py`
- Test: extend `tests/dashboard/test_workflows_card.py`

For each of these three workflow files, perform the same refactor pattern as Task 8: extract a `_resolve_target` helper, add a `st.text_input("For candidate (optional)")`, pipe through to `make_artifact_path(..., for_candidate=...)` and `ArtifactMeta(for_candidate=...)`.

- [ ] **Step 1: Write the failing test (one per workflow)**

Append three smoke tests to `tests/dashboard/test_workflows_card.py`, mirroring the create.py test from Task 8, but for `edit`, `tailor`, and `cover_letter` modules. Each asserts `captured["for_candidate"] == "Mathilda Gell"` and `meta.for_candidate == "Mathilda Gell"`.

- [ ] **Step 2: Run tests to verify they fail**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/test_workflows_card.py -v
```

Expected: 3 FAILs.

- [ ] **Step 3: Apply the same refactor to each workflow file**

For each of `edit.py`, `tailor.py`, `cover_letter.py`:

a. Add the import `from scripts.outputs.naming import split_candidate_name` (alongside existing imports).
b. Extract a `_resolve_target(...)` helper using the same pattern as Task 8 Step 3, adapted for that workflow's existing logic (e.g. for `cover_letter.py`, the artifact kind is `"cover-letter"` not `"resume"`, and `tagged_jd_id` may not apply; check the existing function to identify the exact path resolution it currently does and add `for_candidate` as a new optional argument that overrides the profile name in the same places).
c. In the `render(...)` function, add `for_candidate = st.text_input("For candidate (optional — leave blank for yourself)", key=f"{key_prefix}_for_candidate")` immediately after the jd_id input.
d. Pass `for_candidate=for_candidate` into `_resolve_target(...)`.
e. Update the `handoff_button` note to mention setting `for_candidate` in the tracker insert.

- [ ] **Step 4: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/test_workflows_card.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/workflows/edit.py scripts/dashboard/workflows/tailor.py scripts/dashboard/workflows/cover_letter.py tests/dashboard/test_workflows_card.py
git commit -m "feat(dashboard): edit/tailor/cover-letter surface for_candidate text input"
```

---

## Task 10: Update workflow docs to mention `for_candidate`

**Files:**

- Modify: `references/workflows/create.md`, `references/workflows/edit.md`, `references/workflows/tailor.md`, `references/workflows/cover-letter.md`

Each workflow doc needs an additional Target-Framing sub-step:

> **Q. Is this resume for the profile holder, or for someone else?**
>
> If for someone else, capture their full name (e.g., "Mathilda Gell"). The interview otherwise proceeds normally — every reference to "the user" in subsequent sections applies to the named candidate. Pass the candidate name into the generator path (`make_artifact_path(..., for_candidate="<name>")`) and into the tracker insert (`add_resume_version(..., for_candidate="<name>")`) so the DOCX and the tracker row both record who the artifact is FOR. When the workflow runs for the profile holder, leave `for_candidate` unset.

- [ ] **Step 1: Update `references/workflows/create.md`**

In the "Target Framing" section, add the bullet above after the disclosure-stance question.

- [ ] **Step 2: Update `references/workflows/edit.md`**

Same edit pattern. Confirm that "the user's veto principle" language is preserved — the override is additive, not a replacement.

- [ ] **Step 3: Update `references/workflows/tailor.md`**

Same edit pattern.

- [ ] **Step 4: Update `references/workflows/cover-letter.md`**

Same edit pattern, framed for cover letters (the cover letter is for the same candidate as the parent resume — surface a confirmation step rather than a fresh input).

- [ ] **Step 5: Verify reference tests still pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/references -q
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add references/workflows/create.md references/workflows/edit.md references/workflows/tailor.md references/workflows/cover-letter.md
git commit -m "docs(workflows): document for_candidate step in interview flow"
```

---

## Task 11: End-to-end smoke test

**Files:**

- Create: `tests/test_smoke_multi_candidate.py`

Goal: one test that runs the full flow end-to-end — render a resume DOCX for the profile holder, render a second resume DOCX with `for_candidate="Mathilda Gell"`, assert both files exist with the expected filenames, both have distinct UIDs in custom properties, and the second has `BrainsForCandidate=Mathilda Gell` while the first has an empty string for that property.

- [ ] **Step 1: Write the test**

Create `tests/test_smoke_multi_candidate.py`:

```python
"""Smoke test: multi-candidate output flow (Approach C)."""
from datetime import datetime
from pathlib import Path

import pytest

from scripts.generators.resume_to_docx import render_resume_docx
from scripts.outputs.io import make_artifact_path, finalize_docx
from scripts.outputs.tagging import read_artifact_meta
from scripts.tracker.add import add_jd, add_resume_version
from scripts.tracker.profile import write_profile
from scripts.tracker.models import Profile


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    write_profile(Profile(first_name="Matthew", last_name="Gell"))
    return tmp_path


def _minimal_data(name: str) -> dict:
    return {
        "candidate_name": name,
        "candidate_contact_line": "Somewhere, AU",
        "summary": "Test summary.",
        "skills": "Test skills.",
        "experience": "Role 1\nRole 2",
        "education": "School A",
    }


def test_two_candidates_one_installation(isolated):
    """Same installation produces UID-tagged DOCX for two different candidates."""
    jd_id = add_jd("manual", None, "Acme", "Sales Assistant", "...", {}, [], [])

    # Profile holder
    self_path, self_meta = make_artifact_path(jd_id, "resume", parent_uid=None)
    render_resume_docx(_minimal_data("Matthew Gell"), self_path, template="hybrid")
    finalize_docx(self_path, self_meta)
    add_resume_version(
        file_path=str(self_path), template="hybrid", focus_areas=[],
        tagged_jd_id=jd_id, artifact_uid=self_meta.artifact_uid,
    )

    # For someone else
    other_path, other_meta = make_artifact_path(
        jd_id, "resume", parent_uid=None, for_candidate="Mathilda Gell",
    )
    render_resume_docx(_minimal_data("Mathilda Gell"), other_path, template="hybrid")
    finalize_docx(other_path, other_meta)
    add_resume_version(
        file_path=str(other_path), template="hybrid", focus_areas=[],
        tagged_jd_id=jd_id, artifact_uid=other_meta.artifact_uid,
        for_candidate="Mathilda Gell",
    )

    assert self_path.exists()
    assert other_path.exists()
    assert self_path != other_path

    self_round = read_artifact_meta(self_path)
    other_round = read_artifact_meta(other_path)
    assert self_round.artifact_uid != other_round.artifact_uid
    assert self_round.for_candidate is None
    assert other_round.for_candidate == "Mathilda Gell"
    assert "Matthew" in self_path.name
    assert "Mathilda" in other_path.name
```

- [ ] **Step 2: Run test to verify it passes (everything assembled by now)**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/test_smoke_multi_candidate.py -v
```

Expected: PASS.

- [ ] **Step 3: Run the full suite to check for regressions**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest -q
```

Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add tests/test_smoke_multi_candidate.py
git commit -m "test: end-to-end smoke for multi-candidate Approach C"
```

---

## Task 12: Bump skill version and CHANGELOG entry

**Files:**

- Modify: `scripts/outputs/io.py` (`_SKILL_VERSION`)
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Bump version**

In `scripts/outputs/io.py`, change `_SKILL_VERSION = "1.5.0"` to `_SKILL_VERSION = "1.6.0"`.

- [ ] **Step 2: Update CHANGELOG**

Add at the top of `CHANGELOG.md`:

```markdown
## v1.6.0 — 2026-05-19

### Added
- Multi-candidate support (Approach C): optional `for_candidate` free-text field
  on resumes and cover letters. Pass `for_candidate="<full name>"` into the
  generators / tracker inserts when building a resume for someone other than
  the profile holder. The DOCX records the candidate via the
  `BrainsForCandidate` custom property; the tracker records it via the new
  `for_candidate` columns (migration 0003). When unset, behaviour is identical
  to v1.5.0.
- `scripts.tracker.query.list_artifacts_for_candidate(name)` returns all
  resume + cover-letter rows for a given candidate name.

### Notes
- Single-profile assumption is unchanged. The eventual `candidates` table
  migration (Approach B) will backfill `candidate_id` from this column.
```

- [ ] **Step 3: Commit**

```bash
git add scripts/outputs/io.py CHANGELOG.md
git commit -m "chore: bump version to 1.6.0 + CHANGELOG entry for Approach C"
```

---

## Acceptance Criteria

A. `pytest -q` is green across the full suite.

B. `/brains-create` from the dashboard, run twice — once with the "For candidate" box empty, once with "Mathilda Gell" — produces two DOCX files with distinct UIDs, distinct filenames (`Matthew_Gell_*` vs `Mathilda_Gell_*`), and `BrainsForCandidate` custom property reading as empty-string and "Mathilda Gell" respectively.

C. `scripts.tracker.query.list_artifacts_for_candidate("Mathilda Gell")` returns the second row and not the first.

D. A DOCX written by a v1.5.0 build of the skill, opened by a v1.6.0 build, reads as `for_candidate=None` and the new column on the tracker row is `NULL`. (Forward-compat preserved.)

E. The Mathilda DOCX produced at `c:\Brains_Resume_Skill\output\resume-2026-05-19-142439.docx` (V9MQZX) can be re-tagged with `for_candidate="Mathilda Gell"` by re-calling `write_artifact_meta` with the updated `ArtifactMeta` — verifying the round-trip on a real file from this session.

---

## Self-Review

**Spec coverage:** every architectural touchpoint from the project-multi-candidate-support memory entry maps to a task: schema (Task 1), models (Task 2), inserts (Task 3), reads (Task 4), naming (Task 5), DOCX metadata (Task 6), path resolution (Task 7), dashboard surfacing (Tasks 8-9), workflow docs (Task 10), end-to-end verification (Task 11), versioning (Task 12). No gap.

**Placeholder scan:** every code change has a complete code block. Every test has actual assertions. No "implement similar to above" — Task 9 spells out the per-file adaptation steps because each workflow file has its own pre-existing logic to preserve.

**Type consistency:** `for_candidate: Optional[str] = None` is the field signature everywhere. `make_artifact_path` and `add_resume_version` both take `for_candidate: Optional[str] = None`. `ArtifactMeta.for_candidate: str | None = None` (note: the existing module uses `int | None` syntax, so str | None matches that style). DOCX property name is `BrainsForCandidate` consistently. Empty string → None on the round-trip.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-19-multi-candidate-approach-c.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, two-stage review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in the current session using executing-plans, batch execution with checkpoints.

Which approach?
