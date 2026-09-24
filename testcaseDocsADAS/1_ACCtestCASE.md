# ADAS Test Case Design & Validation — Part 1: ACC (Adaptive Cruise Control)

*Continues from Part 0 (Framework & Methodology), which defines the test case template, categories, and SIL/HIL/vehicle methodology used throughout this section. All numeric values below are example values unless stated otherwise.*

---

## 1.1 Feature Understanding

**What ACC is.** Adaptive Cruise Control automatically controls a vehicle's longitudinal speed to maintain either a driver-set cruising speed (when the road ahead is clear) or a driver-set following distance/time-gap behind a detected lead vehicle (when one is present), without the driver operating the accelerator or brake pedal.

**Purpose.** Reduce driver workload on highways and in steady traffic, improve speed-keeping consistency, and — as a secondary benefit — smooth traffic flow by reducing the accordion effect of manual following-distance variation.

**Cruise Control vs. ACC.**
| Conventional Cruise Control | ACC |
|---|---|
| Holds a fixed set speed only | Holds set speed OR follows a lead vehicle, whichever is lower |
| No environment sensing | Uses RADAR/camera to detect and track lead vehicles |
| Driver must brake for traffic | Automatically decelerates/accelerates for lead vehicle |
| No following-distance concept | Driver-selectable time gap |

**Operating principle.** ACC continuously runs two control modes and arbitrates between them:
1. **Speed control mode** — no valid lead vehicle in path → vehicle accelerates/maintains the driver-set speed subject to comfort acceleration limits.
2. **Distance/gap control mode** — a valid lead vehicle is tracked in-path → vehicle controls to the selected time gap (e.g., 1.0–2.2 s, OEM-defined discrete steps), which may require decelerating below the set speed.

The system arbitrates by always obeying whichever mode currently demands the *lower* target speed (cannot exceed set speed even if the lead vehicle is faster and lane is otherwise clear).

**Target vehicle selection.** RADAR/camera fusion produces an object list (position, relative velocity, lateral offset, classification). A path-prediction algorithm (based on ego yaw rate, steering angle, and/or lane geometry from camera) determines which objects are "in-path." Among in-path objects, the nearest one in the same lane, above a minimum confidence/persistence threshold, is selected as the Primary Target.

**Following-distance control.** Implemented as either constant time-gap (distance = time gap × relative speed, so absolute distance grows with speed) or, less commonly, constant distance. Time-gap control is standard because it approximates the following behavior a human driver naturally scales with speed.

**Speed control.** A closed-loop controller (typically cascaded: outer loop = desired acceleration from gap/speed error, inner loop = torque/brake request to achieve that acceleration) sends requests to the Powertrain ECU (torque request) and Brake ECU (deceleration request) over CAN/CAN‑FD.

**Stop-and-go ACC.** An extension that brings the vehicle to a full stop behind a stopping lead vehicle and — depending on the variant — either holds the stop indefinitely (requiring a driver "resume" input, e.g., accelerator tap or resume-switch press, after a timeout) or automatically resumes if the lead vehicle moves off within a short window (e.g., 3 s), without driver input. This is a distinct, separately-tested capability from highway-speed ACC because it introduces new requirements: hold-to-stop control, creep/launch control, and pedestrian/cross-traffic safety considerations at very low speed.

**ACC limitations (must be understood and tested, not assumed away):**
- Minimum operating speed (many ACC — non-stop&go variants — disengage below ~30 km/h)
- Cannot detect stationary objects reliably in all implementations (legacy RADAR-only systems have historically had reduced confidence on stationary targets to suppress false braking — this is a known, explicitly testable limitation)
- Does not detect pedestrians/cyclists as *followable* targets in most ACC-only (non-AEB-fused) implementations
- Reduced/no operation in heavy rain, fog, or with sensor blockage
- Cannot react to cut-ins with less warning than the sensor's field-of-view and processing latency allow
- Driver remains responsible for the driving task at all times (SAE Level 1–2 feature)

---

## 1.2 ACC Architecture

```text
RADAR + Camera
      |
      v
Object Detection
      |
      v
Object Tracking
      |
      v
Target Selection
      |
      v
ACC Controller
      |
      +------> Engine / Powertrain
      |
      +------> Brake ECU
      |
      +------> Transmission
      |
      v
Vehicle Longitudinal Control
```

**Data flow between ECUs:**
- **RADAR → ADAS ECU:** raw or pre-processed object list (range, range-rate, azimuth, RCS) over CAN‑FD or Automotive Ethernet, depending on RADAR generation.
- **Camera → ADAS ECU:** lane geometry, object classification/bounding boxes, and (in fusion systems) an independent object list, typically over Automotive Ethernet (raw/compressed video) or CAN‑FD (processed object list) depending on architecture — many programs run camera and RADAR object lists through a central fusion function inside the ADAS domain controller.
- **ADAS ECU → Brake ECU:** deceleration request / brake torque request, request-active flag, over CAN‑FD, cyclic (e.g., 10–20 ms).
- **ADAS ECU → Powertrain ECU:** acceleration request / torque request, over CAN‑FD.
- **ADAS ECU → Transmission (where relevant):** gear-hold/kickdown-suppression requests during ACC-controlled deceleration/acceleration.
- **ADAS ECU ↔ Gateway:** ACC status/mode signals routed to Cluster and Body domain as needed (diagnostic routing, cross-domain signals).
- **ADAS ECU → Cluster/HMI:** ACC state (Off/Standby/Active/Overridden/Unavailable), set speed, selected time gap, target-detected icon, warnings.
- **Brake ECU → ADAS ECU:** brake pedal position/driver-braking-active flag (used for override detection), wheel speed, ESC status (used to suppress ACC intervention during ESC events).
- **Powertrain ECU → ADAS ECU:** accelerator pedal position (override detection), engine/torque status, actual delivered torque (closed-loop confirmation).

---

## 1.3 ACC Test Cases

35 test cases below, grouped by category. Cases 1–18 are given in full detail per the Part 0 §1 template; cases 19–35 are given as a compact matrix (same rigor, condensed presentation) to keep this document navigable — each follows the identical template and can be expanded to full detail on request.

### Functional

