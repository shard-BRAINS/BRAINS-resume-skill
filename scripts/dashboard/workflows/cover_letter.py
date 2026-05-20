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
)
from scripts.outputs.tagging import ArtifactMeta
from scripts.tracker.add import NoActiveCandidateError
from scripts.tracker.candidates import get_active_candidate


def _resolve_target(
    jd_id: int,
    parent_uid: Optional[str] = None,
) -> Tuple[Path, ArtifactMeta]:
    """Compute the output path + ArtifactMeta for a /brains-cover-letter run.

    Cover letters always anchor to a JD folder (jd_id > 0), link to a parent
    resume via `parent_uid`, and use the active candidate. Raises
    NoActiveCandidateError when no active candidate is set.
    """
    active = get_active_candidate()
    if active is None:
        raise NoActiveCandidateError(
            "No active candidate is set. Select or create one in the sidebar."
        )
    return make_artifact_path(
        int(jd_id), "cover-letter", parent_uid=parent_uid, candidate_id=active.id,
    )


def render(file_path: Optional[Path] = None, key_prefix: str = "cl") -> None:
    st.markdown("**Generate a cover letter matched to a tailored resume + JD.**")
    active = get_active_candidate()
    if active is None:
        st.error("No active candidate. Select or create one in the sidebar.")
        return
    st.caption(f"This cover letter will be for: **{active.first_name} {active.last_name}**.")
    if file_path is None:
        file_path = pick_file("resume", key=f"{key_prefix}_resume")
    jd_id = st.number_input(
        "JD id (from tracker)", min_value=1, step=1, key=f"{key_prefix}_jd_id",
    )
    st.write(f"Resume: `{file_path}`" if file_path else "_No resume selected._")
    if file_path is not None and jd_id:
        try:
            resume_uid = read_artifact_uid(file_path)
        except Exception:
            resume_uid = None
        try:
            target_path, meta = _resolve_target(int(jd_id), parent_uid=resume_uid)
        except NoActiveCandidateError:
            st.error("No active candidate. Select or create one in the sidebar.")
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
                "artifact_uid=meta.artifact_uid, parent_uid=<resume uid or None>)` "
                "for the active candidate. "
                "Then call `scripts.drift.on_artifact_finalised(meta.artifact_uid, data, "
                "kind=\"cover-letter\")` — a no-op for cover letters, kept uniform "
                "with the resume workflows."
            ),
            key=f"{key_prefix}_btn",
        )
