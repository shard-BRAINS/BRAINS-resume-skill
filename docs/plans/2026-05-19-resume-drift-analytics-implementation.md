# Resume Drift Analytics — v1.7.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v1.7.0 of the BRAINS Resume Skill — a per-fact-class drift analytic that uses the existing `artifact_uid` + `parent_uid` lineage and v1.6.0's `for_candidate` field to track factual drift across each candidate's resume lineage.

**Architecture:** Two new tables (`resume_fact_snapshots`, `resume_drift_scores`), one new column (`resume_versions.is_baseline`), and a new audit log (`baseline_history`). A `scripts/drift/` package holds the snapshot transform, LLM extractor, compute, lineage walker, baseline promotion, and headline formatter. Workflow hooks call `write_snapshot_and_compute_drift` after each `finalize_docx`. Three dashboard surfaces (Overview tile, Resumes-tab columns, dedicated Drift tab) and one new workflow card (`/brains-import` for uploading a baseline DOCX).

**Tech Stack:** Python 3.14, SQLite (forward-only migrations + index-based invariants), python-docx, reportlab, pytest, Streamlit, the Anthropic SDK (for the LLM-based fact extractor — same SDK already used elsewhere in the skill).

**Spec:** `docs/specs/2026-05-19-resume-drift-analytics-design.md`. Read it once before starting Task 1; the plan references its sections (e.g. "spec §5b") but is self-contained.

**Migration number:** This plan claims migration **0004**. Approach B's plan also reserves 0004 — by user decision Drift Analytics ships first, so Approach B's plan will be re-numbered to 0005/0006 when it lands. If that order ever flips, every occurrence of `0004_drift_analytics` in this plan must be renumbered to `0006_drift_analytics`.

**Pre-flight:**

- Confirm working directory is `c:\Brains_Resume_Skill`, current branch is `main`, and the live skill is at v1.6.0 (HEAD should be at or beyond commit `b3e227c` — the Plan C merge). Create a new feature branch `feature/drift-analytics` from `main` before Task 1.
- `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -V` → Python 3.14.x.
- `"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest -q` baseline: 442 passed, 2 pre-existing failures (`tests/dashboard/test_app_workflows_tab.py::test_workflows_tab_has_three_subheaders`, `tests/tracker/test_query.py::test_weekly_summary_pacing_none_when_no_target`). Leave those alone — they are not in scope.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `scripts/tracker/migrations/0004_drift_analytics.py` | **create** | Schema for `resume_fact_snapshots`, `resume_drift_scores`, `baseline_history`; `is_baseline` column on `resume_versions`; partial unique index; first-row-per-candidate backfill |
| `scripts/tracker/add.py` | modify | `add_resume_version` auto-sets `is_baseline=1` when this is the first non-archived row for the candidate |
| `scripts/drift/__init__.py` | **create** | Package marker + `__all__` |
| `scripts/drift/snapshot_from_workflow.py` | **create** | `facts_from_workflow_data(data)` — pure transform of the workflow data dict into Section 4 fact schema; produces `null` for classes the workflow doesn't capture |
| `scripts/drift/formatters.py` | **create** | `format_headline_changes(score)` — produces ≤5 human-readable bullets per spec §5e |
| `scripts/drift/compute.py` | **create** | `compute_drift_score(left, right)` — pure-Python per-class diff + weighted `overall_pct` with renormalisation; `write_snapshot_and_compute_drift(artifact_uid, facts)` — persists snapshot and drift rows |
| `scripts/drift/lineage.py` | **create** | `get_parent_snapshot(uid)`, `get_baseline_snapshot(uid)`, `get_candidate_lineage(scope)` — walks with archived-row skipping and 100-step cycle guard |
| `scripts/drift/baseline.py` | **create** | `promote_baseline(uid, reason)` — single transaction: flip flag, log to history, recompute all `vs_baseline_score` in the candidate scope |
| `scripts/drift/extract_facts.py` | **create** | `extract_facts_from_text(text)` — LLM-backed structured extractor for `/brains-import`; schema validation; implausibility flagging |
| `scripts/dashboard/prep/drift_sparkline.py` | **create** | `drift_trajectory_last_n(scope, n=12)` — pure data prep for the Overview sparkline |
| `scripts/dashboard/tabs/drift.py` | **create** | Full-page Drift tab: lineage strip, per-fact-class table, field-level diff, "Make this my baseline" button |
| `scripts/dashboard/tabs/overview.py` | modify | Add the drift trajectory tile to the existing Overview tile layout |
| `scripts/dashboard/tabs/resumes.py` | modify | Add "Drift vs parent" and "Drift vs baseline" sortable columns to the Resumes-tab table |
| `scripts/dashboard/app.py` | modify | Register the new Drift tab in the top tab nav |
| `scripts/dashboard/workflows/import.py` | **create** | Streamlit card for `/brains-import` — upload DOCX or paste text; runs extractor; surfaces implausibility flags; commits the row + snapshot |
| `scripts/dashboard/workflows/create.py` | modify | After `finalize_docx`, call `write_snapshot_and_compute_drift` |
| `scripts/dashboard/workflows/edit.py` | modify | Same |
| `scripts/dashboard/workflows/tailor.py` | modify | Same |
| `scripts/dashboard/workflows/cover_letter.py` | modify | Same (kind="cover-letter" — only writes a snapshot if the cover-letter workflow opts in; see Task 14) |
| `references/workflows/import.md` | **create** | Reference doc for the `/brains-import` slash command |
| `scripts/outputs/io.py` | modify | `_SKILL_VERSION` bumped to `"1.7.0"` |
| `pyproject.toml` | modify | `version` bumped to `"1.7.0"` |
| `CHANGELOG.md` | modify | v1.7.0 entry |
| `tests/tracker/migrations/test_0004_drift_analytics.py` | **create** | Schema + backfill correctness |
| `tests/tracker/test_add.py` | modify | `add_resume_version` auto-sets `is_baseline=1` for first row per candidate |
| `tests/drift/__init__.py` | **create** | Test-package marker |
| `tests/drift/test_snapshot_from_workflow.py` | **create** | Transform correctness + null-vs-empty semantics |
| `tests/drift/test_formatters.py` | **create** | `format_headline_changes` priority ordering + ≤5 cap |
| `tests/drift/test_compute_set_classes.py` | **create** | Drift for `skills`, `standalone_achievements`, `hobbies` (set-shaped) |
| `tests/drift/test_compute_identity.py` | **create** | Identity per-field drift |
| `tests/drift/test_compute_list_object_classes.py` | **create** | Experience / education / certifications / languages / publications / portfolio_links — natural key + fuzzy fallback |
| `tests/drift/test_compute_overall.py` | **create** | `overall_pct` weighted aggregate + renormalisation across null classes |
| `tests/drift/test_lineage.py` | **create** | Parent walk skipping archived rows, baseline resolution, cycle guard |
| `tests/drift/test_baseline.py` | **create** | `promote_baseline` transaction + recompute trigger + `baseline_history` audit |
| `tests/drift/test_extract_facts.py` | **create** | LLM extraction with mocked client; validation failures; null-vs-[] from silent-vs-empty source |
| `tests/drift/test_compute_writer.py` | **create** | `write_snapshot_and_compute_drift` integration: snapshot persisted, scores computed against parent + baseline |
| `tests/dashboard/prep/test_drift_sparkline.py` | **create** | Trajectory shape over a fixture lineage |
| `tests/dashboard/tabs/test_drift_tab_render.py` | **create** | Streamlit AppTest covering the Drift tab's basic render |
| `tests/dashboard/workflows/test_import.py` | **create** | `_resolve_target` helper for `/brains-import`; LLM-stubbed end-to-end |
| `tests/test_smoke_drift_end_to_end.py` | **create** | `/brains-import` baseline → `/brains-create` derivative → drift score correctness end-to-end |

---

## Task 1: Migration 0004 — schema + first-row backfill

**Files:**

- Create: `scripts/tracker/migrations/0004_drift_analytics.py`
- Test: `tests/tracker/migrations/test_0004_drift_analytics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/tracker/migrations/test_0004_drift_analytics.py
"""Tests for migration 0004 — drift analytics schema + backfill."""
import pytest

from scripts.tracker.db import open_db


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


def test_resume_fact_snapshots_table_exists(fresh_db):
    conn = open_db()
    try:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "resume_fact_snapshots" in names
    finally:
        conn.close()


def test_resume_drift_scores_table_exists(fresh_db):
    conn = open_db()
    try:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "resume_drift_scores" in names
    finally:
        conn.close()


def test_baseline_history_table_exists(fresh_db):
    conn = open_db()
    try:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "baseline_history" in names
    finally:
        conn.close()


def test_is_baseline_column_present_and_defaults_zero(fresh_db):
    conn = open_db()
    try:
        cols = {r[1]: r for r in conn.execute("PRAGMA table_info(resume_versions)")}
        assert "is_baseline" in cols
        # cid, name, type, notnull, dflt_value, pk
        col = cols["is_baseline"]
        assert col[2] == "INTEGER"
        assert col[3] == 1  # NOT NULL
        assert col[4] == "0"  # default
    finally:
        conn.close()


def test_partial_unique_index_allows_multiple_non_baselines(fresh_db):
    """Only is_baseline=1 rows are subject to the uniqueness constraint."""
    conn = open_db()
    try:
        # Two rows for the same for_candidate, both is_baseline=0 — fine.
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate, is_baseline) "
            "VALUES ('hybrid', '[]', '2026-05-01T00:00:00Z', 'Alice Example', 0)"
        )
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate, is_baseline) "
            "VALUES ('hybrid', '[]', '2026-05-02T00:00:00Z', 'Alice Example', 0)"
        )
        conn.commit()
    finally:
        conn.close()


def test_partial_unique_index_blocks_two_active_baselines(fresh_db):
    """Two is_baseline=1 rows for the same candidate (both active) must fail."""
    import sqlite3
    conn = open_db()
    try:
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate, is_baseline) "
            "VALUES ('hybrid', '[]', '2026-05-01T00:00:00Z', 'Alice Example', 1)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate, is_baseline) "
                "VALUES ('hybrid', '[]', '2026-05-02T00:00:00Z', 'Alice Example', 1)"
            )
            conn.commit()
    finally:
        conn.close()


def test_partial_unique_index_ignores_archived(fresh_db):
    """An archived is_baseline=1 row does not block a new active is_baseline=1 row."""
    conn = open_db()
    try:
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, archived_at, for_candidate, is_baseline) "
            "VALUES ('hybrid', '[]', '2026-05-01T00:00:00Z', '2026-05-02T00:00:00Z', 'Alice Example', 1)"
        )
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate, is_baseline) "
            "VALUES ('hybrid', '[]', '2026-05-03T00:00:00Z', 'Alice Example', 1)"
        )
        conn.commit()
    finally:
        conn.close()


def test_backfill_marks_oldest_per_candidate_as_baseline(fresh_db):
    """Pre-existing rows: the oldest non-archived row per for_candidate gets is_baseline=1."""
    conn = open_db()
    # Roll back the migration baseline so we can simulate pre-0004 rows.
    # Insert two candidate scopes, two rows each, varying created_at.
    try:
        # NULL for_candidate scope
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate) "
            "VALUES ('hybrid', '[]', '2026-04-01T00:00:00Z', NULL)"
        )
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate) "
            "VALUES ('hybrid', '[]', '2026-04-15T00:00:00Z', NULL)"
        )
        # Named scope
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate) "
            "VALUES ('hybrid', '[]', '2026-04-10T00:00:00Z', 'Bob Example')"
        )
        conn.execute(
            "INSERT INTO resume_versions (template, focus_areas, created_at, for_candidate) "
            "VALUES ('hybrid', '[]', '2026-04-20T00:00:00Z', 'Bob Example')"
        )
        conn.commit()
    finally:
        conn.close()
    # Re-run the migration's backfill explicitly by calling the helper.
    from scripts.tracker.migrations import _migration_4  # set up by db.py's loader
    # The loader imports the module under that synthetic name. If unavailable
    # by that name, import it directly:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_mig4",
        r"c:\Brains_Resume_Skill\scripts\tracker\migrations\0004_drift_analytics.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    conn = open_db()
    try:
        mod.backfill_baselines(conn)
        rows = conn.execute(
            "SELECT for_candidate, created_at, is_baseline FROM resume_versions ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    # Two rows per scope, oldest of each is baseline.
    by_scope_first = {}
    for fc, ts, bl in rows:
        key = fc or "<null>"
        by_scope_first.setdefault(key, []).append((ts, bl))
    for scope, entries in by_scope_first.items():
        entries.sort()
        assert entries[0][1] == 1, f"oldest row for {scope!r} should be is_baseline=1"
        for _, bl in entries[1:]:
            assert bl == 0
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/migrations/test_0004_drift_analytics.py -v
```

Expected: every test FAILs — no such tables / column / index / module.

- [ ] **Step 3: Write the migration**

```python
# scripts/tracker/migrations/0004_drift_analytics.py
"""Migration 0004 — resume drift analytics schema.

Adds three tables and one column:
- resume_fact_snapshots: structured fact JSON per artifact_uid
- resume_drift_scores: vs_parent + vs_baseline JSON per artifact_uid
- baseline_history: audit log of baseline promotions
- resume_versions.is_baseline: which row is the active baseline per candidate

A partial unique index enforces "exactly one active baseline per candidate".
A backfill step sets is_baseline=1 on the oldest non-archived row per
for_candidate scope (including the implicit NULL scope = profile holder).

See docs/specs/2026-05-19-resume-drift-analytics-design.md.
"""
import sqlite3


SCHEMA_SQL = """
CREATE TABLE resume_fact_snapshots (
    artifact_uid    TEXT PRIMARY KEY,
    facts           TEXT NOT NULL,
    schema_version  INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL
);

CREATE TABLE resume_drift_scores (
    artifact_uid       TEXT PRIMARY KEY,
    vs_parent_score    TEXT,
    vs_baseline_score  TEXT,
    computed_at        TEXT NOT NULL
);

CREATE TABLE baseline_history (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    for_candidate  TEXT,
    artifact_uid   TEXT NOT NULL,
    promoted_at    TEXT NOT NULL,
    reason         TEXT
);

ALTER TABLE resume_versions ADD COLUMN is_baseline INTEGER NOT NULL DEFAULT 0;

CREATE UNIQUE INDEX ux_resume_versions_baseline_per_candidate
  ON resume_versions(for_candidate)
  WHERE is_baseline = 1 AND archived_at IS NULL;
"""


def backfill_baselines(conn: sqlite3.Connection) -> None:
    """Set is_baseline=1 on the oldest non-archived row per for_candidate
    scope. Idempotent — re-runs are no-ops because the partial unique index
    blocks the second baseline insert per scope."""
    # Identify the oldest non-archived row per distinct for_candidate scope
    # (NULL counts as its own scope).
    rows = conn.execute(
        """
        SELECT id FROM resume_versions rv
        WHERE archived_at IS NULL
          AND created_at = (
              SELECT MIN(created_at) FROM resume_versions rv2
              WHERE rv2.archived_at IS NULL
                AND ((rv2.for_candidate IS NULL AND rv.for_candidate IS NULL)
                     OR rv2.for_candidate = rv.for_candidate)
          )
        """
    ).fetchall()
    target_ids = {r[0] for r in rows}
    for rid in target_ids:
        try:
            conn.execute(
                "UPDATE resume_versions SET is_baseline=1 WHERE id=?",
                (rid,),
            )
        except sqlite3.IntegrityError:
            # Already a baseline in this scope (idempotent re-run).
            pass
    conn.commit()


def apply(conn: sqlite3.Connection) -> None:
    """Apply schema then run the backfill."""
    conn.executescript(SCHEMA_SQL)
    backfill_baselines(conn)
```

- [ ] **Step 4: Run test to verify it passes**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/migrations/test_0004_drift_analytics.py -v
```

Expected: all 8 PASS.

- [ ] **Step 5: Run full tracker suite for regressions**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker -q
```

Expected: only the pre-existing `test_weekly_summary_pacing_none_when_no_target` baseline failure remains.

- [ ] **Step 6: Commit**

```bash
git add scripts/tracker/migrations/0004_drift_analytics.py tests/tracker/migrations/test_0004_drift_analytics.py
git commit -m "feat(tracker): migration 0004 — drift analytics schema + baseline backfill"
```

---

## Task 2: `add_resume_version` auto-sets `is_baseline` for first-per-candidate

**Files:**

- Modify: `scripts/tracker/add.py:18-53` (`add_resume_version`)
- Test: `tests/tracker/test_add.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/tracker/test_add.py`:

```python
def test_add_resume_version_first_row_per_candidate_sets_is_baseline(fresh_db):
    """The first non-archived row inserted for a candidate gets is_baseline=1."""
    from scripts.tracker.add import add_resume_version
    from scripts.tracker.db import open_db

    rv_id = add_resume_version(None, "hybrid", [], for_candidate="Mathilda Gell")
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT is_baseline FROM resume_versions WHERE id=?", (rv_id,)
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == 1


def test_add_resume_version_second_row_per_candidate_is_not_baseline(fresh_db):
    from scripts.tracker.add import add_resume_version
    from scripts.tracker.db import open_db

    first = add_resume_version(None, "hybrid", [], for_candidate="Mathilda Gell")
    second = add_resume_version(None, "hybrid", [], for_candidate="Mathilda Gell")
    conn = open_db()
    try:
        rows = conn.execute(
            "SELECT id, is_baseline FROM resume_versions WHERE id IN (?, ?)",
            (first, second),
        ).fetchall()
    finally:
        conn.close()
    by_id = {r[0]: r[1] for r in rows}
    assert by_id[first] == 1
    assert by_id[second] == 0


def test_add_resume_version_separate_candidates_each_get_a_baseline(fresh_db):
    from scripts.tracker.add import add_resume_version
    from scripts.tracker.db import open_db

    a = add_resume_version(None, "hybrid", [], for_candidate="Matthew Gell")
    b = add_resume_version(None, "hybrid", [], for_candidate="Mathilda Gell")
    conn = open_db()
    try:
        rows = conn.execute(
            "SELECT id, is_baseline FROM resume_versions WHERE id IN (?, ?)",
            (a, b),
        ).fetchall()
    finally:
        conn.close()
    by_id = {r[0]: r[1] for r in rows}
    assert by_id[a] == 1
    assert by_id[b] == 1


def test_add_resume_version_explicit_is_baseline_false_overrides_auto(fresh_db):
    """Caller can opt out of the auto-baseline by passing is_baseline=False."""
    from scripts.tracker.add import add_resume_version
    from scripts.tracker.db import open_db

    rv_id = add_resume_version(
        None, "hybrid", [], for_candidate="Mathilda Gell", is_baseline=False,
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT is_baseline FROM resume_versions WHERE id=?", (rv_id,)
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_add.py -v -k is_baseline
```

Expected: 4 FAILs — column not set; unexpected-keyword-argument on the fourth.

- [ ] **Step 3: Update `add_resume_version`**

