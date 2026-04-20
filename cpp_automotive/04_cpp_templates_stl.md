# C++ Templates & STL for Automotive Software

> **Coverage:** Function Templates, Class Templates, STL Containers, Algorithms, Type Traits
> **Context:** AUTOSAR Adaptive, Simulation Frameworks, Test Harnesses, Signal Processing
> **Note:** STL containers with heap allocation BANNED in AUTOSAR Classic. Safe in Adaptive.

---

## 1. Function Templates

```cpp
// Generic signal clamp — replaces 3 separate float/int/uint implementations
template<typename T>
constexpr T clamp(const T& value, const T& min_val, const T& max_val) {
    if (value < min_val) return min_val;
    if (value > max_val) return max_val;
    return value;
}

// Generic map/scale — physical value ↔ raw ADC
template<typename RawType, typename PhysType>
PhysType raw_to_physical(RawType raw, RawType raw_min, RawType raw_max,
                          PhysType phys_min, PhysType phys_max) {
    if (raw_max == raw_min) return phys_min;
    float ratio = static_cast<float>(raw - raw_min) / static_cast<float>(raw_max - raw_min);
    return static_cast<PhysType>(static_cast<float>(phys_min) +
                                  ratio * static_cast<float>(phys_max - phys_min));
}

// Usage
float voltage = raw_to_physical<uint16_t, float>(2048U, 0U, 4095U, 0.0f, 5.0f);
int16_t torque = raw_to_physical<uint16_t, int16_t>(3000U, 0U, 65535U, -3000, 3000);

// Generic endian swap
template<typename T>
T byteswap(T value) {
    static_assert(std::is_integral<T>::value, "Only integral types supported");
    T result = 0;
    for (std::size_t i = 0; i < sizeof(T); ++i) {
        result = static_cast<T>((result << 8U) | (value & 0xFFU));
        value >>= 8U;
    }
    return result;
}

uint32_t big_endian_id = byteswap<uint32_t>(0x12345678U);  // → 0x78563412
```

---

## 2. Class Templates — Static-Size Collections

```cpp
// AUTOSAR Classic safe: Fixed-size array wrapper
template<typename T, std::size_t N>
class StaticArray {
    static_assert(N > 0U, "Array size must be positive");
public:
    using value_type = T;
    static constexpr std::size_t SIZE = N;

    T& operator[](std::size_t idx) {
        // Bounds check in debug builds
        assert(idx < N);
        return data_[idx];
    }
    const T& operator[](std::size_t idx) const {
        assert(idx < N);
        return data_[idx];
    }

    constexpr std::size_t size(void) const { return N; }

    T* begin(void) { return data_; }
    T* end(void)   { return data_ + N; }
    const T* begin(void) const { return data_; }
    const T* end(void)   const { return data_ + N; }

    void fill(const T& val) {
        for (auto& elem : *this) elem = val;
    }

private:
    T data_[N] = {};
};

// Usage
StaticArray<float, 96U>   cell_voltages;
StaticArray<int8_t, 8U>   module_temps;
StaticArray<uint32_t, 32U> dtc_buffer;

cell_voltages.fill(3.7f);
```

---

## 3. Template Specialization — Protocol-Specific Decode

```cpp
// Primary template — generic CAN signal decode
template<typename SignalType>
SignalType decode_can_signal(const uint8_t* frame, uint8_t byte_offset,
                              float factor, float offset) {
    uint16_t raw = static_cast<uint16_t>((frame[byte_offset] << 8U) | frame[byte_offset + 1U]);
    return static_cast<SignalType>(static_cast<float>(raw) * factor + offset);
}

// Specialization for bool (single-bit signal)
template<>
bool decode_can_signal<bool>(const uint8_t* frame, uint8_t byte_offset,
                              float /*factor*/, float /*offset*/) {
    return (frame[byte_offset] & 0x01U) != 0U;
}

// Specialization for int8_t (temperature, offset -40)
template<>
int8_t decode_can_signal<int8_t>(const uint8_t* frame, uint8_t byte_offset,
                                   float /*factor*/, float offset) {
    return static_cast<int8_t>(static_cast<int>(frame[byte_offset]) + static_cast<int>(offset));
}
```

