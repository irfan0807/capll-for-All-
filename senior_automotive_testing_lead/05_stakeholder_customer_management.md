# Section 5: Stakeholder & Customer Management
> **Role**: Senior Automotive Testing Team Lead | **Questions**: Q45–Q52

---

## Q45: How do you communicate test status to a demanding OEM customer?

### Question
Your OEM customer calls every morning asking for updates. They are dissatisfied with the level of reporting detail. How do you structure stakeholder communication?

### Detailed Answer

**Stakeholder Communication Strategy:**

**Principle: Proactive > Reactive**
A weekly structured report eliminates the need for daily calls. If you provide meaningful, accurate reports before they ask, the number of ad-hoc calls drops significantly.

**Weekly Test Status Report (sent every Monday morning):**

```
SUBJECT: [OEM-XYZ / Cluster ECU] Week 32 Test Status Report — v3.4.1

Executive Summary:
  Overall Status: 🟡 AMBER (execution on track; 2 P1 defects under SW investigation)

Test Execution Progress:
  Total TCs:     1125
  Executed:       892 (79%)
  Passed:         834 (93.5% pass rate)
  Failed:          42
  Blocked:         16 (blocked: waiting for SWv3.5.0 fix for Defect #1023)
  Not Run:        233

  Milestone tracking: SOP-6 milestone target: ≥ 85% RTM | Current: 79% | Status: ✓ On track

Open Defects:
  P1: 2 (Defect #1019: Speedometer CAN timeout — fix ETA Fri; #1020: ABS tell-tale delay)
  P2: 7
  P3: 18
  P4: 11

Top Risks This Week:
  R01: P1 #1019 (Speedometer) — SW root cause identified; fix in 3.5.0 expected Friday
  R02: HIL bench CH2 intermittent — hardware team investigating; fallback: manual testing

Plan This Week:
  - Test areas: Fuel gauge, Temperature signals, Climate tell-tales
  - Execute: 120 TCs
  - Target: Reach 90% execution by Wk-33
```

**Communication Norms with OEM:**
| Situation | Response |
|-----------|---------|
| Routine progress | Weekly report (every Monday) |
| P1 defect found | Same-day email + call if safety-related |
| Milestone at risk | 1 week advance warning email + mitigation plan |
| Critical blockers | Immediate call + root cause within 24 hours |
| Meeting requests | Structured agenda sent 24h in advance; minutes within 4 hours |

**How to handle a demanding customer who wants daily calls:**
- *"I understand you need frequent visibility. I propose a daily 10-minute status email at 8 AM with key metrics. If any metric is amber or red, I will proactively schedule a call. This gives you real-time visibility without consuming either team's time on routine status."*
- Most OEMs accept this after seeing the first two reports.

**Key Points ★**
- ★ Proactive, regular reports with actual numbers eliminate surprise-driven escalations.
- ★ Never report just a RAG status without explaining WHY it is amber/red — customers rightly distrust unexplained statuses.
- ★ Deliver bad news early with a plan — a P1 defect at SOP-2 weeks with a recovery plan is better than silence.

---

## Q46: How do you handle a production escalation from an OEM?

### Question
An OEM customer calls on a Friday afternoon: 10 vehicles in production have a Cluster defect showing wrong speed at >200 km/h. How do you handle this escalation?

### Detailed Answer

**Escalation Response Framework: OODA Loop (Observe → Orient → Decide → Act)**

**Hour 0–1: Immediate Response**
```
1. Acknowledge to OEM within 15 min: "Confirmed receipt. Assembling technical team now."
2. Create War Room: Test Lead + Senior Tester + SW developer + system architect
3. Gather all available evidence:
   - Exact DTC/log from affected vehicles
   - CAN trace from any affected vehicle (if captured)
   - SW version on affected vehicles
   - Which market/plant produced them
```

**Hour 1–3: Rapid Investigation**
```
Reproduce on bench:
  1. Configure HIL bench to simulate >200 km/h speed on CAN
  2. Observe Cluster behavior: does bug reproduce?
  
If reproduced → proceed to root cause
If not reproduced → ask OEM for exact SW ver + VIN for one vehicle → pull build from archive → flash bench ECU
```

