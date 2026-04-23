// ─────────────────────────────────────────────────────────────────────────────
//  Gear Recommender Tests  –  GMock: AUTOSAR SWC host testing pattern
// ─────────────────────────────────────────────────────────────────────────────
#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include "gear_recommender.h"
#include "mocks/mock_gear_input.h"

using ::testing::Return;
using ::testing::NiceMock;

class GearRecommenderTest : public ::testing::Test {
protected:
    NiceMock<MockGearInput> mock_input_;

    // Helper: configure mock with all four signals in one call
    void SetSignals(float speed_kph, float rpm, float throttle, uint8_t gear) {
        ON_CALL(mock_input_, GetVehicleSpeedKph()).WillByDefault(Return(speed_kph));
        ON_CALL(mock_input_, GetEngineRpm()).WillByDefault(Return(rpm));
        ON_CALL(mock_input_, GetThrottlePercent()).WillByDefault(Return(throttle));
        ON_CALL(mock_input_, GetCurrentGear()).WillByDefault(Return(gear));
    }
};

// ─── Upshift scenarios ─────────────────────────────────────────

TEST_F(GearRecommenderTest, UpshiftWhenHighRpmLowThrottle) {
    SetSignals(80.0f, 4000.0f, 50.0f, 3);
    GearRecommender rec(mock_input_);
    EXPECT_EQ(rec.RecommendedGear(), 4u);   // gear 3 → 4
}

TEST_F(GearRecommenderTest, NoUpshiftAtMaxGear) {
    SetSignals(200.0f, 5000.0f, 40.0f, GearRecommender::MAX_GEAR);
    GearRecommender rec(mock_input_);
    EXPECT_EQ(rec.RecommendedGear(), 0u);   // 0 = no change
}

TEST_F(GearRecommenderTest, NoUpshiftWhenThrottleHigh) {
    // High throttle = driver accelerating hard, do not upshift
    SetSignals(100.0f, 4000.0f, 95.0f, 3);
    GearRecommender rec(mock_input_);
    // rpm > 3500 but throttle > 80 → might downshift instead  
    // with rpm=4000 and throttle=95: ShouldDownshift: rpm ≥ 1500 and not (throttle>90 && rpm<2500)
    // So no upshift and no downshift
    uint8_t result = rec.RecommendedGear();
    EXPECT_NE(result, 4u);  // must NOT upshift
}

// ─── Downshift scenarios ───────────────────────────────────────

TEST_F(GearRecommenderTest, DownshiftWhenRpmTooLow) {
    SetSignals(20.0f, 1200.0f, 30.0f, 4);
    GearRecommender rec(mock_input_);
    EXPECT_EQ(rec.RecommendedGear(), 3u);   // gear 4 → 3
}

TEST_F(GearRecommenderTest, DownshiftWhenDriverDemandsHighPowerAtLowRpm) {
    // High throttle (>90) but low RPM (<2500): kickdown
    SetSignals(60.0f, 2000.0f, 95.0f, 5);
    GearRecommender rec(mock_input_);
    EXPECT_EQ(rec.RecommendedGear(), 4u);   // gear 5 → 4
}

TEST_F(GearRecommenderTest, NoDownshiftAtMinGear) {
    SetSignals(5.0f, 800.0f, 10.0f, GearRecommender::MIN_GEAR);
    GearRecommender rec(mock_input_);
    EXPECT_EQ(rec.RecommendedGear(), 0u);   // already at gear 1
}

// ─── No-change scenarios ───────────────────────────────────────

TEST_F(GearRecommenderTest, NoChangeInNominalCruise) {
    // steady highway cruise: RPM mid-range, moderate throttle
    SetSignals(130.0f, 2500.0f, 30.0f, 6);
    GearRecommender rec(mock_input_);
    EXPECT_EQ(rec.RecommendedGear(), 0u);
}

// ─── Boundary: RPM exactly at upshift threshold ───────────────

TEST_F(GearRecommenderTest, RpmExactlyAtUpshiftThreshold) {
    // rpm == 3500 exactly: condition is rpm > 3500, so should NOT upshift
    SetSignals(90.0f, 3500.0f, 50.0f, 3);
    GearRecommender rec(mock_input_);
    EXPECT_EQ(rec.RecommendedGear(), 0u);
}

TEST_F(GearRecommenderTest, RpmJustAboveUpshiftThreshold) {
    SetSignals(90.0f, 3501.0f, 50.0f, 3);
    GearRecommender rec(mock_input_);
    EXPECT_EQ(rec.RecommendedGear(), 4u);   // should upshift
}
