# SECTION 3 — AUTOMOTIVE COMMUNICATION PROTOCOLS
## Course: Automotive Ethernet Testing — Complete Industry Training

---

## 3.1 CAN — CONTROLLER AREA NETWORK

### CAN Overview

CAN (ISO 11898) was developed by Bosch in 1986. It is a multi-master serial bus with CSMA/CD+AMP (Carrier Sense Multiple Access with Collision Detection and Arbitration on Message Priority).

### CAN Frame Structure

```
CAN DATA FRAME (Standard 2.0A — 11-bit ID):
┌────┬────┬──────────────┬─────┬────┬───────────────────────┬─────┬──────┐
│ SOF│ ID │     ID       │ RTR │ IDE│         DLC            │DATA │ CRC  │
│ 1  │[10:3]│  [2:0]    │  1  │  1 │  4 bits (0–8 bytes)   │0-8B │ 15+1 │
└────┴────┴──────────────┴─────┴────┴───────────────────────┴─────┴──────┘
 SOF = Start of Frame (dominant bit)
 ID  = Message Priority (lower ID = higher priority)
 RTR = Remote Transmission Request
 IDE = Identifier Extension (0 = Standard, 1 = Extended)
 DLC = Data Length Code
 CRC = Cyclic Redundancy Check
 ACK = Acknowledge
 EOF = End of Frame

CAN Extended Frame (2.0B — 29-bit ID):
┌────┬───────────────────────────────┬─────┬─────────────────┬────┬──────┐
│SOF │     29-bit Message ID         │ SRR │     DLC         │DATA│CRC/ACK│
└────┴───────────────────────────────┴─────┴─────────────────┴────┴──────┘
```

### CAN Arbitration — Non-Destructive

```
ARBITRATION EXAMPLE:
ECU A wants to send ID = 0x100 = 0001 0000 0000
ECU B wants to send ID = 0x080 = 0000 1000 0000

Bit-by-bit transmission (MSB first):
Bit 10: ECU_A=0, ECU_B=0 → Bus=0 (both match, continue)
Bit  9: ECU_A=0, ECU_B=0 → Bus=0 (continue)
Bit  8: ECU_A=0, ECU_B=0 → Bus=0 (continue)
Bit  7: ECU_A=1, ECU_B=1 → Bus=1 (continue)
Wait... ID 0x100 = 1 0000 0000, ID 0x080 = 0 1000 0000

Bit 10: ECU_A=0, ECU_B=0 → Bus=0
Bit  9: ECU_A=0, ECU_B=0 → Bus=0
Bit  8: ECU_A=1, ECU_B=0 → Bus=1 (ECU_B sees dominant from ECU_A)
                                   ECU_B loses arbitration → STOPS TX
                                   ECU_A wins, continues transmitting

RESULT: Lower ID wins. ID 0x080 (ECU_B) is lower → ECU_B wins!
Correction: ID 0x080 < 0x100, so ECU_B with 0x080 wins arbitration.
```

### CAN Physical Layer

```
CAN BUS TOPOLOGY:
                    ECU 1           ECU 2           ECU 3
                      │               │               │
120Ω ──┬─────────────┴───────────────┴───────────────┴──────── 120Ω
    CANH│ ─────────────────────────────────────────────────── CANH
    CANL│ ─────────────────────────────────────────────────── CANL
       ─┴─
      GND

Electrical Levels:
• Dominant bit (0): CANH = 3.5V, CANL = 1.5V → Differential = 2.0V
• Recessive bit (1): CANH = 2.5V, CANL = 2.5V → Differential = 0.0V
• Termination resistors (120Ω at each end) prevent signal reflections
```

### CAN Timing (Bit Timing)

