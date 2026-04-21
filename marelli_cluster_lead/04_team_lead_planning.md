# Team Leadership, Planning & Customer Communication — Cluster Lead

> **Role:** Cluster Lead — Marelli / LTTS Bangalore
> **Scope:** Task allocation, progress monitoring, team mentoring, OEM stakeholder management

---

## 1. Role of a Cluster Lead — Responsibilities Breakdown

```
Cluster Lead
├── Technical Authority
│   ├── Review test cases for correctness and coverage
│   ├── Define test strategy for each feature
│   ├── Resolve technical blockers (DBC issues, tool setup)
│   └── Own test architecture — reusable CAPL libraries, naming conventions
│
├── Team Management
│   ├── Assign tasks by skill and capacity
│   ├── Daily/weekly review of team outputs
│   ├── Identify risks early — blocked tasks, skill gaps
│   └── Mentor juniors on CAN, CAPL, cluster domain
│
├── Process & Quality
│   ├── Ensure test case review before execution
│   ├── Enforce defect reporting standards
│   ├── Maintain traceability: Requirement → Test Case → Execution → Defect
│   └── Own test closure sign-off before OEM delivery
│
└── Customer Interface
    ├── Weekly status to OEM/customer team
    ├── Defect triage calls with ECU owners
    ├── Manage customer expectations on open issues
    └── Present test results in OEM review gates
```

---

## 2. Task Allocation Framework

### 2.1 Skill Matrix — Map Engineers to Test Areas

```
SKILL MATRIX TEMPLATE (Rate: 1=Beginner, 2=Working, 3=Expert)

Engineer    | CAN/DBC | CAPL | UDS/Diag | Cluster HW | Python | Test Mgmt
------------|---------|------|----------|------------|--------|----------
Ravi K      |    3    |  3   |    2     |     3      |   2    |    2
Priya M     |    2    |  2   |    1     |     2      |   3    |    2
Suresh L    |    3    |  2   |    3     |     2      |   1    |    1
Anjali R    |    1    |  1   |    1     |     1      |   2    |    1  (fresher)
You (Lead)  |    3    |  3   |    3     |     3      |   3    |    3

ASSIGNMENT STRATEGY:
  Senior testers (Ravi, Suresh) → Safety telltales, NVM, ABS/SRS validation (ASIL B)
  Mid testers (Priya) → Gauge sweep tests, Python automation scripts
  Freshers (Anjali) → DIS/trip meter tests with senior pairing first 2 weeks
  Lead (You) → Test strategy, OEM communication, critical defect RCA, review
```

### 2.2 Sprint Planning — Weekly / Bi-Weekly

```
SPRINT PLANNING WORKSHEET — IC Validation Sprint 3 (WK17–WK18)

Team Capacity:
  - 4 engineers × 5 days × 6 effective hours = 120 person-hours
  - Lead: 2 days test execution + 3 days review/reporting

Sprint Goal:
  - Complete Telltale validation (TC_TEL_001 to TC_TEL_030)
  - Retest all P1 defects from Sprint 2
  - Start CAN Timeout tests (TC_CTO_001 to TC_CTO_010)

BACKLOG ITEM           | Owner  | Est(hrs) | Dependency
-----------------------|--------|----------|-------------------
TC_TEL_001-010 Execute | Ravi   |   12     | Bench SLA (Sprint 2)
TC_TEL_011-020 Execute | Suresh |   12     | ABS signal coverage done
TC_TEL_021-030 Execute | Priya  |    8     | None
Retest CLU-1024        | Ravi   |    3     | SW build v1.5.1 available
Retest CLU-1031        | Suresh |    3     | SW build v1.5.1 available
Python timeout script  | Priya  |    8     | None
TC_CTO_001-010 Review  | Lead   |    4     | Priya completes script
Daily defect triage    | Lead   |    5     | Daily 30min × 5 days = 2.5h each WK
Weekly OEM report      | Lead   |    4     | WK17 + WK18 = 2 reports
Total Est              |        |   59h    | Buffer: 61h remaining (45% buffer)
```

---

## 3. Test Case Review — Lead's Checklist

```
BEFORE EXECUTING ANY TEST CASE, LEAD CONFIRMS:

✓ COVERAGE
  - Does the TC trace to a requirement in the SRS? (requirement ID linked)
  - Are boundary conditions covered? (min/max/default/timeout)
  - Is negative test included? (invalid signal, wrong value)

✓ CLARITY
  - Steps are unambiguous — a different engineer can run without asking
  - Expected Result is specific and measurable (not "check fuel gauge moves")

✓ PREREQUISITE
  - Correct SW baseline stated
  - Bench configuration is defined (channel assignments, termination)
  - DBC version referenced

✓ CAPL SCRIPT
  - Script reviewed for CAPL correctness
  - Signal names match current DBC
  - Output message IDs are correct for current bus
  - No hardcoded timestamps that might fail on different builds

✓ TRACEABILITY
  - TC ID exists in test management tool (Jira/ALM)
  - TC linked to defect if retesting

REJECTION CRITERIA (send back for rework):
  ✗ No requirement trace
  ✗ Expected result says "as per SRS" without quoting the specific value
  ✗ Wrong DBC signal name used in CAPL
  ✗ Missing preconditions (e.g., doesn't state ignition must be ON)
```

---

## 4. Progress Monitoring — KPIs for Cluster Lead

### 4.1 Daily Tracking

```
DAILY STANDUP STRUCTURE (15 minutes):

Each engineer answers:
  1. "Yesterday I completed: [TC IDs or tasks]"
  2. "Today I plan: [TC IDs or tasks]"
  3. "My blocker is: [tool, bench, SW build, DBC, knowledge]"

Lead notes:
  - Update execution tracker immediately
  - If blocker: assign action with due time (not "sometime today" → "by 3pm")
  - Re-prioritise if any P1 defect needs retest by EOD
```

