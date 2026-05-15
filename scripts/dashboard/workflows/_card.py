"""Shared helpers for workflow modules: input collection, handoff buttons."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Union

import streamlit as st

from scripts.dashboard import handoff as _handoff


ArgLike = Union[str, Path, None]


def collect_args(values: Iterable[ArgLike]) -> list[str]:
    """Filter out None/empty values and stringify Path objects."""
    out: list[str] = []
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            out.append(s)
    return out


def handoff_button(cmd: str, args: Iterable[ArgLike], note: str = "", key: Optional[str] = None) -> None:
    """Render a `Copy /brains-<cmd> to clipboard` button. On click, calls handoff."""
    label = f"Copy /brains-{cmd} to clipboard"
    if st.button(label, key=key or f"handoff_{cmd}"):
        _handoff.handoff(cmd, *collect_args(args), note=note)
