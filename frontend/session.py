"""Streamlit session-state wiring for the simulation runner."""

from __future__ import annotations

import streamlit as st

from backend.constants import DBSControlMode
from backend.simulation import SimulationRunner
from backend.therapy_recommendation import RecommendedTherapyParameters


def _init_control_defaults() -> None:
    defaults = {
        "dbs_control_mode_label": DBSControlMode.PROPORTIONAL.value,
        "pathological_beta_detection_threshold": 0.45,
        "controller_gain_kp": 4.0,
        "base_symptom_severity": 0.70,
        "neuromodulatory_gain": 0.85,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def get_runner() -> SimulationRunner:
    if "simulation_runner" not in st.session_state:
        st.session_state.simulation_runner = SimulationRunner()
    return st.session_state.simulation_runner


def reset_simulation() -> None:
    st.session_state.simulation_runner = SimulationRunner()


def apply_recommended_therapy(recommendation: RecommendedTherapyParameters) -> None:
    st.session_state.dbs_control_mode_label = recommendation.dbs_control_mode.value
    st.session_state.pathological_beta_detection_threshold = recommendation.pathological_beta_detection_threshold
    st.session_state.controller_gain_kp = recommendation.controller_gain_kp


def render_sidebar() -> tuple:
    _init_control_defaults()
    st.sidebar.header("Neuromodulation Control Panel")

    control_mode_label = st.sidebar.selectbox(
        "DBS Control Mode",
        options=[m.value for m in DBSControlMode],
        key="dbs_control_mode_label",
        help="Select open-loop baseline, fixed stimulation, or proportional adaptive DBS.",
    )
    control_mode = DBSControlMode(control_mode_label)

    beta_detection_threshold = st.sidebar.slider(
        "Pathological Beta Detection Threshold",
        min_value=0.10,
        max_value=0.90,
        step=0.01,
        key="pathological_beta_detection_threshold",
        help="Clinical decision boundary for triggering adaptive neuromodulation.",
    )

    controller_gain_kp = st.sidebar.slider(
        "Controller Gain (Kp) / Neuromodulatory Gain",
        min_value=0.5,
        max_value=8.0,
        step=0.1,
        key="controller_gain_kp",
        help="Proportional gain mapping Pathological Beta Power → DBS Amplitude (mA).",
    )

    base_symptom_severity = st.sidebar.slider(
        "Base Symptom Severity",
        min_value=0.20,
        max_value=1.00,
        step=0.01,
        key="base_symptom_severity",
        help="Underlying Parkinsonian Beta burden before neuromodulatory intervention.",
    )

    neuromodulatory_gain = st.sidebar.slider(
        "Neuromodulatory Gain (Stim Suppression Efficacy)",
        min_value=0.10,
        max_value=1.50,
        step=0.01,
        key="neuromodulatory_gain",
        help="Efficacy with which DBS Amplitude suppresses pathological Beta oscillations.",
    )

    col_a, col_b = st.sidebar.columns(2)
    with col_a:
        if st.button("Reset Simulation", use_container_width=True):
            reset_simulation()
            st.rerun()
    with col_b:
        paused = st.toggle("Pause", value=False)

    from backend.constants import BETA_BAND_HIGH_HZ, BETA_BAND_LOW_HZ, BIOMARKER_WINDOW_MS, SAMPLE_RATE_HZ

    st.sidebar.markdown("---")
    st.sidebar.caption(
        f"Sampling: **{SAMPLE_RATE_HZ} Hz** · Biomarker window: **{BIOMARKER_WINDOW_MS} ms** · "
        f"Beta band: **{BETA_BAND_LOW_HZ:.0f}–{BETA_BAND_HIGH_HZ:.0f} Hz**"
    )

    return (
        control_mode,
        beta_detection_threshold,
        controller_gain_kp,
        base_symptom_severity,
        neuromodulatory_gain,
        paused,
    )
