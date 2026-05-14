# 02 — Simulink Integration with CarMaker

> **Tools**: MATLAB/Simulink, IPG CarMaker for Simulink (CM4SL), Embedded Coder  
> **Prerequisites**: CarMaker Basics (01), Simulink experience  
> **Outcome**: Build MIL→SIL→HIL workflow using CM4SL co-simulation

---

## 1. Why Integrate Simulink with CarMaker?

CarMaker provides the **virtual vehicle + environment**, Simulink provides the **SUT (System Under Test)** — typically an ADAS or powertrain controller model:

```
┌──────────────────────────────────────────────────────────────┐
│              CarMaker + Simulink Co-Simulation               │
│                                                              │
│  ┌─────────────────────┐        ┌────────────────────────┐  │
│  │    CarMaker Kernel  │        │   Simulink SUT Model   │  │
│  │                     │ ◄────► │                        │  │
│  │  • Road model       │ signals│  • AEB algorithm       │  │
│  │  • Vehicle dynamics │        │  • ACC controller      │  │
│  │  • Sensor models    │        │  • LKA function        │  │
│  │  • Traffic          │        │  • Calibration params  │  │
│  └─────────────────────┘        └────────────────────────┘  │
│              │                              │                │
│              └──────── XIL Bus API ─────────┘                │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. MIL → SIL → HIL Workflow

```
Development Stage       Execution Platform      Key Question
────────────────────────────────────────────────────────────
MIL (Model-in-Loop)  ← Simulink only (PC)    "Does the algorithm work?"
SIL (Software-in-Loop)← C code on PC          "Does the generated code work?"
PIL (Processor-in-Loop)← C code on target CPU  "Does it run on target HW?"
HIL (Hardware-in-Loop)← Real ECU + dSPACE      "Does it work in the full system?"
VIL (Vehicle-in-Loop) ← Real car + simulation  "Does it work on the road?"

Each step: Same CarMaker TestRun, different SUT wrapper
```

### Step-by-Step Transition
```
1. MIL:
   [Simulink Model] ←→ [CarMaker CM4SL block] on PC
   No code generation. Pure Simulink simulation.

2. SIL:
   [Embedded Coder] → generate C code from Simulink model
   [SIL wrapper] runs generated code in Simulink
   Same CM4SL interface — verify code matches model behavior

3. HIL:
   Flash generated code to ECU
   Connect ECU to dSPACE SCALEXIO I/O boards
   CarMaker runs on real-time OS, ECU receives real signals
```

---

## 3. CarMaker for Simulink (CM4SL) — Architecture

CM4SL is an S-Function block that **embeds CarMaker inside Simulink**:

```
Simulink Model Layout (CM4SL):
────────────────────────────────────────────────────────
┌──────────────────────────────────────────────────────┐
│                   Simulink Model                     │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │         CM4SL Master Block                  │    │
│  │  (CarMaker vehicle + road + sensors run     │    │
│  │   inside this S-Function at each time step) │    │
│  │                                             │    │
│  │  Outputs: Car.vx, Car.ax, Sensor.Radar.*   │    │
│  │  Inputs:  BrakeCmd, ThrottleCmd, SteerAngle │    │
│  └──────────────────┬──────────────────────────┘    │
│                     │                               │
│         ┌───────────▼───────────┐                  │
│         │     ADAS SUT Model    │                  │
│         │  (AEB / ACC / LKA)    │                  │
│         │   ← Your Simulink →   │                  │
│         └───────────────────────┘                  │
└──────────────────────────────────────────────────────┘
```

### CM4SL Block Ports
| Port Direction | Signal | DVA Name |
|----------------|--------|----------|
| Output (CM→SL) | Ego vehicle speed | `Car.vx` |
| Output (CM→SL) | Radar object distance | `Sensor.Radar.0.NearestObject.ds` |
| Output (CM→SL) | Radar object speed | `Sensor.Radar.0.NearestObject.vRel` |
| Input (SL→CM) | Brake pressure demand | `DM.Brake` |
| Input (SL→CM) | Throttle demand | `DM.Gas` |
| Input (SL→CM) | Steering angle demand | `DM.Steer.Ang` |

---

## 4. Setting Up CM4SL — Step by Step

### Step 1: Install CM4SL Toolbox
```matlab
% In MATLAB command window:
cm4sl_setup    % Run IPG's setup script — adds CM4SL to MATLAB path

% Verify:
which cmSetupLib    % Should return path to CarMaker toolbox
```

### Step 2: Create New Simulink Model
```matlab
% Open a new Simulink model
open_system('new_system')

% Add CM4SL Master block from library:
%   Simulink Library Browser → CarMaker → CM4SL Master

% Configure block parameters:
%  - CarMaker project path: /home/user/CarMaker_Projects/ADAS_Test
%  - TestRun: TestRun/AEB_City_30kmh
%  - Sample time: 0.001 (1 kHz)
```

### Step 3: Connect SUT Model
```
CM4SL Outputs → ADAS SUT inputs:
  Car.vx          → AEB.ego_speed
  Radar.ds        → AEB.target_distance
  Radar.vRel      → AEB.target_rel_speed

ADAS SUT outputs → CM4SL inputs:
  AEB.brake_cmd   → DM.Brake
  AEB.alert_flag  → (optional display)
