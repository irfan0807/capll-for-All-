# ADAS Test Case Design & Validation — Part 2: LKA (Lane Keeping Assist)

*Continues the series. Part 0 (Framework & Methodology) defines the test case template, categories, and SIL/HIL/vehicle methodology used here. All numeric values are example values unless stated otherwise.*

---

## 2.1 Feature Understanding

**Purpose of LKA.** LKA is a lateral-control feature that actively steers the vehicle to keep it centered (or within) its lane, intervening with corrective steering torque when the vehicle drifts toward or crosses a lane boundary — distinct from a warning-only feature (LDW, covered in Part 3) in that LKA *acts* on the steering system rather than only alerting the driver.

**Lane detection.** A forward camera identifies lane boundary features (painted markings, road edges, botts' dots, curbs where markings are absent) in the image, typically producing a set of detected lane-boundary points or a parametric curve fit per boundary (left and right).

**Lane model.** The detected boundary points are fit to a mathematical model — commonly a clothoid or polynomial curve (e.g., a 3rd-order polynomial: lateral offset as a function of longitudinal distance, capturing lane curvature, heading angle, and offset) — that predicts the lane geometry ahead of the vehicle, including through short gaps in the visible markings.

**Vehicle lateral position.** The vehicle's offset from the lane center (and/or from each boundary), computed from the lane model relative to the camera's known mounting geometry, is the primary control-error input to the lateral controller.

**Lane center.** The midpoint between left and right lane boundary models at a given longitudinal distance; LKA's steering target is typically to minimize offset from this center line (as opposed to LDW, which only cares about proximity to the boundary itself).

**Lane departure prediction.** Using current lateral position, lateral velocity (rate of drift), and often a short time horizon (e.g., predicted position 1–2 s ahead), the system estimates whether the vehicle will cross a lane boundary if no correction occurs — this predictive element is what allows LKA to intervene *before* a boundary is actually touched, not after.

**Steering intervention.** Once departure is predicted (or, in some architectures, once lane-center offset exceeds a threshold even without imminent departure — a "lane centering" variant), the system applies a corrective torque request to the Steering ECU (typically an EPS — Electric Power Steering — system), proportional to the offset/predicted-departure severity, bounded by defined maximum torque and rate limits for driver comfort and to remain easily overridable.

**Driver override.** The system is explicitly designed to be overridable by the driver applying steering torque above a defined threshold (indicating deliberate driver steering input, e.g., an intentional lane change without signaling) — LKA must yield authority promptly and not fight the driver.

**LKA availability conditions.** Typically requires: vehicle speed within an operating band (commonly disabled below a minimum speed, e.g., ~60 km/h for many highway-oriented LKA systems, and above a maximum where lateral dynamics are outside the validated envelope), lane markings detected with sufficient confidence on at least one side (implementation-dependent whether single-side operation is supported), no conflicting driver input (e.g., turn signal active, which typically suspends intervention to allow an intentional lane change), and no active faults in camera or steering path.

---

## 2.2 LKA Architecture

```text
Front Camera
     |
     v
Lane Detection
     |
     v
Lane Model
     |
     v
Vehicle Position Estimation
     |
     v
Lateral Control Algorithm
     |
     v
Steering ECU
     |
     v
Steering Actuator
```

**Data flow:**
- **Camera → ADAS ECU:** lane boundary points/curve parameters, confidence per boundary, marking type (dashed/solid), typically over Automotive Ethernet or CAN‑FD depending on architecture.
- **ADAS ECU (Vehicle Position Estimation):** fuses lane model with ego vehicle signals — yaw rate, wheel speed, steering angle (from the Steering ECU / chassis bus) — to estimate lateral position and predicted trajectory relative to the lane.
- **ADAS ECU → Steering ECU (EPS):** torque request (or angle request, depending on architecture), request-active flag, intervention-type flag, over CAN‑FD, cyclic.
- **Steering ECU → ADAS ECU:** actual applied torque, driver hands-on/override torque estimate, steering angle sensor value, EPS fault status.
- **ADAS ECU → Cluster/HMI:** LKA state (Off/Standby/Active/Suppressed/Unavailable), lane-detection confidence icon (both sides / one side / none), intervention indication.
- **Turn Signal (Body ECU) → ADAS ECU:** turn-signal-active flag, used to suspend intervention during an intentional driver-initiated lane change.
- **Gateway:** routes cross-domain signals (e.g., steering angle to cluster, LKA state to body domain) as required by the vehicle's E/E architecture.

---

## 2.3 LKA Test Cases

35 test cases, grouped by category. Cases 1–17 in full template detail; cases 18–35 in a compact matrix (same template fields, condensed for readability).

### Functional

**LKA_TC_001 — LKA Activation on Straight Road with Clear Markings**
- *Why:* Baseline functional gate — confirms activation preconditions and steady centering behavior before any edge case is tested.
- Requirement ID: `SYSREQ-LKA-0010` | Test Type: Functional | Test Level: Vehicle / HIL
- Preconditions: Speed within operating band (example: ≥60 km/h), both lane boundaries detected with high confidence, no faults, LKA switched on by driver
- Test Environment: Test track, straight road, clear painted lines
- Vehicle State: 90 km/h, gear D, steering hands-on
- Test Steps: 1) Drive straight at 90 km/h. 2) Enable LKA. 3) Observe steering behavior for 30 s.
- Expected Result: LKA state = Active; vehicle held near lane center with minor, smooth corrective torque; no oscillation.
- CAN Signals: `LKA_State`, `Lane_Offset`, `Steering_Torque_Request`
- KPI: Lateral error ≤ 0.15 m (example) steady-state, no oscillation (torque sign reversals ≤ defined rate)
- Pass/Fail: `LKA_State == ACTIVE` AND lateral error within bound for ≥20 s continuous
- Postcondition: LKA remains active

