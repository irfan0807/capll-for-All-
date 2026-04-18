# STAR Format Scenarios — Automotive Project Manager
## April 2026

> **STAR = Situation → Task → Action → Result**
> These are realistic automotive PM interview scenarios using full detail.

---

### Scenario 1 — Managing a Supplier Delay That Threatened SOP

**Situation:**
I was the Project Manager for the integration of a 77GHz front radar sensor into a new vehicle platform at a Tier-1 automotive supplier. The radar hardware was being developed by a Tier-2 supplier overseas. Eight weeks before our critical hardware freeze milestone, the Tier-2 supplier informed us that their radar PCB had a design flaw in the RF front-end that would require a board spin — pushing hardware delivery 6 weeks later than agreed. Our SOP date was fixed at an OEM-level vehicle launch event and could not move. A 6-week hardware delay would cascade into a 6-week loss of system integration and vehicle test time, directly jeopardising the SOP.

**Task:**
My responsibility was to protect the SOP date, maintain OEM confidence, manage the supplier relationship, and produce a credible recovery plan within 72 hours of receiving the delay notification. I was accountable to both our internal programme manager and the OEM's chief engineer.

**Action:**
I immediately convened an emergency steering meeting and executed across four tracks simultaneously:

1. **Root cause & recovery assessment with Tier-2** — Flew to the supplier site within 48 hours with our HW lead. We reviewed the failure analysis, proposed board spin timeline, and negotiated for an accelerated prototype run (reduced board quantity with fast-turn PCB manufacturer). The Tier-2 committed to delivering 5 engineering sample boards in 4 weeks instead of 6 by prioritising our project and using an express PCB fabrication service.

2. **Parallel path with simulation** — Worked with our SW team lead to identify which SW integration activities could proceed using HIL (Hardware-in-the-Loop) simulation with a virtual radar model instead of waiting for real hardware. We identified 65% of SW integration tests could be executed on HIL, reducing the real hardware dependency window from 10 weeks to 4 weeks.

3. **Schedule rebaseline** — Rebuilt the project schedule with the recovery assumptions. Identified 3 non-critical test cycles that could be compressed (reduced regression depth from 3 full passes to 2 passes with risk acknowledgement). Critical path was maintained with a 1-week float buffer by the time of revised SOP.

4. **OEM communication** — Prepared a formal delay notification package (root cause, recovery plan, risk assessment, revised milestones) and presented it to the OEM's engineering team in a dedicated meeting. Was transparent about the root cause and presented the recovery options with confidence. The OEM accepted the plan and agreed to the revised schedule, noting the proactive management style.

5. **Risk entry and monitoring** — Raised a formal risk item in the project RAID log with weekly steering-level visibility. Set up a daily 15-minute standup with the Tier-2 supplier lead for the 4-week board spin period.

**Result:**
The Tier-2 delivered engineering samples in 3 weeks and 5 days (ahead of the 4-week recovery commitment). The parallel HIL SW integration track completed 62% of planned tests before hardware arrived, reducing the real-hardware integration phase by 3.5 weeks. The project delivered all mandatory SOP test evidence with 4 days of float remaining. SOP was not delayed. The OEM cited the transparent and structured supplier management as exemplary in the programme review. The lessons learned were published across the programme: all Tier-2 hardware milestones now have a mandatory 4-week float buffer in the master schedule.

---

### Scenario 2 — ASPICE Level 2 Assessment — Team Was Not Ready

**Situation:**
Six months into a new vehicle ADAS programme, the OEM scheduled a formal ASPICE Level 2 assessment — a contractual requirement. This was announced with only 8 weeks' notice. When I reviewed the team's ASPICE readiness, I found significant gaps: requirements had no unique IDs, review records were missing for the first three architecture reviews (no minutes taken), and the risk register had not been updated in 10 weeks. A failed assessment would trigger a contractual penalty clause and potentially put the programme at risk of being moved to a competing Tier-1 supplier.

