# 01 — CarMaker Basics

> **Tool**: IPG CarMaker (v10+)  
> **Prerequisites**: Basic automotive knowledge, command line comfort  
> **Outcome**: Run, configure, and script CarMaker TestRuns; understand all core model components

---

## 1. What Is CarMaker?

IPG CarMaker is a **virtual test driving** simulation platform used to develop, test, and validate vehicle systems — especially ADAS, powertrain, and chassis functions — before physical prototypes exist.

```
┌──────────────────────────────────────────────────────────┐
│                    CarMaker Ecosystem                    │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │  Road    │  │ Vehicle  │  │ Driver   │  │ Traffic│  │
│  │  Model   │  │  Model   │  │  Model   │  │ Model  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘  │
│       │             │             │             │        │
│       └─────────────┴─────────────┴─────────────┘        │
│                          │                               │
│              ┌───────────▼───────────┐                   │
│              │   Simulation Kernel   │                   │
│              │  (real-time capable)  │                   │
│              └───────────┬───────────┘                   │
│                          │                               │
│     ┌────────────────────┼────────────────────┐          │
│     ▼                    ▼                    ▼          │
│  ┌──────┐          ┌──────────┐         ┌──────────┐    │
│  │ SUT  │          │ DataDict │         │ CarMaker │    │
│  │(ECU) │          │ (DVA)    │         │   GUI    │    │
│  └──────┘          └──────────┘         └──────────┘    │
└──────────────────────────────────────────────────────────┘
```

### When to Use CarMaker
| Use Case | CarMaker Role |
|----------|--------------|
| ADAS function development | Closed-loop virtual testing before HIL |
| Euro NCAP scenario testing | Standardized test road + scenario library |
| Sensor model validation | Camera, radar, LiDAR sensor models |
| Regression testing overnight | Batch TestRun execution via scripts |
| SIL→HIL transition | Same TestRun, swapped execution target |

---

## 2. CarMaker Workspace Structure

```
CarMaker_Project/
├── Data/
│   ├── TestRun/            ← .tcl TestRun definitions
│   ├── Vehicle/            ← Vehicle parameter sets (.veh)
│   ├── Driver/             ← Driver parameter sets (.drv)
│   ├── Road/               ← Road files (.rd5 or OpenDRIVE .xodr)
│   ├── Sensor/             ← Sensor configurations (.uss, .radar, .cam)
│   ├── Traffic/            ← Traffic object definitions
│   └── Maneuver/           ← Maneuver scripts (.man)
├── src/                    ← Custom C/C++ user model code
├── Makefile                ← Project build file
└── CMProject.cm            ← Project configuration
```

### Key File Types
| Extension | Description |
|-----------|-------------|
| `.tcl` | TestRun script (parameters, start/stop conditions) |
| `.veh` | Vehicle parameter set (mass, geometry, suspension) |
| `.drv` | Driver model parameters (aggressiveness, preview time) |
| `.rd5` | CarMaker binary road format |
| `.xodr` | OpenDRIVE road format (ISO 21726) |
| `.man` | Maneuver file (steering, throttle, brake sequences) |
| `.erg` | Simulation result file (binary) |
| `.csv` | Exported results |

---

## 3. TestRun — The Core Unit

A **TestRun** defines one complete simulation experiment:

```
TestRun structure (.tcl):
─────────────────────────────────────────
# Vehicle to use
Vehicle.cfg = "Vehicle/MyCar.veh"

# Road to drive on
Road = "Road/HighwayLane.rd5"

# Driver model
Driver.cfg = "Driver/Default.drv"

# Start conditions
StartTime = 0.0
EndTime   = 30.0          ← or event-based end

# Simulation parameters
SimRate = 1000            ← Hz (1 kHz = 1 ms step)
SampleRate = 1000

# Outputs (DVA quantities to log)
DVA.cfg = "Data/DVA/AEB_quantities.dvacfg"

# Test result pass/fail condition
TestCriteria {
    Quantity   "AEB.BrakeActive"
    Condition  >= 1
    TimeFrom   2.0
    TimeTo     5.0
}
─────────────────────────────────────────
```

### TestRun Execution Modes
| Mode | Description | Typical Use |
|------|-------------|-------------|
| **Offline** | Faster-than-realtime on PC | Development, large batch runs |
| **Sync (1:1)** | Real-time on PC | SIL with strict timing |
| **HIL** | On dSPACE/NI hardware | Integration testing with real ECU |

