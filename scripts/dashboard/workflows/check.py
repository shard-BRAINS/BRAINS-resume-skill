"""/brains-check — composite final-pass: ATS + integrity + bias + AI-signal."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import is_docx, pick_file
from scripts.dashboard.workflows._card import handoff_button
from scripts.parsers.docx_to_text import parse_docx_resume
from scripts.validators.ai_signal_check import ai_signal_check
from scripts.validators.ats_check import ats_check
from scripts.validators.bias_scan import bias_scan
from scripts.validators.integrity_check import integrity_check


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Final pre-submit pass — ATS-safety, document integrity, ND-bias, AI-signal score.**")
    st.caption("Runs all four validators in-dashboard. Use the handoff button for the LLM coaching layer.")

    if file_path is None:
        file_path = pick_file("resume", key="check")
    if file_path is None:
        return

    st.write(f"Selected: `{file_path}`")
    if not is_docx(file_path):
        st.error("DOCX required for in-dashboard checks. Use the handoff button.")
        handoff_button("check", [file_path], note="Run composite check in Claude Code (reads PDF).", key="check_handoff_pdf")
        return

    if st.button("Run all checks", key="check_run_btn"):
        try:
            text = parse_docx_resume(file_path).get("raw_text", "")
        except Exception as e:
            st.error(f"Could not parse DOCX: {e}")
            return

        cols = st.columns(2)
        with cols[0]:
            st.subheader("ATS-safety")
            try:
                ats_result = ats_check(str(file_path))
                if ats_result.passed:
                    st.success("ATS-safe.")
                for f in ats_result.failures:
                    st.error(f"{f.code}: {f.message}")
                for w in ats_result.warnings:
                    st.warning(f"{w.code}: {w.message}")
            except Exception as e:
                st.error(f"ATS check failed: {e}")

            st.subheader("Document integrity")
            try:
                integ_result = integrity_check(text)
                if not integ_result.findings:
                    st.success("Integrity clean.")
                for f in integ_result.findings:
                    sev = (f.severity or "low").lower()
                    label = f"{f.code} ({sev})"
                    if sev == "high":
                        st.error(label)
                    else:
                        st.warning(label)
                    if f.excerpt:
                        st.code(f.excerpt, language="text")
                    if f.suggestion:
                        st.caption(f.suggestion)
            except Exception as e:
                st.error(f"Integrity check failed: {e}")

        with cols[1]:
            st.subheader("ND-bias scan")
            try:
                bias_result = bias_scan(text)
                bias_hits = bias_result.findings
                if not bias_hits:
                    st.success("No bias-catalog hits.")
                for b in bias_hits[:5]:
                    st.warning(f"**{b.pattern_code}**: {b.excerpt[:120] if b.excerpt else ''}")
                    if b.suggestion:
                        st.caption(b.suggestion)
                if len(bias_hits) > 5:
                    st.caption(f"+ {len(bias_hits) - 5} more")
            except Exception as e:
                st.error(f"Bias scan failed: {e}")

            st.subheader("AI-signal")
            try:
                ai_result = ai_signal_check(text)
                if ai_result.score is not None:
                    st.metric("AI-signal score (lower = better)", f"{ai_result.score}/100")
                if ai_result.findings:
                    top = ai_result.findings[:3]
                    st.caption("Top findings:")
                    for f in top:
                        st.caption(f"• {f.code} ({f.severity})")
            except Exception as e:
                st.error(f"AI-signal scan failed: {e}")

    st.markdown("---")
    handoff_button("check", [file_path], note="Get the LLM coaching layer in Claude Code.", key="check_handoff_btn")
