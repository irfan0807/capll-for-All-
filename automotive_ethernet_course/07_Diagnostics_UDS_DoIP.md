# SECTION 7 — DIAGNOSTICS: UDS, OBD, DoIP
## Course: Automotive Ethernet Testing — Complete Industry Training

---

## 7.1 UDS — UNIFIED DIAGNOSTIC SERVICES (ISO 14229)

### UDS Overview

UDS is the standard diagnostic protocol for automotive ECUs. It defines a client-server model where a tester (client) sends service requests and the ECU (server) responds. UDS replaced KWP2000 and is transported over CAN TP (ISO 15765-2) or DoIP (ISO 13400) for Ethernet.

### UDS Session Model

```
UDS DIAGNOSTIC SESSIONS:

┌─────────────────────────────────────────────────────────────────┐
│  DEFAULT SESSION (0x01)                                         │
│  • Available always (ignition ON)                               │
│  • Limited service set: 0x10, 0x11, 0x14, 0x19, 0x22, 0x3E   │
│  • No security access required for basic read                  │
│  • ECU operates normally (no intrusion)                        │
├─────────────────────────────────────────────────────────────────┤
│  EXTENDED DIAGNOSTIC SESSION (0x03)                             │
│  • Full read/write access to ECU data                          │
│  • Requires security access (0x27) for write operations        │
│  • Services: all default + 0x27, 0x28, 0x2E, 0x31, 0x85      │
│  • TesterPresent (0x3E) required to stay in session            │
├─────────────────────────────────────────────────────────────────┤
│  PROGRAMMING SESSION (0x02)                                     │
│  • Only for ECU software update (flashing)                     │
│  • Full security access required                               │
│  • Services: 0x34, 0x36, 0x37, 0x31 (flash routines)         │
│  • ECU may disable normal application behavior                 │
└─────────────────────────────────────────────────────────────────┘

Session Transitions:
Default ──► Extended  (0x10 03)
Default ──► Programming (0x10 02) — with Security Access
Extended ──► Programming (0x10 02)
Any ──► Default (0x10 01 or timeout without TesterPresent)
```

### Complete UDS Service Table

```
UDS SERVICE TABLE:
┌─────┬────────────────────────────────┬──────────────────────────────────┐
│ SID │ Service Name                   │ Description                      │
├─────┼────────────────────────────────┼──────────────────────────────────┤
│ 10  │ DiagnosticSessionControl       │ Change session type              │
│ 11  │ ECUReset                       │ Reset ECU (hard/soft/key-off)    │
│ 14  │ ClearDiagnosticInformation     │ Clear all DTCs                   │
│ 19  │ ReadDTCInformation             │ Read DTC list and status         │
│ 22  │ ReadDataByIdentifier           │ Read data record by 2-byte DID   │
│ 23  │ ReadMemoryByAddress            │ Read raw ECU memory              │
│ 24  │ ReadScalingDataByIdentifier    │ Read DID with scaling info       │
│ 27  │ SecurityAccess                 │ Seed-key unlock mechanism        │
│ 28  │ CommunicationControl           │ Enable/disable ECU communication │
│ 29  │ Authentication                 │ PKI-based auth (ISO 14229-1:2020)│
│ 2C  │ DynamicallyDefineDataIdentifier│ Create custom DID on-the-fly     │
│ 2E  │ WriteDataByIdentifier          │ Write data to ECU by DID         │
│ 2F  │ InputOutputControlByIdentifier │ Override ECU I/O actuators       │
│ 31  │ RoutineControl                 │ Execute ECU routines (start/stop)│
│ 34  │ RequestDownload                │ Initiate firmware download       │
│ 35  │ RequestUpload                  │ Initiate data upload from ECU    │
│ 36  │ TransferData                   │ Transfer data blocks             │
│ 37  │ RequestTransferExit            │ End data transfer                │
│ 38  │ RequestFileTransfer            │ File-based transfer              │
│ 3D  │ WriteMemoryByAddress           │ Write raw ECU memory             │
│ 3E  │ TesterPresent                  │ Keep session alive (prevent timeout│
│ 83  │ AccessTimingParameter          │ Modify P2/P2* timing             │
│ 84  │ SecuredDataTransmission        │ Encrypted service (SecOC)        │
│ 85  │ ControlDTCSetting              │ Enable/disable DTC storage       │
│ 86  │ ResponseOnEvent                │ Event-triggered UDS notification │
│ 87  │ LinkControl                    │ Change communication baud rate   │
└─────┴────────────────────────────────┴──────────────────────────────────┘
```

