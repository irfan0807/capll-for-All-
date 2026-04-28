# ADAS Level 4 – Automotive Software Project

A complete **SAE Level 4** autonomous driving stack implemented in C++14, following MISRA-aligned coding conventions (no heap allocation, no exceptions in embedded code). The project covers the full chain from sensor ingestion through safety monitoring to CAN bus output.

---

## Project Structure

```
adas_l4_project/
├── docs/                          # 5 Learning documents
│   ├── 01_ADAS_L4_Overview.md
│   ├── 02_Sensor_Technologies.md
│   ├── 03_Perception_Algorithms.md
│   ├── 04_Path_Planning_Control.md
│   └── 05_ISO26262_Functional_Safety.md
├── include/                       # 17 header files
│   ├── sensors/                   # sensor_types, lidar, radar, camera, imu
│   ├── perception/                # perception_types, sensor_fusion, lane_detector
│   ├── planning/                  # route_types, path_planner, trajectory_generator
│   ├── control/                   # pid_controller, vehicle_controller
│   ├── safety/                    # adas_fsm, safety_monitor, emergency_handler
│   └── can/                       # adas_can_signals, adas_can_bus
├── src/                           # 13 implementation files + main.cpp
├── tests/                         # 2 test executables (50 tests total)
│   ├── test_sensors.cpp           # 23 tests – LiDAR, Radar, Camera, IMU
│   └── test_perception.cpp        # 27 tests – Fusion, Lane, PID, Safety, FSM
├── capl_scripts/
│   └── ADAS_L4_Monitor.can        # 10 CAPL test cases for CANalyzer/CANoe
└── CMakeLists.txt
```

---

## Architecture

```
LiDAR ──┐
Radar ──┤──► Sensor Fusion ──► Path Planner ──► Trajectory Gen ──► Vehicle Controller ──► CAN Bus
Camera ─┤         │                                                          ▲
IMU ────┘    Lane Detector ──────────────────────────────────────────────────┘
                  │
             Safety Monitor ◄────────────────────────────────────────────────┘
                  │
             ADAS FSM ──► Emergency Handler
```

### Modules

| Module | Description |
|--------|-------------|
| **LidarSensor** | RANSAC ground-plane removal, obstacle isolation |
| **RadarSensor** | Doppler object list, timeout/health tracking |
| **CameraSensor** | Lane quality, camera detection list |
| **ImuSensor** | Plausibility checks, dead-reckoning data |
| **SensorFusion** | 8-DOF EKF per track, Hungarian-style association, TTC |
| **LaneDetector** | Camera-primary + LiDAR fusion, departure detection |
| **PathPlanner** | Behaviour FSM (10 states), curvature-aware path |
| **TrajectoryGenerator** | Jerk-minimal quintic polynomial, 15 candidate evaluation |
| **PidController** | Anti-windup PID for longitudinal speed control |
| **VehicleController** | Speed PID + Stanley lateral, actuator command output |
| **SafetyMonitor** | Watchdog timers, fault bits, TTC → safety decision |
| **AdasFSM** | POWER_OFF → SELF_TEST → STANDBY → ACTIVE_L4 → SAFE_STOP |
| **EmergencyHandler** | AEB execution, minimal-risk gradual deceleration |
| **AdasCanBus** | CAN frame encode/transmit (0x300–0x360, UDS 0x7E2/0x7EA) |

---

## Build & Run

### Prerequisites
- CMake ≥ 3.14
- C++14-capable compiler (GCC, Clang, AppleClang)

### Compile

```bash
cd adas_l4_project
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build .
```

### Run simulation (6 scenarios)

```bash
./adas_l4_sim
```

**Scenarios covered:**
1. Highway cruise – L4 engaged at 120 km/h
2. Lead vehicle – ACC follow mode with TTC warning
3. Pedestrian crossing – yield decision and full brake
4. LiDAR failure – degraded mode transition
5. AEB trigger – TTC < 1 s → 100 % brake
6. ODD exit – minimal risk / safe stop

### Run unit tests

```bash
ctest --verbose
# or individually:
./test_sensors
./test_perception
```

**Results (verified):**
```
100% tests passed, 0 tests failed out of 2
  test_sensors    – 23/23 passed
  test_perception – 27/27 passed
```

---

## Key Technical Details

### CAN Message Map

| CAN ID | Message | Rate |
|--------|---------|------|
| 0x300 | Object List (up to 8 objects) | 100 ms |
| 0x310 | Lane Info (offset, width, curvature) | 100 ms |
| 0x320 | Ego State (speed, yaw, position) | 100 ms |
| 0x330 | Path Info (next waypoint) | 100 ms |
| 0x340 | Vehicle Command (throttle, brake, steer) | 20 ms |
| 0x350 | Safety Status (fault bits, decision) | 10 ms |
| 0x360 | Sensor Health (LiDAR/Radar/Camera/IMU) | 100 ms |
| 0x7E2/0x7EA | UDS Diagnostic (DID 0x0200–0x0202) | on-demand |

### Safety Thresholds (ISO 26262 ASIL D)

| Parameter | Value |
|-----------|-------|
| TTC → AEB trigger | < 1.0 s |
| TTC → Warning | < 2.5 s |
| Sensor fusion timeout | 50 ms |
| Planning timeout | 200 ms |
| Control timeout | 50 ms |
| Sensors failed → MINIMAL_RISK | ≥ 2 sensors |

### EKF State Vector

$$\mathbf{x} = [p_x,\ p_y,\ v_x,\ v_y,\ a_x,\ a_y,\ \psi,\ \dot\psi]^T$$

---

## Learning Documents

| File | Topics |
|------|--------|
| `01_ADAS_L4_Overview.md` | SAE levels, architecture, CAN DBC spec |
| `02_Sensor_Technologies.md` | LiDAR ToF, FMCW radar, camera ISP, IMU |
| `03_Perception_Algorithms.md` | EKF, data association, TTC, lane polynomials |
| `04_Path_Planning_Control.md` | Frenet frame, quintic trajectories, PID, Stanley, MPC |
| `05_ISO26262_Functional_Safety.md` | HARA, ASIL, FMEA, watchdog design |

---

## CAPL Test Script

`capl_scripts/ADAS_L4_Monitor.can` provides 10 test cases for use in **CANalyzer / CANoe**:

- TC1: Safety heartbeat @ 10 Hz
- TC2: L4 engagement state validation
- TC3–TC4: Object list and lane info presence
- TC5: AEB trigger via UDS DID 0x0200
- TC6: Speed command limits (0–100 %)
- TC7: LiDAR fault → degraded mode
- TC8: ODD exit → minimal risk
- TC9: Emergency brake = 100 %
- TC10: Bus load < 50 %

---

## Relation to Other Projects

| Project | Protocol | Location |
|---------|----------|----------|
| ECU CAN/UDS | ISO 11898, ISO 14229, ISO 15765-2 | `ecu_can_uds_project/` |
| **ADAS L4** | SAE L4, ISO 26262 ASIL D | `adas_l4_project/` ← you are here |
