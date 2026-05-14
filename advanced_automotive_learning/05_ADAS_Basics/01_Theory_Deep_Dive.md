# ADAS BASICS — DEEP DIVE
## Module 5 of 7 | advanced_automotive_learning

---

## 1. SAE AUTOMATION LEVELS (J3016)

```
LEVEL  NAME                    DRIVER ROLE                   EXAMPLE
─────────────────────────────────────────────────────────────────────────────
L0     No Automation           Full human control             Basic car
L1     Driver Assistance       Monitors + assists 1 axis      ACC or LKA (not both)
L2     Partial Automation      Assists lateral + longitudinal  Tesla Autopilot, GM SC
       ┌──────────────────────────────────────────────────────────────┐
       │ CRITICAL BOUNDARY: Below L2, human monitors continuously.   │
       │ At L3+, system monitors; human is a fallback.               │
       └──────────────────────────────────────────────────────────────┘
L3     Conditional Automation  System monitors, human takeover Highway driving
                               when requested               (Honda Sensing Elite)
L4     High Automation         No human needed for ODD       Waymo Robotaxi (geo-fenced)
L5     Full Automation         No human ever needed          Not commercially available yet

ODD = Operational Design Domain:
  Subset of conditions (speed range, weather, road type, geography)
  within which the system is designed to function.
  Example L4 ODD: "Highway driving, weather = clear, speed < 130 km/h, Germany A-roads"
```

---

## 2. ADAS FEATURE ARCHITECTURE

### 2.1 Feature Map

```
ADAS FEATURES BY DOMAIN:

  LONGITUDINAL                    LATERAL                     MONITORING
  ─────────────────────────────────────────────────────────────────────
  ACC  - Adaptive Cruise          LKA  - Lane Keep Assist     BSD  - Blind Spot Detection
  STOP&GO - Queue assist          LCA  - Lane Change Assist   DOW  - Door Opening Warning
  AEB  - Auto Emergency Braking   LDW  - Lane Departure Warn  RCTA - Rear Cross Traffic Alert
  FCW  - Forward Collision Warn   TJA  - Traffic Jam Assist   SLI  - Speed Limit Info
  PAS  - Park Assist System       APA  - Auto Parking Assist  DMS  - Driver Monitoring System
  CMS  - Collision Mitigation
```

### 2.2 ADAS Perception-Planning-Control Loop

```
ADAS SYSTEM ARCHITECTURE:
                                         
  ┌──────────────────────────────────────────────────────────────────────┐
  │                        ADAS DOMAIN CONTROLLER                        │
  │                                                                      │
  │  ┌────────────┐    ┌────────────┐    ┌─────────────┐    ┌────────┐  │
  │  │ PERCEPTION │───►│  FUSION    │───►│  PLANNING   │───►│CONTROL │  │
  │  │            │    │            │    │             │    │        │  │
  │  │ Object     │    │ Track-to-  │    │ Risk assess │    │ Brake  │  │
  │  │ Detection  │    │ Track      │    │ TTC calc    │    │ Steer  │  │
  │  │ Free space │    │ Extended   │    │ Decision    │    │ Throttle   │
  │  │ Lane detect│    │ Kalman     │    │ Trajectory  │    │        │  │
  │  └────────────┘    └────────────┘    └─────────────┘    └────────┘  │
  │         ▲                ▲                                    │      │
  │         │                │                                    │      │
  │  ┌──────┴──────────────────────────────────────────┐         │      │
  │  │              SENSOR INPUTS                       │         │      │
  │  │  Camera    Radar    LiDAR    GPS/IMU   V2X       │         │      │
  │  └──────────────────────────────────────────────────┘         │      │
  │                                                                ▼      │
  │                                              ┌─────────────────────┐ │
  │                                              │  ACTUATORS           │ │
  │                                              │  ESC (brake)         │ │
  │                                              │  EPS (steering)      │ │
  │                                              │  Engine controller   │ │
  │                                              └─────────────────────┘ │
  └──────────────────────────────────────────────────────────────────────┘
```

### 2.3 AEB — Automatic Emergency Braking (Deep Dive)

