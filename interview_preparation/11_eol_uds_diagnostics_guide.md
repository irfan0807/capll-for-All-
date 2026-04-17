# EOL Testing & UDS Diagnostics — Complete Interview Guide
## Automotive Cluster Validation | April 2026

---

## PART 1 — UDS (Unified Diagnostic Services)

---

### What is UDS?

UDS stands for **Unified Diagnostic Services**.
It is the standard protocol used by diagnostic tools (scan tools, EOL testers, CANoe) to communicate with ECUs in a vehicle.

- **Standard:** ISO 14229
- **Transport layer:** ISO 15765 (CAN), ISO 10681 (FlexRay), DoIP (Ethernet)
- **Used for:** Reading data, writing data, clearing faults, programming ECUs, activating functions

Think of UDS as a **language** — the tester speaks UDS to the ECU, and the ECU replies in UDS.

---

### UDS Message Structure

Every UDS message follows this structure:

```
REQUEST (Tester → ECU):
  [ Service ID (1 byte) ] [ Sub-function/Parameters ] [ Data ]

RESPONSE (ECU → Tester):
  Positive: [ Service ID + 0x40 ] [ Data ]
  Negative: [ 0x7F ] [ Request Service ID ] [ NRC (error code) ]
```

**Example — Read Data:**
```
Request:  22 F1 90          → Read DID 0xF190 (VIN)
Response: 62 F1 90 57 56 31 → Positive response with VIN data
```

**Example — Negative Response:**
```
Request:  22 F1 90
Response: 7F 22 31          → 0x7F (negative) 0x22 (service) 0x31 (request out of range)
```

---

### The 10 Most Important UDS Services

#### 1. `0x10` — Diagnostic Session Control

Controls which diagnostic session the ECU is in.

| Sub-function | Session | Access Level |
|-------------|---------|--------------|
| `0x01` | Default Session | Everyone — read basic data |
| `0x02` | Programming Session | Software flashing |
| `0x03` | Extended Diagnostic Session | Full access — write, calibrate |

```capl
// Switch to Extended session
diagRequest ECU.DiagnosticSessionControl req;
diagSetParameter(req, "DiagnosticSessionType", 0x03);   // Extended
diagSendRequest(req);
// ECU must respond: 50 03 (positive) within 50ms
```

**Interview point:** You MUST be in the right session before many other services work.
Trying to write data in Default session → NRC `0x31` (request out of range) or `0x22` (conditions not correct).

---

#### 2. `0x11` — ECU Reset

Resets the ECU. Three types:

| Sub-function | Type | Effect |
|-------------|------|--------|
| `0x01` | Hard Reset | Full power cycle (like battery disconnect) |
| `0x02` | Key Off On Reset | Simulates ignition off → on |
| `0x03` | Soft Reset | Software restart, keeps NVM |

```capl
diagRequest ECU.ECUReset req;
diagSetParameter(req, "resetType", 0x01);   // Hard reset
diagSendRequest(req);
```

**When used in EOL:** After programming/calibration, ECU is reset to load new settings.

---

#### 3. `0x14` — Clear Diagnostic Information

Clears all DTCs (Diagnostic Trouble Codes) from the ECU's fault memory.

```
Request:  14 FF FF FF    → Clear all DTCs (group 0xFFFFFF = all)
Response: 54             → Positive (just the service response byte)
```

**Important:** `0x14` clears the DTC history but does NOT clear the fault itself.
If the fault condition still exists, the DTC will come back on the next drive cycle.

---

#### 4. `0x19` — Read DTC Information

The most important diagnostic service. Reads fault codes from the ECU.

| Sub-function | Name | What It Returns |
|-------------|------|-----------------|
| `0x01` | reportNumberOfDTCByStatusMask | How many DTCs match a status filter |
| `0x02` | reportDTCByStatusMask | List of DTCs matching status |
| `0x04` | reportDTCSnapshotDataByDTCNumber | Freeze frame data for a specific DTC |
| `0x06` | reportDTCExtendedDataByDTCNumber | Extended data (occurrence count, etc.) |
| `0x0A` | reportSupportedDTC | All DTCs supported by the ECU |

