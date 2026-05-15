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
