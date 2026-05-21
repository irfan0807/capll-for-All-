/**
 * 03_CPP_FOR_AUTOMOTIVE_AI — AI Inference Engine for ECU
 * Production C++17 TensorRT + ONNX Runtime inference pipeline
 * Targets: NVIDIA Drive Orin, Jetson Orin NX
 * Compile: g++ -std=c++17 -O3 -o engine ai_inference_engine.cpp
 *          -I/usr/local/cuda/include -L/usr/local/cuda/lib64 -lcuda -lcudart
 *          -lnvinfer -lnvonnxparser
 */

#include <iostream>
#include <fstream>
#include <vector>
#include <memory>
#include <chrono>
#include <array>
#include <cassert>
#include <cstring>
#include <numeric>

// ============================================================================
// 1. FIXED-SIZE MEMORY POOL (no heap in hot path)
// ============================================================================

/**
 * Pre-allocated memory pool for inference buffers.
 * Rule: NEVER call malloc/new in the hot inference path on safety-critical ECUs.
 * ISO 26262 ASIL-B/D: dynamic memory allocation is forbidden in some contexts.
 */
template<typename T, std::size_t MaxSize>
class StaticMemoryPool {
    std::array<T, MaxSize> _storage{};
    std::size_t _used = 0;

public:
    T* allocate(std::size_t n) {
        if (_used + n > MaxSize) {
            return nullptr;  // Silent failure — caller must check
        }
        T* ptr = _storage.data() + _used;
        _used += n;
        return ptr;
    }

    void reset() noexcept { _used = 0; }
    std::size_t available() const noexcept { return MaxSize - _used; }
    std::size_t used() const noexcept { return _used; }
};

// Pre-allocated pool: 4MB for radar/lidar point clouds
constexpr std::size_t POOL_SIZE = 4 * 1024 * 1024 / sizeof(float);
static StaticMemoryPool<float, POOL_SIZE> g_inference_pool;

// ============================================================================
// 2. TENSOR DESCRIPTOR
// ============================================================================

struct TensorDescriptor {
    std::vector<int64_t> shape;
    float* data   = nullptr;
    std::size_t numel() const {
        if (shape.empty()) return 0;
        std::size_t n = 1;
        for (auto d : shape) n *= static_cast<std::size_t>(d);
        return n;
    }
    std::size_t bytes() const { return numel() * sizeof(float); }
};

// ============================================================================
// 3. ONNX RUNTIME INFERENCE ENGINE (CPU/GPU)
// ============================================================================

/**
 * Lightweight ONNX Runtime wrapper for embedded targets.
 * Supports: TDA4VM (ARM A72), S32G (ARM A53), Renesas V3H (ARM A53)
 * When NVIDIA GPU is unavailable, falls back to optimised CPU execution.
 *
 * NOTE: This is a MOCK implementation showing the production interface.
 *       Real deployment requires linking against onnxruntime.so.
 */
class OnnxInferenceEngine {
public:
    struct Config {
        std::string model_path;
        bool        use_gpu       = true;
        int         gpu_device_id = 0;
        int         num_threads   = 4;    // CPU thread pool size
        bool        enable_profiling = false;
    };

    explicit OnnxInferenceEngine(const Config& cfg) : _cfg(cfg) {}

    bool load() {
        // Real ORT: Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "adas");
        //           Ort::SessionOptions opts;
        //           if (_cfg.use_gpu) OrtSessionOptionsAppendExecutionProvider_CUDA(...)
        //           _session = std::make_unique<Ort::Session>(env, _cfg.model_path.c_str(), opts);
        std::cout << "[OnnxEngine] Loading model: " << _cfg.model_path << "\n";
        _loaded = true;
        return true;
    }

