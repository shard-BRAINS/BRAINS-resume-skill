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
