"""Streamlit session-state wiring for the simulation runner."""

from __future__ import annotations

from collections import deque

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
    MAX_HISTORY_SECONDS,
    SAMPLE_RATE_HZ,
    STIM_FREQUENCY_HZ,
    STIM_FREQUENCY_MAX_HZ,
    STIM_FREQUENCY_MIN_HZ,
    UPPER_STIM_MA,
)
from backend.constants import DBSControlMode
from backend.controller import ControllerLimits
from backend.simulation import SimulationRunner
from backend.therapy_recommendation import RecommendedTherapyParameters


def _init_control_defaults() -> None:
    defaults = {
        "dbs_control_mode_label": DBSControlMode.NONE.value,
        "lfp_threshold_pct": 5.5,
        "lfp_upper_threshold_pct": 6.0,
        "lfp_lower_threshold_pct": 2.5,
        "lower_stim_ma": LOWER_STIM_MA,
        "upper_stim_ma": UPPER_STIM_MA,
        "stim_frequency_hz": STIM_FREQUENCY_HZ,
        "dopaminergic_state_label": DopaminergicState.OFF.value,
        "symptom_severity_scale": 1.0,
        "intervention_start_time_sec": None,
        "intervention_label": None,
        "_last_control_mode_label": DBSControlMode.NONE.value,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _migrate_runner(runner: SimulationRunner) -> None:
    """Back-fill history keys when a live session predates a schema change."""
    hist = runner.history
    if "dbs_frequency_hz" not in hist:
        max_samples = int(MAX_HISTORY_SECONDS * SAMPLE_RATE_HZ)
        n = len(hist.get("time_sec", []))
        hist["dbs_frequency_hz"] = deque([STIM_FREQUENCY_HZ] * n, maxlen=max_samples)


def get_runner() -> SimulationRunner:
    if "simulation_runner" not in st.session_state:
        st.session_state.simulation_runner = SimulationRunner()
    else:
        _migrate_runner(st.session_state.simulation_runner)
    return st.session_state.simulation_runner


def reset_simulation() -> None:
    """Reset engine to open-loop baseline (None) and clear intervention marker."""
    st.session_state.simulation_runner = SimulationRunner()
    st.session_state["_pending_therapy_recommendation"] = {
        "dbs_control_mode_label": DBSControlMode.NONE.value,
    }
    st.session_state["intervention_start_time_sec"] = None
    st.session_state["intervention_label"] = None
    st.session_state["_last_control_mode_label"] = DBSControlMode.NONE.value
    st.session_state.pop("_mark_intervention_on_next_run", None)
    get_runner().reset_comparison_arms()


def get_intervention_marker() -> tuple[float | None, str | None]:
    t = st.session_state.get("intervention_start_time_sec")
    label = st.session_state.get("intervention_label")
    return t, label


def _mark_intervention_start(control_mode_label: str) -> None:
    if control_mode_label == DBSControlMode.NONE.value:
        return
    runner = get_runner()
    st.session_state["intervention_start_time_sec"] = runner.sim_time_sec
    st.session_state["intervention_label"] = control_mode_label


def _sync_intervention_marker(control_mode: DBSControlMode) -> None:
    """Record vertical-line time when user switches from None → active therapy."""
    prev_label = st.session_state.get("_last_control_mode_label", DBSControlMode.NONE.value)
    current_label = control_mode.value

    if prev_label == DBSControlMode.NONE.value and current_label != DBSControlMode.NONE.value:
        _mark_intervention_start(current_label)
    elif current_label == DBSControlMode.NONE.value:
        st.session_state["intervention_start_time_sec"] = None
        st.session_state["intervention_label"] = None

    st.session_state["_last_control_mode_label"] = current_label


def get_controller_limits() -> ControllerLimits:
    return ControllerLimits(
        lower_stim_ma=st.session_state.lower_stim_ma,
        upper_stim_ma=st.session_state.upper_stim_ma,
        lfp_threshold_pct=st.session_state.lfp_threshold_pct,
        lfp_upper_threshold_pct=st.session_state.lfp_upper_threshold_pct,
        lfp_lower_threshold_pct=st.session_state.lfp_lower_threshold_pct,
        stim_frequency_hz=st.session_state.stim_frequency_hz,
    )


def apply_recommended_therapy(recommendation: RecommendedTherapyParameters) -> None:
    """Queue therapy params for next run (must apply before sidebar widgets mount)."""
    st.session_state["_pending_therapy_recommendation"] = {
        "dbs_control_mode_label": recommendation.dbs_control_mode.value,
        "lfp_threshold_pct": recommendation.lfp_threshold_pct,
        "lfp_upper_threshold_pct": recommendation.lfp_upper_threshold_pct,
        "lfp_lower_threshold_pct": recommendation.lfp_lower_threshold_pct,
        "lower_stim_ma": recommendation.lower_stim_ma,
        "upper_stim_ma": recommendation.upper_stim_ma,
    }
    if (
        recommendation.dbs_control_mode != DBSControlMode.NONE
        and st.session_state.get("dbs_control_mode_label") == DBSControlMode.NONE.value
    ):
        st.session_state["_mark_intervention_on_next_run"] = True


def _apply_pending_therapy_recommendation() -> None:
    """Apply queued params before widgets bind to session_state keys."""
    pending = st.session_state.pop("_pending_therapy_recommendation", None)
    mark_intervention = st.session_state.pop("_mark_intervention_on_next_run", False)
    if not pending:
        return
    for key, value in pending.items():
        st.session_state[key] = value
    mode_label = pending.get("dbs_control_mode_label", DBSControlMode.NONE.value)
    st.session_state["_last_control_mode_label"] = mode_label
    if mark_intervention and mode_label != DBSControlMode.NONE.value:
        _mark_intervention_start(mode_label)


def _render_device_connection() -> None:
    """BLE stimulator link controls: starts/stops the GATT server host that the
    Arduino Nano ESP32 (BLE central) connects to (see fw/ble_dbs_host.py)."""
    st.session_state.setdefault("bt_device_connected", False)
    connected = st.session_state["bt_device_connected"]

    with st.container(border=True):
        st.markdown("**Device Connection**")
        if connected:
            st.success("BLE advertising")
        else:
            st.caption("No stimulator paired · BLE host stopped")

        label = "Disconnect Bluetooth Device" if connected else "Connect Bluetooth Device"
        if st.button(label, use_container_width=True, key="bt_connect_btn"):
            from fw.ble_dbs_host import start_ble_host, stop_ble_host

            if connected:
                stop_ble_host()
                st.session_state["bt_device_connected"] = False
                st.toast("BLE host stopped.")
            elif start_ble_host():
                st.session_state["bt_device_connected"] = True
                st.toast("BLE host advertising")
            else:
                st.toast("Failed to start BLE host — check logs.", icon="\u26a0\ufe0f")
            st.rerun()


def render_sidebar() -> tuple:
    _init_control_defaults()
    _apply_pending_therapy_recommendation()

    with st.sidebar:
        st.markdown("### Control Panel")
        st.caption("Neuromodulation therapy settings")

        _render_device_connection()

        st.markdown("#### Therapy Mode")
        control_mode_label = st.selectbox(
            "DBS Control Mode",
            options=[m.value for m in DBSControlMode],
            key="dbs_control_mode_label",
            help="Open-loop baseline, fixed cDBS, or ADAPT-PD Single/Dual Threshold aDBS.",
        )
        control_mode = DBSControlMode(control_mode_label)

        dopaminergic_label = st.selectbox(
            "Dopaminergic State",
            options=[s.value for s in DopaminergicState],
            key="dopaminergic_state_label",
            help="OFF = withdrawn levodopa (pathological Beta elevated). ON = medicated state.",
        )
        dopaminergic_state = DopaminergicState(dopaminergic_label)

        st.divider()
        st.markdown("#### LFP Power Thresholds")
        st.caption("% of total power, 8–30 Hz sense band")
        lfp_threshold_pct = st.slider(
            "Single-Threshold LFP Power (ST-aDBS)",
            min_value=1.0,
            max_value=12.0,
            step=0.1,
            key="lfp_threshold_pct",
            help=f"Literature OFF LB reference: {LB_POWER_OFF_PCT:.1f}%; therapeutic: {LB_POWER_THERAPEUTIC_PCT:.1f}%.",
        )
        lfp_upper_threshold_pct = st.slider(
            "Dual-Threshold Upper LFP Power",
            min_value=2.0,
            max_value=14.0,
            step=0.1,
            key="lfp_upper_threshold_pct",
        )
        lfp_lower_threshold_pct = st.slider(
            "Dual-Threshold Lower LFP Power",
            min_value=0.5,
            max_value=8.0,
            step=0.1,
            key="lfp_lower_threshold_pct",
        )

        st.divider()
        st.markdown("#### Stimulation Amplitude Limits")
        st.caption("Milliamps (mA)")
        lower_stim_ma = st.slider(
            "Lower Stim Limit (mA)",
            min_value=0.5,
            max_value=2.5,
            step=0.1,
            key="lower_stim_ma",
            help="ADAPT-PD: never zero — sub-therapeutic rebound prevention.",
        )
        upper_stim_ma = st.slider(
            "Upper Stim Limit (mA)",
            min_value=1.5,
            max_value=3.5,
            step=0.1,
            key="upper_stim_ma",
        )
        st.slider(
            "Stimulation Frequency (Hz)",
            min_value=float(STIM_FREQUENCY_MIN_HZ),
            max_value=float(STIM_FREQUENCY_MAX_HZ),
            step=5.0,
            key="stim_frequency_hz",
            help="DBS pulse-train frequency (typical Percept: 130 Hz). "
            "Scales total energy delivered; controller adjusts amplitude only.",
        )

        st.divider()
        st.markdown("#### Simulation")
        symptom_severity_scale = st.slider(
            "Base Symptom Severity",
            min_value=0.5,
            max_value=1.5,
            step=0.05,
            key="symptom_severity_scale",
            help="Scales OFF-state burst duration around literature mean (579 ms).",
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Reset", use_container_width=True, help="Reset to open-loop baseline (None)"):
                reset_simulation()
                st.rerun()
        with col_b:
            paused = st.toggle("Pause", value=False)

        _sync_intervention_marker(control_mode)

        st.divider()
        st.caption(
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
