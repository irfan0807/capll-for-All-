#pragma once
// ============================================================================
// perception_types.hpp  –  Output types from the perception layer
// ============================================================================
#include "../sensors/sensor_types.hpp"

namespace adas {
namespace perception {

static constexpr uint8_t MAX_TRACKED_OBJECTS = 32U;

// ---------------------------------------------------------------------------
// Track life cycle state
// ---------------------------------------------------------------------------
enum class TrackState : uint8_t {
    NEW_CANDIDATE = 0,
    PROBABLE      = 1,
    CONFIRMED     = 2,
    LOST          = 3
};

// ---------------------------------------------------------------------------
// Fused and tracked object (output of sensor fusion + MOT)
// ---------------------------------------------------------------------------
struct TrackedObject {
    uint8_t     id;
    ObjectClass object_class;
    TrackState  state;

    // Kinematics in vehicle frame
    float x_m;          ///< forward, metres
    float y_m;          ///< lateral, metres (+ = left)
    float z_m;          ///< height, metres
    float vx_mps;       ///< forward velocity, m/s
    float vy_mps;       ///< lateral velocity, m/s
    float ax_mps2;      ///< forward acceleration
    float ay_mps2;      ///< lateral acceleration
    float yaw_rad;      ///< heading
    float yaw_rate_rps; ///< turn rate

    // Geometry
    float length_m;
    float width_m;
    float height_m;

    float confidence;       ///< 0.0 – 1.0
    float ttc_s;            ///< time-to-collision (INVALID_FLOAT if not applicable)

    uint8_t  observed_by;   ///< bitmask: bit0=LiDAR, bit1=Camera, bit2=Radar
    uint16_t track_age_cycles;
    uint8_t  miss_count;

    bool is_in_ego_path;    ///< collision prediction result
};

// ---------------------------------------------------------------------------
// Object list (output of perception, sent to planning)
// ---------------------------------------------------------------------------
struct ObjectList {
    TrackedObject objects[MAX_TRACKED_OBJECTS];
    uint8_t       count;
    uint32_t      timestamp_ms;
    bool          valid;
};

// ---------------------------------------------------------------------------
// Lane estimation output
// ---------------------------------------------------------------------------
struct LaneEstimate {
    float lateral_offset_m;     ///< + = ego left of centre
    float lane_width_m;
    float curvature_inv_m;      ///< 1/R
    float heading_error_rad;    ///< ego heading vs lane direction
    uint8_t quality;             ///< 0 – 100
    bool  left_marking_valid;
    bool  right_marking_valid;
    uint32_t timestamp_ms;
};

// ---------------------------------------------------------------------------
// Observation sensor mask constants
// ---------------------------------------------------------------------------
static constexpr uint8_t OBS_LIDAR  = 0x01U;
static constexpr uint8_t OBS_CAMERA = 0x02U;
static constexpr uint8_t OBS_RADAR  = 0x04U;

} // namespace perception
} // namespace adas
