# Resume Drift Analytics — Design

**Status:** Approved by user 2026-05-19; ready for implementation planning.
**Author:** Brainstormed with Claude (Opus 4.7) in conversation with Matthew Gell on 2026-05-19.
**Prerequisites:** Multi-candidate support Approach C (v1.6.0) is merged. This design is designed to be installed on top of v1.6.0 and to coexist cleanly with the future Approach B (`candidates` table) migration.
**Target release:** v1.7.0 of the BRAINS Resume Skill.

---

## 1. Motivation

The BRAINS Resume Skill already tracks a complete lineage of every resume via `artifact_uid` + `parent_uid` (v1.5.0) and groups lineages per person via `for_candidate` (v1.6.0). What's missing is a metric for **how much the FACTS in a resume have drifted** from the user's original baseline as the resume gets repeatedly tailored, edited, and recycled across applications.

The driving concern is **factual accuracy**: when a user tailors a resume across dozens of applications, role titles get reworded, dates get nudged to fit narratives, achievements get reframed, and over time the cumulative drift can carry the resume away from what's actually true. For ND users in particular — who may rely on the resume itself as an external record of their work history — silent drift erodes a load-bearing memory artifact.

This design ships an analytic that:

1. Captures a structured fact snapshot of every resume at render time (free for resumes the skill generates; LLM-extracted for uploaded baselines).
2. Computes per-fact-class drift scores against (a) the immediate parent and (b) the candidate's current baseline.
3. Surfaces drift across three dashboard layers — an Overview tile, a Resumes-tab column, and a dedicated Drift tab with per-fact diffs.
4. Lets the user promote a new baseline when real life moves on (new job, completed degree).

Editorial drift (rephrase rate, restructure count) is **out of scope for v1**; the design accommodates it as a future addition but does not implement it.

---

## 2. Decisions

The brainstorm landed these specific decisions:

| Decision | Choice | Rationale |
|---|---|---|
| Primary purpose | **Factual drift** | The user-facing question is "is this still TRUE to the baseline?" Editorial drift is interesting but secondary. |
| Granularity | **Per-fact-class** | Answers "which kind of fact moved?" directly. Most informative for the dashboard. |
| Comparison base | **Both parent and baseline** | Two independent signals: incremental edit health vs cumulative decay. |
| Baseline mutability | **User-promotable** | First upload is the default baseline; user can promote any later version when reality legitimately diverges (new job, completed degree). Locked baselines would degrade in usefulness; auto-rebaselining would risk re-baselining drift-corrupted content. |
| Surfacing posture | **Informational, no automatic warnings** | Matches the skill's existing user-veto-is-absolute stance. Drift is shown; the user decides. |
| Compute trigger | **Eager at render** | Snapshot writes at render time are free for generated resumes; drift compute is pure-Python diff. No reason to defer. |
| Dashboard surface | **Three layers** | Overview sparkline tile + Resumes-tab column + dedicated Drift tab with full per-fact diff. Matches the TSE Tools visual vocabulary already established for the dashboard. |
| Storage | **Two new tables + one column** | `resume_fact_snapshots`, `resume_drift_scores`, plus `is_baseline` on `resume_versions`. Clean separation. |

---

## 3. Architecture

```text
┌─────────────────────┐
│ /brains-create      │
│ /brains-edit        │     (generated resume — workflow has the
│ /brains-tailor      │      structured data dict in memory)
└──────────┬──────────┘
           │
           │  facts_from_workflow_data(data)  ── pure transform, no LLM ──┐
           │                                                              │
           ▼                                                              ▼
┌─────────────────────┐                                  ┌──────────────────────────┐
│ /brains-import      │  ── extract_facts (LLM) ──►      │ resume_fact_snapshots    │
│ (new — upload a     │                                  │ (artifact_uid PK,        │
│  baseline DOCX)     │                                  │  facts JSON,             │
└─────────────────────┘                                  │  schema_version,         │
                                                         │  created_at)             │
                                                         └─────────────┬────────────┘
                                                                       │
                                                                       │
                                                         ┌─────────────▼────────────┐
                                                         │ compute_drift()          │
                                                         │ (pure-Python diff)       │
                                                         └─────────────┬────────────┘
                                                                       │
                                                                       ▼
                                                         ┌──────────────────────────┐
                                                         │ resume_drift_scores      │
                                                         │ (artifact_uid PK,        │
                                                         │  vs_parent_score JSON,   │
                                                         │  vs_baseline_score JSON, │
                                                         │  computed_at)            │
                                                         └─────────────┬────────────┘
                                                                       │
                                                  ┌────────────────────┼──────────────────────┐
                                                  ▼                    ▼                      ▼
                                            Overview tab        Resumes tab           Drift tab
                                            (sparkline tile)    (column + sortable)   (per-fact diff)
```

**Auxiliary tables:**

- `baseline_history` — append-only audit log of which version was the baseline at any given time, with the user's stated reason for each promotion.

**Modules** (new):

- `scripts/drift/` package containing `snapshot_from_workflow.py`, `extract_facts.py`, `compute.py`, `baseline.py`, `lineage.py`, `formatters.py`.
- `scripts/dashboard/tabs/drift.py` (new dashboard tab).
- `scripts/dashboard/workflows/import.py` (new workflow card for the new `/brains-import` slash command).

**Migrations** (new):