**LKA_TC_002 — Gradual Left Lane Departure Triggers Corrective Steering**
- *Why:* Core intervention behavior — verifies the predictive-departure logic engages before boundary crossing.
- Requirement ID: `SYSREQ-LKA-0015` | Test Type: Functional | Test Level: HIL / Vehicle
- Initial Conditions: Vehicle drifting left at a slow, steady rate (example: 0.3 m/s lateral) with no turn signal
- Expected Result: Corrective steering torque applied proportional to predicted departure, before the wheel contacts the boundary line; vehicle returns toward lane center
- CAN Signals: `Lane_Offset`, `Predicted_Departure_Flag`, `Steering_Torque_Request`
- KPI: Intervention onset occurs at predicted-crossing time ≥ defined margin (example: ≥0.5 s before actual boundary contact would occur)
- Pass/Fail: No boundary crossing occurs; intervention torque within defined comfort/effectiveness band

**LKA_TC_003 — Gradual Right Lane Departure**
- *Why:* Mirror of TC_002; verifies symmetry of left/right intervention (a common asymmetric-defect area, e.g., camera lateral calibration bias).
- Requirement ID: `SYSREQ-LKA-0015` | Test Type: Functional | Test Level: HIL / Vehicle
- Expected Result: Symmetric behavior to TC_002, mirrored
- KPI: Intervention onset timing and torque magnitude within defined tolerance of the left-side equivalent (asymmetry check)

**LKA_TC_004 — Fast (Abrupt) Lane Departure**
- *Why:* Verifies the system scales its response to departure rate, not just offset — a fast drift needs a faster/firmer correction than a slow one at the same offset.
- Requirement ID: `SYSREQ-LKA-0016` | Test Type: Functional | Test Level: HIL
- Initial Conditions: Higher lateral drift rate (example: 1.0 m/s)
- Expected Result: Earlier and/or firmer intervention than the slow-drift case, still within max torque/rate limits
- KPI: Intervention onset scales inversely with drift rate per the predictive-departure model; peak torque within max bound

**LKA_TC_005 — Curved Road, Steady Lane-Center Tracking**
- *Why:* Verifies the lane model correctly represents curvature (not just straight-line offset) and the controller tracks a curved reference correctly.
- Requirement ID: `SYSREQ-LKA-0018` | Test Type: Functional | Test Level: HIL / Vehicle
- Initial Conditions: Defined-radius curve (example: 500 m radius), both markings visible
- Expected Result: Vehicle tracks near lane center through the curve, smooth continuous steering (not a series of discrete corrections)
- KPI: Lateral error ≤ defined bound through curve, no oscillation

**LKA_TC_006 — Sharp Curve (Boundary of Curvature Capability)**
- *Why:* Verifies documented behavior at/near the system's specified maximum curvature capability, distinct from the moderate-curve functional case.
- Requirement ID: `SYSREQ-LKA-0019` | Test Type: Functional / Boundary | Test Level: HIL / Vehicle (closed track)
- Initial Conditions: Curve radius at spec minimum (example: 250 m)
- Expected Result: System either maintains tracking within relaxed (but still specified) tolerance, or correctly suspends intervention with driver notification if beyond capability — behavior must match documented spec exactly
- KPI: Conformance to documented curvature-capability behavior

**LKA_TC_007 — Different Lane Widths (Narrow and Wide)**
- *Why:* Verifies the lane model and controller adapt correctly rather than assuming a fixed nominal width.
- Requirement ID: `SYSREQ-LKA-0020` | Test Type: Functional | Test Level: HIL
- Initial Conditions: Narrow lane (example: 3.0 m) and wide lane (example: 4.0 m), tested separately
- Expected Result: Correct lane-center computation and tracking in both cases
- KPI: Lateral error bound met independent of lane width within the spec'd width range

**LKA_TC_008 — Dashed Lane Markings**
- *Why:* Verifies the lane model correctly interpolates across gaps between dashes rather than losing tracking repeatedly.
- Requirement ID: `SYSREQ-LKA-0021` | Test Type: Functional | Test Level: HIL / Vehicle
- Expected Result: Continuous, stable lane model maintained across dash gaps; no intervention drop-out at each gap
- KPI: Lane-model confidence remains above minimum-operation threshold continuously across dash pattern

**LKA_TC_009 — Solid Lane Markings**
- *Why:* Baseline marking-type functional case; also relevant to confirming no unintended behavior difference is introduced by marking-type-specific logic (e.g., some programs treat solid-line departure as higher-priority).
- Expected Result: Stable tracking; if program-specific solid-line intervention prioritization exists, verify it activates correctly

**LKA_TC_010 — Double Lane Markings**
- *Why:* Verifies correct boundary selection when more than one line is present per side (e.g., dashed+solid combination, common at merge/HOV lane boundaries).
- Requirement ID: `SYSREQ-LKA-0022` | Test Type: Functional | Test Level: HIL
- Expected Result: System selects the correct (innermost, ego-lane-defining) line per spec, not the outer/adjacent-lane line

**LKA_TC_011 — Lane Merge (Boundary Geometry Change)**
- *Why:* Verifies stable behavior through a geometry discontinuity, a known stress case for lane-model continuity.
- Requirement ID: `SYSREQ-LKA-0023` | Test Type: Functional | Test Level: HIL / Vehicle
- Expected Result: No abrupt/incorrect steering command as the lane boundary geometry changes at the merge point; system either tracks the new geometry smoothly or suspends intervention with notification if confidence drops below threshold

