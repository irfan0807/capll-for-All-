# 10 — ADAS & Cluster Validation Workflows

> **Domain**: ADAS domain controller + Instrument Cluster HIL validation  
> **Tools**: CarMaker, dSPACE SCALEXIO, ControlDesk, AutomationDesk, Wireshark  
> **Outcome**: Run full Euro NCAP scenarios on HIL; validate cluster/HMI responses

---

## 1. ADAS HIL Test Architecture

```
ADAS HIL Setup — Full Architecture:
───────────────────────────────────────────────────────────────────────
                    ┌─────────────────────────────┐
                    │        Host PC              │
                    │  ControlDesk / AutomDesk    │
                    │  CarMaker GUI               │
                    └──────────┬──────────────────┘
                               │ Ethernet (XCP + CM API)
                    ┌──────────▼──────────────────┐
                    │    dSPACE SCALEXIO           │
                    │    DS6001 (CarMaker RT app)  │
                    │    DS1552 (CAN FD)           │
                    │    DS4330 (Ethernet)         │
                    │    DS2211 (Analog I/O)       │
                    │    DS2655 (FPGA)             │
                    └──────────┬──────────────────┘
                               │ Physical wiring
           ┌───────────────────┼───────────────────┐
           │                   │                   │
     ┌─────▼─────┐       ┌─────▼─────┐      ┌─────▼─────┐
     │ ADAS      │       │ Cluster   │      │ Brake     │
     │ Domain    │       │ ECU       │      │ ECU       │
     │ Controller│       │ (HMI)     │      │ (ABS/ESC) │
     └───────────┘       └───────────┘      └───────────┘
     (SUT - primary)     (SUT - display)    (SUT - actuator)
───────────────────────────────────────────────────────────────────────
```

---

## 2. ADAS Feature Validation Matrix

```
Feature             Test Type       Primary Signal          Pass Criterion
───────────────────────────────────────────────────────────────────────────
AEB (City)          Euro NCAP       Brake pressure           No collision
AEB (Inter-Urban)   Euro NCAP       Brake pressure           No collision
FCW                 Alert latency   Warning indicator CAN    Alert < 1.5 s TTC
ACC                 Functional      ThrottleCmd / BrakeCmd   ±0.5 km/h speed hold
LKA                 Functional      Steer torque output      Lane offset < 0.2 m
LCA                 Alert latency   Turn indicator + warning Alert before LCW zone
BLIS                Functional      Blind spot indicator     Lit when car in zone
Speed Sign Recog.   Functional      TSR_Speed_kmh CAN signal ±5 km/h accuracy
───────────────────────────────────────────────────────────────────────────
```

---

## 3. Euro NCAP AEB Scenarios on HIL

Euro NCAP defines exact test protocols for AEB. CarMaker has built-in scenario support:

### AEB City (CCRs — Car-to-Car Rear Stationary)
```
Scenario definition:
  Ego vehicle:    moving at v = [20, 30, 40, 50] km/h
  Target:         stationary vehicle (GVT — Global Vehicle Target)
  Overlap:        100% (centered)
  Road:           straight, dry (μ = 1.0)
  Pass criterion: No collision (0 points if collision, 4 if full avoidance)

CarMaker TestRun (AEB_City_CCRs.tcl):
─────────────────────────────────────────────────────────────────
Road = "Road/EuroNCAP_Straight.rd5"
Vehicle.cfg = "Vehicle/DUT_ADAS.veh"
Driver.cfg  = "Driver/ClosedLoop_ConstantSpeed.drv"

# Target object (stationary GVT)
Traffic.Obj[0].Type     = Car
Traffic.Obj[0].State    = Stationary
Traffic.Obj[0].PosLong  = 50.0    ;# 50 m ahead at t=0
Traffic.Obj[0].PosLat   = 0.0     ;# centered

DVA.cfg = "Data/DVA/AEB_Euro_NCAP.dvacfg"

TestCriteria {
    # Pass = no collision
    Quantity   "Collision.Occured"
    Condition  == 0
}
─────────────────────────────────────────────────────────────────
```

