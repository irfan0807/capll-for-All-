# 04 — Simulation Methods for ADAS Validation

> **Topic**: SIL, MIL, HIL, scenario-based testing, sensor simulation, digital twin  
> **Tools**: CarMaker, Prescan, MATLAB/Simulink, dSPACE, ROS2/CARLA  
> **Outcome**: Know when to use which simulation method, how to design scenarios, and how to scale testing

---

## 1. Why Simulation?

```
The combinatorial problem:
──────────────────────────────────────────────────────────────────────────
ADAS validation requires testing millions of scenarios.
Physical testing is impossible at scale.

Real vehicle test:       $5,000/day, 1 scenario/hour = 1,000 scenarios/year
HIL simulation:          $500/day, 3 scenarios/min = 1,000,000/year
SIL simulation:          $5/hour, 1 scenario/second = 30,000,000/year
Monte Carlo simulation:  Automated, statistical coverage

A self-driving car needs ~10 billion miles of validation
(RAND Corp estimate) — physical testing impossible.
──────────────────────────────────────────────────────────────────────────

Simulation does NOT replace real testing — it:
  1. Catches 90% of bugs before real ECU arrives (saves rework)
  2. Enables edge case exploration (impossible on road)
  3. Scales regression to thousands of variants overnight
  4. Provides repeatable, deterministic scenarios
```

---

## 2. The Simulation Hierarchy

```
                                   Cost / Realism
                               ──────────────────────►
                     MIL          SIL          HIL           VIL / Road
                      │            │            │               │
Algorithm design ──── │            │            │               │
SW code tested ───────────── │    │            │               │
ECU HW tested ────────────────────────── │     │               │
Bus protocols ───────────────────────────────── │              │
Real sensors ─────────────────────────────────────────────── │ │
Real weather ────────────────────────────────────────────────────── │

Simulation fidelity
  Low ──────────────────────────────────────────────────────► High

Simulation speed
  Fast ──────────────────────────────────────────────────── Slow
  (1000× real time)                                         (real time)
```

### MIL — Model-in-Loop
```
Definition: Simulink algorithm model running in pure software simulation
            No code generation, no real hardware

When to use:
  - Early algorithm development
  - Quick parameter sweeps (1000 variants in 1 hour)
  - Unit/module level testing

What you test:
  - Algorithm logic correctness
  - Control loop stability
  - Parameter sensitivity

What you CANNOT test:
  - Real-time timing
  - CAN bus behavior
  - ECU hardware behavior
  - Sensor model accuracy
```

### SIL — Software-in-Loop
```
Definition: Generated C code (or pre-compiled ECU SW) running in simulation
            on PC. No real ECU hardware. Real software, fake hardware.

When to use:
  - After code generation from Simulink
  - Large regression suites (run in parallel on CI server farm)
  - Before ECU hardware is available

What you test:
  - Generated code correctness vs model
  - Software integration (multiple components)
  - CAN message encoding/decoding (with CAPL or Python)
  - DTC logic

What you CANNOT test:
  - Real-time timing (no hard deadline)
  - Real ECU hardware faults
  - Multi-ECU interaction (unless simulated)
```

### HIL — Hardware-in-Loop
```
Definition: Real ECU connected to simulation environment.
            Real hardware + real timing + simulated environment.

When to use:
  - System-level validation (primary)
  - Euro NCAP scenario testing
  - Fault injection
  - Before vehicle integration

What you test:
  - Everything: algorithm + code + HW + timing + bus
  - Real bus protocols (CAN FD, LIN, Ethernet)
  - ECU bootloader and flash
  - Supply voltage faults
  - Thermal behavior

What you CANNOT test:
  - Real sensor hardware (radar/camera) behavior
  - Road surface forces (unless full motion-base HIL)
  - Real-world weather effects
```

