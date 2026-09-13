# ADAS Test Case Design & Validation — Part 0: Framework & Methodology

**Scope of this document series:** ACC, LKA, LDW, BSD, Automatic Parking, Parking Assistance, DMS
**Audience:** ADAS Test Engineer / ADAS Validation Engineer / RADAR Validation Engineer / HIL Engineer / System Test Engineer / Vehicle Test Engineer
**Note on numbers:** All speeds, distances, TTC values, thresholds, and timings in this document are **example values** for illustration unless explicitly tied to a cited standard. Real acceptance thresholds always come from the OEM/Tier‑1 requirement specification and calibration data for the specific program.

This is Part 0 of a multi-part series. It covers the material that is common across all seven ADAS features: the test case template, test categories, the requirement‑to‑test workflow, the SIL→HIL→Vehicle progression, fault‑injection methodology, and the execution workflow used day‑to‑day by a validation engineer. Parts 1–7 apply this framework to each feature (ACC, LKA, LDW, BSD, Automatic Parking, Parking Assistance, DMS) with 30–40+ detailed test cases, KPIs, defects, and interview questions each.

---

## 1. Common Test Case Structure

Every test case in this series — regardless of feature — uses the following template. Using one template across all features matters for two practical reasons: it lets a test management tool (Polarion, codebeamer, Jama, ALM) treat all ADAS test cases uniformly for traceability, and it lets a reviewer or interviewer immediately locate the information they're checking for (preconditions vs. expected result vs. KPI) without re-learning a new layout per feature.

| Field | Description | Why it matters |
|---|---|---|
| **Test Case ID** | Unique ID, e.g. `ACC_TC_014`, `LKA_TC_022` | Traceability into the test management tool and defect reports |
| **Feature** | ADAS feature under test | Filtering/reporting by feature |
| **Requirement ID** | Related requirement (e.g. `SYSREQ-ACC-0231`) | Requirement-to-test traceability (ASPICE SWE.1–SWE.6, ISO 26262 Part 8 Clause 9) |
| **Test Objective** | One sentence: what is being verified | Keeps the test scoped to one verifiable claim |
| **Test Type** | Functional / Negative / Boundary / Fault Injection / Regression | Drives test-suite categorization and coverage reporting |
| **Test Level** | SIL / HIL / Bench / Vehicle | Determines which environment and which subset of signals are available |
| **Preconditions** | Required initial conditions (ignition state, feature enabled, no active faults, etc.) | Test isn't valid unless these hold; also the first thing to check when a test fails unexpectedly |
| **Test Environment** | Chamber, test track, public road, HIL bench, SIL simulation | Repeatability and safety classification of the test |
| **Vehicle State** | Speed, gear, ignition, steering angle, brake/accelerator state | Longitudinal/lateral tests are state-dependent; this pins the starting dynamics |
| **Sensor State** | Camera/RADAR/Ultrasonic operating normally, degraded, or faulted | Distinguishes "feature failed" from "sensor input was invalid by design" |
| **Initial Conditions** | Concrete starting scenario (lead vehicle at X m, lane width Y m, etc.) | Makes the test reproducible in SIL/HIL scenario scripting |
| **Test Inputs** | Stimulus applied (target vehicle profile, CAN signal injection, driver input) | What the tester or scenario script actually varies |
| **Test Steps** | Ordered, executable steps | What the tester (human or automated script) does |
| **Expected Result** | System behavior that constitutes a pass | The oracle against which actual behavior is compared |
| **CAN Signals** | Relevant signals to monitor (name, and typically DBC-defined range/scaling) | What to capture on the bus during execution |
| **Logs Required** | CAN trace, video, sensor raw data, debug logs | What must be archived for defect analysis / audit |
| **KPI** | Quantitative measurement criteria (e.g., distance error ≤ 0.3 m) | Converts a pass/fail into a measurable, trendable number |
| **Pass/Fail Criteria** | Explicit numeric or logical condition | Removes ambiguity from test execution sign-off |
| **Postcondition** | State of system/vehicle at test end | Needed to safely reset for the next test, and to confirm no side effects (e.g., fault not left latched) |
| **Remarks** | Notes, known issues, applicable variants | Context for future engineers re-running the test |

**Why explain "why" for every test case:** A test case that only says *what* to do is brittle — when the requirement changes slightly, or the tester encounters an edge condition the steps didn't anticipate, they can't judge intent. Explaining *why* a test exists (which failure mode, hazard, or requirement clause it protects against) is also exactly what an interviewer is checking for: can you justify your test design, not just execute a script.

---

## 2. Test Case Categories