Replace `add_resume_version` in `scripts/tracker/add.py`:

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
    is_baseline: Optional[bool] = None,
) -> int:
    """Insert a resume_versions row, return the new id.

    is_baseline:
      - None (default): auto — set to 1 if this is the first non-archived row
        in this for_candidate scope, else 0.
      - True / False: explicit override; the caller controls the flag.
    """
    conn = open_db()
    try:
        if is_baseline is None:
            existing = conn.execute(
                "SELECT COUNT(*) FROM resume_versions "
                "WHERE archived_at IS NULL AND "
                "((? IS NULL AND for_candidate IS NULL) OR for_candidate = ?)",
                (for_candidate, for_candidate),
            ).fetchone()[0]
            resolved_baseline = 1 if existing == 0 else 0
        else:
            resolved_baseline = 1 if is_baseline else 0

        cur = conn.execute(
            """
            INSERT INTO resume_versions
                (file_path, template, focus_areas, parent_id, tagged_jd_id,
                 created_at, artifact_uid, parent_uid, for_candidate,
                 is_baseline)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_path, template, json.dumps(focus_areas),
                parent_id, tagged_jd_id, _now_iso(),
                artifact_uid, parent_uid, for_candidate,
                resolved_baseline,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/tracker/test_add.py -v
```

Expected: all PASS (existing tests + 4 new).

- [ ] **Step 5: Commit**

```bash
git add scripts/tracker/add.py tests/tracker/test_add.py
git commit -m "feat(tracker): add_resume_version auto-sets is_baseline for first-per-candidate"
```

---

## Task 3: `scripts/drift/` package skeleton + `snapshot_from_workflow`

**Files:**

- Create: `scripts/drift/__init__.py`
- Create: `scripts/drift/snapshot_from_workflow.py`
- Create: `tests/drift/__init__.py`
- Create: `tests/drift/test_snapshot_from_workflow.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/drift/__init__.py — empty marker file
```

```python
# tests/drift/test_snapshot_from_workflow.py
"""Tests for facts_from_workflow_data (pure transform, no I/O)."""
import pytest

from scripts.drift.snapshot_from_workflow import facts_from_workflow_data


SAMPLE_WORKFLOW_DATA = {
    "candidate_name": "Mathilda Gell",
    "candidate_contact_line": "Rochedale, QLD  ·  0433 814 874  ·  mathilda@malin.com.au",
    "summary": "Grade 10 student at Redeemer Lutheran College.",
    "skills": (
        "• Customer engagement\n"
        "• Public speaking\n"
        "• Team leadership"
    ),
    "experience": (
        "Holiday Work — Faith Christian Distance Education\n"
        "Brisbane, QLD  ·  January 2026\n"
        "• Worked 5 to 6 days preparing enrolment material.\n"
        "• Packed and organised enrolment packs."
    ),
    "education": (
        "Redeemer Lutheran College — Rochedale, QLD\n"
        "Currently in Grade 10  ·  Expected to complete Year 12 in 2028"
    ),
}


def test_identity_parsed_from_contact_line():
    facts = facts_from_workflow_data(SAMPLE_WORKFLOW_DATA)
    assert facts["identity"]["name"] == "Mathilda Gell"
    assert facts["identity"]["location"] == "Rochedale, QLD"
    assert facts["identity"]["phone"] == "0433 814 874"
    assert facts["identity"]["email"] == "mathilda@malin.com.au"


def test_skills_parsed_as_list_of_strings():
    facts = facts_from_workflow_data(SAMPLE_WORKFLOW_DATA)
    assert facts["skills"] == [
        "Customer engagement",
        "Public speaking",
        "Team leadership",
    ]


def test_experience_parsed_into_entries():
    facts = facts_from_workflow_data(SAMPLE_WORKFLOW_DATA)
    assert len(facts["experience"]) == 1
    e = facts["experience"][0]
    assert e["entry_id"] == "exp-1"
    assert e["employer"] == "Faith Christian Distance Education"
    assert e["title"] == "Holiday Work"
    assert e["start_date"] == "2026-01"
    assert e["end_date"] == "2026-01"
    assert e["location"] == "Brisbane, QLD"
    assert "Worked 5 to 6 days preparing enrolment material." in e["key_points"]


def test_education_parsed_into_entries():
    facts = facts_from_workflow_data(SAMPLE_WORKFLOW_DATA)
    assert len(facts["education"]) == 1
    ed = facts["education"][0]
    assert ed["entry_id"] == "edu-1"
    assert ed["institution"] == "Redeemer Lutheran College"
    assert "Grade 10" in ed["qualification"]


def test_uncaptured_classes_are_null_not_empty_list():
    """Workflow doesn't ask for hobbies/languages/publications/portfolio_links;
    they must be null (skipped in drift compute) not [] (treated as removed)."""
    facts = facts_from_workflow_data(SAMPLE_WORKFLOW_DATA)
    for cls in ("hobbies", "languages", "publications", "portfolio_links"):
        assert facts[cls] is None, f"{cls} must be null, not {facts[cls]!r}"


def test_certifications_and_achievements_inconsistent_workflow_returns_null():
    """When the workflow doesn't surface certifications or standalone_achievements
    as their own sections, the transform returns null for those classes too."""
    facts = facts_from_workflow_data(SAMPLE_WORKFLOW_DATA)
    # Sample data has neither — both null.
    assert facts["certifications"] is None
    assert facts["standalone_achievements"] is None


def test_schema_version_is_1():
    facts = facts_from_workflow_data(SAMPLE_WORKFLOW_DATA)
    # schema_version lives on the snapshot row, not in the facts dict — but
    # the transform exposes it via a constant for the writer to pick up.
    from scripts.drift.snapshot_from_workflow import SCHEMA_VERSION
    assert SCHEMA_VERSION == 1
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_snapshot_from_workflow.py -v
```

Expected: ImportError on every test.

- [ ] **Step 3: Create the package marker**

```python
# scripts/drift/__init__.py
"""BRAINS Resume Skill — drift analytics package.

See docs/specs/2026-05-19-resume-drift-analytics-design.md.
"""
```

- [ ] **Step 4: Implement `snapshot_from_workflow`**

```python
# scripts/drift/snapshot_from_workflow.py
"""Transform the workflow's render-time data dict into the Section 4 fact schema.

Pure function, no I/O. Classes the workflow does not capture today (hobbies,
languages, publications, portfolio_links — and inconsistently certifications,
standalone_achievements) are returned as null, NOT empty list, per spec §4.
"""
from __future__ import annotations

import re
from typing import Optional


SCHEMA_VERSION = 1


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
_PHONE_RE = re.compile(r"(?:\+?\d[\d \-()]{7,}\d)")


def _split_contact_line(contact_line: str) -> dict:
    """Parse 'Location  ·  Phone  ·  Email' into identity dict."""
    if not contact_line:
        return {"name": None, "location": None, "phone": None, "email": None}
    # Normalize separator runs (· or | or -) to a single delimiter.
    parts = re.split(r"\s*[·|]\s*", contact_line)
    parts = [p.strip() for p in parts if p.strip()]
    email = None
    phone = None
    location = None
    for p in parts:
        m_email = _EMAIL_RE.search(p)
        if m_email and not email:
            email = m_email.group(0)
            continue
        m_phone = _PHONE_RE.fullmatch(p)
        if m_phone and not phone:
            phone = p
            continue
        if not location:
            location = p
    return {"name": None, "location": location, "phone": phone, "email": email}


_MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09", "sept": "09",
    "oct": "10", "nov": "11", "dec": "12",
}


def _normalize_date(token: str) -> Optional[str]:
    """Best-effort normalisation to YYYY-MM or YYYY. Returns None on failure."""
    if not token:
        return None
    s = token.strip().lower()
    if s in ("present", "current", "now"):
        return "present"
    m = re.match(r"([a-z]+)\s+(\d{4})$", s)
    if m and m.group(1) in _MONTH_MAP:
        return f"{m.group(2)}-{_MONTH_MAP[m.group(1)]}"
    m = re.match(r"(\d{4})-(\d{1,2})$", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.match(r"(\d{4})$", s)
    if m:
        return s
    return None


def _split_entries(block: str) -> list[list[str]]:
    """Split a multi-entry block into per-entry line lists.

    An entry starts at a non-bullet line followed by a meta line. Bullets
    (lines starting with • or -) belong to the current entry.
    """
    lines = [ln.rstrip() for ln in (block or "").splitlines() if ln.strip()]
    entries: list[list[str]] = []
    current: list[str] = []
    for ln in lines:
        is_bullet = ln.lstrip().startswith(("•", "-"))
        if not is_bullet and current and not current[-1].lstrip().startswith(("•", "-")):
            # Two non-bullet lines in a row — second is the meta line of current entry.
            current.append(ln)
        elif not is_bullet and current:
            # Non-bullet starting a new entry.
            entries.append(current)
            current = [ln]
        else:
            current.append(ln)
    if current:
        entries.append(current)
    return entries


def _parse_experience(block: str) -> list[dict]:
    """Parse an experience block into entry dicts."""
    if not block:
        return []
    entries = _split_entries(block)
    result = []
    for idx, lines in enumerate(entries, start=1):
        head = lines[0].lstrip()
        if "—" in head:
            title_part, employer_part = head.split("—", 1)
        elif " - " in head:
            title_part, employer_part = head.split(" - ", 1)
        else:
            title_part, employer_part = head, ""
        title = title_part.strip()
        employer = employer_part.strip()
        location = None
        start = None
        end = None
        key_points: list[str] = []
        for ln in lines[1:]:
            stripped = ln.lstrip()
            if stripped.startswith(("•", "-")):
                key_points.append(stripped.lstrip("•-").strip())
            else:
                # meta line — look for location · dates
                parts = re.split(r"\s*[·|]\s*", stripped)
                for p in parts:
                    p = p.strip()
                    if not p:
                        continue
                    if re.match(r"^[A-Z][a-zA-Z ]+,\s*[A-Z]{2,3}$", p):
                        location = p
                        continue
                    if re.search(r"[a-z]+\s+\d{4}", p, flags=re.IGNORECASE) or re.match(r"^\d{4}", p):
                        # Date range or single date.
                        if "–" in p or " to " in p.lower() or "-" in p:
                            sep = "–" if "–" in p else (" to " if " to " in p.lower() else "-")
                            left, right = p.split(sep, 1)
                            start = _normalize_date(left)
                            end = _normalize_date(right)
                        else:
                            start = _normalize_date(p)
                            end = start
        result.append({
            "entry_id": f"exp-{idx}",
            "employer": employer or None,
            "title": title or None,
            "start_date": start,
            "end_date": end,
            "location": location,
            "key_points": key_points,
        })
    return result


def _parse_education(block: str) -> list[dict]:
    """Parse an education block into entry dicts.

    Format expected: 'Institution — Location' / meta-line / optional bullets.
    """
    if not block:
        return []
    entries = _split_entries(block)
    result = []
    for idx, lines in enumerate(entries, start=1):
        head = lines[0].lstrip()
        if "—" in head:
            inst_part, _ = head.split("—", 1)
            institution = inst_part.strip()
        elif " - " in head:
            inst_part, _ = head.split(" - ", 1)
            institution = inst_part.strip()
        else:
            institution = head
        qualification = None
        completion_year = None
        completion_status = None
        for ln in lines[1:]:
            stripped = ln.lstrip().lstrip("•-").strip()
            if not stripped:
                continue
            m = re.search(r"(\d{4})", stripped)
            if m:
                completion_year = m.group(1)
            if "expected" in stripped.lower():
                completion_status = "expected"
            elif "currently" in stripped.lower() or "in progress" in stripped.lower():
                completion_status = "in_progress"
            elif "completed" in stripped.lower():
                completion_status = "completed"
            if qualification is None:
                qualification = stripped
        result.append({
            "entry_id": f"edu-{idx}",
            "institution": institution or None,
            "qualification": qualification,
            "completion_year": completion_year,
            "completion_status": completion_status,
            "honours": [],
        })
    return result


def _parse_skills(block: str) -> list[str]:
    """Parse a bullet-or-line skills block into a clean list of strings."""
    if not block:
        return []
    items: list[str] = []
    for ln in block.splitlines():
        stripped = ln.lstrip().lstrip("•-").strip()
        if not stripped:
            continue
        # Drop trailing parenthetical context for matching purposes.
        items.append(stripped.split(" — ", 1)[0].split(" - ", 1)[0].strip())
    return items


def facts_from_workflow_data(data: dict) -> dict:
    """Convert the workflow's render-time data dict into the Section 4 schema.

    For classes the workflow doesn't capture today (hobbies, languages,
    publications, portfolio_links), returns null (NOT empty list) so drift
    compute correctly skips them. Inconsistent classes (certifications,
    standalone_achievements) also return null unless the workflow opts in
    by including them as their own keys.
    """
    identity = _split_contact_line(data.get("candidate_contact_line", ""))
    identity["name"] = data.get("candidate_name") or None

    experience = _parse_experience(data.get("experience", "")) or []
    education = _parse_education(data.get("education", "")) or []
    skills = _parse_skills(data.get("skills", ""))

    return {
        "identity": identity,
        "experience": experience,
        "education": education,
        "skills": skills,
        "certifications": data.get("certifications") if "certifications" in data else None,
        "standalone_achievements": data.get("standalone_achievements") if "standalone_achievements" in data else None,
        "hobbies": data.get("hobbies") if "hobbies" in data else None,
        "languages": data.get("languages") if "languages" in data else None,
        "publications": data.get("publications") if "publications" in data else None,
        "portfolio_links": data.get("portfolio_links") if "portfolio_links" in data else None,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_snapshot_from_workflow.py -v
```

Expected: all 7 PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/drift/__init__.py scripts/drift/snapshot_from_workflow.py tests/drift/__init__.py tests/drift/test_snapshot_from_workflow.py
git commit -m "feat(drift): package skeleton + facts_from_workflow_data transform"
```

---

## Task 4: `compute_drift_score` — set-shaped classes (skills / standalone_achievements / hobbies)

**Files:**

- Create: `scripts/drift/compute.py` (this task introduces it; later tasks extend it)
- Test: `tests/drift/test_compute_set_classes.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/drift/test_compute_set_classes.py
"""Drift for set-shaped classes (skills, standalone_achievements, hobbies)."""
import pytest

from scripts.drift.compute import compute_class_diff


def test_set_class_unchanged():
    out = compute_class_diff(["A", "B", "C"], ["A", "B", "C"], kind="set")
    assert out == {"added": [], "removed": [], "total": 3, "pct": 0.0}


def test_set_class_one_added():
    out = compute_class_diff(["A", "B"], ["A", "B", "C"], kind="set")
    assert out["added"] == ["C"]
    assert out["removed"] == []
    assert out["total"] == 3
    assert out["pct"] == pytest.approx(33.333333, abs=0.001)


def test_set_class_one_removed():
    out = compute_class_diff(["A", "B", "C"], ["A", "B"], kind="set")
    assert out["added"] == []
    assert out["removed"] == ["C"]
    assert out["total"] == 3  # max(3, 2)
    assert out["pct"] == pytest.approx(33.333333, abs=0.001)


def test_set_class_both_added_and_removed():
    out = compute_class_diff(["A", "B"], ["B", "C"], kind="set")
    assert out["added"] == ["C"]
    assert out["removed"] == ["A"]
    assert out["total"] == 2  # max(2, 2)
    assert out["pct"] == 100.0


def test_set_class_all_removed():
    out = compute_class_diff(["A", "B", "C"], [], kind="set")
    assert out["added"] == []
    assert out["removed"] == ["A", "B", "C"]
    assert out["total"] == 3
    assert out["pct"] == 100.0


def test_set_class_both_empty():
    out = compute_class_diff([], [], kind="set")
    assert out == {"added": [], "removed": [], "total": 0, "pct": 0.0}


def test_set_class_null_left_returns_status_not_captured():
    out = compute_class_diff(None, ["A"], kind="set")
    assert out == {"status": "not_captured", "pct": None}


def test_set_class_null_right_returns_status_not_captured():
    out = compute_class_diff(["A"], None, kind="set")
    assert out == {"status": "not_captured", "pct": None}


def test_set_class_both_null_returns_status_not_captured():
    out = compute_class_diff(None, None, kind="set")
    assert out == {"status": "not_captured", "pct": None}
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_compute_set_classes.py -v
```

Expected: ImportError on `compute_class_diff`.

- [ ] **Step 3: Implement `compute_class_diff` for set-shape**

```python
# scripts/drift/compute.py
"""Drift compute — pure-Python per-class diff + weighted overall_pct.

See spec §5 for the formula. Compute is split into per-class helpers:
- compute_class_diff(left, right, kind=...) — single class diff.
- compute_drift_score(left_facts, right_facts) — full snapshot diff.
- write_snapshot_and_compute_drift(artifact_uid, facts) — persistence wrapper.

