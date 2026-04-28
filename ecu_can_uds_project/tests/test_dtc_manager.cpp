/**
 * @file    test_dtc_manager.cpp
 * @brief   Unit tests for DTCManager and ECUCore integration
 */

#include <cstdio>
#include <cassert>

#include "../include/ecu/dtc_manager.hpp"
#include "../include/can/can_bus.hpp"
#include "../include/ecu/ecu_core.hpp"

using namespace automotive;
using namespace automotive::ecu;

static int g_passed = 0;
static int g_failed = 0;

#define TEST(name) static void name()
#define ASSERT_TRUE(expr)  do { if (!(expr)) { std::printf("  FAIL: %s (line %d)\n", #expr, __LINE__); g_failed++; return; } } while(false)
#define ASSERT_EQ(a, b)    do { if ((a) != (b)) { std::printf("  FAIL: %s != %s [%d vs %d] line %d\n", #a, #b, (int)(a), (int)(b), __LINE__); g_failed++; return; } } while(false)
#define RUN(fn)  do { std::printf("[TEST] " #fn "\n"); fn(); g_passed++; } while(false)

// ─── DTCManager Tests ─────────────────────────────────────────────────────────

TEST(test_dtc_set_and_query) {
    DTCManager mgr;
    mgr.setDTC(0xC0300U, DTCSeverity::CHECK_IMMEDIATELY);

    ASSERT_TRUE(mgr.isDTCActive(0xC0300U));
    uint8_t status = mgr.getDTCStatus(0xC0300U);
    ASSERT_TRUE(status & DTCStatusBit::TEST_FAILED);
    ASSERT_TRUE(status & DTCStatusBit::PENDING);
}

TEST(test_dtc_not_found_returns_zero) {
    DTCManager mgr;
    ASSERT_EQ(mgr.getDTCStatus(0x123456U), 0U);
    ASSERT_TRUE(!mgr.isDTCActive(0x123456U));
    ASSERT_TRUE(!mgr.isDTCConfirmed(0x123456U));
}

TEST(test_dtc_confirmed_after_two_failures) {
    DTCManager mgr;
    mgr.setDTC(0xAAAAAU);  // First failure
    mgr.setDTC(0xAAAAAU);  // Second failure → promotes to confirmed

    ASSERT_TRUE(mgr.isDTCConfirmed(0xAAAAAU));
    uint8_t status = mgr.getDTCStatus(0xAAAAAU);
    ASSERT_TRUE(status & DTCStatusBit::CONFIRMED);
    ASSERT_TRUE(status & DTCStatusBit::WARNING_INDICATOR);
}

TEST(test_dtc_clear_failed) {
    DTCManager mgr;
    mgr.setDTC(0x100000U);
    ASSERT_TRUE(mgr.isDTCActive(0x100000U));

    mgr.clearDTCFailed(0x100000U);
    ASSERT_TRUE(!mgr.isDTCActive(0x100000U));
    // Confirmed bit may still be set
}

TEST(test_dtc_clear_all) {
    DTCManager mgr;
    mgr.setDTC(0x100000U);
    mgr.setDTC(0x200000U);
    mgr.setDTC(0x300000U);
    ASSERT_EQ(mgr.getTotalDTCCount(), 3U);

    mgr.clearAllDTCs();
    ASSERT_EQ(mgr.getTotalDTCCount(), 0U);
    ASSERT_TRUE(!mgr.isDTCActive(0x100000U));
}

TEST(test_dtc_count_by_status_mask) {
    DTCManager mgr;
    mgr.setDTC(0xAAAA0U);  // Active
    mgr.setDTC(0xBBBB0U);  // Active
    mgr.setDTC(0xBBBB0U);  // → Confirmed
    mgr.setDTC(0xAAAA0U);  // → Confirmed

    uint8_t activeCnt = mgr.countDTCsByStatusMask(DTCStatusBit::TEST_FAILED);
    ASSERT_EQ(activeCnt, 2U);
}

TEST(test_dtc_get_by_status_mask) {
    DTCManager mgr;
    mgr.setDTC(0x111111U);
    mgr.setDTC(0x222222U);

    uint32_t codes[10]{};
    uint8_t  status[10]{};
    uint8_t  count = mgr.getDTCsByStatusMask(DTCStatusBit::TEST_FAILED,
                                               codes, status, 10U);
    ASSERT_EQ(count, 2U);
    // Both should be active
    ASSERT_TRUE(status[0] & DTCStatusBit::TEST_FAILED);
    ASSERT_TRUE(status[1] & DTCStatusBit::TEST_FAILED);
}

TEST(test_dtc_snapshot_capture) {
    DTCManager mgr;
    DTCSnapshot snap{};
    snap.engineRPM   = 3500;
    snap.coolantTemp = 95;
    snap.vehicleSpeed= 120;
    snap.valid       = 1U;

    mgr.setDTC(0xF00001U, DTCSeverity::CHECK_IMMEDIATELY, &snap);

    DTCSnapshot retrieved{};
    bool found = mgr.getDTCSnapshot(0xF00001U, retrieved);
    ASSERT_TRUE(found);
    ASSERT_EQ(retrieved.engineRPM,    3500);
    ASSERT_EQ(retrieved.coolantTemp,    95);
    ASSERT_EQ(retrieved.vehicleSpeed,  120);
}

