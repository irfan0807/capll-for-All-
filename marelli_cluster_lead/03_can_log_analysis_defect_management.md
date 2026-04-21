# CAN Log Analysis, Root-Cause Investigation & Defect Management

> **Role:** Cluster Lead — Marelli / LTTS Bangalore
> **Focus:** Trace analysis workflows, root-cause methodology, defect lifecycle,
>            tools (CANoe, Jira/Mantis/ALM), OEM reporting standards

---

## 1. CAN Log Analysis Workflow

### 1.1 Log File Types in CANoe/CANalyzer

| Format | Extension | Notes |
|---|---|---|
| Vector Binary Log | `.blf` | Timestamped binary — primary format. Very fast read/write. |
| ASCII Log | `.asc` | Human-readable, larger file size. Useful for grep/Python parsing. |
| MF4 (ASAM) | `.mf4` | Modern measurement format — supports all channels |
| Trace database | `.csv` | Exported from trace for Excel/Python analysis |
| Vector vMeas | `.vmes` | Measurement data with variable groups |

### 1.2 Systematic Trace Analysis Approach

```
STEP 1 — SCOPE
  Define the time window:
  - Note test start (KL15 ON) and test end timestamps
  - Narrow to ±2 seconds around the failure event

STEP 2 — FILTER
  Filter to relevant messages only:
  - E.g., Filter = 0x3B3 (Speed) + 0x316 (Engine) + 0x3A5 (ABS)
  - Remove heartbeat/keep-alive messages that clutter trace

STEP 3 — SIGNAL PLOT
  Use CANoe/CANalyzer Graphics window:
  - Plot VehicleSpeed, ABS_Fault, FuelLevel vs time
  - Look for: signal drop, unexpected spikes, missing cycles

STEP 4 — TIMING CHECK
  - Measure message cycle time: should be 10ms for speed, 100ms for fuel
  - A 200ms gap in a 10ms message = timeout (ECU or bus fault)
  - Use Bus Statistics panel: check load%, error rate, CRC errors

STEP 5 — CORRELATION
  - Correlate multiple signals: does ABS_Fault = 1 match ABS_Active = 0 at same time?
  - Cross-reference BCM ignition state with cluster behaviour
  - Timeline: when did signal arrive vs when did display change? Measure delta.

STEP 6 — ISOLATE
  - Does fault occur at the sender (source ECU not transmitting)?
  - Or at the receiver (cluster not processing signal correctly)?
  - Swap DBC signal decode — is the bit position correct?

STEP 7 — DOCUMENT
  - Capture screenshot with annotations in CANoe
  - Export filtered log as .asc for defect attachment
  - Note: timestamp, signal value, expected vs actual
```

---

## 2. Root-Cause Investigation — Framework

### 2.1 The 5-Why Method for Cluster Defects

```
DEFECT: Fuel gauge needle stuck at 'E' even when fuel level signal shows 80%

Why 1: Needle is not moving despite correct signal?
  → Cluster is not updating gauge from the received signal.

Why 2: Why is the cluster not updating?
  → Signal value 80 (raw) decoded with wrong factor.

Why 3: Why wrong factor?
  → DBC file used in CANoe has FuelLevel scaling: factor=1, offset=0
    Cluster firmware uses: factor=0.5, offset=0 (old version loaded in ECU)

Why 4: Why was old DBC loaded in ECU?
  → Software delivery received from ECU team was not tagged correctly.
    CI/CD release included an older .hex that was not rebuilt after DBC update.

Why 5: Why not caught in review?
  → DBC version not tracked in release checklist. No automated check.

ROOT CAUSE: Configuration management gap — DBC version not validated in CI/CD.
CORRECTIVE ACTION: Add DBC SHA-256 hash comparison step in build pipeline.
```

### 2.2 Fishbone (Ishikawa) for Cluster Defects

```
                   DEFECT: MIL does not extinguish after fault cleared
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
      SOFTWARE             SIGNAL/CAN           HARDWARE
    ─────────            ──────────           ──────────
  Latch logic bug      Signal not cleared    Backlight circuit
  Wrong DTC clear      DTC active in ECU     Fuse blown
  State machine fault  DBC decode error      Display damage
         │                    │                    │
      PROCESS              CONFIG               TOOLING
    ─────────            ──────────           ──────────
  Missing test case    Wrong variant loaded  Stale CANoe DBC
  Incomplete SRS       EOL not complete      Logger time drift
```

### 2.3 Root Cause Categories for Cluster

| Category | Example Root Cause |
|---|---|
| Signal issue | Signal scaling mismatch between DBC and cluster SW |
| Timing issue | Cluster debounce too long — doesn't react to 50ms fault pulse |
| DBC mismatch | Signal bit position wrong in DBC — adjacent signal decoded instead |
| SW bug | Cluster firmware state machine has stuck state |
| Configuration | Wrong software variant loaded for this vehicle region |
| Test environment | CAN interface not terminating bus correctly — 60Ω instead of 60Ω each end |
| NVM issue | Factory EOL not run — factory defaults persisted |

---

## 3. CAN Log Analysis with Python

