# 41 — Debugging Scenarios for ADAS AI Systems

## Overview
Real-world debugging methodology and scenario catalogue for ADAS AI systems: false positives, missed detections, TTC errors, sensor fusion bugs, ECU deployment issues, and CI failures.

---

## 1. Debug Methodology

```
OBSERVE symptom (metric regression, field report, CI failure)
    ↓
ISOLATE (which module: sensor? model? fusion? planning? CAN?)
    ↓
REPRODUCE (minimal reproducible case)
    ↓
ANALYSE (logs, feature maps, activations, CAN traces)
    ↓
HYPOTHESISE root cause
    ↓
VERIFY (test hypothesis on held-out data)
    ↓
FIX → VALIDATE → PREVENT (add regression test)
```

---

## 2. Scenario Catalogue

### Bug 01: Pedestrian Missed at Night (False Negative)

**Symptom:** Night AP dropped from 84% to 71% after new firmware release.

**Investigation steps:**
```python
# Step 1: Compare model version outputs on same test set
def compare_model_versions(test_frames: list, 
                            model_v1, model_v2) -> dict:
    diffs = []
    for frame in test_frames:
        out_v1 = model_v1.infer(frame)
        out_v2 = model_v2.infer(frame)
        iou    = compute_iou(out_v1.boxes, out_v2.boxes)
        if iou < 0.5:    # Significantly different outputs
            diffs.append({'frame': frame.id,
                          'v1_conf': out_v1.max_conf,
                          'v2_conf': out_v2.max_conf})
    return diffs
```

**Root cause found:** ISP pipeline firmware change altered gamma correction for night frames — mean pixel value shifted from 85 to 102. Training data had mean 85 → distribution shift.

**Fix:** Updated preprocessing normalisation to use per-sensor-firmware running stats; added ISP firmware version check on boot.

---

### Bug 02: ACC Ghost Braking (False Positive)

**Symptom:** ACC occasionally applies −1.2 m/s² on clear highway, driver-reported 3 incidents.

**Debug via CAN log replay:**
```python
import struct

def parse_can_log(log_path: str, msg_id: int = 0x3E9) -> list:
    """Parse CANalyzer .asc log for specific message ID."""
    events = []
    with open(log_path) as f:
        for line in f:
            if f'  {hex(msg_id)} ' in line.lower() or f' {msg_id} ' in line:
                parts = line.split()
                ts     = float(parts[0])
                data   = bytes.fromhex(''.join(parts[7:15]))
                range_m      = struct.unpack_from('>H', data, 0)[0] * 0.1
                range_rate   = struct.unpack_from('>h', data, 2)[0] * 0.05
                confidence   = struct.unpack_from('>B', data, 4)[0] / 255.0
                events.append({'ts': ts, 'range': range_m,
                                'range_rate': range_rate, 'conf': confidence})
    return events

# Found: camera_track at range=67m, confidence=0.71 appearing 4s before braking
# Radar: NO corresponding track at same range
# Conclusion: camera false positive, not gated by radar
```

**Root cause:** ACC triggered on camera-only track. Radar gating condition had regression: `if radar_conf > 0.8` (was 0.6) → radar gate too strict → camera passed alone.

**Fix:** Restored radar gate to 0.6; added unit test on gate threshold.

---

### Bug 03: LiDAR-Camera Fusion Misalignment

**Symptom:** Fused track has 40cm systematic lateral offset vs ground truth.

**Debug: check extrinsic calibration:**
```python
import numpy as np

def project_lidar_to_image(lidar_pts: np.ndarray,
                            T_lidar_cam: np.ndarray,
                            K: np.ndarray) -> np.ndarray:
    """Project LiDAR points to camera pixel space."""
    pts_cam = T_lidar_cam[:3,:3] @ lidar_pts.T + T_lidar_cam[:3,3:]
    valid   = pts_cam[2] > 0.1          # In front of camera
    pts_cam = pts_cam[:, valid]
    uv      = K @ pts_cam
    uv      = uv[:2] / uv[2]            # Normalise
    return uv.T

# Overlaid LiDAR points on camera → systematic 40cm right shift
# Check calibration file timestamp → 3 weeks old
# Vehicle had minor front impact → LiDAR mount shifted 0.8° yaw
```

**Fix:** Automated online calibration health check (compare LiDAR points on lane markings vs camera lane estimates → report offset daily); trigger recalibration if >2cm drift detected.

---

### Bug 04: TensorRT Engine Accuracy Drop

**Symptom:** INT8 TRT engine has 6% lower pedestrian AP than FP16.

**Debug: calibration layer-by-layer analysis:**
```python
import tensorrt as trt

def analyse_layer_precision(engine_path: str):
    """List precision of each layer in TRT engine."""
    logger  = trt.Logger(trt.Logger.WARNING)
    runtime = trt.Runtime(logger)
    with open(engine_path, 'rb') as f:
        engine = runtime.deserialize_cuda_engine(f.read())
    
    for i in range(engine.num_layers):
        layer = engine.get_layer(i)
        print(f"Layer {i:3d} | {layer.name:40s} | "
              f"precision={engine.get_binding_dtype(i)}")

# Found: detection head output layer forced to INT8 → pedestrian score precision loss
# Small pedestrians: score in 0.3-0.4 range → INT8 rounds incorrectly
```

