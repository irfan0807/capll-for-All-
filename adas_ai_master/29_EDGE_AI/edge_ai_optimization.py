"""
29_EDGE_AI — Edge AI Optimisation for ADAS
TensorRT INT8 quantisation, pruning, knowledge distillation,
and inference benchmarking on Jetson Orin NX.
"""

from __future__ import annotations
import numpy as np
import time
from typing import Tuple, Optional, Dict, Any
from pathlib import Path


# ==========================================================================
# INT8 Calibration (TensorRT)
# ==========================================================================

class AdasCalibrationDataset:
    """TensorRT INT8 calibration dataset.
    
    Requires 500-1000 representative images from deployment environment.
    Captures activation distributions for optimal INT8 scaling."""
    
    def __init__(self, image_paths: list, batch_size: int = 8,
                  input_hw: Tuple[int,int] = (640, 640)):
        self.paths      = image_paths
        self.batch_size = batch_size
        self.h, self.w  = input_hw
        self._idx       = 0
    
    def get_batch(self) -> Optional[np.ndarray]:
        """Return next calibration batch, or None when exhausted."""
        if self._idx >= len(self.paths):
            return None
        
        batch = []
        for path in self.paths[self._idx : self._idx + self.batch_size]:
            img = self._load_and_preprocess(path)
            batch.append(img)
        
        self._idx += self.batch_size
        return np.stack(batch, axis=0).astype(np.float32)
    
    def _load_and_preprocess(self, path: str) -> np.ndarray:
        """Load and normalise image to [0,1]."""
        try:
            import cv2
            img = cv2.imread(path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (self.w, self.h))
            return img.transpose(2, 0, 1) / 255.0   # HWC → CHW, [0,1]
        except Exception:
            # Dummy data if OpenCV not available
            return np.random.rand(3, self.h, self.w).astype(np.float32)
    
    def reset(self):
        self._idx = 0


# ==========================================================================
# TensorRT Build + Inference (simulation without TRT installed)
# ==========================================================================

class TensorRTModel:
    """TensorRT engine wrapper for production ADAS inference.
    
    Usage:
        engine = TensorRTModel.build_from_onnx('detector.onnx',
                     precision='int8', calib_dataset=calib)
        output = engine.infer(frame_np)  # ~2ms on Jetson Orin NX
    """
    
    def __init__(self, engine_path: str, input_name: str = 'input',
                  output_names: list = None):
        self.engine_path   = engine_path
        self.input_name    = input_name
        self.output_names  = output_names or ['output']
        self._session      = None
        self._load_engine()
    
    def _load_engine(self):
        """Load TensorRT or ONNX Runtime engine."""
        try:
            import onnxruntime as ort
            self._session = ort.InferenceSession(
                self.engine_path,
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
            )
            print(f"Loaded engine: {self.engine_path} (ONNX Runtime)")
        except (ImportError, Exception) as e:
            print(f"Engine load skipped (demo mode): {e}")
    
    def infer(self, input_array: np.ndarray) -> Dict[str, np.ndarray]:
        """Run inference. Returns dict of output name → array."""
        if self._session is None:
            # Demo mode: return dummy output
            return {'output': np.random.rand(1, 100, 7).astype(np.float32)}
        
        outputs = self._session.run(
            None,
            {self.input_name: input_array}
        )
        return dict(zip(self.output_names, outputs))
    
    @classmethod
    def build_from_onnx(cls, onnx_path: str,
                          engine_path: str = None,
                          precision: str = 'fp16',
                          calib_dataset: Optional[AdasCalibrationDataset] = None,
                          workspace_gb: int = 4) -> 'TensorRTModel':
        """Build TensorRT engine from ONNX model.
        
        precision: 'fp32', 'fp16', 'int8'
        int8 requires calib_dataset (500+ images)"""
        if engine_path is None:
            engine_path = onnx_path.replace('.onnx', f'_{precision}.trt')
        
        print(f"Building TensorRT engine: {precision}, workspace={workspace_gb}GB")
        
        try:
            import tensorrt as trt
            logger = trt.Logger(trt.Logger.WARNING)
            builder = trt.Builder(logger)
            network = builder.create_network(
                1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
            parser = trt.OnnxParser(network, logger)
            
            with open(onnx_path, 'rb') as f:
                parser.parse(f.read())
            
            config = builder.create_builder_config()
            config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE,
                                          workspace_gb * (1024**3))
            
            if precision == 'fp16':
                config.set_flag(trt.BuilderFlag.FP16)
            elif precision == 'int8':
                config.set_flag(trt.BuilderFlag.INT8)
                # Set calibrator here (requires INT8Calibrator implementation)
            
            engine = builder.build_serialized_network(network, config)
            with open(engine_path, 'wb') as f:
                f.write(engine)
            print(f"Engine saved: {engine_path}")
        except (ImportError, Exception) as e:
            print(f"TensorRT not available, using ONNX Runtime: {e}")
            engine_path = onnx_path  # Fallback to ONNX
        
        return cls(engine_path)


# ==========================================================================
# Model Pruning (PyTorch)
# ==========================================================================

