"""Persistent live-chart iframe (uPlot).

Rendered exactly once per page load (outside any ``run_every`` fragment) so the
iframe is never re-mounted by Streamlit. It polls the static JSON payload on its
own timer and updates each chart in place with ``uPlot.setData`` — a smooth,
flicker-free scrolling view fully decoupled from Streamlit reruns.

Rendering is defensive: every chart update is length-guarded and isolated so a
single transient/ragged frame can never blank a chart or surface an error.
"""

from __future__ import annotations

import streamlit.components.v1 as components

from frontend.plots import LIVE_DATA_URL, SCROLL_WINDOW_SEC

_CHART_HEIGHT = 1080

_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="color-scheme" content="light only"/>
<link rel="stylesheet" href="https://unpkg.com/uplot@1.6.31/dist/uPlot.min.css"/>
<script src="https://unpkg.com/uplot@1.6.31/dist/uPlot.iife.min.js"></script>
<style>
  :root { color-scheme: light only; }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: #F4F6FB; color: #1B1B2F;
               font-family: Inter, 'Segoe UI', Roboto, sans-serif; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 1px; }
  .card { background: #FFFFFF; border: 1px solid #E1E6EF; border-radius: 12px;
          padding: 10px 12px 6px; box-shadow: 0 1px 3px rgba(23,15,95,0.04); }
  .card.wide { grid-column: 1 / -1; }
  .card h3 { margin: 0 0 6px 0; font-size: 13px; font-weight: 600; color: #170F5F; }
  .chart { width: 100%; }
  .u-legend { font-size: 11px; color: #4A5261; }
  .u-legend .u-marker { width: 10px; height: 10px; }
  #fatal { display: none; color: #C8102E; font-size: 13px; padding: 12px; }
</style>
</head>
<body>
<div id="fatal"></div>
<div class="grid">
  <div class="card wide"><h3>STN Local Field Potential (raw µV)</h3><div id="c-stn" class="chart"></div></div>
  <div class="card wide"><h3>Pathological Beta Power (% total spectral power)</h3><div id="c-beta" class="chart"></div></div>
  <div class="card"><h3>DBS Amplitude — controller output (mA)</h3><div id="c-dbs" class="chart"></div></div>
  <div class="card"><h3>Low-Beta Burst Duration (ms)</h3><div id="c-burst" class="chart"></div></div>
  <div class="card"><h3>Cumulative Symptom Burden — lower is better</h3><div id="c-sym" class="chart"></div></div>
  <div class="card"><h3>Total Energy Delivered — lower is better</h3><div id="c-teed" class="chart"></div></div>
</div>
<script>
const DATA_URL = "__DATA_URL__";
const WINDOW = __WINDOW__;
const C = {
  cobalt:"#0077C8", red:"#C8102E", purple:"#6B4EFF", amber:"#E8A33D",
  green:"#00843D", gray:"#9AA5B4", muted:"#5F6876", slate:"#4A5261",
  grid:"#EDF0F6", border:"#E1E6EF", ink:"#1B1B2F",
};

let intervention = null;
let refs = { offLb: 8.43, therLb: 2.11, burstOff: 579, burstOn: 359, maxMa: 3.5 };

/* ---- plugins ------------------------------------------------------------- */
function vLinePlugin() {
  return { hooks: { draw: u => {
    if (intervention == null) return;
    const xr = u.scales.x.range(u, u.scales.x.min, u.scales.x.max);
    if (intervention < xr[0] || intervention > xr[1]) return;
    const x = Math.round(u.valToPos(intervention, "x", true));
    const ctx = u.ctx;
    ctx.save();
    ctx.strokeStyle = C.cobalt; ctx.lineWidth = 1.5; ctx.setLineDash([5,4]);
    ctx.beginPath(); ctx.moveTo(x, u.bbox.top); ctx.lineTo(x, u.bbox.top + u.bbox.height); ctx.stroke();
    ctx.restore();
  }}};
}
function hLinePlugin(getLines) {
  return { hooks: { draw: u => {
    const ctx = u.ctx;
    for (const ln of getLines()) {
      const y = Math.round(u.valToPos(ln.y, "y", true));
      if (y < u.bbox.top || y > u.bbox.top + u.bbox.height) continue;
      ctx.save();
      ctx.strokeStyle = ln.color; ctx.lineWidth = 1; ctx.setLineDash([2,3]);
      ctx.beginPath(); ctx.moveTo(u.bbox.left, y); ctx.lineTo(u.bbox.left + u.bbox.width, y); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = ln.color; ctx.font = "10px Inter, sans-serif";
      ctx.textBaseline = "bottom"; ctx.textAlign = "right";
      ctx.fillText(ln.label, u.bbox.left + u.bbox.width - 4, y - 2);
      ctx.restore();
    }
  }}};
}

/* ---- chart factory ------------------------------------------------------- */
function xScale() {
  return { time: false, range: (u, min, max) => {
    if (max == null || max <= WINDOW) return [0, WINDOW];
    return [max - WINDOW, max];
  }};
}
function axes(yLabel) {
  const base = { stroke: C.slate, grid: { stroke: C.grid, width: 1 },
                 ticks: { stroke: C.border, width: 1 }, font: "11px Inter, sans-serif" };
  return [
    { ...base, values: (u, vs) => vs.map(v => v.toFixed(0)) },
    { ...base, label: yLabel, labelFont: "11px Inter, sans-serif", labelSize: 30, size: 52 },
  ];
}
function serie(label, color, opts = {}) {
  return { label, stroke: color, width: opts.width || 2, dash: opts.dash, points: { show: false },
           value: (u, v) => v == null ? "--" : v.toFixed(opts.dp == null ? 2 : opts.dp) };
}
function make(elId, series, yLabel, plugins, yRange, legend) {
  const el = document.getElementById(elId);
  const h = elId === "c-stn" ? 180 : (elId === "c-beta" ? 205
          : (elId === "c-sym" || elId === "c-teed" ? 205 : 175));
  const opts = {
    width: el.clientWidth || 600, height: h,
    legend: { show: !!legend },
    cursor: { drag: { x: false, y: false }, points: { show: false }, y: false },
    scales: { x: xScale(), y: yRange ? { range: () => yRange } : {} },
    axes: axes(yLabel),
    series: [{}].concat(series),
    plugins: plugins || [],
  };
  const u = new uPlot(opts, [[]].concat(series.map(() => [])), el);
  new ResizeObserver(() => u.setSize({ width: el.clientWidth || 600, height: h })).observe(el);
  return u;
}

/* Length-guarded, isolated update — a ragged/transient frame is skipped, never thrown. */
function safeSet(u, data) {
  if (!u || !data || !data[0]) return;
  const L = data[0].length;
  for (let i = 1; i < data.length; i++) {
    if (!Array.isArray(data[i]) || data[i].length !== L) return;
  }
  try { u.setData(data); } catch (e) { /* skip this frame */ }
}

/* ---- build charts once --------------------------------------------------- */
let cStn, cBeta, cDbs, cBurst, cSym, cTeed;
function buildCharts() {
  cStn = make("c-stn", [serie("STN LFP", C.cobalt, { width: 1.4 })], "µV",
    [vLinePlugin()], [-38, 38], false);

  cBeta = make("c-beta",
    [serie("Low-beta 13–20 Hz", C.red, { width: 2.2 }),
     serie("High-beta 20–35 Hz", C.purple, { width: 1.6 }),
     serie("Threshold", C.amber, { width: 1.6, dash: [6,4] })],
    "% total",
    [vLinePlugin(), hLinePlugin(() => [
       { y: refs.offLb, color: C.muted, label: "OFF ref 8.4%" },
       { y: refs.therLb, color: C.green, label: "Therapeutic 2.1%" }])],
    [0, 36], true);

  cDbs = make("c-dbs", [serie("DBS mA", C.green, { width: 2 })], "mA",
    [vLinePlugin()], [0, refs.maxMa * 1.05], false);

  cBurst = make("c-burst", [serie("Burst ms", C.amber, { width: 2, dp: 0 })], "ms",
    [vLinePlugin(), hLinePlugin(() => [
       { y: refs.burstOff, color: C.muted, label: "OFF 579 ms" },
       { y: refs.burstOn, color: C.green, label: "ON 359 ms" }])],
    null, false);

  const comp = () => [
    serie("No DBS", C.gray, { width: 2, dash: [4,4], dp: 0 }),
    serie("Fixed DBS", C.purple, { width: 2, dp: 0 }),
    serie("Closed-Loop DBS", C.cobalt, { width: 3, dp: 0 }),
  ];
  cSym = make("c-sym", comp(), "ms·s", [vLinePlugin()], null, true);
  cTeed = make("c-teed", comp(), "mA²·s", [vLinePlugin()], null, true);
}

/* ---- polling loop -------------------------------------------------------- */
async function poll() {
  let d;
  try {
    const res = await fetch(DATA_URL + "?t=" + Date.now(), { cache: "no-store" });
    if (!res.ok) return;
    d = await res.json();
  } catch (e) { return; }               // transient network/parse — keep last good frame
  if (!d || !d.t) return;

  refs = d.refs || refs;
  intervention = d.intervention;

  safeSet(cStn,  [d.t, d.stn]);
  safeSet(cBeta, [d.t, d.lb, d.hb, d.thr]);
  safeSet(cDbs,  [d.t, d.dbs]);
  safeSet(cBurst,[d.t, d.burst]);
  const ct = d.comp && d.comp.t, sy = d.comp && d.comp.symptom, en = d.comp && d.comp.energy;
  if (ct && sy) safeSet(cSym,  [ct, sy["No DBS"], sy["Fixed DBS"], sy["Closed-Loop DBS"]]);
  if (ct && en) safeSet(cTeed, [ct, en["No DBS"], en["Fixed DBS"], en["Closed-Loop DBS"]]);
}

function boot() {
  if (typeof uPlot === "undefined") {
    const f = document.getElementById("fatal");
    f.textContent = "Charts failed to load (uPlot unavailable). Check your network connection.";
    f.style.display = "block";
    return;
  }
  buildCharts();
  poll();
  setInterval(poll, 200);
}
boot();
</script>
</body>
</html>
"""


def render_persistent_charts() -> None:
    html = _HTML.replace("__DATA_URL__", LIVE_DATA_URL).replace("__WINDOW__", str(SCROLL_WINDOW_SEC))
    components.html(html, height=_CHART_HEIGHT, scrolling=False)