```
ONE CAN BIT:
┌───────────────────────────────────────────┐
│ Sync_Seg │ Prop_Seg │ Phase_Seg1 │ Phase_Seg2 │
│  1 TQ    │  1-8 TQ  │  1-8 TQ    │  1-8 TQ   │
└───────────────────────────────────────────┘
                        ▲
                   Sample Point (typically 75-80% of bit time)
                   
Example: 500 kbps CAN at 80 MHz MCU
• TQ = 1/(80MHz / prescaler) = 62.5ns (with prescaler=5)
• Bit time = 500 kbps → 2000ns
• Total TQ per bit = 2000ns / 62.5ns = 32 TQ
• Sync=1, Prop=7, PhSeg1=12, PhSeg2=12 → Sample at 62.5%
```

---

## 3.2 CAN FD — FLEXIBLE DATA RATE

### CAN FD vs Classic CAN

| Feature | CAN (2.0) | CAN FD |
|---------|-----------|--------|
| Standard | ISO 11898-1 | ISO 11898-1:2015 |
| Max Payload | 8 bytes | **64 bytes** |
| Arbitration Speed | Up to 1 Mbps | Up to 1 Mbps |
| Data Phase Speed | Up to 1 Mbps | **Up to 8 Mbps** |
| Frame Format | Fixed | Two speeds per frame |
| CRC | 15-bit | 17/21-bit |
| Automotive Use | Legacy ECUs | Gateway, ADAS, new ECUs |

### CAN FD Frame Structure

```
CAN FD DATA FRAME:
┌────┬────────────┬─────┬────┬────┬────┬──────────────────┬─────┬──────┐
│SOF │   Arbitration Phase (slow — up to 1Mbps)           │BRS  │ ESI  │
│    │  11-bit ID │ RRS │ IDE│ FDF│ res│ DLC (0-15→0-64B) │     │      │
└────┴────────────┴─────┴────┴────┴────┴──────────────────┴─────┴──────┘
                                        ▼
                              ┌─────────────────────────┐
                              │  Data Phase (fast—8Mbps)│
                              │  Payload: up to 64 bytes│
                              │  CRC: 17 or 21-bit      │
                              └─────────────────────────┘

BRS = Bit Rate Switch (enables data phase speed change)
FDF = FD Format bit (distinguishes CAN FD from classic CAN)
ESI = Error State Indicator
```

### CAN FD DLC Encoding

```
DLC Code │ 0  1  2  3  4  5  6  7  8  9  10  11  12  13  14  15
Bytes    │ 0  1  2  3  4  5  6  7  8  12  16  20  24  32  48  64
```

---

## 3.3 LIN — LOCAL INTERCONNECT NETWORK

### LIN Overview

LIN is a single-wire, master-slave serial protocol for low-speed body functions (windows, mirrors, seat adjustment, HVAC). Governed by LIN Consortium specification.

### LIN Frame Structure

```
LIN FRAME:
┌─────────┬──────────────────────────┬──────────────────────┬─────────────┐
│  BREAK  │      SYNC BYTE (0x55)    │  PID (Protected ID)  │ DATA + CRC  │
│ 13 bits │       0101 0101          │  6-bit ID + 2 parity │ 1–8 bytes   │
└─────────┴──────────────────────────┴──────────────────────┴─────────────┘

LIN Network Topology:
                  LIN Master (Body Control Module)
                         │
              ┌──────────┴──────────┐
              │  LIN Bus (12V, 1-wire)  │
     ┌────────┴────┐  ┌─────────────┴──┐  ┌───────────────┐
     │ Seat Motor  │  │  Mirror Motor  │  │  HVAC Blower  │
     │  (Slave)    │  │   (Slave)      │  │   (Slave)     │
     └────────────-┘  └────────────────┘  └───────────────┘
```

| Feature | Value |
|---------|-------|
| Speed | 1–20 kbps |
| Topology | Single master, up to 16 slaves |
| Cable | Single wire (+ GND) |
| Protocol | Request-response (master schedules) |
| Use Case | Window, seat, mirror, HVAC, lighting |

---

## 3.4 FLEXRAY

### FlexRay Overview

FlexRay is a high-speed, deterministic, fault-tolerant protocol used in X-by-wire applications (steer-by-wire, brake-by-wire) and chassis control.

### FlexRay Frame Structure

