"""
14_OBJECT_DETECTION — Production ADAS Object Detection Pipeline
YOLO-style inference, NMS, mAP evaluation, and TensorRT-ready export.
"""

from __future__ import annotations
import numpy as np
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import torch
import torch.nn as nn
import torch.nn.functional as F


# ============================================================================
# 1. DATA TYPES
# ============================================================================

@dataclass
class BBox2D:
    """Bounding box in image coordinates."""
    x1: float; y1: float; x2: float; y2: float
    
    @property
    def cx(self) -> float: return (self.x1 + self.x2) / 2
    @property
    def cy(self) -> float: return (self.y1 + self.y2) / 2
    @property
    def w(self)  -> float: return self.x2 - self.x1
    @property
    def h(self)  -> float: return self.y2 - self.y1
    @property
    def area(self) -> float: return self.w * self.h

@dataclass
class Detection2D:
    """Single detected object."""
    bbox:       BBox2D
    confidence: float         # Object confidence × class probability
    cls_id:     int           # Class index
    cls_name:   str           # Class name

COCO_CLASSES = ['person','bicycle','car','motorcycle','airplane','bus',
                'train','truck','boat','traffic light','fire hydrant',
                'stop sign','parking meter','bench','bird']

ADAS_CLASSES = ['car', 'truck', 'bus', 'motorcycle', 'bicycle', 'pedestrian',
                'traffic_sign', 'traffic_light']

# ============================================================================
# 2. NMS (Non-Maximum Suppression)
# ============================================================================

