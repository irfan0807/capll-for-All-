# C++ Fundamentals for Automotive Software Engineering

> **Target Role:** Embedded C++, AUTOSAR Classic/Adaptive, ECU Software, HIL/SIL Validation
> **Standards Referenced:** MISRA C++ 2008, AUTOSAR C++ 14, ISO 26262, ASPICE

---

## 1. Data Types in Embedded / Automotive Context

### Fixed-Width Integer Types (Always prefer in automotive)

```cpp
#include <cstdint>      // ISO C99 / C++11

int8_t   speed_delta;       // -128 to 127
uint8_t  gear_position;     // 0 to 255
int16_t  torque_request;    // -32768 to 32767
uint16_t engine_rpm;        // 0 to 65535
int32_t  odometer_cm;       // signed 32-bit
uint32_t timestamp_ms;      // unsigned 32-bit
int64_t  calibration_ref;   // 64-bit (avoid on 8/16-bit MCUs)
```

**MISRA C++ Rule 3-9-2:** Use typedefs for numeric types — `uint16_t` not `unsigned short`.

### Automotive Signal Scaling

```cpp
// Physical value = (raw * factor) + offset
constexpr float VOLTAGE_FACTOR  = 0.001f;   // 1 mV per bit
constexpr float VOLTAGE_OFFSET  = 0.0f;
constexpr float TEMP_FACTOR     = 0.5f;     // 0.5°C per bit
constexpr float TEMP_OFFSET     = -40.0f;   // -40°C offset

float decode_cell_voltage(uint16_t raw) {
    return static_cast<float>(raw) * VOLTAGE_FACTOR + VOLTAGE_OFFSET;
}

float decode_temperature(uint8_t raw) {
    return static_cast<float>(raw) * TEMP_FACTOR + TEMP_OFFSET;
}
```

---

## 2. Pointers & References in Embedded C++

```cpp
// Raw pointer — avoid in modern AUTOSAR Adaptive
uint8_t ecu_buffer[256];
uint8_t* p_buf = ecu_buffer;

// Safer: reference (no null, no arithmetic)
void process_frame(const uint8_t& frame_id) {
    // frame_id cannot be null, cannot be reseated
}

// Pointer to function — used heavily in callback/ISR architectures
using IrqHandler = void(*)(void);
IrqHandler can_rx_isr = nullptr;

void register_isr(IrqHandler handler) {
    can_rx_isr = handler;
}
```

### MISRA Rules on Pointers
- **Rule 5-2-6:** Do not cast between pointer-to-function and any other type
- **Rule 5-2-7:** An object with pointer type shall not be converted to an unrelated pointer type
- **Rule 7-5-1:** A function shall not return a reference/pointer to an automatic variable

---

## 3. Control Flow — Automotive Patterns

### State Machine (switch-based — common in ECU software)

```cpp
enum class VehicleState : uint8_t {
    INIT     = 0U,
    STANDBY  = 1U,
    READY    = 2U,
    DRIVING  = 3U,
    CHARGING = 4U,
    FAULT    = 5U
};

VehicleState current_state = VehicleState::INIT;

void state_machine_10ms(void) {
    switch (current_state) {
        case VehicleState::INIT:
            if (self_test_passed()) {
                current_state = VehicleState::STANDBY;
            }
            break;

        case VehicleState::STANDBY:
            if (ignition_on() && hvil_ok()) {
                current_state = VehicleState::READY;
            }
            break;

        case VehicleState::READY:
            if (accelerator_pressed()) {
                current_state = VehicleState::DRIVING;
            }
            if (fault_detected()) {
                current_state = VehicleState::FAULT;
            }
            break;

        case VehicleState::FAULT:
            execute_safe_state();
            break;

        default:
            /* MISRA: default must be present */
            break;
    }
}
```

### Debounce Counter Pattern (ISO 26262 ASIL B)

```cpp
struct DebounceCounter {
    uint8_t fault_count;
    uint8_t heal_count;
    static constexpr uint8_t FAULT_THRESHOLD = 3U;
    static constexpr uint8_t HEAL_THRESHOLD  = 5U;
    bool faulted = false;

    void update(bool condition_active) {
        if (condition_active) {
            heal_count = 0U;
            if (fault_count < FAULT_THRESHOLD) {
                ++fault_count;
            } else {
                faulted = true;
            }
        } else {
            fault_count = 0U;
            if (heal_count < HEAL_THRESHOLD) {
                ++heal_count;
            } else {
                faulted = false;
            }
        }
    }
};
```

---

## 4. Arrays & Buffers

