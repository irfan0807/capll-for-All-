# Embedded C++ Patterns for Automotive ECU Development

## 1. Why C++ in Automotive Embedded Systems?

C++ in automotive differs from desktop C++:
- **No heap allocation** (MISRA-C++, AUTOSAR C++14 guidelines)
- **No exceptions** (overhead, non-deterministic)
- **No RTTI** (memory overhead)
- **No dynamic polymorphism** where avoidable (use templates)
- Use **static allocation**, **placement new**, **fixed-size containers**

Compiler flags typically:
```cmake
-fno-exceptions -fno-rtti -fno-threadsafe-statics
-Os  # optimize for size
-Wall -Wextra -Wpedantic
```

---

## 2. MISRA C++ Compliance Patterns

```cpp
// BAD – dynamic allocation (MISRA violation)
uint8_t* buffer = new uint8_t[256];  // heap allocation

// GOOD – static allocation
static uint8_t buffer[256];  // or on stack if bounded

// BAD – range not checked
uint8_t getValue(uint8_t* arr, int idx) {
    return arr[idx];  // undefined behavior if idx out of range
}

// GOOD – with bounds check
uint8_t getValue(const uint8_t* arr, uint8_t idx, uint8_t maxLen) {
    if (idx >= maxLen) {
        return 0U;  // safe default
    }
    return arr[idx];
}

// BAD – magic numbers
if (session == 2) { ... }

// GOOD – named constants
constexpr uint8_t UDS_SESSION_PROGRAMMING = 0x02U;
if (session == UDS_SESSION_PROGRAMMING) { ... }
```

---

## 3. State Machine Pattern (Template-based)

```cpp
// Generic State Machine using enum class + function pointer table
// No virtual functions, no heap – safe for embedded

enum class EngineState : uint8_t {
    POWER_OFF = 0,
    INIT,
    CRANKING,
    RUNNING,
    SHUTDOWN,
    COUNT
};

enum class EngineEvent : uint8_t {
    IGN_ON = 0,
    CRANK,
    RPM_ABOVE_500,
    IGN_OFF,
    COUNT
};

using StateHandler = void(*)();
using TransitionTable = EngineState[static_cast<uint8_t>(EngineState::COUNT)]
                                   [static_cast<uint8_t>(EngineEvent::COUNT)];

class EngineStateMachine {
public:
    EngineStateMachine() : m_state(EngineState::POWER_OFF) {}

    void processEvent(EngineEvent event) {
        EngineState nextState = s_transitions[idx(m_state)][idx(event)];
        if (nextState != m_state) {
            executeExit(m_state);
            m_state = nextState;
            executeEntry(m_state);
        }
    }

    EngineState getState() const { return m_state; }

private:
    EngineState m_state;

    static constexpr uint8_t idx(EngineState s) {
        return static_cast<uint8_t>(s);
    }
    static constexpr uint8_t idx(EngineEvent e) {
        return static_cast<uint8_t>(e);
    }

    static const TransitionTable s_transitions;

    void executeEntry(EngineState state);
    void executeExit(EngineState state);
};

const EngineStateMachine::TransitionTable EngineStateMachine::s_transitions = {
    //              IGN_ON              CRANK              RPM>500             IGN_OFF
    /* POWER_OFF */ {EngineState::INIT, EngineState::POWER_OFF, EngineState::POWER_OFF, EngineState::POWER_OFF},
    /* INIT      */ {EngineState::INIT, EngineState::CRANKING,  EngineState::INIT,      EngineState::SHUTDOWN},
    /* CRANKING  */ {EngineState::CRANKING, EngineState::CRANKING, EngineState::RUNNING, EngineState::SHUTDOWN},
    /* RUNNING   */ {EngineState::RUNNING,  EngineState::RUNNING,  EngineState::RUNNING, EngineState::SHUTDOWN},
    /* SHUTDOWN  */ {EngineState::INIT, EngineState::SHUTDOWN,  EngineState::SHUTDOWN,  EngineState::POWER_OFF},
};
```

---

## 4. Fixed-Size Ring Buffer (Lock-Free, ISR-Safe)

