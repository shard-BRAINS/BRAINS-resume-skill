"""High-level orchestration for output organization.

Bridges naming (pure rules) and tagging (DOCX writes) with the tracker.
Public API (subsequent tasks expand this):

- get_outputs_root() -> Path
- ensure_jd_folder(jd_id) -> Path
- make_artifact_path(jd_id, kind, parent_uid=None) -> (Path, ArtifactMeta)
- finalize_docx(path, meta) -> None
- read_artifact_uid(path) -> str | None
- find_artifact_by_uid(uid) -> ResumeVersion | CoverLetter | None
"""
from __future__ import annotations

import os
from pathlib import Path


DEFAULT_OUTPUTS_ROOT = Path.home() / ".brains-resume" / "outputs"


class ProfileNameMissingError(Exception):
    """Raised when first_name or last_name is missing from profile.json."""


class OutputsDirNotWritableError(Exception):
    """Raised when the configured outputs directory cannot be written to."""


class UIDCollisionError(Exception):
    """Raised when 5 consecutive UID generations all collided with existing rows."""


def get_outputs_root() -> Path:
    """Return the outputs root, honouring BRAINS_OUTPUTS_DIR override."""
    override = os.environ.get("BRAINS_OUTPUTS_DIR")
    if override:
        return Path(override)
    return DEFAULT_OUTPUTS_ROOT


from datetime import datetime

from scripts.outputs.naming import folder_name, resolve_folder_collision
from scripts.tracker.db import open_db


def ensure_jd_folder(jd_id: int) -> Path:
    """Look up the JD row, compute the folder path, create the directory
    on disk if missing, write the path to jds.folder_path on first create.
    Idempotent.
    """
    conn = open_db()
    try:
        row = conn.execute(
            """SELECT company, role_title, created_at, folder_path,
                      source, source_ref
               FROM jds WHERE id = ?""",
            (jd_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"No JD with id={jd_id}")
        company, role_title, created_at, existing_path, source, source_ref = row
        if existing_path:
            folder = Path(existing_path)
            folder.mkdir(parents=True, exist_ok=True)
            return folder
        outputs_root = get_outputs_root()
        try:
            outputs_root.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OutputsDirNotWritableError(
                f"Cannot create or write to outputs dir {outputs_root}: {e}"
            )
        jd_date = datetime.fromisoformat(created_at.rstrip("Z")).date()
        # Recruiter: when source='agency', source_ref holds the agency name.
        recruiter = source_ref if source == "agency" else None
        # Use company unless it's empty/falsy (treat empty string as None).
        anchor_company = company if company else None
        candidate = folder_name(jd_date, anchor_company, recruiter, role_title)
        unique_name = resolve_folder_collision(outputs_root, candidate)
        folder = outputs_root / unique_name
        folder.mkdir(parents=True, exist_ok=True)
        conn.execute(
            "UPDATE jds SET folder_path = ? WHERE id = ?",
            (str(folder), jd_id),
        )
        conn.commit()
        return folder
    finally:
        conn.close()
