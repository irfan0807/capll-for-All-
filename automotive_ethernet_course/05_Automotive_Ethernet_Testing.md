# SECTION 5 — AUTOMOTIVE ETHERNET TESTING
## Course: Automotive Ethernet Testing — Complete Industry Training

---

## 5.1 ETHERNET PHY AND MAC LAYER TESTING

### PHY Layer Validation Test Cases

```
TEST SUITE: 100BASE-T1 PHY Validation

TC-PHY-001: Link Establishment
  Precondition: Two ECUs connected via STP cable
  Action: Power on both ECUs
  Expected: Link status = UP within 300ms
  Pass Criteria: EthTrcv_GetLinkState() = ETHTRCV_LINK_STATE_ACTIVE
  Tools: Oscilloscope, CANoe EthernetProbe

TC-PHY-002: Signal Quality — Eye Diagram
  Action: Transmit 1000BASE-T1 test patterns
  Expected: Eye height > 60mV, jitter < 1.4ns
  Tools: Keysight DCA oscilloscope, 802.3bp conformance suite

TC-PHY-003: EMC Stress Test
  Action: Apply RF interference (100MHz, 3V/m)
  Expected: Link maintains, <0.1% frame error rate
  Tools: EMC test chamber, signal generator, Wireshark

TC-PHY-004: Cable Fault Detection
  Action: Disconnect one wire of the STP pair
  Expected: PHY reports OPEN fault within 500ms
            EthTrcv diagnostic: ETHTRCV_PHYTESTRESULT_OPEN
  Tools: CANoe Ethernet diagnostic window

TC-PHY-005: Wake-Up Pulse (WUP) Test
  Action: Send WUP from master to sleeping ECU
  Expected: ECU wakes up within 20ms, link established
  Tools: Power analyzer, CANoe timing trace

TC-PHY-006: Temperature Range
  Action: Validate PHY at -40°C and +125°C
  Expected: Link UP, frame error rate < 0.01%
  Tools: Temperature chamber, frame error counter
```

### MAC Layer Test Cases

```
TC-MAC-001: Broadcast Frame Reception
  Action: Send Ethernet frame with DA = FF:FF:FF:FF:FF:FF
  Expected: All ECUs on segment receive the frame
  
TC-MAC-002: Unicast Frame Routing
  Action: Send frame with specific ECU MAC as DA
  Expected: Only target ECU receives frame (switch validates)

TC-MAC-003: CRC Error Handling
  Action: Inject frame with corrupted FCS (Wireshark corrupt frame option)
  Expected: MAC discards frame silently, Eth_RxErrorCount increments

TC-MAC-004: Jumbo Frame Rejection
  Action: Send frame with payload > 1518 bytes
  Expected: Frame rejected, no buffer overflow

TC-MAC-005: Frame Rate Measurement
  Action: Send 1000 frames at 100Mbps line rate
  Expected: No frame loss, all delivered in order
  Tools: IXIA/Spirent traffic generator
```

---

## 5.2 ETHERNET SWITCH ARCHITECTURE TESTING

### Automotive Ethernet Switch Internals

```
ETHERNET SWITCH ARCHITECTURE:
┌────────────────────────────────────────────────────────────────────┐
│                 AUTOMOTIVE ETHERNET SWITCH (NXP SJA1110)           │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Port 0 ──[100BASE-T1 PHY]──► │              │◄──── MAC Table     │
│  Port 1 ──[100BASE-T1 PHY]──► │  Switching   │     (CAM/TCAM)     │
│  Port 2 ──[1000BASE-T1 PHY]──►│  Fabric      │◄──── VLAN Table    │
│  Port 3 ──[1000BASE-T1 PHY]──►│              │◄──── QoS/TAS Config│
│  Port 4 ──[SGMII to Host MCU]►│              │                    │
│                                │              │                    │
│  ┌─────────────────────────────────────────┐ │                    │
│  │  Management Port (SPI/MDIO to host MCU) │◄─────────────────────│
│  │  • VLAN config, MAC table read/write    │                      │
│  │  • Port mirroring for debug             │                      │
│  │  • TAS schedule programming             │                      │
│  └─────────────────────────────────────────┘                      │
└────────────────────────────────────────────────────────────────────┘
```

