# 43 — Performance Optimisation for ADAS AI

## Overview
GPU/CPU performance optimisation for ADAS AI inference: CUDA kernels, TensorRT tuning, memory bandwidth, quantisation, and profiling methodology targeting Jetson Orin NX, TDA4VM, and NVIDIA Drive Orin.

---

## 1. Performance Targets by Hardware

| Hardware | Model | Precision | Target Latency | FPS |
|---------|-------|-----------|---------------|-----|
| Jetson Orin NX 16GB | YOLOv8n | INT8 | 3ms | 333 |
| Jetson Orin NX 16GB | YOLOv8s | INT8 | 6ms | 166 |
| Jetson Orin NX 16GB | YOLOv8m | INT8 | 10ms | 100 |
| TDA4VM (TIDL) | MobileNetV3+SSD | INT8 | 12ms | 83 |
| Drive Orin (DLA+GPU) | YOLOv8l | INT8 | 8ms | 125 |
| Snapdragon Ride | Custom MobileNet | INT8 | 15ms | 66 |

---

## 2. TensorRT Optimisation Pipeline

```python
import tensorrt as trt
import numpy as np

def build_optimised_engine(onnx_path: str, 
                            calibration_data: np.ndarray,
                            precision: str = 'INT8') -> bytes:
    """
    Build TRT engine with maximum optimisations.
    Returns serialised engine bytes.
    """
    logger  = trt.Logger(trt.Logger.WARNING)
    builder = trt.Builder(logger)
    config  = builder.create_builder_config()
    network = builder.create_network(
        1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    parser  = trt.OnnxParser(network, logger)
    
    # Parse ONNX
    with open(onnx_path, 'rb') as f:
        parser.parse(f.read())
    
    # --- Optimisation flags ---
    config.max_workspace_size = 4 * (1024 ** 3)   # 4GB workspace
    
    if precision == 'FP16':
        config.set_flag(trt.BuilderFlag.FP16)
    elif precision == 'INT8':
        config.set_flag(trt.BuilderFlag.INT8)
        config.set_flag(trt.BuilderFlag.FP16)       # Fallback for INT8-unsupported layers
        config.int8_calibrator = AdasCalibrator(calibration_data)
    
    # Timing cache: reuse layer profiling across builds
    cache = config.create_timing_cache(b'')
    config.set_timing_cache(cache, ignore_mismatch=False)
    
    # DLA offload (Jetson Orin): backbone layers to DLA, head to GPU
    # config.default_device_type = trt.DeviceType.DLA
    # config.DLA_core = 0
    
    # Build
    engine = builder.build_engine(network, config)
    return engine.serialize()
```

---

## 3. Layer Fusion Opportunities

| Pattern | Before | After | Speedup |
|---------|--------|-------|---------|
| Conv+BN+ReLU | 3 kernels | 1 kernel (CBR) | 2.1× |
| Conv+BN+SiLU (YOLOv8) | 3 kernels | 1 kernel | 1.9× |
| Matmul+Bias+GELU | 3 ops | 1 (flash attention-like) | 1.7× |
| Residual skip | Add+Relu | fused | 1.3× |

TensorRT automatically fuses these. Verify with `trtexec --dumpLayerInfo`.

---

## 4. Memory Bandwidth Profiling

```bash
# Nsight Compute: memory throughput analysis
nv-nsight-cu-cli --metrics \
  l1tex__t_bytes_pipe_lsu_mem_global_op_ld.sum,\
  l1tex__t_bytes_pipe_lsu_mem_global_op_st.sum \
  --target-processes all \
  python inference.py

# Key metrics to check:
# DRAM Bandwidth: target > 60% of peak (Orin NX peak = 68GB/s)
# L2 Hit Rate: target > 70%
# Occupancy: target > 50%
```

---

## 5. CUDA Kernel Optimisation Principles

### Coalesced Memory Access
```c
// WRONG: Strided access (each thread accesses non-contiguous memory)
__global__ void bad_kernel(float* in, float* out, int N) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    // threads 0-31 access elements 0, N, 2N, 3N... (not coalesced)
    out[tid] = in[tid * N];  // BAD
}

// CORRECT: Coalesced access (adjacent threads access adjacent memory)
__global__ void good_kernel(float* in, float* out, int H, int W) {
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;
    if (row < H && col < W)
        out[row * W + col] = in[row * W + col] * 2.0f;  // GOOD
}
```

### Shared Memory Tiling
```c
// Tiled preprocessing: reduces global memory accesses
#define TILE 16
__global__ void normalise_tile(float* img, float* out, 
                                float mean, float std, int N) {
    __shared__ float tile[TILE];
    int idx = blockIdx.x * TILE + threadIdx.x;
    
    if (idx < N) {
        tile[threadIdx.x] = img[idx];   // Load tile into SMEM
        __syncthreads();
        out[idx] = (tile[threadIdx.x] - mean) / std;
    }
}
```

