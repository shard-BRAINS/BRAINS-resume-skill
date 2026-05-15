"""/brains-consolidate — handoff to Claude Code for resume↔LinkedIn diff.

Structural diff parsing (DOCX/ZIP → position dicts) is not available natively in
the dashboard. The diff itself runs in the LLM workflow; this surface just
collects the two file paths and copies the slash command to the clipboard.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import pick_file
from scripts.dashboard.workflows._card import handoff_button


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Detect inconsistencies between a resume and a LinkedIn profile.**")
    st.caption("The diff runs in Claude Code (the parsers live there). Pick both files here, then copy the handoff command.")

    resume_path = file_path or pick_file("resume", key="cons_resume")
    linkedin_path_str = st.text_input("LinkedIn export DOCX or ZIP path", key="cons_linkedin")
    linkedin_path = Path(linkedin_path_str) if linkedin_path_str else None

    if linkedin_path_str and (linkedin_path is None or not linkedin_path.exists()):
        st.error(f"LinkedIn file not found: {linkedin_path_str}")
        return

    st.write(f"Resume: `{resume_path}`" if resume_path else "_No resume selected._")
    st.write(f"LinkedIn: `{linkedin_path}`" if linkedin_path else "_No LinkedIn file selected._")

    if resume_path and linkedin_path:
        st.markdown("---")
        handoff_button(
            "consolidate",
            [resume_path, linkedin_path],
            note="Claude Code will diff both files and produce inconsistencies with LLM-coached resolutions.",
            key="cons_handoff_btn",
        )
