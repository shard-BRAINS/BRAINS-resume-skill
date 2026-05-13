"""Read/write helpers for ~/.brains-resume/profile.json.

The profile holds the user's focus areas (used by the JD analyzer's role-fit
score) and their self-defined healthy weekly application rate (used by the
pre-application sanity check). Missing file or corrupt JSON both return an
empty Profile — never crash. Tests override the path via
BRAINS_TRACKER_PROFILE_PATH.
"""
import json
import os
from pathlib import Path

from scripts.tracker.models import Profile


DEFAULT_PROFILE_PATH = Path.home() / ".brains-resume" / "profile.json"


def get_profile_path() -> Path:
    """Return the profile path, honouring BRAINS_TRACKER_PROFILE_PATH override."""
    override = os.environ.get("BRAINS_TRACKER_PROFILE_PATH")
    if override:
        return Path(override)
    return DEFAULT_PROFILE_PATH


def read_profile() -> Profile:
    """Read the profile file. Missing file or corrupt JSON both return empty Profile."""
    path = get_profile_path()
    if not path.exists():
        return Profile()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Profile()
    return Profile(
        focus_areas=list(data.get("focus_areas", []) or []),
        healthy_weekly_rate=data.get("healthy_weekly_rate"),
    )


def write_profile(profile: Profile) -> None:
    """Write the profile to disk. Creates parent directory if needed."""
    path = get_profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "focus_areas": profile.focus_areas,
                "healthy_weekly_rate": profile.healthy_weekly_rate,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
