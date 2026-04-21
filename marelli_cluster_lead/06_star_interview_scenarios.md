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

## STAR 6 — Process Improvement: DBC Version Control (OEM Standards Adherence)

### Situation
During a mid-project audit, I discovered that three engineers were using different DBC file versions to write their test cases. Two were on Powertrain_v2.2.dbc, one was on v2.3.dbc. ABS_Fault signal had moved from Byte 0 Bit 0 to Byte 0 Bit 1 between the two versions. As a result, 14 test cases had been written with the wrong bit position — they would all pass in CANoe against the wrong decode but would fail on real hardware. The project had no formal DBC version control process.

### Task
Immediately fix the in-flight TC errors and introduce a repeatable DBC version control process that would prevent recurrence across all future sprints.

### Action
1. **Immediate triage:** Identified which TCs relied on signals that had changed between v2.2 and v2.3. Ran the Python DBC comparison script (diff on start_bit, factor, length fields) — output showed 7 changed signals. Manually reviewed all 14 impacted TCs and corrected bit positions.

2. **Root cause analysis:** DBC files were stored in a shared Confluence folder with no versioning — engineers downloaded when convenient, without knowing if a newer version existed.

3. **Process introduced:**
   - DBC files moved into the project Git repository under `config/dbc/`
   - DBC version recorded in every test case precondition section: *"Requires: Powertrain_v2.3.dbc"*
   - Added `dbc_validator.py` to the CI pipeline — runs on every new DBC commit and outputs a diff report
   - Added a sprint start checklist item: *"All engineers confirm same DBC version as DBC baseline tracker"*
   - Nominated one engineer (Suresh) as DBC custodian per project — only he merges DBC updates

4. **Team training:** 30-minute session on how DBC scaling works (start_bit, factor, byte order) — engineers could now manually verify their signal decode in trace without relying on tool automation alone.

### Result
- 14 TCs corrected before execution — zero escaped to gateway with wrong bit positions
- No DBC-related defects were raised in the next 3 sprints (previous 2 sprints had 4 each)
- Process was adopted as LTTS Bangalore cluster team standard and shared with 2 other IC projects
- Customer acknowledged improved DBC traceability at sprint review

---

## STAR 7 — Handling a Resource Crunch Mid-Sprint (Delivery Under Pressure)

### Situation
In Sprint 09 of a cluster delivery project, two engineers went on unplanned leave simultaneously — one for a medical emergency, one for a family function that wasn't in the capacity plan. This removed 100 person-hours from a 188-hour sprint. The sprint contained TC_CTO_001–015 (CAN timeout tests) which were on the critical path for the gateway review in 5 days. Missing them would have delayed the OEM delivery by 2 weeks.

### Task
Recover the sprint without impacting the gateway. Either complete the critical-path TCs in time or negotiate a credible, evidence-backed risk mitigation plan with the OEM.

### Action
1. **Prioritised ruthlessly:** Listed all remaining sprint backlog items. Marked CAN timeout TCs (15 TCs, ~15h effort) as non-negotiable. All P3 cosmetic TCs and documentation tasks were moved to Sprint 10.

2. **Redistributed load:**
   - Took on 10 hours of execution myself (CAN timeout tests — I knew the bench setup well)
   - Pulled in Anjali (fresher, assigned simpler TCs in previous sprints) to run 5 straightforward timeout TCs with me providing a quick 2-hour walkthrough before she started
   - Scheduled extended bench session: 7am–8pm for 2 days (with team agreement)

3. **Automated a portion on the fly:**
   - 6 of the 15 CAN timeout TCs had identical structure (different message IDs). I wrote a parametrised CAPL test in 90 minutes that covered all 6 instead of manual execution — net saving: 4 hours.

4. **Communicated proactively:**
   - Emailed PM same day with updated plan: "We will deliver all 15 CTO TCs by Friday with adjusted team. P3 items deferred to Sprint 10 — no gateway impact."
   - PM informed OEM as a courtesy — OEM appreciated the advance notice.

### Result
- All 15 CAN timeout TCs executed by Thursday (1 day ahead of revised plan)
- 3 defects found: CLU-1051 (speed fallback wrong value), CLU-1052, CLU-1053
- Gateway not delayed — OEM confirmed sign-off on schedule
- Anjali gained confidence executing independently — her first full solo TC batch
- CAPL parametrised script reused in Sprint 10 for remaining timeout tests

---

## STAR 8 — Handling a Disagreement with ECU Team on Defect Ownership (Stakeholder Management)

### Situation
CLU-1031: Odometer rollback of 1.2 km after cold crank was raised as a cluster defect (S1 / P1). The cluster SW team reviewed and responded: "Odometer rollback is caused by incorrect KL15 OFF signal from BCM — BCM drops KL15 too fast, doesn't allow cluster NVM write to complete. Not a cluster bug — it's BCM's fault." The BCM team responded: "BCM KL15 timing is within spec per BCM_SRS_Rev_B. Cluster must tolerate it." Both teams refused to own the fix. The defect was in danger of being closed as NAB (Not A Bug) with the root cause unresolved — and the odometer would still roll back.

### Task
Resolve the ownership dispute using technical evidence and ensure the defect was fixed in one of the two ECUs before the gateway. ISO 16844 prohibits odometer rollback — this was a regulatory non-compliance issue.

### Action
1. **Technical investigation:** Measured KL15 OFF timing from CAN trace:
   - BCM drops KL15 flag (IgnitionStatus = 0) at T=0ms
   - Cluster detects KL15 OFF flag at T=0ms
   - Cluster NVM write initiates at T=10ms
   - Cluster NVM write completes at T=2510ms (2.5 second write cycle)
   - BCM removes KL30 power at T=1800ms (battery relay opens)
   - **900ms power gap — cluster NVM write is aborted 700ms before completion**

