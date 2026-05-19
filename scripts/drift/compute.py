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

import re as _re
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


_IDENTITY_FIELDS = ("name", "location", "email", "phone")


def _identity_diff(left: dict, right: dict) -> dict:
    left = left or {}
    right = right or {}
    fields_changed = []
    for f in _IDENTITY_FIELDS:
        if (left.get(f) or None) != (right.get(f) or None):
            fields_changed.append(f)
    total = len(_IDENTITY_FIELDS)
    pct = (len(fields_changed) / total) * 100.0 if total else 0.0
    return {"fields_changed": fields_changed, "fields_total": total, "pct": pct}


def _jaccard_with_prefix(a: str, b: str) -> float:
    """Greedy token-set Jaccard with prefix-aware matching.

    Tokens are lowercased, trailing punctuation stripped. Two tokens are
    considered "matched" if they are equal OR one is a prefix of the
    other (both at least 3 chars). This handles abbreviations such as
    "Corp." vs "Corporation".
    """
    aw = [t.rstrip(".,;:") for t in (a or "").lower().split()]
    bw = [t.rstrip(".,;:") for t in (b or "").lower().split()]
    if not aw and not bw:
        return 1.0
    if not aw or not bw:
        return 0.0
    matched = 0
    used_b = [False] * len(bw)
    for ta in aw:
        for i, tb in enumerate(bw):
            if used_b[i]:
                continue
            if ta == tb or (
                len(ta) >= 3 and len(tb) >= 3
                and (ta.startswith(tb) or tb.startswith(ta))
            ):
                matched += 1
                used_b[i] = True
                break
    union = len(aw) + len(bw) - matched
    return matched / union if union else 1.0


def _token_set_ratio(a: str, b: str) -> float:
    """Token-set similarity in [0, 1].

    Uses rapidfuzz.fuzz.token_set_ratio when available for character-level
    fuzziness, AND a prefix-aware Jaccard for abbreviation handling.
    Returns the max of the two so we benefit from both regardless of
    whether rapidfuzz is installed.
    """
    prefix_score = _jaccard_with_prefix(a or "", b or "")
    try:
        from rapidfuzz.fuzz import token_set_ratio  # type: ignore
        return max(prefix_score, token_set_ratio(a or "", b or "") / 100.0)
    except ImportError:
        return prefix_score


def _canonicalise_url(url: str) -> str:
    """Lowercase, strip http(s)://, strip trailing /."""
    if not url:
        return ""
    s = url.strip().lower()
    s = _re.sub(r"^https?://", "", s)
    s = s.rstrip("/")
    return s


def _natural_key(entry: dict, kind: str) -> tuple | str | None:
    if kind == "experience":
        if not entry.get("employer") or not entry.get("start_date"):
            return None
        return (entry["employer"].strip().lower(), entry["start_date"])
    if kind == "education":
        if not entry.get("institution") or not entry.get("qualification"):
            return None
        return (entry["institution"].strip().lower(),
                entry["qualification"].strip().lower())
    if kind == "certifications":
        if not entry.get("name"):
            return None
        return entry["name"].strip().lower()
    if kind == "languages":
        if not entry.get("language"):
            return None
        return entry["language"].strip().lower()
    if kind == "publications":
        if not entry.get("title"):
            return None
        return (entry["title"].strip().lower(), entry.get("year") or "")
    if kind == "portfolio_links":
        if not entry.get("url"):
            return None
        return _canonicalise_url(entry["url"])
    raise ValueError(f"No natural key for kind {kind!r}")


_FUZZY_FIELDS = {
    "experience": (["employer", "title"], 0.85),
    "education": (["institution"], 0.85),
    "certifications": (["name"], 0.85),
    "languages": (["language"], 0.90),
    "publications": (["title"], 0.85),
    "portfolio_links": (None, None),  # exact-only via canonicalised URL
}


_COMPARE_FIELDS = {
    "experience": ("employer", "title", "start_date", "end_date", "location", "key_points"),
    "education":  ("institution", "qualification", "completion_year",
                   "completion_status", "honours"),
    "certifications": ("name", "issuer", "year"),
    "languages": ("language", "proficiency"),
    "publications": ("title", "venue", "year", "authors", "url"),
    "portfolio_links": ("label", "url"),
}


