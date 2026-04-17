# Section 1: Test Strategy & Planning
> **Role**: Senior Automotive Testing Team Lead | **Questions**: Q1–Q9

---

## Q1: How do you build an end-to-end test strategy for a new ECU (e.g., Infotainment Head Unit)?

### Question
You are assigned as Test Lead for a brand-new Infotainment Head Unit (IHU) project (Android Automotive OS). The hardware arrives in 3 months. How do you build the complete test strategy from scratch?

### Detailed Answer

An end-to-end test strategy for a new ECU follows the **V-Model** structure — validation is mirrored against each development phase:

```
Requirements (SRS/SDS)
    ↓ analyse
    ↓ → System Test Plan (STP)
Software Architecture
    ↓ → Integration Test Plan (ITP)
Software Unit Design
    ↓ → Unit Test Plan (UTP)
    ↓ IMPLEMENT
Unit Code → Unit Testing (SWC tests, CAPL, Google Test)
    ↓
Integration Build → Integration Testing (inter-module, CAN signals, IPC)
    ↓
Full SW+HW Build → System Testing (functional, regression, performance, stress)
    ↓
Vehicles → Validation (field, homologation, OEM acceptance)
```

**Step-by-step test strategy build:**

**Phase 1 — Requirements Analysis (Week 1–2)**
1. Extract all functional requirements from SRS (System Requirement Specification): feature list, performance targets, interface definitions.
2. Map each requirement to a **test category**: functional, performance, negative, boundary, interface.
3. Flag requirements lacking testability — raise a **Requirement Review Issue** to the system team.
4. Create **RTM v0** (Requirement Traceability Matrix): Req ID → Test Case ID placeholder.

**Phase 2 — Test Planning (Week 2–4)**
1. Define **test levels**: Unit → Integration → System → Acceptance.
2. Select **test types** per level:
   - Functional, Regression, Sanity, Smoke, Performance, Stress, Boundary, Equivalence Partition
3. Define **test environments**: SIL bench (software emulation), HIL bench (with real ECU + signal simulator), vehicle.
4. Define **entry/exit criteria** for each test phase.
5. Estimate effort using **function point analysis** or **test case count × avg execution time**.
6. Publish **Test Plan document** (IEEE 829 / ISO 29119 template).

**Phase 3 — Resource & Tool Setup (Month 1–2)**
- CANoe/CANalyzer for CAN/LIN signal validation
- Android ADB for log capture, crash debugging
- Automation: Python + UiAutomator / Appium for HMI test automation
- Jenkins for CI/CD nightly regression runs
- JIRA for defect tracking

**Phase 4 — Test Execution Strategy**
- Sprint-based execution aligned with software drops.
- **Smoke test** every drop (15 min sanity to gate the build).
- **Regression suite** after each sprint (8 h automated nightly).
- Manual exploratory testing for new features.

**Key Points ★**
- ★ Test strategy is a living document — update it at each milestone.
- ★ RTM must be 100% covered before system test exit.
- ★ Define clear entry criteria (build smoke passed) before starting any test cycle.
- ★ Always separate environment-specific risks (lab vs. vehicle) in the risk register.

### Entry/Exit Criteria Table

| Phase | Entry Criteria | Exit Criteria |
|-------|---------------|---------------|
| Unit Test | Code review done, peer approved | 100% line coverage, 0 critical defects |
| Integration Test | All SWC unit tests passed | All interface signals validated, 0 P1 defects |
| System Test | Integration test exit criteria met, HIL bench ready | RTM ≥ 98% covered, 0 critical open, sign-off |
| Acceptance Test | System test exit met | OEM sign-off, homologation certificate |

---

## Q2: How do you perform requirement analysis for automotive ECU testing (ASPICE context)?

### Question
Walk through how you analyse requirements for a Cluster ECU using ASPICE SWE.1 (Software Requirements Analysis) and how it impacts your test design.

### Detailed Answer

**ASPICE (Automotive SPICE)** is the process assessment standard used by most OEMs. For a Test Lead, the key processes are:
- **SWE.1** — Software Requirements Analysis
- **SWE.4** — Software Testing
- **SWE.6** — Software Qualification Testing
- **SUP.10** — Change request management

**Step-by-step requirement analysis for Cluster ECU:**

