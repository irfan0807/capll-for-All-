# Section 6: Process & Quality
> **Role**: Senior Automotive Testing Team Lead | **Questions**: Q53–Q60

---

## Q53: How do you manage the full defect lifecycle in JIRA for an automotive project?

### Question
Describe the end-to-end defect lifecycle used in your automotive testing projects and how you enforce discipline in JIRA.

### Detailed Answer

**Defect Lifecycle (Automotive Standard Workflow):**

```
[NEW] → Raised by tester with full reproduction steps + log/trace attachment

  ↓ (Daily Triage)
  
[IN TRIAGE] → Test Lead validates severity/priority; assigns to developer
  → If invalid: [REJECTED] with reason (tester must acknowledge and learn)
  → If duplicate: [DUPLICATE] → linked to original
  → If valid: severity set; developer assigned; sprint target set

  ↓
  
[ASSIGNED / IN DEVELOPMENT] → Developer investigates; updates defect with findings
  Expected: Developer updates within 48h (P1), 72h (P2)
  
  ↓
  
[FIXED] → Developer sets status; attaches: fix commit ID, build number containing fix
  Note: Defect MUST NOT be set to "Fixed" without a build reference
  
  ↓
  
[READY FOR RETEST] → Build with fix handed to test team
  Retest: performed by ORIGINAL reporter (knows the exact reproduction path)
  
  ↓ Retest passes     ↓ Retest fails
  
[VERIFIED]          [REOPENED] → Back to [ASSIGNED/IN DEVELOPMENT]
  ↓
[CLOSED] → Quality gate: 2 independent testers must confirm close for P1

Parallel state: [DEFERRED] → Known defect moved to later milestone (with PM + OEM approval)
```

**JIRA Defect Template (mandatory fields):**
```
Summary: [ECU] [Feature] [Brief description]
  Example: [Cluster][Speed] Speedometer shows 0 km/h when VehicleSpeed signal > 200 km/h

Description:
  Preconditions: [SW version, bench config, tool versions]
  Steps to Reproduce:
    1. Set VehicleSpeed CAN signal to 210 km/h via CANoe
    2. Observe Cluster speedometer
  Actual Result: Speedometer displays 0 km/h
  Expected Result: Speedometer displays 210 km/h (per SRS §4.2.3)
  
  Attachments: [CANoe trace, screenshot, ADB log]
  
Severity: P1 / P2 / P3 / P4
Test Case ID: TC-SPD-220 (requirement reference: CLUS-REQ-045)
Regression: Yes (this feature was previously passing — regressed in v4.1.0)
```

**JIRA Metrics Dashboard (Team Lead monitors weekly):**

| Metric | Healthy | Warning |
|--------|---------|---------|
| P1 defects open | 0 | >0 = escalate immediately |
| P2 defects age > 5 days | 0 | >2 = developer planning issue |
| Defect invalid rate | < 10% | >15% = tester training needed |
| Reopened rate | < 5% | >10% = developer fix quality issue |
| Deferred defects | Tracked, approved | Untracked deferral = process violation |
| Defects with no build reference | 0 | Any = reject immediately |

**Key Points ★**
- ★ A "Fixed" defect without a build/commit reference is evidence-free — enforce this rule with zero exceptions.
- ★ P1 defects must have daily updates from the developer until closed — silence on a P1 is not acceptable.
- ★ The reopened rate is a developer quality metric — track it per developer and address patterns directly in 1:1s.

---

## Q54: How do you build and maintain a Requirement Traceability Matrix (RTM)?

### Question
An OEM ASPICE auditor asks: "Show me end-to-end traceability from a customer requirement to a test result to any defects raised." Walk through this.

### Detailed Answer

**RTM Structure (End-to-End Traceability):**

