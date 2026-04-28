#pragma once
// ============================================================================
// safety_monitor.hpp  –  ISO 26262 ASIL-D safety monitoring
// ============================================================================
#include "adas_fsm.hpp"
#include "../sensors/sensor_types.hpp"
#include "../perception/perception_types.hpp"
#include <cstdint>

namespace adas {
namespace safety {

// ---------------------------------------------------------------------------
// Fault flags bitmask
// ---------------------------------------------------------------------------
struct FaultFlags {
    bool lidar_failed      : 1;
    bool camera_failed     : 1;
    bool radar_failed      : 1;
    bool imu_failed        : 1;
    bool gnss_failed       : 1;
    bool fusion_timeout    : 1;
    bool planning_timeout  : 1;
    bool control_timeout   : 1;
    bool speed_exceeded    : 1;
    bool steering_fault    : 1;
    uint8_t reserved       : 6;
};

// ---------------------------------------------------------------------------
// Safety evaluation result
// ---------------------------------------------------------------------------
enum class SafetyDecision : uint8_t {
    NOMINAL        = 0,
    WARN           = 1,
    DEGRADE_ODD    = 2,
    MINIMAL_RISK   = 3,
    EMERGENCY_STOP = 4
};

class SafetyMonitor {
public:
    SafetyMonitor();

    /// Supply sensor health flags
    void updateSensorHealth(SensorHealth lidar,
                            SensorHealth camera,
                            SensorHealth radar,
                            SensorHealth imu);

    /// Supply perception object list (for TTC check)
    void updateObjectList(const perception::ObjectList& objects);

    /// Supply ego speed and commanded speed (for over-speed check)
    void updateSpeed(float ego_mps, float cmd_mps);

    /// Supply task-alive timestamps
    void kickFusionWatchdog   (uint32_t ts_ms);
    void kickPlanningWatchdog (uint32_t ts_ms);
    void kickControlWatchdog  (uint32_t ts_ms);

    /// Evaluate all faults (call at 1 ms cycle)
    SafetyDecision evaluate(uint32_t now_ms);

    const FaultFlags& getFaults() const { return m_faults; }
    float             getMinTTC()  const { return m_minTtc; }
    bool              isAebRequired() const { return m_aebRequired; }

private:
    static constexpr float   TTC_AEB_THRESHOLD    = 1.0f;  // seconds
    static constexpr float   TTC_WARN_THRESHOLD   = 2.5f;
    static constexpr float   SPEED_OVERSHOOT_MPS  = 3.0f;  // +3 m/s tolerance
    static constexpr uint32_t FUSION_TIMEOUT_MS   = 50U;
    static constexpr uint32_t PLAN_TIMEOUT_MS     = 200U;
    static constexpr uint32_t CTRL_TIMEOUT_MS     = 50U;

    FaultFlags  m_faults;
    float       m_minTtc;
    bool        m_aebRequired;

    float    m_egoSpeed_mps;
    float    m_cmdSpeed_mps;

    uint32_t m_fusionKickTs;
    uint32_t m_planKickTs;
    uint32_t m_ctrlKickTs;
};

} // namespace safety
} // namespace adas
