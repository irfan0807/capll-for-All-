# CARMAKER + dSPACE — DEEP DIVE
## Module 7 of 7 | advanced_automotive_learning

---

## 1. MIL / SIL / HIL / VIL OVERVIEW

```
SIMULATION LEVELS — PROGRESSIVE FIDELITY:

  ┌─────────────────────────────────────────────────────────────────┐
  │  MIL (Model-In-the-Loop)                                        │
  │  • Simulink model of algorithm runs inside Simulink             │
  │  • Plant model also Simulink (vehicle + environment)            │
  │  • No real ECU code — algorithm prototype only                  │
  │  • Speed: very fast (100× real-time possible)                   │
  │  • Use: algorithm verification, design exploration              │
  └─────────────────────────────────────────────────────────────────┘
            │ Code generation (Embedded Coder / TargetLink)
  ┌─────────────────────────────────────────────────────────────────┐
  │  SIL (Software-In-the-Loop)                                     │
  │  • Generated C/C++ code runs in PC process                      │
  │  • Plant model still virtual (CarMaker or Simulink)             │
  │  • Tests: unit test, integration test of algorithm code         │
  │  • Speed: ≈ real-time                                           │
  │  • Use: MISRA compliance, code coverage, regression             │
  └─────────────────────────────────────────────────────────────────┘
            │ Port code to ECU hardware
  ┌─────────────────────────────────────────────────────────────────┐
  │  HIL (Hardware-In-the-Loop)                                     │
  │  • Real ECU hardware runs real production software              │
  │  • Plant model runs on real-time simulator (dSPACE SCALEXIO)    │
  │  • I/O: real CAN, Ethernet, analog, digital signals             │
  │  • Speed: strictly real-time (1ms or faster)                    │
  │  • Use: system integration test, fault injection, ADAS test     │
  └─────────────────────────────────────────────────────────────────┘
            │ Add driver/real roads
  ┌─────────────────────────────────────────────────────────────────┐
  │  VIL (Vehicle-In-the-Loop)                                      │
  │  • Real vehicle on proving ground                               │
  │  • Synthetic sensor data injected in real-time                  │
  │  • (e.g., synthetic radar objects injected into real ECU)       │
  │  • Use: ADAS scenario testing without physical GVT targets       │
  └─────────────────────────────────────────────────────────────────┘
```

---

## 2. DSPACE SCALEXIO HARDWARE

```
dSPACE SCALEXIO HIL SYSTEM ARCHITECTURE:

  ┌─────────────────────────────────────────────────────────────────┐
  │                    SCALEXIO CHASSIS                             │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
  │  │  DS1552       │  │  DS4330       │  │  DS2655       │         │
  │  │  Ethernet     │  │  I/O Board    │  │  Signal Gen.  │         │
  │  │  Interface    │  │  (16 DI/O,    │  │  (PWM, Sine,  │         │
  │  │  - 1000BASE-T │  │  8 AI, 4 AO)  │  │  sensor sim)  │         │
  │  │  - CAN FD     │  │               │  │               │         │
  │  │  - FlexRay    │  └──────────────┘  └──────────────┘         │
  │  └──────────────┘                                               │
  │  ┌──────────────────────────────────────────────────────────┐   │
  │  │  FPGA Core (Xilinx Virtex-7)   Processing Core (Intel)  │   │
  │  │  Real-time I/O at < 1μs        Model at 1ms / 100μs     │   │
  │  └──────────────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────────────┘
           │ Ethernet (RTMaps, ControlDesk API)
  ┌────────▼──────────────────────────────────────────────────────┐
  │  Host PC                                                       │
  │  - ControlDesk (instrument panel)                              │
  │  - SCALEXIO Experiment Manager                                 │
  │  - Python (via dSPACE API or ControlDesk Python scripting)     │
  └────────────────────────────────────────────────────────────────┘
           │ CAN/LIN/Ethernet/Analog/Digital
  ┌────────▼──────────────────────────────────────────────────────┐
  │  ECU Under Test (DUT)                                          │
  │  - ADAS Domain Controller                                      │
  │  - BCM, Engine Controller, etc.                                │
  └────────────────────────────────────────────────────────────────┘
```

### 2.1 dSPACE Key Hardware Boards

