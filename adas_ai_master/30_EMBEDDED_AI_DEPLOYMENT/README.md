# 30 — Embedded AI Deployment for ADAS ECUs

## Overview
Deploying AI models to resource-constrained automotive ECUs: TIDL on TDA4VM, ONNX Runtime on AUTOSAR Adaptive, model packaging, OTA updates, and production monitoring.

---

## 1. ECU Deployment Challenges

| Challenge | Description | Solution |
|---------|-----------|--------|
| Memory constraint | ECU RAM: 2-16GB, Flash: 32-512MB | INT8 quantisation, model compression |
| Latency requirement | Camera ECU: < 50ms (20Hz) | TensorRT, DLA, async pipeline |
| Power budget | ECU: 5-25W total | Precision reduction, DLA offload |
| Thermal management | ECU junction temp < 125°C | Throttling, thermal model, fan |
| Functional safety | ISO 26262 ASIL-A to ASIL-D | Watchdog, E2E, FMEA, SOTIF |
| Deterministic timing | No garbage collection, no heap in hot path | Static memory, RAII, fixed buffers |

---

## 2. TI TDA4VM (Texas Instruments) Deployment via TIDL

TDA4VM is common in camera ECUs (e.g., rear-view, surround-view):

```
TDA4VM AI blocks:
  - 2× ARM Cortex-A72 (1.0 GHz) — application code
  - 6× ARM Cortex-R5F — safety MCUs
  - 4× C71x DSP — custom kernels
  - 2× MMA (Matrix Multiply Accelerator) — AI inference

TIDL (TI Deep Learning Library) workflow:
  1. Train model (PyTorch/TF)
  2. Export ONNX
  3. TIDL import tool → converts to .tidl binary
  4. Flash to ECU partition
  5. Runtime: TIDL API calls from C application
```

```c
// TIDL API usage (simplified, C code)
#include "tidl_api.h"

tidl_net_t* net = tidl_net_create("detector.tidl");
tidl_net_alloc(net, TIDL_MEM_HEAP);

float input[3 * 640 * 640];  // Preprocessed image
float output[100 * 7];       // Detection outputs

tidl_net_run(net, input, output);

// Parse detections from output
for (int i = 0; i < 100; i++) {
    if (output[i*7 + 4] > 0.5f) {  // confidence
        float x1 = output[i*7 + 0];
        float y1 = output[i*7 + 1];
        // ...
    }
}

tidl_net_free(net);
```

---

## 3. ONNX Runtime on AUTOSAR Adaptive

```cpp
// AUTOSAR Adaptive R21-11 SWC with ONNX Runtime
#include <onnxruntime_cxx_api.h>

class AiInferenceSWC {
    Ort::Env env_{ORT_LOGGING_LEVEL_WARNING, "adas_inference"};
    Ort::Session* session_ = nullptr;
    
    static constexpr size_t kInputH = 640;
    static constexpr size_t kInputW = 640;
    
    // Static allocation — no heap in hot path
    alignas(64) float input_buffer_[3 * kInputH * kInputW];
    alignas(64) float output_buffer_[1 * 100 * 7];
    
public:
    void Init(const std::string& model_path) {
        Ort::SessionOptions options;
        options.SetIntraOpNumThreads(2);
        options.SetGraphOptimizationLevel(ORT_ENABLE_ALL);
        
        // Enable CUDA EP if available
        OrtCUDAProviderOptions cuda_opts;
        cuda_opts.device_id = 0;
        options.AppendExecutionProvider_CUDA(cuda_opts);
        
        session_ = new Ort::Session{env_, model_path.c_str(), options};
    }
    
    void RunInference() {
        // Pre-filled input_buffer_ from camera preprocessing
        
        auto memory_info = Ort::MemoryInfo::CreateCpu(
            OrtArenaAllocator, OrtMemTypeDefault);
        
        std::array<int64_t,4> input_shape{1,3,kInputH,kInputW};
        Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
            memory_info, input_buffer_, 3*kInputH*kInputW,
            input_shape.data(), 4);
        
        const char* input_names[]  = {"images"};
        const char* output_names[] = {"output0"};
        
        auto outputs = session_->Run(Ort::RunOptions{nullptr},
                                      input_names, &input_tensor, 1,
                                      output_names, 1);
        
        // Copy to output_buffer_
        auto* data = outputs[0].GetTensorData<float>();
        std::copy(data, data + 100*7, output_buffer_);
    }
};
```

---

## 4. Model Versioning and OTA

