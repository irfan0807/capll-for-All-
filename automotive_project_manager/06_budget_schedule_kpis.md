# Budget, Schedule & KPIs — Automotive Project Manager
## April 2026

---

## 1. Earned Value Management (EVM) — Full Reference

### 1.1 Core EVM Variables

| Variable | Full Name | Definition |
|----------|-----------|-----------|
| **PV** | Planned Value | Budgeted cost of work *scheduled* to date |
| **EV** | Earned Value | Budgeted cost of work *actually completed* to date |
| **AC** | Actual Cost | Actual cost *spent* to date |
| **BAC** | Budget at Completion | Total approved project budget |
| **EAC** | Estimate at Completion | Forecast of total cost at completion |
| **ETC** | Estimate to Complete | Forecast of remaining cost to finish |
| **VAC** | Variance at Completion | BAC − EAC (positive = under budget forecast) |

### 1.2 EVM Formulas

```
Schedule Variance:     SV  = EV − PV     (negative = behind schedule)
Cost Variance:         CV  = EV − AC     (negative = over budget)

Schedule Performance:  SPI = EV / PV     (<1 = behind, >1 = ahead)
Cost Performance:      CPI = EV / AC     (<1 = over budget, >1 = under budget)

Estimate at Compl:     EAC = BAC / CPI   (most common formula)
                   OR: EAC = AC + (BAC − EV) / CPI
                   OR: EAC = AC + ETC    (bottom-up re-estimate)

Estimate to Complete:  ETC = EAC − AC
Variance at Compl:     VAC = BAC − EAC

To-Complete CPI:       TCPI = (BAC − EV) / (BAC − AC)   (CPI needed to finish on budget)
```

### 1.3 EVM Interpretation — Automotive Examples

```
Project: ADAS Radar Integration  |  BAC = €2,000,000  |  Week 26 of 52

Status at mid-point:
  PV  = €1,000,000   (half the budget was planned by now)
  EV  = €850,000     (only €850K worth of work actually completed)
  AC  = €950,000     (€950K actually spent)

Calculations:
  SV  = EV − PV = 850K − 1000K = −€150,000  → €150K behind schedule
  CV  = EV − AC = 850K − 950K  = −€100,000  → €100K over budget
  SPI = EV / PV = 850K / 1000K = 0.85       → 85% schedule efficiency
  CPI = EV / AC = 850K / 950K  = 0.895      → only €0.89 delivered per €1 spent
  EAC = BAC / CPI = 2,000K / 0.895 = €2,235,521 → €235K overrun forecast

Interpretation:
  → Project is behind schedule AND over budget
  → Need corrective action or schedule/budget revision
  → Present to steering committee with recovery plan
```

### 1.4 EVM Dashboard — What to Present to Steering Committee

```
┌─────────────────────────────────────────────────────────────┐
│             PROJECT STATUS — Week 26                        │
├────────────┬────────────┬───────────┬────────────────────────┤
│ Metric     │ Target     │ Actual    │ Status                 │
├────────────┼────────────┼───────────┼────────────────────────┤
│ SPI        │ ≥ 0.95     │ 0.85      │ 🔴 Behind schedule     │
│ CPI        │ ≥ 0.95     │ 0.90      │ 🔴 Over budget         │
│ SV         │ 0          │ −€150K    │ 🔴 3 weeks behind      │
│ CV         │ 0          │ −€100K    │ 🔴 5% over budget      │
│ EAC        │ €2,000K    │ €2,235K   │ 🔴 €235K overrun       │
│ Defects    │ <20 open   │ 14 open   │ 🟡 Acceptable          │
│ Test Cov   │ ≥85%       │ 78%       │ 🔴 Below target        │
│ SOP Risk   │ GREEN      │ AMBER     │ 🟡 2-week risk         │
└────────────┴────────────┴───────────┴────────────────────────┘
```

---

## 2. Schedule Management

### 2.1 Gantt Chart — Key Automotive Milestones

```
ID  | Task                           | Q1 Jan | Q1 Feb | Q1 Mar | Q2 Apr | Q2 May | Q3 Jun | Q3 Jul | Q3 Aug | Q4 Sep | Q4 Oct
----|--------------------------------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------
1   | Project Kick-Off               | ●      |        |        |        |        |        |        |        |        |
2   | System Requirements Review     |        | ●      |        |        |        |        |        |        |        |
3   | SW Architecture Review         |        |        | ●      |        |        |        |        |        |        |
4   | HW Freeze                      |        |        |        | ●      |        |        |        |        |        |
5   | HARA & Safety Concept          | ████████████████|        |        |        |        |        |        |
6   | SW Development Sprints         |        |        | ██████████████████████████████|        |        |
7   | HIL Setup & Config             |        |        |        | ████████████|        |        |        |
8   | SW Integration Test            |        |        |        |        |        | ██████████████|        |
9   | Vehicle Test                   |        |        |        |        |        |        | ████████████|
10  | ASPICE Assessment              |        |        |        |        | ●      |        |        |        |        |
11  | Safety Audit                   |        |        |        |        |        |        | ●      |        |        |
12  | SW Alpha                       |        |        |        |        | ●      |        |        |        |        |
13  | SW Beta                        |        |        |        |        |        |        | ●      |        |        |
14  | SIL (SW Inspection Lock)       |        |        |        |        |        |        |        | ●      |        |
15  | PPAP Submission                |        |        |        |        |        |        |        |        | ●      |
16  | SOP                            |        |        |        |        |        |        |        |        |        | ●
```

