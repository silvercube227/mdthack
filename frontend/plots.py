"""Plotly visualization helpers for the closed-loop DBS dashboard."""

from __future__ import annotations

from typing import List

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from backend.clinical_parameters import LB_POWER_OFF_PCT, LB_POWER_THERAPEUTIC_PCT, MAX_STIM_MA

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


def build_stn_lfp_figure(time_sec: List[float], stn_lfp_uv: List[float]) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=time_sec,
            y=stn_lfp_uv,
            mode="lines",
            name="STN LFP",
            line=dict(color="#58a6ff", width=1.2),
        )
    )
    fig.update_layout(
        **PLOTLY_DARK_LAYOUT,
        title="Subthalamic Nucleus (STN) LFP — Raw Local Field Potential",
        height=260,
        xaxis=_axis("Time (s)"),
        yaxis=_axis("Amplitude (µV)"),
        showlegend=False,
    )
    return fig


def build_beta_power_figure(
    time_sec: List[float],
    lb_power: List[float],
    hb_power: List[float],
    threshold: List[float],
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=time_sec,
            y=lb_power,
            mode="lines",
            name="Low-Beta Power (13–20 Hz)",
            line=dict(color="#f78166", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=time_sec,
            y=hb_power,
            mode="lines",
            name="High-Beta Power (20–35 Hz)",
            line=dict(color="#d2a8ff", width=1.5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=time_sec,
            y=threshold,
            mode="lines",
            name="LFP Detection Threshold",
            line=dict(color="#ffa657", width=1.5, dash="dash"),
        )
    )
    fig.add_hline(
        y=LB_POWER_OFF_PCT,
        line=dict(color="#8b949e", dash="dot", width=1),
        annotation_text="Literature OFF (8.4%)",
        annotation_position="right",
    )
    fig.add_hline(
        y=LB_POWER_THERAPEUTIC_PCT,
        line=dict(color="#3fb950", dash="dot", width=1),
        annotation_text="Therapeutic (2.1%)",
        annotation_position="right",
    )
    fig.update_layout(
        **PLOTLY_DARK_LAYOUT,
        title="Pathological Beta Band Power (% Total Spectral Power)",
        height=280,
        xaxis=_axis("Time (s)"),
        yaxis=_axis("Power (% total)"),
    )
    return fig


def build_burst_duration_figure(time_sec: List[float], burst_duration_ms: List[float]) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=time_sec,
            y=burst_duration_ms,
            mode="lines",
            name="LB Burst Duration",
            line=dict(color="#ffa657", width=1.8),
            fill="tozeroy",
            fillcolor="rgba(255, 166, 87, 0.12)",
        )
    )
    fig.add_hline(
        y=579,
        line=dict(color="#8b949e", dash="dash", width=1),
        annotation_text="OFF mean (579 ms)",
    )
    fig.add_hline(
        y=359,
        line=dict(color="#3fb950", dash="dash", width=1),
        annotation_text="ON mean (359 ms)",
    )
    fig.update_layout(
        **PLOTLY_DARK_LAYOUT,
        title="Low-Beta Burst Duration (75th-Percentile Envelope Detection)",
        height=240,
        xaxis=_axis("Time (s)"),
        yaxis=_axis("Burst Duration (ms)"),
        showlegend=False,
    )
    return fig


def build_dbs_amplitude_figure(time_sec: List[float], dbs_amplitude_ma: List[float]) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=time_sec,
            y=dbs_amplitude_ma,
            mode="lines",
            fill="tozeroy",
            name="DBS Amplitude",
            line=dict(color="#3fb950", width=1.8),
            fillcolor="rgba(63, 185, 80, 0.18)",
        )
    )
    fig.update_layout(
        **PLOTLY_DARK_LAYOUT,
        title="DBS Amplitude (mA) — Neuromodulatory Controller Output",
        height=240,
        xaxis=_axis("Time (s)"),
        yaxis=_axis("DBS Amplitude (mA)"),
        yaxis_range=[0, MAX_STIM_MA * 1.05],
        showlegend=False,
    )
    return fig


def build_closed_loop_efficiency_figure(comparison_history: dict) -> go.Figure:
    """Money Plot: cumulative symptom burden vs TEED across DBS strategies."""
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            "Cumulative Patient Symptom Burden (Burst Duration × Time)",
            "Total Energy Delivered — TEED Proxy",
        ),
        horizontal_spacing=0.10,
    )

    colors = {
        "No DBS": "#8b949e",
        "Fixed DBS": "#d2a8ff",
        "Closed-Loop DBS": "#3fb950",
    }

    for label, hist in comparison_history.items():
        t = list(hist["time_sec"])
        symptom = list(hist["cumulative_patient_symptom_burden"])
        energy = list(hist["cumulative_total_energy_delivered"])
        color = colors.get(label, "#58a6ff")

        fig.add_trace(
            go.Scatter(x=t, y=symptom, mode="lines", name=label, line=dict(color=color, width=2.5)),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=t, y=energy, mode="lines", name=label, line=dict(color=color, width=2.5), showlegend=False),
            row=1,
            col=2,
        )

    fig.update_layout(
        **PLOTLY_DARK_LAYOUT,
        title="Closed-Loop Efficiency Metric — Symptom Suppression vs. TEED",
        height=320,
    )
    fig.update_xaxes(**_axis("Time (s)"), row=1, col=1)
    fig.update_xaxes(**_axis("Time (s)"), row=1, col=2)
    fig.update_yaxes(**_axis("Cumulative Burden (ms·s)"), row=1, col=1)
    fig.update_yaxes(**_axis("TEED Proxy (mA²·s)"), row=1, col=2)

    return fig
