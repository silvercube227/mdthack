"""Module 4: Virtual DBS feedback loop orchestration and comparison simulations."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from backend.clinical_parameters import (
    BURST_DURATION_OFF_MS,
    DOSE_RESPONSE_BETA_PCT,
    DopaminergicState,
    LB_POWER_OFF_PCT,
    low_beta_power_pct_from_stim_ma,
)
from backend.constants import DBSControlMode, MAX_HISTORY_SECONDS, SAMPLE_RATE_HZ, TICKS_PER_FRAME
from backend.controller import ControllerLimits, DBSControllerLayer, compute_teed_increment
from backend.signal_cleaning import PathologicalBetaExtractor
from backend.signal_generator import SimulatedSTNBrain


def _display_burst_duration_ms(
    brain: SimulatedSTNBrain,
    extractor: PathologicalBetaExtractor,
) -> float:
    """
    Burst duration for charts: literature-scaled expected length during active
    generator bursts (responds to DBS), else envelope-detected duration.
    """
    if brain.burst_active:
        return brain._mean_burst_duration_ms()
    return extractor.low_beta_burst_duration_ms


@dataclass
class ComparisonArmState:
    brain: SimulatedSTNBrain
    extractor: PathologicalBetaExtractor
    controller: DBSControllerLayer
    control_mode: DBSControlMode
    prior_dbs_amplitude_ma: float = 0.0
    cumulative_patient_symptom_burden: float = 0.0
    cumulative_teed: float = 0.0


def _effective_lb_power_pct(measured_pct: float, dbs_amplitude_ma: float) -> float:
    """Blend measured biomarker with literature dose-response for display."""
    if dbs_amplitude_ma <= 0.0:
        return float(0.35 * measured_pct + 0.65 * LB_POWER_OFF_PCT)
    table_target = low_beta_power_pct_from_stim_ma(dbs_amplitude_ma)
    literature_target = LB_POWER_OFF_PCT * (table_target / DOSE_RESPONSE_BETA_PCT[0])
    return float(0.7 * literature_target + 0.3 * measured_pct)


def _comparison_mode_for_arm(
    label: str,
    sim_time_sec: float,
    intervention_time_sec: Optional[float],
    user_control_mode: DBSControlMode,
) -> DBSControlMode:
    """Shadow arms stay untreated until intervention; then Fixed / Closed-Loop diverge."""
    if intervention_time_sec is None or sim_time_sec < intervention_time_sec:
        return DBSControlMode.NONE
    if label == "No DBS":
        return DBSControlMode.NONE
    if label == "Fixed DBS":
        return DBSControlMode.FIXED
    if user_control_mode in (
        DBSControlMode.ADAPTIVE_SINGLE_THRESHOLD,
        DBSControlMode.ADAPTIVE_DUAL_THRESHOLD,
    ):
        return user_control_mode
    return DBSControlMode.ADAPTIVE_SINGLE_THRESHOLD


def _create_comparison_arms() -> Dict[str, ComparisonArmState]:
    return {
        "No DBS": ComparisonArmState(
            brain=SimulatedSTNBrain(rng=np.random.default_rng(42)),
            extractor=PathologicalBetaExtractor(),
            controller=DBSControllerLayer(),
            control_mode=DBSControlMode.NONE,
        ),
        "Fixed DBS": ComparisonArmState(
            brain=SimulatedSTNBrain(rng=np.random.default_rng(42)),
            extractor=PathologicalBetaExtractor(),
            controller=DBSControllerLayer(),
            control_mode=DBSControlMode.FIXED,
        ),
        "Closed-Loop DBS": ComparisonArmState(
            brain=SimulatedSTNBrain(rng=np.random.default_rng(42)),
            extractor=PathologicalBetaExtractor(),
            controller=DBSControllerLayer(),
            control_mode=DBSControlMode.ADAPTIVE_SINGLE_THRESHOLD,
        ),
    }


class SimulationRunner:
    """Stateful closed-loop DBS simulation engine (no UI dependencies)."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        max_samples = int(MAX_HISTORY_SECONDS * SAMPLE_RATE_HZ)

        self.main_brain = SimulatedSTNBrain()
        self.main_extractor = PathologicalBetaExtractor()
        self.main_controller = DBSControllerLayer()
        self.prior_dbs_amplitude_ma = 0.0
        self.sim_time_sec = 0.0

        self.history = {
            "time_sec": deque(maxlen=max_samples),
            "stn_lfp_uv": deque(maxlen=max_samples),
            "pathological_beta_power": deque(maxlen=max_samples),
            "high_beta_power": deque(maxlen=max_samples),
            "low_beta_burst_duration_ms": deque(maxlen=max_samples),
            "dbs_amplitude_ma": deque(maxlen=max_samples),
            "beta_detection_threshold": deque(maxlen=max_samples),
        }

        self.comparison_arms = _create_comparison_arms()
        self.comparison_history = {
            label: {
                "time_sec": deque(maxlen=max_samples),
                "cumulative_patient_symptom_burden": deque(maxlen=max_samples),
                "cumulative_total_energy_delivered": deque(maxlen=max_samples),
            }
            for label in self.comparison_arms
        }

    def reset_comparison_arms(self) -> None:
        """Reset shadow comparison sims (e.g. on full baseline reset)."""
        max_samples = int(MAX_HISTORY_SECONDS * SAMPLE_RATE_HZ)
        self.comparison_arms = _create_comparison_arms()
        self.comparison_history = {
            label: {
                "time_sec": deque(maxlen=max_samples),
                "cumulative_patient_symptom_burden": deque(maxlen=max_samples),
                "cumulative_total_energy_delivered": deque(maxlen=max_samples),
            }
            for label in self.comparison_arms
        }

    def _symptom_increment(
        self,
        burst_ms: float,
        lb_power_pct: float,
        dt_sec: float,
    ) -> float:
        beta_fraction = lb_power_pct / LB_POWER_OFF_PCT
        burst_factor = burst_ms / BURST_DURATION_OFF_MS if burst_ms > 0.0 else 0.0
        return beta_fraction * (1.0 + burst_factor) * dt_sec

    def _advance_comparison_arm(
        self,
        label: str,
        arm: ComparisonArmState,
        dt_sec: float,
        limits: ControllerLimits,
        dopaminergic_state: DopaminergicState,
        symptom_severity_scale: float,
        intervention_time_sec: Optional[float],
        user_control_mode: DBSControlMode,
    ) -> None:
        arm.brain.dopaminergic_state = dopaminergic_state
        arm.brain.symptom_severity_scale = symptom_severity_scale

        active_mode = _comparison_mode_for_arm(
            label, self.sim_time_sec, intervention_time_sec, user_control_mode
        )

        stn_lfp = arm.brain.generate_stn_lfp_sample(arm.prior_dbs_amplitude_ma)
        arm.extractor.ingest_stn_lfp_sample(stn_lfp)
        measured_lb = arm.extractor.compute_pathological_beta_power()

        dbs_amplitude = arm.controller.compute_dbs_amplitude_ma(
            active_mode, measured_lb, limits, dt_sec
        )
        lb_power_pct = _effective_lb_power_pct(measured_lb, dbs_amplitude)

        burst_ms = _display_burst_duration_ms(arm.brain, arm.extractor)

        arm.cumulative_patient_symptom_burden += self._symptom_increment(burst_ms, lb_power_pct, dt_sec)
        arm.cumulative_teed += compute_teed_increment(dbs_amplitude, dt_sec)
        arm.prior_dbs_amplitude_ma = dbs_amplitude

    def advance(
        self,
        control_mode: DBSControlMode,
        limits: ControllerLimits,
        dopaminergic_state: DopaminergicState,
        symptom_severity_scale: float,
        intervention_time_sec: Optional[float] = None,
    ) -> None:
        """Advance primary + shadow simulations by TICKS_PER_FRAME samples."""
        dt_sec = 1.0 / SAMPLE_RATE_HZ

        self.main_brain.dopaminergic_state = dopaminergic_state
        self.main_brain.symptom_severity_scale = symptom_severity_scale

        for arm in self.comparison_arms.values():
            arm.brain.dopaminergic_state = dopaminergic_state
            arm.brain.symptom_severity_scale = symptom_severity_scale

        for _ in range(TICKS_PER_FRAME):
            stn_lfp = self.main_brain.generate_stn_lfp_sample(self.prior_dbs_amplitude_ma)
            self.main_extractor.ingest_stn_lfp_sample(stn_lfp)
            measured_lb = self.main_extractor.compute_pathological_beta_power()

            dbs_amplitude_ma = self.main_controller.compute_dbs_amplitude_ma(
                control_mode, measured_lb, limits, dt_sec
            )
            lb_power_pct = _effective_lb_power_pct(measured_lb, dbs_amplitude_ma)

            self.sim_time_sec += dt_sec
            self.history["time_sec"].append(self.sim_time_sec)
            self.history["stn_lfp_uv"].append(stn_lfp)
            self.history["pathological_beta_power"].append(lb_power_pct)
            self.history["high_beta_power"].append(self.main_extractor.high_beta_power_pct)
            burst_ms = _display_burst_duration_ms(self.main_brain, self.main_extractor)
            self.history["low_beta_burst_duration_ms"].append(burst_ms)
            self.history["dbs_amplitude_ma"].append(dbs_amplitude_ma)
            self.history["beta_detection_threshold"].append(limits.lfp_threshold_pct)

            self.prior_dbs_amplitude_ma = dbs_amplitude_ma

            for label, arm in self.comparison_arms.items():
                self._advance_comparison_arm(
                    label,
                    arm,
                    dt_sec,
                    limits,
                    dopaminergic_state,
                    symptom_severity_scale,
                    intervention_time_sec,
                    control_mode,
                )
                comp_hist = self.comparison_history[label]
                comp_hist["time_sec"].append(self.sim_time_sec)
                comp_hist["cumulative_patient_symptom_burden"].append(arm.cumulative_patient_symptom_burden)
                comp_hist["cumulative_total_energy_delivered"].append(arm.cumulative_teed)

