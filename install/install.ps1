<#
.SYNOPSIS
  BRAINS Resume Skill installer for Windows.

.DESCRIPTION
  Sets up the BRAINS Resume Skill in your local Claude Code environment.

  Steps performed:
    1. Verifies Python 3.10+ is on PATH
    2. Creates the project virtual environment (.venv)
    3. Installs the project in editable mode with dev extras
    4. Creates ~/.claude/skills/brains-resume as a junction to this directory
    5. Copies slash-command definitions to ~/.claude/commands/
    6. Runs the test suite to verify

  Re-run is safe: existing junctions and venvs are detected and not duplicated.

.EXAMPLE
  PS> .\install\install.ps1
#>

param(
  [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path

Write-Host "BRAINS Resume Skill installer"
Write-Host "Project root: $ProjectRoot"
Write-Host ""

# Step 1 — Python check
Write-Host "[1/6] Checking Python ..."
$pyVersion = (python --version 2>&1) | Out-String
if ($pyVersion -notmatch "Python 3\.(1[0-9]|[2-9][0-9])") {
    Write-Error "Python 3.10 or later is required. Detected: $pyVersion"
    exit 1
}
Write-Host "  OK: $pyVersion"

# Step 2 — Virtual environment
Write-Host "[2/6] Creating virtual environment ..."
$venvPath = Join-Path $ProjectRoot ".venv"
if (Test-Path $venvPath) {
    Write-Host "  Already present, reusing."
} else {
    python -m venv $venvPath
    Write-Host "  Created at $venvPath"
}

# Step 3 — pip install
Write-Host "[3/6] Installing dependencies ..."
$pythonExe = Join-Path $venvPath "Scripts\python.exe"
& $pythonExe -m pip install --upgrade pip --quiet
& $pythonExe -m pip install -e "$ProjectRoot[dev]" --quiet
Write-Host "  Done."

# Step 4 — Skills directory junction
Write-Host "[4/6] Linking into Claude Code skills directory ..."
$skillsDir = Join-Path $env:USERPROFILE ".claude\skills"
$junctionPath = Join-Path $skillsDir "brains-resume"
New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null
if (Test-Path $junctionPath) {
    Write-Host "  Already linked, skipping."
} else {
    cmd /c mklink /J $junctionPath $ProjectRoot | Out-Null
    Write-Host "  Linked: $junctionPath -> $ProjectRoot"
}

# Step 5 — Slash commands
Write-Host "[5/6] Installing slash commands ..."
$commandsSrc = Join-Path $ProjectRoot "commands"
$commandsDst = Join-Path $env:USERPROFILE ".claude\commands"
New-Item -ItemType Directory -Force -Path $commandsDst | Out-Null
if (Test-Path $commandsSrc) {
    Copy-Item -Path (Join-Path $commandsSrc "*.md") -Destination $commandsDst -Force
    Write-Host "  Slash commands copied to $commandsDst"
} else {
    Write-Host "  No commands/ directory found; skipping."
}

# Step 6 — Tests
if ($SkipTests) {
    Write-Host "[6/6] Tests skipped per -SkipTests flag."
} else {
    Write-Host "[6/6] Running test suite ..."
    & $pythonExe -m pytest "$ProjectRoot\tests" -q
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Test suite failed. Install completed but tests are not green."
        exit 1
    }
}

Write-Host ""
Write-Host "Install complete."
Write-Host "Next steps:"
Write-Host "  1. Start a new Claude Code session from any directory."
Write-Host "  2. Try one of: /brains-review, /brains-disclosure, /brains-edit, /brains-tailor, /brains-cover-letter, /brains-create, /brains-linkedin, /brains-career-change, /brains-check"
Write-Host "  3. Or invoke by natural language: 'review my resume at C:\path\to\resume.docx'"
