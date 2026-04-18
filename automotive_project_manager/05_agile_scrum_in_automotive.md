# Agile & SCRUM in Automotive — Project Manager Guide
## April 2026

---

## 1. Why Agile in Automotive?

```
Traditional automotive used pure Waterfall (V-Model):
  → Good for hardware, safety-critical SW (ISO 26262 demands documentation)
  → Too slow for infotainment, HMI, connected features (OTA, apps, cloud)

Modern reality: HYBRID
  ┌──────────────────────────────────────────────────────────────┐
  │               Vehicle Programme Level                        │
  │   Waterfall gates: CDS → SRR → CDR → HW Freeze → SOP        │
  │                                                              │
  │   Inside each phase:                                         │
  │   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │
  │   │Sprint 1│ │Sprint 2│ │Sprint 3│ │Sprint 4│ │Sprint 5│   │
  │   │2 weeks │ │2 weeks │ │2 weeks │ │2 weeks │ │2 weeks │   │
  │   └────────┘ └────────┘ └────────┘ └────────┘ └────────┘   │
  └──────────────────────────────────────────────────────────────┘
```

---

## 2. Scrum Framework — Complete Overview

### 2.1 Scrum Roles

| Role | Responsibility | Automotive Context |
|------|---------------|-------------------|
| **Product Owner (PO)** | Owns and prioritises the Product Backlog | Often the technical lead or the OEM's requirement owner |
| **Scrum Master (SM)** | Facilitates Scrum process, removes impediments | Internal process champion — NOT the PM |
| **Development Team** | Self-organising, delivers sprint increment | SW engineers, testers, safety engineers |
| **Project Manager** | NOT a formal Scrum role — but manages programme-level tracking, stakeholders, budget | You bridge Scrum team and programme governance |

### 2.2 Scrum Artefacts

```
Product Backlog:
  - Master list of ALL work items (user stories, features, bugs, tech debt)
  - Owned and prioritised by Product Owner
  - Items written as User Stories: "As a [user], I want [feature], so that [benefit]"
  - Each story has Acceptance Criteria

Sprint Backlog:
  - Subset of Product Backlog committed to in the current sprint
  - Team-owned — team decides what fits in the sprint
  - Visible on Scrum board (JIRA, Azure DevOps)

Sprint Increment:
  - Working, potentially shippable product at end of each sprint
  - In automotive: "Integrated and tested SW increment on HIL"

Definition of Done (DoD) — Automotive:
  ☐ Code reviewed (peer review + static analysis MISRA-C/C++)
  ☐ Unit tests written and passing (≥85% branch coverage)
  ☐ Integration test executed on HIL
  ☐ No open ASIL-relevant defects
  ☐ Requirements traceability updated in RTM
  ☐ ASPICE evidence artifacts updated
```

### 2.3 Scrum Ceremonies

| Ceremony | Duration | Purpose | PM involvement |
|----------|----------|---------|---------------|
| **Sprint Planning** | 2–4 hours (for 2-week sprint) | Team selects backlog items, creates Sprint Backlog | Attend — confirm priority aligns with programme milestones |
| **Daily Standup** | 15 minutes | What did I do? What will I do? Any blockers? | Optional — attend occasionally to observe, remove blockers |
| **Sprint Review** | 1–2 hours | Demo working increment to stakeholders | ATTEND — demonstrate progress to OEM and programme mgmt |
| **Sprint Retrospective** | 1–1.5 hours | Team reflects: what went well, what to improve | Attend occasionally — respect team ownership |
| **Backlog Refinement** | 1 hour/week | Estimate, clarify, split stories for future sprints | Ensure programme priorities are reflected |

---

## 3. SAFe (Scaled Agile Framework) — Large Automotive Programmes

```
Used when multiple Scrum teams (50–500+ engineers) need to coordinate
across one large programme (e.g., full ADAS Level 3 development).

4 Core SAFe Configurations:
  Essential SAFe → Team + Programme level
  Large Solution → Multiple ARTs (Agile Release Trains)
  Portfolio SAFe → Portfolio + Programme + Team
  Full SAFe → All levels

Key SAFe Concepts for Automotive PM:
```

### 3.1 Agile Release Train (ART)

```
ART = 50–125 people organised into 5–12 Scrum teams
      working together on a shared programme increment

In automotive: One ART = ADAS feature development team
  Team 1: Radar sensor integration
  Team 2: Camera sensor integration
  Team 3: Sensor fusion algorithm
  Team 4: ADAS domain controller SW
  Team 5: HMI / cluster display
  Team 6: Safety validation
```

### 3.2 PI Planning (Programme Increment Planning)

```
Most important SAFe event — 2-day conference-style planning event
All ART teams + stakeholders + OEM in one room (or virtual)

PI = 5 sprints (10 weeks) of planned work aligned to OEM milestone

Day 1:
  AM: Programme vision, OEM priorities, architecture briefing
  PM: Team breakouts — plan sprints 1–5 of the PI, identify dependencies

Day 2:
  AM: Risk review, dependency resolution
  PM: Team confidence votes → Programme Board → PI Objectives signed

Outputs:
  - PI Objectives (5–10 measurable outcomes for the PI)
  - Team Sprint Plans for all 5 sprints
  - Programme Board (visual dependency map)
  - ROAM Risk Board: Resolved, Owned, Accepted, Mitigated
```

### 3.3 SAFe Roles Relevant to Automotive PM