```
FLEXRAY FRAME:
┌─────────────────────────────────────────────────────────────┐
│  HEADER SEGMENT                                             │
│  ├── Reserved Bit                                           │
│  ├── Payload Preamble Indicator                             │
│  ├── Null Frame Indicator                                   │
│  ├── Sync Frame Indicator                                   │
│  ├── Startup Frame Indicator                                │
│  ├── Frame ID (11-bit, 1–2047)                              │
│  ├── Payload Length (7-bit, in 2-byte words)                │
│  ├── Header CRC (11-bit)                                    │
│  └── Cycle Count (6-bit)                                    │
├─────────────────────────────────────────────────────────────┤
│  PAYLOAD SEGMENT (0–254 bytes)                              │
├─────────────────────────────────────────────────────────────┤
│  TRAILER (CRC 24-bit)                                       │
└─────────────────────────────────────────────────────────────┘
```

### FlexRay Cycle Structure

```
FLEXRAY COMMUNICATION CYCLE (typically 5ms):
┌──────────────────────────────────────────────────────────┐
│  Static Segment        │  Dynamic Segment │  NIT  │ ST   │
│  (TDMA — guaranteed)   │  (FTDMA — best   │       │ sym  │
│  Pre-scheduled slots   │  effort slots)   │       │      │
└──────────────────────────────────────────────────────────┘

Static: Each ECU gets fixed time slot → deterministic
Dynamic: ECUs compete for slots in priority order → flexible
```

| Feature | Value |
|---------|-------|
| Speed | 10 Mbps (per channel, dual channel = 20 Mbps) |
| Topology | Bus or star, up to 2 channels |
| Use Case | Steer-by-wire, brake-by-wire, chassis |
| Key Feature | TDMA — deterministic timing |

---

## 3.5 AUTOMOTIVE ETHERNET — DEEP DIVE

### BroadR-Reach / 100BASE-T1 Physical Layer

```
STANDARD ETHERNET vs AUTOMOTIVE ETHERNET:

Standard (100BASE-TX):
├── 2 pairs of twisted wire (TX + RX separate)
├── Connectors: RJ-45
├── Max cable length: 100m
└── Not suitable for automotive (EMI, connector size, weight)

Automotive (100BASE-T1 — IEEE 802.3bw):
├── 1 PAIR of twisted wire (bi-directional, Full Duplex)
├── No RJ-45 — uses HSD/FAKRA/MATEnet connectors
├── Max cable length: 15m (typ.)
├── EMI optimized for vehicle environment
├── Operates at 12V vehicle supply
└── Supports wake-up via WUP (Wake-Up Pulse)

1000BASE-T1 (IEEE 802.3bp — Gigabit Automotive Ethernet):
├── 1 pair of STP (Shielded Twisted Pair)
├── 1 Gbps Full Duplex
├── Max length: 15m
└── Used for camera, LiDAR, domain controller backbone
```

### Automotive Ethernet PHY — NXP TJA1100

```
ETHERNET ECU CONNECTION:
                                   
MCU (S32K3)                      Another ECU
┌──────────────┐   MII/RMII    ┌──────────────┐  100BASE-T1 ┌────────────┐
│ Ethernet MAC │◄─────────────►│  TJA1100 PHY │◄───────────►│ Switch ECU │
│  (in MCU)   │               │  (External)  │  Single Pair│            │
└──────────────┘               └──────────────┘             └────────────┘

TJA1100 Key Features:
├── 100BASE-T1 (BroadR-Reach) compliant
├── MII/RMII/RGMII MAC interface
├── MDI/MDI-X auto-detection
├── Wake-Up Pulse support
├── OPEN/SHORT/SWAP fault detection
└── Diagnostic registers via MDIO/SPI
```

### Ethernet Frame Structure (IEEE 802.3)

