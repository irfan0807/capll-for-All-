# UDS (ISO 14229) — Complete Study Guide
## All Services, Frame Formats, Sessions, Error Codes | April 2026

---

## Chapter 1 — What is UDS?

**Unified Diagnostic Services (UDS)** is the automotive ECU diagnostic protocol defined in **ISO 14229**. It operates over CAN, LIN, Ethernet (DoIP), FlexRay, and K-Line transport layers. UDS defines how a diagnostic tester (workshop tool, EOL station, or test bench) communicates with an ECU to:

- Read fault codes (DTCs)
- Read live data (sensor values, calibration)
- Write data (configuration, VIN, variant coding)
- Flash new software (ECU programming)
- Perform actuator tests (routine control)
- Control communication and security

### Transport Layer Stack

```
ISO 14229 (UDS Application Layer — services 0x10 to 0xBA)
        ↕
ISO 15765-2 (CAN Transport Protocol — TP / ISO-TP)
        ↕
ISO 11898 (CAN Physical Layer)

For Ethernet:
ISO 14229 UDS
        ↕
ISO 13400 (DoIP — Diagnostics over Internet Protocol)
        ↕
TCP/IP + Ethernet
```

### ISO-TP Frame Types

| Frame Type | ID | Description |
|------------|----|-------------|
| Single Frame (SF) | 0x0_ | Payload ≤ 7 bytes. PCI: nibble=0, length nibble |
| First Frame (FF) | 0x1_ | First frame of multi-frame message. PCI: nibble=1, 12-bit length |
| Consecutive Frame (CF) | 0x2_ | Follow-on data. PCI: nibble=2, sequence counter |
| Flow Control (FC) | 0x3_ | Receiver controls transmission. PCI: nibble=3 |

**Flow Control flags:** 0x30 = ContinueToSend, 0x31 = Wait, 0x32 = Overflow

**Example — Reading DTC (single frame):**
```
Request:  7A0#03 19 02 09      (3 bytes: SID=19, subFunc=02, statusMask=09)
Response: 7A8#09 59 02 09 C0 00 01 03   (first 9 bytes — multi-frame if more DTCs)
```

---

## Chapter 2 — Diagnostic Sessions (Service 0x10)

### 2.1 Session Types

| Sub-function | Name | Hex | Purpose |
|-------------|------|-----|---------|
| 0x01 | defaultSession | `10 01` | Normal operation. Basic read, clear |
| 0x02 | programmingSession | `10 02` | ECU flashing. Full access with security |
| 0x03 | extendedDiagnosticSession | `10 03` | Advanced diagnostics, write data, routine |
| 0x04 | safetySystemDiagnosticSession | `10 04` | Safety-critical ECUs (rare) |
| 0x40–0x5F | vehicleManufacturerSpecific | varies | OEM-defined sessions |
| 0x60–0x7E | systemSupplierSpecific | varies | Tier-1 defined sessions |

### 2.2 Session Transitions

```
Default → Extended: 10 03 → positive response 50 03 → now in extended
Default → Programming: 10 01 → Security Access 27 01/02 → 10 02
Extended → Default: 10 01 (or timeout — P3 client timer)
```

### 2.3 Timing Parameters (ISO 14229)

| Parameter | Typical Value | Description |
|-----------|--------------|-------------|
| P2 Client | 50ms | Timeout waiting for ECU response |
| P2* Client | 5000ms | Timeout for slow response (after 0x78 NRC) |
| P2 Server | 50ms | ECU must respond within this time |
| P3 Client | 5000ms | Tester Present interval (session keepalive) |
| S3 Client | 5000ms | Session timeout (ECU falls back to default) |

### 2.4 Negative Response for Session Change

```
NRC 0x22 (conditionsNotCorrect): ECU in wrong state for requested session
NRC 0x25 (requestOutOfRange is wrong here — actually 0x25 = invalidKey)
NRC 0x7E (subFunctionNotSupportedInActiveSession): session doesn't support this sub-function
NRC 0x7F (serviceNotSupportedInActiveSession): service not available in this session
```

---

## Chapter 3 — Security Access (Service 0x27)

### 3.1 Purpose

Protect sensitive operations (write calibration, flash ECU, activate actuators) from unauthorised access.

### 3.2 Flow

