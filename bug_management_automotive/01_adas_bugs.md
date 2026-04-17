# ADAS — Bug Reproduction, Reporting, Resolving & Diagnostics

> **Domain**: Advanced Driver Assistance Systems
> **Sensors**: Radar (77 GHz) · Camera (Mono/Stereo) · Ultrasonic · LiDAR
> **Features**: AEB · LKA · ACC · BSD · LCA · PDC · TSR · AVM

---

## 1. Bug Categories in ADAS

| Category | Description | Example |
|---------|-------------|---------|
| False Positive | Feature activates when it should NOT | AEB brakes on a clear road; LKA steers on a straight road |
| False Negative | Feature does NOT activate when it SHOULD | AEB fails to brake for pedestrian; BSD misses a vehicle |
| Intermittent | Works sometimes, fails sometimes — hardest to fix | AEB activates randomly only on wet roads |
| Calibration Error | Sensor position, angle or gain incorrect | Radar reports object 2 m in front of actual position |
| Sensor Fusion Bug | Fusion incorrectly combines sensor data | Camera says "no object"; radar says "object"; fusion follows wrong sensor |
| CAN Signal Bug | ADAS output signals wrong on bus | AEB_Active bit never set to 1 even when braking occurs |
| Mode Transition Bug | Feature state machine incorrect | ACC stuck in HOLD state after speed resumes |
| Performance Bug | Feature works but too slow | AEB reacts in 600 ms; spec requires ≤ 300 ms |

---

## 2. Bug Scenario 1 — AEB False Activation on Metal Bridge

### Bug Description
**Title:** AEB triggers emergency braking at 80 km/h with no obstacle present  
**Severity:** P1 — Safety Critical  
**Reported by:** Field test driver  
**Frequency:** 3 occurrences, same location (motorway bridge near Frankfurt)

### Reproduction Steps
```
Environment:
  Vehicle speed: 80 km/h
  Road: Motorway (2-lane)
  Obstacle: None ahead
  Weather: Dry, clear
  Location: Approaching a steel overhead road bridge (span across motorway)

Steps:
  1. Drive at constant 80 km/h in right lane
  2. Approach the overhead metal bridge
  3. Observe: AEB activates — full braking, ≈ 4 m/s² deceleration
  4. Vehicle brakes for 1.5 s then releases (no contact)
```

### Reproduction on HIL Bench
```
dSPACE SCALEXIO HIL bench:
  1. Set host speed = 80 km/h (via vehicle model)
  2. Inject radar ghost target via CAPL:
       - Object type: stationary
       - Relative velocity: 0 m/s (Doppler = 0)
       - Range: 40 m
       - Azimuth: 0° (straight ahead)
       - RCS (Radar Cross Section): 20 dBm² (large metallic object: bridge)
  3. Run AEB algorithm
  4. Observe: AEB activates at TTC = 40/(80/3.6) = 1.8 s ← below 2 s threshold
  → Reproduced on bench ✓
```

### Diagnostics — CANoe Signal Trace
```
Signal: RadarObject_01_RelVelocity = 0.0 m/s  ← stationary
Signal: RadarObject_01_Range      = 40.0 m
Signal: AEB_BrakeRequest         = 1  ← activated
Signal: Camera_ObjectValid        = 0  ← camera sees NO object (bridge overhead, not in FOV)

Finding:
  - Radar detects bridge girder (RCS = large metallic)
  - Camera does NOT see it (bridge is above camera FOV)
  - AEB fusion logic: if radar object present AND TTC < 2s → activate (camera NOT mandatory)
  - Bug: stationary objects with Doppler = 0 at speed > 60 km/h should be filtered
           (they are overwhelmingly infrastructure, not vehicles)
```

### Root Cause
AEB's stationary object suppression filter was tuned for low-speed urban scenarios. At highway speeds (> 60 km/h), the filter threshold was not applied — the AEB treated all stationary radar returns as potential stopped vehicles.

### Fix
```
Algorithm change:
  IF host_speed > 60 km/h AND object_relative_velocity == 0 m/s:
    Require camera confirmation (camera_object_valid == 1) before AEB activation
    If camera does not confirm: suppress brake request
    
  Test: 1000 SIL scenarios — stationary object at 40 m, 80 km/h, no camera confirmation
  Expected: 0 AEB activations
  Result: 0 activations ✓ (false positive eliminated)
  
  Regression test: pedestrian at 30 km/h (moving, Doppler ≠ 0): still activates ✓
```

