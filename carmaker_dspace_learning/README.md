# CarMaker + dSPACE Complete Learning Guide

> **Target Role**: HIL Test Engineer / ADAS Validation Engineer / Embedded Systems Tester  
> **Tools Covered**: IPG CarMaker, dSPACE SCALEXIO, ControlDesk, ConfigurationDesk, AutomationDesk, Simulink  
> **Difficulty**: Intermediate → Advanced  
> **Last Updated**: May 2026

---

## Course Structure

```
carmaker_dspace_learning/
├── README.md                          ← You are here (master index)
├── 01_CarMaker_Basics.md              ← TestRun, DVA, road/driver models, TCL scripting
├── 02_Simulink_Integration.md         ← CM4SL, MIL→HIL workflow, code generation
├── 03_Real_Time_Concepts.md           ← Scheduling, WCET, overruns, RTOS, FPGA offload
├── 04_dSPACE_SCALEXIO_Architecture.md ← Hardware boards, IOCNET, processor, FPGA
├── 05_ConfigurationDesk_Basics.md     ← App config, I/O routing, build & download
├── 06_ECU_Signal_Mapping.md           ← Stimulation, measurement, fault injection, restbus
├── 07_CAN_LIN_Ethernet_Communication.md ← Bus simulation, DBC/LDF, error frames
├── 08_AutomationDesk_Testing.md       ← Test sequences, Python API, ASAM XIL, CI/CD
├── 09_HIL_Debugging.md                ← Overrun analysis, XCP DAQ, signal tracing
└── 10_ADAS_Cluster_Validation.md      ← Euro NCAP HIL, sensor injection, cluster HMI
```

---

## 10-Topic Map

| # | Topic | Key Skills | Tools |
|---|-------|-----------|-------|
| 01 | CarMaker Basics | TestRun, DVA, vehicle dynamics | IPG CarMaker |
| 02 | Simulink Integration | CM4SL, co-sim, Embedded Coder | MATLAB/Simulink |
| 03 | Real-Time Concepts | Scheduling, jitter, WCET | QNX, RTOS |
| 04 | SCALEXIO Architecture | Board selection, FPGA, IOCNET | dSPACE HW |
| 05 | ConfigurationDesk | I/O config, signal routing, build | ConfigurationDesk |
| 06 | ECU Signal Mapping | A/D-D/A, PWM, BIST bypass | ControlDesk |
| 07 | CAN/LIN/Ethernet | Bus sim, DBC/LDF, Ethernet | dSPACE DS1552/DS4330 |
| 08 | AutomationDesk | XIL API, Python tests, reports | AutomationDesk |
| 09 | HIL Debugging | Overrun, XCP DAQ, profiling | ControlDesk/Trace32 |
| 10 | ADAS/Cluster Validation | Euro NCAP, sensor inject, HMI | CarMaker + HIL |

---

## Recommended Learning Path

### Beginner (Week 1–2)
1. Read `01_CarMaker_Basics.md` → run your first TestRun
2. Read `04_dSPACE_SCALEXIO_Architecture.md` → understand the hardware
3. Read `05_ConfigurationDesk_Basics.md` → build and download a model

### Intermediate (Week 3–4)
4. Read `06_ECU_Signal_Mapping.md` → connect real ECU signals
5. Read `07_CAN_LIN_Ethernet_Communication.md` → simulate bus traffic
6. Read `03_Real_Time_Concepts.md` → understand timing

### Advanced (Week 5–6)
7. Read `02_Simulink_Integration.md` → build CM4SL model
8. Read `08_AutomationDesk_Testing.md` → automate test execution
9. Read `09_HIL_Debugging.md` → diagnose real failures
10. Read `10_ADAS_Cluster_Validation.md` → full ADAS HIL workflow

---

## Interview Readiness Checklist

- [ ] Explain the difference between MIL, SIL, HIL, VIL
- [ ] Describe SCALEXIO board selection for a project
- [ ] Walk through ConfigurationDesk → ControlDesk workflow
- [ ] Explain how CAN restbus simulation works
- [ ] Describe a real overrun you debugged
- [ ] Explain CarMaker DVA and how you used it in testing
- [ ] Describe how AutomationDesk integrates with CI/CD
- [ ] Explain sensor injection for ADAS HIL testing
- [ ] Walk through an Euro NCAP AEB test on HIL

---

## Target Companies
Vector Informatik · dSPACE · IPG Automotive · Continental · Bosch · ZF · Aptiv · Marelli · Valeo · Magna · NXP · Nvidia (AV) · Mobileye · TÜV SÜD · AVL · Ricardo