```
AEB SYSTEM LOGIC:

  Inputs:
    - Radar/camera object distance (d)
    - Relative velocity (v_rel = v_ego - v_target)
    - Ego vehicle speed (v_ego)
    - Road friction estimate (μ)

  Key Calculations:
    TTC = d / v_rel          (Time To Collision, seconds)
    
    Deceleration needed:
    a_needed = v_rel² / (2 × d)
    
    Available deceleration (dry road):
    a_max = μ × g ≈ 0.8 × 9.81 ≈ 7.8 m/s²

  Warning/Braking Decision:
    TTC > 3.0s  → No action
    3.0s > TTC > 1.5s → FCW alert (visual + haptic)
    1.5s > TTC > 0.8s → Partial braking (30% deceleration)
    TTC < 0.8s → Full AEB (100% deceleration, up to 0.9g)

  AEB Inhibit Conditions (AEB is suppressed):
    - Speed < 5 km/h (avoids parking lot triggers)
    - Speed > 200 km/h (system disabled at very high speed)
    - Reversing (R gear)
    - ESC active (braking already in progress)
    - Driver actively steering away (measured by SWA rate)

  False Positive Sources:
    - Metal drain covers (radar reflection)
    - Overhanging road signs (wrong height)
    - Oncoming vehicles in curves (before separation is detected)
    → Height/position filtering in radar reduces false positives
```

### 2.4 ACC — Adaptive Cruise Control

```
ACC CONTROL LAW:
  Headway time: THW = d / v_ego  (desired = 1.5–2.0 seconds)
  
  Follow controller (PID):
    error = d_actual - d_desired
    a_command = Kp × error + Ki × ∫error dt + Kd × d(error)/dt
  
  Setpoint modes:
    Free driving:  maintain set speed (classic cruise control)
    Following:     maintain THW to lead vehicle
    Cut-in detect: detect new lead vehicle entering lane (short THW transition)
    Stop & Go:     bring to full stop and resume from 0 km/h
  
  Sensor requirements:
    Range: 150–200m (long range radar)
    Azimuth accuracy: ±0.5° for reliable lane assignment
    Update rate: 20–50ms (50Hz radar cycle)
```

---

## 3. ISO 26262 — FUNCTIONAL SAFETY FOR ADAS

### 3.1 ASIL Assignment Process

```
ASIL DETERMINATION (hazard analysis):
  
  For each hazard:
    ASIL = f(Severity, Exposure, Controllability)
  
  Severity (S):
    S0 = No injuries
    S1 = Light/moderate injuries
    S2 = Severe/life-threatening injuries (survival probable)
    S3 = Life-threatening/fatal injuries
  
  Exposure (E):
    E0 = Incredible
    E1 = Very low probability
    E2 = Low probability
    E3 = Medium probability
    E4 = High probability (driving on motorway)
  
  Controllability (C):
    C0 = Controllable generally
    C1 = Simple controllable
    C2 = Normally controllable
    C3 = Difficult to control / uncontrollable
  
  ASIL TABLE (simplified):
  Severity × Exposure × Controllability → ASIL A/B/C/D or QM
  
  Example: AEB nuisance braking on motorway
    S = S2 (severe injury from rear-end collision)
    E = E4 (frequently on motorway)
    C = C3 (difficult to control at high speed)
    → ASIL D (highest safety requirement)

AEB ASIL Assignment:
  AEB false activation (nuisance braking): ASIL D
  AEB non-activation (miss): ASIL C
  FCW missed warning:         ASIL B
  DMS false drowsiness alert: ASIL A / QM
```

### 3.2 ISO 26262 V-Model for ADAS

```
ISO 26262 V-MODEL:

LEFT SIDE (Requirements):          RIGHT SIDE (Verification):
  Item Definition                     Confirmation Reviews
         │                                    ▲
  HARA + Safety Goal                  Safety Validation
         │                                    ▲
  Functional Safety Concept          System Integration Test
         │                                    ▲
  Technical Safety Concept          HW/SW Integration Test
         │                                    ▲
  System Design                      SW Integration Test
         │                                    ▲
  SW Architecture Design             SW Unit Test
         │                                    ▲
  SW Unit Design ──────────────────► SW Unit Implementation

KEY OUTPUTS AT EACH LEVEL:
  HARA: Hazard list + ASIL + Safety Goals
  FSC:  Safety Mechanisms (watchdogs, plausibility checks)
  TSC:  Hardware safety requirements (EMC, SBC, watchdog timer)
  SW:   MISRA-C, defensive programming, runtime monitors
```