This file is grown incrementally across Tasks 4-9. This is the set-shape
branch (Task 4); identity (Task 5), list-of-object (Task 6), and the
overall_pct aggregator (Task 7) extend it.
"""
from __future__ import annotations

from typing import Any


def _null_status() -> dict:
    return {"status": "not_captured", "pct": None}


def _set_diff(left: list, right: list) -> dict:
    left_set = list(left or [])
    right_set = list(right or [])
    added = [x for x in right_set if x not in left_set]
    removed = [x for x in left_set if x not in right_set]
    total = max(len(left_set), len(right_set))
    if total == 0:
        return {"added": [], "removed": [], "total": 0, "pct": 0.0}
    changed = len(added) + len(removed)
    pct = (changed / total) * 100.0
    return {"added": added, "removed": removed, "total": total, "pct": pct}


def compute_class_diff(left: Any, right: Any, kind: str) -> dict:
    """Compute the per-class diff dict for a single class.

    kind: one of 'set' (set-shaped: list[str]).
          'identity', 'list_object' added in later tasks.

    Returns {'status': 'not_captured', 'pct': None} if either side is None
    (spec §5b — null-class handling).
    """
    if left is None or right is None:
        return _null_status()

    if kind == "set":
        return _set_diff(left, right)
    raise ValueError(f"Unknown class kind: {kind!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_compute_set_classes.py -v
```

Expected: all 9 PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/drift/compute.py tests/drift/test_compute_set_classes.py
git commit -m "feat(drift): compute_class_diff for set-shaped classes + null handling"
```

---

## Task 5: `compute_class_diff` — identity class

**Files:**

- Modify: `scripts/drift/compute.py`
- Test: `tests/drift/test_compute_identity.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/drift/test_compute_identity.py
import pytest

from scripts.drift.compute import compute_class_diff


IDENTITY_A = {"name": "Mathilda Gell", "location": "Rochedale, QLD",
              "email": "m@x.com", "phone": "0433814874"}
IDENTITY_B = {"name": "Mathilda Gell", "location": "Brisbane, QLD",
              "email": "m@x.com", "phone": "0433814874"}


def test_identity_unchanged():
    out = compute_class_diff(IDENTITY_A, dict(IDENTITY_A), kind="identity")
    assert out == {"fields_changed": [], "fields_total": 4, "pct": 0.0}


def test_identity_one_field_changed():
    out = compute_class_diff(IDENTITY_A, IDENTITY_B, kind="identity")
    assert out["fields_changed"] == ["location"]
    assert out["fields_total"] == 4
    assert out["pct"] == 25.0


def test_identity_null_field_counts_when_other_side_has_value():
    left = dict(IDENTITY_A)
    right = dict(IDENTITY_A)
    right["phone"] = None
    out = compute_class_diff(left, right, kind="identity")
    assert out["fields_changed"] == ["phone"]
    assert out["pct"] == 25.0


def test_identity_both_null_on_field_is_not_a_change():
    left = dict(IDENTITY_A); left["phone"] = None
    right = dict(IDENTITY_A); right["phone"] = None
    out = compute_class_diff(left, right, kind="identity")
    assert out["fields_changed"] == []
    assert out["pct"] == 0.0


def test_identity_null_object_returns_not_captured():
    out = compute_class_diff(None, IDENTITY_A, kind="identity")
    assert out == {"status": "not_captured", "pct": None}
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_compute_identity.py -v
```

Expected: ValueError on "Unknown class kind".

- [ ] **Step 3: Extend `compute.py`**

Append to `scripts/drift/compute.py` (BEFORE the existing `if kind == "set":` branch, add an `if kind == "identity":` branch in `compute_class_diff` and the helper below):

```python
_IDENTITY_FIELDS = ("name", "location", "email", "phone")


def _identity_diff(left: dict, right: dict) -> dict:
    left = left or {}
    right = right or {}
    fields_changed = []
    for f in _IDENTITY_FIELDS:
        if (left.get(f) or None) != (right.get(f) or None):
            fields_changed.append(f)
    total = len(_IDENTITY_FIELDS)
    pct = (len(fields_changed) / total) * 100.0 if total else 0.0
    return {"fields_changed": fields_changed, "fields_total": total, "pct": pct}
```

Then add the dispatch in `compute_class_diff`:

```python
    if kind == "identity":
        return _identity_diff(left, right)
```

The full `compute_class_diff` body now looks like (replace it as one block to avoid drift between the two branches):

```python
def compute_class_diff(left: Any, right: Any, kind: str) -> dict:
    """Compute the per-class diff dict for a single class.

    kind: one of 'set', 'identity'. 'list_object' added in Task 6.

    Returns {'status': 'not_captured', 'pct': None} if either side is None.
    """
    if left is None or right is None:
        return _null_status()
    if kind == "set":
        return _set_diff(left, right)
    if kind == "identity":
        return _identity_diff(left, right)
    raise ValueError(f"Unknown class kind: {kind!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_compute_identity.py tests/drift/test_compute_set_classes.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/drift/compute.py tests/drift/test_compute_identity.py
git commit -m "feat(drift): compute_class_diff for identity per-field"
```

---

## Task 6: `compute_class_diff` — list-of-object classes with natural-key + fuzzy fallback

**Files:**

- Modify: `scripts/drift/compute.py`
- Test: `tests/drift/test_compute_list_object_classes.py`

The classes that share list-of-object shape per spec §5c: `experience`, `education`, `certifications`, `languages`, `publications`, `portfolio_links`. Each has its own natural-key + fuzzy-match rule (spec §5c table).

- [ ] **Step 1: Write the failing test**

```python
# tests/drift/test_compute_list_object_classes.py
"""Per-class drift for the six list-of-object classes."""
import pytest

from scripts.drift.compute import compute_class_diff


EXP_A = [
    {"entry_id": "exp-1", "employer": "Acme", "title": "Engineer",
     "start_date": "2024-01", "end_date": "2025-12",
     "location": "Brisbane, QLD", "key_points": ["Did X"]},
]
EXP_B = [
    {"entry_id": "exp-1", "employer": "Acme", "title": "Engineer II",
     "start_date": "2024-01", "end_date": "2025-12",
     "location": "Brisbane, QLD", "key_points": ["Did X"]},
]
EXP_C_NEW_ENTRY = [
    {"entry_id": "exp-1", "employer": "Acme", "title": "Engineer",
     "start_date": "2024-01", "end_date": "2025-12",
     "location": "Brisbane, QLD", "key_points": ["Did X"]},
    {"entry_id": "exp-2", "employer": "Beta", "title": "Senior",
     "start_date": "2026-01", "end_date": "present",
     "location": "Brisbane, QLD", "key_points": ["Did Y"]},
]


def test_experience_unchanged():
    out = compute_class_diff(EXP_A, EXP_A, kind="experience")
    assert out["entries_added"] == 0
    assert out["entries_removed"] == 0
    assert out["entries_with_field_changes"] == 0
    assert out["entries_total"] == 1
    assert out["pct"] == 0.0
    assert out["field_changes"] == []


def test_experience_title_field_change():
    out = compute_class_diff(EXP_A, EXP_B, kind="experience")
    assert out["entries_with_field_changes"] == 1
    assert any(fc["field"] == "title" for fc in out["field_changes"])
    assert out["entries_total"] == 1
    assert out["pct"] == 100.0


def test_experience_entry_added():
    out = compute_class_diff(EXP_A, EXP_C_NEW_ENTRY, kind="experience")
    assert out["entries_added"] == 1
    assert out["entries_removed"] == 0
    assert out["entries_total"] == 2
    assert out["pct"] == 50.0


def test_experience_natural_key_matches_across_reorder():
    """Same entries in different order — should match via (employer, start_date)."""
    out = compute_class_diff(EXP_C_NEW_ENTRY, list(reversed(EXP_C_NEW_ENTRY)), kind="experience")
    assert out["pct"] == 0.0


def test_experience_fuzzy_fallback_matches_renamed_employer():
    """Employer renamed slightly — fuzzy match prevents 'added + removed'."""
    left = [{"entry_id": "exp-1", "employer": "Acme Corporation",
             "title": "Engineer", "start_date": "2024-01",
             "end_date": "2025-12", "location": "Brisbane, QLD",
             "key_points": []}]
    right = [{"entry_id": "exp-1", "employer": "Acme Corp.",
              "title": "Engineer", "start_date": "2024-01",
              "end_date": "2025-12", "location": "Brisbane, QLD",
              "key_points": []}]
    out = compute_class_diff(left, right, kind="experience")
    # Natural key (employer + start_date) doesn't match exactly; fuzzy
    # fallback should treat them as the same entry with employer changed.
    assert out["entries_added"] == 0
    assert out["entries_removed"] == 0
    assert out["entries_with_field_changes"] == 1
    assert any(fc["field"] == "employer" for fc in out["field_changes"])


def test_education_natural_key_institution_qualification():
    left = [{"entry_id": "edu-1", "institution": "X High",
             "qualification": "Year 12", "completion_year": "2027",
             "completion_status": "expected", "honours": []}]
    right = [{"entry_id": "edu-1", "institution": "X High",
              "qualification": "Year 12", "completion_year": "2027",
              "completion_status": "completed", "honours": []}]
    out = compute_class_diff(left, right, kind="education")
    assert out["entries_with_field_changes"] == 1
    assert any(fc["field"] == "completion_status" for fc in out["field_changes"])
    assert out["pct"] == 100.0


def test_certifications_natural_key_by_name():
    left = [{"name": "AWS SAA", "issuer": "Amazon", "year": "2023"}]
    right = [{"name": "AWS SAA", "issuer": "Amazon", "year": "2024"}]
    out = compute_class_diff(left, right, kind="certifications")
    assert any(fc["field"] == "year" for fc in out["field_changes"])
    assert out["pct"] == 100.0


def test_languages_proficiency_change():
    left = [{"language": "Spanish", "proficiency": "basic"}]
    right = [{"language": "Spanish", "proficiency": "conversational"}]
    out = compute_class_diff(left, right, kind="languages")
    assert any(fc["field"] == "proficiency" for fc in out["field_changes"])
    assert out["pct"] == 100.0


def test_languages_added_entry():
    left = [{"language": "English", "proficiency": "native"}]
    right = [{"language": "English", "proficiency": "native"},
             {"language": "Spanish", "proficiency": "basic"}]
    out = compute_class_diff(left, right, kind="languages")
    assert out["entries_added"] == 1
    assert out["pct"] == 50.0


def test_publications_title_year_natural_key():
    left = [{"title": "A study of X", "venue": "Journal Y",
             "year": "2024", "authors": ["A"], "url": None}]
    right = [{"title": "A study of X", "venue": "Journal Y",
              "year": "2024", "authors": ["A", "B"], "url": None}]
    out = compute_class_diff(left, right, kind="publications")
    assert any(fc["field"] == "authors" for fc in out["field_changes"])
    assert out["pct"] == 100.0


def test_portfolio_links_url_canonicalised():
    """Same URL with/without trailing slash, protocol prefix, case differences match."""
    left = [{"label": "GitHub", "url": "https://github.com/Mathilda/"}]
    right = [{"label": "GitHub profile", "url": "github.com/mathilda"}]
    out = compute_class_diff(left, right, kind="portfolio_links")
    # URL canonicalises to same; label is the field change.
    assert out["entries_added"] == 0
    assert out["entries_removed"] == 0
    assert any(fc["field"] == "label" for fc in out["field_changes"])


def test_null_class_returns_not_captured():
    out = compute_class_diff(None, EXP_A, kind="experience")
    assert out == {"status": "not_captured", "pct": None}


def test_empty_vs_populated_is_full_drift():
    """[] vs populated counts as 100% drift (everything 'added')."""
    out = compute_class_diff([], EXP_A, kind="experience")
    assert out["entries_added"] == 1
    assert out["pct"] == 100.0
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_compute_list_object_classes.py -v
```

Expected: all FAIL with ValueError on unknown class kind.

- [ ] **Step 3: Extend `compute.py` with list-of-object support**

Append to `scripts/drift/compute.py`:

```python
import re as _re


def _token_set_ratio(a: str, b: str) -> float:
    """Token-set similarity in [0, 1]. Inline implementation — uses rapidfuzz
    when available, falls back to a simple Jaccard on lowercased tokens.
    """
    try:
        from rapidfuzz.fuzz import token_set_ratio  # type: ignore
        return token_set_ratio(a or "", b or "") / 100.0
    except ImportError:
        pass
    aw = set((a or "").lower().split())
    bw = set((b or "").lower().split())
    if not aw and not bw:
        return 1.0
    if not aw or not bw:
        return 0.0
    return len(aw & bw) / len(aw | bw)


def _canonicalise_url(url: str) -> str:
    """Lowercase, strip http(s)://, strip trailing /."""
    if not url:
        return ""
    s = url.strip().lower()
    s = _re.sub(r"^https?://", "", s)
    s = s.rstrip("/")
    return s


def _natural_key(entry: dict, kind: str) -> tuple | str | None:
    if kind == "experience":
        if not entry.get("employer") or not entry.get("start_date"):
            return None
        return (entry["employer"].strip().lower(), entry["start_date"])
    if kind == "education":
        if not entry.get("institution") or not entry.get("qualification"):
            return None
        return (entry["institution"].strip().lower(),
                entry["qualification"].strip().lower())
    if kind == "certifications":
        if not entry.get("name"):
            return None
        return entry["name"].strip().lower()
    if kind == "languages":
        if not entry.get("language"):
            return None
        return entry["language"].strip().lower()
    if kind == "publications":
        if not entry.get("title"):
            return None
        return (entry["title"].strip().lower(), entry.get("year") or "")
    if kind == "portfolio_links":
        if not entry.get("url"):
            return None
        return _canonicalise_url(entry["url"])
    raise ValueError(f"No natural key for kind {kind!r}")


_FUZZY_FIELDS = {
    "experience": (["employer", "title"], 0.85),
    "education": (["institution"], 0.85),
    "certifications": (["name"], 0.85),
    "languages": (["language"], 0.90),
    "publications": (["title"], 0.85),
    "portfolio_links": (None, None),  # exact-only via canonicalised URL
}


_COMPARE_FIELDS = {
    "experience": ("employer", "title", "start_date", "end_date", "location", "key_points"),
    "education":  ("institution", "qualification", "completion_year",
                   "completion_status", "honours"),
    "certifications": ("name", "issuer", "year"),
    "languages": ("language", "proficiency"),
    "publications": ("title", "venue", "year", "authors", "url"),
    "portfolio_links": ("label", "url"),
}


def _fuzzy_match(target: dict, candidates: list[dict], kind: str) -> int | None:
    """Return index in candidates of best fuzzy match, or None if below threshold.

    Used when natural-key match fails. Compares specified text fields.
    """
    fields, threshold = _FUZZY_FIELDS[kind]
    if fields is None:
        return None
    best_idx = None
    best_score = 0.0
    for i, cand in enumerate(candidates):
        scores = [_token_set_ratio(target.get(f, "") or "", cand.get(f, "") or "")
                  for f in fields]
        score = min(scores) if scores else 0.0
        if score > best_score and score >= threshold:
            best_idx = i
            best_score = score
    return best_idx


def _compare_entries(left: dict, right: dict, kind: str, entry_id: str) -> list[dict]:
    """Per-field comparison. Returns list of {entry_id, field, from, to}."""
    changes = []
    for f in _COMPARE_FIELDS[kind]:
        l_val = left.get(f)
        r_val = right.get(f)
        if (l_val or None) != (r_val or None):
            changes.append({"entry_id": entry_id, "field": f,
                            "from": l_val, "to": r_val})
    return changes


def _list_object_diff(left: list[dict], right: list[dict], kind: str) -> dict:
    left = list(left or [])
    right = list(right or [])

    # Build natural-key indices.
    left_by_key: dict = {}
    left_unkeyed: list[int] = []
    for i, e in enumerate(left):
        k = _natural_key(e, kind)
        if k is None:
            left_unkeyed.append(i)
        else:
            left_by_key.setdefault(k, []).append(i)

    right_consumed = [False] * len(right)
    left_consumed = [False] * len(left)
    field_changes: list[dict] = []
    entries_with_field_changes = 0

    # Pass 1: natural-key matches.
    for j, r_entry in enumerate(right):
        rk = _natural_key(r_entry, kind)
        if rk is None:
            continue
        bucket = left_by_key.get(rk)
        if not bucket:
            continue
        i = bucket.pop(0)
        left_consumed[i] = True
        right_consumed[j] = True
        changes = _compare_entries(left[i], r_entry, kind,
                                   left[i].get("entry_id") or r_entry.get("entry_id") or f"{kind}-{i}")
        if changes:
            entries_with_field_changes += 1
            field_changes.extend(changes)

    # Pass 2: fuzzy fallback for the unmatched.
    unmatched_left = [i for i, used in enumerate(left_consumed) if not used]
    unmatched_right = [j for j, used in enumerate(right_consumed) if not used]
    for j in list(unmatched_right):
        cand_idxs = [i for i in unmatched_left if not left_consumed[i]]
        candidates = [left[i] for i in cand_idxs]
        m = _fuzzy_match(right[j], candidates, kind)
        if m is None:
            continue
        i = cand_idxs[m]
        left_consumed[i] = True
        right_consumed[j] = True
        changes = _compare_entries(left[i], right[j], kind,
                                   left[i].get("entry_id") or right[j].get("entry_id") or f"{kind}-{i}")
        if changes:
            entries_with_field_changes += 1
            field_changes.extend(changes)

    entries_removed = sum(1 for u in left_consumed if not u)
    entries_added = sum(1 for u in right_consumed if not u)

    total = max(len(left), len(right))
    if total == 0:
        return {"entries_added": 0, "entries_removed": 0,
                "entries_with_field_changes": 0,
                "field_changes": [], "entries_total": 0, "pct": 0.0}
    changed_units = entries_added + entries_removed + entries_with_field_changes
    pct = (changed_units / total) * 100.0
    return {
        "entries_added": entries_added,
        "entries_removed": entries_removed,
        "entries_with_field_changes": entries_with_field_changes,
        "field_changes": field_changes,
        "entries_total": total,
        "pct": pct,
    }
```

Then replace `compute_class_diff` with the full multi-kind dispatcher:

```python
_LIST_OBJECT_KINDS = ("experience", "education", "certifications",
                     "languages", "publications", "portfolio_links")


