# C++ Embedded ADAS — Cheat Sheet & Quick Reference

> Fast-access reference for patterns, rules, and idioms used daily in automotive embedded C++ development.

---

## 1. Type Cheat Sheet

```cpp
// ALWAYS use these in ECU code:
#include <cstdint>
uint8_t   // 0 to 255
uint16_t  // 0 to 65,535
uint32_t  // 0 to 4,294,967,295
uint64_t  // 0 to 18.4 × 10^18
int8_t    // -128 to 127
int16_t   // -32,768 to 32,767
int32_t   // -2,147,483,648 to 2,147,483,647
float     // single precision — use on M4/M7 with FPU
bool      // always 1 byte on ARM embedded

// Literal suffixes to avoid implicit conversions:
uint8_t  x = 100U;       // U suffix
uint32_t y = 1000000UL;  // UL suffix
float    z = 3.14F;      // F suffix — NOT 3.14 (that's double!)
```

---

## 2. constexpr vs #define vs const

```cpp
// #define — no type, no scope, no debugger visibility
#define SPEED_MAX 200       // BAD

// const — typed but may not be compile-time (depends on context)
const float kMaxSpeed = 200.0F;  // OK but may be in flash (runtime load)

// constexpr — guaranteed compile-time, typed, scoped
constexpr float kMaxSpeedKmh  = 200.0F;   // BEST
constexpr uint8_t kCanDlcMax  = 8U;
constexpr uint32_t kEcuId     = 0x7E0U;

// constexpr function — computed at compile time
constexpr uint32_t BytesToBits(uint32_t bytes) { return bytes * 8U; }
static_assert(BytesToBits(8U) == 64U);  // compile-time verification
```

---

## 3. Memory Regions on ARM MCU

```
Flash (Read-only program + const data)
  .text      → compiled machine code
  .rodata    → const variables, string literals, vtables

RAM (Read-write, lost on power-off)
  .data      → initialized global/static variables (copied from flash at startup)
  .bss       → zero-initialized globals (zeroed by startup code)
  stack      → function call frames, local variables (grows downward)
  heap       → dynamic allocation (avoid in ECU production code)

Peripheral Address Space (Memory-mapped I/O)
  0x40000000+ → APB1 peripherals (UART, SPI, CAN, TIM)
  0x40020000+ → AHB1 peripherals (GPIO, DMA, RCC)
  0xE0000000+ → ARM Cortex-M system (SCB, SysTick, NVIC, DWT)
```

---

## 4. Five Golden Rules of Embedded C++

```
1. NEVER allocate memory at runtime (no new/delete/malloc/free)
   → Use static arrays, memory pools, stack objects

2. NEVER block in an ISR
   → Set a flag, push to queue, give semaphore — then return

3. ALWAYS declare ISR-shared variables as `volatile`
   → Prevents compiler from caching stale register values

4. ALWAYS use fixed-width types (uint8_t, int32_t...)
   → Size of 'int' is platform-dependent

5. ALWAYS protect shared data with critical sections or mutexes
   → Race conditions cause subtle, non-reproducible bugs
```

---

## 5. ISR Checklist

```cpp
// ✅ Correct ISR structure:
extern "C" void CAN1_RX0_IRQHandler() {
    // 1. Clear interrupt flag FIRST (prevent re-entry)
    CAN1->RF0R |= CAN_RF0R_RFOM0;

    // 2. Read hardware (minimal)
    CanFrame frame;
    frame.id  = CAN1->sFIFOMailBox[0].RIR >> 21U;
    frame.dlc = CAN1->sFIFOMailBox[0].RDTR & 0x0FU;

    // 3. Post to queue (non-blocking)
    BaseType_t woken = pdFALSE;
    xQueueSendFromISR(g_canQueue, &frame, &woken);

    // 4. Yield if higher-priority task woken
    portYIELD_FROM_ISR(woken);
}

// ❌ NEVER in ISR:
// - HAL_Delay() or vTaskDelay()
// - printf() or any I/O
// - Mutex acquire (xSemaphoreTake) — only ISR-safe *FromISR variants
// - Complex computation or infinite loops
// - Dynamic memory allocation
```

---

## 6. Common ADAS Signal Encoding

```
Signal       | DBC Factor | DBC Offset | Raw Type | Physical Range
-------------|------------|------------|----------|------------------
VehicleSpeed | 0.01       | 0          | uint16   | 0–327.67 km/h
SteerAngle   | 0.1        | -780       | uint16   | -780 to +776.7 deg
YawRate      | 0.01       | -163.84    | uint16   | -163.84 to +163.83 deg/s
Accel_X      | 0.001      | -32.768    | uint16   | -32.768 to +32.767 m/s²
BrakePress   | 0.1        | 0          | uint16   | 0–6553.5 kPa
ThrottlePct  | 0.392157   | 0          | uint8    | 0–100%
GearPos      | 1          | 0          | uint4    | enum
EngineRPM    | 0.25       | 0          | uint16   | 0–16383.75 RPM
```