- `scripts/tracker/migrations/000N_drift_analytics.py` — adds two tables, the `is_baseline` column on `resume_versions`, `baseline_history`, the partial unique index, and the backfill that sets `is_baseline=1` on the oldest non-archived row per candidate. The migration number `N` depends on shipping order — see "Migration number coordination" below.

**Migration number coordination.** Approach B's plan (`docs/plans/2026-05-19-multi-candidate-approach-b.md`) reserves migration 0004 for the `candidates` table; its own follow-up migration 0005 is the optional cleanup that drops the `for_candidate` columns. Whichever feature ships first claims 0004; the other shifts up. Recommended order (user's call at planning time): **Drift Analytics first** (0004), **Approach B second** (0005 candidates + 0006 cleanup), because Drift Analytics is smaller, has no migration-runner-hook complexity, and gives the user useful telemetry before the bigger B refactor. If Approach B ships first instead, this design's migration becomes 0005 and the rest of the spec is unaffected — the drift module is candidate-scope-agnostic.

This design assumes Approach C (v1.6.0) is already shipped. It is designed to coexist with the future Approach B migration (proper `candidates` table) — when B ships, `baseline_history.for_candidate` migrates to `candidate_id` alongside the rest of the candidate-scoped columns; nothing else in this design changes.

---

## 4. Fact schema

Stored as JSON in `resume_fact_snapshots.facts`. This is the structured representation of a candidate's **professional identity baseline** — deliberately broader than any single tailored resume. Produced either by transforming the workflow's render-time data dict (generated resumes — partial coverage by design) or by LLM extraction from an uploaded source (baselines — full coverage).

```json
{
  "identity": {
    "name": "Mathilda Gell",
    "location": "Rochedale, QLD",
    "email": "mathilda@malin.com.au",
    "phone": "0433814874"
  },
  "experience": [
    {
      "entry_id": "exp-1",
      "employer": "Faith Christian Distance Education",
      "title": "Holiday Work",
      "start_date": "2026-01",
      "end_date": "2026-01",
      "location": "Brisbane, QLD",
      "key_points": [
        "Worked 5–6 days during the school holiday period preparing enrolment material for thousands of families.",
        "Packed and organised enrolment packs for the school's start-of-year intake."
      ]
    }
  ],
  "education": [
    {
      "entry_id": "edu-1",
      "institution": "Redeemer Lutheran College",
      "qualification": "Grade 10",
      "completion_year": "2028",
      "completion_status": "expected",
      "honours": []
    }
  ],
  "skills": ["Customer engagement", "Public speaking", "Team leadership"],
  "certifications": [
    {"name": "Black Belt Tae Kwon Do", "issuer": null, "year": null}
  ],
  "standalone_achievements": [
    "Netball MVP 2025",
    "1st Youth Nationals Archery 2022"
  ],
  "hobbies": ["Netball", "Archery", "Tae Kwon Do", "Volleyball", "Touch football"],
  "languages": [
    {"language": "English", "proficiency": "native"}
  ],
  "publications": null,
  "portfolio_links": null
}
```

**Conventions:**

- `entry_id` is a stable identifier assigned at snapshot creation. Format: `exp-N`, `edu-N`, `pub-N`, monotonically numbered in chronological order. Survives across versions when the natural key matches.
- `key_points` is always a list of strings. The workflow already produces these as a list; the LLM extractor reverse-engineers it from prose.
- Dates use `YYYY-MM` or `YYYY`. Day precision is never used.
- `completion_status` is one of `"completed"`, `"expected"`, `"in_progress"`, or `null`.
- `languages[].proficiency` is from a controlled vocabulary: `"native"`, `"fluent"`, `"professional"`, `"conversational"`, `"basic"`.
- `publications[]` entries have shape `{title, venue, year, authors[], url}`. `authors` is a list of strings. `year` is `YYYY` or `null`.
- `portfolio_links[]` entries have shape `{label, url}` (e.g., `{"label": "GitHub", "url": "github.com/mathilda"}`).
- All scalar fields are nullable. Absent scalar means `null`, never empty string.

**Top-level class semantics — `null` vs `[]`:**

The ten fact classes are all top-level nullable. The distinction between `null` and `[]` is load-bearing:

- `null` = **"this version did not capture this category"**. The baseline may have data here; the derivative simply didn't surface it. Drift compute SKIPS this class entirely — it contributes nothing to either the per-class score or the weighted `overall_pct`.
- `[]` (or `{}` for `identity`) = **"this version captured the category and it is empty"**. Counts as 0 of the unit type. If the other side has items, those count as "removed" / "added" normally.

This matters because the baseline (broader-than-resume) often holds categories that tailored derivatives legitimately omit. A teen retail-application resume shouldn't be penalized for drifting from a baseline that contains publications — the publications weren't *removed*, they just weren't surfaced for that role.

**Top-level keys (ten fact classes):**

| Class | Type | Workflow captures today? | LLM extractor captures? |
|---|---|---|---|
| `identity` | object | Yes (from contact_line) | Yes |
| `experience` | list[entry] | Yes | Yes |
| `education` | list[entry] | Yes | Yes |
| `skills` | list[string] | Yes | Yes |
| `certifications` | list[entry] | Inconsistent — sometimes folded into skills | Yes |
| `standalone_achievements` | list[string] | Inconsistent — sometimes folded into experience | Yes |
| `hobbies` | list[string] | No → `null` | Yes |
| `languages` | list[entry] | No → `null` | Yes |
| `publications` | list[entry] | No → `null` | Yes |
| `portfolio_links` | list[entry] | No → `null` | Yes |

