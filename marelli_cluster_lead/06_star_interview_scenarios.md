# STAR Interview Scenarios — Cluster Lead, Marelli / LTTS

> **Role:** Cluster Lead, L&T Technology Services → Marelli, Bangalore
> **Format:** Situation → Task → Action → Result
> **JD Coverage:** Validation leadership, CANoe/CAPL, CAN log analysis, defect management,
>                  team handling, OEM communication, mentoring, Python automation

---

## STAR 1 — Leading End-to-End Cluster Validation (Core Leadership)

### Situation
I was leading the Instrument Cluster validation for a B-segment vehicle platform with a Japanese OEM. The project had 320 test cases covering speedometer, telltales, NVM, CAN timeout behaviour, and DIS features. We were 3 weeks from the customer gateway review, and my team of 4 engineers had only executed 40% of test cases. The previous lead had left the project.

### Task
Take full ownership of the validation programme: re-plan execution, re-allocate tasks by skill level, maintain quality, and deliver the gateway with all P1/P2 defects closed — within the 3-week window.

### Action
1. **Assessment (Day 1):** Audited all 320 TCs. Classified: 40 TCs were CAPL-automated (fast), 180 manual (medium effort), 100 required hardware intervention (bench change, slow). Identified 12 TCs had missing preconditions — sent back for rework.

2. **Re-planning:** Using capacity calculation (4 engineers × 5 days × 6h = 120h/week), I re-sequenced work:
   - Automated CAPL TCs run first by one engineer (Suresh) — could execute 15/day
   - Manual gauge tests assigned to two mid-level engineers in parallel
   - Hardware-dependent NVM/power-mode tests batched at bench using a booking schedule

3. **Daily reviews:** 15-min standups. I created an execution tracker (Excel + Jira) visible to all. Each failing TC got a defect raised same day.

4. **Defect triage:** Called a biweekly triage with ECU owners. CLU-1024 (ABS telltale not activating) was escalated to P1 — I personally traced the CAN log, found the signal bit position mismatch between the DBC we used and the cluster ECU's internal definition, narrowed it to a DBC version mismatch (v2.2 vs v2.3), and provided the exact reproduction steps with log evidence, which shrank the SW fix time from 5 days to 2.

5. **OEM communication:** Prepared and delivered weekly status reports with colour-coded risk flags. All open items were tracked with mitigation plans.

### Result
- Executed all 320 TCs in 3 weeks (vs 18 TCs/day target — achieved 22 TCs/day average)
- Gateway review passed with **zero P1 open defects** and only 4 minor open P3 items
- Customer gave positive feedback on report clarity and defect depth
- Project delivery was on-time with zero scope reduction

---

## STAR 2 — CAPL Automation Reducing Manual Effort by 65% (CAPL / Test Design)

### Situation
During a cluster validation project, telltale testing was entirely manual. An engineer had to physically press buttons, inject CAN signals, observe the cluster, and write results. For 60 telltale TCs, this took 3 days minimum — prone to human error and not repeatable.

### Task
Design and implement a CAPL-based automated telltale test suite that could execute all 60 telltale tests in under 4 hours with auto-pass/fail logging.

### Action
1. **Analysis of test cases:** Each telltale test followed the same pattern:
   - Inject fault CAN signal → Wait N ms → Read telltale status via UDS → Compare → Log.

2. **Designed a reusable CAPL test framework:**

```capl
/* Telltale test engine — runs N tests from a lookup table */
typedef struct {
    char   tc_id[20];
    long   fault_msg_id;
    int    fault_byte_idx;
    int    fault_bit;
    long   read_did;         /* UDS DID to read telltale status */
    int    expected_state;   /* 1 = ON, 0 = OFF */
    int    react_time_ms;
} TelltaleTc_t;

TelltaleTc_t tc_table[60];  /* Populated from file at startup */

void run_telltale_test(TelltaleTc_t tc) {
    /* Inject fault */
    message 0x000 fault_msg;
    fault_msg.id   = tc.fault_msg_id;
    fault_msg.byte(tc.fault_byte_idx) |= (1 << tc.fault_bit);
    output(fault_msg);
    TestWaitForTimeout(tc.react_time_ms);

    /* Read via UDS */
    int result = read_telltale_status_via_uds(tc.read_did);

    if (result == tc.expected_state) {
        TestStep(tc.tc_id, "passed", "Telltale state: %d", result);
    } else {
        TestStep(tc.tc_id, "failed",
                 "Expected=%d Got=%d", tc.expected_state, result);
        /* Auto-raise defect tag */
        write("DEFECT_CANDIDATE: %s", tc.tc_id);
    }

    /* Clear fault */
    fault_msg.byte(tc.fault_byte_idx) &= ~(1 << tc.fault_bit);
    output(fault_msg);
    TestWaitForTimeout(500);
}
```

