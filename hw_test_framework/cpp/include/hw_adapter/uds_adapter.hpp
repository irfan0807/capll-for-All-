#pragma once
/**
 * uds_adapter.hpp
 * UDS (ISO 14229) adapter layered on top of CanAdapter.
 * Handles ISO 15765-2 transport layer (segmentation/flow control),
 * session management, and service encoding/decoding.
 */

#include "can_adapter.hpp"
#include <cstdint>
#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace hw_adapter {

// ─── UDS Service IDs ─────────────────────────────────────────────────────────

enum class UdsService : uint8_t {
    DiagnosticSessionControl     = 0x10,
    ECUReset                     = 0x11,
    ClearDiagnosticInfo          = 0x14,
    ReadDTCInformation           = 0x19,
    ReadDataByIdentifier         = 0x22,
    ReadMemoryByAddress          = 0x23,
    WriteDataByIdentifier        = 0x2E,
    InputOutputControlByID       = 0x2F,
    RoutineControl               = 0x31,
    RequestDownload              = 0x34,
    TransferData                 = 0x36,
    RequestTransferExit          = 0x37,
    SecurityAccess               = 0x27,
    CommunicationControl         = 0x28,
};

// ─── UDS Session types ────────────────────────────────────────────────────────

enum class UdsSession : uint8_t {
    Default          = 0x01,
    Programming      = 0x02,
    Extended         = 0x03,
};

// ─── UDS NRC (Negative Response Codes) ───────────────────────────────────────

enum class UdsNrc : uint8_t {
    ServiceNotSupported          = 0x11,
    SubFunctionNotSupported      = 0x12,
    IncorrectMessageLength       = 0x13,
    ConditionsNotCorrect         = 0x22,
    RequestSequenceError         = 0x24,
    RequestOutOfRange            = 0x31,
    SecurityAccessDenied         = 0x33,
    InvalidKey                   = 0x35,
    ExceedNumberOfAttempts       = 0x36,
    ResponsePending              = 0x78,
    ServiceNotSupportedInSession = 0x7F,
};

inline const char* nrcToString(UdsNrc nrc) {
    switch (nrc) {
        case UdsNrc::ServiceNotSupported:          return "ServiceNotSupported";
        case UdsNrc::SubFunctionNotSupported:      return "SubFunctionNotSupported";
        case UdsNrc::IncorrectMessageLength:       return "IncorrectMessageLength";
        case UdsNrc::ConditionsNotCorrect:         return "ConditionsNotCorrect";
        case UdsNrc::RequestSequenceError:         return "RequestSequenceError";
        case UdsNrc::RequestOutOfRange:            return "RequestOutOfRange";
        case UdsNrc::SecurityAccessDenied:         return "SecurityAccessDenied";
        case UdsNrc::InvalidKey:                   return "InvalidKey";
        case UdsNrc::ResponsePending:              return "ResponsePending";
        case UdsNrc::ServiceNotSupportedInSession: return "ServiceNotSupportedInSession";
        default:                                    return "UnknownNRC";
    }
}

// ─── UDS Response ─────────────────────────────────────────────────────────────

struct UdsResponse {
    bool        positive    = false;
    uint8_t     service_id  = 0;
    UdsNrc      nrc         = UdsNrc::ServiceNotSupported;  // only valid if !positive
    Buffer      payload;    ///< Response payload (excluding service byte)
    int64_t     elapsed_us  = 0;  ///< Round-trip time in microseconds

    bool ok() const noexcept { return positive; }

    /// Extract a uint16_t DID value from the payload at given offset.
    uint16_t u16At(size_t offset) const {
        if (offset + 1 >= payload.size())
            throw std::out_of_range("u16At: offset out of range");
        return static_cast<uint16_t>((payload[offset] << 8) | payload[offset + 1]);
    }

    /// Extract a uint8_t value from payload at given offset.
    uint8_t u8At(size_t offset) const {
        if (offset >= payload.size())
            throw std::out_of_range("u8At: offset out of range");
        return payload[offset];
    }
};

// ─── DTC Record ───────────────────────────────────────────────────────────────

