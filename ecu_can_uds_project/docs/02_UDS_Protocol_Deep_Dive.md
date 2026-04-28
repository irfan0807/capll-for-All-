# UDS (Unified Diagnostic Services) – Complete Protocol Guide

## 1. What is UDS?

UDS (**ISO 14229**) is a diagnostic communication protocol used in automotive ECUs. It defines how a **diagnostic tester** (e.g., CANalyzer, INCA, workshop tool) communicates with an **ECU over the vehicle network** (CAN, LIN, Ethernet, FlexRay).

```
  ┌──────────────────────┐        Request (SID + Data)       ┌─────────────────┐
  │   Diagnostic Tester  │ ─────────────────────────────────► │    ECU (Server) │
  │  (CANalyzer / Python)│ ◄───────────────────────────────── │                 │
  └──────────────────────┘        Response (0x40+SID / NRC)  └─────────────────┘
```

UDS follows a **client-server model**:
- **Client** = Tester (sends requests)
- **Server** = ECU (processes and responds)

---

## 2. UDS Transport Layer – ISO-TP (ISO 15765-2)

UDS messages > 8 bytes use **ISO-TP** segmentation over CAN:

```
Single Frame (SF):   ┌────┬────────────────────────────┐
                     │0xNN│       Data (up to 7 bytes) │   DLC ≤ 8
                     └────┴────────────────────────────┘

First Frame (FF):    ┌────┬────┬────────────────────────┐
                     │0x1N│0xNN│  Data bytes 1-6        │   Starts multi-frame
                     └────┴────┴────────────────────────┘

Consecutive Frame:   ┌────┬────────────────────────────┐
                     │0x2N│       Data (7 bytes)        │   N = sequence 1-F
                     └────┴────────────────────────────┘

Flow Control (FC):   ┌────┬────┬────┐
                     │0x30│ BS │STmin│   ECU tells tester: "send more"
                     └────┴────┴────┘
```

**Standard CAN IDs for UDS:**
- Tester → ECU: `0x7DF` (functional), `0x7E0`–`0x7E7` (physical)
- ECU → Tester: `0x7E8`–`0x7EF`

---

## 3. UDS Service IDs (SID) – Complete Reference

### Diagnostic Session Control Services

| SID  | Service Name                        | Sub-Function | Direction |
|------|-------------------------------------|--------------|-----------|
| 0x10 | DiagnosticSessionControl            | Yes          | Request   |
| 0x11 | ECUReset                            | Yes          | Request   |
| 0x27 | SecurityAccess                      | Yes          | Request   |
| 0x28 | CommunicationControl                | Yes          | Request   |
| 0x29 | Authentication                      | Yes          | Request   |
| 0x3E | TesterPresent                       | Yes          | Request   |
| 0x83 | AccessTimingParameter               | Yes          | Request   |
| 0x84 | SecuredDataTransmission             | No           | Request   |
| 0x85 | ControlDTCSetting                   | Yes          | Request   |
| 0x86 | ResponseOnEvent                     | Yes          | Request   |
| 0x87 | LinkControl                         | Yes          | Request   |

### Data Transmission Services

| SID  | Service Name                        |
|------|-------------------------------------|
| 0x22 | ReadDataByIdentifier (RDBI)         |
| 0x23 | ReadMemoryByAddress                 |
| 0x24 | ReadScalingDataByIdentifier         |
| 0x2A | ReadDataByPeriodicIdentifier        |
| 0x2C | DynamicallyDefineDataIdentifier     |
| 0x2E | WriteDataByIdentifier (WDBI)        |
| 0x3D | WriteMemoryByAddress                |

### Diagnostic Trouble Code Services

| SID  | Service Name                        |
|------|-------------------------------------|
| 0x14 | ClearDiagnosticInformation          |
| 0x19 | ReadDTCInformation                  |

### Upload/Download Services

| SID  | Service Name                        |
|------|-------------------------------------|
| 0x34 | RequestDownload                     |
| 0x35 | RequestUpload                       |
| 0x36 | TransferData                        |
| 0x37 | RequestTransferExit                 |
| 0x38 | RequestFileTransfer                 |

### Routine Control

| SID  | Service Name                        |
|------|-------------------------------------|
| 0x31 | RoutineControl                      |

---

## 4. Diagnostic Sessions (0x10)

