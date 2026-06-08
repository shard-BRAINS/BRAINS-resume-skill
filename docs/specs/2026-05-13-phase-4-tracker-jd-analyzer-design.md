# Phase 4 — Data Layer, JD Analyzer, Pre-Application Check — Design Specification

<!-- readability: skip -->
<!-- Historical planning/spec document; predates the BRAINS readability standard (adopted 2026-05-29). -->

**Version:** Draft v1
**Date:** 2026-05-13
**Status:** Awaiting user review
**Target release:** v1.2.0
**Builds on:** v1.1.0 (Plan 3 — 11 workflows, 4 resume + 2 cover-letter templates, all shipped)
**Successor:** Phase 5 / v1.3.0 — Streamlit dashboard built on top of this data layer

---

## 1. Purpose

Establish the deterministic data and analysis foundation that the v1.3.0 dashboard will consume:

1. **JD analyzer workflow** — surfaces ND-relevant signals in a job description (soft-culture red flags, masking-cost markers, evidence-of-real-flexibility, role-fit score, duplicate-application detection). Mirrors the `bias_scan` / `integrity_check` validator pattern.
2. **Application tracker data layer** — durable SQLite store at user level (`~/.brains-resume/tracker.db`) with five entity tables and a Python module providing the public API for both the CLI slash command and the future dashboard.
3. **Pre-application sanity check workflow** — a six-question coaching pass that runs before submission, asks about duplicate applications, fit-vs-pressure, pacing against the user's self-defined healthy weekly rate, and registers the application in the tracker.

These three pieces are designed together because each is largely useless without the others: the analyzer's findings inform the precheck; the precheck registers tracker rows; the tracker is queried by the analyzer for duplicate detection. Bundling them keeps the data flow coherent and lets Phase 5 build a dashboard on a stable foundation.

## 2. Scope

### In scope for Phase 4 (v1.2.0)

1. **JD analyzer validator** — `scripts/validators/jd_analyzer.py` with finding catalog covering soft-culture red flags, masking-cost markers, evidence-of-flex signals, required-vs-nice parsing, role-fit scoring, and duplicate-application detection
2. **JD analyzer workflow reference** — `references/workflows/jd-analyze.md` describing inputs, procedure, finding presentation, and handoff to the precheck
3. **JD analyzer slash command** — `commands/brains-jd-analyze.md`
4. **Tracker data layer** — `scripts/tracker/` Python module with `db.py`, `models.py`, `add.py`, `query.py`, `profile.py`
5. **SQLite schema** — five entity tables (`resume_versions`, `cover_letters`, `jds`, `applications`, `outcomes`) with foreign keys, soft-delete, and migration support
6. **User profile store** — `~/.brains-resume/profile.json` for focus areas + self-defined healthy weekly application rate
7. **Pre-application check workflow reference** — `references/workflows/pre-application-check.md`
8. **Pre-application check slash command** — `commands/brains-precheck.md`
9. **Tracker slash command** — `commands/brains-track.md` with subcommands (`add`, `update`, `list`, `summary`, `focus-areas`, `healthy-rate`)
10. **Opt-in integration with existing workflows** — `brains-tailor`, `brains-cover-letter`, `brains-review`, `brains-check` get a one-line end-of-workflow prompt offering to register the artifact in the tracker
11. **SKILL.md router updates** — three new workflow entries
12. **README + brand-application + CHANGELOG + Claude Project bundle** — slash-command cheat sheet, v1.2.0 entry, bundle rebuilt
13. **v1.2.0 git tag**

### Out of scope for Phase 4 (deferred)

- **Streamlit dashboard UI** — Phase 5 / v1.3.0 builds on the Phase 4 data layer
- **Pacing/burnout tracker as a dedicated page** — surfaced as a CLI summary in `/brains-track summary` for v1.2.0; gets a dedicated page in Phase 5
- **Efficacy analytics with confidence bands** — basic counts in `/brains-track summary` for v1.2.0; full analytics in Phase 5
- **Anonymized community efficacy data** — Phase 5+ at the earliest; requires careful consent/anonymization design
- **Interview prep skill** — sibling skill, separate bundle; parallel work
- **Salary negotiation skill** — sibling skill, separate bundle
- **Network/referral lane** — could fold into v1.2.0 tracker as a `channel` value; full first-class lane deferred to Phase 5
- **Recurring weekly job-search review** — deferred to Phase 5 (depends on dashboard data presentation)
- **MCP server for Claude Desktop** — still deferred from prior phases

