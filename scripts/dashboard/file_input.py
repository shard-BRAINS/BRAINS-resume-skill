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
    paths: set[str] = set()
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
        paths.update(r for r in rows if r)
    except Exception:
        pass

    upload_dir = UPLOAD_ROOT / kind
    if upload_dir.exists():
        for p in upload_dir.iterdir():
            if p.is_file() and p.suffix.lower() in (".docx", ".pdf", ".zip"):
                paths.add(str(p))

    return sorted(paths)


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