**Root Cause Analysis (Rapid 5-Why):**
```
Bug: Speed display > 200 km/h shows wrong value (displays 201 as 101 — halved)
  Why? Speed signal value > 200 → cluster rendering truncates to 7-bit display range max (128)
  Why? CAN signal decode: 8-bit display buffer used for value > 8-bit range (255 max, but gauge shows 200 max)
  Why? Gauge sweep logic applies range clamp: 0–200 for display, but CAN raw 16-bit not correctly mapped to gauge pixels for >200
  Why? No test case existed for speed > 200 km/h (spec said max display 220; no test at 201–220)
  
Root cause: Missing boundary test case (speed at 201–220 km/h range)
```

**Communication to OEM (within 4 hours):**
```
EMAIL: [URGENT] Cluster Speed Display Escalation — Root Cause + Mitigation Plan

We have reproduced and identified the root cause:
  - Issue: Speed signal > 200 km/h displayed incorrectly due to gauge pixel mapping calculation
  - SW versions affected: v3.2.1, v3.3.0 (pre-v3.4.0)
  - Vehicles affected: units with SW < v3.4.0 (released 3 weeks ago — not yet in affected cars)

Immediate actions:
  1. SW fix: identified; patch ready by Monday EOD
  2. Field fix: OTA update to v3.4.1 (patch) prepared for deployment to all affected VINs
  3. Production line: already on v3.4.0 — no further affected vehicles from today's production

Testing team corrective action:
  1. New test: TC-SPD-220 (speed at 201, 210, 219, 220 km/h) added to regression suite immediately
  2. Root cause: missing boundary test. CAPA: add >200 km/h range to test specification

Timeline: SW patch tested and OTA-ready: Tuesday 20th.
```

**Key Points ★**
- ★ OEM escalations require a response within minutes, not days — have an escalation playbook ready before it happens.
- ★ Always communicate: what happened, which vehicles are affected, what the fix is, and when it will be deployed — in that order.
- ★ The corrective action (new test case, CAPA) is as important to the OEM as the fix — it shows process maturity.

---

## Q47: How do you handle a scope change (Change Request) from an OEM mid-project?

### Question
With 4 weeks until the SOP milestone, the OEM requests 3 additional features to be tested (not in the original SRS). How do you handle this?

### Detailed Answer

**Change Request (CR) Process:**

**Step 1: Don't say yes or no immediately — assess first**
```
Team Lead response to OEM: 
  "We've received the CR. We will perform an impact analysis and come back within 48 hours."
  
  Internal Impact Analysis:
    Feature A: Android Auto Wireless (new)
      Test cases needed: ~40 new TCs
      New tool required: Wi-Fi channel analyser (we don't have)
      Additional effort: 8 person-days
      Risk: Requires new HW (Wi-Fi AP in HIL bench) — procurement: 1 week lead time
    
    Feature B: Rear camera + cluster display integration (new)
      Test cases: ~25 new TCs
      Effort: 5 person-days
      Risk: Camera injection in HIL not yet configured
      
    Feature C: Emergency services message on cluster (existing feature — minor change)
      Test cases: 3 modified TCs already exist
      Effort: 0.5 person-days
      Risk: Low
      
    Total new effort: ~14 person-days
    Available capacity in 4 weeks (3 engineers): ~60 PD available; already committed ~52 PD
    Free capacity: 8 PD → insufficient for all 3 features without scope trade-off
```

**Step 2: Present the options to OEM**
```
EMAIL: CR Impact Analysis — 3 Options for OEM Decision

Option 1 (Preferred): Accept Feature C (minor) + defer A and B to post-SOP regression
  Impact: SOP milestone on time; Feature C tested fully; A and B in next release
  
Option 2: Accept all 3 features; extend SOP by 2 weeks
  Impact: Full scope tested; SOP delayed 2 weeks (impacts production schedule)
  Cost: Additional €15K (team extension 2 weeks)
  
Option 3: Accept Feature C + B; descope 10 P4 tests from existing scope
  Impact: SOP on time; all 3 features in, but 10 low-risk TCs deferred
  Risk: Low (P4 features are cosmetic)

Recommendation: Option 3 (balanced scope/schedule trade-off)
Decision required by: Wednesday to preserve SOP timeline
```

