# 05 — ConfigurationDesk Basics

> **Tool**: dSPACE ConfigurationDesk  
> **Prerequisites**: SCALEXIO Architecture (04)  
> **Outcome**: Configure hardware I/O, import Simulink model, build & download to SCALEXIO

---

## 1. What Is ConfigurationDesk?

ConfigurationDesk is dSPACE's **hardware configuration IDE**. It bridges the gap between:
- Your Simulink model (algorithms + signals)
- Your SCALEXIO hardware (physical I/O boards)

```
Workflow:
───────────────────────────────────────────────────────────────
Simulink Model  →  ConfigurationDesk  →  SCALEXIO Hardware
(.slx)             (.cdx project)         (DS6001 + I/O boards)

Tasks in ConfigurationDesk:
  1. Create application (link Simulink model)
  2. Configure I/O boards (which boards, which channels)
  3. Map Simulink signals ↔ physical I/O channels
  4. Configure buses (CAN, LIN, Ethernet)
  5. Set task rates (1 ms, 10 ms)
  6. Build → Deploy to SCALEXIO
───────────────────────────────────────────────────────────────
```

---

## 2. ConfigurationDesk Project Structure

```
ConfigurationDesk Project (.cdx):
───────────────────────────────────────────────────
Project
├── Applications
│   └── ADAS_HIL_App
│       ├── Simulink Model reference
│       │   └── AEB_HIL_Model.slx
│       ├── Task Configuration
│       │   ├── BaseRate: 1 ms
│       │   └── SubRate:  10 ms
│       └── Variable Access (XCP)
├── Platform Configuration
│   └── SCALEXIO
│       ├── DS6001 (Processor)
│       ├── DS1552 (CAN FD) — 8 channels
│       ├── DS4330 (Ethernet) — 4 channels
│       ├── DS2211 (Analog I/O)
│       └── DS2680 (Digital I/O)
└── Signal Mapping
    ├── Analog Inputs / Outputs
    ├── Digital I/O
    ├── CAN Bus Configuration
    └── Ethernet Configuration
───────────────────────────────────────────────────
```

---

## 3. Step-by-Step: ConfigurationDesk Workflow

### Step 1 — Create New Project
```
File → New → ConfigurationDesk Project
  Project Name: ADAS_ECU_HIL
  Platform:     SCALEXIO
  Path:         C:\HIL_Projects\ADAS_ECU_HIL\
```

### Step 2 — Discover Hardware
```
Platform → Scan for Hardware
  ↳ ConfigurationDesk scans IOCNET
  ↳ Detected boards appear in Platform tree:
      ✓ DS6001-x (serial: 1234)
      ✓ DS1552 (serial: 5678) — 8 CAN FD channels
      ✓ DS2211 (serial: 9012) — 16 AI, 8 AO
```

### Step 3 — Import Simulink Model
```
Application → New Application
  Simulink Model: Browse to AEB_HIL_Model.slx
  
  ConfigurationDesk reads:
    - Inport blocks → become "inputs to model" (stimulus)
    - Outport blocks → become "outputs from model" (measurement)
    - Goto/From labels → internal signals
```

### Step 4 — Task Rate Configuration
```
Application → Task Configuration

BaseRate Task:
  Period: 1.0 ms    ← Must match Simulink fixed-step solver
  Priority: High
  Trigger: IOCNET sync (hardware timer)

SubRate Task:
  Period: 10.0 ms
  Priority: Medium
  Triggered by: BaseRate (every 10th tick)
```

### Step 5 — Signal Mapping
```
I/O Mapping view:
  Application Signal         →   Hardware Channel
  ─────────────────────────────────────────────────
  AEB_Model/Radar_Dist_In    → DS2211 AI Channel 1  (0-5V → 0-250m)
  AEB_Model/BrakeCmd_Out     → DS2211 AO Channel 1  (0-10V → 0-100 bar)
  AEB_Model/IgnitionSim_Out  → DS2680 DI Channel 3  (3.3V logic)
  AEB_Model/CAN_Rx_Frame     → DS1552 CAN1           (via DBC)
```

---

## 4. CAN Bus Configuration in ConfigurationDesk

