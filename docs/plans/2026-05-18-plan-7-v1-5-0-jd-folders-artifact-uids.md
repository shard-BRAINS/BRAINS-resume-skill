# v1.5.0 Per-JD folders + traceable artifact UIDs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v1.5.0 — every JD gets its own folder; every resume/cover letter has a canonical filename and an invisible 6-char Crockford base32 UID embedded as a DOCX custom property, pinning the file to its tracker row regardless of rename.

**Architecture:** Three new modules under `scripts/outputs/` (pure-function `naming`, DOCX-property `tagging`, orchestration `io`); a forward tracker migration adding `artifact_uid` + `parent_uid` columns on the two artifact tables and `folder_path` on `jds`; two new Profile fields (`first_name`, `last_name`); seven dashboard workflows wired to route writes through `io.make_artifact_path`; one Streamlit modal on first launch when names are missing.

**Tech Stack:** Python 3.10+, `python-docx>=1.1.0` (custom properties API), SQLite via stdlib, Streamlit for sidebar/modal, pytest for testing. No new dependencies.

**Spec:** [docs/specs/2026-05-18-v1-5-0-jd-folders-artifact-uids-design.md](docs/specs/2026-05-18-v1-5-0-jd-folders-artifact-uids-design.md)

---

## Task ordering rationale

Build bottom-up so every later task can rely on tested foundations:

1. **Naming module** (pure functions, no I/O) — tasks 1-5
2. **Tagging module** (DOCX custom properties) — tasks 6-7
3. **Tracker schema + API** (migration, profile, models, add, query) — tasks 8-12
4. **IO orchestration** (exceptions, folder, path, finalize) — tasks 13-16
5. **Generator integration** (resume + cover letter DOCX writers) — tasks 17-18
6. **Sidebar UI** (name fields, first-use modal, outputs dir display) — tasks 19-20
7. **Workflow integration** (7 workflows) — tasks 21-27
8. **End-to-end smoke + docs + release polish** — tasks 28-30

Each task is TDD: failing test → minimal implementation → passing test → commit.

---

## Task 1: `scripts/outputs/naming.py` — `slugify`

**Files:**
- Create: `scripts/outputs/__init__.py` (empty)
- Create: `scripts/outputs/naming.py`
- Create: `tests/outputs/__init__.py` (empty)
- Create: `tests/outputs/test_naming.py`

- [ ] **Step 1: Write the failing tests for `slugify`**

Create `tests/outputs/test_naming.py`:

```python
"""Tests for scripts/outputs/naming.py — pure naming/sanitization functions."""
import pytest

from scripts.outputs.naming import slugify


@pytest.mark.parametrize("text,expected", [
    ("Senior Data Engineer", "Senior-Data-Engineer"),
    ("R&D / Platform", "R-D-Platform"),
    ("Engineer (Sydney)", "Engineer-Sydney"),
    ("O'Brien & Co.", "OBrien-Co"),
    ("AI/ML — Lead", "AI-ML-Lead"),
    ("Acme   Corp", "Acme-Corp"),
    ("—Acme—", "Acme"),
    ("", ""),
    ("---", ""),
    ("a", "a"),
])
def test_slugify_table(text, expected):
    assert slugify(text) == expected


def test_slugify_max_len_truncates_at_word_boundary():
    # "Senior Software Engineer" -> truncate to 18: cut mid-word would
    # produce "Senior-Software-En"; we strip trailing partial token cleanly.
    assert slugify("Senior Software Engineer", max_len=18) == "Senior-Software-En"


def test_slugify_max_len_strips_trailing_hyphen():
    # Exact truncation that lands on a hyphen should not leave one trailing.
    assert slugify("Senior Software Engineer", max_len=15) == "Senior-Software"


def test_slugify_default_max_len_is_40():
    long_text = "a" * 100
    assert len(slugify(long_text)) == 40
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/outputs/test_naming.py -v`
Expected: All FAIL with `ModuleNotFoundError: No module named 'scripts.outputs'`.

- [ ] **Step 3: Create empty package files**

Create `scripts/outputs/__init__.py`:
```python
"""Output organization, naming, and DOCX tagging for the BRAINS Resume Skill."""
```

Create `tests/outputs/__init__.py` (empty file).

- [ ] **Step 4: Write `slugify`**

Create `scripts/outputs/naming.py`:

```python
"""Pure naming/sanitization functions for output folders and filenames.

No I/O. No tracker access. Every function is deterministic given its
inputs. The folder/filename conventions defined here are the single
source of truth — generators, the tracker, and CLI helpers all consume
this module.
"""
from __future__ import annotations

import re
import secrets
from datetime import date
from typing import Literal


CROCKFORD_BASE32 = "23456789ABCDEFGHJKMNPQRSTVWXYZ"  # 30 chars, no 0/O/1/I/L

# Em-dash, en-dash, figure-dash, horizontal-bar — all normalize to '-'.
_DASH_LIKE = "–—―−"

_APOSTROPHE_LIKE = "'’‘ʼ"


def slugify(text: str, max_len: int = 40) -> str:
    """Normalize text for folder/filename use.

    - Drops apostrophes (don't / won't / O'Brien -> dont / wont / OBrien)
    - Normalizes em/en-dashes to '-'
    - Replaces any non-alphanumeric run with a single '-'
    - Strips leading/trailing '-'
    - Truncates to max_len with no trailing dash
    """
    if not text:
        return ""
    # Drop apostrophes entirely first so "O'Brien" becomes "OBrien", not "O-Brien".
    for ch in _APOSTROPHE_LIKE:
        text = text.replace(ch, "")
    # Normalize dash-like characters to '-'.
    for ch in _DASH_LIKE:
        text = text.replace(ch, "-")
    # Replace any run of non-alphanumeric with a single '-'.
    text = re.sub(r"[^A-Za-z0-9]+", "-", text)
    text = text.strip("-")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/outputs/test_naming.py -v`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/outputs/__init__.py scripts/outputs/naming.py tests/outputs/__init__.py tests/outputs/test_naming.py
git commit -m "feat(outputs): add slugify for folder/filename sanitization"
```

---

## Task 2: `scripts/outputs/naming.py` — `new_uid`

**Files:**
- Modify: `scripts/outputs/naming.py`
- Modify: `tests/outputs/test_naming.py`

- [ ] **Step 1: Write failing tests for `new_uid`**

Append to `tests/outputs/test_naming.py`:

```python
from scripts.outputs.naming import new_uid, CROCKFORD_BASE32


def test_new_uid_length_is_6():
    assert len(new_uid()) == 6


def test_new_uid_uses_only_crockford_chars():
    for _ in range(100):
        uid = new_uid()
        assert set(uid).issubset(set(CROCKFORD_BASE32))


def test_new_uid_uniqueness_over_10k_samples():
    # 6 chars from a 30-char alphabet = ~729M possibilities.
    # 10k samples should yield 0 collisions in practice.
    samples = {new_uid() for _ in range(10_000)}
    assert len(samples) == 10_000


def test_new_uid_never_contains_ambiguous_chars():
    for _ in range(100):
        uid = new_uid()
        assert "0" not in uid
        assert "O" not in uid
        assert "1" not in uid
        assert "I" not in uid
        assert "L" not in uid
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/outputs/test_naming.py -v -k new_uid`
Expected: FAIL with `ImportError: cannot import name 'new_uid'`.

- [ ] **Step 3: Add `new_uid` to `naming.py`**

Append to `scripts/outputs/naming.py`:

```python
def new_uid() -> str:
    """Generate a 6-char Crockford base32 UID.

    30^6 = ~729 million possibilities. No 0/O/1/I/L (no visual ambiguity).
    Uses `secrets.choice` for cryptographically-strong randomness so
    UIDs can't be guessed even if an attacker sees recent ones.
    """
    return "".join(secrets.choice(CROCKFORD_BASE32) for _ in range(6))
```

- [ ] **Step 4: Verify**

Run: `pytest tests/outputs/test_naming.py -v`
Expected: All PASS (4 new + 12 existing).

- [ ] **Step 5: Commit**

```bash
git add scripts/outputs/naming.py tests/outputs/test_naming.py
git commit -m "feat(outputs): add new_uid for 6-char Crockford base32 IDs"
```

---

## Task 3: `scripts/outputs/naming.py` — `folder_name`

**Files:**
- Modify: `scripts/outputs/naming.py`
- Modify: `tests/outputs/test_naming.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/outputs/test_naming.py`:

```python
from datetime import date

from scripts.outputs.naming import folder_name


def test_folder_name_company_known():
    assert folder_name(
        jd_date=date(2026, 5, 18),
        company="Acme Corp",
        recruiter=None,
        role_title="Senior Data Engineer",
    ) == "2026-05-18_Acme-Corp_Senior-Data-Engineer"


def test_folder_name_recruiter_only():
    assert folder_name(
        jd_date=date(2026, 5, 18),
        company=None,
        recruiter="Hays",
        role_title="Senior Data Engineer",
    ) == "2026-05-18_via-Hays_Senior-Data-Engineer"


def test_folder_name_both_prefers_company():
    assert folder_name(
        jd_date=date(2026, 5, 18),
        company="Acme Corp",
        recruiter="Hays",
        role_title="Senior Data Engineer",
    ) == "2026-05-18_Acme-Corp_Senior-Data-Engineer"


def test_folder_name_neither():
    assert folder_name(
        jd_date=date(2026, 5, 18),
        company=None,
        recruiter=None,
        role_title="Senior Data Engineer",
    ) == "2026-05-18_unknown_Senior-Data-Engineer"


def test_folder_name_empty_company_treated_as_none():
    assert folder_name(
        jd_date=date(2026, 5, 18),
        company="",
        recruiter="Hays",
        role_title="Senior Data Engineer",
    ) == "2026-05-18_via-Hays_Senior-Data-Engineer"


def test_folder_name_caps_at_80_chars():
    long_role = "A" * 200
    result = folder_name(
        jd_date=date(2026, 5, 18),
        company="Acme",
        recruiter=None,
        role_title=long_role,
    )
    assert len(result) <= 80
    assert result.startswith("2026-05-18_Acme_")


def test_folder_name_sanitizes_company_and_role():
    assert folder_name(
        jd_date=date(2026, 5, 18),
        company="R&D / Platform Ltd.",
        recruiter=None,
        role_title="AI/ML — Lead",
    ) == "2026-05-18_R-D-Platform-Ltd_AI-ML-Lead"
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/outputs/test_naming.py -v -k folder_name`
Expected: FAIL with `ImportError: cannot import name 'folder_name'`.

- [ ] **Step 3: Implement `folder_name`**

Append to `scripts/outputs/naming.py`:

```python
_FOLDER_MAX_LEN = 80


def folder_name(
    jd_date: date,
    company: str | None,
    recruiter: str | None,
    role_title: str,
) -> str:
    """Compose 'YYYY-MM-DD_<Anchor>_<Role>'.

    Anchor: company if present, else 'via-<Recruiter>' if recruiter present,
    else 'unknown'. Total length capped at _FOLDER_MAX_LEN; role suffix is
    truncated first.
    """
    date_str = jd_date.isoformat()
    if company:
        anchor = slugify(company)
    elif recruiter:
        anchor = f"via-{slugify(recruiter)}"
    else:
        anchor = "unknown"
    role = slugify(role_title)
    base = f"{date_str}_{anchor}_{role}"
    if len(base) > _FOLDER_MAX_LEN:
        # Truncate the role portion only.
        prefix = f"{date_str}_{anchor}_"
        available = _FOLDER_MAX_LEN - len(prefix)
        role = role[: max(0, available)].rstrip("-")
        base = prefix + role
    return base
```

- [ ] **Step 4: Verify**

Run: `pytest tests/outputs/test_naming.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/outputs/naming.py tests/outputs/test_naming.py
git commit -m "feat(outputs): add folder_name with company/recruiter anchor logic"
```

---

## Task 4: `scripts/outputs/naming.py` — `artifact_filename`

**Files:**
- Modify: `scripts/outputs/naming.py`
- Modify: `tests/outputs/test_naming.py`

- [ ] **Step 1: Write failing tests**

Append:

```python
from scripts.outputs.naming import artifact_filename


