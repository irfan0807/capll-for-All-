# C++ Object-Oriented Programming for Automotive Software

> **Coverage:** Classes, Inheritance, Polymorphism, Encapsulation, Design Patterns
> **Context:** ECU Software Architecture, AUTOSAR SWC, HIL Frameworks, Diagnostics Clients

---

## 1. Classes & Encapsulation

### ECU Software Component (SWC) Pattern

```cpp
// bms_monitor.hpp
#ifndef BMS_MONITOR_HPP
#define BMS_MONITOR_HPP

#include <cstdint>
#include "can_driver.hpp"
#include "dtc_manager.hpp"

class BmsMonitor {
public:
    // Constructors
    explicit BmsMonitor(CanDriver& can, DtcManager& dtc);

    // Delete copy/move (singleton hardware resource)
    BmsMonitor(const BmsMonitor&)            = delete;
    BmsMonitor& operator=(const BmsMonitor&) = delete;

    // Public interface — SWC RunEntity equivalent
    void init(void);
    void cyclic_10ms(void);
    void cyclic_100ms(void);

    // Read-only accessors
    float    get_soc(void)         const;
    float    get_pack_voltage(void) const;
    uint8_t  get_fault_level(void)  const;
    bool     is_hv_ready(void)      const;

private:
    // Private data members — MISRA 11-0-1
    CanDriver&  can_;
    DtcManager& dtc_;

    float    soc_pct_    = 0.0f;
    float    pack_v_     = 0.0f;
    uint16_t cell_v_[96] = {0U};
    int8_t   cell_t_[8]  = {0};
    uint8_t  fault_level_ = 0U;
    bool     hv_ready_    = false;

    // Private methods
    void check_voltage_protection(void);
    void check_thermal_protection(void);
    void calculate_soc(float delta_ah);
    void transmit_status_can(void);
};

#endif // BMS_MONITOR_HPP
```

```cpp
// bms_monitor.cpp
#include "bms_monitor.hpp"

BmsMonitor::BmsMonitor(CanDriver& can, DtcManager& dtc)
    : can_(can), dtc_(dtc) {}

void BmsMonitor::init(void) {
    can_.register_rx_callback(0x3A0U, [this](const CanFrame& f){ on_cell_voltage_rx(f); });
    fault_level_ = 0U;
    hv_ready_ = false;
}

void BmsMonitor::cyclic_10ms(void) {
    check_voltage_protection();
    check_thermal_protection();
}

void BmsMonitor::cyclic_100ms(void) {
    calculate_soc(0.0f);
    transmit_status_can();
}

float BmsMonitor::get_soc(void) const { return soc_pct_; }
bool  BmsMonitor::is_hv_ready(void) const { return hv_ready_; }
```

---

## 2. Inheritance — Sensor Base Class

```cpp
// Base class — pure interface
class Sensor {
public:
    virtual ~Sensor() = default;

    virtual bool     init(void)     = 0;
    virtual bool     read(void)     = 0;
    virtual float    get_value(void) const = 0;
    virtual bool     is_valid(void)  const = 0;
    virtual uint32_t get_error_code(void) const = 0;

protected:
    float    value_  = 0.0f;
    bool     valid_  = false;
    uint32_t error_  = 0U;
};

// Derived — NTC temperature sensor
class NtcTemperatureSensor : public Sensor {
public:
    explicit NtcTemperatureSensor(uint8_t adc_channel, float ref_resistance)
        : adc_ch_(adc_channel), r_ref_(ref_resistance) {}

    bool init(void) override {
        adc_init(adc_ch_);
        return true;
    }

    bool read(void) override {
        uint16_t raw = adc_read(adc_ch_);
        if (raw == 0xFFFFU) {
            error_ = 0x0001U;  // Open circuit
            valid_ = false;
            return false;
        }
        float r_ntc = r_ref_ * static_cast<float>(raw) / (4095.0f - static_cast<float>(raw));
        value_ = ntc_to_celsius(r_ntc);
        valid_ = true;
        return true;
    }

    float    get_value(void)      const override { return value_; }
    bool     is_valid(void)       const override { return valid_; }
    uint32_t get_error_code(void) const override { return error_; }

private:
    uint8_t adc_ch_;
    float   r_ref_;

    static float ntc_to_celsius(float r) {
        // Steinhart–Hart simplified: 1/T = 1/T0 + (1/B)*ln(R/R0)
        constexpr float B  = 3950.0f;
        constexpr float T0 = 298.15f;
        constexpr float R0 = 10000.0f;
        return 1.0f / (1.0f/T0 + (1.0f/B) * logf(r / R0)) - 273.15f;
    }
};

// Derived — Hall effect current sensor
class HallCurrentSensor : public Sensor {
public:
    explicit HallCurrentSensor(uint8_t adc_channel, float sensitivity_mv_per_a)
        : adc_ch_(adc_channel), sensitivity_(sensitivity_mv_per_a) {}

    bool init(void) override { adc_init(adc_ch_); return true; }
    bool read(void) override {
        uint16_t raw = adc_read(adc_ch_);
        float vout_mv = static_cast<float>(raw) * (3300.0f / 4095.0f);
        value_ = (vout_mv - 1650.0f) / sensitivity_;  // Bipolar, 1.65V = 0A
        valid_ = true;
        return true;
    }
    float    get_value(void)      const override { return value_; }
    bool     is_valid(void)       const override { return valid_; }
    uint32_t get_error_code(void) const override { return error_; }

private:
    uint8_t adc_ch_;
    float   sensitivity_;
};
```