2. **Referenced standards:**
   - ISO 16844-1 Section 7.4: *"The recording device shall ensure completion of all data storage operations before final shutdown."*
   - BCM_SRS_Rev_B timing spec: KL30 must remain active for minimum 2.0s after KL15 OFF.
   - Measured BCM KL30 hold: 1.8s — **200ms below its own SRS requirement**.
   - Cluster SRS: *"NVM write on ignition off shall complete assuming KL30 hold of ≥ 2.5s."*

3. **Position paper with annotated timing diagram:**
   - BCM violates its own SRS (1.8s < 2.0s) — BCM defect confirmed
   - Cluster NVM design relies on 2.5s KL30 hold — cluster SRS needs review for resilience
   - Recommended dual fix: BCM fix (extend KL30 hold to 2.5s) + cluster SW fix (synchronous NVM write as backup)

4. **Escalated to integration lead** (not PM), who facilitated a joint BCM + Cluster + me technical call with my evidence. BCM team agreed to extend KL30 hold.

### Result
- BCM fix applied in BCM_SW_v2.1.1 (KL30 hold extended to 2.8s)
- Cluster SW team added synchronous NVM write as a defensive secondary fix
- CLU-1031 verified closed — no odometer rollback in 20 subsequent KL30 cycle tests
- Integration lead documented this as a cross-ECU interface gap and added KL30 hold timing to the integration ICD (Interface Control Document)
- ISO 16844 compliance confirmed at gateway review

---

## STAR 9 — Introducing Nightly Regression (Process Improvement / Python Automation)

### Situation
Cluster validation was build-on-demand — whenever the SW team released a new IC build (roughly every 2–3 weeks), our team would manually set up CANoe, load the new DBC, and run regression. This took 2 engineers full-time for 3 days per build. With builds accelerating to weekly in the final phase, we were spending 6+ engineer-days per week just on regression — leaving insufficient capacity for new TC development.

### Task
Implement a nightly automated regression so that each new SW build was tested overnight and results were available by 9am the next morning — without engineer involvement during the night run.

### Action
1. **Assessed automation feasibility:** 
   - 40 of 320 TCs were already in a CANoe Test Module and could run headless via command line
   - 90 TCs could be converted to CAPL automation within a sprint (gauges and telltales — same pattern)
   - 190 TCs required manual observation (display quality, animation, illumination) — cannot automate

2. **CANoe command-line execution:**
   ```
   canotestmodule.exe /cfg IC_Validation.cfg /environment NIGHTLY
                      /testmodule IC_System_TestSuite.vts /output results\
   ```
   Added this to a Windows Task Scheduler job triggered at 22:00 each weekday.

3. **Python build detector:**
   Wrote `build_notifier.py` — polls build server API for new IC SW build version. If new build detected, copies it to bench PC, reloads CANoe, triggers the nightly run, emails results to team at 8:30am with pass/fail summary.

4. **Converted 90 manual TCs to CAPL automation** over 2 sprints using the parametrised CAPL table pattern — TC ID, inject value, expected value, tolerance read from CSV → no hardcoded test data.

5. **Dashboard:** Python script parsed the CANoe XML result + emailed an HTML colour table (green/red per TC) to the team and PM every morning. Failing TCs had Jira defect auto-created via REST API.

### Result
- **Nightly regression running 130 TCs per night** by end of Sprint 6
- Build verification time: 3 days manual → **zero extra engineer-hours** (results ready at 9am)
- 3 build-introduced regressions caught overnight before engineers started work — fixing cost reduced (found on day 0 vs day 3)
- Engineering capacity freed: 6 engineer-days/week reclaimed for new TC authoring
- PM requested the automation framework be documented and offered to 2 other LTTS cluster projects

---

## STAR 10 — Cross-Cluster Variant Delivery (Multi-Platform Handling)

### Situation
The project expanded scope mid-execution: instead of one cluster variant (EU, petrol), we were asked to validate 4 variants simultaneously:
- EU Petrol (km/h, L/100km)
- EU EV (km/h, SOC%, kWh/100km)
- US Petrol (mph, MPG)
- US EV (mph, mi, SOC%)

All 4 had the same base cluster HW but different SW builds, DBC files, and OEM SRS documents. Timeline was unchanged. No additional engineers. We had one bench.

### Task
Deliver validation coverage for all 4 variants within the same timeline using the same team of 4 engineers, without reducing test case depth for any variant.

### Action
1. **Analysed variant delta — what actually differs:**
   - Speed display: unit label + scale ring (km/h vs mph)
   - Fuel gauge replaced by SOC gauge on EV variants
   - Economy: different formula per variant (not different signal — same raw, different display)
   - Telltales: identical across all 4 (ISO 2575 symbols unchanged)
   - NVM, power mode, CAN timeout: identical behaviour

   Conclusion: **60% of TCs were shared across all variants** — no point running them 4 times.

2. **Created a Variant Test Matrix:**
   ```
   TC Category        | EU Pet | EU EV | US Pet | US EV | Variant-specific?
   ───────────────────|--------|-------|--------|-------|------------------
   Telltale matrix    |  RUN   |  RUN  |  SKIP  |  SKIP | EU only (1 run)
   Speed unit (km/h)  |  RUN   |  RUN  |  SKIP  |  SKIP | EU unit
   Speed unit (mph)   |  SKIP  |  SKIP |  RUN   |  RUN  | US unit
   Fuel gauge         |  RUN   |  SKIP |  RUN   |  SKIP | Petrol only
   SOC gauge          |  SKIP  |  RUN  |  SKIP  |  RUN  | EV only
   Odometer (km)      |  RUN   |  RUN  |  SKIP  |  SKIP |
   Odometer (miles)   |  SKIP  |  SKIP |  RUN   |  RUN  |
   CAN timeout        |  RUN   |  SKIP |  SKIP  |  SKIP | Common — run once
   Power mode         |  RUN   |  SKIP |  SKIP  |  SKIP | Common — run once
   ```

