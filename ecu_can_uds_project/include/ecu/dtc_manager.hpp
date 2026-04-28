#pragma once

#include <cstdint>
#include <cstring>

namespace automotive {
namespace ecu {

// ─── DTC Status Byte Bits (ISO 14229-1) ──────────────────────────────────────
namespace DTCStatusBit {
    constexpr uint8_t TEST_FAILED               = 0x01U;  ///< Bit 0
    constexpr uint8_t TEST_FAILED_THIS_CYCLE    = 0x02U;  ///< Bit 1
    constexpr uint8_t PENDING                   = 0x04U;  ///< Bit 2
    constexpr uint8_t CONFIRMED                 = 0x08U;  ///< Bit 3
    constexpr uint8_t NOT_COMPLETED_SINCE_CLEAR = 0x10U;  ///< Bit 4
    constexpr uint8_t FAILED_SINCE_CLEAR        = 0x20U;  ///< Bit 5
    constexpr uint8_t NOT_COMPLETED_THIS_CYCLE  = 0x40U;  ///< Bit 6
    constexpr uint8_t WARNING_INDICATOR         = 0x80U;  ///< Bit 7 (MIL)
}

/// DTC severity (for reporting)
enum class DTCSeverity : uint8_t {
    NO_SEVERITY         = 0x00U,
    MAINTENANCE_ONLY    = 0x20U,
    CHECK_AT_NEXT_HALT  = 0x40U,
    CHECK_IMMEDIATELY   = 0x80U,
};

/// Snapshot (freeze frame) data captured when a DTC is first set
struct DTCSnapshot {
    uint32_t timestamp{0U};       ///< Milliseconds since ECU start
    uint16_t vehicleSpeed{0U};    ///< km/h × 100
    int16_t  engineRPM{0};        ///< RPM
    int8_t   coolantTemp{0};      ///< °C
    uint8_t  throttlePos{0U};     ///< % (0-100)
    uint8_t  engineLoad{0U};      ///< % (0-100)
    uint8_t  valid{0U};
};

/// A single DTC record
struct DTCRecord {
    uint32_t    code{0U};          ///< 3-byte DTC code packed as uint32
    uint8_t     statusByte{0U};    ///< Status mask per ISO 14229
    DTCSeverity severity{DTCSeverity::NO_SEVERITY};
    DTCSnapshot snapshot{};
    uint16_t    occurrenceCounter{0U};
    bool        active{false};     ///< Slot in use
};

/**
 * @brief Manages Diagnostic Trouble Codes (DTCs) for an ECU.
 *
 * Provides:
 *  - DTC set / clear / query API
 *  - Status byte management (confirmed, pending, warning indicator)
 *  - Freeze frame (snapshot) capture
 *  - Serialization for UDS 0x19 ReadDTCInformation responses
 */
class DTCManager {
public:
    static constexpr uint8_t MAX_DTC_RECORDS = 50U;

    DTCManager();
    ~DTCManager() = default;

    // Non-copyable (global manager)
    DTCManager(const DTCManager&) = delete;
    DTCManager& operator=(const DTCManager&) = delete;

    /**
     * @brief Set/update a DTC
     * @param code       3-byte DTC code (e.g. 0xU0100 = CAN timeout)
     * @param severity   Severity classification
     * @param snapshot   Optional freeze frame data
     */
    void setDTC(uint32_t code,
                DTCSeverity severity = DTCSeverity::CHECK_AT_NEXT_HALT,
                const DTCSnapshot* snapshot = nullptr);

    /**
     * @brief Mark a DTC as no longer failing (clears TEST_FAILED bit).
     *        Confirmed bit remains until explicitly cleared.
     */
    void clearDTCFailed(uint32_t code);

    /**
     * @brief Clear all DTCs and reset status bytes (UDS 0x14)
     */
    void clearAllDTCs();

    /**
     * @brief Query DTC status byte
     * @return Status byte, or 0 if DTC not found
     */
    uint8_t getDTCStatus(uint32_t code) const;

    /**
     * @brief Check if a DTC is currently active (TEST_FAILED bit set)
     */
    bool isDTCActive(uint32_t code) const;

    /**
     * @brief Check if a DTC is confirmed
     */
    bool isDTCConfirmed(uint32_t code) const;

    /**
     * @brief Get all DTCs matching a status mask
     * @param statusMask   Bitmask to filter by (e.g. 0x08 = confirmed only)
     * @param outCodes     Output buffer for matching DTC codes
     * @param outStatus    Output buffer for status bytes
     * @param maxRecords   Size of output buffers
     * @return Number of matching DTCs
     */
    uint8_t getDTCsByStatusMask(uint8_t statusMask,
                                 uint32_t* outCodes,
                                 uint8_t*  outStatus,
                                 uint8_t   maxRecords) const;

    /**
     * @brief Get count of DTCs matching a status mask
     */
    uint8_t countDTCsByStatusMask(uint8_t statusMask) const;

    /**
     * @brief Get freeze frame for a specific DTC
     * @return true if DTC found and snapshot populated
     */
    bool getDTCSnapshot(uint32_t code, DTCSnapshot& outSnapshot) const;

    /**
     * @brief End-of-drive-cycle processing:
     *        - Promotes pending DTCs to confirmed if failed in 2+ cycles
     *        - Updates "not completed" bits
     * @param cycleCompleted true = monitoring cycle completed without failure
     */
    void processDriveCycle(bool cycleCompleted);

    uint8_t getTotalDTCCount() const noexcept { return m_dtcCount; }

private:
    DTCRecord* findDTC(uint32_t code);
    const DTCRecord* findDTC(uint32_t code) const;
    DTCRecord* findOrCreateSlot(uint32_t code);

    DTCRecord m_records[MAX_DTC_RECORDS]{};
    uint8_t   m_dtcCount{0U};
    uint8_t   m_failCountThisCycle[MAX_DTC_RECORDS]{};
};

} // namespace ecu
} // namespace automotive