### Decision ledger

| # | Decision | Choice | Rationale |
|---|---|---|---|
| P4-Q1 | Phase 4 scope | Data layer + JD analyzer + precheck; dashboard deferred to Phase 5 | Foundation-first sequencing — Phase 5 builds on a battle-tested data layer rather than the two evolving together |
| P4-Q2 | Tracker storage location | `~/.brains-resume/tracker.db` (user-level), NOT `./output/` | Tracker is durable career data, must survive project moves and `rm -rf` of the working directory; breaks the v1.0 "everything in output/" convention but the convention was about per-project artifacts |
| P4-Q3 | Tracker integration model | Opt-in — existing workflows prompt at end, don't auto-register | Privacy-respecting; users who never engage with the tracker never create the db file; no breaking changes |
| P4-Q4 | JD analyzer finding catalog | 6 categories: SOFT_CULTURE, MASKING_COST, EVIDENCE_OF_FLEX, REQ_VS_NICE_PARSING, ROLE_FIT_SCORE, DUPLICATE_APPLICATION | Each category surfaces a different ND-relevant signal; the mix gives the user a multi-axis read on the JD without averaging it to a single number |
| P4-Q5 | Role-fit scoring approach | Token-overlap + simple semantic match against user-supplied focus areas | Deterministic, no LLM call, no embedding model dependency; refines in Phase 5 if needed |
| P4-Q6 | Pre-application check operating mode | 6 conversational questions, one per turn, never blocks submission | Coaching not gating; the user always submits or doesn't — the workflow is informational |
| P4-Q7 | Healthy weekly rate default | NO default — asked once, stored in `profile.json` per user | The skill never tells the user "you should apply 5/week" because that figure varies enormously by sensory bandwidth and life context; ND-respecting answer is "you tell me, I'll help you stay near it" |
| P4-Q8 | CLI namespace | `/brains-track` with subcommands rather than 5 separate commands | Cleaner top-level slash-command space; subcommand discoverability handled by `--help` and the workflow reference |
| P4-Q9 | Foreign-key behaviour on file deletion | `file_path` columns nullable; mismatched paths surface as broken-link warnings, not crashes | Real users delete files; the tracker row is more durable than the underlying artifact |
| P4-Q10 | Schema migration support | YES — migrations table + numbered migration scripts from day one | Phase 5 will almost certainly want schema changes (tags, custom statuses, etc.); building in migration from the start avoids painful rewrites |
| P4-Q11 | Brand on tracker output | Branded coaching artifacts (markdown summaries carry BRAINS coaching frame); the SQLite db itself is data, not branded | Tracker is internal coaching, same category as the review coaching report |
| P4-Q12 | Network/referral lane | `channel` enum includes `referral` for v1.2.0; first-class network-tracking lane deferred to Phase 5 | Lightweight inclusion now; full design later when it can co-evolve with dashboard pages |

## 3. Architecture overview

Same hybrid skill structure as v1.1.0: always-loaded `SKILL.md` core + on-demand reference files + deterministic Python scripts + validators. Adds a new user-level state directory and a tracker Python module.

### New user-level state directory

```
~/.brains-resume/
├── tracker.db         # SQLite — 5 entity tables + migrations table
└── profile.json       # focus areas, healthy weekly application rate
```

This directory is created on first tracker write. Users who never run `/brains-track` or `/brains-precheck` never have this directory. The directory is OUTSIDE any git repo by design — it's the user's durable career data, not project state.

### New scripts/tracker/ Python module

