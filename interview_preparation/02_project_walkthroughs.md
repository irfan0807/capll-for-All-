# Project Walkthroughs — STAR Method Answers

> **STAR** = Situation → Task → Action → Result
> Interviewers evaluate: problem-solving, technical depth, ownership, and impact.
> Prepare 2 stories per project. Practice telling each in 2–3 minutes.

---

## Project 1: BYD — ADAS ECU Validation (Most Recent — Lead With This)

### Story 1A: Ultrasonic Sensor False Detection Bug

**Situation:**
"At BYD, I was responsible for end-to-end validation of the Parking Assist system using ultrasonic sensors. During HIL testing, we discovered that the parking sensors were falsely detecting obstacles when the vehicle approached metal bollards and guardrails at low speed — about 5–10 km/h. This was causing unnecessary parking warnings and automatic braking interventions, which was a P1 safety issue."

**Task:**
"I was tasked with reproducing the issue on the HIL bench, identifying the root cause, and ensuring it was fixed before the production release."

**Action:**
"First, I analyzed the CAN logs in CANoe and found that the ultrasonic echo signal patterns from metal surfaces had a similar reflection profile to real obstacles — specifically, the echo amplitude and time-of-flight values overlapped with valid obstacle ranges at 1m and 3m.

I designed new edge-case test scenarios covering different surface materials — metal, glass, wood, and plastic — at distances of 0.5m, 1m, 3m, and 5m. I wrote CAPL scripts to inject these echo patterns on the dSPACE HIL bench, so we could reproduce the issue without needing a physical test track every time.

I also performed UDS diagnostics — using service 0x22 to read the sensor calibration DIDs and 0x19 to check if any DTCs were logged during the false detections. The diagnostics showed no DTC, which meant the ECU considered the detection 'valid' — confirming the issue was in the algorithm, not the hardware.

I shared my analysis with the software team, who found that the material-type filter in the signal processing algorithm was not active below 15 km/h. They fixed the filter threshold, and I re-ran the complete test suite."

**Result:**
"The fix resolved the false detection issue across all material types. My CAPL-based HIL test scenarios were added to the regression suite permanently, which improved defect detection efficiency by 30%. The issue was caught and resolved before production release, avoiding a potential field recall."

---

### Story 1B: CAPL Automation for Regression Testing

**Situation:**
"At BYD, our ADAS regression test suite had about 200 test cases that were executed manually every sprint. This was taking 3 full days of manual effort per cycle and was prone to human error — sometimes signal boundary checks were missed."

**Task:**
"I was asked to automate the repetitive CAN-signal-level test cases to reduce execution time and improve reliability."

**Action:**
"I identified 120 out of 200 test cases that were purely CAN-signal-based — things like verifying signal ranges, timeout behavior, default values on bus-off, and DTC response to fault injection.

I wrote CAPL scripts in CANoe that:
- Simulated vehicle speed, gear position, and sensor signals on the CAN bus
- Injected faults like signal timeout, bus-off, and invalid signal values
- Automatically checked CAN responses against expected values from the test specification
- Generated pass/fail reports in XML format compatible with our test management tool

I also added UDS automation — scripts that automatically sent 0x19 (Read DTC), verified DTC status bytes, and validated freeze frame data after each fault injection."

**Result:**
"Automation reduced regression execution from 3 days to less than 1 day — a 35% improvement in execution efficiency. The automated suite caught 3 critical bugs that were previously missed in manual execution due to timing-sensitive signal checks. The framework was adopted by the team for all future test cycles."

---

### Story 1C: Camera System Validation (RVC/MVC)

**Situation:**
"I was also responsible for validating the Reverse View Camera and Multi View Camera systems. We found that the camera display had a 400ms delay when shifting to reverse gear — the specification required activation within 200ms."

**Task:**
"Measure the exact activation delay, identify the bottleneck, and validate the fix."

**Action:**
"I set up a test scenario in dSPACE VT Studio where I simulated the gear shift from Drive to Reverse on the CAN bus and measured the timestamp delta between the GearPosition CAN signal change and the camera video stream activation signal.

Using CANoe trace tools, I measured the end-to-end delay:
- CAN signal propagation: ~10ms (normal)
- ECU processing time: ~380ms (too slow — should be <150ms)
- Total: ~390ms (exceeds 200ms requirement)

I logged a detailed defect in JIRA with the CAN trace screenshots, exact timestamps, and the signal names involved. The SW team found that the video initialization was waiting for 3 consecutive valid camera frames instead of 1, adding unnecessary latency."

**Result:**
"After the fix, the camera activation time dropped to 120ms — well within the 200ms requirement. I created a dedicated CAPL timing measurement script that became a standard tool for all camera feature validation."

