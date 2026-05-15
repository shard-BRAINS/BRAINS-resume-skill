# BRAINS Resume Skill v1.4.0 — Dashboard workflows design

**Date:** 2026-05-15
**Author:** BRAINS Incubator
**Status:** Approved — ready for plan writing
**Predecessor:** v1.3.0 (Streamlit dashboard shipped 2026-05-15)

---

## 1. Goal

Expose every BRAINS Resume slash command through the v1.3.0 Streamlit dashboard's UI, without taking on a paid LLM API dependency. The dashboard becomes a mixed surface: it runs the existing Python validators natively (no LLM, no cost) and hands the LLM-heavy workflows off to Claude Code via clipboard.

## 2. Scope summary

In scope:

1. New `scripts/dashboard/workflows/` package — one module per slash command (15 modules; `/brains-dashboard` is self-referential and excluded).
2. New `scripts/dashboard/handoff.py` — clipboard-based handoff helper.
3. New `scripts/dashboard/file_input.py` — three-way file picker component (dropdown / path / uploader).
4. New 8th tab `Workflows` with all 15 commands as cards, grouped into three sections.
5. Inline contextual action buttons in the existing Resumes, Cover Letters, JDs, and Applications tabs.
6. In-dashboard execution of validator-backed commands (`/brains-deai`, `/brains-jd-analyze`, `/brains-track` full CRUD, `/brains-consolidate`, `/brains-check`, `/brains-review` partial preview).
7. Clipboard handoff for pure-LLM commands (`/brains-create`, `/brains-edit`, `/brains-tailor`, `/brains-cover-letter`, `/brains-disclosure`, `/brains-linkedin`, `/brains-linkedin-improve`, `/brains-career-change`, `/brains-precheck`).
8. Optional handoff audit log at `~/.brains-resume/handoffs/<timestamp>-<cmd>.txt` (Profile toggle, default on).
9. `pyperclip>=1.8.0` dependency added to `pyproject.toml`.
10. Release polish: SKILL.md, README, brand-application, CHANGELOG, claude-project-setup, bundle rebuild, version bump 1.3.0→1.4.0, v1.4.0 tag.

Out of scope:

- Any direct Anthropic API integration in the dashboard.
- Multi-turn LLM conversations rendered in Streamlit (those stay in Claude Code).
- File-watcher / hot-reload of new resume files.
- Multi-user / network / authentication surfaces (the dashboard remains localhost-only and single-user).
- iOS/Android mobile rendering tuning (desktop-first; ND-accessible already from v1.3.0).

## 3. Architecture

### 3.1 New package layout

```
scripts/dashboard/
  app.py                    # unchanged structure; adds Workflows tab + button wiring
  data.py                   # unchanged
  launch.py                 # unchanged
  sidebar.py                # add: handoff-log toggle, recent-handoffs viewer
  style.py                  # unchanged
  handoff.py                # NEW — clipboard helper + handoff logging
  file_input.py             # NEW — three-way file picker component
  prep/                     # unchanged (4 prep modules)
  tabs/
    overview.py             # unchanged
    resumes.py              # MODIFIED — adds inline action buttons
    cover_letters.py        # MODIFIED — adds inline action buttons
    jds.py                  # MODIFIED — adds inline action buttons
    applications.py         # MODIFIED — adds inline action buttons
    analytics.py            # unchanged
    pacing.py               # unchanged
    workflows.py            # NEW — 8th tab, grid of cards
  workflows/                # NEW PACKAGE — one module per slash command
    __init__.py
    review.py
    edit.py
    tailor.py
    cover_letter.py
    create.py
    deai.py
    check.py
    jd_analyze.py
    precheck.py
    track.py
    career_change.py
    linkedin.py
    linkedin_improve.py
    consolidate.py
    disclosure.py
```

### 3.2 Module contract — `workflows/<command>.py`

Each workflow module exposes one public function:

```python
def render(file_path: Optional[Path] = None) -> None:
    """Render the workflow's form (and validator results, if applicable) into the current Streamlit container.

    Args:
        file_path: Optional pre-filled file path when invoked from a contextual inline button
                   (e.g. Resumes tab "Review" button passes the row's file path).
                   When invoked from the Workflows tab, this is None and the form's file picker is empty.
    """
```

Behavioural rules:

