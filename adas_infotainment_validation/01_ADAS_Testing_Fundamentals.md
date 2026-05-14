# 01 — ADAS Testing Fundamentals

> **Standards**: ISO 26262, ISO 21448 (SOTIF), Euro NCAP, UNECE R155/R156  
> **Prerequisite**: Basic automotive knowledge  
> **Outcome**: Understand the testing framework, safety levels, test pyramid, and ADAS system architecture

---

## 1. What Is ADAS?

ADAS (Advanced Driver Assistance Systems) are electronic systems that help drivers and improve road safety:

```
ADAS Feature Landscape:
─────────────────────────────────────────────────────────────────────
Longitudinal Control        Lateral Control          Warning Systems
─────────────────────────────────────────────────────────────────────
AEB   Autonomous Emergency  LKA  Lane Keep Assist    FCW  Forward Collision Warn
ACC   Adaptive Cruise       LCA  Lane Change Assist  LDW  Lane Departure Warn
ISA   Intelligent Speed     AES  Auto Emergency Steer BSW  Blind Spot Warning
      Adaptation            RSM  Road Sign Recognition PCW  Pedestrian Collision Warn
─────────────────────────────────────────────────────────────────────

Automation levels (SAE J3016):
  L0 = No automation (only warnings)
  L1 = Driver assistance (one axis: cruise OR lane)
  L2 = Partial automation (both axes: cruise AND lane)
  L3 = Conditional automation (driver can disengage attention)
  L4 = High automation (no driver needed in ODD)
  L5 = Full automation (all conditions)
─────────────────────────────────────────────────────────────────────
```

---

## 2. ADAS System Architecture

```
ADAS Processing Pipeline:
────────────────────────────────────────────────────────────────────────────
SENSE          PERCEIVE        FUSE            DECIDE          ACT
────────────────────────────────────────────────────────────────────────────
Radar      ──► Object list ──►              ──►             ──► Brake ECU
Camera     ──► Lane data   ──► Fusion &     ──► ADAS        ──► EPS ECU
LiDAR      ──► Point cloud ──► Object map   ──► Decision    ──► Throttle
Ultrasonic ──► Near zones  ──►              ──► Logic       ──► HMI warning
GPS/IMU    ──► Ego pose    ──►              ──►             ──► Dashboard
────────────────────────────────────────────────────────────────────────────
Each arrow = a software interface = a test interface

ECU structure:
┌─────────────────────────────────────────────────────────────────┐
│                   ADAS Domain Controller                        │
│                                                                 │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ Sensor  │  │ Fusion   │  │ Decision │  │ Actuation      │  │
│  │ Drivers │→ │ Module   │→ │ Module   │→ │ Interface      │  │
│  │ (CAN/   │  │ (Kalman  │  │ (AEB/ACC │  │ (CAN Tx/SPI    │  │
│  │  Eth)   │  │  Filter) │  │  logic)  │  │  to brake ECU) │  │
│  └─────────┘  └──────────┘  └──────────┘  └────────────────┘  │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │   AUTOSAR OS  /  QNX  /  ROS2                         │    │
│  │   RTOS, 1–10 ms cyclic tasks                          │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. The V-Model for ADAS

The V-model maps every development artifact to a corresponding test level:

```
V-Model (ADAS development):
────────────────────────────────────────────────────────────────────────────

System Requirements ──────────────────────────────► System Test (HIL/Road)
        │                                                    ▲
        ▼                                                    │
  SW Architecture ──────────────────────────► Integration Test (SIL/HIL)
        │                                                    ▲
        ▼                                                    │
   SW Design ─────────────────────────────────► Module Test (SIL/bench)
        │                                                    ▲
        ▼                                                    │
   Unit Design ────────────────────────────────────► Unit Test (MIL/SIL)
        │                                                    ▲
        └──────────────── Implementation ───────────────────┘
                           (Code writing)

Left side = decomposition (requirements → code)
Right side = verification (code → requirements)
────────────────────────────────────────────────────────────────────────────
```

### Test Level Definitions
| Level | What Is Tested | Where Runs | Who Tests |
|-------|---------------|-----------|-----------|
| **Unit Test** | Single function/module in isolation | PC (MIL/SIL) | Developer |
| **Integration Test** | Multiple modules working together | PC/SIL/bench | Developer + Test Eng |
| **System Test** | Full ECU in vehicle environment | HIL / bench | Test Engineer |
| **Acceptance Test** | Feature validation vs customer req | HIL / vehicle | Test Engineer |
| **Homologation** | Type approval vs regulation | Track / road | Homologation team |

---

## 4. ISO 26262 — Functional Safety

ISO 26262 is the functional safety standard for road vehicles. Every ADAS test engineer must understand ASIL:

### ASIL Determination
```
ASIL = Severity × Exposure × Controllability

Severity (S):
  S0 = No injury
  S1 = Light injury
  S2 = Serious injury (survival likely)
  S3 = Life-threatening / fatal

Exposure (E):
  E0 = Incredible (never in real operation)
  E1 = Very low (rare)
  E2 = Low (occasionally)
  E3 = Medium (fairly often)
  E4 = High (almost all the time)

