/**
 * @file  main.c
 * @brief ADAS ECU Application — entry point and task definitions.
 *
 * C vs C++ differences visible here:
 *   - All controller instances are plain structs, not class objects
 *   - Explicit _init() calls instead of constructors
 *   - No 'this' pointer — struct pointer passed to every function
 *   - No namespaces — module prefix convention (acc_, lka_, bsd_, ...)
 *   - Function pointers stored in Scheduler_t for callbacks
 *   - Global message structs instead of AUTOSAR RTE ports
 *
 * Execution model (Cyclic Executive):
 *   10ms  task_fast_sensors  — drain CAN Rx, decode all input messages
 *   20ms  task_control       — sensor fusion + ACC + LKA + BSD
 *   50ms  task_medium        — Parking + HHA + LDW
 *  100ms  task_diagnostics   — DTC end-of-cycle
 * 1000ms  task_background    — health log + scheduler stats print
 */

#include "hal/hal_types.h"
#include "hal/hal_timer.h"
#include "drivers/can_driver.h"
#include "drivers/can_messages.h"
#include "rtos/scheduler.h"
#include "features/sensor_fusion.h"
#include "features/acc_controller.h"
#include "features/lka_controller.h"
#include "features/bsd_controller.h"
#include "features/parking_controller.h"
#include "features/hha_controller.h"
#include "diagnostics/dtc_manager.h"

#include <stdio.h>
#include <string.h>
#include <math.h>

/* ── Module instances (plain structs — no constructors) ──────────────────── */
static AccController_t     g_acc;
static LkaController_t     g_lka;
static BsdController_t     g_bsd;
static ParkingController_t g_park;
static HhaController_t     g_hha;
static Scheduler_t         g_sched;

/* ── Decoded CAN input messages ──────────────────────────────────────────── */
static MsgVehicleSpeed_t   g_speed;
static MsgSteeringAngle_t  g_steer;
static MsgWheelSpeeds_t    g_wheels;
static MsgRadarObject_t    g_radar;
static MsgCameraLane_t     g_camera;
static MsgBSDRadar_t       g_bsd_radar;
static MsgUltrasonic_t     g_ultrasonic;
static MsgDriverInputs_t   g_driver;
static MsgGearShifter_t    g_gear;

/* Dispatch received CAN frame to correct decoder */
static void dispatch_rx(const CanFrame_t *f) {
    switch (f->id) {
        case MSG_VEHICLE_SPEED_ID:   msg_vehicle_speed_decode (&g_speed,      f); break;
        case MSG_STEERING_ANGLE_ID:  msg_steering_decode      (&g_steer,      f); break;
        case MSG_WHEEL_SPEEDS_ID:    msg_wheel_speeds_decode  (&g_wheels,     f); break;
        case MSG_RADAR_OBJECT_ID:    msg_radar_object_decode  (&g_radar,      f); break;
        case MSG_CAMERA_LANE_ID:     msg_camera_lane_decode   (&g_camera,     f); break;
        case MSG_BSD_RADAR_ID:       msg_bsd_radar_decode     (&g_bsd_radar,  f); break;
        case MSG_ULTRASONIC_ID:      msg_ultrasonic_decode    (&g_ultrasonic, f); break;
        case MSG_DRIVER_INPUTS_ID:   msg_driver_inputs_decode (&g_driver,     f); break;
        case MSG_GEAR_SHIFTER_ID:    msg_gear_shifter_decode  (&g_gear,       f); break;
        default: break;
    }
}

/* ══════════════════════════════════════════════════════════════════════════════
 * TASK IMPLEMENTATIONS
 * Each is a void(void) — stored as function pointer in Scheduler_t.
 * ══════════════════════════════════════════════════════════════════════════════ */

