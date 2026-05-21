# 03 — C++ for Automotive AI

## Overview
Production C++17/20 patterns for AI inference on automotive-grade ECUs. Covers memory management, SIMD optimisation, TensorRT C++ API, ONNX Runtime, and multi-threaded producer-consumer pipelines.

**Hardware targets:** NVIDIA Drive Orin, Jetson Orin NX, TDA4VM (ARM A72), S32G (Cortex-A53)  
**Standards:** ISO 26262, AUTOSAR Adaptive R21-11, MISRA C++ 2023

---

## 1. Why C++ for ECU AI Inference?

| Concern | Python | C++17 |
|---------|--------|-------|
| Memory allocation | Runtime GC | Static pool (deterministic) |
| Latency | 5-50ms overhead | <1ms overhead |
| MISRA compliance | Impossible | Achievable |
| Real-time OS compatibility | No | Yes (POSIX RT, QNX) |
| ISO 26262 ASIL-D | Not certifiable | Certifiable with tool qualification |

---

## 2. Memory Management Rules for Safety-Critical AI

```cpp
// RULE 1: Pre-allocate ALL buffers at startup
// RULE 2: Never call new/malloc in inference hot path
// RULE 3: Use static arrays or custom memory pools

// BAD — dynamic allocation in hot path (forbidden in ASIL-B+):
void process_frame(const uint8_t* in) {
    float* buffer = new float[640*384*3];  // VIOLATION
    // ...
    delete[] buffer;
}

// GOOD — pre-allocated static pool:
static float g_input_buffer[640*384*3];   // stack or BSS segment
static float g_output_buffer[256];

void process_frame(const uint8_t* in) {
    preprocess(in, g_input_buffer);        // no allocation
    engine.infer(g_input_buffer, g_output_buffer);
}
```

### RAII for CUDA resources:
```cpp
struct CudaBuffer {
    void* ptr = nullptr;
    explicit CudaBuffer(size_t bytes) { cudaMalloc(&ptr, bytes); }
    ~CudaBuffer() { if (ptr) cudaFree(ptr); }
    CudaBuffer(const CudaBuffer&) = delete;
    CudaBuffer& operator=(const CudaBuffer&) = delete;
};
// RAII guarantees cudaFree() on any exit path (exception, early return)
```

---

## 3. SIMD Optimisation (ARM NEON / SSE2)

### Auto-vectorisation (GCC/Clang with -O3):
```cpp
// This loop is auto-vectorised to NEON on ARM (processes 4 floats per cycle):
void normalise(const float* __restrict__ in, float* __restrict__ out,
               int n, float mean, float std) noexcept {
    float inv_std = 1.0f / std;
    for (int i = 0; i < n; ++i) {
        out[i] = (in[i] - mean) * inv_std;   // 4-wide NEON VMUL/VSUB
    }
}
// Compile: g++ -O3 -march=armv8-a+simd -ffast-math
// Verify: g++ -O3 -march=armv8-a+simd -fopt-info-vec normalise.cpp
```

### Manual NEON intrinsics (when compiler misses opportunity):
```cpp
#include <arm_neon.h>

void bgr_to_rgb_neon(const uint8_t* bgr, uint8_t* rgb, int n_pixels) {
    // Process 16 pixels per iteration using NEON 128-bit registers
    for (int i = 0; i < n_pixels; i += 16) {
        uint8x16x3_t pix = vld3q_u8(bgr + i*3);  // Deinterleaved BGR load
        std::swap(pix.val[0], pix.val[2]);          // Swap B <-> R channels
        vst3q_u8(rgb + i*3, pix);                   // Store RGB
    }
}
```

---

## 4. TensorRT C++ API

### Full build + inference workflow:
```cpp
// Step 1: Build engine from ONNX (run once, cache .engine file)
nvinfer1::IBuilder* builder = nvinfer1::createInferBuilder(gLogger);
nvinfer1::INetworkDefinition* network = builder->createNetworkV2(
    1U << static_cast<int>(nvinfer1::NetworkDefinitionCreationFlag::kEXPLICIT_BATCH));

nvonnxparser::IParser* parser = nvonnxparser::createParser(*network, gLogger);
parser->parseFromFile("model.onnx", 2);  // verbosity = 2

nvinfer1::IBuilderConfig* config = builder->createBuilderConfig();
config->setMemoryPoolLimit(nvinfer1::MemoryPoolType::kWORKSPACE, 1ULL << 30); // 1GB
if (builder->platformHasFastFp16()) config->setFlag(nvinfer1::BuilderFlag::kFP16);

nvinfer1::IHostMemory* serialized = builder->buildSerializedNetwork(*network, *config);
// Save to file:
std::ofstream f("model.engine", std::ios::binary);
f.write(static_cast<const char*>(serialized->data()), serialized->size());

// Step 2: Load + infer (every ECU startup)
nvinfer1::IRuntime* runtime = nvinfer1::createInferRuntime(gLogger);
std::vector<char> engine_data = load_engine_file("model.engine");
nvinfer1::ICudaEngine* engine = runtime->deserializeCudaEngine(
    engine_data.data(), engine_data.size());
nvinfer1::IExecutionContext* context = engine->createExecutionContext();

// Step 3: Bind I/O buffers and run
void* d_input;  void* d_output;
cudaMalloc(&d_input,  1*3*384*640*sizeof(float));
cudaMalloc(&d_output, 1*256*sizeof(float));

cudaStream_t stream; cudaStreamCreate(&stream);

cudaMemcpyAsync(d_input, h_input, input_bytes, cudaMemcpyHostToDevice, stream);
void* bindings[] = {d_input, d_output};
context->enqueueV3(stream);  // TRT 8.5+ API
cudaMemcpyAsync(h_output, d_output, output_bytes, cudaMemcpyDeviceToHost, stream);
cudaStreamSynchronize(stream);
```