def prune_model_channels(model_state_dict: dict,
                           prune_ratio: float = 0.2) -> dict:
    """Structured channel pruning simulation.
    
    Real implementation: torch.nn.utils.prune.l1_unstructured
    or use torch-pruning (https://github.com/VainF/Torch-Pruning)
    
    Removes least-important channels based on L1 norm magnitude."""
    pruned = {}
    for key, tensor in model_state_dict.items():
        if 'weight' in key and tensor.ndim == 4:
            # Conv weight: (out_ch, in_ch, kH, kW)
            l1_norms = np.abs(tensor).sum(axis=(1,2,3))
            n_keep   = max(1, int(len(l1_norms) * (1 - prune_ratio)))
            keep_idx = np.argsort(l1_norms)[-n_keep:]  # Keep largest norms
            pruned[key] = tensor[keep_idx]
        else:
            pruned[key] = tensor
    return pruned


# ==========================================================================
# Knowledge Distillation
# ==========================================================================

def knowledge_distillation_loss(student_logits: np.ndarray,
                                  teacher_logits: np.ndarray,
                                  true_labels:    np.ndarray,
                                  temperature:    float = 4.0,
                                  alpha:          float = 0.5) -> float:
    """Knowledge distillation loss = alpha * KL_div(soft) + (1-alpha) * CE(hard).
    
    temperature: soft target sharpness (higher = softer)
    alpha: distillation weight (0=hard labels only, 1=soft only)
    
    Typical: student achieves 95% of teacher accuracy at 5× smaller model."""
    
    def softmax(x, T=1.0):
        e = np.exp((x - x.max(axis=-1, keepdims=True)) / T)
        return e / e.sum(axis=-1, keepdims=True)
    
    def cross_entropy(pred, target):
        pred = np.clip(pred, 1e-7, 1.0)
        return -np.mean(np.sum(target * np.log(pred), axis=-1))
    
    # Soft targets from teacher
    soft_targets  = softmax(teacher_logits, T=temperature)
    soft_student  = softmax(student_logits, T=temperature)
    
    kl_loss = cross_entropy(soft_student, soft_targets) * (temperature**2)
    ce_loss = cross_entropy(softmax(student_logits), true_labels)
    
    return float(alpha * kl_loss + (1 - alpha) * ce_loss)


# ==========================================================================
# Inference Latency Benchmark
# ==========================================================================

def benchmark_inference(model_fn, input_shape: tuple,
                          n_warmup: int = 10, n_runs: int = 100) -> Dict[str, float]:
    """Benchmark model inference latency.
    
    Returns dict: mean_ms, p50_ms, p95_ms, p99_ms, throughput_fps"""
    dummy_input = np.random.rand(*input_shape).astype(np.float32)
    
    # Warmup
    for _ in range(n_warmup):
        model_fn(dummy_input)
    
    # Benchmark
    latencies_ms = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        model_fn(dummy_input)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000)
    
    latencies_ms.sort()
    mean_ms = float(np.mean(latencies_ms))
    
    return {
        'mean_ms':         mean_ms,
        'p50_ms':          float(np.percentile(latencies_ms, 50)),
        'p95_ms':          float(np.percentile(latencies_ms, 95)),
        'p99_ms':          float(np.percentile(latencies_ms, 99)),
        'throughput_fps':  1000 / mean_ms if mean_ms > 0 else 0.0,
    }


# ==========================================================================
# DEMO
# ==========================================================================

if __name__ == "__main__":
    print("=== Edge AI Optimisation Demo ===\n")
    
    # Knowledge Distillation Loss
    B, C = 4, 80   # Batch=4, Classes=80 (COCO-like)
    teacher_logits = np.random.randn(B, C)
    student_logits = np.random.randn(B, C)
    one_hot = np.eye(C)[np.random.randint(0, C, B)]
    
    kd_loss = knowledge_distillation_loss(student_logits, teacher_logits,
                                           one_hot, temperature=4.0, alpha=0.5)
    print(f"Knowledge Distillation Loss: {kd_loss:.4f}")
    
    # Inference benchmark (simulated)
    def dummy_model(x):
        return x @ np.random.randn(x.shape[-1], 100)
    
    results = benchmark_inference(dummy_model, input_shape=(1, 1000),
                                   n_warmup=5, n_runs=50)
    print(f"\nLatency Benchmark:")
    for k, v in results.items():
        print(f"  {k}: {v:.2f}")
    
    # Precision comparison table
    print("\nTarget latency per ADAS model (Jetson Orin NX 16GB):")
    targets = [
        ("YOLOv8n FP32",  "14ms",  "71 FPS"),
        ("YOLOv8n FP16",  "7ms",   "143 FPS"),
        ("YOLOv8n INT8",  "4ms",   "250 FPS"),
        ("YOLOv8s INT8",  "7ms",   "143 FPS"),
        ("BEVFusion INT8","35ms",  "28 FPS"),
    ]
    print(f"  {'Model':<20} {'Latency':>8} {'Throughput':>12}")
    print(f"  {'-'*42}")
    for name, lat, fps in targets:
        print(f"  {name:<20} {lat:>8} {fps:>12}")
