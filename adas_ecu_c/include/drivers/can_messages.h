/**
 * @file  can_messages.h
 * @brief CAN signal codec for all ADAS bus messages.
 *
 * Each message is a struct with a decode() or encode() function.
 * Signal math: physical = raw * factor + offset  (DBC convention)
 *
 * In C, "methods" are free functions with the struct pointer as first arg.
 * Naming: msg_xxx_decode(&msg, &frame) / msg_xxx_encode(&msg, &frame)
 */

#ifndef CAN_MESSAGES_H
#define CAN_MESSAGES_H

#include "hal/hal_types.h"
#include "drivers/can_driver.h"

/* ── Input messages (ECU ← sensors / other ECUs) ──────────────────────────*/

/* 0x100  VehicleSpeed  10ms  ← ABS */
#define MSG_VEHICLE_SPEED_ID   0x100u
#define MSG_VEHICLE_SPEED_DLC  4u
typedef struct {
    float   speed_kph;      /* factor=0.01, offset=0, range 0–327.67 km/h */
    bool    valid;
    bool    direction_fwd;
} MsgVehicleSpeed_t;
void msg_vehicle_speed_decode(MsgVehicleSpeed_t *m, const CanFrame_t *f);

/* 0x101  SteeringAngle  10ms  ← EPS */
#define MSG_STEERING_ANGLE_ID   0x101u
#define MSG_STEERING_ANGLE_DLC  4u
typedef struct {
    float   angle_deg;      /* factor=0.1, offset=-800, range -800..+800 */
    float   rate_dps;       /* degrees per second */
    bool    valid;
} MsgSteeringAngle_t;
void msg_steering_decode(MsgSteeringAngle_t *m, const CanFrame_t *f);

/* 0x102  WheelSpeeds  10ms  ← ABS */
#define MSG_WHEEL_SPEEDS_ID   0x102u
#define MSG_WHEEL_SPEEDS_DLC  8u
typedef struct {
    float   fl_kph, fr_kph, rl_kph, rr_kph;
} MsgWheelSpeeds_t;
void msg_wheel_speeds_decode(MsgWheelSpeeds_t *m, const CanFrame_t *f);

/* 0x200  RadarObject  20ms  ← Radar */
#define MSG_RADAR_OBJECT_ID   0x200u
#define MSG_RADAR_OBJECT_DLC  8u
typedef enum { RADAR_OBJ_UNKNOWN=0, RADAR_OBJ_CAR=1, RADAR_OBJ_BIKE=2, RADAR_OBJ_PEDESTRIAN=3 } RadarObjType_t;
typedef struct {
    float          distance_m;    /* factor=0.01 */
    float          rel_vel_mps;   /* factor=0.01, offset=-327.68 */
    float          lateral_m;     /* factor=0.01, offset=-327.68 */
    float          ttc_s;         /* factor=0.1  */
    bool           valid;
    RadarObjType_t obj_type;
} MsgRadarObject_t;
void msg_radar_object_decode(MsgRadarObject_t *m, const CanFrame_t *f);

/* 0x201  CameraLane  20ms  ← Camera */
#define MSG_CAMERA_LANE_ID   0x201u
#define MSG_CAMERA_LANE_DLC  8u
typedef struct {
    uint8_t left_quality;   /* 0=invalid, 1–3 = quality tier */
    uint8_t right_quality;
    float   left_offset_m;  /* factor=0.001, offset=-32.768 */
    float   right_offset_m;
    bool    left_ldw;
    bool    right_ldw;
} MsgCameraLane_t;
void msg_camera_lane_decode(MsgCameraLane_t *m, const CanFrame_t *f);

/* 0x202  BSD_Radar  20ms  ← Rear radar */
#define MSG_BSD_RADAR_ID   0x202u
#define MSG_BSD_RADAR_DLC  4u
typedef struct {
    bool    left_occupied;
    bool    right_occupied;
    float   left_dist_m;
    float   right_dist_m;
} MsgBSDRadar_t;
void msg_bsd_radar_decode(MsgBSDRadar_t *m, const CanFrame_t *f);

/* 0x203  Ultrasonic  50ms  ← Park sensors */
#define MSG_ULTRASONIC_ID   0x203u
#define MSG_ULTRASONIC_DLC  4u
typedef struct {
    uint8_t front_left_cm;
    uint8_t front_right_cm;
    uint8_t rear_left_cm;
    uint8_t rear_right_cm;
} MsgUltrasonic_t;
void msg_ultrasonic_decode(MsgUltrasonic_t *m, const CanFrame_t *f);

