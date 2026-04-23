#pragma once
#include <gmock/gmock.h>
#include "gear_recommender.h"

class MockGearInput : public IGearSensorInput {
public:
    MOCK_METHOD(float,   GetVehicleSpeedKph,  (), (const, override));
    MOCK_METHOD(float,   GetEngineRpm,        (), (const, override));
    MOCK_METHOD(float,   GetThrottlePercent,  (), (const, override));
    MOCK_METHOD(uint8_t, GetCurrentGear,      (), (const, override));
};