```

### Step 4: Configure DVA in CM4SL
```matlab
% In CM4SL block dialog: "DVA Signals" tab
% Add quantities to log:
CM4SL_DVA_Signals = {
    'Car.vx',      1000,   'ego speed'
    'Car.ax',      1000,   'ego accel'
    'Sensor.Radar.0.NearestObject.ds',  1000, 'radar distance'
    'ADAS.AEB.BrakeActive',             1000, 'AEB state'
};
```

---

## 5. Code Generation with Embedded Coder

After MIL validation, generate production C code:

```matlab
%% Step 1: Configure model for code generation
set_param('AEB_SUT', 'SystemTargetFile', 'ert.tlc');  % Embedded Real-Time target
set_param('AEB_SUT', 'SolverType', 'Fixed-step');
set_param('AEB_SUT', 'FixedStep', '0.001');           % 1 ms step

%% Step 2: Set data types (no dynamic allocation in generated code)
set_param('AEB_SUT', 'DefaultParameterBehavior', 'Inlined');
set_param('AEB_SUT', 'DataInitialization', 'Static');  % No malloc

%% Step 3: Generate code
slbuild('AEB_SUT')
% Output: AEB_SUT_ert_rtw/
%   AEB_SUT.c      ← Model step function
%   AEB_SUT.h      ← Header with I/O struct definitions
%   AEB_SUT_data.c ← Calibration data
%   rtwtypes.h     ← Fixed-width types

%% Step 4: SIL verification
set_param('AEB_SUT/AEB_Controller', 'SimulationMode', 'Software-in-the-loop (SIL)');
sim('AEB_SUT')  % Runs generated code, compares to MIL output
```

### Generated Code Structure
```c
/* AEB_SUT.h — auto-generated by Embedded Coder */
#ifndef AEB_SUT_H
#define AEB_SUT_H

#include "rtwtypes.h"

/* External inputs (root inport signals) */
typedef struct {
    real32_T ego_speed;        /* Car.vx [m/s] */
    real32_T target_distance;  /* Radar.ds [m] */
    real32_T target_rel_speed; /* Radar.vRel [m/s] */
} ExtU_AEB_SUT_T;

/* External outputs (root outport signals) */
typedef struct {
    real32_T brake_cmd;        /* Brake pressure [bar] */
    uint8_T  alert_flag;       /* 0=off, 1=warn, 2=brake */
} ExtY_AEB_SUT_T;

/* Model entry points */
extern void AEB_SUT_initialize(void);
extern void AEB_SUT_step(void);
extern void AEB_SUT_terminate(void);

extern ExtU_AEB_SUT_T AEB_SUT_U;
extern ExtY_AEB_SUT_T AEB_SUT_Y;

#endif
```

---

## 6. MATLAB TestManager for Batch Execution

```matlab
% Create a test suite with multiple CarMaker TestRuns
import matlab.unittest.TestSuite;

% Define test scenarios as a parameter sweep
speeds = [20, 30, 40, 50];          % km/h
ttc_thresholds = [1.5, 2.0, 2.5];  % seconds
results = table();

for i = 1:length(speeds)
    for j = 1:length(ttc_thresholds)
        % Set parameters in CarMaker via DVA
        cm_set('Car.vx', speeds(i)/3.6);
        cm_set('ADAS.AEB.TTCThreshold', ttc_thresholds(j));

        % Run simulation
        cm_sim('TestRun/AEB_City');

        % Collect result
        brake_active = cm_get('ADAS.AEB.BrakeActive');
        results(end+1,:) = {speeds(i), ttc_thresholds(j), brake_active};
    end
end

results.Properties.VariableNames = {'Speed_kmh','TTC_s','BrakeActive'};
writetable(results, 'aeb_sweep_results.csv');
disp(results);
```

---

## 7. Common CM4SL Issues and Fixes

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| CM4SL block shows red X | CarMaker project path wrong | Check `cmSetupLib` path in block params |
| Simulation runs slow | Too many DVA signals logged | Reduce DVA quantity count or lower sample rate |
| SIL vs MIL output mismatch | Data type overflow in generated code | Use `int32` not `int16` for intermediate calculations |
| Overrun in real-time | Step function too slow | Profile with `tic/toc`, optimize Simulink model |
| CM4SL port mismatch | Signal count changed in CM version | Re-run `cmUpdateLib` after CM update |

---

## 8. Interview Q&A

**Q1: What is CM4SL?**  
CM4SL (CarMaker for Simulink) is an S-Function toolbox that embeds the CarMaker simulation kernel inside a Simulink model block, allowing the vehicle/environment model (CarMaker) and the controller algorithm (Simulink) to co-simulate step-by-step at the same sample rate.

**Q2: What is the difference between MIL and SIL?**  
MIL runs the Simulink block diagram interpreted (no code generation); SIL compiles the model to C code with Embedded Coder and runs that C code in Simulink. SIL validates that the generated production code behaves identically to the design model.

**Q3: Why do you need a fixed-step solver for HIL?**  
Real-time systems advance by fixed wall-clock ticks (e.g., 1 ms). A variable-step solver can't guarantee when the next step fires, causing missed deadlines and overruns. Fixed-step solver with step size matching the real-time task period ensures deterministic execution.

**Q4: What is Embedded Coder and why is it used in automotive?**  
Embedded Coder generates MISRA-C-compliant, no-dynamic-allocation C code from Simulink models. It produces a deterministic `model_step()` function callable by the RTOS scheduler, making it suitable for safety-critical automotive ECUs (ASIL-B/D).

**Q5: How do you verify SIL matches MIL after code generation?**  
Run the same test scenario in both MIL and SIL mode with identical inputs. Compare output signals numerically — typical acceptance: absolute difference < 1e-6 (float precision). Simulink's `SIL/PIL Manager` automates this comparison and generates a compliance report.
