/**
 * @file    test_can_bus.cpp
 * @brief   Unit tests for CANBus and CANFrame classes
 *
 * Uses a simple lightweight test framework (no external dependencies).
 * Run via: ./ecu_tests
 */

#include <cstdio>
#include <cstring>
#include <cassert>
#include <functional>

#include "../include/can/can_frame.hpp"
#include "../include/can/can_bus.hpp"

using namespace automotive::can;

// ─── Minimal test harness ─────────────────────────────────────────────────────
static int g_passed = 0;
static int g_failed = 0;

#define TEST(name) static void name()
#define ASSERT_TRUE(expr)  do { if (!(expr)) { std::printf("  FAIL: %s (line %d)\n", #expr, __LINE__); g_failed++; return; } } while(false)
#define ASSERT_EQ(a,b)     do { if ((a) != (b)) { std::printf("  FAIL: %s != %s (line %d)\n", #a, #b, __LINE__); g_failed++; return; } } while(false)
#define RUN(fn)  do { std::printf("[TEST] " #fn "\n"); fn(); g_passed++; } while(false)

// ─── CANFrame Tests ───────────────────────────────────────────────────────────

TEST(test_canframe_default_constructor) {
    CANFrame frame;
    ASSERT_EQ(frame.getId(),  0U);
    ASSERT_EQ(frame.getDLC(), 0U);
    ASSERT_TRUE(frame.isValid());
    ASSERT_TRUE(frame.isDataFrame());
}

TEST(test_canframe_constructor_with_data) {
    uint8_t payload[8] = { 0x10U, 0x03U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U, 0x00U };
    CANFrame frame(0x7E0U, 8U, payload);
    ASSERT_EQ(frame.getId(),  0x7E0U);
    ASSERT_EQ(frame.getDLC(), 8U);
    ASSERT_EQ(frame.getByte(0), 0x10U);
    ASSERT_EQ(frame.getByte(1), 0x03U);
    ASSERT_TRUE(frame.isValid());
}

TEST(test_canframe_invalid_dlc) {
    uint8_t data[10]{};
    CANFrame frame(0x123U, 9U, data);  // DLC > 8, but still stored in FD buffer
    // isValid() checks if DLC <= CAN_MAX_DLC (8 for CAN 2.0)
    ASSERT_TRUE(!frame.isValid());
}

TEST(test_canframe_match_id_exact) {
    CANFrame frame(0x7E0U, 0U, nullptr);
    ASSERT_TRUE(frame.matchesID(0x7E0U));
    ASSERT_TRUE(!frame.matchesID(0x7E1U));
}

TEST(test_canframe_match_id_masked) {
    CANFrame frame(0x7E3U, 0U, nullptr);
    // Mask 0x7F0 → matches 0x7E0–0x7EF range
    ASSERT_TRUE(frame.matchesID(0x7E0U, 0x7F0U));
    ASSERT_TRUE(!frame.matchesID(0x700U, 0x7F0U));
}

TEST(test_canframe_get_byte_out_of_bounds) {
    uint8_t data[4] = { 0xAAU, 0xBBU, 0xCCU, 0xDDU };
    CANFrame frame(0x100U, 4U, data);
    ASSERT_EQ(frame.getByte(3), 0xDDU);
    ASSERT_EQ(frame.getByte(4), 0x00U);  // Out of range → 0
    ASSERT_EQ(frame.getByte(7), 0x00U);
}

TEST(test_canframe_reset) {
    uint8_t data[4] = { 0x01U, 0x02U, 0x03U, 0x04U };
    CANFrame frame(0x123U, 4U, data);
    frame.reset();
    ASSERT_EQ(frame.getId(),  0U);
    ASSERT_EQ(frame.getDLC(), 0U);
    ASSERT_EQ(frame.getByte(0), 0U);
}

TEST(test_canframe_setdata) {
    CANFrame frame;
    uint8_t newData[3] = { 0x22U, 0xF1U, 0x90U };
    bool result = frame.setData(newData, 3U);
    ASSERT_TRUE(result);
    ASSERT_EQ(frame.getDLC(), 3U);
    ASSERT_EQ(frame.getByte(0), 0x22U);
    ASSERT_EQ(frame.getByte(1), 0xF1U);
    ASSERT_EQ(frame.getByte(2), 0x90U);
}

TEST(test_canframe_setdata_too_large) {
    CANFrame frame;
    uint8_t bigData[70]{};
    bool result = frame.setData(bigData, 70U);
    ASSERT_TRUE(!result);  // Should fail
}

// ─── CANBus Tests ─────────────────────────────────────────────────────────────

TEST(test_canbus_initialize_shutdown) {
    CANBus bus("TestCAN", 500000U);
    ASSERT_TRUE(!bus.isInitialized());
    ASSERT_TRUE(bus.initialize());
    ASSERT_TRUE(bus.isInitialized());
    ASSERT_EQ(static_cast<uint8_t>(bus.getBusState()),
              static_cast<uint8_t>(BusState::ACTIVE));
    bus.shutdown();
    ASSERT_TRUE(!bus.isInitialized());
}

