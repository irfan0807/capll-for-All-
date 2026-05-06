# ECU Embedded Testing in Automotive Domain
## Complete Professional Guide for CSE Engineers

> **Who this is for**: Engineers with a Computer Science / CSE background who are working in — or transitioning into — automotive ECU embedded testing. You understand software, C, debugging, and testing theory. This guide bridges your CS knowledge to the automotive embedded world.

---

## Table of Contents

1. [What is an ECU and Why Do We Test It?](#1-what-is-an-ecu-and-why-do-we-test-it)
2. [Automotive Software Architecture — AUTOSAR](#2-automotive-software-architecture--autosar)
3. [ECU Communication Protocols — CAN, LIN, UDS, DoIP](#3-ecu-communication-protocols--can-lin-uds-doip)
4. [ECU Testing Levels — Unit, Integration, System, HIL](#4-ecu-testing-levels--unit-integration-system-hil)
5. [Test Environment Setup — MIL, SIL, PIL, HIL](#5-test-environment-setup--mil-sil-pil-hil)
6. [Writing ECU Test Cases — Methodology and Templates](#6-writing-ecu-test-cases--methodology-and-templates)
7. [Diagnostic Testing — UDS Protocol Deep Dive](#7-diagnostic-testing--uds-protocol-deep-dive)
8. [CAN Bus Testing with CANoe and CAPL](#8-can-bus-testing-with-canoe-and-capl)
9. [Requirement-Based Testing and Traceability](#9-requirement-based-testing-and-traceability)
10. [Fault Injection and Negative Testing](#10-fault-injection-and-negative-testing)
11. [Automated ECU Test Frameworks — Python](#11-automated-ecu-test-frameworks--python)
12. [ISO 26262 Functional Safety Testing](#12-iso-26262-functional-safety-testing)
13. [Debugging ECU Failures — Tools and Techniques](#13-debugging-ecu-failures--tools-and-techniques)
14. [Real Work Scenarios and Walkthroughs](#14-real-work-scenarios-and-walkthroughs)
15. [ECU Boot Sequence — Testing Startup and Shutdown](#15-ecu-boot-sequence--testing-startup-and-shutdown)
16. [AUTOSAR OS — Scheduling, Tasks, and Timing Tests](#16-autosar-os--scheduling-tasks-and-timing-tests)
17. [CAN Error Handling — Bus-Off, TEC, REC Deep Dive](#17-can-error-handling--bus-off-tec-rec-deep-dive)
18. [CAN-FD — Testing Flexible Data Rate](#18-can-fd--testing-flexible-data-rate)
19. [XCP — Calibration and Measurement Protocol](#19-xcp--calibration-and-measurement-protocol)
20. [OBD-II Testing — On-Board Diagnostics](#20-obd-ii-testing--on-board-diagnostics)
21. [NvM Testing — Non-Volatile Memory](#21-nvm-testing--non-volatile-memory)
22. [DTC Lifecycle — Complete State Machine](#22-dtc-lifecycle--complete-state-machine)
23. [Flash Programming — Deep Dive Test Strategy](#23-flash-programming--deep-dive-test-strategy)
24. [Network Management — AUTOSAR NM Testing](#24-network-management--autosar-nm-testing)
25. [ECU State Machine Testing](#25-ecu-state-machine-testing)
26. [Static Analysis and Code Coverage in ECU SW](#26-static-analysis-and-code-coverage-in-ecu-sw)
27. [CI/CD Pipeline for ECU Testing](#27-cicd-pipeline-for-ecu-testing)
28. [EMC and Environmental Robustness Testing](#28-emc-and-environmental-robustness-testing)
29. [Interview Preparation — 80 Q&A](#29-interview-preparation--80-qa)

---

## 1. What is an ECU and Why Do We Test It?

### 1.1 ECU — Electronic Control Unit

An ECU is an embedded computer inside a vehicle that controls one specific function. Modern vehicles have 70–150 ECUs communicating over a shared network.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     VEHICLE ELECTRONIC ARCHITECTURE                     │
│                                                                         │
│  Engine        Transmission    Brakes       Steering      Body         │
│  Control       Control         (ABS/ESC)    (EPS)         Control      │
│  Module (ECM)  Module (TCM)    Module       Module        Module       │
│     │              │              │             │             │         │
│     └──────────────┴──────────────┴─────────────┴─────────────┘        │
│                              CAN Bus                                    │
│     ┌──────────────────────────────────────────────────┐               │
│     │          Gateway ECU (Central Hub)               │               │
│     └──────────────────────────────────────────────────┘               │
│              │              │              │                            │
│         LIN Bus          FlexRay        Ethernet                       │
│    (body functions)   (chassis/powertrain)  (ADAS, infotainment)       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 ECU Hardware Components

```
┌─────────────────────────────────────────────────────────────────┐
│  ECU HARDWARE BLOCK DIAGRAM                                     │
│                                                                 │
│  Power Supply ──► Voltage Regulator ──► 3.3V / 5V rails        │
│                                                                 │
│  Microcontroller (MCU)                                          │
│  ┌──────────────────────────────────┐                           │
│  │  CPU Core (ARM Cortex-M / TriCore│                           │
│  │  Flash (code + cal data)          │                           │
│  │  SRAM (variables, stack, heap)    │                           │
│  │  CAN Controller (1-6 channels)    │──► CAN Transceiver ──► Bus│
│  │  LIN Controller                   │──► LIN Transceiver ──► Bus│
│  │  SPI / I2C / UART                 │──► Sensors / EEPROM       │
│  │  ADC (12-16 bit)                  │◄── Analog sensors         │
│  │  PWM outputs                      │──► Actuators / motors     │
│  │  Watchdog Timer                   │    (hardware safety)      │
│  │  DMA Controller                   │                           │
│  └──────────────────────────────────┘                           │
│                                                                 │
│  External EEPROM / Flash (non-volatile data, calibration)       │
│  JTAG / SWD debug port (for development only)                   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Why ECU Testing is Different from Regular Software Testing

| Dimension | Regular Software Testing | ECU Embedded Testing |
|---|---|---|
| Target | PC / Server / Mobile | Microcontroller (resource-constrained) |
| OS | Full OS (Linux, Windows, Android) | Bare metal or RTOS (FreeRTOS, OSEK) |
| Debugging | IDE debugger, logs, remote debug | JTAG, serial traces, oscilloscope |
| Test environment | Local machine | HIL rack with real hardware simulation |
| Time constraints | Usually loose | Hard real-time (miss a deadline = failure) |
| Failure impact | App crash, retry | Vehicle crash, safety hazard |
| Standards | General SQA | ISO 26262, ASPICE, MISRA C |
| Language | Python, Java, JS, etc. | C / Embedded C (primarily) |
| Memory | GB of RAM | 64 KB – 4 MB SRAM |
| Communication | TCP/IP, REST APIs | CAN, LIN, SPI, I2C, UDS |
| Test tools | JUnit, pytest, Selenium | CANoe, CANalyzer, INCA, dSPACE |

### 1.4 ECU Testing in the V-Model

The automotive industry uses the **V-Model** — every development step on the left has a corresponding test step on the right:

```
Requirements ──────────────────────────────► Acceptance Test
    │                                              │
  System Design ─────────────────────► System Test (HIL)
       │                                      │
     SW Architecture ───────────► Integration Test (SIL)
          │                               │
        SW Detailed Design ─────► Unit Test (MIL / SIL)
               │                       │
             Coding ◄──────────────────┘
```

---

## 2. Automotive Software Architecture — AUTOSAR

### 2.1 AUTOSAR Classic Platform Layers

AUTOSAR (AUTomotive Open System ARchitecture) standardises ECU software structure so that software from different suppliers can run on different hardware with minimal changes.

```
┌─────────────────────────────────────────────────────────┐
│  APPLICATION LAYER                                      │
│  SWC: Software Components (the actual feature logic)    │
│  e.g., SpeedControl_SWC, BrakeControl_SWC              │
├─────────────────────────────────────────────────────────┤
│  RUNTIME ENVIRONMENT (RTE)                              │
│  Middleware that connects SWCs to BSW                   │
│  Generated code — never written manually                │
├─────────────────────────────────────────────────────────┤
│  BASIC SOFTWARE (BSW)                                   │
│  ┌────────────┬──────────────┬──────────────────────┐   │
│  │  Services  │ ECU Abstraction  │  Microcontroller  │   │
│  │  OSEK/OS   │ CAN Interface    │  Abstraction      │   │
│  │  NvM       │ ADC abstraction  │  (MCAL)           │   │
│  │  COM       │ I/O Hardware     │  CAN Driver       │   │
│  │  DCM (diag)│ Abstraction      │  ADC Driver       │   │
│  └────────────┴──────────────┴──────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  MICROCONTROLLER (Hardware)                             │
│  Renesas RH850, Infineon TriCore, NXP S32K, STM32       │
└─────────────────────────────────────────────────────────┘
```

### 2.2 AUTOSAR Modules Commonly Tested

| Module | Purpose | What You Test |
|---|---|---|
| **COM** | Signal packing/unpacking for CAN | Signal values, endianness, scaling |
| **DCM** | Diagnostic Communication Manager | UDS service responses |
| **DEM** | Diagnostic Event Manager | DTC storage, snapshot data |
| **NvM** | Non-Volatile Memory Manager | Data persistence across power cycles |
| **WdgM** | Watchdog Manager | Reset on task deadline miss |
| **OS** | OSEK/AUTOSAR OS | Task scheduling, timing |
| **CanSM** | CAN State Manager | Bus-off recovery, network management |
| **ComM** | Communication Manager | Network wake-up/sleep sequences |
| **Rte** | Runtime Environment | Port connections, inter-SWC communication |

### 2.3 CSE Engineer's Bridge to AUTOSAR

> **For CSE engineers**: Think of AUTOSAR like this:
> - **SWC** = your business logic class/module
> - **RTE** = dependency injection framework / middleware (like Spring DI)
> - **BSW** = OS + hardware drivers (like Linux kernel + device drivers)
> - **MCAL** = HAL (Hardware Abstraction Layer) — like POSIX for Linux

---

## 3. ECU Communication Protocols — CAN, LIN, UDS, DoIP

### 3.1 CAN Bus — The Backbone

CAN (Controller Area Network) is the primary bus for ECU-to-ECU communication.

```
Physical layer:
  Two wires: CAN_H (High) and CAN_L (Low)
  Differential voltage: dominant = CAN_H - CAN_L ≈ 2V
                        recessive = CAN_H - CAN_L ≈ 0V

Bit rates (CAN 2.0):
  125 kbps — body/comfort functions (windows, lights)
  250 kbps — chassis / diagnostic bus
  500 kbps — powertrain (engine, transmission)
  1 Mbps   — high-speed (rare in classic CAN)

CAN FD (Flexible Data-rate):
  Arbitration phase: up to 1 Mbps
  Data phase:        up to 8 Mbps
  Data payload:      up to 64 bytes (vs 8 bytes for CAN 2.0)
```

**CAN Frame Structure**:

```
 SOF  │ Arbitration ID │ Control │   Data (0-8 bytes)   │ CRC │ ACK │ EOF
  1   │   11 or 29 bit │  6 bit  │    0–64 bytes        │15+1 │  2  │  7
 bit  │                │         │                      │ bit │bit  │ bit

SOF  = Start of Frame (dominant bit)
ID   = Message identifier (also determines priority — lower = higher priority)
RTR  = Remote Transmission Request
DLC  = Data Length Code (0–8 for CAN 2.0, 0–15 for CAN FD)
CRC  = Cyclic Redundancy Check (15-bit)
ACK  = Acknowledgement (any receiver pulls this dominant)
EOF  = End of Frame (7 recessive bits)
```

**DBC File — Database of CAN messages**:

A DBC file defines every message on the CAN bus. It is the "API contract" of the network.

```
VERSION ""

NS_:    /* symbols */

BS_:    /* bit timing */

BU_: ECM TCM ABS EPS BCM GW   /* list of nodes */

/* Message: Engine Speed */
BO_ 100 EngineStatus: 8 ECM
 SG_ EngineSpeed : 0|16@1+ (0.25,0) [0|16383.75] "rpm" TCM,ABS,GW
 SG_ CoolantTemp : 16|8@1+ (1,-40) [−40|215] "degC" BCM,GW
 SG_ ThrottlePos : 24|8@1+ (0.392157,0) [0|100] "%" TCM,GW
 SG_ EngineRunning : 32|1@1+ (1,0) [0|1] "" TCM,ABS,GW
 SG_ CheckEngineLight : 33|1@1+ (1,0) [0|1] "" BCM,GW

/*
 Signal format: Name : start_bit | length @ byte_order value_type
                       (factor, offset) [min|max] "unit" receivers
 @1 = little-endian (Intel), @0 = big-endian (Motorola)
 + = unsigned, - = signed
*/
```

### 3.2 LIN Bus

LIN (Local Interconnect Network) is used for low-cost sensors/actuators (windows, mirrors, rain sensor):

```
Single wire, 12V, up to 20 kbps
Master-slave: only master initiates communication
Master sends header (break + sync + frame ID), slave responds with data

Use cases: window lift, sunroof, mirror control, rain sensor, seat position
```

### 3.3 UDS — Unified Diagnostic Services

UDS (ISO 14229) is the protocol used for all ECU diagnostics, reprogramming, and calibration.

```
Request/Response pattern over CAN (or Ethernet via DoIP)

Request: [Service ID] [Sub-function] [Parameters...]
Response (positive): [Service ID + 0x40] [Data...]
Response (negative): [0x7F] [Service ID] [NRC]

NRC = Negative Response Code
  0x10 = generalReject
  0x11 = serviceNotSupported
  0x12 = subFunctionNotSupported
  0x22 = conditionsNotCorrect
  0x24 = requestSequenceError
  0x31 = requestOutOfRange
  0x33 = securityAccessDenied
  0x35 = invalidKey
  0x78 = requestCorrectlyReceivedResponsePending (keep alive)
```

**Key UDS Services**:

| Service ID | Name | What it does |
|---|---|---|
| 0x10 | DiagnosticSessionControl | Enter Default/Extended/Programming session |
| 0x11 | ECUReset | Soft reset, hard reset |
| 0x14 | ClearDiagnosticInformation | Clear DTCs |
| 0x19 | ReadDTCInformation | Read stored fault codes |
| 0x22 | ReadDataByIdentifier | Read live data (VIN, sensor values) |
| 0x27 | SecurityAccess | Unlock ECU for programming (seed-key) |
| 0x2E | WriteDataByIdentifier | Write configuration data |
| 0x2F | InputOutputControlByIdentifier | Force ECU outputs for testing |
| 0x31 | RoutineControl | Execute ECU routines (calibration, self-test) |
| 0x34 | RequestDownload | Start flash programming session |
| 0x36 | TransferData | Send firmware data blocks |
| 0x37 | RequestTransferExit | End flash programming |
| 0x3E | TesterPresent | Keep ECU in diagnostic session alive |

### 3.4 ISO-TP — Transport Protocol

UDS messages can be larger than 8 bytes. ISO-TP (ISO 15765-2) segments them:

```
Single Frame (SF): payload ≤ 7 bytes
  Byte 0: [0][length 4-bit]
  Bytes 1-7: data

First Frame (FF): payload > 7 bytes, first 6 bytes
  Byte 0: [1][length high 4-bit]
  Byte 1: length low 8-bit
  Bytes 2-7: data[0..5]

Consecutive Frame (CF): remaining bytes
  Byte 0: [2][sequence number 4-bit]
  Bytes 1-7: data

Flow Control (FC): sent by receiver to allow transmission
  Byte 0: [3][flow status: 0=ContinueToSend, 1=Wait, 2=Overflow]
  Byte 1: BlockSize (0 = send all)
  Byte 2: SeparationTime (milliseconds)

Example — send 20-byte UDS response:
  ECU sends FF: [10][14][d0][d1][d2][d3][d4][d5]
  Tester sends FC: [30][00][00]
  ECU sends CF1: [21][d6][d7][d8][d9][da][db][dc]
  ECU sends CF2: [22][dd][de][df][d10][d11][d12][d13]
```

### 3.5 DoIP — Diagnostics over IP (Ethernet)

Modern vehicles with Ethernet backbone use DoIP (ISO 13400) instead of CAN-based UDS:

```
Architecture:
  Tester PC ──► Ethernet ──► Gateway ECU ──► CAN/LIN ──► Target ECU

DoIP uses TCP/UDP on port 13400
UDS payload is the same — only transport layer changes from ISO-TP to TCP/IP

Activation sequence:
  1. UDP broadcast: VehicleIdentificationRequest
  2. ECU responds: VehicleIdentificationResponse (VIN, logical address)
  3. TCP connect to port 13400
  4. RoutingActivation request/response
  5. Normal UDS messages over TCP
```

---

## 4. ECU Testing Levels — Unit, Integration, System, HIL

### 4.1 Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                    ECU TEST LEVELS                                   │
│                                                                      │
│  Level 4: Vehicle Test         Real vehicle, road/track             │
│           ─────────────────────────────────────────────             │
│  Level 3: HIL Test             ECU + simulated vehicle              │
│           (Hardware-in-Loop)   (fastest feedback at system level)   │
│           ─────────────────────────────────────────────             │
│  Level 2: SIL Test             Software on PC, no hardware          │
│           (Software-in-Loop)                                        │
│           ─────────────────────────────────────────────             │
│  Level 1: Unit Test            Individual function / module on PC   │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Unit Testing ECU Software

Unit tests run on the host PC (not on the MCU). The hardware is replaced with mocks.

**What you test at unit level**:
- Individual C functions / modules
- State machines (transitions, guards)
- Calculation functions (PID controllers, signal conversions)
- Error handling paths

**Tools**: Unity (C), Google Test (C++), CMock (for mocking), pytest (for Python wrapper tests)

```c
/* Example: Test a speed calculation function */
/* Production code */
float Speed_Convert_KphToMs(float kph) {
    return kph / 3.6f;
}

/* Unit test — runs on PC */
#include "unity.h"

void test_speed_convert_zero(void) {
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, Speed_Convert_KphToMs(0.0f));
}

void test_speed_convert_100kph(void) {
    /* 100 km/h = 27.778 m/s */
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 27.778f, Speed_Convert_KphToMs(100.0f));
}

void test_speed_convert_negative(void) {
    /* Reverse speed — should handle gracefully */
    float result = Speed_Convert_KphToMs(-10.0f);
    TEST_ASSERT_TRUE(result < 0.0f);
}
```

### 4.3 Integration Testing (SIL — Software-in-Loop)

Integration tests verify that software modules communicate correctly with each other.

**What you test at integration level**:
- AUTOSAR COM signal routing between SWCs
- UDS service handling chain (DCM → DEM → application)
- NvM read/write through the full stack
- Task scheduling and timing

**Tools**: MATLAB/Simulink SIL mode, dSPACE VEOS, AUTOSAR-specific test tools, pytest with AUTOSAR virtual platform

### 4.4 HIL Testing (Hardware-in-Loop)

HIL is the most important test environment in automotive. The real ECU hardware is tested but the vehicle is simulated.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HIL TEST SETUP                                       │
│                                                                         │
│  ┌─────────────────┐        ┌──────────────────────┐                   │
│  │   REAL ECU       │        │   HIL SIMULATOR       │                   │
│  │                 │        │ (dSPACE / NI LabVIEW) │                   │
│  │  Firmware       │◄──────►│                       │                   │
│  │  running on     │  CAN   │  Vehicle model        │                   │
│  │  real MCU       │  LIN   │  (engine, wheels,     │                   │
│  │                 │  I/O   │   sensors, actuators) │                   │
│  └─────────────────┘        │                       │                   │
│                             │  Fault insertion unit │                   │
│  ┌─────────────────┐        │  (short to GND/VCC,   │                   │
│  │  Test PC        │◄──────►│   open circuit,       │                   │
│  │  (CANoe, INCA,  │  CAN   │   out-of-range signal)│                   │
│  │   Python test   │        │                       │                   │
│  │   scripts)      │        └──────────────────────┘                   │
│  └─────────────────┘                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

**What you test at HIL level**:
- ECU response to simulated sensor inputs (throttle, brake, speed)
- CAN message timing and content
- ECU behaviour in fault conditions (sensor open/short, voltage drops)
- Startup and shutdown sequences
- Diagnostic communication (UDS) on real hardware

---

## 5. Test Environment Setup — MIL, SIL, PIL, HIL

### 5.1 The Four Simulation Levels

```
MIL — Model in the Loop
  What runs: Both plant model and controller model in simulation
  Hardware: None — pure software simulation
  Used for: Algorithm validation before any code generation
  Tools: MATLAB/Simulink

SIL — Software in the Loop
  What runs: Generated C code from model + plant model in simulation
  Hardware: PC (x86)
  Used for: Verify generated code matches model behaviour
  Tools: Simulink SIL, dSPACE VEOS, AUTOSAR virtual platform

PIL — Processor in the Loop
  What runs: Generated C code compiled for TARGET MCU + plant model on PC
  Hardware: Target MCU board (e.g., Aurix TC397) connected via serial
  Used for: Verify code runs correctly on actual processor
  Tools: Simulink PIL, JTAG debug connection

HIL — Hardware in the Loop
  What runs: Full ECU (real hardware + real firmware)
  Hardware: Real ECU + HIL simulator (dSPACE DS1007, NI PXI)
  Used for: System-level testing, regression, acceptance
  Tools: CANoe, INCA, Python automation, dSPACE ControlDesk
```

### 5.2 Practical HIL Environment — What You Actually Touch Daily

```python
# Typical HIL automation test script (Python + CANoe COM API)
import win32com.client  # pywin32 — Vector CANoe COM automation
import time

class CANoeHIL:
    def __init__(self, cfg_path: str):
        self.app = win32com.client.Dispatch("CANoe.Application")
        self.app.Open(cfg_path)
        self.measurement = self.app.Measurement
        self.bus = self.app.getBus("CAN")

    def start(self):
        self.measurement.Start()
        time.sleep(2.0)  # let bus settle

    def stop(self):
        self.measurement.Stop()

    def get_signal(self, msg_name: str, sig_name: str) -> float:
        """Read a signal from the CANoe environment"""
        sig = self.app.GetBus("CAN").GetSignal(msg_name, sig_name)
        return sig.Value

    def set_signal(self, msg_name: str, sig_name: str, value: float):
        """Inject a signal value into the simulation"""
        sig = self.app.GetBus("CAN").GetSignal(msg_name, sig_name)
        sig.Value = value

    def send_uds_request(self, tester_id: int, ecu_id: int,
                         data: bytes) -> bytes:
        """Send a UDS request and get response"""
        # Implementation via CAPL function or python-can + isotp
        pass
```

### 5.3 Setting Up a Minimal Test Bench on Your Desk

Without a full HIL rack, you can still do meaningful testing:

```
Equipment needed for desktop ECU testing:
  1. ECU under test (or ADAS/body control module development board)
  2. 12V power supply (bench supply with current limit at 3A)
  3. CAN interface adapter: Vector VN1610 or Kvaser Leaf Pro
  4. PC with CANoe or python-can + isotp installed
  5. Multimeter + oscilloscope (Rigol DS1054Z is affordable)
  6. Jumper wires for fault injection (open circuit simulation)

Software (free/trial):
  - python-can: pip install python-can
  - python-isotp: pip install can-isotp
  - udsoncan: pip install udsoncan
  - CANalyzer trial: Vector website (30-day free trial)
```

---

## 6. Writing ECU Test Cases — Methodology and Templates

### 6.1 IEEE 829 Test Case Structure (Automotive Adapted)

```
Test Case ID   : TC-ECU-[MODULE]-[NUMBER]
Test Case Name : Clear, action-oriented description
Version        : 1.0
Date           : 2026-05-05
Author         : [Name, Role]
Reviewed by    : [Name]
Approved by    : [Name]

LINKS
  Requirement(s)  : [SRS-XXX-NNN] (trace to SW requirement)
  Test Plan       : [TP-XXX-001]
  Related Defects : [JIRA-NNN] (if testing a bug fix)

OBJECTIVE
  One sentence: what property of the ECU does this test verify?

PRECONDITIONS
  - ECU powered with 12V ± 0.5V
  - Default session active (DiagnosticSession = 0x01)
  - No active DTCs present (cleared before test)
  - [Any specific initialisation required]

TEST ENVIRONMENT
  - Tool: CANoe 17.0 / Python 3.11 + udsoncan 1.22
  - Interface: Vector VN1610 @ 500 kbps
  - ECU: [Part number, SW version, HW version]

TEST STEPS
  #   Action                              Expected Result         Status
  1   Power on ECU                        ECU sends NM frames     [ ]
      → observe CAN bus
  2   Wait for initialisation (5 s)       No DTC active           [ ]
  3   Send 0x22 0xF1 0x86 (Read SW ver)  Positive response       [ ]
      (ReadDataByIdentifier, DID=0xF186)  [0x62 0xF1 0x86 <ver>]
  4   Verify response length = 6 bytes    length == 6             [ ]
  5   Verify version string is ASCII      All bytes in 0x20-0x7E  [ ]

PASS CRITERIA
  All steps show "Pass". No unexpected negative response.
  SW version string is non-empty and printable ASCII.

FAIL CRITERIA
  Any step produces unexpected result OR
  Response timeout (> 150 ms) OR
  NRC received (0x7F response)

POST-CONDITIONS
  ECU left in default session, no DTCs introduced

NOTES
  DID 0xF186 is defined in ISO 14229-1 Annex C
  If ECU returns NRC 0x31 (requestOutOfRange), DID may not be supported
  — this is not a failure, update preconditions note
```

### 6.2 Test Case Categories for ECU Testing

```
Category 1: Normal Function Tests (happy path)
  - ECU correctly processes valid inputs
  - CAN signals within normal range produce correct outputs
  - Example: throttle input 0-100% → correct engine torque request

Category 2: Boundary Tests
  - Values at exact min, max, just inside, just outside limits
  - Example: coolant temp sensor: min=-40°C, max=150°C
    → test at: -41°C (below min), -40°C, 0°C, 149°C, 150°C, 151°C

Category 3: Negative / Fault Tests
  - Invalid inputs, out-of-range values, protocol violations
  - Example: DLC=0 CAN frame when 8 bytes expected

Category 4: Fault Injection Tests
  - Hardware fault simulation: short to GND, open circuit, short to VCC
  - CAN bus fault: bus-off, dominant spikes, missing frames

Category 5: Timing Tests
  - Message periodicity verification (500 ms ± 10%)
  - Diagnostic response time < 150 ms (P2 server max timer)
  - ECU reset recovery time < 500 ms

Category 6: Regression Tests
  - Re-run after every firmware change to catch regressions
  - Automated — should run in CI pipeline

Category 7: Diagnostic Tests
  - All UDS services: session transitions, DTC storage/clear, flashing
  - Security access seed-key algorithm
```

### 6.3 Equivalence Partitioning for Sensor Inputs

> **CSE concept applied to automotive**: Equivalence partitioning (the same technique you know from software testing) applies directly to ECU inputs.

```
Example: Throttle Position Sensor (TPS) — valid range 0.5V to 4.5V

Partition 1: Below minimum (invalid)
  Values: 0V, 0.1V, 0.49V
  Expected: ECU sets DTC "TPS signal below range"

Partition 2: Valid range
  Values: 0.5V, 2.5V, 4.5V
  Expected: Normal operation, throttle position calculated

Partition 3: Above maximum (invalid)
  Values: 4.51V, 4.8V, 5V
  Expected: ECU sets DTC "TPS signal above range"

Partition 4: Open circuit (wire disconnected)
  Values: High impedance → ADC reads 0V or VCC depending on pull
  Expected: ECU detects "TPS open circuit" DTC

Partition 5: Short to GND
  Values: 0V solid
  Expected: ECU detects "TPS short to GND" DTC

Partition 6: Short to battery (12V)
  Values: > 5V on 5V-referenced ADC
  Expected: ADC protection, DTC "TPS short to battery"
```

---

## 7. Diagnostic Testing — UDS Protocol Deep Dive

### 7.1 Session Management Testing

Before any diagnostic operation, you must be in the correct session:

```
Session Hierarchy:
  Default Session (0x01)        ← ECU starts here on power-on
       │
  Extended Session (0x03)       ← Allows DTC read/clear, IO control
       │
  Programming Session (0x02)    ← Allows flashing firmware
       │
  (Supplier-specific sessions)  ← 0x60-0x7E for OEM/supplier

Test: Session transition matrix
┌─────────────────┬─────────────────────────────────────────────────┐
│  From \ To      │  Default   │  Extended  │  Programming          │
├─────────────────┼────────────┼────────────┼───────────────────────┤
│ Default         │ OK (no-op) │ OK         │ OK (if precond met)   │
│ Extended        │ OK         │ OK (no-op) │ OK (if security done) │
│ Programming     │ After reset│ N/A        │ OK (no-op)            │
└─────────────────┴────────────┴────────────┴───────────────────────┘
```

### 7.2 UDS Testing with Python (udsoncan library)

```python
"""
ECU Diagnostic Testing using udsoncan + python-can
Tested with: Vector VN1610 on 500 kbps CAN bus
"""

import udsoncan
from udsoncan.client import Client
from udsoncan.connections import PythonIsoTpConnection
import isotp
import can
import time
import pytest


# ── Connection setup ──────────────────────────────────────────────────────

def make_uds_client(interface: str = "vector",
                    channel: int = 0,
                    tx_id: int = 0x7E0,
                    rx_id: int = 0x7E8) -> Client:
    """Create a UDS client connected to the ECU under test."""
    bus = can.interface.Bus(
        interface=interface,
        channel=channel,
        bitrate=500000,
    )
    tp_addr = isotp.Address(
        isotp.AddressingMode.Normal_11bits,
        txid=tx_id,
        rxid=rx_id,
    )
    conn = PythonIsoTpConnection(bus, tp_addr)
    config = {
        "exception_on_negative_response": False,
        "exception_on_invalid_response": True,
        "p2_timeout": 0.15,     # 150 ms — ISO 14229 default
        "p2_star_timeout": 5.0, # 5 s for 0x78 NRC pending
    }
    return Client(conn, config=config)


# ── Test cases ────────────────────────────────────────────────────────────

class TestSessionControl:

    def test_enter_default_session(self, uds_client):
        """Verify ECU accepts DiagnosticSessionControl for Default session."""
        resp = uds_client.change_session(
            udsoncan.DiagnosticSessionControl.Session.defaultSession
        )
        assert resp.positive, f"Failed to enter Default session: {resp.code}"

    def test_enter_extended_session(self, uds_client):
        """Verify ECU transitions to Extended Diagnostic session."""
        resp = uds_client.change_session(
            udsoncan.DiagnosticSessionControl.Session.extendedDiagnosticSession
        )
        assert resp.positive, f"Failed to enter Extended session: {resp.code}"

    def test_session_timeout_returns_to_default(self, uds_client):
        """If TesterPresent is not sent, ECU should return to Default session."""
        uds_client.change_session(
            udsoncan.DiagnosticSessionControl.Session.extendedDiagnosticSession
        )
        # Do NOT send TesterPresent — wait for S3 timer (5 seconds default)
        time.sleep(6.0)
        # Now try an Extended-session-only service — should get NRC
        resp = uds_client.clear_dtc(group=0xFFFFFF)
        # Accept either success (some ECUs stay extended) or NRC 0x22
        if not resp.positive:
            assert resp.code in (
                udsoncan.NegativeResponseCode.conditionsNotCorrect,
                udsoncan.NegativeResponseCode.requestSequenceError,
            ), f"Unexpected NRC: {resp.code}"

    def test_programming_session_requires_security(self, uds_client):
        """Programming session should require SecurityAccess first (or fail gracefully)."""
        resp = uds_client.change_session(
            udsoncan.DiagnosticSessionControl.Session.programmingSession
        )
        # May succeed or return NRC 0x22 (conditions not correct)
        if not resp.positive:
            assert resp.code == \
                udsoncan.NegativeResponseCode.conditionsNotCorrect


class TestReadData:

    def test_read_vin(self, uds_client):
        """Read Vehicle Identification Number — DID 0xF190."""
        resp = uds_client.read_data_by_identifier(0xF190)
        assert resp.positive, f"Read VIN failed: {resp.code}"
        vin = resp.service_data.values[0xF190]
        assert len(vin) == 17, f"VIN length should be 17, got {len(vin)}"
        assert vin.isascii(), "VIN contains non-ASCII characters"

    def test_read_ecuid_sw_version(self, uds_client):
        """Read ECU Software Version — DID 0xF189."""
        resp = uds_client.read_data_by_identifier(0xF189)
        assert resp.positive or \
               resp.code == udsoncan.NegativeResponseCode.requestOutOfRange

    def test_read_invalid_did(self, uds_client):
        """Reading an unsupported DID must return NRC 0x31 (requestOutOfRange)."""
        resp = uds_client.read_data_by_identifier(0x0001)  # invalid DID
        assert not resp.positive
        assert resp.code == udsoncan.NegativeResponseCode.requestOutOfRange, \
               f"Expected NRC 0x31, got {resp.code}"


class TestDTC:

    def test_clear_dtcs(self, uds_client):
        """Clear all DTCs in Extended session."""
        uds_client.change_session(
            udsoncan.DiagnosticSessionControl.Session.extendedDiagnosticSession
        )
        resp = uds_client.clear_dtc(group=0xFFFFFF)
        assert resp.positive, f"Clear DTC failed: {resp.code}"

    def test_read_dtc_after_clear(self, uds_client):
        """After clearing, no DTCs should be present."""
        uds_client.change_session(
            udsoncan.DiagnosticSessionControl.Session.extendedDiagnosticSession
        )
        uds_client.clear_dtc(group=0xFFFFFF)
        resp = uds_client.get_dtc_by_status_mask(0xFF)
        assert resp.positive
        assert len(resp.service_data.dtcs) == 0, \
               f"Expected 0 DTCs, found {len(resp.service_data.dtcs)}"

    def test_dtc_stored_after_fault(self, uds_client, hil_interface):
        """Inject fault → verify DTC stored → clear → verify gone."""
        # 1. Clear all DTCs
        uds_client.change_session(
            udsoncan.DiagnosticSessionControl.Session.extendedDiagnosticSession
        )
        uds_client.clear_dtc(group=0xFFFFFF)

        # 2. Inject fault via HIL (short throttle sensor to GND)
        hil_interface.inject_fault("TPS_Short_GND", duration_ms=500)
        time.sleep(1.0)  # wait for ECU to detect and store DTC

        # 3. Read DTCs — expect TPS DTC present
        resp = uds_client.get_dtc_by_status_mask(0x01)  # testFailed bit
        dtc_numbers = [dtc.dtc_number for dtc in resp.service_data.dtcs]
        assert 0x012345 in dtc_numbers, \
               f"TPS DTC not stored. Found DTCs: {dtc_numbers}"

        # 4. Clear and verify gone
        uds_client.clear_dtc(group=0xFFFFFF)
        resp = uds_client.get_dtc_by_status_mask(0xFF)
        assert len(resp.service_data.dtcs) == 0


class TestSecurityAccess:

    def test_security_access_level1(self, uds_client):
        """Verify seed-key security access for level 0x01."""
        uds_client.change_session(
            udsoncan.DiagnosticSessionControl.Session.extendedDiagnosticSession
        )
        # Request seed
        resp = uds_client.request_seed(0x01)
        assert resp.positive, f"Seed request failed: {resp.code}"
        seed = resp.service_data.seed

        # Calculate key (algorithm is ECU-specific — example XOR key)
        key = seed ^ 0xDEADBEEF  # replace with actual algorithm

        # Send key
        resp = uds_client.send_key(0x01, key)
        assert resp.positive, f"Key rejected: {resp.code} (wrong algorithm?)"

    def test_security_access_wrong_key_locked_out(self, uds_client):
        """Sending wrong key 3 times should lock out further attempts."""
        uds_client.change_session(
            udsoncan.DiagnosticSessionControl.Session.extendedDiagnosticSession
        )
        for attempt in range(3):
            resp = uds_client.request_seed(0x01)
            if not resp.positive:
                break
            resp = uds_client.send_key(0x01, 0xFFFFFFFF)  # wrong key always
            if resp.positive:
                return  # ECU accepted wrong key — test fails expectation

        # After 3 failures, further seed request should return NRC 0x36 (exceededNumberOfAttempts)
        resp = uds_client.request_seed(0x01)
        if not resp.positive:
            assert resp.code in (
                udsoncan.NegativeResponseCode.exceededNumberOfAttempts,
                udsoncan.NegativeResponseCode.requestSequenceError,
            )
```

### 7.3 DTC Status Byte — Understanding All 8 Bits

```
DTC Status Byte (1 byte, 8 flags):
  Bit 7: warningIndicatorRequested  — MIL / warning light should be on
  Bit 6: testNotCompletedThisMonitoringCycle  — ECU has not run the test yet
  Bit 5: testFailedSinceLastClear  — has failed at least once since last clear
  Bit 4: testNotCompletedSinceLastClear  — test not run since last clear
  Bit 3: confirmedDTC  — failed in 2 consecutive drive cycles (confirmed)
  Bit 2: pendingDTC  — failed in current drive cycle but not yet confirmed
  Bit 1: testFailed  — currently failing RIGHT NOW
  Bit 0: testFailed  (same as bit 1 in many implementations — check spec)

Common status masks to use:
  0x01 — currently active faults (testFailed)
  0x09 — active or confirmed faults
  0xFF — all DTCs in any state
```

---

## 8. CAN Bus Testing with CANoe and CAPL

### 8.1 What is CAPL?

CAPL (Communication Access Programming Language) is a C-like scripting language embedded in Vector CANoe/CANalyzer. It runs inside the simulation and can:
- Send and receive CAN messages
- React to signals and events
- Automate test sequences
- Write test verdict (pass/fail) to a test report

### 8.2 CAPL Test Node — Structure

```capl
/*
 * CAN Test Node: Engine Speed Signal Validation
 * Tool: Vector CANoe
 * Bus: Powertrain CAN @ 500 kbps
 */

variables {
    message EngineStatus  msg_engine;      /* from DBC file */
    mstimer t_timeout;
    float   g_last_engine_speed;
    int     g_test_running;
}

/* ── Test: Engine speed in valid range ─────────────────────────────── */
testcase TC_EngineSpeed_ValidRange() {
    float speed;
    float SPEED_MIN = 0.0;
    float SPEED_MAX = 8000.0;  /* RPM */
    int   test_duration_ms = 5000;
    int   samples = 0;
    int   violations = 0;

    testStep("", "Start engine speed range test for 5 seconds");

    /* Sample for 5 seconds */
    long start_time = timeNow();
    while ((timeNow() - start_time) < test_duration_ms * 1000) {  /* timeNow in µs */
        speed = @EngineStatus::EngineSpeed;   /* read signal via @ operator */
        if (speed < SPEED_MIN || speed > SPEED_MAX) {
            violations++;
            write("VIOLATION: EngineSpeed=%.1f RPM at t=%d ms", speed,
                  (timeNow() - start_time) / 1000);
        }
        samples++;
        testWaitForTimeout(100);   /* check every 100 ms */
    }

    if (violations == 0) {
        testStepPass("EngineSpeed", "All %d samples within range [%.0f, %.0f] RPM",
                     samples, SPEED_MIN, SPEED_MAX);
    } else {
        testStepFail("EngineSpeed", "%d violations found in %d samples",
                     violations, samples);
    }
}

/* ── Test: Message periodicity ──────────────────────────────────────── */
testcase TC_EngineStatus_Periodicity() {
    long  last_rx_time = 0;
    long  current_time;
    long  delta_ms;
    long  PERIOD_NOMINAL_MS = 10;   /* 10 ms cycle time from DBC */
    long  PERIOD_TOLERANCE  = 2;    /* ±2 ms tolerance */
    int   violations = 0;
    int   count = 0;

    testStep("", "Verify EngineStatus message period is 10 ms ± 2 ms");

    /* Wait for first message */
    testWaitForMessage(EngineStatus, 200);   /* wait up to 200 ms */
    last_rx_time = timeNow();

    /* Check 20 consecutive periods */
    while (count < 20) {
        testWaitForMessage(EngineStatus, 200);
        current_time = timeNow();
        delta_ms = (current_time - last_rx_time) / 1000;  /* µs to ms */

        if (delta_ms < (PERIOD_NOMINAL_MS - PERIOD_TOLERANCE) ||
            delta_ms > (PERIOD_NOMINAL_MS + PERIOD_TOLERANCE)) {
            violations++;
            write("Period violation: %d ms (expected %d±%d ms)",
                  delta_ms, PERIOD_NOMINAL_MS, PERIOD_TOLERANCE);
        }
        last_rx_time = current_time;
        count++;
    }

    if (violations == 0) {
        testStepPass("Periodicity", "All 20 periods within %d±%d ms",
                     PERIOD_NOMINAL_MS, PERIOD_TOLERANCE);
    } else {
        testStepFail("Periodicity", "%d period violations", violations);
    }
}

/* ── Test: Engine speed signal scaling ─────────────────────────────── */
testcase TC_EngineSpeed_Scaling() {
    /* Force a known raw value via a simulation variable, check the decoded signal */
    float expected_speed = 3000.0;   /* RPM */
    float actual_speed;

    /* Inject raw CAN value: speed = 3000 RPM, factor=0.25, offset=0
       raw = (3000 - 0) / 0.25 = 12000 = 0x2EE0 */
    msg_engine.EngineSpeed = (int)(expected_speed / 0.25);
    output(msg_engine);

    testWaitForTimeout(50);   /* let signal settle */

    actual_speed = @EngineStatus::EngineSpeed;

    if (abs(actual_speed - expected_speed) < 1.0) {
        testStepPass("Scaling", "EngineSpeed correctly decoded as %.1f RPM",
                     actual_speed);
    } else {
        testStepFail("Scaling", "Expected %.1f RPM, got %.1f RPM",
                     expected_speed, actual_speed);
    }
}

/* ── Test suite runner ───────────────────────────────────────────────── */
maintest TestSuite_EngineSignals() {
    testModuleTitle("Engine CAN Signal Validation");
    testGroupBegin("EngineStatus Signal Tests", "Group 1");
    TC_EngineSpeed_ValidRange();
    TC_EngineStatus_Periodicity();
    TC_EngineSpeed_Scaling();
    testGroupEnd();
    testModuleTitle("Finished");
}
```

### 8.3 Common CAN Signal Tests Every ECU Tester Writes

```
1. Signal range test
   → All signal values remain within [min, max] during normal operation

2. Signal periodicity test
   → Cyclic messages arrive at declared cycle time ± tolerance (typically ±5ms or ±10%)

3. Signal default value test
   → On power-on, signal initialises to correct default (not 0 for temperature, etc.)

4. Signal response to input test
   → When HIL injects sensor input X, CAN output Y changes accordingly

5. Signal resolution / scaling test
   → Raw value decoded using DBC factor/offset matches expected physical value

6. Bus-off recovery test
   → After induced bus-off, CanSM recovers within spec time

7. Missing message handling test
   → When a critical message stops, ECU enters fallback/limp-home mode

8. Signal SNA (Signal Not Available) test
   → When sending SNA value (defined in DBC), ECU handles gracefully

9. Counter and checksum test
   → Alive counter increments each cycle; CRC/checksum covers correct bytes

10. Timeout test
    → ECU detects missing message within timeout period and sets DTC
```

---

## 9. Requirement-Based Testing and Traceability

### 9.1 Types of Requirements in Automotive SW

```
LEVEL 1: Customer / Vehicle Requirements
  "The ABS system shall prevent wheel lock-up during braking on wet roads"

LEVEL 2: System Requirements
  "The ABS ECU shall reduce brake pressure within 50 ms of wheel lock detection"

LEVEL 3: Software Requirements (SRS)
  SRS-ABS-047: The ABS_Control function shall set BrakePressureRequest to
               REDUCE when WheelSpeedDelta exceeds 5 km/h for more than 10 ms

LEVEL 4: Software Architecture
  "ABS_Control SWC receives WheelSpeed from sensor SWC via RTE port"

LEVEL 5: Detailed Design
  "if (delta_speed > 5.0f && timer_ms > 10U) { pressure_req = REDUCE; }"

LEVEL 6: Code
  Actual C implementation

TEST CASES trace back to Level 3 (SRS):
  TC-ABS-047 tests SRS-ABS-047
```

### 9.2 Traceability Matrix — Example

```
┌──────────────┬────────────────────────────────────┬───────────────────────┐
│ Requirement  │ Description (brief)                │ Test Case(s)          │
├──────────────┼────────────────────────────────────┼───────────────────────┤
│ SRS-ABS-040  │ Detect wheel lock in < 10 ms       │ TC-ABS-040-01,02      │
│ SRS-ABS-041  │ Reduce brake pressure on lock      │ TC-ABS-041-01         │
│ SRS-ABS-042  │ Release fully when speed recovered │ TC-ABS-042-01,02      │
│ SRS-ABS-043  │ Max 3 pressure cycles/second       │ TC-ABS-043-01         │
│ SRS-ABS-044  │ DTC set on sensor fault            │ TC-ABS-044-01,02,03   │
│ SRS-ABS-045  │ Limp home: ABS off, brakes normal  │ TC-ABS-045-01         │
│ SRS-ABS-046  │ Warning lamp on ABS fault          │ TC-ABS-046-01         │
│ SRS-ABS-047  │ Pressure reduce within 50 ms       │ TC-ABS-047-01 (timing)│
│ SRS-ABS-048  │ OBD-II DTC format for ABS faults   │ TC-ABS-048-01,02      │
└──────────────┴────────────────────────────────────┴───────────────────────┘

Coverage = (Requirements with ≥1 test) / (Total requirements) × 100
Target: 100% requirement coverage before production release
```

### 9.3 Tools for Requirement Traceability

| Tool | Use | Note |
|---|---|---|
| DOORS / DOORS Next | Requirements management | IBM product, industry standard |
| Polarion | Requirements + test management | Siemens, widely used |
| Jama Connect | Modern requirements tool | Web-based |
| JIRA + Xray | Issue + test management | Common in Agile automotive |
| Excel | Simple traceability matrix | Acceptable for small projects |
| Python script | Auto-generate from DOORS export | Custom automation |

---

## 10. Fault Injection and Negative Testing

### 10.1 Why Fault Injection is Critical

> In automotive, your ECU must behave safely even when things go wrong. A temperature sensor that gets disconnected, a CAN bus with noise, a power supply that drops to 9V — all of these must not cause unsafe vehicle behaviour. Testing the fault response is mandatory for ISO 26262 compliance.

### 10.2 Types of Faults to Inject

```
ELECTRICAL FAULTS
  Short to GND     — sensor wire connects to chassis ground
  Short to VCC     — sensor wire connects to battery positive
  Open circuit     — wire disconnected (broken harness)
  Short between wires — two adjacent wires touch
  Out of range     — sensor voltage outside ADC range

CAN BUS FAULTS
  Bus-off          — ECU stops communicating after error saturation
  Dominant stuck   — CAN_H permanently dominant (blocks all traffic)
  Missing message  — expected message stops arriving
  Wrong DLC        — message with unexpected data length
  CRC error        — message with corrupted checksum
  Babbling idiot   — node transmitting at wrong rate, flooding bus

POWER SUPPLY FAULTS
  Undervoltage     — battery drops to 6V during cranking
  Overvoltage      — load dump: 40V spike when alternator disconnected
  Power interrupt  — brief power loss (< 50 ms)

SOFTWARE / PROTOCOL FAULTS
  Invalid UDS service ID
  Request in wrong session
  Wrong sequence (skip required step)
  Buffer overflow attempt (max payload tests)
```

### 10.3 Fault Injection via Python

```python
"""
Hardware Fault Injection via HIL relay board
Uses a relay matrix connected to sensor wires
"""
import serial
import time


class FaultInjector:
    """Controls a relay board for hardware fault injection."""

    FAULT_SHORT_GND = 0x01
    FAULT_SHORT_VCC = 0x02
    FAULT_OPEN_CIRCUIT = 0x03
    FAULT_NONE = 0x00

    CHANNEL_TPS  = 1    # Throttle Position Sensor
    CHANNEL_CTS  = 2    # Coolant Temperature Sensor
    CHANNEL_IAT  = 3    # Intake Air Temperature Sensor
    CHANNEL_MAP  = 4    # Manifold Absolute Pressure Sensor

    def __init__(self, port: str = "COM5", baud: int = 115200):
        self.ser = serial.Serial(port, baud, timeout=1.0)
        time.sleep(0.5)

    def inject(self, channel: int, fault_type: int, duration_ms: int = 0):
        """
        Inject a fault on a sensor channel.
        duration_ms=0 means permanent (until clear_fault is called).
        """
        cmd = f"FAULT {channel} {fault_type} {duration_ms}\n"
        self.ser.write(cmd.encode())
        resp = self.ser.readline().decode().strip()
        assert resp == "OK", f"Fault injection failed: {resp}"

    def clear_fault(self, channel: int):
        """Remove injected fault — restore normal wiring."""
        self.inject(channel, self.FAULT_NONE)

    def inject_can_bus_off(self, can_channel: int = 0):
        """Force CAN bus into bus-off by injecting errors."""
        cmd = f"CAN_BUSOFF {can_channel}\n"
        self.ser.write(cmd.encode())

    def __enter__(self): return self
    def __exit__(self, *args): self.ser.close()


# ── Test using fault injector ─────────────────────────────────────────

def test_tps_short_gnd_sets_dtc(uds_client, fault_injector):
    """
    Scenario: TPS sensor wire shorts to GND.
    Expected: ECU detects fault, stores DTC, enters limp-home mode.
    """
    # Clear any pre-existing DTCs
    uds_client.change_session(
        udsoncan.DiagnosticSessionControl.Session.extendedDiagnosticSession
    )
    uds_client.clear_dtc(group=0xFFFFFF)

    # Inject fault
    fault_injector.inject(
        FaultInjector.CHANNEL_TPS,
        FaultInjector.FAULT_SHORT_GND,
        duration_ms=2000
    )

    # Allow time for ECU to detect (typically 2-3 monitor cycles = ~200 ms)
    time.sleep(0.5)

    # Verify DTC stored
    resp = uds_client.get_dtc_by_status_mask(0x01)
    dtc_list = [dtc.dtc_number for dtc in resp.service_data.dtcs]
    assert 0xP0120 in dtc_list, f"TPS DTC not stored. Active DTCs: {dtc_list}"

    # Verify limp-home via CAN signal (engine limited to 2000 RPM)
    # This would read from HIL's CAN bus monitor
    # engine_limit = hil.read_signal("EngineStatus", "EngineSpeed")
    # assert engine_limit <= 2000.0

    # Remove fault and verify recovery
    fault_injector.clear_fault(FaultInjector.CHANNEL_TPS)
    time.sleep(0.5)

    # DTC should now be "stored but not active" (bit 1 = 0, bit 3 = 1)
    resp = uds_client.get_dtc_by_status_mask(0x01)  # testFailed
    dtc_list = [dtc.dtc_number for dtc in resp.service_data.dtcs]
    assert 0xP0120 not in dtc_list, "TPS DTC still active after fault removed"
```

---

## 11. Automated ECU Test Frameworks — Python

### 11.1 Framework Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  AUTOMATED ECU TEST FRAMEWORK                                           │
│                                                                         │
│  test_runner.py (pytest)                                                │
│       │                                                                 │
│       ├── conftest.py (fixtures: uds_client, can_bus, hil_interface)   │
│       │                                                                 │
│       ├── tests/
│       │     ├── test_session_management.py                             │
│       │     ├── test_dtc_handling.py                                   │
│       │     ├── test_signal_range.py                                   │
│       │     ├── test_fault_injection.py                                │
│       │     └── test_flashing.py                                       │
│       │                                                                 │
│       ├── adapters/
│       │     ├── uds_adapter.py   ← wraps udsoncan                      │
│       │     ├── can_adapter.py   ← wraps python-can                    │
│       │     └── hil_adapter.py   ← wraps dSPACE COM API                │
│       │                                                                 │
│       └── reporting/
│             ├── junit_report.py  ← for Jenkins CI                      │
│             └── html_report.py   ← human-readable                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 11.2 conftest.py — Test Fixtures

```python
"""conftest.py — pytest fixtures for ECU test automation"""
import pytest
import can
import isotp
import udsoncan
from udsoncan.client import Client
from udsoncan.connections import PythonIsoTpConnection


@pytest.fixture(scope="session")
def can_bus():
    """CAN bus connection — shared across all tests in session."""
    bus = can.interface.Bus(
        interface="vector",
        channel=0,
        bitrate=500000,
        app_name="ECU_Test",
    )
    yield bus
    bus.shutdown()


@pytest.fixture(scope="function")
def uds_client(can_bus):
    """Fresh UDS client for each test function."""
    tp_addr = isotp.Address(
        isotp.AddressingMode.Normal_11bits,
        txid=0x7E0,
        rxid=0x7E8,
    )
    conn = PythonIsoTpConnection(can_bus, tp_addr)
    config = {
        "exception_on_negative_response": False,
        "p2_timeout": 0.15,
        "p2_star_timeout": 5.0,
        "security_algo": compute_key,     # your key algorithm
        "security_algo_params": None,
    }
    with Client(conn, config=config) as client:
        # Ensure we start in Default session
        client.change_session(
            udsoncan.DiagnosticSessionControl.Session.defaultSession
        )
        yield client


@pytest.fixture(scope="function", autouse=True)
def clear_dtcs_before_test(uds_client):
    """Auto-run before each test: clear DTCs for a clean state."""
    uds_client.change_session(
        udsoncan.DiagnosticSessionControl.Session.extendedDiagnosticSession
    )
    uds_client.clear_dtc(group=0xFFFFFF)
    uds_client.change_session(
        udsoncan.DiagnosticSessionControl.Session.defaultSession
    )
    yield


def compute_key(seed: bytes, params) -> bytes:
    """
    Security access key calculation.
    Replace with actual algorithm from ECU spec (NDA-protected).
    Example: XOR with constant.
    """
    seed_int = int.from_bytes(seed, "big")
    key_int  = seed_int ^ 0xDEADBEEF
    return key_int.to_bytes(len(seed), "big")
```

### 11.3 pytest.ini — Test Configuration

```ini
[pytest]
testpaths = tests
addopts = -v --tb=short --junit-xml=reports/results.xml

markers =
    unit: Unit tests (no hardware needed)
    integration: SIL integration tests
    hil: HIL tests (requires hardware setup)
    regression: Regression suite
    diagnostic: UDS diagnostic tests
    can: CAN bus signal tests
    fault_injection: Fault injection tests
    slow: Tests taking > 30 seconds

filterwarnings =
    ignore::DeprecationWarning:can.*
```

### 11.4 Running the Test Suite

```bash
# Run all tests
pytest tests/ -v

# Run only diagnostic tests (no hardware)
pytest tests/ -m "diagnostic" -v

# Run HIL tests on specific ECU version
pytest tests/ -m "hil" --ecu-version="SW_1.2.3" -v

# Run with detailed failure report
pytest tests/ --tb=long --html=reports/report.html

# Run in CI — stop on first failure, XML output
pytest tests/ -m "regression" -x --junit-xml=results.xml

# Check specific test case by ID
pytest tests/ -k "TC_ECU_DTC_001" -v
```

---

## 12. ISO 26262 Functional Safety Testing

### 12.1 What ISO 26262 Means for Testers

ISO 26262 is the automotive functional safety standard. As a tester, it affects you because:

```
1. You must test safety mechanisms — the code that prevents hazards
2. Your tests must have full requirement traceability
3. Your test environment must be qualified (tool qualification)
4. Test results must be documented and auditable
5. Coverage requirements are higher for ASIL-D than for ASIL-A
```

### 12.2 ASIL Levels

```
ASIL = Automotive Safety Integrity Level

ASIL D — Highest (risk: injury or death)
  Examples: brake control, steering, airbag deployment
  Testing: 100% MC/DC coverage, formal review, independence

ASIL C — High
  Examples: ABS, ESC, EPS torque control
  Testing: 100% branch coverage, peer review

ASIL B — Medium
  Examples: engine torque limitation, transmission control
  Testing: full branch coverage, structural coverage

ASIL A — Lower
  Examples: instrument cluster, HVAC with safety aspects
  Testing: statement coverage

QM — Quality Management (no safety requirement)
  Examples: infotainment, seat adjustment, mirror control
  Testing: standard software quality processes
```

### 12.3 Safety Mechanism Testing

```python
"""Test safety mechanisms required by ISO 26262"""

class TestSafetyMechanisms:

    def test_watchdog_reset_on_task_overrun(self, ecu):
        """
        Safety Mechanism: Hardware watchdog resets ECU if software hangs.
        This is a hardware-level test — requires oscilloscope or reset GPIO.
        """
        # Stimulate a software hang (test mode command — supplier-specific)
        ecu.trigger_software_hang_test_mode()

        # Expect ECU to reset within watchdog timeout (typically 10-100 ms)
        reset_detected = ecu.wait_for_reset(timeout_ms=200)
        assert reset_detected, "Watchdog did not reset ECU after software hang"

        # Verify ECU recovered cleanly
        time.sleep(2.0)
        resp = ecu.uds_client.change_session(
            udsoncan.DiagnosticSessionControl.Session.defaultSession
        )
        assert resp.positive, "ECU did not recover from watchdog reset"

    def test_output_limited_on_sensor_fault(self, ecu, fault_injector):
        """
        Safety Mechanism: On sensor fault, output must be limited to safe range.
        ASIL-B requirement: system must not produce unsafe torque if TPS fails.
        """
        # Inject TPS fault
        fault_injector.inject(FaultInjector.CHANNEL_TPS,
                               FaultInjector.FAULT_OPEN_CIRCUIT)
        time.sleep(0.3)

        # Read engine torque request from CAN
        torque_request = ecu.can.read_signal("EngineControl", "TorqueRequest")

        # Must not exceed safe limit (e.g., idle torque only)
        assert torque_request <= SAFE_TORQUE_LIMIT, \
               f"Unsafe torque {torque_request} Nm on sensor fault"

        fault_injector.clear_fault(FaultInjector.CHANNEL_TPS)

    def test_ram_test_passes_on_startup(self, ecu):
        """
        Safety Mechanism: BIST (Built-In Self-Test) tests RAM on startup.
        If RAM test fails, ECU must not allow normal operation.
        """
        # Read the BIST result DID (supplier-specific DID)
        resp = ecu.uds_client.read_data_by_identifier(0xFD01)  # BIST result DID
        assert resp.positive
        bist_result = resp.service_data.values[0xFD01]
        assert bist_result[0] == 0x01, \
               f"BIST failed: result=0x{bist_result[0]:02X}"
```

---

## 13. Debugging ECU Failures — Tools and Techniques

### 13.1 Your Debug Toolkit

```
Tool             | What it shows                    | When to use
─────────────────┬──────────────────────────────────┬─────────────────────
CANalyzer        │ All CAN traffic, signal decode   │ Always — first tool
Oscilloscope     │ Waveforms, timing, signal quality│ Signal integrity issues
Logic Analyser   │ Digital protocol decode (SPI,I2C)│ Peripheral debug
JTAG Debugger    │ CPU state, registers, breakpoints│ Software crash debug
Serial terminal  │ printf debug output from ECU     │ Development firmware
Lauterbach TRACE32│ CPU trace, code coverage on HW  │ Deep software debug
INCA / ETAS      │ ECU calibration data read/write  │ Parameter tuning
PCAN-View        │ Free CAN monitor (no DBC decode) │ Quick CAN check
```

### 13.2 Root Cause Analysis Workflow

```
Problem report received:
  "ABS warning lamp illuminates intermittently during normal braking"

Step 1: Reproduce the issue
  → Set up HIL with braking scenario
  → Run 50 braking cycles
  → 3 cases with ABS lamp: confirmed reproducible

Step 2: Gather data
  → CANoe logging during failing cycle
  → Check: ABS DTC stored? Which DTC? What status byte?
  → Check: Wheel speed signals during failure cycle
  → Check: Brake pressure signal timing

Step 3: Narrow the scope
  → DTC P0123 — "Wheel Speed Sensor FL Signal Intermittent"
  → Waveform: WheelSpeed_FL drops to 0 for 8 ms during braking
  → 8 ms > ABS debounce time (5 ms) → DTC triggers

Step 4: Determine root cause
  → Physical check: FL wheel speed sensor connector loose
  → Connector vibration at high brake deceleration causes momentary loss
  → Not an ECU firmware bug — harness/sensor issue

Step 5: Corrective action
  → Hardware: connector clip replacement (harness team)
  → Software: review debounce time — 5 ms may be too sensitive?
  → Test: verify with new connector over 200 braking cycles

Step 6: Documentation
  → JIRA ticket updated with root cause and resolution
  → Test case added to regression: "TC-ABS-050: Connector bounce immunity test"
```

### 13.3 Reading a CAN Trace — What to Look For

```
In CANalyzer / CANoe trace window:
  Column: Time | ID  | Dlc | Data                    | Sig decode

  0.000  | 100 | 8   | 00 00 00 00 00 00 00 00 | EngineSpeed=0 RPM
  0.010  | 100 | 8   | 00 00 00 00 00 00 00 00 | EngineSpeed=0 RPM
  0.020  | 100 | 8   | 84 0C 28 00 01 00 00 00 | EngineSpeed=812 RPM  ← jump?
  ...
  5.000  | 100 | 8   | E0 27 64 14 01 00 00 00 | EngineSpeed=2552 RPM
  5.010  |     |     |                          |  ← MESSAGE MISSING!
  5.020  |     |     |                          |  ← MISSING AGAIN
  5.030  | 100 | 8   | E0 27 64 14 01 00 00 00 | EngineSpeed=2552 RPM

Red flags to look for:
  ✗ Message period much longer than DBC specification
  ✗ Message completely missing for > 2 cycles
  ✗ DLC different from DBC definition
  ✗ CRC/counter value incorrect
  ✗ Signal value outside physical range
  ✗ Signal stuck at one value for > 1 second (sensor frozen)
  ✗ Signal toggling between two values rapidly (noise / fault)
  ✗ Error frames visible in trace (red highlight in CANoe)
  ✗ Bus-off event (ECU disappears from bus)
```

---

## 14. Real Work Scenarios and Walkthroughs

### 14.1 Scenario: New ECU Software Version Released — Run Regression

```
Context: Engine Control Module (ECM) SW updated from v1.2 to v1.3.
         Change: Idle speed control algorithm tuned.
         Your job: Run regression tests, report pass/fail.

Step 1: Flash ECU with new SW version v1.3
  Tool: ETAS Flash Tool / CANoe Flashing CAPL
  Command: flash_ecu("ECM_SW_v1.3.hex")
  Verify: Read DID 0xF189 (SW version), confirm "1.3"

Step 2: Run automated regression suite
  Command: pytest tests/ -m "regression" -v --junit-xml=v1.3_regression.xml
  Duration: ~45 minutes

Step 3: Review results
  Passed: 87 / 90 tests
  Failed: 3 tests:
    TC-ECM-031: Idle speed at hot soak — measured 820 RPM, expected 750 RPM
    TC-ECM-045: Idle speed recovery after A/C engage — 200 ms slower than spec
    TC-ECM-067: Fuel trim at idle — outside ±5% tolerance

Step 4: File JIRA tickets for failures
  BUG-ECM-0234: Idle speed 70 RPM too high after hot soak [v1.3]
  BUG-ECM-0235: A/C idle recovery 200 ms slow [v1.3]
  BUG-ECM-0236: Fuel trim out of tolerance at idle [v1.3]

Step 5: Write regression report
  Software version: ECM_SW_v1.3
  Test date: 2026-05-05
  Total tests: 90
  Passed: 87 (96.7%)
  Failed: 3 (3.3%)
  Verdict: FAIL — must fix before production release
  Critical failures: 0 (no safety-critical tests failed)
  Regression compared to v1.2: 3 new failures introduced
```

### 14.2 Scenario: CAN Signal Missing — Debugging Live

```
Bug report: "Instrument cluster shows '---' instead of fuel level"

Investigation:
  1. Connect CANalyzer to Instrument Cluster CAN bus
  2. Open DBC file, look for FuelLevel signal
     → Found: BO_ 420 FuelDisplay: 8 BCM
                SG_ FuelLevel : 0|8@1+ (0.5,0) [0|100] "%" ICM

  3. Monitor message 0x1A4 (420 dec) on bus
     → Not seen in trace! Message is completely missing.

  4. Check the sender: BCM (Body Control Module)
     → Connect to BCM CAN bus: message IS present on BCM bus
     → Conclusion: Gateway ECU not routing BCM → ICM

  5. Check gateway routing table
     → Open gateway configuration in DOORS
     → Route 0x1A4 BCM→ICM: ENABLED in config
     → But! Filter condition: FuelLevel > 5% (suppressed if tank very low?)
     → Check actual fuel level: tank is empty (test vehicle not fuelled)
     → Gateway suppressing message at 0% fuel

  6. Root cause: Gateway filter logic incorrect — 
     should route even at 0% (cluster must show 'empty')
     
  7. Fix: Remove > 5% filter from gateway routing config
  8. Retest: Message now visible on ICM bus, cluster shows 'E'
  9. DTC check: No DTC — this was a routing configuration issue, not a fault
```

### 14.3 Scenario: Security Access Testing

```
Context: Before flashing new firmware, ECU requires security access.
         You need to validate the seed-key mechanism.

The protocol:
  1. Request seed:  7E0 02 27 01    (service 0x27, level 0x01)
  2. ECU responds:  7E8 06 67 01 A1 B2 C3 D4  (seed = A1B2C3D4)
  3. Calculate key: your algorithm (from ECU spec)
  4. Send key:      7E0 06 27 02 K1 K2 K3 K4
  5. ECU responds:  7E8 02 67 02    (positive = unlocked!)
               OR:  7E8 03 7F 27 35 (NRC 0x35 = invalid key)

Python test:
```

```python
def test_security_access_and_flash_session(uds_client):
    """Full security access flow to enter programming session."""

    # Step 1: Enter extended session
    resp = uds_client.change_session(
        udsoncan.DiagnosticSessionControl.Session.extendedDiagnosticSession
    )
    assert resp.positive

    # Step 2: Request seed for level 0x01
    resp = uds_client.request_seed(0x01)
    assert resp.positive, f"Seed request failed: NRC={resp.code}"
    seed_bytes = resp.service_data.seed
    print(f"Received seed: {seed_bytes.hex()}")

    # Step 3: Compute key using supplier algorithm
    key_bytes = compute_security_key(seed_bytes)
    print(f"Computed key:  {key_bytes.hex()}")

    # Step 4: Send key
    resp = uds_client.send_key(0x02, key_bytes)
    assert resp.positive, f"Key rejected! NRC={resp.code} (wrong algorithm?)"
    print("Security access granted!")

    # Step 5: Transition to programming session
    resp = uds_client.change_session(
        udsoncan.DiagnosticSessionControl.Session.programmingSession
    )
    assert resp.positive, f"Programming session rejected: NRC={resp.code}"
    print("Programming session active — ready to flash")
```

---

## 15. ECU Boot Sequence — Testing Startup and Shutdown

### 15.1 ECU Power-On Sequence

Understanding how an ECU boots is critical because many bugs appear only during startup or during power-down. The test engineer must know exactly what the ECU should do in the first 500 ms.

```
Timeline: ECU Power-On Sequence (typical Engine Control Module)

T=0 ms       : KL15 (ignition) switched ON — 12V applied to ECU
T=0–2 ms     : Voltage ramp-up, MCU comes out of reset
T=2–5 ms     : Boot ROM executes (chip vendor code):
               - Configure PLLs (set CPU clock frequency)
               - RAM ECC initialisation (clear all SRAM to 0x00)
               - Flash CRC check (verify firmware integrity)
               - Jump to application reset vector

T=5–20 ms    : AUTOSAR startup (EcuM — ECU Manager):
               - EcuM_Init() called
               - Os_Init() — AUTOSAR OS initialised
               - All BSW module Init called in order:
                 Det, SchM, Rte, Com, ComM, CanSM, NvM, Dem, Dcm, WdgM

T=20–50 ms   : Application SWCs initialise:
               - Default calibration values loaded from NvM
               - Sensor plausibility checks start
               - CAN communication starts (network management frames)

T=50–200 ms  : ECU "ready" state:
               - All CAN signals transmitting at correct rates
               - UDS diagnostic available in Default session
               - No initial DTCs (unless persistent faults from NvM)

T=200–500 ms : Full operational state:
               - Closed-loop control algorithms active
               - All monitors running
               - ECU broadcasts "ECU Status = Ready" on CAN
```

### 15.2 What to Test at Boot

```
TEST GROUP 1: CAN Bus Activity at Startup
  TC-BOOT-001  First CAN frame appears within 50 ms of power-on
  TC-BOOT-002  Network Management frames appear within 20 ms
  TC-BOOT-003  All cyclic messages transmitting within 200 ms
  TC-BOOT-004  No error frames during startup
  TC-BOOT-005  Message IDs and DLCs match DBC definition at first transmission

TEST GROUP 2: Signal Initialisation
  TC-BOOT-010  EngineSpeed = 0 RPM on startup (not garbage value)
  TC-BOOT-011  ThrottlePosition initialises to 0% (not previous power-cycle value)
  TC-BOOT-012  FaultActive signals = 0 on clean power-on (no false faults)
  TC-BOOT-013  NvM-backed calibration values load correctly (compare with INCA)

TEST GROUP 3: Diagnostic Availability
  TC-BOOT-020  UDS Default session available within 500 ms
  TC-BOOT-021  ReadDataByIdentifier 0xF186 (session type) returns 0x01 after boot
  TC-BOOT-022  No active DTCs after clean power-on (with no pre-existing faults)

TEST GROUP 4: Low Voltage at Startup (cranking scenario)
  TC-BOOT-030  ECU boots correctly when supply voltage drops to 8V during crank
  TC-BOOT-031  ECU does not reset during 9V sustained supply
  TC-BOOT-032  After voltage recovery to 12V, no spurious DTCs set

TEST GROUP 5: Power-Down (KL15 OFF)
  TC-BOOT-040  ECU completes NvM write-back within 500 ms of KL15 OFF
  TC-BOOT-041  No incomplete NvM blocks after immediate power cut
  TC-BOOT-042  After unexpected power cut (no KL15 OFF), ECU recovers cleanly
```

### 15.3 Boot Time Measurement with CAPL

```capl
/*
 * CAPL: Measure ECU boot time — from power-on to first CAN frame
 * Assumes HIL controls power supply via environment variable
 */
variables {
    msTimer t_boot_timeout;
    long    g_power_on_time;
    long    g_first_frame_time;
    int     g_boot_complete;
}

on envVar PowerSupply_Enable {
    if (getValue(PowerSupply_Enable) == 1) {
        g_power_on_time = timeNow() / 1000;   /* µs → ms */
        g_boot_complete = 0;
        write("Power-ON at %d ms", g_power_on_time);
        setTimer(t_boot_timeout, 2000);        /* 2 s overall timeout */
    }
}

on timer t_boot_timeout {
    if (!g_boot_complete) {
        write("FAIL: No CAN activity within 2000 ms of power-on");
        testStepFail("BootTime", "No CAN frame received within 2000 ms");
    }
}

on message * {
    if (!g_boot_complete) {
        g_first_frame_time = timeNow() / 1000;
        long boot_ms = g_first_frame_time - g_power_on_time;
        write("First CAN frame at %d ms (msg ID=0x%X)", boot_ms, this.id);

        if (boot_ms <= 50) {
            testStepPass("BootTime", "First frame at %d ms (spec: ≤50 ms)", boot_ms);
        } else {
            testStepFail("BootTime", "First frame at %d ms (spec: ≤50 ms)", boot_ms);
        }
        g_boot_complete = 1;
        cancelTimer(t_boot_timeout);
    }
}
```

### 15.4 Post-Reset DTC Behaviour Testing

A key thing to validate: after an ECU reset, which DTCs should survive and which should be cleared?

```
DTC Persistence Rules (per ISO 26262 / OEM specification):

PERSISTENT (survive reset and power cycle):
  - Confirmed DTCs (status bit 3 = 1)
  - Failed DTC history count (number of occurrences)
  - DTC snapshot / freeze frame data
  Storage: NvM (EEPROM-backed area)

NON-PERSISTENT (cleared on reset):
  - Pending DTCs (status bit 2 = 1, but bit 3 = 0)
  - Active testFailed (status bit 1 = 1)
  - In-memory only counters (not yet saved to NvM)

Test procedure:
  1. Inject fault → verify DTC pending (bit 2 = 1)
  2. Power cycle ECU
  3. Read DTC: pending bit should be 0 (not persisted)
  4. Inject fault for 2 consecutive drive cycles → confirmed (bit 3 = 1)
  5. Power cycle ECU
  6. Read DTC: confirmed bit should still be 1 (persisted via NvM)
```

---

## 16. AUTOSAR OS — Scheduling, Tasks, and Timing Tests

### 16.1 AUTOSAR OS Concepts for Testers

The AUTOSAR OS is a fixed-priority preemptive RTOS based on OSEK. Unlike Linux, all tasks and their scheduling are configured at compile time — you cannot create tasks at runtime.

```
Key Concepts:

TASK
  A function that runs periodically or is triggered by an event.
  Has a fixed priority (1 = lowest, 255 = highest on most platforms).
  Can be: BASIC (runs to completion) or EXTENDED (can wait for events).

  Example tasks in a typical ECM:
    OS_Task_1ms   (priority 10): Read sensors, update I/O
    OS_Task_5ms   (priority 8):  PID control algorithms
    OS_Task_10ms  (priority 6):  CAN signal sending
    OS_Task_20ms  (priority 4):  Diagnostics monitoring
    OS_Task_100ms (priority 2):  NvM operations
    OS_Task_1000ms(priority 1):  Temperature averaging, long-term monitors

ISR (Interrupt Service Routine)
  Category 1: Minimal ISR — no OS API calls, no context switch, < 1 µs
  Category 2: Full ISR — can activate tasks, set events

ALARM
  Triggers a task or sets an event on a cyclic or one-shot timer basis.

OsCounter
  Hardware timer that drives alarms. Typically the system tick (e.g., 1 ms).
```

### 16.2 Task Timing Testing

```python
"""
AUTOSAR OS Task Timing Validation via CAN trace
Tasks send CAN messages — we verify the timing of those messages
to confirm the OS is scheduling correctly.

Uses python-can + offline log analysis
"""
import can
import cantools
import statistics
from pathlib import Path
from typing import Dict, List


def measure_message_periodicity(
    log_file: str,
    dbc_file: str,
    message_name: str,
    expected_period_ms: float,
    tolerance_percent: float = 5.0,
) -> dict:
    """
    Analyse a CAN log file and verify a message's periodicity.

    Args:
        log_file:         Path to CANoe/Vector ASC or MF4 log
        dbc_file:         DBC file for decoding
        message_name:     Message name as in DBC (e.g., "EngineStatus")
        expected_period_ms: Expected cycle time in ms (from DBC comment)
        tolerance_percent:  Acceptable deviation ± %

    Returns:
        dict with statistics and pass/fail verdict
    """
    db = cantools.database.load_file(dbc_file)
    msg = db.get_message_by_name(message_name)

    # Load log (ASC format)
    timestamps: List[float] = []
    with open(log_file, "r") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 3:
                try:
                    ts = float(parts[0])
                    msg_id = int(parts[1], 16)
                    if msg_id == msg.frame_id:
                        timestamps.append(ts * 1000)  # s → ms
                except (ValueError, IndexError):
                    continue

    if len(timestamps) < 10:
        return {"verdict": "INCONCLUSIVE", "reason": f"Only {len(timestamps)} samples"}

    # Compute inter-arrival times
    periods = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
    mean_ms   = statistics.mean(periods)
    stdev_ms  = statistics.stdev(periods)
    min_ms    = min(periods)
    max_ms    = max(periods)

    tolerance_ms = expected_period_ms * (tolerance_percent / 100.0)
    lower = expected_period_ms - tolerance_ms
    upper = expected_period_ms + tolerance_ms

    violations = [p for p in periods if p < lower or p > upper]

    result = {
        "message":         message_name,
        "expected_ms":     expected_period_ms,
        "tolerance_ms":    tolerance_ms,
        "mean_ms":         round(mean_ms, 3),
        "stdev_ms":        round(stdev_ms, 3),
        "min_ms":          round(min_ms, 3),
        "max_ms":          round(max_ms, 3),
        "samples":         len(periods),
        "violations":      len(violations),
        "violation_pct":   round(len(violations) / len(periods) * 100, 1),
        "verdict":         "PASS" if len(violations) == 0 else "FAIL",
    }
    return result


# Example usage in pytest:
def test_engine_status_10ms_cycle(tmp_log_file, dbc_file):
    result = measure_message_periodicity(
        log_file=tmp_log_file,
        dbc_file=dbc_file,
        message_name="EngineStatus",
        expected_period_ms=10.0,
        tolerance_percent=5.0,
    )
    assert result["verdict"] == "PASS", (
        f"EngineStatus periodicity FAIL: "
        f"mean={result['mean_ms']} ms, "
        f"{result['violations']} violations out of {result['samples']}"
    )
```

### 16.3 Deadline Monitoring — Testing WdgM Behaviour

```
AUTOSAR WdgM (Watchdog Manager) supervised entity states:

  DEACTIVATED → EXPIRED → FAILED → STOPPED

Each SW component that uses the watchdog must call:
  WdgM_CheckpointReached(SWCID, CheckpointID)

at the right time in its execution.

If a checkpoint is missed (task overrun, infinite loop):
  WdgM detects → WdgM does NOT kick hardware watchdog → HW watchdog fires → MCU reset

How to test this:
  1. Identify which SWC/task has WdgM supervision
  2. Find the test mode routine (RoutineControl 0x31 to freeze a task — supplier-specific)
  3. Request the routine → ECU should reset within watchdog timeout
  4. Measure reset time vs. WdgM timeout spec value
  5. Verify ECU recovers after reset and comes back online
```

---

## 17. CAN Error Handling — Bus-Off, TEC, REC Deep Dive

### 17.1 CAN Error Counters

Every CAN node maintains two counters:

```
TEC — Transmit Error Counter
  Increments by 8 on each transmission error
  Decrements by 1 on each successful transmission

REC — Receive Error Counter  
  Increments by 1 on each receive error
  Decrements by 1 on each successful reception

Node states based on counters:
  ERROR ACTIVE:   TEC < 128 and REC < 128  (normal operation)
  ERROR PASSIVE:  TEC ≥ 128 or  REC ≥ 128  (sends passive error flags only)
  BUS-OFF:        TEC ≥ 256               (node stops transmitting, stops receiving)

Bus-Off Recovery:
  After bus-off, node waits for 128 × 11 recessive bits
  Then re-joins the bus in ERROR ACTIVE state
  AUTOSAR CanSM handles this automatically
  Recovery time: ~1.4 ms at 1 Mbps, ~11 ms at 125 kbps
```

### 17.2 Testing Bus-Off Recovery

```python
"""
Test CAN bus-off recovery using python-can error injection.
Requires a CAN interface that supports error frame injection
(e.g., Peak PCAN-USB Pro FD or Vector hardware with error injection).
"""
import can
import time
import pytest


class BusOffTest:
    """Tests for AUTOSAR CanSM bus-off recovery behaviour."""

    def __init__(self, test_bus: can.BusABC, monitor_bus: can.BusABC):
        # test_bus: interface that injects errors
        # monitor_bus: separate monitor to observe ECU behaviour
        self.test_bus   = test_bus
        self.monitor    = monitor_bus

    def inject_bus_off_condition(self) -> None:
        """
        Force bus-off by sending 32 error frames rapidly.
        This drives TEC above 256 on the target ECU.
        NOTE: Actual implementation depends on HW capabilities.
        """
        for _ in range(32):
            # Send dominant bit at wrong time (form error injection)
            err_frame = can.Message(
                arbitration_id=0x000,
                data=[0xFF] * 8,
                is_error_frame=True,
            )
            self.test_bus.send(err_frame)

    def wait_for_message(self, msg_id: int, timeout_s: float) -> bool:
        """Wait for a specific message ID on the monitor bus."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            msg = self.monitor.recv(timeout=0.01)
            if msg and msg.arbitration_id == msg_id:
                return True
        return False

    def test_bus_off_recovery(self):
        """
        1. Verify ECU is transmitting normally
        2. Inject bus-off condition
        3. Verify ECU messages stop (bus-off achieved)
        4. Verify ECU recovers and resumes transmission within spec
        """
        ECU_MSG_ID    = 0x100          # EngineStatus message
        RECOVERY_SPEC = 0.150          # 150 ms max recovery time per SRS

        # Pre-condition: ECU transmitting
        assert self.wait_for_message(ECU_MSG_ID, 0.5), \
            "PRECONDITION FAIL: ECU not transmitting before test"

        # Inject bus-off
        self.inject_bus_off_condition()
        bus_off_time = time.monotonic()

        # Verify bus goes quiet (ECU stops transmitting)
        time.sleep(0.050)  # wait 50 ms

        # Wait for recovery
        recovered = self.wait_for_message(ECU_MSG_ID, RECOVERY_SPEC + 0.5)
        recovery_time = time.monotonic() - bus_off_time

        assert recovered, \
            f"ECU did not recover from bus-off within {RECOVERY_SPEC*1000:.0f} ms"
        assert recovery_time <= RECOVERY_SPEC, \
            f"Recovery took {recovery_time*1000:.1f} ms, spec = {RECOVERY_SPEC*1000:.0f} ms"

        print(f"Bus-off recovery time: {recovery_time*1000:.1f} ms — PASS")
```

### 17.3 CAN Error Frame Test Matrix

```
┌──────────────────────────────┬──────────────────────────────┬───────────────────────────┐
│ Error Condition               │ Expected ECU Behaviour        │ How to Test               │
├──────────────────────────────┼──────────────────────────────┼───────────────────────────┤
│ Single dominant spike        │ 1 error frame, continue TX    │ HIL signal glitch inject  │
│ 10 consecutive TX errors     │ ECU enters Error Passive      │ Error injection tool      │
│ Bus-off (TEC ≥ 256)          │ CanSM triggers recovery       │ Error injection / relay   │
│ Bus-off + recovery failure   │ CanSM sets DTC, limp-home     │ Block bus 130 × 11 bits   │
│ Missing message (timeout)    │ ComM sets signal SNA, DTC     │ Disconnect sender ECU     │
│ Wrong DLC                    │ COM layer rejects, counters   │ Send modified frame       │
│ CRC mismatch                 │ Receiver increments REC       │ Corrupt data byte         │
│ Dominant stuffing violation  │ Stuff error detected          │ Error injection tool      │
└──────────────────────────────┴──────────────────────────────┴───────────────────────────┘
```

---

## 18. CAN-FD — Testing Flexible Data Rate

### 18.1 CAN-FD Differences from Classic CAN

CAN-FD (ISO 11898-1:2015) is increasingly used in ADAS, powertrain, and gateway ECUs.

```
Key differences from CAN 2.0:

SPEED:
  Arbitration phase: same as classic CAN (up to 1 Mbps)
  Data phase:        up to 8 Mbps (typical: 2 Mbps or 5 Mbps)

PAYLOAD:
  Classic CAN: max 8 bytes
  CAN-FD:      max 64 bytes (DLC encoding: 9→12, 10→16, 11→20, 12→24, 13→32, 14→48, 15→64)

NEW FIELDS IN FRAME:
  BRS bit (Bit Rate Switch):  1 = switch to higher data rate for payload
  ESI bit (Error State Indicator): 1 = sender is error passive
  FDF bit (FD Frame):         1 = this is a CAN-FD frame

CRC:
  Classic CAN: 15-bit CRC
  CAN-FD:     17-bit (≤16 bytes payload) or 21-bit (>16 bytes payload)

NO REMOTE FRAMES:
  CAN-FD does not support RTR (Remote Transmission Request)
```

### 18.2 CAN-FD DBC Differences

```
/* CAN-FD message in DBC */
BO_ 200 PowertrainStatus_FD: 32 ECM    /* 32 bytes payload */
 SG_ EngineSpeed_HiRes : 0|32@1+ (0.001,0) [0|10000] "rpm" TCM,ABS
 SG_ TorqueRequest_HiRes : 32|32@1- (0.001,0) [-500|500] "Nm" TCM
 SG_ GearPosition : 64|4@1+ (1,0) [0|15] "" TCM
 SG_ DriveMode : 68|4@1+ (1,0) [0|7] "" TCM,BCM
 ...
 /* 32 bytes × 8 bits = 256 bits total */
```

### 18.3 CAN-FD Testing Specifics

```python
"""Testing CAN-FD messages with python-can"""
import can
import cantools

# CAN-FD bus setup
bus = can.interface.Bus(
    interface="vector",
    channel=0,
    fd=True,                      # enable CAN-FD
    bitrate=500000,               # arbitration phase
    data_bitrate=2000000,         # data phase
    sjw_abr=16,
    sjw_dbr=4,
)

# Send a CAN-FD frame with 32-byte payload
msg = can.Message(
    arbitration_id=0x200,
    data=[0x01, 0x02] * 16,       # 32 bytes
    is_fd=True,
    bitrate_switch=True,          # use fast data rate for payload
)
bus.send(msg)

# Verify BRS and FDF bits in received frame
received = bus.recv(timeout=1.0)
assert received.is_fd,            "Expected FD frame"
assert received.bitrate_switch,   "Expected BRS=1 (fast data phase)"
assert len(received.data) == 32,  f"Expected 32 bytes, got {len(received.data)}"
```

```
CAN-FD Specific Test Cases:

TC-CANFD-001  Verify FDF bit = 1 for all FD messages
TC-CANFD-002  Verify BRS bit = 1 when data bitrate > arbitration bitrate
TC-CANFD-003  64-byte payload received intact (no truncation)
TC-CANFD-004  DLC encoding correct for FD frames (DLC=9 → 12 bytes)
TC-CANFD-005  CAN 2.0 and CAN-FD frames coexist on same bus without errors
TC-CANFD-006  FD node handles reception of classic CAN frame without error
TC-CANFD-007  Data phase bit rate measured ≤ ±1% of nominal (2 Mbps)
TC-CANFD-008  No frame errors with maximum payload (64 bytes) at 5 Mbps
TC-CANFD-009  ESI=1 set correctly when node enters error passive state
TC-CANFD-010  Oscilloscope: verify clean bit transitions at 5 Mbps
              (rise/fall time < 20 ns, no ringing > 10% of swing)
```

---

## 19. XCP — Calibration and Measurement Protocol

### 19.1 What is XCP?

XCP (Universal Measurement and Calibration Protocol) is used by calibration engineers to:
- **Read** ECU internal variables in real time (measurement)
- **Write** calibration parameters (maps, tables, scalars) to ECU memory
- Essential for engine tuning, ABS calibration, ADAS threshold adjustment

```
XCP over CAN (XCP on CAN) uses two CAN message IDs:
  CMD (Master → Slave): calibration tool sends commands
  RES/ERR (Slave → Master): ECU responds

Common XCP Commands:
  CONNECT           — establish XCP session
  DISCONNECT        — end session
  GET_COMM_MODE_INFO — query ECU XCP capabilities
  SET_MTA           — set Memory Transfer Address (pointer)
  UPLOAD            — read N bytes from current MTA
  DOWNLOAD          — write N bytes to current MTA
  SHORT_UPLOAD      — read 1-4 bytes with inline address
  SHORT_DOWNLOAD    — write 1-4 bytes with inline address
  COPY_CAL_PAGE     — copy working page to reference page (save calibration)
  SET_CAL_PAGE      — switch between calibration pages
  GET_DAQ_PROCESSOR_INFO — query DAQ capabilities
  ALLOC_DAQ         — allocate DAQ lists (measurement setup)
  WRITE_DAQ         — configure measurement signals
  START_STOP_DAQ    — start / stop measurement
```

### 19.2 XCP A2L File

The A2L file (ASAP2 format) is to XCP what a DBC file is to CAN — it defines all calibration parameters and measurement variables:

```asap2
/begin PROJECT ECM_Calibration ""
  /begin MODULE ECM ""
    
    /* Calibration parameter: idle speed target */
    /begin CHARACTERISTIC IdleSpeed_Target
      ""                                /* description */
      VALUE                             /* type: scalar */
      0x20001234                        /* ECU memory address */
      /begin DEPOSIT ABSOLUTE
        WORD                            /* data type: 16-bit unsigned */
      /end DEPOSIT
      0                                 /* min value */
      3000                              /* max value */
      "rpm"                             /* unit */
      (0.25, 0)                         /* factor, offset */
    /end CHARACTERISTIC
    
    /* Measurement variable: actual engine speed */
    /begin MEASUREMENT EngineSpeed_Actual
      ""
      UWORD                             /* data type */
      0x20005678                        /* ECU memory address */
      1                                 /* bit mask */
      (0.25, 0)                         /* factor, offset */
      0                                 /* min */
      16000                             /* max */
      "rpm"
    /end MEASUREMENT
    
    /* Calibration table: fuel injection map (16×16) */
    /begin CHARACTERISTIC FuelMap_2D
      ""
      MAP
      0x2000ABCD
      /begin DEPOSIT ABSOLUTE
        UWORD
      /end DEPOSIT
      ...
    /end CHARACTERISTIC
    
  /end MODULE
/end PROJECT
```

### 19.3 XCP Test Cases

```python
"""
XCP testing using pyxcp library (pip install pyxcp)
"""
import pyxcp.transport as transport
import pyxcp.master as master
import struct


def test_xcp_connect_and_read_parameter():
    """Verify XCP connection and parameter read-back."""
    # Connect to ECU via CAN
    with master.Master("CAN", transportLayerParams={
        "interface": "vector",
        "channel": 0,
        "bitrate": 500000,
        "can_id_master": 0x701,  # CMD CAN ID
        "can_id_slave":  0x700,  # RES CAN ID
    }) as xcpmaster:
        xcpmaster.connect()

        # Read idle speed target from known A2L address
        IDLE_SPEED_ADDR = 0x20001234
        xcpmaster.setMta(IDLE_SPEED_ADDR)
        raw_data = xcpmaster.upload(2)   # 2 bytes = WORD
        raw_value = struct.unpack("<H", raw_data)[0]
        physical_value = raw_value * 0.25   # factor from A2L

        print(f"IdleSpeed_Target = {physical_value:.1f} RPM (raw=0x{raw_value:04X})")
        assert 600.0 <= physical_value <= 1200.0, \
               f"Idle speed {physical_value} out of expected range 600-1200 RPM"

        xcpmaster.disconnect()


def test_xcp_write_and_verify_parameter():
    """Write calibration value and read it back to verify."""
    NEW_IDLE_SPEED = 750.0   # RPM
    IDLE_SPEED_ADDR = 0x20001234
    factor = 0.25
    raw_to_write = int(NEW_IDLE_SPEED / factor)    # 3000

    with master.Master("CAN", transportLayerParams={...}) as xcpmaster:
        xcpmaster.connect()

        # Write
        xcpmaster.setMta(IDLE_SPEED_ADDR)
        xcpmaster.download(struct.pack("<H", raw_to_write))

        # Read back and verify
        xcpmaster.setMta(IDLE_SPEED_ADDR)
        raw_read = struct.unpack("<H", xcpmaster.upload(2))[0]
        read_back_value = raw_read * factor

        assert abs(read_back_value - NEW_IDLE_SPEED) < 0.5, \
               f"Write-readback mismatch: wrote {NEW_IDLE_SPEED}, read {read_back_value}"

        xcpmaster.disconnect()
```

### 19.4 What to Test with XCP

```
XCP Test Coverage:

1. Connection/Disconnection
   - CONNECT, GET_COMM_MODE_INFO, DISCONNECT sequence
   - Multiple connect/disconnect cycles without resource leak

2. Memory Access
   - Read calibration values (compare against reference values from INCA)
   - Write within allowed range, verify write-back
   - Write boundary values (min, max of parameter range)
   - Write out of range — ECU should reject or clamp

3. Calibration Page Management
   - SET_CAL_PAGE to switch working/reference page
   - COPY_CAL_PAGE to save calibration to non-volatile
   - After ECU reset, verify saved calibration persists

4. DAQ Measurement
   - Configure DAQ list for engine speed at 10 ms rate
   - START_STOP_DAQ → verify samples arrive at correct rate
   - Compare XCP measurement vs. CAN signal — values must match

5. Security
   - Verify XCP is protected by seed-key (if specified)
   - Verify writing is only possible after UNLOCK
```

---

## 20. OBD-II Testing — On-Board Diagnostics

### 20.1 OBD-II Overview

OBD-II (SAE J1979) is the US/EU mandatory standardised diagnostic interface for emissions-related faults. Every petrol car sold after 1996 and diesel after 2001 must support it.

```
Physical access:
  16-pin OBD-II port under the steering column
  Standard protocols: ISO 15765-4 (CAN-based — most modern vehicles)

OBD-II "Modes" (called "Services" in UDS context):

Mode $01 — Show Current Data (live PIDs)
  PID 0x0C: Engine RPM           (formula: (A×256+B)/4 rpm)
  PID 0x0D: Vehicle Speed        (A km/h)
  PID 0x05: Coolant Temperature  (A-40 °C)
  PID 0x11: Throttle Position    (A×100/255 %)
  PID 0x42: Control Module Voltage
  PID 0x00: Supported PIDs 01-20 (bitmask)

Mode $02 — Show Freeze Frame Data
  Same PIDs as Mode $01, but snapshot at fault time

Mode $03 — Show Stored DTCs
  Returns all confirmed (pending + confirmed) emission-related DTCs
  Format: 2 bytes per DTC [code type + 3-digit code]

Mode $04 — Clear DTCs and Stored Values
  Clears Mode $03 and Mode $02 data
  Resets readiness monitors

Mode $09 — Request Vehicle Information
  PID 0x02: VIN (17 chars)
  PID 0x04: Calibration ID
  PID 0x0A: ECU Name
```

### 20.2 OBD-II DTC Format

```
OBD-II DTC encoding — 2 bytes:

Byte 1, bits 7-6: System identifier
  00 = P — Powertrain (engine, transmission)
  01 = C — Chassis (ABS, steering)
  10 = B — Body (airbags, climate)
  11 = U — Network (communication)

Byte 1, bits 5-4: DTC category
  00 = Generic (SAE standard)
  01 = OEM-specific (manufacturer)
  10 = Generic (SAE)
  11 = OEM-specific

Byte 1, bits 3-0 + Byte 2: 3-digit hex code

Example: P0300 (random/multiple cylinder misfire)
  P = powertrain
  0 = generic
  300 = cylinder misfire code

Example: P1234 (OEM-specific)
  P = powertrain
  1 = OEM specific
  234 = OEM-defined fault
```

### 20.3 OBD-II Readiness Monitors

```
Before an OBD-II DTC is stored, the ECU must run its "readiness monitor" — 
a diagnostic test that checks if a component or system is functioning.

Monitors:
  Continuous monitors (always running):
    - Misfire monitor
    - Fuel system monitor
    - Comprehensive component monitor

  Non-continuous monitors (run under specific conditions):
    - Catalyst efficiency
    - Heated catalyst
    - Evaporative system (EVAP)
    - Oxygen sensor
    - EGR system
    - Secondary air
    - A/C refrigerant

Test cases for monitors:
  TC-OBD-001  All monitors "not ready" after ClearDTC (Mode $04)
  TC-OBD-002  After complete drive cycle, catalyst monitor = "ready"
  TC-OBD-003  O2 sensor monitor ready after 2 min warm idle
  TC-OBD-004  Misfire monitor triggers DTC when cylinder disabled (testmode)
  TC-OBD-005  Mode $03 DTC matches Mode $19 DTC (UDS and OBD-II agree)
```

### 20.4 Python: OBD-II Live Testing

```python
"""
OBD-II testing using python-OBD library (pip install obd)
Requires ELM327 USB adapter or direct CAN interface
"""
import obd
import time
import pytest


@pytest.fixture(scope="session")
def obd_connection():
    """Connect to ECU via OBD-II."""
    conn = obd.OBD("/dev/ttyUSB0")   # or COM port on Windows
    assert conn.is_connected(), "OBD-II connection failed"
    yield conn
    conn.close()


class TestOBD2LivePIDs:

    def test_engine_rpm_pid(self, obd_connection):
        """Mode $01 PID $0C — Engine RPM must be readable and in range."""
        cmd = obd.commands.RPM
        response = obd_connection.query(cmd)
        assert not response.is_null(), "PID $0C not supported"
        rpm = response.value.magnitude
        assert 0 <= rpm <= 8000, f"RPM out of range: {rpm}"

    def test_vehicle_speed_pid(self, obd_connection):
        """Mode $01 PID $0D — Vehicle speed must be readable."""
        response = obd_connection.query(obd.commands.SPEED)
        assert not response.is_null()
        speed = response.value.magnitude  # km/h
        assert 0 <= speed <= 250

    def test_coolant_temp_pid(self, obd_connection):
        """Mode $01 PID $05 — Coolant temp must be in valid range."""
        response = obd_connection.query(obd.commands.COOLANT_TEMP)
        assert not response.is_null()
        temp = response.value.magnitude  # °C
        assert -40 <= temp <= 215, f"Coolant temp out of range: {temp}°C"

    def test_dtc_clear_and_reread(self, obd_connection):
        """Mode $04 clear → Mode $03 should return no DTCs."""
        # Clear DTCs
        resp = obd_connection.query(obd.commands.CLEAR_DTC)
        time.sleep(1.0)
        # Read DTCs
        resp = obd_connection.query(obd.commands.GET_DTC)
        dtc_list = resp.value
        assert len(dtc_list) == 0, f"DTCs after clear: {dtc_list}"

    def test_vin_readable(self, obd_connection):
        """Mode $09 PID $02 — VIN must be 17 printable ASCII chars."""
        response = obd_connection.query(obd.commands.VIN)
        assert not response.is_null()
        vin = response.value
        assert len(vin) == 17, f"VIN length = {len(vin)}, expected 17"
        assert vin.isascii() and vin.isprintable(), f"VIN contains bad chars: {vin!r}"
```

---

## 21. NvM Testing — Non-Volatile Memory

### 21.1 What is NvM in AUTOSAR?

NvM (Non-Volatile Memory Manager) is the AUTOSAR module that manages reading and writing persistent data to EEPROM or Flash. It provides an abstraction over the physical storage.

```
Data stored in NvM:
  - DTC status and snapshot data (managed by DEM)
  - Calibration values (managed by application SWCs)
  - Odometer, service interval counter
  - ECU variant coding (which options are activated)
  - Learned values (idle speed adaptation, injection trim)
  - Security access attempt counters
  - Production-mode lock flags

NvM Block types:
  NATIVE     — single block, no redundancy
  REDUNDANT  — two copies written, use valid one on read error
  DATASET    — multiple data sets (e.g., 8 variants)

NvM block states:
  NVM_REQ_OK             — block read/written successfully
  NVM_REQ_NOT_OK         — read/write failed (CRC error, erase needed)
  NVM_REQ_PENDING        — operation in progress
  NVM_REQ_INTEGRITY_FAILED — CRC check failed on read (corrupt data)
  NVM_REQ_BLOCK_SKIPPED  — block not written since last format
```

### 21.2 NvM Test Strategy

```
TEST CATEGORY 1: Normal read/write
  TC-NVM-001  After power cycle, calibration values unchanged
  TC-NVM-002  Write new calibration via XCP → power cycle → read back matches
  TC-NVM-003  DTC survives power cycle (persistent DTC in NvM)

TEST CATEGORY 2: Integrity
  TC-NVM-004  Corrupt NvM block (flip a byte in EEPROM via JTAG) →
              ECU detects NVM_REQ_INTEGRITY_FAILED → uses default values
  TC-NVM-005  Redundant block: corrupt one copy → ECU uses the good copy
  TC-NVM-006  Both copies corrupt → ECU uses ROM default + sets DTC

TEST CATEGORY 3: Boundary conditions
  TC-NVM-007  Write maximum-size block (test buffer overflow protection)
  TC-NVM-008  Rapid power cycles (10 × power cycle in 5 seconds) → no data corruption
  TC-NVM-009  Power cut during NvM write → block integrity on next boot

TEST CATEGORY 4: NvM full / wear-out simulation
  TC-NVM-010  Write counter block 100,000 times → verify wear levelling active
  TC-NVM-011  Simulate flash block erase limit reached → graceful degradation

NvM verification via UDS:
  Many ECUs expose NvM read via UDS DID or Memory Read service (0x23).
  Example: read NvM block "InjectionTrim" via DID 0xFD20:

  Request:  22 FD 20
  Response: 62 FD 20 [data bytes]

  Compare response bytes against values written by XCP tool.
```

---

## 22. DTC Lifecycle — Complete State Machine

### 22.1 DTC Status Byte — Full 8-Bit State Machine

The DTC status byte is not just 8 independent flags — it follows a specific state machine across multiple drive cycles.

```
                            ┌─────────────────────────┐
                            │  testNotCompleted bits   │
                            │  (bits 4, 6)             │
                            └─────────────────────────┘
                                        │
                              Bits reset at start of
                              each monitoring cycle
                                        │
                                        ▼
FAULT DETECTED ──────────────────► bit1=1 (testFailed)
      │                                 │
      │                        bit2=1 (pendingDTC) set
      │                                 │
      │              ┌──────────────────┴────────────────────┐
      │         1st drive cycle              2nd drive cycle
      │         (failed)                     (also failed)
      │              │                            │
      │              │                    bit3=1 (confirmedDTC)
      │              │                    bit7=1 (warningIndicator)
      │              │                            │
FAULT HEALED ────────┴────────────────────────────┘
      │
      └► bit1=0 (testFailed cleared)
         bit2=0 (pendingDTC cleared if healed before confirmation)
         bit3 stays 1 (confirmedDTC — requires manual clear or N heal cycles)
         bit5=1 (testFailedSinceLastClear — latched until ClearDTC called)

ClearDiagnosticInformation called:
  ALL bits reset to 0
  Snapshot/freeze frame deleted
  Failure counters reset
```

### 22.2 DTC Aging

After a DTC is confirmed, most ECUs implement "DTC aging" — if the vehicle drives N cycles without the fault occurring again, the DTC self-heals:

```
Typical aging configuration (OEM-specific):
  Aging threshold: 40 drive cycles
  Aging counter increments by 1 each fault-free drive cycle
  When counter reaches 40: DTC healed, cleared from memory

Test procedure:
  1. Trigger confirmed DTC (2 drive cycles with fault)
  2. Heal fault
  3. Run N (e.g., 40) simulated drive cycles without fault
     (on HIL: each "drive cycle" = power cycle with complete operation)
  4. Verify DTC auto-cleared after 40 cycles
  5. Verify DTC NOT cleared after 39 cycles

In Python with HIL:
  for cycle in range(40):
      hil.power_cycle_ecu()
      hil.run_drive_cycle()  # simulated full drive pattern

  resp = uds_client.get_dtc_by_status_mask(0xFF)
  assert len(resp.service_data.dtcs) == 0, \
      f"DTC not aged out after 40 cycles"
```

### 22.3 DTC Extended Data Records

UDS Service 0x19 Sub-function 0x06 reads extended data — additional counters per DTC:

```
Common extended data records (OEM-defined):
  Record 0x01: Occurrence counter (how many times DTC confirmed)
  Record 0x02: Aging counter (how many fault-free cycles since last failure)
  Record 0x03: Consecutive failed cycles (how many times failed in a row)
  Record 0x04: Operating time at first occurrence (odometer or run-hours)

Example UDS sequence:
  Request:  19 06 [DTC high] [DTC mid] [DTC low] FF (record 0xFF = all records)
  Response: 59 06 [DTC] [status] [record number] [data bytes] ...

Test:
  1. Trigger DTC 5 times → extended record 0x01 (occurrence) should be 5
  2. Clear DTCs → extended records reset to 0
  3. Trigger DTC again → occurrence counter restarts from 1
```

---

## 23. Flash Programming — Deep Dive Test Strategy

### 23.1 Flash Programming Architecture

```
Flash memory layout in a typical ECM (Infineon TriCore TC397):

┌─────────────────────────────────────────────────────────────┐
│  FLASH MEMORY MAP (2 MB total)                              │
│                                                             │
│  Address: 0x80000000  ┌─────────────────────────────────┐  │
│                        │  Boot sector (64 KB)            │  │
│                        │  - Bootloader (cannot be erased│  │
│                        │    without special tool)        │  │
│  Address: 0x80010000  ├─────────────────────────────────┤  │
│                        │  Application sector 0 (128 KB)  │  │
│                        │  - Software image (part 1)      │  │
│  Address: 0x80030000  ├─────────────────────────────────┤  │
│                        │  Application sector 1 (128 KB)  │  │
│                        │  - Software image (part 2)      │  │
│  ...                   │                                 │  │
│  Address: 0x801E0000  ├─────────────────────────────────┤  │
│                        │  Calibration sector (64 KB)     │  │
│                        │  - ROM defaults (read-only)     │  │
│  Address: 0x801F0000  ├─────────────────────────────────┤  │
│                        │  Working calibration (64 KB)    │  │
│                        │  - Active calibration (XCP RW)  │  │
└──────────────────────── └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

EEPROM emulated in flash (last 64 KB or separate DFLASH):
  - DTC storage
  - NvM data blocks
  - Write counter (wear levelling)
```

### 23.2 Complete Flash Programming Test Suite

```python
"""
Complete UDS Flash Programming test suite.
Assumes hex file is in Intel HEX or Motorola S-Record format.
"""
import udsoncan
import intelhex   # pip install intelhex
import hashlib
import time
from udsoncan.client import Client


class FlashProgrammer:
    """Handles full UDS flash sequence for ECU firmware update."""

    BLOCK_SIZE = 0xF0  # 240 bytes per block (from ECU RequestDownload response)

    def __init__(self, client: Client):
        self.client = client

    # ── Step 1: Prerequisites ─────────────────────────────────────────────

    def check_prerequisites(self) -> bool:
        """Vehicle must be stationary, voltage OK, no critical DTCs."""
        resp = self.client.read_data_by_identifier(0xFD10)   # FlashPrereqStatus DID
        if not resp.positive:
            raise RuntimeError(f"Cannot read prerequisites: {resp.code}")
        prereq_byte = resp.service_data.values[0xFD10][0]
        if prereq_byte != 0x00:
            raise RuntimeError(f"Prerequisites not met: 0x{prereq_byte:02X}")
        return True

    # ── Step 2: Enter programming session with security ───────────────────

    def enter_programming_mode(self):
        """Enter programming session and unlock security."""
        # Extended session first (required by most OEMs)
        resp = self.client.change_session(
            udsoncan.DiagnosticSessionControl.Session.extendedDiagnosticSession
        )
        assert resp.positive, f"Extended session failed: {resp.code}"

        # Programming session
        resp = self.client.change_session(
            udsoncan.DiagnosticSessionControl.Session.programmingSession
        )
        assert resp.positive, f"Programming session failed: {resp.code}"

        # Security access for programming (level 0x11 = programming unlock)
        seed_resp = self.client.request_seed(0x11)
        assert seed_resp.positive
        seed = seed_resp.service_data.seed
        key = self._compute_programming_key(seed)
        key_resp = self.client.send_key(0x12, key)
        assert key_resp.positive, f"Programming key rejected: {key_resp.code}"

    # ── Step 3: Erase ─────────────────────────────────────────────────────

    def erase_flash_routine(self, start_address: int, length: int):
        """Erase target flash area using RoutineControl 0xFF00."""
        erase_routine_id = 0xFF00
        params = start_address.to_bytes(4, "big") + length.to_bytes(4, "big")
        resp = self.client.routine_control_start(erase_routine_id, params)
        assert resp.positive, f"Erase routine failed: {resp.code}"
        # Poll for completion (erase takes time — expect NRC 0x78 responses)
        # udsoncan handles 0x78 automatically via p2_star_timeout

    # ── Step 4: Write firmware blocks ────────────────────────────────────

    def program_hex_file(self, hex_file_path: str, target_address: int):
        """Flash all data from an Intel HEX file to the ECU."""
        ih = intelhex.IntelHex(hex_file_path)
        binary_data = bytes(ih.tobinarray(start=target_address))

        # RequestDownload: address + size + compression=0
        mem_addr_len = 4       # 4-byte address
        mem_size_len = 4       # 4-byte size
        addr_and_len_format = (mem_addr_len << 4) | mem_size_len   # 0x44

        resp = self.client.request_download(
            memory_location=udsoncan.MemoryLocation(
                address=target_address,
                memorysize=len(binary_data),
                address_format=mem_addr_len,
                memorysize_format=mem_size_len,
            ),
            dfi=udsoncan.DataFormatIdentifier(0),  # no compression
        )
        assert resp.positive, f"RequestDownload failed: {resp.code}"
        block_size = resp.service_data.max_block_length - 2   # subtract 2 for overhead

        # Transfer in blocks
        offset = 0
        block_seq = 1
        while offset < len(binary_data):
            chunk = binary_data[offset : offset + block_size]
            resp = self.client.transfer_data(block_seq & 0xFF, chunk)
            assert resp.positive, f"TransferData block {block_seq} failed: {resp.code}"
            offset += len(chunk)
            block_seq += 1

        # RequestTransferExit
        resp = self.client.request_transfer_exit()
        assert resp.positive, f"RequestTransferExit failed: {resp.code}"

    # ── Step 5: Verify ────────────────────────────────────────────────────

    def verify_checksum(self, routine_id: int = 0xFF01):
        """Run CRC verification routine on written firmware."""
        resp = self.client.routine_control_start(routine_id)
        assert resp.positive, f"CRC verify routine failed: {resp.code}"
        result = resp.service_data.routine_status_record
        assert result[0] == 0x01, f"CRC check FAILED: routine returned 0x{result[0]:02X}"

    # ── Step 6: Activate ─────────────────────────────────────────────────

    def reset_and_activate(self):
        """Hard reset to activate new firmware."""
        resp = self.client.ecu_reset(
            udsoncan.ECUReset.ResetType.hardReset
        )
        assert resp.positive, f"ECU reset failed: {resp.code}"
        time.sleep(3.0)  # wait for ECU to boot

    def _compute_programming_key(self, seed: bytes) -> bytes:
        """Replace with actual key algorithm from ECU security specification."""
        seed_int = int.from_bytes(seed, "big")
        key_int  = seed_int ^ 0xFEEDBABE   # EXAMPLE ONLY — not a real algorithm
        return key_int.to_bytes(len(seed), "big")


# ── Test using FlashProgrammer ────────────────────────────────────────

def test_full_flash_programming_cycle(uds_client):
    """
    End-to-end flash programming test:
    1. Check prerequisites
    2. Enter programming mode
    3. Erase
    4. Program hex file
    5. Verify CRC
    6. Reset
    7. Verify new SW version
    """
    programmer = FlashProgrammer(uds_client)

    # Pre-condition: record old SW version
    old_ver_resp = uds_client.read_data_by_identifier(0xF189)
    old_version = old_ver_resp.service_data.values[0xF189] if old_ver_resp.positive else None

    # Flash
    programmer.check_prerequisites()
    programmer.enter_programming_mode()
    programmer.erase_flash_routine(start_address=0x80010000, length=0x1E0000)
    programmer.program_hex_file("firmware_v1.4.hex", target_address=0x80010000)
    programmer.verify_checksum()
    programmer.reset_and_activate()

    # Post-condition: verify new SW version
    new_ver_resp = uds_client.read_data_by_identifier(0xF189)
    assert new_ver_resp.positive
    new_version = new_ver_resp.service_data.values[0xF189]
    assert new_version != old_version, "SW version unchanged after flashing"
    assert b"1.4" in new_version, f"Expected v1.4, got {new_version}"
    print(f"Flash programming successful. Version: {new_version.decode()}")
```

---

## 24. Network Management — AUTOSAR NM Testing

### 24.1 Why Network Management Matters

In a vehicle, not all ECUs need to be awake all the time. Network Management (NM) controls:
- **Wake-up**: bringing ECUs online when needed (ignition, door open, remote start)
- **Sleep**: shutting ECUs down to save battery when not needed
- **Coordination**: ensuring all ECUs agree on whether the network is active

```
AUTOSAR NM state machine (CanNm):

             Bus-Sleep
              │    ▲
   Network   │    │  Network
   Request   ▼    │  Release + timeout
             Pre-Bus-Sleep ──(immediate)──► Bus-Sleep
              │
   Network    │  NM message received
   Requested  ▼
             Normal Operation ◄──────────────────────────────────────────┐
              │                                                           │
              └── NM Timer expires without new NM msg ──► Prepare-Bus-Sleep ──► (above)
```

### 24.2 NM Message Format (CanNm)

```
NM PDU (8 bytes, default layout):
  Byte 0: Source Node Identifier (which ECU sent this NM message)
  Byte 1: Control Bit Vector (CBV)
          Bit 3: Active Wakeup Bit (AWB) — 1 = this node initiated wakeup
          Bit 4: Partial Network Request Bit (PNI) — 1 = partial network
  Bytes 2-7: User Data (optional, defined by OEM — e.g., sleep vote bitmask)

Example NM message on CAN:
  ID:   0x400 + NodeID  (NM messages use higher IDs, 0x400-0x47F typical)
  DLC:  8
  Data: [NodeID] [CBV] [user_data...]

  For ECU with NodeID=0x05:
  0x405  8  05 08 00 00 00 00 00 00
                   └─ CBV bit 3 = AWB set (this node woke up the network)
```

### 24.3 NM Test Cases

```
TC-NM-001  NM messages appear within 50 ms of KL15 (ignition ON)
TC-NM-002  All ECUs send NM messages within their configured T_NM period
TC-NM-003  When all ECUs release network, bus enters Bus-Sleep within T_Wait_Bus_Sleep
TC-NM-004  After bus-sleep, any ECU can wake network by sending NM message
TC-NM-005  Source Node ID in NM message matches ECU's configured node address
TC-NM-006  Active Wakeup Bit set on the ECU that initiated wake-up
TC-NM-007  Network stays awake as long as any ECU has a network request active
TC-NM-008  Door module (LIN master) wakes CAN network when door opens
TC-NM-009  After KL15 OFF, network sleeps within spec time (e.g., 30 seconds)
TC-NM-010  Partial Network request: only wake required ECUs, not all

CAPL test for NM wake-up detection:
  variables { msTimer t_nm_timeout; }

  on start {
    setTimer(t_nm_timeout, 2000);
  }

  on message 0x400-0x47F {    /* NM message range */
    long nm_time = timeNow() / 1000;
    write("NM from node 0x%02X at %d ms", this.byte(0), nm_time);
    cancelTimer(t_nm_timeout);
    testStepPass("NM_Activity", "NM message at %d ms", nm_time);
  }

  on timer t_nm_timeout {
    testStepFail("NM_Activity", "No NM message within 2000 ms");
  }
```

---

## 25. ECU State Machine Testing

### 25.1 Why State Machine Testing is Critical

Most safety-critical ECU features are implemented as state machines. If a transition is missed, a condition is wrongly evaluated, or a state is never exited — the feature fails.

```
Example: ABS Control State Machine

State 0: INACTIVE
  Entry condition: vehicle speed = 0 OR ABS disabled
  Outputs: all brake pressures normal (driver-controlled)
  Transitions:
    → MONITORING: vehicle speed > 5 km/h

State 1: MONITORING  
  Entry condition: vehicle speed > 5 km/h
  Outputs: monitor wheel speed sensors every 10 ms
  Transitions:
    → INACTIVE: vehicle speed ≤ 2 km/h
    → ABS_ACTIVE: any wheel slip_ratio > 0.15 for > 10 ms

State 2: ABS_ACTIVE
  Entry condition: wheel slip detected
  Outputs: modulate brake pressure (APPLY / HOLD / RELEASE cycle)
  Transitions:
    → MONITORING: all wheel slips < 0.05 for > 50 ms
    → FAULT: any wheel speed sensor fails during ABS

State 3: FAULT
  Entry condition: sensor fault detected during ABS operation
  Outputs: ABS OFF, normal braking, warning lamp ON, DTC stored
  Transitions:
    → INACTIVE: ECU reset (ignition cycle)
```

### 25.2 State Machine Test Coverage — Transition Testing

For a state machine with N states and M transitions, complete testing requires:

```
1. State Coverage: visit every state at least once
2. Transition Coverage: execute every defined transition at least once
3. Boundary Condition: test each transition at its exact threshold
4. Invalid Transition: attempt transitions not in the spec — ensure they are rejected
5. Guard Condition: test each guard (if condition) independently

For the ABS example above:
  Transition 1 (0→1): speed increases from 0 to 5.1 km/h → verify state = MONITORING
  Transition 2 (1→0): speed decreases from 10 to 1.9 km/h → verify state = INACTIVE
  Transition 3 (1→2): inject wheel slip 0.16 for 11 ms → verify ABS_ACTIVE
  Transition 4 (2→1): remove wheel slip, wait 51 ms → verify MONITORING
  Transition 5 (2→3): inject sensor fault while ABS_ACTIVE → verify FAULT + DTC
  Transition 6 (3→0): power cycle ECU → verify INACTIVE (no fault active)

  Boundary tests:
    At speed = 4.9 km/h: should remain INACTIVE
    At speed = 5.0 km/h: transition to MONITORING
    At slip = 0.149: should remain MONITORING
    At slip = 0.150 for exactly 10 ms: still MONITORING (boundary exclusive?)
    At slip = 0.150 for 10.1 ms: should enter ABS_ACTIVE
```

### 25.3 Automated State Machine Coverage Tool

```python
"""
State machine transition coverage tracker.
Records which transitions were exercised during test run.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import time


@dataclass
class Transition:
    from_state: str
    to_state:   str
    trigger:    str
    exercised:  bool = False
    timestamp:  Optional[float] = None


class StateMachineCoverage:
    """Tracks state machine transition coverage during testing."""

    def __init__(self, transitions: List[Tuple[str, str, str]]):
        """
        Args:
            transitions: list of (from_state, to_state, trigger_description)
        """
        self.transitions: Dict[Tuple[str, str], Transition] = {}
        for from_s, to_s, trigger in transitions:
            key = (from_s, to_s)
            self.transitions[key] = Transition(from_s, to_s, trigger)

        self.current_state: Optional[str] = None
        self.history: List[Tuple[float, str, str]] = []

    def record_transition(self, from_state: str, to_state: str):
        """Call this whenever the ECU changes state (detected via CAN signal)."""
        key = (from_state, to_state)
        if key in self.transitions:
            self.transitions[key].exercised = True
            self.transitions[key].timestamp = time.monotonic()
        else:
            print(f"WARNING: Unexpected transition {from_state}→{to_state}")
        self.history.append((time.monotonic(), from_state, to_state))
        self.current_state = to_state

    def coverage_report(self) -> dict:
        total = len(self.transitions)
        covered = sum(1 for t in self.transitions.values() if t.exercised)
        not_covered = [(k, v.trigger) for k, v in self.transitions.items()
                       if not v.exercised]
        return {
            "total_transitions":    total,
            "covered_transitions":  covered,
            "coverage_percent":     round(covered / total * 100, 1),
            "not_covered":          not_covered,
        }


# Define the ABS state machine
abs_sm = StateMachineCoverage([
    ("INACTIVE",    "MONITORING",  "speed > 5 km/h"),
    ("MONITORING",  "INACTIVE",    "speed < 2 km/h"),
    ("MONITORING",  "ABS_ACTIVE",  "wheel_slip > 0.15 for 10 ms"),
    ("ABS_ACTIVE",  "MONITORING",  "all_slips < 0.05 for 50 ms"),
    ("ABS_ACTIVE",  "FAULT",       "sensor fault during ABS"),
    ("FAULT",       "INACTIVE",    "ECU reset"),
])
```

---

## 26. Static Analysis and Code Coverage in ECU SW

### 26.1 Static Analysis Tools in Automotive

Static analysis finds bugs without running the code — mandatory for ISO 26262.

```
Tool         │ What it checks                           │ Standard
─────────────┼──────────────────────────────────────────┼───────────────
PC-lint Plus │ MISRA C rules, type safety, null deref   │ MISRA C 2012
Polyspace    │ Run-time errors (div-by-zero, overflow)  │ ISO 26262 ASIL D
LDRA         │ Code coverage, MISRA, McCabe complexity  │ DO-178C, ISO 26262
Coverity     │ Security, memory safety, concurrency     │ General + ISO 26262
SonarQube    │ Code quality, duplication, smells        │ General quality
Helix QAC    │ MISRA compliance, coding rules           │ MISRA C/C++ 2012/2023
```

### 26.2 Code Coverage for ECU Software

```
Coverage types (in order of increasing strength):
  Statement coverage    — every C statement executed at least once
  Branch coverage       — both true and false of every if/else taken
  MC/DC coverage        — Modified Condition/Decision Coverage
                          (required for ASIL D / DO-178C Level A)

MC/DC Example:
  if (speed > 80 && brake_applied && !abs_active) {
      ...
  }

  This condition has 3 inputs. MC/DC requires showing that each input
  independently affects the outcome:

  Test 1: speed=90, brake=1, abs=0 → TRUE  (shows speed matters)
  Test 2: speed=70, brake=1, abs=0 → FALSE
  Test 3: speed=90, brake=0, abs=0 → FALSE (shows brake matters)
  Test 4: speed=90, brake=1, abs=1 → FALSE (shows abs_active matters)

  Minimum 4 test cases for this one condition.

Coverage targets per ASIL (ISO 26262 Part 6):
  ASIL A: Statement coverage (100%)
  ASIL B: Branch coverage (100%)
  ASIL C: MC/DC coverage (recommended)
  ASIL D: MC/DC coverage (mandatory for target code)
```

### 26.3 Measuring Coverage with gcov / LCOV

```bash
# Compile ECU SW for host (SIL mode) with coverage flags
gcc -fprofile-arcs -ftest-coverage \
    -DUNIT_TEST \
    src/abs_control.c src/speed_calc.c \
    tests/test_abs.c \
    -o test_abs_coverage

# Run tests
./test_abs_coverage

# Generate coverage data
gcov src/abs_control.c
lcov --capture --directory . --output-file coverage.info
lcov --remove coverage.info '/usr/*' --output-file coverage_filtered.info

# Generate HTML report
genhtml coverage_filtered.info --output-directory coverage_html/

# Check coverage threshold (script check)
python3 -c "
import subprocess, re
result = subprocess.run(['lcov', '--summary', 'coverage_filtered.info'],
                       capture_output=True, text=True)
match = re.search(r'lines.*?(\d+\.\d+)%', result.stdout)
coverage = float(match.group(1))
print(f'Line coverage: {coverage}%')
assert coverage >= 100.0, f'Coverage {coverage}% below 100% requirement'
"
```

---

## 27. CI/CD Pipeline for ECU Testing

### 27.1 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ECU CI/CD PIPELINE (GitHub Actions + HIL integration)                 │
│                                                                         │
│  Developer pushes code                                                  │
│       │                                                                 │
│       ▼                                                                 │
│  Stage 1: STATIC ANALYSIS (2 min, runs on any Linux agent)             │
│    ┌─────────────────────────────────────────────────────────────┐     │
│    │ - PC-lint / Helix QAC MISRA check                           │     │
│    │ - Compiler warnings (all treated as errors: -Wall -Werror)  │     │
│    │ - SonarQube quality gate                                    │     │
│    └─────────────────────────────────────────────────────────────┘     │
│       │ (fail fast — block merge on MISRA violations)                   │
│       ▼                                                                 │
│  Stage 2: UNIT TESTS + COVERAGE (5 min, Linux agent)                   │
│    ┌─────────────────────────────────────────────────────────────┐     │
│    │ - Unity / Google Test unit tests (gcc -fprofile-arcs)       │     │
│    │ - lcov coverage report (must be ≥ 100% branch)              │     │
│    │ - JUnit XML uploaded to pipeline                            │     │
│    └─────────────────────────────────────────────────────────────┘     │
│       │                                                                 │
│       ▼                                                                 │
│  Stage 3: SIL INTEGRATION TESTS (15 min, Linux agent + VEOS)           │
│    ┌─────────────────────────────────────────────────────────────┐     │
│    │ - dSPACE VEOS starts SW on virtual ECU                      │     │
│    │ - pytest SIL test suite runs                                │     │
│    │ - AUTOSAR module interaction verified                       │     │
│    └─────────────────────────────────────────────────────────────┘     │
│       │                                                                 │
│       ▼                                                                 │
│  Stage 4: HIL REGRESSION (45 min, reserved HIL agent — physical HW)    │
│    ┌─────────────────────────────────────────────────────────────┐     │
│    │ - Flash ECU with new firmware (UDS programming)             │     │
│    │ - Run full regression test suite (pytest -m regression)     │     │
│    │ - CANoe log archive attached to pipeline run                │     │
│    │ - JUnit XML + HTML report published                         │     │
│    └─────────────────────────────────────────────────────────────┘     │
│       │                                                                 │
│       ▼                                                                 │
│  Stage 5: REPORT + MERGE GATE                                          │
│    - All stages pass → allow merge to main branch                       │
│    - Any failure → block merge, notify developer                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 27.2 GitHub Actions Workflow

```yaml
# .github/workflows/ecu_ci.yml
name: ECU Software CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:

  # ── Stage 1: Static Analysis ──────────────────────────────────────────
  static_analysis:
    name: MISRA + Compiler Check
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v3

      - name: Run PC-lint
        run: |
          pclint -u -e900 \
                 +ffn +fcu \
                 -UNIT_TEST \
                 src/*.c \
                 > lint_report.txt 2>&1
          # Fail if any MISRA Required rules violated
          grep -E "error|MISRA Required" lint_report.txt && exit 1 || true

      - name: Compiler warning check
        run: |
          gcc -Wall -Wextra -Werror -std=c11 \
              -fsyntax-only src/*.c

      - name: Upload lint report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: lint_report
          path: lint_report.txt

  # ── Stage 2: Unit Tests ───────────────────────────────────────────────
  unit_tests:
    name: Unit Tests + Coverage
    runs-on: ubuntu-22.04
    needs: static_analysis
    steps:
      - uses: actions/checkout@v3

      - name: Build unit tests
        run: |
          gcc -fprofile-arcs -ftest-coverage \
              -DUNIT_TEST -Iinclude \
              src/*.c tests/unity/unity.c tests/test_*.c \
              -o run_tests -lm

      - name: Run tests
        run: |
          ./run_tests --junit-xml=test_results.xml

      - name: Check coverage
        run: |
          gcov src/*.c
          lcov --capture --directory . --output-file cov.info
          lcov --remove cov.info '*/unity/*' --output-file cov_app.info
          lcov --summary cov_app.info | tee coverage_summary.txt
          # Enforce 100% branch coverage
          python3 -c "
          import re, sys
          with open('coverage_summary.txt') as f: txt = f.read()
          m = re.search(r'branches.*?(\d+\.\d+)%', txt)
          cov = float(m.group(1))
          print(f'Branch coverage: {cov}%')
          sys.exit(0 if cov >= 100.0 else 1)
          "

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: unit_test_results
          path: |
            test_results.xml
            coverage_summary.txt

  # ── Stage 4: HIL Regression (self-hosted HIL agent) ───────────────────
  hil_regression:
    name: HIL Regression Tests
    runs-on: [self-hosted, hil-bench-1]   # label matches the HIL server
    needs: unit_tests
    steps:
      - uses: actions/checkout@v3

      - name: Flash ECU
        run: |
          python3 tools/flash_ecu.py \
              --hex firmware.hex \
              --interface vector \
              --can-channel 0

      - name: Run regression suite
        run: |
          pytest tests/regression/ \
              -m "regression" \
              -v \
              --tb=short \
              --junit-xml=hil_results.xml \
              --html=hil_report.html

      - name: Upload HIL results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: hil_test_results
          path: |
            hil_results.xml
            hil_report.html
```

### 27.3 Nightly vs. On-Demand HIL Strategies

```
ON-DEMAND (every push):
  Run: unit tests + SIL tests
  Duration: < 20 minutes
  Purpose: catch obvious regressions quickly, don't block developer

NIGHTLY (midnight scheduled):
  Run: full HIL regression + fault injection suite + timing tests
  Duration: 2–6 hours
  Purpose: comprehensive validation, catches timing/HW-specific bugs
  Alert: email to team if failures detected

RELEASE GATE (before any production release):
  Run: everything above + formal acceptance tests
  Duration: 1–2 days
  Manual review: test manager signs off report before release
  Deliverable: Test Completion Report (traceability matrix)
```

---

## 28. EMC and Environmental Robustness Testing

### 28.1 EMC Testing Overview

EMC (Electromagnetic Compatibility) testing ensures the ECU:
1. Does not emit interference that affects other systems (emissions)
2. Functions correctly in the presence of external interference (immunity)

```
Relevant standards for automotive ECUs:
  CISPR 25       — Emissions: radio interference limits
  ISO 11452-2    — Immunity: radiated field (antenna method)
  ISO 11452-4    — Immunity: bulk current injection (BCI) on wiring harness
  ISO 7637-2     — Electrical transients on 12V supply (load dump, cranking)
  ISO 16750-2    — Electrical loads and limits (overvoltage, undervoltage)
  SAE J1113-41   — Magnetic field immunity
```

### 28.2 Electrical Robustness Tests (Most Relevant for ECU Testers)

These are the electrical stress tests that ECU testers perform in the lab or via HIL simulation:

```
ISO 7637-2 Transient Tests:

Pulse 1: Supply interruption (during cranking)
  Duration: 100 ms voltage drop to 0V
  Vehicle scenario: wire resistance drops supply voltage momentarily
  ECU requirement: no reset, no DTC, no data loss
  HIL simulation: programmable power supply steps to 0V for 100 ms

Pulse 2a: Mutual inductance (inductive load switch-off)
  Duration: < 2 µs spike to −100V
  Vehicle scenario: inductive load (motor, solenoid) switched off near ECU
  ECU requirement: no damage, no false DTC

Pulse 2b: Similar to 2a but positive polarity (+75V spike)

Pulse 3a/3b: Switching transients from ignition
  Duration: burst of −220V / +150V spikes
  ECU requirement: no damage, continues operation

Pulse 4: Cranking voltage dip
  Duration: 15 ms drop to 6V
  Vehicle scenario: engine starting draws heavy current, voltage sags
  ECU requirement: no reset during or after crank, no DTC from sag

Pulse 5: Load dump (alternator disconnected)
  Duration: 400 ms spike up to 87V
  Vehicle scenario: battery cable disconnects while alternator charges
  ECU requirement: no damage (TVS diodes on ECU protect hardware)
  Note: This can DESTROY unprotected ECUs — only test with proper HW
```

### 28.3 ECU Software-Level Tests for Electrical Conditions

```python
"""
Software robustness tests for electrical conditions.
Uses HIL programmable power supply controlled via GPIB/USB.
"""
import time
import pytest


class PowerSupply:
    """Control a Keysight/Agilent bench supply via pyvisa."""

    def __init__(self, resource_id: str = "USB0::0x0957::0xB918::..."):
        import pyvisa
        rm = pyvisa.ResourceManager()
        self.supply = rm.open_resource(resource_id)
        self.supply.write("SYST:REM")           # take remote control

    def set_voltage(self, volts: float):
        self.supply.write(f"VOLT {volts:.3f}")

    def set_current_limit(self, amps: float):
        self.supply.write(f"CURR {amps:.3f}")

    def output_on(self):
        self.supply.write("OUTP ON")

    def output_off(self):
        self.supply.write("OUTP OFF")

    def voltage_dip(self, low_voltage: float, duration_ms: float, recovery_v: float = 12.0):
        """Simulate a voltage dip (e.g., cranking)."""
        self.set_voltage(low_voltage)
        time.sleep(duration_ms / 1000)
        self.set_voltage(recovery_v)


class TestElectricalRobustness:

    def test_cranking_voltage_dip(self, power_supply, uds_client, can_bus):
        """
        Pulse 4: 15 ms at 6V simulating engine cranking.
        ECU must not reset and must not set spurious DTCs.
        """
        power_supply.set_voltage(12.0)
        time.sleep(1.0)

        # Record any messages before dip
        pre_dip_ids = set()
        for _ in range(50):
            msg = can_bus.recv(timeout=0.01)
            if msg:
                pre_dip_ids.add(msg.arbitration_id)

        # Simulate cranking dip
        power_supply.voltage_dip(low_voltage=6.0, duration_ms=15.0)
        time.sleep(0.5)

        # Verify ECU recovered (still transmitting same messages)
        post_dip_ids = set()
        for _ in range(50):
            msg = can_bus.recv(timeout=0.01)
            if msg:
                post_dip_ids.add(msg.arbitration_id)

        # Key ECU messages must still be present
        assert pre_dip_ids.issubset(post_dip_ids), \
               f"Missing CAN messages after crank dip: {pre_dip_ids - post_dip_ids}"

        # Verify no DTCs from the dip
        uds_client.change_session(
            udsoncan.DiagnosticSessionControl.Session.extendedDiagnosticSession
        )
        resp = uds_client.get_dtc_by_status_mask(0x01)
        assert len(resp.service_data.dtcs) == 0, \
               f"Spurious DTCs after crank dip: {resp.service_data.dtcs}"

    def test_undervoltage_shutdown_threshold(self, power_supply, uds_client):
        """
        Gradually reduce voltage until ECU enters undervoltage protection.
        Verify DTC set at correct threshold and ECU recovers.
        """
        UVLO_THRESHOLD = 9.5   # Under Voltage Lock Out — typical value
        DTC_UNDERVOLTAGE = 0xD00100  # OEM-specific DTC code

        # Slowly ramp voltage down
        for voltage in [12.0, 11.0, 10.5, 10.0, 9.5, 9.0]:
            power_supply.set_voltage(voltage)
            time.sleep(0.5)

        # At 9.0V, ECU should have set undervoltage DTC
        resp = uds_client.get_dtc_by_status_mask(0x01)
        dtc_codes = [dtc.dtc_number for dtc in resp.service_data.dtcs]
        assert DTC_UNDERVOLTAGE in dtc_codes, \
               f"Undervoltage DTC not set at {UVLO_THRESHOLD}V"

        # Recover voltage
        power_supply.set_voltage(12.0)
        time.sleep(2.0)

        # DTC should be stored but no longer active
        resp = uds_client.get_dtc_by_status_mask(0x01)  # testFailed only
        dtc_codes = [dtc.dtc_number for dtc in resp.service_data.dtcs]
        assert DTC_UNDERVOLTAGE not in dtc_codes, \
               "Undervoltage DTC still active after voltage recovery"
```

---

### Part A — CAN / Protocol Questions (Q1–Q10)

**Q1**: What happens when two ECUs transmit on the CAN bus at the same time?
> Bit-by-bit arbitration: each transmitter monitors the bus while it transmits. The CAN ID is sent MSB first. The transmitter sending a recessive bit (1) that sees a dominant bit (0) on the bus knows it has lost arbitration and immediately stops transmitting. The node sending the lower ID (more dominant bits) wins. This is why message priority is encoded in the ID — lower ID = higher priority.

**Q2**: What is a DBC file and why is it important?
> A DBC (Data Base CAN) file is a text file that describes all CAN messages on a network: message ID, name, byte length, sender, and for each signal: bit position, length, byte order, scaling factor, offset, unit, and receiving nodes. It is the "interface contract" of the CAN bus. Test tools (CANoe, python-can) use it to decode raw hex bytes into physical values. Without DBC, you can only see raw bytes, not what they mean.

**Q3**: Explain the difference between CAN 2.0A and CAN 2.0B.
> CAN 2.0A uses an 11-bit message identifier (2048 possible IDs). CAN 2.0B uses a 29-bit extended identifier (over 536 million IDs). Both are part of the CAN 2.0 specification. 2.0B is used when more unique IDs are needed (J1939, CAN-FD systems). The frame is distinguished by the IDE (Identifier Extension) bit.

**Q4**: What is ISO-TP and why is it needed for UDS?
> UDS messages can be up to 4095 bytes (e.g., firmware blocks during flashing). A CAN frame carries maximum 8 bytes. ISO-TP (ISO 15765-2) is the transport layer that segments a large message into multiple CAN frames (First Frame + Consecutive Frames) and reassembles them. It also includes flow control so the receiver can throttle the sender. Without ISO-TP, UDS diagnostics could not work over CAN.

**Q5**: What is a babbling idiot on a CAN bus?
> A node that transmits continuously at a high rate, consuming all available bus bandwidth and starving other nodes of transmission time. Causes: firmware bug (message sent in tight loop), EMI causing the CAN controller to reset, or hardware failure. Detection: high bus load (> 80%) in CANoe bus statistics. Isolation: disconnect suspect ECUs one by one until load drops.

**Q6**: What are the five error types in CAN and which one causes TEC to increment by 8?
> (1) Bit error: transmitter detects a bit different from what it sent. (2) Stuff error: 6 consecutive bits of same polarity detected (violates bit stuffing rule). (3) CRC error: receiver's computed CRC doesn't match frame CRC. (4) Form error: fixed-format fields (EOF, ACK delimiter) have wrong polarity. (5) ACK error: transmitter detects no ACK. All cause TEC/REC to increment by 8, except receiving an error frame as a receiver (increment by 1).

**Q7**: What is bit stuffing in CAN and why is it needed?
> After 5 consecutive bits of the same value, CAN automatically inserts a complementary "stuff" bit. This ensures enough bit transitions for clock synchronisation (NRZ encoding has no self-clocking). Receivers strip out stuff bits after reception. A stuff error occurs when 6 or more consecutive same-polarity bits appear in a data area where stuffing applies (SOF through CRC).

**Q8**: What is the Flow Control frame in ISO-TP and what are the three flow statuses?
> The Flow Control (FC) frame is sent by the receiver after the First Frame to grant permission to transmit remaining Consecutive Frames. Three flow statuses: (0) ContinueToSend — send remaining blocks; (1) Wait — sender must wait; (2) Overflow — receiver cannot handle the message (abort). Key fields: BlockSize (0 = unlimited blocks before next FC), SeparationTime (minimum ms between Consecutive Frames).

**Q9**: How does CAN-FD differ from classic CAN in terms of frame structure?
> CAN-FD adds three new control bits: FDF (FD Format — marks frame as CAN-FD), BRS (Bit Rate Switch — if set, payload uses faster data bit rate), ESI (Error State Indicator — 1 means sender is error passive). Arbitration phase uses same timing as classic CAN. Payload switches to up to 8 Mbps. Payload increased from 8 to 64 bytes. CRC grows from 15-bit to 17 or 21 bits for longer payloads.

**Q10**: What is a CAN message counter and checksum signal, and why do you test them?
> Many safety-critical CAN messages include an alive counter (increments 0-15 cyclically) and a CRC/checksum computed over the data bytes. Receivers use these to detect: missed messages (counter gap > 1), duplicate messages (counter unchanged), corrupted data (CRC mismatch). Test by: verifying counter increments every cycle, injecting a message with wrong counter and confirming ECU detects the error and sets a DTC, injecting wrong checksum and confirming rejection.

---

### Part B — UDS / Diagnostic Questions (Q11–Q20)

**Q11**: What is the difference between DiagnosticSessionControl 0x01, 0x02, and 0x03?
> 0x01 Default Session: ECU's normal operating mode. Allows basic reads (VIN, SW version). No write access. 0x02 Programming Session: allows firmware download (flash), security unlock required. ECU may disable normal communication. 0x03 Extended Diagnostic Session: allows advanced diagnostics — DTC clear, IO control, routine control, calibration write. Most diagnostic tests use 0x03.

**Q12**: What is TesterPresent (0x3E) and when must you use it?
> TesterPresent is a keep-alive message that tells the ECU "the diagnostic tool is still here, don't time out." An ECU in Extended or Programming session will return to Default session after an inactivity timeout (S3 timer — typically 5 seconds). If your test takes longer than 5 seconds between UDS requests, you must send TesterPresent (sub-function 0x80 = suppress positive response) at least every 3–4 seconds. In Python: `client.tester_present(suppress_positive_response=True)`.

**Q13**: Describe the flash programming sequence in UDS.
> 1. Enter Programming Session (0x10 0x02). 2. SecurityAccess (0x27) — seed/key unlock. 3. RoutineControl erase (0x31 0xFF00). 4. RequestDownload (0x34) — specify address, size, compression. 5. TransferData (0x36) — send firmware in blocks (block size from server response). 6. RequestTransferExit (0x37) — finalise transfer. 7. RoutineControl CRC check (0x31 0xFF01). 8. ECUReset (0x11) — activate new firmware.

**Q14**: What is NRC 0x78 and how should a test handle it?
> NRC 0x78 = "requestCorrectlyReceivedResponsePending" — the ECU received the request but needs more time. The ECU sends one or more 0x7F XX 0x78 responses before the final positive or negative response. The test tool must wait (up to P2* timer = typically 5 seconds) and NOT re-send the request. In udsoncan, this is handled automatically if `p2_star_timeout` is configured.

**Q15**: What are the P2 and P2* timers in UDS?
> P2 is the maximum time between request and first response: typically 50–150 ms. If the ECU cannot respond in P2, it sends NRC 0x78 (pending) and enters the extended timeout P2* (typically 5 seconds). P2* is how long the tester waits for the final response after receiving a 0x78. These timers are defined per session — P2 in programming session is often longer (up to 5 seconds) because flash operations take time.

**Q16**: What is DID 0xF190 and 0xF186?
> These are standardised DIDs from ISO 14229-1 Annex C. 0xF190 = VehicleIdentificationNumber (VIN) — 17 ASCII characters. 0xF186 = ActiveDiagnosticSession — returns the current session byte (0x01/0x02/0x03). Both are mandatory for most automotive ECUs. Testing these early confirms basic UDS connectivity before more complex tests.

**Q17**: What is InputOutputControlByIdentifier (0x2F) and when is it used?
> 0x2F allows the tester to override ECU outputs for testing. Example: force the cooling fan relay ON regardless of temperature, force the engine to idle speed regardless of throttle input, force a warning light ON. controlOptionRecord: 0x03 = shortTermAdjustment (the actual override), 0x00 = returnControlToECU. Used to test actuator hardware and dashboard indicators without driving the actual vehicle condition.

**Q18**: Describe the DTC status byte. What does bit 3 mean?
> The 8-bit DTC status byte: bit 0 = testFailed (currently active), bit 2 = pendingDTC (failed this drive cycle), bit 3 = confirmedDTC (failed in ≥2 consecutive drive cycles — stored in NvM), bit 5 = testFailedSinceLastClear, bit 7 = warningIndicatorRequested (MIL on). Bit 3 = 1 means the DTC is confirmed and will persist across power cycles until ClearDTC is called.

**Q19**: How do you verify the seed-key security algorithm is correctly implemented?
> (1) Send SecurityAccess seed request (0x27 level). Record the seed. (2) Using your key algorithm, compute the expected key. (3) Send the key — verify positive response. (4) Send a wrong key — expect NRC 0x35 (invalidKey). (5) After 3 wrong keys, verify NRC 0x36 (exceededNumberOfAttempts) — lockout enforced. (6) Verify lockout requires ECU reset or delay timer to clear.

**Q20**: What is DTC sub-function 0x19 0x04 and what does it return?
> Service 0x19, sub-function 0x04 = ReadDTCSnapshotRecordByDTCNumber. You provide a specific DTC number and a snapshot record number (0xFF = all records). The ECU returns the DTC status byte plus the snapshot data — a collection of signal values captured at the moment the DTC was set (e.g., vehicle speed, RPM, battery voltage, coolant temp at fault time).

---

### Part C — ECU Testing / HIL Questions (Q21–Q30)

**Q21**: What is the difference between SIL and HIL testing?
> SIL (Software-in-Loop): ECU software runs on a PC (not target hardware). Fast, cheap, no hardware needed, easy debug. Used early in development. HIL (Hardware-in-Loop): Real ECU hardware with real firmware, connected to a simulated vehicle environment. Finds hardware-specific bugs (timing, ADC noise, CAN transceiver issues) that SIL misses. Used for final validation and production sign-off.

**Q22**: How do you test a DTC is correctly set and cleared?
> Test set: (1) Inject the fault condition. (2) Wait for monitor time (typically 50-200 ms). (3) Read DTC with status mask 0x01 — DTC should appear. Test clear: (1) Send ClearDiagnosticInformation (0x14 0xFF 0xFF 0xFF). (2) Read DTCs again — zero expected. Test confirmed DTC: fault must persist for 2 consecutive drive cycles before bit 3 = 1.

**Q23**: A test is failing intermittently — 1 in 20 runs fails. How do you debug it?
> (1) Add logging/timestamps. (2) Check for timing variation — replace `time.sleep()` with event-based waits. (3) Check for race condition — is the ECU still initialising when the test starts? (4) Check bus load — is another test running in parallel? (5) Run 20+ times to see if there's a pattern. (6) If intermittency is in production firmware, suspect stack overflow or race condition — provide the CANoe log of the failing instance to the SW team.

**Q24**: What is a DTC freeze frame (snapshot)?
> When a DTC is stored, the ECU captures a snapshot of key signal values at fault detection time. Example: when TPS fault occurs, freeze frame captures vehicle speed, RPM, battery voltage, coolant temp. Used for root cause analysis. In UDS, read with service 0x19 sub-function 0x04. In OBD-II, Mode $02.

**Q25**: What is HIL and describe its main components?
> HIL (Hardware-in-Loop): (1) Real ECU hardware with production firmware. (2) HIL simulator (dSPACE DS1007, NI PXI) running a mathematical vehicle model. (3) I/O boards providing realistic voltages, PWM signals, sensor resistances to the ECU's wiring harness connectors. (4) Test PC running automation scripts (Python, CANoe) to control the simulation and verify ECU behaviour. The vehicle never needs to exist physically.

**Q26**: What is the difference between functional testing and robustness testing in ECU context?
> Functional testing: verifying the ECU does the right thing under normal expected conditions. Robustness testing: verifying the ECU behaves safely under abnormal / extreme conditions (voltage spike, sensor disconnected, CAN bus saturated, extreme temperatures). Functional tests verify features; robustness tests verify safety and reliability margins.

**Q27**: What do you check immediately after flashing a new ECU software version?
> (1) Read DID 0xF189 (SW version) — confirm expected new version. (2) Read DID 0xF186 (active session) — should be 0x01 (Default). (3) Clear all DTCs from previous test session. (4) Verify no active DTCs on clean boot. (5) Check CAN bus activity — all messages transmitting at correct rates. (6) Run a quick smoke test (5-10 basic cases) before committing to full regression.

**Q28**: What is the difference between a pending DTC and a confirmed DTC?
> Pending DTC (status bit 2): fault detected in current drive cycle but not verified in second. Stored in volatile memory. Confirmed DTC (status bit 3): fault detected in at least two consecutive drive cycles. Stored in NvM — survives power cycles. Requires explicit ClearDTC to remove. Confirmed DTCs trigger warning indicators; pending usually do not.

**Q29**: Describe a test for ECU timeout handling when an input CAN message is missing.
> (1) Establish baseline — verify ECU receives message X normally. (2) Stop sending message X. (3) Wait for the timeout period defined in spec (e.g., 500 ms). (4) Verify ECU: sets the signal to SNA (Signal Not Available) value, sets the corresponding timeout DTC, enters any fallback behaviour. (5) Resume sending message X. (6) Verify ECU recovers within spec time, DTC changes to stored-not-active.

**Q30**: What is the significance of testing at temperature extremes?
> Cold (-40°C): capacitors change value, NTC sensors have very high resistance, boot time may increase. Hot (+85°C): leakage currents increase, ADC accuracy drifts, CAN transceiver switching speeds change. Software effects: timer calibration errors, floating-point drift. Test in climatic chamber with full functional test suite at -40°C, +23°C, and +85°C minimum.

---

### Part D — Safety and Process Questions (Q31–Q35)

**Q31**: What is ASIL and what does it stand for?
> ASIL = Automotive Safety Integrity Level. Part of ISO 26262. Levels: QM (no safety requirement), ASIL A (lowest), B, C, ASIL D (highest). Determined by: Severity (S0-S3), Exposure (E0-E4), Controllability (C0-C3). ASIL D functions require 100% MC/DC coverage, formal inspections, independent testing. Examples: ASIL D = airbag, brake control; ASIL A = instrument cluster.

**Q32**: What is ISO 26262 and how does it affect your test activities?
> ISO 26262 is the international standard for functional safety in road vehicle E/E systems. For testers: (1) Every safety requirement must be verified by at least one test case. (2) Test coverage must meet ASIL requirements (MC/DC for ASIL D). (3) Tools used for testing must be qualified per TÜV. (4) Test results must be documented with traceability. (5) Safety-critical tests require independence. (6) Test environment limitations must be documented.

**Q33**: What is ASPICE and what does it mean for testing?
> Automotive SPICE (Software Process Improvement and Capability Determination) defines process areas including SWE.4 (Unit Verification), SWE.5 (Integration Test), SWE.6 (Qualification Test). Level 2 = processes are documented and followed. Level 3 = processes are standardised across the organisation. OEMs assess Tier-1 suppliers on ASPICE. For testers: follow documented test process, maintain records, evidence all activities.

**Q34**: What is a Fault Tree Analysis (FTA) and how does a tester use it?
> FTA is a top-down deductive analysis: start with an undesired top event and systematically identify all combinations of lower-level causes. AND gates (all inputs needed) and OR gates (any input sufficient). Testers use FTA output to ensure test coverage of all leaf-level failure modes. If FTA identifies "sensor short to GND AND plausibility check disabled" as a failure path, there must be a test case that injects sensor short when plausibility is bypassed.

**Q35**: What is FMEA and how is it used in ECU testing?
> FMEA (Failure Mode and Effect Analysis) lists every component/function, its failure modes, and the effect of each failure. Results in a Risk Priority Number (RPN = Severity × Occurrence × Detection). High-RPN items require test cases. In ECU testing: FMEA of CAN communication would list "CAN message missing → ECU uses stale value → vehicle over-torques" — this drives test case: verify timeout handling when message is missing.

---

### Part E — Coding / Embedded C Questions (Q36–Q42)

**Q36**: In C, what is the difference between `uint8_t` and `unsigned char`?
> On most MCUs, `unsigned char` is 8 bits, but the C standard doesn't guarantee this — `char` width is implementation-defined. `uint8_t` (from `<stdint.h>`) is guaranteed to be exactly 8 bits. In MISRA C and automotive embedded code, `uint8_t`, `uint16_t`, `uint32_t` are mandatory — using `int` or `char` is a MISRA violation because their size is platform-dependent.

**Q37**: What is volatile and when should you use it in embedded C?
> `volatile` tells the compiler "this variable may change outside normal program flow — do not optimise reads away." Use it for: (1) hardware registers (value changes when hardware writes to it), (2) variables shared between main code and ISR, (3) variables shared between RTOS tasks without a mutex. Without `volatile`, the compiler may cache the value in a register and miss hardware updates.

**Q38**: A static variable inside a function — what does `static` do there?
> A `static` local variable retains its value between function calls. Initialised only once at program start. Stored in the BSS/data segment, not on the stack. In embedded: avoids re-initialisation overhead on each call, useful for one-shot initialisation flags. Caution: not thread-safe without protection in RTOS environments.

**Q39**: What is a memory-mapped register and how do you access it in C?
> Microcontroller peripherals are accessed by reading/writing to specific memory addresses — the register map in the MCU datasheet. Example: `GPIOC->MODER |= (1 << 10);` using vendor-provided header files. The `volatile` keyword is mandatory on register access — without it, the compiler optimises away the write, thinking it has no observable effect.

**Q40**: What causes a stack overflow in embedded C and how do you detect it?
> Stack overflow occurs when function calls consume more stack memory than allocated (deep recursion, large local arrays in nested calls, ISR nesting). Detection: (1) Stack canary: fill with 0xDEADBEEF at startup, check if corrupted. (2) Stack high-watermark: check which areas are still initialised pattern after running. (3) JTAG: read SP register against stack boundary. Prevention: MISRA rule banning recursion, static worst-case stack depth analysis.

**Q41**: What is an interrupt service routine (ISR) and what are the restrictions?
> An ISR is a function automatically called by the MCU hardware when an interrupt event occurs. Restrictions: (1) Must be short and fast — never call blocking functions. (2) Shared variables must be `volatile`. (3) Disable the same interrupt before modifying shared data in main code. (4) Use AUTOSAR Category 2 ISR API if calling BSW functions. (5) Never call `printf` — use ring buffer logging instead.

**Q42**: What is the difference between `#define PI 3.14` and `const float PI = 3.14f`?
> `#define` is a preprocessor text substitution — no type, no scope, no debug symbol. `const float` is a typed, scoped variable with a debug symbol. In MISRA C, `#define` for numeric constants is discouraged. `const` variables in embedded C are placed in ROM (flash) by the linker, saving RAM. Type checking catches misuse at compile time.

---

### Part F — Tools and Environment Questions (Q43–Q47)

**Q43**: You've never used CANoe before — how would you learn it in one week?
> Day 1: Open a sample project, understand the main windows: Network node, Trace, Graphic, Statistics, Data. Day 2: Import a DBC file, monitor CAN and decode signals. Day 3: Write a simple CAPL node that sends a message and reacts to a response. Day 4: Write a CAPL testcase with testStepPass/testStepFail and run it. Day 5: Connect to a real ECU, run an existing CAPL test suite, understand its output.

**Q44**: What is the difference between CANalyzer and CANoe?
> CANalyzer is a monitoring and analysis tool — passively reads CAN traffic, decodes signals, displays statistics, logs data. Cannot run test scripts programmatically. CANoe is a complete simulation and test tool — CAN network simulation engine, CAPL scripting, automated test sequences with pass/fail verdicts, supports multiple buses simultaneously (CAN + LIN + Ethernet). CANoe includes all CANalyzer functionality plus test automation.

**Q45**: What is INCA (ETAS) and when do you use it?
> INCA (Integrated Calibration and Application Tool) by ETAS reads the A2L file (ASAP2 format) to know ECU parameter addresses and scaling. Calibration engineers use it to read live measurement variables, write calibration parameters (fuel maps, PID gains, thresholds) to ECU RAM, flash calibration data to NvM. Testers use INCA to verify calibration reference values and read internal ECU states not exposed on CAN.

**Q46**: What is dSPACE ControlDesk?
> ControlDesk is the user interface software for dSPACE HIL simulators. It controls the real-time simulation model. During testing, use ControlDesk to: set vehicle simulation parameters, inject fault conditions, read simulation states, create instrument panels to visualise data. Also supports Python scripting via Scripting API for automated test sequences.

**Q47**: What is Lauterbach TRACE32 and when do you need it?
> TRACE32 is a professional JTAG debugging environment for embedded systems. Use cases: (1) Set breakpoints and step through firmware. (2) View all CPU registers, stack, memory at any point. (3) Real-time trace: record all executed instructions to find what happened before a crash. (4) Code coverage on real hardware. (5) Flash firmware directly (faster than UDS for development). Caution: using JTAG halts the CPU — watchdog may fire, real-time behaviour changes.

---

### Part G — Process / Scenario Questions (Q48–Q53)

**Q48**: A new software build has 5 test failures that passed in the previous build. What do you do?
> (1) Confirm failures are reproducible. (2) Check if test environment changed — rule out false positives. (3) Review the change log — what was modified? (4) For each failure: regression from code change, or pre-existing issue? (5) File JIRA bugs with test case ID, pass/fail build versions, CAN log attached. (6) Mark build as "NOT RELEASE CANDIDATE" until addressed. (7) Communicate specific failures and their likely relation to the code change.

**Q49**: A critical safety test is failing and the release is tomorrow. How do you handle it?
> Do NOT approve the release. (1) Immediately escalate to project manager and SW team leader. (2) Document the failure in detail — test case ID, expected vs. actual, severity. (3) If the failure violates an ASIL requirement, the release cannot proceed under ISO 26262 without a formal risk assessment and waiver process requiring management + customer agreement. (4) Never hide a known safety test failure — it has legal and liability implications.

**Q50**: How do you write a test plan for a new ECU feature (e.g., AEB)?
> (1) Review feature requirements — identify all SRS requirements linked to AEB. (2) Identify test scope: which subsystems are involved. (3) Define test environments: SIL, HIL, vehicle for each scenario. (4) Write test cases for each requirement — normal, boundary, fault cases. (5) Define pass/fail criteria: braking distance, timing, DTC behaviour, driver override. (6) Plan for regression: mark all test cases as regression candidates. (7) Resource planning: HIL hours, test vehicle hours needed.

**Q51**: Describe how you would set up a Python-based automated test for verifying a CAN gateway.
> (1) Use two CAN interfaces — one to inject on source bus, one to monitor destination bus. (2) Send known messages on source bus. (3) Verify on destination bus: message arrives, arrives within specified latency (e.g., < 5 ms), data is correctly translated. (4) Verify messages NOT in routing table are NOT forwarded. (5) Test fault cases: message with wrong DLC — gateway must handle gracefully.

**Q52**: How do you handle test cases that require multiple drive cycles?
> In HIL, a "drive cycle" = power on (KL15 ON) → run vehicle simulation → power off (KL15 OFF) → wait 2-5 s → repeat. Python automation can loop this 40 times for DTC aging tests, 2 times for DTC confirmation. Record DTC status via UDS at end of each cycle. Each power-on-to-power-off counts as one drive cycle.

**Q53**: What do you do when a test fails because of a timing issue in the test script, not the ECU?
> (1) Identify root cause: is the test using `time.sleep()` when it should wait for a specific CAN message? (2) Replace time-based waits with event-based waits. (3) Add appropriate timeouts with failure messages. (4) Run corrected test 20+ times to confirm stability. (5) Add to "flaky tests" tracking list and document the fix.

---

### Part H — Advanced Technical Questions (Q54–Q65)

**Q54**: What is MC/DC code coverage and why is it required for ASIL D?
> MC/DC (Modified Condition/Decision Coverage) requires that each individual condition in a compound Boolean expression independently affects the decision outcome. For `A && B && C`, you need tests where changing only A flips the result (B, C fixed), changing only B flips the result, changing only C flips the result. Required for ASIL D (ISO 26262 Part 6). Standard branch coverage is insufficient because it doesn't verify each condition independently.

**Q55**: What is a CAN network management message and what does the Active Wakeup bit mean?
> NM messages coordinate ECU sleep/wake transitions. In AUTOSAR CanNm, each ECU that wants to stay awake sends NM messages periodically. When no ECU wants the network, they stop sending NM messages, and after bus-sleep timer expires, all enter bus-sleep. The Active Wakeup Bit (AWB, bit 3 in CBV byte) is set by the ECU that INITIATED the wakeup — identifies the source of network activity for diagnostics.

**Q56**: Explain the difference between polling and interrupt-driven I/O in embedded systems.
> Polling: CPU continuously checks a flag in a loop — simple but wastes CPU cycles and adds latency. Interrupt-driven: hardware raises an interrupt when data arrives, CPU switches to ISR to handle it. More complex but CPU is free between events and latency is minimised. In CAN communication: CAN controllers are always interrupt-driven — the CAN hardware interrupt fires when a frame is received, ISR deposits it in a ring buffer.

**Q57**: What is a DMA transfer and why is it used in ECU ADC reading?
> DMA (Direct Memory Access) allows the ADC to write samples directly to a RAM buffer WITHOUT involving the CPU. The CPU wakes only when the buffer is full, reads averaged values, and goes back to sleep. Without DMA, the CPU would need to wait for each ADC conversion — very inefficient when reading multiple sensors at 1 ms intervals.

**Q58**: What is the AUTOSAR COM Invalid Value mechanism?
> Each CAN signal in AUTOSAR COM can be configured with an "invalid value" — a specific value meaning "this signal's data is not valid." When COM detects the incoming signal equals the invalid value, it may set the signal to a replacement value or trigger a callback. Test: send a CAN message with the signal value set to the configured invalid value — verify the ECU does NOT use this value for control logic.

**Q59**: How does bit-rate switching in CAN-FD affect your test setup?
> With BRS=1, the CAN frame switches from arbitration bit rate to faster data bit rate at the BRS bit. Your test hardware must support CAN-FD with the same data bit rate as the ECU. If the interface doesn't support CAN-FD or has wrong timing parameters, you will see only error frames. In python-can: ensure `fd=True` and `data_bitrate=2000000` match your ECU. In CANoe: configure both nominal and data timing to match the ECU's oscillator spec.

**Q60**: What is XCP DAQ mode and why is it better than simple polling?
> In polling mode, the calibration tool requests each variable individually — each request/response takes one CAN round trip. For 50 variables at 10 ms rate, polling is too slow. DAQ (Data Acquisition) mode: the ECU is pre-configured with variable addresses and rates. At each configured rate, the ECU automatically packs all values into CAN frames without any request from the tool. Allows high-speed synchronous measurement of multiple signals — critical for engine calibration.

**Q61**: You receive a new DBC file for a new ECU variant. What is your first step?
> (1) Open the DBC and review message IDs, cycle times, signal names, ranges, units. (2) Compare against previous DBC version — what changed? (3) Verify against requirements specification — does every signal have defined range, unit, and sender? (4) Check for gaps: messages with no cycle time defined, signals with default SNA values. (5) Check message IDs for conflicts. (6) Update your CAPL test nodes and Python test scripts.

**Q62**: The ECU sends a CAN message but CANoe shows it as "raw" (not decoded). Why?
> The message is not mapped to any DBC definition. Causes: (1) DBC file not loaded in CANoe. (2) Message ID in DBC does not match what ECU is sending (different in hex vs. decimal, or 11-bit vs. 29-bit ID). (3) ECU uses a different ID based on variant coding. Fix: search DBC for the correct message ID. If not found, the message may be new or undocumented — request updated DBC from supplier.

**Q63**: Your Python UDS test is getting NRC 0x22 when trying to clear DTCs. What could be wrong?
> NRC 0x22 = conditionsNotCorrect. For ClearDTC (0x14): (1) Not in Extended session — ClearDTC typically not available in Default session. Ensure `change_session(extendedDiagnosticSession)` is called first. (2) Vehicle conditions not met — some OEMs require speed = 0 before clearing DTCs. (3) Another diagnostic session is active. Debug: read DID 0xF186 to confirm active session, check ECU communication specification for service 0x14 preconditions.

**Q64**: After a power cycle, your ECU is not responding on CAN at all. Describe your debugging steps.
> (1) Check power supply: measure 12V at ECU connector. (2) Check CAN bus termination: measure 60Ω between CAN_H and CAN_L (no power). (3) Check CAN_H and CAN_L with oscilloscope — any activity? (4) Connect another known-working ECU to same bus — does it appear? Isolates bus vs. ECU problem. (5) Power cycle and watch for any CAN activity in first 500 ms. (6) Check if KL30 (permanent supply) and KL15 (ignition) are both present. (7) If development ECU: check JTAG for flash integrity failure.

**Q65**: How would you test that an ECU correctly handles an alive counter gap (skipped from 3 to 5)?
> (1) Set up a CANoe simulation node sending the message with correct incrementing counter. (2) Modify CAPL to inject a counter skip: send 3, then 5 (skipping 4). (3) Observe ECU behaviour: does it set signal SNA? Trigger a DTC? Fall back to default value? (4) Verify expected DTC is stored. (5) Resume correct counter — verify ECU recovers and DTC changes to stored-not-active. (6) Repeat with other anomalies: repeated counter, counter jump > 1.

---

### Part I — Integration and Architecture Questions (Q66–Q72)

**Q66**: How would you test two ECUs that have never been tested together before?
> (1) Review DBC for both — identify which messages each sends and receives. Draw a communication matrix. (2) Set up bench with both ECUs on same CAN bus. (3) Monitor bus — verify both ECUs transmitting expected messages. (4) Cross-check: does ECU_A react to signals from ECU_B? (5) Test signal scaling compatibility — factor/offset mismatches are a common integration bug. (6) Test timeout handling: stop ECU_B's messages, verify ECU_A handles timeout correctly. (7) Test edge cases from the interface specification.

**Q67**: What is the difference between testing in Normal Operating Conditions vs. Degraded Conditions?
> Normal Operating: all sensors present, correct voltage (12-14V), no active faults, ambient 23°C. Verifies the feature works as intended. Degraded Conditions: one or more inputs degraded — sensor with noise, battery at 9V, CAN message arriving 20% late, non-critical fault active. Verifies the system degrades gracefully — still provides some functionality and does not cause new hazards. Required for ASIL functions.

**Q68**: What is EOL (End of Line) testing and how does it differ from development testing?
> EOL testing happens at the vehicle assembly plant after ECU installation. Done in seconds per vehicle. Tests: flash final firmware + calibration, variant coding, basic smoke test (VIN, no DTCs), odometer initialisation, sensor plausibility. Development testing is thorough (hours/days), covers all edge cases, done in lab with full traceability. EOL only verifies the ECU is correctly configured and functional for that specific vehicle.

**Q69**: What is AUTOSAR RTE and why does it matter for integration testing?
> The Runtime Environment (RTE) is generated middleware connecting Software Components (SWCs) to each other and to Basic Software. It implements the port-connector model: SWC_A sends data via sender port → RTE routes to SWC_B's receiver port. Integration test must verify RTE connections are correct — a misconfigured port means data doesn't flow. RTE configuration errors typically manifest as "signal always zero" or "signal never updates."

**Q70**: What would you do differently testing an ADAS ECU vs. a body control ECU?
> ADAS ECU (AEB, ACC): higher safety requirements (ASIL C/D), complex sensor fusion, real-time latency critical (< 100 ms end-to-end for AEB), test requires representative scenarios (object detection at various speeds), HIL must include sensor simulation (object injection into radar model), more extensive fault injection. Body Control ECU (windows, lights): simpler logic, lower ASIL, shorter test suite, mainly electrical/CAN functional tests, LIN bus testing.

**Q71**: What is a "limp-home mode" and how do you verify it is implemented correctly?
> Limp-home mode: when a critical input fails, the ECU limits its output to a safe default allowing the vehicle to drive slowly to a service location. Examples: TPS fails → engine limited to 1500 RPM. Testing: inject each critical fault, verify the specific limp-home behaviour is activated (check CAN signal values, DTC, warning lamp state), verify output is within safe range, verify normal operation resumes after fault is cleared.

**Q72**: How do you test that calibration changes persist across a power cycle using only UDS?
> (1) Read current calibration value via ReadDataByIdentifier. (2) Write new value via WriteDataByIdentifier. (3) Read back immediately — verify new value active in RAM. (4) Send ECUReset hardReset or power-cycle the ECU. (5) Wait for ECU to boot. (6) Read the DID again. If NvM write-back is working, the value should still be the new value. If reverted, the NvM save routine is not executing.

---

### Part J — Senior-Level Questions (Q73–Q80)

**Q73**: How would you design a test strategy for a complete vehicle ECU network (50+ ECUs)?
> Tiered approach: (1) Component level: each ECU tested individually on HIL with mocked network. (2) Subsystem level: related ECUs tested together (powertrain cluster: ECM + TCM + ABS). (3) Full network integration: complete vehicle HW-in-Loop with all ECUs. (4) Vehicle test: final validation on track/road. Prioritise by ASIL — ASIL D functions must have 100% coverage at all levels. Use test management tool (Polarion) to track coverage. Maintain smoke suite (2 hours) for daily builds and full regression suite (48 hours) for release candidates.

**Q74**: How do you measure and report test effectiveness beyond just pass/fail numbers?
> Additional metrics: (1) Requirement coverage % (tested vs. total). (2) Defect detection effectiveness = bugs found by tests / bugs found in field (goal > 95%). (3) Code coverage % by ASIL level. (4) Test execution time trend. (5) False positive rate. (6) Mean time to detect (how quickly new bugs are caught after code change). (7) Regression escape rate. Present these in sprint reviews and release readiness meetings.

**Q75**: Describe your approach to managing a test suite that has grown to 2000 test cases over 3 years.
> (1) Categorise: smoke (50 cases), regression (500 cases), full validation (2000 cases). (2) Review and retire: remove obsolete tests for deprecated features, merge duplicates. (3) Prioritise: smoke on every commit, regression nightly, full validation on release candidates. (4) Parallelise: partition by subsystem across multiple HIL benches. (5) Track flaky tests: any test failing > 5% of runs without ECU defect is quarantined and fixed. (6) Coverage mapping: no new requirements added without corresponding tests.

**Q76**: What is your process for root-cause analysis when a vehicle issue was not caught in HIL?
> (1) Collect all data: CAN logs, DTC snapshot, drive conditions, ambient temperature. (2) Reproduce in HIL — is the vehicle scenario in any existing HIL scenario? If not, create it. (3) If not reproducible: identify what the HIL model doesn't simulate (real road surface, actual sensor noise). (4) Use JTAG/TRACE32 on development ECU in test vehicle to capture exact CPU state during fault. (5) Once root cause identified: fix firmware, add HIL test case, run regression, update HIL model. (6) Document the HIL coverage gap as a lesson learned.

**Q77**: How do you handle conflicting requirements between two ECU suppliers sharing a CAN signal?
> (1) Document the conflict precisely. (2) Identify the authoritative source: the System DBC owned by the OEM is ground truth. (3) Raise a JIRA/DOORS change request with both suppliers and OEM attached. (4) OEM arbitrates and updates the System DBC. (5) Both suppliers update their ECU-specific DBCs and software. (6) Test regression on both ECUs after the change. (7) Traceability: link the DBC change to the DOORS requirement.

**Q78**: What is your advice to a CSE graduate joining automotive ECU testing for the first time?
> (1) Learn CAN first — install python-can, connect to any CAN bus, decode signals. (2) Read ISO 14229-1 (UDS) — at least services 0x10, 0x22, 0x14, 0x19, 0x27. (3) Your CSE background is a strength — you can write test automation faster than most automotive engineers. (4) Learn CAPL for CANoe. (5) Never sign off a safety-critical test failure — escalate always. (6) Embrace the documentation culture (ASPICE, ISO 26262) — it exists for good legal reasons. (7) Learn what a relay, ADC, and CAN transceiver are — you cannot test what you don't understand.

**Q79**: How would you approach testing an over-the-air (OTA) software update?
> OTA uses DoIP (Ethernet) or UDS over CAN. Test scope: (1) Connectivity: vehicle connects to backend, authentication (TLS certificates verified). (2) Download: firmware package downloaded correctly, CRC verified before apply. (3) Pre-conditions: vehicle stationary, sufficient battery, correct ECU variant. (4) Programming: same UDS flash sequence as workshop. (5) Post-update: verify new SW version, no DTCs, all functions operational. (6) Rollback: if verification fails, rollback to previous version (dual-bank flash). (7) Security: no downgrade attack possible (version rollback prevention).

**Q80**: A customer reports an intermittent stall after engine restart in cold weather. How do you approach this?
> (1) Reproduce: set HIL climatic chamber to -15°C, perform rapid restart cycles (start, run 2 min, stop, restart within 10 s). (2) Collect data: CANoe log all CAN traffic during restart; INCA log internal ECU variables (injection timing, idle controller state, coolant temp). (3) Compare successful vs. failed restart logs: look for timing differences in idle controller, NvM read completion, or sensor plausibility during startup. (4) Check freeze frame of any DTC set during the stall — were there NvM read errors or calibration defaults used? (5) Hypothesis-test: does the stall correlate with NvM being slow to read at cold temperature? (6) Fix: adjust NvM read timeout or idle fallback calibration, retest 50 cold starts to confirm fix.

---

## Learning Path — From CSE to Automotive ECU Test Engineer

### 4-Month Structured Plan

```
MONTH 1 — Foundation
  Week 1: CAN protocol (ISO 11898-1) + DBC files + CANalyzer basics
           → Exercise: Set up python-can, monitor CAN traffic from a demo DBC
           → Deliverable: Python script that decodes EngineSpeed from CAN trace

  Week 2: UDS protocol (ISO 14229-1) — all key services
           → Exercise: Use udsoncan to read VIN and clear DTCs from an ECU
           → Deliverable: pytest test for session control + read VIN

  Week 3: AUTOSAR architecture overview + OSEK OS basics
           → Exercise: Read AUTOSAR_EXP_LayeredSoftwareArchitecture.pdf (free PDF)
           → Deliverable: Diagram showing BSW/RTE/ASW layers with module names

  Week 4: ECU test case writing (IEEE 829 adapted) + traceability
           → Exercise: Write 10 test cases for a CAN gateway function
           → Deliverable: Excel traceability matrix linking SRS to test cases

MONTH 2 — Hands-On Testing
  Week 5: Set up Python test framework (pytest + udsoncan + python-can)
           → Project: Automated diagnostic test suite (session, DTC, read DID)
           → Deliverable: 20 passing pytest tests with conftest.py fixtures

  Week 6: CAPL scripting for CANoe — write your first test node
           → Project: CAPL test: engine speed range + periodicity validation
           → Deliverable: CAPL testcase generating pass/fail XML report

  Week 7: Fault injection — understand HIL relay boards + fault injection theory
           → Exercise: Design test cases for sensor open/short/out-of-range
           → Deliverable: 15 fault injection test cases with expected DTCs

  Week 8: ISO 26262 overview for testers — ASIL, safety mechanisms, tool qual
           → Exercise: Map safety requirements to test cases for ABS ECU
           → Deliverable: ASIL coverage analysis for 20 ABS requirements

MONTH 3 — Advanced Topics
  Week 9:  Flash programming over UDS — RequestDownload → TransferData
           → Exercise: Script a full flash sequence in Python (FlashProgrammer class)
           → Deliverable: Python flash script with error handling

  Week 10: NvM testing + DTC lifecycle state machine
           → Exercise: Write test for DTC confirmation (2-drive-cycle test)
           → Deliverable: pytest parameterised test for all 8 DTC status bits

  Week 11: XCP calibration protocol + A2L files
           → Exercise: Use pyxcp to read and write a calibration parameter
           → Deliverable: XCP read/write test with write-readback verification

  Week 12: CAN-FD + Network Management testing
           → Exercise: Write CAPL test for NM wake-up and bus-sleep timing
           → Deliverable: NM test suite (5 test cases)

MONTH 4 — Integration and Career
  Week 13: CI/CD for ECU tests — GitHub Actions + Jenkins setup
           → Project: CI pipeline that runs unit tests on every push
           → Deliverable: .github/workflows/ecu_ci.yml passing pipeline

  Week 14: Root cause analysis — 5 Whys, fault tree, CAN trace reading
           → Exercise: Analyse a provided CANoe log with 3 intentional bugs
           → Deliverable: RCA report with identified root causes

  Week 15: EMC robustness + boot sequence testing
           → Exercise: Write test cases for voltage dip and ECU startup timing
           → Deliverable: 10 robustness test cases for electrical conditions

  Week 16: Interview prep + portfolio review
           → Practice all 80 Q&A above
           → Deliverable: 2-page project summary describing your test framework
```

### Key Tools to Learn (in order of priority)

```
Priority 1 — Start immediately (free tools)
  python-can           pip install python-can
  can-isotp            pip install can-isotp
  udsoncan             pip install udsoncan
  cantools             pip install cantools  (DBC parsing in Python)
  pyxcp                pip install pyxcp

Priority 2 — Get trial license (Vector website)
  CANalyzer 30-day trial   ← essential for visualising CAN
  CANoe 30-day trial       ← essential for CAPL and test automation

Priority 3 — When you have hardware access
  ETAS INCA               ← calibration tool, see it at work
  dSPACE ControlDesk      ← HIL environment
  PCAN-USB                ← affordable CAN interface (~€80)

Priority 4 — Nice to have
  Lauterbach TRACE32      ← deep debug (expensive — use at employer)
  Vector VN1610           ← professional CAN interface
```

### Essential Standards to Know

```
ISO 11898-1    CAN Data Link Layer
ISO 11898-2    CAN Physical Layer (high-speed)
ISO 14229-1    UDS (Unified Diagnostic Services)
ISO 15765-2    ISO-TP (CAN Transport Layer for UDS)
ISO 15765-4    OBD-II on CAN
ISO 13400-2    DoIP (Diagnostics over IP / Ethernet)
ISO 26262      Functional Safety for Road Vehicles
ISO 16750-2    Electrical Requirements (voltage, temperature, EMC)
ISO 7637-2     Electrical Transients (pulses, load dump)
AUTOSAR 4.x    Automotive Software Architecture
SAE J1939      Heavy vehicle CAN protocol (trucks, buses)
SAE J1979      OBD-II diagnostic services
ASPICE         Automotive SPICE (process standard)
MISRA C 2012   Coding standard for safety-critical C
```

---

*Document: ECU Embedded Testing in Automotive Domain — CSE Engineer Guide*
*Version: 2.0 | Date: 2026-05-05 | Chapters: 29 | Q&A: 80*
