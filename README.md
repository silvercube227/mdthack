# Closed-Loop Deep Brain Stimulation (DBS) Simulator

An interactive, Medtronic-themed simulator that demonstrates how **adaptive
(closed-loop) brain stimulation** could treat Parkinson's disease more
intelligently than traditional always-on stimulation — with an optional
**Bluetooth Low Energy link** that drives a physical Arduino stimulator demo in
real time.

This is **not** a medical device and **not** connected to a real patient. It is
a computer model built from published clinical research, designed to help
judges, students, and curious non-specialists understand *why* closed-loop DBS
is an exciting idea — and what to look for on the dashboard to know whether the
system is "working well."

---

## The problem in plain English

**Parkinson's disease** affects movement. Many patients develop **tremor,
stiffness, and slowness** (bradykinesia). One established treatment is **Deep
Brain Stimulation (DBS)**: a small implanted device sends mild electrical pulses
to a deep brain region called the **subthalamic nucleus (STN)**.

Traditional DBS is like a **porch light left on 24/7** — it runs at fixed
settings whether the patient feels good or bad. That can work, but it also:

- **Wastes battery** (implants need surgery to replace every few years)
- **Over-stimulates** the brain when symptoms are already low
- **Under-stimulates** during symptom flares when the brain needs more help

**Closed-loop (adaptive) DBS** tries to act more like a **thermostat**: it
listens to the brain, detects when Parkinsonian activity rises, turns
stimulation up, and turns it down when activity falls. The goal is **similar
symptom control with less wasted energy**.

---

## What brain signal are we watching?

Inside the STN, doctors can record a slow electrical rhythm called a **Local
Field Potential (LFP)** — think of it as the "background hum" of a brain region.

In Parkinson's, a particular rhythm — the **beta band** (roughly 13–20 Hz) —
often becomes **too strong and too sustained**. Clinicians call this
**pathological beta activity**.

| Term | Plain meaning |
|------|----------------|
| **Beta burst** | Beta comes in **bursts** — short episodes of strong rhythm. Longer bursts correlate with worse symptoms |
| **Low-beta (LB, 13–20 Hz)** | The most clinically important beta sub-band for bradykinesia/rigidity |
| **High-beta (HB, 20–35 Hz)** | A higher-frequency beta component; also modulated by disease and treatment |
| **LFP power** | How *strong* the rhythm is — higher power generally means more pathological activity |
| **DBS amplitude (mA)** | How strongly the implant stimulates — like volume on a speaker |

