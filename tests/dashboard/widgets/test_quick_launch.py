"""Tests for the quick-launch widget."""
from scripts.dashboard.widgets.quick_launch import render_quick_launch, QUICK_LAUNCH_WORKFLOWS


def test_quick_launch_workflow_list():
    slugs = {w[0] for w in QUICK_LAUNCH_WORKFLOWS}
    assert slugs == {"jd_analyze", "deai", "disclosure", "track"}


def test_render_quick_launch_is_callable():
    assert callable(render_quick_launch)
