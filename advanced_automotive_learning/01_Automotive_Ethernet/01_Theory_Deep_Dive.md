# AUTOMOTIVE ETHERNET — DEEP DIVE
## Module 1 of 7 | advanced_automotive_learning

---

## 1. WHY AUTOMOTIVE ETHERNET?

Traditional vehicles used CAN (1–8 Mbps), LIN (20 kbps), and FlexRay (10 Mbps). Modern vehicles have:
- 100+ ECUs generating gigabytes of data per second
- 4K cameras, 4D RADAR, 128-beam LiDAR — all needing high bandwidth
- ADAS domain controllers aggregating sensor feeds
- OTA software updates pushing hundreds of MB

**CAN cannot carry this.** Automotive Ethernet solves it.

```
BANDWIDTH COMPARISON:
─────────────────────────────────────────────────────────
Protocol        Max Speed     Payload/Frame    Cable
─────────────────────────────────────────────────────────
LIN             20 kbps       8 bytes          1-wire
CAN Classical   1 Mbps        8 bytes          2-wire
CAN FD          8 Mbps        64 bytes         2-wire
FlexRay         10 Mbps       254 bytes        2-wire
100BASE-T1      100 Mbps      1500 bytes       1 pair
1000BASE-T1     1 Gbps        1500 bytes       1 pair
10GBASE-T1      10 Gbps       1500 bytes       1 pair
─────────────────────────────────────────────────────────
```

---

## 2. PHYSICAL LAYER — HOW IT WORKS

### 2.1 The Core Innovation: Single Twisted Pair

Standard Ethernet (1000BASE-T) uses 4 pairs (8 wires). Automotive Ethernet uses **1 pair** — because every gram and centimeter of cable costs money in a vehicle.

```
STANDARD ETHERNET vs AUTOMOTIVE ETHERNET:

Standard (1000BASE-T):          Automotive (1000BASE-T1):
  Pair 1 →  TX+/TX-               Pair 1 →  TX+ / TX-
  Pair 2 →  RX+/RX-                         (full-duplex simultaneous)
  Pair 3 →  TX+/TX-               ← Echo cancellation extracts
  Pair 4 →  RX+/RX-                 TX from RX on same pair
```

**Echo cancellation** is what makes this work. The PHY chip simultaneously transmits and receives on the same pair, uses digital signal processing to subtract its own transmitted signal, and isolates the received signal.

### 2.2 IEEE Standards

| Standard | IEEE Spec | Speed | Notes |
|----------|-----------|-------|-------|
| 100BASE-T1 | 802.3bw (2015) | 100 Mbps | First automotive Eth — cameras, sensors |
| 1000BASE-T1 | 802.3bp (2016) | 1 Gbps | Domain controllers, backbone |
| 10GBASE-T1 | 802.3ch (2020) | 10 Gbps | Central compute, AI accelerators |
| MultiGBASE-T1 | 802.3ch | 2.5/5 Gbps | Intermediate steps |

### 2.3 Master / Slave Configuration

Unlike standard Ethernet (auto-negotiation), automotive Ethernet requires **manual master/slave assignment**. This is configured in software (register write to PHY).

```
ECU_A (PHY = MASTER)                 ECU_B (PHY = SLAVE)
       │                                     │
       │  100BASE-T1 link (1 twisted pair)   │
       └─────────────────────────────────────┘

Master: provides clock, initiates link training
Slave: recovers clock from Master, adapts to it

If both are Master or both are Slave → NO LINK!
This is a very common validation bug.
```

### 2.4 NXP TJA1100 — The Industry Standard PHY

```
TJA1100 BLOCK DIAGRAM:
┌────────────────────────────────────────┐
│            NXP TJA1100                 │
│                                        │
│  ┌──────────┐    ┌──────────────────┐  │
│  │ MDC/MDIO │    │ PCS (100BASE-T1) │  │
│  │ (config) │    │ PAM3 encoding    │  │
│  └──────────┘    └──────────────────┘  │
│                                        │
│  ┌──────────┐    ┌──────────────────┐  │
│  │ MII/RMII │    │ Echo Canceller   │  │
│  │ (to MAC) │    │ (DSP)            │  │
│  └──────────┘    └──────────────────┘  │
│                                        │
│  WAKE/INH pins: Wakeup, inhibit supply │
└────────────────────────────────────────┘

Configuration via MDIO (Management Data I/O):
  22.0 (Basic Control): bit 11 = Power Down
  22.0: bit 0 = Master (1) / Slave (0)
  1F.0: Extended registers for link training, loopback
```

