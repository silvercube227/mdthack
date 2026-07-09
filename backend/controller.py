"""Module 3: ADAPT-PD Single- and Dual-Threshold adaptive DBS controllers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.clinical_parameters import (
    DT_RAMP_DOWN_SEC,
    DT_RAMP_UP_SEC,
    FIXED_CDBS_MA,
    ST_RAMP_MS,
)
from backend.constants import DBSControlMode, MAX_STIM_MA


@dataclass
class ControllerLimits:
    lower_stim_ma: float = 1.0
    upper_stim_ma: float = 3.0
    lfp_threshold_pct: float = 4.0
    lfp_upper_threshold_pct: float = 6.0
    lfp_lower_threshold_pct: float = 2.5


class DBSControllerLayer:
    """ADAPT-PD validated neuromodulation control policies."""

    def __init__(self) -> None:
        self.current_amplitude_ma: float = 0.0
        self._st_target_ma: float = 0.0
        self.reset()

    def reset(self) -> None:
        self.current_amplitude_ma = 0.0
        self._st_target_ma = 0.0

    def _ramp_toward(self, target_ma: float, dt_sec: float, ramp_sec: float) -> float:
        if ramp_sec <= 0:
            return target_ma
        max_step = (self._limits_span(target_ma) / ramp_sec) * dt_sec
        delta = target_ma - self.current_amplitude_ma
        if abs(delta) <= max_step:
            return target_ma
        return self.current_amplitude_ma + np.sign(delta) * max_step

    @staticmethod
    def _limits_span(target_ma: float) -> float:
        return abs(target_ma)

    def compute_dbs_amplitude_ma(
        self,
        control_mode: DBSControlMode,
        pathological_beta_power_pct: float,
        limits: ControllerLimits,
        dt_sec: float,
    ) -> float:
        if control_mode == DBSControlMode.NONE:
            self.current_amplitude_ma = 0.0
            return 0.0

        if control_mode == DBSControlMode.FIXED:
            self.current_amplitude_ma = FIXED_CDBS_MA
            return FIXED_CDBS_MA

        lower = float(np.clip(limits.lower_stim_ma, 0.5, MAX_STIM_MA))
        upper = float(np.clip(limits.upper_stim_ma, lower, MAX_STIM_MA))

        if control_mode == DBSControlMode.ADAPTIVE_SINGLE_THRESHOLD:
            self._st_target_ma = upper if pathological_beta_power_pct > limits.lfp_threshold_pct else lower
            ramp_sec = ST_RAMP_MS / 1000.0
            self.current_amplitude_ma = float(
                np.clip(self._ramp_toward(self._st_target_ma, dt_sec, ramp_sec), lower, upper)
            )
            return self.current_amplitude_ma

        # Dual-Threshold (ADAPT-PD): slow incremental adjustment
        if pathological_beta_power_pct > limits.lfp_upper_threshold_pct:
            target = upper
            ramp_sec = DT_RAMP_UP_SEC
        elif pathological_beta_power_pct < limits.lfp_lower_threshold_pct:
            target = lower
            ramp_sec = DT_RAMP_DOWN_SEC
        else:
            target = self.current_amplitude_ma
            ramp_sec = 1e9

        self.current_amplitude_ma = float(
            np.clip(self._ramp_toward(target, dt_sec, ramp_sec), lower, upper)
        )
        return self.current_amplitude_ma


def compute_teed_increment(amplitude_ma: float, dt_sec: float) -> float:
    """Simplified TEED proxy: amplitude squared × time (µJ relative scale)."""
    return float(amplitude_ma**2 * dt_sec)
