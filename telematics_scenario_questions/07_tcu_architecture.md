# TCU Architecture & In-Vehicle Networking — Scenario-Based Questions (Q61–Q70)

> **Domain**: Telematics Control Unit (TCU) hardware/software architecture, in-vehicle Ethernet, CAN/CAN-FD gateway, AUTOSAR, functional safety, power management, and hardware design.

---

## Q61: TCU Hardware Architecture — Core Components and Their Functions

### Scenario
Design the hardware block diagram for a modern automotive TCU that supports 4G LTE, GNSS, V2X (C-V2X), Bluetooth, Wi-Fi, and vehicle bus connectivity. Identify each component and its purpose.

### TCU Hardware Block Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    TCU (Telematics Control Unit)              │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ Application  │  │   LTE/4G/5G  │  │  GNSS (GPS +       │ │
│  │ Processor    │  │   Modem      │  │  GLONASS + Galileo) │ │
│  │ (ARM Cortex- │  │ (Qualcomm    │  │  (u-blox NEO-M9N)  │ │
│  │ A series)    │  │  MDM9205)    │  │                    │ │
│  └──────┬───────┘  └──────┬───────┘  └─────────┬──────────┘ │
│         │PCIe/USB         │RF                   │NMEA/UBX    │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌─────────▼──────────┐ │
│  │ HSM (Secure  │  │  RF Front-end │  │  V2X PC5 Module    │ │
│  │ Hardware Ext)│  │  + Antenna    │  │  (C-V2X: 5.9 GHz)  │ │
│  └──────────────┘  │  Switches     │  └────────────────────┘ │
│                    └──────────────┘                           │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ Wi-Fi + BT   │  │ CAN/CAN-FD   │  │  Vehicle Ethernet  │ │
│  │ Combo chip   │  │ Controller   │  │  (100BASE-T1)      │ │
│  │ (802.11ac    │  │ (2×CAN-FD    │  │  DoIP gateway      │ │
│  │  + BT 5.0)   │  │  channels)   │  │                    │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ eSIM         │  │ PMIC         │  │  Flash (NAND 8 GB) │ │
│  │ (eUICC)      │  │ Power Mgmt IC│  │  + LPDDR4 RAM 2 GB │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### Component Roles

| Component | Key Function |
|-----------|-------------|
| Application Processor (ARM-A) | Runs Linux / AUTOSAR Adaptive; telematics apps; OTA client |
| LTE Modem | 4G/5G cellular connectivity; eCall; OTA data channel |
| GNSS Module | GPS/GLONASS/Galileo positioning; A-GPS |
| HSM | Secure key storage; crypto operations; secure boot root of trust |
| CAN/CAN-FD Controller | In-vehicle bus access; diagnostic messages; V2X signals |
| DoIP Ethernet | High-bandwidth diagnostics; gateway to ECU network |
| eSIM (eUICC) | OEM profile + emergency profile; remote SIM provisioning |
| PMIC | Voltage regulation; sleep/wake management; backup battery control |

### Acceptance Criteria
- TCU boot time: ≤ 5 s from power-on to cellular registration
- Operating temperature range: −40°C to +85°C (automotive grade AEC-Q100)
- EMC compliance: CISPR 25 Class 5 (automotive RF emissions)

---

## Q62: CAN Gateway Routing — TCU as a CAN-to-Ethernet Bridge

### Scenario
The TCU receives a remote diagnostic request (DoIP over cellular). The target ECU is on the powertrain CAN bus. Describe how the TCU routes the UDS request from the cellular interface to the CAN-connected ECU.

### Routing Architecture

```
Backend → [cellular / TLS] → TCU LTE modem → TCP socket → DoIP stack
                                         ↓
                              TCU Application Processor:
                              DoIP server receives request
                              Extracts: Source Address, Target Address, UDS payload
                              Lookup routing table: targetAddress 0x0720 → CAN bus 1, node ID 0x07
                              Translates: DoIP message → ISO 15765-2 (CAN transport protocol)
                                         ↓
                              CAN-FD controller → CAN bus → Target ECU (e.g., Engine ECU)
                                         ↑
                              Response: CAN frame → ISO 15765-2 → DoIP → cellular → backend
```

