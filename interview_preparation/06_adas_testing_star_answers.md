# ADAS Testing — STAR Format Interview Answers

> STAR = **S**ituation → **T**ask → **A**ction → **R**esult
> Use these for behavioural and competency-based questions.
> Adapt the ECU/project names to your actual experience.

---

## 1. ACC — Adaptive Cruise Control

### "Tell me about a time you tested ACC and found a critical bug."

**S — Situation**
> During ADAS integration testing on a BYD Sealion 7 project, ACC was in its final
> validation phase before SOP. The feature had passed all component-level tests on HIL,
> but full vehicle testing was still pending. I was responsible for CAN-level signal
> validation using CANoe.

**T — Task**
> My task was to verify that ACC correctly deactivates and raises a fault when the forward
> radar signal is lost — a safety-critical requirement under ISO 26262 ASIL-B. The
> requirement stated: "ACC shall deactivate within 100ms of radar message timeout and
> log a U0401 DTC."

**A — Action**
> I wrote a CAPL script that sent normal radar target frames (0x300) at 20ms cycle for
> 5 seconds, then abruptly stopped, simulating a radar communication failure. I monitored
> the ACC status output message (0x502) for the fault bit and used the CANoe Diagnostic
> Console to check for U0401 after each run. On the third test run, I noticed the ACC
> fault bit was set correctly but the DTC was not logged — the ECU transition to
> session-less state was clearing the DTC automatically before it could be read.

**R — Result**
> I raised a P2 defect in JIRA with full CAN log, CAPL script, and timestamp analysis
> showing the DTC was being cleared within 80ms of being set. The root cause was a
> missing NvM write call in the diagnostic session transition handler. The SW team
> patched it in the next sprint. The fix was re-verified using the same CAPL script — DTC
> now persists correctly across sessions. This prevented a potential recall issue post-SOP.

---

## 2. LKA — Lane Keep Assist

### "Describe a situation where you had to validate a safety requirement for LKA."

**S — Situation**
> On a passenger vehicle project, the LKA feature had a safety requirement that it must
> NOT apply steering torque when the driver activates the turn signal. This was a known
> driver-override requirement from ISO 22178 and defined in the DOORS trace as
> REQ-LKA-007. During regression testing after a SW update, I was assigned to re-verify
> this requirement.

**T — Task**
> Re-verify that LKA steering torque output drops to zero within one control cycle
> (20ms) whenever TurnSignal is active — for both left and right signals, both during
> active correction and idle monitoring.

**A — Action**
> I created four test cases in CANoe using CAPL signal injection:
> 1. LKA actively correcting left drift → left turn signal injected → torque monitored
> 2. LKA actively correcting right drift → right turn signal injected → torque monitored
> 3. LKA idle (centered) → turn signal → ensure no latent torque spike
> 4. Turn signal removed mid-drift → torque resumes correctly
>
> For each, I captured the exact timestamp of TurnSignal rising edge vs
> LKA_TorqueRequest falling edge in the CANoe Graphics window and measured the delta.
> On test case 2, I found a 60ms delay — three control cycles — before torque dropped.

**R — Result**
> Filed a P1 defect (safety-critical regression) with timestamp analysis, CAN trace,
> and CAPL script attached. The delay was traced to a signal debounce filter that had
> been incorrectly applied to TurnSignal in the new SW build. The filter was removed,
> re-tested — torque now drops within 5ms (< 1 cycle). Test case closed as PASS.
> Requirement REQ-LKA-007 re-verified and signed off in DOORS.

---

## 3. BSD — Blind Spot Detection

### "Give me an example of a time you tested a warning system that involved multiple ECU interactions."

**S — Situation**
> BSD warning on a mid-range SUV project required coordination between three ECUs:
> the rear-corner radar ECU (sends target data), the ADAS ECU (processes and decides),
> and the cluster ECU (displays mirror warning and plays chime). During system integration
> testing, it was reported that the chime was playing even when no target was actually
> present in the blind spot — a false positive that could erode driver trust.

**T — Task**
> Isolate which ECU was responsible for the false chime — was it incorrect target
> detection by the radar ECU, incorrect processing by the ADAS ECU, or incorrect
> triggering logic in the cluster ECU?

**A — Action**
> I took a three-layer approach using CANoe:
> 1. **Radar ECU isolation**: Captured BSD_Left_Target signal (0x330) in Trace — confirmed
>    it was correctly showing 0 (no target) during the false chime events.
> 2. **ADAS ECU isolation**: Monitored BSD_WarnLeft output (0x520). Found it was pulsing
>    0→1→0 briefly every ~2 seconds even with no target — this was the source.
> 3. **Root cause**: Used CANoe Statistics to check message timing. BSD_Left_Target
>    message from radar ECU had a 200ms gap (timeout) under high bus load. The ADAS ECU
>    treated a missing message as "unknown" and momentarily set the warning flag while
>    re-querying — the spec said it should hold last-known state, not trigger warning.