**Status mask (1 byte, 8 bits):**
```
Bit 0: testFailed           — fault is currently active
Bit 1: testFailedThisOp     — failed this operation cycle
Bit 2: pendingDTC           — failed at least once
Bit 3: confirmedDTC         — failed enough times to be confirmed
Bit 4: testNotCompletedSince — monitor not yet run
Bit 5: testFailedSince      — failed since last clear
Bit 6: testNotCompleted     — not run this operation cycle
Bit 7: warningIndicator     — warning lamp is on
```

```capl
// Read all confirmed DTCs (bit 3 = confirmed)
diagRequest ECU.ReadDTCInfo req;
diagSetParameter(req, "subfunction",    0x02);
diagSetParameter(req, "DTCStatusMask",  0x08);   // confirmed DTCs
diagSendRequest(req);

on diagResponse ECU.ReadDTCInfo {
  long dtc_count = diagGetRespArraySize(this, "DTCAndStatusRecord");
  write("Confirmed DTCs: %d", dtc_count);
  for (long i = 0; i < dtc_count; i++) {
    long dtc    = diagGetRespPrimitiveLong(this, "DTCAndStatusRecord[%d].DTC", i);
    byte status = diagGetRespPrimitiveByte(this, "DTCAndStatusRecord[%d].statusOfDTC", i);
    write("  DTC: 0x%06X  Status: 0x%02X", dtc, status);
  }
}
```

---

#### 5. `0x22` — Read Data By Identifier (RDBI)

Reads a specific data value from the ECU using a 2-byte identifier called a **DID** (Data Identifier).

```
Request:  22 F1 90        → Read DID 0xF190
Response: 62 F1 90 [data] → Positive response with data
```

**Common standard DIDs (ISO 14229):**
| DID | Name | Example Value |
|-----|------|---------------|
| `0xF186` | Active Diagnostic Session | `0x03` = extended |
| `0xF187` | Spare Part Number | ASCII string |
| `0xF188` | Programming Date | BCD date |
| `0xF189` | Application Software Version | Version bytes |
| `0xF190` | VIN | 17-byte ASCII |
| `0xF191` | ECU Hardware Version | Version bytes |
| `0xF18C` | ECU Serial Number | ASCII string |

```capl
// Read VIN
diagRequest Cluster.ReadDataByIdentifier req;
diagSetParameter(req, "dataIdentifier", 0xF190);
diagSendRequest(req);

on diagResponse Cluster.ReadDataByIdentifier {
  char vin[18];
  diagGetRespPrimitiveString(this, "VIN", vin, 17);
  write("VIN: %s", vin);
}
```

---

#### 6. `0x2E` — Write Data By Identifier (WDBI)

Writes data to the ECU. Requires Extended session + Security Access first.

```
Request:  2E F1 90 57 56 31 ...   → Write DID 0xF190 with data
Response: 6E F1 90                → Positive write confirmation
```

**EOL use cases:**
- Write variant coding (market, language, units)
- Write calibration values (backlight brightness PWM)
- Write odometer initial value
- Write production date / serial number

```capl
// Write variant code to cluster
diagRequest Cluster.WriteDataByIdentifier req;
diagSetParameter(req, "dataIdentifier",     0x0100);   // Variant DID
diagSetParameter(req, "MarketCode",         0x01);     // 0x01 = Europe
diagSetParameter(req, "LanguageCode",       0x02);     // 0x02 = English
diagSetParameter(req, "SpeedUnit",          0x01);     // 0x01 = km/h
diagSendRequest(req);
```

---

#### 7. `0x27` — Security Access

A two-step challenge/response to unlock write access or programming:

```
Step 1 — Request seed:
  Request:  27 01        → requestSeed (odd sub-function = seed request)
  Response: 67 01 AB CD  → seed = 0xABCD

Step 2 — Send key:
  Request:  27 02 [calculated key]  → sendKey (even sub-function = key send)
  Response: 67 02                   → access granted
```

The key is calculated from the seed using an algorithm known only to the OEM:
```
key = seed XOR 0x5A3C   (simple example — real algorithms are more complex)
```