```
Input:
  ├── Customer Spec (OEM SRS): e.g., "Speedometer shall display 0–340 km/h with ±2% accuracy"
  ├── Technical Spec (Tier-1 SDS): derived from OEM SRS
  ├── Interface Control Documents (ICD): CAN DBs, DBC files, signal definitions
  └── MISRA/AUTOSAR rules (if software testing is in scope)

Analysis Steps:
1. For each requirement — check: Unique ID, Verifiable, Complete, Consistent, Feasible
2. Classify requirements:
   - Functional (F): "Speed shall update every 100 ms"
   - Non-Functional (NFR): "Boot time < 4 s"
   - Interface (IF): "Receive signal VehicleSpeed on CAN-C, 0x350h, 10 ms cycle"
   - Safety (SAFE): "ISO 26262 ASIL-B: if CAN signal lost, display dashes after 500 ms"
3. Identify testable vs. non-testable requirements
4. Write test cases directly derived from each requirement ID (1:n mapping — 1 req → n test cases)
5. Populate RTM (Traceability Matrix) in HP ALM / Polarion
```

**Common Requirement Issues Found During Analysis:**

| Issue Type | Example | Resolution |
|-----------|---------|------------|
| Ambiguous | "display shall be fast" | Raise clarification: define "fast" as < 500 ms |
| Untestable | "UI shall be intuitive" | Reject or convert to measurable usability metric |
| Missing | No spec for CAN timeout behavior | Add derived requirement; confirm with OEM |
| Contradictory | Screen timeout = 5 s in one doc, 10 s in another | Raise CR (Change Request), get written confirmation |
| Over-specified | Exact pixel color defined when OEM confirms "any amber" | Simplify to measurable range |

**Software Qualification (SWE.6):**
- Every system-level requirement must have at least one test case.
- Coverage metric: Requirement Coverage = (requirements with at least one passed test case) / (total requirements) × 100%
- ASPICE Level 2 minimum: documented test cases traceable to requirements.

**Key Points ★**
- ★ Never start test case design until requirements have formal review sign-off.
- ★ Requirements without IDs cannot be traced — enforce IDs from day one.
- ★ Invalid requirements discovered late are the #1 cause of project rework — invest in front-loaded analysis.
- ★ ASPICE audit will specifically check RTM completeness — keep it updated weekly.

---

## Q3: How do you estimate testing effort for a 6-month Infotainment project?

### Question
Your manager asks for a realistic test effort estimate for an infotainment project with 450 requirements and a 6-month delivery. How do you estimate?

### Detailed Answer

**Estimation approach: Three-Point (PERT) technique:**

```
E = (Optimistic + 4 × Most Likely + Pessimistic) / 6
```

**Step 1: Break down effort by test type:**

| Test Activity | Basis | Estimate (Person-Days) |
|--------------|-------|----------------------|
| Requirement analysis & RTM | 450 reqs × 0.5 h/req | 28 PD |
| Test case design | 450 reqs × 2.5 TC/req = 1125 TCs × 0.5 h/TC | 70 PD |
| Test environment setup (HIL bench, ADB, CANoe) | Fixed setup | 15 PD |
| Manual test execution (first cycle) | 1125 TCs × 15 min avg | 35 PD |
| Automated script development | 40% TCs automated = 450 × 2 h/script | 112 PD |
| Automated regression (maintenance) | 20% rework per sprint × 6 sprints | 20 PD |
| Defect reporting / retesting | Estimate 20% re-run | 15 PD |
| Review cycles (peer, customer) | Fixed | 10 PD |
| Reporting / documentation | Fixed | 8 PD |
| **Total** | | **~313 PD** |

**Step 2: Apply PERT buffer:**
- Optimistic: 280 PD (no major blockers)
- Most Likely: 313 PD
- Pessimistic: 380 PD (late requirements, HIL issues)
- **PERT E = (280 + 4×313 + 380) / 6 = 315 PD**

**Step 3: Convert to team size:**
- 315 PD over 6 months (26 working weeks = 130 working days)
- Team size = 315 / 130 = **~2.4 FTE** → recommend 3 engineers (1 senior + 2 mid-level + 1 automation = 4 including team lead)

**Risk buffer: +15% contingency = 315 × 1.15 = 362 PD → round to 4 engineers.**

**Key Points ★**
- ★ Always add 15–20% contingency for automotive projects (hardware delays are the norm, not exception).
- ★ Automation investment pays off from cycle 3 onward — justify it with a payback calculation.
- ★ Present estimate as a range, not a single number, to stakeholders.
- ★ Separate "test design" cost from "test execution" cost — customers often underestimate design effort.

---

## Q4: How do you build a risk register for an ECU testing project?

### Question
What are the key risks in a Cluster ECU testing project and how do you manage them as a test lead?

