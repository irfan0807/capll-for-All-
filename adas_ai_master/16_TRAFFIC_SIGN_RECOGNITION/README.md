# 16 — Traffic Sign Recognition (TSR)

## Overview
Traffic Sign Recognition (TSR) pipeline: detection, classification, and map fusion. Covers German/EU signs (Vienna Convention), speed limit recognition, SOTIF edge cases, and production deployment.

---

## 1. TSR Pipeline

```
Camera frame (1280×720)
        │
        ▼
Sign Detection (CNN — small object detector)
        │  Candidate ROIs [x1,y1,x2,y2, conf]
        ▼
Sign Classification (lightweight CNN per crop)
        │  [sign_type, speed_value, confidence]
        ▼
Temporal Filtering (moving average, min 3 frames)
        │
        ▼
Map Fusion (validate against HD map)
        │
        ▼
ECU Output → ICM display + Powertrain speed limit signal
```

---

## 2. Sign Classification Model

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple

class TSRClassifier(nn.Module):
    """Lightweight TSR classifier for speed limit and warning signs.
    Input: 64×64×3 crop (sign region)
    Output: class probabilities (100 EU sign classes)
    
    Target: <1ms on ARM Cortex-A72 with TensorRT INT8"""
    
    def __init__(self, num_classes: int = 100):
        super().__init__()
        # Depthwise separable convolutions for efficiency
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, 2, 1),                      # 64→32
            nn.BatchNorm2d(32), nn.ReLU(inplace=True),
            self._dw_conv(32, 64),                           # 32→32
            self._dw_conv(64, 128, stride=2),                # 32→16
            self._dw_conv(128, 128),
            self._dw_conv(128, 256, stride=2),               # 16→8
            self._dw_conv(256, 256),
            nn.AdaptiveAvgPool2d(1)
        )
        self.classifier = nn.Linear(256, num_classes)
    
    def _dw_conv(self, in_ch: int, out_ch: int, 
                  stride: int = 1) -> nn.Sequential:
        return nn.Sequential(
            nn.Conv2d(in_ch, in_ch, 3, stride, 1, groups=in_ch, bias=False),
            nn.BatchNorm2d(in_ch), nn.ReLU(inplace=True),
            nn.Conv2d(in_ch, out_ch, 1, bias=False),
            nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x).flatten(1))

# Confidence calibration for TSR (Platt scaling)
def calibrate_confidence(logits: torch.Tensor,
                          temperature: float = 1.5) -> torch.Tensor:
    """Temperature scaling reduces overconfidence in TSR classifier.
    Trained temperature: tune on validation set."""
    return F.softmax(logits / temperature, dim=-1)
```

---

## 3. Speed Limit Sign Parsing

```python
# EU speed limit sign types:
SPEED_LIMIT_CLASSES = {
    'speed_30': 30, 'speed_50': 50, 'speed_60': 60,
    'speed_70': 70, 'speed_80': 80, 'speed_100': 100,
    'speed_120': 120, 'speed_130': 130,
    'speed_end': None  # End of speed limit zone
}

def parse_speed_limit(cls_name: str, confidence: float,
                       min_confidence: float = 0.85) -> int | None:
    """Extract numeric speed limit from classification result.
    Returns None if confidence below threshold or not a speed sign."""
    if confidence < min_confidence:
        return None
    return SPEED_LIMIT_CLASSES.get(cls_name)
```

---

## 4. Temporal Filtering

Single-frame classification is noisy (sun glare, motion blur). Use sliding window majority vote:

```python
from collections import deque, Counter

class TSRTemporalFilter:
    """Majority-vote temporal filter over sliding window.
    Prevents spurious sign changes from transient misclassifications."""
    
    def __init__(self, window: int = 5, min_votes: int = 3):
        self._buffer = deque(maxlen=window)
        self.min_votes = min_votes
    
    def update(self, cls_name: str | None) -> str | None:
        self._buffer.append(cls_name)
        if len(self._buffer) < self.min_votes:
            return None
        counts = Counter(self._buffer)
        top, vote_count = counts.most_common(1)[0]
        return top if vote_count >= self.min_votes else None
```

---

## 5. SOTIF Edge Cases

| Scenario | Failure | Mitigation |
|---------|---------|-----------|
| Partially occluded sign | Wrong class | Require full sign in frame (min size 20×20px) |
| Sign reflection on wet road | False positive | Validate sign position (above horizon line) |
| Temporary construction sign | Unknown class → "no sign" | Confidence threshold; log to OTA for retraining |
| Backlit sign (strong sun) | Bloom/glare → classify as wrong sign | HDR exposure fusion; low-confidence fallback to map |
| Double speed limit signs at roadworks | Contradictory output | Map priority > camera for safety-critical limits |

---

## 6. Map Fusion for TSR Robustness

```
Camera TSR: "speed_80" at position P
Map speed limit at position P: 100
Decision: → Warn driver (mismatch → take lower of the two)
          → Log camera reading for OTA map update

Camera TSR: "speed_50" at position P
Map speed limit at position P: 50
Decision: → Confirmed, display to driver
```

---

## 7. Interview Q&A

### L1
**Q: Why is temporal filtering essential for TSR in production?**  
A: Single-frame classification is unreliable due to motion blur (sign at road edge during 130kph travel), partial occlusion by trucks, sun glare, and CNN softmax overconfidence. A majority vote over 5 consecutive frames (0.17s at 30fps) ensures the sign has been consistently classified before informing the driver. Without temporal filtering, speed limit display would flicker — which is unacceptable for driver trust and HMI guidelines (ISO 15622 ACC).

### L2
**Q: How do you handle the EU "End of all restrictions" sign (circular white with diagonal stripes)?**  
A: Special class in the 100-class classifier. When detected: (1) clear all active speed limit restrictions; (2) revert to map-based speed limit. Challenge: this sign is visually similar to other circular signs under poor lighting. Mitigation: use high temperature scaling (temperature=2.0) for this class to prevent overconfident false activation; require map confirmation that a restriction zone was active before clearing.

### L3
**Q: Design an end-to-end TSR pipeline for a production Tier-1 ADAS ECU targeting SOTIF compliance.**  
A: (1) Detection: YOLOv5s at P3 scale (small object head), trained on GTSRB + custom dataset, targets signs ≥15px. (2) Classification: TSRClassifier (64×64 crop), INT8 TensorRT, ~0.3ms/sign. (3) Temporal filter: 5-frame majority vote per sign type, separate instance per unique sign detected in scene. (4) Confidence calibration: temperature scaling (T=1.5) validated on held-out night/rain partition. (5) Map fusion: HD map lookup within 50m; camera vs map mismatch logged + driver displayed lower limit. (6) SOTIF coverage: ODD restrictions (e.g., disable TSR in construction zones with known map flag); validation covers GTSRB test set + adversarial patch dataset; trigger rate analysis for false speed changes.
