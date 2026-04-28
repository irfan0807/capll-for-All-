/**
 * @file    main.cpp
 * @brief   ECU CAN/UDS Simulation – Entry Point
 *
 * This simulation demonstrates a complete automotive ECU lifecycle:
 *  1. Power-on / initialization
 *  2. Ignition key-on event
 *  3. Engine running – periodic CAN message transmission
 *  4. UDS diagnostic session interaction
 *  5. DTC fault injection and clearing
 *  6. Security access challenge-response
 *  7. Graceful shutdown
 *
 * Usage:
 *   Build with CMake (see CMakeLists.txt), then:
 *     ./ecu_simulation
 *
 * Output: Simulated CAN Tx frames + UDS service log to stdout
 */

#include <cstdio>
#include <cstring>
#include <cstdlib>

#include "can/can_bus.hpp"
#include "can/can_frame.hpp"
#include "uds/uds_server.hpp"
#include "ecu/ecu_core.hpp"

using namespace automotive;

// Forward-declared helper – advances the UDS server's internal tick
extern void UDSServer_AdvanceTick(uint32_t ms);

// ─── Simulation Scenario Helpers ─────────────────────────────────────────────

/**
 * Simulate multiple ECU cyclic ticks with optional elapsed-time acceleration
 */
static void runTicks(ecu::ECUCore& ecu, uint32_t count) {
    for (uint32_t i = 0; i < count; ++i) {
        ecu.cyclic_1ms();
        UDSServer_AdvanceTick(1U);
    }
}

/**
 * Inject a UDS request into the ECU's CAN bus as an ISO-TP Single Frame.
 * ISO-TP SF format: [0x0N | byte0=length, data bytes...]
 */
static void sendUDSRequest(can::CANBus& bus, uint32_t canId,
                            const uint8_t* data, uint8_t len)
{
    // Build ISO-TP Single Frame: byte[0] = (0x00 | length), rest = payload
    uint8_t isoTpFrame[8]{};
    isoTpFrame[0] = len & 0x0FU;   // SF PCI: upper nibble=0 (SF type), lower=length
    for (uint8_t i = 0; i < len && i < 7U; ++i) {
        isoTpFrame[i + 1U] = data[i];
    }
    bus.injectFrame(can::CANFrame(canId, static_cast<uint8_t>(len + 1U), isoTpFrame));
}

// ─── Scenario: ReadDataByIdentifier ──────────────────────────────────────────

static void scenario_ReadVIN(can::CANBus& bus, ecu::ECUCore& ecu) {
    std::printf("\n=== SCENARIO: ReadDataByIdentifier (VIN 0xF190) ===\n");
    uint8_t req[] = { 0x22U, 0xF1U, 0x90U };
    sendUDSRequest(bus, ecu::ECUCore::CAN_ID_DIAG_REQ, req, sizeof(req));
    runTicks(ecu, 5);
}

// ─── Scenario: DiagnosticSessionControl ──────────────────────────────────────

static void scenario_EnterExtendedSession(can::CANBus& bus, ecu::ECUCore& ecu) {
    std::printf("\n=== SCENARIO: Enter Extended Diagnostic Session (0x10 03) ===\n");
    uint8_t req[] = { 0x10U, 0x03U };
    sendUDSRequest(bus, ecu::ECUCore::CAN_ID_DIAG_REQ, req, sizeof(req));
    runTicks(ecu, 5);
}

// ─── Scenario: SecurityAccess ─────────────────────────────────────────────────