3. **CAPL parametrised for unit variants:**
   - One CAPL script with a variable `market` (0=EU, 1=US)
   - Speed tolerance adjusted: EU ±2 km/h, US ±1.5 mph
   - Economy formula swapped via `if(market==US)` block

4. **Bench rotation schedule:** 2 variants per week — EU week 1, US week 2.

5. **Shared regression suite:** Common TCs run once on EU Petrol and their results applied to all 4 (with documented justification in test closure report).

### Result
- All 4 variants signed off within original timeline
- Total TCs executed: 680 (4 × 320 - 600 duplicates eliminated by shared suite) = ~280 unique + 400 variant-specific
- Zero variant-specific defect leakage to OEM
- Variant test matrix became a project standard document used on next platform (4 new variants)
- Customer commented that multi-variant delivery with such a compact team was "impressive"

---

## STAR 11 — Safety Concern Raised During Test Execution (ASIL / Safety Escalation)

### Situation
During speedometer validation, Suresh noticed that at exactly 0 km/h (vehicle stationary), the cluster speedometer needle was showing a reading of 3 km/h instead of 0. It looked like a minor cosmetic issue. However, I recognised that ISO 4513 states the speedometer must not indicate a speed greater than actual speed — 3 km/h over at true 0 km/h is a regulation violation, and more importantly, this was below our ABS engagement threshold. If a vehicle displayed 3 km/h at rest, it could mask the true stationary condition from the driver.

### Task
Assess the safety severity immediately, escalate to the correct level, and ensure the defect was not treated as a cosmetic issue and closed without analysis.

### Action
1. **Immediate severity call:** Classified as P1 / S1 on my own authority — I did not wait for confirmation. Reason: UN ECE Reg 39 prohibits speedometer reading above true speed. 3 km/h > 0 km/h = regulatory violation. Any defect touching a regulatory requirement is S1 by project definition.

2. **Raised defect CLU-1055 with full technical justification:**
   - Regulation reference: UN ECE Regulation No. 39, Section 5.2.1
   - Potential consequence: Driver may perceive vehicle as still moving at rest (safety)
   - Test log attached: 10 captures at 0 km/h = 0 km/h injected, cluster reads 3.0 km/h

3. **Root cause hypothesis provided:**
   - Speed signal injection shows raw value = 0 → cluster applies a DMP (dead-zone masking filter) that treats 0–4 km/h raw as "suppress jitter" but returns 3 km/h display instead of 0
   - Likely SW bug in the display filter logic (should clamp to 0, not return average of filter window)

4. **Escalated to LTTS Safety Lead** (not just PM) — this triggered the functional safety review process per our project's ISO 26262 workproduct checklist.

5. **Communicated to OEM same day** via PM — did not wait for root cause confirmation. Reason: OEM had responsibility to know about potential regulatory non-compliance on their platform.

### Result
- SW team confirmed the dead-zone filter bug: returning mid-point of [0, 6] = 3 km/h instead of 0
- Fix applied in IC_SW_v1.5.2 (filter clamp at 0 when input raw = 0)
- Verified: 10 × captures at 0 km/h = all show 0.0 km/h on cluster
- Safety Lead reviewed and DID NOT require ASIL re-analysis (bug in display layer only — not in speed sensing path)
- OEM appreciated the proactive communication and early escalation
- My reclassification from cosmetic to S1 was validated — had it been closed as cosmetic, it would have been a warranty / regulatory risk post-production

---

## STAR 12 — First Time as Cluster Lead (Stepping Up from Senior Engineer)

### Situation
I had been a senior cluster validation engineer for 3 years. My manager informed me I was being promoted to Cluster Lead for a new Marelli project — a C-segment platform with Honda as the OEM. This was my first lead role. The team had 5 engineers including 2 freshers and 1 engineer who had more years of experience than me. I had to establish credibility quickly, define the test strategy from scratch, and manage customer communication — all for the first time.

### Task
Step into the Cluster Lead role effectively: create a test strategy the team could trust, earn the team's respect (including the senior engineer), and deliver the first sprint milestone on time.

### Action
1. **First week — listen and learn the project:**
   - Read the full OEM SRS document (IC_SRS_Honda_Rev_C): 220 pages
   - Shadow the system lead for 2 days — learned the vehicle architecture, key ECU interfaces
   - Held 1:1s with each team member: asked what they needed to be effective, what had slowed them on previous projects

2. **Published test strategy within 2 weeks:**
   - Scope, entry/exit criteria, risk table, tool versions, bench setup
   - Shared for team review before finalising — incorporated 3 suggestions from engineers (including the senior one, Ramesh)
   - Having Ramesh's suggestions in the document made him a stakeholder in the plan — not just a follower

3. **Handled the "more experienced engineer" dynamic:**
   - Gave Ramesh the highest-complexity area: ASIL B telltale validation (played to his strength)
   - In technical discussions, I stated my position with evidence, not authority: "Based on the SRS, I read it this way — Ramesh, does that align with your reading?"
   - When Ramesh disagreed on test depth for NVM tests, I asked him to write a 1-paragraph technical justification and we reviewed it together — his point was valid, I updated the plan

4. **First sprint delivery:**
   - Ran daily standups with strict 15-min timebox
   - Blockers resolved same day — I personally unblocked 3 bench issues in the first 2 weeks
   - Weekly OEM status sent every Friday before 5pm, no exceptions

