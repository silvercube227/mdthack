"""Recommended therapy parameter panel for the dashboard."""

from __future__ import annotations

import streamlit as st

from backend.therapy_recommendation import recommend_therapy_parameters
from frontend.session import apply_recommended_therapy, get_runner


def render_therapy_recommendation_panel() -> None:
    runner = get_runner()
    beta_history = list(runner.history["pathological_beta_power"])
    recommendation = recommend_therapy_parameters(beta_history)

    st.markdown("#### Recommended Therapy Parameters")
    c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1.2])

    with c1:
        st.markdown(
            f"**Beta Detection Threshold:** `{recommendation.pathological_beta_detection_threshold:.2f}`  \n"
            f"**Controller Gain (Kp):** `{recommendation.controller_gain_kp:.1f}`  \n"
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
        ("1 · STN LFP", "Pathological Beta waves generated"),
        ("2 · Biomarker Filter", "13–30 Hz band power extracted"),
        ("3 · Therapy Suggestion", "Parameters inferred from Beta burden"),
        ("4 · aDBS Control", "Proportional stimulation"),
        ("5 · Feedback", "DBS suppresses Beta at t+1"),
    ]
    for col, (title, detail) in zip(steps, pipeline):
        with col:
            st.markdown(
                f"<div style='background:#161b26;border:1px solid #2a3142;border-radius:8px;"
                f"padding:0.6rem;font-size:0.82rem;'>"
                f"<b style='color:#58a6ff;'>{title}</b><br><span style='color:#9ba7b8;'>{detail}</span></div>",
                unsafe_allow_html=True,
            )
