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
