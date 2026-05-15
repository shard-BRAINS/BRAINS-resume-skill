"""/brains-precheck — six-question coaching pass; registers the application in tracker."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.workflows._card import handoff_button


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Six-question coaching pass before submitting an application.**")
    st.caption("Coaching turns happen in Claude Code; the registration writes to the tracker DB.")
    company = st.text_input("Company", key="precheck_company")
    role = st.text_input("Role", key="precheck_role")
    jd_input = st.text_input("JD URL or file path", key="precheck_jd")
    if company and role and jd_input:
        handoff_button("precheck", [company, role, jd_input], note="Claude Code will run the six coaching questions, then register the application in the tracker.", key="precheck_btn")
