"""/brains-career-change — translate experience for a pivot."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import pick_file
from scripts.dashboard.workflows._card import handoff_button


def render(file_path: Optional[Path] = None, key_prefix: str = "career_change") -> None:
    st.markdown("**Translate experience from one domain into another for a career pivot.**")
    if file_path is None:
        file_path = pick_file("resume", key=f"{key_prefix}_pick")
    st.write(f"Selected: `{file_path}`" if file_path else "_No file selected._")
    if file_path is not None:
        handoff_button("career-change", [file_path], note="Claude Code will rewrite your experience around your pivot target.", key=f"{key_prefix}_btn")
