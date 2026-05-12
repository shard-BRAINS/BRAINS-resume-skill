"""LinkedIn data-export ZIP parser.

Parses the user's own profile data and explicitly skips files containing
third-party PII (Connections.csv, messages.csv, Invitations.csv,
Reactions.csv, Comments.csv, Likes.csv). Logs the skipped files so the
user sees the safeguarding behaviour.

LinkedIn export file naming varies slightly over time; this parser is
defensive about case and minor variations.
"""
import csv
import io
import zipfile
from pathlib import Path
from typing import Union


READABLE_FILES = {
    "profile.csv": "profile",
    "positions.csv": "positions",
    "education.csv": "education",
    "skills.csv": "skills",
    "certifications.csv": "certifications",
    "projects.csv": "projects",
    "publications.csv": "publications",
    "languages.csv": "languages",
}

SKIP_FILES = {
    "connections.csv",
    "messages.csv",
    "invitations.csv",
    "reactions.csv",
    "comments.csv",
    "likes.csv",
    "ad_targeting.csv",
    "endorsement_given_info.csv",
    "endorsement_received_info.csv",
}


def _read_csv_text(text: str) -> list:
    """Read CSV text and return a list of dicts."""
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def parse_linkedin_export(path: Union[str, Path]) -> dict:
    """Parse a LinkedIn data export ZIP and return structured user data.

    Skips third-party-PII files and records them in ``skipped_files``.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"LinkedIn export not found: {path}")

    if not zipfile.is_zipfile(path):
        raise ValueError(f"File is not a valid ZIP archive: {path}")

    result = {
        "profile": {},
        "positions": [],
        "education": [],
        "skills": [],
        "certifications": [],
        "projects": [],
        "publications": [],
        "languages": [],
        "skipped_files": [],
    }

    with zipfile.ZipFile(path, "r") as zf:
        for name in zf.namelist():
            basename = Path(name).name
            lower = basename.lower()

            if lower in SKIP_FILES:
                result["skipped_files"].append(basename)
                continue

            if lower not in READABLE_FILES:
                continue

            key = READABLE_FILES[lower]
            try:
                content = zf.read(name).decode("utf-8-sig")
            except UnicodeDecodeError:
                content = zf.read(name).decode("latin-1")

            rows = _read_csv_text(content)

            if key == "profile":
                result["profile"] = rows[0] if rows else {}
            elif key == "skills":
                result["skills"] = [r.get("Name", "") for r in rows if r.get("Name")]
            else:
                result[key] = rows

    return result
