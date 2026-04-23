#include "sensor_fusion.h"
#include <algorithm>

SensorFusion::SensorFusion(ISensorFusionInput& input) : input_(input) {}

FusionResult SensorFusion::FuseObjects() {
    const float radar_range  = input_.GetRadarRange();
    const float camera_range = input_.GetCameraRange();
    const float velocity     = input_.GetObjectVelocity();

    FusionResult result{};

    // Guard against NaN / Inf distance inputs
    bool radar_valid  = !std::isnan(radar_range)  && !std::isinf(radar_range)  && radar_range  >= 0.0f;
    bool camera_valid = !std::isnan(camera_range) && !std::isinf(camera_range) && camera_range >= 0.0f;

    if (radar_valid && camera_valid) {
        result.estimated_distance = (radar_range * 0.6f) + (camera_range * 0.4f);
        result.confidence         = ConfidenceLevel::HIGH;
    } else if (radar_valid) {
        result.estimated_distance = radar_range;
        result.confidence         = ConfidenceLevel::MEDIUM;
    } else if (camera_valid) {
        result.estimated_distance = camera_range;
        result.confidence         = ConfidenceLevel::LOW;
    } else {
        result.estimated_distance = 0.0f;
        result.confidence         = ConfidenceLevel::LOW;
    }

    // Clamp velocity to physical maximum
    if (std::isnan(velocity) || std::isinf(velocity)) {
        result.estimated_velocity = 0.0f;
        result.confidence         = ConfidenceLevel::LOW;
    } else {
        result.estimated_velocity = std::min(velocity, MAX_VALID_VELOCITY);
    }

    return result;
}
