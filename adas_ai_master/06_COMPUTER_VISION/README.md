# 06 — Computer Vision for ADAS

## Overview
Camera geometry, perspective transforms, optical flow, stereo depth, and image quality assessment. Foundation for all camera-based ADAS perception systems.

---

## 1. Pinhole Camera Model

The relationship between a 3D world point $\mathbf{P} = [X, Y, Z]^T$ and its 2D image projection $\mathbf{p} = [u, v]^T$:

$$\begin{bmatrix} u \\ v \\ 1 \end{bmatrix} = \frac{1}{Z} \begin{bmatrix} f_x & 0 & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix} \begin{bmatrix} R & t \end{bmatrix} \begin{bmatrix} X \\ Y \\ Z \\ 1 \end{bmatrix}$$

**Parameters (calibrated per camera unit):**
- $f_x, f_y$: focal lengths in pixels (~1000-1500px for automotive cameras)
- $c_x, c_y$: principal point (usually near image centre ±5px)
- $R, t$: extrinsic rotation and translation (camera pose in world)

**Why calibration matters in ADAS:**  
A 1% focal length error at 50m range = 0.5m position error. AEB activation distance tolerance is ±0.2m. Therefore camera calibration must achieve sub-pixel accuracy (reprojection error < 0.5px).

---

## 2. Lens Distortion Correction

Real lenses introduce radial and tangential distortion:

$$x_{distorted} = x(1 + k_1r^2 + k_2r^4 + k_3r^6) + 2p_1xy + p_2(r^2 + 2x^2)$$

```python
# Calibrate using 10-20 checkerboard images
ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
    objpoints, imgpoints, gray.shape[::-1], None, None)

# Undistort at runtime
undistorted = cv2.undistort(frame, K, dist)
```

**Automotive requirement:** Undistortion must run at <2ms for 720p. Use `cv2.initUndistortRectifyMap()` + `cv2.remap()` for pre-computed LUT (lookup table) approach — 5-10× faster than `cv2.undistort()`.

---

## 3. Inverse Perspective Mapping (IPM / BEV)

