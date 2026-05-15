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
