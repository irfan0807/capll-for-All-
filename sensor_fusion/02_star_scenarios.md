# Sensor Fusion — STAR Format Interview Scenarios
## 10 Real Interview Answers | April 2026

STAR = **S**ituation → **T**ask → **A**ction → **R**esult

---

## STAR Scenario 1 — False Emergency Braking From Ghost Radar Target

**SITUATION:**
During highway validation testing on a test track, the AEB (Autonomous Emergency Braking) system triggered a full braking event at 110 km/h with no object ahead. The vehicle decelerated from 110 km/h to 80 km/h in approximately 1.5 seconds. No injury occurred but the event was highly dangerous. The fusion-based AEB system had been working correctly for the previous 3 days of testing.

**TASK:**
As the validation engineer, I was responsible for analysing the logged data to identify the root cause and deliver a finding within 24 hours so the test programme could continue. I needed to determine whether the false activation was a sensor issue, a fusion algorithm issue, or a system integration issue.

**ACTION:**
I immediately extracted the CANoe MDF4 log from the test vehicle. My investigation followed these steps:

*Step 1 — Reconstruct the event timeline:*
I loaded the log into CANoe and looked at T-2000ms to T+1000ms around the braking event. I found:
- Front radar (ARS540) reported a stationary object at 45m, relative velocity −110 km/h (closing)
- Front camera reported: no object detected
- Fusion ECU: object confidence = 0.87, exceeding AEB trigger threshold of 0.80 → braking commanded

*Step 2 — Characterise the radar detection:*
The detected object had:
- Range: 45m (constant — stationary in road frame)
- Azimuth angle: 0.0° (dead ahead)
- Radar cross-section (RCS): −4 dBsm (unusually low — like a small metal object)
- Duration: detected for only 280ms before braking triggered

*Step 3 — Identify it as a multi-path ghost:*
I checked the road geometry data. At that exact location, there was a highway bridge overpass at 45m. Radar signal from our vehicle bounced off the road surface → up to the bridge underside → reflected back = a phantom stationary object at exactly 45m.
The camera correctly saw no object (no visual target).

*Step 4 — Root cause — fusion weight imbalance:*
The fusion algorithm was giving radar detections very high confidence weight when camera was "no detection" — incorrectly treating camera absence of detection as neutral instead of as active negative evidence.
Correct logic: camera saying "nothing there" should REDUCE object confidence, not leave it unchanged.
The current logic: camera absent → confidence stays at radar value alone (0.87) → triggers AEB.
Corrected logic: camera absent confirmation → apply penalty factor → confidence = 0.87 × 0.7 = 0.61 → below AEB threshold.

*Step 5 — Additional fix — ghost detection filter:*
Added a check: if RCS < −2 dBsm AND object appears for < 300ms → classify as potential ghost, require 3 consecutive radar hits before elevating confidence.

**RESULT:**
- Root cause confirmed: multi-path ghost from bridge underpass + fusion weight error
- Fix delivered within 18 hours: camera negative evidence weighting updated, ghost RCS filter added
- Regression test: 200 passes under the same bridge with no false activations
- Finding documented in JIRA, presented to system architect — fusion weight logic updated in production SW
- Test programme resumed next morning with no further incidents

---

## STAR Scenario 2 — Radar and Camera Objects Misaligned by 1.5 Metres

**SITUATION:**
During object fusion validation (radar-camera object matching), the test analysis showed that radar-detected objects and camera-detected objects for the same real vehicle were consistently offset by 1.5m laterally. This meant the data association algorithm was either creating two separate tracks (one from each sensor) or creating very low-confidence fused tracks, degrading ACC performance.

**TASK:**
Determine whether the offset was a sensor calibration issue, a coordinate transform error, or a data association issue. The deadline was the end of the sprint (5 working days).

**ACTION:**

*Step 1 — Static calibration test:*
I set up a corner reflector (a target with known radar and visual markers) at exactly 20m ahead, 0° azimuth, 0° elevation. Both sensors should detect it at the same position in vehicle frame.
Result: Radar reported (20.1m, 0.1°) — correct. Camera reported (20.1m, 1.5° azimuth) — offset.

*Step 2 — Intrinsic camera check:*
Camera intrinsic parameters (focal length, principal point) were nominal.
Camera intrinsic calibration: PASS.