### VIL — Vehicle-in-Loop
```
Definition: Real car connected to real-time simulation.
            Car drives on chassis dynamometer while simulation 
            generates virtual environment.

When to use:
  - Before proving ground (bridging HIL to road)
  - Reproducible scenarios with real vehicle dynamics
  - Certification testing in controlled environment

What you test:
  - Full vehicle system with all ECUs
  - Real actuator dynamics (brake hydraulics, EPS)
  - Multi-ECU network behavior
  - Calibration validation
```

---

## 3. Scenario-Based Testing

### What Is a Test Scenario?
```
A scenario = an ADAS test situation defined by:
  ┌──────────────────────────────────────────────────────────┐
  │ Scenario Components                                      │
  │                                                          │
  │  Road layout:   straight / curve / intersection          │
  │  Weather:       dry / rain / fog / snow                  │
  │  Lighting:      day / dusk / night / headlights          │
  │  Ego vehicle:   speed, initial position, gear            │
  │  Traffic:       other vehicle positions, speeds          │
  │  Pedestrians:   walking path, speed, age profile         │
  │  Road surface:  μ = 1.0 (dry) / 0.6 (wet) / 0.2 (ice)  │
  │  Pass/fail:     collision? warning triggered? speed?     │
  └──────────────────────────────────────────────────────────┘
```

### Scenario Taxonomy
```
Scenario database structure:
──────────────────────────────────────────────────────────────────────────
Level 1: Functional Scenarios
  "The ego vehicle approaches a stationary object on a straight road."
  Abstract description, no exact parameters.

Level 2: Logical Scenarios
  "Ego speed ∈ [20–80] km/h, object type ∈ {car, pedestrian, cyclist},
   visibility ∈ [50–∞] m, road condition ∈ {dry, wet}"
  Parameter ranges, not specific values.

Level 3: Concrete Scenarios
  "Ego speed = 40 km/h, stationary car target, visibility = unlimited,
   dry road. Placed at 60 m ahead at t=0."
  Exact, runnable scenario.

Level 4: Executed Scenario
  Concrete scenario + actual results recorded.
  "Pass: AEB activated at TTC=1.18 s, no collision."
──────────────────────────────────────────────────────────────────────────
```

### Scenario Database (YAML format)
```yaml
# scenarios/aeb_city/CCRs_40kmh.yaml
scenario_id:    SCN-AEB-007
standard:       Euro NCAP 2026
category:       AEB City — CCRs (Car-to-Car Rear Stationary)
description:    Ego approaches stationary target at 40 km/h

road:
  type:         straight
  length_m:     500
  width_m:      3.65
  surface:      dry
  friction_mu:  1.0

weather:
  condition:    clear
  visibility_m: unlimited
  temperature:  20

ego_vehicle:
  model:        passenger_car
  mass_kg:      1650
  initial_speed_kmh: 40
  initial_position:
    x_m: 0.0
    lane: center

traffic:
  - id:          GVT_01
    type:        GVT            # Global Vehicle Target (Euro NCAP spec)
    speed_kmh:   0              # stationary
    initial_position:
      x_m: 80.0                 # 80 m ahead
      lane: center
    dimensions:
      length_m: 4.2
      width_m:  1.8

pass_criteria:
  - metric:     collision_occurred
    operator:   "=="
    value:      false
    description: No collision
  - metric:     aeb_brake_active_at_any_point
    operator:   "=="
    value:      true
    description: AEB must have activated
```

