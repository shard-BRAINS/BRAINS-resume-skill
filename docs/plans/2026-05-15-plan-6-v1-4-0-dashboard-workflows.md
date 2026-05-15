# Plan 6 — BRAINS Resume Skill v1.4.0 (Dashboard workflows) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose every BRAINS Resume slash command through the v1.3.0 Streamlit dashboard UI by running deterministic validators natively and handing LLM-heavy workflows off to Claude Code via clipboard.

**Architecture:** New `scripts/dashboard/workflows/` package (one module per slash command), new `handoff.py` (clipboard + log helper using `pyperclip`), new `file_input.py` (three-way file picker). An 8th `Workflows` tab houses cards for all 15 slash commands. The existing 4 row-bearing tabs (Resumes, Cover Letters, JDs, Applications) gain inline action buttons that pre-fill workflow forms. Validator-backed commands run analyzers in-dashboard; pure-LLM commands collect inputs and copy the slash command to clipboard for Claude Code.

**Tech Stack:** Streamlit 1.30+, Plotly 5.18+ (already from v1.3.0), Python 3.10+, SQLite tracker (~/.brains-resume/tracker.db), existing validators (`scripts/validators/{ai_signal_check,ats_check,bias_scan,consolidation_check,integrity_check,jd_analyzer}.py`), existing tracker (`scripts/tracker/{add,query,profile}.py`). New dependency: `pyperclip>=1.8.0`.

