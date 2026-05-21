# 08 — Sensor Fusion for ADAS

## Overview
Camera + Radar + LiDAR fusion using Kalman filtering, Extended Kalman Filter (EKF), and multi-object tracking. Covers the complete fusion pipeline from raw detections to confirmed tracked objects.

**Sensor comparison for fusion:**

| Sensor | Range | Accuracy | Weather | Velocity | 3D |
|--------|-------|----------|---------|---------|-----|
| Camera | 200m | High (visual) | Poor (rain/fog) | No (frame diff) | No (mono) |
| Radar | 250m | Medium (pos) | Excellent | Yes (Doppler) | Limited |
| LiDAR | 150m | Very high | Good | No | Yes |
| **Fused** | **250m** | **Very high** | **Good** | **Yes** | **Yes** |

---

## 1. Kalman Filter Theory

**State-space model:**
$$\mathbf{x}_{k+1} = F\mathbf{x}_k + B\mathbf{u}_k + \mathbf{w}_k \quad \mathbf{w}_k \sim \mathcal{N}(0, Q)$$
$$\mathbf{z}_k = H\mathbf{x}_k + \mathbf{v}_k \quad \mathbf{v}_k \sim \mathcal{N}(0, R)$$

**Two-step recursion:**

**Predict:**
$$\hat{\mathbf{x}}_{k|k-1} = F\hat{\mathbf{x}}_{k-1|k-1}$$
$$P_{k|k-1} = FP_{k-1|k-1}F^T + Q$$

**Update:**
$$K_k = P_{k|k-1}H^T(HP_{k|k-1}H^T + R)^{-1}$$
$$\hat{\mathbf{x}}_{k|k} = \hat{\mathbf{x}}_{k|k-1} + K_k(\mathbf{z}_k - H\hat{\mathbf{x}}_{k|k-1})$$
$$P_{k|k} = (I - K_kH)P_{k|k-1}$$

**For radar ACC tracking:**
- State: $[r, \dot{r}]^T$ — range and range_rate
- $F = \begin{bmatrix} 1 & \Delta t \\ 0 & 1 \end{bmatrix}$, $H = [1, 0]$
- $Q = \sigma_a^2 \begin{bmatrix} \Delta t^4/4 & \Delta t^3/2 \\ \Delta t^3/2 & \Delta t^2 \end{bmatrix}$

---

## 2. Extended Kalman Filter (EKF) — Camera + Radar

Radar measures in polar coordinates (range, bearing, range_rate). These are nonlinear functions of the state $[x, y, v_x, v_y]^T$:

$$h(\mathbf{x}) = \begin{bmatrix} \sqrt{x^2+y^2} \\ \arctan(y/x) \\ (xv_x + yv_y)/\sqrt{x^2+y^2} \end{bmatrix}$$

EKF linearises $h$ via Jacobian:

$$H_j = \frac{\partial h}{\partial \mathbf{x}}\bigg|_{\hat{\mathbf{x}}} = \begin{bmatrix} x/\rho & y/\rho & 0 & 0 \\ -y/\rho^2 & x/\rho^2 & 0 & 0 \\ \cdots & \cdots & x/\rho & y/\rho \end{bmatrix}$$

**Implementation note:** Angle wrapping in innovation vector:
```python
y[1] = (y[1] + np.pi) % (2*np.pi) - np.pi  # Keep in [-π, π]
```

---

## 3. Multi-Object Tracking Architecture

```
Frame N detections (CNN output)
           │
           ▼
    ┌─────────────────────────┐
    │  Data Association        │
    │  IoU Matrix → Hungarian  │
    │  Threshold: 0.3          │
    └─────────────┬───────────┘
                  │
          ┌───────┴───────┐
          │               │
    Matched          Unmatched
    detections       detections
          │               │
    Update EKF      Create new
    (hits++)        track (hits=1)
                         │
    ┌────────────────────┐
    │ Tracks with        │
    │ misses > max_miss  │ → Delete
    └────────────────────┘
          │
    ┌─────▼──────────────┐
    │ Confirmed tracks   │
    │ hits >= min_hits   │ → Output to ADAS
    └────────────────────┘
```

### Why min_hits = 3 before output?
Prevents false activations: a pedestrian confirmed for 3 frames (~150ms) at 20Hz is genuine. Single-frame detections (CNN FP) are suppressed before they reach LKA/AEB logic.

---

## 4. Temporal Alignment — The #1 Production Bug

```
Camera:  t=0ms    t=50ms    t=100ms    t=150ms
Radar:   t=0ms        t=60ms        t=120ms
LiDAR:         t=25ms         t=125ms
```

**Problem:** Associate a camera detection at t=100ms with a radar detection at t=120ms — 20ms delay means the object has moved ~0.55m at 100kph.

