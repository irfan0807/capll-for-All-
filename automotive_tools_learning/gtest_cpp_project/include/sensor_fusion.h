#pragma once
#include <cstdint>
#include <cmath>

enum class ConfidenceLevel : uint8_t { HIGH = 0, MEDIUM = 1, LOW = 2 };

struct FusionResult {
    float          estimated_distance;   // metres
    float          estimated_velocity;   // m/s
    ConfidenceLevel confidence;
};

// ─────────────────────────────────────────────────────────────
//  ISensorFusionInput  –  interface for radar + camera data
// ─────────────────────────────────────────────────────────────
class ISensorFusionInput {
public:
    virtual ~ISensorFusionInput() = default;
    virtual float GetRadarRange()    const = 0;
    virtual float GetCameraRange()   const = 0;
    virtual float GetObjectVelocity() const = 0;
};

// ─────────────────────────────────────────────────────────────
//  SensorFusion  –  radar + camera object fusion
// ─────────────────────────────────────────────────────────────
class SensorFusion {
public:
    static constexpr float MAX_VALID_VELOCITY = 83.33f;  // 300 km/h in m/s

    explicit SensorFusion(ISensorFusionInput& input);

    FusionResult FuseObjects();

private:
    ISensorFusionInput& input_;
};
