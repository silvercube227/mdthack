"""Module 4: Virtual DBS feedback loop orchestration and comparison simulations."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict

import numpy as np

from backend.constants import DBSControlMode, MAX_HISTORY_SECONDS, SAMPLE_RATE_HZ, TICKS_PER_FRAME
from backend.pid import DBSControllerLayer
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
    cumulative_total_energy_delivered: float = 0.0


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
            control_mode=DBSControlMode.PROPORTIONAL,
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
        controller_gain_kp: float,
        threshold: float,
    ) -> None:
        stn_lfp = arm.brain.generate_stn_lfp_sample(arm.prior_dbs_amplitude_ma)
        arm.extractor.ingest_stn_lfp_sample(stn_lfp)
        beta_power = arm.extractor.compute_pathological_beta_power()

        dbs_amplitude = arm.controller.compute_dbs_amplitude_ma(
            arm.control_mode, beta_power, controller_gain_kp, threshold, dt_sec
        )

        arm.cumulative_patient_symptom_burden += beta_power * dt_sec
        arm.cumulative_total_energy_delivered += dbs_amplitude * dt_sec
        arm.prior_dbs_amplitude_ma = dbs_amplitude

    def advance(
        self,
        control_mode: DBSControlMode,
        beta_detection_threshold: float,
        controller_gain_kp: float,
        base_symptom_severity: float,
        neuromodulatory_gain: float,
    ) -> None:
        """Advance primary + shadow simulations by TICKS_PER_FRAME samples."""
        dt_sec = 1.0 / SAMPLE_RATE_HZ

        self.main_brain.base_symptom_severity = base_symptom_severity
        self.main_brain.neuromodulatory_gain = neuromodulatory_gain

        for arm in self.comparison_arms.values():
            arm.brain.base_symptom_severity = base_symptom_severity
            arm.brain.neuromodulatory_gain = neuromodulatory_gain

        for _ in range(TICKS_PER_FRAME):
            stn_lfp = self.main_brain.generate_stn_lfp_sample(self.prior_dbs_amplitude_ma)
            self.main_extractor.ingest_stn_lfp_sample(stn_lfp)
            pathological_beta_power = self.main_extractor.compute_pathological_beta_power()

            dbs_amplitude_ma = self.main_controller.compute_dbs_amplitude_ma(
                control_mode,
                pathological_beta_power,
                controller_gain_kp,
                beta_detection_threshold,
                dt_sec,
            )

            self.sim_time_sec += dt_sec
            self.history["time_sec"].append(self.sim_time_sec)
            self.history["stn_lfp_uv"].append(stn_lfp)
            self.history["pathological_beta_power"].append(pathological_beta_power)
            self.history["dbs_amplitude_ma"].append(dbs_amplitude_ma)
            self.history["beta_detection_threshold"].append(beta_detection_threshold)

            self.prior_dbs_amplitude_ma = dbs_amplitude_ma

            for label, arm in self.comparison_arms.items():
                self._advance_comparison_arm(arm, dt_sec, controller_gain_kp, beta_detection_threshold)
                comp_hist = self.comparison_history[label]
                comp_hist["time_sec"].append(self.sim_time_sec)
                comp_hist["cumulative_patient_symptom_burden"].append(arm.cumulative_patient_symptom_burden)
                comp_hist["cumulative_total_energy_delivered"].append(arm.cumulative_total_energy_delivered)
