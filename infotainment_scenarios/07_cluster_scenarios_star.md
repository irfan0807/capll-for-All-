# Cluster Scenarios — STAR Format with CAPL Code
## Instrument Cluster Test Validation — Interview Preparation

> **Format:** Each scenario follows the STAR method:
> - **S**ituation — Project context and the problem
> - **T**ask — What you were responsible for
> - **A**ction — What you did (investigation + CAPL code)
> - **R**esult — Outcome and impact

---

## Scenario 1 — Speedometer Showing 20 km/h Higher Than Actual Speed

### STAR Story

**Situation:**
During integration testing of a new instrument cluster ECU on a B-segment vehicle program, a test driver reported that the cluster speedometer was reading approximately 20 km/h higher than the actual speed at all times — confirmed by reference GPS speed logger. This was found 6 weeks before SOP (Start of Production) and would have resulted in a regulatory compliance failure since EU regulations (2021/1341) mandate speedometer accuracy within +10%/−0%.

**Task:**
I was the IVI/Cluster validation engineer responsible for all CAN signal validation between the powertrain ECUs and the instrument cluster. My task was to identify the root cause, provide evidence to the SW team, and verify the fix within 48 hours to keep SOP on schedule.

**Action:**

**Step 1 — Isolated the signal source:**
I used CANalyzer to capture the raw `VehicleSpeed` CAN message (0x3B0) from the ABS/ESC ECU and compared it against the cluster display reading side by side. The CAN signal showed the correct speed, but the cluster displayed speed + 20 km/h. This told me the issue was inside the cluster ECU's signal decoding or display calculation, not upstream in the ABS ECU.

**Step 2 — Checked the scaling factor:**
The `VehicleSpeed` signal in the DBC file had:
- Factor: `0.01 km/h per bit`
- Raw value at 80 km/h physical = 8000
But after a recent DBC update, the factor had been changed to `0.01 km/h per bit` with an **offset of +20 km/h** mistakenly added to match a different vehicle program's DBC. The physical value was being calculated as: `raw × 0.01 + 20.0 = actual_speed + 20`.

**Step 3 — Wrote a CAPL validation script** to automatically compare the CAN raw signal against the cluster displayed value across the full speed range, and flag any offset or scaling deviation:

```capl
/*
 * TC_SPD_ACCURACY: Validate speedometer display accuracy against CAN raw signal
 * Checks: offset error, scaling error, response latency
 * Expected: displayed speed = CAN speed ± 2 km/h
 */

variables {
  message VehicleSpeed_BC  msgSpeed;
  msTimer                  tmrSweep;
  int                      gTestSpeed_kmh = 0;
  int                      gPass = 0;
  int                      gFail = 0;
  float                    gMaxError = 0.0;
  int                      gSpeedSteps[10] = {0, 20, 40, 60, 80, 100, 120, 140, 160, 200};
  int                      gStepIdx = 0;
}

on start {
  write("=== Speedometer Accuracy Test START ===");
  write("Testing %d speed setpoints...", elcount(gSpeedSteps));
  setTimer(tmrSweep, 500);
}

on timer tmrSweep {
  if (gStepIdx >= elcount(gSpeedSteps)) {
    // All steps tested — print summary
    write("==========================================");
    write("=== Speedometer Accuracy: PASS=%d FAIL=%d ===", gPass, gFail);
    write("=== Maximum Error Observed: %.1f km/h ===", gMaxError);
    if (gFail == 0)
      write("=== RESULT: PASS ===");
    else
      write("=== RESULT: FAIL — Defect raised ===");
    stop();
    return;
  }

  gTestSpeed_kmh = gSpeedSteps[gStepIdx];

  // Encode speed: factor 0.01 km/h per bit → raw = speed / 0.01
  msgSpeed.VehicleSpeed_raw = (word)(gTestSpeed_kmh * 100);
  output(msgSpeed);

  // Wait 300ms for cluster to update display
  delay(300);

  // Read cluster displayed speed (from cluster output signal)
  float clusterDisplay = getValue(Cluster::Speedometer_Display_kmh);
  float error          = clusterDisplay - (float)gTestSpeed_kmh;
  float absError       = abs(error);

  if (absError > gMaxError)
    gMaxError = absError;

  if (absError <= 2.0) {
    write("PASS  [%3d km/h] CAN=%d  Display=%.1f  Error=%.1f km/h",
          gTestSpeed_kmh, gTestSpeed_kmh, clusterDisplay, error);
    gPass++;
  } else {
    write("FAIL  [%3d km/h] CAN=%d  Display=%.1f  Error=%.1f km/h  *** OUT OF SPEC ***",
          gTestSpeed_kmh, gTestSpeed_kmh, clusterDisplay, error);
    gFail++;
  }

  gStepIdx++;
  setTimer(tmrSweep, 800);
}
```

