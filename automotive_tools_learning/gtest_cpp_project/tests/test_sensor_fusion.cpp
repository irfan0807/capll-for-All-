// ─────────────────────────────────────────────────────────────────────────────
//  Sensor Fusion Tests  –  GMock injection of radar/camera data
//  IEEE 754 edge cases: NaN, Inf, negative, nominal
// ─────────────────────────────────────────────────────────────────────────────
#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include "sensor_fusion.h"
#include "mocks/mock_sensor_fusion.h"
#include <limits>
#include <cmath>

using ::testing::Return;
using ::testing::NiceMock;

class SensorFusionTest : public ::testing::Test {
protected:
    NiceMock<MockSensorFusionInput> mock_input_;

    SensorFusion MakeFusion() { return SensorFusion(mock_input_); }
};

// ─── Nominal fusion ───────────────────────────────────────────

TEST_F(SensorFusionTest, BothSensorsValidGivesHighConfidence) {
    ON_CALL(mock_input_, GetRadarRange()).WillByDefault(Return(50.0f));
    ON_CALL(mock_input_, GetCameraRange()).WillByDefault(Return(55.0f));
    ON_CALL(mock_input_, GetObjectVelocity()).WillByDefault(Return(10.0f));

    auto fusion = MakeFusion();
    auto result = fusion.FuseObjects();

    EXPECT_EQ(result.confidence, ConfidenceLevel::HIGH);
    // Expected: 50*0.6 + 55*0.4 = 30 + 22 = 52
    EXPECT_NEAR(result.estimated_distance, 52.0f, 0.01f);
    EXPECT_NEAR(result.estimated_velocity, 10.0f, 0.01f);
}

// ─── IEEE 754 edge cases ──────────────────────────────────────

TEST_F(SensorFusionTest, NaN_RadarInput_FallsBackToCameraLowConfidence) {
    ON_CALL(mock_input_, GetRadarRange())
        .WillByDefault(Return(std::numeric_limits<float>::quiet_NaN()));
    ON_CALL(mock_input_, GetCameraRange()).WillByDefault(Return(40.0f));
    ON_CALL(mock_input_, GetObjectVelocity()).WillByDefault(Return(5.0f));

    auto fusion = MakeFusion();
    auto result = fusion.FuseObjects();

    EXPECT_FALSE(std::isnan(result.estimated_distance));
    EXPECT_EQ(result.confidence, ConfidenceLevel::LOW);
    EXPECT_NEAR(result.estimated_distance, 40.0f, 0.01f);
}

TEST_F(SensorFusionTest, Inf_Velocity_ClampedToMaxValid) {
    ON_CALL(mock_input_, GetRadarRange()).WillByDefault(Return(30.0f));
    ON_CALL(mock_input_, GetCameraRange()).WillByDefault(Return(30.0f));
    ON_CALL(mock_input_, GetObjectVelocity())
        .WillByDefault(Return(std::numeric_limits<float>::infinity()));

    auto fusion = MakeFusion();
    auto result = fusion.FuseObjects();

    EXPECT_LE(result.estimated_velocity, SensorFusion::MAX_VALID_VELOCITY);
    EXPECT_FALSE(std::isinf(result.estimated_velocity));
}

TEST_F(SensorFusionTest, NaN_Velocity_SetsLowConfidence) {
    ON_CALL(mock_input_, GetRadarRange()).WillByDefault(Return(30.0f));
    ON_CALL(mock_input_, GetCameraRange()).WillByDefault(Return(30.0f));
    ON_CALL(mock_input_, GetObjectVelocity())
        .WillByDefault(Return(std::numeric_limits<float>::quiet_NaN()));

    auto fusion = MakeFusion();
    auto result = fusion.FuseObjects();

    EXPECT_FALSE(std::isnan(result.estimated_velocity));
    EXPECT_EQ(result.confidence, ConfidenceLevel::LOW);
}

TEST_F(SensorFusionTest, BothSensors_NaN_GivesZeroDistanceLowConfidence) {
    ON_CALL(mock_input_, GetRadarRange())
        .WillByDefault(Return(std::numeric_limits<float>::quiet_NaN()));
    ON_CALL(mock_input_, GetCameraRange())
        .WillByDefault(Return(std::numeric_limits<float>::quiet_NaN()));
    ON_CALL(mock_input_, GetObjectVelocity()).WillByDefault(Return(5.0f));

    auto fusion = MakeFusion();
    auto result = fusion.FuseObjects();

    EXPECT_FLOAT_EQ(result.estimated_distance, 0.0f);
    EXPECT_EQ(result.confidence, ConfidenceLevel::LOW);
}

TEST_F(SensorFusionTest, OnlyRadarValidGivesMediumConfidence) {
    ON_CALL(mock_input_, GetRadarRange()).WillByDefault(Return(60.0f));
    ON_CALL(mock_input_, GetCameraRange())
        .WillByDefault(Return(std::numeric_limits<float>::quiet_NaN()));
    ON_CALL(mock_input_, GetObjectVelocity()).WillByDefault(Return(15.0f));

    auto fusion = MakeFusion();
    auto result = fusion.FuseObjects();

    EXPECT_EQ(result.confidence, ConfidenceLevel::MEDIUM);
    EXPECT_NEAR(result.estimated_distance, 60.0f, 0.01f);
}

// ─── Velocity at exactly max allowed ──────────────────────────

TEST_F(SensorFusionTest, VelocityAtExactMaxIsNotClamped) {
    ON_CALL(mock_input_, GetRadarRange()).WillByDefault(Return(20.0f));
    ON_CALL(mock_input_, GetCameraRange()).WillByDefault(Return(20.0f));
    ON_CALL(mock_input_, GetObjectVelocity())
        .WillByDefault(Return(SensorFusion::MAX_VALID_VELOCITY));

    auto fusion = MakeFusion();
    auto result = fusion.FuseObjects();

    EXPECT_FLOAT_EQ(result.estimated_velocity, SensorFusion::MAX_VALID_VELOCITY);
}
