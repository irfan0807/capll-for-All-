#pragma once
// ============================================================================
// sensor_types.hpp  –  Common data types shared across all sensor modules
// ADAS Level 4 Project
// ============================================================================

#include <cstdint>
#include <cmath>

namespace adas {

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
static constexpr uint32_t MAX_LIDAR_POINTS   = 150000U;
static constexpr uint8_t  MAX_RADAR_OBJECTS  = 64U;
static constexpr uint8_t  MAX_CAMERA_OBJECTS = 32U;
static constexpr float    INVALID_FLOAT      = -9999.0f;

// ---------------------------------------------------------------------------
// Coordinate frame: ISO 8855 (SAE J670)
//   X = forward, Y = left, Z = up  (right-hand)
// ---------------------------------------------------------------------------
struct Point3D {
    float x;   ///< metres, forward
    float y;   ///< metres, left
    float z;   ///< metres, up
};

struct Pose2D {
    float x;     ///< metres
    float y;     ///< metres
    float yaw;   ///< radians, counter-clockwise positive
};

struct BoundingBox3D {
    Point3D centre;
    float   length;  ///< x-axis extent (metres)
    float   width;   ///< y-axis extent (metres)
    float   height;  ///< z-axis extent (metres)
    float   yaw;     ///< heading radians
};

// ---------------------------------------------------------------------------
// Sensor health status
// ---------------------------------------------------------------------------
enum class SensorHealth : uint8_t {
    OK       = 0,
    DEGRADED = 1,
    FAILED   = 2,
    INIT     = 3
};

// ---------------------------------------------------------------------------
// Object classification
// ---------------------------------------------------------------------------
enum class ObjectClass : uint8_t {
    UNKNOWN     = 0,
    CAR         = 1,
    TRUCK       = 2,
    BUS         = 3,
    MOTORCYCLE  = 4,
    BICYCLE     = 5,
    PEDESTRIAN  = 6,
    STATIC_OBS  = 7,
    ANIMAL      = 8
};

// ---------------------------------------------------------------------------
// LiDAR point
// ---------------------------------------------------------------------------
struct LidarPoint {
    float   x;           ///< metres, vehicle frame
    float   y;           ///< metres
    float   z;           ///< metres
    float   intensity;   ///< 0.0 – 1.0
    uint8_t ring;        ///< beam index
};

// ---------------------------------------------------------------------------
// LiDAR scan (one full rotation)
// ---------------------------------------------------------------------------
struct LidarScan {
    LidarPoint points[MAX_LIDAR_POINTS];
    uint32_t   count;
    uint32_t   timestamp_ms;
    SensorHealth health;
};

// ---------------------------------------------------------------------------
// Radar object
// ---------------------------------------------------------------------------
struct RadarObject {
    uint8_t  id;
    float    range_m;          ///< radial distance
    float    azimuth_deg;      ///< horizontal angle (+ = left)
    float    elevation_deg;    ///< vertical angle
    float    range_rate_mps;   ///< negative = approaching
    float    rcs_dBsm;         ///< radar cross section
    uint8_t  confidence;       ///< 0 – 100
    bool     is_moving;
};

// ---------------------------------------------------------------------------
// Radar scan (one measurement cycle)
// ---------------------------------------------------------------------------
struct RadarScan {
    RadarObject objects[MAX_RADAR_OBJECTS];
    uint8_t     count;
    uint32_t    timestamp_ms;
    SensorHealth health;
};

// ---------------------------------------------------------------------------
// Camera detection (2D bounding box in image → projected to ground plane)
// ---------------------------------------------------------------------------
struct CameraDetection {
    uint8_t     id;
    ObjectClass object_class;
    float       confidence;   ///< 0.0 – 1.0
    // Projected to ground plane (mono camera):
    float       x_m;          ///< forward distance, metres
    float       y_m;          ///< lateral offset, metres (+ = left)
    float       width_m;
    float       length_m;
    // Image-space bounding box:
    uint16_t    img_x;        ///< pixels
    uint16_t    img_y;
    uint16_t    img_w;
    uint16_t    img_h;
};

// ---------------------------------------------------------------------------
// Camera frame
// ---------------------------------------------------------------------------
struct CameraFrame {
    CameraDetection detections[MAX_CAMERA_OBJECTS];
    uint8_t  count;
    uint32_t timestamp_ms;
    // Lane data
    float    left_lane_offset_m;    ///< lateral offset to left lane marking
    float    right_lane_offset_m;   ///< lateral offset to right lane marking
    float    lane_width_m;
    float    lane_curvature_inv_m;  ///< 1/curve_radius
    uint8_t  lane_quality;          ///< 0 – 100
    SensorHealth health;
};

// ---------------------------------------------------------------------------
// IMU data
// ---------------------------------------------------------------------------
struct ImuData {
    float ax;      ///< acceleration X, m/s²
    float ay;      ///< acceleration Y, m/s²
    float az;      ///< acceleration Z, m/s²
    float gx;      ///< angular rate X, rad/s (roll rate)
    float gy;      ///< angular rate Y, rad/s (pitch rate)
    float gz;      ///< angular rate Z, rad/s (yaw rate)
    uint32_t timestamp_ms;
    SensorHealth health;
};

// ---------------------------------------------------------------------------
// GNSS fix
// ---------------------------------------------------------------------------
struct GnssFix {
    double   latitude;     ///< degrees
    double   longitude;    ///< degrees
    float    altitude_m;
    float    speed_mps;
    float    heading_deg;
    float    accuracy_m;   ///< horizontal accuracy (1-sigma)
    uint8_t  num_sats;
    bool     rtk_active;
    uint32_t timestamp_ms;
    SensorHealth health;
};

} // namespace adas
