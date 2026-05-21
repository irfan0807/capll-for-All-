# ADAS AI Master — Complete ML/DL for Autonomous Driving

> **Level:** Principal Autonomous Driving AI Engineer  
> **Languages:** Python 3.10+ | Modern C++17/20  
> **Targets:** Tesla, NVIDIA, Waymo, Mobileye, Bosch, Continental, Aptiv, Qualcomm  
> **Standards:** ISO 26262, SOTIF (ISO 21448), AUTOSAR Adaptive, ROS2

---

## Repository Purpose

This repository simulates a **production ADAS AI engineering workspace** used at Tier 1 automotive AI teams. Every module follows real OEM/Tier1 development practices — not toy examples.

---

## Folder Structure (45 Modules)

| # | Folder | Topic | Key Files |
|---|--------|-------|-----------|
| 01 | `01_MATH_FOR_AI` | Linear algebra, probability, calculus for NN | README + notebooks |
| 02 | `02_PYTHON_FOR_ADAS_AI` | NumPy, PyTorch, TensorFlow pipelines | README + .py |
| 03 | `03_CPP_FOR_AUTOMOTIVE_AI` | High-perf C++, SIMD, real-time AI | README + .cpp |
| 04 | `04_MACHINE_LEARNING` | Regression, SVM, ensemble, anomaly detection | README + .py |
| 05 | `05_DEEP_LEARNING` | CNN, YOLO, Transformers, segmentation | README + .py |
| 06 | `06_COMPUTER_VISION` | Image processing, epipolar, homography | README + .py |
| 07 | `07_OPENCV_FOR_ADAS` | OpenCV pipelines, real-time processing | README + .py |
| 08 | `08_SENSOR_FUSION` | Kalman, EKF, UKF, radar-camera fusion | README + .py/.cpp |
| 09 | `09_AUTONOMOUS_DRIVING_STACK` | Full AD architecture, perception→actuation | README |
| 10 | `10_CAMERA_SYSTEMS` | ISP, optics, camera models, stereo | README + .py |
| 11 | `11_RADAR_SYSTEMS` | FMCW, Doppler, radar signal processing | README + .py |
| 12 | `12_LIDAR_SYSTEMS` | Point clouds, VoxelNet, PointPillars | README + .py |
| 13 | `13_LANE_DETECTION` | Classical CV + CNN + BEV lane detection | README + .py |
| 14 | `14_OBJECT_DETECTION` | YOLO v5/v8, SSD, Faster R-CNN | README + .py |
| 15 | `15_OBJECT_TRACKING` | SORT, DeepSORT, ByteTrack | README + .py |
| 16 | `16_TRAFFIC_SIGN_RECOGNITION` | CNN classifier, GTSRB | README + .py |
| 17 | `17_DRIVER_MONITORING_SYSTEM` | DMS, fatigue detection, MediaPipe | README + .py |
| 18 | `18_PEDESTRIAN_DETECTION` | Pose estimation, intent prediction | README + .py |
| 19 | `19_FREE_SPACE_DETECTION` | Drivable area segmentation | README + .py |
| 20 | `20_PATH_PLANNING` | A*, RRT, MPC, trajectory optimisation | README + .py |
| 21 | `21_BEHAVIOR_PLANNING` | Decision-making, FSM, RL for AD | README + .py |
| 22 | `22_SENSOR_CALIBRATION` | Intrinsic/extrinsic, LiDAR-camera | README + .py |
| 23 | `23_SLAM` | ORB-SLAM3, LIO-SAM, graph optimisation | README |
| 24 | `24_LOCALIZATION` | HD maps, particle filter, GNSS fusion | README + .py |
| 25 | `25_ACC_AI_SYSTEM` | Radar AI, safe distance, RL-ACC | README + .py |
| 26 | `26_LKA_AI_SYSTEM` | Steering prediction, end-to-end LKA | README + .py |
| 27 | `27_AEB_SYSTEM` | TTC, collision prediction AI | README + .py |
| 28 | `28_AUTONOMOUS_PARKING` | Surround view, path generation | README + .py |
| 29 | `29_EDGE_AI` | Quantisation, pruning, NAS | README + .py |
| 30 | `30_EMBEDDED_AI_DEPLOYMENT` | NVIDIA Drive, Jetson, TDA4VM | README |
| 31 | `31_TENSORRT_ONNX` | ONNX export, TensorRT optimisation | README + .py |
| 32 | `32_AUTOSAR_AI` | AUTOSAR Adaptive + AI integration | README |
| 33 | `33_FUNCTIONAL_SAFETY_AI` | ISO 26262 for ML, SOTIF | README |
| 34 | `34_AUTOMOTIVE_ETHERNET` | TSN, SOME/IP for AI data streams | README |
| 35 | `35_CARLA_SIMULATOR` | CARLA Python API, AD simulation | README + .py |
| 36 | `36_ROS2_AUTONOMOUS_DRIVING` | ROS2 nodes, sensor fusion stack | README + .py |
| 37 | `37_VECTOR_TOOLS` | CANoe + CAPL for AI system testing | README |
| 38 | `38_DATASETS` | KITTI, nuScenes, Waymo Open, GTSRB | README |
| 39 | `39_INTERVIEW_PREPARATION` | 500+ Q&A: ML/DL/CV/ADAS/AD | README |
| 40 | `40_REAL_WORLD_PROJECTS` | 9 production-grade mini projects | README |
| 41 | `41_DEBUGGING_SCENARIOS` | 10 real AI production debug labs | README |
| 42 | `42_SYSTEM_DESIGN` | Autonomous driving system design | README |
| 43 | `43_PERFORMANCE_OPTIMIZATION` | CUDA, TensorRT, memory, pipeline | README + .py |
| 44 | `44_AI_FOR_ECU` | Embedded inference, ASIL, scheduling | README + .cpp |
| 45 | `45_CAPSTONE_AUTONOMOUS_SYSTEM` | Full mini autonomous driving stack | README + code |

