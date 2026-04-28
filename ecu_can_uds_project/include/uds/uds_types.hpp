#pragma once

#include <cstdint>
#include <array>
#include <functional>

namespace automotive {
namespace uds {

// ─── Session Types ────────────────────────────────────────────────────────────
enum class DiagSession : uint8_t {
    DEFAULT             = 0x01U,
    PROGRAMMING         = 0x02U,
    EXTENDED_DIAGNOSTIC = 0x03U,
    SAFETY_SYSTEM       = 0x04U,
};

// ─── UDS Service IDs ─────────────────────────────────────────────────────────
enum class ServiceID : uint8_t {
    DIAGNOSTIC_SESSION_CONTROL      = 0x10U,
    ECU_RESET                       = 0x11U,
    CLEAR_DIAGNOSTIC_INFORMATION    = 0x14U,
    READ_DTC_INFORMATION            = 0x19U,
    READ_DATA_BY_IDENTIFIER         = 0x22U,
    READ_MEMORY_BY_ADDRESS          = 0x23U,
    SECURITY_ACCESS                 = 0x27U,
    COMMUNICATION_CONTROL           = 0x28U,
    WRITE_DATA_BY_IDENTIFIER        = 0x2EU,
    ROUTINE_CONTROL                 = 0x31U,
    REQUEST_DOWNLOAD                = 0x34U,
    REQUEST_UPLOAD                  = 0x35U,
    TRANSFER_DATA                   = 0x36U,
    REQUEST_TRANSFER_EXIT           = 0x37U,
    TESTER_PRESENT                  = 0x3EU,
    CONTROL_DTC_SETTING             = 0x85U,
};

// ─── Negative Response Codes ──────────────────────────────────────────────────
enum class NRC : uint8_t {
    GENERAL_REJECT                           = 0x10U,
    SERVICE_NOT_SUPPORTED                    = 0x11U,
    SUB_FUNCTION_NOT_SUPPORTED               = 0x12U,
    INCORRECT_MESSAGE_LENGTH_OR_FORMAT       = 0x13U,
    RESPONSE_TOO_LONG                        = 0x14U,
    BUSY_REPEAT_REQUEST                      = 0x21U,
    CONDITIONS_NOT_CORRECT                   = 0x22U,
    REQUEST_SEQUENCE_ERROR                   = 0x24U,
    REQUEST_OUT_OF_RANGE                     = 0x31U,
    SECURITY_ACCESS_DENIED                   = 0x33U,
    INVALID_KEY                              = 0x35U,
    EXCEEDED_NUMBER_OF_ATTEMPTS              = 0x36U,
    REQUIRED_TIME_DELAY_NOT_EXPIRED          = 0x37U,
    UPLOAD_DOWNLOAD_NOT_ACCEPTED             = 0x70U,
    TRANSFER_DATA_SUSPENDED                  = 0x71U,
    GENERAL_PROGRAMMING_FAILURE              = 0x72U,
    WRONG_BLOCK_SEQUENCE_COUNTER             = 0x73U,
    REQUEST_CORRECTLY_RECEIVED_RESPONSE_PENDING = 0x78U,
    SUB_FUNCTION_NOT_SUPPORTED_IN_SESSION    = 0x7EU,
    SERVICE_NOT_SUPPORTED_IN_SESSION         = 0x7FU,
};

// ─── UDS PDU ─────────────────────────────────────────────────────────────────
constexpr uint16_t UDS_MAX_PDU_SIZE = 4096U;

struct UDSRequest {
    uint8_t  data[UDS_MAX_PDU_SIZE];
    uint16_t length{0U};
    uint32_t sourceAddr{0U};       ///< Tester physical address
    bool     isFunctional{false};  ///< Functional (broadcast) vs physical

    uint8_t  serviceId() const { return (length > 0) ? data[0] : 0x00U; }
    uint8_t  subFunction() const { return (length > 1) ? (data[1] & 0x7FU) : 0x00U; }
    bool     suppressPositiveResponse() const {
        return (length > 1) && ((data[1] & 0x80U) != 0U);
    }
};

struct UDSResponse {
    uint8_t  data[UDS_MAX_PDU_SIZE];
    uint16_t length{0U};
    bool     isNegative{false};

    void setNegativeResponse(uint8_t serviceId, NRC nrc) {
        data[0] = 0x7FU;
        data[1] = serviceId;
        data[2] = static_cast<uint8_t>(nrc);
        length = 3U;
        isNegative = true;
    }

    void setPositiveResponse(uint8_t serviceId, const uint8_t* payload, uint16_t payloadLen) {
        data[0] = serviceId | 0x40U;
        if (payload != nullptr && payloadLen > 0U) {
            for (uint16_t i = 0; i < payloadLen && (i + 1U) < UDS_MAX_PDU_SIZE; i++) {
                data[i + 1U] = payload[i];
            }
        }
        length = payloadLen + 1U;
        isNegative = false;
    }
};

// ─── Service Handler Callback ─────────────────────────────────────────────────
using ServiceHandler = std::function<void(const UDSRequest&, UDSResponse&)>;

// ─── Data Identifier (DID) Entry ─────────────────────────────────────────────
struct DIDEntry {
    uint16_t did;
    bool     readable;
    bool     writable;
    DiagSession minReadSession;
    DiagSession minWriteSession;
    uint8_t     data[64];
    uint8_t     dataLen;
};

// ─── Security Level ───────────────────────────────────────────────────────────
struct SecurityLevel {
    uint8_t  level;      ///< Access level (1, 3, 5 … odd = request seed)
    bool     unlocked;
    uint32_t seed;
    uint32_t failAttempts;
    uint32_t lockoutTimerStart;
};

} // namespace uds
} // namespace automotive