### Routing Table (Example)

| Logical Address | Physical Path | Protocol |
|----------------|--------------|---------|
| 0x0720 | CAN bus 1, ID 0x720 | ISO 15765-2 (CAN TP) |
| 0x0760 | CAN bus 2, ID 0x760 | ISO 15765-2 (CAN TP) |
| 0x0810 | Ethernet, IP 192.168.1.10 | DoIP direct |
| 0x0E11 | Internal (TCU self) | Local |

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Two concurrent diagnostic sessions routing to different ECUs | DoIP supports multiple TCP connections; each connection independently routed |
| CAN bus overloaded: diagnostic frames delayed | ISO 15765-2 P_Br maximum timing applies; flow control manages CAN bus load |
| Target ECU not responding: gateway times out | DoIP returns timeout NRC 0x78 (RequestCorrectlyReceivedResponsePending) then error; no gateway hang |

### Acceptance Criteria
- Gateway routing latency (cellular → CAN → response → cellular): ≤ 150 ms for single-frame UDS
- Routing table correctly configured: 100% of target ECUs reachable via correct bus
- Concurrent sessions: ≥ 3 simultaneous DoIP sessions supported

---

## Q63: AUTOSAR Classic vs. Adaptive — TCU Software Architecture Decision

### Scenario
The OEM must decide whether to implement the new TCU software on AUTOSAR Classic Platform (CP) or AUTOSAR Adaptive Platform (AP). Provide the architectural decision framework.

### Comparison

| Attribute | AUTOSAR Classic (CP) | AUTOSAR Adaptive (AP) |
|-----------|---------------------|----------------------|
| Execution model | Static; tasks pre-defined at build time | Dynamic; services start/stop at runtime |
| OS | AUTOSAR OS (RTOS, OSEK) | POSIX-compliant (Linux/QNX) |
| Communication | COM stack (signal-based, SWC) | ara::com (service-oriented, SOME/IP) |
| Language | C (primarily) | C++14/17 |
| Dynamic reconfiguration | No; fixed at design time | Yes; add/remove services at runtime |
| OTA update granularity | Full ECU firmware update | Individual application update |
| Processing requirement | Low-power MCU (Cortex-M) | High-throughput SoC (Cortex-A) |
| Use case | Safety-critical ECUs (ABS, airbag) | Connectivity, infotainment, OTA management |
| Tooling | Vector, AUTOSAR CP tools | AUTOSAR AP SDK, C++ toolchain |
| ASIL rating | Up to ASIL D | Up to ASIL B (AP with safety extension) |

### TCU Architecture Decision
- TCU Application Processor (connectivity, OTA, fleet management): **AUTOSAR Adaptive** (needs dynamic services, high bandwidth, C++ app stack).
- TCU Safety Monitor (eCall trigger, backup power management): **AUTOSAR Classic** or bare-metal ASIL microcontroller (simpler, deterministic).
- Many production TCUs use a dual-chip architecture: AP + CP cores communicating via internal bus.

### Acceptance Criteria
- AP application update: individual service updated via OTA without rebooting CP partition
- CP eCall logic: deterministic latency ≤ 200 ms from trigger to 112 dial
- Memory partition: CP and AP isolated (no shared memory without access control)

---

## Q64: TCU Power Management — Sleep Modes, Wake-Up Sources, and Battery Drain

### Scenario
A vehicle is parked for 4 weeks. The TCU must remain available for remote wake-up (e.g., remote DTC read) while minimizing 12V battery drain. Describe the power modes and expected current consumption.

### Power Mode State Machine

