# Stakeholder & Risk Management — Automotive Project Manager
## April 2026

---

## 1. Stakeholder Management

### 1.1 Typical Automotive Project Stakeholders

```
                            OEM (Customer)
                         ┌──────────────────┐
                         │ Chief Engineer    │
                         │ Programme Manager │
                         │ Safety Officer    │
                         │ Purchasing        │
                         │ Quality           │
                         │ Homologation/Regs │
                         └─────────┬────────┘
                                   │
                         ┌─────────▼────────┐
                         │  Tier-1 (YOU)     │
                         │ Project Manager   │
                         │ SW Lead           │
                         │ HW Lead           │
                         │ Safety Manager    │
                         │ Test Lead         │
                         │ Quality Manager   │
                         └──────┬────────────┘
              ┌─────────────────┼─────────────────┐
    ┌─────────▼────────┐  ┌─────▼──────┐  ┌───────▼──────┐
    │ Tier-2 Supplier  │  │ Tool/IP    │  │ Test Lab /   │
    │ (HW components,  │  │ Vendor     │  │ HIL Partner  │
    │ radar, sensors)  │  │ (Vector,   │  │              │
    └──────────────────┘  │ ETAS, EB)  │  └──────────────┘
                          └────────────┘

Internal Stakeholders:
  - Finance / Controlling
  - HR / Recruitment
  - Legal / Contracts
  - Production / Manufacturing Engineering
  - After-sales / Service
```

### 1.2 Stakeholder Register Template

| Stakeholder | Role | Interest | Influence | Current Engagement | Target Engagement | PM Strategy |
|-------------|------|----------|-----------|-------------------|------------------|-------------|
| OEM Chief Engineer | Customer decision maker | Feature delivery, quality, SOP | Very High | Neutral | Supportive | Weekly status report, proactive risk disclosure |
| OEM Purchasing | Contract & cost control | Budget, change orders | High | Supportive | Supportive | Involve in all scope change discussions early |
| OEM Safety Officer | Safety compliance | ISO 26262, ASIL findings | High | Monitoring | Supportive | Regular safety status updates, no surprises |
| Internal SW Lead | SW delivery | Technical quality, team load | High | Supportive | Leading | Daily standups, remove blockers fast |
| Tier-2 Radar Supplier | Component delivery | Order fulfilment | Medium | Neutral | Committed | Regular milestone reviews, contractual monitoring |
| Internal Finance | Budget control | Cost variance | Medium | Monitoring | Informed | Monthly EVM report |
| Production Engineering | EOL station readiness | SOP production capability | Medium | Not engaged | Informed | Pull into project 6 months before SOP |

### 1.3 Stakeholder Engagement Matrix (Power/Interest Grid)

```
        HIGH POWER
        │
        │  MANAGE CLOSELY     │   KEEP SATISFIED
        │  (OEM Chief Eng,    │   (Executive sponsor,
        │   OEM Safety)       │   OEM Purchasing)
        │                     │
        ├─────────────────────┼────────────────────
        │                     │
        │  MONITOR            │   KEEP INFORMED
        │  (Tier-2 sub-sup,   │   (Internal SW team,
        │   tool vendors)     │   Test Lab, Finance)
        │                     │
        LOW POWER
        └──────────────────────────────────────────
              LOW INTEREST        HIGH INTEREST
```

---

## 2. Risk Management

### 2.1 Risk Identification Methods

```
Sources of risk in automotive projects:
  Technical:     HW design failure, SW architecture gaps, integration complexity
  Schedule:      Supplier delays, resource unavailability, milestone dependencies
  Cost:          Underestimation, OEM scope changes, rework from defects
  Regulatory:    ISO 26262 findings, OBD compliance, UNECE R155/R156 (cybersecurity/OTA)
  Supplier:      Single-source components, overseas supplier lead times
  People:        Key person dependency, skill gaps, attrition
  OEM:           Late requirement changes, delayed sign-offs, payment delays
```

