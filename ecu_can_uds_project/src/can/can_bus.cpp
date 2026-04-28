#include "../../include/can/can_bus.hpp"
#include <cstdio>
#include <cstring>

namespace automotive {
namespace can {

CANBus::CANBus(const std::string& channelName, uint32_t baudRateBps)
    : m_channelName(channelName)
    , m_baudRate(baudRateBps)
    , m_initialized(false)
    , m_busState(BusState::UNINITIALIZED)
    , m_rxHead(0U)
    , m_rxTail(0U)
    , m_txErrorCounter(0U)
    , m_rxErrorCounter(0U)
{
}

CANBus::~CANBus() {
    shutdown();
}

bool CANBus::initialize() {
    if (m_initialized) {
        return true;
    }
    // In production: initialize MCAL CAN driver here
    // For simulation: just mark ready
    m_busState   = BusState::ACTIVE;
    m_initialized = true;
    m_stats.reset();
    std::memset(m_callbacks.data(), 0, sizeof(m_callbacks));
    std::printf("[CANBus] Channel '%s' initialized @ %u bps\n",
                m_channelName.c_str(), m_baudRate);
    return true;
}

void CANBus::shutdown() {
    if (!m_initialized) return;
    m_initialized = false;
    m_busState    = BusState::UNINITIALIZED;
    std::printf("[CANBus] Channel '%s' shutdown\n", m_channelName.c_str());
}

bool CANBus::transmit(const CANFrame& frame) {
    if (!m_initialized || m_busState == BusState::BUS_OFF) {
        m_stats.txErrorCount++;
        return false;
    }
    if (!frame.isValid()) {
        m_stats.txErrorCount++;
        return false;
    }
    // In production: call CAN_Write() MCAL
    // For simulation: log the frame
    m_stats.txFrameCount++;
    std::printf("[CANBus][TX] ID=0x%03X DLC=%u Data=",
                frame.getId(), frame.getDLC());
    for (uint8_t i = 0; i < frame.getDLC(); ++i) {
        std::printf("%02X ", frame.getData()[i]);
    }
    std::printf("\n");
    return true;
}

bool CANBus::transmit(uint32_t id, const uint8_t* data, uint8_t dlc, IDType idType) {
    CANFrame frame(id, dlc, data, idType);
    return transmit(frame);
}

int8_t CANBus::registerRxCallback(RxCallback callback,
                                    uint32_t idFilter,
                                    uint32_t idMask) {
    for (uint8_t i = 0U; i < MAX_RX_CALLBACKS; ++i) {
        if (!m_callbacks[i].active) {
            m_callbacks[i].callback = callback;
            m_callbacks[i].idFilter = idFilter;
            m_callbacks[i].idMask   = idMask;
            m_callbacks[i].active   = true;
            return static_cast<int8_t>(i);
        }
    }
    return -1;  // No free slot
}

void CANBus::unregisterRxCallback(int8_t handle) {
    if (handle >= 0 && handle < static_cast<int8_t>(MAX_RX_CALLBACKS)) {
        m_callbacks[static_cast<uint8_t>(handle)].active = false;
    }
}

void CANBus::injectFrame(const CANFrame& frame) {
    // Insert into ring buffer
    uint8_t nextHead = (m_rxHead + 1U) % RX_QUEUE_SIZE;
    if (nextHead != m_rxTail) {
        m_rxQueue[m_rxHead] = frame;
        m_rxHead = nextHead;
    }
    // Immediate statistics update
    m_stats.rxFrameCount++;
}

void CANBus::processRxQueue() {
    while (m_rxTail != m_rxHead) {
        const CANFrame& frame = m_rxQueue[m_rxTail];
        m_rxTail = (m_rxTail + 1U) % RX_QUEUE_SIZE;

        // Dispatch to matching callbacks
        for (auto& entry : m_callbacks) {
            if (!entry.active) continue;

            bool match = true;
            if (entry.idMask != 0U) {
                match = (frame.getId() & entry.idMask) ==
                        (entry.idFilter & entry.idMask);
            } else if (entry.idFilter != 0U) {
                match = (frame.getId() == entry.idFilter);
            }
            // idFilter=0 && idMask=0 → receive all

            if (match && entry.callback) {
                entry.callback(frame);
            }
        }
    }
}

void CANBus::injectBusError(uint8_t errorType) {
    switch (errorType) {
        case 0: m_stats.stuffErrorCount++; m_txErrorCounter += 8U; break;
        case 1: m_stats.crcErrorCount++;   m_rxErrorCounter += 8U; break;
        case 2: m_stats.formErrorCount++;  m_rxErrorCounter += 8U; break;
        default: break;
    }
    updateBusState();
}

void CANBus::updateBusState() {
    if (m_txErrorCounter > 255U || m_rxErrorCounter > 255U) {
        m_busState = BusState::BUS_OFF;
        m_stats.busOffCount++;
    } else if (m_txErrorCounter > 127U || m_rxErrorCounter > 127U) {
        m_busState = BusState::PASSIVE;
    } else if (m_txErrorCounter > 96U || m_rxErrorCounter > 96U) {
        m_busState = BusState::WARNING;
    } else {
        m_busState = BusState::ACTIVE;
    }
}

} // namespace can
} // namespace automotive