3. **Test table loaded from CSV** (not hardcoded) — so I could add new TCs by editing a CSV file, not touching CAPL code.

4. **Auto-generated HTML test report** via CAPL `write()` + a Python post-processor.

5. **Ran nightly** via CANoe command-line launch — results waiting for team each morning.

### Result
- 60 telltale TCs executed in **2.5 hours** vs 3 days manual (65% time reduction)
- Repeatability: exact same input conditions every run — eliminated human observer variability
- Script reused across 2 subsequent projects saving ~30 engineer-days
- Defect detection rate improved: 2 telltale defects caught that manual testing had missed (edge case: simultaneous dual-fault priority conflict)

---

## STAR 3 — Root-Cause Investigation: Odometer Rollback After Cold Start

### Situation
During NVM validation on a cluster bench, the odometer was showing incorrect values after a battery disconnect + reconnect sequence. Specifically, the odo rolled back by 2–5 km after a cold start (KL30 removal). This was a Critical (S1) defect — ISO 16844 prohibits odometer rollback.

### Task
Investigate and identify the root cause within 48 hours. Provide log evidence and a clear technical summary to the SW team for fix prioritisation.

### Action

**Step 1 — Reproduce and characterise:**
I ran the sequence 5 times with identical conditions:
- Record odo via UDS (DID 0xF400) = X km
- Drive simulation: inject 100 km/h × 60s = 1.666 km added
- KL30 OFF (battery disconnect)
- 10s delay, KL30 ON
- Read odo → result was X + (0 to 1.5 km) — consistently missing up to 5 minutes of distance.

**Step 2 — CAN log timing analysis:**
```python
# Python timing analysis on KL15-OFF sequence
# Find time delta between "last odometer write trigger" and "KL30 OFF"

events = extract_events_from_log("odo_test.asc")
kl15_off_ts   = find_event(events, "BCM.IgnitionStatus", 0)["ts_ms"]
odo_write_ts  = find_last_event(events, 0x726, did=0xF400)["ts_ms"]  # UDS write response

gap_ms = kl15_off_ts - odo_write_ts
print(f"Gap: {gap_ms:.0f} ms between last odo write and KL15 OFF")
# Output: Gap: 1820 ms → NVM write happens 1.82s before KL15 OFF
# BUT: cluster shutdown sequence takes 2.5s → NVM write is too early!
```

**Step 3 — Identified root cause:**
The cluster NVM write was triggered by *KL15 OFF detection*, but the NVM write itself was asynchronous with a 2.5s completion guarantee. If KL30 was removed within 2.5s of KL15 OFF (fast operator action), the NVM write was aborted mid-write → partial data → checksum invalid → cluster loaded stale data on next boot.

**Step 4 — Delivered root-cause report:**
- Timing diagram showing NVM write window vs KL30 minimum dwell requirement
- Recommendation: Add a KL30 hold circuit (1.5F supercapacitor or wake-up hold relay) to guarantee 3s minimum after KL15 OFF before KL30 can fall
- Short-term SW fix: Write NVM synchronously before releasing KL15 OFF acknowledge

### Result
- Root cause confirmed by SW team within 4 hours of report delivery
- SW side applied synchronous NVM write in next build (IC_SW_v1.5.1)
- HW team added supercapacitor recommendation into ECU design review for next platform
- Defect closed as Verified in 2 weeks, no recurrence in 10 subsequent test cycles

---

## STAR 4 — Team Conflict: Engineer Producing Low Quality Test Cases

### Situation
One of my mid-level engineers (Priya, 2 years experience) was producing test cases with vague expected results like "cluster should show something" and missing requirement traces. When colleagues reviewed her work, it caused friction because her TCs were being rejected repeatedly. This was creating team tension and slowing the sprint.

### Task
Resolve the quality issue fairly, maintain team morale, and bring Priya's output to the required standard without demoralising her.

### Action

1. **Private conversation (not in front of team):** I booked a 1:1 meeting. I opened with what was working well ("Your test input analysis is solid — you understand the feature"), then addressed the gap: "The expected results need to be measurable — let me show you a good example vs what we have."

2. **Gave a concrete template:**
   - Before: *"Cluster should display correct speed"*
   - After: *"Cluster speedometer shall read [injected value ±3 km/h] within 500ms of receiving VehicleSpeed CAN signal. Reference: SRS_SPD_REQ_004 Rev B."*

3. **Paired her with Suresh** (senior engineer) for 2 days — shadow review, not passive. Suresh reviewed each TC as it was written, not after batch submission.

4. **Set a measurable checkpoint:** "By end of this week, 10 TCs submitted — I will review personally, target zero rework comments."

5. **Gave ownership:** Asked her to own the Python test report automation task — her strength area. This rebuilt confidence.

