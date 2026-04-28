#pragma once
// ============================================================================
// camera_sensor.hpp  –  Camera sensor interface
// ============================================================================
#include "sensor_types.hpp"

namespace adas {

class CameraSensor {
public:
    explicit CameraSensor(uint8_t cameraId);

    /// Inject processed frame (detections already run through NN)
    void injectFrame(const CameraFrame& frame);

    const CameraFrame& getFrame() const { return m_frame; }
    SensorHealth       getHealth() const { return m_health; }
    uint8_t            getCameraId() const { return m_cameraId; }

    void cyclic100ms();

private:
    static constexpr uint32_t TIMEOUT_THRESHOLD_MS = 100U;

    uint8_t      m_cameraId;
    CameraFrame  m_frame;
    SensorHealth m_health;
    uint32_t     m_lastTimestamp_ms;
    uint32_t     m_systemTime_ms;
};

} // namespace adas