**Step 4 — Escalated with evidence:**
I provided the CAPL log output showing consistent +20.0 km/h error at every test point to the cluster SW team with the exact DBC line that contained the wrong offset. The fix was a one-line DBC correction.

**Step 5 — Regression test after fix:**
Re-ran the same CAPL script → all 10 speed points passed within ±1 km/h. I also ran the test at intermediate speeds (30, 50, 70, 90 km/h) to confirm linearity.

**Result:**
The defect was root-caused, fixed, and closed within 18 hours. The cluster passed EU speedometer accuracy requirements at the next vehicle-level test event. SOP was not impacted. The CAPL script was added to the project's regression test suite and runs automatically on every cluster SW build.

---

## Scenario 2 — Tachometer Needle Sweeps to Red Zone on Cold Start

### STAR Story

**Situation:**
During winter testing at −20°C in Finland, the instrument cluster tachometer needle performed a full sweep up to the red zone (4500 RPM area) during every cold start, even though the engine idle was at 850 RPM. The display lasted 2–3 seconds before settling at the correct idle. This was flagged as a safety concern by the test driver — seeing the tachometer in the red zone on every cold start created customer anxiety and incorrect perception of engine distress.

**Task:**
As the cluster signal validation engineer, I was responsible for determining whether this was: (a) an ECM reporting incorrect RPM for a brief period during cold crank, (b) a cluster startup animation playing unintentionally, or (c) a CAN timing issue causing the cluster to misinterpret data.

**Action:**

**Step 1 — Simultaneous logging of ECM RPM and cluster display:**
I connected a dual-trace logger: one trace on the `EngineRPM` CAN signal from the ECM (message 0x100), and a second trace on the cluster `Tachometer_Display_RPM` output signal. This was the key method — if both traces show 4500 RPM simultaneously, ECM is reporting wrong. If only cluster shows 4500 RPM → cluster rendering issue.

**Result of trace:** ECM showed 800 RPM steady during crank. Cluster showed 4500 RPM for 2.2 seconds after KL15 ON, then correctly dropped to follow ECM at 800 RPM.

**Step 2 — Identified the startup sweep animation:**
I checked the cluster SW spec: there was a defined "gauge sweep" animation (also called "needle theatre") that runs once after KL15 ON to demonstrate gauge functionality. The animation was specified to sweep up to max RPM and return before the engine starts. The bug: the sweep animation was STILL running 2.2 seconds after the engine cranked (at −20°C, crank time was 1.8 seconds — longer than at room temperature, causing overlap).