**R — Result**
> Root cause confirmed: missing timeout handling in ADAS ECU — it should hold the last
> valid target state for 500ms before flagging "no data." Raised P2 defect with CAN
> bus load analysis, timing screenshots, and a CAPL script that reproduced the issue
> by injecting a 200ms gap in BSD radar messages. Fix implemented and verified — chime
> now requires 3 consecutive valid target frames before activating, which eliminated
> the false positive completely.

---

## 4. DMS — Driver Monitoring System

### "Tell me about a time you had to test a feature where the test environment was difficult to set up."

**S — Situation**
> DMS relies on infrared camera data to detect drowsiness. On a real vehicle, you need
> a human driver with controlled eye closure — impossible to repeat precisely. On HIL,
> the camera data would need a real IR camera pointed at a face, which was not available
> in our lab. The test needed to be repeatable, automated, and independent of human
> subjects for regression testing.

**T — Task**
> Design an automated DMS test that could be run in CANoe without a camera, without a
> human driver, and produce consistent, repeatable results — covering the full warning
> escalation from Level 1 (visual) to Level 3 (haptic + brake).

**A — Action**
> I worked with the DMS ECU team to understand the CAN interface: the camera processes
> the IR image internally and sends pre-processed parameters (EyeClosure%, GazeDirection,
> HeadPose_Yaw) over CAN (0x340). I wrote a CAPL script that simulated these parameters
> directly — bypassing the camera hardware entirely. The script ramped `DMS_EyeClosure`
> from 10% to 95% over 10 seconds in 5% steps every 500ms, while keeping FaceDetected=1
> and GazeDirection=0 (forward head, eyes closing). I added assertion handlers on
> DMS_Warning_Level (0x530) to auto-log the exact eye closure percentage at which each
> warning level was triggered. I ran this 10 times per SW build for regression.

**R — Result**
> The automated script replaced 3 hours of manual testing per build cycle with a
> 12-minute automated run. It caught two regressions: one where the Level 2 threshold
> shifted from 70% to 55% eye closure (too sensitive — false alarms while blinking),
> and one where Level 3 never triggered due to a timer reset bug. Both were caught
> before vehicle testing. The script was adopted by the team as the standard DMS
> regression suite.

---

## 5. APS — Automatic Parking System

### "Describe a time you found a bug during parking system testing that was hard to reproduce."

**S — Situation**
> During APS validation on a BYD crossover project, the test team occasionally reported
> that APS aborted mid-maneuver with no obstacle present and no DTC logged. It happened
> roughly 1 in 20 test runs and only during reverse parallel parking — never during
> perpendicular parking. No one had been able to reliably reproduce it.

**T — Task**
> Reproduce the intermittent APS abort, identify the root cause, and provide a reliable
> reproduction script so the SW team could debug it.

**A — Action**
> I started by analysing .blf logs from the failed runs. Using CANoe's post-processing
> tools, I filtered for APS_Status transitions and searched for the 60 seconds before
> each abort. I noticed a pattern: the abort always coincided with a brief 40ms dropout
> on the USS_Side_R message (0x351) during the final steering correction phase. The
> dropout was caused by CAN bus overload from a concurrent OBD2 diagnostic poll that
> the test team ran in parallel.
> I wrote a CAPL script to reproduce it precisely: start APS maneuver, at the 8-second
> mark (matching the typical timing of the final correction) inject a 50ms gap in 0x351
> by suspending its output for one timer cycle. This reproduced the abort 100% of the time.

**R — Result**
> Root cause: APS ECU treated a single-cycle USS timeout as a sensor fault and aborted
> — per spec, it should tolerate up to 3 consecutive missing frames before aborting.
> I documented the reproduction CAPL script, the CAN log analysis, and the spec
> reference in JIRA. SW team patched the timeout tolerance from 1 to 3 frames. Verified
> with the same script — APS now tolerates the 50ms gap and completes the maneuver
> successfully. Issue closed as resolved.

---

## 6. PCW — Pedestrian Collision Warning / AEB-P

### "Tell me about your involvement in safety testing for an AEB feature."

**S — Situation**
> AEB for pedestrians (AEB-P) on a hatchback project was undergoing pre-SOP safety
> validation. The feature had an ISO 22737 reference and required AEB-P to activate
> within 150ms of a pedestrian entering the critical zone (< 8m, in-path). I was
> responsible for ECU-level signal validation — the HIL team handled the full-speed
> vehicle model testing.

**T — Task**
> Verify the AEB-P activation latency requirement (<150ms from pedestrian crossing the
> 8m threshold to AEB_P_Active = 1) for 5 speed setpoints: 20, 30, 40, 50, 60 km/h.

**A — Action**
> I developed a CAPL script that:
> 1. Set VehicleSpeed to the target setpoint
> 2. Injected a pedestrian at 10m (outside threshold) and held for 2 seconds
> 3. At t=2s, stepped distance to 750cm (7.5m — inside 8m threshold) in one frame
> 4. Recorded the timestamp of that step (tTrigger)
> 5. In the `on message 0x551` handler (AEB_P_Active), recorded tActivation
> 6. Calculated latency = tActivation - tTrigger and logged PASS/FAIL vs 150ms limit
>
> I ran 10 iterations per speed setpoint (50 runs total), logging min/max/average latency.
> At 60 km/h I found an average latency of 142ms — inside the limit but with a max spike
> of 178ms (FAIL). The spike correlated with a specific CAN bus load condition.

