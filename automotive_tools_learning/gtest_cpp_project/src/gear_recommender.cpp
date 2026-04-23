#include "gear_recommender.h"

GearRecommender::GearRecommender(IGearSensorInput& input) : input_(input) {}

uint8_t GearRecommender::RecommendedGear() {
    const float   speed    = input_.GetVehicleSpeedKph();
    const float   rpm      = input_.GetEngineRpm();
    const float   throttle = input_.GetThrottlePercent();
    const uint8_t gear     = input_.GetCurrentGear();

    if (ShouldUpshift(speed, rpm, throttle, gear)) {
        return std::min(static_cast<uint8_t>(gear + 1), MAX_GEAR);
    }
    if (ShouldDownshift(speed, rpm, throttle, gear)) {
        return std::max(static_cast<uint8_t>(gear - 1), MIN_GEAR);
    }
    return 0;  // 0 = no change
}

bool GearRecommender::ShouldUpshift(float /*speed*/, float rpm,
                                     float throttle, uint8_t gear) const {
    if (gear >= MAX_GEAR) return false;
    // Upshift if RPM is high and driver is not flooring it
    return (rpm > 3500.0f && throttle < 80.0f);
}

bool GearRecommender::ShouldDownshift(float /*speed*/, float rpm,
                                       float throttle, uint8_t gear) const {
    if (gear <= MIN_GEAR) return false;
    // Downshift if RPM is low or driver demands power at low RPM
    return (rpm < 1500.0f || (throttle > 90.0f && rpm < 2500.0f));
}