```
┌──────────────────────────────────────────────────────────┐
│                  Session State Machine                    │
│                                                          │
│    ┌─────────────────────────────────────────────────┐   │
│    │           Default Session (0x01)                │   │
│    │ • Read DTCs • Read data • TesterPresent         │   │
│    └───────────────────────┬──── 0x10 01 ────────────┘   │
│                            │                              │
│              ┌─────────────┼──────────────┐              │
│              ▼             ▼              ▼              │
│    ┌──────────────┐ ┌───────────────┐ ┌────────────┐    │
│    │  Programming │ │   Extended    │ │  Supplier  │    │
│    │  Session     │ │   Diagnostic  │ │  Specific  │    │
│    │  (0x02)      │ │   (0x03)      │ │  (0x40+)   │    │
│    │ • Flash prog │ │ • Write DID   │ └────────────┘    │
│    │ • Security   │ │ • Actuators   │                   │
│    └──────────────┘ └───────────────┘                   │
└──────────────────────────────────────────────────────────┘
```

**Session timeout**: ECU returns to Default Session if no `TesterPresent (0x3E)` within P3 timeout (typically 5 seconds).

---

## 5. Security Access (0x27) – Challenge-Response

This is the **seed/key mechanism** to protect sensitive ECU functions:

```
Step 1 – Request Seed:
  Tester  → ECU:   27 01              (Request Seed for level 0x01)
  ECU    → Tester: 67 01 A3 F2 11 C4  (Seed: 0xA3F211C4)

Step 2 – Calculate Key:
  Key = f(Seed, SecretAlgorithm)   ← implemented in ECU and tester
  Example: Key = Seed XOR 0x5A5A5A5A = 0xF9A84BCE

Step 3 – Send Key:
  Tester  → ECU:   27 02 F9 A8 4B CE  (Send key for level 0x02)
  ECU    → Tester: 67 02              (Access granted!)
```

**Negative Response Codes (NRC) for Security Access:**

| NRC  | Meaning |
|------|---------|
| 0x35 | invalidKey |
| 0x36 | exceededNumberOfAttempts |
| 0x37 | requiredTimeDelayNotExpired |

---

## 6. Read Data By Identifier – 0x22 (RDBI)

Most commonly used service for reading ECU data:

```
Request:  22 F1 90           → Read VIN (DID 0xF190)
Response: 62 F1 90 57 30 4C 5A 5A 5A 32 33 34 35 36 37 38 39 30 31
          └──── 0x62 = 0x22 + 0x40 (positive response)
                   └── DID echoed back
                           └── VIN: "W0LZZZ234567890 1"

Request:  22 F1 86 F1 87 F1 89      → Read multiple DIDs at once
Response: 62 F1 86 [data] F1 87 [data] F1 89 [data]
```

### Common Standard DIDs

| DID    | Name                          |
|--------|-------------------------------|
| 0xF186 | ActiveDiagnosticSessionDID    |
| 0xF187 | VehicleManufacturerSparePartNumber |
| 0xF18A | SystemSupplierIdentifierDID   |
| 0xF18B | ECUManufacturingDateDID       |
| 0xF18C | ECUSerialNumberDID            |
| 0xF190 | VINDataIdentifier             |
| 0xF191 | VehicleManufacturerECUHardwareNumberDID |
| 0xF192 | SystemSupplierECUHardwareNumberDID |
| 0xF193 | SystemSupplierECUHardwareVersionNumberDID |
| 0xF194 | SystemSupplierECUSoftwareNumberDID |
| 0xF195 | SystemSupplierECUSoftwareVersionNumberDID |

---

## 7. DTC (Diagnostic Trouble Code) – 0x19

### DTC Structure

```
    ┌──────────────────────────────────────────┐
    │         DTC = 3 Bytes (ISO 14229-1)      │
    │                                          │
    │  Byte 1: [Group Prefix 2bit][12bit code] │
    │  Byte 2: [fault path continued]          │
    │  Byte 3: Status Byte                     │
    └──────────────────────────────────────────┘

Status Byte Bits:
  Bit 0: testFailed              (DTC is currently failing)
  Bit 1: testFailedThisMonitoringCycle
  Bit 2: pendingDTC              (failed in current or last cycle)
  Bit 3: confirmedDTC            (failed in 2+ consecutive cycles)
  Bit 4: testNotCompletedSinceLastClear
  Bit 5: testFailedSinceLastClear
  Bit 6: testNotCompletedThisMonitoringCycle
  Bit 7: warningIndicatorRequested (MIL lamp)
```

### Common ReadDTCInformation Sub-functions