---

## 4. SENSOR FUSION PIPELINE

```
MULTI-SENSOR FUSION ARCHITECTURE:

Sensor           Raw Output        After ECU Processing    Fused Object
────────────────────────────────────────────────────────────────────────
Camera ECU    → image frames     → 2D bounding box list  ─┐
Radar ECU     → point clusters   → object list            ├─► Fusion
LiDAR ECU     → point cloud      → object list            │   Engine
GPS/IMU       → position+heading → ego state              ─┘     │
                                                                   ▼
                                                           Fused Object List
                                                           (ID, x, y, v, w, h)
                                                                   │
                                                           Tracking (EKF)
                                                                   │
                                                           Risk Assessment
                                                                   │
                                                           ADAS Decision

FUSION TYPES:
  Early fusion: Merge raw data (point cloud + image pixels together)
    Pros: Maximum information retention
    Cons: High compute, tight timing requirement

  Late fusion:  Each sensor runs its own tracker, then merge object lists
    Pros: Sensor-independent, easier integration
    Cons: Some information lost in per-sensor detection step
    
  Deep fusion:  Neural network fuses feature maps from multiple sensors
    Pros: Best accuracy, learned complementarity
    Cons: Black box, hard to certify (ISO 26262)

TYPICAL AUTOMOTIVE CHOICE: Late fusion (easier to certify, modular)
```

---

## 5. ADAS TESTING METHODOLOGY

### 5.1 Test Levels

```
ADAS TEST PYRAMID:

  ▲ Reality        Physical test track  (expensive, weather-dependent)
  │             HIL simulation     (sensor signal injection)
  │          SIL  (software model in loop — virtual sensors)
  ▼ Virtual    MIL (model in loop — algorithm verification)

TEST COVERAGE APPROACH:
  1. Standard scenarios:   Euro NCAP AEB City/Interurban/Pedestrian
  2. Edge cases:           Sensor degradation, partial occlusion
  3. Fault injection:      ECU reset during AEB, sensor dropout
  4. Boundary conditions:  TTC at exactly 1.5s, speed at 5 km/h threshold
  5. Regression:           All previously fixed bugs get a specific test case
```

### 5.2 Euro NCAP Test Scenarios

```
EURO NCAP AEB TEST MATRIX (simplified):
  
  SCENARIO             SPEED RANGE    TARGET           PASS CRITERION
  ────────────────────────────────────────────────────────────────────
  AEB City             10–50 km/h     Soft GVT car     Avoid or mitigate
  AEB Interurban       30–80 km/h     Soft GVT car     Avoid or mitigate
  AEB Pedestrian       10–60 km/h     Adult/Child dummy Avoid
  AEB Cyclist          10–60 km/h     Cyclist dummy    Avoid
  AEB VRU Night        10–50 km/h     Pedestrian dummy Avoid or mitigate
  ACC Following        30–130 km/h    Lead vehicle     THW maintained ≥ 1.4s
  LKA Lane Departure   60–130 km/h    Lane marking     No crossing

GVT = Global Vehicle Target (inflatable fake car used in testing)
```

---

## 6. TEST CASE EXAMPLES

```
TC-ADAS-001: AEB Activation at Correct TTC Threshold
  Pre-condition: ECU in default state, ego speed = 50 km/h, dry road
  Action: Place target at 30m, stationary; drive toward at 50 km/h
  Expected: Partial braking at TTC < 1.5s, full AEB at TTC < 0.8s
  Pass criteria: Full stop before collision; no earlier/later activation

TC-ADAS-002: AEB Inhibition at Speed < 5 km/h
  Pre-condition: Ego speed = 3 km/h
  Action: Place obstacle at 0.5m
  Expected: AEB NOT activated
  Pass criteria: No automatic braking event

TC-ADAS-003: FCW Alert Timing
  Pre-condition: Ego speed 80 km/h, target decelerating at 5 m/s²
  Action: Close at 3.0s TTC
  Expected: FCW visual/audible alert within 200ms of TTC = 3.0s
  Pass criteria: Alert timestamp within ±200ms of calculated TTC boundary

TC-ADAS-004: ACC Cut-In Detection
  Pre-condition: ACC active, following target at 50 km/h, THW = 2.0s
  Action: New vehicle cuts in at 1.0s THW
  Expected: Deceleration begins within 300ms of cut-in detection
  Pass criteria: Brake request generated within 300ms; no passenger discomfort (< 0.3g)
```

