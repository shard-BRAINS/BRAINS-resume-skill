#!/usr/bin/env bash
# BRAINS Resume Skill installer for macOS and Linux.

set -euo pipefail

PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
SKIP_TESTS="${SKIP_TESTS:-0}"

echo "BRAINS Resume Skill installer"
echo "Project root: $PROJECT_ROOT"
echo ""

# Step 1 — Python check
echo "[1/6] Checking Python ..."
if ! command -v python3 > /dev/null 2>&1; then
  echo "ERROR: python3 not found on PATH." >&2
  exit 1
fi
PY_VERSION="$(python3 --version)"
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then
  echo "ERROR: Python 3.10 or later is required. Detected: $PY_VERSION" >&2
  exit 1
fi
echo "  OK: $PY_VERSION"

# Step 2 — Virtual environment
echo "[2/6] Creating virtual environment ..."
VENV_PATH="$PROJECT_ROOT/.venv"
if [ -d "$VENV_PATH" ]; then
  echo "  Already present, reusing."
else
  python3 -m venv "$VENV_PATH"
  echo "  Created at $VENV_PATH"
fi

# Step 3 — pip install
echo "[3/6] Installing dependencies ..."
PY_EXE="$VENV_PATH/bin/python"
"$PY_EXE" -m pip install --upgrade pip --quiet
"$PY_EXE" -m pip install -e "$PROJECT_ROOT[dev]" --quiet
echo "  Done."

# Step 4 — Skills directory symlink
echo "[4/6] Linking into Claude Code skills directory ..."
SKILLS_DIR="$HOME/.claude/skills"
LINK_PATH="$SKILLS_DIR/brains-resume"
mkdir -p "$SKILLS_DIR"
if [ -L "$LINK_PATH" ] || [ -d "$LINK_PATH" ]; then
  echo "  Already linked, skipping."
else
  ln -s "$PROJECT_ROOT" "$LINK_PATH"
  echo "  Symlinked: $LINK_PATH -> $PROJECT_ROOT"
fi

# Step 5 — Slash commands
echo "[5/6] Installing slash commands ..."
COMMANDS_SRC="$PROJECT_ROOT/commands"
COMMANDS_DST="$HOME/.claude/commands"
mkdir -p "$COMMANDS_DST"
if [ -d "$COMMANDS_SRC" ]; then
  cp "$COMMANDS_SRC"/*.md "$COMMANDS_DST/" 2>/dev/null || true
  echo "  Slash commands copied to $COMMANDS_DST"
else
  echo "  No commands/ directory found; skipping."
fi

# Step 6 — Tests
if [ "$SKIP_TESTS" = "1" ]; then
  echo "[6/6] Tests skipped per SKIP_TESTS=1."
else
  echo "[6/6] Running test suite ..."
  "$PY_EXE" -m pytest "$PROJECT_ROOT/tests" -q
fi

echo ""
echo "Install complete."
echo "Next steps:"
echo "  1. Start a new Claude Code session from any directory."
echo "  2. Try one of: /brains-review, /brains-disclosure, /brains-edit, /brains-tailor,"
echo "     /brains-cover-letter, /brains-create, /brains-linkedin, /brains-career-change,"
echo "     /brains-check"
echo "  3. Or invoke by natural language: 'review my resume at /path/to/resume.docx'"
