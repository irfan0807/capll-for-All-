# Recurring Bugs — Cross-Domain Diagnostics, Tracking & Prevention

> **Domain**: All (ADAS · Infotainment · Cluster · Telematics)
> **Purpose**: Framework for identifying, tracking, investigating, and permanently eliminating bugs that reappear after they were previously declared "Fixed"
> **Tools**: JIRA · CANoe · ADB · Python · CI/CD Gate Scripts · Test Management (HP ALM / TestRail)

---

## 1. What Is a Recurring Bug?

A **recurring bug** is a defect that:
1. Was reported, investigated, and marked **Resolved/Fixed** in JIRA
2. Reappears in a later software version — either identical symptom or closely related
3. Forces a SECOND investigation cycle, wasting engineering time and introducing risk

### Why Do Bugs Recur?

| Root Cause of Recurrence | Description | Example |
|--------------------------|-------------|---------|
| **Incomplete fix** | Symptom was masked, not root cause solved | Increasing retry count hid the timeout; hardware still fails |
| **Missing regression test** | No automated test added → next regression runs never catch it | Memory leak fixed but no long-soak test in CI |
| **Regression by new feature** | New SW feature re-activates same code path that was broken | New power-save mode restarts modem; breaks eCall config |
| **Config regression** | Calibration, DBC, or AT configuration reverted silently | Modem FW update resets AT+QCFG to factory defaults |
| **Different root cause, same symptom** | Different code defect presents identically to a prior bug | Speedometer 2× error: first time = DBC factor; second time = signal byte order |
| **Platform / variant divergence** | Fix applied to one HW variant, not ported to another | HW variant 0x03 never received the NVM fix applied to 0x01 |
| **Intermittent hardware** | HW works borderline — only fails under specific conditions | Bad solder joint on CAN transceiver; only fails at -30°C |

---

## 2. Recurring Bug Classification

### Classification Tag (add to all JIRA recurring bugs)
```
Labels: RECURRING_BUG
Custom Fields:
  - Recurrence Count: [1 / 2 / 3+]
  - Time Since Last Fix (weeks): [e.g., 12]
  - Recurrence Category: [Regression / Config / Platform / Intermittent-HW / Incomplete-Fix]
  - Linked JIRA Bug (previous occurrence): [JIRA-XXXX]
  - Regression Test Present: [Yes / No / Pending]
```

### Severity Escalation Rule
```
Recurrence Count = 1: Normal process
Recurrence Count = 2: Root cause review mandatory; fix requires 2nd engineer review
Recurrence Count = 3: Escalated to Technical Lead; CAPA (Corrective & Preventive Action) required
```

---

## 3. Domain-Specific Recurring Bug Patterns

### 3.1 ADAS — Recurring Bug Patterns

#### Common ADAS Recurring Triggers
| Trigger | Recurring Pattern | Detection Method |
|---------|-------------------|-----------------|
| Sensor calibration firmware update | Recalibrates object suppression filters → previous false-positive fix undone | Run false-positive test on every radar/camera FW update |
| New road type added to map database | Map-based speed context changes → AEB threshold miscalculated | Regression test on all road types |
| AUTOSAR RTE update | CAN signal access APIs change → signal reading off-by-one | Full ADAS signal integrity test after every RTE update |
| Fusion algorithm version upgrade | Sensor weighting changes → previously stable edge cases fail | Extended HIL test campaign on edge case library |