```
ECU Flash Layout:
  Partition A: Current model (active)  128MB
  Partition B: OTA candidate           128MB
  Partition C: Factory fallback        128MB (read-only)

OTA Update Flow:
  1. Cloud server signs new model binary (HSM private key)
  2. Vehicle downloads to Partition B (background, WiFi)
  3. ECU verifies signature (public key in ECU eFuse)
  4. Run self-test: inference on 50 stored reference images
     → output must match stored reference outputs ± tolerance
  5. If pass: swap active partition (A↔B)
  6. If fail: revert to A; log DTC P1A01 "AI Model Update Failed"
```

---

## 5. Production Monitoring (Log-based)

```python
class InferenceHealthMonitor:
    """Monitor AI inference quality in production vehicle.
    
    Logs anomalies for OTA analytics and potential retraining triggers."""
    
    def __init__(self, conf_threshold: float = 0.4,
                  window_frames: int = 100):
        self._conf_history = []
        self._window = window_frames
        self._threshold = conf_threshold
    
    def update(self, detections: list):
        """Record confidence distribution per frame."""
        confs = [d['confidence'] for d in detections if d['confidence'] > 0.1]
        self._conf_history.append(confs)
        
        if len(self._conf_history) > self._window:
            self._conf_history.pop(0)
    
    def mean_confidence(self) -> float:
        all_confs = [c for frame in self._conf_history for c in frame]
        return float(sum(all_confs) / max(len(all_confs), 1))
    
    def detect_distribution_drift(self,
                                    baseline_mean: float = 0.75) -> bool:
        """Flag if mean confidence drops significantly (possible domain shift)."""
        return self.mean_confidence() < baseline_mean * 0.8
```

---

## 6. Interview Q&A

### L1
**Q: What is the difference between TensorRT and ONNX Runtime for ECU deployment?**  
A: TensorRT (NVIDIA): NVIDIA-specific optimisation library that fuses layers, applies INT8/FP16 precision, and generates a device-specific .trt engine; best performance on Jetson/Drive hardware; requires TRT installed on target ECU; engine is not portable across GPU generations. ONNX Runtime (Microsoft): cross-platform inference runtime supporting many hardware backends via Execution Providers (CUDA, TensorRT, OpenVINO, TIDL); more portable — same model binary runs on multiple hardware; slightly higher overhead than hand-optimised TRT. Production: use TensorRT EP inside ONNX Runtime for NVIDIA hardware — get portability + TRT optimisation.

### L2
**Q: How is an AI model updated over-the-air while maintaining ASIL compliance?**  
A: (1) Model binary is cryptographically signed (SHA-256 hash signed with OEM private key stored in HSM). (2) Vehicle ECU validates signature before flash using public key burned into ECU eFuse — prevents tampered models. (3) A/B partitioning: new model written to inactive partition; never overwrites active model until validation passes. (4) Post-flash self-test: ECU runs inference on N stored golden inputs, compares outputs to stored references ± acceptable tolerance. (5) Fallback: factory partition always available (write-protected) for hard reset. (6) DTC logging: model version hash + validation result logged to extended diagnostic memory — traceable for liability/recall purposes. (7) ISO 26262 SW element version tracking: each model update requires regression testing signed off by safety engineer (reflected in ASIL assessment).

### L3
**Q: Design an embedded AI pipeline for a front camera ECU (40W budget, 30Hz, ASIL-A).**  
A: (1) Hardware: TDA4VM ECU, 4GB LPDDR4, 128MB NOR Flash for code + 1GB eMMC for AI models; 2× MMA cores for inference. (2) Camera input: 8MP RCCB sensor, ISP via dedicated TDA4VM ISP → resized to 640×640 via hardware scaler (zero CPU cost). (3) AI inference: YOLOv8n INT8 via TIDL on MMA; 8ms inference per frame at 30Hz → 25% MMA utilisation (headroom for second model — lane segmentation). (4) Pipeline: ARM A72 handles: camera DMA, preprocessing, post-processing (NMS, tracking), CAN output; C71x DSP: handles radar preprocessing in parallel. (5) Memory: static allocation at boot — no malloc in hot path; ring buffer (8 frames, 640×640×3 = 15MB) for async pipeline. (6) Safety: ARM R5F runs diagnostic watchdog (pings A72 every 10ms); if missed → safe state (output = "no detection", trigger fault on ADAS CAN bus). (7) ASIL-A: single-point fault detection (watchdog + E2E CRC on CAN output messages); FMEA covers: camera stuck frame, TIDL crash, memory corruption (ECC on LPDDR4).

---

## Files
- Python/C++ code embedded in README above