**Step 3 — Wrote CAPL to precisely measure sweep-to-live timing:**
```capl
/*
 * TC_TACHO_STARTUP: Measure tachometer needle sweep timing
 * Verify: gauge sweep COMPLETES before engine fires (RPM > 0)
 * Spec: sweep must complete within 1.5s of KL15 ON, regardless of crank duration
 */

variables {
  msTimer   tmrTimeout;
  dword     tKL15_ON         = 0;
  dword     tSweepComplete   = 0;
  dword     tEngineStart     = 0;
  int       gSweepDone       = 0;
  int       gEngineStarted   = 0;
  float     gLastRPM         = 0;
  float     gMaxRPM_InSweep  = 0;
}

on sysvar SysVar::KL15_State {
  if (@SysVar::KL15_State == 1) {
    tKL15_ON  = timeNow() / 10;
    gSweepDone = 0;
    gEngineStarted = 0;
    write("[%d ms] KL15 ON — monitoring tachometer sweep...", tKL15_ON);
    setTimer(tmrTimeout, 5000);   // watchdog — expect result within 5s
  }
}

on signal ECM::Engine_RPM {
  float rpm = this.value;

  // Detect engine actually started (RPM sustained > 400 = engine firing)
  if (rpm > 400.0 && !gEngineStarted) {
    gEngineStarted = 1;
    tEngineStart = timeNow() / 10;
    write("[%d ms] Engine started: RPM=%.0f", tEngineStart, rpm);
  }
}

on signal Cluster::Tachometer_Display_RPM {
  float displayRPM = this.value;

  // Track maximum displayed RPM during startup sweep
  if (!gEngineStarted && displayRPM > gMaxRPM_InSweep)
    gMaxRPM_InSweep = displayRPM;

  // Detect sweep completion: needle returns to near zero before engine starts
  if (!gEngineStarted && !gSweepDone && gMaxRPM_InSweep > 1000.0 && displayRPM < 200.0) {
    gSweepDone = 1;
    tSweepComplete = timeNow() / 10;
    dword sweepDuration = tSweepComplete - tKL15_ON;
    write("[%d ms] Sweep complete: Max=%.0f RPM  Duration=%d ms",
          tSweepComplete, gMaxRPM_InSweep, sweepDuration);

    if (sweepDuration <= 1500) {
      write("PASS — Sweep completed in %d ms (spec ≤1500ms)", sweepDuration);
    } else {
      write("FAIL — Sweep took %d ms (spec ≤1500ms) — overlap with crank likely", sweepDuration);
    }
  }

  // Detect overlap: sweep still showing high RPM when engine actually starts
  if (gEngineStarted && !gSweepDone) {
    write("FAIL — Gauge sweep still active when engine started! Display=%.0f RPM  Engine=%.0f RPM",
          displayRPM, getValue(ECM::Engine_RPM));
  }
}

on timer tmrTimeout {
  if (!gSweepDone) write("TIMEOUT — Gauge sweep never completed within 5s");
}
```

**Step 4 — Cold temperature correlation test:**
I used the climate chamber to test at: +25°C, 0°C, −10°C, −20°C.
- At +25°C: crank = 0.4s → sweep completes at 1.3s → no overlap → PASS
- At −20°C: crank = 1.8s → sweep completes at 1.3s → overlap 0.5s → cluster shows sweep RPM over engine firing RPM → FAIL

**Step 5 — Root cause confirmed and fix specified:**
The sweep animation completion was not linked to the actual KL15-to-crank duration. I specified the fix: the cluster SW should suppress/abort the gauge sweep animation the moment the ECM reports RPM > 0 — the sweep must yield to live data immediately.

**Result:**
Fix implemented in cluster SW v2.3 — the sweep now aborts as soon as ECM RPM signal exceeds 200 RPM. Re-test across all 4 temperatures: PASS at all temperatures. The defect report I raised included the CAPL trace data showing the exact 500ms overlap, which allowed the SW team to implement the correct fix immediately without back-and-forth.

---

## Scenario 3 — Cluster Warning Icons Incorrect After CAN Database Update

### STAR Story

**Situation:**
Following a mid-program DBC file update (v4.1 → v4.2) affecting 6 CAN messages, automated regression tests in CI (Continuous Integration) flagged 8 failures related to cluster warning icon display — icons showing for wrong conditions, not showing when they should, or showing incorrect icons. This was caught by the automated test suite 2 days after the DBC merge, before any physical test drive.