```
[IGNITION_ON] → Full operation: LTE + GNSS + CAN active: ~300 mA @ 12V

[IGNITION_OFF — 5 min] → Graceful shutdown:
  - Close cellular connections
  - Save state to NVM
  - Enter SLEEP mode

[SLEEP mode] → 
  - CAN bus monitoring (NM wake-up): ~5 mA
  - LTE modem: paging channel only (PSM / eDRX): ~1.5 mA avg
  - GNSS: off
  - AP processor: off; CP microcontroller only: ~2 mA
  → Total sleep current: ~8.5 mA

[DEEP_SLEEP (if no remote access needed for 7+ days)] →
  - LTE: completely off
  - CP: minimal timer only
  → Total deep sleep current: ~0.5 mA
```

**Battery Drain Calculation:**
- Vehicle battery: 60 Ah.
- Sleep current: 8.5 mA.
- Discharge time: 60,000 mAh / 8.5 mA ≈ **7,059 hours ≈ 29 days** before full discharge.
- For 4-week parking: borderline! Solution: scheduled eDRX (extended discontinuous reception) extends sleep periods.

### Wake-Up Sources

| Source | Mechanism | Latency |
|--------|-----------|---------|
| Ignition ON | CAN NM wake-up frame | ≤ 500 ms to full power |
| Remote diagnostic request | LTE modem wakes on incoming SMS / Data push | ≤ 3 s from deep sleep |
| Vehicle motion (theft) | Accelerometer interrupt to CP | ≤ 200 ms |
| Scheduled OTA (2 AM) | CP RTC alarm | ≤ 5 s to cellular ready |

### Acceptance Criteria
- Sleep current: ≤ 10 mA (prevents parasitic drain exceeding 30-day parking limit)
- Wake from sleep (remote request): ≤ 5 s to cellular data ready
- Deep sleep mode (> 7 days park): ≤ 1 mA total; explicit remote wake by workshop via CAN diagnostic wake

---

## Q65: TCU Functional Safety — ASIL Classification for eCall

### Scenario
eCall is a life-safety function. If the eCall module fails and cannot dial 112 after a crash, an occupant may die. What ASIL level applies, and what design requirements follow?

### ASIL Derivation (ISO 26262 Part 3)

**Hazard Analysis:**
- Hazardous event: eCall fails to activate after severe crash.
- Harm: occupants not found; preventable deaths.

**ASIL Parameters:**
- **Severity (S)**: S3 (life-threatening / fatal).
- **Exposure (E)**: E1 (very low probability — severe crash is rare).
- **Controllability (C)**: C3 (occupants may be unconscious; cannot self-rescue).

**ASIL = S3 × E1 × C3 → ASIL A** (per ISO 26262 Table B.1)

_Note: Despite low exposure, the consequence severity and low controllability result in ASIL A._

**ASIL A Design Requirements:**
- Fault detection via periodic self-test (hardware + software).
- FMEA (Failure Mode and Effects Analysis) for eCall hardware.
- Documented safety goal: "The eCall function shall activate within 5 s of a valid crash trigger with a probability of failure on demand < 10⁻⁵/h."
- Software: MISRA-C compliance; code review; unit test coverage ≥ 95%.

### Acceptance Criteria
- ASIL A safety goal: Probability of Failure on Demand (PFD) < 10⁻⁵/h for eCall module
- Periodic self-test (see Q27): detects ≥ 90% of hardware failures
- Safety analysis (FMEA + FTA) documented and reviewed by Functional Safety Engineer

---

## Q66: CAN-FD for Telematic Gateway — Why the Upgrade from Classical CAN?

### Scenario
A new vehicle platform migrates the TCU from CAN 2.0B (250 kbps) to CAN-FD (ISO 11898-1, 2 Mbps). What operational improvements does this bring for telematics, and what compatibility challenges must be addressed?

### CAN vs. CAN-FD Comparison

