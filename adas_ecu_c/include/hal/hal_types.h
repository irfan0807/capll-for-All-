/**
 * @file  hal_types.h
 * @brief Foundation types for the ADAS ECU firmware.
 *
 * In C there are no namespaces or classes.
 * Patterns used here:
 *   - stdint.h for portable fixed-width integers
 *   - typedef enum  for state machines and status codes
 *   - typedef struct for aggregate data
 *   - #define macros for bit manipulation and section attributes
 *   - Physical-unit typedefs (self-documenting signal types)
 */

#ifndef HAL_TYPES_H
#define HAL_TYPES_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* ── Status codes returned by all driver / module functions ─────────────────*/
typedef enum {
    STATUS_OK      = 0,
    STATUS_ERROR   = 1,
    STATUS_TIMEOUT = 2,
    STATUS_BUSY    = 3,
    STATUS_FAULT   = 4
} Status_t;

/* ── ECU operating modes ──────────────────────────────────────────────────── */
typedef enum {
    ECU_MODE_BOOT    = 0,
    ECU_MODE_INIT    = 1,
    ECU_MODE_NORMAL  = 2,
    ECU_MODE_SLEEP   = 3,
    ECU_MODE_FAULT   = 4
} EcuMode_t;

/* ── System tick type (ms, wraps at ~49 days) ─────────────────────────────── */
typedef uint32_t TickType_t;

/* ── Physical unit aliases — prevents accidental unit mismatch ────────────── */
typedef float Kph_t;        /* kilometres per hour                   */
typedef float Mps_t;        /* metres per second                     */
typedef float Metres_t;     /* metres                                */
typedef float Nm_t;         /* Newton-metres (torque)                */
typedef float Pct_t;        /* percentage  0.0–100.0                 */
typedef float Mps2_t;       /* metres per second squared (accel)     */
typedef float Degrees_t;    /* steering angle degrees                */

/* ── Utility macros ───────────────────────────────────────────────────────── */
#define ARRAY_SIZE(arr)      (sizeof(arr) / sizeof((arr)[0]))
#define BIT(n)               (1u << (n))
#define CLAMP(v, lo, hi)     ((v) < (lo) ? (lo) : (v) > (hi) ? (hi) : (v))
#define UNUSED(x)            ((void)(x))

/* ── Memory-section / packing attributes ─────────────────────────────────── */
#ifdef EMBEDDED_TARGET
#  define PACKED             __attribute__((packed))
#  define FLASH_CONST        __attribute__((section(".rodata")))
#  define RAM_FUNC           __attribute__((section(".ramfunc")))
#  define WEAK               __attribute__((weak))
#else
#  define PACKED             /* simulation: compilers pack naturally for test */
#  define FLASH_CONST
#  define RAM_FUNC
#  define WEAK
#endif

#endif /* HAL_TYPES_H */