### TCAM — Ternary Content Addressable Memory

```
TCAM CONCEPTS:
TCAM enables matching packets against rules simultaneously (parallel lookup).
Each entry has: VALUE + MASK bits (ternary: 0, 1, or "don't care" X)

AUTOMOTIVE FIREWALL RULE EXAMPLE (TCAM entries):
┌────────────────────────────────────────────────────────────────────────┐
│ Priority │ Src IP       │ Dst IP       │ Protocol │ Dst Port │ Action  │
├────────────────────────────────────────────────────────────────────────┤
│    1     │ 192.168.1.100│ 239.255.0.1  │ UDP      │ 30490    │ ALLOW   │
│          │ (RADAR ECU)  │ (SOME/IP mc) │          │(SOME/IP) │ (event) │
├────────────────────────────────────────────────────────────────────────┤
│    2     │ X.X.X.X      │ 192.168.1.5  │ TCP      │ 13400    │ ALLOW   │
│          │ (Any tester) │ (DoIP GW)    │          │ (DoIP)   │(diag)   │
├────────────────────────────────────────────────────────────────────────┤
│    3     │ 192.168.2.X  │ 192.168.1.X  │ ANY      │ ANY      │ BLOCK   │
│          │ (IVI domain) │ (ADAS domain)│          │          │         │
├────────────────────────────────────────────────────────────────────────┤
│  DEFAULT │ X.X.X.X      │ X.X.X.X      │ ANY      │ ANY      │ DROP    │
└────────────────────────────────────────────────────────────────────────┘
X = "don't care" — matches any value in that position
```

### Switch Testing — Port Mirroring for Debug

```
PORT MIRROR CONFIGURATION:
• Configure Port 0 (ADAS ECU port) as source
• Configure Port 4 (Analysis port) as mirror destination
• Connect Wireshark PC to Port 4

All frames on Port 0 (Tx + Rx) are copied to Port 4
Wireshark on analysis port captures all ADAS ECU traffic
without interrupting real communication

CANoe Configuration:
• EthernetProbe → connect to mirror port
• All frames captured in Ethernet trace window
```

---

## 5.3 TSN VALIDATION TESTING

### TSN Test Cases — gPTP (IEEE 802.1AS)

```
TC-TSN-001: Time Synchronization Accuracy
  Setup: Grand Master (GM) = ADAS ECU, Slave = RADAR ECU
  Action: Start gPTP sync, measure offset after 1000 sync cycles
  Expected: Offset < 1µs (automotive requirement)
  Tools: CANoe TSN plugin, PTP analyzer

TC-TSN-002: Grand Master Failover
  Setup: Primary GM active, secondary GM configured
  Action: Disconnect primary GM
  Expected: Secondary GM takes over within 6s (per 802.1AS spec)
            Time continuity maintained during switchover
  Tools: CANoe, power relay for disconnect simulation

TC-TSN-003: TAS Schedule Compliance (IEEE 802.1Qbv)
  Setup: ADAS events in Class 7 (100µs gate), video in Class 5
  Action: Generate maximum load on all traffic classes simultaneously
  Expected: Class 7 ADAS frames NOT delayed by Class 5 video
            ADAS latency < 500µs even under 100% load
  Tools: CANoe TAS test plugin, Spirent traffic generator

TC-TSN-004: Credit-Based Shaper (AVB, IEEE 802.1Qav)
  Setup: Audio stream + background traffic
  Action: Generate 110% bandwidth utilization
  Expected: Audio stream maintains reserved 50Mbps bandwidth
            Jitter < 125µs (802.1Qav requirement)
  Tools: IXIA traffic generator, Wireshark timing analysis
```

---

## 5.4 SOME/IP TESTING

### SOME/IP Test Framework — CANoe Setup