def _fuzzy_match(target: dict, candidates: list[dict], kind: str) -> int | None:
    """Return index in candidates of best fuzzy match, or None if below threshold.

    Used when natural-key match fails. Compares specified text fields.
    """
    fields, threshold = _FUZZY_FIELDS[kind]
    if fields is None:
        return None
    best_idx = None
    best_score = 0.0
    for i, cand in enumerate(candidates):
        scores = [_token_set_ratio(target.get(f, "") or "", cand.get(f, "") or "")
                  for f in fields]
        score = min(scores) if scores else 0.0
        if score > best_score and score >= threshold:
            best_idx = i
            best_score = score
    return best_idx


def _compare_entries(left: dict, right: dict, kind: str, entry_id: str) -> list[dict]:
    """Per-field comparison. Returns list of {entry_id, field, from, to}."""
    changes = []
    for f in _COMPARE_FIELDS[kind]:
        l_val = left.get(f)
        r_val = right.get(f)
        if (l_val or None) != (r_val or None):
            changes.append({"entry_id": entry_id, "field": f,
                            "from": l_val, "to": r_val})
    return changes


def _list_object_diff(left: list[dict], right: list[dict], kind: str) -> dict:
    left = list(left or [])
    right = list(right or [])

    # Build natural-key indices.
    left_by_key: dict = {}
    left_unkeyed: list[int] = []
    for i, e in enumerate(left):
        k = _natural_key(e, kind)
        if k is None:
            left_unkeyed.append(i)
        else:
            left_by_key.setdefault(k, []).append(i)

    right_consumed = [False] * len(right)
    left_consumed = [False] * len(left)
    field_changes: list[dict] = []
    entries_with_field_changes = 0

    # Pass 1: natural-key matches.
    for j, r_entry in enumerate(right):
        rk = _natural_key(r_entry, kind)
        if rk is None:
            continue
        bucket = left_by_key.get(rk)
        if not bucket:
            continue
        i = bucket.pop(0)
        left_consumed[i] = True
        right_consumed[j] = True
        changes = _compare_entries(left[i], r_entry, kind,
                                   left[i].get("entry_id") or r_entry.get("entry_id") or f"{kind}-{i}")
        if changes:
            entries_with_field_changes += 1
            field_changes.extend(changes)

    # Pass 2: fuzzy fallback for the unmatched.
    unmatched_left = [i for i, used in enumerate(left_consumed) if not used]
    unmatched_right = [j for j, used in enumerate(right_consumed) if not used]
    for j in list(unmatched_right):
        cand_idxs = [i for i in unmatched_left if not left_consumed[i]]
        candidates = [left[i] for i in cand_idxs]
        m = _fuzzy_match(right[j], candidates, kind)
        if m is None:
            continue
        i = cand_idxs[m]
        left_consumed[i] = True
        right_consumed[j] = True
        changes = _compare_entries(left[i], right[j], kind,
                                   left[i].get("entry_id") or right[j].get("entry_id") or f"{kind}-{i}")
        if changes:
            entries_with_field_changes += 1
            field_changes.extend(changes)

    entries_removed = sum(1 for u in left_consumed if not u)
    entries_added = sum(1 for u in right_consumed if not u)

    total = max(len(left), len(right))
    if total == 0:
        return {"entries_added": 0, "entries_removed": 0,
                "entries_with_field_changes": 0,
                "field_changes": [], "entries_total": 0, "pct": 0.0}
    changed_units = entries_added + entries_removed + entries_with_field_changes
    pct = (changed_units / total) * 100.0
    return {
        "entries_added": entries_added,
        "entries_removed": entries_removed,
        "entries_with_field_changes": entries_with_field_changes,
        "field_changes": field_changes,
        "entries_total": total,
        "pct": pct,
    }


_LIST_OBJECT_KINDS = ("experience", "education", "certifications",
                     "languages", "publications", "portfolio_links")