**Register programming example (C):**
```c
/* Set TJA1100 as Master via MDIO */
#define PHY_ADDR    0x01u
#define REG_CTRL    0x00u  /* Basic Control Register */
#define REG_EXTCTRL 0x17u  /* Extended Control Register */

/* Read-modify-write: set master mode bit */
uint16_t val = mdio_read(PHY_ADDR, REG_EXTCTRL);
val |= (1u << 14);  /* Bit 14 = Master/Slave select */
mdio_write(PHY_ADDR, REG_EXTCTRL, val);

/* Enable 100BASE-T1 link */
val = mdio_read(PHY_ADDR, REG_CTRL);
val &= ~(1u << 11);  /* Clear power-down */
mdio_write(PHY_ADDR, REG_CTRL, val);
```

---

## 3. DATA LINK LAYER — ETHERNET FRAME

```
ETHERNET FRAME WITH VLAN TAG:

 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
├─────────────────────────────────────────────────────────────────┤
│                    Destination MAC (6 bytes)                    │
├─────────────────────────────────────────────────────────────────┤
│                     Source MAC (6 bytes)                        │
├─────────────────────────────────────────────────────────────────┤
│      TPID = 0x8100          │       TCI (2 bytes)               │
│      (VLAN tag present)     │  PCP(3b) | DEI(1b) | VID(12b)    │
├─────────────────────────────────────────────────────────────────┤
│       EtherType (2 bytes)   │    Payload (46–1500 bytes)        │
│  0x0800=IPv4, 0x88F7=gPTP  │                                   │
│  0x8100=VLAN, 0x86DD=IPv6  │                                   │
├─────────────────────────────────────────────────────────────────┤
│                       FCS (4 bytes)                             │
└─────────────────────────────────────────────────────────────────┘

VID (VLAN ID) — 12 bits = 4096 possible VLANs (0 and 4095 reserved)
PCP — Priority Code Point (0–7): 7 = highest (safety-critical)
DEI — Drop Eligible Indicator (1 = may drop under congestion)
```

### Automotive VLAN Assignment (Typical)

| VLAN | Domain | PCP | Typical Services |
|------|--------|-----|-----------------|
| 10 | ADAS / Safety | 7 | AEB, FCW, radar, camera |
| 20 | Diagnostics | 5 | DoIP, UDS, OBD-II |
| 30 | Powertrain | 6 | Engine, gearbox ECUs |
| 40 | Infotainment | 3 | HMI, media, connectivity |
| 50 | Body | 2 | Lights, HVAC, access |
| 60 | OTA Update | 1 | Software download |
| 70 | V2X / Telematics | 4 | C-V2X, gNSS |

---

## 4. NETWORK LAYER — IP ADDRESSING IN AUTOMOTIVE

```
AUTOMOTIVE IP ADDRESSING:

Static IP:        Assigned at ARXML config time (AUTOSAR TcpIp)
                  Example: ADAS controller = 192.168.10.10/24
                           Camera ECU      = 192.168.10.20/24
                           Radar ECU       = 192.168.10.30/24

DHCP:             Rare in safety-critical paths (non-deterministic)
                  Used in diagnostics, infotainment, OTA

IPv6 Link-local:  Used in DoIP discovery (fe80::/10 prefix)
Multicast:        224.224.224.245 — SOME/IP-SD service discovery

TYPICAL AUTOMOTIVE TOPOLOGY:
 ┌──────────────────────────────────────────────────────────┐
 │                    CENTRAL GATEWAY                        │
 │              (NXP SJA1110 Ethernet Switch)               │
 │   VLAN 10   VLAN 20   VLAN 30   VLAN 40   VLAN 60       │
 └────┬────────────┬─────────┬────────┬─────────┬──────────┘
      │            │         │        │          │
   ADAS DC    Diagnostics  Powertrain  IVI     OTA Module
 192.168.10.x 192.168.20.x 192.168.30.x ...
```

---

## 5. TSN — TIME-SENSITIVE NETWORKING

TSN transforms best-effort Ethernet into a **deterministic, real-time network**. Critical for ADAS where a 10ms delay in brake command is unacceptable.

### 5.1 gPTP — Generalized Precision Time Protocol (IEEE 802.1AS)

```
gPTP SYNC SEQUENCE:
                                                    
  GRANDMASTER              SLAVE ECU
  (Domain Ctrl)            (Camera ECU)
       │                        │
       │── Sync ──────────────►│  t1: Master TX time
       │── Follow_Up ─────────►│  (corrects for HW delay)
       │◄─ Delay_Req ──────────│  t2: Slave RX time
       │── Delay_Resp ────────►│  t3: Slave TX time
                                   t4: Master RX time
                                   
  Offset = ((t2-t1) - (t4-t3)) / 2
  Propagation delay = ((t2-t1) + (t4-t3)) / 2
  
  Target accuracy: < 1 microsecond
  (NTP = ~10ms, PTP regular = ~1ms, gPTP = <1µs)
```

