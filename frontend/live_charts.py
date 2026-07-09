"""Canvas-based live charts (lightweight-charts) — payload embedded inline each tick."""

from __future__ import annotations

import json
from typing import Any, Optional, Sequence

import streamlit.components.v1 as components

from frontend.plots import SCROLL_WINDOW_SEC, decimate_scroll_window

_CHART_HEIGHT = 1320


def _series_points(t: Sequence[float], y: Sequence[float]) -> list[dict[str, float]]:
    return [{"time": float(tv), "value": float(yv)} for tv, yv in zip(t, y) if yv is not None]


def build_live_chart_payload(
    history: dict,
    comparison_history: dict,
    intervention_time_sec: Optional[float] = None,
    reset: bool = False,
) -> dict[str, Any]:
    from frontend.debug_log import debug_log

    t, lfp = decimate_scroll_window(history["time_sec"], history["stn_lfp_uv"])
    _, lb, hb, thr = decimate_scroll_window(
        history["time_sec"],
        history["pathological_beta_power"],
        history["high_beta_power"],
        history["beta_detection_threshold"],
    )
    _, burst = decimate_scroll_window(history["time_sec"], history["low_beta_burst_duration_ms"])
    _, dbs = decimate_scroll_window(history["time_sec"], history["dbs_amplitude_ma"])

    comp: dict[str, dict[str, list]] = {}
    for label in ("No DBS", "Fixed DBS", "Closed-Loop DBS"):
        hist = comparison_history[label]
        ct, symptom, energy = decimate_scroll_window(
            hist["time_sec"],
            hist["cumulative_patient_symptom_burden"],
            hist["cumulative_total_energy_delivered"],
        )
        comp[label] = {
            "t": ct,
            "symptom": _series_points(ct, symptom),
            "energy": _series_points(ct, energy),
        }

    lfp_points = _series_points(t, lfp)
    # #region agent log
    debug_log(
        "live_charts.py:build_live_chart_payload",
        "chart_payload_built",
        {
            "n_lfp_points": len(lfp_points),
            "intervention_time_sec": intervention_time_sec,
            "reset": reset,
        },
        hypothesis_id="G",
        run_id="post-fix-v2",
    )
    # #endregion

    return {
        "reset": reset,
        "windowSec": SCROLL_WINDOW_SEC,
        "interventionTime": intervention_time_sec,
        "t": t,
        "lfp": lfp_points,
        "lb": _series_points(t, lb),
        "hb": _series_points(t, hb),
        "threshold": _series_points(t, thr),
        "burst": _series_points(t, burst),
        "dbs": _series_points(t, dbs),
        "comparison": comp,
        "refs": {"offLb": 8.43, "therapeuticLb": 2.11, "burstOff": 579, "burstOn": 359},
    }


_CHART_HTML = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0e1117; color: #9ba7b8; font-family: Inter, Segoe UI, sans-serif; }
  .panel { margin: 0 0 10px 0; border: 1px solid #2a3142; border-radius: 8px; overflow: hidden; background: #161b26; }
  .title { font-size: 12px; color: #c9d1d9; padding: 8px 12px 4px; }
  .chart { width: 100%; height: 180px; }
  .chart.tall { height: 200px; }
  .chart.short { height: 160px; }
</style>
</head>
<body>
<div id="p-lfp" class="panel"><div class="title">STN LFP — Raw Local Field Potential</div><div id="c-lfp" class="chart tall"></div></div>
<div id="p-beta" class="panel"><div class="title">Pathological Beta Band Power (% Total Spectral Power)</div><div id="c-beta" class="chart"></div></div>
<div id="p-burst" class="panel"><div class="title">Low-Beta Burst Duration</div><div id="c-burst" class="chart short"></div></div>
<div id="p-dbs" class="panel"><div class="title">DBS Amplitude (mA)</div><div id="c-dbs" class="chart short"></div></div>
<div id="p-eff" class="panel"><div class="title">Cumulative Symptom Burden — grey (No DBS) should stay on top</div><div id="c-eff" class="chart short"></div></div>
<div id="p-teed" class="panel"><div class="title">Total Energy Delivered (TEED proxy)</div><div id="c-teed" class="chart short"></div></div>
<script>
const PAYLOAD = __PAYLOAD__;

const theme = {
  layout: { background: { color: "#161b26" }, textColor: "#9ba7b8" },
  grid: { vertLines: { color: "#2a3142" }, horLines: { color: "#2a3142" } },
  timeScale: { timeVisible: true, secondsVisible: true, borderColor: "#3d4659" },
  rightPriceScale: { borderColor: "#3d4659" },
};

function makeChart(el, opts = {}) {
  const chart = LightweightCharts.createChart(el, {
    ...theme,
    width: el.clientWidth,
    height: el.clientHeight,
    ...opts,
  });
  const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth, height: el.clientHeight }));
  ro.observe(el);
  return chart;
}

function lineSeries(chart, color, opts = {}) {
  return chart.addLineSeries({
    color,
    lineWidth: 2,
    priceLineVisible: false,
    lastValueVisible: false,
    crosshairMarkerRadius: 3,
    ...opts,
  });
}

function interventionMarkers(tInt) {
  if (tInt == null) return [];
  return [{ time: tInt, position: "aboveBar", color: "#f0883e", shape: "arrowDown", text: "Intervention" }];
}

function scrollChart(chart, tArr, windowSec) {
  if (!tArr || !tArr.length) return;
  const tMax = tArr[tArr.length - 1];
  const tMin = Math.max(0, tMax - windowSec);
  chart.timeScale().setVisibleRange({ from: tMin, to: Math.max(tMax + 0.05, windowSec) });
}

