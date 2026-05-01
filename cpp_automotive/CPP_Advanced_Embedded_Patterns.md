# Advanced C++ Patterns for Automotive Embedded Systems

> Companion to: `CPP_Embedded_ADAS_ECU_Complete_Guide.md`
> Focus: Modern C++17 idioms, metaprogramming, advanced RTOS usage, AUTOSAR code patterns, security

---

## Table of Contents

1. [Policy-Based Design for Drivers](#1-policy-based-design-for-drivers)
2. [Compile-Time Dispatch — `if constexpr`](#2-compile-time-dispatch--if-constexpr)
3. [Variadic Templates for CAN Signal Packing](#3-variadic-templates-for-can-signal-packing)
4. [Type Erasure for Callback Registration](#4-type-erasure-for-callback-registration)
5. [Operator Overloading for DSP Types](#5-operator-overloading-for-dsp-types)
6. [CRTP — Curiously Recurring Template Pattern](#6-crtp--curiously-recurring-template-pattern)
7. [Move Semantics in Embedded Context](#7-move-semantics-in-embedded-context)
8. [std::optional Replacement for Embedded](#8-stdoptional-replacement-for-embedded)
9. [Static Polymorphism vs Runtime Polymorphism](#9-static-polymorphism-vs-runtime-polymorphism)
10. [Advanced RTOS Patterns](#10-advanced-rtos-patterns)
11. [Memory-Mapped Register Classes](#11-memory-mapped-register-classes)
12. [CRC & Checksum Utilities](#12-crc--checksum-utilities)
13. [Logging System for ECU](#13-logging-system-for-ecu)
14. [Bootloader & Flash Programming](#14-bootloader--flash-programming)
15. [Cybersecurity Patterns — SecOC in C++](#15-cybersecurity-patterns--secoc-in-c)
16. [Sensor Fusion Architecture](#16-sensor-fusion-architecture)
17. [Interview Questions & Answers](#17-interview-questions--answers)

---

## 1. Policy-Based Design for Drivers

```cpp
// Combine multiple independent policies at compile time
// No virtual dispatch — policies resolved at compile time

// Checksum policies
struct NullChecksum {
    static uint8_t Compute(const uint8_t*, uint16_t) { return 0U; }
    static bool    Verify (const uint8_t*, uint16_t, uint8_t) { return true; }
};

struct XorChecksum {
    static uint8_t Compute(const uint8_t* data, uint16_t len) {
        uint8_t cs = 0U;
        for (uint16_t i = 0U; i < len; ++i) cs ^= data[i];
        return cs;
    }
    static bool Verify(const uint8_t* data, uint16_t len, uint8_t expected) {
        return Compute(data, len) == expected;
    }
};

// Framing policies
struct SlipFraming {
    static constexpr uint8_t kEnd = 0xC0U;
    static uint16_t Encode(const uint8_t* in, uint16_t inLen,
                           uint8_t* out, uint16_t outMax) {
        uint16_t pos = 0U;
        out[pos++] = kEnd;
        for (uint16_t i = 0U; i < inLen && pos < outMax - 1U; ++i) {
            if (in[i] == 0xC0U) { out[pos++] = 0xDBU; out[pos++] = 0xDCU; }
            else if (in[i] == 0xDBU) { out[pos++] = 0xDBU; out[pos++] = 0xDDU; }
            else out[pos++] = in[i];
        }
        out[pos++] = kEnd;
        return pos;
    }
};

// Combined driver using policies
template<typename ChecksumPolicy, typename FramingPolicy>
class SerialProtocol {
public:
    bool Send(const uint8_t* payload, uint16_t len) {
        uint8_t buf[256];
        uint8_t cs = ChecksumPolicy::Compute(payload, len);
        buf[0] = cs;
        memcpy(buf + 1U, payload, len);

        uint8_t framed[300];
        uint16_t framedLen = FramingPolicy::Encode(buf, len + 1U, framed, 300U);
        return UartSend(framed, framedLen);
    }

private:
    bool UartSend(const uint8_t* data, uint16_t len);
};

// Instantiations — zero cost abstraction
using SafeSerial  = SerialProtocol<XorChecksum, SlipFraming>;
using FastSerial  = SerialProtocol<NullChecksum, SlipFraming>;
```

---

## 2. Compile-Time Dispatch — `if constexpr`

```cpp
#include <type_traits>

// Different behavior based on type — resolved at compile time
template<typename T>
void SerializeTo(uint8_t* buf, const T& value) {
    if constexpr (std::is_same_v<T, float>) {
        // IEEE 754 float serialization
        uint32_t raw;
        memcpy(&raw, &value, 4U);
        buf[0] = (raw >> 24U) & 0xFFU;
        buf[1] = (raw >> 16U) & 0xFFU;
        buf[2] = (raw >>  8U) & 0xFFU;
        buf[3] =  raw         & 0xFFU;
    } else if constexpr (std::is_integral_v<T> && sizeof(T) == 2U) {
        buf[0] = (value >> 8U) & 0xFFU;
        buf[1] =  value        & 0xFFU;
    } else if constexpr (std::is_integral_v<T> && sizeof(T) == 4U) {
        buf[0] = (value >> 24U) & 0xFFU;
        buf[1] = (value >> 16U) & 0xFFU;
        buf[2] = (value >>  8U) & 0xFFU;
        buf[3] =  value         & 0xFFU;
    } else {
        static_assert(sizeof(T) == 0, "Unsupported type for serialization");
    }
}

// Usage — correct code path selected at compile time
uint8_t buf[4];
SerializeTo(buf, 3.14F);        // uses float path
SerializeTo(buf, uint16_t{100}); // uses 2-byte path
SerializeTo(buf, uint32_t{500}); // uses 4-byte path
```

---

## 3. Variadic Templates for CAN Signal Packing

```cpp
// Recursive variadic template to pack multiple signals in one call

// Base case
void PackSignals(uint8_t* /*data*/) {}

// Recursive case
template<typename First, typename... Rest>
void PackSignals(uint8_t* data,
                 uint8_t startBit, uint8_t length, First value,
                 Rest... rest) {
    uint64_t raw = static_cast<uint64_t>(value);
    for (uint8_t i = 0U; i < length; ++i) {
        uint8_t bitPos = startBit + i;
        if (raw & (1ULL << i)) {
            data[bitPos / 8U] |=  (1U << (bitPos % 8U));
        } else {
            data[bitPos / 8U] &= ~(1U << (bitPos % 8U));
        }
    }
    PackSignals(data, rest...);
}

// Usage: pack speed (bits 0-15), temperature (bits 16-23), status (bits 24-27)
uint8_t frame[8]{};
PackSignals(frame,
    0U,  16U, uint16_t{12000},  // speed raw = 120.00 kmh * 100
    16U,  8U, uint8_t{85},      // temperature 85°C
    24U,  4U, uint8_t{0x5});    // status nibble
```

---

## 4. Type Erasure for Callback Registration

```cpp
// Function<> — small, heap-free callback holder
// Replaces std::function (which uses heap allocation)

template<typename Sig, uint8_t StorageBytes = 16U>
class Function;

template<typename Ret, typename... Args, uint8_t StorageBytes>
class Function<Ret(Args...), StorageBytes> {
public:
    Function() = default;

    // Lambda or functor — must fit in StorageBytes
    template<typename F>
    Function(F&& f) {
        static_assert(sizeof(F) <= StorageBytes, "Functor too large for storage");
        new (m_storage) F(std::forward<F>(f));
        m_invoke = [](void* storage, Args... args) -> Ret {
            return (*reinterpret_cast<F*>(storage))(std::forward<Args>(args)...);
        };
        m_destroy = [](void* storage) {
            reinterpret_cast<F*>(storage)->~F();
        };
    }

    ~Function() {
        if (m_destroy) m_destroy(m_storage);
    }

    Ret operator()(Args... args) const {
        return m_invoke(const_cast<void*>(
            static_cast<const void*>(m_storage)),
            std::forward<Args>(args)...);
    }

    explicit operator bool() const { return m_invoke != nullptr; }

private:
    alignas(std::max_align_t) uint8_t m_storage[StorageBytes]{};
    Ret (*m_invoke)(void*, Args...)   = nullptr;
    void (*m_destroy)(void*)          = nullptr;
};

// Usage
Function<void(const CanFrame&)> onCanRx;
onCanRx = [](const CanFrame& f) {
    // handle frame
    (void)f;
};

// Register in driver
class CanDriver {
public:
    void SetRxCallback(Function<void(const CanFrame&)> cb) {
        m_rxCallback = cb;
    }
private:
    Function<void(const CanFrame&)> m_rxCallback;
};
```

---

## 5. Operator Overloading for DSP Types

```cpp
// Vector2D for lateral control algorithms
struct Vec2 {
    float x, y;

    Vec2 operator+(const Vec2& o)  const { return {x + o.x, y + o.y}; }
    Vec2 operator-(const Vec2& o)  const { return {x - o.x, y - o.y}; }
    Vec2 operator*(float s)        const { return {x * s, y * s}; }
    Vec2& operator+=(const Vec2& o) { x += o.x; y += o.y; return *this; }

    float Dot(const Vec2& o) const { return x * o.x + y * o.y; }
    float Norm()             const { return std::sqrt(x*x + y*y); }
    Vec2  Normalized()       const {
        float n = Norm();
        return (n > 1e-6F) ? Vec2{x/n, y/n} : Vec2{0.0F, 0.0F};
    }
    float Cross(const Vec2& o) const { return x * o.y - y * o.x; }
};

// Q-number class for fixed-point arithmetic
template<int8_t FractBits>
class QNum {
public:
    using Raw = int16_t;
    static constexpr Raw kScale = 1 << FractBits;

    explicit QNum(float f) : m_raw(static_cast<Raw>(f * kScale)) {}
    explicit QNum(Raw r) : m_raw(r) {}

    float ToFloat() const { return static_cast<float>(m_raw) / kScale; }
    Raw   RawValue() const { return m_raw; }

    QNum operator+(const QNum& o) const { return QNum(static_cast<Raw>(m_raw + o.m_raw)); }
    QNum operator-(const QNum& o) const { return QNum(static_cast<Raw>(m_raw - o.m_raw)); }
    QNum operator*(const QNum& o) const {
        int32_t result = (static_cast<int32_t>(m_raw) * o.m_raw) >> FractBits;
        return QNum(static_cast<Raw>(result));
    }
    bool operator<(const QNum& o) const { return m_raw < o.m_raw; }
    bool operator>(const QNum& o) const { return m_raw > o.m_raw; }

private:
    Raw m_raw;
};

using Q8_8 = QNum<8>;   // range ±127.996, resolution 0.00390625
using Q4_12 = QNum<12>; // range ±7.9997, resolution 0.000244
```

---

## 6. CRTP — Curiously Recurring Template Pattern

```cpp
// CRTP — static polymorphism without virtual table overhead
// Used in AUTOSAR NvM, COM, and diagnostic handlers

// Base provides common interface and calls derived implementation
template<typename Derived>
class SensorBase {
public:
    bool Init() {
        return static_cast<Derived*>(this)->InitImpl();
    }

    float Read() {
        float raw = static_cast<Derived*>(this)->ReadRawImpl();
        return ApplyCalibration(raw);
    }

    bool IsValid() const {
        return static_cast<const Derived*>(this)->IsValidImpl();
    }

protected:
    float ApplyCalibration(float raw) {
        return raw * m_gain + m_offset;
    }

    float m_gain{1.0F};
    float m_offset{0.0F};
};

// Derived — provides concrete impl
class ThermistorSensor : public SensorBase<ThermistorSensor> {
public:
    bool  InitImpl()    { /* ADC init */ return true; }
    float ReadRawImpl() { return ReadADC(m_channel) * 3.3F / 4095.0F; }
    bool  IsValidImpl() const { return m_valid; }

private:
    uint8_t m_channel{0U};
    bool    m_valid{true};
};

class PressureSensor : public SensorBase<PressureSensor> {
public:
    bool  InitImpl()    { /* SPI init */ return true; }
    float ReadRawImpl() { /* SPI read */ return 0.0F; }
    bool  IsValidImpl() const { return true; }
};

// No virtual call — compiler inlines derived impl
ThermistorSensor therm;
float temp = therm.Read();  // no vtable lookup
```

---

## 7. Move Semantics in Embedded Context

```cpp
// Move semantics reduce copies for heap-free objects

// Movable large struct
struct SensorSnapshot {
    uint32_t timestamp;
    float    data[64];
    uint8_t  sensorId;

    // User-defined move constructor (avoids deep copy of 256 bytes)
    SensorSnapshot(SensorSnapshot&& other) noexcept
        : timestamp(other.timestamp), sensorId(other.sensorId) {
        memcpy(data, other.data, sizeof(data));
        other.sensorId = 0U;  // mark as moved-from
    }

    SensorSnapshot& operator=(SensorSnapshot&& other) noexcept {
        if (this != &other) {
            timestamp = other.timestamp;
            sensorId  = other.sensorId;
            memcpy(data, other.data, sizeof(data));
            other.sensorId = 0U;
        }
        return *this;
    }
};

// In a process pipeline:
SensorSnapshot Capture();  // returns by value — NRVO or move

void Pipeline() {
    SensorSnapshot snap = Capture();        // NRVO — no copy
    ProcessSnapshot(std::move(snap));        // explicit move — no copy
    // snap is now in moved-from state
}

// Move-only handle to hardware resource
class DmaHandle {
public:
    explicit DmaHandle(uint8_t channel) : m_channel(channel) { AcquireDma(channel); }
    ~DmaHandle() { if (m_channel != 0xFFU) ReleaseDma(m_channel); }

    // Non-copyable (one owner)
    DmaHandle(const DmaHandle&) = delete;
    DmaHandle& operator=(const DmaHandle&) = delete;

    // Movable (transfer ownership)
    DmaHandle(DmaHandle&& o) noexcept : m_channel(o.m_channel) { o.m_channel = 0xFFU; }
    DmaHandle& operator=(DmaHandle&& o) noexcept {
        if (this != &o) {
            if (m_channel != 0xFFU) ReleaseDma(m_channel);
            m_channel = o.m_channel;
            o.m_channel = 0xFFU;
        }
        return *this;
    }

private:
    uint8_t m_channel;
};
```

---

## 8. `std::optional` Replacement for Embedded

```cpp
// std::optional uses heap? No — it's stack-allocated.
// But it may pull in heavy headers; this is a minimal version.

template<typename T>
class Optional {
public:
    Optional() : m_hasValue(false) {}

    explicit Optional(const T& value) : m_hasValue(true) {
        new (m_storage) T(value);
    }

    ~Optional() { Reset(); }

    Optional(const Optional& o) : m_hasValue(o.m_hasValue) {
        if (m_hasValue) new (m_storage) T(*o);
    }

    void Reset() {
        if (m_hasValue) {
            reinterpret_cast<T*>(m_storage)->~T();
            m_hasValue = false;
        }
    }

    bool HasValue() const { return m_hasValue; }
    explicit operator bool() const { return m_hasValue; }

    T& Value() {
        // assert(m_hasValue);
        return *reinterpret_cast<T*>(m_storage);
    }
    const T& Value() const {
        return *reinterpret_cast<const T*>(m_storage);
    }

    T& operator*()       { return Value(); }
    const T& operator*() const { return Value(); }
    T* operator->()      { return &Value(); }

private:
    alignas(T) uint8_t m_storage[sizeof(T)]{};
    bool m_hasValue;
};

// Usage — express absence of value cleanly
Optional<RadarTarget> FindClosestTarget(const RadarTarget* targets, uint8_t count) {
    if (count == 0U) return Optional<RadarTarget>{};
    // find minimum range target
    uint8_t minIdx = 0U;
    for (uint8_t i = 1U; i < count; ++i) {
        if (targets[i].rangeM < targets[minIdx].rangeM) minIdx = i;
    }
    return Optional<RadarTarget>{targets[minIdx]};
}

void ProcessTargets() {
    auto closest = FindClosestTarget(g_targets, g_targetCount);
    if (closest) {
        float ttc = closest->rangeM / (-closest->relVelocityMps);
        (void)ttc;
    }
}
```

---

## 9. Static Polymorphism vs Runtime Polymorphism

```cpp
// Benchmark context: ARM Cortex-M4 @ 168 MHz
//
// Virtual call overhead:
//   - Load vtable pointer: 1 cycle
//   - Load function pointer: 1 cycle
//   - Branch to function: 1 cycle (if in branch predictor) + pipeline flush
//   - Total overhead: ~3-5 cycles per call
//   - If function NOT cached: cache miss → 8-50 extra cycles!
//
// Template (compile-time) call:
//   - Inlined → 0 overhead
//   - Or direct call → 1 cycle (no indirection)

// USE VIRTUAL when:
//   1. You need runtime selection (different hardware variants at runtime)
//   2. Objects stored in heterogeneous containers
//   3. Interface shared across module boundaries (ABI stable)
//   4. Called infrequently (not in 1ms tight loop)

// USE TEMPLATES when:
//   1. Variant known at compile time
//   2. Hot path — called in ISR or periodic 1ms task
//   3. No need for heterogeneous containers

// Practical rule for ADAS ECU:
//   - Driver HAL interfaces: use virtual (hardware differs between targets)
//   - Algorithm internals: use templates (PID, filter, state machine)
//   - RTOS wrappers: mix (template for type safety, virtual for mockability)

// Example: Algorithm with template policy, injectable hardware via interface
template<typename FilterPolicy>
class RadarProcessor {
public:
    explicit RadarProcessor(IRadarHardware& hw) : m_hw(hw) {}

    float GetFilteredRange() {
        float raw = m_hw.ReadRangeM();    // virtual call — OK, once per cycle
        return m_filter.Apply(raw);        // inlined — no overhead
    }

private:
    IRadarHardware& m_hw;           // runtime: real or mock
    FilterPolicy    m_filter;        // compile-time: filter algorithm
};
```

---

## 10. Advanced RTOS Patterns

### 10.1 Active Object Pattern

```cpp
// Active Object: encapsulates task + message queue
// All state mutation happens inside the object's task — no external sync needed

template<typename MsgType, uint8_t QueueDepth>
class ActiveObject {
public:
    ActiveObject(const char* name, uint16_t stackWords, uint8_t priority)
        : m_task(name, stackWords, priority, [this]() { TaskBody(); }) {}

    bool Post(const MsgType& msg) {
        return m_queue.Send(msg, 0U);
    }

    virtual ~ActiveObject() = default;

protected:
    virtual void HandleMessage(const MsgType& msg) = 0;

private:
    void TaskBody() {
        while (true) {
            MsgType msg;
            if (m_queue.Receive(msg)) {
                HandleMessage(msg);
            }
        }
    }

    MessageQueue<MsgType, QueueDepth> m_queue;
    LambdaTask                         m_task;
};

// Concrete active object — thread-safe without external locks
struct AdasCommand {
    enum class Type { Enable, Disable, SetTarget } type;
    float param;
};

class AdasActiveObject : public ActiveObject<AdasCommand, 8U> {
public:
    AdasActiveObject()
        : ActiveObject("ADAS_AO", 512U, 5U) {}

protected:
    void HandleMessage(const AdasCommand& cmd) override {
        switch (cmd.type) {
            case AdasCommand::Type::Enable:  m_sm.HandleEvent(AdasEvent::DriverEnable); break;
            case AdasCommand::Type::Disable: m_sm.HandleEvent(AdasEvent::DriverCancel); break;
            case AdasCommand::Type::SetTarget: m_targetSpeed = cmd.param; break;
        }
    }

private:
    AdasStateMachine m_sm;
    float            m_targetSpeed{0.0F};
};
```

### 10.2 Periodic Timer with Drift Compensation

```cpp
class PeriodicTimer {
public:
    PeriodicTimer(uint32_t periodMs) : m_period(pdMS_TO_TICKS(periodMs)) {
        m_lastWakeTime = xTaskGetTickCount();
    }

    void WaitForNextPeriod() {
        // vTaskDelayUntil — compensates for execution time drift
        vTaskDelayUntil(&m_lastWakeTime, m_period);
    }

private:
    TickType_t m_period;
    TickType_t m_lastWakeTime;
};

// Usage in task — 10 ms periodic with drift compensation
void AebTask(void*) {
    PeriodicTimer timer{10U};
    while (true) {
        timer.WaitForNextPeriod();
        // This runs exactly every 10 ms regardless of execution time
        RunAebCycle();
    }
}
```

### 10.3 Watchdog Task Pattern

```cpp
// Software watchdog: tracks liveness of all registered tasks
class TaskWatchdog {
public:
    static constexpr uint8_t kMaxTasks = 16U;

    uint8_t Register(const char* name, uint32_t maxPeriodMs) {
        if (m_count >= kMaxTasks) return 0xFFU;
        uint8_t id = m_count++;
        m_entries[id] = { name, maxPeriodMs, GetTickMs(), false };
        return id;
    }

    void Kick(uint8_t taskId) {
        if (taskId < m_count) {
            m_entries[taskId].lastKick = GetTickMs();
            m_entries[taskId].healthy = true;
        }
    }

    // Called from dedicated monitor task every 1 ms
    void Monitor() {
        uint32_t now = GetTickMs();
        for (uint8_t i = 0U; i < m_count; ++i) {
            auto& e = m_entries[i];
            if ((now - e.lastKick) > e.maxPeriodMs) {
                if (e.healthy) {
                    e.healthy = false;
                    OnTaskTimeout(e.name);
                }
            }
        }
    }

private:
    struct Entry {
        const char* name;
        uint32_t    maxPeriodMs;
        uint32_t    lastKick;
        bool        healthy;
    };

    void OnTaskTimeout(const char* name) {
        // Log DTC, enter safe state, trigger HW watchdog
        (void)name;
    }

    Entry   m_entries[kMaxTasks]{};
    uint8_t m_count{0U};
};
```

---

## 11. Memory-Mapped Register Classes

```cpp
// Type-safe memory-mapped I/O register
template<uint32_t Address, typename T = uint32_t>
class MmioRegister {
public:
    static T Read() {
        return *reinterpret_cast<volatile T*>(Address);
    }
    static void Write(T value) {
        *reinterpret_cast<volatile T*>(Address) = value;
    }
    static void SetBits(T mask)   { Write(Read() | mask); }
    static void ClearBits(T mask) { Write(Read() & ~mask); }
    static void ModifyBits(T mask, T value) { Write((Read() & ~mask) | (value & mask)); }
    static bool TestBits(T mask)  { return (Read() & mask) == mask; }
};

// Define registers as types — not instances (no memory consumed)
using GPIOA_MODER = MmioRegister<0x40020000UL>;
using GPIOA_ODR   = MmioRegister<0x40020014UL>;
using GPIOA_IDR   = MmioRegister<0x40020010UL>;
using TIM2_CR1    = MmioRegister<0x40000000UL>;
using TIM2_CNT    = MmioRegister<0x40000024UL>;

// Usage — readable and type-safe
void InitGpioA5AsOutput() {
    // Clear bits [11:10] for pin 5 mode
    GPIOA_MODER::ClearBits(0x00000C00UL);
    // Set bits [11:10] = 01 (output)
    GPIOA_MODER::SetBits(0x00000400UL);
}

void SetGpioA5(bool high) {
    if (high) GPIOA_ODR::SetBits(1UL << 5U);
    else      GPIOA_ODR::ClearBits(1UL << 5U);
}
```

---

## 12. CRC & Checksum Utilities

```cpp
// CRC-8/AUTOSAR — used in AUTOSAR E2E protection
class Crc8Autosar {
public:
    static uint8_t Compute(const uint8_t* data, uint16_t len,
                            uint8_t startValue = 0xFFU) {
        uint8_t crc = startValue;
        for (uint16_t i = 0U; i < len; ++i) {
            crc = s_table[crc ^ data[i]];
        }
        return crc ^ 0xFFU;
    }

private:
    // CRC-8/AUTOSAR polynomial: 0x2F
    static const uint8_t s_table[256U];
};

// CRC-32 (ISO-HDLC) — used in UDS, flash verification
class Crc32 {
public:
    static uint32_t Compute(const uint8_t* data, uint32_t len,
                             uint32_t seed = 0xFFFFFFFFUL) {
        uint32_t crc = seed;
        for (uint32_t i = 0UL; i < len; ++i) {
            crc = (crc >> 8U) ^ s_table[(crc ^ data[i]) & 0xFFU];
        }
        return crc ^ 0xFFFFFFFFUL;
    }

    // Verify NVM block integrity
    static bool VerifyBlock(const uint8_t* block, uint32_t size) {
        // Last 4 bytes are stored CRC
        if (size < 4UL) return false;
        uint32_t stored;
        memcpy(&stored, block + size - 4UL, 4UL);
        uint32_t computed = Compute(block, size - 4UL);
        return stored == computed;
    }

private:
    static const uint32_t s_table[256U];
};

// AUTOSAR E2E Profile 2 — safety wrapper
class E2EProfile2Wrapper {
public:
    struct Header {
        uint8_t counter;   // increments each transmission
        uint8_t crc;       // CRC-8 over data + counter
        uint8_t dataId;    // unique per signal
    };

    static void Protect(uint8_t* buf, uint16_t dataLen, uint8_t dataId,
                        uint8_t& counter) {
        Header hdr;
        hdr.dataId  = dataId;
        hdr.counter = counter++ & 0x0FU;  // 4-bit counter
        hdr.crc     = Crc8Autosar::Compute(buf, dataLen);
        hdr.crc     = Crc8Autosar::Compute(&hdr.counter, 1U, hdr.crc);
        hdr.crc     = Crc8Autosar::Compute(&hdr.dataId,  1U, hdr.crc);
        memcpy(buf + dataLen, &hdr, sizeof(hdr));
    }

    static bool Check(const uint8_t* buf, uint16_t dataLen, uint8_t dataId,
                      uint8_t& expectedCounter) {
        Header hdr;
        memcpy(&hdr, buf + dataLen, sizeof(hdr));
        if (hdr.dataId != dataId) return false;
        if ((hdr.counter & 0x0FU) != (expectedCounter & 0x0FU)) return false;

        uint8_t crc = Crc8Autosar::Compute(buf, dataLen);
        crc = Crc8Autosar::Compute(&hdr.counter, 1U, crc);
        crc = Crc8Autosar::Compute(&hdr.dataId,  1U, crc);
        if (crc != hdr.crc) return false;

        ++expectedCounter;
        return true;
    }
};
```

---

## 13. Logging System for ECU

```cpp
// Non-blocking, circular trace buffer
// Uses RTT (Segger Real-Time Transfer) pattern concept

enum class LogLevel : uint8_t {
    Debug   = 0U,
    Info    = 1U,
    Warning = 2U,
    Error   = 3U,
    Fatal   = 4U
};

struct LogEntry {
    uint32_t  timestamp;   // ms tick
    LogLevel  level;
    uint8_t   moduleId;    // which subsystem
    uint8_t   msgId;       // event code (no string — saves space)
    uint32_t  param1;
    uint32_t  param2;
};

class EcuLogger {
public:
    static constexpr uint16_t kBufferSize = 256U;

    static EcuLogger& Instance() {
        static EcuLogger inst;
        return inst;
    }

    void Log(LogLevel level, uint8_t module, uint8_t msgId,
             uint32_t p1 = 0U, uint32_t p2 = 0U) {
        LogEntry entry{GetTickMs(), level, module, msgId, p1, p2};
        CriticalSection cs;
        (void)m_buffer.Push(entry);  // drop if full — never block
    }

    bool GetNext(LogEntry& entry) {
        return m_buffer.Pop(entry);
    }

    uint16_t Count() const { return m_buffer.Count(); }

private:
    EcuLogger() = default;
    RingBuffer<LogEntry, kBufferSize> m_buffer;
};

// Module IDs
constexpr uint8_t kModAeb     = 0x01U;
constexpr uint8_t kModCan     = 0x02U;
constexpr uint8_t kModUds     = 0x03U;

// Message IDs (documented in log_catalog.h)
constexpr uint8_t kMsgAebActivated    = 0x10U;
constexpr uint8_t kMsgCanBusOff       = 0x20U;
constexpr uint8_t kMsgUdsSessionChange = 0x30U;

// Usage
void OnAebActivated(float ttc) {
    EcuLogger::Instance().Log(LogLevel::Warning, kModAeb,
        kMsgAebActivated,
        static_cast<uint32_t>(ttc * 1000.0F),  // ttc in ms
        0U);
}
```

---

## 14. Bootloader & Flash Programming

```cpp
// Flash memory programming API (STM32-style)
class FlashDriver {
public:
    enum class Sector : uint8_t { Sec0=0, Sec1, Sec2, Sec3, Sec4, Sec5 };

    static bool Unlock() {
        FLASH->KEYR = 0x45670123UL;
        FLASH->KEYR = 0xCDEF89ABUL;
        return (FLASH->CR & FLASH_CR_LOCK) == 0U;
    }

    static bool Lock() {
        FLASH->CR |= FLASH_CR_LOCK;
        return true;
    }

    static bool EraseSector(Sector sector) {
        WaitBusy();
        FLASH->CR &= ~FLASH_CR_SNB_Msk;
        FLASH->CR |= (static_cast<uint32_t>(sector) << FLASH_CR_SNB_Pos)
                   | FLASH_CR_SER;
        FLASH->CR |= FLASH_CR_STRT;
        WaitBusy();
        return (FLASH->SR & FLASH_SR_EOP) != 0U;
    }

    // Program word (32-bit)
    static bool ProgramWord(uint32_t address, uint32_t data) {
        WaitBusy();
        FLASH->CR &= ~FLASH_CR_PSIZE_Msk;
        FLASH->CR |= (0x02UL << FLASH_CR_PSIZE_Pos) | FLASH_CR_PG;
        *reinterpret_cast<volatile uint32_t*>(address) = data;
        WaitBusy();
        FLASH->CR &= ~FLASH_CR_PG;
        return (FLASH->SR & FLASH_SR_EOP) != 0U;
    }

    // Program block
    static bool ProgramBlock(uint32_t startAddr, const uint8_t* data,
                              uint32_t len) {
        uint32_t addr = startAddr;
        for (uint32_t i = 0UL; i < len; i += 4UL, addr += 4UL) {
            uint32_t word = 0xFFFFFFFFUL;
            memcpy(&word, data + i,
                   (len - i >= 4UL) ? 4UL : (len - i));
            if (!ProgramWord(addr, word)) return false;
        }
        return true;
    }

private:
    static void WaitBusy() {
        while (FLASH->SR & FLASH_SR_BSY) {}
    }
};

// UDS Download Sequence (0x34/0x36/0x37)
class FirmwareDownloader {
public:
    enum class DownloadState : uint8_t {
        Idle, AddressReceived, Downloading, Verifying
    };

    bool StartDownload(uint32_t targetAddress, uint32_t expectedLength) {
        if (!ValidateAddress(targetAddress, expectedLength)) return false;
        m_address = targetAddress;
        m_remaining = expectedLength;
        m_crc = 0xFFFFFFFFUL;
        if (!FlashDriver::Unlock()) return false;
        if (!FlashDriver::EraseSector(FlashDriver::Sector::Sec2)) return false;
        m_state = DownloadState::AddressReceived;
        return true;
    }

    bool TransferData(const uint8_t* block, uint32_t blockLen) {
        if (m_state != DownloadState::AddressReceived &&
            m_state != DownloadState::Downloading) return false;
        if (blockLen > m_remaining) return false;

        if (!FlashDriver::ProgramBlock(m_address, block, blockLen)) return false;
        m_address   += blockLen;
        m_remaining -= blockLen;
        m_crc = Crc32::Compute(block, blockLen, m_crc);
        m_state = DownloadState::Downloading;
        return true;
    }

    bool Finish(uint32_t expectedCrc) {
        if (m_remaining != 0UL) return false;
        FlashDriver::Lock();
        m_state = DownloadState::Verifying;
        return (m_crc ^ 0xFFFFFFFFUL) == expectedCrc;
    }

private:
    bool ValidateAddress(uint32_t addr, uint32_t size) {
        constexpr uint32_t kAppStart = 0x08020000UL;
        constexpr uint32_t kAppEnd   = 0x080FFFFFUL;
        return (addr >= kAppStart) && ((addr + size - 1UL) <= kAppEnd);
    }

    uint32_t      m_address{0U};
    uint32_t      m_remaining{0U};
    uint32_t      m_crc{0xFFFFFFFFUL};
    DownloadState m_state{DownloadState::Idle};
};
```

---

## 15. Cybersecurity Patterns — SecOC in C++

```cpp
// SecOC — Secure Onboard Communication (AUTOSAR)
// Authenticates CAN/Ethernet messages with MACs

// CMAC truncated to 24 bits (SecOC standard)
class SecOcAuthenticator {
public:
    // Fresh Value Counter (prevents replay attacks)
    using FreshnessValue = uint64_t;

    struct AuthResult {
        bool    success;
        uint8_t truncatedMac[3];  // 24-bit MAC
    };

    // Authenticate outgoing PDU
    AuthResult Authenticate(const uint8_t* pdu, uint16_t pduLen,
                             uint32_t dataId, FreshnessValue& fv) {
        AuthResult result{};
        ++fv;  // increment freshness

        // Build auth data: dataId (4B) + freshness (8B) + PDU
        uint8_t authData[256];
        uint16_t pos = 0U;
        memcpy(authData + pos, &dataId, 4U); pos += 4U;
        memcpy(authData + pos, &fv,     8U); pos += 8U;
        memcpy(authData + pos, pdu, pduLen); pos += pduLen;

        // Compute CMAC (simplified — real impl uses AES-128-CMAC)
        uint8_t mac[16];
        ComputeCmac(authData, pos, m_key, mac);

        // Truncate to 24 bits
        memcpy(result.truncatedMac, mac, 3U);
        result.success = true;
        return result;
    }

    // Verify incoming PDU
    bool Verify(const uint8_t* pdu, uint16_t pduLen,
                const uint8_t* rxMac, uint32_t dataId,
                FreshnessValue receivedFv) {
        // Check freshness is within window
        if (receivedFv <= m_lastFv) return false;
        if ((receivedFv - m_lastFv) > kMaxFreshnessGap) return false;

        uint8_t authData[256];
        uint16_t pos = 0U;
        memcpy(authData + pos, &dataId,     4U); pos += 4U;
        memcpy(authData + pos, &receivedFv, 8U); pos += 8U;
        memcpy(authData + pos, pdu, pduLen);      pos += pduLen;

        uint8_t mac[16];
        ComputeCmac(authData, pos, m_key, mac);

        if (memcmp(mac, rxMac, 3U) != 0) return false;
        m_lastFv = receivedFv;
        return true;
    }

    void SetKey(const uint8_t key[16]) {
        memcpy(m_key, key, 16U);
    }

private:
    static constexpr uint64_t kMaxFreshnessGap = 100ULL;
    void ComputeCmac(const uint8_t* data, uint16_t len,
                     const uint8_t key[16], uint8_t out[16]);

    uint8_t          m_key[16]{};
    FreshnessValue   m_lastFv{0ULL};
};
```

---

## 16. Sensor Fusion Architecture

```cpp
// Track-level fusion for ADAS — combining radar + camera targets

struct RadarTarget {
    uint8_t  id;
    float    rangeM, rangeRateMps, azimuthDeg;
    bool     valid;
};

struct CameraTarget {
    uint8_t  id;
    float    lateralOffsetM, longitudinalM;
    uint8_t  classification;  // 0=car, 1=truck, 2=pedestrian, 3=cyclist
    float    confidence;
    bool     valid;
};

struct FusedObject {
    uint8_t  id;
    float    x, y;           // position in vehicle frame (m)
    float    vx, vy;         // velocity (m/s)
    float    length, width;  // dimensions (m)
    uint8_t  classification;
    float    existenceProbability;
    bool     radarContrib, cameraContrib;
};

class ObjectFusion {
public:
    static constexpr uint8_t kMaxObjects = 32U;

    void Update(const RadarTarget* radarTargets, uint8_t radarCount,
                const CameraTarget* camTargets, uint8_t camCount,
                float dt) {
        // Predict all tracked objects forward
        for (uint8_t i = 0U; i < m_count; ++i) {
            Predict(m_objects[i], dt);
        }

        // Associate radar to existing tracks
        AssociateRadar(radarTargets, radarCount);

        // Associate camera to existing tracks
        AssociateCamera(camTargets, camCount);

        // Remove stale tracks
        PruneTracks();
    }

    const FusedObject* GetObjects() const { return m_objects; }
    uint8_t            GetCount()   const { return m_count; }

private:
    void Predict(FusedObject& obj, float dt) {
        obj.x += obj.vx * dt;
        obj.y += obj.vy * dt;
    }

    void AssociateRadar(const RadarTarget* targets, uint8_t count) {
        for (uint8_t i = 0U; i < count; ++i) {
            if (!targets[i].valid) continue;
            float tx = targets[i].rangeM * cosf(targets[i].azimuthDeg * kPiDeg);
            float ty = targets[i].rangeM * sinf(targets[i].azimuthDeg * kPiDeg);

            uint8_t bestMatch = FindBestMatch(tx, ty, kRadarGateM);
            if (bestMatch < kMaxObjects) {
                // Update existing track with radar measurement
                UpdateWithRadar(m_objects[bestMatch], targets[i]);
            } else {
                // Create new track
                CreateTrack(tx, ty, targets[i].rangeRateMps, true, false);
            }
        }
    }

    void AssociateCamera(const CameraTarget* targets, uint8_t count) {
        for (uint8_t i = 0U; i < count; ++i) {
            if (!targets[i].valid) continue;
            uint8_t bestMatch = FindBestMatch(
                targets[i].longitudinalM,
                targets[i].lateralOffsetM,
                kCameraGateM);
            if (bestMatch < kMaxObjects) {
                m_objects[bestMatch].cameraContrib = true;
                m_objects[bestMatch].classification = targets[i].classification;
            } else {
                CreateTrack(targets[i].longitudinalM,
                            targets[i].lateralOffsetM, 0.0F, false, true);
            }
        }
    }

    uint8_t FindBestMatch(float x, float y, float gate) {
        float bestDist = gate * gate;
        uint8_t bestIdx = kMaxObjects;
        for (uint8_t i = 0U; i < m_count; ++i) {
            float dx = m_objects[i].x - x;
            float dy = m_objects[i].y - y;
            float d2 = dx*dx + dy*dy;
            if (d2 < bestDist) { bestDist = d2; bestIdx = i; }
        }
        return bestIdx;
    }

    void UpdateWithRadar(FusedObject& obj, const RadarTarget& t) {
        // Simple alpha-beta update (could use Kalman)
        constexpr float kAlpha = 0.3F;
        float measX = t.rangeM * cosf(t.azimuthDeg * kPiDeg);
        float measY = t.rangeM * sinf(t.azimuthDeg * kPiDeg);
        obj.x  += kAlpha * (measX - obj.x);
        obj.y  += kAlpha * (measY - obj.y);
        obj.vx += kAlpha * (t.rangeRateMps - obj.vx);
        obj.radarContrib = true;
    }

    void CreateTrack(float x, float y, float vx, bool radar, bool camera) {
        if (m_count >= kMaxObjects) return;
        m_objects[m_count++] = {m_nextId++, x, y, vx, 0.0F,
                                 4.5F, 2.0F, 0U, 0.5F, radar, camera};
    }

    void PruneTracks() {
        for (uint8_t i = 0U; i < m_count; ) {
            if (m_objects[i].existenceProbability < 0.1F) {
                m_objects[i] = m_objects[--m_count];
            } else {
                ++i;
            }
        }
    }

    static constexpr float kRadarGateM  = 3.0F;
    static constexpr float kCameraGateM = 2.0F;
    static constexpr float kPiDeg       = 3.14159265F / 180.0F;

    FusedObject m_objects[kMaxObjects]{};
    uint8_t     m_count{0U};
    uint8_t     m_nextId{1U};
};
```

---

## 17. Interview Questions & Answers

### Q1: What is the difference between `volatile` and `atomic` in embedded C++?

**`volatile`:**
- Prevents compiler from caching a memory read
- Does NOT guarantee atomicity of read-modify-write
- Required for memory-mapped hardware registers
- Required for variables shared between ISR and main code on single-core

**`std::atomic` (C++11):**
- Guarantees atomicity of operations (no torn reads/writes)
- Generates memory barriers — prevents CPU reordering
- Required for shared variables between tasks on multi-core
- More expensive than plain `volatile`

```cpp
// Single-core MCU: volatile is sufficient for ISR↔task
volatile bool g_flag = false;

// Multi-core (Cortex-A/A57 in ADAS SoC):
#include <atomic>
std::atomic<bool> g_flag{false};  // safe across cores
```

### Q2: Why is `new`/`delete` forbidden in safety-critical automotive software?

1. **Non-deterministic timing** — heap allocator may take arbitrarily long
2. **Heap fragmentation** — over time, free blocks become too small
3. **No guaranteed success** — allocator can return nullptr after uptime
4. **Hard to test** — allocation failure is difficult to inject in testing
5. **ISO 26262** — prohibits non-deterministic behavior in ASIL-B/C/D

**Alternatives:** Static arrays, memory pools `MemPool<T,N>`, stack allocation

### Q3: What is priority inversion and how do you prevent it?

Priority inversion: Low-priority task L holds mutex M. High-priority task H blocks on M. Medium-priority task X preempts L → H is starved by X indirectly.

**Prevention:**
- Use **Priority Inheritance Protocol (PIP)** — OS temporarily raises L's priority to H's level
- FreeRTOS: `xSemaphoreCreateMutex()` has PIP built in
- Keep critical sections minimal
- Avoid blocking calls inside mutexes

### Q4: How do you implement a thread-safe singleton on AUTOSAR Adaptive platform?

```cpp
// C++11 magic statics guarantee thread-safe initialization
class NvMManager {
public:
    static NvMManager& Instance() {
        static NvMManager inst;  // constructed exactly once, thread-safe
        return inst;
    }
private:
    NvMManager() = default;
};
```

### Q5: Explain RAII and give an automotive example

RAII (Resource Acquisition Is Initialization): resource is acquired in constructor and released in destructor. Destructor is called deterministically when object goes out of scope — even on exception or early return.

**Automotive example:** Disabling CAN bus interrupts during multi-frame update:
```cpp
class CanIsrGuard {
public:
    CanIsrGuard()  { DisableCanInterrupts(); }
    ~CanIsrGuard() { EnableCanInterrupts(); }
};

void UpdateMultiFrameBuffer(const uint8_t* data, uint16_t len) {
    CanIsrGuard guard;  // interrupts disabled
    memcpy(g_buffer, data, len);
    g_length = len;
}   // interrupts re-enabled here — even if function returns early
```

### Q6: How do you profile stack usage on ARM Cortex-M?

```cpp
// Stack painting: fill with known pattern at startup
extern uint32_t _stack_start;
extern uint32_t _stack_end;

void PaintStack() {
    uint32_t* p = &_stack_start;
    while (p < &_stack_end) *p++ = 0xDEADBEEFUL;
}

// At runtime, find first non-painted word
uint32_t GetMaxStackUsed() {
    const uint32_t* p = &_stack_start;
    while (*p == 0xDEADBEEFUL) ++p;
    return (uint32_t)(&_stack_end - p) * sizeof(uint32_t);
}
```

---

*Document Version: 1.0 — May 2026*