---

## 90-Day Learning Roadmap

### Phase 1 — Foundation (Days 1–30)

```
Week 1:  01_MATH_FOR_AI + 02_PYTHON_FOR_ADAS_AI
  Daily: 2h theory + 2h code
  Goal: Confident NumPy/PyTorch, understand backpropagation maths

Week 2:  03_CPP_FOR_AUTOMOTIVE_AI + 04_MACHINE_LEARNING
  Daily: 2h C++ ECU patterns + 2h ML algorithms
  Goal: Build ML pipeline for sensor anomaly detection in C++ + Python

Week 3:  05_DEEP_LEARNING + 06_COMPUTER_VISION
  Daily: CNN theory + OpenCV implementation
  Goal: Train first ADAS CNN (traffic sign classifier on GTSRB)

Week 4:  07_OPENCV_FOR_ADAS + 08_SENSOR_FUSION
  Daily: OpenCV lane detection + Kalman filter
  Goal: Real-time classical lane detection + radar object tracking
  
Assessment: Build a lane detection + vehicle tracking demo (Python)
```

### Phase 2 — ADAS Features (Days 31–60)

```
Week 5:  09_AUTONOMOUS_DRIVING_STACK + 10_CAMERA_SYSTEMS + 11_RADAR_SYSTEMS
  Goal: Understand full AD perception pipeline

Week 6:  13_LANE_DETECTION + 14_OBJECT_DETECTION
  Goal: YOLOv8 inference on KITTI dataset + CNN lane detection

Week 7:  15_OBJECT_TRACKING + 16_TSR + 17_DMS + 18_PEDESTRIAN
  Goal: Multi-object tracking + driver fatigue detection demo

Week 8:  20_PATH_PLANNING + 21_BEHAVIOR_PLANNING
  Goal: A* + MPC path planner for simulated vehicle

Assessment: ADAS feature demo: YOLOv8 + SORT tracking + lane detection
```

### Phase 3 — Deployment & Production (Days 61–90)

```
Week 9:  25_ACC_AI + 26_LKA_AI + 27_AEB
  Goal: RL-based ACC + end-to-end LKA + AEB logic

Week 10: 29_EDGE_AI + 31_TENSORRT_ONNX + 30_EMBEDDED_AI_DEPLOYMENT
  Goal: Export YOLOv8 to ONNX → TensorRT → benchmark latency

Week 11: 35_CARLA_SIMULATOR + 36_ROS2_AUTONOMOUS_DRIVING
  Goal: CARLA simulation + ROS2 sensor fusion node

Week 12: 39_INTERVIEW_PREPARATION + 45_CAPSTONE
  Goal: Complete capstone + 500 interview Q&A

Final Assessment: Mini Autonomous Driving Stack (CARLA + ROS2 + TensorRT)
```

---

## Hardware & Software Requirements

```bash
# Minimum for training:
GPU: NVIDIA RTX 3060 12GB (or Google Colab Pro)
RAM: 16GB
CPU: 8-core

# Recommended for ECU deployment:
NVIDIA Jetson Orin NX (16GB) — embedded AI target
OR Google Colab T4/A100 (free/Pro) for training

# Software:
Python 3.10+
CUDA 11.8 / 12.1
PyTorch 2.0+
TensorFlow 2.13+
OpenCV 4.8+
TensorRT 8.6+
ROS2 Humble
CARLA 0.9.14
CMake 3.16+
GCC/G++ 11+
```

## Installation

```bash
# Clone or create this repository
mkdir -p /Users/macbook/Documents/capl/adas_ai_master
cd /Users/macbook/Documents/capl/adas_ai_master

# Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install tensorflow opencv-python numpy pandas matplotlib scikit-learn
pip install ultralytics onnx onnxruntime tensorrt

# Or use requirements.txt (see 02_PYTHON_FOR_ADAS_AI/requirements.txt)
```

---

## GitHub Portfolio Plan

```
Repositories to create (each = one module):
1. adas-lane-detection          ← 13_LANE_DETECTION
2. adas-object-detection        ← 14_OBJECT_DETECTION
3. adas-sensor-fusion           ← 08_SENSOR_FUSION
4. adas-driver-monitoring       ← 17_DMS
5. adas-path-planner            ← 20_PATH_PLANNING
6. tensorrt-adas-inference      ← 31_TENSORRT_ONNX
7. ros2-autonomous-stack        ← 36_ROS2
8. mini-autonomous-vehicle      ← 45_CAPSTONE

Each repo: README with demo GIF + runnable code + model weights link
```
