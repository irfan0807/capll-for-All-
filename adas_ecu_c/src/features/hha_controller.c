/**
 * @file  hha_controller.c
 * @brief Hill Hold with brake-pressure ramp.
 */

#include "features/hha_controller.h"
#include "hal/hal_timer.h"
#include <string.h>

#define HHA_MIN_GRADIENT   0.02f    /* 2% grade */
#define HHA_HOLD_PCT       80.0f
#define HHA_MAX_HOLD_MS    3000u
#define HHA_RELEASE_MS     500u
#define HHA_MAX_SPEED_KPH  1.0f

void hha_init(HhaController_t *c) {
    memset(c, 0, sizeof(*c));
    c->state = HHA_STATE_OFF;
}

void hha_tick(HhaController_t *c, const VehicleState_t *v) {
    bool on_hill  = (v->hill_gradient >=  HHA_MIN_GRADIENT
                 ||  v->hill_gradient <= -HHA_MIN_GRADIENT);
    bool stopped  = (v->speed_kph < HHA_MAX_SPEED_KPH);
    bool braking  = (v->brake_pct > 5.0f);
    bool released = (c->prev_brake_pressed && !braking);
    bool drive    = (v->gear == GEAR_DRIVE || v->gear == GEAR_REVERSE);

    c->prev_brake_pressed = braking;

    switch (c->state) {
        case HHA_STATE_OFF:
            if (on_hill && stopped && drive) { c->state = HHA_STATE_READY; }
            c->brake_hold_pct = 0.0f;
            c->active = false;
            break;

        case HHA_STATE_READY:
            if (released) {
                c->hold_start_tick = hal_timer_get_tick();
                c->state           = HHA_STATE_HOLDING;
            }
            if (!on_hill || !stopped) { c->state = HHA_STATE_OFF; }
            break;

        case HHA_STATE_HOLDING:
            c->brake_hold_pct = HHA_HOLD_PCT;
            c->active         = true;
            if (hal_timer_elapsed(c->hold_start_tick) >= HHA_MAX_HOLD_MS
                || v->accel_pct > 10.0f) {
                c->release_start_tick = hal_timer_get_tick();
                c->state = HHA_STATE_RELEASING;
            }
            break;

        case HHA_STATE_RELEASING: {
            uint32_t elapsed = hal_timer_elapsed(c->release_start_tick);
            if (elapsed >= HHA_RELEASE_MS) {
                c->brake_hold_pct = 0.0f;
                c->active         = false;
                c->state          = HHA_STATE_OFF;
            } else {
                float ratio        = 1.0f - ((float)elapsed / (float)HHA_RELEASE_MS);
                c->brake_hold_pct  = HHA_HOLD_PCT * ratio;
            }
            break;
        }

        default: break;
    }
}

void hha_get_status_msg(const HhaController_t *c, MsgHHAStatus_t *out) {
    out->state          = (uint8_t)c->state;
    out->brake_hold_pct = c->brake_hold_pct;
    out->active         = c->active;
}
