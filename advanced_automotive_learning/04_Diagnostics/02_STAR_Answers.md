# DIAGNOSTICS — STAR INTERVIEW STORIES
## Module 4 of 7 | 7 Ready-to-Use STAR Answers

---

## STAR-1: Catching a DTC Debouncing Bug Before Production

**Situation:**
During ADAS validation, a review of DTC behavior showed that the FCW_FAILURE diagnostic event was being stored as a confirmed DTC (bit 3 = 1) within 20ms of a sensor fault being injected — far faster than the required 100ms debounce window (10 × 10ms evaluation period).

**Task:**
Determine whether the debounce was misconfigured and assess the impact on vehicle diagnostics quality.

**Action:**
1. Injected a 10ms FCW sensor fault and checked DTC status byte via UDS 0x19: bit 3 was already set. Expected: bit 3 not set after a single evaluation cycle.
2. Read the ARXML `<DemDebounceCounterBasedClass>` for FCW: `<DemDebounceCounterFailedThreshold>1</DemDebounceCounterFailedThreshold>`. Threshold was set to 1 — first failure immediately confirms the DTC.
3. The requirement said: "threshold = 10 evaluations (100ms)." Developer had left the default value of 1 and never changed it.
4. Quantified the impact: with threshold=1, any single noise spike (EMI, transient wiring glitch) would set a confirmed DTC — leading to false MIL lamp and incorrect workshop repairs.
5. Corrected threshold to 10 in ARXML, rebuilt DEM, retested: DTC now requires 10 consecutive failures (100ms) before confirming.

**Result:**
Bug classified as critical — would have caused false MIL on 30–50% of production vehicles based on EMI testing data. Fix delivered to software team. Added DEM debounce thresholds to the pre-build ARXML review checklist. Zero false DTC storage in subsequent 6-month production validation.

---

## STAR-2: Security Access Lockout Test Failure

**Situation:**
During end-of-line (EOL) testing at the production plant, 8% of vehicles were failing the security access test and timing out. The EOL test sent the correct security key, but the ECU was returning NRC 0x37 (requiredTimeDelayNotExpired) — lockout active.

**Task:**
Determine why production ECUs were entering lockout during EOL security access, causing test failures and production line stops.

**Action:**
1. Collected logs from 5 failed vehicles: NRC 0x37 was returned on the very first SecurityAccess attempt — as if a lockout was pre-existing.
2. Checked ECU NvM contents via 0x23 (ReadMemoryByAddress) for the security access attempt counter. It showed: Attempts = 3, LockoutActive = 1.
3. Root cause trace: ECUs were arriving at EOL with a previously triggered lockout from the ECU supplier's end-of-line flash sequence. The supplier's EOL tool sent 3 incorrect security keys (during a protocol alignment error) — triggering lockout — and shipped the ECUs without clearing it.
4. Immediate fix: added a 15-second power cycle before the security access step to allow lockout timer to expire.
5. Long-term fix: required ECU supplier to verify NvM security access counter = 0 at shipment as part of their acceptance test.

**Result:**
Production line failure rate dropped from 8% to 0.2% (residual due to other issues). Supplier contract updated with explicit shipment requirement. Root cause documented in the ECU integration guide.

---

## STAR-3: Building a DTC Dashboard for Workshop Engineers

**Situation:**
Workshop engineers at a dealership were spending 20–30 minutes per vehicle manually interpreting raw DTC hex codes from the scan tool. They needed a translation tool that mapped hex DTCs to meaningful descriptions, recommended next steps, and tracked DTC history across vehicle visits.

**Task:**
Build a DTC interpretation tool that workshop engineers could use without diagnostic expertise.

**Action:**
1. Exported the DEM event catalog from ARXML as a JSON file: {DTC_hex: {description, group, ASIL, recommended_action}}.
2. Built a Python Flask web application: upload scan tool CSV export → auto-decode DTC status bytes → display human-readable descriptions with severity color coding.
3. Added "recommended next steps" field per DTC (provided by calibration engineers): "Check FCW camera alignment" for FCW_FAILURE.
4. Added vehicle history: stored previous DTC sets per VIN; highlighted new DTCs that appeared since last visit (orange) and recurring DTCs (red).
5. Deployed on a Raspberry Pi in the workshop — accessible from any PC on the workshop network.

**Result:**
DTC interpretation time reduced from 25 minutes to 3 minutes per vehicle. Workshop engineers rated the tool 4.8/5 in a satisfaction survey. The tool was shared with 3 other dealerships. Intermittent DTC pattern detection (recurring faults across 2+ visits) identified a field software defect that was then patched via OTA.

---

## STAR-4: OBD-II Readiness Test Failure Root Cause

**Situation:**
A batch of 500 vehicles at an emissions test station had a 12% failure rate on OBD-II readiness check (Mode 0x01 PID 0x41). The catalyst monitor was showing "incomplete." This was blocking vehicle registration.

**Task:**
Determine why the catalyst monitor was not completing and provide a resolution within 48 hours (vehicles were blocking registration).