---

## 3. Polymorphism — Sensor Manager

```cpp
// Runtime polymorphism — array of base pointers
class SensorManager {
public:
    static constexpr uint8_t MAX_SENSORS = 16U;

    bool register_sensor(Sensor* sensor) {
        if (count_ >= MAX_SENSORS) return false;
        sensors_[count_++] = sensor;
        return true;
    }

    void init_all(void) {
        for (uint8_t i = 0U; i < count_; ++i) {
            sensors_[i]->init();
        }
    }

    void read_all(void) {
        for (uint8_t i = 0U; i < count_; ++i) {
            sensors_[i]->read();
        }
    }

    bool all_valid(void) const {
        for (uint8_t i = 0U; i < count_; ++i) {
            if (!sensors_[i]->is_valid()) return false;
        }
        return true;
    }

private:
    Sensor* sensors_[MAX_SENSORS] = {nullptr};
    uint8_t count_ = 0U;
};

// Usage
NtcTemperatureSensor t1(0U, 10000.0f);
NtcTemperatureSensor t2(1U, 10000.0f);
HallCurrentSensor    cs(2U, 66.0f);

SensorManager mgr;
mgr.register_sensor(&t1);
mgr.register_sensor(&t2);
mgr.register_sensor(&cs);
mgr.init_all();
mgr.read_all();
```

---

## 4. Design Patterns in Automotive ECU Software

### Pattern 1: Singleton — CAN Bus Driver

```cpp
class CanBus {
public:
    static CanBus& get_instance(void) {
        static CanBus instance;  // C++11 guaranteed thread-safe
        return instance;
    }

    bool transmit(uint32_t id, const uint8_t* data, uint8_t dlc);
    bool receive(uint32_t& id, uint8_t* data, uint8_t& dlc);

private:
    CanBus()  = default;
    ~CanBus() = default;
    CanBus(const CanBus&)            = delete;
    CanBus& operator=(const CanBus&) = delete;
};

// Usage
CanBus::get_instance().transmit(0x3A1U, data, 8U);
```

### Pattern 2: Observer — Fault Event Notification

```cpp
// Observer interface
class FaultObserver {
public:
    virtual ~FaultObserver() = default;
    virtual void on_fault_detected(uint32_t dtc_code, uint8_t severity) = 0;
    virtual void on_fault_cleared(uint32_t dtc_code) = 0;
};

// Subject
class FaultManager {
public:
    static constexpr uint8_t MAX_OBSERVERS = 8U;

    void subscribe(FaultObserver* obs) {
        if (obs_count_ < MAX_OBSERVERS) {
            observers_[obs_count_++] = obs;
        }
    }

    void report_fault(uint32_t dtc, uint8_t severity) {
        store_dtc(dtc, severity);
        for (uint8_t i = 0U; i < obs_count_; ++i) {
            observers_[i]->on_fault_detected(dtc, severity);
        }
    }

private:
    FaultObserver* observers_[MAX_OBSERVERS] = {nullptr};
    uint8_t obs_count_ = 0U;
    void store_dtc(uint32_t dtc, uint8_t sev) { /* write to NVM */ }
};

// Concrete observer — Dashboard warning light
class DashboardController : public FaultObserver {
public:
    void on_fault_detected(uint32_t dtc_code, uint8_t severity) override {
        if (severity >= 2U) {
            illuminate_mil_lamp();
        }
    }
    void on_fault_cleared(uint32_t dtc_code) override {
        extinguish_mil_lamp();
    }
};
```

