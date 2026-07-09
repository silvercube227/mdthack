"""Closed-Loop DBS Simulator — Streamlit dashboard entry point."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from backend.constants import DBSControlMode
from frontend.plots import (
    build_beta_power_figure,
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
    beta_detection_threshold: float,
    controller_gain_kp: float,
    base_symptom_severity: float,
    neuromodulatory_gain: float,
    paused: bool,
) -> None:
    runner = get_runner()

    if not paused:
        runner.advance(
            control_mode,
            beta_detection_threshold,
            controller_gain_kp,
            base_symptom_severity,
            neuromodulatory_gain,
        )

    hist = runner.history
    t = list(hist["time_sec"])
    if not t:
        st.info("Initializing closed-loop neuromodulation simulation…")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pathological Beta Power", f"{hist['pathological_beta_power'][-1]:.3f}")
    m2.metric("DBS Amplitude (mA)", f"{hist['dbs_amplitude_ma'][-1]:.2f}")
    m3.metric("Simulation Time (s)", f"{t[-1]:.1f}")

    closed_loop_arm = runner.comparison_arms["Closed-Loop DBS"]
    efficiency = 0.0
    if closed_loop_arm.cumulative_total_energy_delivered > 0:
        efficiency = (
            1.0
            - closed_loop_arm.cumulative_patient_symptom_burden
            / max(runner.comparison_arms["No DBS"].cumulative_patient_symptom_burden, 1e-6)
        ) / max(closed_loop_arm.cumulative_total_energy_delivered, 1e-6)
        efficiency *= 100
    m4.metric("Closed-Loop Efficiency", f"{efficiency:.2f}" if efficiency else "—")

    st.plotly_chart(build_stn_lfp_figure(t, list(hist["stn_lfp_uv"])), use_container_width=True, key="plot_stn_lfp")
    st.plotly_chart(
        build_beta_power_figure(
            t,
            list(hist["pathological_beta_power"]),
            list(hist["beta_detection_threshold"]),
        ),
        use_container_width=True,
        key="plot_beta_power",
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
            <h1>Closed-Loop Deep Brain Stimulation (DBS) Simulator</h1>
            <p>Subthalamic Nucleus LFP → Pathological Beta Biomarker → Controller → Virtual DBS Feedback Loop</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    (
        control_mode,
        beta_detection_threshold,
        controller_gain_kp,
        base_symptom_severity,
        neuromodulatory_gain,
        paused,
    ) = render_sidebar()

    st.markdown(
        "**Control Pipeline:** Simulated STN LFP w/ Pathological Beta Waves → "
        "Band-Pass Biomarker Extraction → Recommended Therapy Parameters → "
        "Adaptive DBS (aDBS) w/ Proportional Control *(control variable: Beta Band Power)* → "
        "Neuromodulatory Feedback to STN"
    )

    render_therapy_recommendation_panel()

    live_simulation_fragment(
        control_mode,
        beta_detection_threshold,
        controller_gain_kp,
        base_symptom_severity,
        neuromodulatory_gain,
        paused,
    )

    st.markdown("---")
    st.markdown("### Pitch & Demo Guide")
    st.markdown(
        """
        **For judges — how to demo this closed-loop neuromodulation system:**

        1. **Start with `None (Open-Loop Baseline)`** — observe unchecked Pathological Beta Band Power waxing
           and waning as the Parkinsonian symptom flare evolves. Note the elevated cumulative Patient Symptom Burden
           in the left panel of the Closed-Loop Efficiency Metric plot.

        2. **Switch to `Fixed DBS`** — the controller delivers a constant, unyielding DBS Amplitude (mA) regardless
           of brain state. Symptom Burden drops, but **Total Energy Delivered** rises continuously — mimicking
           accelerated implant battery depletion in clinical fixed-parameter DBS.

        3. **Switch to `Proportional (Adaptive) DBS`** — stimulation scales with
           real-time Pathological Beta Power. When Beta activity falls, DBS Amplitude
           scales back, **conserving energy** while maintaining superior symptom suppression during flares.

        4. **Adjust the Pathological Beta Detection Threshold and Controller Gain (Kp)** — show how therapy
           parameters tune the trade-off between aggressive Beta suppression and energy efficiency.

        5. **Read the Money Plot** — the green **Closed-Loop DBS** trace achieves comparable or lower cumulative
           Patient Symptom Burden than Fixed DBS while delivering substantially less Total Energy — the core value
           proposition of closed-loop neuromodulation: **better symptom control per milliamp delivered**, extending
           neurostimulator battery life and reducing unnecessary tissue stimulation.
        """
    )


if __name__ == "__main__":
    main()