def compute_class_diff(left: Any, right: Any, kind: str) -> dict:
    """Compute the per-class diff dict for a single class.

    kind: one of 'set', 'identity', or any of the list-of-object classes:
          experience, education, certifications, languages, publications,
          portfolio_links.

    Returns {'status': 'not_captured', 'pct': None} if either side is None
    (spec §5b — null-class handling). [] is NOT the same as None.
    """
    if left is None or right is None:
        return _null_status()
    if kind == "set":
        return _set_diff(left, right)
    if kind == "identity":
        return _identity_diff(left, right)
    if kind in _LIST_OBJECT_KINDS:
        return _list_object_diff(left, right, kind)
    raise ValueError(f"Unknown class kind: {kind!r}")


DRIFT_CLASS_WEIGHTS = {
    "identity": 0.20,
    "experience": 0.25,
    "education": 0.12,
    "skills": 0.08,
    "certifications": 0.08,
    "standalone_achievements": 0.06,
    "hobbies": 0.04,
    "languages": 0.07,
    "publications": 0.06,
    "portfolio_links": 0.04,
}

_CLASS_KIND = {
    "identity": "identity",
    "experience": "experience",
    "education": "education",
    "skills": "set",
    "certifications": "certifications",
    "standalone_achievements": "set",
    "hobbies": "set",
    "languages": "languages",
    "publications": "publications",
    "portfolio_links": "portfolio_links",
}


def compute_drift_score(left: dict, right: dict) -> dict:
    """Compute the full per-class + overall drift between two snapshots.

    See spec §5d for the weighted aggregate with null-class renormalisation.
    Both snapshots must use schema_version 1 (Section 4).
    """
    out: dict = {}
    captured_weights_sum = 0.0
    weighted_total = 0.0
    for cls, kind in _CLASS_KIND.items():
        diff = compute_class_diff(left.get(cls), right.get(cls), kind=kind)
        out[cls] = diff
        if diff.get("status") == "not_captured":
            continue
        weight = DRIFT_CLASS_WEIGHTS[cls]
        captured_weights_sum += weight
        weighted_total += weight * diff["pct"]

    if captured_weights_sum > 0:
        overall_pct = weighted_total / captured_weights_sum
    else:
        overall_pct = 0.0
    out["overall_pct"] = round(overall_pct, 2)

    # Headline changes — delegated to formatters.format_headline_changes.
    from scripts.drift.formatters import format_headline_changes
    out["headline_changes"] = format_headline_changes(out)
    return out


import json as _json
from datetime import datetime as _datetime


def _now_iso() -> str:
    return _datetime.utcnow().isoformat() + "Z"


def write_snapshot_and_compute_drift(artifact_uid: str, facts: dict) -> None:
    """Persist the snapshot, look up parent + baseline, compute and persist scores.

    Idempotent on artifact_uid — uses INSERT OR REPLACE so calling twice for the
    same UID overwrites cleanly.

    The baseline-relative score is NULL when this row IS the baseline (looked up
    by checking is_baseline on the resume_versions row).
    """
    from scripts.drift.lineage import get_parent_snapshot, get_baseline_snapshot
    from scripts.tracker.db import open_db

    conn = open_db()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO resume_fact_snapshots "
            "(artifact_uid, facts, schema_version, created_at) "
            "VALUES (?, ?, ?, ?)",
            (artifact_uid, _json.dumps(facts), 1, _now_iso()),
        )

        # Determine whether this row IS the baseline.
        row = conn.execute(
            "SELECT is_baseline FROM resume_versions WHERE artifact_uid=?",
            (artifact_uid,),
        ).fetchone()
        is_baseline = bool(row and row[0])

        parent_snap = None if is_baseline else get_parent_snapshot(artifact_uid)
        # For non-baseline rows, baseline_snap is the active baseline's facts.
        baseline_snap = None if is_baseline else get_baseline_snapshot(artifact_uid)

        vs_parent = (compute_drift_score(parent_snap, facts)
                     if parent_snap is not None else None)
        vs_baseline = (compute_drift_score(baseline_snap, facts)
                       if baseline_snap is not None else None)

        conn.execute(
            "INSERT OR REPLACE INTO resume_drift_scores "
            "(artifact_uid, vs_parent_score, vs_baseline_score, computed_at) "
            "VALUES (?, ?, ?, ?)",
            (
                artifact_uid,
                _json.dumps(vs_parent) if vs_parent is not None else None,
                _json.dumps(vs_baseline) if vs_baseline is not None else None,
                _now_iso(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
