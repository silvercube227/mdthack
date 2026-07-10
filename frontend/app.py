"""Closed-Loop DBS Simulator — Streamlit dashboard entry point."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from backend.constants import DBSControlMode
from frontend.live_charts import render_persistent_charts
from frontend.plots import write_live_payload
from frontend.session import get_intervention_marker, get_runner, render_sidebar
from frontend.theme import inject_theme, section
from frontend.therapy_panel import render_therapy_recommendation_panel


def _kpi_tile(label: str, value: str, delta: str | None = None, cls: str = "flat") -> str:
    delta_html = f"<div class='mdt-kpi-d {cls}'>{delta}</div>" if delta else ""
    return (
        f"<div class='mdt-kpi'><div class='mdt-kpi-k'>{label}</div>"
        f"<div class='mdt-kpi-v'>{value}</div>{delta_html}</div>"
    )


def _kpi_row(hist: dict, t: list) -> None:
    lb = hist["pathological_beta_power"][-1]
    hb = hist["high_beta_power"][-1]
    burst = hist["low_beta_burst_duration_ms"][-1]
    dbs = hist["dbs_amplitude_ma"][-1]

    tiles = (
        _kpi_tile("Low-Beta Power", f"{lb:.2f}%")
        + _kpi_tile("High-Beta Power", f"{hb:.2f}%")
        + _kpi_tile("Burst Duration", f"{burst:.0f} ms")
        + _kpi_tile("DBS Amplitude", f"{dbs:.2f} mA")
        + _kpi_tile("Elapsed", f"{t[-1]:.1f} s")
    )
    st.markdown(f'<div class="mdt-kpi-row">{tiles}</div>', unsafe_allow_html=True)


def _push_ble_amplitude(dbs_amplitude_ma: float) -> None:
    """Forward the live DBS amplitude (mA, the same value shown in the KPI card)
    to the BLE stimulator link, if a client has been connected via the sidebar's
    "Connect INS Device " button. Scaling to the BLE uint8 payload happens
    centrally in fw/ble_dbs_host.py (`ma_to_uint8`)."""
    if not st.session_state.get("bt_device_connected"):
        return
    try:
        from fw.ble_dbs_host import update_amplitude
    except ImportError:
        return
    update_amplitude(dbs_amplitude_ma)


def _outcome_row(runner, intervention_time_sec) -> None:
    closed = runner.comparison_arms["Closed-Loop DBS"]
    no_dbs = runner.comparison_arms["No DBS"]
    fixed = runner.comparison_arms["Fixed DBS"]
    if intervention_time_sec is None or no_dbs.cumulative_patient_symptom_burden <= 0:
        return
    symptom_reduction = 1.0 - (
        closed.cumulative_patient_symptom_burden / max(no_dbs.cumulative_patient_symptom_burden, 1e-6)
    )
    energy_savings = 1.0 - (closed.cumulative_teed / max(fixed.cumulative_teed, 1e-6))
    a, b = st.columns(2)
    a.markdown(
        _kpi_tile("Symptom reduction vs No DBS", f"{symptom_reduction * 100:.0f}%", "closed-loop benefit", "down"),
        unsafe_allow_html=True,
    )
    b.markdown(
        _kpi_tile("Energy saved vs Fixed DBS", f"{energy_savings * 100:.0f}%", "battery benefit", "down"),
        unsafe_allow_html=True,
    )


@st.fragment(run_every=0.4)
def live_metrics(control_mode, limits, dopaminergic_state, symptom_severity_scale, paused) -> None:
    """Advance the simulation, refresh KPI cards, and publish the live chart payload.

    Chart drawing happens in the persistent iframe (rendered once in ``main``),
    which polls the payload written here — so the charts never re-mount.
    """
    runner = get_runner()
    intervention_time_sec, _ = get_intervention_marker()

    if not paused:
        runner.advance(
            control_mode,
            limits,
            dopaminergic_state,
            symptom_severity_scale,
            intervention_time_sec=intervention_time_sec,
        )

    hist = runner.history
    t = list(hist["time_sec"])
    if not t:
        st.info("Initializing closed-loop neuromodulation simulation…")
        return

    with st.container(border=True):
        _kpi_row(hist, t)
        _outcome_row(runner, intervention_time_sec)
    _push_ble_amplitude(hist["dbs_amplitude_ma"][-1])
    write_live_payload(hist, runner.comparison_history, intervention_time_sec)


def _render_references() -> None:
    with st.expander("Clinical references"):
        st.markdown(
            """
            - **Neumann et al., npj Parkinson's Disease 2022** — Beta suppression as chronic biomarker;
              dose-response 0.5–2.5 mA; LB power OFF 8.43% → therapeutic 2.11%.
            - **Tinkhauser et al., Brain 2017** — Beta burst dynamics; 75th-percentile envelope detection.
            - **Anderson et al., npj Parkinson's Disease 2023** (n=106) — LB burst duration OFF 579 ms, ON 359 ms.
            - **Stanslaski et al., npj Parkinson's Disease 2024 (ADAPT-PD)** — Single/Dual Threshold aDBS;
              8–30 Hz LFP control signal; TEED as primary energy endpoint.
            """
        )


def main() -> None:
    st.set_page_config(
        page_title="Medtronic Closed-Loop DBS Simulator",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="locked",
    )
    inject_theme()
    get_runner()

    (
        control_mode,
        limits,
        dopaminergic_state,
        symptom_severity_scale,
        paused,
    ) = render_sidebar()

    render_therapy_recommendation_panel()

    section("Live neural biomarkers — untreated vs treated")
    live_metrics(control_mode, limits, dopaminergic_state, symptom_severity_scale, paused)
    render_persistent_charts()

    st.divider()
    _render_references()


if __name__ == "__main__":
    main()
