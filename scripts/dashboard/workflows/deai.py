"""/brains-deai — scan a DOCX for AI-tell signals + optional Claude Code handoff."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import is_docx, pick_file
from scripts.dashboard.workflows._card import handoff_button
from scripts.outputs.io import (
    read_artifact_uid,
    ProfileNameMissingError,
)
from scripts.outputs.naming import artifact_filename, new_uid
from scripts.outputs.tagging import ArtifactMeta
from scripts.parsers.docx_to_text import parse_docx_resume
from scripts.tracker.profile import read_profile
from scripts.validators.ai_signal_check import ai_signal_check


def render(file_path: Optional[Path] = None, key_prefix: str = "deai") -> None:
    st.markdown("**Scan a document for AI-tell signals.**")
    st.caption("Runs the nine-finding-code de-AI scanner natively. Use the handoff button for rewrite suggestions in Claude Code.")
    if file_path is None:
        file_path = pick_file("resume", key=f"{key_prefix}_pick")
    if file_path is None:
        return

    st.write(f"Selected: `{file_path}`")
    if not is_docx(file_path):
        st.error("DOCX required for in-dashboard scan. Use the handoff button (Claude Code can read PDFs).")
        handoff_button("deai", [file_path], note="Run de-AI scan in Claude Code (reads PDF).", key=f"{key_prefix}_handoff_pdf")
        return

    if st.button("Scan now", key=f"{key_prefix}_scan_btn"):
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

    # Compute output path alongside the source file.
    source_uid = read_artifact_uid(file_path)
    profile = read_profile()
    if not profile.first_name or not profile.last_name:
        st.error("Set your first and last name in the sidebar before using the handoff.")
        return
    uid = new_uid()
    target_path = file_path.parent / artifact_filename(
        first_name=profile.first_name,
        last_name=profile.last_name,
        kind="resume",
        created_date=date.today(),
        uid=uid,
    )
    meta = ArtifactMeta(
        artifact_uid=uid,
        artifact_kind="resume",
        jd_id=None,
        parent_uid=source_uid,
        created_at=datetime.utcnow().isoformat() + "Z",
        skill_version="1.5.0",
    )
    st.caption(f"Cleaned copy will land at: `{target_path}`")
    handoff_button(
        "deai",
        [str(file_path), str(target_path), meta.artifact_uid,
         meta.parent_uid or ""],
        note="Get rewrite suggestions in Claude Code.",
        key=f"{key_prefix}_handoff_btn",
    )
