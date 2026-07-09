/*
 * Arduino Nano ESP32 - BLE DBS Receiver Client Sketch
 *
 * Acts as a BLE client/central that scans for and connects to the Python BLE
 * host (a GATT server / peripheral running on the laptop, see fw/ble_dbs_host.py).
 * Receives stimulation intensity values (0-255) via BLE notifications.
 * Controls an external LED brightness via PWM based on received values.
 *
 * Library note: ArduinoBLE targets boards with a u-blox NINA-B3 / Nordic
 * nRF52840 radio (Nano 33 BLE, Portenta, MKR WiFi 1010) -- it does NOT support
 * the ESP32-S3 radio used by the Nano ESP32, so it cannot compile/run correctly
 * here. The Nano ESP32's "Arduino ESP32 Boards" package bundles the ESP32
 * Arduino BLE library (BLEDevice / BLEClient / BLEScan, from
 * espressif/arduino-esp32), which is the correct choice for this board and
 * needs no extra installation.
 *
 * Wiring:
 * - LED cathode (shorter leg) to GND
 * - LED anode (longer leg) to a 220-470 ohm resistor
 * - Resistor other end to GPIO pin D2 (PWM-capable pin on Nano ESP32)
 */

#include <BLEDevice.h>
#include <BLEClient.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

// BLE Service and Characteristic UUIDs (must match fw/ble_dbs_host.py exactly).
// Real random 128-bit UUIDs -- NOT SIG-adopted placeholder UUIDs.
#define BLE_SERVICE_UUID "30f38274-4fee-49d5-9dda-c671f21497b2"
#define BLE_CHARACTERISTIC_UUID "8ed6f47d-f7ef-4220-beea-26075caa24fc"

// LED Configuration
#define LED_PIN D2                // PWM-capable pin on Nano ESP32
#define LED_MAX_BRIGHTNESS 255     // Maximum PWM value (8-bit, matches analogWrite default)

// Heartbeat / status print interval (non-blocking)
#define STATUS_LOG_INTERVAL_MS 5000

static const BLEUUID serviceUUID(BLE_SERVICE_UUID);
static const BLEUUID charUUID(BLE_CHARACTERISTIC_UUID);

// Global BLE state
static BLEClient* pClient = nullptr;
static BLERemoteCharacteristic* pRemoteCharacteristic = nullptr;
static BLEAdvertisedDevice* targetDevice = nullptr;

static volatile bool doConnect = false;
static volatile bool connectedToHost = false;
static bool scanningActive = false;
static uint8_t lastIntensityValue = 0;
static unsigned long lastStatusLogMs = 0;

// Function Prototypes
void startScanning();
void stopScanning();
bool connectToServer();
void updateLEDBrightness(uint8_t intensity);
void logDebug(const String& message);
void logDebugInt(const String& message, int value);
static void notifyCallback(BLERemoteCharacteristic* characteristic, uint8_t* data, size_t length, bool isNotify);

/*
 * BLEAdvertisedDeviceCallbacks - invoked by the BLE stack (from its own scan
 * task) whenever an advertisement is seen. Runs asynchronously / non-blocking
 * with respect to loop().
 */
class AdvertisedDeviceCallbacks : public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice advertisedDevice) override {
    if (!advertisedDevice.haveServiceUUID() || !advertisedDevice.isAdvertisingService(serviceUUID)) {
      return;
    }

    logDebug("Target peripheral found: " + String(advertisedDevice.getAddress().toString().c_str()));
    BLEDevice::getScan()->stop();
    scanningActive = false;

    if (targetDevice != nullptr) {
      delete targetDevice;
    }
    targetDevice = new BLEAdvertisedDevice(advertisedDevice);
    doConnect = true;
  }
};

/*
 * ClientCallbacks - tracks connect/disconnect at the BLE link layer so the LED
 * can be forced off immediately on disconnect and scanning can resume.
 */
class ClientCallbacks : public BLEClientCallbacks {
  void onConnect(BLEClient* client) override {
    logDebug("Link connected");
  }

  void onDisconnect(BLEClient* client) override {
    logDebug("Disconnected from BLE DBS Host");
    connectedToHost = false;
    lastIntensityValue = 0;
    updateLEDBrightness(0);
    startScanning();
  }
};

/*
 * setup() - Initialize serial, LED PWM, and start BLE scanning
 */
void setup() {
  Serial.begin(115200);
  delay(2000);  // Wait for Serial to be ready

  logDebug("========================================");
  logDebug("Arduino Nano ESP32 - BLE DBS Receiver");
  logDebug("========================================");
  logDebug("Boot");

  // Configure LED pin (default analogWrite is 8-bit / 0-255 on Nano ESP32)
  pinMode(LED_PIN, OUTPUT);
  updateLEDBrightness(0);  // LED off on boot
  logDebugInt("LED pin configured on", LED_PIN);

  BLEDevice::init("DBS-Receiver");

  BLEScan* pBLEScan = BLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new AdvertisedDeviceCallbacks());
  pBLEScan->setInterval(1349);
  pBLEScan->setWindow(449);
  pBLEScan->setActiveScan(true);

  logDebug("Setup complete. Waiting for Python BLE host to advertise...");
  startScanning();
}

