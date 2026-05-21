/**
 * Module 44 — AI Inference Engine for ECU
 * Hardware: TI TDA4VM (ARM Cortex-A72) / Jetson Orin NX
 * Standards: ISO 26262 ASIL-A, MISRA C++23 compatible patterns
 *
 * Build: g++ -std=c++17 -O2 -o ecu_inference ecu_inference_engine.cpp
 * Note: ONNX Runtime and TIDL headers required for production build.
 *       This file compiles standalone as a reference/simulation.
 */

#include <array>
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

// ──────────────────────────────────────────────────────────────────────────────
// Constants
// ──────────────────────────────────────────────────────────────────────────────

static constexpr int   MAX_DETECTIONS     = 64;
static constexpr int   NUM_CLASSES        = 5;   // Car, Ped, Cyclist, Van, Truck
static constexpr float CONF_THRESHOLD     = 0.45f;
static constexpr float NMS_IOU_THRESHOLD  = 0.45f;
static constexpr int   INPUT_H            = 640;
static constexpr int   INPUT_W            = 640;
static constexpr int   INPUT_C            = 3;
static constexpr std::size_t INPUT_SIZE   = static_cast<std::size_t>(INPUT_H) *
                                             INPUT_W * INPUT_C;

// ──────────────────────────────────────────────────────────────────────────────
// Data Structures (no dynamic allocation in hot path)
// ──────────────────────────────────────────────────────────────────────────────

struct Detection {
    float x1{0.f}, y1{0.f}, x2{0.f}, y2{0.f};
    float confidence{0.f};
    int   class_id{-1};
    float range_m{0.f};        // Computed from box height via camera model
    float lateral_m{0.f};      // Computed from box centre-x via camera model
};

struct InferenceResult {
    std::array<Detection, MAX_DETECTIONS> detections{};
    int   num_detections{0};
    float inference_ms{0.f};
    bool  valid{false};
};

// ──────────────────────────────────────────────────────────────────────────────
// Camera Model (pinhole) — converts pixel position to real-world range
// ──────────────────────────────────────────────────────────────────────────────

struct CameraModel {
    float fx{950.f};     // Focal length x (pixels)
    float fy{950.f};     // Focal length y (pixels)
    float cx{960.f};     // Principal point x (pixels) — for 1920px width
    float cy{540.f};     // Principal point y (pixels) — for 1080px height
    float height_m{1.4f};// Camera mounting height (metres)
    float pitch_rad{0.f};// Camera tilt (radians, positive = downward)

    float compute_range(float box_y2_pixel) const {
        // Ground-touch point range via inverse perspective
        // tan(pitch + atan2(cy - y2, fy)) * height = range
        float angle_rad = pitch_rad + std::atan2(cy - box_y2_pixel, fy);
        if (std::abs(angle_rad) < 1e-4f) { return 999.f; }
        return height_m / std::tan(angle_rad);
    }

    float compute_lateral(float box_cx_pixel) const {
        // Use range ≈ 30m average assumption for lateral estimate
        constexpr float nominal_range_m = 30.f;
        return (box_cx_pixel - cx) / fx * nominal_range_m;
    }
};

// ──────────────────────────────────────────────────────────────────────────────
// Static Memory Pool (avoid heap allocation in safety-critical paths)
// ──────────────────────────────────────────────────────────────────────────────

class StaticPool {
public:
    // Pre-allocate maximum possible tensors
    alignas(64) float input_tensor[INPUT_SIZE];
    // Raw model output: [1, 8400, (4 + NUM_CLASSES)] for YOLOv8 640×640
    static constexpr int GRID_CELLS = 8400;
    static constexpr int PRED_DIM   = 4 + NUM_CLASSES;
    alignas(64) float raw_output[GRID_CELLS * PRED_DIM];

    // Decode buffer
    std::array<Detection, MAX_DETECTIONS * 4> decode_buf{};  // Pre-NMS
    int decode_count{0};
};

