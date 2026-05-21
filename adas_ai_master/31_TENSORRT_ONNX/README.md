# 31 — TensorRT and ONNX for ADAS Production Deployment

## Overview
TensorRT and ONNX form the core model deployment stack for automotive AI. Covers the full pipeline: PyTorch training → ONNX export → TensorRT engine build → ECU deployment, with layer fusion, INT8 calibration, and performance validation.

---

## 1. Why TensorRT for ADAS?

| Feature | Benefit for ADAS |
|---------|----------------|
| Layer fusion | Conv+BN+ReLU → single GPU kernel; 2-5× speedup |
| FP16/INT8 | Doubles/quadruples throughput on Tensor Cores |
| Dynamic shapes | Handles variable batch size, resolution |
| DLA offload | Backbone on DLA (low power) + head on GPU |
| Persistent cache | Engine persists on ECU — no rebuild at boot |
| Latency predictability | WCET (Worst-Case Execution Time) estimable |

---

## 2. ONNX Export Best Practices

```python
import torch

def export_yolo_to_onnx(model, save_path: str, 
                          input_hw: tuple = (640, 640)):
    """Production ONNX export for YOLO-style detectors."""
    model.eval()
    dummy = torch.randn(1, 3, *input_hw)
    
    torch.onnx.export(
        model,
        dummy,
        save_path,
        opset_version=17,       # Latest stable (2024)
        input_names=['images'],
        output_names=['output0'],
        dynamic_axes={
            'images':  {0: 'batch'},
            'output0': {0: 'batch'}
        },
        do_constant_folding=True,    # Fold BN into Conv weights
        export_params=True,
        verbose=False
    )
    
    # Validate exported model
    import onnx
    import onnxsim                  # pip install onnxsim
    
    onnx_model = onnx.load(save_path)
    onnx.checker.check_model(onnx_model)
    
    # Simplify: remove redundant reshape/slice nodes
    simplified, ok = onnxsim.simplify(onnx_model)
    if ok:
        onnx.save(simplified, save_path.replace('.onnx', '_sim.onnx'))
    
    print(f"Exported: {save_path}")
```

---

## 3. TensorRT Engine Build (Full Reference)

```python
import tensorrt as trt

def build_trt_engine(onnx_path: str, engine_path: str,
                      precision: str = 'fp16') -> bool:
    logger  = trt.Logger(trt.Logger.WARNING)
    builder = trt.Builder(logger)
    network = builder.create_network(
        1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    parser  = trt.OnnxParser(network, logger)
    
    with open(onnx_path, 'rb') as f:
        parser.parse(f.read())
    
    config = builder.create_builder_config()
    config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 4 * 1024**3)
    
    # Precision
    if precision == 'fp16':
        config.set_flag(trt.BuilderFlag.FP16)
    elif precision == 'int8':
        config.set_flag(trt.BuilderFlag.INT8)
        config.set_flag(trt.BuilderFlag.FP16)
        # config.int8_calibrator = MyCalibrator()  # Required for INT8
    
    # Optimization profile for dynamic batch
    profile = builder.create_optimization_profile()
    profile.set_shape('images',
                       min=(1,3,640,640), opt=(1,3,640,640), max=(4,3,640,640))
    config.add_optimization_profile(profile)
    
    engine = builder.build_serialized_network(network, config)
    with open(engine_path, 'wb') as f:
        f.write(engine)
    return engine is not None
```

---

## 4. TensorRT Layer Fusion Examples

| Original Layers | After Fusion |
|----------------|-------------|
| Conv → BatchNorm → ReLU | CBR fusion (single kernel) |
| Conv → Add (residual) → ReLU | CBAR fusion |
| Concat → Conv | ConvConcat fusion |
| MaxPool → Conv | PoolConv fusion |

**Impact:** YOLOv8n: 72 layers before fusion → 47 layers after → 1.8× faster memory bandwidth utilisation.

---

## 5. INT8 Calibration (EntropyCalibrator2)

