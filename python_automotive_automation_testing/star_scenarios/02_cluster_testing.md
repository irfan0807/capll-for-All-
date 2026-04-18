# Python Automotive Testing – Instrument Cluster
## STAR Format Scenarios (Situation → Task → Action → Result)

---

## Overview

Instrument Cluster (IC) displays speed, RPM, fuel, temperature, odometer, gear, and warning telltales. Testing validates signal accuracy, warning activation thresholds, display latency, and pixel/rendering correctness.

**Python Tools Used:**
- `python-can` + `cantools` — inject CAN signals to cluster
- `pytest` + `pytest-parametrize` — data-driven threshold tests
- `opencv-python` — screen capture image comparison
- `pyserial` — LIN bus commands

---

## STAR Scenario 1 – Speedometer Accuracy Validation

### Situation
The IC receives `VehicleSpeed` signal on CAN message `0x200`. The cluster must display the correct speed within ±2 km/h tolerance across the full range 0–260 km/h. During manual spot-checks, values at 0 km/h, 120 km/h, and 200 km/h were verified — but intermediate and boundary values had never been automated.

### Task
Write a parametrized Python test that injects a range of speed values (0 to 260 in 5 km/h steps), reads back the `DisplaySpeed` signal from the IC CAN response message, and asserts each value is within ±2 km/h tolerance.

### Action
```python
import can
import cantools
import time
import pytest

db = cantools.database.load_file("cluster.dbc")
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan')

SPEED_TOLERANCE_KMH = 2.0
TX_INTERVAL_MS      = 20   # 50 Hz CAN message cycle
SETTLE_TIME_S       = 0.5  # wait for cluster to render

def set_vehicle_speed(bus, speed_kmh):
    msg_def = db.get_message_by_name('VehicleSpeed')
    data = msg_def.encode({'VehicleSpeed': speed_kmh, 'SpeedValid': 1})
    msg = can.Message(arbitration_id=msg_def.frame_id, data=data, is_extended_id=False)
    # Send cyclically for SETTLE_TIME_S to allow cluster to update
    deadline = time.time() + SETTLE_TIME_S
    while time.time() < deadline:
        bus.send(msg)
        time.sleep(TX_INTERVAL_MS / 1000.0)

def read_display_speed(bus, timeout=1.0):
    ic_response_id = db.get_message_by_name('IC_DisplayData').frame_id
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=0.05)
        if msg and msg.arbitration_id == ic_response_id:
            decoded = db.decode_message(msg.arbitration_id, msg.data)
            return float(decoded.get('DisplaySpeed', -1))
    return None

@pytest.mark.parametrize("input_speed", list(range(0, 261, 5)))
def test_speedometer_accuracy(input_speed):
    set_vehicle_speed(bus, input_speed)
    displayed = read_display_speed(bus)
    assert displayed is not None, f"No IC response for speed {input_speed} km/h"
    error = abs(displayed - input_speed)
    assert error <= SPEED_TOLERANCE_KMH, (
        f"Speed {input_speed} km/h: displayed {displayed} km/h, error={error:.1f} > {SPEED_TOLERANCE_KMH}"
    )
    print(f"PASS: input={input_speed} displayed={displayed} error={error:.1f}")
```

### Result
- 53 speed values tested (0 to 260, step 5)
- Failures found at 0 km/h (displayed 2 km/h — residual value from previous frame)
- Failure at 260 km/h (cluster capped at 240, but signal was valid to 260)
- Defect `CLU-101` – Zero-speed residual display issue
- Defect `CLU-102` – Scale max under-specified (240 vs 260 km/h)
- Both fixed in next cluster firmware sprint.

---

## STAR Scenario 2 – Warning Telltale Activation Threshold Test

### Situation
ISO 26262 requires warning telltales to activate within defined signal thresholds: low fuel warning below 10L, engine temp warning above 110°C, oil pressure warning below 1.5 bar. No Python automation existed — all testing was manual with DVM.