**Task:**
My task was to lead the ASPICE assessment preparation, close all identified gaps within 8 weeks, and achieve a Level 2 result across all assessed process areas (MAN.3, SYS.1, SWE.1, SUP.9, SUP.10) without disrupting the ongoing SW development sprint cycle.

**Action:**
I ran a structured 8-week recovery plan:

**Week 1–2 — Gap Assessment:**
- Conducted an internal pre-assessment with our ASPICE coach against all required process areas
- Documented each gap with: evidence missing, owner, due date
- Identified 47 individual evidence gaps across 5 process areas

**Week 3–4 — Requirements Remediation:**
- Held a 2-day requirements workshop with the SW team to assign unique IDs to all 312 SW requirements
- Established a Requirements Traceability Matrix (RTM) in our tool (PTC Integrity)
- Retrospectively created review records for the 3 architecture reviews by collecting email chains, slide decks, and action items and formalising them into review minutes (with team attestation and dates)

**Week 5–6 — Process Compliance:**
- Updated and maintained the risk register weekly with documented risk owner, probability, impact, and mitigation status
- Established a configuration management baseline in Git with tags for each major release
- Updated the SUP.9 defect process: all open defects moved to JIRA with correct priority/status fields

**Week 7 — Internal Mock Assessment:**
- Ran a full mock ASPICE assessment with our quality team acting as assessors
- Found 6 remaining gaps — all minor (missing timestamps in two review records, 4 defects without root cause entries)
- Closed all 6 in 2 days

**Week 8 — OEM Assessment:**
- Hosted the OEM ASPICE assessors for a 3-day on-site assessment
- Provided evidence walkthroughs for each process area
- Fielded all technical questions with the relevant process owner present

**Result:**
The ASPICE assessment resulted in **Level 2 achieved across all 5 assessed process areas** with zero Level 1 findings. There were 4 minor improvement notes (not weaknesses) that were incorporated into the next quarter's process improvement plan. The OEM assessment team noted the quality of the Requirements Traceability Matrix as a best practice example. The contractual penalty clause was not triggered. The programme retained full OEM confidence. The 8-week preparation template I developed was standardised and reused for two subsequent programmes.

---

### Scenario 3 — Budget Overrun Identified at Mid-Project Review

**Situation:**
During the mid-project Earned Value Management review of an infotainment ECU project (total budget €1.8M, 18-month programme), I identified that the project was tracking at a Cost Performance Index (CPI) of 0.82 — meaning for every €1 spent, we were only delivering €0.82 of planned value. At this trajectory, the project would finish at an Estimated at Completion (EAC) of €2.19M — a €390K overrun. The primary driver was SW integration effort having been severely underestimated: the integration phase had consumed 40% more hours than planned due to unexpected interface compatibility issues between the new infotainment HU and the existing BCM software.

**Task:**
My task was to present the cost situation to the programme steering committee, propose credible corrective measures, and either contain the overrun within a 10% approved contingency (€180K) or formally request an exception from the customer with a justified business case.

**Action:**
I took a transparent and structured approach:

1. **Detailed cost driver analysis** — Broke down the overrun by work package. Found that 78% of the overrun was in integration testing (unexpected interface defects requiring multiple rework cycles). The remaining 22% was in documentation (an OEM requirement change had added 40 pages to the SW architecture document mid-project).

2. **Corrective action for integration** — Worked with the SW lead to implement a triage protocol: defects were now severity-ranked and only ASIL-relevant and integration-blocking defects were addressed in the current sprint. Cosmetic and non-blocking defects were deferred to a post-SOP maintenance release. This reduced active integration rework effort by approximately 25%.

3. **Scope negotiation with OEM** — The documentation overrun was directly caused by an OEM-initiated requirement change. Raised a formal change request (as per contract), documented the change, the impact, and the additional cost of €88K. The OEM accepted and approved the additional budget for this scope change.