**Plan conventions:**
- Conventional commits (`feat:` / `fix:` / `test:` / `docs:` / `build:` / `chore:` / `refactor:`)
- **NEVER** include `Co-Authored-By` footers — BRAINS-only attribution
- TDD discipline for pure-Python modules: failing test → confirm failure → implement → confirm pass → commit
- Streamlit-coupled tab modules (workflows/*.py with Streamlit UI calls) are not unit-tested; covered by AppTest happy-paths only
- Stage and commit after each task
- Working directory: `c:\Brains_Resume_Skill\`
- Baseline: HEAD `9b683d8` (spec commit), 297 tests green at v1.3.0
- Target: ~335 tests green at v1.4.0 tag
- Execution: continue on `main` branch (consistent with v0.1.x → v1.3.0)

---

## Phase 1 — Infrastructure (Tasks 1-4)

---

## Task 1 — Add pyperclip dependency + handoff.py module skeleton

**Files:**
- Modify: `pyproject.toml`
- Create: `scripts/dashboard/handoff.py`
- Create: `tests/dashboard/test_handoff.py`

### Steps

- [ ] **Step 1: Add pyperclip to dependencies**

In `pyproject.toml`, find the `dependencies = [` list (which already includes `streamlit>=1.30.0` and `plotly>=5.18.0` from v1.3.0). Add `pyperclip>=1.8.0` to the list. Final entries:

```toml
dependencies = [
    "python-docx>=0.8.11",
    "pypdf>=3.0.0",
    "streamlit>=1.30.0",
    "plotly>=5.18.0",
    "pyperclip>=1.8.0",
]
```

(Preserve the existing leading entries — only add `pyperclip>=1.8.0` to the end.)

- [ ] **Step 2: Install the dependency**

```powershell
pip install -e .
```

Expected: `pyperclip` resolves and installs (or is already present). No errors.

- [ ] **Step 3: Write the failing test for `build_command`**

Create `tests/dashboard/test_handoff.py`:

```python
"""Tests for scripts.dashboard.handoff — clipboard + log helper."""
from pathlib import Path

import pytest


def test_build_command_no_args():
    from scripts.dashboard.handoff import build_command
    assert build_command("review") == "/brains-review"


def test_build_command_single_arg():
    from scripts.dashboard.handoff import build_command
    assert build_command("review", "C:/path/resume.docx") == "/brains-review C:/path/resume.docx"


def test_build_command_path_with_space_is_quoted():
    from scripts.dashboard.handoff import build_command
    assert build_command("tailor", "C:/Users/me/My Resume.docx", "https://jd.url") == '/brains-tailor "C:/Users/me/My Resume.docx" https://jd.url'


def test_build_command_filters_empty_args():
    from scripts.dashboard.handoff import build_command
    assert build_command("review", "", "C:/r.docx", "") == "/brains-review C:/r.docx"


def test_build_command_multiple_args():
    from scripts.dashboard.handoff import build_command
    assert build_command("consolidate", "C:/r.docx", "C:/li.zip") == "/brains-consolidate C:/r.docx C:/li.zip"
```

- [ ] **Step 4: Verify the tests fail**

```powershell
python -m pytest tests/dashboard/test_handoff.py -v
```

Expected: 5 failures with `ImportError: cannot import name 'build_command' from 'scripts.dashboard.handoff'` (module does not exist yet).

- [ ] **Step 5: Create the handoff.py skeleton with build_command**

Create `scripts/dashboard/handoff.py`:

```python
"""Clipboard + handoff log helper for dashboard workflow buttons.

Builds a slash-command string from a command name + args, copies to OS clipboard,
optionally logs to disk, and renders a Streamlit toast. Pure-Python pieces are
unit-tested; the Streamlit toast rendering is covered by AppTest only.
"""
from __future__ import annotations


def build_command(cmd: str, *args: str) -> str:
    """Build `/brains-<cmd> arg1 arg2 ...`. Whitespace-quotes args containing spaces."""
    quoted = [f'"{a}"' if " " in a else a for a in args if a]
    return f"/brains-{cmd} {' '.join(quoted)}".strip()
```

- [ ] **Step 6: Verify the tests pass**

```powershell
python -m pytest tests/dashboard/test_handoff.py -v
```

Expected: 5 tests pass.

- [ ] **Step 7: Run the full suite to confirm no regressions**

```powershell
python -m pytest -q
```

Expected: 302 tests pass (297 baseline + 5 new).

- [ ] **Step 8: Commit**

```powershell
git add pyproject.toml scripts/dashboard/handoff.py tests/dashboard/test_handoff.py
git commit -m "build: add pyperclip dependency and handoff.build_command helper"
```

---

## Task 2 — handoff.py full implementation (clipboard + log + toast)

**Files:**
- Modify: `scripts/dashboard/handoff.py`
- Modify: `tests/dashboard/test_handoff.py`

### Steps

- [ ] **Step 1: Write failing tests for copy_to_clipboard and log_handoff**

Append to `tests/dashboard/test_handoff.py`:

```python
def test_copy_to_clipboard_success(monkeypatch):
    from scripts.dashboard import handoff
    captured = {}
    monkeypatch.setattr(handoff.pyperclip, "copy", lambda text: captured.setdefault("text", text))
    assert handoff.copy_to_clipboard("hello") is True
    assert captured["text"] == "hello"


def test_copy_to_clipboard_failure_returns_false(monkeypatch):
    from scripts.dashboard import handoff

    def raise_(*_args, **_kwargs):
        raise RuntimeError("no clipboard")

    monkeypatch.setattr(handoff.pyperclip, "copy", raise_)
    assert handoff.copy_to_clipboard("hello") is False


def test_log_handoff_writes_file(tmp_path, monkeypatch):
    from scripts.dashboard import handoff
    monkeypatch.setattr(handoff, "HANDOFF_LOG_DIR", tmp_path)
    result = handoff.log_handoff("review", "/brains-review C:/r.docx", note="audit")
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "/brains-review C:/r.docx" in content
    assert "audit" in content


def test_log_handoff_no_note(tmp_path, monkeypatch):
    from scripts.dashboard import handoff
    monkeypatch.setattr(handoff, "HANDOFF_LOG_DIR", tmp_path)
    result = handoff.log_handoff("deai", "/brains-deai")
    assert result.read_text(encoding="utf-8").strip() == "/brains-deai"


def test_log_handoff_creates_dir_if_missing(tmp_path, monkeypatch):
    from scripts.dashboard import handoff
    target = tmp_path / "nested" / "handoffs"
    monkeypatch.setattr(handoff, "HANDOFF_LOG_DIR", target)
    result = handoff.log_handoff("review", "/brains-review")
    assert target.exists()
    assert result.parent == target
```

- [ ] **Step 2: Verify the tests fail**

```powershell
python -m pytest tests/dashboard/test_handoff.py -v
```

Expected: 5 new failures with `AttributeError` (functions and `HANDOFF_LOG_DIR` not defined yet) or `ImportError`.

- [ ] **Step 3: Implement clipboard, log, and orchestrator**

Replace `scripts/dashboard/handoff.py` with the full implementation:

```python
"""Clipboard + handoff log helper for dashboard workflow buttons.

Builds a slash-command string from a command name + args, copies to OS clipboard,
optionally logs to disk, and renders a Streamlit toast. Pure-Python pieces are
unit-tested; the Streamlit toast rendering is covered by AppTest only.
"""
from __future__ import annotations

import datetime
from pathlib import Path

import pyperclip
import streamlit as st

HANDOFF_LOG_DIR = Path.home() / ".brains-resume" / "handoffs"


def build_command(cmd: str, *args: str) -> str:
    """Build `/brains-<cmd> arg1 arg2 ...`. Whitespace-quotes args containing spaces."""
    quoted = [f'"{a}"' if " " in a else a for a in args if a]
    return f"/brains-{cmd} {' '.join(quoted)}".strip()


def copy_to_clipboard(text: str) -> bool:
    """Return True on success, False if pyperclip raised (e.g. no clipboard available)."""
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def log_handoff(cmd: str, command_str: str, note: str = "") -> Path:
    """Append a record to the handoff log directory. Return the file path."""
    HANDOFF_LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = HANDOFF_LOG_DIR / f"{ts}-{cmd}.txt"
    body = f"{command_str}\n\n{note}" if note else command_str
    path.write_text(body, encoding="utf-8")
    return path


def handoff(cmd: str, *args: str, note: str = "", log: bool = True) -> None:
    """One-call helper: build → copy → log → toast.

    Renders a Streamlit toast on success, or a warning + st.code block on
    clipboard failure. Must be called inside a Streamlit context (e.g. inside
    an `if st.button(...):` block).
    """
    command_str = build_command(cmd, *args)
    ok = copy_to_clipboard(command_str)
    if log:
        try:
            log_handoff(cmd, command_str, note=note)
        except Exception:
            pass  # log failure is non-fatal
    if ok:
        st.toast(f"Copied: {command_str}", icon="✓")
    else:
        st.warning("Clipboard unavailable — copy this command manually:")
        st.code(command_str, language="text")
    if note:
        st.caption(note)
```

- [ ] **Step 4: Verify the tests pass**

```powershell
python -m pytest tests/dashboard/test_handoff.py -v
```

Expected: 10 tests pass (5 from Task 1 + 5 new).

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 307 tests pass (302 + 5).

- [ ] **Step 6: Commit**

```powershell
git add scripts/dashboard/handoff.py tests/dashboard/test_handoff.py
git commit -m "feat: add handoff clipboard + log + toast orchestrator"
```

---

## Task 3 — file_input.py three-way file picker

**Files:**
- Create: `scripts/dashboard/file_input.py`
- Create: `tests/dashboard/test_file_input.py`

### Steps

- [ ] **Step 1: Write failing tests for resolve_path priority**

Create `tests/dashboard/test_file_input.py`:

```python
"""Tests for scripts.dashboard.file_input — three-way file picker resolution."""
from pathlib import Path

import pytest


def test_resolve_path_dropdown_wins(tmp_path):
    from scripts.dashboard.file_input import resolve_path
    dropdown_pick = tmp_path / "from-dropdown.docx"
    dropdown_pick.write_bytes(b"")
    text_input = tmp_path / "from-text.docx"
    text_input.write_bytes(b"")
    result = resolve_path(dropdown_value=str(dropdown_pick), text_value=str(text_input), upload=None, upload_dir=tmp_path)
    assert result == dropdown_pick


def test_resolve_path_text_used_when_dropdown_placeholder(tmp_path):
    from scripts.dashboard.file_input import resolve_path
    text_input = tmp_path / "from-text.docx"
    text_input.write_bytes(b"")
    result = resolve_path(dropdown_value="(select a file...)", text_value=str(text_input), upload=None, upload_dir=tmp_path)
    assert result == text_input


def test_resolve_path_text_skipped_if_missing(tmp_path):
    from scripts.dashboard.file_input import resolve_path
    result = resolve_path(dropdown_value=None, text_value=str(tmp_path / "nope.docx"), upload=None, upload_dir=tmp_path)
    assert result is None


def test_resolve_path_upload_saved(tmp_path):
    from scripts.dashboard.file_input import resolve_path

    class FakeUpload:
        name = "upload.docx"
        def getbuffer(self):
            return b"upload-content"

    result = resolve_path(dropdown_value=None, text_value="", upload=FakeUpload(), upload_dir=tmp_path)
    assert result is not None
    assert result.name == "upload.docx"
    assert result.read_bytes() == b"upload-content"


def test_resolve_path_returns_none_when_all_empty(tmp_path):
    from scripts.dashboard.file_input import resolve_path
    result = resolve_path(dropdown_value=None, text_value="", upload=None, upload_dir=tmp_path)
    assert result is None


def test_resolve_path_dropdown_placeholder_string(tmp_path):
    from scripts.dashboard.file_input import resolve_path
    result = resolve_path(dropdown_value="(select a file...)", text_value="", upload=None, upload_dir=tmp_path)
    assert result is None


def test_is_docx_path():
    from scripts.dashboard.file_input import is_docx
    assert is_docx(Path("foo.docx")) is True
    assert is_docx(Path("foo.DOCX")) is True
    assert is_docx(Path("foo.pdf")) is False
    assert is_docx(Path("foo.txt")) is False


def test_is_pdf_path():
    from scripts.dashboard.file_input import is_pdf
    assert is_pdf(Path("foo.pdf")) is True
    assert is_pdf(Path("foo.PDF")) is True
    assert is_pdf(Path("foo.docx")) is False
```

- [ ] **Step 2: Verify the tests fail**

```powershell
python -m pytest tests/dashboard/test_file_input.py -v
```

Expected: 8 failures with `ImportError`.

- [ ] **Step 3: Create file_input.py**

Create `scripts/dashboard/file_input.py`:

```python
"""Three-way file picker for dashboard workflow forms.

Renders a dropdown of tracker-known files + a path text input + a file uploader.
Returns the first resolved path (dropdown > text > upload). Pure-Python `resolve_path`
is unit-tested; the Streamlit `pick_file` wrapper is covered by AppTest only.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional

import streamlit as st

UPLOAD_ROOT = Path.home() / ".brains-resume" / "uploads"
DROPDOWN_PLACEHOLDER = "(select a file...)"


def is_docx(path: Path) -> bool:
    return path.suffix.lower() == ".docx"


def is_pdf(path: Path) -> bool:
    return path.suffix.lower() == ".pdf"


def resolve_path(
    dropdown_value: Optional[str],
    text_value: str,
    upload: Optional[Any],
    upload_dir: Path,
) -> Optional[Path]:
    """Resolve the user's intended path from three sources, in priority order.

    1. Dropdown (a path string from the tracker DB), unless it's the placeholder.
    2. Text input, only if the file exists at the given path.
    3. Upload (a Streamlit UploadedFile-like object), saved to upload_dir.
    """
    if dropdown_value and dropdown_value != DROPDOWN_PLACEHOLDER:
        return Path(dropdown_value)

    if text_value:
        p = Path(text_value)
        if p.exists():
            return p

    if upload is not None:
        upload_dir.mkdir(parents=True, exist_ok=True)
        out = upload_dir / upload.name
        out.write_bytes(upload.getbuffer())
        return out

    return None


def _list_tracker_files(kind: Literal["resume", "cover_letter", "jd"]) -> list[str]:
    """Return distinct file paths from the tracker DB for the given kind.

    Lazy import of `scripts.dashboard.data` to avoid Streamlit import-cycle.
    """
    try:
        from scripts.dashboard import data
        if kind == "resume":
            rows = data.cached_list_resume_paths()
        elif kind == "cover_letter":
            rows = data.cached_list_cover_letter_paths()
        elif kind == "jd":
            rows = data.cached_list_jd_paths()
        else:
            rows = []
        return sorted({r for r in rows if r})
    except Exception:
        return []


def pick_file(kind: Literal["resume", "cover_letter", "jd"], key: str) -> Optional[Path]:
    """Render the three-way picker. Return the first resolved Path or None.

    The `key` arg must be unique per call site (Streamlit widget key).
    """
    options = [DROPDOWN_PLACEHOLDER] + _list_tracker_files(kind)
    dropdown_value = st.selectbox(f"Pick a known {kind}", options=options, key=f"{key}_dropdown")

    text_value = st.text_input(f"Or paste an absolute path", value="", key=f"{key}_text")

    upload = st.file_uploader(f"Or upload a file", type=["docx", "pdf"], key=f"{key}_upload")

    upload_dir = UPLOAD_ROOT / kind
    return resolve_path(dropdown_value, text_value, upload, upload_dir)
```

- [ ] **Step 4: Verify the tests pass**

```powershell
python -m pytest tests/dashboard/test_file_input.py -v
```

Expected: 8 tests pass.

- [ ] **Step 5: Add the helper data wrappers**

`file_input.py` references `data.cached_list_resume_paths()`, `data.cached_list_cover_letter_paths()`, `data.cached_list_jd_paths()` which don't yet exist. Add them to `scripts/dashboard/data.py`.

Read the existing `scripts/dashboard/data.py` and append (before the `clear_all_caches` function):

```python
@st.cache_data(ttl=60)
def cached_list_resume_paths() -> list[str]:
    """Distinct resume file paths known to the tracker DB."""
    from scripts.tracker import query
    apps = query.list_applications()
    return list({a.resume_path for a in apps if getattr(a, "resume_path", None)})


@st.cache_data(ttl=60)
def cached_list_cover_letter_paths() -> list[str]:
    """Distinct cover-letter file paths known to the tracker DB."""
    from scripts.tracker import query
    rows = query.list_cover_letters() if hasattr(query, "list_cover_letters") else []
    return list({r.path for r in rows if getattr(r, "path", None)})


@st.cache_data(ttl=60)
def cached_list_jd_paths() -> list[str]:
    """Distinct JD identifier strings (URLs or file paths) known to the tracker DB."""
    from scripts.tracker import query
    rows = query.list_jds() if hasattr(query, "list_jds") else []
    return list({r.source for r in rows if getattr(r, "source", None)})
```

(The `hasattr` guards keep the code resilient against tracker-query helpers that may or may not exist on this branch — if a helper is missing, the dropdown is just empty rather than crashing.)

- [ ] **Step 6: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 315 tests pass (307 + 8).

- [ ] **Step 7: Commit**

```powershell
git add scripts/dashboard/file_input.py scripts/dashboard/data.py tests/dashboard/test_file_input.py
git commit -m "feat: add three-way file_input picker + data list helpers"
```

---

## Task 4 — Profile schema: log_handoffs field

**Files:**
- Modify: `scripts/tracker/models.py`
- Modify: `scripts/tracker/profile.py`
- Modify: `tests/tracker/test_profile.py`

### Steps

- [ ] **Step 1: Write failing tests for log_handoffs profile field**

Append to `tests/tracker/test_profile.py`:

```python
def test_profile_default_log_handoffs_is_true():
    from scripts.tracker.models import Profile
    p = Profile()
    assert p.log_handoffs is True


def test_read_profile_missing_log_handoffs_defaults_to_true(tmp_path, monkeypatch):
    from scripts.tracker import profile
    monkeypatch.setattr(profile, "PROFILE_PATH", tmp_path / "profile.json")
    (tmp_path / "profile.json").write_text('{"focus_areas": ["A"], "healthy_weekly_rate": 5}', encoding="utf-8")
    p = profile.read_profile()
    assert p.log_handoffs is True


def test_write_profile_persists_log_handoffs_false(tmp_path, monkeypatch):
    from scripts.tracker import profile
    from scripts.tracker.models import Profile
    monkeypatch.setattr(profile, "PROFILE_PATH", tmp_path / "profile.json")
    profile.write_profile(Profile(focus_areas=["X"], healthy_weekly_rate=4, log_handoffs=False))
    data = (tmp_path / "profile.json").read_text(encoding="utf-8")
    assert '"log_handoffs": false' in data


def test_round_trip_log_handoffs_false(tmp_path, monkeypatch):
    from scripts.tracker import profile
    from scripts.tracker.models import Profile
    monkeypatch.setattr(profile, "PROFILE_PATH", tmp_path / "profile.json")
    profile.write_profile(Profile(focus_areas=["X"], healthy_weekly_rate=4, log_handoffs=False))
    p = profile.read_profile()
    assert p.log_handoffs is False
```

- [ ] **Step 2: Verify the tests fail**

```powershell
python -m pytest tests/tracker/test_profile.py -v
```

Expected: 4 failures (`log_handoffs` not a Profile field yet).

- [ ] **Step 3: Add log_handoffs to the Profile dataclass**

In `scripts/tracker/models.py`, find the `Profile` dataclass and add the new field after `pacing_notes`:

```python
@dataclass
class Profile:
    focus_areas: List[str] = field(default_factory=list)
    healthy_weekly_rate: Optional[int] = None
    pacing_notes: Optional[str] = None
    log_handoffs: bool = True
```

- [ ] **Step 4: Update read_profile / write_profile to handle log_handoffs**

In `scripts/tracker/profile.py`, find `read_profile`. It should already parse the JSON into a dict and construct a Profile. Update the construction to include `log_handoffs`:

```python
def read_profile() -> Profile:
    if not PROFILE_PATH.exists():
        return Profile()
    data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    return Profile(
        focus_areas=data.get("focus_areas", []),
        healthy_weekly_rate=data.get("healthy_weekly_rate"),
        pacing_notes=data.get("pacing_notes"),
        log_handoffs=data.get("log_handoffs", True),
    )
```

And `write_profile` to serialize it:

```python
def write_profile(profile: Profile) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "focus_areas": profile.focus_areas,
        "healthy_weekly_rate": profile.healthy_weekly_rate,
        "pacing_notes": profile.pacing_notes,
        "log_handoffs": profile.log_handoffs,
    }
    PROFILE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
```

(If the existing `write_profile` uses a different style — e.g. `dataclasses.asdict` — preserve that style and just ensure the new field is included.)

- [ ] **Step 5: Verify the tests pass**

```powershell
python -m pytest tests/tracker/test_profile.py -v
```

Expected: All tests in that file pass (existing + 4 new).

- [ ] **Step 6: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 319 tests pass (315 + 4).

- [ ] **Step 7: Commit**

```powershell
git add scripts/tracker/models.py scripts/tracker/profile.py tests/tracker/test_profile.py
git commit -m "feat: add log_handoffs field to Profile schema"
```

---

## Phase 2 — Workflows tab + pure-LLM cards (Tasks 5-10)

---

## Task 5 — workflows/__init__.py + shared _handoff_card helper

**Files:**
- Create: `scripts/dashboard/workflows/__init__.py`
- Create: `scripts/dashboard/workflows/_card.py`
- Create: `tests/dashboard/test_workflows_card.py`

### Steps

- [ ] **Step 1: Write failing tests for the args-validation helper**

Create `tests/dashboard/test_workflows_card.py`:

```python
"""Tests for the shared workflow-card helper."""
from pathlib import Path


def test_collect_args_filters_none_and_empty():
    from scripts.dashboard.workflows._card import collect_args
    assert collect_args([Path("a.docx"), None, "", "b.txt"]) == ["a.docx", "b.txt"]


def test_collect_args_stringifies_paths(tmp_path):
    from scripts.dashboard.workflows._card import collect_args
    p = tmp_path / "r.docx"
    p.write_bytes(b"")
    result = collect_args([p])
    assert result == [str(p)]


def test_collect_args_passes_strings_through():
    from scripts.dashboard.workflows._card import collect_args
    assert collect_args(["https://jd.url", "extra"]) == ["https://jd.url", "extra"]


def test_collect_args_all_none_returns_empty():
    from scripts.dashboard.workflows._card import collect_args
    assert collect_args([None, None]) == []
```

- [ ] **Step 2: Verify the tests fail**

```powershell
python -m pytest tests/dashboard/test_workflows_card.py -v
```

Expected: 4 failures with `ImportError`.

- [ ] **Step 3: Create the workflows package and _card helper**

Create `scripts/dashboard/workflows/__init__.py`:

```python
"""Per-slash-command workflow modules for the dashboard.

Each module exposes a single `render(file_path=None)` function called by either
the Workflows tab or an inline contextual button. Validator-backed modules run
their analyzer in-dashboard; pure-LLM modules collect inputs and trigger the
clipboard handoff.
"""
```

Create `scripts/dashboard/workflows/_card.py`:

```python
"""Shared helpers for workflow modules: input collection, handoff buttons."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Union

import streamlit as st

from scripts.dashboard import handoff as _handoff


ArgLike = Union[str, Path, None]


def collect_args(values: Iterable[ArgLike]) -> list[str]:
    """Filter out None/empty values and stringify Path objects."""
    out: list[str] = []
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            out.append(s)
    return out


def handoff_button(cmd: str, args: Iterable[ArgLike], note: str = "", key: Optional[str] = None) -> None:
    """Render a `Copy /brains-<cmd> to clipboard` button. On click, calls handoff."""
    label = f"Copy /brains-{cmd} to clipboard"
    if st.button(label, key=key or f"handoff_{cmd}"):
        _handoff.handoff(cmd, *collect_args(args), note=note)
```

- [ ] **Step 4: Verify the tests pass**

```powershell
python -m pytest tests/dashboard/test_workflows_card.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 323 tests pass (319 + 4).

- [ ] **Step 6: Commit**

```powershell
git add scripts/dashboard/workflows/__init__.py scripts/dashboard/workflows/_card.py tests/dashboard/test_workflows_card.py
git commit -m "feat: add workflows package + shared _card helper"
```

---

## Task 6 — 5 simple pure-LLM workflow modules (create, disclosure, edit, career_change, linkedin)

**Files:**
- Create: `scripts/dashboard/workflows/create.py`
- Create: `scripts/dashboard/workflows/disclosure.py`
- Create: `scripts/dashboard/workflows/edit.py`
- Create: `scripts/dashboard/workflows/career_change.py`
- Create: `scripts/dashboard/workflows/linkedin.py`

These five modules are pure form-only handoffs. Each is a thin wrapper that collects 0-1 inputs and triggers `handoff_button`. No unit tests — covered by the Workflows tab AppTest in Task 10.

### Steps

- [ ] **Step 1: Create workflows/create.py (no inputs)**

```python
"""/brains-create — interactive interview to build a resume from scratch."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.workflows._card import handoff_button


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Create a resume from scratch.**")
    st.caption("Claude Code walks through a structured interview — pace yourself, use breaks freely.")
    handoff_button("create", [], note="Open Claude Code; paste this command to start the interview.", key="create_btn")
```

- [ ] **Step 2: Create workflows/disclosure.py (no inputs)**

```python
"""/brains-disclosure — coaching walkthrough for the disclosure decision framework."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.workflows._card import handoff_button


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Walk through the disclosure-decision framework.**")
    st.caption("Whether, when, and how to disclose neurodivergence. Always your call — this is structured reflection, not a prescription.")
    handoff_button("disclosure", [], note="Open Claude Code to start the coaching turn.", key="disclosure_btn")
```

- [ ] **Step 3: Create workflows/edit.py (1 input: resume path)**

```python
"""/brains-edit — apply review fixes to a resume."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import pick_file
from scripts.dashboard.workflows._card import handoff_button


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Apply review fixes to a resume.**")
    st.caption("Hands the resume + the most recent review findings off to Claude Code for a clean ATS-safe rewrite.")
    if file_path is None:
        file_path = pick_file("resume", key="edit")
    st.write(f"Selected: `{file_path}`" if file_path else "_No file selected._")
    if file_path is not None:
        handoff_button("edit", [file_path], note="Claude Code will load the resume and apply review findings.", key="edit_btn")
```

- [ ] **Step 4: Create workflows/career_change.py (1 input: resume path)**

```python
"""/brains-career-change — translate experience for a pivot."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import pick_file
from scripts.dashboard.workflows._card import handoff_button


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Translate experience from one domain into another for a career pivot.**")
    if file_path is None:
        file_path = pick_file("resume", key="career_change")
    st.write(f"Selected: `{file_path}`" if file_path else "_No file selected._")
    if file_path is not None:
        handoff_button("career-change", [file_path], note="Claude Code will rewrite your experience around your pivot target.", key="career_change_btn")
```

- [ ] **Step 5: Create workflows/linkedin.py (1 input: ZIP path)**

```python
"""/brains-linkedin — ingest a LinkedIn export ZIP."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.workflows._card import handoff_button


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Ingest a LinkedIn export ZIP (third-party PII excluded automatically).**")
    st.caption("Get your LinkedIn data export from Settings → Data Privacy → Get a copy of your data → 'Want something in particular?' → Profile.")
    zip_path_str = st.text_input("Path to LinkedIn export ZIP", key="linkedin_zip_path", value=str(file_path) if file_path else "")
    if zip_path_str:
        p = Path(zip_path_str)
        if not p.exists():
            st.error(f"File not found: {p}")
        else:
            handoff_button("linkedin", [p], note="Claude Code will ingest and summarise the export.", key="linkedin_btn")
```

- [ ] **Step 6: Run the full suite to confirm no regressions**

```powershell
python -m pytest -q
```

Expected: 323 tests still pass (no new tests; modules are Streamlit-coupled).

- [ ] **Step 7: Commit**

```powershell
git add scripts/dashboard/workflows/create.py scripts/dashboard/workflows/disclosure.py scripts/dashboard/workflows/edit.py scripts/dashboard/workflows/career_change.py scripts/dashboard/workflows/linkedin.py
git commit -m "feat: add 5 simple pure-LLM workflow modules (create/disclosure/edit/career_change/linkedin)"
```

---

## Task 7 — 4 multi-input pure-LLM workflow modules (tailor, cover_letter, linkedin_improve, precheck)

**Files:**
- Create: `scripts/dashboard/workflows/tailor.py`
- Create: `scripts/dashboard/workflows/cover_letter.py`
- Create: `scripts/dashboard/workflows/linkedin_improve.py`
- Create: `scripts/dashboard/workflows/precheck.py`

### Steps

- [ ] **Step 1: Create workflows/tailor.py (2 inputs: resume + JD)**

```python
"""/brains-tailor — tailor a resume to a specific job description."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import pick_file
from scripts.dashboard.workflows._card import handoff_button


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Tailor a resume to a specific job description.**")
    if file_path is None:
        file_path = pick_file("resume", key="tailor_resume")
    jd_input = st.text_input("JD URL or file path", key="tailor_jd")
    st.write(f"Resume: `{file_path}`" if file_path else "_No resume selected._")
    if file_path is not None and jd_input:
        handoff_button("tailor", [file_path, jd_input], note="Claude Code will produce a tailored resume with focus-area alignment.", key="tailor_btn")
```

- [ ] **Step 2: Create workflows/cover_letter.py (2 inputs: resume + JD)**

```python
"""/brains-cover-letter — generate a cover letter matched to a tailored resume + JD."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import pick_file
from scripts.dashboard.workflows._card import handoff_button


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Generate a cover letter matched to a tailored resume + JD.**")
    if file_path is None:
        file_path = pick_file("resume", key="cl_resume")
    jd_input = st.text_input("JD URL or file path", key="cl_jd")
    st.write(f"Resume: `{file_path}`" if file_path else "_No resume selected._")
    if file_path is not None and jd_input:
        handoff_button("cover-letter", [file_path, jd_input], note="Claude Code will draft a cover letter against the tailored resume.", key="cl_btn")
```

- [ ] **Step 3: Create workflows/linkedin_improve.py (1 input: LinkedIn DOCX)**

```python
"""/brains-linkedin-improve — rewrite Headline / About / Experience / Skills."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import pick_file
from scripts.dashboard.workflows._card import handoff_button


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Rewrite a LinkedIn profile using the ND-aware framework.**")
    st.caption("Headline, About, Experience, Skills — identity-first, strengths-aligned.")
    if file_path is None:
        file_path = pick_file("cover_letter", key="li_improve")  # LinkedIn DOCX exports
    st.write(f"Selected: `{file_path}`" if file_path else "_No file selected._")
    if file_path is not None:
        handoff_button("linkedin-improve", [file_path], note="Claude Code will rewrite each section.", key="li_improve_btn")
```

- [ ] **Step 4: Create workflows/precheck.py (multi-input: company + role + JD)**

```python
"""/brains-precheck — six-question coaching pass; registers the application in tracker."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.workflows._card import handoff_button


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Six-question coaching pass before submitting an application.**")
    st.caption("Coaching turns happen in Claude Code; the registration writes to the tracker DB.")
    company = st.text_input("Company", key="precheck_company")
    role = st.text_input("Role", key="precheck_role")
    jd_input = st.text_input("JD URL or file path", key="precheck_jd")
    if company and role and jd_input:
        handoff_button("precheck", [company, role, jd_input], note="Claude Code will run the six coaching questions, then register the application in the tracker.", key="precheck_btn")
```

- [ ] **Step 5: Run the full suite to confirm no regressions**

```powershell
python -m pytest -q
```

Expected: 323 tests still pass.

- [ ] **Step 6: Commit**

```powershell
git add scripts/dashboard/workflows/tailor.py scripts/dashboard/workflows/cover_letter.py scripts/dashboard/workflows/linkedin_improve.py scripts/dashboard/workflows/precheck.py
git commit -m "feat: add 4 multi-input pure-LLM workflow modules (tailor/cover_letter/linkedin_improve/precheck)"
```

---

## Task 8 — Workflows tab module + wire into app.py

**Files:**
- Create: `scripts/dashboard/tabs/workflows.py`
- Modify: `scripts/dashboard/app.py`

### Steps

- [ ] **Step 1: Create the Workflows tab module**

Create `scripts/dashboard/tabs/workflows.py`:

```python
"""Workflows tab — all 15 slash commands as cards, grouped by theme."""
from __future__ import annotations

import streamlit as st

from scripts.dashboard.style import INCUBATOR_BLUE
from scripts.dashboard.workflows import (
    career_change,
    cover_letter,
    create,
    disclosure,
    edit,
    linkedin,
    linkedin_improve,
    precheck,
    tailor,
)

# Validator-backed workflows (created in Phase 3 — Tasks 11-16). Import lazily
# so this module loads cleanly during Phase 2 even though those modules don't exist yet.
def _import_phase3():
    from scripts.dashboard.workflows import check, consolidate, deai, jd_analyze, review, track
    return {
        "check": check,
        "consolidate": consolidate,
        "deai": deai,
        "jd_analyze": jd_analyze,
        "review": review,
        "track": track,
    }


def _render_card(col, slug: str, icon: str, label: str, blurb: str, module=None) -> None:
    """Render a single workflow card in the given Streamlit column."""
    with col:
        st.markdown(
            f"<div style='border:1px solid {INCUBATOR_BLUE}33; border-radius:8px; padding:12px; margin-bottom:8px;'>"
            f"<div style='font-size:1.6em;'>{icon}</div>"
            f"<div style='font-weight:600; color:{INCUBATOR_BLUE};'>{label}</div>"
            f"<div style='font-size:0.85em; color:#888;'>{blurb}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        with st.expander(f"Open {label}"):
            if module is not None:
                module.render(file_path=None)
            else:
                st.info(f"`{slug}` will be available after Phase 3 lands.")


def render() -> None:
    st.header("Workflows")
    st.caption("Run any BRAINS workflow from here. Validator-backed ones execute in-dashboard; LLM-heavy ones copy the slash command to your clipboard for Claude Code.")

    phase3 = {}
    try:
        phase3 = _import_phase3()
    except Exception:
        phase3 = {}

    st.subheader("Resume workflows")
    cols = st.columns(3)
    _render_card(cols[0], "review",       "🔍", "Review",       "Audit a resume for ND-bias, ATS, and integrity", phase3.get("review"))
    _render_card(cols[1], "edit",         "✏️", "Edit",         "Apply review fixes to a resume", edit)
    _render_card(cols[2], "tailor",       "🎯", "Tailor",       "Customise a resume to a specific JD", tailor)
    cols = st.columns(3)
    _render_card(cols[0], "cover-letter", "💌", "Cover letter", "Generate a cover letter for a JD", cover_letter)
    _render_card(cols[1], "create",       "🆕", "Create",       "Build a resume from scratch", create)
    _render_card(cols[2], "deai",         "🧹", "De-AI",        "Scan + suggest de-AI rewrites", phase3.get("deai"))
    cols = st.columns(3)
    _render_card(cols[0], "check",        "✅", "Final check",  "ATS + integrity + bias + AI-signal composite", phase3.get("check"))

    st.subheader("JD & application workflows")
    cols = st.columns(3)
    _render_card(cols[0], "jd-analyze",    "📋", "JD analyze",     "Red flags, masking cost, role-fit", phase3.get("jd_analyze"))
    _render_card(cols[1], "precheck",      "🛡️", "Pre-application","Six-question coaching pass", precheck)
    _render_card(cols[2], "track",         "📈", "Track",          "Manage application outcomes", phase3.get("track"))
    cols = st.columns(3)
    _render_card(cols[0], "career-change", "🔄", "Career change",  "Translate experience for a pivot", career_change)

    st.subheader("LinkedIn & coaching workflows")
    cols = st.columns(3)
    _render_card(cols[0], "linkedin",         "📥", "LinkedIn ingest", "Import a LinkedIn export ZIP", linkedin)
    _render_card(cols[1], "linkedin-improve", "💼", "LinkedIn improve","Rewrite Headline / About / etc.", linkedin_improve)
    _render_card(cols[2], "consolidate",      "🧩", "Consolidate",     "Resolve resume ↔ LinkedIn inconsistencies", phase3.get("consolidate"))
    cols = st.columns(3)
    _render_card(cols[0], "disclosure",       "💭", "Disclosure",      "Walk through disclosure decision", disclosure)
```

- [ ] **Step 2: Wire the Workflows tab into app.py**

Read the current `scripts/dashboard/app.py`. Find the `st.tabs([...])` call (currently 7 entries) and update it to 8:

```python
tab_overview, tab_resumes, tab_cover_letters, tab_jds, tab_applications, tab_analytics, tab_pacing, tab_workflows = st.tabs([
    "Overview", "Resumes", "Cover Letters", "JDs", "Applications", "Analytics", "Pacing", "Workflows",
])
```

Add the matching `with` block at the end of the existing tab blocks:

```python
with tab_workflows:
    from scripts.dashboard.tabs import workflows as workflows_tab
    workflows_tab.render()
```

- [ ] **Step 3: Run the full suite to confirm no regressions**

```powershell
python -m pytest -q
```

Expected: 323 tests still pass.

- [ ] **Step 4: Smoke-import the new tab**

```powershell
python -c "from scripts.dashboard.tabs import workflows; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 5: Commit**

```powershell
git add scripts/dashboard/tabs/workflows.py scripts/dashboard/app.py
git commit -m "feat: add Workflows tab with 15 command cards"
```

---

## Task 9 — Sidebar handoff-log toggle + recent-handoffs viewer

**Files:**
- Modify: `scripts/dashboard/sidebar.py`

### Steps

- [ ] **Step 1: Read current sidebar.py**

Read `scripts/dashboard/sidebar.py` to find the existing `render_sidebar()` function and the spot after the pacing_notes textarea + Save button.

- [ ] **Step 2: Add handoff-log section after the existing profile editor**

Edit `sidebar.py` to import the handoff log dir and add a section after the Save button. Insert before the version footer:

```python
def _render_handoff_section(profile) -> None:
    import datetime
    from pathlib import Path

    from scripts.dashboard import handoff

    st.markdown("---")
    st.markdown("**Handoff log**")
    new_value = st.checkbox(
        "Log handoffs to disk",
        value=profile.log_handoffs,
        key="sidebar_log_handoffs",
        help=f"Writes one .txt per handoff to {handoff.HANDOFF_LOG_DIR}",
    )
    if new_value != profile.log_handoffs:
        from scripts.tracker import profile as profile_io
        profile.log_handoffs = new_value
        profile_io.write_profile(profile)
        st.toast("Handoff-log preference saved.", icon="✓")

    with st.expander("Recent handoffs (last 10)"):
        if not handoff.HANDOFF_LOG_DIR.exists():
            st.caption("_No handoffs logged yet._")
            return
        files = sorted(handoff.HANDOFF_LOG_DIR.glob("*.txt"), reverse=True)[:10]
        if not files:
            st.caption("_No handoffs logged yet._")
            return
        for f in files:
            ts = datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            st.caption(f"`{f.name}` — {ts}")
```

Then call `_render_handoff_section(profile)` from inside `render_sidebar()` just before the version footer.

- [ ] **Step 3: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 323 tests still pass.

- [ ] **Step 4: Smoke-import**

```powershell
python -c "from scripts.dashboard import sidebar; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 5: Commit**

```powershell
git add scripts/dashboard/sidebar.py
git commit -m "feat: add sidebar handoff-log toggle and recent-handoffs viewer"
```

---

## Task 10 — AppTest happy-path for Workflows tab

**Files:**
- Create: `tests/dashboard/test_app_workflows_tab.py`

### Steps

- [ ] **Step 1: Write the AppTest happy-path**

Create `tests/dashboard/test_app_workflows_tab.py`:

```python
"""AppTest: the Workflows tab renders without exceptions."""
from pathlib import Path

import pytest

APP_PATH = Path(__file__).parent.parent.parent / "scripts" / "dashboard" / "app.py"


@pytest.fixture
def empty_tracker(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "p.json"))
    return tmp_path


def test_workflows_tab_renders_without_exception(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=15)
    assert not at.exception, f"App raised: {at.exception}"


def test_workflows_tab_has_workflows_header(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=15)
    headers = [h.value for h in at.header]
    assert "Workflows" in headers


def test_workflows_tab_has_three_subheaders(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=15)
    subheaders = [s.value for s in at.subheader]
    assert "Resume workflows" in subheaders
    assert "JD & application workflows" in subheaders
    assert "LinkedIn & coaching workflows" in subheaders
```

- [ ] **Step 2: Run the new tests**

```powershell
python -m pytest tests/dashboard/test_app_workflows_tab.py -v
```

Expected: 3 tests pass.

- [ ] **Step 3: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 326 tests pass (323 + 3).

- [ ] **Step 4: Commit**

```powershell
git add tests/dashboard/test_app_workflows_tab.py
git commit -m "test: add AppTest happy-path for Workflows tab"
```

---

## Phase 3 — Validator-backed workflow modules (Tasks 11-16)

---

## Task 11 — workflows/deai.py (uses ai_signal_check)

**Files:**
- Create: `scripts/dashboard/workflows/deai.py`

### Steps

- [ ] **Step 1: Create deai.py**

```python
"""/brains-deai — scan a DOCX for AI-tell signals + optional Claude Code handoff."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import is_docx, pick_file
from scripts.dashboard.workflows._card import handoff_button
from scripts.validators import ai_signal_check


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Scan a document for AI-tell signals.**")
    st.caption("Runs the nine-finding-code de-AI scanner natively. Use the handoff button for rewrite suggestions in Claude Code.")
    if file_path is None:
        file_path = pick_file("resume", key="deai")
    if file_path is None:
        return

    st.write(f"Selected: `{file_path}`")
    if not is_docx(file_path):
        st.error("DOCX required for in-dashboard scan. Use the handoff button (Claude Code can read PDFs).")
        handoff_button("deai", [file_path], note="Run de-AI scan in Claude Code (reads PDF).", key="deai_handoff_pdf")
        return

    if st.button("Scan now", key="deai_scan_btn"):
        try:
            result = ai_signal_check.scan(str(file_path))
        except Exception as e:
            st.error(f"Scan failed: {e}")
            return
        score = getattr(result, "score", None)
        findings = getattr(result, "findings", [])
        if score is not None:
            colour = "green" if score < 30 else ("orange" if score < 60 else "red")
            st.markdown(f"**Score:** <span style='color:{colour}; font-size:1.4em; font-weight:600;'>{score}/100</span> (lower is better)", unsafe_allow_html=True)
        if findings:
            st.subheader("Findings")
            for f in findings:
                code = getattr(f, "code", "?")
                severity = getattr(f, "severity", "?")
                snippet = getattr(f, "snippet", "")
                with st.expander(f"{code} — {severity}"):
                    st.code(snippet, language="text")
        else:
            st.success("No de-AI findings.")

    st.markdown("---")
    handoff_button("deai", [file_path], note="Get rewrite suggestions in Claude Code.", key="deai_handoff_btn")
```

- [ ] **Step 2: Update Workflows tab to use the deai module**

The Workflows tab's `_import_phase3()` already imports `deai`. No edit needed; the tab will now wire `deai` to its card automatically once the module exists.

- [ ] **Step 3: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 326 tests still pass.

- [ ] **Step 4: Smoke-import**

```powershell
python -c "from scripts.dashboard.workflows import deai; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 5: Commit**

```powershell
git add scripts/dashboard/workflows/deai.py
git commit -m "feat: add /brains-deai validator-backed workflow surface"
```

---

## Task 12 — workflows/jd_analyze.py (uses jd_analyzer)

**Files:**
- Create: `scripts/dashboard/workflows/jd_analyze.py`

### Steps

- [ ] **Step 1: Create jd_analyze.py**

```python
"""/brains-jd-analyze — analyze a JD for ND-relevant signals + optional handoff."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.workflows._card import handoff_button
from scripts.validators import jd_analyzer


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Analyse a job description for ND-relevant signals.**")
    st.caption("Red flags, masking cost, role-fit score (vs your profile focus areas), duplicate-application check.")

    jd_text = st.text_area("Paste JD text", key="jda_text", height=180, value="")
    jd_url = st.text_input("Or JD URL / file path (for the Claude Code handoff)", key="jda_url")

    if st.button("Analyze", key="jda_analyze_btn"):
        if not jd_text.strip():
            st.error("Paste the JD text first (in-dashboard analyzer needs raw text).")
        else:
            try:
                result = jd_analyzer.analyze(jd_text)
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                return
            red_flags = getattr(result, "red_flags", [])
            masking_cost = getattr(result, "masking_cost", None)
            role_fit = getattr(result, "role_fit", None)
            if red_flags:
                st.subheader("Red flags")
                for f in red_flags:
                    st.warning(getattr(f, "message", str(f)))
            else:
                st.success("No red flags surfaced.")
            if masking_cost is not None:
                st.metric("Masking cost", f"{masking_cost}/10")
            if role_fit is not None:
                st.metric("Role-fit score", f"{role_fit}/100")

    st.markdown("---")
    handoff_arg = jd_url or "(paste-from-clipboard)"
    handoff_button("jd-analyze", [handoff_arg], note="Full coaching report in Claude Code (will load the JD).", key="jda_handoff_btn")
```

- [ ] **Step 2: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 326 tests still pass.

- [ ] **Step 3: Commit**

```powershell
git add scripts/dashboard/workflows/jd_analyze.py
git commit -m "feat: add /brains-jd-analyze validator-backed workflow surface"
```

---

## Task 13 — workflows/track.py (fully in-dashboard tracker CRUD)

**Files:**
- Create: `scripts/dashboard/workflows/track.py`

### Steps

- [ ] **Step 1: Create track.py**

```python
"""/brains-track — full tracker CRUD in-dashboard (no LLM handoff needed)."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.tracker import add as tracker_add, query as tracker_query

EVENT_TYPES = [
    "acknowledged", "callback", "phone_screen", "first_round", "second_round",
    "take_home", "offer", "rejection", "ghosted", "withdrew",
]


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Manage the application tracker.**")
    st.caption("Fully in-dashboard — no Claude Code handoff for tracker actions.")

    apps = tracker_query.list_applications()
    if not apps:
        st.info("No applications tracked yet. Use the Pre-application workflow to register the first one.")
        return

    options = {f"#{a.id} — {a.company} / {a.role}": a.id for a in apps}
    selected_label = st.selectbox("Pick an application", options=list(options.keys()), key="track_pick")
    app_id = options[selected_label]

    event_type = st.selectbox("Event type", EVENT_TYPES, key="track_event")
    event_date = st.date_input("Date", value=date.today(), key="track_date")
    notes = st.text_input("Notes (optional)", key="track_notes")

    if st.button("Log outcome", key="track_log_btn"):
        try:
            tracker_add.record_outcome(app_id=app_id, event_type=event_type, event_date=event_date.isoformat(), notes=notes or None)
            st.success(f"Logged `{event_type}` on application #{app_id}.")
        except Exception as e:
            st.error(f"Failed to log outcome: {e}")
```

- [ ] **Step 2: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 326 tests still pass.

- [ ] **Step 3: Commit**

```powershell
git add scripts/dashboard/workflows/track.py
git commit -m "feat: add /brains-track in-dashboard tracker CRUD workflow"
```

---

## Task 14 — workflows/consolidate.py (uses consolidation_check)

**Files:**
- Create: `scripts/dashboard/workflows/consolidate.py`

### Steps

- [ ] **Step 1: Create consolidate.py**

```python
"""/brains-consolidate — diff a resume against a LinkedIn export + optional handoff."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import pick_file
from scripts.dashboard.workflows._card import handoff_button
from scripts.validators import consolidation_check


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Detect inconsistencies between a resume and a LinkedIn profile.**")
    st.caption("In-dashboard diff produces the structural inconsistency list. Use the handoff button to get LLM-coached resolutions.")

    resume_path = file_path or pick_file("resume", key="cons_resume")
    linkedin_path_str = st.text_input("LinkedIn export DOCX or ZIP path", key="cons_linkedin")
    linkedin_path = Path(linkedin_path_str) if linkedin_path_str else None

    if resume_path and linkedin_path and linkedin_path.exists():
        if st.button("Diff", key="cons_diff_btn"):
            try:
                result = consolidation_check.diff(str(resume_path), str(linkedin_path))
            except Exception as e:
                st.error(f"Diff failed: {e}")
                return
            inconsistencies = getattr(result, "inconsistencies", [])
            if not inconsistencies:
                st.success("No inconsistencies detected.")
            else:
                st.subheader("Inconsistencies")
                for inc in inconsistencies:
                    category = getattr(inc, "category", "?")
                    message = getattr(inc, "message", str(inc))
                    st.markdown(f"- **{category}**: {message}")

        st.markdown("---")
        handoff_button("consolidate", [resume_path, linkedin_path], note="Get LLM-coached resolutions for each inconsistency.", key="cons_handoff_btn")
    elif linkedin_path_str and not linkedin_path.exists():
        st.error(f"LinkedIn file not found: {linkedin_path}")
```

- [ ] **Step 2: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 326 tests still pass.

- [ ] **Step 3: Commit**

```powershell
git add scripts/dashboard/workflows/consolidate.py
git commit -m "feat: add /brains-consolidate validator-backed workflow surface"
```

---

## Task 15 — workflows/check.py (composite of 4 validators)

**Files:**
- Create: `scripts/dashboard/workflows/check.py`

### Steps

- [ ] **Step 1: Create check.py**

```python
"""/brains-check — composite final-pass: ATS + integrity + bias + AI-signal."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import is_docx, pick_file
from scripts.dashboard.workflows._card import handoff_button
from scripts.validators import ai_signal_check, ats_check, bias_scan, integrity_check


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Final pre-submit pass — ATS-safety, document integrity, ND-bias, AI-signal score.**")
    st.caption("Runs all four validators in-dashboard. Use the handoff button for the LLM coaching layer.")

    if file_path is None:
        file_path = pick_file("resume", key="check")
    if file_path is None:
        return

    st.write(f"Selected: `{file_path}`")
    if not is_docx(file_path):
        st.error("DOCX required for in-dashboard checks. Use the handoff button.")
        handoff_button("check", [file_path], note="Run composite check in Claude Code (reads PDF).", key="check_handoff_pdf")
        return

    if st.button("Run all checks", key="check_run_btn"):
        cols = st.columns(2)
        with cols[0]:
            st.subheader("ATS-safety")
            try:
                ats_result = ats_check.check(str(file_path))
                hits = getattr(ats_result, "findings", [])
                if not hits:
                    st.success("ATS-safe.")
                else:
                    for h in hits:
                        st.warning(getattr(h, "message", str(h)))
            except Exception as e:
                st.error(f"ATS check failed: {e}")

            st.subheader("Document integrity")
            try:
                integ_result = integrity_check.check(str(file_path))
                issues = getattr(integ_result, "issues", [])
                if not issues:
                    st.success("Integrity clean.")
                else:
                    for i in issues:
                        st.warning(getattr(i, "message", str(i)))
            except Exception as e:
                st.error(f"Integrity check failed: {e}")

        with cols[1]:
            st.subheader("ND-bias scan")
            try:
                bias_result = bias_scan.scan(str(file_path))
                bias_hits = getattr(bias_result, "findings", [])
                if not bias_hits:
                    st.success("No bias-catalog hits.")
                else:
                    for b in bias_hits[:5]:
                        st.warning(f"{getattr(b, 'pattern', '?')}: {getattr(b, 'message', '')}")
                    if len(bias_hits) > 5:
                        st.caption(f"+ {len(bias_hits) - 5} more")
            except Exception as e:
                st.error(f"Bias scan failed: {e}")

            st.subheader("AI-signal")
            try:
                ai_result = ai_signal_check.scan(str(file_path))
                score = getattr(ai_result, "score", None)
                if score is not None:
                    st.metric("AI-signal score (lower = better)", f"{score}/100")
            except Exception as e:
                st.error(f"AI-signal scan failed: {e}")

    st.markdown("---")
    handoff_button("check", [file_path], note="Get the LLM coaching layer in Claude Code.", key="check_handoff_btn")
```

- [ ] **Step 2: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 326 tests still pass.

- [ ] **Step 3: Commit**

```powershell
git add scripts/dashboard/workflows/check.py
git commit -m "feat: add /brains-check composite validator workflow surface"
```

---

## Task 16 — workflows/review.py (bias_scan preview + handoff)

**Files:**
- Create: `scripts/dashboard/workflows/review.py`

### Steps

- [ ] **Step 1: Create review.py**

```python
"""/brains-review — partial preview via bias_scan, full multi-pass review in Claude Code."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import is_docx, pick_file
from scripts.dashboard.workflows._card import handoff_button
from scripts.validators import bias_scan


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Audit a resume for ND-bias, ATS-safety, and integrity issues.**")
    st.caption("Dashboard shows a shallow bias-scan preview. The full multi-pass review (LLM-driven) runs in Claude Code.")

    if file_path is None:
        file_path = pick_file("resume", key="review")
    if file_path is None:
        return

    st.write(f"Selected: `{file_path}`")

    if is_docx(file_path) and st.button("Preview bias scan", key="review_preview_btn"):
        try:
            result = bias_scan.scan(str(file_path))
            findings = getattr(result, "findings", [])
            if not findings:
                st.success("No bias-catalog hits in the shallow preview.")
            else:
                st.subheader("Bias-scan preview")
                for f in findings:
                    pattern = getattr(f, "pattern", "?")
                    message = getattr(f, "message", "")
                    line = getattr(f, "line", None)
                    line_str = f" (line {line})" if line else ""
                    st.warning(f"**{pattern}**{line_str}: {message}")
        except Exception as e:
            st.error(f"Preview failed: {e}")

    st.markdown("---")
    handoff_button("review", [file_path], note="Run the full multi-pass review in Claude Code (LLM-coached).", key="review_handoff_btn")
```

- [ ] **Step 2: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 326 tests still pass.

- [ ] **Step 3: Add AppTest to confirm Phase 3 modules import cleanly**

Append to `tests/dashboard/test_app_workflows_tab.py`:

```python
def test_phase3_workflow_modules_import():
    from scripts.dashboard.workflows import check, consolidate, deai, jd_analyze, review, track  # noqa: F401
```

- [ ] **Step 4: Run the test**

```powershell
python -m pytest tests/dashboard/test_app_workflows_tab.py -v
```

Expected: 4 tests pass (3 from Task 10 + 1 new).

- [ ] **Step 5: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 327 tests pass (326 + 1).

- [ ] **Step 6: Commit**

```powershell
git add scripts/dashboard/workflows/review.py tests/dashboard/test_app_workflows_tab.py
git commit -m "feat: add /brains-review preview workflow surface + Phase 3 import smoke"
```

---

## Phase 4 — Inline contextual buttons (Tasks 17-20)

---

## Task 17 — Resumes tab inline buttons (Review / Edit / Tailor / De-AI / Check)

**Files:**
- Modify: `scripts/dashboard/tabs/resumes.py`

### Steps

- [ ] **Step 1: Read current resumes.py**

Open `scripts/dashboard/tabs/resumes.py` and locate the end of its existing `render()` function (just after the resumes table is shown).

- [ ] **Step 2: Add the inline-action block**

Append the following inside the `render()` function, after the existing table:

```python
    # Inline workflow actions
    st.markdown("---")
    st.subheader("Actions")
    versions = _list_resume_versions()
    if not versions:
        st.caption("_No resumes tracked yet._")
        return

    options = {f"{v['name']} — {v['path']}": v["path"] for v in versions}
    selected = st.selectbox("Select a resume to act on", options=list(options.keys()), key="resumes_action_pick")
    if selected:
        from pathlib import Path
        from scripts.dashboard.workflows import check as wf_check, deai as wf_deai, edit as wf_edit, review as wf_review, tailor as wf_tailor

        file_path = Path(options[selected])
        action = st.radio(
            "Action",
            ["Review", "Edit", "Tailor", "De-AI", "Final check"],
            horizontal=True,
            key="resumes_action_radio",
        )
        st.markdown("---")
        if action == "Review":
            wf_review.render(file_path=file_path)
        elif action == "Edit":
            wf_edit.render(file_path=file_path)
        elif action == "Tailor":
            wf_tailor.render(file_path=file_path)
        elif action == "De-AI":
            wf_deai.render(file_path=file_path)
        elif action == "Final check":
            wf_check.render(file_path=file_path)
```

`_list_resume_versions()` already exists in this module (added in v1.3.0 Task 12 — reads the tracker DB and returns a list of dicts with `name` and `path` keys). The snippet above uses it directly.

- [ ] **Step 3: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 327 tests still pass.

- [ ] **Step 4: Smoke-import**

```powershell
python -c "from scripts.dashboard.tabs import resumes; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 5: Commit**

```powershell
git add scripts/dashboard/tabs/resumes.py
git commit -m "feat: add inline workflow actions (Review/Edit/Tailor/De-AI/Check) on Resumes tab"
```

---

## Task 18 — Cover Letters tab inline buttons (Edit / De-AI)

**Files:**
- Modify: `scripts/dashboard/tabs/cover_letters.py`

### Steps

- [ ] **Step 1: Append inline-action block**

In `scripts/dashboard/tabs/cover_letters.py`, after the existing cover-letters table:

```python
    # Inline workflow actions
    st.markdown("---")
    st.subheader("Actions")
    rows = _list_cover_letters()
    if not rows:
        st.caption("_No cover letters tracked yet._")
        return

    options = {f"{r['name']} — {r['path']}": r["path"] for r in rows}
    selected = st.selectbox("Select a cover letter to act on", options=list(options.keys()), key="cl_action_pick")
    if selected:
        from pathlib import Path
        from scripts.dashboard.workflows import deai as wf_deai, edit as wf_edit

        file_path = Path(options[selected])
        action = st.radio("Action", ["Edit", "De-AI"], horizontal=True, key="cl_action_radio")
        st.markdown("---")
        if action == "Edit":
            wf_edit.render(file_path=file_path)
        elif action == "De-AI":
            wf_deai.render(file_path=file_path)
```

`_list_cover_letters()` already exists in this module (added in v1.3.0 Task 13 — joins cover_letters and jds tables). The snippet above uses it directly. If the dict keys differ (e.g. `file_path` instead of `path`), adapt the f-string keys to match what `_list_cover_letters()` actually returns.

- [ ] **Step 2: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 327 tests still pass.

- [ ] **Step 3: Commit**

```powershell
git add scripts/dashboard/tabs/cover_letters.py
git commit -m "feat: add inline workflow actions (Edit/De-AI) on Cover Letters tab"
```

---

## Task 19 — JDs tab inline buttons (Analyze / Tailor-to-this-JD)

**Files:**
- Modify: `scripts/dashboard/tabs/jds.py`

### Steps

- [ ] **Step 1: Append inline-action block**

In `scripts/dashboard/tabs/jds.py`, after the existing JDs table:

```python
    # Inline workflow actions
    st.markdown("---")
    st.subheader("Actions")
    rows = _list_jds()
    if not rows:
        st.caption("_No JDs tracked yet._")
        return

    options = {f"{r['title']} — {r['source']}": r["source"] for r in rows}
    selected = st.selectbox("Select a JD to act on", options=list(options.keys()), key="jds_action_pick")
    if selected:
        from scripts.dashboard.workflows import jd_analyze as wf_jda, tailor as wf_tailor

        jd_source = options[selected]
        action = st.radio("Action", ["Analyze", "Tailor a resume to this JD"], horizontal=True, key="jds_action_radio")
        st.markdown("---")
        if action == "Analyze":
            wf_jda.render(file_path=None)
            st.caption(f"JD source: `{jd_source}` — paste its text into the analyzer above, or use the handoff button.")
        elif action == "Tailor a resume to this JD":
            wf_tailor.render(file_path=None)
            st.caption(f"JD source pre-filled: `{jd_source}`")
```

- [ ] **Step 2: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 327 tests still pass.

- [ ] **Step 3: Commit**

```powershell
git add scripts/dashboard/tabs/jds.py
git commit -m "feat: add inline workflow actions (Analyze/Tailor) on JDs tab"
```

---

## Task 20 — Applications tab inline buttons (Track update)

**Files:**
- Modify: `scripts/dashboard/tabs/applications.py`

### Steps

- [ ] **Step 1: Append inline-action block**

In `scripts/dashboard/tabs/applications.py`, after the existing applications table:

```python
    # Inline workflow actions
    st.markdown("---")
    st.subheader("Log a new outcome")
    from scripts.dashboard.workflows import track as wf_track
    wf_track.render(file_path=None)
```

- [ ] **Step 2: Add AppTest happy-path for tabs gaining inline actions**

Append to `tests/dashboard/test_app_workflows_tab.py`:

```python
def test_resumes_tab_has_actions_subheader(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=15)
    subheaders = [s.value for s in at.subheader]
    assert "Actions" in subheaders or "Log a new outcome" in subheaders


def test_app_does_not_raise_with_all_inline_actions(empty_tracker):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH))
    at.run(timeout=15)
    assert not at.exception, f"App raised: {at.exception}"
```

- [ ] **Step 3: Run the tests**

```powershell
python -m pytest tests/dashboard/test_app_workflows_tab.py -v
```

Expected: 6 tests pass (4 prior + 2 new).

- [ ] **Step 4: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 329 tests pass (327 + 2).

- [ ] **Step 5: Commit**

```powershell
git add scripts/dashboard/tabs/applications.py tests/dashboard/test_app_workflows_tab.py
git commit -m "feat: add inline outcome-logging on Applications tab + tab-render smoke"
```

---

## Phase 5 — Release polish (Tasks 21-24)

---

## Task 21 — Docs updates (SKILL.md, README, brand-application, claude-project-setup)

**Files:**
- Modify: `SKILL.md`
- Modify: `README.md`
- Modify: `references/brand-application.md`
- Modify: `docs/claude-project-setup.md`

### Steps

- [ ] **Step 1: Update SKILL.md Tooling Notes**

Append a new bullet to the Tooling Notes section:

```markdown
- **Dashboard workflows** — From v1.4.0, every slash command is reachable through the dashboard. The 8th `Workflows` tab houses all 15 commands as cards; the existing Resumes / Cover Letters / JDs / Applications tabs gain inline action buttons. Validator-backed commands (de-AI, JD analyze, tracker, consolidate, final check, review preview) execute in-dashboard with no Claude Code roundtrip. LLM-heavy commands (review, edit, tailor, cover-letter, create, disclosure, linkedin, linkedin-improve, career-change, precheck) copy the ready-to-paste slash command to the clipboard. No new API key required.
```

- [ ] **Step 2: Update README.md**

In the "Launching the dashboard" section (added in v1.3.0), append:

```markdown

### What's new in v1.4.0

The dashboard now exposes every slash command:

- **Workflows tab (8th tab)** — all 15 commands as cards, grouped into Resume / JD & application / LinkedIn & coaching workflows
- **Inline action buttons** on Resumes, Cover Letters, JDs, and Applications tabs — pick a row, run the workflow directly
- **Validator-backed commands run in-dashboard** — de-AI scan, JD analyze, tracker CRUD, consolidation diff, final composite check, review preview — no Claude Code roundtrip required
- **LLM-heavy commands hand off via clipboard** — click "Copy /brains-X" → paste into Claude Code chat. Optional audit log at `~/.brains-resume/handoffs/`.

The dashboard remains read-only for resume / cover letter / JD content; the only mutable state is the profile editor and the tracker (outcomes logging).
```

- [ ] **Step 3: Update references/brand-application.md**

The Streamlit dashboard row added in v1.3.0 covers v1.4.0 too — no edit needed. Confirm by reading the file and verifying the row says "Streamlit dashboard UI (`brains-resume-dashboard`)". If a v1.4.0-specific row is appropriate, append:

```markdown
| Dashboard workflow handoffs (clipboard text) | Plain slash-command text — no BRAINS branding in the clipboard payload (the payload becomes a Claude Code chat message, which is user-private context) | Internal pipe; clipboard is not a publication surface |
```

- [ ] **Step 4: Update docs/claude-project-setup.md**

The Dashboard sub-section added in v1.3.0 covers v1.4.0 too. Append one line to that sub-section:

```markdown

From v1.4.0, the dashboard also exposes every slash command via a Workflows tab and inline action buttons — see the README's "What's new in v1.4.0" subsection for details.
```

- [ ] **Step 5: Run the full suite to confirm no regressions**

```powershell
python -m pytest -q
```

Expected: 329 tests still pass.

- [ ] **Step 6: Commit**

```powershell
git add SKILL.md README.md references/brand-application.md docs/claude-project-setup.md
git commit -m "docs: update SKILL.md, README, brand-application, and Claude Project guide for v1.4.0"
```

---

## Task 22 — CHANGELOG entry + Claude Project bundle rebuild

**Files:**
- Modify: `CHANGELOG.md`
- Rebuild: `dist/brains-resume-claude-project.zip` (gitignored)

### Steps

- [ ] **Step 1: Add v1.4.0 CHANGELOG entry**

At the top of `CHANGELOG.md`, above the v1.3.0 entry, add:

```markdown
## [1.4.0] — 2026-05-15

### Added
- **Dashboard workflows** — every slash command is now reachable through the v1.3.0 dashboard. New 8th tab `Workflows` with 15 command cards, grouped into three sections (Resume / JD & application / LinkedIn & coaching). Existing Resumes, Cover Letters, JDs, and Applications tabs gain inline action buttons that pre-fill the workflow form below the table.
- **`scripts/dashboard/workflows/` package** — one module per slash command (15 modules) exposing `render(file_path=None)`. Validator-backed modules run analyzers in-dashboard; pure-LLM modules collect inputs and trigger a clipboard handoff.
- **`scripts/dashboard/handoff.py`** — clipboard helper using `pyperclip`. Optional audit log at `~/.brains-resume/handoffs/<timestamp>-<cmd>.txt`. Graceful fallback to `st.code` block on clipboard failure.
- **`scripts/dashboard/file_input.py`** — three-way file picker (dropdown of tracker-known files / path text input / `st.file_uploader`). Uploads land in `~/.brains-resume/uploads/<kind>/`.
- **Validator-backed in-dashboard workflows** — `/brains-deai`, `/brains-jd-analyze`, `/brains-track` (full CRUD), `/brains-consolidate`, `/brains-check`, `/brains-review` (preview) execute natively. Optional Claude Code handoff for follow-on LLM coaching.
- **Pure-LLM handoff cards** — `/brains-create`, `/brains-edit`, `/brains-tailor`, `/brains-cover-letter`, `/brains-disclosure`, `/brains-linkedin`, `/brains-linkedin-improve`, `/brains-career-change`, `/brains-precheck` collect inputs and copy the ready-to-paste slash command to the clipboard.
- **Sidebar additions** — handoff-log toggle (default on, persisted to profile.json as `log_handoffs`), expander showing the last 10 handoff filenames.
- **`log_handoffs` field on Profile** — backward-compat default `True` when missing from existing profile.json.
- **`pyperclip>=1.8.0`** added to `pyproject.toml` dependencies.

### Changed
- **`SKILL.md`, `README.md`, `docs/claude-project-setup.md`** — v1.4.0 dashboard-workflows note.
- **`references/brand-application.md`** — clipboard-handoff row added to the Split Rule table.
```

- [ ] **Step 2: Rebuild Claude Project bundle**

```powershell
python scripts\packaging\build_project_bundle.py
```

Expected: prints `Wrote ...\dist\brains-resume-claude-project.zip`. Dashboard scripts (including the new workflows package) are excluded from the Claude Project bundle as they remain Claude-Code-only.

- [ ] **Step 3: Verify the bundle still has the v1.2.1 ai-signal-patterns reference**

```powershell
python -c "import zipfile; z = zipfile.ZipFile('dist/brains-resume-claude-project.zip'); names = z.namelist(); print('ai-signal-patterns:', 'brains-resume-claude-project/references/ai-signal-patterns.md' in names)"
```

Expected: `True`.

- [ ] **Step 4: Run the full suite**

```powershell
python -m pytest -q
```

Expected: 329 tests pass.

- [ ] **Step 5: Commit (the dist zip is gitignored)**

```powershell
git add CHANGELOG.md
git commit -m "docs: add v1.4.0 CHANGELOG entry"
```

`git status` should be clean afterwards.

---

## Task 23 — Version bump 1.3.0 → 1.4.0

**Files:**
- Modify: `SKILL.md`
- Modify: `pyproject.toml`

### Steps

- [ ] **Step 1: Bump SKILL.md frontmatter**

In `SKILL.md`, change:

```yaml
version: 1.3.0
```

to:

```yaml
version: 1.4.0
```

- [ ] **Step 2: Bump SKILL.md body version reference**

Find:

> This is a BRAINS Incubator project, v1.3.0.

Update to:

> This is a BRAINS Incubator project, v1.4.0.

- [ ] **Step 3: Bump pyproject.toml**

Change:

```toml
version = "1.3.0"
```

to:

```toml
version = "1.4.0"
```

- [ ] **Step 4: Run the full suite one final time**

```powershell
python -m pytest -q
```

Expected: 329 tests pass, all green.

- [ ] **Step 5: Commit**

```powershell
git add SKILL.md pyproject.toml
git commit -m "chore: bump version to 1.4.0"
```

---

## Task 24 — v1.4.0 annotated git tag

### Steps

- [ ] **Step 1: Create the v1.4.0 tag**

```powershell
git tag -a v1.4.0 -m "v1.4.0 - Dashboard workflows (all slash commands via UI)"
```

Use a hyphen, not em dash, to avoid PowerShell shell-escape issues.

- [ ] **Step 2: Verify the tag**

```powershell
git tag --list
git show v1.4.0 --stat
```

Expected: `v1.4.0` appears in the tag list; `git show v1.4.0` displays the chore commit + the SKILL.md/pyproject.toml changes.

- [ ] **Step 3: Final status check**

```powershell
git status
git log --oneline -15
```

Expected: working tree clean. The last ~24 commits trace Plan 6 work. Most recent commit is `chore: bump version to 1.4.0`. Tag points at that commit.

Do NOT push to remote — the plan does not push. When ready, the user pushes with `git push && git push --tags`.

---

## Plan completion checklist

After all 24 tasks are marked complete, verify:

- [ ] All 24 tasks have every step checked off.
- [ ] `python -m pytest -q` reports ~329 tests green (297 baseline + ~32 new — slightly under the spec's 38 estimate; the test count holds at 329).
- [ ] `git tag --list` includes `v1.4.0`.
- [ ] `dist/brains-resume-claude-project.zip` was rebuilt and still contains the v1.2.1 ai-signal-patterns reference.
- [ ] No commits include `Co-Authored-By` footers.
- [ ] No third-party org/project proper-name attribution appears in any committed file or commit message.
- [ ] `SKILL.md` frontmatter says `version: 1.4.0`.
- [ ] `pyproject.toml` says `version = "1.4.0"` and includes `pyperclip>=1.8.0`.
- [ ] `scripts/dashboard/workflows/` package exists with 15 modules (no `dashboard.py` — `/brains-dashboard` is self-referential and intentionally absent).
- [ ] `scripts/dashboard/handoff.py` and `scripts/dashboard/file_input.py` exist.
- [ ] `scripts/dashboard/tabs/workflows.py` exists; `app.py` has 8 tabs.
- [ ] Sidebar shows handoff-log toggle + recent-handoffs expander.
- [ ] Manual smoke verified: clicking a workflow handoff button copies the correct slash command to the clipboard with whitespace-quoted paths.
- [ ] Manual smoke verified: on the Resumes tab, picking a resume and an action expands the corresponding workflow form pre-filled with the file path.

When every box is ticked, v1.4.0 is shippable.
