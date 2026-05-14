"""Verify the four text-producing workflows now mention the de-AI check."""
from pathlib import Path

REF_DIR = Path(__file__).parent.parent.parent / "references" / "workflows"


WORKFLOWS_THAT_MUST_MENTION_DEAI = (
    "bias-check.md",
    "tailor.md",
    "cover-letter.md",
    "linkedin-improve.md",
    "edit.md",
)


def test_all_five_workflows_mention_ai_signal_check():
    for fname in WORKFLOWS_THAT_MUST_MENTION_DEAI:
        text = (REF_DIR / fname).read_text(encoding="utf-8")
        assert "ai_signal_check" in text, (
            f"{fname} does not invoke ai_signal_check"
        )


def test_bias_check_runs_deai_automatically():
    """bias-check should auto-invoke ai_signal_check (not just mention it as optional)."""
    text = (REF_DIR / "bias-check.md").read_text(encoding="utf-8")
    assert "auto" in text.lower() or "automatically" in text.lower()


def test_four_workflows_offer_optional_deai():
    """tailor, cover-letter, linkedin-improve, edit — all four should describe de-AI as optional."""
    for fname in ("tailor.md", "cover-letter.md", "linkedin-improve.md", "edit.md"):
        text = (REF_DIR / fname).read_text(encoding="utf-8")
        assert "De-AI check (optional)" in text or "(optional)" in text


def test_ai_signal_patterns_reference_cross_linked():
    for fname in WORKFLOWS_THAT_MUST_MENTION_DEAI:
        text = (REF_DIR / fname).read_text(encoding="utf-8")
        assert "ai-signal-patterns.md" in text
