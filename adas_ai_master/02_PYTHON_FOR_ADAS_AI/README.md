# 02 — Python for ADAS AI Development

## Overview
Production Python patterns for automotive AI: camera pipelines, training loops, radar processing, and real-time inference under strict latency budgets.

**Target hardware:** NVIDIA Jetson Orin NX, TDA4VM, host GPU (training)  
**Latency budget:** < 50ms end-to-end per frame (front camera 20 Hz)

---

## Environment Setup

```bash
# Python 3.10+ (3.11 not yet fully supported by PyTorch CUDA builds as of 2024)
python3.10 -m venv adas_ai_env
source adas_ai_env/bin/activate

pip install torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cu121
pip install opencv-python-headless==4.8.1.78   # headless = no GUI deps (ECU deployment)
pip install numpy==1.26.0 scipy==1.11.3
pip install onnx==1.15.0 onnxruntime-gpu==1.16.3
pip install albumentations==1.3.1               # Automotive-specific data augmentation
pip install wandb==0.16.0                        # Experiment tracking
pip install pytest==7.4.0 pytest-benchmark
```

### `requirements.txt`
```
torch>=2.1.0
torchvision>=0.16.0
opencv-python-headless>=4.8.0
numpy>=1.24.0
scipy>=1.11.0
onnx>=1.14.0
onnxruntime-gpu>=1.16.0
albumentations>=1.3.0
scikit-learn>=1.3.0
matplotlib>=3.7.0
wandb>=0.16.0
pytest>=7.0.0
```

---

## 1. NumPy for Sensor Data Processing

### Why NumPy over pure Python for sensor data?
- Vectorised ops: 100-1000× faster than Python loops
- Memory-contiguous arrays (C-order): crucial for DMA transfers on ECU
- Broadcasting: apply operations across entire sensor batches without explicit loops

### Broadcast example — normalise a batch of radar detections:
```python
import numpy as np

# (N, 5): [range_m, azimuth_deg, elevation_deg, velocity_mps, snr_db]
detections = np.random.uniform(0, 200, size=(512, 5)).astype(np.float32)

# Min-max normalise per feature (broadcasting: shape (5,) applied to (512, 5))
mins  = np.array([0.0, -90.0, -15.0, -60.0, 0.0], dtype=np.float32)
maxes = np.array([200.0, 90.0, 15.0,  60.0, 40.0], dtype=np.float32)
norm  = (detections - mins) / (maxes - mins + 1e-6)
# norm shape: (512, 5) — no Python loop needed
```

### Memory layout matters on ECU:
```python
# Prefer C-contiguous arrays for CUDA/DMA transfers
arr = np.ascontiguousarray(detections)         # force C layout
print(arr.flags['C_CONTIGUOUS'])               # True
tensor = torch.from_numpy(arr)                 # zero-copy if contiguous
```

---

## 2. OpenCV Integration with PyTorch

### Critical pattern: avoid uint8→float32 conversion bugs
```python
import cv2, torch

frame = cv2.imread("frame.png")                  # BGR uint8 [0,255]
frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

# WRONG: direct cast loses precision
# tensor = torch.from_numpy(frame_rgb)

# CORRECT: float32 normalise THEN to tensor
frame_f32 = frame_rgb.astype(np.float32) / 255.0
tensor = torch.from_numpy(frame_f32).permute(2, 0, 1).unsqueeze(0)  # (1,3,H,W)
```

### OpenCV inference with .onnx model (no PyTorch required at runtime):
```python
net = cv2.dnn.readNetFromONNX("lane_detector.onnx")
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA_FP16)

blob = cv2.dnn.blobFromImage(frame, 1/255.0, (640, 384),
                              mean=(0.485*255, 0.456*255, 0.406*255),
                              swapRB=True, crop=False)
net.setInput(blob)
output = net.forward()   # numpy array
```

---

## 3. PyTorch Training Loop Patterns

### Mixed Precision (FP16) — 2× throughput on Ampere+ GPUs
```python
scaler = torch.cuda.amp.GradScaler()

for images, labels in dataloader:
    optimizer.zero_grad()
    with torch.cuda.amp.autocast():     # FP16 forward pass
        outputs = model(images)
        loss = criterion(outputs, labels)
    scaler.scale(loss).backward()       # scaled FP16 gradients
    scaler.step(optimizer)
    scaler.update()
```

### Learning Rate Scheduling for ADAS training:
```python
# Warmup + CosineAnnealingLR (prevents divergence in early epochs)
from torch.optim.lr_scheduler import OneCycleLR

scheduler = OneCycleLR(
    optimizer, max_lr=1e-3,
    steps_per_epoch=len(train_loader),
    epochs=100,
    pct_start=0.05,          # 5% warmup
    div_factor=25,           # initial_lr = max_lr/25
    final_div_factor=1e4     # final_lr = initial_lr/10000
)
# Call scheduler.step() after each batch (not epoch) for OneCycleLR
```

### Data augmentation for automotive datasets:
```python
import albumentations as A

transform = A.Compose([
    A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.5),
    A.HueSaturationValue(hue_shift_limit=10, p=0.3),
    A.GaussianBlur(blur_limit=(3, 7), p=0.2),       # Camera defocus simulation
    A.RandomRain(p=0.2),                              # Rain on lens simulation
    A.RandomShadow(p=0.3),                            # Overpass/tunnel shadow
    A.HorizontalFlip(p=0.5),
    A.Normalize(mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225)),
], bbox_params=A.BboxParams(format='pascal_voc', label_fields=['class_labels']))
```

