# 24 — Localisation for ADAS / AD

## Overview
Vehicle localisation: GPS/GNSS, IMU dead reckoning, HD map matching, and multi-source fusion. Covers the localisation stack from 10m GPS to sub-centimetre HD map pose.

---

## 1. Localisation Accuracy Requirements

| ADAS Level | Function | Required Accuracy |
|-----------|---------|-----------------|
| L1/L2 | Lane centering, TSR map validation | ±0.5-2.0m |
| L3 | Highway pilot (lane-level) | ±0.1-0.3m |
| L4 | Urban AD (lane-precise) | ±0.03-0.05m |
| Parking | Sub-metre parking manoeuvre | ±0.05-0.10m |

---

## 2. GNSS (GPS) Limitations

**Standard GPS:** ±3-10m, degraded in tunnels, urban canyons
**RTK-GPS:** ±0.02m, requires fixed base station (cost-prohibitive for fleet)
**PPP (Precise Point Positioning):** ±0.03-0.1m, works anywhere, ~30min convergence

**GNSS denial environments:**
- Tunnels (total loss)
- Underground parking (total loss)
- Dense urban canyons (multipath, ±20m error)

---

## 3. IMU Dead Reckoning

```python
import numpy as np
from dataclasses import dataclass

@dataclass
class IMUData:
    timestamp_s: float
    accel: np.ndarray   # (3,) m/s²  [ax, ay, az]
    gyro:  np.ndarray   # (3,) rad/s [wx, wy, wz]

class IMUDeadReckoning:
    """6-DOF dead reckoning from IMU integration.
    Accumulates drift over time — must be corrected by GNSS/map fusion.
    
    Typical drift: ~1% of distance without correction."""
    
    def __init__(self, g: float = 9.81):
        self.pos   = np.zeros(3)      # [x, y, z] metres
        self.vel   = np.zeros(3)      # [vx, vy, vz] m/s
        self.quat  = np.array([1.0, 0.0, 0.0, 0.0])   # Quaternion [w, x, y, z]
        self.g_vec = np.array([0, 0, -g])
        self._last_ts = None
    
    def update(self, imu: IMUData):
        if self._last_ts is None:
            self._last_ts = imu.timestamp_s
            return
        
        dt = imu.timestamp_s - self._last_ts
        self._last_ts = imu.timestamp_s
        
        # Integrate gyroscope → orientation
        omega_mag = np.linalg.norm(imu.gyro)
        if omega_mag > 1e-6:
            axis = imu.gyro / omega_mag
            angle = omega_mag * dt
            dq = np.array([np.cos(angle/2),
                            axis[0]*np.sin(angle/2),
                            axis[1]*np.sin(angle/2),
                            axis[2]*np.sin(angle/2)])
            self.quat = self._quat_mult(self.quat, dq)
            self.quat /= np.linalg.norm(self.quat)
        
        # Rotate accelerometer to world frame
        R = self._quat_to_rot(self.quat)
        accel_world = R @ imu.accel + self.g_vec   # Remove gravity
        
        # Integrate acceleration → velocity → position
        self.vel += accel_world * dt
        self.pos += self.vel * dt + 0.5 * accel_world * dt**2
    
    def _quat_mult(self, q1, q2) -> np.ndarray:
        w1,x1,y1,z1 = q1; w2,x2,y2,z2 = q2
        return np.array([
            w1*w2 - x1*x2 - y1*y2 - z1*z2,
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2
        ])
    
    def _quat_to_rot(self, q) -> np.ndarray:
        w,x,y,z = q
        return np.array([
            [1-2*(y**2+z**2),   2*(x*y-z*w),   2*(x*z+y*w)],
            [2*(x*y+z*w),   1-2*(x**2+z**2),   2*(y*z-x*w)],
            [2*(x*z-y*w),     2*(y*z+x*w),   1-2*(x**2+y**2)]
        ])
```

---

## 4. HD Map Localisation (LiDAR Point Cloud Matching)