**Step 3: Formal CR documentation**
- CR form: description, requestor, date, effort impact, schedule impact, decision, sign-off by both OEM and PM.
- Update RTM, test plan, and project schedule after approval.

**Key Points ★**
- ★ A CR without a formal process and sign-off is invisible scope creep — it will cause a missed deadline with no accountability.
- ★ Always give options with clear trade-offs — customers appreciate choice; "we can't do it" with no alternative is seen as lack of proactivity.
- ★ Everything discussed verbally about CRs must be in writing — automotive OEMs will hold you to verbal commitments.

---

## Q48: How do you manage requirements clarifications from a Tier-1 customer?

### Question
You receive a requirement that says "The Cluster shall display vehicle speed accurately." This is vague. How do you clarify it?

### Detailed Answer

**Requirement Quality Issues (SMART analysis):**
- Specific? NO — "accurately" is undefined.
- Measurable? NO — no numeric threshold.
- Achievable? Unknown — depends on sensor accuracy.
- Relevant? Yes.
- Testable? NO — cannot write a pass/fail test case against "accurately."

**Clarification Process:**

**Step 1: Draft targeted clarification questions**
```
Requirement Clarification Request (formal document):
  Requirement ID: CLUS-REQ-045
  Original: "Cluster shall display vehicle speed accurately"
  
  Questions for OEM:
    Q1: What is the acceptable display accuracy? (e.g., ±2% or ±2 km/h at 60 km/h)
    Q2: What is the speed range to be validated? (0–220 km/h? 0–340 km/h?)
    Q3: What is the CAN signal source and its stated accuracy? (wheel speed sensor: ±0.5 km/h?)
    Q4: What is the display update rate? (100 ms? 200 ms?)
    Q5: Is the requirement ASIL-rated? If yes, which ASIL level?
    
Submitted to: OEM Systems Team Lead
Deadline for response: MM/DD (7 days)
```

**Step 2: Propose a testable interpretation while waiting**
```
Proposed derived requirement (for internal planning):
  CLUS-REQ-045a: Speed displayed on cluster shall match CAN signal VehicleSpeed
                  within ± 2 km/h for speeds 0–240 km/h.
  CLUS-REQ-045b: Speed display shall update within 200 ms of CAN signal change.
  CLUS-REQ-045c: When CAN signal is invalid/timeout, display shall show dashes
                  within 500 ms.
                  
Status: Provisional (pending OEM confirmation). Test cases designed against these;
        will update upon OEM response.
```

**Step 3: Track open requirement clarifications**
- JIRA board: "Requirement Open Issues" — every unanswered clarification tracked.
- Weekly report to PM: how many open clarifications and their impact on test design.

**Key Points ★**
- ★ Never design test cases against ambiguous requirements — you will discover the mismatch at OEM acceptance and lose weeks.
- ★ Proposed derived requirements (with OEM confirmation) are better than "waiting" — keeps the team moving.
- ★ Track requirement clarification turnaround time — slow OEM responses are a project risk; document them.

---

## Q49: How do you prepare and present a weekly test dashboard to project management?

### Question
Your PM asks for a new weekly dashboard format that both non-technical managers and technical leads can use. Design it.

### Detailed Answer

**Two-Level Dashboard Design:**

**Level 1: Management Summary (1 page, RAG-based)**
```
PROJECT: Infotainment Head Unit | WEEK: 32 | SW BUILD: v4.1.2

┌────────────────────────────────────────────────────────────┐
│ OVERALL STATUS:  🟡 AMBER                                   │
│ Key Concern: 2 P1 defects open; SW fix expected Fri        │
└────────────────────────────────────────────────────────────┘

EXECUTION PROGRESS:
  ████████████████░░░░  79% | 1125 TCs total | 892 executed | 234 remaining

DEFECT SUMMARY:
  🔴 P1: 2  |  🟠 P2: 7  |  🟡 P3: 18  |  🔵 P4: 11  |  Total: 38 open

MILESTONE: SOP-6 (in 3 weeks)  →  Status: ✅ ON TRACK (target 85% execution; current 79%)

RISKS:
  1. P1 #1019 Speed CAN timeout: SW fix ETA Friday (Wk32)  → Impact: 16 blocked TCs
  2. HIL Bench CH2: hardware repair in progress → Recovery: new bench ordered (ETA Mon Wk33)

PLAN NEXT WEEK:
  → Execute 120 TCs (Climate, HVAC, Tell-tales)
  → Retest P1/P2 fixes delivered in v4.1.3
  → Target: ≥ 90% execution by Wk33
```