/* 10ms — Read CAN, decode, monitor timeouts */
static void task_fast_sensors(void) {
    CanFrame_t frame;
    while (can_receive(&frame) == STATUS_OK) {
        dispatch_rx(&frame);
    }

    /* Radar timeout DTC */
    static TickType_t last_radar = 0u;
    if (g_radar.valid) {
        last_radar = hal_timer_get_tick();
        dtc_report_passed(DTC_RADAR_COMM_LOSS);
    } else if (hal_timer_elapsed(last_radar) > 500u) {
        dtc_report_fault(DTC_RADAR_COMM_LOSS);
    }

    /* Camera timeout DTC */
    static TickType_t last_camera = 0u;
    if (g_camera.left_quality > 0u || g_camera.right_quality > 0u) {
        last_camera = hal_timer_get_tick();
        dtc_report_passed(DTC_CAMERA_COMM_LOSS);
    } else if (hal_timer_elapsed(last_camera) > 2000u) {
        dtc_report_fault(DTC_CAMERA_COMM_LOSS);
    }

    /* CAN bus-off DTC */
    if (can_is_bus_off()) {
        dtc_report_fault(DTC_CAN_BUS_OFF);
    } else {
        dtc_report_passed(DTC_CAN_BUS_OFF);
    }
}

/* 20ms — Sensor fusion + ACC + LKA + BSD */
static void task_control(void) {
    CanFrame_t out_frame;

    /* 1. Update world model */
    fusion_update(&g_radar, &g_camera, &g_bsd_radar, &g_ultrasonic,
                  &g_speed, &g_steer, &g_driver, &g_gear);

    const WorldModel_t *world = fusion_get_world();

    /* 2. ACC */
    acc_tick(&g_acc, &world->vehicle, &world->front_target, &g_driver);

    MsgACCStatus_t  acc_sts;
    MsgACCControl_t acc_ctrl;
    acc_get_status_msg (&g_acc, &acc_sts);
    acc_get_control_msg(&g_acc, &acc_ctrl);
    msg_acc_status_encode (&acc_sts,  &out_frame); can_transmit(&out_frame);
    msg_acc_control_encode(&acc_ctrl, &out_frame); can_transmit(&out_frame);

    /* 3. LKA */
    lka_tick(&g_lka, &world->vehicle, &world->lane, &g_driver);

    MsgLKAStatus_t    lka_sts;
    MsgLKATorqueCmd_t lka_torq;
    lka_get_status_msg(&g_lka, &lka_sts);
    lka_get_torque_msg(&g_lka, &lka_torq);
    msg_lka_status_encode(&lka_sts,  &out_frame); can_transmit(&out_frame);
    msg_lka_torque_encode (&lka_torq, &out_frame); can_transmit(&out_frame);

    /* 4. BSD */
    bsd_tick(&g_bsd, &world->vehicle, &world->blind_zone, &g_driver);

    MsgBSDStatus_t bsd_sts;
    bsd_get_status_msg(&g_bsd, &bsd_sts);
    msg_bsd_status_encode(&bsd_sts, &out_frame); can_transmit(&out_frame);
}

/* 50ms — Parking + HHA + LDW */
static void task_medium(void) {
    CanFrame_t out_frame;

    const WorldModel_t *world = fusion_get_world();

    /* Parking */
    park_tick(&g_park, &world->vehicle, &world->parking, &g_driver);
    MsgParkStatus_t park_sts;
    park_get_status_msg(&g_park, &park_sts);
    msg_park_status_encode(&park_sts, &out_frame); can_transmit(&out_frame);

    /* HHA */
    hha_tick(&g_hha, &world->vehicle);
    MsgHHAStatus_t hha_sts;
    hha_get_status_msg(&g_hha, &hha_sts);
    msg_hha_status_encode(&hha_sts, &out_frame); can_transmit(&out_frame);

    /* LDW */
    MsgLDWWarning_t ldw;
    lka_get_ldw_msg(&g_lka, &ldw);
    msg_ldw_warning_encode(&ldw, &out_frame); can_transmit(&out_frame);
}

/* 100ms — DTC end of cycle */
static void task_diagnostics(void) {
    if (sched_has_overrun(&g_sched)) {
        dtc_report_fault(DTC_TASK_OVERRUN);
    } else {
        dtc_report_passed(DTC_TASK_OVERRUN);
    }
    dtc_end_of_cycle();
}

