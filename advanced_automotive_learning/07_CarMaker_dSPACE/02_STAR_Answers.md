# CARMAKER + dSPACE — STAR INTERVIEW STORIES
## Module 7 of 7 | 6 Ready-to-Use STAR Answers

---

## STAR-1: Catching an AEB Timing Bug That Only Appeared on HIL

**Situation:**
SIL testing showed AEB activated at the correct TTC with 100% pass rate. But when the same scenario was run on the HIL bench with the real ADAS ECU and SCALEXIO, AEB activated 150ms late — outside the 100ms tolerance — in 30% of runs.

**Task:**
Determine why SIL passed while HIL failed, since the same algorithm and scenario were being used.

**Action:**
1. Compared SIL and HIL timing logs side by side: SIL showed brake request at t=1.850s; HIL showed brake request at t=2.001s for the same scenario. Delta = 151ms.
2. HIL is real-time at 1ms steps; SIL runs faster-than-real-time with no timing constraints. Suspected the real ECU's CAN scheduling was introducing latency not present in SIL.
3. Traced the CAN message path: radar object list was sent every 20ms (50Hz) on HIL. In SIL, radar data was synchronous with the algorithm step (1ms). On HIL, worst-case radar data could be 20ms stale when AEB evaluation ran.
4. Additionally found that the ADAS task ran at 20ms cycle — but was scheduled after the radar CAN receive task. In worst case: radar arrives at t=0ms, ADAS evaluates at t=40ms (20ms radar delay + 20ms ADAS step) = 40ms latency vs. 1ms in SIL.
5. Fix: set the ADAS task to run immediately after the radar receive interrupt instead of at the fixed 20ms tick. This reduced latency from up to 40ms to < 2ms.

**Result:**
AEB timing variance: reduced from ±150ms to ±8ms on HIL. 100% pass rate restored. Lesson documented: SIL timing is not representative of ECU real-time scheduling — HIL is required to validate timing requirements. This finding was added to the project SIL→HIL transition checklist.

---

## STAR-2: Automating a 60-Scenario ADAS HIL Test Suite Overnight

**Situation:**
The ADAS HIL test suite had grown to 60 scenarios (Euro NCAP + internal edge cases). Each scenario took 3–5 minutes of manual setup: load TestRun, monitor for pass/fail, record result, load next TestRun. Running all 60 scenarios took 2 engineers a full day. This blocked releasing software updates quickly.

**Task:**
Automate the 60-scenario HIL test suite to run unattended overnight and deliver a pass/fail report by morning.

**Action:**
1. Built a Python test orchestrator using: CarMaker TCP API (load/start/stop TestRun, read quantities), ControlDesk COM API (read ECU signals, check pass criteria), and pytest for test organization.
2. Each scenario was defined in a YAML config: {testrun_name, timeout_s, pass_criteria: {AEB_BrakeReq: {expected: 1, tolerance_ms: 100}}}.
3. The orchestrator: loaded TestRun → started simulation → waited for end → read measured AEB activation timing from ControlDesk → compared to criteria → logged result.
4. Added parallel scenario execution for independent scenarios (SIL scenarios run on a second server in parallel with HIL).
5. Set up Jenkins job: triggered by software build completion → runs overnight → emails HTML report at 7am.

**Result:**
Test execution time: 60 scenarios in 3.5 hours unattended (vs. 8+ hours with 2 engineers). First run caught 3 regressions before morning code review. 30% of development-cycle time previously spent on manual HIL testing recovered. Used as a template for 2 other vehicle platforms.

---

## STAR-3: Diagnosing a Task Overrun During Rain Scenario

**Situation:**
During HIL ADAS testing with CarMaker rain weather model active, SCALEXIO was logging task overruns (CPU usage > 90%) approximately every 5 seconds. The HIL system was not producing reliable test results.

**Task:**
Identify the model component causing the overrun and resolve it without compromising rain scenario fidelity.

**Action:**
1. Used SCALEXIO Task Manager (via ControlDesk) to profile model CPU usage. The "WeatherModel" block was consuming 35% of the 1ms time budget alone — 3× higher than in dry-weather tests.
2. Root cause: the rain weather model was computing light scattering using a full ray-tracing algorithm for each of 1,000 raindrops per frame. This computation did not scale well with rain density.
3. The rain model detail was not needed for ADAS sensor simulation (we were using object-level injection, not raw signal injection). The rain effect on radar was being applied as a separate degradation factor.
4. Solution: disabled the high-fidelity rain rendering in the CarMaker visual model (used for camera image generation only). Kept the radar signal degradation model (simple gain reduction — very low CPU cost).
5. CPU utilization dropped from 90% to 52%. Zero task overruns.

**Result:**
Stable rain scenario execution. 18 previously-overrunning test cases re-run successfully. Decision documented: high-fidelity camera rendering in CarMaker should only be enabled when camera perception testing is in scope. For radar/AEB HIL testing, use simplified visual model.

---

## STAR-4: Building a Fault Injection Suite for Safety Validation

