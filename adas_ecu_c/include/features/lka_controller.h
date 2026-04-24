/**
 * @file  lka_controller.h
 * @brief Lane-Keeping Assist + Lane-Departure Warning.
 */

#ifndef LKA_CONTROLLER_H
#define LKA_CONTROLLER_H

#include "hal/hal_types.h"
#include "features/sensor_fusion.h"
#include "drivers/can_messages.h"

typedef enum {
    LKA_STATE_OFF         = 0,
    LKA_STATE_READY       = 1,
    LKA_STATE_PREPARING   = 2,
    LKA_STATE_INTERVENING = 3
} LkaState_t;

typedef struct {
    LkaState_t state;
    Nm_t       torque_nm;
    bool       ldw_left;
    bool       ldw_right;
    bool       intervening;
    float      prev_offset;
} LkaController_t;

void lka_init(LkaController_t *c);
void lka_tick(LkaController_t *c,
              const VehicleState_t    *vehicle,
              const LaneModel_t       *lane,
              const MsgDriverInputs_t *driver);

void lka_get_status_msg(const LkaController_t *c, MsgLKAStatus_t    *out);
void lka_get_torque_msg(const LkaController_t *c, MsgLKATorqueCmd_t *out);
void lka_get_ldw_msg   (const LkaController_t *c, MsgLDWWarning_t   *out);

#endif /* LKA_CONTROLLER_H */