```
ETHERNET FRAME (Layer 2):
┌──────────────┬──────────────┬────────┬──────────────────────┬─────────┐
│  Preamble    │  Destination │ Source │    EtherType/Length  │ Payload │
│  7 bytes     │  MAC 6 bytes │ MAC    │    2 bytes           │ 46-1500 │
│  + 1 SFD byte│  (FF:FF:...  │ 6 bytes│    (e.g., 0x0800=IP) │  bytes  │
│              │  = broadcast)│        │    (e.g., 0x8100=VLAN)│         │
└──────────────┴──────────────┴────────┴──────────────────────┴─────────┘
                                                               │
                              + optional 802.1Q VLAN tag (4B) ─┘
                              + FCS (4 bytes CRC) at end

VLAN Tagged Frame (IEEE 802.1Q):
┌───────┬────────┬────────┬──────────────┬──────────────────────┐
│ DA MAC│ SA MAC │  TPID  │  TCI         │ EtherType │ Payload   │
│ 6 B   │ 6 B    │ 0x8100 │ PCP(3) DEI(1)│           │           │
│       │        │ 2 B    │ VID(12 bits) │  2 B      │ 46-1500 B │
│       │        │        │ 4 B total    │           │           │
└───────┴────────┴────────┴──────────────┴──────────────────────┘
PCP = Priority Code Point (0-7, used for QoS)
DEI = Drop Eligible Indicator
VID = VLAN Identifier (1-4094)
```

---

## 3.6 TCP/IP STACK — AUTOMOTIVE

### TCP/IP Layer Model in Automotive Context

```
OSI LAYER    │  TCP/IP LAYER    │  AUTOMOTIVE PROTOCOL
─────────────┼──────────────────┼────────────────────────────────────
7 Application│  Application     │  SOME/IP, DoIP, HTTP (OTA), MQTT
6 Presentation│                 │  TLS/DTLS (Cybersecurity)
5 Session    │                  │  SOME/IP SD (Service Discovery)
4 Transport  │  Transport       │  TCP (reliable), UDP (fast)
3 Network    │  Internet        │  IPv4/IPv6
2 Data Link  │  Link            │  Ethernet IEEE 802.3 (MAC/LLC)
1 Physical   │  Physical        │  100BASE-T1, 1000BASE-T1 (PHY)
─────────────┴──────────────────┴────────────────────────────────────
```

### TCP vs UDP — Automotive Decision Guide

| Feature | TCP | UDP |
|---------|-----|-----|
| Connection | Connection-oriented | Connectionless |
| Reliability | Guaranteed delivery (ACK) | Best-effort |
| Ordering | In-order delivery | No guarantee |
| Overhead | High (headers, ACK) | Low |
| Latency | Higher | Lower |
| Use in Automotive | DoIP, OTA, SOME/IP reliable | SOME/IP sensor data |
| Example | ECU flashing via DoIP | RADAR object data SOME/IP |

### TCP Header