### AEB Scoring Logic
```python
def score_aeb_ccrs(results: dict) -> float:
    """
    Euro NCAP 2026 AEB City scoring.
    Returns score 0.0 – 4.0 points.
    """
    v_kmh = results["ego_speed_kmh"]
    collision = results["collision_occurred"]
    impact_speed = results["impact_speed_kmh"]

    if collision and impact_speed == 0:
        # Full avoidance
        return 4.0
    elif collision and impact_speed < v_kmh * 0.75:
        # Partial mitigation: speed reduced by > 25%
        return 2.0 * (1 - impact_speed / v_kmh)
    elif not collision:
        return 4.0  # Clean avoidance
    else:
        return 0.0  # No mitigation


# Run full Euro NCAP matrix
test_speeds = [20, 30, 40, 50]
total_score = 0.0

for speed in test_speeds:
    result = run_aeb_scenario(speed_kmh=speed)
    pts = score_aeb_ccrs(result)
    total_score += pts
    print(f"v={speed} km/h → {pts:.2f} pts")

print(f"\nTotal AEB City score: {total_score:.1f} / {4.0 * len(test_speeds):.1f}")
```

---

## 4. Sensor Injection for ADAS HIL

ADAS ECUs have multiple sensor inputs. The HIL must inject **realistic sensor data**:

### Radar Object List (CAN FD)
```
Radar CAN message (Object_01, ID=0x400, 10 ms cycle):
  Byte[0:1]  Object ID           (0x0001)
  Byte[2:3]  Distance [m×10]    (0x01F4 = 50.0 m)
  Byte[4:5]  Rel velocity [m/s] (0xFFEC = -2.0 m/s, approaching)
  Byte[6:7]  Azimuth [°×10]     (0x0000 = centered)
  Byte[8]    Object class       (0x01 = vehicle)
  Byte[9]    Confidence [%]     (0x64 = 100%)

HIL generates this from CarMaker:
  Distance  = CarMaker.Sensor.Radar.0.NearestObject.ds
  RelSpeed  = CarMaker.Sensor.Radar.0.NearestObject.vRel
  Azimuth   = CarMaker.Sensor.Radar.0.NearestObject.az
```

### Camera Lane Data (CAN FD)
```
Lane markings CAN message (ID=0x500, 20 ms cycle):
  Left_lane_offset_m   = CarMaker.Sensor.Camera.0.Lane.Left.Dist
  Right_lane_offset_m  = CarMaker.Sensor.Camera.0.Lane.Right.Dist
  Lane_width_m         = Right - Left
  Curvature_1_per_m    = CarMaker road curvature at current pos

These are packed into CAN signals via DBC and sent by DS1552
to the ADAS ECU — simulating what a real camera ECU would provide.
```

### Video Injection (Advanced HIL)
```
For camera-based ADAS (using raw video, not object list):
  Tool: dSPACE Video Injection (or NVIDIA DRIVE Sim)
  
  Setup:
  1. CarMaker generates 3D scene → rendered to virtual camera
  2. Video stream encoded to MIPI CSI-2
  3. DS5335 Video Injection Board injects MIPI into ECU camera input
  4. ECU processes real video → outputs lane/object data via CAN
  
  Use case: Test camera neural network on realistic video
  Limitation: Requires custom hardware + rendering pipeline (expensive)
```

---

## 5. Instrument Cluster Validation Workflows

### Cluster HIL Architecture
```
Cluster validation setup:
────────────────────────────────────────────────────────────────
┌──────────────────────────────────────────────────────────┐
│  SCALEXIO                                                │
│  ├─ DS1552: CAN restbus (vehicle speed, RPM, fuel, etc.) │
│  ├─ DS2211: Analog (temperature, fuel level sensors)     │
│  └─ DS2680: Digital (door, belt, warning lamp signals)   │
└─────────────────────────┬────────────────────────────────┘
                          │
                   ┌──────▼──────┐
                   │  Cluster    │
                   │  ECU (SUT)  │
                   └──────┬──────┘
                          │ Display output
                   ┌──────▼──────┐
                   │   Physical  │   ← Test engineer visually checks
                   │   Cluster   │   ← or camera + image recognition
                   └─────────────┘
────────────────────────────────────────────────────────────────
```

