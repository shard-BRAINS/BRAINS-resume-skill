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


@pytest.mark.parametrize("text,expected", [
    # Curly quotes (U+2018, U+2019) and modifier letter apostrophe (U+02BC).
    ("O’Brien", "OBrien"),
    ("’Acme’ Corp", "Acme-Corp"),
    ("Marʼa’s Resume", "Maras-Resume"),
])
def test_slugify_strips_curly_apostrophes(text, expected):
    assert slugify(text) == expected


from scripts.outputs.naming import new_uid, CROCKFORD_BASE32


def test_new_uid_length_is_6():
    assert len(new_uid()) == 6


def test_new_uid_uses_only_crockford_chars():
    for _ in range(100):
        uid = new_uid()
        assert set(uid).issubset(set(CROCKFORD_BASE32))


def test_new_uid_uniqueness_over_10k_samples():
    # 6 chars from a 30-char alphabet = ~729M possibilities.
    # 10k samples should yield 0 collisions in practice.
    samples = {new_uid() for _ in range(10_000)}
    assert len(samples) == 10_000


def test_new_uid_never_contains_ambiguous_chars():
    for _ in range(100):
        uid = new_uid()
        assert "0" not in uid
        assert "O" not in uid
        assert "1" not in uid
        assert "I" not in uid
        assert "L" not in uid
