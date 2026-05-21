# 05 — Deep Learning for ADAS

## Overview
CNN architectures, loss functions, training strategies, and deployment for automotive perception networks. Covers the full pipeline from MobileNet backbone to FPN, detection heads, and segmentation decoders used at Tesla, NVIDIA, and Mobileye.

**Key reference architectures:**
- Tesla FSD: HydraNet (single backbone, 48 heads) — BEV, depth, lanes, objects
- Mobileye RSS: multi-task CNN + probabilistic safety layer
- NVIDIA DRIVE AV: DRIVENET (object) + DRIVEMAP (BEV) + LaneNet
- Waymo: PointPillars (LiDAR) + camera fusion transformer

---

## 1. Why CNN for ADAS?

| Method | Accuracy | Latency | Edge Deployable | Handles Occlusion |
|--------|---------|---------|-----------------|-------------------|
| Classical CV (Sobel + Hough) | Low | ~1ms | Yes | Poor |
| ML on features (SVM/RF) | Medium | ~1ms | Yes | Medium |
| Shallow CNN (5-10 layers) | Good | 5-15ms | Yes | Good |
| Deep CNN (ResNet-50) | Very good | 20-50ms | Limited | Very good |
| Transformer (ViT) | Best | 50-200ms | No (today) | Excellent |

**Decision: Use MobileNetV2/V3 backbone for production ECU, ResNet-50 for server-side validation.**

---

## 2. Key Building Blocks

### Depthwise Separable Convolution (MobileNet)
```
Standard conv: H×W×Cin×Cout → Cin×Cout×kH×kW FLOPs
Depthwise separable: (Cin×kH×kW) + (Cin×Cout) FLOPs  →  8-9× reduction at k=3

Used by: MobileNetV2/V3, EfficientNet, YOLO-Nano
```

### Inverted Residual Block:
```
Input (C) → Expand ×6 (6C) → Depthwise → Project back (C') → + skip
                                                                ↑
                                              Only if stride=1 and C=C'
```

### Feature Pyramid Network (FPN):
```
C3 (/8)  ──── lat3 ──────────────────────────────── P3 → small objects
                                                 ↗
C4 (/16) ──── lat4 ──── + ─── out4 ─── P4 → medium objects
                        ↑ upsample x2
C5 (/32) ──── lat5 ─────────── P5 → large objects
```

---

## 3. Loss Functions for ADAS

### Focal Loss (Object Detection)
```python
def focal_loss(pred_logits, targets, alpha=0.25, gamma=2.0):
    """Focal loss: reduces loss contribution from easy negatives.
    Critical for ADAS: 99%+ of anchor boxes are background.
    Without focal loss, model predicts 'background' for everything."""
    p = torch.sigmoid(pred_logits)
    ce = F.binary_cross_entropy_with_logits(pred_logits, targets, reduction='none')
    p_t = p * targets + (1 - p) * (1 - targets)           # pt = p if y=1 else 1-p
    alpha_t = alpha * targets + (1 - alpha) * (1 - targets)
    fl = alpha_t * (1 - p_t) ** gamma * ce
    return fl.mean()
```

### IoU Loss (Bounding Box Regression)
```python
def iou_loss(pred_boxes, target_boxes):
    """IoU loss for bounding box regression.
    Better than L1/L2: scale-invariant, directly optimises overlap metric."""
    inter_x1 = torch.max(pred_boxes[:,0], target_boxes[:,0])
    inter_y1 = torch.max(pred_boxes[:,1], target_boxes[:,1])
    inter_x2 = torch.min(pred_boxes[:,2], target_boxes[:,2])
    inter_y2 = torch.min(pred_boxes[:,3], target_boxes[:,3])
    
    inter = (inter_x2 - inter_x1).clamp(0) * (inter_y2 - inter_y1).clamp(0)
    area_p = (pred_boxes[:,2]-pred_boxes[:,0]) * (pred_boxes[:,3]-pred_boxes[:,1])
    area_t = (target_boxes[:,2]-target_boxes[:,0]) * (target_boxes[:,3]-target_boxes[:,1])
    union = area_p + area_t - inter
    iou = inter / (union + 1e-6)
    return 1.0 - iou.mean()
```

### Smooth L1 Loss (Lane Regression)
```python
# Smooth L1: L2 for small errors (smooth gradients near 0)
#            L1 for large errors (robust to outliers — lane marking occlusions)
loss = F.smooth_l1_loss(predicted_offset, target_offset, beta=0.1)
```

