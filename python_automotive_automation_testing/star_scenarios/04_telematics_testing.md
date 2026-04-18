# Python Automotive Testing – Telematics Systems
## STAR Format Scenarios (Situation → Task → Action → Result)

---

## Overview

Telematics ECUs handle vehicle-to-cloud (V2C) communication: GPS tracking, remote diagnostics, OTA updates, eCall/bCall emergency services, and fleet management data. Testing covers CAN signal capture, MQTT/HTTP data transmission, GPS accuracy, and emergency service activation.

**Python Tools Used:**
- `python-can` + `cantools` — CAN signal extraction
- `paho-mqtt` — MQTT broker communication
- `requests` + `httpx` — REST API validation
- `pynmea2` — NMEA GPS message parsing
- `pytest` + `pytest-asyncio` — Async test execution

---

## STAR Scenario 1 – GPS Position Data Validation in Telematics Uplink

### Situation
A fleet management system receives vehicle GPS coordinates via MQTT every 10 seconds. During a field trial, several vehicles showed GPS coordinates "frozen" at the same position for 2–3 minutes even while moving. The telematics ECU was suspected of caching and re-sending stale GPS data.

### Task
Automate a test that reads GPS NMEA sentences from the telematics ECU serial port, correlates with the GPS coordinates published to the MQTT broker, and detects stale/repeated coordinates over a 5-minute window.

### Action
```python
import serial
import pynmea2
import paho.mqtt.client as mqtt
import json
import time
import threading

# ----- GPS Serial Reader -----
gps_readings = []

def read_gps_serial(port='COM3', baud=9600, duration=300):
    ser = serial.Serial(port, baud, timeout=1)
    deadline = time.time() + duration
    while time.time() < deadline:
        line = ser.readline().decode('ascii', errors='replace').strip()
        try:
            msg = pynmea2.parse(line)
            if hasattr(msg, 'latitude') and msg.latitude:
                gps_readings.append({
                    'ts':  time.time(),
                    'lat': msg.latitude,
                    'lon': msg.longitude,
                    'spd': getattr(msg, 'spd_over_grnd', 0)
                })
        except pynmea2.ParseError:
            pass
    ser.close()

# ----- MQTT Subscriber -----
mqtt_payloads = []

def on_mqtt_message(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode())
        payload['rx_ts'] = time.time()
        mqtt_payloads.append(payload)
    except Exception:
        pass

def subscribe_mqtt(broker='192.168.1.100', topic='vehicle/+/gps', duration=300):
    client = mqtt.Client()
    client.on_message = on_mqtt_message
    client.connect(broker, 1883, 60)
    client.subscribe(topic)
    client.loop_start()
    time.sleep(duration)
    client.loop_stop()

# ----- Test -----
def test_gps_no_stale_data():
    # Run GPS serial reader and MQTT subscriber in parallel
    gps_thread  = threading.Thread(target=read_gps_serial, args=('COM3', 9600, 300))
    mqtt_thread = threading.Thread(target=subscribe_mqtt, daemon=True)
    gps_thread.start()
    mqtt_thread.start()
    gps_thread.join()

    assert mqtt_payloads, "No MQTT GPS messages received"
    assert gps_readings,  "No GPS serial readings captured"

    # Check MQTT update interval (must be <= 15 seconds between messages)
    intervals = [mqtt_payloads[i]['rx_ts'] - mqtt_payloads[i-1]['rx_ts']
                 for i in range(1, len(mqtt_payloads))]
    max_gap = max(intervals)
    print(f"Max MQTT gap: {max_gap:.1f}s (limit: 15s)")
    assert max_gap <= 15.0, f"MQTT GPS message gap of {max_gap:.1f}s exceeds 15s"

    # Check for frozen coordinates (same lat/lon for >30s)
    frozen_count = 0
    for i in range(1, len(mqtt_payloads)):
        same_pos = (
            mqtt_payloads[i]['lat'] == mqtt_payloads[i-1]['lat'] and
            mqtt_payloads[i]['lon'] == mqtt_payloads[i-1]['lon']
        )
        time_gap = mqtt_payloads[i]['rx_ts'] - mqtt_payloads[i-1]['rx_ts']
        if same_pos and time_gap > 30.0:
            frozen_count += 1
            print(f"  FROZEN POSITION at {mqtt_payloads[i]['lat']},{mqtt_payloads[i]['lon']} for {time_gap:.0f}s")

    assert frozen_count == 0, f"Detected {frozen_count} frozen GPS positions"
    print(f"PASS: {len(mqtt_payloads)} MQTT messages, 0 frozen positions")

if __name__ == "__main__":
    test_gps_no_stale_data()
```

