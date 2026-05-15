"""Tests for scripts.dashboard.handoff — clipboard + log helper."""
from pathlib import Path

import pytest


def test_build_command_no_args():
    from scripts.dashboard.handoff import build_command
    assert build_command("review") == "/brains-review"


def test_build_command_single_arg():
    from scripts.dashboard.handoff import build_command
    assert build_command("review", "C:/path/resume.docx") == "/brains-review C:/path/resume.docx"


def test_build_command_path_with_space_is_quoted():
    from scripts.dashboard.handoff import build_command
    assert build_command("tailor", "C:/Users/me/My Resume.docx", "https://jd.url") == '/brains-tailor "C:/Users/me/My Resume.docx" https://jd.url'


def test_build_command_filters_empty_args():
    from scripts.dashboard.handoff import build_command
    assert build_command("review", "", "C:/r.docx", "") == "/brains-review C:/r.docx"


def test_build_command_multiple_args():
    from scripts.dashboard.handoff import build_command
    assert build_command("consolidate", "C:/r.docx", "C:/li.zip") == "/brains-consolidate C:/r.docx C:/li.zip"


def test_copy_to_clipboard_success(monkeypatch):
    from scripts.dashboard import handoff
    captured = {}
    monkeypatch.setattr(handoff.pyperclip, "copy", lambda text: captured.setdefault("text", text))
    assert handoff.copy_to_clipboard("hello") is True
    assert captured["text"] == "hello"


def test_copy_to_clipboard_failure_returns_false(monkeypatch):
    from scripts.dashboard import handoff

    def raise_(*_args, **_kwargs):
        raise RuntimeError("no clipboard")

    monkeypatch.setattr(handoff.pyperclip, "copy", raise_)
    assert handoff.copy_to_clipboard("hello") is False


def test_log_handoff_writes_file(tmp_path, monkeypatch):
    from scripts.dashboard import handoff
    monkeypatch.setattr(handoff, "HANDOFF_LOG_DIR", tmp_path)
    result = handoff.log_handoff("review", "/brains-review C:/r.docx", note="audit")
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "/brains-review C:/r.docx" in content
    assert "audit" in content


def test_log_handoff_no_note(tmp_path, monkeypatch):
    from scripts.dashboard import handoff
    monkeypatch.setattr(handoff, "HANDOFF_LOG_DIR", tmp_path)
    result = handoff.log_handoff("deai", "/brains-deai")
    assert result.read_text(encoding="utf-8").strip() == "/brains-deai"


def test_log_handoff_creates_dir_if_missing(tmp_path, monkeypatch):
    from scripts.dashboard import handoff
    target = tmp_path / "nested" / "handoffs"
    monkeypatch.setattr(handoff, "HANDOFF_LOG_DIR", target)
    result = handoff.log_handoff("review", "/brains-review")
    assert target.exists()
    assert result.parent == target
