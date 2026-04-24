# ADAS ECU — Embedded C Application

Same ADAS ECU as the C++ version, rewritten in **C11** to show how automotive ECU firmware is actually written — the majority of production ECU code (AUTOSAR BSW, most MCAL drivers) is still C, not C++.

---

## C vs C++ — Key Differences Here

| Concept | C++ version | C version |
|---|---|---|
| Data + behaviour | `class AccController` with methods | `AccController_t` struct + `acc_init()` / `acc_tick()` free functions |
| Encapsulation | `private:` members | `static` module-level variables in `.c` file |
| Constructors | `AccController() { ... }` | `acc_init(&g_acc)` — explicit call |
| Name collisions | `features::AccController` namespace | `acc_` prefix convention |
| Polymorphism | Virtual methods / inheritance | Function pointers (`TaskFunc_t`) |
| Singleton | `static AccController& instance()` | Module static: `static WorldModel_t s_world` |
| Compile-time constants | `static constexpr` | `#define` or `static const` |
| Typed enums | `enum class AccState : uint8_t` | `typedef enum { ... } AccState_t` |
| Aggregate init | Constructor member init list | `memset()` + field assignment in `_init()` |

---

## Architecture

```
main.c
  ├── hal/hal_timer.c       SysTick ISR (embedded) / clock_gettime (sim)
  ├── drivers/can_driver.c  bxCAN peripheral + Rx ring buffer
  ├── drivers/can_messages.c CAN encode/decode (factor/offset)
  ├── rtos/scheduler.c      Cyclic executive with function-pointer tasks
  ├── features/sensor_fusion.c  World model update
  ├── features/acc_controller.c PID + state machine
  ├── features/lka_controller.c PD torque + LDW
  ├── features/bsd_controller.c Blind spot logic
  ├── features/parking_controller.c Zone mapping
  ├── features/hha_controller.c Brake-pressure ramp
  └── diagnostics/dtc_manager.c AUTOSAR Dem-aligned DTC
```

### Task periods

| Task | Period |
|------|--------|
| `task_fast_sensors` | 10 ms |
| `task_control` | 20 ms |
| `task_medium` | 50 ms |
| `task_diagnostics` | 100 ms |
| `task_background` | 1000 ms |

---

## Build

### Simulation (macOS / Linux — no hardware needed)
```bash
cd adas_ecu_c
mkdir build && cd build
cmake -DBUILD_SIMULATION=ON -DCMAKE_BUILD_TYPE=Debug ..
make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu)
./adas_ecu_sim
```

### Embedded — ARM Cortex-M4
```bash
mkdir build_hw && cd build_hw
cmake -DEMBEDDED_TARGET=ON -DCMAKE_BUILD_TYPE=Release ..
make -j4
arm-none-eabi-size adas_ecu_sim
```

---

## Core Embedded C Patterns

### Function pointer tasks (replaces virtual dispatch)
```c
typedef void (*TaskFunc_t)(void);

typedef struct {
    const char *name;
    TaskFunc_t  func;       /* ← function pointer */
    uint32_t    period_ms;
    ...
} TaskDesc_t;

/* Registration */
sched_register(&g_sched, "Control", task_control, 20u);

/* Dispatch */
t->func();   /* call through pointer — no vtable overhead */
```

### Module state hidden in .c file
```c
/* can_driver.c — not visible outside this translation unit */
static CanFrame_t s_rx_buf[CAN_RX_BUFFER_SIZE];   /* ring buffer */
static uint8_t    s_rx_head = 0u;
static uint8_t    s_rx_tail = 0u;
static bool       s_bus_off = false;
```

### Explicit init instead of constructor
```c
/* C++ would have:  AccController acc;  (constructor auto-called) */
/* C requires:      */
AccController_t g_acc;
acc_init(&g_acc);            /* memset + set defaults */
```

### Volatile ISR counter — same in C and C++
```c
static volatile uint32_t g_tick = 0u;

void SysTick_Handler(void) {
    g_tick++;   /* volatile — compiler cannot optimise this away */
}
```

### Ring buffer without dynamic allocation
```c
#define CAN_RX_BUFFER_SIZE 64u   /* power of 2 — allows & masking */

static uint8_t rb_next(uint8_t idx) {
    return (uint8_t)((idx + 1u) & (CAN_RX_BUFFER_SIZE - 1u));
}
```

### PACKED struct for hardware DMA compatibility
```c
typedef struct PACKED {
    uint32_t id;
    uint8_t  dlc;
    uint8_t  data[8];
} CanFrame_t;
/* __attribute__((packed)) — no padding bytes, matches CAN peripheral layout */
```

### CAN signal factor/offset (DBC convention)
```c
/* Decode: physical = raw * factor  */
float speed_kph = (float)((f->data[1] << 8u) | f->data[0]) * 0.01f;

/* Encode: raw = physical / factor  */
uint16_t raw = (uint16_t)(speed_kph / 0.01f);
f->data[0] = (uint8_t)(raw & 0xFFu);
f->data[1] = (uint8_t)(raw >> 8u);
```

---

## Simulation Output Example

```
+=================================================+
| ADAS ECU Firmware  v1.0.0                       |
| Mode: SIMULATION                                |
+=================================================+

[MAIN] Scheduler started with 5 tasks

==================================================
  ADAS ECU v1.0.0  tick=1000      speed=50.0 km/h
  ACC  state=2   set=80 km/h  AEB=0
  LKA  state=2   torque=0.14 Nm  LDW-L=0 LDW-R=0
  Target: dist=70.5m  relV=-1.50m/s  TTC=47.00s  valid=1
  DTCs: active=0  confirmed=0
  Sched tasks:
    FastSensors            10ms  overruns=0  maxExec=0ms
    Control                20ms  overruns=0  maxExec=1ms
    MediumCycle            50ms  overruns=0  maxExec=0ms
    Diagnostics           100ms  overruns=0  maxExec=0ms
    Background           1000ms  overruns=0  maxExec=0ms
==================================================
```