---

## 4. DVA — Data Variable Access

DVA is CarMaker's internal signal bus. Every quantity in the simulation is accessible by path name.

```
DVA naming convention:
  Car.ax              ← longitudinal acceleration [m/s²]
  Car.vx              ← longitudinal velocity [m/s]
  Car.Steer.Ang       ← steering angle [rad]
  Sensor.Radar.0.NearestObject.ds ← radar nearest object distance
  ADAS.AEB.BrakeRequest          ← AEB brake demand
  ECU.CAN.AEB_BrakeCmd           ← CAN signal from ECU

DVA configuration file (.dvacfg):
  Quantity "Car.vx"        SampleRate 1000
  Quantity "Car.ax"        SampleRate 1000
  Quantity "ADAS.AEB.*"    SampleRate 1000   ← wildcard
```

### Accessing DVA via Python (IPG Remote)
```python
import socket
import time

class CarMakerClient:
    """TCP connection to CarMaker Remote API (port 16660)."""

    def __init__(self, host="localhost", port=16660):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock.settimeout(5.0)

    def _send(self, cmd: str) -> str:
        self.sock.sendall((cmd + "\n").encode())
        return self.sock.recv(4096).decode().strip()

    def get_quantity(self, name: str) -> float:
        """Read a DVA quantity by name."""
        resp = self._send(f"DVAGet {name}")
        # Response: "OK <value>" or "ERR <message>"
        if resp.startswith("OK"):
            return float(resp.split()[1])
        raise RuntimeError(f"DVA error: {resp}")

    def set_quantity(self, name: str, value: float):
        """Write a DVA quantity."""
        resp = self._send(f"DVASet {name} {value}")
        if not resp.startswith("OK"):
            raise RuntimeError(f"DVA set error: {resp}")

    def start_testrun(self, testrun_path: str):
        resp = self._send(f"StartSim {testrun_path}")
        if not resp.startswith("OK"):
            raise RuntimeError(f"StartSim failed: {resp}")

    def wait_for_end(self, timeout: float = 120.0):
        start = time.time()
        while time.time() - start < timeout:
            status = self._send("GetStatus")
            if "idle" in status.lower():
                return True
            time.sleep(0.5)
        raise TimeoutError("TestRun did not finish in time")

    def close(self):
        self.sock.close()


# Usage
if __name__ == "__main__":
    cm = CarMakerClient()
    cm.start_testrun("TestRun/AEB_City_30kmh")
    cm.wait_for_end()
    ttc = cm.get_quantity("Sensor.Radar.0.NearestObject.TTC")
    brk = cm.get_quantity("ADAS.AEB.BrakeActive")
    print(f"TTC={ttc:.2f}s  BrakeActive={brk}")
    cm.close()
```

---

## 5. Vehicle Model

CarMaker provides a multi-body vehicle dynamics model:

```
Vehicle Model Components:
─────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────┐
│                  Vehicle (.veh file)                │
│                                                     │
│  Body Mass  ←── Inertia tensor, CoG position        │
│  Suspension ←── Spring/damper, kinematics           │
│  Tires      ←── Magic Formula / FTire / CDTire      │
│  Powertrain ←── Engine torque map, gearbox          │
│  Brakes     ←── Hydraulic model, ABS               │
│  Steering   ←── Rack-and-pinion, EPS torque model   │
└─────────────────────────────────────────────────────┘
```

### Key Vehicle Parameters
```ini
# Vehicle/MyCar.veh
Body.mass       = 1650       # kg
Body.I.xx       = 450        # Roll inertia [kg·m²]
Body.I.yy       = 2100       # Pitch inertia [kg·m²]
Body.I.zz       = 2000       # Yaw inertia [kg·m²]

# Tire model
Tire.kind = FTire            # High-fidelity flexible ring tire
Tire.0.Fz.nominal = 4000     # Nominal load [N]

# Powertrain
Powertrain.kind = Generic
Engine.TqMax = 320           # [Nm]
Engine.nMax  = 6500          # [rpm]
```

---

## 6. Road Model