    bool run(const TensorDescriptor& input, TensorDescriptor& output) {
        if (!_loaded) return false;
        auto t0 = std::chrono::steady_clock::now();

        // Real ORT:
        //   auto mem_info = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
        //   Ort::Value in_tensor = Ort::Value::CreateTensor<float>(
        //       mem_info, input.data, input.numel(), input.shape.data(), input.shape.size());
        //   auto out_tensors = _session->Run(Ort::RunOptions{nullptr},
        //       input_names.data(), &in_tensor, 1,
        //       output_names.data(), 1);

        // Simulate inference (fill output with zeros)
        if (output.data && output.numel() > 0) {
            std::fill(output.data, output.data + output.numel(), 0.0f);
        }

        auto t1 = std::chrono::steady_clock::now();
        _last_latency_us = std::chrono::duration_cast<std::chrono::microseconds>(t1-t0).count();
        return true;
    }

    int64_t last_latency_us() const noexcept { return _last_latency_us; }

private:
    Config  _cfg;
    bool    _loaded         = false;
    int64_t _last_latency_us = 0;
};

// ============================================================================
// 4. TENSORRT ENGINE (NVIDIA Orin / Drive Orin)
// ============================================================================

/**
 * TensorRT inference engine.
 * Key TRT concepts:
 *   - IRuntime:          parses serialised .engine file
 *   - ICudaEngine:       compiled network optimised for GPU SM architecture
 *   - IExecutionContext: inference execution state (manages CUDA device memory)
 *   - Enqueue:           async GPU execution via CUDA stream
 *
 * Workflow:
 *   1. Build once: .onnx → trtexec → .engine  (takes 2-10 minutes)
 *   2. Deploy: load .engine → bind buffers → enqueueV3() in inference loop
 */
class TensorRTEngine {
public:
    struct Config {
        std::string engine_path;      // Pre-built .engine file
        int         batch_size  = 1;
        bool        use_fp16    = true;   // FP16 on Orin: 2× throughput
        bool        use_int8    = false;  // INT8: 4× throughput, needs calibration
    };

    explicit TensorRTEngine(const Config& cfg) : _cfg(cfg) {}

    bool load() {
        // Real TRT:
        //   nvinfer1::IRuntime* runtime = nvinfer1::createInferRuntime(gLogger);
        //   std::ifstream file(_cfg.engine_path, std::ios::binary|std::ios::ate);
        //   size_t size = file.tellg(); file.seekg(0, std::ios::beg);
        //   std::vector<char> buffer(size); file.read(buffer.data(), size);
        //   _engine.reset(runtime->deserializeCudaEngine(buffer.data(), size));
        //   _context.reset(_engine->createExecutionContext());
        //   cudaStreamCreate(&_stream);
        //   // Allocate GPU buffers (input + output)
        //   cudaMalloc(&_d_input,  input_size_bytes);
        //   cudaMalloc(&_d_output, output_size_bytes);

        std::cout << "[TensorRT] Engine loaded: " << _cfg.engine_path
                  << " (FP16=" << _cfg.use_fp16 << ")\n";
        _loaded = true;
        return true;
    }

    bool infer(const float* h_input, float* h_output,
               int input_size, int output_size) {
        if (!_loaded) return false;

        // Real TRT:
        //   cudaMemcpyAsync(_d_input, h_input, input_size*sizeof(float),
        //                   cudaMemcpyHostToDevice, _stream);
        //   void* bindings[] = {_d_input, _d_output};
        //   _context->enqueueV3(_stream);   // async GPU execution
        //   cudaMemcpyAsync(h_output, _d_output, output_size*sizeof(float),
        //                   cudaMemcpyDeviceToHost, _stream);
        //   cudaStreamSynchronize(_stream);

        // Mock: zero output
        if (h_output && output_size > 0) {
            std::memset(h_output, 0, output_size * sizeof(float));
        }
        return true;
    }

    ~TensorRTEngine() {
        // Real TRT: cudaFree(_d_input); cudaFree(_d_output); cudaStreamDestroy(_stream);
    }

private:
    Config _cfg;
    bool   _loaded = false;
    // Real TRT members:
    // std::unique_ptr<nvinfer1::ICudaEngine>     _engine;
    // std::unique_ptr<nvinfer1::IExecutionContext> _context;
    // void*  _d_input  = nullptr;
    // void*  _d_output = nullptr;
    // cudaStream_t _stream{};
};

