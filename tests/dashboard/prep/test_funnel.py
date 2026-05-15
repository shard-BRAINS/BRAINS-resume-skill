"""Tests for scripts/dashboard/prep/funnel.py — funnel-chart data computation."""
from scripts.dashboard.prep.funnel import compute_funnel_data


def _row(latest_outcome=None):
    """Small ApplicationRow stand-in for testing."""
    class _Row:
        pass
    r = _Row()
    r.latest_outcome = latest_outcome
    return r


def test_empty_input_returns_zero_funnel():
    data = compute_funnel_data([])
    assert data["Applications"] == 0
    assert data["Callbacks"] == 0
    assert data["Interviews"] == 0
    assert data["Offers"] == 0
    assert data["Rejections"] == 0


def test_application_counted():
    data = compute_funnel_data([_row()])
    assert data["Applications"] == 1
    assert data["Callbacks"] == 0


def test_callback_counted():
    data = compute_funnel_data([_row(latest_outcome="callback")])
    assert data["Applications"] == 1
    assert data["Callbacks"] == 1


def test_interview_events_count_as_interview_stage():
    rows = [
        _row(latest_outcome="phone_screen"),
        _row(latest_outcome="first_round"),
        _row(latest_outcome="second_round"),
        _row(latest_outcome="take_home"),
    ]
    data = compute_funnel_data(rows)
    assert data["Applications"] == 4
    assert data["Interviews"] == 4


def test_offer_counted():
    data = compute_funnel_data([_row(latest_outcome="offer")])
    assert data["Applications"] == 1
    assert data["Offers"] == 1


def test_rejection_counted():
    data = compute_funnel_data([_row(latest_outcome="rejection")])
    assert data["Applications"] == 1
    assert data["Rejections"] == 1


def test_ghosted_and_withdrew_not_counted_in_funnel_advance_stages():
    """Ghosted/withdrew are terminal but don't advance the funnel."""
    rows = [
        _row(latest_outcome="ghosted"),
        _row(latest_outcome="withdrew"),
    ]
    data = compute_funnel_data(rows)
    assert data["Applications"] == 2
    assert data["Callbacks"] == 0
    assert data["Interviews"] == 0
    assert data["Offers"] == 0
    assert data["Rejections"] == 0


def test_funnel_data_keys_in_expected_order():
    """The returned dict should iterate in funnel-stage order for chart rendering."""
    data = compute_funnel_data([])
    assert list(data.keys()) == [
        "Applications", "Callbacks", "Interviews", "Offers", "Rejections",
    ]
