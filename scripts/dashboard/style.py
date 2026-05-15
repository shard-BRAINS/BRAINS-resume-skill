"""BRAINS Incubator branding for the Streamlit dashboard.

Applied via CSS injection at app startup by calling inject_brand_css() once
from app.py. References the brand spec documented in
references/brand-application.md.

At implementation time, the brains-brand skill was consulted for the
current BRAINS Incubator spec. The values below match that spec; update
this module if the spec changes in future.

Key Incubator deltas from the BRAINS parent brand:
- Primary accent is Incubator Blue (#4DA8FF), not BRAINS Gold (#FCC14D).
- Gold Deep (#D99518) is retained for accessible gold-on-white data callouts
  (4.6:1 contrast ratio, AA) but is not the Incubator accent colour.
- Footer credit uses the verbatim Group-A protected phrase:
  "Built by neurodivergent minds, for neurodivergent people."
"""
import streamlit as st


# ---- Brand constants ---------------------------------------------------------

INCUBATOR_BLUE = "#4DA8FF"   # BRAINS Incubator accent (sub-brand primary)
GOLD_DEEP = "#D99518"        # Accessible gold-on-white (4.6:1); data callouts
BG_DARK = "#1A1A1A"
BG_PANEL = "#2D2D2D"
TEXT_PRIMARY = "#E8E8E8"
TEXT_MUTED = "#A0A0A0"
ACCENT_POSITIVE = "#7ABA7A"  # subdued green for callbacks
ACCENT_WARNING = "#E0A040"   # amber for pacing-above-target
ACCENT_NEGATIVE = "#C76060"  # subdued red for rejections


BRAND_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Inter:wght@700&display=swap');

html, body, [class*="css"]  {{
    font-family: 'Atkinson Hyperlegible', sans-serif;
}}

h1, h2, h3, h4, h5, h6 {{
    font-family: 'Inter', sans-serif;
    color: {INCUBATOR_BLUE};
}}

/* Streamlit tab styling — top nav bar */
.stTabs [data-baseweb="tab-list"] {{
    border-bottom: 2px solid {INCUBATOR_BLUE};
    background-color: {BG_DARK};
}}
.stTabs [data-baseweb="tab"] {{
    color: {TEXT_PRIMARY};
    background-color: transparent;
    font-weight: 700;
}}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    color: {INCUBATOR_BLUE};
    border-bottom: 3px solid {INCUBATOR_BLUE};
}}

/* Metric tile styling */
[data-testid="stMetricValue"] {{
    color: {TEXT_PRIMARY};
    font-family: 'Inter', sans-serif;
}}
[data-testid="stMetricDelta"] {{
    color: {GOLD_DEEP};
}}
[data-testid="stMetricLabel"] {{
    color: {TEXT_MUTED};
    font-family: 'Atkinson Hyperlegible', sans-serif;
}}

/* Sidebar styling */
[data-testid="stSidebar"] {{
    background-color: {BG_PANEL};
    border-right: 1px solid {INCUBATOR_BLUE};
}}

/* Buttons — Incubator Blue primary */
.stButton button {{
    background-color: {BG_PANEL};
    color: {INCUBATOR_BLUE};
    border: 1px solid {INCUBATOR_BLUE};
}}
.stButton button:hover {{
    background-color: {INCUBATOR_BLUE};
    color: {BG_DARK};
}}

/* Success callouts — Incubator Blue instead of default green */
[data-testid="stAlert"][data-baseweb="notification"][kind="success"] {{
    background-color: rgba(77, 168, 255, 0.15);
    border-left: 4px solid {INCUBATOR_BLUE};
}}

/* DataFrame styling */
[data-testid="stDataFrame"] {{
    background-color: {BG_PANEL};
}}
</style>
"""


def inject_brand_css() -> None:
    """Inject BRAINS Incubator CSS. Call once at app startup."""
    st.markdown(BRAND_CSS, unsafe_allow_html=True)


def footer() -> None:
    """Render the BRAINS Incubator origin-credit footer."""
    st.markdown(
        "<div style='text-align:center; color:#A0A0A0; font-size:0.85em; padding-top:2em;'>"
        "BRAINS Incubator · Built by neurodivergent minds, for neurodivergent people."
        "</div>",
        unsafe_allow_html=True,
    )
