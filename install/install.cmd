@echo off
REM BRAINS Resume Skill installer wrapper for Windows.
REM
REM Bypasses PowerShell's default Restricted execution policy for this
REM single invocation only. No system setting is changed.
REM
REM Usage:
REM   .\install\install.cmd
REM   .\install\install.cmd -SkipTests
REM
REM Equivalent to running:
REM   powershell -ExecutionPolicy Bypass -File install\install.ps1

setlocal
set "SCRIPT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install.ps1" %*
endlocal
