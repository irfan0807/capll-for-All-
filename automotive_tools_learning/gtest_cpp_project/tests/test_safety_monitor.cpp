// ─────────────────────────────────────────────────────────────────────────────
//  Safety Monitor Tests  –  STAR Case 4: Death Tests for abort() verification
// ─────────────────────────────────────────────────────────────────────────────
#include <gtest/gtest.h>
#include "safety_monitor.h"

// ─── Normal state (no fault) ──────────────────────────────────

TEST(SafetyMonitorTest, TickWithNoFaultDoesNotAbort) {
    SafetyMonitor monitor;
    // Must NOT abort
    EXPECT_NO_FATAL_FAILURE(monitor.Tick());
    EXPECT_FALSE(monitor.IsFaultActive());
}

TEST(SafetyMonitorTest, IsFaultActiveAfterInjection) {
    SafetyMonitor monitor;
    monitor.InjectFault(FaultType::RAM_PARITY_ERROR);
    EXPECT_TRUE(monitor.IsFaultActive());
}

// ─── Death tests: every CRITICAL fault must call abort() ──────────

TEST(SafetyMonitorDeathTest, AbortOnCpuLockup) {
    EXPECT_DEATH(
        {
            SafetyMonitor monitor;
            monitor.InjectFault(FaultType::CRITICAL_CPU_LOCKUP);
            monitor.Tick();
        },
        "CRITICAL FAULT"
    );
}

TEST(SafetyMonitorDeathTest, AbortOnWatchdogTimeout) {
    EXPECT_DEATH(
        {
            SafetyMonitor monitor;
            monitor.InjectFault(FaultType::WATCHDOG_TIMEOUT);
            monitor.Tick();
        },
        "CRITICAL FAULT"
    );
}

TEST(SafetyMonitorDeathTest, AbortOnStackOverflow) {
    EXPECT_DEATH(
        {
            SafetyMonitor monitor;
            monitor.InjectFault(FaultType::STACK_OVERFLOW);
            monitor.Tick();
        },
        "CRITICAL FAULT"
    );
}

TEST(SafetyMonitorDeathTest, AbortOnRamParityError) {
    EXPECT_DEATH(
        {
            SafetyMonitor monitor;
            monitor.InjectFault(FaultType::RAM_PARITY_ERROR);
            monitor.Tick();
        },
        "CRITICAL FAULT"
    );
}

TEST(SafetyMonitorDeathTest, AbortOnPowerSupplyBrownout) {
    EXPECT_DEATH(
        {
            SafetyMonitor monitor;
            monitor.InjectFault(FaultType::POWER_SUPPLY_BROWNOUT);
            monitor.Tick();
        },
        "CRITICAL FAULT"
    );
}

// ─── Verify meaningful stderr message is printed ──────────────

TEST(SafetyMonitorDeathTest, AbortMessageContainsFaultName) {
    EXPECT_DEATH(
        {
            SafetyMonitor monitor;
            monitor.InjectFault(FaultType::WATCHDOG_TIMEOUT);
            monitor.Tick();
        },
        "WATCHDOG_TIMEOUT"
    );
}