The "broader than the resume" property is enforced by the LLM extractor: when ingesting an uploaded baseline, it captures all ten classes even when the source DOCX only surfaces some. Workflows that don't ask the user for hobbies/languages/publications/portfolio_links produce `null` for those classes in their derivative snapshots, and drift compute correctly treats those absences as "not captured" rather than "removed".

**Out of scope for v1:**

- Cover-letter facts. Cover letters are derivative; drift on a cover letter doesn't carry the same signal.
- Image / signature / formatting facts. Content only.
- Workflow enhancements to start asking for hobbies/languages/publications/portfolio_links during the interview. Those workflows can populate the new classes in a future enhancement; v1 just needs the schema to accommodate them and the LLM extractor to fill them on baseline upload.

**Schema versioning:**
The `resume_fact_snapshots` table includes a `schema_version INTEGER NOT NULL DEFAULT 1` column so future schema evolution can be tracked. Drift compute requires both compared snapshots to share a schema version; if they differ, a one-shot lossless upgrade is applied to the older snapshot. If lossless upgrade is impossible, the drift score returns `{"status": "schema_mismatch", "details": "..."}`. v1 ships at `schema_version = 1`.

---

## 5. Drift formula

Pure-Python comparison of two snapshots. No LLM at compute time.

### 5a. Per-class outputs

Stored as `vs_parent_score` and `vs_baseline_score` JSON. Shape:

```json
{
  "identity": {
    "fields_changed": ["location"],
    "fields_total": 4,
    "pct": 25.0
  },
  "experience": {
    "entries_added": 0,
    "entries_removed": 0,
    "entries_with_field_changes": 1,
    "field_changes": [
      {"entry_id": "exp-1", "field": "title", "from": "Holiday Work", "to": "Holiday Assistant"},
      {"entry_id": "exp-1", "field": "end_date", "from": "2026-01", "to": "2026-02"}
    ],
    "entries_total": 1,
    "pct": 50.0
  },
  "education": {
    "entries_added": 0,
    "entries_removed": 0,
    "entries_with_field_changes": 0,
    "field_changes": [],
    "entries_total": 1,
    "pct": 0.0
  },
  "skills": {
    "added": ["Composure under pressure"],
    "removed": [],
    "total": 5,
    "pct": 20.0
  },
  "certifications": {
    "added": [],
    "removed": [],
    "field_changes": [],
    "total": 1,
    "pct": 0.0
  },
  "standalone_achievements": {
    "added": [],
    "removed": ["Netball MVP 2025"],
    "total": 5,
    "pct": 20.0
  },
  "overall_pct": 17.4,
  "headline_changes": [
    "Title changed in 1 experience entry",
    "End-date changed in 1 experience entry",
    "1 skill added",
    "1 standalone achievement removed"
  ]
}
```

### 5b. Per-class `pct` rules

`pct = (changed_units / total_units) * 100`, where "unit" depends on the class:

| Class | Unit | Counted as "changed" when |
|---|---|---|
| `identity` | Per-field (name, location, email, phone) | Field value differs |
| `experience` | Per-entry | Any field on the entry differs, OR the entry was added/removed |
| `education` | Per-entry | Same rule as experience |
| `skills` | Per-string | String appears in only one side (added OR removed both count) |
| `certifications` | Per-entry (by `name`) | Entry added, removed, or any field changed |
| `standalone_achievements` | Per-string | Same rule as skills |
| `hobbies` | Per-string | Same rule as skills |
| `languages` | Per-entry (by `language`) | Entry added, removed, OR `proficiency` field changed |
| `publications` | Per-entry | Any field on the entry differs, OR the entry was added/removed |
| `portfolio_links` | Per-entry (by canonicalised `url`) | Entry added, removed, OR `label` field changed |

`total_units` is the **max** of the unit count on the two sides (so a 100% removal still produces a 100% drift, not >100%).

**`null`-class handling:** If either side of the comparison has `null` for a class, that class is **skipped**: its per-class output is `{"status": "not_captured", "pct": null}` and it does NOT contribute to the weighted `overall_pct`. The aggregate's denominator (sum of weights) is renormalised across only the classes where both sides are non-null. This is the mechanism that protects tailored resumes from being penalised for legitimately omitting baseline categories.

### 5c. Entry matching for list-of-object classes

Natural keys per class:

| Class | Natural key | Fuzzy fallback |
|---|---|---|
| `experience` | `(employer, start_date)` | Token-set ratio ≥ 0.85 on `employer` + ≥ 0.85 on `title` |
| `education` | `(institution, qualification)` | Token-set ratio ≥ 0.85 on `institution` |
| `certifications` | `name` (case-insensitive) | Token-set ratio ≥ 0.85 |
| `languages` | `language` (canonicalised: lowercase, strip whitespace) | Token-set ratio ≥ 0.90 (language names are short, demand high similarity) |
| `publications` | `(title, year)` (case-insensitive title) | Token-set ratio ≥ 0.85 on `title` |
| `portfolio_links` | canonicalised `url` (lowercase, strip trailing slash, strip `https?://` prefix) | None — URLs match exactly or they don't |

Fuzzy matching uses `rapidfuzz` if available, else a small inline implementation in `scripts/drift/compute.py`.

Unmatched entries on the baseline side count as "removed"; unmatched on the candidate side count as "added". Once an entry is matched, subsequent field-level comparison runs across all entry fields.