// ============================================================================
// 5. IMAGE PRE-PROCESSOR (SIMD-optimised, no heap)
// ============================================================================

/**
 * Camera frame normalisation: BGR uint8 → RGB float32 normalised [0,1].
 * Optimised for ARM Cortex-A72 (TDA4VM) using SIMD-friendly patterns.
 * The compiler auto-vectorises this to NEON/SSE2 with -O3 -march=armv8-a.
 */
struct ImagePreprocessor {
    static constexpr int INPUT_W = 640;
    static constexpr int INPUT_H = 384;
    static constexpr int INPUT_C = 3;
    static constexpr int INPUT_N = INPUT_W * INPUT_H * INPUT_C;

    // ImageNet normalisation parameters (float32)
    static constexpr float MEAN[3] = {0.485f, 0.456f, 0.406f};
    static constexpr float STD[3]  = {0.229f, 0.224f, 0.225f};

    /**
     * in:  (H, W, 3) BGR uint8 at INPUT_H x INPUT_W
     * out: (3, H, W) CHW float32 normalised — pre-allocated by caller
     */
    static void process(const uint8_t* __restrict__ in,
                        float* __restrict__ out) noexcept {
        const float inv255 = 1.0f / 255.0f;
        const int stride   = INPUT_W * INPUT_C;

        for (int h = 0; h < INPUT_H; ++h) {
            for (int w = 0; w < INPUT_W; ++w) {
                const uint8_t* px = in + h * stride + w * INPUT_C;
                // Note: OpenCV is BGR, swap to RGB
                float r = (px[2] * inv255 - MEAN[0]) / STD[0];
                float g = (px[1] * inv255 - MEAN[1]) / STD[1];
                float b = (px[0] * inv255 - MEAN[2]) / STD[2];
                // CHW layout: channel-first for PyTorch/TensorRT
                out[0 * INPUT_H * INPUT_W + h * INPUT_W + w] = r;
                out[1 * INPUT_H * INPUT_W + h * INPUT_W + w] = g;
                out[2 * INPUT_H * INPUT_W + h * INPUT_W + w] = b;
            }
        }
    }
};

// ============================================================================
// 6. PRODUCER-CONSUMER INFERENCE PIPELINE
// ============================================================================

#include <thread>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <queue>

/**
 * Lock-free ring buffer for camera frames (single producer, single consumer).
 * Used between: V4L2 capture thread → inference thread.
 * MaxSlots should be small (2-4) to minimise latency, not maximise throughput.
 */
template<typename T, int MaxSlots = 3>
class RingBuffer {
    std::array<T, MaxSlots> _slots;
    std::atomic<int>        _write_idx{0};
    std::atomic<int>        _read_idx{0};

public:
    bool try_push(const T& item) noexcept {
        int next = (_write_idx.load(std::memory_order_relaxed) + 1) % MaxSlots;
        if (next == _read_idx.load(std::memory_order_acquire)) {
            return false;  // Full — caller drops oldest frame
        }
        _slots[_write_idx.load(std::memory_order_relaxed)] = item;
        _write_idx.store(next, std::memory_order_release);
        return true;
    }

    bool try_pop(T& item) noexcept {
        int cur = _read_idx.load(std::memory_order_relaxed);
        if (cur == _write_idx.load(std::memory_order_acquire)) {
            return false;  // Empty
        }
        item = _slots[cur];
        _read_idx.store((cur + 1) % MaxSlots, std::memory_order_release);
        return true;
    }
};

// ============================================================================
// 7. COMPLETE INFERENCE PIPELINE
// ============================================================================

class AdasAiPipeline {
public:
    static constexpr int INPUT_SIZE  = ImagePreprocessor::INPUT_N;  // 640*384*3
    static constexpr int OUTPUT_SIZE = 256;  // Detection head output (simplified)

