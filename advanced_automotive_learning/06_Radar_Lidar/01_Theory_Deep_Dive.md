# RADAR & LIDAR — DEEP DIVE
## Module 6 of 7 | advanced_automotive_learning

---

## 1. RADAR PHYSICS — FMCW

### 1.1 Why 77 GHz?

```
AUTOMOTIVE RADAR FREQUENCY BANDS:
  24 GHz: Short-range (BSD, PAS) — being phased out (EU regulation)
  77 GHz: Long/mid-range — dominant (ACC, AEB, FCW)
  79 GHz: Ultra-short-range (4D imaging radar) — emerging

WHY 77 GHz?
  Wavelength: λ = c/f = 3×10⁸ / 77×10⁹ ≈ 3.9 mm
  
  Advantages:
    ✓ Compact antenna size (λ/2 ≈ 2mm spacing → small module)
    ✓ 4 GHz bandwidth (76–81 GHz) → fine range resolution
    ✓ Penetrates rain, fog, dust (unlike LiDAR)
    ✓ All-weather operation
  
  Range resolution: ΔR = c / (2 × BW) = 3×10⁸ / (2 × 4×10⁹) ≈ 3.75 cm
```

### 1.2 FMCW (Frequency Modulated Continuous Wave) Operation

```
FMCW RADAR CHIRP:

Frequency
  │
  │          /|    /|    /|
  │         / |   / |   / |
  │        /  |  /  |  /  |
  │ f_start   | /   | /   |
  │────────────────────────── Time
  │       ├──T──┤
  │     One chirp period T
  
  Transmitted: f_start to f_start + BW over time T
  Received:    delayed copy of transmitted (delay = 2R/c)
  
  Beat frequency (IF signal):
    f_beat = (BW / T) × (2R / c)
    
  Solving for range:
    R = f_beat × c × T / (2 × BW)

EXAMPLE:
  BW = 4 GHz, T = 100 μs, f_beat = 100 kHz
  R = 100×10³ × 3×10⁸ × 100×10⁻⁶ / (2 × 4×10⁹)
  R = 3×10¹² / 8×10⁹ = 375 m
  (Typical real range: 0.5 – 250 m for long-range radar)
```

### 1.3 Velocity Measurement (Doppler)

```
DOPPLER EFFECT:
  A moving target shifts the beat frequency by Doppler shift:
  
  f_doppler = 2 × v_rel × f_carrier / c
            = 2 × v_rel × 77×10⁹ / 3×10⁸
            = 2 × v_rel × 256.7 Hz per m/s

  Velocity from Doppler:
    v_rel = f_doppler × c / (2 × f_carrier)
  
EXAMPLE:
  f_doppler = 2000 Hz (2 kHz beat frequency shift)
  v_rel = 2000 × 3×10⁸ / (2 × 77×10⁹)
        = 6×10¹¹ / 1.54×10¹¹
        ≈ 3.9 m/s ≈ 14 km/h (approaching)

Positive f_doppler = approaching target
Negative f_doppler = receding target

VELOCITY RESOLUTION:
  Δv = λ / (2 × N_chirps × T)
  Higher N_chirps in a frame → finer velocity resolution
```

### 1.4 Azimuth (Angle) Measurement

```
ANGLE MEASUREMENT VIA ANTENNA ARRAY:
  Multiple RX antennas separated by d = λ/2
  Phase difference between adjacent RX antennas:
  
  Δφ = 2π × d × sin(θ) / λ
  
  Solving for angle:
    θ = arcsin(Δφ × λ / (2π × d))
  
  Angular resolution: Δθ ≈ λ / (N_ant × d)
  
  EXAMPLE (8 RX antennas, d = λ/2):
  Δθ ≈ λ / (8 × λ/2) = 1/4 rad ≈ 14.3°
  
  With 2D MIMO (4TX × 4RX = 16 virtual antennas):
  Δθ ≈ λ / (16 × λ/2) = 1/8 rad ≈ 7.2°

TYPICAL AUTOMOTIVE RADAR SPECS:
  Parameter          Long-Range (LRR)    Short-Range (SRR)
  ─────────────────────────────────────────────────────────
  Range              0.5 – 250 m         0.1 – 30 m
  Range resolution   < 0.4 m             < 0.15 m
  Velocity range     ±70 m/s             ±30 m/s
  Azimuth FoV        ±9° (narrow)        ±75° (wide)
  Update rate        20 ms (50 Hz)       50 ms (20 Hz)
  Use case           ACC, AEB, FCW       BSD, PAS, RCTA
```

---

## 2. RADAR OBJECT LIST FORMAT