---

## 7. UDS Service Quick Reference

```
SID  | Service                    | Common DIDs / Sub-functions
-----|----------------------------|---------------------------------
0x10 | DiagnosticSessionControl  | 01=Default, 02=Programming, 03=Extended
0x11 | ECUReset                  | 01=HardReset, 02=KeyOffOn, 03=SoftReset
0x14 | ClearDiagInfo             | 0xFFFFFF (all groups)
0x19 | ReadDTCInfo               | 02=ByStatus, 06=DetailedByDTC
0x22 | ReadDataByIdentifier      | F186=Session, F18C=SerialNo, F190=VIN
0x27 | SecurityAccess            | 01=Seed, 02=Key (pair)
0x28 | CommunicationControl      | 00=Enable, 01=DisableRxTx
0x2E | WriteDataByIdentifier     | F190=VIN write, custom DIDs
0x31 | RoutineControl            | 01=Start, 02=Stop, 03=RequestResult
0x34 | RequestDownload           | dataFormatId + addrAndLen
0x36 | TransferData              | blockSeqCounter + data
0x37 | RequestTransferExit       | (no sub-function)
0x3E | TesterPresent             | 00=noResponse, 80=suppressPosResp
0x85 | ControlDTCSetting         | 01=Enable, 02=Disable

Negative Response: 0x7F + SID + NRC
NRC: 0x11=ServiceNotSupported, 0x22=CondNot Correct, 0x31=RequestOutOfRange
     0x33=SecurityAccessDenied, 0x35=InvalidKey, 0x78=ResponsePending
```

---

## 8. RTOS Task Priority Guidelines (FreeRTOS)

```
Priority | Task Type                | Examples
---------|--------------------------|-------------------------------
  10     | Safety-critical          | Watchdog monitor, AEB brake
   9     | Hard real-time           | Motor control, ABS, EPS
   8     | Sensor acquisition       | CAN ISR handler, ADC
   7     | Control algorithms       | ACC, LKA, AEB logic
   6     | Communication            | CAN transmit, LIN master
   5     | State management         | Mode management, DEM
   4     | Diagnostics              | UDS, DTC management
   3     | Background processing    | NvM write, calibration
   2     | Logging / tracing        | RTT logger
   1     | Idle hooks               | Power save, stack check
   0     | FreeRTOS Idle task       | (automatic)
```

---

## 9. Memory Layout Quick Reference

```
Embedded C++ Storage Classes:
┌─────────────────────────────────────────────────────────┐
│ Storage Class    │ Section  │ Initialized │ Scope        │
├─────────────────────────────────────────────────────────┤
│ int x = 5;       │ .data    │ Yes (5)     │ global       │
│ int x;           │ .bss     │ Yes (0)     │ global       │
│ const int x = 5; │ .rodata  │ Yes (5)     │ global       │
│ static int x;    │ .bss     │ Yes (0)     │ file/func    │
│ int x (local)    │ stack    │ No (undef)  │ function     │
│ constexpr int x  │ .rodata  │ Yes         │ any          │
│ new int          │ heap     │ No          │ manual       │
└─────────────────────────────────────────────────────────┘
```

---

## 10. Algorithm Complexity in ADAS Real-Time Context

```
Operation                   | Complexity | Max targets | Budget (10ms cycle)
----------------------------|------------|-------------|---------------------
Linear search               | O(n)       | 64          | ~0.1 ms
Insertion sort              | O(n²)      | 32          | ~0.5 ms
Sort (partial selection)    | O(n·k)     | 64, k=5     | ~0.3 ms
Kalman predict+update       | O(1)       | per target  | ~0.01 ms/target
Hungarian assignment        | O(n³)      | 16          | ~1 ms
IIR filter                  | O(1)       | per signal  | ~0.001 ms
FIR filter (64 taps)        | O(n)       | per signal  | ~0.05 ms
sin/cos (software)          | O(1)       | —           | ~0.5 µs on M4+FPU
sqrt (hardware)             | O(1)       | —           | ~0.1 µs on M4+FPU
```

---

## 11. Compiler Warning Flags for Automotive

```cmake
# Recommended compiler flags for safety-critical code
set(SAFETY_WARNINGS
    -Wall                   # Standard warnings
    -Wextra                 # Extra warnings
    -Werror                 # Treat all warnings as errors
    -Wshadow                # Variable shadowing
    -Wconversion            # Implicit type conversions
    -Wsign-conversion       # Signed/unsigned conversion
    -Wdouble-promotion      # float implicitly promoted to double
    -Wfloat-equal           # Float direct comparison (MISRA 6-2-2)
    -Wundef                 # Undefined macro in #if
    -Wnull-dereference       # Potential null dereference
    -Wstrict-overflow=5     # Signed integer overflow
    -Wmissing-declarations  # Function without declaration
    -Wcast-align            # Misaligned pointer cast
    -Wunused-variable       # Declared but unused
    -Wunused-parameter      # Parameter not used
    -Wpedantic              # Strict ISO C++ compliance
)
```

