"""Clipboard + handoff log helper for dashboard workflow buttons.

Builds a slash-command string from a command name + args, copies to OS clipboard,
optionally logs to disk, and renders a Streamlit toast. Pure-Python pieces are
unit-tested; the Streamlit toast rendering is covered by AppTest only.
"""
from __future__ import annotations

import datetime
from pathlib import Path

import pyperclip
import streamlit as st

HANDOFF_LOG_DIR = Path.home() / ".brains-resume" / "handoffs"


def build_command(cmd: str, *args: str) -> str:
    """Build `/brains-<cmd> arg1 arg2 ...`. Whitespace-quotes args containing spaces."""
    quoted = [f'"{a}"' if " " in a else a for a in args if a]
    return f"/brains-{cmd} {' '.join(quoted)}".strip()


def copy_to_clipboard(text: str) -> bool:
    """Return True on success, False if pyperclip raised (e.g. no clipboard available)."""
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def log_handoff(cmd: str, command_str: str, note: str = "") -> Path:
    """Append a record to the handoff log directory. Return the file path."""
    HANDOFF_LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = HANDOFF_LOG_DIR / f"{ts}-{cmd}.txt"
    body = f"{command_str}\n\n{note}" if note else command_str
    path.write_text(body, encoding="utf-8")
    return path


def handoff(cmd: str, *args: str, note: str = "", log: bool = True) -> None:
    """One-call helper: build → copy → log → toast.

    Renders a Streamlit toast on success, or a warning + st.code block on
    clipboard failure. Must be called inside a Streamlit context (e.g. inside
    an `if st.button(...):` block).
    """
    command_str = build_command(cmd, *args)
    ok = copy_to_clipboard(command_str)
    if log:
        try:
            log_handoff(cmd, command_str, note=note)
        except Exception:
            pass  # log failure is non-fatal
    if ok:
        st.toast(f"Copied: {command_str}", icon="✅")
    else:
        st.warning("Clipboard unavailable — copy this command manually:")
        st.code(command_str, language="text")
    if note:
        st.caption(note)
