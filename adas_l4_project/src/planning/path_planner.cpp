// ============================================================================
// path_planner.cpp  –  Behavioral + local path planner
// ============================================================================
#include "../../include/planning/path_planner.hpp"
#include <cstring>
#include <cmath>

namespace adas {
namespace planning {

PathPlanner::PathPlanner()
    : m_egoX(0), m_egoY(0), m_egoYaw(0), m_egoSpeed(0),
      m_targetSpeed(30.0f / 3.6f),  // 30 km/h default
      m_laneChangeCooldown(0)
{
    m_decision = {};
    m_path     = {};
    m_objects  = {};
    m_lane     = {};
    m_decision.follow_object_id = 0xFF;
}

void PathPlanner::setObjectList   (const perception::ObjectList&   o) { m_objects = o; }
void PathPlanner::setLaneEstimate (const perception::LaneEstimate& l) { m_lane    = l; }
void PathPlanner::setTargetSpeed  (float s_mps)                       { m_targetSpeed = s_mps; }

void PathPlanner::setEgoPose(float x, float y, float yaw, float speed) {
    m_egoX = x; m_egoY = y; m_egoYaw = yaw; m_egoSpeed = speed;
}

void PathPlanner::plan() {
    if (m_laneChangeCooldown > 0) m_laneChangeCooldown--;
    decideBehavior();
    generatePath();
}

// ---------------------------------------------------------------------------
void PathPlanner::decideBehavior() {
    m_decision.state             = BehaviorState::LANE_FOLLOWING;
    m_decision.target_lane_offset= 0;
    m_decision.target_speed_mps  = m_targetSpeed;
    m_decision.follow_object_id  = 0xFF;
    m_decision.must_stop         = false;
    m_decision.emergency_stop    = false;

    // Check all confirmed objects
    for (uint8_t i = 0; i < m_objects.count; ++i) {
        const auto& obj = m_objects.objects[i];

        // Emergency: object in path with very low TTC
        if (obj.is_in_ego_path && obj.ttc_s > 0.0f && obj.ttc_s < 1.5f) {
            m_decision.state          = BehaviorState::EMERGENCY_STOP;
            m_decision.emergency_stop = true;
            m_decision.must_stop      = true;
            return;
        }

        // Follow vehicle ahead (ACC)
        if (obj.is_in_ego_path && obj.x_m > 0.0f && obj.x_m < 80.0f) {
            m_decision.state           = BehaviorState::FOLLOW_VEHICLE;
            m_decision.follow_object_id= obj.id;
            m_decision.target_speed_mps= computeFollowSpeed();
        }
    }

    // Pedestrian crossing detection
    for (uint8_t i = 0; i < m_objects.count; ++i) {
        const auto& obj = m_objects.objects[i];
        if (obj.object_class == ObjectClass::PEDESTRIAN &&
            obj.x_m > 0.0f && obj.x_m < 20.0f &&
            fabsf(obj.y_m) < 5.0f) {
            m_decision.state           = BehaviorState::YIELD;
            m_decision.must_stop       = (obj.x_m < 10.0f);
            m_decision.target_speed_mps= 0.0f;
            return;
        }
    }
}

float PathPlanner::computeFollowSpeed() const {
    // Find closest object ahead in path
    float minRange = 999.0f;
    float leadSpeed = 0.0f;
    for (uint8_t i = 0; i < m_objects.count; ++i) {
        const auto& obj = m_objects.objects[i];
        if (obj.is_in_ego_path && obj.x_m > 0.0f && obj.x_m < minRange) {
            minRange  = obj.x_m;
            leadSpeed = m_egoSpeed + obj.vx_mps;  // absolute speed
            if (leadSpeed < 0) leadSpeed = 0;
        }
    }
    // Desired following distance
    float desired_gap = 3.0f + m_egoSpeed * 1.5f;
    float gap_error   = minRange - desired_gap;
    float cmd_speed   = leadSpeed + 0.5f * gap_error;
    if (cmd_speed < 0) cmd_speed = 0;
    if (cmd_speed > m_targetSpeed) cmd_speed = m_targetSpeed;
    return cmd_speed;
}

bool PathPlanner::isAdjacentLaneClear(int8_t direction) const {
    float lateral_target = direction * m_lane.lane_width_m;
    float safe_margin    = 3.0f;  // metres lateral clearance

    for (uint8_t i = 0; i < m_objects.count; ++i) {
        const auto& obj = m_objects.objects[i];
        float lateral_dist = fabsf(obj.y_m - lateral_target);
        if (lateral_dist < safe_margin &&
            obj.x_m > -10.0f && obj.x_m < 60.0f) {
            return false;
        }
    }
    return true;
}

// ---------------------------------------------------------------------------
// Generate a simple forward path based on lane curvature
// ---------------------------------------------------------------------------
void PathPlanner::generatePath() {
    m_path.count        = 0;
    m_path.valid        = true;
    m_path.behavior     = m_decision.state;

    // Generate 100 points at 0.5m intervals (50m horizon)
    float cumX = m_egoX;
    float cumY = m_egoY;
    float heading = m_egoYaw;
    float curvature = m_lane.curvature_inv_m;

    float lateral_target = 0.0f;
    if (m_decision.state == BehaviorState::LANE_CHANGE_LEFT)  lateral_target = -m_lane.lane_width_m;
    if (m_decision.state == BehaviorState::LANE_CHANGE_RIGHT) lateral_target =  m_lane.lane_width_m;

    static constexpr uint8_t PATH_COUNT = 100U;
    static constexpr float   DS         = 0.5f;

    for (uint8_t i = 0; i < PATH_COUNT && m_path.count < MAX_PATH_POINTS; ++i) {
        PathPoint& pp = m_path.points[m_path.count++];
        pp.x_m          = cumX;
        pp.y_m          = cumY + lateral_target * (static_cast<float>(i) / PATH_COUNT);
        pp.heading_rad  = heading;
        pp.curvature    = curvature;
        pp.speed_limit_mps = m_decision.target_speed_mps;

        cumX += DS * cosf(heading);
        cumY += DS * sinf(heading);
        heading += curvature * DS;
    }
}

} // namespace planning
} // namespace adas