### 2.2 Risk Register — Full Template

| Risk ID | Description | Category | Probability (1-5) | Impact (1-5) | Risk Score | Owner | Response Strategy | Mitigation Action | Contingency | Status |
|---------|-------------|----------|-------------------|--------------|------------|-------|------------------|-------------------|-------------|--------|
| RSK-001 | Tier-2 radar HW delivery delayed by 6 weeks | Supplier | 3 | 5 | 15 | HW Lead | Mitigate | Negotiate expedited delivery; run parallel HIL path | Compress non-critical test cycles | OPEN |
| RSK-002 | ASPICE assessment fails Level 2 | Compliance | 2 | 4 | 8 | Quality Mgr | Mitigate | 8-week prep plan, internal pre-assessment | Request reassessment slot | MITIGATED |
| RSK-003 | Key AUTOSAR engineer leaves | Resource | 2 | 5 | 10 | PM | Mitigate | Cross-train 2nd engineer; contractor framework | Hire contractor immediately | OPEN |
| RSK-004 | OEM delays SW requirement sign-off | Schedule | 3 | 4 | 12 | PM | Mitigate | Weekly requirement review meetings; escalation path | Start with provisional requirements | OPEN |
| RSK-005 | ISO 26262 ASIL-C gap found late | Safety | 2 | 5 | 10 | Safety Mgr | Avoid | Early safety audits at each ASPICE gate | Push SOP by minimum required time | OPEN |
| RSK-006 | Integration defect rate exceeds estimate | Cost | 3 | 3 | 9 | SW Lead | Mitigate | Tighter unit test criteria, early SIL target | Activate contingency budget | OPEN |
| RSK-007 | OEM adds new feature 3 months before freeze | Scope | 4 | 3 | 12 | PM | Transfer | Formal ECR/ECO change control process | Defer to SOP+6 release | OPEN |

### 2.3 Risk Scoring Matrix

```
         IMPACT
           1       2       3       4       5
P    1  │  1  │   2  │   3  │   4  │   5  │  LOW
R    2  │  2  │   4  │   6  │   8  │  10  │  LOW
O    3  │  3  │   6  │   9  │  12  │  15  │  MEDIUM
B    4  │  4  │   8  │  12  │  16  │  20  │  HIGH
A    5  │  5  │  10  │  15  │  20  │  25  │  CRITICAL
B
I   Score: 1-5=Low(Green), 6-12=Medium(Amber), 13-25=High(Red)
L
I
T
Y
```

### 2.4 Risk Response Strategies

| Strategy | Definition | Automotive Example |
|----------|-----------|-------------------|
| **Avoid** | Eliminate the threat by removing the cause | Drop a feature that has unacceptable ASIL cost |
| **Mitigate** | Reduce probability or impact | Start supplier qualification earlier, add test buffer |
| **Transfer** | Shift risk to another party | Contractual penalty clause for supplier delay |
| **Accept (Active)** | Contingency plan prepared | Budget reserve for tool procurement delay |
| **Accept (Passive)** | No action, monitor | Minor cosmetic DTC logged post-SOP — monitor in field |

### 2.5 RAID Log

```
RAID = Risks, Assumptions, Issues, Dependencies

RISKS:   Potential future problems (managed as above)

ASSUMPTIONS:
  - OEM will sign off System Requirements by Week 8 (if not → risk RSK-004 triggers)
  - HW samples will be available by milestone HWS-001
  - ISO 26262 auditor available in Q3 window
  - Team headcount stays at 12 FTE for full project duration

ISSUES (already occurred — not future risks):
  - Issue 01: AUTOSAR BSW integration error discovered Week 14. Owner: SW Lead. Due: Week 16. Status: IN PROGRESS
  - Issue 02: OEM review meeting missed Week 10. Owner: PM. Due: Reschedule + extra review. Status: CLOSED
  - Issue 03: Supplier PPAP package incomplete. Owner: Quality Mgr. Due: Week 22. Status: OPEN

DEPENDENCIES:
  - SW coding cannot start until HW prototype available (Task: SW-003 depends on HW-012)
  - Safety Case cannot be completed until all ASIL verification tests passed
  - EOL station programming cannot start until SW is at SIL (Software Inspection Lock)
  - OEM homologation submission depends on vehicle test completion
```