### Loading Scenario in Python/CarMaker
```python
import yaml

def load_and_run_scenario(carmaker_client, scenario_file: str) -> dict:
    """Load scenario YAML and execute in CarMaker."""
    with open(scenario_file) as f:
        scn = yaml.safe_load(f)

    cm = carmaker_client

    # Configure ego
    cm.set("Car.vx", scn["ego_vehicle"]["initial_speed_kmh"] / 3.6)

    # Configure traffic (target object)
    for obj in scn["traffic"]:
        cm.set(f"Traffic.Obj[0].PosLong", obj["initial_position"]["x_m"])
        cm.set(f"Traffic.Obj[0].vx",      obj["speed_kmh"] / 3.6)

    # Configure environment
    cm.set("Weather.Rain",        0 if scn["weather"]["condition"] == "clear" else 1)
    cm.set("Road.FrictionScale",  scn["road"]["friction_mu"])

    # Start simulation
    cm.start_testrun("TestRun/AEB_Generic")
    cm.wait_for_end(timeout=30.0)

    # Collect results
    results = {
        "scenario_id": scn["scenario_id"],
        "collision_occurred": cm.get("Collision.Occurred") > 0.5,
        "aeb_brake_active":   cm.get("ECU.AEB.MaxBrakeActive") > 0.5,
        "min_ttc":            cm.get("Sensor.Radar.MinTTC"),
        "impact_speed_kmh":   cm.get("Collision.ImpactSpeed") * 3.6,
    }

    # Evaluate pass criteria
    passed = True
    for criterion in scn["pass_criteria"]:
        val = results.get(criterion["metric"])
        exp = criterion["value"]
        ok = eval(f"{val!r} {criterion['operator']} {exp!r}")
        if not ok:
            print(f"  FAIL: {criterion['description']} "
                  f"(got {val}, expected {criterion['operator']} {exp})")
            passed = False

    results["passed"] = passed
    return results
```

---

## 4. CarMaker Sensor Models

CarMaker provides virtual sensor models that feed the ADAS ECU in SIL/HIL:

### Radar Model
```
CarMaker Radar Model characteristics:
───────────────────────────────────────────────────────────────────────
Parameter          Typical Value      Notes
───────────────────────────────────────────────────────────────────────
Max range          250 m              LRR radar
Azimuth FOV        ±9° (LRR)          ±60° for SRR
Range resolution   0.1 m              Depends on bandwidth
Velocity resolution 0.05 m/s          Doppler resolution
Update rate        10–20 Hz           Depends on sensor
Noise model        Gaussian           σ_range = 0.05 m
Object model       Point + box        Extended object model optional
Multipath          Not modeled*       *Available in Prescan/SensorSim
───────────────────────────────────────────────────────────────────────

What CarMaker radar DOES model:
  ✓ Line-of-sight occlusion (object hidden behind another)
  ✓ Object list output (range, velocity, azimuth, classification)
  ✓ Mounting position / orientation on vehicle
  ✓ FOV limits
  ✓ Configurable Gaussian noise

What it does NOT model (use Prescan/IPG VTD for these):
  ✗ FMCW signal physics
  ✗ Multipath reflections from ground/guardrail
  ✗ Rain attenuation
  ✗ RCS variation with angle
```

### Camera Model
```
CarMaker Camera Model:
───────────────────────────────────────────────────────────────────────
Output type:   Semantic (object list + lane data), NOT raw video
               For raw video: use CarMaker MovieDesk + rendering
───────────────────────────────────────────────────────────────────────

Camera sensor config (.cam file):
  Resolution:    1920 × 1080 (virtual)
  FOV:           52° horizontal, 32° vertical
  FocalLength:   8 mm equivalent
  MountPos:      windshield center, h=1.2m, pitch=-2°

Lane outputs (CarMaker DVA):
  Sensor.Camera.0.Lane.Left.Dist    ← distance to left lane [m]
  Sensor.Camera.0.Lane.Right.Dist   ← distance to right lane [m]
  Sensor.Camera.0.Lane.Curvature    ← road curvature [1/m]
  Sensor.Camera.0.Lane.HeadingAngle ← angle to lane center [rad]

Object outputs:
  Sensor.Camera.0.Object[N].Type    ← Car/Pedestrian/Cyclist
  Sensor.Camera.0.Object[N].ds      ← distance [m]
  Sensor.Camera.0.Object[N].vy      ← lateral velocity [m/s]
```

---

## 5. Monte Carlo Simulation

Monte Carlo testing systematically samples the parameter space to find edge cases:

```python
"""
Monte Carlo AEB scenario sweep.
Tests 5000 random scenarios to find failure conditions.
"""
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor

def run_single_scenario(params: dict) -> dict:
    """Run one AEB scenario with given parameters."""
    # Import here to avoid pickling issues
    from carmaker_client import CarMakerClient
    cm = CarMakerClient()

    cm.set("Car.vx", params["speed_ms"])
    cm.set("Traffic.Obj[0].PosLong", params["initial_dist"])
    cm.set("Traffic.Obj[0].vx", params["target_speed_ms"])
    cm.set("Road.FrictionScale", params["friction"])

    cm.start_testrun("TestRun/AEB_Generic_MC")
    cm.wait_for_end(30)

    return {
        **params,
        "collision": cm.get("Collision.Occurred") > 0.5,
        "aeb_fired": cm.get("ECU.AEB.MaxBrakeActive") > 0.5,
        "impact_speed": cm.get("Collision.ImpactSpeed"),
    }

# Define parameter distributions
N = 5000
rng = np.random.default_rng(seed=42)

parameter_sets = [{
    "speed_ms":        rng.uniform(5.0, 22.0),     # 18–80 km/h
    "initial_dist":    rng.uniform(20.0, 80.0),    # m
    "target_speed_ms": rng.uniform(-8.0, 0.0),     # stationary to 28 km/h ahead
    "friction":        rng.choice([1.0, 0.8, 0.6, 0.3],  # dry/wet/snow/ice
                                  p=[0.6, 0.2, 0.15, 0.05]),
} for _ in range(N)]

# Run in parallel (multiple CarMaker instances)
with ProcessPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(run_single_scenario, parameter_sets))

df = pd.DataFrame(results)
collisions = df[df["collision"]]

print(f"Total scenarios: {N}")
print(f"Collisions: {len(collisions)} ({len(collisions)/N*100:.1f}%)")
print(f"\nCollision parameter analysis:")
print(collisions[["speed_ms","initial_dist","target_speed_ms","friction"]].describe())

# Find failure boundary
print("\nCollision at low friction:")
low_friction_fails = collisions[collisions["friction"] < 0.5]
print(f"  {len(low_friction_fails)} collisions on slippery surface")
```

---

## 6. Prescan — Advanced Sensor Simulation

For physics-accurate sensor simulation, Prescan/SensorSim is used instead of CarMaker's basic models:

```
Prescan capabilities (vs CarMaker):
──────────────────────────────────────────────────────────────────────────
Feature                    CarMaker          Prescan
──────────────────────────────────────────────────────────────────────────
Radar physics              Object list only  FMCW signal processing
Radar multipath            No                Yes
Camera raw video           Optional          Full GPU rendering
LiDAR point cloud          Object list       Full point cloud (100k pts)
Weather effects            None              Rain, fog, snow attenuation
Road surface texture       None              RCS / reflectance maps
Sensor noise realism       Gaussian          Physics-based models
Co-simulation with Simulink Yes              Yes (Prescan + Simulink)
Co-simulation with CarMaker Tight integration Loose coupling via FMI
──────────────────────────────────────────────────────────────────────────

Typical use case:
  CarMaker = vehicle dynamics + traffic scenarios
  Prescan  = radar/camera/LiDAR physics
  Combined via co-simulation interface (Simulink FMU)
```

---

## 7. OpenSCENARIO and ASAM Standards

OpenSCENARIO 2.0 is becoming the standard for scenario description:

