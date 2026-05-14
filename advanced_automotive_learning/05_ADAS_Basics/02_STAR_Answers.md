# ADAS BASICS — STAR INTERVIEW STORIES
## Module 5 of 7 | 6 Ready-to-Use STAR Answers

---

## STAR-1: Investigating AEB False Positive at Production Gate

**Situation:**
During production validation testing, AEB was triggering nuisance braking when vehicles drove over a particular steel drainage grate on the test track at 30 km/h. The Euro NCAP AEB City test required zero false activations in a 500m straight-line drive — which crossed this grate. Test was failing on 30% of attempts.

**Task:**
Determine why the steel grate was triggering AEB and implement a fix without compromising genuine AEB performance.

**Action:**
1. Captured the radar object list during the false trigger: the grate was reflecting a strong broadside return at range 8m, azimuth 0° — appearing as a stationary object directly in the path.
2. The radar was correctly detecting the grate. The problem was that the height filter was not applied: the grate was at road level (height = 0m), but the radar's object height field showed "unknown" for this detection because it was a flat reflection rather than a 3D object.
3. Review of ADAS algorithm: the height filter was only applied when height was explicitly "below road surface" (-0.3m). When height was "unknown," the object was treated as a full-height obstacle.
4. Proposed fix: if height is "unknown" AND object is stationary AND range < 5m, classify as "potential road surface feature" and require 3 consecutive radar scans before triggering AEB.
5. Co-designed the fix with the perception team; validated with 50 test passes over the grate and 20 controlled AEB interventions with a genuine stationary target.

**Result:**
False positive rate: 0% across 50 grate passes. Genuine AEB performance unchanged (same TTC threshold, same braking profile). Change documented in the AEB plausibility specification. Fix pattern was also applied to metal speed bumps, preventing 2 other false positive scenarios.

---

## STAR-2: AEB Miss Detection During Partial Occlusion

**Situation:**
Customer reported that AEB did not activate during a low-speed parking collision where a shopping cart was partially behind a pole. Post-incident log analysis showed the ADAS ECU had the correct raw sensor data — but the fusion algorithm did not generate a valid object track.

**Task:**
Determine why the partially occluded shopping cart did not produce a valid ADAS object and assess whether this was a design gap or a software bug.

**Action:**
1. Replayed ECU logs through the sensor fusion simulation: at the moment of approach, the shopping cart radar cross-section (RCS) was below the minimum detection threshold (minimum = 1m²; shopping cart = 0.3m²). The cart was being detected intermittently — 2 out of 5 scans.
2. The tracker required 3 consecutive detections to confirm a new object. With only 2 of 5 scans detecting the cart, no track was ever confirmed.
3. This was a design limitation, not a software bug: the requirement document said "AEB target: pedestrians, bicycles, cars; minimum detectable RCS = 1m²." Shopping carts were not in scope.
4. Presented this as a design gap to product management: the feature was compliant with requirements but the customer expected coverage of all obstacles.
5. Proposed two options: (a) reduce confirmation threshold from 3 to 2 consecutive detections (lower RCS requirement, higher false positive risk), (b) add camera-based small obstacle detection to supplement radar.

**Result:**
Decision: add camera-based obstacle detection for close-range low-speed operation (< 20 km/h). I drafted the new requirement: "AEB-PAS: detect obstacles ≥ 0.2m² using camera at range < 3m, speed < 20 km/h." This extended coverage to shopping carts, bollards, and small animals.

---

## STAR-3: ACC Disengage During Radar Temporary Blockage

**Situation:**
ACC was automatically disengaging during heavy rain — with no warning other than a "SENSOR DEGRADED" message. Customers were reporting this as a defect. Marketing reported it was affecting 1-star reviews on forums.

**Task:**
Determine whether this was expected behavior or a calibration issue, and propose a user experience improvement.

**Action:**
1. Retrieved ECU logs from 3 affected vehicles. Pattern: rain sensor showed heavy rain; radar signal quality metric ("radDetectionReliability") dropped below 60% threshold; ACC disengaged within 100ms.
2. Compared with the specification: the requirement said "Disengage ACC if radar reliability < 60% for 500ms." But the code implemented "< 60% for 100ms." A 400ms timing error in the implementation.
3. Impact: the 100ms timeout was triggering on momentary radar reflections from large rain drops (< 200ms disturbances), which should not have caused disengagement per spec.
4. Fixed the timing threshold from 100ms to 500ms in the ACC degrade state machine.
5. Also proposed UX improvement: show a 5-second countdown timer before disengagement ("ACC degrading due to weather, disengaging in 5s") to reduce driver surprise.