**Level 2: Technical Detail (for Test Lead + Dev Lead)**
```
DETAILED METRICS (Week 32):

Execution:
  Feature       | Total | Exec | Pass | Fail | Blocked | Coverage
  Speed/RPM     |   85  |  85  |  83  |   2  |    0    | 100%
  Tell-tales    |  200  | 180  | 175  |   4  |    1    |  90%
  Bluetooth     |   95  |  60  |  55  |   4  |    1    |  63% ← lagging
  Navigation    |  120  | 100  |  92  |   6  |    2    |  83%
  
Defect Aging:
  #1011 P2 (opened 12 days ago): assigned Dev=Suresh; ETA missed → ESCALATE
  #1019 P1 (opened 3 days): root cause found; patch in progress ✓
  
Automation Coverage:
  Automated TCs: 620/1125 (55%)  |  Last CI Run: 598 pass / 14 fail
  New scripts added this sprint: 12
  
Traceability:
  RTM Coverage: 87% (1125 reqs, 977 with at least 1 passed TC)
```

**Key Points ★**
- ★ Two-level dashboards serve two audiences — never send a 4-page technical report to a VP, and never send a 1-page summary to a test architect expecting detail.
- ★ RAG statuses without numbers are meaningless — always pair green/amber/red with a metric.
- ★ Defect aging is one of the most powerful risk indicators — a P2 open 12 days is a process failure, not just a technical one.

---

## Q50: How do you prepare for and handle an OEM ASPICE assessment?

### Question
In 6 weeks you have an ASPICE Level 2 assessment by the OEM. How do you prepare your team and documentation?

### Detailed Answer

**ASPICE Level 2 Assessment — Key Processes for Test Team:**

| ASPICE Process | Relevance to Testing | Key Evidence Required |
|---------------|---------------------|----------------------|
| SWE.4 Software Unit Verification | Unit testing coverage, test cases | Unit test reports, code coverage |
| SWE.5 Software Integration Test | Integration test design, execution | Test plan, test cases, execution logs |
| SWE.6 Software Qualification Test | System-level test, traceability | STP, test cases, RTM, test reports |
| SUP.9 Problem Resolution Management | Defect lifecycle | JIRA defect records, fix evidence |
| SUP.10 Change Request Management | CR process | CR forms, CR register |
| MAN.3 Project Management | Planning, monitoring | Project plan, status reports |

**6-Week Preparation Plan:**

```
Week 1: Gap Analysis
  → Review all test artefacts against ASPICE L2 checklist
  → Common gaps:
       - Test cases not directly linked to requirements in RTM
       - Test reports lack pass/fail criteria rationale
       - Defect records missing root cause documentation

Week 2–3: Documentation Catch-Up
  → Complete RTM: every requirement → at least 1 test case link
  → Add missing test result evidence to ALM
  → Document test environment configuration (bench setup doc)
  → Ensure defect records have: description, root cause, fix, retest evidence

Week 4: Internal Mock Audit
  → Team Lead conducts internal ASPICE walkthrough
  → Role-play: "How do you demonstrate this test case is derived from a requirement?"
  → Identify remaining gaps; fix in Week 5

Week 5: Final Document Review
  → All test plans signed/approved by relevant stakeholders
  → All test reports generated and archived
  → JIRA/ALM clean-up: no orphaned defects, no un-linked test cases

Week 6: Assessment Prep
  → Brief all team members on ASPICE terminology and what to expect
  → Prepare Q&A pack: common assessor questions + your answers
  → Logistics: meeting room, sample project walk-through prepared
```

**Common ASPICE Assessor Questions for the Test Lead:**
- *"Show me how you trace from this OEM requirement to a test case to a defect."*
- *"What are your entry and exit criteria for system testing?"*
- *"How do you handle a requirement change after test cases are designed?"*
- *"How do you verify that a defect is truly fixed before closing it?"*

