// ============================================================================
// adas_fsm.cpp  –  ADAS operating state machine
// ============================================================================
#include "../../include/safety/adas_fsm.hpp"
#include <cstring>

namespace adas {
namespace safety {

const char* stateToStr(AdasSystemState s) {
    switch (s) {
        case AdasSystemState::POWER_OFF:    return "POWER_OFF";
        case AdasSystemState::SELF_TEST:    return "SELF_TEST";
        case AdasSystemState::STANDBY:      return "STANDBY";
        case AdasSystemState::ACTIVE_L4:    return "ACTIVE_L4";
        case AdasSystemState::DEGRADED:     return "DEGRADED";
        case AdasSystemState::SAFE_STOP:    return "SAFE_STOP";
        case AdasSystemState::MINIMAL_RISK: return "MINIMAL_RISK";
        case AdasSystemState::PULL_OVER:    return "PULL_OVER";
        case AdasSystemState::FAULT:        return "FAULT";
        default:                            return "UNKNOWN";
    }
}

AdasFSM::AdasFSM()
    : m_state(AdasSystemState::POWER_OFF),
      m_selfTestCycles(0), m_engageRequested(false)
{}

bool AdasFSM::isSafeState() const {
    return m_state == AdasSystemState::SAFE_STOP ||
           m_state == AdasSystemState::FAULT      ||
           m_state == AdasSystemState::POWER_OFF;
}

void AdasFSM::transition(AdasSystemState next) {
    m_state = next;
}

void AdasFSM::onIgnitionOn() {
    if (m_state == AdasSystemState::POWER_OFF) {
        transition(AdasSystemState::SELF_TEST);
        m_selfTestCycles = 0;
    }
}

void AdasFSM::onIgnitionOff() {
    transition(AdasSystemState::POWER_OFF);
    m_engageRequested = false;
}

void AdasFSM::requestEngage() {
    if (m_state == AdasSystemState::STANDBY ||
        m_state == AdasSystemState::DEGRADED) {
        m_engageRequested = true;
    }
}

void AdasFSM::requestDisengage() {
    if (m_state == AdasSystemState::ACTIVE_L4 ||
        m_state == AdasSystemState::DEGRADED) {
        transition(AdasSystemState::STANDBY);
        m_engageRequested = false;
    }
}

void AdasFSM::update(bool selfTestPassed,
                      bool oddValid,
                      bool criticalFault,
                      bool majorFault,
                      bool emergencyStopRequired,
                      bool pulloverComplete) {
    switch (m_state) {
        case AdasSystemState::POWER_OFF:
            // Wait for ignition
            break;

        case AdasSystemState::SELF_TEST:
            m_selfTestCycles++;
            if (criticalFault) {
                transition(AdasSystemState::FAULT);
            } else if (m_selfTestCycles >= 10 && selfTestPassed) {
                transition(AdasSystemState::STANDBY);
            }
            break;

        case AdasSystemState::STANDBY:
            if (criticalFault) { transition(AdasSystemState::FAULT); break; }
            if (m_engageRequested && oddValid && !majorFault) {
                transition(AdasSystemState::ACTIVE_L4);
                m_engageRequested = false;
            }
            if (m_engageRequested && majorFault) {
                transition(AdasSystemState::DEGRADED);
            }
            break;

        case AdasSystemState::ACTIVE_L4:
            if (criticalFault || emergencyStopRequired) {
                transition(AdasSystemState::SAFE_STOP); break;
            }
            if (!oddValid || majorFault) {
                transition(AdasSystemState::MINIMAL_RISK); break;
            }
            break;

        case AdasSystemState::DEGRADED:
            if (criticalFault || emergencyStopRequired) {
                transition(AdasSystemState::SAFE_STOP); break;
            }
            if (!oddValid || majorFault) {
                transition(AdasSystemState::MINIMAL_RISK); break;
            }
            if (!majorFault && oddValid && m_engageRequested) {
                transition(AdasSystemState::ACTIVE_L4);
            }
            break;

        case AdasSystemState::MINIMAL_RISK:
            if (criticalFault || emergencyStopRequired) {
                transition(AdasSystemState::SAFE_STOP); break;
            }
            if (pulloverComplete) {
                transition(AdasSystemState::SAFE_STOP);
            }
            break;

        case AdasSystemState::SAFE_STOP:
            // Latching state – only ignition cycle clears
            break;

        case AdasSystemState::FAULT:
            // Latching – service required
            break;

        case AdasSystemState::PULL_OVER:
            if (pulloverComplete) transition(AdasSystemState::SAFE_STOP);
            break;
    }
}

} // namespace safety
} // namespace adas
