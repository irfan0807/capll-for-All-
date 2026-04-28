# ADAS Sensor Technologies – Deep Dive

## 1. LiDAR (Light Detection and Ranging)

### Operating Principle

```
Emitter pulses laser → photon travels at speed of light c
Receiver detects reflected pulse
Range = (c × time-of-flight) / 2

Time-of-flight resolution Δt → range resolution Δr = c·Δt/2
  Δt = 1ns → Δr = 0.15m
  Δt = 100ps → Δr = 1.5cm (modern ASICs)

Beam Steering Methods:
  1. Mechanical spinning (Velodyne HDL-64E) – mature, 360°, expensive
  2. MEMS mirror (Continental HFL110)       – compact, limited FOV
  3. Optical phased array (Intel RealSense) – no moving parts (future)
  4. Flash LiDAR                            – full scene at once, short range
```

### Point Cloud Data Format

```cpp
struct LidarPoint {
    float x;            // Meters, ego vehicle frame
    float y;            // Meters
    float z;            // Meters (positive up)
    float intensity;    // 0.0 – 1.0 (reflectivity)
    uint8_t ring;       // Beam index (0 = lowest)
    uint32_t timestamp; // microseconds since epoch
};

// Coordinate frame (ISO 8855):
//   x = forward
//   y = left
//   z = up
// Transform from sensor frame: multiply by calibration extrinsic matrix
```

### Ground Plane Removal (RANSAC)

```
Algorithm:
1. Random sample 3 points from cloud
2. Fit plane equation ax + by + cz + d = 0
3. Count inliers (distance to plane < threshold, e.g. 15cm)
4. Repeat N iterations (N = 100 sufficient for 95% ground noise)
5. Best-fit plane = ground, remove from cloud
6. Remaining points = obstacle candidates
```

### Clustering (DBSCAN for object detection)

```
Parameters:
  epsilon = 0.5m (neighborhood radius)
  minPoints = 5

Algorithm:
1. Mark all points as unvisited
2. For each point, find all points within epsilon
3. If >= minPoints neighbors: start new cluster, expand recursively
4. Else: mark as noise (irrelevant)
5. Each cluster → bounding box → object hypothesis
```

---

## 2. Camera

### Image Processing Pipeline

```
RAW Bayer RGGB → ISP (dead pixel correct, black level) →
Demosaicing → White balance → Gamma correction →
Lens undistortion (Brown-Conrady model) →
→ NN Inference (object detection, lane seg)
→ Stereo matching (disparity → depth) [for stereo pairs]
```

### Intrinsic Calibration (Pinhole Model)

```
Projection:
  u = fx · (X/Z) + cx
  v = fy · (Y/Z) + cy

Calibration matrix K:
  K = [fx   0  cx]
      [ 0  fy  cy]
      [ 0   0   1]

Distortion coefficients (Brown-Conrady):
  k1, k2, p1, p2, k3 (radial k1/k2/k3, tangential p1/p2)

Calibration tool: OpenCV calibrateCamera()
  - Checkerboard 9×6, 30mm squares
  - Minimum 20 poses, RMS reprojection error < 0.5 px
```

### Lane Detection Algorithm

```
Step 1: Perspective transform (IPM – Inverse Perspective Mapping)
  Front camera → Bird's Eye View (BEV)
  Removes near-far size variation

Step 2: Lane marking extraction
  Gradient filter (Sobel X) → threshold → morphological close
  OR
  Semantic segmentation NN → lane pixel mask

Step 3: Lane curve fitting (polynomial)
  f(y) = a·y² + b·y + c  (2nd order Bezier)
  Fit using least squares to detected lane pixels

Step 4: Ego position in lane
  Lane center = (left_x + right_x) / 2  at ego y
  Lateral offset = ego_x - lane_center_x

Step 5: Output
  - Lane width, curvature, lateral offset
  - Lane quality score (number of inlier pixels)
```

### Object Detection with Neural Network

```
Network: YOLOv8 (You Only Look Once version 8)

Architecture:
  Backbone (CSPDarknet) → neck (PANet) → head (decoupled)

Input:  640×640×3 RGB
Output: N detections × [cx, cy, w, h, confidence, class_scores×80]

Post-processing:
  1. Filter by confidence > 0.5
  2. NMS (Non-Maximum Suppression, IoU threshold 0.45)
  3. Output: {class, bbox_pixels, confidence}

Inference time:
  GPU (Tesla T4): 4ms
  Automotive SoC (Orin): 12ms
  CPU only: 120ms (not real-time for L4)

COCO classes used: car, truck, bus, motorcycle, bicycle, person
```

---

## 3. Radar

### FMCW (Frequency Modulated Continuous Wave) Principle