4. **Resource reallocation** — Identified one senior engineer who had completed his architecture work and was available. Reassigned him to integration support, absorbing 3 weeks of integration effort without additional cost.

5. **Revised EAC** — After corrective actions, reforecast EAC was €1.94M — a €140K overrun, within the 10% approved contingency of €180K.

6. **Steering committee presentation** — Presented the full picture: root cause, corrective actions taken, new EAC, and request for OEM change approval for the €88K scope change. No surprises were hidden.

**Result:**
The steering committee approved the revised EAC of €1.94M and the OEM approved the €88K scope change. Final project cost came in at €1.97M — a €170K overrun, just within the approved contingency. The CPI recovered to 0.91 by project close. The root cause (underestimated integration effort) was documented in lessons learned and a 25% integration complexity buffer was added to the estimating model for all future infotainment projects in the business unit.

---

### Scenario 4 — Key Engineer Resigned 4 Months Before SOP

**Situation:**
With 4 months remaining before SOP on a body control module (BCM) project, the project's only AUTOSAR configuration expert — who held unique knowledge of the entire BSW configuration — resigned to join a competitor. No other team member had sufficient depth in AUTOSAR EB Tresos to maintain or modify the BSW configuration. Several critical SOP-blocking defect fixes required AUTOSAR BSW changes. Without this engineer, the project faced a severe single-point-of-failure risk.

**Task:**
My task was to manage the knowledge transfer, secure an immediate replacement or interim resource, and ensure the SOP was not impacted while managing the sensitive HR and contractual situation of the departing engineer.

**Action:**
I immediately activated a four-track plan:

1. **Knowledge transfer during notice period** — Worked with HR to confirm the engineer would work his full 4-week notice period. Created a structured knowledge transfer plan with daily 2-hour sessions covering: BSW configuration architecture, tool setup (EB Tresos), known quirks and workarounds, SOP-blocking defect backlog. All sessions were recorded and notes taken by two team members simultaneously.

2. **Internal upskilling** — Identified two engineers with partial AUTOSAR knowledge and enrolled them in a 3-day EB Tresos AUTOSAR training with Vector. During the notice period, they shadowed the departing engineer on all real tasks.

3. **External contractor** — In parallel, engaged our preferred supplier framework to hire an AUTOSAR BSW contractor. The contractor started exactly on the day the engineer left. Contractor was given the recorded knowledge transfer materials and paired with one of the two upskilled engineers for the first 2 weeks.

4. **Scope triage** — Reviewed all remaining SOP-blocking items requiring AUTOSAR BSW changes. Identified 3 that were genuinely SOP-critical and 4 that could be deferred to a post-SOP patch release. Formally agreed the deferral with the OEM in writing, documenting the rationale.

**Result:**
The contractor became effective within 2 weeks (faster than expected due to the structured knowledge transfer materials). All 3 SOP-critical AUTOSAR defects were resolved on schedule. The 4 deferred items were delivered in a maintenance release 6 weeks after SOP as planned. The SOP date was not impacted. The incident led to a new policy: all projects must maintain a minimum of 2 people competent in each safety/critical knowledge domain. A skills matrix is now reviewed at every project phase gate.

---

### Scenario 5 — OEM Changed Requirements 3 Months Before SW Freeze

**Situation:**
Three months before SW code freeze on an ADAS Level 2 system, the OEM's programme team requested a new feature addition: "Driver Attention Warning Integration" — displaying a driver drowsiness alert on the instrument cluster when the ADAS domain controller detected fatigue. This was not in the original scope. The OEM sent it as a "customer requirement change" email expecting fast acceptance. Analysis showed the change required: new CAN signal definition, cluster display asset design, HMI approval cycle, SW implementation (BCM + cluster), and re-testing of affected functions. Estimated impact: 8 weeks of work, €120K cost, and the change would push SW freeze by 3 weeks.

**Task:**
My task was to manage the requirement change through the formal change control process, protect the team from uncontrolled scope creep, negotiate with the OEM, and either deliver the feature within the existing timeline (not feasible) or obtain a formal change order with schedule and cost adjustment.