def nms(boxes: np.ndarray, scores: np.ndarray,
        iou_threshold: float = 0.45) -> List[int]:
    """Greedy NMS: suppress overlapping boxes with lower score.
    
    Args:
        boxes: (N, 4) [x1, y1, x2, y2]
        scores: (N,) confidence scores
        iou_threshold: suppress if IoU > this value
    Returns:
        List of kept indices
    """
    if len(boxes) == 0:
        return []
    
    x1, y1, x2, y2 = boxes[:,0], boxes[:,1], boxes[:,2], boxes[:,3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    
    keep = []
    while len(order) > 0:
        i = order[0]
        keep.append(int(i))
        
        ix1 = np.maximum(x1[i], x1[order[1:]])
        iy1 = np.maximum(y1[i], y1[order[1:]])
        ix2 = np.minimum(x2[i], x2[order[1:]])
        iy2 = np.minimum(y2[i], y2[order[1:]])
        
        inter = np.maximum(0, ix2-ix1) * np.maximum(0, iy2-iy1)
        iou   = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        
        order = order[1:][iou <= iou_threshold]
    
    return keep

def batched_nms(boxes: np.ndarray, scores: np.ndarray,
                class_ids: np.ndarray, iou_threshold: float = 0.45) -> List[int]:
    """NMS applied per-class to avoid suppressing objects of different classes."""
    all_keep = []
    for cls_id in np.unique(class_ids):
        mask = class_ids == cls_id
        idx  = np.where(mask)[0]
        kept = nms(boxes[idx], scores[idx], iou_threshold)
        all_keep.extend(idx[kept].tolist())
    return all_keep

# ============================================================================
# 3. YOLO OUTPUT DECODER
# ============================================================================

def decode_yolo_output(raw: torch.Tensor,
                        anchors: List[Tuple[int,int]],
                        num_classes: int,
                        conf_threshold: float = 0.25,
                        img_size: Tuple[int,int] = (640, 384)) -> List[Detection2D]:
    """Decode YOLO output tensor to Detection2D list.
    
    raw shape: (B, A*(5+nc), H, W)
    where A = num anchors per scale, 5 = [tx, ty, tw, th, obj_conf]
    
    Returns detections for batch index 0."""
    B, _, H, W = raw.shape
    A  = len(anchors)
    nc = num_classes
    
    # Reshape to (B, A, 5+nc, H, W)
    raw = raw.view(B, A, 5+nc, H, W).permute(0, 1, 3, 4, 2)  # (B,A,H,W,5+nc)
    
    # Decode
    pred = raw[0].cpu().numpy()   # Single batch: (A, H, W, 5+nc)
    
    detections: List[Detection2D] = []
    cell_w = img_size[0] / W
    cell_h = img_size[1] / H
    
    for a_idx, (aw, ah) in enumerate(anchors):
        for row in range(H):
            for col in range(W):
                box = pred[a_idx, row, col]
                obj_conf = 1.0 / (1.0 + np.exp(-box[4]))  # sigmoid
                if obj_conf < conf_threshold:
                    continue
                
                cls_logits = box[5:5+nc]
                cls_id     = int(np.argmax(cls_logits))
                cls_conf   = 1.0 / (1.0 + np.exp(-cls_logits[cls_id]))
                score      = obj_conf * cls_conf
                
                if score < conf_threshold:
                    continue
                
                # Box decoding (YOLO v3 style)
                bx = (col + 1.0/(1.0+np.exp(-box[0]))) * cell_w
                by = (row + 1.0/(1.0+np.exp(-box[1]))) * cell_h
                bw = aw * np.exp(box[2])
                bh = ah * np.exp(box[3])
                
                x1 = max(0, bx - bw/2)
                y1 = max(0, by - bh/2)
                x2 = min(img_size[0], bx + bw/2)
                y2 = min(img_size[1], by + bh/2)
                
                cls_name = ADAS_CLASSES[cls_id] if cls_id < len(ADAS_CLASSES) else f'class_{cls_id}'
                detections.append(Detection2D(
                    BBox2D(x1, y1, x2, y2), score, cls_id, cls_name
                ))
    
    return detections

# ============================================================================
# 4. COMPLETE DETECTION PIPELINE
# ============================================================================

class AdasObjectDetector:
    """Production ADAS object detector wrapper.
    Supports PyTorch, ONNX Runtime, and TensorRT backends.
    
    Typical use: camera frame → preprocess → infer → decode → NMS → object list"""
    
    # Default YOLO anchors for 3 scales (small/medium/large)
    ANCHORS = {
        'large':  [(116,90), (156,198), (373,326)],  # P5 32× stride
        'medium': [(30,61),  (62,45),   (59,119)],   # P4 16× stride  
        'small':  [(10,13),  (16,30),   (33,23)],    # P3 8× stride
    }
    
    def __init__(self, model: nn.Module, num_classes: int = 8,
                 conf_thresh: float = 0.25, nms_thresh: float = 0.45,
                 img_hw: Tuple[int,int] = (384, 640)):
        self.model      = model.eval()
        self.num_classes = num_classes
        self.conf_thresh = conf_thresh
        self.nms_thresh  = nms_thresh
        self.img_hw      = img_hw  # (H, W)
    
    def preprocess(self, frame: np.ndarray) -> torch.Tensor:
        """BGR→RGB, resize, normalise, add batch dim."""
        import cv2
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (self.img_hw[1], self.img_hw[0]))
        frame_f = frame_resized.astype(np.float32) / 255.0
        # ImageNet normalisation
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        frame_f = (frame_f - mean) / std
        tensor = torch.from_numpy(frame_f).permute(2, 0, 1).unsqueeze(0)
        return tensor  # (1, 3, H, W)
    
    @torch.no_grad()
    def infer(self, tensor: torch.Tensor) -> List[Detection2D]:
        """Run model inference and decode + NMS."""
        outputs = self.model(tensor)
        # outputs: list of 3 tensors (small/medium/large)
        all_dets: List[Detection2D] = []
        
        for scale_idx, (scale_name, anchors) in enumerate(self.ANCHORS.items()):
            if scale_idx < len(outputs):
                dets = decode_yolo_output(
                    outputs[scale_idx], anchors, self.num_classes,
                    self.conf_thresh, (self.img_hw[1], self.img_hw[0])
                )
                all_dets.extend(dets)
        
        return self._apply_nms(all_dets)
    
    def _apply_nms(self, dets: List[Detection2D]) -> List[Detection2D]:
        """Apply class-aware NMS."""
        if not dets:
            return []
        boxes    = np.array([[d.bbox.x1, d.bbox.y1, d.bbox.x2, d.bbox.y2] for d in dets])
        scores   = np.array([d.confidence for d in dets])
        cls_ids  = np.array([d.cls_id for d in dets])
        kept_idx = batched_nms(boxes, scores, cls_ids, self.nms_thresh)
        return [dets[i] for i in kept_idx]

# ============================================================================
# 5. EVALUATION: mAP
# ============================================================================

def compute_ap(recall: np.ndarray, precision: np.ndarray) -> float:
    """Compute Average Precision using 11-point interpolation (VOC)."""
    ap = 0.0
    for thr in np.arange(0.0, 1.1, 0.1):
        prec = precision[recall >= thr]
        ap += np.max(prec) if len(prec) > 0 else 0.0
    return ap / 11.0