```
scripts/tracker/
├── __init__.py
├── db.py              # connection, schema bootstrap, migrations, transaction helpers
├── models.py          # dataclasses for the 5 entities + Outcome event enum
├── add.py             # add_resume_version, add_jd, add_application, record_outcome, etc.
├── query.py           # list_applications, weekly_summary, efficacy_by_template, find_duplicates
└── profile.py         # read_profile, write_profile (focus areas + healthy rate)
```

The public API is `scripts.tracker.add` + `scripts.tracker.query` + `scripts.tracker.profile`. Phase 5's Streamlit dashboard imports these directly — zero SQL outside `db.py`.

### New JD analyzer

```
scripts/validators/
└── jd_analyzer.py     # finding catalog + role-fit scoring
```

Pattern mirrors existing `bias_scan.py` and `integrity_check.py`: pure-function entry point, structured result with findings list, no I/O beyond the optional duplicate-application tracker lookup (which goes through `scripts.tracker.query.find_duplicates`).

### Three new workflow references

```
references/workflows/
├── jd-analyze.md
└── pre-application-check.md
```

Plus integration touch-ups (single paragraph each) on the four existing workflow files that gain the opt-in tracker prompt.

### Three new slash commands

```
commands/
├── brains-jd-analyze.md
├── brains-precheck.md
└── brains-track.md     # composite with subcommands
```

## 4. Data model detail

### 4.1 Schema (SQLite)

All tables: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `created_at TEXT NOT NULL`, `archived_at TEXT NULL` (soft-delete).

**`resume_versions`**

| Column | Type | Notes |
|---|---|---|
| `file_path` | TEXT NULL | Path to DOCX/PDF; nullable so row survives file deletion |
| `template` | TEXT NOT NULL | One of `chronological`/`functional`/`hybrid`/`executive` |
| `focus_areas` | TEXT NOT NULL | JSON list of strings — user's tags for this version |
| `parent_id` | INTEGER NULL | FK to resume_versions(id) — tracks tailored-from lineage |
| `tagged_jd_id` | INTEGER NULL | FK to jds(id) — if this version was tailored for a specific JD |

**`cover_letters`**

| Column | Type | Notes |
|---|---|---|
| `file_path` | TEXT NULL | Path to DOCX/PDF |
| `resume_version_id` | INTEGER NOT NULL | FK |
| `jd_id` | INTEGER NOT NULL | FK |
| `template` | TEXT NOT NULL | `formal-business` or `modern-clean` |

**`jds`**

| Column | Type | Notes |
|---|---|---|
| `source` | TEXT NOT NULL | Enum: `paste` / `url` / `screenshot` |
| `source_ref` | TEXT NULL | URL or filename if applicable |
| `company` | TEXT NOT NULL | Parsed or user-confirmed |
| `role_title` | TEXT NOT NULL | Parsed or user-confirmed |
| `raw_text` | TEXT NOT NULL | Full JD text |
| `analyzer_findings` | TEXT NOT NULL | JSON dump of jd_analyzer output |
| `focus_areas_required` | TEXT NOT NULL | JSON list — parsed must-haves |
| `focus_areas_nice` | TEXT NOT NULL | JSON list — parsed nice-to-haves |

**`applications`**

| Column | Type | Notes |
|---|---|---|
| `jd_id` | INTEGER NOT NULL | FK |
| `resume_version_id` | INTEGER NOT NULL | FK |
| `cover_letter_id` | INTEGER NULL | FK; some channels don't require a CL |
| `submitted_at` | TEXT NOT NULL | ISO-8601 timestamp |
| `channel` | TEXT NOT NULL | Enum: `linkedin` / `agency` / `direct` / `referral` / `other` |
| `agency_name` | TEXT NULL | Required when channel = `agency` |
| `recruiter_contact` | TEXT NULL | Free-text |
| `notes` | TEXT NULL | Free-text — pre-application check answers concatenated here |

**`outcomes`**

| Column | Type | Notes |
|---|---|---|
| `application_id` | INTEGER NOT NULL | FK |
| `event_type` | TEXT NOT NULL | Enum: `acknowledged` / `callback` / `phone_screen` / `first_round` / `second_round` / `take_home` / `offer` / `rejection` / `ghosted` / `withdrew` |
| `event_date` | TEXT NOT NULL | ISO-8601 timestamp |
| `notes` | TEXT NULL | Free-text |