**Security levels:** Different operations need different security levels:
- Level 1 (0x01/0x02): Diagnostic write access
- Level 3 (0x03/0x04): Programming / flashing
- Level 5 (0x05/0x06): EOL calibration

```capl
// Full security access sequence
variables {
  diagRequest Cluster.SecurityAccess_Seed reqSeed;
  diagRequest Cluster.SecurityAccess_Key  reqKey;
}

on start {
  diagSetParameter(reqSeed, "securityAccessType", 0x01);
  diagSendRequest(reqSeed);
}

on diagResponse Cluster.SecurityAccess_Seed {
  dword seed = diagGetRespPrimitiveLong(this, "securitySeed");
  dword key  = seed ^ 0x5A3C9F1E;   // OEM algorithm
  write("Seed: 0x%08X  Key: 0x%08X", seed, key);
  diagSetParameter(reqKey, "securityAccessType", 0x02);
  diagSetParameter(reqKey, "securityKey", key);
  diagSendRequest(reqKey);
}

on diagResponse Cluster.SecurityAccess_Key {
  if (diagGetRespCode(this) == 0x67) {
    write("Security access GRANTED");
  } else {
    write("Security access DENIED");
  }
}
```

---

#### 8. `0x31` — Routine Control

Triggers a function or test inside the ECU remotely.

| Sub-function | Action |
|-------------|--------|
| `0x01` | Start Routine |
| `0x02` | Stop Routine |
| `0x03` | Request Routine Results |

**Routine IDs are OEM-defined. Common examples:**
| Routine ID | Function |
|-----------|----------|
| `0x0203` | All-pixel display test |
| `0x0204` | Gauge sweep (needle theatre) |
| `0x0205` | Backlight full brightness test |
| `0x0210` | EOL complete check |
| `0xE101` | Memory (NVM) integrity check |

```capl
// Trigger gauge sweep routine
diagRequest Cluster.RoutineControl req;
diagSetParameter(req, "routineControlType", 0x01);    // Start
diagSetParameter(req, "routineIdentifier",  0x0204);  // Gauge sweep
diagSendRequest(req);

on diagResponse Cluster.RoutineControl {
  byte result = diagGetRespPrimitiveByte(this, "routineResult");
  write("Gauge sweep routine started: %d (1=OK)", result);
}
```

---

#### 9. `0x3E` — Tester Present

Keeps the ECU in an active diagnostic session. Without this, ECUs time out after ~5 seconds and return to Default session.

```
Request:  3E 00        (suppressPosRspMsgIndicationBit = 0 → send response)
Request:  3E 80        (suppressPosRspMsgIndicationBit = 1 → no response needed)
Response: 7E 00
```

In CANoe, this is typically sent every 2 seconds on a timer:
```capl
variables {
  msTimer tmrTesterPresent;
  diagRequest ECU.TesterPresent reqTP;
}

on start {
  diagSetParameter(reqTP, "subfunction", 0x80);   // No response needed
  setTimer(tmrTesterPresent, 2000);
}

on timer tmrTesterPresent {
  diagSendRequest(reqTP);
  setTimer(tmrTesterPresent, 2000);
}
```

---

#### 10. `0x85` — Control DTC Setting

Enables or disables DTC logging. Used during active testing to prevent spurious DTCs.

```
Request:  85 01    → Enable DTC setting (normal)
Request:  85 02    → Disable DTC setting (DTCs won't be stored during test)
Response: C5 01    → Positive
```

**EOL use:** Disable DTCs during the initial power-up sequence (some signals are absent during early boot → would falsely generate DTCs without this).

---

### NRC — Negative Response Codes (What Goes Wrong)

When an ECU rejects a request, it sends a Negative Response with an NRC byte.

