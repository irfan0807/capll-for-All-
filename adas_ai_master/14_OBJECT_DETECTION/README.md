# 14 — Object Detection for ADAS

## Overview
2D object detection pipeline for ADAS: YOLO-style anchored detectors, NMS decoding, mAP evaluation, and production deployment. Covers pedestrian, vehicle, traffic sign, and traffic light detection.

---

## 1. Object Detection Methods Comparison

| Method | Speed (GPU) | mAP (COCO) | Anchors | Production Use |
|--------|------------|-----------|--------|---------------|
| YOLOv5s | 6ms | 37.4% | Anchor-based | Bosch MPC, Continental |
| YOLOv8s | 4ms | 44.9% | Anchor-free | 2023+ ADAS ECUs |
| RT-DETR-S | 9ms | 48.1% | Anchor-free (Transformer) | Premium AD platforms |
| EfficientDet-D0 | 10ms | 34.6% | Anchor-based | Automotive SoC |
| SSD-MobileNetV2 | 2ms | 22.1% | Anchor-based | Legacy ADAS |

---

## 2. Anchor Boxes — Design Rationale

Anchor boxes encode expected aspect ratios. ADAS-specific anchors differ from COCO:

```python
# COCO trained anchors (for general objects):
# [(10,13), (16,30), (33,23)] for small scale
# These assume small objects of various shapes

# ADAS-specific anchors (cars, trucks, pedestrians on road):
ADAS_ANCHORS = {
    'P3_8x':  [(30,70), (50,45), (90,30)],    # Pedestrians, cyclists (tall/narrow)
    'P4_16x': [(100,60),(160,90),(120,150)],   # Cars at medium range
    'P5_32x': [(200,90),(280,150),(350,250)],  # Trucks, buses, large vehicles
}
```

**Anchor-free trend (2022+):** YOLOv8, RT-DETR, and DINO use anchor-free detection (FCOS-style centerness or DETR object queries) — removes anchor engineering complexity.

---

## 3. YOLO Architecture for ADAS

```
Input (640×384×3)
       │
   Backbone (CSPDarknet / MobileNetV2 / EfficientNet)
       │
    C3(80×48)  C4(40×24)  C5(20×12)
       │           │           │
       └─────────FPN──────────┘
       │           │           │
   P3(80×48)  P4(40×24)  P5(20×12)
       │           │           │
   Head×3      Head×3      Head×3
   (3 anchors) (3 anchors) (3 anchors)
       │           │           │
   Decode ──────────────────────► NMS ──► Detection list
```

---

## 4. Loss Functions

**YOLO training loss:**

$$L_{total} = \lambda_{box} L_{box} + \lambda_{obj} L_{obj} + \lambda_{cls} L_{cls}$$

**Box regression:** CIoU (Complete IoU) — penalises centre distance, aspect ratio, and overlap:

$$\text{CIoU} = \text{IoU} - \frac{\rho^2(b, b^{gt})}{c^2} - \alpha v$$

where $\rho$ = Euclidean distance of centres, c = diagonal of enclosing box, $v$ = aspect ratio consistency.

**Classification:** Binary cross-entropy (not softmax — allows multi-label)

**Objectness:** Focal loss (handles class imbalance: mostly background)

```python
import torch
import torch.nn.functional as F

def ciou_loss(pred_boxes: torch.Tensor, 
               gt_boxes: torch.Tensor) -> torch.Tensor:
    """CIoU loss for bounding box regression.
    pred_boxes, gt_boxes: (N, 4) [x1, y1, x2, y2]"""
    # Intersection
    ix1 = torch.max(pred_boxes[:,0], gt_boxes[:,0])
    iy1 = torch.max(pred_boxes[:,1], gt_boxes[:,1])
    ix2 = torch.min(pred_boxes[:,2], gt_boxes[:,2])
    iy2 = torch.min(pred_boxes[:,3], gt_boxes[:,3])
    inter = (ix2-ix1).clamp(0) * (iy2-iy1).clamp(0)
    
    area_pred = (pred_boxes[:,2]-pred_boxes[:,0]) * (pred_boxes[:,3]-pred_boxes[:,1])
    area_gt   = (gt_boxes[:,2]-gt_boxes[:,0])   * (gt_boxes[:,3]-gt_boxes[:,1])
    union     = area_pred + area_gt - inter
    iou       = inter / (union + 1e-6)
    
    # Centre distance penalty
    cx_p = (pred_boxes[:,0]+pred_boxes[:,2])/2; cy_p = (pred_boxes[:,1]+pred_boxes[:,3])/2
    cx_g = (gt_boxes[:,0]+gt_boxes[:,2])/2;   cy_g = (gt_boxes[:,1]+gt_boxes[:,3])/2
    rho2 = (cx_p-cx_g)**2 + (cy_p-cy_g)**2
    
    # Enclosing box diagonal
    ecx1 = torch.min(pred_boxes[:,0], gt_boxes[:,0])
    ecy1 = torch.min(pred_boxes[:,1], gt_boxes[:,1])
    ecx2 = torch.max(pred_boxes[:,2], gt_boxes[:,2])
    ecy2 = torch.max(pred_boxes[:,3], gt_boxes[:,3])
    c2 = (ecx2-ecx1)**2 + (ecy2-ecy1)**2 + 1e-6
    
    # Aspect ratio consistency
    w_p = pred_boxes[:,2]-pred_boxes[:,0]; h_p = pred_boxes[:,3]-pred_boxes[:,1]
    w_g = gt_boxes[:,2]-gt_boxes[:,0];   h_g = gt_boxes[:,3]-gt_boxes[:,1]
    v   = (4/torch.pi**2) * (torch.atan(w_g/(h_g+1e-6)) - torch.atan(w_p/(h_p+1e-6)))**2
    alpha = v / (1 - iou + v + 1e-6)
    
    ciou = iou - rho2/c2 - alpha*v
    return (1 - ciou).mean()
```

