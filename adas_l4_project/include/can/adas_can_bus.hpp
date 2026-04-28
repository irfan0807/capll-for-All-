#pragma once
// ============================================================================
// adas_can_bus.hpp  –  CAN bus adapter for ADAS ECU (Tx / Rx)
// ============================================================================
#include "adas_can_signals.hpp"
#include "../perception/perception_types.hpp"
#include "../safety/safety_monitor.hpp"
#include "../control/vehicle_controller.hpp"
#include <cstdint>

namespace adas {
namespace can_bus {

// ---------------------------------------------------------------------------
// CAN frame (8-byte payload, no FD for simplicity)
// ---------------------------------------------------------------------------
struct CanFrame {
    uint32_t id;
    uint8_t  dlc;
    uint8_t  data[8];

    CanFrame() : id(0), dlc(0) {
        for (uint8_t i = 0; i < 8; i++) data[i] = 0;
    }
};

// ---------------------------------------------------------------------------
// Tx callback type (set by platform / HAL)
// ---------------------------------------------------------------------------
using CanTxFn = void(*)(const CanFrame&);

class AdasCanBus {
public:
    AdasCanBus();

    /// Register hardware transmit function
    void setTxCallback(CanTxFn fn) { m_txFn = fn; }

    /// Inject a received CAN frame (from HAL Rx interrupt or test)
    void injectRx(const CanFrame& frame);

    /// Transmit ADAS outputs every 100ms
    void transmitAll(
        const perception::ObjectList&      objects,
        const perception::LaneEstimate&    lane,
        const control::ActuatorCommands&   cmds,
        const safety::FaultFlags&          faults,
        safety::AdasSystemState            state,
        float ego_speed_mps,
        float ego_yaw_rad,
        float min_ttc_s,
        bool  aeb_active,
        bool  odd_valid);

    /// Last received raw frame (for testing)
    const CanFrame& getLastRx() const { return m_lastRx; }
    uint32_t getTxCount() const { return m_txCount; }
    uint32_t getRxCount() const { return m_rxCount; }

private:
    void txObjectList  (const perception::TrackedObject& obj);
    void txLaneInfo    (const perception::LaneEstimate& lane);
    void txVehicleCmd  (const control::ActuatorCommands& cmds);
    void txSafetyStatus(const safety::FaultFlags& faults,
                        safety::AdasSystemState state,
                        float min_ttc_s, bool aeb_active, bool odd_valid);
    void txEgoState    (float speed_mps, float yaw_rad);

    void sendFrame(const CanFrame& frame);

    CanTxFn   m_txFn;
    CanFrame  m_lastRx;
    uint32_t  m_txCount;
    uint32_t  m_rxCount;
};

} // namespace can_bus
} // namespace adas
