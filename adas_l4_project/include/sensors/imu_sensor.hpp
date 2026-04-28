#pragma once
// ============================================================================
// imu_sensor.hpp  –  IMU sensor interface (6-DOF MEMS)
// ============================================================================
#include "sensor_types.hpp"

namespace adas {

class ImuSensor {
public:
    ImuSensor();

    void injectData(const ImuData& data);

    const ImuData& getData() const { return m_data; }
    SensorHealth   getHealth() const { return m_health; }

    /// Validate data ranges (|a| < 20 m/s², |g| < 5.24 rad/s)
    bool isDataPlausible(const ImuData& d) const;

    void cyclic100ms();

private:
    static constexpr uint32_t TIMEOUT_THRESHOLD_MS = 20U;  // 50Hz minimum
    static constexpr float    MAX_ACCEL_MPS2       = 20.0f;
    static constexpr float    MAX_GYRO_RADPS       = 5.24f; // 300 deg/s

    ImuData      m_data;
    SensorHealth m_health;
    uint32_t     m_lastTimestamp_ms;
    uint32_t     m_systemTime_ms;
};

} // namespace adas