```
BOARD       PURPOSE                          KEY SPECS
───────────────────────────────────────────────────────────────────
DS1552      Bus Interfaces                   CAN FD × 8, Ethernet × 4, 
                                             LIN × 8, FlexRay × 2
DS4330      Multi-purpose I/O                16 digital I/O, 8 analog in,
                                             4 analog out, 2 PWM
DS2655      Signal Conditioning / Gen        Sensor simulation (NTC, potentiometer)
                                             LVDS, SENT, PSI5
DS5202      FPGA board for custom timing     < 1μs latency for critical I/O
ConfigDesk  Model-to-hardware mapping tool   Connects Simulink signals to board I/O

REAL-TIME REQUIREMENT:
  Model step size: typically 1ms (1 kHz)
  CPU utilization budget: 75% max
  If model exceeds 75% CPU: overrun → test failure
  Solution: reduce model complexity or use faster task rates
```

---

## 3. CARMAKER — VIRTUAL VEHICLE TESTING

### 3.1 CarMaker Architecture

```
IPGCARMAKER COMPONENTS:

  Road/Environment Model:
    - Road surface (IPGRoad): 3D road geometry, surface type, friction
    - Traffic: other vehicles with behavior (follow, overtake, cut-in)
    - Environment: weather, visibility, traffic signs

  Vehicle Dynamics Model:
    - TireModel: MF (Magic Formula) tire physics
    - Powertrain: engine, transmission, braking model
    - Suspension: 4-corner model
    - Aerodynamics: Cd, lift coefficient

  Driver Model:
    - IPGDriver: follows a defined path at target speed
    - Configurable: aggressiveness, reaction time, steering style

  Sensor Models (for ADAS):
    - RSI (Radar Sensor Interface): generates radar object list
    - CSI (Camera Sensor Interface): generates camera image / bounding boxes
    - LiDAR model: generates point cloud

  TestRun:
    - Defines scenario: road, vehicle, driver, initial conditions
    - Start/stop/event conditions
    - Output variables (time-stamped signals for analysis)
```

### 3.2 CarMaker + dSPACE HIL Integration

```
CLOSED-LOOP HIL WITH CARMAKER + dSPACE:

  ┌──────────────────────────────────────────────────────────────────┐
  │  CarMaker (Vehicle Dynamics)                                      │
  │  Running on SCALEXIO real-time target                             │
  │                                                                  │
  │  Outputs → to ECU (via DS1552):                                  │
  │    - Vehicle speed (CAN)                                         │
  │    - Wheel speeds (analog from DS4330)                           │
  │    - Radar object list (synthetic, via CAN)                      │
  │    - Camera lane data (synthetic, via Ethernet SOME/IP)          │
  │                                                                  │
  │  Inputs ← from ECU:                                              │
  │    - Brake request (CAN)                                         │
  │    - Throttle position                                           │
  │    - Steering angle request                                      │
  │                                                                  │
  │  Result: ECU controls virtual vehicle → vehicle dynamics change  │
  │          → new sensor data → ECU reacts → closed loop            │
  └──────────────────────────────────────────────────────────────────┘

TIMING:
  CarMaker step: 1ms (1kHz vehicle dynamics)
  SCALEXIO FPGA: 100μs I/O latency
  ECU CAN cycle: 10ms (100Hz actuator command)
  Total loop latency: ≈ 12ms → acceptable for ADAS

SENSOR INJECTION MODES:
  Object-level injection: inject radar object list (synthetic objects from CarMaker)
  Raw-level injection:    inject analog radar signal (requires RF injection hardware)
  For most HIL ADAS testing: object-level is sufficient and practical
```

---

## 4. CARMAKER TESTRUN API (PYTHON)

