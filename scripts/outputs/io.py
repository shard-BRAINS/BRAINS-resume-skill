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


from datetime import datetime, date as _date
from typing import Literal

from scripts.outputs.naming import folder_name, resolve_folder_collision, artifact_filename, new_uid
from scripts.outputs.tagging import ArtifactMeta
from scripts.tracker.db import open_db
from scripts.tracker.profile import read_profile


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


_SKILL_VERSION = "2.2.0"
_MAX_UID_RETRIES = 5


def make_artifact_path(
    jd_id: int,
    kind: Literal["resume", "cover-letter"],
    parent_uid: str | None = None,
    for_candidate: str | None = None,
    candidate_id: int | None = None,
) -> tuple[Path, ArtifactMeta]:
    """Reserve a new artifact path + UID within the JD folder.

    Does NOT write the tracker row (the workflow does that after the
    generator succeeds). The caller passes the returned ArtifactMeta
    into the generator or to finalize_docx after save.

    Resolution order for the candidate whose name appears in the filename:
      1. explicit candidate_id (if provided)
      2. for_candidate name (resolved to candidate_id via find_or_create_by_name)
      3. active candidate from profile.json
      4. raises NoActiveCandidateError if none of the above resolves

    `for_candidate`, when provided, is also stamped onto the returned
    ArtifactMeta so the DOCX records the free-text name the caller used.
    """
    from scripts.tracker.candidates import (
        get_active_candidate, get_candidate, find_or_create_by_name,
    )

    if candidate_id is None and for_candidate:
        candidate_id = find_or_create_by_name(for_candidate)
    if candidate_id is None:
        active = get_active_candidate()
        if active is None:
            from scripts.tracker.add import NoActiveCandidateError
            raise NoActiveCandidateError(
                "No active candidate set. Pass candidate_id, for_candidate, "
                "or select a candidate in the dashboard sidebar."
            )
        candidate_id = active.id

    candidate = get_candidate(candidate_id)
    if candidate is None:
        raise ValueError(f"No candidate row with id={candidate_id}")

    folder = ensure_jd_folder(jd_id)
    today = _date.today()
    for _ in range(_MAX_UID_RETRIES):
        uid = new_uid()
        if find_artifact_by_uid(uid) is None:
            break
    else:
        raise UIDCollisionError(
            f"5 consecutive UID generations all collided. "
            f"Database may be saturated; investigate."
        )
    filename = artifact_filename(
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        kind=kind,
        created_date=today,
        uid=uid,
    )
    path = folder / filename
    meta = ArtifactMeta(
        artifact_uid=uid,
        artifact_kind=kind,
        jd_id=jd_id,
        parent_uid=parent_uid,
        created_at=datetime.utcnow().isoformat() + "Z",
        skill_version=_SKILL_VERSION,
        for_candidate=for_candidate,
        candidate_id=candidate_id,
    )
    return path, meta


def find_artifact_by_uid(uid: str):
    """Re-export of tracker.query.get_artifact_by_uid for callers that
    only want the outputs API."""
    from scripts.tracker.query import get_artifact_by_uid
    return get_artifact_by_uid(uid)


from scripts.outputs.tagging import read_artifact_meta, write_artifact_meta


def finalize_docx(path: Path, meta: ArtifactMeta) -> None:
    """Write the artifact's UID + metadata into the DOCX custom properties.

    Raises FileNotFoundError if the DOCX doesn't exist (caller must have
    already invoked the generator).
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Cannot finalize {path}: file does not exist. "
            f"Generator must run before finalize_docx."
        )
    write_artifact_meta(path, meta)


def read_artifact_uid(path: Path) -> str | None:
    """Convenience: return just the BrainsArtifactId or None."""
    meta = read_artifact_meta(path)
    return meta.artifact_uid if meta else None