---

## 6. Quantisation: PTQ vs QAT

| Property | PTQ (Post-Training) | QAT (Quant-Aware Training) |
|---------|--------------------|-----------------------------|
| Accuracy loss | 1-3% mAP | < 0.5% mAP |
| Time | 2 hours | 1-2 days (fine-tuning) |
| Data needed | Calibration set (100-1000 frames) | Full training set |
| When to use | First deployment, rapid iteration | Final production model |

### QAT with PyTorch
```python
import torch
from torch.quantization import get_default_qat_qconfig
from torch.quantization import prepare_qat, convert

model = load_yolo_model()
model.qconfig = get_default_qat_qconfig('qnnpack')
model_qat = prepare_qat(model.train())

# Fine-tune for 5 epochs with original LR × 0.01
optimizer = torch.optim.SGD(model_qat.parameters(), lr=0.0001)
for epoch in range(5):
    train_one_epoch(model_qat, dataloader, optimizer)

# Convert to INT8 inference model
model_int8 = convert(model_qat.eval())
```

---

## 7. Profiling with nvprof / Nsight Systems

```bash
# Full pipeline profile
nsys profile --trace=cuda,nvtx,osrt \
             --output=adas_inference \
             python inference.py

# Analyse with nsys-ui (GUI) or CLI:
nsys stats --report gputrace adas_inference.qdrep
```

### NVTX Markers for Fine-Grained Profiling
```python
import torch
import torch.cuda.nvtx as nvtx

def inference_pipeline(frame):
    nvtx.mark("start_pipeline")
    
    with nvtx.annotate("preprocessing"):
        tensor = preprocess(frame)
    
    with nvtx.annotate("model_inference"):
        with torch.no_grad():
            output = model(tensor)
    
    with nvtx.annotate("postprocessing"):
        detections = postprocess(output)
    
    return detections
```

---

## 8. Interview Q&A

### L1
**Q: What is the difference between FP32, FP16, and INT8 inference in terms of ADAS performance?**  
A: FP32: full precision (32-bit float), highest accuracy, most memory/compute. FP16: half precision, ~2× faster, ~2× less memory, <0.5% accuracy loss in practice — standard for production. INT8: 8-bit integer, ~4× faster than FP32, ~4× less memory, 1-3% accuracy loss with PTQ (< 0.5% with QAT) — used for maximum throughput on ECU. ADAS: FP32 for development/training; FP16 for most production deployment; INT8 for tight latency-constrained ECUs (TDA4VM, Snapdragon Ride).

### L2
**Q: A model's inference is taking 18ms but budget is 12ms. How do you optimise it?**  
A: Systematic approach: (1) Profile first: use Nsight Systems to identify bottleneck (is it GPU compute, memory, or CPU pre/post?). Common finding: preprocessing is on CPU → move to CUDA; (2) Check NMS: CPU NMS at high detection count can be 3-4ms → use GPU NMS (TRT batched NMS plugin); (3) Precision: switch FP32 → INT8 (4× speedup potential); (4) Model architecture: try YOLOv8n instead of YOLOv8s if accuracy permits; (5) Input resolution: 640×640 → 416×416 (35% fewer MACs); (6) TRT engine: rebuild with `--best` flag, enable DLA offload for backbone, enable timing cache; (7) Batch size: if running multiple cameras, batch them (amortise fixed overhead). Typically combination of INT8 + resolution reduction achieves 30-40% latency reduction.

### L3
**Q: Describe how DLA (Deep Learning Accelerator) on Jetson Orin reduces power consumption while meeting latency targets.**  
A: DLA on Orin NX: dedicated fixed-function accelerator, 8-bit integer, ~1.3ms for MobileNetV3 at < 2W vs GPU at 5W for same model. Integration strategy: (1) Run backbone (ResNet/MobileNet feature extractor) on DLA — these are standard conv/BN/ReLU layers that DLA supports well; (2) Run detection head (FPN, detection heads, NMS) on GPU — these have dynamic shapes, attention layers not supported by DLA; (3) Pipeline: GPU submits backbone job to DLA, continues other work while DLA runs, GPU retrieves features and completes head; (4) Limitation: DLA latency slightly higher than GPU for same task (due to memory transfer), but power is ~3× lower → 30fps camera processing on DLA leaves GPU free for more complex tasks. Production metric: YOLOv8n backbone on DLA = 1.8ms at 1.8W; on GPU = 1.1ms at 4.5W → DLA preferred when thermal budget constrained.
