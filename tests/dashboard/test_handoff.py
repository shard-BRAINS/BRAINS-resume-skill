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