// ──────────────────────────────────────────────────────────────────────────────
// Preprocessing
// ──────────────────────────────────────────────────────────────────────────────

// ImageNet normalisation constants
static constexpr float MEAN_R = 0.485f, MEAN_G = 0.456f, MEAN_B = 0.406f;
static constexpr float STD_R  = 0.229f, STD_G  = 0.224f, STD_B  = 0.225f;

void preprocess_frame(const uint8_t* bgr_hwc,
                      int src_h, int src_w,
                      float* out_chw) {
    /**
     * Resize (letterbox) + BGR→RGB + normalise → NCHW float32
     * Production: replace with CUDA kernel for 0.5ms latency.
     */
    const float scale   = std::min(
        static_cast<float>(INPUT_H) / src_h,
        static_cast<float>(INPUT_W) / src_w);
    const int   nh      = static_cast<int>(src_h * scale);
    const int   nw      = static_cast<int>(src_w * scale);
    const int   pad_y   = (INPUT_H - nh) / 2;
    const int   pad_x   = (INPUT_W - nw) / 2;

    // Fill with padding value (normalised 114/255)
    const float pad_val = (114.f / 255.f - MEAN_R) / STD_R;
    std::fill(out_chw, out_chw + INPUT_SIZE, pad_val);

    // Fill channels (simplified nearest-neighbour resize)
    for (int y = 0; y < nh; ++y) {
        const int src_y = static_cast<int>(y / scale);
        for (int x = 0; x < nw; ++x) {
            const int src_x    = static_cast<int>(x / scale);
            const int src_idx  = (src_y * src_w + src_x) * 3;
            const int dst_y    = y + pad_y;
            const int dst_x    = x + pad_x;

            // BGR → RGB, normalise
            const float r = (bgr_hwc[src_idx + 2] / 255.f - MEAN_R) / STD_R;
            const float g = (bgr_hwc[src_idx + 1] / 255.f - MEAN_G) / STD_G;
            const float b = (bgr_hwc[src_idx + 0] / 255.f - MEAN_B) / STD_B;

            out_chw[0 * INPUT_H * INPUT_W + dst_y * INPUT_W + dst_x] = r;
            out_chw[1 * INPUT_H * INPUT_W + dst_y * INPUT_W + dst_x] = g;
            out_chw[2 * INPUT_H * INPUT_W + dst_y * INPUT_W + dst_x] = b;
        }
    }
}

// ──────────────────────────────────────────────────────────────────────────────
// Decode YOLOv8 raw output
// ──────────────────────────────────────────────────────────────────────────────

static inline float sigmoid(float x) {
    return 1.f / (1.f + std::exp(-x));
}

int decode_yolov8_output(const float* raw,
                          int grid_cells, int pred_dim,
                          Detection* out_buf, int max_out,
                          float conf_thresh) {
    /**
     * YOLOv8 output: [grid_cells, 4 + num_classes]
     * Boxes already decoded (cx,cy,w,h) in model output (not anchors).
     * Class probabilities need sigmoid.
     */
    int count = 0;
    for (int i = 0; i < grid_cells && count < max_out; ++i) {
        const float* pred = raw + i * pred_dim;
        const float  cx   = pred[0], cy = pred[1];
        const float  bw   = pred[2], bh = pred[3];

        // Find best class
        int   best_cls  = -1;
        float best_prob = 0.f;
        for (int c = 0; c < NUM_CLASSES; ++c) {
            const float prob = sigmoid(pred[4 + c]);
            if (prob > best_prob) { best_prob = prob; best_cls = c; }
        }

        if (best_prob < conf_thresh) { continue; }

        Detection& d = out_buf[count++];
        d.x1         = cx - bw * 0.5f;
        d.y1         = cy - bh * 0.5f;
        d.x2         = cx + bw * 0.5f;
        d.y2         = cy + bh * 0.5f;
        d.confidence = best_prob;
        d.class_id   = best_cls;
    }
    return count;
}

