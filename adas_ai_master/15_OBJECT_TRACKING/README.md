# 15 — Object Tracking for ADAS

## Overview
Multi-object tracking (MOT) bridges detection frames into persistent object identities. Critical for ACC target selection, AEB threat assessment, and blind-spot monitoring. Covers SORT, ByteTrack, DeepSORT, and ADAS-specific production considerations.

---

## 1. Why Tracking Matters for ADAS

| ADAS Function | Why Tracking is Needed |
|--------------|----------------------|
| ACC | Maintain consistent target ID across frames; reject false detections |
| AEB | Predict collision trajectory — needs velocity over time |
| LCA (Lane Change Assist) | Track approaching vehicles in blind spot for 2-3 seconds |
| Pedestrian AEB | Track pedestrians across frames, predict crossing trajectory |
| Overtaking | Classify oncoming vehicle speed via tracked velocity history |

**Without tracking:** Each frame produces independent detections → no velocity → no TTC → AEB cannot work.

---

## 2. Tracker Comparison

| Tracker | Method | Re-ID | Speed | Notes |
|---------|--------|-------|-------|-------|
| SORT | IoU + Kalman | No | <0.5ms | Fast, fails in crowds |
| Deep SORT | IoU + ReID + Kalman | CNN (128-dim) | ~2ms | Better re-association |
| ByteTrack | IoU (high+low) + Kalman | No | <0.5ms | Best recall, simple |
| OC-SORT | IoU + velocity | No | ~1ms | Better after occlusion |
| StrongSORT | IoU + ReID + ECC | CNN | ~3ms | State-of-art 2022 |

**ADAS production choice:** ByteTrack (no ReID CNN → ECU-friendly) + EMA gallery for lost track recovery.

---

## 3. Track Lifecycle

```
New Detection
     │
     ▼
TENTATIVE (hits=1,2)
     │ hits >= min_hits (3)
     ▼
CONFIRMED ──── missed frames ──→ COASTED ──── misses > max ──→ DELETED
     ▲                                │
     │         re-detected ◄──────────┘
     └──────────────────────────────────
```

---

## 4. ByteTrack Innovation

Standard SORT: only uses detections with confidence > threshold (e.g., 0.5). Misses objects that are partially occluded (score 0.3-0.5).

ByteTrack: two-stage matching:
1. Match high-confidence dets (score ≥ 0.6) → all active tracks
2. Match low-confidence dets (0.1 ≤ score < 0.6) → unmatched tracks from step 1

Result: 2-3% MOTA improvement on MOT17/20 benchmarks, especially in crowded scenes.

---

## 5. Kalman Filter State for Bounding Box

State vector: $[c_x, c_y, w, h, \dot{c}_x, \dot{c}_y, \dot{w}, \dot{h}]$

```
x = [cx, cy, w, h, vcx, vcy, vw, vh]^T

Transition F (dt=1 frame):
[1 0 0 0 | 1 0 0 0]   cx  += vcx
[0 1 0 0 | 0 1 0 0]   cy  += vcy
[0 0 1 0 | 0 0 1 0]   w   += vw
[0 0 0 1 | 0 0 0 1]   h   += vh
[0 0 0 0 | 1 0 0 0]   vcx = const
[0 0 0 0 | 0 1 0 0]   vcy = const
[0 0 0 0 | 0 0 1 0]   vw  = const
[0 0 0 0 | 0 0 0 1]   vh  = const

Measurement H (observe position+size only):
[1 0 0 0 | 0 0 0 0]
[0 1 0 0 | 0 0 0 0]
[0 0 1 0 | 0 0 0 0]
[0 0 0 1 | 0 0 0 0]
```

---

## 6. Velocity Estimation from Tracks

```python
import numpy as np

def estimate_velocity_mps(track_state: np.ndarray,
                           pixels_per_metre: float = 20.0,
                           dt: float = 0.033) -> tuple:
    """Extract real-world velocity from Kalman state.
    
    track_state: [cx, cy, w, h, vcx, vcy, vw, vh] (pixels, pixels/frame)
    pixels_per_metre: from camera calibration / IPM
    dt: frame period (0.033s @ 30fps)
    
    Returns: (vx_mps, vy_mps) longitudinal + lateral velocity in m/s"""
    vcx_pxf = track_state[4]   # pixels per frame
    vcy_pxf = track_state[5]
    
    # Convert: px/frame → m/s
    vx_mps = vcx_pxf / pixels_per_metre / dt
    vy_mps = vcy_pxf / pixels_per_metre / dt
    return vx_mps, vy_mps

def compute_ttc(ego_vx_mps: float, target_vx_mps: float,
                 range_m: float) -> float:
    """Time-to-Collision (TTC) assuming constant velocity.
    Positive TTC = collision ahead, negative = separating."""
    closing_speed = ego_vx_mps - target_vx_mps
    if closing_speed <= 0.1:
        return float('inf')
    return range_m / closing_speed
```

