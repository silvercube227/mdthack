"""Recommended therapy parameter panel for the dashboard."""

from __future__ import annotations

import streamlit as st

from backend.therapy_recommendation import recommend_therapy_parameters
from frontend.session import apply_recommended_therapy, get_runner


def render_therapy_recommendation_panel() -> None:
    runner = get_runner()
    beta_history = list(runner.history["pathological_beta_power"])
    recommendation = recommend_therapy_parameters(beta_history)

    st.markdown("#### Recommended Therapy Parameters (ADAPT-PD Workflow)")
    c1, c2, c4 = st.columns([1.4, 1.2, 1.2])

    with c1:
        st.markdown(
            f"**LFP Threshold (ST):** `{recommendation.lfp_threshold_pct:.1f}%`  \n"
            f"**Dual Thresholds:** `{recommendation.lfp_lower_threshold_pct:.1f}%` / "
            f"`{recommendation.lfp_upper_threshold_pct:.1f}%`  \n"
            f"**Stim Limits:** `{recommendation.lower_stim_ma:.1f}` – `{recommendation.upper_stim_ma:.1f}` mA  \n"
            f"**Suggested Mode:** `{recommendation.dbs_control_mode.value}`"
        )
    with c2:
        st.caption(recommendation.clinical_rationale)
    with c4:
        if st.button("Apply Recommended Therapy Parameters", use_container_width=True):
            apply_recommended_therapy(recommendation)
            st.rerun()

    steps = st.columns(5)
    pipeline = [
        ("1 · STN LFP", "Beta bursts @ 250 Hz (Percept)"),
        ("2 · Biomarker", "LB power % total + burst detection"),
        ("3 · Timeline Cal.", "OFF baseline threshold"),
        ("4 · aDBS Control", "ADAPT-PD ST / DT algorithm"),
        ("5 · Feedback", "Dose-response Beta suppression"),
    ]
    for col, (title, detail) in zip(steps, pipeline):
        with col:
            st.markdown(
                f"<div style='background:#161b26;border:1px solid #2a3142;border-radius:8px;"
                f"padding:0.6rem;font-size:0.82rem;'>"
                f"<b style='color:#58a6ff;'>{title}</b><br><span style='color:#9ba7b8;'>{detail}</span></div>",
                unsafe_allow_html=True,
            )
