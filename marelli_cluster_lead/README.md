# Marelli Cluster Lead — Job Preparation Pack
### Role: Cluster Lead | LTTS Bangalore → Marelli | L&T Technology Services

---

## Job Description → Learning Map

| JD Requirement | Coverage File |
|---|---|
| Lead end-to-end IC validation activities | 01, 04, STAR 1 |
| CANoe + CAPL scripting for cluster validation | 02, STAR 2 |
| Analyse CAN logs, root-cause investigation | 03, STAR 3 |
| Manage defects — Jira / HP ALM | 03, STAR 1 |
| Allocate tasks, review team outputs, monitor progress | 04, STAR 4 |
| Coordinate with OEM and cross-functional stakeholders | 04, STAR 5 |
| Ensure adherence to OEM and regulatory standards | 01, STAR 5 |
| Mentor and support junior team members | 04, STAR 4 |
| Python scripting (good to have) | 05, STAR 2 |
| 5+ years in automotive / cluster domain | All files provide depth |

---

## Folder Structure

```
marelli_cluster_lead/
├── 01_instrument_cluster_fundamentals.md   ← IC types, CAN messages, telltales, gauges, NVM
├── 02_canoe_capl_mastery.md                ← CANoe workspace, CAPL patterns, test module, panels
├── 03_can_log_analysis_defect_management.md← Log analysis, 5-Why, Python parser, Jira guide
├── 04_team_lead_planning.md                ← Skill matrix, sprint plan, mentoring, escalation
├── 05_python_automation.md                 ← python-can, log parser, Jira API, DBC validator
├── 06_star_interview_scenarios.md          ← 5 STAR stories + Q&A table
└── README.md                               ← This file
```

---

## 6-Week Study Path

| Week | Focus | Files |
|---|---|---|
| 1 | IC domain fundamentals, CAN message map, telltales, gauges, NVM, power modes | 01 |
| 2 | CANoe layout, CAPL event handlers, 5 CAPL test patterns, test module | 02 |
| 3 | CAN log reading in CANoe, timing analysis, 5-Why RCA, defect writing | 03 |
| 4 | Team lead skills: skill matrix, sprint planning, stakeholder communication, escalation | 04 |
| 5 | Python automation: python-can, log parser, Jira API, DBC validation | 05 |
| 6 | STAR story practice (out loud), Q&A table drilling, mock interview | 06 |

---

## Quick Reference — Key CAN Messages

| ID | Message | Key Signal |
|---|---|---|
| 0x3B3 | VehicleSpeed | Speed_kmh (factor 0.01) |
| 0x316 | EngineStatus | RPM (factor 0.25), GearPos |
| 0x34A | FuelLevel | FuelLevel_pct (0–100%) |
| 0x3A5 | ABS_Status | ABS_Fault, ESP_Active |
| 0x3A6 | SRS_Status | Airbag_Deployed |
| 0x3C0 | TPMS_Status | FL/FR/RL/RR pressures |
| 0x726 | UDS Request | diagRequest IC 0x22 DID |

---

## Quick Reference — Telltale Priorities (ISO 2575)

| Level | Colour | Meaning | Example |
|---|---|---|---|
| P1 | Red | Safety critical — immediate action required | Oil pressure, SRS, EBD |
| P2 | Amber | Warning — service required soon | Check engine, ABS, TPMS |
| P3 | Green | Information — system active | Turn indicator, high beam |
| P4 | None | Courtesy info | Door ajar (OEM-specific) |

---

## Quick Reference — Key Standards

| Standard | Topic |
|---|---|
| ISO 2575 | Telltale symbols and priorities |
| ISO 4513 | Speedometer measurement method |
| UN ECE Reg 39 | Speedometer tolerance (≤10% + 4 km/h over-read) |
| ISO 16844 | Odometer — prohibits rollback |

---

## Quick Reference — Top 5 CAPL Patterns

1. **State machine test** — multi-step startup sequence using `testStep` counter in `on timer`
2. **Signal sweep loop** — `while` loop with `$Msg::Signal = sweep[i]` + `TestWaitForTimeout(200)`
3. **Telltale matrix** — `on testcase` with helper functions per fault type
4. **CAN timeout test** — stop TX timer to simulate message loss, verify cluster fallback
5. **UDS read via CAPL** — `diagRequest IC 0x22 DID`, `on diagResponse` compare value

---

*marelli_cluster_lead/README.md — Last updated for LTTS Bangalore Cluster Lead role*