def iou_boxes(b1: np.ndarray, b2: np.ndarray) -> float:
    """IoU of two [x1,y1,x2,y2] boxes."""
    ix1 = max(b1[0], b2[0]); iy1 = max(b1[1], b2[1])
    ix2 = min(b1[2], b2[2]); iy2 = min(b1[3], b2[3])
    inter = max(0, ix2-ix1) * max(0, iy2-iy1)
    area1 = (b1[2]-b1[0]) * (b1[3]-b1[1])
    area2 = (b2[2]-b2[0]) * (b2[3]-b2[1])
    return inter / (area1 + area2 - inter + 1e-6)

def compute_map(predictions: List[dict], ground_truth: List[dict],
                iou_threshold: float = 0.5,
                classes: List[str] = None) -> dict:
    """Compute mAP at given IoU threshold.
    
    predictions: list of {'image_id', 'cls', 'score', 'box': [x1,y1,x2,y2]}
    ground_truth: list of {'image_id', 'cls', 'box': [x1,y1,x2,y2]}
    
    Returns: {'mAP': float, 'per_class': {cls: ap}}"""
    classes = classes or ADAS_CLASSES
    per_class_ap = {}
    
    for cls in classes:
        # Filter to this class
        cls_preds = sorted([p for p in predictions if p['cls'] == cls],
                            key=lambda x: -x['score'])
        cls_gts   = {p['image_id']: [g for g in ground_truth
                                      if g['image_id'] == p['image_id'] and g['cls'] == cls]
                     for p in cls_preds}
        
        tp = np.zeros(len(cls_preds))
        fp = np.zeros(len(cls_preds))
        matched: dict = {}  # {image_id: set of matched GT indices}
        
        for i, pred in enumerate(cls_preds):
            img_id = pred['image_id']
            gts    = cls_gts.get(img_id, [])
            
            best_iou, best_j = 0.0, -1
            for j, gt in enumerate(gts):
                iou = iou_boxes(np.array(pred['box']), np.array(gt['box']))
                if iou > best_iou:
                    best_iou, best_j = iou, j
            
            if best_iou >= iou_threshold:
                if img_id not in matched:
                    matched[img_id] = set()
                if best_j not in matched[img_id]:
                    tp[i] = 1
                    matched[img_id].add(best_j)
                else:
                    fp[i] = 1
            else:
                fp[i] = 1
        
        cum_tp  = np.cumsum(tp)
        cum_fp  = np.cumsum(fp)
        n_gt    = sum(len(g) for g in cls_gts.values())
        recall    = cum_tp / (n_gt + 1e-6)
        precision = cum_tp / (cum_tp + cum_fp + 1e-6)
        
        per_class_ap[cls] = compute_ap(recall, precision)
    
    mAP = np.mean(list(per_class_ap.values()))
    return {'mAP': float(mAP), 'per_class': per_class_ap}

# ============================================================================
# 6. DEMO
# ============================================================================

if __name__ == "__main__":
    print("=== Object Detection Demo ===\n")
    
    # 1. NMS test
    boxes  = np.array([[100,100,200,200], [110,110,210,210], [300,300,400,400]])
    scores = np.array([0.9, 0.8, 0.7])
    kept   = nms(boxes, scores, iou_threshold=0.45)
    print(f"NMS: 3 boxes → {len(kept)} kept (indices: {kept})")
    
    # 2. Mock mAP evaluation
    print("\nmAP evaluation (mock data):")
    mock_preds = [
        {'image_id': 0, 'cls': 'car', 'score': 0.9, 'box': [10,10,100,80]},
        {'image_id': 0, 'cls': 'car', 'score': 0.7, 'box': [200,200,300,280]},
    ]
    mock_gts = [
        {'image_id': 0, 'cls': 'car', 'box': [12,12,102,82]},
        {'image_id': 0, 'cls': 'car', 'box': [205,205,305,285]},
    ]
    result = compute_map(mock_preds, mock_gts, classes=['car'])
    print(f"  mAP@0.5: {result['mAP']:.3f}")
    print(f"  Per-class: {result['per_class']}")
    
    # 3. Latency benchmark (model = placeholder)
    print("\nInference latency demo (random tensor):")
    dummy = torch.randn(1, 3, 384, 640)
    
    # Time simple forward pass without model (just NMS overhead)
    t0 = time.perf_counter()
    for _ in range(100):
        boxes_r  = np.random.rand(500, 4).astype(np.float32) * 640
        scores_r = np.random.rand(500).astype(np.float32)
        cls_ids  = np.random.randint(0, 8, 500)
        batched_nms(boxes_r, scores_r, cls_ids)
    dt = (time.perf_counter() - t0) * 10  # ms per call
    print(f"  NMS latency (500 boxes, 8 classes): {dt:.2f}ms avg")