```python
def localise_against_hdmap(scan: np.ndarray,
                             hdmap_cloud: np.ndarray,
                             initial_guess: np.ndarray) -> np.ndarray:
    """Localise vehicle against HD map using ICP.
    
    scan: (N, 3) current LiDAR scan
    hdmap_cloud: (M, 3) pre-built HD map point cloud (submap within 50m)
    initial_guess: 4×4 initial transform (from GPS/IMU)
    
    Returns: refined 4×4 pose (map → vehicle)"""
    try:
        import open3d as o3d
        source = o3d.geometry.PointCloud()
        source.points = o3d.utility.Vector3dVector(scan)
        target = o3d.geometry.PointCloud()
        target.points = o3d.utility.Vector3dVector(hdmap_cloud)
        
        reg = o3d.pipelines.registration.registration_icp(
            source, target,
            max_correspondence_distance=0.5,
            init=initial_guess,
            estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPlane()
        )
        return reg.transformation
    except ImportError:
        # Simplified ICP (for environments without Open3D)
        return initial_guess
```

---

## 5. Sensor Fusion for Localisation (EKF)

```
State: [x, y, z, vx, vy, vz, roll, pitch, yaw]

Predict: IMU integration (200Hz)
Update:
  - GPS available: update position [x,y,z] (1Hz)
  - LiDAR map match: update full pose [x,y,z,roll,pitch,yaw] (10Hz)
  - Wheel odometry: update velocity [vx,vy] (100Hz)
```

**Key insight:** EKF localisation fuses fast-but-drifting IMU with slow-but-absolute GPS/map to give smooth, accurate, continuous pose estimation.

---

## 6. Lane-Level Localisation from Camera

```python
def compute_cross_track_error(lane_left_coeffs: list,
                               lane_right_coeffs: list,
                               frame_width_px: int = 1280,
                               frame_height_px: int = 720,
                               m_per_pixel_lateral: float = 0.033) -> float:
    """Estimate lateral position within lane from camera lane detection.
    Used for lane-level localisation update in EKF (no HD map needed).
    
    Returns: lateral offset from lane centre in metres"""
    eval_row = int(frame_height_px * 0.75)
    
    left_x  = sum(c * eval_row**i for i, c in enumerate(reversed(lane_left_coeffs)))
    right_x = sum(c * eval_row**i for i, c in enumerate(reversed(lane_right_coeffs)))
    
    lane_centre_px = (left_x + right_x) / 2
    vehicle_px     = frame_width_px / 2
    
    return (vehicle_px - lane_centre_px) * m_per_pixel_lateral
```

---

## 7. Interview Q&A

### L1
**Q: Why can't GPS alone be used for L3 autonomous driving?**  
A: Standard GPS accuracy is ±3-10m — a lane is ~3.5m wide, so GPS alone cannot determine which lane the vehicle is in. Additionally, GPS is unavailable in tunnels and unreliable in urban canyons (multipath). L3 highway pilot requires ±0.1m lateral accuracy for reliable lane-level control. Solution: GPS + HD map matching + camera lane detection fused in an EKF provides lane-level accuracy.

### L2
**Q: How does a vehicle localise itself in a tunnel with no GPS?**  
A: Multi-source dead reckoning: (1) IMU integration: gyroscope + accelerometer → attitude and velocity (drifts at ~1% distance); (2) Wheel odometry: wheel speed sensors → longitudinal distance + yaw from differential speed (better than IMU for forward motion); (3) Camera lane marking tracking + odometry: lane width gives lateral position; (4) Pre-mapped tunnel features (overhead lights, ventilation shafts): camera/LiDAR matching to HD map submap. Accuracy: first 100m = GPS pre-tunnel; after 500m tunnel = ±1-2m (sufficient for L3 highway — tunnel is straight, single lane).

### L3
**Q: Design a localisation system for an L4 urban vehicle achieving ±5cm accuracy.**  
A: (1) LiDAR HD map: offline mapping vehicle builds centimetre-precision 3D point cloud map of city. Updated monthly via fleet vehicles. (2) Runtime: 32-beam LiDAR → NDT (Normal Distributions Transform) matching against cached 50m × 50m map submap; update at 10Hz, latency ~5ms. (3) IMU + wheel odometry: integrate at 200Hz between LiDAR updates; provides smooth trajectory. (4) GPS + RTK: when available (open roads), provides absolute reference; corrects IMU drift after tunnels. (5) Camera lane matching: provides lateral absolute reference when LiDAR matching confidence drops (rain, falling leaves). (6) Fusion: EKF-16 state (position 3D + velocity 3D + attitude 3 + accelerometer bias 3 + gyro bias 3); covariance monitoring — if position uncertainty > 0.1m → trigger localisation alert; at > 0.3m → speed restriction. (7) Validation: KITTI, Waymo Open Dataset; lateral RMSE ≤ 3cm on test routes.