### Pattern 3: Strategy — SoC Algorithm Selection

```cpp
// Strategy interface
class SoCAlgorithm {
public:
    virtual ~SoCAlgorithm() = default;
    virtual float calculate(float current_a, float dt_s, float ocv_v) = 0;
    virtual const char* name(void) const = 0;
};

// Coulomb Counting strategy
class CoulombCounting : public SoCAlgorithm {
public:
    explicit CoulombCounting(float capacity_ah)
        : capacity_as_(capacity_ah * 3600.0f) {}

    float calculate(float current_a, float dt_s, float /*ocv_v*/) override {
        accumulated_as_ += current_a * dt_s;
        soc_ = 1.0f - (accumulated_as_ / capacity_as_);
        soc_ = (soc_ < 0.0f) ? 0.0f : (soc_ > 1.0f) ? 1.0f : soc_;
        return soc_ * 100.0f;
    }
    const char* name(void) const override { return "CoulombCounting"; }

private:
    float capacity_as_;
    float accumulated_as_ = 0.0f;
    float soc_ = 1.0f;
};

// Extended Kalman Filter strategy
class EkfSoC : public SoCAlgorithm {
public:
    float calculate(float current_a, float dt_s, float ocv_v) override {
        // Predict: x_k = x_(k-1) - (eta * I * dt) / Q
        constexpr float ETA = 0.98f;   // Coulombic efficiency
        constexpr float Q   = 216000.0f;  // 60Ah in Coulombs
        x_hat_ -= (ETA * current_a * dt_s) / Q;

        // Correction using OCV-SoC lookup
        float soc_from_ocv = ocv_to_soc(ocv_v);
        float innovation   = soc_from_ocv - x_hat_;
        x_hat_            += K_ * innovation;

        return x_hat_ * 100.0f;
    }
    const char* name(void) const override { return "EKF"; }

private:
    float x_hat_ = 1.0f;
    float K_     = 0.15f;   // Kalman gain (simplified)
    static float ocv_to_soc(float ocv);
};

// Context class
class SoCEstimator {
public:
    void set_algorithm(SoCAlgorithm* algo) { algo_ = algo; }
    float update(float current_a, float dt_s, float ocv_v) {
        if (algo_ == nullptr) return -1.0f;
        return algo_->calculate(current_a, dt_s, ocv_v);
    }
private:
    SoCAlgorithm* algo_ = nullptr;
};
```

### Pattern 4: Command — UDS Diagnostic Services

```cpp
// Command interface
class UDSCommand {
public:
    virtual ~UDSCommand() = default;
    virtual bool execute(const uint8_t* request, uint8_t req_len,
                         uint8_t* response, uint8_t& res_len) = 0;
    virtual uint8_t service_id(void) const = 0;
};

// Concrete command — Read Data By Identifier (0x22)
class ReadDBI : public UDSCommand {
public:
    bool execute(const uint8_t* req, uint8_t req_len,
                 uint8_t* resp, uint8_t& resp_len) override {
        if (req_len < 3U) return false;
        uint16_t did = static_cast<uint16_t>((req[1] << 8U) | req[2]);

        resp[0] = 0x62U;    // Positive response SID
        resp[1] = req[1];
        resp[2] = req[2];

        switch (did) {
            case 0xF190U:
                resp[3] = static_cast<uint8_t>(BmsMonitor::get_soc() * 2.0f);
                resp_len = 4U;
                break;
            default:
                resp[0] = 0x7FU;         // NRC
                resp[1] = 0x22U;
                resp[2] = 0x31U;         // requestOutOfRange
                resp_len = 3U;
                return false;
        }
        return true;
    }
    uint8_t service_id(void) const override { return 0x22U; }
};

// Dispatcher
class UDSServer {
public:
    static constexpr uint8_t MAX_SERVICES = 16U;

    void register_service(UDSCommand* cmd) {
        if (svc_count_ < MAX_SERVICES) services_[svc_count_++] = cmd;
    }

    bool dispatch(const uint8_t* req, uint8_t req_len,
                  uint8_t* resp, uint8_t& resp_len) {
        for (uint8_t i = 0U; i < svc_count_; ++i) {
            if (services_[i]->service_id() == req[0]) {
                return services_[i]->execute(req, req_len, resp, resp_len);
            }
        }
        resp[0] = 0x7FU; resp[1] = req[0]; resp[2] = 0x11U;  // serviceNotSupported
        resp_len = 3U;
        return false;
    }

private:
    UDSCommand* services_[MAX_SERVICES] = {nullptr};
    uint8_t svc_count_ = 0U;
};
```