TEST(test_dtc_snapshot_not_found) {
    DTCManager mgr;
    DTCSnapshot snap{};
    bool found = mgr.getDTCSnapshot(0xDEADBEEU, snap);
    ASSERT_TRUE(!found);
}

TEST(test_dtc_drive_cycle_processing) {
    DTCManager mgr;
    mgr.setDTC(0x555500U);  // Active

    // Simulate successful drive cycle completion without re-failure
    mgr.clearDTCFailed(0x555500U);
    mgr.processDriveCycle(true);

    uint8_t status = mgr.getDTCStatus(0x555500U);
    // After cycle: testFailed should be cleared, notCompleted set
    ASSERT_TRUE(!(status & DTCStatusBit::TEST_FAILED));
    ASSERT_TRUE(!(status & DTCStatusBit::PENDING));
}

TEST(test_dtc_max_storage) {
    DTCManager mgr;
    // Fill all 50 slots
    for (uint32_t i = 0; i < DTCManager::MAX_DTC_RECORDS; ++i) {
        mgr.setDTC(0x100000U + i);
    }
    ASSERT_EQ(mgr.getTotalDTCCount(), DTCManager::MAX_DTC_RECORDS);
    // Setting one more should gracefully fail (no crash, warning printed)
    mgr.setDTC(0x999999U);  // Should be a no-op (storage full)
}

TEST(test_dtc_duplicate_code_reuses_slot) {
    DTCManager mgr;
    mgr.setDTC(0xABCDEFU);
    mgr.setDTC(0xABCDEFU);  // Same code – should reuse, not add new
    // Occurrence counter should be 2
    ASSERT_EQ(mgr.getTotalDTCCount(), 1U);
}

// ─── ECUCore Integration Test ─────────────────────────────────────────────────

extern void UDSServer_AdvanceTick(uint32_t ms);

TEST(test_ecu_lifecycle) {
    can::CANBus  bus("TestCAN", 500000U);
    ECUCore      ecu("TestECU", bus);

    ASSERT_EQ(static_cast<uint8_t>(ecu.getState()),
              static_cast<uint8_t>(ECUState::POWER_OFF));

    bool ok = ecu.initialize();
    ASSERT_TRUE(ok);
    ASSERT_EQ(static_cast<uint8_t>(ecu.getState()),
              static_cast<uint8_t>(ECUState::INIT));

    // Key ON
    ECUSignals sig{};
    sig.ignitionOn    = true;
    sig.engineRunning = true;
    sig.engineRPM     = 800;
    sig.coolantTemp   = 20;
    ecu.setSignals(sig);

    for (int i = 0; i < 50; ++i) {
        ecu.cyclic_1ms();
        UDSServer_AdvanceTick(1U);
    }
    ASSERT_EQ(static_cast<uint8_t>(ecu.getState()),
              static_cast<uint8_t>(ECUState::RUNNING));

    ecu.shutdown();
}

TEST(test_ecu_fault_injection) {
    can::CANBus  bus("FaultTestCAN", 500000U);
    ECUCore      ecu("FaultTestECU", bus);
    ecu.initialize();

    ECUSignals sig{};
    sig.ignitionOn = true;
    sig.engineRunning = true;
    ecu.setSignals(sig);
    for (int i = 0; i < 20; ++i) {
        ecu.cyclic_1ms();
        UDSServer_AdvanceTick(1U);
    }

    ecu.injectFault(0xC0300U, DTCSeverity::CHECK_IMMEDIATELY);
    ASSERT_TRUE(ecu.getDTCManager().isDTCActive(0xC0300U));
    ASSERT_EQ(ecu.getDTCManager().getTotalDTCCount(), 1U);

    ecu.shutdown();
}

// ─── Main ─────────────────────────────────────────────────────────────────────

int main() {
    std::printf("═══════════════════════════════════════════\n");
    std::printf("  DTC Manager + ECU Core Unit Tests\n");
    std::printf("═══════════════════════════════════════════\n");

    RUN(test_dtc_set_and_query);
    RUN(test_dtc_not_found_returns_zero);
    RUN(test_dtc_confirmed_after_two_failures);
    RUN(test_dtc_clear_failed);
    RUN(test_dtc_clear_all);
    RUN(test_dtc_count_by_status_mask);
    RUN(test_dtc_get_by_status_mask);
    RUN(test_dtc_snapshot_capture);
    RUN(test_dtc_snapshot_not_found);
    RUN(test_dtc_drive_cycle_processing);
    RUN(test_dtc_max_storage);
    RUN(test_dtc_duplicate_code_reuses_slot);
    RUN(test_ecu_lifecycle);
    RUN(test_ecu_fault_injection);

    std::printf("═══════════════════════════════════════════\n");
    std::printf("  Results: %d passed, %d failed\n", g_passed, g_failed);
    std::printf("═══════════════════════════════════════════\n");
    return (g_failed == 0) ? 0 : 1;
}
