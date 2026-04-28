// ============================================================================
// emergency_handler.cpp
// ============================================================================
#include "../../include/safety/emergency_handler.hpp"

namespace adas {
namespace safety {

EmergencyHandler::EmergencyHandler()
    : m_safetyMonitor(nullptr), m_controller(nullptr),
      m_emergencyActive(false), m_minimalRiskActive(false),
      m_emergencyStartTime(0)
{}

void EmergencyHandler::setSafetyMonitor(SafetyMonitor* sm)          { m_safetyMonitor = sm; }
void EmergencyHandler::setVehicleController(control::VehicleController* c) { m_controller = c; }

void EmergencyHandler::handle(SafetyDecision decision,
                               AdasSystemState systemState,
                               float egoSpeed_mps) {
    (void)systemState;
    (void)egoSpeed_mps;

    switch (decision) {
        case SafetyDecision::EMERGENCY_STOP:
            executeAEB();
            break;

        case SafetyDecision::MINIMAL_RISK:
            executeMinimalRisk(egoSpeed_mps);
            break;

        case SafetyDecision::NOMINAL:
        case SafetyDecision::WARN:
        case SafetyDecision::DEGRADE_ODD:
            if (m_emergencyActive) {
                // AEB was active – only clear if speed is ~0
                if (egoSpeed_mps < 0.5f) {
                    m_emergencyActive = false;
                    if (m_controller) m_controller->clearEmergencyStop();
                }
            }
            m_minimalRiskActive = false;
            break;
    }
}

void EmergencyHandler::executeAEB() {
    m_emergencyActive = true;
    m_minimalRiskActive = false;
    if (m_controller) m_controller->triggerEmergencyStop();
}

void EmergencyHandler::executeMinimalRisk(float egoSpeed_mps) {
    m_minimalRiskActive = true;
    // Gradual deceleration – limit target speed to 5 m/s (~18 km/h)
    // Full stop if already slow
    if (egoSpeed_mps < 2.0f) {
        executeAEB();
    }
    // Otherwise planning layer should reduce speed (handled by planner)
}

} // namespace safety
} // namespace adas
