#pragma once

#include "../can/can_bus.hpp"
#include "../uds/uds_server.hpp"
#include "dtc_manager.hpp"
#include <cstdint>
#include <string>

namespace automotive {
namespace ecu {

/// Overall ECU operating state
enum class ECUState : uint8_t {
    POWER_OFF   = 0U,
    BOOT        = 1U,
    INIT        = 2U,
    RUNNING     = 3U,
    SHUTDOWN    = 4U,
    SAFE_STATE  = 5U,   ///< Fault detected – limited functionality
    ERROR       = 6U,
};

/// Live ECU signal data (updated by application/simulation layer)
struct ECUSignals {
    int16_t  engineRPM{0};          ///< Engine speed in RPM
    uint8_t  vehicleSpeed{0U};      ///< km/h
    int8_t   coolantTemp{-40};      ///< °C
    uint8_t  throttlePos{0U};       ///< 0–100 %
    uint8_t  engineLoad{0U};        ///< 0–100 %
    uint16_t batteryVoltage{1200U}; ///< mV × 10 (i.e. 1200 = 12.00V)
    bool     ignitionOn{false};
    bool     engineRunning{false};
};

/**
 * @brief Top-level ECU simulation core.
 *
 * Integrates:
 *  - CAN Bus driver (Tx/Rx)
 *  - UDS Server (diagnostics)
 *  - DTC Manager
 *  - Cyclic task scheduling
 *  - Signal transmission (periodic CAN messages)
 *
 * Run loop:
 *   1. Call initialize()
 *   2. Call cyclic_1ms() every 1ms
 *   3. Update signals via setSignals()
 *   4. Call shutdown() when done
 */
class ECUCore {
public:
    static constexpr uint32_t CAN_ID_ENGINE_STATUS  = 0x100U;  ///< Tx: Engine status
    static constexpr uint32_t CAN_ID_VEHICLE_STATUS = 0x200U;  ///< Tx: Vehicle status
    static constexpr uint32_t CAN_ID_DIAG_REQ       = 0x7E0U;  ///< Rx: UDS request (physical)
    static constexpr uint32_t CAN_ID_DIAG_FUNC      = 0x7DFU;  ///< Rx: UDS request (functional)
    static constexpr uint32_t CAN_ID_DIAG_RESP      = 0x7E8U;  ///< Tx: UDS response

    explicit ECUCore(const std::string& ecuName,
                     can::CANBus& canBus);
    ~ECUCore();

    ECUCore(const ECUCore&) = delete;
    ECUCore& operator=(const ECUCore&) = delete;

    // --- Lifecycle ---
    bool initialize();
    void shutdown();

    /**
     * @brief Main 1ms cyclic function – must be called every 1ms
     */
    void cyclic_1ms();

    // --- Application interface ---
    void setSignals(const ECUSignals& signals) noexcept { m_signals = signals; }
    const ECUSignals& getSignals() const noexcept { return m_signals; }

    ECUState getState() const noexcept { return m_state; }
    const std::string& getName() const noexcept { return m_name; }

    DTCManager&         getDTCManager()  noexcept { return m_dtcManager; }
    uds::UDSServer&     getUDSServer()   noexcept { return m_udsServer; }
    can::CANBus&        getCANBus()      noexcept { return m_canBus; }

    /// Simulate an ignition key on event
    void keyOn();
    /// Simulate an ignition key off event
    void keyOff();

    /// Inject a fault to simulate a DTC
    void injectFault(uint32_t dtcCode, ecu::DTCSeverity severity = DTCSeverity::CHECK_AT_NEXT_HALT);

private:
    // Cyclic task handlers (called from cyclic_1ms at different periods)
    void task_1ms();
    void task_10ms();
    void task_100ms();

    // CAN transmit helpers
    void txEngineStatus();
    void txVehicleStatus();

    // UDS DID initialization
    void registerDiagDIDs();

    // State machine
    void processStateMachine();
    void enterState(ECUState newState);

    std::string  m_name;
    can::CANBus& m_canBus;
    DTCManager   m_dtcManager{};
    uds::UDSServer m_udsServer;

    ECUState   m_state{ECUState::POWER_OFF};
    ECUSignals m_signals{};

    uint32_t m_tickMs{0U};      ///< Total 1ms ticks since init
    uint8_t  m_task10Counter{0U};
    uint8_t  m_task100Counter{0U};

    // Reserved for future Tx scheduling timers
    // uint32_t m_txEngineStatusTimer{0U};
    // uint32_t m_txVehicleStatusTimer{0U};
};

} // namespace ecu
} // namespace automotive
