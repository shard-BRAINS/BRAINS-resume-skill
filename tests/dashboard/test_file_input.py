"""Tests for scripts.dashboard.file_input — three-way file picker resolution."""
from pathlib import Path

import pytest


def test_resolve_path_dropdown_wins(tmp_path):
    from scripts.dashboard.file_input import resolve_path
    dropdown_pick = tmp_path / "from-dropdown.docx"
    dropdown_pick.write_bytes(b"")
    text_input = tmp_path / "from-text.docx"
    text_input.write_bytes(b"")
    result = resolve_path(dropdown_value=str(dropdown_pick), text_value=str(text_input), upload=None, upload_dir=tmp_path)
    assert result == dropdown_pick


def test_resolve_path_text_used_when_dropdown_placeholder(tmp_path):
    from scripts.dashboard.file_input import resolve_path
    text_input = tmp_path / "from-text.docx"
    text_input.write_bytes(b"")
    result = resolve_path(dropdown_value="(select a file...)", text_value=str(text_input), upload=None, upload_dir=tmp_path)
    assert result == text_input


def test_resolve_path_text_skipped_if_missing(tmp_path):
    from scripts.dashboard.file_input import resolve_path
    result = resolve_path(dropdown_value=None, text_value=str(tmp_path / "nope.docx"), upload=None, upload_dir=tmp_path)
    assert result is None


def test_resolve_path_upload_saved(tmp_path):
    from scripts.dashboard.file_input import resolve_path

    class FakeUpload:
        name = "upload.docx"
        def getbuffer(self):
            return b"upload-content"

    result = resolve_path(dropdown_value=None, text_value="", upload=FakeUpload(), upload_dir=tmp_path)
    assert result is not None
    assert result.name == "upload.docx"
    assert result.read_bytes() == b"upload-content"


def test_resolve_path_returns_none_when_all_empty(tmp_path):
    from scripts.dashboard.file_input import resolve_path
    result = resolve_path(dropdown_value=None, text_value="", upload=None, upload_dir=tmp_path)
    assert result is None


def test_resolve_path_dropdown_placeholder_string(tmp_path):
    from scripts.dashboard.file_input import resolve_path
    result = resolve_path(dropdown_value="(select a file...)", text_value="", upload=None, upload_dir=tmp_path)
    assert result is None


def test_is_docx_path():
    from scripts.dashboard.file_input import is_docx
    assert is_docx(Path("foo.docx")) is True
    assert is_docx(Path("foo.DOCX")) is True
    assert is_docx(Path("foo.pdf")) is False
    assert is_docx(Path("foo.txt")) is False


def test_is_pdf_path():
    from scripts.dashboard.file_input import is_pdf
    assert is_pdf(Path("foo.pdf")) is True
    assert is_pdf(Path("foo.PDF")) is True
    assert is_pdf(Path("foo.docx")) is False
