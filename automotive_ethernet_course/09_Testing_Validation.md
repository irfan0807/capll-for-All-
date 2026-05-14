# SECTION 9 — TESTING & VALIDATION METHODOLOGY
## Course: Automotive Ethernet Testing — Complete Industry Training

---

## 9.1 AUTOMOTIVE TEST STRATEGY

### V-Model — Testing at Each Level

```
AUTOMOTIVE V-MODEL WITH TEST ACTIVITIES:

DEVELOPMENT PHASES            VERIFICATION PHASES
─────────────────────────────────────────────────────────────────
System Requirements ◄──────────────────────── System Test
      │                                             │
      ▼                                             │
Software Requirements ◄────────────────── Integration Test
      │                                             │
      ▼                                             │
Software Architecture ◄──────────────── Module Test (SIT)
      │                                             │
      ▼                                             │
Software Design ◄──────────────────── Unit Test
      │                                             │
      └──────────────────────────────────────────►  │
                    IMPLEMENTATION                  │
                    (Coding in C/C++)               │
─────────────────────────────────────────────────────────────────
```

### Testing Hierarchy in Automotive Projects

```
TEST TYPES HIERARCHY:
┌──────────────────────────────────────────────────────────────┐
│  SMOKE TEST                                                  │
│  • First test after any SW/HW delivery                       │
│  • Verifies: ECU boots, Ethernet link up, CAN active        │
│  • Duration: 5-15 minutes                                    │
│  • Gate: MUST PASS before any further testing               │
├──────────────────────────────────────────────────────────────┤
│  SANITY TEST                                                 │
│  • Broad coverage of major features                          │
│  • Verifies: Core functions work end-to-end                 │
│  • Duration: 30-60 minutes                                   │
│  • Gate: MUST PASS before full regression                   │
├──────────────────────────────────────────────────────────────┤
│  REGRESSION TEST                                             │
│  • Re-runs all previously passing tests                      │
│  • Triggered by: Every code change, SW delivery             │
│  • Duration: 4-24 hours (automated overnight)               │
│  • Tools: Jenkins CI, Python pytest, CAPL                   │
├──────────────────────────────────────────────────────────────┤
│  INTEGRATION TEST                                            │
│  • Tests ECU with neighboring ECUs and bus                  │
│  • Validates SOME/IP service contracts between ECUs         │
│  • Environment: Network integration bench                   │
│  • Duration: 1-3 days per integration cycle                 │
├──────────────────────────────────────────────────────────────┤
│  SYSTEM TEST                                                 │
│  • Full vehicle-level feature validation                     │
│  • Tests complete feature from sensor to actuator           │
│  • Environment: HIL bench or real vehicle                   │
│  • Covers: Functional, Performance, Fault, Endurance        │
└──────────────────────────────────────────────────────────────┘
```

---

## 9.2 REQUIREMENT ANALYSIS — READING SPECIFICATIONS

### Types of Requirements in Automotive

```
REQUIREMENT TYPES:
┌─────────────────────────────────────────────────────────────────┐
│  SYSTEM REQUIREMENT (OEM Level)                                 │
│  Source: OEM (customer spec, e.g., Mercedes-Benz TL-spec)      │
│  Example: "The AEB system shall initiate emergency braking      │
│            within 100ms of TTC dropping below 0.8s"            │
│  Owner: System engineer                                         │
├─────────────────────────────────────────────────────────────────┤
│  SOFTWARE REQUIREMENT (Supplier Level)                          │
│  Source: Derived from system requirement                        │
│  Example: "The ADAS_Algorithm component shall publish           │
│            AEB_BrakeRequest SOME/IP event within 80ms           │
│            of receiving RadarObject with TTC < 0.8s"           │
│  Owner: Software architect / validation engineer               │
├─────────────────────────────────────────────────────────────────┤
│  COMPONENT REQUIREMENT (Module Level)                           │
│  Source: Derived from software requirement                      │
│  Example: "The SomeIpXf layer shall serialize                   │
│            AEB_BrakeRequest payload in 2 bytes,                 │
│            big-endian, within 5ms of API call"                  │
│  Owner: Module developer / integration tester                  │
└─────────────────────────────────────────────────────────────────┘
```