```
SOME/IP TEST SETUP IN CANoe:
┌──────────────────────────────────────────────────────────┐
│  CANoe PC                                                │
│  ├── Ethernet channel connected to vehicle network       │
│  ├── CANoe SOME/IP simulation node (acts as client)      │
│  ├── vTESTstudio test cases for SOME/IP validation       │
│  └── Wireshark capture on the same interface             │
└──────────────────────────────────────────────────────────┘
         │ 100BASE-T1 / 1000BASE-T1
         ▼
┌──────────────────────────────────────────────────────────┐
│  DUT (RADAR ECU / ADAS ECU)                             │
│  ├── SOME/IP server: RADAR_SERVICE (0x0001)              │
│  ├── Event: RadarObject (0x8001), period 20ms           │
│  └── Method: GetSystemStatus (0x0010)                   │
└──────────────────────────────────────────────────────────┘
```

### SOME/IP Validation Test Cases

```
TC-SOMEIP-001: Service Discovery — OfferService
  Action: DUT powers on, subscribe to SD multicast
  Expected: OfferService received within 1s of DUT startup
  CAPL validation:
    on ethernetPacket {
        if(SomeIp_GetMessageType(this) == 0xFF /* NOTIFICATION */) {
            if(SomeIp_GetServiceId(this) == 0x0001) {
                testStepPass("OfferService received");
            }
        }
    }

TC-SOMEIP-002: Method Call — Request/Response
  Action: Send GetSystemStatus request
  Expected: Response within 100ms with Return Code 0x00 (E_OK)
  
TC-SOMEIP-003: Event Rate Validation
  Action: Subscribe to RadarObject events
  Expected: Events arrive at 20ms ± 2ms
  Measure: Inter-event timestamp delta in Wireshark

TC-SOMEIP-004: Negative Test — Invalid Service ID
  Action: Send request with Service ID = 0xFFFF (not registered)
  Expected: No response (server ignores unknown service IDs)

TC-SOMEIP-005: Subscription Renewal After Server Restart
  Action: Restart DUT (ECU reset)
  Expected: SD re-offers service, client re-subscribes within 3s
            Event stream resumes automatically

TC-SOMEIP-006: Maximum Payload Test
  Action: Configure SOME/IP event with 1400-byte payload (near MTU)
  Expected: No IP fragmentation on 100BASE-T1 (MTU=1500)
  Verify: Single Ethernet frame per SOME/IP event

TC-SOMEIP-007: Concurrent Clients Test
  Action: 3 clients simultaneously subscribe to same event
  Expected: Server sends event to all 3 subscribers
            No degradation in event period

TC-SOMEIP-008: Error Handling — Return Code Validation
  Action: Send request with malformed serialized data
  Expected: Response with Return Code = 0x22 (MALFORMED_MESSAGE)
```

---

## 5.5 DoIP TESTING

### DoIP Validation Test Cases

```
TC-DOIP-001: Vehicle Identification
  Action: Send UDP VehicleIdentityRequest broadcast
  Expected: DoIP GW responds with VIN + EID (Entity ID) + GID
  
TC-DOIP-002: Routing Activation
  Action: TCP connect to GW port 13400, send RoutingActivationRequest
  Expected: RoutingActivationResponse Code = 0x10 (Success)
  
TC-DOIP-003: UDS Session Control via DoIP
  Action: After routing activation, send DiagMsg [10 02] to ADAS ECU
  Expected: DiagMsg Ack, then ADAS ECU sends [50 02] response
  Timing: <500ms

TC-DOIP-004: ECU Flashing via DoIP (Complete Sequence)
  Action: Execute full UDS flash sequence (0x10→0x27→0x34→0x36→0x37→0x11)
  Expected: ECU reflects with new software version, boots successfully
  Duration: < 3 minutes for 8MB firmware

TC-DOIP-005: Routing Activation Timeout
  Action: Establish TCP connection but don't send RoutingActivation
  Expected: DoIP GW closes TCP connection after T_TCP_Initial = 2s

TC-DOIP-006: Invalid Logical Address
  Action: Send DiagMsg to non-existent logical address 0xFFFF
  Expected: DiagMsg Ack with Response Code = 0x06 (Unknown Target)

TC-DOIP-007: Concurrent DoIP Connections
  Action: Establish 3 simultaneous TCP connections to DoIP GW
  Expected: First activates successfully, others get 0x04 (SA in use)
```

---

## 5.6 FIREWALL AND SECURITY TESTING

### Automotive Ethernet Firewall Test Cases