**R — Result**
> Reported the latency spike as a P1 defect with statistical data (10-run latency chart),
> CAN bus load correlation, and the reproduction script. The ADAS ECU team identified
> a priority inversion in the real-time task scheduler that delayed the AEB decision task
> under high bus load. Task priority was elevated in the next build — maximum latency
> dropped to 128ms across all 50 runs. Requirement verified and closed. This finding
> was also escalated to the HIL team to add bus load as a test parameter in their
> scenario matrix.

---

## 7. General ADAS — Cross-Feature Scenarios

### "Tell me about a time you had to coordinate with multiple teams during ADAS testing."

**S — Situation**
> During system-level integration of ACC + AEB + LKA on a BYD Sealion 7 platform, a new
> bug was reported: when ACC was actively braking AND LKA was simultaneously applying
> steering correction, the vehicle responded with an unexpected CAN message flood that
> caused 200ms latency spikes across the ADAS bus. This was discovered during
> combined-feature testing, which had started only that week.

**T — Task**
> Identify which feature or ECU was causing the message flood, reproduce it reliably,
> and coordinate with the ACC, LKA, and gateway ECU teams to resolve it before
> the combined-feature integration milestone deadline (2 weeks away).

**A — Action**
> I set up a CANoe environment with three simultaneous signal injection streams:
> - ACC active: RadarTarget at 15m, ego speed 80 km/h (gentle braking scenario)
> - LKA active: Lane drift -200mm offset, torque correction active
> - Gateway monitoring: bus statistics window tracking message count per 100ms window
>
> I found the flood originated from the gateway ECU, which was re-routing ACC brake
> requests AND LKA torque requests to the chassis domain at the same instant, causing
> a retransmission storm due to a routing table conflict. I captured the exact message
> sequence in a .blf file and shared it with the gateway team with timestamps highlighted.
> I also created a simplified CAPL reproduction script (< 30 lines) so any team member
> could reproduce it without the full simulation setup.

**R — Result**
> Gateway team fixed the routing table conflict within 3 days using the reproduction
> script I provided. I re-ran the combined injection test — bus load returned to normal
> (<30% utilisation), latency spikes eliminated. The integration milestone was met on
> time. Post-incident, I proposed that combined-feature CAN bus load tests be added to
> the standard regression suite — this was approved and implemented for the next project.

---

### "Give an example of when you improved a testing process."

**S — Situation**
> On a previous project, ADAS regression testing was entirely manual. After each SW
> build, engineers would open CANoe, manually change signal values in the Graphics
> panel, observe the output, and write pass/fail in an Excel sheet. Each full regression
> cycle took 3 days for 6 features. With biweekly SW builds, the team was permanently
> behind.

**T — Task**
> Automate the ADAS regression test suite so that results could be generated within
> one working day per build, with consistent pass/fail criteria and no manual signal
> editing.

**A — Action**
> I built a library of CAPL test scripts, one per feature (ACC, LKA, BSD, DMS, APS, PCW),
> each covering the 3–5 most critical test cases per feature. Each script:
> - Injected signals automatically from `on start`
> - Evaluated pass/fail using `on message` handlers with threshold comparisons
> - Wrote results to a structured log file (PASS/FAIL with signal values and timestamps)
> - Ran in sequence using CANoe's test module framework (vTESTstudio-compatible)
>
> I documented a standard header template so new scripts could be added in under 1 hour.

**R — Result**
> Full regression run time reduced from 3 days to 4 hours. Once automated, a junior
> engineer could trigger the suite and collect results without ADAS domain expertise.
> Regression was run after every build instead of every two weeks — two regressions
> were caught that would have been missed under the old schedule. The script library
> was adopted as the project standard and used by two other teams on related platforms.

---

## Quick STAR Template (for adapting to any ADAS question)

```
S — SITUATION
  "On [project/feature], during [phase: integration/validation/HIL/vehicle testing],
   [context that creates the challenge]..."

T — TASK
  "My responsibility was to [specific action/requirement] —
   the key constraint was [time / safety level / spec requirement]."

A — ACTION
  "I [tool used: CANoe / CAPL / dSPACE / Python] to [what you did step by step].
   When I found [unexpected result], I [diagnostic step].
   The key insight was [technical finding]."

R — RESULT
  "[Quantified outcome: bug found / requirement verified / time saved].
   This was important because [impact on project / safety / team].
   As a follow-up, I also [improvement or lesson applied]."
```

> **Interview tips:**
> - Always name the tool (CANoe, CAPL, dSPACE) — interviewers want to know you can use it
> - Always include a number (150ms latency, P1 defect, 3-day reduction)
> - Always end with project impact — not just "I fixed it" but "this prevented X"
> - Keep each answer to 90–120 seconds when spoken aloud