**ACC_TC_001 — ACC Activation with No Lead Vehicle**
- *Why:* Baseline functional test — every other ACC test depends on activation working correctly.
- Requirement ID: `SYSREQ-ACC-0010` | Test Type: Functional | Test Level: Vehicle / HIL
- Preconditions: Ignition ON, engine running, ACC system healthy (no active DTCs), vehicle speed ≥ minimum ACC engagement speed (example: 30 km/h)
- Test Environment: Test track, clear straight road
- Vehicle State: Speed 60 km/h, gear D, no lead vehicle in path
- Sensor State: RADAR and camera nominal
- Initial Conditions: Driver presses ACC "Set" switch
- Test Inputs: ACC Set switch press
- Test Steps: 1) Drive at 60 km/h. 2) Press ACC Set. 3) Observe cluster/HMI. 4) Hold for 30 s.
- Expected Result: ACC transitions to Active state, set speed = 60 km/h displayed, vehicle maintains 60 km/h ± tolerance with no driver pedal input.
- CAN Signals: `ACC_State`, `ACC_SetSpeed`, `ACC_Active_Flag`
- Logs Required: CAN trace, cluster video capture
- KPI: Set-speed accuracy ≤ ±1 km/h steady state
- Pass/Fail: `ACC_State == ACTIVE` AND speed error ≤ 1 km/h sustained ≥ 20 s
- Postcondition: ACC remains active
- Remarks: Repeat at min and max engagement speed boundaries (see boundary cases)

**ACC_TC_002 — ACC Deactivation via Cancel Switch**
- *Why:* Verifies the driver's primary manual disengagement path works instantly and unconditionally.
- Requirement ID: `SYSREQ-ACC-0011` | Test Type: Functional | Test Level: Vehicle / HIL
- Preconditions: ACC Active, set speed 80 km/h
- Vehicle State: 80 km/h, gear D
- Test Inputs: Press Cancel switch
- Test Steps: 1) ACC Active at 80 km/h. 2) Press Cancel. 3) Observe state and vehicle behavior.
- Expected Result: ACC transitions to Standby immediately; vehicle coasts (no active accel/decel request); no residual brake/torque request.
- CAN Signals: `ACC_State`, `Brake_Request`, `Torque_Request`
- KPI: Cancel-to-standby transition latency ≤ 100 ms
- Pass/Fail: `ACC_State == STANDBY` within 100 ms of switch press AND `Brake_Request == 0`
- Postcondition: ACC Standby, previous set speed retained in memory for Resume
- Remarks: Safety-relevant — must not depend on any other condition being true

**ACC_TC_003 — Set Speed Increase (Tap and Hold)**
- *Why:* Verifies both discrete-tap and press-and-hold speed adjustment behave per spec (common UX defect area).
- Requirement ID: `SYSREQ-ACC-0015` | Test Type: Functional | Test Level: Vehicle / HIL
- Preconditions: ACC Active at 60 km/h, clear road
- Test Inputs: Single tap of "+" switch; then press-and-hold "+" for 3 s
- Expected Result: Single tap increases set speed by defined increment (example: +1 or +5 km/h per program); hold increases continuously up to release, in defined step rate (example: 1 km/h per 200 ms)
- CAN Signals: `ACC_SetSpeed`, `SetSpeed_Switch_State`
- KPI: Increment accuracy = exact per-tap value; hold ramp rate within ±10% of spec
- Pass/Fail: Displayed and CAN set-speed match expected value after each input pattern
- Postcondition: New set speed active, vehicle accelerating toward it within comfort limits
- Remarks: Verify upper set-speed clamp (see boundary case)

**ACC_TC_004 — Set Speed Decrease**
- *Why:* Mirror of TC_003; decrease path sometimes uses a different code path (e.g., coast-to-decrease vs. active braking) that must be separately verified.
- Requirement ID: `SYSREQ-ACC-0016` | Test Type: Functional | Test Level: Vehicle / HIL
- Test Inputs: Tap "−" switch repeatedly from 100 km/h to 60 km/h
- Expected Result: Set speed decreases per increment; vehicle decelerates smoothly (coast or light brake, per calibration) without exceeding comfort deceleration limit (example: ≤ 2.0 m/s²)
- CAN Signals: `ACC_SetSpeed`, `Vehicle_Speed`, `Deceleration_Actual`
- KPI: Deceleration ≤ 2.0 m/s² during set-speed-driven decrease (non-emergency)
- Pass/Fail: Set speed correctly decremented AND deceleration within comfort bound
- Postcondition: Vehicle stable at new set speed

**ACC_TC_005 — Lead Vehicle Detection and Automatic Follow**
- *Why:* Core differentiator vs. conventional cruise control; validates target selection and mode arbitration.
- Requirement ID: `SYSREQ-ACC-0020` | Test Type: Functional | Test Level: HIL / Vehicle
- Preconditions: ACC Active, set speed 100 km/h, no current target
- Initial Conditions: Slower lead vehicle (70 km/h) enters path 150 m ahead
- Test Steps: 1) Ego at 100 km/h under ACC. 2) Lead vehicle detected in-path at 150 m, 70 km/h. 3) Observe.
- Expected Result: Target-detected indication appears; ego decelerates to match 70 km/h at the selected time gap, without exceeding comfort deceleration; ego does not exceed set speed once gap closes.
- CAN Signals: `Target_Detected_Flag`, `Target_Distance`, `Target_RelVelocity`, `Vehicle_Speed`
- Logs Required: RADAR object-list log, CAN trace, video
- KPI: Time-gap settling error ≤ ±0.2 s of selected gap; deceleration ≤ 3.0 m/s² (comfort)
- Pass/Fail: Steady-state gap within tolerance, no comfort-limit violation, no false brake-then-release oscillation
- Postcondition: ACC in gap-control mode, following steadily

**ACC_TC_006 — Time Gap Selection (Multiple Settings)**
- *Why:* Verifies all discrete gap settings are correctly applied, not just the default.
- Requirement ID: `SYSREQ-ACC-0021` | Test Type: Functional | Test Level: HIL
- Test Inputs: Cycle gap-select switch through all available settings (e.g., 1, 2, 3, 4 → 1.0/1.4/1.8/2.2 s) while following a steady lead vehicle
- Expected Result: Following distance settles to each selected time gap in turn
- CAN Signals: `TimeGap_Setting`, `Target_Distance`, `Vehicle_Speed`
- KPI: Settled distance = TimeGap × relative closing speed, within ±10%
- Pass/Fail: Each of N gap settings verified independently