*Step 3 — Extrinsic calibration check:*
Camera extrinsic = mounting position (tx, ty, tz) + mounting angles (roll, pitch, yaw).
I ran the camera extrinsic calibration verification routine using the calibration target board.
Found: camera yaw angle in extrinsic file = 0.0° but measured actual yaw = 1.7° (mounting bracket had shifted after a rough test-track section).
At 20m: 1.7° yaw error → lateral offset = 20 × sin(1.7°) = 0.59m → at 50m → 1.5m offset. FOUND.

*Step 4 — Re-calibrate and verify:*
Updated extrinsic calibration file with correct yaw = 1.7°.
Rebuilt fusion ECU calibration data.
Re-ran static target test: camera and radar now agree within 0.1m at 20m, 50m, 100m.
Re-ran dynamic driving test: fusion tracks now show single merged track per vehicle, confidence > 0.90.

*Step 5 — Prevented recurrence:*
Added an online extrinsic monitoring check to fusion ECU: if camera and radar objects for the same confirmed track differ by > 0.5m laterally over 10 consecutive frames → set DTC `U3002 CameraExtrinsicDriftDetected` and alert driver via cluster icon.

**RESULT:**
- Extrinsic calibration error found and corrected in 2 days
- Fusion performance restored: 96% correct object association (up from 61%)
- DTC monitor implemented in SW — prevents silent extrinsic drift in future
- Procedure updated: extrinsic calibration must be verified every 500km of test-track driving

---

## STAR Scenario 3 — Pedestrian Missed by Fusion System in City Test

**SITUATION:**
During NCAP AEB pedestrian test (Euro NCAP 2022 protocol), the test vehicle failed to brake for a pedestrian dummy target crossing at 8 km/h. The vehicle was travelling at 30 km/h. The camera correctly detected the pedestrian at 15m distance. The radar did not detect the pedestrian (humans have very low RCS at 77 GHz). The fusion system — which required both sensors to agree for a confirmed pedestrian — produced low confidence. AEB did not trigger.

**TASK:**
The fusion system incorrectly required radar confirmation for pedestrian detections. My task was to analyse the fusion logic, propose a corrected confidence model for low-RCS objects, and validate the fix before the re-test in 2 weeks.

**ACTION:**

*Step 1 — Reproduce and analyse:*
Reviewed fusion ECU object confidence equation:
```
confidence = w_radar × C_radar + w_camera × C_camera
where w_radar = 0.6, w_camera = 0.4

For pedestrian: C_radar = 0 (not detected), C_camera = 0.85
confidence = 0.6×0 + 0.4×0.85 = 0.34

AEB threshold = 0.70 → NOT triggered
```
Root cause: radar weight (0.6) was too high for pedestrian class. Radar is inherently poor at detecting pedestrians (RCS typically −10 to −20 dBsm vs +10 to +20 for cars).

*Step 2 — Research object class weights:*
Reviewed literature, Euro NCAP test protocol, and Continental/Bosch application notes.
Found: pedestrian detection should be camera-primary, with radar providing secondary confirmation only.
Proposed weights by class:
```
Car:          w_radar=0.6  w_camera=0.4  (radar excellent for vehicles)
Pedestrian:   w_radar=0.2  w_camera=0.8  (camera primary for pedestrians)
Cyclist:      w_radar=0.3  w_camera=0.7  (mid-range)
```

*Step 3 — Validate proposed weights against test data:*
Applied new weights to logged data from 50 NCAP test runs (recorded but not re-driven):
```
New pedestrian confidence = 0.2×0 + 0.8×0.85 = 0.68
Still below 0.70 threshold — needs threshold adjustment too
```
Further tuned: lowered AEB pedestrian threshold to 0.65 (acceptable false positive analysis shows < 0.5 FP/100km).

*Step 4 — Re-validate:*
Updated fusion ECU parameters (weights + pedestrian threshold).
Ran 20 controlled NCAP VRU (Vulnerable Road User) scenarios.
Result: 19/20 AEB triggered correctly. 1 miss at extreme angle (89° crossing — within NCAP exclusion zone).

**RESULT:**
- NCAP re-test PASSED all pedestrian AEB scenarios
- Score improvement: pedestrian AEB score 75% → 94% (NCAP star rating maintained)
- Object-class-specific fusion weights adopted as standard in programme
- Published internal learning note for fusion weight tuning across platform