```
TC-FW-001: ADAS Domain Isolation
  Precondition: Firewall rule: IVI (VLAN 20) → ADAS (VLAN 10) BLOCKED
  Action: Send any IP packet from IVI port to ADAS ECU IP
  Expected: Frame dropped by switch firewall, count increments
  Verification: Wireshark on ADAS port shows 0 frames from IVI

TC-FW-002: Diagnostic Access Allowed
  Precondition: Firewall rule: OBD port (VLAN 40) → DoIP GW TCP 13400 ALLOW
  Action: Connect tester on VLAN 40, send DoIP request to GW
  Expected: Connection succeeds, UDS response received

TC-FW-003: Malformed Frame Rejection
  Action: Send Ethernet frame with invalid EtherType (0x0000)
  Expected: Frame filtered by switch ingress filter

TC-FW-004: Broadcast Storm Prevention
  Action: Inject 10,000 broadcast frames/second from IVI port
  Expected: Broadcast storm control limits to 1000/s per port
            ADAS domain unaffected (VLAN isolation)

TC-FW-005: Rate Limiting Test
  Action: Send UDP to SOME/IP port at 2× allowed rate from unauthorized source
  Expected: Excess frames dropped, rate limited to configured threshold

TC-FW-006: TCAM Rule Priority Validation
  Action: Send packet matching both rule #1 (ALLOW) and rule #3 (BLOCK)
  Expected: Higher priority (lower index) rule #1 wins → ALLOW
```

### Secure Boot Validation

```
SECURE BOOT TEST SEQUENCE:

TC-SB-001: Valid Firmware Boot
  Action: Flash ECU with authentic signed firmware
  Expected: ECU boots successfully, application runs
  
TC-SB-002: Unsigned Firmware Rejection
  Action: Flash ECU with firmware without valid signature
  Expected: ECU does NOT boot application
             Bootloader enters fallback/error state
             DTC set: BOOT_SIGNATURE_INVALID

TC-SB-003: Corrupted Firmware Rejection
  Action: Flash valid firmware, then corrupt 1 byte at offset 0x1000
  Expected: CRC check fails in bootloader
             ECU does not start corrupted application

TC-SB-004: Rollback Protection
  Action: Flash firmware with version number LOWER than current
  Expected: Anti-rollback check fails, update rejected
            Version counter in DFLASH prevents downgrade

TC-SB-005: Certificate Chain Validation
  Action: Flash firmware signed with expired certificate
  Expected: OEM root CA validates timestamp
             Expired cert rejected

ROOT CHAIN:
OEM Root CA → OEM Intermediate CA → Firmware Signing Cert
                                         ↓
                           Signs firmware.hex (ECDSA-256)
                                         ↓
                           ECU bootloader verifies on boot
```

---

## 5.7 ETHERNET PACKET ANALYSIS — REAL SCENARIOS

### Scenario 1: Diagnosing Packet Loss

```
PROBLEM: ADAS ECU reports 5% RadarObject event loss

INVESTIGATION STEPS:

Step 1: Capture Wireshark on mirror port of switch (RADAR ECU port)
Step 2: Apply display filter: someip && someip.serviceid == 0x0001

Step 3: Export to CSV, analyze inter-packet timing
  Expected: 20ms ± 2ms
  Found: Most 20ms, but periodic 200ms gaps (10× period!)

Step 4: Check TAS schedule:
  Gate schedule was 20ms total period
  ADAS gate: slot 0-2ms
  Background gate: 2-20ms
  
Step 5: Identify: RADAR packets arriving at 19.5ms — just missing gate
  TAS gate closes at 2ms, RADAR packet arrives at 2.1ms → HELD for next cycle
  
Step 6: Root cause: gPTP sync offset between RADAR ECU and switch = 2.3µs
  Accumulated error causes periodic gate miss every 10th cycle

FIX: Reduce gPTP acceptable offset to 500ns
     Add 500µs guard band before TAS gate close
```

### Scenario 2: DoIP Connection Instability

