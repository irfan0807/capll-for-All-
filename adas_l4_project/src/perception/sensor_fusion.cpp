// ============================================================================
// sensor_fusion.cpp  –  Extended Kalman Filter multi-sensor fusion
// ============================================================================
#include "../../include/perception/sensor_fusion.hpp"
#include <cstring>
#include <cmath>

namespace adas {
namespace perception {

// ---------------------------------------------------------------------------
SensorFusion::SensorFusion()
    : m_trackCount(0), m_nextId(1)
{
    memset(m_states,  0, sizeof(m_states));
    memset(m_tracks,  0, sizeof(m_tracks));
    m_objectList = {};
    m_lidarScan  = {};
    m_radarScan  = {};
    m_cameraFrame= {};
}

void SensorFusion::setLidarScan  (const LidarScan&  scan)  { m_lidarScan   = scan; }
void SensorFusion::setRadarScan  (const RadarScan&  scan)  { m_radarScan   = scan; }
void SensorFusion::setCameraFrame(const CameraFrame& frame) { m_cameraFrame = frame; }

// ---------------------------------------------------------------------------
// Build 8×8 state transition matrix F
// ---------------------------------------------------------------------------
void SensorFusion::buildF(float F[8][8], float dt) const {
    // Zero initialise
    for (int i = 0; i < 8; i++)
        for (int j = 0; j < 8; j++)
            F[i][j] = (i == j) ? 1.0f : 0.0f;

    float dt2 = 0.5f * dt * dt;
    // px += vx*dt + ax*dt²/2
    F[0][2] = dt;  F[0][4] = dt2;
    // py += vy*dt + ay*dt²/2
    F[1][3] = dt;  F[1][5] = dt2;
    // vx += ax*dt
    F[2][4] = dt;
    // vy += ay*dt
    F[3][5] = dt;
    // yaw += yaw_rate*dt
    F[6][7] = dt;
}

void SensorFusion::matMul8(const float A[8][8], const float B[8][8], float C[8][8]) const {
    for (int i = 0; i < 8; i++) {
        for (int j = 0; j < 8; j++) {
            float sum = 0;
            for (int k = 0; k < 8; k++) sum += A[i][k] * B[k][j];
            C[i][j] = sum;
        }
    }
}

void SensorFusion::matAdd8(const float A[8][8], const float B[8][8], float C[8][8]) const {
    for (int i = 0; i < 8; i++)
        for (int j = 0; j < 8; j++)
            C[i][j] = A[i][j] + B[i][j];
}

void SensorFusion::transposeF(const float F[8][8], float Ft[8][8]) const {
    for (int i = 0; i < 8; i++)
        for (int j = 0; j < 8; j++)
            Ft[j][i] = F[i][j];
}

// ---------------------------------------------------------------------------
// Predict step: x_pred = F*x; P_pred = F*P*F^T + Q
// ---------------------------------------------------------------------------
void SensorFusion::predictAll(float dt_s) {
    float F[8][8], Ft[8][8], FP[8][8], FPFt[8][8];
    buildF(F, dt_s);
    transposeF(F, Ft);

    float sigma2 = SIGMA_PROCESS * SIGMA_PROCESS;

    for (uint8_t t = 0; t < m_trackCount; ++t) {
        KFState& s = m_states[t];
        if (!s.valid) continue;

        // x = F * x
        float xnew[8] = {};
        for (int i = 0; i < 8; i++) {
            for (int k = 0; k < 8; k++) xnew[i] += F[i][k] * s.x[k];
        }
        for (int i = 0; i < 8; i++) s.x[i] = xnew[i];

        // P = F*P*Ft + Q
        matMul8(F, s.P, FP);
        matMul8(FP, Ft, FPFt);

        // Simple additive process noise (diagonal, only on velocity and accel)
        for (int i = 0; i < 8; i++) s.P[i][i] = FPFt[i][i];
        s.P[2][2] += sigma2;  // vx
        s.P[3][3] += sigma2;  // vy
        s.P[4][4] += sigma2 * dt_s;  // ax
        s.P[5][5] += sigma2 * dt_s;  // ay
    }
}

// ---------------------------------------------------------------------------
// Initialise new track at (px, py)
// ---------------------------------------------------------------------------
KFState SensorFusion::initTrack(float px, float py) const {
    KFState s;
    memset(&s, 0, sizeof(s));
    s.valid  = true;
    s.x[0]   = px;
    s.x[1]   = py;
    // Initial uncertainty
    s.P[0][0] = 1.0f;   // px
    s.P[1][1] = 1.0f;   // py
    s.P[2][2] = 25.0f;  // vx
    s.P[3][3] = 25.0f;  // vy
    s.P[4][4] = 4.0f;   // ax
    s.P[5][5] = 4.0f;   // ay
    s.P[6][6] = 0.1f;   // yaw
    s.P[7][7] = 0.1f;   // yaw_rate
    return s;
}

// ---------------------------------------------------------------------------
// Mahalanobis distance for 2D position (obs_x, obs_y) vs state
// ---------------------------------------------------------------------------
float SensorFusion::mahalanobisDistance(const KFState& s,
                                         float ox, float oy) const {
    float dx = ox - s.x[0];
    float dy = oy - s.x[1];
    float S00 = s.P[0][0] + 0.25f;  // measurement noise R ~0.25 m²
    float S11 = s.P[1][1] + 0.25f;
    // Off-diagonals ignored for speed (diagonal approx)
    return (dx * dx / S00) + (dy * dy / S11);
}

// ---------------------------------------------------------------------------
// Simplified EKF update: H = [[1,0,...]], R = small measurement noise
// ---------------------------------------------------------------------------
static void kfUpdate2D(KFState& s, float ox, float oy,
                        float R_noise = 0.25f) {
    // Innovation
    float y0 = ox - s.x[0];
    float y1 = oy - s.x[1];

    // S = H*P*H^T + R  (for rows 0 and 1 only)
    float S00 = s.P[0][0] + R_noise;
    float S11 = s.P[1][1] + R_noise;

    // Kalman gain K = P * H^T * S^-1  (only 2 columns)
    float K0[8], K1[8];
    for (int i = 0; i < 8; i++) {
        K0[i] = s.P[i][0] / S00;
        K1[i] = s.P[i][1] / S11;
    }

    // State update
    for (int i = 0; i < 8; i++) {
        s.x[i] += K0[i] * y0 + K1[i] * y1;
    }

    // Covariance update P = (I - K*H) * P
    for (int i = 0; i < 8; i++) {
        for (int j = 0; j < 8; j++) {
            s.P[i][j] -= K0[i] * s.P[0][j] + K1[i] * s.P[1][j];
        }
    }
}

// ---------------------------------------------------------------------------
// Associate radar/camera/LiDAR measurements with existing tracks
// Very simplified: process known "clusters" from radar object list
// ---------------------------------------------------------------------------
void SensorFusion::associateAndUpdate() {
    // Mark all tracks as not updated this cycle
    bool updated[MAX_TRACKED_OBJECTS] = {};

    // --- Radar association (direct object list) ---
    for (uint8_t r = 0; r < m_radarScan.count; ++r) {
        const RadarObject& ro = m_radarScan.objects[r];
        // Convert polar → Cartesian
        float rad = ro.azimuth_deg * 3.14159265f / 180.0f;
        float ox  = ro.range_m * cosf(rad);
        float oy  = ro.range_m * sinf(rad);

        float bestDist = GATE_THRESHOLD;
        int   bestIdx  = -1;
        for (uint8_t t = 0; t < m_trackCount; ++t) {
            if (!m_states[t].valid) continue;
            float d = mahalanobisDistance(m_states[t], ox, oy);
            if (d < bestDist) { bestDist = d; bestIdx = t; }
        }

        if (bestIdx >= 0) {
            // Update existing track
            kfUpdate2D(m_states[bestIdx], ox, oy, 0.5f);
            // Also update velocity from radar Doppler
            m_states[bestIdx].x[2] = ro.range_rate_mps * cosf(rad);
            m_states[bestIdx].x[3] = ro.range_rate_mps * sinf(rad);
            m_tracks[bestIdx].observed_by |= OBS_RADAR;
            updated[bestIdx] = true;
        } else if (m_trackCount < MAX_TRACKED_OBJECTS) {
            // Create new track from radar
            uint8_t idx = m_trackCount++;
            m_states[idx]              = initTrack(ox, oy);
            m_tracks[idx]              = {};
            m_tracks[idx].id           = m_nextId++;
            m_tracks[idx].state        = TrackState::NEW_CANDIDATE;
            m_tracks[idx].x_m         = ox;
            m_tracks[idx].y_m         = oy;
            m_tracks[idx].observed_by  = OBS_RADAR;
            updated[idx]               = true;
        }
    }

    // --- Camera detection association ---
    for (uint8_t c = 0; c < m_cameraFrame.count; ++c) {
        const CameraDetection& cd = m_cameraFrame.detections[c];
        float ox = cd.x_m, oy = cd.y_m;

        float bestDist = GATE_THRESHOLD;
        int   bestIdx  = -1;
        for (uint8_t t = 0; t < m_trackCount; ++t) {
            if (!m_states[t].valid) continue;
            float d = mahalanobisDistance(m_states[t], ox, oy);
            if (d < bestDist) { bestDist = d; bestIdx = t; }
        }

        if (bestIdx >= 0) {
            kfUpdate2D(m_states[bestIdx], ox, oy, 1.0f);
            m_tracks[bestIdx].object_class = cd.object_class;
            m_tracks[bestIdx].observed_by |= OBS_CAMERA;
            updated[bestIdx] = true;
        } else if (m_trackCount < MAX_TRACKED_OBJECTS) {
            uint8_t idx = m_trackCount++;
            m_states[idx]              = initTrack(ox, oy);
            m_tracks[idx]              = {};
            m_tracks[idx].id           = m_nextId++;
            m_tracks[idx].state        = TrackState::NEW_CANDIDATE;
            m_tracks[idx].x_m         = ox;
            m_tracks[idx].y_m         = oy;
            m_tracks[idx].object_class = cd.object_class;
            m_tracks[idx].observed_by  = OBS_CAMERA;
            updated[idx]               = true;
        }
    }

    // Increment miss counter for non-updated tracks
    for (uint8_t t = 0; t < m_trackCount; ++t) {
        if (!updated[t]) {
            m_tracks[t].miss_count++;
        }
    }
}

// ---------------------------------------------------------------------------
// Track lifecycle management
// ---------------------------------------------------------------------------
void SensorFusion::manageTrackLifecycle() {
    for (uint8_t t = 0; t < m_trackCount; ++t) {
        TrackedObject& tr = m_tracks[t];

        tr.track_age_cycles++;

        // Copy state estimate to track object
        const KFState& s = m_states[t];
        tr.x_m          = s.x[0];
        tr.y_m          = s.x[1];
        tr.vx_mps       = s.x[2];
        tr.vy_mps       = s.x[3];
        tr.ax_mps2      = s.x[4];
        tr.ay_mps2      = s.x[5];
        tr.yaw_rad      = s.x[6];
        tr.yaw_rate_rps = s.x[7];

        // State machine
        switch (tr.state) {
            case TrackState::NEW_CANDIDATE:
                if (tr.track_age_cycles >= 2) tr.state = TrackState::PROBABLE;
                break;
            case TrackState::PROBABLE:
                if (tr.track_age_cycles >= 5) tr.state = TrackState::CONFIRMED;
                break;
            case TrackState::CONFIRMED:
                if (tr.miss_count >= 5) tr.state = TrackState::LOST;
                break;
            case TrackState::LOST:
                // Will be removed below
                break;
        }
    }

    // Compact array – remove LOST tracks
    uint8_t write = 0;
    for (uint8_t t = 0; t < m_trackCount; ++t) {
        if (m_tracks[t].state != TrackState::LOST) {
            if (write != t) {
                m_tracks[write] = m_tracks[t];
                m_states[write] = m_states[t];
            }
            write++;
        }
    }
    m_trackCount = write;
}

// ---------------------------------------------------------------------------
// TTC computation for confirmed tracks
// ---------------------------------------------------------------------------
void SensorFusion::computeTTC(float ego_speed_mps) {
    for (uint8_t t = 0; t < m_trackCount; ++t) {
        TrackedObject& tr = m_tracks[t];
        if (tr.state != TrackState::CONFIRMED) {
            tr.ttc_s = INVALID_FLOAT;
            continue;
        }

        float rel_vx = tr.vx_mps - ego_speed_mps;
        float range  = tr.x_m;  // forward distance

        tr.is_in_ego_path = (fabsf(tr.y_m) < 1.5f && tr.x_m > 0.0f);

        if (rel_vx < -0.1f && range > 0.0f && tr.is_in_ego_path) {
            tr.ttc_s = -range / rel_vx;
        } else {
            tr.ttc_s = INVALID_FLOAT;
        }
    }

    // Rebuild object list so TTC values are visible to callers
    m_objectList.count = 0;
    m_objectList.valid = true;
    for (uint8_t t = 0; t < m_trackCount; ++t) {
        if (m_tracks[t].state == TrackState::CONFIRMED &&
            m_objectList.count < MAX_TRACKED_OBJECTS) {
            m_objectList.objects[m_objectList.count++] = m_tracks[t];
        }
    }
}

// ---------------------------------------------------------------------------
// Main process
// ---------------------------------------------------------------------------
void SensorFusion::process(float dt_s) {
    predictAll(dt_s > 0.0f ? dt_s : DT_DEFAULT);
    associateAndUpdate();
    manageTrackLifecycle();

    // Build output object list (confirmed tracks only)
    m_objectList.count = 0;
    m_objectList.valid = true;
    for (uint8_t t = 0; t < m_trackCount; ++t) {
        if (m_tracks[t].state == TrackState::CONFIRMED &&
            m_objectList.count < MAX_TRACKED_OBJECTS) {
            m_objectList.objects[m_objectList.count++] = m_tracks[t];
        }
    }
}

} // namespace perception
} // namespace adas