```xml
<!-- OpenSCENARIO 2.0 — AEB city scenario -->
<OpenSCENARIO>
  <FileHeader description="AEB City CCRs 40km/h"
              author="TestEng" revMajor="1" revMinor="0"/>

  <RoadNetwork>
    <LogicFile filepath="roads/highway_straight.xodr"/>
  </RoadNetwork>

  <Entities>
    <ScenarioObject name="Ego">
      <Vehicle name="passenger_car" vehicleCategory="car"/>
    </ScenarioObject>
    <ScenarioObject name="GVT_Target">
      <Vehicle name="gvt_car" vehicleCategory="car"/>
    </ScenarioObject>
  </Entities>

  <Storyboard>
    <Init>
      <Actions>
        <!-- Ego starts at 40 km/h -->
        <EntityAction entityRef="Ego">
          <AbsoluteTargetSpeed value="11.11"/>  <!-- m/s -->
        </EntityAction>
        <!-- Target stationary at 80 m ahead -->
        <EntityAction entityRef="GVT_Target">
          <AbsoluteTargetSpeed value="0.0"/>
          <Position><LanePosition roadId="0" laneId="-1" s="80.0"/></Position>
        </EntityAction>
      </Actions>
    </Init>

    <Story name="AEB_Story">
      <Act name="approach">
        <StartTrigger>
          <ConditionGroup>
            <Condition name="SimStart" delay="0" conditionEdge="none">
              <ByValueCondition>
                <SimulationTimeCondition value="0.0" rule="greaterThan"/>
              </ByValueCondition>
            </Condition>
          </ConditionGroup>
        </StartTrigger>
      </Act>
    </Story>

    <StopTrigger>
      <ConditionGroup>
        <Condition name="CollisionOrTimeout">
          <ByValueCondition>
            <SimulationTimeCondition value="15.0" rule="greaterThan"/>
          </ByValueCondition>
        </Condition>
      </ConditionGroup>
    </StopTrigger>
  </Storyboard>
</OpenSCENARIO>
```

---

## 8. Simulation Coverage Metrics

```
Simulation coverage concepts:
──────────────────────────────────────────────────────────────────────────
Scenario coverage:      % of defined scenarios that have been run
  Target: 100% of requirements-driven scenarios

Parameter coverage:     % of parameter space covered
  Use combinatorial testing (pairwise = N² coverage with N^K combinations)

ODD coverage:           % of ODD boundaries tested
  All min/max/nominal for each ODD parameter

Sensor failure coverage: % of sensor failure modes tested
  Each DTC trigger condition tested at least once

Code coverage (SIL):    Line/branch/MC/DC coverage %
  Target: 90% MC/DC for ASIL C/D modules
──────────────────────────────────────────────────────────────────────────
```

---

## 9. Interview Q&A

**Q1: What is the difference between MIL, SIL, and HIL? When do you use each?**  
MIL (Model-in-Loop) runs the Simulink algorithm model with no code generation — used in early development for algorithm design and quick parameter sweeps. SIL (Software-in-Loop) runs generated C code on a PC — used to verify the code matches the model, and for large overnight regression suites on CI servers. HIL (Hardware-in-Loop) uses the real ECU connected to a simulation environment — used for system-level testing including real timing, bus protocols, and hardware interaction.

**Q2: What is Monte Carlo simulation in the ADAS context?**  
Monte Carlo randomly samples the ADAS parameter space (ego speed, target distance, weather, surface friction) and runs thousands of simulations to find conditions where the system fails. This statistically covers the parameter space much more efficiently than manual test case design and is essential for SOTIF validation — finding the unknown failure conditions at ODD boundaries.

**Q3: What is OpenSCENARIO and why is it important?**  
OpenSCENARIO (ASAM standard) is a vendor-neutral XML format for describing traffic scenarios. It enables scenario portability: write the scenario once, run it in CarMaker, CARLA, Prescan, or any compatible simulator. This is important because teams often switch simulation tools, and standardized scenarios can be shared between OEMs, suppliers, and certification bodies.

**Q4: What does CarMaker's radar model simulate vs what it doesn't?**  
CarMaker's radar model simulates: line-of-sight occlusion, object list output with configurable Gaussian noise, field-of-view masking, and mounting position effects. It does NOT simulate: FMCW signal physics, multipath reflections, rain/fog attenuation, or realistic RCS variation with target angle. For physics-accurate radar simulation, you need Prescan/SensorSim or dSPACE ModelFidelity.

**Q5: How do you ensure your simulation results are valid and trust them for release decisions?**  
Simulation validation requires: (1) model correlation — compare HIL results with real vehicle measurements to quantify model error; (2) sensor model accuracy — compare virtual sensor outputs against real sensor recordings in the same scenario; (3) clear scope statements — explicitly document what the simulation can and cannot predict. Simulation results are trusted within the validated model scope; beyond that, real vehicle tests are required.
