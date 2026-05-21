# 17 — Driver Monitoring System (DMS)

## Overview
AI-based Driver Monitoring System (DMS) for drowsiness detection, gaze estimation, distraction classification, and hands-on-wheel detection. Covers facial landmark detection, attention state machine, and ISO 17488 / NHTSA requirements.

---

## 1. DMS Overview

**Regulatory mandate:**  
- EU GSR (General Safety Regulation) 2022: DMS mandatory on all new EU vehicles from July 2024
- Euro NCAP 5-star: DMS required from 2023 assessments

**DMS Functions:**

| Function | Sensor | AI Method |
|---------|--------|----------|
| Eye closure (drowsiness) | NIR camera | Landmark CNN → EAR |
| Gaze zone estimation | NIR camera | Head pose + gaze CNN |
| Distraction detection | NIR camera + microphone | Gaze + phone detection |
| Seat belt / airbag disable | IR weight/camera | Occupant classification |
| Hands on wheel | Capacitive / camera | Segmentation CNN |

---

## 2. Eye Aspect Ratio (EAR)

```python
import numpy as np

def eye_aspect_ratio(eye_landmarks: np.ndarray) -> float:
    """Eye Aspect Ratio (EAR) from 6 eye landmarks.
    Based on Soukupova & Cech, 2016.
    
    eye_landmarks: (6, 2) [x, y] in order: outer, inner, top×2, bottom×2
    EAR ≈ 0.3+ when open, drops to ~0.0 when closed.
    Threshold for drowsiness: EAR < 0.2 for > 2s (PERCLOS > 80%)."""
    p = eye_landmarks
    # Vertical distances
    A = np.linalg.norm(p[1] - p[5])
    B = np.linalg.norm(p[2] - p[4])
    # Horizontal distance
    C = np.linalg.norm(p[0] - p[3])
    return (A + B) / (2.0 * C + 1e-6)

def perclos(ear_history: list[float], threshold: float = 0.2) -> float:
    """PERCLOS — Percentage of Eye Closure.
    Standard drowsiness metric: % of frames with EAR < threshold.
    PERCLOS > 0.15 (15%) → drowsy alert per SAE J2399."""
    if not ear_history:
        return 0.0
    closed_frames = sum(1 for e in ear_history if e < threshold)
    return closed_frames / len(ear_history)
```

---

## 3. Head Pose Estimation

```python
import torch
import torch.nn as nn
from typing import Tuple

class HeadPoseNet(nn.Module):
    """Lightweight head pose estimation network.
    Based on HopeNet architecture (Ruiz et al., 2018).
    Outputs: yaw, pitch, roll in degrees.
    Input: 64×64 face crop (NIR or RGB)"""
    
    def __init__(self, num_bins: int = 66):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Conv2d(1, 32, 3, 2, 1), nn.ReLU(inplace=True),  # NIR: 1-channel
            nn.Conv2d(32, 64, 3, 2, 1), nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, 3, 2, 1), nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(4),
            nn.Flatten()
        )
        self.yaw_head   = nn.Linear(128*16, num_bins)
        self.pitch_head = nn.Linear(128*16, num_bins)
        self.roll_head  = nn.Linear(128*16, num_bins)
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        feat = self.backbone(x)
        return self.yaw_head(feat), self.pitch_head(feat), self.roll_head(feat)

def softmax_expectation(logits: torch.Tensor, bins: int = 66) -> torch.Tensor:
    """Convert classification output to continuous angle (HopeNet-style).
    Angles binned into 66 bins over [-99°, +99°]."""
    angle_bins = torch.linspace(-99, 99, bins).to(logits.device)
    probs = torch.softmax(logits, dim=-1)
    return (probs * angle_bins).sum(dim=-1)  # Expected value
```

---

## 4. Gaze Zone Classification

```
┌────────────────────┐
│ Mirror │ Forward  │ Mirror │
│ Left   │  zone    │ Right  │
├────────┼──────────┼────────┤
│ Instru-│ Road     │ Passen-│
│ ment   │ (target) │ ger    │
│ cluster│          │        │
├────────┴──────────┴────────┤
│        Lap / Phone         │
└────────────────────────────┘
```

