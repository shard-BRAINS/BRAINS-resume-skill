"""/brains-jd-analyze — analyze a JD for ND-relevant signals + optional handoff."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.workflows._card import handoff_button
from scripts.tracker.profile import read_profile
from scripts.validators.jd_analyzer import jd_analyze


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Analyse a job description for ND-relevant signals.**")
    st.caption("Red flags, masking cost, role-fit score (vs your profile focus areas).")

    jd_text = st.text_area("Paste JD text", key="jda_text", height=180, value="")
    jd_url = st.text_input("Or JD URL / file path (for the Claude Code handoff)", key="jda_url")

    if st.button("Analyze", key="jda_analyze_btn"):
        if not jd_text.strip():
            st.error("Paste the JD text first (in-dashboard analyzer needs raw text).")
        else:
            try:
                focus_areas = read_profile().focus_areas or []
            except Exception:
                focus_areas = []
            try:
                result = jd_analyze(jd_text, focus_areas=focus_areas)
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                return

            if result.role_fit_score is not None:
                st.metric("Role-fit score (vs your focus areas)", f"{result.role_fit_score}/100")

            findings = result.findings
            if not findings:
                st.success("No findings surfaced.")
            else:
                by_severity = {"high": [], "medium": [], "low": []}
                for f in findings:
                    sev = (f.severity or "low").lower()
                    by_severity.setdefault(sev, []).append(f)
                for sev in ("high", "medium", "low"):
                    items = by_severity.get(sev, [])
                    if items:
                        st.subheader(f"{sev.title()}-severity findings")
                        for f in items:
                            with st.expander(f"{f.code}"):
                                if f.excerpt:
                                    st.code(f.excerpt, language="text")
                                if f.suggestion:
                                    st.caption(f.suggestion)

            if result.required_list:
                st.markdown("**Required skills/competencies parsed:**")
                st.write(", ".join(result.required_list))
            if result.nice_list:
                st.markdown("**Nice-to-have skills/competencies:**")
                st.write(", ".join(result.nice_list))

    st.markdown("---")
    handoff_arg = jd_url or "(paste-from-clipboard)"
    handoff_button("jd-analyze", [handoff_arg], note="Full coaching report in Claude Code (will load the JD).", key="jda_handoff_btn")
