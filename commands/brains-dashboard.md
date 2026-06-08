---
description: Print the command to launch the BRAINS Resume dashboard in a browser
argument-hint: (no arguments)
---

<!-- markdownlint-disable-file MD041 -->
Print the launch command for the BRAINS Resume dashboard. Do NOT attempt to spawn the streamlit subprocess from Claude Code — long-running processes are awkward for Claude Code to own, and the user keeps terminal control.

Output the following two lines verbatim:

```text
Run: brains-resume-dashboard
Then open: http://localhost:8501
```

The dashboard runs entirely on localhost. Port 8501 is the Streamlit default. The user stops the dashboard by pressing Ctrl+C in the terminal where `brains-resume-dashboard` is running.

If the user reports that `brains-resume-dashboard` is not found on PATH, suggest:

```text
pip install -e .
```

from the project root to register the CLI entry. The entry is declared in `pyproject.toml` under `[project.scripts]` as `brains-resume-dashboard = "scripts.dashboard.launch:main"`.