### 2.2 Critical Path Analysis

```
Critical Path = longest sequence of dependent tasks → determines project end date

Example critical path:
  SRR (2 weeks) → Architecture (4 weeks) → HW Freeze dependency (6 weeks HW lead)
  → SW coding (12 weeks) → Integration test (6 weeks) → Vehicle test (4 weeks)
  → Safety audit (2 weeks) → SIL → PPAP → SOP

Total: 38 weeks (on critical path — any slip here = SOP slip)

Non-critical path example:
  Supplier PPAP (runs parallel to SW development) → 6-week float

PM Action: Focus monitoring effort on critical path tasks.
           Non-critical path has float — less urgent escalation threshold.
```

### 2.3 Schedule Compression Techniques

| Technique | Description | Risk | Automotive Use |
|-----------|-------------|------|---------------|
| **Crashing** | Add resources to shorten duration | Higher cost, possible coordination overhead | Hire contractors for SW testing sprint |
| **Fast Tracking** | Overlap normally sequential tasks | Increased rework risk | Start integration test before coding 100% complete |
| **Scope Reduction** | Remove non-critical features | OEM negotiation required | Defer non-safety features to SOP+6 |
| **Overtime** | Extend team working hours | Burnout, quality risk | Short-term only — max 2 weeks before morale impact |
| **Process Streamlining** | Reduce review cycles for low-risk items | Documentation gap risk | Combine unit + integration review milestone |

---

## 3. Budget Management

### 3.1 Project Budget Structure

```
Total Project Budget: €3,200,000

Category                    Budget      % of Total
─────────────────────────   ─────────   ──────────
Internal Labour             €1,800,000     56%
  SW Engineering (8 FTE)    €960,000
  HW Engineering (2 FTE)    €200,000
  Test Engineering (3 FTE)  €360,000
  PM / Quality (2 FTE)      €280,000

Supplier / Procurement      €900,000      28%
  Tier-2 Radar Sensor HW    €400,000
  Tool Licences (Vector, EB)€150,000
  HIL Hardware              €200,000
  External Contractor (1x)  €150,000

Safety & Compliance         €200,000       6%
  ISO 26262 Safety Auditor  €80,000
  ASPICE Assessment         €60,000
  Homologation Testing      €60,000

Travel & Programme Costs    €100,000       3%

Contingency Reserve (10%)   €200,000       6%
Management Reserve (1%)     €0             1% (held by sponsor)
```

### 3.2 Budget Tracking Table (Monthly)

```
Month    | Planned (€) | Actual (€) | Variance (€) | CPI  | Status
─────────|─────────────|────────────|──────────────|─────-|────────
Jan      | 180,000     | 175,000    | +5,000       | 1.03 | GREEN
Feb      | 180,000     | 185,000    | -5,000       | 0.97 | GREEN
Mar      | 200,000     | 210,000    | -10,000      | 0.95 | GREEN
Apr      | 220,000     | 245,000    | -25,000      | 0.90 | AMBER
May      | 250,000     | 290,000    | -40,000      | 0.86 | RED ⚠
Cum (M5) | 1,030,000   | 1,105,000  | -75,000      | 0.93 | AMBER

Action: M5 CPI 0.86 triggers corrective action meeting.
```

---

## 4. Key Performance Indicators (KPIs) for Automotive PM

### 4.1 Schedule KPIs

| KPI | Target | Formula / Source |
|-----|--------|-----------------|
| SPI (Schedule Performance Index) | ≥ 0.95 | EV / PV |
| Milestone On-Time Rate | 100% | Milestones delivered on planned date / total |
| Defect Closure Rate | ≥ 90% per sprint | Closed defects / total opened per sprint |
| Requirement Stability | <5% change/month | New/changed requirements / total requirements |
| Sprint Velocity Trend | Stable or improving | Story points per sprint (3-sprint rolling avg) |

### 4.2 Quality KPIs

