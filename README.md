# Closed-Loop Deep Brain Stimulation (DBS) Simulator

An interactive educational simulator that demonstrates how **adaptive (closed-loop) brain stimulation** could treat Parkinson’s disease more intelligently than traditional always-on stimulation.

This is **not** a medical device and **not** connected to a real patient. It is a computer model built from published clinical research, designed to help judges, students, and curious non-specialists understand *why* closed-loop DBS is an exciting idea—and what you should look for on the dashboard to know whether the system is “working well.”

---

## The problem in plain English

**Parkinson’s disease** affects movement. Many patients develop **tremor, stiffness, and slowness** (bradykinesia). One established treatment is **Deep Brain Stimulation (DBS)**: a small implanted device sends mild electrical pulses to a deep brain region called the **subthalamic nucleus (STN)**.

Traditional DBS is like a ** porch light left on 24/7**—it runs at fixed settings whether the patient feels good or bad. That can work, but it also:

- **Wastes battery** (implants need surgery to replace every few years)
- **Over-stimulates** the brain when symptoms are already low
- **Under-stimulates** during symptom flares when the brain needs more help

**Closed-loop (adaptive) DBS** tries to act more like a **thermostat**: it listens to the brain, detects when Parkinsonian activity rises, turns stimulation up, and turns it down when activity falls. The goal is **similar symptom control with less wasted energy**.

---

## What brain signal are we watching?

Inside the STN, doctors can record a slow electrical rhythm called a **Local Field Potential (LFP)**—think of it as the “background hum” of a brain region, not individual brain cells firing.

In Parkinson’s, a particular rhythm—the **beta band** (roughly 13–20 Hz, or 13–20 cycles per second)—often becomes **too strong and too sustained**. Clinicians describe this as **pathological beta activity**.

Key ideas:

| Term | Plain meaning |
|------|----------------|
| **Beta wave / beta oscillation** | A rhythmic pattern in the 13–20 Hz range associated with Parkinsonian motor symptoms |
| **Beta burst** | Beta doesn’t run constantly—it comes in **bursts** (short episodes of strong rhythm). Longer bursts correlate with worse symptoms |
| **Low-beta (LB, 13–20 Hz)** | The most clinically important part of the beta band for bradykinesia/rigidity |
| **High-beta (HB, 20–35 Hz)** | A higher-frequency beta component; also modulated by disease and treatment |
| **LFP power** | How *strong* that rhythm is—higher power generally means more pathological activity |
| **DBS amplitude (mA)** | How strongly the implant is stimulating—like volume on a speaker |

Our simulator uses numbers from real studies. For example, in one chronic recording study (Neumann et al., npj Parkinson’s Disease 2022), **low-beta power** in an untreated (“OFF medication”) state averaged about **8.4%** of total brain signal power, and dropped toward about **2.1%** when stimulation was working well.

---

## What this simulator does (the pipeline)

The dashboard runs a continuous loop that mirrors how real adaptive DBS systems are designed:

```
Simulated STN brain signal
    → Extract beta biomarker (how bad is the rhythm right now?)
    → Recommend therapy settings (thresholds, stim limits)
    → Apply DBS control policy (None / Fixed / Adaptive)
    → Stimulation suppresses beta in the next time step
    → Update live charts
```

Behind the scenes:

1. **`backend/signal_generator.py`** — Generates synthetic STN LFP with **beta bursts** whose length and strength change when you toggle medication OFF/ON or apply stimulation.
2. **`backend/signal_cleaning.py`** — Measures **low-beta power as % of total power** (matching clinical methods) and detects bursts.
3. **`backend/controller.py`** — Implements **ADAPT-PD**-style adaptive algorithms (Single Threshold and Dual Threshold).
4. **`backend/simulation.py`** — Runs three parallel “virtual patients” for comparison: **No DBS**, **Fixed DBS**, and **Closed-Loop DBS**.
5. **`frontend/`** — Streamlit dashboard and Plotly charts.