```cpp
#include <cstdint>
#include <cstring>
#include <atomic>

template<typename T, uint16_t CAPACITY>
class RingBuffer {
static_assert((CAPACITY & (CAPACITY - 1)) == 0, "CAPACITY must be power of 2");

public:
    RingBuffer() : m_head(0U), m_tail(0U) {}

    // Called from ISR / producer
    bool push(const T& item) {
        uint16_t head = m_head.load(std::memory_order_relaxed);
        uint16_t nextHead = (head + 1U) & MASK;
        if (nextHead == m_tail.load(std::memory_order_acquire)) {
            return false;  // Buffer full
        }
        m_buffer[head] = item;
        m_head.store(nextHead, std::memory_order_release);
        return true;
    }

    // Called from task / consumer
    bool pop(T& item) {
        uint16_t tail = m_tail.load(std::memory_order_relaxed);
        if (tail == m_head.load(std::memory_order_acquire)) {
            return false;  // Buffer empty
        }
        item = m_buffer[tail];
        m_tail.store((tail + 1U) & MASK, std::memory_order_release);
        return true;
    }

    bool isEmpty() const {
        return m_head.load(std::memory_order_acquire) ==
               m_tail.load(std::memory_order_acquire);
    }

    uint16_t size() const {
        uint16_t h = m_head.load(std::memory_order_acquire);
        uint16_t t = m_tail.load(std::memory_order_acquire);
        return (h - t) & MASK;
    }

private:
    static constexpr uint16_t MASK = CAPACITY - 1U;
    T m_buffer[CAPACITY];
    std::atomic<uint16_t> m_head;
    std::atomic<uint16_t> m_tail;
};
```

---

## 5. Singleton for ECU Managers (Deterministic Construction)

```cpp
// Automotive-safe singleton – avoids dynamic initialization order issues
// Uses static local variable (guaranteed initialized once, thread-safe in C++11)

class DTCManager {
public:
    static DTCManager& getInstance() {
        static DTCManager instance;  // Initialized on first call
        return instance;
    }

    // Delete copy and move
    DTCManager(const DTCManager&) = delete;
    DTCManager& operator=(const DTCManager&) = delete;
    DTCManager(DTCManager&&) = delete;
    DTCManager& operator=(DTCManager&&) = delete;

    void setDTC(uint32_t dtcCode, uint8_t statusByte);
    void clearAllDTCs();
    bool isDTCActive(uint32_t dtcCode) const;

private:
    DTCManager() { initialize(); }
    ~DTCManager() = default;

    void initialize();

    static constexpr uint8_t MAX_DTC_COUNT = 50U;
    struct DTCEntry {
        uint32_t code;
        uint8_t  status;
        uint32_t timestamp;
        bool     valid;
    };
    DTCEntry m_dtcList[MAX_DTC_COUNT];
    uint8_t  m_dtcCount{0U};
};
```

---

## 6. Signal Encoding/Decoding (CAN Signal Extraction)

```cpp
// Extract a CAN signal from raw 8-byte frame using bit manipulation
// This is the core of DBC signal handling

class CANSignalDecoder {
public:
    /**
     * Extract a signal from CAN frame data
     * @param data     : pointer to CAN frame bytes (8 bytes)
     * @param startBit : start bit (Intel byte order, LSB first)
     * @param length   : signal length in bits
     * @param isSigned : true if signed integer
     * @return extracted raw value
     */
    static int64_t extractSignal(const uint8_t* data,
                                  uint8_t startBit,
                                  uint8_t length,
                                  bool isSigned = false)
    {
        uint64_t rawFrame = 0ULL;
        // Pack bytes into 64-bit integer (Intel byte order)
        for (uint8_t i = 0U; i < 8U; ++i) {
            rawFrame |= (static_cast<uint64_t>(data[i]) << (i * 8U));
        }

        // Extract bits
        uint64_t mask = (length == 64U) ? ~0ULL : ((1ULL << length) - 1ULL);
        uint64_t rawValue = (rawFrame >> startBit) & mask;

        // Sign extension
        if (isSigned && (rawValue & (1ULL << (length - 1U)))) {
            rawValue |= ~mask;  // fill upper bits with 1
        }

        return static_cast<int64_t>(rawValue);
    }

    /**
     * Apply signal factor and offset to get physical value
     * Physical = Raw * Factor + Offset
     */
    static double toPhysical(int64_t rawValue, double factor, double offset) {
        return (static_cast<double>(rawValue) * factor) + offset;
    }
};

// Usage:
// uint8_t frameData[8] = {0xFC, 0x08, 0x00, ...};
// int64_t raw = CANSignalDecoder::extractSignal(frameData, 0, 16, false);
// double rpm = CANSignalDecoder::toPhysical(raw, 0.25, 0.0);  // = 570 RPM
```

---

## 7. Timer Abstraction (Hardware-Independent)