---

## 7. COMMON BUGS IN ADAS SYSTEMS

```
BUG 1: Coordinate frame mismatch
  Camera outputs object in image frame (u, v pixels)
  Radar outputs in polar frame (range, azimuth)
  Fusion expects Cartesian vehicle frame (x, y meters)
  → Missing or wrong transformation causes misaligned tracks
  
BUG 2: TTC calculation with closing velocity = 0
  TTC = d / v_rel; if v_rel ≤ 0 (target moving away), TTC = infinity
  Division by zero or NaN propagates through the stack
  → Always check: if v_rel ≤ 0, TTC = infinity (no collision threat)

BUG 3: AEB active before initialization complete
  On power-on, sensor data is invalid for first 500ms
  If AEB decision runs before sensor validity flag is set:
  → False braking on startup
  → Fix: gate AEB on sensor_valid AND system_ready flags

BUG 4: Ghost objects from radar multipath
  Metal tunnel wall creates mirror reflection of lead vehicle
  Appears as two objects at same range but different azimuth
  → Plausibility checks: object at exact mirror azimuth with same dynamics = ghost

BUG 5: Session/DTC interference with ADAS algorithm
  DCM extended diagnostic session locks bus bandwidth
  ADAS algorithm running on same core experiences CPU overload
  Missed deadlines → safety monitor triggers emergency stop
  → Fix: ADAS algorithm must be on partitioned CPU core / higher OS priority
```

---

## 8. INTERVIEW Q&A

**Q1: What is the difference between L2 and L3 automation?**
> At L2 (Partial Automation), the driver must continuously monitor the environment and be ready to take over at any moment — the system is an aid, the driver is responsible. At L3 (Conditional Automation), the system monitors the environment within its ODD. The driver can divert attention (look away, read) but must respond when the system requests takeover within a defined transition time (typically 10 seconds). This distinction has major legal and liability implications.

**Q2: How does AEB decide when to brake?**
> AEB calculates TTC (Time To Collision = distance / closing_velocity). At TTC < 3.0s: FCW alert. At TTC < 1.5s: partial braking. At TTC < 0.8s: full emergency braking. The system also calculates required deceleration (a = v² / 2d) and compares it to available friction-limited deceleration. AEB is inhibited below 5 km/h, during active ESC events, and when the driver is actively steering away.

**Q3: Why is ASIL D assigned to AEB false activation?**
> AEB false activation on a motorway at 130 km/h causes sudden deceleration — creating a high-risk rear-end collision with the following vehicle. Severity = S3 (fatal injury possible), Exposure = E4 (high probability on motorway), Controllability = C3 (driver cannot react fast enough at 130 km/h). This combination of S3+E4+C3 results in ASIL D — the highest safety integrity level.

**Q4: What is sensor fusion and why use late fusion?**
> Sensor fusion combines data from multiple sensors (camera, radar, LiDAR) to produce a single, more accurate world model. Late fusion — where each sensor runs its own object detection and tracker, then the results are merged — is preferred in automotive because: (1) each sensor ECU can be independently certified, (2) failure of one sensor degrades gracefully without crashing the fused model, (3) it is easier to justify to safety assessors.

**Q5: How do you test a safety-critical AEB requirement in a lab environment?**
> Using HIL: inject simulated radar and camera object data into the ADAS ECU via signal injection harness. Ramp the simulated distance from 50m to 0 at the target closing speed. Monitor the AEB brake request output signal. Verify the brake request appears at the expected TTC threshold within the timing tolerance. Also test inhibit conditions by asserting ego speed < 5 km/h and verifying no brake request.

---

*Next: [02_STAR_Answers.md](02_STAR_Answers.md)*
