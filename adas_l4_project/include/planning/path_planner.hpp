#pragma once
// ============================================================================
// path_planner.hpp  –  Behavioral + local path planning
// ============================================================================
#include "route_types.hpp"
#include "../perception/perception_types.hpp"

namespace adas {
namespace planning {

class PathPlanner {
public:
    PathPlanner();

    /// Update inputs each cycle
    void setObjectList   (const perception::ObjectList&  objects);
    void setLaneEstimate (const perception::LaneEstimate& lane);
    void setEgoPose      (float x_m, float y_m, float yaw_rad,
                          float speed_mps);

    /// Set mission target speed (from speed limit / route)
    void setTargetSpeed(float speed_mps);

    /// Run behavioral + local path planning (call at 10 Hz)
    void plan();

    const LocalPath&       getPath()     const { return m_path; }
    const BehaviorDecision& getDecision() const { return m_decision; }

private:
    static constexpr float MIN_LANE_CHANGE_SPEED_MPS = 8.0f;  // ~30 km/h
    static constexpr float LANE_WIDTH_M              = 3.5f;
    static constexpr float SAFE_GAP_S                = 3.0f;  // seconds

    void decideBehavior();
    void generatePath();
    bool isAdjacentLaneClear(int8_t direction) const;
    float computeFollowSpeed() const;

    perception::ObjectList  m_objects;
    perception::LaneEstimate m_lane;
    BehaviorDecision        m_decision;
    LocalPath               m_path;

    float    m_egoX, m_egoY, m_egoYaw, m_egoSpeed;
    float    m_targetSpeed;
    uint16_t m_laneChangeCooldown;  ///< cycles before next allowed LC
};

} // namespace planning
} // namespace adas