**7-zone gaze classification from head pose + eye gaze vector:**

```python
def classify_gaze_zone(yaw_deg: float, pitch_deg: float) -> str:
    """Simple rule-based gaze zone from head pose.
    Production systems add gaze vector from iris tracking."""
    if pitch_deg < -20:
        return 'lap_phone'
    elif pitch_deg > 25:
        return 'visor_mirror'
    elif yaw_deg > 30:
        return 'mirror_right'
    elif yaw_deg < -30:
        return 'mirror_left'
    elif abs(yaw_deg) < 15 and abs(pitch_deg) < 15:
        return 'forward_road'
    elif yaw_deg < -15:
        return 'instrument_cluster'
    else:
        return 'passenger_side'
```

---

## 5. Attention State Machine

```
         EAR < 0.2 for >1s
    ┌──────────────────────────────┐
    │                              ▼
AWAKE ──────────────────────── DROWSY_1 ──── 3s more ──► DROWSY_2 ──► ALERT!
    ▲           EAR > 0.3          │                         │
    └───────────────────────────────┴──── driver response ───┘
    
    Gaze off road > 2s → DISTRACTED
    Hands off wheel > 5s (L2) → HANDS_OFF_WARNING
```

---

## 6. NIR Camera Requirements

**DMS camera spec:**
- NIR illuminator: 850nm or 940nm (940nm = invisible to driver)
- Frame rate: 30fps minimum
- Resolution: 640×480 or higher (face must be ≥ 80×80px at 1m)
- HDR: required for tunnel→sunlight transitions
- Temperature range: -40°C to +85°C (cabin camera)

---

## 7. Interview Q&A

### L1
**Q: What is PERCLOS and what threshold triggers a drowsiness alert?**  
A: PERCLOS (PERcentage of eye CLOSure) measures what percentage of frames (over a rolling window) the eyes are more than 80% closed (EAR < 0.2). SAE J2399 standard: PERCLOS > 15% over a 1-minute window correlates with driver impairment. DMS systems typically trigger Level 1 alert (visual + auditory warning) at PERCLOS > 15%, and Level 2 (haptic steering + automated deceleration) at PERCLOS > 25%.

### L2
**Q: How does head pose estimation differ from eye gaze estimation, and why do production DMS systems need both?**  
A: Head pose (yaw, pitch, roll) tells where the head is pointing — measured from facial landmarks or regression CNN. Gaze direction tells where the eyes are looking — requires iris/pupil detection or a dedicated gaze CNN. Head pose alone is insufficient: a driver can look forward with the head but have eyes closed or gazing sideways without moving the head. Production DMS combines both: head pose for gross attention zone classification + eye gaze/openness for drowsiness and fine gaze direction. Continental SAFE-DAS and Seeing Machines both use this fusion.

### L3
**Q: Design a DMS system compliant with Euro NCAP 2023 and EU GSR requirements.**  
A: (1) Sensor: 940nm NIR camera (1MP) + LED illuminator, dashboard mount, <30cm from driver's face. (2) Face detection: lightweight MTCNN or RetinaFace, 30fps, <5ms. (3) Landmark detection: 68 or 98-point face landmark CNN for EAR + head pose inputs. (4) Head pose: HopeNet INT8, ~1ms. (5) Eye state: EAR + PERCLOS over 60s rolling window. (6) Distraction: gaze zone classifier + phone detection (separate YOLOv5n, 'mobile phone' class). (7) State machine: AWAKE / WARNING_1 / WARNING_2 / EMERGENCY with timing parameters per ECE R79 Amendment 6 and Euro NCAP 2023 DMS protocol. (8) Output: AUTOSAR COM signal to HMI ECU + powertrain torque reduction at EMERGENCY state. (9) ASIL-B: DMS is safety function for L3 hands-off; ISO 26262 decomposition required; redundant eye/head monitoring channels.