```python
# carmaker_api.py
"""
CarMaker TestRun control via TCP API.
Allows Python scripts to control CarMaker from test automation.
"""
import socket
import time
import re


class CarMakerClient:
    """
    Controls CarMaker via TCP command interface.
    CarMaker must be running with IPGMovie server enabled.
    
    Default port: 16660 (command channel)
    """
    CMD_PORT = 16660

    def __init__(self, host: str = "localhost"):
        self.host = host
        self._sock = None

    def connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(5.0)
        self._sock.connect((self.host, self.CMD_PORT))
        # Read welcome message
        self._recv()

    def disconnect(self):
        if self._sock:
            self._sock.close()
            self._sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    def _send(self, cmd: str):
        self._sock.sendall((cmd + "\n").encode("utf-8"))

    def _recv(self) -> str:
        data = b""
        while True:
            chunk = self._sock.recv(4096)
            data += chunk
            if b"\n" in chunk:
                break
        return data.decode("utf-8").strip()

    def get_quantity(self, quantity_name: str) -> float:
        """Read a CarMaker quantity value."""
        self._send(f"GetQuant {quantity_name}")
        response = self._recv()
        # Response: "GetQuant Vehicle.v 27.778"
        parts = response.split()
        return float(parts[-1]) if parts else 0.0

    def set_quantity(self, name: str, value: float):
        """Write a CarMaker quantity value."""
        self._send(f"SetQuant {name} {value}")

    def load_testrun(self, testrun_name: str):
        """Load a TestRun by name."""
        self._send(f"LoadTestRun {testrun_name}")
        response = self._recv()
        return "OK" in response

    def start_simulation(self) -> bool:
        """Start CarMaker simulation."""
        self._send("StartSim")
        response = self._recv()
        return "OK" in response

    def stop_simulation(self):
        """Stop CarMaker simulation."""
        self._send("StopSim")
        self._recv()

    def wait_for_simulation_end(self, timeout: float = 120.0) -> bool:
        """Wait until simulation ends (status = Idle)."""
        t_end = time.monotonic() + timeout
        while time.monotonic() < t_end:
            self._send("GetStatus")
            status = self._recv()
            if "Idle" in status:
                return True
            time.sleep(0.5)
        return False

    def get_vehicle_speed_kmh(self) -> float:
        v_ms = self.get_quantity("Vehicle.v")
        return v_ms * 3.6

    def inject_radar_target(self, obj_id: int, range_m: float,
                             azimuth_deg: float, velocity_mps: float):
        """Inject a synthetic radar target into the simulation."""
        self._send(f"SetQuant Radar.Obj[{obj_id}].Range {range_m}")
        self._send(f"SetQuant Radar.Obj[{obj_id}].Azimuth {azimuth_deg}")
        self._send(f"SetQuant Radar.Obj[{obj_id}].RelVelocity {velocity_mps}")
```

---

## 5. CONTROLDESK PYTHON API

```python
# controldesk_api.py
"""
dSPACE ControlDesk Python automation via COM interface.
Requires ControlDesk installed on the host PC (Windows).
"""
import win32com.client  # pywin32
import time


class ControlDeskAuto:
    """
    ControlDesk automation via COM (Windows only).
    Enables reading/writing ECU signals from Python.
    """
    def __init__(self):
        self.cd = None

    def connect(self):
        self.cd = win32com.client.Dispatch("ControlDesk.Application")
        print(f"ControlDesk {self.cd.Version} connected")

    def read_variable(self, path: str) -> float:
        """
        Read a variable value.
        path example: "Model Root/AEB_System/AEBRequest"
        """
        var = self.cd.ActiveExperiment.Variables[path]
        return var.Value

    def write_variable(self, path: str, value: float):
        """Write a variable value."""
        var = self.cd.ActiveExperiment.Variables[path]
        var.Value = value

    def capture_signals(self, variable_paths: list,
                        duration_s: float, sample_rate_hz: float = 100) -> dict:
        """Capture multiple signals over time. Returns {path: [values]}."""
        results = {p: [] for p in variable_paths}
        t_end = time.monotonic() + duration_s
        interval = 1.0 / sample_rate_hz
        while time.monotonic() < t_end:
            for path in variable_paths:
                results[path].append(self.read_variable(path))
            time.sleep(interval)
        return results
```

---

## 6. FAULT INJECTION CATEGORIES

```
FAULT INJECTION IN HIL TESTING:

  1. SIGNAL FAULTS (via DS4330 I/O Board):
     - Short to ground:    output analog 0V instead of sensor value
     - Short to battery:   output 5V or 12V (overcurrent)
     - Open circuit:       disconnect signal (floating input)
     - Out-of-range:       output value outside sensor physical range
     Implementation: relay matrix controlled by SCALEXIO model
     
  2. BUS FAULTS (via DS1552):
     - Message dropout:    suppress CAN message for N frames
     - Message delay:      add latency to CAN message
     - Corrupted data:     inject wrong signal values
     - Bus off:            force CAN error frame
     Implementation: SCALEXIO Ethernet/CAN fault injection blocks

  3. POWER FAULTS (via DS2655 or external supply):
     - Voltage dip:        reduce supply from 12V to 8V for 100ms
     - Power interruption: remove ECU power briefly (ECU reset test)
     - Overvoltage:        apply 16V (load dump simulation)
     
  4. ALGORITHM FAULTS (model injection):
     - Sensor value stuck: hold radar distance at fixed value
     - Sensor noise:       add white noise to sensor input
     - Latency:            add N-step delay to sensor data

SAFETY RULE FOR FAULT INJECTION:
  Never inject physical overcurrent faults on production ECUs
  Use "Soft fault injection" (model-level signals) for mass testing
  Physical fault injection (relay): only on dedicated fault injection specimens
```