def compute_class_diff(left: Any, right: Any, kind: str) -> dict:
    """Compute the per-class diff dict for a single class.

    kind: one of 'set', 'identity', or any of the list-of-object classes:
          experience, education, certifications, languages, publications,
          portfolio_links.

    Returns {'status': 'not_captured', 'pct': None} if either side is None
    (spec §5b — null-class handling). [] is NOT the same as None.
    """
    if left is None or right is None:
        return _null_status()
    if kind == "set":
        return _set_diff(left, right)
    if kind == "identity":
        return _identity_diff(left, right)
    if kind in _LIST_OBJECT_KINDS:
        return _list_object_diff(left, right, kind)
    raise ValueError(f"Unknown class kind: {kind!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_compute_list_object_classes.py -v
```

Expected: all PASS. Also re-run earlier compute tests to confirm no regression:

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift -v
```

- [ ] **Step 5: Commit**

```bash
git add scripts/drift/compute.py tests/drift/test_compute_list_object_classes.py
git commit -m "feat(drift): compute_class_diff for list-of-object classes with fuzzy fallback"
```

---

## Task 7: `compute_drift_score` — full snapshot diff + weighted `overall_pct`

**Files:**

- Modify: `scripts/drift/compute.py`
- Test: `tests/drift/test_compute_overall.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/drift/test_compute_overall.py
"""End-to-end snapshot diff + overall_pct with renormalisation."""
import pytest

from scripts.drift.compute import compute_drift_score


BASELINE = {
    "identity": {"name": "Mathilda Gell", "location": "Rochedale, QLD",
                 "email": "m@x.com", "phone": "0433"},
    "experience": [
        {"entry_id": "exp-1", "employer": "Acme",
         "title": "Engineer", "start_date": "2024-01",
         "end_date": "2025-12", "location": "Brisbane, QLD",
         "key_points": ["Did X"]}
    ],
    "education": [
        {"entry_id": "edu-1", "institution": "X High",
         "qualification": "Year 12", "completion_year": "2027",
         "completion_status": "expected", "honours": []}
    ],
    "skills": ["A", "B", "C"],
    "certifications": [{"name": "AWS SAA", "issuer": "Amazon", "year": "2023"}],
    "standalone_achievements": ["Award 1"],
    "hobbies": ["Netball"],
    "languages": [{"language": "English", "proficiency": "native"}],
    "publications": [],
    "portfolio_links": [{"label": "GitHub", "url": "github.com/x"}],
}


def test_identical_snapshots_overall_zero():
    out = compute_drift_score(BASELINE, BASELINE)
    assert out["overall_pct"] == 0.0


def test_identity_only_change_uses_identity_weight():
    """Only identity changes (location). Weight 0.20 means overall = 0.20 * 25% = 5.0%."""
    right = {**BASELINE, "identity": {**BASELINE["identity"], "location": "Brisbane, QLD"}}
    out = compute_drift_score(BASELINE, right)
    # identity pct = 25% (1 of 4 fields), weight 0.20 — but all 10 classes are
    # populated on both sides, so overall = 0.20 * 25 = 5.0 (no renormalisation).
    assert out["identity"]["pct"] == 25.0
    assert out["overall_pct"] == pytest.approx(5.0, abs=0.01)


def test_null_class_skipped_and_weights_renormalise():
    """Right side has null for 6 classes — overall_pct should renormalise across
    only the 4 classes both sides cover (identity, experience, education, skills)."""
    right = {
        "identity": BASELINE["identity"],
        "experience": BASELINE["experience"],
        "education": BASELINE["education"],
        "skills": BASELINE["skills"],
        "certifications": None,
        "standalone_achievements": None,
        "hobbies": None,
        "languages": None,
        "publications": None,
        "portfolio_links": None,
    }
    out = compute_drift_score(BASELINE, right)
    # All 4 classes are identical → overall = 0.
    assert out["overall_pct"] == 0.0
    # And the 6 null classes have status 'not_captured'.
    for cls in ("certifications", "standalone_achievements", "hobbies",
                "languages", "publications", "portfolio_links"):
        assert out[cls] == {"status": "not_captured", "pct": None}


def test_null_class_with_changes_in_other_classes():
    """Identity changes 25%, all 6 non-core classes null. Renormalised weights:
    identity 0.20 / (0.20+0.25+0.12+0.08) = 0.3077.
    overall_pct = 0.3077 * 25 = ~7.69."""
    right = {
        "identity": {**BASELINE["identity"], "location": "X"},
        "experience": BASELINE["experience"],
        "education": BASELINE["education"],
        "skills": BASELINE["skills"],
        "certifications": None,
        "standalone_achievements": None,
        "hobbies": None,
        "languages": None,
        "publications": None,
        "portfolio_links": None,
    }
    out = compute_drift_score(BASELINE, right)
    expected = (0.20 / (0.20 + 0.25 + 0.12 + 0.08)) * 25.0
    assert out["overall_pct"] == pytest.approx(expected, abs=0.01)


def test_empty_list_is_not_skipped():
    """[] vs populated counts as 100% drift for that class — not skipped."""
    right = {**BASELINE, "skills": []}
    out = compute_drift_score(BASELINE, right)
    assert out["skills"]["pct"] == 100.0
    # Skills weight 0.08, all other classes unchanged.
    assert out["overall_pct"] == pytest.approx(0.08 * 100.0, abs=0.01)


def test_headline_changes_capped_at_5():
    """Multiple changes — output limited to 5 bullets."""
    right = {
        "identity": {"name": "X", "location": "Y", "email": "z@z", "phone": "0"},
        **{k: v for k, v in BASELINE.items() if k != "identity"},
    }
    out = compute_drift_score(BASELINE, right)
    assert "headline_changes" in out
    assert len(out["headline_changes"]) <= 5
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_compute_overall.py -v
```

Expected: ImportError on `compute_drift_score`.

- [ ] **Step 3: Implement `compute_drift_score`**

Append to `scripts/drift/compute.py`:

```python
DRIFT_CLASS_WEIGHTS = {
    "identity": 0.20,
    "experience": 0.25,
    "education": 0.12,
    "skills": 0.08,
    "certifications": 0.08,
    "standalone_achievements": 0.06,
    "hobbies": 0.04,
    "languages": 0.07,
    "publications": 0.06,
    "portfolio_links": 0.04,
}

_CLASS_KIND = {
    "identity": "identity",
    "experience": "experience",
    "education": "education",
    "skills": "set",
    "certifications": "certifications",
    "standalone_achievements": "set",
    "hobbies": "set",
    "languages": "languages",
    "publications": "publications",
    "portfolio_links": "portfolio_links",
}


def compute_drift_score(left: dict, right: dict) -> dict:
    """Compute the full per-class + overall drift between two snapshots.

    See spec §5d for the weighted aggregate with null-class renormalisation.
    Both snapshots must use schema_version 1 (Section 4).
    """
    out: dict = {}
    captured_weights_sum = 0.0
    weighted_total = 0.0
    for cls, kind in _CLASS_KIND.items():
        diff = compute_class_diff(left.get(cls), right.get(cls), kind=kind)
        out[cls] = diff
        if diff.get("status") == "not_captured":
            continue
        weight = DRIFT_CLASS_WEIGHTS[cls]
        captured_weights_sum += weight
        weighted_total += weight * diff["pct"]

    if captured_weights_sum > 0:
        overall_pct = weighted_total / captured_weights_sum
    else:
        overall_pct = 0.0
    out["overall_pct"] = round(overall_pct, 2)

    # Headline changes — delegated to formatters.format_headline_changes.
    from scripts.drift.formatters import format_headline_changes
    out["headline_changes"] = format_headline_changes(out)
    return out
```

Note: this introduces a dependency on `scripts.drift.formatters.format_headline_changes`, which Task 8 implements. For TDD discipline, write a temporary stub in `scripts/drift/formatters.py` now so Task 7's test passes:

```python
# scripts/drift/formatters.py — temporary stub; Task 8 replaces this.
def format_headline_changes(score: dict) -> list[str]:
    return []
```

- [ ] **Step 4: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift -v
```

Expected: all PASS, including the headline-capped-at-5 test (the stub returns `[]`, which satisfies "≤5").

- [ ] **Step 5: Commit**

```bash
git add scripts/drift/compute.py scripts/drift/formatters.py tests/drift/test_compute_overall.py
git commit -m "feat(drift): compute_drift_score full snapshot diff with renormalised overall_pct"
```

---

## Task 8: `format_headline_changes`

**Files:**

- Modify: `scripts/drift/formatters.py`
- Test: `tests/drift/test_formatters.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/drift/test_formatters.py
"""Headline-changes formatter — priority ordering + ≤5 cap."""
import pytest

from scripts.drift.formatters import format_headline_changes


def test_empty_score_returns_empty_list():
    score = {cls: {"status": "not_captured", "pct": None}
             for cls in ("identity", "experience", "education", "skills",
                         "certifications", "standalone_achievements", "hobbies",
                         "languages", "publications", "portfolio_links")}
    score["overall_pct"] = 0.0
    assert format_headline_changes(score) == []


def test_identity_change_appears_first():
    score = {
        "identity": {"fields_changed": ["location"], "fields_total": 4, "pct": 25.0},
        "experience": {"entries_added": 0, "entries_removed": 0,
                       "entries_with_field_changes": 0, "field_changes": [],
                       "entries_total": 1, "pct": 0.0},
        "education": {"status": "not_captured", "pct": None},
        "skills": {"added": [], "removed": [], "total": 3, "pct": 0.0},
        "certifications": {"status": "not_captured", "pct": None},
        "standalone_achievements": {"status": "not_captured", "pct": None},
        "hobbies": {"status": "not_captured", "pct": None},
        "languages": {"status": "not_captured", "pct": None},
        "publications": {"status": "not_captured", "pct": None},
        "portfolio_links": {"status": "not_captured", "pct": None},
        "overall_pct": 5.0,
    }
    out = format_headline_changes(score)
    assert len(out) == 1
    assert "location" in out[0].lower()


def test_priority_order_identity_then_experience_field_then_added_removed():
    score = {
        "identity": {"fields_changed": ["location"], "fields_total": 4, "pct": 25.0},
        "experience": {"entries_added": 1, "entries_removed": 0,
                       "entries_with_field_changes": 1,
                       "field_changes": [{"entry_id": "exp-1", "field": "title",
                                          "from": "A", "to": "B"}],
                       "entries_total": 2, "pct": 100.0},
        "education": {"status": "not_captured", "pct": None},
        "skills": {"added": ["X"], "removed": [], "total": 4, "pct": 25.0},
        "certifications": {"status": "not_captured", "pct": None},
        "standalone_achievements": {"status": "not_captured", "pct": None},
        "hobbies": {"status": "not_captured", "pct": None},
        "languages": {"status": "not_captured", "pct": None},
        "publications": {"status": "not_captured", "pct": None},
        "portfolio_links": {"status": "not_captured", "pct": None},
        "overall_pct": 30.0,
    }
    out = format_headline_changes(score)
    # Priority: identity → experience field changes → experience entries added → skills added.
    assert out[0].lower().startswith(("identity", "location"))
    assert "title" in out[1].lower() or "experience" in out[1].lower()


def test_capped_at_5():
    """Snapshot with way more than 5 bullets — output capped."""
    score = {
        "identity": {"fields_changed": ["name", "location", "email", "phone"],
                     "fields_total": 4, "pct": 100.0},
        "experience": {"entries_added": 3, "entries_removed": 2,
                       "entries_with_field_changes": 2,
                       "field_changes": [
                           {"entry_id": f"exp-{i}", "field": "title",
                            "from": "A", "to": "B"} for i in range(5)
                       ],
                       "entries_total": 5, "pct": 100.0},
        "education": {"entries_added": 1, "entries_removed": 0,
                      "entries_with_field_changes": 0, "field_changes": [],
                      "entries_total": 1, "pct": 100.0},
        "skills": {"added": ["X", "Y", "Z"], "removed": ["A"],
                   "total": 10, "pct": 40.0},
        "certifications": {"status": "not_captured", "pct": None},
        "standalone_achievements": {"status": "not_captured", "pct": None},
        "hobbies": {"status": "not_captured", "pct": None},
        "languages": {"status": "not_captured", "pct": None},
        "publications": {"status": "not_captured", "pct": None},
        "portfolio_links": {"status": "not_captured", "pct": None},
        "overall_pct": 90.0,
    }
    out = format_headline_changes(score)
    assert len(out) == 5
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_formatters.py -v
```

Expected: 3 FAILs (the stub returns `[]` for everything).

- [ ] **Step 3: Replace the stub with the real formatter**

Replace `scripts/drift/formatters.py`:

```python
"""Headline-changes formatter.

Selects ≤5 most salient changes across a drift score, ordered by
spec §5e priority. Pure function, no I/O.
"""
from __future__ import annotations


def _identity_lines(score: dict) -> list[str]:
    out = []
    info = score.get("identity") or {}
    for f in info.get("fields_changed") or []:
        out.append(f"Identity field changed: {f}")
    return out


def _exp_field_lines(score: dict) -> list[str]:
    info = score.get("experience") or {}
    return [
        f"Experience · {fc['entry_id']} · {fc['field']} changed"
        for fc in (info.get("field_changes") or [])
    ]


def _exp_entry_lines(score: dict) -> list[str]:
    info = score.get("experience") or {}
    out = []
    if info.get("entries_added"):
        out.append(f"{info['entries_added']} experience entries added")
    if info.get("entries_removed"):
        out.append(f"{info['entries_removed']} experience entries removed")
    return out


def _edu_field_lines(score: dict) -> list[str]:
    info = score.get("education") or {}
    return [
        f"Education · {fc['entry_id']} · {fc['field']} changed"
        for fc in (info.get("field_changes") or [])
    ]


def _edu_entry_lines(score: dict) -> list[str]:
    info = score.get("education") or {}
    out = []
    if info.get("entries_added"):
        out.append(f"{info['entries_added']} education entries added")
    if info.get("entries_removed"):
        out.append(f"{info['entries_removed']} education entries removed")
    return out


def _list_class_lines(score: dict, cls: str, label: str) -> list[str]:
    info = score.get(cls) or {}
    out = []
    if info.get("field_changes"):
        for fc in info["field_changes"]:
            out.append(f"{label} · {fc.get('entry_id', '?')} · {fc['field']} changed")
    if info.get("entries_added"):
        out.append(f"{info['entries_added']} {label.lower()} entries added")
    if info.get("entries_removed"):
        out.append(f"{info['entries_removed']} {label.lower()} entries removed")
    return out


def _set_class_lines(score: dict, cls: str, label: str) -> list[str]:
    info = score.get(cls) or {}
    out = []
    if info.get("added"):
        out.append(f"{len(info['added'])} {label.lower()} added")
    if info.get("removed"):
        out.append(f"{len(info['removed'])} {label.lower()} removed")
    return out


_PRIORITY_FNS = [
    _identity_lines,
    _exp_field_lines,
    _exp_entry_lines,
    _edu_field_lines,
    _edu_entry_lines,
    lambda s: _list_class_lines(s, "certifications", "Certifications"),
    lambda s: _list_class_lines(s, "languages", "Languages"),
    lambda s: _list_class_lines(s, "publications", "Publications"),
    lambda s: _set_class_lines(s, "skills", "Skills"),
    lambda s: _set_class_lines(s, "standalone_achievements", "Achievements"),
    lambda s: _list_class_lines(s, "portfolio_links", "Portfolio links"),
    lambda s: _set_class_lines(s, "hobbies", "Hobbies"),
]


def format_headline_changes(score: dict, limit: int = 5) -> list[str]:
    """Return up to `limit` human-readable headline change lines.

    Ordered by spec §5e priority. Skips classes with status 'not_captured'.
    """
    out: list[str] = []
    for fn in _PRIORITY_FNS:
        for line in fn(score):
            out.append(line)
            if len(out) >= limit:
                return out
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift -v
```

Expected: all PASS, including the headline-capped-at-5 test which now actually exercises the formatter.

- [ ] **Step 5: Commit**

```bash
git add scripts/drift/formatters.py tests/drift/test_formatters.py
git commit -m "feat(drift): format_headline_changes priority ordering + 5-item cap"
```

---

## Task 9: `lineage.py` — parent, baseline, candidate-lineage walkers

**Files:**

- Create: `scripts/drift/lineage.py`
- Test: `tests/drift/test_lineage.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/drift/test_lineage.py
"""Lineage walking: parent skipping archived, baseline resolution, cycle guard."""
import pytest

from scripts.tracker.add import add_resume_version
from scripts.tracker.db import open_db


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


def _insert_snapshot(artifact_uid: str, facts: dict):
    import json
    from datetime import datetime
    conn = open_db()
    try:
        conn.execute(
            "INSERT INTO resume_fact_snapshots (artifact_uid, facts, created_at) "
            "VALUES (?, ?, ?)",
            (artifact_uid, json.dumps(facts), datetime.utcnow().isoformat() + "Z"),
        )
        conn.commit()
    finally:
        conn.close()


def test_get_parent_snapshot_returns_parent(fresh_db):
    from scripts.drift.lineage import get_parent_snapshot

    add_resume_version(None, "hybrid", [], artifact_uid="PARENT",
                       for_candidate="Mathilda Gell")
    add_resume_version(None, "hybrid", [], artifact_uid="CHILD",
                       parent_uid="PARENT", for_candidate="Mathilda Gell")
    _insert_snapshot("PARENT", {"skills": ["A"]})
    out = get_parent_snapshot("CHILD")
    assert out == {"skills": ["A"]}


def test_get_parent_snapshot_skips_archived(fresh_db):
    from datetime import datetime
    from scripts.drift.lineage import get_parent_snapshot

    add_resume_version(None, "hybrid", [], artifact_uid="GRAND",
                       for_candidate="X")
    # Archive PARENT mid-chain.
    add_resume_version(None, "hybrid", [], artifact_uid="PARENT",
                       parent_uid="GRAND", for_candidate="X")
    conn = open_db()
    try:
        conn.execute(
            "UPDATE resume_versions SET archived_at=? WHERE artifact_uid=?",
            (datetime.utcnow().isoformat() + "Z", "PARENT"),
        )
        conn.commit()
    finally:
        conn.close()
    add_resume_version(None, "hybrid", [], artifact_uid="CHILD",
                       parent_uid="PARENT", for_candidate="X")
    _insert_snapshot("GRAND", {"skills": ["G"]})
    out = get_parent_snapshot("CHILD")
    # Skips archived PARENT, returns GRAND's snapshot.
    assert out == {"skills": ["G"]}


def test_get_parent_snapshot_returns_none_when_no_parent(fresh_db):
    from scripts.drift.lineage import get_parent_snapshot
    add_resume_version(None, "hybrid", [], artifact_uid="ORPHAN",
                       for_candidate="Z")
    assert get_parent_snapshot("ORPHAN") is None


def test_get_baseline_snapshot_returns_baseline(fresh_db):
    from scripts.drift.lineage import get_baseline_snapshot
    add_resume_version(None, "hybrid", [], artifact_uid="BL",
                       for_candidate="W")
    add_resume_version(None, "hybrid", [], artifact_uid="V2",
                       parent_uid="BL", for_candidate="W")
    _insert_snapshot("BL", {"skills": ["baseline"]})
    out = get_baseline_snapshot("V2")
    assert out == {"skills": ["baseline"]}


def test_get_baseline_snapshot_returns_none_when_no_baseline(fresh_db):
    from scripts.drift.lineage import get_baseline_snapshot
    add_resume_version(None, "hybrid", [], artifact_uid="ALONE",
                       for_candidate="Q", is_baseline=False)
    assert get_baseline_snapshot("ALONE") is None


def test_cycle_guard_caps_walk_at_100(fresh_db):
    """A malformed parent chain (cycle) returns None instead of infinite-looping."""
    from scripts.drift.lineage import get_parent_snapshot
    # Build a cycle: A → B → A.
    add_resume_version(None, "hybrid", [], artifact_uid="A", parent_uid="B",
                       for_candidate="C")
    add_resume_version(None, "hybrid", [], artifact_uid="B", parent_uid="A",
                       for_candidate="C")
    # No snapshots — walker should bail by depth 100, not infinite-loop.
    out = get_parent_snapshot("A")
    assert out is None
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_lineage.py -v
```

Expected: ImportError on every test.

- [ ] **Step 3: Implement `lineage.py`**

```python
# scripts/drift/lineage.py
"""Lineage walkers: parent (skipping archived), baseline, full candidate lineage.

All walkers cap at depth 100 (cycle defence) and skip archived rows.
"""
from __future__ import annotations

import json
from typing import Optional

from scripts.tracker.db import open_db


_DEPTH_CAP = 100


def _load_snapshot_facts(conn, artifact_uid: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT facts FROM resume_fact_snapshots WHERE artifact_uid=?",
        (artifact_uid,),
    ).fetchone()
    if row is None:
        return None
    try:
        return json.loads(row[0])
    except (json.JSONDecodeError, TypeError):
        return None


def _resolve_candidate_scope(conn, artifact_uid: str) -> dict:
    row = conn.execute(
        "SELECT for_candidate FROM resume_versions WHERE artifact_uid=?",
        (artifact_uid,),
    ).fetchone()
    if row is None:
        return {"for_candidate": None}
    return {"for_candidate": row[0]}


def get_parent_snapshot(artifact_uid: str) -> Optional[dict]:
    """Walk parent_uid chain, skipping archived rows, until a row with a
    fact snapshot is found. Returns None if none found within 100 hops.
    """
    conn = open_db()
    try:
        seen: set = set()
        current = artifact_uid
        for _ in range(_DEPTH_CAP):
            row = conn.execute(
                "SELECT parent_uid FROM resume_versions WHERE artifact_uid=?",
                (current,),
            ).fetchone()
            if row is None or row[0] is None:
                return None
            parent_uid = row[0]
            if parent_uid in seen:
                return None  # cycle detected
            seen.add(parent_uid)
            archived = conn.execute(
                "SELECT archived_at FROM resume_versions WHERE artifact_uid=?",
                (parent_uid,),
            ).fetchone()
            if archived is not None and archived[0] is not None:
                # Skip archived row; continue up.
                current = parent_uid
                continue
            facts = _load_snapshot_facts(conn, parent_uid)
            if facts is not None:
                return facts
            current = parent_uid
        return None
    finally:
        conn.close()


def get_baseline_snapshot(artifact_uid: str) -> Optional[dict]:
    """Find the active baseline row for this artifact's candidate scope and
    return its fact snapshot. Returns None if no active baseline or no snapshot.
    """
    conn = open_db()
    try:
        scope = _resolve_candidate_scope(conn, artifact_uid)
        for_candidate = scope["for_candidate"]
        row = conn.execute(
            """SELECT artifact_uid FROM resume_versions
               WHERE is_baseline = 1 AND archived_at IS NULL
                 AND ((? IS NULL AND for_candidate IS NULL) OR for_candidate = ?)
               LIMIT 1""",
            (for_candidate, for_candidate),
        ).fetchone()
        if row is None:
            return None
        return _load_snapshot_facts(conn, row[0])
    finally:
        conn.close()


def get_candidate_lineage(scope: dict) -> list:
    """Return all non-archived resume_versions rows for the given for_candidate
    scope, sorted by created_at ascending."""
    from scripts.tracker.models import ResumeVersion
    conn = open_db()
    try:
        for_candidate = scope.get("for_candidate")
        rows = conn.execute(
            """SELECT id, file_path, template, focus_areas, parent_id,
                      tagged_jd_id, created_at, archived_at, artifact_uid,
                      parent_uid, for_candidate
               FROM resume_versions
               WHERE archived_at IS NULL
                 AND ((? IS NULL AND for_candidate IS NULL) OR for_candidate = ?)
               ORDER BY created_at ASC""",
            (for_candidate, for_candidate),
        ).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        out.append(ResumeVersion(
            id=r[0], file_path=r[1], template=r[2],
            focus_areas=json.loads(r[3] or "[]"),
            parent_id=r[4], tagged_jd_id=r[5],
            created_at=r[6], archived_at=r[7],
            artifact_uid=r[8], parent_uid=r[9], for_candidate=r[10],
        ))
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_lineage.py -v
```

Expected: all 6 PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/drift/lineage.py tests/drift/test_lineage.py
git commit -m "feat(drift): lineage walkers — parent / baseline / candidate-lineage with cycle guard"
```

---

## Task 10: `write_snapshot_and_compute_drift` integration writer

**Files:**

- Modify: `scripts/drift/compute.py`
- Test: `tests/drift/test_compute_writer.py`

This task wires the snapshot persistence + drift compute into a single callable that workflow integrations (Task 13) use after `finalize_docx`.

- [ ] **Step 1: Write the failing test**

```python
# tests/drift/test_compute_writer.py
"""Integration: write_snapshot_and_compute_drift persists snapshot + scores."""
import json

import pytest

from scripts.tracker.add import add_resume_version
from scripts.tracker.db import open_db


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


SAMPLE_FACTS = {
    "identity": {"name": "X", "location": "Y", "email": "x@y", "phone": "0"},
    "experience": [], "education": [], "skills": [],
    "certifications": None, "standalone_achievements": None,
    "hobbies": None, "languages": None, "publications": None,
    "portfolio_links": None,
}


def test_writes_snapshot_row(fresh_db):
    from scripts.drift.compute import write_snapshot_and_compute_drift

    add_resume_version(None, "hybrid", [], artifact_uid="ABC",
                       for_candidate="X")
    write_snapshot_and_compute_drift("ABC", SAMPLE_FACTS)

    conn = open_db()
    try:
        row = conn.execute(
            "SELECT facts, schema_version FROM resume_fact_snapshots "
            "WHERE artifact_uid=?", ("ABC",),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert json.loads(row[0]) == SAMPLE_FACTS
    assert row[1] == 1


def test_baseline_writes_null_drift_scores(fresh_db):
    """The baseline row has no parent and IS the baseline — both scores null."""
    from scripts.drift.compute import write_snapshot_and_compute_drift

    add_resume_version(None, "hybrid", [], artifact_uid="BL",
                       for_candidate="X")
    write_snapshot_and_compute_drift("BL", SAMPLE_FACTS)

    conn = open_db()
    try:
        row = conn.execute(
            "SELECT vs_parent_score, vs_baseline_score "
            "FROM resume_drift_scores WHERE artifact_uid=?", ("BL",),
        ).fetchone()
    finally:
        conn.close()
    assert row[0] is None
    assert row[1] is None


def test_derivative_writes_both_scores(fresh_db):
    """A child of the baseline: both vs_parent and vs_baseline computed."""
    from scripts.drift.compute import write_snapshot_and_compute_drift

    add_resume_version(None, "hybrid", [], artifact_uid="BL",
                       for_candidate="X")
    write_snapshot_and_compute_drift("BL", SAMPLE_FACTS)

    add_resume_version(None, "hybrid", [], artifact_uid="CHILD",
                       parent_uid="BL", for_candidate="X")
    child_facts = {**SAMPLE_FACTS,
                   "identity": {**SAMPLE_FACTS["identity"], "location": "Z"}}
    write_snapshot_and_compute_drift("CHILD", child_facts)

    conn = open_db()
    try:
        row = conn.execute(
            "SELECT vs_parent_score, vs_baseline_score "
            "FROM resume_drift_scores WHERE artifact_uid=?", ("CHILD",),
        ).fetchone()
    finally:
        conn.close()
    parent_score = json.loads(row[0])
    baseline_score = json.loads(row[1])
    assert parent_score["identity"]["pct"] == 25.0
    assert baseline_score["identity"]["pct"] == 25.0


def test_idempotent_on_resave(fresh_db):
    """Calling write twice for the same UID overwrites cleanly (no duplicate rows)."""
    from scripts.drift.compute import write_snapshot_and_compute_drift

    add_resume_version(None, "hybrid", [], artifact_uid="ABC",
                       for_candidate="X")
    write_snapshot_and_compute_drift("ABC", SAMPLE_FACTS)
    write_snapshot_and_compute_drift("ABC", SAMPLE_FACTS)

    conn = open_db()
    try:
        n_snap = conn.execute(
            "SELECT COUNT(*) FROM resume_fact_snapshots WHERE artifact_uid=?",
            ("ABC",),
        ).fetchone()[0]
        n_score = conn.execute(
            "SELECT COUNT(*) FROM resume_drift_scores WHERE artifact_uid=?",
            ("ABC",),
        ).fetchone()[0]
    finally:
        conn.close()
    assert n_snap == 1
    assert n_score == 1
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_compute_writer.py -v
```

Expected: ImportError on `write_snapshot_and_compute_drift`.

- [ ] **Step 3: Implement the writer**

Append to `scripts/drift/compute.py`:

```python
import json as _json
from datetime import datetime as _datetime


def _now_iso() -> str:
    return _datetime.utcnow().isoformat() + "Z"


def write_snapshot_and_compute_drift(artifact_uid: str, facts: dict) -> None:
    """Persist the snapshot, look up parent + baseline, compute and persist scores.

    Idempotent on artifact_uid — uses INSERT OR REPLACE so calling twice for the
    same UID overwrites cleanly.

    The baseline-relative score is NULL when this row IS the baseline (looked up
    by checking is_baseline on the resume_versions row).
    """
    from scripts.drift.lineage import get_parent_snapshot, get_baseline_snapshot
    from scripts.tracker.db import open_db

    conn = open_db()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO resume_fact_snapshots "
            "(artifact_uid, facts, schema_version, created_at) "
            "VALUES (?, ?, ?, ?)",
            (artifact_uid, _json.dumps(facts), 1, _now_iso()),
        )

        # Determine whether this row IS the baseline.
        row = conn.execute(
            "SELECT is_baseline FROM resume_versions WHERE artifact_uid=?",
            (artifact_uid,),
        ).fetchone()
        is_baseline = bool(row and row[0])

        parent_snap = None if is_baseline else get_parent_snapshot(artifact_uid)
        # For non-baseline rows, baseline_snap is the active baseline's facts.
        baseline_snap = None if is_baseline else get_baseline_snapshot(artifact_uid)

        vs_parent = (compute_drift_score(parent_snap, facts)
                     if parent_snap is not None else None)
        vs_baseline = (compute_drift_score(baseline_snap, facts)
                       if baseline_snap is not None else None)

        conn.execute(
            "INSERT OR REPLACE INTO resume_drift_scores "
            "(artifact_uid, vs_parent_score, vs_baseline_score, computed_at) "
            "VALUES (?, ?, ?, ?)",
            (
                artifact_uid,
                _json.dumps(vs_parent) if vs_parent is not None else None,
                _json.dumps(vs_baseline) if vs_baseline is not None else None,
                _now_iso(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/drift/compute.py tests/drift/test_compute_writer.py
git commit -m "feat(drift): write_snapshot_and_compute_drift integration writer"
```

---

## Task 11: `baseline.py` — `promote_baseline` + recompute

**Files:**

- Create: `scripts/drift/baseline.py`
- Test: `tests/drift/test_baseline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/drift/test_baseline.py
"""Baseline promotion: single-baseline invariant, audit log, recompute trigger."""
import json

import pytest

from scripts.drift.compute import write_snapshot_and_compute_drift
from scripts.tracker.add import add_resume_version
from scripts.tracker.db import open_db


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


def _seed(scope="X"):
    """Build a baseline + 2 derivatives for the candidate."""
    facts_base = {
        "identity": {"name": "X", "location": "Q", "email": "x@y", "phone": "0"},
        "experience": [], "education": [], "skills": ["A"],
        "certifications": None, "standalone_achievements": None,
        "hobbies": None, "languages": None, "publications": None,
        "portfolio_links": None,
    }
    facts_v2 = {**facts_base, "skills": ["A", "B"]}
    facts_v3 = {**facts_base, "skills": ["A", "B", "C"]}

    add_resume_version(None, "hybrid", [], artifact_uid="BL", for_candidate=scope)
    write_snapshot_and_compute_drift("BL", facts_base)

    add_resume_version(None, "hybrid", [], artifact_uid="V2",
                       parent_uid="BL", for_candidate=scope)
    write_snapshot_and_compute_drift("V2", facts_v2)

    add_resume_version(None, "hybrid", [], artifact_uid="V3",
                       parent_uid="V2", for_candidate=scope)
    write_snapshot_and_compute_drift("V3", facts_v3)


def test_promote_flips_is_baseline(fresh_db):
    from scripts.drift.baseline import promote_baseline
    _seed()
    promote_baseline("V2", reason="Test promotion")
    conn = open_db()
    try:
        rows = dict(conn.execute(
            "SELECT artifact_uid, is_baseline FROM resume_versions "
            "WHERE for_candidate='X'"
        ).fetchall())
    finally:
        conn.close()
    assert rows["BL"] == 0
    assert rows["V2"] == 1
    assert rows["V3"] == 0


def test_promote_appends_history_row(fresh_db):
    from scripts.drift.baseline import promote_baseline
    _seed()
    promote_baseline("V2", reason="Real-life change")
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT for_candidate, artifact_uid, reason "
            "FROM baseline_history WHERE artifact_uid='V2'"
        ).fetchone()
    finally:
        conn.close()
    assert row == ("X", "V2", "Real-life change")


def test_promote_recomputes_vs_baseline_for_descendants(fresh_db):
    """After promoting V2, V3's vs_baseline_score should be recomputed against V2."""
    from scripts.drift.baseline import promote_baseline
    _seed()
    # V3 vs_baseline_score before promotion (computed against BL: skills A vs A,B,C = 100%).
    promote_baseline("V2", reason="x")
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT vs_baseline_score FROM resume_drift_scores WHERE artifact_uid='V3'"
        ).fetchone()
    finally:
        conn.close()
    score = json.loads(row[0])
    # V3 vs V2: skills A,B vs A,B,C → 1 added of 3 = ~33%.
    assert score["skills"]["pct"] == pytest.approx(33.333333, abs=0.01)


def test_promote_sets_promoted_baseline_to_null_drift(fresh_db):
    """The newly-promoted baseline's own vs_baseline_score becomes null."""
    from scripts.drift.baseline import promote_baseline
    _seed()
    promote_baseline("V2", reason="x")
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT vs_baseline_score FROM resume_drift_scores WHERE artifact_uid='V2'"
        ).fetchone()
    finally:
        conn.close()
    assert row[0] is None
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_baseline.py -v
```

Expected: ImportError on `scripts.drift.baseline`.

- [ ] **Step 3: Implement `baseline.py`**

```python
# scripts/drift/baseline.py
"""Baseline promotion API.

promote_baseline(artifact_uid, reason) flips is_baseline in one transaction,
appends an audit row to baseline_history, and recomputes vs_baseline_score for
every non-archived resume in the candidate's scope.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from scripts.drift.compute import compute_drift_score
from scripts.drift.lineage import _load_snapshot_facts
from scripts.tracker.db import open_db


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def promote_baseline(artifact_uid: str, reason: str) -> None:
    """Set the given artifact as the active baseline for its candidate scope.

    Single transaction:
      1. Resolve candidate scope from the artifact_uid.
      2. UPDATE: clear is_baseline on any existing active baseline in scope.
      3. UPDATE: set is_baseline=1 on this artifact.
      4. INSERT into baseline_history (for_candidate, artifact_uid, promoted_at, reason).
      5. Recompute vs_baseline_score for every non-archived row in scope:
         - The new baseline gets vs_baseline_score = NULL.
         - Every other row gets a fresh compute against the new baseline's snapshot.
    """
    conn = open_db()
    try:
        scope_row = conn.execute(
            "SELECT for_candidate FROM resume_versions WHERE artifact_uid=?",
            (artifact_uid,),
        ).fetchone()
        if scope_row is None:
            raise ValueError(f"No resume_versions row for artifact_uid={artifact_uid!r}")
        for_candidate = scope_row[0]

        conn.execute(
            "UPDATE resume_versions SET is_baseline=0 "
            "WHERE is_baseline=1 AND archived_at IS NULL "
            "  AND ((? IS NULL AND for_candidate IS NULL) OR for_candidate = ?)",
            (for_candidate, for_candidate),
        )
        conn.execute(
            "UPDATE resume_versions SET is_baseline=1 WHERE artifact_uid=?",
            (artifact_uid,),
        )
        conn.execute(
            "INSERT INTO baseline_history (for_candidate, artifact_uid, promoted_at, reason) "
            "VALUES (?, ?, ?, ?)",
            (for_candidate, artifact_uid, _now_iso(), reason),
        )

        new_baseline_facts = _load_snapshot_facts(conn, artifact_uid)

        # Recompute every row in scope.
        rows = conn.execute(
            "SELECT artifact_uid FROM resume_versions "
            "WHERE archived_at IS NULL "
            "  AND ((? IS NULL AND for_candidate IS NULL) OR for_candidate = ?)",
            (for_candidate, for_candidate),
        ).fetchall()
        now = _now_iso()
        for (uid,) in rows:
            facts = _load_snapshot_facts(conn, uid)
            if facts is None:
                continue
            # vs_parent_score is unaffected by baseline promotion — preserve it.
            prev = conn.execute(
                "SELECT vs_parent_score FROM resume_drift_scores WHERE artifact_uid=?",
                (uid,),
            ).fetchone()
            vs_parent = prev[0] if prev else None
            if uid == artifact_uid:
                vs_baseline = None
            elif new_baseline_facts is not None:
                vs_baseline = json.dumps(
                    compute_drift_score(new_baseline_facts, facts)
                )
            else:
                vs_baseline = None
            conn.execute(
                "INSERT OR REPLACE INTO resume_drift_scores "
                "(artifact_uid, vs_parent_score, vs_baseline_score, computed_at) "
                "VALUES (?, ?, ?, ?)",
                (uid, vs_parent, vs_baseline, now),
            )
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_baseline.py -v
```

Expected: 4 PASS. Re-run full drift suite to check for regressions.

- [ ] **Step 5: Commit**

```bash
git add scripts/drift/baseline.py tests/drift/test_baseline.py
git commit -m "feat(drift): promote_baseline + transactional recompute of vs_baseline"
```

---

## Task 12: `extract_facts.py` — LLM-backed extractor

**Files:**

- Create: `scripts/drift/extract_facts.py`
- Test: `tests/drift/test_extract_facts.py`

This task uses the same Anthropic SDK already imported elsewhere in the skill. The SDK call is wrapped behind a `_call_llm(prompt)` private function that tests monkey-patch with a deterministic stub — no network calls in tests.

- [ ] **Step 1: Write the failing test**

```python
# tests/drift/test_extract_facts.py
"""LLM-backed fact extractor: validation, null-vs-[] semantics, implausibility."""
import pytest


SAMPLE_DOCX_TEXT = """\
Mathilda Gell
Rochedale, QLD  ·  mathilda@malin.com.au  ·  0433814874

Summary
Grade 10 student at Redeemer Lutheran College.

Skills
Customer engagement; Public speaking; Team leadership

Experience
Holiday Work — Faith Christian Distance Education
Brisbane, QLD  ·  January 2026
- Packed enrolment packs for school's intake.

Education
Redeemer Lutheran College — Rochedale, QLD
Grade 10 · Expected completion 2028

Hobbies
Netball, Archery, Tae Kwon Do
"""


VALID_EXTRACTED = {
    "identity": {"name": "Mathilda Gell", "location": "Rochedale, QLD",
                 "email": "mathilda@malin.com.au", "phone": "0433814874"},
    "experience": [{
        "entry_id": "exp-1", "employer": "Faith Christian Distance Education",
        "title": "Holiday Work", "start_date": "2026-01", "end_date": "2026-01",
        "location": "Brisbane, QLD",
        "key_points": ["Packed enrolment packs for school's intake."],
    }],
    "education": [{
        "entry_id": "edu-1", "institution": "Redeemer Lutheran College",
        "qualification": "Grade 10", "completion_year": "2028",
        "completion_status": "expected", "honours": [],
    }],
    "skills": ["Customer engagement", "Public speaking", "Team leadership"],
    "certifications": None,
    "standalone_achievements": None,
    "hobbies": ["Netball", "Archery", "Tae Kwon Do"],
    "languages": None,
    "publications": None,
    "portfolio_links": None,
}


def test_valid_extraction_round_trips(monkeypatch):
    from scripts.drift import extract_facts

    monkeypatch.setattr(extract_facts, "_call_llm",
                        lambda prompt: VALID_EXTRACTED)
    result = extract_facts.extract_facts_from_text(SAMPLE_DOCX_TEXT)
    assert result["identity"]["name"] == "Mathilda Gell"
    assert result["hobbies"] == ["Netball", "Archery", "Tae Kwon Do"]
    assert result["publications"] is None  # not mentioned in source


def test_invalid_extraction_missing_required_key_raises(monkeypatch):
    from scripts.drift import extract_facts

    bad = {k: v for k, v in VALID_EXTRACTED.items() if k != "identity"}
    monkeypatch.setattr(extract_facts, "_call_llm", lambda prompt: bad)
    with pytest.raises(extract_facts.FactExtractionError) as exc:
        extract_facts.extract_facts_from_text(SAMPLE_DOCX_TEXT)
    assert "identity" in str(exc.value)


def test_invalid_extraction_extra_key_raises(monkeypatch):
    from scripts.drift import extract_facts

    bad = {**VALID_EXTRACTED, "secret_field": "nope"}
    monkeypatch.setattr(extract_facts, "_call_llm", lambda prompt: bad)
    with pytest.raises(extract_facts.FactExtractionError):
        extract_facts.extract_facts_from_text(SAMPLE_DOCX_TEXT)


def test_invalid_extraction_wrong_type_raises(monkeypatch):
    from scripts.drift import extract_facts

    bad = {**VALID_EXTRACTED, "skills": "not a list"}
    monkeypatch.setattr(extract_facts, "_call_llm", lambda prompt: bad)
    with pytest.raises(extract_facts.FactExtractionError):
        extract_facts.extract_facts_from_text(SAMPLE_DOCX_TEXT)


def test_flag_implausible_values_catches_placeholders():
    from scripts.drift.extract_facts import flag_implausible_values

    facts = {**VALID_EXTRACTED}
    facts["identity"] = {**facts["identity"], "name": "John Doe"}
    flags = flag_implausible_values(facts)
    assert any("name" in f.lower() and "placeholder" in f.lower() for f in flags)


def test_flag_implausible_values_catches_invalid_dates():
    from scripts.drift.extract_facts import flag_implausible_values

    facts = {**VALID_EXTRACTED}
    facts["experience"] = [{**VALID_EXTRACTED["experience"][0], "start_date": "1899-01"}]
    flags = flag_implausible_values(facts)
    assert any("1899" in f for f in flags)


def test_flag_implausible_values_clean_returns_empty():
    from scripts.drift.extract_facts import flag_implausible_values
    assert flag_implausible_values(VALID_EXTRACTED) == []
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_extract_facts.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `extract_facts.py`**

```python
# scripts/drift/extract_facts.py
"""LLM-backed fact extraction for /brains-import.

Calls an LLM with a structured-output prompt, validates the result against
the Section 4 schema, and flags implausible values for user review.

The LLM call is isolated in _call_llm so tests can monkey-patch it. The
production implementation uses anthropic.Anthropic with model selection
read from the BRAINS_DRIFT_EXTRACT_MODEL env var (defaults to claude-haiku-4-5
for cost; can be bumped to sonnet for accuracy).
"""
from __future__ import annotations

import json
import os
import re


class FactExtractionError(Exception):
    """Raised when the LLM returns invalid or unparseable output."""


_EXTRACTION_SYSTEM_PROMPT = """\
You are a structured data extractor. Read the resume text and return a JSON
object matching the BRAINS Resume Skill fact schema v1.

The schema has 10 top-level keys. Each MUST be present. Use null (NOT []) when
the source text doesn't mention the category at all. Use [] only when the
source explicitly states the category is empty (e.g., "Languages: English only"
→ list with one entry; "Languages: none" → []).

Top-level keys:
- identity: object with {name, location, email, phone}. Use null for missing fields.
- experience: list of {entry_id, employer, title, start_date, end_date, location, key_points}.
  entry_id is "exp-N" numbered from 1. Dates in YYYY or YYYY-MM. key_points is a list of strings.
- education: list of {entry_id, institution, qualification, completion_year, completion_status, honours}.
  completion_status one of "completed", "expected", "in_progress", null.
- skills: list of strings, or null if the source has no skills section.
- certifications: list of {name, issuer, year} or null.
- standalone_achievements: list of strings (e.g. awards, recognitions) or null.
- hobbies: list of strings or null.
- languages: list of {language, proficiency} where proficiency is one of
  "native", "fluent", "professional", "conversational", "basic". Or null.
- publications: list of {title, venue, year, authors, url} or null.
  authors is a list of strings.
- portfolio_links: list of {label, url} or null.

Output ONLY the JSON object. No prose.
"""


_REQUIRED_KEYS = (
    "identity", "experience", "education", "skills",
    "certifications", "standalone_achievements", "hobbies",
    "languages", "publications", "portfolio_links",
)


def _call_llm(prompt: str) -> dict:
    """Make the actual Anthropic API call. Monkeypatched in tests.

    Returns the parsed JSON dict. Raises FactExtractionError on parse failure.
    """
    try:
        import anthropic
    except ImportError as e:
        raise FactExtractionError(f"anthropic SDK not installed: {e}")
    client = anthropic.Anthropic()
    model = os.environ.get("BRAINS_DRIFT_EXTRACT_MODEL", "claude-haiku-4-5-20251001")
    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=_EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text if resp.content else ""
    # Strip code fences if the model wrapped output.
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise FactExtractionError(f"LLM returned non-JSON output: {e}") from e


def _validate_schema(data: dict) -> None:
    """Strict shape validation. Raises FactExtractionError on any issue."""
    if not isinstance(data, dict):
        raise FactExtractionError("Expected top-level JSON object")
    missing = [k for k in _REQUIRED_KEYS if k not in data]
    if missing:
        raise FactExtractionError(f"Missing required keys: {missing}")
    extra = [k for k in data if k not in _REQUIRED_KEYS]
    if extra:
        raise FactExtractionError(f"Unexpected keys: {extra}")
    # Type checks.
    if data["identity"] is not None and not isinstance(data["identity"], dict):
        raise FactExtractionError("identity must be object or null")
    for k in ("experience", "education", "skills", "certifications",
              "standalone_achievements", "hobbies", "languages",
              "publications", "portfolio_links"):
        if data[k] is not None and not isinstance(data[k], list):
            raise FactExtractionError(f"{k} must be list or null, got {type(data[k]).__name__}")


_PLACEHOLDER_NAMES = {"john doe", "jane doe", "first last", "your name",
                      "fullname", "name here", "<name>"}
_PLACEHOLDER_EMAILS = {"example@example.com", "user@example.com",
                       "your.email@example.com", "<email>"}


def _looks_like_placeholder(value: str | None, vocab: set[str]) -> bool:
    if not value:
        return False
    return value.strip().lower() in vocab or "<" in value or "{{" in value


def flag_implausible_values(facts: dict) -> list[str]:
    """Return a list of human-readable warnings about likely-placeholder values.

    Used as a soft warning surface in the /brains-import workflow card.
    """
    flags: list[str] = []
    identity = facts.get("identity") or {}
    if _looks_like_placeholder(identity.get("name"), _PLACEHOLDER_NAMES):
        flags.append(
            f"identity.name looks like a placeholder: {identity.get('name')!r}"
        )
    if _looks_like_placeholder(identity.get("email"), _PLACEHOLDER_EMAILS):
        flags.append(
            f"identity.email looks like a placeholder: {identity.get('email')!r}"
        )
    # Experience / education dates outside [1900, 2100].
    for entry in (facts.get("experience") or []):
        for f in ("start_date", "end_date"):
            v = entry.get(f) or ""
            m = re.match(r"^(\d{4})", v)
            if m:
                year = int(m.group(1))
                if year < 1900 or year > 2100:
                    flags.append(
                        f"experience entry {entry.get('entry_id')!r} {f}={v!r} — year 1899 (looks suspicious)"
                        if year == 1899 else
                        f"experience entry {entry.get('entry_id')!r} {f}={v!r} — implausible year"
                    )
    return flags


def extract_facts_from_text(text: str) -> dict:
    """Extract a Section 4 fact dict from raw resume text via LLM.

    Validates strictly. Raises FactExtractionError on any failure.
    """
    if not text or not text.strip():
        raise FactExtractionError("Empty input text")
    data = _call_llm(text)
    _validate_schema(data)
    return data
```

- [ ] **Step 4: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/drift/test_extract_facts.py -v
```

Expected: all 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/drift/extract_facts.py tests/drift/test_extract_facts.py
git commit -m "feat(drift): extract_facts_from_text LLM extractor with strict validation"
```

---

## Task 13: Integrate `write_snapshot_and_compute_drift` into the 4 generator workflows

**Files:**

- Modify: `scripts/dashboard/workflows/create.py`, `edit.py`, `tailor.py`, `cover_letter.py`
- Test: `tests/dashboard/workflows/test_drift_integration.py` (new)

Each workflow card today builds a `target_path` + `meta` via `_resolve_target(...)` and renders the DOCX through a Claude Code handoff. The actual `add_resume_version` and `finalize_docx` calls happen inside Claude Code's slash command — *outside* the dashboard's Python. So the dashboard layer can't drop in the drift-compute call directly there.

Instead, this task adds a new public helper `scripts/drift/__init__.py::on_artifact_finalised(artifact_uid, workflow_data)` that the slash-command handoff prompt instructs Claude Code to call after `finalize_docx(target_path, meta)`. The helper:

1. Calls `facts_from_workflow_data(workflow_data)` to produce the snapshot.
2. Calls `write_snapshot_and_compute_drift(artifact_uid, facts)`.

The four workflow cards' `handoff_button` notes get a one-line addition reminding Claude Code to call `scripts.drift.on_artifact_finalised(meta.artifact_uid, data)` after save. The cover-letter workflow uses `kind="cover-letter"` and we skip snapshotting cover letters per spec §4 ("out of scope for v1") — but we still call `on_artifact_finalised` with a flag so the helper is the single integration point.

- [ ] **Step 1: Write the failing test**

```python
# tests/dashboard/workflows/test_drift_integration.py
"""End-to-end: on_artifact_finalised persists snapshot + drift after a render."""
import pytest

from scripts.tracker.add import add_resume_version
from scripts.tracker.db import open_db


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


SAMPLE_DATA = {
    "candidate_name": "Mathilda Gell",
    "candidate_contact_line": "Rochedale, QLD  ·  0433  ·  m@x.com",
    "summary": "...",
    "skills": "• A\n• B",
    "experience": "T — E\nB · 2024-01\n• X",
    "education": "I — L\nGrade",
}


def test_on_artifact_finalised_resume_writes_snapshot(fresh_db):
    from scripts.drift import on_artifact_finalised

    add_resume_version(None, "hybrid", [], artifact_uid="ABC",
                       for_candidate="Mathilda Gell")
    on_artifact_finalised("ABC", SAMPLE_DATA, kind="resume")

    conn = open_db()
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM resume_fact_snapshots WHERE artifact_uid=?",
            ("ABC",),
        ).fetchone()[0]
    finally:
        conn.close()
    assert n == 1