---

## 4. Multi-Task Learning (Tesla HydraNet Pattern)

```python
class HydraNet(nn.Module):
    """Single backbone, multiple task heads.
    Reduces total parameters vs separate networks per task.
    Shared features: BEV transformation, depth, segmentation share backbone."""
    
    def __init__(self):
        super().__init__()
        self.backbone = MobileNetV2Backbone()
        self.fpn      = FPN()
        
        # Detection head (object bounding boxes)
        self.det_head = YoloHead(128, num_classes=5)
        # Lane segmentation head
        self.lane_head = LaneSegmentationHead(128)
        # Depth estimation head
        self.depth_head = nn.Sequential(
            nn.Conv2d(128, 64, 3, padding=1), nn.ReLU(),
            nn.Upsample(scale_factor=8, mode='bilinear', align_corners=False),
            nn.Conv2d(64, 1, 1), nn.Sigmoid()  # normalised depth
        )
    
    def forward(self, x):
        c3, c4, c5 = self.backbone(x)
        p3, p4, p5 = self.fpn(c3, c4, c5)
        return {
            'det':   self.det_head(p4),      # Medium-scale detection
            'lane':  self.lane_head(p3),     # High-res lane seg
            'depth': self.depth_head(p3)     # Per-pixel depth
        }

# Multi-task loss (weighted sum)
def multitask_loss(outputs, targets, weights=(1.0, 2.0, 0.5)):
    det_loss   = focal_loss(outputs['det'],   targets['det'])
    lane_loss  = F.cross_entropy(outputs['lane'], targets['lane'])
    depth_loss = F.smooth_l1_loss(outputs['depth'], targets['depth'])
    return (weights[0] * det_loss +
            weights[1] * lane_loss +
            weights[2] * depth_loss)
```

---

## 5. Transfer Learning for Automotive

```python
# Start from ImageNet pretrained backbone (trained on 1.28M images)
# Fine-tune on KITTI/nuScenes (typically 10-50k images)

import torchvision.models as models

backbone = models.mobilenet_v2(pretrained=True)

# Freeze early layers (low-level features are domain-agnostic)
for name, param in backbone.features.named_parameters():
    layer_idx = int(name.split('.')[0])
    if layer_idx < 10:
        param.requires_grad = False  # Freeze first 10 blocks

# Learning rate schedule: lower LR for pretrained layers
optimizer = torch.optim.AdamW([
    {'params': [p for n,p in backbone.named_parameters()
                if 'features' in n], 'lr': 1e-4},   # Pretrained: low LR
    {'params': [p for n,p in backbone.named_parameters()
                if 'features' not in n], 'lr': 1e-3}  # New heads: higher LR
], weight_decay=1e-4)
```

---

## 6. Batch Normalisation Issues in ADAS

```python
# PROBLEM: BatchNorm statistics depend on batch size
# At inference (batch=1), BN uses running mean/std from training
# On ECU: batch size = 1 → BN behaves differently than during training

# SOLUTION 1: Switch to GroupNorm (not batch-dependent)
nn.GroupNorm(num_groups=32, num_channels=128)

# SOLUTION 2: Fold BN into Conv post-training (most common in TensorRT)
# Conv weight: W_new = W / sqrt(var + eps) * gamma
# Conv bias:   b_new = (b - mean) / sqrt(var + eps) * gamma + beta
# Result: zero-overhead BN at inference

# SOLUTION 3: Use frozen BN with running stats (production default)
model.eval()   # ALWAYS call before inference — BN uses running stats
with torch.no_grad():
    output = model(input)
```

---

## 7. Data Augmentation Strategy

### Automotive-specific augmentation sequence:
```python
import albumentations as A

train_aug = A.Compose([
    # Photometric: simulate varying lighting/weather
    A.RandomBrightnessContrast(0.3, 0.3, p=0.5),
    A.RandomFog(fog_coef_lower=0.1, fog_coef_upper=0.4, p=0.2),
    A.RandomRain(p=0.15),
    A.RandomSunFlare(p=0.1),
    A.GaussNoise(var_limit=(10,50), p=0.3),
    A.MotionBlur(blur_limit=7, p=0.2),       # Camera motion shake
    
    # Geometric: limited — keep perspective realistic
    A.HorizontalFlip(p=0.5),                 # Road is left-right symmetric
    # DO NOT: vertical flip, large rotations — breaks lane topology
    
    # Resize to network input
    A.Resize(384, 640),
    A.Normalize(mean=(0.485,0.456,0.406), std=(0.229,0.224,0.225)),
], bbox_params=A.BboxParams(format='pascal_voc'))
```