```
PROBLEM: DoIP diagnostic session drops every 2–3 minutes

WIRESHARK ANALYSIS:
Filter: tcp.port == 13400 && tcp.flags.rst == 1

Found: TCP RST sent by DoIP GW exactly 120s after last DiagMsg

Root cause: DoIP T_TCP_General = 120s (general inactivity timeout)
The test tool was NOT sending TesterPresent (0x3E) to keep session alive

FIX 1 (Tool side): Send UDS 0x3E 80 every 60s (suppress positive response)
FIX 2 (ECU side): Increase T_TCP_General from 120s to 300s per project spec

VERIFICATION: After fix, Wireshark shows no RST frames during 10min test
```

### Scenario 3: SOME/IP Serialization Error

```
PROBLEM: ADAS ECU receives RadarObject but distance value is garbage

WIRESHARK CAPTURE of RadarObject event payload:
Raw bytes: 00 00 00 28 00 0A ... (28 hex = 40 decimal)

Expected: distance = 4.0 meters → raw = 40 (×0.1m resolution)
Received in ADAS: distance = 10240 meters (garbage!)

ANALYSIS:
RADAR sends (Motorola byte order, big-endian):
  byte[0]=0x00, byte[1]=0x28 → value = 0x0028 = 40 → 4.0m ✓

ADAS receives and interprets (Intel byte order, little-endian):  
  reads: 0x2800 = 10240 → 1024.0m ✗ (wrong endianness!)

ROOT CAUSE: SOME/IP serialization byte order mismatch
ADAS SWC expecting Intel byte order, RADAR SWC using Motorola

FIX: Update ARXML I-PDU byte order attribute:
     <PACKING-BYTE-ORDER>MOST-SIGNIFICANT-BYTE-FIRST</PACKING-BYTE-ORDER>
     Regenerate SomeIpXf transformer code, re-test
```

---

## 5.8 NETWORK TOPOLOGY VALIDATION

### Full Vehicle Network Validation Checklist

```
ETHERNET NETWORK VALIDATION CHECKLIST:

1. PHYSICAL LAYER
   ☐ All 100BASE-T1/1000BASE-T1 links UP within spec time
   ☐ PHY diagnostic registers: no OPEN/SHORT/SWAP faults
   ☐ Eye diagram within 802.3bw/3bp mask
   ☐ Bit Error Rate (BER) < 10^-9

2. LINK LAYER
   ☐ MAC address uniqueness — no conflicts in ARP table
   ☐ VLAN configuration correct for all ports
   ☐ Switch MAC table populated correctly
   ☐ Port mirroring functional for debug

3. NETWORK LAYER
   ☐ All ECU IP addresses unique, correct subnet
   ☐ DHCP server (or static IP) working
   ☐ ARP resolution working for all ECUs
   ☐ ICMP ping round-trip < 1ms for all ECU pairs

4. TRANSPORT LAYER
   ☐ TCP connections stable for DoIP
   ☐ UDP datagrams delivered within latency spec
   ☐ No spurious TCP RST or FIN

5. APPLICATION LAYER
   ☐ SOME/IP services all OfferService within startup spec
   ☐ All required subscriptions successful
   ☐ DoIP routing activation successful
   ☐ UDS basic services (0x10, 0x22, 0x3E) responsive

6. TIMING (TSN)
   ☐ gPTP sync offset < 1µs
   ☐ TAS gates compliant for all traffic classes
   ☐ ADAS traffic latency < spec (typically < 5ms end-to-end)

7. SECURITY
   ☐ Firewall rules block cross-domain unauthorized traffic
   ☐ Secure boot validates firmware on every power cycle
   ☐ TLS/DTLS active for OTA communication
   ☐ No open diagnostic ports accessible from untrusted ports
```

---

## 5.9 ROOT CAUSE ANALYSIS — METHODOLOGY

### 5-Why Analysis for Ethernet Issues

