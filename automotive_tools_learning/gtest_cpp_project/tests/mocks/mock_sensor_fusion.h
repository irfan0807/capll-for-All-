#pragma once
#include <gmock/gmock.h>
#include "sensor_fusion.h"

class MockSensorFusionInput : public ISensorFusionInput {
public:
    MOCK_METHOD(float, GetRadarRange,     (), (const, override));
    MOCK_METHOD(float, GetCameraRange,    (), (const, override));
    MOCK_METHOD(float, GetObjectVelocity, (), (const, override));
};