---

## 4. Variadic Templates — Logging Framework

```cpp
// Type-safe variadic logger (replaces printf in embedded)
enum class LogLevel : uint8_t { DEBUG=0, INFO=1, WARNING=2, ERROR=3, CRITICAL=4 };

template<typename... Args>
void log_message(LogLevel level, const char* fmt, Args&&... args) {
    if (level < CURRENT_LOG_LEVEL) return;

    // Serialize to static buffer (no heap)
    static char log_buf[256U];
    snprintf(log_buf, sizeof(log_buf), fmt, std::forward<Args>(args)...);

    // Send to UART/SWO
    uart_transmit(reinterpret_cast<const uint8_t*>(log_buf),
                  static_cast<uint16_t>(strlen(log_buf)));
}

// Usage
log_message(LogLevel::ERROR, "[BMS] OV2 fault: cell=%u voltage=%.3fV", cell_id, voltage);
log_message(LogLevel::INFO,  "[UDS] Session 0x%02X opened", session_id);
log_message(LogLevel::WARNING, "[CAN] Queue overflow: dropped %u frames", drop_count);
```

---

## 5. Type Traits — Compile-Time Safety

```cpp
#include <type_traits>

// Only allow floating point for physical values
template<typename T>
float normalize(T raw, T max_raw) {
    static_assert(std::is_arithmetic<T>::value, "T must be arithmetic");
    return static_cast<float>(raw) / static_cast<float>(max_raw);
}

// Only allow integral for CAN IDs
template<typename T>
bool is_valid_can_id(T id) {
    static_assert(std::is_integral<T>::value && std::is_unsigned<T>::value,
                  "CAN ID must be unsigned integer");
    static_assert(sizeof(T) >= 2U, "CAN ID type too small");
    return id <= 0x7FFU;    // Standard 11-bit CAN
}

// Conditional type selection — choose container based on size
template<std::size_t N>
using DtcStorage = typename std::conditional<
    (N <= 32U),
    StaticArray<uint32_t, N>,    // Small: use static array
    std::vector<uint32_t>         // Large: use vector (Adaptive only)
>::type;

// enable_if — restrict template to numeric types only
template<typename T, typename = typename std::enable_if<std::is_arithmetic<T>::value>::type>
T safe_divide(T numerator, T denominator, T fallback = T{0}) {
    if (denominator == T{0}) return fallback;
    return numerator / denominator;
}
```

---

## 6. STL Containers (AUTOSAR Adaptive)

### `std::array` — Fixed-size (allowed everywhere)

```cpp
#include <array>
#include <algorithm>

std::array<float, 96U> cell_v;
cell_v.fill(3.7f);

auto max_v = *std::max_element(cell_v.begin(), cell_v.end());
auto min_v = *std::min_element(cell_v.begin(), cell_v.end());
float delta = max_v - min_v;

// Count cells with OV condition
uint8_t ov_count = static_cast<uint8_t>(
    std::count_if(cell_v.begin(), cell_v.end(),
                  [](float v) { return v > 4.20f; })
);
```

### `std::vector` — Dynamic (AUTOSAR Adaptive only)

```cpp
#include <vector>

// DTC list — size unknown at compile time
std::vector<uint32_t> active_dtcs;
active_dtcs.reserve(64U);  // Pre-allocate to avoid reallocations

active_dtcs.push_back(0xD00100U);
active_dtcs.push_back(0xD00200U);

// Sort and deduplicate
std::sort(active_dtcs.begin(), active_dtcs.end());
auto last = std::unique(active_dtcs.begin(), active_dtcs.end());
active_dtcs.erase(last, active_dtcs.end());

// Remove a specific DTC
active_dtcs.erase(
    std::remove(active_dtcs.begin(), active_dtcs.end(), 0xD00100U),
    active_dtcs.end()
);
```

