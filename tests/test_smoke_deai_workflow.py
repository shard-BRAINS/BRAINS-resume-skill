"""Smoke test for the deterministic portion of the de-AI workflow.

Exercises: ai_signal_check runs end-to-end on a heavily-AI fixture, score is
non-zero, findings have the expected fields, and a markdown report artifact
can be written without crashing.
"""
from pathlib import Path

from scripts.validators.ai_signal_check import ai_signal_check
from tests.fixtures import ai_signal_fixtures as fx


def test_deai_smoke(tmp_path):
    # (a) Scan a heavily-AI fixture
    result = ai_signal_check(fx.HEAVILY_AI_TEXT)
    assert result.score > 0
    assert result.score >= 60  # heavily-AI fixture should be solidly in the "heavy" band
    assert len(result.findings) >= 4

    # (b) Each finding has the public-API shape
    for f in result.findings:
        assert f.code
        assert f.severity in ("HIGH", "MEDIUM", "LOW")
        assert f.excerpt
        assert f.suggestion

    # (c) Render a markdown report (what the slash command will do at runtime)
    lines = [
        "# De-AI Report\n\n",
        f"**AI-signal score:** {result.score}/100\n\n",
        f"**Findings:** {len(result.findings)}\n\n",
        "---\n\n",
    ]
    for f in result.findings:
        lines.append(f"### {f.code} ({f.severity})\n\n")
        lines.append(f"**Excerpt:** {f.excerpt}\n\n")
        lines.append(f"**Suggestion:** {f.suggestion}\n\n")
    report = tmp_path / "deai-report-2026-05-14-120000.md"
    report.write_text("".join(lines), encoding="utf-8")

    assert report.exists()
    content = report.read_text(encoding="utf-8")
    assert "De-AI Report" in content
    assert "AI-signal score" in content


def test_deai_smoke_clean_text_zero_score(tmp_path):
    """A clean human-written fixture should produce zero findings and zero score."""
    result = ai_signal_check(fx.CLEAN_HUMAN_TEXT)
    assert result.score == 0
    assert result.findings == []