**Situation:**
Our ADAS safety case required testing 12 defined fault conditions (radar dropout, CAN timeout, power supply dip, etc.) for ISO 26262 ASIL-D compliance. These tests had never been automated — they were performed manually by connecting/disconnecting cables, which was inconsistent and could damage hardware.

**Task:**
Build a software-controlled fault injection suite that triggers all 12 faults safely and repeatably, producing evidence for the ISO 26262 safety case.

**Action:**
1. Designed fault injection architecture: used a relay matrix board (controlled by SCALEXIO DS4330) to intercept each fault circuit. Software-commanded fault injection = no physical cable handling.
2. For bus-level faults (CAN dropout): implemented in SCALEXIO Simulink model — a switch block interrupts CAN message forwarding when the fault command is asserted.
3. For power faults: used a programmable power supply (Keysight N6705C) controlled via GPIB/Python to apply voltage dips.
4. Wrote a Python test runner: for each fault condition, load the CarMaker AEB scenario → assert the fault at t=1.0s → measure ECU response (time-to-DTC, time-to-safe-state, whether AEB was inhibited) → log to JSON.
5. Added safety interlocks: fault injection blocked if vehicle speed > 0 in the CarMaker model (prevents injecting faults during an active AEB event — could cause runaway test).

**Result:**
12 fault conditions tested fully automated with reproducible timing. Safety case evidence: test logs with timestamps accepted by ISO 26262 assessor as valid evidence. 2 faults revealed: CAN dropout inhibit transition was 280ms (required: < 250ms) and power dip < 8V caused ECU to enter boot rather than safe state. Both fixed before SOP.

---

## STAR-5: CarMaker Scenario Library for Euro NCAP Preparation

**Situation:**
Our vehicle was 4 months from Euro NCAP testing. Internal ADAS HIL results were close to 5-star but we had identified 3 edge cases in CarMaker simulation where AEB performance was marginal. We needed to iterate rapidly on algorithm calibration before the real test track.

**Task:**
Build a systematic Euro NCAP scenario library in CarMaker to enable rapid calibration iteration, with quantitative scoring aligned with Euro NCAP methodology.

**Action:**
1. Mapped all Euro NCAP ADAS test scenarios to CarMaker TestRuns: 6 AEB City speeds (10–60 km/h), 5 AEB Interurban speeds, 3 pedestrian scenarios, 2 cyclist scenarios. Total: 16 TestRuns.
2. For each scenario: configured CarMaker road geometry (straight road, correct surface), traffic object (GVT, pedestrian dummy model), initial speed, target deceleration per Euro NCAP specification.
3. Added a scoring function: mirrored the Euro NCAP algorithm — collision avoided = full score; speed at impact < 25% of test speed = partial score; no mitigation = 0.
4. Built a calibration sweep tool: for each AEB threshold parameter (FCW_TTC, PARTIAL_BRAKE_TTC, FULL_BRAKE_TTC), swept ±10% in 1% steps and ran all 16 scenarios. Total: 30 × 16 = 480 scenario runs overnight.
5. Generated a heat map: x-axis = parameter value, y-axis = scenario, color = score. Identified optimal parameter values.

**Result:**
Euro NCAP simulation score: 5.5/6.0 (target was 5.0). On actual Euro NCAP test track: 5.3/6.0. The 3 marginal scenarios all passed after calibration. CarMaker scenario library adopted as the standard pre-test tool for all future programs.

---

## STAR-6: Explaining HIL Value to a Budget-Cutting Stakeholder

**Situation:**
A program manager proposed eliminating the HIL testing phase to save €300K and 6 weeks of schedule. His argument: "SIL already proves the algorithm. HIL just runs the same tests on expensive hardware."

**Task:**
Defend the value of HIL testing with data and business impact analysis, while remaining collaborative rather than defensive.

**Action:**
1. Pulled data from the previous 3 programs: counted defects found at each test level. MIL: 45, SIL: 28, HIL: 14, vehicle testing: 3, field: 0.
2. Key finding: of the 14 HIL-unique defects, 11 were related to timing (real ECU scheduling, CAN latency, interrupt priorities). Zero of these were catchable by SIL.
3. Cost modelling: average cost to fix a defect increases 10× per test level. HIL fix cost ≈ €5,000. Vehicle fix cost ≈ €50,000. Field fix (OTA + PR) ≈ €500,000+.
4. If we skip HIL: expected 11 timing defects to escape to vehicle testing = 11 × €50K = €550K additional cost. Skip HIL saving: €300K. Net: -€250K.
5. Presented this as a business decision: "Skipping HIL saves €300K upfront but is expected to cost €550K at vehicle level based on historical defect data. I recommend keeping HIL but reducing scope to 40 highest-risk scenarios instead of 60, saving €120K while retaining 85% of defect detection value."

**Result:**
Compromise accepted: HIL scope reduced from 60 to 40 scenarios (risk-prioritized). €120K saved. Program stayed on schedule. 9 of the expected 11 HIL-only defects were still caught within the reduced 40-scenario scope.

---

*Next: [03_Mini_Projects.md](03_Mini_Projects.md)*
