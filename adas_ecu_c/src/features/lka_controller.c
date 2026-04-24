/**
 * @file  lka_controller.c
 * @brief LKA PD torque steering + LDW suppressed by turn signal.
 */

#include "features/lka_controller.h"
#include <math.h>
#include <string.h>

#define LKA_MIN_SPEED_KPH    60.0f
#define LKA_KP               3.5f
#define LKA_KD               1.2f
#define LKA_MAX_TORQUE_NM    5.0f
#define LDW_WARN_THRESHOLD_M 0.27f
#define LKA_DT_S             0.020f

void lka_init(LkaController_t *c) {
    memset(c, 0, sizeof(*c));
    c->state = LKA_STATE_OFF;
}

static bool can_activate(const VehicleState_t *v, const LaneModel_t *l,
                          const MsgDriverInputs_t *d) {
    return v->speed_kph >= LKA_MIN_SPEED_KPH
        && (l->left_quality > 0u || l->right_quality > 0u)
        && !d->turn_left && !d->turn_right;
}

void lka_tick(LkaController_t *c,
              const VehicleState_t    *v,
              const LaneModel_t       *lane,
              const MsgDriverInputs_t *driver) {

    /* ── LDW: always evaluated ─────────────────────────────────────────── */
    bool turn = driver->turn_left || driver->turn_right;
    c->ldw_left  = !turn && lane->left_quality  > 0u
                   && (lane->left_offset_m  > LDW_WARN_THRESHOLD_M);
    c->ldw_right = !turn && lane->right_quality > 0u
                   && (lane->right_offset_m < -LDW_WARN_THRESHOLD_M);

    /* ── LKA state machine ─────────────────────────────────────────────── */
    switch (c->state) {
        case LKA_STATE_OFF:
            if (driver->lka_toggle) { c->state = LKA_STATE_READY; }
            c->torque_nm = 0.0f;
            break;

        case LKA_STATE_READY:
            if (driver->lka_toggle) { c->state = LKA_STATE_OFF; break; }
            if (can_activate(v, lane, driver)) { c->state = LKA_STATE_PREPARING; }
            c->torque_nm = 0.0f;
            break;

        case LKA_STATE_PREPARING:
            if (!can_activate(v, lane, driver)) { c->state = LKA_STATE_READY; break; }
            c->state = LKA_STATE_INTERVENING;
            break;

        case LKA_STATE_INTERVENING: {
            if (!can_activate(v, lane, driver)) { c->state = LKA_STATE_READY; break; }

            /* Use left offset (positive = drifting right = need left correction) */
            float offset = lane->left_offset_m;
            float rate   = (offset - c->prev_offset) / LKA_DT_S;
            c->prev_offset = offset;

            /* PD controller: positive torque = steer left */
            float torque = -(LKA_KP * offset + LKA_KD * rate);

            if (torque >  LKA_MAX_TORQUE_NM) { torque =  LKA_MAX_TORQUE_NM; }
            if (torque < -LKA_MAX_TORQUE_NM) { torque = -LKA_MAX_TORQUE_NM; }
            c->torque_nm  = torque;
            c->intervening = (fabsf(torque) > 0.5f);
            break;
        }

        default: break;
    }
}

void lka_get_status_msg(const LkaController_t *c, MsgLKAStatus_t *out) {
    out->state       = (uint8_t)c->state;
    out->ldw_left    = c->ldw_left;
    out->ldw_right   = c->ldw_right;
    out->intervening = c->intervening;
}

void lka_get_torque_msg(const LkaController_t *c, MsgLKATorqueCmd_t *out) {
    out->torque_nm = c->torque_nm;
}

void lka_get_ldw_msg(const LkaController_t *c, MsgLDWWarning_t *out) {
    out->warn_left  = c->ldw_left;
    out->warn_right = c->ldw_right;
    out->intensity  = (c->ldw_left || c->ldw_right) ? 3u : 0u;
}
