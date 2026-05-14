# DoIP — DEEP DIVE
## Module 3 of 7 | advanced_automotive_learning

---

## 1. WHAT IS DoIP?

**DoIP** = Diagnostics over Internet Protocol (ISO 13400)

Traditional vehicle diagnostics ran over CAN using TP (ISO 15765-2) — slow, 8-byte frames, one message at a time. Modern vehicles with 100+ ECUs and software packages up to several GB needed something faster.

DoIP routes UDS diagnostic messages over **TCP/IP on Automotive Ethernet**, delivering:
- Up to 1 Gbps throughput (vs ~1 Mbps CAN)
- Simultaneous multi-ECU diagnostics
- OTA software updates over the same infrastructure
- Remote diagnostics over cellular (telematics + DoIP)

```
TRADITIONAL DIAGNOSTICS:              DoIP DIAGNOSTICS:
  Tester ──CAN TP──► ECU               Tester ──Ethernet──► Gateway
  Max: ~1 Mbps                                               │
  1 ECU at a time                       ────────────────────►│ ECU_A
  Max payload: 4095 bytes (CanTp)       ────────────────────►│ ECU_B
                                                             ►│ ECU_C
                                        Max: 1 Gbps
                                        All ECUs simultaneously
```

---

## 2. DoIP ARCHITECTURE

```
VEHICLE NETWORK:

  ┌──────────────────────────────────────────────────────────┐
  │                    EXTERNAL TESTER                        │
  │         (CANoe + DoIP plugin, or Python client)          │
  └───────────────────────┬──────────────────────────────────┘
                          │ Ethernet / TCP 13400
                          │
  ┌───────────────────────▼──────────────────────────────────┐
  │                  DoIP GATEWAY / EDGE NODE                 │
  │  - Accepts external TCP connections (port 13400)         │
  │  - Authenticates tester (Routing Activation)             │
  │  - Routes UDS to internal ECUs via internal bus          │
  │  - Vehicle Identification, Announcement                  │
  └──────┬──────────────┬──────────────┬─────────────────────┘
         │ CAN TP       │ Ethernet     │ LIN / FR
         ▼              ▼              ▼
    ECU_A (BCM)    ECU_B (ADAS)   ECU_C (Instrument)
    0x0010         0x0020         0x0030
```

### Key Participants

| Role | Description |
|------|-------------|
| External Test Equipment (ETE) | Laptop/tester with DoIP client |
| DoIP Gateway | Entry point into vehicle, authenticates tester |
| DoIP Node | ECU that speaks DoIP directly |
| Internal Gateway | Routes across internal buses (CAN, LIN) |
| Logical Address | Unique identifier per ECU (2 bytes, e.g., 0x0010) |

---

## 3. DoIP PROTOCOL DETAILS

### 3.1 Transport Layer

```
DoIP uses:
  TCP port 13400 — diagnostic messages (reliable, ordered)
  UDP port 13400 — vehicle discovery, announcement (lightweight)

Both TCP and UDP use port 13400.
TCP: connection-oriented, reliable delivery, for UDS
UDP: discovery only (Vehicle Identification, VehicleAnnouncement)
```

### 3.2 DoIP Header Format

```
DoIP GENERIC HEADER (8 bytes, every message starts with this):

  Byte:  0    1    2    3    4    5    6    7
       ┌────┬────┬────┬────┬────┬────┬────┬────┐
       │ Ver│~Ver│  Payload Type (2B)  │  Length │
       │    │    │                    │  (4B)   │
       └────┴────┴────┴────┴────┴────┴────┴────┘

  Ver:          0x02 (ISO 13400-2:2012), 0x03 (2019)
  ~Ver:         Bitwise inverse of Ver (0xFD for 0x02) — error detection
  Payload Type: Identifies message type (see table below)
  Length:       Byte count of payload (not including 8-byte header)
```

### 3.3 Payload Types

