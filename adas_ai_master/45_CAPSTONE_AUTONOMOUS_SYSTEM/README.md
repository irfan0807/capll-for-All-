# 45 — Capstone: Mini Autonomous Driving Stack

## Overview
Integrates all 44 preceding modules into a complete autonomous driving stack: Perception → Threat Assessment → Path Planning → Longitudinal + Lateral Control → AEB Safety Override → Vehicle Model. Runs in simulation mode on any CPU; intended to be migrated to ROS2 + Jetson Orin NX for embedded execution.

---

## 1. Stack Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Mini Autonomous Stack (30Hz)                  │
│                                                                 │
│  ┌──────────────┐   ┌───────────────────────┐                  │
│  │  Perception  │   │   Threat Assessment   │                  │
│  │ (Cam+Radar)  │──▶│   TTC, path overlap   │                  │
│  │  Module 14/15│   │      Module 27        │                  │
│  └──────────────┘   └────────────┬──────────┘                  │
│                                  │                              │
│  ┌──────────────────────────────▼──────────────────────────┐   │
│  │              Path Planner (Module 20)                   │   │
│  │  Waypoints: ego-centric, 2m spacing, 20 points ahead    │   │
│  └──────────────────────┬────────────────────────────────--┘   │
│                         │                                       │
│  ┌──────────────────────▼────────────────────────────────┐     │
│  │              Controllers                              │     │
│  │  Longitudinal: IDM (Module 25)  →  Acceleration cmd  │     │
│  │  Lateral: Stanley (Module 26)   →  Steering angle    │     │
│  └──────────────────────┬──────────────────────────────--┘     │
│                         │                                       │
│  ┌──────────────────────▼────────────────────────────────┐     │
│  │              AEB Safety Override (Module 27)          │     │
│  │  TTC < 1.0s → Full brake  |  TTC < 1.6s → Partial    │     │
│  └──────────────────────┬──────────────────────────────--┘     │
│                         │                                       │
│  ┌──────────────────────▼────────────────────────────────┐     │
│  │              Vehicle Model (Bicycle Model)            │     │
│  │  x, y, heading, speed → next state                   │     │
│  └───────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Module Integration Map

| Module | Component | Role in Capstone |
|--------|-----------|-----------------|
| 06 Computer Vision | Camera pipeline | Raw perception foundation |
| 08 Sensor Fusion | EKF fusion | Camera + radar track fusion |
| 14 Object Detection | YOLOv8 | Detect cars, pedestrians, cyclists |
| 15 Object Tracking | Kalman tracker | Continuous tracks between frames |
| 20 Path Planning | A*/IDM | Trajectory generation |
| 25 ACC | IDM controller | Longitudinal gap control |
| 26 LKA | Stanley controller | Lateral lane keeping |
| 27 AEB | TTC + safety override | Emergency braking |
| 29 Edge AI | INT8 TRT | Model deployment on ECU |
| 33 Functional Safety | ASIL monitors | Safety watchdogs |
| 36 ROS2 | Node graph | Production deployment |

---

## 3. Running the Capstone

```bash
# Run demo scenarios
python mini_autonomous_stack.py

# Expected output:
# Scenario: highway_follow (90 steps @ 30Hz)
#  Step  Speed     Acc   Steer   Brake      TTC  Objects
#     0  28.0m/s  +0.5m/s²  +0.0°     0%   5.3s    2 obj
#    10  28.8m/s  +0.3m/s²  +0.0°     0%   5.8s    2 obj
# ...
# Scenario: pedestrian_crossing
#     0  15.0m/s  -0.1m/s²  +0.0°     0%   2.1s    1 obj
#    10  13.1m/s  -4.0m/s²  +0.0°    60%   1.4s    1 obj
#    20   5.1m/s  -8.0m/s²  +0.0°   100%   0.8s    1 obj  ← AEB FULL
```

---

## 4. Production Migration Checklist

