"""Tests for the Customize-mode reorder helper."""
from scripts.dashboard.widgets.customize import move_entry, render_customize


def test_move_entry_up():
    entries = [("a", True), ("b", True), ("c", True)]
    assert move_entry(entries, 1, "up") == [("b", True), ("a", True), ("c", True)]


def test_move_entry_down():
    entries = [("a", True), ("b", True), ("c", True)]
    assert move_entry(entries, 1, "down") == [("a", True), ("c", True), ("b", True)]


def test_move_entry_up_at_top_is_noop():
    entries = [("a", True), ("b", True)]
    assert move_entry(entries, 0, "up") == [("a", True), ("b", True)]


def test_move_entry_down_at_bottom_is_noop():
    entries = [("a", True), ("b", True)]
    assert move_entry(entries, 1, "down") == [("a", True), ("b", True)]


def test_move_entry_does_not_mutate_input():
    entries = [("a", True), ("b", True)]
    move_entry(entries, 1, "up")
    assert entries == [("a", True), ("b", True)]


def test_render_customize_is_callable():
    assert callable(render_customize)