---

## 5. Data Augmentation Strategy

```python
import albumentations as A

train_aug = A.Compose([
    A.RandomSizedBBoxSafeCrop(384, 640, p=0.5),
    A.HorizontalFlip(p=0.5),
    A.ColorJitter(brightness=0.4, contrast=0.4,
                  saturation=0.3, hue=0.1, p=0.5),
    A.GaussNoise(var_limit=(10,50), p=0.3),
    A.RandomRain(p=0.2),    # SOTIF weather
    A.RandomFog(fog_coef_lower=0.1, fog_coef_upper=0.4, p=0.15),
    A.RandomShadow(p=0.3),  # Tree shadows, bridge shadows
    A.Mosaic(p=0.5),        # YOLOv5-style mosaic (not native in albumentations — custom)
], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))
```

---

## 6. Metrics

| Metric | Formula | Notes |
|--------|---------|-------|
| mAP@0.5 | Mean AP at IoU≥0.5 | Standard benchmark |
| mAP@0.5:0.95 | Mean AP, 10 IoU thresholds | COCO standard (harder) |
| FPS | Frames per second | Real-time: ≥30fps camera rate |
| Recall@FPPI | Recall at fixed FP-per-image | Pedestrian detection benchmark |

**Production gate criteria (typical Tier-1):**
- Pedestrian recall @ 0.3 FPPI: ≥97% (AEB safety requirement)
- Car AP@0.5: ≥92%
- Night / rain: ≤5% degradation vs daytime

---

## 7. Interview Q&A

### L1
**Q: What is mAP and why use IoU thresholds?**  
A: mAP (mean Average Precision) = average of AP scores across all detection classes. AP measures the area under the precision-recall curve for each class. IoU threshold defines what counts as a correct detection — at IoU=0.5 a predicted box must overlap the ground truth by ≥50%. mAP@0.5:0.95 averages over IoU 0.5, 0.55, …, 0.95 — rewards precise localisation. For AEB, a loose IoU@0.5 threshold is insufficient — we care about precise distance, so mAP@0.75 matters.

### L2
**Q: Why is focal loss preferred over cross-entropy for YOLO objectness head?**  
A: In a 640×384 image with 12-anchor feature maps, there are ~20,000 anchor boxes but only ~10-20 contain objects. 99.9% of anchors are background. Standard binary cross-entropy is dominated by easy background samples (very low loss, very large count) — gradients from rare positive samples are overwhelmed. Focal loss: $FL = -(1-p_t)^\gamma \log(p_t)$ with $\gamma=2$ down-weights easy negatives by $(1-p_t)^2$ factor. At $p_t=0.99$ (easy background), weight = 0.0001. Focuses training on hard positives and hard negatives.

### L3
**Q: Design an object detection deployment pipeline for a production AEB ECU (TDA4VM, 20ms budget).**  
A: (1) Model selection: YOLOv5s (6ms on A72 at INT8 via TI Deep Learning Library — TIDL). (2) Quantisation: TI TIDL-RT INT8 calibration with 500-frame representative dataset; post-training quantisation (PTQ) acceptable for YOLOv5 with <1% mAP drop. (3) NMS: run on TDA4VM ARM A72 core (C code, ~0.3ms for 500 detections). (4) Pre-processing: TDA4VM ISP + hardware resize/normalise in 2ms. (5) Budget allocation: 2ms pre-process + 6ms NN + 0.5ms NMS + 1ms decode = 9.5ms. Remaining: 10ms for fusion+AEB decision. (6) Fallback: if frame latency exceeds 15ms, skip NMS (output raw top-K by score without suppression) — documented as degraded mode in FMEA. (7) Safety: use ASIL decomposition — camera detection + radar confirmation before AEB; TIDL tool generates safety manual for functional safety certification.

---

## Files
- [object_detection.py](object_detection.py) — NMS, YOLO decoder, mAP evaluation
