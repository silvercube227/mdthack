"""Live-chart data pipeline.

The dashboard renders charts in a *persistent* browser iframe (see
``live_charts.py``) that polls a small JSON file on its own timer. This fully
decouples chart rendering from Streamlit reruns, so the charts update smoothly
in place and never re-mount / blink.

This module builds that JSON payload from the simulation history and writes it
atomically to Streamlit's static-serving directory.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from typing import List, Sequence, Tuple

from backend.clinical_parameters import LB_POWER_OFF_PCT, LB_POWER_THERAPEUTIC_PCT, MAX_STIM_MA

SCROLL_WINDOW_SEC = 15.0
MAX_DISPLAY_POINTS = 450

_REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = _REPO_ROOT / "static"
LIVE_DATA_FILENAME = "dbs_live.json"
LIVE_DATA_URL = "app/static/dbs_live.json"

_WRITE_LOCK = threading.Lock()

_COMPARISON_ARMS = ("No DBS", "Fixed DBS", "Closed-Loop DBS")


def decimate_scroll_window(
    time_sec: Sequence[float],
    *series: Sequence[float],
    window_sec: float = SCROLL_WINDOW_SEC,
    max_points: int = MAX_DISPLAY_POINTS,
) -> Tuple[List[float], ...]:
    """Return the trailing time window, decimated for smooth live rendering."""
    if not time_sec:
        return ((),) + ((),) * len(series)

    t = list(time_sec)
    t_max = t[-1]
    t_min = max(0.0, t_max - window_sec)
    start = 0
    for i, tv in enumerate(t):
        if tv >= t_min:
            start = i
            break

    t_win = t[start:]
    arrs = [list(series[i])[start:] for i in range(len(series))]
    n = len(t_win)
    if n > max_points:
        step = max(n // max_points, 1)
        idx = list(range(0, n, step))
        t_win = [t_win[i] for i in idx]
        arrs = [[arr[i] for i in idx] for arr in arrs]

    return (t_win, *arrs)


def _round(values: Sequence[float], ndigits: int = 3) -> List[float]:
    return [round(float(v), ndigits) for v in values]


def build_payload(history: dict, comparison_history: dict, intervention_time_sec) -> dict:
    """Assemble the decimated live payload consumed by the chart iframe.

    All series that share an x-axis are truncated to a common length so the
    front-end ``uPlot.setData`` never receives ragged arrays (which would throw
    and briefly blank a chart).
    """
    t, stn, lb, hb, thr, burst, dbs = decimate_scroll_window(
        history["time_sec"],
        history["stn_lfp_uv"],
        history["pathological_beta_power"],
        history["high_beta_power"],
        history["beta_detection_threshold"],
        history["low_beta_burst_duration_ms"],
        history["dbs_amplitude_ma"],
    )
    n_main = min(len(t), len(stn), len(lb), len(hb), len(thr), len(burst), len(dbs))
    t, stn, lb, hb, thr, burst, dbs = (
        t[:n_main], stn[:n_main], lb[:n_main], hb[:n_main], thr[:n_main], burst[:n_main], dbs[:n_main],
    )

    arm_t: dict[str, list] = {}
    symptom: dict[str, List[float]] = {}
    energy: dict[str, List[float]] = {}
    for arm in _COMPARISON_ARMS:
        hist = comparison_history[arm]
        at, sy, en = decimate_scroll_window(
            hist["time_sec"],
            hist["cumulative_patient_symptom_burden"],
            hist["cumulative_total_energy_delivered"],
        )
        arm_t[arm] = list(at)
        symptom[arm] = list(sy)
        energy[arm] = list(en)

    n_comp = min(
        [len(arm_t[a]) for a in _COMPARISON_ARMS]
        + [len(symptom[a]) for a in _COMPARISON_ARMS]
        + [len(energy[a]) for a in _COMPARISON_ARMS]
    )
    comp_t = arm_t[_COMPARISON_ARMS[0]][:n_comp]
    for arm in _COMPARISON_ARMS:
        symptom[arm] = _round(symptom[arm][:n_comp])
        energy[arm] = _round(energy[arm][:n_comp])

    return {
        "t": _round(t),
        "stn": _round(stn),
        "lb": _round(lb),
        "hb": _round(hb),
        "thr": _round(thr),
        "burst": _round(burst, 1),
        "dbs": _round(dbs),
        "comp": {
            "t": _round(comp_t),
            "symptom": symptom,
            "energy": energy,
        },
        "intervention": None if intervention_time_sec is None else round(float(intervention_time_sec), 3),
        "window": SCROLL_WINDOW_SEC,
        "refs": {
            "offLb": LB_POWER_OFF_PCT,
            "therLb": LB_POWER_THERAPEUTIC_PCT,
            "burstOff": 579.0,
            "burstOn": 359.0,
            "maxMa": MAX_STIM_MA,
        },
    }


def write_live_payload(history: dict, comparison_history: dict, intervention_time_sec) -> None:
    """Atomically write the live payload to the static-serving directory."""
    payload = build_payload(history, comparison_history, intervention_time_sec)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    target = STATIC_DIR / LIVE_DATA_FILENAME
    body = json.dumps(payload)
    with _WRITE_LOCK:
        tmp = STATIC_DIR / f".{LIVE_DATA_FILENAME}.{uuid.uuid4().hex}.tmp"
        try:
            tmp.write_text(body, encoding="utf-8")
            os.replace(tmp, target)
        finally:
            if tmp.exists():
                tmp.unlink()