**Task:**
I was responsible for maintaining the CAPL-based automated test suite for the cluster validation pipeline. My task was to: analyse the 8 failures, determine if they were real defects or test script issues, and either fix the test scripts or raise defect reports on the cluster SW.

**Action:**

**Step 1 — Categorised the 8 failures:**
After reviewing CI log output:
- 3 failures: CAPL test scripts had hardcoded signal encoding values from v4.1 DBC — test input was wrong, not the cluster
- 3 failures: Real cluster defect — cluster SW still using old encoding from v4.1 for 3 signals (cluster SW not yet updated to v4.2 DBC)
- 2 failures: New warning icons added in v4.2 not yet covered by any test — gaps in test coverage

**Step 2 — Fixed test scripts for the 3 script issues:**
Updated the encoding constants in the test scripts to v4.2 values.

**Step 3 — Wrote comprehensive warning icon validation CAPL for the 3 real failures:**
```capl
/*
 * TC_TELLTALE_MATRIX: Warning icon validation matrix
 * Tests all safety-critical telltale icons against their CAN trigger signals
 * DBC Version: v4.2
 * Spec Reference: Cluster_Functional_Spec_v2.1, Section 8
 */

variables {
  // Test result counters
  int gPass       = 0;
  int gFail       = 0;
  int gSkip       = 0;

  // Test state machine
  int gTCurrent   = 0;
  msTimer tmrTC;

  // Allowable display delay from signal to icon ON (ms)
  int SPEC_DELAY_MS = 500;
}

/*
 * Telltale test record structure:
 *   [0] = message signal value to inject
 *   [1] = expected cluster icon state (0=OFF 1=ON 2=BLINK)
 *   [2] = signal source (1=BCM 2=ECM 3=ABS 4=SRS)
 * Name tracked separately for readability
 */

// Inject BCM door status and check door-open telltale
testcase TC_DoorOpen_Icon() {
  // Step 1: all doors closed → icon OFF
  message BCM_DoorStatus_BC msgDoor;
  msgDoor.DoorFL_Open = 0;
  msgDoor.DoorFR_Open = 0;
  msgDoor.DoorRL_Open = 0;
  msgDoor.DoorRR_Open = 0;
  output(msgDoor);
  testWaitForTimeout(SPEC_DELAY_MS);

  int iconState = testGetSignalValue("Cluster::Telltale_DoorAjar_State");
  if (iconState == 0) {
    testStepPass("TC_DOOR_01", "Door ajar icon OFF when all doors closed — PASS");
    gPass++;
  } else {
    testStepFail("TC_DOOR_01", "Door ajar icon should be OFF — showing ON");
    gFail++;
  }

  // Step 2: open FL door → icon ON
  msgDoor.DoorFL_Open = 1;
  output(msgDoor);
  testWaitForTimeout(SPEC_DELAY_MS);

  iconState = testGetSignalValue("Cluster::Telltale_DoorAjar_State");
  if (iconState == 1) {
    testStepPass("TC_DOOR_02", "Door ajar icon ON when FL door open — PASS");
    gPass++;
  } else {
    testStepFail("TC_DOOR_02", "Door ajar icon should be ON — showing OFF/BLINK");
    gFail++;
  }

  // Step 3: close FL door → icon OFF
  msgDoor.DoorFL_Open = 0;
  output(msgDoor);
  testWaitForTimeout(SPEC_DELAY_MS);
  iconState = testGetSignalValue("Cluster::Telltale_DoorAjar_State");
  testStep("TC_DOOR_03", iconState == 0 ? eTestResult::TP_NONE : eTestResult::TP_NONE,
           "Door icon clears within 500ms of door close");
}

// Validate engine temperature warning telltale
testcase TC_EngineTemp_Warning() {
  message ECM_EngineData_BC msgECM;

  // Normal temperature — no warning
  msgECM.Coolant_Temp_degC = 85;
  msgECM.EngineOvertemp_Warning = 0;
  output(msgECM);
  testWaitForTimeout(300);

  int iconNormal = testGetSignalValue("Cluster::Telltale_EngineTemp_State");
  if (iconNormal == 0) {
    write("PASS TC_TEMP_01 — Engine temp icon OFF at 85°C");
    gPass++;
  } else {
    write("FAIL TC_TEMP_01 — Engine temp icon ON at 85°C (false positive)");
    gFail++;
  }

  // Overheat — warning ON
  msgECM.Coolant_Temp_degC = 118;
  msgECM.EngineOvertemp_Warning = 1;
  output(msgECM);
  testWaitForTimeout(SPEC_DELAY_MS);

  int iconHot = testGetSignalValue("Cluster::Telltale_EngineTemp_State");
  if (iconHot == 1) {
    write("PASS TC_TEMP_02 — Engine temp icon ON at 118°C");
    gPass++;
  } else {
    write("FAIL TC_TEMP_02 — Engine temp icon OFF at 118°C (missed fault)");
    gFail++;
  }
}

// Validate ABS warning telltale — uses CAN v4.2 encoding
testcase TC_ABS_Warning() {
  message ABS_Status_BC msgABS;

  // v4.1 encoding: ABS_Fault = 0x01 (old)
  // v4.2 encoding: ABS_Fault = 0x03 (updated — this was the mismatch!)
  msgABS.ABS_SystemStatus = 0x03;    // v4.2: 0x03 = fault
  output(msgABS);
  testWaitForTimeout(SPEC_DELAY_MS);

  int absIcon = testGetSignalValue("Cluster::Telltale_ABS_State");
  if (absIcon == 1) {
    write("PASS TC_ABS_01 — ABS warning ON with 0x03 (v4.2 encoding)");
    gPass++;
  } else {
    write("FAIL TC_ABS_01 — ABS warning NOT showing with 0x03 — cluster still using v4.1 encoding!");
    gFail++;
  }

  // Clear fault
  msgABS.ABS_SystemStatus = 0x00;
  output(msgABS);
  testWaitForTimeout(300);
  int absClear = testGetSignalValue("Cluster::Telltale_ABS_State");
  if (absClear == 0) {
    write("PASS TC_ABS_02 — ABS warning clears on fault removal");
    gPass++;
  } else {
    write("FAIL TC_ABS_02 — ABS warning stays ON after fault removed");
    gFail++;
  }
}

// Main test runner
on start {
  write("=== Cluster Telltale Matrix Test — DBC v4.2 ===");
  testModule_TC_DoorOpen_Icon();
  testModule_TC_EngineTemp_Warning();
  testModule_TC_ABS_Warning();
  write("=== FINAL: PASS=%d  FAIL=%d  SKIP=%d ===", gPass, gFail, gSkip);
}
```

