"""/brains-edit — apply review fixes to a resume."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.file_input import pick_file
from scripts.dashboard.workflows._card import handoff_button
from scripts.outputs.io import (
    make_artifact_path,
    read_artifact_uid,
    get_outputs_root,
    ProfileNameMissingError,
)
from scripts.outputs.naming import artifact_filename, new_uid
from scripts.outputs.tagging import ArtifactMeta
from scripts.tracker.profile import read_profile


def render(file_path: Optional[Path] = None, key_prefix: str = "edit") -> None:
    st.markdown("**Apply review fixes to a resume.**")
    st.caption("Hands the resume + the most recent review findings off to Claude Code for a clean ATS-safe rewrite.")
    if file_path is None:
        file_path = pick_file("resume", key=f"{key_prefix}_pick")
    jd_id = st.number_input(
        "JD id (optional — leave at 0 to save in _library)", min_value=0, step=1,
        key=f"{key_prefix}_jd_id",
    )
    st.write(f"Selected: `{file_path}`" if file_path else "_No file selected._")
    if file_path is not None:
        try:
            source_uid = read_artifact_uid(file_path)
        except Exception:
            source_uid = None
        if jd_id:
            try:
                target_path, meta = make_artifact_path(
                    int(jd_id), "resume", parent_uid=source_uid,
                )
            except ProfileNameMissingError:
                st.error("Set your first and last name in the sidebar before editing.")
                return
            except Exception as exc:
                st.warning(f"Could not resolve output path: {exc}")
                return
        else:
            profile = read_profile()
            if not profile.first_name or not profile.last_name:
                st.error("Set your first and last name in the sidebar before editing.")
                return
            library = get_outputs_root() / "_library"
            library.mkdir(parents=True, exist_ok=True)
            uid = new_uid()
            target_path = library / artifact_filename(
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
        st.caption(f"Output will land at: `{target_path}`")
        handoff_button(
            "edit",
            [str(file_path), str(target_path), meta.artifact_uid,
             meta.parent_uid or ""],
            note=(
                "Claude Code will load the resume and apply review findings. "
                "After save, call `scripts.outputs.io.finalize_docx(target_path, meta)` "
                "and register the new version in the tracker."
            ),
            key=f"{key_prefix}_btn",
        )
