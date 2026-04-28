# ADAS Level 4 – Complete Technical Reference

## 1. SAE Autonomy Levels (J3016)

| Level | Name | Driver's Role | System Handles |
|-------|------|--------------|---------------|
| L0 | No Automation | Full human control | None |
| L1 | Driver Assistance | Monitors always | Steering OR acceleration |
| L2 | Partial Automation | Monitors always | Steering AND acceleration |
| L3 | Conditional Automation | Ready to take over | All tasks in defined conditions |
| **L4** | **High Automation** | **Not needed in ODD** | **All tasks in defined ODD** |
| L5 | Full Automation | Never needed | All tasks everywhere |

**ODD = Operational Design Domain** (the defined conditions under which the system operates: geofenced highway, speed limit, weather, etc.)

---

## 2. L4 ADAS System Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        ADAS L4 System Architecture                        │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                         SENSOR LAYER                                 │ │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌─────────────────┐  │ │
│  │  │  LiDAR    │  │  Camera   │  │   Radar   │  │ GNSS / IMU / HD │  │ │
│  │  │ 128-beam  │  │ 8× surr.  │  │ 4× corner │  │    Map / V2X    │  │ │
│  │  │ 360°/10Hz │  │ 60fps     │  │ 77GHz     │  │                 │  │ │
│  │  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └────────┬────────┘  │ │
│  └────────┼──────────────┼──────────────┼─────────────────┼────────────┘ │
│           └──────────────┴──────────────┴─────────────────┘              │
│                                    │                                       │
│  ┌─────────────────────────────────▼──────────────────────────────────┐  │
│  │                       PERCEPTION LAYER                              │  │
│  │  ┌──────────────────┐   ┌──────────────────┐   ┌────────────────┐  │  │
│  │  │  Sensor Fusion   │   │ Object Detection  │   │ Lane / Road    │  │  │
│  │  │  (Kalman Filter) │   │ & Tracking (MOT)  │   │ Understanding  │  │  │
│  │  └──────────────────┘   └──────────────────┘   └────────────────┘  │  │
│  └───────────────────────────────────┬────────────────────────────────┘  │
│                                       │ World model                        │
│  ┌────────────────────────────────────▼───────────────────────────────┐  │
│  │                        PLANNING LAYER                               │  │
│  │  ┌──────────────┐  ┌───────────────────┐  ┌────────────────────┐  │  │
│  │  │ Route Plan   │  │ Behavioral Plan   │  │ Trajectory Plan    │  │  │
│  │  │ (HD Map)     │  │ (Lane change,     │  │ (Spline, velocity  │  │  │
│  │  │              │  │  turn, merge)     │  │  profile MPC)      │  │  │
│  │  └──────────────┘  └───────────────────┘  └────────────────────┘  │  │
│  └───────────────────────────────────┬────────────────────────────────┘  │
│                                       │ Commands                           │
│  ┌────────────────────────────────────▼───────────────────────────────┐  │
│  │                        CONTROL LAYER                                │  │
│  │  ┌──────────────┐  ┌──────────────────┐  ┌────────────────────┐   │  │
│  │  │ Longitudinal │  │    Lateral        │  │  Safety Monitor    │  │  │
│  │  │ (PID ACC)    │  │ (Stanley/MPC)     │  │  (ISO 26262 ASIL D)│  │  │
│  │  └──────────────┘  └──────────────────┘  └────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                       │ Actuator targets                  │
│            THROTTLE / BRAKE / STEERING WHEEL / GEAR                       │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. L4 Sensors – Specifications

### LiDAR (Light Detection and Ranging)

```
Technology: Time-of-flight pulsed laser (905nm / 1550nm)
Resolution: 128 beams × 2048 azimuth points
Range:      0.1m – 300m
Accuracy:   ±2cm at 100m
Rate:       10 Hz (full rotation), 20 Hz (forward half)
Data:       ~1.5M points/sec → PointCloud (x, y, z, intensity, ring)
FOV:        360° azimuth, ±15° vertical
Mounting:   Roof center (Velodyne VLP-128 / Hesai AT128)

Point cloud format:
  struct LidarPoint { float x, y, z, intensity; uint8_t ring; };
  Coordinate: sensor frame → ego vehicle frame (calibration matrix)
```

