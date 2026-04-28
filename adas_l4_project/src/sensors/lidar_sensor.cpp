// ============================================================================
// lidar_sensor.cpp  –  LiDAR sensor implementation with RANSAC ground removal
// ============================================================================
#include "../../include/sensors/lidar_sensor.hpp"
#include <cstring>
#include <cstdlib>
#include <cmath>

namespace adas {

LidarSensor::LidarSensor()
    : m_groundA(0.0f), m_groundB(0.0f), m_groundC(1.0f), m_groundD(0.0f),
      m_health(SensorHealth::INIT),
      m_lastTimestamp_ms(0), m_systemTime_ms(0)
{
    m_rawScan.count      = 0;
    m_obstacleScan.count = 0;
    m_rawScan.health     = SensorHealth::INIT;
    m_obstacleScan.health= SensorHealth::INIT;
}

void LidarSensor::injectScan(const LidarScan& scan) {
    m_rawScan           = scan;
    m_lastTimestamp_ms  = scan.timestamp_ms;
    m_systemTime_ms     = scan.timestamp_ms;
    m_health            = SensorHealth::OK;
    removeGroundPlane();
}

const LidarScan& LidarSensor::getObstacleScan() const {
    return m_obstacleScan;
}

void LidarSensor::getGroundPlane(float& a, float& b, float& c, float& d) const {
    a = m_groundA; b = m_groundB; c = m_groundC; d = m_groundD;
}

void LidarSensor::cyclic100ms() {
    m_systemTime_ms += 100U;
    if (m_lastTimestamp_ms > 0 &&
        (m_systemTime_ms - m_lastTimestamp_ms) > TIMEOUT_THRESHOLD_MS) {
        m_health = SensorHealth::FAILED;
    }
}

// ---------------------------------------------------------------------------
// RANSAC ground plane removal
// ---------------------------------------------------------------------------
bool LidarSensor::fitPlane(const LidarPoint& p1, const LidarPoint& p2,
                            const LidarPoint& p3,
                            float& a, float& b, float& c, float& d) const {
    // Two edge vectors
    float ux = p2.x - p1.x, uy = p2.y - p1.y, uz = p2.z - p1.z;
    float vx = p3.x - p1.x, vy = p3.y - p1.y, vz = p3.z - p1.z;
    // Cross product → normal
    a = uy * vz - uz * vy;
    b = uz * vx - ux * vz;
    c = ux * vy - uy * vx;
    float len = sqrtf(a*a + b*b + c*c);
    if (len < 1e-6f) return false;
    a /= len; b /= len; c /= len;
    d = -(a * p1.x + b * p1.y + c * p1.z);
    return true;
}

uint32_t LidarSensor::countInliers(float a, float b, float c, float d) const {
    uint32_t count = 0;
    for (uint32_t i = 0; i < m_rawScan.count; ++i) {
        const LidarPoint& p = m_rawScan.points[i];
        float dist = fabsf(a * p.x + b * p.y + c * p.z + d);
        if (dist < GROUND_DIST_THRESHOLD) ++count;
    }
    return count;
}

void LidarSensor::removeGroundPlane() {
    if (m_rawScan.count < 3U) {
        m_obstacleScan = m_rawScan;
        return;
    }

    float bestA = 0, bestB = 0, bestC = 1, bestD = 0;
    uint32_t bestCount = 0;

    // Simple pseudo-random seed for reproducibility
    uint32_t rng = 12345U;
    for (uint32_t iter = 0; iter < RANSAC_ITERATIONS; ++iter) {
        // Cheap LCG RNG
        rng = rng * 1664525U + 1013904223U;
        uint32_t i1 = rng % m_rawScan.count;
        rng = rng * 1664525U + 1013904223U;
        uint32_t i2 = rng % m_rawScan.count;
        rng = rng * 1664525U + 1013904223U;
        uint32_t i3 = rng % m_rawScan.count;

        if (i1 == i2 || i2 == i3 || i1 == i3) continue;

        float a, b, c, d;
        if (!fitPlane(m_rawScan.points[i1], m_rawScan.points[i2],
                      m_rawScan.points[i3], a, b, c, d)) continue;

        // Ground planes have normal pointing roughly upward
        if (c < 0.8f) continue;

        uint32_t inliers = countInliers(a, b, c, d);
        if (inliers > bestCount) {
            bestCount = inliers;
            bestA = a; bestB = b; bestC = c; bestD = d;
        }
    }

    m_groundA = bestA; m_groundB = bestB;
    m_groundC = bestC; m_groundD = bestD;

    // Copy non-ground points to obstacle scan
    uint32_t obsCount = 0;
    for (uint32_t i = 0; i < m_rawScan.count && obsCount < MAX_LIDAR_POINTS; ++i) {
        const LidarPoint& p = m_rawScan.points[i];
        float dist = fabsf(bestA * p.x + bestB * p.y + bestC * p.z + bestD);
        if (dist >= GROUND_DIST_THRESHOLD) {
            m_obstacleScan.points[obsCount++] = p;
        }
    }
    m_obstacleScan.count        = obsCount;
    m_obstacleScan.timestamp_ms = m_rawScan.timestamp_ms;
    m_obstacleScan.health       = SensorHealth::OK;
}

} // namespace adas