```python
"""
can_log_analyzer.py
Parse a .asc log file and detect CAN timeout for VehicleSpeed 0x3B3
"""

import re
from collections import defaultdict

LOG_FILE     = "cluster_test_run.asc"
TARGET_ID    = 0x3B3           # VehicleSpeed message
TIMEOUT_MS   = 200.0           # Expected max cycle: 200ms before timeout alarm
CYCLE_EXPECT = 10.0            # Expected cycle: 10ms

def parse_asc_log(filepath: str) -> list:
    """Parse Vector .asc file and return message list"""
    messages = []
    pattern  = re.compile(
        r"(\d+\.\d+)\s+(\d+)\s+([0-9A-Fa-f]+)\s+[RT]\s+d\s+\d+\s+([\w\s]+)"
    )
    with open(filepath, "r") as f:
        for line in f:
            m = pattern.match(line.strip())
            if m:
                messages.append({
                    "ts_ms"    : float(m.group(1)) * 1000.0,
                    "channel"  : int(m.group(2)),
                    "msg_id"   : int(m.group(3), 16),
                    "data_hex" : m.group(4).split()
                })
    return messages

def check_cycle_time_and_timeouts(messages: list, target_id: int,
                                  timeout_ms: float) -> dict:
    """Find gaps in message cycle time and report timeouts"""
    results = {"gaps": [], "min_cycle": float("inf"), "max_cycle": 0.0}
    last_ts  = None

    for msg in messages:
        if msg["msg_id"] != target_id:
            continue
        if last_ts is not None:
            delta = msg["ts_ms"] - last_ts
            results["min_cycle"] = min(results["min_cycle"], delta)
            results["max_cycle"] = max(results["max_cycle"], delta)
            if delta > timeout_ms:
                results["gaps"].append({
                    "start_ms" : last_ts,
                    "end_ms"   : msg["ts_ms"],
                    "gap_ms"   : delta
                })
        last_ts = msg["ts_ms"]
    return results

def decode_vehicle_speed(data_hex: list) -> float:
    """Decode VehicleSpeed: bytes [0:2], factor 0.01 km/h"""
    raw = (int(data_hex[1], 16) << 8) | int(data_hex[0], 16)
    return raw * 0.01

def analyze_speed_signal(messages: list):
    """Extract speed values and detect anomalies"""
    print(f"\n{'Timestamp_ms':>14} | {'Speed_kmh':>10} | {'Flag':>10}")
    print("-" * 40)
    for msg in messages:
        if msg["msg_id"] != TARGET_ID:
            continue
        speed = decode_vehicle_speed(msg["data_hex"])
        flag  = "SPIKE" if speed > 300.0 else ""
        print(f"{msg['ts_ms']:>14.1f} | {speed:>10.2f} | {flag:>10}")

def main():
    messages = parse_asc_log(LOG_FILE)
    print(f"Total messages parsed: {len(messages)}")

    results = check_cycle_time_and_timeouts(messages, TARGET_ID, TIMEOUT_MS)
    print(f"\n=== Cycle Analysis: 0x{TARGET_ID:X} (VehicleSpeed) ===")
    print(f"  Min cycle: {results['min_cycle']:.1f} ms")
    print(f"  Max cycle: {results['max_cycle']:.1f} ms")
    print(f"  Timeouts (>{TIMEOUT_MS}ms): {len(results['gaps'])}")
    for gap in results["gaps"]:
        print(f"    GAP: {gap['start_ms']:.1f} → {gap['end_ms']:.1f} ms "
              f"= {gap['gap_ms']:.1f} ms")

    analyze_speed_signal(messages)

if __name__ == "__main__":
    main()
```

---

## 4. Defect Management — Full Lifecycle

### 4.1 Defect Attributes (LTTS / OEM Reporting)

| Field | Description | Example |
|---|---|---|
| Defect ID | Unique identifier | CLU-1024 |
| Title | Clear one-line summary | `[IC][Speed] Speedometer reads 5 km/h high at 60 km/h input` |
| Severity | Impact on functionality | Critical / Major / Minor / Cosmetic |
| Priority | Fix urgency | P1 / P2 / P3 |
| Component | Subsystem | Cluster SW / Cluster HW / CAN DBC / Test Env |
| Status | Current state | New → Open → In-Analysis → Fixed → Verify → Closed |
| Found in build | Software baseline | IC_SW_v1.4.2_Build234 |
| Fixed in build | Resolution baseline | IC_SW_v1.4.3_Build246 |
| Test case | Linked test | TC_SPD_001_Accuracy_60kph |
| Root cause | Technical cause | DBC signal offset wrong in cluster variant B |
| Attachments | Evidence | CAN log .blf, screenshot, trace screenshot |
| OEM visibility | Customer-facing? | Yes / No |

### 4.2 Defect Severity Definition (Cluster Context)

| Severity | Definition | Example |
|---|---|---|
| Critical (S1) | Safety hazard or vehicle cannot operate | Speedometer reads 0 at 120 km/h, MIL not showing active engine fault |
| Major (S2) | Feature completely broken, no workaround | Odometer not incrementing, ABS telltale never activates |
| Minor (S3) | Feature partially wrong, workaround exists | Fuel gauge 5% off at half tank, trip meter resets 1km late |
| Cosmetic (S4) | Visual/UX issue, no functional impact | Backlight flickers once at startup, icon misaligned 2px |