---

## 7.2 UDS SERVICE DEEP DIVE

### 0x10 — DiagnosticSessionControl

```
REQUEST:  10 02             → Enter Programming Session
RESPONSE: 50 02 00 19 01 F4 → Positive: P2=25ms, P2*=500ms (BCD encoded)

REQUEST:  10 03             → Enter Extended Session
RESPONSE: 50 03 00 19 01 F4 → Positive response

NEGATIVE: 7F 10 22          → NRC 0x22 = Conditions Not Correct
                               (e.g., vehicle speed > 5 km/h)
```

### 0x27 — SecurityAccess (Seed-Key)

```
SECURITY ACCESS FLOW:

Step 1: Request Seed
  TX: 27 01        (odd = seed request for level 1)
  RX: 67 01 A1 B2 C3 D4    (4-byte seed returned)

Step 2: Calculate Key
  Algorithm (example — actual is OEM-defined):
  Key = Seed XOR 0x36 49 52 A3
  Key = A1 XOR 36, B2 XOR 49, C3 XOR 52, D4 XOR A3
  Key = 97, FB, 91, 77

Step 3: Send Key
  TX: 27 02 97 FB 91 77    (even = send key for level 1)
  RX: 67 02                 (access granted!)

NEGATIVE CASES:
  Wrong key 3 times → 7F 27 35 (exceededNumberOfAttempts)
  Wait until cooldown (typically 10-30s before retry)
  
SECURITY LEVELS:
  0x01/0x02 → Development level (ADAS team)
  0x03/0x04 → Calibration level (Calibration engineers)
  0x05/0x06 → Extended diagnostic level (Dealers)
  0x11/0x12 → Programming level (ECU flash)
```

### 0x19 — ReadDTCInformation

```
SUB-FUNCTIONS:
  19 01 FF  → reportNumberOfDTCByStatusMask (count all DTCs)
  19 02 FF  → reportDTCByStatusMask (all DTCs with status)
  19 03     → reportDTCSnapshotIdentification
  19 04 XX XX XX 01 → reportDTCSnapshotRecordByDTCNumber
  19 06 XX XX XX    → reportDTCExtDataRecordByDTCNumber

EXAMPLE: Read all confirmed DTCs
  TX: 19 02 08     (statusMask = 0x08 = confirmed)
  RX: 59 02 2A     (positive prefix + statusAvailabilityMask)
      C0 41 00 2F  (DTC 1: code C04100, status 0x2F)
      C0 42 01 2A  (DTC 2: code C04201, status 0x2A)
      ...

DTC STATUS BYTE (0x2F = 0010 1111):
  Bit 0: testFailed           (1 = currently failed)
  Bit 1: testFailedThisOperationCycle
  Bit 2: pendingDTC           (1 = not yet confirmed)
  Bit 3: confirmedDTC         (1 = stored in NvM)
  Bit 4: testNotCompletedSinceLastClear
  Bit 5: testFailedSinceLastClear
  Bit 6: testNotCompletedThisOperationCycle
  Bit 7: warningIndicatorRequested (MIL light)
```

### 0x22 — ReadDataByIdentifier (DID)

```
COMMON DIDs (Standard + OEM-defined):
  F186 → ActiveDiagnosticSession   (0x01, 0x02, or 0x03)
  F187 → VehicleManufacturerSparePartNumber
  F188 → VehicleManufacturerECUSWVersionNumber
  F189 → VehicleManufacturerECUSWVersionNumber (AUTOSAR variant)
  F18A → SystemSupplierIdentifier
  F18B → ECUManufacturingDate
  F18C → ECUSerialNumber
  F190 → VIN (Vehicle Identification Number — 17 chars)
  F191 → VehicleManufacturerHardwareVersionNumber
  
  OEM-defined DIDs (example):
  2000 → ADAS_SystemStatus
  2001 → RADAR_ObjectCount
  2002 → Camera_FrameRate
  2010 → ECU_Temperature

REQUEST: 22 F1 90
RESPONSE: 62 F1 90 57 42 41 ... (VIN bytes, ASCII)
           62 = positive prefix (0x22 + 0x40)
```

