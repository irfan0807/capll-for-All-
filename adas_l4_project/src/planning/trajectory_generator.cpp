// ============================================================================
// trajectory_generator.cpp  –  Jerk-minimal 5th-order polynomial trajectories
// ============================================================================
#include "../../include/planning/trajectory_generator.hpp"
#include <cstring>
#include <cmath>

namespace adas {
namespace planning {

TrajectoryGenerator::TrajectoryGenerator()
    : m_egoX(0), m_egoY(0), m_egoYaw(0),
      m_egoSpeed(0), m_egoAccel(0)
{
    m_path    = {};
    m_best    = {};
    m_objects = {};
}

void TrajectoryGenerator::setLocalPath(const LocalPath& p)              { m_path  = p; }
void TrajectoryGenerator::setEgoState (float x, float y, float yaw,
                                        float spd, float acc) {
    m_egoX = x; m_egoY = y; m_egoYaw = yaw;
    m_egoSpeed = spd; m_egoAccel = acc;
}
void TrajectoryGenerator::setObjectList(const perception::ObjectList& o) { m_objects = o; }

// ---------------------------------------------------------------------------
// Solve quintic (5th-order) polynomial: d(t) = c0+c1*t+...+c5*t^5
// Boundary conditions: d(0)=d0, d'(0)=dv0, d''(0)=da0
//                      d(T)=df,  d'(T)=dvf,  d''(T)=daf
// ---------------------------------------------------------------------------
void TrajectoryGenerator::solveQuintic(float d0, float dv0, float da0,
                                        float df, float dvf, float daf,
                                        float T, float coeffs[6]) const {
    coeffs[0] = d0;
    coeffs[1] = dv0;
    coeffs[2] = 0.5f * da0;

    float T2 = T * T, T3 = T2 * T, T4 = T3 * T, T5 = T4 * T;

    // Remaining 3 coefficients from 3×3 system
    float a3 = df - d0 - dv0 * T - 0.5f * da0 * T2;
    float a4 = dvf - dv0 - da0 * T;
    float a5 = daf - da0;

    // Solve:
    // [T3  T4  T5 ] [c3]   [a3]
    // [3T2 4T3 5T4] [c4] = [a4]
    // [6T  12T2 20T3][c5]   [a5]
    float inv_T3 = (T3 > 1e-9f) ? 1.0f / T3 : 0.0f;

    // Simplified closed-form for zero terminal accel/vel (daf=dvf=0):
    coeffs[3] = (10.0f * a3 - 4.0f * a4 * T + 0.5f * a5 * T2) * inv_T3;
    coeffs[4] = (-15.0f * a3 * inv_T3 + 7.0f * a4 / T4 - a5 / (2.0f * T3)) / T;
    coeffs[5] = (6.0f * a3 * inv_T3 - 3.0f * a4 / T4 + 0.5f * a5 / T5);
}

float TrajectoryGenerator::evalPoly(const float c[6], float t) const {
    return c[0] + t*(c[1] + t*(c[2] + t*(c[3] + t*(c[4] + t*c[5]))));
}

float TrajectoryGenerator::evalPolyD1(const float c[6], float t) const {
    return c[1] + t*(2.0f*c[2] + t*(3.0f*c[3] + t*(4.0f*c[4] + t*5.0f*c[5])));
}

float TrajectoryGenerator::evalPolyD2(const float c[6], float t) const {
    return 2.0f*c[2] + t*(6.0f*c[3] + t*(12.0f*c[4] + t*20.0f*c[5]));
}

bool TrajectoryGenerator::isCollisionFree(const Trajectory& traj) const {
    static constexpr float EGO_HALF_W = 1.0f;  // metres
    static constexpr float EGO_HALF_L = 2.5f;

    for (uint8_t pi = 0; pi < traj.count; ++pi) {
        float t  = traj.pts[pi].time_s;
        float ex = traj.pts[pi].x_m;
        float ey = traj.pts[pi].y_m;

        for (uint8_t oi = 0; oi < m_objects.count; ++oi) {
            const auto& obj = m_objects.objects[oi];
            // Predict object position at time t
            float ox = obj.x_m + obj.vx_mps * t;
            float oy = obj.y_m + obj.vy_mps * t;
            float hw = obj.width_m  / 2.0f + EGO_HALF_W + 0.3f;
            float hl = obj.length_m / 2.0f + EGO_HALF_L + 0.3f;
            if (fabsf(ex - ox) < hl && fabsf(ey - oy) < hw) return false;
        }
    }
    return true;
}

float TrajectoryGenerator::computeCost(const Trajectory& traj) const {
    float cost = 0;
    for (uint8_t i = 1; i < traj.count; ++i) {
        float dt = traj.pts[i].time_s - traj.pts[i-1].time_s;
        // Lateral jerk
        float dy1 = traj.pts[i].y_m - traj.pts[i-1].y_m;
        cost += 0.5f * dy1 * dy1 / (dt * dt);
        // Speed deviation from reference
        float ref_spd = (m_path.count > 0) ? m_path.points[0].speed_limit_mps : 10.0f;
        float sv = traj.pts[i].speed_mps - ref_spd;
        cost += 0.2f * sv * sv;
    }
    return cost;
}

Trajectory TrajectoryGenerator::generateCandidate(float d_target_m, float T_s) const {
    Trajectory traj;
    traj.count = 0;
    traj.valid = true;
    traj.collision_free = false;

    float c[6];
    solveQuintic(0.0f, 0.0f, 0.0f,   // start: at lane centre, zero lat vel/acc
                 d_target_m, 0.0f, 0.0f,  // end: at target with zero lat vel/acc
                 T_s, c);

    static constexpr uint8_t STEPS = 20U;
    float dt = T_s / STEPS;

    for (uint8_t s = 0; s <= STEPS && traj.count < MAX_TRAJECTORY_PTS; ++s) {
        float t = s * dt;
        TrajectoryPoint& pt = traj.pts[traj.count++];
        pt.time_s    = t;
        // Global position: forward = ego frame X + path curvature
        pt.x_m       = m_egoX + m_egoSpeed * t;
        pt.y_m       = m_egoY + evalPoly(c, t);
        pt.heading_rad = m_egoYaw + evalPolyD1(c, t);
        pt.speed_mps = m_egoSpeed;  // simplified constant speed longitudinal
        pt.accel_mps2= 0.0f;
        pt.steering_rad = 0.0f;
    }

    traj.total_cost = computeCost(traj);
    return traj;
}

void TrajectoryGenerator::generate() {
    if (!m_path.valid || m_path.count == 0) {
        m_best.valid = false;
        return;
    }

    static const float LATERAL_TARGETS[NUM_LATERAL_TARGETS] =
        {-1.5f, -0.75f, 0.0f, 0.75f, 1.5f};
    static const float TIME_HORIZONS[NUM_TIME_HORIZONS] =
        {2.0f, 3.0f, 5.0f};

    float bestCost = 1e10f;
    bool  found    = false;

    for (uint8_t li = 0; li < NUM_LATERAL_TARGETS; ++li) {
        for (uint8_t ti = 0; ti < NUM_TIME_HORIZONS; ++ti) {
            Trajectory cand = generateCandidate(LATERAL_TARGETS[li],
                                                 TIME_HORIZONS[ti]);
            cand.collision_free = isCollisionFree(cand);
            if (!cand.collision_free) continue;

            if (cand.total_cost < bestCost) {
                bestCost = cand.total_cost;
                m_best   = cand;
                found    = true;
            }
        }
    }

    m_best.valid = found;
}

} // namespace planning
} // namespace adas