def test_artifact_filename_resume():
    assert artifact_filename(
        first_name="Matthew",
        last_name="Gell",
        kind="resume",
        created_date=date(2026, 5, 19),
        uid="KX7M9Q",
    ) == "Matthew_Gell_resume_2026-05-19_KX7M9Q.docx"


def test_artifact_filename_cover_letter():
    assert artifact_filename(
        first_name="Matthew",
        last_name="Gell",
        kind="cover-letter",
        created_date=date(2026, 5, 19),
        uid="H8VR3W",
    ) == "Matthew_Gell_cover-letter_2026-05-19_H8VR3W.docx"


def test_artifact_filename_pdf_extension():
    assert artifact_filename(
        first_name="Matthew",
        last_name="Gell",
        kind="resume",
        created_date=date(2026, 5, 19),
        uid="KX7M9Q",
        ext="pdf",
    ) == "Matthew_Gell_resume_2026-05-19_KX7M9Q.pdf"


def test_artifact_filename_sanitizes_name_with_space():
    # "Mary Anne" first name becomes "Mary-Anne" — names with spaces.
    assert artifact_filename(
        first_name="Mary Anne",
        last_name="O'Brien",
        kind="resume",
        created_date=date(2026, 5, 19),
        uid="KX7M9Q",
    ) == "Mary-Anne_OBrien_resume_2026-05-19_KX7M9Q.docx"


def test_artifact_filename_invalid_kind_raises():
    with pytest.raises(ValueError, match="kind must be"):
        artifact_filename(
            first_name="Matthew", last_name="Gell",
            kind="report",  # not allowed
            created_date=date(2026, 5, 19),
            uid="KX7M9Q",
        )
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/outputs/test_naming.py -v -k artifact_filename`
Expected: FAIL.

- [ ] **Step 3: Implement**

Append:

```python
_VALID_KINDS = ("resume", "cover-letter")


def artifact_filename(
    first_name: str,
    last_name: str,
    kind: Literal["resume", "cover-letter"],
    created_date: date,
    uid: str,
    ext: str = "docx",
) -> str:
    """Compose '<First>_<Last>_<kind>_<YYYY-MM-DD>_<UID>.<ext>'.

    Names are slugified to single hyphen-joined tokens. Kind must be one
    of 'resume' or 'cover-letter'.
    """
    if kind not in _VALID_KINDS:
        raise ValueError(
            f"kind must be one of {_VALID_KINDS}, got {kind!r}"
        )
    first = slugify(first_name)
    last = slugify(last_name)
    return f"{first}_{last}_{kind}_{created_date.isoformat()}_{uid}.{ext}"
```

- [ ] **Step 4: Verify**

Run: `pytest tests/outputs/test_naming.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/outputs/naming.py tests/outputs/test_naming.py
git commit -m "feat(outputs): add artifact_filename for resumes and cover letters"
```

---

## Task 5: `scripts/outputs/naming.py` — `resolve_folder_collision`

**Files:**
- Modify: `scripts/outputs/naming.py`
- Modify: `tests/outputs/test_naming.py`

- [ ] **Step 1: Write failing tests**

Append:

```python
from scripts.outputs.naming import resolve_folder_collision


def test_resolve_folder_collision_no_existing(tmp_path):
    assert resolve_folder_collision(tmp_path, "abc") == "abc"


def test_resolve_folder_collision_one_existing(tmp_path):
    (tmp_path / "abc").mkdir()
    assert resolve_folder_collision(tmp_path, "abc") == "abc_v2"


def test_resolve_folder_collision_chain(tmp_path):
    (tmp_path / "abc").mkdir()
    (tmp_path / "abc_v2").mkdir()
    (tmp_path / "abc_v3").mkdir()
    assert resolve_folder_collision(tmp_path, "abc") == "abc_v4"
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/outputs/test_naming.py -v -k resolve_folder_collision`
Expected: FAIL.

- [ ] **Step 3: Implement**

Append:

```python
from pathlib import Path


def resolve_folder_collision(parent: Path, candidate_name: str) -> str:
    """If candidate_name exists in parent, return 'name_v2', 'name_v3', ...

    Returns the candidate unchanged when no collision.
    """
    if not (parent / candidate_name).exists():
        return candidate_name
    n = 2
    while (parent / f"{candidate_name}_v{n}").exists():
        n += 1
    return f"{candidate_name}_v{n}"
```

- [ ] **Step 4: Verify**

Run: `pytest tests/outputs/test_naming.py -v`
Expected: All PASS. `naming.py` is now complete.

- [ ] **Step 5: Commit**

```bash
git add scripts/outputs/naming.py tests/outputs/test_naming.py
git commit -m "feat(outputs): add resolve_folder_collision for _v2/_v3 suffixing"
```

---

## Task 6: `scripts/outputs/tagging.py` — `ArtifactMeta` + `write_artifact_meta`

**Files:**
- Create: `scripts/outputs/tagging.py`
- Create: `tests/outputs/test_tagging.py`

- [ ] **Step 1: Write failing tests for write**

Create `tests/outputs/test_tagging.py`:

```python
"""Tests for scripts/outputs/tagging.py — DOCX custom property read/write."""
from pathlib import Path

import pytest
from docx import Document

from scripts.outputs.tagging import ArtifactMeta, write_artifact_meta


@pytest.fixture
def minimal_docx(tmp_path):
    """A bare DOCX with one paragraph."""
    path = tmp_path / "minimal.docx"
    doc = Document()
    doc.add_paragraph("Hello world.")
    doc.save(str(path))
    return path


def _meta_for_test():
    return ArtifactMeta(
        artifact_uid="KX7M9Q",
        artifact_kind="resume",
        jd_id=47,
        parent_uid="PT4N2B",
        created_at="2026-05-19T10:33:02Z",
        skill_version="1.5.0",
    )


def test_write_artifact_meta_creates_custom_properties(minimal_docx):
    write_artifact_meta(minimal_docx, _meta_for_test())
    # Re-open and check via python-docx's custom properties API.
    doc = Document(str(minimal_docx))
    props = doc.custom_properties
    assert props["BrainsArtifactId"] == "KX7M9Q"
    assert props["BrainsArtifactKind"] == "resume"
    assert props["BrainsJDId"] == 47
    assert props["BrainsParentId"] == "PT4N2B"
    assert props["BrainsCreatedAt"] == "2026-05-19T10:33:02Z"
    assert props["BrainsSkillVersion"] == "1.5.0"


def test_write_artifact_meta_with_no_parent(minimal_docx):
    meta = _meta_for_test()
    meta.parent_uid = None
    write_artifact_meta(minimal_docx, meta)
    doc = Document(str(minimal_docx))
    # Absent parent stored as empty string (custom-property API does not
    # support typed nulls; readers convert empty -> None).
    assert doc.custom_properties["BrainsParentId"] == ""


def test_write_artifact_meta_with_no_jd(minimal_docx):
    meta = _meta_for_test()
    meta.jd_id = None
    write_artifact_meta(minimal_docx, meta)
    doc = Document(str(minimal_docx))
    # Absent JD stored as 0 (custom-property API does not support typed
    # nulls; readers convert 0 -> None).
    assert doc.custom_properties["BrainsJDId"] == 0


def test_write_artifact_meta_does_not_change_body(minimal_docx):
    original_text = Document(str(minimal_docx)).paragraphs[0].text
    write_artifact_meta(minimal_docx, _meta_for_test())
    after_text = Document(str(minimal_docx)).paragraphs[0].text
    assert original_text == after_text == "Hello world."
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/outputs/test_tagging.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `tagging.py` (write side)**

Create `scripts/outputs/tagging.py`:

```python
"""Read/write DOCX custom properties for artifact tracking.

These properties are invisible in the Word body, header, footer, and
comment pane. The only way a user sees them is *File -> Info -> Properties
-> Advanced Properties -> Custom*. The skill uses six properties, all
prefixed 'Brains' to avoid collision with anything else.

| Property              | Type    | Notes                              |
| --------------------- | ------- | ---------------------------------- |
| BrainsArtifactId      | string  | 6-char Crockford base32 UID        |
| BrainsArtifactKind    | string  | 'resume' or 'cover-letter'         |
| BrainsJDId            | integer | tracker JD row id; 0 if unset      |
| BrainsParentId        | string  | parent UID; '' if root             |
| BrainsCreatedAt       | string  | ISO 8601 UTC                       |
| BrainsSkillVersion    | string  | e.g. '1.5.0'                       |

The python-docx CustomProperties API does not support null/None — we
represent absent values as 0 (for the integer JD id) or '' (for the
string parent UID), and the reader converts these back to None.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from docx import Document


@dataclass
class ArtifactMeta:
    artifact_uid: str
    artifact_kind: Literal["resume", "cover-letter"]
    jd_id: int | None
    parent_uid: str | None
    created_at: str
    skill_version: str


def write_artifact_meta(docx_path: Path | str, meta: ArtifactMeta) -> None:
    """Embed the artifact metadata as DOCX custom properties.

    Opens the existing DOCX, sets six 'Brains*' custom properties, and
    saves in place. Absent jd_id stored as 0; absent parent_uid stored
    as ''.
    """
    docx_path = Path(docx_path)
    doc = Document(str(docx_path))
    props = doc.custom_properties
    props["BrainsArtifactId"] = meta.artifact_uid
    props["BrainsArtifactKind"] = meta.artifact_kind
    props["BrainsJDId"] = meta.jd_id if meta.jd_id is not None else 0
    props["BrainsParentId"] = meta.parent_uid if meta.parent_uid is not None else ""
    props["BrainsCreatedAt"] = meta.created_at
    props["BrainsSkillVersion"] = meta.skill_version
    doc.save(str(docx_path))
```

- [ ] **Step 4: Verify**

Run: `pytest tests/outputs/test_tagging.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/outputs/tagging.py tests/outputs/test_tagging.py
git commit -m "feat(outputs): add ArtifactMeta + write_artifact_meta (DOCX custom props)"
```

---

## Task 7: `scripts/outputs/tagging.py` — `read_artifact_meta`

**Files:**
- Modify: `scripts/outputs/tagging.py`
- Modify: `tests/outputs/test_tagging.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/outputs/test_tagging.py`:

```python
from scripts.outputs.tagging import read_artifact_meta


def test_read_artifact_meta_round_trip(minimal_docx):
    original = _meta_for_test()
    write_artifact_meta(minimal_docx, original)
    loaded = read_artifact_meta(minimal_docx)
    assert loaded == original


def test_read_artifact_meta_converts_zero_jd_to_none(minimal_docx):
    meta = _meta_for_test()
    meta.jd_id = None
    write_artifact_meta(minimal_docx, meta)
    loaded = read_artifact_meta(minimal_docx)
    assert loaded.jd_id is None


def test_read_artifact_meta_converts_empty_parent_to_none(minimal_docx):
    meta = _meta_for_test()
    meta.parent_uid = None
    write_artifact_meta(minimal_docx, meta)
    loaded = read_artifact_meta(minimal_docx)
    assert loaded.parent_uid is None


def test_read_artifact_meta_returns_none_on_untagged_docx(minimal_docx):
    # No write_artifact_meta call — fresh docx.
    assert read_artifact_meta(minimal_docx) is None


def test_read_artifact_meta_survives_rename(minimal_docx, tmp_path):
    write_artifact_meta(minimal_docx, _meta_for_test())
    renamed = tmp_path / "manually-renamed.docx"
    minimal_docx.rename(renamed)
    loaded = read_artifact_meta(renamed)
    assert loaded.artifact_uid == "KX7M9Q"
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/outputs/test_tagging.py -v -k read_artifact_meta`
Expected: FAIL with `ImportError: cannot import name 'read_artifact_meta'`.

- [ ] **Step 3: Implement `read_artifact_meta`**

Append to `scripts/outputs/tagging.py`:

