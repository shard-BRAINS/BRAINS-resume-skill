"""Clipboard + handoff log helper for dashboard workflow buttons.

Builds a slash-command string from a command name + args, copies to OS clipboard,
optionally logs to disk, and renders a Streamlit toast. Pure-Python pieces are
unit-tested; the Streamlit toast rendering is covered by AppTest only.
"""
from __future__ import annotations


def build_command(cmd: str, *args: str) -> str:
    """Build `/brains-<cmd> arg1 arg2 ...`. Whitespace-quotes args containing spaces."""
    quoted = [f'"{a}"' if " " in a else a for a in args if a]
    return f"/brains-{cmd} {' '.join(quoted)}".strip()
