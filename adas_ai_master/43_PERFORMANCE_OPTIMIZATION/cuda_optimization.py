"""
Module 43 — CUDA / GPU Performance Optimisation for ADAS AI
Hardware targets: Jetson Orin NX 16GB, NVIDIA Drive Orin, A100 (training)
"""

from __future__ import annotations

import time
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# 1.  Custom CUDA-style NMS (Python simulation with NumPy)
#     In production: implemented as CUDA kernel in C++ / TensorRT plugin
# ──────────────────────────────────────────────────────────────────────────────

def batched_nms(boxes: np.ndarray,
                scores: np.ndarray,
                class_ids: np.ndarray,
                iou_threshold: float = 0.45) -> np.ndarray:
    """
    Class-aware NMS. Applies per-class NMS to avoid suppressing across classes.
    boxes:     (N,4) float32  [x1,y1,x2,y2]
    scores:    (N,)  float32
    class_ids: (N,)  int32
    Returns:   indices of kept detections
    """
    keep_all: List[int] = []
    
    for cls_id in np.unique(class_ids):
        mask    = (class_ids == cls_id)
        indices = np.where(mask)[0]
        cls_boxes  = boxes[indices]
        cls_scores = scores[indices]
        
        kept_local = _nms_single_class(cls_boxes, cls_scores, iou_threshold)
        keep_all.extend(indices[kept_local].tolist())
    
    # Sort final keeps by score descending
    keep_arr = np.array(keep_all, dtype=np.int32)
    sort_idx = np.argsort(-scores[keep_arr])
    return keep_arr[sort_idx]


def _nms_single_class(boxes: np.ndarray,
                      scores: np.ndarray,
                      iou_thresh: float) -> np.ndarray:
    """Greedy NMS for single class."""
    x1, y1, x2, y2 = boxes[:,0], boxes[:,1], boxes[:,2], boxes[:,3]
    areas  = (x2 - x1) * (y2 - y1)
    order  = np.argsort(-scores)
    keep   = []
    
    while order.size > 0:
        i = order[0]
        keep.append(i)
        
        if order.size == 1:
            break
        
        rest = order[1:]
        xx1  = np.maximum(x1[i], x1[rest])
        yy1  = np.maximum(y1[i], y1[rest])
        xx2  = np.minimum(x2[i], x2[rest])
        yy2  = np.minimum(y2[i], y2[rest])
        
        inter = np.maximum(0.0, xx2-xx1) * np.maximum(0.0, yy2-yy1)
        iou   = inter / (areas[i] + areas[rest] - inter + 1e-7)
        
        order = rest[iou < iou_thresh]
    
    return np.array(keep, dtype=np.int32)


# ──────────────────────────────────────────────────────────────────────────────
# 2.  Vectorised preprocessing (NCHW, normalise, HWC→NCHW)
# ──────────────────────────────────────────────────────────────────────────────

class AdasPreprocessor:
    """
    GPU-style preprocessing pipeline (NumPy reference implementation).
    Production equivalent: CUDA kernel performing all ops in one pass.
    Mean/std: ImageNet defaults commonly used for ADAS transfer learning.
    """
    
    MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    
    def __init__(self, target_h: int = 640, target_w: int = 640):
        self.target_h = target_h
        self.target_w = target_w
    
    def preprocess_batch(self, frames: List[np.ndarray]) -> np.ndarray:
        """
        frames: list of HWC uint8 BGR images
        Returns: NCHW float32 normalised tensor
        """
        batch = np.zeros((len(frames), 3, self.target_h, self.target_w),
                         dtype=np.float32)
        
        for i, frame in enumerate(frames):
            resized = self._resize_letterbox(frame,
                                             self.target_h, self.target_w)
            rgb     = resized[:, :, ::-1]                   # BGR→RGB
            norm    = (rgb.astype(np.float32) / 255.0 - self.MEAN) / self.STD
            batch[i] = norm.transpose(2, 0, 1)              # HWC→CHW
        
        return batch                                         # NCHW
    
    @staticmethod
    def _resize_letterbox(img: np.ndarray, h: int, w: int) -> np.ndarray:
        """Resize preserving aspect ratio with padding."""
        ih, iw = img.shape[:2]
        scale  = min(h / ih, w / iw)
        nh, nw = int(ih * scale), int(iw * scale)
        
        # Pad with constant (114 = YOLO default grey)
        out = np.full((h, w, 3), 114, dtype=np.uint8)
        pad_y = (h - nh) // 2
        pad_x = (w - nw) // 2
        
        # Simple nearest-neighbour resize (production: bilinear via CUDA)
        resized = img[
            (np.linspace(0, ih-1, nh)).astype(int)[:, None],
            (np.linspace(0, iw-1, nw)).astype(int)[None, :]
        ]
        out[pad_y:pad_y+nh, pad_x:pad_x+nw] = resized
        return out


