# 40 — Real-World ADAS AI Projects

## Overview
End-to-end project walkthroughs from five production ADAS AI deployments: pedestrian detector, parking AI, ACC system integration, lane departure detection, and a HIL regression suite.

---

## PROJECT 1: Pedestrian Detection System — Production Deployment

### Problem Statement
OEM required pedestrian AP > 87% at distances 5–80m, day/night, city + highway, on TDA4VM ECU at < 12ms latency per frame. Starting baseline: YOLOv8n, AP = 79% (day), 58% (night). Deployment hardware: TI TDA4VM with TIDL accelerator.

### Architecture
```
Input: 1920×1080 @ 30fps (ISP de-bayered)
  ↓
Resize to 640×384 (maintain AR)
  ↓ 
YOLOv8n backbone (INT8 TIDL)
  ↓
FPN neck (P3/P4/P5)
  ↓
Detection head (anchor-free, 3 scales)
  ↓
NMS (threshold=0.3, IoU=0.45)
  ↓
Output: PedDetection CAN FD message (range, lateral, confidence)
```

### Development Timeline
- Week 1-2: Data analysis. Found 73% of training failures occurred on partial occlusion (>50%) and small pedestrians (< 40px height).
- Week 3-4: Data augmentation pipeline: copy-paste augmentation to increase partial occlusion examples 4×; mosaic augmentation for small object diversity.
- Week 5-6: Architecture: switched from YOLOv8n to YOLOv8s (5.3M → 11.2M params); justified by 3ms latency budget available.
- Week 7-8: Night performance: added IR channel (from NIR-capable camera) as 4th input; trained with day+night data 50/50.
- Week 9-10: TDA4VM TIDL deployment: exported to ONNX, ran TIDL calibration with 1000-frame INT8 calibration set; verified accuracy degradation < 1.5% AP.
- Week 11-12: Validation: 50 physical test scenarios; pass on Euro NCAP PED test points.

### Results
| Metric | Baseline | Final |
|--------|---------|-------|
| Day AP@0.5 | 79% | 91% |
| Night AP@0.5 | 58% | 84% |
| 5-80m AP | 72% | 89% |
| TDA4VM latency | N/A | 10.8ms |

### Key Lessons
1. Data quality >> model size: targeted data collection (partial occlusion, night) improved AP more than architecture changes.
2. INT8 calibration set: must use representative data; using only day data for calibration caused 4% night AP drop → use 50/50.
3. ECU export testing: run inference accuracy check at each export step (PyTorch → ONNX → TRT/TIDL) — errors compound.

---

## PROJECT 2: Automated Parking AI — End-to-End

### Problem Statement
Implement Remote Park Assist (RPA): vehicle finds slot, manoeuvres autonomously while driver stands outside. Sensors: 12 USS + 4 surround-view cameras. Platform: NVIDIA Jetson Orin NX.

### AI Components
```python
# High-level pipeline
class ParkingAIPipeline:
    def __init__(self):
        self.bev_stitcher   = BEVStitcher(cameras=4)       # 4-camera BEV
        self.slot_detector  = SlotDetectionModel()          # YOLO-based slot detection
        self.occupancy_grid = USSParkingGrid(rows=40,cols=40) # 5cm resolution
        self.path_planner   = HybridAStarPlanner()          # Reeds-Shepp curves
        self.controller     = StanleyController()           # Lateral control
    
    def run_once(self, camera_frames, uss_readings) -> ParkingCommand:
        # Step 1: Build BEV
        bev = self.bev_stitcher.stitch(camera_frames)       # 800×800 BEV image
        
        # Step 2: Detect parking slots
        slots = self.slot_detector.detect(bev)              # List[ParkingSlot]
        
        # Step 3: Update occupancy from USS
        self.occupancy_grid.update(uss_readings)
        free_slots = [s for s in slots 
                      if self.occupancy_grid.is_free(s.center)]
        
        # Step 4: Plan path to best slot
        if free_slots:
            target = min(free_slots, key=lambda s: s.distance_from_vehicle)
            path   = self.path_planner.plan(self.current_pose, target.entry_pose)
            cmd    = self.controller.compute(self.current_pose, path)
        else:
            cmd = ParkingCommand(action='SEARCH')
        
        return cmd
```

### Calibration Challenge
Surround-view cameras require accurate extrinsic calibration for BEV. Method: checkerboard calibration routine at production line; max allowed reprojection error: 1.5 pixels; automated calibration check on each boot (uses known parking lot lines as reference).

