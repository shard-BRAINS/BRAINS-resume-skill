"""Per-slash-command workflow modules for the dashboard.

Each module exposes a single `render(file_path=None)` function called by either
the Workflows tab or an inline contextual button. Validator-backed modules run
their analyzer in-dashboard; pure-LLM modules collect inputs and trigger the
clipboard handoff.
"""