```
TCP HEADER (20 bytes minimum):
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
┌─────────────────────────────────────────────────────────────────┐
│          Source Port          │       Destination Port          │
├─────────────────────────────────────────────────────────────────┤
│                        Sequence Number                          │
├─────────────────────────────────────────────────────────────────┤
│                    Acknowledgment Number                        │
├───────────────────┬─────────────────────────────────────────────┤
│  Data Offset      │  Flags: SYN, ACK, FIN, RST, PSH, URG       │
├───────────────────┴─────────────────────────────────────────────┤
│           Window Size         │           Checksum              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3.7 VLAN — VIRTUAL LAN

### VLAN in Automotive Ethernet Networks

VLANs segment the automotive Ethernet network into logical domains, ensuring ADAS traffic is isolated from IVI traffic, preventing interference.

```
AUTOMOTIVE VLAN SEGMENTATION:
┌──────────────────────────────────────────────────────────────────┐
│              CENTRAL GATEWAY / ETHERNET SWITCH                   │
│                                                                  │
│  Port 1 ─── ADAS ECU       ─── VLAN 10 (Safety Critical)       │
│  Port 2 ─── Camera ECU     ─── VLAN 10 (Safety Critical)       │
│  Port 3 ─── RADAR ECU      ─── VLAN 10 (Safety Critical)       │
│  Port 4 ─── IVI Unit       ─── VLAN 20 (Infotainment)         │
│  Port 5 ─── Telematics ECU ─── VLAN 30 (Connectivity)         │
│  Port 6 ─── OBD Port       ─── VLAN 40 (Diagnostics)          │
│                                                                  │
│  VLAN 10 → VLAN 20 routing: BLOCKED (safety isolation)         │
│  VLAN 40 → All VLANs: READ ONLY (diagnostic monitoring)        │
└──────────────────────────────────────────────────────────────────┘
```

### VLAN Configuration Table (Ethernet Switch)

| Port | ECU | VLAN ID | Priority (PCP) | Tagged/Untagged |
|------|-----|---------|----------------|-----------------|
| 1 | ADAS ECU | 10 | 7 (highest) | Tagged |
| 2 | Camera ECU | 10 | 7 | Tagged |
| 3 | IVI Unit | 20 | 3 | Untagged (access port) |
| 4 | TCU | 30 | 4 | Tagged |
| 5 | Diagnostic | 40 | 0 | Tagged |
| Uplink | Gateway | All | — | Trunk (all VLANs) |

---

## 3.8 TSN — TIME-SENSITIVE NETWORKING

### What Is TSN?

TSN (Time-Sensitive Networking) is a set of IEEE 802.1 standards extending Ethernet with deterministic, bounded-latency transmission. This is critical for safety-critical ADAS data (e.g., camera feed must arrive within 5ms).

### TSN Standards Used in Automotive

| Standard | Purpose | Function |
|---------|---------|---------|
| IEEE 802.1AS | gPTP (Generalized Precision Time Protocol) | Time synchronization across all ECUs |
| IEEE 802.1Qbv | TAS (Time-Aware Shaper) | Scheduled traffic gates |
| IEEE 802.1Qbu + 802.3br | Frame Preemption | High-priority frames interrupt low-priority |
| IEEE 802.1Qav | CBS (Credit-Based Shaper) | AVB audio/video bandwidth reservation |
| IEEE 802.1CB | FRER (Frame Replication/Elimination) | Redundant path reliability |

### gPTP Time Synchronization (IEEE 802.1AS)

```
TIME SYNC FLOW:
                    
GM (Grand Master)        Bridge ECU              Slave ECU
  │                         │                       │
  │ Sync (t1)──────────────►│                       │
  │                         │ Sync (t2)────────────►│
  │                         │                       │
  │                         │◄── Delay_Req (t3)─────│
  │◄── Delay_Req (t4)───────│                       │
  │                         │                       │
  │ Follow_Up (t1 precise)─►│                       │
  │                         │ Follow_Up ────────────►│
  │                         │ Delay_Resp (t4)───────►│
  │                         │                       │
  │                         │            Slave calculates:
  │                         │            Offset = (t2-t1+t3-t4)/2
  │                         │            Delay  = (t2-t1+t4-t3)/2
  │                         │            Slave adjusts local clock
```

### TAS (Time-Aware Shaper) — IEEE 802.1Qbv

```
TAS GATE SCHEDULE (8 traffic classes, 1ms cycle):
Time:    0µs   100µs 200µs 300µs     800µs 900µs 1000µs
         │      │     │     │          │     │      │
Class 7  ████████                                     ████ (ADAS — 100µs window)
Class 6          ██████                                    (AV Audio — 100µs)
Class 3                ████████████████████               (Engine CAN — 500µs)
Class 0                                     ██████         (Best Effort — 200µs)

Each gate opens/closes at precise times to guarantee ADAS data
gets its exclusive time slot with ZERO contention from other traffic.
```

---

## 3.9 SOME/IP — SCALABLE SERVICE-ORIENTED MIDDLEWARE OVER IP

### SOME/IP Architecture

SOME/IP (AUTOSAR-defined) enables service-oriented communication over Ethernet, replacing signal-based CAN communication with a client-server / publisher-subscriber model.

```
SOME/IP COMMUNICATION MODELS:

