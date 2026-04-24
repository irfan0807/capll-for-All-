/**
 * @file  hal_timer.h
 * @brief Hardware timer abstraction.
 *        Embedded: volatile uint32_t incremented by SysTick ISR.
 *        Simulation: std::chrono steady_clock milliseconds.
 */

#ifndef HAL_TIMER_H
#define HAL_TIMER_H

#include "hal_types.h"

/* Initialise the timer subsystem (call once in main before scheduler). */
void         hal_timer_init(void);

/* Return current tick count in milliseconds. */
TickType_t   hal_timer_get_tick(void);

/* Block for ms milliseconds (busy-wait in embedded, sleep_for in sim). */
void         hal_timer_delay_ms(uint32_t ms);

/* Return ms elapsed since 'start_tick'. */
uint32_t     hal_timer_elapsed(TickType_t start_tick);

/* ── SysTick ISR (implemented in hal_timer.c, declared weak) ─────────────── */
/* On embedded, the startup file calls this directly from the vector table.   */
void SysTick_Handler(void);

/* ── Software timer helper ───────────────────────────────────────────────── */
typedef struct {
    TickType_t start;
    uint32_t   period_ms;
    bool       running;
    bool       one_shot;
} SoftTimer_t;

void soft_timer_start  (SoftTimer_t *t, uint32_t period_ms, bool one_shot);
void soft_timer_stop   (SoftTimer_t *t);
bool soft_timer_expired(SoftTimer_t *t);

#endif /* HAL_TIMER_H */