# ──────────────────────────────────────────────────────────────────────────────
# 3.  Memory bandwidth optimisation strategies
# ──────────────────────────────────────────────────────────────────────────────

class MemoryOptimizer:
    """
    Demonstrates memory access pattern analysis for CUDA optimisation.
    Production: use Nsight Compute to profile, then apply these patterns.
    """
    
    @staticmethod
    def coalesced_access_example(h: int = 1024, w: int = 1024) -> None:
        """
        Coalesced (row-major) access pattern is 10–50× faster on GPU.
        This simulates the difference in cache efficiency.
        """
        data = np.random.rand(h, w).astype(np.float32)
        
        # Coalesced: access rows (contiguous in C order)
        t0 = time.perf_counter()
        for _ in range(100):
            _ = data.sum(axis=1)   # Row-wise: cache-friendly
        t_coal = (time.perf_counter() - t0) * 1e3
        
        # Strided: access columns (non-contiguous in C order)
        t0 = time.perf_counter()
        for _ in range(100):
            _ = data.sum(axis=0)   # Col-wise: cache-unfriendly
        t_stride = (time.perf_counter() - t0) * 1e3
        
        logger.info(f"Coalesced: {t_coal:.2f}ms  Strided: {t_stride:.2f}ms")
    
    @staticmethod
    def tiled_matmul(A: np.ndarray, B: np.ndarray,
                     tile_size: int = 16) -> np.ndarray:
        """
        Tiled matrix multiplication: improves L2 cache utilisation.
        CUDA implementation achieves near-cuBLAS speed for small matrices.
        Reference: GPU Gems, Ch.3
        """
        assert A.shape[1] == B.shape[0], "Dimension mismatch"
        M, K = A.shape; _, N = B.shape
        C = np.zeros((M, N), dtype=A.dtype)
        
        for i in range(0, M, tile_size):
            for j in range(0, N, tile_size):
                for k in range(0, K, tile_size):
                    C[i:i+tile_size, j:j+tile_size] += (
                        A[i:i+tile_size, k:k+tile_size] @
                        B[k:k+tile_size, j:j+tile_size]
                    )
        return C


# ──────────────────────────────────────────────────────────────────────────────
# 4.  Latency profiler for pipeline stages
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class StageProfile:
    name:    str
    min_ms:  float
    p50_ms:  float
    p95_ms:  float
    p99_ms:  float
    max_ms:  float


class PipelineProfiler:
    """Measure latency of each stage in inference pipeline."""
    
    def __init__(self, warmup: int = 10, runs: int = 100):
        self.warmup = warmup
        self.runs   = runs
    
    def profile_stage(self, stage_fn, *args, name: str = "stage") -> StageProfile:
        """Run stage_fn(*args) and collect latency statistics."""
        latencies: List[float] = []
        
        # Warmup (fill caches, JIT compile)
        for _ in range(self.warmup):
            stage_fn(*args)
        
        # Measurement
        for _ in range(self.runs):
            t0 = time.perf_counter()
            stage_fn(*args)
            latencies.append((time.perf_counter() - t0) * 1e3)
        
        lat = np.array(latencies)
        return StageProfile(
            name   = name,
            min_ms = float(np.min(lat)),
            p50_ms = float(np.percentile(lat, 50)),
            p95_ms = float(np.percentile(lat, 95)),
            p99_ms = float(np.percentile(lat, 99)),
            max_ms = float(np.max(lat)),
        )
    
    def print_report(self, profiles: List[StageProfile]) -> None:
        total_p50 = sum(p.p50_ms for p in profiles)
        print(f"\n{'Stage':<30} {'min':>8} {'p50':>8} {'p95':>8} {'p99':>8}")
        print("-" * 70)
        for p in profiles:
            print(f"{p.name:<30} {p.min_ms:>7.2f}ms {p.p50_ms:>7.2f}ms "
                  f"{p.p95_ms:>7.2f}ms {p.p99_ms:>7.2f}ms")
        print("-" * 70)
        print(f"{'Total pipeline (p50)':<30} {total_p50:>7.2f}ms")


