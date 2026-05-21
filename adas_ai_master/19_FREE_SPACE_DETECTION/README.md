# 19 — Free Space Detection

## Overview
Free space (drivable area) detection: semantic segmentation of the drivable road surface and boundaries. Used for AEB, path planning, parking, and off-road detection.

---

## 1. Free Space vs Lane Detection

| Method | Output | Use |
|--------|--------|-----|
| Lane detection | Polylines (lane edges) | Lane keeping, lane centering |
| Free space | Binary/multi-class mask | Full drivable region, parking, unstructured roads |
| Occupancy grid | 2D grid of occupied cells | Path planning, collision avoidance |
| BEV segmentation | Top-down semantic map | Multi-sensor fusion, AD stack |

---

## 2. Segmentation Architecture

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class FreeSpaceDecoder(nn.Module):
    """Lightweight U-Net-style decoder for free space segmentation.
    Classes: 0=background, 1=drivable, 2=road_marking, 3=sidewalk
    
    Input: backbone features P3(80×48), P4(40×24), P5(20×12) for 640×384 input
    Output: (B, 4, 384, 640) segmentation logits"""
    
    def __init__(self, num_classes: int = 4,
                 enc_channels: tuple = (256, 128, 64)):
        super().__init__()
        # Upsample P5 → P4 resolution
        self.up5 = nn.ConvTranspose2d(enc_channels[0], 128, 2, stride=2)
        self.conv5 = nn.Sequential(
            nn.Conv2d(128 + enc_channels[1], 128, 3, 1, 1),
            nn.BatchNorm2d(128), nn.ReLU(inplace=True)
        )
        # Upsample P4 → P3 resolution
        self.up4 = nn.ConvTranspose2d(128, 64, 2, stride=2)
        self.conv4 = nn.Sequential(
            nn.Conv2d(64 + enc_channels[2], 64, 3, 1, 1),
            nn.BatchNorm2d(64), nn.ReLU(inplace=True)
        )
        # Upsample to full resolution
        self.up3  = nn.ConvTranspose2d(64, 32, 2, stride=2)
        self.up2  = nn.ConvTranspose2d(32, 16, 2, stride=2)
        self.up1  = nn.ConvTranspose2d(16, 16, 2, stride=2)
        self.head = nn.Conv2d(16, num_classes, 1)
    
    def forward(self, p3, p4, p5) -> torch.Tensor:
        x = F.relu(self.up5(p5))
        x = torch.cat([x, p4], dim=1)
        x = self.conv5(x)
        x = F.relu(self.up4(x))
        x = torch.cat([x, p3], dim=1)
        x = self.conv4(x)
        x = F.relu(self.up3(x))
        x = F.relu(self.up2(x))
        x = F.relu(self.up1(x))
        return self.head(x)  # (B, num_classes, H, W)
```

---

## 3. Free Space Post-Processing

```python
import numpy as np
import cv2
from typing import Tuple

def extract_free_space_boundary(mask: np.ndarray,
                                  roi_top: float = 0.4) -> np.ndarray:
    """Extract free space boundary line from binary drivable mask.
    
    mask: (H, W) binary mask (1 = drivable)
    roi_top: top of region of interest (fraction of frame height)
    Returns: (W,) array — height of free space boundary per column (pixels)"""
    H, W = mask.shape
    roi_start = int(H * roi_top)
    boundary = np.full(W, H, dtype=np.int32)  # Default: no boundary = bottom
    
    for col in range(W):
        col_slice = mask[roi_start:, col]
        # Find first row from top that is NOT drivable
        non_drivable = np.where(col_slice == 0)[0]
        if len(non_drivable) > 0:
            boundary[col] = roi_start + non_drivable[0]
    
    return boundary

def compute_free_space_area(mask: np.ndarray,
                             pixels_per_m2: float = 400.0) -> float:
    """Estimate drivable area in m² from segmentation mask.
    pixels_per_m2: calibration value from IPM."""
    return float(mask.sum()) / pixels_per_m2