**`migrations`**

| Column | Type | Notes |
|---|---|---|
| `version` | INTEGER PRIMARY KEY | Sequential migration number |
| `applied_at` | TEXT NOT NULL | ISO-8601 timestamp |
| `description` | TEXT NOT NULL | One-line summary |

### 4.2 Migration strategy

Numbered migration scripts in `scripts/tracker/migrations/`:

```
scripts/tracker/migrations/
├── 0001_initial_schema.py    # creates all 5 tables + migrations table
├── 0002_*.py                 # future migrations
```

`db.py:open_db()` runs pending migrations on every connection open. Idempotent — re-running is safe. Phase 5 schema changes get migration `0002`, `0003`, etc.

### 4.3 Public Python API

Phase 5's dashboard imports these directly:

```python
# scripts/tracker/add.py
def add_resume_version(file_path: Optional[Path], template: str, 
                       focus_areas: list[str], parent_id: Optional[int] = None,
                       tagged_jd_id: Optional[int] = None) -> int: ...

def add_jd(source: str, source_ref: Optional[str], company: str, 
           role_title: str, raw_text: str, 
           analyzer_findings: dict) -> int: ...

def add_application(jd_id: int, resume_version_id: int, 
                    cover_letter_id: Optional[int], submitted_at: datetime,
                    channel: str, agency_name: Optional[str] = None,
                    recruiter_contact: Optional[str] = None, 
                    notes: Optional[str] = None) -> int: ...

def record_outcome(application_id: int, event_type: str, 
                   event_date: datetime, notes: Optional[str] = None) -> int: ...

# scripts/tracker/query.py
def list_applications(company: Optional[str] = None, since: Optional[date] = None,
                      status: Optional[str] = None) -> list[ApplicationRow]: ...

def weekly_summary(now: Optional[datetime] = None) -> WeeklySummary: ...

def efficacy_by_template() -> dict[str, EfficacyRow]: ...

def find_duplicates(company: str, role_title: str, 
                    within_days: int = 60) -> list[ApplicationRow]: ...

# scripts/tracker/profile.py
def read_profile() -> Profile: ...
def write_profile(profile: Profile) -> None: ...
```

`Profile` carries `focus_areas: list[str]` and `healthy_weekly_rate: Optional[int]`.

## 5. JD analyzer detail

### 5.1 Finding catalog

| Code | Severity | Detection method | What it surfaces |
|---|---|---|---|
| `JD_RED_FLAG_SOFT_CULTURE` | MEDIUM (or HIGH if 3+ hits) | Keyword/regex list (`rockstar`, `ninja`, `wear many hats`, `fast-paced environment`, `we're a family`, `work hard play hard`, `flexible attitude`, etc.) | Culture markers that historically correlate with high-masking demands |
| `JD_MASKING_COST` | MEDIUM (informational) | Keyword list (`high-EQ`, `stakeholder management`, `client-facing presentations`, `open-plan office`, `phone-heavy`, `frequent context switching`) | Role demands that exact a higher cost for ND candidates; not a red flag, but informs disclosure and energy-budget thinking |
| `JD_EVIDENCE_OF_FLEX` | POSITIVE (boosts role-fit score) | Keyword list (`remote-first`, `async-first`, `flexible hours`, `accommodations available`, `written-comms culture`, explicit hybrid-day count, parental-leave specifics) | Concrete signals that the employer has actually thought about flexibility, not just used it as a buzzword |
| `JD_REQ_VS_NICE_PARSING` | INFO | Heading detection (`Required` / `Must-have` / `Essential` vs `Nice-to-have` / `Preferred` / `Bonus`) + bulleted list extraction | Separates the must-haves from the wishlist so the user isn't intimidated by an inflated requirements list |
| `JD_ROLE_FIT_SCORE` | INFO (0-100) | Token-overlap + simple semantic match between user's `profile.focus_areas` and JD's parsed required + nice lists | Numeric signal of fit; weighted: required matches > nice matches; capped at 100 |
| `JD_DUPLICATE_APPLICATION` | HIGH | Tracker query `find_duplicates(company, role_title, within_days=60)` | Prevents accidental re-application; the precheck workflow lets the user confirm if intentional |

