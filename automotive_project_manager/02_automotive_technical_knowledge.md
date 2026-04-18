# Automotive Technical Knowledge for Project Managers
## April 2026

> As an Automotive PM you don't need to write code — but you MUST understand the technical landscape well enough to plan, risk-assess, and communicate with engineers, OEMs, and suppliers.

---

## 1. Automotive ECU Domain Architecture

```
Vehicle Domains (Modern Architecture):
┌──────────────────────────────────────────────────────────┐
│                    Domain Controller                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │  Powertrain│  │  Chassis   │  │  ADAS / AD         │ │
│  │  ECU       │  │  ECU       │  │  Domain Controller │ │
│  └────────────┘  └────────────┘  └────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐  │
│  │         Body / Comfort Domain                      │  │
│  │  BCM │ Lighting │ HVAC │ Seat │ Window │ Door       │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │         Infotainment / HMI Domain                  │  │
│  │  Head Unit │ Cluster │ HUD │ Rear-seat display      │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │         Telematics / Gateway Domain                │  │
│  │  TCU │ V2X │ OTA │ Cloud connectivity              │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

**PM Implication:** A change in one domain often has change impact across others (e.g., ADAS feature change affects HMI cluster display, telematics data logging, safety classification). A good PM tracks cross-domain dependencies.

---

## 2. ASPICE (Automotive SPICE) — ISO/IEC 15504

### What It Is
Automotive Software Process Improvement and Capability dEtermination — the **process maturity standard** for automotive software development. Almost all OEMs (BMW, VW, Daimler, Stellantis, etc.) mandate ASPICE compliance from Tier-1 suppliers.

### Capability Levels

| Level | Name | Description |
|-------|------|-------------|
| 0 | Incomplete | Process not performed |
| 1 | Performed | Basic process outcomes achieved |
| 2 | Managed | Process planned, monitored, work products controlled |
| 3 | Established | Process uses a defined, standard process |
| 4 | Predictable | Process is quantitatively managed |
| 5 | Optimising | Process continuously improved |

**Most OEMs require Level 2 minimum; Level 3 is standard for major Tier-1s.**

### Key ASPICE Process Areas (PM Must Know)

| ID | Process | What It Means for PM |
|----|---------|----------------------|
| **MAN.3** | Project Management | YOUR process — planning, monitoring, control |
| **MAN.5** | Risk Management | Maintain RAID log, assess & mitigate risks |
| **MAN.6** | Measurement | Define and track project metrics (KPIs) |
| **SYS.1** | Requirements Elicitation | Are system requirements captured and agreed? |
| **SYS.2** | System Requirements Analysis | System req traced and consistent? |
| **SYS.3** | System Architecture Design | Architecture documented and reviewed? |
| **SWE.1** | SW Requirements Analysis | SW req derived from system req? |
| **SWE.2** | SW Architecture Design | Architecture reviewed vs safety? |
| **SWE.3** | SW Detailed Design | Detailed design reviewed? |
| **SWE.4** | SW Unit Construction | Code review, static analysis done? |
| **SWE.5** | SW Unit Verification | Unit test executed and results reviewed? |
| **SWE.6** | SW Integration Verification | Integration test complete? |
| **SUP.1** | Quality Assurance | Internal audits, non-conformance tracking |
| **SUP.8** | Configuration Management | Baseline control, version management |
| **SUP.9** | Problem Resolution | Defect tracking (JIRA, GitHub Issues) |
| **SUP.10** | Change Request Management | ECR/ECO process followed? |

**PM must ensure all ASPICE process areas are being executed and can be evidenced at an audit.**

### ASPICE Assessment Preparation Checklist
```
Before an ASPICE assessment the PM must confirm:
  ☐ Project plan exists, is current, and approved
  ☐ All requirements have unique IDs and traceability
  ☐ Review minutes exist for every formal review
  ☐ Defects are tracked in a tool (JIRA, PTC Integrity)
  ☐ Configuration baseline defined and controlled
  ☐ Risk register maintained and reviewed regularly
  ☐ Work products are version-controlled (Git, SVN, PTC)
  ☐ Competency records for team members available
  ☐ Interface agreements with OEM/suppliers documented