---

## 12. Quick Pattern Recognition

```
Symptom                          → Pattern/Solution
---------------------------------+------------------------------------------
RAM running out                  → reduce stack sizes, use static pools
Stack overflow                   → reduce recursion, increase stack
Intermittent data corruption     → missing volatile, missing critical section
Tasks not running                → priority starvation, missing yield
CAN message not received         → wrong filter, wrong DLC/ID
UDS negative response 0x22       → conditions not correct (wrong session/security)
Float comparison bugs            → use epsilon comparison (MISRA 6-2-2)
Compiler optimizes away register → missing volatile keyword
ISR not firing                   → NVIC not enabled, wrong priority mask
Code size too large              → -Os, -ffunction-sections, LTO, remove STL
```

---

## 13. AUTOSAR SWC Interface Cheat Sheet

```
Term         | Meaning                               | C++ Equivalent
-------------|---------------------------------------|--------------------------
SWC          | Software Component                    | Class
Runnable     | Schedulable function in SWC           | Member function
Port         | Connection point for data/ops         | Member variable (interface)
P-Port       | Provide Port (produces data)          | Output parameter / write
R-Port       | Require Port (consumes data)          | Input parameter / read
S/R          | Sender/Receiver (data flow)           | Message passing
C/S          | Client/Server (function call)         | Function call / virtual method
DEM          | Diagnostic Event Manager              | DTC manager
NvM          | Non-volatile Memory Manager           | Flash storage interface
WdgM         | Watchdog Manager                      | Software watchdog
ComM         | Communication Manager                 | CAN/LIN state manager
SchM         | Scheduler Manager                     | RTOS task scheduler
```

---

## 14. CAN Bit Timing Configuration

```cpp
// BTR register for STM32 CAN at 500 kbps with 42 MHz APB1 clock:
// BRP (prescaler) = 6-1 = 5   → time quanta = 1/(42e6/6) = 142.86 ns
// TS1 (time seg1) = 8-1 = 7   → 8 TQ
// TS2 (time seg2) = 5-1 = 4   → 5 TQ
// SJW             = 1-1 = 0   → 1 TQ
// Total: 1 (sync) + 8 + 5 = 14 TQ
// Bitrate: 42e6/(6*14) = 500,000 bps ✓
// Sample point: (1+8)/14 = 64.3% ← aim for 75-80% for robustness

// Common bitrate configurations for 42 MHz APB1:
// 1 Mbps:  BRP=3,  TS1=11, TS2=2, SJW=1  (84% sample point)
// 500kbps: BRP=6,  TS1=8,  TS2=5, SJW=1  (64% sample point)  
// 250kbps: BRP=12, TS1=8,  TS2=5, SJW=1
// 125kbps: BRP=24, TS1=8,  TS2=5, SJW=1
```

---

## 15. Key C++ Concepts Map for Embedded

```
C++ Feature          | Embedded Safe? | Notes
---------------------|----------------|------------------------------------------
constexpr            | ✅ Yes          | Use liberally — compile-time only
enum class           | ✅ Yes          | Preferred over #define or plain enum
struct               | ✅ Yes          | POD types preferred for hardware data
class                | ✅ Yes          | Be aware of constructor overhead
templates            | ✅ Yes          | Zero runtime cost — compile-time only
inline functions     | ✅ Yes          | Eliminates function call overhead
references           | ✅ Yes          | No null risk, no copy
raw pointers         | ⚠️ Be careful  | Use with ownership discipline
virtual functions    | ⚠️ Use sparingly| vtable lookup — avoid in hot paths
virtual destructor   | ⚠️ Be careful  | Required if deleting via base ptr
new / delete         | ❌ Forbidden   | Non-deterministic in production ECU
std::vector          | ❌ Production  | Uses heap — OK in test builds
std::string          | ❌ Production  | Uses heap — OK in test builds
std::function        | ❌ Production  | Uses heap — use Function<> wrapper
throw / catch        | ❌ Forbidden   | Disable with -fno-exceptions
dynamic_cast         | ❌ Forbidden   | Disable with -fno-rtti
recursion            | ❌ Limit depth  | Unbounded = stack overflow risk
global variables     | ⚠️ Use static  | Minimize mutable global state
std::atomic          | ✅ Multi-core  | Use for shared vars on multi-core SoC
std::array           | ✅ Yes          | Safe wrapper, no heap
std::optional        | ✅ Stack        | Stack allocated — safe in embedded
lambdas              | ✅ Yes          | Non-capturing = zero overhead
```

---

*Last updated: May 2026 | Based on MISRA C++:2008, ISO 26262:2018, AUTOSAR R22-11*