```
PROBLEM: AEB (Autonomous Emergency Braking) failed to activate in validation

WHY 1: AEB algorithm didn't receive radar object data in time
WHY 2: Radar object SOME/IP event was delayed by 850ms (should be 20ms)
WHY 3: SOME/IP event wasn't sent because SD subscription was lost
WHY 4: SD subscription lost because DoIP GW reset network interfaces
WHY 5: DoIP GW reset Ethernet when it received an invalid DoIP frame
         from a connected tester that sent a malformed packet

ROOT CAUSE: DoIP GW error handling bug — malformed packet caused
            unintended Ethernet interface reset affecting ALL traffic

CORRECTIVE ACTION:
1. Fix DoIP GW: Discard malformed packets without resetting interface
2. Add isolation: Diagnostic port (VLAN 40) reset should NOT affect
                  ADAS VLAN 10 traffic
3. Add test case: TC-DOIP-ISOLATION-001 — verify malformed DoIP
                  packet does not affect SOME/IP event delivery

PREVENTIVE ACTION:
1. Add defensive DoIP frame parser with length/type validation
2. Add VLAN isolation test in HIL regression suite
3. Update FMEA with this failure mode
```

---

## 5.10 INTERVIEW QUESTIONS — SECTION 5

**Q1: How do you validate SOME/IP event delivery rate and latency in CANoe?**

> In CANoe, I use the SOME/IP simulation node as a client and configure it to subscribe to the DUT's event group. I enable Ethernet trace logging to capture all SOME/IP packets with timestamps. I then use a CAPL script to calculate inter-event deltas: `(currentTimestamp - previousTimestamp)` and assert it's within `20ms ± 2ms`. For latency, I use gPTP-synchronized timestamps in both the sender ECU and CANoe to measure end-to-end delay. I also use Wireshark with `frame.time_delta` filter to cross-verify.

**Q2: What is TCAM and how is it used in automotive Ethernet firewalls?**

> TCAM (Ternary Content Addressable Memory) is a specialized memory that allows searching all entries simultaneously against a lookup key. Each TCAM entry has a VALUE, MASK, and ACTION. The mask defines "don't care" bits (X). In automotive Ethernet switches (like NXP SJA1110), TCAM implements the firewall rule table. When a packet arrives, its 5-tuple (source IP, dest IP, protocol, source port, dest port) is matched against all TCAM entries in parallel. The highest-priority matching entry's action (ALLOW/BLOCK/REDIRECT) is applied. This enables wire-speed packet filtering.

**Q3: How would you debug a SOME/IP event that is received at random intervals instead of the configured 20ms period?**

> I would: (1) Capture Wireshark on a switch mirror port during the issue. (2) Export SOME/IP packets and compute inter-event timestamps. (3) Look for patterns — are gaps multiples of 20ms? If so, suspect TAS gate miss due to gPTP desync. (4) Check gPTP offset in the switch log — if >500µs, this could cause gate misses. (5) Check if the sending ECU's AUTOSAR OS timer jitter is within spec using TRACE32 profiling. (6) Check for SoAd Tx queue overflow using diagnostic counters. I'd also verify the SOME/IP event is configured as cyclic (not event-triggered) in the ARXML.

**Q4: Explain secure boot and what you validate as an Ethernet testing engineer.**

> Secure boot is a chain-of-trust process where each boot stage verifies the next using cryptographic signatures. The bootloader contains an OEM root public key. On startup, it verifies the application firmware's ECDSA signature before executing. As an Ethernet testing engineer, I validate: (1) Valid firmware boots correctly. (2) Firmware without signature doesn't boot. (3) Firmware signed with wrong key doesn't boot. (4) Anti-rollback prevents flashing older versions. (5) The Ethernet OTA channel only accepts update packages that pass the same signature check. I use DoIP to send test firmware packages and verify ECU response.

**Q5: A vehicle's ADAS ECU shows intermittent communication loss with the camera ECU. Walk through your debugging approach.**

> Step 1: Check PHY layer — MDIO register read for link status, error counters (CRC errors, symbol errors). Step 2: Check EthSM state transitions in ECU logs — when does link drop? Step 3: Capture Wireshark during the event — look for burst of CRC errors or frame drops. Step 4: Physical inspection — cable routing, connector torque, contact resistance. Step 5: Check power supply — voltage drop during high-current events (motor actuation) can cause PHY glitch. Step 6: Temperature correlation — does it happen more at specific temperatures? Step 7: gPTP offset during the event — desync before or after the link loss? This systematic approach typically isolates EMI, connector, or timing issues.

---

*Next Section → [Section 6: Vector Tools & CAPL](06_Vector_Tools_CANoe_CAPL.md)*