---

## STAR Scenario 4 — Track ID Instability Causing ACC Speed Oscillation

**SITUATION:**
During motorway ACC validation, a speed oscillation was reported: the vehicle was following a target at 110 km/h with set speed 130 km/h. Every 3–4 seconds, the ACC speed would briefly increase (vehicle accelerated slightly) before correcting. The customer perception: "ACC is hunting, it's uncomfortable."

**TASK:**
Debug the ACC speed control instability and identify whether it was a control system issue or a sensor fusion issue. I was sole engineer on this investigation for the week.

**ACTION:**

*Step 1 — Data analysis:*
Logged ACC controller input: `target_object_id` and `target_object_distance`.
Found: the track ID assigned to the vehicle ahead was switching between two IDs every 3–4 seconds.
When the ID switches, the ACC controller interprets it as losing the target and briefly reverts to set-speed mode (130 km/h) before re-acquiring the new track.

*Step 2 — Why was the track ID switching?*
Loaded the fusion object log. Found two tracks were being maintained simultaneously for the same vehicle ahead:
- Track A: from front radar (long-range, high confidence, ID=42)
- Track B: from camera (shorter range, slightly different position, ID=55)

The merger algorithm was oscillating: it merged the tracks, then split them, then merged, then split — every 3–4 seconds.

*Step 3 — Identify merger oscillation cause:*
The merge criterion: merge if distance between tracks < 0.8m.
The split criterion: split if distance between tracks > 1.2m.
At 110 km/h, normal lateral oscillation of the target vehicle (lane keeping hunting) = ±0.5m.
When target drifts 0.9m laterally →  merge condition failed (0.9 > 0.8) → split.
When target comes back → merge again. Cycle repeats at the lane-keeping frequency.

*Step 4 — Fix:*
Increased merge hysteresis: merge threshold 1.2m, split threshold 2.0m (wider band prevents oscillation at normal lane-keeping amplitudes).
Additionally: once tracks are merged into one ID, ACC controller must not treat track ID change as a target loss — added "track handover" event that passes distance/velocity to new ID without discontinuity.

**RESULT:**
- ACC hunting eliminated on all subsequent test runs
- Merge hysteresis values documented and applied across all speed ranges
- ACC smoothness metric (jerk during following) improved by 60%
- Finding: first-of-type issue, no prior documentation — wrote wiki page on fusion track oscillation for team

---

## STAR Scenario 5 — Fusion System Fails LiDAR Alignment Qualification Test

**SITUATION:**
A new LiDAR sensor (solid-state, 120° FoV) was being integrated into an existing radar-camera fusion stack. The LiDAR qualification test (static geometric accuracy) was failing: LiDAR-detected object positions were offset from radar-detected positions by up to 2.5m at 50m range. This was before any dynamic testing.

**TASK:**
Lead the LiDAR-to-radar extrinsic calibration and verify alignment within a 2-week window before the integration test gate.

**ACTION:**

*Step 1 — Extrinsic calibration setup:*
Built a 5-target checkerboard + radar reflector array (each board has both a visual pattern for LiDAR/camera and a corner reflector for radar) at positions: 10m, 20m, 30m, 50m, 70m ahead and at ±10° lateral angles.

*Step 2 — Initial offset measurement:*
At 50m, 0° azimuth:
```
Radar reports:  (50.1m,  0.1°) ← reference
LiDAR reports:  (50.2m, 2.8°) ← offset
Expected offset: < 0.2°
Actual offset:   2.7° → 2.5m lateral at 50m
```

*Step 3 — Calculate required extrinsic correction:*
```
LiDAR nominal mounting: tx=-0.3m (behind radar), ty=0.0m, tz=-0.15m, yaw=0°, pitch=0°, roll=0°

Measured actual yaw = 2.7° (LiDAR was rotated during installation)
Corrected extrinsic: yaw = -2.7°
```

*Step 4 — Apply and retest:*
Updated LiDAR extrinsic calibration file in the fusion ECU configuration.
Reran all 15 target positions.
Maximum residual error after correction: 0.12m at 50m → within 0.3m specification.