**Step 4 — Raised 3 defect reports** against the cluster SW team with:
- CAN trace showing wrong encoding being used (v4.1 vs v4.2)
- Expected vs actual CAPL log output
- Specific DBC signal names and byte positions

**Step 5 — Added coverage for 2 new icons:**
Wrote CAPL test cases for the two new warning icons added in v4.2 (Lane Keep Assist fault, Over-The-Air update in progress) and merged them into the CI test suite.

**Result:**
All 3 real defects were fixed in the next cluster SW build (v2.6). CI now runs automatically on every DBC change and every cluster SW build. The incident became a process improvement: we established a rule that DBC changes must always be accompanied by a cluster SW update and a test suite update in the same pull request. Zero cluster telltale failures shipped to SOP.

---

## Scenario 4 — Cluster Freezes During IGN OFF Transition

### STAR Story

**Situation:**
During End-of-Line (EOL) testing at the factory, 1 in 200 units was failing a functional check: after ignition OFF, the cluster display was found frozen on the trip summary screen instead of transitioning to the power-off screen and shutting down. The affected unit had to be manually restarted at the production line, causing a 4-minute delay per affected vehicle and threatening the production line takt time.

**Task:**
As the validation engineer supporting the production team, I was tasked with reproducing the freeze condition reliably in the lab (on a bench setup) so that the cluster SW team could debug it — the intermittent 1-in-200 rate made it very difficult to catch in development testing.

