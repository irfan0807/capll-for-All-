// ============================================================================
// vehicle_controller.cpp  –  Speed PID + Stanley lateral controller
// ============================================================================
#include "../../include/control/vehicle_controller.hpp"
#include <cmath>
#include <cstring>

namespace adas {
namespace control {

VehicleController::VehicleController()
    : m_speedPid(SPEED_PID_KP, SPEED_PID_KI, SPEED_PID_KD,
                  -10.0f, 10.0f, 20.0f),
      m_emergencyStop(false),
      m_egoSpeed(0), m_egoYaw(0), m_egoX(0), m_egoY(0)
{
    memset(&m_commands,   0, sizeof(m_commands));
    memset(&m_trajectory, 0, sizeof(m_trajectory));
    m_commands.gear = 1U;  // Drive
}

void VehicleController::setEgoState(float spd, float yaw, float x, float y) {
    m_egoSpeed = spd; m_egoYaw = yaw; m_egoX = x; m_egoY = y;
}

void VehicleController::setTrajectory(const planning::Trajectory& t) {
    m_trajectory = t;
}

void VehicleController::triggerEmergencyStop() {
    m_emergencyStop = true;
    m_speedPid.reset();
}

void VehicleController::clearEmergencyStop() {
    m_emergencyStop = false;
}

// ---------------------------------------------------------------------------
// Stanley lateral controller: δ = ψ_e + arctan(k·e_fa / v)
// ---------------------------------------------------------------------------
float VehicleController::computeStanleySteer(
        const planning::TrajectoryPoint& target) const {

    // Heading error
    float psi_e = target.heading_rad - m_egoYaw;
    // Normalise to [-pi, pi]
    while (psi_e >  3.14159265f) psi_e -= 2.0f * 3.14159265f;
    while (psi_e < -3.14159265f) psi_e += 2.0f * 3.14159265f;

    // Cross-track error at front axle (approx at lookahead point)
    float e_fa = (target.y_m - m_egoY) * cosf(m_egoYaw)
               - (target.x_m - m_egoX) * sinf(m_egoYaw);

    float speed = (m_egoSpeed < 0.5f) ? 0.5f : m_egoSpeed;
    float delta = psi_e + atanf(STANLEY_GAIN * e_fa / speed);

    // Convert front wheel angle to steering wheel angle (rough ratio 15:1)
    float sw_deg = delta * 180.0f / 3.14159265f * 15.0f;

    if (sw_deg >  MAX_STEERING_WHEEL_DEG) sw_deg =  MAX_STEERING_WHEEL_DEG;
    if (sw_deg < -MAX_STEERING_WHEEL_DEG) sw_deg = -MAX_STEERING_WHEEL_DEG;
    return sw_deg;
}

const planning::TrajectoryPoint* VehicleController::findLookahead(
        float lookahead_m) const {

    if (m_trajectory.count == 0) return nullptr;

    for (uint8_t i = 0; i < m_trajectory.count; ++i) {
        float dx = m_trajectory.pts[i].x_m - m_egoX;
        float dy = m_trajectory.pts[i].y_m - m_egoY;
        float dist = sqrtf(dx*dx + dy*dy);
        if (dist >= lookahead_m) return &m_trajectory.pts[i];
    }
    return &m_trajectory.pts[m_trajectory.count - 1];
}

void VehicleController::compute(float dt_s) {
    // Emergency stop override
    if (m_emergencyStop) {
        m_commands.throttle_pct = 0.0f;
        m_commands.brake_pct    = 100.0f;
        m_commands.steering_deg = 0.0f;
        m_commands.aeb_active   = true;
        m_commands.gear         = 1U;
        return;
    }

    m_commands.aeb_active = false;

    if (!m_trajectory.valid || m_trajectory.count == 0) {
        // Default: hold speed, keep straight
        m_commands.brake_pct    = 0.0f;
        m_commands.throttle_pct = 0.0f;
        return;
    }

    // --- Longitudinal PID ---
    float target_speed = m_trajectory.pts[0].speed_mps;
    float pid_out = m_speedPid.compute(target_speed, m_egoSpeed, dt_s);

    if (pid_out >= 0.0f) {
        m_commands.throttle_pct = pid_out * 10.0f;  // scale to 0-100%
        if (m_commands.throttle_pct > 100.0f) m_commands.throttle_pct = 100.0f;
        m_commands.brake_pct = 0.0f;
    } else {
        m_commands.throttle_pct = 0.0f;
        m_commands.brake_pct = (-pid_out) * BRAKE_GAIN * 10.0f;
        if (m_commands.brake_pct > 100.0f) m_commands.brake_pct = 100.0f;
    }

    // --- Lateral Stanley ---
    float lookahead = 5.0f + 0.3f * m_egoSpeed;
    const planning::TrajectoryPoint* target = findLookahead(lookahead);
    if (target) {
        m_commands.steering_deg = computeStanleySteer(*target);
    }

    m_commands.gear = (m_egoSpeed >= 0.0f) ? 1U : 3U;  // D or R
}

} // namespace control
} // namespace adas