function boot() {
  try {
    if (typeof LightweightCharts === "undefined") {
      throw new Error("lightweight-charts failed to load");
    }
    const refs = PAYLOAD.refs;
    const markers = interventionMarkers(PAYLOAD.interventionTime);

    const lfpChart = makeChart(document.getElementById("c-lfp"));
    const lfpSeries = lineSeries(lfpChart, "#58a6ff", { lineWidth: 1.5 });
    lfpSeries.setData(PAYLOAD.lfp || []);
    lfpSeries.setMarkers(markers);
    scrollChart(lfpChart, PAYLOAD.t, PAYLOAD.windowSec);

    const betaChart = makeChart(document.getElementById("c-beta"));
    const lb = lineSeries(betaChart, "#f78166");
    const hb = lineSeries(betaChart, "#d2a8ff", { lineWidth: 1.5 });
    const thr = lineSeries(betaChart, "#ffa657", { lineWidth: 1.5, lineStyle: 2 });
    lb.createPriceLine({ price: refs.offLb, color: "#8b949e", lineWidth: 1, lineStyle: 2, title: "OFF 8.4%" });
    lb.createPriceLine({ price: refs.therapeuticLb, color: "#3fb950", lineWidth: 1, lineStyle: 2, title: "Ther 2.1%" });
    lb.setData(PAYLOAD.lb || []);
    hb.setData(PAYLOAD.hb || []);
    thr.setData(PAYLOAD.threshold || []);
    scrollChart(betaChart, PAYLOAD.t, PAYLOAD.windowSec);

    const burstChart = makeChart(document.getElementById("c-burst"));
    const burstSeries = lineSeries(burstChart, "#ffa657");
    burstSeries.createPriceLine({ price: refs.burstOff, color: "#8b949e", lineWidth: 1, lineStyle: 2, title: "OFF 579ms" });
    burstSeries.createPriceLine({ price: refs.burstOn, color: "#3fb950", lineWidth: 1, lineStyle: 2, title: "ON 359ms" });
    burstSeries.setData(PAYLOAD.burst || []);
    burstSeries.setMarkers(markers);
    scrollChart(burstChart, PAYLOAD.t, PAYLOAD.windowSec);

    const dbsChart = makeChart(document.getElementById("c-dbs"));
    const dbsSeries = lineSeries(dbsChart, "#3fb950");
    dbsSeries.setData(PAYLOAD.dbs || []);
    dbsSeries.setMarkers(markers);
    scrollChart(dbsChart, PAYLOAD.t, PAYLOAD.windowSec);

    const effChart = makeChart(document.getElementById("c-eff"), { height: 160 });
    const comp = PAYLOAD.comparison || {};
    lineSeries(effChart, "#8b949e", { lineWidth: 2.5 }).setData(comp["No DBS"]?.symptom || []);
    lineSeries(effChart, "#d2a8ff", { lineWidth: 2.5 }).setData(comp["Fixed DBS"]?.symptom || []);
    lineSeries(effChart, "#3fb950", { lineWidth: 2.5 }).setData(comp["Closed-Loop DBS"]?.symptom || []);
    scrollChart(effChart, PAYLOAD.t, PAYLOAD.windowSec);

    const teedChart = makeChart(document.getElementById("c-teed"), { height: 160 });
    lineSeries(teedChart, "#8b949e", { lineWidth: 2.5 }).setData(comp["No DBS"]?.energy || []);
    lineSeries(teedChart, "#d2a8ff", { lineWidth: 2.5 }).setData(comp["Fixed DBS"]?.energy || []);
    lineSeries(teedChart, "#3fb950", { lineWidth: 2.5 }).setData(comp["Closed-Loop DBS"]?.energy || []);
    scrollChart(teedChart, PAYLOAD.t, PAYLOAD.windowSec);

    // #region agent log
    fetch('http://127.0.0.1:7538/ingest/bd5338f9-16af-480f-b848-3ec5469ef828',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'7f5275'},body:JSON.stringify({sessionId:'7f5275',location:'live_charts.html:boot',message:'chart_render_ok',data:{nLfp:(PAYLOAD.lfp||[]).length,intervention:PAYLOAD.interventionTime},timestamp:Date.now(),hypothesisId:'G',runId:'post-fix-v2'})}).catch(()=>{});
    // #endregion
  } catch (err) {
    document.body.innerHTML = '<pre style="color:#f85149;padding:12px;">Chart error: ' + err + '</pre>';
    fetch('http://127.0.0.1:7538/ingest/bd5338f9-16af-480f-b848-3ec5469ef828',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'7f5275'},body:JSON.stringify({sessionId:'7f5275',location:'live_charts.html:boot',message:'chart_render_error',data:{error:String(err)},timestamp:Date.now(),hypothesisId:'G',runId:'post-fix-v2'})}).catch(()=>{});
  }
}

boot();
</script>
</body>
</html>
"""


def render_live_charts(
    history: dict,
    comparison_history: dict,
    intervention_time_sec: Optional[float] = None,
    *,
    reset: bool = False,
) -> None:
    payload = build_live_chart_payload(
        history,
        comparison_history,
        intervention_time_sec=intervention_time_sec,
        reset=reset,
    )
    html = _CHART_HTML.replace("__PAYLOAD__", json.dumps(payload))
    components.html(html, height=_CHART_HEIGHT, scrolling=False)