def test_on_artifact_finalised_cover_letter_no_snapshot(fresh_db):
    """Cover letters are out of scope for v1 — no snapshot written."""
    from scripts.drift import on_artifact_finalised

    add_resume_version(None, "hybrid", [], artifact_uid="CL", for_candidate="X")
    on_artifact_finalised("CL", SAMPLE_DATA, kind="cover-letter")

    conn = open_db()
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM resume_fact_snapshots WHERE artifact_uid=?",
            ("CL",),
        ).fetchone()[0]
    finally:
        conn.close()
    assert n == 0
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/workflows/test_drift_integration.py -v
```

Expected: ImportError on `scripts.drift.on_artifact_finalised`.

- [ ] **Step 3: Expose `on_artifact_finalised` from the package**

Replace `scripts/drift/__init__.py`:

```python
"""BRAINS Resume Skill — drift analytics package.

See docs/specs/2026-05-19-resume-drift-analytics-design.md.
"""
from typing import Literal


def on_artifact_finalised(
    artifact_uid: str,
    workflow_data: dict,
    kind: Literal["resume", "cover-letter"] = "resume",
) -> None:
    """Single integration point called by Claude Code after finalize_docx.

    For resumes: builds a snapshot from the workflow data and runs drift compute.
    For cover letters: no-op (out of scope for v1; see spec §4).
    """
    if kind != "resume":
        return
    from scripts.drift.snapshot_from_workflow import facts_from_workflow_data
    from scripts.drift.compute import write_snapshot_and_compute_drift
    facts = facts_from_workflow_data(workflow_data)
    write_snapshot_and_compute_drift(artifact_uid, facts)
