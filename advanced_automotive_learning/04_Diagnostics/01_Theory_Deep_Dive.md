# DIAGNOSTICS (UDS / OBD-II / DTC) — DEEP DIVE
## Module 4 of 7 | advanced_automotive_learning

---

## 1. THE PURPOSE OF VEHICLE DIAGNOSTICS

Every ECU in a vehicle must be:
- **Testable** by the manufacturing line (EOL test)
- **Diagnosable** by the workshop (scan tool)
- **Updateable** with new software (OTA/in-shop flash)
- **Monitorable** by the vehicle system itself (fault detection)

This is achieved through two layered standards:
- **OBD-II** (ISO 15031): External standardized diagnostics (emissions, scan tools)
- **UDS** (ISO 14229): Full manufacturer-specific diagnostics (all services)

```
DIAGNOSTIC ECOSYSTEM:
 ┌────────────────────────────────────────────────────────┐
 │                    VEHICLE                              │
 │  ┌─────────────┐     ┌────────────┐   ┌─────────────┐ │
 │  │   BCM ECU   │     │ Engine ECU │   │   ADAS ECU  │ │
 │  │  DEM: DTCs  │     │  DEM: DTCs │   │  DEM: DTCs  │ │
 │  │  DCM: UDS   │     │  DCM: UDS  │   │  DCM: UDS   │ │
 │  └──────┬──────┘     └─────┬──────┘   └──────┬──────┘ │
 │         │                  │                  │        │
 │  ────────────────────CAN/Ethernet──────────────────── │
 │         │                                             │
 │  ┌──────▼──────────────────────────────────────────┐  │
 │  │             DoIP GATEWAY / OBD PORT             │  │
 │  └──────────────────────────────────────────────────┘  │
 └────────────────────────────────────────────────────────┘
          │ DoIP / CAN TP
  ┌───────▼────────┐
  │  Diagnostic    │
  │  Tester / OBD  │
  │  Scan Tool     │
  └────────────────┘
```

---

## 2. UDS — UNIFIED DIAGNOSTIC SERVICES (ISO 14229)

### 2.1 Session Model

UDS has three diagnostic sessions that control which services are available:

```
SESSION STATE MACHINE:

  Power on → Default Session (0x01)
               │
               │ 10 02 (SessionControl, Programming)
               ▼
         Programming Session (0x02)
         - Allows: flash download, security access, write NVM
         - Requires: security access (0x27) first
               │
               │ 10 01 (back to default) or timeout
               ▼
  Default Session (0x01) ◄───────────────────────────────┐
               │                                          │
               │ 10 03 (SessionControl, Extended)         │
               ▼                                          │
          Extended Session (0x03)                         │
          - Allows: all Default + write DIDs, activate    │
            functions, change parameters                  │
          - Example: enable/disable DTC storage          │
               │                                          │
               │ Timeout or 10 01                         └──────────
               ▼
         Back to Default

TESTER PRESENT (0x3E 00):
  Must be sent every P2 seconds to keep non-default session alive.
  If not sent: ECU returns to Default session after S3 timer (~5s).
```

### 2.2 Complete UDS Service Table

