"""Funnel-chart data computation for the Overview tab.

Counts applications and the stages they have advanced to. Each application
contributes once to "Applications". An application with a callback event
contributes to "Callbacks". Interview events (phone_screen / first_round /
second_round / take_home) contribute to "Interviews". Offers and rejections
are terminal categories. Ghosted/withdrew are terminal but don't advance.

Pure function — no Streamlit imports, no I/O.
"""
from typing import List


INTERVIEW_EVENT_TYPES = {"phone_screen", "first_round", "second_round", "take_home"}


def compute_funnel_data(rows: List) -> dict:
    """Aggregate ApplicationRow objects into funnel-stage counts.

    Returns a dict with keys in funnel order: Applications, Callbacks,
    Interviews, Offers, Rejections.
    """
    counts = {
        "Applications": len(rows),
        "Callbacks": 0,
        "Interviews": 0,
        "Offers": 0,
        "Rejections": 0,
    }
    for r in rows:
        outcome = getattr(r, "latest_outcome", None)
        if outcome == "callback":
            counts["Callbacks"] += 1
        elif outcome in INTERVIEW_EVENT_TYPES:
            counts["Interviews"] += 1
        elif outcome == "offer":
            counts["Offers"] += 1
        elif outcome == "rejection":
            counts["Rejections"] += 1
    return counts
