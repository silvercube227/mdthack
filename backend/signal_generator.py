"""Module 1: Simulated Brain — Subthalamic Nucleus LFP generation."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from backend.constants import BETA_CENTER_HZ, SAMPLE_RATE_HZ


@dataclass
class SimulatedSTNBrain:
    """Generates pathological STN LFP with waxing/waning Beta oscillations."""

    sample_rate_hz: float = SAMPLE_RATE_HZ
    base_symptom_severity: float = 0.7
    neuromodulatory_gain: float = 0.85
    beta_center_hz: float = BETA_CENTER_HZ
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng(42))

    sample_index: int = 0
    beta_phase_rad: float = 0.0
    pathological_beta_amplitude: float = 0.7
    _pink_state: np.ndarray = field(default_factory=lambda: np.zeros(7))

    def symptom_flare_envelope(self, time_sec: float) -> float:
        """Slow baseline drift simulating shifting Parkinsonian disease states."""
        slow = 0.45 + 0.30 * np.sin(2 * np.pi * 0.04 * time_sec)
        medium = 0.12 * np.sin(2 * np.pi * 0.11 * time_sec + 0.6)
        fast = 0.08 * np.sin(2 * np.pi * 0.23 * time_sec + 1.2)
        return float(np.clip(slow + medium + fast, 0.15, 1.0))

    def _pink_noise_sample(self) -> float:
        """Approximate 1/f ambient neural noise (microvolts)."""
        white = self.rng.standard_normal()
        self._pink_state = np.roll(self._pink_state, 1)
        self._pink_state[0] = white
        pink = np.sum(self._pink_state * np.array([1.0, 0.8, 0.6, 0.4, 0.25, 0.15, 0.08]))
        return pink * 4.5

    def generate_stn_lfp_sample(self, prior_dbs_amplitude_ma: float) -> float:
        """
        Produce one STN LFP sample (µV).
        Closed-loop feedback: prior stimulation suppresses pathological Beta amplitude.
        """
        time_sec = self.sample_index / self.sample_rate_hz
        flare = self.symptom_flare_envelope(time_sec)
        base_pathological_beta = self.base_symptom_severity * flare

        # Module 4: Virtual DBS neuromodulatory feedback loop (t -> t+1)
        self.pathological_beta_amplitude = float(
            np.clip(
                base_pathological_beta - self.neuromodulatory_gain * prior_dbs_amplitude_ma,
                0.04,
                1.0,
            )
        )

        self.beta_phase_rad += 2 * np.pi * self.beta_center_hz / self.sample_rate_hz
        beta_oscillation = self.pathological_beta_amplitude * np.sin(self.beta_phase_rad)
        ambient_noise = self._pink_noise_sample() + self.rng.standard_normal() * 1.2

        stn_lfp_uv = beta_oscillation * 55.0 + ambient_noise
        self.sample_index += 1
        return stn_lfp_uv
