/**
 * @file  hal_timer.c
 * @brief Timer implementation.
 *
 * Embedded path: SysTick IRQ increments g_tick every 1 ms.
 * Simulation path: wraps POSIX clock_gettime / nanosleep.
 */

#include "hal/hal_timer.h"
#include <stdbool.h>

#ifdef SIMULATION_BUILD
#  include <time.h>
#  include <unistd.h>
static struct timespec g_start_time;

void hal_timer_init(void) {
    clock_gettime(CLOCK_MONOTONIC, &g_start_time);
}

TickType_t hal_timer_get_tick(void) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    /* Safe nanosecond subtraction: borrow from seconds if needed */
    long sec  = now.tv_sec  - g_start_time.tv_sec;
    long nsec = now.tv_nsec - g_start_time.tv_nsec;
    if (nsec < 0) { sec -= 1; nsec += 1000000000L; }
    uint64_t ms = (uint64_t)sec * 1000u + (uint64_t)nsec / 1000000u;
    return (TickType_t)ms;
}

void hal_timer_delay_ms(uint32_t ms) {
    usleep((useconds_t)ms * 1000u);
}

/* SysTick_Handler is not used in simulation */
WEAK void SysTick_Handler(void) {}

#else
/* ── Embedded: SysTick at 1 kHz ─────────────────────────────────────────── */

/* volatile — must not be cached by the compiler                             */
static volatile uint32_t g_tick = 0u;

void hal_timer_init(void) {
    /* Configure SysTick for 1 ms reload.
     * Assuming 168 MHz core clock (STM32F4):
     *   SYSTICK_LOAD = (168,000,000 / 1000) - 1  = 167999
     */
    /* SysTick->LOAD = 167999u; */
    /* SysTick->VAL  = 0u;      */
    /* SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk  */
    /*               | SysTick_CTRL_TICKINT_Msk     */
    /*               | SysTick_CTRL_ENABLE_Msk;     */
    g_tick = 0u;
}

/* Called every 1 ms from the vector table */
void SysTick_Handler(void) {
    g_tick++;
}

TickType_t hal_timer_get_tick(void) {
    /* Disable interrupts for atomic 32-bit read on Cortex-M */
    /* uint32_t primask = __get_PRIMASK(); __disable_irq(); */
    TickType_t t = g_tick;
    /* __set_PRIMASK(primask); */
    return t;
}

void hal_timer_delay_ms(uint32_t ms) {
    TickType_t start = hal_timer_get_tick();
    while (hal_timer_elapsed(start) < ms) { /* busy-wait */ }
}
#endif /* SIMULATION_BUILD */

uint32_t hal_timer_elapsed(TickType_t start) {
    return (uint32_t)(hal_timer_get_tick() - start);
}

/* ── SoftTimer ───────────────────────────────────────────────────────────── */

void soft_timer_start(SoftTimer_t *t, uint32_t period_ms, bool one_shot) {
    t->start     = hal_timer_get_tick();
    t->period_ms = period_ms;
    t->running   = true;
    t->one_shot  = one_shot;
}

void soft_timer_stop(SoftTimer_t *t) {
    t->running = false;
}

bool soft_timer_expired(SoftTimer_t *t) {
    if (!t->running) { return false; }
    if (hal_timer_elapsed(t->start) >= t->period_ms) {
        if (t->one_shot) { t->running = false; }
        else             { t->start   = hal_timer_get_tick(); }
        return true;
    }
    return false;
}
