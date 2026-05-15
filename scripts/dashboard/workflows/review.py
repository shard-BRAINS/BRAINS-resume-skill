"""/brains-review — partial preview via bias_scan, full multi-pass review in Claude Code."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import is_docx, pick_file
from scripts.dashboard.workflows._card import handoff_button
from scripts.parsers.docx_to_text import parse_docx_resume
from scripts.validators.bias_scan import bias_scan


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Audit a resume for ND-bias, ATS-safety, and integrity issues.**")
    st.caption("Dashboard shows a shallow bias-scan preview. The full multi-pass review (LLM-driven) runs in Claude Code.")

    if file_path is None:
        file_path = pick_file("resume", key="review")
    if file_path is None:
        return

    st.write(f"Selected: `{file_path}`")

    if is_docx(file_path) and st.button("Preview bias scan", key="review_preview_btn"):
        try:
            text = parse_docx_resume(file_path).get("raw_text", "")
            if not text:
                st.warning("No text extracted from the DOCX — nothing to scan.")
            else:
                result = bias_scan(text)
                findings = result.findings
                if not findings:
                    st.success("No bias-catalog hits in the shallow preview.")
                else:
                    st.subheader("Bias-scan preview")
                    for f in findings:
                        st.warning(f"**{f.pattern_code}**: {f.excerpt[:200] if f.excerpt else ''}")
                        if f.suggestion:
                            st.caption(f.suggestion)
        except Exception as e:
            st.error(f"Preview failed: {e}")

    st.markdown("---")
    handoff_button("review", [file_path], note="Run the full multi-pass review in Claude Code (LLM-coached).", key="review_handoff_btn")