### 4.3 Writing a Good Defect Report

```
DEFECT REPORT TEMPLATE
======================
Title: [IC][Telltale][ABS] ABS Fault telltale does not activate on ABS_Fault=1

Environment:
  - HW: Cluster bench A3, SW baseline IC_SW_v1.5.0_Build312
  - CANoe version: 16.0 SP4
  - DBC: Powertrain_v2.3.dbc

Steps to Reproduce:
  1. Set KL15 ON — wait for bulb check to complete
  2. Inject CAN message 0x3A5 with ABS_Fault bit = 1 (byte 0, bit 3)
  3. Observe cluster telltale area (top row, 4th from left)

Expected Result:
  ABS telltale (amber, triangle with ABS text) illuminates within 200ms
  per SRS requirement IC_REQ_0042 Rev C.

Actual Result:
  ABS telltale remains OFF. No change observed after 5 seconds.
  CAN trace shows message 0x3A5 transmitted correctly with ABS_Fault = 1.

Attachments:
  - cluster_abs_fail_20260421.blf (CAN log 10 seconds)
  - screenshot_abs_not_active.png
  - abs_trace.asc (filtered)

Root Cause (Initial Hypothesis):
  Possible DBC mismatch — ABS_Fault bit position may differ between
  test DBC and cluster ECU SW.

Severity: Major (S2)
Priority: P1 — Blocking ASIL B validation gate
```

### 4.4 Defect State Transitions

```
New
 └→ Open (assigned to SW/HW team)
     ├→ In-Analysis (team actively investigating)
     │   ├→ Cannot Reproduce (needs more info → back to Open)
     │   ├→ Not-a-Bug (as-per-design → WAD/Closed)
     │   └→ Fixed (fix implemented in new build)
     │       └→ Verify (tester re-runs TC on fixed build)
     │           ├→ Verified-Pass → Closed
     │           └→ Reopen (fix incomplete → back to Open)
     └→ Deferred (post release, low severity)
```

---

## 5. Defect Tools — Quick Reference

### 5.1 Jira (most common at LTTS)

```
Key operations for Cluster Lead:

1. Create defect:
   - Project: Cluster_IC
   - Issue Type: Bug
   - Priority: P1/P2/P3
   - Labels: [CAN] [CAPL] [Telltale] [Gauge] [NVM]
   - Link to Test Case in Xray/Zephyr plugin

2. Bulk triage:
   - Filter: Project=Cluster_IC AND Status=New AND Priority>=P2
   - Assign to engineers by component

3. Metrics dashboard:
   - Defect Open vs Closed chart
   - Severity distribution
   - Average resolution time per engineer
   - First-pass yield (defects found by team before OEM sees them)

4. Weekly status report from Jira:
   - Opened this week: X, Closed: Y, Open P1: Z
```

### 5.2 HP ALM / Micro Focus ALM (OEM-typical)

```
Used by OEMs like FCA, Renault (Marelli OEM partners):

Defect Module:
  - Created under test run → auto-linked to test case
  - Approval workflow: Engineer → Lead → OEM → Close

Test Execution Module:
  - Test sets map to test cycles (Sprint/Release)
  - Execution results: Passed / Failed / Blocked / N/A

Reports:
  - Test Execution Progress Report (auto from ALM)
  - Defect Aging Report (defects open > 14 days)
```

---

## 6. OEM Reporting & Communication

### 6.1 Weekly Status Report Template

```
PROJECT: Marelli IC Validation — Platform X
WEEK: WK17 2026 | Reporting Lead: [Your Name]

OVERALL STATUS: 🟡 AMBER (2 open P1 defects blocking ABS validation gate)

TEST EXECUTION:
  Total TCs: 320 | Executed: 280 (87.5%) | Passed: 261 | Failed: 15 | Blocked: 4

DEFECTS:
  Total Open: 19 | P1: 2 | P2: 9 | P3: 8
  New this week: 7 | Closed this week: 5
  Oldest open: CLU-1001 (18 days, awaiting SW fix from ECM team)

TOP RISKS:
  1. CLU-1024: ABS telltale not activating (P1, ASIL B gate) → SW fix ETA: WK18
  2. CLU-1031: Odometer NVM rollback on cold crank (P1) → Root cause in progress

COMPLETED THIS WEEK:
  ✓ Speedometer validation (TC_SPD_001 to TC_SPD_012): All Passed
  ✓ Fuel gauge sweep test: 11/12 Passed, 1 Minor defect (CLU-1041)
  ✓ Power mode sequence test: All 8 TCs Passed

PLAN NEXT WEEK:
  → Execute telltale matrix: TC_TEL_001 to TC_TEL_030
  → Retest CLU-1024 on new SW build v1.5.1
  → CAN timeout battery test (TC_CTO_001 to TC_CTO_015)
```

---

*File: 03_can_log_analysis_defect_management.md | marelli_cluster_lead series*
