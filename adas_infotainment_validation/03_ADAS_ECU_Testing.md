# 03 — ADAS ECU Testing

> **Topic**: How to test a real ADAS ECU — from bench setup through full regression  
> **Tools**: dSPACE SCALEXIO, CANoe, ControlDesk, AutomationDesk, UDS tester  
> **Outcome**: Configure a test bench, stimulate sensor inputs, measure ECU outputs, run structured test cases

---

## 1. ADAS ECU Test Bench — Physical Setup

```
Minimal ADAS HIL Bench (domain controller test):
────────────────────────────────────────────────────────────────────────────────
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Test Bench                                         │
│                                                                              │
│   Power Supply (13.5 V / 40 A)     Bench PC (Windows 11)                   │
│       │                                │                                     │
│       │ 12 V + GND                 Ethernet (XCP + CM API)                  │
│       │                                │                                     │
│   ┌───▼────────────────────────────────▼────────────────────────────────┐   │
│   │              dSPACE SCALEXIO Rack                                   │   │
│   │  DS6001 (CPU)  DS1552 (CAN FD)  DS4330 (Eth)  DS2211 (Analog)      │   │
│   └──────────────────────────────┬───────────────────────────────────────┘   │
│                                  │ Wiring harness                            │
│   ┌──────────────────────────────▼───────────────────────────────────────┐   │
│   │                    BreakoutBox                                       │   │
│   │  (all ECU connector pins accessible for probing)                     │   │
│   └──────────────────────────────┬───────────────────────────────────────┘   │
│                                  │ ECU connector (original OEM plug)         │
│   ┌──────────────────────────────▼───────────────────────────────────────┐   │
│   │                   ADAS Domain Controller ECU                         │   │
│   │   (real production HW: processor, memory, sensor interfaces)         │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

### BreakoutBox — Why It Matters
```
BreakoutBox sits between HIL and ECU.
Every pin is broken out to a test point.

Advantages:
  ✓ Probe any signal with oscilloscope without opening the connector
  ✓ Insert fault injectors on any line
  ✓ Manually cut a signal (jumper) for open-circuit test
  ✓ Measure real voltage / current at each pin
  ✓ Add capacitors / resistors for noise simulation

Critical before any test:
  1. Use BreakoutBox continuity checker
  2. Verify all ECU power pins have 12 V / GND
  3. Verify CAN bus termination (120 Ω between CANH and CANL)
```

---

## 2. Bench Startup Procedure

```
Bench power-on sequence (always in this order):
────────────────────────────────────────────────────────────────────
Step  Action                              Wait Time  Check
────────────────────────────────────────────────────────────────────
  1   Power supply ON (12 V, limit 10 A)   —         LED green
  2   Boot dSPACE SCALEXIO                 30 s      ControlDesk detects HW
  3   Load .sdf application                5 s       Application running
  4   Start CarMaker (if simulation active) 10 s      CM GUI shows IDLE
  5   Assert KL15 signal (ignition)        —         DS2680 GPIO HIGH
  6   Wait for ECU boot                    3 s       CAN heartbeat present
  7   Verify ECU in STANDBY state          —         ADAS.State = 1 on CAN
  8   Clear DTCs                           —         UDS 14 FF FF FF
  9   Run post-flash sanity checks         30 s      All checks PASS
 10   Begin test execution                 —         Ready
────────────────────────────────────────────────────────────────────
```

---

## 3. Signal Stimulation for ADAS ECU

The HIL must simulate all vehicle signals the ADAS ECU reads:

### Sensor Signal Map (Example: ADAS Domain Controller)
```
Signal Category    Signal Name              HIL Source         Update Rate
───────────────────────────────────────────────────────────────────────────
Radar inputs       Radar_ObjectList         DS1552 CAN FD Tx   10 ms
Camera inputs      LaneData, ObjectList     DS1552 CAN FD Tx   20 ms
Ego dynamics       VehicleSpeed_kmh         DS1552 CAN FD Tx   10 ms
Ego dynamics       YawRate_degps            DS1552 CAN FD Tx   10 ms
Ego dynamics       LateralAccel_mss         DS1552 CAN FD Tx   10 ms
Steering           SteeringAngle_deg        DS1552 CAN FD Tx   10 ms
Engine             EngineRunning, RPM       DS1552 CAN FD Tx   20 ms
Brakes             BrakePedalActiv          DS1552 CAN FD Tx   10 ms
Gear               GearPosition             DS1552 CAN FD Tx   20 ms
Driver demand      AccelPedalPos_pct        DS2211 AO CH1       1 ms
Supply voltage     ECU_Vcc                  Power supply        —
Ignition           KL15                     DS2680 GPIO         —
───────────────────────────────────────────────────────────────────────────
```

### CAN Restbus Signal Definitions (Python)
```python
"""
Restbus signal generator for ADAS ECU test bench.
Simulates all vehicle ECU messages to create a realistic network.
"""
import can
import struct
import time
import math