### 5d. `overall_pct` (the headline number)

Weighted average of per-class `pct`s, with renormalisation across only the classes where both sides are non-null:

| Class | Weight |
|---|---|
| `identity` | 0.20 |
| `experience` | 0.25 |
| `education` | 0.12 |
| `skills` | 0.08 |
| `certifications` | 0.08 |
| `standalone_achievements` | 0.06 |
| `hobbies` | 0.04 |
| `languages` | 0.07 |
| `publications` | 0.06 |
| `portfolio_links` | 0.04 |

(Weights sum to 1.00.)

**Rationale for the relative weights:**

- Identity and experience changes are the highest-signal of factual problems — if employer or role dates have shifted, that's where to look first.
- Education, certifications, languages all carry credential-like signal (claims about qualifications).
- Skills, standalone achievements, publications, hobbies, portfolio links drift more legitimately over time — added/removed often reflects real life, not corruption.

**Renormalisation:** classes that are `null` on either side are excluded from both numerator and denominator. If only 4 of the 10 classes have data on both sides, the `overall_pct` is computed using only those 4, and the weights renormalise to sum to 1.0 across them. This is what protects tailored derivatives from being penalised for narrower scope than the baseline.

Weights live as a module-level constant `DRIFT_CLASS_WEIGHTS` in `scripts/drift/compute.py`. Per-candidate weight tuning is out of scope for v1; can be added on the `candidates` row when Approach B ships if real users ask for it.

### 5e. `headline_changes`

Short human-readable list (max 5 items) for the dashboard tile and per-row tooltip. Generated by `scripts/drift/formatters.py::format_headline_changes(score)`. Selects the most "salient" changes across classes by a fixed priority order and stops at 5:

1. `identity` field changes
2. `experience` field changes
3. `experience` entries added/removed
4. `education` field changes
5. `education` entries added/removed
6. `certifications` changes
7. `languages` changes (proficiency claims)
8. `publications` entries added/removed/changed
9. `skills` added/removed
10. `standalone_achievements` added/removed
11. `portfolio_links` changes
12. `hobbies` added/removed

Within each tier, ordering is by appearance in the snapshot.

### 5f. Special cases

