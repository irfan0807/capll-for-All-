/**
 * @file  dtc_manager.c
 * @brief AUTOSAR Dem-aligned DTC storage.
 */

#include "diagnostics/dtc_manager.h"
#include "hal/hal_timer.h"
#include <string.h>

static DtcEntry_t s_table[DTC_MAX_ENTRIES];
static uint8_t    s_count = 0u;

/* Find or create an entry for this DTC ID */
static DtcEntry_t *get_entry(DtcId_t id) {
    for (uint8_t i = 0u; i < s_count; i++) {
        if (s_table[i].id == id) { return &s_table[i]; }
    }
    if (s_count >= DTC_MAX_ENTRIES) { return NULL; }
    DtcEntry_t *e  = &s_table[s_count++];
    memset(e, 0, sizeof(*e));
    e->id          = id;
    e->first_tick  = hal_timer_get_tick();
    e->active      = true;
    return e;
}

void dtc_init(void) {
    memset(s_table, 0, sizeof(s_table));
    s_count = 0u;
}

void dtc_report_fault(DtcId_t id) {
    DtcEntry_t *e = get_entry(id);
    if (!e) { return; }

    e->status.test_failed            = 1u;
    e->status.test_failed_this_cycle = 1u;
    e->status.test_not_completed     = 0u;
    e->status.test_failed_since_clear= 1u;
    e->last_tick = hal_timer_get_tick();
    e->pass_counter = 0u;

    if (e->fail_counter < 255u) { e->fail_counter++; }

    if (e->fail_counter >= DTC_FAIL_TRIP_THRESHOLD) {
        if (!e->status.pending) {
            e->status.pending = 1u;
            e->occurrence++;
        }
        e->status.confirmed = 1u;
    }
}

void dtc_report_passed(DtcId_t id) {
    DtcEntry_t *e = get_entry(id);
    if (!e) { return; }

    e->status.test_failed            = 0u;
    e->status.test_failed_this_cycle = 0u;
    e->fail_counter = 0u;

    if (e->pass_counter < 255u) { e->pass_counter++; }

    if (e->pass_counter >= DTC_PASS_TRIP_THRESHOLD) {
        e->status.pending = 0u;
    }
}

void dtc_end_of_cycle(void) {
    for (uint8_t i = 0u; i < s_count; i++) {
        s_table[i].status.test_not_completed = 0u;
    }
}

void dtc_clear_all(void) {
    memset(s_table, 0, sizeof(s_table));
    s_count = 0u;
}

uint8_t dtc_get_confirmed(DtcId_t *out, uint8_t max_count) {
    uint8_t n = 0u;
    for (uint8_t i = 0u; i < s_count && n < max_count; i++) {
        if (s_table[i].status.confirmed) {
            out[n++] = s_table[i].id;
        }
    }
    return n;
}

uint8_t dtc_active_count(void) {
    uint8_t n = 0u;
    for (uint8_t i = 0u; i < s_count; i++) {
        if (s_table[i].status.test_failed) { n++; }
    }
    return n;
}

uint8_t dtc_confirmed_count(void) {
    uint8_t n = 0u;
    for (uint8_t i = 0u; i < s_count; i++) {
        if (s_table[i].status.confirmed) { n++; }
    }
    return n;
}
