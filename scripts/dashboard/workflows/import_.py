"""/brains-import — upload a DOCX (or paste text) as a candidate's baseline.

The workflow runs the LLM-backed fact extractor, surfaces any implausibility
flags for user review, and on confirmation writes the resume_versions row
plus snapshot + drift scores.

The module is named import_.py because `import` is a Python keyword.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st

from scripts.outputs.io import get_outputs_root, _SKILL_VERSION
from scripts.outputs.naming import artifact_filename, new_uid
from scripts.outputs.tagging import ArtifactMeta
from scripts.tracker.add import NoActiveCandidateError
from scripts.tracker.candidates import get_active_candidate


def _resolve_target() -> Tuple[Path, ArtifactMeta, int]:
    """Compute the output path + ArtifactMeta for an imported baseline.

    Imports always land in the _library directory (no JD anchor) and use the
    active candidate's name for the filename and id stamped on the meta.

    Raises NoActiveCandidateError when no active candidate is set.
    """
    active = get_active_candidate()
    if active is None:
        raise NoActiveCandidateError(
            "No active candidate is set. Select or create one in the sidebar."
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
    return target_path, meta, active.id


def run_import(
    source_text: str,
    confirm_despite_warnings: bool,
) -> dict:
    """Pure-Python entry point used by the Streamlit card AND by tests.

    The imported baseline is linked to the active candidate. To import for a
    new person, create that candidate in the sidebar first.

    Returns one of:
      {'status': 'imported', 'artifact_uid': '...', 'facts': {...}, 'warnings': []}
      {'status': 'needs_confirmation', 'artifact_uid': None, 'facts': {...}, 'warnings': [...]}
      {'status': 'error', 'message': '...', 'artifact_uid': None}
    """
    from scripts.drift.extract_facts import (
        extract_facts_from_text, flag_implausible_values, FactExtractionError,
    )
    from scripts.drift.compute import write_snapshot_and_compute_drift
    from scripts.tracker.add import add_resume_version

    try:
        facts = extract_facts_from_text(source_text)
    except FactExtractionError as e:
        return {"status": "error", "message": str(e), "artifact_uid": None}

    warnings = flag_implausible_values(facts)
    if warnings and not confirm_despite_warnings:
        return {
            "status": "needs_confirmation",
            "artifact_uid": None,
            "facts": facts,
            "warnings": warnings,
        }

    try:
        path, meta, candidate_id = _resolve_target()
    except NoActiveCandidateError as e:
        return {"status": "error", "message": str(e), "artifact_uid": None}

    add_resume_version(
        file_path=str(path),
        template="imported",
        focus_areas=[],
        artifact_uid=meta.artifact_uid,
        candidate_id=candidate_id,
    )
    write_snapshot_and_compute_drift(meta.artifact_uid, facts)
    return {
        "status": "imported",
        "artifact_uid": meta.artifact_uid,
        "facts": facts,
        "warnings": warnings,
    }


def render(file_path: Optional[Path] = None, key_prefix: str = "import") -> None:
    st.markdown("**Import an existing resume as a baseline.**")
    st.caption(
        "Upload a DOCX or paste text. The LLM extractor will produce a fact "
        "snapshot you can review before committing."
    )

    active = get_active_candidate()
    if active is None:
        st.error("No active candidate. Select or create one in the sidebar.")
        return
    st.caption(f"This baseline will be for: **{active.first_name} {active.last_name}**.")

    source_text = st.text_area(
        "Resume text (paste the plain-text content of the DOCX here)",
        key=f"{key_prefix}_source",
        height=300,
    )
    confirm = st.checkbox(
        "I have reviewed the warnings below and want to import anyway",
        key=f"{key_prefix}_confirm",
    )

    if st.button("Import baseline", key=f"{key_prefix}_btn"):
        if not source_text.strip():
            st.warning("Paste some resume text first.")
            return
        result = run_import(
            source_text=source_text,
            confirm_despite_warnings=confirm,
        )
        if result["status"] == "error":
            st.error(result["message"])
            return
        if result["status"] == "needs_confirmation":
            st.warning("Implausible values detected — review and confirm to proceed:")
            for w in result["warnings"]:
                st.write(f"- {w}")
            return
        st.success(
            f"Imported baseline with artifact_uid={result['artifact_uid']!r}. "
            "If this is the candidate's first resume, it is now their active "
            "baseline; otherwise use the Drift tab to promote it."
        )