---

## 4. Real-Time Inference Pipeline

### Latency budget breakdown (20 Hz = 50ms per frame):
| Stage | Budget |
|-------|--------|
| Camera ISP + V4L2 capture | ~5ms |
| Resize + normalise (CPU) | ~2ms |
| DMA to GPU | ~1ms |
| CNN inference (TensorRT FP16) | ~8ms |
| Post-processing (NMS, decode) | ~3ms |
| DMA from GPU + output | ~1ms |
| **Total** | **~20ms (headroom for LKA/ACC)** |

### Thread pinning for real-time:
```python
import os, threading

def set_realtime_thread():
    """Pin thread to specific CPU core (avoid scheduler jitter)."""
    os.sched_setaffinity(0, {2})  # Pin to core 2
    # On embedded Linux with RT kernel: set SCHED_FIFO priority 80
    # import ctypes; ctypes.CDLL('libc.so.6').sched_setscheduler(...)
```

### Ring buffer for zero-copy frame passing:
```python
from queue import Queue

frame_queue = Queue(maxsize=3)  # Drop old frames if consumer is slow

def capture_thread(cap):
    while True:
        ret, frame = cap.read()
        if frame_queue.full():
            frame_queue.get_nowait()   # Drop oldest frame
        frame_queue.put(frame)

def inference_thread(model, pipeline):
    while True:
        frame = frame_queue.get()
        tensor, _ = pipeline.preprocess(frame)
        with torch.no_grad():
            result = model(tensor.cuda())
```

---

## 5. Model Export to ONNX

```python
model.eval()
dummy_input = torch.randn(1, 3, 384, 640).cuda()

torch.onnx.export(
    model, dummy_input, "adas_detector.onnx",
    export_params=True,
    opset_version=17,         # opset 17 supports more TensorRT-compatible ops
    do_constant_folding=True,
    input_names=['input'],
    output_names=['p3_out', 'p4_out', 'p5_out'],
    dynamic_axes={
        'input': {0: 'batch_size'},   # variable batch size for TensorRT
    }
)

# Verify
import onnx
model_onnx = onnx.load("adas_detector.onnx")
onnx.checker.check_model(model_onnx)
print(f"ONNX model valid. Size: {os.path.getsize('adas_detector.onnx')/1e6:.1f}MB")
```

---

## 6. Profiling for ECU Deployment

```python
# Torch profiler — identify bottleneck ops
from torch.profiler import profile, ProfilerActivity

with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],
             record_shapes=True) as prof:
    for i in range(20):
        with torch.no_grad():
            model(dummy_input)

print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=10))
```

---

## 7. Interview Q&A

### L1 (Junior)
**Q: Why use mixed precision (FP16) training?**  
A: FP16 uses half the memory (enabling 2× batch size), and modern GPUs (Volta+) have tensor cores that compute FP16 matrix multiplications ~8× faster than FP32. The `GradScaler` prevents underflow by scaling loss before backward pass.

**Q: What is `pin_memory=True` in DataLoader?**  
A: Pins CPU tensors in non-pageable memory, enabling faster asynchronous DMA transfers to GPU. Use with `non_blocking=True` in `.to(device)` for ~30% speedup.

### L2 (Mid-level)
**Q: How do you handle class imbalance in KITTI/NuScenes datasets?**  
A: Three strategies: (1) WeightedRandomSampler to oversample pedestrians/cyclists; (2) Focal Loss (reduces well-classified easy examples); (3) OHEM (Online Hard Example Mining) — backprop only on top-k highest-loss samples.

**Q: What is gradient clipping and when is it critical?**  
A: Clips gradient norm to a max value (e.g., 10.0) preventing exploding gradients in deep networks. Critical in ADAS models with large dynamic range in inputs (e.g., 0.01 pedestrian confidence vs 200m range value).

### L3 (Senior)
**Q: How would you reduce inference latency on Jetson Orin from 25ms to 10ms?**  
A: (1) Export to TensorRT INT8 with calibration dataset (~2× speedup); (2) Enable CUDA streams for concurrent pre/post-processing; (3) Profile with Nsight Systems — identify memory-bound vs compute-bound ops; (4) Use torch.compile() or TorchScript; (5) Replace dynamic shapes with fixed shapes (eliminating shape inference overhead); (6) Fuse BatchNorm into Conv weights post-training.

**Q: Describe the tradeoffs between TorchScript, ONNX, and TensorRT for ECU deployment.**  
A: TorchScript — easiest to generate, portable, but no hardware-specific optimisation. ONNX — hardware-agnostic intermediate format, supported by most accelerators, manual opset compatibility management. TensorRT — maximum performance on NVIDIA, graph fusion + kernel auto-tuning, engine is device-specific and must be regenerated per GPU/SM version. For non-NVIDIA targets (TDA4VM, Renesas V3H), ONNX + TVM or vendor SDK is preferred.

---

## Files in this Module
- [adas_python_pipeline.py](adas_python_pipeline.py) — Production camera, radar, and training pipelines
