# Automotive ECU – CAN Bus + UDS Diagnostic Simulation

A **production-quality learning project** demonstrating real-world automotive embedded software development for ECU design using CAN Bus, UDS diagnostics, and Embedded C++.

---

## What This Project Teaches

| Topic | Files | Real-World Relevance |
|-------|-------|---------------------|
| CAN Bus protocol (ISO 11898) | `include/can/`, `src/can/` | Every automotive ECU communicates via CAN |
| UDS Diagnostics (ISO 14229) | `include/uds/`, `src/uds/` | Workshop tools, production testing, EOL |
| ISO-TP (ISO 15765-2) | `uds_server.cpp` | Multi-byte UDS message segmentation |
| DTC Management | `include/ecu/dtc_manager.hpp` | Fault storage, MIL lamp control |
| ECU State Machine | `src/ecu/ecu_core.cpp` | POWER_OFF → BOOT → INIT → RUNNING |
| Embedded C++ Patterns | `docs/04_Embedded_Cpp_Patterns.md` | MISRA, no-heap, ring buffers |
| CAPL Test Scripting | `capl_scripts/` | CANalyzer/CANoe automated testing |
| Troubleshooting | `docs/05_Troubleshooting_Guide.md` | Root cause analysis, NRC decoding |

---

## Project Architecture

```
ecu_can_uds_project/
│
├── docs/                               ← Learning Material (Read First!)
│   ├── 01_CAN_Bus_Fundamentals.md     ← CAN frames, arbitration, DBC, errors
│   ├── 02_UDS_Protocol_Deep_Dive.md   ← All UDS services, NRCs, flash programming
│   ├── 03_ECU_Software_Architecture.md← AUTOSAR layers, OS tasks, NVM maps
│   ├── 04_Embedded_Cpp_Patterns.md    ← MISRA-C++, state machines, ring buffers
│   └── 05_Troubleshooting_Guide.md    ← CAN/UDS debug methods, RCA template
│
├── include/
│   ├── can/
│   │   ├── can_frame.hpp              ← CAN frame class (standard/extended/FD)
│   │   └── can_bus.hpp                ← CAN bus driver abstraction
│   ├── uds/
│   │   ├── uds_types.hpp              ← Session, NRC, DID, PDU types
│   │   └── uds_server.hpp             ← Full UDS server (ISO-TP + services)
│   └── ecu/
│       ├── dtc_manager.hpp            ← DTC storage, status, freeze frames
│       └── ecu_core.hpp               ← Top-level ECU integration
│
├── src/
│   ├── can/
│   │   ├── can_frame.cpp
│   │   └── can_bus.cpp
│   ├── uds/
│   │   └── uds_server.cpp             ← ISO-TP + all UDS service handlers
│   ├── ecu/
│   │   ├── dtc_manager.cpp
│   │   └── ecu_core.cpp               ← Task scheduler, signal Tx, DID updates
│   └── main.cpp                       ← Full simulation scenario
│
├── tests/
│   ├── test_can_bus.cpp               ← 16 unit tests for CAN layer
│   └── test_dtc_manager.cpp           ← 14 unit tests for DTC + ECU core
│
├── capl_scripts/
│   └── CAN_UDS_Tester.can             ← CANalyzer/CANoe test module
│
└── CMakeLists.txt                     ← Build system
```

---

## Quick Start

### Prerequisites
```bash
# macOS
brew install cmake

# Ubuntu/Debian
sudo apt install cmake g++ make
```

### Build & Run
```bash
cd ecu_can_uds_project
mkdir build && cd build

cmake .. -DCMAKE_BUILD_TYPE=Debug
cmake --build . -j4

# Run full ECU simulation
./ecu_simulation

# Run unit tests
./test_can_bus
./test_dtc_manager

# Or use CTest
ctest --output-on-failure
```

---

## Simulation Output (Expected)