### Detailed Answer

A **Risk Register** is a living document capturing all project risks with probability, impact, mitigation, and owner. For a Cluster ECU project:

**Risk Register Template:**

| Risk ID | Risk Description | Likelihood (1–5) | Impact (1–5) | Risk Score | Mitigation | Owner | Status |
|---------|-----------------|-----------------|-------------|-----------|-----------|-------|--------|
| R01 | Late hardware delivery | 4 | 5 | 20 | Start SIL/virtual testing early; prepare HIL bench in parallel | PM | Open |
| R02 | Unstable/frequent SW drops | 4 | 4 | 16 | Define minimum smoke-pass criteria before testing; reject unstable builds | Test Lead | Open |
| R03 | DBC file not finalized late | 3 | 4 | 12 | Use placeholder DBC; flag as provisional; freeze Wk-4 | Systems | Open |
| R04 | HIL simulation model inaccurate | 3 | 4 | 12 | Validate HIL model with real vehicle measurements before milestone | HIL Eng | Open |
| R05 | ASPICE audit readiness | 2 | 5 | 10 | Weekly RTM review; documentation hygiene from day 1 | Test Lead | Open |
| R06 | Resource attrition (key tester leaves) | 2 | 4 | 8 | Knowledge documentation; cross-training within team | TL/HR | Open |
| R07 | OEM requirement change late (CR) | 3 | 3 | 9 | Impact analysis template ready; change freeze after Wk-10 | PM/TL | Open |
| R08 | Automation framework instability | 2 | 3 | 6 | Maintain manual fallback test suite for all critical paths | Automation Eng | Open |

**Risk Score = Likelihood × Impact (1–5 scale)**
- 15–25: **Critical** — immediate mitigation action
- 8–14: **High** — mitigate within sprint
- 4–7: **Medium** — monitor weekly
- 1–3: **Low** — log and review monthly

**Key Points ★**
- ★ Review risk register at every sprint retrospective — risks change weekly in automotive projects.
- ★ The biggest risk in ALL automotive ECU projects is late/unstable hardware — plan for it.
- ★ Never accept a project plan with zero risk buffer — it is not realistic and will fail.

---

## Q5: Describe your approach to test estimation using the V-Model in an ADAS project.

### Question
You are the test lead for an AEB (Automatic Emergency Braking) feature. How do you map the V-model to test levels and define what must be tested at each level?

### Detailed Answer

**V-Model for AEB Feature:**

```
LEFT ARM (Development)              RIGHT ARM (Testing)
─────────────────────────────────────────────────────────
System Requirements (SRS)     ←→   System Acceptance Test (SAT)
  AEB shall activate below 15 km/h       Field test, OEM track test, homologation
  
System Architecture (SAD)      ←→   System Integration Test (SIT)
  Sensor Fusion + Brake Actuator          HIL: radar + camera fusion + brake response
  
SW Architecture (SWArch)       ←→   Software Integration Test (SWIT)
  Fusion algorithm + brake control        SIL: module-level integration in simulation
  
SW Unit (SWUnit)               ←→   Software Unit Test (SUT)
  Object detection, TTC calculation       Unit test: Google Test / CUnit; >90% MC/DC
```

**AEB Test Cases Per Level:**

| Level | Example Test Cases | Environment |
|-------|-------------------|-------------|
| Unit Test | TTC calculation: verify time-to-collision formula for given relative speed/distance | SIL (MATLAB/Simulink, Google Test) |
| SW Integration | Fusion output: radar + camera agree on object; fusion selects correct object | SIL (MIL/SIL bench) |
| System Integration | HIL: inject radar target at 20 m, 60 km/h relative; verify brake demand signal issued within 200 ms | HIL (dSPACE SCALEXIO) |
| Acceptance | Real vehicle: pedestrian dummy at 30 km/h; verify full stop before impact | Track / OEM facility |

**ASIL Impact on Test Depth (ISO 26262):**
- AEB is typically **ASIL-B to ASIL-D** depending on speed range.
- ASIL-D requires: MC/DC coverage ≥ 100%, fault injection tests, diverse redundancy testing.

**Key Points ★**
- ★ For safety-critical ADAS features, unit test must achieve MC/DC (Modified Condition/Decision Coverage) — not just line coverage.
- ★ HIL testing is mandatory for AEB — you cannot safely test real braking in all edge cases in a real vehicle.
- ★ V-model exit gate review must be formal — no verbal sign-off for safety features.

---