- Baseline resume itself: `vs_parent_score = null` AND `vs_baseline_score = null`. The baseline has no comparator.
- Resume with no parent (orphan upload that isn't the baseline either): `vs_parent_score = null`; `vs_baseline_score` still computed.
- Resume whose parent has been archived: lineage walking SKIPS archived rows; drift compares against the next non-archived ancestor. If no non-archived ancestor exists, `vs_parent_score = null`.

---

## 6. Baseline policy

### 6a. Default behaviour

Exactly one resume per candidate has `is_baseline = 1`. The first non-archived `resume_versions` row inserted for a new candidate gets it automatically by `add_resume_version`. For existing candidates at migration time, the backfill sets `is_baseline = 1` on the oldest non-archived row per `for_candidate` value (post-B: per `candidate_id`).

Enforced by a partial unique index:

```sql
CREATE UNIQUE INDEX ux_resume_versions_baseline_per_candidate
  ON resume_versions(for_candidate)
  WHERE is_baseline = 1 AND archived_at IS NULL;
```

(Post-B: same index on `candidate_id`.)

### 6b. Promotion API

```python
# scripts/drift/baseline.py
def promote_baseline(artifact_uid: str, reason: str) -> None:
    """Set this artifact as the active baseline for its candidate.

    Single transaction:
      1. Look up the row by artifact_uid; resolve its candidate scope.
      2. UPDATE resume_versions SET is_baseline=0 WHERE <candidate scope>
         AND is_baseline=1.
      3. UPDATE resume_versions SET is_baseline=1 WHERE artifact_uid=?.
      4. INSERT INTO baseline_history (for_candidate, artifact_uid, promoted_at, reason).
      5. recompute_all_vs_baseline(candidate_scope) — every non-archived resume's
         vs_baseline_score is recomputed against the new baseline.
    """
```

### 6c. Audit trail

```sql
CREATE TABLE baseline_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    for_candidate TEXT,                    -- post-B: candidate_id INTEGER
    artifact_uid TEXT NOT NULL,
    promoted_at TEXT NOT NULL,
    reason TEXT
);
```

Append-only. Lets us answer "what was the baseline when this resume was created?" if needed in future.

### 6d. Dashboard promotion surface

In the Drift tab, each non-baseline resume in the lineage shows a "Make this my baseline" button. Clicking opens a modal:

> **Promote this version as the new truthful baseline?**
> Your old baseline will be retained in history. Drift scores for every resume in this lineage will be recalculated.
>
> **Why are you promoting?** (required)
>
> - [ ] Real-life change (new job, completed degree, certification)
> - [ ] Correcting historical inaccuracy
> - [ ] Other (please describe)
>
> [ Cancel ]   [ Promote ]

The reason text is logged in `baseline_history.reason`. After promotion, the Drift tab refreshes and shows a subtle annotation: "Baseline changed on 2026-05-19 — historical scores recalculated."

### 6e. What if there's no baseline yet?

Doesn't happen in practice. `is_baseline` is set automatically when the first row per candidate is inserted; the migration backfills existing data. The single case where it could be `null` is if the lone baseline gets archived — then the dashboard's Drift tab shows an empty state with a "promote a new baseline" picker listing non-archived versions.

### 6f. Multiple lineages per candidate

Out of scope for v1. A user with two distinct lineages for the same candidate (e.g., two different industries) will see a single drift trajectory that may look noisy when they switch lineages. The Drift tab's empty/help state notes this limitation. A `lineage_id` extension can be added later if real users hit this — the snapshot and drift-score tables are unaffected.

---

## 7. Dashboard surfaces

Three layered surfaces matching the TSE Tools visual vocabulary already established for the dashboard (dark theme, top tab nav, summary tiles, sparklines, dense tables).

### 7a. Overview tab — drift trajectory tile

A new tile on the existing Overview tab, sized like the other summary tiles:

```text
┌─────────────────────────────────────────────┐
│  Drift from baseline · active candidate     │
│                                             │
│  17.4%   ▁▂▃▅▇▆▃▂                          │
│  Latest    last 12 versions                 │
│                                             │
│  Identity stable · 1 experience field moved │
└─────────────────────────────────────────────┘
```

- Headline number: `vs_baseline_score.overall_pct` of the most recent non-archived resume in the active candidate's lineage. Shows `—` if no scored resume exists.
- Sparkline: last N (default 12, configurable in `scripts/dashboard/prep/sparkline.py`) resumes' `vs_baseline_score.overall_pct` in chronological order. Lineage walked from baseline forward; archived rows skipped. Branches use most-recent path back to baseline.
- One-line summary: `format_headline_changes` output truncated to fit on one line.
- Click → opens the Drift tab focused on the active candidate.

### 7b. Resumes tab — drift columns

Add two sortable columns to the existing per-resume table on the Resumes tab:

| File | Created | Template | JD | Drift vs parent | Drift vs baseline |
| --- | --- | --- | --- | --- | --- |
| `Mathilda_Gell_resume_2026-05-19_V9MQZX.docx` | 2026-05-19 | hybrid | — | — (baseline) | — |
| `Mathilda_Gell_resume_2026-05-22_KP3X8M.docx` | 2026-05-22 | hybrid | Big W | 8.2% | 8.2% |
| `Mathilda_Gell_resume_2026-06-01_F7TLW2.docx` | 2026-06-01 | hybrid | McDonald's | 12.1% | 17.4% |

- "Drift vs parent" shows `vs_parent_score.overall_pct`. `— (baseline)` when this row IS the baseline; `—` when parent has no snapshot or no parent.
- "Drift vs baseline" shows `vs_baseline_score.overall_pct`. `—` when this row IS the baseline.
- Both columns sortable.
- Hover on a cell shows `headline_changes` as a tooltip.
- Click a row → opens the Drift tab focused on that resume.
- No color-coding for accessibility — sortable numeric columns are the affordance. A small "•" prefix appears when drift is above the user-set threshold (default off; configured in the candidate row when Approach B ships, OR in a local preference file pre-B).

### 7c. Drift tab — full-page deep dive

New top-level tab. Three sub-sections:

```text
┌─ Drift · Mathilda Gell ──────────────────────────────────────┐
│                                                              │
│  Lineage (12 versions, baseline V9MQZX)                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  ●─●─●─●─●─●─●─●─●─●─●─●                              │   │
│  │  bl                              ↑ selected            │   │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  Selected: KP3X8M  (2026-05-22 · hybrid · Big W)             │
│  vs parent: 8.2% · vs baseline: 8.2%                         │
│  [ Make this my baseline ]                                   │
│                                                              │
│  Per-fact-class                                              │
│  ┌────────────────────────┬──────────┬───────────┐           │
│  │ Class                  │ vs parent │ vs baseline│          │
│  ├────────────────────────┼──────────┼───────────┤           │
│  │ Identity               │   0.0%   │   0.0%    │           │
│  │ Experience             │  16.7%   │  16.7%    │           │
│  │ Education              │   0.0%   │   0.0%    │           │
│  │ Skills                 │  20.0%   │  20.0%    │           │
│  │ Certifications         │   0.0%   │   0.0%    │           │
│  │ Standalone achievements│  20.0%   │  20.0%    │           │
│  │ Hobbies                │     —    │   0.0%    │           │
│  │ Languages              │     —    │   0.0%    │           │
│  │ Publications           │     —    │     —     │           │
│  │ Portfolio links        │     —    │     —     │           │
│  └────────────────────────┴──────────┴───────────┘           │
│  (— = not captured in this version; class skipped)            │
│                                                              │
│  Field-level changes                                         │
│  • Experience · exp-1 · title:                               │
│      "Holiday Work" → "Holiday Assistant"                    │
│  • Experience · exp-1 · end_date:                            │
│      "2026-01" → "2026-02"                                   │
│  • Skills · added: "Composure under pressure"                │
│  • Standalone achievements · removed: "Netball MVP 2025"     │
│                                                              │
│  [ Open the resume DOCX ]                                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

- **Lineage strip**: horizontal chain of dots, oldest left → newest right, baseline labeled `bl`. Click a dot to select. Branches (forks) shown as offshoots when they exist.
- **Selected version summary**: artifact UID, timestamp, template, paired JD, both drift scores, "Make this my baseline" button.
- **Per-fact-class table**: `pct` per class against parent and baseline side-by-side.
- **Field-level changes**: flat list aggregating `field_changes` + added/removed from both score JSONs. Sorted by class priority (Section 5e) then by appearance.
- **"Open the resume DOCX"**: existing handoff pattern from elsewhere in the dashboard.

### 7d. Intentionally not built (v1)

- No automatic email/push notification when drift crosses a threshold.
- No "merge two lineages" UI.
- No direct edit of baseline facts. Baselines are immutable artifacts; "correcting" requires generating a new resume and promoting it.
- No text-level diff overlay (side-by-side DOCX content). The fact-level diff is the v1 view; text-level can be a v2.

---

## 8. Compute pipeline

### 8a. Generated-resume pipeline (the common case — free, fast)

Every workflow that produces a resume already has the structured `data` dict in memory at render time:

```python
data = {
    "candidate_name": "Mathilda Gell",
    "candidate_contact_line": "Rochedale, QLD · 0433814874 · mathilda@malin.com.au",
    "summary": "...",
    "skills": "...",
    "experience": "...",
    "education": "...",
}
```

A pure transform converts this into the Section 4 fact schema:

```python
# scripts/drift/snapshot_from_workflow.py
def facts_from_workflow_data(data: dict) -> dict:
    """Convert the workflow's render-time data dict into the fact-snapshot schema.

    Parses contact_line into identity sub-fields (location, email, phone).
    Splits experience/education blocks into entries via line-shape heuristics
    (heading line + bullet lines). Normalises bullet lines into key_points.

    For classes the workflow doesn't capture today (hobbies, languages,
    publications, portfolio_links) the returned dict has those keys set to
    null — NOT empty list. This signals to drift compute that the class was
    not captured and should be skipped in the comparison, rather than being
    treated as 'user explicitly has zero hobbies'. See Section 5b for the
    null-vs-empty-list semantics.

    Pure function, no I/O. Returns a dict matching Section 4 schema, schema_version 1.
    """
```

Integration in each workflow: after `render_resume_docx(...)` succeeds AND `add_resume_version` returns the new row id AND `finalize_docx(target_path, meta)` has run, call:

```python
# scripts/drift/compute.py
def write_snapshot_and_compute_drift(artifact_uid: str, facts: dict) -> None:
    """Persist snapshot in resume_fact_snapshots; look up parent + baseline;
    compute scores; persist them in resume_drift_scores. Idempotent."""
```

Added cost: ~10ms (pure-Python diff of two JSON blobs). No LLM. No network.

### 8b. Uploaded-resume pipeline (rare — LLM cost, once per upload)

New workflow / slash command:

```text
/brains-import — upload an existing DOCX as the candidate's baseline.
```

Pipeline:

1. User uploads DOCX (or pastes plain text).
2. `scripts/parsers/docx_to_text.py` extracts the raw text.
3. `scripts/drift/extract_facts.py::extract_facts_from_text(text)` calls the LLM with a structured-output prompt asking for all ten fact classes (identity, experience, education, skills, certifications, standalone_achievements, hobbies, languages, publications, portfolio_links). Returns a Section 4 dict OR raises `FactExtractionError` on validation failure. The extractor uses `null` (not `[]`) for classes the source text doesn't mention at all, and `[]` for classes the source explicitly says are empty (e.g., "Languages: English only" → `[{"language": "English", "proficiency": "native"}]`; vs. no mention of languages → `null`).
4. Implausibility check (`scripts/drift/extract_facts.py::flag_implausible_values(facts)`) — flags placeholder-like values (`John Doe`, `<example>`, dates before 1900 / after 2100, `null` for required fields). User confirms before commit.
5. `add_resume_version(file_path=..., is_baseline=True, ...)` writes the tracker row.
6. `write_snapshot_and_compute_drift(artifact_uid, facts)` — `vs_baseline_score` and `vs_parent_score` are both `null` since this IS the baseline.

LLM cost: one extraction per uploaded resume. Typically once per candidate (the baseline). Users can also import additional historical resumes — each is an extraction.

Validation enforces the Section 4 schema strictly (required keys, types, no extra fields). Failure → no partial write; user sees the LLM output for review and can retry, edit the source DOCX, or paste plain text.

### 8c. Baseline-promotion recompute

When `promote_baseline(artifact_uid, reason)` runs:

```python
# scripts/drift/compute.py
def recompute_all_vs_baseline(candidate_scope: dict) -> int:
    """Recompute vs_baseline_score for every non-archived resume in the
    given candidate scope. Returns the number of rows updated. Idempotent.

    Runs inside the same transaction as the promotion (Section 6b)
    so the dashboard sees a consistent state."""
```

`vs_parent_score` is unaffected — parent relationships don't shift on baseline promotion.

A `baseline_promoted` row is also appended to `baseline_history` (Section 6c) so the Drift tab can show a subtle annotation: "Baseline changed on 2026-05-19 — historical scores recalculated."

### 8d. Lineage walking

```python
# scripts/drift/lineage.py
def get_parent_snapshot(artifact_uid: str) -> dict | None:
    """Walk up the parent_uid chain, skipping archived rows, until a row
    with a snapshot is found. Returns None if none found (orphan or
    archived-out ancestor)."""


def get_baseline_snapshot(artifact_uid: str) -> dict | None:
    """Look up the candidate scope of artifact_uid; find the row where
    is_baseline=1 AND archived_at IS NULL; return its snapshot.
    Returns None if no active baseline exists."""


def get_candidate_lineage(candidate_scope: dict) -> list[ResumeVersion]:
    """Return all non-archived resume_versions rows for this candidate,
    sorted by created_at ascending. Used by Drift tab + sparkline prep."""
```

Cycle guard: lineage walks cap depth at 100 and log a warning if exceeded. `parent_uid` is set at creation and never updated, so cycles shouldn't occur — this is purely defensive.

### 8e. Migration `000N_drift_analytics`

(See "Migration number coordination" in Section 3. If Drift Analytics ships before Approach B, `N = 4`; if after, `N = 6` — Approach B claims 4 and 5.)

```sql
-- scripts/tracker/migrations/000N_drift_analytics.py

CREATE TABLE resume_fact_snapshots (
    artifact_uid TEXT PRIMARY KEY,
    facts TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (artifact_uid) REFERENCES resume_versions(artifact_uid)
);

CREATE TABLE resume_drift_scores (
    artifact_uid TEXT PRIMARY KEY,
    vs_parent_score TEXT,
    vs_baseline_score TEXT,
    computed_at TEXT NOT NULL,
    FOREIGN KEY (artifact_uid) REFERENCES resume_versions(artifact_uid)
);

CREATE TABLE baseline_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    for_candidate TEXT,
    artifact_uid TEXT NOT NULL,
    promoted_at TEXT NOT NULL,
    reason TEXT
);

