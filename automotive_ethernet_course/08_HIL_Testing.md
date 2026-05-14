# SECTION 8 — HIL TESTING
## Course: Automotive Ethernet Testing — Complete Industry Training

---

## 8.1 MIL vs SIL vs HIL vs VIL

### Testing Levels in the V-Model

```
┌──────────────────────────────────────────────────────────────────────┐
│              AUTOMOTIVE TESTING LEVELS                               │
├─────────────────────────────────────────────────────────────────────-┤
│  MIL — Model In the Loop                                            │
│  ├── Platform: MATLAB/Simulink (desktop PC)                         │
│  ├── What runs: Algorithm model ONLY (Simulink model)               │
│  ├── SW under test: None (model verification)                       │
│  ├── Speed: Faster than real-time                                   │
│  ├── Use: Verify algorithm correctness early                        │
│  └── Cost: Very low (PC only)                                       │
├─────────────────────────────────────────────────────────────────────-┤
│  SIL — Software In the Loop                                         │
│  ├── Platform: Desktop PC or virtual machine                        │
│  ├── What runs: Compiled ECU software (cross-compiled for x86)      │
│  ├── SW under test: Application + BSW (no HW dependency)           │
│  ├── Speed: Real-time or slower                                     │
│  ├── Use: Validate software logic before hardware is ready          │
│  └── Tools: Vector VEOS, MATLAB SIL mode, dSPACE VEOS              │
├─────────────────────────────────────────────────────────────────────-┤
│  HIL — Hardware In the Loop                                         │
│  ├── Platform: dSPACE SCALEXIO, ETAS LABCAR, NI VeriStand          │
│  ├── What runs: Real ECU hardware + real firmware                   │
│  ├── HW under test: Actual production-intent ECU                   │
│  ├── Speed: Exactly real-time                                       │
│  ├── Use: Full ECU functional validation, fault injection           │
│  └── Cost: High (HIL rack = $100K–$500K)                           │
├─────────────────────────────────────────────────────────────────────-┤
│  VIL — Vehicle In the Loop                                          │
│  ├── Platform: Real vehicle + simulated environment                 │
│  ├── What runs: Real vehicle on chassis dynamometer                 │
│  ├── Environment: Virtual road (CarMaker, IPG, PreScan)            │
│  ├── Speed: Real-time                                               │
│  ├── Use: System-level validation, NCAP scenarios                  │
│  └── Cost: Very high (vehicle + dyno + sim = $1M+)                 │
└─────────────────────────────────────────────────────────────────────-┘
```

---

## 8.2 dSPACE ARCHITECTURE

### dSPACE Product Lineup

```
dSPACE PRODUCT FAMILY FOR AUTOMOTIVE HIL:
┌─────────────────────────────────────────────────────────────────┐
│  SCALEXIO (Flagship HIL System — 2012+)                         │
│  ├── Real-time processor: Intel Xeon + FPGA                     │
│  ├── I/O: Ethernet, CAN FD, LIN, flexbox modules               │
│  ├── Eth module: Supports 100BASE-T1, 1000BASE-T1               │
│  ├── Sync: IEEE 1588 (PTP) for multi-rack sync                  │
│  └── Software: ControlDesk + ConfigurationDesk                  │
├─────────────────────────────────────────────────────────────────┤
│  MicroLabBox (Compact HIL / Rapid Prototyping)                  │
│  ├── Processor: 4-core Intel + 4× FPGAs                         │
│  ├── I/O: 200+ channels (analog, digital, CAN, LIN)            │
│  ├── Form factor: Shoebox size                                  │
│  └── Use: Rapid prototyping, small ECU HIL                      │
├─────────────────────────────────────────────────────────────────┤
│  AUTERA AutoBox (Autonomous Driving HIL)                        │
│  ├── HPC: NVIDIA Jetson TX2 + Intel Xeon                       │
│  ├── Sensors: Camera, LiDAR, RADAR simulation interfaces        │
│  ├── Eth: 1000BASE-T1, 10GBASE-T1                              │
│  └── Use: ADAS / AD domain controller validation                │
├─────────────────────────────────────────────────────────────────┤
│  VEOS (Virtual ECU OS — SIL tool)                               │
│  ├── PC-based (no dedicated hardware)                           │
│  ├── Runs AUTOSAR BSW + Application SW on PC                   │
│  ├── Virtual CAN, LIN, Ethernet interfaces                      │
│  └── CANoe integration for full bus simulation                  │
└─────────────────────────────────────────────────────────────────┘
```