*Step 5 — Dynamic validation:*
Drove 10 overlapping passes at 30/50/80 km/h past a known obstacle course.
LiDAR and radar tracks now fully merge (90% association rate, up from 22%).

**RESULT:**
- Extrinsic calibration completed in 8 days (within 2-week gate)
- Static accuracy: max error 0.12m at 50m (spec: 0.3m) — PASS
- Dynamic association rate: 90%+ (spec: 85%) — PASS
- Integration test gate PASSED, schedule maintained
- LiDAR extrinsic calibration procedure written and added to the vehicle preparation SOP

---

## STAR Scenario 6 — Sensor Fusion Causing Unnecessary ACC Deceleration at Tunnel Entrance

**SITUATION:**
ACC was performing unexpected deceleration events (−0.3g) as the vehicle approached motorway tunnel entrances at 120 km/h. The deceleration was enough to be uncomfortable but not sufficient to be an AEB event. It happened consistently at the same 3 tunnel entrances on the validation route.

**TASK:**
Identify the root cause and propose a fix that doesn't compromise safety in genuine deceleration scenarios. The fix needed to be validated within the current sprint.

**ACTION:**

*Step 1 — Correlate with sensor data:*
Extracted logs for all 3 tunnel approach events. Common pattern:
- Camera: detects the dark tunnel opening. Due to brightness contrast (bright outside, dark inside), the camera's exposure adjusts → for ~500ms, the image is overexposed → object detection disabled
- Radar: detects the tunnel structure (metal arch) at range decreasing from 120m to 80m as we approach
- Fusion: camera absent + radar detects approaching structure → confidence rises → ACC decelerates for "approaching obstacle"

*Step 2 — Fusion context failure:*
The radar correctly detected the tunnel arch — a real object. But the tunnel arch is a static infrastructure element above the road, not an object in the vehicle path.
The camera, if functioning, would see the geometry and classify: "this is a tunnel, not a road obstacle."
With camera absent, fusion had no context to reclassify.

*Step 3 — Solutions considered:*
Option A: Map-based: use HD map data — tunnel location known → suppress radar stationary targets at tunnel entrance
Option B: Geometry filter: tunnel arch has a specific reflected energy pattern (very wide, high altitude, high RCS) → filter targets with these characteristics
Option C: Camera confidence: hold ACC deceleration authority until camera confidence is available, use a higher confirmation threshold when camera is degraded

*Step 4 — Implemented fix:*
Option B + C combined:
- Added a geometry filter: if detected static target width > 6m → classify as infrastructure, reduce confidence by 50%
- When camera confidence falls below 0.5 (transitioning into tunnel), increase ACC deceleration threshold (requires higher fusion confidence, not lower) until camera stabilises

**RESULT:**
- All 3 tunnel entrances tested: no deceleration events
- 50 additional tunnel entrances tested across the motorway network: 49/50 no event (1 residual at an unusual steel-mesh tunnel with extremely high RCS — documented as known limitation)
- ACC comfort rating in tunnel entry scenario improved from "uncomfortable deceleration" to "smooth"
- Fix released in next software drop, no regressions in existing AEB tests

---

## STAR Scenario 7 — Fusion Validation Framework Built From Scratch

**SITUATION:**
Joining a new ADAS team, I found that fusion validation was entirely manual — engineers drove test routes, eyeballed the fusion display in real time, and logged subjective "OK / NOK" notes. There were no quantitative metrics, no automation, and no regression testing. With 3 vehicle variants and a product launch in 6 months, this was unsustainable.

**TASK:**
Design and implement an automated fusion validation framework that could:
1. Process MDF4 logs from vehicle testing
2. Compare fusion output against ground truth (RTK GPS on target vehicle)
3. Produce quantitative metrics (RMSE, detection rate, false positive rate)
4. Flag regressions automatically when SW changes

**ACTION:**

*Step 1 — Define metrics:*
Agreed with system architect on 6 KPIs:
- Detection rate per object class (car, pedestrian, cyclist, truck)
- False positive rate (per km driven)
- Position RMSE (compared to RTK ground truth)
- Velocity RMSE
- Track latency (time from object appearance to confirmed track)
- Track stability (number of ID switches per tracked object)