Numbers come from real studies. In one chronic recording study (Neumann et al.,
npj Parkinson's Disease 2022), **low-beta power** averaged about **8.4%** of
total signal power OFF medication and dropped toward about **2.1%** under
effective stimulation.

---

## What this simulator does (the pipeline)

```
Simulated STN brain signal
    → Extract beta biomarker (how bad is the rhythm right now?)
    → Recommend therapy settings (thresholds, stim limits)
    → Apply a DBS control policy (None / Fixed / Adaptive)
    → Stimulation suppresses beta in the next time step
    → Publish live data  →  browser charts + (optional) BLE stimulator
```

Behind the scenes:

1. **`backend/signal_generator.py`** — Generates synthetic STN LFP with **beta
   bursts** whose length/strength change with medication (OFF/ON) and stimulation.
2. **`backend/signal_cleaning.py`** — Measures **low-beta power as % of total
   power** (matching clinical methods) and detects bursts.
3. **`backend/controller.py`** — Implements **ADAPT-PD**-style adaptive
   algorithms (Single Threshold and Dual Threshold).
4. **`backend/simulation.py`** — Runs the main patient plus three parallel
   "virtual patients" (**No DBS**, **Fixed DBS**, **Closed-Loop DBS**) for
   comparison, and records each arm's raw STN LFP.
5. **`backend/therapy_recommendation.py`** — Suggests thresholds/limits from the
   recent biomarker timeline (ADAPT-PD programming analogue).
6. **`frontend/`** — Streamlit dashboard, a persistent uPlot chart iframe, and
   the Medtronic design system.
7. **`fw/`** — Optional BLE hardware link (Python GATT host + Arduino Nano
   ESP32 client) that mirrors the live DBS amplitude onto a real LED.

---

## Architecture at a glance

- **Simulation runs inside the Streamlit fragment** (`live_metrics`) about
  every 0.4 s, advancing the model and writing a small JSON payload to
  `static/dbs_live.json`.
- **Charts live in a persistent browser iframe** (`frontend/live_charts.py`,
  built on [uPlot](https://github.com/leeoniya/uPlot)). The iframe is mounted
  **once** and polls the JSON on its own timer, so the charts update **in place,
  flicker-free**, fully decoupled from Streamlit reruns. Streamlit's static file
  serving (`enableStaticServing`) exposes the payload at `app/static/…`.
- **The x-axis scroll window is computed server-side** from the monotonic
  simulation clock, so it fills cleanly from 0 → 15 s and then scrolls smoothly
  without flip-flopping or clipping.
- **The UI is forced into light mode** (Medtronic navy `#170F5F` / cobalt
  `#0077C8`) regardless of the browser's dark-mode preference.

---

## Quick start

### Prerequisites

- Python 3.10+ recommended

### Install and run

```bash
cd mdthack
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Your browser opens to the dashboard. The simulation **starts automatically**.
Use **Pause** in the sidebar to freeze it, or **Reset** to return to the
open-loop baseline.

> The chart iframe loads uPlot from a CDN on first render, so an internet
> connection is needed the first time you open the app.

---

## Dashboard tour

### Sidebar — Control Panel

| Control | What it means |
|---------|----------------|
| **Device Connection** | Start/stop the BLE stimulator link (see [Hardware link](#optional-hardware-link-ble)). Shows *BLE advertising* when active |
| **DBS Control Mode** | Which stimulation strategy to use (see below) |
| **Dopaminergic State** | **OFF** = medication withdrawn (worse symptoms/beta); **ON** = medicated (beta bursts shorten) |
| **Single-Threshold LFP Power** | Trip point for fast adaptive mode: beta above this → stimulation increases |
| **Dual-Threshold Upper / Lower** | Hysteresis band for the slow adaptive mode |
| **Lower / Upper Stim Limit (mA)** | Adaptive DBS never goes below the lower limit or above the upper (safety) |
| **Base Symptom Severity** | Scales OFF-medication burst duration around the literature mean (579 ms) |
| **Reset / Pause** | Reset to open-loop baseline / freeze the simulation |

### DBS Control Modes

| Mode | Real-world analogy | What to expect |
|------|--------------------|----------------|
| **None (Open-Loop Baseline)** | Implant not delivering therapy | Beta stays **high**; symptom burden **accumulates**; zero energy |
| **Fixed DBS (cDBS)** | Traditional always-on DBS | Beta **suppressed** steadily; energy use **high and constant** |
| **Adaptive — Single Threshold (ADAPT-PD)** | Fast thermostat (250 ms ramp) | Stimulation **jumps between limits** as beta crosses threshold; usually **less energy than fixed** |
| **Adaptive — Dual Threshold (ADAPT-PD)** | Slow thermostat (2.5 min up / 5 min down) | Smooth ramps; good for **slow wearing-off drift** |

### Recommended Therapy Parameters panel

After a few seconds of recording, the panel suggests parameters the way
clinicians program the **Medtronic Percept** device in the **ADAPT-PD** trial:

- **ST Threshold** and **DT Thresholds** from your recent beta activity
- **Stim Limits** from literature-based therapeutic ranges
- **Suggested Mode** based on how fast beta fluctuates

Click **Apply Recommended Therapy Parameters** to copy the suggestions into the
sidebar controls (this also marks the "intervention" moment used by the
comparison arms).

---

## The live metrics (KPI cards)

| Card | Good sign |
|------|-----------|
| **Low-Beta Power** | ~8% OFF without treatment; drops toward ~2% under effective stimulation (delta shown vs the 2.1% target) |
| **High-Beta Power** | Usually lower than low-beta; also drops with stimulation |
| **Burst Duration** | OFF ~579 ms; ON ~359 ms (delta shown vs the ON mean) |
| **DBS Amplitude** | Fixed: flat ~2.5 mA; Adaptive: alternates between limits |
| **Elapsed** | Simulation time |

Once you apply a therapy (the "intervention"), two outcome cards appear:

- **Symptom reduction vs No DBS** — higher % is better for closed-loop
- **Energy saved vs Fixed DBS** — higher % means the adaptive arm used less
  energy than always-on stimulation (the core "same relief, less battery" story)

---

## The charts

All charts are full-width, stacked, and share a smooth 15-second scrolling
window with an orange marker at the moment therapy was applied.

1. **STN LFP — Raw Simulated** — the untreated (No DBS) STN waveform (µV).
2. **STN LFP — Treated Simulated** — the Closed-Loop DBS arm's waveform. Before
   you apply therapy the two traces are identical; afterwards the treated trace
   visibly **shrinks** as stimulation suppresses beta — the headline comparison.
3. **Pathological Beta Power (% total)** — low-beta (red), high-beta (purple),
   and the detection threshold (dashed amber), with reference lines at the
   literature OFF (~8.4%) and therapeutic (~2.1%) levels.
4. **DBS Amplitude (mA)** — the controller's output over time.
5. **Low-Beta Burst Duration (ms)** — with OFF (579 ms) and ON (359 ms)
   reference lines.

---

## Optional hardware link (BLE)

The **Connect Bluetooth Device** button in the sidebar starts a cross-platform
BLE **GATT server** on your laptop (`fw/ble_dbs_host.py`, built on
[`bless`](https://pypi.org/project/bless/)). An **Arduino Nano ESP32** running
`fw/nano_dbs_receiver.ino` acts as the BLE **client**: it connects, subscribes,
and drives an LED whose brightness tracks the live **DBS Amplitude** KPI
(0 mA → off, 3.5 mA → full brightness). The dashboard pushes the amplitude every
simulation tick via `update_amplitude()`.

`bless` is included in `requirements.txt`. Full wiring, upload, and end-to-end
test steps are in **[`fw/README.md`](fw/README.md)**. The link is optional — the
dashboard runs fully without any hardware connected.

---

## Suggested demo script (5 minutes)

1. **Start on None, Dopaminergic OFF** — Raw and Treated STN traces match; beta
   power sits near the OFF reference and symptom burden accumulates.
2. **Switch to Fixed DBS** — beta drops; the Treated trace shrinks; DBS
   amplitude is flat.
3. **Switch to Single-Threshold Adaptive** — watch DBS amplitude bounce between
   limits and the *Energy saved vs Fixed DBS* card climb.
4. **Toggle Dopaminergic ON** — burst durations shorten toward ~359 ms.
5. **Click Apply Recommended Therapy Parameters** — show automated calibration.
6. *(Optional)* **Connect INS Device ** — the Arduino LED now tracks the
   live amplitude.

---

## Project structure

```
mdthack/
├── app.py                       # Entry point — run with Streamlit
├── requirements.txt
├── README.md
├── .streamlit/config.toml       # Medtronic light theme + static file serving
├── static/                      # Runtime-generated live-chart payload (served)
├── backend/
│   ├── clinical_parameters.py   # Literature constants & dose-response
│   ├── constants.py             # Control modes & shared settings
│   ├── signal_generator.py      # Simulated STN LFP with beta bursts
│   ├── signal_cleaning.py       # Biomarker extraction & calibration
│   ├── controller.py            # ADAPT-PD Single/Dual Threshold aDBS
│   ├── simulation.py            # Closed-loop orchestration & comparison arms
│   └── therapy_recommendation.py
├── frontend/
│   ├── app.py                   # Dashboard layout & live fragment
│   ├── session.py               # Sidebar, session state, BLE controls
│   ├── plots.py                 # Live JSON payload builder/writer
│   ├── live_charts.py           # Persistent uPlot chart iframe
│   ├── theme.py                 # Medtronic design system + forced-light CSS
│   └── therapy_panel.py         # Therapy recommendation panel
└── fw/
    ├── ble_dbs_host.py          # Python BLE GATT server (peripheral)
    ├── nano_dbs_receiver.ino    # Arduino Nano ESP32 BLE client
    └── README.md                # Hardware setup & test procedure
```

---

## Clinical references

Inspired by and parameterized from peer-reviewed research — not a substitute for it.

| Topic | Source |
|-------|--------|
| Beta suppression vs stimulation amplitude; % power metrics | Neumann et al., *npj Parkinson's Disease* 2022 |
| Beta burst dynamics OFF/ON levodopa | Tinkhauser et al., *Brain* 2017 |
| LB burst duration vs symptoms (n=106) | Anderson et al., *npj Parkinson's Disease* 2023 |
| ADAPT-PD trial: Single/Dual Threshold aDBS, TEED endpoints | Stanslaski et al., *npj Parkinson's Disease* 2024 |
| Percept sensing at 250 Hz | Neumann et al., *npj Parkinson's Disease* 2024 |

---

## Important limitations (please read)

- **Simulation only.** No human or animal data is recorded in real time.
- **Reduced physics.** We model the **control logic and average statistics**,
  not electrode geometry, tissue impedance, or patient-specific anatomy.
- **Single biomarker.** We focus on **low-beta STN LFP**, the best-validated
  signal for adaptive DBS today — it does not capture tremor, gait, or cognition.
- **Numbers are population averages** and fluctuate around literature targets by
  design (stochastic burst model).
- **The BLE hardware demo is illustrative** — the LED brightness is a stand-in
  for stimulation amplitude, not a real stimulator output.

---

## Troubleshooting

| Issue | Try |
|-------|-----|
| Blank charts at start | Wait 2–3 seconds for buffers to fill; ensure internet access (uPlot CDN) |
| `ModuleNotFoundError` | Activate the venv and `pip install -r requirements.txt` |
| Sliders feel "jumpy" after Apply | Normal — use **Reset** for a clean baseline |
| Adaptive never drops amplitude | Lower the threshold or widen the upper/lower spread |
| `bless not available` in logs | `pip install bless` didn't finish, or wrong venv (BLE link only) |
| Nano never finds the host | Confirm the UUIDs match and Bluetooth is on — see `fw/README.md` |

---

## License & purpose

Built as an **educational demonstration** of closed-loop neuromodulation control
systems. If you use it in a competition, paper, or clinic, cite the underlying
clinical studies above and clearly state that outputs are **simulated**.

For code architecture details, see the inline module docstrings in `backend/`,
`frontend/`, and `fw/`.