### Pattern 5: Factory — Multi-Variant ECU Configuration

```cpp
enum class VehicleVariant { SEDAN_EV, SUV_PHEV, TRUCK_HEV };

class BatteryConfig {
public:
    virtual ~BatteryConfig() = default;
    virtual uint8_t  num_cells(void)       const = 0;
    virtual float    capacity_ah(void)     const = 0;
    virtual float    nominal_voltage(void) const = 0;
    virtual uint16_t ov2_threshold_mv(void) const = 0;
};

class NMC_60kWh : public BatteryConfig {
public:
    uint8_t  num_cells(void)        const override { return 96U; }
    float    capacity_ah(void)      const override { return 60.0f; }
    float    nominal_voltage(void)  const override { return 350.0f; }
    uint16_t ov2_threshold_mv(void) const override { return 4250U; }
};

class LFP_40kWh : public BatteryConfig {
public:
    uint8_t  num_cells(void)        const override { return 128U; }
    float    capacity_ah(void)      const override { return 40.0f; }
    float    nominal_voltage(void)  const override { return 409.6f; }
    uint16_t ov2_threshold_mv(void) const override { return 3650U; }
};

// Factory
class BatteryConfigFactory {
public:
    static BatteryConfig* create(VehicleVariant variant) {
        switch (variant) {
            case VehicleVariant::SEDAN_EV:  return new NMC_60kWh();
            case VehicleVariant::TRUCK_HEV: return new LFP_40kWh();
            default:                         return nullptr;
        }
    }
};
```

---

## 5. Operator Overloading — CAN Frame Type

```cpp
struct CanFrame {
    uint32_t id;
    uint8_t  dlc;
    uint8_t  data[8];

    // Equality comparison
    bool operator==(const CanFrame& rhs) const {
        if (id != rhs.id || dlc != rhs.dlc) return false;
        for (uint8_t i = 0U; i < dlc; ++i) {
            if (data[i] != rhs.data[i]) return false;
        }
        return true;
    }

    bool operator!=(const CanFrame& rhs) const { return !(*this == rhs); }

    // Less-than for sorting by ID
    bool operator<(const CanFrame& rhs) const { return id < rhs.id; }

    // Index operator — data byte access
    uint8_t& operator[](uint8_t index) { return data[index]; }
    const uint8_t& operator[](uint8_t index) const { return data[index]; }
};
```

---

## 6. RAII — Resource Acquisition Is Initialization

```cpp
// CAN bus mutex guard (RTOS context)
class CanBusMutexGuard {
public:
    explicit CanBusMutexGuard(OsMutex& mutex) : mutex_(mutex) {
        mutex_.lock();
    }
    ~CanBusMutexGuard(void) {
        mutex_.unlock();
    }
    // Non-copyable
    CanBusMutexGuard(const CanBusMutexGuard&)            = delete;
    CanBusMutexGuard& operator=(const CanBusMutexGuard&) = delete;
};

// Usage — mutex automatically released even on early return
bool transmit_safe(uint32_t id, const uint8_t* data, uint8_t dlc) {
    CanBusMutexGuard guard(can_mutex);
    if (dlc > 8U) return false;         // mutex released here
    hardware_tx(id, data, dlc);
    return true;                         // mutex released here
}   // mutex also released on exception (if enabled)
```

---

## 7. Smart Pointers (AUTOSAR Adaptive / C++14+)