| SID | Service Name | Session | Key Detail |
|-----|--------------|---------|------------|
| 0x10 | DiagnosticSessionControl | All | Req: [10 xx] Resp: [50 xx P2hi P2lo P2*hi P2*lo] |
| 0x11 | ECUReset | All | 01=Hard, 02=KeyOffOn, 03=Soft |
| 0x14 | ClearDiagnosticInformation | Default/Extended | [14 FF FF FF] = clear all DTCs |
| 0x19 | ReadDTCInformation | All | Subfunction 0x02 = all DTCs by status |
| 0x22 | ReadDataByIdentifier | All | [22 F1 90] = read VIN |
| 0x23 | ReadMemoryByAddress | Extended | Raw memory read |
| 0x24 | ReadScalingDataByIdentifier | All | DID scaling factor |
| 0x27 | SecurityAccess | Prog/Extended | Request seed → send key → access granted |
| 0x28 | CommunicationControl | Extended | Enable/disable TX/RX on bus |
| 0x29 | Authentication | All | PKI-based auth (R20-11+) |
| 0x2A | ReadDataByPeriodId | Extended | Cyclic DID reading |
| 0x2C | DynamicallyDefineDataIdentifier | Extended | Define custom DID on-the-fly |
| 0x2E | WriteDataByIdentifier | Prog/Extended | [2E F1 90 VIN...] = write VIN |
| 0x2F | InputOutputControlById | Extended | Override actuator / sensor value |
| 0x31 | RoutineControl | All (sub-function dependent) | 01=Start, 02=Stop, 03=RequestResult |
| 0x34 | RequestDownload | Programming | Begin flash transfer |
| 0x35 | RequestUpload | Programming | Begin read from ECU memory |
| 0x36 | TransferData | Programming | Data block transfer |
| 0x37 | RequestTransferExit | Programming | End of transfer |
| 0x38 | RequestFileTransfer | Programming | File-based transfer |
| 0x3D | WriteMemoryByAddress | Extended | Raw memory write |
| 0x3E | TesterPresent | All | Keep non-default session alive |
| 0x83 | AccessTimingParameter | Extended | Read/write P2, P2* timers |
| 0x84 | SecuredDataTransmission | All | Encrypted service (with SecOC) |
| 0x85 | ControlDTCSettings | Extended | Enable/disable DTC storage |
| 0x86 | ResponseOnEvent | Extended | Event-driven response |
| 0x87 | LinkControl | Extended | Change baud rate |

### 2.3 Security Access (0x27) Deep Dive

```
SECURITY ACCESS PROTOCOL:
  Purpose: Prevent unauthorized clients from performing sensitive operations
           (flash, write DIDs, control actuators)

  Algorithm (typical, OEM-specific):
    Key = f(Seed, ConstantK)
    Common implementations: XOR, SHA-256 HMAC, AES-128

  Sequence:
  ┌─────────────────────────────────────────────────────────┐
  │  Tester           ECU                                   │
  │    │── [27 01] ──►│  RequestSeed (AccessLevel=01)       │
  │    │◄─ [67 01 S1 S2 S3 S4] ─│  Seed = 4 random bytes   │
  │    │                          │                          │
  │    │  Key = Seed XOR 0xABCD1234 (example)               │
  │    │── [27 02 K1 K2 K3 K4] ──►│  SendKey                │
  │    │◄─ [67 02] ───────────────│  Access Granted          │
  │                                │                          │
  │  WRONG KEY:                    │                          │
  │    │── [27 02 XX XX XX XX] ──►│                          │
  │    │◄─ [7F 27 35] ─────────────│  NRC 35 = InvalidKey    │
  │                                │                          │
  │  After 3 wrong keys: NRC 36 (exceededNumberOfAttempts)  │
  │  ECU locks out for T_Lockout (typically 10 seconds)     │
  └─────────────────────────────────────────────────────────┘
```

---

## 3. DTC — DIAGNOSTIC TROUBLE CODES

### 3.1 DTC Structure

```
DTC FORMAT (ISO 14229):
  3 bytes = DTC identifier
  
  Byte 0: Group (2 bits) + Position (6 bits)
  ─────────────────────────────────────────
  Bits 7-6:  00 = Powertrain (P)
             01 = Chassis (C)
             10 = Body (B)
             11 = Network (U)
  Bits 5-0:  Sub-group identifier

  Byte 1-2: Specific fault identifier
  
  Example: P0300 = random misfire
    B in OBD-II format: P0300
    In bytes: [00][03][00]
    Group: 00 = Powertrain
```

### 3.2 DTC Status Byte (Every DTC has 8 status bits)

