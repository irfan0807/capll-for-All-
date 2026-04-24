/**
 * @file  hha_controller.h
 * @brief Hill Hold Assist — brake pressure hold on gradient.
 */

#ifndef HHA_CONTROLLER_H
#define HHA_CONTROLLER_H

#include "hal/hal_types.h"
#include "features/sensor_fusion.h"
#include "drivers/can_messages.h"

typedef enum {
    HHA_STATE_OFF      = 0,
    HHA_STATE_READY    = 1,
    HHA_STATE_HOLDING  = 2,
    HHA_STATE_RELEASING= 3
} HhaState_t;

typedef struct {
    HhaState_t state;
    Pct_t      brake_hold_pct;
    bool       active;
    bool       prev_brake_pressed;
    TickType_t hold_start_tick;
    TickType_t release_start_tick;
} HhaController_t;

void hha_init(HhaController_t *c);
void hha_tick(HhaController_t *c, const VehicleState_t *vehicle);
void hha_get_status_msg(const HhaController_t *c, MsgHHAStatus_t *out);

#endif /* HHA_CONTROLLER_H */