```
╔══════════════════════════════════════════╗
║    Automotive ECU – CAN Bus + UDS        ║
╚══════════════════════════════════════════╝

[CANBus] Channel 'Powertrain_CAN' initialized @ 500000 bps
[UDSServer] Initialized. PhysReq=0x7E0 FuncReq=0x7DF Resp=0x7E8
[ECU:EngineECU] Registered 7 diagnostic DIDs

=== KEY ON ===

[CANBus][TX] ID=0x100 DLC=8 Data=10 B0 41 05 00 03 05 6F
[CAN 0x100] RPM=1068  CoolantTemp=25°C  Load=2.0%  Throttle=2.0%  Batt=13.95V

=== SCENARIO: ReadDataByIdentifier (VIN 0xF190) ===
[UDSServer] RX SID=0x22 Len=3
[CANBus][TX] ID=0x7E8 DLC=8 Data=13 62 F1 90 57 30 4C 5A
...
[UDSServer] SecurityAccess: Seed=0xA3F211C4 for level 1
[UDSServer] SecurityAccess: UNLOCKED level 1

=== Final Statistics ===
  CAN Tx frames   : 47
  CAN Rx frames   : 12
  UDS Requests    : 9
  UDS Responses   : 9
  UDS Neg Resp    : 2
  DTCs stored     : 0
```

---

## UDS Service Matrix – What's Implemented

| Service (SID) | Status | Notes |
|---------------|--------|-------|
| 0x10 DiagnosticSessionControl | ✅ | Default, Extended, Programming |
| 0x11 ECUReset | ✅ | Hard, Key-off, Soft |
| 0x14 ClearDiagnosticInformation | ✅ | All groups |
| 0x19 ReadDTCInformation | ✅ | Sub-fn 0x01, 0x02 |
| 0x22 ReadDataByIdentifier | ✅ | Multi-DID, session-gated |
| 0x27 SecurityAccess | ✅ | Seed/Key, lockout, 3 attempts |
| 0x2E WriteDataByIdentifier | ✅ | Session + security gated |
| 0x31 RoutineControl | ✅ | Start/Stop/Results |
| 0x3E TesterPresent | ✅ | Session keep-alive |
| 0x34/0x35/0x36/0x37 Upload/Download | 🔧 | Stub (extend for flash) |

---

## Key Design Decisions (Production-aligned)

1. **No heap allocation** – all objects use stack or static storage (MISRA-compliant)
2. **No C++ exceptions** – return codes (`Std_ReturnType`) throughout
3. **Lock-free ring buffer** – ISR-safe CAN Rx queue using `std::atomic`
4. **ISO-TP built-in** – UDS server handles segmentation/reassembly internally
5. **Layered architecture** – CAN driver → UDS server → ECU core (mirrors AUTOSAR)
6. **Timer abstraction** – `SystemTimer` class separates MCU/host implementations
7. **DID session gating** – can't read calibration DIDs without Extended session

---

## Learning Path

```
1. Read docs/01_CAN_Bus_Fundamentals.md        (30 min)
2. Read docs/02_UDS_Protocol_Deep_Dive.md      (45 min)
3. Build and run the simulation                 (10 min)
4. Trace through main.cpp scenarios             (20 min)
5. Read include/uds/uds_server.hpp             (15 min)
6. Study src/uds/uds_server.cpp – ISO-TP       (30 min)
7. Add a new UDS service (e.g., 0x2A periodic) (hands-on)
8. Write a CAPL test for your new service       (hands-on)
9. Read docs/05_Troubleshooting_Guide.md        (20 min)
10. Study docs/04_Embedded_Cpp_Patterns.md      (30 min)
```

---

## Interview Preparation Scenarios

This project directly covers these common interview scenarios:

| Interview Question | Where to Find Answer |
|-------------------|---------------------|
| "Explain CAN arbitration" | docs/01, can_bus.hpp |
| "How does UDS session management work?" | docs/02, uds_server.cpp |
| "Implement a DTC manager" | dtc_manager.hpp/cpp |
| "What is ISO-TP?" | docs/02, uds_server.cpp:isoTpAssemble() |
| "How do you handle security access?" | uds_server.cpp:handleSecurityAccess() |
| "Explain ECU software layers" | docs/03 |
| "How do you avoid heap allocation in embedded?" | docs/04 |
| "How would you troubleshoot CAN Bus off?" | docs/05 |
| "Write a CAPL script for UDS testing" | capl_scripts/ |

---

## Standards Referenced

- ISO 11898-1:2015 – CAN Data Link Layer
- ISO 11898-2:2016 – CAN Physical Layer
- ISO 14229-1:2020 – Unified Diagnostic Services
- ISO 15765-2:2016 – ISO-TP (CAN Transport Protocol)
- ISO 15031-6 – Diagnostic Trouble Codes (OBD-II)
- AUTOSAR Classic Platform 4.x – SW architecture
- MISRA C++:2008 – Coding guidelines for safety-critical C++
