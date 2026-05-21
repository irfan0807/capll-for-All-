"""
05_DEEP_LEARNING — Production ADAS Neural Networks
CNN, YOLO, Transformers, Segmentation for Automotive AI
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Tuple, Dict, Optional

# ============================================================================
# 1. BACKBONE — MobileNetV3-Small (ECU-deployable CNN)
# ============================================================================

class DepthwiseSeparableConv(nn.Module):
    """Depthwise separable convolution — 8× fewer ops than standard conv.
    Core building block of MobileNet, EfficientNet.
    Used in ECU-deployed CNNs (TDA4VM, Ethos-U65)."""
    
    def __init__(self, in_ch: int, out_ch: int, stride: int = 1):
        super().__init__()
        # Depthwise: one filter per input channel
        self.dw = nn.Conv2d(in_ch, in_ch, 3, stride=stride, padding=1,
                            groups=in_ch, bias=False)
        # Pointwise: mix channels
        self.pw = nn.Conv2d(in_ch, out_ch, 1, bias=False)
        self.bn1 = nn.BatchNorm2d(in_ch)
        self.bn2 = nn.BatchNorm2d(out_ch)
        
    def forward(self, x):
        x = F.relu6(self.bn1(self.dw(x)))
        return F.relu6(self.bn2(self.pw(x)))


class InvertedResidual(nn.Module):
    """MobileNetV2/V3 inverted residual block.
    Expand → Depthwise → Project (squeeze)
    Expand ratio = 6 is standard; 2-4 for more aggressive compression."""
    
    def __init__(self, in_ch: int, out_ch: int, stride: int, expand: int = 6):
        super().__init__()
        mid_ch = in_ch * expand
        self.use_skip = (stride == 1 and in_ch == out_ch)
        
        layers = []
        if expand != 1:
            layers += [nn.Conv2d(in_ch, mid_ch, 1, bias=False),
                       nn.BatchNorm2d(mid_ch), nn.ReLU6(inplace=True)]
        layers += [
            nn.Conv2d(mid_ch, mid_ch, 3, stride=stride, padding=1,
                      groups=mid_ch, bias=False),
            nn.BatchNorm2d(mid_ch), nn.ReLU6(inplace=True),
            nn.Conv2d(mid_ch, out_ch, 1, bias=False),
            nn.BatchNorm2d(out_ch)
        ]
        self.conv = nn.Sequential(*layers)
    
    def forward(self, x):
        return x + self.conv(x) if self.use_skip else self.conv(x)


class MobileNetV2Backbone(nn.Module):
    """MobileNetV2 backbone for ADAS perception.
    Used as backbone in: SSD-MobileNet (TFLite automotive), EfficientDet-D0.
    At 640×384 input: ~2.5M params, ~0.9 GFLOPs."""
    
    def __init__(self):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(3, 32, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(32), nn.ReLU6(inplace=True)
        )
        # [expand, out_ch, num_blocks, stride]
        config = [
            [1,  16, 1, 1],
            [6,  24, 2, 2],  # /4
            [6,  32, 3, 2],  # /8
            [6,  64, 4, 2],  # /16
            [6,  96, 3, 1],
            [6, 160, 3, 2],  # /32
            [6, 320, 1, 1],
        ]
        self.layers = nn.ModuleList()
        in_ch = 32
        for expand, out_ch, n, s in config:
            blocks = []
            for i in range(n):
                blocks.append(InvertedResidual(in_ch, out_ch,
                                               stride=s if i==0 else 1,
                                               expand=expand))
                in_ch = out_ch
            self.layers.append(nn.Sequential(*blocks))
        
        # Feature pyramid outputs: C3 (/8), C4 (/16), C5 (/32)
        self.c3_idx, self.c4_idx, self.c5_idx = 3, 5, 6
    
    def forward(self, x) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        x = self.stem(x)
        features = []
        for layer in self.layers:
            x = layer(x)
            features.append(x)
        return features[self.c3_idx], features[self.c4_idx], features[self.c5_idx]

# ============================================================================
# 2. FEATURE PYRAMID NETWORK (FPN) — Multi-scale detection
# ============================================================================

class FPN(nn.Module):
    """Feature Pyramid Network — multi-scale feature fusion.
    Detects small objects (pedestrians far away) using high-resolution features
    and large objects (trucks close-up) using low-resolution features.
    Critical for automotive: pedestrians can be 20-200px tall in the image."""
    
    def __init__(self, in_channels: Tuple[int,int,int] = (32, 96, 320),
                 out_ch: int = 128):
        super().__init__()
        c3, c4, c5 = in_channels
        # Lateral connections (1×1 conv to unify channel counts)
        self.lat5 = nn.Conv2d(c5, out_ch, 1)
        self.lat4 = nn.Conv2d(c4, out_ch, 1)
        self.lat3 = nn.Conv2d(c3, out_ch, 1)
        # Output smoothing (3×3 conv after upsampling)
        self.out5 = nn.Conv2d(out_ch, out_ch, 3, padding=1)
        self.out4 = nn.Conv2d(out_ch, out_ch, 3, padding=1)
        self.out3 = nn.Conv2d(out_ch, out_ch, 3, padding=1)
    
    def forward(self, c3, c4, c5):
        p5 = self.lat5(c5)
        p4 = self.lat4(c4) + F.interpolate(p5, scale_factor=2, mode='nearest')
        p3 = self.lat3(c3) + F.interpolate(p4, scale_factor=2, mode='nearest')
        return self.out3(p3), self.out4(p4), self.out5(p5)  # P3, P4, P5

# ============================================================================
# 3. YOLO-STYLE DETECTION HEAD
# ============================================================================

class YoloHead(nn.Module):
    """Single-scale YOLO detection head.
    Predicts: (tx, ty, tw, th, obj_conf, class_probs) per anchor.
    
    For automotive: 3 anchors per scale calibrated to typical object sizes:
    P3 (/8):  small anchors  → far pedestrians, small vehicles
    P4 (/16): medium anchors → typical vehicles at 30-80m
    P5 (/32): large anchors  → close vehicles, trucks
    """
    
    def __init__(self, in_ch: int, num_anchors: int = 3, num_classes: int = 5):
        super().__init__()
        # 5 classes: car, truck, bus, pedestrian, cyclist (KITTI-like)
        out_ch = num_anchors * (5 + num_classes)  # 5 = tx,ty,tw,th,obj
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, in_ch*2, 3, padding=1, bias=False),
            nn.BatchNorm2d(in_ch*2),
            nn.LeakyReLU(0.1, inplace=True),
            nn.Conv2d(in_ch*2, out_ch, 1)
        )
        self.num_anchors = num_anchors
        self.num_classes = num_classes
    
    def forward(self, x):
        # x: (B, C, H, W) → (B, A, H, W, 5+num_classes)
        out = self.conv(x)
        B, _, H, W = out.shape
        return out.view(B, self.num_anchors, 5 + self.num_classes, H, W)\
                  .permute(0, 1, 3, 4, 2)  # (B, A, H, W, 5+nc)

# ============================================================================
# 4. FULL YOLO-STYLE DETECTOR
# ============================================================================

class AdasDetector(nn.Module):
    """Production ADAS object detector.
    Architecture: MobileNetV2 + FPN + 3-scale YOLO heads.
    Target: real-time on TDA4VM (12ms @ INT8) or Jetson Orin (3ms @ FP16).
    
    Classes: Car, Truck, Pedestrian, Cyclist, Motorbike
    """
    
    def __init__(self, num_classes: int = 5, anchors_per_scale: int = 3):
        super().__init__()
        self.backbone = MobileNetV2Backbone()
        self.fpn      = FPN(in_channels=(64, 96, 320), out_ch=128)
        
        self.head_p3 = YoloHead(128, anchors_per_scale, num_classes)
        self.head_p4 = YoloHead(128, anchors_per_scale, num_classes)
        self.head_p5 = YoloHead(128, anchors_per_scale, num_classes)
        
        # Anchors calibrated to KITTI dataset
        # Format: (width_px, height_px) at 640×384 input
        self.anchors = {
            'p3': [(15, 30), (25, 55), (40, 45)],    # small (pedestrians far)
            'p4': [(60, 50), (80, 100), (120, 80)],   # medium (typical cars)
            'p5': [(150, 100), (200, 150), (300, 200)] # large (close vehicles)
        }
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor,...]:
        c3, c4, c5 = self.backbone(x)
        p3, p4, p5 = self.fpn(c3, c4, c5)
        return self.head_p3(p3), self.head_p4(p4), self.head_p5(p5)
    
    def count_params(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

# ============================================================================
# 5. NON-MAXIMUM SUPPRESSION (NMS)
# ============================================================================

def non_max_suppression(boxes: torch.Tensor, scores: torch.Tensor,
                         iou_threshold: float = 0.45) -> List[int]:
    """Vectorised NMS — removes duplicate detections.
    Returns indices of kept boxes.
    
    Production note: on TensorRT, use batched NMS plugin (~10× faster than Python).
    """
    if len(boxes) == 0:
        return []
    
    x1, y1, x2, y2 = boxes[:,0], boxes[:,1], boxes[:,2], boxes[:,3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort(descending=True)
    
    keep = []
    while len(order) > 0:
        i = order[0].item()
        keep.append(i)
        
        if len(order) == 1:
            break
        
        # Compute IoU with all remaining boxes
        rest = order[1:]
        ix1 = torch.max(x1[i], x1[rest])
        iy1 = torch.max(y1[i], y1[rest])
        ix2 = torch.min(x2[i], x2[rest])
        iy2 = torch.min(y2[i], y2[rest])
        
        inter = (ix2 - ix1).clamp(0) * (iy2 - iy1).clamp(0)
        union = areas[i] + areas[rest] - inter
        iou   = inter / (union + 1e-6)
        
        order = rest[iou <= iou_threshold]
    
    return keep

# ============================================================================
# 6. LANE SEGMENTATION — SEMANTIC SEGMENTATION HEAD
# ============================================================================

class LaneSegmentationHead(nn.Module):
    """Lightweight lane segmentation decoder.
    Takes P3 features from FPN, upsamples to full resolution.
    Output: binary mask (lane / not-lane) per pixel.
    
    Alternative to polynomial-fitting classical CV — more robust to occlusion.
    Used in Tesla FSD bird's-eye view (BEV) network."""
    
    def __init__(self, in_ch: int = 128, num_classes: int = 3):
        # 3 classes: background, left lane, right lane
        super().__init__()
        self.decode = nn.Sequential(
            nn.Conv2d(in_ch, 64, 3, padding=1),
            nn.BatchNorm2d(64), nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False),
            nn.Conv2d(64, 32, 3, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False),
            nn.Conv2d(32, 16, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False),
            nn.Conv2d(16, num_classes, 1)  # (B, num_classes, H, W) logits
        )
    
    def forward(self, p3: torch.Tensor) -> torch.Tensor:
        return self.decode(p3)  # (B, 3, H_orig, W_orig)