```
LEVEL 1: Customer Requirement (OEM SRS)
  OEM-REQ-025: "Instrument Cluster shall display external temperature in the range -40°C to +80°C"
  
    ↓ derived by Tier-1 systems team
    
LEVEL 2: System Requirement (Tier-1 SRS/SDS)
  SYS-REQ-112: "Cluster ECU shall receive ExtTemp_CAN signal (0x220, byte 2, factor 0.5, offset -40)"
  SYS-REQ-113: "Cluster shall display ExtTemp with formula: displayed_val = raw × 0.5 - 40"
  SYS-REQ-114: "Cluster shall display '---' if CAN signal timeout > 1000 ms"
  
    ↓ test cases designed per requirement
    
LEVEL 3: Test Cases
  TC-TEMP-001: ExtTemp at -40°C (raw = 0): verify display shows -40°C
  TC-TEMP-002: ExtTemp at 0°C (raw = 80): verify display shows 0°C
  TC-TEMP-003: ExtTemp at +80°C (raw = 240): verify display shows +80°C
  TC-TEMP-004: CAN signal timeout >1000 ms: verify display shows '---'
  TC-TEMP-005: Boundary: raw = 255 (>+87.5°C, out of spec): verify graceful handling
  
    ↓ execution results
    
LEVEL 4: Test Results
  TC-TEMP-001: PASSED (v4.1.2, Wk32)
  TC-TEMP-002: PASSED
  TC-TEMP-003: PASSED
  TC-TEMP-004: FAILED → Defect #1033 raised
  TC-TEMP-005: N/A (out-of-scope; boundary deferred)
  
    ↓ defect lifecycle
    
LEVEL 5: Defects
  Defect #1033: ExtTemp '---' not showing after CAN timeout; shows last valid value
    Status: Fixed in v4.1.3; Retested v4.1.3: PASSED; Closed Wk33
```

**RTM Coverage Report (for ASPICE / OEM):**

```
Total Requirements:            450
Requirements with Test Cases:  441  (98%)
Requirements with Passed TCs:  415  (92%)
Requirements with Failed TCs:   18  (4%)   ← open defects
Requirements with no TCs:        9  (2%)   ← open gap: SYS-REQ-380–388 (safety requirements; planned Wk33)

RTM Coverage = 441/450 = 98% ← ASPICE minimum: 100% at system test exit
```

**Maintaining RTM in HP ALM / Polarion:**
- Requirement changes automatically flag linked test cases as "suspect" — tester must review and confirm or update TC.
- Automated gap report: ALM filter → requirements with 0 linked TCs → assigned to tester each sprint.

**Key Points ★**
- ★ RTM is the most important ASPICE artifact for testing — invest in it from day 1; retrospective build is exponentially more expensive.
- ★ "Suspect" flag on requirement change is critical — a changed requirement without test case update is a silent gap.
- ★ 100% RTM coverage is the exit criterion for system testing: not "we tried our best."

---

## Q55: How do you apply ISO 26262 concepts to your testing approach for safety-critical features?

### Question
The Cluster ECU's speedometer is classified as ASIL-B. What does this mean for your testing approach?

### Detailed Answer

**ISO 26262 ASIL levels:**

| ASIL | Descriptions | Typical Coverage |
|------|-------------|-----------------|
| QM | Quality Managed (no ASIL) | Standard testing |
| ASIL A | Occasional hazard; low severity | Statement coverage |
| ASIL B | Controlled exposure; major injury possible | Branch coverage |
| ASIL C | Frequent exposure; life-threatening | MC/DC coverage |
| ASIL D | Highest risk; life-critical | 100% MC/DC + formal methods |

**ASIL-B Requirements for Speedometer Testing:**

**1. Coverage: Branch Coverage (minimum for ASIL-B)**
```
If speedometer SW has:
  if (speed_valid) { display(speed); }
  else             { display(dashes); }
  
Branch coverage requires:
  TC1: speed_valid = true → display(speed) branch taken ✓
  TC2: speed_valid = false → display(dashes) branch taken ✓
```

**2. Fault Injection Testing (required for ASIL-B+)**
```
Fault injection scenarios:
  IF-001: CAN signal corrupted (bit flip in speed byte) → cluster displays safe value (dashes or 0)
  IF-002: CAN message ID clash (another ECU sends 0x3B4) → cluster detects duplicate; displays last valid or dashes
  IF-003: Single-event upset (SEU) in SRAM (simulated) → ECU detects via CRC → safe state
  IF-004: Stack overflow → watchdog resets ECU → cluster recovers within 2 s
```

**3. Diagnostic Coverage (DC)**
- ASIL-B requires DC ≥ 60% (ASIL-C: 90%, ASIL-D: 99%).
- Diagnostic mechanisms for speed signal:
  - CAN signal timeout detection (covers signal loss fault)
  - CAN message CRC check (covers signal corruption)
  - Signal range check (covers implausible value fault)
  - Redundant speed signal cross-check (covers wrong signal fault)
- Each mechanism provides coverage for a specific fault class: document in the Safety Concept.

**4. Safety Test Documentation (ISO 26262 Part 6)**
- For every ASIL-B test: document test rationale (which safety requirement it covers).
- Formal test report: test date, engineer, environment version, result, signature.
- Maintained for vehicle lifetime (minimum 10 years per ISO 26262 §6.4.11).

**5. Independence (required for ASIL-B)**
- Test cases for ASIL-B requirements must be reviewed by an independent engineer (not the test case author).
- Test execution may be by same team but test design must be independent.