| Feature | Classical CAN | CAN-FD |
|---------|--------------|--------|
| Max data rate | 1 Mbps | 8 Mbps (data phase) |
| Max payload | 8 bytes | 64 bytes |
| Arbitration phase | Equal to data | Nominal (slower, 500 kbps) for arbitration |
| FD CRC | 15-bit CRC | 17/21-bit CRC (stronger error detection) |
| Backwards compatible | N/A | CAN-FD frames rejected by Classic CAN nodes |

**Benefits for Telematics Gateway:**
- UDS over CAN-FD: larger diagnostic frames (64-byte payload) reduce segmentation overhead.
- OTA data pre-staging from TCU to ECU: CAN-FD (2 Mbps) vs. CAN 2.0 (500 kbps) = 4× faster ECU firmware transfer.
- Sensor fusion data to TCU: higher bandwidth allows richer datasets.

### Compatibility Challenge
- Legacy CAN nodes (Classic CAN) on the same bus: they cannot receive CAN-FD frames.
- Solution: separate CAN-FD network (new ECUs) from Classic CAN buses; TCU bridges both.

### Acceptance Criteria
- CAN-FD controller tested: ≥ 100% frame receive rate at 2 Mbps under 70% bus load
- No EMC violations from CAN-FD higher edges (faster slew rates): verified per CISPR 25
- Gateway correctly bridges CAN-FD ↔ Classic CAN: payload fragmentation transparent to both sides

---

## Q67: DoIP (Diagnostics over IP) — Vehicle Discovery and Routing Activation

### Scenario
A workshop scan tool connects to the vehicle via OBD-II Ethernet (ISO 13400). Walk through the DoIP discovery and routing activation sequence in detail.

### DoIP Discovery Sequence (UDP Broadcast)

```
T=0  Scan tool sends UDP broadcast to 255.255.255.255:13400
     Payload: DoIP_VehicleIdentification_Request
             {payloadType: 0x0001}

T=10ms  Vehicle DoIP gateway responds:
     Payload: DoIP_VehicleIdentification_Response {
       VIN: "WBAJF91060L000001"
       LogicalAddress: 0x0E80  (gateway address)
       EID: 6-byte Ethernet MAC
       GID: 6-byte group ID (fleet/OEM group)
       FurtherAction: 0x00 (no further action required)
     }

T=50ms  Scan tool opens TCP connection to vehicle IP:13400
T=60ms  DoIP Routing Activation Request:
     {sourceAddress: 0x0E80, activationType: 0x00, reserved: 0x00000000}
Response: {responseCode: 0x10 (OK), logicalAddress: (gateway)}

→ Diagnostic session open; UDS messages may now flow
```

### Acceptance Criteria
- Vehicle Identification Response: < 50 ms after UDP broadcast
- TCP Routing Activation: ≤ 100 ms
- Gateway correctly routes to all ECUs in routing table per Q62

---

## Q68: TCU Operating System — Linux vs. QNX for Automotive Telematics

### Scenario
The OEM must choose between an Automotive Linux (AGL / GENIVI) and QNX Neutrino RTOS for the TCU application processor. What are the trade-offs?

### Comparison

| Attribute | Linux (AGL/GENIVI) | QNX Neutrino RTOS |
|-----------|-------------------|--------------------|
| Open source | Yes (GPL/permissive) | No (commercial license) |
| Determinism | Soft real-time (PREEMPT_RT) | Hard real-time (microkernel) |
| Automotive safety (ISO 26262) | Up to QM / ASIL A (with effort) | ASIL B/D certified (QNX certifiable) |
| Boot time | 5–15 s (kernel + systemd) | < 2 s (fast boot) |
| Ecosystem | Large (AUTOSAR AP, Android Auto) | Mature automotive ecosystem (instrument clusters common) |
| Over-the-Air update tools | SWUpdate, RAUC (mature OSS) | Custom or commercial |
| Tooling cost | Low (open source) | License cost per device |
| Memory footprint | Higher | Lower |

