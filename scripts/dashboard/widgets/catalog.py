"""The widget catalog — registers every widget and resolves saved layouts.

A Widget bundles display metadata with its render callable. WIDGET_CATALOG
order is the default display order. resolve_layout reconciles a candidate's
saved layout (from layout.py) against the current catalog.
"""
from dataclasses import dataclass
from typing import Callable, List, Tuple

from scripts.dashboard.widgets.playbook_widgets import (
    make_playbook_card_renderer, render_in_progress_runs,
)
from scripts.dashboard.widgets.worklist import render_worklist
from scripts.dashboard.widgets.pipeline import render_pipeline
from scripts.dashboard.widgets.tiles import (
    render_tile_pacing, render_tile_drift, render_tile_library_counts,
    render_tile_recent_outcomes,
)
from scripts.dashboard.widgets.quick_launch import render_quick_launch


@dataclass(frozen=True)
class Widget:
    """A canvas widget: display metadata + its render callable.

    render: a function (candidate) -> None.
    zone:   'upper' (playbooks/in-progress) or 'lower' (reporting).
    """
    key: str
    label: str
    zone: str
    default_enabled: bool
    render: Callable


WIDGET_CATALOG: Tuple[Widget, ...] = (
    Widget("in_progress_runs", "In progress", "upper", True,
           render_in_progress_runs),
    Widget("playbook_apply", "Apply to a job", "upper", True,
           make_playbook_card_renderer("apply_to_job")),
    Widget("playbook_build", "Build a base resume", "upper", True,
           make_playbook_card_renderer("build_resume")),
    Widget("playbook_improve", "Improve a resume", "upper", True,
           make_playbook_card_renderer("improve_resume")),
    Widget("playbook_linkedin", "Refresh LinkedIn", "upper", True,
           make_playbook_card_renderer("refresh_linkedin")),
    Widget("playbook_career_change", "Career change", "upper", True,
           make_playbook_card_renderer("career_change")),
    Widget("worklist", "Next actions", "lower", True, render_worklist),
    Widget("pipeline_mini", "Pipeline", "lower", True, render_pipeline),
    Widget("tile_pacing", "Pacing", "lower", True, render_tile_pacing),
    Widget("tile_drift", "Drift", "lower", True, render_tile_drift),
    Widget("tile_library_counts", "Library", "lower", True,
           render_tile_library_counts),
    Widget("quick_launch", "Quick launch", "lower", True, render_quick_launch),
    Widget("tile_recent_outcomes", "Recent outcomes", "lower", False,
           render_tile_recent_outcomes),
)

_BY_KEY = {w.key: w for w in WIDGET_CATALOG}


def get_widget(key: str) -> Widget:
    """Return the widget with the given key. Raises KeyError if unknown."""
    if key not in _BY_KEY:
        raise KeyError(f"Unknown widget: {key!r}")
    return _BY_KEY[key]


def resolve_layout(saved: List[Tuple[str, bool]]) -> List[Tuple[Widget, bool]]:
    """Reconcile a saved layout against the current catalog.

    - Known saved widgets keep their saved order and enabled flag.
    - Unknown saved keys are dropped.
    - Catalog widgets absent from the saved layout are appended in catalog
      order with their default_enabled flag.
    An empty saved layout therefore yields the full catalog with defaults.
    """
    result: List[Tuple[Widget, bool]] = []
    seen: set = set()
    for key, enabled in saved:
        if key in _BY_KEY and key not in seen:
            result.append((_BY_KEY[key], enabled))
            seen.add(key)
    for w in WIDGET_CATALOG:
        if w.key not in seen:
            result.append((w, w.default_enabled))
            seen.add(w.key)
    return result