## Q6: How do you plan a regression test suite that can run nightly in CI?

### Question
The team has 1200 test cases for a Cluster ECU. How do you design a regression suite that fits within a 6-hour nightly CI window?

### Detailed Answer

**Regression Suite Design Strategy: Risk-Based Prioritization**

**Step 1: Categorize all 1200 test cases by priority:**

| Priority | Criteria | Count | Estimated TCs |
|---------|---------|-------|--------------|
| P1 — Critical | Safety-critical features (speed, warnings); ASIL requirements; P0 defect areas | Core 15% | ~180 TCs |
| P2 — High | Key feature flows (boot, CAN signals, all tell-tales); frequently defective areas | 35% | ~420 TCs |
| P3 — Medium | Peripheral features (climate HMI, ambient light); rarely defective | 35% | ~420 TCs |
| P4 — Low | Edge case, cosmetic, low-used features | 15% | ~180 TCs |

**Step 2: Define 3 regression tiers:**

| Suite | TCs | Run Time | Trigger |
|-------|-----|----------|---------|
| **Smoke** (Critical) | P1: 180 TCs | 30 min | Every software build |
| **Daily Regression** | P1+P2: 600 TCs | 3 hours | Every night (nightly job) |
| **Full Regression** | All 1200 TCs | 8 hours | Weekly (weekend) or pre-milestone |

**Step 3: Automation to meet CI time budget:**
- Target: automate all P1 and 80% of P2 TCs.
- Automation time calc: 600 TCs × avg 17 s per TC = 10,200 s = **2.83 hours** ✓ fits in 3 h window.
- Parallel execution: run on 4 HIL stations in parallel → 3 h / 4 = **45 min daily regression**.

**Step 4: CI Pipeline (Jenkins):**
```
Git push → Trigger Jenkins pipeline
  → Stage 1: Build & static analysis (SonarQube)
  → Stage 2: Smoke test (180 TCs, 30 min)
      → If FAIL: block merge, notify team
      → If PASS: proceed
  → Stage 3: Nightly regression (600 TCs, parallel)
      → Report: pass/fail per TC, new failures highlighted
      → Failure: auto-raise JIRA defect with log attachment
  → Stage 4 (weekly): Full regression (1200 TCs)
```

**Key Points ★**
- ★ Smoke suite must be ≤ 30 minutes — developers will not wait longer for build feedback.
- ★ Parallel HIL execution reduces wall-clock time dramatically — invest in bench capacity.
- ★ Automate defect creation on CI failure — manual defect writing on nightly failures is unsustainable.

---

## Q7: How do you define and track testing milestones in a program?

### Question
Your project has a 12-month timeline with 3 major milestones (SOP-12 months, SOP-6 months, SOP). What testing milestones do you set?

### Detailed Answer

**Testing Milestone Plan (12-Month Program):**

| Month | Milestone | Key Testing Deliverables | Exit Criteria |
|-------|-----------|------------------------|---------------|
| M1 | Project Kickoff | Test Strategy document approved, RTM skeleton created | Test plan signed by OEM |
| M2–3 | SIL/MIL tests begin | Unit + module-level tests in simulation; no hardware yet | 90% unit test coverage |
| M4 | First HW (A-Sample) | Bring-up testing: boot, power, basic CAN comms | Board powers on, basic signals visible |
| M5–6 | SOP-6 Milestone | Integration test complete; system test FT1 (first test) cycle start | 80% req coverage, 0 P1/P2 open |
| M7–8 | B-Sample HW | Full system test; HIL regression; performance testing | RTM 90% covered; regression baseline established |
| M9–10 | SOP-3 Milestone | Regression complete; OEM acceptance test (OAT) starts | 95% RTM; 0 critical open defects |
| M11 | C-Sample / Pre-SOP | Homologation tests, field tests, final performance validation | 100% RTM; 0 P1; OEM sign-off letter |
| M12 | SOP (Start of Production) | Final test report; ASPICE documentation; lessons learned | All exit criteria met; sign-off archived |

**Weekly Dashboard (tracked by Test Lead):**

```
Week 32 Test Status Dashboard:
----------------------------------------------
Test Cases:        Planned: 1125 | Executed: 890 (79%) | Passed: 820 | Failed: 54 | Blocked: 16
Defects:           Open P1: 2 | P2: 8 | P3: 21 | Total Open: 31
RTM Coverage:      87% (target: 85% ✔)
Automation Rate:   61% (target: 60% ✔)
Build Status:      v3.4.1 — STABLE (smoke passed)
Risks:             R02 — 2 P1 defects still open (owner: SW team, ETA: 4 days)
----------------------------------------------
```