### Reading a Requirement for Test Design

```
EXAMPLE REQUIREMENT ANALYSIS:

REQUIREMENT ID: AEB-SW-042
TEXT: "The ADAS_FCW component shall generate a FCW_Trigger signal 
      within 100ms ± 10ms after TTC_Estimate drops below 2.0 
      seconds. This requirement applies under the following 
      conditions:
      - Ego vehicle speed > 30 km/h
      - Detected object type: vehicle or pedestrian
      - System mode: Normal (not degraded)"

TEST ENGINEER BREAKDOWN:
┌───────────────────────────────────────────────────────────────┐
│  WHAT to test: FCW_Trigger timing relative to TTC threshold   │
│  WHEN: After TTC drops below 2.0s                             │
│  HOW LONG: 90ms to 110ms (100ms ± 10ms)                      │
│  PRECONDITION 1: Ego speed > 30 km/h                          │
│  PRECONDITION 2: Object = vehicle or pedestrian               │
│  PRECONDITION 3: System mode = Normal                         │
│  NOT TESTED: Degraded mode (separate requirement)             │
└───────────────────────────────────────────────────────────────┘

TEST CASES DERIVED:
  TC-AEB-042-001: FCW timing — vehicle target, speed 50 km/h
  TC-AEB-042-002: FCW timing — pedestrian target, speed 35 km/h
  TC-AEB-042-003: No FCW at speed < 30 km/h (boundary)
  TC-AEB-042-004: No FCW in degraded mode (verify negative)
  TC-AEB-042-005: Boundary — ego speed exactly 30 km/h
```

---

## 9.3 TEST CASE DESIGN — COMPLETE METHODOLOGY

### Test Case Template

```
STANDARD AUTOMOTIVE TEST CASE FORMAT:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST CASE ID:    TC-ETH-022
TITLE:           SOME/IP Service Discovery — Offer Service Timeout
REQUIREMENT ID:  SD-REQ-007
PRIORITY:        HIGH
TESTED BY:       [Engineer Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OBJECTIVE:
  Verify that ADAS_ECU removes service from SD table and stops 
  subscribing when SOME/IP OfferService message is not received 
  within the configured TTL (3000ms).

PRECONDITIONS:
  1. ADAS_ECU powered on, Ethernet link active
  2. RADAR_ECU service discovery active and offering service 0x1234
  3. ADAS_ECU has subscribed to RADAR_ECU service
  4. CANoe measurement running with SOME/IP analysis

TEST STEPS:
  Step 1: Verify ADAS_ECU is subscribed (SD_SubscribeEventgroup seen)
  Step 2: Stop RADAR_ECU SOME/IP SD offering (disable SD in simulation)
  Step 3: Start timer (3000ms TTL countdown)
  Step 4: Monitor Ethernet for ADAS_ECU behavior

EXPECTED RESULTS:
  Step 1: Captured SubscribeEventgroup in Wireshark — PASS
  Step 2: OfferService messages stop appearing on Ethernet
  Step 3: Within 3000ms after last OfferService, ADAS_ECU shall:
          - Stop expecting RADAR data events
          - Log DTC: RADAR_SERVICE_TIMEOUT (if DTC configured)
          - Not crash or hang
  Step 4: When RADAR_ECU SD offer resumes, ADAS_ECU re-subscribes

PASS/FAIL CRITERIA:
  PASS if: Subscription timeout occurs within 3000ms ± 200ms
  FAIL if: ADAS_ECU still processes old RADAR events after timeout
  FAIL if: ADAS_ECU crashes or generates watchdog reset
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Equivalence Class Partitioning

```
TEST DESIGN TECHNIQUE: Equivalence Class Partitioning

EXAMPLE: ECU accepts DID 0x2000 = Speed Limit Setting (valid: 50-200)

Equivalence Classes:
  Class 1 (VALID):   50 ≤ value ≤ 200     → Test with: 50, 130, 200
  Class 2 (INVALID): value < 50            → Test with: 0, 10, 49
  Class 3 (INVALID): value > 200           → Test with: 201, 255, 65535