5. **Made one visible mistake and owned it:**
   - Week 3: I approved a TC batch without checking SRS revision — one TC had a stale expected value. When OEM raised it, I said "That was my review error — here is the correction and the review process change I am implementing." No blame on the engineer who wrote it.

### Result
- Sprint 01 milestone delivered on time — 80 TCs executed, 0 missed
- OEM noted "test strategy document is the most complete first-sprint deliverable we have seen from a new lead"
- Ramesh became a strong collaborator — he took ownership of the DBC review process
- I received a formal L2 → L3 grade promotion at the end of the project
- Two freshers' skill levels doubled over the project — both independently running full TC sets by project end

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
| What is ASIL and why does it matter for cluster? | Automotive Safety Integrity Level (ISO 26262) — speedometer is ASIL B. Defects on ASIL-classified features need safety review before closure. |
| What is a bulb check? | Self-test sequence at KL15 ON where cluster lights all telltales for ~2–3 seconds to verify display hardware. |
| How do you handle a situation where two ECU teams disagree on defect ownership? | Gather timing evidence from the CAN log, reference SRS requirements from both ECUs, identify which SRS is violated, present a technical position paper to the integration lead. |
| What is UDS? | Unified Diagnostic Services — ISO 14229. A protocol used over CAN (ISO-TP) for reading/writing ECU data, reading DTCs, and controlling ECU functions. |
| What is a DID in UDS? | Data Identifier — a 2-byte address used with UDS service 0x22 (ReadDataByIdentifier) to read specific ECU data like odometer (0xF400) or SW version (0xF189). |
| What causes a speedometer to read high at 0 km/h? | Common cause: display jitter filter returning mid-point of filter window instead of clamping to 0. Root cause is SW bug in the dead-zone filter logic. |
| What is first-pass yield? | Percentage of test cases that pass on their first execution. FPY > 85% is a healthy target. Low FPY may indicate poor test TC preconditions, unstable builds, or poor test design. |
| How do you manage multiple cluster variants in one project? | Identify the common base TCs (run once), variant-specific TCs (per market/fuel type), use parametrised CAPL, and manage with a variant test matrix document. |
| What is your approach when a project schedule is at risk? | Re-assess scope: defer P3/cosmetic TCs, automate what is repeatable, re-allocate resource to critical path, inform PM immediately with updated plan and risk level. |
| Describe your test strategy exit criteria. | All P1/P2 closed/verified, ≥95% TCs executed, ≥85% first-pass yield, traceability matrix complete, OEM sign-off on all open P3 items (accept or defer). |
| What is the difference between severity and priority? | Severity = technical impact (S1 = safety). Priority = business urgency (P1 = fix first). A cosmetic defect before a customer demo may be P1/S3 — high business priority, low severity. |
| What is ICD in automotive? | Interface Control Document — defines the agreed signals between two ECUs (IDs, signal names, ranges, cycle times). Resolves disputes between ECU teams on "what was specified". |
| How do you verify odometer accuracy without a physical vehicle? | Inject a known speed (e.g. 100 km/h) for a measured time (e.g. 60s) via CAN → calculated distance = 1.666 km → read cluster odo via UDS before and after → compare delta. |

---

## STAR 13 — Managing a Low-Performing Engineer Without Losing Them

### Situation
Three weeks into Sprint 04, Priya's execution output had dropped significantly — from 12 TCs per day to 4-5. She was missing standup updates, her defect reports lacked reproduction steps, and two of her test cases had already been rejected. Other engineers were silently picking up her backlog. If this continued, the sprint would miss its target and the team dynamics would deteriorate.

### Task
Address Priya's performance drop constructively, identify whether it was a skill gap, a motivation issue, or a personal problem — and recover the sprint without damaging the team or losing a trained engineer.

### Action
1. **Private 1:1 first — not in front of the team:** I reached out same day and booked a private 30-minute slot. Rule: never raise performance issues publicly.

