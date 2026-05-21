# 42 — System Design for ADAS AI

## Overview
End-to-end system design answers for senior ADAS AI engineer interviews. Covers perception stacks, sensor fusion architectures, edge deployment systems, and complete AD stacks.

---

## Design Question 1: "Design an AEB System for a Premium Sedan"

### Requirements Clarification
- Euro NCAP AEB score ≥ 85%
- ISO 26262 ASIL-B
- Speed range: 0–200kph
- Scenarios: CCRs, CCRm, CCRb, Pedestrian (day + night), Cyclist
- Latency: sensor to brake ≤ 600ms

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     SENSOR LAYER                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ LRR Radar   │  │ Front Cam   │  │ SRR Radar (corners) │ │
│  │ 200m, 20Hz  │  │ 1920×1080   │  │ 80m, 20Hz           │ │
│  │ CAN FD      │  │ 30Hz Eth    │  │ CAN FD              │ │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────────┘ │
│         │                │                   │              │
└─────────┼────────────────┼───────────────────┼─────────────┘
          │                │                   │
┌─────────▼────────────────▼───────────────────▼─────────────┐
│                ADAS DOMAIN CONTROLLER ECU                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Perception Module                                  │    │
│  │  Camera: YOLOv8s INT8 (8ms, pedestrian/vehicle/cyc) │    │
│  │  Radar: Kalman tracker (all objects, range + rate)  │    │
│  │  Fusion: EKF per-track (camera + radar)             │    │
│  └───────────────────────────┬─────────────────────────┘    │
│  ┌────────────────────────────▼──────────────────────────┐  │
│  │  AEB Function (ASIL-B via decomposition)              │  │
│  │  TTC computation (range / range_rate)                 │  │
│  │  Path overlap check (lateral corridor)                │  │
│  │  Threat classification (WARNING/PARTIAL/FULL)         │  │
│  │  Safety monitor (dual-sensor AND gate for FULL AEB)   │  │
│  └───────────────────────────┬───────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────┘
                               │ CAN (AEB_Active, AEB_Decel)
                               ▼
                     ABS/Brake ECU → Calipers
```

### Safety Architecture (ASIL-B)
```
Camera perception   : ASIL-A (E2E, watchdog, plausibility)
Radar perception    : ASIL-A (E2E, watchdog, hardware redundancy)
                         ↓           ↓
              AND gate: FULL AEB requires both sensors
              OR gate: WARNING can use either sensor
Result: ASIL-A (cam) × ASIL-A (rad) = ASIL-B (combined)
```

### Key Design Decisions
| Decision | Choice | Rationale |
|---------|--------|-----------|
| Sensor priority | Radar primary for range, camera for classification | Radar more reliable range; camera needed for pedestrian/cyclist class |
| Fusion | Late fusion (track level) | Easier ASIL decomposition, graceful degradation |
| AEB trigger | TTC < 2.7s + path overlap > 30% | Euro NCAP ISR optimised threshold |
| Night capability | IR-capable camera (850nm) | Required for pedestrian NCAP night tests |

---

## Design Question 2: "Design Tesla FSD Perception Stack (No LiDAR)"

### Constraints
- 8 cameras (3MP each), no radar (FSD v12+), no LiDAR
- Must produce 3D scene understanding for planning
- Target: full self-driving capability Level 4

### Architecture
```
8 Cameras (360° coverage, ~3MP each)
  ↓  
Per-Camera Feature Extractor: RegNet-Y-3.2GF (per cam backbone)
  ↓
Transformer BEV Encoder (Tesla Hydranet-style):
  - Multi-camera cross-attention to BEV grid
  - 50m × 50m BEV resolution: 0.2m/cell = 250×250 grid
  - Temporal fusion: BEV features from past 8 frames integrated
  ↓
Multi-Task Heads (all in BEV space):
  - 3D Object Detection (class, x,y,z, velocity, heading)
  - Occupancy Prediction (per-cell occupied probability)
  - Lane Graph (node + edge topology)
  - Drivable Area
  - Traffic light state (with vector association)
  ↓
Autoregressive Trajectory Planner (Transformer):
  - Input: BEV features + ego state + routing goal
  - Output: 6-second trajectory (x,y,v,a) at 10Hz
```

### Key Trade-offs
| Trade-off | Tesla FSD Choice | Alternative |
|-----------|-----------------|------------|
| Range measurement | Depth from parallax + temporal | LiDAR direct range |
| 3D from 2D | Learned perspective transform | Physical camera model + BEV |
| Failure mode | Rare OOD scenarios fail | Sensor hw failure (LiDAR) |
| Cost | Low (cameras cheap) | High (LiDAR $500-$5000) |

---

## Design Question 3: "Design a Scalable Data Pipeline for ML at an OEM"

### Requirements
- 1000 test vehicles globally
- 4 cameras + 3 radar + 1 LiDAR per vehicle
- 8 hours/day driving → 8TB raw data/vehicle/day
- Goal: continuously improve models with fleet data

### Pipeline Architecture
```
Vehicle → OTA upload → Data Lake (S3) → Trigger detection → Auto-label → Human review → Training
```

### Detailed Design
```python
# Trigger detection: which frames need human labelling?
def should_send_for_labelling(frame_metadata: dict) -> bool:
    """Identify high-value frames for labelling."""
    # High uncertainty from ensemble: model doesn't know
    if frame_metadata['model_uncertainty'] > 0.7:
        return True
    # Low confidence on critical class
    if frame_metadata['pedestrian_max_conf'] < 0.6:
        return True
    # Scenario flag (ODD boundary: rain, night, construction)
    if frame_metadata['weather_score'] > 0.6:
        return True
    # Random sample (coverage)
    if random.random() < 0.002:    # 0.2% random
        return True
    return False
