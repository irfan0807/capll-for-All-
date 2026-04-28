// ============================================================================
// pid_controller.cpp
// ============================================================================
#include "../../include/control/pid_controller.hpp"
#include <cmath>

namespace adas {
namespace control {

PidController::PidController(float kp, float ki, float kd,
                              float outMin, float outMax, float intMax)
    : m_kp(kp), m_ki(ki), m_kd(kd),
      m_outputMin(outMin), m_outputMax(outMax),
      m_integralMax(intMax),
      m_integral(0.0f), m_prevError(0.0f), m_firstCycle(true)
{}

float PidController::clamp(float v, float lo, float hi) const {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

void PidController::setGains (float kp, float ki, float kd)    { m_kp=kp; m_ki=ki; m_kd=kd; }
void PidController::setLimits(float lo, float hi)               { m_outputMin=lo; m_outputMax=hi; }

void PidController::reset() {
    m_integral   = 0.0f;
    m_prevError  = 0.0f;
    m_firstCycle = true;
}

float PidController::compute(float setpoint, float measurement, float dt_s) {
    float error = setpoint - measurement;

    float derivative = 0.0f;
    if (!m_firstCycle && dt_s > 1e-6f) {
        derivative = (error - m_prevError) / dt_s;
    }
    m_firstCycle = false;
    m_prevError  = error;

    // Anti-windup: only integrate if not saturated in error direction
    m_integral += error * dt_s;
    m_integral = clamp(m_integral, -m_integralMax, m_integralMax);

    float out = m_kp * error
              + m_ki * m_integral
              + m_kd * derivative;

    return clamp(out, m_outputMin, m_outputMax);
}

} // namespace control
} // namespace adas
