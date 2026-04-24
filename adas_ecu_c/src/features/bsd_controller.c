/**
 * @file  bsd_controller.c
 */

#include "features/bsd_controller.h"
#include <string.h>

#define BSD_MIN_SPEED_KPH 12.0f

void bsd_init(BsdController_t *c) {
    memset(c, 0, sizeof(*c));
    c->state = BSD_STATE_OFF;
}

void bsd_tick(BsdController_t *c,
              const VehicleState_t    *v,
              const BlindZoneModel_t  *bz,
              const MsgDriverInputs_t *driver) {

    if (v->speed_kph < BSD_MIN_SPEED_KPH || v->gear == GEAR_REVERSE) {
        c->state       = BSD_STATE_OFF;
        c->left_warn   = false;
        c->right_warn  = false;
        c->left_alert  = false;
        c->right_alert = false;
        return;
    }

    c->state = BSD_STATE_ACTIVE;

    /* Warning (LED steady): object detected in blind zone */
    c->left_warn  = bz->left_occupied;
    c->right_warn = bz->right_occupied;

    /* Alert (LED flash + chime): object + driver indicates lane change */
    c->left_alert  = bz->left_occupied  && driver->turn_left;
    c->right_alert = bz->right_occupied && driver->turn_right;

    if (c->left_alert || c->right_alert) {
        c->state = BSD_STATE_ALERT;
    }
}

void bsd_get_status_msg(const BsdController_t *c, MsgBSDStatus_t *out) {
    out->left_warn   = c->left_warn;
    out->right_warn  = c->right_warn;
    out->left_alert  = c->left_alert;
    out->right_alert = c->right_alert;
}