```

---

## 3. ISO 26262 — Functional Safety

### What It Is
International standard for **functional safety of road vehicles' E/E systems**. Defines ASIL (Automotive Safety Integrity Level) classification and requirements.

### ASIL Levels

| ASIL | Risk Level | Example |
|------|-----------|---------|
| QM | No safety requirement | Infotainment radio |
| ASIL A | Lowest | Windshield wiper fault |
| ASIL B | Low-medium | Electric steering secondary sensor |
| ASIL C | Medium-high | Airbag control |
| ASIL D | Highest | Primary brake-by-wire control |

### HARA (Hazard Analysis and Risk Assessment)

```
For each functional hazard, evaluate:
  S = Severity (0–3): How bad is the injury? S3 = life-threatening
  E = Exposure (0–4): How often is vehicle in this situation? E4 = always
  C = Controllability (0–3): Can driver control/avoid? C3 = uncontrollable

  ASIL = f(S, E, C) — determined by lookup table in ISO 26262 Part 3

Example:
  Hazard: Unintended braking at motorway speed
  S=3, E=4, C=3 → ASIL D → highest safety requirement
```

### PM Responsibilities for ISO 26262
```
  ☐ Appoint qualified Safety Manager (separate from PM — independence requirement)
  ☐ Ensure Safety Plan is created and maintained
  ☐ Budget for safety activities (HARA, FTA, FMEA, safety audits)
  ☐ Never override Safety Manager's decisions (safety vs schedule conflict)
  ☐ Confirm Safety Case is complete before SOP gate
  ☐ Ensure ASIL decomposition agreed between OEM and Tier-1 in DIA (Development Interface Agreement)
  ☐ Plan for Confirmation Measure reviews (mandatory in ISO 26262)
```

### ISO 26262 — Key Documents PM Tracks

| Document | Purpose |
|----------|---------|
| Safety Plan | How safety activities are organised and planned |
| HARA | Identifies hazards, ASILs assigned |
| Functional Safety Concept | Safety goals and measures at system level |
| Technical Safety Concept | Safety mechanisms at SW/HW level |
| Safety Analysis (FTA, FMEA) | Fault tree / failure mode analysis |
| Safety Case | Evidence package demonstrating safety requirement met |
| Confirmation Measures | Independent review, audit, assessment evidence |

---

## 4. AUTOSAR (AUTomotive Open System ARchitecture)

```
Two variants:
  Classic AUTOSAR — real-time embedded ECUs (brake, engine, airbag)
  Adaptive AUTOSAR — high-compute ECUs (ADAS, AD, OTA, Ethernet-based)

Layered architecture:
  Application Layer   → SW components (SWCs) written by engineers
  RTE (Runtime Env)   → connects SWCs to BSW
  Basic SW (BSW)      → OS, drivers, communication stacks
  Microcontroller     → hardware
```

**PM Implication:**
- AUTOSAR projects have a **Configuration Phase** before coding starts — PM must plan 4–6 weeks for tool configuration (EB Tresos, Vector DaVinci)
- AUTOSAR SW component design must be complete before any integration — waterfall dependency
- Tool licences (Vector, ETAS, EB) are a procurement and budget item

---

## 5. CAN / LIN / Ethernet — Communication Protocols

| Protocol | Speed | Used For | PM Consideration |
|----------|-------|----------|-----------------|
| CAN 2.0 | 1 Mbit/s | Powertrain, body | Legacy, most vehicles |
| CAN-FD | 5–8 Mbit/s | High-data powertrain, ADAS | Requires CAN-FD capable tools (budget) |
| LIN | 20 kbit/s | Switches, sensors, simple actuators | Low cost, no acknowledge |
| FlexRay | 10 Mbit/s | Safety-critical chassis | Deterministic timing |
| Automotive Ethernet | 100M–10Gbit/s | ADAS, camera, radar, OTA | Modern domain controllers |
| MOST | 150 Mbit/s | Legacy infotainment | Being phased out |

**PM Implication:** Network database changes (`.dbc`, `.arxml`) require change control — a single signal rename can break multiple ECUs. Always budget for network integration testing after any CAN database change.

---

## 6. Diagnostics — UDS / OBD (PM Awareness)

```
UDS (ISO 14229):
  - Every ECU must support diagnostic services for workshop, EOL, OTA
  - PM must plan for diagnostic specification review, tool setup, and EOL station validation
  - Diagnostic identifiers (DIDs, DTCs) are project-specific — must be documented