Each feature part in this series builds its test suite from five categories. Together they form the coverage argument you'd present in a test plan review or ASPICE assessment.

### 2.1 Functional Tests
Verify the feature behaves correctly under normal, expected operating conditions — the "happy path." These establish a baseline: if a functional test fails, nothing else about the feature is trustworthy, so functional tests are typically gate-blocking (must pass before boundary/negative testing proceeds).

### 2.2 Boundary Tests
Exercise the edges of the operating envelope: minimum/maximum speed, minimum/maximum detection distance, TTC (time-to-collision) thresholds, lane width limits, object size limits, sensor detection limits, steering angle limits, parking-space dimension limits, driver attention thresholds. Boundary defects are disproportionately common in production ADAS because algorithms are frequently tuned and validated near the *center* of the operating range and under-tested at the edges — exactly where hazardous behavior (e.g., a feature that silently disengages at 3 km/h below its stated minimum) tends to hide.

### 2.3 Negative Tests
Verify the system fails safely, not incorrectly, when an input is invalid: sensor failure, sensor blockage, invalid CAN signal, CAN timeout, CAN‑FD communication failure, Ethernet communication failure, ECU failure, invalid configuration, feature unavailable, driver override, unexpected object, environmental degradation. The pass criterion for a negative test is almost never "the feature keeps working" — it's "the system degrades to a defined, documented state" (warning + graceful handover to the driver, feature-unavailable indication, etc.).

### 2.4 Corner Cases
Real-world conditions that stress perception and control simultaneously: rain, fog, night, low sunlight, strong sunlight/glare, tunnels (entry/exit transition), curved roads, poor/faded lane markings, wet road, snow (where applicable), heavy traffic, multiple simultaneous objects, motorcycles, pedestrians, bicycles, trucks, trailers. These are typically drawn from field data (fleet logging) and known "long-tail" scenarios, and are where camera/RADAR sensor fusion earns its complexity.

### 2.5 Regression Tests
A defined subset of functional + boundary + key negative tests re-run whenever one of these changes:
- **Software update** — re-run full functional suite + prior open-defect verification tests
- **Calibration change** (camera/RADAR extrinsic/intrinsic) — re-run detection-accuracy and KPI tests
- **ECU change** (hardware revision/supplier change) — re-run CAN/CAN‑FD/Ethernet communication and timing tests
- **Sensor change** (new part number/supplier) — re-run full sensor-validation suite (Part 0 §10-equivalent in each feature part) and KPI baseline comparison
- **Requirement change** — re-run only the tests traced to the changed requirement, plus adjacent tests sharing the same code path
- **Algorithm change** (e.g., tracking filter, path planner) — re-run functional + boundary + corner-case suite for the affected feature
- **CAN database (DBC) change** — re-run all communication-validation tests (signal scaling, endianness, timeout, CRC, alive counter) across every feature that consumes the changed messages, since a DBC change can silently break a feature that didn't itself change

---

## 3. Requirement-Based Testing

Converting a requirement into an executable test case is the core skill being validated in this whole document. The flow:

```text
Requirement
     ↓
Requirement Analysis      (Is it verifiable? Is it atomic? Does it have a measurable
                            acceptance value, or does one need to be derived?)
     ↓
Preconditions              (What state must the system be in before this applies?)
     ↓
Test Scenario               (Concrete world: road, traffic, weather, sensor state)
     ↓
Input Parameters            (What is varied, and over what range?)
     ↓
Test Steps                  (Ordered, executable, reproducible)
     ↓
Expected Result              (Derived directly from the requirement's "shall" clause)
     ↓
KPI                          (Numeric threshold that operationalizes "expected result")
     ↓
Pass / Fail
```

**Worked example (generic, feature-agnostic):**

> Requirement: *"The system shall issue a warning to the driver within [T] ms of detecting condition [X], provided precondition [P] holds."*

