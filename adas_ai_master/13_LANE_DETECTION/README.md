# 13 — Lane Detection

## Overview
Lane detection from monocular camera: classical Hough-based methods, deep learning segmentation, polynomial fitting, and real-world edge cases. Covers ACC+LKA lane-keeping and SOTIF safety limits.

---

## 1. Classical vs CNN Lane Detection

| Method | Speed | Accuracy | Robustness | Production Use |
|--------|-------|----------|-----------|---------------|
| Hough Lines | Very fast (<1ms) | Low | Poor (marks, shadows) | Legacy (pre-2018) |
| Polynomial + IPM | Fast (<2ms) | Medium | OK (highway) | ADAS L1 fallback |
| Semantic segmentation (ERFNet) | ~10ms GPU | High | Good | Bosch, Continental |
| Instance segmentation (LaneNet) | ~15ms GPU | Very high | Very good | Mobileye-style |
| Transformer (CLRNet, RESA) | ~5ms GPU | SOTA | Excellent | 2023+ production |

---

## 2. Classical Pipeline

```
Frame → Undistort → ROI crop → Grayscale
  → Gaussian blur → Canny edges
  → IPM (Birds-Eye View warp)
  → Sliding window peak detection
  → Polynomial fit (2nd-order)
  → Convert back to camera frame
```

**Polynomial representation:**
$$x = a_2 y^2 + a_1 y + a_0$$
where y is vertical position in BEV, x is lateral offset. 2nd order handles typical road curves.

**3rd order for tighter curves:**
$$x = a_3 y^3 + a_2 y^2 + a_1 y + a_0$$

---

## 3. Deep Learning: ERFNet Segmentation

ERFNet (Efficient Residual Factorised Network):
- Real-time semantic segmentation backbone
- Non-Bottleneck-1D residual block: 3×3 conv factorised into 3×1 + 1×3
- Lane output: binary mask (lane / not-lane) or multi-class (solid/dashed/double)

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple

class NonBottleneck1D(nn.Module):
    """ERFNet residual factorised block.
    3×3 conv → 3×1 + 1×3 (factorised) saves ~3× FLOPs."""
    def __init__(self, ch: int, dilation: int = 1, dropout: float = 0.1):
        super().__init__()
        self.branch = nn.Sequential(
            nn.Conv2d(ch, ch, (3,1), padding=(1,0), bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(ch, ch, (1,3), padding=(0,1), bias=False),
            nn.BatchNorm2d(ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(ch, ch, (3,1), padding=(dilation,0),
                      dilation=(dilation,1), bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(ch, ch, (1,3), padding=(0,dilation),
                      dilation=(1,dilation), bias=False),
            nn.BatchNorm2d(ch),
            nn.Dropout2d(dropout),
        )
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.relu(x + self.branch(x), inplace=True)

class LightLaneSegHead(nn.Module):
    """Lightweight lane segmentation head (for demo).
    Input: (B, 128, H/8, W/8) backbone features
    Output: (B, 3, H, W) — background / left-lane / right-lane"""
    def __init__(self, in_ch: int = 128, num_classes: int = 3):
        super().__init__()
        self.up1 = nn.ConvTranspose2d(in_ch, 64, 2, stride=2)
        self.nb1 = NonBottleneck1D(64)
        self.up2 = nn.ConvTranspose2d(64, 32, 2, stride=2)
        self.nb2 = NonBottleneck1D(32)
        self.up3 = nn.ConvTranspose2d(32, 16, 2, stride=2)
        self.head = nn.Conv2d(16, num_classes, 1)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.relu(self.up1(x))
        x = self.nb1(x)
        x = F.relu(self.up2(x))
        x = self.nb2(x)
        x = F.relu(self.up3(x))
        return self.head(x)  # Raw logits (B, num_classes, H, W)
```

---

## 4. Post-Processing: Lane Line Extraction from Mask

```python
import numpy as np
import cv2
from typing import Optional

def fit_lane_polynomial(mask: np.ndarray, 
                         degree: int = 2) -> Optional[np.ndarray]:
    """Fit polynomial to binary lane mask using sliding window.
    
    Args:
        mask: (H, W) binary lane mask, values {0, 1}
        degree: polynomial degree (2 = parabola)
    Returns:
        coeffs: polynomial coefficients [a2, a1, a0] or None if no points
    """
    ys, xs = np.where(mask > 0)
    if len(ys) < 10:
        return None
    
    # Fit y = f(x): column position as function of row
    # Use np.polyfit — least squares polynomial
    try:
        coeffs = np.polyfit(ys, xs, degree)
        return coeffs
    except np.RankWarning:
        return None

def lateral_offset_from_lane(left_coeffs: Optional[np.ndarray],
                               right_coeffs: Optional[np.ndarray],
                               frame_height: int = 720,
                               frame_width: int = 1280,
                               pixels_per_metre_lateral: float = 30.0) -> float:
    """Estimate vehicle lateral offset from lane centre.
    Positive = vehicle is right of centre.
    
    Returns offset in metres."""
    eval_row = int(frame_height * 0.75)   # Evaluate near bottom of frame
    vehicle_centre_px = frame_width / 2
    
    if left_coeffs is not None and right_coeffs is not None:
        left_x  = np.polyval(left_coeffs,  eval_row)
        right_x = np.polyval(right_coeffs, eval_row)
        lane_centre = (left_x + right_x) / 2
    elif left_coeffs is not None:
        left_x = np.polyval(left_coeffs, eval_row)
        lane_centre = left_x + (3.7 * pixels_per_metre_lateral / 2)  # Assume 3.7m lane
    elif right_coeffs is not None:
        right_x = np.polyval(right_coeffs, eval_row)
        lane_centre = right_x - (3.7 * pixels_per_metre_lateral / 2)
    else:
        return 0.0  # No lanes detected — no correction
    
    offset_px = vehicle_centre_px - lane_centre
    return offset_px / pixels_per_metre_lateral
```

---

## 5. SOTIF Edge Cases

| Scenario | Failure Mode | Mitigation |
|---------|-------------|-----------|
| Construction zone (temporary markings over old) | Two lanes detected, wrong one followed | Confidence threshold + speed limit (SOTIF ODD) |
| Sun glare into camera | Edge detector fails | Glare detection DTC; disable LKA |
| Lane merge (dashed → no lane) | Lane lost → lane following continues with dead reckoning | Dead reckoning timeout (3s) → alert driver |
| Snow covering lane markings | No lane detected | Fallback to HD map lanes |
| Curvy road with strong shadows | False lane edges from shadow | Shadow augmentation in training; temporal smoothing |

---

## 6. Curvature and Steering Angle

Given left lane coefficients $[a_2, a_1, a_0]$ (pixel space):

$$R_{curve} = \frac{(1 + (2a_2 y + a_1)^2)^{3/2}}{|2a_2|}$$

Convert to world: $R_{world} = R_{pixels} \times m_{pix}$ where $m_{pix}$ = metres/pixel in IPM.

**Steering angle approximation (Ackermann, small angle):**
$$\delta = \arctan(L / R_{curve})$$
where L = wheelbase (~2.7m for passenger car).

---

## 7. Interview Q&A

### L1
**Q: Why is inverse perspective mapping (IPM) important for lane detection?**  
A: IPM removes perspective distortion, converting the camera view to a birds-eye view (BEV). In the camera view, parallel lanes converge (vanishing point). In BEV, parallel lanes remain parallel and lane width is constant — making polynomial fitting much more accurate and interpretable. Limitation: IPM assumes flat road — fails on hills, bridges.

### L2
**Q: How do you handle the case when one lane line is not visible?**  
A: Use ego-lane width estimate. Standard lane width = 3.5-3.7m. If left lane visible (left_x), right lane estimated as `right_x = left_x + 3.7 × ppm` (pixels per metre). Vehicle offset estimated from single line. Mark confidence as "half-detected" — may reduce LKA correction strength. If no lanes: dead reckoning using IMU heading for 3s, then alert driver.

### L3
**Q: CLRNet achieves 80%+ F1 on CULane. What architectural advances enabled this?**  
A: CLRNet (Cross-Layer Refinement Network) uses: (1) Lane proposal representation as points along a fixed y-coordinates grid (similar to anchor-based detection, but for lines); (2) Cross-layer refinement: proposals initialised at coarse feature map and progressively refined at higher-resolution features; (3) Line IoU metric for NMS: uses overlap along the lane direction, more semantically correct than box IoU for thin structures; (4) ROIAlignBasedAggregator: samples multi-scale features along the predicted line for re-scoring. Training: focal loss on classification + smooth L1 for offset regression. Compared to segmentation approaches, CLRNet avoids the post-processing bottleneck (connecting mask pixels into lines).

---

## Files
- [lane_detection.py](lane_detection.py) — ERFNet head, polynomial fit, lateral offset, IPM demo
