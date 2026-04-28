# Perception Algorithms – Object Detection, Tracking & Scene Understanding

## 1. Multi-Object Tracking (MOT) with Kalman Filter

### State Vector

Each tracked object maintains an 8-dimensional state:

```
x = [px, py, vx, vy, ax, ay, yaw, yaw_rate]
     m    m   m/s  m/s  m/s²  m/s²  rad   rad/s
```

### Constant Acceleration Motion Model

```
Δt = 0.1s (10 Hz prediction step)

Transition matrix F:
  | 1  0  Δt  0  Δt²/2    0    0     0  |
  | 0  1   0  Δt    0    Δt²/2  0     0  |
  | 0  0   1  0   Δt    0    0     0  |
  | 0  0   0  1    0    Δt    0     0  |
  | 0  0   0  0    1    0    0     0  |
  | 0  0   0  0    0    1    0     0  |
  | 0  0   0  0    0    0    1    Δt  |
  | 0  0   0  0    0    0    0     1  |

Process noise Q ~ acceleration uncertainty σ_a
  Q = G · G^T · σ_a²
  G = [Δt²/2, Δt²/2, Δt, Δt, 1, 1, Δt²/2, Δt]^T
```

### Data Association (Hungarian Algorithm)

```
Problem: M measurements, N existing tracks → find optimal assignment

Cost matrix C[i][j] = Mahalanobis distance(track_i, measurement_j)
  dist = sqrt( (z-Hx)^T · S^-1 · (z-Hx) )
  where S = H·P·H^T + R (innovation covariance)

Gate: reject assignments with dist > chi2_threshold(0.99, dof=4) ≈ 9.49

Hungarian algorithm: O(N³), optimal assignment minimising total cost

Outcome:
  Matched pairs → update Kalman filter
  Unmatched measurements → new track candidates
  Unmatched tracks → increment miss counter → delete if miss > threshold
```

### Track Life Cycle

```
NEW_CANDIDATE → (2 consecutive matches) → PROBABLE
PROBABLE      → (3 consecutive matches) → CONFIRMED
CONFIRMED     → (miss < 5 frames)       → CONFIRMED
CONFIRMED     → (miss >= 5 frames)      → LOST → DELETED

Track output: only CONFIRMED tracks sent to planning layer
```

---

## 2. Sensor Fusion – Track-to-Track vs Central

### Central Fusion (preferred for L4)

```
Raw measurements from all sensors → single EKF per object

Advantages:
  - No information loss from pre-processing
  - Full uncertainty propagation
  - Better handling of partial occlusion

Architecture:
  LiDAR point cloud  ──┐
  Camera detections  ──┼──► Measurement  ──► EKF per ──► Fused object list
  Radar object list  ──┘      manager         object
```

### Occupancy Grid

```
Alternative representation for static environment:
  Grid: 200×200 cells, each 0.2×0.2m → 40m×40m around ego
  Each cell: probability of occupancy [0.0 – 1.0]

Log-odds update:
  l(cell) = l(cell) + log(p(occ|z)/p(free|z))    (if measurement in cell)
  l(cell) = l(cell) + log(p_free)                  (if ray passes through)

Thresholds:
  p > 0.7  → OCCUPIED
  p < 0.3  → FREE
  else     → UNKNOWN

Used for: drivable area computation, path collision checking
```

---

## 3. Collision Risk Assessment

### Time-to-Collision (TTC)

```
For each tracked object with relative velocity approaching ego:

  TTC = -range / range_rate   (Radar), or
  TTC = range / |relative_velocity|  (LiDAR/cam derived)

  range_rate < 0 → object approaching

Actions:
  TTC < 1.5s AND object in ego path → Emergency Brake (AEB)
  TTC < 2.5s                        → FCW (Forward Collision Warning)
  TTC < 3.5s                        → Pre-charge brakes
  TTC ≥ 3.5s                        → Normal ACC operation
```

### Object Path Intersection (Polygon Collision Check)

```
Method: Swept volume overlap test
1. Predict object trajectory for T=3s using constant velocity/turn model
2. Predict ego trajectory for T=3s using planned path
3. For each time step t ∈ {0, 0.1, 0.2, ..., 3.0}:
   - Compute ego bounding box at t (expanded by safety margin)
   - Compute object bounding box at t
   - Check polygon intersection (Separating Axis Theorem)
4. If any intersection found → collision predicted
```

---

## 4. Lane Detection Details

### Polynomial Lane Model

```cpp
struct LanePolynomial {
    float c0;   // lateral offset at reference point (m)
    float c1;   // heading angle (rad)
    float c2;   // curvature (1/m)
    float c3;   // curvature rate (1/m²)
    float startX, endX;  // longitudinal range (m)
    float quality;        // 0.0 – 1.0

    // Evaluate lane position at longitudinal distance x:
    float y(float x) const {
        return c0 + c1*x + c2*x*x + c3*x*x*x;
    }
};
```

### Lane Change Detection (FSM)

```
State machine per lane:
  IN_LANE → (lateral offset > 0.3m AND turn signal) → LC_INTENDED
  LC_INTENDED → (offset > 0.8m) → LC_IN_PROGRESS
  LC_IN_PROGRESS → (offset < 0.1m, new lane) → IN_LANE (new lane)

Without turn signal:
  IN_LANE → (offset > 0.5m) → LDW_WARNING
  (force feedback on steering wheel / acoustic alert)
```

---

## 5. Semantic Segmentation

```
Network: DeepLabV3+ with MobileNetV3 backbone (automotive optimised)
Input:   1024×512 pixels
Output:  Per-pixel class probability map

Classes:
  0: background      5: traffic_sign
  1: road            6: pedestrian
  2: sidewalk        7: car
  3: building        8: truck
  4: vegetation      9: bicycle  ...etc

Drivable area:
  All pixels classified as "road" within ego corridor → navigable space
```

---

## 6. Free Space Detection

```
LiDAR-based approach:
1. Ground removal (RANSAC)
2. Remaining elevated points → obstacles
3. Range image from LiDAR: 2D angular representation
4. For each azimuth column: find first obstacle hit → range
5. Free space polygon: connect range endpoints in ground plane
6. Dilate by vehicle width/2 + margin (0.3m)

Output: FreeSpacePolygon {N points bounding navigable area}
```

---

## 7. Pedestrian Behaviour Prediction

```
Common models:
  1. Constant velocity (CV): simple, for < 0.5s horizon
  2. Social Force Model (SFM): accounts for group/crowd behaviour
  3. LSTM-based (data driven): predicts probability distribution

Simplified CV prediction:
  x_pred(t) = x_0 + vx·t
  y_pred(t) = y_0 + vy·t
  (with uncertainty growing as σ = A·t, A≈0.5m/s for pedestrians)

Crossing probability estimation:
  If pedestrian velocity vector intersects ego path AND
  ego ETA at crossing point within pedestrian ETA ± 1s:
  → crossing_risk = HIGH
```