**Solution: Timestamp-aligned fusion**
```python
def propagate_to_time(state, covariance, dt_sec, F, Q):
    """Extrapolate a detection's state to a target timestamp."""
    F_dt = compute_transition_matrix(dt_sec)
    x_aligned = F_dt @ state
    P_aligned  = F_dt @ covariance @ F_dt.T + Q * dt_sec
    return x_aligned, P_aligned

# Align all detections to common fusion timestamp before association
fusion_time = max(cam_ts, radar_ts, lidar_ts)  # Latest timestamp
cam_det_aligned   = propagate_to_time(cam_det,   (fusion_time - cam_ts)/1000)
radar_det_aligned = propagate_to_time(radar_det, (fusion_time - radar_ts)/1000)
```

---

## 5. Gating — Reject Spurious Associations

```python
def mahalanobis_gate(z: np.ndarray, x_pred: np.ndarray,
                     S: np.ndarray, threshold_chi2: float = 9.49) -> bool:
    """Chi-squared gating to reject implausible associations.
    threshold_chi2 = 9.49 corresponds to 95% confidence for 2-DOF (x,y).
    
    An EKF track should not jump more than ~3σ in one step."""
    y = z[:2] - x_pred[:2]
    d2 = float(y.T @ np.linalg.inv(S[:2,:2]) @ y)
    return d2 <= threshold_chi2
```

---

## 6. Safety Considerations

### SOTIF-relevant fusion risks:
1. **Ghost objects** — Radar multi-path reflections create spurious targets. Mitigation: require camera confirmation within 2 frames for AEB trigger.

2. **Merged objects** — Two close targets merged into one track. Mitigation: track width estimate; if width > 2× expected, split track.

3. **Missed detections** — All sensors simultaneously miss an obstacle (e.g., bicycle at dawn). Mitigation: SOTIF operational design domain restriction + speed limits.

4. **Temporal desync** — Sensor clocks drift. Mitigation: IEEE 1588 PTP (Precision Time Protocol) hardware timestamping on all ECUs.

5. **EKF divergence** — Process/measurement noise mismatch causes filter to diverge. Mitigation: covariance bound checks; if any P diagonal > 100 → reinitialise track.

---

## 7. Interview Q&A

### L1
**Q: What is the Kalman gain K, and what happens as R → 0?**  
A: $K = PH^T(HPH^T + R)^{-1}$ determines how much weight the filter gives to the new measurement vs the prediction. As R → 0 (perfect measurement), K → $H^{-1}$ and the state is fully replaced by the measurement. As Q → 0 (perfect model), K → 0 and the filter ignores new measurements. In ADAS, radar range measurements are low-noise (R small) so K is close to 1 — the filter quickly tracks new values.

**Q: What is the innovation (or residual) in a Kalman filter?**  
A: Innovation $y = z - H\hat{x}$ is the difference between actual measurement and predicted measurement. If the filter is consistent, innovations should be zero-mean Gaussian with covariance S. Monitoring innovation statistics is a standard filter health check — large innovations indicate either a new object entering the scene or a filter divergence.

### L2
**Q: When is EKF required instead of standard Kalman filter?**  
A: EKF when the measurement model is nonlinear — specifically when radar measures in polar coordinates (range, bearing, range_rate) but the state is Cartesian (x, y, vx, vy). The standard KF assumes $z = Hx + v$ (linear) — radar violates this. EKF linearises $h(x)$ via first-order Taylor expansion (Jacobian). Unscented KF (UKF) is more accurate than EKF for highly nonlinear cases (tight turns, large dt).

**Q: Explain the data association problem and how IoU-based SORT solves it.**  
A: At each timestep, there are M predicted track positions and N new detections. We must decide which detection updates which track (M×N assignment problem). IoU-based SORT: build M×N IoU matrix (intersection-over-union of predicted bounding boxes with detected boxes), then use Hungarian algorithm for optimal minimum-cost assignment. Tracks with IoU < 0.3 with all detections are marked "missed"; detections with IoU < 0.3 with all tracks create new tracks.

### L3
**Q: Describe how you would fuse camera and radar in a production AEB system, meeting ISO 26262 ASIL-C requirements.**  
A: (1) **Time alignment**: hardware PTP timestamps on camera (CSI) and radar (CAN); extrapolate to common fusion time using KF prediction. (2) **Coordinate alignment**: camera detects in pixel space → unproject to 3D using known extrinsic calibration T_cam_radar; update on ECU power-on and every service interval. (3) **EKF object tracking**: state [x,y,vx,vy], camera updates [x,y], radar updates [range,bearing,range_rate] via Jacobian. (4) **Confirmation logic**: AEB trigger requires object confirmed by BOTH sensors in last 3 frames (reduces false activations). (5) **Degraded mode**: if one sensor fails (DTC set), reduce to single-sensor mode with increased safety margin (larger TTC threshold). (6) **Verification**: HARA (Hazard Analysis and Risk Assessment) shows AEB false activation ASIL-B + missed detection ASIL-C; dual-sensor fusion achieves systematic failure coverage. Document in FMEA.

---

## Files
- [sensor_fusion.py](sensor_fusion.py) — KF, EKF, multi-object tracker, covariance intersection
