# Python Automotive Testing – ADAS Systems
## STAR Format Scenarios (Situation → Task → Action → Result)

---

## Overview

Advanced Driver Assistance Systems (ADAS) include Forward Collision Warning (FCW), Automatic Emergency Braking (AEB), Lane Departure Warning (LDW), Blind Spot Detection (BSD), and Adaptive Cruise Control (ACC). Testing validates sensor fusion logic, activation thresholds, timing, and fail-safe behaviors.

**Python Tools Used:**
- `python-can` + `cantools` — CAN signal injection/monitoring
- `pytest` — Test framework
- `numpy` — Physics calculations (TTC, deceleration)
- `matplotlib` — Visualize test results
- `dSPACE AutomationDesk Python API` — HIL bench control

---

## STAR Scenario 1 – Forward Collision Warning (FCW) Time-to-Collision Threshold

### Situation
The FCW system must issue a warning when Time-to-Collision (TTC) drops below 2.5 seconds. The TTC is computed from relative speed and distance signals received on CAN from the radar ECU. During calibration reviews, engineers questioned whether the software threshold was exactly 2.5s or had tolerance drift.

### Task
Inject radar object signals (distance + relative speed) to synthesize exact TTC values (3.0s, 2.6s, 2.5s, 2.4s, 2.0s) and verify the FCW warning activates only at and below 2.5s.

### Action
```python
import can
import cantools
import time
import numpy as np

db  = cantools.database.load_file("adas.dbc")
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan')

TTC_THRESHOLD_S = 2.5
TX_CYCLES       = 25   # ~500ms at 20ms cycle

def ttc_to_signals(ttc_s, ego_speed_kmh=100.0):
    """Convert desired TTC to radar distance + relative speed."""
    ego_ms  = ego_speed_kmh / 3.6
    rel_spd = ego_ms          # assume target stationary
    dist_m  = rel_spd * ttc_s
    return round(dist_m, 2), round(rel_spd, 2)

def inject_radar_object(bus, distance_m, rel_speed_ms, cycles=TX_CYCLES):
    msg_def = db.get_message_by_name('Radar_Object1')
    data = msg_def.encode({
        'Obj_Distance':    distance_m,
        'Obj_RelSpeed':    rel_speed_ms,
        'Obj_Valid':       1,
        'Obj_MeasState':   1
    })
    msg = can.Message(arbitration_id=msg_def.frame_id, data=data, is_extended_id=False)
    for _ in range(cycles):
        bus.send(msg)
        time.sleep(0.02)

def read_fcw_status(bus, timeout=1.0):
    fcw_id = db.get_message_by_name('FCW_Status').frame_id
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=0.05)
        if msg and msg.arbitration_id == fcw_id:
            decoded = db.decode_message(msg.arbitration_id, msg.data)
            return int(decoded.get('FCW_Warning', 0))
    return 0

def test_fcw_ttc_threshold():
    test_cases = [
        (3.0,  False, "Above threshold"),
        (2.6,  False, "Just above"),
        (2.5,  True,  "At exact threshold"),
        (2.4,  True,  "Just below"),
        (1.5,  True,  "Well below"),
    ]
    failures = []
    for ttc, expect_warn, label in test_cases:
        dist, rel_spd = ttc_to_signals(ttc)
        inject_radar_object(bus, dist, rel_spd)
        warned = bool(read_fcw_status(bus))
        passed = warned == expect_warn
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] TTC={ttc}s ({label}) dist={dist}m relSpd={rel_spd}m/s warn={'ON' if warned else 'OFF'}")
        if not passed:
            failures.append(f"TTC={ttc}s: expected warn={expect_warn}, got {warned}")
    assert not failures, "\n".join(failures)

if __name__ == "__main__":
    test_fcw_ttc_threshold()
    bus.shutdown()
```

### Result
- FCW activated at TTC = 2.5s ✓
- Unexpectedly, FCW also activated at TTC = 2.6s in 4 out of 10 runs
- Root cause: radar object distance signal has ±0.5m resolution → effective TTC uncertainty ±0.1s
- Defect `ADAS-112` raised; sensor spec reviewed — acceptable per ISO 22179 classification
- Test tolerance adjusted to TTC_THRESHOLD ± 0.1s in test spec.

---

## STAR Scenario 2 – AEB Activation and Deceleration Verification

### Situation
The AEB system must trigger autonomous braking within 300ms of TTC crossing 1.2s, applying minimum 0.3g deceleration. A regression test suite existed in CANoe but could not run headlessly in CI. Python was chosen to replicate this test for the CI pipeline.

### Task
Inject a closing-target scenario (TTC ramping down from 3.0s to 0.8s), measure AEB trigger latency, and verify the deceleration request signal value on CAN matches ≥0.3g.