```
CAN Configuration steps:
─────────────────────────────────────────────────────────────
1. Select DS1552 board → CAN Channel 1
2. Set baud rate: 500 kbit/s (nominal), 2 Mbit/s (data)
3. Import DBC file: Vehicle_Network.dbc
4. ConfigurationDesk auto-generates:
   - Tx frames (signals the HIL sends to ECU)
   - Rx frames (signals the HIL receives from ECU)
5. Map DBC signals to application signals:
   AEB_BrakeCommand → AEB_Model/BrakeCmd_CAN_Out
   Radar_ObjectList  → AEB_Model/Radar_CAN_In
─────────────────────────────────────────────────────────────
```

### CAN Configuration Parameters
| Parameter | Value | Description |
|-----------|-------|-------------|
| Baud rate nominal | 500 kbit/s | Arbitration phase |
| Baud rate data | 2000 kbit/s | Data phase (CAN FD) |
| Termination | 120 Ω | On-board termination |
| Bus mode | Active | Normal operation |
| Error handling | Passive | Log errors, don't disconnect |
| Tx delay | 0 µs | Immediate transmission |

---

## 5. Building and Downloading

```
Build process:
────────────────────────────────────────────────────
Build → Build All
  Step 1: Validate configuration (no missing mappings)
  Step 2: Generate real-time code (RTI = Real-Time Interface)
  Step 3: Compile with dSPACE GCC toolchain
  Step 4: Link application image (.sdf file)
  
Download process:
  Platform → Download to Target
  Step 1: Transfer .sdf file to DS6001 over Ethernet
  Step 2: DS6001 loads application into RAM
  Step 3: Application starts automatically
  Step 4: ControlDesk connects for monitoring
────────────────────────────────────────────────────

.sdf = dSPACE System Description File
  Contains: executable code + variable map for XCP access
```

---

## 6. Common ConfigurationDesk Errors

| Error | Meaning | Fix |
|-------|---------|-----|
| `Unconnected outport: BrakeCmd` | Simulink outport not mapped to any I/O | Map it to DAC or mark as "not connected (monitoring only)" |
| `Sample time mismatch: 0.001 vs 0.002` | Simulink model has different step than task config | Match Simulink Fixed-Step to ConfigurationDesk BaseRate |
| `Board not found: DS1552` | Hardware not detected on IOCNET | Check power, IOCNET cable, board seating |
| `DBC signal not found: AEB_BrakeCmd` | DBC file version mismatch | Reimport updated DBC |
| `Overrun detected during download` | Model too big for configured task period | Increase period or optimize model |

---

## 7. ConfigurationDesk vs ControlDesk — Know the Difference

```
ConfigurationDesk:
  ← Used BEFORE running the test
  ← Hardware setup, signal mapping, build
  ← Engineers change this rarely (once per project setup)
  ← Produces: .sdf application image

ControlDesk:
  ← Used DURING and AFTER running the test
  ← Monitor signals, calibrate parameters, log data
  ← Engineers use this daily
  ← Connects to running .sdf application via XCP
```

---

## 8. Interview Q&A

**Q1: What does ConfigurationDesk do?**  
ConfigurationDesk configures the dSPACE hardware: it imports the Simulink model, discovers connected I/O boards, maps model signals to physical I/O channels (CAN, analog, digital, Ethernet), sets task rates, then builds and downloads the real-time application to SCALEXIO.

**Q2: What is an .sdf file?**  
An SDF (System Description File) is the compiled real-time application package produced by ConfigurationDesk. It contains the executable code and a variable descriptor that tells ControlDesk/AutomationDesk the address and data type of every accessible variable for XCP measurement and calibration.

**Q3: What happens if a Simulink outport has no I/O mapping in ConfigurationDesk?**  
ConfigurationDesk flags it as an error during validation. You must either map it to a physical I/O channel or mark it as a "monitoring only" variable (accessible via XCP in ControlDesk but not driving any hardware output).

**Q4: How do you add a second CAN bus to an existing ConfigurationDesk project?**  
In the Platform tree, select the DS1552 board → right-click Channel 2 → Add CAN Configuration. Set baud rate, import the relevant DBC file, then map the new DBC signals to the Simulink model's corresponding inports/outports. Rebuild and redeploy.

**Q5: Why must the Simulink solver step size match the ConfigurationDesk BaseRate?**  
The SCALEXIO hardware timer fires every BaseRate period (e.g., 1 ms) and triggers the model step function. If the model was compiled for a 2 ms step but the hardware triggers every 1 ms, the model runs twice as fast as designed, producing wrong results. ConfigurationDesk enforces this match during build validation.
