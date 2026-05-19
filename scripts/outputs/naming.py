"""Pure naming/sanitization functions for output folders and filenames.

No I/O. No tracker access. Every function is deterministic given its
inputs. The folder/filename conventions defined here are the single
source of truth — generators, the tracker, and CLI helpers all consume
this module.
"""
from __future__ import annotations

import re
import secrets
from datetime import date
from typing import Literal


CROCKFORD_BASE32 = "23456789ABCDEFGHJKMNPQRSTVWXYZ"  # 30 chars, no 0/O/1/I/L

# Em-dash, en-dash, figure-dash, horizontal-bar — all normalize to '-'.
_DASH_LIKE = "–—―−"

_APOSTROPHE_LIKE = "'‘’ʼ"  # straight, left-curly, right-curly, modifier-letter


def slugify(text: str, max_len: int = 40) -> str:
    """Normalize text for folder/filename use.

    - Drops apostrophes (don't / won't / O'Brien -> dont / wont / OBrien)
    - Normalizes em/en-dashes to '-'
    - Replaces any non-alphanumeric run with a single '-'
    - Strips leading/trailing '-'
    - Truncates to max_len with no trailing dash
    """
    if not text:
        return ""
    # Drop apostrophes entirely first so "O'Brien" becomes "OBrien", not "O-Brien".
    for ch in _APOSTROPHE_LIKE:
        text = text.replace(ch, "")
    # Normalize dash-like characters to '-'.
    for ch in _DASH_LIKE:
        text = text.replace(ch, "-")
    # Replace any run of non-alphanumeric with a single '-'.
    text = re.sub(r"[^A-Za-z0-9]+", "-", text)
    text = text.strip("-")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text


def new_uid() -> str:
    """Generate a 6-char Crockford base32 UID.

    30^6 = ~729 million possibilities. No 0/O/1/I/L (no visual ambiguity).
    Uses `secrets.choice` for cryptographically-strong randomness so
    UIDs can't be guessed even if an attacker sees recent ones.
    """
    return "".join(secrets.choice(CROCKFORD_BASE32) for _ in range(6))


_FOLDER_MAX_LEN = 80


def folder_name(
    jd_date: date,
    company: str | None,
    recruiter: str | None,
    role_title: str,
) -> str:
    """Compose 'YYYY-MM-DD_<Anchor>_<Role>'.

    Anchor: company if present, else 'via-<Recruiter>' if recruiter present,
    else 'unknown'. Total length capped at _FOLDER_MAX_LEN; role suffix is
    truncated first.
    """
    date_str = jd_date.isoformat()
    if company:
        anchor = slugify(company)
    elif recruiter:
        anchor = f"via-{slugify(recruiter)}"
    else:
        anchor = "unknown"
    role = slugify(role_title)
    base = f"{date_str}_{anchor}_{role}"
    if len(base) > _FOLDER_MAX_LEN:
        # Truncate the role portion only.
        prefix = f"{date_str}_{anchor}_"
        available = _FOLDER_MAX_LEN - len(prefix)
        role = role[: max(0, available)].rstrip("-")
        base = prefix + role
    return base


_VALID_KINDS = ("resume", "cover-letter")


def artifact_filename(
    first_name: str,
    last_name: str,
    kind: Literal["resume", "cover-letter"],
    created_date: date,
    uid: str,
    ext: str = "docx",
) -> str:
    """Compose '<First>_<Last>_<kind>_<YYYY-MM-DD>_<UID>.<ext>'.

    Names are slugified to single hyphen-joined tokens. Kind must be one
    of 'resume' or 'cover-letter'.
    """
    if kind not in _VALID_KINDS:
        raise ValueError(
            f"kind must be one of {_VALID_KINDS}, got {kind!r}"
        )
    first = slugify(first_name)
    last = slugify(last_name)
    return f"{first}_{last}_{kind}_{created_date.isoformat()}_{uid}.{ext}"