- The module renders directly into whatever Streamlit container is active (it does NOT create its own tab).
- If the command is validator-backed, `render()` runs the validator(s) synchronously when the user clicks "Scan" / "Analyze" and shows the result inline. A secondary "Send to Claude Code for full coaching" button is shown below the result.
- If the command is pure-LLM, `render()` only collects inputs and exposes a single "Copy handoff" button.
- All buttons funnel through `handoff.handoff(cmd, *args, note=...)` for the clipboard side-effect.

### 3.3 Handoff infrastructure (`handoff.py`)

```python
import datetime
import os
from pathlib import Path
from typing import Optional

import pyperclip
import streamlit as st

HANDOFF_LOG_DIR = Path.home() / ".brains-resume" / "handoffs"


def build_command(cmd: str, *args: str) -> str:
    """Builds `/brains-<cmd> arg1 arg2 ...`. Whitespace-quotes paths with spaces."""
    quoted = [f'"{a}"' if " " in a else a for a in args if a]
    return f"/brains-{cmd} {' '.join(quoted)}".strip()


def copy_to_clipboard(text: str) -> bool:
    """Returns True on success, False if pyperclip raised (e.g. no clipboard available)."""
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def log_handoff(cmd: str, command_str: str, note: str = "") -> Path:
    """Appends a record to the handoff log directory. Returns the file path."""
    HANDOFF_LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = HANDOFF_LOG_DIR / f"{ts}-{cmd}.txt"
    path.write_text(f"{command_str}\n\n{note}" if note else command_str, encoding="utf-8")
    return path


def handoff(cmd: str, *args: str, note: str = "", log: bool = True) -> None:
    """One-call helper: build → copy → log → toast."""
    command_str = build_command(cmd, *args)
    ok = copy_to_clipboard(command_str)
    if log:
        log_handoff(cmd, command_str, note=note)
    if ok:
        st.toast(f"Copied: {command_str}", icon="✓")
    else:
        st.warning("Clipboard unavailable — copy this command manually:")
        st.code(command_str, language="text")
    if note:
        st.caption(note)
```

### 3.4 File-input component (`file_input.py`)

```python
def pick_file(kind: Literal["resume", "cover_letter", "jd"], key: str) -> Optional[Path]:
    """Renders a 3-way file picker. Returns first resolved path or None.

    1. Dropdown of tracker-known files for this kind (queries data.py cached wrappers).
    2. Text input for arbitrary absolute path.
    3. st.file_uploader; uploaded files are copied to ~/.brains-resume/uploads/<kind>/.

    Picker semantics:
    - If the dropdown has a selection AND it's not the placeholder, return that path.
    - Else if the text input has a non-empty value AND Path(value).exists(), return that.
    - Else if a file was uploaded, save it and return the saved path.
    - Else return None.

    `key` is the Streamlit widget key — caller must pass a unique string per usage site.
    """
```

### 3.5 Inline-button pattern in existing tabs