2. **Asked open questions, listened first:**
   - "I've noticed your output has changed in the last two weeks — how are you finding the current work?"
   - Priya disclosed she was struggling with the UDS-based tests (which required reading CAPL `diagRequest` — a skill she hadn't fully developed) and felt embarrassed to ask for help after 2 years in the team.

3. **Separated the issue: skill gap, not attitude:**
   - She had been assigned UDS NVM tests (beyond her current CAPL level) without a ramp-up
   - I had assigned the task assuming she had the UDS knowledge — that was my planning oversight

4. **Immediate corrective actions:**
   - Reassigned her to gauge sweep tests (her strength) for remainder of the sprint
   - Paired her with Suresh for 3 UDS sessions (1 hour each) over 2 weeks — structured upskilling
   - Set a clear checkpoint: "By Sprint 06, I expect you to run 5 UDS TCs independently"

5. **Addressed the backlog impact transparently:**
   - Redistribted her blocked TCs to Ravi for that sprint — told the team it was a sprint rebalancing decision, not a performance call (protected her dignity)

### Result
- Sprint 04 target recovered — Ravi completed the UDS TCs in 8 hours
- Priya's output returned to 10+ TCs/day in Sprint 05 on gauge tasks
- By Sprint 06, Priya ran 8 UDS TCs independently — exceeded the checkpoint target
- She stayed on the project and became the team's Python automation specialist
- I added a sprint planning rule: always verify engineer's current capability before assigning new skill domain tasks

---

## STAR 14 — Building Team Morale During a High-Pressure Final Phase

### Situation
We were in the final 3 weeks before OEM gateway delivery. The SW team had released 3 builds in 10 days — each with new fixes that required partial regression. My team of 4 engineers was executing 35+ TCs per day, raising defects, retesting fixes, and writing closure reports simultaneously. Two engineers mentioned they were exhausted and one joked about "wanting to quit." Team morale was visibly low.

### Task
Sustain team productivity through the high-pressure final phase without burning out the engineers or losing quality in the final deliverable.

### Action
1. **Acknowledged the pressure openly in standup:**
   - "I know this phase is intense. The pace is higher than normal. I want you to know I see it and I'm going to make some changes today."
   - Teams lose morale faster when they feel invisible. Acknowledgement costs nothing and costs everything if skipped.

2. **Reduced unnecessary overhead immediately:**
   - Cancelled the weekly documentation update task (deferred to post-gateway) — saved 3 hours per engineer
   - Condensed standups from 30 min to 10 min — only blockers and today's priority
   - Removed the requirement to write execution notes in Jira for every passed TC during regression (summary note only)

3. **Introduced a "done board" visibility:**
   - Created a shared Teams message pinned at top: "🟢 Passed today: X TCs | 🔴 Defects raised: Y | 🔑 Retests completed: Z"
   - Updated every evening. Engineers could see progress — progress is motivating.

4. **Gave ownership of a visible win:**
   - When CLU-1024 (the long-running P1) was finally verified closed, I called it out in the standup: "Suresh found this, Ravi did the detailed trace, Priya retested — this was a team result. This is the one the OEM is watching."

5. **Protected weekends:**
   - Despite pressure, I held the line on no weekend work. Sustainable pace is a lead's responsibility.
   - I worked Saturday myself to prepare the OEM status report so the team didn't have to.

### Result
- Team completed the final phase with 312/320 TCs executed (97.5%) — above target
- No engineer left the project or requested transfer
- Ravi mentioned in the project retrospective: "The final sprint was hard but felt manageable — the daily progress update helped a lot."
- Gateway passed — OEM gave written commendation on delivery quality
- I was asked to present "team management during high-pressure delivery" at the LTTS Bangalore engineering town hall

---

## STAR 15 — Handling a Scope Increase from OEM Mid-Project (Change Management)

### Situation
We were 60% through execution when the OEM sent a change request: they wanted to add 45 new test cases for a new DIS feature (Eco Score display) that had been added to the cluster SW in the latest build. The project was already at full capacity. No additional budget or timeline was offered initially.

### Task
Assess the impact of the scope increase, negotiate with the OEM on timeline or resources, and either absorb or formally reject the change with a documented position.

### Action
1. **Impact assessment first — estimated before negotiating:**
   - 45 new TCs at average 30 minutes each = 22.5 engineer-hours
   - Plus: DBC signal analysis for Eco Score signal (new signal from VCU, not in current DBC) = 4h
   - Plus: CAPL script update = 6h
   - Total: ~33 hours = approximately 1 engineer-week
   - Current buffer in plan: 8 hours → **shortfall: ~25 hours**

2. **Presented options in writing to the PM, not verbal:**
   ```
   OPTION A — Accept full scope, extend timeline by 1 week
   OPTION B — Accept scope, swap out 30 P3 cosmetic TCs (de-scope, OEM approval needed)
   OPTION C — Partial accept: execute 20 critical Eco Score TCs now, defer 25 to next sprint
   OPTION D — Reject change, document OEM's written direction if they insist
   ```

3. **PM escalated to OEM with the option table.** OEM chose Option C — 20 now, 25 in next sprint.

4. **Integrated into backlog immediately:**
   - Priya took the Eco Score DBC signal work (her strengths: Python + signal analysis)
   - 20 TCs written and executed within 5 days
   - 25 TCs documented in Sprint backlog with SRS reference for next sprint

5. **Updated test strategy document** to formally record the scope change, date, and OEM decision reference — essential for closure sign-off.

### Result
- 20 Eco Score TCs completed within the sprint with no delay to existing work
- 2 defects raised (Eco Score display wrong unit — L/100km showed as Wh/km on EV variant)
- OEM signed off scope change formally — no ambiguity at project closure
- Remaining 25 TCs planned for Sprint 10 — no surprise at sprint planning
- PM acknowledged the structured option table approach and reused it for 2 subsequent scope changes on the project

---

## STAR 16 — Knowledge Transfer to a New Team at Project Handover

### Situation
Our cluster validation project was 14 months long. At completion, LTTS management decided the ongoing maintenance validation (handling future SW builds) would be passed to a junior team in Pune, none of whom had worked on this platform before. I had 3 weeks to transfer full project knowledge: CANoe setup, CAPL scripts, bench configuration, DBC management, defect history, and test process.

### Task
Deliver a complete, effective knowledge transfer so the Pune team could independently run regression tests on a new build within 6 weeks of handover — with no dependency on me.

### Action
1. **Created a KT (Knowledge Transfer) Pack — first:**
   - `0_KT_OVERVIEW.md` — team structure, platform overview, key contacts
   - `1_BENCH_SETUP.md` — step-by-step bench startup, CANoe config load, trouble common errors
   - `2_DBC_MANAGEMENT.md` — DBC version process, where files live, how to compare versions
   - `3_CAPL_SCRIPTS.md` — what each script does, how to modify parameters, known limitations
   - `4_DEFECT_HISTORY.md` — all closed P1/P2 defects with root causes — "known failure modes gallery"
   - `5_TEST_EXECUTION_SOP.md` — step-by-step SOP for running a full regression cycle

2. **Three-week structured KT plan:**
   - Week 1: Watch + document (Pune team watches our engineers run full regression remotely via screen share, then documents gaps)
   - Week 2: Do + review (Pune team runs regression themselves — we review results together)
   - Week 3: Independent run (Pune team runs alone — I review output without coaching)

3. **Seeded a known defect into the bench for Week 3:**
   - Injected a DBC version mismatch (changed one signal factor) without telling the Pune team
   - They had to find it using the comparison process we taught — they did, in 2 hours
   - This confirmed they could independently debug, not just follow SOPs

4. **Created a "5 Common Failures on This Platform" one-pager:**
   - Odometer rollback on fast KL30 cycle (root cause + fix history)
   - ABS telltale DBC bit position (recurring across builds)
   - Speed filter returning 3 km/h at 0 (display layer bug)
   - Eco Score unit mismatch on EV variant
   - CAN timeout fallback shows wrong default value

### Result
- Pune team ran their first independent regression (40 TCs) in Week 4 — 1 week ahead of target
- They found a genuine build-introduced regression (fuel gauge rounding error) — unprompted, using the DBC compare script
- Zero escalations to me in the 8 weeks following handover
- KT documentation was reviewed by LTTS delivery head and adopted as the standard cluster project handover template
- My manager used this KT as proof of lead maturity for my grade promotion case

---

## STAR 17 — Onboarding a Fresher Engineer to Full Productivity in 4 Weeks

### Situation
Anjali joined the cluster validation team directly from college with zero automotive or CAN domain experience. She had basic Python but no CAPL knowledge, no understanding of CANoe, and had never seen a DBC file. My sprint plan had assumed 30 engineer-hours of output from her in week 3. I had 4 weeks to get her to that level.

### Task
Design and execute a structured 4-week onboarding plan that brought Anjali to the point of independently executing DIS and gauge test cases, raising defects correctly, and using CANoe trace — without pulling senior engineers off their own work for more than 30 minutes per day.

### Action

**Week 1 — Domain (Mornings: Self-study. Afternoons: Shadow)**
- Reading: `01_instrument_cluster_fundamentals.md` (provided upfront)
- Task: Identify 10 CAN messages in a live CANoe trace and note what each signal means
- Outcome check: Written summary — "What does the cluster need from the CAN bus to display at KL15 ON?"

**Week 2 — CANoe + CAPL Basics**
- I gave her `test_01_telltale_validation.can` — asked her to read it and explain what it does in her own words
- Exercise: Modify one parameter in the CAPL script (change a timer value from 1000ms to 500ms), run it, observe the change in trace
- Exercise: Send a manual CAN message using a Panel slider — observe cluster response on bench
- Outcome check: She must write one CAPL test stub independently (inject a speed signal, wait 200ms, check signal presence in trace)

**Week 3 — Defect Training**
- I seeded 3 known defects into the bench:
  1. ABS telltale not activating (DBC bit mismatch)
  2. Speed showing 3 km/h at 0 km/h
  3. Odometer not updating (NVM write blocked)
- She had to find them, identify root cause hypothesis, and write defect reports using the project template
- I reviewed each report with written feedback: what was correct, what needed improvement, specific example of the correct phrasing

**Week 4 — Independent Execution**
- Assigned 15 real TCs from the backlog (DIS: trip meter, odometer, fuel range display)
- She executed, raised defects, and submitted results — I reviewed output but did not assist unless blocked > 30 minutes
- Friday: structured feedback session

### Result
- Week 3: Anjali found all 3 seeded defects and wrote defect reports rated "acceptable quality" by Suresh's peer review
- Week 4: 13 of 15 TCs executed (2 blocked due to bench availability — documented correctly)
- Week 4: Raised 2 real defects (CLU-1067 trip meter reset in wrong km, CLU-1068 fuel range jumps on cold start)
- By Sprint 09, Anjali was producing 10 TCs/day — equivalent to a mid-level engineer
- She was retained on 2 subsequent cluster projects and is now a junior CAPL developer
- My 4-week plan was shared across the LTTS Bangalore team as an onboarding template

---

## STAR 18 — Managing a Conflict Between Two Senior Engineers

### Situation
Ravi and Suresh — both senior engineers on my team — had a visible disagreement during a test case review. Suresh had reviewed Ravi's NVM test cases and written 8 rejection comments, some of which Ravi felt were "nit-picks and personal." Ravi responded in the Jira comment thread in a tone that was unprofessional ("Some people should focus on their own work"). This was in written form, visible to the whole team and had the potential to damage team cohesion at a critical point in the project.

### Task
De-escalate the conflict immediately, maintain professionalism in written project tools, and resolve the underlying technical disagreement — all without losing either engineer's commitment to the project.

### Action
1. **Acted same day — did not let it sit:**
   - Edited the Jira comment (as project admin) and posted: "Inline technical discussion continues offline. This thread is now for technical resolution only."
   - Sent individual messages to both: "Can we three meet for 20 minutes today?"

2. **In the meeting — structure mattered:**
   - First 5 minutes: Stated the meeting purpose: "We need to resolve this review technically and keep the Jira record professional. I'm not here to judge who was right — I'm here to get the TCs unblocked."
   - Asked Suresh to walk through his 8 rejection comments one by one — technical only, no framing
   - Asked Ravi to respond to each: "Agree / Disagree / Need to discuss"
   - Result: 5 comments were valid rejections (Ravi agreed after explanation). 3 were genuine preference, not defects.

3. **Made a decision on the 3 disputed items** rather than letting it remain unresolved — vague decisions cause resentment to linger.

4. **Separately — private conversation with Ravi:**
   - "The comment in Jira was not the right forum. I know you're under pressure — but I need the written record to stay professional. I trust you to keep it that way going forward."
   - No formal warning — this was a first incident, private conversation was the proportionate response.

5. **Separately — private word with Suresh:**
   - "When reviewing senior peers, frame rejections in terms of the SRS or the checklist — 'This doesn't meet SRS_REQ_014' lands better than a list of comments without justification."
   - Suresh accepted this — he adjusted his review style.

### Result
- 5 of 8 TCs corrected by Ravi same day — sprint unblocked
- 3 disputed TCs resolved with documented lead decision in Jira
- No further incidents between Ravi and Suresh for the remainder of the project
- Ravi and Suresh collaborated directly on the CAN timeout automation in Sprint 10 — a sign of restored working relationship
- I updated the team working agreements document with: *"Technical disagreements are resolved offline. Jira is for technical tracking only."*

---

## STAR 19 — Presenting Test Results at an OEM Gateway Review

### Situation
The IC Cluster Gateway Review with the OEM (Renault team) was a formal milestone. My manager was travelling, so I was asked to present the test results directly to the OEM's validation lead and system architect — approximately 8 people on the call. This was my first solo OEM gateway presentation. The results included 2 open P2 defects that the OEM would scrutinise.

### Task
Present the test results clearly, handle technical questions from OEM engineers with confidence, and achieve gateway sign-off — with 2 open P2 defects on record.

### Action
1. **Prepared a structured slide deck (10 slides, no more):**
   - Slide 1: Scope of validation (what was tested, what was out-of-scope)
   - Slide 2: Test execution summary (TCs: 320 total, 314 passed, 4 failed, 2 blocked)
   - Slide 3: Defect summary (open P1: 0. Open P2: 2. Open P3: 8)
   - Slide 4–5: P2 CLU-1044 (speedometer over-read) — root cause, OEM SRS vs observation, SW fix plan
   - Slide 6–7: P2 CLU-1051 (CAN timeout fallback wrong value) — root cause, fix plan, ETA
   - Slide 8: Test coverage heatmap (feature × test type matrix — visual)
   - Slide 9: Risk table with mitigations
   - Slide 10: OEM decision request (sign off with 2 P2 open, fix confirmed by Sprint 10)

2. **Prepared answers to likely hard questions:**
   - "Why is CLU-1044 still open?": SW fix was provided in v1.5.2 but we need one more full regression cycle — ETA 5 days
   - "Can you guarantee no further P1 defects?": Not guarantee — but coverage is 98.7% of SRS, all ASIL B features verified
   - "What is the risk of shipping with P2 open?": CLU-1044 is within EU Reg 39 limits — OEM SRS tighter, agreed deferral option if needed

3. **During the call — stayed factual, no defensiveness:**
   - When OEM architect challenged CLU-1044 severity: "Understood. We have the log data here — let me share screen and walk through the measurement."
   - Showed the trace live, walked through signal vs display value, quoted Reg 39 and OEM SRS side by side
   - OEM architect: "OK — that's clear. What's the fix ETA?" → answered precisely: "Build v1.5.2 available Monday, retest complete by Wednesday."

4. **Requested the gateway decision explicitly at the end:**
   - "Based on the evidence presented, I am requesting gateway sign-off with the 2 P2 defects tracked to Sprint 10 delivery. Are there any objections?"

### Result
- **Gateway signed off in the same session** — no follow-up meeting required
- OEM validation lead commented: "Best-prepared gateway pack we have received from LTTS in this programme"
- CLU-1044 and CLU-1051 both fixed and verified in Sprint 10 as committed
- My manager promoted me to technical lead grade at end of the year, citing the gateway presentation as evidence of customer-facing readiness
- I documented the gateway prep process and slide structure as a reusable checklist for future cluster leads

---

## STAR 20 — Recovering from a Test Coverage Gap Found at Gateway

### Situation
Two days before the OEM gateway review, during my final internal audit of the traceability matrix, I discovered that 12 test cases linked to SRS requirement cluster `IC_SRS_TEL_REQ_020` (telltale dual-fault priority) had never been executed — they were written, but not scheduled due to a sprint planning error. Six of them tested ASIL B telltale priority behaviour (SRS/ABS simultaneous fault — which one takes priority). These were not cosmetic — they were safety-relevant requirements.

### Task
Assess whether the 12 TCs could be executed in 2 days without disrupting delivery, decide whether to disclose the gap to the OEM, and ensure the coverage gap was formally handled before gateway.

### Action
1. **Immediate scope assessment:**
   - 12 TCs: 6 ASIL B priority tests + 6 P3 visual priority tests
   - Average execution time: 20 minutes per TC = 4 hours total
   - CAPL script already existed for telltale injection — no new scripting needed
   - Bench available: yes

2. **Decision: execute all 12 before gateway, do not enter gateway with an untested ASIL B requirement:**
   - Communicated to team at 4pm: "We have 12 TCs to execute tomorrow. Suresh — you own the ASIL B 6. Ravi — you take the 3 visual. I take the remaining 3."
   - Bench booked 7am–1pm the next day

3. **Results — executed all 12 TCs by 2pm, one day before gateway:**
   - 10 passed
   - 2 failed: CLU-1071 (SRS wins over ABS simultaneously — incorrect) and CLU-1072 (cluster shows both P1 simultaneously — only one should show per ISO 2575 priority rule)
   - Both raised as P1 immediately

4. **Decision on disclosure — I chose to be transparent with the OEM:**
   - Told PM same day: "We found a coverage gap — 12 TCs not previously executed. We ran them today. 2 found real P1 defects that would have escaped. I recommend we disclose this at gateway and explain the corrective action."
   - PM agreed

5. **At gateway — stated it directly:**
   - "During our internal pre-gateway audit, we identified 12 TCs from requirement IC_SRS_TEL_REQ_020 had not been executed due to a sprint scheduling error. We executed all 12 yesterday. 10 passed. 2 P1 defects were found and are now on the defect register. The corrective process: we have updated the sprint planning checklist to include mandatory traceability matrix review in week 1 and week N-2 of each sprint."

### Result
- OEM validation lead: "We appreciate the proactive disclosure. Two P1s found before delivery is better than two P1s found in production."
- Gateway was conditioned — sign-off given pending P1 fix delivery, not cancelled
- CLU-1071 and CLU-1072 both fixed in IC_SW_v1.5.3 (SW priority logic corrected per ISO 2575)
- Verified passed — conditional gateway became full gateway 8 days later
- The traceability matrix review became a formal sprint checklist item across all LTTS IC projects
- I received internal recognition for transparency — explicitly mentioned in the project retrospective by the PM

---

## STAR 21 — Handling Customer Escalation Directly (Bypassing PM)

### Situation
The OEM customer lead (Renault validation manager) sent me a direct email at 7pm on a Thursday — bypassing our PM — with a list of 6 questions about a P1 defect (CLU-1024) that had been open for 9 days. The email tone was sharp: *"We are not satisfied with the pace of resolution. Please explain what is being done and when this will be fixed."* My PM was on a flight and unreachable for 6 hours.

### Task
Respond professionally and factually to the OEM without overstepping my authority, reassure the customer with evidence, and brief my PM as soon as they landed.

### Action
1. **Read all 6 questions — categorised them:**
   - Q1–Q3: Status and root cause of CLU-1024 (I know this fully)
   - Q4: Escalation path within LTTS (requires PM)
   - Q5: Impact on gateway date (requires PM)
   - Q6: What process change will prevent recurrence (I can answer partially)

2. **Responded within 90 minutes — factual, measured, no promises outside my authority:**

   *"Thank you for reaching out directly. Here is everything I can share right now:*

   *CLU-1024 Status: Root cause confirmed — ABS ECU DBC v2.2 used in test, cluster SW references v2.3 (bit position delta: Byte 0, Bit 0 → Bit 1). ABS ECU team confirmed fix in build ABS_SW_v3.1.1, ETA delivery to us: Monday 09:00. Our retest plan: Monday afternoon, results by 17:00.*

   *Q4 (escalation path) and Q5 (gateway impact): I am copying [PM name] on this reply — he will respond to those questions by [tomorrow] morning when he lands.*

   *Q6 (process change): I have already introduced a DBC version verification step at every bench session start. I can provide the updated process checklist.*

   *I understand the frustration. A 9-day P1 is not acceptable — this is also unacceptable to our team. I am personally on the retest Monday."*

3. **Immediately drafted a brief for PM:** Sent a 5-bullet WhatsApp summary so PM could read it on landing and respond to Q4 and Q5.

4. **Monday — retested as committed:** CLU-1024 passed on ABS_SW_v3.1.1. Results sent to OEM by 16:30.

### Result
- OEM responded: *"Thank you for the detailed response and for owning the Monday retest personally. This is the clarity we needed."*
- PM returned, reviewed my reply — no concern raised. PM told me: *"That's exactly how I would have answered it. Good call not to speculate on Q4/Q5."*
- CLU-1024 formally closed Tuesday — OEM satisfied with resolution speed once they had visibility
- No further direct bypassing of PM by OEM — the channel was re-established correctly
- I was given broader direct OEM communication authority for the rest of the project by PM

---

## STAR 22 — Running Retrospectives to Continuously Improve the Team

### Situation
After Sprint 06, I noticed the same types of issues repeating across sprints: TCs with vague expected results (fixed in Sprint 03, reappearing in Sprint 06), engineers not updating Jira on completion (raised in Sprint 04, still happening in Sprint 06). The team had no formal retrospective process. Problems were flagged, forgotten, and rediscovered.

### Task
Introduce a structured retrospective process that would capture lessons, assign owners to improvements, and actually close them — turning retrospectives from a venting exercise into a delivery improvement mechanism.

### Action
1. **Introduced a 30-minute retrospective at the end of every sprint — not optional:**

   Format (strict):
   ```
   10 min — What went well? (each person shares 1 item — not generic, specific)
   10 min — What didn't go well? (each person shares 1 item)
   10 min — Action items (max 3 items, each with owner + due date)
   ```

2. **The 3-action-item rule was important:**
   - Previous retrospectives had 12 "improvements" — none got closed
   - 3 items, owned, with a due date → accountability
   - Items carried to next retro until closed

3. **Sprint 07 retrospectives output (example):**
   ```
   ACTION 1: Ravi — Add SRS revision check to TC review checklist (due: Tue Sprint 08 Day 1)
   ACTION 2: Lead — Publish Jira board link in daily standup message (due: Sprint 08 Day 1)
   ACTION 3: Priya — Create a common CAPL script parameter CSV template (due: Sprint 08 Day 5)
   ```

4. **Built a retrospective tracker (1-page Google Sheet):**
   - Sprint | Action | Owner | Status | Closed date
   - Reviewed in first 5 minutes of the next sprint's retrospective

5. **Made "what went well" mandatory — not optional:**
   - Engineers in delivery pressure phases often only focus on problems
   - Naming what worked reinforced good patterns (e.g., "the daily progress board helped a lot")

### Result
- Sprint 08 opened with all 3 Sprint 07 actions closed — first time in the project
- TC rejection rate for vague expected results: 40% (Sprint 03) → 8% (Sprint 09)
- Jira update compliance: engineer self-reported at end of day → near 100% by Sprint 09
- The retrospective format was adopted across 3 other LTTS IC project teams
- My PM included the retrospec tracker as a project management best practice in his year-end report
- Engineers mentioned in 360 feedback: *"Finally a team that actually learns from each sprint"*

---

*File: 06_star_interview_scenarios.md | marelli_cluster_lead series*
