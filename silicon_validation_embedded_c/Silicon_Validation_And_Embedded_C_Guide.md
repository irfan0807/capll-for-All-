# Silicon Validation, Emulation Platforms, IP Test Planning & Embedded C
## Comprehensive Technical Reference — Pre/Post-Silicon Engineering

---

## Table of Contents

1. [Pre-Silicon Validation](#1-pre-silicon-validation)
2. [Post-Silicon Validation](#2-post-silicon-validation)
3. [Pre vs Post Silicon — Side-by-Side Comparison](#3-pre-vs-post-silicon-comparison)
4. [Emulation Platforms](#4-emulation-platforms)
5. [Test Case & Test Plan Development for IPs](#5-test-case--test-plan-development-for-ips)
6. [C & Embedded C Proficiency](#6-c--embedded-c-proficiency)
7. [Project Structure — Reference Implementation](#7-project-structure--reference-implementation)
8. [Requirements Engineering for Embedded Projects](#8-requirements-engineering-for-embedded-projects)
9. [End-to-End Workflow Example — CAN Controller IP](#9-end-to-end-workflow-example--can-controller-ip)
10. [Glossary](#10-glossary)

---

## 1. Pre-Silicon Validation

### 1.1 Definition
Pre-silicon validation is the process of verifying the functional correctness, timing, and power behaviour of a chip design **before physical silicon is manufactured**. The goal is to find as many bugs as possible in simulation or emulation, because defects discovered after tape-out can cost hundreds of thousands of dollars and months of re-spin time.

### 1.2 Stages in the Pre-Silicon Flow

```
RTL Design  →  Lint / CDC / RDC  →  Functional Simulation  →  Formal Verification
     ↓                                          ↓
 Synthesis                              Emulation / FPGA Proto
     ↓                                          ↓
Gate-Level Sim                         Coverage Closure
     ↓
Static Timing Analysis (STA)
```

| Stage | Tool Examples | What It Catches |
|---|---|---|
| RTL Lint | SpyGlass, Verilator | Coding style errors, latches, X-propagation |
| Clock Domain Crossing (CDC) | SpyGlass CDC, Meridian | Meta-stability, missing synchronizers |
| Functional Simulation | VCS, ModelSim, Xcelium | Protocol violations, datapath bugs |
| Formal Verification | JasperGold, VC Formal | Proves properties exhaustively, no test vectors needed |
| Emulation | Palladium Z1, Zebu, Veloce | SoC bring-up, SW/HW co-verification at speed |
| FPGA Prototyping | Xilinx VCU118, ZCU102 | Early software development, system-level tests |
| Gate-Level Sim | Same as functional but with netlist | Timing issues, scan chain, power gating |
| STA | PrimeTime, Tempus | Setup/hold violations across PVT corners |

### 1.3 Functional Verification Methodology (UVM)

Universal Verification Methodology (UVM) is the dominant methodology for pre-silicon functional verification.

```
┌─────────────────────────────────────────────────────────────────────┐
│  UVM Test                                                           │
│   └── UVM Environment                                              │
│         ├── UVM Agent (Active)                                     │
│         │     ├── Sequencer  ──► Sequence (stimulus)              │
│         │     ├── Driver     ──► DUT Interface (pin-level)        │
│         │     └── Monitor    ──► scoreboard / coverage             │
│         ├── UVM Agent (Passive) ← only monitor, no driver         │
│         ├── Scoreboard          ← checks DUT vs reference model   │
│         └── Coverage Collector  ← functional + code coverage      │
│  DUT (RTL under test)                                               │
└─────────────────────────────────────────────────────────────────────┘
```

**Key UVM Concepts**

- **Sequence**: Generates stimulus — constrained-random or directed.  
- **Driver**: Translates transactions into pin wiggling (protocol-aware).  
- **Monitor**: Observes bus traffic non-intrusively; publishes to TLM ports.  
- **Scoreboard**: Compares DUT output against a golden reference model.  
- **Coverage**: Both code coverage (line/branch/toggle/FSM) and functional coverage (covergroups/coverpoints).

### 1.4 Coverage-Driven Verification (CDV)

```
Test Plan (Feature → Coverage Model)
        ↓
Write covergroups / cover properties
        ↓
Run constrained-random tests
        ↓
Measure coverage holes → write directed tests to hit them
        ↓
Coverage sign-off (typically 100% functional, >95% code)
```

Coverage types:

| Type | Meaning | Example |
|---|---|---|
| Line | Every RTL line executed | All reset sequences |
| Branch | Every if/else taken | CRC error vs no-error path |
| Toggle | Every net toggled 0→1 and 1→0 | All data bus bits active |
| FSM | Every state + every arc | CAN bus integration states |
| Functional | Designer-defined cross-products | DLC × IDE × frame type |

### 1.5 Assertion-Based Verification (ABV)

SVA (SystemVerilog Assertions) are used inline in RTL or in bind files.

```systemverilog
// Immediate assertion — checked procedurally
always @(posedge clk) begin
  assert (fifo_full -> ~wr_en)
    else $error("Write to full FIFO at time %0t", $time);
end

// Concurrent assertion — temporal, always active
property no_spurious_ack;
  @(posedge clk) disable iff (rst_n == 0)
  req |-> ##[1:4] ack;
endproperty
assert property (no_spurious_ack)
  else $fatal(1, "ACK not seen within 4 cycles of REQ");
```

### 1.6 Pre-Silicon Test Plan Template

```
Test Plan: CAN Controller IP — Pre-Silicon
Version   : 1.0
Date      : 2026-05-05
Author    : Silicon Validation Engineer

1. SCOPE
   IP block under test: CAN 2.0B / CAN-FD Controller
   Reference Spec: ISO 11898-1:2015, Bosch CAN FD 1.0

2. FEATURES TO VERIFY
   F1  — Basic frame TX (standard + extended)
   F2  — Basic frame RX with acceptance filter
   F3  — CAN FD frame TX/RX (up to 64 bytes)
   F4  — Error detection: bit error, stuff error, CRC error, form error, ACK error
   F5  — Error counters: TEC / REC increment/decrement rules
   F6  — Bus-off entry and recovery
   F7  — Arbitration (multi-node simulation)
   F8  — Interrupt generation and masking
   F9  — DMA interface
   F10 — Low power / sleep mode

3. STIMULUS PLAN
   3.1 Constrained-random with UVM sequences
   3.2 Corner-case directed tests (bit timing at limits, max DLC)
   3.3 Error injection via backdoor and interface forcing

4. COVERAGE GOALS
   Code coverage  : ≥ 95% line, ≥ 90% branch, ≥ 85% toggle
   Functional cov : 100% (all covergroups sampled)
   Assertions     : 0 failures at sign-off

5. EXIT CRITERIA
   No P1/P2 bugs open
   Coverage goals met
   Formal closure on key properties
```

---

## 2. Post-Silicon Validation

### 2.1 Definition
Post-silicon validation is performed on **actual physical silicon** — engineering samples (ES) or production samples. The objectives shift from functional correctness (largely proven pre-silicon) to:

- **Silicon bring-up** — getting the first chip to boot.
- **Debug of silicon bugs** — issues not caught in simulation.
- **Characterisation** — measuring actual timing, power, noise margins.
- **Compliance testing** — meeting external standards (USB, PCIe, CAN, Ethernet).
- **Yield improvement** — identifying systemic failure patterns.

### 2.2 Post-Silicon Flow

```
Silicon Arrives (ES0)
       ↓
Power-on sequencing validation
       ↓
Clock / PLL bring-up
       ↓
Basic CPU / memory smoke test
       ↓
IP block bring-up (SPI, I2C, CAN, Ethernet…)
       ↓
Software / Firmware bring-up
       ↓
Full regression (automated)
       ↓
Characterisation (PVT corners: min/typ/max voltage × −40°C to 125°C)
       ↓
Compliance & Certification
       ↓
Production Qualification (AEC-Q100 for automotive)
```

### 2.3 Tools and Equipment

| Category | Tool | Purpose |
|---|---|---|
| Logic Analyser | Saleae Logic Pro 16, Keysight 16850 | Bus protocol capture |
| Oscilloscope | Tektronix MSO 6, Keysight DSOX | Signal integrity, timing |
| Protocol Analyser | Vector CANalyzer, Wireshark | CAN/LIN/Ethernet decode |
| JTAG Debugger | Lauterbach TRACE32, OpenOCD | CPU debug, memory peek/poke |
| Power Analyser | Yokogawa WT310, Keysight N6705 | Dynamic current measurement |
| Thermal Chamber | Tenney T-series | Temperature stress testing |
| ATE | Advantest T2000, Teradyne UltraFLEX | Mass production testing |
| Automated Test | Python + PyVISA + pyvxicom | Lab automation, bench scripts |

### 2.4 Post-Silicon Debug Techniques

**Hardware Debug**

```
1. JTAG boundary scan — verify device is alive, read IDCODE
2. Memory Built-In Self-Test (MBIST) — run on all embedded SRAMs
3. Scan chain test — structural test for stuck-at and transition faults
4. BIST / LBIST — logic self-test for cores without external tester access
```

**Software-Assisted Debug**

```
1. Boot ROM execution trace via JTAG
2. Register read/write via debug access port (DAP / AHB-AP)
3. Trace buffer (ETM/PTM) for instruction-level post-mortem
4. Performance counter reads (PMU) to isolate bottlenecks
```

**Signal Integrity Debug**

```
1. Eye diagram at SerDes receiver — check BER
2. Jitter measurement (TIE histogram, Rj/Dj separation)
3. S-parameter measurements for PCB traces
4. Power supply noise correlation with functional failures
```

### 2.5 Post-Silicon Test Plan Template

```
Post-Silicon Validation Plan: SoC Automotive Cluster Chip
Version : 1.0
Date    : 2026-05-05

PHASE 1 — SILICON BRING-UP (ES0, 2 weeks)
  1.1  Power rail sequencing — verify PMIC outputs within ±3%
  1.2  Crystal oscillator start-up — measure frequency accuracy
  1.3  JTAG connectivity — confirm TAP responds, read IDCODE
  1.4  MBIST — run on all SRAMs, expect PASS
  1.5  CPU0 boot — execute from internal ROM, observe UART output

PHASE 2 — IP VALIDATION (ES0/ES1, 6 weeks)
  2.1  CAN FD — loopback + external node tests at all baud rates
  2.2  LIN Master/Slave — schedule table execution, error injection
  2.3  SPI Flash — read/write/erase at max frequency, all CS
  2.4  I2C — master and slave modes, 100k/400k/1MHz
  2.5  Ethernet AVB — frame TX/RX, gPTP sync accuracy < 1µs
  2.6  LPDDR4 — traffic patterns at 3200 MT/s, stress at voltage extremes

PHASE 3 — SYSTEM VALIDATION (ES1, 4 weeks)
  3.1  RTOS boot and task scheduling on all cores
  3.2  DMA transfers between all IPs
  3.3  Interrupt latency measurement for all sources
  3.4  Watchdog and reset recovery

PHASE 4 — CHARACTERISATION (ES1, 4 weeks)
  4.1  Frequency vs voltage sweep (F-V characterisation)
  4.2  Power states: active, idle, sleep, deep-sleep
  4.3  Temperature range: −40°C, 25°C, 105°C, 125°C
  4.4  PVT-corner regression: SS/FF/SF/FS corners

PHASE 5 — COMPLIANCE & QUALIFICATION (ES2/MP, 8 weeks)
  5.1  CAN ISO 11898-1 compliance (Vector CANoe test suite)
  5.2  CISPR 25 EMC (external lab)
  5.3  AEC-Q100 Grade 1 qualification (−40°C to 125°C)
  5.4  ISO 26262 FMEA and safety mechanism testing

EXIT CRITERIA
  Zero P1 bugs open
  All compliance tests passed
  AEC-Q100 PPAP documentation complete
```

---

## 3. Pre vs Post Silicon Comparison

| Dimension | Pre-Silicon | Post-Silicon |
|---|---|---|
| Medium | RTL / Netlist / Emulator | Physical chip on PCB |
| Speed | Simulation: ~kHz; Emulation: ~MHz | Real silicon: GHz |
| Observability | Full — any signal visible | Limited — pins, JTAG, trace buffers |
| Controllability | Full — any state injectable | Limited — must use real interfaces |
| Bug Fix Cost | Low — RTL edit, re-sim in minutes | High — re-spin may take 3–6 months |
| Bug Type Found | Functional, micro-arch, X-propagation | Silicon bugs, analog, yield, margins |
| Team | Design Verification (DV) engineers | Silicon Validation (SiVal) / bring-up engineers |
| Languages | SystemVerilog, UVM, C for embedded | C, Python, JTAG scripts, shell |
| Coverage | Code + functional coverage metrics | Test coverage from test cases, scope captures |

---

## 4. Emulation Platforms

### 4.1 What is Emulation?

An emulator maps RTL design onto a **reconfigurable hardware fabric** (typically FPGAs) to run orders of magnitude faster than software simulation while retaining full RTL visibility. It bridges the gap between simulation (cycle-accurate but slow) and real silicon (fast but limited debug).

```
Simulation  ──  kHz     ──  Full observability  ──  cheap to change
Emulation   ──  1–10 MHz ──  Near-full observability  ──  expensive platform
FPGA Proto  ──  10–100 MHz ── Limited observability  ──  moderate cost
Real Silicon──  GHz     ──  Very limited visibility  ──  very expensive to fix
```

### 4.2 Major Emulation Platforms

#### Cadence Palladium Z1 / Z2

```
Architecture  : Custom ASIC-based emulation fabric
Speed         : Up to 10 MHz emulation clock
Capacity      : Up to 9 billion gates (Z2)
Key features  :
  - Transaction-based acceleration (TBA)
  - In-circuit emulation (ICE) — connects real devices over interface
  - Power analysis (dynamic power estimation)
  - Assertion replay
  - Deep debug with time-travel debug capability
Use cases     : SoC-level software bring-up, VIP-based protocol testing
```

#### Synopsys ZeBu Server 4

```
Architecture  : FPGA-based (Xilinx UltraScale+)
Speed         : 5–50 MHz depending on design complexity
Capacity      : Up to 8 billion gates
Key features  :
  - zebu Studio GUI for setup and debug
  - zFPD (FPGA Debug) — run-stop debug like a simulator
  - Hybrid emulation + virtual platform (ARM FastModels)
  - PCIe host-based acceleration
Use cases     : SoC verification, hypervisor bring-up, Android boot
```

#### Mentor Veloce Strato

```
Architecture  : Custom ASIC fabric
Speed         : 100 MHz+
Key features  :
  - AppMD (Application Multi-Domain) for multi-chip designs
  - In-circuit emulation (ICE)
  - AppLINK — connects to real test benches
Use cases     : Networking SoCs, storage controllers
```

#### FPGA Prototyping (Xilinx / Intel)

```
Boards   : Xilinx VCU118, ZCU102, Alveo; Intel Stratix 10 MX
Speed    : 30–200 MHz
Capacity : Limited (1–2 billion ASIC gates per board; multi-FPGA for large SoCs)
Trade-off: Less observability, faster speed, lower cost than emulator
Use case : Early driver development, OS porting before silicon
```

### 4.3 Emulation Setup Workflow

```
Step 1 — RTL Compile
  emcc -techlib <emulator_lib> -top soc_top -f filelist.f -o soc.emu

Step 2 — Elaboration
  Partition design across emulator fabric
  Place-and-route on ASIC/FPGA fabric
  Estimate achieved clock rate

Step 3 — Test bench connection
  - UVM test bench running on host CPU via SCE-MI (Standard Co-Emulation Modeling Interface)
  - Or transactors bridge between software model and hardware DUT

Step 4 — Execution
  emrun -cfg soc.cfg -test <test_name> -waves <probe_list>

Step 5 — Debug
  - Load waveform into Verdi / DVE
  - Use time-travel debug to replay failing sequences
  - Check assertions triggered in emulation run
```

### 4.4 SCE-MI Transactor Model

```
Host (x86)                      Emulator Fabric
──────────────────               ──────────────────────────────
UVM Test                         Hardware Transactor
  │                                     │
  │  TLM transaction                    │  Pin-level wiggling
  ├──────────────────────► SCE-MI ─────►│─────────────────► DUT RTL
  │                       Bridge        │                       │
  │◄──────────────────────────────────◄─│◄──────────────────────┘
  │  Response transaction              Monitor transactor
```

### 4.5 In-Circuit Emulation (ICE)

ICE connects the emulated design to real hardware components:

```
                     ┌─────────────────────────┐
  Real CAN Bus ──────► ICE Cable / Breakout     │
  Real Sensor  ──────► Board connects to        ├──► Emulator Fabric (DUT RTL)
  Real Memory  ──────► physical I/O pins        │
                     └─────────────────────────┘
```

This enables:
- Testing with actual ECU traffic on a live CAN bus.
- Connecting real sensors (camera, radar) to an emulated ISP/DSP.
- Testing power sequences with real PMIC.

### 4.6 Emulation Accelerated Use Cases

| Use Case | Why Emulation vs Simulation |
|---|---|
| Linux/Android boot | Billions of cycles; simulation would take weeks |
| USB enumeration | Complex host stack; too slow in sim |
| Camera frame processing | 30 fps = millions of cycles per frame |
| OTA firmware update | Flash write sequences over hours |
| AUTOSAR OS scheduling | Multi-core scheduling over ms of real time |
| CAN bus stress test | 1000 frames at 5 Mbps CAN-FD |

---

## 5. Test Case & Test Plan Development for Various IPs

### 5.1 General Test Plan Structure

Every IP test plan follows this structure:

```
1. Document Header       — IP name, version, author, date, approver
2. Scope                 — what is tested, what is out-of-scope
3. Reference Documents   — specifications, architecture doc, register map
4. Feature List          — enumerated list of all features to verify
5. Test Strategy         — methodology (directed, CDV, formal)
6. Test Environment      — TB architecture, tools, simulators
7. Test Case Table       — ID, feature, type, priority, expected result
8. Coverage Plan         — code and functional coverage targets
9. Exit Criteria         — bug counts, coverage thresholds
10. Schedule & Milestones
```

### 5.2 CAN FD Controller IP — Full Test Plan

```
Test Plan : CAN FD Controller IP
Doc ID    : TP-CAN-001
Version   : 2.0
Date      : 2026-05-05
SoC       : Automotive Cluster SoC

╔══════════════════════════════════════════════════════════════════════╗
║ FEATURE TABLE                                                        ║
╠═══╦═══════════════════════════════════════╦══════════╦═════════════╣
║ # ║ Feature                               ║ Priority ║ Risk        ║
╠═══╬═══════════════════════════════════════╬══════════╬═════════════╣
║ F1║ TX Standard Frame                     ║ P1       ║ Low         ║
║ F2║ TX Extended Frame                     ║ P1       ║ Low         ║
║ F3║ TX CAN-FD Frame (up to 64B)           ║ P1       ║ Medium      ║
║ F4║ RX Acceptance Filter (ID mask)        ║ P1       ║ Medium      ║
║ F5║ Error Frame Detection (all types)     ║ P1       ║ High        ║
║ F6║ TEC / REC counter management          ║ P1       ║ High        ║
║ F7║ Bus-off and auto-recovery             ║ P2       ║ High        ║
║ F8║ Interrupt (TX done, RX ready, error)  ║ P1       ║ Medium      ║
║ F9║ DMA Burst Transfer                    ║ P2       ║ Medium      ║
║F10║ Sleep / Wake-up via CAN activity      ║ P2       ║ High        ║
║F11║ Bit timing configuration             ║ P1       ║ Medium      ║
║F12║ Loopback mode (internal/external)    ║ P1       ║ Low         ║
╚═══╩═══════════════════════════════════════╩══════════╩═════════════╝

╔══════════════════════════════════════════════════════════════════════════════╗
║ TEST CASE TABLE                                                              ║
╠══════════╦════════╦════════════════════════════════════╦═══════╦═══════════╣
║ TC-ID    ║ Feature║ Description                        ║ Type  ║ Expected  ║
╠══════════╬════════╬════════════════════════════════════╬═══════╬═══════════╣
║TC-CAN-001║ F1     ║ Transmit standard frame, DLC=0     ║ Direct║ ACK bit=1 ║
║TC-CAN-002║ F1     ║ Transmit standard frame, DLC=8     ║ Direct║ ACK bit=1 ║
║TC-CAN-003║ F2     ║ Transmit extended 29-bit ID frame  ║ Direct║ IDE bit=1 ║
║TC-CAN-004║ F3     ║ CAN-FD frame, DLC=12 (10 bytes)    ║ Direct║ FDF bit=1 ║
║TC-CAN-005║ F3     ║ CAN-FD frame, DLC=15 (64 bytes)    ║ Direct║ BRS active║
║TC-CAN-006║ F4     ║ RX filter exact match, pass        ║ Direct║ Frame rcvd║
║TC-CAN-007║ F4     ║ RX filter mismatch, reject         ║ Direct║ No rcv int║
║TC-CAN-008║ F5     ║ Inject bit error in data phase     ║ Direct║ ERR frame ║
║TC-CAN-009║ F5     ║ Inject stuff error (>5 same bits)  ║ Direct║ ERR frame ║
║TC-CAN-010║ F5     ║ Inject CRC error                   ║ Direct║ ERR frame ║
║TC-CAN-011║ F6     ║ TEC increments on TX error         ║ Direct║ TEC=TEC+8 ║
║TC-CAN-012║ F6     ║ REC decrements on good RX          ║ Direct║ REC=REC−1 ║
║TC-CAN-013║ F7     ║ TEC>255 → bus-off entry            ║ Direct║ BOFF bit=1║
║TC-CAN-014║ F7     ║ 128×11 recessive bits → recovery   ║ Direct║ BOFF bit=0║
║TC-CAN-015║ F8     ║ TX done interrupt fires             ║ Direct║ INT assrtd║
║TC-CAN-016║ F8     ║ Interrupt mask — masked INT silent  ║ Direct║ No INT    ║
║TC-CAN-017║ F9     ║ DMA burst 16 frames, no CPU poll   ║ Direct║ All rcvd  ║
║TC-CAN-018║F10     ║ Sleep mode entered, wake on CAN act║ Direct║ Wake intrt║
║TC-CAN-019║ All    ║ Random frame mix, 10000 frames     ║ Random║ 0 errors  ║
║TC-CAN-020║ All    ║ Concurrent TX+RX stress            ║ Random║ 0 lost frm║
╚══════════╩════════╩════════════════════════════════════╩═══════╩═══════════╝
```

### 5.3 I2C Controller IP — Test Cases

```
TC-I2C-001  Master Write — 7-bit addr, 1 byte data, ACK received
TC-I2C-002  Master Write — 7-bit addr, 16 byte burst, all ACKed
TC-I2C-003  Master Read  — 7-bit addr, 1 byte data, NACK on last byte
TC-I2C-004  Master Read  — repeated START between write and read
TC-I2C-005  10-bit addressing — write and read
TC-I2C-006  Slave ACK — DUT as slave, ACK each byte
TC-I2C-007  Slave NACK — DUT as slave, NACK when buffer full
TC-I2C-008  Arbitration loss — two masters start simultaneously
TC-I2C-009  Clock stretching — slave holds SCL low
TC-I2C-010  Bus timeout — SCL held low > timeout → reset
TC-I2C-011  SMBus Alert — alert signal handling
TC-I2C-012  Speed modes: 100 kHz, 400 kHz, 1 MHz, 3.4 MHz (HS)
```

### 5.4 SPI Controller IP — Test Cases

```
TC-SPI-001  Single byte TX, CPOL=0 CPHA=0 (Mode 0)
TC-SPI-002  Single byte TX, all 4 modes (0,1,2,3)
TC-SPI-003  Full-duplex TX+RX simultaneously
TC-SPI-004  Burst 256 bytes, CS held throughout
TC-SPI-005  CS de-assert between each byte
TC-SPI-006  LSB-first bit order
TC-SPI-007  16-bit word size
TC-SPI-008  DMA-driven burst — 1024 bytes without CPU
TC-SPI-009  MISO tie-high while TX — verify loopback
TC-SPI-010  Max frequency at 3.3V and 1.8V
TC-SPI-011  Dual SPI — two data lines simultaneously
TC-SPI-012  Quad SPI — four data lines (QSPI flash read)
```

### 5.5 UART Controller IP — Test Cases

```
TC-UART-001  8N1 transmit — 8 data, no parity, 1 stop
TC-UART-002  8E1 — even parity generation and checking
TC-UART-003  8O1 — odd parity
TC-UART-004  7-bit word size
TC-UART-005  2 stop bits
TC-UART-006  Baud rates: 9600, 115200, 921600, 4000000
TC-UART-007  RX overrun error — FIFO full, new frame arrives
TC-UART-008  Framing error — bad stop bit injected
TC-UART-009  Parity error — flipped parity bit
TC-UART-010  Break detection — RXD held low > 1 frame duration
TC-UART-011  FIFO threshold interrupt — half-full, almost-full
TC-UART-012  Flow control — RTS/CTS handshake
TC-UART-013  DMA RX — receive 1000 bytes to memory ring buffer
TC-UART-014  Auto-baud detection
```

### 5.6 USB 2.0 Controller IP — Test Cases

```
TC-USB-001  Device enumeration — SETUP stage completes
TC-USB-002  GET_DESCRIPTOR — Device, Config, Interface, Endpoint
TC-USB-003  SET_ADDRESS — device responds at new address
TC-USB-004  Bulk IN transfer — 512-byte max packet
TC-USB-005  Bulk OUT transfer
TC-USB-006  Interrupt IN endpoint — polling every 1 ms
TC-USB-007  Isochronous IN — 1 ms frame, 1023 bytes
TC-USB-008  Control transfer — class-specific request
TC-USB-009  SUSPEND / RESUME signaling
TC-USB-010  USB reset — SE0 for > 2.5 µs
TC-USB-011  CRC5 and CRC16 error injection
TC-USB-012  NAK/STALL response handling
TC-USB-013  High-speed chirp negotiation (HS handshake)
TC-USB-014  Split transaction (HS host to FS device via TT)
```

### 5.7 DDR4 / LPDDR4 Memory Controller — Test Cases

```
TC-DDR-001  Read after Write — basic functional verify
TC-DDR-002  Burst Length 8 — sequential addresses
TC-DDR-003  Wrap burst — address wraps within boundary
TC-DDR-004  Auto-precharge — write/read with auto-precharge bit
TC-DDR-005  Refresh — tREFI compliance, no data loss
TC-DDR-006  All-bank refresh vs per-bank refresh
TC-DDR-007  Self-refresh entry and exit
TC-DDR-008  Mode register programming — CL, CWL, burst settings
TC-DDR-009  ODT control — on-die termination enable/disable
TC-DDR-010  Write leveling — DQS to CLK alignment
TC-DDR-011  Read training — DQ to DQS centering
TC-DDR-012  Data bus inversion (DBI) — verify bus inversion logic
TC-DDR-013  ECC single-bit error correction
TC-DDR-014  ECC double-bit error detection
TC-DDR-015  Stress test — 1 million R/W at max frequency
```

---

## 6. C & Embedded C Proficiency

### 6.1 C for Embedded Systems — Key Concepts

#### Volatile and Memory-Mapped Registers

```c
/* WRONG — compiler may optimise away repeated reads */
uint32_t status = STATUS_REG;
while (status & STATUS_BUSY) {
    status = STATUS_REG;  /* compiler may hoist this out of loop */
}

/* CORRECT — volatile tells compiler to always load from memory */
#define CAN_BASE_ADDR   0x40020000UL
#define CAN_STATUS_REG  (*((volatile uint32_t *)(CAN_BASE_ADDR + 0x04)))

while (CAN_STATUS_REG & CAN_STATUS_BUSY_Msk) {
    /* always re-reads the hardware register */
}
```

#### Register Bit Manipulation (MISRA-safe style)

```c
#include <stdint.h>

/* CAN Control Register bit definitions */
#define CAN_CR_INIT_Pos     (0U)
#define CAN_CR_INIT_Msk     (0x1UL << CAN_CR_INIT_Pos)
#define CAN_CR_IE_Pos       (1U)
#define CAN_CR_IE_Msk       (0x1UL << CAN_CR_IE_Pos)
#define CAN_CR_SIE_Pos      (2U)
#define CAN_CR_SIE_Msk      (0x1UL << CAN_CR_SIE_Pos)
#define CAN_CR_CCE_Pos      (6U)
#define CAN_CR_CCE_Msk      (0x1UL << CAN_CR_CCE_Pos)

typedef struct {
    volatile uint32_t CR;       /*!< 0x000 Control Register */
    volatile uint32_t SR;       /*!< 0x004 Status Register */
    volatile uint32_t ECR;      /*!< 0x008 Error Counter Register */
    volatile uint32_t BTR;      /*!< 0x00C Bit Timing Register */
    volatile uint32_t TESR;     /*!< 0x010 TX Error Status Register */
    uint32_t          RESERVED[11];
    volatile uint32_t BRPE;     /*!< 0x040 Baud Rate Prescaler Extension */
} CAN_TypeDef;

#define CAN1    ((CAN_TypeDef *)0x40020000UL)

/* Set bit — use OR */
static inline void CAN_EnableInterrupt(CAN_TypeDef *can) {
    can->CR |= CAN_CR_IE_Msk;
}

/* Clear bit — use AND NOT */
static inline void CAN_DisableInterrupt(CAN_TypeDef *can) {
    can->CR &= ~CAN_CR_IE_Msk;
}

/* Read bit field */
static inline uint32_t CAN_GetTEC(CAN_TypeDef *can) {
    return (can->ECR >> 8U) & 0xFFU;   /* TEC in bits [15:8] */
}

/* Write bit field (read-modify-write) */
static inline void CAN_SetBRP(CAN_TypeDef *can, uint32_t brp) {
    uint32_t tmp = can->BTR;
    tmp &= ~(0x1FFUL);           /* clear BRP field */
    tmp |= (brp & 0x1FFUL);      /* set new value */
    can->BTR = tmp;
}
```

#### Fixed-Width Integer Types

```c
#include <stdint.h>
#include <stdbool.h>

/* Always use fixed-width types for hardware registers */
uint8_t  dlc;       /* 8-bit  — CAN DLC field */
uint16_t can_id;    /* 16-bit — standard CAN ID */
uint32_t ext_id;    /* 32-bit — extended CAN ID */
uint64_t timestamp; /* 64-bit — microsecond timestamp */

/* WRONG: int size is platform-dependent */
int      bad_id;

/* Use bool for flags (C99) */
bool is_extended = false;
bool is_remote   = false;
```

### 6.2 CAN Driver — Full Embedded C Implementation

```c
/**
 * @file    can_driver.c
 * @brief   CAN 2.0B driver for automotive SoC
 * @version 1.0
 * @date    2026-05-05
 *
 * Compliant with:
 *   - ISO 11898-1:2015
 *   - MISRA C:2012 (selected rules)
 *   - AUTOSAR Classic Platform driver interface
 */

#include "can_driver.h"
#include <string.h>   /* memcpy */
#include <assert.h>

/* ─── Private macros ────────────────────────────────────────────────────── */
#define CAN_MAX_DLC          (8U)
#define CAN_TIMEOUT_CYCLES   (100000UL)

#define CAN_SR_TXOK_Msk      (0x08UL)
#define CAN_SR_RXOK_Msk      (0x10UL)
#define CAN_SR_EPASS_Msk     (0x20UL)
#define CAN_SR_EWARN_Msk     (0x40UL)
#define CAN_SR_BOFF_Msk      (0x80UL)

/* ─── Driver state ──────────────────────────────────────────────────────── */
typedef struct {
    CAN_TypeDef         *hw;
    CAN_Config_t         cfg;
    CAN_RxCallback_t     rx_cb;
    CAN_ErrorCallback_t  err_cb;
    bool                 initialised;
} CAN_Driver_State_t;

static CAN_Driver_State_t s_drv[CAN_INSTANCE_COUNT];

/* ─── Bit timing lookup table ────────────────────────────────────────────── */
typedef struct {
    uint32_t bitrate;
    uint32_t brp;
    uint32_t tseg1;
    uint32_t tseg2;
    uint32_t sjw;
} CAN_BitTimingEntry_t;

/* Lookup for 80 MHz peripheral clock */
static const CAN_BitTimingEntry_t s_timing_table[] = {
    { 1000000UL, 1U,  7U, 2U, 1U },   /* 1 Mbit/s  */
    {  500000UL, 1U, 13U, 2U, 1U },   /* 500 kbit/s */
    {  250000UL, 2U, 13U, 2U, 1U },   /* 250 kbit/s */
    {  125000UL, 4U, 13U, 2U, 1U },   /* 125 kbit/s */
    {  100000UL, 5U, 13U, 2U, 1U },   /* 100 kbit/s */
};
#define TIMING_TABLE_SIZE  (sizeof(s_timing_table) / sizeof(s_timing_table[0]))

/* ─── Internal helpers ───────────────────────────────────────────────────── */
static CAN_Status_t can_set_init_mode(CAN_TypeDef *hw)
{
    uint32_t timeout = CAN_TIMEOUT_CYCLES;

    hw->CR |= CAN_CR_INIT_Msk;
    while (((hw->SR & CAN_SR_INIT_Msk) == 0U) && (timeout > 0U)) {
        timeout--;
    }
    return (timeout > 0U) ? CAN_STATUS_OK : CAN_STATUS_TIMEOUT;
}

static CAN_Status_t can_clear_init_mode(CAN_TypeDef *hw)
{
    uint32_t timeout = CAN_TIMEOUT_CYCLES;

    hw->CR &= ~CAN_CR_INIT_Msk;
    while (((hw->SR & CAN_SR_INIT_Msk) != 0U) && (timeout > 0U)) {
        timeout--;
    }
    return (timeout > 0U) ? CAN_STATUS_OK : CAN_STATUS_TIMEOUT;
}

static const CAN_BitTimingEntry_t *can_find_timing(uint32_t bitrate)
{
    for (uint32_t i = 0U; i < TIMING_TABLE_SIZE; i++) {
        if (s_timing_table[i].bitrate == bitrate) {
            return &s_timing_table[i];
        }
    }
    return NULL;
}

/* ─── Public API ─────────────────────────────────────────────────────────── */

/**
 * @brief  Initialise a CAN instance.
 * @param  instance  CAN instance index (0 = CAN1, 1 = CAN2, …)
 * @param  cfg       Pointer to configuration structure
 * @return CAN_STATUS_OK or error code
 */
CAN_Status_t CAN_Init(uint8_t instance, const CAN_Config_t *cfg)
{
    assert(instance < CAN_INSTANCE_COUNT);
    assert(cfg != NULL);

    CAN_Driver_State_t *drv = &s_drv[instance];
    CAN_TypeDef        *hw  = drv->hw;
    CAN_Status_t        ret;
    const CAN_BitTimingEntry_t *timing;

    /* 1. Enter initialisation mode */
    ret = can_set_init_mode(hw);
    if (ret != CAN_STATUS_OK) { return ret; }

    /* 2. Enable configuration change */
    hw->CR |= CAN_CR_CCE_Msk;

    /* 3. Configure bit timing */
    timing = can_find_timing(cfg->bitrate);
    if (timing == NULL) { return CAN_STATUS_INVALID_PARAM; }

    hw->BTR = ((timing->brp   - 1U) & 0x1FFUL)
            | (((timing->tseg1 - 1U) & 0xFUL) << 16U)
            | (((timing->tseg2 - 1U) & 0x7UL) << 20U)
            | (((timing->sjw   - 1U) & 0x3UL) << 24U);

    /* 4. Configure loopback / silent mode for testing */
    if (cfg->mode == CAN_MODE_LOOPBACK) {
        hw->BTR |= (1UL << 30U);   /* LBACK bit */
    } else if (cfg->mode == CAN_MODE_SILENT) {
        hw->BTR |= (1UL << 31U);   /* SILM bit */
    }

    /* 5. Disable CCE, leave init mode */
    hw->CR &= ~CAN_CR_CCE_Msk;
    ret = can_clear_init_mode(hw);
    if (ret != CAN_STATUS_OK) { return ret; }

    /* 6. Enable interrupts */
    hw->CR |= CAN_CR_IE_Msk | CAN_CR_SIE_Msk | CAN_CR_EIE_Msk;

    /* 7. Save configuration */
    drv->cfg         = *cfg;
    drv->initialised = true;

    return CAN_STATUS_OK;
}

/**
 * @brief  Transmit a CAN frame.
 * @param  instance  CAN instance index
 * @param  frame     Pointer to frame to transmit
 * @return CAN_STATUS_OK or error code
 */
CAN_Status_t CAN_Transmit(uint8_t instance, const CAN_Frame_t *frame)
{
    assert(instance < CAN_INSTANCE_COUNT);
    assert(frame != NULL);
    assert(frame->dlc <= CAN_MAX_DLC);

    CAN_TypeDef  *hw      = s_drv[instance].hw;
    uint32_t      timeout = CAN_TIMEOUT_CYCLES;

    /* Wait for a free TX mailbox */
    while (((hw->TSR & CAN_TSR_TME0_Msk) == 0U) && (timeout > 0U)) {
        timeout--;
    }
    if (timeout == 0U) { return CAN_STATUS_TX_BUSY; }

    /* Load mailbox 0 */
    if (frame->is_extended) {
        hw->sTxMailBox[0].TIR  = (frame->id << 3U) | CAN_TIR_EXID | CAN_TIR_IDE;
    } else {
        hw->sTxMailBox[0].TIR  = (frame->id << 21U);
    }

    /* Data Length Code */
    hw->sTxMailBox[0].TDTR = frame->dlc & 0x0FU;

    /* Data bytes — little-endian packing */
    hw->sTxMailBox[0].TDLR = ((uint32_t)frame->data[0])
                           | ((uint32_t)frame->data[1] << 8U)
                           | ((uint32_t)frame->data[2] << 16U)
                           | ((uint32_t)frame->data[3] << 24U);

    hw->sTxMailBox[0].TDHR = ((uint32_t)frame->data[4])
                           | ((uint32_t)frame->data[5] << 8U)
                           | ((uint32_t)frame->data[6] << 16U)
                           | ((uint32_t)frame->data[7] << 24U);

    /* Request transmission */
    hw->sTxMailBox[0].TIR |= CAN_TIR_TXRQ;

    return CAN_STATUS_OK;
}

/**
 * @brief  Receive a CAN frame from FIFO0.
 * @param  instance  CAN instance index
 * @param  frame     Output buffer
 * @param  timeout   Timeout in microseconds
 * @return CAN_STATUS_OK or CAN_STATUS_TIMEOUT
 */
CAN_Status_t CAN_Receive(uint8_t instance, CAN_Frame_t *frame, uint32_t timeout_us)
{
    assert(instance < CAN_INSTANCE_COUNT);
    assert(frame != NULL);

    CAN_TypeDef *hw = s_drv[instance].hw;
    uint32_t     deadline = CAN_GetTick_us() + timeout_us;

    /* Wait until FIFO0 has a message pending */
    while ((hw->RF0R & CAN_RF0R_FMP0_Msk) == 0U) {
        if (CAN_GetTick_us() >= deadline) {
            return CAN_STATUS_TIMEOUT;
        }
    }

    /* Extract frame */
    uint32_t rir = hw->sFIFOMailBox[0].RIR;

    if ((rir & CAN_RIR_IDE_Msk) != 0U) {
        frame->id          = (rir >> 3U) & 0x1FFFFFFFUL;
        frame->is_extended = true;
    } else {
        frame->id          = (rir >> 21U) & 0x7FFUL;
        frame->is_extended = false;
    }

    frame->is_remote   = ((rir & CAN_RIR_RTR_Msk) != 0U);
    frame->dlc         = hw->sFIFOMailBox[0].RDTR & 0x0FU;
    frame->timestamp   = (hw->sFIFOMailBox[0].RDTR >> 16U) & 0xFFFFU;

    uint32_t rdlr = hw->sFIFOMailBox[0].RDLR;
    uint32_t rdhr = hw->sFIFOMailBox[0].RDHR;

    frame->data[0] = (uint8_t)((rdlr >>  0U) & 0xFFU);
    frame->data[1] = (uint8_t)((rdlr >>  8U) & 0xFFU);
    frame->data[2] = (uint8_t)((rdlr >> 16U) & 0xFFU);
    frame->data[3] = (uint8_t)((rdlr >> 24U) & 0xFFU);
    frame->data[4] = (uint8_t)((rdhr >>  0U) & 0xFFU);
    frame->data[5] = (uint8_t)((rdhr >>  8U) & 0xFFU);
    frame->data[6] = (uint8_t)((rdhr >> 16U) & 0xFFU);
    frame->data[7] = (uint8_t)((rdhr >> 24U) & 0xFFU);

    /* Release FIFO */
    hw->RF0R |= CAN_RF0R_RFOM0_Msk;

    return CAN_STATUS_OK;
}
```

### 6.3 CAN Driver Header File

```c
/**
 * @file    can_driver.h
 * @brief   CAN 2.0B Driver Public API
 */

#ifndef CAN_DRIVER_H
#define CAN_DRIVER_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ─── Constants ─────────────────────────────────────────────────────────── */
#define CAN_INSTANCE_COUNT   (2U)
#define CAN_MAX_DATA_LEN     (8U)

/* ─── Enumerations ───────────────────────────────────────────────────────── */
typedef enum {
    CAN_STATUS_OK            = 0,
    CAN_STATUS_TIMEOUT       = 1,
    CAN_STATUS_TX_BUSY       = 2,
    CAN_STATUS_RX_EMPTY      = 3,
    CAN_STATUS_BUS_OFF       = 4,
    CAN_STATUS_INVALID_PARAM = 5,
    CAN_STATUS_ERROR         = 6
} CAN_Status_t;

typedef enum {
    CAN_MODE_NORMAL   = 0,
    CAN_MODE_LOOPBACK = 1,
    CAN_MODE_SILENT   = 2,
    CAN_MODE_COMBINED = 3   /* loopback + silent (test mode) */
} CAN_Mode_t;

typedef enum {
    CAN_BITRATE_1M   = 1000000UL,
    CAN_BITRATE_500K =  500000UL,
    CAN_BITRATE_250K =  250000UL,
    CAN_BITRATE_125K =  125000UL,
    CAN_BITRATE_100K =  100000UL
} CAN_Bitrate_t;

/* ─── Data structures ────────────────────────────────────────────────────── */
typedef struct {
    uint32_t id;
    uint8_t  data[CAN_MAX_DATA_LEN];
    uint8_t  dlc;
    bool     is_extended;
    bool     is_remote;
    uint16_t timestamp;     /* free-running timer value */
} CAN_Frame_t;

typedef struct {
    CAN_Bitrate_t bitrate;
    CAN_Mode_t    mode;
    bool          auto_recovery;  /* auto bus-off recovery */
    bool          ttcm;           /* time-triggered communication */
} CAN_Config_t;

/* ─── Callback typedefs ──────────────────────────────────────────────────── */
typedef void (*CAN_RxCallback_t)   (uint8_t instance, const CAN_Frame_t *frame);
typedef void (*CAN_ErrorCallback_t)(uint8_t instance, uint32_t error_flags);

/* ─── Public API ─────────────────────────────────────────────────────────── */
CAN_Status_t CAN_Init      (uint8_t instance, const CAN_Config_t *cfg);
CAN_Status_t CAN_DeInit    (uint8_t instance);
CAN_Status_t CAN_Transmit  (uint8_t instance, const CAN_Frame_t *frame);
CAN_Status_t CAN_Receive   (uint8_t instance, CAN_Frame_t *frame, uint32_t timeout_us);
CAN_Status_t CAN_SetFilter (uint8_t instance, uint32_t id, uint32_t mask, bool extended);
CAN_Status_t CAN_RegisterRxCallback  (uint8_t instance, CAN_RxCallback_t  cb);
CAN_Status_t CAN_RegisterErrCallback (uint8_t instance, CAN_ErrorCallback_t cb);
uint8_t      CAN_GetTEC    (uint8_t instance);
uint8_t      CAN_GetREC    (uint8_t instance);
bool         CAN_IsBusOff  (uint8_t instance);
void         CAN_IRQHandler(uint8_t instance);  /* call from interrupt vector */

#ifdef __cplusplus
}
#endif

#endif /* CAN_DRIVER_H */
```

### 6.4 Unit Test for CAN Driver (Unity Framework)

```c
/**
 * @file    test_can_driver.c
 * @brief   Unit tests for CAN driver using Unity test framework
 * @note    Runs on host with hardware register stubs
 */

#include "unity.h"
#include "can_driver.h"
#include "mock_can_hw.h"   /* Software model of hardware registers */

/* ─── Test fixtures ──────────────────────────────────────────────────────── */
static CAN_Config_t g_default_cfg = {
    .bitrate       = CAN_BITRATE_500K,
    .mode          = CAN_MODE_LOOPBACK,
    .auto_recovery = true,
    .ttcm          = false
};

void setUp(void) {
    mock_can_hw_reset(0U);           /* reset all hardware registers to POR state */
    mock_can_hw_reset(1U);
}

void tearDown(void) { /* nothing */ }

/* ─── Test cases ─────────────────────────────────────────────────────────── */
void test_init_returns_ok_with_valid_config(void) {
    CAN_Status_t ret = CAN_Init(0U, &g_default_cfg);
    TEST_ASSERT_EQUAL(CAN_STATUS_OK, ret);
}

void test_init_fails_on_invalid_bitrate(void) {
    CAN_Config_t bad_cfg = g_default_cfg;
    bad_cfg.bitrate = 99999UL;
    CAN_Status_t ret = CAN_Init(0U, &bad_cfg);
    TEST_ASSERT_EQUAL(CAN_STATUS_INVALID_PARAM, ret);
}

void test_transmit_standard_frame(void) {
    CAN_Init(0U, &g_default_cfg);

    CAN_Frame_t tx = {
        .id          = 0x123U,
        .data        = {0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0x00, 0x00, 0x00},
        .dlc         = 4U,
        .is_extended = false,
        .is_remote   = false,
    };

    CAN_Status_t ret = CAN_Transmit(0U, &tx);
    TEST_ASSERT_EQUAL(CAN_STATUS_OK, ret);

    /* In loopback mode, the frame should appear in RX FIFO */
    CAN_Frame_t rx;
    ret = CAN_Receive(0U, &rx, 1000U);
    TEST_ASSERT_EQUAL(CAN_STATUS_OK, ret);
    TEST_ASSERT_EQUAL_UINT32(tx.id, rx.id);
    TEST_ASSERT_EQUAL_UINT8(tx.dlc, rx.dlc);
    TEST_ASSERT_EQUAL_UINT8_ARRAY(tx.data, rx.data, tx.dlc);
}

void test_transmit_extended_frame(void) {
    CAN_Init(0U, &g_default_cfg);

    CAN_Frame_t tx = {
        .id          = 0x1ABCDEF0UL,
        .data        = {0xFF},
        .dlc         = 1U,
        .is_extended = true,
        .is_remote   = false,
    };

    TEST_ASSERT_EQUAL(CAN_STATUS_OK, CAN_Transmit(0U, &tx));

    CAN_Frame_t rx;
    TEST_ASSERT_EQUAL(CAN_STATUS_OK, CAN_Receive(0U, &rx, 1000U));
    TEST_ASSERT_TRUE(rx.is_extended);
    TEST_ASSERT_EQUAL_UINT32(tx.id, rx.id);
}

void test_receive_timeout_returns_timeout_status(void) {
    CAN_Init(0U, &g_default_cfg);
    /* Do NOT inject any frame — RX FIFO stays empty */
    CAN_Frame_t rx;
    CAN_Status_t ret = CAN_Receive(0U, &rx, 100U);   /* 100 µs timeout */
    TEST_ASSERT_EQUAL(CAN_STATUS_TIMEOUT, ret);
}

void test_tec_increments_on_bus_off(void) {
    CAN_Init(0U, &g_default_cfg);
    mock_can_hw_inject_bus_off(0U);   /* simulate 128 consecutive errors */
    TEST_ASSERT_TRUE(CAN_IsBusOff(0U));
}

void test_filter_rejects_non_matching_id(void) {
    CAN_Init(0U, &g_default_cfg);
    CAN_SetFilter(0U, 0x200U, 0x7FFU, false);  /* accept only 0x200 */

    CAN_Frame_t tx = { .id = 0x123U, .dlc = 1U, .data = {0xAA} };
    CAN_Transmit(0U, &tx);   /* loopback — but filter should reject */

    CAN_Frame_t rx;
    CAN_Status_t ret = CAN_Receive(0U, &rx, 100U);
    TEST_ASSERT_EQUAL(CAN_STATUS_TIMEOUT, ret);  /* filtered out */
}

/* ─── Runner ─────────────────────────────────────────────────────────────── */
int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_init_returns_ok_with_valid_config);
    RUN_TEST(test_init_fails_on_invalid_bitrate);
    RUN_TEST(test_transmit_standard_frame);
    RUN_TEST(test_transmit_extended_frame);
    RUN_TEST(test_receive_timeout_returns_timeout_status);
    RUN_TEST(test_tec_increments_on_bus_off);
    RUN_TEST(test_filter_rejects_non_matching_id);
    return UNITY_END();
}
```

### 6.5 MISRA C:2012 — Key Rules for Embedded C

| Rule | Description | Example Violation → Fix |
|---|---|---|
| R.1.1 | All code shall be C99 or C11 conforming | Non-standard GCC extensions |
| R.2.1 | Unreachable code | `if (0) { ... }` → remove |
| R.3.2 | Side effects in dead code | `x = func()` in dead branch |
| R.7.2 | Use `u` suffix for unsigned constants | `0xFF` → `0xFFU` |
| R.10.1 | No arithmetic on bool | `if (flag + 1)` → `if (flag)` |
| R.10.4 | Both operands same essential type | `uint8 + int32` → cast explicitly |
| R.11.3 | No cast from integer to pointer | `(int*)0x40000000` → use `volatile uint32_t *` |
| R.12.1 | Use parentheses for precedence clarity | `a + b << 2` → `a + (b << 2)` |
| R.13.2 | No increment in complex expressions | `arr[i++] = arr[i]` → separate stmts |
| R.14.4 | `if` condition shall be boolean | `if (ptr)` → `if (ptr != NULL)` |
| R.15.5 | Single `return` per function | Multiple returns → single exit |
| R.17.7 | Return value of non-void functions must be used | `memcpy(...)` → cast to `(void)memcpy(...)` |
| R.21.3 | No dynamic memory allocation | No `malloc/free` in production code |

---

## 7. Project Structure — Reference Implementation

### 7.1 Embedded C IP Driver Project

```
can_driver_ip/
├── README.md                       ← Project overview
├── CMakeLists.txt                  ← CMake build (host + target)
├── docs/
│   ├── architecture.md             ← Driver architecture
│   ├── api_reference.md            ← Public API documentation
│   ├── test_plan.md                ← Test plan document
│   └── register_map.xlsx           ← IP register map
├── include/
│   ├── can_driver.h                ← Public API header
│   ├── can_driver_types.h          ← Enums and structs
│   └── can_hw.h                    ← Hardware register definitions
├── src/
│   ├── can_driver.c                ← Driver implementation
│   ├── can_driver_irq.c            ← Interrupt handlers
│   └── can_driver_filter.c         ← Acceptance filter logic
├── tests/
│   ├── unit/
│   │   ├── CMakeLists.txt
│   │   ├── mock_can_hw.h           ← Hardware register mock
│   │   ├── mock_can_hw.c
│   │   └── test_can_driver.c       ← Unity test cases
│   ├── integration/
│   │   └── test_can_loopback.c     ← On-target loopback test
│   └── system/
│       └── test_can_bus_stress.c   ← Multi-frame stress test
├── tools/
│   ├── trace_parser.py             ← Parse CAN trace logs
│   └── bitrate_calc.py             ← Bit timing calculator
└── .github/
    └── workflows/
        └── ci.yml                  ← Build + unit test on push
```

### 7.2 CMakeLists.txt for Host Unit Tests

```cmake
cmake_minimum_required(VERSION 3.20)
project(can_driver_tests C)

set(CMAKE_C_STANDARD 11)

# Unity test framework (fetched automatically)
include(FetchContent)
FetchContent_Declare(
    unity
    GIT_REPOSITORY https://github.com/ThrowTheSwitch/Unity.git
    GIT_TAG        v2.5.2
)
FetchContent_MakeAvailable(unity)

# Driver library (compiled for host — no hardware dependency)
add_library(can_driver_lib
    src/can_driver.c
    src/can_driver_irq.c
    src/can_driver_filter.c
)
target_include_directories(can_driver_lib PUBLIC include)
target_compile_definitions(can_driver_lib PRIVATE CAN_HOST_TEST=1)

# Unit test executable
add_executable(test_can_driver
    tests/unit/test_can_driver.c
    tests/unit/mock_can_hw.c
)
target_link_libraries(test_can_driver
    can_driver_lib
    unity
)
target_include_directories(test_can_driver PRIVATE tests/unit include)

enable_testing()
add_test(NAME CAN_Unit_Tests COMMAND test_can_driver)
```

---

## 8. Requirements Engineering for Embedded Projects

### 8.1 Requirement Levels

```
Customer Requirements (L1)
         │
         ▼
System Requirements (L2)    ← What the system shall do
         │
         ▼
Software Requirements (L3)  ← What the SW module shall do (SWS)
         │
         ▼
Software Architecture (L4)  ← How it is structured
         │
         ▼
Software Detailed Design (L5) ← How each function works
         │
         ▼
Source Code
         │
         ▼
Test Cases (trace back to L2/L3 requirements)
```

### 8.2 CAN Driver — Requirement Specification

```
Document  : CAN Driver Software Requirements Specification
Doc ID    : SRS-CAN-DRV-001
Version   : 1.2
Status    : Approved
Date      : 2026-05-05

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ID          │ Requirement Text                        │ Priority
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQ-CAN-001 │ The driver shall support CAN 2.0A (11-  │ M
            │ bit ID) and CAN 2.0B (29-bit ID).       │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQ-CAN-002 │ The driver shall support bit rates of   │ M
            │ 100k, 125k, 250k, 500k, 1000k bit/s.   │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQ-CAN-003 │ CAN_Transmit() shall complete within    │ M
            │ one CAN frame period + 10 µs margin.   │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQ-CAN-004 │ CAN_Receive() shall return              │ M
            │ CAN_STATUS_TIMEOUT if no frame arrives  │
            │ within the specified timeout period.   │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQ-CAN-005 │ The driver shall increment TEC by 8 for │ M
            │ each transmitted error frame.           │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQ-CAN-006 │ The driver shall enter bus-off state    │ M
            │ when TEC > 255 per ISO 11898-1.        │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQ-CAN-007 │ When auto_recovery is enabled, the      │ M
            │ driver shall automatically recover from  │
            │ bus-off after 128 × 11 recessive bits. │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQ-CAN-008 │ The driver shall support up to 14       │ M
            │ acceptance filter banks (ID mask mode). │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQ-CAN-009 │ Interrupt latency from frame complete   │ S
            │ to callback invocation shall be < 5 µs  │
            │ at 168 MHz core clock.                 │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQ-CAN-010 │ The driver shall comply with            │ M
            │ MISRA C:2012 Rules (all mandatory +     │
            │ required rules applicable).            │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQ-CAN-011 │ CAN_Init() shall be re-entrant: calling │ M
            │ it twice without DeInit shall return   │
            │ an error, not corrupt state.           │
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Priority key: M = Mandatory, S = Should, C = Could
```

### 8.3 Requirements-to-Test Traceability Matrix

```
╔══════════════╦═════════════════════════════════════════════════╦══════════════╗
║ Requirement  ║ Test Case(s)                                    ║ Status       ║
╠══════════════╬═════════════════════════════════════════════════╬══════════════╣
║ REQ-CAN-001  ║ TC-CAN-001, TC-CAN-002, TC-CAN-003             ║ Covered      ║
║ REQ-CAN-002  ║ TC-CAN-BTR-001 to TC-CAN-BTR-005               ║ Covered      ║
║ REQ-CAN-003  ║ TC-CAN-TIMING-001 (timing measurement test)    ║ Covered      ║
║ REQ-CAN-004  ║ test_receive_timeout_returns_timeout_status     ║ Covered      ║
║ REQ-CAN-005  ║ TC-CAN-011 (TEC increment on TX error)         ║ Covered      ║
║ REQ-CAN-006  ║ TC-CAN-013 (bus-off entry)                     ║ Covered      ║
║ REQ-CAN-007  ║ TC-CAN-014 (bus-off recovery)                  ║ Covered      ║
║ REQ-CAN-008  ║ test_filter_rejects_non_matching_id            ║ Covered      ║
║ REQ-CAN-009  ║ TC-CAN-IRQ-001 (interrupt latency)             ║ Pending HW   ║
║ REQ-CAN-010  ║ MISRA static analysis (SpyGlass)               ║ Covered      ║
║ REQ-CAN-011  ║ TC-CAN-INIT-003 (double-init test)             ║ Covered      ║
╚══════════════╩═════════════════════════════════════════════════╩══════════════╝
```

---

## 9. End-to-End Workflow Example — CAN Controller IP

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WEEK 1–2 : Spec study & test plan                                          │
│    Read ISO 11898-1, IP datasheet, register map                             │
│    Write TP-CAN-001 (test plan)                                             │
│    Write SRS-CAN-DRV-001 (requirements)                                     │
│    Review with design and architecture teams                                │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│  WEEK 3–4 : Pre-silicon simulation (UVM)                                    │
│    Build UVM test bench with CAN VIP                                        │
│    Write directed test cases for F1-F8                                     │
│    Run constrained-random sequences                                         │
│    Close code coverage to 95%+                                              │
│    Log bugs in JIRA, regression clean                                       │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│  WEEK 5–6 : Emulation bring-up                                              │
│    Compile RTL to Palladium Z1                                              │
│    Connect real CAN transceiver via ICE cable                               │
│    Run Linux CAN driver (socketcan) on emulated ARM core                   │
│    Verify candump / cansend traffic                                         │
│    Run regression suite on emulator (1000× faster than sim)                │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│  WEEK 7–8 : Embedded C driver development                                   │
│    Write can_driver.c / can_driver.h against register map                  │
│    Unit tests using Unity framework on host (CI via GitHub Actions)        │
│    Integration tests on FPGA prototype board                               │
│    MISRA analysis with SpyGlass                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│  WEEK 9–14 : Post-silicon bring-up                                          │
│    Power on ES0 chip, verify JTAG                                           │
│    Run CAN loopback test (internal + external with Vector VN1610)          │
│    Capture CAN bus eye diagram on scope                                     │
│    Run ISO 11898-1 compliance suite in CANoe                               │
│    Temperature characterisation −40°C / 105°C                              │
│    Close P1/P2 bugs, sign-off report                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Glossary

| Term | Meaning |
|---|---|
| ABV | Assertion-Based Verification |
| AEC-Q100 | Automotive reliability qualification standard for ICs |
| ATE | Automatic Test Equipment |
| BRS | Bit Rate Switch (CAN-FD) |
| CDV | Coverage-Driven Verification |
| CDC | Clock Domain Crossing |
| DAP | Debug Access Port (ARM CoreSight) |
| DBI | Data Bus Inversion (LPDDR) |
| DLC | Data Length Code (CAN) |
| DVT | Design Verification Test |
| ECR | Error Counter Register |
| ES0 | Engineering Sample revision 0 (first silicon) |
| FD | Flexible Data-rate (CAN-FD) |
| FIFO | First-In First-Out buffer |
| FSM | Finite State Machine |
| FPGA | Field-Programmable Gate Array |
| ICE | In-Circuit Emulation |
| MBIST | Memory Built-In Self-Test |
| MISRA | Motor Industry Software Reliability Association |
| NRC | Negative Response Code (UDS) |
| POR | Power-On Reset |
| PVT | Process, Voltage, Temperature corners |
| RDC | Reset Domain Crossing |
| REC | Receive Error Counter (CAN) |
| RTL | Register Transfer Level |
| SCE-MI | Standard Co-Emulation Modeling Interface |
| SoC | System on Chip |
| STA | Static Timing Analysis |
| SVA | SystemVerilog Assertions |
| TEC | Transmit Error Counter (CAN) |
| TLM | Transaction-Level Modelling |
| UVM | Universal Verification Methodology |
| VIP | Verification Intellectual Property |

---

*Document generated: 2026-05-05 | Revision: 1.0 | Author: Silicon Validation & Embedded Systems Engineering*