/* 1000ms — Print ECU health */
static void task_background(void) {
    const WorldModel_t *w = fusion_get_world();

    printf("\n==================================================\n");
    printf("  ADAS ECU v%d.%d.%d  tick=%-8u  speed=%.1f km/h\n",
           ADAS_VER_MAJOR, ADAS_VER_MINOR, ADAS_VER_PATCH,
           hal_timer_get_tick(), w->vehicle.speed_kph);
    printf("  ACC  state=%-2u  set=%.0f km/h  AEB=%d\n",
           (unsigned)g_acc.state, g_acc.set_speed_kph,
           g_acc.aeb_active ? 1 : 0);
    printf("  LKA  state=%-2u  torque=%.2f Nm  LDW-L=%d LDW-R=%d\n",
           (unsigned)g_lka.state, g_lka.torque_nm,
           g_lka.ldw_left  ? 1 : 0,
           g_lka.ldw_right ? 1 : 0);
    printf("  Target: dist=%.1fm  relV=%.2fm/s  TTC=%.2fs  valid=%d\n",
           w->front_target.distance_m,
           w->front_target.rel_vel_mps,
           w->front_target.ttc_s,
           w->front_target.valid ? 1 : 0);
    printf("  DTCs: active=%u  confirmed=%u\n",
           dtc_active_count(), dtc_confirmed_count());

    /* Confirmed DTC list */
    if (dtc_confirmed_count() > 0u) {
        DtcId_t list[32];
        uint8_t n = dtc_get_confirmed(list, 32u);
        for (uint8_t i = 0u; i < n; i++) {
            printf("    [%u] DTC 0x%06X\n", i, (unsigned)list[i]);
        }
    }

    printf("  Sched tasks:\n");
    for (uint8_t i = 0u; i < g_sched.task_count; i++) {
        const TaskDesc_t *t = &g_sched.tasks[i];
        printf("    %-22s %4ums  overruns=%u  maxExec=%ums\n",
               t->name, t->period_ms, t->overrun_count, t->max_exec_ms);
    }
    printf("==================================================\n\n");
}

/* ══════════════════════════════════════════════════════════════════════════════
 * Simulation stimulus
 * On a real ECU these messages arrive from the physical CAN bus.
 * ══════════════════════════════════════════════════════════════════════════════ */
#ifdef SIMULATION_BUILD

static void inject_simulation_frames(void) {
    static TickType_t last_inject = 0u;
    if (hal_timer_elapsed(last_inject) < 100u) { return; }
    last_inject = hal_timer_get_tick();

    static float sim_speed = 0.0f;
    static float sim_dist  = 120.0f;
    static int   sim_step  = 0;

    sim_step++;
    if      (sim_step < 50)  { sim_speed += 1.0f; }         /* Accelerate  */
    else if (sim_step < 100) { sim_dist  -= 1.5f; }          /* Target closing */
    else if (sim_step < 120) { sim_dist   = 8.0f; }          /* Critical zone  */
    else if (sim_step < 150) { sim_dist  += 2.5f; }          /* Target recedes */
    else                     { sim_step = 0; sim_speed = 0.0f; sim_dist = 120.0f; }

    if (sim_speed > 100.0f) { sim_speed = 100.0f; }
    if (sim_dist  <   2.0f) { sim_dist  =   2.0f; }

    /* VehicleSpeed */
    {
        CanFrame_t f = {0};
        f.id  = MSG_VEHICLE_SPEED_ID;
        f.dlc = MSG_VEHICLE_SPEED_DLC;
        uint16_t raw = (uint16_t)(sim_speed / 0.01f);
        f.data[0] = (uint8_t)(raw & 0xFFu);
        f.data[1] = (uint8_t)(raw >> 8u);
        f.data[2] = 0x01u;  /* valid */
        can_on_rx_isr(&f);
    }

    /* RadarObject */
    {
        CanFrame_t f = {0};
        f.id  = MSG_RADAR_OBJECT_ID;
        f.dlc = MSG_RADAR_OBJECT_DLC;
        uint16_t raw_d = (uint16_t)(sim_dist / 0.01f);
        float    ttc   = (sim_speed > 0.1f) ? (sim_dist / (sim_speed / 3.6f)) : 99.0f;
        f.data[0] = (uint8_t)(raw_d & 0xFFu);
        f.data[1] = (uint8_t)(raw_d >> 8u);
        f.data[4] = (sim_dist < 150.0f) ? 0x01u : 0x00u;
        f.data[5] = 0x01u;   /* RADAR_OBJ_CAR */
        f.data[6] = (uint8_t)(ttc < 25.5f ? ttc / 0.1f : 255u);
        can_on_rx_isr(&f);
    }

    /* DriverInputs — ACC set at step 50 */
    {
        CanFrame_t f = {0};
        f.id  = MSG_DRIVER_INPUTS_ID;
        f.dlc = MSG_DRIVER_INPUTS_DLC;
        if (sim_step == 50) {
            f.data[0] = BIT(0);   /* acc_set */
            f.data[1] = 80u;      /* set speed */
        }
        can_on_rx_isr(&f);
    }

    /* CameraLane — good quality */
    {
        CanFrame_t f = {0};
        f.id  = MSG_CAMERA_LANE_ID;
        f.dlc = MSG_CAMERA_LANE_DLC;
        f.data[0] = 3u;
        f.data[1] = 3u;
        int16_t lo = (int16_t)(0.04f / 0.001f);
        f.data[2] = (uint8_t)((uint16_t)lo & 0xFFu);
        f.data[3] = (uint8_t)((uint16_t)lo >> 8u);
        can_on_rx_isr(&f);
    }

    /* GearShifter — DRIVE */
    {
        CanFrame_t f = {0};
        f.id     = MSG_GEAR_SHIFTER_ID;
        f.dlc    = MSG_GEAR_SHIFTER_DLC;
        f.data[0] = (uint8_t)GEAR_DRIVE;
        f.data[1] = 0x01u;
        can_on_rx_isr(&f);
    }
}
#endif /* SIMULATION_BUILD */

