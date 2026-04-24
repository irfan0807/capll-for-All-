/**
 * @file  can_messages.c
 * @brief CAN signal encode/decode implementations.
 *        Demonstrates factor/offset signal math — the same logic CAN tools
 *        (CANdb++, CAPL, Python-cantools) apply per DBC file.
 */

#include "drivers/can_messages.h"
#include <string.h>

/* ── Decode helpers ──────────────────────────────────────────────────────── */
static inline uint16_t u16_le(const CanFrame_t *f, uint8_t b) {
    return (uint16_t)((uint16_t)f->data[b] | ((uint16_t)f->data[b+1u] << 8u));
}
static inline int16_t s16_le(const CanFrame_t *f, uint8_t b) {
    return (int16_t)u16_le(f, b);
}

/* ── Input decodes ────────────────────────────────────────────────────────── */

void msg_vehicle_speed_decode(MsgVehicleSpeed_t *m, const CanFrame_t *f) {
    uint16_t raw    = u16_le(f, 0u);
    m->speed_kph    = (float)raw * 0.01f;
    m->valid        = (bool)(f->data[2] & 0x01u);
    m->direction_fwd= !(bool)(f->data[3] & 0x01u);
}

void msg_steering_decode(MsgSteeringAngle_t *m, const CanFrame_t *f) {
    int16_t raw_ang = s16_le(f, 0u);
    int16_t raw_rate= s16_le(f, 2u);
    m->angle_deg    = (float)raw_ang  * 0.1f;   /* signed, centre=0 */
    m->rate_dps     = (float)raw_rate * 0.1f;
    m->valid        = true;
}

void msg_wheel_speeds_decode(MsgWheelSpeeds_t *m, const CanFrame_t *f) {
    m->fl_kph = (float)u16_le(f, 0u) * 0.01f;
    m->fr_kph = (float)u16_le(f, 2u) * 0.01f;
    m->rl_kph = (float)u16_le(f, 4u) * 0.01f;
    m->rr_kph = (float)u16_le(f, 6u) * 0.01f;
}

void msg_radar_object_decode(MsgRadarObject_t *m, const CanFrame_t *f) {
    uint16_t raw_dist = u16_le(f, 0u);
    int16_t  raw_vel  = s16_le(f, 2u);
    m->distance_m     = (float)raw_dist * 0.01f;
    m->rel_vel_mps    = (float)raw_vel  * 0.01f;
    m->valid          = (bool)(f->data[4] & 0x01u);
    m->obj_type       = (RadarObjType_t)(f->data[5] & 0x03u);
    m->ttc_s          = (float)f->data[6] * 0.1f;
    m->lateral_m      = 0.0f;
}

void msg_camera_lane_decode(MsgCameraLane_t *m, const CanFrame_t *f) {
    m->left_quality   = f->data[0] & 0x03u;
    m->right_quality  = f->data[1] & 0x03u;
    int16_t lo        = s16_le(f, 2u);
    int16_t ro        = s16_le(f, 4u);
    m->left_offset_m  = (float)lo * 0.001f;
    m->right_offset_m = (float)ro * 0.001f;
    m->left_ldw       = (bool)(f->data[6] & 0x01u);
    m->right_ldw      = (bool)(f->data[6] & 0x02u);
}

void msg_bsd_radar_decode(MsgBSDRadar_t *m, const CanFrame_t *f) {
    m->left_occupied  = (bool)(f->data[0] & 0x01u);
    m->right_occupied = (bool)(f->data[0] & 0x02u);
    m->left_dist_m    = (float)f->data[1] * 0.5f;
    m->right_dist_m   = (float)f->data[2] * 0.5f;
}

void msg_ultrasonic_decode(MsgUltrasonic_t *m, const CanFrame_t *f) {
    m->front_left_cm  = f->data[0];
    m->front_right_cm = f->data[1];
    m->rear_left_cm   = f->data[2];
    m->rear_right_cm  = f->data[3];
}

void msg_driver_inputs_decode(MsgDriverInputs_t *m, const CanFrame_t *f) {
    m->acc_set     = (bool)(f->data[0] & BIT(0));
    m->acc_resume  = (bool)(f->data[0] & BIT(1));
    m->acc_cancel  = (bool)(f->data[0] & BIT(2));
    m->lka_toggle  = (bool)(f->data[0] & BIT(3));
    m->set_speed_kph = f->data[1];
    m->turn_left   = (bool)(f->data[2] & BIT(0));
    m->turn_right  = (bool)(f->data[2] & BIT(1));
    m->brake_pct   = (float)f->data[3] * (100.0f / 255.0f);
    m->accel_pct   = (float)f->data[4] * (100.0f / 255.0f);
}

