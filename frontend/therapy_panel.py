"""Recommended therapy parameter panel for the dashboard."""

from __future__ import annotations

import streamlit as st

from backend.constants import DBSControlMode
from backend.therapy_recommendation import recommend_therapy_parameters
from frontend.session import apply_recommended_therapy, get_runner

_MODE_SHORT = {
    DBSControlMode.NONE: "Open-loop",
    DBSControlMode.FIXED: "Fixed cDBS",
    DBSControlMode.ADAPTIVE_SINGLE_THRESHOLD: "Adaptive · Single",
    DBSControlMode.ADAPTIVE_DUAL_THRESHOLD: "Adaptive · Dual",
}


def _param_tile(label: str, value: str) -> str:
    return (
        f"<div class='mdt-param'><div class='mdt-param-k'>{label}</div>"
        f"<div class='mdt-param-v'>{value}</div></div>"
    )


def render_therapy_recommendation_panel() -> None:
    runner = get_runner()
    beta_history = list(runner.history["pathological_beta_power"])
    recommendation = recommend_therapy_parameters(beta_history)

    with st.container(border=True):
        st.markdown("#### Recommended Therapy Parameters — ADAPT-PD Workflow")

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(_param_tile("ST Threshold", f"{recommendation.lfp_threshold_pct:.1f}%"), unsafe_allow_html=True)
        c2.markdown(
            _param_tile(
                "DT Thresholds",
                f"{recommendation.lfp_lower_threshold_pct:.1f}–{recommendation.lfp_upper_threshold_pct:.1f}%",
            ),
            unsafe_allow_html=True,
        )
        c3.markdown(
            _param_tile("Stim Limits", f"{recommendation.lower_stim_ma:.1f}–{recommendation.upper_stim_ma:.1f} mA"),
            unsafe_allow_html=True,
        )
        c4.markdown(
            _param_tile("Suggested Mode", _MODE_SHORT.get(recommendation.dbs_control_mode, "—")),
            unsafe_allow_html=True,
        )

        st.caption(recommendation.clinical_rationale)

        if st.button("Apply Recommended Therapy Parameters", use_container_width=True):
            apply_recommended_therapy(recommendation)
            st.rerun()

