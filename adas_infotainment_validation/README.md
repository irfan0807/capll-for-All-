# ADAS & Infotainment Validation — Complete Learning Guide

> **Target Role**: ADAS Test Engineer / Infotainment Validation Engineer / Embedded SW Tester  
> **Coverage**: Full software delivery pipeline → simulation → ECU testing → HMI validation  
> **Last Updated**: May 2026

---

## What This Guide Covers

This guide walks through the **complete validation lifecycle** of two of the most complex systems in a modern vehicle:

- **ADAS (Advanced Driver Assistance Systems)** — perception, fusion, decision, actuation
- **Infotainment (IVI)** — head unit, connectivity, HMI, multimedia, OTA updates

```
Software Journey:
──────────────────────────────────────────────────────────────────────
Developer writes code  →  SW Release  →  Integration  →  Test  →  Homologation
     (IDE/Jira)           (Gerrit/Git)   (SIL/HIL)    (Bench/Road)  (TÜV/NHTSA)
──────────────────────────────────────────────────────────────────────
```

---

## Folder Structure

```
adas_infotainment_validation/
├── README.md                                   ← You are here
├── 01_ADAS_Testing_Fundamentals.md             ← V-model, ASIL, levels, terminology
├── 02_Software_Delivery_to_Testing.md          ← Git→Flash→Bench pipeline
├── 03_ADAS_ECU_Testing.md                      ← Unit/integration/system ECU tests
├── 04_Simulation_Methods.md                    ← SIL, CarMaker, sensor sim, scenarios
├── 05_Infotainment_Validation.md               ← IVI, HMI, connectivity, OTA testing
└── 06_Test_Automation_CI_CD.md                 ← Frameworks, Python, Jenkins, reports
```

---

## Topic Map

| # | File | Key Content | Tools |
|---|------|-------------|-------|
| 01 | ADAS Testing Fundamentals | V-model, ASIL, test levels, ODD | ISO 26262, SOTIF |
| 02 | SW Delivery to Testing | Git, release, flashing, sanity | Gerrit, JIRA, UDS |
| 03 | ADAS ECU Testing | Bench setup, signal injection, regression | dSPACE, CANoe |
| 04 | Simulation Methods | SIL, HIL, CarMaker, scenario DB | CarMaker, Prescan |
| 05 | Infotainment Validation | HMI, media, connectivity, OTA | Android, ADB, Appium |
| 06 | CI/CD Automation | Python, pytest, Jenkins, reporting | Jenkins, pytest |

---

## Recommended Learning Path

**Week 1**: Topics 01 → 02 (Understand the process first)  
**Week 2**: Topics 03 → 04 (Get into technical testing)  
**Week 3**: Topic 05 (Infotainment specifics)  
**Week 4**: Topic 06 (Automate everything)

---

## Interview Readiness Checklist

- [ ] Explain the V-model and where each test level sits
- [ ] Describe how you receive software from development
- [ ] Walk through flashing an ECU and performing a sanity check
- [ ] Explain what MIL, SIL, and HIL mean and when each is used
- [ ] Describe sensor injection for ADAS HIL testing
- [ ] Explain ISO 26262 ASIL and why it matters for test design
- [ ] Describe how you validate an HMI response
- [ ] Explain OTA update testing for infotainment
- [ ] Walk through a Euro NCAP AEB test on simulation
- [ ] Explain how CI/CD fits into automotive test validation
