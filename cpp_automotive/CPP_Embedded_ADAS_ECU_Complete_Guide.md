# C++ for Embedded ADAS & ECU Software — Complete Learning Guide

> **Audience:** Engineers moving into or deepening skills in embedded automotive C++ (ADAS, Body ECU, Powertrain, Gateway, BMS, Chassis).
> **Standard Baseline:** C++14 / C++17 as used in production automotive stacks (AUTOSAR Adaptive, ROS2-based ADAS, custom RTOS targets).

---

## Table of Contents

1. [Embedded C++ vs Desktop C++](#1-embedded-c-vs-desktop-c)
2. [Core Language Foundations](#2-core-language-foundations)
3. [Memory Management in Embedded Systems](#3-memory-management-in-embedded-systems)
4. [Object-Oriented Design for ECU Software](#4-object-oriented-design-for-ecu-software)
5. [Templates & Generic Programming](#5-templates--generic-programming)
6. [Concurrency & Real-Time Programming](#6-concurrency--real-time-programming)
7. [Interrupt Service Routines & Hardware Abstraction](#7-interrupt-service-routines--hardware-abstraction)
8. [Communication Protocols in C++](#8-communication-protocols-in-c)
9. [Diagnostics & UDS in C++](#9-diagnostics--uds-in-c)
10. [AUTOSAR Classic & Adaptive C++ Patterns](#10-autosar-classic--adaptive-c-patterns)
11. [ADAS Algorithm Implementation in C++](#11-adas-algorithm-implementation-in-c)
12. [Safety-Critical C++ — MISRA & ISO 26262](#12-safety-critical-c--misra--iso-26262)
13. [Testing & Validation of Embedded C++](#13-testing--validation-of-embedded-c)
14. [Build Systems, Toolchains & Cross-Compilation](#14-build-systems-toolchains--cross-compilation)
15. [Performance Optimization for ECU Targets](#15-performance-optimization-for-ecu-targets)
16. [Common Patterns & Anti-Patterns](#16-common-patterns--anti-patterns)
17. [Complete Code Examples by Domain](#17-complete-code-examples-by-domain)

---

## 1. Embedded C++ vs Desktop C++

### Key Differences

| Feature              | Desktop C++                  | Embedded / Automotive C++             |
|----------------------|------------------------------|---------------------------------------|
| Heap allocation      | Freely used                  | Restricted or forbidden at runtime    |
| Exceptions           | Standard                     | Often disabled (`-fno-exceptions`)    |
| RTTI                 | Available                    | Often disabled (`-fno-rtti`)          |
| STL containers       | Freely used                  | Restricted (no dynamic allocation)    |
| `std::thread`        | OK                           | Replaced by RTOS tasks                |
| Startup time         | Not critical                 | Deterministic init required           |
| Stack size           | OS-managed, large            | Fixed, small (often 1–8 KB/task)      |
| Floating point       | Hardware FPU assumed         | May be software emulated — costly     |
| Timing               | `std::chrono` loose          | Cycle-accurate, deterministic         |
| Compiler             | GCC/Clang/MSVC               | arm-none-eabi-g++, TASKING, GreenHills|

### What Is Allowed — Safe Subset

```
ALLOWED in automotive C++:
  - All value types (int, float, struct, enum class)
  - Stack-allocated objects
  - References and raw pointers (with ownership discipline)
  - Templates (resolved at compile time)
  - Inline functions
  - constexpr / static_assert
  - Placement new (pre-allocated pools)
  - RTOS wrappers (FreeRTOS, OSEK/OIL, Adaptive AUTOSAR ara::exec)

RESTRICTED / FORBIDDEN:
  - new / delete at runtime (use memory pools)
  - std::vector, std::map, std::string (use static alternatives)
  - Virtual destructors in safety-critical paths (table lookup overhead)
  - Exceptions (catch/throw — non-deterministic stack unwinding)
  - RTTI (dynamic_cast, typeid — code size, non-determinism)
  - Recursion (stack overflow risk — ban or bound depth)
  - Global mutable state shared across tasks without synchronisation
```

---

## 2. Core Language Foundations

### 2.1 Data Types & Sizing

Always use fixed-width types from `<cstdint>` in ECU code:

```cpp
#include <cstdint>

// Correct for embedded:
uint8_t  byteValue  = 0xFFU;
uint16_t canId      = 0x7DFU;
uint32_t timestamp  = 0UL;
int16_t  steerAngle = -450;    // -45.0 degrees * 10
int32_t  velocity   = 0;       // mm/s

// NEVER use: int, long, unsigned -- size is platform-dependent
// size of 'int' on ARM Cortex-M = 32 bits, but code must be portable
```

### 2.2 `constexpr` — Compile-Time Constants

```cpp
// Bad: macro, no type safety
#define MAX_CAN_DLC 8

// Good: constexpr, typed, scoped
constexpr uint8_t  kMaxCanDlc   = 8U;
constexpr uint16_t kMaxCanId    = 0x7FFU;
constexpr uint32_t kTickRate_Hz = 1000U;   // 1 ms tick

// Compile-time computation
constexpr uint32_t MillisToTicks(uint32_t ms) {
    return ms * kTickRate_Hz / 1000U;
}
static_assert(MillisToTicks(10U) == 10U, "Tick calc wrong");
```

### 2.3 `enum class` — Type-Safe Enumerations

```cpp
// Old C-style enums — namespace pollution, implicit conversion to int:
enum GearState { PARK, REVERSE, NEUTRAL, DRIVE }; // BAD

// Modern, safe:
enum class GearState : uint8_t {
    Park    = 0U,
    Reverse = 1U,
    Neutral = 2U,
    Drive   = 3U,
    Invalid = 0xFFU
};

void SetGear(GearState gear) {
    if (gear == GearState::Drive) {
        // type-safe comparison, no accidental int comparison
    }
}
```

### 2.4 References vs Pointers

```cpp
// Use const references for read-only large inputs (no copy, no null)
void ProcessSensorData(const SensorFrame& frame);

// Use pointers only when nullptr is a valid sentinel
bool GetCalibration(CalibData* out);   // returns false if unavailable

// Use output parameters by reference for multiple return values
void ComputeSteerCmd(float lateralError, float& cmdAngle, float& cmdTorque);
```

### 2.5 `static` Variables — Gotchas in Embedded

```cpp
// Function-local static — initialized once, NOT thread-safe on multi-core
uint32_t GetUniqueId() {
    static uint32_t counter = 0U;   // WARNING: race condition on multi-core
    return ++counter;
}

// Module-level static — limits linkage to translation unit (good for HAL)
static uint32_t s_adcRawValue = 0U;  // only visible in this .cpp file

// Static class members — shared across all instances
class CanBus {
public:
    static uint32_t s_totalFramesSent;
};
uint32_t CanBus::s_totalFramesSent = 0U;
```

### 2.6 `volatile` — Essential for Hardware Registers

```cpp
// Without volatile, compiler may optimize away repeated reads
// This is WRONG for memory-mapped registers:
uint32_t* reg = reinterpret_cast<uint32_t*>(0x40020000UL);
while (*reg == 0U) {}   // compiler may cache first read!

// Correct:
volatile uint32_t* reg = reinterpret_cast<volatile uint32_t*>(0x40020000UL);
while (*reg == 0U) {}   // re-read every iteration

// In ISR shared variables always use volatile:
volatile bool g_adcReady = false;

void ADC_IRQHandler() {
    g_adcReady = true;   // volatile write — compiler won't optimise away
}
```

### 2.7 Bit Manipulation — The Embedded Staple

```cpp
#include <cstdint>

// Register manipulation utilities
inline void SetBit(volatile uint32_t& reg, uint8_t bit) {
    reg |= (1UL << bit);
}
inline void ClearBit(volatile uint32_t& reg, uint8_t bit) {
    reg &= ~(1UL << bit);
}
inline bool TestBit(uint32_t reg, uint8_t bit) {
    return (reg & (1UL << bit)) != 0U;
}

// Bit-field structures — useful but watch alignment/padding
struct CanFlags {
    uint8_t ide  : 1;   // Extended ID flag
    uint8_t rtr  : 1;   // Remote Transmission Request
    uint8_t dlc  : 4;   // Data Length Code (0-8)
    uint8_t rsv  : 2;   // Reserved
};

// Better — explicit masks to avoid compiler-specific bit ordering
constexpr uint8_t kCanIde = 0x01U;
constexpr uint8_t kCanRtr = 0x02U;
constexpr uint8_t kCanDlcMask = 0x3CU;
constexpr uint8_t kCanDlcShift = 2U;
```

---

## 3. Memory Management in Embedded Systems

### 3.1 Why Dynamic Allocation is Banned

- `new`/`delete` call the heap allocator → **non-deterministic timing**
- Heap fragmentation → eventual allocation failure after long runtime
- Heap corruption is hard to detect and causes cascading failures
- ISO 26262 ASIL-D / IEC 61508 SIL-3 prohibit unbounded dynamic allocation

### 3.2 Static Allocation Patterns

```cpp
// Statically allocated buffers — size known at compile time
constexpr uint16_t kMaxCanFrames = 64U;

struct CanFrame {
    uint32_t id;
    uint8_t  dlc;
    uint8_t  data[8];
    uint32_t timestamp;
};

// Global or file-scope static — allocated in BSS/data segment
static CanFrame s_canRxBuffer[kMaxCanFrames];
static uint16_t s_canRxHead = 0U;
static uint16_t s_canRxTail = 0U;
```

### 3.3 Memory Pool (Fixed-Size Block Allocator)

```cpp
// Generic typed memory pool — O(1) alloc/free, no fragmentation
template<typename T, uint16_t Capacity>
class MemPool {
public:
    MemPool() : m_freeCount(Capacity) {
        // Build free list
        for (uint16_t i = 0U; i < Capacity - 1U; ++i) {
            m_pool[i].next = &m_pool[i + 1U];
        }
        m_pool[Capacity - 1U].next = nullptr;
        m_freeHead = &m_pool[0U];
    }

    T* Allocate() {
        if (m_freeHead == nullptr) return nullptr;
        Node* node = m_freeHead;
        m_freeHead = node->next;
        --m_freeCount;
        return reinterpret_cast<T*>(&node->storage);
    }

    void Free(T* ptr) {
        if (ptr == nullptr) return;
        ptr->~T();  // explicit destructor
        Node* node = reinterpret_cast<Node*>(ptr);
        node->next = m_freeHead;
        m_freeHead = node;
        ++m_freeCount;
    }

    uint16_t FreeCount() const { return m_freeCount; }

private:
    union Node {
        alignas(T) uint8_t storage[sizeof(T)];
        Node* next;
    };
    Node     m_pool[Capacity];
    Node*    m_freeHead;
    uint16_t m_freeCount;
};

// Usage:
MemPool<CanFrame, 64U> g_canPool;

void OnCanReceive(const CanFrame& raw) {
    CanFrame* frame = g_canPool.Allocate();
    if (frame != nullptr) {
        *frame = raw;
        ProcessFrame(frame);
        g_canPool.Free(frame);
    }
}
```

### 3.4 Ring Buffer (Circular Queue)

```cpp
// Lock-free single-producer single-consumer ring buffer
// Safe between one ISR (producer) and one task (consumer)
template<typename T, uint16_t Size>
class RingBuffer {
    static_assert((Size & (Size - 1U)) == 0U, "Size must be power of 2");
public:
    bool Push(const T& item) {
        uint16_t head = m_head;
        uint16_t next = (head + 1U) & (Size - 1U);
        if (next == m_tail) return false;  // full
        m_buffer[head] = item;
        m_head = next;
        return true;
    }

    bool Pop(T& item) {
        uint16_t tail = m_tail;
        if (tail == m_head) return false;  // empty
        item = m_buffer[tail];
        m_tail = (tail + 1U) & (Size - 1U);
        return true;
    }

    bool IsEmpty() const { return m_head == m_tail; }
    uint16_t Count() const {
        return (m_head - m_tail + Size) & (Size - 1U);
    }

private:
    T                    m_buffer[Size];
    volatile uint16_t    m_head{0U};
    volatile uint16_t    m_tail{0U};
};

// Example: ISR → Task
static RingBuffer<CanFrame, 32U> s_canRxQueue;

// Called from CAN ISR (producer)
void CAN1_RX0_IRQHandler() {
    CanFrame frame = ReadHardwareCanFrame();
    (void)s_canRxQueue.Push(frame);
}

// Called from processing task (consumer)
void CanProcessingTask() {
    CanFrame frame;
    while (s_canRxQueue.Pop(frame)) {
        HandleCanFrame(frame);
    }
}
```

### 3.5 Stack Usage Analysis

```cpp
// Annotate maximum stack depth for safety review
// GCC extension to measure stack usage at compile time
void MyTask() __attribute__((optimize("O0")));

// Use compiler flag: -fstack-usage
// Generates .su files with per-function stack usage

// Manual worst-case estimation:
// Task stack = local vars + call tree depth + interrupt nesting
// Rule of thumb: allocate 2x worst-case + 256 bytes guard
```

---

## 4. Object-Oriented Design for ECU Software

### 4.1 Class Design Principles — SOLID in Embedded

```cpp
// Single Responsibility: One class = one ECU concern
class SpeedSensor {
public:
    explicit SpeedSensor(uint8_t channelId);
    bool     Init();
    float    ReadSpeedKmh() const;
    bool     IsValid() const;
private:
    uint8_t m_channel;
    float   m_lastReading;
    bool    m_valid;
};

// Open/Closed: Extend via composition or policy, not modification
// Liskov: Derived ECU components must be substitutable for base
// Interface Segregation: Don't force clients to depend on unused interfaces
// Dependency Inversion: High-level modules depend on abstractions
```

### 4.2 Interface (Pure Abstract Base) Pattern

```cpp
// ICanTransceiver.h — Abstract interface for CAN hardware
class ICanTransceiver {
public:
    virtual ~ICanTransceiver() = default;
    virtual bool     Init(uint32_t baudRate) = 0;
    virtual bool     Send(const CanFrame& frame) = 0;
    virtual bool     Receive(CanFrame& frame) = 0;
    virtual bool     IsOnBus() const = 0;
};

// Mcp2515Transceiver.h — Real hardware implementation
class Mcp2515Transceiver : public ICanTransceiver {
public:
    bool Init(uint32_t baudRate) override;
    bool Send(const CanFrame& frame) override;
    bool Receive(CanFrame& frame) override;
    bool IsOnBus() const override;
private:
    void WriteRegister(uint8_t addr, uint8_t value);
};

// MockCanTransceiver.h — Test double for unit testing
class MockCanTransceiver : public ICanTransceiver {
public:
    bool Init(uint32_t baudRate) override { return true; }
    bool Send(const CanFrame& frame) override {
        m_sentFrames.push_back(frame);  // OK to use STL in test build
        return true;
    }
    bool Receive(CanFrame& frame) override {
        if (m_injectQueue.empty()) return false;
        frame = m_injectQueue.front();
        m_injectQueue.pop_front();
        return true;
    }
    bool IsOnBus() const override { return true; }
    // Test helpers
    std::vector<CanFrame>    m_sentFrames;
    std::deque<CanFrame>     m_injectQueue;
};
```

### 4.3 RAII — Resource Acquisition Is Initialization

Critical in embedded for managing hardware resources:

```cpp
// RAII wrapper for critical sections (disable/enable interrupts)
class CriticalSection {
public:
    CriticalSection() {
        m_savedMask = DisableInterrupts();  // platform-specific
    }
    ~CriticalSection() {
        RestoreInterrupts(m_savedMask);
    }
    // Non-copyable
    CriticalSection(const CriticalSection&) = delete;
    CriticalSection& operator=(const CriticalSection&) = delete;
private:
    uint32_t m_savedMask;
};

// Usage — interrupts restored even on early return
void UpdateSharedData(uint32_t value) {
    CriticalSection cs;  // interrupts disabled here
    g_sharedValue = value;
    if (value == 0U) return;   // destructor fires → interrupts re-enabled
    g_otherValue = value * 2U;
}   // destructor fires here normally
```

### 4.4 Singleton for ECU Managers (With Care)

```cpp
// Meyers Singleton — thread-safe in C++11 and later
// Use sparingly — prefer dependency injection for testability
class CanManager {
public:
    static CanManager& Instance() {
        static CanManager instance;  // constructed once, guaranteed
        return instance;
    }

    bool Init(ICanTransceiver& transceiver) {
        m_transceiver = &transceiver;
        return m_transceiver->Init(500000U);  // 500 kbps
    }

    bool SendFrame(const CanFrame& frame) {
        return (m_transceiver != nullptr) && m_transceiver->Send(frame);
    }

private:
    CanManager() = default;
    ~CanManager() = default;
    CanManager(const CanManager&) = delete;
    CanManager& operator=(const CanManager&) = delete;

    ICanTransceiver* m_transceiver{nullptr};
};
```

### 4.5 State Machine Pattern — Core ECU Pattern

```cpp
// Strongly-typed state machine for ADAS feature states
enum class AdasState : uint8_t {
    Inactive     = 0U,
    Standby      = 1U,
    Active       = 2U,
    Override     = 3U,
    Fault        = 4U
};

enum class AdasEvent : uint8_t {
    IgnitionOn   = 0U,
    DriverEnable = 1U,
    DriverCancel = 2U,
    FaultDetect  = 3U,
    FaultClear   = 4U,
    IgnitionOff  = 5U
};

class AdasStateMachine {
public:
    AdasStateMachine() : m_state(AdasState::Inactive) {}

    void HandleEvent(AdasEvent event) {
        switch (m_state) {
            case AdasState::Inactive:
                if (event == AdasEvent::IgnitionOn)
                    Transition(AdasState::Standby);
                break;

            case AdasState::Standby:
                if (event == AdasEvent::DriverEnable)
                    Transition(AdasState::Active);
                else if (event == AdasEvent::FaultDetect)
                    Transition(AdasState::Fault);
                else if (event == AdasEvent::IgnitionOff)
                    Transition(AdasState::Inactive);
                break;

            case AdasState::Active:
                if (event == AdasEvent::DriverCancel)
                    Transition(AdasState::Standby);
                else if (event == AdasEvent::FaultDetect)
                    Transition(AdasState::Fault);
                break;

            case AdasState::Fault:
                if (event == AdasEvent::FaultClear)
                    Transition(AdasState::Standby);
                else if (event == AdasEvent::IgnitionOff)
                    Transition(AdasState::Inactive);
                break;

            default:
                break;
        }
    }

    AdasState GetState() const { return m_state; }

private:
    void Transition(AdasState newState) {
        OnExit(m_state);
        m_state = newState;
        OnEntry(m_state);
    }

    void OnEntry(AdasState state) {
        // Platform-specific actions on state entry
        switch (state) {
            case AdasState::Active:   ActivateActuators(); break;
            case AdasState::Fault:    SetDTCFault();       break;
            default: break;
        }
    }

    void OnExit(AdasState state) {
        switch (state) {
            case AdasState::Active: DeactivateActuators(); break;
            default: break;
        }
    }

    AdasState m_state;
};
```

---

## 5. Templates & Generic Programming

### 5.1 Why Templates in Embedded?

Templates produce code resolved at **compile time** — zero runtime overhead.
Ideal for: typed buffers, generic algorithms, units of measure, protocol codecs.

### 5.2 Fixed-Size Array Wrapper

```cpp
// Safe array with bounds checking — replaces raw C arrays
template<typename T, uint16_t N>
class Array {
public:
    static constexpr uint16_t kSize = N;

    T& operator[](uint16_t idx) {
        // Hard fault or assert in production if out of bounds
        assert(idx < N);
        return m_data[idx];
    }

    const T& operator[](uint16_t idx) const {
        assert(idx < N);
        return m_data[idx];
    }

    constexpr uint16_t Size() const { return N; }
    T* Data() { return m_data; }
    const T* Data() const { return m_data; }

    // Range-based for loop support
    T* begin() { return m_data; }
    T* end()   { return m_data + N; }
    const T* begin() const { return m_data; }
    const T* end()   const { return m_data + N; }

private:
    T m_data[N]{};
};

// Sensor data frame example
Array<uint16_t, 8U> adcSamples;
adcSamples[0] = ReadADC(0U);
for (auto& sample : adcSamples) {
    // process...
}
```

### 5.3 Strong Types for Physical Units

```cpp
// Prevent unit mix-ups — critical in ADAS
template<typename Tag, typename ValueType = float>
class StrongType {
public:
    explicit StrongType(ValueType v) : m_value(v) {}
    ValueType Value() const { return m_value; }

    bool operator==(const StrongType& o) const { return m_value == o.m_value; }
    bool operator< (const StrongType& o) const { return m_value <  o.m_value; }
    bool operator> (const StrongType& o) const { return m_value >  o.m_value; }

private:
    ValueType m_value;
};

struct MetersTag {};
struct SecondsTag {};
struct KphTag {};
struct DegreesTag {};

using Meters  = StrongType<MetersTag>;
using Seconds = StrongType<SecondsTag>;
using Kph     = StrongType<KphTag>;
using Degrees = StrongType<DegreesTag>;

// Compiler error if you accidentally pass Meters where Kph expected:
void SetFollowDistance(Meters dist);   // can't pass Kph accidentally
void SetTargetSpeed(Kph speed);

// Construction requires explicit tag
Meters  followDist{50.0F};
Kph     cruiseSpeed{120.0F};
SetFollowDistance(followDist);   // OK
// SetFollowDistance(cruiseSpeed); // COMPILE ERROR — type safety!
```

### 5.4 Template Policy Pattern

```cpp
// Strategy for sensor filtering — swap algorithms without runtime cost
template<typename FilterPolicy>
class SensorProcessor {
public:
    float Process(float raw) {
        return m_filter.Apply(raw);
    }
private:
    FilterPolicy m_filter;
};

// Filter policies
struct NoFilter {
    float Apply(float raw) { return raw; }
};

struct MovingAverage {
    static constexpr uint8_t kWindow = 8U;
    float Apply(float raw) {
        m_samples[m_idx] = raw;
        m_idx = (m_idx + 1U) % kWindow;
        float sum = 0.0F;
        for (uint8_t i = 0U; i < kWindow; ++i) sum += m_samples[i];
        return sum / static_cast<float>(kWindow);
    }
    float   m_samples[kWindow]{};
    uint8_t m_idx{0U};
};

struct MedianFilter {
    // ... implementation
    float Apply(float raw) { /* sort 3-tap window */ return raw; }
};

// Compile-time selection — no virtual dispatch overhead
SensorProcessor<MovingAverage> radarProcessor;
SensorProcessor<MedianFilter>  lidarProcessor;
```

---

## 6. Concurrency & Real-Time Programming

### 6.1 RTOS Task Model

Most automotive ECUs run FreeRTOS, OSEK/OIL, or proprietary RTOS.
C++ tasks are wrapped around RTOS primitives:

```cpp
// FreeRTOS C++ task wrapper
#include "FreeRTOS.h"
#include "task.h"

class RtosTask {
public:
    RtosTask(const char* name, uint16_t stackWords, uint8_t priority)
        : m_name(name), m_stackWords(stackWords), m_priority(priority) {}

    bool Start() {
        return xTaskCreate(
            TaskEntry,
            m_name,
            m_stackWords,
            this,
            m_priority,
            &m_handle
        ) == pdPASS;
    }

    virtual void Run() = 0;  // Override in derived class
    virtual ~RtosTask() = default;

protected:
    void Delay(uint32_t ms) {
        vTaskDelay(pdMS_TO_TICKS(ms));
    }

private:
    static void TaskEntry(void* param) {
        static_cast<RtosTask*>(param)->Run();
        vTaskDelete(nullptr);
    }
    const char*  m_name;
    uint16_t     m_stackWords;
    uint8_t      m_priority;
    TaskHandle_t m_handle{nullptr};
};

// Concrete ADAS task
class AebControlTask : public RtosTask {
public:
    AebControlTask() : RtosTask("AEB_Ctrl", 512U, 5U) {}

    void Run() override {
        while (true) {
            float ttc = m_radar.GetTimeToCollision();
            if (ttc < kWarningThreshold) {
                m_brakeCtrl.ApplyBrake(ComputeBrakeLevel(ttc));
            }
            Delay(10U);  // 10 ms period
        }
    }

private:
    static constexpr float kWarningThreshold = 2.5F;  // seconds
    RadarSensor   m_radar;
    BrakeControl  m_brakeCtrl;
};
```

### 6.2 Mutex & Semaphore Wrappers

```cpp
// RAII mutex for FreeRTOS
class Mutex {
public:
    Mutex() { m_handle = xSemaphoreCreateMutex(); }
    ~Mutex() { vSemaphoreDelete(m_handle); }

    bool Lock(uint32_t timeoutMs = portMAX_DELAY) {
        return xSemaphoreTake(m_handle, pdMS_TO_TICKS(timeoutMs)) == pdTRUE;
    }
    void Unlock() {
        xSemaphoreGive(m_handle);
    }

private:
    SemaphoreHandle_t m_handle;
};

class LockGuard {
public:
    explicit LockGuard(Mutex& m) : m_mutex(m) { m_mutex.Lock(); }
    ~LockGuard() { m_mutex.Unlock(); }
    LockGuard(const LockGuard&) = delete;
private:
    Mutex& m_mutex;
};

// Usage
static Mutex g_sensorMutex;
static SensorData g_latestSensor;

void UpdateSensor(const SensorData& data) {
    LockGuard lock(g_sensorMutex);
    g_latestSensor = data;
}

SensorData ReadSensor() {
    LockGuard lock(g_sensorMutex);
    return g_latestSensor;
}
```

### 6.3 Event Flags & Message Queues

```cpp
// Message queue for inter-task communication
template<typename T, uint8_t Depth>
class MessageQueue {
public:
    MessageQueue() {
        m_handle = xQueueCreate(Depth, sizeof(T));
    }

    bool Send(const T& msg, uint32_t timeoutMs = 0U) {
        return xQueueSend(m_handle, &msg, pdMS_TO_TICKS(timeoutMs)) == pdTRUE;
    }

    bool SendFromISR(const T& msg) {
        BaseType_t woken = pdFALSE;
        bool ok = xQueueSendFromISR(m_handle, &msg, &woken) == pdTRUE;
        portYIELD_FROM_ISR(woken);
        return ok;
    }

    bool Receive(T& msg, uint32_t timeoutMs = portMAX_DELAY) {
        return xQueueReceive(m_handle, &msg, pdMS_TO_TICKS(timeoutMs)) == pdTRUE;
    }

private:
    QueueHandle_t m_handle;
};

// Example usage
struct CanMsg { uint32_t id; uint8_t data[8]; uint8_t dlc; };
static MessageQueue<CanMsg, 16U> g_canRxQueue;

// ISR producer
extern "C" void CAN1_RX0_IRQHandler() {
    CanMsg msg = ReadCanHardware();
    g_canRxQueue.SendFromISR(msg);
}

// Task consumer
void CanDispatchTask() {
    CanMsg msg;
    while (g_canRxQueue.Receive(msg)) {
        DispatchCanMessage(msg);
    }
}
```

### 6.4 Priority Inversion & Priority Inheritance

```cpp
// Priority inversion scenario:
// Low priority task L holds mutex M
// High priority task H waits on M
// Medium priority task X preempts L indefinitely -> H starved

// Solution: Priority Inheritance Mutex (PIM)
// FreeRTOS: Use xSemaphoreCreateMutex() — has built-in priority inheritance

// Rule: Keep critical sections SHORT
// Avoid calling any blocking API inside a mutex lock

// Bad:
void BadTask() {
    LockGuard lock(g_mutex);
    SendCanFrame(frame);    // BLOCKING — can cause inversion
    ReadUART(buffer, 64);   // BLOCKING
}

// Good:
void GoodTask() {
    CanFrame localCopy;
    {
        LockGuard lock(g_mutex);
        localCopy = g_sharedFrame;  // copy only — brief lock
    }
    SendCanFrame(localCopy);   // outside lock
}
```

---

## 7. Interrupt Service Routines & Hardware Abstraction

### 7.1 ISR Rules in C++

```cpp
// ISRs must be C-linkage (no name mangling)
extern "C" void TIM2_IRQHandler();

// Keep ISRs very short — only set flags or push to queues
// Never: allocate memory, call printf, acquire mutex (non-ISR-safe), 
//        call complex C++ functions

volatile bool g_timer2Fired = false;

extern "C" void TIM2_IRQHandler() {
    // Clear interrupt flag first (hardware-specific)
    TIM2->SR &= ~TIM_SR_UIF;
    // Signal task
    g_timer2Fired = true;
}

// Or use FreeRTOS ISR-safe API
extern "C" void TIM2_IRQHandler() {
    TIM2->SR &= ~TIM_SR_UIF;
    BaseType_t woken = pdFALSE;
    vTaskNotifyGiveFromISR(g_timerTaskHandle, &woken);
    portYIELD_FROM_ISR(woken);
}
```

### 7.2 Hardware Abstraction Layer (HAL) in C++

```cpp
// Abstract GPIO interface
class IGpio {
public:
    enum class Direction { Input, Output };
    enum class Level     { Low = 0, High = 1 };

    virtual ~IGpio() = default;
    virtual void     SetDirection(Direction dir) = 0;
    virtual void     Write(Level level) = 0;
    virtual Level    Read() const = 0;
    virtual void     Toggle() = 0;
};

// STM32 HAL implementation
class Stm32Gpio : public IGpio {
public:
    Stm32Gpio(GPIO_TypeDef* port, uint16_t pin) 
        : m_port(port), m_pin(pin) {}

    void SetDirection(Direction dir) override {
        GPIO_InitTypeDef cfg{};
        cfg.Pin  = m_pin;
        cfg.Mode = (dir == Direction::Output) ? 
                   GPIO_MODE_OUTPUT_PP : GPIO_MODE_INPUT;
        cfg.Pull = GPIO_NOPULL;
        cfg.Speed = GPIO_SPEED_FREQ_LOW;
        HAL_GPIO_Init(m_port, &cfg);
    }

    void Write(Level level) override {
        HAL_GPIO_WritePin(m_port, m_pin,
            (level == Level::High) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    }

    Level Read() const override {
        return (HAL_GPIO_ReadPin(m_port, m_pin) == GPIO_PIN_SET) ?
               Level::High : Level::Low;
    }

    void Toggle() override {
        HAL_GPIO_TogglePin(m_port, m_pin);
    }

private:
    GPIO_TypeDef* m_port;
    uint16_t      m_pin;
};

// Test stub
class GpioStub : public IGpio {
public:
    void  SetDirection(Direction) override {}
    void  Write(Level level) override { m_level = level; }
    Level Read() const override { return m_level; }
    void  Toggle() override {
        m_level = (m_level == Level::Low) ? Level::High : Level::Low;
    }
    Level m_level{Level::Low};
};
```

### 7.3 SPI Driver Example

```cpp
class ISpiDriver {
public:
    virtual ~ISpiDriver() = default;
    virtual bool Transfer(const uint8_t* tx, uint8_t* rx, uint16_t len) = 0;
    virtual void ChipSelect(bool active) = 0;
};

// Generic sensor over SPI
class SpiSensor {
public:
    explicit SpiSensor(ISpiDriver& spi) : m_spi(spi) {}

    bool ReadRegister(uint8_t regAddr, uint8_t& value) {
        uint8_t tx[2] = { static_cast<uint8_t>(regAddr | 0x80U), 0x00U };
        uint8_t rx[2] = { 0U, 0U };
        m_spi.ChipSelect(true);
        bool ok = m_spi.Transfer(tx, rx, 2U);
        m_spi.ChipSelect(false);
        if (ok) value = rx[1];
        return ok;
    }

    bool WriteRegister(uint8_t regAddr, uint8_t value) {
        uint8_t tx[2] = { static_cast<uint8_t>(regAddr & 0x7FU), value };
        m_spi.ChipSelect(true);
        bool ok = m_spi.Transfer(tx, nullptr, 2U);
        m_spi.ChipSelect(false);
        return ok;
    }

private:
    ISpiDriver& m_spi;
};
```

---

## 8. Communication Protocols in C++

### 8.1 CAN Frame Encoder/Decoder

```cpp
// Signal encoding for CAN — matching DBC definitions
class CanSignalCodec {
public:
    // Pack a signal into frame bytes (Intel byte order)
    static void PackSignal(uint8_t* data, uint8_t startBit, uint8_t length,
                           uint64_t value) {
        for (uint8_t i = 0U; i < length; ++i) {
            uint8_t bitPos = startBit + i;
            uint8_t byteIdx = bitPos / 8U;
            uint8_t bitIdx  = bitPos % 8U;
            if (value & (1ULL << i)) {
                data[byteIdx] |=  (1U << bitIdx);
            } else {
                data[byteIdx] &= ~(1U << bitIdx);
            }
        }
    }

    // Unpack a signal from frame bytes (Intel byte order)
    static uint64_t UnpackSignal(const uint8_t* data, uint8_t startBit,
                                 uint8_t length) {
        uint64_t result = 0ULL;
        for (uint8_t i = 0U; i < length; ++i) {
            uint8_t bitPos = startBit + i;
            uint8_t byteIdx = bitPos / 8U;
            uint8_t bitIdx  = bitPos % 8U;
            if (data[byteIdx] & (1U << bitIdx)) {
                result |= (1ULL << i);
            }
        }
        return result;
    }

    // Apply scale/offset (from DBC)
    static float PhysicalValue(uint64_t rawVal, float factor, float offset) {
        return static_cast<float>(rawVal) * factor + offset;
    }
};

// Generated signal packer for specific message
class VehicleSpeedMessage {
public:
    static constexpr uint32_t kCanId  = 0x3E9U;
    static constexpr uint8_t  kDlc    = 8U;
    // DBC: VehicleSpeed, startBit=0, length=16, factor=0.01, offset=0
    static constexpr uint8_t  kSpeedStartBit = 0U;
    static constexpr uint8_t  kSpeedLength   = 16U;
    static constexpr float    kSpeedFactor   = 0.01F;
    static constexpr float    kSpeedOffset   = 0.0F;

    void SetSpeed(float speedKmh) {
        uint64_t raw = static_cast<uint64_t>(
            (speedKmh - kSpeedOffset) / kSpeedFactor);
        CanSignalCodec::PackSignal(m_data, kSpeedStartBit, kSpeedLength, raw);
    }

    float GetSpeed() const {
        uint64_t raw = CanSignalCodec::UnpackSignal(
            m_data, kSpeedStartBit, kSpeedLength);
        return CanSignalCodec::PhysicalValue(raw, kSpeedFactor, kSpeedOffset);
    }

    const uint8_t* Data() const { return m_data; }
    uint8_t Dlc() const { return kDlc; }

private:
    uint8_t m_data[kDlc]{};
};
```

### 8.2 LIN Protocol Handler

```cpp
// LIN frame structure
struct LinFrame {
    uint8_t  pid;         // Protected Identifier
    uint8_t  data[8];
    uint8_t  dataLength;
    uint8_t  checksum;

    static uint8_t ComputeChecksum(const uint8_t* data, uint8_t len,
                                   uint8_t pid, bool enhanced) {
        uint16_t sum = enhanced ? pid : 0U;
        for (uint8_t i = 0U; i < len; ++i) {
            sum += data[i];
            if (sum > 0xFFU) sum -= 0xFFU;
        }
        return static_cast<uint8_t>(0xFFU - static_cast<uint8_t>(sum));
    }

    static uint8_t ComputePid(uint8_t id) {
        bool p0 = ((id ^ (id >> 1U) ^ (id >> 2U) ^ (id >> 4U)) & 1U) != 0U;
        bool p1 = !((((id >> 1U) ^ (id >> 3U) ^ (id >> 4U) ^ (id >> 5U)) & 1U) != 0U);
        return static_cast<uint8_t>((id & 0x3FU) | (p0 ? 0x40U : 0U) | (p1 ? 0x80U : 0U));
    }
};
```

### 8.3 UDS / Diagnostic Framing

See Section 9 for full UDS implementation.

### 8.4 Ethernet / SOME/IP Basics (Adaptive ADAS ECU)

```cpp
// SOME/IP header structure
struct SomeIpHeader {
    uint32_t serviceId;    // 16-bit service + 16-bit method
    uint32_t length;       // payload length + 8 (header fields after)
    uint32_t clientSession;// 16-bit client + 16-bit session
    uint8_t  protoVersion; // 0x01
    uint8_t  ifaceVersion;
    uint8_t  msgType;      // 0x00=Request, 0x02=Response, 0x01=Fire&Forget
    uint8_t  returnCode;   // 0x00=OK

    void Serialize(uint8_t* buf) const {
        // Big-endian serialization
        buf[0]  = (serviceId >> 24U) & 0xFFU;
        buf[1]  = (serviceId >> 16U) & 0xFFU;
        buf[2]  = (serviceId >>  8U) & 0xFFU;
        buf[3]  =  serviceId         & 0xFFU;
        // ... etc
    }
};
```

---

## 9. Diagnostics & UDS in C++

### 9.1 UDS Service Dispatcher

```cpp
// UDS ISO 14229 service handler framework
enum class UdsServiceId : uint8_t {
    DiagnosticSessionControl = 0x10U,
    EcuReset                 = 0x11U,
    ClearDTC                 = 0x14U,
    ReadDTCInfo              = 0x19U,
    ReadDataByIdentifier     = 0x22U,
    WriteDataByIdentifier    = 0x2EU,
    RoutineControl           = 0x31U,
    RequestDownload          = 0x34U,
    TransferData             = 0x36U,
    RequestTransferExit      = 0x37U,
    TesterPresent            = 0x3EU,
    SecurityAccess           = 0x27U
};

enum class UdsNrc : uint8_t {
    PositiveResponse         = 0x00U,  // not an NRC — response SID = req+0x40
    GeneralReject            = 0x10U,
    ServiceNotSupported      = 0x11U,
    SubFunctionNotSupported  = 0x12U,
    IncorrectLength          = 0x13U,
    RequestOutOfRange        = 0x31U,
    SecurityAccessDenied     = 0x33U,
    InvalidKey               = 0x35U,
    ConditionsNotCorrect     = 0x22U
};

// Abstract service handler
class IUdsServiceHandler {
public:
    virtual ~IUdsServiceHandler() = default;
    virtual UdsServiceId ServiceId() const = 0;
    virtual void Handle(const uint8_t* req, uint16_t reqLen,
                        uint8_t* resp, uint16_t& respLen) = 0;
};

// ReadDataByIdentifier (0x22) handler
class ReadDataByIdHandler : public IUdsServiceHandler {
public:
    UdsServiceId ServiceId() const override {
        return UdsServiceId::ReadDataByIdentifier;
    }

    void Handle(const uint8_t* req, uint16_t reqLen,
                uint8_t* resp, uint16_t& respLen) override {
        if (reqLen < 3U) {
            BuildNegativeResponse(resp, respLen,
                UdsServiceId::ReadDataByIdentifier, UdsNrc::IncorrectLength);
            return;
        }

        uint16_t did = (static_cast<uint16_t>(req[1]) << 8U) | req[2];
        resp[0] = static_cast<uint8_t>(UdsServiceId::ReadDataByIdentifier) + 0x40U;
        resp[1] = req[1];
        resp[2] = req[2];

        switch (did) {
            case 0xF186U: {  // ActiveDiagnosticSession
                resp[3] = static_cast<uint8_t>(m_session);
                respLen = 4U;
                break;
            }
            case 0xF18CU: {  // ECU Serial Number
                const char* sn = "ECU-SN-2025-001";
                uint8_t snLen = static_cast<uint8_t>(strlen(sn));
                memcpy(&resp[3], sn, snLen);
                respLen = 3U + snLen;
                break;
            }
            default:
                BuildNegativeResponse(resp, respLen,
                    UdsServiceId::ReadDataByIdentifier,
                    UdsNrc::RequestOutOfRange);
                break;
        }
    }

private:
    void BuildNegativeResponse(uint8_t* resp, uint16_t& respLen,
                               UdsServiceId sid, UdsNrc nrc) {
        resp[0] = 0x7FU;
        resp[1] = static_cast<uint8_t>(sid);
        resp[2] = static_cast<uint8_t>(nrc);
        respLen = 3U;
    }

    uint8_t m_session{0x01U};  // default session
};

// UDS dispatcher — routes requests to handlers
class UdsDispatcher {
public:
    static constexpr uint8_t kMaxHandlers = 16U;

    bool RegisterHandler(IUdsServiceHandler& handler) {
        if (m_count >= kMaxHandlers) return false;
        m_handlers[m_count++] = &handler;
        return true;
    }

    void ProcessRequest(const uint8_t* req, uint16_t reqLen,
                        uint8_t* resp, uint16_t& respLen) {
        if (reqLen == 0U) return;
        auto sid = static_cast<UdsServiceId>(req[0]);

        for (uint8_t i = 0U; i < m_count; ++i) {
            if (m_handlers[i]->ServiceId() == sid) {
                m_handlers[i]->Handle(req, reqLen, resp, respLen);
                return;
            }
        }

        // No handler — ServiceNotSupported
        resp[0] = 0x7FU;
        resp[1] = req[0];
        resp[2] = static_cast<uint8_t>(UdsNrc::ServiceNotSupported);
        respLen = 3U;
    }

private:
    IUdsServiceHandler* m_handlers[kMaxHandlers]{};
    uint8_t             m_count{0U};
};
```

### 9.2 DTC Manager

```cpp
struct Dtc {
    uint32_t code;           // e.g. P0100
    uint8_t  statusByte;     // ISO 14229 DTC status bits
    uint32_t timestamp;      // ms since ECU start
};

class DtcManager {
public:
    static constexpr uint8_t kMaxDtcs = 32U;

    bool SetDtc(uint32_t code) {
        // Check if already exists
        for (uint8_t i = 0U; i < m_count; ++i) {
            if (m_dtcs[i].code == code) {
                m_dtcs[i].statusByte |= 0x01U;  // testFailed
                return true;
            }
        }
        if (m_count >= kMaxDtcs) return false;
        m_dtcs[m_count++] = {code, 0x01U, GetTimestamp()};
        return true;
    }

    bool ClearAll() {
        m_count = 0U;
        return true;
    }

    uint8_t GetCount() const { return m_count; }
    const Dtc& Get(uint8_t idx) const { return m_dtcs[idx]; }

private:
    Dtc     m_dtcs[kMaxDtcs]{};
    uint8_t m_count{0U};
};
```

---

## 10. AUTOSAR Classic & Adaptive C++ Patterns

### 10.1 AUTOSAR Classic — SWC (Software Component) Pattern

```cpp
// Runnable concept — AUTOSAR SWC runnable in C++
class AebSwc {
public:
    // Called by RTE at configured period (e.g., 10ms)
    void Run_10ms() {
        // Read via RTE port (abstracted)
        float distance = Rte_Read_RadarPort_Distance();
        float speed    = Rte_Read_VehicleSpeed_Speed();

        float ttc = (speed > 0.1F) ? (distance / speed) : 999.0F;

        uint8_t brakeCmd = 0U;
        if (ttc < 1.0F) {
            brakeCmd = 255U;  // Full brake
        } else if (ttc < 2.5F) {
            brakeCmd = static_cast<uint8_t>((2.5F - ttc) / 1.5F * 255.0F);
        }

        Rte_Write_BrakePort_BrakeCommand(brakeCmd);
    }

private:
    // RTE abstractions (generated by tools like ISOLAR-A, SystemDesk)
    float Rte_Read_RadarPort_Distance();
    float Rte_Read_VehicleSpeed_Speed();
    void  Rte_Write_BrakePort_BrakeCommand(uint8_t cmd);
};
```

### 10.2 AUTOSAR Adaptive — ara::com Service Interface

```cpp
// AUTOSAR Adaptive Platform — service proxy pattern
#include "ara/com/types.h"

// Proxy class (auto-generated from ARXML)
class RadarServiceProxy {
public:
    struct Fields {
        ara::com::SamplePtr<RadarTargetList> latestTargets;
    };

    // Subscribe to event
    void SubscribeToTargetList(uint16_t cacheSize) {
        TargetListEvent.Subscribe(cacheSize);
    }

    ara::com::Event<RadarTargetList> TargetListEvent;
};

// Usage in ADAS application
class FusionApp {
public:
    void Init() {
        // Find service instance
        auto handles = RadarServiceProxy::FindService(
            ara::com::InstanceIdentifier("Radar_Front"));
        if (!handles.empty()) {
            m_radarProxy = std::make_unique<RadarServiceProxy>(handles[0]);
            m_radarProxy->SubscribeToTargetList(5U);
            m_radarProxy->TargetListEvent.SetReceiveHandler(
                [this]() { OnRadarUpdate(); });
        }
    }

    void OnRadarUpdate() {
        m_radarProxy->TargetListEvent.GetNewSamples(
            [this](auto sample) {
                ProcessTargets(*sample);
            });
    }

private:
    std::unique_ptr<RadarServiceProxy> m_radarProxy;
    void ProcessTargets(const RadarTargetList& targets);
};
```

---

## 11. ADAS Algorithm Implementation in C++

### 11.1 Time-To-Collision (TTC) Calculator

```cpp
class TtcCalculator {
public:
    struct Target {
        float rangeM;         // meters
        float relVelocityMps; // m/s (negative = approaching)
    };

    // Returns TTC in seconds. Returns infinity if not approaching.
    static float Compute(const Target& t) {
        if (t.relVelocityMps >= 0.0F) {
            return std::numeric_limits<float>::infinity();
        }
        return -t.rangeM / t.relVelocityMps;
    }

    // FCW threshold classification
    enum class WarningLevel : uint8_t { None, Caution, Warning, Critical };

    static WarningLevel Classify(float ttcSeconds) {
        if      (ttcSeconds < 1.2F) return WarningLevel::Critical;
        else if (ttcSeconds < 2.0F) return WarningLevel::Warning;
        else if (ttcSeconds < 3.5F) return WarningLevel::Caution;
        else                        return WarningLevel::None;
    }
};
```

### 11.2 PID Controller — Adaptive Cruise Control

```cpp
class PidController {
public:
    struct Config {
        float kP;
        float kI;
        float kD;
        float outputMin;
        float outputMax;
        float integralClamp;  // anti-windup
    };

    explicit PidController(const Config& cfg) : m_cfg(cfg) {}

    float Update(float setpoint, float measured, float dt) {
        float error = setpoint - measured;

        // Proportional
        float p = m_cfg.kP * error;

        // Integral with anti-windup clamping
        m_integral += error * dt;
        m_integral = Clamp(m_integral, -m_cfg.integralClamp, m_cfg.integralClamp);
        float i = m_cfg.kI * m_integral;

        // Derivative (on measurement to avoid derivative kick)
        float dError = (m_lastMeasured - measured) / dt;  // note: inverted
        float d = m_cfg.kD * dError;

        m_lastMeasured = measured;

        float output = p + i + d;
        return Clamp(output, m_cfg.outputMin, m_cfg.outputMax);
    }

    void Reset() {
        m_integral = 0.0F;
        m_lastMeasured = 0.0F;
    }

private:
    static float Clamp(float val, float lo, float hi) {
        return (val < lo) ? lo : (val > hi) ? hi : val;
    }

    Config m_cfg;
    float  m_integral{0.0F};
    float  m_lastMeasured{0.0F};
};

// ACC usage
void AccTask(float targetDist, float currentDist, float currentSpeed) {
    static PidController distPid({
        .kP = 0.4F, .kI = 0.05F, .kD = 0.1F,
        .outputMin = -3.0F, .outputMax = 2.0F,  // m/s² acceleration limits
        .integralClamp = 10.0F
    });
    constexpr float kDt = 0.01F;  // 10 ms task period

    float accelCmd = distPid.Update(targetDist, currentDist, kDt);
    ApplyAcceleration(accelCmd);
}
```

### 11.3 Kalman Filter — Object Tracking

```cpp
// 1D Kalman filter for radar target range tracking
class KalmanFilter1D {
public:
    struct State {
        float position;   // estimated position
        float velocity;   // estimated velocity
        float P[2][2];    // error covariance matrix
    };

    // Process noise Q and measurement noise R
    KalmanFilter1D(float Q_pos, float Q_vel, float R_meas)
        : m_q_pos(Q_pos), m_q_vel(Q_vel), m_r(R_meas) {
        m_state = {0.0F, 0.0F, {{100.0F, 0.0F}, {0.0F, 100.0F}}};
    }

    // Predict step (dt in seconds)
    void Predict(float dt) {
        // State transition: x = F*x
        m_state.position += m_state.velocity * dt;

        // Update covariance: P = F*P*F' + Q
        float P00 = m_state.P[0][0] + dt * (m_state.P[1][0] + m_state.P[0][1])
                                     + dt * dt * m_state.P[1][1] + m_q_pos;
        float P01 = m_state.P[0][1] + dt * m_state.P[1][1];
        float P10 = m_state.P[1][0] + dt * m_state.P[1][1];
        float P11 = m_state.P[1][1] + m_q_vel;
        m_state.P[0][0] = P00;
        m_state.P[0][1] = P01;
        m_state.P[1][0] = P10;
        m_state.P[1][1] = P11;
    }

    // Update step with measurement z
    void Update(float z) {
        float S  = m_state.P[0][0] + m_r;  // innovation covariance
        float K0 = m_state.P[0][0] / S;    // Kalman gain position
        float K1 = m_state.P[1][0] / S;    // Kalman gain velocity

        float innovation = z - m_state.position;
        m_state.position += K0 * innovation;
        m_state.velocity += K1 * innovation;

        float P00_new = (1.0F - K0) * m_state.P[0][0];
        float P01_new = (1.0F - K0) * m_state.P[0][1];
        float P10_new = m_state.P[1][0] - K1 * m_state.P[0][0];
        float P11_new = m_state.P[1][1] - K1 * m_state.P[0][1];
        m_state.P[0][0] = P00_new;
        m_state.P[0][1] = P01_new;
        m_state.P[1][0] = P10_new;
        m_state.P[1][1] = P11_new;
    }

    float GetPosition() const { return m_state.position; }
    float GetVelocity() const { return m_state.velocity; }

private:
    State m_state;
    float m_q_pos, m_q_vel, m_r;
};
```

### 11.4 Lane Departure Warning — Cross-Track Error

```cpp
struct LaneMarker {
    float a, b, c;  // polynomial: y = a*x^2 + b*x + c
};

class LaneDepartureDetector {
public:
    struct Warning {
        bool  departing;
        float crossTrackError;  // meters, positive = right
        float lateralSpeed;     // m/s
    };

    Warning Evaluate(const LaneMarker& left, const LaneMarker& right,
                     float vehicleY, float vehicleYdot) {
        // Lane center at lookahead x = 20m
        constexpr float kLookahead = 20.0F;
        float leftY  = left.a * kLookahead * kLookahead
                     + left.b * kLookahead + left.c;
        float rightY = right.a * kLookahead * kLookahead
                     + right.b * kLookahead + right.c;
        float centerY = (leftY + rightY) * 0.5F;

        float cte = vehicleY - centerY;

        constexpr float kDepartureThresh = 0.3F;  // 30 cm
        bool departing = (std::abs(cte) > kDepartureThresh) &&
                         (std::abs(vehicleYdot) > 0.05F);

        return {departing, cte, vehicleYdot};
    }
};
```

---

## 12. Safety-Critical C++ — MISRA & ISO 26262

### 12.1 Key MISRA C++ 2008 Rules for ADAS

```cpp
// MISRA 5-2-6: Casts from base to derived must use static_cast
// MISRA 5-2-7: No cast between pointer to function and any other type
// MISRA 6-2-2: Floating-point expressions shall not be directly tested for equality
// MISRA 7-5-1: No function with non-void return type without return value
// MISRA 15-0-1: Exceptions shall only be used for exceptional circumstances
//               (often interpreted as: disable exceptions entirely)
// MISRA 17-0-2: Standard library shall not be re-used in safety-critical code
//               (reimplement or qualify each function used)

// Example violations and fixes:

// VIOLATION: float equality
float speed = ReadSpeed();
if (speed == 0.0F) {}  // MISRA 6-2-2 violation

// FIX: use epsilon comparison
constexpr float kEpsilon = 1e-5F;
if (std::abs(speed) < kEpsilon) {}

// VIOLATION: implicit conversion
uint8_t  byteVal = 255U;
uint16_t wordVal = byteVal;  // implicit promotion — may warn MISRA 5-0-3

// FIX: explicit cast
uint16_t wordVal2 = static_cast<uint16_t>(byteVal);

// VIOLATION: use of malloc/free
uint8_t* buf = static_cast<uint8_t*>(malloc(64));  // FORBIDDEN

// FIX: static array
static uint8_t buf[64U];
```

### 12.2 ISO 26262 — Software Architecture Patterns

```cpp
// Freedom from Interference — partitioned memory between ASILs
// ASIL-D: AEB braking core <-> ASIL-B: comfort features
// Use MPU (Memory Protection Unit) regions on ARM Cortex-M

// Defensive programming — every input must be range-checked
float ComputeBrakeForce(float decelReqMps2) {
    // Precondition check
    constexpr float kMinDecel = 0.0F;
    constexpr float kMaxDecel = 10.0F;  // m/s²
    if (decelReqMps2 < kMinDecel || decelReqMps2 > kMaxDecel) {
        ReportSafetyViolation(Safety::kInvalidInput);
        return 0.0F;  // safe default
    }
    return decelReqMps2 * kVehicleMass * kBrakeEfficiency;
}

// Software-level watchdog
class SoftwareWatchdog {
public:
    void Init(uint32_t timeoutMs) {
        m_timeout = timeoutMs;
        m_lastFeed = GetTickMs();
    }

    void Feed() {
        m_lastFeed = GetTickMs();
    }

    bool IsExpired() const {
        return (GetTickMs() - m_lastFeed) > m_timeout;
    }

    // Called by monitor task
    void Check() {
        if (IsExpired()) {
            TriggerSafeState();  // e.g., release brakes, alert driver
        }
    }

private:
    uint32_t m_timeout{0U};
    uint32_t m_lastFeed{0U};
};

// Dual-channel redundancy for ASIL-D
class RedundantBrakeCommand {
public:
    void SetChannel1(float value) { m_ch1 = value; }
    void SetChannel2(float value) { m_ch2 = value; }

    bool IsConsistent() const {
        constexpr float kMaxDelta = 0.5F;  // m/s²
        return std::abs(m_ch1 - m_ch2) < kMaxDelta;
    }

    float GetSafeValue() const {
        if (!IsConsistent()) {
            return 0.0F;   // fail-safe: no braking if channels disagree
        }
        return (m_ch1 + m_ch2) * 0.5F;
    }

private:
    float m_ch1{0.0F};
    float m_ch2{0.0F};
};
```

---

## 13. Testing & Validation of Embedded C++

### 13.1 Unit Testing with Google Test

```cpp
// test_pid_controller.cpp
#include <gtest/gtest.h>
#include "pid_controller.h"

class PidTest : public ::testing::Test {
protected:
    PidController::Config cfg{
        .kP = 1.0F, .kI = 0.0F, .kD = 0.0F,
        .outputMin = -10.0F, .outputMax = 10.0F,
        .integralClamp = 100.0F
    };
};

TEST_F(PidTest, ProportionalOnlyResponseIsCorrect) {
    PidController pid(cfg);
    // Setpoint=10, measured=0 → error=10 → output = kP * error = 10
    float out = pid.Update(10.0F, 0.0F, 0.01F);
    EXPECT_NEAR(out, 10.0F, 0.001F);
}

TEST_F(PidTest, OutputClampedAtMax) {
    PidController pid(cfg);
    float out = pid.Update(1000.0F, 0.0F, 0.01F);
    EXPECT_EQ(out, 10.0F);  // clamped at outputMax
}

TEST_F(PidTest, ZeroErrorGivesZeroOutput) {
    PidController pid(cfg);
    float out = pid.Update(5.0F, 5.0F, 0.01F);
    EXPECT_NEAR(out, 0.0F, 0.001F);
}

TEST_F(PidTest, ResetClearsIntegral) {
    cfg.kI = 1.0F;
    PidController pid(cfg);
    pid.Update(1.0F, 0.0F, 1.0F);  // accumulate integral
    pid.Reset();
    float out = pid.Update(0.0F, 0.0F, 1.0F);  // error=0, integral=0
    EXPECT_NEAR(out, 0.0F, 0.001F);
}
```

### 13.2 Hardware-In-Loop (HIL) C++ Interface

```cpp
// SUT adapter pattern — same interface for SIL and HIL
class IVehicleBus {
public:
    virtual ~IVehicleBus() = default;
    virtual bool SendCanFrame(const CanFrame& frame) = 0;
    virtual bool ReceiveCanFrame(CanFrame& frame, uint32_t timeoutMs) = 0;
};

// SIL: in-process simulation bus
class VirtualBus : public IVehicleBus {
public:
    bool SendCanFrame(const CanFrame& frame) override {
        m_sentFrames.push_back(frame);
        return true;
    }
    bool ReceiveCanFrame(CanFrame& frame, uint32_t) override {
        if (m_injectFrames.empty()) return false;
        frame = m_injectFrames.front();
        m_injectFrames.pop_front();
        return true;
    }
    std::vector<CanFrame>    m_sentFrames;
    std::deque<CanFrame>     m_injectFrames;
};

// HIL: real Vector VN1610 hardware channel
class VectorCanBus : public IVehicleBus {
public:
    bool SendCanFrame(const CanFrame& frame) override {
        // xlCanTransmit(...) via Vector XL-Driver
        return true;
    }
    bool ReceiveCanFrame(CanFrame& frame, uint32_t timeoutMs) override {
        // xlCanReceive(...) with timeout
        return false;
    }
};
```

### 13.3 Code Coverage in Embedded

```bash
# GCC coverage flags for host-based unit tests
arm-none-eabi-g++ -O0 --coverage -fprofile-arcs -ftest-coverage \
    -o test_pid test_pid.cpp pid_controller.cpp

# Run tests
./test_pid

# Generate coverage report
gcov pid_controller.cpp
lcov --capture --directory . --output-file coverage.info
genhtml coverage.info --output-directory coverage_html
```

---

## 14. Build Systems, Toolchains & Cross-Compilation

### 14.1 CMakeLists.txt for ARM Cortex-M Target

```cmake
cmake_minimum_required(VERSION 3.20)
project(AdasEcu CXX C ASM)

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

# ARM GCC toolchain
set(CMAKE_CXX_COMPILER arm-none-eabi-g++)
set(CMAKE_C_COMPILER   arm-none-eabi-gcc)
set(CMAKE_ASM_COMPILER arm-none-eabi-as)
set(CMAKE_OBJCOPY      arm-none-eabi-objcopy)
set(CMAKE_SIZE         arm-none-eabi-size)

# Cortex-M4 with FPU
set(CPU_FLAGS "-mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard")

set(CMAKE_CXX_FLAGS "${CPU_FLAGS} \
    -std=c++17 \
    -Wall -Wextra -Werror \
    -fno-exceptions \
    -fno-rtti \
    -fno-use-cxa-atexit \
    -ffunction-sections \
    -fdata-sections \
    -Os")

set(CMAKE_EXE_LINKER_FLAGS "${CPU_FLAGS} \
    -T${CMAKE_SOURCE_DIR}/linker/stm32f446re.ld \
    -Wl,--gc-sections \
    -Wl,-Map=output.map \
    --specs=nano.specs")

include_directories(
    include/
    drivers/
    middleware/
    ${CMAKE_SOURCE_DIR}/../third_party/FreeRTOS/include
)

add_executable(adas_ecu.elf
    src/main.cpp
    src/adas/aeb_controller.cpp
    src/adas/acc_controller.cpp
    src/drivers/can_driver.cpp
    src/drivers/adc_driver.cpp
    src/os/rtos_tasks.cpp
)

# Post-build: generate .bin and print size
add_custom_command(TARGET adas_ecu.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary 
        $<TARGET_FILE:adas_ecu.elf> adas_ecu.bin
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:adas_ecu.elf>
)
```

### 14.2 Compiler Flags Explained

```
-mcpu=cortex-m4          : Target CPU (also: cortex-m0, cortex-m7, cortex-a55)
-mfpu=fpv4-sp-d16        : FPU type (fpv5-d16 for M7, none for M0)
-mfloat-abi=hard         : Use hardware FPU registers (fastest)
-mfloat-abi=soft         : Software float emulation (slowest, portable)
-mfloat-abi=softfp       : ABI-compatible but uses FPU instructions
-fno-exceptions          : Disable C++ exception machinery (reduces code size)
-fno-rtti                : Disable runtime type information (RTTI)
-ffunction-sections      : One ELF section per function (enables dead-code removal)
-fdata-sections          : One ELF section per data item
-Wl,--gc-sections        : Linker removes unreferenced sections
-Os                      : Optimize for size
-O2                      : Optimize for speed (use with profiling)
-flto                    : Link-time optimisation
-DNDEBUG                 : Disable assert() in release
```

---

## 15. Performance Optimization for ECU Targets

### 15.1 Cache-Friendly Data Layout

```cpp
// BAD: struct layout causes cache thrashing for array iteration
struct TargetBad {
    uint32_t id;             // 4 bytes
    float    position[3];   // 12 bytes
    float    velocity[3];   // 12 bytes
    char     label[32];     // 32 bytes  — total: 60 bytes
};
TargetBad targets[100];
// Iterating just positions → load 60-byte struct to access 12 bytes

// GOOD: struct of arrays — cache-efficient for vectorization
struct TargetArrays {
    uint32_t ids[100];
    float    posX[100], posY[100], posZ[100];
    float    velX[100], velY[100], velZ[100];
};
// Iterating positions → contiguous 400-byte load
```

### 15.2 Avoiding Branching in Hot Paths

```cpp
// Replace conditional with arithmetic (no branch misprediction)
// BAD:
float ClampBad(float v, float lo, float hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

// Better with branchless (if compiler doesn't already optimize):
float ClampGood(float v, float lo, float hi) {
    v = v < lo ? lo : v;  // compiler may use conditional move (FCSEL on ARM)
    v = v > hi ? hi : v;
    return v;
}
// On ARM Cortex-M with FPU, VMAX.F32 / VMIN.F32 instructions will be used
```

### 15.3 Fixed-Point Arithmetic for MCUs Without FPU

```cpp
// Fixed-point Q8.8 format: 8 integer bits, 8 fractional bits
// Range: -128.0 to 127.996
using Fixed16 = int16_t;
constexpr int16_t kFixedShift = 8;
constexpr int16_t kFixedOne   = 1 << kFixedShift;  // 256

inline Fixed16 FloatToFixed(float f) {
    return static_cast<Fixed16>(f * static_cast<float>(kFixedOne));
}
inline float FixedToFloat(Fixed16 f) {
    return static_cast<float>(f) / static_cast<float>(kFixedOne);
}
inline Fixed16 FixedMul(Fixed16 a, Fixed16 b) {
    return static_cast<Fixed16>((static_cast<int32_t>(a) * b) >> kFixedShift);
}

// PID in fixed-point — 10x faster on Cortex-M0 (no FPU)
Fixed16 pid_p = FloatToFixed(0.5F);
Fixed16 error = FloatToFixed(3.7F);
Fixed16 output = FixedMul(pid_p, error);
// output ≈ 1.85 in fixed-point
```

---

## 16. Common Patterns & Anti-Patterns

### 16.1 Good Patterns

```
GOOD PATTERNS:
╔══════════════════════════════════════════════════════════════╗
║ Pattern               │ Use Case                           ║
╠══════════════════════════════════════════════════════════════╣
║ RAII                  │ ISR masking, mutex, GPIO           ║
║ State Machine         │ ADAS mode management, gear shift   ║
║ Observer / Callback   │ CAN signal notification            ║
║ Strategy (Template)   │ Swappable algorithms (filter, PID) ║
║ Facade                │ Hide HAL complexity behind simple  ║
║                       │ interface                          ║
║ Command               │ Actuator command queuing           ║
║ Singleton             │ Shared managers (use sparingly)    ║
║ Object Pool           │ Frame buffers, message blocks      ║
╚══════════════════════════════════════════════════════════════╝
```

### 16.2 Anti-Patterns to Avoid

```cpp
// ANTI-PATTERN 1: Using new/delete in production ECU code
void ProcessFrame() {
    uint8_t* buf = new uint8_t[256];  // FORBIDDEN in ECU
    // ...
    delete[] buf;
}

// ANTI-PATTERN 2: Blocking in ISR
void UART_IRQHandler() {
    HAL_Delay(10);  // DEADLOCK! Delay uses SysTick, blocked by ISR
}

// ANTI-PATTERN 3: Global state modified from multiple tasks without sync
uint32_t g_sharedCounter = 0U;
void Task1() { ++g_sharedCounter; }  // race condition
void Task2() { ++g_sharedCounter; }  // race condition

// ANTI-PATTERN 4: Using printf in production
void DiagTask() {
    printf("Speed: %f km/h\n", speed);  // huge code, blocks, non-deterministic
}
// Use: circular log buffer, DMA-based UART, RTT (Segger Real-Time Transfer)

// ANTI-PATTERN 5: Deep inheritance hierarchies
class Sensor {};
class AnalogSensor : public Sensor {};
class TemperatureSensor : public AnalogSensor {};
class CoolantTempSensor : public TemperatureSensor {};
class HeatedCoolantSensor : public CoolantTempSensor {};
// → Prefer composition over deep inheritance

// ANTI-PATTERN 6: Copying large objects by value
void HandleFrame(CanFrame frame) {}  // copies 16 bytes — OK but...
void HandleSensorData(SensorData data) {}  // copies 1024 bytes — BAD
// Fix: pass by const reference
void HandleSensorData(const SensorData& data) {}
```

---

## 17. Complete Code Examples by Domain

### 17.1 Full AEB (Automatic Emergency Braking) Module

```cpp
// aeb_controller.h
#pragma once
#include <cstdint>
#include <cmath>

struct RadarTarget {
    float rangeM;
    float relVelocityMps;
    float azimuthDeg;
    bool  valid;
};

enum class AebPhase : uint8_t {
    Inactive = 0U,
    PreWarning,
    Warning,
    PartialBrake,
    FullBrake
};

class AebController {
public:
    struct Config {
        float preWarnTtcS   = 3.5F;
        float warnTtcS      = 2.5F;
        float partialBrakeS = 1.8F;
        float fullBrakeS    = 1.2F;
        float maxDecelMps2  = 9.8F;
    };

    explicit AebController(const Config& cfg = {}) : m_cfg(cfg) {}

    void Update(const RadarTarget& target, float egoSpeedMps) {
        if (!target.valid || egoSpeedMps < 1.0F) {
            m_phase = AebPhase::Inactive;
            m_decelCmd = 0.0F;
            return;
        }

        float ttc = ComputeTtc(target);

        if      (ttc < m_cfg.fullBrakeS)    TransitionTo(AebPhase::FullBrake);
        else if (ttc < m_cfg.partialBrakeS) TransitionTo(AebPhase::PartialBrake);
        else if (ttc < m_cfg.warnTtcS)      TransitionTo(AebPhase::Warning);
        else if (ttc < m_cfg.preWarnTtcS)   TransitionTo(AebPhase::PreWarning);
        else                                 TransitionTo(AebPhase::Inactive);

        m_decelCmd = ComputeDecelCommand(ttc);
    }

    AebPhase GetPhase()    const { return m_phase; }
    float    GetDecelCmd() const { return m_decelCmd; }
    bool     IsActive()    const { return m_phase >= AebPhase::PartialBrake; }

private:
    float ComputeTtc(const RadarTarget& t) const {
        if (t.relVelocityMps >= 0.0F) return 99.0F;
        return -t.rangeM / t.relVelocityMps;
    }

    float ComputeDecelCommand(float ttc) const {
        if (m_phase == AebPhase::FullBrake)    return m_cfg.maxDecelMps2;
        if (m_phase == AebPhase::PartialBrake) {
            float factor = (m_cfg.partialBrakeS - ttc) /
                           (m_cfg.partialBrakeS - m_cfg.fullBrakeS);
            return factor * m_cfg.maxDecelMps2 * 0.6F;
        }
        return 0.0F;
    }

    void TransitionTo(AebPhase next) {
        if (m_phase != next) {
            m_phase = next;
            OnPhaseEntry(next);
        }
    }

    void OnPhaseEntry(AebPhase phase) {
        (void)phase;
        // Log DTC, trigger HMI notification, etc.
    }

    Config   m_cfg;
    AebPhase m_phase{AebPhase::Inactive};
    float    m_decelCmd{0.0F};
};
```

### 17.2 CAN Gateway Module

```cpp
// can_gateway.h — routes frames between two CAN buses
#pragma once

class CanGateway {
public:
    struct RoutingRule {
        uint32_t srcId;       // CAN ID to match
        uint32_t destId;      // CAN ID to transmit on destination bus
        uint8_t  busIndex;    // destination bus (0 or 1)
        float    factor;      // signal scaling (1.0 = no scale)
        bool     active;
    };

    static constexpr uint8_t kMaxRules = 32U;

    void AddRule(const RoutingRule& rule) {
        if (m_ruleCount < kMaxRules) {
            m_rules[m_ruleCount++] = rule;
        }
    }

    // Call from CAN RX callback with source bus index
    void OnFrameReceived(uint8_t srcBus, const CanFrame& frame) {
        for (uint8_t i = 0U; i < m_ruleCount; ++i) {
            const RoutingRule& rule = m_rules[i];
            if (rule.active && rule.srcId == frame.id) {
                CanFrame routed = frame;
                routed.id = rule.destId;
                if (rule.factor != 1.0F) {
                    ApplyScaling(routed, rule.factor);
                }
                (void)srcBus;
                TransmitFrame(rule.busIndex, routed);
            }
        }
    }

private:
    void ApplyScaling(CanFrame& frame, float factor) {
        // Simplified: scale first 2 bytes as uint16
        uint16_t raw;
        memcpy(&raw, frame.data, 2U);
        raw = static_cast<uint16_t>(static_cast<float>(raw) * factor);
        memcpy(frame.data, &raw, 2U);
    }

    void TransmitFrame(uint8_t bus, const CanFrame& frame);

    RoutingRule m_rules[kMaxRules]{};
    uint8_t     m_ruleCount{0U};
};
```

---

## Quick Reference Card

| Topic                      | Key Class / Pattern          | File Section   |
|----------------------------|------------------------------|----------------|
| Fixed-width types          | `uint8_t`, `int32_t`         | §2.1           |
| Compile-time constants     | `constexpr`                  | §2.2           |
| Safe enumerations          | `enum class`                 | §2.3           |
| Hardware registers         | `volatile`                   | §2.6           |
| No heap / pools            | `MemPool<T,N>`               | §3.3           |
| ISR-safe buffer            | `RingBuffer<T,N>`            | §3.4           |
| Hardware abstraction       | `ICanTransceiver`, `IGpio`   | §4.2, §7.2     |
| RAII                       | `CriticalSection`, `LockGuard` | §4.3, §6.2   |
| State machine              | `AdasStateMachine`           | §4.5           |
| Generic typed buffer       | `Array<T,N>`                 | §5.2           |
| Physical units safety      | `StrongType<Tag,T>`          | §5.3           |
| RTOS task                  | `RtosTask`                   | §6.1           |
| ISR rules                  | `extern "C"`, `volatile`     | §7.1           |
| CAN encoding               | `CanSignalCodec`             | §8.1           |
| UDS dispatcher             | `UdsDispatcher`              | §9.1           |
| PID controller             | `PidController`              | §11.2          |
| Kalman filter              | `KalmanFilter1D`             | §11.3          |
| MISRA compliance           | epsilon compare, explicit cast | §12.1        |
| Unit testing               | Google Test patterns         | §13.1          |
| CMake cross-compile        | ARM toolchain setup          | §14.1          |
| Fixed-point math           | `Fixed16`, `FixedMul`        | §15.3          |

---

*Document Version: 1.0 — May 2026*
*Standards Referenced: ISO 26262:2018, MISRA C++:2008, AUTOSAR R22-11, ISO 14229-1:2020*