```cpp
#include <cstdint>

// Platform abstraction for system tick
// Implemented differently on MCU vs unit test host
class SystemTimer {
public:
    using TickType = uint32_t;

    static TickType getTickMs();   // Implemented in platform layer
    static TickType getTickUs();

    static bool hasElapsed(TickType startTick, TickType durationMs) {
        return (getTickMs() - startTick) >= durationMs;
    }
};

// Software timer built on top
class SoftwareTimer {
public:
    SoftwareTimer() : m_startTick(0U), m_isRunning(false) {}

    void start() {
        m_startTick = SystemTimer::getTickMs();
        m_isRunning = true;
    }

    void stop() { m_isRunning = false; }

    bool hasExpired(uint32_t durationMs) const {
        return m_isRunning && SystemTimer::hasElapsed(m_startTick, durationMs);
    }

    uint32_t elapsed() const {
        return SystemTimer::getTickMs() - m_startTick;
    }

    bool isRunning() const { return m_isRunning; }

private:
    uint32_t m_startTick;
    bool     m_isRunning;
};
```

---

## 8. Bit Manipulation Utilities

```cpp
#include <cstdint>

namespace Bits {

// Set a bit
template<typename T>
constexpr void set(T& reg, uint8_t bit) {
    reg |= static_cast<T>(1U) << bit;
}

// Clear a bit
template<typename T>
constexpr void clear(T& reg, uint8_t bit) {
    reg &= ~(static_cast<T>(1U) << bit);
}

// Toggle a bit
template<typename T>
constexpr void toggle(T& reg, uint8_t bit) {
    reg ^= static_cast<T>(1U) << bit;
}

// Check if bit is set
template<typename T>
constexpr bool isSet(T reg, uint8_t bit) {
    return (reg & (static_cast<T>(1U) << bit)) != 0U;
}

// Extract a bit field
template<typename T>
constexpr T extractField(T reg, uint8_t start, uint8_t width) {
    T mask = (static_cast<T>(1U) << width) - static_cast<T>(1U);
    return (reg >> start) & mask;
}

// Insert a bit field
template<typename T>
constexpr void insertField(T& reg, T value, uint8_t start, uint8_t width) {
    T mask = ((static_cast<T>(1U) << width) - static_cast<T>(1U)) << start;
    reg = (reg & ~mask) | ((value << start) & mask);
}

} // namespace Bits

// DTC Status byte operations
namespace DTCStatus {
    constexpr uint8_t TEST_FAILED              = 0x01U;
    constexpr uint8_t TEST_FAILED_THIS_CYCLE   = 0x02U;
    constexpr uint8_t PENDING_DTC             = 0x04U;
    constexpr uint8_t CONFIRMED_DTC           = 0x08U;
    constexpr uint8_t TEST_NOT_COMPLETED      = 0x10U;
    constexpr uint8_t TEST_FAILED_SINCE_CLEAR = 0x20U;
    constexpr uint8_t TEST_NOT_DONE_THIS_CYCLE= 0x40U;
    constexpr uint8_t WARNING_INDICATOR       = 0x80U;
}
```

---

## 9. AUTOSAR-style Return Type Pattern

```cpp
// Instead of exceptions, use return codes (MISRA-compliant)

enum class Std_ReturnType : uint8_t {
    E_OK        = 0x00U,
    E_NOT_OK    = 0x01U,
    E_PENDING   = 0x02U,
    E_OVERFLOW  = 0x03U,
    E_UNDERFLOW = 0x04U,
    E_BUSY      = 0x05U,
};

class CANInterface {
public:
    Std_ReturnType transmit(uint32_t canId, const uint8_t* data, uint8_t dlc);
    Std_ReturnType receive(uint32_t& canId, uint8_t* data, uint8_t& dlc);
};

// Usage:
// Std_ReturnType result = canIf.transmit(0x7E8, responseData, 8);
// if (result != Std_ReturnType::E_OK) {
//     DTCManager::getInstance().setDTC(0xC0300, DTCStatus::TEST_FAILED);
// }
```

---

## 10. MISRA Key Rules Summary

| Rule Category | Key Rules |
|---------------|-----------|
| **Types**     | Use fixed-width types (uint8_t, int32_t) not int/long |
| **Arithmetic**| Cast before arithmetic; check for overflow |
| **Pointers**  | No pointer arithmetic; check NULL before deref |
| **Functions** | Single entry/exit or documented; max cyclomatic complexity 10 |
| **Initialization** | All variables initialized at declaration |
| **Flow control** | No goto; no recursive functions |
| **Dynamic memory** | No malloc/free/new/delete |
| **Exceptions** | Disable C++ exceptions |
| **Unions**    | No unions (use bitfields with caution) |