| KPI | Target | Definition |
|-----|--------|-----------|
| Requirements Coverage | 100% | % of requirements with at least one test case |
| Test Execution Rate | ≥ 95% | Tests executed / total planned tests |
| Test Pass Rate | ≥ 90% (per sprint) | Tests passed / tests executed |
| Code Review Coverage | 100% | Lines of code peer-reviewed / total changed |
| Static Analysis Violations | 0 MISRA-C critical | MISRA mandatory rule violations |
| Unit Test Coverage | ≥ 85% branch | Branches covered / total branches |
| Open ASIL-Critical Defects | 0 at SOP | ASIL critical defects open at SOP gate |

### 4.3 Cost KPIs

| KPI | Target | Formula |
|-----|--------|---------|
| CPI (Cost Performance Index) | ≥ 0.95 | EV / AC |
| Budget Variance | ≤ ±5% | (PV − AC) / PV × 100 |
| Change Order Rate | <10% of budget | Total approved change orders / BAC |
| Contingency Consumption | <60% at mid-point | Contingency used / total contingency |

### 4.4 Supplier KPIs

| KPI | Target | Measurement |
|-----|--------|------------|
| Milestone Delivery On-Time | ≥ 90% | Supplier milestones met / total due |
| Defect Escape Rate (from supplier) | <5% | Defects found in integration caused by supplier / total integration defects |
| PPAP First-Time Pass Rate | 100% | PPAP submissions passed without resubmission |
| Response to NCR (Non-Conformance) | ≤ 5 working days | Time from NCR raised to supplier response |

---

## 5. Programme Reporting — Status Report Template

```
PROJECT STATUS REPORT — Week 26 / 52
Project: ADAS Radar Integration — Programme OMEGA
Date: 18 April 2026
PM: [Name]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OVERALL STATUS:    🟡 AMBER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCHEDULE:  🔴 RED  |  2 weeks at risk — supplier HW delivery delayed
COST:      🟡 AMBER | CPI 0.93, within contingency, monitoring required
QUALITY:   🟢 GREEN | Test pass rate 91%, 0 ASIL-critical open defects
RISK:      🟡 AMBER | RSK-001 (supplier delay) ACTIVE, mitigation in progress

─────────────────────────────
HIGHLIGHTS THIS WEEK:
─────────────────────────────
  ✔ SW Sprint 12 completed — FCW detection algorithm delivered and tested
  ✔ ASPICE pre-assessment completed — 4 gaps identified, all closeable by W30
  ✔ Contractor AUTOSAR BSW resource onboarded — productive from Day 3

─────────────────────────────
ISSUES & RISKS:
─────────────────────────────
  ⚠ RSK-001: Tier-2 radar samples delayed to W28 (was W26) — 2-week slip
    Mitigation: Parallel HIL path active — 60% of integration tests running on virtual model
    Impact: SW Beta date pushed from W34 to W36. SOP buffer reduced from 4w to 2w.

  ⚠ ISSUE-07: OEM requirement document v2.3 not received — was due W25
    Owner: PM | Chasing OEM PM | Escalation if not received by W27

─────────────────────────────
UPCOMING MILESTONES:
─────────────────────────────
  W28: Radar HW samples received (was W26 — revised)
  W30: ASPICE gap closure target
  W32: HIL integration test phase start
  W40: SW Beta release
  W48: Vehicle test completion
  W52: SOP

─────────────────────────────
DECISIONS NEEDED:
─────────────────────────────
  1. OEM approval of revised SW Beta date (W36 vs W34) — needed by W27
  2. Approval of €50K contractor extension (current contract ends W30) — needed by W28
```

---

## 6. Lessons Learned (Project Closure)

```
Template for each lesson:

Category:        [Schedule / Cost / Risk / Technical / Process / People]
Event:           What happened?
Root Cause:      Why did it happen?
Impact:          What was the effect on project?
Action Taken:    How was it resolved?
Future Action:   What should be done differently on the next project?
Owner:           Who should implement the future action?

Examples:
─────────────────────────────────────────────────────────────────────────
Category:    Schedule
Event:       Tier-2 supplier hardware delayed 6 weeks
Root Cause:  Single-source HW component; no contractual hardware delivery penalty
Impact:      SOP buffer reduced; parallel HIL track required (€30K unplanned)
Action:      Activated parallel HIL path, recovered 4 weeks
Future:      All Tier-2 hardware contracts must include a penalty clause for delay >2 weeks
             AND all projects must maintain 2-source option for critical HW through CDR
Owner:       Procurement Manager

─────────────────────────────────────────────────────────────────────────
Category:    Quality
Event:       Integration defect rate 40% higher than estimate
Root Cause:  Interface between BCM and infotainment HU not tested at component level
Impact:      Integration test phase extended 3 weeks, €80K cost overrun
Action:      Interface-level tests added to SW component acceptance criteria
Future:      All inter-ECU interfaces must have documented interface test cases
             in SW integration test spec before SW coding phase starts
Owner:       Test Lead
```

---

*File: 06_budget_schedule_kpis.md | Automotive PM Interview Prep | April 2026*
