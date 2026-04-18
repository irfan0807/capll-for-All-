# PM Fundamentals & Frameworks — Automotive Project Manager
## April 2026

---

## 1. Project Management Core Concepts

### 1.1 What is a Project?

```
A temporary endeavour with:
  ✔ Defined START and END date
  ✔ Unique deliverable (product, service, result)
  ✔ Progressive elaboration (details refined over time)
  ✔ Resource constraints (people, budget, time)

In automotive: delivering a new ECU SW release, validating ADAS feature,
launching a vehicle variant on time for SOP (Start of Production).
```

### 1.2 Triple Constraint (Iron Triangle)

```
              SCOPE
              /\
             /  \
            /    \
           /      \
    TIME ──────────── COST

Change one → impacts at least one other.

Automotive reality: SOP date is FIXED (launch event, marketing, homologation).
  → Scope and cost must flex if timeline is at risk.
```

### 1.3 Project vs Programme vs Portfolio

| Level | Definition | Automotive Example |
|-------|-----------|-------------------|
| **Portfolio** | Collection of programmes/projects aligned to strategy | All electrification ECU projects for 2026–2030 |
| **Programme** | Group of related projects managed together | Full ADAS Level 3 feature development (sensors + ECU + HMI + validation) |
| **Project** | Single temporary endeavour | Deliver radar sensor integration SW v3.2 by SOP+6 months |

---

## 2. PMBOK 7 — 12 Principles (2021)

| # | Principle | Automotive Application |
|---|-----------|----------------------|
| 1 | Stewardship | Responsible use of budget, time, supplier trust |
| 2 | Team | Cross-functional (HW, SW, Testing, Safety, Supply Chain) |
| 3 | Stakeholders | OEM, Tier-1, Tier-2, Homologation, Legal |
| 4 | Value | Deliver features that meet vehicle program needs — on time for SOP |
| 5 | Systems Thinking | ECU change affects CAN bus, HMI, ADAS — see the whole system |
| 6 | Leadership | Lead distributed teams across Germany, India, China, USA |
| 7 | Tailoring | Adapt PMBOK to ASPICE and V-Model requirements |
| 8 | Quality | IATF 16949, ISO 26262 ASIL classifications |
| 9 | Complexity | Safety-critical SW, real-time OS, hardware dependencies |
| 10 | Risk | Reliability risks → recalls → liability → brand damage |
| 11 | Adaptability | Agile sprints within waterfall V-Model gates |
| 12 | Change | Requirement changes from OEM → manage impact on schedule/cost |

---

## 3. PMBOK 5 Process Groups (Still Asked in Interviews)

```
INITIATING → PLANNING → EXECUTING → MONITORING & CONTROLLING → CLOSING

Initiating:
  - Project Charter
  - Stakeholder identification
  - Business case (ROI, SOP alignment)

Planning:
  - WBS (Work Breakdown Structure)
  - Schedule (Gantt, MS Project, JIRA)
  - Budget baseline
  - Risk Register
  - Communication Plan
  - Resource Plan
  - RACI matrix

Executing:
  - Manage team (local + distributed)
  - Supplier management
  - Quality assurance (ASPICE assessment, audits)
  - Issue resolution

Monitoring & Controlling:
  - Track milestones vs plan
  - Earned Value Management (EVM)
  - Change Control (ECR/ECO process)
  - Risk monitoring
  - Reporting to steering committee

Closing:
  - Lessons learned
  - SOP handover
  - Post-launch support transition
  - Archive
```

---

## 4. PMBOK 10 Knowledge Areas

| Knowledge Area | Key Automotive Tools/Outputs |
|---------------|------------------------------|
| Integration | Project Charter, Change Control, Lessons Learned |
| Scope | WBS, Requirements Traceability Matrix, scope creep control |
| Schedule | Gantt, CPM (Critical Path Method), milestones to SOP |
| Cost | Budget baseline, EVM, EAC (Estimate at Completion) |
| Quality | IATF 16949, ISO 26262, test coverage, ASPICE |
| Resource | RACI, staffing plan, supplier SOW |
| Communications | Status reports, steering deck, escalation path |
| Risk | RAID log, risk register, FMEA linkage |
| Procurement | Supplier contracts, SOW, SLA, change orders |
| Stakeholder | Stakeholder register, engagement matrix |

---

## 5. V-Model (Automotive Development Standard)

```
                   System Requirements
                  /                    \
         SW Requirements              System Integration Test
        /                \           /                       \
  SW Architecture      SW Integration Test
      /          \     /               \
SW Detailed Design  SW Unit Test
        \         /
        Coding
```

**Key PM responsibilities at each V-Model gate:**
- **SYS.1** Requirements: Has OEM signed off on system requirements?
- **SWE.1** SW Requirements: Are all SW requirements traced to system requirements?
- **SWE.3** SW Unit Design: Are unit test specifications complete?
- **SWE.4–6** Integration/Test: Test completion criteria met before gate?
- **Gate Reviews**: Formal ASPICE assessments at each phase boundary

---

## 6. Prince2 — Key Concepts (Some Automotive OEMs Use It)