---

## 8. Training Tips (ADAS-specific)

1. **Gradient accumulation** — simulate large batch without GPU memory:
   ```python
   ACCUM_STEPS = 8   # Effective batch = actual_batch × 8
   for i, (imgs, targets) in enumerate(loader):
       loss = model(imgs) / ACCUM_STEPS
       loss.backward()
       if (i+1) % ACCUM_STEPS == 0:
           optimizer.step(); optimizer.zero_grad()
   ```

2. **Curriculum learning** — start with easy examples (clear weather, day), add hard examples (night, rain, fog) after 50% of training.

3. **Hard negative mining** — sample 3× more background patches near object boundaries.

4. **Exponential Moving Average (EMA)** — maintain EMA of model weights for more stable predictions:
   ```python
   ema_model = copy.deepcopy(model)
   for ema_p, p in zip(ema_model.parameters(), model.parameters()):
       ema_p.data = 0.999 * ema_p.data + 0.001 * p.data
   ```

---

## 9. Evaluation Metrics

| Task | Metric | Production Target |
|------|--------|-------------------|
| Object detection | mAP@IoU=0.5 | >0.85 on KITTI |
| Lane detection | Accuracy@0.5 IoU | >0.95 |
| Depth estimation | AbsRel, SqRel | AbsRel < 0.1 |
| Segmentation | mIoU | >0.75 |
| FP rate (false detections) | FP/km | < 0.1 for AEB |

---

## 10. Interview Q&A

### L1
**Q: What is the vanishing gradient problem and how does ResNet solve it?**  
A: In deep networks, gradients during backpropagation shrink by the chain rule multiplication of small numbers, making early layers train very slowly. ResNet adds identity skip connections (residual connections): `output = F(x) + x`. Gradients flow directly through the shortcut, bypassing the problematic multiplication chain.

**Q: Why use BatchNorm after Conv in ADAS networks?**  
A: BatchNorm normalises layer inputs to zero mean, unit variance across the batch, which: (1) reduces internal covariate shift → faster training; (2) allows higher learning rates; (3) acts as mild regulariser. In ADAS, it also makes the network robust to varying lighting since photometric variations affect activation magnitudes.

### L2
**Q: Explain Focal Loss and why it's important for object detection in ADAS.**  
A: In a 640×384 image with 3 anchor scales, there are ~20,000 candidate anchor boxes but typically only 5-30 actual objects. Standard cross-entropy loss is dominated by the 19,970+ background anchors (easy negatives). Focal Loss = `-(1-p_t)^γ × log(p_t)`: the factor `(1-p_t)^γ` downweights easy examples (high p_t). With γ=2, a 99% confidence correct prediction contributes ~0.0001× its original loss. Result: training focuses on the rare hard positives.

**Q: What is the trade-off between anchor-based (YOLO) and anchor-free (FCOS/CenterNet) detectors?**  
A: Anchor-based: predicts offsets from predefined boxes, requires careful anchor design per dataset, well-understood and optimised for TensorRT. Anchor-free: predicts objects from centre points or feature map locations, simpler hyperparameters, better for unusual aspect ratios (long trucks, cyclists). In production ADAS I prefer anchor-based for predictable TensorRT optimisation and validated performance on KITTI/nuScenes.

### L3
**Q: How does Tesla's HydraNet differ from training separate networks per task?**  
A: HydraNet shares the entire backbone (and FPN) across all 48 tasks. Benefits: (1) 10× fewer total parameters vs 48 separate networks; (2) Shared representation learning — lane features benefit object depth estimation; (3) Single inference pass for all tasks — critical for <20ms total latency; (4) Feature reuse reduces memory bandwidth on ECU. Challenge: gradient interference between tasks (loss balancing, task-specific learning rate scheduling). Solution: uncertainty weighting (Kendall et al.) or gradient surgery.

---

## Files
- [adas_nn_models.py](adas_nn_models.py) — MobileNetV2, FPN, YoloHead, LaneSegNet, NMS
