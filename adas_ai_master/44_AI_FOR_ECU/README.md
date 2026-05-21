# 44 — AI for ECU: Embedded Inference Engine

## Overview
End-to-end guide for deploying AI models on automotive ECUs: TI TDA4VM, NVIDIA Jetson Orin NX, Qualcomm Snapdragon Ride, and Renesas V3H. Covers memory constraints, deterministic latency, safety monitors, and CAN output integration.

---

## 1. ECU Hardware Comparison

| ECU | Processor | AI Accelerator | RAM | AI TOPS | Use Case |
|-----|----------|---------------|-----|---------|---------|
| TI TDA4VM | 2× ARM A72 + 6× R5F | C7x DSP (TIDL) | 8GB | ~8 | Camera ECU, AEB |
| Jetson Orin NX 16GB | 8× Cortex-A78AE | 1024-core GPU + 2× DLA | 16GB | 100 | Domain controller |
| NVIDIA Drive Orin | 12× Cortex-A78AE | 2× Ampere GPU + 4× DLA | 32GB | 254 | L3+ domain controller |
| Snapdragon Ride | 4× Cortex-A77 + DSP | Hexagon NPU | 8GB | ~30 | ADAS SoC mid-range |
| Renesas V3H | 4× CA53 + IMP-X5 | Proprietary CNN IP | 4GB | ~4 | Surround camera ECU |

---

## 2. TIDL Deployment (TDA4VM)

### C Reference Code
```c
#include <TI/tivx.h>
#include <TI/j7_tidl.h>

typedef struct {
    vx_context  vx_ctx;
    vx_graph    graph;
    vx_node     tidl_node;
    vx_tensor   input_tensor;
    vx_tensor   output_tensor;
} TidlHandle;

TidlHandle* tidl_init(const char* net_bin, const char* params_bin,
                       int batch, int ch, int h, int w) {
    TidlHandle* hdl = (TidlHandle*)calloc(1, sizeof(TidlHandle));
    hdl->vx_ctx = vxCreateContext();
    
    // Import TIDL network (pre-converted from ONNX via TIDL import tool)
    tivx_tidl_params_t cfg;
    cfg.num_input_tensors  = 1;
    cfg.num_output_tensors = 1;
    cfg.net_file    = net_bin;
    cfg.params_file = params_bin;
    
    // Create input/output tensors
    vx_size dims_in[4]  = {batch, ch, h, w};
    vx_size dims_out[4] = {batch, 85, 8400, 1};  // YOLOv8 output
    hdl->input_tensor  = vxCreateTensor(hdl->vx_ctx, 4, dims_in,
                                          VX_TYPE_INT8, 0);
    hdl->output_tensor = vxCreateTensor(hdl->vx_ctx, 4, dims_out,
                                          VX_TYPE_INT8, 0);
    
    // Build graph
    hdl->graph    = vxCreateGraph(hdl->vx_ctx);
    hdl->tidl_node = tivxTIDLNode(hdl->graph, &cfg,
                                    hdl->input_tensor, hdl->output_tensor);
    vxVerifyGraph(hdl->graph);
    return hdl;
}

int tidl_run(TidlHandle* hdl, const int8_t* input, int8_t* output) {
    vxCopyTensorPatch(hdl->input_tensor, NULL, input,
                       VX_WRITE_ONLY, VX_MEMORY_TYPE_HOST);
    vxProcessGraph(hdl->graph);  // Blocking, ~10ms on TDA4VM
    vxCopyTensorPatch(hdl->output_tensor, NULL, output,
                       VX_READ_ONLY, VX_MEMORY_TYPE_HOST);
    return 0;
}

void tidl_free(TidlHandle* hdl) {
    vxReleaseGraph(&hdl->graph);
    vxReleaseContext(&hdl->vx_ctx);
    free(hdl);
}
```

---

## 3. Memory Budget Analysis

```
Jetson Orin NX 16GB Memory Budget:
  OS + system services:       2.0 GB
  Camera ISP buffers (4×cam): 1.5 GB  (2× triple-buffered 1920×1080)
  Model weights:
    YOLOv8s INT8:             11 MB
    BEV encoder:              45 MB
    TRT engine overhead:      200 MB
  Activations (peak):         800 MB
  Tracker state:              50 MB
  Output buffers:             100 MB
  Safety buffer:              500 MB
  ─────────────────────────────────
  Total:                     ~5.2 GB  ✓ Within 16GB
  
TDA4VM (8GB) Budget:
  OS + RTOS:                  512 MB
  Camera capture (2 cam):     400 MB
  TIDL model:                  8 MB
  TIDL activations:           256 MB
  App SW:                     256 MB
  ─────────────────────────────────
  Total:                     ~1.4 GB  ✓ Within 8GB (headroom for 2 more models)
```

---

## 4. Deterministic Latency

Key requirement for ASIL: inference latency must be deterministic (bounded worst-case).

