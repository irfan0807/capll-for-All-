// ============================================================================
// camera_sensor.cpp
// ============================================================================
#include "../../include/sensors/camera_sensor.hpp"

namespace adas {

CameraSensor::CameraSensor(uint8_t cameraId)
    : m_cameraId(cameraId), m_health(SensorHealth::INIT),
      m_lastTimestamp_ms(0), m_systemTime_ms(0)
{
    m_frame.count  = 0;
    m_frame.health = SensorHealth::INIT;
}

void CameraSensor::injectFrame(const CameraFrame& frame) {
    m_frame            = frame;
    m_lastTimestamp_ms = frame.timestamp_ms;
    m_systemTime_ms    = frame.timestamp_ms;
    m_health           = SensorHealth::OK;
    m_frame.health     = SensorHealth::OK;
}

void CameraSensor::cyclic100ms() {
    m_systemTime_ms += 100U;
    if (m_lastTimestamp_ms > 0 &&
        (m_systemTime_ms - m_lastTimestamp_ms) > TIMEOUT_THRESHOLD_MS) {
        m_health       = SensorHealth::FAILED;
        m_frame.health = SensorHealth::FAILED;
    }
}

} // namespace adas
