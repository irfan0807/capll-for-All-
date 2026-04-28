#pragma once
// ============================================================================
// sensor_fusion.hpp  –  Extended Kalman Filter based multi-sensor fusion
// ============================================================================
#include "perception_types.hpp"
#include "../sensors/lidar_sensor.hpp"
#include "../sensors/radar_sensor.hpp"
#include "../sensors/camera_sensor.hpp"

namespace adas {
namespace perception {

// ---------------------------------------------------------------------------
// KF state per track (8-dimensional)
// ---------------------------------------------------------------------------
struct KFState {
    float x[8];    ///< [px, py, vx, vy, ax, ay, yaw, yaw_rate]
    float P[8][8]; ///< Covariance matrix
    bool  valid;
};

// ---------------------------------------------------------------------------
// SensorFusion: maintains one KF per tracked ID
// ---------------------------------------------------------------------------
class SensorFusion {
public:
    SensorFusion();

    /// Feed latest sensor outputs (call before process())
    void setLidarScan  (const LidarScan&   scan);
    void setRadarScan  (const RadarScan&    scan);
    void setCameraFrame(const CameraFrame&  frame);

    /// Run one fusion cycle (call at 10 Hz)
    void process(float dt_s);

    /// Get fused object list
    const ObjectList& getObjectList() const { return m_objectList; }

    /// Compute TTC for all confirmed tracks
    void computeTTC(float ego_speed_mps);

private:
    static constexpr float DT_DEFAULT     = 0.1f;  // 10 Hz
    static constexpr float GATE_THRESHOLD = 9.49f; // Chi-sq 4 dof, 99%
    static constexpr float SIGMA_PROCESS  = 2.0f;  // m/s² process noise

    void   predictAll(float dt_s);
    void   associateAndUpdate();
    void   manageTrackLifecycle();
    void   updateFromLidar  (TrackedObject& track);
    void   updateFromRadar  (TrackedObject& track);
    void   updateFromCamera (TrackedObject& track);
    KFState initTrack(float px, float py) const;
    float  mahalanobisDistance(const KFState& state,
                                float obs_x, float obs_y) const;
    void   buildF(float F[8][8], float dt_s) const;
    void   matMul8(const float A[8][8], const float B[8][8],
                   float C[8][8]) const;
    void   matAdd8(const float A[8][8], const float B[8][8],
                   float C[8][8]) const;
    void   transposeF(const float F[8][8], float Ft[8][8]) const;

    KFState      m_states[MAX_TRACKED_OBJECTS];
    TrackedObject m_tracks[MAX_TRACKED_OBJECTS];
    uint8_t       m_trackCount;
    uint8_t       m_nextId;
    ObjectList    m_objectList;

    // Latest sensor data
    LidarScan   m_lidarScan;
    RadarScan   m_radarScan;
    CameraFrame m_cameraFrame;
};

} // namespace perception
} // namespace adas