struct DtcRecord {
    uint32_t dtc_number    = 0;   ///< 3-byte DTC code
    uint8_t  status_byte   = 0;   ///< ISO 14229 DTC status mask
    bool     confirmed()   const noexcept { return (status_byte & 0x08) != 0; }
    bool     pending()     const noexcept { return (status_byte & 0x01) != 0; }
    bool     testFailed()  const noexcept { return (status_byte & 0x04) != 0; }
    std::string hex()      const;
};

// ─── Transport Layer Config ───────────────────────────────────────────────────

struct IsoTpConfig {
    DWord  tx_id           = 0x7E0;  ///< Tester request ID
    DWord  rx_id           = 0x7E8;  ///< ECU response ID
    bool   extended_ids    = false;
    uint8_t  block_size    = 0;      ///< 0 = no flow control limitation
    uint8_t  st_min_ms     = 0;      ///< Minimum separation time
    int    timeout_ms      = 1000;   ///< P2 timeout (default response)
    int    timeout_ext_ms  = 5000;   ///< P2* extended timeout (0x78 pending)
};

// ─── UdsAdapter ───────────────────────────────────────────────────────────────

class UdsAdapter : public BaseAdapter {
public:
    explicit UdsAdapter(std::shared_ptr<CanAdapter> can);
    ~UdsAdapter() override;

    // ─── BaseAdapter ──────────────────────────────────────────────────────────
    AdapterStatus open(const std::string& device_uri) override;
    AdapterStatus close() override;
    bool          isOpen()  const noexcept override;
    std::string   name()    const noexcept override { return "UDS"; }
    std::string   version() const noexcept override;
    Stats         stats()   const noexcept override;
    void          resetStats() noexcept override;

    // ─── Configuration ────────────────────────────────────────────────────────
    void configure(const IsoTpConfig& cfg);
    IsoTpConfig config() const noexcept;

    // ─── Session management ───────────────────────────────────────────────────

    /// Open a diagnostic session (0x10).
    UdsResponse openSession(UdsSession session = UdsSession::Extended);

    /// Send tester-present to keep session alive.
    UdsResponse testerPresent(bool suppress_response = true);

    /// Request ECU reset (0x11). type: 0x01=hard, 0x02=key-off, 0x03=soft.
    UdsResponse ecuReset(uint8_t reset_type = 0x01);

    // ─── Security access ──────────────────────────────────────────────────────

    /// Perform seed-key exchange for a given security level.
    /// seed_to_key: user-supplied lambda that computes the key from the seed.
    UdsResponse securityAccess(uint8_t level,
                               std::function<Buffer(const Buffer&)> seed_to_key);

    // ─── Data services ────────────────────────────────────────────────────────

    /// Read a DID (0x22).
    UdsResponse readDataByIdentifier(uint16_t did);

    /// Write a DID (0x2E).
    UdsResponse writeDataByIdentifier(uint16_t did, const Buffer& data);

    /// Read memory by address (0x23).
    UdsResponse readMemoryByAddress(uint32_t address, uint8_t length);

    /// Force ECU I/O (0x2F).
    UdsResponse inputOutputControl(uint16_t did, uint8_t control_param, const Buffer& data = {});

    // ─── DTC services ─────────────────────────────────────────────────────────

    /// Read all DTCs matching status mask (0x19 02).
    std::vector<DtcRecord> readDTCs(uint8_t status_mask = 0x0F);

    /// Read DTCs with snapshot (freeze frame) data (0x19 04).
    UdsResponse readDTCSnapshot(uint32_t dtc_number, uint8_t record_number = 0x01);

    /// Clear all DTCs (0x14 FF FF FF).
    UdsResponse clearDTCs(uint32_t group = 0xFFFFFF);

    // ─── Routine control ──────────────────────────────────────────────────────

    /// Start a routine (0x31 01).
    UdsResponse startRoutine(uint16_t routine_id, const Buffer& params = {});

    /// Stop a routine (0x31 02).
    UdsResponse stopRoutine(uint16_t routine_id);

    /// Request routine result (0x31 03).
    UdsResponse requestRoutineResults(uint16_t routine_id);

    // ─── Raw send ─────────────────────────────────────────────────────────────

    /// Send a raw UDS request and return the response.
    UdsResponse send(const Buffer& request);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace hw_adapter
