"""Module 1: Simulated Brain — literature-calibrated STN LFP with beta bursts."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from backend.clinical_parameters import (
    BURST_DURATION_OFF_MS,
    BURST_DURATION_ON_MS,
    DopaminergicState,
    HIGH_BETA_PEAK_HZ,
    LB_POWER_OFF_PCT,
    LB_POWER_THERAPEUTIC_PCT,
    LOW_BETA_PEAK_HZ,
    SAMPLE_RATE_HZ,
    low_beta_power_pct_from_stim_ma,
)


@dataclass
class SimulatedSTNBrain:
    """
    Generates pathological STN LFP with dual low/high beta bursts embedded in
    broad-band neural noise (theta/alpha/gamma) so LB power ≈ 8.4% total OFF.
    """

    sample_rate_hz: float = SAMPLE_RATE_HZ
    low_beta_peak_hz: float = LOW_BETA_PEAK_HZ
    high_beta_peak_hz: float = HIGH_BETA_PEAK_HZ
    dopaminergic_state: DopaminergicState = DopaminergicState.OFF
    symptom_severity_scale: float = 1.0
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng(42))

    sample_index: int = 0
    low_beta_phase_rad: float = 0.0
    high_beta_phase_rad: float = 0.0
    theta_phase_rad: float = 0.0
    alpha_phase_rad: float = 0.0
    gamma_phase_rad: float = 0.0
    burst_active: bool = False
    burst_samples_remaining: int = 0
    inter_burst_samples_remaining: int = 0
    lb_power_scale: float = 1.0
    _pink_state: np.ndarray = field(default_factory=lambda: np.zeros(7))

    def _mean_burst_duration_ms(self) -> float:
        if self.dopaminergic_state == DopaminergicState.ON:
            return BURST_DURATION_ON_MS
        return BURST_DURATION_OFF_MS * self.symptom_severity_scale

    def _sample_burst_duration_samples(self) -> int:
        mean_ms = max(self._mean_burst_duration_ms(), 120.0)
        sigma = 0.55
        mu = np.log(mean_ms) - 0.5 * sigma**2
        duration_ms = float(np.clip(self.rng.lognormal(mu, sigma), 100.0, 2500.0))
        return int(duration_ms * self.sample_rate_hz / 1000.0)

    def _sample_inter_burst_samples(self) -> int:
        mean_gap_ms = 600.0 if self.dopaminergic_state == DopaminergicState.ON else 1200.0
        gap_ms = float(self.rng.exponential(mean_gap_ms))
        return max(int(gap_ms * self.sample_rate_hz / 1000.0), 8)

    def _advance_burst_state(self) -> float:
        if self.burst_samples_remaining <= 0 and self.inter_burst_samples_remaining <= 0:
            self.burst_active = True
            self.burst_samples_remaining = self._sample_burst_duration_samples()

        if self.burst_active:
            self.burst_samples_remaining -= 1
            if self.burst_samples_remaining <= 0:
                self.burst_active = False
                self.inter_burst_samples_remaining = self._sample_inter_burst_samples()
            return 1.0

        self.inter_burst_samples_remaining -= 1
        return 0.05

    def _pink_noise_sample(self) -> float:
        white = self.rng.standard_normal()
        self._pink_state = np.roll(self._pink_state, 1)
        self._pink_state[0] = white
        pink = np.sum(self._pink_state * np.array([1.0, 0.8, 0.6, 0.4, 0.25, 0.15, 0.08]))
        return pink * 5.5

    def _update_suppression_from_dbs(self, prior_dbs_amplitude_ma: float) -> None:
        target_pct = low_beta_power_pct_from_stim_ma(prior_dbs_amplitude_ma)
        self.lb_power_scale = float(
            np.clip(target_pct / LB_POWER_OFF_PCT, LB_POWER_THERAPEUTIC_PCT / LB_POWER_OFF_PCT, 1.0)
        )

    def generate_stn_lfp_sample(self, prior_dbs_amplitude_ma: float) -> float:
        """Produce one STN LFP sample (µV) with burst-modulated LB/HB components."""
        self._update_suppression_from_dbs(prior_dbs_amplitude_ma)

        burst_env = self._advance_burst_state()
        med_factor = 0.55 if self.dopaminergic_state == DopaminergicState.ON else 1.0
        beta_gain = burst_env * (self.lb_power_scale ** 2) * med_factor * self.symptom_severity_scale

        dt = 1.0 / self.sample_rate_hz
        self.low_beta_phase_rad += 2 * np.pi * self.low_beta_peak_hz * dt
        self.high_beta_phase_rad += 2 * np.pi * self.high_beta_peak_hz * dt
        self.theta_phase_rad += 2 * np.pi * 6.0 * dt
        self.alpha_phase_rad += 2 * np.pi * 10.0 * dt
        self.gamma_phase_rad += 2 * np.pi * 45.0 * dt

        # Pathological beta bursts (minority of total power — Neumann npj 2022)
        low_beta = beta_gain * 2.2 * np.sin(self.low_beta_phase_rad)
        high_beta = beta_gain * 0.55 * np.sin(self.high_beta_phase_rad)

        # Non-beta physiological content dominates STN LFP spectrum
        theta = 3.8 * np.sin(self.theta_phase_rad)
        alpha = 3.2 * np.sin(self.alpha_phase_rad)
        gamma = 1.4 * np.sin(self.gamma_phase_rad)
        ambient = self._pink_noise_sample() + self.rng.standard_normal() * 2.2

        stn_lfp_uv = low_beta + high_beta + theta + alpha + gamma + ambient
        self.sample_index += 1
        return stn_lfp_uv

    @property
    def in_beta_burst(self) -> bool:
        return self.burst_active and self.burst_samples_remaining > 0
