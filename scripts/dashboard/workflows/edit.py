"""/brains-edit — apply review fixes to a resume."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import pick_file
from scripts.dashboard.workflows._card import handoff_button


def render(file_path: Optional[Path] = None, key_prefix: str = "edit") -> None:
    st.markdown("**Apply review fixes to a resume.**")
    st.caption("Hands the resume + the most recent review findings off to Claude Code for a clean ATS-safe rewrite.")
    if file_path is None:
        file_path = pick_file("resume", key=f"{key_prefix}_pick")
    st.write(f"Selected: `{file_path}`" if file_path else "_No file selected._")
    if file_path is not None:
        handoff_button("edit", [file_path], note="Claude Code will load the resume and apply review findings.", key=f"{key_prefix}_btn")
