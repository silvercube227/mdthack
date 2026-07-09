# BLE DBS Hardware Link — Setup & Next Steps

This folder contains the two halves of the BLE link between the Streamlit
dashboard and the Arduino Nano ESP32 stimulator demo:

- `ble_dbs_host.py` — Python BLE **peripheral / GATT server** (runs on the
  laptop, started from the Streamlit sidebar). Uses [`bless`](https://pypi.org/project/bless/)
  for cross-platform peripheral support (WinRT on Windows, CoreBluetooth on
  macOS, BlueZ on Linux).
- `nano_dbs_receiver.ino` — Arduino Nano ESP32 BLE **central / client**. Scans
  for the host, subscribes to notifications, and drives an LED via PWM.

Both sides already share the same custom UUIDs and one-byte (`uint8`, 0-255)
payload format. See the docstring/comments in each file for the full design
rationale.

## 1. Python side (Windows laptop)

```powershell
pip install -r requirements.txt
```

This installs `bless` along with the existing project dependencies. No extra
system packages are needed on Windows (the WinRT backend ships with the
`winrt`/`bleak-winrt` wheel that `bless` depends on).

Quick standalone smoke test (no Arduino needed yet):

```powershell
python fw/ble_dbs_host.py
```

You should see logs like `BLE host starting...` → `Advertising started as
'DBS-Host'` → periodic `Amplitude updated to N, notification sent`. Press
Ctrl+C to stop. If you see `bless not available`, re-run the `pip install`
above.

Then run the full app as usual (`streamlit run app.py`) and use the
**Connect Bluetooth Device** button in the sidebar — this is already wired to
`start_ble_host()` / `stop_ble_host()`, and the live DBS amplitude (mA) is
pushed automatically every simulation tick via `update_amplitude()`.

## 2. Arduino side (Nano ESP32)

1. In the Arduino IDE, install the **"Arduino ESP32 Boards"** package (Boards
   Manager → search "Nano ESP32") if not already installed.
2. Select **Tools → Board → Nano ESP32**.
3. Open `nano_dbs_receiver.ino` and upload it. No extra libraries are
   required — `BLEDevice.h` ships with the board package.
4. Wire an LED: cathode → GND, anode → 220-470 Ω resistor → **D2**.
5. Open the Serial Monitor at **115200 baud** to watch the boot/scan/connect
   logs.

## 3. End-to-end test procedure

1. Power the Nano ESP32 (USB or battery) — Serial Monitor should show
   `Boot` → `Starting BLE scan for DBS Host service...`.
2. In the Streamlit sidebar, click **Connect Bluetooth Device**.
   - Python log: `Advertising started as 'DBS-Host'`.
3. Within a few seconds the Nano should log:
   `Target peripheral found` → `Connected to BLE DBS Host and subscribed to
   notifications`.
4. Change the DBS control mode / thresholds in the sidebar to vary the
   simulated amplitude — the LED brightness should track the **DBS
   Amplitude** KPI card in real time (0 mA → LED off, `MAX_STIM_MA` (3.5 mA)
   → full brightness).
5. Click **Disconnect Bluetooth Device** (or quit the Streamlit process) —
   the LED must go dark immediately and the Nano should resume scanning.
6. Click **Connect** again — the Nano should reconnect automatically without
   needing a re-upload or reset.

## 4. Troubleshooting

- **`bless not available` in Python logs**: `pip install bless` didn't
  complete, or you're in the wrong virtual environment.
- **Nano never finds the host**: confirm both `SERVICE_UUID` values in
  `ble_dbs_host.py` and `nano_dbs_receiver.ino` still match exactly, and that
  Bluetooth is enabled on the Windows laptop.
- **LED flickers to full brightness randomly**: check the LED wiring polarity
  and that D2 is actually connected (not floating).
- **Connection drops repeatedly**: increase `HEARTBEAT_INTERVAL_SEC` in
  `ble_dbs_host.py` isn't necessary for this — instead check for USB power
  brown-outs on the Nano, a common cause of BLE stack resets.

## 5. Known caveats

- This has been functionally validated on macOS (the available dev machine)
  end-to-end for the Python peripheral lifecycle (advertise → notify →
  stop). The Windows WinRT backend has not been hardware-tested yet — it is
  expected to behave the same or better (it has no equivalent of the
  CoreBluetooth "cached value + notify" restriction that had to be worked
  around on macOS).
- The `.ino` sketch has not been compiled on physical hardware; the API calls
  were cross-checked against the ESP32 Arduino BLE library's documented
  signatures but a real compile/upload pass on the Nano ESP32 is still the
  next concrete step.
