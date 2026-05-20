"""Headline-changes formatter.

Selects ≤5 most salient changes across a drift score, ordered by
spec §5e priority. Pure function, no I/O.
"""
from __future__ import annotations


def _identity_lines(score: dict) -> list[str]:
    out = []
    info = score.get("identity") or {}
    for f in info.get("fields_changed") or []:
        out.append(f"Identity field changed: {f}")
    return out


def _exp_field_lines(score: dict) -> list[str]:
    info = score.get("experience") or {}
    return [
        f"Experience · {fc['entry_id']} · {fc['field']} changed"
        for fc in (info.get("field_changes") or [])
    ]


def _exp_entry_lines(score: dict) -> list[str]:
    info = score.get("experience") or {}
    out = []
    if info.get("entries_added"):
        out.append(f"{info['entries_added']} experience entries added")
    if info.get("entries_removed"):
        out.append(f"{info['entries_removed']} experience entries removed")
    return out


def _edu_field_lines(score: dict) -> list[str]:
    info = score.get("education") or {}
    return [
        f"Education · {fc['entry_id']} · {fc['field']} changed"
        for fc in (info.get("field_changes") or [])
    ]


def _edu_entry_lines(score: dict) -> list[str]:
    info = score.get("education") or {}
    out = []
    if info.get("entries_added"):
        out.append(f"{info['entries_added']} education entries added")
    if info.get("entries_removed"):
        out.append(f"{info['entries_removed']} education entries removed")
    return out


def _list_class_lines(score: dict, cls: str, label: str) -> list[str]:
    info = score.get(cls) or {}
    out = []
    if info.get("field_changes"):
        for fc in info["field_changes"]:
            out.append(f"{label} · {fc.get('entry_id', '?')} · {fc['field']} changed")
    if info.get("entries_added"):
        out.append(f"{info['entries_added']} {label.lower()} entries added")
    if info.get("entries_removed"):
        out.append(f"{info['entries_removed']} {label.lower()} entries removed")
    return out


def _set_class_lines(score: dict, cls: str, label: str) -> list[str]:
    info = score.get(cls) or {}
    out = []
    if info.get("added"):
        out.append(f"{len(info['added'])} {label.lower()} added")
    if info.get("removed"):
        out.append(f"{len(info['removed'])} {label.lower()} removed")
    return out


_PRIORITY_FNS = [
    _identity_lines,
    _exp_field_lines,
    _exp_entry_lines,
    _edu_field_lines,
    _edu_entry_lines,
    lambda s: _list_class_lines(s, "certifications", "Certifications"),
    lambda s: _list_class_lines(s, "languages", "Languages"),
    lambda s: _list_class_lines(s, "publications", "Publications"),
    lambda s: _set_class_lines(s, "skills", "Skills"),
    lambda s: _set_class_lines(s, "standalone_achievements", "Achievements"),
    lambda s: _list_class_lines(s, "portfolio_links", "Portfolio links"),
    lambda s: _set_class_lines(s, "hobbies", "Hobbies"),
]


def format_headline_changes(score: dict, limit: int = 5) -> list[str]:
    """Return up to `limit` human-readable headline change lines.

    Ordered by spec §5e priority. Skips classes with status 'not_captured'.
    """
    out: list[str] = []
    for fn in _PRIORITY_FNS:
        for line in fn(score):
            out.append(line)
            if len(out) >= limit:
                return out
    return out
