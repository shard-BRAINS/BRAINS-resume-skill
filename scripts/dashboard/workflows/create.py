"""/brains-create — interactive interview to build a resume from scratch."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st

from scripts.dashboard.workflows._card import handoff_button
from scripts.outputs.io import (
    _SKILL_VERSION,
    make_artifact_path,
    get_outputs_root,
)
from scripts.outputs.naming import artifact_filename, new_uid
from scripts.outputs.tagging import ArtifactMeta
from scripts.tracker.add import NoActiveCandidateError
from scripts.tracker.candidates import get_active_candidate


def _resolve_target(jd_id: int) -> Tuple[Path, ArtifactMeta]:
    """Compute the output path + ArtifactMeta for a /brains-create run.

    Either branch resolves the active candidate. jd_id > 0 anchors to that
    JD's folder via make_artifact_path; jd_id == 0 writes to the _library
    directory using the active candidate's name.
    Raises NoActiveCandidateError when no active candidate is set.
    """
    active = get_active_candidate()
    if active is None:
        raise NoActiveCandidateError(
            "No active candidate is set. Select or create one in the sidebar."
        )

    if jd_id:
        return make_artifact_path(
            int(jd_id), "resume", parent_uid=None, candidate_id=active.id,
        )

    library = get_outputs_root() / "_library"
    library.mkdir(parents=True, exist_ok=True)
    uid = new_uid()
    target_path = library / artifact_filename(
        first_name=active.first_name, last_name=active.last_name,
        kind="resume", created_date=date.today(), uid=uid,
    )
    meta = ArtifactMeta(
        artifact_uid=uid, artifact_kind="resume",
        jd_id=None, parent_uid=None,
        created_at=datetime.utcnow().isoformat() + "Z",
        skill_version=_SKILL_VERSION,
        candidate_id=active.id,
    )
    return target_path, meta


def render(file_path: Optional[Path] = None, key_prefix: str = "create") -> None:
    st.markdown("**Create a resume from scratch.**")
    st.caption("Claude Code walks through a structured interview — pace yourself, use breaks freely.")
    active = get_active_candidate()
    if active is None:
        st.error("No active candidate. Select or create one in the sidebar.")
        return
    st.caption(f"This resume will be for: **{active.first_name} {active.last_name}**.")
    jd_id = st.number_input(
        "JD id (optional — leave at 0 to save in _library)", min_value=0, step=1,
        key=f"{key_prefix}_jd_id",
    )
    try:
        target_path, meta = _resolve_target(int(jd_id))
    except NoActiveCandidateError:
        st.error("No active candidate. Select or create one in the sidebar.")
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
            "and register the new resume in the tracker for the active candidate. "
            "Then call `scripts.drift.on_artifact_finalised(meta.artifact_uid, data)` "
            "to persist a fact snapshot and compute drift."
        ),
        key=f"{key_prefix}_btn",
    )
