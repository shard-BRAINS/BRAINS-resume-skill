"""Verify all four existing workflows now cross-reference the tracker opt-in."""
from pathlib import Path

REF_DIR = Path(__file__).parent.parent.parent / "references" / "workflows"


WORKFLOWS_THAT_MUST_PROMPT = (
    "tailor.md",
    "cover-letter.md",
    "review.md",
    "bias-check.md",
)


def test_all_four_workflows_offer_tracker_optin():
    for fname in WORKFLOWS_THAT_MUST_PROMPT:
        text = (REF_DIR / fname).read_text(encoding="utf-8")
        assert "Application tracker" in text, (
            f"{fname} does not contain the tracker opt-in paragraph"
        )
        assert "opt-in" in text.lower() or "scripts/tracker" in text


def test_tailor_prompts_for_precheck():
    text = (REF_DIR / "tailor.md").read_text(encoding="utf-8")
    assert "pre-application" in text.lower() or "precheck" in text.lower()