### 0x2E — WriteDataByIdentifier

```
Write OEM-defined parameter (ECU calibration):
TX: 2E 20 00 00 00 05 DC     (Write DID 0x2000, value 0x000005DC = 1500)
RX: 6E 20 00                  (Positive response)

Security: Session must be Extended, Security Level unlocked
```

### 0x31 — RoutineControl

```
SUB-FUNCTIONS:
  01 = StartRoutine
  02 = StopRoutine
  03 = RequestRoutineResult

EXAMPLE: Initiate CRC check of flashed software
TX: 31 01 FF 01              (Start routine 0xFF01 = CheckMemory)
RX: 71 01 FF 01 00           (Positive, routineStatus = 0x00 = complete)

EXAMPLE: Erase flash memory
TX: 31 01 FF 00 00 44 00 00 00 80 000  (EraseMemory, addr=0x44000, len=0x80000)
RX: 71 01 FF 00               (Positive response when complete)
    (may take 2-5 seconds, use 0x78 NRC for response pending)
```

---

## 7.3 OBD-II DIAGNOSTICS

### OBD-II Overview

OBD-II (ISO 15031) is the standardized on-board diagnostics system mandated by law for emissions monitoring. All passenger vehicles since 1996 (USA) must support it.

```
OBD-II SERVICE MODES:
Mode 01: Show Current Data (live sensor values)
Mode 02: Show Freeze Frame Data (at fault occurrence)
Mode 03: Show Stored DTCs
Mode 04: Clear DTCs and Reset Monitors
Mode 05: Oxygen Sensor Monitoring Results
Mode 06: On-Board Monitoring Test Results
Mode 07: Show Pending DTCs
Mode 08: Control On-Board System/Test
Mode 09: Request Vehicle Information (VIN, calibration IDs)
Mode 0A: Show Permanent DTCs

OBD-II DTC FORMAT:
P0171 → P = Powertrain, 0 = SAE-standard, 171 = specific fault
         B = Body, C = Chassis, U = Network

COMMON OBD PIDs:
PID 0D → Vehicle Speed (km/h)
PID 0C → Engine RPM (r/4 formula)
PID 05 → Engine Coolant Temperature (°C)
PID 04 → Engine Load (%)
PID 0B → Intake Manifold Pressure
PID 11 → Throttle Position
```

---

## 7.4 DoIP — COMPLETE PROTOCOL GUIDE

### DoIP Protocol Architecture (ISO 13400)

```
DoIP LAYER STACK:
┌─────────────────────────────────────────────────┐
│  UDS (ISO 14229) — Application Layer            │
│  e.g., 10 02 / 27 01 / 34 / 36 / 37           │
├─────────────────────────────────────────────────┤
│  DoIP (ISO 13400-2) — Transport Layer           │
│  Payload Types: DiagMsg, RoutingActivation, ... │
├─────────────────────────────────────────────────┤
│  TCP (port 13400) or UDP (port 13400)           │
│  TCP for diagnostics, UDP for discovery         │
├─────────────────────────────────────────────────┤
│  IP (IPv4 or IPv6)                              │
├─────────────────────────────────────────────────┤
│  Ethernet (100BASE-T1 / 1000BASE-T1)           │
└─────────────────────────────────────────────────┘
```

### DoIP Header Format