#### CAPL: ADAS Recurring Sensor Failure Pattern Detection
```capl
// Detect pattern: AEB activates but camera says no object (recurring false positive)
variables {
  int   aebBrakeCount;
  int   falsePositiveCount;
  timer tSessionEnd;
}

on start {
  aebBrakeCount    = 0;
  falsePositiveCount = 0;
  setTimer(tSessionEnd, 3600000);  // 1-hour session
}

on message 0x420 {  // AEB_BrakeRequest CAN message
  byte aebBrake = this.byte(0) & 0x01;
  if (aebBrake == 1) {
    aebBrakeCount++;
    // Check if camera also confirms object
    if (@Camera_ObjectValid == 0) {
      falsePositiveCount++;
      write("[RECURRING ADAS BUG CHECK] AEB#%d — Camera says NO OBJECT (false positive?)",
            aebBrakeCount);
      write("  Snapshot: Radar_Dist=%.1f  Radar_RCS=%.1f  Doppler=%.1f",
            @RadarObject_01_Distance, @RadarObject_01_RCS, @RadarObject_01_RelVelocity);
    }
  }
}

on timer tSessionEnd {
  write("=== Session Summary ===");
  write("AEB activations: %d  |  False positives (no camera object): %d",
        aebBrakeCount, falsePositiveCount);
  if (falsePositiveCount > 0) {
    write("WARNING: False positive ratio = %.1f%% — investigate recurring AEB bug",
          (float)falsePositiveCount / (float)aebBrakeCount * 100.0);
  }
}
```

---

### 3.2 Infotainment — Recurring Bug Patterns

#### Common Infotainment Recurring Triggers
| Trigger | Recurring Pattern | Detection |
|---------|------------------|-----------|
| Navigation app version update | Memory leak regression — tile eviction logic reverted | 60-min soak test with meminfo monitoring after every app update |
| Android security patch | BT coexistence config overwritten by OS update | BT A2DP soak test after every security patch |
| GMS / Google services update | Android Auto compatibility broken by new AA client version | AA connect + 30-min session test |
| Platform SDK update | ADB API changes → diagnostic tools stop working (not caught until field) | Smoke test: adb shell dumpsys after every SDK bump |

#### ADB Script: Automated Memory Growth Detector (CI Integration)
```bash
#!/bin/bash
# Recurring Bug Prevention: Memory soak test for Navigation app
# Run after every navigation app release

APP_PACKAGE="com.oem.navigation"
DURATION_SEC=3600    # 1 hour
SAMPLE_INTERVAL=300  # every 5 minutes
ALERT_THRESHOLD_MB=20  # alert if heap grows > 20 MB in 5 min

echo "Starting memory soak test for $APP_PACKAGE"
START_HEAP=$(adb shell dumpsys meminfo $APP_PACKAGE | grep "TOTAL:" | awk '{print $2}')
PREV_HEAP=$START_HEAP

for i in $(seq 1 $((DURATION_SEC / SAMPLE_INTERVAL))); do
    sleep $SAMPLE_INTERVAL
    
    CURR_HEAP=$(adb shell dumpsys meminfo $APP_PACKAGE | grep "TOTAL:" | awk '{print $2}')
    DELTA=$((CURR_HEAP - PREV_HEAP))
    TOTAL_GROWTH=$((CURR_HEAP - START_HEAP))
    
    echo "T=$((i * SAMPLE_INTERVAL))s: heap=${CURR_HEAP}KB, delta=${DELTA}KB, total_growth=${TOTAL_GROWTH}KB"
    
    if [ $DELTA -gt $((ALERT_THRESHOLD_MB * 1024)) ]; then
        echo "ERROR: MEMORY LEAK DETECTED — grew ${DELTA}KB in ${SAMPLE_INTERVAL}s"
        echo "FAIL: Recurring memory leak bug — check MapTileCache or similar"
        exit 1
    fi
    
    PREV_HEAP=$CURR_HEAP
done

echo "PASS: Memory stable over ${DURATION_SEC}s (total growth: ${TOTAL_GROWTH}KB)"
exit 0
```

---

### 3.3 Cluster — Recurring Bug Patterns

