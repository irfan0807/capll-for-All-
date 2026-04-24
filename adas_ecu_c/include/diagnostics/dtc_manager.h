/**
 * @file  dtc_manager.h
 * @brief AUTOSAR Dem-aligned Diagnostic Trouble Code manager.
 *
 * C patterns:
 *   - enum for DTC IDs
 *   - Bitfield struct for AUTOSAR ISO 14229 status byte
 *   - Fixed-size DTC table (no dynamic allocation)
 *   - Module-level state hidden behind function interface
 */

#ifndef DTC_MANAGER_H
#define DTC_MANAGER_H

#include "hal/hal_types.h"

/* ── DTC identifiers ────────────────────────────────────────────────────── */
typedef enum {
    DTC_RADAR_COMM_LOSS     = 0x010101u,
    DTC_CAMERA_COMM_LOSS    = 0x010201u,
    DTC_ACC_INTERNAL_FAULT  = 0x020101u,
    DTC_LKA_TORQUE_OVERLOAD = 0x020201u,
    DTC_BSD_SENSOR_FAULT    = 0x020301u,
    DTC_PARKING_SENSOR_FAULT= 0x020401u,
    DTC_HHA_ACTUATOR_FAULT  = 0x020501u,
    DTC_TASK_OVERRUN        = 0x030101u,
    DTC_ECU_UNDER_VOLTAGE   = 0x040101u,
    DTC_CAN_BUS_OFF         = 0x040201u
} DtcId_t;

/* ── AUTOSAR ISO 14229 DTC status byte ───────────────────────────────────── */
typedef struct {
    uint8_t test_failed             : 1;
    uint8_t test_failed_this_cycle  : 1;
    uint8_t pending                 : 1;
    uint8_t confirmed               : 1;
    uint8_t test_not_completed      : 1;
    uint8_t test_failed_since_clear : 1;
    uint8_t reserved                : 2;
} DtcStatus_t;

/* ── DTC table entry ────────────────────────────────────────────────────── */
#define DTC_FAIL_TRIP_THRESHOLD  3u
#define DTC_PASS_TRIP_THRESHOLD  3u
#define DTC_MAX_ENTRIES         32u

typedef struct {
    DtcId_t    id;
    DtcStatus_t status;
    uint8_t    occurrence;
    uint8_t    fail_counter;
    uint8_t    pass_counter;
    TickType_t first_tick;
    TickType_t last_tick;
    bool       active;
} DtcEntry_t;

/* ── Public API ──────────────────────────────────────────────────────────── */
void    dtc_init          (void);
void    dtc_report_fault  (DtcId_t id);
void    dtc_report_passed (DtcId_t id);
void    dtc_end_of_cycle  (void);

/* UDS 0x14 — clear all DTCs */
void    dtc_clear_all     (void);

/* UDS 0x19 — get confirmed DTC list. Returns count. */
uint8_t dtc_get_confirmed (DtcId_t *out, uint8_t max_count);

uint8_t dtc_active_count   (void);
uint8_t dtc_confirmed_count(void);

#endif /* DTC_MANAGER_H */