---

## 7. ID Switching and Occlusion

**ID switch** = same physical object assigned different track IDs after occlusion. Degrades AEB consistency.

**Mitigation strategies:**
1. **Coasting**: Kalman prediction keeps track alive during short occlusions (max_misses = 30 frames @ 30fps = 1s)
2. **ReID gallery**: Store 128-dim appearance embedding; on re-detection, compare cosine distance
3. **IoU expansion during occlusion**: Temporarily increase matching IoU threshold to 0.1 to recover coasted tracks
4. **Kalman velocity gate**: Reject matches where predicted position vs detection > 3σ (Mahalanobis distance)

---

## 8. ADAS-Specific Considerations

### AEB Target Lock-on
```python
# ACC/AEB requires ONE confirmed target in ego lane
# Multi-object tracker provides all tracks; lane assignment needed

def find_ego_lane_target(tracks: list, 
                          lane_left_x: float,
                          lane_right_x: float,
                          min_range: float = 3.0,
                          max_range: float = 150.0) -> int:
    """Select the closest confirmed track within the ego lane.
    Returns track_id of ACC target, -1 if no target."""
    best_id, best_range = -1, float('inf')
    for t in tracks:
        cx = (t.bbox.x1 + t.bbox.x2) / 2
        if lane_left_x < cx < lane_right_x:
            # Estimate range from bounding box height (calibrated)
            # In production: use radar range + camera confirmation
            range_est = 5.0 / (t.bbox.h / 720)  # Rough: 5m target at 720px/h
            if min_range < range_est < max_range and range_est < best_range:
                best_range = range_est
                best_id    = t.track_id
    return best_id
```

---

## 9. Interview Q&A

### L1
**Q: What is an ID switch in object tracking and why does it matter for ADAS?**  
A: An ID switch occurs when the tracker assigns a new ID to an object that was previously tracked under a different ID, typically after occlusion. For ADAS: ACC target selection uses the target track ID to maintain smooth following. If the target switches ID after passing under a bridge (1s occlusion), the ACC system might lose the target or briefly select the wrong vehicle. ByteTrack's low-confidence matching specifically reduces ID switches by recovering tracks before they expire.

### L2
**Q: Compare IoU-based association vs appearance-based (ReID) for ADAS tracking.**  
A: IoU: fast (~0.1ms), no extra CNN, works well when objects are spatially separated. Fails when objects overlap (pedestrian crossing in front of car) or during occlusion (object disappears then reappears displaced). ReID: requires dedicated CNN (~1-2ms), but matches based on visual appearance — survives occlusions up to seconds. For ECU-constrained ADAS (20ms budget), IoU-only (ByteTrack) is preferred for ACC/AEB. ReID gallery (AppearanceTracker) is added as second-stage for parking manoeuvres or low-speed crowded scenarios where occlusions are frequent.

### L3
**Q: Design a production multi-object tracker for an automotive ASIL-B AEB system running at 30fps on a TDA4VM.**  
A: (1) **Tracker design**: ByteTrack (IoU matching, no ReID) — pure ARM C code, <0.3ms. (2) **State**: 8-state Kalman [cx, cy, w, h, vcx, vcy, vw, vh]; measurement from camera detections. (3) **Temporal alignment**: Camera at 30Hz, tracker ticks at 30Hz. Radar at 20Hz asynchronously updates range via separate Kalman. (4) **Track lifecycle**: min_hits=3 (100ms), max_misses=30 (1s). TENTATIVE tracks never output to AEB. (5) **Target selection**: in-lane tracks sorted by range; closest = ACC/AEB target. Target ID stored in AUTOSAR SWC as signal; change of target ID logged as DTC for diagnostic. (6) **ASIL-B**: tracker module monitored via E2E library checksum on output; staleness counter (if tracker output > 35ms old, raise safe state); dual-core lockstep on Cortex-R5F validates tracker determinism.

---

## Files
- [object_tracking.py](object_tracking.py) — ByteTracker, KalmanBoxTracker, AppearanceTracker, TTC estimation
