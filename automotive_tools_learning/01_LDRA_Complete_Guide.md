# LDRA Tool Suite — Complete Learning Guide
## Static Analysis, Code Coverage & Compliance for Automotive Embedded Systems

**Classification:** Internal Training Document  
**Date:** April 2026  
**Applicable Standards:** ISO 26262, MISRA C:2012, DO-178C, IEC 61508, ASPICE SWE.4/SWE.5

---

## 1. TOOL OVERVIEW

LDRA (Liverpool Data Research Associates) provides a suite of software verification tools used to enforce coding standards, measure test coverage, and demonstrate compliance in safety-critical embedded software development.

### Core Products
| Product | Function |
|---|---|
| **LDRAunit** | Unit testing framework for C/C++ embedded code |
| **TBvision** | Code visualization — call graphs, flow charts, data flow |
| **TBrun** | Test case generation and execution |
| **TBmisra** | MISRA C/C++ compliance checking |
| **TBcover** | Code coverage measurement (statement, branch, MC/DC) |
| **LDRA Testbed** | Full static and dynamic analysis integrated platform |

### Coverage Levels Supported
| Level | Description | ISO 26262 ASIL |
|---|---|---|
| **Statement Coverage (SC)** | Every line executed at least once | ASIL A |
| **Branch Coverage (BC)** | Every decision branch taken (true/false) | ASIL B |
| **MC/DC** | Modified Condition/Decision Coverage — every condition independently affects outcome | ASIL C, D |
| **Function Coverage** | Every function called | ASIL A |

---

## 2. ARCHITECTURE & WORKFLOW

