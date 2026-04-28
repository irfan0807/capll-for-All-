#include "../../include/can/can_frame.hpp"
#include <cstring>
#include <algorithm>

namespace automotive {
namespace can {

CANFrame::CANFrame()
    : m_id(0U), m_dlc(0U), m_idType(IDType::STANDARD),
      m_frameType(FrameType::DATA), m_timestamp(0U)
{
    std::memset(m_data, 0, sizeof(m_data));
}

CANFrame::CANFrame(uint32_t id,
                   uint8_t  dlc,
                   const uint8_t* data,
                   IDType    idType,
                   FrameType frameType)
    : m_id(id), m_idType(idType), m_frameType(frameType), m_timestamp(0U)
{
    std::memset(m_data, 0, sizeof(m_data));
    m_dlc = std::min(dlc, CAN_FD_MAX_DLC);
    if (data != nullptr && m_dlc > 0U) {
        std::memcpy(m_data, data, m_dlc);
    }
}

uint8_t CANFrame::getByte(uint8_t index) const noexcept {
    if (index >= m_dlc) {
        return 0x00U;
    }
    return m_data[index];
}

bool CANFrame::setData(const uint8_t* data, uint8_t dlc) {
    if (dlc > CAN_FD_MAX_DLC) {
        return false;
    }
    m_dlc = dlc;
    if (data != nullptr) {
        std::memcpy(m_data, data, dlc);
    } else {
        std::memset(m_data, 0, dlc);
    }
    return true;
}

bool CANFrame::matchesID(uint32_t id, uint32_t mask) const noexcept {
    return (m_id & mask) == (id & mask);
}

void CANFrame::reset() noexcept {
    m_id        = 0U;
    m_dlc       = 0U;
    m_idType    = IDType::STANDARD;
    m_frameType = FrameType::DATA;
    m_timestamp = 0U;
    std::memset(m_data, 0, sizeof(m_data));
}

} // namespace can
} // namespace automotive