---

## Project 2: BMW — ADAS & Cluster Validation

### Story 2A: Adaptive Cruise Control Sensor Failure Handling

**Situation:**
"At BMW, I was validating Adaptive Cruise Control (ACC) behavior under sensor failure conditions. During testing, I discovered that when the front radar sensor was simulated as 'lost' (no signal for 300ms), the ACC did not gracefully degrade — instead of handing control back to the driver with an alert, the system maintained the last known speed for 2 additional seconds."

**Task:**
"Investigate the degradation behavior, document the safety gap, and validate the fix."

**Action:**
"I used dSPACE HIL to simulate radar signal loss at different speeds — 30, 60, 80, and 120 km/h. For each speed, I measured:
- Time from signal loss to ACC warning on cluster
- Time from signal loss to ACC deactivation
- Whether the driver was prompted to take over

Using CANoe, I traced the signal flow: RadarStatus → ADAS_ECU → ACC_State → Cluster_Alert. I found that the ADAS ECU was waiting for 5 consecutive missing radar frames before declaring sensor loss — this 5-frame wait at 10Hz cycle time = 500ms, plus the internal debounce added another 1.5s.

I created requirement-gap documentation with exact signal traces and shared it with the BMW system team. They adjusted the debounce from 5 frames to 2 frames and added an immediate cluster warning on the first missing frame."

**Result:**
"After the fix, ACC degradation time dropped from 2+ seconds to under 500ms, meeting the ISO 26262 ASIL-B timing requirement. My test scenarios covering sensor loss at multiple speeds were incorporated into the HIL regression suite, improving test coverage by 30%."

---

### Story 2B: Cluster Telltale Defect Leakage Reduction

**Situation:**
"The Cluster testing team was experiencing defect leakage — bugs were escaping to the integration testing phase because telltale validation was mostly manual and focused on happy-path scenarios."

**Task:**
"Improve telltale test coverage to reduce defect escape rate."

**Action:**
"I reviewed the existing test cases and found they only covered ON/OFF states for telltales. They missed:
- Boundary conditions (e.g., fuel level exactly at 10L threshold)
- CAN signal timeout behavior (what happens when the CAN message stops?)
- Priority conflicts (two warnings competing for the same display area)

I designed 40 additional test cases covering these gaps and wrote CAPL scripts to:
- Inject CAN signals at exact boundary values
- Simulate CAN message timeouts for each telltale source signal
- Verify telltale priority logic when multiple warnings are active simultaneously

I used UDS 0x19 to verify that proper DTCs were set when telltale-related CAN signals timed out."

**Result:**
"Defect leakage from Cluster testing reduced by 25% over the next 3 releases. Two critical defects were found in the new test cases — one where the low fuel warning did not activate at exactly 10L, and another where the seatbelt warning was overridden by a less critical door-ajar warning."

---

## Project 3: Lexus (Concentrix) — Infotainment & Cluster

### Story 3A: Bluetooth A2DP Connectivity Issue Across Devices

**Situation:**
"At Lexus, we received field complaints that Bluetooth music streaming (A2DP) was dropping on certain Samsung phones after 15–20 minutes of playback. The issue was not reproducible on iPhone or Pixel devices."

**Task:**
"Reproduce the issue in the lab, identify the root cause, and validate the fix across all supported devices."

**Action:**
"I set up a test matrix of 8 phone models across Android and iOS. I connected each phone via Bluetooth, started A2DP streaming, and monitored for 30 minutes.

Key observations:
- Samsung S20, S21: disconnects at ~18 min (consistent)
- iPhone 12, 13: no disconnects
- Pixel 5: no disconnects

I captured BT HCI snoop logs from the head unit and analyzed them in Wireshark. I found that Samsung phones were sending an AVDTP SUSPEND command after 15 minutes of continuous streaming — this was triggered by Samsung's battery optimization feature that suspends background audio after 15 min.

The head unit was not handling the SUSPEND → RESUME transition correctly — instead of resuming, it was dropping the A2DP connection entirely.

I logged a detailed defect with HCI packet captures, timestamps, and device-specific behavior comparison. The SW team fixed the A2DP state machine to properly handle SUSPEND/RESUME."

**Result:**
"After the fix, all 8 devices streamed A2DP continuously for 2+ hours without disconnection. I created a standardized Bluetooth endurance test procedure (30-min soak test per device) that was adopted for all future Infotainment releases, reducing defect escape rate by 20%."

---

### Story 3B: Apple CarPlay / Android Auto Integration Testing