All findings carry: `code`, `severity`, `excerpt` (where in JD it appeared), `suggestion` (what the user might do with this signal).

### 5.2 Scoring logic for `JD_ROLE_FIT_SCORE`

Deterministic, no LLM:

```
required_matches = count(focus_areas ∩ jd.focus_areas_required)
nice_matches     = count(focus_areas ∩ jd.focus_areas_nice)

# Weighted: each required match worth 2x a nice match
raw_score = (required_matches * 2 + nice_matches)
max_possible = (len(jd.focus_areas_required) * 2 + len(jd.focus_areas_nice))

score = min(100, round(100 * raw_score / max(1, max_possible)))
```

Semantic match uses simple normalisation (lowercase, strip punctuation, stem common variants like `python`/`pythonic`/`python3`). No embeddings, no LLM call. Phase 5 may revisit if precision/recall warrants it.

### 5.3 Input parsing

Reuses existing `scripts/parsers/jd_url_fetch.py` (shipped in v1.0) for URL inputs. Paste input is direct text. Screenshot input is OCR-out-of-scope (consistent with v1.0); user pastes text from the screenshot.

## 6. Pre-application sanity check detail

### 6.1 Trigger conditions

- User runs `/brains-precheck` directly.
- User has just completed `brains-tailor` and answered "yes" or "use precheck now" to the opt-in prompt.
- User has just completed `brains-cover-letter` for an application they intend to submit immediately, and they explicitly opted in.

### 6.2 The six questions

One per turn. Workflow does NOT block submission — every question can be answered, deferred, or skipped.

| Q | Question | Source | Recorded in |
|---|---|---|---|
| 1 | **Duplicate check.** "Did you apply to {company} on {date}? Continue?" (Asked only if `find_duplicates()` returns rows) | tracker | If user proceeds, gets a `duplicate_acknowledged: True` flag in `notes` |
| 2 | **JD findings recap.** "Quick recap of the JD findings: {N} soft-culture red flags, {M} masking-cost markers, {K} evidence-of-flex signals. Want to review before submitting?" | jd_analyzer result | Notes field — `findings_acknowledged: True/declined` |
| 3 | **Fit-or-pressure.** "Are you applying because the role genuinely fits, or because you feel pressure to apply somewhere this week? One-line answer." | User | Verbatim in notes |
| 4 | **Pacing check.** "You've submitted {N} applications in the last 7 days. Your stated healthy rate is {M}/week. Continue?" (If healthy rate not set, asks once and saves to profile.json) | tracker.weekly_summary() | `pacing: above/at/below_target` |
| 5 | **Cover letter check.** "This application doesn't have a cover letter attached. Most {channel} applications expect one. Add one now?" (only fires if cover_letter_id is null and channel suggests CL is standard) | conditional | If skipped, `cover_letter_omitted_deliberately: True` |
| 6 | **Channel + agency.** "How are you submitting? (linkedin / agency / direct / referral / other) — If agency, which one?" | User | `applications.channel` and `applications.agency_name` columns |

### 6.3 Output

A new row in the `applications` table with all six answers represented either in dedicated columns or in the `notes` field (JSON-encoded sub-fields). The application id is surfaced to the user so they can refer to it later when logging outcomes.

The workflow concludes with a short summary: "Application #N registered for {company} / {role}. To log outcomes later: `/brains-track update {N} <event-type>`."

## 7. Integration with existing workflows

Four existing workflows get a single end-of-workflow paragraph added to their reference doc. The actual integration is conversational — Claude reads the reference, sees the prompt instruction, and asks the user.

**End-of-workflow prompt (verbatim text Claude will deliver):**

> "Saved to `{file_path}`. Track this in the application tracker? (yes runs the pre-application sanity check; later registers it without the check; no skips tracking entirely)"

