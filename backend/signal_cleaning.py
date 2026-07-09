"""Module 2: Biomarker Extraction — validated Pathological Beta detection."""

from __future__ import annotations

from collections import deque
from typing import Deque, Optional

import numpy as np
from scipy.signal import butter, hilbert, sosfilt, welch

from backend.clinical_parameters import (
    BASELINE_CALIBRATION_SEC,
    BURST_MIN_DURATION_MS,
    BURST_THRESHOLD_PERCENTILE,
    LB_POWER_OFF_PCT,
    LOW_BETA_HIGH_HZ,
    LOW_BETA_LOW_HZ,
    SAMPLE_RATE_HZ,
    TOTAL_POWER_HIGH_HZ,
    TOTAL_POWER_LOW_HZ,
)
from backend.constants import BIOMARKER_WINDOW_MS, trapz


class PathologicalBetaExtractor:
    """
    Sliding-window biomarker extraction aligned with Percept / Tinkhauser methods.
    Primary output: low-beta power as % total spectral power (3–47 Hz).
    Secondary: beta burst duration via 75th-percentile Hilbert envelope.
    """

    def __init__(self, sample_rate_hz: float = SAMPLE_RATE_HZ, window_ms: float = BIOMARKER_WINDOW_MS):
        self.sample_rate_hz = sample_rate_hz
        window_samples = int(sample_rate_hz * window_ms / 1000.0)
        self._stn_lfp_buffer: Deque[float] = deque(maxlen=max(window_samples, 64))
        self._calibration_buffer: Deque[float] = deque(maxlen=int(BASELINE_CALIBRATION_SEC * sample_rate_hz))

        self._off_baseline_pct: Optional[float] = None
        self._calibration_factor: float = 1.0
        self._raw_calibration_values: list[float] = []
        self._last_lb_power_pct: float = LB_POWER_OFF_PCT
        self._last_hb_power_pct: float = 2.0
        self._last_burst_duration_ms: float = 0.0
        self._last_burst_time_pct: float = 0.0
        self._samples_since_compute: int = 999
        self._compute_every_n_samples: int = 8

    def ingest_stn_lfp_sample(self, stn_lfp_uv: float) -> None:
        self._stn_lfp_buffer.append(stn_lfp_uv)
        if self._off_baseline_pct is None:
            self._calibration_buffer.append(stn_lfp_uv)

    def _band_power_pct(self, segment: np.ndarray, band: tuple[float, float]) -> float:
        segment = segment - np.mean(segment)
        sos = butter(4, list(band), btype="band", fs=self.sample_rate_hz, output="sos")
        filtered = sosfilt(sos, segment)
        band_power = float(np.mean(filtered**2))

        sos_total = butter(4, [TOTAL_POWER_LOW_HZ, TOTAL_POWER_HIGH_HZ], btype="band", fs=self.sample_rate_hz, output="sos")
        total_filtered = sosfilt(sos_total, segment)
        total_power = float(np.mean(total_filtered**2))
        if total_power <= 1e-12:
            return 0.0
        return 100.0 * band_power / total_power

    def _welch_band_power_pct(self, segment: np.ndarray, band: tuple[float, float]) -> float:
        freqs, psd = welch(segment, fs=self.sample_rate_hz, nperseg=min(128, len(segment)))
        total_mask = (freqs >= TOTAL_POWER_LOW_HZ) & (freqs <= TOTAL_POWER_HIGH_HZ)
        band_mask = (freqs >= band[0]) & (freqs <= band[1])
        total = trapz(psd[total_mask], freqs[total_mask])
        band = trapz(psd[band_mask], freqs[band_mask])
        if total <= 1e-12:
            return 0.0
        return 100.0 * band / total

    def _detect_burst_metrics(self, segment: np.ndarray) -> tuple[float, float]:
        """75th-percentile envelope burst detection (Tinkhauser et al. 2017)."""
        sos = butter(4, [LOW_BETA_LOW_HZ, LOW_BETA_HIGH_HZ], btype="band", fs=self.sample_rate_hz, output="sos")
        beta_signal = sosfilt(sos, segment - np.mean(segment))
        envelope = np.abs(hilbert(beta_signal))
        if len(envelope) >= 5:
            kernel = np.ones(5) / 5.0
            envelope = np.convolve(envelope, kernel, mode="same")
        threshold = float(np.percentile(envelope, BURST_THRESHOLD_PERCENTILE))
        above = envelope >= threshold

        min_samples = max(int(BURST_MIN_DURATION_MS * self.sample_rate_hz / 1000.0), 1)
        burst_duration_ms = 0.0
        burst_time_pct = 0.0
        max_duration_ms = 0.0
        total_burst_samples = 0

        i = 0
        n = len(above)
        while i < n:
            if above[i]:
                start = i
                while i < n and above[i]:
                    i += 1
                length = i - start
                if length >= min_samples:
                    dur_ms = 1000.0 * length / self.sample_rate_hz
                    max_duration_ms = max(max_duration_ms, dur_ms)
                    total_burst_samples += length
            else:
                i += 1

        if total_burst_samples > 0:
            burst_duration_ms = max_duration_ms
            burst_time_pct = 100.0 * total_burst_samples / n

        return burst_duration_ms, burst_time_pct

    def _finalize_baseline(self, raw_lb_pct: float) -> None:
        if self._off_baseline_pct is not None:
            return
        self._raw_calibration_values.append(raw_lb_pct)
        if len(self._calibration_buffer) < int(BASELINE_CALIBRATION_SEC * self.sample_rate_hz * 0.8):
            return
        median_raw = float(np.median(self._raw_calibration_values[-80:]))
        if median_raw > 0.1:
            self._calibration_factor = LB_POWER_OFF_PCT / median_raw
        self._off_baseline_pct = LB_POWER_OFF_PCT

    def compute_pathological_beta_power(self) -> float:
        """Returns low-beta power as % total spectral power."""
        if len(self._stn_lfp_buffer) < 32:
            return self._last_lb_power_pct

        self._samples_since_compute += 1
        if self._samples_since_compute < self._compute_every_n_samples:
            return self._last_lb_power_pct

        self._samples_since_compute = 0
        segment = np.asarray(self._stn_lfp_buffer, dtype=float)
        raw_lb_pct = self._welch_band_power_pct(segment, (LOW_BETA_LOW_HZ, LOW_BETA_HIGH_HZ))
        self._finalize_baseline(raw_lb_pct)

        # Hold OFF reference until baseline calibration completes — raw Welch is
        # unscaled before _calibration_factor is set and would clip to ~25%.
        if self._off_baseline_pct is None:
            self._last_lb_power_pct = LB_POWER_OFF_PCT
            return LB_POWER_OFF_PCT

        lb_pct = float(np.clip(raw_lb_pct * self._calibration_factor, 0.0, 25.0))

        from backend.clinical_parameters import HIGH_BETA_HIGH_HZ, HIGH_BETA_LOW_HZ

        self._last_hb_power_pct = self._welch_band_power_pct(segment, (HIGH_BETA_LOW_HZ, HIGH_BETA_HIGH_HZ))
        self._last_hb_power_pct *= self._calibration_factor
        self._last_lb_power_pct = float(max(lb_pct, 0.0))
        self._last_burst_duration_ms, self._last_burst_time_pct = self._detect_burst_metrics(segment)
        return self._last_lb_power_pct

    @property
    def high_beta_power_pct(self) -> float:
        return self._last_hb_power_pct

    @property
    def low_beta_burst_duration_ms(self) -> float:
        return self._last_burst_duration_ms

    @property
    def burst_time_pct(self) -> float:
        return self._last_burst_time_pct

    @property
    def off_baseline_pct(self) -> float:
        return self._off_baseline_pct if self._off_baseline_pct is not None else LB_POWER_OFF_PCT

    def normalized_beta_power(self) -> float:
        """Beta power normalized to patient OFF baseline (Timeline-style)."""
        baseline = max(self.off_baseline_pct, 0.5)
        return float(np.clip(self._last_lb_power_pct / baseline, 0.0, 2.0))