Parameters (sampling rate, burst durations, dose-response curves, ramp times) are calibrated from published papers—see [Clinical references](#clinical-references) at the bottom.

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

Your browser opens to the dashboard. The simulation **starts automatically** and refreshes several times per second.

Use **Pause** in the sidebar to freeze the simulation, or **Reset Simulation** to start over.

---

## Dashboard tour (for non-engineers)

### Sidebar: Neuromodulation Control Panel

| Control | What it means |
|---------|----------------|
| **DBS Control Mode** | Which stimulation strategy to use (see below) |
| **Dopaminergic State** | **OFF** = no levodopa (medication withdrawn)—symptoms and beta activity are worse. **ON** = medicated—beta bursts shorten, like in real patients after pills |
| **Single-Threshold LFP Power** | The “trip point” for adaptive mode: if beta power rises above this, stimulation increases |
| **Dual-Threshold Upper / Lower** | Hysteresis band for slower adaptive mode: upper triggers ramp-up, lower triggers ramp-down |
| **Lower / Upper Stim Limit (mA)** | Adaptive DBS never goes below the lower limit (avoiding “turning off” therapy) or above the upper limit (safety ceiling) |
| **Base Symptom Severity** | Scales how long beta bursts last in OFF medication—higher = more severe simulated disease |

### DBS Control Modes explained

| Mode | Real-world analogy | What you should expect |
|------|--------------------|------------------------|
| **None (Open-Loop Baseline)** | Implant off or not delivering therapy | Beta power stays relatively **high**; symptom burden **accumulates**; zero energy used |
| **Fixed DBS (cDBS)** | Traditional always-on DBS at ~2.5 mA | Beta **suppressed** steadily; symptom burden **lower**; energy use **high and constant** |
| **Adaptive — Single Threshold (ADAPT-PD)** | Smart thermostat with fast response (250 ms ramp) | Stimulation ** jumps between lower and upper limits** as beta crosses threshold; energy use **varies**—usually **less than fixed** |
| **Adaptive — Dual Threshold (ADAPT-PD)** | Smart thermostat with slow, gentle adjustments (2.5 min up / 5 min down) | Smoother amplitude changes; good for **slow symptom drift** (e.g., wearing off over hours) |

### Recommended Therapy Parameters panel

After ~5 seconds of recording, the simulator suggests thresholds and limits similar to how clinicians program the **Medtronic Percept** device in the **ADAPT-PD** clinical trial:

- **LFP threshold** from your recent beta activity (Timeline-style calibration)
- **Stim limits** from literature-based therapeutic ranges
- **ST vs DT mode** based on how *fast* beta fluctuates

Click **Apply Recommended Therapy Parameters** to copy suggestions into the sidebar sliders.

---

## The live metrics (top row)

| Metric | Good sign | Bad / concerning sign |
|--------|-----------|------------------------|
| **Low-Beta Power (%)** | Near **~8% OFF** without treatment; drops toward **~2%** under effective stimulation | Stays very high (>10%) despite Fixed or Adaptive DBS → therapy not suppressing beta |
| **High-Beta Power (%)** | Usually lower than low-beta; also drops with stimulation | Dominates the trace unexpectedly (context-dependent; less validated as primary biomarker) |
| **LB Burst Duration (ms)** | **OFF medication ~579 ms** average in literature; **~359 ms ON** medication | Very long bursts during active DBS → symptoms likely undertreated |
| **DBS Amplitude (mA)** | Adaptive mode: **alternates** between lower (~1.0) and upper (~2.5–3.0) limits; Fixed: **flat** at 2.5 | Adaptive stuck at upper limit 100% of the time → threshold may be too low or disease too severe |
| **Simulation Time (s)** | — | — |

Caption below metrics (when available):

- **Symptom reduction vs No DBS** — higher % is better for closed-loop
- **TEED savings vs Fixed DBS** — higher % means adaptive mode used **less energy** than always-on stimulation (battery win)

---

## The five charts (what am I looking at?)

### 1. Subthalamic Nucleus (STN) LFP — Raw waveform

**What it is:** The simulated “microphone recording” from the STN, in microvolts (µV).

**What to notice:** Bursts of rhythmic activity riding on noisy background. It will look jittery and fast—that is normal.

**Good:** Visible rhythm that **flattens or shrinks** when you switch from None → Fixed or Adaptive DBS.

**Bad:** Rhythm looks equally large regardless of mode (stimulation not coupling to the signal—check thresholds).

---

### 2. Pathological Beta Band Power (% total)

**What it is:** The main biomarker—how much **low-beta (13–20 Hz)** and **high-beta (20–35 Hz)** contribute to the overall signal, expressed as **percent of total power**.

**Reference lines on the chart:**

| Line | Meaning |
|------|---------|
| Gray dotted **~8.4%** | Literature average for untreated OFF-medication low-beta |
| Green dotted **~2.1%** | Literature average at **therapeutic** stimulation |

**Good:**

- **None mode:** Low-beta often **above** the green line, fluctuating around the gray OFF reference during bursts
- **Fixed / Adaptive:** Low-beta **trends downward**, ideally approaching or below the green therapeutic line during effective periods
- Orange dashed line = your **detection threshold**; adaptive mode reacts when the red trace crosses it

**Bad:**

- Low-beta **never** drops below threshold even with Fixed DBS → dose-response or calibration issue in the run (try Reset)
- Low-beta **always** below threshold → adaptive mode may rarely stimulate (energy-efficient but verify symptoms aren’t undertreated)

---

### 3. Low-Beta Burst Duration

**What it is:** How long the current beta burst has been active (milliseconds). Based on the burst generator’s internal state, calibrated to clinical averages.

**Reference lines:**

| Line | Meaning |
|------|---------|
| **579 ms (OFF)** | Average burst length without levodopa (106-patient study) |
| **359 ms (ON)** | Average burst length with levodopa |

**Good:**

- Toggle **Dopaminergic ON** → burst durations **shorten** toward ~360 ms range
- Effective DBS → fewer / shorter high-power bursts (symptom burden grows more slowly)

**Bad:**

- Burst durations stay long (>600 ms frequently) with Fixed DBS active → stimulation not breaking pathological bursts effectively

---

### 4. DBS Amplitude (mA)

**What it is:** How hard the controller is stimulating **right now**.

**Good:**

- **Fixed mode:** Flat line at **2.5 mA** (constant therapy)
- **Single Threshold adaptive:** Square-wave-like switching between **lower** and **upper** limits—spikes when beta is high, drops when beta falls
- **Dual Threshold adaptive:** Slow ramps—changes gradually over minutes

**Bad:**

- Adaptive mode pegged at **upper limit continuously** → “always max volume”; saves no battery vs fixed
- Adaptive mode pegged at **lower limit continuously** while beta power remains high → undertreatment

---

### 5. Closed-Loop Efficiency Metric (the “money plot”)

Two panels side by side, tracking three invisible parallel simulations:

| Trace color | Strategy |
|-------------|----------|
| Gray | **No DBS** |
| Purple | **Fixed DBS** |
| Green | **Closed-Loop DBS** (Single Threshold adaptive) |

**Left panel — Cumulative Patient Symptom Burden**

A proxy for total Parkinsonian burden over time (combines burst duration and beta power). **Lower is better.**

**Good:** Green (closed-loop) **well below gray** (no DBS), and **comparable to or below purple** (fixed).

**Bad:** Green line **tracks with or above gray** → adaptive therapy not helping symptoms.

**Right panel — Total Energy Delivered (TEED proxy)**

Measures cumulative stimulation energy (proportional to amplitude squared × time). **Lower is better for battery life.**

**Good:** Green **clearly below purple** while left-panel symptom burden stays similar—this is the core value proposition: **“same relief, less energy.”** Real ADAPT-PD studies report roughly **48–74%** energy savings in short-term comparisons; our simplified model may show more modest savings but should trend in the same direction.

**Bad:** Green energy **equals or exceeds purple** while symptoms aren’t better → worst of both worlds.

**Ideal pattern to demo to judges:**

```
Symptom burden:  No DBS (highest) > Closed-Loop ≈ Fixed DBS (lowest)
Energy (TEED):   Fixed DBS (highest) > Closed-Loop >> No DBS (zero)
```

That is: closed-loop **matches fixed symptom control** while **using less electricity**.

---

## Suggested demo script (5 minutes)

1. **Start on None, Dopaminergic OFF** — point at rising low-beta power and symptom burden (gray line climbing on money plot).
2. **Switch to Fixed DBS** — beta drops; symptom burden slows; TEED rises steadily (purple line).
3. **Switch to Single Threshold Adaptive** — watch DBS amplitude bounce between limits; TEED (green) should grow **slower** than purple.
4. **Toggle Dopaminergic ON** — burst durations shrink; beta power falls further (medication effect).
5. **Click Apply Recommended Therapy Parameters** — show automated calibration.
6. **Read the money plot** — “Same symptom control, less energy.”

---

## Project structure

```
mdthack/
├── app.py                      # Entry point — run this with Streamlit
├── requirements.txt
├── README.md
├── backend/
│   ├── clinical_parameters.py  # Literature constants & dose-response
│   ├── constants.py            # Control modes & shared settings
│   ├── signal_generator.py     # Simulated STN LFP with beta bursts
│   ├── signal_cleaning.py      # Biomarker extraction & calibration
│   ├── controller.py           # ADAPT-PD Single/Dual Threshold aDBS
│   ├── simulation.py           # Closed-loop orchestration & comparisons
│   └── therapy_recommendation.py
└── frontend/
    ├── app.py                  # Dashboard layout
    ├── session.py              # Sidebar & session state
    ├── plots.py                # Plotly figures
    └── therapy_panel.py        # Therapy suggestion UI
```

---

## Clinical references

This simulator is **inspired by and parameterized from** peer-reviewed research—not a substitute for it.

| Topic | Source |
|-------|--------|
| Beta suppression vs stimulation amplitude; % power metrics | Neumann et al., *npj Parkinson’s Disease* 2022 |
| Beta burst dynamics OFF/ON levodopa | Tinkhauser et al., *Brain* 2017 |
| LB burst duration vs symptoms (n=106) | Anderson et al., *npj Parkinson’s Disease* 2023 |
| ADAPT-PD trial: Single/Dual Threshold aDBS, TEED endpoints | Stanslaski et al., *npj Parkinson’s Disease* 2024 |
| Percept sensing at 250 Hz | Neumann et al., *npj Parkinson’s Disease* 2024 |

---

## Important limitations (please read)

- **Simulation only.** No human or animal data is recorded in real time.
- **Reduced physics.** Real DBS involves electrode geometry, tissue impedance, stimulation artifacts, and patient-specific anatomy—we model the **control logic and average statistics**, not every biophysical detail.
- **Single biomarker.** Clinical Parkinson’s is multidimensional (tremor, gait, cognition, dyskinesia). We focus on **low-beta STN LFP**, the best-validated signal for adaptive DBS today, but it does not capture everything.
- **Numbers are population averages.** Your dashboard may show values that fluctuate around literature targets (e.g., 8.4% OFF beta) rather than hitting them exactly every second—that is expected in a stochastic burst model.

---

## Troubleshooting

| Issue | Try |
|-------|-----|
| Blank charts at start | Wait 2–3 seconds for buffers to fill |
| `ModuleNotFoundError` | Activate venv and `pip install -r requirements.txt` |
| Sliders feel “jumpy” after Apply | Normal—Reset Simulation for a clean baseline |
| Adaptive never drops amplitude | Lower the threshold or increase upper/lower spread |

---

## License & purpose

Built as an **educational demonstration** of closed-loop neuromodulation control systems. If you use it in a competition, paper, or clinic, cite the underlying clinical studies above and clearly state that outputs are **simulated**.

For questions about the code architecture, see inline module docstrings in `backend/` and `frontend/`.