```
DoIP GENERIC HEADER (8 bytes):
┌──────────────┬──────────────┬──────────────────┬────────────────────┐
│ Protocol Ver │ Inverse Ver  │  Payload Type    │   Payload Length   │
│  1 byte      │  1 byte      │  2 bytes         │   4 bytes          │
│  0x02        │  0xFD        │  0x0005 (example)│  (remaining bytes) │
└──────────────┴──────────────┴──────────────────┴────────────────────┘

DoIP PAYLOAD TYPES:
0x0000 → Generic DoIP Header Negative Acknowledge
0x0001 → Vehicle Identification Request (broadcast, UDP)
0x0002 → Vehicle Identification Request with EID
0x0003 → Vehicle Identification Request with VIN
0x0004 → Vehicle Announcement / Vehicle Identification Response
0x0005 → Routing Activation Request
0x0006 → Routing Activation Response
0x0007 → Alive Check Request
0x0008 → Alive Check Response
0x4001 → DoIP Entity Status Request
0x4002 → DoIP Entity Status Response
0x8001 → Diagnostic Message (UDS payload)
0x8002 → Diagnostic Message Positive Ack
0x8003 → Diagnostic Message Negative Ack
```

### Complete DoIP Flash Sequence — Wireshark Analysis

```
ACTUAL WIRE-LEVEL SEQUENCE FOR ECU FLASHING VIA DoIP:

=== PHASE 1: NETWORK DISCOVERY ===
Frame 1: UDP Broadcast 255.255.255.255:13400
  DoIP: VehicleIdentificationRequest (0x0001)
  Length: 0

Frame 2: UDP from 192.168.1.50 (DoIP GW):
  DoIP: VehicleAnnouncement (0x0004)
  VIN: "WDB1234567890ABCD" (17 bytes)
  EID: 00:11:22:33:44:55 (MAC)
  GID: 00:11:22:33:44:56
  Further action: 0x00 (none required)

=== PHASE 2: TCP CONNECTION ===
Frame 3: TCP SYN → 192.168.1.50:13400
Frame 4: TCP SYN-ACK ← 192.168.1.50:13400
Frame 5: TCP ACK (3-way handshake complete)

=== PHASE 3: ROUTING ACTIVATION ===
Frame 6: TCP → DoIP RoutingActivationRequest (0x0005)
  Source Address: 0xE000 (tester logical address)
  Activation Type: 0x00 (default)

Frame 7: TCP ← DoIP RoutingActivationResponse (0x0006)
  Source Address: 0xE000
  Logical Address: 0x0010 (ADAS ECU)
  Response Code: 0x10 (routing activation success)

=== PHASE 4: PROGRAMMING SESSION ===
Frame 8: TCP → DoIP DiagMsg (0x8001)
  Source: 0xE000, Target: 0x0010
  UDS: 10 02 (ProgrammingSession request)

Frame 9: TCP ← DoIP DiagMsg Ack (0x8002)
Frame 10: TCP ← DoIP DiagMsg (0x8001)
  UDS: 50 02 00 19 01 F4 (ProgrammingSession positive response)

=== PHASE 5: SECURITY ACCESS ===
Frame 11: TX → 27 11 (RequestSeed for programming level)
Frame 12: RX ← 67 11 A4 B3 C2 D1 (Seed returned)
Frame 13: TX → 27 12 5B 4C 3D 2E (Computed key)
Frame 14: RX ← 67 12 (Access granted)

=== PHASE 6: FLASH ERASE ===
Frame 15: TX → 31 01 FF 00 ... (EraseMemory routine)
Frame 16: RX ← 78 ... (RequestCorrectlyReceivedResponsePending)
Frame 17: RX ← 71 01 FF 00 (EraseMemory complete ~3s later)

=== PHASE 7: DOWNLOAD (TRANSFER DATA) ===
Frame 18: TX → 34 00 44 00 40 00 00 80 00 (RequestDownload)
  dataFormatId: 0x00 (no compression/encryption)
  addressAndLengthFormatId: 0x44
  memoryAddress: 0x00400000
  memorySize: 0x00080000 (512KB)

Frame 19: RX ← 74 20 04 00 (maxBlockLength = 0x0400 = 1024 bytes per block)

Frame 20: TX → 36 01 [1024 bytes block 1] (TransferData)
Frame 21: RX ← 76 01 (TransferData positive ack)
Frame 22: TX → 36 02 [1024 bytes block 2]
Frame 23: RX ← 76 02
... (repeat for all blocks = 512 blocks for 512KB)

=== PHASE 8: VERIFY AND RESET ===
Frame 530: TX → 37 (RequestTransferExit)
Frame 531: RX ← 77 (OK)
Frame 532: TX → 31 01 FF 01 (CheckMemory — verify CRC/hash)
Frame 533: RX ← 71 01 FF 01 00 (Memory valid)
Frame 534: TX → 11 01 (ECUReset — hardReset)
Frame 535: RX ← 51 01 (OK, ECU resetting)
... ECU reboots, runs new application
```