ALTER TABLE resume_versions ADD COLUMN is_baseline INTEGER NOT NULL DEFAULT 0;

CREATE UNIQUE INDEX ux_resume_versions_baseline_per_candidate
  ON resume_versions(for_candidate)
  WHERE is_baseline = 1 AND archived_at IS NULL;
```

Backfill (run inside the migration `apply()` after the schema changes):

For each distinct `for_candidate` value (including the implicit `NULL` for the profile holder), find the oldest non-archived `resume_versions` row and set `is_baseline = 1`. No fact snapshots are backfilled for pre-existing resumes — their drift columns show `—` until the user runs `/brains-import` on them or until a separate (opt-in, out-of-scope-for-v1) batch backfill is provided.

### 8f. Approach B interaction

When Approach B (proper `candidates` table) ships:

- `baseline_history.for_candidate` migrates to `candidate_id INTEGER REFERENCES candidates(id)` in lockstep with the rest of the candidate-scoped columns (handled by Approach B's migration).
- The partial unique index on `resume_versions` rebuilds on `candidate_id`.
- Snapshot and drift-score tables (keyed by `artifact_uid`) are unaffected.
- Lineage walks switch their candidate-scope predicate from "rows with matching `for_candidate` text" to "rows with matching `candidate_id`".

The drift module itself stays candidate-agnostic — it cares about `artifact_uid` chains and a callable that returns the candidate scope for a given row.

---

## 9. Edge cases and failure modes

| # | Case | Behaviour |
|---|---|---|
| 9.1 | Resume has `parent_uid = NULL` (e.g., fresh `/brains-create`) | `vs_parent_score = null`. Dashboard shows `—`. |
| 9.2 | Parent has no snapshot (created pre-v1.7.0) | `vs_parent_score = {"status": "parent_unsnapshotted", "headline_changes": []}`. Dashboard renders `—` with a hover note. User can run `/brains-import` on the parent to fix. |
| 9.3 | Baseline has no snapshot | Same as 9.2 but for `vs_baseline_score`. Promoting a snapshotted version as the new baseline fixes all downstream rows. |
| 9.4 | Resume archived | Excluded from baseline resolution, sparkline, tab listings. Snapshot and drift-score rows retained. Lineage walks skip archived rows. |
| 9.5 | Fact extraction fails during `/brains-import` | NO partial snapshot. NO tracker row. User sees the raw LLM output for inspection. Retry, edit DOCX, or paste plain text. |
| 9.6 | Fact extraction succeeds but values look implausible | Soft warning before commit. User can edit before saving. Snapshot only written after confirmation. |
| 9.7 | Lineage forks (two children share one parent) | Both children get `vs_parent_score` against the same parent. Drift tab lineage strip shows the fork. Overview sparkline uses most-recent-created path back to baseline. |
| 9.8 | Cycle in `parent_uid` | Shouldn't occur (parent_uid is set at creation, never updated). Defensive depth cap of 100 in lineage walk + log warning. |
| 9.9 | Multiple candidates per installation (pre-Approach-B) | Drift scoped by `for_candidate`. Each candidate has its own baseline, sparkline, and lineage. Migration backfill sets `is_baseline=1` per distinct `for_candidate` including `NULL`. |
| 9.10 | After Approach B ships | `for_candidate` text scope migrates to `candidate_id` FK. Snapshot and drift-score tables unaffected (UID-keyed). Lineage walks switch scope predicate. |
| 9.11 | Old resume from before v1.7.0 | Snapshot is absent → drift columns show `—`. User can `/brains-import` the file to backfill, or ignore. No automatic backfill. |
| 9.12 | Snapshot schema evolves (e.g., v2 adds a category) | `schema_version` column on snapshots. Drift compute requires matching schema versions; older snapshot upgrades via lossless transform. If lossless impossible, score returns `{"status": "schema_mismatch", ...}`. v1 ships at `schema_version = 1` and doesn't exercise this path. |
| 9.13 | Two natural keys collide (e.g., two experience entries with same employer + start_date) | Entry matcher pairs them in order of appearance. Practically rare. Loud warning logged. |
| 9.14 | Active baseline gets archived | The candidate has no baseline. Dashboard Drift tab shows empty state with a picker to promote a new one from the non-archived versions. |
| 9.15 | Class is `null` on derivative but populated on baseline (e.g., tailored teen resume omits publications, baseline has them) | Class is **skipped** in drift compute. Per-class score is `{"status": "not_captured", "pct": null}`. Doesn't contribute to `overall_pct`. Dashboard renders `—`. The omission is NOT counted as drift. |
| 9.16 | Class is `[]` on derivative but populated on baseline | Class is compared normally. Items on the baseline count as "removed". Per-class `pct` is 100%. This is the "user genuinely removed all items" case — distinct from 9.15. |
| 9.17 | LLM extractor returns `[]` for a category the source doesn't mention | Bug. Extractor MUST return `null` when the source is silent. Validation step in `extract_facts.py` flags `[]` results for review when the corresponding region of the source text has no apparent mention of the category. |

---

## 10. Test strategy

Each module gets a dedicated test file under `tests/drift/`:

- `test_snapshot_from_workflow.py` — round-trip the existing workflow `data` dicts; assert the Section 4 schema is produced. Includes Mathilda's session data from `c:\Brains_Resume_Skill\output\resume-2026-05-19-142439.docx` (UID `V9MQZX`) as a fixture.
- `test_extract_facts.py` — golden-file tests against fixture DOCX text + expected fact schema, with mocked LLM (deterministic stub) so tests don't make network calls. Coverage includes the silent-vs-explicitly-empty distinction: when fixture text mentions hobbies → list; when fixture text omits hobbies entirely → `null` (not `[]`). Validation failure paths covered separately (invalid JSON, missing required keys, extra keys, type mismatches).
- `test_compute.py` — pure-Python diff: per-class `pct` rules, entry matching (natural + fuzzy), `overall_pct` weighted aggregate with renormalisation, `headline_changes` formatter. Hand-built snapshot fixtures cover:
  - identity-only changes
  - experience entries added/removed/edited
  - education unchanged-vs-changed
  - skills set diff
  - certification changes
  - standalone_achievements set diff
  - hobbies set diff
  - languages entry add/remove + proficiency-only change
  - publications entry add + title-fuzzy match
  - portfolio_links entry add/remove + canonicalised-URL match (`https://github.com/x` matches `github.com/x/`)
  - **null-class semantics**: baseline has 10 classes populated, derivative has 4; assert `overall_pct` is computed only over the 4 with renormalised weights, and the 6 null-classes show `{"status": "not_captured", "pct": null}`.
  - **null vs []**: a derivative with `hobbies: []` against a baseline with `hobbies: ["X", "Y"]` produces `pct: 100%` and `removed: ["X", "Y"]`; whereas `hobbies: null` against the same baseline produces `{"status": "not_captured", "pct": null}` and excludes hobbies from `overall_pct`.
