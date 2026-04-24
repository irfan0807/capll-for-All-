/**
 * @file  acc_controller.c
 * @brief ACC state machine, PID speed-hold, following control, AEB.
 *
 * Algorithm:
 *   STANDBY → ACTIVE on driver ACC-set button press.
 *   ACTIVE:
 *     if no target → PID speed-hold at set_speed_kph
 *     if target    → time-gap following (desired dist = speed * 2.0s + 3.0m)
 *   AEB: evaluated every tick regardless of state; latches FAULT if TTC < 1.5s
 */

#include "features/acc_controller.h"
#include "hal/hal_timer.h"
#include <math.h>
#include <string.h>

/* ── Tuning constants ────────────────────────────────────────────────────── */
#define ACC_KP              0.5f
#define ACC_KI              0.1f
#define ACC_KD              0.05f
#define ACC_MAX_INTEGRAL    2.0f
#define ACC_DT_S            0.020f      /* 20ms task period */
#define ACC_MIN_SPEED_KPH   30.0f
#define ACC_MAX_DECEL       (-4.5f)
#define AEB_DECEL           (-8.0f)
#define AEB_TTC_THRESHOLD    1.5f
#define TIME_GAP_S           2.0f
#define MIN_FOLLOW_DIST_M    3.0f

void acc_init(AccController_t *a) {
    memset(a, 0, sizeof(*a));
    a->state = ACC_STATE_OFF;
}

/* ── PID speed hold ──────────────────────────────────────────────────────── */
static float pid_speed(AccController_t *a, float set_mps, float actual_mps) {
    float error     = set_mps - actual_mps;
    a->pid_integral += error * ACC_DT_S;
    if (a->pid_integral >  ACC_MAX_INTEGRAL) { a->pid_integral =  ACC_MAX_INTEGRAL; }
    if (a->pid_integral < -ACC_MAX_INTEGRAL) { a->pid_integral = -ACC_MAX_INTEGRAL; }
    float deriv     = (error - a->pid_prev_error) / ACC_DT_S;
    a->pid_prev_error = error;
    float out       = ACC_KP * error + ACC_KI * a->pid_integral + ACC_KD * deriv;
    if (out < ACC_MAX_DECEL) { out = ACC_MAX_DECEL; }
    if (out > 3.0f)          { out = 3.0f; }
    return out;
}

/* ── Target following ─────────────────────────────────────────────────────*/
static float following_control(float dist_m, float rel_vel, float speed_mps) {
    float desired = speed_mps * TIME_GAP_S + MIN_FOLLOW_DIST_M;
    float gap_err = dist_m - desired;
    float demand  = 0.3f * gap_err + 0.5f * rel_vel;
    if (demand < ACC_MAX_DECEL) { demand = ACC_MAX_DECEL; }
    if (demand > 2.0f)          { demand = 2.0f; }
    return demand;
}

/* ── AEB — always evaluated regardless of state ──────────────────────────*/
static void run_aeb(AccController_t *a, const FrontTarget_t *target) {
    if (target->valid && target->ttc_s < AEB_TTC_THRESHOLD) {
        a->aeb_active        = true;
        a->accel_demand_mps2 = AEB_DECEL;
        a->brake_req_pct     = 100.0f;
        a->throttle_req_pct  = 0.0f;
        if (a->state != ACC_STATE_FAULT) { a->state = ACC_STATE_FAULT; }
    } else {
        a->aeb_active = false;
    }
}

void acc_tick(AccController_t *a,
              const VehicleState_t    *vehicle,
              const FrontTarget_t     *target,
              const MsgDriverInputs_t *driver) {

    run_aeb(a, target); /* safety function — always first */
    if (a->aeb_active) { return; }

    switch (a->state) {
        case ACC_STATE_OFF:
            if (driver->acc_set && vehicle->speed_kph > ACC_MIN_SPEED_KPH) {
                a->set_speed_kph = vehicle->speed_kph;
                a->state         = ACC_STATE_STANDBY;
            }
            break;

        case ACC_STATE_STANDBY:
            if (driver->acc_cancel) { a->state = ACC_STATE_OFF;    break; }
            if (driver->acc_set || driver->acc_resume) {
                a->pid_integral   = 0.0f;
                a->pid_prev_error = 0.0f;
                a->state          = ACC_STATE_ACTIVE;
            }
            break;

        case ACC_STATE_ACTIVE: {
            if (driver->acc_cancel)            { a->state = ACC_STATE_OFF;      break; }
            if (driver->brake_pct > 5.0f
                || driver->accel_pct > 50.0f)  { a->state = ACC_STATE_OVERRIDE; break; }
            if (driver->acc_set) { a->set_speed_kph = vehicle->speed_kph; }

            float demand;
            if (target->valid && target->distance_m < 120.0f) {
                demand = following_control(target->distance_m,
                                           target->rel_vel_mps,
                                           vehicle->speed_mps);
            } else {
                demand = pid_speed(a, a->set_speed_kph / 3.6f, vehicle->speed_mps);
            }

            a->accel_demand_mps2 = demand;
            a->brake_req_pct     = (demand < 0.0f) ? (-demand / 4.5f * 100.0f) : 0.0f;
            a->throttle_req_pct  = (demand > 0.0f) ? ( demand / 3.0f * 100.0f) : 0.0f;
            break;
        }

        case ACC_STATE_OVERRIDE:
            /* Return to ACTIVE once driver releases */
            if (driver->brake_pct < 2.0f && driver->accel_pct < 5.0f) {
                a->state = ACC_STATE_ACTIVE;
            }
            a->accel_demand_mps2 = 0.0f;
            a->brake_req_pct     = 0.0f;
            a->throttle_req_pct  = 0.0f;
            break;

        case ACC_STATE_FAULT:
            /* AEB latch — no movement until re-init */
            a->accel_demand_mps2 = 0.0f;
            a->brake_req_pct     = 100.0f;
            a->throttle_req_pct  = 0.0f;
            break;

        default: break;
    }
}

void acc_get_status_msg(const AccController_t *a, MsgACCStatus_t *out) {
    out->state         = (uint8_t)a->state;
    out->set_speed_kph = a->set_speed_kph;
    out->aeb_active    = a->aeb_active;
    out->fault         = (a->state == ACC_STATE_FAULT);
}

void acc_get_control_msg(const AccController_t *a, MsgACCControl_t *out) {
    out->accel_demand_mps2 = a->accel_demand_mps2;
    out->brake_req_pct     = a->brake_req_pct;
    out->throttle_req_pct  = a->throttle_req_pct;
}