---

## 3. Change Management

### 3.1 Change Control Process

```
Trigger: OEM request, defect-driven change, regulatory change, technology change
    ↓
Step 1: ECR (Engineering Change Request) raised — within 24h of identification
    ↓
Step 2: Impact Analysis — Scope, Schedule, Cost, Safety, Quality impacts assessed
    ↓
Step 3: Change Control Board (CCB) review — PM chairs
    ↓
Step 4: CCB Decision:
    ├─ APPROVE → ECO issued, change implemented, baseline updated
    ├─ REJECT  → ECR closed, rationale documented
    └─ DEFER   → Scheduled for future release, ECR held open
    ↓
Step 5: Implementation — tasks created, tracked in project plan
    ↓
Step 6: Verification — re-test / re-review of changed items
    ↓
Step 7: Baseline update — version control, RTM updated
```

### 3.2 Change Impact Assessment Template

```
Change Request: CR-042 — Add Driver Attention Warning feature

Impact Area     | Description                           | Effort (days) | Cost (€)
----------------|---------------------------------------|---------------|----------
SW Development  | New CAN signal handling, HMI logic    | 15 days       | 18,000
Testing         | New test cases + regression           | 10 days       | 10,000
Documentation   | SW req, arch, test spec update        | 5 days        | 5,000
Safety          | Safety analysis update (ASIL review)  | 3 days        | 4,000
HMI Assets      | New cluster display graphics          | 5 days (OEM)  | OEM scope
OEM Review      | Requirements approval cycle           | 15 days (OEM) | OEM scope
─────────────────────────────────────────────────────────────────────────────────
TOTAL TIER-1    | 38 working days = ~8 calendar weeks   |               | €37,000
Schedule impact | SW freeze pushed by 3 weeks           |               |
```

---

## 4. Escalation Management

### 4.1 Escalation Matrix

```
Issue Level     │ Severity           │ Escalate To           │ Response Time
────────────────┼────────────────────┼───────────────────────┼──────────────
Level 1 (Low)   │ Manageable within  │ Handled by PM         │ Within sprint
                │ project team       │                       │
Level 2 (Medium)│ Cross-team impact  │ Internal Programme    │ 48 hours
                │ or cost risk       │ Director              │
Level 3 (High)  │ SOP risk, budget   │ Internal VP Eng +     │ 24 hours
                │ overrun >10%       │ OEM Programme Mgr     │
Level 4 (Critical)│ SOP delay,       │ CEO/Exec + OEM VP     │ Immediate
                │ safety finding,    │ Engineering           │ (same day)
                │ legal exposure     │                       │
```

### 4.2 Escalation Email Template

```
Subject: [ESCALATION – Level 3] [Project Name] — [Issue Summary] — Action Required

To: [Steering Committee]
CC: [Relevant Tech Leads]

SITUATION:
  [1-2 sentences: what happened, when discovered]

IMPACT:
  Schedule: [X weeks at risk / SOP date affected]
  Cost:     [€X at risk]
  Quality:  [What is affected]

ROOT CAUSE:
  [Confirmed or preliminary root cause]

OPTIONS CONSIDERED:
  Option A: [Description] → Benefit: [x] | Risk: [y] | Cost: [€]
  Option B: [Description] → Benefit: [x] | Risk: [y] | Cost: [€]

RECOMMENDED ACTION:
  [Clear recommendation with rationale]

DECISION NEEDED BY:
  [Date — to maintain schedule options]

PM: [Name]  |  Tel: [Number]  |  Available for call: [Times]
```

---

*File: 04_stakeholder_and_risk_management.md | Automotive PM Interview Prep | April 2026*
