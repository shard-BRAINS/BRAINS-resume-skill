"""CLI entry point for the BRAINS Resume dashboard.

Registered in pyproject.toml [project.scripts] as `brains-resume-dashboard`.
After `pip install -e .`, the user runs the command from any terminal and
the dashboard launches on localhost:8501.

The launcher resolves the absolute path to app.py so the command works
regardless of the user's current working directory.
"""
import shutil
import subprocess
import sys
from pathlib import Path


APP_PATH = Path(__file__).parent / "app.py"


def main() -> int:
    """Launch the Streamlit dashboard. Returns the streamlit subprocess exit code."""
    if not APP_PATH.exists():
        sys.stderr.write(f"BRAINS Resume dashboard: app.py not found at {APP_PATH}\n")
        return 1

    streamlit_bin = shutil.which("streamlit")
    if streamlit_bin is None:
        sys.stderr.write(
            "BRAINS Resume dashboard: streamlit executable not on PATH. "
            "Reinstall the skill via `pip install -e .` to register dependencies.\n"
        )
        return 1

    print("BRAINS Resume Dashboard launching at http://localhost:8501")
    print("Press Ctrl+C in this terminal to stop the dashboard.")
    print()

    result = subprocess.run(
        [
            streamlit_bin,
            "run",
            str(APP_PATH),
            "--server.headless",
            "true",
            "--server.port",
            "8501",
        ]
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