// ──────────────────────────────────────────────────────────────────────────────
// NMS
// ──────────────────────────────────────────────────────────────────────────────

static float compute_iou(const Detection& a, const Detection& b) {
    const float ix1  = std::max(a.x1, b.x1);
    const float iy1  = std::max(a.y1, b.y1);
    const float ix2  = std::min(a.x2, b.x2);
    const float iy2  = std::min(a.y2, b.y2);
    const float inter = std::max(0.f, ix2-ix1) * std::max(0.f, iy2-iy1);
    const float area_a = (a.x2-a.x1) * (a.y2-a.y1);
    const float area_b = (b.x2-b.x1) * (b.y2-b.y1);
    return inter / (area_a + area_b - inter + 1e-7f);
}

int apply_nms(Detection* dets, int n, float iou_thresh) {
    // Sort by confidence descending (in-place)
    std::sort(dets, dets + n, [](const Detection& a, const Detection& b) {
        return a.confidence > b.confidence;
    });

    static bool suppressed[MAX_DETECTIONS * 4];
    std::fill(suppressed, suppressed + n, false);

    int kept = 0;
    for (int i = 0; i < n; ++i) {
        if (suppressed[i]) { continue; }
        ++kept;
        for (int j = i + 1; j < n; ++j) {
            if (suppressed[j]) { continue; }
            if (dets[i].class_id == dets[j].class_id &&
                compute_iou(dets[i], dets[j]) > iou_thresh) {
                suppressed[j] = true;
            }
        }
    }

    // Compact kept detections to front
    int write = 0;
    for (int i = 0; i < n; ++i) {
        if (!suppressed[i]) { dets[write++] = dets[i]; }
    }
    return kept;
}

// ──────────────────────────────────────────────────────────────────────────────
// Main Inference Engine
// ──────────────────────────────────────────────────────────────────────────────

class AdasEcuInferenceEngine {
public:
    explicit AdasEcuInferenceEngine(const CameraModel& cam)
        : cam_model_(cam)
    {
        std::cout << "[Engine] Initialised (standalone/simulation mode)\n";
    }

    InferenceResult run(const uint8_t* bgr_frame,
                        int frame_h, int frame_w) {
        InferenceResult result{};
        auto t0 = std::chrono::steady_clock::now();

        // Step 1: Preprocess
        preprocess_frame(bgr_frame, frame_h, frame_w, pool_.input_tensor);

        // Step 2: Model inference (simulation — fill with test pattern)
        simulate_inference_output(pool_.raw_output);

        // Step 3: Decode
        pool_.decode_count = decode_yolov8_output(
            pool_.raw_output,
            StaticPool::GRID_CELLS, StaticPool::PRED_DIM,
            pool_.decode_buf.data(),
            static_cast<int>(pool_.decode_buf.size()),
            CONF_THRESHOLD);

        // Step 4: NMS
        int final_count = apply_nms(
            pool_.decode_buf.data(), pool_.decode_count, NMS_IOU_THRESHOLD);
        final_count = std::min(final_count, MAX_DETECTIONS);

        // Step 5: Camera model → range/lateral
        for (int i = 0; i < final_count; ++i) {
            Detection& d = pool_.decode_buf[static_cast<std::size_t>(i)];
            d.range_m   = cam_model_.compute_range(d.y2 * frame_h / INPUT_H);
            d.lateral_m = cam_model_.compute_lateral(
                (d.x1 + d.x2) * 0.5f * frame_w / INPUT_W);
            result.detections[static_cast<std::size_t>(i)] = d;
        }

        result.num_detections = final_count;
        result.valid          = true;

        auto t1 = std::chrono::steady_clock::now();
        result.inference_ms = std::chrono::duration<float, std::milli>(t1-t0).count();

        return result;
    }

private:
    CameraModel cam_model_;
    StaticPool  pool_{};