Controllability (C):
  C0 = Controllable in general
  C1 = Simply controllable
  C2 = Normally controllable
  C3 = Difficult to control

ASIL matrix (simplified):
────────────────────────────────
S × E × C → ASIL
────────────────────────────────
S1 E1 C1  → QM (no ASIL needed)
S2 E2 C2  → ASIL A
S3 E3 C2  → ASIL B
S3 E4 C2  → ASIL C
S3 E4 C3  → ASIL D  (highest safety level)
────────────────────────────────
```

### What ASIL Means for Testing
| ASIL | Code Coverage Required | Review Required | Test Type |
|------|----------------------|-----------------|-----------|
| QM | None specified | Optional | Standard testing |
| A | Statement coverage | Peer review | Basic verification |
| B | Branch coverage | Independent review | Formal verification |
| C | MC/DC coverage | Independent safety auditor | FMEA + test |
| D | MC/DC + data-flow coverage | Independent safety auditor | FMEA + FMEDA + extensive test |

```
ADAS typical ASILs:
  AEB brake command output:        ASIL C / D
  ACC target speed setting:         ASIL B
  FCW warning alert:                ASIL A / B
  Lane departure warning:           ASIL A
  Parking sensor beep:              QM
  Navigation map display:           QM
```

---

## 5. ISO 21448 — SOTIF

SOTIF (Safety Of The Intended Functionality) addresses **misuse and insufficiency** — cases where the system is functionally correct but causes accidents:

```
ISO 21448 vs ISO 26262:

ISO 26262 (Functional Safety):
  "System does the WRONG THING due to hardware/software failure"
  Example: AEB fires because a sensor short-circuit returns 0m

ISO 21448 (SOTIF):
  "System does the RIGHT THING in the WRONG SITUATION"
  Example: AEB does NOT fire because radar misses a low radar-cross-section
           pedestrian (algorithm limitation, not a failure)

SOTIF test focus:
  - Edge cases: unusual objects, weather, road types
  - Sensor performance limits (fog, rain, glare)
  - Unknown unknowns: scenarios not in training data
  - ODD boundaries: what happens just outside the design envelope
```

### ODD — Operational Design Domain
```
ODD definition (example for AEB city):
──────────────────────────────────────────────────────────────────
Parameter           Min        Max         Condition
──────────────────────────────────────────────────────────────────
Vehicle speed       0 km/h     80 km/h     AEB active
Target speed        0 km/h     50 km/h     Stationary or slow
Ego–target distance 3 m        200 m       Radar detection range
Visibility          > 100 m    ∞           No dense fog
Road type           All paved roads        No off-road
Weather             Dry/light rain         Not snow/ice
Time of day         Day/Night              Not heavy backlight
──────────────────────────────────────────────────────────────────

Tests outside ODD = SOTIF boundary tests:
  - Speed 82 km/h → AEB should be INHIBITED
  - Dense fog → system should alert driver, not activate
  - Wet road (μ=0.4) → AEB threshold adjusted or inhibited
```

---

## 6. Euro NCAP — The Consumer Test Protocol

Euro NCAP (European New Car Assessment Programme) runs standardized tests that OEMs must score highly on for commercial success:

```
Euro NCAP 2026 ADAS Tests:
──────────────────────────────────────────────────────────────────────────
Category              Test Name         Max Score  Measure
──────────────────────────────────────────────────────────────────────────
AEB City              CCRs, CCRm, CCRb  6 pts      No collision / speed reduction
AEB Inter-Urban       CCRs, CCRB, CCRS  6 pts      No collision
AEB Pedestrian        CPFA, CPNCO       6 pts      No pedestrian collision
AEB Cyclist           CBNA, CBFA        4 pts      No cyclist collision
Lane Support Systems  LDW, LKA, AES     4 pts      No lane departure
Speed Assistance      ISA active        3 pts      Speed compliance
Rear AEB              RCTA, RCCb        4 pts      No rear collision
──────────────────────────────────────────────────────────────────────────
Total ADAS score: 33 points (counts towards 5-star rating)
──────────────────────────────────────────────────────────────────────────

CCRs = Car-to-Car Rear Stationary
CCRm = Car-to-Car Rear Moving
CCRb = Car-to-Car Rear Braking
CPFA = Car-to-Pedestrian Far Adult
```

---

## 7. Test Types in ADAS Validation

```
Test Types (what you are checking):
──────────────────────────────────────────────────────────────────────────
Functional Test:    "Does the feature work?"
  Example: Does AEB fire when TTC < 1 s?

Boundary / Edge Case Test:  "Does it work at the limits?"
  Example: AEB at exactly 80 km/h (ODD boundary)
  Example: Object at minimum radar range (5 m)

Negative Test:      "Does it correctly NOT do something?"
  Example: AEB must NOT fire on open road at 60 km/h

Regression Test:    "Did the new SW version break anything?"
  Example: Run all previous PASSED tests on new SW build

Fault Injection Test: "How does it behave when hardware fails?"
  Example: Radar disconnected → ECU stores DTC, deactivates AEB gracefully

