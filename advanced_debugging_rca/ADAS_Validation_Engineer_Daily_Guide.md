# ADAS Validation Test Engineer — Daily Tasks, Responsibilities & Feature Testing Guide

> **Scope:** Complete day-to-day reference for ADAS validation engineers covering test bench
> preparation, feature-by-feature test execution (BSD, ACC, LKA, LDW, FCW, BCW, DMS, Parking
> Assistance), dynamic CAN message injection, DTC-based root cause analysis, and debugging.
>
> **Tools assumed:** CANoe / CANalyzer, vTestStudio, dSPACE HIL, Python, JIRA, DBC files

---

## Table of Contents

1. [Engineer Role Overview](#1-engineer-role-overview)
2. [Daily Workflow Checklist](#2-daily-workflow-checklist)
3. [Test Bench Preparation](#3-test-bench-preparation)
   - 3.1 Hardware Setup
   - 3.2 Software Setup
   - 3.3 Power-On Sequence
   - 3.4 Bus Health Verification
4. [Feature Testing — BSD (Blind Spot Detection)](#4-feature-testing--bsd-blind-spot-detection)
5. [Feature Testing — ACC (Adaptive Cruise Control)](#5-feature-testing--acc-adaptive-cruise-control)
6. [Feature Testing — LKA (Lane Keep Assist)](#6-feature-testing--lka-lane-keep-assist)
7. [Feature Testing — LDW (Lane Departure Warning)](#7-feature-testing--ldw-lane-departure-warning)
8. [Feature Testing — FCW (Forward Collision Warning)](#8-feature-testing--fcw-forward-collision-warning)
9. [Feature Testing — BCW (Blind Corner Warning / Cross Traffic Alert)](#9-feature-testing--bcw-blind-corner-warning--cross-traffic-alert)
10. [Feature Testing — DMS (Driver Monitoring System)](#10-feature-testing--dms-driver-monitoring-system)
11. [Feature Testing — Parking Assistance (APS/APA)](#11-feature-testing--parking-assistance-apsapa)
12. [Dynamic CAN Message Injection Reference](#12-dynamic-can-message-injection-reference)
13. [DTC Codes — Root Cause Analysis](#13-dtc-codes--root-cause-analysis)
14. [Debugging Workflow](#14-debugging-workflow)
15. [Defect Reporting Template](#15-defect-reporting-template)
16. [Glossary of Signal Abbreviations](#16-glossary-of-signal-abbreviations)
17. [ECU Software Flashing and Variant Coding](#17-ecu-software-flashing-and-variant-coding)
18. [Test Case Design Methodology](#18-test-case-design-methodology)
19. [vTestStudio Automated Test Framework](#19-vteststudio-automated-test-framework)
20. [Python Automation Scripts](#20-python-automation-scripts)
21. [Fault Injection Testing](#21-fault-injection-testing)
22. [LIN Bus Testing for Ultrasonic Sensors](#22-lin-bus-testing-for-ultrasonic-sensors)
23. [Automotive Ethernet (100BASE-T1) Testing for Camera ECU](#23-automotive-ethernet-100base-t1-testing-for-camera-ecu)
24. [XCP Calibration and Measurement During Testing](#24-xcp-calibration-and-measurement-during-testing)
25. [Regression Testing Strategy](#25-regression-testing-strategy)
26. [Test Metrics and Coverage Reporting](#26-test-metrics-and-coverage-reporting)
27. [Requirements Traceability](#27-requirements-traceability)
28. [ISO 26262 Functional Safety Considerations for Test Engineers](#28-iso-26262-functional-safety-considerations-for-test-engineers)
29. [Environmental and Stress Testing](#29-environmental-and-stress-testing)
30. [Test Execution Log Template](#30-test-execution-log-template)
31. [Common Pitfalls and Pro Tips](#31-common-pitfalls-and-pro-tips)

---

## 1. Engineer Role Overview

### Primary Responsibilities

| Category | Responsibility |
|----------|---------------|
| **Bench Ops** | Set up, power, maintain, and document HIL/SIL test benches |
| **Test Execution** | Execute manual and automated test cases for ADAS ECU features |
| **Signal Injection** | Simulate dynamic vehicle conditions via CAN/LIN/Ethernet stimulation |
| **Fault Injection** | Inject electrical faults (short to GND/VBAT, open circuit) and software faults |
| **DTC Analysis** | Read, clear, and root-cause Diagnostic Trouble Codes using UDS (ISO 14229) |
| **Debugging** | Trace timing, signal values, and state machine transitions to isolate bugs |
| **Defect Mgmt** | Log defects in JIRA with reproducible steps, traces, and DTC snapshots |
| **Coverage** | Map executed tests to requirements in DOORS / Excel requirement traceability matrix |
| **Reporting** | Daily status update, end-of-sprint test summary, regression gate report |
| **Release Gate** | Verify pass criteria before software release (sanity, regression, feature sign-off) |

### Typical Daily Time Allocation

```
07:30 - 08:00  Stand-up / JIRA board review
08:00 - 09:00  Bench power-on & health checks
09:00 - 12:00  Automated regression run + monitoring
12:00 - 13:00  Lunch
13:00 - 15:30  Manual feature testing / new test case execution
15:30 - 16:30  DTC analysis + defect logging
16:30 - 17:00  Test report update + hand-off notes
```

---

## 2. Daily Workflow Checklist

### Morning Startup

```
[ ] Pull latest ECU software build from CI server (e.g., TeamCity / Jenkins)
[ ] Check build release notes for changed features / fixed defects
[ ] Power on bench: PSU → HIL simulator → ECU → CAN interfaces
[ ] Launch CANoe, load project (.cfg), verify database (DBC/ARXML) versions
[ ] Run CAN bus health check — confirm all nodes transmitting at correct cycle times
[ ] Confirm ECU boot: check UDS 0x22 F186 (active session), 0x22 F189 (SW version)
[ ] Start measurement logging (blf + asc)
```

### Mid-Day

```
[ ] Check automated test run status — triage any new failures
[ ] Assign DTC snapshots to root cause categories (sensor, communication, logic)
[ ] Execute 2–3 planned manual test cases from sprint backlog
[ ] Update JIRA tickets: status, steps, traces attached
```

### End of Day

```
[ ] Save all measurement logs with naming: YYYY-MM-DD_<feature>_<SW-version>.blf
[ ] Archive test reports to shared drive / Confluence
[ ] Post daily status update (pass count, fail count, blocked count)
[ ] Close bench if unattended: ECU off → HIL off → PSU off
```

---

## 3. Test Bench Preparation

### 3.1 Hardware Setup

```
Physical Layout:
┌─────────────────────────────────────────────────────────────────┐
│  Power Supply (13.5 V / 20 A nominal; 16 V spike for cranking)  │
│       │                                                          │
│       ▼                                                          │
│  Fuse Panel (15 A per ECU rail)                                  │
│       │                                                          │
│       ▼                                                          │
│  ADAS ECU (Device Under Test)                                    │
│   │      │        │         │                                    │
│  CAN1   CAN2    LIN1     ETH (100BASE-T1)                        │
│   │      │        │         │                                    │
│  Vector VN1640A (4-channel CAN-FD / LIN)                        │
│                             │                                    │
│                        dSPACE DS6601 (Eth)                       │
│                                                                  │
│  dSPACE SCALEXIO  ←→  I/O Board DS2655                          │
│   (Plant Model)      (Analog: wheel speed, steering angle)       │
└─────────────────────────────────────────────────────────────────┘
```

**Wiring Rules:**
- CAN bus must be terminated at both ends: **120 Ω** between CANH and CANL
- Use shielded twisted-pair cables; shield connected to chassis GND at one end only
- LIN bus pull-up resistor: **1 kΩ** from LIN to VBAT on master side
- ECU GND must be solid star-point connection to bench GND
- Power lines ≥ 1.5 mm² cross-section for high-current ECUs (radar, camera)

### 3.2 Software Setup

**Step 1 — Install and license tools:**
```
- CANoe 17.x (Vector)      → License via VLT server or USB dongle
- vTestStudio 5.x          → Same VLT license
- MATLAB/Simulink + dSPACE MLIB/MTRACE  → for plant model
- Python 3.11 + pytest + python-can      → automated test scripts
- JIRA / Confluence access
```

**Step 2 — CANoe project configuration:**
```
1. Open CANoe → File → Open → select <project>.cfg
2. Assign hardware channels:
   - Ch1 → CAN HS (500 kbps)
   - Ch2 → CAN MS (125 kbps) or CAN-FD (2 Mbps)
   - Ch3 → LIN 1 (19.2 kbps)
3. Load DBC databases:
   - ADAS_ECU.dbc  (ECU transmit/receive signals)
   - Body.dbc      (VehicleSpeed, GearPos, SteeringAngle from BCM)
   - Sensor.dbc    (Radar, Camera, USS signal frames)
4. Load ODX/PDX for UDS diagnostics
5. Enable logging: File → Logging → set output path and format (.blf)
```

**Step 3 — dSPACE plant model:**
```
1. Open ControlDesk → Load experiment
2. Compile and download Simulink plant model to SCALEXIO
3. Verify I/O mapping: wheel speed PWM → DS2655 digital output Ch1–Ch4
4. Start real-time application
5. Check signal values match expected idle state
```

### 3.3 Power-On Sequence

```
Order | Device          | Action                           | Expected Result
------|-----------------|----------------------------------|----------------------------------
1     | PSU             | Enable 13.5 V output             | Voltage = 13.2–13.8 V
2     | dSPACE SCALEXIO | Power on + load RT model         | Status LED green, model running
3     | Vector VN1640A  | USB connect, CANoe assigns HW    | Channels listed in Hw Config
4     | ADAS ECU        | Apply KL15 (ignition ON)         | Boot messages appear on CAN bus
5     | CANoe           | Start measurement                | Bus traffic visible in Trace
6     | UDS             | Send 0x10 03 (Extended Session)  | Positive response 0x50 03
7     | UDS             | Send 0x22 F189               | ECU returns SW version string
```

### 3.4 Bus Health Verification

**CAN Bus Health Checklist:**
```
[ ] Bus load: < 50% for HS CAN (warning if > 70%)
[ ] All expected periodic messages present (check Trace / Statistics window)
[ ] No error frames visible (CAN error counter = 0)
[ ] Message timing within ±10% of nominal cycle time
[ ] No "Bus Off" state on any channel
```

**CAPL: Automated bus health check at startup**
```c
on start {
  // Verify key periodic messages are alive
  setTimer(tHealthCheck, 2000);  // Check after 2s of measurement
}

on timer tHealthCheck {
  // Check VehicleSpeed message (0x200, 10 ms cycle)
  if (timeLastMsg(0x200) > 50) {
    write("ERROR: VehicleSpeed msg (0x200) missing or late! Last seen: %d ms ago",
          timeLastMsg(0x200));
  } else {
    write("OK: VehicleSpeed (0x200) alive");
  }

  // Check Radar message (0x300, 20 ms cycle)
  if (timeLastMsg(0x300) > 100) {
    write("ERROR: Radar msg (0x300) missing!");
  } else {
    write("OK: Radar (0x300) alive");
  }

  // Check ECU heartbeat (0x100, 10 ms cycle)
  if (timeLastMsg(0x100) > 50) {
    write("ERROR: ECU heartbeat (0x100) missing — ECU may not have booted!");
  } else {
    write("OK: ECU heartbeat (0x100) alive");
  }
}
```

---

## 4. Feature Testing — BSD (Blind Spot Detection)

### Feature Overview
BSD uses rear-corner radar sensors to detect vehicles in the driver's blind zones (left/right rear
flanks). It illuminates a warning indicator in the door mirror when a vehicle is detected, and
escalates to an audible/haptic alert if the turn signal is activated with a target present.

### Key CAN Signals

| Signal | Message ID | Byte/Bit | Values | Direction |
|--------|-----------|----------|--------|-----------|
| `BSD_Left_ObjectDetected` | 0x3A0 | B0, bit0 | 0=clear, 1=detected | ECU → Network |
| `BSD_Right_ObjectDetected` | 0x3A0 | B0, bit1 | 0=clear, 1=detected | ECU → Network |
| `BSD_Left_WarningActive` | 0x3A0 | B1, bit0 | 0=off, 1=warning | ECU → Network |
| `BSD_Right_WarningActive` | 0x3A0 | B1, bit1 | 0=off, 1=warning | ECU → Network |
| `TurnSignal_Left` | 0x220 | B0, bit0 | 0=off, 1=active | Network → ECU |
| `TurnSignal_Right` | 0x220 | B0, bit1 | 0=off, 1=active | Network → ECU |
| `VehicleSpeed` | 0x200 | B0-B1 | km/h × 100 | Network → ECU |
| `Radar_Rear_Left_Distance` | 0x3B0 | B0-B1 | cm | Network → ECU |
| `Radar_Rear_Right_Distance` | 0x3B0 | B2-B3 | cm | Network → ECU |
| `BSD_SystemStatus` | 0x3A0 | B2 | 0=off,1=standby,2=active | ECU → Network |

### Preconditions
```
- Vehicle speed: > 20 km/h (BSD activates above minimum speed threshold)
- Gear: D (Drive)
- No active DTC suppressing BSD
- BSD_Enable flag = 1 (set via CANoe IG or CAPL)
```

### Test Cases

#### TC-BSD-001: Target in Left Blind Spot — Warning Illuminated
```
Step 1: Set VehicleSpeed = 80 km/h
        CAN frame 0x200: [0xD0, 0x1F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        (0x1FD0 = 8144 → 8144 / 100 = 81.44 km/h ≈ 80 km/h)

Step 2: Set Radar_Rear_Left_Distance = 300 cm (3.0 m — within BSD zone)
        CAN frame 0x3B0: [0x2C, 0x01, 0xFF, 0x7F, 0x00, 0x00, 0x00, 0x00]
        (0x012C = 300 cm on B0-B1; B2-B3 = 0x7FFF = no target right)

Step 3: Wait 200 ms for ECU processing

Step 4: Verify CAN 0x3A0:
        BSD_Left_ObjectDetected = 1 (B0 bit0)
        BSD_Left_WarningActive  = 1 (B1 bit0)

Expected Result: Left mirror indicator ON, no escalation (no turn signal active)
Pass Criteria:   Response within 300 ms of target placement
```

#### TC-BSD-002: Target + Turn Signal (Escalation to Alert)
```
Step 1: Repeat TC-BSD-001 steps 1–3

Step 2: Activate left turn signal
        CAN frame 0x220: [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        (B0 bit0 = 1 → TurnSignal_Left active)

Step 3: Verify CAN 0x3A0:
        BSD_Left_WarningActive = 1 AND
        BSD_AlertEscalation    = 1 (B1 bit2)

Expected Result: Mirror indicator + audible/haptic warning
Pass Criteria:   Escalation within 100 ms of turn signal assertion
```

#### TC-BSD-003: Below Speed Threshold — No Warning
```
Step 1: Set VehicleSpeed = 15 km/h (below 20 km/h threshold)
Step 2: Set Radar_Rear_Left_Distance = 200 cm
Step 3: Verify BSD_Left_WarningActive = 0 (BSD inactive below threshold)
Pass Criteria:   No warning output regardless of target presence
```

#### TC-BSD-004: Target Leaves Blind Zone — Warning Cleared
```
Step 1: Run TC-BSD-001 until warning is active
Step 2: Set Radar_Rear_Left_Distance = 0x7FFF (no target)
Step 3: Verify BSD_Left_ObjectDetected = 0 within 500 ms (hysteresis)
```

### CAPL Script — BSD Dynamic Simulation
```c
variables {
  message 0x200 msg_VehicleSpeed;
  message 0x3B0 msg_RadarRear;
  message 0x220 msg_TurnSignal;
  msTimer tBSD_Sequence;
  int bsd_step = 0;
}

on start {
  // Initialize: vehicle moving at 80 km/h, no targets
  msg_VehicleSpeed.byte(0) = 0xD0;
  msg_VehicleSpeed.byte(1) = 0x1F;
  output(msg_VehicleSpeed);
  // No radar target: 0x7FFF both sides
  msg_RadarRear.byte(0) = 0xFF;
  msg_RadarRear.byte(1) = 0x7F;
  msg_RadarRear.byte(2) = 0xFF;
  msg_RadarRear.byte(3) = 0x7F;
  output(msg_RadarRear);
  setTimer(tBSD_Sequence, 1000);
}

on timer tBSD_Sequence {
  switch(bsd_step) {
    case 0:  // Inject left-rear target at 3 m
      msg_RadarRear.byte(0) = 0x2C;
      msg_RadarRear.byte(1) = 0x01;  // 300 cm left
      output(msg_RadarRear);
      write("BSD: Left target injected at 300 cm");
      setTimer(tBSD_Sequence, 500);
      bsd_step = 1;
      break;

    case 1:  // Check ECU output
      write("BSD_Left_ObjectDetected = %d",
            $BSD_Left_ObjectDetected);
      write("BSD_Left_WarningActive  = %d",
            $BSD_Left_WarningActive);
      // Activate turn signal
      msg_TurnSignal.byte(0) = 0x01;
      output(msg_TurnSignal);
      write("BSD: Left turn signal activated");
      setTimer(tBSD_Sequence, 300);
      bsd_step = 2;
      break;

    case 2:  // Verify escalation
      write("BSD_AlertEscalation = %d", $BSD_AlertEscalation);
      // Clear target
      msg_RadarRear.byte(0) = 0xFF;
      msg_RadarRear.byte(1) = 0x7F;
      output(msg_RadarRear);
      msg_TurnSignal.byte(0) = 0x00;
      output(msg_TurnSignal);
      write("BSD: Target cleared, turn signal off");
      bsd_step = 3;
      break;
  }
}
```

---

## 5. Feature Testing — ACC (Adaptive Cruise Control)

### Feature Overview
ACC maintains a driver-set speed and automatically adjusts throttle/braking to keep a safe
following distance from a lead vehicle detected by forward-facing radar.

### Key CAN Signals

| Signal | Message ID | Byte/Bit | Values | Direction |
|--------|-----------|----------|--------|-----------|
| `ACC_Enable` | 0x410 | B2, bit0 | 0=off, 1=on | Network → ECU |
| `ACC_SetSpeed` | 0x410 | B0-B1 | km/h × 10 | Network → ECU |
| `ACC_TimeGap` | 0x410 | B3 | 1–4 (gap settings) | Network → ECU |
| `RadarFwd_Distance` | 0x300 | B0-B1 | cm | Network → ECU |
| `RadarFwd_RelSpeed` | 0x300 | B2-B3 | signed, km/h × 10 | Network → ECU |
| `VehicleSpeed` | 0x200 | B0-B1 | km/h × 100 | Network → ECU |
| `WheelSpeed_FL/FR/RL/RR` | 0x201 | B0-B7 | km/h × 100 per wheel | Network → ECU |
| `GearPosition` | 0x210 | B0 | 0=P,1=R,2=N,3=D | Network → ECU |
| `BrakeSwitch` | 0x210 | B1, bit0 | 0=off, 1=pressed | Network → ECU |
| `ThrottleRequest` | 0x500 | B0 | 0–100% | ECU → Network |
| `BrakeRequest_mbar` | 0x501 | B0-B1 | pressure in mbar | ECU → Network |
| `ACC_Status` | 0x502 | B0 | 0=off,1=standby,2=active,3=override | ECU → Network |
| `ACC_DisplaySpeed` | 0x502 | B1-B2 | set speed for cluster display | ECU → Network |

### Test Cases

#### TC-ACC-001: Straight-line Speed Hold
```
Step 1: Set GearPosition = D, BrakeSwitch = 0
        CAN 0x210: [0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

Step 2: Set VehicleSpeed = 100 km/h
        CAN 0x200: [0xE8, 0x27, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        (0x27E8 = 10216 / 100 = 102.16 ~ 100 km/h)

Step 3: Enable ACC, set target = 100 km/h
        CAN 0x410: [0xE8, 0x03, 0x01, 0x02, 0x00, 0x00, 0x00, 0x00]
        (0x03E8 = 1000 / 10 = 100 km/h; B2 bit0 = 1 enable; B3 = 2 medium gap)

Step 4: Inject no lead vehicle: RadarFwd_Distance = 0xFFFF
        CAN 0x300: [0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

Step 5: Verify ThrottleRequest maintains ~30–40% to sustain 100 km/h
        ACC_Status = 2 (active)

Pass Criteria: Speed stays within ±2 km/h of set speed over 10 seconds
```

#### TC-ACC-002: Lead Vehicle Cut-in — Deceleration
```
Step 1: ACC active at 100 km/h (repeat TC-ACC-001 setup)

Step 2: Inject lead vehicle at 50 m, relative speed = -30 km/h (approaching fast)
        CAN 0x300: [0xD0, 0x07, 0xD4, 0xFE, 0x00, 0x00, 0x00, 0x00]
        B0-B1: 0x07D0 = 2000 cm = 20 m
        B2-B3: 0xFED4 = -300 signed = -300 / 10 = -30 km/h relative speed

Step 3: Verify ECU response within 300 ms:
        - ThrottleRequest drops to 0
        - BrakeRequest_mbar > 0 (active braking)
        - ACC_Status = 2 (still active, no override)

Pass Criteria: Brake applied within 300 ms; distance to virtual target stabilizes
```

#### TC-ACC-003: Driver Override (Brake Pressed)
```
Step 1: ACC active state

Step 2: Set BrakeSwitch = 1
        CAN 0x210: [0x03, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

Step 3: Verify ACC_Status = 3 (override) within 100 ms
        ThrottleRequest = 0 (ECU releases throttle immediately)

Step 4: Release brake: BrakeSwitch = 0
Step 5: Verify ACC_Status returns to 1 (standby) — requires driver re-enable
Pass Criteria: Override response < 100 ms; no automatic re-engagement
```

#### TC-ACC-004: ACC Auto Cancel on Gear Shift to N
```
Step 1: ACC active
Step 2: Set GearPosition = N (Neutral)
        CAN 0x210 B0 = 0x02
Step 3: Verify ACC_Status = 0 (off) within 200 ms
Pass Criteria: ACC cancels on neutral; cluster shows ACC unavailable
```

---

## 6. Feature Testing — LKA (Lane Keep Assist)

### Feature Overview
LKA uses a forward-facing camera to detect lane markings and applies corrective steering torque
to keep the vehicle centred in the lane. Active above ~60 km/h.

### Key CAN Signals

| Signal | Message ID | Byte/Bit | Values | Direction |
|--------|-----------|----------|--------|-----------|
| `LKA_Enable` | 0x430 | B0, bit0 | 0/1 | Network → ECU |
| `LaneOffset_cm` | 0x350 | B0-B1 | signed, cm from centre | Network → ECU |
| `LaneCurvature` | 0x350 | B2-B3 | signed, 1/m × 1000 | Network → ECU |
| `LaneQuality` | 0x350 | B4, b0-b3 | 0–15 (15=best) | Network → ECU |
| `SteeringAngle_deg` | 0x230 | B0-B1 | signed, deg × 10 | Network → ECU |
| `SteeringTorque_Nm` | 0x230 | B2-B3 | signed, Nm × 100 | Network → ECU |
| `TurnSignal_Left` | 0x220 | B0, bit0 | 0/1 | Network → ECU |
| `TurnSignal_Right` | 0x220 | B0, bit1 | 0/1 | Network → ECU |
| `LKA_TorqueRequest_Nm` | 0x503 | B0-B1 | signed Nm × 100, ECU request to EPS | ECU → Network |
| `LKA_Status` | 0x503 | B2 | 0=off,1=standby,2=active,3=warning | ECU → Network |
| `LKA_SoundAlert` | 0x503 | B3, bit0 | 0/1 | ECU → Network |

### Test Cases

#### TC-LKA-001: Normal Lane Centring
```
Step 1: VehicleSpeed = 80 km/h, GearPosition = D
Step 2: Enable LKA: CAN 0x430 B0 = 0x01
Step 3: Set LaneOffset = 0 cm (perfectly centred), LaneQuality = 12
        CAN 0x350: [0x00, 0x00, 0x00, 0x00, 0xC0, 0x00, 0x00, 0x00]
        (B4 b0-b3 = 12 = 0xC)

Step 4: Verify LKA_Status = 2 (active), LKA_TorqueRequest ≈ 0 Nm (no correction needed)
Pass Criteria: No unnecessary torque applied when vehicle is centred
```

#### TC-LKA-002: Left Lane Drift — Corrective Torque Applied
```
Step 1: LKA active (TC-LKA-001 precondition)

Step 2: Gradually increase LaneOffset to +40 cm (drifting left)
        CAN 0x350 B0-B1: 0x0028 = 40 cm
        Send in increments: +10, +20, +30, +40 cm (simulate gradual drift)

Step 3: Verify LKA_TorqueRequest becomes positive (right-correcting torque)
        Expected: ≥ +150 Nm × 100 (i.e., ≥ 1.5 Nm) at 40 cm offset

Step 4: Ramp offset back to 0 → torque returns to 0
Pass Criteria: Proportional torque response; no oscillation
```

#### TC-LKA-003: Turn Signal Suppression
```
Step 1: LKA active, LaneOffset = +35 cm (would trigger correction)
Step 2: Activate right turn signal: CAN 0x220 B0 bit1 = 1
Step 3: Verify LKA_TorqueRequest = 0 (suppressed during intentional lane change)
Step 4: Deactivate turn signal → torque correction resumes
Pass Criteria: LKA suppressed within 50 ms of turn signal; resumes after signal off
```

#### TC-LKA-004: Low Lane Quality — LKA Standby
```
Step 1: LKA active
Step 2: Set LaneQuality = 3 (low confidence — rain, faded lines)
        CAN 0x350 B4 = 0x03
Step 3: Verify LKA_Status transitions to 1 (standby) within 500 ms
        LKA_SoundAlert = 1 (driver attention notification)
Pass Criteria: LKA gracefully degrades; no abrupt torque cut
```

---

## 7. Feature Testing — LDW (Lane Departure Warning)

### Feature Overview
LDW is a warning-only feature (unlike LKA it does NOT apply steering). It alerts the driver via
audible and visual warning when the vehicle crosses lane markings without a turn signal active.

### Key CAN Signals

| Signal | Message ID | Byte/Bit | Values | Direction |
|--------|-----------|----------|--------|-----------|
| `LDW_Enable` | 0x431 | B0, bit0 | 0/1 | Network → ECU |
| `LaneOffset_cm` | 0x350 | B0-B1 | signed cm | Network → ECU |
| `TurnSignal_Left/Right` | 0x220 | B0 bits | 0/1 | Network → ECU |
| `VehicleSpeed` | 0x200 | B0-B1 | km/h × 100 | Network → ECU |
| `LDW_LeftWarning` | 0x504 | B0, bit0 | 0/1 | ECU → Network |
| `LDW_RightWarning` | 0x504 | B0, bit1 | 0/1 | ECU → Network |
| `LDW_AudioAlert` | 0x504 | B1, bit0 | 0/1 | ECU → Network |

### Test Cases

#### TC-LDW-001: Left Lane Departure — Warning Triggered
```
Step 1: VehicleSpeed = 70 km/h, GearPosition = D, LDW enabled
Step 2: TurnSignal = OFF (no intentional lane change)
Step 3: Set LaneOffset to -35 cm (crossing left marking threshold)
        CAN 0x350 B0-B1: 0xFFDB (signed: -35 in two's complement)
Step 4: Verify:
        LDW_LeftWarning = 1
        LDW_AudioAlert  = 1
Pass Criteria: Warning within 200 ms of threshold crossing
```

#### TC-LDW-002: Intentional Lane Change — No Warning
```
Step 1: LDW active, TurnSignal_Left = 1
Step 2: Set LaneOffset to -35 cm
Step 3: Verify LDW_LeftWarning = 0 (suppressed by turn signal)
Pass Criteria: No false warning during intentional lane change
```

#### TC-LDW-003: Below Speed Threshold
```
Step 1: VehicleSpeed = 30 km/h (below LDW activation speed ~60 km/h)
Step 2: Set LaneOffset to -40 cm
Step 3: Verify LDW_LeftWarning = 0
Pass Criteria: No warning below minimum speed
```

---

## 8. Feature Testing — FCW (Forward Collision Warning)

### Feature Overview
FCW warns the driver of an imminent collision with a vehicle or obstacle ahead. It uses
forward radar and/or camera fusion. Warning is escalated (visual → audible → haptic) as
time-to-collision (TTC) decreases.

### Key CAN Signals

| Signal | Message ID | Byte/Bit | Values | Direction |
|--------|-----------|----------|--------|-----------|
| `RadarFwd_Distance` | 0x300 | B0-B1 | cm | Network → ECU |
| `RadarFwd_RelSpeed` | 0x300 | B2-B3 | signed km/h × 10 | Network → ECU |
| `RadarFwd_ObjectValid` | 0x300 | B4, bit0 | 0/1 | Network → ECU |
| `VehicleSpeed` | 0x200 | B0-B1 | km/h × 100 | Network → ECU |
| `FCW_Sensitivity` | 0x440 | B0 | 1=low,2=med,3=high | Network → ECU |
| `FCW_VisualWarning` | 0x510 | B0, bit0 | 0/1 | ECU → Network |
| `FCW_AudioWarning` | 0x510 | B0, bit1 | 0/1 | ECU → Network |
| `FCW_HapticWarning` | 0x510 | B0, bit2 | 0/1 | ECU → Network |
| `FCW_TTC_ms` | 0x510 | B1-B2 | TTC in ms | ECU → Network |
| `FCW_Status` | 0x510 | B3 | 0=off,1=standby,2=active | ECU → Network |

### TTC-Based Warning Thresholds (Typical)

| TTC Range | Warning Level |
|-----------|--------------|
| > 3.0 s | No warning |
| 2.0–3.0 s | Visual only |
| 1.2–2.0 s | Visual + Audio |
| < 1.2 s | Visual + Audio + Haptic (pre-brake) |

### Test Cases

#### TC-FCW-001: Approaching Stationary Object — TTC 2.5 s (Visual Warning)
```
Step 1: VehicleSpeed = 80 km/h, FCW_Sensitivity = 2 (medium)
Step 2: Set RadarFwd_Distance = 5556 cm (55.56 m)
        RelSpeed = -800 (i.e., -80 km/h — stationary target, ego speed = 80)
        CAN 0x300: [0xB4, 0x15, 0x38, 0xFC, 0x01, 0x00, 0x00, 0x00]
        B0-B1: 0x15B4 = 5556 cm; B2-B3: 0xFC38 = -968 (≈ -96.8 km/h rel) — adjust to match
        Note: TTC = distance / relative_speed = 5556 cm / (8000 cm/s) ≈ 0.69 s — adjust distance

        Corrected for TTC = 2.5 s:
        distance = TTC × speed = 2.5 × (80/3.6) m = 55.6 m = 5560 cm
        CAN 0x300: [0xB8, 0x15, 0x38, 0xFC, 0x01, 0x00, 0x00, 0x00]

Step 3: Verify FCW_VisualWarning = 1, FCW_AudioWarning = 0, FCW_HapticWarning = 0
Step 4: Read FCW_TTC_ms — expected ≈ 2500
Pass Criteria: Visual-only warning at TTC 2.0–3.0 s
```

#### TC-FCW-002: Critical TTC — Full Escalation
```
Step 1: Ramp RadarFwd_Distance down from 5560 cm to 1200 cm over 3 seconds
        (simulate rapidly closing gap)

Step 2: At distance ≈ 1333 cm (TTC ≈ 0.6 s):
        Verify FCW_VisualWarning = 1
             FCW_AudioWarning  = 1
             FCW_HapticWarning = 1

Pass Criteria: All three warning levels active; TTC reading < 1200 ms
```

#### TC-FCW-003: False Positive Check — Stationary Object Off-Path
```
Step 1: Set RadarFwd_ObjectValid = 0 (object not in ego lane)
Step 2: Set distance to 1000 cm
Step 3: Verify FCW_VisualWarning = 0 (no warning for off-path objects)
Pass Criteria: No warning when object validity flag is 0
```

---

## 9. Feature Testing — BCW (Blind Corner Warning / Cross Traffic Alert — CTA)

### Feature Overview
BCW/CTA warns the driver about cross-traffic approaching from the sides while reversing or
manoeuvring in tight spaces (e.g., exiting a parking bay). Uses rear-corner radars.

### Key CAN Signals

| Signal | Message ID | Byte/Bit | Values | Direction |
|--------|-----------|----------|--------|-----------|
| `GearPosition` | 0x210 | B0 | 1=R (Reverse) | Network → ECU |
| `VehicleSpeed` | 0x200 | B0-B1 | km/h × 100 (near 0) | Network → ECU |
| `Radar_Corner_Left_Distance` | 0x3C0 | B0-B1 | cm | Network → ECU |
| `Radar_Corner_Right_Distance` | 0x3C0 | B2-B3 | cm | Network → ECU |
| `Radar_Corner_Left_Speed` | 0x3C0 | B4-B5 | km/h × 10 | Network → ECU |
| `Radar_Corner_Right_Speed` | 0x3C0 | B6-B7 | km/h × 10 | Network → ECU |
| `BCW_Left_Warning` | 0x3D0 | B0, bit0 | 0/1 | ECU → Network |
| `BCW_Right_Warning` | 0x3D0 | B0, bit1 | 0/1 | ECU → Network |
| `BCW_AudioAlert` | 0x3D0 | B1 | 0=off,1=slow,2=fast | ECU → Network |

### Test Cases

#### TC-BCW-001: Reversing — Cross-Traffic from Left
```
Step 1: GearPosition = R, VehicleSpeed = 3 km/h
        CAN 0x210: [0x01, 0x00, ...]; CAN 0x200: [0x2C, 0x01, ...]

Step 2: Inject vehicle approaching from left at 20 km/h at 400 cm
        CAN 0x3C0: [0x90, 0x01, 0xFF, 0x7F, 0xC8, 0x00, 0x00, 0x00]
        B0-B1: 0x0190 = 400 cm; B4-B5: 0x00C8 = 200 (20 km/h × 10)

Step 3: Verify BCW_Left_Warning = 1, BCW_AudioAlert > 0
Pass Criteria: Warning within 300 ms; escalation as distance decreases
```

---

## 10. Feature Testing — DMS (Driver Monitoring System)

### Feature Overview
DMS uses an in-cabin infrared camera (or eye-tracking sensor) to monitor driver attention —
detecting drowsiness (eye closure, head nod), distraction (gaze off-road), and absence.

### Key CAN Signals

| Signal | Message ID | Byte/Bit | Values | Direction |
|--------|-----------|----------|--------|-----------|
| `DMS_GazeDirection` | 0x3E0 | B0 | 0=forward,1=left,2=right,3=down,4=up | Network → ECU |
| `DMS_EyeClosure_pct` | 0x3E0 | B1 | 0–100% | Network → ECU |
| `DMS_HeadPose_Yaw` | 0x3E0 | B2-B3 | signed deg × 10 | Network → ECU |
| `DMS_HeadPose_Pitch` | 0x3E0 | B4-B5 | signed deg × 10 | Network → ECU |
| `DMS_FaceDetected` | 0x3E0 | B6, bit0 | 0/1 | Network → ECU |
| `DMS_DrowsinessLevel` | 0x520 | B0 | 0=alert,1=mild,2=moderate,3=severe | ECU → Network |
| `DMS_DistractionAlert` | 0x520 | B1, bit0 | 0/1 | ECU → Network |
| `DMS_AbsenceAlert` | 0x520 | B2, bit0 | 0/1 | ECU → Network |
| `DMS_AudioWarning` | 0x520 | B3 | 0=off,1=chime,2=voice | ECU → Network |

### Test Cases

#### TC-DMS-001: Drowsiness Detection (Eye Closure > 80%)
```
Step 1: VehicleSpeed = 60 km/h, DMS_FaceDetected = 1, eyes open (EyeClosure = 5%)

Step 2: Ramp EyeClosure to 85% over 3 seconds (simulating dozing)
        CAN 0x3E0 B1: 0x05 → 0x20 → 0x40 → 0x55 → 0x64 → 0x69 (increments)

Step 3: Hold EyeClosure = 85% for 1.5 seconds

Step 4: Verify DMS_DrowsinessLevel ≥ 2 (moderate)
        DMS_AudioWarning = 1 or 2

Pass Criteria: Drowsiness alert within 2 s of sustained high eye closure
```

#### TC-DMS-002: Gaze Distraction (Gaze Off-Road > 3 s)
```
Step 1: DMS_FaceDetected = 1, initial gaze = 0 (forward)
Step 2: Set DMS_GazeDirection = 2 (right, off-road) for 4 continuous seconds
Step 3: Verify DMS_DistractionAlert = 1 after 3 s threshold
Pass Criteria: Alert triggered at 3 s; cleared within 500 ms of gaze return
```

#### TC-DMS-003: Driver Absence
```
Step 1: VehicleSpeed > 10 km/h (vehicle in motion)
Step 2: Set DMS_FaceDetected = 0 for 5 seconds
Step 3: Verify DMS_AbsenceAlert = 1, DMS_AudioWarning = 2 (voice escalation)
Pass Criteria: Absence alert within 5 s; escalates to maximum warning
```

---

## 11. Feature Testing — Parking Assistance (APS/APA)

### Feature Overview
Parking assistance includes ultrasonic-sensor-based obstacle detection (PDC), and in advanced
systems, Automatic Parking Assist (APA) with autonomous steering/throttle/brake control.

### Key CAN Signals — PDC (Proximity Detection)

| Signal | Message ID | Byte/Bit | Values | Direction |
|--------|-----------|----------|--------|-----------|
| `USS_Front_L/CL/CR/R` | 0x3F0 | B0–B3 | distance cm (0=no object, 255=out of range) | Network → ECU |
| `USS_Rear_L/CL/CR/R` | 0x3F1 | B0–B3 | distance cm | Network → ECU |
| `GearPosition` | 0x210 | B0 | 1=R triggers rear PDC | Network → ECU |
| `VehicleSpeed` | 0x200 | B0-B1 | km/h × 100 (near 0 for parking) | Network → ECU |
| `PDC_Front_Zone` | 0x530 | B0 | 0=clear,1=far,2=mid,3=near,4=critical | ECU → Network |
| `PDC_Rear_Zone` | 0x530 | B1 | 0=clear … 4=critical | ECU → Network |
| `PDC_AudioBeep_Rate` | 0x530 | B2 | 0=off,1=slow,2=med,3=fast,4=continuous | ECU → Network |

### Key CAN Signals — APA (Auto Parking)

| Signal | Message ID | Byte/Bit | Values | Direction |
|--------|-----------|----------|--------|-----------|
| `APA_Enable` | 0x450 | B0, bit0 | 0/1 | Network → ECU |
| `APA_ParkingSpaceDetected` | 0x531 | B0, bit0 | 0/1 | ECU → Network |
| `APA_SteeringRequest_deg` | 0x532 | B0-B1 | signed deg × 10 | ECU → Network |
| `APA_BrakeRequest_mbar` | 0x533 | B0-B1 | pressure | ECU → Network |
| `APA_ThrottleRequest_pct` | 0x533 | B2 | 0–100% | ECU → Network |
| `APA_Status` | 0x531 | B1 | 0=off,1=scanning,2=space_found,3=maneuvering,4=done,5=aborted | ECU → Network |
| `APA_DriverInstruction` | 0x531 | B2 | 0=none,1=release_brakes,2=apply_brakes,3=engage_gear | ECU → Network |

### Test Cases

#### TC-PDC-001: Rear Object Detection Zones
```
Step 1: GearPosition = R, VehicleSpeed = 2 km/h

Step 2: Set rear USS distances in sequence:
  Far zone  (150 cm): CAN 0x3F1: [0x96, 0x96, 0x96, 0x96, ...]
             Verify PDC_Rear_Zone = 1, PDC_AudioBeep_Rate = 1 (slow)

  Mid zone  (100 cm): CAN 0x3F1: [0x64, 0x64, 0x64, 0x64, ...]
             Verify PDC_Rear_Zone = 2, PDC_AudioBeep_Rate = 2 (medium)

  Near zone  (50 cm): CAN 0x3F1: [0x32, 0x32, 0x32, 0x32, ...]
             Verify PDC_Rear_Zone = 3, PDC_AudioBeep_Rate = 3 (fast)

  Critical   (20 cm): CAN 0x3F1: [0x14, 0x14, 0x14, 0x14, ...]
             Verify PDC_Rear_Zone = 4, PDC_AudioBeep_Rate = 4 (continuous)

Pass Criteria: Correct zone and beep rate at each distance threshold
```

#### TC-PDC-002: Front PDC — Gear D at Low Speed
```
Step 1: GearPosition = D, VehicleSpeed = 5 km/h
Step 2: Set USS_Front_CL = 40 cm
        CAN 0x3F0 B1 = 0x28
Step 3: Verify PDC_Front_Zone = 3 (near), PDC_AudioBeep_Rate = 3
Pass Criteria: Front PDC active in Drive gear at low speed
```

#### TC-APA-001: Parking Space Scan
```
Step 1: VehicleSpeed = 20 km/h (slow drive-by to scan)
Step 2: Enable APA: CAN 0x450 B0 = 0x01
Step 3: Simulate parking space by setting side USS to out-of-range (255) over 3 m of travel
        (inject USS side sensor = 255 = no object for 3 m, indicating open space)

Step 4: Verify APA_Status = 1 (scanning) → 2 (space_found)
        APA_ParkingSpaceDetected = 1

Step 5: Simulate driver stopping and releasing brakes
        APA_DriverInstruction: expect instruction 1 (release_brakes)

Step 6: Verify APA_SteeringRequest_deg changes (ECU autonomously steering)
Pass Criteria: Space detected within 3 m scan; steering manoeuvre initiated
```

### CAPL Script — USS Parking Scenario
```c
variables {
  message 0x3F1 msg_USS_Rear;
  message 0x210 msg_GearPos;
  message 0x200 msg_Speed;
  msTimer tPDC_Ramp;
  int pdc_step = 0;
}

on start {
  // Gear = R, speed = 2 km/h
  msg_GearPos.byte(0) = 0x01;
  output(msg_GearPos);
  msg_Speed.byte(0) = 0xC8; // 200 / 100 = 2 km/h
  msg_Speed.byte(1) = 0x00;
  output(msg_Speed);
  // Start with clear zone
  msg_USS_Rear.byte(0) = 0xFF;
  msg_USS_Rear.byte(1) = 0xFF;
  msg_USS_Rear.byte(2) = 0xFF;
  msg_USS_Rear.byte(3) = 0xFF;
  output(msg_USS_Rear);
  setTimer(tPDC_Ramp, 1000);
}

on timer tPDC_Ramp {
  switch(pdc_step) {
    case 0:  // Far zone: 150 cm
      msg_USS_Rear.byte(0) = 0x96;
      msg_USS_Rear.byte(1) = 0x96;
      msg_USS_Rear.byte(2) = 0x96;
      msg_USS_Rear.byte(3) = 0x96;
      output(msg_USS_Rear);
      write("PDC: Far zone — 150 cm");
      write("Expected PDC_Rear_Zone = 1, Beep = slow");
      setTimer(tPDC_Ramp, 1500); pdc_step = 1; break;

    case 1:  // Near zone: 50 cm
      msg_USS_Rear.byte(0) = 0x32;
      msg_USS_Rear.byte(1) = 0x32;
      msg_USS_Rear.byte(2) = 0x32;
      msg_USS_Rear.byte(3) = 0x32;
      output(msg_USS_Rear);
      write("PDC: Near zone — 50 cm");
      write("Expected PDC_Rear_Zone = 3, Beep = fast");
      setTimer(tPDC_Ramp, 1500); pdc_step = 2; break;

    case 2:  // Critical: 20 cm
      msg_USS_Rear.byte(0) = 0x14;
      msg_USS_Rear.byte(1) = 0x14;
      msg_USS_Rear.byte(2) = 0x14;
      msg_USS_Rear.byte(3) = 0x14;
      output(msg_USS_Rear);
      write("PDC: CRITICAL — 20 cm");
      write("Expected PDC_Rear_Zone = 4, Beep = continuous");
      write("PDC_Rear_Zone = %d", $PDC_Rear_Zone);
      write("PDC_AudioBeep_Rate = %d", $PDC_AudioBeep_Rate);
      pdc_step = 3; break;
  }
}
```

---

## 12. Dynamic CAN Message Injection Reference

### Converting Physical Values to CAN Raw Values

**Formula:**
```
raw_value = (physical_value - offset) / factor
```

**Common Signal Encoding Table:**

| Signal | Factor | Offset | Unit | Example |
|--------|--------|--------|------|---------|
| VehicleSpeed | 0.01 | 0 | km/h | 80 km/h → raw = 8000 = 0x1F40 |
| RadarDistance | 1 | 0 | cm | 500 cm → raw = 500 = 0x01F4 |
| RelativeSpeed | 0.1 | 0 | km/h signed | -30 km/h → raw = -300 = 0xFED4 |
| SteeringAngle | 0.1 | 0 | deg signed | -15° → raw = -150 = 0xFF6A |
| BrakeRequest | 1 | 0 | mbar | 150 mbar → 0x0096 |
| ThrottleRequest | 1 | 0 | % | 40% → 0x28 |
| LaneOffset | 1 | 0 | cm signed | +40 cm → 0x0028 |
| TTC | 1 | 0 | ms | 1500 ms → 0x05DC |

### CAPL Helper Function for Physical-to-Raw Conversion
```c
// Encode a 2-byte signed value into a message
void encodeInt16(message * msg, int bytePos, int rawValue) {
  msg.byte(bytePos)     = (rawValue >> 8) & 0xFF;  // high byte
  msg.byte(bytePos + 1) = rawValue & 0xFF;          // low byte
}

// Encode VehicleSpeed: physical km/h → raw (factor 0.01)
void setVehicleSpeed(float speed_kmh) {
  message 0x200 msg;
  int raw = (int)(speed_kmh * 100);
  encodeInt16(msg, 0, raw);
  output(msg);
}

// Encode Radar distance: cm → raw (factor 1)
void setRadarDistance(float dist_cm) {
  message 0x300 msg;
  int raw = (int)dist_cm;
  encodeInt16(msg, 0, raw);
  output(msg);
}
```

### Periodic Signal Injection (IG-equivalent CAPL)
```c
// Simulate periodic messages at correct cycle times
on timer tCyclic_10ms {
  output(msg_VehicleSpeed);  // 10 ms cycle
  output(msg_WheelSpeed);
  setTimer(tCyclic_10ms, 10);
}

on timer tCyclic_20ms {
  output(msg_RadarFwd);      // 20 ms cycle
  output(msg_RadarRear);
  setTimer(tCyclic_20ms, 20);
}

on timer tCyclic_100ms {
  output(msg_GearPos);       // 100 ms cycle
  output(msg_SteeringAngle);
  setTimer(tCyclic_100ms, 100);
}
```

---

## 13. DTC Codes — Root Cause Analysis

### Reading DTCs (UDS Service 0x19)

```
Request:  19 02 08        → ReadDTCInformation: reportDTCByStatusMask (confirmed)
Response: 59 02 08 [DTC1 3 bytes + status 1 byte] [DTC2 ...] ...

Request:  19 02 0F        → All DTCs (any status)
Request:  14 FF FF FF     → ClearAllDTCs
```

### CAPL: Read and Log All DTCs
```c
on key 'd' {
  diagRequest ADAS_ECU.ReadDTCByStatusMask req;
  req.StatusMask = 0x0F;  // All active DTCs
  diagSendRequest(req);
}

on diagResponse ADAS_ECU.ReadDTCByStatusMask {
  int i;
  write("=== Active DTCs ===");
  for (i = 0; i < this.numberOfDTCs; i++) {
    write("DTC[%d]: %06X  Status: %02X  Description: %s",
          i,
          this.DTC[i].DTCNumber,
          this.DTC[i].StatusByte,
          this.DTC[i].Description);
  }
}
```

### ADAS DTC Reference Table

#### BSD DTCs

| DTC Code | Description | Likely Root Cause | Resolution |
|----------|-------------|-------------------|------------|
| `C1501` | Left Rear Radar — No Communication | CAN bus open/short, radar power loss | Check CAN wiring, radar connector, 12V supply |
| `C1502` | Right Rear Radar — No Communication | Same as above, right side | Same |
| `C1503` | BSD Left Sensor Blocked | Mud/ice on radar lens | Clean sensor; check radar FOV mounting |
| `C1504` | BSD Right Sensor Blocked | Same | Same |
| `C1510` | BSD ECU Internal Fault | ECU software exception | Check SW logs; re-flash ECU |
| `C1511` | BSD Overvoltage | Supply > 16 V | Check PSU, alternator output |
| `C1512` | BSD Undervoltage | Supply < 9 V | Check battery, wiring resistance |

#### ACC DTCs

| DTC Code | Description | Likely Root Cause | Resolution |
|----------|-------------|-------------------|------------|
| `C1101` | Forward Radar — No Communication | CAN/Ethernet link failure | Check radar data bus; VN1640 channel mapping |
| `C1102` | Forward Radar Blocked | Sensor occlusion | Inspect radar grille; check mounting angle |
| `C1103` | Wheel Speed Sensor FL — Signal Implausible | ABS sensor fault or wiring | Check WSS signal via oscilloscope; replace sensor |
| `C1104` | Wheel Speed Sensor FR — Signal Implausible | Same | Same |
| `C1110` | ACC Actuator Fault — Throttle | ETC/E-gas communication fault | Check throttle actuator CAN node |
| `C1111` | ACC Actuator Fault — Brake | ESP/ABS communication fault | Check ESP response on CAN; check brake actuator |
| `C1115` | ACC Calibration Required | Radar misalignment after mechanical work | Run radar calibration procedure in EOL |
| `C1120` | ACC System Overheat | Prolonged high-load radar use | Cool down; check ECU thermal management |

#### LKA / LDW DTCs

| DTC Code | Description | Likely Root Cause | Resolution |
|----------|-------------|-------------------|------------|
| `C1201` | Camera — No Communication | Ethernet link down, camera power loss | Check 100BASE-T1 wiring; camera 12V |
| `C1202` | Camera Image Quality Degraded | Lens dirty, sun glare, fog | Clean lens; check auto-exposure calibration |
| `C1203` | EPS Communication Fault | LKA cannot send torque requests | Check EPS CAN node; verify EPS in enabled state |
| `C1204` | LKA Torque Request Rejected | EPS out of LKA-enabled mode | Check EPS status signal; confirm LKA handshake |
| `C1210` | Camera Calibration Required | Camera replaced or knocked | Run in-vehicle camera calibration target procedure |

#### FCW DTCs

| DTC Code | Description | Likely Root Cause | Resolution |
|----------|-------------|-------------------|------------|
| `C1301` | FCW Forward Radar Fault | Radar hardware failure | Swap radar; check CAN ID conflict |
| `C1302` | FCW Camera Fusion Mismatch | Sensor fusion disagreement > threshold | Check camera/radar synchronisation timestamps |
| `C1310` | FCW Warning Output Fault | Cluster/buzzer not responding | Check warning output pin, cluster CAN node |

#### DMS DTCs

| DTC Code | Description | Likely Root Cause | Resolution |
|----------|-------------|-------------------|------------|
| `C1601` | DMS Camera — No Communication | USB/Ethernet link fault | Check DMS camera connector and data link |
| `C1602` | DMS Infrared Illuminator Fault | LED driver failure | Check IR LED power supply; replace camera module |
| `C1603` | DMS Face Not Detected on Start | Camera blocked or mis-aimed | Check mounting angle; run DMS calibration |
| `C1610` | DMS Processing Fault | High CPU load / algorithm crash | Check ECU load; update firmware |

#### Parking Assistance DTCs

| DTC Code | Description | Likely Root Cause | Resolution |
|----------|-------------|-------------------|------------|
| `C1801` | USS Front Left — No Signal | Sensor wiring open/short | Check LIN bus connection to FL sensor |
| `C1802` | USS Front Centre Left — No Signal | Same | Same |
| `C1803` | USS Front Centre Right — No Signal | Same | Same |
| `C1804` | USS Front Right — No Signal | Same | Same |
| `C1811` | USS Rear Left — No Signal | Same, rear | Same |
| `C1812` | USS Rear Centre Left — No Signal | Same | Same |
| `C1813` | USS Rear Centre Right — No Signal | Same | Same |
| `C1814` | USS Rear Right — No Signal | Same | Same |
| `C1820` | PDC Buzzer Circuit Fault | Open circuit on buzzer output | Check buzzer wiring; measure resistance |
| `C1830` | APA Steering Request Rejected | EPS not in APA-enabled mode | Verify EPS approval signal; check APA handshake |
| `C1831` | APA Brake Request Rejected | ESP/ABS not responding to APA | Check ESP CAN and APA permission frame |

### DTC Status Byte Interpretation

```
Bit 7 (0x80): Warning Indicator Requested  — Illuminates MIL/warning lamp
Bit 6 (0x40): Test Not Completed Since Last Clear
Bit 5 (0x20): Test Failed Since Last Clear
Bit 4 (0x10): Test Not Completed This Cycle
Bit 3 (0x08): Confirmed DTC             — Set after fault present in ≥ N drive cycles
Bit 2 (0x04): Pending DTC               — Fault detected this cycle, not yet confirmed
Bit 1 (0x02): Test Failed This Cycle    — Current test run failure
Bit 0 (0x01): Test Passed               — Most recent test: pass
```

**Example:** DTC status `0x2F` = `0010 1111`
- Bit7=0: No lamp request
- Bit5=1: Failed since last clear
- Bit3=1: Confirmed
- Bit2=1: Pending (still failing)
- Bit1=1: Failed this cycle
- Bit0=1: Also passed (contradictory — may indicate intermittent fault)

---

## 14. Debugging Workflow

### Step-by-Step Debugging Approach

```
┌───────────────────────────────────────────────────────────────────┐
│ STEP 1: Reproduce the defect                                      │
│  - Run the exact test case that failed                            │
│  - Enable CANoe measurement logging (.blf)                        │
│  - Note the timestamp of the failure                              │
└───────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│ STEP 2: Read DTCs                                                 │
│  - UDS 0x19 02 0F → collect all DTCs + freeze frames             │
│  - Check DTC status bytes (confirmed vs pending)                  │
│  - Note freeze frame data (speed, temperature at time of fault)   │
└───────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│ STEP 3: Analyse measurement trace                                 │
│  - Load .blf in CANoe → go to failure timestamp                   │
│  - Check signal values: were inputs correct?                      │
│  - Check ECU output signals: did ECU respond correctly?           │
│  - Measure response latency: input change → output change         │
└───────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│ STEP 4: Isolate — Sensor / Communication / Logic / Actuator       │
│  Decision tree:                                                   │
│  ├── Missing input signal?  → Sensor/wiring fault                 │
│  ├── Input present, no ECU response? → ECU logic/state bug        │
│  ├── ECU responds, no actuator effect? → Actuator/bus fault       │
│  └── Timing issue? → Check cycle times, delays, debounce         │
└───────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│ STEP 5: Verify fix                                                │
│  - Request SW fix or bench workaround                             │
│  - Re-run full test case + regression of related features         │
│  - Confirm DTC cleared after fix and does not re-appear           │
└───────────────────────────────────────────────────────────────────┘
```

### Debugging Tools and Techniques

#### CANoe Trace Analysis
```
1. Open trace window → filter to relevant message IDs
2. Use "Trigger" function: trigger on message 0x3A0 (BSD output)
3. Use timeline to compare input timestamps vs output timestamps
4. Right-click signal → "Show in Graphics Window" for time-series plot
5. Use Statistics window to check message cycle time and gaps
```

#### Signal Plotter — Correlated View
```
Create a panel with:
- Row 1: RadarFwd_Distance (input)
- Row 2: FCW_TTC_ms (calculated)
- Row 3: FCW_VisualWarning (output)
- Cursor: mark fault timestamp

Look for: TTC reaching threshold but output NOT asserting
→ Indicates ECU logic bug (output not firing at threshold)
OR
TTC threshold crossed but output fires with wrong latency
→ Indicates timing/debounce configuration issue
```

#### CAPL Debugging Logger
```c
// Log all ADAS output signals with timestamps for post-analysis
on message 0x510 {  // FCW output
  write("[FCW @%dms] Visual=%d Audio=%d Haptic=%d TTC=%d ms",
        timeNow() / 100000,  // convert 100ns ticks to ms
        this.byte(0) & 0x01,
        (this.byte(0) >> 1) & 0x01,
        (this.byte(0) >> 2) & 0x01,
        (this.byte(1) | (this.byte(2) << 8)));
}

on message 0x3A0 {  // BSD output
  write("[BSD @%dms] L_Obj=%d R_Obj=%d L_Warn=%d R_Warn=%d",
        timeNow() / 100000,
        this.byte(0) & 0x01,
        (this.byte(0) >> 1) & 0x01,
        this.byte(1) & 0x01,
        (this.byte(1) >> 1) & 0x01);
}
```

#### UDS Extended Data Record (Freeze Frame)
```
Request:  19 04 [DTC 3 bytes] 01  → ReadDTCSnapshotRecordByDTCNumber
Example:  19 04 C1 10 1 01

Response contains: vehicle speed, voltage, temperature at time of fault
Use to correlate environmental conditions with fault occurrence
```

#### Electrical Fault Checks
```
Short to GND:    Measure pin voltage with multimeter — should be > 0 V
Open circuit:    Measure resistance — should be < 1 Ω for GND; > 10 kΩ for open
CAN voltage:     CANH = 2.75–3.5 V; CANL = 1.5–2.25 V during dominant bit
Bus impedance:   Measure between CANH/CANL with all power off = 60 Ω (two 120 Ω terminators)
```

#### State Machine Tracing
```
For ADAS features that have state machines (ACC: off/standby/active/override):
1. Enable ECU diagnostic logging if available (e.g., XCP/JTAG)
2. OR use known output signals to infer state transitions:
   - ACC_Status signal tracks state directly
3. Create state transition log in CAPL:
```
```c
variables { int acc_state_prev = -1; }

on message 0x502 {
  int acc_state_now = this.byte(0);
  if (acc_state_now != acc_state_prev) {
    write("[STATE CHANGE @%dms] ACC: %d → %d",
          timeNow()/100000,
          acc_state_prev,
          acc_state_now);
    acc_state_prev = acc_state_now;
  }
}
```

---

## 15. Defect Reporting Template

```markdown
## Defect Report

**ID:**          [Auto-assigned by JIRA]
**Title:**       [Feature]: [Short description of unexpected behaviour]
**Severity:**    Critical / Major / Minor / Cosmetic
**Priority:**    P1 / P2 / P3 / P4
**Component:**   BSD / ACC / LKA / LDW / FCW / BCW / DMS / PDC / APA
**SW Version:**  [ECU SW version, e.g., v2.3.1_build_4512]
**HW Variant:**  [Bench ID, ECU part number]
**Found Date:**  YYYY-MM-DD

---

### Environment
- CANoe version: 17.x
- DBC version:   <filename + version>
- Test case ID:  TC-XXX-00Y

### Preconditions
[List exact bench state, signal values, ECU mode before test]

### Steps to Reproduce
1. Step 1 description + CAN frame injected
2. Step 2 description
3. ...

### Expected Result
[Describe what SHOULD happen per requirements document / SRS section]

### Actual Result
[Describe what ACTUALLY happened — include signal values, timing]

### Attachments
- [ ] CANoe log file: YYYY-MM-DD_<feature>_<version>.blf
- [ ] Screenshot of Trace / Graphics window at failure timestamp
- [ ] DTC snapshot: DTCs active at time of failure
- [ ] CAPL write output log

### Root Cause (if known)
[Leave blank for developer; fill after analysis]

### Fix Verification
[To be completed by test engineer after fix is applied]
```

---

## 16. Glossary of Signal Abbreviations

| Abbreviation | Full Name |
|-------------|-----------|
| ACC | Adaptive Cruise Control |
| AEB | Automatic Emergency Braking |
| APA | Automatic Parking Assist |
| APS | Automatic Parking System |
| BCW | Blind Corner Warning / Cross Traffic Alert |
| BSD | Blind Spot Detection |
| CAN | Controller Area Network |
| CTA | Cross Traffic Alert |
| DBC | CAN Database file (.dbc) |
| DMS | Driver Monitoring System |
| DTC | Diagnostic Trouble Code |
| ECU | Electronic Control Unit |
| EPS | Electric Power Steering |
| ESP | Electronic Stability Program |
| FCW | Forward Collision Warning |
| FOV | Field of View |
| HIL | Hardware-in-the-Loop |
| IG | Interaction Generator (CANoe tool) |
| KL15 | Ignition-switched 12V supply (German: Klemme 15) |
| LDW | Lane Departure Warning |
| LIN | Local Interconnect Network |
| LKA | Lane Keep Assist |
| MIL | Malfunction Indicator Lamp |
| PDC | Parking Distance Control |
| PSU | Power Supply Unit |
| RCA | Root Cause Analysis |
| SIL | Software-in-the-Loop |
| TTC | Time to Collision |
| UDS | Unified Diagnostic Services (ISO 14229) |
| USS | Ultrasonic Sensor |
| WSS | Wheel Speed Sensor |
| XCP | Universal Measurement and Calibration Protocol |

---

## 17. ECU Software Flashing and Variant Coding

### 17.1 Why Flashing Matters for Test Engineers

Every new SW build delivered by the development team must be flashed to the bench ECU before
testing begins. Flashing errors, version mismatches, or missing variant coding are the #1 cause
of wasted test time at the start of a sprint.

### 17.2 UDS Flash Programming Sequence (ISO 14229-1)

```
Step  | Service | Request Frame           | Description
------|---------|-------------------------|--------------------------------------------
1     | 0x10    | 10 02                   | Enter Programming Session
2     | 0x27    | 27 01                   | SecurityAccess — Request Seed
3     | 0x27    | 27 02 [4-byte key]      | SecurityAccess — Send Key
4     | 0x31    | 31 01 FF 00             | RoutineControl — Erase Memory
5     | 0x34    | 34 00 44 [addr] [size]  | RequestDownload
6     | 0x36    | 36 [block#] [data...]   | TransferData (repeat for all blocks)
7     | 0x37    | 37                      | RequestTransferExit
8     | 0x31    | 31 01 FF 01             | RoutineControl — Check Programming
9     | 0x11    | 11 01                   | ECUReset — Hard Reset
10    | 0x10    | 10 01                   | Return to Default Session
11    | 0x22    | 22 F1 89                | Read SW version — confirm new build
```

### 17.3 Flashing with CANdela / CANoe Diagnostic Console

```
1. Open CANoe → Diagnostics → Diagnostic Console
2. Import ODX/PDX or CDD file for ADAS ECU
3. Select "Programming" tab
4. Browse to ECU hex file (.hex / .s19 / .srec)
5. Click "Program ECU" → workflow runs steps 1–11 automatically
6. Verify in Output window: "Programming successful"
7. Read 0x22 F1 89 — confirm SW version matches build notes
```

### 17.4 CAPL-based Flashing Trigger
```c
// Trigger flash from CAPL (for automation pipelines)
on key 'f' {
  diagRequest ADAS_ECU.ProgrammingSession req_prog;
  diagSendRequest(req_prog);
  write("Flash: Entered Programming Session");
}

on diagResponse ADAS_ECU.ProgrammingSession {
  if (this.isPositiveResponse()) {
    write("Flash: Programming session OK — proceed with Security Access");
  } else {
    write("Flash ERROR: Negative response 0x%02X", this.NRC);
  }
}
```

### 17.5 Variant Coding (Configuration Data)

Variant coding customises the ECU for a specific vehicle variant (market, trim level, optional
features). Without correct coding, features like BSD or APA may be disabled even if HW is present.

**Common Coding Parameters:**

| Parameter | Description | Example Values |
|-----------|-------------|----------------|
| `BSD_Equipped` | BSD HW present | 0=no, 1=yes |
| `ACC_MaxSpeed_kmh` | Market-specific speed cap | 130 (EU), 120 (CN) |
| `LKA_TorqueLimit_Nm` | Regulatory torque limit | 3.5 Nm (EU), 3.0 Nm (JP) |
| `DMS_Mandatory` | Mandated by regulation | 0=optional, 1=mandatory (EU GSR) |
| `APA_ParkType` | Supported parking types | 0x03 = parallel+perpendicular |
| `SpeedUnit` | Cluster display unit | 0=km/h, 1=mph |

**Write Variant Coding via UDS 0x2E:**
```
Request: 2E [DID_High] [DID_Low] [data bytes]
Example: 2E F1 80 01  → Write DID F180: BSD_Equipped = 1

CANoe: Diagnostics → Symbol Explorer → Coding → Write
```

**Read back to verify:**
```
Request: 22 F1 80
Response: 62 F1 80 01  → confirmed BSD_Equipped = 1
```

---

## 18. Test Case Design Methodology

### 18.1 Equivalence Partitioning (EP)

Divide input ranges into partitions where the ECU is expected to behave identically within each
partition. Test one value per partition — no need to test all values.

**Example — BSD Speed Threshold (activation at 20 km/h):**

| Partition | Range | Representative Value | Expected Behaviour |
|-----------|-------|---------------------|--------------------|
| Below threshold | 0–19 km/h | 10 km/h | BSD OFF |
| At threshold | 20 km/h | 20 km/h | BSD ON (boundary) |
| Active range | 21–200 km/h | 80 km/h | BSD fully active |

### 18.2 Boundary Value Analysis (BVA)

Always test the values immediately at, just below, and just above every threshold.

**Example — FCW TTC Warning Thresholds:**

| Threshold (TTC) | Test Value | Expected Output |
|----------------|------------|-----------------|
| Visual ON at 3.0 s | 3.1 s → 2.9 s | OFF → ON |
| Audio ON at 2.0 s | 2.1 s → 1.9 s | Visual only → Visual+Audio |
| Haptic ON at 1.2 s | 1.3 s → 1.1 s | V+A → V+A+Haptic |
| Hysteresis OFF at 3.5 s | 3.4 s → 3.6 s | ON → OFF |

### 18.3 State Transition Testing

Map all valid states and transitions. Every transition must have at least one test case.

**ACC State Transition Diagram:**
```
    ┌─────────────────────────────────────────────────────┐
    │                    OFF (0)                           │
    │   Entry: ECU boot or ignition OFF                   │
    └──────────┬──────────────────────────────────────────┘
               │ Driver presses SET/RES + valid conditions
               ▼
    ┌─────────────────────────────────────────────────────┐
    │                  STANDBY (1)                         │
    │   Speed within range; no target                     │
    └──────┬──────────────────────────────────────────────┘
           │ Target acquired or speed maintained
           ▼
    ┌─────────────────────────────────────────────────────┐
    │                   ACTIVE (2)                         │
    │   Throttle/brake control engaged                    │
    └──────┬─────────────────┬───────────────────────────┘
           │                 │
     Brake pressed      Gear → N/P/R
           │                 │
           ▼                 ▼
    ┌─────────────┐   ┌─────────────────┐
    │ OVERRIDE(3) │   │    OFF (0)       │
    │ → Standby   │   │  (hard cancel)  │
    └─────────────┘   └─────────────────┘

Transitions to test:
TC: OFF→STANDBY, STANDBY→ACTIVE, ACTIVE→OVERRIDE, OVERRIDE→STANDBY,
    ACTIVE→OFF (gear N), ACTIVE→OFF (speed < min), STANDBY→OFF (ignition)
```

### 18.4 Negative Testing (Out-of-Range Inputs)

Always test what happens when signals are outside their valid range.

| Input | Valid Range | Out-of-Range Test | Expected ECU Behaviour |
|-------|------------|-------------------|----------------------|
| VehicleSpeed | 0–250 km/h | 300 km/h raw | Signal invalid, DTC set, feature disabled |
| RadarDistance | 0–25000 cm | 0xFFFF (65535) | No-target condition, feature clears |
| LaneQuality | 0–15 | 16–255 | Treated as invalid; LKA → standby |
| DMS_EyeClosure | 0–100% | 150% raw | Clamp to max or flag as implausible |

### 18.5 Timing Tests

Verify response latency from input stimulus to ECU output.

**Timing test procedure in CANoe:**
```
1. Set up a Graphics window with:
   - Trigger signal (input — e.g., Radar_Rear_Left_Distance crosses threshold)
   - Response signal (output — e.g., BSD_Left_WarningActive)
2. Use "Cursor" tool: place cursor 1 at input rising edge, cursor 2 at output rising edge
3. Delta time between cursors = response latency
4. Compare against requirement (e.g., "BSD warning within 300 ms")
5. Record in test log with screenshot
```

**CAPL timing measurement:**
```c
variables {
  dword t_InputRise;
  dword t_OutputRise;
}

on signal Radar_Rear_Left_Distance {
  if (this < 350) {  // Threshold crossed: target entered zone
    t_InputRise = timeNow() / 100000;  // ms
    write("[TIMING] Input trigger at %d ms", t_InputRise);
  }
}

on signal BSD_Left_WarningActive {
  if (this == 1) {
    t_OutputRise = timeNow() / 100000;
    write("[TIMING] Output asserted at %d ms — Latency = %d ms",
          t_OutputRise, t_OutputRise - t_InputRise);
    if ((t_OutputRise - t_InputRise) > 300) {
      write("[FAIL] Latency %d ms exceeds 300 ms requirement!",
            t_OutputRise - t_InputRise);
    } else {
      write("[PASS] Latency within requirement");
    }
  }
}
```

### 18.6 Test Case ID Naming Convention

```
TC-[FEATURE]-[NUMBER]-[VARIANT]

Feature codes:
  BSD  = Blind Spot Detection
  ACC  = Adaptive Cruise Control
  LKA  = Lane Keep Assist
  LDW  = Lane Departure Warning
  FCW  = Forward Collision Warning
  BCW  = Blind Corner Warning
  DMS  = Driver Monitoring System
  PDC  = Parking Distance Control
  APA  = Automatic Parking Assist

Examples:
  TC-BSD-001       = First BSD test case
  TC-ACC-003-NEG   = Third ACC negative/out-of-range test
  TC-FCW-002-BVA   = Second FCW boundary value test
  TC-LKA-005-REG   = Fifth LKA regression test
```

---

## 19. vTestStudio Automated Test Framework

### 19.1 Project Structure

```
vTestStudio Project (.vtp)
├── Test Modules/
│   ├── BSD_Tests.vtm        — all BSD automated test cases
│   ├── ACC_Tests.vtm
│   ├── LKA_LDW_Tests.vtm
│   ├── FCW_Tests.vtm
│   ├── DMS_Tests.vtm
│   └── PDC_APA_Tests.vtm
├── Test Units/
│   ├── CAPL_Stimulation.cte — signal stimulation library
│   └── Verdict_Checks.cte   — pass/fail evaluation helpers
├── Sequences/
│   ├── Smoke_Test.vseq      — 15 min quick sanity
│   ├── Full_Regression.vseq — complete suite ~8 hours
│   └── Feature_BSD.vseq     — BSD-only run
└── Reports/
    └── output/              — auto-generated HTML + XML
```

### 19.2 Creating a Test Module (vTestStudio CAPL)

**Test module structure:**
```c
// BSD_Tests.vtm — Test Module
// Runs as part of vTestStudio test execution

#include "CAPL_Stimulation.cte"

testcase TC_BSD_001_TargetDetected() {
  // Arrange
  setVehicleSpeed(80.0);
  setRadarRearLeft(350);  // within zone
  TestWaitForTimeout(200);

  // Assert
  if ($BSD_Left_ObjectDetected == 1 && $BSD_Left_WarningActive == 1) {
    TestStepPass("TC-BSD-001", "Left blind spot warning active as expected");
  } else {
    TestStepFail("TC-BSD-001",
      "Expected BSD warning. Got: ObjectDetected=%d WarningActive=%d",
      $BSD_Left_ObjectDetected, $BSD_Left_WarningActive);
  }

  // Teardown
  setRadarRearLeft(0x7FFF);
  TestWaitForTimeout(100);
}

testcase TC_BSD_003_BelowSpeedThreshold() {
  setVehicleSpeed(15.0);
  setRadarRearLeft(200);
  TestWaitForTimeout(300);

  if ($BSD_Left_WarningActive == 0) {
    TestStepPass("TC-BSD-003", "No BSD warning below speed threshold — correct");
  } else {
    TestStepFail("TC-BSD-003", "BSD warning active below threshold — FAIL");
  }
  setRadarRearLeft(0x7FFF);
}

testcase TC_ACC_001_SpeedHold() {
  float speed_initial, speed_t10s;
  setVehicleSpeed(100.0);
  enableACC(100, 2);  // setSpeed=100, timeGap=2
  setRadarFwd(0xFFFF);  // no lead vehicle
  TestWaitForTimeout(10000);  // 10 seconds

  speed_t10s = $VehicleSpeed / 100.0;
  if (abs(speed_t10s - 100.0) <= 2.0) {
    TestStepPass("TC-ACC-001", "Speed held within ±2 km/h: actual=%.1f km/h", speed_t10s);
  } else {
    TestStepFail("TC-ACC-001", "Speed deviation too large: %.1f km/h", speed_t10s);
  }
  disableACC();
}
```

### 19.3 Verdict Configuration

```
In vTestStudio:
1. Select test case node → Properties → Verdict
2. Set:
   - PASS condition:  TestStepPass() called with no preceding fail
   - FAIL condition:  TestStepFail() called OR timeout
   - INCONCLUSIVE:    TestStepInconclusive() — DUT not ready, skip
3. Timeout per test case: set in test module Properties → Timeout
   Recommended: feature complexity × 5 = safety margin
   BSD: 2000 ms; ACC: 15000 ms; APA: 120000 ms
```

### 19.4 Running Tests and Viewing Results

```
1. Select sequence in Sequences panel
2. Click Run (▶)
3. Monitor real-time progress in Execution panel
4. View results:
   - Green = PASS
   - Red = FAIL
   - Yellow = INCONCLUSIVE
5. After run: File → Generate Report → HTML report auto-saved to Reports/output/
6. Open HTML report — shows:
   - Test summary (pass/fail counts)
   - Per-test case: verdict, steps, timing, CAPL write output
   - Test run metadata (SW version, date, engineer)
```

### 19.5 CI/CD Integration

```yaml
# Jenkins pipeline example — run vTestStudio tests on new ECU build
pipeline:
  stages:
    - flash_ecu:
        command: python flash_ecu.py --hex builds/latest.hex
        timeout: 300

    - smoke_test:
        command: VTESTstudio.exe -project ADAS_Tests.vtp
                                 -sequence Smoke_Test.vseq
                                 -report reports/smoke_${BUILD_NUMBER}.html
        timeout: 1200
        on_failure: abort

    - regression:
        command: VTESTstudio.exe -project ADAS_Tests.vtp
                                 -sequence Full_Regression.vseq
                                 -report reports/regression_${BUILD_NUMBER}.html
        timeout: 32400  # 9 hours
        on_failure: notify_jira

    - publish_report:
        command: python upload_results.py --report reports/
```

---

## 20. Python Automation Scripts

### 20.1 python-can: Sending CAN Messages

```python
# requirements: pip install python-can
import can
import time
import struct

# Configure Vector VN1640A interface
bus = can.interface.Bus(
    bustype='vector',
    app_name='PythonCAN',
    channel=0,
    bitrate=500000
)

def send_vehicle_speed(speed_kmh: float):
    """Send VehicleSpeed on 0x200 with factor 0.01."""
    raw = int(speed_kmh * 100)
    data = [
        (raw >> 8) & 0xFF,
        raw & 0xFF,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00
    ]
    msg = can.Message(arbitration_id=0x200, data=data, is_extended_id=False)
    bus.send(msg)

def send_radar_fwd(distance_cm: int, rel_speed_kmh: float):
    """Send forward radar data on 0x300."""
    dist_raw = distance_cm
    rel_raw = int(rel_speed_kmh * 10)
    rel_bytes = struct.pack('>h', rel_raw)  # signed big-endian 16-bit
    data = [
        (dist_raw >> 8) & 0xFF,
        dist_raw & 0xFF,
        rel_bytes[0],
        rel_bytes[1],
        0x01,  # ObjectValid = 1
        0x00, 0x00, 0x00
    ]
    msg = can.Message(arbitration_id=0x300, data=data, is_extended_id=False)
    bus.send(msg)

def send_gear(gear: int):
    """GearPosition: 0=P, 1=R, 2=N, 3=D."""
    msg = can.Message(arbitration_id=0x210,
                      data=[gear, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                      is_extended_id=False)
    bus.send(msg)

def enable_acc(set_speed_kmh: float, time_gap: int = 2):
    """Enable ACC with given set speed."""
    speed_raw = int(set_speed_kmh * 10)
    data = [
        (speed_raw >> 8) & 0xFF,
        speed_raw & 0xFF,
        0x01,         # ACC_Enable = 1
        time_gap,
        0x00, 0x00, 0x00, 0x00
    ]
    msg = can.Message(arbitration_id=0x410, data=data, is_extended_id=False)
    bus.send(msg)
```

### 20.2 pytest Test Case — ACC Speed Hold

```python
# test_acc.py
import pytest
import can
import time
from can_helpers import send_vehicle_speed, send_gear, enable_acc, send_radar_fwd

@pytest.fixture(scope="module")
def can_bus():
    bus = can.interface.Bus(bustype='vector', app_name='pytest',
                             channel=0, bitrate=500000)
    yield bus
    bus.shutdown()

class TestACC:

    def test_TC_ACC_001_speed_hold(self, can_bus):
        """TC-ACC-001: ACC maintains set speed ±2 km/h for 10 s with no lead vehicle."""
        # Setup
        send_gear(3)                    # Drive
        send_vehicle_speed(100.0)
        send_radar_fwd(0xFFFF, 0)       # No target
        time.sleep(0.5)
        enable_acc(100.0, 2)
        time.sleep(10.0)                # Let ACC run

        # Read ACC_Status and speed
        speed_samples = []
        deadline = time.time() + 2.0
        while time.time() < deadline:
            msg = can_bus.recv(timeout=0.05)
            if msg and msg.arbitration_id == 0x502:
                acc_status = msg.data[0]
                assert acc_status == 2, f"ACC_Status={acc_status}, expected 2 (active)"
            if msg and msg.arbitration_id == 0x200:
                raw = (msg.data[0] << 8) | msg.data[1]
                speed_samples.append(raw / 100.0)

        assert speed_samples, "No VehicleSpeed messages received"
        avg_speed = sum(speed_samples) / len(speed_samples)
        assert abs(avg_speed - 100.0) <= 2.0, \
            f"Speed deviation too large: {avg_speed:.1f} km/h"

    def test_TC_ACC_002_cut_in_deceleration(self, can_bus):
        """TC-ACC-002: ACC decelerates when lead vehicle cuts in close."""
        # Precondition: ACC active at 100 km/h
        send_vehicle_speed(100.0)
        enable_acc(100.0)
        time.sleep(1.0)

        # Inject lead vehicle: 20 m away, -30 km/h relative speed
        send_radar_fwd(2000, -30.0)
        time.sleep(0.5)  # Allow ECU to react

        # Verify brake request is positive
        brake_applied = False
        deadline = time.time() + 0.5
        while time.time() < deadline:
            msg = can_bus.recv(timeout=0.05)
            if msg and msg.arbitration_id == 0x501:
                brake_mbar = (msg.data[0] << 8) | msg.data[1]
                if brake_mbar > 0:
                    brake_applied = True
                    break

        assert brake_applied, "No brake request from ACC after lead vehicle cut-in"

    def test_TC_ACC_003_driver_override(self, can_bus):
        """TC-ACC-003: Brake override cancels ACC."""
        enable_acc(80.0)
        time.sleep(0.5)
        # Press brake
        msg = can.Message(arbitration_id=0x210,
                          data=[0x03, 0x01, 0, 0, 0, 0, 0, 0],
                          is_extended_id=False)
        can_bus.send(msg)
        time.sleep(0.2)

        # ACC_Status must be 3 (override)
        deadline = time.time() + 0.3
        while time.time() < deadline:
            rx = can_bus.recv(timeout=0.05)
            if rx and rx.arbitration_id == 0x502:
                assert rx.data[0] == 3, \
                    f"ACC_Status={rx.data[0]}, expected 3 (override)"
                return
        pytest.fail("No ACC_Status update received after brake press")
```

### 20.3 DTC Reader Script

```python
# dtc_reader.py — Read and report all active DTCs via python-can + UDS
import can
import time

bus = can.interface.Bus(bustype='vector', app_name='DTC_Reader',
                         channel=0, bitrate=500000)
ADAS_ECU_TX_ID = 0x700  # Tester → ECU
ADAS_ECU_RX_ID = 0x708  # ECU → Tester (response)

def send_uds(service_bytes: list) -> list:
    """Send UDS request and return response data bytes."""
    # Single-frame: length byte + service bytes
    data = [len(service_bytes)] + service_bytes + [0xCC] * (7 - len(service_bytes))
    tx = can.Message(arbitration_id=ADAS_ECU_TX_ID, data=data, is_extended_id=False)
    bus.send(tx)
    deadline = time.time() + 0.5
    while time.time() < deadline:
        rx = bus.recv(timeout=0.1)
        if rx and rx.arbitration_id == ADAS_ECU_RX_ID:
            return list(rx.data)
    return []

def read_all_dtcs():
    # Enter Extended Session
    send_uds([0x10, 0x03])
    time.sleep(0.05)

    # Service 0x19 0x02 0x0F — read all DTCs
    resp = send_uds([0x19, 0x02, 0x0F])
    if not resp or resp[1] != 0x59:
        print("ERROR: No positive response to ReadDTCInformation")
        return

    print(f"\n{'='*60}")
    print("  ADAS ECU Active DTCs")
    print(f"{'='*60}")

    # Parse response: each DTC is 4 bytes (3-byte DTC + 1-byte status)
    dtc_bytes = resp[4:]  # skip length, service ID, subfunction, status mask
    num_dtcs = len(dtc_bytes) // 4
    if num_dtcs == 0:
        print("  No active DTCs found.")
    else:
        for i in range(num_dtcs):
            offset = i * 4
            dtc_code = (dtc_bytes[offset] << 16) | \
                       (dtc_bytes[offset+1] << 8) | \
                        dtc_bytes[offset+2]
            status   = dtc_bytes[offset+3]
            confirmed = "CONFIRMED" if status & 0x08 else "PENDING"
            print(f"  DTC #{i+1}: {dtc_code:06X}  Status: {status:02X}  [{confirmed}]")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    read_all_dtcs()
    bus.shutdown()
```

---

## 21. Fault Injection Testing

### 21.1 Why Fault Injection?

Fault injection validates that the ECU detects failures gracefully, sets the correct DTCs, limits
feature functionality safely, and recovers when the fault is removed. Required for ISO 26262
ASIL-rated ADAS functions.

### 21.2 Electrical Fault Injection Methods

**Method 1: Manual wiring faults (bench)**
```
Short to GND:    Connect CAN signal pin directly to GND using a jumper wire
Short to VBAT:   Connect CAN signal pin to +12 V rail
Open circuit:    Disconnect connector pin while ECU is powered
                 ⚠ Always confirm ECU can survive the fault before bench-level injection
```

**Method 2: dSPACE Fault Injection Module (FIU)**
```
Hardware: DS2680 Fault Injection Board installed in SCALEXIO rack
ControlDesk → FIU tab → select signal → set fault type:
  - Short to GND
  - Short to VCC
  - Open (high impedance)
  - Intermittent (toggling at set frequency)
Duration: set fault duration (100 ms, 500 ms, continuous)
```

### 21.3 Software Fault Injection via CAN

Inject invalid or missing signals to test ECU's internal plausibility checks.

**TC-FI-BSD-001: Radar CAN Message Timeout**
```
Step 1: BSD active (TC-BSD-001 precondition)
Step 2: Stop sending Radar_Rear_Left (0x3B0) — suppress message in CANoe
        CANoe: IG window → right-click 0x3B0 → "Stop Sending"
Step 3: Wait 150 ms (expected timeout detection window)
Step 4: Verify:
        DTC C1501 (Radar Left — No Communication) = PENDING
        BSD_SystemStatus = 0 (feature disabled due to sensor loss)
        BSD_Left_WarningActive = 0 (no false warning)
Step 5: Resume sending 0x3B0
Step 6: Verify DTC goes to HEALED; BSD recovers within 1 s
Pass Criteria: DTC set within timeout window; feature disables safely; recovers after fault
```

**TC-FI-ACC-001: Implausible Wheel Speed**
```
Step 1: ACC active at 80 km/h
Step 2: Inject implausible wheel speed: FL=80, FR=80, RL=120, RR=80
        (RL is 40 km/h higher — physically impossible for straight driving)
        CAN 0x201: inject RL raw = 12000 while others = 8000
Step 3: Verify:
        DTC C1103 or C1104 (WSS implausible) set
        ACC_Status = 0 or 1 (feature disabled/standby due to sensor plausibility failure)
Pass Criteria: Implausible WSS causes safe ACC disable; correct DTC logged
```

**TC-FI-LKA-001: EPS Communication Loss**
```
Step 1: LKA active
Step 2: Suppress EPS status message on CAN
Step 3: Verify:
        DTC C1203 (EPS Communication Fault) set
        LKA_Status = 0 (disabled) within 200 ms
        LKA_TorqueRequest = 0 (ECU stops sending torque requests to absent EPS)
Pass Criteria: LKA disables safely; steering is NOT autonomously commanded without EPS feedback
```

### 21.4 Fault Injection Test Log Template

```
TC ID:         TC-FI-[FEATURE]-[NUMBER]
Fault Type:    [Open / Short GND / Short VBAT / CAN timeout / Implausible signal]
Signal/Wire:   [Signal name, message ID, or physical pin]
Duration:      [e.g., 500 ms / continuous]

Pre-fault state:
  - Feature status: ___
  - All DTCs: None / [list]

During fault:
  - DTC set: ___ (time to set from fault injection: ___ ms)
  - Feature response: ___
  - Any unsafe output? Yes/No: ___

Post-fault recovery:
  - Fault removed at: ___ ms
  - Feature recovery time: ___ ms
  - DTC healed: Yes/No (time: ___ ms)
  - Any residual effects: ___

Verdict: PASS / FAIL / INCONCLUSIVE
```

---

## 22. LIN Bus Testing for Ultrasonic Sensors

### 22.1 LIN Architecture for Parking Sensors

USS (Ultrasonic Sensors) in modern vehicles are typically connected via LIN bus to the parking
ECU. The ECU acts as LIN Master; each sensor is a LIN Slave.

```
Parking ECU (LIN Master)
     │
     ├── USS_FL (ID: 0x01)   — Front Left
     ├── USS_FCL (ID: 0x02)  — Front Centre Left
     ├── USS_FCR (ID: 0x03)  — Front Centre Right
     ├── USS_FR (ID: 0x04)   — Front Right
     ├── USS_RL (ID: 0x05)   — Rear Left
     ├── USS_RCL (ID: 0x06)  — Rear Centre Left
     ├── USS_RCR (ID: 0x07)  — Rear Centre Right
     └── USS_RR (ID: 0x08)   — Rear Right
```

### 22.2 LIN Frame Structure

```
  Break Field (min 13 bit-times)
  Sync Byte (0x55)
  Protected Identifier (PID) = ID | parity bits
  Data Bytes (1–8 bytes)
  Checksum (classic or enhanced)
```

**USS LIN Response Frame (Sensor → Master):**
```
PID: 0x81 (ID 0x01 = USS_FL, parity=10)
Data[0]: Distance high byte (cm)
Data[1]: Distance low byte
Data[2]: Status (0x00 = OK, 0x01 = blocked, 0x02 = fault)
Data[3]: Temperature compensation factor
Checksum: 0x[calculated]
```

### 22.3 CANoe LIN Monitoring Setup

```
1. CANoe → Hardware → Assign LIN channel:
   - Channel 3 → LIN1, baud = 19200, LDF file = USS_Network.ldf
2. Load LDF database → signal definitions auto-loaded
3. Start measurement → LIN Trace shows all USS frames
4. Statistics window: verify master sends schedule at correct rate (e.g., 10 ms/sensor)
```

### 22.4 Simulating USS Sensor in CAPL (LIN Slave Simulation)

```c
// Simulate USS_FL returning distance = 80 cm
on linMessage 0x81 {  // Master polls USS_FL
  linFrame 0x81 resp;
  resp.byte(0) = 0x00;  // Distance high = 0
  resp.byte(1) = 0x50;  // Distance low = 80 cm (0x0050)
  resp.byte(2) = 0x00;  // Status = OK
  resp.byte(3) = 0x40;  // Temperature factor = 64
  linSendResponse(resp);
}
```

### 22.5 LIN Bus Fault Tests

| Fault | How to Inject | Expected DTC | Recovery |
|-------|--------------|--------------|----------|
| Sensor disconnect | Suppress LIN response for PID 0x81 | C1801 (USS_FL No Signal) | Reconnect → heal |
| Wrong checksum | Send frame with inverted checksum | C1801 (comm error) | Correct frame → heal |
| Sensor blocked | Return distance = 0 (blocked status byte = 0x01) | C1803 (blocked) | Clear obstruction |
| Bus short to GND | Hardware short | All USS DTCs + C1820 | Remove short |

---

## 23. Automotive Ethernet (100BASE-T1) Testing for Camera ECU

### 23.1 Overview

Front camera (for LKA/LDW/FCW) and sometimes radar ECUs communicate via Automotive Ethernet
(100BASE-T1, single unshielded twisted pair). The ADAS ECU receives camera data as:
- **SOME/IP** service messages (signal data, status)
- **Raw Ethernet frames** with AUTOSAR-defined PDUs

### 23.2 CANoe Ethernet Setup

```
1. CANoe → Hardware → Ethernet Channels:
   - Assign dSPACE DS6601 or VN5610A to Ethernet channel
   - Set network: 100BASE-T1, speed = 100 Mbps
2. Load ARXML / Fibex database for SOME/IP service definitions
3. Load IP assignment: Camera = 169.254.x.x / ADAS ECU = 169.254.x.y
4. Start measurement → Ethernet Trace shows all IP traffic
```

### 23.3 Key Ethernet Frames for Camera

| Service | SOME/IP Service ID | Method/Event ID | Data |
|---------|--------------------|-----------------|------|
| Lane Detection | 0x0101 | Event 0x8001 | LaneOffset, Curvature, Quality |
| Object List | 0x0102 | Event 0x8002 | Up to 32 objects: class, distance, speed |
| Camera Status | 0x0103 | Event 0x8003 | BlockedFlag, CalibrationStatus |
| FCW Target | 0x0104 | Event 0x8004 | TTC, ObjectClass, Confidence |

### 23.4 Simulating Camera via CAPL Ethernet Node

```c
// CANoe Ethernet node — simulate camera sending lane data
on start {
  setTimer(tCamera_Send, 33);  // 30 fps ≈ 33 ms
}

on timer tCamera_Send {
  // Build SOME/IP frame for LaneDetection service
  byte payload[12];
  int offset_cm = 15;   // +15 cm right of centre
  int curv = 50;        // mild right curve
  int quality = 12;     // good quality

  payload[0]  = (offset_cm >> 8) & 0xFF;
  payload[1]  = offset_cm & 0xFF;
  payload[2]  = (curv >> 8) & 0xFF;
  payload[3]  = curv & 0xFF;
  payload[4]  = quality;
  payload[5]  = 0x00;   // blocked = 0
  payload[6]  = 0x01;   // calibrated = 1

  EthSendFrame(0x0101, 0x8001, payload, elcount(payload));
  setTimer(tCamera_Send, 33);
}
```

### 23.5 Ethernet Health Checks

```
[ ] Ping camera IP from CANoe: ping 169.254.x.x → response < 5 ms
[ ] SOME/IP service discovery: verify camera publishes lane service
[ ] Frame rate: camera events arriving at 30 Hz ±2 Hz
[ ] Jitter: max inter-frame gap < 50 ms (frame loss detection threshold)
[ ] Error check: no CRC errors in Ethernet Statistics window
```

---

## 24. XCP Calibration and Measurement During Testing

### 24.1 What is XCP?

XCP (Universal Measurement and Calibration Protocol) allows the test engineer to:
- **Read internal ECU variables** (not visible on CAN) in real time
- **Modify calibration parameters** (thresholds, gains) without flashing
- Useful for debugging and for temporary parameter exploration during testing

### 24.2 XCP Setup in CANoe

```
1. CANoe → Tools → ASAP3 / XCP
2. Load A2L file: ADAS_ECU.a2l (contains all internal variable definitions)
3. Assign XCP master interface: CAN channel 1, XCP master address
4. Connect: CANoe → XCP → Connect → ECU acknowledges
5. Configure DAQ (Data Acquisition) list:
   - Add variables: ACC_InternalSpeed, LKA_TorqueCalc, FCW_TTC_Internal
   - Set ODT rate: 10 ms
6. Start measurement → XCP variables appear in Signal Panel
```

### 24.3 Key Internal Variables to Monitor During Testing

| Variable Name (A2L) | Feature | What it Shows |
|--------------------|---------|---------------|
| `acc_ctrl_throttle_pct` | ACC | Internal throttle command before actuator |
| `acc_ctrl_brake_mbar` | ACC | Internal brake command |
| `acc_target_dist_cm` | ACC | ECU's estimate of lead vehicle distance |
| `lka_lane_offset_filtered` | LKA | Post-filter lane offset (may differ from raw input) |
| `lka_torque_cmd_Nm` | LKA | Final torque command before EPS send |
| `fcw_ttc_internal_ms` | FCW | Internal TTC calculation |
| `fcw_warning_state` | FCW | Internal warning state machine |
| `dms_eye_closure_filtered` | DMS | Post-filter eye closure % |
| `dms_drowsiness_score` | DMS | Internal drowsiness accumulator |
| `pdc_zone_rear` | PDC | Internal zone classifier output |

### 24.4 Calibration Parameter Modification (Temporary)

```
Use case: SRS says FCW visual warning threshold = 3.0 s TTC.
          ECU seems to trigger at 2.7 s — suspected miscalibration.

Step 1: In A2L / INCA, find parameter: fcw_warn_visual_ttc_s
        Current value: 2700 ms (raw = 2700 × factor)

Step 2: In CANoe XCP or INCA: modify value to 3000 ms

Step 3: Re-run TC-FCW-001 → confirm warning now occurs at 3.0 s TTC

Step 4: Log the parameter change as a calibration deviation in test report

Step 5: Raise calibration change request to development team
        DO NOT release SW without the parameter being officially updated
```

---

## 25. Regression Testing Strategy

### 25.1 Three-Tier Regression Model

```
TIER 1 — SMOKE TEST (run on every build)
  Duration: ~15 minutes
  Coverage: 1 happy-path test per feature (8 tests total)
  Purpose:  Confirm basic feature functionality; gate for further testing
  Pass gate: 8/8 PASS → proceed to Tier 2

TIER 2 — TARGETED REGRESSION (run on builds with significant changes)
  Duration: ~2 hours
  Coverage: All test cases for changed features + direct dependencies
  Purpose:  Verify changed features work; no side-effects on connected features
  Pass gate: ≥ 95% PASS → accepted for integration

TIER 3 — FULL REGRESSION (run before every release candidate)
  Duration: ~8 hours (overnight)
  Coverage: 100% of defined test cases across all features
  Purpose:  Full confidence for software release
  Pass gate: 100% PASS (zero open P1/P2 defects)
```

### 25.2 Feature Dependency Matrix

When a feature changes, also run regression for all dependent features:

| Changed Feature | Must Also Regression Test |
|----------------|--------------------------|
| VehicleSpeed signal | ACC, BSD, LKA, LDW, FCW, BCW, PDC |
| Forward Radar | ACC, FCW |
| Rear Radar | BSD, BCW |
| Camera (lane) | LKA, LDW |
| EPS interface | LKA, APA |
| USS sensors | PDC, APA |
| DMS camera | DMS only (isolated) |
| UDS/Diagnostics | All DTC tests |

### 25.3 Regression Test Prioritisation (Risk-Based)

Score each test case: **Priority = Severity × Change Risk**

```
Severity:    3=Safety-critical, 2=Functional, 1=HMI/cosmetic
Change Risk: 3=Directly in changed code, 2=Indirect dependency, 1=No overlap

Priority ≥ 6: Run first (safety-critical + directly changed)
Priority 4–5: Run in main regression wave
Priority 1–3: Run in full regression only
```

### 25.4 Regression Pass/Fail Criteria

```
Status          | Criteria
----------------|-------------------------------------------------------------
PASS (release)  | All safety-critical TCs pass; zero P1/P2 open defects
CONDITIONAL     | ≤ 3 P3 defects open with approved workaround
BLOCKED         | Any P1 safety-critical failure → stop, raise to dev team
FAILED          | Any P2 functional regression on previously passing feature
```

---

## 26. Test Metrics and Coverage Reporting

### 26.1 Key Performance Indicators (KPIs)

Track these metrics in your test management tool (JIRA, HP ALM, TestRail):

| Metric | Formula | Target |
|--------|---------|--------|
| Test Execution Rate | Tests run / Tests planned × 100 | ≥ 95% per sprint |
| Pass Rate | Tests passed / Tests run × 100 | ≥ 90% (regression) |
| Defect Density | Open defects / KLOC | Track trend (lower = better) |
| DTC Detection Rate | DTCs validated / DTCs defined × 100 | 100% |
| Requirement Coverage | Requirements with ≥1 TC / Total reqs × 100 | 100% |
| Regression Stability | % of passing tests that stay passing sprint-over-sprint | ≥ 98% |
| Mean Time to Detect | Avg time from SW merge to defect found | Minimise |

### 26.2 Daily Status Report Template

```
ADAS Test Daily Status — [DATE] — [Engineer Name]

SW Build Under Test: v[X.Y.Z]_build_[NNNN]
Bench ID: ADAS-HIL-Bench-02

EXECUTION SUMMARY
  Planned today:    [N] test cases
  Executed:         [N] test cases
  PASS:             [N]  ([%])
  FAIL:             [N]  ([%])
  BLOCKED:          [N]  (reason: ___)
  INCONCLUSIVE:     [N]  (reason: ___)

NEW DEFECTS LOGGED TODAY
  P1: [N]  — [brief description]
  P2: [N]
  P3: [N]

DEFECTS CLOSED TODAY
  [JIRA-ID]: [feature] — [brief description of fix verified]

OPEN BLOCKERS
  [describe any bench issues, tool issues, or SW blockers]

PLAN FOR TOMORROW
  [list test cases planned]
```

### 26.3 Requirements Traceability Matrix (RTM) — Excel Structure

```
Column A: Requirement ID        (e.g., SRS-BSD-001)
Column B: Requirement Text      (brief description)
Column C: ASIL Level            (QM / A / B / C / D)
Column D: Test Case IDs         (e.g., TC-BSD-001, TC-BSD-003)
Column E: Test Status           (Not Run / Pass / Fail / Blocked)
Column F: Last Run Date
Column G: SW Version Tested
Column H: Linked Defect         (JIRA ID if failing)
Column I: Coverage %            (auto-calculated)
```

**Coverage formula (Excel):**
```excel
=COUNTIF(E2:E100,"Pass") / COUNTA(A2:A100) * 100
```

---

## 27. Requirements Traceability

### 27.1 Requirement Sources

| Document | Content | Tool |
|----------|---------|------|
| System Requirements Spec (SRS) | Top-level feature requirements | DOORS NG |
| Software Requirements Spec (SWRS) | SW-level signal thresholds, timing | DOORS NG |
| FMEA / FMEDA | Safety-relevant fault behaviour | Excel / PTC Integrity |
| AUTOSAR Software Component Description | Signal interfaces | Enterprise Architect |
| Test Plan | Test strategy and scope decisions | Confluence |

### 27.2 Tracing a Test Case to Requirement — Example

```
SRS Requirement:
  ID:   SRS-BSD-004
  Text: "The BSD system shall activate a visual warning in the corresponding
         door mirror indicator within 300 ms of a target entering the blind zone
         while vehicle speed ≥ 20 km/h."

Derived Test Cases:
  TC-BSD-001: Target in left blind spot → warning within 300 ms  (functional)
  TC-BSD-003: Speed < 20 km/h → no warning                      (boundary)
  TC-BSD-TIM-001: Latency measurement: input to output ≤ 300 ms (timing)

DOORS NG Link:
  SRS-BSD-004 ← [Satisfies] → TC-BSD-001, TC-BSD-003, TC-BSD-TIM-001

Coverage report in DOORS:
  All three TCs = PASS → SRS-BSD-004 is VERIFIED
```

### 27.3 Handling Untraceable Tests

If a test case has no matching requirement:
1. Check if it tests an implicit requirement (standard behaviour)
2. If yes → raise a CR (Change Request) to add the requirement to SRS
3. If no → mark test case as "exploratory" — does not count toward coverage

---

## 28. ISO 26262 Functional Safety Considerations for Test Engineers

### 28.1 ASIL Levels and Their Impact on Testing

| ASIL | Description | Testing Implication |
|------|-------------|---------------------|
| QM | Quality Management — no functional safety | Standard testing |
| A | Lowest safety integrity | Basic fault detection tests |
| B | Medium integrity | DTC tests + plausibility checks mandatory |
| C | High integrity | All fault paths tested; independence of verification required |
| D | Highest safety integrity | Full fault injection suite; formal review of test results |

**ADAS Feature ASIL Examples:**
```
FCW (Forward Collision Warning) — ASIL B (warning only)
AEB (Automatic Emergency Braking) — ASIL C or D (autonomous braking)
LKA (torque > 3 Nm) — ASIL B
DMS (drowsiness warning) — ASIL A
BSD (warning only) — QM
PDC (proximity warning) — QM
APA (autonomous steering/braking) — ASIL B
```

### 28.2 Safety-Relevant Test Cases

For any ASIL-rated feature, the following must be tested and documented:

**1. Safe State Verification**
```
When any sensor input fails, the feature must transition to a safe state
(typically: feature disabled, driver notified via cluster/warning lamp)

TC-SAFETY-001: Verify safe state on forward radar loss
  Inject: Stop all forward radar messages
  Expect: ACC disabled (Status=0), DTC set, cluster warning active
  Verify: No autonomous braking or throttle output during sensor fault
```

**2. No Unintended Activation**
```
TC-SAFETY-002: LKA must not apply torque when LKA_Enable = 0
  Condition: LKA_Enable = 0 (disabled by driver or ignition state)
  Inject: LaneOffset = +60 cm (large drift that would normally trigger correction)
  Expect: LKA_TorqueRequest = 0 regardless of offset
```

**3. Torque Limitation**
```
TC-SAFETY-003: LKA torque must not exceed specification limit
  Inject: LaneOffset = +100 cm (extreme drift)
  Monitor: LKA_TorqueRequest_Nm over time
  Expect: TorqueRequest ≤ [ASIL-defined limit, e.g., 3.5 Nm] at all times
```

**4. Reaction to Implausible Inputs**
```
TC-SAFETY-004: ACC must not accelerate on implausible speed signal
  Inject: VehicleSpeed = 0xFFFF (beyond valid range: 250 km/h)
  Expect: ACC_Status = 0 (OFF), no ThrottleRequest sent
         DTC set for implausible speed
```

### 28.3 Test Documentation Requirements for ASIL Features

```
For each ASIL ≥ B test case, the test report must include:
  [ ] Test case ID + requirement ID (traceability)
  [ ] ASIL level of the requirement
  [ ] Test execution log with timestamps
  [ ] CAN trace/measurement file reference (filename + storage path)
  [ ] Pass/fail verdict with engineer signature
  [ ] DTC snapshot (relevant fault conditions)
  [ ] Reviewer signature (independence — different engineer from executor)
```

---

## 29. Environmental and Stress Testing

### 29.1 Voltage Variation Testing

ADAS ECUs must function across the full automotive voltage range.

| Test Condition | Voltage | Duration | Expected Behaviour |
|---------------|---------|----------|--------------------|
| Normal operation | 13.5 V | Continuous | All features active |
| Engine crank simulation | 6.0 V (dip) | 40 ms | Features gracefully degrade; no crash |
| Battery charging | 14.4 V | Continuous | All features active; no overvoltage DTC |
| High voltage spike | 16.0 V | 500 ms | Features active or safe disable; recover after spike |
| Low battery | 9.0 V | 30 s | Undervoltage DTC set; features may disable |
| Deep discharge | 6.5 V | 5 s | ECU may reset; full recovery after voltage restoration |

**CAPL-based voltage monitoring during test:**
```c
variables {
  float vbat_min = 99.0;
  float vbat_max = 0.0;
}

on message 0x600 {  // PowerManagement message from BCM
  float vbat = (this.byte(0) * 256.0 + this.byte(1)) / 100.0;
  if (vbat < vbat_min) vbat_min = vbat;
  if (vbat > vbat_max) vbat_max = vbat;
  if (vbat < 9.0) {
    write("[WARNING] Supply voltage LOW: %.2f V at %d ms",
          vbat, timeNow()/100000);
  }
  if (vbat > 15.5) {
    write("[WARNING] Supply voltage HIGH: %.2f V at %d ms",
          vbat, timeNow()/100000);
  }
}

on stop {
  write("Voltage range during test: Min=%.2f V  Max=%.2f V", vbat_min, vbat_max);
}
```

### 29.2 Temperature Testing (Bench-Level)

```
Cold soak test:
  1. Place ECU in temperature chamber at -40°C for 2 hours
  2. Apply ignition ON without pre-heating
  3. Verify ECU boots within [spec] seconds
  4. Run TC-BSD-001: verify BSD functions at cold temperature
  5. Check for temperature-related DTCs (over/under temp)

Hot soak test:
  1. Set temperature chamber to +85°C (or +105°C for under-bonnet ECU)
  2. Run full feature regression while maintaining temperature
  3. Monitor ECU thermal protection: if over-temp DTC appears, verify feature degradation
  4. Verify recovery after temperature normalises

Test bench alternative (no climate chamber):
  1. Use a heat gun at safe distance to warm ECU surface
  2. Monitor ECU internal temperature via XCP (variable: ecu_temp_degC)
  3. Log temperature vs feature availability
```

### 29.3 Electromagnetic Compatibility (EMC) — Bench Notes

```
EMC is performed in accredited test labs, but bench engineers support:

Pre-EMC checks:
  [ ] All connectors properly mated (no loose pins that would worsen emissions)
  [ ] Cable harness routing per vehicle drawing (routing affects antenna effect)
  [ ] Termination resistors in place (un-terminated bus creates reflections = emissions)
  [ ] ECU GND strap tight and low-resistance

During EMC test (remote monitoring from outside chamber):
  [ ] CANoe logging active: capture any errors during radiated immunity sweep
  [ ] Watch for error frames on CAN (increase in bus errors = susceptibility issue)
  [ ] Watch for DTC appearances during frequency sweep
  [ ] Feature output monitoring: any unwanted assertions during RF injection

Post-EMC:
  [ ] Verify all features pass full functionality test after EMC exposure
  [ ] Check for any latent DTCs that appeared during EMC
```

---

## 30. Test Execution Log Template

Use this template for every manual test execution session. File as a PDF/spreadsheet attached
to the JIRA sprint or Confluence test page.

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ADAS FEATURE TEST EXECUTION LOG                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ Project:       ___________________   Build:   v___.___.___ build __________  ║
║ Date:          ___________________   Bench:   ___________________________    ║
║ Engineer:      ___________________   Reviewed: _________________________     ║
║ CANoe Ver:     ___________________   DBC File: ________________________      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ BENCH STATUS BEFORE TEST                                                     ║
║   Supply voltage:  _______ V     CAN bus load:  _______ %                   ║
║   ECU SW version:  _______       DTC count at start:  _______               ║
║   Measurement log: _______________________________________                   ║
╠═════════╦══════════════════╦═══════════╦══════════════════╦═════════════════╣
║ TC ID   ║ Test Name        ║ Verdict   ║ Actual Result     ║ Notes / Defect  ║
╠═════════╬══════════════════╬═══════════╬══════════════════╬═════════════════╣
║ BSD-001 ║ Left target det. ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ BSD-002 ║ Turn sig escalat ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ BSD-003 ║ Below speed thr. ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ BSD-004 ║ Target clears    ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ ACC-001 ║ Speed hold       ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ ACC-002 ║ Cut-in decel     ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ ACC-003 ║ Driver override  ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ ACC-004 ║ Auto cancel N    ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ LKA-001 ║ Lane centring    ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ LKA-002 ║ Corrective torq  ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ LKA-003 ║ Turn sig suppress║ PASS/FAIL ║ ________________  ║ ______________  ║
║ LKA-004 ║ Low quality degrde PASS/FAIL ║ ________________  ║ ______________  ║
║ LDW-001 ║ Left departure   ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ LDW-002 ║ Intentional LC   ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ FCW-001 ║ TTC 2.5 s visual ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ FCW-002 ║ Full escalation  ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ FCW-003 ║ Off-path no warn ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ BCW-001 ║ CTA from left    ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ DMS-001 ║ Drowsiness det.  ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ DMS-002 ║ Gaze distraction ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ DMS-003 ║ Driver absence   ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ PDC-001 ║ Rear zones       ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ PDC-002 ║ Front PDC gear D ║ PASS/FAIL ║ ________________  ║ ______________  ║
║ APA-001 ║ Space scan       ║ PASS/FAIL ║ ________________  ║ ______________  ║
╠═════════╩══════════════════╩═══════════╩══════════════════╩═════════════════╣
║ SUMMARY                                                                      ║
║   Total: ___   Pass: ___   Fail: ___   Blocked: ___   Inconclusive: ___     ║
║   Pass Rate: _______ %                                                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ DTCs AFTER TEST                                                              ║
║   DTC 1: ___________   DTC 2: ___________   DTC 3: ___________              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ DEFECTS RAISED                                                               ║
║   JIRA-ID 1: __________________   Severity: ______                          ║
║   JIRA-ID 2: __________________   Severity: ______                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ SIGN-OFF                                                                     ║
║   Engineer: ___________________   Signature: _________   Date: ___________  ║
║   Reviewer: ___________________   Signature: _________   Date: ___________  ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## 31. Common Pitfalls and Pro Tips

### 31.1 Top 10 Mistakes ADAS Test Engineers Make

| # | Mistake | Correct Practice |
|---|---------|-----------------|
| 1 | Not checking ECU SW version before testing | Always read 0x22 F1 89 as first step |
| 2 | Running tests without logging enabled | Always start .blf logging before measurement |
| 3 | Forgetting to terminate CAN bus | Check 60 Ω impedance every bench change |
| 4 | Using wrong DBC version for the SW build | Pin DBC version to SW build in CI |
| 5 | Not clearing DTCs between test cases | Run 14 FF FF FF between independent TCs |
| 6 | Sending signals at wrong cycle time | Match DBC nominal cycle time in CAPL |
| 7 | Declaring PASS without timing verification | Always measure latency, not just state |
| 8 | Not testing hysteresis (only activation) | Test both entry AND exit of every threshold |
| 9 | Ignoring the turn signal for LKA/LDW | Always test suppression cases |
| 10 | Re-running failed TC without root cause | Root cause first; then re-test with justification |

### 31.2 CANoe Power Tips

```
Tip 1: Use Symbol Editor (Alt+S) to quickly find signal encoding
       → shows factor, offset, bit position at a glance

Tip 2: Create a "Test Panel" with buttons wired to CAPL functions
       → one-click injection of common scenarios

Tip 3: Use "Replay" block to play back a previously recorded .blf
       → reproduce exact conditions from a field failure report

Tip 4: Export Graphics window data to CSV (right-click → Export)
       → enables Excel-based latency analysis across multiple runs

Tip 5: Use CANoe's "Check" feature (CAN message timing checks)
       → auto-flags messages that are late, early, or missing

Tip 6: Save/restore CANoe environment states with "Measurement Setup"
       → snapshot the exact configuration before a sprint starts

Tip 7: Assign keyboard shortcuts (Ctrl+1, Ctrl+2...) to common CAPL scripts
       → dramatically speeds up manual test execution
```

### 31.3 CAN Frame Calculation Quick Reference

**Calculate raw value for any signal:**
```
raw = (physical_value - offset) / factor

Example: LaneOffset = -25 cm, factor=1, offset=0
  raw = (-25 - 0) / 1 = -25
  As signed 16-bit: -25 = 0xFFE7
  CAN bytes (big-endian): B0 = 0xFF, B1 = 0xE7

Example: VehicleSpeed = 120 km/h, factor=0.01, offset=0
  raw = (120 - 0) / 0.01 = 12000
  As unsigned 16-bit: 12000 = 0x2EE0
  CAN bytes: B0 = 0x2E, B1 = 0xE0
```

**Two's complement for signed values:**
```
For a negative value N in M-bit field:
  raw = 2^M + N

Example: -300 in 16-bit:
  raw = 65536 + (-300) = 65236 = 0xFED4
  CAN bytes: B0 = 0xFE, B1 = 0xD4
```

### 31.4 When to Escalate vs. Investigate Yourself

```
Investigate yourself first:
  ✓ Signal encoding issue (wrong factor/offset in test setup)
  ✓ DBC version mismatch
  ✓ Missing precondition (gear, speed, enable flag)
  ✓ Bus termination / wiring issue
  ✓ DTC that you can root-cause from trace

Escalate to development team immediately:
  ✗ Safety-critical feature produces unexpected output (e.g., phantom braking)
  ✗ ECU resets spontaneously during normal operation
  ✗ CAN messages with incorrect content from ECU (not test setup error)
  ✗ Feature enables in a condition where it should be prohibited
  ✗ DTC that cannot be reproduced after root-cause attempt
  ✗ New DTC introduced in latest build with no linked change
```