- Requirement analysis: this is a single atomic, verifiable requirement — it has an explicit input trigger, a measurable time bound, and an explicit precondition gate. Good requirement.
- Precondition: `P` must be independently testable (i.e., you need a separate test case verifying that the feature behaves correctly when `P` is *false* — the warning must NOT fire).
- Test scenario: construct the minimal scenario that produces condition `X` unambiguously (avoid confounding with other trigger conditions).
- Input parameters: the stimulus that produces `X`, parameterized so the same test can be re-run at boundary values of `X`.
- Test steps: set up precondition `P`, inject/stimulate `X`, start a timer at the moment `X` becomes true (per ground-truth/reference sensor, not the ECU's own detection — otherwise you're only testing the ECU's self-consistency).
- Expected result: warning observed on the defined channel (HMI/audio/CAN signal) — described in system terms, not implementation terms.
- KPI: measured latency ≤ `T` ms, over N repeated trials, with a defined percentile (e.g., P95 ≤ T, not just mean ≤ T — mean can hide a long tail that matters for safety).
- Pass/Fail: explicit numeric gate, e.g., "P95 latency ≤ 700 ms AND no false-negative in N=30 trials."

Each feature part in this series (Parts 1–7) provides **5 requirement-to-test-case examples** built exactly this way against realistic ADAS requirement statements for that feature.

---

## 4. SIL → HIL → Vehicle Testing

### 4.1 SIL (Software-in-the-Loop)
The ADAS algorithm (or a model of it) runs against a **software model** of the vehicle, sensors, and environment — no real ECU hardware, no real bus hardware. Used earliest in the V-model, cheapest to run, fully deterministic/repeatable, and highly parallelizable (thousands of scenario variants overnight in a CI pipeline). Weaknesses: sensor models are approximations (especially RADAR multipath/clutter and camera photometric effects), and timing is not representative of the real target hardware/OS/bus.

**SIL architecture:**
```text
Scenario Definition (parametrized: road, weather, traffic, ego state)
        |
        v
Vehicle Model  (longitudinal/lateral dynamics)  +  Sensor Model (camera/RADAR/ultrasonic)
        |
        v
Software-under-test (algorithm binary or model, e.g. Simulink/production code)
        |
        v
KPI Calculation + Automated Pass/Fail (regression suite, often thousands of cases per night)
```

### 4.2 HIL (Hardware-in-the-Loop)
The **real target ECU** (production hardware, production software) is connected to a real-time simulator that feeds it synthetic sensor data (RADAR object lists or raw ADC, camera video injection or CAN-based object lists, ultrasonic echo simulation) and real CAN/CAN‑FD/Ethernet bus traffic, and reads back the ECU's actuation commands (brake request, steering torque request) into a vehicle dynamics model that closes the loop in real time.

**HIL architecture:**
```text
Scenario Generator
        |
        v
Vehicle / Sensor Simulation (real-time, deterministic step size, e.g. 1-10 ms)
        |
        v
HIL System (real-time OS, I/O cards, restbus simulation)
        |
        v
ADAS ECU  (real target hardware + production software)
        |
        +---- CAN / CAN-FD  (to Brake ECU, Powertrain ECU, Steering ECU — simulated or real)
        |
        +---- Automotive Ethernet (camera streams, diagnostic-over-IP)
        |
        v
Vehicle ECUs (real or restbus-simulated)
        |
        v
Measurement System (CAN logger, scope, video capture, KPI extraction)
```
HIL is where timing-, fault-injection-, and communication-level defects are found that SIL cannot see (bus load effects, real ECU boot/reset behavior, actual message timeout handling, real diagnostic response behavior).

### 4.3 Vehicle Testing
Test track (controlled, repeatable targets — e.g., a Euro NCAP-style soft target vehicle for AEB/ACC, marked lane geometry for LKA/LDW) and public-road testing (uncontrolled, statistically representative but not repeatable — used for KPI trend confirmation and long-tail corner-case collection, not for pass/fail certification of a single defect). Vehicle testing is the only stage that validates true sensor physics (real RADAR RCS returns, real camera optics/rolling shutter, real road surface friction) and true human-machine interaction (driver override force/torque feel, real HMI visibility in sunlight).

### 4.4 Why all three, not just one
- SIL catches algorithmic and logic defects cheaply and early, and enables regression at scale.
- HIL catches timing, communication, and fault-handling defects using real target software, safely and repeatably (you cannot safely repeat "inject a CAN bus-off during an active parking maneuver with a pedestrian mannequin" on a public road).
- Vehicle testing catches sensor-physics, human-factors, and truly-unmodeled-environment defects that no simulation currently captures with full fidelity.
A defect found late (in vehicle testing) that could have been caught in SIL is a process signal, not just a bug — it usually means SIL sensor/vehicle models need to be improved, which is itself tracked and reported.

---

## 5. Fault Injection Methodology

For every fault type below, the analysis follows the same five-stage chain, and every fault-injection test case in Parts 1–7 is written against this chain:

**Fault → Detection → Diagnostic → System Reaction → Driver Notification → Recovery**

| Stage | What is verified |
|---|---|
| **Fault** | The specific fault injected (see list below) — must be injected at the correct layer (physical, bus, application) to be representative |
| **Detection** | Does the system detect the fault within the required time, and correctly classify it (vs. misclassifying a valid-but-unusual input as a fault, or vice versa)? |
| **Diagnostic** | Is a correct DTC (Diagnostic Trouble Code) set, with correct freeze-frame data, retrievable over UDS? |
| **System Reaction** | Does the feature degrade to the *defined* state (not an undefined/unsafe state) — e.g., ACC disengages and hands control back, LKA suppresses steering intervention, DMS falls back to a conservative "cannot determine attention" state |
| **Driver Notification** | Is the driver informed via the correct HMI channel, with correct message/icon/audio, within the required latency? |
| **Recovery** | When the fault clears, does the system correctly restore the feature (or correctly require re-activation), without a latched fault state that persists incorrectly? |

**Fault types covered across the feature parts:** sensor failure, sensor blockage, CAN timeout, CAN‑FD timeout, Ethernet loss, CRC error, alive-counter error, ECU reset, watchdog reset, invalid signal, missing signal, power interruption, low voltage, high temperature, software restart.

---

## 6. Test Execution Workflow

```text
Requirement
     ↓
Test Specification        (test strategy, coverage targets, environment mapping)
     ↓
Test Case                  (using the template in §1)
     ↓
Test Script                 (SIL/HIL automation, or documented manual procedure)
     ↓
Test Environment Setup       (bench config, HIL restbus config, vehicle instrumentation)
     ↓
SIL / HIL / Vehicle          (execution stage — see §4)
     ↓
Test Execution
     ↓
Data Logging                  (CAN trace, video, sensor raw/processed data, DTCs)
     ↓
KPI Calculation
     ↓
Pass / Fail
     ↓
Defect (if Fail)               (see Defect Analysis template in each Part)
     ↓
Root Cause Analysis
     ↓
Fix
     ↓
Regression                      (per §2.5)
     ↓
Test Report
```

**Notes per stage:**
- *Test Specification* is where coverage is planned against requirements (traceability matrix) — this is the artifact an ASPICE assessor reviews first.
- *Test Script* vs. manual procedure: SIL is almost always scripted; HIL is scripted for regression and manual/exploratory for new scenario development; vehicle testing is a mix, with manual test-track evaluation and semi-automated data logging.
- *Data Logging* must capture enough to reconstruct the failure without re-running the test — this is what makes a defect report actionable instead of "doesn't work, please investigate."
- *Root Cause Analysis* is not complete until you can state which layer failed (sensor, algorithm, communication, actuation, or test-setup-itself) — see the Defect Analysis template in each feature Part for the full field set.

---

## 7. Final Test Engineer Checklist

### Requirements
- [ ] Requirement reviewed for verifiability (atomic, has a measurable acceptance value)
- [ ] Requirement traceability established (requirement ↔ test case ↔ result)
- [ ] Acceptance criteria identified and agreed with requirement owner

### Test Design
- [ ] Functional tests
- [ ] Negative tests
- [ ] Boundary tests
- [ ] Corner cases
- [ ] Fault injection
- [ ] Regression tests

### Sensors
- [ ] Camera
- [ ] RADAR
- [ ] Ultrasonic
- [ ] Sensor health monitoring
- [ ] Sensor blockage handling
- [ ] Calibration verification (extrinsic/intrinsic, post-service recalibration)

### Communication
- [ ] CAN
- [ ] CAN-FD
- [ ] Ethernet
- [ ] CRC
- [ ] Alive counter
- [ ] Timeout handling

### Testing
- [ ] SIL
- [ ] HIL
- [ ] Bench
- [ ] Lab vehicle
- [ ] Test track
- [ ] Real vehicle (public road)

### Analysis
- [ ] Logs collected
- [ ] CAN traces analyzed
- [ ] Sensor data analyzed
- [ ] KPI calculated
- [ ] Pass/fail determined
- [ ] Defect created if required
- [ ] Root cause identified
- [ ] Regression executed

---

## Series Roadmap

| Part | Feature | Contents |
|---|---|---|
| 0 (this doc) | Common framework | Template, categories, requirement-to-test, SIL/HIL/vehicle, fault injection, workflow, checklist |
| 1 | ACC | Understanding, architecture, 35+ test cases, KPIs, requirement examples, defects, interview Q&A |
| 2 | LKA | Same structure |
| 3 | LDW (incl. LDW vs LKA) | Same structure |
| 4 | BSD | Same structure |
| 5 | Automatic Parking | Same structure |
| 6 | Parking Assistance | Same structure |
| 7 | DMS | Same structure, incl. ADAS-interaction section |
| 8 (cross-cutting) | Sensor validation, CAN/CAN-FD/Ethernet validation, Python automation examples | Shared across all 7 features |

Part 1 (ACC) follows.