void msg_gear_shifter_decode(MsgGearShifter_t *m, const CanFrame_t *f) {
    m->gear  = (Gear_t)(f->data[0] & 0x03u);
    m->valid = (bool)(f->data[1] & 0x01u);
}

/* ── Output encodes ──────────────────────────────────────────────────────── */

void msg_acc_status_encode(const MsgACCStatus_t *m, CanFrame_t *f) {
    memset(f, 0, sizeof(*f));
    f->id      = MSG_ACC_STATUS_ID;
    f->dlc     = MSG_ACC_STATUS_DLC;
    f->data[0] = m->state;
    f->data[1] = (uint8_t)(m->set_speed_kph);
    f->data[2] = (uint8_t)((m->aeb_active ? BIT(0) : 0u) |
                            (m->fault      ? BIT(1) : 0u));
}

void msg_acc_control_encode(const MsgACCControl_t *m, CanFrame_t *f) {
    memset(f, 0, sizeof(*f));
    f->id      = MSG_ACC_CONTROL_ID;
    f->dlc     = MSG_ACC_CONTROL_DLC;
    int16_t raw_acc  = (int16_t)(m->accel_demand_mps2 * 100.0f);
    f->data[0] = (uint8_t)((uint16_t)raw_acc & 0xFFu);
    f->data[1] = (uint8_t)((uint16_t)raw_acc >> 8u);
    f->data[2] = (uint8_t)(m->brake_req_pct    * 2.55f);
    f->data[3] = (uint8_t)(m->throttle_req_pct * 2.55f);
}

void msg_lka_status_encode(const MsgLKAStatus_t *m, CanFrame_t *f) {
    memset(f, 0, sizeof(*f));
    f->id      = MSG_LKA_STATUS_ID;
    f->dlc     = MSG_LKA_STATUS_DLC;
    f->data[0] = m->state;
    f->data[1] = (uint8_t)((m->ldw_left    ? BIT(0) : 0u) |
                            (m->ldw_right   ? BIT(1) : 0u) |
                            (m->intervening ? BIT(2) : 0u));
}

void msg_lka_torque_encode(const MsgLKATorqueCmd_t *m, CanFrame_t *f) {
    memset(f, 0, sizeof(*f));
    f->id      = MSG_LKA_TORQUE_ID;
    f->dlc     = MSG_LKA_TORQUE_DLC;
    int16_t raw = (int16_t)(m->torque_nm * 100.0f);
    f->data[0] = (uint8_t)((uint16_t)raw & 0xFFu);
    f->data[1] = (uint8_t)((uint16_t)raw >> 8u);
}

void msg_bsd_status_encode(const MsgBSDStatus_t *m, CanFrame_t *f) {
    memset(f, 0, sizeof(*f));
    f->id      = MSG_BSD_STATUS_ID;
    f->dlc     = MSG_BSD_STATUS_DLC;
    f->data[0] = (uint8_t)((m->left_warn   ? BIT(0) : 0u) |
                            (m->right_warn  ? BIT(1) : 0u) |
                            (m->left_alert  ? BIT(2) : 0u) |
                            (m->right_alert ? BIT(3) : 0u));
}

void msg_park_status_encode(const MsgParkStatus_t *m, CanFrame_t *f) {
    memset(f, 0, sizeof(*f));
    f->id      = MSG_PARK_STATUS_ID;
    f->dlc     = MSG_PARK_STATUS_DLC;
    f->data[0] = m->zone_fl;
    f->data[1] = m->zone_fr;
    f->data[2] = m->zone_rl;
    f->data[3] = m->zone_rr;
    f->data[4] = (uint8_t)((m->active     ? BIT(0) : 0u) |
                            (m->auto_brake ? BIT(1) : 0u));
}

void msg_hha_status_encode(const MsgHHAStatus_t *m, CanFrame_t *f) {
    memset(f, 0, sizeof(*f));
    f->id      = MSG_HHA_STATUS_ID;
    f->dlc     = MSG_HHA_STATUS_DLC;
    f->data[0] = m->state;
    f->data[1] = (uint8_t)(m->brake_hold_pct * 2.55f);
    f->data[2] = (uint8_t)(m->active ? 0x01u : 0x00u);
}

void msg_ldw_warning_encode(const MsgLDWWarning_t *m, CanFrame_t *f) {
    memset(f, 0, sizeof(*f));
    f->id      = MSG_LDW_WARNING_ID;
    f->dlc     = MSG_LDW_WARNING_DLC;
    f->data[0] = (uint8_t)((m->warn_left  ? BIT(0) : 0u) |
                            (m->warn_right ? BIT(1) : 0u));
    f->data[1] = m->intensity;
}