```
DTC STATUS BYTE (bit 7 to bit 0):
  Bit 7: warningIndicatorRequested (MIL lamp on/off)
  Bit 6: testNotCompletedThisMonitoringCycle
  Bit 5: testFailedSinceLastClear
  Bit 4: testNotCompletedSinceLastClear
  Bit 3: confirmedDTC (fault confirmed ≥ N occurrences)
  Bit 2: pendingDTC (fault detected in current cycle)
  Bit 1: testFailed (current cycle, current moment)
  Bit 0: testFailedSinceLastClear (at least once since last clear)

EXAMPLE STATUS BYTE 0x09:
  Binary: 0000 1001
  Bit 3 = confirmedDTC = 1 (confirmed)
  Bit 0 = testFailedSinceLastClear = 1
  → This is a confirmed, persistent fault

Read all DTCs: [19 02 FF] → all DTCs regardless of status
Read confirmed: [19 02 08] → only confirmed DTCs (bit 3 = 1)
```

### 3.3 DEM — Diagnostic Event Manager (AUTOSAR)

```
AUTOSAR DEM ARCHITECTURE:

Application SWC (sensor, algorithm)
  │ Dem_SetEventStatus(DEM_EVENT_ID_FCW_FAILURE, DEM_EVENT_STATUS_FAILED)
  ▼
DEM (Diagnostic Event Manager):
  - Manages event debouncing (counter/time-based)
  - Updates DTC status byte
  - Stores DTC in NVM (freeze frame, extended data)
  - Triggers MIL lamp (if warningIndicatorRequested)
  ▼
DCM (Diagnostic Communication Manager):
  - Exposes DTCs via UDS 0x19 service
  - Handles DTC clear (0x14)
  - Controls DTC setting (0x85)
  ▼
NvM:
  - Persistent DTC storage (survives power cycle)
  - Stores: DTC identifier + status + freeze frame (sensor values at fault time)

DEBOUNCING:
  Counter-based: DEM_DEBOUNCE_COUNTER_BASED
    Failed threshold = 10 (fault set after 10 consecutive fails)
    Pass threshold = -5 (fault healed after 5 consecutive passes)
  Time-based: DEM_DEBOUNCE_TIME_BASED
    Failed time = 200ms (fault set after 200ms continuous fail)
```

---

## 4. OBD-II OVERVIEW

### 4.1 OBD-II vs UDS

```
OBD-II                              UDS
─────────────────────────────────────────────────────
ISO 15031 / SAE J1979              ISO 14229
Mandatory by regulation (all OEMs)  OEM-specific
Limited service set (Mode 01-0A)    Full service set (0x10-0x87)
Read emissions-related data only    Read/write any data
CAN SID: 0x7DF (functional)        Physical address (0x7D0, etc.)
Response SID = request + 0x40      Same
Standardized PIDs (F190, etc.)     OEM-defined DIDs
```

### 4.2 OBD-II Services (Modes)

```
MODE  HEX   SERVICE                     EXAMPLE
──────────────────────────────────────────────────────────────
01    0x01  Show current data           PID 0x0C = Engine RPM
02    0x02  Show freeze frame data      Values at DTC storage
03    0x03  Show stored DTCs            P0300, P0171 etc.
04    0x04  Clear DTCs and reset        Clear all emission DTCs
05    0x05  Test O2 sensor results      (ISO 9141-2 / KWP only)
06    0x06  Show test results           Component monitor results
07    0x07  Show pending DTCs           Currently failing, not confirmed
08    0x08  Special control mode        (OEM-specific)
09    0x09  Request vehicle info        VIN, calibration ID
0A    0x0A  Show permanent DTCs         Cannot be cleared by Mode 04

IMPORTANT PIDs:
  0x00 = Supported PIDs [01-20] (bit field)
  0x01 = Monitor status since DTCs cleared (readiness flags)
  0x04 = Engine load
  0x05 = Coolant temperature (°C - 40)
  0x0C = Engine RPM (A*256+B / 4)
  0x0D = Vehicle speed (km/h)
  0x0F = Intake air temperature
  0x11 = Throttle position
  0x2F = Fuel level input
  0x41 = Monitor status this driving cycle (8 readiness monitors)
```