IPM transforms the front-facing camera view into a top-down (bird's-eye) view under the flat ground assumption.

**Transform derivation:**
1. Select 4 source points (trapezoid in road plane)
2. Define 4 destination points (rectangle in BEV)
3. Compute homography: `M = cv2.getPerspectiveTransform(src, dst)`
4. Apply: `bev = cv2.warpPerspective(frame, M, (bev_w, bev_h))`

**Metric calibration:**
```
BEV pixel → real world:
  x_metric = (px - bev_w/2) × (total_lateral_m / bev_w)
  y_metric = (bev_h - py) × (total_forward_m / bev_h)
```

**Limitations and modern solutions:**
- IPM assumes flat road → fails on inclines >3° (detected as lateral drift)
- Tesla FSD replaces IPM with learned BEV (transformer attention across multiple camera views)
- BEVFormer: position encoding + deformable attention → camera-to-BEV without ground assumption

---

## 4. Optical Flow — Ego-motion Estimation

**Lucas-Kanade sparse optical flow:**
1. Detect Shi-Tomasi corners in previous frame
2. Track corner positions in current frame using local window matching
3. Median of tracked motions = ego vehicle motion
4. Outliers (motions inconsistent with ego) = moving objects

**Applications in ADAS:**
| Application | How |
|------------|-----|
| Camera fault detection | Zero optical flow = frozen frame (DTC trigger) |
| Moving object segmentation | Points with flow ≠ ego-motion = vehicles/pedestrians |
| Visual odometry (GPS backup) | Integrate flow over time |
| Lane departure warning | Lateral ego-motion from optical flow |

---

## 5. Stereo Vision Depth Estimation

**Depth from disparity:**
$$Z = \frac{f \times B}{d}$$
- $Z$: depth (metres)
- $f$: focal length (pixels)  
- $B$: stereo baseline (metres, typically 10-20cm)
- $d$: disparity (pixels, difference in matched point x-coordinates)

**Depth accuracy vs range (B=12cm, f=1050px):**
| Range (m) | Disparity (px) | Depth error ±1px |
|-----------|---------------|-----------------|
| 10m | 12.6px | ±0.8m |
| 30m | 4.2px | ±7.1m |
| 50m | 2.5px | ±20m |

**Conclusion:** Stereo vision is reliable to ~30-40m. Beyond that, radar or LiDAR provides better depth accuracy.

---

## 6. Camera Quality Monitoring (ISO 26262)

Safety-critical ADAS must detect camera degradation before it affects function:

| Fault | Detection Method | Trigger DTC |
|-------|-----------------|-------------|
| Lens dirt / occlusion | Uniform region detection | Yes — disable LKA |
| Blur / defocus | Laplacian variance < 100 | Yes |
| Brightness loss (night) | Mean brightness < 40 | Warning only |
| Overexposure | Mean brightness > 220 | Warning only |
| Fog / low contrast | Std deviation < 20 | Yes — disable AEB |
| Frozen frame | Zero optical flow | Yes — safety stop |

---

## 7. Camera-Radar Extrinsic Calibration

```python
# Find camera-radar extrinsic: T_radar_to_camera
# Method: target with both radar reflector + visual marker

# Step 1: Detect target in camera (corner detection)
cam_pts = detect_calibration_target_in_camera(frames)  # (N, 2) image pts

# Step 2: Get radar detection of same target
radar_pts = radar_detections_of_target(frames)          # (N, 3) XYZ in radar frame

# Step 3: Solve PnP (3D-2D correspondence)
ret, rvec, tvec = cv2.solvePnP(radar_pts, cam_pts, K, dist)
R, _ = cv2.Rodrigues(rvec)

# Result: T_radar_to_camera = [R | t]
# Use this to project radar detections onto camera image for fusion
```

---

## 8. Interview Q&A

### L1
**Q: What does a camera intrinsic matrix K represent?**  
A: K maps 3D camera-frame coordinates to 2D image pixels. It encodes focal lengths (f_x, f_y) which determine magnification, and principal point (c_x, c_y) which is where the optical axis hits the image plane. K is fixed for a given lens/sensor combination and determined during factory calibration.

**Q: Why must you undistort images before running ADAS algorithms?**  
A: Lens distortion makes straight lines appear curved. Lane detection algorithms fitting polynomial curves will get incorrect lane position estimates. Camera-radar calibration assumes straight-line projection — distorted images break this assumption. Undistortion corrects pixel positions so all downstream algorithms work in a valid pinhole model.

### L2
**Q: What are the limitations of IPM (Inverse Perspective Mapping) for lane detection?**  
A: (1) Flat ground assumption — fails on hills, ramps, speed bumps; (2) Moving objects get distorted and stretched in BEV; (3) Far-range lanes become very narrow in BEV (limited resolution); (4) Can't handle camera pitch changes (vibration on rough roads). Modern systems replace IPM with learned BEV transformations that handle non-planar scenes.

**Q: How do you detect a frozen camera frame in production?**  
A: Three methods: (1) Frame difference — if `|frame_t - frame_{t-1}| < threshold` for 3+ consecutive frames, flag as frozen; (2) Optical flow — if tracked feature motion is exactly 0 while vehicle is moving, trigger DTC; (3) Hardware-level: V4L2 driver timestamp monitoring — missing frame timestamps = buffer stall.

### L3
**Q: Describe how you would implement camera-radar extrinsic calibration in a production line.**  
A: Use an L-shaped calibration target with both a trihedral radar reflector and checkerboard pattern. The production line fixture holds the target at a known position. Camera: detect checkerboard corners, solve PnP to get target pose in camera frame. Radar: cluster 3D detections around the reflector, get centroid in radar frame. With multiple target positions (minimum 4), solve least-squares for the 6-DOF transform T_cam_radar. Validate: project radar detections onto camera — RMS reprojection error must be < 5px. Store calibration parameters in ECU NVM, re-run at every service interval.

---

## Files
- [cv_pipeline.py](cv_pipeline.py) — Camera geometry, BEV, optical flow, stereo depth, quality assessment