class RestbusSim:
    """CAN restbus simulator — sends all non-SUT messages."""

    def __init__(self, channel="PCAN_USBBUS1", bitrate=500000):
        self.bus = can.interface.Bus(channel=channel,
                                     interface="pcan",
                                     bitrate=bitrate)
        self.t0 = time.time()

    def _elapsed(self):
        return time.time() - self.t0

    def _send(self, arb_id, data):
        msg = can.Message(arbitration_id=arb_id,
                          data=data, is_extended_id=False)
        self.bus.send(msg)

    def send_vehicle_speed(self, speed_kmh: float):
        """0x200 — WheelSpeeds, 10 ms cycle."""
        # Each wheel speed: 2 bytes, factor 0.01 km/h/LSB
        raw = int(speed_kmh / 0.01)
        data = struct.pack(">HHHH", raw, raw, raw, raw)
        self._send(0x200, data)

    def send_yaw_rate(self, yaw_rate_degps: float):
        """0x202 — IMU data, 10 ms cycle."""
        # Yaw rate: signed 16-bit, factor 0.01 deg/s/LSB, offset 0
        raw = int(yaw_rate_degps / 0.01) & 0xFFFF
        lat_accel_raw = 0  # 0 m/s²
        data = struct.pack(">HH", raw, lat_accel_raw)
        self._send(0x202, data)

    def send_radar_object(self, obj_id: int, dist_m: float,
                          rel_speed_ms: float, azimuth_deg: float):
        """0x400 + obj_id — Radar object list, 10 ms cycle."""
        arb_id = 0x400 + (obj_id & 0xF)
        dist_raw   = int(dist_m * 10) & 0xFFFF      # 0.1 m/LSB
        speed_raw  = int(rel_speed_ms * 100 + 32768) & 0xFFFF  # signed, offset
        angle_raw  = int(azimuth_deg * 10 + 1800) & 0xFFFF   # 0.1°/LSB, offset
        conf_raw   = 100  # 100% confidence
        data = struct.pack(">HHHB", dist_raw, speed_raw, angle_raw, conf_raw)
        self._send(arb_id, data)

    def run_scenario_approach(self, ego_speed_kmh: float,
                               initial_dist_m: float = 80.0,
                               approach_ms: float = 15.0):
        """
        Simulate a target vehicle approaching:
        - Ego drives at constant ego_speed_kmh
        - Target is stationary
        - Relative speed = ego_speed / 3.6 (approaching)
        """
        dist = initial_dist_m
        rel_spd = -(ego_speed_kmh / 3.6)  # negative = approaching

        print(f"Scenario: ego={ego_speed_kmh} km/h, "
              f"initial dist={initial_dist_m} m")

        start = time.time()
        while dist > 0 and time.time() - start < 30.0:
            self.send_vehicle_speed(ego_speed_kmh)
            self.send_radar_object(0, dist, rel_spd, 0.0)

            dist += rel_spd * 0.01   # dt = 10 ms
            time.sleep(0.01)

        print(f"Scenario ended. Final dist: {dist:.1f} m")
        return dist


# Usage
sim = RestbusSim()
final_dist = sim.run_scenario_approach(ego_speed_kmh=40, initial_dist_m=60)
if final_dist <= 0:
    print("COLLISION OCCURRED")
elif final_dist > 0:
    print(f"Avoided collision. Final gap: {final_dist:.1f} m")
```

---

## 4. Measuring ECU Outputs

The ECU produces outputs on multiple channels. The bench must capture all of them:

```
ADAS ECU Output Measurement Map:
───────────────────────────────────────────────────────────────────────────
Output                  Interface      HIL Measurement        Rate
───────────────────────────────────────────────────────────────────────────
Brake demand            CAN FD Tx      DS1552 CAN Rx          10 ms
ACC target accel        CAN FD Tx      DS1552 CAN Rx          20 ms
Steering torque req     CAN FD Tx      DS1552 CAN Rx          10 ms
FCW warning signal      CAN FD Tx      DS1552 CAN Rx          10 ms
ADAS state              CAN FD Tx      DS1552 CAN Rx          50 ms
Active DTC list         UDS 0x19       On demand (test)       —
Diagnostic status       UDS 0x22       On demand (test)       —
Supply current          Shunt resistor DS2211 AI CH1          1 ms
CAN bus load            DS1552 monitor ControlDesk variable    —
───────────────────────────────────────────────────────────────────────────
```

---

## 5. ADAS ECU Test Case Structure

### Test Case Template
```
ID:           TC-AEB-034
Title:        AEB city — stationary target — 40 km/h
Category:     Functional / ASIL C
Priority:     P1
Requirement:  REQ-AEB-012 (AEB shall activate when TTC ≤ 1.2 s)