### dSPACE SCALEXIO Architecture

```
SCALEXIO HIL RACK — INTERNAL ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────┐
│  SCALEXIO Processing Unit                                        │
│  ├── Host PC (ControlDesk + MATLAB/Simulink)                    │
│  │   ├── Model: CarMaker/Simulink vehicle model                 │
│  │   ├── I/O mapping: Signal ↔ Physical pin                    │
│  │   └── Test automation: Python/CAPL scripts                   │
│  │                                                              │
│  └── SCALEXIO Real-Time CPU (DS6001 processor board)           │
│      ├── Intel Core i7 @3.2GHz (6 cores)                       │
│      ├── 32 GB RAM                                              │
│      ├── Real-time OS: dSPACE RTOS (guaranteed < 1µs jitter)   │
│      └── FPGA I/O processing (sub-microsecond response)        │
│                                                                  │
│  SCALEXIO I/O MODULES:                                          │
│  ├── DS1552: 100BASE-T1 / 1000BASE-T1 Ethernet module          │
│  ├── DS4330: CAN FD module (4 channels)                         │
│  ├── DS4340: LIN module (4 channels)                            │
│  ├── DS2655: Analog I/O module (32 ADC + 8 DAC channels)       │
│  ├── DS4341: GPIO + PWM module                                  │
│  └── DS6601: Load board (resistor/relay load simulation)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8.3 HIL TEST BENCH SETUP FOR AUTOMOTIVE ETHERNET

### ADAS ECU HIL Test Bench Architecture

```
ADAS ECU HIL BENCH:
┌──────────────────────────────────────────────────────────────────┐
│  HOST PC (Engineering Workstation)                               │
│  ├── ControlDesk 7.x (dSPACE GUI)                               │
│  ├── MATLAB/Simulink R2024b (vehicle model)                     │
│  ├── CarMaker 12.x (traffic/road scenarios)                     │
│  ├── CANoe 15.x (bus monitoring + diagnostics)                  │
│  └── Python 3.11 (test automation scripts)                      │
│                     │ PCIe / Ethernet                           │
│                     ▼                                           │
│  SCALEXIO REAL-TIME UNIT                                        │
│  ├── Vehicle model running at 1kHz:                             │
│  │   ├── Ego vehicle dynamics (speed, yaw rate, steering)      │
│  │   ├── Sensor models (RADAR, camera, USS field simulation)   │
│  │   └── Traffic objects (other vehicles, pedestrians)         │
│  │                                                              │
│  └── I/O MODULES:                                              │
│      ├── DS1552 Eth ───── 100BASE-T1 ──────► ADAS ECU (DUT)   │
│      ├── DS4330 CAN ───── CAN FD ──────────► ADAS ECU (DUT)   │
│      ├── DS2655 ADC ────── Power supply monitoring             │
│      ├── DS2655 DAC ────── Analog sensor emulation             │
│      └── DS6601 Load ──── Actuator load simulation            │
│                                         │                       │
│                               ┌─────────▼──────────┐           │
│                               │  ADAS ECU (DUT)    │           │
│                               │  ├── ECU hardware  │           │
│                               │  ├── Real firmware │           │
│                               │  └── Production SW │           │
│                               └────────────────────┘           │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8.4 CARMAKER — VEHICLE AND TRAFFIC SIMULATION

### CarMaker Integration for ADAS Testing

CarMaker (by IPG Automotive) provides realistic 3D vehicle dynamics and traffic simulation that feeds sensor models in the HIL environment.

