"""Read/write helpers for ~/.brains-resume/profile.json (post-B trimmed shape).

The profile now holds two fields only: the pointer to the active candidate
and the log_handoffs UI preference. Per-candidate data (name, focus areas,
healthy weekly rate, pacing notes) lives in the candidates table.

Backwards-compat: a legacy-shape file (with first_name/focus_areas/etc) is
read as an empty Profile. The legacy fields are NOT lost — they are consumed
by scripts.tracker._post_migration.run_b_backfill when the schema reaches v5.
"""
import json
import os
from pathlib import Path

from scripts.tracker.models import Profile


DEFAULT_PROFILE_PATH = Path.home() / ".brains-resume" / "profile.json"


def get_profile_path() -> Path:
    override = os.environ.get("BRAINS_TRACKER_PROFILE_PATH")
    if override:
        return Path(override)
    return DEFAULT_PROFILE_PATH


def read_profile() -> Profile:
    path = get_profile_path()
    if not path.exists():
        return Profile()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Profile()
    if not isinstance(data, dict):
        return Profile()
    return Profile(
        active_candidate_id=data.get("active_candidate_id"),
        log_handoffs=data.get("log_handoffs", True),
    )


def write_profile(profile: Profile) -> None:
    path = get_profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "active_candidate_id": profile.active_candidate_id,
                "log_handoffs": profile.log_handoffs,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
