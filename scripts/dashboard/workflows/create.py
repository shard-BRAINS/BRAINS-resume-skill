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
