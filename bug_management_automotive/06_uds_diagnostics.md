# UDS Diagnostics — Complete Guide for All Domains & Bug Scenarios

> **Standard**: ISO 14229-1 (UDS — Unified Diagnostic Services)
> **Applies to**: ADAS ECU · Infotainment HU · Instrument Cluster · Telematics TCU
> **Tools**: CANoe DiagnosticsDLL · CAPL diagRequest/diagResponse · Python-UDS · Vector CANdela · ODX/PDX · ISO-TP (ISO 15765-2)
> **Transport**: CAN / CAN-FD / DoIP (Ethernet) / K-Line (legacy)

---

## Table of Contents

1. [UDS Protocol Fundamentals](#1-uds-protocol-fundamentals)
2. [ISO-TP Transport Layer](#2-iso-tp-transport-layer)
3. [Session Management — Service 0x10](#3-session-management--service-0x10)
4. [Security Access — Service 0x27](#4-security-access--service-0x27)
5. [DTC Diagnostics — Service 0x19](#5-dtc-diagnostics--service-0x19)
6. [Read Data — Service 0x22](#6-read-data--service-0x22)
7. [Write Data — Service 0x2E](#7-write-data--service-0x2e)
8. [Routine Control — Service 0x31](#8-routine-control--service-0x31)
9. [ECU Reset — Service 0x11](#9-ecu-reset--service-0x11)
10. [Flash Programming — Services 0x34/0x36/0x37/0x38](#10-flash-programming--services-0x340x360x370x38)
11. [Communication Control — Service 0x28](#11-communication-control--service-0x28)
12. [Tester Present — Service 0x3E](#12-tester-present--service-0x3e)
13. [ADAS — UDS Diagnostics for Every Bug](#13-adas--uds-diagnostics-for-every-bug)
14. [Infotainment — UDS Diagnostics for Every Bug](#14-infotainment--uds-diagnostics-for-every-bug)
15. [Cluster — UDS Diagnostics for Every Bug](#15-cluster--uds-diagnostics-for-every-bug)
16. [Telematics — UDS Diagnostics for Every Bug](#16-telematics--uds-diagnostics-for-every-bug)
17. [Negative Response Codes — NRC Reference](#17-negative-response-codes--nrc-reference)
18. [CAPL UDS Automation Templates](#18-capl-uds-automation-templates)
19. [Python UDS Automation Scripts](#19-python-uds-automation-scripts)
20. [UDS Diagnostics Quick Reference Card](#20-uds-diagnostics-quick-reference-card)

---

## 1. UDS Protocol Fundamentals

### Service ID Structure

```
Request  frame: [SID]  [SubFunction / DID High]  [DID Low]  [Data...]
Response frame: [SID+0x40]  [SubFunction / DID High]  [DID Low]  [Data...]
NRC frame:      [0x7F]  [SID]  [NRC Code]
```

### All UDS Services Quick Reference

| Service ID | Name | Direction | Usage |
|-----------|------|-----------|-------|
| 0x10 | DiagnosticSessionControl | Req/Resp | Switch session (default/extended/programming) |
| 0x11 | ECUReset | Req/Resp | Hard reset / soft reset / key-off reset |
| 0x14 | ClearDiagnosticInformation | Req/Resp | Clear stored DTCs |
| 0x19 | ReadDTCInformation | Req/Resp | Read DTC list, status, snapshot, freeze frame |
| 0x22 | ReadDataByIdentifier | Req/Resp | Read ECU data (SW version, VIN, sensor values) |
| 0x23 | ReadMemoryByAddress | Req/Resp | Read raw memory address |
| 0x27 | SecurityAccess | Req/Resp | Seed/Key authentication to unlock privileged access |
| 0x28 | CommunicationControl | Req/Resp | Enable/disable TX/RX on CAN network |
| 0x29 | AuthenticationService | Req/Resp | PKI-based authentication (UDS 2020) |
| 0x2E | WriteDataByIdentifier | Req/Resp | Write calibration, config, NVM data |
| 0x2F | InputOutputControlByIdentifier | Req/Resp | Force actuator / override sensor signal |
| 0x31 | RoutineControl | Req/Resp | Start / stop / request result of routine |
| 0x34 | RequestDownload | Req/Resp | Initiate ECU flash programming |
| 0x35 | RequestUpload | Req/Resp | Upload data from ECU to tester |
| 0x36 | TransferData | Req/Resp | Transfer data blocks during flash |
| 0x37 | RequestTransferExit | Req/Resp | End data transfer |
| 0x38 | RequestFileTransfer | Req/Resp | File-based transfer (DoIP / Ethernet ECUs) |
| 0x3D | WriteMemoryByAddress | Req/Resp | Write raw memory address |
| 0x3E | TesterPresent | Req/Resp | Keep non-default session alive |
| 0x85 | ControlDTCSetting | Req/Resp | Enable/disable DTC storage |
| 0x86 | ResponseOnEvent | Req/Resp | Event-driven responses |
| 0x87 | LinkControl | Req/Resp | Change CAN baudrate |

---

## 2. ISO-TP Transport Layer

UDS runs on top of ISO-TP (ISO 15765-2) for CAN. Understanding frame types is essential for debugging failed UDS sessions.

### ISO-TP Frame Types

```
Single Frame (SF):   [0x0N] [Data...]         N = data length (0–7 bytes)
First Frame (FF):    [0x1H] [0xLL] [Data...]  HL = total length (12 bits)
Consecutive Frame (CF): [0x2N] [Data...]      N = sequence number (0–F)
Flow Control (FC):   [0x3X] [BS] [STmin]      X=0(CTS), X=1(WAIT), X=2(OVERFLOW)
```

### CANoe / CAPL: ISO-TP Debug Monitor
```capl
// Detect and log all ISO-TP frames on the diagnostic channel
variables {
  dword diagRequestId  = 0x7E0;   // Tester → ECU (Cluster example)
  dword diagResponseId = 0x7E8;   // ECU → Tester
}

on message * {
  if (this.id == diagRequestId || this.id == diagResponseId) {
    byte frameType = (this.byte(0) >> 4) & 0x0F;
    
    switch (frameType) {
      case 0x0:
        write("[ISO-TP] SINGLE FRAME  | ID=0x%03X | Len=%d | SID=0x%02X",
              this.id, this.byte(0) & 0x0F, this.byte(1));
        break;
      case 0x1:
        write("[ISO-TP] FIRST FRAME   | ID=0x%03X | TotalLen=%d | SID=0x%02X",
              this.id,
              ((this.byte(0) & 0x0F) << 8) | this.byte(1),
              this.byte(2));
        break;
      case 0x2:
        write("[ISO-TP] CONSEC FRAME  | ID=0x%03X | SeqNum=%d",
              this.id, this.byte(0) & 0x0F);
        break;
      case 0x3:
        write("[ISO-TP] FLOW CONTROL  | ID=0x%03X | FS=%d | BS=%d | STmin=%d ms",
              this.id,
              this.byte(0) & 0x0F,
              this.byte(1),
              this.byte(2));
        break;
    }
  }
}
```

### ISO-TP Timing Parameters (Critical for Debugging Timeouts)

| Parameter | Description | Typical Value | Max (ISO 15765) |
|-----------|-------------|---------------|----------------|
| N_As | Time for tester to send one frame | < 25 ms | 25 ms |
| N_Bs | Time for ECU to send Flow Control | < 25 ms | 25 ms |
| N_Cr | Time between receiving FC and sending next CF | < 25 ms | 25 ms |
| P2 | ECU response time after request | < 50 ms | 50 ms |
| P2* | Extended response time (0x78 NRC pending) | < 5000 ms | 5000 ms |

---

## 3. Session Management — Service 0x10

### Session Types

| SubFunction | Session | Access Level | Used For |
|-------------|---------|-------------|---------|
| 0x01 | Default Session | Basic | Read DTCs, Read data |
| 0x02 | Programming Session | FBL (Flashing) | Flash new firmware |
| 0x03 | Extended Diagnostic Session | Full diagnostics | Write calibration, actuator control, full DTC access |
| 0x40–0x5F | Vehicle Manufacturer Specific | OEM-defined | OEM-specific routines |

### Session Transition Protocol
```
Tester                                 ECU
  │                                     │
  │──── 10 03 ───────────────────────► │  RQ: Enter Extended Session
  │◄─── 50 03 [P2=0x00C8] [P2*=0x0258]─│  RS: OK; P2=200ms, P2*=60s
  │                                     │
  │  (every < 5 s, tester must send:)  │
  │──── 3E 00 ───────────────────────► │  RQ: TesterPresent (keep-alive)
  │◄─── 7E 00 ─────────────────────── │  RS: Acknowledged
```

### CAPL: Session Management with Auto Keep-Alive
```capl
variables {
  msTimer tKeepAlive;
  msTimer tSessionTimeout;
  int     currentSession;    // 1=default, 2=programming, 3=extended
}

on start {
  currentSession = 1;  // assume default at startup
}

// Switch to Extended Session
void enterExtendedSession() {
  diagRequest ECU_Target.DiagnosticSessionControl_ExtendedDiagnosticSession req;
  diagSendRequest(req);
}

on diagResponse ECU_Target.DiagnosticSessionControl_ExtendedDiagnosticSession {
  if (diagGetLastResponseCode(this) == 0) {
    write("Extended session active");
    currentSession = 3;
    setTimer(tKeepAlive, 4000);  // keep alive every 4 s (P2S is usually 5 s)
  } else {
    write("Session switch FAILED — NRC=0x%02X", diagGetLastResponseCode(this));
  }
}

// Auto Keep-Alive
on timer tKeepAlive {
  if (currentSession != 1) {
    diagRequest ECU_Target.TesterPresent req;
    diagSendRequest(req);
    setTimer(tKeepAlive, 4000);
  }
}

// Return to default on test end
on stopMeasurement {
  diagRequest ECU_Target.DiagnosticSessionControl_DefaultSession req;
  diagSendRequest(req);
  currentSession = 1;
}
```

---

## 4. Security Access — Service 0x27

Security Access uses a **Seed/Key** challenge-response to protect privileged operations (write calibration, flash, clear DTCs in production ECUs).

### Protocol Flow
```
Step 1: Tester sends RequestSeed
  Request:  27 [Level]        e.g. 27 01 (Level 1 seed request)
  Response: 67 [Level] [Seed bytes...]  e.g. 67 01 A3 2F 11 CC

Step 2: Tester computes Key = f(Seed, SecretKey)
  Key algorithm is OEM-proprietary (CRC, AES, custom XOR in legacy systems)

Step 3: Tester sends SendKey
  Request:  27 [Level+1] [Key bytes...]  e.g. 27 02 B7 4E 02 FF
  Response: 67 [Level+1]                 e.g. 67 02 → ACCESS GRANTED

Failure response (wrong key):
  7F 27 35   → NRC 0x35: invalidKey
  7F 27 36   → NRC 0x36: exceededNumberOfAttempts (ECU locks for 10 min)
```

### CAPL: Security Access with Seed/Key Computation
```capl
variables {
  byte g_seed[4];
}

// Step 1: Request seed
void securityAccess_Level01_RequestSeed() {
  diagRequest ECU_Target.SecurityAccess_requestSeed req;
  diagSendRequest(req);
}

on diagResponse ECU_Target.SecurityAccess_requestSeed {
  long nrcCode = diagGetLastResponseCode(this);
  if (nrcCode < 0) {
    write("SecurityAccess seed received");
    diagGetParameter(this, "securitySeed", g_seed, 4);
    write("  Seed: %02X %02X %02X %02X",
          g_seed[0], g_seed[1], g_seed[2], g_seed[3]);
    // Compute key and send
    securityAccess_Level02_SendKey(g_seed);
  }
}

// Step 2: Compute Key (OEM algorithm — example: XOR + rotate)
void computeKey(byte seed[], byte key[], int len) {
  int i;
  dword magic = 0xA5A5A5A5;   // OEM-specific constant
  for (i = 0; i < len; i++) {
    key[i] = (seed[i] ^ (magic >> (i * 8))) & 0xFF;
  }
}

// Step 3: Send key
void securityAccess_Level02_SendKey(byte seed[]) {
  byte key[4];
  diagRequest ECU_Target.SecurityAccess_sendKey req;
  computeKey(seed, key, 4);
  diagSetParameter(req, "securityKey", key, 4);
  diagSendRequest(req);
}

on diagResponse ECU_Target.SecurityAccess_sendKey {
  if (diagGetLastResponseCode(this) < 0) {  // < 0 means positive response
    write("Security Access GRANTED — Level 01");
  } else {
    write("Security Access DENIED — NRC=0x%02X", diagGetLastResponseCode(this));
  }
}
```

### Security Access Levels (Typical OEM Mapping)

| Level (Seed) | Level (Key) | Access Granted |
|-------------|-------------|---------------|
| 0x01 | 0x02 | Extended session operations (write DIDs, clear DTCs) |
| 0x03 | 0x04 | Programming session (flash FBL + application) |
| 0x05 | 0x06 | OEM engineering mode (forced actuator, direct memory write) |
| 0x11 | 0x12 | ADAS sensor calibration data write |
| 0x21 | 0x22 | Telematics eSIM profile provisioning |

---

## 5. DTC Diagnostics — Service 0x19

### DTC Status Byte — Bit Definitions

```
Bit 0 (0x01): testFailed                  — Test currently failing
Bit 1 (0x02): testFailedThisOperationCycle — Failed at least once this cycle
Bit 2 (0x04): pendingDTC                  — Failed in current OR previous cycle (not confirmed)
Bit 3 (0x08): confirmedDTC                — Failed in two consecutive cycles (confirmed fault)
Bit 4 (0x10): testNotCompletedSinceLastClear — DTC not run since last clear
Bit 5 (0x20): testFailedSinceLastClear    — Passed this cycle, but failed before last clear
Bit 6 (0x40): testNotCompletedThisOperationCycle — Monitor not run yet this cycle
Bit 7 (0x80): warningIndicatorRequested   — Tell-tale / MIL requested ON
```

### Sub-Function 0x02: Read DTCs by Status Mask

```
Request:  19 02 [statusMask]
  Common statusMasks:
    FF = all DTCs (any status bit set)
    09 = confirmed + currently failing
    08 = confirmed DTCs only
    04 = pending DTCs only

Response: 59 02 [availabilityMask] [DTC_1_High] [DTC_1_Mid] [DTC_1_Low] [Status_1]
                                    [DTC_2_High] [DTC_2_Mid] [DTC_2_Low] [Status_2] ...
```

### Sub-Function 0x06: Read DTC Snapshot (Freeze Frame)
```
Request:  19 06 [DTC_High] [DTC_Mid] [DTC_Low] [SnapshotRecordNumber=FF (all)]
Response: 59 06 [DTC_H] [DTC_M] [DTC_L] [Status]
                [RecordNum] [NumberOfIdentifiers]
                [DID_1_High] [DID_1_Low] [Length] [Data...]  ← freeze frame data
                [DID_2_High] [DID_2_Low] [Length] [Data...]
```

### Sub-Function 0x04: Read DTC Extended Data
```
Request:  19 04 [DTC_High] [DTC_Mid] [DTC_Low] [ExtDataRecordNum=FF]
Response: 59 04 [DTC_H] [DTC_M] [DTC_L] [Status]
                [RecordNum=0x01] [OccurrenceCounter] [AgingCounter] [OdometerAtFirstFail_km...]
```

### CAPL: Full DTC Read + Decode
```capl
variables {
  byte g_dtcBuffer[512];
  int  g_dtcCount;
}

// Read all confirmed DTCs  
void readAllConfirmedDTCs() {
  diagRequest ECU_Target.ReadDTCInformation_reportDTCByStatusMask req;
  diagSetParameter(req, "DTCStatusMask", 0x09);  // confirmed + currently failing
  diagSendRequest(req);
}

on diagResponse ECU_Target.ReadDTCInformation_reportDTCByStatusMask {
  long dtcHigh, dtcMid, dtcLow, dtcStatus;
  int  numDTCs, i;
  long nrc = diagGetLastResponseCode(this);
  
  if (nrc > 0) {
    write("ReadDTC FAILED — NRC=0x%02X", nrc);
    return;
  }
  
  numDTCs = diagGetParameterRaw(this, "DTCAndStatusRecord", g_dtcBuffer, elcount(g_dtcBuffer));
  numDTCs = numDTCs / 4;   // each DTC record = 3 bytes DTC + 1 byte status
  
  write("=== DTC Report: %d DTCs found ===", numDTCs);
  
  for (i = 0; i < numDTCs; i++) {
    dtcHigh   = g_dtcBuffer[i*4 + 0];
    dtcMid    = g_dtcBuffer[i*4 + 1];
    dtcLow    = g_dtcBuffer[i*4 + 2];
    dtcStatus = g_dtcBuffer[i*4 + 3];
    
    write("  DTC #%d: %02X%02X%02X | Status=0x%02X [%s%s%s%s]",
          i+1, dtcHigh, dtcMid, dtcLow, dtcStatus,
          (dtcStatus & 0x01) ? "ACTIVE " : "",
          (dtcStatus & 0x08) ? "CONFIRMED " : "",
          (dtcStatus & 0x80) ? "MIL-ON " : "",
          (dtcStatus & 0x04) ? "PENDING" : "");
  }
}

// Clear all DTCs
void clearAllDTCs() {
  diagRequest ECU_Target.ClearDiagnosticInformation req;
  diagSetParameter(req, "groupOfDTC", 0xFFFFFF);   // clear all
  diagSendRequest(req);
}

on diagResponse ECU_Target.ClearDiagnosticInformation {
  if (diagGetLastResponseCode(this) < 0) {
    write("DTCs cleared successfully");
  } else {
    write("Clear DTCs FAILED — NRC=0x%02X", diagGetLastResponseCode(this));
  }
}
```

### DTC Format Types

| Format | Structure | Example |
|--------|-----------|---------|
| SAE J2012 (OBD-II) | Letter + 4 digits | P0300, C1234, B2201, U0100 |
| ISO 14229 hex | 3 bytes hex | 0xC10325 |
| OEM-specific | OEM prefix + number | ADAS_042, TCU_017 |

---

## 6. Read Data — Service 0x22

### Standard DIDs (ISO 14229 Annex C)

| DID | Name | Typical Content |
|-----|------|----------------|
| 0xF186 | ActiveDiagnosticSession | Current session (01/02/03) |
| 0xF187 | VehicleManufacturerSparePartNumber | Part number string |
| 0xF188 | VehicleManufacturerECUSoftwareNumber | SW number |
| 0xF189 | VehicleManufacturerECUSoftwareVersionNumber | SW version |
| 0xF18A | SystemSupplierIdentifier | Supplier name/ID |
| 0xF18B | ECUManufacturingDate | Production date YYYYMMDD |
| 0xF18C | ECUSerialNumber | Unit serial number |
| 0xF190 | VIN | 17-byte Vehicle Identification Number |
| 0xF191 | VehicleManufacturerECUHardwareNumber | HW number |
| 0xF192 | SystemSupplierECUHardwareNumber | Supplier HW ID |
| 0xF193 | SystemSupplierECUHardwareVersionNumber | Supplier HW version |
| 0xF194 | SystemSupplierECUSoftwareNumber | Supplier SW number |
| 0xF195 | SystemSupplierECUSoftwareVersionNumber | SW version (supplier) |
| 0xF197 | VehicleManufacturerECUProductionDate | Production date |
| 0xF1A0 | BootSoftwareIdentification | Bootloader version |
| 0xF1A2 | ApplicationSoftwareIdentification | App SW fingerprint |

### CAPL: Read ECU Identity Block
```capl
void readECUIdentity() {
  word dids[7] = {0xF190, 0xF18C, 0xF195, 0xF191, 0xF1A0, 0xF186, 0xF18B};
  char names[7][40] = {
    "VIN", "ECU Serial", "SW Version", "HW Number",
    "Bootloader Version", "Active Session", "Manufacture Date"
  };
  int i;
  byte response[64];
  
  write("=== ECU Identity Read ===");
  for (i = 0; i < 7; i++) {
    diagRequest ECU_Target.ReadDataByIdentifier req;
    diagSetParameter(req, "dataIdentifier", dids[i]);
    diagSendRequest(req);
    // (responses handled in on diagResponse below)
  }
}

on diagResponse ECU_Target.ReadDataByIdentifier {
  word did;
  byte data[64];
  int len;
  
  did = diagGetParameter(this, "dataIdentifier");
  len = diagGetParameterRaw(this, "dataRecord", data, elcount(data));
  
  write("  DID 0x%04X: ", did);
  // Print as string if printable, else as hex
  int i; int allPrintable = 1;
  for (i = 0; i < len; i++) {
    if (data[i] < 0x20 || data[i] > 0x7E) { allPrintable = 0; break; }
  }
  if (allPrintable) {
    char strVal[64];
    strncpy(strVal, data, len); strVal[len] = 0;
    write("    '%s'", strVal);
  } else {
    write("    [hex] %02X %02X %02X %02X ...", data[0], data[1], data[2], data[3]);
  }
}
```

---

## 7. Write Data — Service 0x2E

Used to write calibration values, configuration flags, threshold parameters, and NVM data.

```
Request:  2E [DID_High] [DID_Low] [Data bytes...]
Response: 6E [DID_High] [DID_Low]       ← positive
          7F 2E [NRC]                   ← negative
```

### Pre-requisites for Write
1. Switch to **Extended Session** (0x10 03)
2. Perform **Security Access** (0x27) for the required access level
3. Send 0x2E with payload

### CAPL: Write Calibration DID with Full Session/Security Setup
```capl
// Complete write sequence: session → security → write → verify
void writeCalibrationValue(word did, byte data[], int dataLen) {
  // Step 1: Extended session
  diagRequest ECU_Target.DiagnosticSessionControl_ExtendedDiagnosticSession sessReq;
  diagSendRequest(sessReq);
  // Steps 2 and 3 handled in response callbacks (see Security Access section)
  // Step 4: actual write triggered after security granted
  g_pendingWriteDID  = did;
  g_pendingWriteData = data;
  g_pendingWriteLen  = dataLen;
}

on diagResponse ECU_Target.SecurityAccess_sendKey {
  // Security granted → now write the calibration value
  if (diagGetLastResponseCode(this) < 0) {
    diagRequest ECU_Target.WriteDataByIdentifier req;
    diagSetParameter(req, "dataIdentifier", g_pendingWriteDID);
    diagSetParameterRaw(req, "dataRecord", g_pendingWriteData, g_pendingWriteLen);
    diagSendRequest(req);
  }
}

on diagResponse ECU_Target.WriteDataByIdentifier {
  if (diagGetLastResponseCode(this) < 0) {
    write("Write DID 0x%04X: SUCCESS", diagGetParameter(this, "dataIdentifier"));
    // Verify: read back
    diagRequest ECU_Target.ReadDataByIdentifier verReq;
    diagSetParameter(verReq, "dataIdentifier", g_pendingWriteDID);
    diagSendRequest(verReq);
  } else {
    write("Write FAILED — NRC=0x%02X", diagGetLastResponseCode(this));
  }
}
```

---

## 8. Routine Control — Service 0x31

### Sub-Functions

| Sub-Function | Meaning |
|-------------|---------|
| 0x01 | Start Routine |
| 0x02 | Stop Routine |
| 0x03 | Request Routine Results |

### Common Routine IDs

| Routine ID | Description | Domain |
|-----------|-------------|--------|
| 0xFF00 | Erase Flash Memory (programming session) | All |
| 0xFF01 | Check Programming Integrity (CRC verify) | All |
| 0xFF02 | Check Programming Dependencies | All |
| 0x0202 | Check Memory | All |
| 0x0203 | Erase NVM (reset to factory) | Cluster, TCU |
| 0xE001 | ADAS Sensor Calibration Start | ADAS |
| 0xE002 | Camera Intrinsic Calibration | ADAS Camera ECU |
| 0xE003 | Radar Boresight Calibration | ADAS Radar ECU |
| 0xF010 | eCall Test Mode Trigger | TCU |
| 0xF020 | Modem Software Reset | TCU |
| 0xF030 | OTA Server Check-In | TCU |
| 0xB001 | Gauge Sweep Animation Trigger | Cluster |
| 0xB002 | Tell-tale Lamp Test (all ON) | Cluster |
| 0xB003 | Display Pixel Test | Cluster / HU |
| 0xC001 | Battery Reset (clear energy counters) | BMS ECU |

### CAPL: Trigger and Read Routine Result
```capl
// Trigger ADAS Radar Calibration Routine and poll for result
variables {
  msTimer tPollCalibResult;
  int     calibAttempts;
}

void startRadarCalibration() {
  diagRequest ECU_ADAS.RoutineControl_startRoutine req;
  diagSetParameter(req, "routineIdentifier", 0xE003);
  diagSetParameter(req, "routineControlOptionRecord", 0x01);  // option: full 360° sweep
  diagSendRequest(req);
}

on diagResponse ECU_ADAS.RoutineControl_startRoutine {
  if (diagGetLastResponseCode(this) < 0) {
    write("Radar calibration started — polling for result...");
    calibAttempts = 0;
    setTimer(tPollCalibResult, 2000);  // poll every 2 s
  }
}

on timer tPollCalibResult {
  calibAttempts++;
  if (calibAttempts > 30) {  // 60-second timeout
    write("ERROR: Calibration result timeout after 60 s");
    return;
  }
  
  diagRequest ECU_ADAS.RoutineControl_requestRoutineResults req;
  diagSetParameter(req, "routineIdentifier", 0xE003);
  diagSendRequest(req);
}

on diagResponse ECU_ADAS.RoutineControl_requestRoutineResults {
  byte status = diagGetParameter(this, "routineStatusRecord");
  
  switch(status) {
    case 0x00: 
      write("Calibration: IN PROGRESS — polling again...");
      setTimer(tPollCalibResult, 2000);
      break;
    case 0x01:
      write("Calibration: COMPLETE — SUCCESS");
      write("  Azimuth offset: %.2f deg", diagGetParameter(this, "azimuthOffset_mdeg") / 1000.0);
      write("  Elevation offset: %.2f deg", diagGetParameter(this, "elevationOffset_mdeg") / 1000.0);
      break;
    case 0xFF:
      write("Calibration: FAILED — code=0x%02X", diagGetParameter(this, "failureCode"));
      break;
  }
}
```

---

## 9. ECU Reset — Service 0x11

| SubFunction | Reset Type | Behavior |
|-------------|-----------|---------|
| 0x01 | HardReset | Simulates power cycle; NVM preserved; all RAM cleared |
| 0x02 | KeyOffOnReset | Simulates key-off then key-on; same as cycling ignition |
| 0x03 | SoftReset | Software-triggered restart; faster; preserves some RAM state |
| 0x04–0x5F | OEM Specific | OEM-defined (e.g., 0x04 = factory reset including NVM) |

```
Request:  11 01   (Hard Reset)
Response: 51 01   (acknowledged; ECU will reset)
           then ECU is offline for 0.5–5 s depending on boot time
```

---

## 10. Flash Programming — Services 0x34/0x36/0x37/0x38

### Full Flash Sequence
```
Step  | Service | Direction | Description
------|---------|-----------|------------
1     | 10 02   | Tester→ECU | Enter Programming Session
2     | 27 03   | Tester→ECU | RequestSeed (programming level)
3     | 27 04   | Tester→ECU | SendKey
4     | 28 03 01| Tester→ECU | CommunicationControl: disable non-diagnostic messages
5     | 85 02   | Tester→ECU | ControlDTCSetting: disable DTC storage during flash
6     | 31 01 FF00 | Tester→ECU | Erase Flash (RoutineControl 0xFF00)
7     | 34       | Tester→ECU | RequestDownload: [address][length][encrypt/compress]
8     | 36 01   | Tester→ECU | TransferData block 1 (max 0xFFD bytes per CAN frame multi)
9     | 36 02   | Tester→ECU | TransferData block 2 ...
10    | ...      | ...         | (continue for all blocks)
11    | 37       | Tester→ECU | RequestTransferExit: signal end of data
12    | 31 01 FF01 | Tester→ECU | CheckProgrammingIntegrity (CRC verify)
13    | 31 01 FF02 | Tester→ECU | CheckProgrammingDependencies
14    | 11 01   | Tester→ECU | ECUReset HardReset
15    | 10 01   | Tester→ECU | Return to Default Session
16    | 28 00 01| Tester→ECU | CommunicationControl: re-enable all messages
17    | 85 01   | Tester→ECU | ControlDTCSetting: re-enable DTC storage
```

### Service 0x34 — RequestDownload Parameters
```
Request:  34 [dataFormatIdentifier] [addressAndLengthFormatIdentifier]
             [memoryAddress...] [memorySize...]

dataFormatIdentifier:
  0x00 = no compression, no encryption
  0x10 = compressed, no encryption
  0x11 = compressed + encrypted

addressAndLengthFormatIdentifier:
  Upper nibble = length of memorySize  (bytes)
  Lower nibble = length of memoryAddress (bytes)
  e.g. 0x44 = 4-byte address + 4-byte size

Example:
  34 00 44 08010000 00070000
     ↑  ↑  ↑        ↑
     │  │  │        └ size = 0x70000 = 458752 bytes (448 KB)
     │  │  └ start address = 0x08010000 (application start)
     │  └ addr=4 bytes, size=4 bytes
     └ no compression/encryption

Response: 74 [blockLengthFormatIdentifier] [maxBlockLength]
  e.g.  74 20 0FFD  → max 4093 bytes per TransferData block
```

---

## 11. Communication Control — Service 0x28

```
Request:  28 [subFunction] [communicationType]

subFunction:
  0x00 = enableRxAndTx        (normal operation)
  0x01 = enableRxAndDisableTx (ECU listens but does not send non-diag)
  0x02 = disableRxAndEnableTx
  0x03 = disableRxAndTx       (suppress all non-diagnostic traffic)

communicationType:
  0x01 = normal CAN messages (nm, app signals, etc.)
  0x02 = NM messages
  0x03 = all CAN messages
```

**Usage**: Always call 0x28 03 01 (disable normal traffic) before flashing to prevent CAN load from interfering with flash timing. Always re-enable with 0x28 00 01 after flashing.

---

## 12. Tester Present — Service 0x3E

```
Request:  3E 00        (responseRequired = 0 → ECU responds)
          3E 80        (suppressPositiveResponse = 1 → ECU does NOT respond; saves bus bandwidth)
Response: 7E 00        (positive response when 0x00 used)
```

**Rule**: In non-default sessions (Extended, Programming), send 0x3E 80 every ≤ 4 seconds or the ECU will time out back to Default Session (losing security access and current mode).

---

## 13. ADAS — UDS Diagnostics for Every Bug

### Bug 1: AEB False Activation (Stationary Metal Bridge)

**Symptoms**: AEB activates without real obstacle.  
**UDS Diagnostic Path**:

```
Step 1: Read active DTCs immediately after AEB false activation event
  Request:  10 03               ← Extended session
  Request:  19 02 FF            ← Read all DTCs
  
  Expected DTCs to look for:
  DTC code (OEM)    | Name                          | Action
  ADAS_042          | RadarObject_NoFusion           | Radar sees target, camera does not
  ADAS_088          | AEB_UnjustifiedBrake           | ECU logged unexpected brake
  ADAS_101          | StationaryObjectFilter_Bypass  | Filter disabled flag

Step 2: Read Freeze Frame for ADAS_088 (snapshot at moment of AEB activation)
  Request:  19 06 [ADAS_088 DTC bytes] FF
  
  Freeze Frame expected content:
  DID      | Signal                   | Expected Value | Actual (fault)
  0x4010   | VehicleSpeed_kmh         | 80             | 80   ✓ (high speed)
  0x4011   | RadarObj_Distance_m      | 42             | 42   ← ghost at 42 m
  0x4012   | RadarObj_RelVelocity_mps | 0.0            | 0.0  ← stationary (bridge)
  0x4013   | RadarObj_RCS_dBsm        | 22.5           | 22.5 ← strong reflection
  0x4014   | Camera_ObjectValid       | 1              | 0    ✗ (camera sees nothing)
  0x4015   | AEB_BrakeRequest         | 0              | 1    ✗ (brake active)
  0x4016   | StatObjFilter_Active     | 1              | 0    ✗ (filter NOT running)
  
  Diagnosis: StationaryObjectFilter not active at speed > 60 km/h → DTC ADAS_101

Step 3: Read sensor calibration status
  Request:  22 E001    ← ADAS Radar calibration status DID
  Response: Live data — azimuth offset should be 0.0 ± 0.5 deg; if > 1 deg → recalibrate

Step 4: Trigger calibration verification routine
  Request:  31 01 E003    ← Start Radar Boresight Calibration Check
  Poll:     31 03 E003    ← Read result
  Pass:     status = 0x01, azimuth_error < 0.5 deg

Step 5: Clear DTCs after fix deployed
  Request:  14 FF FF FF
```

---

### Bug 2: FCW Not Triggering (False Negative)

```
Step 1: Read Extended Data for ADAS_FCW_Miss DTC (if logged)
  Request:  19 04 [DTC] FF
  
  Extended data record:
  Field               | Value      | Meaning
  OccurrenceCounter   | 3          | Happened 3 times
  AgingCounter        | 0          | Never passed (still active)
  OdomAtFirstFail_km  | 85,420     | First occurrence at this odometer
  
Step 2: Force-activate FCW test mode via IO Control
  Request:  2F [FCW_TestMode_DID] 03 01
  ServiceID=0x2F (InputOutputControlByIdentifier)
  controlOption=0x03 (shortTermAdjustment)
  value=0x01 (enable FCW test target injection)
  
  In test mode: ECU generates internal radar target at 25 m, 30 km/h closing
  Expected: FCW alert within 500 ms
  If no FCW: → FCW algorithm not reaching alert threshold → investigate threshold DID
  
Step 3: Read FCW threshold calibration
  Request:  22 4020    ← DID: FCW_AlertThreshold_m (alert distance in meters)
  Expected: 25–40 m range; if 0xFF or 0x00 → corrupted calibration
  
Step 4: Re-write FCW threshold if corrupted
  Request:  27 11, 27 12    ← Security Access Level 0x11 (ADAS calibration)
  Request:  2E 4020 00 1E   ← Write 30 m threshold (0x1E = 30)
```

---

### Bug 3: ADAS Calibration Loss After Update

```
Step 1: Read calibration validity flags
  Request:  22 E010    ← ADAS CalibrationStatus DID
  Response bytes:
    Byte 0: RadarCalib_Valid    (0x01=valid, 0x00=invalid)
    Byte 1: CameraCalib_Valid   (0x01=valid, 0x00=invalid)
    Byte 2: FusionCalib_Valid   (0x01=valid, 0x00=invalid)
    Byte 3: CalibNVM_CRC_OK     (0x01=OK,    0x00=CRC fail)
    
  If CalibNVM_CRC_OK = 0x00 → NVM CRC fail → calibration lost after OTA

Step 2: Check NVM status routine
  Request:  31 01 0205    ← OEM-specific NVM integrity check routine
  Response: 0x01=OK; 0xE1=CRC_Error; 0xE2=Address_Error; 0xE3=Content_Invalid

Step 3: Recover calibration from EOL calibration record
  Request:  31 01 E010    ← Restore calibration from backup NVM block
  Response: 0x01=restored; 0xFF=no backup available → full workshop calibration needed

Step 4: If no backup → full calibration on calibration bench
  31 01 E001    ← Start radar calibration routine (vehicle on calibration rig)
  31 01 E002    ← Start camera calibration (target board at 5 m)
```

---

## 14. Infotainment — UDS Diagnostics for Every Bug

> Note: Infotainment HU may support UDS over CAN or over DoIP (Ethernet/IP). 
> For DoIP: Source/Target Address in UDP are used instead of CAN IDs.

### Bug 1: Navigation ANR / Memory Leak

```
Step 1: Check ECU state (is HU responding to UDS?)
  Request:  3E 00    ← TesterPresent
  If no response within 50 ms → HU crashed; attempt ECU reset

Step 2: Soft reset to recover (preserves NVM)
  Request:  11 03    ← SoftReset
  Wait 20 s for HU to re-boot
  Then: 3E 00 → confirm response

Step 3: Read HU SW version (confirm build affected by known memory leak)
  Request:  22 F195
  Response: parse Navigation app version embedded in SW string
  Compare with known-bad version: v4.2.1 → if match → apply patch OTA

Step 4: Read relevant DTC (Memory Pressure Warning, if OEM implements it)
  Request:  19 02 09
  DTC: HU_MemPressure_Warning (OEM code)
  If present → confirm memory leak occurrence logged by ECU

Step 5: Check heap size DID (OEM-specific, if supported)
  Request:  22 A010    ← OEM DID: AndroidHeapUsed_MB
  Response: 2 bytes = current heap used in MB
  If value > 180 MB → near OOM boundary (heap limit 192 MB on SA8155P)
  
Step 6: Force app stop and memory reclaim via routine
  Request:  31 01 C010    ← OEM routine: ForceGarbageCollection_NavigationApp
  This triggers Android System.gc() + trim memory to background apps
```

---

### Bug 2: Android Auto Disconnect

```
Step 1: Read AA connection status DID
  Request:  22 A020    ← OEM DID: AndroidAutoConnectionStatus
  Byte 0: 0x00=Disconnected, 0x01=Connecting, 0x02=Connected, 0x03=Error
  
Step 2: Read AA disconnect reason DID
  Request:  22 A021    ← OEM DID: AndroidAutoLastDisconnectReason
  Code  | Meaning
  0x01  | Heartbeat timeout (CPU starvation)
  0x02  | USB voltage drop
  0x03  | Protocol version mismatch
  0x04  | User-initiated disconnect
  
Step 3: Read CPU load DID at time of last disconnect (if freeze frame supported)
  Request:  19 06 [AA_Disconnect_DTC bytes] FF
  Freeze frame field: CPU_Load_Percent → if > 90% → confirm CPU starvation cause

Step 4: Read USB VBUS voltage DID
  Request:  22 A022    ← OEM DID: USB_VBUS_Voltage_mV
  Expected: ≥ 4750 mV; if < 4500 mV → USB power sag → AA disconnect from power issue

Step 5: Reset AA session (force clean reconnect)
  Request:  31 01 C020    ← OEM routine: ResetAndroidAutoSession
  This resets the AA stack; user must reconnect USB
```

---

### Bug 3: HU Boot Failure After OTA

```
Step 1: Check if HU responds (any UDS service)
  Request:  3E 00    ← functional addressing (0x7DF) TesterPresent
  If no response → HU in bootloader or completely failed boot

Step 2: Try to reach bootloader directly
  Change CAN ID: use FBL diagnostic address (OEM-defined, e.g. 0x7F0/0x7F8)
  Request:  3E 00
  If response → bootloader alive → can attempt re-flash application

Step 3: Read FBL version to confirm bootloader integrity
  Request:  22 F1A0    ← BootSoftwareIdentification
  If response → FBL healthy; application failed
  
Step 4: Full application re-flash via FBL
  (Follow flash sequence: 10 02 → 27 03/04 → 28 03 01 → 31 01 FF00 → 34 → 36... → 37 → 11 01)
  Flash correct application hex file
  
Step 5: Verify boot after re-flash
  Wait 20 s → Request 22 F195 → confirm SW version = expected
  Request 22 F186 → confirm session=0x01 (default; boot complete)
```

---

## 15. Cluster — UDS Diagnostics for Every Bug

### Bug 1: Speedometer Wrong Value (DBC Regression)

```
Step 1: Read VehicleSpeed DID from Cluster (cluster's decoded value)
  Request:  22 B010    ← OEM DID: ClusterDecoded_VehicleSpeed_kmh
  Response: 2 bytes, uint16, LSB first (or MSB per OEM DBC)
  Compare with: GPS reference speed / test bench CAN injected speed
  If cluster_decoded = 2 × injected_speed → confirms factor=0.02 bug

Step 2: Read DBC version used by cluster SW
  Request:  22 F1C0    ← OEM DID: CANMatrixVersion
  Response: version string e.g. "v3.1.0"
  Cross-check: v3.1.0 is the known bad version → confirm regression

Step 3: Read active DTCs related to speed signal
  Request:  19 02 FF
  DTC: CLUSTER_051 = VehicleSpeed_SignalValueOutOfRange → if set → confirms signal decode issue

Step 4: After DBC fix deployed (new SW build) — verify
  Inject known CAN speed on test bench: 0x2328 raw = 90 km/h (factor 0.01)
  Request: 22 B010 → response should be 0x005A = 90 decimal
  If 0x00B4 = 180 → factor still wrong

Step 5: Clear residual DTCs
  Request:  10 03    ← Extended
  Request:  27 01    ← Seed
  Request:  27 02 [key]
  Request:  14 FF FF FF
```

---

### Bug 2: CEL Tell-tale Flickering (CAN ID Arbitration)

```
Step 1: Read MIL (CEL) status DID
  Request:  22 B020    ← OEM DID: MIL_LampStatus
  Response: 0x01=ON, 0x00=OFF, 0x02=Blinking
  
  If response oscillates ON/OFF when read repeatedly → confirms real-time conflict

Step 2: Read tell-tale command source DID
  Request:  22 B021    ← OEM DID: MIL_ControlSource_NodeID
  Expected: 0x10 (ECM node ID)
  If shows 0x10 and 0xCC alternating → two nodes fight for control

Step 3: Check DTC for CAN signal conflict
  Request:  19 02 09
  DTC: CLUSTER_072 = LampControl_CAN_MultipleNodeConflict → if set → confirms root cause

Step 4: Identify conflicting node via DTC freeze frame
  Request:  19 06 [DTC CLUSTER_072 bytes] FF
  Freeze Frame:
  DID B030 = ConflictingNodeID = 0xCC (calibration ECU node address)
  DID B031 = ConflictingCANID  = 0x500

Step 5: Fix verification — disconnect CAL ECU, confirm no oscillation
  Request:  22 B020 every 500 ms for 30 s → value must remain stable at 0x00 (OFF)
```

---

### Bug 3: Cluster Boot Failure After OTA (NVM CRC)

```
Step 1: Check if cluster responds at all
  Use functional addressing 0x7DF:
  Request:  3E 00
  If no response → cluster in boot halt → attempt FBL contact

Step 2: Contact Cluster FBL (bootloader)
  Cluster FBL CAN ID: typically 0x6A0 / 0x6A8 (OEM-defined)
  Request:  3E 00
  If response → FBL alive → can re-flash application

Step 3: Read FBL DTC (FBL may store reason for boot failure)
  Request:  10 02    ← Enter programming session (FBL level)
  Request:  27 03    ← Seed
  Request:  27 04 [key]
  Request:  19 02 FF
  DTC: CLUSTER_FBL_001 = NVM_CRC_BootFailure → confirms NVM CRC caused halt

Step 4: Trigger NVM factory reset routine
  Request:  31 01 0203    ← NVM factory reset / erase routine
  Response: 0x01 = NVM reset successful
  
Step 5: ECU hard reset → boot with factory NVM defaults
  Request:  11 01
  Wait 8 s
  Request:  3E 00 → if response → cluster rebooted successfully

Step 6: Verify all gauge data (factory defaults applied)
  Request:  22 B040    ← OEM DID: OdometerValue_km
  If = 0xFFFFFF (0) → NVM reset worked; odometer will be re-learned from drive
  Request:  22 B020    ← MIL status → should be 0x00 (off, clean state)

Step 7: Re-apply OTA with NVM migration package
  Standard flash sequence + NVM migration data block
```

---

### Bug 4: Low Fuel Warning Missing

```
Step 1: Read current decoded fuel level from cluster
  Request:  22 B050    ← OEM DID: ClusterDecoded_FuelLevel_L
  If reading shows 10.0 L but no telltale → threshold mismatch confirmed

Step 2: Read cluster low-fuel threshold DID
  Request:  22 B051    ← OEM DID: LowFuelWarning_Threshold_L
  Response: should be 0x0A (10 decimal = 10 L)
  If response = 0x06 (6 L) → calibration error (threshold too low)

Step 3: Security Access + Write correct threshold
  Request:  10 03
  Request:  27 01    ← RequestSeed
  Request:  27 02 [computed key]
  Request:  2E B051 00 0A    ← Write threshold = 10 L (0x0A)
  Response: 6E B051    ← Success

Step 4: Verify write (read back)
  Request:  22 B051
  Expected: 0x000A

Step 5: Functional test — inject CAN value for 9.5 L, verify telltale activates
  Simulate CAN FuelLevel = 9.5 L on bench
  Request:  22 B020 every 500 ms
  Telltale must change from 0x00 → 0x01 within 500 ms of fuel dropping below 10 L
```

---

## 16. Telematics — UDS Diagnostics for Every Bug

### Bug 1: eCall Not Triggered (GNSS Denied)

```
Step 1: Read eCall system status DID
  Request:  22 T010    ← OEM DID: eCall_SystemStatus
  Byte 0: eCallState (0=IDLE, 1=READY, 2=ACTIVE, 3=FAIL, 4=BLOCKED)
  Byte 1: GNSS_Valid (0=NO_FIX, 1=VALID)
  Byte 2: LastFix_Age_sec (age of last GNSS fix, 0–255 s; 0xFF=exceeded 255 s)
  Byte 3: CellNetwork_Connected (0/1)
  Byte 4: eSIM_Active (0/1)
  
  If eCallState = BLOCKED and GNSS_Valid = 0 → confirms GNSS-blocked eCall bug

Step 2: Read eCall last error code DID
  Request:  22 T011    ← OEM DID: eCall_LastErrorCode
  Code  | Meaning
  0x01  | GNSS_Freshness_Failed     ← this bug
  0x02  | Network_Registration_Failed
  0x03  | MSD_Build_Error
  0x04  | PSAP_No_Answer
  0x05  | Audio_Channel_Failed

Step 3: Check GNSS freshness threshold calibration
  Request:  22 T012    ← OEM DID: GNSS_FreshnessThreshold_sec
  Expected: 3600 (1 hour, per UN R144)
  If = 30 (30 seconds) → bug: too tight threshold → blocks eCall in any tunnel > 30 s
  
Step 4: Write corrected GNSS freshness threshold
  Request:  10 03
  Request:  27 21, 27 22    ← Access Level for eCall configuration (regulatory function)
  Request:  2E T012 0E 10   ← 0x0E10 = 3600 seconds
  
Step 5: Trigger eCall test (regulatory test mode)
  Request:  31 01 F010    ← eCall Test Routine (generates test eCall to PSAP simulator)
  Response: in progress (0x00) → poll
  Poll:     31 03 F010 until status = 0x01 (test call established) or 0xFF (fail)
  
Step 6: Read resulting MSD to verify position data
  Request:  22 T020    ← OEM DID: LastMSD_Latitude_1e7deg
  Request:  22 T021    ← OEM DID: LastMSD_Longitude_1e7deg
  Request:  22 T022    ← OEM DID: LastMSD_PositionConfidence (0=GNSS, 1=CELL_APPROX)
  
  R144 compliance check:
  If GNSS unavailable → MSD must be sent with posConf=0x01 (approximate)
  If MSD not sent at all → compliance FAIL → bug not fixed
```

---

### Bug 2: OTA Brick (Bootloader Overwritten)

```
Step 1: Attempt TCU contact on normal diagnostic address
  CAN ID: 0x7C6 (Req) / 0x7CE (Resp) — typical TCU diag address
  Request:  3E 00
  If no response → TCU bricked → bootloader contact attempt

Step 2: Attempt TCU FBL contact
  CAN ID: 0x7A0 (FBL Req) / 0x7A8 (FBL Resp) — OEM FBL address
  Request:  3E 00
  If no response → FBL also corrupted → physical JTAG required

Step 3 (if FBL alive): Read FBL version
  Request:  22 F1A0
  Confirms FBL is intact → proceed with application re-flash

Step 4 (FBL alive): Flash correct TCU application
  Full flash sequence (10 02 → 27 03/04 → 28 03 01 → 31 01 FF00 → 34 → 36 → 37 → 11 01)
  Use corrected OTA package with start address = 0x08010000 (NOT 0x08000000)

Step 5 (FBL dead): Physical JTAG recovery
  External tool (STM32CubeProgrammer or Lauterbach Trace32) required
  Flash FBL golden image at 0x08000000
  Flash application at 0x08010000
  Reset

Step 6: Post-flash validation
  Request:  3E 00 → response within 5 s → ECU alive
  Request:  22 F195 → confirm SW version = expected v3.0 (correct build)
  Request:  22 F1A0 → confirm FBL version unchanged = golden
  Request:  19 02 FF → confirm no critical boot DTCs present
  
Step 7: OTA prevention validation
  Request:  22 T030    ← OEM DID: OTA_PackageAddressCheck_Result
  Expected: 0x01 (PASS) — CI gate ran address check before flash
  If 0x00 (FAIL) → CI gate not active → escalate to build/release process team
```

---

### Bug 3: Cellular Dropout

```
Step 1: Read modem signal quality DID
  Request:  22 T040    ← OEM DID: Modem_RSRP_dBm (int16, signed)
  Response: e.g. 0xFF8A = -118 dBm → very weak signal
  
Step 2: Read cellular registration status
  Request:  22 T041    ← OEM DID: CellularRegistration_State
  0x01 = Registered home
  0x02 = Not registered, searching
  0x05 = Registered roaming
  0xFF = No SIM / SIM error
  
Step 3: Read dropout occurrence counter
  Request:  22 T042    ← OEM DID: CellularDropout_Count (uint16)
  High count (> 10 in current session) → confirms repeated dropout issue
  
Step 4: Read modem configuration (AT+QCFG stored settings)
  Request:  22 T043    ← OEM DID: ModemNWScanMode_Config
  Value: 0x00=auto(all) / 0x01=GSM / 0x02=LTE_only / 0x03=LTE+WCDMA+GSM
  Expected: 0x03 (auto with all modes) for best reconnect resilience
  If 0x02 (LTE only) → modem cannot fall back to 3G → prolonged dropout in LTE gaps

Step 5: Write corrected modem rescan config
  Request:  10 03
  Request:  27 01, 27 02 [key]
  Request:  2E T043 03    ← Set nwscanmode=3 (auto with all modes)

Step 6: Trigger modem reset to apply config
  Request:  31 01 F020    ← Modem software reset routine
  Wait 15 s; check 3E 00 response

Step 7: Re-read signal quality to verify improvement
  Request:  22 T040 every 2 s for 30 s → observe RSRP value stabilize
  Request:  22 T041 → 0x01 (registered) within 10 s post-reset
```

---

### Bug 4: MSD Wrong Position (Cell Tower Used Instead of GNSS)

```
Step 1: Read current GNSS data from TCU
  Request:  22 T050    ← GNSS_Latitude_1e7
  Request:  22 T051    ← GNSS_Longitude_1e7
  Request:  22 T052    ← GNSS_HDOP_x10 (e.g. 0x0E = 14 → HDOP=1.4)
  Request:  22 T053    ← GNSS_FixValid (0/1)
  Request:  22 T054    ← GNSS_Fix_Age_sec

Step 2: Read position source selection DID (which source TCU is using for MSD)
  Request:  22 T055    ← OEM DID: MSD_PositionSource
  0x01 = GNSS (correct)
  0x02 = Cell tower                         ← bug condition
  0x03 = Last known GNSS (GNSS unavailable)

Step 3: Read HDOP threshold calibration
  Request:  22 T056    ← OEM DID: PositionSource_HDOP_Threshold
  Expected: 20 (HDOP = 2.0 → use GNSS even up to HDOP=20.0)
  If = 5 (HDOP = 0.5) → only uses GNSS for extremely accurate fix → falls back too early
  
Step 4: Write corrected HDOP threshold
  Request:  10 03
  Request:  27 21, 27 22    ← eCall config security level
  Request:  2E T056 00 14   ← 0x0014 = 20 → accept GNSS up to HDOP=2.0

Step 5: Verify by reading MSD after fix
  Request:  31 01 F010    ← Trigger test eCall in PSAP-simulator test mode
  After call: 22 T022     ← MSD_PositionConfidence
  Expected: 0x00 (GNSS fix, not cell approximate) when GNSS available
```

---

## 17. Negative Response Codes — NRC Reference

| NRC | Mnemonic | Meaning | Common Cause |
|-----|----------|---------|-------------|
| 0x10 | generalReject | Generic rejection | Unsupported in this context |
| 0x11 | serviceNotSupported | Service ID not implemented | ECU does not support this service |
| 0x12 | subFunctionNotSupported | SubFunction not supported | DTC sub-function not implemented |
| 0x13 | incorrectMessageLengthOrInvalidFormat | Wrong number of bytes | Missing data byte in request |
| 0x14 | responseTooLong | Response exceeds transport buffer | ISO-TP buffer overflow |
| 0x21 | busyRepeatRequest | ECU busy with previous request | Retry after 20 ms |
| 0x22 | conditionsNotCorrect | Prerequisites not met | Wrong session, not yet initialized |
| 0x24 | requestSequenceError | Wrong order of services | e.g. 0x36 without 0x34 first |
| 0x25 | noResponseFromSubnetComponent | Gateway cannot reach ECU | Routing not active; ECU offline |
| 0x26 | failurePreventsExecutionOfRequestedAction | Hardware fault prevents action | Sensor fault blocks calibration |
| 0x31 | requestOutOfRange | DID or parameter value outside range | DID 0xFFFF not defined; value out of scale |
| 0x33 | securityAccessDenied | Insufficient security level | Not yet performed Security Access |
| 0x35 | invalidKey | Wrong key provided | Seed/Key algorithm mismatch |
| 0x36 | exceededNumberOfAttempts | Too many failed security attempts | ECU locked; wait 10 min |
| 0x37 | requiredTimeDelayNotExpired | Security delay not elapsed | ECU unlocks after timeout |
| 0x70 | uploadDownloadNotAccepted | Download not accepted by ECU | Wrong session; prerequisites missing |
| 0x71 | transferDataSuspended | Transfer interrupted | Timeout; retry from step 0x34 |
| 0x72 | generalProgrammingFailure | Flash write error | Flash sector failed; HW fault |
| 0x73 | wrongBlockSequenceCounter | 0x36 block counter wrong | Sent block 3 after block 1 (skipped 2) |
| 0x78 | requestCorrectlyReceivedResponsePending | ECU still processing | Wait for final response (P2* up to 5 s) |
| 0x7E | subFunctionNotSupportedInActiveSession | SubFunction not in current session | Need Extended or Programming session |
| 0x7F | serviceNotSupportedInActiveSession | Service not in current session | e.g. 0x34 requires Programming session |

### CAPL: NRC Handler
```capl
void handleNRC(long nrc, char serviceName[]) {
  switch((int)nrc) {
    case 0x22: write("[NRC] %s: conditionsNotCorrect — check session/prerequisites", serviceName); break;
    case 0x33: write("[NRC] %s: securityAccessDenied — perform 0x27 first", serviceName); break;
    case 0x35: write("[NRC] %s: invalidKey — check seed/key algorithm", serviceName); break;
    case 0x36: write("[NRC] %s: exceededAttempts — ECU locked, wait 10 min", serviceName); break;
    case 0x78: write("[NRC] %s: responsePending — waiting for ECU (up to P2*=5s)", serviceName); break;
    case 0x7E: write("[NRC] %s: notSupportedInSession — switch to Extended session first", serviceName); break;
    case 0x7F: write("[NRC] %s: notSupportedInSession — switch to Programming session first", serviceName); break;
    default:   write("[NRC] %s: NRC=0x%02X (see ISO 14229-1 Table A.1)", serviceName, (int)nrc); break;
  }
}
```

---

## 18. CAPL UDS Automation Templates

### Template: Complete Diagnostic Session with Auto-Recovery
```capl
variables {
  msTimer tKeepAlive;
  msTimer tResponseTimeout;
  int     g_securityGranted;
  int     g_sessionActive;
  
  enum DiagState {
    DIAG_IDLE,
    DIAG_SESSION_PENDING,
    DIAG_SECURITY_SEED,
    DIAG_SECURITY_KEY,
    DIAG_READY,
    DIAG_ERROR
  } g_diagState;
}

// ═══════════════════════════════════════════════
// PUBLIC: Start a full diagnostic session
// ═══════════════════════════════════════════════
void diagInit() {
  g_diagState = DIAG_SESSION_PENDING;
  g_securityGranted = 0;
  
  diagRequest ECU_Target.DiagnosticSessionControl_ExtendedDiagnosticSession req;
  diagSendRequest(req);
  setTimer(tResponseTimeout, 2000);
}

on diagResponse ECU_Target.DiagnosticSessionControl_ExtendedDiagnosticSession {
  cancelTimer(tResponseTimeout);
  if (diagGetLastResponseCode(this) < 0) {
    write("[DIAG] Extended session active");
    g_diagState = DIAG_SECURITY_SEED;
    setTimer(tKeepAlive, 4000);
    diagRequestSeed_Level01();
  } else {
    write("[DIAG] Session switch FAILED — NRC=0x%02X", diagGetLastResponseCode(this));
    g_diagState = DIAG_ERROR;
  }
}

void diagRequestSeed_Level01() {
  diagRequest ECU_Target.SecurityAccess_requestSeed req;
  diagSendRequest(req);
}

on diagResponse ECU_Target.SecurityAccess_requestSeed {
  byte seed[4];
  if (diagGetLastResponseCode(this) < 0) {
    diagGetParameter(this, "securitySeed", seed, 4);
    g_diagState = DIAG_SECURITY_KEY;
    
    byte key[4];
    computeKey(seed, key, 4);
    
    diagRequest ECU_Target.SecurityAccess_sendKey keyReq;
    diagSetParameter(keyReq, "securityKey", key, 4);
    diagSendRequest(keyReq);
  }
}

on diagResponse ECU_Target.SecurityAccess_sendKey {
  if (diagGetLastResponseCode(this) < 0) {
    g_securityGranted = 1;
    g_diagState = DIAG_READY;
    write("[DIAG] Security Access granted — diagnostics ready");
    onDiagReady();  // callback — override in your test script
  } else {
    write("[DIAG] Security DENIED — NRC=0x%02X", diagGetLastResponseCode(this));
    g_diagState = DIAG_ERROR;
  }
}

// Override this function in your test script
void onDiagReady() {
  write("[DIAG] Override onDiagReady() in your test script");
}

on timer tKeepAlive {
  if (g_diagState != DIAG_IDLE && g_diagState != DIAG_ERROR) {
    diagRequest ECU_Target.TesterPresent req;
    req.suppressPosRspMsgIndicationBit = 1;  // suppress response (0x3E 80)
    diagSendRequest(req);
    setTimer(tKeepAlive, 4000);
  }
}

on timer tResponseTimeout {
  write("[DIAG] TIMEOUT — no response from ECU within 2 s");
  g_diagState = DIAG_ERROR;
}
```

### Template: DTC Snapshot Reporter
```capl
// Reads all confirmed DTCs, then reads freeze frame for each one
variables {
  byte  g_dtcRecords[512];
  int   g_totalDTCs;
  int   g_currentDTCIndex;
}

void readAllDTCsWithFreezeFrames() {
  diagRequest ECU_Target.ReadDTCInformation_reportDTCByStatusMask req;
  diagSetParameter(req, "DTCStatusMask", 0x08);  // confirmed only
  diagSendRequest(req);
}

on diagResponse ECU_Target.ReadDTCInformation_reportDTCByStatusMask {
  int len, i;
  len = diagGetParameterRaw(this, "DTCAndStatusRecord", g_dtcRecords, 512);
  g_totalDTCs = len / 4;
  write("=== %d confirmed DTC(s) found ===", g_totalDTCs);
  
  g_currentDTCIndex = 0;
  if (g_totalDTCs > 0) {
    readNextFreezeFrame();
  }
}

void readNextFreezeFrame() {
  if (g_currentDTCIndex >= g_totalDTCs) {
    write("=== All DTC freeze frames read ===");
    return;
  }
  
  byte dtcH = g_dtcRecords[g_currentDTCIndex*4];
  byte dtcM = g_dtcRecords[g_currentDTCIndex*4 + 1];
  byte dtcL = g_dtcRecords[g_currentDTCIndex*4 + 2];
  byte stat = g_dtcRecords[g_currentDTCIndex*4 + 3];
  
  write("DTC #%d: %02X%02X%02X status=0x%02X — reading freeze frame...",
        g_currentDTCIndex+1, dtcH, dtcM, dtcL, stat);
  
  diagRequest ECU_Target.ReadDTCInformation_reportDTCSnapshotRecordByDTCNumber req;
  diagSetParameter(req, "DTCGroup", ((long)dtcH<<16)|((long)dtcM<<8)|dtcL);
  diagSetParameter(req, "DTCSnapshotRecordNumber", 0xFF);
  diagSendRequest(req);
}

on diagResponse ECU_Target.ReadDTCInformation_reportDTCSnapshotRecordByDTCNumber {
  byte snap[256];
  int  len, i;
  len = diagGetParameterRaw(this, "DTCSnapshotRecord", snap, 256);
  
  write("  Freeze Frame (%d bytes):", len);
  for (i = 0; i < len; i += 8) {
    write("    +%03d: %02X %02X %02X %02X %02X %02X %02X %02X",
          i, snap[i], snap[i+1], snap[i+2], snap[i+3],
          snap[i+4], snap[i+5], snap[i+6], snap[i+7]);
  }
  
  g_currentDTCIndex++;
  readNextFreezeFrame();  // read next DTC
}
```

---

## 19. Python UDS Automation Scripts

### Script: Full UDS Diagnostic Session via python-udsoncan
```python
#!/usr/bin/env python3
"""
Full UDS Diagnostic Automation
Requires: pip install udsoncan python-can
Usage: python3 uds_full_diag.py --interface vector --channel 0 --bitrate 500000
"""

import udsoncan
from udsoncan.connections import PythonIsoTpConnection
from udsoncan.client import Client
import udsoncan.services as services
import isotp
import argparse
import time
import struct

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────
ECU_TXID = 0x7E0   # Tester → ECU
ECU_RXID = 0x7E8   # ECU → Tester

CLIENT_CONFIG = udsoncan.ClientConfig(
    request_timeout        = 2.0,
    p2_timeout             = 0.2,
    p2_star_timeout        = 5.0,
    security_algo          = None,   # Set to your OEM key function
    data_identifiers       = {},
    standard_version       = 2020,
)

DTC_STATUS_NAMES = {
    0x01: "testFailed",
    0x02: "testFailedThisCycle",
    0x04: "pendingDTC",
    0x08: "confirmedDTC",
    0x80: "MIL_requested",
}

# ──────────────────────────────────────────────────────────────
# OEM Security Key Algorithm (replace with real OEM algorithm)
# ──────────────────────────────────────────────────────────────
def compute_key(seed: bytes, level: int) -> bytes:
    magic = 0xA5A5A5A5
    key = bytearray(len(seed))
    for i, byte in enumerate(seed):
        key[i] = (byte ^ ((magic >> (i * 8)) & 0xFF)) & 0xFF
    return bytes(key)

# ──────────────────────────────────────────────────────────────
# UDS Session Setup
# ──────────────────────────────────────────────────────────────
def setup_session(client: Client, security_level: int = 0x01):
    print("[DIAG] Switching to Extended Diagnostic Session...")
    client.change_session(services.DiagnosticSessionControl.Session.extendedDiagnosticSession)
    print("[DIAG] Extended session active")
    
    print(f"[DIAG] Security Access — Level {security_level:#04x}...")
    seed = client.request_seed(security_level)
    key  = compute_key(seed.security_seed, security_level)
    client.send_key(security_level + 1, key)
    print("[DIAG] Security Access granted")

# ──────────────────────────────────────────────────────────────
# Read ECU Identity
# ──────────────────────────────────────────────────────────────
def read_ecu_identity(client: Client):
    print("\n=== ECU Identity ===")
    dids = {
        0xF190: "VIN",
        0xF18C: "ECU Serial",
        0xF195: "SW Version",
        0xF191: "HW Number",
        0xF1A0: "Bootloader Version",
        0xF186: "Active Session",
    }
    for did, name in dids.items():
        try:
            result = client.read_data_by_identifier(did)
            raw = result.service_data.values[did]
            try:
                value = raw.decode('ascii').strip('\x00')
            except Exception:
                value = raw.hex(' ').upper()
            print(f"  {name:25s} (0x{did:04X}): {value}")
        except Exception as e:
            print(f"  {name:25s} (0x{did:04X}): ERROR — {e}")

# ──────────────────────────────────────────────────────────────
# Read All DTCs
# ──────────────────────────────────────────────────────────────
def read_all_dtcs(client: Client):
    print("\n=== DTC Report ===")
    try:
        result = client.get_dtc_by_status_mask(0xFF)
        dtcs = result.dtcs
        if not dtcs:
            print("  No DTCs stored (clean)")
            return []
        
        print(f"  {len(dtcs)} DTC(s) found:")
        for dtc in dtcs:
            status_flags = []
            for bit, name in DTC_STATUS_NAMES.items():
                if dtc.status.raw & bit:
                    status_flags.append(name)
            print(f"  DTC {dtc.id:#08x} | status={dtc.status.raw:#04x} | {', '.join(status_flags)}")
        
        return dtcs
    except Exception as e:
        print(f"  ReadDTC failed: {e}")
        return []

# ──────────────────────────────────────────────────────────────
# Read DTC Freeze Frame
# ──────────────────────────────────────────────────────────────
def read_dtc_freeze_frame(client: Client, dtc_id: int):
    print(f"\n  Freeze Frame for DTC {dtc_id:#08x}:")
    try:
        result = client.get_dtc_snapshot_by_dtc_number(dtc_id, record_number=0xFF)
        for record in result.dtcs:
            for snap_rec in record.snapshots:
                print(f"    Record #{snap_rec.record_number}: {snap_rec.raw_data.hex(' ').upper()}")
    except Exception as e:
        print(f"    Freeze Frame read failed: {e}")

# ──────────────────────────────────────────────────────────────
# Clear DTCs
# ──────────────────────────────────────────────────────────────
def clear_all_dtcs(client: Client):
    print("\n[DIAG] Clearing all DTCs...")
    try:
        client.clear_dtc()
        print("[DIAG] DTCs cleared successfully")
    except Exception as e:
        print(f"[DIAG] Clear DTCs failed: {e}")

# ──────────────────────────────────────────────────────────────
# ECU Reset
# ──────────────────────────────────────────────────────────────
def ecu_reset(client: Client, reset_type: int = 0x01):
    names = {0x01: "Hard", 0x02: "KeyOffOn", 0x03: "Soft"}
    print(f"\n[DIAG] ECU Reset — {names.get(reset_type, 'Unknown')} ({reset_type:#04x})...")
    try:
        client.ecu_reset(reset_type)
        print("[DIAG] Reset command sent — waiting 5 s for re-boot...")
        time.sleep(5)
    except Exception as e:
        print(f"[DIAG] Reset failed: {e}")

# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="UDS Full Diagnostic Script")
    parser.add_argument("--interface", default="vector", help="CAN interface (vector/pcan/socketcan)")
    parser.add_argument("--channel",   default="0",     help="CAN channel")
    parser.add_argument("--bitrate",   default=500000,  type=int)
    parser.add_argument("--clear-dtcs", action="store_true", help="Clear DTCs after reading")
    args = parser.parse_args()

    # Set up ISO-TP connection
    tp_addr  = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=ECU_TXID, rxid=ECU_RXID)
    bus      = isotp.CanStack(interface=args.interface, channel=args.channel, bitrate=args.bitrate)
    conn     = PythonIsoTpConnection(bus, tp_addr)

    with Client(conn, config=CLIENT_CONFIG) as client:
        setup_session(client)
        read_ecu_identity(client)
        
        dtcs = read_all_dtcs(client)
        for dtc in dtcs[:5]:   # read freeze frames for first 5 DTCs
            read_dtc_freeze_frame(client, dtc.id)
        
        if args.clear_dtcs:
            clear_all_dtcs(client)
        
        print("\n[DIAG] Session complete.")

if __name__ == "__main__":
    main()
```

---

## 20. UDS Diagnostics Quick Reference Card

### Session Entry Sequence
```
1. 10 03            Enter Extended Session
2. 27 [odd]         Request Seed
3. 27 [odd+1] [Key] Send Key
4. (3E 80 every 4s) Keep-alive
```

### DTC Read Sequence
```
19 02 FF    Read all by status mask FF
19 02 09    Confirmed + currently failing
19 06 [DTC] FF   Freeze Frame for specific DTC
19 04 [DTC] FF   Extended Data (occurrence count, age)
14 FF FF FF      Clear all DTCs
```

### Write Sequence (Calibration)
```
1. 10 03
2. 27 [level], 27 [level+1] [key]
3. 2E [DID_H] [DID_L] [data...]
4. 22 [DID_H] [DID_L]    → verify read-back
```

### Flash Sequence (Summary)
```
10 02 → 27 03/04 → 28 03 01 → 85 02 →
31 01 FF00 → 34 → 36 (blocks...) → 37 →
31 01 FF01 → 31 01 FF02 → 11 01 →
10 01 → 28 00 01 → 85 01
```

### Per-Domain Diagnostic CAN IDs (Typical OEM)

| ECU | Req ID | Resp ID | FBL Req | FBL Resp |
|-----|--------|---------|---------|---------|
| ADAS ECU | 0x714 | 0x71C | 0x700 | 0x708 |
| Cluster | 0x7A0 | 0x7A8 | 0x790 | 0x798 |
| Head Unit | 0x7D0 | 0x7D8 | 0x7C0 | 0x7C8 |
| TCU | 0x7C6 | 0x7CE | 0x7B0 | 0x7B8 |
| Functional | 0x7DF | N/A | N/A | N/A |

> Note: Always verify actual CAN IDs from your project's CAN matrix / ODX database. The above are representative only.
