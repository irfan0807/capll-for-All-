/**
 * @file  bsd_controller.h
 * @brief Blind Spot Detection + Cross Traffic Alert.
 */

#ifndef BSD_CONTROLLER_H
#define BSD_CONTROLLER_H

#include "hal/hal_types.h"
#include "features/sensor_fusion.h"
#include "drivers/can_messages.h"

typedef enum {
    BSD_STATE_OFF    = 0,
    BSD_STATE_ACTIVE = 1,
    BSD_STATE_ALERT  = 2
} BsdState_t;

typedef struct {
    BsdState_t state;
    bool       left_warn;
    bool       right_warn;
    bool       left_alert;
    bool       right_alert;
} BsdController_t;

void bsd_init(BsdController_t *c);
void bsd_tick(BsdController_t *c,
              const VehicleState_t    *vehicle,
              const BlindZoneModel_t  *bz,
              const MsgDriverInputs_t *driver);
void bsd_get_status_msg(const BsdController_t *c, MsgBSDStatus_t *out);

#endif /* BSD_CONTROLLER_H */