Preconditions:
  - ECU SW v3.2.1 flashed and sanity check passed
  - No active DTCs
  - ECU in STANDBY state
  - Dry road condition (μ = 1.0 in simulation)
  - Temperature: 23°C ambient

Test Steps:
  1. Set vehicle speed: Car.vx = 40 km/h (11.11 m/s)
  2. Enable radar target: stationary object at 50 m, centered (0° azimuth)
  3. Allow simulation to run — target approaches at 11.11 m/s
  4. At TTC = 1.2 s → distance = 11.11 × 1.2 = 13.3 m
  5. Record: AEB.BrakeActive CAN signal
  6. Record: ECU brake pressure demand
  7. Allow scenario to run until Car.vx = 0 or 6 s elapsed

Expected Results:
  E1: AEB.BrakeActive transitions 0→1 within 150 ms of TTC = 1.2 s
  E2: Brake pressure demand ≥ 60 bar within 300 ms
  E3: No collision (Car.ContactForce = 0)
  E4: No unexpected DTC stored

Pass Criteria: ALL of E1, E2, E3, E4 satisfied

Actual Results: [FILLED IN DURING TEST]
Status: PASS / FAIL
Notes: [Any observations]
```

---

## 6. State Machine Testing

ADAS ECUs have complex state machines. Every state transition must be tested:

```
AEB State Machine:
──────────────────────────────────────────────────────────────────────
              Power ON
                 │
                 ▼
         ┌──────────────┐
         │  INIT        │ → Wait for sensor data + vehicle data
         └──────┬───────┘
                │ All inputs valid
                ▼
         ┌──────────────┐     Speed > 80 km/h OR
         │  STANDBY     │ ←── Rain sensor flag
         └──────┬───────┘
                │ Speed in ODD + sensors OK
                ▼
         ┌──────────────┐     Driver brakes
         │  ACTIVE      │ ←── System override
         └──────┬───────┘
                │ TTC < 1.5 s
                ▼
         ┌──────────────┐
         │  WARNING     │ → FCW alert signal on CAN
         └──────┬───────┘
                │ TTC < 1.2 s
                ▼
         ┌──────────────┐
         │  BRAKING     │ → Brake demand on CAN
         └──────┬───────┘
                │ Car.vx = 0 or obstacle cleared
                ▼
         ┌──────────────┐
         │  STANDBY     │ ← Reset after activation
         └──────────────┘
──────────────────────────────────────────────────────────────────────

State transition test matrix:
From        To          Trigger                    Test ID
──────────────────────────────────────────────────────────────────────
INIT        STANDBY     Sensor data valid           TC-AEB-001
STANDBY     ACTIVE      Speed ≤ 80 km/h             TC-AEB-002
ACTIVE      STANDBY     Speed > 80 km/h (inhibit)   TC-AEB-003
ACTIVE      WARNING     TTC = 1.5 s                 TC-AEB-004
WARNING     BRAKING     TTC = 1.2 s                 TC-AEB-005
BRAKING     STANDBY     Vehicle stopped              TC-AEB-006
ANY         FAULT       Radar disconnected           TC-AEB-020
──────────────────────────────────────────────────────────────────────
```

---

## 7. Timing Validation

Timing is critical for ADAS. Every response time must be measured:

```python
def measure_aeb_response_latency(bench, trigger_ttc_s=1.2,
                                  max_latency_ms=150):
    """
    Measure latency from TTC threshold crossing to brake command.
    
    Methodology:
    1. Timestamp when TTC crosses threshold (HIL side, known precisely)
    2. Timestamp when brake command appears on CAN (DS1552 HW timestamp)
    3. Latency = t_brake_cmd - t_ttc_cross
    """
    import time

    # Start scenario: 40 km/h, target at 50 m
    bench.set_variable("Sim.Car.vx", 40 / 3.6)
    bench.set_variable("Sim.Obstacle.Enable", 1)
    bench.set_variable("Sim.Obstacle.Dist", 50.0)

    t_threshold_crossed = None
    t_brake_cmd_seen    = None

    start = time.time()
    while time.time() - start < 10.0:
        ttc  = bench.get_variable("Sim.Sensor.Radar.TTC")
        brake = bench.get_variable("CAN_Rx.AEB_BrakeCmd.Pressure")

        if t_threshold_crossed is None and ttc <= trigger_ttc_s:
            t_threshold_crossed = time.time()

        if t_threshold_crossed is not None and brake > 5.0:
            t_brake_cmd_seen = time.time()
            break

        time.sleep(0.001)  # 1 ms polling

    if t_brake_cmd_seen and t_threshold_crossed:
        latency_ms = (t_brake_cmd_seen - t_threshold_crossed) * 1000
        status = "PASS" if latency_ms <= max_latency_ms else "FAIL"
        print(f"[{status}] AEB latency: {latency_ms:.1f} ms "
              f"(limit: {max_latency_ms} ms)")
        return latency_ms
    else:
        print("[FAIL] AEB did not activate")
        return None
