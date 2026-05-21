# 18 — Pedestrian Detection

## Overview
Pedestrian detection for ADAS: thermal imaging, RGB+IR fusion, occlusion handling, and multi-scale detection. Covers EURO NCAP pedestrian AEB assessment scenarios and SOTIF boundary conditions.

---

## 1. Pedestrian Detection Challenges vs Cars

| Challenge | Pedestrian | Car |
|---------|------------|-----|
| Size variability | 15-400px height | 50-500px |
| Aspect ratio | Variable (walking, cycling, crouching) | Consistent |
| Occlusion | Frequent (crowd, parked cars) | Moderate |
| Deformable | High (joint articulation) | Low |
| Night IR | Required for AEB compliance | Less critical |
| Class confusion | Cyclist, mannequin, pole | Truck, van |

---

## 2. Thermal Camera for Pedestrian Detection

**Why thermal (LWIR 8-14µm):**
- Human body radiates ~9.3µm thermal radiation (body temp ~36°C)
- Visible in complete darkness, fog, and adverse weather
- Distinguishes warm humans from cold background

**Thermal + RGB fusion:**
```python
import torch
import torch.nn as nn

class ThermalRGBFusion(nn.Module):
    """Dual-stream pedestrian detector: RGB + Thermal fusion.
    RGB stream: standard visual features (texture, colour, shape)
    Thermal stream: temperature features (human heat signature)
    
    Fusion: concatenate feature maps at P3 level, then shared detection head."""
    
    def __init__(self, out_ch: int = 256):
        super().__init__()
        # RGB encoder (shared backbone channels)
        self.rgb_enc = nn.Sequential(
            nn.Conv2d(3, 64, 3, 2, 1), nn.BatchNorm2d(64), nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, 3, 2, 1), nn.BatchNorm2d(128), nn.ReLU(inplace=True),
        )
        # Thermal encoder (single channel)
        self.thr_enc = nn.Sequential(
            nn.Conv2d(1, 32, 3, 2, 1), nn.BatchNorm2d(32), nn.ReLU(inplace=True),
            nn.Conv2d(32, 128, 3, 2, 1), nn.BatchNorm2d(128), nn.ReLU(inplace=True),
        )
        # Fusion projection
        self.fuse = nn.Conv2d(256, out_ch, 1)
    
    def forward(self, rgb: torch.Tensor, 
                thermal: torch.Tensor) -> torch.Tensor:
        f_rgb = self.rgb_enc(rgb)
        f_thr = self.thr_enc(thermal)
        fused = torch.cat([f_rgb, f_thr], dim=1)
        return self.fuse(fused)
```

---

## 3. Pedestrian-Specific Augmentation

```python
import albumentations as A

pedestrian_aug = A.Compose([
    # Night simulation
    A.RandomBrightnessContrast(brightness_limit=(-0.5,-0.2), p=0.3),
    # Partial occlusion simulation
    A.CoarseDropout(max_holes=4, max_height=60, max_width=30,
                    min_holes=1, p=0.4),
    # Rain / headlight glare
    A.RandomRain(drop_length=20, p=0.2),
    A.ImageCompression(quality_lower=50, p=0.2),
    A.HorizontalFlip(p=0.5),
], bbox_params=A.BboxParams(format='pascal_voc', min_visibility=0.3))
```

---

## 4. EURO NCAP Pedestrian AEB Test Scenarios

| Test ID | Scenario | Speed | Pass Condition |
|---------|---------|-------|----------------|
| PED_CPFA_25 | Child crossing from far side, adult | 25kph | No collision / speed <5kph at contact |
| PED_CPNCO_40 | Adult crossing near-side, no occlusion | 40kph | No collision |
| PED_CPCB | Adult crossing, car blocking view | 20kph | Trigger AEB within 0.5s of clear view |
| PED_Lon_25 | Pedestrian walking in lane ahead | 25kph | AEB stops before contact |

**Sensor performance floor for NCAP 5-star:**
- Detection range: ≥ 25m at night for upright pedestrian
- Recall: ≥ 98% under NCAP conditions (daytime + artificial night lighting)
- False positive rate: < 1 per 1000km

---

## 5. Occlusion-Aware Detection

```python
import numpy as np

def non_max_suppression_pedestrian(boxes: np.ndarray,
                                    scores: np.ndarray,
                                    iou_threshold: float = 0.3) -> list:
    """Lower IoU threshold for pedestrian NMS to preserve occluded pedestrians.
    Standard NMS at 0.45 suppresses partially visible people in crowds.
    Softer NMS: weight by overlap instead of suppressing."""
    if len(boxes) == 0:
        return []
    
    order = scores.argsort()[::-1]
    x1,y1,x2,y2 = boxes[:,0],boxes[:,1],boxes[:,2],boxes[:,3]
    areas = (x2-x1) * (y2-y1)
    keep  = []
    
    while len(order) > 0:
        i = order[0]
        keep.append(int(i))
        
        ix1 = np.maximum(x1[i], x1[order[1:]])
        iy1 = np.maximum(y1[i], y1[order[1:]])
        ix2 = np.minimum(x2[i], x2[order[1:]])
        iy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0, ix2-ix1) * np.maximum(0, iy2-iy1)
        iou   = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        
        # Soft suppression: keep if IoU < threshold (lower = keep more)
        order = order[1:][iou <= iou_threshold]
    
    return keep
```

---

## 6. Interview Q&A

### L1
**Q: Why is a lower NMS threshold used for pedestrian detection vs vehicle detection?**  
A: Vehicles rarely overlap significantly in normal driving. Pedestrians in crowds can substantially overlap — a threshold of 0.45 (standard YOLO) would suppress adjacent pedestrians. Pedestrian-specific NMS uses 0.3 or Soft-NMS (reduces score instead of suppressing) to maintain multiple pedestrian detections in crowded crossings — critical for AEB scenarios with multiple pedestrians.

### L2
**Q: Describe how thermal camera improves nighttime pedestrian detection.**  
A: At night, visible camera requires active illumination (headlights) or starlight sensors. Thermal (LWIR 8-14µm) passively detects human body heat. Human body temperature ~36°C emits peak radiation at ~9µm. Contrast: human body at 36°C vs road at 10°C = large thermal signature. RGB camera at night: person barely visible, headlight glare overwhelms nearby dark figures. Thermal: person is bright, road is dark — very high contrast. Dual-stream RGB+Thermal fusion adds ~8% mAP@0.5 improvement on Caltech Pedestrian Dataset nighttime subset.

### L3
**Q: How would you validate pedestrian detection for EURO NCAP 2023 AEB pedestrian assessment?**  
A: Validation process: (1) Static performance: measure precision-recall on KAIST, CityPersons, EuroCity Persons datasets (day, night, rain partitions). Requirement: recall ≥ 95% @ 0.3 FPPI. (2) Closed-track testing: EURO NCAP protocol — actuator dummies (Global VSS pedestrian dummy), 10-50kph, 25 scenarios across day/night/rain. (3) Open road: 10,000km naturalistic data collection; analyse miss rate per scenario type (crossing, longitudinal, occluded). (4) SOTIF: edge cases for ODD restriction — disable pedestrian AEB at speeds >80kph (urban only); thermal camera fallback for low-visibility. (5) DFM (Design FMEA): failure of camera, thermal, or fusion software → speed restriction + audio warning + DTC. All AEB inhibit logic reviewed by ISO 26262 safety team.
