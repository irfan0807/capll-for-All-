"""
06_COMPUTER_VISION — Classical CV Pipeline for ADAS
Camera geometry, image processing, bird's-eye-view projection
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List
from dataclasses import dataclass

# ============================================================================
# 1. CAMERA MODEL & CALIBRATION
# ============================================================================

@dataclass
class CameraIntrinsics:
    """Pinhole camera model with distortion.
    Calibrated using cv2.calibrateCamera() on checkerboard images."""
    fx: float   # Focal length X (pixels)
    fy: float   # Focal length Y (pixels)
    cx: float   # Principal point X (pixels) — usually image centre
    cy: float   # Principal point Y (pixels)
    # Distortion coefficients [k1, k2, p1, p2, k3]
    dist: np.ndarray = None

    def K(self) -> np.ndarray:
        """3×3 intrinsic matrix."""
        return np.array([[self.fx, 0, self.cx],
                         [0, self.fy, self.cy],
                         [0, 0,       1      ]], dtype=np.float64)

# Typical front camera parameters (1280×720, 60° FOV)
FRONT_CAMERA = CameraIntrinsics(
    fx=1050.0, fy=1050.0, cx=640.0, cy=360.0,
    dist=np.array([-0.12, 0.08, 0.001, 0.001, -0.02])
)

def project_3d_to_image(points_3d: np.ndarray,
                          cam: CameraIntrinsics,
                          R: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Project 3D world points to 2D image coordinates.
    points_3d: (N, 3) in world frame
    R: (3, 3) rotation matrix (camera extrinsics)
    t: (3,) translation vector
    Returns: (N, 2) pixel coordinates"""
    # Transform to camera frame
    pts_cam = (R @ points_3d.T).T + t  # (N, 3)
    # Perspective division
    u = cam.fx * pts_cam[:, 0] / pts_cam[:, 2] + cam.cx
    v = cam.fy * pts_cam[:, 1] / pts_cam[:, 2] + cam.cy
    return np.stack([u, v], axis=1)

def undistort_frame(frame: np.ndarray, cam: CameraIntrinsics) -> np.ndarray:
    """Remove radial/tangential distortion from camera image.
    Must run BEFORE any perspective transform or feature matching."""
    h, w = frame.shape[:2]
    new_K, roi = cv2.getOptimalNewCameraMatrix(
        cam.K(), cam.dist, (w, h), alpha=0)
    undistorted = cv2.undistort(frame, cam.K(), cam.dist, None, new_K)
    x, y, rw, rh = roi
    return undistorted[y:y+rh, x:x+rw]

# ============================================================================
# 2. BIRD'S EYE VIEW (IPM — Inverse Perspective Mapping)
# ============================================================================

class BirdsEyeView:
    """Inverse Perspective Mapping: front camera → top-down view.
    Used for: lane detection, free space detection, parking assistance.
    
    Limitation: IPM assumes flat ground plane — fails on hills and ramps.
    Modern ADAS: use learned BEV (Tesla FSD, BEVFormer) instead."""
    
    def __init__(self, img_w: int = 1280, img_h: int = 720,
                 bev_w: int = 400, bev_h: int = 600):
        self.img_w = img_w
        self.img_h = img_h
        self.bev_w = bev_w
        self.bev_h = bev_h
        
        # Source points: trapezoid in front camera image
        # Calibrated for a car with front camera at 1.4m height, 2.5m forward
        self.src = np.float32([
            [200,  720],  # Bottom-left
            [580,  460],  # Top-left
            [700,  460],  # Top-right
            [1100, 720],  # Bottom-right
        ])
        # Destination: rectangle in BEV
        self.dst = np.float32([
            [50,  bev_h],
            [50,  0],
            [bev_w-50, 0],
            [bev_w-50, bev_h],
        ])
        self.M     = cv2.getPerspectiveTransform(self.src, self.dst)
        self.M_inv = cv2.getPerspectiveTransform(self.dst, self.src)
    
    def warp(self, img: np.ndarray) -> np.ndarray:
        """Transform image to bird's-eye view."""
        return cv2.warpPerspective(img, self.M, (self.bev_w, self.bev_h))
    
    def unwarp(self, bev: np.ndarray) -> np.ndarray:
        """Transform BEV back to front camera perspective."""
        return cv2.warpPerspective(bev, self.M_inv, (self.img_w, self.img_h))
    
    def pixel_to_metric(self, px: float, py: float) -> Tuple[float, float]:
        """Convert BEV pixel to real-world metres (ground plane).
        Assumes: bev_h=600px covers 30m forward, bev_w=400px covers 8m lateral."""
        x_m = (px - self.bev_w/2) * (8.0 / self.bev_w)   # lateral
        y_m = (self.bev_h - py) * (30.0 / self.bev_h)     # longitudinal
        return x_m, y_m

