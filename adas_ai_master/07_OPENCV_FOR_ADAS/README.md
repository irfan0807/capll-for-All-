# 07 — OpenCV for ADAS

## Overview
Production OpenCV usage: camera capture pipelines, image preprocessing, classical lane detection, background subtraction, DNN inference module, and video annotation tools for automotive applications.

---

## 1. OpenCV in the ADAS Stack

```
┌──────────────────────────────────────────────────────────────────┐
│                      ADAS Camera Pipeline                        │
├──────────────────────────────────────────────────────────────────┤
│  V4L2 / CSI Camera  →  cv2.VideoCapture (GStreamer on Jetson)    │
│  Undistortion LUT   →  cv2.remap() (3-5× faster than undistort) │
│  ISP                →  White balance, gamma (OpenCV or ISP HW)   │
│  Resize             →  cv2.resize() → 640×384 for NN input       │
│  BGR→RGB            →  cv2.cvtColor()                            │
│  DNN Inference      →  cv2.dnn.readNetFromONNX() + forward()     │
│  Post-processing    →  NMS, contour detection, annotation        │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Camera Capture — Latency Optimisation

### OpenCV default: 3-5 frame buffer lag
```python
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # CRITICAL: reduce to 1 frame
# Without this: you are processing frames that are 100-150ms old
```

### Jetson GStreamer pipeline (hardware-accelerated):
```
nvarguscamerasrc → NvJPEG decode → NvVIC ISP → NvVidConv → BGR
```
Advantage: ISP processing on dedicated HW (no CPU load), <5ms from capture to BGR frame.

---

## 3. Undistortion Performance

### Comparison at 1280×720:
| Method | Time | Notes |
|--------|------|-------|
| `cv2.undistort()` | 15-25ms | Direct computation |
| `cv2.remap()` with precomputed LUT | 3-5ms | **Production standard** |
| Hardware ISP undistortion | <1ms | Available on TDA4VM, NVIDIA ISP |

```python
# Compute LUT once at startup:
map1, map2 = cv2.initUndistortRectifyMap(K, dist, None, new_K, (w,h), cv2.CV_16SC2)

# Use in every frame:
undistorted = cv2.remap(frame, map1, map2, cv2.INTER_LINEAR)  # 3-5ms
```

---

## 4. Canny Edge Detection Parameters

```python
edges = cv2.Canny(blurred, threshold1=50, threshold2=150)
# threshold1: below → definitely not edge
# threshold2: above → definitely edge
# Between: edge only if connected to strong edge (hysteresis)

# Rule of thumb: threshold2 / threshold1 = 2-3
# For lane markings on asphalt: threshold1=40, threshold2=120
# For high-contrast road: threshold1=80, threshold2=200
```

---

## 5. Hough Transform for Lane Lines

```python
lines = cv2.HoughLinesP(
    edges,
    rho=1,              # Distance resolution (pixels)
    theta=np.pi/180,    # Angle resolution (1 degree)
    threshold=50,       # Minimum vote count to accept line
    minLineLength=50,   # Reject short fragments (<50px)
    maxLineGap=150      # Bridge gaps up to 150px (dashed lines)
)
```

**Why Hough fails in production:**
- Shadows cast line-shaped edges that confuse Hough
- Worn lane markings have low contrast → missed
- Construction zones: multiple overlapping lines
- Night driving: headlight reflections on wet road

**ADAS solution:** Use Hough + CNN ensemble — Hough for interpretability, CNN for robustness. If CNN confidence > 0.8, trust CNN. Otherwise, validate against Hough.

---

## 6. Background Subtraction for Moving Objects

```python
# MOG2 (Gaussian Mixture Model)
bg_sub = cv2.createBackgroundSubtractorMOG2(
    history=500,          # Frames to model background
    varThreshold=16,      # Sensitivity (lower = more sensitive)
    detectShadows=True    # Mark shadows as grey (127) not white (255)
)

