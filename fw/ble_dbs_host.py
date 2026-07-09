"""
BLE DBS Host - GATT server (peripheral) for the Arduino Nano ESP32 stimulation client.

Platform note
-------------
The original implementation used `bluezero`, which only implements the BLE
peripheral/GATT-server role on Linux (via BlueZ over D-Bus). It cannot advertise
a GATT server on macOS or Windows at all, so it was non-functional on this
demo machine.

There is no CoreBluetooth-based peripheral support in `bleak` (bleak is a
BLE-central/client library only), so we use `bless` instead -- a GATT-server
library that is a genuine cross-platform supplement to bleak (CoreBluetooth on
macOS, BlueZ on Linux, WinRT on Windows). This preserves the original
architecture:

    Python (this file)  = BLE peripheral / GATT server / advertiser
    Arduino Nano ESP32   = BLE central / client (scans, connects, subscribes)

Public API (unchanged): `start_ble_host()`, `update_amplitude(value)`, `stop_ble_host()`.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from bless import (
        BlessGATTCharacteristic,
        BlessServer,
        GATTAttributePermissions,
        GATTCharacteristicProperties,
    )

    BLESS_AVAILABLE = True
except ImportError:
    BLESS_AVAILABLE = False
    logger.warning("bless not available. Install with: pip install bless")

# The maximum DBS amplitude (mA) the controller can command -- mirrors
# backend.clinical_parameters.MAX_STIM_MA. Imported defensively so this module
# still runs standalone (e.g. `python fw/ble_dbs_host.py`) without the project
# root on sys.path.
try:
    from backend.clinical_parameters import MAX_STIM_MA
except ImportError:
    MAX_STIM_MA = 3.5  # Fallback -- keep in sync with backend/clinical_parameters.py

DEVICE_NAME = "DBS-Host"

# Custom random 128-bit UUIDs generated for this project (NOT SIG-adopted
# placeholder UUIDs). Must match the values in fw/nano_dbs_receiver.ino exactly.
SERVICE_UUID = "30f38274-4fee-49d5-9dda-c671f21497b2"
CHARACTERISTIC_UUID = "8ed6f47d-f7ef-4220-beea-26075caa24fc"

# Periodic notification even if the value hasn't changed, so a subscribed
# client always sees fresh traffic. Purely a reliability aid.
HEARTBEAT_INTERVAL_SEC = 1.0


def ma_to_uint8(amplitude_ma: float, max_ma: float = MAX_STIM_MA) -> int:
    """Map a DBS amplitude in mA (0..max_ma) to a single-byte BLE payload (0-255).

    This is the single place amplitude scaling happens. `amplitude_ma` should
    always be the real project amplitude (the same value shown on the
    dashboard's "DBS Amplitude" KPI, i.e. `history["dbs_amplitude_ma"][-1]` in
    backend/simulation.py), never a value that has already been pre-scaled.
    """
    if max_ma <= 0:
        return 0
    fraction = max(0.0, min(1.0, amplitude_ma / max_ma))
    return int(round(fraction * 255))


class BLEDBSHost:
    """BLE GATT server host for DBS stimulation control (bless-based)."""

    def __init__(self) -> None:
        self.running = False
        self.server: Optional["BlessServer"] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._current_uint8 = 0
        self._ready_event = threading.Event()
        self._ready_ok = False

    # -- bless callbacks ----------------------------------------------------
    def _read_request(self, characteristic: "BlessGATTCharacteristic", **_kwargs: Any) -> bytearray:
        return characteristic.value

    # -- background asyncio loop --------------------------------------------
    def _thread_main(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._async_start())
            self._ready_ok = True
        except Exception:
            logger.exception("Failed to start BLE GATT server")
            self._ready_ok = False
        finally:
            self._ready_event.set()

        if self._ready_ok:
            heartbeat_task = self.loop.create_task(self._heartbeat_loop())
            try:
                self.loop.run_forever()
            finally:
                heartbeat_task.cancel()
                try:
                    self.loop.run_until_complete(self._async_stop())
                except Exception:
                    logger.exception("Error while stopping BLE GATT server")

        self.loop.close()
        self.running = False

    async def _async_start(self) -> None:
        logger.info("BLE host starting, creating GATT service %s", SERVICE_UUID)
        server = BlessServer(name=DEVICE_NAME, loop=self.loop)
        server.read_request_func = self._read_request

        await server.add_new_service(SERVICE_UUID)

        char_flags = GATTCharacteristicProperties.read | GATTCharacteristicProperties.notify
        permissions = GATTAttributePermissions.readable
        # NOTE: value=None here is required, not optional -- and it must stay
        # unset until *after* server.start(). On macOS (CoreBluetooth), a service
        # cannot be registered with the peripheral manager while one of its
        # characteristics has a "cached" (ever-set) value AND the `notify`
        # property; doing so raises NSInternalInconsistencyException. Once the
        # service is registered, it's safe to set/push the initial value.
        await server.add_new_characteristic(
            SERVICE_UUID, CHARACTERISTIC_UUID, char_flags, None, permissions
        )

        await server.start()
        self.server = server
        server.get_characteristic(CHARACTERISTIC_UUID).value = bytearray([0])
        logger.info("Advertising started as '%s'", DEVICE_NAME)

    async def _async_update(self, value: int) -> None:
        if self.server is None:
            return
        characteristic = self.server.get_characteristic(CHARACTERISTIC_UUID)
        characteristic.value = bytearray([value])
        self.server.update_value(SERVICE_UUID, CHARACTERISTIC_UUID)
        logger.info("Amplitude updated to %d, notification sent", value)

    async def _heartbeat_loop(self) -> None:
        """Re-send the current value periodically to keep the link fresh."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL_SEC)
                with self._lock:
                    value = self._current_uint8
                await self._async_update(value)
        except asyncio.CancelledError:
            pass

    async def _async_stop(self) -> None:
        if self.server is not None:
            await self.server.stop()
            logger.info("BLE host stopped")
            self.server = None

    # -- public API -----------------------------------------------------------
    def start(self) -> bool:
        """Start advertising the BLE GATT server."""
        if self.running:
            logger.warning("BLE host already running")
            return False
        if not BLESS_AVAILABLE:
            logger.error("bless library not available")
            return False

        self.running = True
        self._ready_event.clear()
        self.thread = threading.Thread(target=self._thread_main, daemon=True, name="ble-dbs-host")
        self.thread.start()

        if not self._ready_event.wait(timeout=10.0):
            logger.error("Timed out waiting for BLE host to start")
            self.running = False
            return False
        if not self._ready_ok:
            self.running = False
            return False
        return True

    def update_amplitude(self, value: float) -> None:
        """Queue a DBS amplitude update.

        Args:
            value: DBS amplitude in mA (0..MAX_STIM_MA) -- the same final value
                shown on the dashboard's "DBS Amplitude" KPI. Converted to a
                uint8 (0-255) via `ma_to_uint8` before being sent over BLE.
        """
        if not self.running or self.loop is None:
            logger.warning("BLE host not running, ignoring amplitude update")
            return

        uint8_value = ma_to_uint8(value)
        with self._lock:
            if uint8_value == self._current_uint8:
                return
            self._current_uint8 = uint8_value

        asyncio.run_coroutine_threadsafe(self._async_update(uint8_value), self.loop)

    def stop(self) -> bool:
        """Stop advertising and tear down the BLE GATT server."""
        if not self.running:
            logger.warning("BLE host not running")
            return False

        logger.info("Stopping BLE host...")
        if self.loop is not None:
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread is not None:
            self.thread.join(timeout=5.0)

        self.running = False
        return True