# ============================================================================
# 3. OPTICAL FLOW — Ego-motion estimation
# ============================================================================

class OpticalFlowEgoMotion:
    """Lucas-Kanade sparse optical flow for ego-motion estimation.
    Detects corners → tracks across frames → computes homography → extract motion.
    
    Applications:
    - Moving object detection (objects with flow inconsistent with ego-motion)
    - Ego vehicle speed estimation (visual odometry backup)
    - Camera fault detection (no flow = frozen frame)
    """
    
    def __init__(self):
        # Shi-Tomasi corner detector parameters
        self.feature_params = dict(
            maxCorners=200, qualityLevel=0.01,
            minDistance=10, blockSize=7
        )
        # Lucas-Kanade optical flow parameters
        self.lk_params = dict(
            winSize=(21, 21), maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)
        )
        self._prev_frame: Optional[np.ndarray] = None
        self._prev_pts:   Optional[np.ndarray] = None
    
    def update(self, frame_gray: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Process new frame. Returns (prev_pts, curr_pts) if tracked, else None."""
        if self._prev_frame is None:
            self._prev_frame = frame_gray
            self._prev_pts = cv2.goodFeaturesToTrack(frame_gray, mask=None,
                                                      **self.feature_params)
            return None, None
        
        if self._prev_pts is None or len(self._prev_pts) < 10:
            self._prev_pts = cv2.goodFeaturesToTrack(self._prev_frame, mask=None,
                                                      **self.feature_params)
        
        # Track features to new frame
        curr_pts, status, _ = cv2.calcOpticalFlowPyrLK(
            self._prev_frame, frame_gray, self._prev_pts, None, **self.lk_params)
        
        # Filter: only keep successfully tracked points
        if status is None:
            return None, None
        good_prev = self._prev_pts[status == 1]
        good_curr = curr_pts[status == 1]
        
        self._prev_frame = frame_gray.copy()
        # Refresh features every 30 frames
        self._prev_pts = good_curr.reshape(-1, 1, 2)
        
        return good_prev, good_curr
    
    def estimate_translation(self, prev_pts: np.ndarray,
                              curr_pts: np.ndarray) -> Tuple[float, float]:
        """Estimate lateral and longitudinal translation (pixels/frame)."""
        if len(prev_pts) < 8:
            return 0.0, 0.0
        flow = curr_pts - prev_pts
        # Median flow = ego motion (removes moving object outliers)
        tx = float(np.median(flow[:, 0]))
        ty = float(np.median(flow[:, 1]))
        return tx, ty

# ============================================================================
# 4. DEPTH FROM STEREO
# ============================================================================

class StereoDepthEstimator:
    """Stereo disparity to depth map using semi-global block matching (SGBM).
    Used in: Subaru EyeSight, Delphi stereo camera, Continental SVC.
    
    Requires: calibrated stereo pair (left + right camera, known baseline).
    Typical baseline: 10-20cm for ADAS, 30-60cm for trucks."""
    
    def __init__(self, baseline_m: float = 0.12, focal_px: float = 1050.0):
        self.baseline = baseline_m
        self.focal    = focal_px
        
        self.stereo = cv2.StereoSGBM_create(
            minDisparity=0,
            numDisparities=128,    # Must be divisible by 16
            blockSize=5,
            P1=8 * 3 * 5**2,      # Smoothness penalty small disparity changes
            P2=32 * 3 * 5**2,     # Smoothness penalty large disparity changes
            disp12MaxDiff=1,
            uniquenessRatio=10,    # Reject ambiguous matches
            speckleWindowSize=100,
            speckleRange=32,
            preFilterCap=63,
            mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY
        )
    
    def compute_depth(self, left_gray: np.ndarray,
                      right_gray: np.ndarray) -> np.ndarray:
        """Returns depth map in metres. 0.0 = invalid (no disparity)."""
        disparity = self.stereo.compute(left_gray, right_gray).astype(np.float32)
        disparity /= 16.0   # SGBM stores disparity ×16 for sub-pixel precision
        
        # depth = baseline × focal / disparity
        with np.errstate(divide='ignore', invalid='ignore'):
            depth = np.where(disparity > 0,
                             self.baseline * self.focal / disparity,
                             0.0)
        return depth
    
    def depth_to_point_cloud(self, depth_map: np.ndarray,
                              cam: CameraIntrinsics) -> np.ndarray:
        """Convert depth map to 3D point cloud (N, 3) in camera frame."""
        h, w = depth_map.shape
        u, v = np.meshgrid(np.arange(w), np.arange(h))
        
        valid = depth_map > 0
        z = depth_map[valid]
        x = (u[valid] - cam.cx) * z / cam.fx
        y = (v[valid] - cam.cy) * z / cam.fy
        return np.stack([x, y, z], axis=1)

# ============================================================================
# 5. IMAGE QUALITY ASSESSMENT
# ============================================================================

def assess_camera_quality(frame: np.ndarray) -> dict:
    """Assess camera image quality for fault detection.
    Returns quality metrics used to decide if perception is reliable."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape)==3 else frame
    h, w = gray.shape
    
    # Blur detection (Laplacian variance)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    is_blurry = laplacian_var < 100.0  # Threshold tuned empirically
    
    # Brightness
    mean_brightness = float(gray.mean())
    is_dark = mean_brightness < 40.0
    is_overexposed = mean_brightness > 220.0
    
    # Contrast (standard deviation)
    std_brightness = float(gray.std())
    is_low_contrast = std_brightness < 20.0  # Fog/blizzard signature
    
    # Partial occlusion (large uniform region = lens cover / dirt)
    # Check if any quadrant has near-zero variance
    quadrants = [gray[:h//2, :w//2], gray[:h//2, w//2:],
                 gray[h//2:, :w//2], gray[h//2:, w//2:]]
    is_occluded = any(q.std() < 5.0 for q in quadrants)
    
    quality_score = 100
    quality_score -= 40 if is_blurry     else 0
    quality_score -= 30 if is_dark       else 0
    quality_score -= 20 if is_overexposed else 0
    quality_score -= 30 if is_low_contrast else 0
    quality_score -= 50 if is_occluded   else 0
    
    return {
        'quality_score': max(0, quality_score),
        'laplacian_var': laplacian_var,
        'mean_brightness': mean_brightness,
        'is_blurry': is_blurry,
        'is_dark': is_dark,
        'is_overexposed': is_overexposed,
        'is_low_contrast': is_low_contrast,
        'is_occluded': is_occluded,
    }

# ============================================================================
# 6. DEMO
# ============================================================================

if __name__ == "__main__":
    print("=== Computer Vision Pipeline Demo ===\n")
    
    # 1. Camera projection
    cam = FRONT_CAMERA
    print(f"Camera K:\n{cam.K()}\n")
    
    # Project 3D road points to image
    R = np.eye(3)
    t = np.array([0.0, -1.4, 2.5])  # Camera 1.4m high, 2.5m forward of world origin
    road_pts = np.array([[0, 0, 20], [1, 0, 20], [-1, 0, 20],
                         [0, 0, 40], [0, 0, 60]], dtype=np.float64)
    img_pts = project_3d_to_image(road_pts, cam, R, t)
    print("3D road points projected to image:")
    for p3, p2 in zip(road_pts, img_pts):
        print(f"  {p3} → ({p2[0]:.0f}, {p2[1]:.0f}) px")
    
    # 2. BEV
    bev = BirdsEyeView()
    dummy_img = np.zeros((720, 1280, 3), dtype=np.uint8)
    bev_img = bev.warp(dummy_img)
    print(f"\nBEV: {dummy_img.shape} → {bev_img.shape}")
    x_m, y_m = bev.pixel_to_metric(200, 300)
    print(f"BEV pixel (200, 300) = ({x_m:.1f}m lateral, {y_m:.1f}m forward)")
    
    # 3. Camera quality
    print("\nCamera quality assessment:")
    clear_frame = np.random.randint(50, 200, (720, 1280, 3), dtype=np.uint8)
    quality = assess_camera_quality(clear_frame)
    print(f"  Quality score: {quality['quality_score']}/100")
    print(f"  Laplacian var: {quality['laplacian_var']:.1f}")
    
    # Simulate foggy/blurry frame
    foggy = np.ones((720, 1280, 3), dtype=np.uint8) * 180  # Uniform grey
    foggy_q = assess_camera_quality(foggy)
    print(f"\nFoggy frame quality: {foggy_q['quality_score']}/100 "
          f"(low_contrast={foggy_q['is_low_contrast']})")