```
PAYLOAD TYPE       HEX      DIRECTION    PURPOSE
─────────────────────────────────────────────────────────────────
GenericDoIpNegAck  0x0000   Any          Error response
VehicleIdentReq    0x0001   T→G (UDP)    "Who is there?"
VehicleIdentEID    0x0002   T→G (UDP)    Find by EID
VehicleIdentVIN    0x0003   T→G (UDP)    Find by VIN
VehicleAnnounce    0x0004   G→T (UDP)    Response with VIN, EID, GID
RoutingActReq      0x0005   T→G (TCP)    "Activate this connection"
RoutingActResp     0x0006   G→T (TCP)    Accept/reject activation
AliveCheckReq      0x0007   G→T (TCP)    Keepalive probe
AliveCheckResp     0x0008   T→G (TCP)    Keepalive response
EntityStatusReq    0x4001   T→G (TCP)    Query gateway status
EntityStatusResp   0x4002   G→T (TCP)    Gateway status (max conn, etc.)
DiagMsg            0x8001   T→G (TCP)    UDS request payload
DiagMsgPosAck      0x8002   G→T (TCP)    UDS delivered to ECU
DiagMsgNegAck      0x8003   G→T (TCP)    Delivery failed
```

### 3.4 Logical Addresses

```
LOGICAL ADDRESS RANGES:
  0x0000        = Generic DoIP gateway address
  0x0001–0x0DFF = External test equipment (testers)
  0x0E00–0x0FFF = DoIP entities (gateways, internal nodes)
  0x1000–0xFFFE = ECU addresses (vehicle-specific assignment)
  0xFFFF        = Functional addressing (broadcast to all ECUs)

FUNCTIONAL vs PHYSICAL ADDRESSING:
  Physical (0x0010):  "Send this UDS request to ECU at 0x0010 only"
  Functional (0xFFFF): "Send to ALL ECUs simultaneously" 
                       (used for: TesterPresent, ECUReset broadcast)
```

---

## 4. COMPLETE DoIP SEQUENCE — STEP BY STEP

```
EXTERNAL TESTER                         DOIP GATEWAY
     │                                        │
     │──── UDP Broadcast ────────────────────►│
     │  VehicleIdentificationRequest          │
     │  Src: 255.255.255.255:13400            │
     │  Payload Type: 0x0001                  │
     │                                        │
     │◄─── UDP Response ─────────────────────│
     │  VehicleAnnouncement                   │
     │  Payload Type: 0x0004                  │
     │  VIN: "WAUZZZ8V6KN000000" (17B)       │
     │  EID: AA:BB:CC:DD:EE:FF (6B)          │
     │  GID: 00:00:00:00:00:01 (6B)          │
     │  Gateway Logical Addr: 0x0E00          │
     │                                        │
     │══ TCP Connect → 192.168.20.10:13400 ══│
     │  (3-way handshake SYN/SYN-ACK/ACK)    │
     │                                        │
     │──── RoutingActivationRequest ─────────►│
     │  Payload Type: 0x0005                  │
     │  Source Address: 0x0E01 (tester)       │
     │  ActivationType: 0x00 (default)        │
     │                                        │
     │◄─── RoutingActivationResponse ────────│
     │  Payload Type: 0x0006                  │
     │  Tester Addr: 0x0E01                   │
     │  Gateway Addr: 0x0E00                  │
     │  ResponseCode: 0x10 (Routing success!) │
     │                                        │
     │──── DiagnosticMessage ────────────────►│
     │  Payload Type: 0x8001                  │
     │  Source Addr: 0x0E01                   │
     │  Target Addr: 0x0010 (BCM)            │
     │  UDS Payload: [10 03]                  │
     │                (0x10=DiagSession 0x03=Extended)
     │                                        │
     │◄─── DiagnosticMessagePositiveAck ─────│
     │  Payload Type: 0x8002                  │
     │  (Message delivered to BCM!)           │
     │                                        │
     │◄─── DiagnosticMessage (response) ─────│
     │  Source Addr: 0x0010 (BCM)            │
     │  Target Addr: 0x0E01 (tester)         │
     │  UDS Payload: [50 03 00 19 01 F4]      │
     │  (Session Control positive response)   │
     │                                        │
     │══ TCP Close ══════════════════════════│
```