```
CarMaker WORKFLOW:
┌─────────────────────────────────────────────────────────────────┐
│  CARMAKER SCENARIO SETUP                                        │
│  ├── Road: Highway A9 Germany, 3-lane, 130 km/h limit          │
│  ├── Ego Vehicle: Mercedes E-Class, full dynamics model         │
│  ├── Traffic Objects:                                           │
│  │   ├── Vehicle A: 200m ahead, speed 80 km/h (slow!)         │
│  │   ├── Vehicle B: adjacent lane, speed 120 km/h             │
│  │   └── Pedestrian C: crossing at T=45s                       │
│  └── Environment: Clear weather, daytime                       │
│                                                                 │
│  SENSOR MODEL OUTPUT → SCALEXIO:                               │
│  ├── RADAR model: Object distance, velocity, azimuth           │
│  ├── Camera model: Lane marking positions                       │
│  └── USS model: Near-range obstacle distance                   │
│                     │                                          │
│                     ▼ (via DS1552 Ethernet)                    │
│  ADAS ECU RECEIVES:                                            │
│  ├── SOME/IP RadarObject events (20ms)                         │
│  ├── SOME/IP CameraLane events (30ms)                          │
│  └── ECU runs FCW/AEB algorithm on simulated data             │
│                     │                                          │
│                     ▼ (ECU output via CAN FD)                  │
│  SCALEXIO CAPTURES:                                            │
│  ├── FCW_Trigger signal                                        │
│  ├── AEB_BrakeRequest signal                                   │
│  └── Timing: FCW in < 100ms after TTC < 2.0s                  │
└─────────────────────────────────────────────────────────────────┘
```

### Test Scenario: Forward Collision Warning

```
SCENARIO: Highway Braking — Leading Vehicle Cut-In

T=0s:    Ego speed = 130 km/h, no obstacles
T=5s:    Vehicle A enters from adjacent lane at 100m, speed 50 km/h
T=5.5s:  TTC = 100m / (130-50) km/h = 100/(80/3.6) = 4.5s (safe)
T=8s:    Distance closes to 30m, TTC = 30/(80/3.6) = 1.35s
         → FCW_TRIGGER expected (TTC < 2.0s threshold)
T=8.5s:  Distance = 15m, TTC = 0.67s
         → AEB_BRAKE_REQUEST expected (TTC < 0.8s threshold)

VALIDATION CRITERIA:
├── FCW_TRIGGER asserted within 100ms of TTC crossing 2.0s
├── AEB_BRAKE_REQUEST within 50ms of TTC crossing 0.8s
├── No false FCW/AEB during T=0 to T=5 (no target)
└── Brake request released when TTC > 1.5s (hysteresis)
```

---

## 8.5 CLOSED-LOOP SIMULATION

### What Is Closed-Loop in HIL?

```
OPEN LOOP:
  SCALEXIO ──► [generates signals] ──► ECU_DUT (no feedback)
  Test inputs are fixed, regardless of ECU output

CLOSED LOOP:
  SCALEXIO ──► [vehicle model] ──► ECU_DUT ──► [ECU output] ──► 
       ▲                                                           │
       └──────────────────────────────── [SCALEXIO applies output] ┘
  ECU output CHANGES the simulation state:
  ECU requests braking → SCALEXIO applies deceleration to vehicle model
  Vehicle slows → TTC changes → sensor data changes → ECU re-evaluates
```

### Closed-Loop AEB Scenario Implementation