```

- [ ] **Step 4: Update each workflow's `handoff_button` note**

For `scripts/dashboard/workflows/create.py`, `edit.py`, `tailor.py`, replace the existing `handoff_button` `note=...` text to append the new drift instruction. Example for `create.py`:

```python
    handoff_button(
        "create",
        [str(target_path), meta.artifact_uid],
        note=(
            "Open Claude Code; paste this command to start the interview. "
            "After save, call `scripts.outputs.io.finalize_docx(target_path, meta)`, "
            "register the new resume in the tracker with `for_candidate` set "
            "to the same value if provided, and call "
            "`scripts.drift.on_artifact_finalised(meta.artifact_uid, data)` "
            "to persist the fact snapshot and drift scores."
        ),
        key=f"{key_prefix}_btn",
    )
```

Apply analogous updates in `edit.py`, `tailor.py`. For `cover_letter.py`, the note mentions `kind="cover-letter"`:

```python
            "...call `scripts.drift.on_artifact_finalised(meta.artifact_uid, "
            "data, kind=\"cover-letter\")` — no-op for cover letters today, "
            "but uniform across workflows."
```

- [ ] **Step 5: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/workflows/test_drift_integration.py -v
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard -q
```

Expected: new tests PASS; pre-existing `test_workflows_tab_has_three_subheaders` is the only failing test (the known baseline).

- [ ] **Step 6: Commit**

```bash
git add scripts/drift/__init__.py scripts/dashboard/workflows/create.py scripts/dashboard/workflows/edit.py scripts/dashboard/workflows/tailor.py scripts/dashboard/workflows/cover_letter.py tests/dashboard/workflows/test_drift_integration.py
git commit -m "feat(drift): on_artifact_finalised integration hook + workflow note updates"
```

---

## Task 14: `drift_sparkline.py` — Overview tile data prep

**Files:**

- Create: `scripts/dashboard/prep/drift_sparkline.py`
- Test: `tests/dashboard/prep/test_drift_sparkline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/dashboard/prep/test_drift_sparkline.py
"""Drift trajectory sparkline prep."""
import json

import pytest

from scripts.drift.compute import write_snapshot_and_compute_drift
from scripts.tracker.add import add_resume_version
from scripts.tracker.db import open_db


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


def _seed_lineage():
    """Baseline + 3 derivatives with increasing drift on skills."""
    skills_list = [["A"], ["A", "B"], ["A", "B", "C"], ["A", "B", "C", "D"]]
    facts_template = {
        "identity": {"name": "X", "location": "Y", "email": "x@y", "phone": "0"},
        "experience": [], "education": [], "skills": ["A"],
        "certifications": None, "standalone_achievements": None,
        "hobbies": None, "languages": None, "publications": None,
        "portfolio_links": None,
    }
    uids = ["BL", "V2", "V3", "V4"]
    parents = [None, "BL", "V2", "V3"]
    for uid, parent, sk in zip(uids, parents, skills_list):
        add_resume_version(None, "hybrid", [], artifact_uid=uid,
                           parent_uid=parent, for_candidate="Test")
        write_snapshot_and_compute_drift(uid, {**facts_template, "skills": sk})
    return uids


def test_returns_n_most_recent(fresh_db):
    from scripts.dashboard.prep.drift_sparkline import drift_trajectory_last_n
    _seed_lineage()
    out = drift_trajectory_last_n({"for_candidate": "Test"}, n=3)
    assert len(out) == 3
    # Most-recent path — V2, V3, V4.
    assert [p["artifact_uid"] for p in out] == ["V2", "V3", "V4"]


def test_returns_all_when_fewer_than_n(fresh_db):
    from scripts.dashboard.prep.drift_sparkline import drift_trajectory_last_n
    _seed_lineage()
    out = drift_trajectory_last_n({"for_candidate": "Test"}, n=20)
    assert len(out) == 4
    assert out[0]["artifact_uid"] == "BL"
    assert out[0]["overall_pct"] is None  # baseline has no vs_baseline


def test_overall_pct_increases_with_drift(fresh_db):
    from scripts.dashboard.prep.drift_sparkline import drift_trajectory_last_n
    _seed_lineage()
    out = drift_trajectory_last_n({"for_candidate": "Test"}, n=4)
    # Skips baseline (overall_pct is None there); pct should increase across derivatives.
    pcts = [p["overall_pct"] for p in out if p["overall_pct"] is not None]
    assert pcts == sorted(pcts)


def test_empty_lineage_returns_empty(fresh_db):
    from scripts.dashboard.prep.drift_sparkline import drift_trajectory_last_n
    assert drift_trajectory_last_n({"for_candidate": "Nobody"}, n=12) == []
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/prep/test_drift_sparkline.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `drift_sparkline.py`**

```python
# scripts/dashboard/prep/drift_sparkline.py
"""Drift trajectory data prep for the Overview tile.

Pure function — returns a chart-ready list of {artifact_uid, created_at,
overall_pct} ordered oldest first. Streamlit/visualisation code reads it
directly without further transformation.
"""
from __future__ import annotations

import json
from typing import Optional

from scripts.drift.lineage import get_candidate_lineage
from scripts.tracker.db import open_db


def drift_trajectory_last_n(scope: dict, n: int = 12) -> list[dict]:
    """Return the last N non-archived resumes in the scope, with overall_pct."""
    lineage = get_candidate_lineage(scope)
    if not lineage:
        return []
    # Take the last n; sort oldest-first within that window.
    window = lineage[-n:]
    uids = [v.artifact_uid for v in window]
    placeholders = ",".join("?" * len(uids))
    conn = open_db()
    try:
        rows = conn.execute(
            f"SELECT artifact_uid, vs_baseline_score "
            f"FROM resume_drift_scores WHERE artifact_uid IN ({placeholders})",
            uids,
        ).fetchall()
    finally:
        conn.close()
    score_by_uid: dict = {}
    for uid, vs_baseline in rows:
        if vs_baseline is None:
            score_by_uid[uid] = None
        else:
            try:
                score_by_uid[uid] = json.loads(vs_baseline).get("overall_pct")
            except json.JSONDecodeError:
                score_by_uid[uid] = None
    return [
        {
            "artifact_uid": v.artifact_uid,
            "created_at": v.created_at,
            "overall_pct": score_by_uid.get(v.artifact_uid),
        }
        for v in window
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/prep/test_drift_sparkline.py -v
```

Expected: all 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard/prep/drift_sparkline.py tests/dashboard/prep/test_drift_sparkline.py
git commit -m "feat(dashboard): drift_trajectory_last_n prep for Overview sparkline"
```

---

## Task 15: Overview tab — drift trajectory tile

**Files:**

- Modify: `scripts/dashboard/tabs/overview.py`
- Test: `tests/dashboard/test_app_overview_render.py`

The existing Overview tab renders a set of summary tiles. Add a new tile for the active candidate's drift trajectory, sized to match the existing tiles. Per the user's stored memory entry, follow the TSE Tools visual vocabulary: dark theme, summary tile, sparkline, dense layout.

- [ ] **Step 1: Inspect the current Overview tab**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/test_app_overview_render.py -v
```

Read `scripts/dashboard/tabs/overview.py` end-to-end. Identify the current tile-layout pattern. The new tile will follow it.

- [ ] **Step 2: Append the failing test**

Append to `tests/dashboard/test_app_overview_render.py`:

```python
def test_overview_includes_drift_trajectory_tile(monkeypatch, tmp_path):
    """Overview renders a drift trajectory tile reading from drift_trajectory_last_n."""
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))

    from scripts.drift.compute import write_snapshot_and_compute_drift
    from scripts.tracker.add import add_resume_version
    from scripts.tracker.profile import write_profile
    from scripts.tracker.models import Profile

    write_profile(Profile(first_name="Matthew", last_name="Gell"))

    facts = {
        "identity": {"name": "Matthew Gell", "location": "X",
                     "email": "m@x", "phone": "0"},
        "experience": [], "education": [], "skills": ["A"],
        "certifications": None, "standalone_achievements": None,
        "hobbies": None, "languages": None, "publications": None,
        "portfolio_links": None,
    }
    add_resume_version(None, "hybrid", [], artifact_uid="BL")
    write_snapshot_and_compute_drift("BL", facts)
    add_resume_version(None, "hybrid", [], artifact_uid="V2", parent_uid="BL")
    write_snapshot_and_compute_drift("V2", {**facts, "skills": ["A", "B"]})

    # Streamlit AppTest: render the overview module's tile-building helper directly.
    from scripts.dashboard.tabs.overview import _drift_tile_summary
    summary = _drift_tile_summary({"for_candidate": None})
    # The most-recent (V2) drift, plus sparkline series.
    assert summary["headline_pct"] is not None
    assert isinstance(summary["sparkline"], list)
    assert len(summary["sparkline"]) >= 1
```

- [ ] **Step 3: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/test_app_overview_render.py -v -k drift
```

Expected: FAIL — `_drift_tile_summary` doesn't exist.

- [ ] **Step 4: Implement the tile**

Add to `scripts/dashboard/tabs/overview.py` (at the end of the file, in the same section as other tile helpers):

```python
def _drift_tile_summary(scope: dict) -> dict:
    """Pure helper: return the data the drift trajectory tile renders.

    Returns:
        headline_pct: float | None — overall_pct of the most-recent resume,
            or None if the most-recent IS the baseline or no scored resume exists.
        sparkline: list[float | None] — last 12 vs_baseline overall_pct values,
            oldest first, with None for the baseline row.
        headline_changes: list[str] — top headline_changes from the latest
            non-baseline score.
        count: int — number of resumes in the lineage.
    """
    from scripts.dashboard.prep.drift_sparkline import drift_trajectory_last_n

    points = drift_trajectory_last_n(scope, n=12)
    if not points:
        return {"headline_pct": None, "sparkline": [], "headline_changes": [], "count": 0}

    latest = points[-1]
    headline_pct = latest["overall_pct"]
    sparkline = [p["overall_pct"] for p in points]

    # Latest version's headline_changes (read from the stored score).
    import json
    from scripts.tracker.db import open_db
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


def render_drift_tile(scope: dict) -> None:
    """Render the drift trajectory tile in the Overview layout.

    Called from the main render() function alongside the other summary tiles.
    """
    import streamlit as st

    summary = _drift_tile_summary(scope)
    with st.container(border=True):
        st.caption("Drift from baseline · active candidate")
        if summary["headline_pct"] is None:
            st.markdown("**—**")
            st.caption("No baseline yet")
            return
        st.markdown(f"**{summary['headline_pct']:.1f}%**")
        if summary["sparkline"]:
            # Use Streamlit's line_chart for a minimal sparkline.
            import pandas as pd
            chart_data = pd.DataFrame({
                "drift": [v if v is not None else 0.0 for v in summary["sparkline"]],
            })
            st.line_chart(chart_data, height=60, use_container_width=True)
        if summary["headline_changes"]:
            st.caption(summary["headline_changes"][0])
```

Then call `render_drift_tile(scope)` from the existing top-level `render()` function in the same module, alongside whatever other tile-rendering calls already exist. The scope dict is built from `read_profile()` plus any active-candidate selection (pre-Approach-B, this is just `{"for_candidate": None}` for the profile holder, or `{"for_candidate": <name>}` if the sidebar lets users select).

- [ ] **Step 5: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard -q
```

Expected: only the pre-existing baseline failures remain.

- [ ] **Step 6: Commit**

```bash
git add scripts/dashboard/tabs/overview.py tests/dashboard/test_app_overview_render.py
git commit -m "feat(dashboard): Overview tile shows drift trajectory + headline"
```

---

## Task 16: Resumes tab — Drift columns

**Files:**

- Modify: `scripts/dashboard/tabs/resumes.py`
- Test: `tests/dashboard/test_resumes_tab.py` (new if it doesn't exist; otherwise extend)

Add two columns to the Resumes-tab table: "Drift vs parent" and "Drift vs baseline". Each shows `overall_pct` for the corresponding score (or `—` when the score is null/missing). Hover-on-cell shows the `headline_changes` list as a tooltip.

- [ ] **Step 1: Inspect the current Resumes tab**

Read `scripts/dashboard/tabs/resumes.py`. Identify the function that produces the per-resume row data for the table. Extract it (if not already extracted) into a pure helper like `_build_resume_rows(scope) -> list[dict]` so it's testable without Streamlit.

- [ ] **Step 2: Write the failing test**

Create `tests/dashboard/test_resumes_tab.py` (or extend the existing one):

```python
"""Resumes tab row builder includes drift columns."""
import json

import pytest

from scripts.drift.compute import write_snapshot_and_compute_drift
from scripts.tracker.add import add_resume_version


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path


def test_row_builder_includes_drift_columns(fresh_db):
    from scripts.dashboard.tabs.resumes import _build_resume_rows

    facts = {
        "identity": {"name": "X", "location": "Y", "email": "x@y", "phone": "0"},
        "experience": [], "education": [], "skills": ["A"],
        "certifications": None, "standalone_achievements": None,
        "hobbies": None, "languages": None, "publications": None,
        "portfolio_links": None,
    }
    add_resume_version(None, "hybrid", [], artifact_uid="BL", for_candidate="X")
    write_snapshot_and_compute_drift("BL", facts)
    add_resume_version(None, "hybrid", [], artifact_uid="V2",
                       parent_uid="BL", for_candidate="X")
    write_snapshot_and_compute_drift("V2", {**facts, "skills": ["A", "B"]})

    rows = _build_resume_rows({"for_candidate": "X"})
    by_uid = {r["artifact_uid"]: r for r in rows}

    # Baseline row: both drift values are '—' (None mapped to display dash).
    assert by_uid["BL"]["drift_vs_parent"] is None
    assert by_uid["BL"]["drift_vs_baseline"] is None
    # V2: skills 0→1 of 2 → 50%; identity etc unchanged.
    assert by_uid["V2"]["drift_vs_parent"] is not None
    assert by_uid["V2"]["drift_vs_baseline"] is not None
    assert by_uid["V2"]["headline_changes_vs_baseline"]  # at least one entry
```

- [ ] **Step 3: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/test_resumes_tab.py -v
```

Expected: ImportError or AttributeError on `_build_resume_rows`.

- [ ] **Step 4: Implement `_build_resume_rows`**

Replace the current row-construction code in `scripts/dashboard/tabs/resumes.py` with a pure helper + Streamlit-rendering split:

```python
def _build_resume_rows(scope: dict) -> list[dict]:
    """Build the per-resume row dicts for the Resumes-tab table.

    Each row includes the existing fields (file, created, template, jd) plus
    the new drift columns:
      - drift_vs_parent: float | None — overall_pct from vs_parent_score
      - drift_vs_baseline: float | None — overall_pct from vs_baseline_score
      - headline_changes_vs_parent: list[str]
      - headline_changes_vs_baseline: list[str]
    """
    import json
    from scripts.drift.lineage import get_candidate_lineage
    from scripts.tracker.db import open_db

    lineage = get_candidate_lineage(scope)
    if not lineage:
        return []
    uids = [v.artifact_uid for v in lineage if v.artifact_uid]
    if not uids:
        return [_resume_to_row_dict(v, None, None) for v in lineage]

    placeholders = ",".join("?" * len(uids))
    conn = open_db()
    try:
        score_rows = conn.execute(
            f"SELECT artifact_uid, vs_parent_score, vs_baseline_score "
            f"FROM resume_drift_scores WHERE artifact_uid IN ({placeholders})",
            uids,
        ).fetchall()
    finally:
        conn.close()
    by_uid = {}
    for uid, vp, vb in score_rows:
        by_uid[uid] = {
            "vs_parent": json.loads(vp) if vp else None,
            "vs_baseline": json.loads(vb) if vb else None,
        }
    out = []
    for v in lineage:
        scores = by_uid.get(v.artifact_uid or "", {"vs_parent": None, "vs_baseline": None})
        out.append(_resume_to_row_dict(v, scores.get("vs_parent"), scores.get("vs_baseline")))
    return out


def _resume_to_row_dict(rv, vs_parent, vs_baseline) -> dict:
    """Map a ResumeVersion + (optional) scores into a row dict for the table."""
    return {
        "artifact_uid": rv.artifact_uid,
        "file_path": rv.file_path,
        "template": rv.template,
        "created_at": rv.created_at,
        "tagged_jd_id": rv.tagged_jd_id,
        "drift_vs_parent": (vs_parent or {}).get("overall_pct"),
        "drift_vs_baseline": (vs_baseline or {}).get("overall_pct"),
        "headline_changes_vs_parent": (vs_parent or {}).get("headline_changes", []),
        "headline_changes_vs_baseline": (vs_baseline or {}).get("headline_changes", []),
    }
```