**Situation:**
"During Infotainment validation, we had to certify Apple CarPlay and Android Auto compatibility across 15+ phone models and multiple OS versions. The test matrix was large — about 300 test combinations — and we were behind schedule."

**Task:**
"Prioritize testing to cover maximum risk within the available time, and ensure core functionality was validated."

**Action:**
"I used a risk-based testing approach:
1. I categorized test combinations into High/Medium/Low risk based on:
   - Market share of phone model (top 5 phones = 80% of users)
   - OS version freshness (latest 2 versions = highest risk for compatibility)
   - Historical defect data (which phone models had most bugs in previous releases)

2. I created a priority matrix and got approval from the test lead to focus on the top 60 High-risk combinations first (covering 80% of real-world usage).

3. For each combination, I tested: connection setup, navigation projection, media playback, phone call handling, and disconnection/reconnection.

4. I documented all test results in DOORS with full traceability."

**Result:**
"We completed high-risk testing within the deadline. We found 5 critical bugs — 3 in Android Auto (USB reconnection issues on Pixel 6) and 2 in CarPlay (Siri voice routing to wrong speaker on iPhone 14). All were fixed before release. The prioritization approach was adopted as the standard strategy for future certification cycles, improving test coverage by 30% within the same time frame."

---

## How to Use These Stories in an Interview

### When Asked: "Tell me about a challenging bug you found"
→ Use **Story 1A** (ultrasonic false detection) or **Story 3A** (BT A2DP dropout)

### When Asked: "Tell me about your automation experience"
→ Use **Story 1B** (CAPL regression automation)

### When Asked: "How do you handle tight deadlines?"
→ Use **Story 3B** (CarPlay/Android Auto risk-based prioritization)

### When Asked: "Tell me about a safety-critical issue"
→ Use **Story 2A** (ACC sensor failure degradation)

### When Asked: "How did you improve test coverage?"
→ Use **Story 2B** (Cluster telltale defect leakage) or **Story 1B** (CAPL automation)

### When Asked: "Tell me about cross-team collaboration"
→ Use **Story 1A** (shared analysis with SW team) or **Story 2A** (worked with BMW system team)

---

## STAR Story Quick Reference Card

| # | Project | Story Title | Key Metric | Best For Question |
|---|---------|-------------|-----------|-------------------|
| 1A | BYD | Ultrasonic false detection | 30% defect detection improvement | Challenging bug, root cause analysis |
| 1B | BYD | CAPL regression automation | 35% execution efficiency | Automation experience |
| 1C | BYD | Camera activation delay | 390ms → 120ms | Timing/performance testing |
| 2A | BMW | ACC sensor failure handling | ISO 26262 compliance achieved | Safety-critical, sensor failure |
| 2B | BMW | Cluster telltale leakage | 25% defect leakage reduction | Test coverage improvement |
| 3A | Lexus | BT A2DP disconnection | 20% defect escape reduction | Device compatibility, debugging |
| 3B | Lexus | CarPlay/AA prioritization | 30% coverage in same time | Deadline pressure, prioritization |

---

## Project 4: BYD — Advanced ADAS & HIL Scenarios

### Story 4A: BSD False Alarm — DBC Bitfield Swap

**Situation:**
"At BYD, during HIL testing, the Blind Spot Detection system was triggering false alarms when the driver initiated a lane change to the left while a vehicle was present on the right side. Both sides were alerting simultaneously."

**Task:**
"Isolate whether the issue was in sensor fusion, ECU decision logic, or CAN DBC mapping."

**Action:**
"I set up a dSPACE scenario: Left turn indicator ON, BSD_Right detecting a vehicle at 3m, BSD_Left detecting empty lane. I captured the CAN trace and checked TurnSignal_Status, BSD_Right_Object_Distance, BSD_Warning_Left, and BSD_Warning_Right. BSD_Warning_Left was asserting even though the left lane was clear. I compared the DBC bitfield definitions and found BSD_Warning_Left and BSD_Warning_Right were swapped at the ECU output. I logged the defect with the DBC comparison and CAN trace."

**Result:**
"The DBC was corrected and verified. Warnings triggered only on the relevant side. I added a BSD directional accuracy test covering all 4 indicator x sensor combinations to the regression suite."

---

### Story 4B: Parking Assist Audio Cadence CAPL Validation

**Situation:**
"The Parking Assist system uses audio beep cadence to indicate obstacle distance. During testing I found the beep frequency was not increasing linearly below 0.5m, which could mislead the driver."

**Task:**
"Validate audio warning cadence against the OEM spec across all 4 sensor zones."