```python
class YoloCalibrator(trt.IInt8EntropyCalibrator2):
    def __init__(self, calib_images: list, cache_file: str,
                  batch_size: int = 8, input_shape=(3,640,640)):
        super().__init__()
        self.cache_file   = cache_file
        self.batch_size   = batch_size
        self.images       = calib_images
        self.input_shape  = input_shape
        self._idx         = 0
        
        import pycuda.driver as cuda
        nbytes = batch_size * int(np.prod(input_shape)) * 4
        self._device_input = cuda.mem_alloc(nbytes)
    
    def get_batch_size(self): 
        return self.batch_size
    
    def get_batch(self, names):
        if self._idx >= len(self.images):
            return None
        
        batch = self._load_batch(self.images[self._idx:self._idx+self.batch_size])
        self._idx += self.batch_size
        
        import pycuda.driver as cuda
        cuda.memcpy_htod(self._device_input, batch)
        return [int(self._device_input)]
    
    def read_calibration_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'rb') as f:
                return f.read()
        return None
    
    def write_calibration_cache(self, cache):
        with open(self.cache_file, 'wb') as f:
            f.write(cache)
    
    def _load_batch(self, paths):
        import cv2
        batch = []
        for p in paths:
            img = cv2.imread(p)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (self.input_shape[2], self.input_shape[1]))
            img = img.transpose(2,0,1).astype(np.float32) / 255.0
            batch.append(img)
        return np.stack(batch).ravel()
```

---

## 6. Latency Targets (Jetson Orin NX 16GB)

| Model | FP32 | FP16 | INT8 |
|-------|------|------|------|
| YOLOv8n | 14ms | 7ms | 4ms |
| YOLOv8s | 22ms | 12ms | 7ms |
| YOLOv8m | 40ms | 20ms | 11ms |
| DepthEstNet | 60ms | 28ms | 16ms |
| BEVFusion | 80ms | 40ms | 22ms |
| PointPillars | 30ms | 16ms | 9ms |

---

## 7. Interview Q&A

### L1
**Q: What is ONNX and why is it important for automotive AI deployment?**  
A: ONNX (Open Neural Network Exchange) is an open standard format for representing neural network models. Key benefits for automotive: (1) Framework independence — train in PyTorch/TensorFlow, deploy via ONNX Runtime on any hardware; (2) Standardised layer representation — enables hardware vendors (TI, Qualcomm, Renesas) to write ONNX parsers for their AI accelerators; (3) Model validation — onnx.checker validates model graph integrity; (4) Ecosystem — hundreds of tools for graph optimisation (onnxsim), visualisation (Netron), inference (ONNX Runtime). In production: ONNX is the "contract" between AI training team and ECU team — training team delivers ONNX, ECU team handles TRT/TIDL compilation.

### L2
**Q: What is layer fusion in TensorRT and which common ADAS model patterns benefit most?**  
A: Layer fusion merges multiple consecutive operations into a single GPU kernel, eliminating intermediate memory reads/writes. Key fusions: (1) CBR fusion (Conv+BN+ReLU): most common in ResNet/YOLO — eliminates 2 memory round-trips per layer; (2) Skip connection fusion (Conv+Add+ReLU): eliminates Add kernel overhead in ResNet shortcuts; (3) Attention QKV fusion (Transformer): merges 3 matmuls into single fused kernel. Most impactful for ADAS models: YOLOv8 backbone has 50+ CBR blocks → 30-40% latency reduction from fusion alone. TensorRT applies fusion automatically during engine build — no manual code changes required.

### L3
**Q: A YOLOv8m model achieves 95% mAP@0.5 in FP32 but drops to 88% in INT8 for pedestrian detection at night. How do you debug and resolve this?**  
A: (1) Root cause: INT8 quantisation loses precision in low-contrast feature maps — night images have small activation magnitudes in early convolutional layers; scale factors computed from daytime calibration set poorly represent night activations. (2) Debug: use TensorRT layer-by-layer sensitivity analysis (polygraphy inspect — compare FP32 vs INT8 per-layer outputs); identify layers with highest cosine distance between FP32/INT8 activations → find problematic layers. (3) Solutions: (a) Expand calibration set with night images (target ≥ 30% night scenes); (b) Per-layer precision fallback: force first 10 layers (low-contrast sensitive) to FP16, rest INT8; (c) QAT: add fake quantisation nodes during training specifically with night data; (d) Partial INT8: use INT8 for backbone (less critical), FP16 for detection head (confidence-sensitive). (4) Validation after fix: compare pedestrian AP@FP32 vs AP@INT8 on night-only test set; must be within 1%. (5) Production gate: automated regression test in CI pipeline checks per-class, per-condition mAP on each model update.

---

## Files
- [tensorrt_pipeline.py](tensorrt_pipeline.py) — AdasTensorRTPipeline, ModelConfig, export, benchmark