Workflows touched: `brains-tailor`, `brains-cover-letter`, `brains-review`, `brains-check`. Other workflows (`brains-create`, `brains-edit`, `brains-disclosure`, `brains-linkedin-ingest`, `brains-linkedin-improve`, `brains-consolidate`, `brains-career-change`) don't get the prompt because their output isn't a candidate-for-submission artifact.

Users who consistently answer "no" never create the tracker db. The opt-in is preserved indefinitely.

## 8. CLI — `/brains-track` slash command

Single command with subcommands. The slash command file describes the subcommand surface; Claude routes by reading the user's argument.

| Subcommand | Behaviour |
|---|---|
| `/brains-track add` | Interactive add of an application (when the user already submitted without going through precheck and wants to backfill) |
| `/brains-track update <id> <event-type> [date] [notes]` | Append an outcome event to an existing application |
| `/brains-track list [--company X] [--since YYYY-MM-DD] [--status open\|closed]` | Filtered table of applications + latest outcome |
| `/brains-track summary` | Pipeline funnel + this-week pacing + healthy-rate comparison |
| `/brains-track focus-areas` | View or edit stored focus areas (one-line list, comma-separated) |
| `/brains-track healthy-rate` | View or set the user's healthy weekly application rate |

All subcommands return markdown rendered in chat. Tables use the same BRAINS coaching artifact frame as the existing review report.

## 9. SKILL.md router updates

Three new router rows added to the workflow-router table:

```markdown
| Analyse a job description for ND-relevant signals | `references/workflows/jd-analyze.md` |
| Run a pre-application sanity check before submitting | `references/workflows/pre-application-check.md` |
| Manage the application tracker | `commands/brains-track.md` (no separate reference — slash command is self-describing) |
```

Capability-menu update: three new "Live" rows. Slash-command-list sentence updates from "eleven commands" to "fourteen commands" and includes `jd-analyze`, `precheck`, `track` in the list.

## 10. Testing

Same TDD discipline as Plan 3.

### 10.1 Tracker tests (`tests/tracker/`)

Per-helper unit tests using `tmp_path` for isolated SQLite db (override `BRAINS_TRACKER_DB_PATH` env var to point at the tmp file):

- `test_db.py` — schema bootstrap, migrations apply cleanly, reopening db doesn't re-run migrations
- `test_add.py` — each `add_*` function inserts the expected row, foreign keys enforced
- `test_query.py` — `list_applications` filters work, `weekly_summary` returns correct counts, `efficacy_by_template` aggregates correctly, `find_duplicates` honours `within_days`
- `test_profile.py` — `read_profile` / `write_profile` round-trip; missing file returns empty profile, doesn't crash

### 10.2 JD analyzer tests (`tests/validators/test_jd_analyzer.py`)

Fixture-driven, mirroring `tests/fixtures/bias_fixtures.py` structure. New `tests/fixtures/jd_analyzer_fixtures.py` containing one synthetic JD per finding code:

- `RED_FLAG_HEAVY_JD` — 4+ soft-culture hits → HIGH severity cluster
- `MASKING_COST_HEAVY_JD` → MEDIUM findings
- `EVIDENCE_OF_FLEX_HEAVY_JD` → POSITIVE findings, boosts role-fit
- `WELL_PARSED_JD` → REQ_VS_NICE parsing succeeds, both lists populated
- `CLEAN_NEUTRAL_JD` → 0 findings of red-flag or masking-cost type
- Role-fit score tests with synthetic focus-area + JD-requirements combinations

### 10.3 Pre-application check smoke test

Synthetic JD fixture → analyzer → tracker add → precheck flow simulated as a sequence of asserts (the workflow itself is Claude-driven; the smoke test exercises the deterministic supporting pieces).

### 10.4 End-to-end smoke tests

One per new workflow:
- `test_smoke_jd_analyze_workflow.py` — analyzer runs on fixture, findings persisted to tracker, summary returned
- `test_smoke_precheck_workflow.py` — synthetic application data flows through precheck → application row created
- `test_smoke_track_workflow.py` — add an application, record an outcome, query summary