**Action:**
"I developed a CAPL script that: simulated obstacle distance from 2.0m to 0.1m in 0.1m steps, waited for PA_AudioWarning_Frequency on CAN after each step, and compared the measured Hz against the spec table. The rear-right sensor was outputting 3Hz instead of the required 5Hz in the 0.3-0.5m range. UDS 0x22 confirmed calibration DIDs were within tolerance — pointing to the audio mapping table in ECU firmware."

**Result:**
"Firmware corrected the mapping table. My CAPL cadence validation script became the standard for every Parking Assist release, catching 2 additional regressions in subsequent builds."

---

### Story 4C: UDS Security Access NRC 0x35 — Timing Root Cause

**Situation:**
"During ECU software update testing at BYD, the UDS flash sequence intermittently failed at Security Access (0x27) — 8 of 50 attempts returned NRC 0x35 (Invalid Key)."

**Task:**
"Determine the root cause and achieve 100% flash reliability."

**Action:**
"I captured full UDS sequences in CANoe for both passing and failing attempts. In failing cases, the seed request 0x27 01 was being sent immediately after the Programming Session positive response — but the ECU needed 150ms stabilization before accepting a seed request. I added a 200ms delay between the session response and the seed request."

**Result:**
"100 consecutive flash attempts succeeded with zero NRC 0x35 errors. This timing requirement was documented as a platform characteristic and applied to all ECU flash scripts in the project."

---

### Story 4D: MVC Stitching Artifact Under Bright Light

**Situation:**
"At BYD, the Multi-View Camera bird's-eye display was showing visible seams between camera images when parked under direct sunlight above ~800 lux."

**Task:**
"Reproduce the artifact under controlled conditions and provide root cause data."

**Action:**
"I used HIL with pre-recorded video feeds at 200, 500, 800, 1200, and 2000 lux. UDS 0x22 read camera brightness compensation DIDs per lighting condition. Above 800 lux, the front camera auto-exposure was updating faster than side cameras — causing a momentary brightness mismatch at the stitch boundary. I documented specific lux thresholds, camera IDs, and frame timestamps where the artifact appeared."

**Result:**
"Firmware synchronized auto-exposure update cadence across all 4 cameras. No stitching artifacts were visible up to 2000 lux post-fix. I added a 3-scenario lighting stress test to the MVC test suite."

---

### Story 4E: ASPICE Level 2 Traceability Audit

**Situation:**
"Before a mid-year ASPICE Level 2 audit at BYD, the test manager identified that test documentation lacked 100% bi-directional traceability."

**Task:**
"Audit 420 test cases and close all traceability gaps before the audit."

**Action:**
"I found 85 test cases with no requirement link and 30 requirements with no test case. For unlinked tests, I traced back to the SRS by analyzing test objectives and CAN signals under test. For 30 untested requirements I wrote skeleton test cases, flagging 12 as 'HIL setup not yet available' for risk acceptance. I produced a Requirement ID to Test Case ID to Status traceability matrix."

**Result:**
"We achieved 98% bi-directional traceability. ASPICE auditors specifically noted the matrix as well-structured. We passed Level 2 with only minor observations — none related to test documentation."

---

## Project 5: BMW / Capgemini — Extended ADAS Scenarios

### Story 5A: LKA Activation Failure at High Curvature in Wet Conditions

**Situation:**
"At BMW, LKA was not activating at road curvatures above 400m radius in wet conditions — the specification required activation up to 600m radius."

**Task:**
"Characterize the failure boundary, document the defect, and validate the fix."

**Action:**
"I created dSPACE HIL scenarios for road curves from 200m to 700m radius in 50m steps under dry, wet, and snowy friction. I logged LKA_Active, Camera_LaneConfidence, and SteeringTorque_Correction per combination. The lane confidence dropped below the LKA threshold (0.70) above 400m on wet surfaces — but the camera detected lane at 0.72. The LKA wet-condition internal threshold (0.75) was too high, causing unnecessary deactivation."

**Result:**
"The ADAS team recalibrated the wet-condition threshold from 0.75 to 0.68. LKA remained active up to 610m radius in wet conditions. My parametric test matrix was added to the standard HIL regression suite."

---

### Story 5B: ACC Speed Accuracy on Uphill Gradient

**Situation:**
"At BMW, ACC must maintain set speed within plus or minus 2 km/h at all road gradients. During testing on a simulated 8% uphill gradient, the deviation was up to 5 km/h."

**Task:**
"Validate speed accuracy across all gradients and identify the cause."

**Action:**
"I ran HIL scenarios at -10% to +10% gradient in 2% steps at set speeds of 60, 80, 100, and 120 km/h. I logged ACC_SetSpeed, VehicleActualSpeed, ThrottlePosition, and BrakeRequest. At +8% gradient, the throttle request capped at 85% when 95% was needed. The gradient feed-forward lookup table in the ADAS ECU was capped at 6% gradient — no feed-forward was added above that level."