### Task
Inject boundary, nominal, and beyond-boundary values for each warning signal and verify telltale activation via the `IC_TelltaleStatus` CAN message.

### Action
```python
import can
import cantools
import time

db = cantools.database.load_file("cluster.dbc")
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan')

# (signal_name, tx_msg_name, telltale_bit_name, threshold, below_triggers)
WARNINGS = [
    ("FuelLevel",   "FuelData",  "LowFuelWarn",   10.0,   True),
    ("EngineTemp",  "EngineData","HighTempWarn",   110.0,  False),
    ("OilPressure", "EngineData","LowOilWarn",     1.5,    True),
]

def send_signal(bus, msg_name, signal_name, value, cycles=25):
    msg_def = db.get_message_by_name(msg_name)
    data = msg_def.encode({signal_name: value})
    msg = can.Message(arbitration_id=msg_def.frame_id, data=data, is_extended_id=False)
    for _ in range(cycles):
        bus.send(msg)
        time.sleep(0.02)

def read_telltale(bus, telltale_name, timeout=2.0):
    ic_id = db.get_message_by_name('IC_TelltaleStatus').frame_id
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=0.05)
        if msg and msg.arbitration_id == ic_id:
            decoded = db.decode_message(msg.arbitration_id, msg.data)
            if telltale_name in decoded:
                return int(decoded[telltale_name])
    return None

def test_warning_thresholds():
    results = []
    for sig, tx_msg, telltale, threshold, below_triggers in WARNINGS:
        # Test cases: just above, at boundary, just below
        test_cases = [
            (threshold - 1,  below_triggers,     "below threshold"),
            (threshold,      below_triggers,     "at threshold"),
            (threshold + 1,  not below_triggers, "above threshold"),
        ]
        for value, expect_on, label in test_cases:
            send_signal(bus, tx_msg, sig, value)
            state = read_telltale(bus, telltale)
            passed = (state == (1 if expect_on else 0))
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] {sig}={value} ({label}) → {telltale}={'ON' if state else 'OFF'} (expected={'ON' if expect_on else 'OFF'})")
            results.append(passed)

    assert all(results), f"Warning threshold failures: {results.count(False)} failed"

if __name__ == "__main__":
    test_warning_thresholds()
    bus.shutdown()
```

### Result
- 9 test points across 3 warnings executed
- Low Fuel warning: activated at exactly 10L ✓
- Engine Temp warning: failed to activate at 110°C — activated only at 112°C (2°C hysteresis not documented)
- Oil Pressure: passed all 3 points ✓
- Defect `CLU-215` raised for temperature hysteresis mismatch; spec updated to require 110–112°C hysteresis band.

---

## STAR Scenario 3 – Odometer Non-Decrement Integrity Test

### Situation
Safety requirement: "Odometer value shall never decrement. If an invalid CAN value is received (lower than stored), the cluster must retain the last valid value." This was not tested in regression — a firmware update broke it once in production.

### Task
Automate injection of a decreasing odometer sequence and verify the IC retains the highest value seen.

### Action
```python
import can
import cantools
import time

db = cantools.database.load_file("cluster.dbc")
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan')

def send_odometer(bus, value_km, cycles=30):
    msg_def = db.get_message_by_name('VehicleOdometer')
    data = msg_def.encode({'Odometer_km': value_km})
    msg = can.Message(arbitration_id=msg_def.frame_id, data=data, is_extended_id=False)
    for _ in range(cycles):
        bus.send(msg)
        time.sleep(0.02)

def read_displayed_odometer(bus, timeout=2.0):
    ic_id = db.get_message_by_name('IC_DisplayData').frame_id
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=0.05)
        if msg and msg.arbitration_id == ic_id:
            decoded = db.decode_message(msg.arbitration_id, msg.data)
            if 'DisplayOdometer' in decoded:
                return float(decoded['DisplayOdometer'])
    return None

def test_odometer_non_decrement():
    odometer_sequence = [12500, 12600, 12700, 12650, 12400, 12800, 12500]
    peak = 0
    results = []

    for km in odometer_sequence:
        send_odometer(bus, km)
        displayed = read_displayed_odometer(bus)
        peak = max(peak, km)
        expected = peak  # IC should never go below peak

        passed = (displayed is not None) and (displayed >= expected - 1)
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] sent={km} peak={peak} displayed={displayed}")
        results.append(passed)

    assert all(results), f"Odometer non-decrement violated: {results.count(False)} failures"

if __name__ == "__main__":
    test_odometer_non_decrement()
    bus.shutdown()
```