**LKA_TC_012 — Construction Zone with Temporary Markings**
- *Why:* Corner case combining marking-type change, potential conflicting old/new markings, and reduced confidence — realistic and high-value.
- Requirement ID: `SYSREQ-LKA-0024` | Test Type: Corner Case | Test Level: Vehicle (data-collection) / HIL (replay)
- Expected Result: Documented degraded-confidence behavior (suspension with notification) rather than following an incorrect/ambiguous marking set

**LKA_TC_013 — Driver Steering Input Below Override Threshold**
- *Why:* Verifies LKA continues normal operation for small, non-deliberate driver steering inputs (e.g., minor correction), not incorrectly interpreting them as an override.
- Requirement ID: `SYSREQ-LKA-0026` | Test Type: Functional | Test Level: HIL / Vehicle
- Test Inputs: Driver applies steering torque below the defined override threshold while LKA is correcting
- Expected Result: LKA continues its intervention, blended with the driver's minor input, no full disengagement
- KPI: LKA remains Active; no unintended override triggered below threshold

**LKA_TC_014 — Driver Torque Override (Deliberate Lane Change, No Signal)**
- *Why:* Safety-critical — driver authority must always win; verifies prompt, clean handover.
- Requirement ID: `SYSREQ-LKA-0027` | Test Type: Functional | Test Level: Vehicle / HIL
- Test Inputs: Driver applies steering torque above override threshold, no turn signal
- Expected Result: LKA immediately suspends intervention (torque request → 0), driver has full unimpeded steering authority
- CAN Signals: `Driver_Override_Torque`, `Steering_Torque_Request`
- KPI: Override recognition and torque-request removal within ≤1 control cycle
- Pass/Fail: Zero counter-torque after override threshold crossed

**LKA_TC_015 — Hands-Off Detection (Where Supported)**
- *Why:* Verifies the system correctly distinguishes true hands-off from light/passive hands-on, and reacts per the defined escalation policy (this is program-dependent; some LKA variants require hands-on and escalate warnings if hands-off is detected for too long).
- Requirement ID: `SYSREQ-LKA-0028` | Test Type: Functional | Test Level: Vehicle / HIL
- Expected Result: Hands-off state correctly detected (via torque sensor pattern or dedicated capacitive sensor, per program) and escalation sequence (warning stages) proceeds exactly per spec timing

**LKA_TC_016 — Turn Signal Suspends Intervention for Intentional Lane Change**
- *Why:* Verifies LKA doesn't fight a driver's deliberate, signaled lane change.
- Requirement ID: `SYSREQ-LKA-0029` | Test Type: Functional | Test Level: HIL / Vehicle
- Test Inputs: Driver activates turn signal, then drifts across the boundary in the signaled direction
- Expected Result: No corrective intervention while turn signal is active and departure direction matches signal direction
- KPI: Zero intervention torque during a correctly-signaled lane change in N trials

**LKA_TC_017 — Steering Intervention Cancellation Once Vehicle Re-Centers**
- *Why:* Verifies the controller correctly winds down intervention (not an abrupt cutoff) once the vehicle returns to a safe lateral position, avoiding an overshoot-then-fight cycle.
- Requirement ID: `SYSREQ-LKA-0030` | Test Type: Functional | Test Level: HIL
- Expected Result: Torque request smoothly ramps to zero as lateral offset returns within the nominal band, no oscillation or overshoot beyond defined bound

### Boundary, Negative, and Corner-Case Matrix (LKA_TC_018 – LKA_TC_035)

