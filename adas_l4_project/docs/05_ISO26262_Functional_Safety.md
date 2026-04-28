# ISO 26262 Functional Safety for ADAS Level 4

## 1. ISO 26262 Standard Overview

**ISO 26262** – "Road vehicles – Functional safety" (2018, 2nd edition)

```
Scope:      Safety of E/E (electrical/electronic/programmable) systems
            in series production road vehicles
            Covers hardware, software, system, and process activities

ASIL:       Automotive Safety Integrity Level A, B, C, D
            (D = highest, like IEC 61508 SIL 3/4)

Key concept: Freedom from unreasonable risk due to hazards caused by
             malfunctioning behaviour of E/E systems
```

---

## 2. ASIL Determination (HARA – Hazard Analysis and Risk Assessment)

### Risk Parameters

| Parameter | Description | Values |
|-----------|-------------|--------|
| **S** | Severity | S0 (none) → S3 (life-threatening) |
| **E** | Exposure | E0 (improbable) → E4 (continuous) |
| **C** | Controllability | C0 (easy) → C3 (uncontrollable) |

### ASIL Assignment Table

```
        C0      C1      C2      C3
S1 E1:  QM      QM      QM      QM
S1 E2:  QM      QM      QM      A
S1 E3:  QM      QM      A       B
S1 E4:  QM      A       B       C
S2 E1:  QM      QM      QM      A
S2 E2:  QM      QM      A       B
S2 E3:  QM      A       B       C
S2 E4:  QM      B       C       D
S3 E1:  QM      QM      A       B
S3 E2:  QM      A       B       C
S3 E3:  A       B       C       D
S3 E4:  B       C       D       D

QM = Quality Management (no ASIL requirement)
```

### ADAS L4 Example HARA

```
Hazard: Emergency stop not triggered when pedestrian in path
  S = S3 (life-threatening – pedestrian could be killed)
  E = E3 (urban driving is relatively frequent)
  C = C3 (pedestrian cannot control the vehicle)
  → ASIL D

Hazard: False positive emergency stop at highway speed
  S = S3 (rear-end collision risk)
  E = E4 (highway driving frequent)
  C = C2 (driver may react but delayed)
  → ASIL D

Hazard: Incorrect lane change causes collision
  S = S2 (significant injury)
  E = E3 (lane changes are frequent)
  C = C2 (limited controllability due to high speed)
  → ASIL C
```

---

## 3. Safety Goals and FSR

```
Safety Goal 1 (SG1, ASIL D):
  "The ADAS system shall not cause the vehicle to collide with a detected obstacle."
  Functional Safety Requirement:
    FSR1.1: The emergency stop function shall be triggered within 100ms of
            detecting an obstacle with TTC < 1.0s
    FSR1.2: AEB function shall be free from single-point failure
            (redundant hardware: dual braking channels)

Safety Goal 2 (SG2, ASIL D):
  "The ADAS system shall not cause the vehicle to exceed road speed limits
   by more than 10 km/h."
  FSR2.1: Speed limiter override shall be enabled at all times
  FSR2.2: Speed signal shall be validated against wheel speed sensors

Safety Goal 3 (SG3, ASIL C):
  "Lane change manoeuvre shall not be initiated without free adjacent lane
   confirmed for > 3s duration."
```

---

## 4. Safety Architecture

### Safe State Analysis

```
For each hazard, a safe state must be defined:

Function               | Fault               | Safe State
-----------------------|---------------------|---------------------------
Emergency Stop         | AEB ECU failure     | Mechanical brakes engage (fallback)
Steering Control       | EPS controller fail | Steering freeze + alert
Lane Change            | Perception timeout  | Abort LC, return to lane
Speed Control          | Throttle stuck      | Engine cut + brake apply
Sensor Fusion          | All sensors fail    | Minimal Risk Condition
Path Planning          | Planning timeout    | Follow lane, decelerate
```

### Dual-Channel Redundancy (ASIL D)

```
ASIL D requires: No single point of failure shall cause violation of safety goal

Approach: ASIL D = ASIL B + ASIL B (decomposition via ISO 26262-9)

Implementation:
  Main channel:    Primary ECU running full L4 stack
  Monitor channel: Separate MCU checking critical outputs
                   - Validates steering commands (|cmd| < limit)
                   - Validates braking (applied when required)
                   - Compares perception outputs for plausibility

  If main ≠ monitor AND safety-critical:
    → Set SAFE_STATE flag
    → Assert hardware emergency stop signal
    → Alert driver (takeover request)
```

---

## 5. Watchdog & Deadline Monitoring

### Software Watchdog

```cpp
// Cyclic alive counters per task
void task_perception_10ms() {
    process_sensors();
    WatchdogManager::kick(WD_PERCEPTION);  // must call within 10ms window
}

void task_safety_1ms() {
    safety_monitor.checkAll();
    WatchdogManager::kick(WD_SAFETY);
}

// Watchdog manager triggers safe state if any kick is missed
void WatchdogManager::check() {  // called from HW timer interrupt
    for (auto& wd : watchdogs) {
        if (!wd.kicked) {
            SafetyMonitor::forceSafeState(wd.id);
        }
        wd.kicked = false;
    }
}
```

