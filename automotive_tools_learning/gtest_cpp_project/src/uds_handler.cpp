#include "uds_handler.h"

UdsHandler::UdsHandler() = default;

UdsResponse UdsHandler::ProcessRequest(const std::vector<uint8_t>& req) {
    if (req.empty()) {
        return { false, {}, 0x13 };  // NRC: incorrectMessageLengthOrInvalidFormat
    }
    const uint8_t sid = req[0];
    switch (sid) {
        case 0x10: return HandleDiagnosticSession(req);
        case 0x11: return HandleEcuReset(req);
        case 0x3E: return HandleTesterPresent(req);
        case 0x27: return HandleSecurityAccess(req);
        case 0x22: return HandleReadDataById(req);
        case 0x2E: return HandleWriteDataById(req);
        default:
            return { false, {}, 0x11 };  // NRC: serviceNotSupported
    }
}

UdsResponse UdsHandler::HandleDiagnosticSession(const std::vector<uint8_t>& req) {
    if (req.size() < 2) return { false, {}, 0x13 };
    const uint8_t sub_fn = req[1];
    if (sub_fn < 0x01 || sub_fn > 0x03)
        return { false, {}, 0x12 };  // NRC: subFunctionNotSupported
    active_session_ = sub_fn;
    // Positive response: SID + 0x40, echo sub-function
    return { true, { static_cast<uint8_t>(0x10 + 0x40), sub_fn }, 0x00 };
}

UdsResponse UdsHandler::HandleEcuReset(const std::vector<uint8_t>& req) {
    if (req.size() < 2) return { false, {}, 0x13 };
    const uint8_t reset_type = req[1];
    if (reset_type < 0x01 || reset_type > 0x03)
        return { false, {}, 0x12 };
    return { true, { static_cast<uint8_t>(0x11 + 0x40), reset_type }, 0x00 };
}

UdsResponse UdsHandler::HandleTesterPresent(const std::vector<uint8_t>& req) {
    if (req.size() < 2) return { false, {}, 0x13 };
    return { true, { static_cast<uint8_t>(0x3E + 0x40), 0x00 }, 0x00 };
}

UdsResponse UdsHandler::HandleSecurityAccess(const std::vector<uint8_t>& req) {
    if (req.size() < 2) return { false, {}, 0x13 };
    const uint8_t sub_fn = req[1];
    if (sub_fn == 0x01) {
        // Request seed — return dummy seed 0xDEAD
        return { true, { 0x67, 0x01, 0xDE, 0xAD }, 0x00 };
    }
    if (sub_fn == 0x02) {
        // Send key — accept key 0xBEEF
        if (req.size() >= 4 && req[2] == 0xBE && req[3] == 0xEF) {
            security_unlocked_ = true;
            return { true, { 0x67, 0x02 }, 0x00 };
        }
        return { false, {}, 0x35 };  // NRC: invalidKey
    }
    return { false, {}, 0x12 };
}

UdsResponse UdsHandler::HandleReadDataById(const std::vector<uint8_t>& req) {
    if (req.size() < 3) return { false, {}, 0x13 };
    // DID 0xF190 = VIN
    if (req[1] == 0xF1 && req[2] == 0x90) {
        std::vector<uint8_t> resp = { 0x62, 0xF1, 0x90 };
        // Dummy VIN: 17 bytes
        const char vin[] = "WBAXXXXXXXX123456";
        for (char c : vin) if (c) resp.push_back(static_cast<uint8_t>(c));
        return { true, resp, 0x00 };
    }
    return { false, {}, 0x31 };  // NRC: requestOutOfRange
}

UdsResponse UdsHandler::HandleWriteDataById(const std::vector<uint8_t>& req) {
    if (!security_unlocked_)
        return { false, {}, 0x33 };  // NRC: securityAccessDenied
    if (req.size() < 4) return { false, {}, 0x13 };
    return { true, { static_cast<uint8_t>(0x2E + 0x40), req[1], req[2] }, 0x00 };
}