---

## 7.5 DIAGNOSTIC ROUTING — Gateway Architecture

### DoIP Gateway Routing Table

```
DoIP GATEWAY ROUTING:
                              
External Tester           DoIP Gateway           Target ECUs
(192.168.0.100)          (192.168.1.1)
    │                         │
    │ DoIP TCP connect ───────►│
    │ RoutingActivation ──────►│
    │ DiagMsg[Target=0x0010] ─►│
    │                         │──► Internal CAN TP → ADAS_ECU (0x0010)
    │                         │       CAN ID: 0x7A0 (Tester to ECU)
    │◄── DiagMsg Response ─────│◄── CAN TP Response from ADAS_ECU
    │    [UDS Response]        │       CAN ID: 0x7A8 (ECU to Tester)

ROUTING TABLE IN GATEWAY ECU (DoIP/AUTOSAR DCM Config):
┌─────────────────────────────────────────────────────────────────┐
│ Tester Logical│ Target Logical │ Transport   │ Target ECU       │
│ Address       │ Address        │ Protocol    │ CAN ID           │
├─────────────────────────────────────────────────────────────────┤
│ 0xE000        │ 0x0010         │ CAN TP      │ Tx:0x7A0, Rx:0x7A8│
│ 0xE000        │ 0x0020         │ CAN TP      │ Tx:0x7B0, Rx:0x7B8│
│ 0xE000        │ 0x0030         │ Eth Unicast │ IP:192.168.1.30  │
│ 0xE000        │ 0xFFFF         │ Functional  │ CAN ID: 0x7DF    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7.6 ECU FLASHING STRATEGY

### Bootloader Modes

```
AUTOMOTIVE BOOTLOADER STATE MACHINE:

Power ON
    │
    ▼
PBL checks:
  ├── Is PROG_REQUEST_FLAG set in RAM? (set by previous reset)
  │       YES → jump to SBL
  │
  ├── Is application valid? (CRC check)
  │       NO  → jump to SBL
  │
  └── Default → jump to Application
                       │
               ┌───────▼──────────────────────────────────────┐
               │  SBL (Secondary Bootloader / Reprogramming)  │
               │  ├── Receives DoIP/CAN TP UDS requests       │
               │  ├── Processes 0x34, 0x36, 0x37 services    │
               │  ├── Erases and programs target flash areas  │
               │  ├── Validates CRC/hash of received data     │
               │  └── Sets valid flag, triggers reset         │
               └──────────────────────────────────────────────┘
```

### Flashing Validation Test Cases

```
TC-FLASH-001: Normal Flash Sequence
  Prerequisites: ECU in default session
  Steps: Session → SecurityAccess → Erase → Download → Verify → Reset
  Expected: ECU boots with new SW version (confirm via 0x22 F189)
  
TC-FLASH-002: Wrong Security Key Rejection
  Steps: Send wrong key 3 times in programming session
  Expected: NRC 0x35 (exceededNumberOfAttempts) after 3rd failure
             10-minute lockout before retry

TC-FLASH-003: Block Transfer Interruption
  Steps: Start download, interrupt after 10 blocks, reconnect and retry
  Expected: ECU allows restart of full download sequence
             No permanent damage to ECU

TC-FLASH-004: CRC Verification Failure
  Steps: Flash valid firmware, corrupt 1 byte, send CheckMemory
  Expected: CheckMemory fails with negative response
             ECU stays in bootloader (does not accept corrupted image)

TC-FLASH-005: Anti-Rollback Check
  Steps: Flash firmware version 2.0.0, then try to flash 1.0.0
  Expected: Version check in SBL rejects older version
             NRC 0x72 (generalProgrammingFailure)

TC-FLASH-006: Flash Performance Measurement
  Steps: Flash 8MB firmware, measure total time
  Expected: < 3 minutes via DoIP over 100BASE-T1
             (calculation: 8MB / 100Mbps × 8 = 0.64s + overhead)
