#include "safety_monitor.h"
#include <cstdlib>
#include <cstdio>

SafetyMonitor::SafetyMonitor() = default;

void SafetyMonitor::InjectFault(FaultType fault) {
    active_fault_ = fault;
}

void SafetyMonitor::Tick() {
    switch (active_fault_) {
        case FaultType::CRITICAL_CPU_LOCKUP:
            HandleCriticalFault("CRITICAL FAULT: CPU_LOCKUP detected");
        case FaultType::WATCHDOG_TIMEOUT:
            HandleCriticalFault("CRITICAL FAULT: WATCHDOG_TIMEOUT detected");
        case FaultType::STACK_OVERFLOW:
            HandleCriticalFault("CRITICAL FAULT: STACK_OVERFLOW detected");
        case FaultType::RAM_PARITY_ERROR:
            HandleCriticalFault("CRITICAL FAULT: RAM_PARITY_ERROR detected");
        case FaultType::POWER_SUPPLY_BROWNOUT:
            HandleCriticalFault("CRITICAL FAULT: POWER_SUPPLY_BROWNOUT detected");
        case FaultType::NONE:
        default:
            break;
    }
}

[[noreturn]] void SafetyMonitor::HandleCriticalFault(const char* msg) {
    std::fprintf(stderr, "%s\n", msg);
    std::abort();
}