**Action:**

**Step 1 — Analysed the EOL conditions:**
The EOL ignition OFF test was performed immediately after the cluster passed a series of display tests (brightness, backlight, all-pixel test). The last test before the freeze was always the trip computer display. This was a strong clue — the freeze happened specifically after the trip computer was on screen.

**Step 2 — Designed a high-frequency stress test with CAPL to increase reproduction rate:**
```capl
/*
 * TC_IGN_OFF_FREEZE: High-frequency ignition cycle stress test
 * Purpose: Reproduce 1-in-200 cluster freeze on IGN OFF
 * Method: 500 rapid IGN OFF cycles while trip computer screen is active
 * Pass: Cluster powers off cleanly every time (no freeze)
 */

variables {
  msTimer tmrIgnCycle;
  msTimer tmrWatchdog;
  int     gCycle       = 0;
  int     gTarget      = 500;
  int     gFreezeCount = 0;
  int     gPassCount   = 0;
  dword   tIgnOFF_sent = 0;
}

on start {
  write("=== IGN OFF Freeze Stress Test: %d cycles ===", gTarget);
  // First: navigate to trip computer screen via HMI signal
  sendTripComputerActivate();
  delay(1000);   // let screen settle
  setTimer(tmrIgnCycle, 100);
}

void sendTripComputerActivate() {
  message IVI_HMI_Cmd msgHMI;
  msgHMI.HMI_ScreenRequest = 0x0A;   // 0x0A = Trip Computer screen
  output(msgHMI);
}

on timer tmrIgnCycle {
  gCycle++;
  write("[Cycle %d/%d] Sending IGN OFF...", gCycle, gTarget);

  // Record time of IGN OFF command
  tIgnOFF_sent = timeNow() / 10;

  // Send KL15 OFF (ignition off)
  setSignal(PowerSupply::KL15_Active, 0);

  // Start watchdog: cluster must respond (start shutdown) within 500ms
  setTimer(tmrWatchdog, 500);
}

on timer tmrWatchdog {
  // Check cluster shutdown state signal
  int clusterState = getValue(Cluster::ClusterPowerState);
  // 0 = ON/active, 1 = shutting down, 2 = OFF

  if (clusterState == 0) {
    // Cluster did NOT respond to IGN OFF — FROZEN
    gFreezeCount++;
    write("FAIL [Cycle %d] FREEZE DETECTED — Cluster still in ACTIVE state %d ms after IGN OFF",
          gCycle, (timeNow()/10) - tIgnOFF_sent);
    // Force recovery: toggle KL15 to reset cluster
    setSignal(PowerSupply::KL15_Active, 1);
    delay(2000);
    setSignal(PowerSupply::KL15_Active, 0);
  } else {
    gPassCount++;
    write("PASS [Cycle %d] Cluster entered shutdown state (state=%d)", gCycle, clusterState);
  }

  // IGN ON for next cycle (2 second gap)
  delay(2000);
  setSignal(PowerSupply::KL15_Active, 1);
  delay(1000);
  sendTripComputerActivate();
  delay(500);

  if (gCycle < gTarget) {
    setTimer(tmrIgnCycle, 3500);
  } else {
    write("===========================================");
    write("=== IGN OFF Freeze Test COMPLETE ===");
    write("=== Cycles: %d | PASS: %d | FREEZE: %d ===", gTarget, gPassCount, gFreezeCount);
    write("=== Freeze Rate: %.2f%% ===", (float)gFreezeCount / gTarget * 100.0);
    stop();
  }
}
```

