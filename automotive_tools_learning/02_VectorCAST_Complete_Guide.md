# VectorCAST — Complete Learning Guide
## Unit Testing, Coverage & Regression Testing for Embedded C/C++

**Classification:** Internal Training Document  
**Date:** April 2026  
**Applicable Standards:** ISO 26262, MISRA C:2012, DO-178C, ASPICE SWE.4/SWE.5

---

## 1. TOOL OVERVIEW

VectorCAST is a commercial automated unit testing and regression testing platform developed by Vector Informatik (integrated after acquisition of LDRA VectorCAST's original creators). It is widely used in the automotive, aerospace, and medical device industries to test embedded C and C++ code.

### Core Products
| Product | Function |
|---|---|
| **VectorCAST/C++** | Unit and integration testing for C and C++ code |
| **VectorCAST/Cover** | Code coverage measurement (statement, branch, MC/DC) |
| **VectorCAST/QA** | Centralized test management and reporting |
| **VectorCAST/MISRA** | MISRA C/C++ static analysis integration |
| **VectorCAST/Manage** | Multi-project regression management dashboard |
| **VectorCAST/RSP** | Remote shell protocol — on-target embedded execution |

### Key Differentiators vs. Competitors
| Feature | VectorCAST | GoogleTest | LDRA |
|---|---|---|---|
| Embedded target testing | ✅ Native RSP protocol | ❌ Host-based primarily | ✅ Native |
| Auto test generation | ✅ Strong | ❌ Manual | ✅ Strong |
| ISO 26262 TQI reports | ✅ Native | ❌ | ✅ Native |
| CI/CD CLI support | ✅ Scripted | ✅ Native | ✅ Scripted |
| MISRA enforcement | ✅ Integrated | ❌ | ✅ Integrated |

---

## 2. ARCHITECTURE & WORKFLOW

```
┌──────────────────────────────────────────────────────────────────────┐
│                       VECTORCAST WORKFLOW                            │
│                                                                      │
│  Source Files (.c / .cpp / .h)                                       │
│        │                                                             │
│        ▼                                                             │
│  [Instrumentation] ── VectorCAST wraps functions with probes         │
│        │                                                             │
│        ▼                                                             │
│  [Test Case Creation]                                                │
│     • Auto-generated basis path tests                                │
│     • Manual test cases (input/expected output tables)               │
│     • Regression baseline tests                                      │
│        │                                                             │
│        ▼                                                             │
│  [Execution — Host (x86) OR On-Target via RSP]                       │
│        │                                                             │
│        ▼                                                             │
│  [Coverage Report] ── Statement / Branch / MC/DC                     │
│        │                                                             │
│        ▼                                                             │
│  [VectorCAST/QA Report] ── Aggregated multi-project dashboard        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. KEY CONCEPTS

### 3.1 Test Harness Generation
VectorCAST automatically generates a test harness for every function under test. The harness:
- Stubs out all external dependencies (other modules, hardware registers, OS calls).
- Provides a controlled input/output framework.
- Removes the need for a complete integration environment to test a single function.

### 3.2 Stubbing Strategy
| Stub Type | When to Use |
|---|---|
| **Auto-stub** | VectorCAST auto-generates return values | External library functions |
| **User-coded stub** | You write a behavioral stub | Complex dependencies (state machines, CAN callbacks) |
| **Parameterized stub** | Return value is a VectorCAST test parameter | Simulating hardware sensor returns |

### 3.3 Regression Baseline Management
VectorCAST's "Expected" result system: once a test passes and is marked as a baseline, any future result deviation is flagged as a regression — not just a failure.

---

## 4. STAR CASES — 20+ Real-World Scenarios

---

### STAR Case 1: Unit Testing a Safety-Critical Throttle Control Function

**Situation:** An electronic throttle control (ETC) function was ASIL D classified. It controlled the throttle plate angle based on accelerator pedal input, with multiple safety limits and failsafe paths that were impossible to exercise via integration testing alone.

**Task:** Build a VectorCAST unit test suite that achieves 100% MC/DC coverage and exercises all failsafe paths for the ETC function.

**Action:**
- Imported the ETC source file into VectorCAST/C++.
- Auto-generated the test harness — all hardware register accesses were automatically stubbed.
- Identified all 14 compound decisions in the function using the control flow view.
- Used VectorCAST's basis path analysis to auto-suggest MC/DC test case pairs.
- Manually added test cases for fault injection paths (invalid pedal sensor readings, over-temperature conditions).
- Executed the full suite on both host (x86) and the embedded ECU target via VectorCAST/RSP.

**Result:**
- 100% MC/DC achieved on host. 98.7% on-target (2 hardware-interrupt fault paths required fault injection testing — documented separately).
- Suite executed in 2.1 minutes on-target. Added to CI nightly build.
- ISO 26262 Part 6, Table 11 evidence package generated in VectorCAST/QA format.

---

### STAR Case 2: Regression Detection After Software Update

**Situation:** A supplier released a new version of a CAN communication stack. The integration team integrated the new stack but had no automated way to confirm that the existing ECU functions still behaved identically.

**Task:** Use VectorCAST regression testing to detect any behavioral changes introduced by the new CAN stack version.

**Action:**
- Ran the existing VectorCAST test suite against the old stack version and captured the baseline results (all 847 tests: PASS).
- Switched the dependency to the new stack version. Re-ran the suite.
- VectorCAST flagged 23 tests as "UNEXPECTED RESULT" — meaning the output of these functions changed, even though the functions themselves had not been modified.
- Root cause analysis: 5 new functions in the new stack returned different default values when called with null parameters.

**Result:**
- Regression detected before integration into the main branch.
- Fixes applied to the new stack by the supplier.
- Re-run: all 847 tests passed. Integration approved.
- Estimated saving: prevented a 2-week system-level regression investigation.

---

### STAR Case 3: On-Target Execution via VectorCAST/RSP on ARM Cortex-M7

**Situation:** Unit tests were running successfully on the host (x86) simulator but a critical arithmetic routine was behaving differently on the ARM Cortex-M7 ECU target due to compiler-specific floating-point optimization flags.

**Task:** Configure VectorCAST for on-target execution to expose target-specific behavioral differences.

**Action:**
- Configured VectorCAST/RSP to communicate with the ARM target via JTAG (using a Lauterbach TRACE32 probe).
- Cross-compiled the VectorCAST harness with the production ARM compiler (GCC ARM 12.3 with `-mfpu=fpv5-d16`).
- Executed the test suite on-target. VectorCAST collected coverage and results via the RSP communications channel.
- Identified 4 tests that passed on host but failed on target due to floating-point rounding differences.

**Result:**
- Target-specific defects found and fixed.
- Host-only testing policy revised: all safety-critical modules must pass on-target execution.
- Procedure documented as the team's standard for cross-compilation validation.

---

### STAR Case 4: Building a VectorCAST Test Suite for an AUTOSAR SWC

**Situation:** An AUTOSAR Software Component (SWC) responsible for gear shift recommendation logic could not be tested at system level because it required a fully integrated AUTOSAR environment. No HIL rig was available for 3 months.

**Task:** Unit test the SWC in isolation using VectorCAST by stubbing out AUTOSAR RTE calls.

**Action:**
- Imported the SWC source into VectorCAST.
- Stubbed all AUTOSAR RTE (Runtime Environment) function calls (Rte_Read, Rte_Write, Rte_Call) using VectorCAST user-coded stubs.
- Parameterized stubs to return specific signal values (vehicle speed, engine torque, gear position) as test parameters.
- Built 120 test cases covering all gear shift decision boundaries.

**Result:**
- 94% branch coverage achieved without AUTOSAR infrastructure.
- 7 boundary condition defects found (incorrect gear recommendation at speed/torque thresholds).
- All 7 defects fixed and confirmed before HIL rig became available — saving estimated 6 HIL rig days.

---

### STAR Case 5: Generating ISO 26262 Evidence from VectorCAST/QA

**Situation:** The project's ISO 26262 Part 6 software verification plan required a documented test case specification, test execution log, and coverage report for each ASIL-classified module.

**Task:** Generate the required ISO 26262 software verification evidence from VectorCAST as a single, traceable package.

**Action:**
- Used VectorCAST/QA to compile results from all 18 project modules.
- Generated the following reports from VectorCAST:
  * Test Case Specification (mapping test cases to requirements)
  * Test Execution Results Log (pass/fail per test case with timestamp)
  * Coverage Analysis Report (MC/DC per function)
  * VectorCAST Tool Qualification report (VectorCAST is a pre-qualified tool under ISO 26262)
- Structured the evidence folder per the project's Document Management System (DMS) requirements.

**Result:**
- ISO 26262 auditor accepted the complete package generated from VectorCAST — no manual test documentation required.
- Audit time for software verification evidence: reduced from 3 days to 4 hours.
- Package reused for a related platform within 2 months.

---

### STAR Case 6: VectorCAST Integration into Jenkins CI/CD Pipeline

**Situation:** Unit tests were being run manually by senior engineers at the end of each sprint. This meant defects persisted for 2 weeks before being caught.

**Task:** Automate VectorCAST test execution in the CI/CD pipeline so every code commit triggers a unit test run.

**Action:**
- Installed VectorCAST's `clicast` command-line tool on the Jenkins build agent.
- Wrote a Jenkins pipeline stage that:
  * Rebuilt the VectorCAST environment for changed modules.
  * Executed all test cases via `clicast manage --project ci_project --run-tests`.
  * Published results in JUnit XML format for Jenkins test reporting.
  * Failed the build if any test failed or coverage dropped below 85% branch.

```groovy
stage('VectorCAST Unit Tests') {
    steps {
        sh '''
          cd /vectorcast
          clicast manage --project ci_project.vcm --run-tests
          clicast manage --project ci_project.vcm --report junit --output results.xml
        '''
        junit 'results.xml'
    }
}
```

**Result:**
- Defect detection cycle compressed from 2 weeks to under 10 minutes.
- 3 critical regressions caught in the first month of operation.
- Engineer capacity freed from manual test runs: estimated 8 hours/sprint reclaimed.

---

### STAR Case 7: Basis Path Testing for Complex Decision Functions

**Situation:** A braking distribution algorithm had a cyclomatic complexity of 19 and no existing unit tests. The safety manager required proof that every independent path through the function was tested.

**Task:** Use VectorCAST's basis path analysis to design and execute a minimum test set that covers all independent paths.

**Action:**
- Opened the function in VectorCAST and enabled basis path analysis mode.
- VectorCAST automatically identified 19 independent paths through the function (matching the cyclomatic complexity).
- For each path, VectorCAST suggested the required input conditions.
- Manually reviewed and validated each path suggestion, adjusting 4 inputs where VectorCAST's suggestion was not physically achievable.
- Executed all 19 basis path tests.

**Result:**
- 100% branch coverage achieved with exactly 19 carefully designed tests — far fewer than the 80+ tests that would have been needed without basis path guidance.
- All 19 tests passed. Coverage report submitted as evidence.

---

### STAR Case 8: Testing Exception Handlers and Error Paths

**Situation:** A software quality audit found that 30% of uncovered code in a module was error-handling branches (null pointer guards, range checks, CRC failure handlers). These paths were never triggered in normal functional testing.

**Task:** Build test cases specifically targeting all error and exception handling paths to improve branch coverage.

**Action:**
- Used VectorCAST's control flow view to identify every `if (ptr == NULL)`, `if (value > MAX)`, and `if (crc != expected)` branch.
- For each, designed a test case that specifically triggers the error condition:
  * Set pointer parameters to NULL.
  * Set value parameters to MAX+1 (boundary violation).
  * Set CRC input to a known-bad value.
- Captured function return values and global state changes to verify the error handler executed correctly.

**Result:**
- Branch coverage increased from 68% to 93%.
- 4 defects found in error handlers: 2 functions returned incorrect error codes; 1 function set a global flag incorrectly on CRC failure.
- All defects fixed. These would never have been found via integration testing.

---

### STAR Case 9: VectorCAST for Battery State-of-Charge (SoC) Algorithm Testing

**Situation:** A BMS SoC estimation algorithm used complex mathematical models (Kalman filter, Coulomb counting) that required precise numerical accuracy validation across a wide range of input conditions.

**Task:** Build a systematic parametric test suite validating SoC accuracy within ±2% across all temperature, current, and voltage combinations.

**Action:**
- Used VectorCAST's parameterized test capability to define input ranges:
  * Temperature: −40°C to +60°C in 5°C steps = 21 values.
  * Current: −200A to +200A in 10A steps = 41 values.
  * Voltage: 2.5V to 4.2V in 0.05V steps = 35 values.
- Generated 21 × 41 × 35 = 30,135 parameterized test cases.
- Compared VectorCAST output against a reference MATLAB/Simulink model output for the same inputs (golden reference approach).

**Result:**
- 99.7% of parameterized tests passed (≤2% SoC error).
- 87 test cases identified numerical corner cases exceeding the 2% threshold at extreme temperatures with high discharge currents.
- Algorithm updated to handle the identified edge cases.

---

### STAR Case 10: Detecting Memory Corruption in Embedded C Code

**Situation:** An intermittent ECU reset was occurring in a field vehicle approximately once per 800 hours of operation. The root cause was suspected to be a memory corruption issue but was impossible to reproduce in integration testing.

**Task:** Use VectorCAST's dynamic analysis features to detect any memory violations in the suspected module at unit test level.

**Action:**
- Enabled VectorCAST's memory bounds checking and uninitialized variable detection instrumentation.
- Re-ran the full unit test suite with these probes active.
- VectorCAST reported a write-beyond-buffer event in a CAN message parsing function when a specific message ID combination was used.
- The parsing function was writing 1 byte beyond a statically allocated buffer when the data length field of the CAN message was set to maximum (8 bytes).

**Result:**
- Root cause of the intermittent ECU reset confirmed at unit level.
- Fix was a one-line bounds check added to the parser.
- Field issue eliminated after software update. No further field resets reported.

---

### STAR Case 11: Code Coverage Baseline for a Legacy Module

**Situation:** A 15-year-old instrument cluster module was being integrated into a new platform. It had no unit tests and no coverage data. The platform required a minimum of 80% statement coverage before integration.

**Task:** Generate a baseline unit test suite for the legacy module and bring it to 80% statement coverage.

**Action:**
- Imported all 12,000 lines of legacy C source into VectorCAST.
- Used VectorCAST's automatic test case generation to create basic I/O boundary tests for all 127 public functions.
- Auto-generated 982 test cases. Executed. Coverage reached 59%.
- Identified the top 30 uncovered functions by coverage gap. Wrote targeted tests for each.
- Coverage plateau was due to 5 functions requiring hardware interrupts to trigger — documented separately.

**Result:**
- Statement coverage reached 83% without hardware dependencies.
- 5 interrupt-driven functions covered separately via HIL testing (documented in test plan).
- Integration approved. Legacy module deployed to new platform on schedule.

---

### STAR Case 12: Multi-Compiler Host/Target Coverage Comparison

**Situation:** A team discovered that their module passed 100% of VectorCAST tests on the x86 host but had 6 test failures on the real ARM target. The target used a different compiler (Arm Compiler 6) vs. host (GCC x86).

**Task:** Systematically compare host and target behavior and document all compiler-specific differences.

**Action:**
- Configured VectorCAST for both execution environments: x86 host and ARM target via RSP.
- Ran identical test suites on both environments.
- Used VectorCAST's result comparison report to identify divergences.
- Root cause: 6 tests relied on `int` being 32-bit (true on x86) but the ARM compiler used 16-bit `int` for the target.
- Added explicit type casts throughout the module: `uint32_t` instead of `int`.

**Result:**
- Host/target divergence eliminated.
- Policy updated: all new code must use explicit `stdint.h` types (uint8_t, uint32_t, etc.) — a MISRA Rule 4.6 requirement.

---

### STAR Case 13: VectorCAST for ASPICE SWE.4 Evidence

**Situation:** An ASPICE Level 2 gap assessment identified that the organization had no formal unit test specification documentation for its embedded SW modules (SWE.4 Base Practice 4.1: Develop software unit verification criteria).

**Task:** Use VectorCAST to generate ASPICE-aligned unit test specification and results documentation.

**Action:**
- Mapped each VectorCAST test case to a software unit requirement using VectorCAST's requirements link feature.
- Generated VectorCAST's "Test Case Specification" report — listing each test case, its purpose, inputs, expected outputs, and pass/fail status.
- Published the report as the formal "Software Unit Verification Specification" document in the project DMS.

**Result:**
- ASPICE SWE.4 gap closed. Evidence accepted by the ASPICE assessor.
- ASPICE Level 2 rating achieved for the software engineering process area.

---

### STAR Case 14: Parallel VectorCAST Execution on Multiple Build Agents

**Situation:** A platform with 24 software modules had a total unit test runtime of 47 minutes when run sequentially. The CI/CD pipeline was only viable if the total run was under 10 minutes.

**Task:** Parallelize VectorCAST execution across Jenkins build agents to meet the 10-minute CI gate requirement.

**Action:**
- Divided the 24 modules into 6 groups of 4.
- Configured Jenkins Matrix Build to run each group on a separate agent simultaneously.
- Used VectorCAST/Manage to merge the results from all 6 agents into a single consolidated report after execution.

**Result:**
- Total CI execution time: reduced from 47 minutes to **8.5 minutes** (6x speedup).
- CI gate requirement met. Nightly regression fully automated.

---

### STAR Case 15: Investigating a Suspected Defect Before Confirmation

**Situation:** A software defect was reported in a field vehicle. The defect report described a condition but the root cause was unconfirmed. Recreating it in system testing would require a 3-day test drive program.

**Task:** Use VectorCAST to reproduce and confirm the defect at unit test level within 1 day.

**Action:**
- Reviewed the defect description and identified the suspected function.
- Wrote a VectorCAST test case specifically parametrized to recreate the reported condition.
- Executed the test case. Confirmed: the function produced incorrect output under the reported conditions.
- Root cause identified: an unsigned subtraction produced wrap-around when the subtrahend exceeded the minuend.

**Result:**
- Defect confirmed and root cause identified in 2 hours, not 3 days.
- Fix verified with VectorCAST before deployment.
- Test case added to the permanent regression suite.

---

### STAR Case 16: VectorCAST Environment Rebuild After Compiler Upgrade

**Situation:** The project upgraded from GCC 9.4 to GCC 12.3. Half of the existing VectorCAST environments failed to build with the new compiler due to C18 strict mode changes.

**Task:** Rebuild and validate all 24 VectorCAST environments for the new compiler within one sprint.

**Action:**
- Ran `clicast manage --rebuild` on all 24 environments with the new compiler settings.
- 12 rebuilt cleanly. 12 failed due to deprecated GCC flags and new strict aliasing warnings treated as errors.
- Fixed each environment: updated compiler flags, resolved strict aliasing violations, updated type casts.
- Ran the full test suite after rebuild. 3 tests failed due to compiler-induced behavior changes.

**Result:**
- All 24 environments running on GCC 12.3 within 4 days.
- 3 tests fixed by correcting underlying type issues (which had been masked by the old compiler).
- Compiler upgrade process documented as a standard runbook.

---

### STAR Case 17: Demonstrating No-Regression After Safety-Critical Patch

**Situation:** A safety-critical patch was applied urgently to a braking ECU in response to a field issue. The patch needed to be validated and pushed to production within 48 hours.

**Task:** Use VectorCAST to demonstrate that the patch fixed the defect without introducing regressions, within the 48-hour window.

**Action:**
- Applied the patch to the relevant module.
- Ran the full VectorCAST test suite (340 tests) — all passed except the 2 tests designed specifically to reproduce the original defect (which now passed vs. previously failed).
- Generated a VectorCAST "Regression Test Results" report showing 340/340 tests passing, with the delta showing the 2 defect-specific tests moving from FAIL to PASS.
- Report submitted to the safety manager and the customer within 30 hours of patch delivery.

**Result:**
- Patch approved and deployed within the 48-hour window.
- No field regressions reported after patch deployment.
- Process used as the template for all future safety-critical emergency patches.

---

### STAR Case 18: Configuring VectorCAST for C++ Polymorphism Testing

**Situation:** A new ADAS module was developed in C++ using polymorphism (virtual functions, abstract classes). The team's VectorCAST setup was configured for C only and the C++ harness generation was failing.

**Task:** Configure VectorCAST/C++ correctly to test polymorphic C++ classes and achieve coverage of all virtual method implementations.

**Action:**
- Switched to VectorCAST/C++ project type (not VectorCAST/C).
- Configured the harness to instantiate concrete implementations of abstract interfaces.
- Used VectorCAST's "object factory" configuration to inject mock implementations of virtual base classes.
- Wrote test cases for all 3 concrete implementations of the abstract `ISensorHandler` interface.

**Result:**
- All 3 concrete implementations fully tested in isolation.
- 88% MC/DC coverage across all virtual method implementations.
- Team now self-sufficient in C++ VectorCAST configuration.

---

### STAR Case 19: Building a shared VectorCAST Library for Common Utilities

**Situation:** 8 modules all used the same set of utility functions (CRC calculation, bit packing, timer utilities). Each module had its own duplicate VectorCAST test environment for the utilities, causing 8x maintenance overhead.

**Task:** Consolidate utility function testing into a single shared VectorCAST sub-project, referenced by all 8 module projects.

**Action:**
- Created a standalone VectorCAST project for the utility library.
- Achieved 100% coverage on the utility library independently.
- Configured each of the 8 module projects to link against the utility library project (referencing its stub outputs) rather than re-testing the utilities.
- Updated VectorCAST/Manage to include the utility project in the platform-level rollup.

**Result:**
- Utility test maintenance reduced from 8 copies to 1.
- Total test suite size reduced by 847 duplicate test cases.
- Utility library coverage report centralized and referenced in all 8 module safety files.

---

### STAR Case 20: VectorCAST + Polyspace Integration for Deep Defect Detection

**Situation:** A safety manager required both dynamic test coverage (VectorCAST) and formal static verification (MathWorks Polyspace) for an ASIL D module. Running both tools independently was creating contradictory reports.

**Task:** Integrate VectorCAST and Polyspace results into a single combined V&V evidence view.

**Action:**
- Ran VectorCAST dynamic tests to achieve MC/DC coverage.
- Ran Polyspace Code Prover on the same module to identify proven-safe / unproven / defective code.
- Used Polyspace's results to identify functions that VectorCAST tests did not adequately probe (Polyspace flagged unproven array access — added 4 VectorCAST tests to exercise these).
- Combined the VectorCAST and Polyspace reports into a single V&V Summary for the safety file.

**Result:**
- 4 previously undetected array out-of-bounds risks identified by Polyspace and confirmed as reachable by VectorCAST tests.
- Fixes applied. Combined V&V report accepted by the external safety assessor.

---

### STAR Case 21: Measuring Test Effectiveness — Mutation Testing with VectorCAST

**Situation:** A team had 95% branch coverage but management questioned whether the test cases actually verified correct behavior or just executed code paths without meaningful assertions.

**Task:** Use VectorCAST's mutation testing capability to measure the fault-detection effectiveness of the existing test suite.

**Action:**
- Enabled VectorCAST's mutation testing mode.
- VectorCAST introduced 1,200 seeded code mutations (flipped boolean operators, changed comparison operators, mutated arithmetic).
- Ran the full test suite against each mutation. A "killed" mutation = the test suite detected the change.
- Mutation score: 78% of mutations were killed. 22% survived (test suite did not detect the change).

**Result:**
- 22% surviving mutations = test assertions too weak in certain areas.
- Targeted assertion improvements made for the 15 most critical surviving mutations.
- Final mutation score: 91%. Test quality demonstrably improved, independent of coverage %.

---

## 5. QUICK REFERENCE — VECTORCAST KEY COMMANDS

```bash
# Rebuild VectorCAST environment with new source
clicast -e my_env rebuild

# Run all test cases in an environment
clicast -e my_env test script run

# Generate coverage report
clicast -e my_env cover results aggregate

# Export JUnit-format results for CI
clicast manage --project project.vcm --report junit --output results.xml

# Run specific test case by name
clicast -e my_env test script run TestSuite.TestCase_001
```

---

## 6. INTERVIEW PREPARATION — Top Questions

1. **How does VectorCAST stub external dependencies? What is the difference between auto-stubs and user-coded stubs?**
2. **What is basis path testing and how does VectorCAST use cyclomatic complexity to guide it?**
3. **How do you configure VectorCAST for on-target execution? What is RSP?**
4. **What is the VectorCAST/QA tool and when would you use it over the standard VectorCAST interface?**
5. **How does VectorCAST generate ISO 26262 evidence? What reports does it produce?**
6. **How would you integrate VectorCAST into a Jenkins pipeline with coverage gates?**