### Camera

```
Count:      8 cameras (surround view)
  - 3× forward (long, mid, short range)
  - 2× side pillar
  - 2× rear
  - 1× fisheye front
Resolution: 1920×1080 @ 60fps (forward main: 3840×2160)
FOV:        52° (long range) to 190° (fisheye)
Pipeline:   ISP → debayer → undistort → Neural network inference
Outputs:    2D bounding boxes, lane markings, semantic segmentation
```

### Radar

```
Count:      4 (corner) + 1 (long-range forward)
Frequency:  77 GHz (chirp FMCW)
Range:      0.5m – 250m (long range)
Velocity:   ±100 km/h (Doppler directly measured)
Range res:  0.4m @ 250m range
Advantages: Works in rain/fog/snow, measures velocity directly, 24/7
Output:     Object list (range, azimuth, elevation, Dv, RCS)
```

### GNSS + IMU + HD Map

```
GNSS:  RTK-corrected GPS/GLONASS/BeiDou → 2cm accuracy (RTK mode)
IMU:   6-DOF MEMS (3× accelerometer + 3× gyroscope)
       • Accelerometer: ±6g, 100Hz
       • Gyro: ±300°/s, 100Hz
HD Map: Lane-level map with 10cm accuracy
        Layers: roads, lanes, signs, traffic lights, speed limits, crossings
V2X:   DSRC/C-V2X for infrastructure communication
```

---

## 4. Sensor Fusion Architecture (Extended Kalman Filter)

```
EKF State Vector (per tracked object):
  x = [px, py, vx, vy, ax, ay, yaw, yaw_rate]
      Position  Velocity  Accel  Heading

Predict Step (motion model):
  x_pred = F · x_prev + noise
  P_pred = F · P · F^T + Q

Update Step (per sensor measurement):
  y = z - H · x_pred          (Innovation)
  S = H · P_pred · H^T + R   (Innovation covariance)
  K = P_pred · H^T · S^-1    (Kalman gain)
  x = x_pred + K · y
  P = (I - K · H) · P_pred

Sensor-specific measurement matrices H, noise R:
  LiDAR:  H_lidar = [1 0 0 0 0 0 0 0]   (observe px, py)
                    [0 1 0 0 0 0 0 0]
  Radar:  H_radar = [1 0 0 0 0 0 0 0]   (observe px, py, vx, vy)
                    [0 1 0 0 0 0 0 0]
                    [0 0 1 0 0 0 0 0]
                    [0 0 0 1 0 0 0 0]
  Camera: H_cam = [1 0 0 0 0 0 0 0]     (observe px, py ← projected)
                  [0 1 0 0 0 0 0 0]
```

---

## 5. Object Classification

| Class | Typical Size (L×W×H) | Key Sensor | Use in Planning |
|-------|---------------------|------------|----------------|
| Car | 4.5×1.8×1.5m | Cam+LiDAR | Keep safety margin 2s |
| Truck | 12×2.5×3.5m | LiDAR+Radar | Extended safety margin |
| Pedestrian | 0.5×0.5×1.8m | Camera | Hard-stop if trajectory crosses |
| Cyclist | 0.6×0.6×1.8m | Cam+LiDAR | Yield, 1.5m side clearance |
| Motorcycle | 2.0×0.8×1.5m | Cam+Radar | Lane-lane monitoring |
| Static Obs. | Variable | LiDAR | Minimum 0.3m clearance |
| Unknown | Unknown | Any | Treat as worst-case |

---

## 6. L4 Functional Safety – ISO 26262 ASIL Allocation

| Function | ASIL | Monitoring |
|----------|------|-----------|
| Emergency Stop | **ASIL D** | Hardware + SW watchdog |
| Steering Control | **ASIL D** | Dual-channel EPS |
| Braking Control | **ASIL C** | Redundant braking |
| Object Detection | **ASIL B** | Fault injection testing |
| Path Planning | **ASIL B** | Plausibility checks |
| Sensor Fusion | **ASIL B** | Cross-sensor validation |
| Route Planning | **ASIL A** | HD map sanity checks |