Then update the Streamlit-rendering section of `resumes.py` to consume `_build_resume_rows(scope)` and to add two new columns to the displayed DataFrame:

```python
def render(scope: dict | None = None) -> None:
    import streamlit as st
    import pandas as pd

    scope = scope or {"for_candidate": None}
    rows = _build_resume_rows(scope)
    if not rows:
        st.caption("No resumes for this candidate yet.")
        return

    df = pd.DataFrame([
        {
            "File": (r["file_path"] or "").split("\\")[-1].split("/")[-1],
            "Created": r["created_at"][:10],
            "Template": r["template"],
            "JD": r["tagged_jd_id"] or "—",
            "Drift vs parent": (f"{r['drift_vs_parent']:.1f}%"
                                if r["drift_vs_parent"] is not None else "—"),
            "Drift vs baseline": (f"{r['drift_vs_baseline']:.1f}%"
                                  if r["drift_vs_baseline"] is not None else "—"),
        }
        for r in rows
    ])
    st.dataframe(df, use_container_width=True)
```

(If the existing `render()` is more elaborate, keep its behaviour and just add the two columns to whatever DataFrame is built.)

- [ ] **Step 5: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard -q
```

Expected: only pre-existing baseline failures remain.

- [ ] **Step 6: Commit**

```bash
git add scripts/dashboard/tabs/resumes.py tests/dashboard/test_resumes_tab.py
git commit -m "feat(dashboard): Resumes tab gains Drift vs parent + Drift vs baseline columns"
```

---

## Task 17: Drift tab — full page

**Files:**

- Create: `scripts/dashboard/tabs/drift.py`
- Modify: `scripts/dashboard/app.py` (register the new tab)
- Test: `tests/dashboard/tabs/test_drift_tab_render.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/dashboard/tabs/test_drift_tab_render.py
"""Drift tab — lineage strip, per-fact-class table, field-level diff."""
import json

import pytest

from scripts.drift.compute import write_snapshot_and_compute_drift
from scripts.tracker.add import add_resume_version


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    return tmp_path


def _seed():
    facts = {
        "identity": {"name": "X", "location": "Y", "email": "x@y", "phone": "0"},
        "experience": [], "education": [], "skills": ["A"],
        "certifications": None, "standalone_achievements": None,
        "hobbies": None, "languages": None, "publications": None,
        "portfolio_links": None,
    }
    add_resume_version(None, "hybrid", [], artifact_uid="BL", for_candidate="X")
    write_snapshot_and_compute_drift("BL", facts)
    add_resume_version(None, "hybrid", [], artifact_uid="V2",
                       parent_uid="BL", for_candidate="X")
    write_snapshot_and_compute_drift("V2", {**facts, "skills": ["A", "B"]})


def test_lineage_data_for_strip(fresh_db):
    from scripts.dashboard.tabs.drift import _lineage_data
    _seed()
    data = _lineage_data({"for_candidate": "X"})
    assert data["baseline_uid"] == "BL"
    assert [n["artifact_uid"] for n in data["nodes"]] == ["BL", "V2"]
    assert data["nodes"][0]["is_baseline"] is True
    assert data["nodes"][1]["is_baseline"] is False


def test_selected_summary(fresh_db):
    from scripts.dashboard.tabs.drift import _selected_summary
    _seed()
    summary = _selected_summary("V2")
    assert summary["artifact_uid"] == "V2"
    assert summary["vs_parent_overall_pct"] is not None
    assert summary["vs_baseline_overall_pct"] is not None
    assert "skills" in summary["per_class_table"]


def test_field_level_changes_list(fresh_db):
    from scripts.dashboard.tabs.drift import _field_level_changes
    _seed()
    out = _field_level_changes("V2")
    # vs_baseline: skills [A] → [A,B] → set diff (added=["B"]).
    assert any("skill" in line.lower() and "B" in line for line in out)
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/tabs/test_drift_tab_render.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `drift.py`**

```python
# scripts/dashboard/tabs/drift.py
"""Drift tab — full-page deep dive.

Three pure data-builder helpers (testable without Streamlit) + render()
that composes them with Streamlit widgets.
"""
from __future__ import annotations

import json
from typing import Optional

from scripts.drift.lineage import get_candidate_lineage
from scripts.tracker.db import open_db


_CLASS_LABELS = {
    "identity": "Identity",
    "experience": "Experience",
    "education": "Education",
    "skills": "Skills",
    "certifications": "Certifications",
    "standalone_achievements": "Standalone achievements",
    "hobbies": "Hobbies",
    "languages": "Languages",
    "publications": "Publications",
    "portfolio_links": "Portfolio links",
}


def _lineage_data(scope: dict) -> dict:
    """Build the lineage strip data: nodes list + baseline_uid."""
    lineage = get_candidate_lineage(scope)
    nodes = [
        {
            "artifact_uid": v.artifact_uid,
            "created_at": v.created_at,
            "is_baseline": bool(
                _is_baseline_row(v.artifact_uid)
            ) if v.artifact_uid else False,
        }
        for v in lineage
    ]
    baseline_uid = next((n["artifact_uid"] for n in nodes if n["is_baseline"]), None)
    return {"nodes": nodes, "baseline_uid": baseline_uid}


def _is_baseline_row(artifact_uid: str) -> bool:
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT is_baseline FROM resume_versions WHERE artifact_uid=?",
            (artifact_uid,),
        ).fetchone()
    finally:
        conn.close()
    return bool(row and row[0])


def _load_scores(artifact_uid: str) -> tuple[Optional[dict], Optional[dict]]:
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT vs_parent_score, vs_baseline_score "
            "FROM resume_drift_scores WHERE artifact_uid=?",
            (artifact_uid,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None, None
    parent = json.loads(row[0]) if row[0] else None
    baseline = json.loads(row[1]) if row[1] else None
    return parent, baseline


def _selected_summary(artifact_uid: str) -> dict:
    """Build the 'Selected version summary' + per-class table."""
    vs_parent, vs_baseline = _load_scores(artifact_uid)
    per_class: dict = {}
    for cls in _CLASS_LABELS:
        per_class[cls] = {
            "label": _CLASS_LABELS[cls],
            "vs_parent_pct": (vs_parent or {}).get(cls, {}).get("pct"),
            "vs_baseline_pct": (vs_baseline or {}).get(cls, {}).get("pct"),
            "vs_parent_status": (vs_parent or {}).get(cls, {}).get("status"),
            "vs_baseline_status": (vs_baseline or {}).get(cls, {}).get("status"),
        }
    return {
        "artifact_uid": artifact_uid,
        "vs_parent_overall_pct": (vs_parent or {}).get("overall_pct"),
        "vs_baseline_overall_pct": (vs_baseline or {}).get("overall_pct"),
        "per_class_table": per_class,
    }


def _field_level_changes(artifact_uid: str) -> list[str]:
    """Flat list of field-level changes from both vs_parent and vs_baseline."""
    vs_parent, vs_baseline = _load_scores(artifact_uid)
    lines: list[str] = []
    for label, score in (("vs parent", vs_parent), ("vs baseline", vs_baseline)):
        if not score:
            continue
        for cls, info in score.items():
            if cls in ("overall_pct", "headline_changes"):
                continue
            if not isinstance(info, dict):
                continue
            for fc in info.get("field_changes", []) or []:
                lines.append(
                    f"{_CLASS_LABELS.get(cls, cls)} ({label}) · "
                    f"{fc.get('entry_id', '?')} · {fc['field']}: "
                    f"{fc.get('from')!r} → {fc.get('to')!r}"
                )
            for item in info.get("added", []) or []:
                lines.append(
                    f"{_CLASS_LABELS.get(cls, cls)} ({label}) · added: {item}"
                )
            for item in info.get("removed", []) or []:
                lines.append(
                    f"{_CLASS_LABELS.get(cls, cls)} ({label}) · removed: {item}"
                )
    # Dedupe while preserving order (vs_parent and vs_baseline may overlap).
    seen = set()
    out = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            out.append(line)
    return out


def render(scope: dict | None = None) -> None:
    import streamlit as st
    from scripts.drift.baseline import promote_baseline

    scope = scope or {"for_candidate": None}
    data = _lineage_data(scope)
    if not data["nodes"]:
        st.caption("No resumes for this candidate yet. Use /brains-import to upload a baseline.")
        return

    st.subheader(f"Drift · {scope.get('for_candidate') or 'profile holder'}")
    st.caption(f"Lineage: {len(data['nodes'])} versions · baseline {data['baseline_uid'] or '—'}")

    selected = st.selectbox(
        "Selected version",
        options=[n["artifact_uid"] for n in data["nodes"]],
        format_func=lambda u: f"{u} {'(baseline)' if u == data['baseline_uid'] else ''}",
        key="drift_selected_uid",
    )
    summary = _selected_summary(selected)
    st.markdown(
        f"**vs parent:** {(f'{summary[\"vs_parent_overall_pct\"]:.1f}%') if summary['vs_parent_overall_pct'] is not None else '—'}  ·  "
        f"**vs baseline:** {(f'{summary[\"vs_baseline_overall_pct\"]:.1f}%') if summary['vs_baseline_overall_pct'] is not None else '—'}"
    )

    if selected != data["baseline_uid"]:
        with st.expander("Make this my baseline"):
            reason = st.text_input("Why? (required)", key="drift_promote_reason")
            if st.button("Promote", key="drift_promote_btn") and reason.strip():
                promote_baseline(selected, reason.strip())
                st.success(f"{selected} is now the active baseline. Drift scores have been recalculated.")
                st.rerun()

    st.markdown("#### Per-fact-class")
    import pandas as pd
    df = pd.DataFrame([
        {
            "Class": v["label"],
            "vs parent": (f"{v['vs_parent_pct']:.1f}%" if v["vs_parent_pct"] is not None else "—"),
            "vs baseline": (f"{v['vs_baseline_pct']:.1f}%" if v["vs_baseline_pct"] is not None else "—"),
        }
        for v in summary["per_class_table"].values()
    ])
    st.dataframe(df, use_container_width=True)

    st.markdown("#### Field-level changes")
    for line in _field_level_changes(selected):
        st.write(f"- {line}")
```

- [ ] **Step 4: Register the tab in `app.py`**

In `scripts/dashboard/app.py`, find the existing top-tab nav (probably a `st.tabs([...])` call) and add `"Drift"` to the labels list and a call to `drift_tab.render(scope)` to the corresponding branch. Example diff:

```python
from scripts.dashboard.tabs import drift as drift_tab  # add to imports

# ...

tabs = st.tabs(["Overview", "Resumes", "Cover Letters", "Applications", "JDs", "Drift", "Workflows", "Analytics"])
# (Adjust the existing label list to match — append "Drift" before "Workflows".)

with tabs[5]:  # whichever index ends up corresponding to "Drift"
    drift_tab.render(scope)
```

(The exact index depends on the current ordering; check the file before editing.)

- [ ] **Step 5: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard -q
```

Expected: only pre-existing baseline failures remain.

- [ ] **Step 6: Commit**

```bash
git add scripts/dashboard/tabs/drift.py scripts/dashboard/app.py tests/dashboard/tabs/test_drift_tab_render.py
git commit -m "feat(dashboard): Drift tab with lineage strip, per-class table, field-level diff"
```

---

## Task 18: `/brains-import` workflow card + reference doc

**Files:**

- Create: `scripts/dashboard/workflows/import.py`
- Create: `references/workflows/import.md`
- Test: `tests/dashboard/workflows/test_import.py`

The new workflow lets a user upload an existing DOCX (or paste text) as the candidate's baseline. It runs the LLM extractor, surfaces implausibility flags for review, and on confirm writes the resume row + snapshot + drift scores.

- [ ] **Step 1: Write the failing test**

```python
# tests/dashboard/workflows/test_import.py
"""/brains-import workflow card — LLM-stubbed end-to-end."""
import pytest


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    from scripts.tracker.profile import write_profile
    from scripts.tracker.models import Profile
    write_profile(Profile(first_name="Matthew", last_name="Gell"))
    return tmp_path


VALID_FACTS = {
    "identity": {"name": "Matthew Gell", "location": "Brisbane, QLD",
                 "email": "m@gell.com", "phone": "0400000000"},
    "experience": [], "education": [], "skills": ["Python"],
    "certifications": None, "standalone_achievements": None,
    "hobbies": None, "languages": None, "publications": None,
    "portfolio_links": None,
}


def test_resolve_target_for_named_candidate(fresh_db):
    from scripts.dashboard.workflows.import_ import _resolve_target

    path, meta, for_candidate = _resolve_target(for_candidate="Mathilda Gell")
    assert "Mathilda" in path.name
    assert meta.for_candidate == "Mathilda Gell"
    assert for_candidate == "Mathilda Gell"


def test_resolve_target_falls_back_to_profile(fresh_db):
    from scripts.dashboard.workflows.import_ import _resolve_target

    path, meta, for_candidate = _resolve_target(for_candidate="")
    assert "Matthew" in path.name
    assert meta.for_candidate is None
    assert for_candidate is None


def test_commit_writes_row_snapshot_and_drift(monkeypatch, fresh_db):
    """The import commit path persists everything end-to-end."""
    from scripts.dashboard.workflows import import_ as import_mod
    from scripts.drift import extract_facts

    monkeypatch.setattr(extract_facts, "_call_llm", lambda prompt: VALID_FACTS)

    result = import_mod.run_import(
        source_text="Mathilda's resume text...",
        for_candidate="Mathilda Gell",
        confirm_despite_warnings=False,
    )
    assert result["status"] == "imported"
    assert result["artifact_uid"] is not None
    assert result["facts"]["identity"]["name"] == "Matthew Gell"  # from VALID_FACTS

    # Confirm DB rows.
    from scripts.tracker.db import open_db
    conn = open_db()
    try:
        rv = conn.execute(
            "SELECT artifact_uid, for_candidate, is_baseline "
            "FROM resume_versions WHERE artifact_uid=?",
            (result["artifact_uid"],),
        ).fetchone()
        snap = conn.execute(
            "SELECT COUNT(*) FROM resume_fact_snapshots WHERE artifact_uid=?",
            (result["artifact_uid"],),
        ).fetchone()[0]
    finally:
        conn.close()
    assert rv[1] == "Mathilda Gell"
    assert rv[2] == 1  # auto-baseline (first row for Mathilda)
    assert snap == 1


def test_commit_blocked_by_implausibility_unless_confirmed(monkeypatch, fresh_db):
    from scripts.dashboard.workflows import import_ as import_mod
    from scripts.drift import extract_facts

    bad = {**VALID_FACTS, "identity": {**VALID_FACTS["identity"], "name": "John Doe"}}
    monkeypatch.setattr(extract_facts, "_call_llm", lambda prompt: bad)

    result = import_mod.run_import(
        source_text="text",
        for_candidate="Mathilda Gell",
        confirm_despite_warnings=False,
    )
    assert result["status"] == "needs_confirmation"
    assert any("placeholder" in w.lower() for w in result["warnings"])
    assert result["artifact_uid"] is None

    # User confirms; import proceeds.
    result2 = import_mod.run_import(
        source_text="text",
        for_candidate="Mathilda Gell",
        confirm_despite_warnings=True,
    )
    assert result2["status"] == "imported"
```

- [ ] **Step 2: Run test to verify it fails**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/workflows/test_import.py -v
```

Expected: ImportError on `scripts.dashboard.workflows.import_`.

- [ ] **Step 3: Implement `import_.py`**

Note: `import` is a Python keyword so the module file is named `import_.py`. The reference doc still refers to the slash command as `/brains-import`.

```python
# scripts/dashboard/workflows/import_.py
"""/brains-import — upload a DOCX (or paste text) as a candidate's baseline.

The workflow runs the LLM-backed fact extractor, surfaces any implausibility
flags for user review, and on confirmation writes the resume_versions row
plus snapshot + drift scores.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st

from scripts.dashboard.workflows._card import handoff_button
from scripts.outputs.io import get_outputs_root, ProfileNameMissingError
from scripts.outputs.naming import artifact_filename, new_uid, split_candidate_name
from scripts.outputs.tagging import ArtifactMeta
from scripts.tracker.profile import read_profile


def _resolve_target(
    for_candidate: Optional[str] = None,
) -> Tuple[Path, ArtifactMeta, Optional[str]]:
    """Compute the output path + ArtifactMeta for an imported baseline.

    Imports always land in the _library directory (no JD anchor).
    """
    for_candidate = (for_candidate or "").strip() or None

    if for_candidate:
        first_name, last_name = split_candidate_name(for_candidate)
    else:
        profile = read_profile()
        if not profile.first_name or not profile.last_name:
            raise ProfileNameMissingError(
                "Set first and last name in the sidebar, or fill 'For candidate' above."
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
        skill_version="1.7.0",
        for_candidate=for_candidate,
    )
    return target_path, meta, for_candidate


def run_import(
    source_text: str,
    for_candidate: Optional[str],
    confirm_despite_warnings: bool,
) -> dict:
    """Pure-Python entry point used by the Streamlit card AND by tests.

    Returns one of:
      {'status': 'imported', 'artifact_uid': '...', 'facts': {...}, 'warnings': []}
      {'status': 'needs_confirmation', 'artifact_uid': None, 'facts': {...}, 'warnings': [...]}
      {'status': 'error', 'message': '...', 'artifact_uid': None}
    """
    from scripts.drift.extract_facts import (
        extract_facts_from_text, flag_implausible_values, FactExtractionError,
    )
    from scripts.drift.compute import write_snapshot_and_compute_drift
    from scripts.tracker.add import add_resume_version

    try:
        facts = extract_facts_from_text(source_text)
    except FactExtractionError as e:
        return {"status": "error", "message": str(e), "artifact_uid": None}

    warnings = flag_implausible_values(facts)
    if warnings and not confirm_despite_warnings:
        return {
            "status": "needs_confirmation",
            "artifact_uid": None,
            "facts": facts,
            "warnings": warnings,
        }

    path, meta, resolved_for = _resolve_target(for_candidate=for_candidate)
    add_resume_version(
        file_path=str(path),
        template="imported",
        focus_areas=[],
        artifact_uid=meta.artifact_uid,
        for_candidate=resolved_for,
    )
    write_snapshot_and_compute_drift(meta.artifact_uid, facts)
    return {
        "status": "imported",
        "artifact_uid": meta.artifact_uid,
        "facts": facts,
        "warnings": warnings,
    }


def render(file_path: Optional[Path] = None, key_prefix: str = "import") -> None:
    st.markdown("**Import an existing resume as a baseline.**")
    st.caption("Upload a DOCX or paste text. The LLM extractor will produce a fact snapshot you can review before committing.")

    for_candidate = st.text_input(
        "For candidate (optional — leave blank for yourself)",
        key=f"{key_prefix}_for_candidate",
    )
    source_text = st.text_area(
        "Resume text (paste the plain-text content of the DOCX here)",
        key=f"{key_prefix}_source",
        height=300,
    )
    confirm = st.checkbox(
        "I have reviewed the warnings below and want to import anyway",
        key=f"{key_prefix}_confirm",
    )

    if st.button("Import baseline", key=f"{key_prefix}_btn"):
        if not source_text.strip():
            st.warning("Paste some resume text first.")
            return
        result = run_import(
            source_text=source_text,
            for_candidate=for_candidate,
            confirm_despite_warnings=confirm,
        )
        if result["status"] == "error":
            st.error(result["message"])
            return
        if result["status"] == "needs_confirmation":
            st.warning("Implausible values detected — review and confirm to proceed:")
            for w in result["warnings"]:
                st.write(f"- {w}")
            return
        st.success(
            f"Imported baseline with artifact_uid={result['artifact_uid']!r}. "
            "It is now the active baseline for this candidate."
        )
```

- [ ] **Step 4: Write the reference doc**