```

---

## 7.7 WIRESHARK — UDS/DoIP ANALYSIS

### Wireshark Filters for Diagnostic Analysis

```
ESSENTIAL WIRESHARK FILTERS FOR DIAGNOSTICS:

# All DoIP traffic
doip

# DoIP diagnostic messages only
doip.payload_type == 0x8001

# UDS negative responses (NRC analysis)
doip && frame contains "7f"

# Specific UDS service (0x10 = session, 0x27 = security access)
doip && frame[16] == 0x10     # Session control
doip && frame[16] == 0x27     # Security access
doip && frame[16] == 0x7f     # Negative response

# TCP connection management (DoIP)
tcp.port == 13400

# Timing analysis — requests without quick response
tcp.analysis.ack_rtt > 0.1   # ACK round-trip > 100ms
tcp.analysis.retransmission  # Retransmitted segments

# Filter specific ECU by logical address
# DoIP Diagnostic Message: Source@offset 8 (2 bytes), Target@offset 10 (2 bytes)
# This requires custom Lua dissector for easy viewing
```

### Python Script — Automated DoIP Testing

```python
#!/usr/bin/env python3
"""
Automotive DoIP Test Client
Sends UDS requests via DoIP TCP connection
"""

import socket
import struct
import time

DOIP_UDP_PORT = 13400
DOIP_TCP_PORT = 13400
TESTER_ADDR   = 0xE000
TARGET_ADDR   = 0x0010   # ADAS ECU

def build_doip_header(payload_type: int, payload: bytes) -> bytes:
    """Build DoIP generic header."""
    return struct.pack(
        ">BBHI",
        0x02,           # Protocol version
        0xFD,           # Inverse protocol version
        payload_type,   # Payload type
        len(payload)    # Payload length
    ) + payload

def routing_activation_request() -> bytes:
    """Build DoIP Routing Activation Request."""
    payload = struct.pack(
        ">HBH",
        TESTER_ADDR,    # Source address
        0x00,           # Activation type (default)
        0x0000          # Reserved
    )
    return build_doip_header(0x0005, payload)

def diagnostic_message(uds_data: bytes) -> bytes:
    """Build DoIP Diagnostic Message."""
    payload = struct.pack(">HH", TESTER_ADDR, TARGET_ADDR) + uds_data
    return build_doip_header(0x8001, payload)

def parse_doip_response(data: bytes) -> dict:
    """Parse DoIP header and return info dict."""
    if len(data) < 8:
        return {}
    proto_ver, inv_ver, payload_type, payload_len = struct.unpack(">BBHI", data[:8])
    return {
        "payload_type": payload_type,
        "payload_len": payload_len,
        "payload": data[8:8 + payload_len]
    }