```cpp
#include <memory>

// unique_ptr — sole ownership (preferred in AUTOSAR Adaptive)
auto bms = std::make_unique<BmsMonitor>(can_drv, dtc_mgr);
bms->init();
bms->cyclic_10ms();
// Automatically deleted when bms goes out of scope

// shared_ptr — shared ownership (use sparingly — overhead)
std::shared_ptr<CanBus> shared_can = std::make_shared<CanBus>();
auto bms2 = std::make_unique<BmsMonitor2>(shared_can);
auto vcu  = std::make_unique<VehicleController>(shared_can);

// weak_ptr — observe without owning (breaks cycles)
std::weak_ptr<CanBus> weak_can = shared_can;
if (auto locked = weak_can.lock()) {
    locked->transmit(0x3A1U, data, 8U);
}

// NOTE: Dynamic allocation (new/delete) is BANNED in AUTOSAR Classic
//       shared_ptr may be restricted — check project guidelines
```

---

## 8. Virtual Destructors & Object Slicing

```cpp
// ALWAYS declare virtual destructor in base class
class EcuComponent {
public:
    virtual ~EcuComponent(void) = default;  // Virtual destructor
    virtual void cyclic_10ms(void) = 0;
};

class BmsSwc : public EcuComponent {
public:
    ~BmsSwc(void) override {
        // Release BMS-specific resources
    }
    void cyclic_10ms(void) override { /* ... */ }

private:
    uint8_t* nvm_buffer_ = nullptr;
};

// Without virtual destructor: undefined behavior (slicing)
EcuComponent* comp = new BmsSwc();
delete comp;  // SAFE: virtual destructor ensures BmsSwc::~BmsSwc() is called
```

---

## 9. Multiple Inheritance — Interface Composition

```cpp
// Multiple pure-virtual interfaces (safe multi-inheritance)
class IDiagnosable {
public:
    virtual ~IDiagnosable() = default;
    virtual bool run_self_test(void) = 0;
    virtual uint32_t get_diagnostic_status(void) const = 0;
};

class ICalibrateable {
public:
    virtual ~ICalibrateable() = default;
    virtual bool calibrate(float reference) = 0;
    virtual bool is_calibrated(void) const = 0;
};

class IMonotonicClock {
public:
    virtual ~IMonotonicClock() = default;
    virtual uint32_t get_tick_ms(void) const = 0;
};

// Concrete class inherits all interfaces
class BmsModule : public IDiagnosable, public ICalibrateable {
public:
    bool run_self_test(void)     override { return check_hardware(); }
    uint32_t get_diagnostic_status(void) const override { return diag_status_; }
    bool calibrate(float ref)    override { cal_ref_ = ref; calibrated_ = true; return true; }
    bool is_calibrated(void)     const override { return calibrated_; }

private:
    uint32_t diag_status_ = 0U;
    float    cal_ref_     = 0.0f;
    bool     calibrated_  = false;
    bool check_hardware(void) { return true; }
};
```

---

## 10. Callable Objects & `std::function` (AUTOSAR Adaptive)

```cpp
#include <functional>

class EventRouter {
public:
    using Callback = std::function<void(uint32_t msg_id, const uint8_t* data)>;

    void register_callback(uint32_t msg_id, Callback cb) {
        callbacks_[msg_id] = cb;
    }

    void on_message(uint32_t msg_id, const uint8_t* data) {
        auto it = callbacks_.find(msg_id);
        if (it != callbacks_.end()) {
            it->second(msg_id, data);
        }
    }

private:
    std::map<uint32_t, Callback> callbacks_;
};

// Lambda registration
EventRouter router;
router.register_callback(0x3B0U, [&bms](uint32_t id, const uint8_t* data) {
    bms.on_soc_message(data);
});

// Member function binding
class Instrument {
public:
    void handle_rpm(uint32_t /*id*/, const uint8_t* data) {
        rpm_ = static_cast<uint16_t>((data[0] << 8U) | data[1]);
    }
private:
    uint16_t rpm_ = 0U;
};

Instrument cluster;
router.register_callback(0x316U,
    std::bind(&Instrument::handle_rpm, &cluster,
              std::placeholders::_1, std::placeholders::_2));
```

---

*File: 02_cpp_oop_automotive.md | cpp_automotive study series*
