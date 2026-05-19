"""Drift compute — pure-Python per-class diff + weighted overall_pct.

See spec §5 for the formula. Compute is split into per-class helpers:
- compute_class_diff(left, right, kind=...) — single class diff.
- compute_drift_score(left_facts, right_facts) — full snapshot diff.
- write_snapshot_and_compute_drift(artifact_uid, facts) — persistence wrapper.

This file is grown incrementally across Tasks 4-9. This is the set-shape
branch (Task 4); identity (Task 5), list-of-object (Task 6), and the
overall_pct aggregator (Task 7) extend it.
"""
from __future__ import annotations

from typing import Any


def _null_status() -> dict:
    return {"status": "not_captured", "pct": None}


def _set_diff(left: list, right: list) -> dict:
    left_set = list(left or [])
    right_set = list(right or [])
    added = [x for x in right_set if x not in left_set]
    removed = [x for x in left_set if x not in right_set]
    total = max(len(left_set), len(right_set))
    if total == 0:
        return {"added": [], "removed": [], "total": 0, "pct": 0.0}
    changed = len(added) + len(removed)
    pct = (changed / total) * 100.0
    return {"added": added, "removed": removed, "total": total, "pct": pct}


def compute_class_diff(left: Any, right: Any, kind: str) -> dict:
    """Compute the per-class diff dict for a single class.

    kind: one of 'set' (set-shaped: list[str]).
          'identity', 'list_object' added in later tasks.

    Returns {'status': 'not_captured', 'pct': None} if either side is None
    (spec §5b — null-class handling).
    """
    if left is None or right is None:
        return _null_status()

    if kind == "set":
        return _set_diff(left, right)
    raise ValueError(f"Unknown class kind: {kind!r}")
