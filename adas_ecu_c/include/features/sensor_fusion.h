/**
 * @file  sensor_fusion.h
 * @brief World model — fuses radar + camera + vehicle state CAN inputs.
 *
 * C pattern: all world-model data is in a single struct (WorldModel_t).
 * The fusion module owns one static instance; callers access via pointer.
 */

#ifndef SENSOR_FUSION_H
#define SENSOR_FUSION_H

#include "hal/hal_types.h"
#include "drivers/can_messages.h"

/* ── Sub-models ──────────────────────────────────────────────────────────── */

typedef enum {
    TARGET_TYPE_UNKNOWN     = 0,
    TARGET_TYPE_CAR         = 1,
    TARGET_TYPE_BIKE        = 2,
    TARGET_TYPE_PEDESTRIAN  = 3
} TargetType_t;

typedef struct {
    float        distance_m;
    float        rel_vel_mps;
    float        ttc_s;
    float        lateral_m;
    TargetType_t type;
    bool         valid;
    bool         confirmed;  /* Radar + camera both agree */
} FrontTarget_t;

typedef struct {
    float   left_offset_m;
    float   right_offset_m;
    uint8_t left_quality;
    uint8_t right_quality;
    bool    ldw_left;
    bool    ldw_right;
} LaneModel_t;

typedef struct {
    bool  left_occupied;
    bool  right_occupied;
    float left_dist_m;
    float right_dist_m;
} BlindZoneModel_t;

typedef struct {
    uint8_t fl_cm, fr_cm, rl_cm, rr_cm;
} ParkingModel_t;

typedef struct {
    Kph_t     speed_kph;
    Mps_t     speed_mps;
    Degrees_t steer_angle_deg;
    Pct_t     brake_pct;
    Pct_t     accel_pct;
    Gear_t    gear;
    bool      turn_left;
    bool      turn_right;
    float     hill_gradient;    /* estimated grade 0.0–1.0 */
} VehicleState_t;

/* ── World model aggregate ──────────────────────────────────────────────── */
typedef struct {
    FrontTarget_t    front_target;
    LaneModel_t      lane;
    BlindZoneModel_t blind_zone;
    ParkingModel_t   parking;
    VehicleState_t   vehicle;
} WorldModel_t;

/* ── API ─────────────────────────────────────────────────────────────────── */

/* Initialise fusion module (call once). */
void fusion_init  (void);

/* Update world model from latest decoded CAN messages (call every 20ms). */
void fusion_update(const MsgRadarObject_t   *radar,
                   const MsgCameraLane_t    *camera,
                   const MsgBSDRadar_t      *bsd,
                   const MsgUltrasonic_t    *park,
                   const MsgVehicleSpeed_t  *speed,
                   const MsgSteeringAngle_t *steer,
                   const MsgDriverInputs_t  *driver,
                   const MsgGearShifter_t   *gear);

/* Read-only access to world model */
const WorldModel_t *fusion_get_world(void);

#endif /* SENSOR_FUSION_H */
