# 29 — Edge AI Optimisation for ADAS

## Overview
Deploying trained neural networks on automotive-grade ECUs requires aggressive optimisation: quantisation, pruning, knowledge distillation, and hardware-specific tuning. Target: <10ms inference on Jetson Orin NX / TDA4VM.

---

## 1. Edge Hardware Comparison

| Hardware | AI Compute | Power | Typical Use |
|----------|----------|-------|------------|
| NVIDIA Jetson Orin NX 16GB | 100 TOPS | 25W | L2+ domain controller, research |
| NVIDIA Drive Orin | 254 TOPS | 65W | L3+ AD system |
| TDA4VM (TI) | 8 TOPS MMA | 12W | Camera ECU, LiDAR pre-processing |
| Qualcomm Snapdragon Ride | 30-700 TOPS (family) | 10-80W | OEM central ECU |
| Renesas V3H | 2 TOPS CNN | 5W | Individual sensor ECU |

---

## 2. Precision Comparison (YOLOv8n, Jetson Orin)

| Precision | Latency | mAP Loss | Memory |
|---------|---------|---------|--------|
| FP32 | 14ms | 0% (baseline) | 12MB |
| FP16 | 7ms | <0.1% | 6MB |
| INT8 | 4ms | 0.5-1.5% | 3MB |
| INT4 (experimental) | 2.5ms | 2-5% | 1.5MB |

**Rule of thumb:** FP16 is free — always use on Jetson NVIDIA hardware. INT8 requires calibration but is safe for ADAS detection if mAP validated.

---

## 3. TensorRT INT8 Quantisation Workflow

```
Train model (PyTorch, FP32)
     │
     ▼
Export to ONNX (opset 17)
     │ torch.onnx.export(model, dummy, 'model.onnx',
     │     opset_version=17, dynamic_axes={'input': {0: 'batch'}})
     ▼
TensorRT INT8 calibration
     │ Collect 500-1000 representative images (deployment domain)
     │ Run INT8 calibrator → computes per-layer scale factors
     ▼
Build TRT engine (int8 flag)
     │
     ▼
Validate mAP on held-out test set
     │ Acceptance: mAP drop < 1% vs FP32
     ▼
Deploy .trt engine to ECU
```

---

## 4. Post-Training Quantisation vs Quantisation-Aware Training

| Approach | Process | mAP Loss | Complexity |
|---------|---------|---------|-----------|
| PTQ (Post-Training Quantisation) | After training, calibration only | 0.5-2% | Low |
| QAT (Quantisation-Aware Training) | Simulate INT8 during training | 0-0.3% | High |

**When to use QAT:** Small models (MobileNet, EfficientDet-Lite), where PTQ mAP drop exceeds threshold, or when deploying to INT4 (experimental NVIDIA ampere).

---

## 5. Model Pruning

```python
# PyTorch structured pruning using torch-pruning
import torch_pruning as tp
import torch

model = YourModel()

# Compute importance scores (L2 norm of filters)
example_inputs = torch.randn(1, 3, 640, 640)
imp = tp.importance.MagnitudeImportance(p=2)

pruner = tp.pruner.MagnitudePruner(
    model,
    example_inputs,
    importance=imp,
    pruning_ratio=0.3,   # Remove 30% of channels
    global_pruning=True,
)

for i in range(5):
    pruner.step()    # Step iterative pruning

# Fine-tune for 5 epochs to recover accuracy
```

---

## 6. Knowledge Distillation

Large teacher (YOLOv8l, 43M params) → Small student (YOLOv8n, 3M params):

$$\mathcal{L} = \alpha \cdot T^2 \cdot \text{KL}\!\left(\sigma\!\left(\frac{z_s}{T}\right), \sigma\!\left(\frac{z_t}{T}\right)\right) + (1-\alpha) \cdot \mathcal{L}_{CE}(z_s, y)$$