### Result
- 6 frozen GPS events detected in 5-minute window (each ~2 minutes duration)
- Root cause: GPS module entered power-save mode on poor signal; telematics ECU retransmitted last valid fix
- Defect `TEL-143` – Telematics must mark position as STALE and suppress MQTT publish if GPS age > 30s
- Fix implemented; 0 frozen coordinates in 24-hour soak test.

---

## STAR Scenario 2 – eCall Trigger and Response Validation

### Situation
Emergency call (eCall, EN 15722) must auto-trigger within 1 second of detecting airbag deployment via CAN, establish a GSM call, and transmit a Minimum Set of Data (MSD) packet. The system had never been tested end-to-end in automation — only manual lab tests every release.

### Task
Simulate airbag deployment CAN signal, verify eCall state machine transitions via CAN, and check that the MSD data payload is correctly formatted (position, timestamp, vehicle ID).

### Action
```python
import can
import cantools
import time
import json

db  = cantools.database.load_file("telematics.dbc")
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan')

ECALL_TRIGGER_LATENCY_S = 1.0

ECALL_STATES = {
    0: "IDLE", 1: "TRIGGERED", 2: "CALLING",
    3: "CONNECTED", 4: "MSD_SENT", 5: "COMPLETE"
}

def inject_airbag_deployment(bus, cycles=10):
    msg_def = db.get_message_by_name('Airbag_Status')
    data = msg_def.encode({'FrontalAirbagDeployed': 1, 'ImpactDetected': 1})
    msg = can.Message(arbitration_id=msg_def.frame_id, data=data, is_extended_id=False)
    for _ in range(cycles):
        bus.send(msg)
        time.sleep(0.01)

def monitor_ecall_states(bus, duration=15.0):
    ecall_id = db.get_message_by_name('eCall_Status').frame_id
    history  = []
    start    = time.time()
    while time.time() - start < duration:
        msg = bus.recv(timeout=0.05)
        if msg and msg.arbitration_id == ecall_id:
            decoded = db.decode_message(msg.arbitration_id, msg.data)
            state   = int(decoded.get('eCall_State', 0))
            name    = ECALL_STATES.get(state, "UNKNOWN")
            if not history or history[-1]['state'] != name:
                history.append({'state': name, 'ts': time.time() - start})
                print(f"  t={time.time()-start:.2f}s → eCall state: {name}")
    return history

def validate_msd_via_rest(vin, timeout=30):
    """Check backend API for MSD receipt (simulated)."""
    import requests
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"http://ecall-server/api/msd/{vin}", timeout=5)
        if resp.status_code == 200:
            msd = resp.json()
            return msd
        time.sleep(2)
    return None

def test_ecall_trigger_and_msd():
    t_deploy = time.time()
    inject_airbag_deployment(bus)
    history = monitor_ecall_states(bus, duration=20.0)

    # Check TRIGGERED within 1s of airbag injection
    triggered = [h for h in history if h['state'] == 'TRIGGERED']
    assert triggered, "eCall never reached TRIGGERED state"
    assert triggered[0]['ts'] <= ECALL_TRIGGER_LATENCY_S, (
        f"eCall trigger latency {triggered[0]['ts']:.2f}s exceeds 1s limit"
    )

    # Check full sequence reached MSD_SENT
    states_reached = [h['state'] for h in history]
    assert 'MSD_SENT' in states_reached, "eCall never reached MSD_SENT state"

    # Validate MSD content
    msd = validate_msd_via_rest(vin="WDB1234567890", timeout=30)
    assert msd is not None, "No MSD received at backend within 30s"
    assert 'latitude'  in msd, "MSD missing latitude"
    assert 'longitude' in msd, "MSD missing longitude"
    assert 'timestamp' in msd, "MSD missing timestamp"
    print(f"PASS: eCall triggered in {triggered[0]['ts']:.2f}s, MSD received at backend")

if __name__ == "__main__":
    test_ecall_trigger_and_msd()
    bus.shutdown()
```

