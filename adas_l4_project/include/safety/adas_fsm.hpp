#pragma once
// ============================================================================
// adas_fsm.hpp  –  ADAS L4 system operating state machine
// ============================================================================
#include <cstdint>

namespace adas {
namespace safety {

enum class AdasSystemState : uint8_t {
    POWER_OFF       = 0,
    SELF_TEST       = 1,
    STANDBY         = 2,
    ACTIVE_L4       = 3,
    DEGRADED        = 4,
    SAFE_STOP       = 5,
    MINIMAL_RISK    = 6,
    PULL_OVER       = 7,
    FAULT           = 8
};

const char* stateToStr(AdasSystemState s);

class AdasFSM {
public:
    AdasFSM();

    /// Called on ignition on
    void onIgnitionOn();
    /// Called on ignition off
    void onIgnitionOff();
    /// Request L4 engagement (driver presses button)
    void requestEngage();
    /// Driver requests manual takeover
    void requestDisengage();

    /// Feed fault and condition flags (call at 10 Hz)
    void update(bool selfTestPassed,
                bool oddValid,
                bool criticalFault,
                bool majorFault,
                bool emergencyStopRequired,
                bool pulloverComplete);

    AdasSystemState getState() const { return m_state; }
    bool isL4Active()    const { return m_state == AdasSystemState::ACTIVE_L4; }
    bool isSafeState()   const;

private:
    void transition(AdasSystemState next);

    AdasSystemState m_state;
    uint16_t        m_selfTestCycles;
    bool            m_engageRequested;
};

} // namespace safety
} // namespace adas