**Result:**
"The calibration team updated the table to cover gradients up to 12%. Post-fix, speed deviation stayed within plus or minus 1.5 km/h at all gradients — better than the requirement. I added gradient sweep tests to the ACC regression suite."

---

### Story 5C: FCW False Positive Under Highway Gantries

**Situation:**
"At BMW, Forward Collision Warning was generating false alerts when passing under highway gantry structures and bridge overpasses."

**Task:**
"Identify why overhead structures triggered FCW and validate the fix."

**Action:**
"I analyzed radar point cloud data in CAN logs during false-alert events. Large overhead metal structures produced strong reflections at close vertical angles — the radar vertical field of view wasn't filtering stationary overhead objects. I created dSPACE scenarios injecting radar objects at 5m, 10m, and 20m heights alongside a moving vehicle at 1.5m. Across 40 overhead scenarios, 12 triggered false FCW alerts."

**Result:**
"The radar processing team added a vertical angle filter for stationary objects above 3.5m. Post-fix, 0 out of 40 overhead scenarios triggered FCW while longitudinal FCW for real vehicles remained intact."

---

### Story 5D: Cluster Warning Priority Matrix Testing

**Situation:**
"At BMW, when multiple warnings are simultaneously active, the Cluster must display them in correct priority order and never suppress safety-critical warnings. This logic had not been exhaustively tested."

**Task:**
"Build a test suite validating warning priority logic across 30 warning types."

**Action:**
"I mapped all 30 warnings into: P1 safety-critical (seatbelt, airbag, brake failure), P2 driver-important (fuel low, engine temperature), and P3 informational (door ajar, trunk open). I wrote CAPL scripts to simultaneously inject 2, 3, and 4 warnings from different tiers and verify display behavior. I tested 45 combinations covering all P1xP2, P1xP3, P2xP3, and P1xP2xP3 scenarios."

**Result:**
"Found 4 defects: 2 where P2 suppressed a P1 warning during startup, and 2 where P3 was not suppressed when P1 and P2 were both active. All 4 were fixed. My CAPL priority test script became the standard regression tool for all Cluster SW releases."

---

### Story 5E: Freeze Frame Data — NVM Write Timing Issue

**Situation:**
"At BMW, UDS 0x19 04 freeze frame data for some DTCs was returning all zeros, suggesting the ECU wasn't capturing sensor snapshots when faults were set."

**Task:**
"Identify which DTCs were not capturing freeze frames and find the root cause."

**Action:**
"I injected each fault via dSPACE HIL and immediately sent 0x19 04. 8 of 45 DTCs returned zero freeze frames. I noticed my test was reading within 50ms of DTC set — but the ECU needed at least 200ms to write freeze frame data to NVM. I updated the test procedure to wait 250ms after fault injection before reading freeze frame."

**Result:**
"All 45 DTCs returned valid non-zero freeze frame data. The 200ms NVM write delay was documented as a platform characteristic, preventing future false-positive defects from teams reading freeze frames too early."

---

## Project 6: Lexus / Concentrix — Extended Infotainment Scenarios

### Story 6A: BT HFP Echo on 2nd and 3rd Consecutive Calls

**Situation:**
"At Lexus, customers reported echo on Bluetooth Hands-Free calls — specifically from the 2nd call onwards. The 1st call was always clear."

**Task:**
"Reproduce the issue in a lab setup and isolate the root cause."

**Action:**
"I ran a test: make call 1 (5 min), end, make call 2 (5 min), end, make call 3 (5 min). Repeated 10 times with 5 phone models. Echo appeared from call 2 onward on 3 out of 5 phones. HCI snoop logs in Wireshark showed the head unit falling back from mSBC to CVSD codec on call 2, due to an incomplete SCO teardown from call 1. The AEC (Acoustic Echo Cancellation) buffer was not being reset between calls."

**Result:**
"SW team added full SCO teardown and AEC buffer reset between calls. Echo-free quality was maintained across 10 consecutive calls on all 5 phones. I established the multi-call HFP endurance test as a standard validation procedure."

---

### Story 6B: OTA Map Update — Validation Including Failure Scenarios

**Situation:**
"Lexus was launching over-the-air map updates. My task was to validate download, install, and rollback behavior including failure/interruption scenarios."

**Task:**
"Build and execute a 15-scenario OTA test suite covering happy path and failure modes."

**Action:**
"I designed: normal update with MD5 checksum verification, download interrupted at 30%, 70%, and 99%, install interrupted by simulated power cut via programmable relay, corrupted file injection, and manual rollback. I used UDS 0x22 map version DID to verify state before and after each scenario."

