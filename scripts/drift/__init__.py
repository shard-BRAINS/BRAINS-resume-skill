"""BRAINS Resume Skill — drift analytics package.

See docs/specs/2026-05-19-resume-drift-analytics-design.md.
"""
from typing import Literal


def on_artifact_finalised(
    artifact_uid: str,
    workflow_data: dict,
    kind: Literal["resume", "cover-letter"] = "resume",
) -> None:
    """Single integration point called by Claude Code after finalize_docx.

    For resumes: builds a snapshot from the workflow data and runs drift compute.
    For cover letters: no-op (out of scope for v1; see spec §4).
    """
    if kind != "resume":
        return
    from scripts.drift.snapshot_from_workflow import facts_from_workflow_data
    from scripts.drift.compute import write_snapshot_and_compute_drift
    facts = facts_from_workflow_data(workflow_data)
    write_snapshot_and_compute_drift(artifact_uid, facts)