Boundary Value Analysis (within Class 1):
  Test 49  → INVALID (just below lower bound)
  Test 50  → VALID   (lower bound)
  Test 51  → VALID   (just above lower bound)
  Test 199 → VALID   (just below upper bound)
  Test 200 → VALID   (upper bound)
  Test 201 → INVALID (just above upper bound)

WHY: Bugs frequently occur at boundaries, not middle of range.
```

---

## 9.4 REQUIREMENT TRACEABILITY MATRIX (RTM)

### RTM Structure

```
REQUIREMENT TRACEABILITY MATRIX (RTM):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Req ID      │ Req Summary           │ TC ID        │ Result│ Cov%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AEB-SW-042  │ FCW trigger < 100ms   │ TC-AEB-042-001│ PASS  │ 20%
            │                       │ TC-AEB-042-002│ PASS  │ 40%
            │                       │ TC-AEB-042-003│ PASS  │ 60%
            │                       │ TC-AEB-042-004│ PASS  │ 80%
            │                       │ TC-AEB-042-005│ FAIL  │ 100%
            │                       │               │       │
ETH-SW-007  │ SOME/IP SD timeout    │ TC-ETH-022-001│ PASS  │ 50%
            │                       │ TC-ETH-022-002│ PASS  │ 100%
            │                       │               │       │
FLASH-SW-015│ Flash < 3 minutes     │ TC-FLASH-006  │ PASS  │ 100%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RTM RULES:
• Every requirement MUST have at least 1 test case
• Requirement with 0 test cases = untested = zero coverage
• ASPICE SWE.4 requires 100% requirement coverage
• Failed TCs block software delivery
```

---

## 9.5 ASPICE — AUTOMOTIVE SPICE BASICS

### ASPICE Process Areas

```
AUTOMOTIVE SPICE (ASPICE) — ISO/IEC 15504 adapted for automotive

RELEVANT PROCESS AREAS FOR VALIDATION ENGINEERS:
┌────────────────────────────────────────────────────────────────┐
│  SWE.1 — Software Requirements Analysis                        │
│  • Validate that requirements are clear, complete, consistent  │
│  • Generate review reports (inspection, walkthrough)           │
│  • Traceability: System Req → Software Req                    │
├────────────────────────────────────────────────────────────────┤
│  SWE.4 — Software Unit Verification (Unit Testing)             │
│  • Developer tests individual modules                          │
│  • Coverage: Statement, Branch, MC/DC coverage                │
│  • Tools: VectorCAST, Tessy                                   │
├────────────────────────────────────────────────────────────────┤
│  SWE.5 — Software Integration Testing                          │
│  • Integration of modules and components                       │
│  • Tests AUTOSAR SWC integration on virtual/real ECU          │
│  • RTM: Software Req → Integration Test Case                  │
├────────────────────────────────────────────────────────────────┤
│  SWE.6 — Software Qualification Testing                        │
│  • System-level validation (HIL, vehicle testing)             │
│  • Full feature validation against customer requirements       │
│  • RTM: System Req → System Test Case → Test Result           │
└────────────────────────────────────────────────────────────────┘

ASPICE CAPABILITY LEVELS:
Level 0: Incomplete (process not done)
Level 1: Performed (process works)
Level 2: Managed (planned, tracked, adjusted)
Level 3: Established (process documented, reused)
Target: OEM typically requires Level 2 minimum, Level 3 for safety
```

---

## 9.6 DEFECT LIFECYCLE & JIRA WORKFLOW

### Defect States

```
DEFECT LIFECYCLE IN AUTOMOTIVE PROJECTS:

       ┌─────────────────────────────────────────────────────┐
       │                                                     │
  NEW ─►─ OPEN ─►─ IN ANALYSIS ─►─ IN PROGRESS ─►─ FIXED ─►─ RETEST
   │         │                                        │          │
   │         └─► REJECTED (not a bug — by design)    │          ├─► PASS → CLOSED
   │         └─► DUPLICATE (already reported)         │          │
   │                                                  │          └─► FAIL → REOPENED
   └──────────────────────────────────────────────────►─ DEFERRED (fix next release)

