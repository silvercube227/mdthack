"""Plotly visualization helpers for the closed-loop DBS dashboard."""

from __future__ import annotations

from typing import List

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from backend.constants import MAX_STIM_MA

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
        height=280,
        xaxis=_axis("Time (s)"),
        yaxis=_axis("Amplitude (µV)"),
        showlegend=False,
    )
    return fig


def build_beta_power_figure(
    time_sec: List[float],
    beta_power: List[float],
    threshold: List[float],
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=time_sec,
            y=beta_power,
            mode="lines",
            name="Pathological Beta Band Power",
            line=dict(color="#f78166", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=time_sec,
            y=threshold,
            mode="lines",
            name="Beta Detection Threshold",
            line=dict(color="#ffa657", width=1.5, dash="dash"),
        )
    )
    fig.update_layout(
        **PLOTLY_DARK_LAYOUT,
        title="Real-Time Pathological Beta Band Power (13–30 Hz Biomarker)",
        height=280,
        xaxis=_axis("Time (s)"),
        yaxis=_axis("Normalized Beta Power"),
        yaxis_range=[0, 1.05],
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
        height=280,
        xaxis=_axis("Time (s)"),
        yaxis=_axis("DBS Amplitude (mA)"),
        yaxis_range=[0, MAX_STIM_MA * 1.05],
        showlegend=False,
    )
    return fig


def build_closed_loop_efficiency_figure(comparison_history: dict) -> go.Figure:
    """Money Plot: cumulative symptom burden vs total energy across DBS strategies."""
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            "Cumulative Patient Symptom Burden",
            "Total Energy Delivered (Closed-Loop Efficiency Metric)",
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
        title="Closed-Loop Efficiency Metric — Symptom Suppression vs. Energy Delivered",
        height=340,
        barmode="group",
    )
    fig.update_xaxes(**_axis("Time (s)"), row=1, col=1)
    fig.update_xaxes(**_axis("Time (s)"), row=1, col=2)
    fig.update_yaxes(**_axis("Cumulative Symptom Burden (a.u.)"), row=1, col=1)
    fig.update_yaxes(**_axis("Total Energy (mA·s)"), row=1, col=2)

    return fig