Each existing-tab row gains action buttons via a per-row `st.button` group below the table, exposed when the user selects a row from a row-index `st.selectbox`. (Streamlit's `st.dataframe` does not natively support per-row action buttons; selectbox + button row is the idiomatic pattern.)

Pattern:

```python
# Resumes tab — at the bottom of the existing table
st.markdown("---")
selected_row = st.selectbox("Select resume for action", df.index, format_func=lambda i: df.loc[i, "name"])
if selected_row is not None:
    file_path = Path(df.loc[selected_row, "path"])
    cols = st.columns(5)
    if cols[0].button("Review", key=f"review_{selected_row}"):
        workflows.review.render(file_path=file_path)
    if cols[1].button("Edit", key=f"edit_{selected_row}"):
        workflows.edit.render(file_path=file_path)
    # ... etc
```

The workflow module's `render()` then expands its full form below, with the file path pre-filled.

### 3.6 Workflows tab structure

```python
# tabs/workflows.py
def render():
    inject_brand_css()
    st.header("Workflows")
    st.caption("Run any BRAINS workflow from here. Validator-backed ones execute in-dashboard; LLM-heavy ones copy the slash command to your clipboard for Claude Code.")

    st.subheader("Resume workflows")
    cols = st.columns(3)
    _render_card(cols[0], "review",      "🔍", "Review",      "Audit a resume for ND-bias, ATS, and integrity")
    _render_card(cols[1], "edit",        "✏️", "Edit",        "Apply review fixes to a resume")
    _render_card(cols[2], "tailor",      "🎯", "Tailor",      "Customise a resume to a specific JD")
    cols = st.columns(3)
    _render_card(cols[0], "cover_letter","💌", "Cover letter","Generate a cover letter for a JD")
    _render_card(cols[1], "create",      "🆕", "Create",      "Build a resume from scratch")
    _render_card(cols[2], "deai",        "🧹", "De-AI",       "Scan + suggest de-AI rewrites")
    cols = st.columns(3)
    _render_card(cols[0], "check",       "✅", "Final check", "ATS + integrity + bias + AI-signal composite")

    st.subheader("JD & application workflows")
    cols = st.columns(3)
    _render_card(cols[0], "jd_analyze",   "📋", "JD analyze",   "Red flags, masking cost, role-fit")
    _render_card(cols[1], "precheck",     "🛡️", "Pre-application","Six-question coaching pass")
    _render_card(cols[2], "track",        "📈", "Track",         "Manage application outcomes")
    cols = st.columns(3)
    _render_card(cols[0], "career_change","🔄", "Career change", "Translate experience for a pivot")

    st.subheader("LinkedIn & coaching workflows")
    cols = st.columns(3)
    _render_card(cols[0], "linkedin",         "📥", "LinkedIn ingest", "Import a LinkedIn export ZIP")
    _render_card(cols[1], "linkedin_improve", "💼", "LinkedIn improve","Rewrite Headline / About / etc.")
    _render_card(cols[2], "consolidate",      "🧩", "Consolidate",     "Resolve resume ↔ LinkedIn inconsistencies")
    cols = st.columns(3)
    _render_card(cols[0], "disclosure",       "💭", "Disclosure",      "Walk through disclosure decision")
```

`_render_card` renders a styled card with an `st.expander` that holds the workflow's form. When the expander is open, it calls `workflows.<cmd>.render(file_path=None)`.

### 3.7 Sidebar additions

Sidebar gains, below the existing profile editor:

- **Handoff log** section — checkbox "Log handoffs to disk" (writes to `~/.brains-resume/handoffs/`, default checked) and an `st.expander` "Recent handoffs" showing the last 10 handoff filenames as a list with click-to-view.

Profile schema gains `log_handoffs: bool = True` field.

## 4. Validator-backed workflow surfaces

### 4.1 `/brains-deai` (in-dashboard)

Form:
- File picker (resume / cover_letter / linkedin export DOCX)

Action: Scan → calls `scripts.validators.ai_signal_check.scan(file_path)` → renders:
- Overall score (0–100, lower = better) with colored badge
- Findings table: code, severity, line, snippet, fix-suggestion
- Per-finding breakdown via `st.expander`

Secondary action: "Get rewrite suggestions from Claude Code" → `handoff("deai", file_path)`.

### 4.2 `/brains-jd-analyze` (in-dashboard)

Form:
- Text area for JD paste OR file path picker

Action: Analyze → calls `scripts.validators.jd_analyzer.analyze(text)` → renders:
- Red flags table
- Masking-cost score
- Role-fit score (vs profile.focus_areas)
- Duplicate-application check (queries tracker DB)

Secondary action: "Full coaching report in Claude Code" → `handoff("jd-analyze", path_or_temp)`.

### 4.3 `/brains-track` (fully in-dashboard, no LLM)

Already partially in the Applications tab from v1.3.0. v1.4.0 adds:
- Add-application form with the six pre-application coaching questions inline
- Inline outcome-logging buttons on each application row (acknowledged, callback, interview, offer, rejection, ghosted, withdrew)
- No clipboard handoff — `/brains-track` is fully self-contained

### 4.4 `/brains-consolidate` (in-dashboard)

Form:
- Resume picker
- LinkedIn export picker (DOCX or ZIP)

Action: Diff → calls `scripts.validators.consolidation_check.diff(resume_path, linkedin_path)` → renders inconsistencies table grouped by category (employment dates, titles, skills, locations).

Secondary action: "LLM-coached resolution in Claude Code" → `handoff("consolidate", resume_path, linkedin_path)`.

### 4.5 `/brains-check` (composite, in-dashboard)

Form:
- Resume picker

Action: Run all → calls all four: `ats_check`, `integrity_check`, `bias_scan`, `ai_signal_check`. Renders composite report:
- ATS-safety: pass/fail by check, with offending content
- Integrity: encoding/font/table issues
- Bias-scan: hits from the ten-pattern catalog with line numbers
- AI-signal: score + top 3 findings

Secondary action: "Final coaching pass in Claude Code" → `handoff("check", file_path)`.

### 4.6 `/brains-review` (partial preview)

Validator preview only: runs `bias_scan` and renders a shallow preview table. Primary action is the handoff to Claude Code for the full multi-pass review (which includes LLM-driven nuance the validators don't catch).

Form:
- Resume picker

Action: Preview → shows bias-scan preview
Primary handoff: "Full review in Claude Code" → `handoff("review", file_path)`.

## 5. Pure-LLM handoff surfaces

Nine commands have form-only pages — no in-dashboard analysis. Each `workflows/<cmd>.py` collects the inputs the slash command needs and triggers `handoff()`.

| Command | Inputs collected by the form | Args passed to `handoff()` |
|---|---|---|
| `/brains-edit` | Resume path | `(file_path,)` |
| `/brains-tailor` | Resume path, JD URL or file | `(resume_path, jd_arg)` |
| `/brains-cover-letter` | Tailored resume path, JD URL or file | `(resume_path, jd_arg)` |
| `/brains-create` | None (note about interview style) | `()` |
| `/brains-disclosure` | None | `()` |
| `/brains-linkedin` | Path to LinkedIn ZIP | `(zip_path,)` |
| `/brains-linkedin-improve` | LinkedIn DOCX path | `(file_path,)` |
| `/brains-career-change` | Resume path | `(file_path,)` |
| `/brains-precheck` | Company, role, JD path/URL, intent notes | `(company, role, jd_arg)` — joined as a single quoted string |

Note for `precheck`: this is hybrid in practice (tracker write happens in dashboard via `scripts.tracker.add.add_application` if user confirms; LLM coaching still in Claude Code). The form has a "Register in tracker only" button and a "Register + open coaching in Claude Code" button.

## 6. Inline contextual buttons

| Tab | Row context | Buttons added |
|---|---|---|
| Resumes | a tracked resume file | Review · Edit · Tailor · De-AI · Final check |
| Cover letters | a tracked cover-letter file | Edit · De-AI |
| JDs | a tracked JD entry | Analyze · Tailor-resume-to-this-JD |
| Applications | an application row (already registered) | Track update (log new outcome) |

Each button calls `workflows.<cmd>.render(file_path=...)` which expands its form inline below the table.

## 7. File-input UX

Implemented in `scripts/dashboard/file_input.py` per §3.4. Behaviour:

- For `kind="resume"` and `kind="cover_letter"`, the dropdown queries `cached_list_applications()` and filters for distinct DOCX paths.
- For `kind="jd"`, the dropdown queries the JDs table.
- Upload destination: `~/.brains-resume/uploads/<kind>/<original_filename>` (overwrites if exists; user is shown a warning toast).
- PDF accepted for handoff-only flows; DOCX required for in-dashboard validator runs. The picker shows a yellow warning when a PDF is selected and a validator-backed action is enabled.

## 8. Profile schema additions

`scripts/tracker/models.py` `Profile` dataclass gains:

```python
log_handoffs: bool = True
```

`scripts/tracker/profile.py` `read_profile` / `write_profile` handle the new field with backward-compat default `True` when absent.

## 9. Dependencies

`pyproject.toml` `[project] dependencies` gains:

```toml
"pyperclip>=1.8.0",
```

No other new dependencies. (Streamlit 1.30+, Plotly 5.18+ already added in v1.3.0.)

## 10. Error handling

- **Clipboard failure** (`pyperclip` raises) → `handoff()` falls back to `st.code` block + warning. No crash.
- **PDF passed to validator** → workflow's form shows an `st.error` "DOCX required for in-dashboard analysis. Use the Claude Code handoff button instead, which can read PDFs."
- **Missing file** (path provided but `Path(p).exists()` is False) → `st.error` "File not found at <path>". Form does not run.
- **Profile schema upgrade** — old profile.json files without `log_handoffs` field are read with the default; first write upgrades the file. No migration script needed.
- **Tracker DB empty** — dropdown shows "(no tracked files yet)" placeholder, doesn't crash.

## 11. Testing strategy

Three test categories:

**(A) Pure-Python unit tests (TDD)**
- `tests/dashboard/test_handoff.py` — `build_command`, `copy_to_clipboard` (mocked), `log_handoff`, `handoff` toast paths. ~10 tests.
- `tests/dashboard/test_file_input.py` — path resolution priority (dropdown > path > upload), DOCX/PDF gating logic. ~8 tests.
- `tests/dashboard/test_workflows/*.py` — input-validation helpers per workflow (form-args → slash-command string). ~12 tests across 15 workflow modules.

**(B) Streamlit AppTest happy-paths**
- `tests/dashboard/test_app_workflows_tab.py` — Workflows tab renders, all 15 cards present, no exception.
- `tests/dashboard/test_inline_buttons.py` — Resumes/Cover-Letters/JDs/Applications tabs render with inline buttons, no exception.

Existing 297 tests remain green throughout.

Target: 297 → ~335 tests.

**(C) Manual verification (documented in plan, not automated)**
- Clipboard integration (`pyperclip.copy` actually writes to OS clipboard on Windows)
- Toast appearance and timing
- File-uploader saves to expected directory

## 12. Phasing

**Phase 1 — Infrastructure (Tasks 1-4)**
1. `pyperclip` dependency + `handoff.py` skeleton (TDD)
2. `handoff.py` full implementation + tests
3. `file_input.py` (TDD)
4. Profile schema: `log_handoffs` field

**Phase 2 — Workflows tab + pure-LLM cards (Tasks 5-10)**
5. `workflows/__init__.py` + 9 pure-LLM card modules (create, edit, tailor, cover_letter, disclosure, linkedin, linkedin_improve, career_change, precheck) — each is a thin form-only module
6. `tabs/workflows.py` 8th tab skeleton
7. Wire 8th tab into `app.py` (st.tabs goes from 7 to 8)
8. Card-grid rendering helper `_render_card`
9. Sidebar handoff-log toggle + recent-handoffs viewer
10. AppTest happy-path for Workflows tab

**Phase 3 — Validator-backed workflows (Tasks 11-16)**
11. `workflows/deai.py` (uses `ai_signal_check`)
12. `workflows/jd_analyze.py` (uses `jd_analyzer`)
13. `workflows/track.py` (extends Applications tab CRUD)
14. `workflows/consolidate.py` (uses `consolidation_check`)
15. `workflows/check.py` (composite of 4 validators)
16. `workflows/review.py` (uses `bias_scan` for preview)

**Phase 4 — Inline contextual buttons (Tasks 17-20)**
17. Resumes tab inline buttons
18. Cover Letters tab inline buttons
19. JDs tab inline buttons
20. Applications tab inline buttons

**Phase 5 — Release polish (Tasks 21-24)**
21. SKILL.md, README, brand-application, claude-project-setup docs
22. CHANGELOG v1.4.0 entry + bundle rebuild
23. Version bump 1.3.0 → 1.4.0
24. v1.4.0 annotated tag

Total: ~24 tasks. Comparable to Plan 5b (23 tasks).

## 13. Brand & accessibility

- BRAINS Incubator brand preserved (Incubator Blue accents, Gold Deep delta callouts, Atkinson Hyperlegible).
- Footer phrase verbatim: "BRAINS Incubator · Built by neurodivergent minds, for neurodivergent people."
- All workflow cards use identity-first language consistent with v1.3.0 dashboard text.
- New surfaces honor existing dark-theme baseline.
- Toast and error messages use the existing colour tokens from `style.py`.

## 14. Open risks

- **Streamlit re-render after handoff** — Streamlit's reactive model re-runs the script on each click. The `handoff()` toast must fire from the click handler, not from a session-state effect. Plan tasks specify the toast goes inside the `if st.button(...)` block.
- **pyperclip on headless Windows** — should work in a desktop Streamlit run. If the user later runs the dashboard in WSL or via SSH, clipboard fails gracefully via the `st.code` fallback.
- **15 form modules** — risk of copy-paste drift. The `workflows/` package will share a common `_handoff_card(cmd, inputs, args_builder)` helper to keep each module ≤30 lines.

## 15. Plan completion checklist

When v1.4.0 is shippable, the following must all hold:

- 24 tasks complete, all step boxes checked.
- `python -m pytest -q` reports ~335 tests green (297 baseline + ~38 new).
- `git tag --list` includes `v1.4.0`.
- `dist/brains-resume-claude-project.zip` rebuilt (dashboard scripts excluded as in v1.3.0).
- No `Co-Authored-By` footers in any commit.
- No third-party org/project proper-name references in code, docs, or commit messages.
- `SKILL.md` frontmatter says `version: 1.4.0`.
- `pyproject.toml` says `version = "1.4.0"` and includes `pyperclip>=1.8.0`.
- All 15 workflow modules import cleanly.
- AppTest happy-paths for Workflows tab + 4 modified tabs pass without exception.
- Manual smoke verified: clicking a workflow button copies the correct slash command to the clipboard, with file paths whitespace-quoted.