1. REQUEST-RESPONSE (Method Call):
   Client (Tester)          Server (ADAS ECU)
        │                        │
        │── SOME/IP Request ────►│ Service ID: 0x0001
        │   Method ID: 0x0010    │ Method: GetObjectList()
        │                        │ Process request (20ms)
        │◄── SOME/IP Response ───│ Response: Object array
        │   Return Code: 0x00    │
        
2. EVENT (Publish-Subscribe):
   Publisher (RADAR ECU)    Subscriber (ADAS ECU)
        │                        │
        │── SOME/IP Event ──────►│ Service: 0x0001
        │   Event ID: 0x8001     │ Event: RadarObjectUpdate
        │   Period: 20ms         │ (no response expected)
        │── SOME/IP Event ──────►│
        │   (repeats every 20ms) │

3. FIELD (Getter/Setter + Notification):
   Client (HMI)             Server (ADAS ECU)
        │                        │
        │── Get Request ────────►│ Field: TargetSpeed
        │◄── Get Response ───────│ Value: 120 km/h
        │                        │
        │── Set Request ────────►│ Set TargetSpeed = 100
        │◄── Set Response ───────│ OK
        │◄── Notification ───────│ TargetSpeed changed (notified)
```

### SOME/IP Header Format

```
SOME/IP MESSAGE HEADER (8 bytes):
 0       7 8      15 16     23 24     31
┌─────────────────────────────────────┐
│         Service ID (16-bit)         │   Example: 0x0001 (RADAR Service)
├──────────────────┬──────────────────┤
│  Method ID (16) │ Reserved (16-bit) │   0x0010 (GetObjects method)
├─────────────────────────────────────┤
│           Length (32-bit)           │   Length of remaining message
├──────────────────┬──────────────────┤
│   Client ID (16) │  Session ID (16) │   Client = 0x0001, Session++
├──────────────────┬────────┬─────────┤
│ Protocol Ver (8) │ Ifc Ver │MsgType │   Proto=0x01, Type=0x00=Request
├──────────────────┴────────┴─────────┤
│         Return Code (8-bit)         │   0x00 = E_OK, 0x01 = E_NOT_OK
└─────────────────────────────────────┘
```

### SOME/IP Service Discovery (SD)

```
SOME/IP-SD MESSAGE TYPES:
• OfferService    — Server announces available service
• FindService     — Client searches for service
• SubscribeEventgroup — Client subscribes to events
• SubscribeEventgroupAck — Server confirms subscription
• StopOfferService — Server going offline

SD FLOW:
RADAR ECU (Server)          ADAS ECU (Client)
     │                            │
     │ OfferService ─────────────►│ "RADAR Service 0x0001 is available
     │ (UDP Multicast 224.0.0.1)  │  at my IP:PORT"
     │                            │
     │◄── SubscribeEventgroup ────│ "I want RadarObject events"
     │                            │
     │── SubscribeEventgroupAck──►│ "Subscription confirmed"
     │                            │
     │── SOME/IP Event (20ms) ───►│ RadarObject data begins flowing
     │── SOME/IP Event (20ms) ───►│
```

---

## 3.10 DoIP — DIAGNOSTICS OVER IP

### DoIP Overview (ISO 13400)

DoIP routes UDS (Unified Diagnostic Services) diagnostic messages over Ethernet/IP, enabling:
- High-speed ECU flashing
- Remote diagnostics (workshop → vehicle)
- OTA update validation

```
DoIP NETWORK ARCHITECTURE:
                                     
Tester PC / Workshop Tool           Vehicle Ethernet Network
┌──────────────────┐                ┌──────────────────────────────────┐
│   CANoe /        │                │  DoIP Gateway ECU                │
│   ISTA / ODIS    │                │  ┌────────────────────────────┐  │
│   Diagnostic     │  Ethernet      │  │  Edge Node Activation      │  │
│   Application    │◄──────────────►│  │  Routing Activation        │  │
│                  │  DoIP TCP/UDP  │  │  VIN Announcement          │  │
└──────────────────┘                │  └────────────────────────────┘  │
                                    │           │                      │
                                    │  ┌────────▼────────────────┐    │
                                    │  │  ECU 1 (Engine ECU)     │    │
                                    │  │  Logical Address: 0x0001│    │
                                    │  └─────────────────────────┘    │
                                    │  ┌─────────────────────────┐    │
                                    │  │  ECU 2 (ADAS ECU)       │    │
                                    │  │  Logical Address: 0x0010│    │
                                    │  └─────────────────────────┘    │
                                    └──────────────────────────────────┘
