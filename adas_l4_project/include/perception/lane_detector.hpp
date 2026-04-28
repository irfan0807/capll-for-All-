#pragma once
// ============================================================================
// lane_detector.hpp  –  Lane estimation from camera and LiDAR
// ============================================================================
#include "perception_types.hpp"
#include "../sensors/camera_sensor.hpp"
#include "../sensors/lidar_sensor.hpp"

namespace adas {
namespace perception {

class LaneDetector {
public:
    LaneDetector();

    void setCameraFrame(const CameraFrame& frame);
    void setLidarScan  (const LidarScan&   scan);

    /// Compute lane estimate (call at 10 Hz)
    void process();

    const LaneEstimate& getLaneEstimate() const { return m_estimate; }

    /// Check if ego is departing lane (|offset| > threshold)
    bool isLaneDeparture(float threshold_m = 0.5f) const;

private:
    static constexpr float LANE_WIDTH_MIN = 2.5f;
    static constexpr float LANE_WIDTH_MAX = 5.0f;
    static constexpr float QUALITY_DECAY  = 0.95f; // per cycle if no update

    void fuseCameraAndLidar();
    void decayQuality();

    CameraFrame  m_cameraFrame;
    LidarScan    m_lidarScan;
    LaneEstimate m_estimate;
};

} // namespace perception
} // namespace adas
