"""/brains-deai — scan a DOCX for AI-tell signals + optional Claude Code handoff."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import is_docx, pick_file
from scripts.dashboard.workflows._card import handoff_button
from scripts.parsers.docx_to_text import parse_docx_resume
from scripts.validators.ai_signal_check import ai_signal_check


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Scan a document for AI-tell signals.**")
    st.caption("Runs the nine-finding-code de-AI scanner natively. Use the handoff button for rewrite suggestions in Claude Code.")
    if file_path is None:
        file_path = pick_file("resume", key="deai")
    if file_path is None:
        return

    st.write(f"Selected: `{file_path}`")
    if not is_docx(file_path):
        st.error("DOCX required for in-dashboard scan. Use the handoff button (Claude Code can read PDFs).")
        handoff_button("deai", [file_path], note="Run de-AI scan in Claude Code (reads PDF).", key="deai_handoff_pdf")
        return

    if st.button("Scan now", key="deai_scan_btn"):
        try:
            text = parse_docx_resume(file_path).get("raw_text", "")
            if not text:
                st.warning("No text extracted from the DOCX — nothing to scan.")
                return
            result = ai_signal_check(text)
        except Exception as e:
            st.error(f"Scan failed: {e}")
            return
        score = result.score
        findings = result.findings
        if score is not None:
            colour = "green" if score < 30 else ("orange" if score < 60 else "red")
            st.markdown(f"**Score:** <span style='color:{colour}; font-size:1.4em; font-weight:600;'>{score}/100</span> (lower is better)", unsafe_allow_html=True)
        if findings:
            st.subheader("Findings")
            for f in findings:
                with st.expander(f"{f.code} — {f.severity}"):
                    if f.excerpt:
                        st.code(f.excerpt, language="text")
                    if f.suggestion:
                        st.caption(f.suggestion)
        else:
            st.success("No de-AI findings.")

    st.markdown("---")
    handoff_button("deai", [file_path], note="Get rewrite suggestions in Claude Code.", key="deai_handoff_btn")