```
RADAR OBJECT MESSAGE (typical CAN/Ethernet output):
  
  Each detected object:
  ┌─────────────────────────────────────────────────────┐
  │ Field           Bits  Unit      Range               │
  │─────────────────────────────────────────────────────│
  │ Object ID       6     -         0–63                │
  │ Longitudinal x  13    0.1 m    -200 to 200 m        │
  │ Lateral y       11    0.1 m    -50 to 50 m          │
  │ Velo longit.    11    0.1 m/s  -70 to 70 m/s        │
  │ Velo lateral    9     0.1 m/s  -20 to 20 m/s        │
  │ RCS             7     0.5 dBsm -50 to 13 dBsm       │
  │ Object type     3     -        Unknown/Car/Truck/Ped │
  │ Probability     2     -        0/25/50/75%           │
  │ MeasState       3     -        New/Measured/Predicted│
  └─────────────────────────────────────────────────────┘

RCS = Radar Cross Section
  Car:        10–30 dBsm
  Motorcycle:  0–10 dBsm
  Pedestrian: -10–0 dBsm
  Bicycle:    -15–-5 dBsm
  Drain grate: 20+ dBsm (strong reflector → false positive source)
```

---

## 3. LIDAR PRINCIPLES

### 3.1 LiDAR Types Comparison

```
LIDAR TECHNOLOGY COMPARISON:

                   Mechanical         Solid-State      FMCW LiDAR
                   Rotating           Flash/MEMS        (4D)
  ─────────────────────────────────────────────────────────────────
  Principle        Spinning mirror    Phased array      Coherent freq
                   + 905nm laser      or MEMS mirror    + Doppler
  
  Range            200 m              150 m             300 m
  FoV (H)          360°               60–120°           120°
  FoV (V)          ±15°               ±20°              ±15°
  Points/sec       100K–1.3M          200K              500K+
  Velocity         No (ToF only)      No                YES (Doppler)
  Weather resist   Moderate           Better            Best
  Durability       Moderate (moving)  High (no moving)  High
  Cost (2024)      $500–$5000         $200–$2000        $1000–$8000
  
  Examples:
    Mechanical:  Velodyne VLP-16, Ouster OS1
    Solid-state: Innoviz ONE, Continental HRL131
    FMCW:        Aeva Aeries II, Aurora

AUTOMOTIVE STATUS (2024):
  L2+/L3: mainly cameras + radar (LiDAR optional)
  L4 production: Volvo EX90 (Luminar Iris), Waymo One
```

### 3.2 LiDAR Point Cloud Format

```
POINT CLOUD DATA FORMAT:
  Each point = (x, y, z, intensity)
  
  Coordinate system (ISO 8855):
    x = forward (positive forward)
    y = left (positive left)
    z = up (positive up)
    Origin = center of rear axle
  
  Common storage formats:
    PCD (Point Cloud Data):  ASCII or binary, used by PCL library
    LAS/LAZ:                 standard geospatial, aviation-grade
    MCAP/ROS bag:            autonomous driving (replay in Foxglove)
    Custom binary:           OEM-specific, real-time streaming
  
POINT CLOUD DENSITY EXAMPLE (Velodyne VLP-16):
  16 beams × 1800 azimuth points/revolution × 10 Hz = 288,000 points/sec
  At 100m range, angular resolution 0.2° → point spacing ≈ 0.35m at 100m

POINT CLOUD SEGMENTATION (typical pipeline):
  Raw cloud → Ground removal → Clustering → Bounding box → Classification
  Ground removal: RANSAC plane fitting (remove flat ground plane)
  Clustering:     DBSCAN or voxel grid
  Classification: PointNet / BEV projection + CNN
```

---

## 4. SENSOR FUSION COORDINATE FRAME TRANSFORMS

```
COORDINATE FRAME TRANSFORMS FOR SENSOR FUSION:

Each sensor has its own mounting position and orientation on the vehicle.
Before fusing, all data must be in a common vehicle frame.

Transform from sensor frame to vehicle frame:
  P_vehicle = R × P_sensor + T
  
  R = rotation matrix (3×3)
  T = translation vector (3×1)
  
For a front radar mounted at:
  Position: x=3.5m (front of car), y=0, z=0.7m (height)
  Orientation: 0° tilt, 0° azimuth
  
  T = [3.5, 0, 0.7]ᵀ  meters
  R = identity (no rotation)
  P_vehicle = P_radar + T

For a left-rear corner radar mounted at:
  Position: x=-2.5m (rear), y=0.9m (left), z=0.5m
  Orientation: yaw=135° (pointing rear-left)
  
  T = [-2.5, 0.9, 0.5]ᵀ
  R = rotation by 135° around z-axis

EXTRINSIC CALIBRATION:
  At vehicle assembly, sensors are mounted with mechanical tolerance ≈ ±5mm, ±0.5°
  Calibration procedure:
    1. Drive past corner reflectors at known positions
    2. Algorithm computes optimal R, T to minimize detection error
    3. Calibration values stored in NvM (DID 0xF1A1 = radar calibration)
  
  If calibration is off by 1° at 100m range:
    Lateral error = 100m × sin(1°) ≈ 1.75m
    → At highway speed, this means wrong lane assignment → ACC follows wrong vehicle
```

---

## 5. RADAR/LIDAR INTERFACE PROTOCOLS