static void scenario_SecurityAccess(can::CANBus& bus, ecu::ECUCore& ecu) {
    std::printf("\n=== SCENARIO: Security Access (Seed/Key for level 1) ===\n");

    // Step 1: Request seed
    uint8_t reqSeed[] = { 0x27U, 0x01U };
    sendUDSRequest(bus, ecu::ECUCore::CAN_ID_DIAG_REQ, reqSeed, sizeof(reqSeed));
    runTicks(ecu, 5);

    // Step 2: Send correct key (Seed XOR 0x5A5A5A5A – same algorithm in server)
    // NOTE: In real test, the seed is read from the bus. We hard-code for simulation.
    // Seed comes from server response; here we compute expected key for a known seed.
    // The server uses calculateKey() = seed XOR 0x5A5A5A5A
    // For demonstration we send a fixed key (will only unlock if seed matches)
    uint8_t reqKey[] = { 0x27U, 0x02U, 0xFFU, 0xFFU, 0xFFU, 0xFFU };
    sendUDSRequest(bus, ecu::ECUCore::CAN_ID_DIAG_REQ, reqKey, sizeof(reqKey));
    runTicks(ecu, 5);
}

// ─── Scenario: DTC Fault Injection ────────────────────────────────────────────

static void scenario_DTCFaultAndRead(can::CANBus& bus, ecu::ECUCore& ecu) {
    std::printf("\n=== SCENARIO: Inject Fault DTC and Read DTCs (0x19 02) ===\n");

    // Inject a fault
    ecu.injectFault(0xC0300U, ecu::DTCSeverity::CHECK_IMMEDIATELY);  // CAN timeout fault
    ecu.injectFault(0x161400U, ecu::DTCSeverity::CHECK_AT_NEXT_HALT); // Engine sensor fault

    // Read DTC by status mask (0x08 = confirmed)
    uint8_t req[] = { 0x19U, 0x02U, 0xFFU };
    sendUDSRequest(bus, ecu::ECUCore::CAN_ID_DIAG_REQ, req, sizeof(req));
    runTicks(ecu, 5);

    std::printf("[Main] Active DTC count: %u\n",
                ecu.getDTCManager().countDTCsByStatusMask(ecu::DTCStatusBit::TEST_FAILED));
    std::printf("[Main] Confirmed DTC count: %u\n",
                ecu.getDTCManager().countDTCsByStatusMask(ecu::DTCStatusBit::CONFIRMED));
}

// ─── Scenario: Clear DTCs ──────────────────────────────────────────────────────

static void scenario_ClearDTCs(can::CANBus& bus, ecu::ECUCore& ecu) {
    std::printf("\n=== SCENARIO: Clear All DTCs (0x14 FF FF FF) ===\n");
    uint8_t req[] = { 0x14U, 0xFFU, 0xFFU, 0xFFU };
    sendUDSRequest(bus, ecu::ECUCore::CAN_ID_DIAG_REQ, req, sizeof(req));
    runTicks(ecu, 5);
    ecu.getDTCManager().clearAllDTCs();
    std::printf("[Main] DTC count after clear: %u\n",
                ecu.getDTCManager().getTotalDTCCount());
}

// ─── Scenario: ECU Reset ──────────────────────────────────────────────────────

static void scenario_ECUReset(can::CANBus& bus, ecu::ECUCore& ecu) {
    std::printf("\n=== SCENARIO: ECU Soft Reset (0x11 03) ===\n");
    uint8_t req[] = { 0x11U, 0x03U };
    sendUDSRequest(bus, ecu::ECUCore::CAN_ID_DIAG_REQ, req, sizeof(req));
    runTicks(ecu, 5);
}

// ─── Scenario: TesterPresent ──────────────────────────────────────────────────

static void scenario_TesterPresent(can::CANBus& bus, ecu::ECUCore& ecu) {
    std::printf("\n=== SCENARIO: TesterPresent (0x3E 00) – keep-alive ===\n");
    uint8_t req[] = { 0x3EU, 0x00U };
    sendUDSRequest(bus, ecu::ECUCore::CAN_ID_DIAG_FUNC, req, sizeof(req));
    runTicks(ecu, 5);
}

// ─── Scenario: Write DID ──────────────────────────────────────────────────────