```
┌─────────────────────────────────────────────────────────────────┐
│                        LDRA WORKFLOW                            │
│                                                                 │
│  Source Code (.c/.cpp)                                          │
│       │                                                         │
│       ▼                                                         │
│  [Static Analysis] ──► MISRA violations, metric violations      │
│       │                                                         │
│       ▼                                                         │
│  [Instrumentation] ──► LDRA inserts probes into source code     │
│       │                                                         │
│       ▼                                                         │
│  [Compilation + Execution on Target or Host]                    │
│       │                                                         │
│       ▼                                                         │
│  [Coverage Report] ──► Statement / Branch / MC/DC %            │
│       │                                                         │
│       ▼                                                         │
│  [Compliance Report] ──► ISO 26262 TQI, DO-178C artifacts      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. KEY CONCEPTS

### 3.1 MISRA C:2012 Enforcement
MISRA (Motor Industry Software Reliability Association) defines mandatory and advisory coding rules for safety-critical C/C++ code. LDRA checks all 143 MISRA C:2012 rules automatically.

**Example Violations LDRA Catches:**
- Use of dynamic memory allocation (Rule 21.3)
- Functions with multiple exit points (Rule 15.5)
- Implicit type conversions (Rule 10.x family)
- Unreachable code paths (Rule 2.1)

### 3.2 MC/DC Coverage — The ISO 26262 ASIL D Standard
Modified Condition/Decision Coverage requires that every condition in a compound boolean decision independently affects the outcome, with all other conditions held constant.

**Example:**
```c
if (speed > 100 && brake_pressure > 50) {  // Decision with 2 conditions
    apply_emergency_brake();
}
```
For MC/DC: you need test cases where:
- `speed > 100` is TRUE, `brake_pressure > 50` varies (TRUE/FALSE) → outcome changes
- `brake_pressure > 50` is TRUE, `speed > 100` varies (TRUE/FALSE) → outcome changes

### 3.3 Test Qualification Interface (TQI)
LDRA produces a TQI report that maps test coverage results directly to ISO 26262 Table 11 requirements, providing the traceability evidence required for a safety audit.

---

## 4. STAR CASES — 20+ Real-World Scenarios

---

### STAR Case 1: MISRA Compliance Baseline for BMS Software

**Situation:** A Battery Management System (BMS) software module had been developed by a team of 8 engineers over 18 months without enforced MISRA rules. The software was approaching ASIL B certification review.

**Task:** Establish a MISRA C:2012 compliance baseline and reduce violations to zero for the safety-critical files before the ISO 26262 Part 6 audit.

**Action:**
- Imported all ~40,000 lines of BMS source code into LDRA Testbed.
- Executed initial MISRA scan. Identified **3,847 violations** across 180 files.
- Categorized violations by severity: 212 mandatory, 1,204 required, 2,431 advisory.
- Created a deviation report template for justified advisory rule violations.
- Ran weekly enforcement scans, using LDRA's violation trend report to track progress.
- Added LDRA static analysis as a mandatory CI gate — build fails if any mandatory violation is introduced.

**Result:**
- Mandatory and required violations reduced to **0** within 10 weeks.
- Advisory violations documented with 47 formal deviation records accepted by the safety manager.
- ASIL B certification audit passed. MISRA compliance evidence submitted as part of the safety case.

---

### STAR Case 2: Achieving MC/DC Coverage for ASIL D Braking Module

**Situation:** An electronic braking control unit (ECU) contained a 2,400-line safety function responsible for distributing brake force across axles. The function was ASIL D and required 100% MC/DC coverage per ISO 26262 Part 6.

**Task:** Design a test suite that provably achieves MC/DC coverage for all 87 decisions in the module, demonstrable in the LDRA coverage report.

**Action:**
- Used LDRA TBvision to generate control flow graphs for each function, identifying all compound decisions.
- Used LDRA TBrun to auto-suggest MC/DC test case pairs for each boolean condition.
- Built 340 test cases in LDRAunit, exercising each condition in isolation per MC/DC rules.
- Cross-referenced coverage report with requirement traceability matrix in IBM DOORS.

**Result:**
- 100% MC/DC coverage achieved and verified via LDRA TQI report.
- Coverage evidence accepted by the TÜV SÜD assessor without additional testing.
- Test suite execution time: 4.2 minutes on the embedded target, enabling nightly regression.

---

### STAR Case 3: Reducing Dead Code in AUTOSAR Legacy Module

**Situation:** A legacy AUTOSAR SWC (Software Component) inherited from a previous platform contained large sections of code that were never executed during any test run. This posed a traceability risk during an ASPICE SWE.4 review.

**Task:** Identify all unreachable/dead code paths using LDRA, document them, and either remove or justify every unreachable segment.

**Action:**
- Ran LDRA statement coverage analysis using the full system test suite as stimulus.
- Identified 1,143 lines (8.7% of the module) that were never executed — flagged in red in TBvision.
- Reviewed each uncovered path: 723 lines were genuinely unreachable (defensive null pointer guards that could never trigger given the call hierarchy).
- Collaborated with the software architect. Removed 723 lines of confirmed dead code after peer review.
- Remaining 420 uncovered lines were defensive exception handlers — documented with formal justification records.

**Result:**
- Module reduced by 5.7% in size. Improved worst-case execution time (WCET) by 3%.
- ASPICE SWE.4 coverage evidence accepted. Dead code register submitted to the safety manager.

---

### STAR Case 4: CI/CD Integration of LDRA into Jenkins Pipeline

**Situation:** A cross-functional embedded software team was running LDRA manually on a weekly basis. Results were inconsistently applied, and there was a 3-week delay between code commit and MISRA violation discovery.

**Task:** Automate LDRA static analysis and coverage reporting as a mandatory gate in the Jenkins CI/CD pipeline so every commit is checked within minutes.

**Action:**
- Used LDRA's command-line interface (CLI) to script Testbed project execution headlessly.
- Integrated the LDRA CLI command into a Jenkins declarative pipeline stage called `static-analysis`.
- Configured the pipeline to fail the build if any new mandatory MISRA violation was introduced (delta analysis mode).
- Published LDRA HTML coverage reports as Jenkins build artifacts via the HTML Publisher plugin.
- Set up email alerts to the relevant module owner on any new violation.

**Action (Pipeline Snippet):**
```groovy
stage('LDRA Static Analysis') {
    steps {
        sh 'ldra_cmd --project bms_module.ldra --rules MISRA_C_2012 --report html --fail-on mandatory'
    }
    post {
        always {
            publishHTML([reportDir: 'ldra_reports', reportFiles: 'index.html', reportName: 'LDRA Report'])
        }
    }
}
```

**Result:**
- MISRA violation discovery time reduced from 3 weeks to **under 6 minutes**.
- New mandatory violations dropped to zero within the first sprint of enforcement.
- The approach was adopted by 4 other teams in the organization.

---

### STAR Case 5: Branch Coverage Improvement for Motor Control Module

**Situation:** A motor control algorithm had only 41% branch coverage. The project was 2 weeks from a customer review, and the contractual requirement was 85% minimum.

**Task:** Increase branch coverage from 41% to ≥85% within 10 working days.

**Action:**
- Used LDRA TBvision to display the uncovered branches as a visual control flow map.
- Identified the top 25 uncovered branches by priority (safety-critical paths first).
- Wrote 180 new unit test cases in LDRAunit targeting specific uncovered branches, especially error-handling and boundary conditions.
- Focused particularly on branches guarding against division by zero, invalid sensor inputs, and overflow conditions.

**Result:**
- Branch coverage reached **91.4%** in 8 working days.
- Remaining uncovered branches were formally justified (hardware-triggered fault paths tested via fault injection, not unit tests).
- Customer review passed. Coverage evidence added to the product safety file.

---

### STAR Case 6: Multi-Compiler Coverage Merge for Embedded Target

**Situation:** An ECU software module was developed using two compilers — IAR for application code and GCC for a low-level hardware abstraction layer. Coverage data could not be merged in standard tools because of the dual-compiler environment.

**Task:** Use LDRA to instrument both codebases and produce a single, unified coverage report for the complete software stack.

**Action:**
- Configured LDRA Testbed separately for IAR and GCC targets, with project-specific compiler profiles.
- Instrumented each codebase with LDRA probes.
- Executed tests on the physical ECU target, collecting execution traces from both environments.
- Used LDRA's merge utility to combine two trace files into a single unified project coverage view.

**Result:**
- Single unified coverage report delivered to the safety manager for the first time.
- Revealed a critical gap: the GCC HAL layer had only 34% coverage, despite the IAR application layer showing 94%.
- Additional 80 hardware-layer tests added, raising HAL coverage to 87%.

---

### STAR Case 7: Compliance Package Preparation for ISO 26262 Audit

**Situation:** The organization was undergoing an ISO 26262 Part 6 certification audit by an external assessor for an ASIL C transmission control ECU.

**Task:** Prepare the complete software verification evidence package using LDRA, mapping all test coverage data to the ISO 26262 clause requirements.

**Action:**
- Generated LDRA TQI (Test Quality Index) reports for all safety-critical modules.
- Exported LDRA's traceability matrix linking requirements (from DOORS) to test cases to coverage results.
- Produced LDRA's ISO 26262-specific compliance report as a standalone evidence document.
- Cross-referenced with the Safety Analysis (FMEA) to ensure high-criticality functions had MC/DC evidence.

**Result:**
- Auditor accepted all LDRA-generated evidence without requesting additional testing.
- Zero Non-Conformance Reports (NCRs) raised against the software verification activities.
- Certificate of compliance issued for the ASIL C ECU.

---

### STAR Case 8: Unit Test Generation for Untested Legacy Code

**Situation:** 60% of a body control module (BCM) codebase had no unit tests. The module was 8 years old and was being integrated into a new vehicle platform requiring ASPICE Level 2 evidence.

**Task:** Generate a baseline unit test suite using LDRA TBrun to bring coverage to a starting point without manually writing 2,000+ test cases from scratch.

**Action:**
- Used LDRA TBrun's automatic test case generation feature to create initial test stubs for all 214 functions.
- Auto-generated 1,847 test cases covering boundary values, nominal values, and null pointer inputs.
- Executed the auto-generated suite to get baseline coverage metrics.
- Manually enhanced the 40 most safety-critical functions with hand-crafted tests to increase MC/DC coverage.

**Result:**
- Starting baseline: 0% coverage. After automation: 58% statement, 41% branch.
- After manual enhancement of safety functions: 89% statement, 82% branch, 100% MC/DC on safety-critical paths.
- Time to baseline: 3 weeks. Estimated time if done fully manually: 18 weeks.

---

### STAR Case 9: LDRA on Cross-Platform Embedded Target (ARM Cortex-M4)

**Situation:** Team was struggling to run LDRA on-target for an ARM Cortex-M4 microcontroller due to limited RAM on the target device. LDRA's standard instrumentation overhead exceeded available memory.

**Task:** Configure LDRA for low-overhead execution tracing on a resource-constrained embedded target.

**Action:**
- Switched LDRA instrumentation mode from full function-level to compressed bit-field tracing.
- Used LDRA's "probe minimize" feature to reduce probe density by 60% while preserving branch coverage accuracy.
- Configured LDRA to offload trace data via UART at 921600 baud during test execution rather than storing on-chip.
- Wrote a Python script to capture UART trace output and feed it back into LDRA for coverage reconstruction.

**Result:**
- On-target RAM overhead reduced from 48KB to 11KB — within the 14KB budget.
- Full branch and MC/DC coverage reporting maintained.
- Technique documented as the team's standard procedure for constrained-target testing.

---

### STAR Case 10: Code Complexity Reduction via LDRA Metrics

**Situation:** A software module responsible for CAN message routing had a cyclomatic complexity score of 87 in one function (industry threshold for high risk: >10). This was flagged by LDRA's metric analysis.

**Task:** Use LDRA metrics data to guide a refactoring effort to reduce complexity below the project threshold of 15.

**Action:**
- Used LDRA TBvision to generate a visual call graph and highlight the function in question.
- Identified 6 nested decision structures that could be extracted into separate functions.
- Refactored the function into 9 smaller functions, each with complexity ≤8.
- Re-ran LDRA metrics post-refactoring to confirm all functions were within threshold.
- Re-ran the full test suite to confirm no regressions were introduced.

**Result:**
- Maximum cyclomatic complexity per function: reduced from 87 to 8.
- Test suite still passed 100%. No regressions.
- Code review time for the module decreased by an estimated 40% per reviewer feedback.

---

### STAR Case 11: Detecting Type Conversion Defects via MISRA Enforcement

**Situation:** A fuel injection timing module was exhibiting intermittent overflow behavior in production vehicles. Static analysis had not been run on the module in 2 years.

**Task:** Use LDRA MISRA enforcement to identify the root cause of the overflow defect.

**Action:**
- Ran full MISRA C:2012 scan on the module using LDRA Testbed.
- Identified 11 violations of MISRA Rule 10.1 (implicit conversion of integer types).
- Found that a `uint8_t` variable was being silently promoted to `int` in an arithmetic expression, causing unexpected behavior when the result exceeded 255.
- Fixed all type conversion violations with explicit casts and re-tested.

**Result:**
- The overflow defect was confirmed as caused by an implicit `uint8_t` → `int` → `uint8_t` conversion.
- Fix deployed. Intermittent issue eliminated in field.
- MISRA scanning added to the module's mandatory pre-release checklist.

---

### STAR Case 12: Proof of Coverage for Functional Safety Argument

**Situation:** A safety argument in the ISO 26262 Safety Case for an adaptive cruise control (ACC) ECU claimed that all safety-relevant requirements were "adequately tested." The auditor challenged this claim as unsubstantiated.

**Task:** Substantiate the safety argument with quantitative, tool-generated coverage evidence.

**Action:**
- Used LDRA to generate a requirement-to-test traceability report that linked each safety requirement (tagged in DOORS) to the test case IDs that exercised it.
- Generated the LDRA TQI report showing MC/DC coverage percentage per safety function.
- Mapped each ACC safety requirement to its corresponding LDRA coverage result.

**Result:**
- Auditor's challenge resolved. Safety argument upgraded from qualitative to quantitative.
- All 34 safety-critical functions showed ≥95% MC/DC coverage.
- Safety Case accepted without further challenge.

---

### STAR Case 13: Parallel LDRA Execution Across Teams

**Situation:** 4 separate sub-teams working on different ECU modules of a powertrain platform needed to produce combined coverage reports for a joint sprint review.

**Task:** Set up a shared LDRA server environment enabling parallel multi-team execution with a single consolidated coverage dashboard.

**Action:**
- Deployed LDRA in client-server mode with a central Testbed server accessible via VPN.
- Each team published their coverage results to the shared server project after nightly test runs.
- Configured LDRA's project merge feature to aggregate results from all 4 sub-projects into a master platform coverage view.
- Set up an automated HTML dashboard updated every morning.

**Result:**
- Sprint review conducted with a single, complete platform coverage report for the first time.
- Management could see coverage per module, per team, per ASIL level in one view.
- Inter-team test gap discussions reduced review meetings from 2 hours to 30 minutes.

---

### STAR Case 14: LDRA for DO-178C Avionics — Cross-Industry Application

**Situation:** The organization expanded from automotive into avionics software. A DO-178C DAL B certification project required structural coverage evidence identical to MC/DC.

**Task:** Reuse the team's existing LDRA expertise and adapt the toolchain for DO-178C requirements.

**Action:**
- Configured LDRA for DO-178C operational profile (different rule set from MISRA, different coverage levels).
- Mapped LDRA's existing MC/DC capability directly to DO-178C DAL B structural coverage requirements (identical standard).
- Generated DO-178C-specific traceability reports linking test procedures to code coverage.

**Result:**
- Zero ramp-up time for the team on the new standard.
- DO-178C qualification evidence generated within the first sprint.
- Cross-industry competency established — firm could now serve aerospace clients.

---

### STAR Case 15: Detecting Null Pointer Dereferences Before Integration

**Situation:** During a system integration test, a null pointer dereference caused the ECU to hard-fault. The defect had survived 4 weeks of functional testing but was not caught at the unit test level.

**Task:** Introduce LDRA analysis that would catch null pointer paths before unit tests reach integration.

**Action:**
- Enabled LDRA's dynamic analysis probes for null pointer and array-out-of-bounds detection.
- Re-ran all unit tests with LDRA instrumentation. LDRA flagged 3 functions where a null pointer return path was never exercised.
- Added specific test cases to exercise those null paths.
- Null pointer dereference was found and fixed at the unit test stage on re-run.

**Result:**
- Integration defect class eliminated from future code.
- Null pointer analysis added as standard to the module's test policy.
- Defect removal cost: £200 (unit test fix) vs. £14,000 (estimated cost of a system-level regression and root cause investigation).

---

### STAR Case 16: Customer Audit Support with LDRA Evidence Package

**Situation:** A major OEM customer demanded a full software V&V evidence package for a Tier-1 supplier's ECU, including code coverage data, static analysis results, and test case traceability.

**Task:** Compile a complete LDRA evidence package ready for customer review in 5 working days.

**Action:**
- Ran LDRA full suite analysis (MISRA, coverage, metrics, traceability) on all 62 software files.
- Generated 6 reports: MISRA summary, violation detail, branch coverage, MC/DC coverage, TQI report, and requirement traceability matrix.
- Packaged all reports in a structured evidence folder with a README explaining each document.
- Added LDRA tool qualification evidence (LDRA is a qualified tool under ISO 26262 — no further qualification required).

**Result:**
- Package delivered within 3 working days. Customer OEM accepted without rejections.
- Contract renewal confirmed 2 weeks later. Evidence package cited as a differentiator.

---

### STAR Case 17: Ensuring No Regression in Coverage After Refactoring

**Situation:** A software refactoring effort to simplify a state machine unintentionally reduced branch coverage from 91% to 74%, discovered 2 weeks after the refactoring was merged.

**Task:** Establish a LDRA coverage regression gate so that future refactoring cannot reduce coverage below the baseline without explicit approval.

**Action:**
- Captured the current coverage baseline in a LDRA snapshot report.
- Added a Jenkins pipeline stage that compared new coverage metrics to the snapshot.
- If any module's coverage dropped more than 2% from baseline, the build was halted and a notification sent to the team lead.
- Wrote a simple Python script to parse LDRA's XML output and compute delta against the snapshot baseline.

**Result:**
- Coverage regression gate blocked 2 subsequent accidental coverage drops in the next 3 months.
- Both blocked builds were investigated and test cases added before merge.
- Coverage stability maintained at ≥90% branch for the remainder of the project.

---

### STAR Case 18: Introducing LDRA to a Team with No Prior Experience

**Situation:** A newly formed team of 12 junior engineers had no exposure to static analysis or coverage tooling. They were joining an ISO 26262 project requiring ASIL B evidence.

**Task:** Train the team on LDRA fundamentals and get them independently running analyses within 2 weeks.

**Action:**
- Designed a 3-day internal training program:
  * Day 1: MISRA rules — what they are, how to read violation reports, how to fix them.
  * Day 2: Coverage concepts — statement, branch, MC/DC, hands-on with LDRAunit.
  * Day 3: End-to-end workflow — running analysis, reading TQI, preparing evidence.
- Created a simplified "starter project" in LDRA Testbed with a 500-line training codebase.
- Each engineer ran the full pipeline end-to-end and submitted their coverage report.

**Result:**
- All 12 engineers passed the internal competency assessment.
- First project sprint saw MISRA compliance enforced from day one.
- Training material formalized into the organization's onboarding guide for new engineers.

---

### STAR Case 19: LDRA for Safety Element out of Context (SEooC)

**Situation:** A software module was being developed as a Safety Element out of Context (SEooC) — meaning it needed to be validated independently of the final system integration, capable of claiming ASIL B conformance.

**Task:** Use LDRA to generate all software verification evidence needed to support the SEooC safety case independent of the system it would eventually integrate into.

**Action:**
- Developed a complete LDRAunit test suite for all SEooC module interfaces.
- Achieved 100% MC/DC coverage on all safety-relevant functions (ASIL B requires 100% MC/DC on safety functions per ISO 26262 Table 11, method 1c).
- Generated LDRA TQI report specifically tagged to the SEooC context.
- Documented all assumptions on use (AoU) in the SEooC documentation package.

**Result:**
- SEooC safety case accepted by the assessor. Module sold to 3 different OEM customers independently.
- Each OEM integration required no additional unit testing — they used the SEooC evidence directly.

---

### STAR Case 20: Automated Nightly LDRA Execution with Trend Reporting

**Situation:** Management needed visibility into coverage trends over time, not just point-in-time snapshots. Coverage was stalling at 71% branch for 3 sprints without anyone noticing.

**Task:** Build an automated nightly LDRA execution pipeline with trend visualization.

**Action:**
- Configured Jenkins to run LDRA full suite every night at 02:00.
- Parsed LDRA XML output with a Python script and stored coverage metrics in a SQLite database.
- Built a simple Grafana dashboard pulling from the database to show weekly coverage trend per module.
- Set up threshold alerts: if a module's coverage trend dropped 2+ consecutive weeks, the team lead received a Slack notification.

**Result:**
- Stalling coverage pattern discovered 3 days after dashboard launch (previously would have been found at a quarterly review).
- Root cause: new code was being added without corresponding test cases.
- Coverage trend reversed within 2 sprints after visibility was established.

---

### STAR Case 21: Integrating LDRA with IBM DOORS for Full Traceability

**Situation:** A project had separate tools for requirements (DOORS) and testing (LDRA) with no automated link between them. Auditors had to manually verify that every requirement had a test case.

**Task:** Automate the requirements-to-coverage traceability by integrating LDRA output with IBM DOORS.

**Action:**
- Used LDRA's DOORS integration module to export test case IDs linked to DOORS requirement IDs.
- Created DOORS attributes: `Covered_by_Test` and `LDRA_Coverage_%` fields on every requirement object.
- Wrote a DOORS DXL script to automatically populate these fields from the LDRA export file after each nightly run.

**Result:**
- Full requirements-to-coverage traceability automated.
- Audit previously took 2 days of manual cross-referencing; now ran automatically in 7 minutes.
- Zero untested requirements escaped to final review.

---

### STAR Case 22: Handling MISRA Rule Deviations Formally

**Situation:** A CAN driver module required use of `union` types for bit-field register map access, which violates MISRA C:2012 Rule 19.2. The code was correct and the violation was justified but undocumented.

**Task:** Establish a formal deviation management process for justified MISRA violations using LDRA's deviation handling capability.

**Action:**
- Used LDRA's built-in deviation management to formally classify the Rule 19.2 violation as a permitted deviation.
- Wrote a deviation justification note: "Union used for hardware register mapping per processor datasheet. Behavior is deterministic on this platform. Reviewed and accepted by Safety Manager."
- Tagged the deviation in LDRA so it no longer appeared as an open violation in compliance reports.
- Created a deviation register document listing all approved deviations with justification.

**Result:**
- MISRA compliance report no longer flagged the justified violation as open.
- Deviation register accepted by ASPICE assessor as evidence of a controlled process.
- Process scaled: 14 similar deviations across the project handled consistently.

---

## 5. QUICK REFERENCE — LDRA KEY COMMANDS

```bash
# Run MISRA C:2012 analysis on a project
ldra_cmd --project my_project.ldra --rules MISRA_C_2012 --report html

# Run coverage analysis and generate report
ldra_cmd --project my_project.ldra --coverage BRANCH,MCDC --report xml

# Delta analysis — only report NEW violations introduced since last run
ldra_cmd --project my_project.ldra --delta --fail-on mandatory

# Merge coverage from multiple sub-projects
ldra_cmd --merge sub1.ldra sub2.ldra --output merged_project.ldra
```

---

## 6. INTERVIEW PREPARATION — Top Questions

1. **What is the difference between branch coverage and MC/DC? When does ISO 26262 require MC/DC?**
2. **How do you handle MISRA violations that are technically justified but cannot be fixed?**
3. **How would you integrate LDRA into a CI/CD pipeline?**
4. **What is the TQI report and when is it used?**
5. **How does LDRA support an ASPICE SWE.4 review?**
6. **Explain how LDRA instruments source code and what overhead this introduces on an embedded target.**
