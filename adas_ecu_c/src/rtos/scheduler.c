/**
 * @file  scheduler.c
 * @brief Cyclic executive implementation.
 *        No OS, no context switch — poll-based "if (now - last >= period)".
 */

#include "rtos/scheduler.h"
#include "hal/hal_timer.h"
#include <string.h>
#include <stdio.h>

void sched_init(Scheduler_t *s) {
    memset(s, 0, sizeof(*s));
}

Status_t sched_register(Scheduler_t *s,
                         const char  *name,
                         TaskFunc_t   func,
                         uint32_t     period_ms) {
    if (s->task_count >= SCHED_MAX_TASKS) { return STATUS_ERROR; }
    TaskDesc_t *t = &s->tasks[s->task_count++];
    t->name        = name;
    t->func        = func;
    t->period_ms   = period_ms;
    t->last_run    = 0u;
    t->overrun_count = 0u;
    t->max_exec_ms   = 0u;
    return STATUS_OK;
}

void sched_start(Scheduler_t *s) {
    TickType_t now = hal_timer_get_tick();
    for (uint8_t i = 0u; i < s->task_count; i++) {
        s->tasks[i].last_run = now;
    }
    s->started    = true;
    s->any_overrun = false;
}

void sched_dispatch(Scheduler_t *s) {
    if (!s->started) { return; }
    s->any_overrun = false;
    TickType_t now = hal_timer_get_tick();

    for (uint8_t i = 0u; i < s->task_count; i++) {
        TaskDesc_t *t   = &s->tasks[i];
        uint32_t    elapsed = (uint32_t)(now - t->last_run);

        if (elapsed >= t->period_ms) {
            TickType_t t0 = hal_timer_get_tick();

            t->func();  /* ← Run the task via function pointer */

            uint32_t exec_ms = hal_timer_elapsed(t0);

            if (exec_ms > t->max_exec_ms)  { t->max_exec_ms = exec_ms; }
            if (exec_ms > t->period_ms)    {
                t->overrun_count++;
                s->any_overrun = true;
            }
            t->last_run = now;
        }
    }
}

bool sched_has_overrun(const Scheduler_t *s) {
    return s->any_overrun;
}
