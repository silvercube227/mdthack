"""Closed-Loop DBS Simulator — Streamlit dashboard entry point."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from backend.constants import DBSControlMode
from frontend.plots import (
    build_beta_power_figure,
    build_burst_duration_figure,
    build_closed_loop_efficiency_figure,
    build_dbs_amplitude_figure,
    build_stn_lfp_figure,
)
from frontend.session import get_runner, render_sidebar
from frontend.therapy_panel import render_therapy_recommendation_panel


def inject_dark_theme_css() -> None:
    st.markdown(
        """
        <style>
        .stApp { background-color: #0e1117; }
        [data-testid="stSidebar"] { background-color: #161b26; border-right: 1px solid #2a3142; }
        .dbs-header {
            background: linear-gradient(135deg, #161b26 0%, #1f2937 100%);
            border: 1px solid #2a3142;
            border-radius: 12px;
            padding: 1.2rem 1.5rem;
            margin-bottom: 1rem;
        }
        .dbs-header h1 { color: #e6edf3; font-size: 1.55rem; margin: 0; }
        .dbs-header p { color: #9ba7b8; margin: 0.4rem 0 0 0; font-size: 0.95rem; }
        div[data-testid="stMetricValue"] { color: #58a6ff; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.fragment(run_every=0.35)
def live_simulation_fragment(
    control_mode: DBSControlMode,
    limits,
    dopaminergic_state,
    symptom_severity_scale: float,
    paused: bool,
) -> None:
    runner = get_runner()

    if not paused:
        runner.advance(control_mode, limits, dopaminergic_state, symptom_severity_scale)

    hist = runner.history
    t = list(hist["time_sec"])
    if not t:
        st.info("Initializing closed-loop neuromodulation simulation…")
        return

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Low-Beta Power", f"{hist['pathological_beta_power'][-1]:.2f}%")
    m2.metric("High-Beta Power", f"{hist['high_beta_power'][-1]:.2f}%")
    m3.metric("LB Burst Duration", f"{hist['low_beta_burst_duration_ms'][-1]:.0f} ms")
    m4.metric("DBS Amplitude (mA)", f"{hist['dbs_amplitude_ma'][-1]:.2f}")
    m5.metric("Simulation Time (s)", f"{t[-1]:.1f}")

    closed_loop_arm = runner.comparison_arms["Closed-Loop DBS"]
    no_dbs_arm = runner.comparison_arms["No DBS"]
    fixed_arm = runner.comparison_arms["Fixed DBS"]
    if closed_loop_arm.cumulative_teed > 0 and no_dbs_arm.cumulative_patient_symptom_burden > 0:
        symptom_reduction = 1.0 - (
            closed_loop_arm.cumulative_patient_symptom_burden
            / max(no_dbs_arm.cumulative_patient_symptom_burden, 1e-6)
        )
        energy_vs_fixed = 1.0 - (
            closed_loop_arm.cumulative_teed / max(fixed_arm.cumulative_teed, 1e-6)
        )
        st.caption(
            f"Closed-Loop vs No DBS symptom reduction: **{symptom_reduction * 100:.1f}%** · "
            f"TEED savings vs Fixed DBS: **{energy_vs_fixed * 100:.1f}%**"
        )

    st.plotly_chart(build_stn_lfp_figure(t, list(hist["stn_lfp_uv"])), use_container_width=True, key="plot_stn_lfp")
    st.plotly_chart(
        build_beta_power_figure(
            t,
            list(hist["pathological_beta_power"]),
            list(hist["high_beta_power"]),
            list(hist["beta_detection_threshold"]),
        ),
        use_container_width=True,
        key="plot_beta_power",
    )
    st.plotly_chart(
        build_burst_duration_figure(t, list(hist["low_beta_burst_duration_ms"])),
        use_container_width=True,
        key="plot_burst",
    )
    st.plotly_chart(
        build_dbs_amplitude_figure(t, list(hist["dbs_amplitude_ma"])),
        use_container_width=True,
        key="plot_dbs_amp",
    )
    st.plotly_chart(
        build_closed_loop_efficiency_figure(runner.comparison_history),
        use_container_width=True,
        key="plot_efficiency",
    )


def main() -> None:
    st.set_page_config(
        page_title="Closed-Loop DBS Simulator",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_dark_theme_css()
    get_runner()

    st.markdown(
        """
        <div class="dbs-header">
            <h1>Medically Validated Closed-Loop DBS Simulator</h1>
            <p>STN LFP Beta Bursts → Validated Biomarker → ADAPT-PD aDBS → Literature Dose-Response Feedback</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    (
        control_mode,
        limits,
        dopaminergic_state,
        symptom_severity_scale,
        paused,
    ) = render_sidebar()

    st.markdown(
        "**Control Pipeline:** Simulated STN LFP w/ Pathological Beta Bursts (13–20 Hz LB) → "
        "% Total Power Biomarker Extraction → ADAPT-PD Therapy Parameter Calibration → "
        "Single/Dual Threshold aDBS *(control variable: LFP Beta Band Power)* → "
        "Literature Dose-Response Feedback to STN"
    )

    render_therapy_recommendation_panel()

    live_simulation_fragment(
        control_mode,
        limits,
        dopaminergic_state,
        symptom_severity_scale,
        paused,
    )

    st.markdown("---")
    st.markdown("### Pitch & Demo Guide")
    st.markdown(
        """
        1. **Start with `None (Open-Loop Baseline)`** — observe Low-Beta power near the literature OFF reference
           (~8.4% total power) and burst durations near 579 ms. Symptom burden accumulates from burst duration.

        2. **Switch to `Fixed DBS (cDBS)`** at 2.5 mA — Beta suppresses toward the therapeutic range (~2.1%),
           but TEED rises continuously (battery drain analogue).

        3. **Switch to `Adaptive DBS — Single Threshold`** — stimulation ramps in 250 ms when LFP power crosses
           the calibrated threshold, conserving TEED while suppressing flares.

        4. **Try `Dual Threshold`** for slow wearing-off dynamics (2.5 min ramp up / 5 min ramp down).

        5. **Toggle Dopaminergic ON** — burst durations shorten toward the literature ON mean (~359 ms).

        6. **Apply Recommended Therapy Parameters** — ADAPT-PD-style threshold calibration from the live timeline.
        """
    )

    st.markdown("---")
    st.markdown("### Clinical References")
    st.markdown(
        """
        - **Neumann et al., npj Parkinson's Disease 2022** — Beta-band suppression as chronic biomarker;
          dose-response at 0.5–2.5 mA; LB power OFF 8.43% → therapeutic 2.11%.
        - **Tinkhauser et al., Brain 2017** — Beta burst dynamics; 75th-percentile envelope detection;
          burst duration OFF > ON with levodopa.
        - **Anderson et al., npj Parkinson's Disease 2023** (n=106) — LB burst duration OFF 579 ms, ON 359 ms;
          strongest symptom correlation in 13–20 Hz band.
        - **Stanslaski et al., npj Parkinson's Disease 2024 (ADAPT-PD)** — Single Threshold (250 ms ramp) and
          Dual Threshold (2.5/5 min) aDBS; 8–30 Hz LFP control signal; TEED as primary energy endpoint.
        """
    )


if __name__ == "__main__":
    main()