Performance Test:   "Is it fast enough?"
  Example: AEB response latency < 150 ms end-to-end

Security Test:      "Can it be attacked?"
  Example: CAN spoofing attack on radar frame → ECU rejects invalid frames

Stress Test:        "Does it cope under maximum load?"
  Example: All 8 CAN buses at 70% load → ADAS still responds in time
──────────────────────────────────────────────────────────────────────────
```

---

## 8. Sensor Technology Basics for Test Engineers

```
Radar (77 GHz FMCW):
  Measures:  Range (0.3–250 m), relative velocity (±70 m/s), azimuth (±60°)
  Strength:  Works in rain, fog, night, high speed
  Weakness:  Poor lateral resolution, cannot detect pedestrians well at low speed
  Output:    Object list via CAN FD (range, vel, azimuth, RCS, classification)

Camera (visible / IR):
  Measures:  Lane markings, traffic signs, pedestrians, cyclists
  Strength:  Rich semantic information, sign text/color recognition
  Weakness:  Fails in glare, fog, heavy rain, direct sunlight
  Output:    Object list + lane data via CAN FD or Ethernet SOME/IP

LiDAR (905 nm / 1550 nm):
  Measures:  3D point cloud, range (0.5–300 m), precise shape
  Strength:  Precise 3D geometry, not affected by color/texture
  Weakness:  Expensive, rain/snow degrades, some glass surfaces invisible
  Output:    Point cloud via Ethernet (MCAP/ROS2) or object list via CAN

Ultrasonic (40 kHz):
  Measures:  Very short range (0.1–5 m), presence only
  Strength:  Very cheap, works in all weather
  Weakness:  Short range only, slow update rate (100 ms)
  Output:    Distance per zone via LIN or CAN
```

---

## 9. Test Design Process

```
Test case design steps:
─────────────────────────────────────────────────────────────────────
1. Requirements analysis
   Source: SW requirements spec (e.g., "AEB shall activate when TTC < 1.2 s")

2. Equivalence partitioning
   Partition input space into classes with same expected behavior
   TTC values: [>3s: no action], [3–1.2s: warning only], [<1.2s: brake]

3. Boundary value analysis
   Test at exactly the boundaries: TTC = 3.0, 1.2, 1.19 s

4. Decision table
   Speed | Obstacle | Rain | AEB State | Expected
   30    |  yes     |  no  | active    | brake
   90    |  yes     |  no  | inhibited | no brake
   30    |  no      |  no  | active    | no brake

5. State transition
   Test every state transition in the system state machine:
   OFF → STANDBY → ACTIVE → BRAKING → OVERRIDE → STANDBY

6. Write formal test case
   ID:       TC-AEB-015
   Title:    AEB activates at TTC boundary 1.2 s
   Precond:  ECU in ACTIVE state, dry road, speed 40 km/h
   Input:    Place obstacle at distance = 40 × 1.2 / 3.6 = 13.3 m
   Expected: BrakeActive = 1 within 200 ms
   Postcond: Collision counter = 0
─────────────────────────────────────────────────────────────────────
```

---

## 10. Interview Q&A

**Q1: What is the difference between ISO 26262 and ISO 21448?**  
ISO 26262 (Functional Safety) covers failures — hardware faults, software bugs, and random hardware failures that cause the system to malfunction. ISO 21448 (SOTIF) covers insufficiency — situations where the system performs exactly as designed but the design itself is insufficient for certain real-world conditions (e.g., sensor limitations in fog, edge cases not covered by the algorithm's training data).

**Q2: What is ASIL D and what does it require for testing?**  
ASIL D is the highest automotive safety integrity level, applied to functions where a failure could cause life-threatening injury with no easy driver recovery (S3, E4, C3). Testing at ASIL D requires: MC/DC (Modified Condition/Decision Coverage) plus data-flow coverage, independent verification by a safety assessor, formal FMEA and FMEDA analyses, and complete traceability from system requirement down to test result.

**Q3: What is the ODD in ADAS context?**  
ODD (Operational Design Domain) defines the specific conditions under which an ADAS feature is designed to function: vehicle speed range, road type, weather, visibility, target type, and time of day. A test engineer must test both inside the ODD (feature must work) and at ODD boundaries (feature must deactivate or degrade gracefully), and test SOTIF edge cases just outside the ODD.

**Q4: What is a negative test case and give an ADAS example?**  
A negative test verifies that the system correctly does NOT perform an action when conditions are wrong. For AEB: "The system shall NOT activate braking on an open highway at 120 km/h with no obstacle present." This validates the inhibit logic and prevents false positives, which are a major concern for customer acceptance and safety.

**Q5: Explain the test pyramid for ADAS software.**  
The test pyramid has unit tests at the base (many, fast, automated, run by developers), integration tests in the middle (fewer, test component interactions, SIL), and system tests at the top (fewest, most realistic, on HIL/vehicle, slow and expensive). The principle is to catch as many bugs as possible at lower, cheaper levels — only the final system-level behavior needs to be validated on real hardware.