### Deadline Monitoring

```
Task           | Period | Max jitter | Miss action
---------------|--------|------------|------------------------
Safety Monitor | 1ms    | 200µs      | Immediate safe state
AEB decision   | 5ms    | 1ms        | Apply max braking
Perception     | 10ms   | 2ms        | Hold last output
Planning       | 100ms  | 20ms       | Hold trajectory
Control        | 10ms   | 2ms        | Previous command
```

---

## 6. Fault Injection Testing (FMEA)

### FMEA Process

```
1. Identify functions and components
2. For each: what could fail? (failure modes)
3. For each failure mode:
   - Effects (immediate, system, end)
   - Severity (1-10)
   - Occurrence probability (1-10)
   - Detection capability (1-10)
   - RPN = Severity × Occurrence × Detection
4. Prioritise by RPN > 100 for corrective action

ADAS L4 – Top FMEA Items:
  Component       | Failure Mode     | Severity | Occur | Detect | RPN
  LiDAR           | No output        |    9     |   2   |   1    |  18
  LiDAR           | Partial output   |    8     |   3   |   3    |  72
  Camera          | Blinded (sun)    |    7     |   4   |   2    |  56
  EPS             | Loss of control  |   10     |   2   |   2    |  40
  ABS             | No brake         |   10     |   1   |   2    |  20
  Planning SW     | Timeout          |    9     |   2   |   1    |  18
  Fusion          | Ghost object     |    8     |   3   |   4    |  96   ← mitigation needed
```

---

## 7. ADAS Safety Monitor – State Machine (C++)

```cpp
enum class SafetyState {
    NOMINAL,           // All healthy
    DEGRADED,          // Minor fault, reduce ODD
    MINIMAL_RISK,      // Major fault, pull over safely
    EMERGENCY_STOP,    // Immediate halt required
    SAFE_STATE         // System at rest, all actuators parked
};

struct FaultFlags {
    bool lidar_failed     : 1;
    bool camera_failed    : 1;
    bool radar_failed     : 1;
    bool fusion_timeout   : 1;
    bool planning_timeout : 1;
    bool control_timeout  : 1;
    bool speed_exceeded   : 1;
    bool steering_fault   : 1;
    uint8_t reserved      : 8;
};

class SafetyMonitor {
public:
    SafetyState evaluate(const FaultFlags& faults, float ttc_s) {
        // Emergency conditions (ASIL D – immediate)
        if (ttc_s < 1.0f && !faults.radar_failed) {
            return SafetyState::EMERGENCY_STOP;
        }
        if (faults.steering_fault || faults.speed_exceeded) {
            return SafetyState::EMERGENCY_STOP;
        }

        // Major sensor loss → pull over
        uint8_t sensor_failures = faults.lidar_failed +
                                   faults.camera_failed +
                                   faults.radar_failed;
        if (sensor_failures >= 2) {
            return SafetyState::MINIMAL_RISK;
        }

        // Planning or control timeout
        if (faults.planning_timeout || faults.control_timeout) {
            return SafetyState::MINIMAL_RISK;
        }

        // Single sensor fault → degraded
        if (sensor_failures == 1 || faults.fusion_timeout) {
            return SafetyState::DEGRADED;
        }

        return SafetyState::NOMINAL;
    }
};
```

---

## 8. Over-The-Air (OTA) Update Safety

```
For L4 ADAS software updates (cybersecurity meets functional safety):

Requirements:
  1. Update signed with OEM private key (RSA-4096 or ECDSA P-521)
  2. Version downgrade protection (anti-rollback counter in fuse register)
  3. Vehicle must be stationary, park brake engaged before update
  4. Safety monitor active during update (cannot update safety partition live)
  5. Dual-bank flash: new image written to inactive bank
                     CRC check before activation
                     Rollback if boot fails 3× (watchdog triggered)

Validation sequence:
  1. Receive signed update package
  2. Verify signature (PKI)
  3. Verify CRC of payload
  4. Flash inactive partition
  5. Verify flashed image CRC
  6. Schedule activation on next key cycle with safety checks
  7. Post-update: run BIST (Built-In Self Test) before L4 engagement
```

---

## 9. Certification Pathway for L4 (EU/US)

```
Europe (EU):   UNECE WP.29 Regulation No. 157 (ALKS) and future L4 regs
               Type Approval from National Authority (e.g. KBA, DVSA)
               Functional safety: ISO 26262 compliance (independent audit)

USA:           NHTSA AV guidance (voluntary), FMVSS amendments
               SAFETY Act certification for cyber
               State-level deployment permits (CA, TX, AZ)

Process:
  1. Safety Case (argument + evidence)
  2. Independent Functional Safety Assessment (FSA)
  3. HARA / FMEA / FTA documented and audited
  4. Validation: > 10M km simulation + 100k km road testing
  5. Incident reporting to authority (post-deployment)
```