```markdown
<!-- references/workflows/import.md -->
# /brains-import — Import an existing resume as a baseline

**Purpose:** Add an existing resume to the BRAINS Resume Skill as a candidate's *baseline* — the source-of-truth professional-identity record that future tailored resumes are drift-compared against.

## When to use

- A user has a polished resume they want to track from this point forward.
- A user wants to upload a known-good historical version of their resume to serve as the baseline for drift analytics.
- A user is helping someone else (parent → teenager) and wants to register that person's existing resume as their baseline.

## Inputs

1. **Source text** — the plain-text content of the DOCX. The user can paste it directly or upload a DOCX (parsed via `scripts/parsers/docx_to_text.py`).
2. **For candidate (optional)** — the name of the person this resume is FOR, if not the profile holder. Same `for_candidate` mechanism as `/brains-create`, `/brains-tailor`, etc.

## Procedure

1. Run `scripts.drift.extract_facts.extract_facts_from_text(text)` to produce a Section-4 fact dict via LLM extraction.
2. Run `scripts.drift.extract_facts.flag_implausible_values(facts)` to flag placeholder names, invalid dates, suspicious values.
3. If any flags exist, present them to the user and require explicit confirmation before continuing.
4. Resolve the output path via `scripts.dashboard.workflows.import_._resolve_target(for_candidate=...)` — imports land in the `_library/` directory and are stamped with a fresh UID.
5. Call `add_resume_version(...)` with `template="imported"`, `for_candidate=<name>`, the new UID, and no parent.
6. Call `write_snapshot_and_compute_drift(artifact_uid, facts)`. As the first row in this candidate's scope, `is_baseline=1` is set automatically by `add_resume_version`; `vs_parent_score` and `vs_baseline_score` are both NULL.

## Output

- A `resume_versions` row with `is_baseline=1`, `template="imported"`, `for_candidate=<name>` or NULL.
- A `resume_fact_snapshots` row keyed by the new `artifact_uid`.
- A `resume_drift_scores` row with both score columns NULL.

## Boundaries

- The original DOCX file is not stored in `_library/` — only its parsed fact snapshot. The user keeps the source file wherever they uploaded from.
- Schema-validation failures and LLM parse errors surface to the user with the raw LLM output. No partial writes.
- Implausibility flags are soft — the user can confirm and proceed if the flagged values are actually correct (e.g., a stage name "Cher" trips the placeholder-name heuristic; user confirms and it imports).
- Hobbies, languages, publications, portfolio links are all captured by the LLM extractor when present in the source. When absent from the source, the extractor returns `null` for those classes (not `[]`).

## See also

- `docs/specs/2026-05-19-resume-drift-analytics-design.md` — full design.
- `references/workflows/create.md` — for the generated-resume path; baselines can also be generated rather than imported.
```

- [ ] **Step 5: Register the workflow card in the dashboard**

In `scripts/dashboard/tabs/workflows.py` (or wherever the workflow cards are listed), add a row for the new card. Example:

```python
from scripts.dashboard.workflows import import_ as import_workflow
# ...
with col:
    import_workflow.render(key_prefix="import")
```

(The exact integration point depends on the existing workflows tab layout; preserve the existing structure.)

- [ ] **Step 6: Run tests to verify they pass**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard/workflows/test_import.py -v
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/dashboard -q
```

Expected: new tests PASS; pre-existing baseline failures only.

- [ ] **Step 7: Commit**

```bash
git add scripts/dashboard/workflows/import_.py references/workflows/import.md tests/dashboard/workflows/test_import.py
git commit -m "feat(dashboard): /brains-import workflow card + LLM-extracted baseline import"
```

---

## Task 19: End-to-end smoke test

**Files:**

- Create: `tests/test_smoke_drift_end_to_end.py`

A single integration test that exercises the whole pipeline: import a baseline via `run_import` (with stubbed LLM), generate a derivative resume via the workflow data dict + `on_artifact_finalised`, assert the drift scores are correct end-to-end.

- [ ] **Step 1: Write the test**

```python
# tests/test_smoke_drift_end_to_end.py
"""End-to-end smoke for v1.7.0 — import baseline → derivative → drift correctness."""
import json

import pytest

from scripts.tracker.db import open_db


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    from scripts.tracker.profile import write_profile
    from scripts.tracker.models import Profile
    write_profile(Profile(first_name="Matthew", last_name="Gell"))
    return tmp_path


def test_drift_pipeline_end_to_end(monkeypatch, isolated):
    """Mathilda baseline imported → /brains-tailor derivative → drift scores."""
    from scripts.dashboard.workflows import import_ as import_mod
    from scripts.drift import extract_facts, on_artifact_finalised
    from scripts.tracker.add import add_resume_version

    BASELINE_FACTS = {
        "identity": {"name": "Mathilda Gell", "location": "Rochedale, QLD",
                     "email": "m@x", "phone": "0433814874"},
        "experience": [{
            "entry_id": "exp-1", "employer": "Faith Christian Distance Education",
            "title": "Holiday Work", "start_date": "2026-01", "end_date": "2026-01",
            "location": "Brisbane, QLD",
            "key_points": ["Packed enrolment packs."],
        }],
        "education": [{
            "entry_id": "edu-1", "institution": "Redeemer Lutheran College",
            "qualification": "Grade 10", "completion_year": "2028",
            "completion_status": "expected", "honours": [],
        }],
        "skills": ["Customer engagement", "Public speaking", "Team leadership"],
        "certifications": [{"name": "Black Belt Tae Kwon Do",
                            "issuer": None, "year": None}],
        "standalone_achievements": ["Netball MVP 2025"],
        "hobbies": ["Netball", "Archery", "Tae Kwon Do"],
        "languages": [{"language": "English", "proficiency": "native"}],
        "publications": None,
        "portfolio_links": None,
    }
    monkeypatch.setattr(extract_facts, "_call_llm", lambda prompt: BASELINE_FACTS)

    # 1. Import the baseline.
    result = import_mod.run_import(
        source_text="Mathilda's baseline resume text",
        for_candidate="Mathilda Gell",
        confirm_despite_warnings=False,
    )
    assert result["status"] == "imported"
    baseline_uid = result["artifact_uid"]

    # 2. Generate a derivative (simulated workflow handoff).
    derivative_data = {
        "candidate_name": "Mathilda Gell",
        "candidate_contact_line": "Brisbane, QLD  ·  0433814874  ·  m@x",
        "summary": "...",
        "skills": "• Customer engagement\n• Public speaking",  # one skill removed
        "experience": (
            "Holiday Work — Faith Christian Distance Education\n"
            "Brisbane, QLD  ·  January 2026\n"
            "• Packed enrolment packs."
        ),
        "education": (
            "Redeemer Lutheran College — Rochedale, QLD\n"
            "Grade 10  ·  Expected completion 2028"
        ),
    }
    add_resume_version(None, "hybrid", [], artifact_uid="DERIV",
                       parent_uid=baseline_uid, for_candidate="Mathilda Gell")
    on_artifact_finalised("DERIV", derivative_data, kind="resume")

    # 3. Assert drift compute results.
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT vs_parent_score, vs_baseline_score "
            "FROM resume_drift_scores WHERE artifact_uid=?", ("DERIV",),
        ).fetchone()
    finally:
        conn.close()
    vs_parent = json.loads(row[0])
    vs_baseline = json.loads(row[1])

    # Identity: location changed from Rochedale → Brisbane → 1/4 = 25%.
    assert vs_parent["identity"]["pct"] == 25.0
    # Skills: Team leadership removed → 1/3 = ~33%.
    assert vs_parent["skills"]["pct"] == pytest.approx(33.333333, abs=0.01)
    # Hobbies / languages / certifications / standalone_achievements are
    # null in the derivative (workflow doesn't capture them) → skipped.
    for cls in ("hobbies", "languages", "certifications", "standalone_achievements"):
        assert vs_parent[cls] == {"status": "not_captured", "pct": None}
    # Overall renormalised across identity + experience + education + skills.
    assert vs_parent["overall_pct"] is not None
    assert vs_parent["overall_pct"] > 0.0
    # vs_baseline matches vs_parent because parent IS the baseline.
    assert vs_baseline["overall_pct"] == vs_parent["overall_pct"]


def test_promote_baseline_recompute_end_to_end(monkeypatch, isolated):
    """Promote V2 → V3's vs_baseline_score recomputes against V2's facts."""
    from scripts.drift import extract_facts
    from scripts.drift.baseline import promote_baseline
    from scripts.drift.compute import write_snapshot_and_compute_drift
    from scripts.tracker.add import add_resume_version

    facts_a = {
        "identity": {"name": "X", "location": "Q", "email": "x@y", "phone": "0"},
        "experience": [], "education": [], "skills": ["A"],
        "certifications": None, "standalone_achievements": None,
        "hobbies": None, "languages": None, "publications": None,
        "portfolio_links": None,
    }
    facts_b = {**facts_a, "skills": ["A", "B"]}
    facts_c = {**facts_a, "skills": ["A", "B", "C"]}

    add_resume_version(None, "hybrid", [], artifact_uid="A", for_candidate="X")
    write_snapshot_and_compute_drift("A", facts_a)
    add_resume_version(None, "hybrid", [], artifact_uid="B",
                       parent_uid="A", for_candidate="X")
    write_snapshot_and_compute_drift("B", facts_b)
    add_resume_version(None, "hybrid", [], artifact_uid="C",
                       parent_uid="B", for_candidate="X")
    write_snapshot_and_compute_drift("C", facts_c)

    # Before promotion: C's vs_baseline_score is computed against A.
    conn = open_db()
    try:
        before = conn.execute(
            "SELECT vs_baseline_score FROM resume_drift_scores WHERE artifact_uid='C'"
        ).fetchone()
    finally:
        conn.close()
    before_pct = json.loads(before[0])["skills"]["pct"]
    # A→C: skills [A] → [A,B,C] → 2 added of 3 = ~66.7%.
    assert before_pct == pytest.approx(66.666666, abs=0.01)

    # Promote B.
    promote_baseline("B", reason="Real-life change")

    # After: C's vs_baseline_score is against B.
    conn = open_db()
    try:
        after = conn.execute(
            "SELECT vs_baseline_score FROM resume_drift_scores WHERE artifact_uid='C'"
        ).fetchone()
    finally:
        conn.close()
    after_pct = json.loads(after[0])["skills"]["pct"]
    # B→C: skills [A,B] → [A,B,C] → 1 added of 3 = ~33%.
    assert after_pct == pytest.approx(33.333333, abs=0.01)
```

- [ ] **Step 2: Run the test**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest tests/test_smoke_drift_end_to_end.py -v
```

Expected: both tests PASS.

- [ ] **Step 3: Run the full suite for regressions**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest -q
```

Expected: only the 2 pre-existing baseline failures (`test_workflows_tab_has_three_subheaders`, `test_weekly_summary_pacing_none_when_no_target`).

- [ ] **Step 4: Commit**

```bash
git add tests/test_smoke_drift_end_to_end.py
git commit -m "test: end-to-end smoke for v1.7.0 drift analytics"
```

---

## Task 20: Version bump + CHANGELOG

**Files:**

- Modify: `scripts/outputs/io.py` (`_SKILL_VERSION`)
- Modify: `pyproject.toml`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Bump `_SKILL_VERSION`**

In `scripts/outputs/io.py`, change `_SKILL_VERSION = "1.6.0"` to `_SKILL_VERSION = "1.7.0"`.

Also check `scripts/dashboard/workflows/create.py`, `edit.py`, `tailor.py`, `cover_letter.py` for any leftover hardcoded `"1.6.0"` literals (Plan C cleaned these up in commit `43aeb15`, but it's worth re-checking the library-fallback `ArtifactMeta` calls). If any are found, replace them with `from scripts.outputs.io import _SKILL_VERSION` and use the constant.

Also: in `scripts/dashboard/workflows/import_.py`, the `_resolve_target` builds an `ArtifactMeta` with `skill_version="1.7.0"` — replace this literal with `_SKILL_VERSION` via the same import to keep version-coupling in one place.

- [ ] **Step 2: Bump `pyproject.toml`**

In `pyproject.toml`, change `version = "1.6.0"` to `version = "1.7.0"`.

- [ ] **Step 3: Update CHANGELOG**

Add at the top of `CHANGELOG.md`, above the v1.6.0 entry:

```markdown
## v1.7.0 — 2026-XX-XX

### Added
- **Resume drift analytics** — per-fact-class drift scoring across the existing
  `artifact_uid` + `parent_uid` lineage. Tracks how far each tailored resume has
  moved from (a) its immediate parent and (b) the candidate's current baseline.
- Ten fact classes captured per snapshot: identity, experience, education,
  skills, certifications, standalone achievements, hobbies, languages,
  publications, portfolio links. The fact schema is deliberately broader than
  any single resume so the baseline acts as a "professional-identity record."
- New tables: `resume_fact_snapshots` (artifact_uid → fact JSON),
  `resume_drift_scores` (artifact_uid → vs_parent + vs_baseline JSON),
  `baseline_history` (audit log of baseline promotions).
- New column on `resume_versions`: `is_baseline`. Exactly one active baseline
  per candidate, enforced by a partial unique index.
- New module `scripts/drift/` containing `snapshot_from_workflow`, `compute`,
  `lineage`, `baseline`, `extract_facts`, `formatters`.
- New slash command **`/brains-import`** for uploading an existing DOCX as the
  candidate's baseline. The LLM-backed extractor produces the structured fact
  snapshot; implausible values are flagged for review before commit.
- Dashboard:
  - Drift trajectory tile on the Overview tab (active candidate's
    drift-from-baseline sparkline + headline drift %).
  - "Drift vs parent" and "Drift vs baseline" sortable columns on the
    Resumes tab.
  - New top-level **Drift tab** with lineage strip, per-fact-class table,
    field-level diff, and "Make this my baseline" promotion.

### Changed
- `add_resume_version` now auto-sets `is_baseline=1` for the first non-archived
  row in each candidate scope. Override with `is_baseline=False` if needed.
- `_SKILL_VERSION` bumped to `"1.7.0"`. New artifacts stamp the new version
  into the `BrainsSkillVersion` DOCX custom property.

### Migration
- Migration `0004_drift_analytics` runs automatically on first `open_db()`
  after upgrade. The backfill marks the oldest non-archived row per
  `for_candidate` scope as the active baseline. No snapshots are backfilled
  for pre-existing resumes — they show `—` in the drift columns until either
  (a) the user runs `/brains-import` on them, or (b) a future batch-backfill
  job extracts facts from the historical DOCX files.

### Notes
- This is preparatory for Approach B (proper `candidates` table) — when that
  ships, `baseline_history.for_candidate` migrates to `candidate_id`
  alongside the rest of the candidate-scoped columns. Snapshot and drift-score
  tables are unaffected (UID-keyed).
- Cover letters do NOT get snapshots in v1.7.0 — derivative artifacts, low
  signal value. Out of scope per design spec §4.
- PDF metadata still doesn't carry artifact UIDs — same pre-existing gap as
  v1.5.0/1.6.0.
```

- [ ] **Step 4: Run the full suite for final sanity check**

```text
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -m pytest -q
```

Expected: only the 2 pre-existing baseline failures.

- [ ] **Step 5: Commit**

```bash
git add scripts/outputs/io.py scripts/dashboard/workflows/import_.py pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 1.7.0 + CHANGELOG entry for drift analytics"
```

---

## Acceptance Criteria

A. `pytest -q` is green across the full suite except the 2 pre-existing baseline failures (`test_workflows_tab_has_three_subheaders`, `test_weekly_summary_pacing_none_when_no_target`).

B. **End-to-end smoke** (`tests/test_smoke_drift_end_to_end.py`) passes: a baseline import via `run_import` followed by a derivative-resume generation produces correct drift scores against both parent and baseline, with null-class semantics correctly preserving the renormalised `overall_pct`.

C. **Migration safety**: an existing v1.6.0 install opened by a v1.7.0 build runs migration 0004 cleanly. The oldest non-archived row per `for_candidate` scope is marked `is_baseline=1`. The partial unique index allows multiple `is_baseline=0` rows per scope and exactly one `is_baseline=1` row per scope.

D. **Forward-compat**: a DOCX file written by a v1.6.0 build (no `BrainsForCandidate` property absent — already handled by Plan C; no `BrainsSkillVersion=1.7.0` either) reads cleanly under v1.7.0 with `for_candidate=None` and the older skill version preserved in its custom properties. (Drift just shows `—` until the user `/brains-import`s the file.)

E. **Baseline promotion**: calling `promote_baseline(uid, reason)` in a candidate scope flips `is_baseline=1` exactly to the targeted row, appends an audit row to `baseline_history`, and recomputes every non-archived resume's `vs_baseline_score` against the new baseline's snapshot in the same transaction.

F. **Mathilda's V9MQZX is now her baseline.** After merge, manually run:

```python
"c:\Brains_Resume_Skill\.venv\Scripts\python.exe" -c "
import sys; sys.path.insert(0, r'c:\Brains_Resume_Skill')
from scripts.tracker.db import open_db
conn = open_db()
try:
    conn.execute(\"UPDATE resume_versions SET is_baseline=1 WHERE artifact_uid='V9MQZX'\")
    conn.commit()
finally:
    conn.close()
"
```

Then re-extract her facts from the saved DOCX via `/brains-import` (or, if the DOCX is already on disk and already has an artifact row, write the snapshot directly using the workflow data dict that produced it). The Drift tab then shows Mathilda's baseline with `headline_pct=0` and no derivatives yet.

---

## Self-Review

**Spec coverage.** Each section of the spec maps to a task or tasks:

- §3 (Architecture) → Task 1 (migration), Task 13 (workflow integration hook)
- §4 (Fact schema) → Task 3 (snapshot_from_workflow), Task 12 (extract_facts)
- §5 (Drift formula) → Tasks 4, 5, 6, 7 (compute split by class shape), Task 8 (formatters)
- §6 (Baseline policy) → Task 2 (auto-baseline-on-first-row), Task 11 (promote_baseline + audit + recompute)
- §7 (Dashboard surfaces) → Tasks 14 (sparkline), 15 (Overview tile), 16 (Resumes tab), 17 (Drift tab)
- §8 (Compute pipeline) → Task 10 (writer integration), Task 13 (workflow integration)
- §9 (Edge cases) — exercised throughout: 9.1, 9.2 (lineage null-snapshot path), 9.4 (archived-skip in lineage walker), 9.5 (extract_facts error path), 9.6 (implausibility), 9.7 (lineage forks — Task 9 walks most-recent path), 9.8 (cycle guard — Task 9), 9.13 (natural-key collision — Task 6), 9.14 (active baseline archived — Task 11 + Task 15 empty state), 9.15-9.17 (null vs [] — Tasks 4, 5, 6, 7, 12). 9.10 (Approach B interaction) is documented but not implemented here. 9.12 (schema evolution) is forward-compat scaffolding only — schema_version=1 ships, no migration logic for >1 because no v2 exists.
- §10 (Test strategy) → tests across Tasks 1-19; the suggested file split from the spec maps 1:1 to the tests files this plan creates.
- §11 (Open questions) — Task 14 picks `prep/drift_sparkline.py` location. Task 16 leaves the "•" prefix threshold UI out of scope for v1 (per spec). Task 12 uses `BRAINS_DRIFT_EXTRACT_MODEL` env var defaulting to `claude-haiku-4-5-20251001` for the LLM model choice. Task 18 ships the `/brains-import` card.
- §12 (Implementation order) — this plan follows it: migration → drift module → workflow hook → /brains-import → dashboard → smoke → version bump.

**Placeholder scan.** Every step has a complete code block or exact text. No "TBD" / "implement later" / "similar to Task N without code". The cover-letter workflow note text is the only place that intentionally refers to a no-op call site; that's documented behaviour, not a placeholder. Task 16's render() is shortened to "or whatever the existing render is — keep it and add columns" — that's explicit context-handing, not a placeholder.

**Type consistency.**

- `compute_class_diff(left, right, kind: str)` returns a dict with shape determined by `kind` — set kinds return `{added, removed, total, pct}`, identity returns `{fields_changed, fields_total, pct}`, list-of-object returns `{entries_added, entries_removed, entries_with_field_changes, field_changes, entries_total, pct}`. Null-on-either-side returns `{status: "not_captured", pct: null}`. Used consistently across Tasks 4-8.
- `compute_drift_score(left, right) -> dict` with 10 class keys + `overall_pct` + `headline_changes`. Used in Tasks 7, 8, 10, 11.
- `write_snapshot_and_compute_drift(artifact_uid: str, facts: dict) -> None`. Used in Tasks 10, 11, 13, 18, 19.
- `on_artifact_finalised(artifact_uid: str, workflow_data: dict, kind: Literal["resume", "cover-letter"]="resume") -> None`. Used in Task 13, 19.
- `promote_baseline(artifact_uid: str, reason: str) -> None`. Used in Tasks 11, 17, 19.
- `get_parent_snapshot(artifact_uid: str) -> dict | None`, `get_baseline_snapshot(artifact_uid: str) -> dict | None`, `get_candidate_lineage(scope: dict) -> list[ResumeVersion]`. Used in Tasks 9, 10, 14, 16, 17.
- Fact schema (Section 4 of spec) is the single source of truth for the structure used in every snapshot and every diff result.

No drift between task signatures.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-19-resume-drift-analytics-implementation.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, two-stage review between tasks, fast iteration. Same approach used successfully for the v1.6.0 Plan C ship.
2. **Inline Execution** — execute tasks in the current session using executing-plans, batch execution with checkpoints.

Which approach?
