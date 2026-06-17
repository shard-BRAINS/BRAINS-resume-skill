"""Customize mode — edit which widgets show on the Home canvas and in what
order. Persists via layout.save_layout; reset via layout.clear_layout.
"""
from typing import List, Tuple

import streamlit as st

from scripts.dashboard.widgets.catalog import resolve_layout
from scripts.dashboard.widgets.layout import (
    get_saved_layout, save_layout, clear_layout,
)


def move_entry(entries: List[Tuple[str, bool]], index: int,
               direction: str) -> List[Tuple[str, bool]]:
    """Return a new list with the entry at `index` moved one slot up or down.
    Out-of-range moves are a no-op. Does not mutate the input."""
    result = list(entries)
    if direction == "up" and index > 0:
        result[index - 1], result[index] = result[index], result[index - 1]
    elif direction == "down" and index < len(result) - 1:
        result[index + 1], result[index] = result[index], result[index + 1]
    return result


def render_customize(candidate) -> None:
    """Render the Customize editor for the active candidate."""
    st.caption("Toggle widgets on/off and reorder them. Saved per candidate.")
    resolved = resolve_layout(get_saved_layout(candidate.id))
    entries: List[Tuple[str, bool]] = [(w.key, en) for w, en in resolved]
    labels = {w.key: w.label for w, _ in resolved}

    for idx, (key, enabled) in enumerate(entries):
        cols = st.columns([3, 1, 1])
        with cols[0]:
            new_enabled = st.checkbox(
                labels.get(key, key), value=enabled, key=f"cz_en_{key}"
            )
            if new_enabled != enabled:
                save_layout(candidate.id,
                            [(k, new_enabled if k == key else e)
                             for k, e in entries])
                st.rerun()
        with cols[1]:
            if st.button("↑", key=f"cz_up_{key}") and idx > 0:
                save_layout(candidate.id, move_entry(entries, idx, "up"))
                st.rerun()
        with cols[2]:
            if st.button("↓", key=f"cz_dn_{key}") and idx < len(entries) - 1:
                save_layout(candidate.id, move_entry(entries, idx, "down"))
                st.rerun()

    if st.button("Reset to default", key="cz_reset"):
        clear_layout(candidate.id)
        st.rerun()
