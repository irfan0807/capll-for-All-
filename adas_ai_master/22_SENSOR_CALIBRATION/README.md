# 22 — Sensor Calibration

## Overview
Intrinsic and extrinsic calibration for cameras, radar, and LiDAR. Covers camera calibration mathematics, camera-to-radar extrinsic calibration, online recalibration, and production calibration workflow.

---

## 1. Camera Intrinsic Calibration

**Pinhole model:**
$$\begin{bmatrix} u \\ v \\ 1 \end{bmatrix} = K \begin{bmatrix} X/Z \\ Y/Z \\ 1 \end{bmatrix}, \quad K = \begin{bmatrix} f_x & 0 & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix}$$

**Distortion (Brown-Conrady model):**
$$x' = x(1 + k_1r^2 + k_2r^4 + k_3r^6) + 2p_1xy + p_2(r^2+2x^2)$$

**Calibration algorithm (Zhang, 2000):**
1. Capture 15-30 images of checkerboard at varied poses
2. Detect corners with sub-pixel accuracy (`cv2.cornerSubPix`)
3. Solve for K and distortion via homography decomposition
4. Non-linear refinement using Levenberg-Marquardt

```python
import cv2
import numpy as np
from pathlib import Path

def calibrate_camera(image_paths: list[str],
                      board_size: tuple = (9, 6),
                      square_size_m: float = 0.025) -> dict:
    """Standard OpenCV camera calibration.
    
    board_size: (cols-1, rows-1) inner corners
    square_size_m: physical square side length
    
    Returns: {'K': 3×3, 'dist': 1×5, 'rms_px': float}"""
    objp = np.zeros((board_size[0]*board_size[1], 3), np.float32)
    objp[:,:2] = np.mgrid[0:board_size[0], 0:board_size[1]].T.reshape(-1,2)
    objp *= square_size_m
    
    obj_points, img_points = [], []
    img_size = None
    
    for path in image_paths:
        img  = cv2.imread(path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if img_size is None:
            img_size = gray.shape[::-1]
        
        ret, corners = cv2.findChessboardCorners(gray, board_size)
        if ret:
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners = cv2.cornerSubPix(gray, corners, (11,11), (-1,-1), criteria)
            obj_points.append(objp)
            img_points.append(corners)
    
    rms, K, dist, _, _ = cv2.calibrateCamera(
        obj_points, img_points, img_size, None, None)
    return {'K': K, 'dist': dist, 'rms_px': rms}
```

---

## 2. Camera-Radar Extrinsic Calibration

**Goal:** Find $T_{CR}$ — 4×4 rigid transform from radar frame to camera frame.

**Method: Target-based calibration:**
1. Place corner-reflector (high RCS) at known 3D positions visible to both sensors
2. Radar detects reflector: $(r, \theta)$ → world position
3. Camera detects reflector: pixel $(u, v)$ → 3D via known target height
4. Optimise $T_{CR}$ minimising reprojection error

```python
import numpy as np
from scipy.spatial.transform import Rotation

def estimate_extrinsic_radar_camera(radar_pts: np.ndarray,
                                     camera_pts: np.ndarray) -> np.ndarray:
    """Estimate rigid transform T_camera_radar using corresponding points.
    
    radar_pts:  (N, 3) — 3D points in radar frame
    camera_pts: (N, 3) — corresponding 3D points in camera frame
    Returns: 4×4 transformation matrix T (radar → camera)"""
    assert len(radar_pts) >= 4
    
    # Centroid alignment
    c_radar  = radar_pts.mean(axis=0)
    c_camera = camera_pts.mean(axis=0)
    A = radar_pts  - c_radar
    B = camera_pts - c_camera
    
    # SVD for rotation
    H = A.T @ B
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    
    # Correct reflection
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = Vt.T @ U.T
    
    t = c_camera - R @ c_radar
    
    T = np.eye(4)
    T[:3,:3] = R
    T[:3,3]  = t
    return T
```

