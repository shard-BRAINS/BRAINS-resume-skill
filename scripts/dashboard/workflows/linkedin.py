"""/brains-linkedin — ingest a LinkedIn export ZIP."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from scripts.dashboard.workflows._card import handoff_button


def render(file_path: Optional[Path] = None) -> None:
    st.markdown("**Ingest a LinkedIn export ZIP (third-party PII excluded automatically).**")
    st.caption("Get your LinkedIn data export from Settings → Data Privacy → Get a copy of your data → 'Want something in particular?' → Profile.")
    zip_path_str = st.text_input("Path to LinkedIn export ZIP", key="linkedin_zip_path", value=str(file_path) if file_path else "")
    if zip_path_str:
        p = Path(zip_path_str)
        if not p.exists():
            st.error(f"File not found: {p}")
        else:
            handoff_button("linkedin", [p], note="Claude Code will ingest and summarise the export.", key="linkedin_btn")
