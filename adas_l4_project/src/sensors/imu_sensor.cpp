// ============================================================================
// imu_sensor.cpp
// ============================================================================
#include "../../include/sensors/imu_sensor.hpp"
#include <cmath>

namespace adas {

ImuSensor::ImuSensor()
    : m_health(SensorHealth::INIT),
      m_lastTimestamp_ms(0), m_systemTime_ms(0)
{
    m_data = {};
    m_data.health = SensorHealth::INIT;
}

bool ImuSensor::isDataPlausible(const ImuData& d) const {
    if (fabsf(d.ax) > MAX_ACCEL_MPS2 || fabsf(d.ay) > MAX_ACCEL_MPS2 ||
        fabsf(d.az) > MAX_ACCEL_MPS2) return false;
    if (fabsf(d.gx) > MAX_GYRO_RADPS || fabsf(d.gy) > MAX_GYRO_RADPS ||
        fabsf(d.gz) > MAX_GYRO_RADPS) return false;
    return true;
}

void ImuSensor::injectData(const ImuData& data) {
    if (!isDataPlausible(data)) {
        m_health      = SensorHealth::DEGRADED;
        m_data.health = SensorHealth::DEGRADED;
        return;
    }
    m_data             = data;
    m_lastTimestamp_ms = data.timestamp_ms;
    m_systemTime_ms    = data.timestamp_ms;
    m_health           = SensorHealth::OK;
    m_data.health      = SensorHealth::OK;
}

void ImuSensor::cyclic100ms() {
    m_systemTime_ms += 100U;
    if (m_lastTimestamp_ms > 0 &&
        (m_systemTime_ms - m_lastTimestamp_ms) > TIMEOUT_THRESHOLD_MS) {
        m_health      = SensorHealth::FAILED;
        m_data.health = SensorHealth::FAILED;
    }
}

} // namespace adas