/* 0x400  DriverInputs  20ms  ← BCM */
#define MSG_DRIVER_INPUTS_ID   0x400u
#define MSG_DRIVER_INPUTS_DLC  5u
typedef struct {
    bool    acc_set;
    bool    acc_resume;
    bool    acc_cancel;
    bool    lka_toggle;
    uint8_t set_speed_kph;
    bool    turn_left;
    bool    turn_right;
    Pct_t   brake_pct;
    Pct_t   accel_pct;
} MsgDriverInputs_t;
void msg_driver_inputs_decode(MsgDriverInputs_t *m, const CanFrame_t *f);

/* 0x401  GearShifter  20ms  ← TCU */
#define MSG_GEAR_SHIFTER_ID   0x401u
#define MSG_GEAR_SHIFTER_DLC  2u
typedef enum { GEAR_PARK=0, GEAR_REVERSE=1, GEAR_NEUTRAL=2, GEAR_DRIVE=3 } Gear_t;
typedef struct {
    Gear_t  gear;
    bool    valid;
} MsgGearShifter_t;
void msg_gear_shifter_decode(MsgGearShifter_t *m, const CanFrame_t *f);

/* ── Output messages (ECU → bus) ──────────────────────────────────────────*/

/* 0x300  ACC_Status  20ms */
#define MSG_ACC_STATUS_ID   0x300u
#define MSG_ACC_STATUS_DLC  4u
typedef struct {
    uint8_t state;
    float   set_speed_kph;
    bool    aeb_active;
    bool    fault;
} MsgACCStatus_t;
void msg_acc_status_encode(const MsgACCStatus_t *m, CanFrame_t *f);

/* 0x301  ACC_Control  20ms */
#define MSG_ACC_CONTROL_ID   0x301u
#define MSG_ACC_CONTROL_DLC  4u
typedef struct {
    float   accel_demand_mps2;
    Pct_t   brake_req_pct;
    Pct_t   throttle_req_pct;
} MsgACCControl_t;
void msg_acc_control_encode(const MsgACCControl_t *m, CanFrame_t *f);

/* 0x302  LKA_Status  20ms */
#define MSG_LKA_STATUS_ID   0x302u
#define MSG_LKA_STATUS_DLC  3u
typedef struct {
    uint8_t state;
    bool    ldw_left;
    bool    ldw_right;
    bool    intervening;
} MsgLKAStatus_t;
void msg_lka_status_encode(const MsgLKAStatus_t *m, CanFrame_t *f);

/* 0x303  LKA_TorqueCmd  20ms */
#define MSG_LKA_TORQUE_ID   0x303u
#define MSG_LKA_TORQUE_DLC  2u
typedef struct {
    Nm_t    torque_nm;      /* factor=0.01, offset=-327.68 */
} MsgLKATorqueCmd_t;
void msg_lka_torque_encode(const MsgLKATorqueCmd_t *m, CanFrame_t *f);

/* 0x304  BSD_Status  20ms */
#define MSG_BSD_STATUS_ID   0x304u
#define MSG_BSD_STATUS_DLC  2u
typedef struct {
    bool    left_warn;
    bool    right_warn;
    bool    left_alert;
    bool    right_alert;
} MsgBSDStatus_t;
void msg_bsd_status_encode(const MsgBSDStatus_t *m, CanFrame_t *f);

/* 0x305  Park_Status  50ms */
#define MSG_PARK_STATUS_ID   0x305u
#define MSG_PARK_STATUS_DLC  6u
typedef struct {
    uint8_t zone_fl, zone_fr, zone_rl, zone_rr;  /* 0=clear, 8=contact */
    bool    active;
    bool    auto_brake;
} MsgParkStatus_t;
void msg_park_status_encode(const MsgParkStatus_t *m, CanFrame_t *f);

/* 0x306  HHA_Status  20ms */
#define MSG_HHA_STATUS_ID   0x306u
#define MSG_HHA_STATUS_DLC  3u
typedef struct {
    uint8_t state;
    Pct_t   brake_hold_pct;
    bool    active;
} MsgHHAStatus_t;
void msg_hha_status_encode(const MsgHHAStatus_t *m, CanFrame_t *f);

/* 0x500  LDW_Warning  100ms  → HMI */
#define MSG_LDW_WARNING_ID   0x500u
#define MSG_LDW_WARNING_DLC  2u
typedef struct {
    bool    warn_left;
    bool    warn_right;
    uint8_t intensity;
} MsgLDWWarning_t;
void msg_ldw_warning_encode(const MsgLDWWarning_t *m, CanFrame_t *f);

#endif /* CAN_MESSAGES_H */