EOL (End of Line):
  - At manufacturing: every ECU is tested and configured via diagnostic protocol
  - EOL station development is a sub-project — needs PM coordination with production team
  - EOL failures on production line = line stoppage = very high cost impact

OBD (On-Board Diagnostics):
  - Legal requirement in EU, US for emissions-related systems
  - OBD compliance verification is a milestone gate before SOP
```

---

## 7. Key Automotive Development Milestones

| Milestone | Name | Description |
|-----------|------|-------------|
| **KOM** | Kick-Off Meeting | Project officially starts |
| **CDS** | Concept Decision | System concept agreed with OEM |
| **SRR** | System Requirements Review | SYS.1/SYS.2 gate |
| **PDR** | Preliminary Design Review | Architecture reviewed |
| **CDR** | Critical Design Review | Detailed design reviewed, ready to code |
| **HW Freeze** | Hardware Freeze | PCB design locked — no more HW changes |
| **SW Alpha** | SW Alpha Release | Feature code complete, internal test only |
| **SW Beta** | SW Beta Release | All features complete, OEM vehicle test |
| **SIL** | Software Inspection Lock | Final SW content locked |
| **PPAP** | Production Part Approval Process | Supplier proves production process capable |
| **SOP** | Start of Production | Vehicle enters series production |
| **SOP+3** | SOP+3 months | Post-launch support obligation |

---

## 8. IATF 16949 — Quality Management

```
Automotive-specific quality management system standard (replaces ISO/TS 16949).
Built on top of ISO 9001.

Key requirements for PM:
  - Documented process descriptions for all activities
  - Customer-specific requirements (CSR) must be identified and accepted
  - APQP (Advanced Product Quality Planning) process
  - PPAP (Production Part Approval Process)
  - MSA (Measurement System Analysis)
  - SPC (Statistical Process Control) for production

PM must ensure:
  ☐ All team members understand CSRs
  ☐ APQP phases are scheduled in project plan
  ☐ PPAP submission is on project timeline
  ☐ Supplier quality plan agreed
```

---

## 9. APQP — Advanced Product Quality Planning

```
5 Phases:
  Phase 1: Plan and Define Program
    → Voice of Customer, design goals, reliability targets, preliminary BOM
  
  Phase 2: Product Design and Development
    → DFMEA, design verification, design reviews, prototype builds
  
  Phase 3: Process Design and Development
    → Process flow diagram, PFMEA, control plan, MSA
  
  Phase 4: Product and Process Validation
    → Production trial runs, PPAP, capability studies
  
  Phase 5: Feedback, Assessment and Corrective Action
    → Post-SOP monitoring, lesson-learned documentation
```

---

## 10. OTA (Over-the-Air Updates) — Emerging PM Domain

```
Key PM considerations for OTA projects:
  - UNECE R155 (Cybersecurity) and R156 (SW Update Management) compliance — legal requirement since 2022 EU
  - OTA project requires: Backend server, campaign management, ECU OTA client SW, rollback mechanism
  - Phased rollout strategy: internal fleet → limited customer → full fleet
  - Rollback plan must exist before any OTA campaign launches
  - DTC and error monitoring strategy must be planned for post-update field issues
  - Cybersecurity PM: coordinate with TARA (Threat Analysis and Risk Assessment) team
```

---

*File: 02_automotive_technical_knowledge.md | Automotive PM Interview Prep | April 2026*