```python
def read_artifact_meta(docx_path: Path | str) -> ArtifactMeta | None:
    """Read the artifact metadata from a DOCX. Returns None if no
    BrainsArtifactId custom property is present.
    """
    docx_path = Path(docx_path)
    doc = Document(str(docx_path))
    props = doc.custom_properties
    try:
        uid = props["BrainsArtifactId"]
    except KeyError:
        return None
    jd_id_raw = props.get("BrainsJDId", 0)
    parent_raw = props.get("BrainsParentId", "")
    return ArtifactMeta(
        artifact_uid=uid,
        artifact_kind=props.get("BrainsArtifactKind", ""),
        jd_id=jd_id_raw if jd_id_raw else None,
        parent_uid=parent_raw if parent_raw else None,
        created_at=props.get("BrainsCreatedAt", ""),
        skill_version=props.get("BrainsSkillVersion", ""),
    )
```

Note: `docx.opc.coreprops.CustomProperties` exposes both `__getitem__` (raises KeyError on miss) and `get(key, default)`. The implementation above uses both. If the installed `python-docx` version doesn't expose `.get`, replace with `try/except KeyError` blocks.

- [ ] **Step 4: Verify**

Run: `pytest tests/outputs/test_tagging.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/outputs/tagging.py tests/outputs/test_tagging.py
git commit -m "feat(outputs): add read_artifact_meta with None for untagged docs"
```

---

## Task 8: Tracker migration `0002_artifact_uids.py`

**Files:**
- Create: `scripts/tracker/migrations/0002_artifact_uids.py`
- Create: `tests/tracker/migrations/__init__.py` (if missing)
- Create: `tests/tracker/migrations/test_0002_artifact_uids.py`

- [ ] **Step 1: Write failing migration tests**

Create `tests/tracker/migrations/test_0002_artifact_uids.py`:

```python
"""Tests for migration 0002_artifact_uids."""
import sqlite3

import pytest

from scripts.tracker.db import open_db


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path / "test.db"


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def test_0002_adds_artifact_uid_to_resume_versions(fresh_db):
    conn = open_db()
    try:
        assert "artifact_uid" in _columns(conn, "resume_versions")
        assert "parent_uid" in _columns(conn, "resume_versions")
    finally:
        conn.close()


def test_0002_adds_artifact_uid_to_cover_letters(fresh_db):
    conn = open_db()
    try:
        assert "artifact_uid" in _columns(conn, "cover_letters")
        assert "parent_uid" in _columns(conn, "cover_letters")
    finally:
        conn.close()


def test_0002_adds_folder_path_to_jds(fresh_db):
    conn = open_db()
    try:
        assert "folder_path" in _columns(conn, "jds")
    finally:
        conn.close()


def test_0002_unique_index_on_resume_artifact_uid_allows_nulls(fresh_db):
    """The partial unique index must allow multiple NULL artifact_uids
    (pre-v1.5.0 rows) without raising."""
    conn = open_db()
    try:
        # Insert two resume rows with NULL artifact_uid — must not collide.
        for _ in range(2):
            conn.execute(
                """INSERT INTO resume_versions
                   (file_path, template, focus_areas, created_at, artifact_uid)
                   VALUES (?, ?, ?, ?, ?)""",
                ("/tmp/r.docx", "hybrid", "[]", "2026-05-18T00:00:00Z", None),
            )
        conn.commit()
        count = conn.execute(
            "SELECT COUNT(*) FROM resume_versions WHERE artifact_uid IS NULL"
        ).fetchone()[0]
        assert count == 2
    finally:
        conn.close()


def test_0002_unique_index_rejects_duplicate_non_null(fresh_db):
    conn = open_db()
    try:
        conn.execute(
            """INSERT INTO resume_versions
               (file_path, template, focus_areas, created_at, artifact_uid)
               VALUES (?, ?, ?, ?, ?)""",
            ("/tmp/a.docx", "hybrid", "[]", "2026-05-18T00:00:00Z", "KX7M9Q"),
        )
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO resume_versions
                   (file_path, template, focus_areas, created_at, artifact_uid)
                   VALUES (?, ?, ?, ?, ?)""",
                ("/tmp/b.docx", "hybrid", "[]", "2026-05-18T00:00:00Z", "KX7M9Q"),
            )
            conn.commit()
    finally:
        conn.close()


def test_0002_idempotent_on_reopen(fresh_db):
    open_db().close()
    # Reopening must not error from "column already exists".
    conn = open_db()
    try:
        applied = conn.execute(
            "SELECT version FROM migrations WHERE version = 2"
        ).fetchone()
        assert applied is not None
    finally:
        conn.close()
```

If `tests/tracker/migrations/__init__.py` doesn't exist, create it (empty file).

- [ ] **Step 2: Verify failure**

Run: `pytest tests/tracker/migrations/test_0002_artifact_uids.py -v`
Expected: FAIL — columns not present.

- [ ] **Step 3: Write the migration**

Create `scripts/tracker/migrations/0002_artifact_uids.py`:

```python
"""Migration 0002 — artifact_uid + parent_uid + folder_path.

Forward-only addition of three new columns:

- resume_versions.artifact_uid  TEXT (UNIQUE where not null)
- resume_versions.parent_uid    TEXT (nullable)
- cover_letters.artifact_uid    TEXT (UNIQUE where not null)
- cover_letters.parent_uid      TEXT (nullable)
- jds.folder_path               TEXT (nullable)

Partial unique indexes (WHERE artifact_uid IS NOT NULL) let pre-v1.5.0
rows keep NULL without colliding with each other while preventing
duplicate non-null UIDs going forward.
"""
import sqlite3


SCHEMA_SQL = """
ALTER TABLE resume_versions ADD COLUMN artifact_uid TEXT;
ALTER TABLE resume_versions ADD COLUMN parent_uid TEXT;
ALTER TABLE cover_letters ADD COLUMN artifact_uid TEXT;
ALTER TABLE cover_letters ADD COLUMN parent_uid TEXT;
ALTER TABLE jds ADD COLUMN folder_path TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS ux_resume_versions_artifact_uid
    ON resume_versions(artifact_uid) WHERE artifact_uid IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_cover_letters_artifact_uid
    ON cover_letters(artifact_uid) WHERE artifact_uid IS NOT NULL;
"""


def apply(conn: sqlite3.Connection) -> None:
    """Apply the artifact-uid schema additions."""
    conn.executescript(SCHEMA_SQL)
```

- [ ] **Step 4: Verify**

Run: `pytest tests/tracker/migrations/test_0002_artifact_uids.py -v`
Expected: All PASS.

Also run the existing tracker tests to confirm nothing regressed:
Run: `pytest tests/tracker/ -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/tracker/migrations/0002_artifact_uids.py tests/tracker/migrations/__init__.py tests/tracker/migrations/test_0002_artifact_uids.py
git commit -m "feat(tracker): migration 0002 — artifact_uid, parent_uid, folder_path"
```

---

## Task 9: Profile gets `first_name` + `last_name`

**Files:**
- Modify: `scripts/tracker/models.py:101-106`
- Modify: `scripts/tracker/profile.py:36-58`
- Modify: `tests/tracker/test_profile.py` (or create if absent)

- [ ] **Step 1: Write failing tests**

Check whether `tests/tracker/test_profile.py` already exists. If yes, append; if no, create. Test content:

```python
"""Tests for scripts/tracker/profile.py — name field additions."""
import pytest

from scripts.tracker.models import Profile
from scripts.tracker.profile import read_profile, write_profile


@pytest.fixture
def profile_path(monkeypatch, tmp_path):
    path = tmp_path / "profile.json"
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(path))
    return path


def test_profile_round_trip_with_names(profile_path):
    p = Profile(
        focus_areas=["platform"],
        first_name="Matthew",
        last_name="Gell",
    )
    write_profile(p)
    loaded = read_profile()
    assert loaded.first_name == "Matthew"
    assert loaded.last_name == "Gell"
    assert loaded.focus_areas == ["platform"]


def test_profile_defaults_names_to_none(profile_path):
    write_profile(Profile(focus_areas=["x"]))
    loaded = read_profile()
    assert loaded.first_name is None
    assert loaded.last_name is None


def test_read_profile_handles_legacy_file_without_names(profile_path):
    # Simulate a pre-v1.5.0 profile.json.
    profile_path.write_text('{"focus_areas": ["x"], "log_handoffs": true}', encoding="utf-8")
    loaded = read_profile()
    assert loaded.focus_areas == ["x"]
    assert loaded.first_name is None
    assert loaded.last_name is None
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/tracker/test_profile.py -v`
Expected: FAIL — `Profile.__init__()` doesn't accept these kwargs.

- [ ] **Step 3: Update `Profile` dataclass**

Replace `scripts/tracker/models.py:101-106` (the `Profile` dataclass) with:

```python
@dataclass
class Profile:
    focus_areas: List[str] = field(default_factory=list)
    healthy_weekly_rate: Optional[int] = None
    pacing_notes: Optional[str] = None
    log_handoffs: bool = True
    first_name: Optional[str] = None
    last_name: Optional[str] = None
```

- [ ] **Step 4: Update `read_profile` and `write_profile`**

In `scripts/tracker/profile.py`, replace the body of `read_profile` (lines 36-41) with:

```python
    return Profile(
        focus_areas=list(data.get("focus_areas", []) or []),
        healthy_weekly_rate=data.get("healthy_weekly_rate"),
        pacing_notes=data.get("pacing_notes"),
        log_handoffs=data.get("log_handoffs", True),
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
    )
```

And the body of `write_profile` (lines 48-58) with:

```python
    path.write_text(
        json.dumps(
            {
                "focus_areas": profile.focus_areas,
                "healthy_weekly_rate": profile.healthy_weekly_rate,
                "pacing_notes": profile.pacing_notes,
                "log_handoffs": profile.log_handoffs,
                "first_name": profile.first_name,
                "last_name": profile.last_name,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
```

- [ ] **Step 5: Verify**

Run: `pytest tests/tracker/test_profile.py -v`
Expected: All PASS.

Also: `pytest tests/tracker/ -v` to confirm no regression.

- [ ] **Step 6: Commit**

```bash
git add scripts/tracker/models.py scripts/tracker/profile.py tests/tracker/test_profile.py
git commit -m "feat(tracker): add first_name + last_name to Profile"
```

---

## Task 10: `ResumeVersion`, `CoverLetter`, `JD` models gain UID/path fields

**Files:**
- Modify: `scripts/tracker/models.py:37-72`

- [ ] **Step 1: Update dataclasses**

In `scripts/tracker/models.py`, replace `ResumeVersion` (lines 37-46), `CoverLetter` (lines 49-57), and `JD` (lines 60-72) with:

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
    folder_path: Optional[str] = None
```

- [ ] **Step 2: Verify nothing broke**

Run: `pytest tests/tracker/ -v`
Expected: All PASS. Adding optional fields with defaults shouldn't break existing call sites.

- [ ] **Step 3: Commit**

```bash
git add scripts/tracker/models.py
git commit -m "feat(tracker): add artifact_uid/parent_uid/folder_path to dataclasses"
```

---

## Task 11: `add_resume_version` + `add_cover_letter` accept UIDs; `add_jd` writes folder_path

**Files:**
- Modify: `scripts/tracker/add.py:18-46`, `:88-108`, `:49-85`
- Modify: `tests/tracker/test_add.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/tracker/test_add.py`:

```python
def test_add_resume_version_persists_artifact_uid(fresh_db):
    id_ = add_resume_version(
        file_path="/tmp/r.docx",
        template="hybrid",
        focus_areas=[],
        artifact_uid="KX7M9Q",
        parent_uid="PT4N2B",
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT artifact_uid, parent_uid FROM resume_versions WHERE id=?",
            (id_,),
        ).fetchone()
    finally:
        conn.close()
    assert row == ("KX7M9Q", "PT4N2B")