- `test_baseline.py` — `promote_baseline` transaction (single baseline invariant; recompute trigger); `baseline_history` append. Migration 0004 backfill behaviour: oldest non-archived row per `for_candidate` gets `is_baseline=1`.
- `test_lineage.py` — parent walk skipping archived rows, fork handling, depth cap, no-snapshot ancestor.
- `test_drift_tab_render.py` — Streamlit AppTest covering the Drift tab's basic render with a fixture snapshot set.
- `test_smoke_drift_end_to_end.py` — full pipeline: `/brains-import` a baseline → `/brains-create` a derivative → assert drift score is computed correctly.

Pre-existing baseline failures from the v1.6.0 ship (`test_workflows_tab_has_three_subheaders`, `test_weekly_summary_pacing_none_when_no_target`) remain out of scope unless directly touched.

---

## 11. Open questions deferred to implementation

These were intentionally not nailed down in the brainstorm; the implementer can answer them during planning.

1. **Sparkline data prep helper location.** Probably `scripts/dashboard/prep/drift_sparkline.py` mirroring the existing `prep/sparkline.py`, but the exact factoring depends on what `prep/sparkline.py` looks like in v1.6.0.
2. **Threshold UI for the Resumes-tab "•" prefix.** Where does the user set the threshold? Pre-Approach-B options: a local preference file at `~/.brains-resume/drift_threshold.json` per-candidate, OR a session-state value in the sidebar. Post-Approach-B: a column on the `candidates` table. v1 can ship without this and add it once real users ask for it.
3. **LLM extractor model choice.** Probably the same model the rest of the skill uses (Claude Sonnet 4.6 or similar). Should be configurable via an env var so the user can downgrade to a cheaper model for non-production extractions.
4. **`/brains-import` workflow card design.** The brainstorm assumed it exists; the planning step will design the actual Streamlit card and handoff command.

---

## 12. Implementation order (suggested for the plan)

Rough sketch — the writing-plans skill will produce the actual task breakdown:

1. Migration 0004 (schema + backfill).
2. `Drift` package skeleton: `snapshot_from_workflow.py`, `compute.py`, `lineage.py`, `formatters.py`, `baseline.py`. TDD per module.
3. Integration into each generator workflow (`/brains-create`, `/brains-edit`, `/brains-tailor`, `/brains-cover-letter`) — call `write_snapshot_and_compute_drift` after `finalize_docx`.
4. `extract_facts.py` (LLM-backed) + `/brains-import` workflow card. Includes the structured-output prompt, validation, and implausibility flagging.
5. Dashboard tab `drift.py` + Overview tile + Resumes-tab column.
6. End-to-end smoke test.
7. Version bump to v1.7.0; CHANGELOG entry.

---

*End of design.*
