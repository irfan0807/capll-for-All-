// ============================================================================
// lane_detector.cpp  –  Lane estimation from camera output
// ============================================================================
#include "../../include/perception/lane_detector.hpp"
#include <cmath>

namespace adas {
namespace perception {

LaneDetector::LaneDetector() {
    m_estimate = {};
    m_estimate.quality = 0;
}

void LaneDetector::setCameraFrame(const CameraFrame& frame) {
    m_cameraFrame = frame;
}

void LaneDetector::setLidarScan(const LidarScan& scan) {
    m_lidarScan = scan;
}

void LaneDetector::process() {
    fuseCameraAndLidar();
}

bool LaneDetector::isLaneDeparture(float threshold_m) const {
    return fabsf(m_estimate.lateral_offset_m) > threshold_m &&
           m_estimate.quality > 30;
}

void LaneDetector::fuseCameraAndLidar() {
    // Primary source: camera lane data
    if (m_cameraFrame.health == SensorHealth::OK &&
        m_cameraFrame.lane_quality > 20) {

        m_estimate.lateral_offset_m  = m_cameraFrame.left_lane_offset_m +
                                        m_cameraFrame.right_lane_offset_m;
        m_estimate.lateral_offset_m /= 2.0f;  // ego position in lane

        float lw = m_cameraFrame.lane_width_m;
        if (lw > LANE_WIDTH_MIN && lw < LANE_WIDTH_MAX) {
            m_estimate.lane_width_m = lw;
        } else {
            m_estimate.lane_width_m = 3.5f;  // default
        }

        m_estimate.curvature_inv_m = m_cameraFrame.lane_curvature_inv_m;
        m_estimate.quality         = static_cast<uint8_t>(m_cameraFrame.lane_quality);
        m_estimate.left_marking_valid  = true;
        m_estimate.right_marking_valid = true;
        m_estimate.timestamp_ms = m_cameraFrame.timestamp_ms;
    } else {
        // Decay quality if camera unavailable
        decayQuality();
        m_estimate.left_marking_valid  = false;
        m_estimate.right_marking_valid = false;
    }
}

void LaneDetector::decayQuality() {
    if (m_estimate.quality > 0) {
        float q = static_cast<float>(m_estimate.quality) * QUALITY_DECAY;
        m_estimate.quality = static_cast<uint8_t>(q);
    }
}

} // namespace perception
} // namespace adas