# Global BLE host instance
_ble_host: Optional[BLEDBSHost] = None


def start_ble_host() -> bool:
    """
    Start the BLE peripheral host (begins advertising).

    Returns:
        bool: True if started successfully, False otherwise.
    """
    global _ble_host

    if _ble_host is None:
        _ble_host = BLEDBSHost()

    return _ble_host.start()


def update_amplitude(value: float) -> None:
    """
    Update the DBS stimulation amplitude and notify any subscribed BLE client.

    Args:
        value: DBS amplitude in mA (0.0 to MAX_STIM_MA). Mapped to a uint8
            (0-255) via `ma_to_uint8` -- see that function for the exact scaling.
    """
    global _ble_host

    if _ble_host is None:
        logger.warning("BLE host not initialized")
        return

    _ble_host.update_amplitude(value)


def stop_ble_host() -> bool:
    """
    Stop the BLE peripheral host.

    Returns:
        bool: True if stopped successfully, False otherwise.
    """
    global _ble_host

    if _ble_host is None:
        logger.warning("BLE host not initialized")
        return False

    return _ble_host.stop()


if __name__ == "__main__":
    """
    Demo: Test the BLE host with periodic amplitude updates (mA, matching the
    real dashboard value range).
    """
    import math
    import time

    logger.info("Starting BLE DBS Host demo...")

    if start_ble_host():
        logger.info("BLE host started successfully")
        try:
            for i in range(30):
                # Simulate a varying DBS amplitude in mA (0..MAX_STIM_MA)
                amplitude_ma = (MAX_STIM_MA / 2.0) * (1 + math.sin(i * 0.2))
                logger.info("Demo update %d: amplitude=%.2f mA", i, amplitude_ma)
                update_amplitude(amplitude_ma)
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Demo interrupted by user")
        finally:
            stop_ble_host()
    else:
        logger.error("Failed to start BLE host")

    logger.info("Demo complete")


# Example Streamlit integration (see frontend/session.py `_render_device_connection`
# and frontend/app.py `live_metrics` for the real wiring):
"""
import streamlit as st
from fw.ble_dbs_host import start_ble_host, update_amplitude, stop_ble_host

if st.button("Connect Bluetooth"):
    start_ble_host()

# Each simulation tick, after computing the final DBS amplitude (mA):
update_amplitude(hist["dbs_amplitude_ma"][-1])

if st.button("Stop DBS"):
    stop_ble_host()
"""