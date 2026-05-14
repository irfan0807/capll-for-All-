# 04 — dSPACE SCALEXIO Architecture

> **Tool**: dSPACE SCALEXIO real-time hardware platform  
> **Prerequisites**: Real-Time Concepts (03)  
> **Outcome**: Select the correct boards for a project, understand IOCNET, build a HIL rack mentally

---

## 1. What Is dSPACE SCALEXIO?

SCALEXIO is dSPACE's **modular, scalable HIL platform** designed for automotive ECU testing. It replaced the older DS1006/DS1005 systems with a modern, scalable architecture.

```
SCALEXIO Physical Architecture:
─────────────────────────────────────────────────────────────
┌──────────────────────────────────────────────────────────┐
│                   SCALEXIO Rack                          │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  DS6001  Processor Board (Intel Xeon, QNX RTOS)   │  │
│  │  └─► Real-time application runs here              │  │
│  └────────────────────────────────────────────────────┘  │
│                         │                                │
│                    IOCNET (1 Gbit/s)                     │
│                         │                                │
│  ┌──────────┐  ┌────────┴───┐  ┌──────────┐            │
│  │ DS1552   │  │  DS4330    │  │  DS2655   │            │
│  │ CAN FD   │  │  Ethernet  │  │  FPGA     │            │
│  │ 8× buses │  │ 4× 100BASE-│  │  Virtex-7 │            │
│  └──────────┘  │   T1       │  └──────────┘            │
│                └────────────┘                           │
│  ┌──────────┐  ┌────────────┐  ┌──────────┐            │
│  │ DS2211   │  │  DS5202    │  │  DS2680   │            │
│  │ Analog   │  │  Motor     │  │  Digital  │            │
│  │ I/O      │  │  Control   │  │  I/O      │            │
│  └──────────┘  └────────────┘  └──────────┘            │
└──────────────────────────────────────────────────────────┘
```

---

## 2. SCALEXIO Board Catalog

### DS6001 — Processor Board (The Brain)
```
Specification:
  CPU:       Intel Xeon (multi-core, 3+ GHz)
  OS:        dSPACE RTOS (QNX-based)
  RAM:       16 GB DDR4
  Storage:   SSD for application + data
  Interface: IOCNET to I/O boards, GigE to host PC

Key rules:
  - Maximum one DS6001 per SCALEXIO system
  - All application code runs here
  - Communicates with I/O boards over IOCNET
  - Connected to host PC via Ethernet (ControlDesk)
```

### DS1552 — CAN FD Board
```
Features:
  - 8 independent CAN FD channels
  - ISO 11898-2 compliant
  - Baud rates: up to 8 Mbit/s (data phase)
  - Hardware timestamping: < 1 µs accuracy
  - Error frame injection
  - Bus load monitoring

Use when:
  - ECU has CAN or CAN FD bus connections
  - Need restbus simulation
  - Fault injection on CAN bus
```

### DS4330 — Automotive Ethernet Board
```
Features:
  - 4× 100BASE-T1 (single-pair Ethernet)
  - 1× 1000BASE-T1 (optional)
  - OPEN Alliance TC8 compliant
  - Hardware timestamping
  - VLAN support (802.1Q)
  - gPTP support (802.1AS)

Use when:
  - ECU uses DoIP or SOME/IP
  - Testing Automotive Ethernet communication
  - OTA update validation
```

### DS2655 — FPGA Base Board (Virtex-7)
```
Features:
  - Xilinx Virtex-7 FPGA (330k logic cells)
  - Interfaces to I/O boards directly
  - Sub-microsecond I/O latency
  - Programmed via dSPACE FPGA Programming Blockset
  - Supports custom protocols (SPI, I2C, encoder)

Use when:
  - PWM > 10 kHz
  - High-speed ADC/DAC
  - Custom sensor simulation
  - Fault injection < 1 µs
```

### DS2211 — Analog I/O Board
```
Features:
  - 16 analog inputs (16-bit, 1 MS/s)
  - 8 analog outputs (16-bit, 1 MS/s)
  - ±10 V range (configurable)
  - Simultaneous sampling

Use when:
  - Sensor voltage simulation (throttle position, temperature)
  - Motor feedback simulation
  - Analog actuator command measurement
```

### DS2680 — Digital I/O Board
```
Features:
  - 32 digital I/O lines (configurable per pin)
  - 3.3 V / 5 V / 12 V / 24 V levels
  - PWM input/output (configurable)
  - Frequency measurement

Use when:
  - Button/switch simulation
  - PWM fan/motor simulation
  - Digital enable/disable lines
```

### DS5202 — Motor Control Board
```
Features:
  - 12 MOSFET gate drive outputs
  - 8 ADC channels for motor current
  - Encoder interface
  - Resolver interface
  - Hardware protection (overcurrent, overvoltage)

Use when:
  - EV motor controller testing
  - BLDC/PMSM drive validation
  - BMS HIL testing
```

---

## 3. IOCNET — The Internal Communication Bus

IOCNET (I/O Communication Network) is the private, high-speed bus connecting the DS6001 processor to all I/O boards:

```
IOCNET characteristics:
  - 1 Gbit/s deterministic ring topology
  - Latency: < 100 µs round-trip (CPU ↔ I/O board)
  - Automatic discovery: DS6001 enumerates connected boards
  - Redundant paths available in large systems
  - Not accessible externally (internal only)

Data flow:
  Application (DS6001)
       │
       │ IOCNET write (1 ms cycle)
       ▼
  DS2211 DAC output → 0–5 V analog to ECU sensor pin
  DS1552 CAN Tx     → CAN frame to ECU network
  DS4330 Eth Tx     → Ethernet frame to ECU
```

---

## 4. dSPACE Software Tools Overview

```
Tool                  Purpose
──────────────────────────────────────────────────────────────
ConfigurationDesk     Configure hardware (I/O, buses, timing)
ControlDesk           Monitor and control real-time application
AutomationDesk        Automate test sequences
SYNECT                Manage projects, versions, configurations
ModelDesk             Configure vehicle model (if using CarMaker)
MotionDesk            3D animation of vehicle simulation
RTMaps                Sensor data processing middleware
──────────────────────────────────────────────────────────────
```

---

## 5. Board Selection Guide

```
Project Requirement                 → Board Needed
──────────────────────────────────────────────────────────────
ECU has 4× CAN FD                  → 1× DS1552
ECU has DoIP Ethernet              → 1× DS4330
ECU has analog sensors             → 1× DS2211 (or DS2212)
ECU has PWM inputs/outputs         → DS2680 or DS2655 FPGA
ECU is EV motor controller         → DS5202
Need fault injection < 1 µs        → DS2655 FPGA
Need custom sensor SPI interface   → DS2655 FPGA
All of the above                   → DS6001 + all boards above
──────────────────────────────────────────────────────────────

Sizing rule:
  I/O boards: limited by IOCNET bandwidth (total 1 Gbit/s)
  CPU task:   stay < 75% of period budget
  Memory:     16 GB RAM is usually more than enough
```

---

## 6. Connecting ECU to SCALEXIO HIL

```
Physical Connection Map (example: ADAS domain controller):
────────────────────────────────────────────────────────────────────
ECU Pin          Wire to         SCALEXIO Board   Signal Type
────────────────────────────────────────────────────────────────────
CAN1_H/L         ──────────────► DS1552 CH1       CAN FD restbus
CAN2_H/L         ──────────────► DS1552 CH2       CAN FD (powertrain)
ETH_100BASE-T1   ──────────────► DS4330 CH1       DoIP / SOME/IP
VCC (12V)        ──────────────► Power supply     ECU power
GND              ──────────────► GND rail         Ground
Radar_SYNC_PWM   ──────────────► DS2680 GPIO1     50 Hz trigger
KL15 (ignition)  ──────────────► DS2680 GPIO2     Ignition simulation
DIAG_K-Line      ──────────────► DS1552 LIN CH1   Legacy diagnostics
────────────────────────────────────────────────────────────────────
```

---

## 7. SCALEXIO vs. Older DS1006

| Feature | DS1006 (legacy) | SCALEXIO |
|---------|----------------|----------|
| Processor | PowerPC | Intel Xeon |
| RTOS | dSPACE custom | QNX-based |
| I/O connection | PCI backplane | IOCNET (Ethernet) |
| Scalability | Fixed chassis | Modular, add boards |
| CAN FD support | No | Yes (DS1552) |
| Eth (100BASE-T1) | No | Yes (DS4330) |
| FPGA | External board | DS2655 |
| Max sample rate | 1 µs | 100 ns (FPGA) |

---

## 8. Interview Q&A

**Q1: What is IOCNET in SCALEXIO?**  
IOCNET is the internal 1 Gbit/s deterministic bus connecting the DS6001 processor board to all I/O boards. It replaces the PCI backplane of older dSPACE systems. The processor reads/writes I/O board registers over IOCNET each task cycle, with < 100 µs latency.

**Q2: How would you select boards for an ADAS ECU HIL setup with 6× CAN FD and 2× 100BASE-T1?**  
I would choose: DS6001 (processor), one DS1552 (8 CAN FD channels, covers all 6 buses), one DS4330 (4× 100BASE-T1, covers both Ethernet links). If the ECU also has analog sensor inputs I'd add DS2211. The DS2655 FPGA would be added if any signal needs sub-microsecond response.

**Q3: What is the 75% CPU rule?**  
Keep maximum CPU task execution time below 75% of the task period. For a 1 ms task, execution time must stay below 750 µs. The remaining 25% provides headroom for interrupt latency, cache misses, and timing jitter. Violating this rule causes sporadic overruns.

**Q4: What board would you use to inject a fault on a PWM signal in < 1 µs?**  
The DS2655 FPGA base board, programmed with the dSPACE FPGA Programming Blockset. CPU-based fault injection has ~10 µs minimum latency (one task step). The FPGA responds in < 100 ns, which is necessary for safety-critical fault injection tests.

**Q5: How does ControlDesk communicate with the running SCALEXIO application?**  
ControlDesk connects to the DS6001 over standard Ethernet. It uses the XCP (Universal Measurement and Calibration Protocol) over Ethernet to read and write variables in the running real-time application without stopping it. This is the standard dSPACE online calibration mechanism.
