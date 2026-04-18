# Python Automotive Testing – Infotainment System
## STAR Format Scenarios (Situation → Task → Action → Result)

---

## Overview

Infotainment systems integrate media, navigation, phone connectivity (Bluetooth/USB/CarPlay/Android Auto), voice recognition, and HMI displays. Testing involves CAN/LIN signals, HMI states, audio routing, and connectivity protocols.

**Python Tools Used:**
- `python-can` — CAN bus communication
- `cantools` — DBC signal decoding
- `pytest` — Test framework
- `pyserial` — Serial/UART communication
- `paramiko` — SSH to Linux-based IVI systems
- `requests` — REST API calls to IVI middleware

---

## STAR Scenario 1 – Audio Volume CAN Signal Validation

### Situation
During integration testing of a Head Unit (HU) on a test bench, the audio volume control was operated via a steering wheel button. Engineers suspected the CAN signal `AudioVolume` in the `HMI_Control` message (0x3A0) was not being transmitted correctly after quick successive presses.

### Task
Write a Python automation script to simulate rapid steering wheel button presses via CAN, capture all transmitted `AudioVolume` signals, and validate that no step is skipped and the range stays within 0–30.

### Action
```python
import can
import cantools
import time
import pytest

db = cantools.database.load_file("infotainment.dbc")
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan')

def send_volume_up(bus, steps=5, interval_ms=100):
    """Simulate rapid volume up button presses."""
    msg_def = db.get_message_by_name('SteeringWheelCtrl')
    for _ in range(steps):
        data = msg_def.encode({'VolUp_Btn': 1, 'VolDown_Btn': 0})
        msg = can.Message(arbitration_id=msg_def.frame_id, data=data, is_extended_id=False)
        bus.send(msg)
        time.sleep(interval_ms / 1000.0)
        # Release button
        data_rel = msg_def.encode({'VolUp_Btn': 0, 'VolDown_Btn': 0})
        msg_rel = can.Message(arbitration_id=msg_def.frame_id, data=data_rel, is_extended_id=False)
        bus.send(msg_rel)
        time.sleep(interval_ms / 1000.0)

def capture_audio_volume(bus, duration_sec=3):
    """Capture AudioVolume signal responses."""
    hmi_id = db.get_message_by_name('HMI_Control').frame_id
    volumes = []
    start = time.time()
    while time.time() - start < duration_sec:
        msg = bus.recv(timeout=0.1)
        if msg and msg.arbitration_id == hmi_id:
            decoded = db.decode_message(msg.arbitration_id, msg.data)
            if 'AudioVolume' in decoded:
                volumes.append(int(decoded['AudioVolume']))
    return volumes

def test_volume_step_and_range():
    initial_vol = 10
    steps = 5
    send_volume_up(bus, steps=steps)
    volumes = capture_audio_volume(bus, duration_sec=2)

    # Validate: no out-of-range values
    for v in volumes:
        assert 0 <= v <= 30, f"Out of range: {v}"

    # Validate: volume incremented step by step (no skips > 1)
    for i in range(1, len(volumes)):
        diff = volumes[i] - volumes[i-1]
        assert diff <= 1, f"Volume skipped step: {volumes[i-1]} → {volumes[i]}"

    print(f"PASS: Captured volumes: {volumes}")

if __name__ == "__main__":
    test_volume_step_and_range()
    bus.shutdown()
```

### Result
- Identified that under 50ms interval presses, 2 steps were skipped intermittently.
- Defect raised: `INF-241 – Volume step loss under rapid input (<50ms)`
- Root cause: HU debounce timer was 80ms but button repeat rate was 50ms
- Fix: Debounce adjusted to 40ms; all 5-step sequences passed with zero skips.

---

## STAR Scenario 2 – Bluetooth Connection State Machine Validation

### Situation
During system-level testing, it was observed that when a phone disconnected from Bluetooth while audio was playing, the HU sometimes stayed in `BT_PLAYING` state instead of transitioning to `BT_DISCONNECTED`, causing the audio source to freeze.

### Task
Automate the BT connection/disconnection lifecycle using CAN signals and validate all state transitions match the expected state machine spec.