---

## 5. DoIP GATEWAY ROUTING

The gateway routes incoming DoIP diagnostic messages to internal ECUs — each ECU may be on a different bus.

```
ROUTING TABLE EXAMPLE:

Logical Address  │ Physical Bus  │ Bus Address │ ECU Name
─────────────────┼───────────────┼─────────────┼──────────────
0x0010           │ CAN 1         │ CAN ID 0x7DF│ BCM (Body)
0x0020           │ CAN 2         │ CAN ID 0x760│ ADAS Domain
0x0030           │ Ethernet Vlan │ IP 192.168.10.20 │ Camera ECU
0x0040           │ LIN 1         │ LIN Node 0x06 │ Instrument
0xFFFF           │ ALL (functional) │ Broadcast │ All ECUs

ROUTING PROCESS:
1. Tester sends DiagMsg with TargetAddr = 0x0010
2. Gateway looks up 0x0010 in routing table
3. Gateway converts to CAN TP frame: CanTp.N_USDATA([10 03], ID=0x7DF)
4. BCM responds via CAN TP
5. Gateway wraps response in DoIP DiagMsg and sends to tester
```

---

## 6. DoIP FLASH SEQUENCE (OTA UPDATE)

```
TESTER (OTA Server)             GATEWAY → TARGET ECU

1. Enter Programming Session:
   ─────────────────────────────────────────────────
   DiagMsg: [10 02]    →        UDS SessionControl(Programming)
   DiagMsgPosAck       ←        Delivery ACK
   DiagMsg: [50 02...] ←        UDS Response: OK

2. Security Access:
   ─────────────────────────────────────────────────
   DiagMsg: [27 01]    →        Request Seed
   DiagMsg: [67 01 XX XX XX XX] ← Seed received
   DiagMsg: [27 02 KK KK KK KK] → Send Key (seed+secret)
   DiagMsg: [67 02]    ←        Access Granted

3. Request Download:
   ─────────────────────────────────────────────────
   DiagMsg: [34 00 44 ADDR ADDR ADDR ADDR SIZE SIZE SIZE SIZE] →
   DiagMsg: [74 20 04 00] ← MaxBlockSize = 0x400 = 1024 bytes

4. Transfer Data (loop):
   ─────────────────────────────────────────────────
   DiagMsg: [36 01 DATA...] →   Block 1 (up to 1024B)
   DiagMsg: [76 01]         ←   Block 1 accepted
   DiagMsg: [36 02 DATA...] →   Block 2
   DiagMsg: [76 02]         ←   Block 2 accepted
   ... (repeat for entire firmware image)

5. Transfer Exit:
   ─────────────────────────────────────────────────
   DiagMsg: [37]        →       End of data
   DiagMsg: [77]        ←       Transfer complete

6. Checksum Verification:
   ─────────────────────────────────────────────────
   DiagMsg: [31 01 FF 01 ADDR SIZE CRC32] → RoutineControl(CheckMemory)
   DiagMsg: [71 01 FF 01 00]              ← Checksum OK

7. Reset:
   ─────────────────────────────────────────────────
   DiagMsg: [11 01]    →        ECUReset(Hard)
   DiagMsg: [51 01]    ←        Reset acknowledged
```

---

## 7. DEBUGGING TEST CASES

### TC-DoIP-001: Vehicle Discovery
```
Objective: Verify gateway responds to VehicleIdentificationRequest
Steps:
  1. Send UDP broadcast to 255.255.255.255:13400
     Payload: [02 FD 00 01 00 00 00 00]
  2. Capture response
Expected:
  - Response within 500ms
  - Payload Type = 0x0004 (VehicleAnnouncement)
  - VIN field = configured VIN
  - Gateway logical address = 0x0E00
Wireshark filter: doip.payload_type == 0x0004
```

