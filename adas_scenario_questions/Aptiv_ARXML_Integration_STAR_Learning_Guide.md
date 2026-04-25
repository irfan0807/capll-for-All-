# Aptiv – Senior SW Engineer: Algorithm Integration & ARXML
## Complete Learning Guide with STAR Interview Answers

**Role:** Senior ADAS Algorithm Integration Engineer (Individual Contributor)  
**Company:** Aptiv  
**Experience:** 9–12 Years  
**Date:** 25 April 2026  

---

## Table of Contents

1. [Job Breakdown – What They Really Want](#1-job-breakdown)
2. [Technical Learning Map](#2-technical-learning-map)
3. [Topic 1: AUTOSAR Classic & ARXML Integration](#3-autosar-classic--arxml-integration)
4. [Topic 2: Vector DaVinci Toolchain](#4-vector-davinci-toolchain)
5. [Topic 3: Embedded C & 32-bit MCU Architectures](#5-embedded-c--32-bit-mcu-architectures)
6. [Topic 4: ADAS Perception & Planning Pipelines](#6-adas-perception--planning-pipelines)
7. [Topic 5: ASPICE & Automotive Standards](#7-aspice--automotive-standards)
8. [Topic 6: ISO 26262 Functional Safety](#8-iso-26262-functional-safety)
9. [Topic 7: SIL/HIL Testing & Debugging](#9-silhil-testing--debugging)
10. [Topic 8: Middleware – SOME-IP, DDS, RTPS](#10-middleware--some-ip-dds-rtps)
11. [Topic 9: Agile/Scrum in Automotive](#11-agilescrum-in-automotive)
12. [STAR Interview Answers – 20 Questions](#12-star-interview-answers)
13. [30-Day Study Roadmap](#13-30-day-study-roadmap)

---

## 1. Job Breakdown – What They Really Want

Understanding the role before studying it is critical. Below is a decoded breakdown of each requirement.

| Job Statement | What It Really Means | Priority |
|---|---|---|
| "Integrating Application ARXML received from customer, supplier, inhouse" | You must be able to import, resolve, and configure ARXML in DaVinci without hand-holding | CRITICAL |
| "Hands-on with AUTOSAR Classic Architecture" | You can configure BSW (COM, DCM, OS, NvM, PduR) and generate RTE independently | CRITICAL |
| "Vector DaVinci Configurator" | Day-to-day tool. You must be proficient, not just familiar | CRITICAL |
| "32-bit MCU – Infineon Aurix, Renesas, ARM" | You have flashed, debugged, and written actual code on real hardware | HIGH |
| "ADAS domain experience" | You know what you're integrating – perception, planning, sensor signals | HIGH |
| "Debugging complex ECUs" | You've used JTAG debuggers (Trace32, iSystem) to find root cause on target hardware | HIGH |
| "SIL/HIL exposure" | You've run test scenarios in at least one simulation environment | HIGH |
| "ASPICE compliance" | You produce traceable artifacts – requirements, design docs, test reports | MEDIUM |
| "ISO 26262 familiarity" | You know ASIL classification, safety requirements, and freedom from interference | MEDIUM |
| "Camera, radar, lidar integration" | You've worked with sensor data over CAN/Ethernet in an ECU | PREFERRED |
| "SOME-IP, DDS middleware" | Bonus – especially for AUTOSAR Adaptive projects | PREFERRED |

---

## 2. Technical Learning Map

```
AUTOSAR Classic (Core)
    ├── Architecture: ASW → RTE → BSW → MCAL
    ├── SWC Design & ARXML (DaVinci Developer)
    ├── BSW Config: COM, PduR, CanIf, DCM, DEM, OS, NvM
    ├── ARXML Integration Workflow
    └── Code Generation & RTE

DaVinci Toolchain
    ├── DaVinci Developer: SWC creation, Port/Interface definition
    └── DaVinci Configurator Pro: BSW config, ARXML import, generation

MCU & Embedded C
    ├── Infineon Aurix TriCore architecture
    ├── ARM Cortex-R/M for safety
    ├── Embedded C: volatile, const, bitfields, MISRA
    └── JTAG Debugging (Trace32, iSystem)

ADAS Domain
    ├── Sensor Pipeline: Camera → ISP → Object List
    ├── Radar: FMCW → Point Cloud → Object Track
    ├── Sensor Fusion: EKF, Object Association
    └── Planning: FSM, ACC, AEB, LKA logic

Standards & Process
    ├── ASPICE SWE.1–SWE.6 (V-Model)
    ├── ISO 26262 (ASIL A–D, Safety Goals)
    ├── GDPR (if telematics involved)
    └── Agile/Scrum Ceremonies

Testing
    ├── SIL: PC-based AUTOSAR simulation
    ├── HIL: Real ECU + dSPACE/Vector simulator
    └── Vehicle Testing: On-road validation
```

---

## 3. AUTOSAR Classic & ARXML Integration

### 3.1 Architecture Layers (Must Know Cold)

```
┌─────────────────────────────────────────┐
│        Application Layer (ASW)          │  ← SWCs live here
├─────────────────────────────────────────┤
│     Runtime Environment (RTE)           │  ← Generated. Never edited manually.
├─────────────────────────────────────────┤
│         Basic Software (BSW)            │
│  ┌──────────┬──────────┬─────────────┐  │
│  │ Services │ ECU Abs  │   Complex   │  │
│  │  Layer   │  Layer   │   Drivers   │  │
├──┴──────────┴──────────┴─────────────┤  │
│   MCAL (Microcontroller Abstraction)    │  ← Vendor-provided (Infineon, NXP)
├─────────────────────────────────────────┤
│           Hardware (MCU)                │
└─────────────────────────────────────────┘
```

### 3.2 SWC Types

| SWC Type | Purpose | Example |
|---|---|---|
| Application SWC | Business logic | ACC Controller |
| Sensor Actuator SWC | Hardware access | Radar signal reader |
| Service SWC | BSW services | NVRAM provider |
| Composition | Groups of SWCs | ADAS Subsystem |

### 3.3 ARXML Integration Workflow (Daily Job)

```
Step 1: RECEIVE ARXML
    - From: OEM (system design), Supplier (SWC), Inhouse developer
    - Contains: SWC description, interfaces, data types, timing

Step 2: IMPORT INTO DAVINCI
    - Open DaVinci Configurator Pro
    - Import ARXML: File → Import → AUTOSAR Description
    - Resolve all data type mismatches and schema conflicts

Step 3: MAP TO SYSTEM
    - Assign SWC to ECU (ECU Extract)
    - Map runnable entities to OS Tasks
    - Connect P-Ports to R-Ports via RTE connectors

Step 4: CONFIGURE BSW
    - COM: Map signals to PDUs, set transmission modes
    - PduR: Define routing paths
    - CanIf: Define CAN HOH (Hardware Object Handles)
    - DCM: Map DIDs to SWC DataProviders
    - OS: Set task priorities, periods, stack sizes

Step 5: GENERATE CODE
    - DaVinci generates: Rte.c, Rte.h, Com_Cfg.c, PduR_Cfg.c
    - Review generated files for correctness

Step 6: BUILD & FLASH
    - Compile with target compiler (e.g., HighTec GCC for Aurix)
    - Flash to ECU via JTAG / UDS flashing

Step 7: VALIDATE
    - Test with CANoe: send/receive CAN messages
    - Verify SWC behavior on target hardware
```

### 3.4 Common ARXML Conflicts You Will Debug

| Conflict | Cause | Fix |
|---|---|---|
| Schema version mismatch | Different AUTOSAR versions (R4.2 vs R4.3) | Align tool schema version or use migration script |
| Port interface not found | Supplier ARXML references type not in system description | Import missing type definition ARXML |
| Data type mismatch | `uint8` vs `uint16` on P-Port/R-Port | Align interface definition in one ARXML file |
| Runnable not mapped to task | SWC imported but OS configuration not updated | Manually assign runnable to OS Alarm in DaVinci |
| CRC mismatch on include | ARXML file modified outside DaVinci | Re-import clean ARXML, version control violation |

---

## 4. Vector DaVinci Toolchain

### 4.1 DaVinci Developer – Key Skills

- Create Application SWC from scratch
- Define Sender-Receiver and Client-Server interfaces
- Generate ARXML and export for system integration
- **Practice task:** Create an ACC_Controller SWC with:
  - R-Port: `LeadVehicleDistance` (float32)
  - R-Port: `EgoSpeed` (float32)
  - P-Port: `TargetDeceleration` (float32)
  - Client-Server: `DEM_SetEventStatus()`

### 4.2 DaVinci Configurator Pro – Configuration Checklist

```
□ EcuC: Set ECU name, PduCollection, buffer sizes
□ CanDrv: Configure CAN controllers and hardware registers
□ CanIf: Create HOH (Transmit/Receive) objects
□ PduR: Define routing paths from CanIf to COM
□ COM: Create I-PDUs, signals, and map to SWC interfaces
□ DCM: Configure DIDs (0x22), Routines (0x31), ECUReset (0x11)
□ DEM: Define DTC events and link to FIM
□ NvM: Map RAM mirrors to NvM blocks
□ OS: Configure tasks (BASIC/EXTENDED), alarms, counters
□ RTE: Generate after all BSW modules configured
```

### 4.3 DaVinci Key Shortcuts & Concepts

| Action | How |
|---|---|
| Import ARXML | File → Import AUTOSAR Description |
| Check consistency | Analysis → Check Consistency (run after every change) |
| Generate code | Project → Generate (CTRL+G) |
| View COM signal mapping | Open COM module → Signal-to-PDU view |
| Debug missing runnable | BSW Scheduler → View unassigned runnables |

---

## 5. Embedded C & 32-bit MCU Architectures

### 5.1 Infineon Aurix TriCore – Must Know

```
Architecture:
- Triple-core: TC0, TC1, TC2 (LOCKSTEP for safety)
- TriCore ISA: optimized for embedded control
- Memory: PFLASH, DFLASH (EEPROM emulation), PSRAM, DSRAM

Safety Features:
- SMPU (Safety Memory Protection Unit) – ASIL-D capability
- Watchdog Timer (WDT) – per-core and safety watchdog
- Cerberus (CSA) – CPU context save area for trap handling

Key Registers (integration-relevant):
- PORT.OUT: GPIO output control
- CAN_MOD: CAN module control
- STM (System Timer Module): used for AUTOSAR OS tick

Debugging:
- Lauterbach Trace32: cmm scripts, hardware breakpoints, trace
- Aurix DAP (Debug Access Protocol): JTAG alternative
```

### 5.2 Critical Embedded C Patterns for AUTOSAR

```c
/* volatile: use for hardware registers and ISR-modified variables */
volatile uint32_t *const CAN_Status = (uint32_t *)0xF0200000U;

/* const pointer to const register (MISRA compliant) */
const uint8_t * const pConfigData = &NvM_Block_0.data[0];

/* Struct packing for CAN signal layout */
#pragma pack(1)
typedef struct {
    uint8_t  SignalA  : 4;
    uint8_t  SignalB  : 4;
    uint16_t Distance : 12;
    uint16_t Speed    : 12;
} Can_AccFrame_t;
#pragma pack()

/* MISRA C:2012 compliant NULL check */
if (NULL_PTR != pBuffer) {
    (void)memcpy(pDest, pBuffer, length);
}

/* Safe division (MISRA Rule 15.5) */
static float32 SafeDivide(float32 num, float32 den) {
    float32 result = 0.0F;
    if (den > FLOAT_EPSILON) {
        result = num / den;
    }
    return result;
}
```

### 5.3 MISRA C:2012 – Top Rules for Integration Work

| Rule | Description | Why it matters |
|---|---|---|
| Rule 10.1 | Operands shall not be of inappropriate essential type | Prevents implicit type issues in signal packing |
| Rule 11.3 | No cast between pointer to object and pointer to different object | Safety for memory-mapped I/O |
| Rule 14.4 | The controlling expression of an if shall be essentially Boolean | Prevents `if(ptr)` instead of `if(ptr != NULL)` |
| Rule 15.5 | A function shall have a single point of exit | Enforced in ASIL-C/D code |
| Rule 17.7 | Return value of non-void function must be used | Prevents ignoring error codes |

---

## 6. ADAS Perception & Planning Pipelines

### 6.1 Sensor Processing Chain

```
CAMERA PIPELINE:
  Raw Sensor → ISP → Distortion Correction → Feature Extraction
      → Object Detection (CNN) → Object List (x, y, class, confidence)
      → Object Tracking (Kalman Filter) → Fusion Input

RADAR PIPELINE:
  TX Antenna → FMCW Signal → RX Antenna → FFT (Range/Velocity)
      → CFAR Detection → Point Cloud → Clustering → Object List
      → Velocity + Range + Angle → Fusion Input

SENSOR FUSION:
  Camera Objects + Radar Objects
      → Extended Kalman Filter (EKF) association
      → Fused Object List: (id, x, y, vx, vy, class, confidence)
      → Input to Planning Module
```

### 6.2 Planning FSM (What You Are Integrating)

```
ADAPTIVE CRUISE CONTROL FSM:

States:
  INACTIVE → ACTIVATING → ACTIVE → BRAKING → STANDBY → INACTIVE

Transitions:
  INACTIVE     → ACTIVATING  : Driver presses ACC button AND speed in range
  ACTIVATING   → ACTIVE      : Radar lock on lead vehicle OR free drive
  ACTIVE       → BRAKING     : TTC < threshold OR lead vehicle decelerating
  BRAKING      → ACTIVE      : Threat cleared
  ACTIVE       → STANDBY     : Driver brake override
  STANDBY      → INACTIVE    : Ignition cycle

Outputs from FSM:
  - Target_Speed (to VCU CAN message)
  - Deceleration_Request (to brake ECU via CAN)
  - ACC_Status (to cluster HMI via CAN)
```

### 6.3 Your Integration Role in ADAS

```
You are NOT writing the algorithm.
You ARE responsible for:

1. Receiving the ADAS SWC ARXML from algorithm team
2. Importing it into DaVinci – resolving all interface issues
3. Configuring the CAN COM stack so the SWC gets:
   - RadarObjectList_PDU from radar ECU
   - EgoSpeed_PDU from ABS ECU
4. Configuring the SWC output to:
   - Send TargetDeceleration_PDU to brake ECU
   - Send ACC_Status_PDU to cluster ECU
5. Setting correct OS task period (e.g., 20 ms cycle for ACC)
6. Testing on HIL: inject radar objects, verify brake commands
7. Debugging: if AEB fires when it shouldn't, trace from
   CAN frame → PDU → COM signal → SWC input → algorithm
```

---

## 7. ASPICE & Automotive Standards

### 7.1 ASPICE V-Model – Your Role Maps Here

```
                    SYS.1 Requirements
                   /                   \
          SYS.2 Architecture       SYS.5 System Test
         /                               \
    SWE.1 SW Req              SWE.6 SW Qualification Test
       /                                    \
  SWE.2 SW Architecture      SWE.5 SW Integration Test
     /                                          \
SWE.3 SW Detailed Design              SWE.4 SW Unit Verification
                \                       /
                  ── SWE.3 Implementation ──
                         (YOU ARE HERE)
```

### 7.2 What ASPICE Requires From You

| ASPICE Process | Your Deliverable |
|---|---|
| SWE.1 | Ensure your integration code maps to a software requirement ID |
| SWE.2 | Document which SWC connects to which BSW module (architecture) |
| SWE.3 | Write inline comments explaining non-obvious integration choices |
| SWE.4 | Unit test results for any functions you write |
| SWE.5 | Integration test evidence (CANoe logs, HIL reports) |
| SWE.6 | System-level test results with pass/fail against requirements |

### 7.3 Traceability Example

```
System Req (SYS-REQ-ACC-003):
  "The ACC system shall maintain a 2-second time gap to the lead vehicle"
         ↓
SW Req (SWE-REQ-ACC-012):
  "The ACC_Controller SWC shall read LeadDistance and EgoSpeed every 20 ms"
         ↓
Architecture (SWE-ARC-ACC-005):
  "ACC_Controller runnable mapped to OsTask_20ms"
         ↓
Implementation:
  Runnable: Rte_Runnable_ACC_Controller_20ms_Execute()
         ↓
Test (SWE-TC-ACC-012):
  "TC-ACC-003: Following Distance Maintenance – HIL test"
```

---

## 8. ISO 26262 Functional Safety

### 8.1 ASIL Classification Quick Reference

| ASIL | Severity | Probability | Controllability | Example |
|---|---|---|---|---|
| QM | Low | Any | Controllable | Climate display |
| A | S1 | P2 | C2 | Lane departure warning |
| B | S2 | P2 | C2 | ACC deceleration |
| C | S2 | P3 | C2 | LKA steering torque |
| D | S3 | P3 | C3 | AEB full braking |

### 8.2 Freedom from Interference

When an ASIL-D SWC (AEB) and a QM SWC (infotainment) share the same ECU:

```
OS Memory Protection (MPU):
- AEB SWC gets its own memory partition
- QM SWC cannot write to AEB partition
- Verified via: Memory Protection Unit configuration in AUTOSAR OS
- DaVinci: OsApplication → MemoryRegion → AccessRights

Timing Protection:
- AEB runnable has execution time budget (WCET)
- OS monitors: if QM task overruns, it is terminated before AEB affected
- DaVinci: OsTask → OsTaskExecutionBudget

Communication Protection:
- E2E (End-to-End) protection on safety-critical CAN messages
- CRC + Counter + Data ID per AUTOSAR E2E Library
```

### 8.3 Diagnostic Coverage Requirements

| ASIL | Fault Detection Coverage | Latent Fault Metric |
|---|---|---|
| A | 60% | 60% |
| B | 90% | 60% |
| C | 97% | 80% |
| D | 99% | 90% |

---

## 9. SIL/HIL Testing & Debugging

### 9.1 SIL Setup for ADAS Integration

```
PC-based simulation:
  - AUTOSAR code compiled for x86/x64
  - MCAL replaced by simulation stub (e.g., VRTA from Vector)
  - Sensor data injected via CANoe simulation node
  - Test script sends radar object list → SWC processes → verify output
  
Tools: Vector CANoe + CAPL scripts, dSPACE TargetLink, MATLAB/Simulink
Use case: Verify algorithm logic and AUTOSAR interfaces BEFORE hardware
```

### 9.2 HIL Setup for ADAS Integration

```
Real ECU on test bench:
  ┌─────────────┐        CAN/Eth       ┌────────────────────┐
  │  ADAS ECU   │◄────────────────────►│  HIL Simulator     │
  │ (Aurix MCU) │                      │  (dSPACE / Vector) │
  └─────────────┘                      │                    │
         │                             │  - Radar object sim│
         │ JTAG                        │  - Ego vehicle sim │
  ┌──────────────┐                     │  - Road simulation │
  │  Trace32     │                     └────────────────────┘
  │  Debugger    │
  └──────────────┘

Test flow:
  1. Load test scenario (e.g., cut-in at 30m)
  2. HIL sends CAN message: RadarObject_PDU
  3. ECU receives, SWC processes
  4. ECU sends: Decel_Request_PDU
  5. CANoe log captured, analyzed in CAPL
  6. Verdict: PASS/FAIL compared to expected value
```

### 9.3 Debugging Workflow on Real ECU

```
Scenario: ACC does not respond to lead vehicle on HIL

Step 1: Verify CAN frame is reaching ECU
  - CANoe trace: Is RadarObject_PDU visible on bus? ✓
  - CANoe trace: Is ECU acknowledging the frame? ✓

Step 2: Verify COM signal extraction
  - Trace32: Set breakpoint in Rte_Read_LeadVehicleDistance()
  - Inspect variable value: Is it 0? → COM signal mapping wrong

Step 3: Check PDU routing
  - DaVinci: Verify PduR routing table maps CanIf → COM correctly
  - Rebuild and re-flash

Step 4: Verify SWC runnable execution
  - Trace32: Set breakpoint in ACC_Controller runnable
  - Check if it is being called at 20 ms interval
  - Check OS task allocation: runnable mapped to correct task?

Step 5: Check algorithm output
  - Inspect Rte_Write_TargetDeceleration() variable
  - Correct value present but not on CAN?
  - Check COM transmit trigger mode (Event vs Periodic)
```

---

## 10. Middleware – SOME-IP, DDS, RTPS

### 10.1 SOME-IP (Service-Oriented Middleware over IP)

```
Used in: AUTOSAR Adaptive, Ethernet-based communication

Key Concepts:
  - Service: A group of methods and events (like a REST API for ECUs)
  - Method: Request/Response (Client calls a function on Server)
  - Event: Publisher/Subscriber (one-to-many notification)
  - Service Discovery (SD): Announces/finds services on the network

SOME-IP message structure:
  [Service ID][Method ID][Length][Client ID][Session ID][Protocol Ver][Interface Ver][Msg Type][Return Code][Payload]

Example in ADAS:
  - Radar ECU publishes: "ObjectList" event (10 Hz)
  - ADAS Fusion ECU subscribes to: "ObjectList"
  - Camera ECU exposes: "GetCalibrationData()" method
```

### 10.2 DDS (Data Distribution Service)

```
Used in: ROS2, autonomous driving platforms, AUTOSAR Adaptive

Key Concepts:
  - Topic: named data channel (e.g., "radar/objects")
  - Publisher: produces data on a topic
  - Subscriber: consumes data from a topic
  - QoS: Quality of Service (reliability, latency, history)

Relevance to ADAS:
  - Sensor fusion middleware in upper-layer ADAS stacks
  - Used in NVIDIA DRIVE, Mobileye EyeQ platforms
  - Enables flexible, low-latency sensor data sharing
```

---

## 11. Agile/Scrum in Automotive

### 11.1 Scrum Ceremonies – What You Attend as a Senior IC

| Ceremony | Frequency | Your Contribution |
|---|---|---|
| Sprint Planning | Every 2 weeks | Estimate ARXML integration tasks in story points |
| Daily Stand-up | Daily | Report: completed yesterday, plan today, blockers |
| Sprint Review | Every 2 weeks | Demo integrated feature running on HIL |
| Retrospective | Every 2 weeks | Suggest process improvements (e.g., CI pipeline) |
| Backlog Refinement | Weekly | Break down "Integrate Radar SWC" into subtasks |

### 11.2 CI/CD in Automotive Embedded Development

```
Typical Pipeline (Automotive-adapted):
  1. Developer pushes code to Git (Gerrit/GitLab)
  2. Static Analysis job triggered (PC-lint / Polyspace)
  3. SIL build job: AUTOSAR stack compiled for host
  4. SIL test job: CAPL-based test scripts executed
  5. Code coverage report generated
  6. If all pass → merge to develop branch
  7. Nightly: HIL test farm runs regression suite
  8. Weekly: Full system integration test report
  
Tools: Jenkins, GitLab CI, Polarion (requirements), DOORS (ALM)
```

---

## 12. STAR Interview Answers – 20 Questions

> **STAR Format:** Situation → Task → Action → Result

---

### Q1. Tell me about a time you integrated an ARXML from a customer or supplier into your project.

**S:** During a Tier-1 ADAS project for a premium OEM, we received a large ARXML package containing a new radar processing SWC from a European sensor supplier. The ARXML was created in DaVinci Developer R4.3, while our project used R4.2.

**T:** My task was to integrate this SWC into the ECU project without any guidance from the supplier (they were unavailable for 2 weeks). I had to resolve all schema differences and ensure the SWC's CAN interfaces were correctly wired to the vehicle's object list PDU.

**A:** I first used DaVinci's schema migration tool to upconvert our project, then imported the supplier ARXML. I identified three port interface mismatches using the Consistency Check tool. I corrected the data types in a local ARXML overlay file, preserving the supplier's original. I then configured the PduR routing path and the COM signal layout per the OEM's CAN DBC file.

**R:** Integration was completed 3 days ahead of the supplier's return. The SWC ran at the correct 20 ms cycle on HIL pass and all 14 integration test cases passed in the first run. This became our team's reference workflow document for third-party ARXML integration.

---

### Q2. Describe a time you debugged a critical issue on embedded hardware with no obvious root cause.

**S:** During system integration of an AEB feature on an Aurix TC277 ECU, the system was triggering false braking events at highway speeds. The issue was not reproducible in SIL and only appeared on HIL with live CAN traffic injected.

**T:** I was the lead integration engineer and needed to find the root cause before a critical review with the OEM customer in 48 hours.

**A:** I attached a Lauterbach Trace32 debugger to the ECU and set a conditional hardware breakpoint on the AEB trigger command. When it fired, I walked back through the call stack. I found that the COM receive indication callback was being called with a corrupted signal value (0xFFFF) at 100 Hz instead of 10 Hz. Further investigation with the CAN trace showed a second CAN node was transmitting the same PDU ID. Cross-referencing the CAN DBC and network topology diagram confirmed a node ID conflict introduced in the latest network topology update.

**R:** I corrected the CAN node ID in the ARXML network description and regenerated the CanIf configuration. The false trigger was eliminated. I also added a COM signal range check to the SWC defensive layer to prevent recurrence, which was subsequently added as a standard practice for the project.

---

### Q3. Tell me about a time you had to work with cross-functional teams to align on requirements and delivery.

**S:** On a LKA (Lane Keeping Assist) program, the algorithm team estimated 6 weeks for their SWC delivery, but the system integration milestone was in 4 weeks. This created a schedule conflict that risked missing the OEM gating review.

**T:** As the integration engineer, I was responsible for ensuring the full integration test suite was ready by the milestone date.

**A:** I organized a cross-functional meeting with the algorithm, systems, and testing teams. I proposed a split delivery: a stub SWC with fixed output values in week 2 to unblock my integration and HIL setup work, followed by the real SWC in week 5 for functional testing. I created a detailed interface document in Polarion specifying exactly what the stub needed to expose. I also worked with the test team to design test cases that could run on the stub immediately.

**R:** We met the gating review milestone. The hardware integration, BSW configuration, and HIL rig setup were all validated 2 weeks before the algorithm SWC arrived. When the real SWC was dropped in, functional testing started immediately with zero interface rework. The OEM commended our phased integration approach.

---

### Q4. Describe a time you improved software quality through a process change.

**S:** Our project had recurring ARXML regeneration errors in CI because developers were manually editing generated files to "fix" issues quickly, then committing them. This caused the next generation step to overwrite manual changes and break the build.

**T:** As a senior engineer, I was asked to permanently eliminate this issue.

**A:** I investigated all occurrences of manual edits in the Git history and categorized each root cause. Most were due to incorrect DaVinci configurations that developers avoided correcting due to time pressure. I created a "DaVinci Hygiene" rule document, added a pre-commit hook that detected edits to files named `*_Cfg.c` / `*_Lcfg.c` (all generated files), and blocked commits if such edits were present. I also held a 1-hour knowledge sharing session on correct configuration practices in DaVinci.

**R:** In the following 3 months, zero manual edits to generated files were committed. CI build stability improved from 72% to 96%. The pre-commit hook was adopted by two other projects in the program.

---

### Q5. Tell me about a time you had to validate an ADAS algorithm on a real ECU with no algorithm developer support.

**S:** On a forward collision warning (FCW) feature, the algorithm developer left the company one week after SWC delivery. Two weeks later, during HIL testing, we discovered the FCW warning was firing 800 ms later than the requirement specified.

**T:** I had to independently debug and either fix the timing issue or provide a root cause analysis for the algorithm team's replacement developer.

**A:** I started by reviewing the SWC ARXML – specifically the runnable timing requirements specification. The ARXML showed the runnable was specified as a 40 ms cycle, but it had been mapped to our 50 ms OS task during integration (my earlier configuration). I verified this in the DaVinci OS configuration. I corrected the task period to 40 ms, regenerated, and reflashed. The warning timing improved to 640 ms. The remaining 140 ms was within the algorithm's own processing latency. I documented the full timing chain (sensor → PDU → SWC input → algorithm compute → output PDU → display) as a timing budget breakdown for the new developer.

**R:** The requirement was met within tolerance. The timing budget document I created became the reference for all future FCW timing compliance arguments.

---

### Q6. Describe a time you applied functional safety concepts in your integration work.

**S:** During integration of the AEB SWC (ASIL-D) on a shared ECU that also hosted a ASIL-QM infotainment audio SWC, a functional safety audit identified a potential freedom-from-interference violation.

**T:** I was tasked with implementing spatial, temporal, and communication isolation between the two SWCs to satisfy ISO 26262 Part 6 requirements.

**A:** For spatial isolation, I configured the Aurix SMPU (Safety Memory Protection Unit) in DaVinci's OS configuration to give the ASIL-D AEB SWC its own protected memory region that the QM SWC had no write access to. For temporal isolation, I set an execution time budget for all QM tasks in the AUTOSAR OS, ensuring a QM task overrun could not starve the AEB periodic runnable. For communication isolation, I enabled E2E (End-to-End) protection on all safety-relevant CAN signals using the AUTOSAR E2E library, adding CRC and counter to the AEB command PDU.

**R:** The safety audit finding was closed within the same sprint. The configuration was reviewed and approved by the functional safety manager and was included in the Safety Case documentation.

---

### Q7. Tell me about a time you led a testing or validation activity.

**S:** On a BSM (Blind Spot Monitoring) project, I was asked to lead all HIL validation activities for the feature. The team had no existing HIL test framework for this specific radar-based feature.

**T:** I had to design, implement, and execute the complete HIL test suite from scratch in 6 weeks.

**A:** I first reviewed the SWE.1 software requirements to derive test cases. I defined 28 test cases and documented them in Polarion with full traceability to requirements. I then wrote CAPL test scripts in CANoe that injected 3D radar object scenarios (position, velocity, confidence) via CAN. I set up the dSPACE HIL rig with the vehicle model and defined the test execution sequence. I trained two junior engineers on the framework so they could run regression tests independently.

**R:** All 28 test cases were executed in 4 weeks. 24 passed on first run. 4 failures led to genuine software defects, all fixed before the gating review. The CAPL framework was reused on the next project with minor modifications, saving an estimated 3 weeks of test framework development.

---

### Q8. Describe a time you maintained requirements traceability under pressure.

**S:** During a rushed release sprint, there was pressure to skip updating the traceability matrix in Polarion to save time, as a critical DTC issue had been fixed overnight.

**T:** As the senior engineer, I had to balance delivery pressure with ASPICE compliance, knowing an audit was scheduled 3 weeks later.

**A:** I explained to the project manager that skipping traceability would create a non-conformance finding in the upcoming ASPICE audit, which would require significantly more rework to resolve than the 2 hours needed to update Polarion now. I offered to do the update myself rather than delay the delivery. I linked the defect fix to the affected test cases, updated the test status, and re-ran the impacted test cases that night, updating the evidence artifacts.

**R:** The delivery was not delayed. The ASPICE audit 3 weeks later found no traceability gaps in that area. The auditor specifically noted the quality of the test evidence as a strength.

---

### Q9. Tell me about a time you used static analysis or code review to prevent a defect.

**S:** During a code review of a newly integrated CAN signal handler in a radar SWC, I noticed a MISRA Rule 10.1 violation where a raw hardware-register value was being used directly in an arithmetic expression without casting.

**T:** I needed to document the issue clearly enough that the developer understood the risk, not just the rule violation.

**A:** In the code review comment, I explained specifically: the raw register value could have its upper bits set in certain MCU power states, causing the arithmetic result to overflow a uint8 buffer, potentially corrupting adjacent memory. I provided a corrected code snippet using an explicit mask and cast. I also ran PC-lint analysis on the entire SWC and found 3 additional violations of a similar nature, which I included in the review.

**R:** All 4 issues were fixed. In testing, we later discovered the MCU did indeed have its upper bits set during startup, confirming the overflow would have occurred. The code review prevented a potential field defect. The PC-lint run profile was added to the CI pipeline as a result.

---

### Q10. Describe your experience with SIL and HIL environments.

**S:** On a multi-feature ADAS program covering ACC, AEB, LDW, and BSM, I was responsible for both SIL and HIL integration testing across all four features.

**T:** My task was to ensure each feature had test coverage at both SIL and HIL levels before the system-level test phase.

**A:** For SIL, I used Vector CANoe with VRTA (Virtual Real-Time OS) to run the full AUTOSAR stack on a PC. CAPL scripts injected sensor data and verified SWC outputs without any hardware. This allowed early algorithm testing within 2 days of SWC delivery. For HIL, I used a dSPACE SCALEXIO rig connected to the real Aurix-based ADAS ECU. I developed parametric scenario scripts that swept TTC values, object distances, and sensor confidence levels across a matrix of conditions. I also used Trace32 during HIL sessions to inspect live memory values during scenario execution to catch intermittent issues.

**R:** SIL testing caught 7 interface bugs before hardware was available, saving approximately 2 weeks of HIL debug time. HIL testing found 3 additional issues related to timing and CAN message scheduling that SIL could not replicate. All features passed their HIL exit criteria on schedule.

---

### Q11. Tell me about a time you integrated sensor hardware (camera, radar, lidar).

**S:** On an active safety program for a European OEM, I integrated a continental ARS540D radar ECU as a new sensor input to the ADAS fusion ECU via Automotive Ethernet (100BASE-T1).

**T:** My task was to configure the AUTOSAR communication stack on the fusion ECU to receive radar object lists published by the radar ECU via SOME-IP, extract the object signals, and make them available to the fusion algorithm SWC via the RTE.

**A:** I configured the AUTOSAR SoAd (Socket Adapter), SD (Service Discovery), and SOME-IP transformer modules in DaVinci Configurator. I then defined the radar service subscription in the SD configuration and mapped the received SOME-IP payload to PDUs in the PduR, and then to COM signals. I created a wrapper SWC that converted raw radar object data into the standard `FusionInput_ObjectList` interface expected by the algorithm SWC. I validated the integration using Wireshark on the Ethernet tap to verify the SOME-IP service discovery handshake and message content.

**R:** First object data was received by the fusion SWC within 1 week. The Wireshark captures were archived as integration evidence. The configuration template I created was reused for the lidar integration 2 months later.

---

### Q12. Describe a time you handled a change in requirements late in the development cycle.

**S:** During system integration testing, the OEM issued an ECR (Engineering Change Request) requiring the ACC time gap setting to be stored in non-volatile memory so it persists across ignition cycles. This was 3 weeks before the final software release.

**T:** I had to implement the NvM storage of the ACC setting without destabilizing the existing release build.

**A:** I assessed the impact: NvM block configuration in DaVinci, a new NvM read on startup in the ACC SWC init runnable, and a write-on-change trigger when the setting is updated. I raised the change in Jira, got it approved by the change board, and created a branch. I added the NvM block in DaVinci, regenerated the NvM and RTE configurations, and modified the ACC SWC to call `Rte_Call_NvM_Write()` on setting update and `Rte_Call_NvM_Read()` on init. I wrote regression test cases specifically for this new behavior.

**R:** The feature was implemented, tested, and merged in 4 days. The 3 regression test cases all passed. The change was delivered ahead of the release freeze date with full Polarion traceability and an updated architectural note.

---

### Q13. Tell me about a time you worked in an Agile/Scrum environment on an automotive project.

**S:** On a 12-month ADAS active safety program, our team of 8 engineers ran 2-week Agile sprints, adapted for ASPICE compliance.

**T:** As a senior engineer, I was responsible for breaking down large ARXML integration epics into sprint-sized tasks and estimating effort accurately for sprint planning.

**A:** I created a decomposition template: each ARXML integration story was broken into: import & consistency check (2 pts), BSW configuration (3 pts), code generation & build (1 pt), SIL test execution (3 pts), Polarion traceability update (1 pt). This gave reliable 10-point sizing for standard integrations. I also maintained a sprint velocity chart and flagged sprint risks in standups early, rather than at review. When a supplier ARXML arrived late, I had a pre-identified substitute task ready to swap in to keep the sprint fully utilized.

**R:** Our team achieved an average sprint velocity of 42 points over 22 sprints against a forecast of 40. Zero sprints ended with unplanned items carried over. The decomposition template was adopted by two other Agile teams in the program.

---

### Q14. Tell me about a challenge you faced with configuration management in a large AUTOSAR project.

**S:** On a complex ECU with 6 SWCs integrated from 3 different teams, conflicting DaVinci project checkouts were causing generated files to differ between developer machines, leading to "works on my machine" build failures in CI.

**T:** I was asked to establish a single-source-of-truth configuration management strategy for all DaVinci artifacts.

**A:** I defined a rule: the DaVinci `.dpa` project file and all ARXML files are stored in Git. Generated files (`*_Cfg.c`, `*_Lcfg.c`, `Rte.c`) are excluded via `.gitignore` and always regenerated by the CI pipeline. I wrote a Jenkins pipeline stage that pulled the ARXML, ran DaVinci in headless mode to generate, and then compiled. I documented the workflow and ran a mandatory team training session.

**R:** CI build failures from generated file conflicts dropped to zero within 2 sprints. Onboarding new team members went from a 2-day setup process to 30 minutes because the pipeline handled all generation automatically.

---

### Q15. Describe a time you had to explain a complex technical issue to a non-technical stakeholder.

**S:** The project manager asked why the integration of a supplier radar SWC was taking 2 weeks instead of the estimated 3 days. There was pressure from the OEM program manager for an explanation.

**T:** I had to clearly explain the root cause (a supplier ARXML schema version conflict) and provide a realistic recovery plan without using AUTOSAR-specific jargon.

**A:** I used a building analogy: "The supplier sent us a blueprint (ARXML) drawn to a different architectural standard than our construction office uses. Before we can build, we have to translate the entire blueprint. We have now completed the translation, but we need to verify every room (SWC port) connects correctly before we can start construction (integration). We are 60% through verification." I presented a day-by-day recovery plan on a single slide and highlighted the two tasks on the critical path.

**R:** The PM was satisfied with the explanation and communicated it effectively to the OEM. No escalation occurred. The integration was completed 1 day ahead of my revised estimate.

---

### Q16. Tell me about a time you mentored a junior engineer.

**S:** A junior engineer joined our team mid-project with theoretical AUTOSAR knowledge but no DaVinci hands-on experience. They were assigned to configure the NvM stack for a new feature.

**T:** I was asked to bring them up to speed within 2 weeks without significantly impacting my own integration deliverables.

**A:** I designed a structured 5-day hands-on program: Day 1 – AUTOSAR architecture walkthrough on a whiteboard with our actual project; Days 2–3 – pair programming in DaVinci on a non-critical module (watchdog configuration); Days 4–5 – independent NvM configuration with me available for review. I reviewed their work daily using a checklist and gave written feedback via code review comments so they had a reference for the future.

**R:** The junior engineer completed the NvM configuration independently by day 8. It passed the consistency check first time. They became the team's NvM configuration owner within 2 months. I received positive feedback from the team lead for the structured approach.

---

### Q17. Describe a time you contributed to a code review that prevented a safety issue.

**S:** During review of a safety-critical SWC for highway pilot, I noticed the runnable was modifying a shared global buffer that was also read by a second runnable in a different OS partition without any data access protection.

**T:** This was a potential ASIL-D safety issue – unprotected shared data between different safety levels.

**A:** I raised the finding in the review with a detailed explanation: if both runnables ran in a preemption window, the reading runnable could see a partially written buffer containing a mix of old and new data – a data race. I proposed two solutions: use AUTOSAR's inter-runnable variable mechanism via the RTE (safe option, longer implementation time) or protect the critical section using `SuspendAllInterrupts/ResumeAllInterrupts` for the write (faster short-term solution). I flagged this as a safety-relevant finding and involved the functional safety manager in the decision.

**R:** The RTE inter-runnable variable solution was chosen and implemented. The finding was formally documented in the safety case as a resolved hazard. The functional safety manager credited the code review process with preventing a potential field recall scenario.

---

### Q18. Tell me about a time you met a tight deadline without compromising quality.

**S:** Two days before a system integration milestone, a new software build failed to boot on the ECU due to an OS stack overflow in a newly added task, introduced in the latest sprint.

**T:** I had to find and fix the root cause in under 24 hours while ensuring the fix did not break any previously passed test cases.

**A:** I used Trace32 to read the OS stack pattern fill values and identify the exact task that overflowed. I then profiled the task's worst-case stack usage by running all test scenarios and monitoring peak stack depth. The task had been given 512 bytes but required 1024 bytes due to a deeply nested function in the ADAS algorithm. I increased the stack size in DaVinci OS configuration, regenerated, rebuilt, and ran the full regression suite overnight using the automated CANoe test suite.

**R:** ECU booted correctly with the new configuration. All 44 regression test cases passed. The milestone was met on time. I also added a stack headroom check (< 80% stack usage) as a standard CI post-build check to prevent recurrence.

---

### Q19. Describe a time you identified and resolved an intermittent issue in a production build.

**S:** In the final system test phase, an intermittent CAN bus error was corrupting the AEB output message approximately once every 45 minutes. It was not reproducible on demand and no one had found the cause in 3 weeks.

**T:** I was asked to take ownership of the investigation.

**A:** I set up a long-running CANoe logging session with pre-trigger and post-trigger capture around the AEB message ID. After 4 days of captures, I collected 6 occurrences. Analysis showed all occurrences happened within 2 ms of a specific NvM write operation. I hypothesized the NvM write was causing a transient MCU performance spike that delayed the CAN TX buffer flush. I confirmed this using Trace32 cycle-accurate tracing: the NvM write held a hardware mutex for 1.8 ms, which delayed the OS scheduler from executing the CAN TX task. The fix was to defer the NvM write to a background low-priority task using an NvM write request flag, keeping it off the main control cycle.

**R:** After the fix, the issue did not recur in 200+ hours of continuous HIL operation. The fix was merged and the defect closed. I presented the investigation methodology as a case study at a project-wide lessons learned session.

---

### Q20. Why do you want to work at Aptiv and in this specific role?

**S:** I've spent 10 years building embedded ADAS integration expertise – from BSW configuration to HIL validation to safety-critical SW delivery. The work I'm most proud of is always at the hardware-software boundary: the moment an algorithm you've integrated runs correctly on a real ECU for the first time.

**T:** I'm looking for a role that maximizes that type of contribution – hands-on, high-ownership, production-grade integration work.

**A:** Aptiv's position at the center of active safety – working on systems that prevent real accidents – directly aligns with what I want my work to mean. The technical depth of this role, specifically the combination of AUTOSAR ARXML integration, real-hardware debugging, and ADAS domain ownership, is precisely where my skills are strongest and where I can deliver value from day one.

**R:** I see this role as both the best use of the experience I've built and the right place to continue growing into system architecture leadership. Aptiv's scale – working across multiple vehicle programs and OEM relationships – gives me the breadth I can't get on a single-program project. That combination is exactly what I'm looking for.

---

## 13. 30-Day Study Roadmap

```
WEEK 1: AUTOSAR & DaVinci Foundation
  Day 1–2 : Review AUTOSAR Classic layered architecture
             Read: AUTOSAR Classic Platform Overview PDF (autosar.org)
  Day 3–4 : DaVinci Developer – create an ACC_Controller SWC
             Define 2 R-Ports, 1 P-Port, 1 Client-Server port
  Day 5–6 : DaVinci Configurator – import your ARXML, configure COM + PduR
  Day 7   : Generate code, review Rte.c and Com_Cfg.c output

WEEK 2: MCU & Embedded C
  Day 8–9 : Aurix TriCore architecture – memory map, safety features, SMPU
             Read: Infineon TC3xx User Manual (Chapters: CPU, CAN, OS)
  Day 10–11: Embedded C – write MISRA-compliant CAN signal handler
              Practice: struct packing, volatile registers, safe arithmetic
  Day 12–13: Trace32 basics – load symbols, set breakpoints, inspect memory
  Day 14  : Debug exercise: find a simulated "signal not received" issue

WEEK 3: ADAS Domain & Standards
  Day 15–16: ADAS perception pipeline – camera, radar, fusion basics
              Watch: Coursera Self-Driving Cars Specialization (Module 1–2)
  Day 17–18: ISO 26262 – ASIL classification, freedom from interference, E2E
  Day 19–20: ASPICE V-model – requirement traceability exercise
              Create: Requirement → Architecture → Code → Test trace for ACC
  Day 21  : Write 5 STAR answers using your real project experience

WEEK 4: Integration Scenarios & Interview Prep
  Day 22–23: SIL/HIL workflow – set up CANoe simulation node, write CAPL test
  Day 24–25: SOME-IP basics – read Vector SOME-IP whitepaper
              Practice: Describe a SOME-IP service subscription in your own words
  Day 26–27: Review all 20 STAR answers. Record yourself answering 5 of them.
  Day 28  : Mock technical interview: explain ARXML integration workflow
             on a whiteboard without notes
  Day 29  : Prepare 5 questions to ask Aptiv interviewers:
             - "What is the current AUTOSAR version used across your programs?"
             - "What is the ratio of customer-supplied vs inhouse ARXML?"
             - "What is the HIL toolchain (dSPACE / Vector)?"
             - "How is functional safety coverage tracked across sprints?"
             - "What does the integration-to-algorithm-developer ratio look like?"
  Day 30  : Full review. Confidence check on all topics. Rest.
```

---

## Quick Reference Card – Interview Day

| Topic | Key Thing to Say |
|---|---|
| AUTOSAR | "ARXML import, BSW config in DaVinci Configurator, generated RTE is never hand-edited" |
| DaVinci | "Daily tool – Consistency Check before every commit, headless generation in CI" |
| Aurix | "TriCore, SMPU for spatial isolation, Trace32 for on-target debug" |
| ADAS | "I integrate the SWC – I own the interface, the OS mapping, and the CAN wire-up" |
| ISO 26262 | "ASIL-D means E2E on CAN, memory partition, task execution budget" |
| ASPICE | "Every code line traces to a requirement, every test traces to a requirement" |
| Debugging | "Reproduce → Isolate on CAN → Trace to SWC input → Check OS mapping" |
| Agile | "Break down by interface, stub early, validate incrementally" |

---

*Document Version: 1.0 | Prepared: 25 April 2026 | Role: Aptiv Senior ADAS Algorithm Integration Engineer*