### Cluster Test Scenarios
```python
class ClusterTestSuite:

    def __init__(self, bench):
        self.bench = bench

    def test_speedometer_accuracy(self):
        """Verify speedometer shows correct speed at 10 test points."""
        test_speeds = [0, 10, 30, 50, 80, 100, 120, 150, 200, 250]
        errors = []

        for v_ref in test_speeds:
            # Set vehicle speed via CAN restbus
            self.bench.set_variable("Restbus.WheelSpeeds.FL", v_ref)
            self.bench.set_variable("Restbus.WheelSpeeds.FR", v_ref)
            self.bench.set_variable("Restbus.WheelSpeeds.RL", v_ref)
            self.bench.set_variable("Restbus.WheelSpeeds.RR", v_ref)
            time.sleep(0.5)  # Cluster settling time

            # Read cluster output (camera OCR or analog needle sensor)
            v_cluster = self.bench.get_variable("Cluster.Speedometer.Display_kmh")
            error = abs(v_cluster - v_ref)
            errors.append(error)
            print(f"v_ref={v_ref} km/h  v_cluster={v_cluster} km/h  err={error:.1f}")

        max_allowed_error_kmh = 5.0  # EU regulation: ±10% + 4 km/h
        assert max(errors) <= max_allowed_error_kmh, \
            f"Speedometer error {max(errors):.1f} > {max_allowed_error_kmh} km/h limit"

    def test_warning_lamp_sequence(self):
        """Verify instrument cluster warning lamps light in correct order."""
        # Simulate ignition on → all lamps on (bulb check)
        self.bench.set_variable("Restbus.Ignition.KL15", 1)
        time.sleep(0.5)  # Bulb check = all lamps on for 3 s

        # Check all critical lamps are ON
        for lamp in ["Lamp.OilPressure", "Lamp.Battery", "Lamp.ABS", "Lamp.Airbag"]:
            state = self.bench.get_variable(f"Cluster.{lamp}")
            assert state == 1, f"Bulb check: {lamp} did not illuminate"

        # After 3 s, all lamps off (assuming no faults)
        time.sleep(3.5)
        for lamp in ["Lamp.OilPressure", "Lamp.Battery", "Lamp.ABS"]:
            state = self.bench.get_variable(f"Cluster.{lamp}")
            assert state == 0, f"Lamp {lamp} still on after bulb check"

    def test_dtc_warning_display(self):
        """Verify cluster shows DTC warning when ECU reports fault."""
        # Simulate engine fault on CAN
        self.bench.set_variable("Restbus.Engine.MIL_Active", 1)
        time.sleep(0.2)

        mil_lamp = self.bench.get_variable("Cluster.Lamp.MIL")
        assert mil_lamp == 1, "MIL lamp did not illuminate on engine fault"

        # Remove fault
        self.bench.set_variable("Restbus.Engine.MIL_Active", 0)
        time.sleep(0.2)
        assert self.bench.get_variable("Cluster.Lamp.MIL") == 0
```

---

## 6. ADAS Warning and Activation Validation

```
ADAS HMI signal chain:
─────────────────────────────────────────────────────────────────────
Physical event         → Sensor → ECU algorithm → HMI output
─────────────────────────────────────────────────────────────────────
Object at TTC 2 s      → Radar  → FCW logic     → Warning buzzer + lamp
Object at TTC 1 s      → Radar  → AEB logic     → Brake + HMI brake icon
Lane departure         → Camera → LDW logic     → Haptic steer / beep
Blind spot occupied    → Radar  → BLIS logic    → Mirror indicator lamp
─────────────────────────────────────────────────────────────────────

Test: FCW alert latency
──────────────────────────────────────────────────────────────────────
1. Set Car.vx = 80 km/h
2. Set TTC = 2.5 s (place target at appropriate distance)
3. Ramp target closer: reduce distance over 1 s
4. Record: timestamp when TTC crosses 2.0 s threshold
5. Record: timestamp when FCW_Warning CAN signal = 1
6. Calculate latency = timestamp_warning - timestamp_threshold_crossed
7. Assert latency < 100 ms (one CAN cycle + one ECU cycle)
──────────────────────────────────────────────────────────────────────
```

---

## 7. Full Regression Workflow (Night Run)