| NRC (hex) | Name | Meaning |
|-----------|------|---------|
| `0x10` | generalReject | Generic rejection |
| `0x11` | serviceNotSupported | ECU doesn't support this service |
| `0x12` | subFunctionNotSupported | Sub-function not supported |
| `0x13` | incorrectMessageLength | Wrong number of bytes in request |
| `0x22` | conditionsNotCorrect | Wrong vehicle state for this request |
| `0x24` | requestSequenceError | Steps out of order (e.g. key before seed) |
| `0x25` | noResponseFromSubnetComponent | Gateway routing failed |
| `0x31` | requestOutOfRange | DID or routine not valid |
| `0x33` | securityAccessDenied | Not unlocked with 0x27 yet |
| `0x35` | invalidKey | Wrong key sent in 0x27 |
| `0x36` | exceededNumberOfAttempts | Too many wrong key attempts → locked out |
| `0x37` | requiredTimeDelayNotExpired | Too soon after failed security attempt |
| `0x70` | uploadDownloadNotAccepted | Flash programming rejected |
| `0x78` | requestCorrectlyReceivedResponsePending | ECU busy, wait for final response |

**`0x78` is special** — it means "I got your request, I'm working on it, wait."
The ECU sends `0x78` every 5 seconds while processing (e.g., flash write takes 30 seconds).
Your tester must keep waiting for the final positive/negative response.

---

## PART 2 — EOL (End of Line) Testing

---

### What is EOL Testing?

EOL (End of Line) testing is the **automated quality validation performed on every production unit** before it leaves the factory.

It is NOT:
- Development testing (that happens during design)
- Prototype validation (that happens before mass production)
- Field diagnostics (that happens at service workshops)

It IS:
- 100% inspection — every single unit
- Automated — runs in 30–90 seconds (must fit production takt time)
- Pass/fail — unit either ships or gets pulled for repair

---

### EOL for an Instrument Cluster — Full Test Sequence

```
┌─────────────────────────────────────────────────────────┐
│                   EOL TEST SEQUENCE                     │
│                                                         │
│  1. CONNECT       CAN/LIN/ETH tester + power supply     │
│  2. POWER ON      Apply KL30 (battery) + KL15           │
│  3. COMMS CHECK   UDS 0x10 01 → ECU responds?           │
│  4. SW VERSION    UDS 0x22 F189 → version matches?      │
│  5. VARIANT CODE  UDS 0x2E → write market/language      │
│  6. PIXEL TEST    UDS 0x31 → all pixels ON → measure    │
│  7. BRIGHTNESS    Photometer reads cd/m² → within spec? │
│  8. GAUGE SWEEP   UDS 0x31 → needles sweep → returns?   │
│  9. TELLTALES     All warning icons illuminate on cmd    │
│  10. NVM WRITE    Write calibration → readback verify   │
│  11. DTC CHECK    UDS 0x19 02 08 → zero confirmed DTCs? │
│  12. RESET        UDS 0x11 01 → ECU hard reset          │
│  13. BOOT CHECK   ECU comes back within 3s?             │
│  14. RESULT       PASS → ship | FAIL → repair queue     │
└─────────────────────────────────────────────────────────┘
```

---

### EOL Step by Step With UDS Commands

#### Step 1 — Communication Check
```
Send:    10 03              (Extended Diagnostic Session)
Expect:  50 03 xx xx        (Positive response)
Timeout: 50ms
Fail if: No response, or NRC received
```

#### Step 2 — Software Version Check
```
Send:    22 F1 89           (Read SW version DID)
Expect:  62 F1 89 [version bytes matching build spec]
Fail if: Version mismatch → wrong SW flashed
```

#### Step 3 — Security Access (for write operations)
```
Send:    27 01              (Request seed)
Receive: 67 01 [seed]
Calculate key from seed using OEM algorithm
Send:    27 02 [key]
Expect:  67 02              (Access granted)
```

#### Step 4 — Variant Coding
```
Send:    2E F0 01 [variant bytes]   (Write variant DID)
Expect:  6E F0 01                   (Written OK)
Verify:  22 F0 01 → readback = written value
```

#### Step 5 — Pixel Test
```
Send:    31 01 02 03        (Start routine 0x0203 — all pixels ON)
Wait:    500ms
Measure: Photometer grid across display
Expect:  Every zone within ±10% of mean brightness
Fail if: Any zone > 20% below mean (dead pixel cluster)
Send:    31 02 02 03        (Stop routine — pixels OFF)
```

