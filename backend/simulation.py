"""Module 4: Virtual DBS feedback loop orchestration and comparison simulations."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict

import numpy as np

from backend.clinical_parameters import DopaminergicState
from backend.constants import DBSControlMode, MAX_HISTORY_SECONDS, SAMPLE_RATE_HZ, TICKS_PER_FRAME
from backend.controller import ControllerLimits, DBSControllerLayer, compute_teed_increment
from backend.signal_cleaning import PathologicalBetaExtractor
from backend.signal_generator import SimulatedSTNBrain


@dataclass
class ComparisonArmState:
    brain: SimulatedSTNBrain
    extractor: PathologicalBetaExtractor
    controller: DBSControllerLayer
    control_mode: DBSControlMode
    prior_dbs_amplitude_ma: float = 0.0
    cumulative_patient_symptom_burden: float = 0.0
    cumulative_teed: float = 0.0


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

    def _advance_comparison_arm(
        self,
        arm: ComparisonArmState,
        dt_sec: float,
        limits: ControllerLimits,
        dopaminergic_state: DopaminergicState,
        symptom_severity_scale: float,
    ) -> None:
        arm.brain.dopaminergic_state = dopaminergic_state
        arm.brain.symptom_severity_scale = symptom_severity_scale

        stn_lfp = arm.brain.generate_stn_lfp_sample(arm.prior_dbs_amplitude_ma)
        arm.extractor.ingest_stn_lfp_sample(stn_lfp)
        lb_power_pct = arm.extractor.compute_pathological_beta_power()

        dbs_amplitude = arm.controller.compute_dbs_amplitude_ma(
            arm.control_mode, lb_power_pct, limits, dt_sec
        )

        if arm.brain.burst_active:
            burst_ms = 1000.0 * arm.brain.burst_samples_remaining / arm.brain.sample_rate_hz
        else:
            burst_ms = 0.0
        # Symptom proxy: burst duration weighted by relative LB power (Anderson/Tinkhauser)
        arm.cumulative_patient_symptom_burden += (burst_ms / 579.0) * (lb_power_pct / 8.43) * dt_sec
        arm.cumulative_teed += compute_teed_increment(dbs_amplitude, dt_sec)
        arm.prior_dbs_amplitude_ma = dbs_amplitude

    def advance(
        self,
        control_mode: DBSControlMode,
        limits: ControllerLimits,
        dopaminergic_state: DopaminergicState,
        symptom_severity_scale: float,
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
            lb_power_pct = self.main_extractor.compute_pathological_beta_power()

            dbs_amplitude_ma = self.main_controller.compute_dbs_amplitude_ma(
                control_mode, lb_power_pct, limits, dt_sec
            )

            self.sim_time_sec += dt_sec
            self.history["time_sec"].append(self.sim_time_sec)
            self.history["stn_lfp_uv"].append(stn_lfp)
            self.history["pathological_beta_power"].append(lb_power_pct)
            self.history["high_beta_power"].append(self.main_extractor.high_beta_power_pct)
            self.history["low_beta_burst_duration_ms"].append(
                1000.0 * self.main_brain.burst_samples_remaining / self.main_brain.sample_rate_hz
                if self.main_brain.burst_active
                else 0.0
            )
            self.history["dbs_amplitude_ma"].append(dbs_amplitude_ma)
            self.history["beta_detection_threshold"].append(limits.lfp_threshold_pct)

            self.prior_dbs_amplitude_ma = dbs_amplitude_ma

            for label, arm in self.comparison_arms.items():
                self._advance_comparison_arm(
                    arm, dt_sec, limits, dopaminergic_state, symptom_severity_scale
                )
                comp_hist = self.comparison_history[label]
                comp_hist["time_sec"].append(self.sim_time_sec)
                comp_hist["cumulative_patient_symptom_burden"].append(arm.cumulative_patient_symptom_burden)
                comp_hist["cumulative_total_energy_delivered"].append(arm.cumulative_teed)
