#pragma once
#include <cstdint>
#include <vector>

// ─────────────────────────────────────────────────────────────
//  UDS (ISO 14229) Service IDs
// ─────────────────────────────────────────────────────────────
enum class UdsSid : uint8_t {
    DIAGNOSTIC_SESSION_CONTROL = 0x10,
    ECU_RESET                  = 0x11,
    SECURITY_ACCESS            = 0x27,
    COMMUNICATION_CONTROL      = 0x28,
    TESTER_PRESENT             = 0x3E,
    READ_DATA_BY_ID            = 0x22,
    WRITE_DATA_BY_ID           = 0x2E,
    CLEAR_DIAGNOSTIC_INFO      = 0x14,
    READ_DTC_INFO              = 0x19,
};

// ─────────────────────────────────────────────────────────────
//  UDS Response
// ─────────────────────────────────────────────────────────────
struct UdsResponse {
    bool                     positive{ false };
    std::vector<uint8_t>     data{};
    uint8_t                  nrc{ 0x00 };  // negative response code
};

// ─────────────────────────────────────────────────────────────
//  UdsHandler
// ─────────────────────────────────────────────────────────────
class UdsHandler {
public:
    UdsHandler();
    UdsResponse ProcessRequest(const std::vector<uint8_t>& request);

private:
    UdsResponse HandleDiagnosticSession(const std::vector<uint8_t>& req);
    UdsResponse HandleEcuReset(const std::vector<uint8_t>& req);
    UdsResponse HandleTesterPresent(const std::vector<uint8_t>& req);
    UdsResponse HandleSecurityAccess(const std::vector<uint8_t>& req);
    UdsResponse HandleReadDataById(const std::vector<uint8_t>& req);
    UdsResponse HandleWriteDataById(const std::vector<uint8_t>& req);

    uint8_t active_session_{ 0x01 };   // default session
    bool    security_unlocked_{ false };
};
