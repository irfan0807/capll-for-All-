/**
 * @file  acc_controller.h
 * @brief Adaptive Cruise Control — state machine + PID + AEB.
 */

#ifndef ACC_CONTROLLER_H
#define ACC_CONTROLLER_H

#include "hal/hal_types.h"
#include "features/sensor_fusion.h"
#include "drivers/can_messages.h"

typedef enum {
    ACC_STATE_OFF      = 0,
    ACC_STATE_STANDBY  = 1,
    ACC_STATE_ACTIVE   = 2,
    ACC_STATE_OVERRIDE = 3,
    ACC_STATE_FAULT    = 4   /* AEB latched */
} AccState_t;

typedef struct {
    AccState_t state;
    float      set_speed_kph;
    float      accel_demand_mps2;
    Pct_t      brake_req_pct;
    Pct_t      throttle_req_pct;
    bool       aeb_active;

    /* PID internals */
    float      pid_integral;
    float      pid_prev_error;
} AccController_t;

void acc_init   (AccController_t *a);
void acc_tick   (AccController_t *a,
                 const VehicleState_t   *vehicle,
                 const FrontTarget_t    *target,
                 const MsgDriverInputs_t *driver);

void acc_get_status_msg (const AccController_t *a, MsgACCStatus_t  *out);
void acc_get_control_msg(const AccController_t *a, MsgACCControl_t *out);

#endif /* ACC_CONTROLLER_H */