---

## 7. ADAS CAN Messages (typical)

```dbc
BO_ 640 ADAS_ObjectList1: 8 ADAS_ECU
 SG_ Obj1_ID       : 0|8@1+   (1,0)    [0|255]     ""
 SG_ Obj1_Class    : 8|4@1+   (1,0)    [0|15]      ""   // 0=car,1=truck,2=ped...
 SG_ Obj1_Range    : 12|12@1+ (0.1,0)  [0|409.5]   "m"
 SG_ Obj1_Azimuth  : 24|12@1+ (0.1,-204.8) [-204.8|204.7] "deg"
 SG_ Obj1_RelVel   : 36|12@1+ (0.05,-102.4)[-102.4|102.35] "m/s"
 SG_ Obj1_ConfScore: 48|8@1+  (0.392,0)[0|99.8]    "%"

BO_ 672 ADAS_LaneInfo: 8 ADAS_ECU
 SG_ LaneWidth      : 0|8@1+  (0.04,0) [0|10.16]   "m"
 SG_ LKA_Warning    : 8|2@1+  (1,0)    [0|3]        ""
 SG_ LKA_Active     : 10|1@1+ (1,0)    [0|1]        ""
 SG_ LeftLaneConf   : 11|4@1+ (6.67,0) [0|100]      "%"
 SG_ RightLaneConf  : 15|4@1+ (6.67,0) [0|100]      "%"
 SG_ LateralOffset  : 19|10@1+(0.01,-5.12)[-5.12|5.11] "m"

BO_ 704 ADAS_DrivingMode: 4 ADAS_ECU
 SG_ DrivingMode    : 0|4@1+  (1,0)    [0|15]       ""  // 0=Manual..4=L4_Auto
 SG_ SystemReady    : 4|1@1+  (1,0)    [0|1]        ""
 SG_ TakeoverReq    : 5|1@1+  (1,0)    [0|1]        ""
 SG_ EmergencyStop  : 6|1@1+  (1,0)    [0|1]        ""
 SG_ ODD_Valid      : 7|1@1+  (1,0)    [0|1]        ""

BO_ 736 ADAS_VehicleCmd: 8 ADAS_ECU
 SG_ TargetSpeed    : 0|12@1+ (0.1,0)  [0|409.5]    "km/h"
 SG_ TargetAccel    : 12|10@1+(0.01,-5.12)[-5.12|5.11]"m/s2"
 SG_ SteeringAngle  : 22|12@1+(0.1,-204.8)[-204.8|204.7]"deg"
 SG_ BrakePressure  : 34|10@1+(0.1,0)  [0|102.3]    "bar"
 SG_ GearRequest    : 44|3@1+ (1,0)    [0|7]        ""
```

---

## 8. L4 System State Machine

```
                    ┌─────────────────────────────────────────┐
                    │        ADAS L4 Operating States          │
                    └─────────────────────────────────────────┘

    POWER_OFF ──IGN_ON──► SELF_TEST ──PASS──► STANDBY ──ENGAGE──► ACTIVE_L4
                              │                   │                     │
                              │ FAIL              │ ODD_EXIT        SAFE_STOP
                              ▼                   ▼                     │
                           FAULT ◄──CRITICAL── MINIMAL_RISK_COND ◄─────┘
                                                  │
                                              PULL_OVER
                                            (stop safely)

State Descriptions:
  POWER_OFF:          ECU unpowered
  SELF_TEST:          Boot diagnostics – sensor checks, calibration verify
  STANDBY:            All systems ready, awaiting driver engagement
  ACTIVE_L4:          Full autonomy within ODD
  SAFE_STOP:          Controlled emergency stop (AEB triggered)
  MINIMAL_RISK_COND:  ODD exited → pull over and stop
  FAULT:              Unrecoverable hardware/software fault
```
