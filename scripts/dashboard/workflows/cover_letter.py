"""/brains-cover-letter — generate a cover letter matched to a tailored resume + JD."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import streamlit as st

from scripts.dashboard.file_input import pick_file
from scripts.dashboard.workflows._card import handoff_button
from scripts.outputs.io import (
    make_artifact_path,
    read_artifact_uid,
    ProfileNameMissingError,
)
from scripts.outputs.tagging import ArtifactMeta


def _resolve_target(
    jd_id: int,
    parent_uid: Optional[str] = None,
    for_candidate: Optional[str] = None,
) -> Tuple[Path, ArtifactMeta]:
    """Compute the output path + ArtifactMeta for a /brains-cover-letter run.

    Cover letters always anchor to a JD folder (jd_id > 0) and link to a
    parent resume via `parent_uid`. The optional `for_candidate` overrides
    the profile name on both the filename and the stamped ArtifactMeta.
    """
    for_candidate = (for_candidate or "").strip() or None
    return make_artifact_path(
        int(jd_id), "cover-letter",
        parent_uid=parent_uid,
        for_candidate=for_candidate,
    )


def render(file_path: Optional[Path] = None, key_prefix: str = "cl") -> None:
    st.markdown("**Generate a cover letter matched to a tailored resume + JD.**")
    if file_path is None:
        file_path = pick_file("resume", key=f"{key_prefix}_resume")
    jd_id = st.number_input(
        "JD id (from tracker)", min_value=1, step=1, key=f"{key_prefix}_jd_id",
    )
    for_candidate = st.text_input(
        "For candidate (optional — leave blank for yourself)",
        key=f"{key_prefix}_for_candidate",
        help="If you're drafting a cover letter for someone else, enter their name here.",
    )
    st.write(f"Resume: `{file_path}`" if file_path else "_No resume selected._")
    if file_path is not None and jd_id:
        try:
            resume_uid = read_artifact_uid(file_path)
        except Exception:
            resume_uid = None
        try:
            target_path, meta = _resolve_target(
                int(jd_id), parent_uid=resume_uid, for_candidate=for_candidate,
            )
        except ProfileNameMissingError:
            st.error(
                "Set your first and last name in the sidebar before generating "
                "a cover letter, or fill 'For candidate' above."
            )
            return
        except Exception as exc:
            st.warning(f"Could not resolve output path: {exc}")
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
                "artifact_uid=meta.artifact_uid, parent_uid=<resume uid or None>, "
                "for_candidate=<same value as above, if set>)`."
            ),
            key=f"{key_prefix}_btn",
        )