| Sub-fn | Name | Usage |
|--------|------|-------|
| 0x01 | reportNumberOfDTCByStatusMask | Count DTCs |
| 0x02 | reportDTCByStatusMask | List all DTCs |
| 0x03 | reportDTCSnapshotIdentification | Freeze frame list |
| 0x04 | reportDTCSnapshotRecordByDTCNumber | Freeze frame data |
| 0x06 | reportDTCExtendedDataRecordByDTCNumber | Extended data |
| 0x0A | reportSupportedDTC | All ECU-supported DTCs |

---

## 8. ECU Reset Service (0x11)

```
Request:  11 01   → Hard Reset (ECU power cycle)
Response: 51 01   → Positive response

Request:  11 02   → Key Off/On Reset
Response: 51 02

Request:  11 03   → Soft Reset (software restart only)
Response: 51 03
```

---

## 9. Negative Response Codes (NRC) – Complete Table

| NRC  | Mnemonic | Meaning |
|------|----------|---------|
| 0x10 | generalReject | Request rejected |
| 0x11 | serviceNotSupported | SID not implemented |
| 0x12 | subFunctionNotSupported | Sub-function unknown |
| 0x13 | incorrectMessageLengthOrInvalidFormat | Wrong length |
| 0x14 | responseTooLong | Response > buffer |
| 0x21 | busyRepeatRequest | ECU busy, retry |
| 0x22 | conditionsNotCorrect | Pre-conditions not met |
| 0x24 | requestSequenceError | Wrong sequence |
| 0x25 | noResponseFromSubnetComponent | Sub-ECU timeout |
| 0x26 | failurePreventsExecutionOfRequestedAction | Action blocked |
| 0x31 | requestOutOfRange | DID/address out of range |
| 0x33 | securityAccessDenied | Not unlocked |
| 0x35 | invalidKey | Wrong seed-key |
| 0x36 | exceededNumberOfAttempts | Too many fails |
| 0x37 | requiredTimeDelayNotExpired | Must wait |
| 0x70 | uploadDownloadNotAccepted | Transfer rejected |
| 0x71 | transferDataSuspended | Transfer aborted |
| 0x72 | generalProgrammingFailure | Flash write fail |
| 0x73 | wrongBlockSequenceCounter | Wrong block number |
| 0x78 | requestCorrectlyReceivedResponsePending | ECU still processing |
| 0x7E | subFunctionNotSupportedInActiveSession | Not in this session |
| 0x7F | serviceNotSupportedInActiveSession | SID locked to session |

---

## 10. Full UDS Transaction – Engine RPM Read

```
Step-by-step with timing:

T=0ms   Tester  ──► ECU:    [0x7DF] 02 22 F4 0C
                                    ││ ││ └──── DID: 0xF40C (Engine RPM)
                                    ││ └─────── SID: ReadDataByIdentifier
                                    └┴───────── Length: 2 bytes follow

T=15ms  ECU     ──► Tester: [0x7E8] 04 62 F4 0C 08 FC
                                    ││ ││ └─────── DID echo
                                    ││ └─────────── Positive response (0x22+0x40)
                                    └┴──────────── Length: 4 bytes follow
                                                        └──── Data: 0x08FC = 2300 RPM
```

---

## 11. UDS Flash Programming Flow

```
1. Enter Programming Session
   Tester → ECU: 10 02
   ECU → Tester: 50 02

2. Security Access (unlock flash)
   Tester → ECU: 27 03        (request seed - programming level)
   ECU → Tester: 67 03 [seed]
   Tester → ECU: 27 04 [key]
   ECU → Tester: 67 04

3. Erase Flash (RoutineControl)
   Tester → ECU: 31 01 FF 00 [address] [size]
   ECU → Tester: 71 01 FF 00 01 (erase started)
   ... wait for completion ...
   ECU → Tester: 71 01 FF 00 02 (erase complete)

4. Request Download
   Tester → ECU: 34 00 44 [memAddr 4 bytes] [memSize 4 bytes]
   ECU → Tester: 74 20 [maxBlockLen 2 bytes]

5. Transfer Data (loop)
   Tester → ECU: 36 01 [data block 1]   (blockSeqCounter=1)
   ECU → Tester: 76 01
   Tester → ECU: 36 02 [data block 2]   (blockSeqCounter=2)
   ECU → Tester: 76 02
   ... repeat for all blocks ...

6. Request Transfer Exit
   Tester → ECU: 37
   ECU → Tester: 77

7. Check Programming Integrity (RoutineControl)
   Tester → ECU: 31 01 02 02 [CRC16/CRC32]
   ECU → Tester: 71 01 02 02 [result]

8. ECU Reset
   Tester → ECU: 11 01
   ECU → Tester: 51 01
```