```
SENSOR INTERFACE TO ADAS ECU:

Radar → ADAS ECU via CAN (traditional):
  CAN speed: 500 kbps or 1 Mbps
  Message: radar_object_1 (0x300), radar_object_2 (0x301)... up to 64 objects
  Update rate: 50 Hz (20ms cycle)
  
Radar → ADAS ECU via Automotive Ethernet (modern):
  Protocol: typically SOME/IP or simple UDP
  Speed: 100BASE-T1 (100 Mbps) — enough for object lists
  LiDAR raw point cloud via 1000BASE-T1 (1 Gbps)
  
LiDAR → ADAS ECU:
  Raw UDP multicast (Velodyne-style): port 2368, ~1.3M points/sec
  Object list (post-processed): SOME/IP or CAN (if condensed)

CAMERA → ADAS ECU:
  Typically MIPI CSI-2 (direct to SoC)
  Or Automotive SerDes: GMSL2 (Maxim) or FPD-Link III (TI)
  Bandwidth: 4K@30fps ≈ 1.5 Gbps per camera
  ADAS SoC has dedicated ISP for each camera lane
```

---

## 6. TEST CASES

```
TC-RLIDAR-001: Radar Range Accuracy Verification
  Setup: Corner reflector at known distance (25m, 50m, 100m)
  Action: Record radar object list for 10 seconds per distance
  Expected: Measured range within ±0.5m of known distance
  Pass criteria: 95% of samples within tolerance

TC-RLIDAR-002: Radar Velocity Measurement
  Setup: Moving target platform at 30 km/h and 60 km/h
  Action: Record radar Doppler velocity vs. reference GPS speed
  Expected: Velocity error < ±1 km/h
  Pass criteria: RMSE < 0.3 m/s

TC-RLIDAR-003: LiDAR Coordinate Frame Alignment
  Setup: Calibration board at known position (10m, 0° azimuth, 0.5m height)
  Action: Record LiDAR point cloud, extract board centroid
  Expected: Centroid within ±5cm of known position in vehicle frame
  Pass criteria: All 3 axes within tolerance

TC-RLIDAR-004: Rain Degradation Test
  Setup: Rain simulator (water spray at 50mm/hour rate)
  Action: Repeat TC-RLIDAR-001 with rain active
  Expected: Detection range reduced by < 30% vs. dry condition
  Pass criteria: > 70% range maintained; valid detection rate > 80%
```

---

## 7. INTERVIEW Q&A

**Q1: How does FMCW radar measure both range and velocity simultaneously?**
> FMCW radar transmits a chirp — a frequency that sweeps from f_start to f_start + BW over time T. The received signal is mixed with the transmit signal to produce a beat frequency proportional to range (f_beat = 2R × BW / (c × T)). Velocity is measured by transmitting multiple chirps and measuring the phase change of the beat signal between chirps — this phase change is the Doppler shift. By processing a "frame" of N chirps with 2D FFT (range FFT + Doppler FFT), both range and velocity are extracted simultaneously.

**Q2: What is the difference between early and late sensor fusion?**
> Early fusion combines raw sensor data (raw radar points + raw LiDAR points + raw image pixels) before any detection processing — maximum information but very high compute. Late fusion runs each sensor through its own detection/tracking pipeline first, producing object lists, then merges the object lists. Late fusion is standard in automotive because each sensor ECU can be developed and certified independently, and a single sensor failure degrades the fused output gracefully without crashing the whole perception stack.

**Q3: Why does a metal drain cover cause AEB false positives?**
> A metal drain cover has a very high radar cross-section (RCS > 20 dBsm) and is stationary at road level. The radar correctly detects it as a strong stationary return. The AEB algorithm without a height filter interprets it as a stopped car. Fix: add a height plausibility filter — if a stationary object is at road level AND has very high RCS (typical of flat metal surfaces), require 3+ consecutive detections before treating it as a vehicle. Camera-based height verification can also filter ground-plane objects.

**Q4: What is extrinsic calibration and why does it matter?**
> Extrinsic calibration determines the precise position (translation) and orientation (rotation) of each sensor relative to the vehicle coordinate frame. This is required before sensor fusion because each sensor produces data in its own local frame. If a radar calibration is off by 1° in yaw, at 100m range this creates a 1.75m lateral error — enough to misassign a target to the wrong lane. Calibration is performed at the assembly line using corner reflectors at known positions.

**Q5: What are the key differences between a mechanical spinning LiDAR and a solid-state LiDAR?**
> Mechanical LiDAR (e.g., Velodyne) uses a rotating mirror to achieve 360° horizontal FoV. High point density, proven technology, but has a rotating mechanical part (MTBF concern for production vehicles). Solid-state LiDAR uses phased arrays or MEMS mirrors — no moving parts, more durable and compact, but typically limited to 60–120° FoV per unit (multiple needed for 360°). FMCW LiDAR adds velocity measurement per point (direct Doppler), which eliminates velocity ambiguity and reduces ghost objects, but is currently more expensive.

---

*Next: [02_STAR_Answers.md](02_STAR_Answers.md)*