/*
 * loop() - Main event loop. Non-blocking: BLE scanning/connections run on the
 * BLE stack's own tasks, this loop only reacts to flags and prints periodic
 * status without ever calling delay().
 */
void loop() {
  if (doConnect) {
    doConnect = false;
    if (connectToServer()) {
      logDebug("Connected to BLE DBS Host and subscribed to notifications");
    } else {
      logDebug("Connection attempt failed, will rescan");
      connectedToHost = false;
      updateLEDBrightness(0);
      startScanning();
    }
  }

  if (!connectedToHost && !scanningActive) {
    startScanning();
  }

  unsigned long now = millis();
  if (now - lastStatusLogMs >= STATUS_LOG_INTERVAL_MS) {
    lastStatusLogMs = now;
    if (connectedToHost) {
      logDebugInt("Connected. Last intensity value:", lastIntensityValue);
    } else {
      logDebug("Scanning for BLE DBS Host...");
    }
  }
}

/*
 * startScanning() - Start BLE scan for the DBS host service (non-blocking;
 * duration 0 means scan indefinitely until stop() is called).
 */
void startScanning() {
  if (scanningActive) {
    return;
  }
  scanningActive = true;
  logDebug("Starting BLE scan for DBS Host service " + String(BLE_SERVICE_UUID));
  BLEDevice::getScan()->start(0, false);
}

/*
 * stopScanning() - Stop the active BLE scan
 */
void stopScanning() {
  if (scanningActive) {
    BLEDevice::getScan()->stop();
    scanningActive = false;
    logDebug("BLE scan stopped");
  }
}

/*
 * connectToServer() - Connect to the discovered peripheral, discover the
 * service/characteristic, and subscribe to notifications.
 */
bool connectToServer() {
  logDebug("Connecting to " + String(targetDevice->getAddress().toString().c_str()));

  if (pClient == nullptr) {
    pClient = BLEDevice::createClient();
    pClient->setClientCallbacks(new ClientCallbacks());
  }

  if (!pClient->connect(targetDevice)) {
    logDebug("ERROR: Failed to connect to device");
    return false;
  }

  BLERemoteService* pRemoteService = pClient->getService(serviceUUID);
  if (pRemoteService == nullptr) {
    logDebug("ERROR: Failed to find service UUID on peripheral");
    pClient->disconnect();
    return false;
  }
  logDebug("Service discovered!");

  pRemoteCharacteristic = pRemoteService->getCharacteristic(charUUID);
  if (pRemoteCharacteristic == nullptr) {
    logDebug("ERROR: Failed to find characteristic UUID on peripheral");
    pClient->disconnect();
    return false;
  }
  logDebug("Characteristic discovered!");

  if (pRemoteCharacteristic->canRead()) {
    std::string value = pRemoteCharacteristic->readValue();
    if (value.length() > 0) {
      updateLEDBrightness(static_cast<uint8_t>(value[0]));
    }
  }

  if (!pRemoteCharacteristic->canNotify()) {
    logDebug("ERROR: Characteristic does not support notifications");
    pClient->disconnect();
    return false;
  }

  pRemoteCharacteristic->registerForNotify(notifyCallback);
  logDebug("Subscribed to intensity notifications!");

  connectedToHost = true;
  return true;
}

/*
 * notifyCallback() - Invoked by the BLE stack when a notification is received.
 * Extracts the single-byte intensity value and updates LED brightness.
 */
static void notifyCallback(BLERemoteCharacteristic* characteristic, uint8_t* data, size_t length, bool isNotify) {
  if (length < 1) {
    logDebug("ERROR: Notification received but value length < 1");
    return;
  }

  uint8_t intensityValue = constrain(data[0], 0, LED_MAX_BRIGHTNESS);

  if (intensityValue != lastIntensityValue) {
    lastIntensityValue = intensityValue;
    updateLEDBrightness(intensityValue);
    logDebugInt("Notification received - Intensity updated to:", intensityValue);
  }
}

/*
 * updateLEDBrightness() - Set LED brightness via PWM.
 * Only allows LED on while actively connected; ensures LED is off when disconnected.
 */
void updateLEDBrightness(uint8_t intensity) {
  if (!connectedToHost && intensity > 0) {
    intensity = 0;
  }
  intensity = constrain(intensity, 0, LED_MAX_BRIGHTNESS);
  analogWrite(LED_PIN, intensity);
  logDebugInt("PWM updated to:", intensity);
}

/*
 * logDebug() - Print debug message with timestamp
 */
void logDebug(const String& message) {
  Serial.print("[");
  Serial.print(millis());
  Serial.print("ms] ");
  Serial.println(message);
}

/*
 * logDebugInt() - Print debug message with integer value
 */
void logDebugInt(const String& message, int value) {
  Serial.print("[");
  Serial.print(millis());
  Serial.print("ms] ");
  Serial.print(message);
  Serial.print(": ");
  Serial.println(value);
}