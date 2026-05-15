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
