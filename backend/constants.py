"""Shared simulation constants and control-mode definitions."""

from __future__ import annotations

from enum import Enum

import numpy as np

from backend.clinical_parameters import (
    ADAPT_PD_SENSE_HIGH_HZ,
    ADAPT_PD_SENSE_LOW_HZ,
    BETA_TOTAL_HIGH_HZ,
    BETA_TOTAL_LOW_HZ,
    DETECTION_WINDOW_MS,
    FIXED_CDBS_MA,
    HIGH_BETA_HIGH_HZ,
    HIGH_BETA_LOW_HZ,
    LOW_BETA_HIGH_HZ,
    LOW_BETA_LOW_HZ,
    LOWER_STIM_MA,
    MAX_HISTORY_SECONDS,
    MAX_STIM_MA,
    SAMPLE_RATE_HZ,
    TICKS_PER_FRAME,
    UPPER_STIM_MA,
)

# Backward-compatible aliases used across modules
BETA_BAND_LOW_HZ = BETA_TOTAL_LOW_HZ
BETA_BAND_HIGH_HZ = BETA_TOTAL_HIGH_HZ
BIOMARKER_WINDOW_MS = DETECTION_WINDOW_MS


class DBSControlMode(str, Enum):
    NONE = "None (Open-Loop Baseline)"
    FIXED = "Fixed DBS (cDBS)"
    ADAPTIVE_SINGLE_THRESHOLD = "Adaptive DBS — Single Threshold (ADAPT-PD)"
    ADAPTIVE_DUAL_THRESHOLD = "Adaptive DBS — Dual Threshold (ADAPT-PD)"


def trapz(y: np.ndarray, x: np.ndarray) -> float:
    """NumPy 1.x / 2.x compatible trapezoidal integration."""
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(y, x))
    if hasattr(np, "trapz"):
        return float(np.trapz(y, x))
    return float(np.sum((y[1:] + y[:-1]) / 2.0 * np.diff(x)))
