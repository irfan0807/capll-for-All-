# 23 — SLAM (Simultaneous Localisation and Mapping)

## Overview
SLAM builds a map of the environment while simultaneously tracking vehicle position within it. Used in parking (HD map building), construction zones (no prior map), and L4 urban driving.

---

## 1. SLAM vs Localisation

| Problem | Given | Estimate |
|---------|-------|---------|
| Localisation | Known map | Vehicle pose |
| Mapping | Known pose | Map |
| SLAM | Neither | Both simultaneously |
| ADAS production | HD map pre-built offline | Only localisation at runtime |

**When SLAM is needed:**
- Underground parking (no GPS, no prior map)
- New road construction (HD map stale)
- L4 first-time deployment in new area

---

## 2. EKF-SLAM (Feature-Based)

```python
import numpy as np
from typing import List, Tuple

class EKFSLAM:
    """Extended Kalman Filter SLAM — landmark-based.
    State: [x, y, θ, lm1_x, lm1_y, lm2_x, lm2_y, ...]
    
    Educational implementation — production uses particle filter or graph-SLAM."""
    
    def __init__(self):
        # Robot pose only initially
        self.state = np.zeros(3)         # [x, y, theta]
        self.P     = np.eye(3) * 0.1
        self.landmarks: List[int] = []   # Known landmark IDs
        
        # Noise
        self.Q_motion   = np.diag([0.01, 0.01, 0.001])  # Process noise
        self.R_landmark = np.diag([0.1, 0.05])           # Range, bearing noise
    
    def predict(self, v: float, omega: float, dt: float):
        """Motion model: unicycle."""
        x, y, th = self.state[:3]
        n = len(self.state)
        
        self.state[0] += v * np.cos(th) * dt
        self.state[1] += v * np.sin(th) * dt
        self.state[2] += omega * dt
        self.state[2]  = (self.state[2] + np.pi) % (2*np.pi) - np.pi
        
        # Jacobian of motion w.r.t. pose
        Fx = np.eye(n)
        Fx[0,2] = -v * np.sin(th) * dt
        Fx[1,2] =  v * np.cos(th) * dt
        
        # Process noise expansion
        Q = np.zeros((n,n))
        Q[:3,:3] = self.Q_motion
        
        self.P = Fx @ self.P @ Fx.T + Q
    
    def add_landmark(self, range_m: float, bearing_rad: float) -> int:
        """Add new landmark to state."""
        x, y, th = self.state[:3]
        lm_x = x + range_m * np.cos(th + bearing_rad)
        lm_y = y + range_m * np.sin(th + bearing_rad)
        
        lm_id = len(self.landmarks)
        self.state = np.append(self.state, [lm_x, lm_y])
        
        n = len(self.state)
        P_new = np.zeros((n,n))
        P_new[:n-2,:n-2] = self.P
        P_new[n-2,n-2] = P_new[n-1,n-1] = 10.0   # High initial uncertainty
        self.P = P_new
        self.landmarks.append(lm_id)
        return lm_id
    
    @property
    def pose(self) -> Tuple[float,float,float]:
        return self.state[0], self.state[1], self.state[2]
```

---

## 3. ORB-SLAM3 (Visual SLAM)

Production visual SLAM for parking:
- **ORB features**: Binary descriptors, real-time extraction
- **Bag-of-Words**: Fast loop closure detection
- **Factor graph**: Pose-graph with loop closure constraints
- **IMU integration**: 6-DOF tracking even when camera is occluded

```
Camera frame
     │
     ▼
ORB feature extraction  (1000 features/frame)
     │
     ▼
Feature matching (DBoW3 vocabulary)
     │
     ├─ Tracking: estimate pose from matched features (PnP)
     │
     ├─ Mapping: triangulate new map points
     │
     └─ Loop closure: detect revisited areas → global optimisation
            (Pose graph, g2o solver)
```

---

## 4. LiDAR SLAM (LeGO-LOAM / LOAM)

```
LiDAR scan
     │
     ▼
Plane/edge feature extraction (ground, building corners)
     │
     ▼
Scan-to-scan odometry (ICP on features — ~10Hz)
     │
     ▼
Scan-to-map refinement (ICP to global point cloud map)
     │
     ▼
Map update (add new areas)
```

**ICP (Iterative Closest Point):**
$$T^* = \arg\min_T \sum_i \|p_i - T q_i\|^2$$

Find rotation + translation minimising distance between corresponding points from consecutive scans.

---

## 5. Parking-Specific SLAM

**Use case:** Underground parking garage, no GPS, marks needed for robotic valet.

**SLAM map stores:**
- Pillar positions (strong LiDAR/visual features)
- Ramp geometry
- Level boundaries
- Charging station locations

**Loop closure in parking:** Car driving in circles → SLAM must recognise "I've been here before" → add constraint → correct accumulated drift.

---

## 6. Interview Q&A

### L1
**Q: What is loop closure in SLAM and why is it important?**  
A: Loop closure is the detection and correction of accumulated pose error when the robot revisits a previously seen location. Over a long trajectory, small odometry errors accumulate ("drift"). When the vehicle returns to a known location (closing a loop), SLAM recognises the familiar features, adds a constraint connecting the current pose to the historical pose, and runs a global optimisation to redistribute the drift error. Without loop closure: after a 500m circuit, accumulated drift may place the vehicle 5m from true position. With loop closure: drift is corrected to <0.1m after loop detection.

### L2
**Q: Compare feature-based SLAM (ORB-SLAM) and direct SLAM (DSO) for automotive applications.**  
A: Feature-based: extract and match discrete features (ORB corners). Advantages: robust to fast motion, illumination changes, easy loop closure via BoW. Disadvantages: sparse map (not suitable for dense occupancy). Direct: minimises photometric error on raw image intensities (all pixels). Advantages: dense reconstruction, better on texture-poor environments. Disadvantages: needs good initial pose, fails with motion blur at high speed. For ADAS: ORB-SLAM3 preferred for parking and feature-rich urban environments; direct SLAM in research (BADSLAM) for dense map building in mapping vehicles.

### L3
**Q: Design an automated parking valet system using SLAM for an underground garage.**  
A: (1) Map building: mapping vehicle equipped with 32-channel LiDAR runs full coverage at 5kph; LeGO-LOAM builds dense 3D map with pillar centroids as landmarks; map compressed to 50MB, stored in cloud + edge server. (2) Runtime localisation: customer vehicle with 4 fisheye cameras + wheel odometry runs visual SLAM (ORB-SLAM3) against stored map; localisation accuracy ≤ ±10cm (sufficient for parking). (3) Communication: vehicle localisation pose transmitted to fleet manager server at 10Hz via C-V2X (802.11p). (4) Path planning: server plans parking path (A* on parking graph), sends as sequence of waypoints. (5) Safety: velocity < 5kph in garage; emergency stop if localisation confidence drops (co-variance trace > threshold); pedestrian detection via cameras (no LiDAR due to cost); SIL/HIL testing: 100% map coverage, 99.9% localisation availability requirement.
