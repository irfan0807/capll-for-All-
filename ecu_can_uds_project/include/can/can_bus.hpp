#pragma once

#include "can_frame.hpp"
#include <cstdint>
#include <functional>
#include <array>
#include <string>

namespace automotive {
namespace can {

/// Maximum number of registered receive callbacks
constexpr uint8_t MAX_RX_CALLBACKS = 16U;

/// CAN bus operating state
enum class BusState : uint8_t {
    ACTIVE      = 0U,  ///< Normal operation (error-active)
    WARNING     = 1U,  ///< Error counter > 96
    PASSIVE     = 2U,  ///< Error-passive (error counter > 127)
    BUS_OFF     = 3U,  ///< Bus-off state (error counter > 255)
    UNINITIALIZED = 4U
};

/// CAN bus statistics
struct CANBusStats {
    uint32_t txFrameCount{0U};
    uint32_t rxFrameCount{0U};
    uint32_t txErrorCount{0U};
    uint32_t rxErrorCount{0U};
    uint32_t busOffCount{0U};
    uint32_t stuffErrorCount{0U};
    uint32_t crcErrorCount{0U};
    uint32_t formErrorCount{0U};

    void reset() { *this = CANBusStats{}; }
};

/// RX callback signature: called when a frame matching filter arrives
using RxCallback = std::function<void(const CANFrame&)>;

/**
 * @brief Simulates a CAN bus node with Tx/Rx, filtering, and statistics.
 *
 * In production this wraps the MCAL CAN driver. In simulation/test it 
 * connects to a virtual bus (shared frame queue between instances).
 */
class CANBus {
public:
    explicit CANBus(const std::string& channelName, uint32_t baudRateBps = 500000U);
    ~CANBus();

    // Non-copyable
    CANBus(const CANBus&) = delete;
    CANBus& operator=(const CANBus&) = delete;

    // --- Lifecycle ---
    bool initialize();
    void shutdown();
    bool isInitialized() const noexcept { return m_initialized; }

    // --- Transmit ---
    /**
     * @brief Transmit a CAN frame
     * @param frame Frame to transmit
     * @return true on success, false if bus is off or Tx queue full
     */
    bool transmit(const CANFrame& frame);

    /**
     * @brief Convenience: transmit raw bytes
     */
    bool transmit(uint32_t id, const uint8_t* data, uint8_t dlc,
                  IDType idType = IDType::STANDARD);

    // --- Receive ---
    /**
     * @brief Register a callback invoked on frame receipt (optional ID filter)
     * @param callback  Function to call
     * @param idFilter  Only call back for this ID (0 = all frames)
     * @param idMask    Mask applied to filter (0xFFFFFFFF = exact match)
     * @return handle index (use to unregister), -1 on failure
     */
    int8_t registerRxCallback(RxCallback callback,
                               uint32_t idFilter = 0U,
                               uint32_t idMask   = 0U);

    void unregisterRxCallback(int8_t handle);

    /**
     * @brief Poll: call registered callbacks for any frames in Rx queue.
     *        Call this from a periodic task (e.g. every 1ms).
     */
    void processRxQueue();

    /**
     * @brief Simulate receiving a frame (for testing / simulation)
     */
    void injectFrame(const CANFrame& frame);

    // --- State & Stats ---
    BusState        getBusState()  const noexcept { return m_busState; }
    const CANBusStats& getStats()  const noexcept { return m_stats; }
    const std::string& getChannel()const noexcept { return m_channelName; }
    uint32_t        getBaudRate()  const noexcept { return m_baudRate; }

    /// Simulate error injection for testing
    void injectBusError(uint8_t errorType);

private:
    static constexpr uint8_t  RX_QUEUE_SIZE = 64U;

    std::string  m_channelName;
    uint32_t     m_baudRate;
    bool         m_initialized{false};
    BusState     m_busState{BusState::UNINITIALIZED};
    CANBusStats  m_stats{};

    // Simple ring buffer for injected/received frames
    CANFrame     m_rxQueue[RX_QUEUE_SIZE];
    uint8_t      m_rxHead{0U};
    uint8_t      m_rxTail{0U};

    struct CallbackEntry {
        RxCallback callback;
        uint32_t   idFilter{0U};
        uint32_t   idMask{0U};
        bool       active{false};
    };
    std::array<CallbackEntry, MAX_RX_CALLBACKS> m_callbacks{};

    void updateBusState();
    uint16_t m_txErrorCounter{0U};
    uint16_t m_rxErrorCounter{0U};
};

} // namespace can
} // namespace automotive
