"""/brains-cover-letter — generate a cover letter matched to a tailored resume + JD."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import pick_file
from scripts.dashboard.workflows._card import handoff_button
from scripts.outputs.io import (
    make_artifact_path,
    read_artifact_uid,
    ProfileNameMissingError,
)


def render(file_path: Optional[Path] = None, key_prefix: str = "cl") -> None:
    st.markdown("**Generate a cover letter matched to a tailored resume + JD.**")
    if file_path is None:
        file_path = pick_file("resume", key=f"{key_prefix}_resume")
    jd_id = st.number_input(
        "JD id (from tracker)", min_value=1, step=1, key=f"{key_prefix}_jd_id",
    )
    st.write(f"Resume: `{file_path}`" if file_path else "_No resume selected._")
    if file_path is not None and jd_id:
        resume_uid = read_artifact_uid(file_path)
        try:
            target_path, meta = make_artifact_path(
                int(jd_id), "cover-letter", parent_uid=resume_uid,
            )
        except ProfileNameMissingError:
            st.error(
                "Set your first and last name in the sidebar before generating a cover letter."
            )
            return
        st.caption(f"Output will land at: `{target_path}`")
        handoff_button(
            "cover-letter",
            [str(file_path), int(jd_id), str(target_path), meta.artifact_uid,
             meta.parent_uid or ""],
            note=(
                "Claude Code will draft a cover letter against the tailored resume. "
                "After save, call `scripts.outputs.io.finalize_docx(target_path, meta)` "
                "and `tracker.add_cover_letter(file_path=target_path, ..., "
                "artifact_uid=meta.artifact_uid, parent_uid=<resume uid or None>)`."
            ),
            key=f"{key_prefix}_btn",
        )