### Action
```python
import can
import cantools
import time

db = cantools.database.load_file("infotainment.dbc")
bus = can.interface.Bus(channel='virtual', bustype='virtual')

STATES = {
    0: "BT_IDLE",
    1: "BT_CONNECTING",
    2: "BT_CONNECTED",
    3: "BT_PLAYING",
    4: "BT_DISCONNECTING",
    5: "BT_DISCONNECTED"
}

VALID_TRANSITIONS = {
    "BT_IDLE":          ["BT_CONNECTING"],
    "BT_CONNECTING":    ["BT_CONNECTED", "BT_IDLE"],
    "BT_CONNECTED":     ["BT_PLAYING", "BT_DISCONNECTING"],
    "BT_PLAYING":       ["BT_CONNECTED", "BT_DISCONNECTING"],
    "BT_DISCONNECTING": ["BT_DISCONNECTED"],
    "BT_DISCONNECTED":  ["BT_IDLE"]
}

def monitor_bt_states(bus, duration=10):
    bt_msg_id = db.get_message_by_name('BT_Status').frame_id
    state_history = []
    start = time.time()
    while time.time() - start < duration:
        msg = bus.recv(timeout=0.1)
        if msg and msg.arbitration_id == bt_msg_id:
            decoded = db.decode_message(msg.arbitration_id, msg.data)
            state_id = int(decoded.get('BT_State', -1))
            state_name = STATES.get(state_id, "UNKNOWN")
            if not state_history or state_history[-1] != state_name:
                state_history.append(state_name)
                print(f"  → State: {state_name}")
    return state_history

def validate_transitions(history):
    errors = []
    for i in range(1, len(history)):
        prev = history[i-1]
        curr = history[i]
        allowed = VALID_TRANSITIONS.get(prev, [])
        if curr not in allowed:
            errors.append(f"INVALID: {prev} → {curr} (allowed: {allowed})")
    return errors

def test_bt_state_machine():
    print("Monitoring BT state transitions for 10 seconds...")
    history = monitor_bt_states(bus, duration=10)
    print(f"\nState history: {' → '.join(history)}")
    errors = validate_transitions(history)
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        raise AssertionError(f"{len(errors)} invalid transitions found")
    else:
        print("PASS: All BT state transitions valid")

if __name__ == "__main__":
    test_bt_state_machine()
    bus.shutdown()
```

### Result
- Script captured the invalid transition: `BT_PLAYING → BT_IDLE` (skipped `BT_DISCONNECTING` and `BT_DISCONNECTED`)
- Defect: `INF-318 – BT disconnection bypasses required intermediate states`
- Root cause: Phone removal event handler directly wrote `BT_IDLE` without going through disconnect sequence
- Fix merged in firmware v2.4.1; all 50 automated test cycles passed.

---

## STAR Scenario 3 – HMI Screen Transition Latency Test

### Situation
A performance requirement stated: "HMI must respond to source switch (e.g., Radio → Navigation) within 500ms." During manual testing, occasional 700–900ms delays were noticed under high CAN bus load.

### Task
Automate the screen transition request over CAN, timestamp both the request and the HMI_State confirmation message, and report latency statistics over 100 iterations.

### Action
```python
import can
import cantools
import time
import statistics

db = cantools.database.load_file("infotainment.dbc")
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan')

SOURCE_RADIO = 0x01
SOURCE_NAV   = 0x02
LATENCY_LIMIT_MS = 500

def send_source_switch(bus, source_id):
    msg_def = db.get_message_by_name('HMI_Request')
    data = msg_def.encode({'SourceSelect': source_id})
    msg = can.Message(arbitration_id=msg_def.frame_id, data=data, is_extended_id=False)
    bus.send(msg)
    return time.perf_counter()

def wait_for_hmi_state(bus, expected_source, timeout=2.0):
    hmi_state_id = db.get_message_by_name('HMI_State').frame_id
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        msg = bus.recv(timeout=0.05)
        if msg and msg.arbitration_id == hmi_state_id:
            decoded = db.decode_message(msg.arbitration_id, msg.data)
            if int(decoded.get('ActiveSource', -1)) == expected_source:
                return time.perf_counter()
    return None

def test_screen_transition_latency(iterations=100):
    latencies = []
    failures = []

    for i in range(iterations):
        t_req = send_source_switch(bus, SOURCE_NAV)
        t_resp = wait_for_hmi_state(bus, SOURCE_NAV, timeout=2.0)

        if t_resp is None:
            failures.append(i)
            print(f"  [{i+1}] TIMEOUT – no HMI_State confirmation")
        else:
            latency_ms = (t_resp - t_req) * 1000
            latencies.append(latency_ms)
            status = "PASS" if latency_ms <= LATENCY_LIMIT_MS else "FAIL"
            print(f"  [{i+1}] {status} – {latency_ms:.1f} ms")

        # Switch back
        time.sleep(0.2)
        send_source_switch(bus, SOURCE_RADIO)
        time.sleep(0.5)

    if latencies:
        print(f"\n--- Latency Report ({iterations} iterations) ---")
        print(f"  Min:    {min(latencies):.1f} ms")
        print(f"  Max:    {max(latencies):.1f} ms")
        print(f"  Mean:   {statistics.mean(latencies):.1f} ms")
        print(f"  Median: {statistics.median(latencies):.1f} ms")
        print(f"  StdDev: {statistics.stdev(latencies):.1f} ms")
        violations = [l for l in latencies if l > LATENCY_LIMIT_MS]
        print(f"  Violations (>{LATENCY_LIMIT_MS}ms): {len(violations)}/{len(latencies)}")
        print(f"  Timeouts: {len(failures)}")
        assert len(violations) == 0, f"{len(violations)} latency violations found"

if __name__ == "__main__":
    test_screen_transition_latency(iterations=100)
    bus.shutdown()
```