    static void simulate_inference_output(float* raw) {
        // Simulate 5 strong detections in output grid
        static constexpr int FAKE_N = 5;
        static constexpr float fake_dets[FAKE_N][4 + NUM_CLASSES] = {
            {320, 540, 80,  60,  5.0f, -1.f, -1.f, -1.f, -1.f},  // Car centre
            {160, 530, 40,  50,  -1.f,  5.0f, -1.f, -1.f, -1.f}, // Pedestrian left
            {480, 520, 60,  55,  5.0f, -1.f, -1.f, -1.f, -1.f},  // Car right
            {320, 400, 30,  45,  -1.f, -1.f,  5.0f, -1.f, -1.f}, // Cyclist far
            {100, 560, 25,  40,  -1.f,  4.0f, -1.f, -1.f, -1.f}, // Ped far left
        };
        std::fill(raw, raw + StaticPool::GRID_CELLS * StaticPool::PRED_DIM, -10.f);
        for (int i = 0; i < FAKE_N; ++i) {
            std::copy(fake_dets[i], fake_dets[i] + StaticPool::PRED_DIM,
                      raw + i * StaticPool::PRED_DIM);
        }
    }
};

// ──────────────────────────────────────────────────────────────────────────────
// Watchdog Monitor (ASIL-A requirement)
// ──────────────────────────────────────────────────────────────────────────────

class InferenceWatchdog {
public:
    explicit InferenceWatchdog(float timeout_ms = 50.f)
        : timeout_ms_(timeout_ms) {}

    void kick() {
        last_kick_ = std::chrono::steady_clock::now();
    }

    bool is_alive() const {
        auto elapsed = std::chrono::duration<float, std::milli>(
            std::chrono::steady_clock::now() - last_kick_).count();
        return elapsed < timeout_ms_;
    }

private:
    float timeout_ms_;
    std::chrono::steady_clock::time_point last_kick_{std::chrono::steady_clock::now()};
};

// ──────────────────────────────────────────────────────────────────────────────
// main — demo
// ──────────────────────────────────────────────────────────────────────────────

int main() {
    std::cout << "==============================================\n";
    std::cout << "  ADAS ECU AI Inference Engine (C++17)\n";
    std::cout << "==============================================\n\n";

    // Simulate 1920×1080 frame
    constexpr int FH = 1080, FW = 1920;
    std::vector<uint8_t> fake_frame(static_cast<std::size_t>(FH) * FW * 3, 128u);

    CameraModel cam;
    AdasEcuInferenceEngine engine{cam};
    InferenceWatchdog      watchdog{50.f};

    // Run 10 frames
    float total_ms = 0.f;
    for (int frame_idx = 0; frame_idx < 10; ++frame_idx) {
        auto result = engine.run(fake_frame.data(), FH, FW);
        watchdog.kick();
        total_ms += result.inference_ms;

        if (frame_idx == 0) {
            std::cout << "Frame " << frame_idx
                      << " | " << result.num_detections << " detections"
                      << " | " << result.inference_ms << "ms\n";
            for (int i = 0; i < result.num_detections; ++i) {
                const auto& d = result.detections[static_cast<std::size_t>(i)];
                static const char* classes[] = {
                    "Car","Pedestrian","Cyclist","Van","Truck"};
                std::cout << "  [" << i << "] " << classes[d.class_id]
                          << " conf=" << d.confidence
                          << " range=" << d.range_m << "m"
                          << " lat=" << d.lateral_m << "m\n";
            }
        }
    }

    std::cout << "\nAverage latency over 10 frames: "
              << total_ms / 10.f << "ms\n";
    std::cout << "Watchdog alive: " << (watchdog.is_alive() ? "YES" : "NO") << "\n";
    std::cout << "\nProduction targets:\n"
              << "  TDA4VM TIDL (ARM A72 + C7x): ~10ms\n"
              << "  Jetson Orin NX INT8 TRT:     ~6ms\n"
              << "  Drive Orin DLA+GPU:           ~4ms\n";

    return 0;
}
