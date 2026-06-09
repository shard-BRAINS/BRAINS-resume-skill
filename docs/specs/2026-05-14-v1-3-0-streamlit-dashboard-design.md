# v1.3.0 — Streamlit Dashboard — Design Specification

<!-- readability: skip -->
<!-- Historical planning/spec document; predates the BRAINS readability standard (adopted 2026-05-29). -->

**Version:** Draft v1
**Date:** 2026-05-14
**Status:** Awaiting user review
**Target release:** v1.3.0
**Builds on:** v1.2.1 (tracker data layer, JD analyzer, pre-application check, AI-signal validator all shipped and pushed)
**Successor:** Phase 6+ — MCP server for Claude Desktop, sibling skills (interview prep, salary), or further dashboard enhancements

---

## 1. Purpose

Build a local Streamlit dashboard that surfaces the data layer the user has been building toward across Phases 4 and 4a. The tracker holds resumes, cover letters, JDs, applications, and outcomes; the AI-signal validator produces a per-text quality score; the JD analyzer produces per-JD findings; the profile holds focus areas and the user's self-defined healthy weekly application rate. None of this is visible at a glance today — every query goes through CLI markdown rendering.

The dashboard makes the data inspectable, navigable, and analyzable in a browser-based UI that runs entirely on localhost. It is BRAINS Incubator branded — Gold Deep `#D99518` accents, dark theme base, Atkinson Hyperlegible body font — applied to a structural layout that mirrors the user's personal TSE Tools finance dashboard (top tab navigation, summary tile row, dense data tables with notes and external-link clusters, mini sparklines, twin side-by-side time-ordered panels).

The dashboard reads from the existing SQLite store via the existing `scripts.tracker.query` public API. It writes only through that same API (sidebar edits to focus areas and healthy weekly rate). Privacy, brand, and architectural conventions inherit from prior phases without modification.

## 2. Scope

### In scope for v1.3.0

1. **Dashboard package** — `scripts/dashboard/` with the entry-point app, launcher CLI, style module, cached data wrappers, per-tab modules, and pure data-prep functions
2. **Seven tabs in single-page top-nav layout** — Overview, Resumes, Cover Letters, JDs, Applications, Analytics, Pacing
3. **Sidebar** — Focus areas editor, healthy weekly rate editor, global refresh, BRAINS Incubator mark, version + git SHA footer
4. **BRAINS Incubator branding** — dark theme, Gold Deep accents, Atkinson Hyperlegible, applied via `style.py` CSS injection consulting the `brains-brand` skill at implementation time
5. **CLI launch entry** — `brains-resume-dashboard` registered via `pyproject.toml [project.scripts]`; invokes `streamlit run scripts/dashboard/app.py` with sensible defaults
6. **`/brains-dashboard` slash command** — prints the launch command for the user to copy
7. **Cached data wrappers** — `scripts/dashboard/data.py` thin caching layer over `scripts.tracker.query` using `@st.cache_data(ttl=60)`; manual refresh per tab
8. **Pure data-prep modules** — `scripts/dashboard/prep/` for funnel, sparkline, trends, idle-state detection (no Streamlit imports, fully unit-testable)
9. **Streamlit dependency** — `streamlit>=1.30.0` and `plotly>=5.18.0` added to `pyproject.toml` dependencies
10. **Streamlit smoke test** — import test plus one `streamlit.testing.v1.AppTest` happy-path interaction test (Overview tab renders without exceptions)
11. **Release polish** — SKILL.md updates, README "Launching the dashboard" section, brand-application.md update for the dashboard artifact type, CHANGELOG entry, Claude Project bundle rebuild, version bump to 1.3.0, `v1.3.0` tag

### Out of scope for v1.3.0