class DoIPClient:
    def __init__(self, ecu_ip: str):
        self.ecu_ip = ecu_ip
        self.sock = None

    def connect(self) -> bool:
        """Establish TCP connection to DoIP gateway."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect((self.ecu_ip, DOIP_TCP_PORT))
            print(f"[OK] Connected to DoIP gateway at {self.ecu_ip}:13400")
            return True
        except Exception as e:
            print(f"[ERR] Connection failed: {e}")
            return False

    def activate_routing(self) -> bool:
        """Send Routing Activation Request."""
        request = routing_activation_request()
        self.sock.send(request)
        response = self.sock.recv(1024)
        parsed = parse_doip_response(response)
        if parsed.get("payload_type") == 0x0006:
            resp_code = parsed["payload"][4]  # Response code byte
            if resp_code == 0x10:
                print("[OK] Routing Activation successful")
                return True
        print(f"[ERR] Routing Activation failed: {parsed}")
        return False

    def send_uds(self, uds_bytes: bytes) -> bytes:
        """Send UDS request via DoIP and return UDS response."""
        request = diagnostic_message(uds_bytes)
        self.sock.send(request)

        # First response: DiagMsg Ack (0x8002)
        response = self.sock.recv(1024)
        parsed = parse_doip_response(response)
        if parsed.get("payload_type") != 0x8002:
            print(f"[WARN] Expected DiagMsg Ack, got: 0x{parsed.get('payload_type', 0):04X}")

        # Second response: DiagMsg with UDS response (0x8001)
        response = self.sock.recv(4096)
        parsed = parse_doip_response(response)
        if parsed.get("payload_type") == 0x8001:
            return parsed["payload"][4:]  # Skip 4-byte address prefix → UDS data
        return b""

    def read_ecu_version(self) -> str:
        """Read SW version via UDS 0x22 0xF189."""
        response = self.send_uds(bytes([0x22, 0xF1, 0x89]))
        if response and response[0] == 0x62:
            return response[3:].decode("ascii", errors="replace")
        return "READ FAILED"

    def close(self):
        if self.sock:
            self.sock.close()

# Main test execution
if __name__ == "__main__":
    client = DoIPClient("192.168.1.50")

    if not client.connect():
        exit(1)

    if not client.activate_routing():
        exit(1)

    # Test 1: Read SW version
    version = client.read_ecu_version()
    print(f"[INFO] ADAS ECU SW Version: {version}")

    # Test 2: Enter extended session
    resp = client.send_uds(bytes([0x10, 0x03]))
    if resp and resp[0] == 0x50:
        print("[OK] Extended diagnostic session active")
    else:
        print(f"[FAIL] Session control failed: {resp.hex()}")

    # Test 3: Clear DTCs
    resp = client.send_uds(bytes([0x14, 0xFF, 0xFF, 0xFF]))
    if resp and resp[0] == 0x54:
        print("[OK] All DTCs cleared")

    client.close()
```

---

## 7.8 INTERVIEW QUESTIONS — SECTION 7

**Q1: Explain the difference between UDS sessions and when each is used.**
> Default session (0x01) is available after ECU startup and allows basic reads. Extended session (0x03) enables full diagnostic access — requires TesterPresent every 5 seconds to maintain, allows write operations with security access. Programming session (0x02) is for ECU flashing — typically requires high-voltage conditions not met during normal driving, and enables download services (0x34/0x36/0x37). Session transitions are managed via service 0x10.

**Q2: What is Security Access (0x27) and how does it work?**
> Security Access uses a Seed-Key mechanism to prevent unauthorized ECU modification. The tester sends a seed request (odd subfunction like 0x01). The ECU returns a random seed value. The tester computes a key using an OEM-defined algorithm (typically XOR, AES, or custom). The tester sends the key (even subfunction like 0x02). If correct, the ECU grants access for that session. Wrong keys 3× trigger a lockout (NRC 0x35) with a mandatory wait period.

**Q3: How does DoIP handle routing to different ECUs behind a gateway?**
> DoIP gateway maintains a routing table mapping logical addresses to physical ECUs. After TCP connection, the tester sends Routing Activation with its source logical address. The gateway associates that TCP connection with that source address. When the tester sends DiagMsg with target logical address (e.g., 0x0010), the gateway looks up the routing table, translates to the target ECU's transport (CAN TP, internal Ethernet), forwards the UDS payload, waits for the ECU response, and tunnels it back to the tester.

**Q4: What is the NRC 0x78 and why is it important for flash operations?**
> NRC 0x78 = `requestCorrectlyReceivedResponsePending`. When an ECU receives a request but needs more time to process (e.g., flash erase taking 3 seconds), it sends 0x78 to tell the tester "I got your request, working on it, don't time out." The tester resets its P2* timer on each 0x78. The ECU can send multiple 0x78 responses until the operation completes, then sends the final positive or negative response.

**Q5: How would you validate a complete DoIP flashing sequence in an automated test?**
> I would write a Python/CAPL test that: (1) Discovers the ECU via UDP VehicleIdentityRequest. (2) Establishes TCP connection and activates routing. (3) Sends session 0x10 02 and security access 0x27 for programming. (4) Executes erase routine 0x31 and waits for completion. (5) Sends RequestDownload 0x34 with firmware size. (6) Transfers all blocks via 0x36, verifying each 0x76 ack. (7) Sends RequestTransferExit 0x37. (8) Runs CheckMemory routine 0x31. (9) Sends ECUReset 0x11. (10) Reconnects and reads SW version 0x22 F189 to confirm new firmware version.

---

*Next Section → [Section 8: HIL Testing](08_HIL_Testing.md)*