static void scenario_WriteDID(can::CANBus& bus, ecu::ECUCore& ecu) {
    std::printf("\n=== SCENARIO: WriteDataByIdentifier – must be in Extended Session ===\n");
    // DID 0xF186 (ActiveDiagnosticSession) – try writing in extended session
    uint8_t req[] = { 0x2EU, 0xF1U, 0x86U, 0x03U };
    sendUDSRequest(bus, ecu::ECUCore::CAN_ID_DIAG_REQ, req, sizeof(req));
    runTicks(ecu, 5);
}

// ─── Main ────────────────────────────────────────────────────────────────────

int main() {
    std::printf("╔══════════════════════════════════════════════════════════╗\n");
    std::printf("║    Automotive ECU – CAN Bus + UDS Simulation              ║\n");
    std::printf("║    ISO 11898 | ISO 14229 | Embedded C++                   ║\n");
    std::printf("╚══════════════════════════════════════════════════════════╝\n\n");

    // ── 1. Create CAN Bus and ECU ─────────────────────────────────────────────
    can::CANBus  canBus("Powertrain_CAN", 500000U);
    ecu::ECUCore engine("EngineECU", canBus);

    // ── 2. Initialize ECU ─────────────────────────────────────────────────────
    if (!engine.initialize()) {
        std::printf("[Main] FATAL: ECU initialization failed\n");
        return EXIT_FAILURE;
    }

    // ── 3. Key ON – start engine running ─────────────────────────────────────
    std::printf("\n=== KEY ON ===\n");
    ecu::ECUSignals signals{};
    signals.ignitionOn    = true;
    signals.engineRunning = true;
    signals.engineRPM     = 850;
    signals.coolantTemp   = 25;
    signals.throttlePos   = 5;
    signals.engineLoad    = 10;
    signals.vehicleSpeed  = 0;
    signals.batteryVoltage= 1395;  // 13.95V
    engine.setSignals(signals);

    // Run 50ms to stabilize
    runTicks(engine, 50);
    std::printf("[Main] ECU state: %u (3=RUNNING)\n",
                static_cast<uint8_t>(engine.getState()));

    // ── 4. Run diagnostic scenarios ───────────────────────────────────────────
    scenario_ReadVIN(canBus, engine);
    scenario_EnterExtendedSession(canBus, engine);
    scenario_SecurityAccess(canBus, engine);
    scenario_WriteDID(canBus, engine);
    scenario_TesterPresent(canBus, engine);

    // Simulate vehicle running at speed
    std::printf("\n=== Simulating vehicle at 80 km/h ===\n");
    signals.vehicleSpeed  = 80U;
    signals.engineRPM     = 2400;
    signals.throttlePos   = 35U;
    signals.engineLoad    = 40U;
    signals.coolantTemp   = 90;
    engine.setSignals(signals);
    runTicks(engine, 200);

    // Fault injection
    scenario_DTCFaultAndRead(canBus, engine);

    // Clear DTCs
    scenario_ClearDTCs(canBus, engine);

    // ECU reset
    scenario_ECUReset(canBus, engine);

    // ── 5. Key OFF and shutdown ───────────────────────────────────────────────
    std::printf("\n=== KEY OFF ===\n");
    engine.keyOff();
    runTicks(engine, 50);

    // ── 6. Print final stats ──────────────────────────────────────────────────
    std::printf("\n=== Final Statistics ===\n");
    const auto& stats = canBus.getStats();
    std::printf("  CAN Tx frames   : %u\n", stats.txFrameCount);
    std::printf("  CAN Rx frames   : %u\n", stats.rxFrameCount);
    std::printf("  CAN Tx errors   : %u\n", stats.txErrorCount);
    std::printf("  UDS Requests    : %u\n", engine.getUDSServer().getRxRequestCount());
    std::printf("  UDS Responses   : %u\n", engine.getUDSServer().getTxResponseCount());
    std::printf("  UDS Neg Resp    : %u\n", engine.getUDSServer().getNRCCount());
    std::printf("  DTCs stored     : %u\n", engine.getDTCManager().getTotalDTCCount());

    engine.shutdown();

    std::printf("\n[Main] Simulation complete.\n");
    return EXIT_SUCCESS;
}
