"""/brains-create — interactive interview to build a resume from scratch."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st

from scripts.dashboard.workflows._card import handoff_button
from scripts.outputs.io import (
    make_artifact_path,
    get_outputs_root,
    ProfileNameMissingError,
)
from scripts.outputs.naming import artifact_filename, new_uid, split_candidate_name
from scripts.outputs.tagging import ArtifactMeta
from scripts.tracker.profile import read_profile


def _resolve_target(
    jd_id: int,
    for_candidate: Optional[str] = None,
) -> Tuple[Path, ArtifactMeta]:
    """Compute the output path + ArtifactMeta for a /brains-create run.

    If jd_id > 0: anchor to that JD's folder via make_artifact_path.
    If jd_id == 0: write to the _library directory using profile name (or
    for_candidate override, when provided).
    Raises ProfileNameMissingError when no candidate name is available.
    """
    for_candidate = (for_candidate or "").strip() or None

    if jd_id:
        return make_artifact_path(
            int(jd_id), "resume",
            parent_uid=None,
            for_candidate=for_candidate,
        )

    if for_candidate:
        first_name, last_name = split_candidate_name(for_candidate)
    else:
        profile = read_profile()
        if not profile.first_name or not profile.last_name:
            raise ProfileNameMissingError(
                "Profile is missing first_name or last_name. "
                "Set them in the sidebar, or fill 'For candidate' above."
            )
        first_name, last_name = profile.first_name, profile.last_name

    library = get_outputs_root() / "_library"
    library.mkdir(parents=True, exist_ok=True)
    uid = new_uid()
    target_path = library / artifact_filename(
        first_name=first_name, last_name=last_name,
        kind="resume", created_date=date.today(), uid=uid,
    )
    meta = ArtifactMeta(
        artifact_uid=uid, artifact_kind="resume",
        jd_id=None, parent_uid=None,
        created_at=datetime.utcnow().isoformat() + "Z",
        skill_version="1.5.0",
        for_candidate=for_candidate,
    )
    return target_path, meta


def render(file_path: Optional[Path] = None, key_prefix: str = "create") -> None:
    st.markdown("**Create a resume from scratch.**")
    st.caption("Claude Code walks through a structured interview — pace yourself, use breaks freely.")
    jd_id = st.number_input(
        "JD id (optional — leave at 0 to save in _library)", min_value=0, step=1,
        key=f"{key_prefix}_jd_id",
    )
    for_candidate = st.text_input(
        "For candidate (optional — leave blank for yourself)",
        key=f"{key_prefix}_for_candidate",
        help="If you're building a resume for someone else, enter their name here.",
    )
    try:
        target_path, meta = _resolve_target(int(jd_id), for_candidate)
    except ProfileNameMissingError as e:
        st.error(str(e))
        return
    except Exception as exc:
        st.warning(f"Could not resolve output path: {exc}")
        return

    st.caption(f"Output will land at: `{target_path}`")
    handoff_button(
        "create",
        [str(target_path), meta.artifact_uid],
        note=(
            "Open Claude Code; paste this command to start the interview. "
            "After save, call `scripts.outputs.io.finalize_docx(target_path, meta)` "
            "and register the new resume in the tracker with `for_candidate` set "
            "to the same value if provided."
        ),
        key=f"{key_prefix}_btn",
    )
