#pragma once
// ============================================================================
// emergency_handler.hpp  –  AEB and minimal risk condition handler
// ============================================================================
#include "safety_monitor.hpp"
#include "../control/vehicle_controller.hpp"

namespace adas {
namespace safety {

class EmergencyHandler {
public:
    EmergencyHandler();

    void setSafetyMonitor(SafetyMonitor* monitor);
    void setVehicleController(control::VehicleController* ctrl);

    /// Called each cycle – reacts to SafetyDecision
    void handle(SafetyDecision decision,
                AdasSystemState systemState,
                float egoSpeed_mps);

    bool isEmergencyActive() const { return m_emergencyActive; }
    bool isMinimalRiskActive() const { return m_minimalRiskActive; }

private:
    void executeAEB();
    void executeMinimalRisk(float egoSpeed_mps);

    SafetyMonitor*            m_safetyMonitor;
    control::VehicleController* m_controller;
    bool                      m_emergencyActive;
    bool                      m_minimalRiskActive;
    uint32_t                  m_emergencyStartTime;
};

} // namespace safety
} // namespace adas