JIRA TICKET FIELDS FOR AUTOMOTIVE BUGS:
  Summary:          [ADAS_ECU] FCW not triggered at TTC=1.9s in degraded mode
  Description:      Steps to reproduce: ...
  Severity:         Critical (S1) / Major (S2) / Minor (S3) / Cosmetic (S4)
  Priority:         P1 / P2 / P3 / P4
  Component:        Ethernet_Stack / SOME_IP / FCW_Algorithm / Diagnostics
  SW Version:       ADAS_SW_v2.3.0-RC4
  Found In:         HIL_Bench_Setup_3
  Assignee:         [Developer name]
  Linked Req:       AEB-SW-042
  Test Case:        TC-AEB-042-004
  Attachments:      wireshark.pcapng, hil_log.mf4, screenshot.png
```

### Real Bug Examples — Automotive Ethernet

```
BUG EXAMPLE 1:
  Summary: SOME/IP event subscription lost after 30 minutes
  Severity: Major (S2)
  Steps: Run HIL for 30+ minutes, monitor SOME/IP events
  Observed: At T=33 min, camera events stop arriving
  Root Cause: SOME/IP subscription TTL = 2000ms,
              SubscribeEventgroupAck not resent by server,
              client subscription expired
  Fix: Set server TTL to 0xFFFFFF (infinite) or fix SD cyclic offer
  Verification: Run 8h soak test, verify events continuous

BUG EXAMPLE 2:
  Summary: DoIP routing activation fails intermittently
  Severity: Critical (S1) — blocks diagnostics
  Steps: Power cycle ECU, immediately connect DoIP, activate routing
  Observed: 20% failure rate — NRC 0x76 (requestOutOfRange)
  Root Cause: Race condition — ECU accepts TCP connection before
              Ethernet stack fully initialized (150ms gap)
  Fix: Add 200ms startup delay before enabling DoIP server socket
  Verification: 100 power cycle tests, 0 failures

BUG EXAMPLE 3:
  Summary: AEB not triggered when RADAR reports 0.7s TTC
  Severity: Critical (S1) — safety bug!
  Steps: CarMaker scenario with sudden cut-in at close range
  Observed: FCW triggered at 1.9s TTC, but AEB never fires
  Root Cause: SOME/IP AEB_BrakeRequest DID schema mismatch
              — RADAR sends float32, ADAS expects uint16
              Serialization deserialization error → NaN in algorithm
  Fix: Align SOME/IP data types between RADAR ECU and ADAS ECU
  Verification: All 50 AEB test scenarios, timing measured
```

---

## 9.7 ISO 26262 — FUNCTIONAL SAFETY BASICS

### Safety Levels

```
ISO 26262 AUTOMOTIVE SAFETY INTEGRITY LEVELS (ASIL):

ASIL D (Highest):
  • Probability of failure < 10⁻⁸ per hour
  • Example: AEB, EPS (Electric Power Steering), Airbag
  • Test requirement: Extensive, MC/DC coverage ≥ 100%
  • Review: Formal inspections required

ASIL C:
  • Example: FCW, ACC (Adaptive Cruise Control)
  • MC/DC coverage ≥ 100% for safety functions

ASIL B:
  • Example: Lane Departure Warning
  • Branch coverage ≥ 100%

ASIL A (Lowest):
  • Example: Park assist feature
  • Statement coverage ≥ 100%

QM (Quality Management — not safety-relevant):
  • Infotainment, climate control
  • Normal software quality processes

DECOMPOSITION EXAMPLE:
  ASIL D → can split into ASIL B + ASIL B (with independence requirement)
  Used when one processor cannot meet ASIL D alone
