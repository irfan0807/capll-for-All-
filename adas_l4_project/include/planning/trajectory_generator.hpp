#pragma once
// ============================================================================
// trajectory_generator.hpp  –  Jerk-minimal trajectory generation (Frenet)
// ============================================================================
#include "route_types.hpp"
#include "../perception/perception_types.hpp"

namespace adas {
namespace planning {

class TrajectoryGenerator {
public:
    TrajectoryGenerator();

    void setLocalPath(const LocalPath& path);
    void setEgoState (float x_m, float y_m, float yaw_rad,
                      float speed_mps, float accel_mps2);
    void setObjectList(const perception::ObjectList& objects);

    /// Generate trajectory candidates and pick the best (call at 10 Hz)
    void generate();

    const Trajectory& getTrajectory() const { return m_best; }

private:
    static constexpr uint8_t NUM_LATERAL_TARGETS = 5U;
    static constexpr uint8_t NUM_TIME_HORIZONS   = 3U;
    static constexpr float   MAX_LAT_ACCEL_MPS2  = 3.0f;
    static constexpr float   MAX_DECEL_MPS2      = 8.0f;

    /// Solve 5th-order polynomial lateral trajectory
    void solveQuintic(float d0, float dv0, float da0,
                      float df, float dvf, float daf,
                      float T, float coeffs[6]) const;

    /// Evaluate polynomial at time t
    float evalPoly(const float c[6], float t) const;
    float evalPolyD1(const float c[6], float t) const;  // 1st derivative
    float evalPolyD2(const float c[6], float t) const;  // 2nd derivative

    bool isCollisionFree(const Trajectory& traj) const;
    float computeCost  (const Trajectory& traj) const;

    Trajectory generateCandidate(float d_target_m, float T_s) const;

    LocalPath   m_path;
    Trajectory  m_best;
    float       m_egoX, m_egoY, m_egoYaw;
    float       m_egoSpeed, m_egoAccel;
    perception::ObjectList m_objects;
};

} // namespace planning
} // namespace adas