#### Common Cluster Recurring Triggers
| Trigger | Recurring Pattern | Detection |
|---------|------------------|-----------|
| DBC database update | Signal scaling regression (factor/offset) | Automated DBC diff on safety signals after every DBC update |
| NVM layout change in OTA | NVM CRC fail → boot hang (while(1)) | OTA regression: apply update on bench; verify boot success |
| New AUTOSAR SWC added | Component priority inversion → gauge render delayed | Full cluster boot + gauge sweep timing test |
| Variant configuration change | Wrong variant calibration active → thresholds wrong | EOL calibration verification test on every variant |

#### Python: DBC Signal Regression Checker (CI Gate)
```python
#!/usr/bin/env python3
"""
DBC Signal Regression Checker
Run in CI/CD pipeline after every DBC update.
Fails build if safety-critical signal attributes change unexpectedly.
"""

import re
import sys

SAFETY_SIGNALS = [
    "VehicleSpeed_kmh",
    "EngineRPM",
    "FuelLevel_L",
    "EngineTemp_C",
    "ABS_Active",
    "MIL_Request",
    "AirbagWarning",
]

def parse_dbc_signals(dbc_file):
    """Extract signal factor, offset, startBit for each signal."""
    signals = {}
    pattern = re.compile(
        r'SG_\s+(\w+)\s*:\s*(\d+)\|(\d+)@(\d+)([+-])\s*\(([0-9.eE+-]+),([0-9.eE+-]+)\)'
    )
    with open(dbc_file) as f:
        for line in f:
            m = pattern.search(line)
            if m:
                name = m.group(1)
                signals[name] = {
                    "startBit": int(m.group(2)),
                    "length":   int(m.group(3)),
                    "byteOrder": m.group(4),  # 1=little-endian, 0=big-endian
                    "signed":    m.group(5),
                    "factor":    float(m.group(6)),
                    "offset":    float(m.group(7)),
                }
    return signals

def check_regression(old_dbc, new_dbc):
    old_sigs = parse_dbc_signals(old_dbc)
    new_sigs = parse_dbc_signals(new_dbc)
    failures = []

    for sig in SAFETY_SIGNALS:
        if sig not in old_sigs or sig not in new_sigs:
            failures.append(f"MISSING signal '{sig}' in one of the DBC files")
            continue
        old = old_sigs[sig]
        new = new_sigs[sig]
        for attr in ["factor", "offset", "startBit", "length", "byteOrder"]:
            if old[attr] != new[attr]:
                failures.append(
                    f"SAFETY SIGNAL CHANGED: {sig}.{attr}: {old[attr]} → {new[attr]}"
                )

    return failures

if __name__ == "__main__":
    old_dbc, new_dbc = sys.argv[1], sys.argv[2]
    print(f"Checking DBC regression: {old_dbc} → {new_dbc}")
    failures = check_regression(old_dbc, new_dbc)
    if failures:
        print("\n[FAIL] DBC regression detected:")
        for f in failures:
            print(f"  ✗ {f}")
        print("\nBuild blocked: safety signal attribute change requires manual review.")
        sys.exit(1)
    else:
        print("[PASS] No safety signal regressions detected.")
        sys.exit(0)
```

---

### 3.4 Telematics — Recurring Bug Patterns

#### Common TCU Recurring Triggers
| Trigger | Recurring Pattern | Detection |
|---------|------------------|-----------|
| Modem firmware update | AT+QCFG settings reset → cellular dropout recurs | Post-modem-FW-update AT config verification script |
| OTA linker script change | FBL overwrite risk returns | Automated OTA address range check in CI |
| eCall regulation update (R144 amendment) | New MSD field required → missing data in MSD | R144 compliance test suite run on every eCall-related change |
| GNSS module firmware | HDOP APIs return different scale → position selection logic broken | eCall MSD position accuracy test |