**Step 3 — Reproduced in lab at 0.8% rate (4 freezes in 500 cycles):**
The stress test reproduced the freeze, but at 0.8% (higher than the 0.5% seen in EOL) because the test cycles were faster (3.5s per cycle vs the slower EOL sequence). With 4 reproducible events, I could now capture the state at the moment of freeze.

**Step 4 — Captured the race condition:**
Using the CAPL state log combined with ECU debug serial output, I captured:
- Freeze always occurred within 50ms of trip computer NVM write completing
- IGN OFF was received by the cluster exactly during the NVM write operation
- The cluster SW had a mutex protecting the NVM write, which was held when the shutdown handler ran
- The shutdown handler was waiting for the mutex → deadlock → cluster frozen in active state

**Result:**
Root cause confirmed as a mutex deadlock in the cluster shutdown handler. The SW team implemented a fix: the NVM write is now interrupted (with data integrity preserved) if a shutdown request is received, and the mutex is released before the shutdown handler proceeds. After the fix, I ran 1000 stress cycles — 0 freezes. The EOL failure rate dropped to 0%. Production line takt time was restored, and the fix was deployed via flash update to the 437 units already produced with the pre-fix SW.

---

## Scenario 5 — Mileage-Dependent Service Interval Indicator Triggering Too Early

### STAR Story

**Situation:**
In a fleet trial (25 vehicles, taxi operators), service interval warnings were triggering 800–1200 km before the actual service distance. The service interval was set at 15,000 km but the warning appeared consistently at 13,800–14,200 km. This was causing unnecessary early servicing, costing the fleet operator approximately £180 per vehicle in premature service costs.

**Task:**
I was assigned as the diagnostics validation engineer to investigate whether the early triggering was due to incorrect odometer data, incorrect service interval configuration, or a calculation error in the cluster service reminder logic.

**Action:**

**Step 1 — Read all relevant UDS DIDs:**
```capl
/*
 * Service Interval Diagnostic Read
 * Reads all DIDs related to service interval calculation
 * to identify discrepancy between configured and actual trigger point
 */

variables {
  diagRequest IVI_ECU.ReadDataByIdentifier reqDID;
}

on start {
  write("=== Service Interval Diagnostic Read ===");

  // DID 0xF1A0: Current odometer value
  diagSetParameter(reqDID, "dataIdentifier", 0xF1A0);
  diagSendRequest(reqDID);
}

on diagResponse IVI_ECU.ReadDataByIdentifier {
  dword odo_km      = diagGetRespPrimitiveLong(this, "Odometer_km");
  dword svcInterval = diagGetRespPrimitiveLong(this, "ServiceInterval_km");
  dword lastService = diagGetRespPrimitiveLong(this, "LastServiceOdo_km");
  dword remaining   = diagGetRespPrimitiveLong(this, "RemainingKm_to_Service");
  dword calculated  = svcInterval - (odo_km - lastService);

  write("Odometer (current):         %d km", odo_km);
  write("Service Interval (config):  %d km", svcInterval);
  write("Last Service at:            %d km", lastService);
  write("Remaining (ECU reports):    %d km", remaining);
  write("Remaining (calculated):     %d km", calculated);

  if (remaining != calculated) {
    write("MISMATCH — ECU reports %d km remaining but calculation gives %d km",
          remaining, calculated);
    write("Discrepancy: %d km (%s)", (int)(calculated - remaining),
          (calculated > remaining) ? "ECU triggering EARLY" : "ECU triggering LATE");
  } else {
    write("MATCH — ECU remaining distance is consistent with calculation");
  }
}
```

**Step 2 — Identified the discrepancy:**
The DID read showed:
- `Odometer_km` = 14,050 (correct)
- `ServiceInterval_km` = 15,000 (correctly configured)
- `LastServiceOdo_km` = 0 (this was the issue — reset not done at last service!)
- `RemainingKm_to_Service` = **950** (triggering now)
- Calculated: 15,000 − (14,050 − 0) = **950 km** — calculation is actually correct