**For TCU with eCall (safety function):**
- eCall isolation: if on Linux, run eCall on a separate ASIL-rated microcontroller (separate core or separate IC).
- QNX: eCall-certified partition with defined time/memory budgets.

### Acceptance Criteria
- eCall application: deterministic latency ≤ 200 ms regardless of OS choice (separate partition or microcontroller)
- OS boot to cellular ready: ≤ 5 s
- Automotive-grade OS certification evidence provided to OEM safety team

---

## Q69: SOME/IP — Service-Oriented Middleware for Telematics

### Scenario
The TCU uses AUTOSAR Adaptive and communicates with the central gateway using SOME/IP (Scalable Service-Oriented Middleware over IP). Describe how a telematics service subscribes to the vehicle speed signal.

### SOME/IP Service Discovery + Event Subscription

```
TCU (Client)                       Central Gateway (Server)
│                                         │
│── SOME/IP SD Find Service ────────────→│  (UDP broadcast port 30490)
│   {vehicleSpeedService, Instance 1}    │
│                                         │
│←── SOME/IP SD Offer Service ───────────│
│   {serviceID=0x1234, IP=192.168.1.5,   │
│    eventGroupID=0x0001}                │
│                                         │
│── SOME/IP SD Subscribe Event Group ───→│
│   {serviceID=0x1234, eventGroup=0x0001}│
│←── SOME/IP SD Subscribe ACK ──────────│
│                                         │
│←── SOME/IP Event Notification ─────────│  (every 100 ms or on change)
│   {serviceID=0x1234, method=0x8001,    │
│    payload: speed=72 km/h}             │
```

**Serialization:** SOME/IP payload serialized as big-endian binary (SOME/IP serialization or protobuf for higher layers).

### Acceptance Criteria
- Service discovery completes: ≤ 500 ms after network up
- Event notification at 100 ms intervals: measured latency ≤ 200 ms (network round-trip)
- SOME/IP implementation interoperable with Vector and AUTOSAR AP reference implementations

---

## Q70: TCU Hardware Validation — Environmental Testing Requirements

### Scenario
A new TCU PCB must pass automotive environmental qualification before production. List all required tests and acceptance criteria.

### Environmental Test Matrix (AEC-Q100 / ISO 16750)

| Test | Standard | Condition | Accept Criteria |
|------|---------|-----------|----------------|
| Temperature cycling | ISO 16750-4 | −40°C to +85°C; 500 cycles | No physical failure; functional after |
| Thermal shock | ISO 16750-4 | −40°C to +125°C; 100 cycles (fast ramp) | No solder joint failure |
| Vibration (engine compartment) | ISO 16750-3 | 5–2000 Hz sweep; 1 g random | No component displacement |
| Mechanical shock | ISO 16750-3 | 50 g / 11 ms half-sine | Functional immediately after |
| Salt spray corrosion | ISO 9227 | 96 hours 5% NaCl | No corrosion causing functional failure |
| IP rating (ingress protection) | IEC 60529 | IP54: dust semi-protected; splash proof | No ingress affecting function |
| EMC emissions | CISPR 25 Class 5 | 100 kHz–1000 MHz antenna method | Under Class 5 limits |
| EMC immunity | ISO 11452-2 | 200 MHz–1 GHz; 100 V/m | Functional during test |
| ESD (electrostatic) | IEC 61000-4-2 | ±8 kV contact; ±15 kV air | No latch-up; functional after |
| Operating voltage range | ISO 16750-2 | 6–18 V DC; load dump 87 V / 400 ms | Functional; no component damage |

### Acceptance Criteria
- All tests passed: zero critical failures in qualification batch (3 samples minimum per test)
- Thermal shock: ≤ 0.5% solder joint failure rate (X-ray inspection post-test)
- EMC: Class 5 emissions at all frequencies; immunity with functional performance criterion A (no degradation)