### Reporting Template (JIRA)
```
Summary: [ADAS][AEB] False emergency braking on metal overhead bridge at 80 km/h

Preconditions:
  - SW: v4.2.1
  - Radar: Continental ARS540
  - Speed: 80 km/h
  - Environment: Metal bridge overhead

Steps to Reproduce:
  1. Drive at 80 km/h approaching steel overhead bridge (or simulate on HIL per bench guide §3.2)
  2. Observe AEB activation

Actual: Vehicle brakes hard at 80 km/h with no obstacle present
Expected: No braking — Radar echo from stationary bridge should be suppressed above 60 km/h

Severity: P1 — Safety (false activation at speed can cause rear-end collision)
Attachments: CANoe_trace_AEB_false_80kmh.blf, dSPACE_replay_bridge.zip
```

### Recurring Bug Watch
> **⚠ Recurrence Risk:** This bug can reappear after algorithm parameter tuning.
> Any change to AEB threshold tables must be followed by re-running the full 
> "stationary object" test suite (1000 SIL scenarios + 5 physical locations).

---

## 3. Bug Scenario 2 — AEB Does Not Activate for Pedestrian at Night

### Bug Description
**Title:** AEB (pedestrian mode) fails to activate for pedestrian in low-light conditions  
**Severity:** P1  
**Trigger condition:** Low ambient light (< 5 lux), pedestrian crossing at 90° angle to vehicle path

### Reproduction Steps
```
Conditions:
  - Vehicle speed: 40 km/h
  - Ambient light: < 5 lux (night driving simulation)
  - Pedestrian: crossing at 90° (left to right, 15 m ahead)
  - Camera: low-light camera (Sony IMX490)
  
Bench reproduction (HIL + camera simulation):
  1. Set ambient light model to 2 lux
  2. Inject camera object: type=pedestrian, crossing_angle=90°, speed=5 km/h
  3. Inject radar object: type=small target, range=15m, azimuth=0°, rel_vel=-11.1m/s
  4. Run AEB algorithm
  5. Observe: AEB does NOT activate
```

### Diagnostics
```
CANoe trace:
  Camera_ObjectType         = UNKNOWN (not PEDESTRIAN — classification failed in low light)
  Camera_Confidence         = 42% (below 60% threshold for pedestrian classification)
  Radar_ObjectType          = POINT_TARGET (radar cannot classify pedestrian vs. bicycle)
  AEB_PedestrianMode        = INACTIVE (requires camera confidence ≥ 60% for pedestrian type)
  AEB_VehicleMode           = INACTIVE (radar type = POINT_TARGET, not VEHICLE)
  AEB_BrakeRequest          = 0 ← No activation
  
Root cause:
  Night + crossing angle → camera confidence drops
  AEB pedestrian path requires camera confidence ≥ 60% — tuned for daytime
  At night, camera confidence = 42% → AEB skips pedestrian check
  Radar alone: cannot confirm pedestrian type → vehicle mode also not triggered
  Result: genuine pedestrian missed
```

### Fix
```
Two-part fix:
  1. Lower camera confidence threshold for pedestrian detection at night:
       IF ambient_light < 10 lux AND camera_conf > 35% → treat as low-confidence pedestrian
  2. Add cross-validation: if radar small target + camera low-confidence pedestrian → 
       apply conservative braking (50% of full AEB) as warning/pre-fill
       
Validation:
  Euro NCAP Night Pedestrian scenario: AEB Child (VRU-Ped-2-CPNCO):
    Before fix: 0 points (0/3 speeds: missed)
    After fix:  2.5 points (activated at 30 and 40 km/h)
```

### Recurring Bug Watch
> **⚠ Recurrence Risk:** Camera confidence thresholds are tuned parameters in ECU NVM.
> After any ECU recalibration, camera firmware update, or sensor replacement:
> Re-run full Euro NCAP night pedestrian test suite.
> Add to release checklist: "Night AEB test: mandatory after any camera SW change."

---

## 4. Bug Scenario 3 — Lane Keep Assist Drifts Right on Sun Glare

### Bug Description
**Title:** LKA applies unintended left-steering correction when driving into direct sun glare  
**Severity:** P2  
**Trigger:** Sunrise/sunset driving (low angle sun directly into camera FOV)