# KNN (K-Nearest Neighbours) — more robust to illumination changes
bg_sub = cv2.createBackgroundSubtractorKNN(
    history=500, dist2Threshold=400.0, detectShadows=True
)
```

**Automotive application:** Parking sensors — detect slow-moving or stationary obstacles in parking assist camera (30fps update, vehicle <10kph).

**Limitation:** Not suitable for >30kph — camera ego-motion dominates over object motion.

---

## 7. OpenCV DNN Module Performance

### Backend/target combinations:
| Backend | Target | Device | Typical Latency (YOLOv5s) |
|---------|--------|--------|--------------------------|
| OPENCV | CPU | x86 Intel | 80-150ms |
| OPENCV | CPU | ARM A72 | 300-500ms |
| OPENCV | OPENCL_FP16 | Mali GPU | 30-60ms |
| CUDA | CUDA_FP16 | NVIDIA Jetson | 5-15ms |

```python
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA_FP16)
```

### Profiling layers:
```python
net.enableProfiling()
output = net.forward()
retval, timings = net.getPerfProfile()
print(f"Total time: {retval * 1e-3:.2f}ms")
```

---

## 8. Video Recording for Dataset Collection

```python
# Production: record raw camera frames for dataset collection
fourcc = cv2.VideoWriter_fourcc(*'MJPG')   # MJPEG: good compression/quality ratio
# For lossless (labelling ground truth): use HFYU or PNG sequence
writer = cv2.VideoWriter(
    'collection_20240115_highway.avi',
    fourcc, 30.0, (1280, 720)
)

while True:
    ret, frame, fps = camera.read()
    writer.write(frame)
    # Also save CAN bus data (vehicle speed, yaw) with matching timestamp
    
writer.release()
```

---

## 9. Real-Time Performance Rules

| Rule | Reason |
|------|--------|
| Use `cv2.remap()` not `cv2.undistort()` | 5× faster |
| Use `INTER_LINEAR` not `INTER_CUBIC` for resize | 3× faster, visually identical for NN input |
| Process in-place when possible: `cv2.cvtColor(src, dst, ...)` | Avoids allocation |
| Profile with `net.getPerfProfile()` | Identifies bottleneck layers |
| Set `CAP_PROP_BUFFERSIZE = 1` | Eliminates 100ms+ latency lag |
| Avoid Python loops over pixel arrays | Use NumPy or OpenCV functions |
| Pre-allocate output buffers | Use `dst=` parameter in OpenCV calls |

---

## 10. Interview Q&A

### L1
**Q: What is the difference between `cv2.Canny()` threshold1 and threshold2?**  
A: Canny uses hysteresis thresholding. Pixels with gradient magnitude > threshold2 are definitely edges. Pixels between threshold1 and threshold2 are edges only if they connect to a strong edge. Pixels below threshold1 are discarded. Ratio 1:3 is typical (e.g., 50:150). Lower values detect more edges including noise; higher values miss faint lane markings.

**Q: Why set `CAP_PROP_BUFFERSIZE = 1` for ADAS?**  
A: OpenCV's default buffer stores 3-5 frames, so the frame you process may be 100-150ms old. In ADAS at 60kph, the vehicle moves 1-2.5m in that time — enough to miss an AEB trigger. Setting buffer to 1 ensures you process the most recent frame.

### L2
**Q: When would you use background subtraction (MOG2) vs deep learning for vehicle detection?**  
A: MOG2 for low-speed scenarios (parking assist, urban <20kph) on CPU-only ECUs. No GPU required, deterministic behavior, <5ms. Deep learning for highway speeds where ego-motion dominates background model, at night/rain, and for accurate bounding boxes and class labels. Many production systems use both: MOG2 triggers initial detection, CNN confirms and classifies.

**Q: What is `blobFromImage` doing, and why do the parameters matter?**  
A: `blobFromImage` converts a BGR image to a 4D NCHW float32 blob: (1) scales to float and multiplies by `scalefactor` (1/255 = normalise to [0,1]); (2) resizes to model input `size`; (3) subtracts `mean` values per channel; (4) swaps B/R channels if `swapRB=True`. The mean values must exactly match what was used during model training (ImageNet mean = [0.485×255, 0.456×255, 0.406×255]). A mismatch causes significant accuracy degradation.

### L3
**Q: How would you reduce total camera-to-decision latency from 120ms to 30ms?**  
A: Attack each stage: (1) Camera buffer: `CAP_PROP_BUFFERSIZE=1` → -50ms; (2) Undistortion: `remap()` with LUT → -15ms; (3) GPU inference: TensorRT FP16 instead of cv2.dnn CPU → -40ms; (4) Async pipeline: capture thread fills ring buffer while inference thread processes previous frame → parallelise 30ms capture + 15ms inference; (5) Frame resolution: reduce from 1080p to 720p with same NN input size → less copy overhead. Combined: 120ms → 25-35ms achievable.

---

## Files
- [opencv_adas.py](opencv_adas.py) — Camera capture, Hough detection, background subtraction, DNN inference, annotation