| ID | Category | Objective (Why) | Key Test Input / Condition | Expected Result | KPI / Pass Criterion |
|---|---|---|---|---|---|
| LKA_TC_018 | Boundary | Minimum operating speed | Attempt/hold LKA activation across the minimum-speed threshold | Suspends below threshold, resumes at/above, with correct HMI messaging | Threshold accuracy ±1 km/h |
| LKA_TC_019 | Boundary | Maximum operating speed | Accelerate through the maximum-speed threshold | Suspends above threshold if spec'd, correct HMI messaging | Threshold accuracy ±1 km/h |
| LKA_TC_020 | Boundary | Minimum lane width capability | Reduce simulated/track lane width to spec minimum | Tracking maintained within relaxed-but-specified tolerance, or documented suspension below capability | Conformance to spec |
| LKA_TC_021 | Boundary | Maximum lane width capability | Increase lane width to spec maximum | Correct lane-center computation, no false-boundary lock to unrelated markings (e.g., adjacent lane) | Lateral error within bound at max width |
| LKA_TC_022 | Boundary | Maximum steering torque/rate limit | Force a scenario demanding maximum correction (fast departure at high curvature) | Torque and torque-rate never exceed defined maximum, even under worst-case demand | Zero limit violations across N worst-case trials |
| LKA_TC_023 | Boundary | Minimum lane-detection confidence for activation | Gradually degrade marking visibility (fading paint simulation) to threshold | Activation/continuation gated exactly at confidence threshold | Threshold conformance |
| LKA_TC_024 | Negative | Camera failure during active intervention | HIL: inject camera fault mid-intervention | LKA suspends immediately, torque request → 0, driver notified, no residual steering command | Suspension latency ≤ defined bound, zero residual torque |
| LKA_TC_025 | Negative | Camera blockage (physical obstruction) | Simulate/physically obstruct camera lens | Distinct blockage DTC/HMI message vs. generic failure vs. low-confidence-no-markings | Correct fault classification |
| LKA_TC_026 | Negative | Missing lane marking (one side) | One boundary marking entirely absent for an extended stretch | System behavior matches documented single-side-operation policy (continues with reduced confidence indication, or suspends) exactly | Conformance to spec policy |
| LKA_TC_027 | Negative | Poor/faded lane markings | Low-contrast, degraded marking scenario (real or simulated) | Reduced-confidence indication, no erratic/false intervention | No false intervention; correct confidence signaling |
| LKA_TC_028 | Negative | Steering ECU (EPS) failure | HIL: inject EPS fault while LKA active | LKA suspends, driver notified, steering reverts to full manual (no residual assist anomaly) | Suspension + notification within defined bounds |
| LKA_TC_029 | Negative | CAN timeout on torque-request path | HIL: withhold ADAS→Steering ECU CAN-FD message | Timeout detected, LKA suspends safely, DTC set | Detection ≤ spec cycle-time multiple |
| LKA_TC_030 | Negative | CAN-FD bus-off | HIL: induce bus-off | Feature unavailable, correct recovery once bus restored, no latched fault | Recovery per Part 0 §5 chain |
| LKA_TC_031 | Negative | Ethernet loss (camera link) | HIL: interrupt Ethernet carrying lane-model data | LKA suspends per spec, driver notified | Conformance to spec fallback |
| LKA_TC_032 | Corner Case | Night driving | Low-light lane tracking (real or simulated) | Tracking maintained within relaxed nighttime tolerance, or documented degradation with notification | Conformance to spec; no false intervention |
| LKA_TC_033 | Corner Case | Rain / wet road with reduced marking contrast | Wet-road, rain scenario | Correct confidence degradation handling, no false/erratic intervention | Zero false-intervention events |
| LKA_TC_034 | Corner Case | Strong sunlight / glare, tunnel exit | Backlighting/glare transition scenario | Brief, bounded confidence dip handled gracefully (no hard fault latch for a transient condition) | Recovery ≤ defined bound after glare clears |
| LKA_TC_035 | Corner Case | Adjacent large vehicle (truck) partially occluding markings | Truck alongside partially occluding one boundary | System does not incorrectly lock onto the truck's edge as a lane boundary | Zero false-boundary-lock events |

*(Additional coverage — poor-marking + curve combination, adjacent motorcycle proximity, road-edge-only detection where no markings exist, and post-camera-recalibration regression — follows the identical template and is included in the full suite; summarized here for brevity.)*

---

## 2.4 LKA KPIs