---

## 3. Online Recalibration

Production vehicles drift out of calibration over time (temperature, vibration, minor collisions). Online recalibration detects and compensates:

**Vanishing point estimation (camera):**
```python
def estimate_vanishing_point_from_lanes(lane_lines: list) -> tuple:
    """Estimate horizon vanishing point from detected lane lines.
    Vanishing point shift = camera pitch/roll change → recalibration signal."""
    intersections = []
    for i in range(len(lane_lines)):
        for j in range(i+1, len(lane_lines)):
            # Line-line intersection
            l1, l2 = lane_lines[i], lane_lines[j]
            # Each line: (x1,y1,x2,y2)
            x1,y1,x2,y2 = l1; x3,y3,x4,y4 = l2
            denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
            if abs(denom) < 1e-6:
                continue
            t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / denom
            ix = x1 + t*(x2-x1)
            iy = y1 + t*(y2-y1)
            intersections.append((ix, iy))
    if not intersections:
        return None, None
    vp = np.mean(intersections, axis=0)
    return float(vp[0]), float(vp[1])
```

---

## 4. Production Calibration Workflow

**EOL (End-of-Line) Calibration — factory:**
1. Vehicle positioned in calibration tunnel with precision targets
2. Automated calibration station runs intrinsic verification + full extrinsic calibration
3. Calibration data written to NVM (non-volatile memory)
4. Reprojection error gate: < 0.5px for camera-to-camera, < 1cm for camera-radar
5. Timestamp + VIN stored with calibration data

**Workshop calibration (replacement sensor):**
1. Technician places targets per OEM guide (3 reflectors at 3m, 5m, 7m)
2. ADAS ECU runs auto-calibration routine via diagnostic service
3. New calibration written to NVM; ECU sends confirmation DTC clear

**Online (operational) calibration:**
1. Running on-board; detects small drift (< ±2°)
2. Applies delta correction without new factory calibration
3. Large drift → DTC P1234 "Camera Calibration Lost" → disable ADAS functions

---

## 5. Interview Q&A

### L1
**Q: What is reprojection error in camera calibration?**  
A: Reprojection error is the distance (in pixels) between a calibration point's actual image position and its projected position using the estimated camera model. It measures calibration quality. For ADAS: RMS reprojection error < 0.5px is required. Errors > 1px indicate significant distortion model mismatch or poor calibration images. Large reprojection error → inaccurate 3D estimates → degraded ADAS performance.

### L2
**Q: How does temperature affect camera calibration in automotive applications?**  
A: Camera lens thermal expansion shifts focal length and principal point. At -40°C to +85°C: focal length can change by ±0.5%, principal point by ±2px for plastic lens mounts (worse than metal). Mitigation: (1) Use invar or metal lens mount (lower thermal expansion); (2) Store calibration at multiple temperatures during EOL; (3) Online temperature-compensated calibration using lookup table (T°C → correction offset); (4) ADAS functions specify maximum calibration error tolerance and reduce accuracy estimates at temperature extremes.

### L3
**Q: Design an online camera-radar calibration monitoring system for a production ADAS ECU.**  
A: (1) Ground truth: When both sensors see the same stationary object (parked car, building corner), compare radar-derived 3D position with camera-derived 3D (depth from radar, projected via T_CR). (2) Error metric: reprojection error = pixel distance between radar point projected onto camera using T_CR vs actual image feature. (3) Kalman filter on calibration delta: state = [Δroll, Δpitch, Δyaw, Δtx, Δty, Δtz], update when stationary objects observed. (4) Thresholds: Δyaw > 1° → soft warning (reduce fusion confidence); Δyaw > 3° → disable fusion + DTC P1566 "Camera-Radar Miscalibration". (5) FMEA: stuck-at-wrong-value failure mode → watchdog checks calibration update frequency; if 100km without any update → assume degradation → log + alert.
