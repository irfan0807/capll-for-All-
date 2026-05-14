# Advanced Automotive Learning — Deep Dive Series
### Industry-Grade Training: Theory + STAR Stories + Mini Projects

---

## Course Philosophy

This course is structured as **folders within folders** — each major topic is a self-contained module with:
1. `01_Theory_Deep_Dive.md` — Full technical explanation with diagrams, code, and Q&A
2. `02_STAR_Answers.md` — 6–8 ready-to-use STAR interview stories
3. `03_Mini_Projects.md` — 3–5 hands-on GitHub-ready projects with code

**Study one folder at a time. Build projects as you learn. Practice STAR stories out loud.**

---

## Folder Structure

```
advanced_automotive_learning/
│
├── README.md                          ← You are here
│
├── 01_Automotive_Ethernet/
│   ├── 01_Theory_Deep_Dive.md         ← 100BASE-T1, 1000BASE-T1, TSN, VLAN, PHY
│   ├── 02_STAR_Answers.md             ← 7 STAR interview stories
│   └── 03_Mini_Projects.md            ← 4 projects (Ethernet monitor, analyzer...)
│
├── 02_SOMEIP/
│   ├── 01_Theory_Deep_Dive.md         ← Header, SD, serialization, timing
│   ├── 02_STAR_Answers.md             ← 7 STAR stories (debugging, automation)
│   └── 03_Mini_Projects.md            ← 4 projects (event monitor, validator...)
│
├── 03_DoIP/
│   ├── 01_Theory_Deep_Dive.md         ← ISO 13400, routing, wire-level sequence
│   ├── 02_STAR_Answers.md             ← 6 STAR stories
│   └── 03_Mini_Projects.md            ← 4 projects (DoIP client, fuzzer...)
│
├── 04_Diagnostics/
│   ├── 01_Theory_Deep_Dive.md         ← UDS ISO 14229, OBD-II, DTC, flashing
│   ├── 02_STAR_Answers.md             ← 7 STAR stories
│   └── 03_Mini_Projects.md            ← 4 projects (UDS automator, DTC dashboard)
│
├── 05_ADAS_Basics/
│   ├── 01_Theory_Deep_Dive.md         ← ADAS levels, FCW/AEB/LKA/ACC architecture
│   ├── 02_STAR_Answers.md             ← 6 STAR stories
│   └── 03_Mini_Projects.md            ← 4 projects (scenario simulator, test bench)
│
├── 06_Radar_Lidar/
│   ├── 01_Theory_Deep_Dive.md         ← Radar physics, LiDAR principles, sensor fusion
│   ├── 02_STAR_Answers.md             ← 6 STAR stories
│   └── 03_Mini_Projects.md            ← 4 projects (point cloud, FMCW sim...)
│
└── 07_CarMaker_dSPACE/
    ├── 01_Theory_Deep_Dive.md         ← HIL architecture, CarMaker, SCALEXIO, Python API
    ├── 02_STAR_Answers.md             ← 6 STAR stories
    └── 03_Mini_Projects.md            ← 4 projects (AEB HIL suite, automation...)
```

---

## Recommended Learning Path

### Beginner Path (4 weeks)
```
Week 1: 01_Automotive_Ethernet → 02_SOMEIP
Week 2: 03_DoIP → 04_Diagnostics
Week 3: 05_ADAS_Basics → 06_Radar_Lidar
Week 4: 07_CarMaker_dSPACE → Build 2 mini projects
```

### Interview Fast-Track (2 weeks)
```
Day 1–2:   All Theory files (skim + mark key facts)
Day 3–5:   All STAR files (memorize 3 per topic)
Day 6–7:   Build Project 1 from each folder
Day 8–10:  Mock interviews using STAR stories
Day 11–14: Deep dive on your weakest 2 topics
```

---

## Technology Stack

| Layer | Tools / Standards |
|-------|-------------------|
| Physical | 100BASE-T1 (IEEE 802.3bw), NXP TJA1100 PHY |
| Network | Automotive Ethernet, VLAN (802.1Q), TSN (802.1AS/Qbv) |
| Transport | TCP/IP, UDP, ISO 13400 (DoIP) |
| Application | SOME/IP, UDS (ISO 14229), OBD-II |
| AUTOSAR | Classic 4.x — SoAd, TcpIp, EthIf, DCM, DEM |
| Simulation | dSPACE SCALEXIO, IPG CarMaker, MATLAB/Simulink |
| Tools | CANoe 15, CAPL, Wireshark, Python 3.11, pytest |
| ADAS Sensors | RADAR (FMCW 77GHz), LiDAR (ToF/FMCW), Camera |
| Safety | ISO 26262, ASIL A–D, ASPICE SWE.4/5/6 |

---

## Quick Reference: Target Companies & Roles

| Company | Role | Key Skills Needed |
|---------|------|-------------------|
| Bosch | ECU Validation Engineer | CAN, Ethernet, AUTOSAR, CANoe |
| Continental | ADAS Test Engineer | Radar, Camera, ISO 26262, HIL |
| KPIT | Automotive Ethernet Dev | SOME/IP, DoIP, AUTOSAR, Python |
| Tata Elxsi | Vehicle Communication Lead | CAN FD, Ethernet, dSPACE |
| Harman | Connected Vehicle Engineer | Ethernet, TCP/IP, OTA, DoIP |
| Aptiv | Functional Safety Engineer | ISO 26262, ASIL, ASPICE |
| ZF | ADAS Integration Engineer | Radar, Lidar, Sensor Fusion |
| Mercedes-Benz R&D | Protocol Validation Specialist | SOME/IP, TSN, V2X |

---

*Start with: [01_Automotive_Ethernet/01_Theory_Deep_Dive.md](01_Automotive_Ethernet/01_Theory_Deep_Dive.md)*