**Result:**
"Identified 1 defect: power cut at 99% install caused the ECU to report success but the map version DID still showed the old version — a partial NVM write issue. The install confirmation logic was fixed. This suite was adopted by the Lexus OTA team for all future map update releases."

---

### Story 6C: Android Auto USB Reconnection Stability

**Situation:**
"Several Android phones were failing to reconnect Android Auto after a brief USB interruption, with success rates as low as 40% on some devices."

**Task:**
"Test USB reconnection stability across 10 Android phone models and provide data to the integration team."

**Action:**
"I ran 20 plug-unplug-replug cycles per phone with a 2-second disconnect interval. Google Pixel 4/5/6 showed 100% reconnect success. Samsung S21/S22 showed 65%. Xiaomi MI11 showed 40%. USB enumeration logs showed Samsung and Xiaomi took over 5 seconds to re-enumerate their USB gadget class after a fast reconnect. The head unit Android Open Accessory timeout was 5 seconds — too short. I recommended increasing it to 12 seconds."

**Result:**
"Post-fix, reconnection success rates reached 100% on all tested devices. I added USB reconnect stability testing to the Infotainment compatibility test suite."

---

### Story 6D: Media Playback Format Compatibility — 120-File Library

**Situation:**
"Lexus was releasing a media player supporting FLAC, AAC, WAV, and OGG. Compatibility across formats, bit depths, and sample rates needed systematic validation."

**Task:**
"Create a comprehensive 120-file test library covering all formats, sample rates, and edge cases."

**Action:**
"My library covered: MP3 (CBR/VBR), FLAC (16/24-bit), AAC (LC/HE), WAV, OGG at 44.1kHz, 48kHz, and 96kHz, plus edge cases — files over 4GB, zero-duration files, missing ID3 tags, and corrupted headers. For each file I validated: playback start within 2s, no distortion, metadata display, and seek backward/forward. I found 11 failures including OGG at 96kHz/24-bit causing a crash, missing ID3 tags showing garbled characters, and 32-bit WAV playing at double speed."

**Result:**
"9 of 11 defects were fixed. 2 were documented as platform limitations in release notes. My media library became the standard compatibility test asset for the project."

---

### Story 6E: FM Radio RDS Corruption on RF Transition

**Situation:**
"During FM Radio testing on a Lexus headunit, RDS station names were displaying corrupted characters when the vehicle moved from a weak to a strong signal zone."

**Task:**
"Reproduce the RDS corruption under controlled conditions and identify the root cause."

**Action:**
"I used an RF signal generator to simulate signal strength transitions from -80dBm to -30dBm at instant, 1-second ramp, and 5-second ramp speeds. I captured the RDS data stream via I2C bus logs. During instant transitions, the tuner briefly lost lock and reset its RDS buffer mid-reception. When it re-locked, it decoded from a mid-group offset, causing character shift. A 1-second ramp showed no corruption."

**Result:**
"SW team added a 500ms RDS buffer hold-off after signal lock re-acquisition. Post-fix, 0 corruption events across 200 test cycles. I added RF transition tests at 3 ramp speeds to the Radio test suite."

---

## Project 7: Cross-Domain & Process Excellence

### Story 7A: Building a Reusable CAPL Utility Library

**Situation:**
"After working on 3 ADAS projects, I noticed each project was building CAPL scripts from scratch — no shared library, causing effort duplication and inconsistent test quality."

**Task:**
"Create a reusable CAPL utility library shareable across projects."

**Action:**
"I identified the most common needs: CAN signal monitoring with configurable timeouts, UDS diagnostic helpers (send request, validate response, check NRC), timer-based timestamp measurement, and XML pass/fail report generation. I built 25 reusable functions, each documented with inline comments and a usage example. I ran a 1-hour knowledge-sharing session for 8 engineers and created a getting-started guide."

**Result:**
"Within 2 sprints, 5 team members adopted the library. New script development time reduced by 40% for common test scenarios. The library was added to the project's version-controlled repo as the team's standard toolset."

---

### Story 7B: Thermal Soak — Reproducing a 3x-Closed DTC

**Situation:**
"At BYD, a DTC related to the ultrasonic sensor power supply was appearing intermittently during soak tests over 4 hours. Development had closed the defect twice as 'not reproducible' because short tests never triggered it."

**Task:**
"Design a test that reliably reproduces the DTC and provides root cause data."

**Action:**
"I hypothesized thermal drift and set up a 4-hour soak in a thermal chamber at 45 degrees C, cycling ignition ON/OFF every 30 minutes while logging the sensor power supply DID via UDS 0x22 every 60 seconds. After 3 hours the DTC appeared. The DID trend showed voltage dropping from 5.05V to 4.78V — below the 4.80V minimum spec."