```

---

## 8. Regression Test Management

```
Regression suite structure:
──────────────────────────────────────────────────────────────────────────────
Suite Name             # Tests  Duration   Run When
──────────────────────────────────────────────────────────────────────────────
Smoke                  12       5 min      Every new SW build
Quick regression       80       1 hour     Daily
Full regression        350      6 hours    Every release candidate
Safety regression      45       1 hour     Every ASIL C/D change
SOTIF edge cases       120      3 hours    Monthly / before homologation
Euro NCAP              60       2 hours    Every week
Fault injection        85       2 hours    Before release
Total                  752      20 hours   Full overnight run
──────────────────────────────────────────────────────────────────────────────

Regression metrics (target):
  Overall pass rate:        ≥ 98%
  New regressions:          0 (no tests that previously passed now fail)
  ASIL D coverage:          100% (all ASIL D requirements tested)
  Requirement coverage:     ≥ 95% (95% of SW reqs have ≥1 test case)
──────────────────────────────────────────────────────────────────────────────
```

---

## 9. DTC Testing

ADAS ECUs must store the correct DTC when sensors fail:

```
DTC test matrix (example):
─────────────────────────────────────────────────────────────────────────
DTC Code  Description                  Trigger Condition      Expected
─────────────────────────────────────────────────────────────────────────
0x112345  Radar sensor communication   No CAN msg for 500 ms  DTC stored,
                                                              ADAS off
0x113456  Camera data implausible      Lane width < 0.5 m     DTC stored,
                                       for 200 ms             LDW off
0x114567  Supply voltage low           V_supply < 9.0 V       DTC stored,
           (brownout)                  for 100 ms             ADAS off
0x115678  Internal processor fault     Watchdog timeout       DTC stored,
                                                              hard reset
─────────────────────────────────────────────────────────────────────────

DTC test procedure:
  1. Inject fault condition (e.g., stop radar CAN message)
  2. Wait for debounce time + confirmation time
  3. Read DTCs via UDS 0x19 02 09 (active DTCs)
  4. Assert expected DTC is present
  5. Assert ADAS feature is disabled (correct fail-safe behavior)
  6. Remove fault condition
  7. Wait for healing time (e.g., 10 driving cycles)
  8. Read DTCs: assert DTC is now PENDING or HEALED
  9. UDS 0x14 FF FF FF (clear all DTCs)
 10. Verify DTC is gone
─────────────────────────────────────────────────────────────────────────
```

---

## 10. Interview Q&A

**Q1: Walk me through setting up an ADAS ECU test bench from scratch.**  
First, the physical setup: power supply → ECU power pins via BreakoutBox, CAN/Ethernet cables between dSPACE I/O boards and ECU connector. Second, ConfigurationDesk: import the Simulink model, map CAN signals from DBC, set task rate to 1 ms, build and deploy. Third, bench startup procedure: apply power, boot SCALEXIO, assert KL15, wait for ECU boot, verify heartbeat. Fourth, flash ECU with latest SW, run sanity checks. Only then start test execution.

**Q2: How do you test an ADAS state machine?**  
I create a state transition test matrix covering every transition from the design document. For each transition: set up preconditions to reach the "from" state, apply the trigger stimulus (CAN signal, analog input, timing condition), and verify the ECU reaches the "to" state by observing the state CAN signal. I also test invalid transitions (e.g., going directly from INIT to BRAKING should be impossible) as negative tests.

**Q3: How do you measure AEB response latency on a HIL bench?**  
I use high-resolution timestamping: DS1552 hardware timestamps CAN message reception with < 1 µs accuracy. I record the exact time the TTC threshold is crossed (known from CarMaker DVA), and the time the brake command appears on CAN (DS1552 Rx timestamp). The difference is the latency. For a 150 ms requirement, typical measured values are 80–120 ms.

**Q4: What is a DTC debounce test?**  
The DTC debounce test verifies that the ECU doesn't store a DTC from a brief transient fault. Most ECUs require a fault to be present continuously for a configurable debounce time (e.g., 500 ms) before confirming it. I inject the fault, measure exactly how long until the DTC appears (should be ≥ debounce time), then remove the fault just before the debounce expires and verify no DTC is stored.

**Q5: What is the difference between a functional test and a fault injection test?**  
A functional test verifies the ADAS feature works correctly under normal operating conditions. A fault injection test verifies the system's fail-safe behavior when a component fails — does the ECU store the correct DTC, disable the affected feature, keep the rest of the system running, and alert the driver? Both are required: functional tests prove the feature works; fault injection tests prove it fails safely.
