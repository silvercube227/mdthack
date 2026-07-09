"""Module 2: Biomarker Extraction — Pathological Beta Detection."""

from __future__ import annotations

from collections import deque
from typing import Deque

import numpy as np
from scipy.signal import butter, sosfilt, welch

from backend.constants import (
    BETA_BAND_HIGH_HZ,
    BETA_BAND_LOW_HZ,
    BIOMARKER_WINDOW_MS,
    SAMPLE_RATE_HZ,
    trapz,
)


class PathologicalBetaExtractor:
    """Sliding-window biomarker extraction targeting the Beta band (13–30 Hz)."""

    def __init__(self, sample_rate_hz: float = SAMPLE_RATE_HZ, window_ms: float = BIOMARKER_WINDOW_MS):
        self.sample_rate_hz = sample_rate_hz
        window_samples = int(sample_rate_hz * window_ms / 1000.0)
        self._stn_lfp_buffer: Deque[float] = deque(maxlen=max(window_samples, 64))
        self._power_ema: float = 0.35
        self._power_scale: float = 1.0

    def ingest_stn_lfp_sample(self, stn_lfp_uv: float) -> None:
        self._stn_lfp_buffer.append(stn_lfp_uv)

    def compute_pathological_beta_power(self) -> float:
        """
        Returns normalized Pathological Beta Band Power in [0, 1].
        Uses bandpass filtering + RMS with Welch PSD cross-check when buffer is full.
        """
        if len(self._stn_lfp_buffer) < 32:
            return self._power_ema

        segment = np.asarray(self._stn_lfp_buffer, dtype=float)
        segment = segment - np.mean(segment)

        sos = butter(
            4,
            [BETA_BAND_LOW_HZ, BETA_BAND_HIGH_HZ],
            btype="band",
            fs=self.sample_rate_hz,
            output="sos",
        )
        beta_band_signal = sosfilt(sos, segment)
        band_rms = float(np.sqrt(np.mean(beta_band_signal**2)))

        if len(segment) >= 128:
            freqs, psd = welch(segment, fs=self.sample_rate_hz, nperseg=min(256, len(segment)))
            beta_mask = (freqs >= BETA_BAND_LOW_HZ) & (freqs <= BETA_BAND_HIGH_HZ)
            beta_psd_power = trapz(psd[beta_mask], freqs[beta_mask])
            raw_power = 0.6 * band_rms + 0.4 * np.sqrt(beta_psd_power) * 10.0
        else:
            raw_power = band_rms

        self._power_scale = max(self._power_scale * 0.999 + raw_power * 0.001, 1e-6)
        normalized = float(np.clip(raw_power / (self._power_scale * 1.8), 0.0, 1.0))
        self._power_ema = 0.85 * self._power_ema + 0.15 * normalized
        return self._power_ema
