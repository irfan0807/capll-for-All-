# SECTION 15 — FINAL INTERVIEW CRASH COURSE
## Course: Automotive Ethernet Testing — Complete Industry Training

### HOW TO USE THIS SECTION
Read this the week before your interview. All key facts in one place. Study each cheat sheet once per day. By Day 7, you should be able to recite these without looking.

---

## CHEAT SHEET 1 — AUTOMOTIVE ETHERNET PROTOCOLS

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUTOMOTIVE ETHERNET — KEY FACTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STANDARDS:
  100BASE-T1  = IEEE 802.3bw = 100 Mbps on 1 pair
  1000BASE-T1 = IEEE 802.3bp = 1 Gbps on 1 pair
  10GBASE-T1  = IEEE 802.3ch = 10 Gbps on 1 pair

PHYSICAL LAYER:
  PHY chip example: NXP TJA1100 (100BASE-T1)
  Config: One end = Master (clock source), other = Slave
  Cable: Single unshielded twisted pair, max 15m
  No auto-negotiation — manual master/slave config

FRAME STRUCTURE (Ethernet + VLAN):
  [Preamble 7B][SFD 1B][Dst MAC 6B][Src MAC 6B]
  [TPID 0x8100 2B][TCI 2B][EtherType 2B][Payload 46-1500B][FCS 4B]
  TCI = PCP(3b) + DEI(1b) + VLAN_ID(12b)

VLAN IDs in automotive (typical):
  VLAN 10: ADAS/Safety (PCP=7, highest priority)
  VLAN 20: Diagnostics/DoIP
  VLAN 30: Infotainment
  VLAN 40: OTA update
  VLAN 50: V2X/Telematics

TSN STANDARDS:
  802.1AS   = gPTP (< 1µs accuracy, replaces PTP)
  802.1Qbv  = TAS (Time-Aware Shaper, gate schedules)
  802.1Qbu  = Frame Preemption
  802.1Qav  = Credit-Based Shaper (AVB audio/video)
  802.1CB   = Frame Replication & Elimination (redundancy)

SWITCH:
  NXP SJA1110: 10 ports (8× 100BASE-T1, 2× SGMII)
                TSN, VLAN, TCAM firewall, port mirroring
                
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SOME/IP — QUICK REFERENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HEADER (16 bytes):
  [Service ID 2B][Method ID 2B][Length 4B][Client ID 2B]
  [Session ID 2B][Protocol Ver 1B][Interface Ver 1B]
  [Message Type 1B][Return Code 1B][Payload...]

METHOD ID RANGES:
  0x0001-0x7FFF = Methods (Request/Response)
  0x8000-0x8FFF = Events (Notifications)
  0xF000        = Ping/Heartbeat

MESSAGE TYPES:
  0x00 = REQUEST           0x40 = REQUEST_NO_RETURN
  0x80 = NOTIFICATION      0x01 = RESPONSE
  0x81 = ERROR

RETURN CODES:
  0x00 = E_OK              0x01 = E_NOT_OK
  0x02 = (used in NOTIFICATION)
  0x0D = E_UNKNOWN_SERVICE  0x0E = E_UNKNOWN_METHOD

SOME/IP-SD DEFAULT:
  Multicast: 224.224.224.245:30490
  TTL: 0xFFFFFF = infinite subscription

TRANSPORT:
  Methods → UDP or TCP (depending on data size)
  Events → UDP (low latency, loss-tolerant)
  Large data → TCP (guaranteed delivery)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DoIP — QUICK REFERENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PORTS: TCP 13400 (diagnostics), UDP 13400 (discovery)

HEADER (8 bytes):
  [Version 0x02][~Version 0xFD][Payload Type 2B][Length 4B]