```python
# Python script for dSPACE ControlDesk automation
# Runs a closed-loop FCW/AEB HIL test

import dspace.python.control_desk as cd

class AEB_HIL_Test:
    def __init__(self, test_bench):
        self.bench = test_bench
        self.PASS = True
        
    def setup(self):
        """Load CarMaker scenario and configure HIL."""
        cd.load_project("Highway_AEB_Scenario.cdx")
        cd.set_parameter("CarMaker/EgoVehicle/Speed", 130.0)   # 130 km/h
        cd.set_parameter("CarMaker/TrafficA/Speed", 50.0)      # Slow vehicle
        cd.set_parameter("CarMaker/TrafficA/InitDist", 200.0)  # 200m ahead
        cd.set_parameter("CarMaker/TrafficA/CutInTime", 5.0)   # Cut in at T=5s
        print("[SETUP] Scenario configured: Highway AEB at 130 km/h")
    
    def run(self):
        """Start simulation and monitor ECU outputs."""
        cd.start_simulation()
        
        fcw_triggered = False
        aeb_triggered = False
        fcw_time = -1.0
        aeb_time = -1.0
        
        for t in range(0, 15000, 10):  # 0 to 15s, step 10ms
            current_time = t / 1000.0  # Convert to seconds
            
            # Read ECU outputs from SCALEXIO I/O
            fcw_signal = cd.read_signal("ADAS_ECU/FCW_Active")
            aeb_signal = cd.read_signal("ADAS_ECU/AEB_BrakeRequest")
            ttc_value  = cd.read_signal("ADAS_ECU/TTC_Estimate")
            
            # Check FCW timing
            if fcw_signal == 1 and not fcw_triggered:
                fcw_triggered = True
                fcw_time = current_time
                print(f"[INFO] FCW triggered at T={fcw_time:.2f}s, TTC={ttc_value:.2f}s")
                
                if ttc_value > 2.5 or ttc_value < 1.0:
                    print(f"[FAIL] FCW triggered at wrong TTC: {ttc_value}")
                    self.PASS = False
            
            # Check AEB timing
            if aeb_signal > 0 and not aeb_triggered:
                aeb_triggered = True
                aeb_time = current_time
                print(f"[INFO] AEB triggered at T={aeb_time:.2f}s, TTC={ttc_value:.2f}s")
                
                if aeb_time - fcw_time < 0.0 or aeb_time - fcw_time > 5.0:
                    print("[FAIL] AEB timing relative to FCW out of spec")
                    self.PASS = False
            
            # Check for false activations before T=5s
            if current_time < 4.9 and (fcw_signal == 1 or aeb_signal > 0):
                print(f"[FAIL] False activation before cut-in at T={current_time:.2f}s")
                self.PASS = False
            
            cd.wait(10)  # 10ms step
        
        cd.stop_simulation()
        
    def report(self):
        """Generate test report."""
        result = "PASS" if self.PASS else "FAIL"
        print(f"\n{'='*60}")
        print(f"AEB HIL TEST RESULT: {result}")
        print(f"{'='*60}")
```

---

## 8.6 SIGNAL GENERATION AND FAULT INJECTION

### Signal Generation — SCALEXIO I/O

```
SIGNAL TYPES GENERATED BY HIL FOR ECU TESTING:

ANALOG OUTPUTS (DAC → ECU pins):
├── Battery voltage: 12V ± ripple (simulated alternator)
├── Temperature sensor: -40°C to +150°C (NTC curve)
├── Accelerometer: ±10g range
└── Pressure sensor: 0–10 bar (manifold pressure)

DIGITAL OUTPUTS (PWM/GPIO → ECU pins):
├── Wheel speed pulses (Hall sensor simulation)
├── Crank/cam position signals
└── Switch status (brake pedal, door open)

PROTOCOL SIMULATION:
├── CAN FD messages (sensor data, gateway messages)
├── LIN schedules (body slave responses)
└── Ethernet SOME/IP events (RADAR, camera data)
```

### Fault Injection — Categories

```
HIL FAULT INJECTION CATEGORIES:

1. SIGNAL FAULTS:
   ├── Signal open (disconnect signal wire)
   ├── Signal short to GND (0V)
   ├── Signal short to battery (12V)
   ├── Signal out of range (above/below valid range)
   └── Signal intermittent (random disconnection at 10Hz)

2. POWER SUPPLY FAULTS:
   ├── Voltage drop: 12V → 9V during heavy load
   ├── Voltage spike: 12V → 32V (load dump pulse)
   ├── Power interruption: 100ms power loss
   └── Reverse polarity (ECU protection test)

3. COMMUNICATION FAULTS:
   ├── CAN bus off (terminate one end, induce bit errors)
   ├── CAN message delay: inject 200ms delay to CAN ID 0x200
   ├── CAN message loss: drop 10% of frames randomly
   ├── Ethernet link loss: disable DS1552 port for 1s
   └── SOME/IP event gap: block UDP port 30490 for 500ms

4. TIMING FAULTS:
   ├── Delayed sensor data: 200ms delay on RADAR input
   ├── Jittered sensor: ±50ms jitter on camera timing
   └── gPTP desync: introduce 10µs offset intentionally

EXAMPLE CAPL FAULT INJECTION SCRIPT:
// Inject CAN bus off condition for 500ms
on key 'f' {
    write("Injecting CAN bus fault for 500ms...");
    setBusOff("CAN1");
    setTimer(t_FaultTimer, 500);
}

on timer t_FaultTimer {
    setBusNormal("CAN1");
    write("CAN fault cleared — bus normal");
}
```