```

### DoIP Connection Sequence

```
TESTER → VEHICLE DoIP CONNECTION:

Step 1: UDP Broadcast — Vehicle Discovery
  Tester ──────── UDP:13400 VehicleIdentityRequest ──────────────► Gateway
  Tester ◄─────── UDP VehicleIdentityResponse (VIN + IP + EID) ─── Gateway

Step 2: TCP Connection
  Tester ──────── TCP SYN → DoIP Gateway Port 13400 ─────────────► Gateway
  Tester ◄─────── TCP SYN-ACK ──────────────────────────────────── Gateway
  Tester ──────── TCP ACK ────────────────────────────────────────► Gateway

Step 3: Routing Activation
  Tester ──────── RoutingActivationRequest (SourceAddr=0xE000) ───► Gateway
  Tester ◄─────── RoutingActivationResponse (0x10=Success) ─────── Gateway

Step 4: UDS Request Routing
  Tester ──────── DoIP DiagnosticMessage (TargetAddr=0x0010) ─────► Gateway
                  [UDS: 0x10 02 = DiagnosticSession Control]       ─► ADAS ECU
  Tester ◄─────── DoIP DiagnosticMessageAck ────────────────────── Gateway
  Tester ◄─────── DoIP DiagnosticMessage (UDS Response: 0x50 02) ─ ADAS ECU
```

---

## 3.11 WIRESHARK — PACKET ANALYSIS FUNDAMENTALS

### Capturing Automotive Ethernet Traffic

```
WIRESHARK SETUP FOR AUTOMOTIVE ETHERNET:

1. Hardware: TAP (Test Access Point) or SPAN port on switch
   Switch Port → Mirror to Analysis Port
   ├── Garland TAP (passive, preferred)
   └── Switch SPAN port (active, may drop frames)

2. Capture filter for SOME/IP:
   udp port 30490 or tcp port 30490

3. Display filter for DoIP:
   tcp.port == 13400

4. Filter for specific VLAN:
   vlan.id == 10

5. Filter for specific ECU (by MAC):
   eth.addr == 00:11:22:33:44:55
```

### Wireshark Dissectors for Automotive Protocols

```
WIRESHARK DISPLAY FILTERS CHEAT SHEET:

# SOME/IP
someip                          → All SOME/IP traffic
someip.serviceid == 0x0001      → Specific service
someip.methodid == 0x8001       → Specific event/method

# DoIP
doip                            → All DoIP traffic
doip.payload_type == 0x8001     → Routing Activation Request
doip.payload_type == 0x8004     → Diagnostic Message

# TCP/IP
tcp.flags.syn == 1 && tcp.flags.ack == 0  → TCP connection start
tcp.analysis.retransmission     → TCP retransmissions (packet loss)
tcp.analysis.out_of_order       → Out-of-order packets

# Timing Analysis
frame.time_delta > 0.1          → Frames with >100ms gap (latency issue)

# gPTP (IEEE 802.1AS)
ptp                             → All PTP/gPTP messages
ptp.v2.messagetype == 0x0      → Sync messages
```

### Wireshark Real Packet Analysis — SOME/IP Event

```
PACKET #12345 — SOME/IP RadarObject Event:
Frame: 234 bytes on wire
Ethernet II:
  Destination: 01:00:5E:00:00:01 (multicast)
  Source: 00:11:22:AA:BB:CC (RADAR ECU)
  Type: IPv4 (0x0800)
Internet Protocol v4:
  Source: 192.168.1.100 (RADAR ECU IP)
  Destination: 239.255.0.1 (SOME/IP Multicast)
  Protocol: UDP