### Action
```python
import can
import cantools
import time

db  = cantools.database.load_file("adas.dbc")
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan')

AEB_TTC_THRESHOLD_S   = 1.2
MAX_TRIGGER_LATENCY_S = 0.300
MIN_DECEL_G           = 0.3

def ramp_radar_closing(bus, start_dist=120.0, rel_spd_ms=30.0, step_m=2.0, interval_s=0.02):
    """Gradually decrease distance to simulate a closing target."""
    aeb_id    = db.get_message_by_name('AEB_Control').frame_id
    radar_def = db.get_message_by_name('Radar_Object1')
    dist = start_dist
    t_threshold_crossed = None
    t_aeb_triggered     = None
    decel_value         = None

    while dist > 0:
        ttc = dist / rel_spd_ms
        data = radar_def.encode({'Obj_Distance': dist, 'Obj_RelSpeed': rel_spd_ms, 'Obj_Valid': 1})
        bus.send(can.Message(arbitration_id=radar_def.frame_id, data=data, is_extended_id=False))

        if ttc <= AEB_TTC_THRESHOLD_S and t_threshold_crossed is None:
            t_threshold_crossed = time.perf_counter()

        # Check AEB response
        msg = bus.recv(timeout=0.005)
        if msg and msg.arbitration_id == aeb_id and t_threshold_crossed is not None:
            decoded = db.decode_message(msg.arbitration_id, msg.data)
            if int(decoded.get('AEB_Active', 0)) == 1 and t_aeb_triggered is None:
                t_aeb_triggered = time.perf_counter()
                decel_value = float(decoded.get('AEB_DecelReq_g', 0))
                break

        dist -= step_m
        time.sleep(interval_s)

    return t_threshold_crossed, t_aeb_triggered, decel_value

def test_aeb_activation():
    t_cross, t_trigger, decel = ramp_radar_closing(bus)

    assert t_cross   is not None, "TTC threshold was never crossed (check radar injection)"
    assert t_trigger is not None, "AEB never activated during scenario"

    latency = t_trigger - t_cross
    print(f"AEB trigger latency: {latency*1000:.1f} ms (limit: {MAX_TRIGGER_LATENCY_S*1000:.0f} ms)")
    print(f"AEB decel request:   {decel:.3f} g (min: {MIN_DECEL_G} g)")

    assert latency <= MAX_TRIGGER_LATENCY_S, f"AEB latency {latency*1000:.1f}ms exceeds 300ms"
    assert decel   >= MIN_DECEL_G,           f"AEB decel {decel:.3f}g below 0.3g requirement"
    print("PASS: AEB activated within spec")

if __name__ == "__main__":
    test_aeb_activation()
    bus.shutdown()
```

### Result
- AEB trigger latency measured: 187ms (within 300ms limit) ✓
- Deceleration request: 0.45g (above 0.3g minimum) ✓
- Test integrated into GitLab CI nightly pipeline
- 3 pipeline runs with regression confirmed; 0 failures over 50 iterations.

---

## STAR Scenario 3 – Lane Departure Warning Inhibit Conditions

### Situation
LDW must be **inhibited** (not warn) when: (a) turn signal is active, (b) vehicle speed < 60 km/h, or (c) wipers are at HIGH speed. During testing it was found that condition (c) was not implemented — LDW still warned during rain.

### Task
Automate all three inhibit conditions via CAN, verify LDW warning is suppressed in each case, and activate in the nominal case (no inhibit, lane crossing detected).

