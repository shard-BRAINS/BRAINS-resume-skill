"""Tests for scripts/outputs/naming.py — pure naming/sanitization functions."""
import pytest

from scripts.outputs.naming import slugify


@pytest.mark.parametrize("text,expected", [
    ("Senior Data Engineer", "Senior-Data-Engineer"),
    ("R&D / Platform", "R-D-Platform"),
    ("Engineer (Sydney)", "Engineer-Sydney"),
    ("O'Brien & Co.", "OBrien-Co"),
    ("AI/ML — Lead", "AI-ML-Lead"),
    ("Acme   Corp", "Acme-Corp"),
    ("—Acme—", "Acme"),
    ("", ""),
    ("---", ""),
    ("a", "a"),
])
def test_slugify_table(text, expected):
    assert slugify(text) == expected


def test_slugify_max_len_truncates_at_word_boundary():
    # "Senior Software Engineer" -> truncate to 18: cut mid-word would
    # produce "Senior-Software-En"; we strip trailing partial token cleanly.
    assert slugify("Senior Software Engineer", max_len=18) == "Senior-Software-En"


def test_slugify_max_len_strips_trailing_hyphen():
    # Exact truncation that lands on a hyphen should not leave one trailing.
    assert slugify("Senior Software Engineer", max_len=15) == "Senior-Software"


def test_slugify_default_max_len_is_40():
    long_text = "a" * 100
    assert len(slugify(long_text)) == 40