```python
"""
Full ADAS/Cluster overnight regression.
Runs ~150 scenarios, generates HTML report.
"""
import pytest
from pathlib import Path
from datetime import datetime

# Test configuration
SCENARIOS = {
    "aeb_city":     [20, 30, 40, 50],          # km/h speeds
    "aeb_highway":  [60, 70, 80],
    "acc_set":      [60, 80, 100, 120, 130],
    "fcw_latency":  [80, 100, 120],
    "cluster_speed": range(0, 260, 10),
    "fault_inject": ["OpenCircuit_TPS", "CanLoss_Radar", "PowerBrownout"],
}

def main():
    report_dir = Path(f"reports/nightly_{datetime.now():%Y%m%d_%H%M}")
    report_dir.mkdir(parents=True, exist_ok=True)

    # Run all test modules
    exit_code = pytest.main([
        "tests/test_aeb_city.py",
        "tests/test_aeb_highway.py",
        "tests/test_acc.py",
        "tests/test_fcw.py",
        "tests/test_cluster.py",
        "tests/test_fault_injection.py",
        "--html",    str(report_dir / "report.html"),
        "--junit-xml", str(report_dir / "junit.xml"),
        "-v",
        "--tb=short",
        f"--log-file={report_dir}/run.log",
    ])

    print(f"\nReport saved to: {report_dir}/report.html")
    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())
```

---

## 8. Common ADAS HIL Failure Modes

| Failure | Symptom | Root Cause | Fix |
|---------|---------|-----------|-----|
| AEB false positive | Brakes on clear road | Radar noise in simulation | Check sensor model noise config |
| AEB non-activation | No brake at TTC 1.0 s | Wrong radar distance scaling | Verify DS2211 AO scaling |
| FCW late warning | Latency > 200 ms | CAN cycle + 1 extra task delay | Check restbus message rate |
| Cluster speed wrong | Shows 0 km/h always | Wheel speed CAN factor error | Verify DBC signal scaling |
| ACC overshoot | Speed oscillates ±10 km/h | Simulink PID gain calibration | Reduce Kp in CarMaker model |
| Warning lamp stuck | Lamp ON after fault cleared | DTC not cleared via UDS 0x14 | Add ClearDTC step in test |

---

## 9. Interview Q&A

**Q1: How do you set up an ADAS HIL rack for AEB validation?**  
The setup includes: CarMaker running on DS6001 providing vehicle dynamics + radar/camera sensor models; DS1552 sending radar object list and camera lane data as CAN messages to the ADAS ECU; DS4330 for any Ethernet-based sensors; DS2211 for analog sensor stimulation; AutomationDesk orchestrating the scenario execution and collecting pass/fail results. The ECU's brake command output is measured via CAN and compared against Euro NCAP pass criteria.

**Q2: What is the difference between radar object list injection and video injection?**  
Object list injection sends pre-processed CAN messages with target parameters (distance, speed, angle) directly to the ADAS ECU — it bypasses the sensor hardware. Video injection feeds raw camera images into the ECU's MIPI interface, so the ECU's own neural network processes them. Video injection is needed when you're validating the camera processing itself, not just the fusion/decision algorithm.

**Q3: How do you validate an instrument cluster HMI response?**  
The HIL sends all CAN messages the cluster listens to (vehicle speed, engine RPM, fuel level, warning flags) via restbus simulation. Cluster outputs are either measured directly (analog needle sensor, brightness sensor for backlight) or captured with a camera and processed with image recognition (OCR for digital displays). Pass/fail checks the cluster response time, accuracy, and correct lamp state.

**Q4: What is a restbus scenario in ADAS HIL?**  
A restbus scenario defines the CAN signals representing the virtual environment: vehicle speed from wheel speed sensors, engine RPM, gear position, ambient temperature, etc. These are generated by the CarMaker simulation and sent by DS1552 to create a realistic network state. Without restbus, the ECU would enter limp mode or generate spurious DTCs that interfere with ADAS function testing.

**Q5: How do you automate a full Euro NCAP AEB test matrix on HIL overnight?**  
Write an AutomationDesk test suite (or pytest + XIL API) that iterates over all required speed/overlap/target combinations. Each iteration: (1) configure CarMaker TestRun parameters, (2) start simulation, (3) wait for end condition, (4) read collision/impact speed result, (5) apply Euro NCAP scoring formula, (6) log result. Run via Jenkins on the HIL node with scheduled overnight execution. The next morning, the Jenkins report shows total score and any regressions.
