#pragma once
#include <cstdint>

// ─────────────────────────────────────────────────────────────
//  IGearSensorInput  –  interface for vehicle signals
// ─────────────────────────────────────────────────────────────
class IGearSensorInput {
public:
    virtual ~IGearSensorInput() = default;
    virtual float    GetVehicleSpeedKph()    const = 0;
    virtual float    GetEngineRpm()          const = 0;
    virtual float    GetThrottlePercent()    const = 0;
    virtual uint8_t  GetCurrentGear()        const = 0;
};

// ─────────────────────────────────────────────────────────────
//  GearRecommender  –  gear shift recommendation logic (AUTOSAR SWC)
// ─────────────────────────────────────────────────────────────
class GearRecommender {
public:
    static constexpr uint8_t MIN_GEAR = 1;
    static constexpr uint8_t MAX_GEAR = 8;

    explicit GearRecommender(IGearSensorInput& input);

    uint8_t RecommendedGear();   // returns 0 = no change, else target gear

private:
    IGearSensorInput& input_;

    bool ShouldUpshift(float speed_kph, float rpm, float throttle,
                       uint8_t current_gear) const;
    bool ShouldDownshift(float speed_kph, float rpm, float throttle,
                          uint8_t current_gear) const;
};