### Result
- 23 out of 100 iterations exceeded 500ms under simulated high-load condition
- Mean latency: 312ms, Max: 847ms
- Identified: HMI task preemption by CAN receive interrupt under 80%+ bus load
- Defect: `INF-452 – HMI source switch latency degrades under high CAN bus load`
- HMI task priority raised; post-fix: 0 violations over 500 iterations.

---

## STAR Scenario 4 – USB Media Mount / Unmount Reliability

### Situation
Customer complaint: "USB device not recognized after rapid plug/unplug 3 times." QA could not reproduce consistently. The test was done manually — no automation existed.

### Task
Simulate USB plug/unplug events via GPIO relay controller, monitor the CAN `USB_Status` signal, and run 200 rapid cycles to measure the failure rate.

### Action
```python
import can
import cantools
import time
import serial  # USB relay controller on COM port

db = cantools.database.load_file("infotainment.dbc")
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan')
relay = serial.Serial('COM5', 9600, timeout=1)

USB_MOUNTED   = 0x01
USB_UNMOUNTED = 0x00
USB_ERROR     = 0xFF

def relay_on():  relay.write(b'\xA0\x01\x01\xA2')   # plug USB
def relay_off(): relay.write(b'\xA0\x01\x00\xA1')   # unplug USB

def wait_usb_status(bus, expected, timeout=5.0):
    usb_id = db.get_message_by_name('USB_Status').frame_id
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=0.1)
        if msg and msg.arbitration_id == usb_id:
            decoded = db.decode_message(msg.arbitration_id, msg.data)
            status = int(decoded.get('USB_State', -1))
            if status == expected or status == USB_ERROR:
                return status
    return -1  # timeout

def test_usb_mount_cycles(cycles=200):
    results = {"pass": 0, "fail_mount": 0, "fail_unmount": 0, "error": 0}

    for i in range(cycles):
        # Plug
        relay_on()
        status = wait_usb_status(bus, USB_MOUNTED, timeout=5)
        if status == USB_ERROR:
            results["error"] += 1
            print(f"[{i+1}] ERROR during mount")
            relay_off()
            time.sleep(1)
            continue
        elif status != USB_MOUNTED:
            results["fail_mount"] += 1
            print(f"[{i+1}] FAIL: USB did not mount (status={status})")
            relay_off()
            time.sleep(1)
            continue

        time.sleep(0.3)  # rapid cycle — intentionally short

        # Unplug
        relay_off()
        status = wait_usb_status(bus, USB_UNMOUNTED, timeout=3)
        if status != USB_UNMOUNTED:
            results["fail_unmount"] += 1
            print(f"[{i+1}] FAIL: USB did not unmount cleanly")
        else:
            results["pass"] += 1

        time.sleep(0.5)

    print(f"\n--- USB Mount Reliability: {cycles} cycles ---")
    for k, v in results.items():
        print(f"  {k}: {v}")
    failure_rate = (cycles - results["pass"]) / cycles * 100
    print(f"  Failure rate: {failure_rate:.1f}%")
    assert results["pass"] == cycles, f"USB reliability test failed: {failure_rate:.1f}% failure rate"

if __name__ == "__main__":
    test_usb_mount_cycles(200)
    bus.shutdown()
    relay.close()
```

### Result
- Failure rate: 7.5% (15 failures in 200 cycles) under 300ms connect/disconnect interval
- 0% failure rate at >1s intervals
- Root cause: USB enumeration sequence did not properly handle VBUS debounce
- Defect `INF-589` raised; firmware added 500ms VBUS settle time
- Post-fix: 0/500 failures across extended soak test.

---

## Summary Table

| Scenario | Area | Python Approach | Defects Found |
|---|---|---|---|
| 1 – Volume step validation | CAN signal test | `python-can` + `cantools` | Step loss <50ms |
| 2 – BT state machine | State validation | CAN monitoring + transition map | Invalid state skip |
| 3 – HMI latency | Performance | Timestamp + statistics | 23% latency violations |
| 4 – USB reliability | Hardware-in-loop | Serial relay + CAN monitoring | 7.5% mount failure |
