#pragma once
// ============================================================================
// pid_controller.hpp  –  Generic discrete-time PID controller
// ============================================================================

namespace adas {
namespace control {

class PidController {
public:
    PidController(float kp, float ki, float kd,
                  float outputMin, float outputMax,
                  float integralMax);

    /// Compute PID output. dt_s = time step in seconds
    float compute(float setpoint, float measurement, float dt_s);

    void reset();
    void setGains(float kp, float ki, float kd);
    void setLimits(float outputMin, float outputMax);

    float getP() const { return m_kp; }
    float getI() const { return m_ki; }
    float getD() const { return m_kd; }
    float getIntegral() const { return m_integral; }

private:
    float m_kp, m_ki, m_kd;
    float m_outputMin, m_outputMax;
    float m_integralMax;
    float m_integral;
    float m_prevError;
    bool  m_firstCycle;

    float clamp(float v, float lo, float hi) const;
};

} // namespace control
} // namespace adas