### TC-DoIP-002: Routing Activation
```
Objective: Verify routing activation with default type succeeds
Steps:
  1. TCP connect to 192.168.20.10:13400
  2. Send RoutingActivationRequest (Type=0x00)
Expected:
  - RoutingActivationResponse with ResponseCode=0x10 (success)
  - ResponseCode=0x06 would mean "denied" (check tester IP whitelist)
```

### TC-DoIP-003: Multi-ECU Parallel Diagnostics
```
Objective: Verify gateway routes to correct ECU
Steps:
  1. Send DiagMsg(TargetAddr=0x0010): [22 F1 90] (read VIN from BCM)
  2. Send DiagMsg(TargetAddr=0x0020): [22 F1 90] (read VIN from ADAS)
Expected:
  - Two DiagMsgPosAck received
  - Two UDS responses, each from correct logical address
  - No cross-routing (BCM response has SrcAddr=0x0010, not 0x0020)
```

### TC-DoIP-004: Connection Alive Check
```
Objective: Verify gateway sends AliveCheckRequest on idle TCP connection
Steps:
  1. Establish routing activation
  2. Send no traffic for A_DoIP_General_Inactivity_Time (500ms default)
  3. Monitor for AliveCheckRequest from gateway
Expected:
  - AliveCheckRequest received within A_DoIP_General_Inactivity_Time
  - Tester responds with AliveCheckResponse
  - Connection maintained after alive check
```

---

## 8. INTERVIEW Q&A

**Q1: What is DoIP and how does it differ from traditional CAN diagnostics?**
> DoIP (ISO 13400) routes UDS diagnostic messages over TCP/IP on Ethernet instead of CAN Transport Protocol. CAN diagnostics: max ~1 Mbps, one ECU at a time, 4095-byte max message. DoIP: up to 1 Gbps, multiple ECUs simultaneously, unlimited payload size, remote diagnostics via telematics. Same UDS services (0x10, 0x22, etc.) — just different transport.

**Q2: What is Routing Activation and why is it needed?**
> Routing Activation (Payload Type 0x0005) is DoIP's authentication step. After TCP connect, the tester must send a RoutingActivationRequest. The gateway verifies the tester is authorized (by IP, OEM-specific authentication, or certificate) and responds with RoutingActivationResponse code 0x10 (success) or 0x06 (denied). Without successful routing activation, the gateway will reject all subsequent DiagnosticMessage requests. It prevents unauthorized devices from performing diagnostics.

**Q3: What is the difference between physical and functional addressing in DoIP?**
> Physical addressing: DiagMsg sent to a specific ECU logical address (e.g., 0x0010 = BCM). Only that ECU processes and responds. Functional addressing: DiagMsg sent to 0xFFFF. All ECUs that support the service process the request. Used for TesterPresent (keep all ECUs active), ECUReset broadcast, and VIN reads across all ECUs. Functional addressing → multiple ECU responses possible.

**Q4: Walk me through a complete OTA flash sequence using DoIP.**
> 1. Vehicle Discovery (UDP): find gateway by VIN/EID. 2. TCP connect to port 13400. 3. RoutingActivation (authenticate). 4. DiagMsg [10 02] → enter Programming Session. 5. DiagMsg [27 01] → request seed, [27 02 + key] → unlock security access. 6. DiagMsg [34...] → RequestDownload with address and size. 7. DiagMsg [36 01 ...data...] × N blocks → TransferData. 8. DiagMsg [37] → RequestTransferExit. 9. DiagMsg [31 01 FF 01 + CRC] → verify checksum. 10. DiagMsg [11 01] → ECUReset. Total 10 phases, all over one TCP connection.

**Q5: What does DoIP NegativeAck code mean?**
> DiagMsgNegativeAck (Payload Type 0x8003) means the gateway could not deliver the UDS message to the target ECU. NACK codes: 0x02 = Invalid Source Address; 0x03 = Unknown Target Address (ECU not in routing table); 0x04 = Message too large; 0x05 = Out of memory; 0x06 = Target unreachable (ECU sleeping or not responding to bus); 0x07 = Unknown Network; 0x08 = Transport Protocol Error.

---

*Next: [02_STAR_Answers.md](02_STAR_Answers.md)*