#### Step 6 — Backlight Brightness Calibration
```
Measure: Actual cd/m² from photometer
Spec:    350–450 cd/m²
If out of spec:
  Calculate correction PWM value
  Send:    2E F2 50 [pwm_correction]   (Write backlight cal DID)
  Expect:  6E F2 50
  Remeasure: must be within 360–440 cd/m²
```

#### Step 7 — DTC Sanity Check
```
Send:    19 02 08           (Read confirmed DTCs)
Expect:  59 02 FF [no DTC records]   OR   59 02 00 with count = 0
Fail if: Any confirmed DTC present
Note:    Send 85 02 first to suppress DTCs during test startup
```

#### Step 8 — Final Reset and Re-check
```
Send:    11 01              (Hard reset)
Wait:    3000ms
Send:    10 01              (Default session)
Expect:  50 01 within 500ms (ECU booted and responding)
```

---

### Takt Time — Why Speed Matters

Takt time = time available per unit on the production line.

```
Factory produces 1000 clusters per day
Working day = 8 hours = 480 minutes
Takt time = 480 / 1000 = 0.48 minutes = 29 seconds per unit

EOL test must complete in < 29 seconds or it becomes the bottleneck
```

This is why:
- Photometer measurement must be fast (< 2 seconds)
- ECU resets must be quick (ECU boot < 3 seconds)
- All steps are parallelised where possible
- Failures exit immediately (don't run remaining steps)

---

### Common EOL Failure Modes

| Failure | Cause | Investigation |
|---------|-------|---------------|
| **No comms** | ECU not booting, wrong CAN address, gateway routing | Check power, CAN termination, address |
| **SW version mismatch** | Wrong software flashed at prior station | Check flash station logs |
| **Dead pixels** | Damaged flex connector, cracked LED, LCD defect | Map zone → trace to driver IC or connector |
| **Brightness out of spec** | LED bin variation, PWM wrong | Check LED batch, recalibrate |
| **Confirmed DTC** | Signal absent during startup, suppression not working | Check 0x85 02 was sent, check startup timing |
| **Security access denied** | Wrong key algorithm, wrong security level | Check algorithm version match between tester and ECU |
| **NVM write fail** | Write in wrong session, not enough NVM cycles | Check session, check NVM write cycle count |
| **ECU no reboot** | Hard reset caused NVM corruption, boot loop | Check power stability during reset |

---

### EOL vs Other Test Types (Know the Difference)

| | **EOL** | **Validation** | **Field Diagnostics** |
|--|---------|---------------|----------------------|
| When | End of production line | Engineering/design phase | Service workshop |
| Who runs it | Production technician / robot | Test engineer | Dealer technician |
| Coverage | 100% of units | Sample / all variants | Specific faulted vehicle |
| Duration | 30–90 seconds | Hours/days | 15 minutes |
| Tool | Dedicated EOL tester | CANoe, HIL | VAS, VIDA, ISTA scan tool |
| Goal | Detect manufacturing defects | Prove design meets spec | Diagnose customer complaint |

---

### EOL CAPL Script Template

```capl
/*
 * Cluster EOL Test Automation — CANoe CAPL
 * Runs complete EOL sequence and logs result
 */

variables {
  diagRequest Cluster.DiagnosticSessionControl  reqSession;
  diagRequest Cluster.SecurityAccess_Seed       reqSeed;
  diagRequest Cluster.SecurityAccess_Key        reqKey;
  diagRequest Cluster.ReadDataByIdentifier      reqRead;
  diagRequest Cluster.WriteDataByIdentifier     reqWrite;
  diagRequest Cluster.RoutineControl            reqRoutine;
  diagRequest Cluster.ReadDTCInfo               reqDTC;
  diagRequest Cluster.ECUReset                  reqReset;
  diagRequest Cluster.ControlDTCSetting         reqDTCCtrl;

  int gPassCount  = 0;
  int gFailCount  = 0;
  int gStepNum    = 0;
  char gUnitSerial[20] = "SN12345678";

  // Expected values
  byte  EXPECTED_SW_VERSION[4] = {0x02, 0x05, 0x01, 0x00};
  float BRIGHTNESS_MIN         = 350.0;   // cd/m²
  float BRIGHTNESS_MAX         = 450.0;
}

void logStep(char step[], int pass, char detail[]) {
  gStepNum++;
  if (pass) {
    gPassCount++;
    write("[STEP %02d PASS] %s — %s", gStepNum, step, detail);
  } else {
    gFailCount++;
    write("[STEP %02d FAIL] %s — %s", gStepNum, step, detail);
  }
}

// ─── STEP 1: Communication Check ─────────────────────────────
on start {
  write("==============================");
  write("EOL TEST START — Unit: %s", gUnitSerial);
  write("==============================");

  diagSetParameter(reqSession, "DiagnosticSessionType", 0x03);
  diagSendRequest(reqSession);
}

on diagResponse Cluster.DiagnosticSessionControl {
  if (diagGetRespCode(this) == 0x50) {
    logStep("CommunicationCheck", 1, "Extended session established");
    // Proceed to disable DTC storage
    diagSetParameter(reqDTCCtrl, "subfunction", 0x02);
    diagSendRequest(reqDTCCtrl);
  } else {
    logStep("CommunicationCheck", 0, "No UDS response from cluster");
    eolComplete();
  }
}

// ─── STEP 2: Disable DTC Storage ─────────────────────────────
on diagResponse Cluster.ControlDTCSetting {
  logStep("DisableDTCStorage", (diagGetRespCode(this) == 0xC5), "0x85 02 sent");
  // Read SW version
  diagSetParameter(reqRead, "dataIdentifier", 0xF189);
  diagSendRequest(reqRead);
}

// ─── STEP 3: SW Version Check ────────────────────────────────
on diagResponse Cluster.ReadDataByIdentifier {
  long did = diagGetParameter(reqRead, "dataIdentifier");

  if (did == 0xF189) {
    byte v0 = diagGetRespPrimitiveByte(this, "SWVersion[0]");
    byte v1 = diagGetRespPrimitiveByte(this, "SWVersion[1]");
    int  match = (v0 == EXPECTED_SW_VERSION[0] && v1 == EXPECTED_SW_VERSION[1]);
    logStep("SWVersionCheck", match,
            match ? "Version match" : "Version MISMATCH — check flash station");

    // Security access for write operations
    diagSetParameter(reqSeed, "securityAccessType", 0x01);
    diagSendRequest(reqSeed);
  }
}

// ─── STEP 4: Security Access ──────────────────────────────────
on diagResponse Cluster.SecurityAccess_Seed {
  dword seed = diagGetRespPrimitiveLong(this, "securitySeed");
  dword key  = seed ^ 0x5A3C9F1E;   // OEM key algorithm
  diagSetParameter(reqKey, "securityAccessType", 0x02);
  diagSetParameter(reqKey, "securityKey", key);
  diagSendRequest(reqKey);
}

on diagResponse Cluster.SecurityAccess_Key {
  int granted = (diagGetRespCode(this) == 0x67);
  logStep("SecurityAccess", granted, granted ? "Key accepted" : "Key REJECTED");

  if (granted) {
    // Trigger pixel test routine
    diagSetParameter(reqRoutine, "routineControlType", 0x01);
    diagSetParameter(reqRoutine, "routineIdentifier",  0x0203);
    diagSendRequest(reqRoutine);
  } else {
    eolComplete();
  }
}

// ─── STEP 5: Pixel Test ───────────────────────────────────────
on diagResponse Cluster.RoutineControl {
  long rid = diagGetParameter(reqRoutine, "routineIdentifier");

  if (rid == 0x0203) {
    // Wait 500ms then read photometer
    float brightness = measurePhotometer();
    int brightPass = (brightness >= BRIGHTNESS_MIN && brightness <= BRIGHTNESS_MAX);
    logStep("BrightnessCheck", brightPass,
            "Measured: " + (string)(long)brightness + " cd/m²");

    if (!brightPass) calibrateBrightness(brightness);

    // Stop pixel test
    diagSetParameter(reqRoutine, "routineControlType", 0x02);
    diagSetParameter(reqRoutine, "routineIdentifier",  0x0203);
    diagSendRequest(reqRoutine);
  }

  if (rid == 0x0204) {
    logStep("GaugeSweep", (diagGetRespCode(this) == 0x71), "Needle sweep completed");

    // Check DTCs
    diagSetParameter(reqDTC, "subfunction",   0x02);
    diagSetParameter(reqDTC, "DTCStatusMask", 0x08);
    diagSendRequest(reqDTC);
  }
}

// ─── STEP 6: DTC Check ────────────────────────────────────────
on diagResponse Cluster.ReadDTCInfo {
  long dtcCount = diagGetRespArraySize(this, "DTCAndStatusRecord");
  logStep("DTCCheck", (dtcCount == 0),
          dtcCount == 0 ? "Zero confirmed DTCs" :
          (string)dtcCount + " confirmed DTC(s) found — INVESTIGATE");

  // Final reset
  diagSetParameter(reqReset, "resetType", 0x01);
  diagSendRequest(reqReset);
}

// ─── STEP 7: Reset & Final Boot Check ─────────────────────────
on diagResponse Cluster.ECUReset {
  testWaitForTimeout(3000);   // wait for ECU to reboot
  diagSetParameter(reqSession, "DiagnosticSessionType", 0x01);
  diagSendRequest(reqSession);
}

// Final boot check handled in DiagnosticSessionControl response
// when gStepNum > 5 → it's the post-reset check

void eolComplete() {
  write("==============================");
  write("EOL TEST COMPLETE — Unit: %s", gUnitSerial);
  write("Steps: %d   Pass: %d   Fail: %d",
        gStepNum, gPassCount, gFailCount);
  write("RESULT: %s", gFailCount == 0 ? "PASS — SHIP" : "FAIL — REPAIR QUEUE");
  write("==============================");
  stop();
}

float measurePhotometer() {
  // Interface to photometer hardware — returns cd/m²
  // In real EOL: reads from instrument via GPIB, USB, or RS232
  return 398.0;   // placeholder
}

void calibrateBrightness(float measured) {
  // Calculate and write PWM correction
  word pwmCorr = (word)(2000.0 * (400.0 / measured));
  write("Calibrating brightness: measured=%.0f, PWM correction=%d", measured, pwmCorr);
  diagSetParameter(reqWrite, "dataIdentifier", 0xF250);
  diagSetParameter(reqWrite, "BacklightPWM",   pwmCorr);
  diagSendRequest(reqWrite);
}
```

---

## PART 3 — Diagnostic Architecture (How It All Connects)

---

### Physical Layer: How Tester Reaches the ECU

```
OBD-II port (under dashboard)
       │
       │  ISO 15031-3 (physical connector, 16-pin)
       │  Pin 6: CAN High  │  Pin 14: CAN Low
       │
       ▼
Central Gateway ECU (GW)
  Routes UDS requests to the correct CAN bus
       │
       ├── HS-CAN1 (Powertrain) → ECM, TCM
       ├── HS-CAN2 (Chassis)    → ABS, EPS, ESP
       ├── HS-CAN3 (Body)       → Cluster, BCM, HVAC
       └── LIN bus              → Seats, mirrors, simple actuators
```

**For cluster diagnostics:**
Tester → OBD port → CAN1 → Gateway → CAN3 → Cluster

If Gateway routing table is missing the cluster address → `No Response` from cluster.

---

### ISO TP (Transport Protocol) — ISO 15765

CAN frames are only 8 bytes. Long UDS messages (e.g. VIN = 17 bytes) need multi-frame transport.

| Frame Type | When Used |
|-----------|-----------|
| **Single Frame (SF)** | UDS message ≤ 7 bytes |
| **First Frame (FF)** | Start of long message (> 7 bytes) |
| **Consecutive Frame (CF)** | Continuation bytes |
| **Flow Control (FC)** | Receiver tells sender: "send more / wait" |

```
Example: Reading VIN (20 bytes response)

ECU sends First Frame:    10 14 62 F1 90 57 56 31   (length=20, first 5 bytes of VIN)
Tester sends Flow Control: 30 00 00                 (go ahead, send all)
ECU sends Consecutive:    21 4A 41 31 55 44 4A 42   (next 7 bytes)
ECU sends Consecutive:    22 46 37 55 35 35 35 33   (next 7 bytes)
ECU sends Consecutive:    23 32 00 00 00 00 00 00   (last byte + padding)
```

---

### DTC Lifecycle (Must Know for Any Automotive Interview)

```
                           ┌─────────────────────────────────────┐
                           │           DTC LIFECYCLE             │
                           └─────────────────────────────────────┘

Fault condition true (1st drive cycle)
         │
         ▼
   ┌─────────────┐
   │   PENDING   │  Status bit 2 = 1
   │  (1 cycle)  │  Not yet confirmed / logged / lamp ON
   └──────┬──────┘
          │
          │ Fault present again in 2nd drive cycle
          │ (for most DTCs — some are immediate)
          ▼
   ┌─────────────┐
   │  CONFIRMED  │  Status bit 3 = 1  │  MIL / warning lamp ON
   │             │  Freeze frame captured
   └──────┬──────┘
          │
          │ 0x14 DTC Clear command (scan tool)
          │  ─ OR ─
          │ Fault heals for 3 consecutive drive cycles
          ▼
   ┌─────────────┐
   │   HEALED /  │  Fault not active, lamp OFF
   │   CLEARED   │  DTC removed from active list
   └─────────────┘
          │
          │ Fault returns → cycle starts again
          ▼
   (back to PENDING)
```

**Key interview points:**
- Clearing DTCs (`0x14`) does NOT fix the problem — if fault is still present, DTC comes back
- MIL does not go off immediately after clear — needs 1–3 passing drive cycles (OBD-II regulation)
- Freeze frame captures vehicle conditions **at the moment DTC was confirmed** — speed, RPM, coolant temp

---

## PART 4 — Quick Reference Cards

---

### UDS Service Summary Card

```
0x10  Session Control     → Switch to Default / Programming / Extended
0x11  ECU Reset           → Hard / Key Off On / Soft reset
0x14  Clear DTC           → Clear all or group of DTCs
0x19  Read DTC Info       → Read fault codes, freeze frames, extended data
0x22  Read Data by ID     → Read any data (VIN, version, live signals, NVM)
0x27  Security Access     → Unlock write/flash access with seed/key
0x2E  Write Data by ID    → Write variant codes, calibration data
0x2F  IO Control          → Force actuators (e.g. turn on MIL for test)
0x31  Routine Control     → Execute tests (pixel test, gauge sweep, self-test)
0x34  Request Download     → Begin ECU flash programming
0x36  Transfer Data        → Transfer flash data blocks
0x37  Transfer Exit        → End programming transfer
0x3E  Tester Present       → Keep session alive (send every 2 seconds)
0x85  Control DTC Setting  → Enable or disable DTC logging
```

---

### NRC Quick Reference Card

```
0x10  generalReject                 — not sure why, rejected
0x11  serviceNotSupported           — ECU doesn't know this service
0x12  subFunctionNotSupported       — sub-function code not valid
0x13  incorrectMessageLength        — wrong number of bytes
0x22  conditionsNotCorrect          — wrong state (e.g. engine running)
0x24  requestSequenceError          — steps out of order
0x31  requestOutOfRange             — DID or routine ID doesn't exist
0x33  securityAccessDenied          — need to do 0x27 first
0x35  invalidKey                    — wrong key sent
0x36  exceededNumberOfAttempts      — locked out (wait 10 min)
0x78  requestCorrectlyReceivedResponsePending  — wait, I'm busy
```

---

### EOL Checklist for Cluster

```
□  Communication check (0x10 03 → 50 03)
□  SW version verified (0x22 F189)
□  Variant coding written (0x2E)
□  Pixel test PASS (0x31 + photometer)
□  Brightness within spec (350–450 cd/m²)
□  Gauge needle sweep (0x31 → needles sweep and return)
□  All warning telltales illuminate on command
□  Backlight calibration written to NVM if needed
□  Zero confirmed DTCs (0x19 02 08 → count = 0)
□  ECU resets cleanly (0x11 01 → boots within 3s)
□  Serial number / production date written to NVM (0x2E)
□  OVERALL: PASS or FAIL recorded against unit serial
```

---

*File: 11_eol_uds_diagnostics_guide.md | Cluster Validation Interview Prep | April 2026*