---

## 7. TEST CASES

```
TC-HIL-001: AEB Activation Timing (CarMaker + dSPACE)
  Setup: CarMaker AEB City scenario (50 km/h, stationary target at 20m)
         SCALEXIO injects synthetic radar data to ADAS ECU
  Action: Run TestRun via CarMaker API; monitor CAN for AEB_BrakeReq
  Expected: AEB_BrakeReq = 1 when TTC < 0.8s
  Pass criteria: Timing within ±100ms of expected activation point

TC-HIL-002: Fault Injection — Radar Message Dropout
  Setup: SCALEXIO configured to drop radar CAN message for 200ms
         AEB scenario running
  Action: Trigger message dropout at TTC = 2.0s
  Expected: ADAS ECU detects signal loss, inhibits AEB, raises DTC
  Pass criteria: DTC RADAR_COMM_ERROR set; AEB inhibited within 250ms

TC-HIL-003: ECU Reset During Active AEB
  Setup: AEB scenario running at TTC = 1.0s
         Power fault injected to ADAS ECU for 50ms
  Expected: ESC (brake) holds current brake pressure during ECU outage
            ECU recovers within 200ms, AEB resumes if threat still present
  Pass criteria: No collision; ESC plausibility check passed

TC-HIL-004: CarMaker Rain Scenario — Sensor Degradation
  Setup: CarMaker rain weather model active (50mm/hr)
         Radar reliability degraded in model
  Action: Run AEB City scenario with rain active
  Expected: AEB still activates (degraded but functional)
  Pass criteria: AEB activates within 2× normal timing tolerance
```

---

## 8. INTERVIEW Q&A

**Q1: What is the difference between HIL and SIL testing?**
> SIL (Software-in-the-Loop) runs generated C code in a PC simulation — no real ECU hardware. It verifies algorithm correctness and code coverage. HIL (Hardware-in-the-Loop) runs the production software on the real ECU hardware connected to a real-time simulator that provides synthetic I/O signals. HIL verifies the complete system including hardware, BSW, and timing — it can catch issues like interrupt latency, memory overflows, and CAN timing that SIL cannot.

**Q2: How does CarMaker integrate with a dSPACE HIL system?**
> CarMaker vehicle dynamics model is compiled and runs on the dSPACE SCALEXIO real-time target. SCALEXIO interfaces to the ECU via physical CAN/Ethernet/analog I/O. The ECU receives sensor signals (e.g., synthetic radar objects generated by CarMaker) and sends actuator commands (e.g., brake request via CAN) back to SCALEXIO, which feeds them to the vehicle dynamics model to close the loop. This is controlled from a host PC via ControlDesk and CarMaker API.

**Q3: What is the real-time budget for SCALEXIO models and what happens if it's exceeded?**
> The standard step size is 1ms (1 kHz). dSPACE recommends keeping CPU utilization below 75%. If the model exceeds the time budget: SCALEXIO reports a "task overrun." In safety applications, a task overrun is treated as a test failure — the system is not operating in real-time. Solutions: simplify model, use multiple rate tasks (fast: 100μs for I/O, slow: 1ms for vehicle dynamics), or use a faster FPGA core.

**Q4: Describe how you would set up a fault injection test for radar message dropout.**
> On SCALEXIO: add a fault injection block to the radar CAN message path. The block has a trigger input (fault_inject_cmd) and when asserted, stops forwarding CAN messages for the configured duration. Connect the fault_inject_cmd to a ControlDesk variable so the test script can trigger it remotely. In the test script: start the AEB scenario, wait for TTC = 2.0s, assert fault_inject_cmd for 200ms, then monitor the ECU's CAN output for RADAR_STATUS = DEGRADED and DTC storage.

**Q5: What is VIL (Vehicle-in-the-Loop) and when would you use it over HIL?**
> VIL puts a real vehicle on a proving ground but injects synthetic sensor data into the ECU — so the ECU responds to virtual scenarios while the vehicle physically drives. This tests the full closed-loop system including real dynamics (tires, suspension, g-forces on sensors), real EMC environment, and driver behavior — things HIL cannot fully replicate. VIL is used for final validation before Euro NCAP testing, when you need to verify AEB performance with real-world dynamics but without risking actual collisions or requiring physical targets.

---

*Next: [02_STAR_Answers.md](02_STAR_Answers.md)*