#### Python: OTA Package Address Safety Checker (CI Gate)
```python
#!/usr/bin/env python3
"""
OTA Package Flash Address Validator
Prevents flash of OTA package that overlaps the bootloader region.
Run in CI before every OTA package release.
"""

import struct
import sys

# Memory map constants (adjust per platform):
FBL_START   = 0x08000000
FBL_END     = 0x0800FFFF   # Bootloader: 64 KB — NEVER overwrite

APP_START   = 0x08010000
APP_END     = 0x0807FFFF   # Application: 448 KB

def parse_ota_package(pkg_path):
    with open(pkg_path, 'rb') as f:
        header = f.read(64)
    start_addr = struct.unpack('>I', header[16:20])[0]
    end_addr   = struct.unpack('>I', header[20:24])[0]
    return start_addr, end_addr

def validate_ota(pkg_path):
    start, end = parse_ota_package(pkg_path)
    print(f"OTA package: {pkg_path}")
    print(f"  Target range: 0x{start:08X} – 0x{end:08X}")
    print(f"  FBL region:   0x{FBL_START:08X} – 0x{FBL_END:08X}  [PROTECTED]")
    print(f"  APP region:   0x{APP_START:08X} – 0x{APP_END:08X}  [VALID]")

    if start < APP_START:
        print(f"\n[CRITICAL FAIL] OTA target 0x{start:08X} is within FBL region!")
        print("This OTA package WILL BRICK the ECU. Release BLOCKED.")
        return False

    if end > APP_END:
        print(f"\n[FAIL] OTA end address 0x{end:08X} exceeds application region!")
        print("Address range error. Release BLOCKED.")
        return False

    print("\n[PASS] OTA address range is safe.")
    return True

if __name__ == "__main__":
    ok = validate_ota(sys.argv[1])
    sys.exit(0 if ok else 1)
```

---

## 4. Recurring Bug Investigation Workflow

### Step-by-Step Recurring Bug Response Protocol

```
Phase 1 — Detection (Day 0)
  □ Bug reported; tester marks as SUSPECTED_RECURRING in JIRA
  □ Search JIRA: component=X, label=RECURRING, summary~= (keyword)
  □ IF prior bug found: link new issue as "is a recurrence of JIRA-XXXX"
  □ Compare: same symptom + same component = Confirmed Recurring
  □ Assign Recurrence Count (increment from prior)

Phase 2 — Reproduction (Day 0–1)
  □ Reproduce using SAME reproduction procedure from the ORIGINAL JIRA issue
  □ If reproducible: confirm recurrence (same code path)
  □ If NOT reproducible same way: different root cause — treat as new bug

Phase 3 — Root Cause Analysis (Day 1–3)
  □ Pull git log for the original fix commit:
      git log --all --oneline -- <file_changed_in_fix>
  □ Verify fix commit is present in current build:
      grep -r "FixNote_JIRA_XXXX" src/ → if absent: fix not merged to this branch
  □ If fix is present: investigate NEW failure mode in same area
      (regression by different code change in same file)
  □ If fix is absent: cherry-pick fix commit to current branch

Phase 4 — Fix (Day 3–5)
  □ Implement root cause fix (not symptom workaround)
  □ Mandatory: add automated regression test BEFORE merging fix
  □ Fix must include: test case, test data, expected result, JIRA link in test name
  □ Second engineer review required for Recurrence Count ≥ 2

Phase 5 — Prevention (Day 5–7)
  □ Identify: what systemic gap allowed this to recur?
    - Missing test? → add to CI suite
    - Config reset risk? → add post-update config verification step
    - Linker script risk? → add address range CI gate
    - Manual DBC edit? → add DBC diff CI gate
  □ Document: update CAPA log with preventive action
  □ Review list: are any other signals / configs / modules at same risk?
    → Fix all similar issues proactively

Phase 6 — Retrospective (Monthly)
  □ Review all bugs with label=RECURRING in past 30 days
  □ Identify top 3 recurrence categories (regression / config / platform / etc.)
  □ Assign one action item per category to a named engineer
  □ Track CI gate coverage: what % of component changes are gated by automated tests?
```

---

