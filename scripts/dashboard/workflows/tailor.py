"""/brains-tailor — tailor a resume to a specific job description."""
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


def render(file_path: Optional[Path] = None, key_prefix: str = "tailor") -> None:
    st.markdown("**Tailor a resume to a specific job description.**")
    if file_path is None:
        file_path = pick_file("resume", key=f"{key_prefix}_resume")
    jd_id = st.number_input(
        "JD id (from tracker)", min_value=1, step=1, key=f"{key_prefix}_jd_id",
    )
    st.write(f"Resume: `{file_path}`" if file_path else "_No resume selected._")
    if file_path is not None and jd_id:
        try:
            source_uid = read_artifact_uid(file_path)
        except Exception:
            source_uid = None
        try:
            target_path, meta = make_artifact_path(
                int(jd_id), "resume", parent_uid=source_uid,
            )
        except ProfileNameMissingError:
            st.error(
                "Set your first and last name in the sidebar before tailoring."
            )
            return
        except Exception as exc:
            st.warning(f"Could not resolve output path: {exc}")
            return
        st.caption(f"Output will land at: `{target_path}`")
        handoff_button(
            "tailor",
            [str(file_path), int(jd_id), str(target_path), meta.artifact_uid,
             meta.parent_uid or ""],
            note=(
                "Claude Code will produce a tailored resume at the path shown above. "
                "After save, call `scripts.outputs.io.finalize_docx(target_path, meta)` "
                "and `tracker.add_resume_version(file_path=target_path, ..., "
                "artifact_uid=meta.artifact_uid, parent_uid=<source resume's uid or None>)`."
            ),
            key=f"{key_prefix}_btn",
        )