### Result
- Within 1 sprint, Priya's TC rejection rate dropped from 40% to under 5%
- Team friction was eliminated — Suresh appreciated being asked to mentor
- Priya independently delivered the Python automation script that saved 2 days/sprint (STAR 2 context)
- She was recognised internally at LTTS as a contributor at the quarterly review

---

## STAR 5 — Cross-Functional OEM Escalation: Defect Misclassified as "Not a Bug"

### Situation
CLU-1044: Speedometer reads 8 km/h high at 120 km/h input. Our team classified it as Major (S2). The ECM team (sender of the VehicleSpeed signal) closed it as "Not a Bug — as per EU Regulation 39, speedometer may read ≤ 10% + 4 km/h high." The cluster PM was uncomfortable escalating further but the OEM customer flagged it as a concern in their gateway review.

### Task
Technically verify whether the defect was genuinely compliant, and either close the case with evidence or escalate with a justified position.

### Action

1. **Read EU Regulation 39:** 
   - Regulation 39 states: speedometer shall never indicate LESS than true speed, and the indicated speed shall not exceed true speed by more than **10% + 4 km/h**.
   - At 120 km/h: limit = 120 × 10% + 4 = **16 km/h max over-read**.
   - Our defect showed 8 km/h over-read → technically within regulation.

2. **But — checked OEM SRS:**
   - The OEM addendum to regulation specified a tighter tolerance: **+5 km/h maximum at any speed for this platform** (customer-specific requirement for sport trim).
   - Our defect (8 km/h over at 120 km/h) **violated the OEM SRS**, not EU Reg 39.

3. **Wrote a technical position paper:**
   - Quoted Regulation 39 limits vs OEM SRS limits side by side
   - Plotted injected speed vs cluster display across 0–200 km/h (from our CAN log data)
   - Highlighted the bandwidth breach at 100–160 km/h range

4. **Escalated to OEM through PM with full evidence** — clear, factual, no blame:
   - "CLU-1044 is compliant with EU Reg 39 but non-compliant with OEM SRS requirement SPD-SRS-14 Rev C. Requesting OEM confirmation on which requirement governs the acceptance criterion."

5. **OEM response:** Confirmed OEM SRS takes precedence → defect re-opened as P1 → ECM team fixed signal offset.

### Result
- Defect correctly escalated and fixed — cluster delivered within OEM SRS
- Prevented a potential recall risk (8 km/h over-read in a sport trim cluster would have been noticed by end customers)
- Established a new project rule: all defects disputed by ECU teams must be reviewed against OEM SRS, not just regulations
- My PM commended the approach in the project retrospective

---

## Quick-Reference Q&A Table — Cluster Lead Interview

| Question | Answer |
|---|---|
| What is an Instrument Cluster? | ECU/display unit in front of driver showing speed, RPM, fuel, telltales, DIS, warnings |
| How do you design a test case for a telltale? | Activation, deactivation, priority, self-check, CAN timeout, NVM, localisation tests |
| What is a DBC file? | Database CAN file defining message IDs, signal positions, factors, offsets, units |
| How do you debug a signal not updating on cluster? | Check CAN trace for signal presence → check DBC decode → check cluster SW configuration |
| What is ISO 16844? | Standard for tachometers and odometers in road vehicles — prohibits odometer rollback |
| What is EU Regulation 39? | Speedometer must never under-read, permitted to over-read by ≤ 10% + 4 km/h |
| What is CAN timeout handling? | When a message is not received within expected cycle, cluster falls back to default or error state |
| How do you prioritise defects? | By severity × safety impact. P1 = safety / gateway blocker. P2 = functional loss. P3 = minor. |
| How do you manage a missed deadline? | Early identification, re-plan with data, inform stakeholders with risk + mitigation, never hide. |
| What is a test traceability matrix? | Maps each requirement to test case(s) and execution result — proves coverage |
| How do you handle a WAD (Working As Designed) dispute? | Cross-check SRS vs implementation vs standard. If SRS is ambiguous, escalate to customer for clarification. |
| How do you mentor a junior engineer? | Task pairing, structured feedback, give ownership of a small feature, measure progress in 1-week checkpoints |
| What Python libraries are useful for CAN testing? | `python-can`, `cantools` (DBC decode), `openpyxl` (Excel reports), `requests` (Jira API) |
| What is the CAPL `testcase` keyword? | A formal test function in a CANoe Test Module that records pass/fail for each step |
| How do you ensure test repeatability? | CAPL automation, defined preconditions, version-controlled DBC and SW baseline, nightly execution |
| What is the difference between gateway and milestone? | Gateway = customer-side quality gate (must pass before next phase). Milestone = internal schedule checkpoint. |

---

*File: 06_star_interview_scenarios.md | marelli_cluster_lead series*
