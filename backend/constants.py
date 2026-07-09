"""Shared simulation constants and control-mode definitions."""

from __future__ import annotations

from enum import Enum

import numpy as np

SAMPLE_RATE_HZ = 512
BETA_CENTER_HZ = 20.0
BETA_BAND_LOW_HZ = 13.0
BETA_BAND_HIGH_HZ = 30.0
BIOMARKER_WINDOW_MS = 500
MAX_HISTORY_SECONDS = 30
MAX_STIM_MA = 5.0
TICKS_PER_FRAME = 64


class DBSControlMode(str, Enum):
    NONE = "None (Open-Loop Baseline)"
    FIXED = "Fixed DBS"
    PROPORTIONAL = "Proportional (Adaptive) DBS"


def trapz(y: np.ndarray, x: np.ndarray) -> float:
    """NumPy 1.x / 2.x compatible trapezoidal integration."""
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(y, x))
    if hasattr(np, "trapz"):
        return float(np.trapz(y, x))
    return float(np.sum((y[1:] + y[:-1]) / 2.0 * np.diff(x)))