### `std::map` — Key-Value (AUTOSAR Adaptive)

```cpp
#include <map>
#include <string>

// DID to signal decoder map
std::map<uint16_t, std::string> did_name_map = {
    {0xF190U, "SoC_pct"},
    {0xF191U, "SoH_pct"},
    {0xF192U, "PackVoltage_V"},
    {0xF193U, "PackCurrent_A"},
    {0xF194U, "MaxCellVoltage_V"}
};

std::string get_did_name(uint16_t did) {
    auto it = did_name_map.find(did);
    return (it != did_name_map.end()) ? it->second : "Unknown_DID";
}

// Callback registration map (event routing)
std::unordered_map<uint32_t, std::function<void(const uint8_t*)>> msg_callbacks;
msg_callbacks[0x3A0U] = [](const uint8_t* d) { bms.on_cell_voltage(d); };
msg_callbacks[0x3B0U] = [](const uint8_t* d) { bms.on_pack_status(d); };
```

### `std::deque` — CAN Frame History Buffer

```cpp
#include <deque>

constexpr std::size_t FRAME_HISTORY_SIZE = 100U;
std::deque<CanFrame> frame_history;

void record_frame(const CanFrame& frame) {
    if (frame_history.size() >= FRAME_HISTORY_SIZE) {
        frame_history.pop_front();  // Remove oldest
    }
    frame_history.push_back(frame);
}

// Replay last N frames for analysis
void replay_frames(std::size_t count) {
    auto start = frame_history.size() > count
                ? frame_history.end() - count
                : frame_history.begin();
    for (auto it = start; it != frame_history.end(); ++it) {
        inject_can_frame(*it);
    }
}
```

---

## 7. STL Algorithms in Automotive Testing

```cpp
#include <algorithm>
#include <numeric>

// Voltage statistics for HIL test validation
std::array<float, 96U> voltages = get_cell_voltages();

// Mean
float sum = std::accumulate(voltages.begin(), voltages.end(), 0.0f);
float mean = sum / static_cast<float>(voltages.size());

// Standard deviation
float variance = std::accumulate(voltages.begin(), voltages.end(), 0.0f,
    [mean](float acc, float v) {
        float diff = v - mean;
        return acc + diff * diff;
    }) / static_cast<float>(voltages.size());
float std_dev = std::sqrt(variance);

// All cells within valid range
bool all_valid = std::all_of(voltages.begin(), voltages.end(),
    [](float v) { return v >= 2.5f && v <= 4.25f; });

// Find first fault cell
auto it = std::find_if(voltages.begin(), voltages.end(),
    [](float v) { return v > 4.20f; });
if (it != voltages.end()) {
    uint8_t fault_cell = static_cast<uint8_t>(std::distance(voltages.begin(), it));
}

// Sort cells by voltage (for balancing priority)
std::array<uint8_t, 96U> cell_ids;
std::iota(cell_ids.begin(), cell_ids.end(), 0U);  // Fill 0..95
std::sort(cell_ids.begin(), cell_ids.end(),
    [&voltages](uint8_t a, uint8_t b) {
        return voltages[a] > voltages[b];  // Highest voltage first
    });
```

---

## 8. `std::optional` — Safe Value Return (C++17)

```cpp
#include <optional>

// Return nullopt when measurement unavailable
std::optional<float> read_isolation_resistance(void) {
    if (!imd_sensor.is_ready()) return std::nullopt;
    float r_iso = imd_sensor.get_value();
    if (r_iso < 0.0f) return std::nullopt;  // Invalid
    return r_iso;
}

// Usage
auto r_iso = read_isolation_resistance();
if (r_iso.has_value()) {
    if (r_iso.value() < 500.0f) {
        report_isolation_fault();
    }
}

// With default fallback
float safe_r = read_isolation_resistance().value_or(0.0f);

// Chain with transform (C++23) or manual
auto resistance_ok = read_isolation_resistance()
    .transform([](float r) { return r >= 500.0f; })
    .value_or(false);
```