/* ══════════════════════════════════════════════════════════════════════════════
 * MAIN
 * ══════════════════════════════════════════════════════════════════════════════ */
int main(void) {
    /* 1. HAL init */
    hal_timer_init();

    printf("+=================================================+\n");
    printf("| ADAS ECU Firmware  v%d.%d.%d                       |\n",
           ADAS_VER_MAJOR, ADAS_VER_MINOR, ADAS_VER_PATCH);
    printf("| Compiled: %s %s          |\n", __DATE__, __TIME__);
#ifdef SIMULATION_BUILD
    printf("| Mode: SIMULATION                                |\n");
#else
    printf("| Mode: EMBEDDED (ARM Cortex-M4)                  |\n");
#endif
    printf("+=================================================+\n\n");

    /* 2. Module init — explicit _init() calls (no constructors in C) */
    dtc_init  ();
    fusion_init();
    acc_init  (&g_acc);
    lka_init  (&g_lka);
    bsd_init  (&g_bsd);
    park_init (&g_park);
    hha_init  (&g_hha);
    sched_init(&g_sched);

    /* 3. CAN driver init */
    CanConfig_t can_cfg;
    can_cfg.bitrate  = CAN_BITRATE_500KBPS;
    can_cfg.channel  = 1u;
    can_cfg.loopback = false;

    if (can_init(&can_cfg) != STATUS_OK) {
        printf("[MAIN] ERROR: CAN init failed\n");
        return -1;
    }
    can_add_filter(0x100u, 0x7F0u);  /* speed/steering   0x100-0x10F */
    can_add_filter(0x200u, 0x7F0u);  /* sensor messages  0x200-0x20F */
    can_add_filter(0x400u, 0x7F0u);  /* driver inputs    0x400-0x40F */

    /* 4. Register tasks (function pointers stored in scheduler struct) */
    sched_register(&g_sched, "FastSensors",  task_fast_sensors,  10u);
    sched_register(&g_sched, "Control",      task_control,       20u);
    sched_register(&g_sched, "MediumCycle",  task_medium,        50u);
    sched_register(&g_sched, "Diagnostics",  task_diagnostics,  100u);
    sched_register(&g_sched, "Background",   task_background,  1000u);

    sched_start(&g_sched);

    printf("[MAIN] Scheduler started with %u tasks\n\n", g_sched.task_count);

    /* 5. Main loop */
#ifdef SIMULATION_BUILD
    const uint32_t SIM_DURATION_MS = 10000u;
    TickType_t     sim_start       = hal_timer_get_tick();

    while (hal_timer_elapsed(sim_start) < SIM_DURATION_MS) {
        inject_simulation_frames();  /* feed test data into CAN Rx */
        sched_dispatch(&g_sched);    /* run any due tasks */
        hal_timer_delay_ms(1u);      /* yield CPU */
    }
    printf("[MAIN] Simulation complete.\n");
#else
    /* Embedded: never returns — SysTick keeps g_tick alive */
    while (1) {
        sched_dispatch(&g_sched);
        /* __WFI(); */ /* Wait For Interrupt — saves CPU power between ticks */
    }
#endif

    return 0;
}
