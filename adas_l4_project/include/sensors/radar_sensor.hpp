#pragma once
// ============================================================================
// radar_sensor.hpp  –  Radar sensor interface (FMCW 77GHz)
// ============================================================================
#include "sensor_types.hpp"

namespace adas {

class RadarSensor {
public:
    explicit RadarSensor(uint8_t sensorId);

    /// Inject object list from radar hardware / CAN parser
    void injectObjectList(const RadarScan& scan);

    const RadarScan& getScan() const { return m_scan; }
    SensorHealth     getHealth() const { return m_health; }

    uint8_t getSensorId() const { return m_sensorId; }

    void cyclic100ms();

private:
    static constexpr uint32_t TIMEOUT_THRESHOLD_MS = 150U;

    uint8_t      m_sensorId;
    RadarScan    m_scan;
    SensorHealth m_health;
    uint32_t     m_lastTimestamp_ms;
    uint32_t     m_systemTime_ms;
};

} // namespace adas