## 5. Soak Test Library for Recurring Bug Prevention

The following test cases must run in CI for all new SW releases to prevent regression:

### Mandatory Soak Tests

| Domain | Test | Duration | Pass Criteria |
|--------|------|----------|--------------|
| ADAS | False-positive detection (metal bridge / overpass scenario) | HIL: 100 triggers | 0 false AEB activations |
| ADAS | FCW missing detection (real target at 30 m, closing) | HIL: 50 triggers | 100% FCW alert rate |
| Infotainment | Navigation memory soak | 60 min GPS replay | Heap growth ≤ 5 MB total |
| Infotainment | Android Auto connection stability | 60-min AA session | 0 disconnects |
| Infotainment | BT A2DP + Wi-Fi hotspot coexistence | 30 min simultaneous | 0 audio stutters |
| Cluster | Speed gauge accuracy | 5-point sweep (20–100 km/h) | ±1 km/h at each point |
| Cluster | Tell-tale flickering detection | 30 min CAN monitor | 0 unexpected flickering |
| Cluster | Boot time after OTA | Apply OTA; measure boot | Boot ≤ 8 s; all gauges visible |
| Telematics | eCall in GNSS-denied scenario | RF shield; crash trigger | eCall initiated ≤ 3 s |
| Telematics | Cellular dropout recovery | RSRP degradation profile | Reconnect ≤ 10 s |
| Telematics | OTA package address validation | CI gate script | No FBL overlap; fail build if overlap |

---

## 6. CAPA Log Template (Corrective & Preventive Action)

Use this template for every Recurrence Count ≥ 2 bug:

```
CAPA Reference: CAPA-[YEAR]-[NUMBER]
Linked JIRA: JIRA-XXXX (recurrence), JIRA-YYYY (original)
Component: [ADAS / Infotainment / Cluster / Telematics]
Recurrence Count: [2 / 3+]
Date: YYYY-MM-DD
Owner: [Engineer Name]

1. Problem Statement:
   [Symptom, when it occurs, frequency, impact]

2. Recurrence Root Cause:
   [WHY did the fix fail? Missing test / config reset / branch not patched / etc.]

3. Corrective Action (fix the current occurrence):
   □ Action: [What was done]
   □ Completed: [YYYY-MM-DD]
   □ Verified by: [Test case name + result]

4. Preventive Action (prevent future occurrences):
   □ Preventive item 1: [e.g., "Add memory soak test to CI gate"]
   □ Preventive item 2: [e.g., "Add DBC diff checker to pipeline"]
   □ Preventive item 3: [e.g., "Monthly recurring bug retrospective"]
   □ Target completion: [YYYY-MM-DD]
   □ Responsible: [Engineer/Team]

5. Effectiveness Check:
   □ Date to verify prevention is working: [YYYY-MM-DD + 90 days]
   □ Criteria: "This bug shall not recur in any release for 90 days"
   □ Checked by: [Test Lead]

6. Lessons Learned:
   [What broader lesson applies? What other components share same risk?]
```

---

## 7. Quick Diagnosis Flow — "Is This a Recurring Bug?"

```
                    Bug Reported
                         │
                         ▼
            Search JIRA: same component +
            same symptom keywords
                         │
              ┌──────────┴──────────┐
              │                     │
           Found               Not found
              │                     │
              ▼                     ▼
    Compare symptom           Treat as NEW bug
    + affected code           Standard process
              │
    ┌─────────┴─────────┐
    │                   │
  Same symptom?       Different symptom?
    │                   │
    ▼                   ▼
  Is fix commit       Different root cause
  in this build?      (same component, new bug)
    │                   → Link as "related to"
  ┌─┴──┐               → New investigation
  │    │
 YES   NO
  │    │
  ▼    ▼
New   Cherry-pick
root  fix commit
cause → re-test
analysis
  │
  ▼
Recurrence Count++
CAPA required if ≥ 2
```