*Step 2 — Build data pipeline:*
```
MDF4 log (vehicle test)            RTK log (target vehicle)
       │                                  │
       ▼                                  ▼
Extract fusion object list          Extract ground truth trajectory
(Python: asammdf library)           (interpolate to 10ms intervals)
       │                                  │
       └─────────────────┬────────────────┘
                         ▼
              Association algorithm (Hungarian, 2m gate)
                         │
                         ▼
              Metrics calculation + report generation
                         │
                         ▼
              HTML/PDF test report (automated)
```

*Step 3 — CI integration:*
Connected the pipeline to Jenkins CI. Every SW build automatically triggered:
1. Replay of 20 canonical test scenarios from stored MDF4 logs
2. Metric calculation vs stored ground truth
3. Pass/fail against thresholds
4. Email alert to team if any metric regressed by > 5%

*Step 4 — Team training:*
Delivered 2-hour workshop to the 6-person validation team. Wrote a 15-page user guide.

**RESULT:**
- Framework in use within 6 weeks
- First CI regression caught: a SW change that reduced pedestrian detection rate from 94% → 87% — would have shipped without the framework. Fix applied before next sprint.
- Validation time for a new SW build: manual (3 days) → automated (2 hours)
- At product launch: all 6 KPIs met across 3 variants
- Framework later adopted by 2 other ADAS programmes in the same organisation

---

## STAR Scenario 8 — Time Synchronisation Error Between Radar and Camera

**SITUATION:**
ACC following target at 100 km/h. When the target braked from 100 to 80 km/h, the fused track showed a velocity spike of +12 m/s upward (approaching at high speed) followed by the correct deceleration. This spike caused the ACC to briefly command a stronger braking response than needed — uncomfortable for the passenger.

**TASK:**
Find the source of the velocity spike in the fused object output and correct it.

**ACTION:**

*Step 1 — Isolate spike timing:*
The velocity spike lasted approximately 40ms and occurred exactly when the target started braking.
Camera update rate: 40ms (25 Hz)
Radar update rate: 25ms (40 Hz)

*Step 2 — Identify time misalignment:*
At the moment of target braking:
- Radar (t=0ms): velocity = −5 m/s (approaching at 5 m/s — target just started braking)
- Camera (t=40ms): position derived velocity = −15 m/s (camera is 40ms later so sees more braking)
- Fusion algorithm: averages without extrapolation → result = −10 m/s average of stale data → when next cycle arrives, the correction appears as a spike

Confirmed: fusion code was using raw timestamps, not compensating for the 40ms camera latency.

*Step 3 — Fix — temporal alignment:*
Fusion ECU must extrapolate each sensor's data to a common fusion timestamp (T_fusion):
```
Radar prediction to T_fusion:  x_radar(T_fusion) = x_radar(t_radar) + v_radar × (T_fusion - t_radar)
Camera prediction to T_fusion: x_cam(T_fusion)   = x_cam(t_cam)   + v_cam   × (T_fusion - t_cam)
Then fuse at T_fusion — both inputs are now at the same time
```

Applied the temporal alignment (2-line code change in fusion ECU SW).

**RESULT:**
- Velocity spike eliminated in all subsequent tests
- ACC braking smoothness metric improved: peak jerk during following-target-deceleration reduced by 55%
- Time alignment now applied to all sensor inputs in fusion stack
- Root cause documented: "dead time compensation mandatory for asynchronous sensor fusion"

---

## STAR Scenario 9 — Blind Spot Fusion Giving Inconsistent Results Across Vehicle Variants

**SITUATION:**
The BSD (Blind Spot Detection) system — using rear-corner radar fusion — passed validation on Variant A (sedan) but repeatedly failed on Variant B (SUV). The failure: BSD activated 0.8 seconds too late for a fast-approaching vehicle in the blind spot. NCAP test requires activation when the approaching vehicle is > 50m behind, the SUV was activating at 32m.

**TASK:**
Determine why the same fusion algorithm produced different latency on the SUV body style.

**ACTION:**

*Step 1 — Compare sensor mounting:*
Sedan rear-corner radar mounting: 0.9m from rear bumper face, 45° angle
SUV rear-corner radar mounting:   1.3m from rear bumper face, 45° angle (longer rear overhang)

