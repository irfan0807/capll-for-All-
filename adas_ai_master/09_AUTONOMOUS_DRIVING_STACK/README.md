# 09 — Autonomous Driving Stack

## Overview
End-to-end autonomous driving system architecture: perception → prediction → planning → control. Covers SAE levels, system decomposition, and how each module fits into the production stack at Tesla, Waymo, and NVIDIA DRIVE.

---

## 1. SAE Automation Levels

| Level | Name | Driver Role | System Role | Examples |
|-------|------|------------|------------|---------|
| L0 | No automation | Full driver | Warnings only | FCW, LDW |
| L1 | Driver assist | Hands on | One function | ACC or LKA |
| L2 | Partial automation | Eyes on | Combined functions | Tesla Autopilot, GM SuperCruise |
| L3 | Conditional | Eyes off (some conditions) | Full loop in ODD | Mercedes DRIVE PILOT (Hwy, <60kph) |
| L4 | High automation | None in ODD | Full loop | Waymo Rider, Cruise (Urban) |
| L5 | Full automation | Never | All conditions | Not yet available |

---

## 2. ADAS vs AD System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                 ADAS ECU (L1-L2)                           │
│                                                            │
│  Camera ─┐                                                 │
│  Radar  ─┼─ Perception ──► Object List ──► ACC Controller  │
│           │                               ► LKA Controller │
│           └─ Lane Detection ──────────────► LDW / LCA      │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│                 Autonomous Driving Stack (L4)              │
│                                                            │
│  8× Camera ─┐                                              │
│  4× Radar   ├─ Perception ──► Prediction ──► Planning      │
│  1× LiDAR   │   (CNN)         (Transformer)   (A*/RL)      │
│  GPS/IMU   ─┘                                    │         │
│                                                  ▼         │
│  HD Map ─────────────────────────────────► Control        │
│                                            (MPC/PID)       │
└────────────────────────────────────────────────────────────┘
```

---

## 3. Perception Module

**Responsibilities:**
- 3D object detection (cars, pedestrians, cyclists, traffic lights, signs)
- Lane detection / road marking segmentation
- Free space / occupancy grid
- Depth estimation (mono, stereo, or LiDAR fusion)

**Key models:**
- Camera: YOLO-style anchor-based detector + FPN (Mobileye, Bosch)
- LiDAR: PointPillars, VoxelNet (Waymo)
- Fusion: BEVFusion, BEVFormer (Tesla FSD approach: pure camera BEV)

---

## 4. Prediction Module

**Responsibilities:**  
Predict future trajectories of all detected objects for 3-5 seconds horizon.

**Model types:**
| Type | Method | Notes |
|------|--------|-------|
| Physics-based | CTRA, CV model | Simple, no intent understanding |
| Map-aware | Polynomial + lane matching | Needs HD map |
| Interaction-aware | LSTM, Transformer | Models social interactions |
| Goal-based | MTR, HiVT | State-of-art (Waymo Challenge) |

```python
# Example: Constant Velocity model (CV) — baseline for highway ACC
def cv_predict(x, y, vx, vy, dt_steps, dt=0.1):
    """Predict N future positions under constant velocity."""
    positions = []
    for t in range(1, dt_steps+1):
        positions.append((x + vx*t*dt, y + vy*t*dt))
    return positions
```

---

## 5. Planning Module

**Responsibilities:**
- Route planning (A* on road graph)
- Behaviour planning (lane change decisions, intersection handling)
- Motion planning (trajectory generation — smooth, comfortable, collision-free)

**Methods:**
- **Lattice planner**: enumerate candidate trajectories, select lowest-cost
- **MPC (Model Predictive Control)**: optimise over rolling horizon
- **RL (Reinforcement Learning)**: end-to-end planning (NVIDIA DRIVE, Wayve)
- **IDM (Intelligent Driver Model)**: ACC following model

---

## 6. Control Module

```python
class PIDLateralController:
    """PID controller for lateral vehicle control (LKA/AD steering).
    Steering angle proportional to lateral error (heading + cross-track error)."""
    
    def __init__(self, Kp=0.5, Ki=0.01, Kd=0.1, dt=0.05):
        self.Kp, self.Ki, self.Kd = Kp, Ki, Kd
        self.dt = dt
        self._integral = 0.0
        self._prev_error = 0.0
    
    def compute(self, lateral_error_m: float) -> float:
        """Returns steering angle (deg). + = turn right."""
        self._integral  += lateral_error_m * self.dt
        derivative       = (lateral_error_m - self._prev_error) / self.dt
        self._prev_error = lateral_error_m
        return self.Kp * lateral_error_m + self.Ki * self._integral + \
               self.Kd * derivative
```

---

## 7. HD Map

**HD Map provides:**
- Lane geometry (polynomial curves at 10cm precision)
- Traffic rules (speed limits, no-overtake zones, stop lines)
- Semantic information (road type, lane type, road markings)

**AD-critical map features:**
- Road edge boundaries → free space limit
- Intersection topology → yield/stop rules
- Speed bump, crosswalk positions
- Traffic light association (which light governs which approach lane)

---

## 8. Interview Q&A

### L1
**Q: What is the difference between SAE L2 and L3?**  
A: L2 (Partial Automation): driver must monitor the environment continuously and be ready to take over at any time. The system operates specific functions (steering + acceleration) but the driver remains responsible. L3 (Conditional Automation): within the Operational Design Domain (ODD), the system manages all driving tasks including responding to emergencies. The driver can disengage from monitoring but must respond to a take-over request.

### L2
**Q: What is an Operational Design Domain (ODD) and why is it critical for safety?**  
A: ODD defines the specific conditions under which an AD system is designed to operate: geographic area, speed range, road type, weather, time of day. Outside the ODD, the system must safely hand over control. Example: Mercedes DRIVE PILOT ODD = German Autobahn, <60kph, good weather, daytime. SOTIF (ISO 21448) requires ODD to be defined and all reasonably foreseeable edge cases within ODD to be validated.

### L3
**Q: Compare end-to-end learning (Tesla FSD v12) vs modular pipeline approaches.**  
A: Modular: separate, interpretable components (perception → prediction → planning). Each module testable individually. Safety arguments per module. Harder to optimise jointly — local optima. End-to-end: single neural network trained with imitation learning or RL from raw sensors to steering/throttle. Better captures joint optimisation (e.g., braking while steering). Harder to explain decisions for safety case. Harder to debug individual failures. Tesla FSD v12 uses end-to-end with intervention data. Waymo uses modular with formal verification on planning layer.