Where $T=4$ (temperature), $\alpha=0.5$ (distillation weight).

**Feature distillation:** Also match intermediate feature maps (FPN features), not just final logits — 2-3% mAP improvement over logit-only distillation.

---

## 7. DLA (Deep Learning Accelerator) on Jetson

NVIDIA Jetson has two DLA co-processors in addition to GPU. DLA is more power-efficient for inference:

```
GPU: 100 TOPS (FP16/INT8) — flexible, dynamic shapes
DLA: 2× DLA cores, 10 TOPS each — fixed models only, ultra low power

Strategy: Run backbone on DLA (static shapes, high throughput)
          Run detection head on GPU (dynamic batch, NMS)
```

```python
# TensorRT DLA submission
config.default_device_type = trt.DeviceType.DLA
config.DLA_core = 0
config.set_flag(trt.BuilderFlag.GPU_FALLBACK)  # Fall back to GPU for unsupported layers
```

---

## 8. Interview Q&A

### L1
**Q: What is the difference between FP32, FP16, and INT8 inference and which is preferred for ADAS?**  
A: FP32: 32-bit floating point, highest precision, 4 bytes/value — used for training. FP16: 16-bit floating point, 2 bytes/value, native NVIDIA Tensor Core support — nearly identical accuracy to FP32 (< 0.1% mAP difference), 2× faster, 2× less memory — **preferred for ADAS inference when GPU has Tensor Cores (Jetson Orin, Drive Orin)**. INT8: 8-bit integer, 1 byte/value, 3-4× faster than FP32 — requires calibration to map floating-point activation range to integer range — 0.5-2% mAP loss, acceptable for most detectors but requires per-function validation (e.g., pedestrian detection separately tested from vehicle detection).

### L2
**Q: How do you validate that INT8 quantised model meets ADAS safety requirements?**  
A: (1) Per-class evaluation: compute mAP separately for pedestrians, cyclists, vehicles — pedestrian AP must not drop > 0.5% vs FP32 baseline. (2) Edge case analysis: evaluate on datasets specifically collected for night, rain, construction — quantisation sometimes loses rare-class performance. (3) False negative analysis: count missed detections by severity — FN on pedestrian at 80kph = critical. (4) Calibration domain: calibration images must match deployment conditions — if car is sold in 50+ countries with varied road conditions, calibration set must include global diversity. (5) Regression gate: automated CI/CD pipeline runs full test suite on every model update, blocks deployment if any metric regresses. (6) On-vehicle log replay: run quantised model on GB of real recorded data, compare outputs to FP32 reference.

### L3
**Q: Design a complete edge AI deployment pipeline from training to production ECU.**  
A: (1) Training: PyTorch 2.1, mixed precision (torch.cuda.amp), gradient checkpointing; 200 epochs, cosine LR schedule, CutMix augmentation; validation set = held-out OEM vehicle fleet data (not public datasets). (2) Export: torch.onnx.export → ONNX opset 17; verify with onnx.check_model(); dynamic batch axis. (3) Optimisation: ONNX simplifier (remove redundant nodes); TensorRT FP16 baseline; INT8 calibration with 1000 representative frames from each camera angle + lighting condition. (4) Validation: compare FP32/FP16/INT8 outputs on 10k image test set; must pass mAP gates (pedestrian AP > 80%, car AP > 90%, speed limit AP > 95%). (5) ECU packaging: TRT engine in .trt file, model version hash in ECU metadata; AUTOSAR Adaptive SWC wrapper (manifest + execution management). (6) OTA delivery: signed model binary (code signing key HSM); flashed to ECU partition B; A/B rollback if self-test fails post-flash. (7) Production monitoring: ECU logs inference confidence distributions; OTA analytics flag confidence distribution drift → triggers retraining.

---

## Files
- [edge_ai_optimization.py](edge_ai_optimization.py) — TensorRTModel, INT8 calibration, pruning, KD loss, latency benchmark