**Action:**
1. **Formal change request raised immediately** — Generated an ECR (Engineering Change Request) within 24 hours of the OEM email. This formally placed the request in the change control process and prevented informal acceptance by any team member.

2. **Impact analysis in 5 days** — Allocated the affected tech leads to produce a detailed impact analysis: SW effort (BCM: 3 weeks, cluster: 2 weeks), test effort (3 weeks regression), signal definition (1 week with OEM CAN team), HMI assets (1 week), documentation (1 week). Total: 11 weeks work across teams with 8 weeks calendar time (parallel tracks).

3. **Change Control Board (CCB)** — Chaired a CCB with internal programme director, SW lead, safety officer, and OEM representative. Presented 3 options:
   - **Option A:** Include feature in current SOP — requires 3-week SW freeze extension, €120K additional budget, OEM to approve both formally
   - **Option B:** Defer to SOP+6 maintenance release — SOP unaffected, feature available in first OTA update post-launch
   - **Option C:** Descope the HMI display integration (retain only the CAN signal) — partial implementation, reduces impact to 4 weeks, €60K

4. **OEM negotiation** — The OEM initially pushed back on any delay, arguing the feature was commercially critical. I presented the detailed analysis showing the impact was driven by their HMI approval process (which required 4 weeks on their side). After discussion, the OEM accepted **Option B** — defer to SOP+6 — as it minimised risk to the SOP gate while committing to the feature's delivery.

5. **Formal ECO issued** — An Engineering Change Order was issued, formally closing the ECR, documenting the agreed decision, scheduling the feature for the SOP+6 release, and allocating the work to the next project phase.

**Result:**
SOP date was protected with no scope addition to the current release. The OEM signed the ECO within 1 week. The deferred feature was delivered on schedule in the SOP+6 maintenance release as an OTA update. The incident was used as a training example for the team: all OEM requirement emails must be logged in the change management system within 24 hours — no verbal acceptance. The project's change control metrics showed 100% changes handled via formal ECR/ECO process from that point onwards.

---

### Scenario 6 — Cross-Cultural Team Conflict Between Germany and India Teams

**Situation:**
On a distributed ADAS software project, the SW architecture team was located in Munich, Germany, and the SW implementation and test team was in Bangalore, India. Significant tension developed between the teams: the Munich team complained that the Bangalore team was not implementing the architecture correctly and kept implementing their own solutions. The Bangalore team complained that the Munich architecture documents were arriving late, with insufficient detail, and that they were blocked waiting for reviews. This was causing integration defects, rework, and a growing backlog. Team morale was declining on both sides.

**Task:**
My task was to resolve the interpersonal and process conflict, restore collaborative working, and eliminate the architecture compliance defects within the remaining 3 months of the project.

**Action:**
I approached this as both a process and a people problem:

1. **Listening sessions first** — Held individual 1:1 calls with the tech leads on both sides (not in the same call initially). Listened without judgment to understand each team's genuine frustrations. Found:
   - Munich: documents were actually being delivered on time, but the Bangalore team was not raising clarification questions — just implementing their interpretation
   - Bangalore: they felt "second class" — decisions were made in Munich without consultation, architecture reviews were held at 7pm their local time (convenience for Munich, late for India)

2. **Process fixes** — Implemented three process changes:
   - All cross-site architecture reviews rescheduled to 2pm CET / 5:30pm IST (fair compromise)
   - Introduced a "specification Q&A freeze" period: 3 working days after document release, Bangalore team raises all questions in a shared doc, Munich answers in writing within 2 days
   - Architecture compliance review added to Bangalore's sprint definition of done — no task closed without confirmation of architecture alignment

3. **Joint working session** — Arranged a 2-day in-person sprint planning session by having 3 Munich architects fly to Bangalore. This was a deliberate signal that Munich valued the Bangalore team's input. The joint session produced a shared integration roadmap and resolved 11 open architecture interpretation issues.