---

## 5. ONNX Runtime C++ (non-NVIDIA targets)

```cpp
#include <onnxruntime_cxx_api.h>

Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "adas");
Ort::SessionOptions opts;
opts.SetIntraOpNumThreads(4);
opts.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);

// For TDA4VM (TI): use TIDLExecutionProvider
// OrtSessionOptionsAppendExecutionProvider_TIDL(opts, 0);

Ort::Session session(env, "model.onnx", opts);

// Prepare input tensor
auto mem_info = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
int64_t shape[] = {1, 3, 384, 640};
Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
    mem_info, input_data.data(), input_data.size(), shape, 4);

const char* input_names[]  = {"input"};
const char* output_names[] = {"output"};

auto results = session.Run(Ort::RunOptions{nullptr},
    input_names, &input_tensor, 1, output_names, 1);
float* output = results[0].GetTensorMutableData<float>();
```

---

## 6. Multi-Threaded Producer-Consumer Pipeline

```
┌─────────────┐      RingBuffer<Frame,3>      ┌──────────────────┐
│ Camera ISP  │ ──────────────────────────────▶ │ Inference Thread │
│ Thread      │        (lock-free SPSC)          │ (GPU/DSP)        │
│ CPU Core 0  │                                  │ CPU Core 2 + GPU │
└─────────────┘                                  └──────────────────┘
                                                          │
                                               Detection results
                                                          ▼
                                               ┌──────────────────┐
                                               │ ADAS Control     │
                                               │ Thread (LKA/ACC) │
                                               └──────────────────┘
```

### Thread priority and CPU affinity:
```cpp
#include <pthread.h>
#include <sched.h>

void set_realtime(pthread_t thread, int core_id, int rt_priority) {
    // CPU affinity
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset); CPU_SET(core_id, &cpuset);
    pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset);

    // Real-time priority (SCHED_FIFO)
    sched_param sp;
    sp.sched_priority = rt_priority;   // 1–99 (99 = highest)
    pthread_setschedparam(thread, SCHED_FIFO, &sp);
}
```

---

## 7. CMakeLists.txt for ECU AI Engine

```cmake
cmake_minimum_required(VERSION 3.18)
project(adas_ai_engine CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_BUILD_TYPE Release)
add_compile_options(-O3 -march=armv8-a+simd -ffast-math -Wall -Wextra)

# TensorRT
find_path(TRT_INCLUDE NvInfer.h PATHS /usr/include/x86_64-linux-gnu)
find_library(TRT_LIB nvinfer PATHS /usr/lib/x86_64-linux-gnu)
find_package(CUDA REQUIRED)

# ONNX Runtime
set(ORT_ROOT /opt/onnxruntime)
find_library(ORT_LIB onnxruntime PATHS ${ORT_ROOT}/lib)

add_executable(adas_ai_engine ai_inference_engine.cpp)
target_include_directories(adas_ai_engine PRIVATE
    ${TRT_INCLUDE} ${CUDA_INCLUDE_DIRS} ${ORT_ROOT}/include)
target_link_libraries(adas_ai_engine
    ${TRT_LIB} ${CUDA_LIBRARIES} cudart ${ORT_LIB} pthread)
```

---

## 8. Interview Q&A

### L1
**Q: Why is `new`/`malloc` forbidden in ISO 26262 ASIL-D embedded code?**  
A: Dynamic allocation can fail non-deterministically (heap fragmentation, OOM), which violates WCET (Worst Case Execution Time) guarantees. ASIL-D requires deterministic timing. Pre-allocated static pools solve this.

**Q: What is `__restrict__` in C++?**  
A: Tells the compiler that two pointer arguments do NOT alias (don't point to overlapping memory). Enables SIMD vectorisation that would otherwise be blocked by aliasing concerns.

### L2
**Q: Explain TensorRT FP16 vs INT8 inference tradeoffs.**  
A: FP16 halves memory bandwidth and uses tensor cores — typical 2-3× speedup with minimal accuracy loss. INT8 quantises weights/activations to 8-bit integers — 4× memory bandwidth reduction, 2-4× additional speedup, but requires a calibration dataset (1000 representative images) to determine optimal quantisation ranges.

**Q: What is CUDA stream and why use it?**  
A: CUDA streams are ordered queues of GPU operations. Multiple streams execute concurrently. In ADAS pipelines: stream 1 runs H2D copy while stream 2 runs inference on the previous frame → overlaps data transfer with compute, hiding memory latency.

### L3
**Q: How would you deploy a single ONNX model across both NVIDIA Orin and TDA4VM?**  
A: (1) Validate model ops — check ONNX opset compatibility for both TensorRT (NVIDIA) and TIDL (TI). (2) For Orin: build TensorRT .engine with trtexec. (3) For TDA4VM: use TI's TIDL Import Tool to generate layer-by-layer compiled artifacts. (4) Abstract behind a common C++ inference interface (`InferenceEngine::run()`). (5) Profile both: typically TRT is faster for conv-heavy networks, TIDL has lower power budget.

---

## Files
- [ai_inference_engine.cpp](ai_inference_engine.cpp) — Complete TensorRT + ONNX RT inference pipeline
