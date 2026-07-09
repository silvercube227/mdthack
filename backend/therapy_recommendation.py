"""Recommended therapy parameter inference — ADAPT-PD programming workflow."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.clinical_parameters import (
    CLINICAL_EFFECT_MA,
    LB_POWER_OFF_PCT,
    LOWER_STIM_MA,
    UPPER_STIM_MA,
)
from backend.constants import DBSControlMode


@dataclass(frozen=True)
class RecommendedTherapyParameters:
    lfp_threshold_pct: float
    lfp_upper_threshold_pct: float
    lfp_lower_threshold_pct: float
    lower_stim_ma: float
    upper_stim_ma: float
    dbs_control_mode: DBSControlMode
    clinical_rationale: str


def recommend_therapy_parameters(
    pathological_beta_power_history: list[float],
) -> RecommendedTherapyParameters:
    """
    ADAPT-PD-style parameter suggestion from chronic LFP timeline proxy.
    Threshold = median OFF-state LB power; limits from clinical effect range.
    """
    default = RecommendedTherapyParameters(
        lfp_threshold_pct=4.0,
        lfp_upper_threshold_pct=6.0,
        lfp_lower_threshold_pct=2.5,
        lower_stim_ma=LOWER_STIM_MA,
        upper_stim_ma=UPPER_STIM_MA,
        dbs_control_mode=DBSControlMode.ADAPTIVE_SINGLE_THRESHOLD,
        clinical_rationale=(
            "Collecting STN LFP for baseline calibration (~5 s). "
            f"Literature OFF-state LB power reference: {LB_POWER_OFF_PCT:.1f}% total."
        ),
    )

    if len(pathological_beta_power_history) < 64:
        return default

    recent = np.asarray(pathological_beta_power_history[-625:], dtype=float)
    baseline = float(np.median(recent[: min(len(recent), 250)]))
    if baseline <= 0:
        baseline = LB_POWER_OFF_PCT

    lfp_threshold_pct = float(np.clip(baseline * 0.75, 2.5, 8.0))
    lfp_upper_threshold_pct = float(np.clip(baseline * 0.95, lfp_threshold_pct + 0.5, 10.0))
    lfp_lower_threshold_pct = float(np.clip(baseline * 0.45, 1.5, lfp_threshold_pct - 0.3))

    volatility = float(np.std(recent[-250:]) / max(np.mean(recent[-250:]), 0.1))
    if volatility > 0.35:
        mode = DBSControlMode.ADAPTIVE_SINGLE_THRESHOLD
        rationale = (
            f"Rapid Beta fluctuations (σ/μ={volatility:.2f}) — ADAPT-PD Single Threshold "
            f"(250 ms ramp) recommended for event-triggered suppression."
        )
    else:
        mode = DBSControlMode.ADAPTIVE_DUAL_THRESHOLD
        rationale = (
            f"Slow Beta dynamics (σ/μ={volatility:.2f}) — ADAPT-PD Dual Threshold "
            f"(2.5 min up / 5 min down) recommended for gradual wearing-off control."
        )

    return RecommendedTherapyParameters(
        lfp_threshold_pct=lfp_threshold_pct,
        lfp_upper_threshold_pct=lfp_upper_threshold_pct,
        lfp_lower_threshold_pct=lfp_lower_threshold_pct,
        lower_stim_ma=CLINICAL_EFFECT_MA,
        upper_stim_ma=UPPER_STIM_MA,
        dbs_control_mode=mode,
        clinical_rationale=rationale,
    )