```

### Safety Testing Requirements

```
ISO 26262 TESTING ACTIVITIES FOR ASIL B/C/D:
┌────────────────────────────────────────────────────────────────┐
│  Test Type        │ ASIL A │ ASIL B │ ASIL C │ ASIL D        │
├───────────────────┼────────┼────────┼────────┼───────────────┤
│ Specification-    │ M      │ HR     │ HR     │ HR            │
│  based testing    │        │        │        │               │
│ Equivalence class │ HR     │ HR     │ HR     │ HR            │
│ Boundary analysis │ HR     │ HR     │ HR     │ HR            │
│ Error guessing    │ R      │ R      │ R      │ R             │
│ Structural        │ Stmt   │ Branch │ MC/DC  │ MC/DC         │
│  coverage target  │ 100%   │ 100%   │ 100%   │ 100%          │
│ Back-to-back test │ -      │ R      │ HR     │ HR            │
│  (MIL vs SIL)    │        │        │        │               │
└────────────────────────────────────────────────────────────────┘
M = Mandatory, HR = Highly Recommended, R = Recommended
```

---

## 9.8 TEST AUTOMATION FRAMEWORK

### Python pytest Framework for Automotive

```python
# conftest.py — shared fixtures for automotive validation
import pytest
import socket
import time
from doip_client import DoIPClient  # custom module

@pytest.fixture(scope="session")
def doip_connection():
    """Establish DoIP connection once per test session."""
    client = DoIPClient("192.168.1.50")
    client.connect()
    client.activate_routing()
    yield client
    client.close()

@pytest.fixture(scope="function")
def default_session(doip_connection):
    """Ensure ECU is in Default Diagnostic Session before each test."""
    doip_connection.send_uds(bytes([0x10, 0x01]))  # Back to default
    time.sleep(0.1)
    yield doip_connection

# test_diagnostics.py
import pytest

class TestUDSServices:

    def test_default_session_entry(self, doip_connection):
        """TC-UDS-001: Verify DiagnosticSessionControl 0x10 01."""
        response = doip_connection.send_uds(bytes([0x10, 0x01]))
        assert response[0] == 0x50, f"Expected 0x50, got 0x{response[0]:02X}"
        assert response[1] == 0x01, "Wrong session echo"
    
    def test_read_sw_version(self, doip_connection):
        """TC-UDS-022: Read SW Version via DID F189."""
        response = doip_connection.send_uds(bytes([0x22, 0xF1, 0x89]))
        assert response[0] == 0x62, "Expected positive response 0x62"
        sw_version = response[3:].decode("ascii", errors="replace")
        assert len(sw_version) >= 4, f"SW version too short: '{sw_version}'"
        print(f"SW Version: {sw_version}")
    
    def test_security_access_wrong_key(self, doip_connection):
        """TC-UDS-027: Wrong security key rejected."""
        # Enter extended session first
        doip_connection.send_uds(bytes([0x10, 0x03]))
        # Request seed
        seed_resp = doip_connection.send_uds(bytes([0x27, 0x01]))
        assert seed_resp[0] == 0x67
        # Send wrong key (all zeros)
        key_resp = doip_connection.send_uds(bytes([0x27, 0x02, 0x00, 0x00, 0x00, 0x00]))
        assert key_resp[0] == 0x7F, "Expected NRC (negative response)"
        assert key_resp[2] == 0x35, f"Expected NRC 0x35, got 0x{key_resp[2]:02X}"
    
    def test_clear_dtcs(self, doip_connection):
        """TC-UDS-014: Clear all DTCs successfully."""
        response = doip_connection.send_uds(bytes([0x14, 0xFF, 0xFF, 0xFF]))
        assert response[0] == 0x54, "Expected positive response 0x54"

# pytest.ini
[pytest]
testpaths = tests
addopts = --tb=short --html=reports/test_report.html -v
markers =
    smoke: Quick sanity tests
    regression: Full regression suite
    diagnostics: UDS/DoIP tests
    ethernet: Ethernet protocol tests
```

---

## 9.9 TEST REPORTS AND METRICS

### Test Report Structure

```
AUTOMOTIVE TEST REPORT FORMAT:

PROJECT:  ADAS_ECU v2.3.0 Integration Test Report
DATE:     2025-01-15
BUILD:    ADAS_SW_v2.3.0-RC5
TESTER:   [Name]
BENCH:    HIL_Rack_3 (dSPACE SCALEXIO + CANoe 15.3)