```cpp
// Stack array — preferred for known-size data
constexpr uint8_t CAN_FRAME_SIZE = 8U;
uint8_t tx_buffer[CAN_FRAME_SIZE] = {0U};

// Multi-dimensional — cell voltage matrix [module][cell]
constexpr uint8_t NUM_MODULES = 12U;
constexpr uint8_t CELLS_PER_MODULE = 8U;
uint16_t cell_voltage[NUM_MODULES][CELLS_PER_MODULE];

// Byte-level access to CAN signal
uint16_t extract_16bit(const uint8_t* frame, uint8_t start_byte) {
    return static_cast<uint16_t>(
        (static_cast<uint16_t>(frame[start_byte]) << 8U) |
        static_cast<uint16_t>(frame[start_byte + 1U])
    );
}

// Circular buffer — UART / CAN ring buffer
template<typename T, uint16_t SIZE>
class RingBuffer {
    T data_[SIZE];
    uint16_t head_ = 0U;
    uint16_t tail_ = 0U;
    uint16_t count_ = 0U;
public:
    bool push(const T& item) {
        if (count_ == SIZE) return false;   // Full
        data_[head_] = item;
        head_ = (head_ + 1U) % SIZE;
        ++count_;
        return true;
    }
    bool pop(T& item) {
        if (count_ == 0U) return false;     // Empty
        item = data_[tail_];
        tail_ = (tail_ + 1U) % SIZE;
        --count_;
        return true;
    }
    bool is_empty() const { return count_ == 0U; }
};
```

---

## 5. Bitwise Operations — CAN Signal Encoding/Decoding

```cpp
// Bit masking
constexpr uint8_t FAULT_MASK    = 0x01U;   // bit 0
constexpr uint8_t CONTACTOR_MASK = 0x06U;  // bits 1-2
constexpr uint8_t BALANCE_MASK  = 0x08U;   // bit 3

uint8_t status_byte = 0U;

// Set bit
status_byte |= FAULT_MASK;

// Clear bit
status_byte &= ~FAULT_MASK;

// Toggle bit
status_byte ^= BALANCE_MASK;

// Test bit
bool is_faulted = (status_byte & FAULT_MASK) != 0U;

// Multi-bit field extraction (CAN signal, big-endian 16-bit)
uint16_t extract_signal(const uint8_t* data, uint8_t start_bit, uint8_t length) {
    uint16_t raw = 0U;
    for (uint8_t i = 0U; i < length; ++i) {
        uint8_t bit_pos = start_bit + i;
        if ((data[bit_pos / 8U] & (1U << (7U - (bit_pos % 8U)))) != 0U) {
            raw |= static_cast<uint16_t>(1U << (length - 1U - i));
        }
    }
    return raw;
}
```

---

## 6. `const`, `constexpr`, `volatile` in Automotive

```cpp
// const — runtime constant, value cannot change
const uint16_t max_rpm = 8000U;

// constexpr — compile-time constant, no RAM usage
constexpr float OV2_THRESHOLD_V = 4.25f;
constexpr uint16_t OV2_RAW = static_cast<uint16_t>(OV2_THRESHOLD_V / 0.001f);  // 4250

// volatile — for hardware registers, shared ISR variables
volatile uint32_t* const TIMER_REG = reinterpret_cast<volatile uint32_t*>(0x40000400U);
volatile bool g_can_rx_flag = false;    // modified in ISR, read in main loop

// ISR sets flag
extern "C" void CAN1_RX_IRQHandler(void) {
    g_can_rx_flag = true;
}

// Main loop polls flag
void main_loop(void) {
    if (g_can_rx_flag) {
        g_can_rx_flag = false;
        process_can_frame();
    }
}
```

---

## 7. Preprocessor & Compile Guards

```cpp
#ifndef BMS_CONFIG_H
#define BMS_CONFIG_H

// Feature flags
#define BMS_ENABLE_CELL_BALANCING    1U
#define BMS_ENABLE_THERMAL_RUNAWAY   1U
#define BMS_NUM_CELLS               96U

// Variant selection
#if defined(VARIANT_LFP)
    #define OV2_THRESHOLD_MV   3650U
    #define UV2_THRESHOLD_MV   2500U
#elif defined(VARIANT_NMC)
    #define OV2_THRESHOLD_MV   4250U
    #define UV2_THRESHOLD_MV   2800U
#else
    #error "No battery chemistry variant defined"
#endif

#endif /* BMS_CONFIG_H */
```

---

## 8. `static` Keyword — Automotive Use Cases

```cpp
// 1. Static local — persistent across calls (like module-level variable)
uint32_t get_uptime_ms(void) {
    static uint32_t ms = 0U;
    ++ms;
    return ms;
}

// 2. Static member — shared across all ECU instances
class VCU {
public:
    static uint8_t instance_count;
    VCU() { ++instance_count; }
};
uint8_t VCU::instance_count = 0U;

// 3. Static function — file scope only (replaces anonymous namespace)
static void reset_can_controller(void) {
    // Only visible in this translation unit
}
```

---

## 9. Type Casting — Safe Automotive Practices