### 4.2 Execution Tracker (Spreadsheet / Jira Board)

```
IC_Validation_Tracker_WK17.xlsx

Column: TC_ID | Feature | Engineer | Status | Date Executed | Result | Defect_ID
---------------------------------------------------------------------------
TC_SPD_001 | Speed 60kph  | Ravi    | Done   | 2026-04-20   | Pass   | -
TC_SPD_002 | Speed 100kph | Ravi    | Done   | 2026-04-20   | Pass   | -
TC_SPD_003 | Speed 200kph | Priya   | Done   | 2026-04-21   | Fail   | CLU-1044
TC_TEL_001 | ABS Telltale | Suresh  | WIP    | 2026-04-21   | -      | -
TC_TEL_002 | SRS Telltale | Suresh  | TODO   | -            | -      | -

Metrics (auto-calculated):
  Executed: 37/320 (11.5%)
  Passed: 35 | Failed: 2 | Blocked: 0
  Execution rate: 12 TC/day → On track for WK20 completion
```

### 4.3 Key Metrics Tracked Weekly

| Metric | Target | How to Measure |
|---|---|---|
| Test Execution Rate | > 85% of planned TCs per sprint | Tracker sheet |
| First-Pass Yield | > 85% tests pass on first run | (Pass / Total Executed) × 100 |
| Defect Leakage | < 5% defects found by OEM not by team | Escaped defects / Total defects |
| P1 Defect Age | < 7 days average open time | Jira: Created → Fixed date |
| Retest Cycle Time | < 2 days from build delivery to retest | Jira timestamps |

---

## 5. Mentoring Junior Engineers — Training Plan

### 5.1 4-Week Onboarding Plan (New Cluster Engineer)

```
WEEK 1 — Domain Foundation
  Mon: Vehicle CAN architecture + DBC reading with CANalyzer
  Tue: Instrument cluster tour (physical bench walkthrough)
  Wed: Understand OEM SRS — read telltale requirements
  Thu: Observe senior engineer run 5 TCs — shadow session
  Fri: Run 3 simple TCs independently (gauge sweep) + review with lead

WEEK 2 — CAPL Fundamentals
  Mon: CAPL syntax: variables, timers, on message handlers
  Tue: Write first CAPL script: send message, observe in trace
  Wed: CAPL telltale injection script workshop
  Thu: Set up full CANoe environment with DBC + panel
  Fri: Mini-project: automate 3 telltale TCs with CAPL, demo to lead

WEEK 3 — Defect Management
  Mon: Defect lifecycle in Jira (create, update, close)
  Tue: Trace analysis technique — read through 2 real defect logs
  Wed: Root-cause 3 pre-canned lab exercises (prepared by lead)
  Thu: Write defect report for a seeded fault the lead injected
  Fri: Peer review session — each engineer reviews another's defect report

WEEK 4 — Execution Independence
  Mon–Fri: Execute 20 TCs independently from the backlog
           Lead reviews all outputs but does not assist unless blocked > 30 minutes
  Review: Lead gives structured feedback session Friday
```

---

## 6. Customer Stakeholder Management

### 6.1 Types of Stakeholders in a Cluster Project

```
OEM Customer (e.g., Renault, Honda, FCA):
  → Cares about: schedule, open P1 defects, whether product is ship-ready
  → Communication: Weekly status reports, gateway reviews
  → Tone: Professional, concise, factual

ECU Owners (ABS ECU team, BCM team, Engine ECU team):
  → Cares about: accurate defect description, reproduction steps, log files
  → Communication: Defect triage calls (bi-weekly or on-demand)
  → Tone: Technical, collaborative, not accusatory

Internal LTTS Management:
  → Cares about: Effort burn, risk flags, customer satisfaction score
  → Communication: Internal project updates, risk register
  → Tone: Metrics-driven, proactive on risks

System/Integration Lead:
  → Cares about: Interface completeness, DBC freeze dates, variant management
  → Communication: DBC review meetings, configuration change notifications
```

### 6.2 Escalation Matrix

```
LEVEL 1 — Team Level (< 2 days to resolve)
  Who: Cluster Lead ↔ ECU engineer
  How: Direct Teams/Slack message + defect comment
  When: Blocked task, environment issue, DBC query

LEVEL 2 — Project Manager (2–5 days unresolved)
  Who: LTTS Cluster Lead → LTTS PM → Customer-side PM
  How: Email + weekly status call agenda item
  When: P1 defect unresolved > 5 days, schedule risk

LEVEL 3 — Director / Customer Management (> 5 days or scope impact)
  Who: LTTS PM → LTTS Delivery Director → OEM Customer Lead
  How: Formal escalation note, risk register update
  When: Potential delivery miss, ASIL-related blocked gate
```

### 6.3 Defect Triage Call Agenda

```
OEM Defect Triage Call — Cluster IC | Duration: 45 min

1. New defects this week                          [10 min]
   - Walk through each new P1/P2: title, status, log evidence
   
2. P1 Status update                               [10 min]
   - CLU-1024: SW fix eta, build expected WK18 Mon
   - CLU-1031: Root cause confirmed, fix in progress

3. Defects pending OEM decision                   [10 min]
   - CLU-1002: "WAD or Defect?" — speedometer reads +3 km/h
                OEM to confirm if within their approved tolerance range

4. Closed defects                                  [5 min]
   - CLU-1018: Verified passed on build v1.5.0 → Closed

5. AOB / Risks                                    [10 min]
   - DBC freeze date: May 5 → request OEM confirms no more SRS changes
```

---

*File: 04_team_lead_planning.md | marelli_cluster_lead series*
