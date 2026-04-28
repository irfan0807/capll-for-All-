#pragma once
// ============================================================================
// route_types.hpp  –  Planning layer data structures
// ============================================================================
#include "../sensors/sensor_types.hpp"

namespace adas {
namespace planning {

static constexpr uint8_t  MAX_PATH_POINTS     = 200U;
static constexpr uint8_t  MAX_TRAJECTORY_PTS  = 50U;
static constexpr float    INVALID_SPEED       = -1.0f;

// ---------------------------------------------------------------------------
// Driving behaviour decisions
// ---------------------------------------------------------------------------
enum class BehaviorState : uint8_t {
    LANE_FOLLOWING    = 0,
    LANE_CHANGE_LEFT  = 1,
    LANE_CHANGE_RIGHT = 2,
    TURN_LEFT         = 3,
    TURN_RIGHT        = 4,
    YIELD             = 5,
    FOLLOW_VEHICLE    = 6,
    EMERGENCY_STOP    = 7,
    MINIMAL_RISK_COND = 8,
    PULL_OVER         = 9
};

// ---------------------------------------------------------------------------
// Path point (local reference path)
// ---------------------------------------------------------------------------
struct PathPoint {
    float x_m;          ///< vehicle frame forward
    float y_m;          ///< vehicle frame lateral
    float heading_rad;  ///< tangent direction
    float curvature;    ///< 1/m (positive = turn left)
    float speed_limit_mps;
};

// ---------------------------------------------------------------------------
// Local reference path (from planner)
// ---------------------------------------------------------------------------
struct LocalPath {
    PathPoint points[MAX_PATH_POINTS];
    uint8_t   count;
    bool      valid;
    uint32_t  timestamp_ms;
    BehaviorState behavior;
};

// ---------------------------------------------------------------------------
// Trajectory point (planned motion with time stamps)
// ---------------------------------------------------------------------------
struct TrajectoryPoint {
    float x_m;
    float y_m;
    float heading_rad;
    float speed_mps;
    float accel_mps2;
    float steering_rad;
    float time_s;       ///< time relative to now (0 = present)
};

// ---------------------------------------------------------------------------
// Planned trajectory (sent to control layer)
// ---------------------------------------------------------------------------
struct Trajectory {
    TrajectoryPoint pts[MAX_TRAJECTORY_PTS];
    uint8_t  count;
    bool     valid;
    bool     collision_free;
    float    total_cost;
    uint32_t timestamp_ms;
};

// ---------------------------------------------------------------------------
// Behavior decision output
// ---------------------------------------------------------------------------
struct BehaviorDecision {
    BehaviorState  state;
    int8_t         target_lane_offset; ///< 0 = current, -1 = left, +1 = right
    float          target_speed_mps;
    uint8_t        follow_object_id;   ///< 0xFF = no object
    bool           must_stop;
    bool           emergency_stop;
};

} // namespace planning
} // namespace adas
