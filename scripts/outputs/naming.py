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

_APOSTROPHE_LIKE = "'''ʼ"


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
