# C++ Implementation Deep Dive – ADAS Level 4 Project

This document explains exactly **what C++ language features are used**, **why they are used**, and **how each module is implemented**, with direct references to the source code.

---

## Table of Contents

1. [C++ Language Features Used Across the Project](#1-c-language-features-used-across-the-project)
2. [Sensor Layer – LiDAR](#2-sensor-layer--lidar)
3. [Sensor Layer – Radar, Camera, IMU](#3-sensor-layer--radar-camera-imu)
4. [Perception – Extended Kalman Filter (EKF) Sensor Fusion](#4-perception--extended-kalman-filter-ekf-sensor-fusion)
5. [Perception – Lane Detector](#5-perception--lane-detector)
6. [Planning – Path Planner](#6-planning--path-planner)
7. [Planning – Trajectory Generator](#7-planning--trajectory-generator)
8. [Control – PID Controller](#8-control--pid-controller)
9. [Control – Vehicle Controller (Stanley)](#9-control--vehicle-controller-stanley)
10. [Safety – Safety Monitor (ASIL-D Watchdog)](#10-safety--safety-monitor-asil-d-watchdog)
11. [Safety – ADAS FSM](#11-safety--adas-fsm)
12. [Safety – Emergency Handler](#12-safety--emergency-handler)
13. [CAN Bus – Frame Encoding and Transmission](#13-can-bus--frame-encoding-and-transmission)
14. [Memory Layout and Embedded Constraints](#14-memory-layout-and-embedded-constraints)
15. [Namespaces and Module Boundaries](#15-namespaces-and-module-boundaries)
16. [Unit Test Architecture](#16-unit-test-architecture)

---

## 1. C++ Language Features Used Across the Project

### Standard Version: C++14

The CMakeLists.txt sets `set(CMAKE_CXX_STANDARD 14)`. C++14 is chosen because:
- It is widely supported on automotive-grade toolchains (Green Hills MULTI, IAR, ARM Compiler).
- `constexpr` functions (C++11/14) replace preprocessor `#define` for type-safe constants.
- `auto` and range-based `for` are available but avoided in safety-critical paths to keep type visibility clear.

### Key C++ features and where they appear

| C++ Feature | Where Used | Why |
|-------------|-----------|-----|
| `class` with member initialiser list | Every class constructor | Ensures deterministic initialisation order |
| `const` member functions | All getters (`getHealth()`, `getScan()`, etc.) | Enforce read-only semantics, allow `const` object use |
| `static constexpr` | Thresholds, array sizes, PID gains | Type-safe compile-time constants, no heap, no linker symbol |
| `#pragma once` | All headers | Prevents double-inclusion without using include guards |
| Nested namespaces | `adas::`, `adas::perception::`, `adas::planning::`, etc. | Module isolation; avoids name clashes |
| `enum class` | `SensorHealth`, `TrackState`, `BehaviorState`, `SafetyDecision`, `AdasSystemState` | Scoped enum, no implicit int conversion, safer switch |
| `struct` for POD data | `LidarPoint`, `RadarObject`, `TrackedObject`, `CanFrame`, `FaultFlags` | Plain data, no virtual dispatch, predictable layout |
| `memset` / `memcpy` (via `<cstring>`) | All constructors that zero-initialise fixed arrays | Deterministic zeroing without STL containers |
| `static` (file-scope) | `kfUpdate2D()` in sensor_fusion.cpp, LUT tables in trajectory_generator | Restricts linkage to translation unit; avoids namespace pollution |
| `static` (function-local) | `makeLidarScan` buffer, LATERAL_TARGETS, TIME_HORIZONS in trajectory gen | Allocates large arrays in BSS/data segment, not stack |
| `const` reference parameters | All `setX(const T&)` methods | Avoids value-copy of large structs; signals no mutation |
| Pointer-to-function callback | `CanTxFn` typedef, `m_txFn` | Decoupled hardware abstraction (HAL pattern) |
| `uint8_t`, `uint16_t`, `uint32_t`, `int16_t` | All data structs and loop variables | Explicit-width types required by MISRA C++ Rule 3-9-2 |
| No `new` / `delete` | Entire project | No dynamic memory allocation (MISRA, ISO 26262 ASIL D) |
| No exceptions | Entire project (`-fno-exceptions` implicit by usage) | Embedded requirement; deterministic error paths only |
| No STL containers | Entire project | No `std::vector`, `std::map` etc.; fixed-size arrays only |

---

## 2. Sensor Layer – LiDAR

### File: `src/sensors/lidar_sensor.cpp`

#### Class Design

```cpp
class LidarSensor {
    LidarScan    m_rawScan;         // fixed 150 000-point array (BSS if static)
    LidarScan    m_obstacleScan;    // output after ground removal
    float        m_groundA, m_groundB, m_groundC, m_groundD; // plane equation
    SensorHealth m_health;
    uint32_t     m_lastTimestamp_ms;
    uint32_t     m_systemTime_ms;
    ...
};
```

Two `LidarScan` members hold up to `MAX_LIDAR_POINTS = 150 000` points each. Because `LidarScan` is a POD `struct` containing a fixed C-array, it is placed in the BSS segment when declared `static`, avoiding a 3 MB stack overflow.

#### Constructor (Member Initialiser List)

```cpp
LidarSensor::LidarSensor()
    : m_groundA(0.0f), m_groundB(0.0f), m_groundC(1.0f), m_groundD(0.0f),
      m_health(SensorHealth::INIT),
      m_lastTimestamp_ms(0), m_systemTime_ms(0)
{
    m_rawScan.count       = 0;
    m_obstacleScan.count  = 0;
}
```

The member initialiser list is used for scalar members because the C++ standard initialises them **in declaration order** before the body runs. The zero-init assignments for the `LidarScan` struct members are in the body because they are aggregate members (no constructor).

#### RANSAC Ground Plane Removal – Implementation Detail

**Step 1 – Random three-point sampling (LCG RNG)**

```cpp
uint32_t rng = 12345U;
for (uint32_t iter = 0; iter < RANSAC_ITERATIONS; ++iter) {
    rng = rng * 1664525U + 1013904223U;   // Numerical Recipes LCG
    uint32_t i1 = rng % m_rawScan.count;
    ...
}
```

A **Linear Congruential Generator (LCG)** is used instead of `<random>` because:
- No STL allowed.
- Deterministic seed `12345U` gives reproducible results for testing.
- LCG is a single multiply + add — O(1), no allocation.

**Step 2 – Plane fit via cross product**

```cpp
bool LidarSensor::fitPlane(const LidarPoint& p1, const LidarPoint& p2,
                            const LidarPoint& p3,
                            float& a, float& b, float& c, float& d) const {
    float ux = p2.x - p1.x, uy = ..., uz = ...;
    float vx = p3.x - p1.x, vy = ..., vz = ...;
    a = uy*vz - uz*vy;   // cross product (normal vector)
    b = uz*vx - ux*vz;
    c = ux*vy - uy*vx;
    float len = sqrtf(a*a + b*b + c*c);
    if (len < 1e-6f) return false;  // degenerate (collinear)
    a /= len; b /= len; c /= len;
    d = -(a*p1.x + b*p1.y + c*p1.z);
    return true;
}
```

- `float&` output parameters instead of returning a struct — avoids stack copy.
- `return false` on degenerate case — defensive programming without exceptions.
- The normal is **normalised** so that `|a*x + b*y + c*z + d|` is the actual Euclidean distance in metres.

**Step 3 – Ground constraint check**

```cpp
if (c < 0.8f) continue;   // reject: normal is not pointing upward
```

Ground planes have their Z-component of the normal close to 1.0. This rejects vertical walls and overhead objects.

**Step 4 – Inlier copy (non-ground obstacles)**

```cpp
float dist = fabsf(bestA*p.x + bestB*p.y + bestC*p.z + bestD);
if (dist >= GROUND_DIST_THRESHOLD) {
    m_obstacleScan.points[obsCount++] = p;
}
```

`GROUND_DIST_THRESHOLD = 0.15f` metres. Points farther than 15 cm from the ground plane are obstacles.

#### Timeout detection (cyclic100ms)

```cpp
void LidarSensor::cyclic100ms() {
    m_systemTime_ms += 100U;
    if (m_lastTimestamp_ms > 0 &&
        (m_systemTime_ms - m_lastTimestamp_ms) > TIMEOUT_THRESHOLD_MS) {
        m_health = SensorHealth::FAILED;
    }
}
```

The system uses **unsigned arithmetic** for time deltas. Wrapping is handled correctly because `(uint32_t)(a - b)` gives the correct elapsed milliseconds even when `m_systemTime_ms` wraps around.

---

## 3. Sensor Layer – Radar, Camera, IMU

### Radar (`src/sensors/radar_sensor.cpp`)

Same `inject + cyclic100ms` pattern as LiDAR.  
The radar stores a `RadarScan` with up to 64 `RadarObject` entries, each containing:
- `range_m` – distance in metres
- `azimuth_deg` – angle in the horizontal plane
- `range_rate_mps` – Doppler velocity (radial, positive = receding)

The Doppler field is crucial; it provides direct velocity measurement that would require two scan comparisons with LiDAR.

### Camera (`src/sensors/camera_sensor.cpp`)

Stores a `CameraFrame` with:
- Up to `MAX_CAMERA_OBJECTS = 32` `CameraDetection` entries (bounding boxes + class)
- Lane metadata: `left_lane_offset_m`, `right_lane_offset_m`, `lane_width_m`, `lane_quality` (0–100)

`lane_quality` is an `uint8_t` representing classifier confidence. It decays each cycle that no new frame arrives (implemented in `LaneDetector`).

### IMU (`src/sensors/imu_sensor.cpp`)

The IMU adds **plausibility checking** before accepting data:

```cpp
bool ImuSensor::isDataPlausible(const ImuData& d) const {
    if (fabsf(d.ax) > MAX_ACCEL_MPS2 ||   // 20 m/s² ~ 2g
        fabsf(d.ay) > MAX_ACCEL_MPS2 ||
        fabsf(d.az) > MAX_ACCEL_MPS2) return false;
    if (fabsf(d.gx) > MAX_GYRO_RADPS ||   // 5.24 rad/s ~ 300°/s
        fabsf(d.gy) > MAX_GYRO_RADPS ||
        fabsf(d.gz) > MAX_GYRO_RADPS) return false;
    return true;
}
```

If implausible: health is set to `DEGRADED` (not `FAILED`) — the sensor is not broken, just reading an out-of-range value (e.g., hard bump). A `FAILED` state requires a timeout without any valid data.

```cpp
void ImuSensor::injectData(const ImuData& data) {
    if (!isDataPlausible(data)) {
        m_health = SensorHealth::DEGRADED;
        return;   // do not update m_data – keep last valid
    }
    m_data = data;
    m_health = SensorHealth::OK;
}
```

**Key C++ pattern**: early `return` on error avoids deep nesting (no exceptions, no `goto`).

---

## 4. Perception – Extended Kalman Filter (EKF) Sensor Fusion

### File: `src/perception/sensor_fusion.cpp`

This is the most mathematically complex module. It maintains up to 32 independent tracks, each with its own 8×8 Kalman filter state.

#### State Vector (8 DOF per track)

```
x = [ px,  py,  vx,  vy,  ax,  ay,  yaw,  yaw_rate ]
        0    1    2    3    4    5    6         7
```

All stored as `float x[8]` and covariance `float P[8][8]` in `KFState`.

#### Matrix Storage

Matrices are stored as **2D C-arrays** `float M[8][8]`, not `std::array` or `std::vector`, because:
- Zero-overhead — layout is identical to a flat 64-float block.
- `memset` can zero them in one call.
- Compatible with MISRA rules forbidding dynamic allocation.

#### buildF — State Transition Matrix

```cpp
void SensorFusion::buildF(float F[8][8], float dt) const {
    // Identity base
    for (int i = 0; i < 8; i++)
        for (int j = 0; j < 8; j++)
            F[i][j] = (i == j) ? 1.0f : 0.0f;

    float dt2 = 0.5f * dt * dt;
    F[0][2] = dt;   F[0][4] = dt2;   // px += vx*dt + ax*dt²/2
    F[1][3] = dt;   F[1][5] = dt2;   // py += vy*dt + ay*dt²/2
    F[2][4] = dt;                     // vx += ax*dt
    F[3][5] = dt;                     // vy += ay*dt
    F[6][7] = dt;                     // yaw += yaw_rate*dt
}
```

This encodes the **constant-acceleration kinematic model** in matrix form. The ternary `(i==j)?1:0` builds the identity in O(n²) without `memset` + sparse fill.

#### Predict Step

$$\hat{x}_{k|k-1} = F \hat{x}_{k-1}$$
$$P_{k|k-1} = F P_{k-1} F^T + Q$$

```cpp
void SensorFusion::predictAll(float dt_s) {
    float F[8][8], Ft[8][8], FP[8][8], FPFt[8][8];
    buildF(F, dt_s);
    transposeF(F, Ft);

    for (uint8_t t = 0; t < m_trackCount; ++t) {
        KFState& s = m_states[t];
        // x = F * x
        float xnew[8] = {};
        for (int i = 0; i < 8; i++)
            for (int k = 0; k < 8; k++) xnew[i] += F[i][k] * s.x[k];
        for (int i = 0; i < 8; i++) s.x[i] = xnew[i];

        // P = F*P*Ft + Q
        matMul8(F, s.P, FP);
        matMul8(FP, Ft, FPFt);
        for (int i = 0; i < 8; i++) s.P[i][i] = FPFt[i][i];
        s.P[2][2] += sigma2;        // vx process noise
        s.P[3][3] += sigma2;        // vy process noise
    }
}
```

`float xnew[8] = {}` uses **value-initialisation** (`= {}`) — all 8 elements set to 0.0f. This is the C++ equivalent of `memset` for VLA-like arrays and does not require `<cstring>`.

#### Update Step (kfUpdate2D — file-static function)

```cpp
static void kfUpdate2D(KFState& s, float ox, float oy, float R_noise = 0.25f) {
    float y0 = ox - s.x[0];   // innovation
    float y1 = oy - s.x[1];

    float S00 = s.P[0][0] + R_noise;  // innovation covariance
    float S11 = s.P[1][1] + R_noise;

    float K0[8], K1[8];   // Kalman gain columns
    for (int i = 0; i < 8; i++) {
        K0[i] = s.P[i][0] / S00;
        K1[i] = s.P[i][1] / S11;
    }

    for (int i = 0; i < 8; i++)
        s.x[i] += K0[i] * y0 + K1[i] * y1;

    for (int i = 0; i < 8; i++)
        for (int j = 0; j < 8; j++)
            s.P[i][j] -= K0[i] * s.P[0][j] + K1[i] * s.P[1][j];
}
```

This function is declared `static` (internal linkage) because it is a pure  mathematical helper — it only uses its arguments and manipulates no class state. Making it a non-member function also avoids an extra `this` pointer indirection per call.

The measurement model $H = [1,0,0,0,0,0,0,0; 0,1,0,0,0,0,0,0]$ is applied implicitly: `s.P[i][0]` is column 0 of $P$, i.e., $P \cdot H_0^T$. This exploits the fact that $H$ is a selector matrix and avoids the full $H P H^T$ matrix multiply.

#### Data Association – Mahalanobis Distance

```cpp
float SensorFusion::mahalanobisDistance(const KFState& s, float ox, float oy) const {
    float dx = ox - s.x[0];
    float dy = oy - s.x[1];
    float S00 = s.P[0][0] + 0.25f;
    float S11 = s.P[1][1] + 0.25f;
    return (dx*dx / S00) + (dy*dy / S11);   // diagonal approx
}
```

$$d_M^2 = \frac{(\Delta x)^2}{P_{00}+R} + \frac{(\Delta y)^2}{P_{11}+R}$$

The nearest-neighbour gate uses `GATE_THRESHOLD = 9.21` (chi-squared 99.5% for 2 DOF). If no track is within the gate, a new track is created. If the track array is full (`MAX_TRACKED_OBJECTS = 32`), the measurement is discarded rather than overwriting.

#### Track Lifecycle State Machine

```cpp
switch (tr.state) {
    case TrackState::NEW_CANDIDATE:
        if (tr.track_age_cycles >= 2) tr.state = TrackState::PROBABLE;
        break;
    case TrackState::PROBABLE:
        if (tr.track_age_cycles >= 5) tr.state = TrackState::CONFIRMED;
        break;
    case TrackState::CONFIRMED:
        if (tr.miss_count >= 5) tr.state = TrackState::LOST;
        break;
    ...
}
```

The `switch` on an `enum class` without a `default:` branch causes a *compiler warning on unhandled cases*. This is a deliberate design — if a new state is added, the compiler forces you to handle it.

LOST tracks are **compacted** after the lifecycle loop:

```cpp
uint8_t write = 0;
for (uint8_t t = 0; t < m_trackCount; ++t) {
    if (m_tracks[t].state != TrackState::LOST) {
        if (write != t) {
            m_tracks[write] = m_tracks[t];
            m_states[write] = m_states[t];
        }
        write++;
    }
}
m_trackCount = write;
```

This is a **compaction / stable-partition** algorithm: it moves active tracks towards index 0 while preserving relative order. `O(n)` time, zero allocation.

#### TTC (Time To Collision)

```cpp
if (rel_vx < -0.1f && range > 0.0f && tr.is_in_ego_path) {
    tr.ttc_s = -range / rel_vx;
} else {
    tr.ttc_s = INVALID_FLOAT;   // = 99.0f sentinel value
}
```

$\text{TTC} = -\frac{x_{rel}}{v_{rel}}$

The sign convention: `rel_vx < -0.1` means the object is approaching (negative relative velocity). Dividing by a negative number and negating gives a positive TTC. The threshold `-0.1` avoids division by near-zero.

---

## 5. Perception – Lane Detector

### File: `src/perception/lane_detector.cpp`

The lane detector is camera-primary with a quality score that decays each cycle without a fresh frame:

```cpp
void LaneDetector::process() {
    if (m_cameraFrame.lane_quality > 0 && m_cameraFrame.timestamp_ms > 0) {
        m_estimate.lateral_offset_m   = m_cameraFrame.left_lane_offset_m;
        m_estimate.lane_width_m       = m_cameraFrame.lane_width_m;
        m_estimate.curvature_inv_m    = m_cameraFrame.lane_curvature_inv_m;
        m_estimate.quality            = m_cameraFrame.lane_quality;
        m_estimate.left_marking_valid = true;
        m_estimate.right_marking_valid= true;
    } else {
        // Decay quality
        if (m_estimate.quality > 10) m_estimate.quality -= 10;
        else                          m_estimate.quality  = 0;
    }
    m_estimate.valid = (m_estimate.quality > 20);
}
```

Departure detection is a simple threshold:

```cpp
bool LaneDetector::isLaneDeparture(float threshold_m) const {
    return m_estimate.valid &&
           fabsf(m_estimate.lateral_offset_m) > threshold_m;
}
```

`fabsf` (C float version) used throughout instead of `fabs` (double) or `std::abs` — avoids implicit `float → double → float` promotion in embedded builds.

---

## 6. Planning – Path Planner

### File: `src/planning/path_planner.cpp`

#### Behavior Decision (10-State FSM encoded as logic cascade)

Instead of a table-driven FSM, the planner uses a **priority cascade** (highest priority first):

```
1. Object in path + TTC < 1.5s  → EMERGENCY_STOP   (highest)
2. Object in path, x < 80m      → FOLLOW_VEHICLE / ACC
3. Pedestrian within 20m        → YIELD / MUST_STOP
4. Default                      → LANE_FOLLOWING    (lowest)
```

```cpp
void PathPlanner::decideBehavior() {
    m_decision.state = BehaviorState::LANE_FOLLOWING;  // default
    ...
    for (uint8_t i = 0; i < m_objects.count; ++i) {
        if (obj.is_in_ego_path && obj.ttc_s < 1.5f) {
            m_decision.state = BehaviorState::EMERGENCY_STOP;
            return;   // early return on highest priority
        }
        ...
    }
    // pedestrian check
    ...
}
```

**`return` on highest priority** avoids nested `if-else` chains. This is idiomatic C++ for priority-ordered FSMs without `goto`.

#### ACC Follow Speed Calculation

```cpp
float PathPlanner::computeFollowSpeed() const {
    float desired_gap = 3.0f + m_egoSpeed * 1.5f;   // Time-gap = 1.5s
    float gap_error   = minRange - desired_gap;
    float cmd_speed   = leadSpeed + 0.5f * gap_error;
    cmd_speed = clamp(cmd_speed, 0.0f, m_targetSpeed);
    return cmd_speed;
}
```

This implements a **Proportional gap controller**: desired gap grows with speed (time-gap law). The `clamp` is implemented inline with conditional assignment (no `std::clamp` — requires C++17).

---

## 7. Planning – Trajectory Generator

### File: `src/planning/trajectory_generator.cpp`

This is the most numerically intensive module.

#### Jerk-Minimal Quintic Polynomial

A 5th-order polynomial $d(t) = c_0 + c_1 t + c_2 t^2 + c_3 t^3 + c_4 t^4 + c_5 t^5$ is used for lateral displacement in the Frenet frame.

**Why quintic?** Minimum-jerk (3rd derivative of position) interpolation requires a 5th-order polynomial given 6 boundary conditions: position, velocity, and acceleration at both endpoints.

```cpp
void TrajectoryGenerator::solveQuintic(float d0, float dv0, float da0,
                                        float df, float dvf, float daf,
                                        float T, float coeffs[6]) const {
    coeffs[0] = d0;
    coeffs[1] = dv0;
    coeffs[2] = 0.5f * da0;

    float T2=T*T, T3=T2*T, T4=T3*T, T5=T4*T;
    float a3 = df  - d0  - dv0*T - 0.5f*da0*T2;
    float a4 = dvf - dv0 - da0*T;
    float a5 = daf - da0;

    float inv_T3 = (T3 > 1e-9f) ? 1.0f/T3 : 0.0f;
    coeffs[3] = (10.0f*a3 - 4.0f*a4*T + 0.5f*a5*T2) * inv_T3;
    coeffs[4] = (-15.0f*a3*inv_T3 + 7.0f*a4/T4 - a5/(2.0f*T3)) / T;
    coeffs[5] = (6.0f*a3*inv_T3 - 3.0f*a4/T4 + 0.5f*a5/T5);
}
```

The closed-form solution avoids a 3×3 matrix inversion at runtime. The `T3 > 1e-9f` guard prevents division by zero for degenerate short horizons.

#### Polynomial Evaluation – Horner's Method

```cpp
float TrajectoryGenerator::evalPoly(const float c[6], float t) const {
    return c[0] + t*(c[1] + t*(c[2] + t*(c[3] + t*(c[4] + t*c[5]))));
}
```

Horner's method reduces 5 additions + 5 multiplications instead of computing $c_5 t^5 + c_4 t^4 + ...$ separately (5 additions + 15 multiplications). This is a standard embedded optimision.

#### Collision Check – Axis-Aligned Bounding Box (AABB)

```cpp
bool TrajectoryGenerator::isCollisionFree(const Trajectory& traj) const {
    static constexpr float EGO_HALF_W = 1.0f;
    static constexpr float EGO_HALF_L = 2.5f;

    for (uint8_t pi = 0; pi < traj.count; ++pi) {
        for (uint8_t oi = 0; oi < m_objects.count; ++oi) {
            float ox = obj.x_m + obj.vx_mps * t;  // predict object position
            float oy = obj.y_m + obj.vy_mps * t;
            float hw = obj.width_m/2.0f + EGO_HALF_W + 0.3f;  // safety margin
            float hl = obj.length_m/2.0f + EGO_HALF_L + 0.3f;
            if (fabsf(ex-ox) < hl && fabsf(ey-oy) < hw) return false;
        }
    }
    return true;
}
```

This is an **inflated AABB** check: the ego vehicle's half-dimensions are added to the object's half-dimensions to form a Minkowski sum, reducing the problem to a point-in-box test. The 0.3 m margin adds a safety buffer.

#### Candidate Generation: 5×3 Grid

```cpp
static const float LATERAL_TARGETS[5] = {-1.5f, -0.75f, 0.0f, 0.75f, 1.5f};
static const float TIME_HORIZONS[3]   = {2.0f, 3.0f, 5.0f};

for (float d : LATERAL_TARGETS) {
    for (float T : TIME_HORIZONS) {
        Trajectory cand = generateCandidate(d, T);
        if (isCollisionFree(cand) && cand.total_cost < bestCost) {
            bestCost = cand.total_cost;
            m_best   = cand;
        }
    }
}
```

Range-based `for` over C-arrays is valid in C++11/14 when the type is a known-size array. The `static const` arrays reside in the data segment (not stack). 15 candidates evaluated per planning cycle (~3–5 ms on a real ECU core).

#### Cost Function

$$J = \sum_{i=1}^{N} \left[ 0.5 \cdot \frac{(\Delta y_i)^2}{(\Delta t_i)^2} + 0.2 \cdot (v_i - v_{ref})^2 \right]$$

Lateral jerk proxy + speed error. The minimum-cost collision-free trajectory is selected.

---

## 8. Control – PID Controller

### File: `src/control/pid_controller.cpp`

#### Class Structure

```cpp
class PidController {
    float m_kp, m_ki, m_kd;
    float m_outputMin, m_outputMax, m_integralMax;
    float m_integral, m_prevError;
    bool  m_firstCycle;
};
```

All floats — no templates, no runtime polymorphism. The integral state and previous error are the only stateful fields.

#### Anti-Windup Implementation

```cpp
float PidController::compute(float setpoint, float measurement, float dt_s) {
    float error = setpoint - measurement;

    float derivative = 0.0f;
    if (!m_firstCycle && dt_s > 1e-6f)
        derivative = (error - m_prevError) / dt_s;
    m_firstCycle = false;
    m_prevError  = error;

    m_integral += error * dt_s;
    m_integral = clamp(m_integral, -m_integralMax, m_integralMax);   // anti-windup

    float out = m_kp * error + m_ki * m_integral + m_kd * derivative;
    return clamp(out, m_outputMin, m_outputMax);
}
```

**Anti-windup** prevents the integral from growing unboundedly when the actuator is saturated. Two `clamp` calls: one on the integral accumulator and one on the final output.

The `m_firstCycle` flag prevents a false derivative spike on the first call (because `m_prevError` is uninitialised). This is an embedded pattern — no constructor parameter needed, the flag handles it.

#### `clamp` as private const member

```cpp
float PidController::clamp(float v, float lo, float hi) const {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}
```

A private helper avoids `std::clamp` (C++17) and `std::min`/`std::max` chains. Marked `const` because it does not modify object state.

---

## 9. Control – Vehicle Controller (Stanley)

### File: `src/control/vehicle_controller.cpp`

#### Longitudinal: Speed PID → Throttle/Brake Split

```cpp
float pid_out = m_speedPid.compute(target_speed, m_egoSpeed, dt_s);
if (pid_out >= 0.0f) {
    m_commands.throttle_pct = pid_out * 10.0f;  // scale 0–100 %
    m_commands.brake_pct    = 0.0f;
} else {
    m_commands.throttle_pct = 0.0f;
    m_commands.brake_pct    = (-pid_out) * BRAKE_GAIN * 10.0f;
}
```

PID output is clamped to [-10, +10] by the PidController. Splitting at zero:
- Positive output → throttle command (0–100%).
- Negative output → brake command (0–100%).
This models the real actuator system where throttle and brake are separate channels.

#### Lateral: Stanley Controller

$$\delta = \psi_e + \arctan\left(\frac{k \cdot e_{fa}}{v}\right)$$

```cpp
float psi_e = target.heading_rad - m_egoYaw;
// Normalise heading error to (-π, π)
while (psi_e >  3.14159265f) psi_e -= 2.0f * 3.14159265f;
while (psi_e < -3.14159265f) psi_e += 2.0f * 3.14159265f;

float e_fa = (target.y_m - m_egoY) * cosf(m_egoYaw)
           - (target.x_m - m_egoX) * sinf(m_egoYaw);

float speed = (m_egoSpeed < 0.5f) ? 0.5f : m_egoSpeed;   // avoid /0
float delta = psi_e + atanf(STANLEY_GAIN * e_fa / speed);
```

`e_fa` (cross-track error at front axle) is computed by projecting the vector from ego to lookahead onto the ego's lateral axis. The ternary guard `(m_egoSpeed < 0.5f) ? 0.5f : m_egoSpeed` prevents division by zero at standstill.

#### Steering Gear Ratio

```cpp
float sw_deg = delta * 180.0f / 3.14159265f * 15.0f;  // 15:1 gear ratio
```

Front wheel angle (radians) → steering wheel angle (degrees). 15:1 is a typical passenger car ratio.

#### Lookahead Search

```cpp
const planning::TrajectoryPoint* VehicleController::findLookahead(float lookahead_m) const {
    for (uint8_t i = 0; i < m_trajectory.count; ++i) {
        float dx = m_trajectory.pts[i].x_m - m_egoX;
        float dy = m_trajectory.pts[i].y_m - m_egoY;
        if (sqrtf(dx*dx + dy*dy) >= lookahead_m)
            return &m_trajectory.pts[i];
    }
    return &m_trajectory.pts[m_trajectory.count - 1];
}
```

Returns a **pointer into an existing array** — zero allocation. The dynamic lookahead distance `5.0 + 0.3 × v` scales with speed (larger lookahead at higher speed for stability).

---

## 10. Safety – Safety Monitor (ASIL-D Watchdog)

### File: `src/safety/safety_monitor.cpp`

#### FaultFlags – Bitfield Struct

```cpp
struct FaultFlags {
    bool lidar_failed    : 1;
    bool camera_failed   : 1;
    bool radar_failed    : 1;
    bool imu_failed      : 1;
    bool fusion_timeout  : 1;
    bool planning_timeout: 1;
    bool control_timeout : 1;
    bool steering_fault  : 1;
    bool speed_exceeded  : 1;
};
```

C++ bitfield struct. Each member takes 1 bit. The entire struct fits in 2 bytes. This is MISRA-compatible when the underlying type is `unsigned` or `bool`. Accessing individual faults is syntactically clean (`m_faults.lidar_failed = true`) without bitmask macros.

#### Three Independent Watchdogs

```cpp
void SafetyMonitor::kickFusionWatchdog   (uint32_t ts) { m_fusionKickTs = ts; }
void SafetyMonitor::kickPlanningWatchdog (uint32_t ts) { m_planKickTs   = ts; }
void SafetyMonitor::kickControlWatchdog  (uint32_t ts) { m_ctrlKickTs   = ts; }

SafetyDecision SafetyMonitor::evaluate(uint32_t now_ms) {
    m_faults.fusion_timeout  = (now_ms - m_fusionKickTs  > FUSION_TIMEOUT_MS);   // 50 ms
    m_faults.planning_timeout= (now_ms - m_planKickTs    > PLAN_TIMEOUT_MS);     // 200 ms
    m_faults.control_timeout = (now_ms - m_ctrlKickTs    > CTRL_TIMEOUT_MS);     // 50 ms
    ...
}
```

Each module kicks its watchdog by writing the current system timestamp. If `evaluate()` is called and the difference exceeds the threshold, the fault fires. The unsigned subtraction `now_ms - kickTs` is naturally correct across uint32_t rollover.

#### Decision Priority Cascade

```
EMERGENCY_STOP  ← AEB required | steering fault | speed exceeded | control timeout
MINIMAL_RISK    ← ≥2 sensors failed | planning timeout
DEGRADE_ODD     ← 1 sensor failed | fusion timeout
WARN            ← TTC < 2.5s
NOMINAL         ← everything healthy
```

Implemented as a simple if-else chain (highest priority first). The function is pure in the sense that it only reads member state and returns a value — no side effects, easy to unit test.

---

## 11. Safety – ADAS FSM

### File: `src/safety/adas_fsm.cpp`

#### State Enum

```cpp
enum class AdasSystemState : uint8_t {
    POWER_OFF, SELF_TEST, STANDBY, ACTIVE_L4,
    DEGRADED,  SAFE_STOP, MINIMAL_RISK, PULL_OVER, FAULT
};
```

`enum class` with underlying type `uint8_t`: the compiler allocates 1 byte per value. The underlying type is explicit so the enum can be serialised to a CAN frame byte directly with `static_cast<uint8_t>(state)`.

#### State Machine Transition Method

```cpp
void AdasFSM::transition(AdasSystemState next) {
    m_state = next;
}
```

A dedicated `transition()` method (even though it is trivial) is a single place to add logging, trace, or illegal-transition checks in the future. Called only from inside `AdasFSM` class methods — not exposed publicly.

#### Self-Test Require 10 Cycles

```cpp
case AdasSystemState::SELF_TEST:
    m_selfTestCycles++;
    if (criticalFault) { transition(AdasSystemState::FAULT); }
    else if (m_selfTestCycles >= 10 && selfTestPassed) {
        transition(AdasSystemState::STANDBY);
    }
    break;
```

This models a real ECU self-test requiring multiple consecutive `OK` frames. At 100 ms/cycle → 1 second minimum self-test, a typical value for ISO 26262 startup checks.

#### `stateToStr` – Switch with String Literals

```cpp
const char* stateToStr(AdasSystemState s) {
    switch (s) {
        case AdasSystemState::POWER_OFF: return "POWER_OFF";
        ...
        default: return "UNKNOWN";
    }
}
```

Returns a **pointer to a string literal** (static storage, never freed). No `std::string`, no allocation. This is the canonical embedded pattern for enum-to-string conversion.

---

## 12. Safety – Emergency Handler

### File: `src/safety/emergency_handler.cpp`

#### Pointer Members (HAL pattern)

```cpp
class EmergencyHandler {
    SafetyMonitor*    m_safetyMon;    // raw pointer – non-owning
    VehicleController* m_controller;  // raw pointer – non-owning
};
```

Raw (non-owning) pointers are used deliberately. In an ASIL-D system:
- `shared_ptr` / `unique_ptr` are prohibited (dynamic allocation inside).
- The lifetime of `SafetyMonitor` and `VehicleController` is managed by `main()` (static storage) — longer than `EmergencyHandler`.
- `assert(m_safetyMon != nullptr)` style null-checks guard before use.

#### AEB Execution

```cpp
void EmergencyHandler::handle(SafetyDecision dec,
                               AdasSystemState state, float egoSpeed) {
    if (dec == SafetyDecision::EMERGENCY_STOP) {
        m_controller->triggerEmergencyStop();  // sets brake = 100%
    } else if (dec == SafetyDecision::MINIMAL_RISK) {
        // Gradual deceleration – proportional to speed
        float brake = (egoSpeed > 5.0f) ? 30.0f : 100.0f;
        m_controller->setGradualBrake(brake);
    }
}
```

AEB (`EMERGENCY_STOP`) applies 100% brake immediately. `MINIMAL_RISK` uses a softer deceleration unless speed is already below 5 m/s (18 km/h), at which point full stop is applied.

---

## 13. CAN Bus – Frame Encoding and Transmission

### File: `src/can/adas_can_bus.cpp` and `include/can/adas_can_signals.hpp`

#### Callback Pointer – Hardware Abstraction

```cpp
using CanTxFn = void(*)(const CanFrame&);  // function pointer typedef

class AdasCanBus {
    CanTxFn m_txFn;
public:
    void setTxCallback(CanTxFn fn) { m_txFn = fn; }
};
```

`using` is the C++11 alias for `typedef`. The function pointer type `void(*)(const CanFrame&)` decouples the CAN logic from the physical driver. In production the callback would call `Can_Write()` from the AUTOSAR CAN stack or a Vector XL driver.

#### Signal Encoding – `inline` Functions

```cpp
// In adas_can_signals.hpp
inline uint16_t encodeRange(float range_m) {
    // resolution = 0.1m, offset = 0, max 6553.5m
    uint32_t raw = static_cast<uint32_t>(range_m * 10.0f);
    return static_cast<uint16_t>(raw > 65535U ? 65535U : raw);
}
```

`inline` in a header file ensures the function is inlined at each call site — no function call overhead, no separate symbol in the object file. Saturation (`> 65535U ? 65535U : raw`) implements signal range clamping.

#### Multi-Byte Signal Packing (Big-Endian / Motorola)

```cpp
uint16_t range = encodeRange(dist);
f.data[2] = static_cast<uint8_t>(range >> 8);    // MSB first
f.data[3] = static_cast<uint8_t>(range & 0xFF);  // LSB
```

This is **Motorola (big-endian) byte order** as specified in the DBC file. Bit-shift operations `>>8` and `&0xFF` extract bytes without relying on host endianness. `static_cast<uint8_t>` makes the narrowing conversion explicit (MISRA Rule 5-0-4).

#### Object List Transmission

```cpp
void AdasCanBus::transmitAll(const perception::ObjectList& objects,
                              const perception::LaneEstimate& lane,
                              const control::ActuatorCommands& cmds,
                              ...) {
    for (uint8_t i = 0; i < objects.count; ++i) {
        txObjectList(objects.objects[i]);
    }
    txLaneInfo(lane);
    txVehicleCmd(cmds);
    txSafetyStatus(faults, state, min_ttc, aeb_active, odd_valid);
    txEgoState(ego_x, ego_y, ego_yaw, ego_speed_mps);
}
```

Each `txXxx()` method constructs a `CanFrame` on the stack (8 bytes + metadata), populates it, and calls `sendFrame()` which invokes the callback. The frame goes out of scope after `sendFrame()` — zero allocation per message.

---

## 14. Memory Layout and Embedded Constraints

### No Dynamic Memory

The project has zero calls to `new`, `delete`, `malloc`, or `free`. All objects either:
- Are declared `static` in `main()` → BSS/data segment.
- Are value members of a class → inside the class's own storage.
- Are local to a function (small structs only) → stack.

The large `LidarScan` (≈3 MB) is declared `static` in `main()` to avoid a stack overflow.

### Fixed-Size Arrays

| Array | Size | Location |
|-------|------|----------|
| `LidarScan::points[150000]` | ~3 MB | BSS (static) |
| `KFState m_states[32]` | ~17 KB | SensorFusion object |
| `TrackedObject m_tracks[32]` | ~5 KB | SensorFusion object |
| `Trajectory::pts[50]` | ~400 B | Stack or member |
| `CanFrame::data[8]` | 8 B | Stack (per transmit) |

All maximum sizes are defined as `static constexpr uint32_t` or `uint8_t` constants in the relevant header, used as array bounds. Changing the constant automatically adjusts the array — no manual updates.

### MISRA C++ Alignment

| Practice | Implementation |
|----------|---------------|
| No dynamic allocation | No STL containers, no `new/delete` |
| Explicit integer widths | `uint8_t`, `uint16_t`, `uint32_t`, `int16_t` everywhere |
| No floating-point implicit conversion | `static_cast<uint8_t>(...)` on all narrowing casts |
| No global mutable state | All state inside class members |
| Single exit from functions | Not always, but early `return` on guard conditions |
| `const` correctness | All getters and non-mutating helpers are `const` |

---

## 15. Namespaces and Module Boundaries

```
adas::                             ← sensors (LidarSensor, RadarSensor, CameraSensor, ImuSensor)
adas::perception::                 ← SensorFusion, LaneDetector, TrackedObject, ObjectList
adas::planning::                   ← PathPlanner, TrajectoryGenerator, BehaviorDecision
adas::control::                    ← PidController, VehicleController, ActuatorCommands
adas::safety::                     ← SafetyMonitor, AdasFSM, EmergencyHandler
adas::can_bus::                    ← AdasCanBus, CanFrame
adas::can_signals::                ← encode/decode inline functions
```

Cross-module access uses **forward references via includes**. For example, `VehicleController` exposes its trajectory input via `setTrajectory(const planning::Trajectory&)` — the `planning` namespace is accessed through the include chain, not through flattening the namespace. This enforces a strict **dependency direction**:

```
sensors → perception → planning → control
                  ↓          ↓         ↓
                       safety_monitor
                              ↓
                       can_bus (reads all, writes to hardware)
```

No reverse dependency exists (e.g., `sensors` never includes `planning`).

---

## 16. Unit Test Architecture

### Files: `tests/test_sensors.cpp`, `tests/test_perception.cpp`

#### Minimal Test Framework (No GTest/Catch2)

```cpp
#define ASSERT_TRUE(cond) \
    do { \
        if (!(cond)) { \
            printf("  [FAIL] %s  (line %d)\n", #cond, __LINE__); \
            g_fail_count++; \
        } else { \
            printf("  [PASS] %s\n", #cond); \
        } \
    } while(0)
```

A single header-style macro. `#cond` uses the **stringification operator** to print the exact expression. `do { } while(0)` is the idiom for multi-statement macros that behave correctly in all `if/else` contexts. `__LINE__` is a standard C preprocessor predefined macro.

This avoids dependencies on GTest (which requires exceptions and RTTI — both prohibited in embedded C++) while still giving clear pass/fail output.

#### Float Comparison Macro

```cpp
#define ASSERT_NEAR(a, b, eps) ASSERT_TRUE(fabsf((float)(a)-(float)(b)) < (eps))
```

IEEE 754 float equality (`a == b`) is unreliable due to rounding. The `eps`-based comparison handles the ~1 ULP error typical in float arithmetic.

#### Test Functions – Static Linkage

```cpp
static void test_lidar_initial_state() { ... }
static void test_lidar_inject_scan()   { ... }
```

All test functions are `static` (internal linkage). This means they cannot be called from another translation unit, preventing accidental cross-test coupling. The `main()` function calls them explicitly in order.

#### Test Output with `printf`

`printf` is used (not `std::cout`) because:
- `<iostream>` with `std::cout` requires static initialisers and can use dynamic allocation on some platforms.
- `printf` is a single C function call, predictable and small.
- Format string `%s`, `%d`, `%u`, `%.2f` gives compact one-line output per test.

---

## Summary Table

| Feature | C++ Pattern | File(s) |
|---------|-------------|---------|
| RANSAC ground removal | LCG RNG, cross product, unsigned index arithmetic | `lidar_sensor.cpp` |
| Sensor timeout detection | Unsigned time subtraction, uint32_t overflow safe | All sensor .cpp |
| IMU plausibility | Early return, `fabsf`, DEGRADED vs FAILED distinction | `imu_sensor.cpp` |
| 8-DOF EKF predict | 2D C-array matrix, Horner multiply, value-init `= {}` | `sensor_fusion.cpp` |
| EKF update | File-static `kfUpdate2D`, diagonal approximation | `sensor_fusion.cpp` |
| Data association | Mahalanobis distance, nearest-neighbour gate | `sensor_fusion.cpp` |
| Track lifecycle | `switch` on `enum class`, compaction in-place | `sensor_fusion.cpp` |
| TTC | Signed velocity, INVALID_FLOAT sentinel | `sensor_fusion.cpp` |
| Quintic polynomial | Closed-form 3×3 solution, Horner eval | `trajectory_generator.cpp` |
| Collision check | Inflated AABB, Minkowski sum, predicted position | `trajectory_generator.cpp` |
| PID anti-windup | Double `clamp`, `m_firstCycle` flag | `pid_controller.cpp` |
| Stanley controller | `atanf`, heading normalisation `while` loop, ternary zero guard | `vehicle_controller.cpp` |
| Safety decision | FaultFlags bitfield, priority cascade | `safety_monitor.cpp` |
| FSM | `enum class : uint8_t`, `stateToStr` string literal | `adas_fsm.cpp` |
| CAN encoding | `inline` encode functions, big-endian byte shift | `adas_can_bus.cpp`, `adas_can_signals.hpp` |
| HAL callback | Function pointer `CanTxFn`, `using` alias | `adas_can_bus.hpp` |
| Memory safety | `static` for large objects, no `new/delete` | `main.cpp`, all modules |
| Test framework | `#define ASSERT_TRUE`, `__LINE__`, `#cond` stringify | `test_sensors.cpp`, `test_perception.cpp` |