### Performance
- Slot detection AP: 94% (marked slots, 91% (unmarked)
- Path success rate: 97.3% on standard slots, 89% on tight slots (< 2.5m width)
- Speed: 5kph max, USS hard-stop at 15cm

---

## PROJECT 3: ACC System — CAN Bus Integration

### Integration Stack
```
[Radar ECU] → CAN FD (Track data) → [ADAS Domain Controller]
[Camera ECU] → Ethernet (Detections) → [ADAS Domain Controller]
[ADAS DC] → CAN (ACC command) → [EPS/ABS ECU] → [Vehicle]
```

### Debugging: ACC Ghost Braking
**Symptom:** ACC applying mild braking (−1.5 m/s²) on open highway with no vehicles.  
**Investigation:** Enabled full trace log; discovered Camera_ECU sending phantom object at range = 82m, confidence = 0.71 at specific GPS coordinates (bridge overpass).  
**Root cause:** Trained detector not exposed to bridge/overpass scenarios → false detection on bridge deck texture.  
**Fix:** Collected 500 bridge frames; added to training set with null-label (no pedestrian, no vehicle); ACC software added static map zone filter (reduce confidence of detections in overpass GPS zones by 0.3).  
**Validation:** 50 bridge passes with ACC active → 0 ghost braking events.

---

## PROJECT 4: Lane Departure Warning — Field Calibration

### Problem
LDW activating inside roundabouts → user complaints.  
Root cause: lane model fitting broken arc to roundabout markings → model detecting artificial departure.

### Solution
```python
def is_roundabout_scenario(lane_curvature: float, 
                             map_road_type: str) -> bool:
    """Suppress LDW in roundabouts."""
    HIGH_CURVATURE_THRESH = 1/20.0  # 20m radius
    return (abs(lane_curvature) > HIGH_CURVATURE_THRESH or
            map_road_type == 'ROUNDABOUT')

# In LDW state machine:
if is_roundabout_scenario(current_lane.curvature, hd_map.road_type):
    lka_state = LKAState.MONITORING  # Don't activate steering
```

---

## PROJECT 5: HIL Regression Suite — 200 Test Scenarios

### Setup
- Vector VT System (hardware I/O)
- CANoe 17 simulation
- CARLA scenario generator → CAN signal replay
- Jenkins CI: nightly runs

### Test Categories
| Category | Count | Pass Criteria |
|----------|-------|--------------|
| AEB CCRs/CCRm | 40 | AEB active within 600ms |
| AEB Pedestrian | 30 | AEB active within 500ms |
| ACC follow | 25 | Gap error < 5m over scenario |
| LKA straight | 20 | Lateral error < 0.3m |
| LKA curved | 15 | Lateral error < 0.5m |
| Sensor fault injection | 40 | Correct DTC generated |
| False positive (bridges, rain) | 30 | No spurious AEB |
| **Total** | **200** | **95% pass rate required** |

---

## Interview Q&A

### L1
**Q: What is the most important metric when validating a pedestrian detector for AEB?**  
A: Recall (sensitivity) at the relevant confidence threshold. Missing a pedestrian (false negative) is more dangerous than a false alarm (false positive). For AEB production gate: pedestrian recall > 95% at confidence threshold = 0.5, evaluated on night + partial occlusion test set (not just average conditions). Secondary: false positive rate < 2% (too many false alarms → driver distrust and disabling).

### L2
**Q: Walk through how you would debug an AEB false positive in a production vehicle.**  
A: (1) Retrieve CAN log from event: camera detections, radar tracks, ADAS commands; (2) Check Camera_ECU: did camera send a detection at the time? What class, confidence, range? (3) Check Radar_ECU: was there a corresponding track? If radar saw nothing but camera triggered AEB → single-sensor activation; (4) Replay in vSignalyzer: reconstruct scene timeline; (5) If camera false detection: identify frame from log → identify scene type (bridge, overhead sign, wet road reflection); (6) Fix: update training data; add ODD suppression logic; increase fusion gate (require both sensors).

### L3
**Q: How would you structure a 6-month programme to take a perception model from research to production?**  
A: Month 1: Requirements and baseline — ASIL analysis, OEM acceptance criteria, baseline model selection, sensor configuration finalised. Month 2: Data engineering — audit training data, identify gaps (night, weather, regional), collect/purchase targeted data, setup annotation pipeline. Month 3: Model development — architecture finalization (validated on representative hardware), training pipeline, first accuracy gate on internal test set. Month 4: ECU integration — hardware bring-up, TIDL/TensorRT deployment, latency optimisation, E2E test with real ECU. Month 5: System integration and HIL — integration with ACC/AEB functions, HIL regression suite (200+ tests), DTC/fault handling. Month 6: Physical validation — track tests (Euro NCAP), field evaluation (10k km), functional safety sign-off, PPAP (production part approval). Total: 6 months typical for Tier-1 supplier new function.
