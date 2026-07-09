"""Streamlit session-state wiring for the simulation runner."""

from __future__ import annotations

import streamlit as st

from backend.clinical_parameters import (
    ADAPT_PD_SENSE_HIGH_HZ,
    ADAPT_PD_SENSE_LOW_HZ,
    BETA_TOTAL_HIGH_HZ,
    BETA_TOTAL_LOW_HZ,
    DETECTION_WINDOW_MS,
    DopaminergicState,
    LB_POWER_OFF_PCT,
    LB_POWER_THERAPEUTIC_PCT,
    LOWER_STIM_MA,
    SAMPLE_RATE_HZ,
    UPPER_STIM_MA,
)
from backend.constants import DBSControlMode
from backend.controller import ControllerLimits
from backend.simulation import SimulationRunner
from backend.therapy_recommendation import RecommendedTherapyParameters


def _init_control_defaults() -> None:
    defaults = {
        "dbs_control_mode_label": DBSControlMode.ADAPTIVE_SINGLE_THRESHOLD.value,
        "lfp_threshold_pct": 5.5,
        "lfp_upper_threshold_pct": 6.0,
        "lfp_lower_threshold_pct": 2.5,
        "lower_stim_ma": LOWER_STIM_MA,
        "upper_stim_ma": UPPER_STIM_MA,
        "dopaminergic_state_label": DopaminergicState.OFF.value,
        "symptom_severity_scale": 1.0,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def get_runner() -> SimulationRunner:
    if "simulation_runner" not in st.session_state:
        st.session_state.simulation_runner = SimulationRunner()
    return st.session_state.simulation_runner


def reset_simulation() -> None:
    st.session_state.simulation_runner = SimulationRunner()


def get_controller_limits() -> ControllerLimits:
    return ControllerLimits(
        lower_stim_ma=st.session_state.lower_stim_ma,
        upper_stim_ma=st.session_state.upper_stim_ma,
        lfp_threshold_pct=st.session_state.lfp_threshold_pct,
        lfp_upper_threshold_pct=st.session_state.lfp_upper_threshold_pct,
        lfp_lower_threshold_pct=st.session_state.lfp_lower_threshold_pct,
    )


def apply_recommended_therapy(recommendation: RecommendedTherapyParameters) -> None:
    st.session_state.dbs_control_mode_label = recommendation.dbs_control_mode.value
    st.session_state.lfp_threshold_pct = recommendation.lfp_threshold_pct
    st.session_state.lfp_upper_threshold_pct = recommendation.lfp_upper_threshold_pct
    st.session_state.lfp_lower_threshold_pct = recommendation.lfp_lower_threshold_pct
    st.session_state.lower_stim_ma = recommendation.lower_stim_ma
    st.session_state.upper_stim_ma = recommendation.upper_stim_ma


def render_sidebar() -> tuple:
    _init_control_defaults()
    st.sidebar.header("Neuromodulation Control Panel")

    control_mode_label = st.sidebar.selectbox(
        "DBS Control Mode",
        options=[m.value for m in DBSControlMode],
        key="dbs_control_mode_label",
        help="Open-loop baseline, fixed cDBS, or ADAPT-PD Single/Dual Threshold aDBS.",
    )
    control_mode = DBSControlMode(control_mode_label)

    dopaminergic_label = st.sidebar.selectbox(
        "Dopaminergic State",
        options=[s.value for s in DopaminergicState],
        key="dopaminergic_state_label",
        help="OFF = withdrawn levodopa (pathological Beta elevated). ON = medicated state.",
    )
    dopaminergic_state = DopaminergicState(dopaminergic_label)

    st.sidebar.markdown("**LFP Power Thresholds (% total power, 8–30 Hz band)**")
    lfp_threshold_pct = st.sidebar.slider(
        "Single-Threshold LFP Power (ST-aDBS)",
        min_value=1.0,
        max_value=12.0,
        step=0.1,
        key="lfp_threshold_pct",
        help=f"Literature OFF LB reference: {LB_POWER_OFF_PCT:.1f}%; therapeutic: {LB_POWER_THERAPEUTIC_PCT:.1f}%.",
    )
    lfp_upper_threshold_pct = st.sidebar.slider(
        "Dual-Threshold Upper LFP Power",
        min_value=2.0,
        max_value=14.0,
        step=0.1,
        key="lfp_upper_threshold_pct",
    )
    lfp_lower_threshold_pct = st.sidebar.slider(
        "Dual-Threshold Lower LFP Power",
        min_value=0.5,
        max_value=8.0,
        step=0.1,
        key="lfp_lower_threshold_pct",
    )

    st.sidebar.markdown("**Stimulation Amplitude Limits (mA)**")
    lower_stim_ma = st.sidebar.slider(
        "Lower Stim Limit (mA)",
        min_value=0.5,
        max_value=2.5,
        step=0.1,
        key="lower_stim_ma",
        help="ADAPT-PD: never zero — sub-therapeutic rebound prevention.",
    )
    upper_stim_ma = st.sidebar.slider(
        "Upper Stim Limit (mA)",
        min_value=1.5,
        max_value=3.5,
        step=0.1,
        key="upper_stim_ma",
    )

    symptom_severity_scale = st.sidebar.slider(
        "Base Symptom Severity",
        min_value=0.5,
        max_value=1.5,
        step=0.05,
        key="symptom_severity_scale",
        help="Scales OFF-state burst duration around literature mean (579 ms).",
    )

    col_a, col_b = st.sidebar.columns(2)
    with col_a:
        if st.button("Reset Simulation", use_container_width=True):
            reset_simulation()
            st.rerun()
    with col_b:
        paused = st.toggle("Pause", value=False)

    st.sidebar.markdown("---")
    st.sidebar.caption(
        f"Percept sampling: **{SAMPLE_RATE_HZ} Hz** · Window: **{DETECTION_WINDOW_MS} ms** · "
        f"Sense band: **{ADAPT_PD_SENSE_LOW_HZ:.0f}–{ADAPT_PD_SENSE_HIGH_HZ:.0f} Hz** · "
        f"Beta: **{BETA_TOTAL_LOW_HZ:.0f}–{BETA_TOTAL_HIGH_HZ:.0f} Hz**"
    )

    return (
        control_mode,
        get_controller_limits(),
        dopaminergic_state,
        symptom_severity_scale,
        paused,
    )
