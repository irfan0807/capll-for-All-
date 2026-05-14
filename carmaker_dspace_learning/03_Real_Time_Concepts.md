# 03 — Real-Time Concepts for HIL

> **Relevance**: Every HIL test engineer must understand real-time — it determines whether your test is valid  
> **Prerequisites**: Basic OS knowledge  
> **Outcome**: Understand scheduling, timing, overruns, FPGA offload, and how dSPACE enforces real-time

---

## 1. What Is Real-Time?

A **real-time system** must produce the correct output **within a guaranteed time deadline**.  
Missing a deadline is a failure — even if the computation result is mathematically correct.

```
Hard Real-Time vs Soft Real-Time:
──────────────────────────────────────────────────────────────
Hard Real-Time:  Missing deadline = SYSTEM FAILURE
                 Example: ABS braking, airbag deployment
                 dSPACE SCALEXIO, QNX, VxWorks

Soft Real-Time:  Missing deadline = degraded performance (OK)
                 Example: video streaming, UI updates
                 Linux, Windows

Firm Real-Time:  Occasional misses tolerated, late result is useless
                 Example: multimedia in infotainment
──────────────────────────────────────────────────────────────
```

---

## 2. Task Scheduling on dSPACE

dSPACE real-time applications use **cyclic scheduling**:

```
Timeline (1 ms base rate):
─────────────────────────────────────────────────────────────────
t=0ms   t=1ms   t=2ms   t=3ms   t=4ms
  │       │       │       │       │
  ▼       ▼       ▼       ▼       ▼
 [T1]   [T1]   [T1]   [T1]   [T1]   ← 1 kHz task (1 ms period)
 [T2]           [T2]           [T2]   ← 500 Hz task (2 ms period)
 [T3]                   [T3]         ← 250 Hz task (4 ms period)

T1: Fast I/O tasks (sensor read, actuator write)  →  1 ms period
T2: Control algorithms (AEB, ACC)                 →  2 ms period
T3: Monitoring/logging                            → 10 ms period
```

### Task Priority Rules
| Priority | Task Type | Period | Example |
|----------|-----------|--------|---------|
| Highest | I/O interrupt | < 0.1 ms | CAN Rx ISR |
| High | Fast control | 1 ms | AEB brake cmd |
| Medium | Slow control | 10 ms | ACC set speed |
| Low | Logging | 100 ms | Data logging |

---

## 3. Overrun — The Most Common HIL Problem

An **overrun** occurs when a task's execution time exceeds its period:

```
Normal execution (1 ms task, step takes 0.7 ms):
──────────────────────────────────────────────
t=0    t=1    t=2    t=3
 │──0.7──│     │──0.7──│     ← OK, 0.3 ms slack

Overrun (step takes 1.4 ms):
──────────────────────────────────────────────
t=0          t=1    t=2
 │────1.4─────│◄──overrun
                   Next step fires while previous still running!
                   dSPACE: logs overrun counter, may abort
```

### Overrun Causes
| Cause | Description | Fix |
|-------|-------------|-----|
| Algorithm too complex | Too many matrix ops, lookup tables | Reduce computation, use FPGA |
| Large Simulink model | Too many blocks at 1 kHz | Move non-critical blocks to 10 ms task |
| Bus spike | CAN flood causes ISR overload | Rate-limit messages, use FPGA CAN filter |
| Memory cache miss | First execution slower due to cold cache | Warm-up run before measurement |
| Task blocking | Mutex/semaphore wait | Redesign shared resource access |

### Detecting Overruns in ControlDesk
```
ControlDesk variable to monitor: 
  "TaskInfo/<task_name>/OverrunCounter"
  "TaskInfo/<task_name>/ExecutionTime_us"
  "TaskInfo/<task_name>/ExecutionTimeMax_us"

Rule of thumb: Max execution time should stay < 75% of period
  1 ms task → max exec time < 750 µs
```

---

## 4. WCET — Worst Case Execution Time

WCET is the **maximum time** a task will ever take to execute, considering all code paths:

```
WCET Analysis Methods:
──────────────────────────────────────────────────────────────
Static Analysis:   Analyze code paths without running
                   Tools: AbsInt aiT, Rapita RVS
                   Result: guaranteed upper bound

Measurement-based: Run many times, record maximum
                   Tools: dSPACE Profiler, oscilloscope
                   Result: observed maximum (not guaranteed)

Hybrid:            Static analysis + measurement confirmation
                   Used in ASIL-D applications (ISO 26262)
──────────────────────────────────────────────────────────────
```

### WCET Budget Allocation (1 ms task)
```
Total budget:          1000 µs
─────────────────────────────
I/O read (ADC/CAN):      50 µs
Algorithm execution:    600 µs  ← primary budget
I/O write:               50 µs
OS overhead:             50 µs
─────────────────────────────
Total budgeted:         750 µs
Safety margin:          250 µs  (25%)
```

---

## 5. Jitter, Latency, and Determinism

```
Key timing terms:
───────────────────────────────────────────────────────────
Jitter:       Variation in task start time
              Ideal: 0 µs  Acceptable: < 10 µs for 1 ms task

Latency:      Time from input event to output response
              Includes: I/O read + compute + I/O write
              Typical HIL: 1–3 ms (1–3 task cycles)

Determinism:  Property of always taking the same time
              Hard to achieve on Linux (non-RT)
              Achieved on: QNX, VxWorks, dSPACE RTOS
───────────────────────────────────────────────────────────

Jitter sources:
  - Task scheduling granularity
  - Interrupt latency
  - Cache effects
  - Memory bus contention (multi-core)
  - Timer resolution
```