```cpp
// Prefer static_cast over C-style cast
uint16_t raw_adc = 3075U;
float voltage = static_cast<float>(raw_adc) * 0.001f;

// reinterpret_cast — hardware register access ONLY
constexpr uint32_t GPIOA_BASE = 0x48000000U;
struct GPIO_TypeDef { volatile uint32_t MODER; volatile uint32_t ODR; };
GPIO_TypeDef* const GPIOA = reinterpret_cast<GPIO_TypeDef*>(GPIOA_BASE);

// Avoid: C-style cast
// float v = (float)raw_adc;   // MISRA 5-2-4 violation

// Range check before narrowing cast (MISRA 5-0-3)
uint32_t big_value = 1000U;
if (big_value <= 255U) {
    uint8_t small = static_cast<uint8_t>(big_value);
}
```

---

## 10. Inline Functions vs Macros (MISRA)

```cpp
// BAD — Macro (MISRA 16-0-4: function-like macros should not be used)
#define MAX_RPM(a, b) ((a) > (b) ? (a) : (b))  // Not type-safe

// GOOD — Inline function
template<typename T>
inline T max_val(const T& a, const T& b) {
    return (a > b) ? a : b;
}

// GOOD — constexpr function
constexpr uint16_t rpm_to_rads(uint16_t rpm) {
    return static_cast<uint16_t>(static_cast<float>(rpm) * 0.10472f);
}
```

---

## 11. Error Handling Patterns (No Exceptions in Embedded)

```cpp
// AUTOSAR / MISRA: No exceptions (Rule 15-3-1)
// Pattern 1: Return codes
enum class Std_ReturnType : uint8_t {
    E_OK        = 0U,
    E_NOT_OK    = 1U,
    E_PENDING   = 2U,
    E_TIMEOUT   = 3U
};

Std_ReturnType can_transmit(uint32_t id, const uint8_t* data, uint8_t dlc) {
    if (data == nullptr) return Std_ReturnType::E_NOT_OK;
    if (dlc > 8U)        return Std_ReturnType::E_NOT_OK;
    // ... transmit
    return Std_ReturnType::E_OK;
}

// Pattern 2: Output parameter + bool return
bool read_cell_voltage(uint8_t cell_id, float& out_voltage) {
    if (cell_id >= 96U) return false;
    out_voltage = decode_cell_voltage(cell_voltage_raw[cell_id]);
    return true;
}

// Pattern 3: Optional-like (C++17, AUTOSAR Adaptive)
#include <optional>
std::optional<float> get_isolation_resistance(void) {
    if (!imd_available()) return std::nullopt;
    return calculate_r_iso();
}
```

---

## 12. Interrupt Service Routines (ISR) Best Practices

```cpp
// Keep ISRs short — only set flags, copy data
volatile bool     g_can1_rx_ready = false;
volatile uint32_t g_can1_rx_id    = 0U;
volatile uint8_t  g_can1_rx_data[8U];
volatile uint8_t  g_can1_rx_dlc   = 0U;

extern "C" void CAN1_RX0_IRQHandler(void) {
    // Read from hardware FIFO
    g_can1_rx_id  = CAN1->sFIFOMailBox[0].RIR >> 21U;
    g_can1_rx_dlc = CAN1->sFIFOMailBox[0].RDTR & 0x0FU;
    for (uint8_t i = 0U; i < g_can1_rx_dlc; ++i) {
        g_can1_rx_data[i] = static_cast<uint8_t>(
            (CAN1->sFIFOMailBox[0].RDLR >> (8U * i)) & 0xFFU
        );
    }
    CAN1->RF0R |= 0x20U;    // Release FIFO
    g_can1_rx_ready = true; // Signal main loop
}
```

---

## MISRA C++ 2008 — Top 20 Rules for Automotive C++

| Rule | Category | Requirement |
|---|---|---|
| 0-1-1 | Project | No dead code |
| 0-1-6 | Project | No unused values |
| 2-10-1 | Lexical | No different identifiers differing only in case |
| 3-9-2 | Basic | Use typedefs for numeric types |
| 5-0-3 | Expressions | No implicit integral conversions |
| 5-2-4 | Expressions | C-style casts not permitted |
| 6-4-5 | Statements | Every switch must have default |
| 6-5-1 | Statements | Loop counter shall not have floating-point type |
| 7-5-1 | Declarations | No return pointer/reference to local |
| 8-4-1 | Declarations | Void functions shall not return a value |
| 9-5-1 | Classes | Unions shall not be used |
| 10-1-1 | Classes | No virtual base classes unless necessary |
| 11-0-1 | Classes | Member data shall be private |
| 15-0-1 | Exceptions | Exceptions shall not be used |
| 16-0-4 | Preprocessing | Function-like macros shall not be used |
| 16-2-1 | Preprocessing | C++ comments shall not be used in C headers |
| 17-0-2 | Library | Banned C standard library functions |
| 18-0-1 | Library | No use of setjmp/longjmp |
| 18-4-1 | Library | Dynamic heap allocation shall not be used |
| 27-0-1 | Library | No stdio in embedded code |

---

*File: 01_cpp_fundamentals_automotive.md | cpp_automotive study series*