# ============================================================================
# 7. TRANSFORMER ATTENTION — For trajectory prediction
# ============================================================================

class VehicleAttention(nn.Module):
    """Multi-head attention for vehicle interaction modelling.
    Used in: trajectory prediction (Waymo Prediction Challenge winner).
    Input: N vehicle states [x, y, vx, vy, heading] at T timesteps.
    Each vehicle attends to all other vehicles → models social interactions."""
    
    def __init__(self, d_model: int = 64, nheads: int = 4):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, nheads, batch_first=True)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_model * 4), nn.GELU(),
            nn.Linear(d_model * 4, d_model)
        )
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, N_vehicles, d_model)
        attn_out, _ = self.attn(x, x, x)  # Self-attention
        x = self.norm1(x + attn_out)       # Residual + LayerNorm
        x = self.norm2(x + self.ffn(x))
        return x

# ============================================================================
# 8. MODEL SUMMARY + DEMO
# ============================================================================

if __name__ == "__main__":
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}\n")
    
    # Create model
    model = AdasDetector(num_classes=5).to(device)
    print(f"AdasDetector parameters: {model.count_params():,}")
    
    # Simulate a batch of 4 ADAS frames at 640×384
    dummy_input = torch.randn(4, 3, 384, 640).to(device)
    
    with torch.no_grad():
        p3_out, p4_out, p5_out = model(dummy_input)
    
    print(f"\nOutput shapes (B, Anchors, H, W, 10):")
    print(f"  P3 (stride 8):  {p3_out.shape}")
    print(f"  P4 (stride 16): {p4_out.shape}")
    print(f"  P5 (stride 32): {p5_out.shape}")
    
    # NMS demo
    test_boxes = torch.tensor([
        [100, 100, 200, 200],
        [105, 105, 205, 205],  # High IoU with first box → should be suppressed
        [300, 100, 400, 200],  # Different location → kept
    ], dtype=torch.float32)
    test_scores = torch.tensor([0.9, 0.85, 0.7])
    kept = non_max_suppression(test_boxes, test_scores, iou_threshold=0.45)
    print(f"\nNMS: {len(test_boxes)} boxes → {len(kept)} kept: indices {kept}")
    
    # Lane segmentation
    lane_head = LaneSegmentationHead(in_ch=128).to(device)
    dummy_p3 = torch.randn(1, 128, 48, 80).to(device)
    seg_out = lane_head(dummy_p3)
    print(f"\nLane seg output: {seg_out.shape}  (B, 3_classes, H, W)")
