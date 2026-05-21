"""
13_LANE_DETECTION — Production Lane Detection Pipeline
Classical CV (OpenCV) + CNN-based (DeepLab segmentation)
"""

import cv2
import numpy as np
import torch
import torch.nn as nn
from typing import Tuple, Optional, List
from dataclasses import dataclass

# ============================================================================
# DATA TYPES
# ============================================================================

@dataclass
class LaneResult:
    left_poly:   Optional[np.ndarray]  # [a, b, c] for ax²+bx+c
    right_poly:  Optional[np.ndarray]
    lane_width_m: float
    curvature_m:  float                 # Radius of curvature in metres
    offset_m:     float                 # Lateral offset from lane centre (+ = right)
    quality:      int                   # 0=LOST, 1=LOW, 2=MED, 3=HIGH

# ============================================================================
# 1. CLASSICAL OPENCV LANE DETECTION
# ============================================================================

class ClassicalLaneDetector:
    """Production-grade classical CV lane detector.
    Pipeline: Undistort → BEV warp → Sobel → Sliding window → Polynomial fit
    Matches the algorithm used in early ADAS systems (pre-2018).
    Still useful as fallback when CNN confidence is low."""
    
    # Perspective transform: src (image corners of lane) → dst (bird's-eye view)
    # Calibrated for a 1280×720 front camera at typical mount height
    SRC_PTS = np.float32([[200, 720], [580, 460], [700, 460], [1100, 720]])
    DST_PTS = np.float32([[200, 720], [200, 0],   [1000, 0],  [1000, 720]])
    
    def __init__(self, img_w: int = 1280, img_h: int = 720):
        self.img_w = img_w
        self.img_h = img_h
        # Perspective transform matrices
        self.M     = cv2.getPerspectiveTransform(self.SRC_PTS, self.DST_PTS)
        self.M_inv = cv2.getPerspectiveTransform(self.DST_PTS, self.SRC_PTS)
        # Pixels per metre calibration (empirically measured)
        self.ym_per_pix = 30.0 / 720   # 30m in Y direction
        self.xm_per_pix = 3.7 / 700    # 3.7m lane width in X direction
    
    def preprocess(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Extract lane-relevant binary mask from image.
        Combines: gradient (Sobel) + colour thresholding (HLS S-channel)."""
        
        # Resize to working resolution
        img = cv2.resize(frame_bgr, (self.img_w, self.img_h))
        
        # Convert to HLS — S channel is robust to shadows and lighting changes
        hls = cv2.cvtColor(img, cv2.COLOR_BGR2HLS)
        s_channel = hls[:, :, 2]
        
        # Sobel gradient in X (detects vertical edges = lane markings)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        abs_sobelx = np.absolute(sobelx)
        scaled_sobel = np.uint8(255 * abs_sobelx / (np.max(abs_sobelx) + 1e-6))
        
        # Binary masks
        sobel_binary = np.zeros_like(scaled_sobel)
        sobel_binary[(scaled_sobel >= 30) & (scaled_sobel <= 100)] = 1
        
        s_binary = np.zeros_like(s_channel)
        s_binary[(s_channel >= 120) & (s_channel <= 255)] = 1
        
        # Combine: pixel = 1 if EITHER condition is met
        binary = np.zeros_like(sobel_binary)
        binary[(sobel_binary == 1) | (s_binary == 1)] = 1
        return binary
    
    def birds_eye_view(self, binary: np.ndarray) -> np.ndarray:
        """Perspective transform to top-down view."""
        return cv2.warpPerspective(binary, self.M, (self.img_w, self.img_h))
    
    def sliding_window_fit(self, bev: np.ndarray,
                           n_windows: int = 9,
                           margin: int = 100,
                           minpix: int = 50) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Sliding window lane pixel detection.
        Returns left and right polynomial coefficients [a, b, c]."""
        
        # Starting X positions from bottom-half histogram peak
        hist = np.sum(bev[bev.shape[0]//2:, :], axis=0)
        midpoint = hist.shape[0] // 2
        leftx_base  = np.argmax(hist[:midpoint])
        rightx_base = np.argmax(hist[midpoint:]) + midpoint
        
        win_h = bev.shape[0] // n_windows
        nonzeroy, nonzerox = bev.nonzero()
        
        leftx_cur, rightx_cur = leftx_base, rightx_base
        left_inds, right_inds = [], []
        
        for win in range(n_windows):
            y_low  = bev.shape[0] - (win + 1) * win_h
            y_high = bev.shape[0] - win * win_h
            
            # Left window
            xl_low, xl_high = leftx_cur - margin, leftx_cur + margin
            good_left = ((nonzeroy >= y_low) & (nonzeroy < y_high) &
                         (nonzerox >= xl_low) & (nonzerox < xl_high)).nonzero()[0]
            left_inds.append(good_left)
            if len(good_left) >= minpix:
                leftx_cur = int(np.mean(nonzerox[good_left]))
            
            # Right window
            xr_low, xr_high = rightx_cur - margin, rightx_cur + margin
            good_right = ((nonzeroy >= y_low) & (nonzeroy < y_high) &
                          (nonzerox >= xr_low) & (nonzerox < xr_high)).nonzero()[0]
            right_inds.append(good_right)
            if len(good_right) >= minpix:
                rightx_cur = int(np.mean(nonzerox[good_right]))
        
        left_inds  = np.concatenate(left_inds)
        right_inds = np.concatenate(right_inds)
        
        left_poly = right_poly = None
        
        if len(left_inds) > 100:
            leftx, lefty = nonzerox[left_inds], nonzeroy[left_inds]
            left_poly = np.polyfit(lefty, leftx, 2)  # ax²+bx+c
        
        if len(right_inds) > 100:
            rightx, righty = nonzerox[right_inds], nonzeroy[right_inds]
            right_poly = np.polyfit(righty, rightx, 2)
        
        return left_poly, right_poly
    
    def compute_curvature_and_offset(self, left_poly, right_poly,
                                      img_h: int) -> Tuple[float, float]:
        """Compute radius of curvature in metres and lateral offset."""
        y_eval = img_h - 1  # Bottom of image (closest to vehicle)
        
        curvature = float('inf')
        if left_poly is not None and right_poly is not None:
            # Convert polynomial to real-world units (metres)
            # Polynomial in pixel space: x = a*y² + b*y + c
            # In metric space: x_m = a_m*y_m² + b_m*y_m + c_m
            ym, xm = self.ym_per_pix, self.xm_per_pix
            
            left_fit_m  = np.polyfit(np.array([0, img_h//2, img_h]) * ym,
                                      np.polyval(left_poly, [0, img_h//2, img_h]) * xm, 2)
            y_m = y_eval * ym
            curvature = ((1 + (2*left_fit_m[0]*y_m + left_fit_m[1])**2)**1.5) / \
                         (2*np.abs(left_fit_m[0]) + 1e-6)
        
        offset = 0.0
        if left_poly is not None and right_poly is not None:
            left_x  = np.polyval(left_poly, y_eval)
            right_x = np.polyval(right_poly, y_eval)
            lane_centre_px = (left_x + right_x) / 2
            img_centre_px  = self.img_w / 2
            offset = (img_centre_px - lane_centre_px) * self.xm_per_pix
        
        return curvature, offset
    
    def detect(self, frame_bgr: np.ndarray) -> LaneResult:
        """Full pipeline: image → LaneResult."""
        binary = self.preprocess(frame_bgr)
        bev    = self.birds_eye_view(binary)
        left_poly, right_poly = self.sliding_window_fit(bev)
        curvature, offset = self.compute_curvature_and_offset(
            left_poly, right_poly, self.img_h)
        
        # Quality assessment
        both_detected = (left_poly is not None and right_poly is not None)
        quality = 3 if both_detected and abs(curvature) > 150 else \
                  2 if both_detected else \
                  1 if (left_poly is not None or right_poly is not None) else 0
        
        lane_width = 3.7  # Default
        if both_detected:
            y_bottom = self.img_h - 1
            w_px = np.polyval(right_poly, y_bottom) - np.polyval(left_poly, y_bottom)
            lane_width = abs(w_px) * self.xm_per_pix
        
        return LaneResult(
            left_poly=left_poly, right_poly=right_poly,
            lane_width_m=lane_width, curvature_m=curvature,
            offset_m=offset, quality=quality
        )

# ============================================================================
# 2. CNN-BASED LANE DETECTION (Lightweight segmentation)
# ============================================================================

class LaneSegNet(nn.Module):
    """CNN lane detector producing pixel-level lane probability maps.
    Architecture: Encoder (MobileNet-style) + Lightweight decoder.
    Input: (B, 3, 256, 512) RGB
    Output: (B, 2, 256, 512) — channel 0 = left lane, channel 1 = right lane
    
    Production equivalent: Mobileye's CNN lane module, Tesla HydraNet lane branch."""
    
    def __init__(self):
        super().__init__()
        # Encoder: progressive downsampling
        def conv_bn_relu(in_c, out_c, s=1):
            return nn.Sequential(
                nn.Conv2d(in_c, out_c, 3, stride=s, padding=1, bias=False),
                nn.BatchNorm2d(out_c), nn.ReLU(inplace=True))
        
        self.enc1 = nn.Sequential(conv_bn_relu(3, 16, 2),   conv_bn_relu(16, 16))   # /2
        self.enc2 = nn.Sequential(conv_bn_relu(16, 32, 2),  conv_bn_relu(32, 32))   # /4
        self.enc3 = nn.Sequential(conv_bn_relu(32, 64, 2),  conv_bn_relu(64, 64))   # /8
        self.enc4 = nn.Sequential(conv_bn_relu(64, 128, 2), conv_bn_relu(128, 128)) # /16
        
        # Decoder: feature aggregation + upsample
        self.dec3 = nn.Sequential(conv_bn_relu(128+64, 64))
        self.dec2 = nn.Sequential(conv_bn_relu(64+32, 32))
        self.dec1 = nn.Sequential(conv_bn_relu(32+16, 16))
        
        self.head = nn.Conv2d(16, 2, 1)  # 2 lane channels
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)   # (B, 16, H/2, W/2)
        e2 = self.enc2(e1)  # (B, 32, H/4, W/4)
        e3 = self.enc3(e2)  # (B, 64, H/8, W/8)
        e4 = self.enc4(e3)  # (B, 128, H/16, W/16)
        
        # Skip connections (U-Net style) — preserves fine lane boundary detail
        d3 = F.interpolate(e4, scale_factor=2, mode='bilinear', align_corners=False)
        d3 = self.dec3(torch.cat([d3, e3], dim=1))
        
        d2 = F.interpolate(d3, scale_factor=2, mode='bilinear', align_corners=False)
        d2 = self.dec2(torch.cat([d2, e2], dim=1))
        
        d1 = F.interpolate(d2, scale_factor=2, mode='bilinear', align_corners=False)
        d1 = self.dec1(torch.cat([d1, e1], dim=1))
        
        d0 = F.interpolate(d1, scale_factor=2, mode='bilinear', align_corners=False)
        return self.head(d0)  # (B, 2, H, W) logits

def lane_mask_to_polynomial(mask: np.ndarray) -> Optional[np.ndarray]:
    """Convert binary lane mask to polynomial coefficients.
    mask: (H, W) binary, 1 = lane pixel
    Returns: [a, b, c] for x = ay² + by + c"""
    ys, xs = np.nonzero(mask)
    if len(xs) < 20:
        return None
    return np.polyfit(ys, xs, 2)

# ============================================================================
# 3. LANE TRACKING — Temporal smoothing
# ============================================================================

class LaneTracker:
    """Temporal lane tracker using exponential moving average.
    Prevents jitter between frames — critical for LKA output stability.
    
    Production: Bosch MPC5 uses 3-5 frame polynomial coefficient averaging."""
    
    def __init__(self, alpha: float = 0.7):
        self.alpha = alpha  # EMA factor: higher = more weight to new detections
        self.left_poly_ema:  Optional[np.ndarray] = None
        self.right_poly_ema: Optional[np.ndarray] = None
        self.age = 0
    
    def update(self, result: LaneResult) -> LaneResult:
        """Apply EMA smoothing to polynomial coefficients."""
        if result.left_poly is not None:
            if self.left_poly_ema is None:
                self.left_poly_ema = result.left_poly.copy()
            else:
                self.left_poly_ema = self.alpha * result.left_poly + \
                                     (1 - self.alpha) * self.left_poly_ema
        
        if result.right_poly is not None:
            if self.right_poly_ema is None:
                self.right_poly_ema = result.right_poly.copy()
            else:
                self.right_poly_ema = self.alpha * result.right_poly + \
                                      (1 - self.alpha) * self.right_poly_ema
        self.age += 1
        
        return LaneResult(
            left_poly=self.left_poly_ema,
            right_poly=self.right_poly_ema,
            lane_width_m=result.lane_width_m,
            curvature_m=result.curvature_m,
            offset_m=result.offset_m,
            quality=result.quality
        )

# ============================================================================
# 4. DEMO
# ============================================================================

if __name__ == "__main__":
    print("=== Lane Detection Pipeline Demo ===\n")
    
    # Classical CV detector
    detector = ClassicalLaneDetector(1280, 720)
    tracker  = LaneTracker(alpha=0.7)
    
    # Simulate 5 frames
    for i in range(5):
        dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        # Draw synthetic lane lines (white)
        cv2.line(dummy_frame, (400, 720), (560, 460), (255,255,255), 5)
        cv2.line(dummy_frame, (880, 720), (720, 460), (255,255,255), 5)
        
        raw = detector.detect(dummy_frame)
        smoothed = tracker.update(raw)
        print(f"Frame {i}: quality={smoothed.quality} offset={smoothed.offset_m:.3f}m "
              f"curvature={smoothed.curvature_m:.0f}m")
    
    # CNN detector
    print("\nCNN LaneSegNet:")
    model = LaneSegNet()
    params = sum(p.numel() for p in model.parameters())
    print(f"  Parameters: {params:,}")
    dummy_input = torch.randn(1, 3, 256, 512)
    with torch.no_grad():
        out = model(dummy_input)
    print(f"  Input: {dummy_input.shape} → Output: {out.shape}")
    lane_prob = torch.sigmoid(out[0, 0]).numpy()
    poly = lane_mask_to_polynomial((lane_prob > 0.5).astype(np.uint8))
    print(f"  Left lane poly from sigmoid mask: {poly}")