### Result
- Test passed for regular increments
- Correctly identified: cluster decremented odometer to 12,500 after receiving 12,500 following a peak of 12,800
- Defect `CLU-334` – Odometer NVM write not triggered correctly; value read from CAN instead of NVM on re-init
- Fix: IC always uses MAX(CAN_value, NVM_stored) on every update cycle.

---

## STAR Scenario 4 – Gear Display Validation (Automatic Transmission)

### Situation
Gear display must show P/R/N/D/1/2/3/4/5/6 correctly. During TCU integration, the cluster showed "D" when the actual gear was "R" after a quick D→N→R transition.

### Task
Inject rapid gear change sequences, capture the displayed gear from IC CAN, and validate correctness using a timing analysis.

### Action
```python
import can
import cantools
import time

db = cantools.database.load_file("cluster.dbc")
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan')

GEAR_MAP = {0: 'P', 1: 'R', 2: 'N', 3: 'D', 4: '1', 5: '2', 6: '3', 7: '4'}

def set_gear(bus, gear_id, cycles=10):
    msg_def = db.get_message_by_name('TransmissionData')
    data = msg_def.encode({'GearPosition': gear_id, 'GearValid': 1})
    msg = can.Message(arbitration_id=msg_def.frame_id, data=data, is_extended_id=False)
    for _ in range(cycles):
        bus.send(msg)
        time.sleep(0.01)

def read_display_gear(bus, timeout=1.0):
    ic_id = db.get_message_by_name('IC_DisplayData').frame_id
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=0.05)
        if msg and msg.arbitration_id == ic_id:
            decoded = db.decode_message(msg.arbitration_id, msg.data)
            if 'DisplayGear' in decoded:
                return int(decoded['DisplayGear'])
    return None

def test_gear_rapid_transition():
    # Simulate D → N → R rapid transition
    transitions = [(3, 'D'), (2, 'N'), (1, 'R')]
    failures = []

    for gear_id, expected_label in transitions:
        set_gear(bus, gear_id)
        displayed_id = read_display_gear(bus)
        displayed_label = GEAR_MAP.get(displayed_id, "?")
        if displayed_label != expected_label:
            failures.append(f"Expected {expected_label}, got {displayed_label}")
            print(f"  FAIL: set={expected_label} displayed={displayed_label}")
        else:
            print(f"  PASS: Gear {expected_label} correctly displayed")

    assert not failures, "Gear display failures:\n" + "\n".join(failures)

if __name__ == "__main__":
    test_gear_rapid_transition()
    bus.shutdown()
```

### Result
- Caught: after D→N→R in 10ms intervals, cluster displayed "N" during "R" phase
- Root cause: IC gear display task ran at 50ms cycle, missed the short-lived N→R transition
- Defect `CLU-441` – Gear display task rate too slow for rapid TCU transitions
- Fix: IC gear update rate increased from 50ms to 20ms; test passed 100% in 200 consecutive rapid cycles.

---

## Summary Table

| Scenario | Area | Python Approach | Defects Found |
|---|---|---|---|
| 1 – Speedometer accuracy | Signal validation | Parametrized 53-point sweep | 2 boundary defects |
| 2 – Warning telltales | Threshold testing | CAN injection + telltale readback | Temp hysteresis gap |
| 3 – Odometer integrity | Safety requirement | Decreasing sequence injection | NVM vs CAN priority bug |
| 4 – Gear display | Real-time display | Rapid sequence injection | 50ms render lag |