---

## 5. DCM — DIAGNOSTIC COMMUNICATION MANAGER (AUTOSAR)

```
DCM RESPONSIBILITIES:
  1. Session management: track current session, enforce session rules
  2. Security access: manage seed/key exchange, lockout counting
  3. Service routing: dispatch UDS service bytes to handlers
  4. Response building: assemble positive/negative responses
  5. Timing: enforce P2, P2*, S3 timers
  6. Transport: communicate via CanTp (CAN) or SoAd (Ethernet)

DCM HANDLERS (generated in ARXML):
  0x10 → DcmDspSessionControl()
  0x22 → DcmDspReadDataByIdentifier()
  0x27 → DcmDspSecurityAccess()
  0x19 → DcmDspReadDtcInformation()
  ...

TIMING PARAMETERS:
  P2:  50ms   - ECU must respond within P2 ms or send NRC 0x78
  P2*: 5000ms - After NRC 0x78, final response within P2* ms
  S3:  5000ms - Non-default session expires if no TesterPresent for S3 ms
```

---

## 6. INTERVIEW Q&A

**Q1: What is the difference between UDS and OBD-II?**
> OBD-II (ISO 15031) is a regulated, standardized diagnostic interface for emissions monitoring accessible by any generic scan tool. UDS (ISO 14229) is a manufacturer-specific comprehensive protocol supporting all operations: reading/writing any DID, security access, flashing, parameter changes. OBD-II is a limited subset; UDS is the full toolkit. OBD-II is mandatory; UDS is OEM-defined.

**Q2: Explain the DTC status byte bits you care about most in testing.**
> Bit 3 (confirmedDTC): most important — this is what triggers MIL and what workshops see. Bit 0 (testFailedSinceLastClear): shows if fault has ever occurred since last DTC clear — useful for intermittent faults. Bit 2 (pendingDTC): fault detected in current drive cycle but not yet confirmed — useful for early fault detection. In testing, I verify: inject fault → check bit 0 and 2 set → inject fault N times → check bit 3 set → clear with 0x14 → verify all bits 0.

**Q3: What is the NRC 0x78 and how do you handle it?**
> NRC 0x78 = requestCorrectlyReceived-ResponsePending. The ECU received the request and is processing it, but needs more time than P2 allows. It sends [7F SID 0x78] as an interim response. The tester must wait up to P2* (5 seconds typically) for the final response. Multiple 0x78 responses are possible. In test automation: always implement 0x78 handling — check if first response is [7F xx 78] and if so, keep waiting for the real response. Forgetting 0x78 handling causes false test failures for long-duration operations like flash or checksum verification.

**Q4: What happens if security access fails 3 times?**
> NRC 0x36 (exceededNumberOfAttempts) is returned. The ECU starts a lockout timer (typically 10 seconds, configured in DcmDspSecurityAccess). During lockout, any SecurityAccess request returns NRC 0x37 (requiredTimeDelayNotExpired). After lockout, attempts reset. In testing, always verify lockout behavior: 3 wrong keys → NRC 0x36 → delay → NRC 0x37 on immediate retry → wait for lockout → successful access with correct key.

**Q5: What is DEM debouncing and why does it matter in testing?**
> Debouncing prevents a single transient fault from immediately setting a DTC. Counter-based: DEM requires N consecutive failed evaluations before setting DTC (typical: N=10 for monitoring at 10ms → 100ms of continuous failure). Time-based: fault must persist for T ms. In testing, this means: injecting a fault once is not enough to verify DTC storage — you must inject the fault continuously for the full debouncing window. Test scripts must simulate sustained faults, not instantaneous ones.

---

*Next: [02_STAR_Answers.md](02_STAR_Answers.md)*
