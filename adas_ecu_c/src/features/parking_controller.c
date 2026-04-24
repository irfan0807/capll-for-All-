/**
 * @file  parking_controller.c
 * @brief Distance zones + auto-brake.
 */

#include "features/parking_controller.h"
#include <string.h>

/* Zone thresholds in cm: index 0=clear, index 8=contact */
static const uint8_t ZONE_UPPER[9] = {255u, 200u, 150u, 100u, 75u, 50u, 30u, 20u, 10u};
#define AUTO_BRAKE_CM  20u
#define MUTE_SPEED_KPH 10.0f

static uint8_t dist_to_zone(uint8_t cm) {
    for (uint8_t z = 8u; z > 0u; z--) {
        if (cm <= ZONE_UPPER[z]) { return z; }
    }
    return 0u;
}

void park_init(ParkingController_t *c) {
    memset(c, 0, sizeof(*c));
    c->state = PARK_STATE_OFF;
}

void park_tick(ParkingController_t *c,
               const VehicleState_t    *v,
               const ParkingModel_t    *park,
               const MsgDriverInputs_t *driver) {
    UNUSED(driver);

    /* Auto-activate when reversing at low speed */
    bool auto_on = (v->gear == GEAR_REVERSE) && (v->speed_kph < MUTE_SPEED_KPH);

    if (c->state == PARK_STATE_OFF && auto_on) { c->state = PARK_STATE_ACTIVE; }
    if (c->state == PARK_STATE_ACTIVE && !auto_on) { c->state = PARK_STATE_MUTED; }
    if (c->state == PARK_STATE_MUTED  &&  auto_on) { c->state = PARK_STATE_ACTIVE; }

    if (c->state != PARK_STATE_ACTIVE) {
        c->zone_fl = 0u; c->zone_fr = 0u;
        c->zone_rl = 0u; c->zone_rr = 0u;
        c->auto_brake = false;
        return;
    }

    c->zone_fl = dist_to_zone(park->fl_cm);
    c->zone_fr = dist_to_zone(park->fr_cm);
    c->zone_rl = dist_to_zone(park->rl_cm);
    c->zone_rr = dist_to_zone(park->rr_cm);

    /* Auto-brake if any rear sensor critical */
    c->auto_brake = (park->rl_cm <= AUTO_BRAKE_CM || park->rr_cm <= AUTO_BRAKE_CM);
}

void park_get_status_msg(const ParkingController_t *c, MsgParkStatus_t *out) {
    out->zone_fl   = c->zone_fl;
    out->zone_fr   = c->zone_fr;
    out->zone_rl   = c->zone_rl;
    out->zone_rr   = c->zone_rr;
    out->active    = (c->state == PARK_STATE_ACTIVE);
    out->auto_brake= c->auto_brake;
}