### Reproduction Steps
```
Conditions:
  Vehicle: Highway, straight road, centre of lane
  Camera: Front mono camera (lane detection camera)
  Sun angle: Low (5–15° above horizon, directly ahead)

Bench reproduction:
  1. In camera simulation tool (dSPACE Aurelion): inject image with strong sun glare at 10° elevation
  2. Apply to standard highway lane image
  3. Run LKA lane detection algorithm
  4. Observe lane detection output and steering demand

Observation:
  - LKA detects phantom left lane marking (sun reflection on road surface)
  - LKA calculates vehicle position as 30 cm to the right of the phantom lane
  - Applies left correction: +10 Nm steering torque
  - Actual vehicle drifts left → potential lane departure
```

### Diagnostics
```
LKA debug signals (CANoe):
  LKA_LaneLeft_Confidence   = 72%  ← erroneously high (phantom line)
  LKA_LaneRight_Confidence  = 88%  ← normal (real right lane marking)
  LKA_LateralOffset         = +0.32 m (vehicle appears right of centre due to phantom left line)
  LKA_SteeringRequest       = -10 Nm (left correction)
  LKA_Active                = 1
  
Camera raw image: sun reflection creates bright horizontal band → lane detection algorithm 
                   interprets bright gradient as left lane marking
```

### Fix
```
Image pre-processing:
  - Add sun glare suppression filter: detect saturated pixels (> 250/255) in lane ROI (Region of Interest)
  - If saturated area > 20% of ROI: flag lane_confidence_valid = FALSE for affected side
  - LKA: if lane_confidence_valid = FALSE for either side → reduce LKA correction authority by 70%
  
Validation:
  100 simulated glare scenarios at 5°/10°/15°/20° sun elevation:
    Before fix: 67% false correction rate
    After fix:  3% (acceptable — natural image variation)
```

### Recurring Bug Watch
> **⚠ Recurrence Risk:** New camera firmware, ISP (Image Signal Processor) tuning changes,
> or lens aperture changes can alter glare behaviour.
> Mandatory test: "Sun glare LKA validation" in every camera-related software drop.

---

## 5. Bug Scenario 4 — ACC Does Not Resume After Speed Resumes Post-Brake

### Bug Description
**Title:** Adaptive Cruise Control stuck in STANDBY after driver brakes and releases — does not resume automatically  
**Severity:** P2  
**Trigger:** ACC set → driver applies brake briefly (speed bump) → releases brake → ACC stays in STANDBY

### State Machine Analysis
```
ACC Normal State Machine:
  [ACTIVE] → driver brakes → [OVERRIDE/STANDBY] 
  → driver releases brake → [RESUME REQUEST]
  → driver presses RESUME button OR speed > threshold → [ACTIVE]
  
Bug: [OVERRIDE/STANDBY] → driver releases brake → [STANDBY] (not RESUME REQUEST)
  ACC_State never transitions back to RESUME REQUEST
  Driver must fully re-engage ACC manually
  
CANoe trace:
  ACC_State = ACTIVE (T=0)
  BrakePedal_Active = 1 (T=2.1s) → ACC_State = STANDBY (T=2.1s) ✓ correct
  BrakePedal_Active = 0 (T=2.8s) → ACC_State = STANDBY (T=2.8s) ← BUG (should → RESUME_PENDING)
  
  Expected: after BrakePedal_Active = 0, if set_speed still stored:
              ACC_State → RESUME_PENDING → if no further driver input: → ACTIVE
```

### Root Cause
```
State machine transition condition (from code review):
  Current buggy code:
    if (brake_released AND speed > 30 AND prev_state == OVERRIDE) {
      state = RESUME_PENDING;
    }
    
  Bug: prev_state checked is OVERRIDE but state was set to STANDBY (not OVERRIDE)
  when brake was applied — enumeration inconsistency:
    OVERRIDE (= 3) used during active deceleration
    STANDBY  (= 4) used when speed < 30 km/h during brake
  The resume condition checked OVERRIDE but vehicle was in STANDBY → condition never true
```

### Fix
```c
// Fixed condition:
if (brake_released && speed > 30 &&
   (prev_state == OVERRIDE || prev_state == STANDBY)) {
  state = RESUME_PENDING;
}
```

### Recurring Bug Watch
> **⚠ Recurrence Risk:** State machine bugs in ACC/ADAS are extremely common after
> any re-numbering of enumerated states or refactoring of state variables.
> Every ACC state machine change must be followed by:
>   - State transition test: all 12 transitions (CAPL automated)
>   - Edge case: brake + gas simultaneously, brake + speed < 30, rapid brake/release

---

## 6. Bug Scenario 5 — Rear Radar Shows Ghost Objects After Car Wash