```

**Annotation pipeline:**
```
Auto-label (detector ensemble → initial boxes)
  ↓
Active learning selection (uncertain frames first)
  ↓
Human annotators (via label tool: CVAT, Scale AI, LabelBox)
  ↓
QA pass (second annotator reviews 10%)
  ↓
Consensus check: IoU(annotator1, annotator2) > 0.8
  ↓
Approved → Training dataset (versioned, immutable)
```

**Model training cycle:**
- Weekly: fine-tune on newest 100K labelled frames
- Monthly: full retrain on entire dataset
- Gate: must pass acceptance test suite before deployment
- Deploy: OTA to test fleet first (100 vehicles, 2 weeks) → full fleet

---

## Design Question 4: "Design a Real-Time LiDAR Processing Pipeline for L3 Highway Pilot"

### Requirements
- LiDAR: 64-beam, 360°, 20Hz, 128K points/scan
- Output: 3D tracks to AEB/ACC in < 50ms
- Hardware: Jetson Orin NX

### Pipeline
```
Raw scan (128K pts) → Ground removal (RANSAC plane, 2ms)
  ↓
Euclidean clustering (DBSCAN, radius=0.5m, 5ms)
  ↓
Bounding box fitting (PCA per cluster, 1ms)
  ↓
PointPillars inference INT8 (8ms, Orin NX)
  ↓
Track association (Hungarian + KF, 2ms)
  ↓
Output: 3D ObjectList via SOME/IP (total: ~18ms)
```

### Code: Ground Removal
```python
import numpy as np

def remove_ground_plane(points: np.ndarray,
                        height_thresh: float = -1.5,
                        ransac_iters: int = 100) -> np.ndarray:
    """Remove ground plane via RANSAC. points: (N,3) [x,y,z]"""
    best_inliers = np.ones(len(points), dtype=bool)
    best_inlier_count = 0
    
    for _ in range(ransac_iters):
        # Sample 3 random points
        idx = np.random.choice(len(points), 3, replace=False)
        p1, p2, p3 = points[idx]
        
        # Plane normal
        v1 = p2 - p1; v2 = p3 - p1
        n  = np.cross(v1, v2)
        if np.linalg.norm(n) < 1e-6:
            continue
        n /= np.linalg.norm(n)
        d  = -np.dot(n, p1)
        
        # Count inliers
        dist = np.abs(points @ n + d)
        inliers = dist < 0.15    # 15cm tolerance
        
        if inliers.sum() > best_inlier_count:
            best_inlier_count = inliers.sum()
            best_inliers = inliers
    
    # Return non-ground points
    return points[~best_inliers]
```

---

## Interview Q&A

### L1
**Q: What are the key components of an ADAS ECU?**  
A: (1) Sensor interfaces: CAN FD / Ethernet physical layer interfaces to radar/camera/LiDAR; (2) Processor: SoC with CPU (ARM A72) + AI accelerator (DLA, NPU) + GPU; (3) AI inference: TIDL/TensorRT INT8 model running perception; (4) Fusion layer: Kalman tracker combining sensor outputs; (5) Safety monitors: watchdogs, E2E checks, ASIL monitors; (6) Output interface: CAN/SOME/IP to braking/steering actuators; (7) Diagnostics: DTC management, OBD-II support.

### L2
**Q: How would you architect a system where camera and radar must both agree before triggering AEB (dual-channel safety)?**  
A: ASIL-B decomposition: (1) Camera and radar run as independent ASIL-A channels — separate HW, separate SW, no shared code or memory; (2) Each channel independently assesses TTC and object confidence; (3) AEB full brake: AND gate — both channels must declare threat; (4) AEB warning/prefill: OR gate — either channel can warn; (5) Temporal consistency: each channel must independently declare threat for >2 frames (prevents transient spikes); (6) Diagnostic: if one channel fails (DTC) → system degrades to single-sensor mode with higher threshold (more conservative).

### L3
**Q: You are the architecture lead for a new L3 highway pilot. Walk through your sensor selection and justification.**  
A: (1) Front perception: 1× LRR radar (range 200m, ASIL-A, all weather) + 1× front camera (range 150m, classifies pedestrian/cycle) → AEB ASIL-B; (2) Side/rear: 4× SRR radar (corners, 80m) → lane change, blind spot; (3) Lane keeping: 2× side cameras (100m forward looking, wide FoV) → lane lines, boundaries; (4) Optional LiDAR: 1× front LiDAR (120m, 10Hz) → dense 3D for edge cases; adds $600/vehicle → justified for L3 premium only; (5) HD map: LTE-connected HD map for localisation and road context; (6) Localisation: GNSS + IMU + camera lane matching → GNSS-denied tunnel capability; Total ECU: one domain controller (NVIDIA Orin 64TOPS), three zone ECUs (cameras), separate radar CAN network. Cost vs competitor benchmark before final sensor freeze.
