// ─────────────────────────────────────────────────────────────────────────────
//  Custom test main  –  configures GTest/GMock and runs all suites
// ─────────────────────────────────────────────────────────────────────────────
#include <gtest/gtest.h>
#include <gmock/gmock.h>

int main(int argc, char** argv) {
    ::testing::InitGoogleMock(&argc, argv);
    return RUN_ALL_TESTS();
}