4. **Regular cross-site sync** — Established a weekly 30-minute Cross-Site Architecture Review meeting (rotating note-taker from each site). Both tech leads co-chaired it.

5. **Recognition** — Explicitly recognised both teams' contributions in my monthly programme update to senior leadership, highlighting specific examples from Bangalore's implementation quality.

**Result:**
Architecture compliance defects dropped from 14 open items to 2 within 6 weeks of the changes. The 2 remaining were dependency issues unrelated to the conflict. Sprint velocity in Bangalore increased by 18% as blockers from waiting for architecture clarification were eliminated. Both tech leads reported improved collaboration in their feedback. One Bangalore architect was nominated by the Munich team lead for an internal excellence award. The joint-working model was adopted as the standard for all future cross-site programmes in the business unit.

---

### Scenario 7 — ISO 26262 Safety Conflict vs Schedule Pressure

**Situation:**
Five weeks before the final SOP gate, the project's Safety Manager raised a formal objection that a safety mechanism in the high-speed CAN communication monitor had a gap in its fault coverage: a specific hardware single-point fault (stuck-at-1 on a CAN transceiver pin) was not covered by any detection mechanism, despite an ASIL-C requirement for diagnostic coverage. The SW team lead estimated that implementing the diagnostic coverage would require 3 weeks of SW development and 2 weeks of re-testing. This 5-week addition would breach the SOP date.

There was significant programme pressure (the OEM had €200M in committed marketing spend tied to the vehicle launch date). The programme director and OEM engineers informally suggested we "accept the residual risk and document it."

**Task:**
My task was to navigate this conflict between safety obligations and schedule pressure — without compromising the legal and ethical requirements of ISO 26262, while finding every possible way to minimise the schedule impact.

**Action:**
I took a principled and systematic approach:

1. **Confirmed the safety manager's finding was valid** — Had the Safety Manager and SW architect jointly review the finding. It was confirmed: the fault was a single-point fault on an ASIL-C function, and ISO 26262 does not permit accepting unmitigated single-point faults at ASIL-C without a compensating measure. Informal risk acceptance by the programme director was not a valid ISO 26262 mechanism.

2. **Documented my position formally** — Sent a written communication to the programme director and the OEM safety representative confirming that informal verbal risk acceptance was not compliant with ISO 26262 Part 4 clause 7 (safety validation) and that proceeding without mitigation would invalidate the Safety Case and potentially expose the company to product liability.

3. **Explored technical options to reduce the 5-week estimate** — Together with the Safety Manager and SW lead, identified an alternative mitigation approach: instead of a full new diagnostic routine, a simplified end-to-end E2E check (already partially implemented in a different module) could be adapted and reused for this fault coverage gap. This reduced the implementation estimate from 3 weeks to 8 days.

4. **Compressed the test cycle** — Proposed a risk-based test strategy: instead of a full regression, run only the targeted CAN monitor test suite plus the affected integration tests (not the full system test suite). Agreed with the OEM test lead that full regression would run post-SOP as a confirmatory test for the production vehicle fleet, with a formal waiver approved at OEM steering level.

5. **Presented the SOP impact** — Final revised impact: 12 days of SW work + 8 days of targeted testing = 20 calendar days. With parallel HIL test preparation starting immediately, net schedule impact was 14 calendar days. SOP was pushed by 2 weeks — formally approved by the OEM.

**Result:**
The safety gap was properly mitigated. The Safety Case was completed without exceptions. The 2-week SOP slip was accepted by the OEM after I presented the legal and liability implications of proceeding without mitigation. The revised SOP was held. The vehicle launched successfully. Post-SOP confirmatory regression passed with zero findings. The programme director later acknowledged that my insistence on maintaining the safety process was correct. The incident was used as a case study in the company's safety culture training programme.

---

*File: 03_star_scenarios.md | Automotive PM Interview Prep | April 2026*
