// ─────────────────────────────────────────────────────────────────────────────
//  Pedal Safety Filter Tests  –  STAR Case: negative / IEEE 754 edge cases
// ─────────────────────────────────────────────────────────────────────────────
#include <gtest/gtest.h>
#include "pedal_safety.h"
#include <limits>

class PedalSafetyValidTest : public ::testing::TestWithParam<float> {};

TEST_P(PedalSafetyValidTest, ValidInputPassesThrough) {
    PedalSafetyFilter f;
    auto result = f.Process(GetParam());
    EXPECT_EQ(result.status, InputStatus::VALID);
    EXPECT_FLOAT_EQ(result.safe_value, GetParam());
}

INSTANTIATE_TEST_SUITE_P(
    ValidInputRange,
    PedalSafetyValidTest,
    ::testing::Values(0.0f, 1.0f, 50.0f, 99.9f, 100.0f)
);

// ─────────────────────────────────────────────────────────────
//  Invalid / Edge cases  (the STAR Case from the guide)
// ─────────────────────────────────────────────────────────────
class PedalSafetyInvalidTest : public ::testing::TestWithParam<float> {};

TEST_P(PedalSafetyInvalidTest, InvalidInputReturnsZeroSafeValue) {
    PedalSafetyFilter f;
    auto result = f.Process(GetParam());
    EXPECT_EQ(result.status, InputStatus::INVALID);
    EXPECT_FLOAT_EQ(result.safe_value, 0.0f);
}

INSTANTIATE_TEST_SUITE_P(
    InvalidInputs,
    PedalSafetyInvalidTest,
    ::testing::Values(
        -0.01f,
        -100.0f,
        100.01f,
        1000.0f,
        std::numeric_limits<float>::quiet_NaN(),
        std::numeric_limits<float>::infinity(),
        -std::numeric_limits<float>::infinity()
    )
);

// Boundary: exactly 0 and exactly 100 are VALID
TEST(PedalSafetyBoundaryTest, ExactMinIsValid) {
    PedalSafetyFilter f;
    EXPECT_EQ(f.Process(0.0f).status, InputStatus::VALID);
}

TEST(PedalSafetyBoundaryTest, ExactMaxIsValid) {
    PedalSafetyFilter f;
    EXPECT_EQ(f.Process(100.0f).status, InputStatus::VALID);
}

TEST(PedalSafetyBoundaryTest, JustBelowMinIsInvalid) {
    PedalSafetyFilter f;
    EXPECT_EQ(f.Process(-0.001f).status, InputStatus::INVALID);
}

TEST(PedalSafetyBoundaryTest, JustAboveMaxIsInvalid) {
    PedalSafetyFilter f;
    EXPECT_EQ(f.Process(100.001f).status, InputStatus::INVALID);
}