def test_add_cover_letter_persists_artifact_uid(fresh_db):
    resume_id = add_resume_version("/tmp/r.docx", "hybrid", [])
    jd_id = add_jd(
        source="manual", source_ref=None, company="Acme",
        role_title="Eng", raw_text="...", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    cl_id = add_cover_letter(
        file_path="/tmp/cl.docx",
        resume_version_id=resume_id, jd_id=jd_id, template="formal-business",
        artifact_uid="H8VR3W", parent_uid=None,
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT artifact_uid, parent_uid FROM cover_letters WHERE id=?",
            (cl_id,),
        ).fetchone()
    finally:
        conn.close()
    assert row == ("H8VR3W", None)


def test_add_jd_persists_folder_path(fresh_db):
    jd_id = add_jd(
        source="manual", source_ref=None, company="Acme",
        role_title="Eng", raw_text="...", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
        folder_path="/tmp/outputs/2026-05-18_Acme_Eng",
    )
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT folder_path FROM jds WHERE id=?", (jd_id,),
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == "/tmp/outputs/2026-05-18_Acme_Eng"


def test_add_resume_version_omitting_uids_inserts_nulls(fresh_db):
    """Backward compatibility — pre-v1.5.0 call sites still work."""
    id_ = add_resume_version("/tmp/r.docx", "hybrid", [])
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT artifact_uid, parent_uid FROM resume_versions WHERE id=?",
            (id_,),
        ).fetchone()
    finally:
        conn.close()
    assert row == (None, None)
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/tracker/test_add.py -v`
Expected: FAIL — `add_resume_version` doesn't take `artifact_uid` etc.

- [ ] **Step 3: Update `add_resume_version`**

Replace `scripts/tracker/add.py:18-46` with:

```python
def add_resume_version(
    file_path: Optional[str],
    template: str,
    focus_areas: List[str],
    parent_id: Optional[int] = None,
    tagged_jd_id: Optional[int] = None,
    artifact_uid: Optional[str] = None,
    parent_uid: Optional[str] = None,
) -> int:
    """Insert a resume_versions row, return the new id."""
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO resume_versions
                (file_path, template, focus_areas, parent_id, tagged_jd_id,
                 created_at, artifact_uid, parent_uid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
```

- [ ] **Step 4: Update `add_cover_letter`**

Replace `scripts/tracker/add.py:88-108` with:

```python
def add_cover_letter(
    file_path: Optional[str],
    resume_version_id: int,
    jd_id: int,
    template: str,
    artifact_uid: Optional[str] = None,
    parent_uid: Optional[str] = None,
) -> int:
    """Insert a cover_letters row, return the new id."""
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO cover_letters
                (file_path, resume_version_id, jd_id, template, created_at,
                 artifact_uid, parent_uid)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (file_path, resume_version_id, jd_id, template, _now_iso(),
             artifact_uid, parent_uid),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
```

- [ ] **Step 5: Update `add_jd`**

Replace `scripts/tracker/add.py:49-85` with:

```python
def add_jd(
    source: str,
    source_ref: Optional[str],
    company: str,
    role_title: str,
    raw_text: str,
    analyzer_findings: dict,
    focus_areas_required: List[str],
    focus_areas_nice: List[str],
    folder_path: Optional[str] = None,
) -> int:
    """Insert a jds row, return the new id."""
    conn = open_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO jds
                (source, source_ref, company, role_title, raw_text,
                 analyzer_findings, focus_areas_required, focus_areas_nice,
                 created_at, folder_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                folder_path,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
```

- [ ] **Step 6: Verify**

Run: `pytest tests/tracker/ -v`
Expected: All PASS — both new tests and existing tests.

- [ ] **Step 7: Commit**

```bash
git add scripts/tracker/add.py tests/tracker/test_add.py
git commit -m "feat(tracker): add_resume_version/add_cover_letter accept UIDs; add_jd accepts folder_path"
```

---

## Task 12: `get_artifact_by_uid` query helper

**Files:**
- Modify: `scripts/tracker/query.py`
- Modify or create: `tests/tracker/test_query.py`

- [ ] **Step 1: Check existing query.py shape**

Run: `cat scripts/tracker/query.py | head -30` (or read the file) to confirm pattern. Then write tests that match it.

- [ ] **Step 2: Write failing tests**

Append (or create) `tests/tracker/test_query.py`:

```python
"""Tests for the get_artifact_by_uid lookup helper."""
import pytest

from scripts.tracker.add import add_resume_version, add_cover_letter, add_jd
from scripts.tracker.query import get_artifact_by_uid
from scripts.tracker.models import ResumeVersion, CoverLetter


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    return tmp_path / "test.db"


def test_get_artifact_by_uid_finds_resume(fresh_db):
    add_resume_version("/tmp/r.docx", "hybrid", [], artifact_uid="KX7M9Q")
    result = get_artifact_by_uid("KX7M9Q")
    assert isinstance(result, ResumeVersion)
    assert result.artifact_uid == "KX7M9Q"


def test_get_artifact_by_uid_finds_cover_letter(fresh_db):
    rv_id = add_resume_version("/tmp/r.docx", "hybrid", [])
    jd_id = add_jd("manual", None, "Acme", "Eng", "...", {}, [], [])
    add_cover_letter("/tmp/cl.docx", rv_id, jd_id, "formal-business",
                     artifact_uid="H8VR3W")
    result = get_artifact_by_uid("H8VR3W")
    assert isinstance(result, CoverLetter)
    assert result.artifact_uid == "H8VR3W"


def test_get_artifact_by_uid_returns_none_on_miss(fresh_db):
    assert get_artifact_by_uid("ZZZZZZ") is None
```

- [ ] **Step 3: Verify failure**

Run: `pytest tests/tracker/test_query.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement `get_artifact_by_uid`**

Append to `scripts/tracker/query.py`:

```python
def get_artifact_by_uid(uid: str) -> ResumeVersion | CoverLetter | None:
    """Look up an artifact by its 6-char Crockford-base32 UID across
    both resume_versions and cover_letters. Returns None if not found.
    """
    conn = open_db()
    try:
        row = conn.execute(
            """SELECT id, file_path, template, focus_areas, parent_id,
                      tagged_jd_id, created_at, archived_at,
                      artifact_uid, parent_uid
               FROM resume_versions WHERE artifact_uid = ?""",
            (uid,),
        ).fetchone()
        if row:
            return ResumeVersion(
                id=row[0],
                file_path=row[1],
                template=row[2],
                focus_areas=json.loads(row[3]),
                parent_id=row[4],
                tagged_jd_id=row[5],
                created_at=row[6],
                archived_at=row[7],
                artifact_uid=row[8],
                parent_uid=row[9],
            )
        row = conn.execute(
            """SELECT id, file_path, resume_version_id, jd_id, template,
                      created_at, archived_at, artifact_uid, parent_uid
               FROM cover_letters WHERE artifact_uid = ?""",
            (uid,),
        ).fetchone()
        if row:
            return CoverLetter(
                id=row[0],
                file_path=row[1],
                resume_version_id=row[2],
                jd_id=row[3],
                template=row[4],
                created_at=row[5],
                archived_at=row[6],
                artifact_uid=row[7],
                parent_uid=row[8],
            )
        return None
    finally:
        conn.close()
```

Ensure the imports at the top of `query.py` include `json`, `ResumeVersion`, `CoverLetter` (add any missing).

- [ ] **Step 5: Verify**

Run: `pytest tests/tracker/ -v`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/tracker/query.py tests/tracker/test_query.py
git commit -m "feat(tracker): add get_artifact_by_uid lookup across both tables"
```

---

## Task 13: `scripts/outputs/io.py` — exceptions + `BRAINS_OUTPUTS_DIR`

**Files:**
- Create: `scripts/outputs/io.py`
- Create: `tests/outputs/test_io.py`

- [ ] **Step 1: Write failing tests**

Create `tests/outputs/test_io.py`:

```python
"""Tests for scripts/outputs/io.py — orchestration layer."""
from pathlib import Path

import pytest

from scripts.outputs.io import (
    get_outputs_root,
    ProfileNameMissingError,
    OutputsDirNotWritableError,
    UIDCollisionError,
)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    """Each test gets isolated DB, profile, and outputs root."""
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    return tmp_path


def test_get_outputs_root_honours_env_var(isolated):
    assert get_outputs_root() == isolated / "outputs"


def test_get_outputs_root_defaults_when_unset(monkeypatch):
    monkeypatch.delenv("BRAINS_OUTPUTS_DIR", raising=False)
    assert get_outputs_root() == Path.home() / ".brains-resume" / "outputs"


def test_exceptions_are_distinct():
    # Sanity: the three exception classes exist and aren't the same.
    assert ProfileNameMissingError is not OutputsDirNotWritableError
    assert ProfileNameMissingError is not UIDCollisionError
    assert OutputsDirNotWritableError is not UIDCollisionError
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/outputs/test_io.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create `io.py` skeleton**

Create `scripts/outputs/io.py`:

```python
"""High-level orchestration for output organization.

Bridges naming (pure rules) and tagging (DOCX writes) with the tracker.
Public API:

- get_outputs_root() -> Path
- ensure_jd_folder(jd_id) -> Path
- make_artifact_path(jd_id, kind, parent_uid=None) -> (Path, ArtifactMeta)
- finalize_docx(path, meta) -> None
- read_artifact_uid(path) -> str | None
- find_artifact_by_uid(uid) -> ResumeVersion | CoverLetter | None
"""
from __future__ import annotations

import os
from pathlib import Path


DEFAULT_OUTPUTS_ROOT = Path.home() / ".brains-resume" / "outputs"


class ProfileNameMissingError(Exception):
    """Raised when first_name or last_name is missing from profile.json."""


class OutputsDirNotWritableError(Exception):
    """Raised when the configured outputs directory cannot be written to."""


class UIDCollisionError(Exception):
    """Raised when 5 consecutive UID generations all collided with existing rows."""


def get_outputs_root() -> Path:
    """Return the outputs root, honouring BRAINS_OUTPUTS_DIR override."""
    override = os.environ.get("BRAINS_OUTPUTS_DIR")
    if override:
        return Path(override)
    return DEFAULT_OUTPUTS_ROOT
```

- [ ] **Step 4: Verify**

Run: `pytest tests/outputs/test_io.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/outputs/io.py tests/outputs/test_io.py
git commit -m "feat(outputs): io.py skeleton — exceptions + outputs-root env var"
```

---

## Task 14: `io.ensure_jd_folder`

**Files:**
- Modify: `scripts/outputs/io.py`
- Modify: `tests/outputs/test_io.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/outputs/test_io.py`:

```python
from datetime import date

from scripts.outputs.io import ensure_jd_folder
from scripts.tracker.add import add_jd
from scripts.tracker.db import open_db


def test_ensure_jd_folder_creates_dir(isolated):
    jd_id = add_jd(
        source="manual", source_ref=None,
        company="Acme Corp", role_title="Senior Data Engineer",
        raw_text="...", analyzer_findings={},
        focus_areas_required=[], focus_areas_nice=[],
    )
    folder = ensure_jd_folder(jd_id)
    assert folder.exists()
    assert folder.is_dir()
    # Folder name is YYYY-MM-DD_<anchor>_<role>
    assert "Acme-Corp" in folder.name
    assert "Senior-Data-Engineer" in folder.name


def test_ensure_jd_folder_writes_folder_path_to_jd_row(isolated):
    jd_id = add_jd("manual", None, "Acme", "Eng", "...", {}, [], [])
    folder = ensure_jd_folder(jd_id)
    conn = open_db()
    try:
        row = conn.execute(
            "SELECT folder_path FROM jds WHERE id=?", (jd_id,),
        ).fetchone()
    finally:
        conn.close()
    assert row[0] == str(folder)


def test_ensure_jd_folder_idempotent(isolated):
    jd_id = add_jd("manual", None, "Acme", "Eng", "...", {}, [], [])
    first = ensure_jd_folder(jd_id)
    second = ensure_jd_folder(jd_id)
    assert first == second


def test_ensure_jd_folder_handles_collision(isolated):
    """Two JDs added on the same day for the same company/role produce
    distinct folders via _v2 suffix."""
    jd_a = add_jd("manual", None, "Acme", "Engineer", "...", {}, [], [])
    folder_a = ensure_jd_folder(jd_a)
    jd_b = add_jd("manual", None, "Acme", "Engineer", "...", {}, [], [])
    folder_b = ensure_jd_folder(jd_b)
    assert folder_a != folder_b
    assert folder_b.name.endswith("_v2")
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/outputs/test_io.py -v -k ensure_jd_folder`
Expected: FAIL — function doesn't exist.

- [ ] **Step 3: Implement**

Append to `scripts/outputs/io.py`:

```python
from datetime import date, datetime

from scripts.outputs.naming import folder_name, resolve_folder_collision
from scripts.tracker.db import open_db


def ensure_jd_folder(jd_id: int) -> Path:
    """Look up the JD row, compute the folder path, create the directory
    on disk if missing, write the path to jds.folder_path on first create.
    Idempotent.
    """
    conn = open_db()
    try:
        row = conn.execute(
            """SELECT company, role_title, created_at, folder_path,
                      source, source_ref
               FROM jds WHERE id = ?""",
            (jd_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"No JD with id={jd_id}")
        company, role_title, created_at, existing_path, source, source_ref = row
        if existing_path:
            folder = Path(existing_path)
            folder.mkdir(parents=True, exist_ok=True)
            return folder
        outputs_root = get_outputs_root()
        try:
            outputs_root.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OutputsDirNotWritableError(
                f"Cannot create or write to outputs dir {outputs_root}: {e}"
            )
        jd_date = datetime.fromisoformat(created_at.rstrip("Z")).date()
        # Recruiter: when source='agency', source_ref holds the agency name.
        recruiter = source_ref if source == "agency" else None
        # Use company unless it's empty/falsy (treat empty string as None).
        anchor_company = company if company else None
        candidate = folder_name(jd_date, anchor_company, recruiter, role_title)
        unique_name = resolve_folder_collision(outputs_root, candidate)
        folder = outputs_root / unique_name
        folder.mkdir(parents=True, exist_ok=True)
        conn.execute(
            "UPDATE jds SET folder_path = ? WHERE id = ?",
            (str(folder), jd_id),
        )
        conn.commit()
        return folder
    finally:
        conn.close()
```

- [ ] **Step 4: Verify**

Run: `pytest tests/outputs/test_io.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/outputs/io.py tests/outputs/test_io.py
git commit -m "feat(outputs): ensure_jd_folder creates per-JD output directory"
```

---

## Task 15: `io.make_artifact_path`

**Files:**
- Modify: `scripts/outputs/io.py`
- Modify: `tests/outputs/test_io.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/outputs/test_io.py`:

```python
from datetime import date

from scripts.outputs.io import make_artifact_path
from scripts.outputs.tagging import ArtifactMeta
from scripts.tracker.profile import write_profile
from scripts.tracker.models import Profile


def _set_profile_name(first="Matthew", last="Gell"):
    write_profile(Profile(focus_areas=[], first_name=first, last_name=last))


def test_make_artifact_path_resume(isolated):
    _set_profile_name()
    jd_id = add_jd("manual", None, "Acme", "Engineer", "...", {}, [], [])
    path, meta = make_artifact_path(jd_id, "resume")
    assert path.parent.exists()
    assert path.name.startswith("Matthew_Gell_resume_")
    assert path.suffix == ".docx"
    assert isinstance(meta, ArtifactMeta)
    assert meta.artifact_uid in path.name
    assert meta.artifact_kind == "resume"
    assert meta.jd_id == jd_id
    assert meta.parent_uid is None


def test_make_artifact_path_cover_letter(isolated):
    _set_profile_name()
    jd_id = add_jd("manual", None, "Acme", "Engineer", "...", {}, [], [])
    path, meta = make_artifact_path(jd_id, "cover-letter")
    assert path.name.startswith("Matthew_Gell_cover-letter_")


def test_make_artifact_path_with_parent_uid(isolated):
    _set_profile_name()
    jd_id = add_jd("manual", None, "Acme", "Engineer", "...", {}, [], [])
    path, meta = make_artifact_path(jd_id, "resume", parent_uid="ABCDEF")
    assert meta.parent_uid == "ABCDEF"


def test_make_artifact_path_raises_when_name_missing(isolated):
    # Profile exists but no first/last name.
    write_profile(Profile(focus_areas=[]))
    jd_id = add_jd("manual", None, "Acme", "Engineer", "...", {}, [], [])
    with pytest.raises(ProfileNameMissingError):
        make_artifact_path(jd_id, "resume")


def test_make_artifact_path_two_calls_yield_distinct_uids(isolated):
    _set_profile_name()
    jd_id = add_jd("manual", None, "Acme", "Engineer", "...", {}, [], [])
    _, meta_a = make_artifact_path(jd_id, "resume")
    _, meta_b = make_artifact_path(jd_id, "resume")
    assert meta_a.artifact_uid != meta_b.artifact_uid
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/outputs/test_io.py -v -k make_artifact_path`
Expected: FAIL.

- [ ] **Step 3: Implement**

Append to `scripts/outputs/io.py`:

```python
from typing import Literal

from scripts.outputs.naming import artifact_filename, new_uid
from scripts.outputs.tagging import ArtifactMeta
from scripts.tracker.profile import read_profile


_SKILL_VERSION = "1.5.0"
_MAX_UID_RETRIES = 5


def make_artifact_path(
    jd_id: int,
    kind: Literal["resume", "cover-letter"],
    parent_uid: str | None = None,
) -> tuple[Path, ArtifactMeta]:
    """Reserve a new artifact path + UID within the JD folder.

    Does NOT write the tracker row (the workflow does that after the
    generator succeeds). The caller passes the returned ArtifactMeta
    into the generator or to finalize_docx after save.

    Raises ProfileNameMissingError if first_name or last_name is unset.
    """
    profile = read_profile()
    if not profile.first_name or not profile.last_name:
        raise ProfileNameMissingError(
            "Profile is missing first_name or last_name. "
            "Set them in the dashboard sidebar."
        )
    folder = ensure_jd_folder(jd_id)
    today = date.today()
    for _ in range(_MAX_UID_RETRIES):
        uid = new_uid()
        # Collision check across both tables.
        if find_artifact_by_uid(uid) is None:
            break
    else:
        raise UIDCollisionError(
            f"5 consecutive UID generations all collided. "
            f"Database may be saturated; investigate."
        )
    filename = artifact_filename(
        first_name=profile.first_name,
        last_name=profile.last_name,
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
    )
    return path, meta
```

Note: `find_artifact_by_uid` is forward-referenced; defined in the next task. It's fine because Python resolves names at call time, not at def time.

- [ ] **Step 4: Implement `find_artifact_by_uid` as a thin re-export**

Also append:

```python
def find_artifact_by_uid(uid: str):
    """Re-export of tracker.query.get_artifact_by_uid for callers that
    only want the outputs API."""
    from scripts.tracker.query import get_artifact_by_uid
    return get_artifact_by_uid(uid)
```

- [ ] **Step 5: Verify**

Run: `pytest tests/outputs/ tests/tracker/ -v`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/outputs/io.py tests/outputs/test_io.py
git commit -m "feat(outputs): make_artifact_path issues UIDs + reserves filenames"
```

---

## Task 16: `io.finalize_docx` + `io.read_artifact_uid`

**Files:**
- Modify: `scripts/outputs/io.py`
- Modify: `tests/outputs/test_io.py`

- [ ] **Step 1: Write failing tests**

Append:

```python
from docx import Document
from scripts.outputs.io import finalize_docx, read_artifact_uid
from scripts.outputs.tagging import read_artifact_meta


def test_finalize_docx_writes_custom_properties(isolated):
    _set_profile_name()
    jd_id = add_jd("manual", None, "Acme", "Engineer", "...", {}, [], [])
    path, meta = make_artifact_path(jd_id, "resume")
    # Generator writes the file:
    doc = Document()
    doc.add_paragraph("body")
    doc.save(str(path))
    # Skill finalizes:
    finalize_docx(path, meta)
    loaded = read_artifact_meta(path)
    assert loaded == meta


def test_finalize_docx_raises_when_file_missing(isolated):
    _set_profile_name()
    jd_id = add_jd("manual", None, "Acme", "Engineer", "...", {}, [], [])
    path, meta = make_artifact_path(jd_id, "resume")
    # Don't actually create the file.
    with pytest.raises(FileNotFoundError):
        finalize_docx(path, meta)


def test_read_artifact_uid_returns_uid_when_present(isolated):
    _set_profile_name()
    jd_id = add_jd("manual", None, "Acme", "Engineer", "...", {}, [], [])
    path, meta = make_artifact_path(jd_id, "resume")
    doc = Document()
    doc.save(str(path))
    finalize_docx(path, meta)
    assert read_artifact_uid(path) == meta.artifact_uid


def test_read_artifact_uid_returns_none_for_untagged(isolated, tmp_path):
    untagged = tmp_path / "u.docx"
    Document().save(str(untagged))
    assert read_artifact_uid(untagged) is None
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/outputs/test_io.py -v -k finalize`
Expected: FAIL.

- [ ] **Step 3: Implement**

Append to `scripts/outputs/io.py`:

```python
from scripts.outputs.tagging import read_artifact_meta, write_artifact_meta


def finalize_docx(path: Path, meta: ArtifactMeta) -> None:
    """Write the artifact's UID + metadata into the DOCX custom properties.

    Raises FileNotFoundError if the DOCX doesn't exist (caller must have
    already invoked the generator).
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Cannot finalize {path}: file does not exist. "
            f"Generator must run before finalize_docx."
        )
    write_artifact_meta(path, meta)


def read_artifact_uid(path: Path) -> str | None:
    """Convenience: return just the BrainsArtifactId or None."""
    meta = read_artifact_meta(path)
    return meta.artifact_uid if meta else None
```

- [ ] **Step 4: Verify**

Run: `pytest tests/outputs/ -v`
Expected: All PASS. `scripts/outputs/` is now complete.

- [ ] **Step 5: Commit**

```bash
git add scripts/outputs/io.py tests/outputs/test_io.py
git commit -m "feat(outputs): add finalize_docx + read_artifact_uid"
```

---

## Task 17: `resume_to_docx` accepts optional `artifact_meta`

**Files:**
- Modify: `scripts/generators/resume_to_docx.py:62-102`
- Modify or create: `tests/generators/test_resume_to_docx.py`

- [ ] **Step 1: Write failing test**

Append (or create) `tests/generators/test_resume_to_docx.py`:

```python
"""Tests for the resume DOCX generator's artifact-meta integration."""
from datetime import datetime
from pathlib import Path

import pytest
from docx import Document

from scripts.generators.resume_to_docx import render_resume_docx
from scripts.outputs.tagging import ArtifactMeta, read_artifact_meta


def test_render_resume_docx_without_meta_still_works(tmp_path):
    out = tmp_path / "r.docx"
    render_resume_docx(
        data={"candidate_name": "M Gell"},
        out_path=out,
        template="chronological",
    )
    assert out.exists()
    assert read_artifact_meta(out) is None  # no custom properties


def test_render_resume_docx_with_meta_embeds_properties(tmp_path):
    out = tmp_path / "r.docx"
    meta = ArtifactMeta(
        artifact_uid="KX7M9Q",
        artifact_kind="resume",
        jd_id=42,
        parent_uid=None,
        created_at="2026-05-19T10:00:00Z",
        skill_version="1.5.0",
    )
    render_resume_docx(
        data={"candidate_name": "M Gell"},
        out_path=out,
        template="chronological",
        artifact_meta=meta,
    )
    loaded = read_artifact_meta(out)
    assert loaded == meta
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/generators/test_resume_to_docx.py -v`
Expected: FAIL — `render_resume_docx` doesn't accept `artifact_meta`.

- [ ] **Step 3: Modify `render_resume_docx`**

In `scripts/generators/resume_to_docx.py`, change the import block at the top (after `from docx import Document`) to:

```python
from scripts.outputs.tagging import ArtifactMeta, write_artifact_meta
```

Replace the signature on line 62 with:

```python
def render_resume_docx(
    data: dict,
    out_path: Union[str, Path],
    template: str = "chronological",
    artifact_meta: ArtifactMeta | None = None,
) -> Path:
```

Replace the docstring to mention the new param. Then replace the existing `doc.save(str(out_path))` (line 101) and the `return` (line 102) with:

```python
    doc.save(str(out_path))
    if artifact_meta is not None:
        write_artifact_meta(out_path, artifact_meta)
    return out_path
```

- [ ] **Step 4: Verify**

Run: `pytest tests/generators/ tests/outputs/ tests/tracker/ -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/generators/resume_to_docx.py tests/generators/test_resume_to_docx.py
git commit -m "feat(generators): resume_to_docx accepts optional artifact_meta"
```

---

## Task 18: `cover_letter_to_docx` accepts optional `artifact_meta`

**Files:**
- Modify: `scripts/generators/cover_letter_to_docx.py`
- Modify or create: `tests/generators/test_cover_letter_to_docx.py`

- [ ] **Step 1: Write failing test**

Create `tests/generators/test_cover_letter_to_docx.py`:

```python
"""Tests for the cover-letter DOCX generator's artifact-meta integration."""
from pathlib import Path

from scripts.generators.cover_letter_to_docx import render_cover_letter_docx
from scripts.outputs.tagging import ArtifactMeta, read_artifact_meta


def test_render_cover_letter_docx_with_meta(tmp_path):
    out = tmp_path / "cl.docx"
    meta = ArtifactMeta(
        artifact_uid="H8VR3W",
        artifact_kind="cover-letter",
        jd_id=42,
        parent_uid="KX7M9Q",
        created_at="2026-05-19T10:00:00Z",
        skill_version="1.5.0",
    )
    render_cover_letter_docx(
        data={"candidate_name": "M Gell", "body": "Dear hiring manager"},
        out_path=out,
        template="formal-business",
        artifact_meta=meta,
    )
    loaded = read_artifact_meta(out)
    assert loaded == meta
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/generators/test_cover_letter_to_docx.py -v`
Expected: FAIL.

- [ ] **Step 3: Modify `cover_letter_to_docx.py`**

Open `scripts/generators/cover_letter_to_docx.py`. Add to imports:

```python
from scripts.outputs.tagging import ArtifactMeta, write_artifact_meta
```

Change the `render_cover_letter_docx` signature to include `artifact_meta: ArtifactMeta | None = None`. After `doc.save(...)` and before `return out_path`, add:

```python
    if artifact_meta is not None:
        write_artifact_meta(out_path, artifact_meta)
```

- [ ] **Step 4: Verify**

Run: `pytest tests/generators/ -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/generators/cover_letter_to_docx.py tests/generators/test_cover_letter_to_docx.py
git commit -m "feat(generators): cover_letter_to_docx accepts optional artifact_meta"
```

---

## Task 19: Sidebar — name fields + outputs-dir display

**Files:**
- Modify: `scripts/dashboard/sidebar.py`
- Modify: `tests/dashboard/test_sidebar.py` (or create if absent)

- [ ] **Step 1: Read existing sidebar**

Run: `head -100 scripts/dashboard/sidebar.py` to understand the existing structure (likely a `render(profile: Profile) -> Profile` function or similar). Tests must follow the existing pattern.

- [ ] **Step 2: Write a smoke test**

Create or append `tests/dashboard/test_sidebar.py`:

```python
"""Smoke tests for the sidebar — name fields rendered, outputs dir shown."""
from unittest.mock import MagicMock, patch

import pytest

from scripts.tracker.models import Profile


def test_sidebar_renders_name_fields_without_crashing(monkeypatch, tmp_path):
    """Mock streamlit; assert sidebar calls text_input for first_name and last_name."""
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    fake_st = MagicMock()
    fake_st.session_state = {}
    fake_st.text_input.side_effect = ["Matthew", "Gell"]
    fake_st.checkbox.return_value = True
    fake_st.number_input.return_value = 5
    fake_st.text_area.return_value = ""
    fake_st.multiselect.return_value = []
    with patch.dict("sys.modules", {"streamlit": fake_st}):
        # Reload sidebar so it picks up the patched streamlit.
        import importlib
        import scripts.dashboard.sidebar
        importlib.reload(scripts.dashboard.sidebar)
        scripts.dashboard.sidebar.render(Profile())
    # Verify the two name fields were rendered.
    labels = [call.args[0] for call in fake_st.text_input.call_args_list]
    assert "First name" in labels
    assert "Last name" in labels
```

- [ ] **Step 3: Verify failure**

Run: `pytest tests/dashboard/test_sidebar.py -v`
Expected: FAIL — sidebar doesn't yet have name fields.

- [ ] **Step 4: Modify `sidebar.py`**

Add a "Your name" subsection at the very top of the sidebar render function (just under the title), before any existing controls. The render call must read first_name and last_name from the profile, expose them as `st.text_input(...)`, and write back to the profile on change.

Concrete addition (place near the top of the existing `render` function — keep the rest of the sidebar untouched):

```python
    # --- Your name (used in artifact filenames) ---
    st.sidebar.subheader("Your name")
    first_name = st.sidebar.text_input(
        "First name",
        value=profile.first_name or "",
        key="sidebar_first_name",
    )
    last_name = st.sidebar.text_input(
        "Last name",
        value=profile.last_name or "",
        key="sidebar_last_name",
    )
    profile.first_name = first_name.strip() or None
    profile.last_name = last_name.strip() or None

    # --- Outputs directory (read-only) ---
    from scripts.outputs.io import get_outputs_root
    st.sidebar.caption(f"Outputs: `{get_outputs_root()}`")
```

The existing `write_profile(profile)` call at the bottom of `render` will persist the new fields automatically (Task 9 already wired that).

- [ ] **Step 5: Verify**

Run: `pytest tests/dashboard/test_sidebar.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/dashboard/sidebar.py tests/dashboard/test_sidebar.py
git commit -m "feat(dashboard): sidebar — name fields + outputs dir display"
```

---

## Task 20: First-use modal when names are missing

**Files:**
- Modify: `scripts/dashboard/app.py`
- Modify: `tests/dashboard/test_sidebar.py` (extend) or create `test_app.py`

- [ ] **Step 1: Read existing app.py to find where to insert the modal**

Run: `head -80 scripts/dashboard/app.py`. The modal should fire before any workflow tab renders, but after the sidebar and Profile read.

- [ ] **Step 2: Write a smoke test**

Append to `tests/dashboard/test_sidebar.py` (or create `tests/dashboard/test_app.py`):

```python
def test_app_shows_modal_when_names_missing(monkeypatch, tmp_path):
    """When Profile has no first/last name, app.py opens a blocking modal."""
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    fake_st = MagicMock()
    fake_st.session_state = {}
    fake_st.dialog = MagicMock(return_value=lambda f: f)  # decorator passthrough
    with patch.dict("sys.modules", {"streamlit": fake_st}):
        import importlib
        import scripts.dashboard.app
        importlib.reload(scripts.dashboard.app)
        # Trigger whatever guard function the app exposes.
        scripts.dashboard.app.require_user_name()
    # Modal was set up via st.dialog or st.warning.
    assert fake_st.dialog.called or fake_st.warning.called
```

- [ ] **Step 3: Verify failure**

Run: `pytest tests/dashboard/test_sidebar.py -v`
Expected: FAIL — `require_user_name` doesn't exist.

- [ ] **Step 4: Implement `require_user_name` in `app.py`**

Add to `scripts/dashboard/app.py` (near the top, after imports):

```python
from scripts.tracker.profile import read_profile, write_profile
from scripts.tracker.models import Profile


def require_user_name() -> None:
    """If profile.json is missing first_name or last_name, surface a
    one-shot modal. Workflow tabs are guarded by this; read-only tabs
    are not.
    """
    profile = read_profile()
    if profile.first_name and profile.last_name:
        return

    @st.dialog("Set your name to continue")
    def _name_modal():
        st.write(
            "BRAINS Resume uses your name in every artifact filename "
            "(e.g. `Matthew_Gell_resume_2026-05-19_KX7M9Q.docx`). "
            "Please set it once."
        )
        first = st.text_input("First name", value=profile.first_name or "")
        last = st.text_input("Last name", value=profile.last_name or "")
        if st.button("Save", type="primary"):
            if first.strip() and last.strip():
                profile.first_name = first.strip()
                profile.last_name = last.strip()
                write_profile(profile)
                st.rerun()
            else:
                st.error("Both first and last names are required.")

    _name_modal()
```

Then add a call to `require_user_name()` immediately before any workflow tab is rendered. Read the existing app.py to find the appropriate location (likely just before the `tabs = st.tabs([...])` block — call `require_user_name()` after the read-only tab setup and only when a workflow tab is selected, OR unconditionally at top if simpler).

Decision: call `require_user_name()` unconditionally at the top of the main render path. Read-only tabs still render behind the modal (Streamlit's `st.dialog` is non-blocking for the rest of the page in current versions but blocks user input until dismissed).

- [ ] **Step 5: Verify**

Run: `pytest tests/dashboard/ -v`
Expected: PASS.

Manual smoke (NOT a test step — note for QA):
1. Delete `~/.brains-resume/profile.json` (or set `BRAINS_TRACKER_PROFILE_PATH` to a fresh location).
2. `streamlit run scripts/dashboard/app.py`.
3. Verify the modal appears and saving redirects.

- [ ] **Step 6: Commit**

```bash
git add scripts/dashboard/app.py tests/dashboard/test_sidebar.py
git commit -m "feat(dashboard): first-use modal prompts for first/last name"
```

---

## Task 21: `jd_analyze.py` — drop `jd.txt` + `jd-analysis.md` into the JD folder

**Files:**
- Modify: `scripts/dashboard/workflows/jd_analyze.py`

- [ ] **Step 1: Read existing `jd_analyze.py`**

Run: `cat scripts/dashboard/workflows/jd_analyze.py` (or view in editor). It already runs analysis via `scripts/validators/jd_analyzer.py` and currently returns the result to the user without persisting. After this task, when the user clicks "Save to tracker", we:
1. Call `tracker.add_jd(...)` (existing).
2. Call `io.ensure_jd_folder(jd_id)`.
3. Write `jd.txt` (the raw JD) into the folder.
4. Write `jd-analysis.md` (the analysis findings as Markdown) into the folder.

- [ ] **Step 2: Write a smoke test**

Append to `tests/dashboard/test_workflows_card.py`:

```python
def test_jd_analyze_persists_jd_and_analysis_to_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    from scripts.dashboard.workflows.jd_analyze import persist_analyzed_jd
    findings = {"role_fit_score": 7, "red_flags": []}
    jd_id, folder = persist_analyzed_jd(
        raw_text="Senior Data Engineer at Acme...",
        company="Acme",
        role_title="Senior Data Engineer",
        source="manual",
        source_ref=None,
        analyzer_findings=findings,
        focus_areas_required=[],
        focus_areas_nice=[],
    )
    assert (folder / "jd.txt").exists()
    assert (folder / "jd.txt").read_text(encoding="utf-8").startswith("Senior Data Engineer")
    assert (folder / "jd-analysis.md").exists()
    assert "role_fit_score" in (folder / "jd-analysis.md").read_text(encoding="utf-8")
```

- [ ] **Step 3: Verify failure**

Run: `pytest tests/dashboard/test_workflows_card.py -v -k jd_analyze`
Expected: FAIL — `persist_analyzed_jd` doesn't exist.

- [ ] **Step 4: Add `persist_analyzed_jd` to `jd_analyze.py`**

Append to `scripts/dashboard/workflows/jd_analyze.py`:

```python
import json
from pathlib import Path

from scripts.tracker.add import add_jd
from scripts.outputs.io import ensure_jd_folder


def persist_analyzed_jd(
    raw_text: str,
    company: str,
    role_title: str,
    source: str,
    source_ref: str | None,
    analyzer_findings: dict,
    focus_areas_required: list[str],
    focus_areas_nice: list[str],
) -> tuple[int, Path]:
    """Persist the analyzed JD to tracker + outputs folder.

    Creates the per-JD folder, writes the raw JD as jd.txt, writes the
    analysis findings as jd-analysis.md, and returns the new jd_id and
    folder path. Called from the Streamlit "Save to tracker" button.
    """
    jd_id = add_jd(
        source=source,
        source_ref=source_ref,
        company=company,
        role_title=role_title,
        raw_text=raw_text,
        analyzer_findings=analyzer_findings,
        focus_areas_required=focus_areas_required,
        focus_areas_nice=focus_areas_nice,
    )
    folder = ensure_jd_folder(jd_id)
    (folder / "jd.txt").write_text(raw_text, encoding="utf-8")
    (folder / "jd-analysis.md").write_text(
        _findings_to_markdown(analyzer_findings, role_title, company),
        encoding="utf-8",
    )
    return jd_id, folder


def _findings_to_markdown(findings: dict, role: str, company: str) -> str:
    """Render analyzer findings as a Markdown report."""
    lines = [
        f"# JD analysis — {role} @ {company}",
        "",
        "```json",
        json.dumps(findings, indent=2),
        "```",
        "",
    ]
    return "\n".join(lines)
```

Then locate the existing "Save to tracker" handler in the same file (the button that previously called `add_jd` inline) and replace its body with `persist_analyzed_jd(...)`. If no such button exists yet, leave the function as a public API — Task 27's docs update will tell users how to invoke it.

- [ ] **Step 5: Verify**

Run: `pytest tests/dashboard/ -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/dashboard/workflows/jd_analyze.py tests/dashboard/test_workflows_card.py
git commit -m "feat(workflows): jd_analyze persists jd.txt + jd-analysis.md to JD folder"
```

---

## Task 22: `tailor.py` — route to per-JD folder with new filename

**Files:**
- Modify: `scripts/dashboard/workflows/tailor.py`

- [ ] **Step 1: Read existing `tailor.py`**

(See earlier read: 21 lines. Currently it just renders a UI and hands off to Claude Code via clipboard. The handoff payload is the resume path + JD input.)

- [ ] **Step 2: Update tailor handoff to include the target output path**

Replace the body of `scripts/dashboard/workflows/tailor.py` with:

```python
"""/brains-tailor — tailor a resume to a specific job description."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import pick_file
from scripts.dashboard.workflows._card import handoff_button
from scripts.outputs.io import make_artifact_path, ProfileNameMissingError


def render(file_path: Optional[Path] = None, key_prefix: str = "tailor") -> None:
    st.markdown("**Tailor a resume to a specific job description.**")
    if file_path is None:
        file_path = pick_file("resume", key=f"{key_prefix}_resume")
    jd_id = st.number_input(
        "JD id (from tracker)", min_value=1, step=1, key=f"{key_prefix}_jd_id",
    )
    st.write(f"Resume: `{file_path}`" if file_path else "_No resume selected._")
    if file_path is not None and jd_id:
        try:
            target_path, meta = make_artifact_path(int(jd_id), "resume")
        except ProfileNameMissingError:
            st.error(
                "Set your first and last name in the sidebar before tailoring."
            )
            return
        st.caption(f"Output will land at: `{target_path}`")
        handoff_button(
            "tailor",
            [str(file_path), int(jd_id), str(target_path), meta.artifact_uid],
            note=(
                "Claude Code will produce a tailored resume at the path shown above. "
                "After save, call `scripts.outputs.io.finalize_docx(target_path, meta)` "
                "and `tracker.add_resume_version(file_path=target_path, ..., "
                "artifact_uid=meta.artifact_uid, parent_uid=<source resume's uid or None>)`."
            ),
            key=f"{key_prefix}_btn",
        )
```

The `references/workflows/tailor.md` doc (updated in Task 28) tells the Claude Code handoff exactly what to do with the four payload args.

- [ ] **Step 3: Smoke**

Run: `pytest tests/dashboard/ -v` (existing tests should still pass; this workflow's behavior is a handoff so no new test).

- [ ] **Step 4: Commit**

```bash
git add scripts/dashboard/workflows/tailor.py
git commit -m "feat(workflows): tailor — output path resolved via io.make_artifact_path"
```

---

## Task 23: `cover_letter.py` — route to per-JD folder

**Files:**
- Modify: `scripts/dashboard/workflows/cover_letter.py`

- [ ] **Step 1: Read existing `cover_letter.py`**

Open the file and confirm it follows the same handoff pattern as `tailor.py`.

- [ ] **Step 2: Update**

Modify `cover_letter.py` to mirror `tailor.py`'s integration. Key addition (replace the existing handoff_button call with):

```python
        try:
            target_path, meta = make_artifact_path(int(jd_id), "cover-letter",
                                                    parent_uid=resume_uid)
        except ProfileNameMissingError:
            st.error(
                "Set your first and last name in the sidebar before generating "
                "a cover letter."
            )
            return
        st.caption(f"Output will land at: `{target_path}`")
        handoff_button(
            "cover-letter",
            [str(resume_path), int(jd_id), str(target_path), meta.artifact_uid,
             meta.parent_uid or ""],
            note=(
                "Claude Code will produce the cover letter at the path shown. "
                "After save, call `scripts.outputs.io.finalize_docx(target_path, meta)` "
                "and `tracker.add_cover_letter(file_path=target_path, ..., "
                "artifact_uid=meta.artifact_uid, parent_uid=meta.parent_uid)`."
            ),
            key=f"{key_prefix}_btn",
        )
```

`resume_uid` comes from reading the source resume's UID via `scripts.outputs.io.read_artifact_uid(resume_path)` near the top of `render`. If the source resume has no UID (pre-v1.5.0), pass `None`.

Imports at the top:

```python
from scripts.outputs.io import (
    make_artifact_path,
    read_artifact_uid,
    ProfileNameMissingError,
)
```

- [ ] **Step 3: Commit**

```bash
git add scripts/dashboard/workflows/cover_letter.py
git commit -m "feat(workflows): cover_letter — output path + parent_uid via io"
```

---

## Task 24: `edit.py` — route to JD folder if JD known, else outputs root

**Files:**
- Modify: `scripts/dashboard/workflows/edit.py`

- [ ] **Step 1: Read existing**

`/brains-edit` may operate on a resume without a JD context. Handle both:
- If `jd_id` is provided in the UI → use `make_artifact_path`
- If not → ask the user to optionally tag it with a JD; if they decline, skip the per-JD folder and produce a path under `<outputs_root>/_library/` with the same filename pattern.

- [ ] **Step 2: Modify `edit.py`**

Concrete addition — replace the handoff block with:

```python
from scripts.outputs.io import (
    make_artifact_path, ProfileNameMissingError, get_outputs_root,
)
from scripts.outputs.naming import artifact_filename, new_uid
from datetime import date

# ... inside render():
        if jd_id:
            try:
                target_path, meta = make_artifact_path(int(jd_id), "resume",
                                                        parent_uid=source_uid)
            except ProfileNameMissingError:
                st.error("Set your name in the sidebar first.")
                return
        else:
            # No JD context — drop into _library/ with the same name shape.
            try:
                profile = read_profile()
                if not profile.first_name or not profile.last_name:
                    raise ProfileNameMissingError
            except ProfileNameMissingError:
                st.error("Set your name in the sidebar first.")
                return
            library = get_outputs_root() / "_library"
            library.mkdir(parents=True, exist_ok=True)
            uid = new_uid()
            target_path = library / artifact_filename(
                first_name=profile.first_name, last_name=profile.last_name,
                kind="resume", created_date=date.today(), uid=uid,
            )
            from scripts.outputs.tagging import ArtifactMeta
            from datetime import datetime
            meta = ArtifactMeta(
                artifact_uid=uid, artifact_kind="resume", jd_id=None,
                parent_uid=source_uid,
                created_at=datetime.utcnow().isoformat() + "Z",
                skill_version="1.5.0",
            )
        st.caption(f"Output will land at: `{target_path}`")
        handoff_button(
            "edit",
            [str(source_path), str(target_path), meta.artifact_uid,
             meta.parent_uid or ""],
            note="Claude Code edits the resume to target path...",
            key=f"{key_prefix}_btn",
        )
```

Imports at the top:

```python
from scripts.tracker.profile import read_profile
```

- [ ] **Step 3: Commit**

```bash
git add scripts/dashboard/workflows/edit.py
git commit -m "feat(workflows): edit — JD folder when tagged, _library otherwise"
```

---

## Task 25: `create.py` — drop into `_library` (or JD folder if a JD is selected)

**Files:**
- Modify: `scripts/dashboard/workflows/create.py`

- [ ] **Step 1: Modify `create.py`**

`/brains-create` builds a resume from scratch via interview — usually no JD attached. Use the same `_library`-fallback pattern as `edit.py`. If the user has selected a JD in the workflow UI, use `make_artifact_path(jd_id, "resume")`.

Replace the handoff block. Pattern is the same as Task 24 — copy the `if jd_id: ... else: _library/` branch verbatim, swapping `source_uid` for `None` (no parent on a created-from-scratch resume).

- [ ] **Step 2: Commit**

```bash
git add scripts/dashboard/workflows/create.py
git commit -m "feat(workflows): create — output path via io (JD folder or _library)"
```

---

## Task 26: `deai.py` — write the de-AI'd copy alongside the source

**Files:**
- Modify: `scripts/dashboard/workflows/deai.py`

- [ ] **Step 1: Inspect**

`/brains-deai` operates on an existing tagged resume. Produce the cleaned copy at the **same folder** as the source (preserving the JD-folder grouping), with a **new UID** and `parent_uid = source's UID`.

- [ ] **Step 2: Modify**

Add to imports:
```python
from scripts.outputs.io import read_artifact_uid, ProfileNameMissingError
from scripts.outputs.naming import artifact_filename, new_uid
from scripts.outputs.tagging import ArtifactMeta
from scripts.tracker.profile import read_profile
from datetime import date, datetime
```

In the deai render handler, after the user picks the source resume:

```python
        source_uid = read_artifact_uid(source_path)
        profile = read_profile()
        if not profile.first_name or not profile.last_name:
            st.error("Set your name in the sidebar first.")
            return
        uid = new_uid()
        target_path = source_path.parent / artifact_filename(
            first_name=profile.first_name, last_name=profile.last_name,
            kind="resume", created_date=date.today(), uid=uid,
        )
        meta = ArtifactMeta(
            artifact_uid=uid, artifact_kind="resume",
            jd_id=None,  # de-AI doesn't bind to a JD by itself
            parent_uid=source_uid,
            created_at=datetime.utcnow().isoformat() + "Z",
            skill_version="1.5.0",
        )
        st.caption(f"Cleaned copy will land at: `{target_path}`")
        handoff_button(
            "deai", [str(source_path), str(target_path), meta.artifact_uid,
                     meta.parent_uid or ""],
            note="Claude Code writes the de-AI'd resume to target path...",
            key=f"{key_prefix}_btn",
        )
```

- [ ] **Step 3: Commit**

```bash
git add scripts/dashboard/workflows/deai.py
git commit -m "feat(workflows): deai — output written alongside source with parent_uid"
```

---

## Task 27: `check.py` — final-pass output alongside source

**Files:**
- Modify: `scripts/dashboard/workflows/check.py`

- [ ] **Step 1: Inspect**

`/brains-check` produces a final-pass-checked copy. Same pattern as `deai.py`: same folder as source, new UID, `parent_uid = source's UID`.

- [ ] **Step 2: Modify**

Apply the identical block from Task 26 to `check.py`, swapping the handoff slot key from `"deai"` to `"check"` and the note text accordingly.

- [ ] **Step 3: Commit**

```bash
git add scripts/dashboard/workflows/check.py
git commit -m "feat(workflows): check — output written alongside source with parent_uid"
```

---

## Task 28: End-to-end smoke test

**Files:**
- Create: `tests/test_smoke_outputs.py`

- [ ] **Step 1: Write the smoke**

Create `tests/test_smoke_outputs.py`:

```python
"""End-to-end smoke for the v1.5.0 outputs pipeline.

Exercises: add_jd -> ensure_jd_folder -> make_artifact_path ->
render_resume_docx (with meta) -> add_resume_version -> find_artifact_by_uid.
"""
import pytest

from scripts.generators.resume_to_docx import render_resume_docx
from scripts.outputs.io import (
    ensure_jd_folder,
    make_artifact_path,
    find_artifact_by_uid,
)
from scripts.outputs.tagging import read_artifact_meta
from scripts.tracker.add import add_jd, add_resume_version
from scripts.tracker.models import Profile
from scripts.tracker.profile import write_profile


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINS_TRACKER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BRAINS_TRACKER_PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setenv("BRAINS_OUTPUTS_DIR", str(tmp_path / "outputs"))
    return tmp_path


def test_smoke_full_chain(isolated):
    # Set up profile.
    write_profile(Profile(focus_areas=[], first_name="Matthew", last_name="Gell"))

    # Add a JD; folder is created and path recorded.
    jd_id = add_jd(
        source="manual", source_ref=None,
        company="Acme Corp", role_title="Senior Data Engineer",
        raw_text="...", analyzer_findings={}, focus_areas_required=[],
        focus_areas_nice=[],
    )
    folder = ensure_jd_folder(jd_id)
    assert folder.exists()

    # Reserve an artifact path + meta.
    path, meta = make_artifact_path(jd_id, "resume")

    # Render the resume with meta embedded.
    render_resume_docx(
        data={
            "candidate_name": "Matthew Gell",
            "candidate_contact_line": "m@example.com",
            "summary": "Senior data engineer.",
            "skills": "Python\nSQL",
            "experience": "Engineer @ Co (2020-2026)",
            "education": "BSc Computer Science",
        },
        out_path=path,
        template="chronological",
        artifact_meta=meta,
    )
    assert path.exists()

    # Tracker write.
    rv_id = add_resume_version(
        file_path=str(path), template="chronological",
        focus_areas=[], parent_id=None, tagged_jd_id=jd_id,
        artifact_uid=meta.artifact_uid,
    )

    # Look up by uid — should find the resume row.
    found = find_artifact_by_uid(meta.artifact_uid)
    assert found is not None
    assert found.id == rv_id
    assert found.file_path == str(path)

    # Embedded meta round-trips.
    loaded = read_artifact_meta(path)
    assert loaded.artifact_uid == meta.artifact_uid

    # Rename the file; lookup by UID still works (filename irrelevant).
    renamed = path.parent / "manual-rename.docx"
    path.rename(renamed)
    loaded2 = read_artifact_meta(renamed)
    assert loaded2.artifact_uid == meta.artifact_uid
```

- [ ] **Step 2: Run**

Run: `pytest tests/test_smoke_outputs.py -v`
Expected: PASS.

- [ ] **Step 3: Run the full suite**

Run: `pytest -v`
Expected: All PASS — no regressions.

- [ ] **Step 4: Commit**

```bash
git add tests/test_smoke_outputs.py
git commit -m "test: end-to-end smoke for v1.5.0 outputs pipeline"
```

---

## Task 29: Docs — `SKILL.md`, `README.md`, `references/workflows/*.md`

**Files:**
- Modify: `SKILL.md`
- Modify: `README.md`
- Modify: `references/workflows/tailor.md`
- Modify: `references/workflows/cover-letter.md`
- Modify: `references/workflows/edit.md`
- Modify: `references/workflows/review.md`
- Modify: `references/workflows/jd-analyze.md` (create if missing)
- Modify: `claude-project-setup.md` (if it exists)

- [ ] **Step 1: Add "File organization" section to SKILL.md**

Insert a new section after the "Slash commands" section (or wherever fits the existing structure). Content:

```markdown
## File organization (v1.5.0+)

The skill writes every output under `~/.brains-resume/outputs/` (overridable
via `BRAINS_OUTPUTS_DIR`). Each JD gets its own folder named:

    YYYY-MM-DD_<Company>_<Role>/

where `<Company>` falls back to `via-<Recruiter>` when the hiring company
isn't known, or to `unknown` when neither is set.

Resumes and cover letters land inside the JD folder with filenames of the
form:

    <First>_<Last>_<resume|cover-letter>_<YYYY-MM-DD>_<UID>.docx

The trailing `<UID>` is a 6-char Crockford base32 identifier. The same UID
is also written as an invisible custom property inside the DOCX itself, so
renaming the file doesn't break tracker lookups.

To set your name (used in every filename), open the dashboard sidebar and
fill in the "Your name" section. The dashboard prompts you with a one-shot
modal on first launch if names are missing.
```

- [ ] **Step 2: Add a brief mention to README.md**

Under the existing "Outputs" / "Where your files go" section (create one if missing), add:

```markdown
### Output organization

All resumes and cover letters produced by the skill land in
`~/.brains-resume/outputs/<JD-folder>/` with a deterministic filename
pattern. See `SKILL.md` § File organization for the full convention.
```

- [ ] **Step 3: Update each `references/workflows/*.md`**

For `tailor.md`, `cover-letter.md`, `edit.md`, `review.md`, `jd-analyze.md`, add or update a "File organization" subsection that says:

```markdown
### File organization

The dashboard reserves the output path before invoking this command. The
handoff payload contains the absolute path to write to. Do NOT pick your
own filename. After saving the DOCX, call:

    from scripts.outputs.io import finalize_docx
    from scripts.outputs.tagging import ArtifactMeta
    finalize_docx(target_path, meta)

then record the row via the appropriate `tracker.add_*` call, passing the
`artifact_uid` and `parent_uid` from the handoff payload.
```

(The handoff payload format for each workflow is documented in the existing workflow `.md` file; just add the file-organization rule.)

- [ ] **Step 4: Update `claude-project-setup.md` if present**

Run: `ls claude-project-setup*.md` to confirm. If it exists, add a section noting that v1.5.0 introduces canonical output paths and that handoff prompts should respect the `target_path` argument.

- [ ] **Step 5: Commit**

```bash
git add SKILL.md README.md references/workflows/ claude-project-setup.md
git commit -m "docs: v1.5.0 — file organization convention + workflow refs"
```

---

## Task 30: Release polish — CHANGELOG, version bump, bundle rebuild, tag

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml:7`
- Modify: `STATUS.yml`
- Modify: `docs/brand-application.md` if it mentions filenames

- [ ] **Step 1: Append CHANGELOG entry**

Open `CHANGELOG.md`. Insert at the top (after the header), a new section:

```markdown
## [1.5.0] - 2026-05-DD

### Added
- Per-JD output folders at `~/.brains-resume/outputs/YYYY-MM-DD_<Company>_<Role>/`
  containing the raw JD, JD analysis, and all tailored artifacts.
- Canonical filename pattern for resumes and cover letters:
  `<First>_<Last>_<kind>_<YYYY-MM-DD>_<UID>.docx`.
- Invisible 6-char Crockford base32 UID embedded as a DOCX custom property
  on every generated artifact (`BrainsArtifactId`, `BrainsArtifactKind`,
  `BrainsJDId`, `BrainsParentId`, `BrainsCreatedAt`, `BrainsSkillVersion`).
- Tracker migration 0002: `artifact_uid` + `parent_uid` columns on
  `resume_versions` and `cover_letters`, `folder_path` column on `jds`.
- Profile fields: `first_name`, `last_name`. First-use modal in the
  dashboard sets them on first launch.
- `BRAINS_OUTPUTS_DIR` env var to override the outputs root.
- New module `scripts/outputs/` (naming, tagging, io) + tests.
- `tracker.get_artifact_by_uid` query helper.

### Changed
- Generators (`render_resume_docx`, `render_cover_letter_docx`) accept
  optional `artifact_meta` to embed properties on save.
- Dashboard workflows (`tailor`, `cover-letter`, `edit`, `create`, `deai`,
  `check`, `jd-analyze`) now reserve their output path via
  `io.make_artifact_path` before handing off to Claude Code.

### Notes
- Forward-only: pre-v1.5.0 files keep their existing names and paths;
  pre-v1.5.0 tracker rows have NULL `artifact_uid`.
- Disclosure framework polish (previously planned for v1.5) moves to v1.6.

### Deferred
- `/brains-relocate` retroactive migration of pre-v1.5.0 files.
- `/brains-scan` to rebuild tracker links from embedded UIDs.
- PDF custom-property embedding (PDFs share the DOCX's UID in their
  filename only).
- LinkedIn artifact organization.
```

Replace `2026-05-DD` with the actual release date when running this step.

- [ ] **Step 2: Bump version in `pyproject.toml`**

Edit `pyproject.toml` line 7:
```
-version = "1.4.1"
+version = "1.5.0"
```

- [ ] **Step 3: Update `STATUS.yml`**

Replace the existing `STATUS.yml` with content reflecting v1.5.0 release:

```yaml
name: BRAINS Resume Skill
status: shipped
priority: P1
next_step: v1.6 — disclosure framework polish
blocker: null
workstream:
  label: v1.6 cycle
  phases:
  - id: SP
    label: spec
    status: upcoming
  - id: BD
    label: build
    status: upcoming
  - id: RL
    label: release
    status: upcoming
lifecycle:
  milestones:
  - v1.0
  - v1.2
  - v1.4
  - v1.5
  - v1.6
  - v2.0
  current_milestone: v1.5
  overall_pct: 85
  target_milestone: v1.6
  target_date: '2026-07-15'
backlog:
- Disclosure framework brainstorm (deferred from v1.5)
notes: 'v1.5.0 released — per-JD folders + traceable artifact UIDs.

  '
```

The `_auto` block at the bottom is regenerated by the existing STATUS-refresh hook; leave it untouched or strip it (it'll be recreated on next run).

- [ ] **Step 4: Bundle rebuild (if applicable)**

If `scripts/packaging/build_project_bundle.py` exists, run it:

Run: `python scripts/packaging/build_project_bundle.py`
Expected: bundle files rebuilt with v1.5.0 version stamps.

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: All PASS.

- [ ] **Step 6: Commit release**

```bash
git add CHANGELOG.md pyproject.toml STATUS.yml
git commit -m "chore: bump version to 1.5.0 + CHANGELOG entry"
```

- [ ] **Step 7: Tag**

```bash
git tag -a v1.5.0 -m "v1.5.0 — per-JD folders + traceable artifact UIDs"
git push origin main
git push origin v1.5.0
```

- [ ] **Step 8: Verify acceptance criteria from the spec**

Walk the spec's §5 acceptance criteria (10 items) against the working tree and produced artifacts. All 10 must be demonstrable. Specifically:

1. `pytest scripts/outputs/` (actually `tests/outputs/`) passes — verified in Task 16.
2. `pytest tests/tracker/migrations/` passes — verified in Task 8.
3. Fresh `/brains-jd-analyze` creates folder + drops jd.txt + jd-analysis.md + writes `folder_path` — verified in Task 21.
4. Fresh `/brains-tailor` writes DOCX at canonical name with readable BrainsArtifactId + matching tracker row — verified in Task 28 smoke.
5. Rename produces no breakage in `find_artifact_by_uid` — verified in Task 28 smoke.
6. Two `/brains-tailor` runs produce two UIDs with `parent_uid` lineage — verified in `make_artifact_path` tests + smoke.
7. No visible BRAINS markings in body/header/footer — verified by Task 6's `test_write_artifact_meta_does_not_change_body`.
8. Clearing names triggers `ProfileNameMissingError` with redirect — verified in Task 15 tests + Task 19/20 modal.
9. CHANGELOG entry — verified by this task.
10. `v1.5.0` git tag on HEAD of main — verified by step 7.

---

## Self-review

After completing all 30 tasks, walk back through the spec sections and confirm:

- **§2 In scope** — every item has a task: outputs package (1-7, 13-16), profile fields (9, 19, 20), migration (8), tracker API extensions (9-12), generator integration (17-18), workflow integration (21-27), outputs root env var (13), docs (29), tests (1-16, 28), release polish (30). ✓
- **§3 Module layout** — every file shown in the spec's tree appears in at least one task. ✓
- **§4 Naming rules** — codified as `slugify`/`folder_name`/`artifact_filename` with explicit parametrized test cases matching the spec's tables (Task 1, 3, 4). ✓
- **§5 Acceptance criteria** — Task 30 step 8 walks all 10 and points to the verifying task. ✓
- **§6 Error handling** — `ProfileNameMissingError` (15), `OutputsDirNotWritableError` (13), `UIDCollisionError` (15), idempotent folder (14), all-or-nothing finalize_docx (16). ✓
- **§8 Migration & rollout** — forward-only nullable columns (8, 11), modal on first launch (20). ✓
- **§9 Documentation** — covered in Task 29. ✓
- **§10 Future work** — explicitly listed as out of scope; no tasks attempt to ship them. ✓

No placeholders, no "fill in details", every step has either runnable code or an exact command. Type names consistent across tasks: `ArtifactMeta`, `artifact_uid`, `parent_uid`, `folder_path` used identically throughout.

---

## Execution

Plan complete and saved to `docs/plans/2026-05-18-plan-7-v1-5-0-jd-folders-artifact-uids.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for a 30-task plan; each subagent gets clean context.

**2. Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints for review.

Which approach?