- **Auto-launch from a slash command** — `/brains-dashboard` prints the launch command rather than spawning a long-running Streamlit subprocess from Claude Code (which doesn't own terminal sessions cleanly)
- **Write paths beyond profile.json sidebar edits** — applications, outcomes, resumes, etc. are read-only in the dashboard. Edits happen via the existing CLI workflows (`/brains-track update`, etc.). The dashboard is for analysis, not data entry.
- **Multi-user collaboration / remote hosting** — local single-user only, just like the existing tracker
- **Auth, accounts, sessions** — no user accounts; the dashboard is local-only and trusts the operating system's session
- **Real-time push updates** — pull-based with 60s cache TTL and manual refresh is sufficient for a single-user local dashboard
- **Sibling-skill integration (interview prep, salary)** — those skills don't exist yet; the dashboard is resume-skill-only
- **MCP server for Claude Desktop** — still deferred from prior phases
- **Anonymized community efficacy data** — privacy-design problem; deferred to Phase 6+

### Decision ledger

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 5b-Q1 | Multi-page (`pages/` directory) vs single-page (`st.tabs`) | **Single-page with `st.tabs`** | Matches TSE Tools top-nav exactly; Streamlit's default multi-page nav lives in the left sidebar |
| 5b-Q2 | Launch mechanism | `brains-resume-dashboard` CLI entry + `/brains-dashboard` slash command prints the launch command | Long-running Streamlit subprocess shouldn't be owned by Claude Code; user keeps terminal control |
| 5b-Q3 | Streamlit + Plotly as required vs optional deps | **Required** (in main `dependencies`, not `[project.optional-dependencies]`) | Dashboard is core v1.3.0 functionality, not a plugin; users who install the skill get the dashboard |
| 5b-Q4 | Code organization | One module per tab in `scripts/dashboard/tabs/` + separate `scripts/dashboard/prep/` for pure data-prep | Tab modules stay focused (<200 lines each); prep functions unit-testable without Streamlit |
| 5b-Q5 | Data refresh model | `@st.cache_data(ttl=60)` on query wrappers + per-tab manual `↻ Refresh` button | Fast within a session; manual override available; no SSE or WebSocket complexity |
| 5b-Q6 | BRAINS Incubator branding application | CSS injection via `style.py` at app startup; consult `brains-brand` skill at implementation time for the exact Incubator-specific spec | Skill is the authoritative source of brand; spec commits to "use it" rather than locking in possibly-stale values |
| 5b-Q7 | Write paths | Read-only except for profile.json sidebar edits | Keeps the dashboard a window onto the data, not a competing entry surface; reduces failure modes |
| 5b-Q8 | Testing strategy | TDD on pure prep functions + cached-wrapper light tests + Streamlit smoke import + one AppTest interaction test | Pragmatic given Streamlit's testing constraints; the data layer is well-tested via Phase 4 |
| 5b-Q9 | Dashboard artifact branding | BRAINS-branded internal coaching artifact (rendered in the dashboard, not exported to disk by default) | Consistent with tracker CLI output rule from v1.2.0 |
| 5b-Q10 | Visual reference anchor | User's personal TSE Tools dashboard (screenshot shared 2026-05-14) | Matching a layout the user already knows works reduces learning curve and signals the dashboard is built for their actual habits |

## 3. Architecture overview

Same hybrid skill structure as v1.2.x (always-loaded `SKILL.md` core + on-demand reference files + deterministic Python). Adds a new `scripts/dashboard/` package that consumes the v1.2.0 tracker public API and the v1.2.1 AI-signal validator. The dashboard is a separate concern from the workflows — it does not invoke or modify them, only reads their persisted output.

### File structure

```text
scripts/dashboard/
├── __init__.py                 # one-line module docstring
├── app.py                      # main Streamlit entry; st.tabs + sidebar
├── launch.py                   # CLI entry point (invoked by `brains-resume-dashboard`)
├── style.py                    # BRAINS Incubator CSS injection
├── data.py                     # cached query wrappers around scripts.tracker.query
├── tabs/
│   ├── __init__.py
│   ├── overview.py             # summary tiles + sparklines + funnel + idle-state + twin panels
│   ├── resumes.py              # versions table with focus areas + AI-signal score
│   ├── cover_letters.py        # table linked to resume + JD
│   ├── jds.py                  # analyzer findings + applications attached
│   ├── applications.py         # sortable table; outcome filter; date filter
│   ├── analytics.py            # efficacy by template/channel; AI-signal correlation
│   └── pacing.py               # this-week count vs healthy rate; sensory-load nudge
└── prep/                       # pure data-prep functions (no Streamlit imports)
    ├── __init__.py
    ├── funnel.py               # applications → callbacks → interviews → offers
    ├── sparkline.py            # AI-signal trend, pacing trend, callback-rate trend
    ├── trends.py               # rolling weekly metrics
    └── idle_states.py          # "no anomalies today" callout detection

.streamlit/
└── config.toml                 # dark theme baseline + page config

commands/
└── brains-dashboard.md         # slash command that prints the launch command

tests/dashboard/
├── __init__.py
├── prep/
│   ├── __init__.py
│   ├── test_funnel.py
│   ├── test_sparkline.py
│   ├── test_trends.py
│   └── test_idle_states.py
├── test_data.py                # cached-wrapper light tests
├── test_app_import.py          # smoke import test
└── test_app_overview_render.py # AppTest happy-path interaction test
```

### Updated files

- `pyproject.toml` — add `streamlit>=1.30.0` and `plotly>=5.18.0` to `dependencies`; add `[project.scripts]` entry `brains-resume-dashboard = "scripts.dashboard.launch:main"`; bump version to 1.3.0
- `SKILL.md` — tooling-notes section gains a "Dashboard" entry; slash-command list 15 → 16 commands; "fourteen workflows" stays unchanged (dashboard is a tool, not a workflow); version bump to 1.3.0
- `README.md` — new "Launching the dashboard" section after "Tracking applications"
- `references/brand-application.md` — split-rule table gains a "Dashboard UI" row
- `docs/claude-project-setup.md` — new sub-section noting the dashboard is Claude-Code-only
- `CHANGELOG.md` — v1.3.0 entry
- Claude Project bundle rebuild (dashboard package not shipped; bundle only contains references and SKILL.md as before)

## 4. Tab detail

### 4.1 Overview

The most complex tab. Five sections, top-to-bottom:

**Summary tile row** (5 tiles, equal width):

| Tile | Metric | Delta (vs last week) |
|---|---|---|
| Applications | Count (lifetime) | Last 7 days |
| Callbacks | Count + rate % | Rate delta vs prior 30-day rolling |
| Interviews | Count + rate % | Rate delta vs prior 30-day rolling |
| Offers | Count (lifetime) | Last 30 days |
| Pacing | This-week count / healthy_weekly_rate | vs healthy rate target |

Rendered via `st.metric()` with `delta` argument. Color is automatic via Streamlit (green up arrow / red down arrow). Custom CSS in `style.py` recolors arrows to Gold Deep when positive in pacing context (over-target may be undesirable for sensory-bandwidth users).

**Mini sparkline row** (3 cards, equal width):

| Card | Data |
|---|---|
| AI-signal trend | Average AI-signal score across all resume versions, rolling 30 days |
| Applications per week | Last 8 weeks bar chart |
| Callback rate trend | 30-day rolling callback rate, last 90 days |

Rendered via Plotly (Streamlit's native charts can't strip axes/grid cleanly for sparkline look). Each card: title, current value, sparkline only (no axes, no grid, no legend), trailing arrow indicating up/down direction.

**Idle-state callouts** (rendered when applicable):

- "No applications submitted this week — sensory-bandwidth respected." (when 0 applications in 7d)
- "No pending outcomes — every application has been responded to." (when all applications have terminal outcomes)
- "AI-signal score consistently low (avg {X} across last 5 resumes)." (when avg AI-signal score < 10 across recent versions)

Callouts use `st.success()` styled with Gold Deep accent rather than default green to match brand. Plural callouts render as a vertical stack.

**Funnel chart** (Plotly):

Applications → Callbacks → Phone screens → 1st rounds → 2nd rounds → Offers and Rejections. Counted from lifetime data. Plotly's `funnel_chart` with custom colors (Gold Deep for advance steps, neutral dark grey for rejection terminus).

**Twin side-by-side panels** (bottom of tab):

- **Pending callbacks** (left): applications with `submitted_at >= now - 30 days` AND no terminal outcome AND no `acknowledged` or `callback` event yet. Sorted by days-since-submission descending.
- **Scheduled interviews** (right): applications with a recent `phone_screen` / `first_round` / `second_round` event in last 14 days. Shows expected next-step timing.

Each panel is a compact table with company / role / days-since column. Both panels use `st.column_config.LinkColumn` to deep-link to the Applications tab filtered for that row.

### 4.2 Resumes

Single dense table. Columns:

| Column | Type | Notes |
|---|---|---|
| Version ID | int | Sort key |
| File | LinkColumn | Resolves to local file path (DOCX/PDF) if file exists |
| Template | text | chronological / functional / hybrid / executive |
| Focus areas | text | Comma-joined from JSON column |
| AI-signal score | number | Color-coded: green <10, amber 10-29, red 30+ |
| Tagged JD | int (FK) | LinkColumn to JDs tab if non-null |
| Parent version | int (FK) | Tailored-from lineage |
| Created | date | YYYY-MM-DD |
| Applications using | int | Count |

Sort defaults to created date descending. Filter row above table: by template, by focus area (multi-select), by AI-signal score threshold, by has-applications-attached.

Manual `↻ Refresh` button top-right.

### 4.3 Cover letters

Same shape as Resumes. Additional columns: linked resume version, linked JD. Same filter row + refresh.

### 4.4 JDs

Two-pane layout:

- **Left:** table of JDs (company, role, source, role-fit score against current profile focus areas, applications-attached count, created date)
- **Right:** expandable cards for the selected JD's analyzer findings, with cross-link to `references/ai-signal-patterns.md` for finding code definitions

Filter: by company (text), by date range, by has-applications-attached.

### 4.5 Applications

Single dense table. Columns:

| Column | Type | Notes |
|---|---|---|
| App ID | int | Sort key |
| Company | text | From JD |
| Role | text | From JD |
| Submitted | date | YYYY-MM-DD |
| Channel | text | linkedin / agency / direct / referral / other |
| Agency | text | Only if channel=agency |
| Resume | LinkColumn | Deep-links to Resumes tab |
| Cover letter | LinkColumn | Deep-links to Cover-letters tab |
| Latest outcome | text | event_type from outcomes |
| Outcome date | date | |
| Days since submitted | int | Computed |

Filters: by company, by status (open / closed / all), by submitted-since date, by channel, by has-cover-letter.

Read-only — outcomes are logged via the existing `/brains-track update <id> <event>` CLI workflow. Future v1.4 may add an inline outcome editor in the dashboard.

### 4.6 Analytics

Three chart sections:

1. **Efficacy by template** — bar chart showing per-template submitted / callback / interview / offer counts (data from `efficacy_by_template()`)
2. **Efficacy by channel** — bar chart showing per-channel breakdown
3. **AI-signal correlation** — scatter plot: AI-signal score (x) vs callback occurred (y, jittered 0/1) — visualises whether lower AI-signal scores correlate with higher callback rates

Each chart has its own `↻ Refresh` button.

### 4.7 Pacing

Single-column layout focused on sensory-bandwidth-aware messaging:

- Current pacing tile: applications-this-week count vs `profile.healthy_weekly_rate`
- Status banner:
  - **Above target:** "{N} applications this week — above your stated healthy rate of {M}/week. Consider pausing." (no shame language; informational)
  - **At target:** "At your healthy rate this week."
  - **Below target:** "Under your healthy rate this week — bandwidth available if you want to use it."
  - **No target set:** prompt to set healthy_weekly_rate in sidebar
- 8-week pacing trend chart (bar chart)
- "Sensory-load notes" panel — a text area persisted to `profile.json` (added schema field `pacing_notes: Optional[str]`) where the user can journal context — what's been overwhelming, what's been sustainable

### 4.8 Sidebar

Persistent across all tabs:

- BRAINS Incubator mark (top, light-bg variant)
- "Profile" section: focus areas (multi-line text input or chip-style multiselect), healthy weekly rate (number input), save button
- "Refresh" section: global `↻ Refresh all` button (clears entire `@st.cache_data` cache)
- "Version" footer: `v1.3.0 · {git_sha}` (sha resolved at launch from `git rev-parse --short HEAD`; falls back to `unknown` if not in a git repo)

## 5. BRAINS Incubator branding application

The `brains-brand` skill is the authoritative source. At implementation time (Phase 2 of the plan, Task 7), the implementer invokes the skill to retrieve current Incubator-specific specs. Spec commits to:

- **Dark theme baseline** via `.streamlit/config.toml`
- **Gold Deep `#D99518` accents** on H1 headings, tile-row separators, chart highlight color, sparkline trend lines, primary button background, sidebar section dividers
- **Atkinson Hyperlegible** body font (accessibility-first; same font used in coaching reports)
- **Inter Bold** for tile labels and section headings (matches coaching-report typography)
- **BRAINS mark light-bg variant** in sidebar header (`assets/brains-mark-light-bg.png`)
- **Footer:** BRAINS Incubator origin credit, rendered via Streamlit's `st.caption()`
- **No italics in body text** (carries through from BRAINS brand rules)
- **No AI-generated imagery** (carries through)
- **Identity-first language** in all UI strings (`autistic candidate`, not `person with autism`)

The CSS injection in `style.py` is a single function `inject_brand_css()` called once at app start. It writes `<style>` tags via `st.markdown(unsafe_allow_html=True)`.

## 6. Data layer

### 6.1 Public API

`scripts/dashboard/data.py` wraps each query function from `scripts.tracker.query`:

```python
import streamlit as st
from scripts.tracker import query
from scripts.tracker.profile import read_profile, write_profile

@st.cache_data(ttl=60)
def cached_list_applications(company=None, since=None, status=None):
    return query.list_applications(company=company, since=since, status=status)

@st.cache_data(ttl=60)
def cached_weekly_summary(now=None):
    return query.weekly_summary(now=now)

@st.cache_data(ttl=60)
def cached_efficacy_by_template():
    return query.efficacy_by_template()

@st.cache_data(ttl=60)
def cached_find_duplicates(company, role_title, within_days=60):
    return query.find_duplicates(company, role_title, within_days=within_days)

# Same pattern for any other query function needed by tabs
```

Tabs import from `data.py`, never directly from `scripts.tracker.query`. Manual refresh buttons call `cached_list_applications.clear()` etc. to invalidate.

Profile reads/writes go directly through `scripts.tracker.profile` (not cached — focus areas and healthy rate are rarely-changed values; freshness matters more than cache hit rate).

### 6.2 Cross-tab navigation

`st.session_state` carries deep-link parameters between tabs. Example: clicking a LinkColumn cell in Applications that says "view resume" sets `st.session_state["jump_to_resume_id"] = 42` and switches to the Resumes tab, which reads the session state on render and pre-filters its table.

## 7. Launch mechanism

### 7.1 CLI entry point

`pyproject.toml` adds:

```toml
[project.scripts]
brains-resume-dashboard = "scripts.dashboard.launch:main"
```

After `pip install -e .` (or any reinstall against the v1.3.0 codebase), the user has a clean terminal command:

```text
brains-resume-dashboard
```

This invokes `scripts/dashboard/launch.py:main()`, which uses `subprocess` to call:

```text
streamlit run scripts/dashboard/app.py --server.headless true --server.port 8501
```

The launcher resolves the absolute path to `app.py` regardless of where the user invokes it from. It opens the user's default browser to `http://localhost:8501` automatically (Streamlit does this by default; `--server.headless true` disables it if the user prefers manual). The launcher exits when the Streamlit process exits.

### 7.2 Slash command

`commands/brains-dashboard.md`:

```yaml
---
description: Print the command to launch the BRAINS Resume dashboard in a browser
argument-hint: (no arguments)
---
```

Body: prints the launch command and a one-line "open http://localhost:8501" instruction. Does NOT spawn the subprocess from Claude Code (long-running processes are awkward for Claude Code to own; the user keeps terminal control).

## 8. Testing

Three-layer strategy.

### 8.1 Pure prep functions (TDD, fully covered)

`scripts/dashboard/prep/*.py` modules contain pure functions: given query results in, return chart-ready data structures out. No Streamlit imports, no I/O, no DB access. Fully unit-testable with fixtures.

Expected tests:

- `test_funnel.py` — funnel-data computation from `ApplicationRow` lists
- `test_sparkline.py` — rolling-30-day AI-signal trend, 8-week applications-per-week, callback-rate trend
- `test_trends.py` — weekly aggregation, rolling averages
- `test_idle_states.py` — detection logic for the three callout types

Expected: ~20 tests.

### 8.2 Cached wrappers (light)

`tests/dashboard/test_data.py` confirms each wrapper:

- Delegates to the underlying `scripts.tracker.query` function
- Returns the same shape
- The `@st.cache_data` decorator is applied (verified via attribute check, not by actually caching across calls)

Expected: ~5 tests.

### 8.3 Streamlit integration

Two tests:

- `test_app_import.py` — `from scripts.dashboard import app` succeeds without exceptions. Catches import-cycle errors and missing-module errors.
- `test_app_overview_render.py` — uses `streamlit.testing.v1.AppTest` to load the app, click into the Overview tab, and assert specific widgets render. Streamlit's testing harness has matured enough for one happy-path interaction test.

Expected: 2 tests.

### 8.4 Total

Expected new tests: ~27. Suite to ~286 (259 baseline + 27 new).

## 9. Privacy and brand

### 9.1 Privacy

Six guarantees unchanged. New surface area:

- **Dashboard runs entirely on localhost.** Default bind `127.0.0.1:8501`, no external network listener
- **No telemetry.** Streamlit's default usage statistics setting `[browser] gatherUsageStats = false` is set in `.streamlit/config.toml`
- **No persistent dashboard-specific state files** beyond what the tracker already writes
- **Profile.json sidebar edits** go through the same `write_profile()` path the CLI uses
- **Streamlit session state** is in-process, cleared when the user closes the browser tab or kills the dashboard process

### 9.2 Brand-on-output rule extension

| New artifact | Branded? |
|---|---|
| Dashboard UI itself | BRAINS Incubator branded — Gold Deep accents, Atkinson Hyperlegible, mark in sidebar |
| Charts and tables rendered in the dashboard | Branded (Gold Deep highlights, identity-first language) |
| (No exported-to-disk dashboard artifacts in v1.3.0) | n/a |

`references/brand-application.md` Section 1 split-rule table gains one row covering the dashboard UI.

## 10. Release plan

Single tag at end: **v1.3.0**.

- All 259 existing tests stay green
- ~27 new tests
- CHANGELOG v1.3.0 entry under "Added" + "Changed" headings
- README updated with "Launching the dashboard" section
- `references/brand-application.md` extended
- `docs/claude-project-setup.md` notes the dashboard is Claude-Code-only
- Claude Project bundle rebuilt (no new content shipped in the bundle — dashboard scripts don't fit the bundle)
- pyproject.toml + SKILL.md frontmatter bumped to 1.3.0
- `v1.3.0` git tag

## 11. Implementation phasing

Approximately 22 tasks across 5 phases. Plan document (separate, produced via `writing-plans`) will define exact task boundaries and TDD steps.

**Phase 1 — Foundation (Tasks 1-4):**

- pyproject deps + project-scripts entry
- Dashboard package skeleton (`__init__.py`, `launch.py`, `app.py` stub)
- `.streamlit/config.toml` dark-theme baseline
- `/brains-dashboard` slash command

**Phase 2 — Data + style (Tasks 5-7):**

- `data.py` cached wrappers + tests
- `prep/` modules with TDD (funnel, sparkline, trends, idle_states)
- `style.py` CSS injection with BRAINS Incubator branding (consults `brains-brand` skill at impl time)

**Phase 3 — Tabs (Tasks 8-14):**

- Overview tab (highest-complexity; tiles + sparklines + funnel + idle-states + twin panels)
- Resumes tab
- Cover-letters tab
- JDs tab
- Applications tab
- Analytics tab
- Pacing tab

**Phase 4 — Sidebar + smoke test (Tasks 15-16):**

- Sidebar (focus areas / healthy rate / refresh / version footer)
- `AppTest` smoke test for Overview render

**Phase 5 — Release polish (Tasks 17-22):**

- SKILL.md updates (router unchanged; slash-command count 15 → 16; tooling-notes)
- README "Launching the dashboard" section
- `references/brand-application.md` row
- `docs/claude-project-setup.md` note
- CHANGELOG v1.3.0 entry + Claude Project bundle rebuild
- Version bump to 1.3.0 + `v1.3.0` tag

---

**Points worth a second look during spec review:**

- **Streamlit dependency size** — adding `streamlit` and `plotly` to required deps adds ~100MB to a fresh install. If you'd rather keep the core skill lighter, we could move them to an optional `[project.optional-dependencies]` group `dashboard = ["streamlit", "plotly"]` so users install via `pip install -e ".[dashboard]"`. Tradeoff: slightly more friction for the install step in exchange for a leaner core install. Default in this spec is **required** because the dashboard is core v1.3.0 functionality, but it's a one-line spec change to flip.
- **AppTest stability** — `streamlit.testing.v1.AppTest` is relatively new and has had API churn across Streamlit versions. Pinning to `streamlit>=1.30.0` is safe, but the AppTest interaction test may be the most fragile test in the suite. If it proves flaky, we can downgrade to just the import smoke test and rely on the prep-function TDD coverage for confidence.
- **`pacing_notes` schema addition** — Section 4.7 adds a new `pacing_notes` field to `profile.json`. This is a schema change requiring nothing more than adding the field to the `Profile` dataclass. The implementation plan will need a small task for this. Worth flagging here so it isn't missed.
