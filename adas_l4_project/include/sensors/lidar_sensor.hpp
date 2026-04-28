#pragma once
// ============================================================================
// lidar_sensor.hpp  –  LiDAR sensor interface and ground-plane removal
// ============================================================================
#include "sensor_types.hpp"

namespace adas {

class LidarSensor {
public:
    LidarSensor();

    /// Inject a raw scan (called by hardware driver / simulator)
    void injectScan(const LidarScan& scan);

    /// Get latest processed scan (ground removed)
    const LidarScan& getObstacleScan() const;

    /// Get ground plane normal vector (ax + by + cz + d = 0)
    void getGroundPlane(float& a, float& b, float& c, float& d) const;

    SensorHealth getHealth() const { return m_health; }

    /// Called every 100ms – check for timeout
    void cyclic100ms();

private:
    static constexpr uint32_t TIMEOUT_THRESHOLD_MS = 200U;  // Missing frames
    static constexpr uint32_t RANSAC_ITERATIONS     = 100U;
    static constexpr float    GROUND_DIST_THRESHOLD = 0.15f; // m

    void removeGroundPlane();
    bool fitPlane(const LidarPoint& p1, const LidarPoint& p2,
                  const LidarPoint& p3,
                  float& a, float& b, float& c, float& d) const;
    uint32_t countInliers(float a, float b, float c, float d) const;

    LidarScan    m_rawScan;
    LidarScan    m_obstacleScan;
    float        m_groundA, m_groundB, m_groundC, m_groundD;
    SensorHealth m_health;
    uint32_t     m_lastTimestamp_ms;
    uint32_t     m_systemTime_ms;
};

} // namespace adas
