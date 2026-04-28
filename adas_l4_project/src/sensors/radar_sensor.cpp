// ============================================================================
// radar_sensor.cpp
// ============================================================================
#include "../../include/sensors/radar_sensor.hpp"

namespace adas {

RadarSensor::RadarSensor(uint8_t sensorId)
    : m_sensorId(sensorId), m_health(SensorHealth::INIT),
      m_lastTimestamp_ms(0), m_systemTime_ms(0)
{
    m_scan.count = 0;
    m_scan.health = SensorHealth::INIT;
}

void RadarSensor::injectObjectList(const RadarScan& scan) {
    m_scan             = scan;
    m_lastTimestamp_ms = scan.timestamp_ms;
    m_systemTime_ms    = scan.timestamp_ms;
    m_health           = SensorHealth::OK;
    m_scan.health      = SensorHealth::OK;
}

void RadarSensor::cyclic100ms() {
    m_systemTime_ms += 100U;
    if (m_lastTimestamp_ms > 0 &&
        (m_systemTime_ms - m_lastTimestamp_ms) > TIMEOUT_THRESHOLD_MS) {
        m_health      = SensorHealth::FAILED;
        m_scan.health = SensorHealth::FAILED;
    }
}

} // namespace adas