User Datagram Protocol:
  Source Port: 30510
  Destination Port: 30490 (SOME/IP default)
SOME/IP:
  Service ID: 0x0002 (RADAR_SERVICE)
  Method ID: 0x8001 (RADAR_OBJECT_EVENT — bit 15 set = notification)
  Length: 196 bytes
  Client ID: 0x0000 (events have no client)
  Session ID: 0x0047 (incrementing)
  Protocol Version: 0x01
  Interface Version: 0x01
  Message Type: 0x02 (NOTIFICATION)
  Return Code: 0x00 (E_OK)
  Payload: [196 bytes of serialized radar object data]
```

---

## 3.12 INTERVIEW QUESTIONS — SECTION 3

**Q1: Explain CAN arbitration with an example. Who wins?**

> CAN uses bitwise Non-Return-to-Zero (NRZ) encoding. When multiple nodes transmit simultaneously, the bus wired-AND resolves conflicts: a dominant bit (0) always overrides a recessive bit (1). Nodes transmit their ID bit by bit and monitor the bus. When a node transmits recessive (1) but reads dominant (0), it lost arbitration and stops. Lower ID = more dominant bits = higher priority and wins arbitration. Example: ID 0x100 vs 0x080 — ID 0x080 has more dominant bits and wins.

**Q2: What is CAN FD and why was it introduced?**

> CAN FD (ISO 11898-1:2015) extends classic CAN with two key improvements: payload up to 64 bytes (vs 8 bytes) and data phase speed up to 8 Mbps (vs 1 Mbps). The data phase switches speed after arbitration completes. This is needed for ADAS gateway use cases where more data per frame is required without upgrading to Ethernet. The BRS (Bit Rate Switch) bit signals the PHY to change speed.

**Q3: What is SOME/IP Service Discovery and how does a client find a service?**

> SOME/IP-SD uses UDP multicast (224.0.0.1, port 30490) for service announcement. A server ECU periodically sends `OfferService` messages. A client ECU either waits for the offer or sends `FindService`. After finding the service, the client sends `SubscribeEventgroup` for events it wants to receive. The server responds with `SubscribeEventgroupAck`. After this handshake, the server starts sending periodic events (SOME/IP notifications) to the client's unicast IP.

**Q4: What is DoIP and how does it differ from KWP2000/CAN diagnostics?**

> DoIP (ISO 13400) transports UDS messages over Ethernet/IP instead of CAN. Traditional diagnostics used K-Line (KWP2000) at 10 kbps or CAN at 500 kbps, giving very slow flash speeds. DoIP uses TCP/IP over Ethernet at 100 Mbps+, enabling ECU flashing in minutes instead of hours. DoIP requires a Routing Activation step where the gateway assigns a logical address to the tester, then routes UDS frames to the target ECU by its logical address.

**Q5: Explain VLAN and why it's used in automotive Ethernet networks.**

> VLANs (IEEE 802.1Q) partition an Ethernet switch into multiple logical networks using 12-bit VLAN IDs in frame headers. In automotive, VLANs separate traffic domains: ADAS (VLAN 10, safety-critical), IVI (VLAN 20, entertainment), Telematics (VLAN 30, connectivity), Diagnostics (VLAN 40). This prevents a low-priority IVI video stream from flooding the ADAS domain and degrading FCW latency. The switch enforces VLAN membership per port and can be configured to block inter-VLAN routing for security isolation.

**Q6: What is TSN and what problem does it solve for automotive Ethernet?**

> Standard Ethernet is "best-effort" — frames can be delayed or dropped under congestion. TSN (Time-Sensitive Networking) adds determinism. IEEE 802.1AS synchronizes all ECU clocks to nanosecond precision. IEEE 802.1Qbv defines time gates that schedule specific traffic classes in dedicated time windows. This guarantees that a camera frame sent by the Camera ECU arrives at the ADAS ECU within a maximum latency (e.g., ≤ 5ms), which is impossible with standard Ethernet.

---

*Next Section → [Section 4: AUTOSAR Complete Guide](04_AUTOSAR_Complete_Guide.md)*