```
Road types available:
─────────────────────────────────────────────
Type          Format    Best For
─────────────────────────────────────────────
CarMaker .rd5 Binary    Simple test tracks
OpenDRIVE     .xodr     Complex road networks
OpenSCENARIO  .xosc     Scenario scripting
IPGRoad GUI   Visual    Custom road building
─────────────────────────────────────────────

Road attributes:
  - Lane widths, markings
  - Road surface (friction coefficient μ)
  - Elevation profile
  - Traffic signs (virtual)
  - Speed limits
```

---

## 7. Driver Model

The driver model controls the vehicle to follow a reference trajectory:

```
Driver Model Types:
───────────────────────────────────────────────────────
Adaptive/APID  ← PID-based, follows road center line
Comfort        ← Human-like smooth inputs
Sportive       ← Aggressive, higher lateral acceleration
Expert         ← Near-limit driving
ClosedLoop     ← Follows exact reference trajectory
OpenLoop       ← Pre-defined steering/throttle from file
───────────────────────────────────────────────────────

Key driver parameters (.drv):
  PreviewTime  = 0.8     # Look-ahead time [s]
  Aggressivity = 0.5     # 0=calm, 1=aggressive
  ax.max       = 3.0     # Max braking [m/s²]
  ay.max       = 4.0     # Max lateral [m/s²]
```

---

## 8. TCL Scripting for Batch Automation

CarMaker uses Tcl (Tool Command Language) for TestRun scripting and automation:

```tcl
# batch_run.tcl — Run 5 speeds for AEB city scenario

set speeds {20 30 40 50 60}
set results {}

foreach v $speeds {
    # Set initial speed
    DVASet "Car.vx" [expr $v / 3.6]   ;# km/h → m/s

    # Start TestRun
    StartSim "TestRun/AEB_City_GVT"

    # Wait for completion
    WaitForEnd 60

    # Read result
    set brk [DVAGet "ADAS.AEB.BrakeActive"]
    set ttc [DVAGet "Sensor.Radar.0.NearestObject.TTC"]

    lappend results "v=${v}kmh BrakeActive=${brk} TTC=${ttc}"
    puts "DONE: v=$v km/h → BrakeActive=$brk TTC=$ttc"
}

# Save results
set fh [open "results_aeb_sweep.txt" w]
foreach r $results { puts $fh $r }
close $fh
puts "All runs complete."
```

---

## 9. Sensor Models in CarMaker

```
Sensor types:
─────────────────────────────────────────────────────────
Radar    ← Object list output (range, speed, angle, RCS)
Camera   ← Image or virtual lane/object detection output
LiDAR    ← Point cloud or object list
Ultrasonic ← Near-range distance sensors
GPS/IMU  ← Position, velocity, acceleration
─────────────────────────────────────────────────────────

Radar sensor config (.radar):
  MaxRange       = 250.0     # [m]
  AzimuthFOV     = 18.0      # [°] half-angle
  ElevationFOV   = 4.0       # [°] half-angle
  Uncertainty.ds = 0.05      # Distance noise [m σ]
  Uncertainty.vx = 0.1       # Velocity noise [m/s σ]
  OutputFormat   = ObjectList
```

---

## 10. Interview Q&A

**Q1: What is DVA in CarMaker?**  
DVA (Data Variable Access) is CarMaker's global signal bus giving read/write access to every simulation quantity — vehicle states, sensor outputs, ECU commands — using hierarchical path names like `Car.vx` or `ADAS.AEB.BrakeRequest`.

**Q2: What is the difference between offline and HIL mode in CarMaker?**  
Offline runs faster-than-real-time on a PC without time constraints; it's used for development and batch sweeps. HIL mode locks the simulation to wall-clock time and connects to real ECU hardware via I/O boards, so timing errors produce overruns.

**Q3: How do you create a batch sweep of 50 scenarios automatically?**  
Write a Tcl script that loops over parameter combinations, calls `DVASet` to inject parameters, calls `StartSim`, and `WaitForEnd` after each run. Results are collected via `DVAGet` or post-processed from `.erg` files.

**Q4: What is a TestRun pass/fail criterion in CarMaker?**  
`TestCriteria` blocks define a quantity, a comparison operator, and a time window. CarMaker evaluates them automatically at the end of each run and marks the TestRun PASSED/FAILED, which drives CI/CD gates.

**Q5: How do you import an OpenDRIVE road into CarMaker?**  
In IPGRoad GUI: File → Import → OpenDRIVE (.xodr). CarMaker converts it to its internal `.rd5` format. For OpenSCENARIO scenarios you reference the `.xodr` directly in the `.xosc` file.