**Fix:** Set detection head to FP16 (partial precision): `builder_config.set_flag(trt.BuilderFlag.FP16)` for output layers; keep backbone INT8. Net result: +4% pedestrian AP, +0.8ms latency (acceptable).

---

### Bug 05: Kalman Filter Track Swap

**Symptom:** Two vehicles passing each other → tracks swap IDs → ACC lock-on fails.

**Debug: plot track state vectors:**
```python
def visualise_track_swap(tracks_history: dict, t_start: float, t_end: float):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(14,5))
    
    for track_id, history in tracks_history.items():
        times  = [e['t'] for e in history if t_start <= e['t'] <= t_end]
        x_vals = [e['x'] for e in history if t_start <= e['t'] <= t_end]
        y_vals = [e['y'] for e in history if t_start <= e['t'] <= t_end]
        axes[0].plot(times, x_vals, label=f'Track {track_id}')
        axes[1].plot(x_vals, y_vals, label=f'Track {track_id}')
    
    axes[0].set_title('Track X vs Time'); axes[0].legend()
    axes[1].set_title('Track Y vs X (path)'); axes[1].legend()
    plt.tight_layout(); plt.savefig('/tmp/track_swap.png')

# Found: tracks swapped when lateral distance < 1.5m for 3 consecutive frames
# Association gate (Mahalanobis distance) was using only range → not using lateral
```

**Fix:** Changed track association to use full 2D Mahalanobis gate including lateral component; increased innovation gate from chi²=9.21 (1D) to chi²=5.99 (2D, p=0.05).

---

### Bug 06: AUTOSAR DTC Not Raised on Sensor Timeout

**Symptom:** Camera goes offline (unplugged in test); ADAS continues without fault; no DTC logged.

**Debug: check watchdog implementation:**
```cpp
// BUG: Timer never reset on camera message receipt
void CameraMonitor::onCameraMsg(const CameraMsg& msg) {
    // BUG: was not calling resetWatchdog() here
    processDetections(msg.detections);
}

// FIX:
void CameraMonitor::onCameraMsg(const CameraMsg& msg) {
    resetWatchdog();   // Reset 150ms watchdog
    processDetections(msg.detections);
}
```

**Root cause:** Developer added new message handler, forgot to call `resetWatchdog()`. Code review missed it.

**Fix:** Refactored watchdog to use RAII guard — watchdog auto-resets when guard is constructed at start of handler:
```cpp
void CameraMonitor::onCameraMsg(const CameraMsg& msg) {
    WatchdogGuard guard(camera_watchdog_);  // Auto-resets + auto-fails on scope exit without refresh
    processDetections(msg.detections);
}
```

---

## 3. Systematic Debug Checklist

```
ADAS AI Debug Checklist:
[ ] Reproduce on latest codebase (not old branch)
[ ] Check sensor health: all signals arriving? correct rate?
[ ] Verify preprocessing: normalisation correct? resize correct?
[ ] Model: correct ONNX version deployed? MD5 hash match?
[ ] Calibration: extrinsic calibration age < 30 days?
[ ] CAN: E2E counter incrementing? Checksum valid?
[ ] Watchdogs: all sensor watchdogs running? DTC verified?
[ ] Log: full CAN trace + image log captured for reproduction?
[ ] Regression: does existing test suite still pass?
```

---

## Interview Q&A

### L1
**Q: What tools do you use to debug CAN signal issues in ADAS?**  
A: (1) CANalyzer: real-time monitoring, signal decoding via DBC, triggers on signal value/error; (2) vSignalyzer: offline analysis of long recordings, overlay multiple signals, compute statistics; (3) Python cantools library: parse .dbc files, decode .asc or .blf logs offline; (4) Wireshark with SocketCAN plugin: for Automotive Ethernet (SOME/IP analysis). Debug workflow: capture full log during incident → decode with DBC → correlate CAN events with timestamps → identify anomaly.

### L2
**Q: Walk through your approach to debugging a model accuracy regression after a data pipeline update.**  
A: (1) Check preprocessing output: sample 100 frames before/after pipeline change, compute pixel statistics (mean, std, min, max) → has normalisation changed? (2) Check data split: has train/val split changed? Ensure validation set is identical for fair comparison; (3) Check augmentation: has any new augmentation been added? Disable augmentations one by one, retrain to isolate culprit; (4) Check label format: any silent parsing change in label loader? Spot-check 10 samples with visualisation; (5) Check class balance: compute per-class count before/after → any class dropped or heavily undersampled?

### L3
**Q: A production AEB system has 3 customer complaints of unexpected braking in 2 months. How do you structure the investigation?**  
A: (1) Data retrieval: extract EDR (event data recorder) log from each incident — full CAN trace, camera frames, GPS; (2) Classify: are all 3 incidents same scenario type? Same location? Same weather? → determines if systematic or random; (3) Signal replay: replay CAN trace in CANoe → reproduce ADAS command → confirm AEB did activate (vs false customer claim); (4) Root cause tree: for each incident — which sensor triggered? Camera alone? Radar alone? Both? With what confidence? What TTC at trigger? (5) If systematic (e.g., all bridges): map+ODD fix; data collection; model retrain; software patch with gating. (6) If random/unexplained: review for rare edge case; widen negative mining dataset; consider confidence threshold increase for that scenario class; (7) Corrective action: field recall or OTA depending on severity; SOTIF analysis update; add scenario to HIL regression suite.