# ──────────────────────────────────────────────────────────────────────────────
# 5.  INT8 calibration range collection
# ──────────────────────────────────────────────────────────────────────────────

class LayerRangeCollector:
    """
    Collects activation ranges per layer for INT8 calibration.
    In production: hooks into TRT calibration API or PyTorch observer.
    """
    
    def __init__(self):
        self.ranges: dict = {}
    
    def update(self, layer_name: str, tensor: np.ndarray) -> None:
        """Update min/max range for a layer's activations."""
        mn = float(tensor.min())
        mx = float(tensor.max())
        
        if layer_name not in self.ranges:
            self.ranges[layer_name] = [mn, mx]
        else:
            self.ranges[layer_name][0] = min(self.ranges[layer_name][0], mn)
            self.ranges[layer_name][1] = max(self.ranges[layer_name][1], mx)
    
    def compute_scales(self) -> dict:
        """Compute INT8 scale factors (symmetric, per-layer)."""
        scales = {}
        for name, (mn, mx) in self.ranges.items():
            abs_max = max(abs(mn), abs(mx))
            scales[name] = abs_max / 127.0      # INT8 symmetric scale
        return scales


# ──────────────────────────────────────────────────────────────────────────────
# Demo
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s: %(message)s")
    
    print("=" * 60)
    print("CUDA Optimisation Demo (CPU reference implementations)")
    print("=" * 60)
    
    # 1. NMS demo
    N = 200
    rng = np.random.default_rng(42)
    boxes     = rng.uniform(0, 640, (N, 4)).astype(np.float32)
    boxes[:,2] = np.maximum(boxes[:,0] + 10, boxes[:,2])
    boxes[:,3] = np.maximum(boxes[:,1] + 10, boxes[:,3])
    scores    = rng.uniform(0.3, 1.0, (N,)).astype(np.float32)
    cls_ids   = rng.integers(0, 5, (N,)).astype(np.int32)
    
    kept = batched_nms(boxes, scores, cls_ids, iou_threshold=0.45)
    print(f"\n[NMS] Input: {N} boxes → Kept: {len(kept)} after NMS")
    
    # 2. Preprocessing demo
    prep   = AdasPreprocessor(640, 640)
    frames = [rng.integers(0, 255, (1080, 1920, 3), dtype=np.uint8) for _ in range(4)]
    batch  = prep.preprocess_batch(frames)
    print(f"\n[Preprocessing] Batch shape: {batch.shape}  dtype: {batch.dtype}")
    print(f"  Value range: [{batch.min():.3f}, {batch.max():.3f}]")
    
    # 3. Pipeline profiler demo
    profiler = PipelineProfiler(warmup=5, runs=50)
    single_frame = [frames[0]]
    
    p_pre  = profiler.profile_stage(prep.preprocess_batch, single_frame, name="Preprocessing")
    p_nms  = profiler.profile_stage(batched_nms, boxes, scores, cls_ids, name="NMS")
    
    profiler.print_report([p_pre, p_nms])
    
    # 4. Calibration range demo
    collector = LayerRangeCollector()
    for i in range(10):
        fake_act = rng.normal(0, 1, (1, 64, 40, 40)).astype(np.float32)
        collector.update(f"backbone.layer{i}", fake_act)
    
    scales = collector.compute_scales()
    print(f"\n[INT8 Scales] Computed {len(scales)} layer scales")
    sample_name = list(scales.keys())[0]
    print(f"  Example: {sample_name} → scale = {scales[sample_name]:.6f}")
    
    print("\n" + "=" * 60)
    print("Production targets (Jetson Orin NX INT8):")
    print("  Preprocessing (CUDA kernel):  ~0.5ms/frame")
    print("  YOLOv8s inference (TRT INT8): ~4-6ms/frame")
    print("  NMS (CUDA kernel):            ~0.3ms")
    print("  Total pipeline budget:        <12ms (83fps)")
    print("=" * 60)