### 5.2 TAS — Time-Aware Shaper (IEEE 802.1Qbv)

Divides time into repeating **Gate Control Lists (GCL)**. In each slot, specific queues are open (gate=1) or closed (gate=0).

```
TAS GATE CONTROL LIST EXAMPLE:
 Period = 1ms (1000 µs)

 Time  │ 0µs    200µs   400µs   600µs   800µs   1000µs
───────┼──────────────────────────────────────────────
 Q7(ADAS)│  ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
 Q5(Diag)│  ░░░░░░██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░
 Q3(IVI) │  ░░░░░░░░░░░░██████████████████████░░░░░░
 Q1(OTA) │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██████

ADAS queue (Q7) gets exclusive 200µs window at start of every 1ms
This GUARANTEES camera frame arrives within 200µs — every cycle.
```

### 5.3 Frame Preemption (IEEE 802.1Qbu)

Allows a high-priority frame to **interrupt** a large low-priority frame mid-transmission.

```
WITHOUT PREEMPTION:
  [Large IVI frame — 1500 bytes — takes 12µs @ 1Gbps]────────────►
  [ADAS frame waiting...... delayed up to 12µs!]

WITH FRAME PREEMPTION:
  [IVI frame segment 1]──[ADAS frame (preempts)]──[IVI continues]►
  ADAS maximum delay: 0.5µs (minimum fragment size)
```

### 5.4 802.1CB — Frame Replication and Elimination

For **functional safety** — send the same frame on two paths simultaneously. The receiver accepts the first copy and discards the duplicate.

```
                    ┌── Path A (VLAN trunk 1) ──┐
  Source ECU ──────►│                           ├──► Destination ECU
  (sends 2 copies)  └── Path B (VLAN trunk 2) ──┘   (accepts first, drops second)
  
Use case: AEB brake command must arrive even if one Ethernet link fails.
```

---

## 6. AUTOSAR ETHERNET STACK

```
APPLICATION (SWC):  CameraFusion_SWC, RadarProcessing_SWC
       │ Rte_Write/Rte_Call
       ▼
RTE (Generated)
       │
       ▼
BSW COMMUNICATION STACK:
  SomeIpXf    ← Serialize/deserialize SOME/IP payload
      │
  SomeIpSd    ← Service discovery (OfferService, Subscribe)
      │
  SoAd        ← Socket Adapter (manages UDP/TCP sockets)
      │
  TcpIp       ← TCP/IP/UDP/ICMP stack
      │
  EthIf       ← Ethernet Interface (VLAN tag insertion/stripping)
      │
  Eth (MCAL)  ← Ethernet driver (DMA descriptors, MAC registers)
      │
  EthTrcv (MCAL) ← PHY driver (MDIO, link state, master/slave)
       │
  ══════════════════════════════ Physical ══════════════════
  NXP TJA1100 PHY chip → Twisted pair cable → Remote PHY
```

**Key configuration parameters (ARXML):**
```xml
<!-- EthIf VLAN configuration -->
<VLAN-ID>10</VLAN-ID>
<PRIORITY>7</PRIORITY>  <!-- PCP = 7 for ADAS -->

<!-- TcpIp IP address -->
<IP-ADDRESS>192.168.10.10</IP-ADDRESS>
<IP-ADDRESS-ASSIGNMENT-PRIORITY>1</IP-ADDRESS-PRIORITY>

<!-- SoAd socket connection -->
<REMOTE-PORT>30490</REMOTE-PORT>  <!-- SOME/IP-SD -->
<PROTOCOL>UDP</PROTOCOL>
```

---

## 7. DEBUGGING & TEST CASES

### TC-ETH-001: PHY Link Establishment
```
Test Case: PHY link comes up within 300ms of power-on
Precondition: Both PHYs powered, master/slave configured correctly
Steps:
  1. Power on both ECUs simultaneously
  2. Monitor TJA1100 LINK_STATUS register via MDIO
  3. Start timer at power-on
Expected: LINK_STATUS = 1 within 300ms
Tools: CANoe + VN5640, oscilloscope on MDIO signals
Pass criteria: Link up in < 300ms, 10/10 power cycles
```

### TC-ETH-002: VLAN Segmentation
```
Test Case: VLAN 10 traffic does not reach VLAN 30 port
Precondition: SJA1110 switch configured with VLAN filtering
Steps:
  1. Send SOME/IP notification on VLAN 10 from ADAS ECU
  2. Capture on Powertrain ECU port (VLAN 30)
Expected: Zero VLAN-10 frames appear on VLAN-30 port
Wireshark filter: vlan.id == 10 (should be empty on port capture)
```

