#pragma once
// ============================================================================
// vehicle_controller.hpp  –  Top-level vehicle actuator controller
//   Longitudinal: PID-based speed/ACC control
//   Lateral: Stanley path-tracking controller
// ============================================================================
#include "pid_controller.hpp"
#include "../planning/route_types.hpp"

namespace adas {
namespace control {

// ---------------------------------------------------------------------------
// Actuator output (to vehicle bus / CAN)
// ---------------------------------------------------------------------------
struct ActuatorCommands {
    float   throttle_pct;    ///< 0.0 – 100.0 %
    float   brake_pct;       ///< 0.0 – 100.0 %
    float   steering_deg;    ///< -540 to +540 (steering wheel angle)
    uint8_t gear;            ///< 1=D, 2=N, 3=R, 4=P
    bool    aeb_active;      ///< AEB hard braking flag
};

class VehicleController {
public:
    VehicleController();

    /// Update ego state
    void setEgoState(float speed_mps, float yaw_rad, float x_m, float y_m);

    /// Set planned trajectory to follow
    void setTrajectory(const planning::Trajectory& traj);

    /// Emergency stop command
    void triggerEmergencyStop();
    void clearEmergencyStop();

    /// Run control loop (call at 10 Hz)
    void compute(float dt_s);

    const ActuatorCommands& getCommands() const { return m_commands; }

    bool isEmergencyStopActive() const { return m_emergencyStop; }

private:
    static constexpr float MAX_STEERING_WHEEL_DEG = 540.0f;
    static constexpr float WHEELBASE_M            = 2.8f;   // typical sedan
    static constexpr float STANLEY_GAIN           = 1.2f;
    static constexpr float SPEED_PID_KP          = 0.5f;
    static constexpr float SPEED_PID_KI          = 0.1f;
    static constexpr float SPEED_PID_KD          = 0.05f;
    static constexpr float BRAKE_GAIN            = 1.5f;   // converts PID neg output → brake%

    float computeStanleySteer(const planning::TrajectoryPoint& target) const;
    const planning::TrajectoryPoint* findLookahead(float lookahead_m) const;

    PidController          m_speedPid;
    ActuatorCommands       m_commands;
    planning::Trajectory   m_trajectory;
    bool                   m_emergencyStop;

    float    m_egoSpeed, m_egoYaw, m_egoX, m_egoY;
};

} // namespace control
} // namespace adas