Expected total test count delta: ~35-45 new tests. Suite goes from 140 → ~180.

## 11. Privacy and brand

### 11.1 Privacy

All six v1.0 guarantees still hold. New surface area:

- **`~/.brains-resume/` is user-level local-only.** Never committed (not in any git repo by default). No outbound network. No telemetry.
- **`tracker.db` is gitignored at the user-home level**. Since the directory is outside any project repo, this is automatic — there's nothing to gitignore.
- **One-time privacy notice extended**: on first tracker write, surface "Application data will be stored locally at `~/.brains-resume/tracker.db`. Nothing is transmitted. You can delete the entire directory at any time to remove all tracker history."
- **Soft-delete semantics**: archiving a row (via `archived_at`) is the standard delete. A hard-delete subcommand (`/brains-track purge <id>`) is available for users who want a row gone permanently.

### 11.2 Brand-on-output rule extension

| New artifact | Branded? | Why |
|---|---|---|
| Tracker markdown summaries (CLI output) | BRAINS branded — coaching artifact frame | Internal coaching, same category as review reports |
| `tracker.db` SQLite file | Not branded — it's data, not a presented artifact | Branding doesn't apply to raw data storage |
| `profile.json` | Not branded — config | Same |
| JD analyzer markdown report (if saved to output/) | BRAINS branded | Internal coaching artifact |
| Pre-application check markdown summary (if saved to output/) | BRAINS branded | Same |

`references/brand-application.md` updated to reflect these decisions.

## 12. Release plan

Single release tag at end of phase: **v1.2.0**.

- All existing 140 tests stay green, plus ~35-45 new tests
- CHANGELOG v1.2.0 entry covering: tracker data layer, JD analyzer, pre-application check, three new slash commands, opt-in integration with existing workflows, schema migration support
- README updated: slash-command cheat sheet + new "Tracking applications" section
- `references/brand-application.md` updated for new artifact types
- Claude Project bundle rebuilt to include new reference docs (note: tracker scripts don't ship in the bundle — claude.ai can't run them, so the tracker is Claude-Code-only for v1.2.0)
- `v1.2.0` git tag

## 13. Implementation phasing

The implementation plan (separate document, produced via `writing-plans`) will sequence the work to keep the test suite green at each commit:

**Recommended phase order inside the plan:**

1. **Tracker data layer first** — `scripts/tracker/` module, schema, migrations, profile.json helpers, all unit tests. No workflow exposure yet; the data layer is internally testable.
2. **JD analyzer second** — `scripts/validators/jd_analyzer.py` with finding catalog and role-fit scoring. Reuses existing JD parsers from v1.0. Unit tests against synthetic fixtures.
3. **Slash commands + workflow references third** — `brains-jd-analyze`, `brains-precheck`, `brains-track`. Their workflow references depend on the tracker + analyzer being in place.
4. **Opt-in integration fourth** — single-paragraph edits to the four existing workflow references that gain the end-of-workflow tracker prompt.
5. **Release polish fifth** — SKILL.md router, README, brand-application.md, CHANGELOG, bundle rebuild, v1.2.0 tag.

The implementation plan will break each phase into TDD tasks with checkbox tracking, matching the Plan 3 format.

---

**Points worth a second look during spec review:**

- The **`JD_DUPLICATE_APPLICATION`** finding is the only finding that requires a live tracker query rather than pure pattern-matching. Implementation needs to handle the case where the tracker db doesn't exist yet (return empty list, no crash).
- The **role-fit scoring** is intentionally simple (token overlap + light normalisation). If precision is poor on real JDs the user should flag it — we may need to revisit in a v1.2.1 patch with stemming/synonym expansion.
- The **healthy-rate question** in the pre-application check fires every time pacing exceeds target. We should consider a "I know, suppress this for this week" option so it doesn't become noisy after the user has acknowledged once. Implementation can default to "always ask" and add suppression later if it proves annoying.
- The **end-of-workflow tracker prompt** is added to four workflow references via a verbatim paragraph. Worth a review pass to ensure the wording doesn't pressure the user into opting in.