def distance_to_obstacle_from_mask(mask: np.ndarray,
                                     lane_x_range: Tuple[int,int],
                                     pixels_per_metre: float = 20.0) -> float:
    """Estimate distance to nearest non-drivable pixel ahead in ego lane.
    For AEB: if free space ends close → possible obstacle."""
    lane_l, lane_r = lane_x_range
    H = mask.shape[0]
    
    # Look column by column in lane region, top-to-bottom
    for row in range(H//2, H):  # Only look in lower half (near range)
        lane_slice = mask[row, lane_l:lane_r]
        if np.mean(lane_slice) < 0.5:  # >50% non-drivable
            dist_px = H - row
            return dist_px / pixels_per_metre
    return float('inf')
```

---

## 4. Training — Loss Functions

**Cross-entropy with class weights** (road is rare in full image):
```python
import torch

# Typical class frequencies in CityScapes-style dataset:
# drivable: 8%, road_marking: 0.5%, sidewalk: 5%, background: 86.5%
FREESPACE_CLASS_WEIGHTS = torch.tensor([0.2, 5.0, 10.0, 2.0])

def freespace_loss(pred: torch.Tensor, 
                    target: torch.Tensor) -> torch.Tensor:
    """Weighted cross-entropy + Dice loss combination."""
    ce = torch.nn.functional.cross_entropy(
        pred, target, weight=FREESPACE_CLASS_WEIGHTS.to(pred.device))
    
    # Dice loss for drivable class (class 1) — handles imbalance
    pred_soft = torch.softmax(pred, dim=1)[:, 1]
    tgt_bin   = (target == 1).float()
    dice_num  = 2 * (pred_soft * tgt_bin).sum()
    dice_den  = pred_soft.sum() + tgt_bin.sum() + 1e-6
    dice_loss = 1.0 - dice_num / dice_den
    
    return ce + dice_loss
```

---

## 5. SOTIF Considerations

| Scenario | Risk | Mitigation |
|---------|------|-----------|
| Tram tracks / rail = drivable | Path planning follows tram track | Semantic map: tracks = restricted zone |
| Water puddle (reflective) | Puddle misclassified as sky = gap in drivable | HDR + puddle appearance augmentation in training |
| Unmarked construction zone | Road ends abruptly | Velocity limiting in construction ODD |
| Desert / off-road (no markings) | No semantic cues → uncertain segmentation | Confidence threshold; disable function outside urban ODD |

---

## 6. Interview Q&A

### L1
**Q: What is the difference between free space detection and occupancy grid mapping?**  
A: Free space detection from camera gives a 2D pixel mask of drivable vs non-drivable areas in the image plane — it's a single-frame output, no temporal accumulation. An occupancy grid is a top-down (BEV) representation of the environment accumulated over time from multiple sensors (camera, LiDAR, radar). Each grid cell stores a probability of being occupied. Occupancy grids handle 3D objects, temporal persistence, and sensor fusion — they are the input to motion planning. Free space segmentation is typically the perception input that populates the occupancy grid.

### L2
**Q: Explain how Dice loss addresses class imbalance in road segmentation.**  
A: In a typical 640×384 ADAS camera frame, the drivable road occupies perhaps 8-15% of pixels. Cross-entropy loss is dominated by the large background class — the gradient from road pixels is small. Dice loss computes the overlap between predicted and ground truth: $\text{Dice} = \frac{2|A \cap B|}{|A| + |B|}$. It's independent of the class frequency — a perfect prediction of the road area (even if small) scores 1.0. In practice, CE + Dice combination works best: CE provides per-pixel gradient signal, Dice drives overall overlap maximisation.

### L3
**Q: How do you deploy a real-time free space segmentation model on a TDA4VM ECU for parking?**  
A: (1) Model: FreeSpaceDecoder with MobileNetV2 backbone, INT8 TIDL quantisation. Target: <8ms @ 15fps (parking) on ARM A72. (2) Input: 640×384, front camera only for forward; all 4 surround cameras for 360° parking assist. (3) IPM post-processing: transform segmentation mask to BEV using pre-computed remap LUT (hardware accelerated on TDA4VM ISP). (4) Occupancy grid update: 0.1m cells, 10m×10m around vehicle; Bayesian update each frame. (5) Path planner uses grid: cost function increases with occupied cells near path. (6) Safety: if model confidence < 0.6 on drivable region → restrict automated parking speed to 3kph; FMEA covers camera failure → disable parking automation + alert driver.
