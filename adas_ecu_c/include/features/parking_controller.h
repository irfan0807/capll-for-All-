/**
 * @file  parking_controller.h
 * @brief Parking Distance Warning + Auto-Brake.
 */

#ifndef PARKING_CONTROLLER_H
#define PARKING_CONTROLLER_H

#include "hal/hal_types.h"
#include "features/sensor_fusion.h"
#include "drivers/can_messages.h"

typedef enum {
    PARK_STATE_OFF    = 0,
    PARK_STATE_ACTIVE = 1,
    PARK_STATE_MUTED  = 2
} ParkState_t;

typedef struct {
    ParkState_t state;
    uint8_t     zone_fl, zone_fr, zone_rl, zone_rr;
    bool        auto_brake;
} ParkingController_t;

void park_init(ParkingController_t *c);
void park_tick(ParkingController_t *c,
               const VehicleState_t    *vehicle,
               const ParkingModel_t    *park,
               const MsgDriverInputs_t *driver);
void park_get_status_msg(const ParkingController_t *c, MsgParkStatus_t *out);

#endif /* PARKING_CONTROLLER_H */
