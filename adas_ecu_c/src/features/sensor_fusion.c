/**
 * @file  sensor_fusion.c
 * @brief World model fusion implementation.
 */

#include "features/sensor_fusion.h"
#include "hal/hal_timer.h"
#include <math.h>
#include <string.h>

/* ── Module-private state ──────────────────────────────────────────────────*/
static WorldModel_t s_world;

/* Gradient low-pass filter state */
static float s_grad_lpf     = 0.0f;
static float s_prev_speed   = 0.0f;
static TickType_t s_prev_tick = 0u;

void fusion_init(void) {
    memset(&s_world, 0, sizeof(s_world));
    s_grad_lpf   = 0.0f;
    s_prev_speed = 0.0f;
    s_prev_tick  = hal_timer_get_tick();
}

/* ── Front target fusion: radar primary, camera confirmation ─────────────*/
static void fuse_front_target(const MsgRadarObject_t *radar,
                               const MsgCameraLane_t  *camera) {
    FrontTarget_t *ft = &s_world.front_target;

    if (radar->valid) {
        ft->distance_m  = radar->distance_m;
        ft->rel_vel_mps = radar->rel_vel_mps;
        ft->ttc_s       = (radar->rel_vel_mps < -0.5f)
                          ? (-radar->distance_m / radar->rel_vel_mps)
                          : 99.0f;
        ft->lateral_m   = radar->lateral_m;
        ft->type        = (TargetType_t)radar->obj_type;
        ft->valid       = true;

        /* Camera confirmation: if camera sees lane and radar is within bounds */
        ft->confirmed = (camera->left_quality > 0u || camera->right_quality > 0u)
                        && (radar->distance_m < 150.0f)
                        && (fabsf(radar->lateral_m) < 1.5f);
    } else {
        ft->valid     = false;
        ft->confirmed = false;
    }
}

/* ── Gradient estimate: Δv / Δt ≈ g·sin(grade) + a_traction ─────────────*/
static void estimate_gradient(float speed_mps) {
    TickType_t now = hal_timer_get_tick();
    float dt = (float)(now - s_prev_tick) * 0.001f;  /* ms → seconds */
    if (dt < 0.001f) { return; }

    float accel = (speed_mps - s_prev_speed) / dt;
    /* Crude grade estimate (assumes small acceleration contribution) */
    float grade_raw = -accel / 9.81f;
    float alpha     = 0.1f;   /* LPF coefficient */
    s_grad_lpf      = s_grad_lpf + alpha * (grade_raw - s_grad_lpf);

    s_prev_speed = speed_mps;
    s_prev_tick  = now;
}

void fusion_update(const MsgRadarObject_t   *radar,
                   const MsgCameraLane_t    *camera,
                   const MsgBSDRadar_t      *bsd,
                   const MsgUltrasonic_t    *park,
                   const MsgVehicleSpeed_t  *speed,
                   const MsgSteeringAngle_t *steer,
                   const MsgDriverInputs_t  *driver,
                   const MsgGearShifter_t   *gear) {

    /* Vehicle state */
    VehicleState_t *v = &s_world.vehicle;
    v->speed_kph       = speed->speed_kph;
    v->speed_mps       = speed->speed_kph / 3.6f;
    v->steer_angle_deg = steer->angle_deg;
    v->brake_pct       = driver->brake_pct;
    v->accel_pct       = driver->accel_pct;
    v->gear            = gear->valid ? gear->gear : GEAR_DRIVE;
    v->turn_left       = driver->turn_left;
    v->turn_right      = driver->turn_right;

    estimate_gradient(v->speed_mps);
    v->hill_gradient = s_grad_lpf;

    /* Front target */
    fuse_front_target(radar, camera);

    /* Lane model */
    LaneModel_t *l     = &s_world.lane;
    l->left_offset_m   = camera->left_offset_m;
    l->right_offset_m  = camera->right_offset_m;
    l->left_quality    = camera->left_quality;
    l->right_quality   = camera->right_quality;
    l->ldw_left        = camera->left_ldw;
    l->ldw_right       = camera->right_ldw;

    /* Blind zones */
    BlindZoneModel_t *bz = &s_world.blind_zone;
    bz->left_occupied    = bsd->left_occupied;
    bz->right_occupied   = bsd->right_occupied;
    bz->left_dist_m      = bsd->left_dist_m;
    bz->right_dist_m     = bsd->right_dist_m;

    /* Parking */
    ParkingModel_t *p = &s_world.parking;
    p->fl_cm = park->front_left_cm;
    p->fr_cm = park->front_right_cm;
    p->rl_cm = park->rear_left_cm;
    p->rr_cm = park->rear_right_cm;
}

const WorldModel_t *fusion_get_world(void) {
    return &s_world;
}