### Action
```python
import can
import cantools
import time

db  = cantools.database.load_file("adas.dbc")
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan')

def send_lane_departure(bus, cycles=20):
    msg_def = db.get_message_by_name('LaneInfo')
    data = msg_def.encode({'LaneDepartureDetected': 1, 'LKA_Override': 0})
    msg = can.Message(arbitration_id=msg_def.frame_id, data=data, is_extended_id=False)
    for _ in range(cycles):
        bus.send(msg)
        time.sleep(0.02)

def set_inhibit_conditions(bus, turn_signal=0, speed_kmh=100, wiper_high=0):
    # Turn signal
    ts_def = db.get_message_by_name('BCM_Signals')
    bus.send(can.Message(
        arbitration_id=ts_def.frame_id,
        data=ts_def.encode({'TurnSignalLeft': turn_signal, 'WiperHighSpeed': wiper_high}),
        is_extended_id=False
    ))
    # Speed
    sp_def = db.get_message_by_name('VehicleSpeed')
    bus.send(can.Message(
        arbitration_id=sp_def.frame_id,
        data=sp_def.encode({'VehicleSpeed': speed_kmh}),
        is_extended_id=False
    ))
    time.sleep(0.1)

def read_ldw_warning(bus, timeout=1.0):
    ldw_id = db.get_message_by_name('LDW_Status').frame_id
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=0.05)
        if msg and msg.arbitration_id == ldw_id:
            decoded = db.decode_message(msg.arbitration_id, msg.data)
            return int(decoded.get('LDW_Warning', 0))
    return 0

def test_ldw_inhibit_conditions():
    test_cases = [
        # (label,              turn, speed, wiper, expect_warn)
        ("Nominal - warn",     0,    80,    0,     True),
        ("Turn signal active", 1,    80,    0,     False),
        ("Speed < 60 km/h",    0,    50,    0,     False),
        ("Wiper HIGH speed",   0,    80,    1,     False),
        ("All inhibits ON",    1,    40,    1,     False),
    ]
    failures = []
    for label, turn, speed, wiper, expect in test_cases:
        set_inhibit_conditions(bus, turn_signal=turn, speed_kmh=speed, wiper_high=wiper)
        send_lane_departure(bus)
        warned = bool(read_ldw_warning(bus))
        passed = warned == expect
        print(f"[{'PASS' if passed else 'FAIL'}] {label}: warn={'ON' if warned else 'OFF'} (expected={'ON' if expect else 'OFF'})")
        if not passed:
            failures.append(label)
    assert not failures, f"LDW inhibit failures: {failures}"

if __name__ == "__main__":
    test_ldw_inhibit_conditions()
    bus.shutdown()
```

### Result
- Inhibit conditions (a) turn signal and (b) speed<60: PASS ✓
- Inhibit condition (c) wiper HIGH: **FAIL** — LDW still warned
- Defect `ADAS-267` – LDW wiper inhibit not implemented
- Feature added in next sprint; all 5 inhibit conditions passed in regression.

---

## STAR Scenario 4 – Blind Spot Detection False Positive Rate

### Situation
BSD must not activate when no vehicle is in the blind spot. A field complaint reported the BSD icon flickering at highway speeds with no adjacent vehicles. No automated false-positive test existed.

### Task
Inject radar clear-object conditions (no targets) for 5 minutes and count any spurious BSD activations.

### Action
```python
import can
import cantools
import time

db  = cantools.database.load_file("adas.dbc")
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan')

def inject_clear_radar(bus, duration_s=300, interval_ms=20):
    """Send 'no object detected' radar frames for duration."""
    msg_def  = db.get_message_by_name('Radar_Object1')
    bsd_id   = db.get_message_by_name('BSD_Status').frame_id
    data     = msg_def.encode({'Obj_Valid': 0, 'Obj_Distance': 0, 'Obj_RelSpeed': 0})
    msg      = can.Message(arbitration_id=msg_def.frame_id, data=data, is_extended_id=False)

    false_positives = 0
    iterations = int(duration_s * 1000 / interval_ms)
    start = time.time()

    for i in range(iterations):
        bus.send(msg)
        rx = bus.recv(timeout=0.005)
        if rx and rx.arbitration_id == bsd_id:
            decoded = db.decode_message(rx.arbitration_id, rx.data)
            bsd_left  = int(decoded.get('BSD_Left',  0))
            bsd_right = int(decoded.get('BSD_Right', 0))
            if bsd_left or bsd_right:
                false_positives += 1
                print(f"  FALSE POSITIVE at t={time.time()-start:.2f}s L={bsd_left} R={bsd_right}")

        time.sleep(interval_ms / 1000.0)

    return false_positives

def test_bsd_false_positive():
    print("Running BSD false positive test (300s)...")
    fp_count = inject_clear_radar(bus, duration_s=300)
    print(f"\nFalse positives in 300s: {fp_count}")
    assert fp_count == 0, f"BSD generated {fp_count} false positive activations"

if __name__ == "__main__":
    test_bsd_false_positive()
    bus.shutdown()
```

### Result
- 14 false positives in 300 seconds (avg 1 every ~21s)
- Pattern: always occurred at exact 20-second intervals → timer-related
- Root cause: BSD internal object track expiry timer re-fired prematurely (20s watchdog reset bug)
- Defect `ADAS-389` – BSD object track expiry timer fires incorrectly
- Post-fix: 0 false positives in 3600s soak test.

---

## Summary Table

| Scenario | ADAS Feature | Python Approach | Defects Found |
|---|---|---|---|
| 1 – FCW TTC threshold | FCW | TTC synthesis via distance+speed | Sensor resolution tolerance |
| 2 – AEB latency & decel | AEB | Closing-target ramp injection | CI pipeline integration |
| 3 – LDW inhibit | LDW | Multi-condition CAN injection | Wiper inhibit not implemented |
| 4 – BSD false positive | BSD | 300s clear-radar soak | 20s timer bug causing FP |