KEY PAYLOAD TYPES:
  0x0001 = VehicleIdentificationRequest (UDP broadcast)
  0x0004 = VehicleAnnouncement (contains VIN, EID, GID)
  0x0005 = RoutingActivationRequest
  0x0006 = RoutingActivationResponse (0x10 = success)
  0x8001 = DiagnosticMessage (UDS payload)
  0x8002 = DiagnosticMessagePositiveAck
  0x8003 = DiagnosticMessageNegativeAck

SEQUENCE:
  UDP Discovery → TCP Connect → RoutingActivation → DiagMsg

LOGICAL ADDRESSES:
  0xE000 = Default tester address
  0x0010-0xFFFE = ECU logical addresses
  0xFFFF = Functional addressing (broadcast)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## CHEAT SHEET 2 — UDS DIAGNOSTICS

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UDS (ISO 14229) — MUST-KNOW SERVICES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

0x10 DiagnosticSessionControl:
  01=Default, 02=Programming, 03=Extended
  Request: 10 02 → Response: 50 02 [P2 hi] [P2 lo] [P2* hi] [P2* lo]

0x11 ECUReset:
  01=HardReset, 03=SoftReset
  Request: 11 01 → Response: 51 01

0x14 ClearDiagnosticInformation:
  Request: 14 FF FF FF → Response: 54

0x19 ReadDTCInformation:
  19 02 FF = All DTCs by status mask
  19 02 08 = Only confirmed DTCs
  Response: 59 02 [avail mask] [DTC1 3B] [status 1B] ...

0x22 ReadDataByIdentifier:
  Request: 22 F1 90 (VIN) → Response: 62 F1 90 [VIN 17 bytes]

0x27 SecurityAccess:
  Request seed: 27 01 → Response: 67 01 [seed bytes]
  Send key:     27 02 [key bytes] → Response: 67 02
  Wrong key 3×: NRC 0x35 (lockout)

0x2E WriteDataByIdentifier:
  Request: 2E [DID 2B] [data...] → Response: 6E [DID 2B]

0x31 RoutineControl:
  01=Start, 02=Stop, 03=RequestResult
  Request: 31 01 FF 00 [params] → Response: 71 01 FF 00

0x34 RequestDownload (Flash start):
  Request: 34 [format] [addr+len format] [address 4B] [size 4B]
  Response: 74 20 [maxBlockLen 2B]

