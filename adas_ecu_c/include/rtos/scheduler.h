/**
 * @file  scheduler.h
 * @brief Cyclic executive task scheduler.
 *
 * No RTOS, no context switch — just "run task if period elapsed".
 * Tasks are registered as function pointers with a period in milliseconds.
 *
 * C pattern: array of TaskDesc_t structs + scheduler module state.
 * Function pointers (TaskFunc_t) replace virtual method calls.
 */

#ifndef SCHEDULER_H
#define SCHEDULER_H

#include "hal/hal_types.h"

#define SCHED_MAX_TASKS 16u

/* Function pointer type for task callbacks */
typedef void (*TaskFunc_t)(void);

typedef struct {
    const char  *name;
    TaskFunc_t   func;
    uint32_t     period_ms;
    TickType_t   last_run;
    uint32_t     overrun_count;
    uint32_t     max_exec_ms;
} TaskDesc_t;

typedef struct {
    TaskDesc_t tasks[SCHED_MAX_TASKS];
    uint8_t    task_count;
    bool       started;
    bool       any_overrun;
} Scheduler_t;

/* Initialise scheduler state */
void     sched_init     (Scheduler_t *s);

/* Register a periodic task. Returns STATUS_ERROR if table full. */
Status_t sched_register (Scheduler_t *s,
                          const char  *name,
                          TaskFunc_t   func,
                          uint32_t     period_ms);

/* Mark scheduler as running (captures start tick). */
void     sched_start    (Scheduler_t *s);

/* Call every loop iteration — dispatches tasks whose period has elapsed. */
void     sched_dispatch (Scheduler_t *s);

/* True if any task exceeded its period in the last dispatch call. */
bool     sched_has_overrun(const Scheduler_t *s);

#endif /* SCHEDULER_H */