**Action:**
1. Tested a failing vehicle: ran a complete warm-up drive cycle per OBD-II monitor requirements (cold start, reach operating temp, drive at 40–60 km/h for 5 minutes). Catalyst monitor still showed "incomplete."
2. Read Mode 0x06 (Test results for on-board monitoring tests) — found catalyst monitor test ID 0x41 showing "not run" even after drive cycle.
3. Compared with a passing vehicle's ECU software version. Failing vehicles had software version X.1, passing had X.2. Software changelog showed: "Fixed catalyst monitor enable condition — added 80°C coolant temperature threshold."
4. Root cause: catalyst monitor had a software bug — it would only run if coolant temperature exceeded 80°C before the monitor evaluation window. Vehicles with 15-minute warm-up were reaching only 78–79°C in winter ambient (5°C outside).
5. Solution: vehicles required a 5-minute extended idle warm-up before the drive cycle to reach 80°C, OR an OTA software update (X.2) to lower the threshold to 70°C.

**Result:**
OTA update deployed to 350 of 500 vehicles wirelessly within 24 hours. Remaining 150 vehicles received a warm-up procedure. All 500 vehicles cleared emissions test. Root cause added to the OBD-II monitor validation matrix as a new test scenario.

---

## STAR-5: UDS Flash Sequence Failing at CheckMemory Step

**Situation:**
During software update testing, the flash sequence was succeeding up to the RequestTransferExit (0x37) but then failing at the RoutineControl CheckMemory step (0x31 01 FF 01) with NRC 0x31 (requestOutOfRange). This blocked the entire OTA capability.

**Task:**
Root-cause the CheckMemory failure and restore the flash capability.

**Action:**
1. Sent CheckMemory routine with address and size matching the flashed region. NRC 0x31.
2. Tested with known-correct parameters from the previous software version — same NRC 0x31.
3. Read the DCM ARXML `<DcmDspRoutineIdentifier>` for routine 0xFF01: found `<DcmDspRoutineUsePort>USE_DATA_ELEMENT_REF</DcmDspRoutineUsePort>` — this meant the routine was provided by an application SWC, not DCM built-in.
4. The application SWC implementing the checksum routine had a version incompatibility: it expected a 6-byte parameter (address 4B + size 2B) but the tester was sending an 8-byte parameter (address 4B + size 4B). The ARXML interface had been updated but the SWC implementation had not.
5. Updated the SWC to accept 8-byte parameter, or alternatively updated the tester script to send 6-byte parameter matching the SWC expectation.

**Result:**
Flash sequence passing in 100% of test runs after fix. Parameter size alignment issue added to the interface review checklist between DCM team and application SWC team.

---

## STAR-6: Automated Diagnostic Test Suite Improving Coverage

**Situation:**
Our diagnostic test suite had 75% requirement coverage — 25% of UDS requirements were untested because they were "too complex" to test manually. The ASPICE assessment was due in 6 weeks and SWE.5 required ≥ 95% test coverage with test evidence.

**Task:**
Increase diagnostic test coverage from 75% to ≥ 95% within 6 weeks using automation.

**Action:**
1. Gap analysis: identified 28 uncovered requirements — mostly around session transitions, NRC boundary conditions, security access lockout, and DTC debouncing edge cases.
2. Categorized by automation difficulty: 20 were automatable with Python DoIP client + UDS service calls; 8 required HIL fault injection (physical sensor faults).
3. Automated the 20 Python-testable cases in 2 weeks: session boundary tests (enter programming without security access → expect NRC 0x33), timeout tests (no TesterPresent → session expires in 5s), NRC matrix tests.
4. For the 8 fault injection tests: used relay box on bench to simulate sensor disconnects, wrote CAPL to control relay + monitor DEM response.
5. All tests integrated into Jenkins, run on every build.

**Result:**
Coverage: 97% in 5 weeks. ASPICE assessment passed SWE.5 with 0 major findings. 3 real defects found during the automation development: session expiry timer was 4.8s instead of 5.0s (timing violation), NRC 0x33 not returned for WriteDID in Default session, lockout counter not persisted across ECUReset.

---

## STAR-7: DTC Freeze Frame Data Quality Investigation

**Situation:**
Workshop engineers reported that freeze frame data (DTC snapshot of sensor values at fault time) was showing "all zeros" for the FCW_FAILURE DTC — making it impossible to diagnose what conditions triggered the fault.

**Task:**
Determine why freeze frame data was empty and restore meaningful diagnostic data.

**Action:**
1. Injected FCW_FAILURE via signal fault injection on bench. Read DTC + freeze frame via UDS 0x19 subfunction 0x04 (readDTCSnapshotRecordByDTCNumber).
2. All freeze frame DIDs returned 0x00 values.
3. Examined DEM ARXML: `<DemFreezeFrameRef>` pointed to DID 0xFD00. Read DID 0xFD00 independently via 0x22 — returned correct non-zero sensor data.
4. Root cause: the DEM freeze frame capture was triggered on the first fault evaluation (debounce evaluation 1 of 10), but the application SWC providing the DID data had not yet been initialized at that point in the startup sequence. The DID read returned all zeros because the SWC's internal data buffer was still at init state.
5. Fix: moved the freeze frame capture trigger to "confirmedDTC" event (evaluation 10) instead of "failedThisMonitoringCycle" (evaluation 1). By confirmation time, all SWCs were fully initialized.

**Result:**
Freeze frame data now correctly captures sensor values at fault confirmation. Workshop diagnosis accuracy improved. Fix also resolved a secondary issue: freeze frames were previously overwriting meaningful data on each evaluation cycle, now only captured once per confirmation.

---

*Next: [03_Mini_Projects.md](03_Mini_Projects.md)*