### Bug Description
**Title:** Rear BSD/LCA radar detects objects in adjacent lane on empty road for 5–10 minutes after car wash  
**Severity:** P2  
**Trigger:** Car wash using high-pressure water → water trapped in radar radome  
**Recurrence pattern:** Bug disappears after 10–15 minutes (water evaporates)

### This is a Recurring/Intermittent Bug
```
Pattern:
  - Occurs only after wet events: car wash, heavy rain, car wash spray
  - Disappears after 10–15 min driving (heat from radar + airflow evaporates water)
  - Reappears after every wet event
  - Not reproducible in dry conditions → difficult to catch in standard regression
```

### Diagnostics
```
CANoe trace (captured immediately after car wash):
  RadarRear_Object_01_Valid  = 1
  RadarRear_Object_01_Range  = 8.5 m
  RadarRear_Object_01_Doppler = -2.3 m/s
  BSD_Alert_Left             = 1 (Blind Spot Alert active)
  
  (No vehicle in adjacent lane — confirmed by camera)
  
Oscilloscope on radar Tx power:
  Radar Tx power: 15 dBm (normal: 18 dBm) ← 3 dB lower due to radome water attenuation
  Multipath: water film on radome creates secondary reflection path
  → returns appear as objects at ≈ 8–10 m
```

### Root Cause
Water film on the radar radome acts as a dielectric lens — it creates multipath reflections that the radar interprets as real targets at 8–10 m. The signal processing plausibility filter does not filter these because the Doppler (relative velocity) of the ghosted return matches a realistic overtaking vehicle pattern.

### Fix
```
Two approaches:
  1. Hardware (preferred long-term): hydrophobic radome coating (water-repellent nano-coating)
     → reduces water retention by 80%; ghosts disappear within 1 min instead of 15 min
     
  2. Software (short-term workaround): add cross-check with rear camera:
     IF BSD_Alert AND rear_camera_adjacent_lane_clear → suppress BSD alert
     (if camera confirms clear but radar insists on object → camera wins for BSD display)
     
Validation:
  1. Car wash test × 10:
       With hydrophobic coating: 0 ghost-object occurrences after 1 min ✓
  2. Wet tunnel (spray simulation on HIL):
       BSD alert suppressed within 2 s of camera confirming clear lane ✓
```

### How to Catch Recurring Wet-Weather Bugs
```
Test approach for weather-dependent intermittent ADAS bugs:
  1. Dedicated wet environment test session: car wash immediately followed by 15-min drive
  2. HIL: inject radar radome attenuation model (reduce Tx power by 3 dB for 10 min)
  3. Schedule wet tests in regression: once per SW release (monthly)
  4. Add to release checklist: "Wet-weather radar validation: 5 car wash cycles"
```

---

## 7. ADAS Diagnostics Quick Reference

### UDS DIDs for ADAS ECU Diagnostics

| DID | Description | Use Case |
|-----|-------------|---------|
| 0xF101 | SW Version | Verify correct SW loaded after OTA |
| 0x2001 | Radar X mounting offset | Verify calibration after mounting change |
| 0x2002 | Radar Y mounting offset | Verify calibration |
| 0x2010 | Camera calibration status | 0=OK, 1=uncalibrated, 2=fault |
| 0x3001 | Last reset cause | Identify watchdog/crash resets |
| 0x4001 | AEB enable/disable status | Verify feature is active |
| 0x4010 | Last AEB activation reason | Identify false positive root cause |
| 0x5001 | Sensor operational status | Radar/Camera/Ultrasonic health |

### ADAS DTCs (Common)

| DTC | Description | Root Cause |
|-----|-------------|-----------|
| U0126 | Steering angle sensor communication fault | CAN signal loss from EPS |
| U0128 | Brake booster pressure sensor signal fault | CAN signal loss from ESP |
| C0300 | ACC sensor misaligned | Radar calibration required |
| C0301 | Camera blocked/obstructed | Lens dirty, ice, sticker |
| B2070 | LKA camera communication fault | Camera ECU not responding |
| U1234 | AEB: no signal from brake ECU | CAN timeout from ESP |

### ADAS Diagnostics Flow
```
1. Read DTCs: Service 0x19 02 FF → identify all confirmed DTCs
2. Read freeze frame: Service 0x19 04 DTC_Number → what was vehicle state at fault?
3. Read DID 0x2001/0x2002: verify sensor calibration parameters
4. Stimulate sensor outputs via HIL / CAPL
5. Monitor fused output signals on CANoe graphic window
6. If calibration suspect: run calibration routine 0x31 01 0xFF10
7. Clear DTCs: 0x14 FF FF FF → retest
```
