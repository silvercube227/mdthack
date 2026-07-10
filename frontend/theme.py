"""Medtronic design system: color tokens, forced-light CSS, and header helpers."""

from __future__ import annotations

import streamlit as st

# --- Medtronic brand palette --------------------------------------------------
NAVY = "#170F5F"
NAVY_DK = "#0E0840"
COBALT = NAVY
COBALT_DK = NAVY_DK
SKY = "#2A3A7A"

INK = "#1B1B2F"
SLATE = "#4A5261"
MUTED = "#5F6876"
BORDER = "#D8DCE8"
GRID = "#E8EBF4"
SURFACE = "#FFFFFF"
# A soft, faintly blue-tinted white — reads as "clean" rather than grey, and is
# used verbatim (same hex) for the app background AND the chart iframe so the
# two never appear as mismatched panels.
CANVAS = "#EEF1FB"
CANVAS_SOLID = CANVAS

GREEN = "#00843D"
RED = "#C8102E"
AMBER = "#E8A33D"
PURPLE = "#6B4EFF"
GRAY = "#9AA5B4"

FONT_STACK = "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


def inject_theme() -> None:
    """Global CSS — a clean, clinical, Medtronic light UI that ignores browser dark mode."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* ---- Force light mode regardless of the browser preference ---- */
        :root, html, body, .stApp,
        [data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stHeader"] {{
            color-scheme: light !important;
        }}

        html, body, [class*="css"] {{ font-family: {FONT_STACK}; }}
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
            background: {CANVAS} !important;
            color: {INK};
        }}
        /* The chart iframe is a separate document (see live_charts.py) that paints
           the identical {CANVAS} hex — keep the host element unpainted so no
           white flash/mismatch shows before it loads. */
        iframe {{ background: {CANVAS} !important; }}

        /* Readable text everywhere (inheritance-safe: no div/span/* so branded tiles keep colors) */
        .stApp p, .stApp li, .stApp label, .stApp td, .stApp th,
        [data-testid="stMarkdownContainer"] {{ color: {INK} !important; }}
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{ color: {NAVY} !important; }}
        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color: {SLATE} !important; }}
        [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label {{ color: {INK} !important; }}

        /* Trim default chrome and tighten layout */
        [data-testid="stHeader"] {{ background: transparent; }}
        [data-testid="stToolbar"], #MainMenu, footer {{ visibility: hidden; }}
        [data-testid="stMainBlockContainer"], .block-container {{
            padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1360px;
        }}

        /* ---- Section label ---- */
        .mdt-section {{
            display: flex; align-items: center; gap: 0.55rem;
            color: {NAVY}; font-size: 1rem; font-weight: 600; margin: 1.3rem 0 0.6rem 0;
            text-transform: uppercase; letter-spacing: 0.03em;
        }}
        .mdt-section::before {{ content: ""; width: 4px; height: 15px; border-radius: 2px; background: {COBALT}; }}

        /* ---- KPI tiles ---- */
        .mdt-kpi {{
            background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
            padding: 0.65rem 0.8rem; height: 100%; box-shadow: 0 1px 3px rgba(23,15,95,0.04);
        }}
        .mdt-kpi-k {{
            color: {SLATE}; font-size: 0.7rem; font-weight: 600; line-height: 1.15;
            text-transform: uppercase; letter-spacing: 0.04em;
        }}
        .mdt-kpi-v {{ color: {NAVY}; font-size: 1.5rem; font-weight: 700; line-height: 1.25; white-space: nowrap; }}
        .mdt-kpi-d {{ font-size: 0.72rem; font-weight: 600; margin-top: 1px; white-space: nowrap; }}
        .mdt-kpi-d.up {{ color: {RED}; }}
        .mdt-kpi-d.down {{ color: {GREEN}; }}
        .mdt-kpi-d.flat {{ color: {MUTED}; }}

        /* ---- KPI row (single line) ---- */
        .mdt-kpi-row {{
            display: flex;
            flex-wrap: nowrap;
            gap: 0.5rem;
            width: 100%;
            margin-bottom: 0.5rem;
        }}
        .mdt-kpi-row .mdt-kpi {{
            flex: 1 1 0;
            min-width: 0;
            padding: 0.55rem 0.65rem;
        }}
        .mdt-kpi-row .mdt-kpi-v {{ font-size: 1.25rem; }}

        /* ---- Parameter tiles (therapy panel) ---- */
        .mdt-param {{
            background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px;
            padding: 0.6rem 0.75rem; height: 100%;
        }}
        .mdt-param-k {{ color: {SLATE}; font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.04em; margin-bottom: 3px; }}
        .mdt-param-v {{ color: {NAVY}; font-size: 1.05rem; font-weight: 700; line-height: 1.2; }}

        /* ---- Buttons ---- */
        .stButton > button,
        .stButton > button p,
        .stButton > button span,
        .stButton > button div {{
            color: #ffffff !important;
        }}
        .stButton > button {{
            background: {COBALT}; color: #ffffff !important; border: none; border-radius: 9px;
            font-weight: 600; padding: 0.5rem 1rem; transition: background 0.15s ease;
        }}
        .stButton > button:hover,
        .stButton > button:hover p,
        .stButton > button:hover span,
        .stButton > button:hover div {{
            background: {COBALT_DK}; color: #ffffff !important;
        }}
        .stButton > button:focus,
        .stButton > button:focus p,
        .stButton > button:focus span,
        .stButton > button:focus div {{
            box-shadow: 0 0 0 3px rgba(23,15,95,0.22); color: #ffffff !important;
        }}
        .stButton > button:active,
        .stButton > button:active p,
        .stButton > button:active span,
        .stButton > button:active div {{
            color: #ffffff !important;
        }}
        [data-testid="stBaseButton-primary"],
        [data-testid="stBaseButton-primary"] p,
        [data-testid="stBaseButton-primary"] span {{
            color: #ffffff !important;
        }}

        /* ---- Sidebar ---- */
        [data-testid="stSidebar"] {{ background: {SURFACE}; border-right: 1px solid {BORDER}; }}
        [data-testid="stSidebar"] h3 {{
            font-size: 1.4rem !important;
            font-weight: 700 !important;
            color: {NAVY} !important;
        }}
        [data-testid="stSidebar"] h4 {{
            font-size: 1.12rem !important;
            font-weight: 600 !important;
            color: {NAVY} !important;
        }}
        [data-testid="stSidebar"] .stButton > button {{ background: {CANVAS_SOLID}; color: {NAVY} !important; border: 1px solid {BORDER}; }}
        [data-testid="stSidebar"] .stButton > button p,
        [data-testid="stSidebar"] .stButton > button span,
        [data-testid="stSidebar"] .stButton > button div {{ color: {NAVY} !important; }}
        [data-testid="stSidebar"] .stButton > button:hover,
        [data-testid="stSidebar"] .stButton > button:hover p,
        [data-testid="stSidebar"] .stButton > button:hover span,
        [data-testid="stSidebar"] .stButton > button:hover div {{
            background: {COBALT}; color: #ffffff !important; border-color: {COBALT};
        }}

        /* ---- Bordered containers, tabs, expander ---- */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 12px; border-color: {BORDER}; background: {SURFACE};
            box-shadow: 0 1px 3px rgba(23,15,95,0.04);
        }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 0.4rem; border-bottom: 1px solid {BORDER}; }}
        .stTabs [data-baseweb="tab"] {{ color: {SLATE}; font-weight: 500; }}
        .stTabs [aria-selected="true"] {{ color: {NAVY}; }}
        [data-testid="stExpander"] {{ border-radius: 12px; border-color: {BORDER}; }}
        iframe {{ border: none !important; }}
        hr {{ border-color: {BORDER}; }}

        /* ---- Form controls forced light (dropdowns render in body-level portals) ---- */
        input, textarea, select,
        [data-baseweb="input"], [data-baseweb="base-input"],
        [data-baseweb="select"] > div, [data-baseweb="textarea"] {{
            background-color: {SURFACE} !important; color: {INK} !important; border-color: {BORDER} !important;
        }}
        input::placeholder, textarea::placeholder {{ color: {MUTED} !important; }}
        [data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="list"], [role="listbox"], ul[role="listbox"] {{
            background-color: {SURFACE} !important; color: {INK} !important; border: 1px solid {BORDER} !important;
        }}
        [role="option"], li[role="option"], [data-baseweb="menu"] li {{
            background-color: {SURFACE} !important; color: {INK} !important;
        }}
        [role="option"]:hover, li[role="option"]:hover,
        [role="option"][aria-selected="true"], li[role="option"][aria-selected="true"] {{
            background-color: {CANVAS_SOLID} !important; color: {NAVY} !important;
        }}
        [data-baseweb="tooltip"], [role="tooltip"] {{ background-color: {NAVY} !important; color: #fff !important; }}
        [data-testid="stTooltipContent"] {{
            background-color: {SURFACE} !important; color: {INK} !important; border: 1px solid {BORDER} !important;
        }}
        [data-baseweb="select"] div {{ color: {INK} !important; }}
        * {{ scrollbar-color: {BORDER} transparent; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def section(label: str) -> None:
    st.markdown(f'<div class="mdt-section">{label}</div>', unsafe_allow_html=True)
