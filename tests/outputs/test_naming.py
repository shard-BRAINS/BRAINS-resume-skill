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


def test_new_uid_distinct_within_small_batch():
    # 6 chars from a 30-char alphabet = ~729M possibilities.
    # 1000 samples from a ~729M space: birthday-paradox collision
    # probability is ~0.00007%. Effectively zero flake rate.
    samples = {new_uid() for _ in range(1000)}
    assert len(samples) == 1000


def test_new_uid_never_contains_ambiguous_chars():
    for _ in range(100):
        uid = new_uid()
        assert "0" not in uid
        assert "O" not in uid
        assert "1" not in uid
        assert "I" not in uid
        assert "L" not in uid


from datetime import date

from scripts.outputs.naming import folder_name


def test_folder_name_company_known():
    assert folder_name(
        jd_date=date(2026, 5, 18),
        company="Acme Corp",
        recruiter=None,
        role_title="Senior Data Engineer",
    ) == "2026-05-18_Acme-Corp_Senior-Data-Engineer"


def test_folder_name_recruiter_only():
    assert folder_name(
        jd_date=date(2026, 5, 18),
        company=None,
        recruiter="Hays",
        role_title="Senior Data Engineer",
    ) == "2026-05-18_via-Hays_Senior-Data-Engineer"


def test_folder_name_both_prefers_company():
    assert folder_name(
        jd_date=date(2026, 5, 18),
        company="Acme Corp",
        recruiter="Hays",
        role_title="Senior Data Engineer",
    ) == "2026-05-18_Acme-Corp_Senior-Data-Engineer"


def test_folder_name_neither():
    assert folder_name(
        jd_date=date(2026, 5, 18),
        company=None,
        recruiter=None,
        role_title="Senior Data Engineer",
    ) == "2026-05-18_unknown_Senior-Data-Engineer"


def test_folder_name_empty_company_treated_as_none():
    assert folder_name(
        jd_date=date(2026, 5, 18),
        company="",
        recruiter="Hays",
        role_title="Senior Data Engineer",
    ) == "2026-05-18_via-Hays_Senior-Data-Engineer"


def test_folder_name_caps_at_80_chars():
    long_role = "A" * 200
    result = folder_name(
        jd_date=date(2026, 5, 18),
        company="Acme",
        recruiter=None,
        role_title=long_role,
    )
    assert len(result) <= 80
    assert result.startswith("2026-05-18_Acme_")


def test_folder_name_sanitizes_company_and_role():
    assert folder_name(
        jd_date=date(2026, 5, 18),
        company="R&D / Platform Ltd.",
        recruiter=None,
        role_title="AI/ML — Lead",
    ) == "2026-05-18_R-D-Platform-Ltd_AI-ML-Lead"


from scripts.outputs.naming import artifact_filename


def test_artifact_filename_resume():
    assert artifact_filename(
        first_name="Matthew",
        last_name="Gell",
        kind="resume",
        created_date=date(2026, 5, 19),
        uid="KX7M9Q",
    ) == "Matthew_Gell_resume_2026-05-19_KX7M9Q.docx"


def test_artifact_filename_cover_letter():
    assert artifact_filename(
        first_name="Matthew",
        last_name="Gell",
        kind="cover-letter",
        created_date=date(2026, 5, 19),
        uid="H8VR3W",
    ) == "Matthew_Gell_cover-letter_2026-05-19_H8VR3W.docx"


def test_artifact_filename_pdf_extension():
    assert artifact_filename(
        first_name="Matthew",
        last_name="Gell",
        kind="resume",
        created_date=date(2026, 5, 19),
        uid="KX7M9Q",
        ext="pdf",
    ) == "Matthew_Gell_resume_2026-05-19_KX7M9Q.pdf"


def test_artifact_filename_sanitizes_name_with_space():
    # "Mary Anne" first name becomes "Mary-Anne" — names with spaces.
    assert artifact_filename(
        first_name="Mary Anne",
        last_name="O'Brien",
        kind="resume",
        created_date=date(2026, 5, 19),
        uid="KX7M9Q",
    ) == "Mary-Anne_OBrien_resume_2026-05-19_KX7M9Q.docx"


def test_artifact_filename_invalid_kind_raises():
    with pytest.raises(ValueError, match="kind must be"):
        artifact_filename(
            first_name="Matthew", last_name="Gell",
            kind="report",  # not allowed
            created_date=date(2026, 5, 19),
            uid="KX7M9Q",
        )


from scripts.outputs.naming import resolve_folder_collision


def test_resolve_folder_collision_no_existing(tmp_path):
    assert resolve_folder_collision(tmp_path, "abc") == "abc"


def test_resolve_folder_collision_one_existing(tmp_path):
    (tmp_path / "abc").mkdir()
    assert resolve_folder_collision(tmp_path, "abc") == "abc_v2"


def test_resolve_folder_collision_chain(tmp_path):
    (tmp_path / "abc").mkdir()
    (tmp_path / "abc_v2").mkdir()
    (tmp_path / "abc_v3").mkdir()
    assert resolve_folder_collision(tmp_path, "abc") == "abc_v4"