```
Tx: chirp signal sweeping from f_start to f_stop in T_chirp time
    f(t) = f_start + (B/T_chirp) · t    (B = bandwidth, e.g. 4GHz @ 77GHz)

Rx: delayed, doppler-shifted echo

Beat frequency f_beat = 2·R·(B/T_chirp)/c   → Range:  R = c·f_beat·T_chirp / (2B)
Doppler frequency f_D = 2·v·f_carrier/c     → Speed:  v = f_D·c / (2·f_carrier)

Range resolution:    ΔR = c/(2B)         [B=4GHz → ΔR=3.75cm]
Velocity resolution: Δv = c/(2·f_c·T_CPI) [T_CPI=50ms → Δv=0.039 m/s]
Angular resolution:  Δθ = 0.9·λ/(N·d)    [N=12 Rx → Δθ≈5° at 77GHz]
```

### Radar Object List Format

```cpp
struct RadarObject {
    uint8_t  id;              // 0-63 tracked objects
    float    range_m;         // Radial distance in meters
    float    azimuth_deg;     // Horizontal angle (+ = left)
    float    elevation_deg;   // Vertical angle
    float    range_rate_ms;   // Radial velocity (m/s, negative = approaching)
    float    rcs_dbsm;        // Radar cross-section (object size indicator)
    uint8_t  confidence;      // 0-100%
    uint8_t  dynamic_prop;    // STATIONARY, MOVING, ONCOMING, CROSSING
};
```

### Radar vs LiDAR vs Camera Comparison

| Property | LiDAR | Camera | Radar |
|---------|-------|--------|-------|
| Range | 200m | 100m (mono) | 250m |
| Lateral resolution | High | High | Low |
| Velocity measurement | Derived | Derived | **Direct** |
| Night operation | **Yes** | Limited | **Yes** |
| Rain/fog | Poor reflections | Poor | **Best** |
| 3D geometry | **Best** | Stereo only | Low res |
| Classification | Shape-based | **Best (NN)** | Limited |
| Cost | High | Low | Medium |

---

## 4. IMU (Inertial Measurement Unit)

### Dead Reckoning

```
When GPS is unavailable (tunnel, parking), use IMU dead reckoning:

Position update (trapezoidal integration):
  v_k = v_{k-1} + a_k · Δt
  p_k = p_{k-1} + v_k · Δt

Errors accumulate:
  Position error ≈ 0.5 · σ_a · t²
  For σ_a = 0.01 m/s² (tactical MEMS), after 10s: error ≈ 0.5m

Correction:
  Fuse IMU preintegration with GPS/LiDAR localization via EKF
```

### Sensor Calibration – Extrinsic (sensor-to-vehicle transform)

```
Each sensor has a 6-DOF pose relative to vehicle frame:
  T_sensor_to_vehicle = [R|t]  (4×4 transformation matrix)

R = rotation (3×3, roll/pitch/yaw)
t = translation (3×1, x/y/z in meters)

Calibration methods:
  LiDAR-Camera: checkerboard in scene → match 3D-2D correspondences
  Radar-LiDAR:  corner reflector known position → match range
  IMU-vehicle:  factory alignment + online estimation (moveability)
```

---

## 5. GNSS + HD Map Localization

### Localization Pipeline

```
1. GNSS RTK (when available, <2cm absolute accuracy)
   - RTK corrections from base station or NTRIP service
   - Outage: tunnel, urban canyon, multi-path

2. LiDAR Localization (NDT/ICP map matching)
   - NDT = Normal Distributions Transform
   - Match live point cloud vs pre-built HD map 3D layer
   - Accuracy: 5-10cm in mapped areas
   - Works without GPS

3. Camera Visual Localization
   - Feature matching vs HD map imagery layer
   - Less accurate than LiDAR but supplemental

4. Dead Reckoning (IMU + wheel odometry)
   - Short-term bridge during sensor outage

5. Sensor fusion (EKF/UKF)
   - State: [x, y, z, roll, pitch, yaw]
   - Inputs: GNSS, LiDAR_loc, IMU, odometry
   - Output: pose with uncertainty covariance
```

---

## 6. Sensor Failure Detection

```cpp
// Sanity checks per sensor:

// LiDAR: check point count per cycle
if (pointCloud.size() < 50000 || pointCloud.size() > 2000000) {
    reportFault(SENSOR_LIDAR, FAULT_POINT_COUNT_OUTOFRNG);
}

// Camera: check frame freshness
if (now_ms - camera.lastFrameTime_ms > 100) {  // 10Hz minimum
    reportFault(SENSOR_CAMERA, FAULT_FRAME_TIMEOUT);
}

// Radar: check object list consistency
if (radar.detectedObjects == 0 && ego_speed > 10.0f) {
    // Likely a hardware fault if driving at speed with no detections
    reportFault(SENSOR_RADAR, FAULT_NO_DETECTIONS);
}

// IMU: check acceleration range
if (fabsf(imu.ax) > 20.0f || fabsf(imu.ay) > 20.0f) {
    reportFault(SENSOR_IMU, FAULT_ACCELERATION_OOR);
}
```
