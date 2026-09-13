# PART 5 — TEST CASE DESIGN: PROFESSIONAL TECHNIQUES
## How Test Analysts Design Comprehensive Test Cases

**Learning Time:** 5 hours  
**Difficulty:** Beginner → Advanced  
**Interview Frequency:** 90% (Core skill, tested extensively)  
**Job Relevance:** CRITICAL - You'll write 100s of test cases

---

## TABLE OF CONTENTS

1. [Test Case Fundamentals](#test-case-fundamentals)
2. [Positive vs Negative Testing](#positive-vs-negative-testing)
3. [Boundary Value Analysis](#boundary-value-analysis)
4. [Equivalence Partitioning](#equivalence-partitioning)
5. [Decision Tables](#decision-tables)
6. [State Transition Testing](#state-transition-testing)
7. [Pairwise Testing](#pairwise-testing)
8. [Real Automotive Test Cases](#real-automotive-test-cases)
9. [Interview Q&A](#interview-qa)

---

## TEST CASE FUNDAMENTALS

### What is a Test Case?

A test case is a **documented specification** of:
- **What to test** (requirement)
- **How to test it** (steps)
- **With what inputs** (test data)
- **Expected outcomes** (results)
- **Pass/Fail criteria** (verification)

### Professional Test Case Format

```
╔═══════════════════════════════════════════════════════════╗
║  TEST CASE TEMPLATE                                       ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  TEST CASE ID:          TC-ENG-001                       ║
║  TITLE:                 Engine RPM Limiting               ║
║  AUTHOR:                John Smith                        ║
║  DATE CREATED:          2025-01-15                        ║
║  VERSION:               2.1                               ║
║                                                           ║
║  REQUIREMENT:           REQ-ENG-045                       ║
║  COMPONENT:             Engine Control Module             ║
║  TEST LEVEL:            SW-SW Integration                 ║
║  PRIORITY:              High (Safety)                     ║
║                                                           ║
║  ─────────────────────────────────────────────────────   ║
║  OBJECTIVE (What we verify):                             ║
║  ─────────────────────────────────────────────────────   ║
║  Verify that engine RPM does not exceed 6500 RPM         ║
║  when throttle command exceeds capability.              ║
║                                                           ║
║  ─────────────────────────────────────────────────────   ║
║  PRECONDITIONS (Starting state):                         ║
║  ─────────────────────────────────────────────────────   ║
║  1. Engine ECU flashed with firmware version 3.2.1       ║
║  2. ECU communication established on CAN bus             ║
║  3. Vehicle speed = 0 km/h (stationary)                  ║
║  4. Engine temperature = 90°C (normal)                   ║
║  5. Fuel pressure = 3.5 bar (normal)                     ║
║                                                           ║
║  ─────────────────────────────────────────────────────   ║
║  TEST ENVIRONMENT:                                        ║
║  ─────────────────────────────────────────────────────   ║
║  • HIL Simulator (dSPACE MicroAuto1401)                  ║
║  • Vehicle dynamics model v2.1                           ║
║  • Real Engine ECU                                       ║
║  • CANoe monitoring                                      ║
║  • Oscilloscope for PWM measurement                      ║
║                                                           ║
║  ─────────────────────────────────────────────────────   ║
║  TEST SETUP:                                              ║
║  ─────────────────────────────────────────────────────   ║
║  1. Launch HIL simulator                                 ║
║  2. Load vehicle dynamics model                          ║
║  3. Connect ECU via CAN transceiver                      ║
║  4. Configure throttle sensor to 0%                      ║
║  5. Start logging: CANoe, oscilloscope, HIL              ║
║                                                           ║
║  ─────────────────────────────────────────────────────   ║
║  TEST STEPS:                                              ║
║  ─────────────────────────────────────────────────────   ║
║  Step 1: Verify engine idle                              ║
║    Action: Monitor engine speed                          ║
║    Time: 1 second after startup                          ║
║    Expected: RPM = 500 ±50 RPM                           ║
║                                                           ║
║  Step 2: Apply 50% throttle                              ║
║    Action: Set throttle ADC = 2.5V (50%)                 ║
║    Time: At t=2s                                         ║
║    Expected: CAN msg "Throttle_Request = 50%"            ║
║             Engine accelerates smoothly                 ║
║                                                           ║
║  Step 3: Measure engine response                         ║
║    Action: Monitor RPM signal                            ║
║    Time: From t=2s to t=5s                               ║
║    Expected: RPM ramps from 500 to ~3000                 ║
║             Rate of change: < 2000 RPM/sec              ║
║                                                           ║
║  Step 4: Apply 100% throttle                             ║
║    Action: Set throttle ADC = 5.0V (100%)                ║
║    Time: At t=6s                                         ║
║    Expected: Engine accelerates further                 ║
║                                                           ║
║  Step 5: Verify RPM limiter activates                    ║
║    Action: Monitor engine RPM                            ║
║    Time: From t=6s to t=10s                              ║
║    Expected: RPM reaches 6500 ±20 RPM (not exceeded!)   ║
║             Fuel cut enabled (PWM = 0%)                 ║
║             CAN msg: "RPM_Limiter_Active = TRUE"         ║
║                                                           ║
║  Step 6: Verify recovery                                 ║
║    Action: Release throttle (set to 0%)                 ║
║    Time: At t=12s                                        ║
║    Expected: RPM decreases smoothly to 500              ║
║             No overshoot or hunting                      ║
║             RPM_Limiter_Active = FALSE                   ║
║                                                           ║
║  ─────────────────────────────────────────────────────   ║
║  EXPECTED RESULTS:                                        ║
║  ─────────────────────────────────────────────────────   ║
║  1. Engine RPM never exceeds 6500 RPM (±20 tolerance)   ║
║  2. Throttle response time < 150ms                       ║
║  3. No oscillation in RPM (steady at limit)              ║
║  4. Fuel PWM = 0% when RPM ≥ 6500                        ║
║  5. CAN message sequence correct and timely              ║
║  6. No error codes generated (DTC = 0)                   ║
║                                                           ║
║  ─────────────────────────────────────────────────────   ║
║  ACTUAL RESULTS:                                          ║
║  ─────────────────────────────────────────────────────   ║
║  [To be filled during test execution]                    ║
║                                                           ║
║  ─────────────────────────────────────────────────────   ║
║  LOGS REQUIRED:                                           ║
║  ─────────────────────────────────────────────────────   ║
║  • CANoe trace (.asc file):                              ║
║    - All CAN messages                                    ║
║    - Timestamps with nanosecond precision               ║
║    - Throttle command evolution                          ║
║    - Engine status messages                              ║
║  • HIL log:                                              ║
║    - Engine RPM signal (100Hz)                           ║
║    - Fuel injection PWM (100Hz)                          ║
║    - Simulator engine model state                        ║
║  • Oscilloscope capture:                                 ║
║    - PWM waveform (frequency, duty cycle)               ║
║    - Timing correlation with CAN messages               ║
║                                                           ║
║  ─────────────────────────────────────────────────────   ║
║  POSTCONDITIONS:                                          ║
║  ─────────────────────────────────────────────────────   ║
║  1. ECU still responsive to CAN commands                 ║
║  2. No fault codes latched in ECU memory                 ║
║  3. ECU can be shut down gracefully                      ║
║  4. All logs saved and timestamped                       ║
║                                                           ║
║  ─────────────────────────────────────────────────────   ║
║  PASS/FAIL CRITERIA:                                      ║
║  ─────────────────────────────────────────────────────   ║
║  PASS if ALL conditions met:                             ║
║  ✓ RPM never exceeds 6520 (6500 + 20 tolerance)         ║
║  ✓ Response time ≤ 150ms                                ║
║  ✓ No oscillation (RPM stays stable at limit)            ║
║  ✓ Fuel PWM = 0% when RPM ≥ 6500                        ║
║  ✓ All CAN messages on time                              ║
║  ✓ No error codes generated                              ║
║                                                           ║
║  FAIL if ANY condition violated:                         ║
║  ✗ RPM exceeds 6520 RPM (even once)                      ║
║  ✗ Response time > 150ms                                 ║
║  ✗ RPM oscillates (hunting behavior)                     ║
║  ✗ Fuel PWM not 0% at limit RPM                          ║
║  ✗ CAN message missing or late                           ║
║  ✗ Error code generated                                  ║
║                                                           ║
║  ─────────────────────────────────────────────────────   ║
║  DEFECTS FOUND (if any):                                 ║
║  ─────────────────────────────────────────────────────   ║
║  [List any defects discovered]                           ║
║  Example:                                                 ║
║  DEF-001: RPM exceeds limit by 50 RPM (6550 vs 6500)    ║
║    Severity: HIGH                                        ║
║    Root cause: Limiter threshold set incorrectly         ║
║    Fix: Adjust calibration constant                      ║
║                                                           ║
║  ─────────────────────────────────────────────────────   ║
║  TEST RESULT:         ✓ PASS / ✗ FAIL / ⚠ BLOCKED       ║
║  EXECUTION DATE:      2025-02-15                         ║
║  EXECUTED BY:         Jane Engineer                      ║
║  REVIEWED BY:         Test Lead                          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

### Traceability

```
Requirement (REQ-ENG-045)
    ↓
    └─→ Test Case (TC-ENG-001)
         ├─ Test Step 1: Idle verification
         ├─ Test Step 2: 50% throttle
         ├─ Test Step 3: Response time
         ├─ Test Step 4: 100% throttle
         ├─ Test Step 5: RPM limit (MAIN)
         └─ Test Step 6: Recovery
              ↓
              └─→ Expected Result
                  • RPM ≤ 6500
                  • Fuel cut = 0%
                  • Status message sent
                       ↓
                       └─→ Pass/Fail
                           ✓ All met = PASS
                           ✗ Any violated = FAIL
                                ↓
                                └─→ Log file
                                    CAN trace, HIL log
                                    Oscilloscope capture
                                         ↓
                                         └─→ Defect Report (if FAIL)
                                             DEF-001: Description
                                             Severity, Root Cause
```

---

## POSITIVE VS NEGATIVE TESTING

### Positive Testing
Tests that system **works correctly** with valid inputs

```
Example: Login Function

Positive Test Case:
  Input:    Username = "john", Password = "correct123"
  Expected: Login successful, redirect to dashboard
  
Positive Test Case:
  Input:    Username = "john", Password = "correct123" (after failed attempt)
  Expected: Session resets, login successful
  
Positive Test Case:
  Input:    Username = "JOHN" (uppercase), Password = "correct123"
  Expected: Login successful (case-insensitive)
```

### Negative Testing
Tests that system **handles errors gracefully** with invalid inputs

```
Example: Login Function

Negative Test Case:
  Input:    Username = "john", Password = "wrong123"
  Expected: Login fails gracefully
           Error message: "Incorrect password"
           No crash, no security vulnerability
           
Negative Test Case:
  Input:    Username = "", Password = ""
  Expected: Validation error
           Message: "Username and password required"
           
Negative Test Case:
  Input:    Username = "john", Password = (SQL injection: "' OR '1'='1")
  Expected: Input sanitized
           Login fails
           No database compromise
           
Negative Test Case:
  Input:    Username = (1000 characters), Password = "test"
  Expected: Input truncated or rejected
           No buffer overflow
           Graceful error message
```

### Automotive Example: Throttle Input

```
POSITIVE TESTS (Valid inputs):
  1. Throttle 0% → Idle (500 RPM)
  2. Throttle 50% → Medium power (3000 RPM)
  3. Throttle 100% → Full power (6000 RPM, limited)
  4. Throttle 0%-50%-0% (ramp up, ramp down)
  5. Rapid throttle changes
  6. Steady throttle hold

NEGATIVE TESTS (Invalid/edge inputs):
  1. Throttle sensor stuck at 0%
     Expected: Limp-home mode, reduced power
  2. Throttle sensor stuck at 100%
     Expected: Limp-home mode, safe state
  3. Throttle sensor open circuit (no signal)
     Expected: Fault code, idle only
  4. Throttle sensor -5V (invalid range)
     Expected: Clamp to 0-5V range, set error
  5. Throttle sensor 12V (over-voltage)
     Expected: Circuit protection, error code
  6. Rapid throttle changes (0% → 100% in 10ms)
     Expected: Rate-limited response (slew rate check)
  7. Missing CAN message from throttle module
     Expected: Timeout detection, safe state after 100ms
```

---

## BOUNDARY VALUE ANALYSIS

### What is BVA?

**Most defects occur at boundaries**, not in the middle:

```
Valid range: 0 to 100

INVALID      │ VALID RANGE     │ INVALID
             │                 │
-1, -2, -10  │ 0, 1, 50, 99... │ 100, 101, 110...
    ↓        │   ↓             │   ↓
  BELOW      │ INSIDE          │  ABOVE
  TEST ALL THREE REGIONS!
```

### Boundary Value Testing Technique

```
For range: 0 to 100

On Boundary:         Just Below:      Just Above:
  0                    -1                1
  100                  99                101
  
Test cases:
  1. Value = -1    (just below lower)    → Should REJECT
  2. Value = 0     (at lower boundary)   → Should ACCEPT
  3. Value = 1     (just above lower)    → Should ACCEPT
  4. Value = 50    (middle - optional)   → Should ACCEPT
  5. Value = 99    (just below upper)    → Should ACCEPT
  6. Value = 100   (at upper boundary)   → Should ACCEPT
  7. Value = 101   (just above upper)    → Should REJECT
```

### Automotive Example: Engine Speed Limiter

```
REQUIREMENT: Engine speed shall not exceed 6500 RPM

Boundaries:
  • Lower boundary: 0 RPM
  • Upper boundary: 6500 RPM
  • Invalid regions: <0, >6500

BVA Test Cases:

TC-001: RPM = -1 (invalid)
  Input: Engine speed sensor = -1
  Expected: Error code, limp-home
  Result: ✓ PASS (rejected invalid)

TC-002: RPM = 0 (boundary, idle)
  Input: Engine speed = 0 RPM (stalled)
  Expected: Idle detection, no fuel
  Result: ✓ PASS

TC-003: RPM = 1 (just above lower)
  Input: Engine speed = 1 RPM (barely turning)
  Expected: Fuel provided, engine cranks
  Result: ✓ PASS

TC-004: RPM = 3000 (middle)
  Input: Engine speed = 3000 RPM
  Expected: Normal operation
  Result: ✓ PASS

TC-005: RPM = 6499 (just below upper)
  Input: Engine speed = 6499 RPM
  Expected: Full fuel injection (not limited yet)
  Result: ✓ PASS

TC-006: RPM = 6500 (boundary, at limit)
  Input: Engine speed = 6500 RPM
  Expected: Fuel cut (limiter engages)
  Result: DEPENDS on specification:
    Option A: Fuel cut at 6500 → ✓ PASS (limiter active)
    Option B: Fuel cut above 6500 → ✗ FAIL (should allow 6500)

TC-007: RPM = 6501 (just above upper)
  Input: Engine speed = 6501 RPM
  Expected: Fuel cut (limiter active)
  Result: ✓ PASS

TC-008: RPM = 8000 (invalid, way above)
  Input: Engine speed = 8000 RPM
  Expected: Error code, limp-home
  Result: ✓ PASS
```

### Why BVA Works

```
Most software logic looks like:

IF (value >= 0 AND value <= 100) THEN
    // Process valid input
ELSE
    // Reject invalid
END IF

Boundaries are where:
  • Comparison operators change (< becomes ≤ or ≥)
  • Different code paths execute
  • Off-by-one errors occur
  • Integer overflow might happen
  
BVA tests these exact transition points!
```

---

## EQUIVALENCE PARTITIONING

### What is Equivalence Partitioning?

**Divide input space into groups where all values behave the same:**

```
Valid temperatures: -40°C to +125°C

Equivalence classes:
  1. Too Cold:     < -40°C  (all behave same: ERROR)
  2. Valid Cold:   -40 to 0°C  (all behave same: START)
  3. Valid Warm:   0 to 100°C  (all behave same: RUN)
  4. Valid Hot:    100 to 125°C  (all behave same: COOL)
  5. Too Hot:      > 125°C  (all behave same: ERROR)

INSTEAD OF testing every temperature:
  -50, -49, -48, ..., 124, 125, 126 (176 tests!)

TEST ONE FROM EACH CLASS:
  -50 (Too cold)
  -30 (Valid cold)
  50  (Valid warm)
  110 (Valid hot)
  150 (Too hot)

5 tests cover all cases!
```

### Equivalence Partitioning for CAN Message Status

```
REQUIREMENT: Handle CAN messages in different states

Valid states:
  1. NO_MESSAGE  (first time, no data yet)
  2. NEW_MESSAGE (received new frame this cycle)
  3. SAME_MESSAGE (same as last cycle, no new data)
  4. TIMEOUT     (expected message not received for >100ms)
  5. ERROR       (message received but corrupted)

Test cases (one per class):
  TC-001: Message not yet received → Handle NEW
  TC-002: Just received first message → Handle NEW
  TC-003: Message received again (same data) → Handle SAME
  TC-004: Message timeout (100ms elapsed) → Handle TIMEOUT
  TC-005: Message CRC error → Handle ERROR
  
Every other variation (timing, frequency) follows same pattern
because they're in same equivalence class!
```

---

## DECISION TABLES

### What is a Decision Table?

A table showing all **combinations of conditions** and their **resulting actions:**

```
Condition 1:  IF engine_running
Condition 2:  IF throttle > 0
Condition 3:  IF temperature > 100°C

Action 1: Start fuel injection
Action 2: Set cooling mode
Action 3: Set error code
```

### Decision Table for Engine Control

```
╔═════════════════════════════════════════════════════════════╗
║  CONDITION                    │ Case1 │ Case2 │ Case3 │ Case4║
╠═════════════════════════════════════════════════════════════╣
║ Engine running?               │ No    │ Yes   │ Yes   │ Yes  ║
║ Throttle command > 0%?        │ X     │ Yes   │ No    │ Yes  ║
║ Temperature > 100°C?          │ X     │ No    │ X     │ Yes  ║
╠═════════════════════════════════════════════════════════════╣
║ ACTION:                                                     ║
║ Start fuel injection?         │ No    │ Yes   │ No    │ Yes* ║
║ Activate cooling?             │ No    │ No    │ No    │ Yes  ║
║ Set overheat code?            │ No    │ No    │ No    │ Yes  ║
║ Reduce power?                 │ No    │ No    │ No    │ Yes  ║
╠═════════════════════════════════════════════════════════════╣
║ NOTES:                                                      ║
║ * Limited fuel to prevent overheat                           ║
║ X = don't care (not evaluated in that case)                 ║
║ Cases 1-4 cover all meaningful combinations                 ║
╚═════════════════════════════════════════════════════════════╝

Test cases from this table:

TC-001: Engine off
  Conditions: Running=No, Throttle=X, Temp=X
  Expected: No fuel, no cooling, no codes

TC-002: Engine on, throttle, normal temp
  Conditions: Running=Yes, Throttle=Yes (50%), Temp=No (95°C)
  Expected: Fuel on, no cooling, no codes

TC-003: Engine on, no throttle
  Conditions: Running=Yes, Throttle=No (0%), Temp=X
  Expected: No fuel (idle), no cooling, no codes

TC-004: Engine on, throttle, overheating
  Conditions: Running=Yes, Throttle=Yes (50%), Temp=Yes (110°C)
  Expected: Limited fuel, cooling on, overheat code
```

---

## STATE TRANSITION TESTING

### What is State Transition?

Software moves through **states**, and **transitions** between them happen based on inputs:

```
States: IDLE → STARTING → RUNNING → STOPPING → IDLE

Transitions:
  IDLE --[START command]-→ STARTING
  STARTING --[Engine cranked]-→ RUNNING
  RUNNING --[STOP command]-→ STOPPING
  STOPPING --[Engine stopped]-→ IDLE
  
(Plus error transitions and edge cases)
```

### Engine ECU State Machine Example

```
                    ┌─ START_ENGINE
                    │
                    ↓
         ╔══════════════════════╗
         ║     STARTING         ║
         ║  (Crank motor on,   ║
         ║   Ignition enabled)  ║
         ╚═════┬────────────────╝
               │ [Engine RPM > 500 RPM]
               ↓
    ╔══════════════════════════╗
    ║      RUNNING             ║
    ║  (Fuel on, ignition on)  ║
    ║  ┌──────────────────┐    ║
    ├──│ Sub-state:       │    ║
    │  │ • Idle (0%)      │    ║
    │  │ • Normal (1-99%) │    ║
    │  │ • Limited (100%) │    ║
    │  └──────────────────┘    ║
    ╚═════┬────────────────────╝
          │ [STOP command]
          ↓
    ╔══════════════════════════╗
    ║      STOPPING            ║
    ║  (Fuel off, ignition off)║
    ╚═════┬────────────────────╝
          │ [Engine RPM < 100]
          ↓
    ╔══════════════════════════╗
    ║      IDLE                ║
    ║  (Ready for next cycle)  ║
    ╚══════════════════════════╝

ERROR TRANSITIONS (safety):
  STARTING --[Cranking > 10s without fire]-→ ERROR
  RUNNING --[CAN timeout]-→ ERROR
  ERROR --[Clear faults + Restart]-→ IDLE
```

### State Transition Test Cases

```
TC-ST-001: Normal Start Sequence
  1. State = IDLE
  2. Send: START_ENGINE command
  3. Verify: State transitions to STARTING
  4. Monitor: Crank motor engaged (PWM > 80%)
  5. Wait: Engine speed increases
  6. Verify: State transitions to RUNNING after RPM > 500
  Expected: Clean state machine progression

TC-ST-002: Normal Stop Sequence
  1. State = RUNNING
  2. Send: STOP_ENGINE command
  3. Verify: State transitions to STOPPING
  4. Monitor: Fuel cut (PWM = 0%), ignition disabled
  5. Wait: Engine speed decreases
  6. Verify: State transitions to IDLE after RPM < 100
  Expected: Clean shutdown

TC-ST-003: Emergency Stop (Safety)
  1. State = RUNNING
  2. Send: EMERGENCY_STOP
  3. Verify: Immediate state → STOPPING
  4. Monitor: Fuel cut IMMEDIATELY (< 50ms)
  5. Ignition: Disabled IMMEDIATELY
  6. Expected: No gradual shutdown, emergency cutoff

TC-ST-004: Invalid Transition (Error handling)
  1. State = IDLE
  2. Send: STOP_ENGINE (shouldn't stop if already stopped)
  3. Expected: Error code set
           State remains IDLE
           No state change

TC-ST-005: Timeout in STARTING (Cranking too long)
  1. State = STARTING
  2. Cranking for > 10 seconds (no engine fire)
  3. Expected: State → ERROR
           Crank motor disabled
           Error code: "Crank timeout"

TC-ST-006: CAN Timeout during RUNNING
  1. State = RUNNING
  2. CAN bus stops responding for 150ms
  3. Expected: State → ERROR
           Fuel cut (limp-home)
           Error code: "CAN bus off"
```

---

## REAL AUTOMOTIVE TEST CASES

Due to space constraints, I'm providing the structure. See dedicated files for full 30+ test cases:
- Electronic Parking Brake control
- Engine speed management  
- ABS wheel speed monitoring
- Transmission shift logic
- Diagnostic session handling
- Safety mechanism testing

---

## INTERVIEW Q&A

### Q1: "Describe your approach to designing test cases for a new requirement."

**Expert Answer:**
"I follow a structured approach: First, I analyze the requirement to identify all conditions, edge cases, and acceptance criteria. Second, I identify the test level needed - unit, component, integration, or system. Third, I apply test design techniques: Boundary Value Analysis for numeric ranges, Equivalence Partitioning to reduce test volume, Decision Tables for complex logic, State Transition for state machines. Fourth, I write detailed test cases with clear steps, expected results, and pass/fail criteria. Finally, I trace each test case back to the requirement to ensure coverage. For automotive, I always include negative tests (sensor failures, timeouts, invalid messages) and safety scenarios."

### Q2: "What's the difference between Boundary Value Analysis and Equivalence Partitioning?"

**Good Answer:**
"Both reduce test volume, but differently. Equivalence Partitioning divides the input space into groups where all values behave identically - you test one representative from each group. Boundary Value Analysis focuses on the edges where behavior changes - you test values just below, at, and just above boundaries. For example, for valid range 0-100: Equivalence Partitioning might test {-1, 50, 150}. BVA tests {-1, 0, 1, 99, 100, 101}. Together, they ensure comprehensive coverage with minimal tests."

### Q3: "How many test cases should you write for a requirement?"

**Good Answer:**
"Quality over quantity. I don't aim for a specific number - instead, I ensure requirements coverage. For simple requirements (e.g., 'RPM shall not exceed 6500'), 2-3 well-designed test cases suffice: boundary value just below (6499), at boundary (6500), and above (6501). For complex requirements with multiple conditions (e.g., multi-input decision logic), I use Decision Tables to generate 3-8 cases covering all combinations. Rule: If you find a requirement that needs 50+ test cases, the requirement is probably poorly written and should be decomposed."

---

## KEY TAKEAWAYS

✅ **Boundary Value Analysis:** Test at boundaries, below, and above  
✅ **Equivalence Partitioning:** One test per behavior group  
✅ **Decision Tables:** All combinations of conditions  
✅ **State Transition:** All state changes and error paths  
✅ **Positive + Negative:** Test what works AND what breaks  
✅ **Traceability:** Every test case traces to a requirement  

---

**Last Updated:** 2025-09-01  
**Status:** Ready for study  
**Interview Priority:** 90% (Core skill)

---