---

## 8.7 REAL-TIME REQUIREMENTS FOR HIL

### Timing Budget Analysis

```
HIL REAL-TIME EXECUTION BUDGET:

Model step time: 1 ms (1kHz execution rate for ADAS)

Budget allocation:
├── CarMaker vehicle model: 0.35ms
├── RADAR sensor model: 0.15ms
├── Camera lane model:  0.10ms
├── I/O processing (FPGA): 0.05ms
├── SOME/IP event generation: 0.10ms
└── Remaining headroom: 0.25ms (25% — IMPORTANT!)

RULE: HIL model must use < 75% of step time
       (25% headroom for timing jitter and model updates)

JITTER TOLERANCE:
• SCALEXIO guaranteed jitter: < 1µs (FPGA I/O)
• Real-time OS scheduler jitter: < 10µs
• gPTP accuracy between SCALEXIO and ECU: < 1µs
```

---

## 8.8 HIL INTERVIEW QUESTIONS

**Q1: What is the difference between MIL, SIL, and HIL? When do you use each?**

> MIL (Model In the Loop) validates the algorithm model in Simulink without real code — used early to verify algorithm logic. SIL (Software In the Loop) runs compiled production code on a PC in a simulated environment — validates that C code matches model behavior. HIL (Hardware In the Loop) runs real ECU hardware with real firmware against a real-time simulator — validates the complete system including hardware timing, interrupt handling, and protocol interfaces. MIL is cheapest, HIL is most realistic and used before vehicle testing.

**Q2: Explain how dSPACE SCALEXIO simulates RADAR data for an ADAS ECU.**

> SCALEXIO runs a RADAR sensor model in real-time at 20ms cycle rate. The model calculates object positions, velocities, and range based on the CarMaker vehicle simulation. The output (object distance, speed, azimuth, elevation) is serialized into SOME/IP format by a Simulink S-function. The DS1552 Ethernet module transmits these as SOME/IP UDP events over 100BASE-T1 to the real ADAS ECU. The ADAS ECU processes them identically to real RADAR sensor data since the protocol is identical.

**Q3: What is closed-loop HIL testing and why is it important?**

> Closed-loop HIL means the ECU's output signals are fed back into the simulation model to change the simulated environment. Example: ADAS ECU requests AEB brake pressure → SCALEXIO applies deceleration to the vehicle model → vehicle slows down → TTC changes → RADAR model updates → ADAS ECU sees the effect. This validates that the control system actually achieves the intended outcome. Open-loop just checks if the ECU produces the right output for a given input without verifying the full feedback cycle.

**Q4: How do you perform fault injection in a HIL environment and what do you verify?**

> HIL fault injection uses the SCALEXIO I/O boards to inject electrical and protocol faults. For signal faults, I configure the DS6601 load board relays to short or open sensor lines. For protocol faults, I use CAPL scripts in CANoe to delay or drop CAN messages. For Ethernet faults, I script the DS1552 to block UDP traffic for specific ports. I verify: (1) ECU detects the fault and reports a DTC. (2) ECU enters a safe state (failsafe mode, reduced function). (3) ECU recovers correctly when the fault is removed. (4) Recovery time is within the specified limit.

**Q5: How does CarMaker integrate with dSPACE SCALEXIO?**

> CarMaker runs on the host PC and provides the vehicle dynamics model. It outputs the ego vehicle state (position, speed, heading) and traffic object positions. These are fed into the sensor models (RADAR, camera) also running in CarMaker or Simulink. The sensor model outputs are compiled and downloaded to SCALEXIO real-time processor via ControlDesk. SCALEXIO runs the sensor model in hard real-time and generates physical-level signals (SOME/IP packets, CAN frames) to the ECU DUT. The ECU's control outputs (braking, steering) are captured by SCALEXIO and fed back to CarMaker to close the loop.

---

*Next Section → [Section 9: Testing & Validation](09_Testing_Validation.md)*