**Result:**
"The hardware team found the power rail capacitor had high ESR at elevated temperature, causing the voltage drop. A revised capacitor was qualified. I added a 4-hour thermal soak test to the standard ECU power rail validation plan."

---

### Story 7C: ISO 26262 FMEA Test Coverage Review

**Situation:**
"At BMW, the safety team invited the testing team to participate in an FMEA review for the ADAS ECU to ensure all ASIL-B failure modes had test coverage."

**Task:**
"Review 18 FMEA rows related to sensor input failures and verify test case coverage."

**Action:**
"For each of the 18 FMEA rows I checked: does a test case exist, is it executable on HIL, and does it cover the exact failure mode described. I found 4 failure modes with no test coverage: camera signal frozen for over 500ms, radar object count stuck at maximum, multi-sensor disagreement (camera says clear, radar says obstacle), and sensor timestamp rollover at 65535ms. I wrote test case descriptions for all 4 and estimated HIL implementation effort."

**Result:**
"All 4 new test cases were added to the safety test suite. ASIL-B sensor failure mode coverage improved from 89% to 100%. My contribution was documented in the project Safety Case."

---

### Story 7D: Self-Service HIL Onboarding Guide

**Situation:**
"At BYD, 3 new engineers joined simultaneously. The HIL setup was complex — involving dSPACE hardware, VT Studio, CANoe, CAPL scripts, and UDS tools. There was no written guide, and senior engineers were spending 2+ days per new joiner on assisted setup."

**Task:**
"Create a self-service HIL environment onboarding guide."

**Action:**
"I spent 2 days documenting the complete setup: dSPACE hardware connections and I/O channel mapping, VT Studio model loading and parameter configuration, CANoe DBC and ARXML database setup, CAPL script library installation, UDS tool (CANdela) project configuration, and a first-test-run walkthrough. I added screenshots for every step and a 'Common Setup Errors and Fixes' section. I validated the guide by having one new joiner follow it independently."

**Result:**
"The new joiner completed the full HIL environment setup in 4 hours independently, compared to the previous 2-day assisted process. The guide was adopted as the official project onboarding document, reducing senior engineer setup time by 80%."

---

### Story 7E: Resolving a 3-Week Cross-Team Deadlock on ACC Defect

**Situation:**
"At BMW, a critical ACC defect about incorrect resume behavior after Temporary Speed Limiter deactivation had been open for 3 weeks. Development said it was a test environment issue. The test team said it was a real bug. Neither team was making progress."

**Task:**
"As the senior tester on the ACC feature, I was asked to investigate and mediate."

**Action:**
"I set up the reproduction scenario independently and captured a fresh CAN trace without referencing either team's previous analysis. In a joint review I walked through the trace: the TSL_Active signal was still set when the ACC_Resume switch command arrived — 20ms before TSL went to 0. The ACC ECU was rejecting the resume command as invalid while TSL was technically still active. I confirmed this was consistently reproducible across 20 test runs and proposed the fix: the ACC should accept a resume command within 200ms before TSL deactivation."

**Result:**
"Both teams agreed on the root cause during the review session. The development team implemented the fix in 2 days — resolving a 3-week impasse. This case demonstrated the value of neutral, data-driven analysis in cross-team disagreements."

---

### Story 7F: CAPL-Based DTC Lifecycle Automation

**Situation:**
"Validating the full DTC lifecycle — fault injection, DTC set, pending, confirmed, aged, healed, cleared — was a 3-day manual effort for 50 DTCs at BYD. It was also error-prone because timing-sensitive state transitions were checked manually."

**Task:**
"Automate the DTC lifecycle test to reduce execution time and improve repeatability."

**Action:**
"I built a CAPL script that: injected each fault via CAN signal manipulation, waited for the DTC to appear via 0x19 02, verified DTC status byte progression through all 6 lifecycle stages, verified freeze frame data via 0x19 04, sent 0x14 to clear DTCs, and verified removal. I parameterized the script with a config table — adding a new DTC required only one table row with: fault signal name, expected DTC code, and threshold values."

**Result:**
"DTC lifecycle testing for 50 DTCs completed in 4 hours automated vs 3 days manually. The framework was extended to 120 DTCs in the next release. Zero DTC lifecycle defects escaped to system integration in the subsequent 3 sprints."

---

### Story 7G: ECU Boot Time Performance Analysis

**Situation:**
"The ADAS ECU at BYD had a requirement: all safety-critical functions must be available within 500ms of ignition ON. During late integration testing, I measured 650-700ms actual initialization time."