EXECUTIVE SUMMARY:
  Total Test Cases:      247
  Executed:              247 (100%)
  Passed:                241 (97.6%)
  Failed:                  5 ( 2.0%)
  Blocked:                 1 ( 0.4%)
  Not Executed:            0 (  0%)

FAILURE SUMMARY:
  Bug ID  │ TC ID         │ Severity │ Component    │ Status
  ────────────────────────────────────────────────────────────
  BUG-421 │ TC-ETH-044    │ S2       │ SOME/IP_SD   │ OPEN
  BUG-422 │ TC-AEB-042-05 │ S1       │ FCW_Algorithm│ IN PROGRESS
  BUG-423 │ TC-FLASH-003  │ S2       │ Bootloader   │ FIXED-RETEST
  BUG-424 │ TC-DOIP-007   │ S3       │ DoIP_GW      │ OPEN
  BUG-425 │ TC-SEC-011    │ S2       │ SecOC        │ OPEN

BLOCKED:
  TC-TSN-006: Blocked by BUG-421 (TSN depends on SD working)

REQUIREMENT COVERAGE: 98.7% (2/158 requirements without TC)

GO/NO-GO RECOMMENDATION:
  NO-GO — BUG-422 (S1 safety bug) must be fixed and verified
  before software can be approved for vehicle testing.
```

---

## 9.10 INTERVIEW QUESTIONS — SECTION 9

**Q1: What is the difference between smoke testing and regression testing?**

> Smoke testing is a shallow, rapid check that the ECU or software delivery is healthy enough to proceed with further testing — does it boot? Is Ethernet up? Are basic services running? It runs in 5-15 minutes. Regression testing is a comprehensive re-run of the entire test suite to ensure that new code changes haven't broken previously working functionality. It runs overnight (4-24 hours) on a CI pipeline and checks 100% of existing test cases.

**Q2: How do you design test cases from a requirement?**

> I start by decomposing the requirement into: what is being tested, the triggering condition, the expected timing/value, and the preconditions. Then I apply equivalence class partitioning to create classes of valid/invalid inputs. I apply boundary value analysis to test at exact limits. I create positive test cases (valid inputs → correct output), negative test cases (invalid input → correct rejection), and boundary test cases. Each test case gets an ID linked to the requirement in the RTM.

**Q3: What is a Requirement Traceability Matrix (RTM) and why is it important?**

> An RTM is a matrix that links every requirement to one or more test cases, and every test case to a test result. It answers "Is this requirement tested? Did it pass?" It's important because: (1) ASPICE SWE.4/SWE.5/SWE.6 mandate 100% requirement coverage. (2) It proves to the OEM that all requirements are validated. (3) It helps identify untested requirements before software delivery. (4) It links bugs back to specific requirements, showing impact of failures.

**Q4: Explain ASIL levels in ISO 26262 and how they affect testing.**

> ASIL (Automotive Safety Integrity Level) ranges from QM (no safety requirement) to ASIL D (most critical). Higher ASIL requires more rigorous testing: ASIL A requires 100% statement coverage, ASIL B requires 100% branch coverage, ASIL C/D requires 100% MC/DC coverage. ASIL D also requires formal inspections, back-to-back testing (MIL vs SIL comparison), and fault injection testing. As a validation engineer, ASIL D features require formal test procedures with witnessed sign-off, not just running automated scripts.

**Q5: You find a Critical (S1) defect 2 days before software delivery. What do you do?**

> I immediately: (1) Log the defect in Jira with severity S1, detailed reproduction steps, logs, and Wireshark capture attached. (2) Notify the test lead and project manager verbally — S1 bugs don't wait for email. (3) Confirm the Go/No-Go criteria — most automotive projects have a policy that S1 bugs block delivery. (4) Determine if a workaround exists that maintains safety — if yes, document it. (5) Work with the developer to understand fix timeline. (6) If fix is available, retest immediately and document in the test report with before/after evidence.

---

*Next Section → [Section 10: 300 Interview Q&A](10_Interview_Questions_300QA.md)*
