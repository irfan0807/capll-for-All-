#pragma once

#include <cstdint>
#include <cstring>

namespace automotive {
namespace can {

/// Maximum CAN 2.0 payload size in bytes
constexpr uint8_t CAN_MAX_DLC = 8U;

/// Maximum CAN FD payload size in bytes  
constexpr uint8_t CAN_FD_MAX_DLC = 64U;

/// CAN frame type
enum class FrameType : uint8_t {
    DATA   = 0U,   ///< Standard data frame
    REMOTE = 1U,   ///< Remote Transmission Request frame
    ERROR  = 2U,   ///< Error frame
    FD     = 3U,   ///< CAN FD frame
};

/// CAN identifier type
enum class IDType : uint8_t {
    STANDARD = 0U,   ///< 11-bit identifier
    EXTENDED = 1U,   ///< 29-bit identifier
};

/**
 * @brief Represents a single CAN bus frame.
 *
 * Stores the CAN identifier, data length code (DLC), payload, and metadata.
 * Supports both standard (11-bit) and extended (29-bit) identifiers.
 */
class CANFrame {
public:
    /// Default constructor – creates an empty data frame
    CANFrame();

    /**
     * @brief Construct a CAN frame with full parameters
     * @param id        CAN arbitration ID
     * @param dlc       Data length (0–8 for CAN 2.0)
     * @param data      Pointer to data bytes
     * @param idType    Standard (11-bit) or Extended (29-bit)
     * @param frameType DATA, REMOTE, ERROR or FD
     */
    CANFrame(uint32_t id,
             uint8_t  dlc,
             const uint8_t* data,
             IDType    idType    = IDType::STANDARD,
             FrameType frameType = FrameType::DATA);

    // --- Accessors ---
    uint32_t  getId()       const noexcept { return m_id; }
    uint8_t   getDLC()      const noexcept { return m_dlc; }
    IDType    getIDType()   const noexcept { return m_idType; }
    FrameType getFrameType()const noexcept { return m_frameType; }
    uint32_t  getTimestamp()const noexcept { return m_timestamp; }

    const uint8_t* getData() const noexcept { return m_data; }
    uint8_t*       getData()       noexcept { return m_data; }

    uint8_t getByte(uint8_t index) const noexcept;

    // --- Mutators ---
    bool setData(const uint8_t* data, uint8_t dlc);
    void setTimestamp(uint32_t ts) noexcept { m_timestamp = ts; }

    /// Check if the frame ID matches a given ID (masked)
    bool matchesID(uint32_t id, uint32_t mask = 0xFFFFFFFFU) const noexcept;

    /// True if this frame carries actual data (not RTR or error)
    bool isDataFrame() const noexcept {
        return m_frameType == FrameType::DATA || m_frameType == FrameType::FD;
    }

    /// Returns true if DLC is valid (0..8 for CAN 2.0)
    bool isValid() const noexcept { return m_dlc <= CAN_MAX_DLC; }

    /// Clear/reset the frame
    void reset() noexcept;

private:
    uint32_t  m_id{0U};
    uint8_t   m_dlc{0U};
    uint8_t   m_data[CAN_FD_MAX_DLC]{};
    IDType    m_idType{IDType::STANDARD};
    FrameType m_frameType{FrameType::DATA};
    uint32_t  m_timestamp{0U};   ///< Receive timestamp in ms
};

} // namespace can
} // namespace automotive
