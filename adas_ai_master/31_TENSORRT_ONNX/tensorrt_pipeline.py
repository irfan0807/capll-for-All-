"""
31_TENSORRT_ONNX — TensorRT + ONNX Production Pipeline
Full workflow: PyTorch → ONNX → TensorRT engine → inference benchmark
"""

from __future__ import annotations
import numpy as np
import time
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """TensorRT model build configuration."""
    onnx_path:       str
    engine_path:     str
    precision:       str       # 'fp32', 'fp16', 'int8'
    input_name:      str       = 'images'
    output_names:    List[str] = None
    input_shape:     Tuple    = (1, 3, 640, 640)   # (B, C, H, W)
    workspace_gb:    int       = 4
    min_batch:       int       = 1
    opt_batch:       int       = 1
    max_batch:       int       = 8


class AdasTensorRTPipeline:
    """End-to-end ADAS inference pipeline using TensorRT.
    
    Supports:
    - FP32 / FP16 / INT8 precision
    - Dynamic batch sizing
    - CUDA pre/post-processing
    - Latency benchmarking
    
    Hardware target: NVIDIA Jetson Orin NX 16GB, Drive Orin
    """
    
    def __init__(self, config: ModelConfig):
        self.cfg      = config
        self._session = None
        self._is_trt  = False
        
        if config.output_names is None:
            config.output_names = ['output0']
        
        self._load_or_build()
    
    def _load_or_build(self):
        """Load existing engine or build from ONNX."""
        if os.path.exists(self.cfg.engine_path):
            self._load_trt_engine()
        elif os.path.exists(self.cfg.onnx_path):
            self._build_trt_engine()
            self._load_trt_engine()
        else:
            print("No model found — running in demo mode")
    
    def _build_trt_engine(self):
        """Build TensorRT engine from ONNX model."""
        try:
            import tensorrt as trt
            logger = trt.Logger(trt.Logger.WARNING)
            builder = trt.Builder(logger)
            network_flags = 1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
            network = builder.create_network(network_flags)
            parser  = trt.OnnxParser(network, logger)
            
            with open(self.cfg.onnx_path, 'rb') as f:
                if not parser.parse(f.read()):
                    for i in range(parser.num_errors):
                        print(f"ONNX parse error: {parser.get_error(i)}")
                    raise RuntimeError("ONNX parsing failed")
            
            config = builder.create_builder_config()
            config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE,
                                          self.cfg.workspace_gb * (1024**3))
            
            # Precision flags
            if self.cfg.precision == 'fp16':
                config.set_flag(trt.BuilderFlag.FP16)
                print("Building FP16 engine...")
            elif self.cfg.precision == 'int8':
                config.set_flag(trt.BuilderFlag.INT8)
                config.set_flag(trt.BuilderFlag.FP16)
                print("Building INT8 engine (requires calibrator)...")
            else:
                print("Building FP32 engine...")
            
            # Dynamic shapes
            profile = builder.create_optimization_profile()
            in_name = self.cfg.input_name
            B, C, H, W = self.cfg.input_shape
            profile.set_shape(in_name,
                               min=(self.cfg.min_batch, C, H, W),
                               opt=(self.cfg.opt_batch, C, H, W),
                               max=(self.cfg.max_batch, C, H, W))
            config.add_optimization_profile(profile)
            
            # Build and save
            engine_bytes = builder.build_serialized_network(network, config)
            with open(self.cfg.engine_path, 'wb') as f:
                f.write(engine_bytes)
            print(f"Engine saved: {self.cfg.engine_path}")
            
        except ImportError:
            print("TensorRT not installed — using ONNX Runtime fallback")
            # Copy ONNX path as engine_path for ORT
            self.cfg.engine_path = self.cfg.onnx_path
    
    def _load_trt_engine(self):
        """Load TRT engine or ONNX with ORT."""
        path = self.cfg.engine_path
        
        # Try TensorRT first
        if path.endswith('.trt'):
            try:
                import tensorrt as trt
                import pycuda.driver as cuda
                import pycuda.autoinit   # noqa
                logger = trt.Logger(trt.Logger.WARNING)
                runtime = trt.Runtime(logger)
                with open(path, 'rb') as f:
                    engine = runtime.deserialize_cuda_engine(f.read())
                self._engine  = engine
                self._context = engine.create_execution_context()
                self._is_trt  = True
                print(f"Loaded TRT engine: {path}")
                return
            except (ImportError, Exception) as e:
                print(f"TRT load failed: {e}")
        
        # Fallback: ONNX Runtime
        try:
            import onnxruntime as ort
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            
            # Configure TRT Execution Provider within ORT
            trt_options = {
                'trt_max_workspace_size': self.cfg.workspace_gb * (1024**3),
                'trt_fp16_enable': self.cfg.precision in ('fp16', 'int8'),
                'trt_int8_enable': self.cfg.precision == 'int8',
                'trt_engine_cache_enable': True,
                'trt_engine_cache_path':   os.path.dirname(self.cfg.engine_path) or '.',
            }
            
            sess_opts = ort.SessionOptions()
            sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_opts.intra_op_num_threads = 4
            
            self._session = ort.InferenceSession(
                self.cfg.onnx_path if path.endswith('.trt') else path,
                sess_options=sess_opts,
                providers=[('TensorrtExecutionProvider', trt_options),
                            ('CUDAExecutionProvider', {}),
                            'CPUExecutionProvider']
            )
            print(f"Loaded ONNX Runtime session: {path}")
        except Exception as e:
            print(f"Model load failed (demo mode): {e}")
    
    def preprocess(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Preprocess camera frame for YOLO-style input.
        BGR → RGB, resize, normalize, CHW, batch dim.
        
        Returns: (1, 3, H, W) float32 [0,1]"""
        try:
            import cv2
            target_h, target_w = self.cfg.input_shape[2:]
            resized = cv2.resize(frame_bgr, (target_w, target_h),
                                  interpolation=cv2.INTER_LINEAR)
            rgb = resized[:, :, ::-1]   # BGR → RGB
        except ImportError:
            rgb = np.random.randint(0, 255,
                                     (*self.cfg.input_shape[2:], 3), dtype=np.uint8)
        
        tensor = rgb.astype(np.float32) / 255.0
        tensor = tensor.transpose(2, 0, 1)   # HWC → CHW
        return np.expand_dims(tensor, axis=0)  # Add batch dim
    
    def infer(self, preprocessed: np.ndarray) -> Dict[str, np.ndarray]:
        """Run inference. Returns dict of output name → numpy array."""
        if self._session is not None:
            outputs = self._session.run(
                None,
                {self.cfg.input_name: preprocessed}
            )
            return dict(zip(self.cfg.output_names, outputs))
        
        # Demo: return dummy detection output (B, N, 7) format: [x1,y1,x2,y2,conf,cls,track]
        B = preprocessed.shape[0]
        return {'output0': np.random.rand(B, 100, 7).astype(np.float32)}
    
    def postprocess(self, outputs: Dict[str, np.ndarray],
                     conf_threshold: float = 0.4,
                     iou_threshold:  float = 0.45) -> List[dict]:
        """Parse YOLO-format output to detection list.
        
        Expected output0 shape: (1, N, 7) — [x1, y1, x2, y2, conf, cls_conf, cls_id]"""
        raw  = outputs['output0'][0]   # (N, 7)
        dets = []
        
        for row in raw:
            if len(row) < 6:
                continue
            x1, y1, x2, y2 = row[:4]
            conf  = float(row[4])
            cls   = int(row[5]) if len(row) > 5 else 0
            
            if conf < conf_threshold:
                continue
            
            dets.append({
                'bbox':       [float(x1), float(y1), float(x2), float(y2)],
                'confidence': conf,
                'class_id':   cls,
            })
        
        return dets
    
    def benchmark(self, n_warmup: int = 20,
                   n_runs:   int = 200) -> Dict[str, float]:
        """Measure inference latency statistics."""
        dummy = np.random.rand(*self.cfg.input_shape).astype(np.float32)
        
        # Warmup
        for _ in range(n_warmup):
            self.infer(dummy)
        
        latencies = []
        for _ in range(n_runs):
            t0 = time.perf_counter()
            self.infer(dummy)
            latencies.append((time.perf_counter() - t0) * 1000)
        
        latencies.sort()
        mean = float(np.mean(latencies))
        return {
            'mean_ms':  mean,
            'p50_ms':   float(np.percentile(latencies, 50)),
            'p95_ms':   float(np.percentile(latencies, 95)),
            'p99_ms':   float(np.percentile(latencies, 99)),
            'fps':      round(1000 / mean, 1) if mean > 0 else 0.0,
        }


def export_pytorch_to_onnx(model_class_or_path: str,
                             output_onnx: str,
                             input_shape: tuple = (1, 3, 640, 640),
                             opset: int = 17) -> bool:
    """Export PyTorch model to ONNX.
    
    model_class_or_path: path to .pt file
    Returns True on success."""
    try:
        import torch
        
        # Load model
        model = torch.load(model_class_or_path, map_location='cpu')
        if hasattr(model, 'eval'):
            model.eval()
        
        dummy_input = torch.randn(*input_shape)
        
        torch.onnx.export(
            model,
            dummy_input,
            output_onnx,
            opset_version=opset,
            input_names=['images'],
            output_names=['output0'],
            dynamic_axes={
                'images':  {0: 'batch_size'},
                'output0': {0: 'batch_size'}
            },
            export_params=True,
            do_constant_folding=True
        )
        
        # Verify
        import onnx
        model_onnx = onnx.load(output_onnx)
        onnx.checker.check_model(model_onnx)
        print(f"ONNX export verified: {output_onnx}")
        return True
        
    except Exception as e:
        print(f"Export failed: {e}")
        return False


# ==========================================================================
# DEMO
# ==========================================================================

if __name__ == "__main__":
    print("=== TensorRT / ONNX Pipeline Demo ===\n")
    
    config = ModelConfig(
        onnx_path='detector.onnx',
        engine_path='detector_fp16.trt',
        precision='fp16',
        input_name='images',
        output_names=['output0'],
        input_shape=(1, 3, 640, 640)
    )
    
    pipeline = AdasTensorRTPipeline(config)
    
    # Simulate a camera frame
    dummy_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    
    preprocessed = pipeline.preprocess(dummy_frame)
    print(f"Preprocessed shape: {preprocessed.shape}")
    
    outputs  = pipeline.infer(preprocessed)
    dets     = pipeline.postprocess(outputs, conf_threshold=0.5)
    print(f"Detections found (demo): {len(dets)}")
    
    # Latency benchmark
    bench = pipeline.benchmark(n_warmup=5, n_runs=50)
    print("\nLatency (demo/CPU mode):")
    for k, v in bench.items():
        print(f"  {k}: {v:.2f}")
    
    print("\n--- Production Latency Targets (Jetson Orin NX FP16) ---")
    targets = [
        ("YOLOv8n",  "~7ms",   "~143fps"),
        ("YOLOv8s",  "~12ms",  "~83fps"),
        ("YOLOv8m",  "~20ms",  "~50fps"),
        ("YOLOv8l",  "~35ms",  "~28fps"),
    ]
    print(f"  {'Model':<12} {'Latency':>10} {'FPS':>10}")
    for name, lat, fps in targets:
        print(f"  {name:<12} {lat:>10} {fps:>10}")