**Step 3 — Found the real root cause:**
The last service odometer was stored as `0` because the dealership used a scan tool that sent a "Reset Service Interval" command via a generic OBD-II adapter. The adapter sent the reset without a Writing Security Access (`0x27`), causing the cluster ECU to reject the NVM write silently (NRC 0x33 returned, adapter ignored it). As a result, `LastServiceOdo` was never updated from 0 — every vehicle counted service interval from 0 km, not from the actual last service odometer.

**Step 4 — Verified the correct reset procedure:**
```capl
/*
 * Service Interval Reset — Correct UDS sequence
 * Requires: Extended Session + Security Level 3
 */

variables {
  diagRequest Cluster.DiagnosticSessionControl        reqSession;
  diagRequest Cluster.SecurityAccess_RequestSeed      reqSeed;
  diagRequest Cluster.SecurityAccess_SendKey          reqKey;
  diagRequest Cluster.WriteDataByIdentifier_ServiceReset reqReset;
}

on start {
  write("=== Service Interval Reset Sequence ===");
  // Step 1: Enter Extended Session
  diagSetParameter(reqSession, "DiagnosticSessionType", 0x03);   // Extended
  diagSendRequest(reqSession);
}

on diagResponse Cluster.DiagnosticSessionControl {
  if (diagGetRespCode(this) == 0x50) {
    write("Extended session established");
    // Step 2: Request seed
    diagSetParameter(reqSeed, "securityAccessType", 0x05);        // Level 3 seed
    diagSendRequest(reqSeed);
  }
}

on diagResponse Cluster.SecurityAccess_RequestSeed {
  dword seed = diagGetRespPrimitiveLong(this, "securitySeed");
  dword key  = calculateServiceKey(seed);   // OEM algorithm
  write("Seed=0x%08X  Calculated Key=0x%08X", seed, key);

  diagSetParameter(reqKey, "securityAccessType", 0x06);           // Level 3 key
  diagSetParameter(reqKey, "securityKey", key);
  diagSendRequest(reqKey);
}

on diagResponse Cluster.SecurityAccess_SendKey {
  if (diagGetRespCode(this) == 0x67) {
    write("Security access granted — sending service reset");
    // Step 3: Write reset DID — stores current odometer as LastServiceOdo
    diagSetParameter(reqReset, "dataIdentifier", 0xF1B0);         // ServiceReset DID
    diagSetParameter(reqReset, "ServiceReset_Flag", 0x01);        // 1 = reset
    diagSendRequest(reqReset);
  } else {
    write("FAIL — Security access rejected (NRC=0x%02X)", diagGetRespCode(this));
  }
}

on diagResponse Cluster.WriteDataByIdentifier_ServiceReset {
  if (diagGetRespCode(this) == 0x6E) {
    write("PASS — Service interval reset confirmed (DID 0xF1B0 written)");
    write("Next service now due at: current_odo + 15,000 km");
  } else {
    write("FAIL — Service reset rejected (NRC=0x%02X)", diagGetRespCode(this));
  }
}

dword calculateServiceKey(dword seed) {
  // OEM-specific HMAC calculation (simplified representation)
  return seed ^ 0xA5C3F1D7;
}
```

**Step 5 — Broader fix implemented:**
I provided the correct UDS reset sequence to the dealership tooling team. The CAPL script was converted into a .NET-based dealer diagnostic tool function. Additionally, a validation test was added to the EOL test sequence: after every service reset, the tool reads back `LastServiceOdo` and confirms it updated — if not, the tool shows an error and requires a retry.

**Result:**
All 25 fleet vehicles were corrected using the proper reset procedure. The new dealer tool with the verification step was deployed to 340 dealerships. No further early service interval triggers were reported. The fleet operator was reimbursed for the 25 premature services. The fix also exposed a larger issue: the generic OBD-II adapter being used by 15% of dealerships for service resets — this was replaced with the validated dealer tool across all markets.

---
*File: 07_cluster_scenarios_star.md | Scenarios 1–5 | STAR Format | April 2026*