```
1. Tester → ECU:  27 01         (requestSeed, level 1)
2. ECU → Tester:  67 01 [seed4 bytes]   (sendSeed)
3. Tester computes key: Key = f(Seed, Algorithm, SecretConst)
4. Tester → ECU:  27 02 [key4 bytes]    (sendKey)
5. ECU validates:  67 02 (positive) OR 7F 27 35 (invalidKey)
```

### 3.3 Security Levels (typical OEM)

| Level | Access Code | Usage |
|-------|-------------|-------|
| 0x01/0x02 | Extended diag key | Routine control, actuator tests |
| 0x03/0x04 | EOL/calibration key | Write calibration data, variant coding |
| 0x05/0x06 | Engineering key | Full read/write, bypass limits |
| 0x11/0x12 | Programming key | ECU flash (reprogramming) |

### 3.4 Key Calculation (Common Algorithms)

**Algorithm A (XOR):** `Key = Seed XOR SecretConst`
**Algorithm B (Shift-XOR):** `Key = (Seed << 1) XOR Mask`
**Algorithm C (CRC32):** `Key = CRC32(Seed + Salt)`

### 3.5 NRC Codes for Security Access

| NRC | Code | Meaning |
|-----|------|---------|
| requestSequenceError | 0x24 | Sent key without requesting seed first |
| invalidKey | 0x35 | Key computation mismatch |
| exceededNumberOfAttempts | 0x36 | Too many failed key attempts (lockout) |
| requiredTimeDelayNotExpired | 0x37 | Must wait before retry after lockout |

---

## Chapter 4 — DTC Services (0x14 and 0x19)

### 4.1 Clear DTC — Service 0x14

```
Request:  14 FF FF FF     (clear all DTCs)
Request:  14 00 42 67     (clear specific group)
Response: 54              (positive — ClearDiagnosticInformation)
NRC 0x22: conditions not correct (engine running, vehicle moving)
```

### 4.2 Read DTC — Service 0x19 Sub-functions

