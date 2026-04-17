# Automotive Bug Management — Complete Reference Guide

> **Scope**: ADAS · Infotainment · Instrument Cluster · Telematics (TCU)
> **Topics**: Bug Reproduction · Approaches · Reporting · Resolving · Diagnostics · Recurring Bugs
> **Audience**: Test Engineers · Test Leads · QA Managers · Developers

---

## Folder Structure

| File | Domain | Topics Covered |
|------|--------|----------------|
| [01_adas_bugs.md](01_adas_bugs.md) | ADAS | False detection, missed detection, sensor faults, calibration errors, fusion bugs, intermittent ADAS failures |
| [02_infotainment_bugs.md](02_infotainment_bugs.md) | Infotainment | Android crashes, BT/AA/CarPlay bugs, media bugs, boot failures, recurring HMI issues |
| [03_cluster_bugs.md](03_cluster_bugs.md) | Cluster | Speed errors, tell-tale bugs, CAN signal issues, display faults, recurring cluster issues |
| [04_telematics_bugs.md](04_telematics_bugs.md) | Telematics | eCall failures, OTA bugs, cellular drop, GPS issues, recurring TCU faults |
| [05_recurring_intermittent_bugs.md](05_recurring_intermittent_bugs.md) | Cross-domain | Bugs that disappear and reappear — detection, reproduction, logging strategies, permanent fixes |

---

## Bug Lifecycle (Universal Across All Domains)

```
DISCOVERY
    ↓
REPRODUCTION (critical step — cannot report what you cannot reproduce)
    ↓
ISOLATION (narrow down to exact condition / component / signal)
    ↓
DOCUMENTATION (defect report with all evidence)
    ↓
TRIAGE (severity, priority, owner assignment)
    ↓
ROOT CAUSE ANALYSIS
    ↓
FIX + UNIT TEST (developer)
    ↓
RETEST (tester — independent from reporter when possible)
    ↓
REGRESSION CHECK (did fix break anything else?)
    ↓
CLOSE (with evidence: test result, build reference, log)
    ↓
PREVENT RECURRENCE (add to regression suite, update checklist)
```

---

## Bug Severity Reference

| Severity | Definition | Examples |
|---------|-----------|---------|
| **P1 — Critical** | Safety risk, total feature failure, production blocker | AEB false braking, eCall not triggering, ECU brick |
| **P2 — High** | Major feature broken, no workaround | Speedometer wrong, navigation crash, BT audio dropout |
| **P3 — Medium** | Feature partially working, workaround exists | Tell-tale delayed, GPS drift, AA disconnects after 2h |
| **P4 — Low** | Cosmetic, minor UX, non-functional | UI alignment off by 2px, font color mismatch |

---

## Tools Reference

| Tool | Purpose |
|------|---------|
| **CANoe / CANalyzer** | CAN/LIN/Eth signal tracing, CAPL automation |
| **Wireshark** | Ethernet, DoIP, SOME/IP packet analysis |
| **ADB (Android Debug Bridge)** | Android infotainment logs, crash dumps |
| **ETAS INCA** | ECU calibration, measurement, flash |
| **dSPACE ControlDesk** | HIL signal injection, vehicle model |
| **Lauterbach Trace32** | JTAG debugging, CPU profiling, stack trace |
| **JIRA / HP ALM** | Defect tracking, test case management |
| **Eclipse MAT** | Java heap dump analysis (memory leaks) |
| **Oscilloscope** | Physical layer: CAN bus, power, wakeup signals |
| **Vector VN1630A/VN7640** | CAN/LIN/Ethernet hardware interface to PC |

---

*All scenarios in this guide are based on real-world automotive project experience.*