```
7 Principles:
  1. Continued Business Justification
  2. Learn from Experience
  3. Defined Roles and Responsibilities
  4. Manage by Stages
  5. Manage by Exception
  6. Focus on Products
  7. Tailor to Suit the Project Environment

7 Themes: Business Case, Organisation, Quality, Plans, Risk, Change, Progress
7 Processes: SU → IP → CS → MP → SB → DP → CP
             (Starting Up → Initiating → Controlling → Managing Product Delivery
              → Managing Stage Boundaries → Directing → Closing)
```

---

## 7. Waterfall vs Agile vs Hybrid (Automotive Reality)

| Model | Description | When Used in Automotive |
|-------|-------------|------------------------|
| **Waterfall / V-Model** | Sequential phases, gates, formal reviews | Safety-critical SW (ASIL-B/D), hardware development, ISO 26262 compliance |
| **Agile (Scrum)** | Iterative sprints, adaptive planning | Infotainment features, HMI development, non-safety SW |
| **SAFe (Scaled Agile)** | Agile at enterprise scale, PI Planning | Large OEM/Tier-1 programs with 50+ engineers |
| **Hybrid** | Waterfall gates with Agile sprints inside phases | Most modern automotive projects: V-Model gates + 2-week sprints |

---

## 8. Key PM Documents & Templates

### Project Charter
```
Project Name:      ADAS Radar Integration — Vehicle Program X5
Project Sponsor:   VP Engineering
PM:                [Your Name]
Start Date:        Jan 2025
SOP Date:          Oct 2026
Budget:            €3.2M
Scope:             Integrate 77GHz front radar, validate FCW/AEB features,
                   achieve ISO 26262 ASIL-B certification
Out of Scope:      Hardware design, radar algorithm development
Key Milestones:    HW freeze Feb 2025, SW Alpha Apr 2025, SIL Aug 2025, SOP Oct 2026
Risks:             Radar supplier delay, ASIL certification timeline
Approvals:         Sponsor, OEM, Safety Officer
```

### RACI Matrix
```
Activity               | PM  | SW Lead | HW Lead | Safety | OEM | Supplier
-----------------------|-----|---------|---------|--------|-----|----------
Requirements review    |  A  |    R    |    R    |   C    |  I  |    I
SW architecture review |  I  |    A    |    C    |   R    |  I  |    C
ASPICE assessment      |  A  |    R    |    R    |   R    |  I  |    I
Budget approval        |  R  |    I    |    I    |   I    |  A  |    I
SOP sign-off           |  R  |    I    |    I    |   C    |  A  |    I

R=Responsible, A=Accountable, C=Consulted, I=Informed
```

### Work Breakdown Structure (WBS) — Automotive Example
```
1.0 ADAS Radar Integration Project
  1.1 Project Management
      1.1.1 Project Planning
      1.1.2 Status Reporting
      1.1.3 Stakeholder Management
      1.1.4 Risk Management
  1.2 Requirements Management
      1.2.1 System Requirements Review
      1.2.2 SW Requirements Specification
      1.2.3 Requirements Traceability Matrix
  1.3 SW Development
      1.3.1 Architecture Design
      1.3.2 Component Design
      1.3.3 Coding
      1.3.4 Unit Test
      1.3.5 Code Review / Static Analysis
  1.4 Integration & Validation
      1.4.1 HIL Test Setup
      1.4.2 SW Integration Test
      1.4.3 System Integration Test
      1.4.4 Vehicle Test (proving ground)
  1.5 Functional Safety
      1.5.1 HARA (Hazard Analysis & Risk Assessment)
      1.5.2 Safety Plan
      1.5.3 Safety Case
      1.5.4 ASIL Classification
      1.5.5 Safety Audit
  1.6 Release & SOP
      1.6.1 Release Notes
      1.6.2 PPAP / SOP Package
      1.6.3 Handover to Production Support
```

---

## 9. Critical Path Method (CPM)

```
Identify all project activities and dependencies.
Calculate:
  ES = Earliest Start
  EF = Earliest Finish
  LS = Latest Start
  LF = Latest Finish
  Float = LS - ES (or LF - EF)

Critical path = chain of activities where Float = 0
  → Any delay on critical path = delay to SOP

Automotive critical path typically runs through:
  Requirements freeze → Architecture review → Safety HARA → HIL test → Vehicle test → SOP
```

---

## 10. Change Control Process (ECR/ECO)

```
ECR = Engineering Change Request
ECO = Engineering Change Order

Process:
  1. Change identified (OEM request, defect fix, regulation change)
  2. ECR raised → impact analysis (scope, cost, schedule, safety)
  3. Change Control Board (CCB) review and approval
  4. ECO issued → approved change implemented
  5. Requirements, design, test artifacts updated (traceability maintained)
  6. Re-verification of affected components
  7. Safety assessment if ASIL-related change

Key PM role: Chair CCB, enforce process, communicate impact to OEM, update baseline
```

---

*File: 01_pm_fundamentals_and_frameworks.md | Automotive PM Interview Prep | April 2026*