| Sub-function | Name | Request Example | Description |
|-------------|------|-----------------|-------------|
| 0x01 | reportNumberOfDTCByStatusMask | `19 01 09` | Count of DTCs matching mask |
| 0x02 | reportDTCByStatusMask | `19 02 09` | List DTCs matching status mask |
| 0x03 | reportDTCSnapshotIdentification | `19 03` | List available freeze frames |
| 0x04 | reportDTCSnapshotRecordByDTCNumber | `19 04 C0 00 01 01` | Freeze frame for specific DTC |
| 0x06 | reportDTCExtendedDataRecordByDTCNumber | `19 06 C0 00 01 01` | Extended data for DTC |
| 0x07 | reportNumberOfDTCBySeverityMaskRecord | `19 07 08 09` | Count by severity + status |
| 0x08 | reportDTCBySeverityMaskRecord | `19 08 08 09` | DTCs by severity + status |
| 0x09 | reportSeverityInformationOfDTC | `19 09 C0 00 01` | Severity info for specific DTC |
| 0x0A | reportSupportedDTC | `19 0A` | All DTCs supported by ECU |
| 0x0B | reportFirstTestFailedDTC | `19 0B` | First DTC that failed since clear |
| 0x0C | reportFirstConfirmedDTC | `19 0C` | First confirmed DTC |
| 0x0D | reportMostRecentTestFailedDTC | `19 0D` | Most recent test-failed DTC |
| 0x0E | reportMostRecentConfirmedDTC | `19 0E` | Most recent confirmed DTC |
| 0x0F | reportMirrorMemoryDTCByStatusMask | `19 0F 09` | DTCs in mirror memory |
| 0x13 | reportUserDefMemoryDTCByStatusMask | `19 13 01 09` | User-defined memory DTCs |
| 0x14 | reportUserDefMemoryDTCSnapshotRecordByDTCNumber | `19 14` | User memory freeze frame |
| 0x15 | reportUserDefMemoryDTCExtDataRecordByDTCNumber | `19 15` | User memory extended data |
| 0x17 | reportDTCFaultDetectionCounter | `19 17` | Pre-confirmed DTCs (counter 1–127) |
| 0x18 | reportDTCWithPermanentStatus | `19 18` | Permanent DTCs (can't be cleared) |
| 0x19 | reportDTCExtDataRecordByRecordNumber | `19 19 01` | Extended data by record number |
| 0x42 | reportWWHOBDDTCByMaskRecord | `19 42 09` | WWH-OBD DTCs |

### 4.3 DTC Status Byte (ISO 14229)

```
Bit 7: warningIndicatorRequested
Bit 6: testNotCompletedThisMonitoringCycle
Bit 5: testFailedSinceLastClear
Bit 4: testNotCompletedSinceLastClear
Bit 3: confirmedDTC
Bit 2: pendingDTC
Bit 1: testFailedThisMonitoringCycle (since power cycle)
Bit 0: testFailed (current monitoring result)
```

Common status masks:
- `0x09` = testFailed (bit0) + confirmedDTC (bit3) → most common
- `0x0F` = all "failure" bits
- `0xFF` = all DTCs regardless of status
- `0x08` = confirmed only

### 4.4 DTC Severity Byte

```
0x20 = maintenanceOnly
0x40 = checkAtNextHalt
0x80 = checkImmediately
```

### 4.5 Freeze Frame Data (Snapshot)

Freeze frame captures ECU sensor values at the moment a DTC was set.
Common freeze frame data IDs:

| DID | Typical Content |
|-----|----------------|
| 0xF400 | Engine speed at DTC set |
| 0xF401 | Vehicle speed at DTC set |
| 0xF402 | Ambient temperature |
| 0xF403 | Odometer value |
| 0xF404 | Ignition cycles since DTC set |
| 0xF405 | Warm-up cycles since DTC clear |

---

## Chapter 5 — Read/Write Data By Identifier (0x22 / 0x2E)

### 5.1 Read Data By Identifier — Service 0x22

```
Request:  22 [DID high] [DID low]
Response: 62 [DID high] [DID low] [data bytes]

Example:  22 F1 10    → Read ECU Software Version
Response: 62 F1 10 "V2.14.01.00"
```

Multiple DIDs in one request (ISO 14229-1 allows multi-DID read):
```
Request:  22 F1 10 F1 89 F1 8C
Response: 62 F1 10 [data1] F1 89 [data2] F1 8C [data3]
```

### 5.2 Standardised DID Ranges (ISO 14229)

| Range | Owner | Description |
|-------|-------|-------------|
| 0x0000–0x00FF | OBD DIDs | Emissions, OBD-II |
| 0xF100–0xF1FF | Vehicle Manufacturer | VIN, ECU HW/SW versions |
| 0xF200–0xF2FF | OBD | System/test monitor data |
| 0xF300–0xF3FF | Vehicle Manufacturer | Stored data records |
| 0xF400–0xF4FF | ISO/SAE | Freeze frame data |
| 0xF500–0xF5FF | Vehicle Manufacturer | |
| 0xF600–0xFEFF | System Supplier | |
| 0xFF00–0xFFFF | ISOSAEReserved | |

### 5.3 Critical Standard DIDs

| DID | Name | Content |
|-----|------|---------|
| 0xF186 | activeSession | Current diagnostic session ID |
| 0xF187 | vehicleManufacturerSparePartNumber | Part number |
| 0xF188 | vehicleManufacturerECUSoftwareNumber | SW part number |
| 0xF189 | vehicleManufacturerECUSoftwareVersionNumber | SW version |
| 0xF18A | systemSupplierIdentifier | Tier-1 supplier code |
| 0xF18B | ECUManufacturingDate | Date of production |
| 0xF18C | ECUSerialNumber | Unique ECU serial |
| 0xF190 | VIN | 17-character Vehicle ID Number |
| 0xF191 | vehicleManufacturerECUHardwareNumber | HW part number |
| 0xF192 | systemSupplierECUHardwareNumber | Supplier HW number |
| 0xF193 | systemSupplierECUHardwareVersionNumber | Supplier HW version |
| 0xF194 | systemSupplierECUSoftwareNumber | Supplier SW number |
| 0xF195 | systemSupplierECUSoftwareVersionNumber | Supplier SW version |
| 0xF197 | vehicleManufacturerVehicleType | Vehicle type code |
| 0xF198 | applicationSoftwareFingerprint | Last programmed by |
| 0xF199 | applicationDataFingerprint | Last data programmed by |
| 0xF19D | programmedState | 0=not programmed, 1=programmed |
| 0xF19E | calDataODX | Calibration data ODX identifier |
| 0xF1A0 | unlockedStatus | Which security levels unlocked |

### 5.4 Write Data By Identifier — Service 0x2E

```
Request:  2E [DID high] [DID low] [data bytes]
Response: 6E [DID high] [DID low]
NRC 0x31: requestOutOfRange (DID not writable)
NRC 0x22: conditionsNotCorrect (wrong session, security not passed)
NRC 0x33: securityAccessDenied (security access required first)
```

Common write scenarios:
- Write VIN: `2E F1 90 [17 ASCII bytes]`
- Write variant code: `2E [OEM DID] [code byte]`
- Write customer configuration: `2E [DID] [config bytes]`

---

## Chapter 6 — ECU Reset (Service 0x11)

| Sub-function | Name | Hex | Description |
|-------------|------|-----|-------------|
| 0x01 | hardReset | `11 01` | Full power cycle simulation |
| 0x02 | keyOffOnReset | `11 02` | Ignition OFF → ON simulation |
| 0x03 | softReset | `11 03` | Software restart (no NVM clear) |
| 0x04–0x3F | ISO reserved | | |
| 0x40–0x5F | vehicleManufacturerSpecific | | |
| 0x60–0x7E | systemSupplierSpecific | | |

### Response Timing

After `11 01`: ECU must respond BEFORE resetting (positive response 0x51), then reset.
Reset completion time varies: 50ms (soft) to 5000ms (hard with NVM operations).

### NRC for Reset

- `0x22 conditionsNotCorrect`: vehicle moving, safety state prevents reset
- `0x25 requestSequenceError`: some ECUs require security access before hard reset

---

## Chapter 7 — Routine Control (Service 0x31)

### 7.1 Sub-functions

| Sub-function | Name | Description |
|-------------|------|-------------|
| 0x01 | startRoutine | Begin execution |
| 0x02 | stopRoutine | Halt execution |
| 0x03 | requestRoutineResults | Read outcome |

### 7.2 Format

```
Request:  31 01 [RID high] [RID low] [optional params]
Response: 71 01 [RID high] [RID low] [optional status/results]
```

### 7.3 Important Routine IDs (ISO and OEM)

| RID | Name | Usage |
|-----|------|-------|
| 0x0202 | vehicleSpeedSensorCalibration | Calibrate VSS |
| 0xF000 | deactivateLocalDiagnostic | Suppress internal monitoring |
| 0xFF00 | eraseMemory | Erase ECU flash (during programming) |
| 0xFF01 | checkProgrammingDependencies | Verify SW compatibility |
| 0xFF02 | eraseMirrorMemoryDTCs | Clear mirror memory |
| OEM defined | initiateReset | Trigger specific reset type |
| OEM defined | selfTest | Run ECU self-test, report result |
| OEM defined | actuatorTest | Drive relay/motor/valve |
| OEM defined | sensorCalibration | Calibrate offset/gain |
| OEM defined | nvmReadback | Verify written NVM data |

### 7.4 NRC for Routine Control

- `0x22`: Conditions not correct (engine must be off for erase)
- `0x24`: Request sequence error (start before checking earlier routine result)
- `0x31`: Request out of range (RID not supported)

---

## Chapter 8 — Communication Control (Service 0x28)

### 8.1 Purpose

Control which messages an ECU transmits/receives during diagnostic operations.
Used during programming to prevent communication interference.

### 8.2 Sub-functions

| Sub-function | Name | Hex | Description |
|-------------|------|-----|-------------|
| 0x00 | enableRxAndTx | `28 00 01` | Resume normal comms |
| 0x01 | enableRxDisableTx | `28 01 01` | Listen but don't transmit |
| 0x02 | disableRxEnableTx | `28 02 01` | Transmit but don't listen |
| 0x03 | disableRxAndTx | `28 03 01` | Full communication shutdown |
| 0x04 | enableRxAndDisableTxWithEnhancedAddressInfo | `28 04 01 [nodeID]` | Selective disable |
| 0x05 | enableRxAndTxWithEnhancedAddressInfo | `28 05 01 [nodeID]` | Selective enable |

### 8.3 Communication Type Byte

```
Bit 3-2: networkNumber (which CAN bus)
Bit 1-0: communicationType
  01 = normalCommunicationMessages
  02 = nmCommunicationMessages
  03 = networkManagementCommunicationMessages
```

---

## Chapter 9 — ECU Programming Sequence (Services 0x34/0x36/0x37)

### 9.1 Full Flash Sequence

```
Step 1:  10 03            → Enter Extended Session
Step 2:  27 01            → Request seed (programming unlock)
Step 3:  27 02 [key]      → Send key
Step 4:  10 02            → Enter Programming Session
Step 5:  27 11            → Request seed (programming level)
Step 6:  27 12 [key]      → Send key (programming level)
Step 7:  28 03 01         → Disable Rx/Tx (comms control)
Step 8:  31 01 FF 00      → Erase memory (routine)
Step 9:  34 00 44 [addr 4 bytes] [size 4 bytes] → RequestDownload
Step 10: 74 20 [maxBlockLen 2-4 bytes] → positive response with block size
Step 11: 36 01 [256 bytes data]  → TransferData block 1
Step 12: 36 02 [256 bytes data]  → TransferData block 2
 ... continue for all blocks ...
Step 13: 37               → RequestTransferExit
Step 14: 31 01 FF 01      → Check programming dependencies
Step 15: 28 00 01         → Enable Rx/Tx
Step 16: 11 01            → Hard Reset (activate new SW)
```

### 9.2 Service 0x34 — Request Download

```
Request:  34 [dataFormatIdentifier] [addressAndLengthFormatIdentifier]
              [memoryAddress N bytes] [memorySize N bytes]
Response: 74 [maxBlockLengthAndLengthFormatIdentifier] [maxBlockLength]

dataFormatIdentifier: 0x00=no compression, 0x11=OEM compress
addressAndLengthFormatIdentifier: 0x44 = 4-byte address + 4-byte size
```

### 9.3 Service 0x36 — Transfer Data

```
Request:  36 [blockSequenceCounter] [data bytes]
Response: 76 [blockSequenceCounter]
Counter: 01→02→...→FF→00→01 (wraps)
NRC 0x72: uploadDownloadNotAccepted
NRC 0x73: transferDataSuspended
```

### 9.4 Service 0x37 — Request Transfer Exit

```
Request:  37 [optional transfer parameter record]
Response: 77
```

---

## Chapter 10 — Input Output Control (Service 0x2F)

### 10.1 Purpose

Temporarily override sensor inputs or actuator outputs for testing without hardware setup.

### 10.2 Format

```
Request:  2F [DID high] [DID low] [controlOptionRecord] [controlEnableRecord]
Response: 6F [DID high] [DID low] [controlStatusRecord]

controlOptionRecord:
  0x00 = returnControlToECU
  0x01 = resetToDefault
  0x02 = freezeCurrentState
  0x03 = shortTermAdjustment (with control value)
```

### 10.3 Examples

```
Force coolant fan ON: 2F D0 01 03 01  (shortTermAdjustment, value=1=ON)
Force headlight ON:   2F D1 20 03 01
Return to ECU:        2F D0 01 00       (returnControlToECU)
Freeze output:        2F D0 01 02       (freeze at current state)
```

---

## Chapter 11 — All Negative Response Codes (0x7F)

### 11.1 Negative Response Format

```
Response:  7F [requested SID] [NRC byte]
Example:   7F 19 22 = Service 0x19 rejected with conditions not correct
```

### 11.2 Complete NRC Table

| NRC | Hex | Name | Meaning |
|-----|-----|------|---------|
| 0x10 | 10 | generalReject | Generic rejection |
| 0x11 | 11 | serviceNotSupported | SID not implemented |
| 0x12 | 12 | subFunctionNotSupported | Sub-function not implemented |
| 0x13 | 13 | incorrectMessageLengthOrInvalidFormat | Wrong byte count or format |
| 0x14 | 14 | responseTooLong | Response doesn't fit in buffer |
| 0x21 | 21 | busyRepeatRequest | ECU busy, resend |
| 0x22 | 22 | conditionsNotCorrect | Wrong vehicle state for request |
| 0x24 | 24 | requestSequenceError | Steps out of order |
| 0x25 | 25 | noResponseFromSubnetComponent | Gateway: downstream ECU not responding |
| 0x26 | 26 | failurePreventsExecutionOfRequestedAction | Hardware failure blocks execution |
| 0x31 | 31 | requestOutOfRange | DID/RID/address not supported |
| 0x33 | 33 | securityAccessDenied | Security not passed |
| 0x34 | 34 | authenticationRequired | ISO 14229-1:2020 new NRC |
| 0x35 | 35 | invalidKey | Wrong security key sent |
| 0x36 | 36 | exceededNumberOfAttempts | Too many failed security attempts |
| 0x37 | 37 | requiredTimeDelayNotExpired | Must wait (lockout period) |
| 0x38–0x4F | | reserved by extended addressing | |
| 0x50–0x5F | | reserved conditions | |
| 0x70 | 70 | uploadDownloadNotAccepted | Download rejected by ECU |
| 0x71 | 71 | transferDataSuspended | Data transfer aborted |
| 0x72 | 72 | generalProgrammingFailure | Flash write/erase failed |
| 0x73 | 73 | wrongBlockSequenceCounter | Transfer data block number wrong |
| 0x78 | 78 | requestCorrectlyReceivedResponsePending | ECU busy, more time needed (keep waiting) |
| 0x7E | 7E | subFunctionNotSupportedInActiveSession | Sub-function ok globally but not in this session |
| 0x7F | 7F | serviceNotSupportedInActiveSession | Service ok globally but not in this session |
| 0x81 | 81 | rpmTooHigh | Engine RPM prevents action |
| 0x82 | 82 | rpmTooLow | |
| 0x83 | 83 | engineIsRunning | |
| 0x84 | 84 | engineIsNotRunning | |
| 0x85 | 85 | engineRunTimeTooLow | |
| 0x86 | 86 | temperatureTooHigh | |
| 0x87 | 87 | temperatureTooLow | |
| 0x88 | 88 | vehicleSpeedTooHigh | |
| 0x89 | 89 | vehicleSpeedTooLow | |
| 0x8A | 8A | throttleOrPedalTooHigh | |
| 0x8B | 8B | throttleOrPedalTooLow | |
| 0x8C | 8C | transmissionRangeNotInNeutral | |
| 0x8D | 8D | transmissionRangeNotInGear | |
| 0x8F | 8F | brakeSwitch(es)NotClosed | |
| 0x90 | 90 | shifterLeverNotInPark | |
| 0x91 | 91 | torqueConverterClutchLocked | |
| 0x92 | 92 | voltageTooHigh | |
| 0x93 | 93 | voltageTooLow | |
| 0x94–0xFE | | vehicleManufacturerSpecific | OEM-defined conditions |

---

## Chapter 12 — Tester Present (Service 0x3E)

```
Request:  3E 00   → send and expect response 7E 00
Request:  3E 80   → suppress response (most common in automation)
Purpose:  Prevent ECU from timing out current session (must send every < P3 Client = 5s)
```

Used in CAPL test scripts to keep session alive during long test sequences.

---

## Chapter 13 — Control DTC Setting (Service 0x85)

```
Request:  85 01   → turnOnDTCSetting  (re-enable DTC logging)
Request:  85 02   → turnOffDTCSetting (disable DTC logging — for actuator tests)

When DTC setting off: ECU will not log DTCs even if fault conditions met.
Always re-enable with 85 01 at end of test! Otherwise DTCs missed in production.
```

---

## Chapter 14 — Link Control (Service 0x87)

```
Purpose: Change CAN/LIN/Ethernet baud rate for flash programming (higher speed)
Request:  87 01 [linkBaudRate byte]     → verifyBaudrateTransitionWithFixedBaudrate
Request:  87 02 [linkBaudRate byte]     → verifyBaudrateTransitionWithSpecificBaudrate
Request:  87 03                         → transitionBaudrate (actually switch now)
```

---

## Chapter 15 — DoIP (Diagnostics over IP / ISO 13400)

### 15.1 DoIP Overview

Used for high-bandwidth diagnostics (typically via OBD Ethernet port or internal vehicle Ethernet).

| Port | Purpose |
|------|---------|
| UDP 13400 | Vehicle announcement, routing activation |
| TCP 13400 | Diagnostic message transport |

### 15.2 DoIP Frame Header

```
[Protocol version 1 byte] [Inverse version 1 byte] [Payload type 2 bytes] [Payload length 4 bytes] [Payload]
Protocol version: 0x02 (ISO 13400-2:2012), 0x03 (ISO 13400-2:2019)
```

### 15.3 Key DoIP Payload Types

| Type | Hex | Description |
|------|-----|-------------|
| Vehicle Identification Request | 0x0001 | Discover ECUs on network |
| Vehicle Identification Response | 0x0004 | ECU VIN, EID, GID |
| Routing Activation Request | 0x0005 | Activate diagnostic channel |
| Routing Activation Response | 0x0006 | Confirm activation (0x10=success) |
| Diagnostic Message | 0x8001 | UDS request payload |
| Diagnostic Message Positive ACK | 0x8002 | UDS request received |
| Diagnostic Negative ACK | 0x8003 | UDS request rejected |

---

## Chapter 16 — EOL (End of Line) Programming Flow

### 16.1 Typical EOL Station Sequence

```
1. Vehicle on assembly line, power applied
2. EOL Tool connects (OBD port or direct ECU connection)
3. For each ECU:
   a. 22 F1 90 → Read VIN (verify correct VIN already programmed or needs writing)
   b. 22 F1 89 → Read SW version (verify correct SW loaded)
   c. 19 02 0F → Read all active DTCs (must be zero at EOL)
   d. If DTCs: investigate → clear → re-read
   e. 31 01 [EOL-RID] → Execute EOL routine (variant coding, customer config, calibration)
   f. 2E [DID] [value] → Write configuration / variant code
   g. 19 02 0F → Final DTC check
   h. PASS / FAIL stamp
4. Move to next station
```

### 16.2 Variant Coding

Writing vehicle-level configuration to ECUs:
```
Example: Infotainment market variant
2E D0 10 [variant byte]:
  0x01 = Europe left-hand drive
  0x02 = UK right-hand drive
  0x03 = North America
  0x04 = China
```

---

## Chapter 17 — UDS Over CAN vs Ethernet Comparison

| Feature | UDS over CAN (ISO-TP) | UDS over DoIP |
|---------|-----------------------|---------------|
| Max payload | 4095 bytes (ISO-TP) | Unlimited |
| Speed | 500 kbit/s–2 Mbit/s (CANFD) | 100 Mbit/s+ |
| Flash speed | ~5 min for 2MB | ~10 sec for 2MB |
| Addressing | 11-bit or 29-bit CAN ID | IP + Logical Address |
| Typical use | Body, Powertrain, Legacy ADAS | Modern ADAS, Domain ECUs, OTA |

---

## Chapter 18 — Functional vs Physical Addressing

| Type | CAN ID | Description |
|------|--------|-------------|
| Physical | 0x7A0 (e.g.) | One specific ECU |
| Functional | 0x7DF | Broadcast to all ECUs |

Use physical addressing for: security access, programming, write operations
Use functional addressing for: reading DTCs from multiple ECUs simultaneously, tester present broadcast

---

## Chapter 19 — Supplemental Services

### 0xBA — Authentication (ISO 14229-1:2020)

Enhanced security replacing 0x27, using PKI certificates:
```
BA 01 → deAuthenticate
BA 02 → verifyCertificateUnidirectional
BA 03 → verifyCertificateBidirectional
BA 04 → proofOfOwnership
BA 05 → transmitCertificate
BA 06 → requestChallengeForAuthentication
BA 07 → verifyProofOfOwnershipUnidirectional
BA 08 → verifyProofOfOwnershipBidirectional
BA 09 → authenticationConfiguration
```

### 0x84 — Secured Data Transmission

Wraps any other UDS service in cryptographic protection.

---

## Chapter 20 — Interview Quick Reference — Common UDS Questions

| Question | Key Answer Points |
|----------|------------------|
| What is 0x78 NRC? | ResponsePending — ECU needs more time. Tester must wait up to P2* (5s). Not an error. |
| Difference 0x7E vs 0x7F? | 0x7E = subfunction not supported in THIS session. 0x7F = service not supported in THIS session. Both implying service/sub-function works in another session. |
| How do DTCs get confirmed? | Must fail twice: first = pending (bit2), second consecutive = confirmed (bit3). |
| What resets permanent DTCs? | Only a completed OBD monitor drive cycle (not 14 FF FF FF). |
| Security access fails with 0x36? | Too many attempts. Must wait delay time (0x37 NRC) before retrying. |
| What is S3 Client timer? | Session timeout. If tester doesn't send 3E within S3 (5s), ECU falls back to Default session. |
| Maximum ISO-TP payload? | 4095 bytes (12-bit length field in First Frame). |
| Functional vs Physical? | Functional 0x7DF broadcasts to all ECUs. Physical targets one ECU directly. |
| When is 28 03 01 sent? | Before programming — disables ECU CAN Tx/Rx to prevent bus interference during flash. |
| What is CheckProgramDeps? | 31 01 FF 01 — after flash, checks compatibility between new SW and other ECUs. |

---
*File: 01_uds_complete_guide.md | UDS ISO 14229 Complete Reference | April 2026*
