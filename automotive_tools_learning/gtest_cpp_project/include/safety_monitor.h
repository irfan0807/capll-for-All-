#pragma once
#include <cstdint>

enum class FaultType : uint8_t {
    NONE               = 0,
    CRITICAL_CPU_LOCKUP   = 1,
    WATCHDOG_TIMEOUT      = 2,
    STACK_OVERFLOW        = 3,
    RAM_PARITY_ERROR      = 4,
    POWER_SUPPLY_BROWNOUT = 5,
};

// ─────────────────────────────────────────────────────────────
//  SafetyMonitor  –  ASIL B safety function; calls abort()
//  on any CRITICAL fault detection
// ─────────────────────────────────────────────────────────────
class SafetyMonitor {
public:
    SafetyMonitor();
    void InjectFault(FaultType fault);
    void Tick();           // evaluate faults and react

    bool IsFaultActive() const { return active_fault_ != FaultType::NONE; }

private:
    FaultType active_fault_{ FaultType::NONE };

    [[noreturn]] void HandleCriticalFault(const char* msg);
};