| SAFe Role | Equivalent | Automotive Responsibility |
|-----------|-----------|--------------------------|
| Release Train Engineer (RTE) | Programme-level Scrum Master | Facilitates PI Planning, ART ceremonies, removes programme impediments |
| Product Management | Programme PO | Translates OEM requirements into features for the Product Backlog |
| System Architect | Chief Architect | Ensures AUTOSAR/system architecture guides team decisions |
| Business Owners | OEM / Programme Director | Attends PI Planning, approves PI Objectives, votes confidence |

---

## 4. User Story Writing — Automotive Examples

### Format
```
As a [persona / user / system]
I want [capability / feature]
So that [benefit / value delivered]

Acceptance Criteria:
  Given [context]
  When [action taken]
  Then [expected result]
```

### Automotive User Stories

```
Story: Radar Object Detection Display
─────────────────────────────────────
As the instrument cluster display system
I want to receive radar-detected object distance and relative speed via CAN signal 0x356
So that the driver sees accurate forward object distance on the ADAS status screen

Acceptance Criteria:
  Given the radar detects an object within 150m
  When the ADAS domain controller sends CAN signal 0x356 (distance, speed)
  Then the cluster displays distance to within ±0.5m accuracy and updates at 10Hz minimum
  And no display update latency exceeds 100ms

──────────────────────────────────────
Story: DTC Logging for Radar Fault
──────────────────────────────────────
As a workshop service tool user
I want to read DTC C1234 (Radar Communication Fault) via UDS Service 19 02 09
So that a radar failure can be diagnosed and the correct component replaced

Acceptance Criteria:
  Given the radar CAN signal is absent for > 500ms
  When a diagnostic tester sends 19 02 09 via UDS
  Then DTC C1234 is returned with status confirmed (0x08)
  And freeze frame captures vehicle speed, ignition time at fault occurrence

──────────────────────────────────────
Story: OTA SW Update Acceptance
──────────────────────────────────────
As a connected vehicle owner
I want to receive and install a SW update for the ADAS domain controller over-the-air
So that new ADAS features are available without visiting a dealer

Acceptance Criteria:
  Given a valid SW package is available on the OTA backend
  When the vehicle is parked, engine off, and connected to WiFi
  Then the vehicle downloads the SW package in background
  And on next ignition-ON with driver consent, installs and verifies the update
  And rolls back automatically if post-install checksum fails
```

---

## 5. Scrum Metrics for Automotive PM

### Velocity
```
Story Points completed per sprint (team capacity measure)
Automotive baseline velocity: measure over first 3 sprints, then use average for planning
Warning: story points don't map to schedule hours — use as relative measure only
```

### Burndown Chart
```
Sprint Burndown:
  Y-axis: Remaining story points
  X-axis: Sprint days (1–10 for 2-week sprint)
  Ideal line: straight diagonal from total points to zero
  Actual line: should track close to ideal
  PM flag: actual line flat for 3+ days = impediment, investigate immediately

Release Burndown:
  Y-axis: Remaining backlog items for the release
  X-axis: Sprints
  Use to forecast when all SOP-required features will be complete
```

### Cumulative Flow Diagram (CFD)
```
Shows work item flow through: Backlog → In Progress → Review → Done
Healthy: bands are roughly equal width, total rising steadily
Warning: "In Progress" band bulging = WIP limit breach, too much parallel work
Critical: "Done" band flat for 2+ sprints = no items completing = systematic blocker
```

### Lead Time and Cycle Time
```
Lead Time   = Time from item raised to item delivered (includes queue time)
Cycle Time  = Time from work started to item done (active work only)

Automotive target: Defect cycle time < 5 days for ASIL-relevant items
                   Feature lead time < 2 sprints (4 weeks)
```

---

## 6. Agile Ceremonies — PM Meeting Guide

### Sprint Review Agenda (Automotive)
```
Duration: 90 minutes

1. Sprint Goal recap (5 min) — what did we commit to?
2. Demo of working increment on HIL/test bench (40 min)
   - Each feature demonstrated by the implementing engineer
   - OEM / stakeholder Q&A after each demo
3. Metrics review (15 min) — velocity, defect trend, test coverage
4. What didn't get done — honest account, moved to next sprint or backlog (10 min)
5. Product Owner updates backlog priorities based on feedback (10 min)
6. Next sprint preview (10 min)

PM role: Facilitate, connect demo output to programme milestones, manage stakeholder expectations
```

### Retrospective Formats the PM May Suggest

```
Start/Stop/Continue:
  Start: What should we begin doing?
  Stop:  What is not working, should be stopped?
  Continue: What is working well?

4Ls:
  Liked | Learned | Lacked | Longed For

Mad/Sad/Glad:
  Post-it exercise — emotional team temperature check
  Useful after stressful sprints (e.g., post-OEM review, post-safety audit)
```

---

## 7. Agile vs ASPICE — How They Coexist

```
Common concern: "Agile doesn't produce the documentation ASPICE requires"
Reality: Agile produces the SAME evidence — just at sprint level, not phase level

ASPICE Requirement          Agile Equivalent
──────────────────          ────────────────
Requirements documented  →  User stories with Acceptance Criteria in JIRA
Architecture reviewed    →  Architecture spikes + team review in sprint
Code reviewed            →  PR (Pull Request) review in GitLab/GitHub
Unit tested              →  Automated unit tests in CI/CD pipeline (pytest, gtest)
Defects tracked          →  JIRA bug tickets with status and resolution
Configuration managed    →  Git with tags/branches per sprint baseline
Reviews documented       →  Sprint Review minutes + retrospective notes
Risk managed             →  ROAM board in SAFe or RAID log maintained by PM
```

---

*File: 05_agile_scrum_in_automotive.md | Automotive PM Interview Prep | April 2026*