```cpp
// Latency measurement with worst-case tracking
class LatencyMonitor {
    static constexpr int HIST_SIZE = 1000;
    float history_[HIST_SIZE]{};
    int   idx_{0};
    float max_observed_{0.f};
    
public:
    void record(float ms) {
        history_[idx_++ % HIST_SIZE] = ms;
        max_observed_ = std::max(max_observed_, ms);
        
        // ASIL-A: if worst-case exceeds 20ms → DTC
        if (ms > 20.f) {
            raise_dtc(DTC_INFERENCE_OVERTIME);
        }
    }
    
    float worst_case_ms() const { return max_observed_; }
    float average_ms()    const {
        int n = std::min(idx_, HIST_SIZE);
        float sum = 0.f;
        for (int i = 0; i < n; ++i) sum += history_[i];
        return n > 0 ? sum / n : 0.f;
    }
};
```

---

## 5. CAN FD Output Format

```
// AEB Output message on CAN FD (8 bytes)
// ID: 0x3E9 (1001)
struct AEBOutputMsg {
    uint8_t  aeb_active   : 1;      // bit 0
    uint8_t  reserved     : 7;
    int16_t  deceleration;          // -100 to 0 (×0.1 = m/s²)
    uint16_t ttc_ms;                // Time-to-collision in ms (0-60000)
    uint8_t  obj_class;             // Primary obstacle class
    uint8_t  confidence;            // 0-100 (× 0.01 = fraction)
    uint8_t  rolling_counter : 4;   // E2E liveness
    uint8_t  checksum        : 4;   // Simple XOR checksum
} __attribute__((packed));
```

---

## 6. Build Instructions

```bash
# Standalone simulation (no ONNX/TIDL required)
g++ -std=c++17 -O2 -Wall -o ecu_inference ecu_inference_engine.cpp

# With ONNX Runtime (Jetson/x86)
g++ -std=c++17 -O2 \
    -I/usr/include/onnxruntime \
    -L/usr/lib/aarch64-linux-gnu \
    -lonnxruntime \
    -o ecu_inference_ort ecu_inference_engine.cpp

# With TensorRT (Jetson Orin NX)
g++ -std=c++17 -O2 \
    -I/usr/include/x86_64-linux-gnu \
    -I/usr/local/cuda/include \
    -L/usr/local/cuda/lib64 \
    -lnvinfer -lnvparsers -lcudart \
    -o ecu_inference_trt ecu_inference_engine.cpp
```

---

## Interview Q&A

### L1
**Q: What is the difference between TIDL and TensorRT for ECU deployment?**  
A: TIDL (TI Deep Learning): TI's proprietary inference framework for TDA4VM SoC; uses the C7x DSP + MMA (matrix multiply accelerator); requires TIDL model converter to convert ONNX to TIDL format; tightly integrated with TI's OpenVX pipeline (TIOVX); optimised for TI hardware only. TensorRT: NVIDIA's inference optimizer; runs on NVIDIA GPUs + DLA; auto-optimises ONNX models via layer fusion, INT8 calibration; cross-platform within NVIDIA products (Jetson, Drive); broader model support. Both require same INT8 calibration workflow (representative dataset) before deployment.

### L2
**Q: How do you ensure deterministic inference latency on an embedded ECU?**  
A: (1) Pre-allocate all memory at startup — no malloc in hot path; static memory pool; (2) Avoid cache pollution: process only one model at a time; pin model weights to cache (CUDA cudaMemPrefetchAsync or TDA4VM cache-lock API); (3) CPU isolation: dedicate one CPU core exclusively to inference using CPU affinity (sched_setaffinity) and real-time scheduling (SCHED_FIFO); (4) Latency testing: measure worst-case over 10,000 frames including thermal throttling scenarios (ECU at 85°C); (5) Watchdog: set maximum latency timer (50ms); if exceeded → DTC + fallback to non-AI path; (6) TRT persistence: disable JIT recompilation in production (use cached engine with --serializedEngine).

### L3
**Q: Design the complete software architecture for a camera perception SWC on TDA4VM running at 30Hz.**  
A: AUTOSAR Classic on TDA4VM R5F core (safety monitor) + Linux on A72 core (AI inference). Architecture: (1) R5F: AUTOSAR SWC receives camera ISP output via TIOVX pipeline → triggers inference via IPC to A72 → receives result → applies E2E checks → sends CAN FD message to ADAS domain controller; watchdog monitors A72 heartbeat; (2) A72 (Linux): TIOVX graph with: Camera capture node → ISP node → TIDL inference node (C7x offload) → result copy to shared memory → signal R5F via IPC semaphore; (3) Memory: shared DMA buffer between ISP, C7x, and A72; zero-copy pipeline (avoid memcpy in hot path); (4) Timing: ISP provides frame at t=0ms; TIDL inference by t=10ms; R5F CAN message by t=12ms; total sensor-to-CAN: 12ms (30Hz × 33ms budget); (5) Safety: R5F monitors A72 via heartbeat (50ms timeout → DTC); ASIL-A monitors: rolling counter on CAN output, range plausibility check (object range vs camera model consistency).