### TC-ETH-003: gPTP Synchronization Accuracy
```
Test Case: Time offset < 1µs after 30 seconds of gPTP sync
Steps:
  1. Start gPTP on all ECUs
  2. Wait 30 seconds for convergence
  3. Measure sync offset via PTP timestamps in Follow_Up messages
Wireshark filter: ptp.v2.messageid == 0  (Sync frames)
Pass criteria: |offset| < 1000 ns (1µs) after 30s
```

### TC-ETH-004: Link Loss Recovery
```
Test Case: ECU recovers Ethernet link within 100ms after disconnect
Steps:
  1. Establish link between two ECUs
  2. Physically disconnect cable for 2 seconds
  3. Reconnect cable
  4. Start timer at reconnect
Expected: LINK_STATUS = 1 and IP-layer communication restored within 100ms
ISO 26262: Recovery time must be documented in safety analysis
```

### Common Bugs Found in Practice

```
BUG 1: Master/Slave swap
  Symptom: Link never comes up (no link LED, LINK_STATUS = 0 forever)
  Root cause: Both PHYs configured as MASTER via MDIO register 0x17 bit 14
  Fix: One side set to Master (bit14=1), other set to Slave (bit14=0)
  How it happens: Config file copy-paste error in ARXML/startup script

BUG 2: VLAN ID mismatch
  Symptom: SOME/IP service discovery fails, no subscriptions received
  Root cause: ADAS ECU sending on VLAN 10; Switch port filtering on VLAN 11
  Fix: Align VLAN IDs in SJA1110 switch config and AUTOSAR EthIf config

BUG 3: MTU mismatch
  Symptom: Fragmented IP packets, unreliable SOME/IP large payloads
  Root cause: One ECU MTU = 1500, other = 1400 (jumbo frames disabled)
  Fix: Set consistent MTU across all ECUs and switch

BUG 4: gPTP Master not elected
  Symptom: TSN timestamps inaccurate (>10ms offset)
  Root cause: Two ECUs both configured as gPTP grandmaster candidates
            with equal priority — no election winner
  Fix: Set one ECU clock priority1 = 128, other = 255
```

---

## 8. INTERVIEW Q&A

**Q1: What is the difference between 100BASE-T1 and 1000BASE-T1?**
> 100BASE-T1 (IEEE 802.3bw) = 100 Mbps on 1 twisted pair, uses PAM3 encoding. Used for sensors, body ECUs. 1000BASE-T1 (IEEE 802.3bp) = 1 Gbps on 1 twisted pair, uses PAM3 at higher symbol rate. Used for domain controllers, camera streams, ADAS backbone.

**Q2: Why does automotive Ethernet use only 1 twisted pair instead of 4?**
> Weight and cost. A modern vehicle has 2–3 km of wiring harness. Using 1 pair vs 4 pairs saves 75% of cable weight in Ethernet links. 100BASE-T1 achieves this using echo cancellation DSP — the PHY transmits and receives simultaneously on the same pair, digitally subtracting its own TX signal to isolate the received signal.

**Q3: What is TSN and why is it needed for ADAS?**
> TSN (Time-Sensitive Networking) is a set of IEEE 802.1 standards that add determinism to Ethernet. Standard Ethernet is best-effort — a packet can be delayed 0 to 100+ ms depending on congestion. ADAS requires deterministic latency: a camera frame must arrive within a fixed window so the AEB algorithm can process it in time. TSN standards like 802.1Qbv (TAS) and 802.1AS (gPTP) provide guaranteed timing and synchronized clocks across all ECUs.

**Q4: What happens if the master/slave configuration is wrong in 100BASE-T1?**
> The link will never establish. Both PHYs will endlessly transmit link training sequences waiting for the other side to respond. The TJA1100's LINK_STATUS register stays 0. The AUTOSAR EthIf will report a link-down event to EcuM, which may trigger a DEM error. Fix: ensure exactly one side is Master (MDIO register bit set) and one is Slave.

**Q5: Walk me through what happens when a camera ECU sends a SOME/IP notification.**
> SWC writes data to R-Port → RTE calls SomeIpXf to serialize → SomeIpSd adds SD header if needed → SoAd packages into UDP datagram → TcpIp adds IP header (src=192.168.10.20, dst=224.224.224.245) → EthIf inserts VLAN tag (VLAN 10, PCP 7) → Eth DMA sends frame → TJA1100 PHY transmits on twisted pair → Destination PHY receives → Path reverses through AUTOSAR stack → Destination SWC's R-Port receives data.

---

*Next: [02_STAR_Answers.md](02_STAR_Answers.md)*