**Task:**
"Measure boot time precisely by phase and identify the initialization bottleneck."

**Action:**
"I built a CAPL measurement script capturing timestamps at: first CAN message after KL15 (T0), first ADAS ECU message (T1), ADAS_SensorInit_Complete signal (T2), and ADAS_SafetyReady signal (T3). I ran 100 boot cycles and generated statistics: mean, min, max, and standard deviation per phase. Results showed T2 — sensor initialization — consumed 420ms of the total 650ms. I shared the per-phase breakdown with the ADAS software architect, who found sensor calibration data was being loaded from NVM sequentially. Parallelizing all 4 sensor loads reduced T2 from 420ms to 180ms."

**Result:**
"Post-fix mean total boot time was 390ms — within the 500ms requirement with margin. I added the boot-time measurement script to the project KPI tracking dashboard for continuous monitoring."

---

### Story 7H: CAN Gateway Routing Validation via Python

**Situation:**
"After a Central Gateway ECU software update at BMW, I noticed some Powertrain network signals were not reaching the ADAS network correctly through routing."

**Task:**
"Verify all 135 routing rules in the Gateway specification were correctly implemented in the new software."

**Action:**
"I wrote a Python script that: injected each signal on its source network using a CANoe simulation node, monitored the destination network for the expected routed signal, and compared the received value, cycle time, and CAN message ID against the routing specification. I ran all 135 routing rules in an automated overnight sequence. Results: 127 passed, 8 failed — 4 signals were routed to wrong CAN IDs on the ADAS network, 2 had doubled cycle time, and 2 were missing from the routing table entirely."

**Result:**
"All 8 routing defects were filed with exact signal names, expected vs actual CAN IDs, and trace evidence. All were fixed in the next gateway SW build. My Python routing validation script saved 2 days of manual verification per gateway release and was adopted as the standard tool for gateway testing."

---

## Extended Quick Reference — Stories 4 to 7

| # | Project | Story Title | Key Metric | Best For Question |
|---|---------|-------------|-----------|-------------------|
| 4A | BYD | BSD false alarm — DBC bitfield swap | Found DBC swap error | CAN DBC, signal analysis |
| 4B | BYD | PA audio cadence CAPL script | Caught 3Hz vs 5Hz deviation | CAPL automation, sensor |
| 4C | BYD | UDS security access timing fix | 100% flash reliability | UDS 0x27, timing issue |
| 4D | BYD | MVC stitching — bright light | Lux-dependent regression found | Camera testing, HIL |
| 4E | BYD | ASPICE traceability audit | 98% bi-directional coverage | ASPICE, documentation |
| 5A | BMW | LKA curvature edge condition | 400m failure boundary found | LKA, parametric HIL |
| 5B | BMW | ACC speed accuracy on gradient | +/-1.5 km/h post-fix | ACC, HIL calibration |
| 5C | BMW | FCW gantry false positive | 0/40 false alerts post-fix | Radar, false positive |
| 5D | BMW | Cluster 30-warning priority matrix | 4 P1-suppression bugs found | Cluster, CAPL priority |
| 5E | BMW | Freeze frame NVM write timing | 100% valid freeze frames | UDS 0x19, NVM timing |
| 6A | Lexus | HFP echo — SCO teardown fix | Echo-free across 10 calls | BT HFP, audio |
| 6B | Lexus | OTA map update validation | Found partial write defect | OTA, UDS validation |
| 6C | Lexus | Android Auto USB reconnect | 100% reconnect all devices | Android Auto, USB |
| 6D | Lexus | 120-file media format library | 11 format defects found | Media, format compatibility |
| 6E | Lexus | RDS corruption on RF transition | 0/200 corruption post-fix | Radio, RF testing |
| 7A | Cross | Reusable CAPL utility library | 40% script dev time saved | Initiative, framework |
| 7B | BYD | Thermal soak — 3x-closed DTC | Reproduced with voltage data | Soak testing, root cause |
| 7C | BMW | FMEA safety coverage review | 89% to 100% ASIL-B coverage | ISO 26262, safety |
| 7D | BYD | HIL self-service onboarding guide | 2 days to 4 hours setup | Documentation, mentoring |
| 7E | BMW | 3-week deadlock resolved | Fixed in 2 days post-analysis | Communication, cross-team |
| 7F | BYD | DTC lifecycle automation | 3 days to 4 hours (50 DTCs) | CAPL, UDS DTC |
| 7G | BYD | ECU boot time optimization | 650ms to 390ms | Performance, boot time |
| 7H | BMW | Gateway routing — Python script | 8 routing defects found | CAN routing, Python |
