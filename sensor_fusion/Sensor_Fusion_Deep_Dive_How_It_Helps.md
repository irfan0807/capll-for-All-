# Sensor Fusion — Deep Dive: How It Helps Automotive Systems
## Why Multi-Sensor Fusion Is the Foundation of Safe Autonomous Driving

**Document Classification:** Technical Reference — ADAS / Autonomous Vehicle Engineering  
**Audience:** Automotive Test Engineers, ADAS Validation Engineers, HIL/SIL Engineers, Systems Engineers  
**Applicable Standards:** ISO 26262, ISO 21448 (SOTIF), ISO/SAE 21434, UNECE WP.29  
**Applicable Platforms:** Bosch, Continental, Aptiv, Mobileye, Baidu Apollo, Waymo, NVIDIA DRIVE  

---

## Table of Contents

1. [The Core Problem Sensor Fusion Solves](#1-the-core-problem-sensor-fusion-solves)
2. [How Each Sensor Fails Alone](#2-how-each-sensor-fails-alone)
3. [How Fusion Makes the System Robust — Mechanism by Mechanism](#3-how-fusion-makes-the-system-robust)
4. [Fusion Algorithms — Deep Dive](#4-fusion-algorithms-deep-dive)
5. [How Fusion Enables Each ADAS Feature](#5-how-fusion-enables-each-adas-feature)
6. [Apollo Go: Real-World Fusion Architecture](#6-apollo-go-real-world-fusion-architecture)
7. [Fusion and Functional Safety (ISO 26262)](#7-fusion-and-functional-safety-iso-26262)
8. [SOTIF — How Fusion Addresses ISO 21448](#8-sotif-how-fusion-addresses-iso-21448)
9. [Failure Modes in Sensor Fusion (and How to Test Them)](#9-failure-modes-in-sensor-fusion)
10. [Sensor Fusion in Localization and HD Maps](#10-sensor-fusion-in-localization-and-hd-maps)
11. [Temporal Fusion — How History Helps](#11-temporal-fusion-how-history-helps)
12. [Validation Strategy for Sensor Fusion Systems](#12-validation-strategy-for-sensor-fusion-systems)
13. [CAPL Scripts for Fusion System Testing](#13-capl-scripts-for-fusion-system-testing)
14. [Interview Q&A — Sensor Fusion](#14-interview-qa)
15. [Summary Cheatsheet](#15-summary-cheatsheet)

---

## 1. The Core Problem Sensor Fusion Solves

### 1.1 The Single-Sensor Impossibility

No single sensor can provide complete, reliable perception for a safe autonomous vehicle. This is not an engineering limitation that will eventually be solved — it is a **fundamental physics constraint**:

```
┌─────────────────────────────────────────────────────────────────────┐
│              WHY A SINGLE SENSOR CANNOT BE SUFFICIENT               │
├────────────────────┬────────────────────────────────────────────────┤
│ Camera alone       │ Cannot measure distance directly               │
│                    │ Fails in fog, rain, night, glare               │
│                    │ Cannot detect a stopped car with no contrast   │
├────────────────────┼────────────────────────────────────────────────┤
│ Radar alone        │ Cannot classify objects (car vs bin vs person) │
│                    │ Cannot read lane markings                      │
│                    │ Cannot detect stationary objects reliably      │
│                    │ Ghost returns from multi-path reflections      │
├────────────────────┼────────────────────────────────────────────────┤
│ LiDAR alone        │ Cannot read lane markings or signs             │
│                    │ Degraded in rain, fog, snow                    │
│                    │ Cannot classify objects by appearance          │
│                    │ Expensive; not all vehicles have it            │
├────────────────────┼────────────────────────────────────────────────┤
│ GPS/IMU alone      │ ±2-5m accuracy (not lane-level)                │
│                    │ Fails in tunnels, urban canyons                │
│                    │ No obstacle detection                          │
└────────────────────┴────────────────────────────────────────────────┘
```

**Sensor fusion is the engineering solution that combines the strengths of each sensor while compensating for the weaknesses of the others.**

### 1.2 Quantified Impact

| Metric | Camera Only | Radar Only | Camera + Radar Fusion |
|--------|-------------|------------|-----------------------|
| False detection rate (stationary) | 12% | 28% | 2.1% |
| Miss rate in heavy rain | 34% | 4% | 3.8% |
| Object classification accuracy | 91% | 41% | 97% |
| Distance accuracy (RMSE) | ±3.2m | ±0.4m | ±0.35m |

*Source: Representative values from published ADAS benchmarks (Euro NCAP, Continental internal test data)*

---

## 2. How Each Sensor Fails Alone

### 2.1 Camera Failure Modes

```
SCENARIO A — Sun glare
  Vehicle driving west at 17:30 → direct sun in camera → 
  Histogram saturated → lane detection fails → LKA deactivates

SCENARIO B — Tunnel exit
  Camera: iris adapts from 80,000 lux (outside) to 200 lux (tunnel) over ~300ms
  During adaptation: AEB camera input = invalid
  Time at 80 km/h during 300ms = 6.7 metres blind

SCENARIO C — Snow on road markings
  Camera sees uniform white surface → lane polynomial fails → 
  LDW cannot warn → vehicle drifts

SCENARIO D — White truck side in bright sunlight
  Mobileye recalls (2016): camera-only AEB missed semi-truck side 
  because truck surface matched sky background
```

### 2.2 Radar Failure Modes

```
SCENARIO E — Stationary metal object
  Radar CFAR (Constant False Alarm Rate) filter suppresses zero-velocity targets
  (road clutter: manhole covers, railings, signs all have zero Doppler)
  Result: Stopped car on highway → NOT detected by radar alone
  → Rear-end collision at highway speed

SCENARIO F — Multi-path ghost
  Radar transmits → bounces off road → reflects off bridge → 
  returns as phantom object at ~2x bridge range
  Result: False AEB braking at highway speed

SCENARIO G — Angular ambiguity
  Two vehicles side by side at 100m:
  Radar azimuth resolution ≈ ±1.5°
  At 100m → cannot distinguish two objects < 5.2m apart
  Result: Two cars appear as one large object → planning error
```

### 2.3 LiDAR Failure Modes

```
SCENARIO H — Heavy rain
  LiDAR 905nm laser backscatters in rain droplets
  At rainfall > 100mm/h: detection range drops from 200m → 40m
  At highway speed (120 km/h): 40m = 1.2 seconds stopping time
  → Insufficient for safe AEB

SCENARIO I — Retroreflective clothing / glass
  LiDAR pulse hits glass window → passes through (not reflected back)
  Result: Pedestrian with large glass door: lidar "sees" through them

SCENARIO J — LiDAR solar saturation
  1550nm LiDAR: more eye-safe but solar interference at sunrise/sunset
  905nm LiDAR: solar background noise degrades SNR
```

### 2.4 Why Failures Are Not Independent

This is the critical insight: **sensor failures are not always independent events.** Some scenarios degrade multiple sensors simultaneously:

```
CORRELATED FAILURE: Fog bank
  Camera:  Contrast loss → object detection fails
  LiDAR:   Backscatter → detection range halved
  GPS:     Unaffected
  Radar:   Largely unaffected (RF propagates through fog)
  → Radar becomes the primary sensor; fusion weight shifts to radar

CORRELATED FAILURE: Tunnel
  Camera:  Transitional blindness
  GPS:     No satellite signal
  HD Map:  Pre-built map still available
  Radar:   Unaffected
  LiDAR:   Unaffected
  → Fusion compensates via radar + LiDAR + map positioning
```

**Fusion handles correlated failures by dynamically adjusting sensor weights — this is the "intelligence" in sensor fusion.**

---

## 3. How Fusion Makes the System Robust — Mechanism by Mechanism

### 3.1 Mechanism 1: Complementary Coverage

Different sensors are physically good at different things. Fusion combines them so the combined system exceeds any individual:

```
┌────────────────────────────────────────────────────────────────────────┐
│                 SENSOR COMPLEMENTARITY MATRIX                          │
├─────────────────────────┬────────┬───────┬────────┬──────┬────────────┤
│ Capability              │ Camera │ Radar │ LiDAR  │ Sono │ GPS+Map    │
├─────────────────────────┼────────┼───────┼────────┼──────┼────────────┤
│ Long-range detection    │  Good  │  Best │  Good  │  No  │ Map-based  │
│ Short-range parking     │  OK    │  OK   │  OK    │  Best│  No        │
│ Velocity measurement    │  Est.  │  Best │  Est.  │  No  │ No         │
│ 3D geometry             │ Stereo │ Poor  │  Best  │  No  │ Map-based  │
│ Object classification   │  Best  │ Poor  │  OK    │  No  │ No         │
│ Lane marking detection  │  Best  │  No   │  No    │  No  │ Map-based  │
│ Traffic sign reading    │  Best  │  No   │  No    │  No  │ Map-based  │
│ Night operation         │  Poor  │  Best │  Good  │  OK  │  Yes       │
│ Rain/fog operation      │  Poor  │  Best │  Poor  │  OK  │  Yes       │
│ Direct distance measure │  No    │  Best │  Best  │  OK  │ No         │
└─────────────────────────┴────────┴───────┴────────┴──────┴────────────┘
Sono = Ultrasonic (Sonar)
```

### 3.2 Mechanism 2: Redundancy for Safety

When sensor A fails, sensor B continues to provide a (degraded but valid) output. This directly supports **ISO 26262 ASIL decomposition**:

```
AEB System ASIL Decomposition:

  Full camera + radar fusion system → ASIL D requirement
  
  Decompose:
    Camera channel:  ASIL B (can fail, radar still active)
    Radar channel:   ASIL B (can fail, camera still active)
    
    ASIL B(camera) + ASIL B(radar) → equivalent to ASIL D coverage
    because both must fail simultaneously → probability much lower

  Calculation:
    P(camera fail) = 1×10⁻⁷ / hour (ASIL B target)
    P(radar fail)  = 1×10⁻⁷ / hour (ASIL B target)
    P(both fail simultaneously) = 1×10⁻¹⁴ / hour
    → exceeds ASIL D requirement of 1×10⁻⁸ / hour (by 6 orders of magnitude)
```

### 3.3 Mechanism 3: Confidence Weighting

Not all sensor readings are equal in all conditions. A good fusion system assigns dynamic weights:

```
Kalman Filter weight (simplified):

  x_fused = (w_camera × x_camera) + (w_radar × x_radar)
            ──────────────────────────────────────────────
                    w_camera + w_radar

  Where weights are derived from covariance (uncertainty):
    w = 1 / σ²   (lower uncertainty → higher weight)

  In rain:
    σ²_camera increases (detection less reliable) → w_camera drops
    σ²_radar stays low (radar unaffected by rain) → w_radar dominates

  At night on a dark road:
    σ²_camera increases → w_camera drops
    σ²_radar stays constant → radar dominates for distance
    But classification: camera still better, even at night with IR
```

### 3.4 Mechanism 4: Cross-Validation / Sanity Checking

Two sensors measuring the same object should agree within physical bounds. If they disagree significantly, something is wrong:

```
Cross-validation example:

  Camera says:   vehicle at  45m, closing at 12 m/s
  Radar says:    vehicle at 180m, closing at  8 m/s

  Delta = 135m — this is not measurement noise, it's a mismatch.
  Possible causes:
    a) Camera locked onto wrong object (lane-adjacent vehicle)
    b) Radar has a ghost target from overpass
    c) Sensor misalignment after a pothole impact

  Fusion action:
    → Raise uncertainty flag on both measurements
    → Request LiDAR confirmation (if available)
    → Downgrade AEB confidence → conservative action (longer TTC margin)
    → Log event for remote analysis
```

### 3.5 Mechanism 5: Ghost Target Rejection

Radar ghost targets (multi-path returns) are a common source of false AEB triggers. Fusion eliminates them:

```
Ghost target signature:
  Radar reports: object at 210m, zero lateral velocity, stationary
  Camera checks: 210m field of view → no object visible
  LiDAR checks:  210m range → no point cloud cluster

  Decision: This is a radar ghost → suppress AEB trigger

Without fusion: AEB activates at highway speed for a ghost → rear-end collision
With fusion:    Ghost identified → no false activation → safety maintained
```

---

## 4. Fusion Algorithms — Deep Dive

### 4.1 Kalman Filter (Standard)

The Kalman Filter is the workhorse of sensor fusion. It maintains a **state estimate** and **uncertainty estimate**, and optimally combines predictions with measurements.

**State vector for a tracked object:**
```
x = [px, py, vx, vy, ax, ay]ᵀ
    (x pos, y pos, x vel, y vel, x acc, y acc)
```

**Two-step cycle:**

```
STEP 1 — PREDICT (using physics model):
  x̂(k|k-1) = F × x̂(k-1|k-1)        (state prediction)
  P(k|k-1)  = F × P(k-1|k-1) × Fᵀ + Q  (covariance prediction)
  
  F = state transition matrix (constant velocity or constant accel model)
  Q = process noise covariance (model uncertainty)
  P = state covariance (uncertainty)

STEP 2 — UPDATE (using sensor measurement):
  K = P(k|k-1) × Hᵀ × [H × P(k|k-1) × Hᵀ + R]⁻¹   (Kalman gain)
  x̂(k|k) = x̂(k|k-1) + K × [z(k) - H × x̂(k|k-1)]  (state update)
  P(k|k)  = (I - K × H) × P(k|k-1)                   (covariance update)
  
  z = measurement vector from sensor
  H = measurement matrix (maps state to measurement space)
  R = measurement noise covariance (sensor uncertainty)
  K = Kalman gain (how much to trust the new measurement)
```

**Key insight — Kalman Gain K:**
```
  K → 0: Ignore the measurement, trust the prediction (low R, high P ratio)
  K → 1: Ignore the prediction, trust the measurement (high R, low P ratio)

  This is exactly the "confidence weighting" from Section 3.3, but mathematically optimal.
```

**Example — Radar + Camera fusion at 50m:**
```
  Radar measurement:   z_r = [49.8m, 0.5m lateral, -12.3 m/s]  R_r = diag(0.25, 0.64, 0.09)
  Camera measurement:  z_c = [50.1m, 0.4m lateral]              R_c = diag(1.44, 0.16)

  (Radar has lower distance uncertainty, camera has lower lateral uncertainty)
  
  After fusion:
    Fused position = [49.9m, 0.42m lateral]
    Fused velocity = -12.3 m/s (from radar — camera doesn't measure velocity directly)
    Fused uncertainty = diag(0.21, 0.12) → lower than either sensor alone
```

### 4.2 Extended Kalman Filter (EKF)

Standard Kalman assumes linear models. Automotive applications are **nonlinear**:
- Radar measures range + angle (polar) → state is Cartesian
- Conversion is nonlinear: x = r×cos(θ), y = r×sin(θ)

EKF linearises these nonlinear functions using the **Jacobian**:

```
  Instead of: x̂ = F × x
  EKF uses:   x̂ = f(x)   (nonlinear motion model)

  Instead of: z = H × x
  EKF uses:   z = h(x)   (nonlinear measurement model)

  Jacobians:
    Fⱼ = ∂f/∂x |x̂        (Jacobian of motion model at current state)
    Hⱼ = ∂h/∂x |x̂        (Jacobian of measurement model at current state)

  These replace F and H in the standard Kalman equations.

  Radar → Cartesian EKF conversion (Hⱼ):
  ┌                    ┐
  │ px/r   py/r   0  0 │
  │-py/r²  px/r²  0  0 │
  │ vx/r   vy/r  px/r py/r│
  └                    ┘
  where r = √(px² + py²)
```

### 4.3 Unscented Kalman Filter (UKF)

EKF linearises using a Taylor expansion — this introduces errors for highly nonlinear systems (e.g., bicycle model for ego motion). UKF uses **sigma points** instead:

```
  Select 2n+1 sigma points around current state estimate
  Pass each sigma point through the nonlinear function
  Reconstruct mean and covariance from transformed sigma points
  
  More accurate than EKF for nonlinear systems
  More expensive to compute (2n+1 function evaluations vs one)
  Used in: high-accuracy localization, pedestrian prediction
```

### 4.4 Particle Filter

For non-Gaussian distributions (e.g., multi-modal hypotheses like "object is behind one of three parked cars"):

```
  Maintain N particles, each representing a possible state
  Each particle has weight proportional to how well it matches measurements
  
  Steps:
  1. Propagate each particle using motion model + noise
  2. Weight each particle by likelihood of current measurement
  3. Resample: particles with high weight are duplicated
             particles with low weight are eliminated
  
  Advantage: Handles non-Gaussian, multi-modal distributions
  Disadvantage: Computationally expensive for high-dimensional state
  Used in: Localization (Monte Carlo Localization), pedestrian intention
```

### 4.5 Deep Learning Fusion (BEV Networks)

Modern autonomous driving systems (Tesla, Waymo, Apollo) increasingly use end-to-end neural networks for fusion:

```
BEV (Bird's Eye View) Fusion Architecture:

  Camera images (8 views) ──────┐
                                 ├──► Backbone CNN ──► BEV feature map ──► Objects
  LiDAR point cloud ────────────┘                     (unified 2D grid   ── Lanes
                                                        top-down view)    ── Freespace
  
  Key innovation: Transform camera features from perspective view → BEV
  using depth estimation or geometry (IPM — Inverse Perspective Mapping)
  
  Examples:
    BEVFusion (MIT 2022):  Camera + LiDAR BEV fusion
    BEVFormer (Shanghai AI Lab): Camera-only BEV with transformers
    Apollo Fusion Net:     Radar + Camera + LiDAR → unified BEV

  Advantage: End-to-end learnable — fusion is optimised for the final task
  Disadvantage: Hard to validate, black-box, requires massive training data
```

---

## 5. How Fusion Enables Each ADAS Feature

### 5.1 AEB (Automatic Emergency Braking) — Fusion is Critical

```
AEB Decision Pipeline with Multi-Sensor Fusion:

  Camera:   Detects object → class=PEDESTRIAN, bounding box [x1,y1,x2,y2]
  Radar:    Detects object → range=23m, velocity=-8.3 m/s (approaching)
  LiDAR:    Detects cluster → centroid (23.1m, 0.2m lateral), height=1.7m
  
  Data Association:
    Camera bbox centre maps to radar return within 0.5°? YES → same object
    LiDAR centroid within 1m of radar position? YES → confirmed
  
  Fused State:
    Object type: PEDESTRIAN (camera)
    Distance:    23.1m (LiDAR most precise)
    Velocity:    -8.3 m/s approach (radar most precise)
    Height:      1.7m (LiDAR) → consistent with adult pedestrian
  
  TTC Calculation:
    TTC = distance / relative_velocity = 23.1 / 8.3 = 2.78 seconds
    AEB threshold: TTC < 2.5s → WARNING
                   TTC < 1.8s → PARTIAL BRAKE (0.5g)
                   TTC < 1.2s → FULL BRAKE (1.0g)
  
  Why fusion helps:
  - Camera alone: No reliable range → TTC calculation inaccurate
  - Radar alone: Cannot confirm it's a pedestrian (not a sign post)
  - LiDAR alone: Cannot classify pedestrian without camera
  - FUSED: Confident object type + accurate distance + accurate velocity
           → reliable TTC → correct AEB activation
```

**Consequence of missing fusion:**
```
REAL INCIDENT: Uber ATG fatality (2018, Tempe AZ):
  Perception system classified pedestrian as "unknown object", then "vehicle", 
  then "bicycle" — oscillating classification caused system to not commit to AEB
  Root cause: insufficient fusion between LiDAR object hypothesis and classification
  Outcome: 1 fatality, entire program suspended
```

### 5.2 ACC (Adaptive Cruise Control) — Radar Primary, Camera Confirms

```
ACC Fusion Role:

  Primary sensor: LONG-RANGE RADAR (250m, tracks lead vehicle)
    - Continuous Doppler tracking: relative velocity = d/dt(range)
    - Smooth following even if camera temporarily loses detection

  Secondary sensor: CAMERA
    - Confirms radar target IS the intended lead vehicle
    - Rejects ghost targets (overpass radar returns)
    - Reads road curvature (lane polynomial) → predict if lead car is in-lane

  Fusion benefit:
    - Radar follows target through camera blind zones (sun, rain)
    - Camera prevents following a vehicle in the adjacent lane
    - Camera prevents false braking from bridge ghost targets

  Cut-in scenario:
    Camera:  Detects new vehicle entering ego lane at 42m
    Radar:   Was tracking lead vehicle at 110m; new radar return at 42m appears
    Fusion:  Transitions tracking from 110m target to 42m cut-in vehicle
             Trajectory prediction: cut-in vehicle decelerating
             ACC response: decelerate to maintain headway
```

### 5.3 LKA (Lane Keeping Assist) — Camera Primary, Map Secondary

```
LKA Fusion Role:

  Primary: CAMERA (lane marking detection)
    - Polynomial model of lane boundaries
    - Lateral offset calculation: ego position relative to lane centre

  Secondary: HD MAP + GPS
    - Pre-built lane geometry → fills in when markings not visible
    - Road curvature → feed-forward to steering controller
    - Helps at lane splits, merges, construction zones

  Fusion benefit:
    Sun glare scenario (camera fails):
      Camera confidence → LOW
      HD Map lateral position → available
      Fusion: switch primary to map guidance for ≤3 seconds
              If map also uncertain → WARN + release torque
              Driver must re-engage

  Radar's role in LKA:
    Adjacent vehicle tracking
    → If adjacent vehicle detected at d < 0.6m lateral: reduce LKA authority
    → Prevents LKA from pushing ego vehicle into adjacent car
```

### 5.4 BSD (Blind Spot Detection) — Radar + Camera

```
BSD Fusion Role:

  Primary: SHORT-RANGE RADAR (covers ±75°, up to 30m behind)
    - Detects objects in blind spot zone
    - Relative velocity measurement

  Secondary: CAMERA (rear-lateral cameras if equipped)
    - Classifies: motorcycle, bicycle, truck
    - Critical for motorcycle detection (small RCS → radar misses)

  Fusion benefit:
    Motorcycle with small radar RCS (≈0.01 m²):
      Radar may not detect at d > 15m
      Camera detects shape → MOTORCYCLE classification
      Fusion: camera detection triggers radar sensitivity increase
              or confirms presence → activate BSD warning

  Without fusion:
    BSD-001 defect: motorcycle at 18m lateral angle not detected
    Driver merges → collision (RPN=720 in FMEA — highest risk)
  
  With fusion:
    Camera pipeline feeds motorcycle detection → BSD activated
    Warning lamp + haptic steering feedback → driver holds lane
```

### 5.5 Parking / PDC — Ultrasonic + Camera

```
Parking Fusion:

  Ultrasonic: ±2cm range accuracy at 0.1m–5m, fast update rate (50ms)
  Camera:     Identifies object type (person, trolley, fixed wall)
  
  Fusion benefit:
    Ultrasonic cannot distinguish:
      A child standing at 0.5m
      A wall at 0.5m
    Same distance → same braking response
    
    Camera adds context:
      "Wall" → apply maximum deceleration (hard stop)
      "Child moving" → earlier warning, slower approach, alert driver
    
    Fused output:
      object_type + distance + predicted_trajectory → 
      graduated intervention (warn → slow → stop)
```

---

## 6. Apollo Go: Real-World Fusion Architecture

### 6.1 RT6 Sensor Configuration

```
Apollo Go RT6 — 38 Sensors:

  LiDAR:
    × 1 roof mechanical spinning LiDAR (360° coverage, 128-line)
    × 4 solid-state LiDAR (front corners + rear corners, 120° FoV each)
    → Covers all angles; solid-state for redundancy if spinning LiDAR fails

  Camera:
    × 8 cameras (360° surround coverage)
    × 3 front cameras (long-range, mid-range, wide-angle)
    × 2 rear cameras
    × 2 lateral cameras
    × 1 interior camera (passenger monitoring)

  Radar:
    × 5 millimetre-wave radar (77 GHz)
    × 1 front long-range (250m, ±15°)
    × 2 front corners (80m, ±60°)
    × 2 rear corners (80m, ±60°)

  Positioning:
    × 1 high-precision GNSS receiver (GPS + BeiDou + GLONASS)
    × 1 IMU (6-DOF: 3-axis accelerometer + 3-axis gyroscope)

  Ultrasonic:
    × 12 ultrasonic sensors (parking / close-range)
```

### 6.2 Apollo Galaxy Platform — Fusion Pipeline

```
┌──────────────────────────────────────────────────────────────────────┐
│                   APOLLO GALAXY FUSION PIPELINE                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  INPUT LAYER                                                         │
│  LiDAR(×5) ──────┐                                                  │
│  Camera(×8) ─────┼──► TIME SYNCHRONISATION (hardware timestamp)     │
│  Radar(×5) ──────┤    + SENSOR COORDINATE TRANSFORM (calibration)   │
│  GNSS+IMU ───────┘                                                  │
│                   │                                                  │
│                   ▼                                                  │
│  PERCEPTION LAYER                                                    │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Camera stream → CNN object detector → 2D detections           │ │
│  │  LiDAR stream  → PointPillar/VoxelNet → 3D bounding boxes      │ │
│  │  Radar stream  → CFAR + clustering → radar objects             │ │
│  └────────────────────────┬───────────────────────────────────────┘ │
│                            │                                         │
│                            ▼                                         │
│  FUSION LAYER                                                        │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  DATA ASSOCIATION: Hungarian algorithm matches objects          │ │
│  │    across sensor modalities (IoU-based + distance-based)        │ │
│  │                                                                  │ │
│  │  TRACK MANAGEMENT: Kalman/EKF per-track state estimate          │ │
│  │    Track confirmed: seen in N of M frames                       │ │
│  │    Track deleted: not seen for T seconds                        │ │
│  │                                                                  │ │
│  │  OUTPUT: Fused Object List                                       │ │
│  │    [id, class, x, y, z, vx, vy, heading, confidence, age]      │ │
│  └────────────────────────┬───────────────────────────────────────┘ │
│                            │                                         │
│  PREDICTION LAYER          ▼                                         │
│  → Trajectory prediction per object (CNN/LSTM-based)                │
│  → 5-second predicted path for each object                          │
│                                                                      │
│  PLANNING → CONTROL → CAN bus → Braking / Steering / Throttle      │
└──────────────────────────────────────────────────────────────────────┘
```

### 6.3 How Apollo Handles Sensor Degradation

```
RAIN SCENARIO (Apollo RT6):
  
  Camera confidence: DEGRADED (lens water droplets)
  LiDAR confidence: DEGRADED (laser backscatter)
  Radar confidence: NORMAL
  
  Apollo response:
    1. Fusion weights shift: radar dominates distance/velocity
    2. Camera still used for classification (best available)
    3. LiDAR used for nearby obstacle (solid-state more rain-resistant)
    4. Speed limit imposed: max speed reduced to 60 km/h in heavy rain
    5. HD Map compensates: localisation via map + IMU dead-reckoning

TUNNEL SCENARIO:
  
  GPS: LOST (no satellite signal)
  Camera: Normal (tunnel lights sufficient)
  Radar: Normal
  LiDAR: Normal
  IMU: Active (dead-reckoning)
  
  Apollo response:
    1. GPS weight → 0
    2. IMU dead-reckoning: integrate accelerations to estimate position
    3. LiDAR scan-matching against pre-built tunnel map
    4. Localisation maintained to ±0.15m until GPS recovers
```

---

## 7. Fusion and Functional Safety (ISO 26262)

### 7.1 How Fusion Achieves ASIL Decomposition

ISO 26262 permits decomposing a high-ASIL requirement across two independent channels. Sensor fusion is the primary enabler of this:

```
Example: AEB system → ASIL D requirement

  Without fusion:
    Single camera AEB → must be developed to ASIL D entirely
    ASIL D software development cost: ~$2-5M, 3+ years

  With fusion (two independent channels):
    Camera channel:  ASIL B
    Radar channel:   ASIL B
    
    ASIL B(d) + ASIL B(d) → satisfies ASIL D
    (suffix 'd' means the two are developed independently)
    
    Cost saving: ~70% reduction in ASIL D development effort
    
  Independence requirements:
    - Separate hardware (no shared microcontroller)
    - Separate power supply domains
    - Separate CAN/Ethernet buses
    - Software developed by different teams (freedom from interference)
    - Different failure modes (HW diversity preferred)
```

### 7.2 FMEA Impact of Fusion

Sensor fusion directly reduces RPN (Risk Priority Number) in FMEA:

```
FMEA Example: AEB Miss Detection

  WITHOUT FUSION (camera-only AEB):
    Severity:     10 (collision, potential fatality)
    Occurrence:   6  (camera fog failure is not rare)
    Detectability: 8 (cannot detect fog failure until too late)
    RPN = 10 × 6 × 8 = 480  → HIGH RISK, requires mitigation

  WITH FUSION (camera + radar + LiDAR):
    Severity:     10 (unchanged — collision is still severe)
    Occurrence:   2  (all three sensors must fail simultaneously)
    Detectability: 3  (fusion monitor detects sensor disagreement)
    RPN = 10 × 2 × 3 = 60   → ACCEPTABLE RISK
    
  Fusion reduced RPN from 480 → 60 (87.5% reduction)
```

### 7.3 Sensor Fusion Monitor (Safety Mechanism)

A well-designed fusion system includes a **fusion health monitor** as a safety mechanism:

```
Health Monitor checks:

  1. Temporal plausibility:
     Sensor last message timestamp > 200ms ago? → Sensor timeout → degrade gracefully
  
  2. Cross-sensor consistency:
     Object position from camera vs radar > 5m discrepancy? → Fusion integrity fault
  
  3. Coverage sufficiency:
     AEB requires: (camera OR (radar AND LiDAR))
     If camera failed AND LiDAR failed AND radar uncertain → AEB unavailable → DTC set
  
  4. Calibration drift detection:
     Track consistent lateral offset between camera and radar detections over time
     Persistent bias > 0.3m → extrinsic calibration drift → service required
     
  DTC codes for fusion faults:
    U0100: CAN communication fault (radar ECU not responding)
    U3000: Sensor fusion unavailability
    C1234: AEB degraded due to sensor fusion fault
```

---

## 8. SOTIF — How Fusion Addresses ISO 21448

SOTIF (Safety Of The Intended Functionality) addresses failures that are **not caused by hardware faults but by functional insufficiency** — the sensor works perfectly but the situation is beyond its design parameters.

### 8.1 SOTIF Scenarios and Fusion Response

```
SOTIF Scenario 1 — Unusual appearance
  Object: A child in a large Halloween costume (unusual shape)
  Single camera: Low confidence classification → misclassified
  Fusion response:
    LiDAR: Detects cluster, correct height for small human (0.9m)
    Radar: Detects moving target, velocity consistent with walking
    Fused: LiDAR height + radar motion → PEDESTRIAN classification confirmed
    → AEB remains armed

SOTIF Scenario 2 — Adverse lighting
  Object: Pedestrian in high-visibility jacket walking across road
  Camera in direct sun glare: Saturated → object not detected
  Fusion response:
    Radar: Detects moving object at 35m (Doppler velocity = 1.2 m/s lateral)
    LiDAR: Detects cluster at 35m (not affected by visible light glare)
    Fused: Pedestrian detected despite camera failure
    → AEB activated

SOTIF Scenario 3 — Novel scenario (out of distribution)
  Object: A ladder fallen across road (never in training data)
  Camera: Low confidence → classified as "unknown obstacle"
  LiDAR: Detects extended object, irregular shape, height 0.3m
  Radar: Weak return (ladder has poor RCS)
  Fusion response:
    Unknown obstacle + LiDAR height < 0.3m + blocking ego path
    → Conservative policy: treat as obstacle → AEB armed
    → Even without classification, fusion ensures safe response
```

### 8.2 Fusion and SOTIF Validation

ISO 21448 requires identifying "triggering conditions" — scenarios that cause the ADAS to behave unsafely. Fusion directly reduces the triggering condition space:

```
  Single sensor triggering conditions:
    Camera alone: fog, night, glare, novel objects, occlusion → many triggers
  
  Fused system triggering conditions:
    All sensors must be simultaneously triggered in a correlated way
    → Triggering conditions dramatically fewer
    → Remaining risk (residual risk) must be accepted or further mitigated
```

---

## 9. Failure Modes in Sensor Fusion

### 9.1 Data Association Failure (Ghost Merging)

```
Scenario:
  Two pedestrians walking side by side at 25m
  Radar: Sees two targets at 24.8m and 25.2m but 1.2° apart
         Angular resolution insufficient → merges into one radar object
  Camera: Sees two distinct people
  LiDAR: Sees two distinct clusters

  Bad fusion: Radar "one object" dominates → merged track created
              Planning thinks one object → dangerous

  Good fusion: Camera + LiDAR both report TWO objects
               Hungarian algorithm: radar return matched to camera left-person
               Second camera detection without radar match → radar-less track
               Both tracks maintained with lower radar confidence
```

### 9.2 Track Swap

```
Scenario:
  Lead vehicle A at 45m, slower vehicle B at 70m in adjacent lane
  B changes lane, now at 45m in ego lane
  A is gone (turned off)
  
  Bad fusion: Track ID for A is maintained, B's measurements are associated to A's track
              Planning thinks the 45m object has been there all along
              Misses the sudden appearance of B → delayed AEB

  Good fusion: Track management detects inconsistency in track A
               Track A deleted; Track B created fresh with new ID
               Planning receives NEW OBJECT at 45m → higher urgency
```

### 9.3 Temporal Desynchronisation

```
Scenario:
  Camera: 60 Hz update (16.7ms period)
  Radar:  20 Hz update (50ms period)
  LiDAR:  10 Hz update (100ms period)
  
  At 120 km/h: vehicle travels 3.3m in 100ms
  
  Bad fusion: Use latest timestamp from each sensor as-is
              LiDAR data is 100ms old → object position shifted 3.3m
              Camera data at t=100ms, LiDAR at t=0ms → 3.3m phantom offset
              → AEB triggers at wrong distance
  
  Good fusion: All sensor data extrapolated to common timestamp
               Using kinematic model: x(t) = x₀ + v×Δt + ½a×Δt²
               All measurements normalised to t_fusion = latest timestamp
               → Correct object position for all sensors
```

### 9.4 Extrinsic Calibration Drift

```
Scenario:
  Vehicle hits pothole → front LiDAR bracket deforms slightly
  LiDAR boresight rotated 0.5° downward from nominal
  
  At 50m: 0.5° angular error = 0.44m positional error
  
  Effect on fusion:
    LiDAR reports object at (50.0m, 0.0m)
    Camera reports object at (50.0m, 0.0m)
    Radar reports object at (50.0m, -0.44m)
    (LiDAR shifted but radar not shifted)
    
    Data association fails: LiDAR + Camera associate, radar alone
    AEB uses radar distance but LiDAR geometry
    → Inconsistent AEB corridor width → potential miss or false trigger
  
  Detection:
    Fusion monitor tracks mean offset between sensor pairs over 100 objects
    Persistent offset > 0.3m over 60 seconds → DTC C1500 (calibration fault)
    → Service required (camera/LiDAR re-calibration with reference board)
```

---

## 10. Sensor Fusion in Localization and HD Maps

### 10.1 The Localization Problem

For autonomous driving, knowing your position to within ±0.1m (lane-level precision) is essential. Standard GPS gives ±2-5m. Fusion solves this:

```
LOCALIZATION FUSION (position estimation):

  Sources:
    GNSS (GPS + BeiDou): Global position, ±2-5m (open sky), ±50m (urban canyon)
    IMU:                 Relative motion, ±0.01m/s velocity (drifts over time)
    LiDAR scan-matching: Compare current scan to pre-built HD map → ±0.05m (relative)
    Camera localisation: Match visual features to HD map imagery → ±0.1m
    Wheel odometry:      Distance travelled from wheel speed sensors → ±1% error

  Fusion via EKF:
    State: [x, y, heading, velocity, yaw_rate]
    
    IMU provides high-frequency (200Hz) prediction step:
      x(k) = x(k-1) + v×cos(θ)×dt
      y(k) = y(k-1) + v×sin(θ)×dt
    
    LiDAR scan-match (10Hz) provides correction:
      High-confidence position update → resets accumulated IMU drift
    
    GNSS (10Hz) provides absolute reference:
      Corrects any divergence from map

  Result: ±0.05-0.10m localisation accuracy — lane-level precision
          Works in tunnel (LiDAR map only), urban canyon (LiDAR + IMU)
```

### 10.2 HD Map as a Virtual Sensor

The HD Map is not a passive data store — it is an **active virtual sensor** in the fusion pipeline:

```
HD Map contributions to fusion:

  1. Speed limit extraction: Map + GNSS → speed limit on current road segment
     Even if camera cannot read speed sign, map provides limit
  
  2. Road geometry: Map provides:
     - Lane width (verify camera lane detection)
     - Curve radius (feed-forward to steering controller)
     - Intersection type (signalised? roundabout? yield?)
     - Lane count and direction
  
  3. Static obstacle overlay:
     Map marks known fixed structures: tunnels, bridges, overpasses
     Fusion: if radar detects large stationary return at known bridge location
             → suppress as ghost target
  
  4. Sensor confidence context:
     Map marks "camera-challenging" zones (tunnels, bridge shadows)
     → Fusion pre-emptively increases radar weight before entering zone
     → No degradation event — proactive adaptation
```

---

## 11. Temporal Fusion — How History Helps

### 11.1 Track History Improves Prediction

```
Object with 3-second track history vs 1-frame detection:

  1-frame detection:
    Position: (45m, 0.3m)
    Velocity: radar Doppler only → vx = -8m/s
    Heading: unknown → cannot predict lateral trajectory

  10-frame track (3 seconds at 3Hz):
    Historical positions: [(45m,0.3), (47m,0.28), (49m,0.27), ...]
    Velocity: (vx=-8m/s, vy=0.01m/s) — lateral velocity near zero
    Heading: atan2(vy, vx) = -0.07° → driving straight ahead
    Acceleration: calculated from velocity change over 3s → mild deceleration
    
    5-second trajectory prediction: vehicle will be at (45+8×5 = 85m ahead, staying in lane)
    → ACC: follow at safe headway
```

### 11.2 Ghosting Suppression via Temporal Consistency

```
Ghost target rejection using track history:

  Frame 1: Radar detects object at 180m, zero velocity
  Frame 2: No object at 180m
  Frame 3: Radar detects object at 180m, zero velocity
  
  Track management: Object appeared in 2 of 3 frames
  Real objects: persist for multiple consecutive frames
  Bridge ghost: sporadic, zero velocity, no LiDAR/camera confirmation
  
  Decision: Track age = 2 frames, no camera/LiDAR confirmation after 3 frames
            → Delete track (not a real object)
            → No AEB trigger
  
  Track confirmation rules:
    Tentative track: seen in 2 of 3 frames → output to planning
    Confirmed track: seen in 4 of 5 frames → high confidence
    Auto-delete: not seen in 5 consecutive frames
```

---

## 12. Validation Strategy for Sensor Fusion Systems

### 12.1 Fusion Validation Pyramid

```
┌──────────────────────────────────────────────────────────────────┐
│                    FUSION VALIDATION PYRAMID                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LEVEL 4 — PUBLIC ROAD (Real Vehicle, Real Environment)         │
│    Scenarios: fog, rain, night, construction zones               │
│    Metric: false positives/km, miss rate, localisation error     │
│    Tools: data logger, ground truth GPS (±2cm), reference LiDAR  │
│                                                                  │
│  LEVEL 3 — PROVING GROUND (Real Vehicle, Controlled Environment) │
│    Scenarios: moving targets, pedestrian mannequins, fog machine │
│    Metric: detection range, classification accuracy, AEB timing  │
│    Tools: VBOX, CANalyzer, breakout ECU                         │
│                                                                  │
│  LEVEL 2 — HIL / SIL (Sensor data replay with real ECUs)        │
│    Pre-recorded sensor data replayed into fusion ECU             │
│    Inject sensor faults: drop radar packets, corrupt camera feed │
│    Tools: dSPACE SCALEXIO, LABCAR, Vector CANoe simulation       │
│                                                                  │
│  LEVEL 1 — UNIT TEST (Algorithm-level, simulated data)          │
│    Test Kalman filter convergence                                │
│    Test data association with synthetic scenarios                │
│    Test ghost rejection logic                                    │
│    Tools: Python/MATLAB simulation, GoogleTest/GTest             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 12.2 Key Test Cases for Sensor Fusion Validation

```
TC-001: Single Sensor Dropout — Radar Failure
  Setup: Inject CAN timeout for radar ECU (suppress radar CAN messages)
  Expected: Fusion switches to camera+LiDAR only
            AEB detection range degrades to 80m (from 200m with radar)
            DTC U0100 raised
            Speed limit warning to driver (degraded mode)
  Fail if: AEB completely deactivated (no graceful degradation)

TC-002: Cross-Sensor Consistency Check
  Setup: Inject 5m longitudinal offset into camera detections
  Expected: Fusion monitor detects discrepancy (camera vs radar > 3m threshold)
            DTC C1500 (calibration fault) raised
            Fusion falls back to radar+LiDAR for distance
  Fail if: Fused distance reports average of camera+radar (biased result)

TC-003: Ghost Target from Bridge
  Setup: Place large metal plate on road surface at specific location
         Program radar simulator to emit ghost at 2× plate distance
  Expected: Camera and LiDAR do NOT detect object at ghost location
            Fusion suppresses ghost: no AEB trigger
  Fail if: AEB brakes for ghost target

TC-004: Temporal Synchronisation Under Load
  Setup: Overload fusion ECU CPU by 90%
  Expected: Sensor timestamps still correctly aligned
            Fused object positions still accurate
  Fail if: Under load, sensor data processed out of order → position errors

TC-005: Fog Degradation Graceful Handling
  Setup: Drive through proving ground fog chamber (LiDAR and camera degraded)
  Expected: Radar confidence increases
            Speed automatically reduced per ODD constraints
            Driver notified of degraded mode
  Fail if: False AEB activation from LiDAR backscatter

TC-006: Post-Pothole Calibration Drift
  Setup: Drive over 10cm pothole at 30 km/h
         Monitor: mean lateral offset between camera and radar detections
  Expected: Offset < 0.1m immediately after
            Drift detection triggers within 60 seconds if > 0.3m offset persists
  Fail if: Calibration drift not detected (silent fault)
```

### 12.3 Metrics for Fusion Performance

```
Detection Performance:
  True Positive Rate (Recall):   TPR = TP / (TP + FN)   → target > 99.5%
  False Positive Rate:           FPR = FP / (FP + TN)   → target < 0.1% per km
  Precision:                     P   = TP / (TP + FP)   → target > 98%
  F1 Score:                      F1  = 2 × P × TPR / (P + TPR)

Position Accuracy:
  RMSE (Root Mean Square Error):  √(mean((x_fused - x_gt)²))  → target < 0.3m
  95th percentile error:          target < 0.5m

Classification Accuracy:
  Per-class accuracy: car, pedestrian, cyclist, truck
  Confusion matrix analysis

Temporal Performance:
  End-to-end latency (sensor measurement → fused object output): target < 50ms
  Synchronisation error: target < 10ms between sensor channels

Availability:
  Fusion uptime: target > 99.9% over 100,000 km test fleet
  Graceful degradation coverage: all single-sensor-failure combinations tested
```

---

## 13. CAPL Scripts for Fusion System Testing

### 13.1 Radar Dropout Simulation

```capl
/*
 * Sensor Fusion Test: Radar ECU Dropout Simulation
 * Purpose: Verify fusion ECU gracefully degrades when radar messages stop
 * DUT: Fusion ECU (on CAN FD bus, 500kbps)
 * Expected: DTC U0100 raised within 500ms, AEB remains active (camera only)
 */

variables {
  msTimer radarDropoutTimer;
  msTimer monitorTimer;
  int radarDropoutActive = 0;
  int dtcU0100Detected = 0;
  long fusionObjectCount = 0;
}

on start {
  setTimer(radarDropoutTimer, 5000); // Start dropout after 5 seconds
  setTimer(monitorTimer, 100);       // Monitor every 100ms
  write("Test TC-001: Radar Dropout - Starting");
}

// Block radar ECU messages when dropout active
on message 0x320 {  // Radar Object List CAN ID
  if (radarDropoutActive == 0) {
    output(this);   // Pass through normally
  }
  // If radarDropoutActive: message is silently dropped (simulates ECU failure)
}

on timer radarDropoutTimer {
  radarDropoutActive = 1;
  write("TC-001: Radar dropout ACTIVATED at %.1f s", timeNowFloat());
}

// Monitor Fusion ECU output for graceful degradation
on message 0x500 {  // Fusion Object List CAN ID
  fusionObjectCount++;
}

// Monitor for DTC U0100 via UDS diagnostic response
on message 0x7E8 {  // Diagnostic response (ECU address 0x7E0)
  byte dtcHigh, dtcLow;
  if (this.byte(0) == 0x59) {  // ReadDTCInformation response
    dtcHigh = this.byte(5);
    dtcLow  = this.byte(6);
    if (dtcHigh == 0xU0 && dtcLow == 0x01) {
      dtcU0100Detected = 1;
      write("TC-001: DTC U0100 confirmed at %.1f s", timeNowFloat());
    }
  }
}

on timer monitorTimer {
  if (radarDropoutActive) {
    // Send UDS ReadDTCInformation request every 500ms
    byte dtcRequest[8] = {0x19, 0x02, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00};
    output(can1, 0x7E0, 8, dtcRequest);
  }
  setTimer(monitorTimer, 500);
}

on stopMeasurement {
  if (radarDropoutActive && dtcU0100Detected) {
    write("TC-001 PASS: Radar dropout detected within 500ms, DTC raised");
  } else if (radarDropoutActive && !dtcU0100Detected) {
    write("TC-001 FAIL: Radar dropout NOT detected by fusion ECU");
  }
  write("Total fusion object list updates: %d", fusionObjectCount);
}
```

### 13.2 Cross-Sensor Consistency Fault Injection

```capl
/*
 * Sensor Fusion Test: Camera-Radar Offset Injection
 * Purpose: Verify fusion monitor detects calibration drift > 0.3m
 * Method: Inject systematic 0.5m offset into camera object positions
 */

variables {
  msTimer testTimer;
  float cameraOffsetMetres = 0.0;
  float injectedOffsetTarget = 0.5; // 0.5m lateral offset
  int calibFaultDetected = 0;
}

// Intercept camera object list, inject lateral offset
on message 0x310 {  // Camera Object List CAN ID
  message 0x310 modifiedMsg;
  float lateralPos;
  
  modifiedMsg = this; // Copy original
  
  if (cameraOffsetMetres > 0) {
    // Object 1 lateral position at bytes 4-5 (signed int16, scale 0.01m)
    lateralPos = (float)(this.word(4)) * 0.01;  // decode
    lateralPos += cameraOffsetMetres;             // inject offset
    modifiedMsg.word(4) = (int)(lateralPos / 0.01); // re-encode
    
    output(modifiedMsg); // Send modified message
  } else {
    output(this); // Pass through unmodified
  }
}

on start {
  setTimer(testTimer, 3000); // Inject offset after 3s (baseline first)
  write("TC-002: Camera Offset Injection - Baseline phase (3s)");
}

on timer testTimer {
  if (cameraOffsetMetres == 0.0) {
    cameraOffsetMetres = injectedOffsetTarget;
    write("TC-002: 0.5m camera lateral offset INJECTED at %.1f s", timeNowFloat());
    setTimer(testTimer, 10000); // Monitor for 10s
  } else {
    // Check result
    if (calibFaultDetected) {
      write("TC-002 PASS: Calibration fault C1500 detected within 10s");
    } else {
      write("TC-002 FAIL: Fusion did not detect 0.5m camera offset");
    }
  }
}

// Watch for calibration fault DTC (C1500)
on message 0x7E8 {
  if (this.byte(5) == 0xC1 && this.byte(6) == 0x50) {
    calibFaultDetected = 1;
    write("TC-002: DTC C1500 (Calibration Drift) detected at %.1f s", timeNowFloat());
  }
}
```

### 13.3 Fusion Latency Measurement

```capl
/*
 * Sensor Fusion Test: End-to-End Latency Measurement
 * Purpose: Measure time from sensor detection to fused object output
 * Target: < 50ms end-to-end
 */

variables {
  long radarDetectionTimestamp;
  long fusionOutputTimestamp;
  long latencySamples[1000];
  int sampleCount = 0;
  long maxLatency = 0;
  long minLatency = 99999;
}

on message 0x320 {  // Radar Object List
  if (this.byte(2) != 0) {  // Object detected (confidence > 0)
    radarDetectionTimestamp = timeNow() / 10; // Convert to microseconds
    output(this);
  }
}

on message 0x500 {  // Fusion Object List
  long latency;
  if (radarDetectionTimestamp > 0) {
    fusionOutputTimestamp = timeNow() / 10;
    latency = fusionOutputTimestamp - radarDetectionTimestamp;
    
    if (sampleCount < 1000) {
      latencySamples[sampleCount] = latency;
      sampleCount++;
    }
    
    if (latency > maxLatency) maxLatency = latency;
    if (latency < minLatency) minLatency = latency;
    
    if (latency > 50000) {  // > 50ms = 50000 microseconds
      write("LATENCY VIOLATION: %d microseconds at %.2f s", latency, timeNowFloat());
    }
  }
}

on stopMeasurement {
  long totalLatency = 0;
  int i;
  
  for (i = 0; i < sampleCount; i++) {
    totalLatency += latencySamples[i];
  }
  
  write("=== TC-004 Latency Results ===");
  write("Samples:       %d", sampleCount);
  write("Mean latency:  %d us (%.1f ms)", totalLatency/sampleCount, (float)(totalLatency/sampleCount)/1000.0);
  write("Min latency:   %d us", minLatency);
  write("Max latency:   %d us", maxLatency);
  
  if (maxLatency < 50000) {
    write("TC-004 PASS: All latencies < 50ms");
  } else {
    write("TC-004 FAIL: Max latency %.1f ms exceeds 50ms limit", (float)maxLatency/1000.0);
  }
}
```

---

## 14. Interview Q&A — Sensor Fusion

**Q1: Why is radar better than camera for AEB on highways?**
> Radar directly measures radial velocity via Doppler — it doesn't need to estimate speed from position change over time. For highway AEB, the target is often a stationary or slow vehicle in the same lane. Camera-only systems struggle with stationary targets (no motion to detect). Radar detects stationary objects via known zero-Doppler signatures (with appropriate clutter filtering). Radar also works in rain, fog, and night conditions.

**Q2: How does a Kalman filter handle a sensor that goes offline?**
> When a sensor stops providing measurements, the Kalman filter simply runs the prediction step without an update step. The state estimate continues to evolve based on the motion model, but the uncertainty (covariance P) grows with each cycle because there are no measurements to correct it. Over time the estimate diverges from reality and the uncertainty grows large. The fusion system can detect this via the increasing covariance value and flag it as sensor unavailability.

**Q3: What is the Hungarian algorithm and why is it used in fusion?**
> The Hungarian algorithm solves the assignment problem: given N tracked objects and M new sensor detections, find the optimal one-to-one matching that minimises total cost (e.g., Euclidean distance between predicted track positions and new detections). It runs in O(n³) time. In sensor fusion, it is used for data association — correctly matching each new radar return / camera bounding box to an existing track, even when objects cross or come close together.

**Q4: What does SOTIF say about sensor fusion?**
> ISO 21448 SOTIF requires identifying triggering conditions — scenarios where the system's functional insufficiency causes unsafe behaviour. For sensor fusion, SOTIF analysis must cover: environmental conditions that degrade each sensor, novel object types outside the training distribution, unusual sensor combinations, and correlated sensor failures. Fusion reduces the number of triggering conditions because scenarios that trigger one sensor often do not simultaneously trigger all others. The validation process must demonstrate that the remaining residual triggering conditions are acceptably rare.

**Q5: A test engineer sees that the AEB is triggering 200ms later than specification. How would you investigate using fusion data?**
> I would look at the fusion object log with timestamp resolution. First check when the radar first detected the target (baseline). Then check when the camera confirmed it (data association). Measure the delta from first radar detection to confirmed fused track creation — this is the association delay. Next check the track confidence build-up time (confirmation threshold N-of-M frames). Then check the planning system's TTC calculation timestamp. The 200ms delay may be in: (a) sensor transmission latency on CAN, (b) fusion association delay due to high track count, (c) planning cycle delay, or (d) conservative confirmation threshold. Each has a different fix.

**Q6: What is extrinsic calibration and why does it drift?**
> Extrinsic calibration defines the physical geometric relationship between sensors — the 3D rotation and translation from one sensor's coordinate frame to another (e.g., from the LiDAR frame to the vehicle centre frame). It is determined at the factory using a calibration target. In service, it drifts because: mechanical vibration loosens sensor mounts, thermal expansion changes bracket geometry, and impacts (potholes, minor collisions) physically shift sensors. Drift causes systematic position errors in the fused object list. It is detected by monitoring the mean offset between sensors over many object observations and setting a drift threshold.

**Q7: Compare early fusion vs late fusion for a camera+LiDAR system.**
> Early fusion (raw data): project LiDAR points onto camera image → combined point-level processing. Maximum information but requires perfect calibration and synchronisation; any calibration error corrupts the fusion input directly. Late fusion (object level): each sensor detects objects independently, then tracks are merged. More robust to calibration errors, simpler to validate each sensor separately, easier to achieve ISO 26262 ASIL decomposition. Production ADAS uses late fusion; research systems (BEVFusion, etc.) use early fusion for higher accuracy.

**Q8: How does Apollo Go handle localisation in a GPS-denied tunnel?**
> Apollo Go uses a multi-source localisation fusion: IMU dead-reckoning integrates accelerations at 200Hz to estimate relative motion, LiDAR scan-matching compares the current LiDAR point cloud to a pre-built tunnel HD map and returns a position correction, and wheel odometry provides an independent relative distance estimate. These are fused via an EKF where IMU provides the prediction step and LiDAR scan-matching provides occasional high-precision correction. The localisation remains accurate to approximately ±0.1m in a tunnel.

---

## 15. Summary Cheatsheet

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    SENSOR FUSION CHEATSHEET                              │
├────────────────────────────┬─────────────────────────────────────────────┤
│ WHAT IT DOES               │ Combines multiple sensor streams to get:    │
│                            │  Higher accuracy than any single sensor     │
│                            │  Redundancy (graceful degradation)          │
│                            │  Complete coverage (each sensor's strength) │
├────────────────────────────┼─────────────────────────────────────────────┤
│ CORE ALGORITHM             │ Kalman Filter (linear)                      │
│                            │ EKF (nonlinear — radar polar→Cartesian)     │
│                            │ UKF (highly nonlinear, sigma points)        │
│                            │ Particle Filter (non-Gaussian, multimodal)  │
│                            │ Deep learning BEV (end-to-end, modern)      │
├────────────────────────────┼─────────────────────────────────────────────┤
│ FUSION LEVELS              │ L1 Raw (early) — max info, hard to sync     │
│                            │ L2 Feature (mid) — balanced                 │
│                            │ L3 Object (late) — production standard      │
├────────────────────────────┼─────────────────────────────────────────────┤
│ KEY FAILURE MODES          │ Ghost target → radar multi-path → false AEB │
│                            │ Track swap → wrong object continuity        │
│                            │ Temporal desync → 3.3m error @120km/h      │
│                            │ Calibration drift → systematic offset       │
│                            │ Correlated failure → fog hits cam+lidar     │
├────────────────────────────┼─────────────────────────────────────────────┤
│ HOW IT HELPS AEB           │ Camera: classifies pedestrian               │
│                            │ Radar:  accurate range + velocity (TTC)     │
│                            │ LiDAR:  confirms 3D geometry                │
│                            │ Fused:  accurate TTC + correct object type  │
├────────────────────────────┼─────────────────────────────────────────────┤
│ ISO 26262 BENEFIT          │ ASIL decomposition:                         │
│                            │  Camera ASIL B + Radar ASIL B = ASIL D     │
│                            │  Saves ~70% development cost vs single ASIL D│
├────────────────────────────┼─────────────────────────────────────────────┤
│ SOTIF BENEFIT              │ Reduces triggering condition space          │
│                            │ Multi-sensor agreement = higher confidence  │
│                            │ Conservative fallback when one sensor fails │
├────────────────────────────┼─────────────────────────────────────────────┤
│ VALIDATION APPROACH        │ Unit test → SIL → HIL → Proving Ground →   │
│                            │ Public road                                 │
│                            │ Key tests: dropout, offset injection,       │
│                            │  ghost rejection, latency, fog              │
├────────────────────────────┼─────────────────────────────────────────────┤
│ APOLLO GO FUSION           │ 38 sensors, Apollo Galaxy platform          │
│                            │ BEV deep learning + Kalman object tracker   │
│                            │ Dynamic weight shift on sensor degradation  │
│                            │ LiDAR scan-match for GPS-denied localisation│
└────────────────────────────┴─────────────────────────────────────────────┘
```

---

*Document Version: 1.0 — May 2026*  
*Reference: Apollo RT6 technical specifications, ISO 26262-4:2018, ISO 21448:2022, Euro NCAP AEB protocols*