**Key Points ★**
- ★ ASIL does not mean "test more" — it means "test smarter with the right coverage criteria and document everything."
- ★ Fault injection is the differentiator — ASIL-B testing is not complete without injecting faults and verifying safe state behavior.
- ★ ISO 26262 evidence must be retained for vehicle lifetime — never delete test logs from safety-critical features.

---

## Q56: How do you use test case design techniques effectively across different feature types?

### Question
Give concrete examples of how you choose and apply test design techniques for automotive features.

### Detailed Answer

**Feature-to-Technique Mapping:**

**Feature 1: Speedometer display (analog sensor → display)**
- Best technique: **Boundary Value Analysis (BVA)**
```
Valid range: 0–220 km/h
Boundaries:
  -1 km/h (below, invalid)   → graceful handling
   0 km/h (lower bound)      → display 0
   1 km/h (just above lower) → display 1
  110 km/h (midpoint)        → display 110
  219 km/h (just below upper)→ display 219
  220 km/h (upper bound)     → display 220
  221 km/h (above upper)     → out of gauge range: clamp or dashes
```

**Feature 2: Tell-tale ON/OFF logic (warning indicator)**
- Best technique: **State Transition Diagram**
```
States: OFF ↔ ON
Transitions:
  OFF → ON : trigger condition met (e.g., ABS fault)
  ON → OFF : trigger condition cleared
  ON → Flashing: persistent fault after 60 s (if spec requires)
  Flashing → OFF: fault cleared
Test: every transition + timer condition
```

**Feature 3: Password/PIN entry for settings menu**
- Best technique: **Equivalence Partitioning**
```
Partitions:
  Valid 4-digit PIN (1234)         → access granted
  Invalid PIN (4321)               → access denied
  Partial PIN (3 digits)           → incomplete; rejected
  PIN with special character (12#4)→ rejected
  Empty PIN submission              → rejected
```

**Feature 4: Vehicle mode selection (NORMAL/ECO/SPORT/OFF-ROAD)**
- Best technique: **Decision Table**
```
| Gear | Speed | Mode Press | Expected |
|------|-------|-----------|---------|
| P    | 0     | ECO       | ECO mode active |
| D    | 0     | SPORT     | SPORT mode active |
| D    | 60    | OFF-ROAD  | REJECTED (speed > 30 km/h) |
| N    | 0     | ANY       | Accepted |
| R    | 0     | SPORT     | REJECTED (SPORT not in reverse) |
```

**Feature 5: AEB activation (complex multi-condition)**
- Best technique: **Pairwise testing (PICT tool)**
```
Parameters:
  Host speed: {10, 30, 50, 80} km/h
  Target type: {pedestrian, bicycle, car, truck}
  Time-to-collision: {< 1 s, 1–2 s, >2 s}
  Driver override: {yes, no}
  
Pairwise: tests every pair of parameter values → reduces 4×4×3×2 = 96 combinations
          to ~20 pairwise tests covering all 2-way interactions
```

**Technique Selection Reference:**

| Feature Type | Primary Technique | Secondary |
|-------------|------------------|-----------| 
| Threshold / sensor | Boundary Value | Equivalence Partition |
| Mode/state switching | State Transition | Decision Table |
| Multi-condition features | Decision Table | Pairwise |
| UI input validation | Equivalence Partition | Boundary Value |
| Complex combinations | Pairwise | Decision Table |
| Protocol sequences | State Transition | Scenario-based |

**Key Points ★**
- ★ Boundary Value Analysis is the highest-ROI technique for automotive sensor/signal testing.
- ★ Pairwise testing for ADAS (many input combinations) reduces test count by 80% while maintaining 2-way coverage.
- ★ No single technique covers all scenarios — always combine 2–3 techniques per feature.

---

## Q57: How do you ensure test automation quality (testing your tests)?

### Question
Your automated test suite keeps giving false-positive results (passing when the feature is actually failing). How do you address automation quality?

### Detailed Answer

**False Positive Root Causes in Automotive Automation:**

| Root Cause | Example | Fix |
|-----------|---------|-----|
| Wrong tolerance | Speed check: `if (speed != 60.0)` → passes on 59.99 (floating point) | Use tolerance: `abs(speed - 60.0) < 0.5` |
| Timeout too short | Signal wait 100 ms; but signal arrives in 200 ms → assumed not received → test says pass blindly | Increase timeout; add explicit failure on non-receipt |
| No actual assertion | CAPL script runs command but never verifies response | Add testStepPass/Fail after EVERY check |
| Test using simulator default (not ECU) | CAPL reads signal from database default, not from ECU | Verify signal source: read from CAN channel, not symbolic default |
| ECU not powered | Test starts; ECU off; all signals at 0; check says "0 == OK" | Add precondition: ECU alive check before test starts |
| Hardcoded VIN/ECU address | Script hardcoded for bench A; run on bench B → different address → test skips silently | Parameterize setup (config file per bench) |