    AdasAiPipeline() {
        // Allocate from static pool (no heap)
        _input_buffer  = g_inference_pool.allocate(INPUT_SIZE);
        _output_buffer = g_inference_pool.allocate(OUTPUT_SIZE);
        assert(_input_buffer  != nullptr && "Inference pool exhausted");
        assert(_output_buffer != nullptr && "Inference pool exhausted");
    }

    bool init(const std::string& engine_path) {
        TensorRTEngine::Config cfg;
        cfg.engine_path = engine_path;
        cfg.use_fp16    = true;
        _engine = std::make_unique<TensorRTEngine>(cfg);
        return _engine->load();
    }

    /**
     * Process one camera frame.
     * raw_bgr: (384, 640, 3) uint8 BGR
     * returns: raw output buffer (caller parses detections)
     */
    const float* process_frame(const uint8_t* raw_bgr) {
        auto t0 = std::chrono::steady_clock::now();

        // Pre-process (CPU, SIMD-vectorised)
        ImagePreprocessor::process(raw_bgr, _input_buffer);

        // Inference (GPU async)
        bool ok = _engine->infer(_input_buffer, _output_buffer,
                                  INPUT_SIZE, OUTPUT_SIZE);
        if (!ok) return nullptr;

        auto t1 = std::chrono::steady_clock::now();
        _last_latency_us = std::chrono::duration_cast<
            std::chrono::microseconds>(t1 - t0).count();

        return _output_buffer;
    }

    int64_t last_latency_us() const noexcept { return _last_latency_us; }

private:
    std::unique_ptr<TensorRTEngine> _engine;
    float*  _input_buffer  = nullptr;
    float*  _output_buffer = nullptr;
    int64_t _last_latency_us = 0;
};

// ============================================================================
// 8. MAIN — DEMO
// ============================================================================

int main() {
    std::cout << "=== ADAS AI Inference Engine (C++17) ===\n\n";

    // 1. Init pipeline
    AdasAiPipeline pipeline;
    if (!pipeline.init("adas_detector_fp16.engine")) {
        std::cerr << "Failed to load engine\n";
        return 1;
    }

    // 2. Simulate 100 frames at 20 Hz
    std::vector<uint8_t> fake_frame(640 * 384 * 3, 128);  // Only allocation is here

    int64_t total_us = 0;
    constexpr int N_FRAMES = 100;

    for (int i = 0; i < N_FRAMES; ++i) {
        const float* output = pipeline.process_frame(fake_frame.data());
        total_us += pipeline.last_latency_us();

        if (i % 20 == 0) {
            std::cout << "Frame " << i
                      << " latency: " << pipeline.last_latency_us() << " us\n";
        }
    }

    std::cout << "\nAverage latency: " << (total_us / N_FRAMES) << " us ("
              << (total_us / N_FRAMES / 1000.0) << " ms)\n";

    // 3. Memory pool stats
    std::cout << "Pool used: " << g_inference_pool.used() << " floats ("
              << g_inference_pool.used() * sizeof(float) / 1024 << " KB)\n";
    std::cout << "Pool remaining: " << g_inference_pool.available() << " floats\n";

    // 4. ONNX Runtime path (non-NVIDIA targets)
    OnnxInferenceEngine::Config ort_cfg;
    ort_cfg.model_path = "adas_detector.onnx";
    ort_cfg.use_gpu    = false;
    ort_cfg.num_threads = 4;
    OnnxInferenceEngine ort_engine(ort_cfg);
    ort_engine.load();

    TensorDescriptor in_desc, out_desc;
    in_desc.shape  = {1, 3, 384, 640};
    out_desc.shape = {1, 256};

    in_desc.data  = g_inference_pool.allocate(in_desc.numel());
    out_desc.data = g_inference_pool.allocate(out_desc.numel());

    if (in_desc.data && out_desc.data) {
        ort_engine.run(in_desc, out_desc);
        std::cout << "\nONNX Runtime inference: "
                  << ort_engine.last_latency_us() << " us\n";
    }

    return 0;
}
