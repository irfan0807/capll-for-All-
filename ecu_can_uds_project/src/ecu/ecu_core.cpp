#include "../../include/ecu/ecu_core.hpp"
#include <cstdio>
#include <cstring>

namespace automotive {
namespace ecu {

// ─── Well-known DID values ────────────────────────────────────────────────────
static const uint8_t DID_VIN_DATA[]     = "W0LZZZ23456789001";   // 17 bytes
static const uint8_t DID_SW_VERSION[]   = { 0x01U, 0x02U, 0x03U };
static const uint8_t DID_HW_NUMBER[]    = { 0x55U, 0xAAU };
static const uint8_t DID_ECU_SERIAL[]   = { 0x12U, 0x34U, 0x56U, 0x78U };
static const uint8_t DID_ACTIVE_SESSION[]= { 0x01U };             // Default

// ─── Constructor / Destructor ─────────────────────────────────────────────────

ECUCore::ECUCore(const std::string& ecuName, can::CANBus& canBus)
    : m_name(ecuName)
    , m_canBus(canBus)
    , m_udsServer(canBus, CAN_ID_DIAG_REQ, CAN_ID_DIAG_FUNC, CAN_ID_DIAG_RESP)
    , m_state(ECUState::POWER_OFF)
    , m_tickMs(0U)
    , m_task10Counter(0U)
    , m_task100Counter(0U)
{
}

ECUCore::~ECUCore() {
    shutdown();
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────

bool ECUCore::initialize() {
    if (m_state != ECUState::POWER_OFF) {
        return true;
    }
    std::printf("[ECU:%s] Initializing...\n", m_name.c_str());
    enterState(ECUState::BOOT);

    if (!m_canBus.initialize()) {
        std::printf("[ECU:%s] CAN Bus initialization FAILED\n", m_name.c_str());
        enterState(ECUState::ERROR);
        return false;
    }

    if (!m_udsServer.initialize()) {
        std::printf("[ECU:%s] UDS Server initialization FAILED\n", m_name.c_str());
        enterState(ECUState::ERROR);
        return false;
    }

    registerDiagDIDs();
    enterState(ECUState::INIT);

    std::printf("[ECU:%s] Initialization complete\n", m_name.c_str());
    return true;
}

void ECUCore::shutdown() {
    if (m_state == ECUState::POWER_OFF) return;
    enterState(ECUState::SHUTDOWN);
    m_udsServer.shutdown();
    m_canBus.shutdown();
    enterState(ECUState::POWER_OFF);
    std::printf("[ECU:%s] Shutdown complete\n", m_name.c_str());
}

// ─── Cyclic Execution ─────────────────────────────────────────────────────────

void ECUCore::cyclic_1ms() {
    m_tickMs++;

    // Process CAN Rx queue (dispatches to UDS server callbacks)
    m_canBus.processRxQueue();

    // UDS server heartbeat
    m_udsServer.cyclic();

    // 1ms tasks
    task_1ms();

    // 10ms tasks
    m_task10Counter++;
    if (m_task10Counter >= 10U) {
        m_task10Counter = 0U;
        task_10ms();
    }

    // 100ms tasks
    m_task100Counter++;
    if (m_task100Counter >= 100U) {
        m_task100Counter = 0U;
        task_100ms();
    }
}

void ECUCore::task_1ms() {
    // Fast sensor polling, closed-loop control would go here
}

void ECUCore::task_10ms() {
    processStateMachine();

    if (m_state == ECUState::RUNNING) {
        // Transmit Engine Status frame every 10ms
        txEngineStatus();
    }
}

void ECUCore::task_100ms() {
    if (m_state == ECUState::RUNNING) {
        txVehicleStatus();
    }

    // Update live DIDs with current signal values
    if (m_state == ECUState::RUNNING) {
        // RPM  (DID 0xF4AB – custom)
        uint16_t rpm = static_cast<uint16_t>(m_signals.engineRPM);
        uint8_t rpmData[2] = {
            static_cast<uint8_t>(rpm >> 8U),
            static_cast<uint8_t>(rpm & 0xFFU)
        };
        m_udsServer.updateDIDData(0xF4ABU, rpmData, 2U);

        // Coolant temp (DID 0xF405 – custom)
        uint8_t tempData[1] = { static_cast<uint8_t>(m_signals.coolantTemp + 40) };
        m_udsServer.updateDIDData(0xF405U, tempData, 1U);
    }
}

// ─── CAN Transmit ─────────────────────────────────────────────────────────────

void ECUCore::txEngineStatus() {
    // CAN ID 0x100 – Engine Status (8 bytes)
    // Byte 0-1: Engine RPM (uint16, factor=0.25, offset=0)
    // Byte 2:   Coolant Temp (uint8, factor=1, offset=-40)
    // Byte 3:   Engine Load (uint8, factor=0.392)
    // Byte 4:   Throttle Position (uint8, factor=0.392)
    // Byte 5:   Ignition/Engine flags
    // Byte 6-7: Battery voltage (uint16, mV × 10)

    uint16_t rpmRaw = static_cast<uint16_t>(
        static_cast<float>(m_signals.engineRPM) / 0.25f);

    uint8_t data[8]{};
    data[0] = static_cast<uint8_t>(rpmRaw >> 8U);
    data[1] = static_cast<uint8_t>(rpmRaw & 0xFFU);
    data[2] = static_cast<uint8_t>(m_signals.coolantTemp + 40);
    data[3] = m_signals.engineLoad;
    data[4] = m_signals.throttlePos;
    data[5] = static_cast<uint8_t>(
        (m_signals.ignitionOn    ? 0x01U : 0x00U) |
        (m_signals.engineRunning ? 0x02U : 0x00U));
    data[6] = static_cast<uint8_t>(m_signals.batteryVoltage >> 8U);
    data[7] = static_cast<uint8_t>(m_signals.batteryVoltage & 0xFFU);

    m_canBus.transmit(CAN_ID_ENGINE_STATUS, data, 8U);
}

void ECUCore::txVehicleStatus() {
    // CAN ID 0x200 – Vehicle Status (4 bytes)
    // Byte 0:   Vehicle speed (km/h)
    // Byte 1:   Gear position
    // Byte 2-3: Odometer (km, 16-bit placeholder)
    uint8_t data[4]{};
    data[0] = m_signals.vehicleSpeed;
    data[1] = 0x00U;   // Gear: P
    data[2] = 0x00U;
    data[3] = 0x00U;
    m_canBus.transmit(CAN_ID_VEHICLE_STATUS, data, 4U);
}

// ─── State Machine ────────────────────────────────────────────────────────────

void ECUCore::processStateMachine() {
    switch (m_state) {
        case ECUState::INIT:
            if (m_signals.ignitionOn) {
                enterState(ECUState::RUNNING);
            }
            break;

        case ECUState::RUNNING:
            if (!m_signals.ignitionOn && !m_signals.engineRunning) {
                enterState(ECUState::SHUTDOWN);
            }
            // Check for critical faults
            if (m_dtcManager.countDTCsByStatusMask(
                    ecu::DTCStatusBit::CONFIRMED | ecu::DTCStatusBit::WARNING_INDICATOR) > 10U) {
                enterState(ECUState::SAFE_STATE);
            }
            break;

        case ECUState::SHUTDOWN:
            // Wait for a few cycles then power off
            static uint8_t shutdownCounter = 0U;
            shutdownCounter++;
            if (shutdownCounter > 10U) {
                shutdownCounter = 0U;
                enterState(ECUState::POWER_OFF);
            }
            break;

        default:
            break;
    }
}

void ECUCore::enterState(ECUState newState) {
    static const char* stateNames[] = {
        "POWER_OFF", "BOOT", "INIT", "RUNNING", "SHUTDOWN", "SAFE_STATE", "ERROR"
    };
    std::printf("[ECU:%s] State: %s → %s\n",
                m_name.c_str(),
                stateNames[static_cast<uint8_t>(m_state)],
                stateNames[static_cast<uint8_t>(newState)]);
    m_state = newState;
}

// ─── Public control ───────────────────────────────────────────────────────────

void ECUCore::keyOn() {
    m_signals.ignitionOn = true;
    std::printf("[ECU:%s] Ignition ON\n", m_name.c_str());
}

void ECUCore::keyOff() {
    m_signals.ignitionOn    = false;
    m_signals.engineRunning = false;
    m_signals.engineRPM     = 0;
    std::printf("[ECU:%s] Ignition OFF\n", m_name.c_str());
}

void ECUCore::injectFault(uint32_t dtcCode, DTCSeverity severity) {
    DTCSnapshot snap{};
    snap.engineRPM    = m_signals.engineRPM;
    snap.coolantTemp  = m_signals.coolantTemp;
    snap.throttlePos  = m_signals.throttlePos;
    snap.engineLoad   = m_signals.engineLoad;
    snap.vehicleSpeed = m_signals.vehicleSpeed;
    snap.timestamp    = m_tickMs;
    snap.valid        = 1U;

    m_dtcManager.setDTC(dtcCode, severity, &snap);
}

// ─── DID Registration ─────────────────────────────────────────────────────────

void ECUCore::registerDiagDIDs() {
    using S = uds::DiagSession;

    // Standard ISO DIDs
    m_udsServer.registerDID(0xF190U, DID_VIN_DATA,      17U, true,  false, S::DEFAULT,             S::EXTENDED_DIAGNOSTIC);
    m_udsServer.registerDID(0xF194U, DID_SW_VERSION,     3U, true,  false, S::DEFAULT,             S::EXTENDED_DIAGNOSTIC);
    m_udsServer.registerDID(0xF191U, DID_HW_NUMBER,      2U, true,  false, S::DEFAULT,             S::EXTENDED_DIAGNOSTIC);
    m_udsServer.registerDID(0xF18CU, DID_ECU_SERIAL,     4U, true,  false, S::DEFAULT,             S::EXTENDED_DIAGNOSTIC);
    m_udsServer.registerDID(0xF186U, DID_ACTIVE_SESSION, 1U, true,  false, S::DEFAULT,             S::DEFAULT);

    // Custom / application-specific DIDs
    uint8_t rpmInit[2]  = { 0x00U, 0x00U };
    uint8_t tempInit[1] = { 0x00U };
    m_udsServer.registerDID(0xF4ABU, rpmInit,  2U, true,  false, S::EXTENDED_DIAGNOSTIC, S::EXTENDED_DIAGNOSTIC);
    m_udsServer.registerDID(0xF405U, tempInit, 1U, true,  false, S::EXTENDED_DIAGNOSTIC, S::EXTENDED_DIAGNOSTIC);

    std::printf("[ECU:%s] Registered %u diagnostic DIDs\n", m_name.c_str(), 7U);
}

} // namespace ecu
} // namespace automotive