**ACC_TC_007 — Lead Vehicle Deceleration (Smooth Follow)**
- *Why:* Verifies the controller responds proportionally, not with abrupt/oscillatory braking, to a moderate lead-vehicle deceleration.
- Requirement ID: `SYSREQ-ACC-0022` | Test Type: Functional | Test Level: HIL
- Initial Conditions: Steady follow at 2.0 s gap, 90 km/h
- Test Inputs: Lead vehicle decelerates at 2 m/s² to 60 km/h
- Expected Result: Ego decelerates to restore gap, matches lead speed, no gap violation below the selected setting during the transient
- CAN Signals: `Target_Distance`, `Target_RelVelocity`, `Deceleration_Actual`
- KPI: Minimum transient gap ≥ 80% of steady-state target gap; jerk ≤ defined comfort limit (example: 2.5 m/s³)
- Pass/Fail: No gap violation beyond threshold, no jerk-limit violation

**ACC_TC_008 — Lead Vehicle Acceleration (Resume to Set Speed)**
- *Why:* Verifies correct return to speed-control mode once a target is no longer speed-limiting.
- Requirement ID: `SYSREQ-ACC-0023` | Test Type: Functional | Test Level: HIL
- Test Inputs: Followed lead vehicle accelerates away above ego's set speed
- Expected Result: Ego accelerates back to set speed (not to lead vehicle's speed) at comfort acceleration; mode indication switches from gap-control to speed-control
- KPI: Acceleration ≤ comfort limit (example: 1.5 m/s²); final steady speed = set speed ± 1 km/h

**ACC_TC_009 — Cut-In Scenario (Vehicle Merges In-Path)**
- *Why:* One of the most safety-relevant and commonly defective ACC scenarios — a new target must be acquired and reacted to within a bounded time.
- Requirement ID: `SYSREQ-ACC-0025` | Test Type: Functional | Test Level: HIL / Vehicle
- Initial Conditions: Ego 100 km/h under speed control, no target; adjacent-lane vehicle at 60 km/h cuts in 40 m ahead
- Expected Result: New target acquired within defined latency; ego decelerates to restore safe gap without harsh braking unless gap is already critically short (then a firmer, still-bounded deceleration is expected)
- CAN Signals: `Target_Detected_Flag`, `Target_Acquisition_Time`
- KPI: Target acquisition time ≤ 500 ms (example); deceleration profile within defined comfort/urgency bands based on initial gap
- Pass/Fail: New target correctly classified as in-path within latency bound; no collision-course condition allowed to persist unaddressed

**ACC_TC_010 — Cut-Out Scenario (Target Vehicle Leaves Path)**
- *Why:* Verifies the system doesn't continue braking for a target that has left the path (common false-continuation defect), and correctly reveals a new target if present.
- Requirement ID: `SYSREQ-ACC-0026` | Test Type: Functional | Test Level: HIL
- Initial Conditions: Following a slow lead vehicle; that vehicle changes lanes out of path, revealing either clear road or a second, more distant lead vehicle
- Expected Result: Target correctly dropped; ego accelerates toward set speed or acquires the newly revealed target, as applicable — without accelerating toward the exiting vehicle
- KPI: Target-drop latency ≤ defined bound (example: 300 ms after exiting vehicle clears path per ground truth)

**ACC_TC_011 — Multiple Vehicles in Path (Correct Nearest-Target Selection)**
- *Why:* Verifies target selection logic picks the correct (nearest, in-path) object among several candidates, not the largest RCS or a stale track.
- Requirement ID: `SYSREQ-ACC-0027` | Test Type: Functional | Test Level: SIL / HIL
- Initial Conditions: Three in-path/near-path vehicles at 60 m, 100 m, 160 m
- Expected Result: Nearest in-path vehicle (60 m) selected as Primary Target
- KPI: Correct target selected in 100% of N repeated trials at this configuration

**ACC_TC_012 — Stationary Vehicle Ahead (Documented Behavior)**
- *Why:* Legacy RADAR-based ACC systems historically suppress braking for stationary in-path targets to avoid false full-stop events from roadside clutter (signs, manhole covers). This test documents and verifies the *actual, specified* behavior for the program under test — do not assume either behavior without checking the requirement.
- Requirement ID: `SYSREQ-ACC-0028` | Test Type: Functional / Boundary | Test Level: HIL / Vehicle (closed track only)
- Expected Result: System behaves exactly per the specified requirement (either: brakes for a confirmed-stationary in-path target above a confidence threshold, or: does not treat stationary targets as followable and relies on driver/AEB) — the test's pass criterion is conformance to spec, not a general safety judgment
- Remarks: Must be run on a closed track only, with a soft/collapsible target, per standard ADAS safety-test protocol

**ACC_TC_013 — Slow Vehicle Ahead (Below Set Speed, Steady)**
- *Why:* Straightforward gap-control functional case at a large speed differential.
- Requirement ID: `SYSREQ-ACC-0029` | Test Type: Functional | Test Level: HIL
- Initial Conditions: Set speed 120 km/h, lead vehicle steady at 40 km/h, gap 100 m
- Expected Result: Smooth, bounded deceleration to 40 km/h with settled selected gap
- KPI: Peak deceleration within comfort/urgency band appropriate to closing rate and gap

**ACC_TC_014 — Fast Vehicle Ahead (Above Set Speed)**
- *Why:* Verifies the system correctly ignores a target that is not speed-limiting.
- Requirement ID: `SYSREQ-ACC-0030` | Test Type: Functional | Test Level: HIL
- Initial Conditions: Set speed 90 km/h, in-path vehicle detected doing 130 km/h ahead
- Expected Result: Ego remains in speed-control mode at 90 km/h; target may be shown as "detected" on HMI but does not affect longitudinal control
- KPI: No unintended deceleration triggered by the faster target

**ACC_TC_015 — Stop-and-Go: Full Stop Behind Stopping Lead Vehicle**
- *Why:* Distinct control mode (hold-to-stop) with its own failure modes (rollback, incomplete stop, late brake-hold).
- Requirement ID: `SYSREQ-ACC-0035` | Test Type: Functional | Test Level: HIL / Vehicle (closed track)
- Initial Conditions: Following at 30 km/h, lead vehicle decelerates to a full stop in traffic
- Expected Result: Ego decelerates smoothly and comes to a complete, held stop at the selected gap behind the lead vehicle, brake-hold engaged (no creep/rollback)
- CAN Signals: `ACC_Stop_State`, `Brake_Hold_Request`, `Vehicle_Speed`
- KPI: Final stopping gap within defined bound (example: selected gap ± 1 m); zero rollback distance while held

**ACC_TC_016 — Stop-and-Go: Auto-Resume Within Timeout Window**
- *Why:* Verifies the auto-resume feature (where implemented) launches smoothly and only within the specified time window.
- Requirement ID: `SYSREQ-ACC-0036` | Test Type: Functional | Test Level: HIL / Vehicle
- Initial Conditions: Ego held stopped behind stopped lead vehicle; lead vehicle moves off after 2 s (within example 3 s auto-resume window)
- Expected Result: Ego automatically resumes and re-establishes gap-controlled follow without driver input
- KPI: Resume launch acceleration ≤ comfort limit; resume triggered only when lead vehicle displacement exceeds the specified minimum (avoids resuming on driver-imperceptible target jitter)

**ACC_TC_017 — Stop-and-Go: Resume Timeout Requires Driver Input**
- *Why:* Negative-adjacent functional case — verifies the system does *not* auto-resume after the timeout, protecting against unintended launch when the driver's attention has genuinely lapsed.
- Requirement ID: `SYSREQ-ACC-0037` | Test Type: Functional | Test Level: HIL
- Initial Conditions: Ego held stopped; lead vehicle moves off after 6 s (beyond example 3 s window)
- Expected Result: Ego remains held; HMI indicates resume-required; ego only launches on explicit driver input (accelerator tap or resume switch)
- KPI: Zero unintended launch beyond timeout in N trials

**ACC_TC_018 — Highway Merge / Congestion Steady-State**
- *Why:* Composite realistic scenario validating overall system stability under continuously varying target speed, representative of the most common real-world use case.
- Requirement ID: `SYSREQ-ACC-0040` | Test Type: Functional | Test Level: Vehicle (test track, drive cycle) / SIL (drive-cycle replay)
- Initial Conditions: Recorded/replayed congested-highway speed profile (repeated accel/decel between 20–80 km/h)
- Expected Result: ACC tracks the lead profile throughout without oscillation, harsh transients, or mode-arbitration errors
- KPI: RMS speed-tracking error over the full cycle ≤ defined bound; zero jerk-limit violations; zero unintended disengagements

### Boundary, Negative, and Corner-Case Matrix (ACC_TC_019 – ACC_TC_035)

| ID | Category | Objective (Why) | Key Test Input / Condition | Expected Result | KPI / Pass Criterion |
|---|---|---|---|---|---|
| ACC_TC_019 | Boundary | Verify behavior exactly at minimum engagement speed | Attempt ACC Set at engagement-speed boundary (example: 30 km/h ±1) | Engages at/above threshold, refuses (with HMI message) below it | Threshold matches spec ±1 km/h, no engagement below floor |
| ACC_TC_020 | Boundary | Verify behavior at maximum settable speed | Increase set speed to program max (example: 180 km/h) then attempt +1 more | Set speed clamps at max, no further increase, no fault | Clamp value = spec max exactly |
| ACC_TC_021 | Boundary | Minimum RADAR detection distance | Target introduced at minimum spec detection range | Target detected and classified within spec latency | Detection range ≥ spec minimum in N trials |
| ACC_TC_022 | Boundary | Maximum RADAR detection distance | Target at maximum spec detection range, closing slowly | Target detected, low-confidence/tentative track state correctly shown | Detection at ≥ spec max range with correct confidence flag |
| ACC_TC_023 | Boundary | TTC threshold for urgency escalation | Reduce gap until TTC crosses the defined urgency threshold (example: 3.0 s) | Deceleration urgency band changes exactly at threshold, not before/after | Escalation trigger within ±0.1 s of spec TTC |
| ACC_TC_024 | Boundary | Object size/classification limit | Introduce object at minimum classifiable RCS/size (e.g., motorcycle-scale target) | Correctly detected/classified per spec-defined minimum object size | Detection consistent at spec boundary size |
| ACC_TC_025 | Negative | RADAR sensor failure during active follow | Simulate RADAR internal fault (HIL fault injection) while gap-controlling | ACC disengages to Standby, driver notified, no uncontrolled brake/accel request left active | Transition to safe state ≤ defined latency, DTC set correctly |
| ACC_TC_026 | Negative | RADAR blockage (physical obstruction, e.g., mud/ice/bumper cover) | Physically or via HIL simulate blocked RADAR aperture | Blockage detected distinct from "no target," feature suspended with specific blockage message | Correct DTC/HMI distinguishes blockage from sensor failure from no-target |
| ACC_TC_027 | Negative | Camera failure/occlusion during fusion-dependent follow | Inject camera fault while camera contributes to target classification/lane context | Graceful degradation per spec (e.g., RADAR-only fallback with reduced confidence, or full disengage if camera is safety-critical to the function) | Behavior matches documented degradation mode exactly |
| ACC_TC_028 | Negative | CAN timeout on Brake_Request path | HIL: withhold/stop ADAS→Brake ECU CAN message | ACC detects loss of actuation path, disengages safely, DTC set, driver notified | Timeout detection ≤ spec cycle-time multiple (e.g., 3× nominal cycle) |
| ACC_TC_029 | Negative | CAN-FD communication failure (bus-off) | HIL: induce CAN-FD bus-off on ADAS domain | System enters defined fail-safe (feature unavailable), recovers correctly once bus restored | No latched fault after valid bus recovery; correct recovery per Part 0 §5 chain |
| ACC_TC_030 | Negative | Ethernet loss (camera stream, fusion architectures) | HIL: interrupt Ethernet link carrying camera object list/video | Fusion falls back per spec (RADAR-only or full disengage), driver notified | Fallback behavior matches spec; no silent degradation without notification |
| ACC_TC_031 | Negative | Driver brake override | Driver presses brake pedal while ACC actively decelerating for a target | ACC immediately disengages/pauses (per program: Standby or Paused-resumable), full driver braking authority restored instantly | Override recognized ≤ 1 control cycle; zero counter-torque/brake conflict |
| ACC_TC_032 | Negative | Driver accelerator override | Driver presses accelerator while ACC gap-controlling below set speed | Vehicle accelerates per driver demand (overrides ACC target speed) until pedal released, then ACC resumes control | Immediate authority handover, no fight between pedal and ACC torque request |
| ACC_TC_033 | Negative | False target rejection | HIL: inject a low-persistence/low-confidence "ghost" object (RADAR multipath artifact) | System does not brake for the ghost target; requires persistence/confidence threshold before acting | Zero false-brake events across N ghost-object trials |
| ACC_TC_034 | Corner Case | Curved road with steady lead vehicle | Following on a defined-radius curve | Correct in-path classification using yaw-rate/curvature-compensated path prediction; gap maintained | Target retained through curve, no false target-loss |
| ACC_TC_035 | Corner Case | Heavy rain / degraded RADAR & camera performance | Following in simulated/real heavy rain | System either maintains function with adjusted confidence, or degrades per spec with clear driver notification — never silently degrades | Behavior conforms exactly to documented rain-performance spec |

*(Additional corner-case and regression coverage — fog, night, tunnel entry/exit, poor lane markings affecting path-prediction confidence, uphill/downhill grade compensation, ECU reset mid-follow, and post-calibration-change regression — follow the identical template and are included in the full test suite; listed here at matrix level for brevity and expandable on request.)*

---

## 1.4 ACC KPIs

| KPI | Definition | Example Formula | Why it's measured |
|---|---|---|---|
| **Speed error** | Deviation of actual vehicle speed from set speed (speed-control mode) | `e_v = v_actual − v_set` | Direct measure of speed-control loop accuracy |
| **Distance error** | Deviation of actual gap from the gap commanded by the selected time-gap × relative speed | `e_d = d_actual − (TimeGap × v_rel)` | Direct measure of gap-control loop accuracy |
| **Time gap** | Actual following interval | `t_gap = d_actual / v_ego` | The quantity the driver actually perceives/selects |
| **Acceleration** | Longitudinal acceleration commanded/achieved | `a = dv/dt` | Comfort and capability envelope check |
| **Deceleration** | Longitudinal deceleration commanded/achieved | `a = dv/dt` (negative) | Comfort/urgency band verification |
| **Jerk** | Rate of change of acceleration | `j = da/dt` | Primary comfort metric — humans are far more sensitive to jerk than to acceleration magnitude alone |
| **Response time** | Delay from a stimulus (e.g., lead vehicle brake light / deceleration onset) to ego's control reaction onset | `t_response = t_ego_reaction − t_stimulus` | Safety-relevant reaction latency |
| **Target acquisition time** | Delay from an object entering the sensor's true detection envelope to the system classifying it as a valid, actionable target | `t_acq = t_classified − t_ground_truth_entry` | Cut-in and new-target safety margin |
| **Target loss time** | Delay from an object leaving the path/detection envelope to the system dropping the target | `t_loss = t_dropped − t_ground_truth_exit` | Prevents false-continued braking for departed targets |
| **Set-speed accuracy** | Steady-state deviation from the exact set speed | `\|v_actual − v_set\|` at steady state | Basic functional acceptance metric |

All KPIs should be reported as a distribution (mean, P95, max) across N repeated trials, not a single-run number — a single pass does not establish statistical confidence, and P95/max is what actually matters for a safety-adjacent latency or error metric.

---

## 1.5 Requirement-to-Test-Case Examples (5)

**1.** *Requirement:* "ACC shall not engage below [30] km/h." → **Analysis:** atomic, verifiable, has explicit numeric threshold. → **Precondition:** vehicle below threshold, ACC switch pressed. → **Scenario:** test track, incrementally increasing speed through the threshold. → **Steps:** attempt engagement at threshold−5, threshold−1, threshold, threshold+1 km/h. → **Expected:** refusal below threshold (with HMI message), success at/above. → **KPI:** threshold accuracy ±1 km/h. → **Pass/Fail:** exact boundary conformance. *(→ ACC_TC_019)*

**2.** *Requirement:* "ACC shall maintain the selected time gap within ±0.2 s in steady-state highway following." → **Precondition:** ACC Active, gap-control mode, steady lead vehicle. → **Scenario:** constant-speed highway following at each of the discrete gap settings. → **Steps:** stabilize follow, hold 30 s, sample gap continuously. → **Expected:** settled gap within tolerance. → **KPI:** `|t_gap_actual − t_gap_set| ≤ 0.2 s` (P95). *(→ ACC_TC_005, ACC_TC_006)*

**3.** *Requirement:* "Upon loss of the primary longitudinal RADAR sensor, ACC shall transition to Standby within [200] ms and notify the driver via cluster message within [500] ms." → **Precondition:** ACC Active. → **Scenario:** HIL fault injection of RADAR internal fault. → **Steps:** inject fault mid-follow, timestamp against injection. → **Expected:** state transition and notification within respective bounds. → **KPI:** two independent latency measurements. *(→ ACC_TC_025)*

**4.** *Requirement:* "ACC shall not command deceleration exceeding [3.0] m/s² except during a driver-initiated cancel." → **Precondition:** any active gap-control scenario. → **Scenario:** cut-in and hard-lead-braking scenarios (most likely to provoke high deceleration demand). → **Steps:** run full boundary sweep of cut-in gap/closing-speed combinations. → **Expected:** commanded deceleration never exceeds bound. → **KPI:** max deceleration across full scenario sweep. *(→ ACC_TC_009, ACC_TC_007)*

**5.** *Requirement:* "When the driver presses the brake pedal while ACC is active, ACC shall relinquish longitudinal control within [1] control cycle (≤ [20] ms) with no residual actuation request." → **Precondition:** ACC actively controlling (either mode). → **Scenario:** brake override during active gap-control deceleration (worst case — override must win against an already-issued brake request). → **Steps:** issue brake override input while ACC brake request is non-zero; monitor both signals. → **Expected:** ACC brake request drops to zero within one cycle of override detection. → **KPI:** `Brake_Request` signal transition latency relative to `Driver_Brake_Active` transition. *(→ ACC_TC_031)*

---

## 1.6 ACC Defects (5 realistic examples)

**DEFECT-ACC-001**
- Feature: ACC | Severity: Critical | Priority: P1 | Requirement: `SYSREQ-ACC-0025` (cut-in)
- Description: During a cut-in at closing gap < 20 m, peak deceleration measured at 4.2 m/s², exceeding the 3.0 m/s² comfort/spec limit.
- Preconditions: ACC Active, 100 km/h, speed-control mode, no prior target
- Reproduction: HIL cut-in scenario, adjacent vehicle at 60 km/h merging to 25 m ahead
- Expected Behavior: Deceleration ≤ 3.0 m/s²
- Actual Behavior: Peak 4.2 m/s² measured at t+1.1 s post cut-in
- Evidence: CAN trace (`Deceleration_Actual`), HIL scenario log, KPI plot
- Possible Root Cause: Gap-control loop's urgency-band transition threshold set too aggressively relative to spec TTC boundary
- Debugging Approach: Review controller gain scheduling table vs. TTC band definition; compare against SIL model (same defect present in SIL? isolates algorithm vs. target-hardware issue)
- Fix Verification: Re-run full cut-in boundary sweep (ACC_TC_009 + boundary variants)
- Regression: Full functional + boundary suite (algorithm change)

**DEFECT-ACC-002**
- Feature: ACC | Severity: Major | Priority: P2 | Requirement: `SYSREQ-ACC-0028`
- Description: On CAN timeout of the Brake_Request path, DTC is set correctly but driver notification (cluster message) is delayed ~2.1 s against a 500 ms requirement.
- Reproduction: HIL — withhold ADAS→Brake ECU CAN-FD message
- Expected: Notification ≤ 500 ms
- Actual: ~2.1 s
- Possible Root Cause: Notification routed through a lower-priority Gateway message queue shared with non-safety signals
- Debugging Approach: Trace message priority/arbitration on the Gateway; compare bus-load conditions with and without background traffic
- Regression: Communication-timing suite for all safety-notification paths, not just ACC (likely shared Gateway defect)

**DEFECT-ACC-003**
- Feature: ACC | Severity: Major | Priority: P2 | Requirement: `SYSREQ-ACC-0033` (false target rejection)
- Description: In a multi-lane curved-road scenario with guardrail present, an intermittent ghost target from RADAR multipath is occasionally (≈2% of trials) accepted as a valid in-path target, causing a brief (~0.5 s) unwarranted deceleration.
- Reproduction: HIL scenario replay of recorded guardrail-curve multipath signature
- Expected: Zero false-brake events
- Actual: 2/100 trials showed unwarranted deceleration
- Possible Root Cause: Target persistence/confidence threshold marginal for this specific multipath signature at this curvature
- Debugging Approach: Analyze RADAR raw object-list confidence scores across the failing trials; check if threshold or path-prediction curvature-compensation is the primary contributor
- Regression: Full corner-case curve suite + false-target suite after threshold tuning

**DEFECT-ACC-004**
- Feature: ACC | Severity: Minor | Priority: P3 | Requirement: `SYSREQ-ACC-0036` (auto-resume)
- Description: Stop-and-go auto-resume occasionally fails to trigger within the 3 s window when lead vehicle displacement is exactly at the minimum-displacement threshold (borderline classification).
- Reproduction: HIL — lead vehicle moves exactly the spec minimum distance at low speed
- Expected: Resume triggers consistently at/above threshold
- Actual: Resume triggers in 7/10 trials at exact threshold (marginal sensor noise around the boundary)
- Root Cause: No hysteresis on the displacement-threshold comparison, so sensor noise flips the decision near the boundary
- Debugging Approach: Add hysteresis band or require N consecutive samples above threshold before triggering
- Regression: Stop-and-go suite (ACC_TC_015–017)

**DEFECT-ACC-005**
- Feature: ACC | Severity: Minor | Priority: P3 | Requirement: `SYSREQ-ACC-0021` (time-gap setting)
- Description: After a CAN database (DBC) update changing the scaling of `TimeGap_Setting`, HIL regression showed the second-shortest gap setting displayed correctly on HMI but was internally applied as the shortest setting.
- Reproduction: Cycle gap switch through all settings post-DBC-update, compare commanded vs. displayed
- Expected: Displayed and applied setting match
- Actual: Off-by-one mapping for setting #2 only
- Root Cause: Signal scaling/offset table not updated consistently between HMI display mapping and ACC controller input mapping after DBC change
- Debugging Approach: Diff old vs. new DBC for `TimeGap_Setting`, check both consumer mappings (HMI, ACC controller) against the new definition
- Regression: Full communication-validation suite for all changed signals in that DBC release (Part 0 §2.5 — CAN database change)

---

## 1.7 ACC Interview Preparation

### Basic (10)
1. **What is ACC and how does it differ from conventional cruise control?** — ACC additionally senses and follows a lead vehicle, automatically adjusting speed to maintain a set time gap, whereas conventional cruise control only holds a fixed speed with no environment sensing.
2. **What sensors does ACC typically use?** — Long-range RADAR as the primary longitudinal sensor, often fused with a forward camera for classification and lane-geometry context; some systems are RADAR-only.
3. **What is a time gap and why is it used instead of a fixed distance?** — The following interval in seconds; using time gap (not fixed distance) naturally scales the following distance with speed, matching how a safe following distance actually needs to grow with speed.
4. **What happens when the driver presses the brake pedal during ACC operation?** — ACC immediately relinquishes longitudinal control; the driver has full, instant override authority.
5. **What is the minimum operating speed limitation of many ACC systems?** — Non-stop&go ACC systems typically have a minimum engagement speed (commonly around 30 km/h example) below which the feature is unavailable.
6. **What is Stop-and-Go ACC?** — An extension of ACC that brings the vehicle to a full stop behind a stopped lead vehicle and can hold or auto-resume within a defined window.
7. **What ECUs does the ADAS domain controller communicate with to execute ACC control?** — Brake ECU (deceleration request), Powertrain ECU (acceleration/torque request), and often Transmission (gear-hold), over CAN/CAN‑FD.
8. **What is target selection in ACC?** — The process of choosing, among all detected objects, the nearest valid in-path object as the vehicle to follow.
9. **Why can't ACC be relied upon to stop for all stationary objects?** — Historically, RADAR-based systems suppress braking for stationary in-path targets above a certain confidence threshold to avoid false full-stop events from roadside clutter; actual behavior is program/spec-defined and must be verified, not assumed.
10. **What is the difference between speed-control mode and gap-control mode in ACC?** — Speed-control mode holds the driver's set speed when no valid lead vehicle is present; gap-control mode holds the selected time gap behind a detected lead vehicle when one is present and speed-limiting.

### Intermediate (10)
1. **How would you test ACC's target acquisition time for a cut-in scenario?** — Define ground truth (independent reference sensor/marker for when the cutting-in vehicle truly enters the path), inject the scenario repeatedly in HIL, timestamp the system's `Target_Detected_Flag` transition, and compute the latency distribution (mean/P95/max) against a spec threshold.
2. **How do you distinguish a sensor-blockage fault from a "no target present" state in test?** — Blockage is verified via a distinct DTC/diagnostic flag (e.g., RADAR self-diagnostic reporting reduced aperture/output confidence) rather than inferred from absence of targets; a dedicated fault-injection test (physical obstruction or HIL-simulated blockage signal) is required.
3. **What's the risk of only testing ACC KPIs as a mean value rather than a distribution?** — A mean can hide a long tail — e.g., 95% of trials meet a latency target but 5% dangerously exceed it — which matters for safety-relevant timing; P95/max reporting is required for meaningful acceptance.
4. **Why is jerk measured in addition to acceleration/deceleration?** — Human comfort/discomfort correlates more strongly with the rate of change of acceleration (jerk) than with acceleration magnitude alone; a smooth deceleration to a hard limit feels very different from an abrupt one to the same limit.
5. **How would you validate that ACC correctly arbitrates between speed-control and gap-control modes?** — Construct scenarios that force transitions in both directions (target appears/disappears, target speed crosses above/below set speed) and verify the system always obeys the mode that yields the lower target speed, with correct, glitch-free transitions.
6. **What's the purpose of testing at the exact minimum engagement speed boundary rather than well above/below it?** — Boundary conditions are where off-by-one and threshold-comparison defects concentrate; testing well clear of the boundary can pass while the actual threshold implementation is wrong.
7. **How do you test the interaction between driver accelerator override and ACC?** — Verify that pressing the accelerator during gap-control immediately hands longitudinal authority to the driver (no fight/conflict with ACC's torque request), and that ACC resumes control correctly, without a speed jump, once the pedal is released.
8. **What would you check first if ACC shows correct behavior in SIL but incorrect behavior in HIL for the same scenario?** — Timing and communication-layer differences: real ECU boot/scheduling, real bus load/arbitration, real sensor object-list latency/jitter not modeled in SIL — narrows whether the defect is algorithmic (would also show in SIL) or platform/timing-related (HIL-only).
9. **How would you design a regression suite after a RADAR supplier change?** — Re-run the full sensor-validation suite (Part 0 §10-equivalent: range, RCS/classification boundaries, ghost-object rejection) plus all functional/boundary ACC test cases that depend on target acquisition/loss timing, since a new RADAR's detection characteristics can shift those KPIs even with unchanged software.
10. **How do you verify ACC does not exceed the driver's set speed even when following a faster lead vehicle?** — Construct a scenario where the tracked in-path target is above set speed and confirm ego's controlled speed never exceeds set speed, across multiple target-speed values above the set point.

### Advanced (10)
1. **How would you design a statistically defensible acceptance test for target acquisition latency?** — Define the population of representative cut-in scenarios (relative speed × gap × classification type sweep), determine required sample size for the target confidence level on the P95 metric, run in HIL/SIL at scale, and report the full distribution against the spec threshold rather than a single pass/fail run.
2. **How would you debug an intermittent false-brake event that only reproduces 2% of the time?** — Capture full raw sensor data (not just the object list) on every trial so failing runs can be replayed exactly; look for a specific environmental signature (multipath geometry, road curvature, specific RCS pattern) correlated with failures; replay the failing raw data offline against the exact algorithm version to separate a data-dependent defect from a timing-dependent one.
3. **How do you validate the interaction between ACC and ESC (Electronic Stability Control) during a simultaneous stability event?** — Verify ACC suspends/limits its deceleration or acceleration request when ESC signals an active stability intervention, to avoid the two control loops fighting; test with induced low-friction/oversteer conditions on a controlled surface.
4. **What's your approach to validating ACC's behavior across a full sensor field-of-view boundary, not just directly ahead?** — Sweep target lateral offset and ego yaw-rate/curvature combinations to verify the in-path classification boundary matches the specified path-prediction model, including on curves where a target can be geometrically "ahead" but algorithmically out-of-path.
5. **How would you approach root-causing a defect that only appears after a specific CAN-FD bus-load condition?** — Reproduce with controlled bus-load injection (background traffic at defined loads) in HIL, correlate defect onset with specific load thresholds, and check for message-queue starvation or priority-inversion on the safety-relevant signal path.
6. **How do you validate long-tail corner cases like fog or heavy rain where sensor physics can't be fully modeled in SIL?** — Combine SIL model refinement using fleet-collected field data (calibrating the sensor degradation model against real degraded-condition sensor logs) with targeted vehicle testing in representative real or environmentally-controlled conditions (fog chamber, rain rig) to validate SIL's fidelity, then rely on SIL for regression scale once fidelity is established.
7. **How would you structure requirement traceability for ACC across ASPICE SWE.1–SWE.6?** — Requirement (SWE.1/SWE.2) → architectural/design element implementing it (SWE.3) → unit test (SWE.4) → integration test (SWE.5) → system/qualification test case per this document's template (SWE.6), each level's test results linked back to the originating requirement ID for full bidirectional traceability.
8. **How do you decide the sample size N for repeated-trial KPIs like target acquisition time?** — Based on the required confidence/precision on the specific percentile being reported (e.g., P95 requires a larger N than a mean estimate for the same confidence interval width); statistically, tighter tolerances or higher percentiles require larger N — this is typically defined in the test strategy, not decided ad hoc per test case.
9. **What is a realistic ACC-related ISO 26262 hazard, and how does it map to a test case?** — Example hazard: "unintended ACC deceleration insufficient during required following-distance closure" contributing to rear-end collision risk; maps to safety goal → functional safety requirement (e.g., max target-acquisition/response latency) → technical safety requirement → the specific latency/response test cases in this section (ACC_TC_005, 007, 009).
10. **How would you validate ACC's degraded-mode behavior when only one of two fused sensors (RADAR/camera) is available?** — Verify against the documented degradation matrix (which capabilities are retained/reduced/disabled per single-sensor loss), test each single-sensor-available combination independently, and confirm driver notification correctly reflects the actual degraded capability (not a generic "ACC unavailable" if partial capability remains, if that's the spec'd behavior).

### Scenario-Based (10)
1. **A lead vehicle brakes hard directly in front of you at close range under ACC — walk through what you'd verify.** — Verify: deceleration escalates appropriately with closing TTC, does not exceed the vehicle's physical/comfort limits inappropriately for the urgency level, hands off cleanly to AEB if TTC crosses the AEB intervention threshold (interaction boundary between ACC and AEB), and driver retains full override capability throughout.
2. **You're testing ACC on a test track and the vehicle oscillates (brake-release-brake) while following a steady lead vehicle. What do you check?** — Controller gain tuning/deadband around the gap-control setpoint, sensor object-list jitter/noise feeding a noisy setpoint, and control-loop cycle time/latency that could cause a lag-induced oscillation; capture the CAN trace of commanded vs. actual deceleration to distinguish a control-tuning issue from a sensor-noise issue.
3. **A construction zone with temporary, confusing lane markings causes ACC's target selection to behave unpredictably. How do you approach this as a corner case?** — Log the full scenario for offline replay, check whether target selection relies on camera lane geometry for path prediction (construction zones commonly defeat lane-based path prediction), and determine whether the observed behavior conforms to a documented degraded-confidence mode or is a genuine defect.
4. **A vehicle two lanes over drifts briefly into your ACC target's lane and back out. Should this affect your ACC target?** — It should not cause target loss or a new target acquisition if it never becomes the nearest in-path object; this is exactly the kind of scenario a false-target-rejection/persistence-threshold test (ACC_TC_033-style) is designed to catch if it does.
5. **How would you test ACC behavior transitioning from a tunnel (GPS/lighting change, no RADAR impact) into bright sunlight glare?** — Since RADAR is largely unaffected by lighting, focus on camera-dependent functions within ACC (if camera contributes to classification/path prediction) — verify no false degradation is triggered by lighting transition alone, and that any camera-confidence-driven fallback behaves correctly and recovers promptly once glare clears.
6. **You observe ACC failing to detect a stopped vehicle at night in a corner case test. What's your triage sequence?** — Check RADAR performance first (largely lighting-independent — was the stationary-target suppression the actual cause, per spec, not a nighttime defect at all), then check whether camera-fusion contribution to target confidence was degraded by low light and whether that correctly/incorrectly affected the fusion confidence score.
7. **A defect report says "ACC felt harsh during a cut-in" from a subjective drive. How do you convert that into an objective test?** — Reproduce the exact cut-in parameters (closing speed, gap, lateral entry rate) in HIL with instrumented deceleration/jerk logging, compare against the comfort-limit KPI thresholds, and determine if it's a genuine spec violation or a subjective-but-within-spec experience (which may still warrant a calibration review, but is a different disposition).
8. **How would you test whether an OTA software update changed ACC's gap-control tuning unintentionally?** — Run the full functional + boundary regression suite (Part 0 §2.5) comparing KPI distributions (settling time, deceleration profile, jerk) before and after the update on identical scenario replays, flagging any statistically significant shift even if all individual tests still "pass" against absolute thresholds.
9. **How do you validate ACC's behavior when the driver manually shifts gears (manual transmission or paddle-shift override) while ACC is active?** — Verify ACC correctly suspends/resumes torque requests around the gear-change event without a torque spike or unintended deceleration, and that mode/state is preserved correctly across the transient.
10. **A fleet data review shows ACC disengages more often than expected on a specific highway interchange. How would you investigate?** — Pull the fleet logs for that location (sensor data, DTCs, disengagement flag/reason code at each event), look for a common signature (e.g., a specific curvature/guardrail/overpass geometry causing repeated sensor confidence drops), then attempt to reproduce the exact geometry in SIL/HIL for controlled root-cause analysis.

### Debugging Questions (5)
1. **ACC intermittently fails to re-engage after a Cancel. How do you isolate the cause?** — Check whether the failure correlates with any specific prior state (was a fault latched? was the set-speed memory corrupted?); replay the exact CAN sequence around the failure from logs; test with a HIL-scripted repeat of the exact Cancel→Set sequence at scale to get a reliable reproduction rate before root-causing.
2. **CAN trace shows `Brake_Request` is correct, but the vehicle doesn't decelerate as commanded. Where do you look next?** — Downstream of the ADAS ECU: verify the Brake ECU actually received and acted on the request (its own log/response signal), check for a CAN-FD signal-scaling mismatch between transmitter and receiver DBC definitions, and check whether a competing/higher-priority brake-inhibiting condition (e.g., ESC arbitration) is suppressing execution.
3. **A HIL regression test that passed for months suddenly fails after a scenario-library update. How do you determine if it's a real defect or a test-asset issue?** — Diff the scenario definition file itself first (did the "same" scenario's parameters silently change with the library update?); if the scenario is unchanged, then treat it as a genuine regression and proceed to algorithm-level root cause.
4. **SIL and HIL disagree on target acquisition time for the identical scenario. How do you narrow the cause?** — Compare object-list timestamps at each stage (sensor model/real sensor output → fusion → target selection) between the two environments; a difference concentrated at the sensor-input stage points to sensor-model fidelity; a difference concentrated after fusion points to a genuine timing/algorithm platform difference.
5. **You suspect a specific DBC change broke `Target_Distance` scaling but the signal "looks reasonable" on a quick check. How do you confirm it precisely?** — Cross-check the raw CAN payload bytes against both the old and new DBC definitions by hand/script for a known ground-truth distance, rather than trusting a plausible-looking decoded value — an incorrect scale/offset can still produce numbers that look superficially reasonable across part of the range.

### Test-Case-Design Questions (5)
1. **Design a test case (at template level) to verify ACC does not accelerate into a newly-revealed stationary hazard immediately after a cut-out.** — Preconditions: following a lead vehicle that then cuts out to reveal a stationary object beyond it. Test Type: Negative/Boundary. Expected: system does not accelerate toward set speed without first correctly evaluating the newly-revealed object per the documented stationary-target policy; KPI: no unintended acceleration if the revealed object is within the applicable detection/action envelope.
2. **Design a boundary test for the maximum closing-speed differential ACC is required to handle for a cut-in.** — Sweep relative closing speed from spec-nominal up to the spec-maximum handled differential; Expected: deceleration remains within the defined maximum band up to and at the boundary, with an explicit, documented (not silently degraded) behavior above the boundary (e.g., handover to AEB or driver).
3. **Design a regression-focused test case to run after any RADAR firmware update.** — Re-run the sensor-validation range/RCS-boundary suite and the target-acquisition-latency KPI suite (ACC_TC_009, 021, 022) with before/after KPI-distribution comparison, since a firmware update can shift detection sensitivity without any ACC application-software change.
4. **Design a test case verifying ACC correctly reports "feature unavailable" rather than silently doing nothing when a required precondition is missing (e.g., ESC fault present).** — Preconditions: induce an ESC fault; Test Inputs: attempt ACC Set; Expected: explicit "ACC unavailable" HMI message, not a silent refusal with no feedback; Pass/Fail: message displayed within defined latency, and the reason is retrievable via diagnostics.
5. **Design a fault-injection test case for a "missing signal" fault (a required CAN signal simply absent from the bus, as opposed to timed-out) on the RADAR object-list message.** — Test Type: Fault Injection; HIL: remove the message entirely (not just delay it) from the simulated bus; Expected: distinguished from a timeout (may have a tighter or different detection latency requirement) and from a valid "no object" state; follow the Fault→Detection→Diagnostic→Reaction→Notification→Recovery chain from Part 0 §5.

---

*End of Part 1 (ACC). Part 2 (LKA) follows the identical structure: feature understanding, architecture, 30–35+ test cases, KPIs, requirement-to-test examples, defects, and interview prep.*