*Step 2 — Coordinate transform implication:*
The radar's range data places the detected object at range r from the sensor.
Converting to vehicle frame: the bumper is 1.3m ahead of the sensor on the SUV (vs 0.9m on sedan).
```
Sedan:  object at 50m from sensor = 50m - 0.9m = 49.1m behind bumper
SUV:    object at 50m from sensor = 50m - 1.3m = 48.7m behind bumper
```
This alone is not enough to explain 0.8s latency.

*Step 3 — Track confirmation threshold in vehicle-frame distance:*
BSD activation trigger: object < 50m **from rear bumper** (in vehicle frame).
On sedan: sensor at 0.9m offset → activation at sensor range 50.9m → correctly detects at 50m bumper distance.
On SUV:   extrinsic calibration file had wrong sensor offset (0.9m used, actual 1.3m).
The transform was placing sensor detections 0.4m closer than reality → BSD triggered at 50m sensor range = 48.7m bumper range — correctly above threshold... but wait.
Further analysis: the SUV had a larger rear plastic bumper cover — radar beam had to penetrate 15mm extra polypropylene → −2 dB attenuation → object RCS below track initiation threshold until closer range = delayed track confirmation.

*Step 4 — Fix:*
Update extrinsic calibration file with correct 1.3m offset for SUV variant.
Update radar transmission power compensation for 15mm bumper cover material (RCS threshold lowered by −2 dB equivalent).

**RESULT:**
- BSD activation distance on SUV variant: improved from 32m to 57m (exceeds 50m requirement)
- NCAP BSD test PASSED on SUV variant
- Variant-specific extrinsic calibration verification added to the build checklist for all body styles
- Finding presented to sensor mounting team — bumper cover thickness now included in radar performance budget

---

## STAR Scenario 10 — Learning from a Fusion System Safety Escape

**SITUATION:**
In a real-world incident (no injury), a production vehicle using radar-camera fusion failed to detect a stationary lorry partially off the side of the road, at night, in rainy conditions. The camera did not detect the lorry (rain + night + unusual partial occlusion by roadside barrier). The radar detected a stationary target at high RCS but the fusion system had a filter specifically designed to suppress large static targets at the roadside (to avoid false highway bridge detections). The lorry fell into the suppression zone. Driver braked manually.

**TASK:**
As part of the post-incident analysis team, determine the chain of events, identify system design gaps, and recommend improvements.

**ACTION:**

*Step 1 — Reconstruct from data:*
Retrieved vehicle data log from eCall/cloud backup:
- Radar: detected stationary target RCS= +22 dBsm at 65m, azimuth= +4° (slightly to right — lorry was half on road)
- Camera: no detection (rain noise on lens, night, no retro-reflective markers on lorry)
- Fusion: static target suppression filter active (azimuth > 3° AND stationary → suppress as roadside infrastructure)
- The lorry was at +4° — just beyond the 3° threshold — suppressed as infrastructure

*Step 2 — Design gap analysis:*
The static target suppression was calibrated for bridge overpasses: high, narrow, centred.
A stationary lorry at 4° is NOT a bridge — it occupies height 0–4m, width 2.5m, partially in the lane.
There was no object size or height dimension check in the suppression filter — it only used azimuth.
If height and width had been checked, the lorry profile would be clearly different from a bridge.

*Step 3 — Improvements proposed:*
1. Add height and width dimensions to suppression filter: suppress only if height > 3m (bridges) AND width > 10m (bridges span full road)
2. For objects partially within lane boundary: never suppress regardless of azimuth
3. Add ensemble disagreement alert: if radar sees a large object and camera disagrees → flag as "uncertain — require driver attention" not silent suppression

*Step 4 — Validation test:*
Designed 15 test cases covering: bridge (must suppress), lorry partially on road (must NOT suppress), barrier without vehicle (must suppress), vehicle against barrier (must NOT suppress).
All 15 pass/fail results verified with the updated filter logic.

**RESULT:**
- Filter updated and validated before next production SW release
- ISO 26262 deviation report filed for existing vehicles (OTA SW update initiated)
- Root cause: suppression logic used too few dimensions (azimuth only) — principle: suppression filters must use multiple independent dimensions to avoid misclassifying real objects
- Incident added to the team's hazard log as a real-world evidence example
- Personal learning: never design a safety suppression filter with a single parameter — always require at least 2 independent conditions

---
*File: 02_star_scenarios.md | Sensor Fusion STAR Interview Scenarios | April 2026*
