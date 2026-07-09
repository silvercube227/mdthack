"""Recommended therapy parameter inference from Pathological Beta biomarker history."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.constants import DBSControlMode


@dataclass(frozen=True)
class RecommendedTherapyParameters:
    pathological_beta_detection_threshold: float
    controller_gain_kp: float
    dbs_control_mode: DBSControlMode
    clinical_rationale: str


def recommend_therapy_parameters(pathological_beta_power_history: list[float]) -> RecommendedTherapyParameters:
    """
    Map recent Pathological Beta Band Power to suggested closed-loop DBS settings.
    """
    if len(pathological_beta_power_history) < 64:
        return RecommendedTherapyParameters(
            pathological_beta_detection_threshold=0.45,
            controller_gain_kp=4.0,
            dbs_control_mode=DBSControlMode.PROPORTIONAL,
            clinical_rationale=(
                "Collecting STN LFP — default proportional aDBS parameters until biomarker window fills."
            ),
        )

    recent = np.asarray(pathological_beta_power_history[-512:], dtype=float)
    mean_beta = float(np.mean(recent))
    peak_beta = float(np.percentile(recent, 85))

    pathological_beta_detection_threshold = float(np.clip(mean_beta * 0.82, 0.12, 0.82))

    if mean_beta >= 0.58:
        controller_gain_kp = float(np.clip(4.5 + (mean_beta - 0.58) * 10.0, 4.0, 8.0))
        dbs_control_mode = DBSControlMode.PROPORTIONAL
        clinical_rationale = (
            f"Peak Pathological Beta Power ({peak_beta:.2f}) indicates active symptom flare — "
            "increase Controller Gain (Kp) for aggressive proportional aDBS suppression."
        )
    elif mean_beta >= 0.38:
        controller_gain_kp = float(np.clip(2.8 + mean_beta * 4.0, 2.5, 6.5))
        dbs_control_mode = DBSControlMode.PROPORTIONAL
        clinical_rationale = (
            f"Moderate Beta burden (mean {mean_beta:.2f}) — proportional adaptive DBS balances "
            "symptom control and neurostimulator energy delivery."
        )
    else:
        controller_gain_kp = float(np.clip(1.2 + mean_beta * 3.0, 0.8, 3.5))
        dbs_control_mode = DBSControlMode.PROPORTIONAL
        clinical_rationale = (
            f"Sub-threshold Beta activity (mean {mean_beta:.2f}) — low Neuromodulatory Gain advised "
            "to minimize unnecessary tissue stimulation."
        )

    return RecommendedTherapyParameters(
        pathological_beta_detection_threshold=pathological_beta_detection_threshold,
        controller_gain_kp=controller_gain_kp,
        dbs_control_mode=dbs_control_mode,
        clinical_rationale=clinical_rationale,
    )
