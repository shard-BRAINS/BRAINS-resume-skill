"""Tests for the shared workflow-card helper."""
from pathlib import Path


def test_collect_args_filters_none_and_empty():
    from scripts.dashboard.workflows._card import collect_args
    assert collect_args([Path("a.docx"), None, "", "b.txt"]) == ["a.docx", "b.txt"]


def test_collect_args_stringifies_paths(tmp_path):
    from scripts.dashboard.workflows._card import collect_args
    p = tmp_path / "r.docx"
    p.write_bytes(b"")
    result = collect_args([p])
    assert result == [str(p)]


def test_collect_args_passes_strings_through():
    from scripts.dashboard.workflows._card import collect_args
    assert collect_args(["https://jd.url", "extra"]) == ["https://jd.url", "extra"]


def test_collect_args_all_none_returns_empty():
    from scripts.dashboard.workflows._card import collect_args
    assert collect_args([None, None]) == []