| KPI | Definition | Example Formula | Why it's measured |
|---|---|---|---|
| **Lateral error** | Deviation of vehicle (typically center of front axle or camera reference point) from lane center | `e_y = y_vehicle − y_lane_center` | Primary control-accuracy metric |
| **Lane offset** | Distance from vehicle to nearest boundary | `d_boundary = lane_width/2 − \|e_y\|` | Direct margin-to-departure metric |
| **Lane departure warning time** (as used by LKA's predictive trigger) | Time between predicted-departure flag and actual would-be boundary crossing | `t_warn = t_crossing_predicted − t_flag_raised` | Verifies adequate intervention lead time |
| **Steering intervention time** | Duration from departure prediction to intervention onset | `t_intervene = t_torque_onset − t_departure_predicted` | Response-latency metric |
| **Steering angle** | Actual road-wheel or steering-wheel angle during intervention | Sensor reading | Verifies intervention magnitude is physically reasonable |
| **Steering torque** | Commanded and actual torque at the EPS | Sensor/CAN signal | Comfort and limit-conformance metric |
| **Lateral acceleration** | Resulting vehicle lateral acceleration from intervention | `a_y` from IMU/estimation | Comfort/stability bound |
| **Yaw rate** | Vehicle rotational rate during correction | Sensor reading | Stability and correction-smoothness indicator |
| **Vehicle heading error** | Angular difference between vehicle heading and lane tangent direction | `e_ψ = ψ_vehicle − ψ_lane` | Secondary control-error term (most lateral controllers use combined lateral + heading error) |

As with ACC KPIs, report distributions (mean/P95/max) across repeated trials, not single-run values.

---

## 2.5 Requirement-to-Test-Case Examples (5)

**1.** *Requirement:* "LKA shall not be available below [60] km/h." → **Precondition:** vehicle below threshold. → **Scenario:** speed sweep through threshold. → **Steps:** attempt activation at threshold−5, −1, at, +1 km/h. → **Expected:** unavailable below, available at/above, with HMI message when unavailable. → **KPI:** threshold accuracy. *(→ LKA_TC_018)*

**2.** *Requirement:* "LKA shall initiate corrective steering at least [0.5] s before a predicted lane-boundary crossing, for lateral drift rates between [0.1] and [1.0] m/s." → **Precondition:** LKA Active, both boundaries detected. → **Scenario:** sweep drift rate across the specified range. → **Steps:** induce each drift rate, timestamp predicted-crossing time vs. actual intervention-onset time. → **Expected:** margin ≥0.5 s across the full rate range. → **KPI:** intervention-lead-time distribution. *(→ LKA_TC_002, LKA_TC_004)*

**3.** *Requirement:* "LKA shall relinquish control within [1] control cycle of driver-applied override torque exceeding [X] Nm." → **Precondition:** LKA actively intervening. → **Scenario:** worst case — override applied at peak intervention torque. → **Steps:** apply override torque ramp, timestamp against `Driver_Override_Torque` threshold crossing and `Steering_Torque_Request` zeroing. → **Expected:** immediate handover. → **KPI:** transition latency. *(→ LKA_TC_014)*

**4.** *Requirement:* "LKA shall not apply corrective torque during a turn-signal-active, signal-direction-matching lane change." → **Precondition:** turn signal active. → **Scenario:** signaled departure in both directions, separately. → **Steps:** activate signal, drift in matching direction; repeat opposite direction (should still intervene, since it's not signal-matching). → **Expected:** zero intervention for matching-direction case, normal intervention for non-matching. → **KPI:** intervention-suppression correctness rate. *(→ LKA_TC_016)*

**5.** *Requirement:* "Upon camera failure, LKA shall suspend within [150] ms with zero residual torque request." → **Precondition:** LKA actively intervening (worst case — mid-correction). → **Scenario:** HIL camera fault injection during active torque application. → **Steps:** inject fault, timestamp against `Steering_Torque_Request` transition to zero. → **Expected:** suspension within bound, zero residual. → **KPI:** suspension latency + residual-torque check. *(→ LKA_TC_024)*

---

## 2.6 LKA Defects (5 realistic examples)

**DEFECT-LKA-001**
- Feature: LKA | Severity: Critical | Priority: P1 | Requirement: `SYSREQ-LKA-0027` (override)
- Description: During a fast, deliberate driver steering input (simulated aggressive lane change without signal) at high intervention torque, a brief (~150 ms) counter-torque "fight" was measured before full handover, instead of immediate release.
- Preconditions: LKA Active, mid-intervention, high commanded torque
- Reproduction: HIL — apply override torque ramp during peak LKA torque output
- Expected: Immediate (≤1 cycle) torque-request removal
- Actual: ~150 ms overlap with residual LKA torque before dropping to zero
- Root Cause: Override-detection threshold comparison used a filtered/averaged torque signal with a filter time constant that delayed detection under fast-changing input
- Debugging Approach: Compare raw vs. filtered override-torque signal timing; evaluate filter time constant against worst-case override ramp rate
- Fix Verification: Re-run LKA_TC_014 at multiple override ramp rates, confirm ≤1-cycle response across all
- Regression: Full driver-override and hands-off suite

**DEFECT-LKA-002**
- Feature: LKA | Severity: Major | Priority: P2 | Requirement: `SYSREQ-LKA-0022` (double markings)
- Description: On a road segment with a dashed lane-change line adjacent to a solid HOV-boundary line, the system occasionally selected the outer (HOV-boundary) line as the ego-lane boundary, causing LKA to steer toward the HOV lane.
- Reproduction: HIL replay of recorded double-marking geometry
- Expected: Innermost, ego-lane-defining line always selected
- Actual: Outer line selected in 3/50 trials at a specific approach angle
- Root Cause: Boundary-selection logic's line-classification confidence was marginal when both lines had similar detected contrast/width
- Debugging Approach: Analyze raw lane-detection candidate list and confidence scores for the failing trials; check if marking-type classification (dashed vs. solid) is being weighted correctly in the selection logic
- Regression: Double-marking and lane-merge suite (LKA_TC_010, LKA_TC_011)

**DEFECT-LKA-003**
- Feature: LKA | Severity: Major | Priority: P2 | Requirement: `SYSREQ-LKA-0019` (sharp curve)
- Description: At curve radii near the specified minimum, lateral error exceeded the relaxed-tolerance bound (measured 0.35 m against a 0.25 m allowed bound) without the system falling back to the documented suspension behavior.
- Reproduction: HIL, curve radius sweep down to spec minimum
- Expected: Either tracking within relaxed bound, or documented suspension — not silent out-of-tolerance tracking
- Actual: Continued active tracking outside tolerance with no suspension or notification
- Root Cause: Curvature-capability check used a look-ahead-distance-based curvature estimate that lagged the true instantaneous curvature entering a tightening curve
- Debugging Approach: Compare estimated vs. ground-truth curvature over the curve entry transient; evaluate look-ahead window sizing
- Regression: Full curve-boundary suite (LKA_TC_006, 020, 021)

**DEFECT-LKA-004**
- Feature: LKA | Severity: Minor | Priority: P3 | Requirement: `SYSREQ-LKA-0021` (dashed markings)
- Description: On a long dash-gap pattern (gap length near the upper end of the spec'd range), lane-model confidence briefly dipped below the operation threshold, causing a momentary (~400 ms) unintended suspension and re-activation.
- Reproduction: HIL replay of long-gap dash pattern
- Expected: Continuous operation across the full spec'd gap-length range
- Actual: Brief suspension at maximum gap length
- Root Cause: Lane-model confidence decay rate during a gap was tuned conservatively relative to the maximum spec'd gap length
- Debugging Approach: Review confidence decay/hold logic parameters against the exact spec'd maximum dash-gap value
- Regression: Marking-type suite (LKA_TC_008, LKA_TC_009)

**DEFECT-LKA-005**
- Feature: LKA | Severity: Minor | Priority: P3 | Requirement: `SYSREQ-LKA-0029` (turn signal suppression)
- Description: When the turn signal is cancelled (auto-cancel after the lane change completes) while the vehicle is still slightly mid-transition, LKA re-engaged intervention slightly early, applying a small corrective torque before the vehicle had fully settled in the new lane, producing a minor "tug."
- Reproduction: HIL — signaled lane change, auto-cancel timed at the exact moment of lane-center crossing
- Expected: Smooth re-engagement without a perceptible torque transient
- Actual: Small torque step measured at re-engagement (~2 Nm step vs. expected smooth ramp-in)
- Root Cause: Re-engagement logic did not ramp in intervention gain gradually after suppression ended, applying full gain immediately
- Debugging Approach: Review re-engagement gain-ramp logic vs. suppression-release logic for consistency
- Regression: Turn-signal-suppression suite (LKA_TC_016, LKA_TC_017)

---

## 2.7 LKA Interview Preparation

### Basic (10)
1. **What is LKA and how does it differ from LDW?** — LKA actively applies corrective steering torque to keep the vehicle in its lane; LDW only warns the driver without acting on the steering (detailed comparison in Part 3).
2. **What sensor is primarily used for LKA?** — A forward-facing camera, used to detect lane boundary markings and build a lane model.
3. **What is a lane model?** — A mathematical (typically polynomial or clothoid) representation of the lane boundary geometry ahead of the vehicle, fit from detected marking points.
4. **What happens when the driver applies significant steering torque during LKA intervention?** — LKA immediately relinquishes control (override), giving the driver full, unimpeded steering authority.
5. **Why does LKA typically have a minimum operating speed?** — The system is validated and tuned for a specific dynamic operating envelope (typically highway-oriented); below that speed, lateral dynamics and typical use cases (parking lots, low-speed maneuvering) fall outside the validated envelope.
6. **What does the turn signal do to LKA behavior?** — Activating the turn signal in the direction of drift suspends intervention, allowing an intentional, signaled lane change without the system fighting the driver.
7. **What is lane departure prediction?** — Using current lateral position and drift rate (and often a short time horizon) to estimate whether the vehicle will cross a boundary if uncorrected, allowing intervention before the boundary is actually reached.
8. **What ECU does LKA send its steering command to?** — The Steering ECU (typically an Electric Power Steering / EPS system), via a torque or angle request over CAN/CAN‑FD.
9. **What happens if the camera fails while LKA is actively steering?** — LKA suspends immediately, the torque request drops to zero (no residual steering command), and the driver is notified.
10. **Can LKA operate reliably with only one lane boundary detected?** — Behavior is program/spec-dependent — some systems support reduced-confidence single-side operation, others suspend; this must be verified against the actual requirement, not assumed.

### Intermediate (10)
1. **How would you test that LKA's intervention timing scales correctly with drift rate?** — Sweep lateral drift rate across the specified range in HIL, measure intervention onset time relative to predicted-crossing time at each rate, and verify the lead-time margin holds throughout the range, not just at a single nominal rate.
2. **How do you verify LKA doesn't fight the driver during a legitimate, unsignaled but deliberate steering input?** — Verify the override-torque threshold and detection latency are correctly tuned so that torque above the threshold reliably and quickly releases LKA control, using a worst-case scenario (override applied during peak LKA intervention torque, per DEFECT-LKA-001-style testing).
3. **Why is asymmetry (left vs. right intervention) a specific thing to test for?** — Camera lateral mounting/calibration bias or asymmetric algorithm tuning can cause different intervention timing/magnitude for left vs. right departures even though the requirement is symmetric; this is a real, historically-seen defect class, not a theoretical concern.
4. **How would you test correct lane-boundary selection when double markings are present?** — Construct scenarios with dashed+solid combinations at realistic geometries (HOV lane boundaries, lane-change zones) and verify the innermost, ego-lane-defining boundary is always selected, across multiple approach angles and marking-contrast conditions.
5. **What's the difference between testing LKA on a straight road vs. a curved road, from a lane-model perspective?** — Straight-road testing primarily validates lateral-offset estimation and basic control loop stability; curved-road testing additionally validates the curvature term of the lane model and the controller's ability to track a continuously changing reference, which is a materially different (and often more defect-prone) code path.
6. **How would you test LKA's behavior through a construction zone with confusing/overlapping markings?** — Collect and replay real or representative confusing-marking data in HIL, and verify the system falls back to its documented low-confidence behavior (suspension with notification) rather than confidently following an ambiguous or incorrect marking set.
7. **Why is it important to test hands-off detection timing precisely, where supported?** — The escalation sequence (warning stages, potential feature suspension) is often itself a distinct safety requirement with defined timing; testing it precisely (not just "it eventually warns") ensures the driver-engagement safety net behaves as specified.
8. **How do you validate LKA doesn't lock onto an adjacent vehicle's edge as a lane boundary?** — Construct scenarios with a large vehicle (truck/bus) alongside partially occluding true lane markings, and verify the lane model doesn't substitute the vehicle's visual edge for the actual marking — a known camera-perception failure mode.
9. **What would you check if LKA's lateral error KPI looks good in SIL but shows a small steady-state bias in vehicle testing?** — Camera extrinsic calibration (mounting angle/offset) is the first suspect for a steady-state (not transient) bias, since SIL's sensor model may not capture real-world calibration tolerance; verify calibration data and consider whether the bias is within a documented acceptable calibration tolerance band.
10. **How would you design regression tests after a camera firmware/algorithm update?** — Re-run the full functional + boundary lane-tracking suite with before/after KPI-distribution comparison (lateral error, intervention timing), plus the marking-type and confidence-threshold suites, since perception changes can shift these without any lateral-controller software change.

### Advanced (10)
1. **How would you validate LKA's predictive-departure model's accuracy independent of the controller's response?** — Log the model's predicted crossing time/position against ground-truth actual crossing time/position (from an independent reference, e.g., high-precision GPS/lane-map ground truth) across many drift-rate/curvature combinations, with LKA's intervention disabled or the prediction logged open-loop, isolating perception/prediction accuracy from control-loop behavior.
2. **How do you approach validating lane-model performance in genuinely ambiguous real-world scenarios where even a human reviewer disagrees on the "correct" lane boundary?** — Define an explicit adjudication protocol (e.g., majority vote among multiple trained reviewers, or defer to the physical road-edge/legal lane definition where markings are ambiguous) before scoring, since without a consistent ground-truth definition, a KPI computed against inconsistent labels is not meaningful.
3. **How would you root-cause a lateral-error KPI that's fine on average but has a long tail of large excursions?** — Segment the trial population by scenario attribute (curvature, marking type, weather, speed) and look for a KPI shift concentrated in a specific segment rather than uniformly distributed — a long tail usually indicates a specific under-tested condition rather than a generally-marginal controller.
4. **What's the relationship between LKA's override-torque threshold and steering-system-level requirements (e.g., ISO 11429/technical steering-effort standards)?** — The override threshold must be set low enough that a driver applying a normal, deliberate steering effort is recognized promptly (safety/controllability requirement) but high enough that incidental torque (road camber, minor corrections) doesn't falsely trigger override (nuisance/availability requirement) — this is a genuine engineering trade-off validated through both objective threshold testing and subjective drive evaluation.
5. **How would you validate LKA and ACC don't produce conflicting or unsafe combined behavior when both are active simultaneously?** — Construct combined scenarios (e.g., simultaneous curve-tracking and gap-control deceleration) and verify each feature's actuation domain (lateral vs. longitudinal) remains independently within its own limits, with no unexpected cross-coupling (e.g., verify braking-induced weight transfer doesn't degrade lane-tracking beyond its own specified tolerance).
6. **How do you validate lane-model performance is invariant to reasonable camera-mounting tolerance across vehicle build variation?** — Test across a sample of vehicles (or a HIL-injected range) spanning the specified camera-mounting tolerance band (angle/height/lateral offset tolerances from the mechanical spec) and verify lateral-error KPIs remain within bound across that entire tolerance range, not just at nominal mounting.
7. **What's your approach to statistically bounding the false-intervention rate (unwarranted torque with no genuine departure) to a very low target (e.g., <1 in 10,000 km)?** — Combine high-volume SIL/HIL replay of fleet-collected real-world drive data (much higher scenario throughput than physical testing can achieve) with targeted vehicle testing to validate SIL fidelity, since directly driving enough kilometers to statistically observe a rare-event rate at that target is generally impractical.
8. **How would you validate LKA's behavior is ASIL-appropriate per ISO 26262 for the relevant hazard (unintended steering intervention)?** — Trace the hazard ("unintended lateral control causing unintended lane departure") to its safety goal and ASIL rating, then verify the technical safety requirements (e.g., max unintended torque magnitude, max override-response latency) are each covered by specific, traceable test cases with appropriate independence/rigor for that ASIL level (e.g., additional fault-injection coverage, diverse redundancy checks if applicable).
9. **How do you handle a scenario where LKA's intervention is technically within all defined KPI/tolerance bounds but "feels wrong" to test drivers?** — Treat it as a valid finding distinct from a spec non-conformance — log it as a calibration/tuning observation with objective supporting data (torque/jerk profile, comparison to a benchmark competitor or prior calibration), and route it to the algorithm/calibration owner for a tuning decision, since "within spec" and "well-tuned" are not automatically the same thing.
10. **How would you design a test strategy for LKA's interaction with a subsequent SAE Level 2+ lane-centering or hands-off feature built on the same lane-model input?** — Validate the underlying lane-model/perception layer's KPIs independently (shared foundation), then validate each feature's specific control-layer behavior and its specific availability/handoff conditions separately, ensuring a lane-model defect is only fixed once (shared root layer) while each feature's distinct control behavior is independently regression-tested.

### Scenario-Based (10)
1. **LKA intervenes correctly on a test track but a field report describes "phantom tugging" on a specific public road. How do you investigate?** — Request/collect the specific location's fleet log data (lane-model confidence, offset, torque request over the reported segment), attempt to identify a specific road feature (faded markings, pavement seam, shadow pattern) correlated with the events, and replay the exact logged perception data in SIL/HIL for controlled root-cause analysis.
2. **A driver reports LKA felt like it "fought" them during a lane change. What do you check first?** — Whether a turn signal was active and correctly detected at the time (suppression should have applied), and if it was active, whether the suppression logic itself has a defect; if no signal was active, this may be expected/documented behavior (intervention against an unsignaled departure) that needs to be explained rather than treated as a defect.
3. **You're validating LKA on a road with a shadow cast diagonally across the lane by an overpass. How would you approach this as a corner case?** — Treat it as a lighting/contrast corner case similar to strong-sunlight/tunnel-transition testing — verify the lane model doesn't misinterpret the shadow edge as a marking or lose confidence unrecoverably, using real or simulated shadow-pattern data.
4. **A curve section shows correct lateral-error KPIs but yaw-rate data shows an oscillatory pattern not visible in the lateral-error metric alone. Why might you still flag this?** — Lateral error alone can mask a controller that's oscillating around the correct average path — yaw-rate (or steering-torque) oscillation is a comfort/stability concern independent of whether the position error stays within bound, so it should be flagged and investigated as a tuning issue even with "passing" lateral-error KPIs.
5. **How would you test LKA behavior when transitioning from a well-marked highway onto a poorly-marked rural connector road?** — Construct a transition scenario spanning both marking-quality regimes, and verify the system smoothly transitions its confidence/availability state (not an abrupt or delayed suspension) as marking quality degrades, with correct, timely driver notification.
6. **A motorcycle is riding near the lane boundary line your vehicle is drifting toward. How does this scenario intersect with LKA testing?** — While LKA's own responsibility is lane-keeping (not object avoidance — that's ACC/AEB's domain), verify LKA's intervention doesn't itself induce an unsafe lateral movement in the direction of a detected adjacent road user, which may require cross-checking with any object-awareness input the specific program's LKA design incorporates, if any (implementation-dependent — verify against the actual architecture).
7. **How would you test that an OTA update to the lane-model algorithm hasn't quietly changed intervention aggressiveness?** — Run before/after KPI-distribution comparison (intervention onset timing, torque magnitude/rate) across the full functional and boundary suite on identical scenario replays, flagging any statistically significant shift even where each individual test still passes absolute thresholds.
8. **A test track run shows correct LKA behavior, but a subsequent HIL regression run of the identical scenario shows a different (incorrect) result. How do you triage?** — Compare exact scenario parameters and initial conditions bit-for-bit between the two runs (a nominally "identical" scenario can differ subtly in initial lateral offset, speed, or lane-model seed state), and check for non-determinism in the HIL scenario or software itself before concluding it's a genuine intermittent defect.
9. **How would you validate LKA's behavior specifically at the moment a dashed-to-solid marking transition occurs (e.g., approaching an intersection)?** — Construct a scenario with the transition point at a controlled location, and verify no discontinuity in intervention behavior (torque step, confidence drop) occurs exactly at the transition, testing the transition point itself as a distinct condition from steady dashed or steady solid marking testing.
10. **How would you approach validating LKA in a right-hand-traffic vs. left-hand-traffic market variant?** — Verify both the lane-model/perception layer (should be symmetric/configurable) and any asymmetric logic (e.g., market-specific override thresholds, if any) are correctly configured and tested per market variant, since a defect could be specific to one traffic-direction configuration only.

### Debugging Questions (5)
1. **Lateral error looks correct in log data, but the recorded video shows the vehicle visibly off-center. What do you check?** — Verify the units/sign convention and reference point used in the logged signal match what's visually apparent (e.g., logged error might be relative to a different reference point than the visually obvious lane center, or there's a sign-convention bug in the logging/display path itself, distinct from an actual control defect).
2. **An intervention-timing regression test fails intermittently in HIL only under specific bus-load conditions. How do you isolate it?** — Reproduce with controlled, incrementally increasing background CAN-FD bus load, and identify the specific load threshold where the timing KPI degrades, checking for message-queue delay on the perception-to-controller or controller-to-EPS signal path.
3. **You see the correct predicted-departure flag timing in logs, but the actual torque-request signal lags behind it more than expected. Where do you look?** — Check the control-loop's own internal latency (filter delays, control-cycle scheduling) between receiving the departure prediction and computing/transmitting the torque request — this narrows whether the delay is in perception-to-decision or decision-to-actuation.
4. **A specific vehicle build shows consistently higher lateral error than the validation fleet average, across all scenarios. What's your first hypothesis and how do you check it?** — Camera mounting/calibration for that specific vehicle — verify its extrinsic calibration data against the fleet-average/nominal values before suspecting a software or algorithm difference.
5. **Two nominally identical HIL test runs of the same scenario produce different lateral-error trajectories. How do you determine if this is expected noise or a real non-determinism defect?** — Check whether the scenario/sensor-model seed and any randomized elements (sensor noise injection) are controlled/repeatable across runs; if the test setup intentionally includes randomized noise, some variation is expected and should be evaluated statistically, not as a pass/fail difference between two single runs.

### Test-Case-Design Questions (5)
1. **Design a boundary test for LKA's maximum specified curvature capability, including the documented fallback behavior.** — Sweep curve radius from the specified minimum capability down through and below it; Expected: tracking within relaxed tolerance at/above the capability boundary, and explicit, notified suspension below it (per DEFECT-LKA-003, verify no silent out-of-tolerance operation occurs at the boundary).
2. **Design a negative test verifying LKA does not apply steering torque based on a stale (no-longer-updating) lane model.** — HIL: freeze the lane-model output (simulate a perception processing hang) while continuing to run the control loop; Expected: system detects the stale data (via a model-update timestamp/freshness check) and suspends rather than continuing to act on outdated geometry.
3. **Design a regression test case to run specifically after any change to the override-torque threshold calibration.** — Re-run the full driver-override suite (LKA_TC_014, plus a sweep of override-torque ramp rates and magnitudes just above/below both old and new threshold values) to confirm the new threshold behaves as intended without reintroducing a fight/lag condition (per DEFECT-LKA-001).
4. **Design a test case verifying correct LKA suppression behavior specifically during a turn-signal-active period where the driver does NOT actually depart the lane (signal on, no lane change follows).** — Preconditions: turn signal active, no drift occurring; Expected: LKA remains in normal centering operation (suppression only applies to intervention against a matching-direction departure, not a blanket disable) — this distinguishes over-broad suppression logic from correctly-scoped suppression.
5. **Design a fault-injection test case for a "missing signal" (as opposed to timeout) fault on the lane-model CAN/Ethernet message, following the Part 0 §5 fault chain.** — Test Type: Fault Injection; HIL: remove the lane-model message entirely from the bus/network; Expected: distinguished from both a timeout and a valid "no lane detected" state, verified through the full Fault→Detection→Diagnostic→Reaction→Notification→Recovery chain, with correct DTC and driver notification.

---

*End of Part 2 (LKA). Part 3 (LDW, including the LDW vs. LKA comparison) follows the identical structure.*