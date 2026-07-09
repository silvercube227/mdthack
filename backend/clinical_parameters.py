"""
Literature-calibrated parameters for STN closed-loop DBS simulation.

Primary sources:
- Neumann et al., npj Parkinson's Disease 2022 (beta suppression vs stimulation amplitude)
- Tinkhauser et al., Brain 2017 (beta burst dynamics OFF/ON levodopa)
- Anderson et al., npj Parkinson's Disease 2023 (106-patient LB burst durations)
- Stanslaski et al., npj Parkinson's Disease 2024 (ADAPT-PD trial methodology)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

# Percept BrainSense sampling (Neumann et al. 2024)
SAMPLE_RATE_HZ = 250

# Frequency bands (npj 2022; ADAPT-PD)
BETA_TOTAL_LOW_HZ = 13.0
BETA_TOTAL_HIGH_HZ = 35.0
LOW_BETA_LOW_HZ = 13.0
LOW_BETA_HIGH_HZ = 20.0
HIGH_BETA_LOW_HZ = 20.0
HIGH_BETA_HIGH_HZ = 35.0
ADAPT_PD_SENSE_LOW_HZ = 8.0
ADAPT_PD_SENSE_HIGH_HZ = 30.0
TOTAL_POWER_LOW_HZ = 3.0
TOTAL_POWER_HIGH_HZ = 47.0

# Individual peak frequencies OFF medication (npj 2022; J Neurosurg 2022)
LOW_BETA_PEAK_HZ = 15.5
HIGH_BETA_PEAK_HZ = 27.0
MEAN_PEAK_FREQ_OFF_HZ = 16.0

# Beta burst detection (Tinkhauser Brain 2017)
BURST_THRESHOLD_PERCENTILE = 75
BURST_MIN_DURATION_MS = 100

# Mean LB burst duration OFF vs ON levodopa (Anderson npj 2023, n=106)
BURST_DURATION_OFF_MS = 579.0
BURST_DURATION_ON_MS = 359.0

# Low-beta power as % total spectral power (Neumann npj 2022)
LB_POWER_OFF_PCT = 8.43
LB_POWER_THERAPEUTIC_PCT = 2.11
LB_POWER_OFF_STD_PCT = 3.14

# Stimulation amplitudes (ADAPT-PD; Neumann npj 2022; Eur J Neurol Percept study)
CLINICAL_EFFECT_MA = 1.5
FIXED_CDBS_MA = 2.5
LOWER_STIM_MA = 1.0
UPPER_STIM_MA = 3.0
MAX_STIM_MA = 3.5

# ADAPT-PD controller timing
ST_RAMP_MS = 250
DT_RAMP_UP_SEC = 150.0  # 2.5 min
DT_RAMP_DOWN_SEC = 300.0  # 5 min
DETECTION_WINDOW_MS = 500

# Simulation
MAX_HISTORY_SECONDS = 30
TICKS_PER_FRAME = 48
BASELINE_CALIBRATION_SEC = 5.0

# DBS pulse train (typical Percept programming: 130 Hz, 60 µs)
PULSE_WIDTH_US = 60.0
STIM_FREQUENCY_HZ = 130.0
STIM_FREQUENCY_MIN_HZ = 60.0
STIM_FREQUENCY_MAX_HZ = 185.0


class DopaminergicState(str, Enum):
    OFF = "OFF (Withdrawn)"
    ON = "ON (Levodopa)"


# Stepwise beta suppression vs stimulation (Neumann npj 2022, Table/Fig 1b)
DOSE_RESPONSE_STIM_MA = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 2.5])
DOSE_RESPONSE_BETA_PCT = np.array([4.31, 4.09, 2.27, 1.53, 1.17, 1.12])


def low_beta_power_pct_from_stim_ma(stim_amplitude_ma: float) -> float:
    """
    Map DBS amplitude to expected LB beta power (% total) using literature dose-response.
    Log-linear interpolation between calibrated stepwise points.
    """
    stim = float(np.clip(stim_amplitude_ma, 0.0, MAX_STIM_MA))
    log_stim = np.log1p(stim)
    log_table = np.log1p(DOSE_RESPONSE_STIM_MA)
    log_beta = np.interp(log_stim, log_table, np.log(DOSE_RESPONSE_BETA_PCT))
    return float(np.exp(log_beta))


def beta_amplitude_scale_from_stim_ma(stim_amplitude_ma: float) -> float:
    """
    Map DBS amplitude to beta burst amplitude scale (0–1 relative to OFF baseline).

    At 0 mA → full pathological amplitude (1.0). At therapeutic dose → ~sqrt(2.11/8.43).
    """
    if stim_amplitude_ma <= 0.0:
        return 1.0
    target_pct = low_beta_power_pct_from_stim_ma(stim_amplitude_ma)
    min_scale = 0.18
    return float(np.clip(np.sqrt(target_pct / LB_POWER_OFF_PCT), min_scale, 1.0))


@dataclass(frozen=True)
class TherapyParameterDefaults:
    lower_stim_ma: float = LOWER_STIM_MA
    upper_stim_ma: float = UPPER_STIM_MA
    lfp_threshold_pct: float = 5.5
    lfp_upper_threshold_pct: float = 6.5
    lfp_lower_threshold_pct: float = 3.0
