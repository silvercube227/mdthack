"""Plotly visualization helpers for the closed-loop DBS dashboard."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from backend.clinical_parameters import LB_POWER_OFF_PCT, LB_POWER_THERAPEUTIC_PCT, MAX_STIM_MA

SCROLL_WINDOW_SEC = 15.0
MAX_DISPLAY_POINTS = 450
UI_REVISION = "dbs-live"

PLOTLY_DARK_LAYOUT = dict(
    paper_bgcolor="#0e1117",
    plot_bgcolor="#161b26",
    font=dict(color="#e6edf3", family="Inter, Segoe UI, sans-serif", size=12),
    margin=dict(l=48, r=24, t=48, b=40),
    hovermode="x unified",
    legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02, x=0),
)


def _axis(title: str) -> dict:
    return dict(
        title=dict(text=title, font=dict(color="#c9d1d9")),
        gridcolor="#2a3142",
        zerolinecolor="#3d4659",
        linecolor="#3d4659",
        tickfont=dict(color="#9ba7b8"),
    )


def decimate_scroll_window(
    time_sec: Sequence[float],
    *series: Sequence[float],
    window_sec: float = SCROLL_WINDOW_SEC,
    max_points: int = MAX_DISPLAY_POINTS,
) -> Tuple[List[float], ...]:
    """Return the trailing time window, decimated for smooth live rendering."""
    if not time_sec:
        return ((),) + ((),) * len(series)

    t = list(time_sec)
    t_max = t[-1]
    t_min = max(0.0, t_max - window_sec)
    start = 0
    for i, tv in enumerate(t):
        if tv >= t_min:
            start = i
            break

    t_win = t[start:]
    arrs = [list(series[i])[start:] for i in range(len(series))]
    n = len(t_win)
    if n > max_points:
        step = max(n // max_points, 1)
        idx = list(range(0, n, step))
        t_win = [t_win[i] for i in idx]
        arrs = [[arr[i] for i in idx] for arr in arrs]

    return (t_win, *arrs)


def _scroll_x_range(t: Sequence[float]) -> Optional[List[float]]:
    if not t:
        return None
    t_max = t[-1]
    if t_max <= SCROLL_WINDOW_SEC:
        return [0.0, max(SCROLL_WINDOW_SEC, t_max + 0.05)]
    return [t_max - SCROLL_WINDOW_SEC, t_max + 0.05]


def _intervention_shape(
    intervention_time_sec: Optional[float],
    intervention_label: Optional[str] = None,
) -> Optional[dict]:
    if intervention_time_sec is None:
        return None
    short_label = (intervention_label or "Intervention").split("(")[0].strip()
    return dict(
        type="line",
        x0=intervention_time_sec,
        x1=intervention_time_sec,
        y0=0,
        y1=1,
        xref="x",
        yref="paper",
        line=dict(color="#f0883e", width=2, dash="dash"),
        label=dict(
            text=f"Intervention: {short_label}",
            textposition="end",
            font=dict(color="#f0883e", size=11),
        ),
    )


def _apply_scroll_layout(
    fig: go.Figure,
    t: Sequence[float],
    intervention_time_sec: Optional[float] = None,
    intervention_label: Optional[str] = None,
) -> None:
    x_range = _scroll_x_range(t)
    shape = _intervention_shape(intervention_time_sec, intervention_label)
    shapes = [shape] if shape else []
    fig.update_layout(
        xaxis=dict(range=x_range, autorange=False) if x_range else dict(autorange=True),
        shapes=shapes,
        uirevision=UI_REVISION,
    )


def create_plot_figures() -> Dict[str, go.Figure]:
    """Create empty figures once; traces are updated in place to avoid flicker."""
    stn = go.Figure()
    stn.add_trace(
        go.Scattergl(x=[], y=[], mode="lines", name="STN LFP", line=dict(color="#58a6ff", width=1.2))
    )
    stn.update_layout(
        **PLOTLY_DARK_LAYOUT,
        title="Subthalamic Nucleus (STN) LFP — Raw Local Field Potential",
        height=260,
        xaxis=_axis("Time (s)"),
        yaxis=_axis("Amplitude (µV)"),
        showlegend=False,
        uirevision=UI_REVISION,
    )

    beta = go.Figure()
    beta.add_trace(
        go.Scattergl(x=[], y=[], mode="lines", name="Low-Beta Power (13–20 Hz)", line=dict(color="#f78166", width=2))
    )
    beta.add_trace(
        go.Scattergl(x=[], y=[], mode="lines", name="High-Beta Power (20–35 Hz)", line=dict(color="#d2a8ff", width=1.5))
    )
    beta.add_trace(
        go.Scattergl(
            x=[], y=[], mode="lines", name="LFP Detection Threshold", line=dict(color="#ffa657", width=1.5, dash="dash")
        )
    )
    beta.update_layout(
        **PLOTLY_DARK_LAYOUT,
        title="Pathological Beta Band Power (% Total Spectral Power)",
        height=280,
        xaxis=_axis("Time (s)"),
        yaxis=_axis("Power (% total)"),
        uirevision=UI_REVISION,
    )
    beta.add_hline(
        y=LB_POWER_OFF_PCT,
        line=dict(color="#8b949e", dash="dot", width=1),
        annotation_text="Literature OFF (8.4%)",
        annotation_position="right",
    )
    beta.add_hline(
        y=LB_POWER_THERAPEUTIC_PCT,
        line=dict(color="#3fb950", dash="dot", width=1),
        annotation_text="Therapeutic (2.1%)",
        annotation_position="right",
    )

    burst = go.Figure()
    burst.add_trace(
        go.Scattergl(
            x=[],
            y=[],
            mode="lines",
            name="LB Burst Duration",
            line=dict(color="#ffa657", width=1.8),
            fill="tozeroy",
            fillcolor="rgba(255, 166, 87, 0.12)",
        )
    )
    burst.update_layout(
        **PLOTLY_DARK_LAYOUT,
        title="Low-Beta Burst Duration (75th-Percentile Envelope Detection)",
        height=240,
        xaxis=_axis("Time (s)"),
        yaxis=_axis("Burst Duration (ms)"),
        showlegend=False,
        uirevision=UI_REVISION,
    )
    burst.add_hline(y=579, line=dict(color="#8b949e", dash="dash", width=1), annotation_text="OFF mean (579 ms)")
    burst.add_hline(y=359, line=dict(color="#3fb950", dash="dash", width=1), annotation_text="ON mean (359 ms)")

    dbs = go.Figure()
    dbs.add_trace(
        go.Scattergl(
            x=[],
            y=[],
            mode="lines",
            fill="tozeroy",
            name="DBS Amplitude",
            line=dict(color="#3fb950", width=1.8),
            fillcolor="rgba(63, 185, 80, 0.18)",
        )
    )
    dbs.update_layout(
        **PLOTLY_DARK_LAYOUT,
        title="DBS Amplitude (mA) — Neuromodulatory Controller Output",
        height=240,
        xaxis=_axis("Time (s)"),
        yaxis=_axis("DBS Amplitude (mA)"),
        yaxis_range=[0, MAX_STIM_MA * 1.05],
        showlegend=False,
        uirevision=UI_REVISION,
    )

    efficiency = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            "Cumulative Patient Symptom Burden (Burst Duration × Time)",
            "Total Energy Delivered — TEED Proxy",
        ),
        horizontal_spacing=0.10,
    )
    colors = {"No DBS": "#8b949e", "Fixed DBS": "#d2a8ff", "Closed-Loop DBS": "#3fb950"}
    for label, color in colors.items():
        efficiency.add_trace(
            go.Scattergl(x=[], y=[], mode="lines", name=label, line=dict(color=color, width=2.5)),
            row=1,
            col=1,
        )
        efficiency.add_trace(
            go.Scattergl(x=[], y=[], mode="lines", name=label, line=dict(color=color, width=2.5), showlegend=False),
            row=1,
            col=2,
        )
    efficiency.update_layout(
        **PLOTLY_DARK_LAYOUT,
        title="Closed-Loop Efficiency Metric — Symptom Suppression vs. TEED",
        height=320,
        uirevision=UI_REVISION,
    )
    efficiency.update_xaxes(**_axis("Time (s)"), row=1, col=1)
    efficiency.update_xaxes(**_axis("Time (s)"), row=1, col=2)
    efficiency.update_yaxes(**_axis("Cumulative Burden (ms·s)"), row=1, col=1)
    efficiency.update_yaxes(**_axis("TEED Proxy (mA²·s)"), row=1, col=2)

    return {
        "stn_lfp": stn,
        "beta_power": beta,
        "burst": burst,
        "dbs_amp": dbs,
        "efficiency": efficiency,
    }


def update_live_plots(
    figures: Dict[str, go.Figure],
    history: dict,
    comparison_history: dict,
    intervention_time_sec: Optional[float] = None,
    intervention_label: Optional[str] = None,
) -> None:
    """Update trace data in place — no full figure rebuild."""
    t, lfp = decimate_scroll_window(history["time_sec"], history["stn_lfp_uv"])
    _, lb, hb, thr = decimate_scroll_window(
        history["time_sec"],
        history["pathological_beta_power"],
        history["high_beta_power"],
        history["beta_detection_threshold"],
    )
    _, burst = decimate_scroll_window(history["time_sec"], history["low_beta_burst_duration_ms"])
    _, dbs = decimate_scroll_window(history["time_sec"], history["dbs_amplitude_ma"])

    stn_fig = figures["stn_lfp"]
    stn_fig.data[0].x = t
    stn_fig.data[0].y = lfp
    _apply_scroll_layout(stn_fig, t, intervention_time_sec, intervention_label)

    beta_fig = figures["beta_power"]
    beta_fig.data[0].x = t
    beta_fig.data[0].y = lb
    beta_fig.data[1].x = t
    beta_fig.data[1].y = hb
    beta_fig.data[2].x = t
    beta_fig.data[2].y = thr
    _apply_scroll_layout(beta_fig, t, intervention_time_sec, intervention_label)

    burst_fig = figures["burst"]
    burst_fig.data[0].x = t
    burst_fig.data[0].y = burst
    _apply_scroll_layout(burst_fig, t, intervention_time_sec, intervention_label)

    dbs_fig = figures["dbs_amp"]
    dbs_fig.data[0].x = t
    dbs_fig.data[0].y = dbs
    _apply_scroll_layout(dbs_fig, t, intervention_time_sec, intervention_label)

    eff_fig = figures["efficiency"]
    labels = ["No DBS", "Fixed DBS", "Closed-Loop DBS"]
    x_range = _scroll_x_range(t)
    for i, label in enumerate(labels):
        comp = comparison_history[label]
        ct, symptom, energy = decimate_scroll_window(
            comp["time_sec"],
            comp["cumulative_patient_symptom_burden"],
            comp["cumulative_total_energy_delivered"],
        )
        eff_fig.data[i * 2].x = ct
        eff_fig.data[i * 2].y = symptom
        eff_fig.data[i * 2 + 1].x = ct
        eff_fig.data[i * 2 + 1].y = energy

    shape = _intervention_shape(intervention_time_sec, intervention_label)
    shapes = [shape] if shape else []
    eff_fig.update_layout(
        shapes=shapes,
        uirevision=UI_REVISION,
    )
    if x_range:
        eff_fig.update_xaxes(range=x_range, autorange=False, row=1, col=1)
        eff_fig.update_xaxes(range=x_range, autorange=False, row=1, col=2)


# Legacy one-shot builders kept for tests / scripts
def build_stn_lfp_figure(
    time_sec: List[float],
    stn_lfp_uv: List[float],
    intervention_time_sec: Optional[float] = None,
    intervention_label: Optional[str] = None,
) -> go.Figure:
    figures = create_plot_figures()
    update_live_plots(
        figures,
        {
            "time_sec": time_sec,
            "stn_lfp_uv": stn_lfp_uv,
            "pathological_beta_power": [],
            "high_beta_power": [],
            "beta_detection_threshold": [],
            "low_beta_burst_duration_ms": [],
            "dbs_amplitude_ma": [],
        },
        {"No DBS": {"time_sec": [], "cumulative_patient_symptom_burden": [], "cumulative_total_energy_delivered": []},
         "Fixed DBS": {"time_sec": [], "cumulative_patient_symptom_burden": [], "cumulative_total_energy_delivered": []},
         "Closed-Loop DBS": {"time_sec": [], "cumulative_patient_symptom_burden": [], "cumulative_total_energy_delivered": []}},
        intervention_time_sec,
        intervention_label,
    )
    return figures["stn_lfp"]


def build_beta_power_figure(
    time_sec: List[float],
    lb_power: List[float],
    hb_power: List[float],
    threshold: List[float],
    intervention_time_sec: Optional[float] = None,
    intervention_label: Optional[str] = None,
) -> go.Figure:
    figures = create_plot_figures()
    update_live_plots(
        figures,
        {
            "time_sec": time_sec,
            "stn_lfp_uv": [],
            "pathological_beta_power": lb_power,
            "high_beta_power": hb_power,
            "beta_detection_threshold": threshold,
            "low_beta_burst_duration_ms": [],
            "dbs_amplitude_ma": [],
        },
        {"No DBS": {"time_sec": [], "cumulative_patient_symptom_burden": [], "cumulative_total_energy_delivered": []},
         "Fixed DBS": {"time_sec": [], "cumulative_patient_symptom_burden": [], "cumulative_total_energy_delivered": []},
         "Closed-Loop DBS": {"time_sec": [], "cumulative_patient_symptom_burden": [], "cumulative_total_energy_delivered": []}},
        intervention_time_sec,
        intervention_label,
    )
    return figures["beta_power"]


def build_burst_duration_figure(
    time_sec: List[float],
    burst_duration_ms: List[float],
    intervention_time_sec: Optional[float] = None,
    intervention_label: Optional[str] = None,
) -> go.Figure:
    figures = create_plot_figures()
    update_live_plots(
        figures,
        {
            "time_sec": time_sec,
            "stn_lfp_uv": [],
            "pathological_beta_power": [],
            "high_beta_power": [],
            "beta_detection_threshold": [],
            "low_beta_burst_duration_ms": burst_duration_ms,
            "dbs_amplitude_ma": [],
        },
        {"No DBS": {"time_sec": [], "cumulative_patient_symptom_burden": [], "cumulative_total_energy_delivered": []},
         "Fixed DBS": {"time_sec": [], "cumulative_patient_symptom_burden": [], "cumulative_total_energy_delivered": []},
         "Closed-Loop DBS": {"time_sec": [], "cumulative_patient_symptom_burden": [], "cumulative_total_energy_delivered": []}},
        intervention_time_sec,
        intervention_label,
    )
    return figures["burst"]


def build_dbs_amplitude_figure(
    time_sec: List[float],
    dbs_amplitude_ma: List[float],
    intervention_time_sec: Optional[float] = None,
    intervention_label: Optional[str] = None,
) -> go.Figure:
    figures = create_plot_figures()
    update_live_plots(
        figures,
        {
            "time_sec": time_sec,
            "stn_lfp_uv": [],
            "pathological_beta_power": [],
            "high_beta_power": [],
            "beta_detection_threshold": [],
            "low_beta_burst_duration_ms": [],
            "dbs_amplitude_ma": dbs_amplitude_ma,
        },
        {"No DBS": {"time_sec": [], "cumulative_patient_symptom_burden": [], "cumulative_total_energy_delivered": []},
         "Fixed DBS": {"time_sec": [], "cumulative_patient_symptom_burden": [], "cumulative_total_energy_delivered": []},
         "Closed-Loop DBS": {"time_sec": [], "cumulative_patient_symptom_burden": [], "cumulative_total_energy_delivered": []}},
        intervention_time_sec,
        intervention_label,
    )
    return figures["dbs_amp"]


def build_closed_loop_efficiency_figure(
    comparison_history: dict,
    intervention_time_sec: Optional[float] = None,
    intervention_label: Optional[str] = None,
) -> go.Figure:
    figures = create_plot_figures()
    t = list(comparison_history["No DBS"]["time_sec"])
    update_live_plots(
        figures,
        {
            "time_sec": t,
            "stn_lfp_uv": [],
            "pathological_beta_power": [],
            "high_beta_power": [],
            "beta_detection_threshold": [],
            "low_beta_burst_duration_ms": [],
            "dbs_amplitude_ma": [],
        },
        comparison_history,
        intervention_time_sec,
        intervention_label,
    )
    return figures["efficiency"]