**Result:**
ACC nuisance disengagements reduced by 70% in rain testing. UX improvement approved and implemented in the next software release. Customer forum mentions of the issue dropped from 12/month to 1/month in the 2 months following the OTA update.

---

## STAR-4: FCW Missed Alert During Lane Change Cut-In

**Situation:**
During Euro NCAP pre-assessment testing, FCW was missing alerts when a target vehicle cut into the ego lane from the adjacent lane at a TTC of 2.5s. FCW was supposed to alert at TTC < 3.0s. Cut-ins were failing 40% of the time.

**Task:**
Root cause why cut-in scenarios were not triggering FCW alerts despite TTC < 3.0s.

**Action:**
1. Analyzed test data frame by frame: when a vehicle cut in from the adjacent lane, the radar initially classified it as "adjacent lane object" and filtered it from FCW evaluation (correctly, to avoid false alarms for vehicles in other lanes).
2. The lane-change detection logic waited until the lateral position of the object crossed the lane center line before reclassifying it as "in-lane." This took 0.8–1.2 seconds.
3. By the time the object was reclassified as in-lane, TTC had dropped to 1.5–2.2s — below the FCW alert window of 3.0s, so FCW had "missed" the alert.
4. Fix: implement a predictive lane assignment. If an object is in the adjacent lane but its lateral velocity is directed toward ego lane and its TTC (based on current trajectory) is < 3.5s — pre-classify as "potential in-lane threat" and activate FCW.
5. Also reduced the lane-center crossing threshold from 100% lane width to 70% (raise alert when object is 70% into ego lane, not 100%).

**Result:**
FCW detection rate for cut-in scenarios improved from 60% to 94% in internal testing. Euro NCAP pre-assessment passed FCW component with 5.0/5.0 on cut-in scenarios.

---

## STAR-5: Building an Automated ADAS Regression Suite

**Situation:**
After a refactoring of the ADAS fusion algorithm, 15 previously fixed AEB and FCW bugs were being re-verified manually — taking 3 engineers 5 days per release cycle. This created a bottleneck for every software update.

**Task:**
Automate the ADAS regression test suite to run on every software build without manual intervention.

**Action:**
1. Catalogued all 15 regression scenarios: each had a defined radar/camera input sequence, expected ADAS output (brake request, FCW alert), and timing tolerance.
2. Built a Python test harness that: replayed recorded sensor data from log files into an ECU-in-loop simulation, captured ADAS output signals via CAN, compared against expected output using configurable tolerances.
3. Integrated with Jenkins: every code commit triggered the regression suite; results emailed to the team with pass/fail status and timing plots.
4. Reduced manual test time: 0 hours (fully automated). Build-to-result time: 25 minutes.
5. Extended to 45 scenarios within 2 months by encoding newly found bugs as regression test cases immediately.

**Result:**
2 regressions caught before release: a TSN timing change that delayed AEB activation by 120ms (above 100ms tolerance) and a memory allocation bug that caused FCW to miss every 10th alert. Both caught automatically in CI, zero customer impact. Test coverage grew from 15 to 45 scenarios. Regression runtime: 25 minutes per build.

---

## STAR-6: Explaining ASIL Requirements to a Non-Safety Engineer

**Situation:**
A new software developer was about to implement a watchdog reset that would restart the ADAS ECU when a memory allocation failure was detected. They proposed: "just reset and the system recovers in 500ms." The ASIL D safety case required a defined safe state within 100ms, not 500ms.

**Task:**
Ensure the developer understood the ISO 26262 requirement without creating defensiveness and get the implementation aligned with the safety case.

**Action:**
1. Instead of citing the rule ("the spec says 100ms"), explained the scenario: "At 130 km/h, 500ms = 18 meters of uncontrolled driving. At 100ms, it's 3.6 meters. In an active AEB event, 400ms of the wrong brake pressure could be the difference between avoiding a collision and not."
2. Walked through the HARA entry: AEB false activation = ASIL D, maximum fault detection time = 100ms, maximum safe state transition = 100ms.
3. Together redesigned the watchdog: instead of a full ECU reset, the watchdog now transitions to a "degraded mode" in < 10ms — disabling AEB but preserving power steering and driver warnings. ECU reset then occurs in the background.
4. The developer wrote the implementation and I co-reviewed it against the safety case.

**Result:**
Implementation compliant with ASIL D timing constraint. Developer became one of the most safety-aware engineers on the team and later led the safety case update for the next platform. Key insight: safety explanations land better with concrete physical consequences than with standards citations.

---

*Next: [03_Mini_Projects.md](03_Mini_Projects.md)*