**Key Points ★**
- ★ Never skip a milestone exit criteria review — it is your last formal gate to prevent known defects entering production.
- ★ Track "planned vs. actual" execution rate weekly — ≥10% deviation is a red flag requiring replanning.
- ★ A well-maintained dashboard is your most powerful tool in stakeholder meetings.

---

## Q8: What is your approach to test case design using standard techniques?

### Question
For a Cluster ECU requirement "Fuel gauge shall display Low Fuel warning when fuel < 10 L," how do you design test cases using standard techniques?

### Detailed Answer

**Applicable design techniques:**

**1. Equivalence Partitioning:**
- Partition the fuel level input range into classes:
  - Class A (Invalid below min): fuel = negative value → system handles gracefully
  - Class B (Low fuel zone): 0 L ≤ fuel < 10 L → warning ON
  - Class C (Normal zone): 10 L ≤ fuel ≤ max → warning OFF
  - Class D (Full/overflow): fuel > max → system handles gracefully

**2. Boundary Value Analysis:**
| Boundary | Value | Expected |
|---------|-------|---------|
| Lower boundary - 1 | −1 L | System handles invalid input |
| Lower boundary | 0 L | Warning ON |
| Threshold − 1 | 9 L | Warning ON |
| Threshold | 10 L | Warning OFF (transition) |
| Threshold + 1 | 11 L | Warning OFF |
| Upper boundary | max_fuel L | Warning OFF |

**3. State Transition Testing:**
```
States: [Warning OFF] ←→ [Warning ON]

Transitions:
  T1: Warning OFF → Warning ON  : fuel drops below 10 L
  T2: Warning ON  → Warning OFF : fuel rises to ≥ 10 L (refueled)
  T3: Warning ON  → Warning ON  : fuel continues to drop (no state change)
  T4: Warning OFF → Warning OFF : fuel continues above 10 L

Test cases needed: cover T1, T2, T3, T4 → 4 state transition tests
```

**4. Decision Table:**
| CAN signal valid? | Fuel < 10 L? | Warning expected |
|-----------------|-------------|-----------------|
| Yes | Yes | ON |
| Yes | No | OFF |
| No (timeout) | — | Dashes (fault state) |
| No (invalid) | — | Dashes (fault state) |

**Key Points ★**
- ★ Boundary value analysis is the most effective technique for sensor-thresholded features (most of cluster/ADAS).
- ★ State transition testing is mandatory for all tell-tale and warning indicators.
- ★ Decision tables are best for multi-condition features (e.g., warning only if seat belt not fastened AND speed > 20 km/h).

---

## Q9: How do you handle test estimation when requirements are not yet finalized?

### Question
The OEM has not finalized the SRS. Your manager still wants an effort estimate. How do you handle this?

### Detailed Answer

This is a very common real-world situation. The approach is to provide an **analogical estimate with clear assumptions and risk-adjusted ranges**.

**Step 1: Use historical data:**
- If you have delivered a similar ECU project before, use its actual effort as a baseline.
- Example: previous Cluster ECU (350 req, 6-month) took 280 PD → this one has ~450 req, so scale: 280 × (450/350) × 1.1 (complexity factor) = 396 PD.

**Step 2: Provide a range, not a point estimate:**
```
Estimate Format to Manager/Customer:
  "Based on preliminary scope description and analogical estimation:
   Low estimate (requirements stable):  280–320 PD
   Most likely estimate:                360–400 PD
   High estimate (requirements unstable, late changes): 450–500 PD
   
   This estimate will be refined and baselined after SRS sign-off at Wk-4.
   Key assumption: requirement freeze by Month 2."
```

**Step 3: Document assumptions explicitly:**
- A1: SRS finalized by Wk-4
- A2: HIL bench available by Month 2
- A3: No more than 10% requirement change after freeze
- A4: Team of 4 FTE with automotive testing background

**Step 4: Formally revise estimate after SRS sign-off:**
- Once SRS is available, re-estimate using the full function-point or test-case count method (see Q3).
- Get written acknowledgment that estimate was baseline-updated — protects the team from scope creep claims.

**Key Points ★**
- ★ Never give a single-point estimate for unclear scope — ranges protect you and set honest expectations.
- ★ Always state assumptions in writing — verbal assumptions are forgotten; written ones are tracked.
- ★ A preliminary estimate is a business commitment, not a technical one — communicate this clearly.