```
From simulation → ROS2 (Module 36):
[ ] Replace PerceptionModule.detect_objects() with ROS2 subscriber
    (/camera/detections topic from YOLOv8 node)
[ ] Replace VehicleModel.step() with real vehicle CAN feedback
    (speed from wheel sensors, yaw rate from IMU)
[ ] Add ROS2 publisher for /vehicle/cmd_vel (VehicleCommand)
[ ] Wrap each module as independent ROS2 node
[ ] Add TF2 transforms for coordinate frames

From simulation → ECU (Module 44):
[ ] Replace Python IDM/Stanley with C++ implementations
[ ] All control loops: static allocation, no std::vector
[ ] Compile with -O2 -DNDEBUG for production
[ ] Add ASIL watchdog (50ms inference timeout)
[ ] Add CAN FD output (AEB_Active, Steering_Torque, ACC_Accel)
[ ] HIL validation: 200+ test scenarios (Module 37)
```

---

## 5. Performance Analysis

```
Scenario: highway_follow at 30m/s, lead car at 40m, 30m/s
  ├── IDM gap maintained: ~25m (T=1.5s headway × 30m/s = 45m target)
  ├── Speed convergence: 5 seconds to settle
  └── AEB not triggered (TTC = 40/0 = ∞, no closing speed)

Scenario: pedestrian_crossing at 15m/s, ped at 25m, 1m/s lateral
  ├── TTC initial: 25/15 = 1.67s → PARTIAL BRAKE (−4 m/s²)
  ├── TTC at step 10: ~1.4s → PARTIAL BRAKE continues
  ├── TTC at step 20: ~0.8s → FULL BRAKE (−8 m/s²)
  └── Stop before collision ✓

Scenario: empty_road, start at 0 m/s
  ├── Free cruise IDM: a = 2.5 × (1 − 0⁴) = 2.5 m/s²
  ├── Converges to 30 m/s in ~12 seconds
  └── No AEB events ✓
```

---

## 6. Safety Considerations (ISO 26262 / SOTIF)

| Risk | Mitigation |
|------|----------|
| Perception false negative | AEB still checks radar independently |
| Controller runaway | Steering limited ±0.4 rad, acceleration ±8 m/s² |
| Watchdog timeout | If step() > 50ms → fallback to constant deceleration |
| ODD violation | Map + sensor quality checks gate autonomous mode |

---

## 7. Interview Q&A

### L1
**Q: What is the purpose of a capstone project in an ADAS engineering role?**  
A: A capstone demonstrates the ability to integrate multiple subsystems into a functional whole. In ADAS: it shows you understand not just individual algorithms (KF, IDM, NMS) but how they interact — timing dependencies, interface definitions, failure mode propagation. Interviewers look for: (1) module boundary clarity (where does perception end, planning begin?); (2) error handling at interfaces (what if perception returns 0 objects?); (3) safety-aware design (what is the fallback when a module fails?).

### L2
**Q: Walk through the control cycle of the mini autonomous stack and explain the timing constraints.**  
A: 30Hz cycle = 33ms budget. Breakdown: (1) Perception: camera frame arrives every 33ms; object detection 8ms (INT8 TRT); KF track update 2ms; total: 10ms. (2) Threat assessment: TTC + path overlap for all tracks: 1ms. (3) Path planning: 20-waypoint generation: 0.5ms. (4) IDM longitudinal: closed-form equation: < 0.1ms. (5) Stanley lateral: < 0.1ms. (6) AEB check: threshold comparison: < 0.1ms. (7) CAN output: 0.1ms. Total: ~12ms → well within 33ms. Margin used for sensor synchronisation and system overhead. If over-budget: reduce detection resolution (416→320), or cache path plan every 2nd frame.

### L3
**Q: If you were presenting this capstone to a principal engineer at Waymo or Tesla, what would you emphasise and what would you improve?**  
A: Emphasise: (1) Clean module interfaces → each module has clear input/output type contracts; (2) Safety override non-negotiable → AEB overrides any planner decision regardless of confidence; (3) Systematic validation mindset → included scenario-based testing framework (not just "it runs"). Improve for production: (1) Replace simple path planner with Hybrid-A* or lattice planner with dynamic obstacle prediction; (2) Add a motion prediction module (Transformer or LSTM predicting each object's future trajectory for 3 seconds) — IDM assumes constant velocity, unsafe for cut-in scenarios; (3) Multi-policy planner with uncertainty: instead of single trajectory, generate and evaluate N candidate trajectories, select one with minimum expected cost (handles occlusion, uncertain pedestrian intent); (4) E2E testing: current scenario testing is hand-crafted; real deployment requires 10,000+ CARLA scenarios including edge cases; (5) Formal safety analysis: HAZOP / FMEA on each module interface.
