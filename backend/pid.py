"""Module 3: Controller Layer — Fixed and Proportional neuromodulation policies."""

from __future__ import annotations

import numpy as np

from backend.constants import DBSControlMode, MAX_STIM_MA


class DBSControllerLayer:
    """Selectable neuromodulation control policies."""

    FIXED_DBS_MA = 3.2

    def compute_dbs_amplitude_ma(
        self,
        control_mode: DBSControlMode,
        pathological_beta_power: float,
        controller_gain_kp: float,
        beta_detection_threshold: float,
        dt_sec: float,
    ) -> float:
        if control_mode == DBSControlMode.NONE:
            return 0.0

        if control_mode == DBSControlMode.FIXED:
            return self.FIXED_DBS_MA

        return float(np.clip(controller_gain_kp * pathological_beta_power, 0.0, MAX_STIM_MA))