### Measuring Jitter
```python
# Measure jitter using dSPACE ControlDesk Python API
import time
import numpy as np

# Sample task tick timestamps (read from DS timer board)
tick_times = []
for i in range(1000):
    tick_times.append(controldesk.get("DS_TIMER.Tick_us"))
    time.sleep(0.001)

intervals = np.diff(tick_times)
print(f"Mean period:  {np.mean(intervals):.2f} µs")
print(f"Jitter (σ):   {np.std(intervals):.2f} µs")
print(f"Max interval: {np.max(intervals):.2f} µs")
print(f"Min interval: {np.min(intervals):.2f} µs")
```

---

## 6. FPGA Offloading

FPGAs provide **sub-microsecond determinism** for tasks that are too fast for the CPU:

```
CPU vs FPGA for HIL:
──────────────────────────────────────────────────────────────
Task                         CPU Timing    FPGA Timing
──────────────────────────────────────────────────────────────
CAN message decode           ~100 µs ISR   ~100 ns
PWM generation               ~10 µs        ~20 ns
High-speed ADC sampling      ~5 µs         ~50 ns  
Short-circuit fault inject   ~1 µs min     ~10 ns
Encoder pulse counting       impossible    ~10 ns
──────────────────────────────────────────────────────────────

dSPACE FPGA boards: DS2655 (Virtex-7), DS5202 (motor control)
Programming: dSPACE FPGA Programming Blockset (Simulink-based)
```

### When to Use FPGA
- PWM signals with frequency > 10 kHz
- ADC sampling > 100 kHz
- Fault injection requiring < 1 µs response
- SPI/I2C/encoder interfaces
- Safety shutdown < 1 µs

---

## 7. Real-Time OS Overview

```
RTOS used with dSPACE:
──────────────────────────────────────────────────────────────
dSPACE RTOS:  Custom RTOS on SCALEXIO DS6001 processor board
              Deterministic, hard real-time, 64-bit

QNX:          POSIX-compliant RTOS, used in many automotive ECUs
              Priority-based preemptive scheduler

VxWorks:      Wind River RTOS, widely used in safety-critical
              Supports ARINC 653 partitioning

Linux RT:     PREEMPT_RT patch — soft real-time
              Max jitter ~50 µs (not suitable for µs-level HIL)
──────────────────────────────────────────────────────────────
```

---

## 8. Real-Time Task Model in dSPACE

```
dSPACE task structure (ConfigurationDesk):
──────────────────────────────────────────────────────────────
Application
└── Task Group
    ├── BaseRate Task (1 ms)         ← All fast I/O
    │   ├── CAN Rx Handler
    │   ├── ADC Read
    │   ├── Algorithm (AEB step)
    │   └── DAC Write
    ├── SubRate Task (10 ms)         ← Slow processing
    │   ├── Diagnostics
    │   └── DVA logging
    └── BackgroundTask              ← No timing guarantee
        ├── MATLAB data exchange
        └── ControlDesk var access
──────────────────────────────────────────────────────────────
```

---

## 9. Timing Budget Example — AEB HIL

```
AEB HIL timing chain (target: < 150 ms brake response):
──────────────────────────────────────────────────────────────────────
Event: Object enters radar FOV at t=0

Step 1:  Radar outputs object on CAN every 50 ms    → t + 50 ms
Step 2:  ECU CAN Rx interrupt fires                  → t + 50.1 ms
Step 3:  AEB algorithm runs (10 ms task)             → t + 60 ms
Step 4:  AEB sets brake demand on CAN                → t + 60.2 ms
Step 5:  Brake ECU CAN Rx + response                 → t + 70 ms
Step 6:  Hydraulic brake pressure builds             → t + 120 ms

Total: ~120 ms ← within 150 ms budget ✓

HIL validates this ENTIRE chain with real ECU hardware
SIL only validates steps 3-4 (algorithm in simulation)
──────────────────────────────────────────────────────────────────────
```

---

## 10. Interview Q&A

**Q1: What happens if a dSPACE task overruns?**  
dSPACE increments an `OverrunCounter` variable accessible in ControlDesk. Depending on configuration, the system continues (soft overrun mode) or halts the application (hard overrun mode). An overrun invalidates the timing behavior of the test — you must investigate and fix the root cause.

**Q2: What is the 75% CPU rule in HIL?**  
Best practice: keep the peak CPU load below 75% of one task period. This leaves 25% headroom for interrupt spikes, cache misses, and timing jitter. Consistently exceeding 75% causes occasional overruns which are hard to reproduce.

**Q3: What is the difference between latency and jitter?**  
Latency is the absolute time from stimulus to response (e.g., 5 ms). Jitter is the variation in that latency across repeated measurements (e.g., ±200 µs). Both matter in HIL: latency validates the functional timing budget; jitter validates determinism.

**Q4: Why can't Linux be used for hard real-time HIL?**  
Standard Linux uses a preemptive scheduler with no timing guarantees — interrupts, kernel work queues, and garbage collection can delay tasks by milliseconds. Even with PREEMPT_RT, jitter is ~50–100 µs. Hard real-time HIL requires jitter < 10 µs, only achievable with a purpose-built RTOS or FPGA timer.

**Q5: What is FPGA offloading and when would you use it in a HIL setup?**  
FPGA offloading moves time-critical I/O from the CPU to a programmable hardware chip. On dSPACE, the DS2655 FPGA board handles tasks like PWM generation (< 100 ns latency), high-speed ADC (1 MS/s), and fault injection (< 1 µs). You use it when CPU jitter is too high for a specific I/O task, or when the signal frequency exceeds what a 1 ms CPU task can handle.
