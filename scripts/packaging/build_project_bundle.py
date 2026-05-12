"""Build a Claude Project bundle: a ZIP for claude.ai Projects users.

The bundle contains:
  - SKILL.md (the workflow router and cross-cutting principles)
  - references/ (all reference docs)
  - templates/ (markdown templates only — DOCX templates require local Python)
  - docs/claude-project-setup.md (setup guide)
  - A README explaining the limitations vs. Claude Code

It does NOT contain:
  - Python scripts (claude.ai cannot execute them)
  - Tests
  - install/ scripts
  - commands/ slash commands (Claude Code-only)
  - .venv/, .git/, output/, user_data/

Output: dist/brains-resume-claude-project.zip
"""
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUNDLE_PATH = DIST_DIR / "brains-resume-claude-project.zip"


INCLUDED_PATHS = [
    "SKILL.md",
    "references",
    "docs/claude-project-setup.md",
    "templates/coaching_report.md",
    "LICENSE",
]


def build_bundle() -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    if BUNDLE_PATH.exists():
        BUNDLE_PATH.unlink()

    with zipfile.ZipFile(BUNDLE_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in INCLUDED_PATHS:
            src = PROJECT_ROOT / rel
            if not src.exists():
                print(f"  WARN: missing {rel}, skipping")
                continue
            if src.is_dir():
                for p in src.rglob("*"):
                    if p.is_file():
                        arcname = "brains-resume-claude-project/" + str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")
                        zf.write(p, arcname)
            else:
                arcname = "brains-resume-claude-project/" + rel.replace("\\", "/")
                zf.write(src, arcname)

        readme = (
            "# BRAINS Resume Skill — Claude Project Bundle\n\n"
            "This bundle is for use with the Claude Project feature on claude.ai.\n\n"
            "See `docs/claude-project-setup.md` for setup instructions.\n\n"
            "Built by neurodivergent minds, for neurodivergent people.\n"
        )
        zf.writestr("brains-resume-claude-project/README.md", readme)

    return BUNDLE_PATH


if __name__ == "__main__":
    path = build_bundle()
    print(f"Wrote {path}")