### Result
- eCall triggered in 0.34s (well within 1s limit) ✓
- State machine correctly traversed: IDLE→TRIGGERED→CALLING→CONNECTED→MSD_SENT ✓
- MSD payload missing `vehicleCategory` field — spec requires it per EN 15722
- Defect `TEL-289` – MSD missing vehicleCategory field
- Fix in telematics firmware; passed in next release regression.

---

## STAR Scenario 3 – OTA Update Package Integrity Verification

### Situation
During a remote OTA software update, two vehicles in a pilot program installed a corrupted firmware image due to a network interruption mid-download. The telematics ECU was supposed to validate CRC before applying. It did not abort — it applied the corrupted firmware.

### Task
Automate an OTA test that: sends a valid package, sends a corrupted package (modified last byte), and verifies the ECU accepts the valid one and rejects the corrupted one via HTTP API response and CAN status signal.

### Action
```python
import requests
import hashlib
import can
import cantools
import time

db  = cantools.database.load_file("telematics.dbc")
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan')

OTA_SERVER = "http://192.168.1.50/ota"

def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def send_ota_package(package_bytes: bytes, corrupt=False):
    payload = bytearray(package_bytes)
    if corrupt:
        payload[-1] ^= 0xFF   # flip last byte to corrupt CRC
    checksum = compute_sha256(bytes(payload))
    if corrupt:
        checksum = "deadbeef" * 8   # wrong checksum
    resp = requests.post(
        f"{OTA_SERVER}/upload",
        files={"firmware": bytes(payload)},
        data={"sha256": checksum},
        timeout=30
    )
    return resp

def read_ota_status(bus, timeout=60.0):
    ota_id = db.get_message_by_name('OTA_Status').frame_id
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=0.1)
        if msg and msg.arbitration_id == ota_id:
            decoded = db.decode_message(msg.arbitration_id, msg.data)
            return {
                'state':  int(decoded.get('OTA_State', 0)),
                'result': int(decoded.get('OTA_Result', 0))
            }
    return None

def test_ota_valid_package():
    firmware = open("firmware_v2.5.bin", "rb").read()
    resp = send_ota_package(firmware, corrupt=False)
    assert resp.status_code == 200, f"OTA upload rejected: {resp.text}"
    status = read_ota_status(bus, timeout=60)
    assert status and status['result'] == 1, "OTA valid package not applied successfully"
    print("PASS: Valid OTA package accepted and applied")

def test_ota_corrupt_package():
    firmware = open("firmware_v2.5.bin", "rb").read()
    resp = send_ota_package(firmware, corrupt=True)
    # Server may reject immediately or ECU may reject after validation
    if resp.status_code == 400:
        print("PASS: Server rejected corrupted package immediately")
        return
    status = read_ota_status(bus, timeout=30)
    assert status and status['result'] == 0, "ECU accepted corrupted OTA package — CRITICAL DEFECT"
    print("PASS: ECU correctly rejected corrupted OTA package")

if __name__ == "__main__":
    test_ota_valid_package()
    test_ota_corrupt_package()
    bus.shutdown()
```

### Result
- Valid OTA accepted and applied ✓
- Corrupted OTA: server returned 200 (did not validate SHA256) → ECU applied corrupted firmware
- Critical defect `TEL-401` – OTA server accepts payload without validating SHA256
- Hotfix deployed to OTA server with mandatory SHA256 verification
- Second run: corrupted package rejected with HTTP 400 ✓

---

## Summary Table

| Scenario | Area | Python Approach | Defects Found |
|---|---|---|---|
| 1 – GPS stale detection | V2C / MQTT | Serial NMEA + MQTT subscriber | GPS power-save stale data |
| 2 – eCall trigger | Emergency systems | CAN injection + REST MSD validation | Missing MSD field |
| 3 – OTA integrity | Cybersecurity | HTTP upload + CAN status | Server missing SHA256 check |