**Automation Test Quality Checks:**

```
For each automated test case, peer-review checklist:
  □ Preconditions verified (ECU powered, CAN active, session entered)?
  □ Every assert has a clear pass/fail — no fire-and-forget commands?
  □ Timeout guards on all signal waits?
  □ Tolerance-based comparison for all analog values (not == for floats)?
  □ Test isolation: does this test work standalone OR does it depend on previous test state?
  □ Cleanup: after test, environment reset to baseline (not left in modified state)?
  □ Log output: does FAIL case produce enough information to debug WITHOUT re-running?
  □ Correct test case linked in test management system?
```

**Mutation Testing (Advanced Validation of Test Effectiveness):**
- Deliberately inject a 1-bit fault into the ECU SW or CAN signal.
- Run the automated test.
- If the test PASSES on a faulty ECU: test is incomplete — it doesn't catch this fault class.
- Fix the test to catch the mutation.

**Key Points ★**
- ★ A test that always passes is useless — periodically verify your automation suite catches known bugs (mutation testing).
- ★ Test isolation is critical for automotive regression — a test that depends on previous state can cascade failures misleadingly.
- ★ The false positive rate is a metric — track it; if > 5% of automation failures require investigation to confirm they are real failures, your assertion design needs improvement.

---

## Q58: How do you set up and use a CI/CD pipeline for automotive ECU testing?

### Question
Your team wants to implement CI/CD for Cluster ECU testing. Describe the pipeline from code commit to test report.

### Detailed Answer

**CI/CD Pipeline for ECU Testing:**

```
git commit → push to GitLab → Webhook triggers Jenkins

Jenkins Pipeline Stages:
─────────────────────────────────────────────────────────────
Stage 1: BUILD VALIDATION (5 min)
  → Pull latest SW build artifact from build server
  → Validate CRC / signature of build
  → Flash ECU on HIL bench via ETAS INCA or Vector FlashRunner
  → If flash fails: abort pipeline; notify Slack #automotive-test

Stage 2: SMOKE TEST (30 min)
  → Run 180 P1 test cases via CANoe automated test module
  → CANoe CAPL TestModules executed via command line:
      canoe.exe -prj ClusterECU.cfg -testmodule SmokeTest.can -noGUI
  → If > 5 failures: abort; notify; block merge

Stage 3: UNIT TEST / SIL (20 min)
  → Run SIL unit tests (Google Test / CUnit via cross-compiler)
  → Coverage report (gcov/LCOV) → fail if coverage < 85%

Stage 4: INTEGRATION TEST (2 h) [Nightly only]
  → 600 P1+P2 test cases across 4 parallel HIL stations
  → Parallel execution via Jenkins parallel stages:
      parallel {
        stage('Bench A - Speed/RPM') { sh 'run_canoe_bench_a.sh' }
        stage('Bench B - Tell-tales') { sh 'run_canoe_bench_b.sh' }
        stage('Bench C - BT/Media') { sh 'run_canoe_bench_c.sh' }
        stage('Bench D - Diagnostics') { sh 'run_canoe_bench_d.sh' }
      }

Stage 5: REPORT GENERATION
  → Parse CANoe .asc / .xml results
  → Generate HTML test report (Allure or custom)
  → Update JIRA: auto-create defect for each new failure (via JIRA REST API)
  → Publish report to Confluence
  → Email digest to team distribution list
─────────────────────────────────────────────────────────────
Total: Smoke → 35 min | Full nightly → 3 h (parallel) | Weekend full regression → 8 h
```

**CANoe command-line integration (Windows):**
```batch
@echo off
"C:\Program Files\Vector CANoe 16\CANoe64.exe" ^
  -prj "C:\Projects\ClusterECU\ClusterTest.cfg" ^
  -testmodule "SmokeTests.can" ^
  -report "C:\Reports\smoke_report_%DATE%.xml" ^
  -noGUI -autorun -quit
```

**Key Points ★**
- ★ CI for hardware-in-the-loop testing requires physical bench automation — the biggest investment is bench remote control capability (flash, power cycle, log capture).
- ★ Parallel HIL execution is the game-changer: 4 benches reduces 3 h test time to 45 min.
- ★ Auto-defect creation on CI failure is critical for scale — 600 nightly tests with manual defect raising is unsustainable.