**Key Points ★**
- ★ ASPICE L2 is achievable with discipline — it is a process capability assessment, not a technical audit.
- ★ Traceability is the single most frequently failed area — invest 50% of your prep time here.
- ★ The internal mock audit in Week 4 is the most valuable preparation activity — it finds the gaps before the assessor does.

---

## Q51: How do you manage a situation where developer insists a defect is "not a bug"?

### Question
Your tester raises a defect: "Climate tell-tale flashes for 2 seconds on boot — incorrect behavior." Developer responds: "That is by design, we added a post-boot lamp test." How do you resolve this?

### Detailed Answer

**Root of the Problem:**
- Missing requirement: the lamp test behavior was added by developer without a documented requirement.
- No test case for the new behavior: tester correctly identified unspecified behavior as a defect.

**Resolution Process:**

**Step 1: Check the requirement**
- Pull up CLA-REQ-089 (Climate tell-tale behavior).
- Spec says: "Climate tell-tale shall illuminate when AC is active."
- No mention of 2-second post-boot lamp test.
- **Conclusion: the behavior is undocumented; it may be intentional but it is unspecified.**

**Step 2: Escalate to systems team (not argue with developer)**
*"The defect is about an undocumented behavior. The question is: should a lamp test be performed at boot? If yes, it needs a requirement. I am escalating to the systems team to determine if CLA-REQ-089 should be updated or if the behavior should be removed."*

**Decision paths:**
| Systems Decision | Action |
|----------------|--------|
| Lamp test is intended: add to SRS | Add requirement; update RTM; create test case; close defect as "by design per NEW requirement" |
| Lamp test is not required: remove it | Developer removes 2-second flash; defect valid; fix and close |

**What NOT to do:**
- Do not close the defect as "WONTFIX" without a documented basis.
- Do not argue directly with the developer — escalate to the requirement/system owner.
- Do not accept "it's done in other OEM projects too" as justification — each project has its own spec.

**Key Points ★**
- ★ "Not a bug" claims always require a spec reference — if behavior is undocumented, it is always a question for the systems team, not a unilateral developer decision.
- ★ Never let the developer close their own defects — independent test team retest is a fundamental quality gate.
- ★ Undocumented features found in testing are a risk for ASPICE audits — every feature must have a requirement.

---

## Q52: How do you communicate a test milestone delay to a customer without damaging trust?

### Question
You discover on Wednesday that the system test milestone (due Friday) will not be met due to a critical P1 defect. How do you communicate this?

### Detailed Answer

**Communication Principle: "No surprise delays"**

**Never wait until Friday to tell the customer. Tell them Wednesday with a plan.**

**Wednesday email structure:**
```
SUBJECT: [Cluster ECU] System Test Milestone — At Risk Notification + Mitigation Plan

Dear [OEM Customer Name],

I am writing to proactively inform you that the System Test milestone planned for 
Friday 18 April is at risk.

Situation:
  A P1 defect (Defect #1042: Speed display incorrect under Bus-off recovery) was 
  identified today during regression. This defect:
  - Impacts 34 test cases which cannot complete without a stable build
  - Is reproducible and confirmed (not user error or bench issue)
  
Developer team status: root cause identified, fix in progress, patch expected Thursday EOD.

Impact:
  Without the Thursday patch, 34 TCs (out of 1125) cannot be executed by Friday.
  Adjusted options for your decision:

Option 1: Extend milestone by 3 working days (to Wednesday 23 April)
  → All 1125 TCs executed fully; full RTM coverage achieved
  → Recommend this option

Option 2: Proceed with Friday milestone; 34 TCs deferred to follow-up patch release
  → Milestone passes with 97% coverage; remaining 3% (34 TCs) completed in v4.2.0 patch window

Action Required: Please advise preference by Thursday 9 AM so we can plan accordingly.

I will call you at 11 AM Thursday to discuss.

Regards,
[Your Name] — Test Lead
```

**Key Points ★**
- ★ Communicating 48 hours early with a plan preserves trust. Informing on the deadline day destroys it.
- ★ Always present options — customers need to feel in control; giving them a decision preserves the relationship.
- ★ Own the process issue in the next retrospective — missing a milestone is always partly a process failure, even if triggered by a P1 defect.