0x36 TransferData:
  Request: 36 [block#] [data...] → Response: 76 [block#]

0x37 RequestTransferExit:
  Request: 37 → Response: 77

0x3E TesterPresent (keep-alive):
  Request: 3E 00 → Response: 7E 00

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UDS NEGATIVE RESPONSE CODES (NRC)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Format: 7F [SID] [NRC]

0x10 = generalReject
0x11 = serviceNotSupported
0x12 = subFunctionNotSupported
0x13 = incorrectMessageLengthOrInvalidFormat
0x22 = conditionsNotCorrect (speed, mode)
0x24 = requestSequenceError (wrong order of calls)
0x25 = noResponseFromSubnetComponent
0x26 = failurePreventsExecutionOfRequestedAction
0x31 = requestOutOfRange (invalid DID or parameter)
0x33 = securityAccessDenied (session doesn't allow it)
0x35 = invalidKey (wrong key / too many attempts)
0x36 = exceededNumberOfAttempts (lock-out)
0x37 = requiredTimeDelayNotExpired (waiting for cooldown)
0x70 = uploadDownloadNotAccepted
0x71 = transferDataSuspended
0x72 = generalProgrammingFailure (flash write failed)
0x73 = wrongBlockSequenceCounter
0x78 = requestCorrectlyReceivedResponsePending (wait!)
0x7E = subFunctionNotSupportedInActiveSession
0x7F = serviceNotSupportedInActiveSession

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STANDARD DIDs:
  F186 = ActiveDiagnosticSession     F18C = ECUSerialNumber
  F187 = SparePartNumber             F18D = VehicleManufacturerSparePartNumber
  F188 = ApplicationSoftwareIdentifier  F190 = VIN (17 chars)
  F189 = ApplicationSoftwareVersionNumber
  F18A = BootSoftwareIdentifier      F191 = HardwareVersionNumber
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## CHEAT SHEET 3 — AUTOSAR

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUTOSAR CLASSIC — LAYER STACK (top to bottom)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Application Layer: SWC (Software Components — business logic)
          ↕ RTE (Runtime Environment — generated, connects SWCs)
BSW (Basic Software):
  ├── Communication Stack:
  │   SomeIpXf → SomeIpSd → SoAd → TcpIp → EthIf → Eth → EthTrcv
  │   (for Ethernet)
  │   COM → PduR → CanTp → CanIf → Can → Transceiver
  │   (for CAN)
  ├── Diagnostic Stack:
  │   DCM ← DEM ← SWC (error reports)
  │   DCM → PduR → CanTp/SoAd (diagnostic transport)
  ├── Memory Stack: NvM → MemIf → Fee/Ea → Flash/EEPROM driver
  ├── System: EcuM, BswM, WdgM, OS (OSEK)
  └── MCAL: Eth, Can, Spi, Adc, Dio, Pwm, Lin ...
Hardware: MCU (AURIX/S32K) + PHY + Transceiver

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KEY AUTOSAR MODULES (must know):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RTE      Runtime Environment (generated, connects SWCs to BSW)
COM      Signal packing/unpacking for CAN, timeout monitoring
PduR     PDU routing between protocol layers (routing table)
CanIf    CAN Interface (hardware abstraction above CAN driver)
CanTp    CAN Transport Protocol (ISO 15765-2, segmentation)
EthIf    Ethernet Interface (VLAN handling, frame routing)
SoAd     Socket Adapter (UDP/TCP sockets for Ethernet)
TcpIp    TCP/IP stack (IPv4/IPv6, UDP, TCP, DHCP, DNS)
SomeIpXf SOME/IP Transformer (serialization/deserialization)
DCM      Diagnostic Communication Manager (UDS handler)
DEM      Diagnostic Event Manager (DTC management)
NvM      Non-volatile Memory Manager (EEPROM/Flash abstraction)
WdgM     Watchdog Manager (watchdog checkpoints)
EcuM     ECU Mode Manager (startup, shutdown, sleep)
BswM     BSW Mode Manager (mode-dependent routing)
SchM     Schedule Manager (generated, triggers Runnables)
OS       AUTOSAR OS (OSEK-based, tasks, alarms, events)
MCAL     Microcontroller Abstraction Layer (hardware drivers)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SWC PORTS:
  P-Port (Provide) = output data/service
  R-Port (Require) = input data/service
  Communication: Sender/Receiver (data), Client/Server (service)
  Inter-ECU: COM/PduR/CanIf/EthIf/SoAd routes data to other ECU
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## CHEAT SHEET 4 — CAPL QUICK REFERENCE

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAPL STRUCTURE + KEY SYNTAX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

variables {
  message 0x100 myMsg;   // CAN message object
  msTimer myTimer;        // One-shot timer
  int count = 0;          // Global variable
}

/* EVENT HANDLERS */
on start { ... }                    // Measurement started
on stopMeasurement { ... }          // Measurement stopped
on message 0x100 { ... }           // CAN message received (by ID)
on message FCW_Status { ... }       // CAN message by DBC name
on ethernetPacket { ... }           // Any Ethernet frame
on timer myTimer { ... }            // Timer fired
on key 'a' { ... }                  // Keyboard shortcut
on sysvar SysVar::MyVar { ... }    // System variable changed

/* TIMER FUNCTIONS */
setTimer(myTimer, 100);             // Arm timer (100ms)
cancelTimer(myTimer);               // Cancel timer

/* CAN MESSAGE ACCESS */
output(myMsg);                      // Send CAN message
this.byte(0)                        // Byte 0 of received message
this.word(0)                        // 2 bytes from offset 0
this.dword(0)                       // 4 bytes from offset 0
this.dlc                            // Data Length Code
$VehicleSpeed                       // Direct signal access (DBC)

/* ETHERNET ACCESS */
this.eth.srcAddr                    // Source MAC
this.eth.dstAddr                    // Destination MAC
this.udp.destPort                   // UDP destination port
this.udp.srcPort                    // UDP source port

/* UTILITY FUNCTIONS */
write("Debug: %d", value);          // Write to output window
timeNow()                           // Current time in 10ns units
setBusOff("CAN1");                  // Force CAN bus-off

/* TEST FUNCTIONS (vTESTstudio) */
testCaseTitle("TC-001", "SOME/IP Event Test");
testStepPass("Step 1", "Event received");
testStepFail("Step 2", "No response");
testCaseFail();                     // Mark entire test case failed

/* TYPES */
byte, word, dword, int, long, float, double, char, string

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## CHEAT SHEET 5 — WIRESHARK FILTERS

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WIRESHARK DISPLAY FILTERS — AUTOMOTIVE CHEAT SHEET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SOME/IP:
  someip                              All SOME/IP frames
  someip.serviceid == 0x1234          Specific service
  someip.methodid >= 0x8000           Events only
  someip.messagetype == 0x80          Notifications
  udp.port == 30490                   SOME/IP default port

SOME/IP-SD:
  someip-sd                           All SD frames
  someip-sd.type == 1                 OfferService
  someip-sd.type == 6                 SubscribeEventgroup

DoIP:
  doip                                All DoIP
  doip.payload_type == 0x0005         Routing Activation Request
  doip.payload_type == 0x8001         Diagnostic Message
  tcp.port == 13400                   DoIP TCP
  udp.port == 13400                   DoIP UDP (discovery)

UDS (within DoIP):
  doip && frame contains 7f:          UDS Negative Response
  doip && frame[16] == 0x10          Session Control (byte offset 16 in DoIP)

TCP:
  tcp.analysis.retransmission         Retransmissions (performance issue)
  tcp.analysis.ack_rtt > 0.1         Slow ACK (> 100ms)
  tcp.flags.syn == 1                  SYN packets only
  tcp.flags.fin == 1                  FIN (connection close)
  tcp.flags.rst == 1                  RST (connection reset — error)

VLAN:
  vlan.id == 10                       ADAS VLAN
  eth.type == 0x8100                  VLAN tagged frames

gPTP:
  ptp                                 All PTP frames (gPTP)
  ptp.v2.messageid == 0               Sync messages
  ptp.v2.messageid == 8               Follow_Up messages
  eth.type == 0x88F7                  PTP EtherType

General:
  eth.src == 00:11:22:33:44:55        Source MAC filter
  eth.dst == ff:ff:ff:ff:ff:ff        Broadcast frames
  ip.src == 192.168.1.50              Source IP filter
  ip.dst == 224.224.224.245           SOME/IP-SD multicast
  !(arp || icmp)                      Exclude ARP and ICMP

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## CHEAT SHEET 6 — EMBEDDED C QUICK FACTS

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMBEDDED C — MUST-KNOW INTERVIEW FACTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

volatile:
  Prevents compiler from caching/optimizing the variable.
  Use for: HW registers, ISR-shared variables, DMA buffers.
  Example: volatile uint32_t *reg = (uint32_t *)0xFFF00100;

const:
  Read-only value. const uint8_t MAX = 255u;
  const pointer: const uint8_t *p = buf; (pointer to const)
  pointer const: uint8_t * const p = buf; (const pointer)
  both: const uint8_t * const p = buf; (const pointer to const)

static:
  Local: variable persists across calls
  Global/Function: limits scope to file (private)
  C++ member: shared across all instances

Endianness:
  Big-endian: MSB at lowest address (network byte order, SOME/IP)
  Little-endian: LSB at lowest address (Intel, ARM Cortex-M)
  Convert: htons(), htonl(), ntohs(), ntohl()

MISRA key rules:
  No heap (malloc/free) in production code
  All pointers must be NULL-checked
  No #define for constants (use const)
  No implicit type casting
  switch must have default case
  No unreachable code

Signal Extraction:
  raw = (frame_int >> start_bit) & ((1u << length) - 1u)
  physical = (raw * factor) + offset

Bitwise operations:
  Set bit:   val |=  (1u << bit);
  Clear bit: val &= ~(1u << bit);
  Toggle:    val ^=  (1u << bit);
  Test:      (val >> bit) & 1u

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## CHEAT SHEET 7 — CAN PROTOCOL FACTS

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAN (ISO 11898) — KEY FACTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FRAME STRUCTURE (Classical CAN):
  SOF + [11-bit ID or 29-bit ID] + RTR + DLC + Data(0-8B) + CRC + ACK + EOF

ARBITRATION:
  Lower CAN ID = Higher priority (dominant bit wins)
  IDs compared bit by bit — first dominant wins arbitration

BIT RATES: 125kbps, 250kbps, 500kbps, 1Mbps (classical max)

ERRORS:
  Bit Error, Stuff Error, CRC Error, Form Error, Acknowledgment Error
  TEC > 127 → Error Passive (node backs off)
  TEC > 255 → Bus-Off (node stops transmitting)
  Recovery: 128 × 11 recessive bits → Auto recovery (or reset)

TERMINATION: 120Ω at each end of the bus

CAN FD vs CAN:
  CAN FD: Up to 8 Mbps data rate, 64-byte payload
  CAN FD: Improved CRC (17-bit for ≤ 16B, 21-bit for > 16B)
  CAN FD DLC encoding for > 8 bytes:
    DLC 9 → 12B, DLC 10 → 16B, DLC 11 → 20B, DLC 12 → 24B
    DLC 13 → 32B, DLC 14 → 48B, DLC 15 → 64B

TOOLS: python-can, CANoe, CANalyzer, SocketCAN (Linux)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 7-DAY REVISION SCHEDULE

```
DAY 1 — Protocols:
  Morning: Read Cheat Sheet 1 (Automotive Ethernet)
  Evening: Answer 20 protocol questions from Section 10 (Q26–Q50)

DAY 2 — Diagnostics:
  Morning: Read Cheat Sheet 2 (UDS/DoIP)
  Evening: Explain DoIP flash sequence without looking at notes

DAY 3 — AUTOSAR:
  Morning: Read Cheat Sheet 3 (AUTOSAR)
  Evening: Draw full AUTOSAR Ethernet stack from memory

DAY 4 — Tools:
  Morning: Read Cheat Sheet 4 (CAPL)
  Evening: Write a SOME/IP event monitor in CAPL from scratch

DAY 5 — Debugging:
  Morning: Read Cheat Sheet 5 (Wireshark)
  Evening: Practice 10 debugging scenario answers (Q81–Q95)

DAY 6 — STAR Stories:
  Morning: Review 10 STAR answers from Section 11
  Evening: Record yourself answering 5 STAR questions

DAY 7 — Mock Interview:
  Full 60-minute mock interview with a friend or self-recorded
  Score yourself on: technical accuracy, clarity, STAR format, time

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## COMMON INTERVIEW MISTAKES — AVOID THESE

```
TECHNICAL MISTAKES:
✗ Saying "SOME-IP" (always say "SOME slash IP" or "SOME/IP")
✗ Confusing DoIP port (13400) with SOME/IP port (30490)
✗ Saying 100BASE-T1 = 1Gbps (it's 100Mbps — 1000BASE-T1 is 1Gbps)
✗ Confusing NRC codes: 0x31=out of range, 0x22=conditions not correct
✗ Saying AUTOSAR RTE is hand-coded (it's generated by tools)
✗ Confusing P-Port (provide/output) with R-Port (require/input)
✗ Saying CAN FD max payload is 8 bytes (it's 64 bytes)
✗ Confusing 802.1AS (gPTP) with 802.1Qbv (TAS)

COMMUNICATION MISTAKES:
✗ Using "we" without specifying your personal contribution
✗ Not having specific numbers in STAR answers
✗ Saying "I would do X" instead of "I did X" (give real examples)
✗ Not asking any questions (always prepare 3 questions)
✗ Saying "I don't know" without offering to walk through your reasoning
✗ Over-explaining when a short answer is needed
✗ Under-explaining when a deep technical answer is expected

WHEN YOU DON'T KNOW THE ANSWER:
✓ "I haven't worked with that specific standard, but from what I know
   about [related topic], I would approach it by..."
✓ "That specific version I haven't used, but I'm familiar with the
   concepts — the key difference would be..."
✓ "That's a good question. Let me think through it..."
   (pause, think, then answer — don't blurt immediately)
```

---

## FINAL CHECKLIST BEFORE INTERVIEW

```
THE NIGHT BEFORE:
□ Review all 7 cheat sheets (45 minutes)
□ Re-read your 5 best STAR stories
□ Check the company's recent news / product launches
□ Prepare 3 smart questions for the interviewer
□ Set 2 alarms (interview + 1 hour earlier)
□ Charge all devices (laptop, phone, headphones)
□ Test video/audio if remote interview
□ Sleep at least 7.5 hours

ON THE DAY:
□ Wake up with buffer time (no rushing)
□ Eat a proper meal
□ Arrive/log in 10 minutes early
□ Have notepad + pen ready
□ Have GitHub open in browser tab
□ Take one deep breath before joining

DURING INTERVIEW:
□ Speak slowly — nervous people rush
□ When asked a technical question: state your understanding first
□ Use the whiteboard / draw diagrams when possible
□ Say "Great question" only once (avoid sounding sycophantic)
□ Ask clarifying questions if the question is ambiguous

AFTER INTERVIEW:
□ Send a thank-you email within 24 hours
□ Note down all questions asked (for preparation improvement)
□ If rejected: ask for feedback (3/10 companies will give it — valuable)
```

---

## CONGRATULATIONS — COURSE COMPLETE

```
┌──────────────────────────────────────────────────────────────────┐
│  COURSE COMPLETION SUMMARY                                       │
│                                                                  │
│  Sections completed: 16/16                                       │
│  Topics covered:                                                 │
│    ✅ Automotive industry & career roadmap                       │
│    ✅ Embedded systems & C/C++                                   │
│    ✅ CAN, CAN FD, LIN, FlexRay                                  │
│    ✅ Automotive Ethernet (100BASE-T1/1000BASE-T1)               │
│    ✅ SOME/IP, DoIP, TSN, VLAN, gPTP                             │
│    ✅ AUTOSAR Classic + Adaptive                                  │
│    ✅ ECU validation test methodology                             │
│    ✅ CANoe + CAPL scripting                                     │
│    ✅ UDS diagnostics + OBD-II                                   │
│    ✅ HIL testing (dSPACE + CarMaker)                            │
│    ✅ ISO 26262 + ASPICE basics                                   │
│    ✅ 300+ interview Q&As                                        │
│    ✅ 50 STAR interview answers                                   │
│    ✅ 20 industry-level mini projects                            │
│    ✅ 90-day learning roadmap                                     │
│    ✅ Resume + LinkedIn optimization                              │
│                                                                  │
│  YOU ARE NOW INTERVIEW-READY.                                    │
│  Apply with confidence.                                          │
└──────────────────────────────────────────────────────────────────┘

Target companies: Bosch, Continental, KPIT, Tata Elxsi, Harman,
                  Aptiv, ZF, Magna, Visteon, Mercedes-Benz R&D
                  
Good luck!
```

---

*← Back to [Course Overview](00_Course_Overview.md)*