TEST(test_canbus_transmit_basic) {
    CANBus bus("TestCAN", 500000U);
    bus.initialize();
    uint8_t data[4] = { 0x01U, 0x02U, 0x03U, 0x04U };
    bool result = bus.transmit(0x100U, data, 4U);
    ASSERT_TRUE(result);
    ASSERT_EQ(bus.getStats().txFrameCount, 1U);
    bus.shutdown();
}

TEST(test_canbus_transmit_busoff) {
    CANBus bus("TestCAN", 500000U);
    bus.initialize();
    // Inject enough errors to go bus-off
    for (int i = 0; i < 40; ++i) {
        bus.injectBusError(0U);  // Stuff errors
    }
    uint8_t data[1] = { 0x00U };
    bool result = bus.transmit(0x100U, data, 1U);
    ASSERT_TRUE(!result);  // Must fail in bus-off
    bus.shutdown();
}

TEST(test_canbus_inject_and_receive_frame) {
    CANBus bus("TestCAN", 500000U);
    bus.initialize();

    bool callbackCalled = false;
    uint32_t receivedId = 0U;

    bus.registerRxCallback([&](const CANFrame& f) {
        callbackCalled = true;
        receivedId = f.getId();
    });

    uint8_t data[8] = { 0x22U, 0xF1U, 0x90U, 0, 0, 0, 0, 0 };
    CANFrame inFrame(0x7E0U, 3U, data);
    bus.injectFrame(inFrame);
    bus.processRxQueue();

    ASSERT_TRUE(callbackCalled);
    ASSERT_EQ(receivedId, 0x7E0U);
    bus.shutdown();
}

TEST(test_canbus_rx_callback_with_filter) {
    CANBus bus("TestCAN", 500000U);
    bus.initialize();

    int callCount7E0 = 0;
    int callCount100 = 0;

    // Only listen for 0x7E0
    bus.registerRxCallback([&](const CANFrame&) { callCount7E0++; },
                            0x7E0U, 0xFFFFFFFFU);
    // Only listen for 0x100
    bus.registerRxCallback([&](const CANFrame&) { callCount100++; },
                            0x100U, 0xFFFFFFFFU);

    uint8_t d[1]{};
    bus.injectFrame(CANFrame(0x7E0U, 1U, d));
    bus.injectFrame(CANFrame(0x100U, 1U, d));
    bus.injectFrame(CANFrame(0x200U, 1U, d));  // Neither callback
    bus.processRxQueue();

    ASSERT_EQ(callCount7E0, 1);
    ASSERT_EQ(callCount100, 1);
    bus.shutdown();
}

TEST(test_canbus_unregister_callback) {
    CANBus bus("TestCAN", 500000U);
    bus.initialize();

    int callCount = 0;
    int8_t handle = bus.registerRxCallback([&](const CANFrame&) { callCount++; });
    ASSERT_TRUE(handle >= 0);

    bus.unregisterRxCallback(handle);

    uint8_t d[1]{};
    bus.injectFrame(CANFrame(0x100U, 1U, d));
    bus.processRxQueue();
    ASSERT_EQ(callCount, 0);  // Should not be called after unregister
    bus.shutdown();
}

TEST(test_canbus_stats_rx_count) {
    CANBus bus("TestCAN", 500000U);
    bus.initialize();

    uint8_t d[1]{};
    for (int i = 0; i < 5; ++i) {
        bus.injectFrame(CANFrame(0x100U, 1U, d));
    }
    bus.processRxQueue();
    ASSERT_EQ(bus.getStats().rxFrameCount, 5U);
    bus.shutdown();
}

// ─── Main ─────────────────────────────────────────────────────────────────────

int main() {
    std::printf("═══════════════════════════════════════════\n");
    std::printf("  CAN Bus + Frame Unit Tests\n");
    std::printf("═══════════════════════════════════════════\n");

    RUN(test_canframe_default_constructor);
    RUN(test_canframe_constructor_with_data);
    RUN(test_canframe_invalid_dlc);
    RUN(test_canframe_match_id_exact);
    RUN(test_canframe_match_id_masked);
    RUN(test_canframe_get_byte_out_of_bounds);
    RUN(test_canframe_reset);
    RUN(test_canframe_setdata);
    RUN(test_canframe_setdata_too_large);

    RUN(test_canbus_initialize_shutdown);
    RUN(test_canbus_transmit_basic);
    RUN(test_canbus_transmit_busoff);
    RUN(test_canbus_inject_and_receive_frame);
    RUN(test_canbus_rx_callback_with_filter);
    RUN(test_canbus_unregister_callback);
    RUN(test_canbus_stats_rx_count);

    std::printf("═══════════════════════════════════════════\n");
    std::printf("  Results: %d passed, %d failed\n", g_passed, g_failed);
    std::printf("═══════════════════════════════════════════\n");
    return (g_failed == 0) ? 0 : 1;
}
