// ============================================================================
// safety_monitor.cpp  –  ASIL-D safety monitoring implementation
// ============================================================================
#include "../../include/safety/safety_monitor.hpp"
#include <cstring>
#include <cmath>

namespace adas {
namespace safety {

SafetyMonitor::SafetyMonitor()
    : m_minTtc(99.0f), m_aebRequired(false),
      m_egoSpeed_mps(0), m_cmdSpeed_mps(0),
      m_fusionKickTs(0), m_planKickTs(0), m_ctrlKickTs(0)
{
    memset(&m_faults, 0, sizeof(m_faults));
}

void SafetyMonitor::updateSensorHealth(SensorHealth lidar,
                                        SensorHealth camera,
                                        SensorHealth radar,
                                        SensorHealth imu) {
    m_faults.lidar_failed  = (lidar  == SensorHealth::FAILED);
    m_faults.camera_failed = (camera == SensorHealth::FAILED);
    m_faults.radar_failed  = (radar  == SensorHealth::FAILED);
    m_faults.imu_failed    = (imu    == SensorHealth::FAILED);
}

void SafetyMonitor::updateObjectList(const perception::ObjectList& objects) {
    m_minTtc     = 99.0f;
    m_aebRequired = false;

    for (uint8_t i = 0; i < objects.count; ++i) {
        const auto& obj = objects.objects[i];
        if (obj.ttc_s > 0.0f && obj.ttc_s < m_minTtc) {
            m_minTtc = obj.ttc_s;
        }
    }

    if (m_minTtc < TTC_AEB_THRESHOLD) m_aebRequired = true;
}

void SafetyMonitor::updateSpeed(float ego_mps, float cmd_mps) {
    m_egoSpeed_mps = ego_mps;
    m_cmdSpeed_mps = cmd_mps;
    m_faults.speed_exceeded =
        (m_egoSpeed_mps > m_cmdSpeed_mps + SPEED_OVERSHOOT_MPS);
}

void SafetyMonitor::kickFusionWatchdog   (uint32_t ts) { m_fusionKickTs = ts; }
void SafetyMonitor::kickPlanningWatchdog (uint32_t ts) { m_planKickTs   = ts; }
void SafetyMonitor::kickControlWatchdog  (uint32_t ts) { m_ctrlKickTs   = ts; }

SafetyDecision SafetyMonitor::evaluate(uint32_t now_ms) {
    // Watchdog checks
    m_faults.fusion_timeout  = (now_ms - m_fusionKickTs  > FUSION_TIMEOUT_MS);
    m_faults.planning_timeout= (now_ms - m_planKickTs    > PLAN_TIMEOUT_MS);
    m_faults.control_timeout = (now_ms - m_ctrlKickTs    > CTRL_TIMEOUT_MS);

    // Emergency conditions
    if (m_aebRequired || m_faults.steering_fault || m_faults.speed_exceeded ||
        m_faults.control_timeout) {
        return SafetyDecision::EMERGENCY_STOP;
    }

    // Minimal risk condition
    uint8_t failCount = static_cast<uint8_t>(m_faults.lidar_failed) +
                        static_cast<uint8_t>(m_faults.camera_failed) +
                        static_cast<uint8_t>(m_faults.radar_failed);

    if (failCount >= 2 || m_faults.planning_timeout) {
        return SafetyDecision::MINIMAL_RISK;
    }

    // Warn / degrade
    if (failCount == 1 || m_faults.fusion_timeout) {
        return SafetyDecision::DEGRADE_ODD;
    }

    if (m_minTtc < TTC_WARN_THRESHOLD) {
        return SafetyDecision::WARN;
    }

    return SafetyDecision::NOMINAL;
}

} // namespace safety
} // namespace adas
