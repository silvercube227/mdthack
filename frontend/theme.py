"""Medtronic design system: color tokens, forced-light CSS, and header helpers."""

from __future__ import annotations

import streamlit as st

# --- Medtronic brand palette --------------------------------------------------
NAVY = "#170F5F"
COBALT = "#0077C8"
COBALT_DK = "#005FA0"
SKY = "#4AA3DB"

INK = "#1B1B2F"
SLATE = "#4A5261"
MUTED = "#5F6876"
BORDER = "#E1E6EF"
GRID = "#EDF0F6"
SURFACE = "#FFFFFF"
CANVAS = "#F4F6FB"

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
        .stApp {{ background: {CANVAS}; color: {INK}; }}

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

        /* ---- Brand header ---- */
        .mdt-header {{
            display: flex; align-items: center; gap: 0.9rem;
            background: {SURFACE}; border: 1px solid {BORDER}; border-left: 5px solid {COBALT};
            border-radius: 14px; padding: 1rem 1.35rem; margin-bottom: 1.1rem;
            box-shadow: 0 2px 10px rgba(23,15,95,0.05);
        }}
        .mdt-mark {{
            width: 38px; height: 38px; border-radius: 10px; flex: none;
            background: linear-gradient(135deg, {NAVY} 0%, {COBALT} 100%);
            display: flex; align-items: center; justify-content: center;
            color: #fff; font-weight: 700; font-size: 1.2rem;
        }}
        .mdt-eyebrow {{
            color: {COBALT}; font-size: 0.66rem; font-weight: 700;
            letter-spacing: 0.14em; text-transform: uppercase;
        }}
        .mdt-title {{ color: {NAVY}; font-size: 1.3rem; font-weight: 700; line-height: 1.15; }}
        .mdt-sub {{ color: {SLATE}; font-size: 0.83rem; margin-top: 1px; }}

        /* ---- Section label ---- */
        .mdt-section {{
            display: flex; align-items: center; gap: 0.55rem;
            color: {NAVY}; font-size: 1rem; font-weight: 600; margin: 0.5rem 0 0.5rem 0;
        }}
        .mdt-section::before {{ content: ""; width: 4px; height: 15px; border-radius: 2px; background: {COBALT}; }}

        /* ---- KPI tiles ---- */
        .mdt-kpi {{
            background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
            padding: 0.65rem 0.8rem; height: 100%; box-shadow: 0 1px 3px rgba(23,15,95,0.04);
        }}
        .mdt-kpi-k {{ color: {SLATE}; font-size: 0.74rem; font-weight: 600; line-height: 1.15; }}
        .mdt-kpi-v {{ color: {NAVY}; font-size: 1.5rem; font-weight: 700; line-height: 1.25; white-space: nowrap; }}
        .mdt-kpi-d {{ font-size: 0.72rem; font-weight: 600; margin-top: 1px; white-space: nowrap; }}
        .mdt-kpi-d.up {{ color: {RED}; }}
        .mdt-kpi-d.down {{ color: {GREEN}; }}
        .mdt-kpi-d.flat {{ color: {MUTED}; }}

        /* ---- Parameter tiles (therapy panel) ---- */
        .mdt-param {{
            background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px;
            padding: 0.6rem 0.75rem; height: 100%;
        }}
        .mdt-param-k {{ color: {SLATE}; font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.04em; margin-bottom: 3px; }}
        .mdt-param-v {{ color: {NAVY}; font-size: 1.05rem; font-weight: 700; line-height: 1.2; }}

        /* ---- Buttons ---- */
        .stButton > button {{
            background: {COBALT}; color: #fff; border: none; border-radius: 9px;
            font-weight: 600; padding: 0.5rem 1rem; transition: background 0.15s ease;
        }}
        .stButton > button:hover {{ background: {COBALT_DK}; color: #fff; }}
        .stButton > button:focus {{ box-shadow: 0 0 0 3px rgba(0,119,200,0.25); color: #fff; }}

        /* ---- Sidebar ---- */
        [data-testid="stSidebar"] {{ background: {SURFACE}; border-right: 1px solid {BORDER}; }}
        [data-testid="stSidebar"] .stButton > button {{ background: {CANVAS}; color: {NAVY}; border: 1px solid {BORDER}; }}
        [data-testid="stSidebar"] .stButton > button:hover {{ background: {COBALT}; color: #fff; border-color: {COBALT}; }}

        /* ---- Bordered containers, tabs, expander ---- */
        [data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 12px; border-color: {BORDER}; }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 0.4rem; border-bottom: 1px solid {BORDER}; }}
        .stTabs [data-baseweb="tab"] {{ color: {SLATE}; font-weight: 500; }}
        .stTabs [aria-selected="true"] {{ color: {NAVY}; }}
        [data-testid="stExpander"] {{ border-radius: 12px; border-color: {BORDER}; }}
        iframe {{ border: none !important; }}

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
            background-color: {CANVAS} !important; color: {NAVY} !important;
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