---

## 9. `std::variant` — Multi-Type Signal Value (C++17)

```cpp
#include <variant>

// CAN signal can be bool, uint8_t, uint16_t, int16_t, or float
using SignalValue = std::variant<bool, uint8_t, uint16_t, int16_t, float>;

struct CanSignal {
    std::string  name;
    SignalValue  value;
    uint32_t     timestamp_ms;
};

void print_signal(const CanSignal& sig) {
    std::visit([&sig](auto&& val) {
        using T = std::decay_t<decltype(val)>;
        if constexpr (std::is_same_v<T, bool>) {
            printf("%s = %s\n", sig.name.c_str(), val ? "TRUE" : "FALSE");
        } else if constexpr (std::is_same_v<T, float>) {
            printf("%s = %.3f\n", sig.name.c_str(), val);
        } else {
            printf("%s = %lu\n", sig.name.c_str(), static_cast<unsigned long>(val));
        }
    }, sig.value);
}

// Usage
CanSignal soc_signal{"SoC_pct", float{85.5f}, 12500U};
CanSignal fault_signal{"FaultActive", bool{true}, 12510U};
print_signal(soc_signal);
print_signal(fault_signal);
```

---

## 10. `std::chrono` — Timing in Test Frameworks

```cpp
#include <chrono>

using namespace std::chrono;

class ResponseTimer {
public:
    void start(void) {
        start_time_ = steady_clock::now();
    }

    milliseconds elapsed(void) const {
        return duration_cast<milliseconds>(steady_clock::now() - start_time_);
    }

    bool has_timeout(milliseconds timeout) const {
        return elapsed() >= timeout;
    }

private:
    steady_clock::time_point start_time_;
};

// HIL test timing validation
bool test_ov2_response_time(void) {
    ResponseTimer timer;

    inject_cell_voltage(7U, 4.26f);   // Trigger OV2
    timer.start();

    while (!timer.has_timeout(milliseconds{200U})) {
        if (get_contactor_state() == OPEN) {
            auto response_ms = timer.elapsed().count();
            printf("OV2 response time: %lld ms (limit: 100ms)\n", response_ms);
            return response_ms <= 100LL;
        }
        std::this_thread::sleep_for(milliseconds{1U});
    }
    printf("FAIL: OV2 contactor did not open within 200ms\n");
    return false;
}
```

---

## 11. Template Metaprogramming — Compile-Time CRC

```cpp
// Compile-time CRC8 table generation
template<uint8_t Poly>
constexpr uint8_t crc8_byte(uint8_t byte) {
    uint8_t crc = byte;
    for (uint8_t i = 0U; i < 8U; ++i) {
        crc = (crc & 0x80U) ? ((crc << 1U) ^ Poly) : (crc << 1U);
    }
    return crc;
}

// CRC8 SAE J1850 (AUTOSAR E2E Profile 1)
constexpr uint8_t CRC8_POLY = 0x1DU;

uint8_t compute_e2e_crc(const uint8_t* data, uint8_t length) {
    uint8_t crc = 0xFFU;
    for (uint8_t i = 0U; i < length; ++i) {
        crc = crc8_byte<CRC8_POLY>(crc ^ data[i]);
    }
    return crc ^ 0xFFU;
}

// Usage — AUTOSAR E2E protection
uint8_t frame[8U] = {0x01U, 0x85U, 0x10U, 0x0AU, 0x00U, 0x00U, 0x00U};
frame[7U] = compute_e2e_crc(frame, 7U);  // Last byte = CRC
```

---

*File: 04_cpp_templates_stl.md | cpp_automotive study series*
