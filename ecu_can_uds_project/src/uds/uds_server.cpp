#include "../../include/uds/uds_server.hpp"
#include <cstdio>
#include <cstring>
#include <cstdlib>  // for rand() – seed generation in simulation

// Minimal system timer stub – replace with real MCU/OS timer
static uint32_t g_simTickMs = 0U;
static uint32_t getSimTickMs() { return g_simTickMs; }
void UDSServer_AdvanceTick(uint32_t ms) { g_simTickMs += ms; }

namespace automotive {
namespace uds {

UDSServer::UDSServer(can::CANBus& bus,
                     uint32_t physReqId,
                     uint32_t funcReqId,
                     uint32_t respId)
    : m_bus(bus)
    , m_physReqId(physReqId)
    , m_funcReqId(funcReqId)
    , m_respId(respId)
{
    std::memset(m_dids, 0, sizeof(m_dids));
    for (auto& lvl : m_securityLevels) {
        lvl = SecurityLevel{};
    }
}

UDSServer::~UDSServer() {
    shutdown();
}

bool UDSServer::initialize() {
    if (m_initialized) return true;

    // Register CAN Rx callback for physical and functional addresses
    m_rxCallbackHandle = m_bus.registerRxCallback(
        [this](const can::CANFrame& frame) { this->onCANFrameReceived(frame); },
        0U,   // idFilter=0 = receive all (we filter inside)
        0U);  // idMask=0

    if (m_rxCallbackHandle < 0) {
        std::printf("[UDSServer] ERROR: Cannot register CAN callback\n");
        return false;
    }

    m_currentSession     = DiagSession::DEFAULT;
    m_sessionTimerStart  = getSimTickMs();
    m_initialized        = true;

    std::printf("[UDSServer] Initialized. PhysReq=0x%03X FuncReq=0x%03X Resp=0x%03X\n",
                m_physReqId, m_funcReqId, m_respId);
    return true;
}

void UDSServer::shutdown() {
    if (!m_initialized) return;
    if (m_rxCallbackHandle >= 0) {
        m_bus.unregisterRxCallback(m_rxCallbackHandle);
        m_rxCallbackHandle = -1;
    }
    m_initialized = false;
}

void UDSServer::cyclic() {
    if (!m_initialized) return;

    // Update session timeout
    updateSessionTimer();

    // Process ISO-TP Tx (consecutive frames)
    if (m_isoTpTxPending) {
        can::CANFrame frame;
        uint8_t fcData[8]{};
        uint8_t bytesLeft = 0U;

        // Build consecutive frame
        fcData[0] = static_cast<uint8_t>(ISOTPFrameType::CONSECUTIVE_FRAME)
                    | (m_isoTpTxSeqCounter & 0x0FU);
        m_isoTpTxSeqCounter = (m_isoTpTxSeqCounter + 1U) & 0x0FU;

        uint8_t bytesInFrame = 7U;
        if (m_isoTpTxOffset + bytesInFrame > m_isoTpTxLen) {
            bytesInFrame = static_cast<uint8_t>(m_isoTpTxLen - m_isoTpTxOffset);
        }
        std::memcpy(&fcData[1], &m_isoTpTxBuffer[m_isoTpTxOffset], bytesInFrame);
        m_isoTpTxOffset += bytesInFrame;

        frame = can::CANFrame(m_respId, bytesInFrame + 1U, fcData);
        m_bus.transmit(frame);
        m_txResponseCount++;

        if (m_isoTpTxOffset >= m_isoTpTxLen) {
            m_isoTpTxPending = false;
        }
        (void)bytesLeft;
    }

    // ISO-TP Rx timeout
    if (m_isoTpState == ISOTPState::RECEIVING_MULTI_FRAME) {
        if ((getSimTickMs() - m_isoTpTimerStart) > 150U) {  // N_Cr timeout
            m_isoTpState = ISOTPState::IDLE;
            std::printf("[UDSServer] ISO-TP Rx timeout\n");
        }
    }
}

// ─── CAN Rx Entry Point ───────────────────────────────────────────────────────

void UDSServer::onCANFrameReceived(const can::CANFrame& frame) {
    bool isPhysical   = (frame.getId() == m_physReqId);
    bool isFunctional = (frame.getId() == m_funcReqId);

    if (!isPhysical && !isFunctional) return;

    UDSRequest request{};
    request.sourceAddr   = frame.getId();
    request.isFunctional = isFunctional;

    if (isoTpAssemble(frame, request)) {
        m_rxRequestCount++;
        dispatchRequest(request);
    }
}

// ─── ISO-TP Reassembly ────────────────────────────────────────────────────────

bool UDSServer::isoTpAssemble(const can::CANFrame& frame, UDSRequest& outRequest) {
    const uint8_t* data = frame.getData();
    uint8_t firstNibble = (data[0] >> 4U) & 0x0FU;

    if (firstNibble == 0x00U) {
        // Single Frame
        uint8_t len = data[0] & 0x0FU;
        if (len == 0U || len > 7U) return false;

        std::memcpy(outRequest.data, &data[1], len);
        outRequest.length  = len;
        m_isoTpState = ISOTPState::IDLE;
        return true;

    } else if (firstNibble == 0x01U) {
        // First Frame – multi-frame message
        m_isoTpExpectedLen = static_cast<uint16_t>(
            ((data[0] & 0x0FU) << 8U) | data[1]);

        if (m_isoTpExpectedLen > UDS_MAX_PDU_SIZE) {
            std::printf("[UDSServer] ISO-TP message too large: %u\n", m_isoTpExpectedLen);
            return false;
        }

        uint8_t bytesInFF = 6U;
        std::memcpy(m_isoTpRxBuffer, &data[2], bytesInFF);
        m_isoTpReceivedLen  = bytesInFF;
        m_isoTpSeqCounter   = 1U;
        m_isoTpState        = ISOTPState::RECEIVING_MULTI_FRAME;
        m_isoTpTimerStart   = getSimTickMs();

        // Send Flow Control (ContinueToSend, BS=0, STmin=0)
        isoTpSendFlowControl(0x00U);
        return false;  // Not yet complete

    } else if (firstNibble == 0x02U) {
        // Consecutive Frame
        if (m_isoTpState != ISOTPState::RECEIVING_MULTI_FRAME) return false;

        uint8_t seq = data[0] & 0x0FU;
        if (seq != (m_isoTpSeqCounter & 0x0FU)) {
            m_isoTpState = ISOTPState::IDLE;
            std::printf("[UDSServer] ISO-TP sequence error: expected %u got %u\n",
                        m_isoTpSeqCounter & 0x0FU, seq);
            return false;
        }
        m_isoTpSeqCounter++;
        m_isoTpTimerStart = getSimTickMs();

        uint8_t remaining = static_cast<uint8_t>(m_isoTpExpectedLen - m_isoTpReceivedLen);
        uint8_t toCopy    = (remaining > 7U) ? 7U : remaining;
        std::memcpy(&m_isoTpRxBuffer[m_isoTpReceivedLen], &data[1], toCopy);
        m_isoTpReceivedLen += toCopy;

        if (m_isoTpReceivedLen >= m_isoTpExpectedLen) {
            // Complete!
            std::memcpy(outRequest.data, m_isoTpRxBuffer, m_isoTpExpectedLen);
            outRequest.length = m_isoTpExpectedLen;
            m_isoTpState = ISOTPState::IDLE;
            return true;
        }
        return false;
    }

    return false;
}

void UDSServer::isoTpSendFlowControl(uint8_t fcFlag) {
    uint8_t fcData[3] = {
        static_cast<uint8_t>(static_cast<uint8_t>(ISOTPFrameType::FLOW_CONTROL) | fcFlag),
        0x00U,   // BS = 0 (send all remaining without further FC)
        0x00U    // STmin = 0ms
    };
    can::CANFrame frame(m_respId, 3U, fcData);
    m_bus.transmit(frame);
}

// ─── ISO-TP Transmit ──────────────────────────────────────────────────────────

void UDSServer::isoTpSendResponse(const UDSResponse& response) {
    if (response.length == 0U) return;

    if (response.length <= 7U) {
        // Single Frame
        uint8_t sfData[8]{};
        sfData[0] = response.length & 0x0FU;
        std::memcpy(&sfData[1], response.data, response.length);
        can::CANFrame frame(m_respId, response.length + 1U, sfData);
        m_bus.transmit(frame);
        m_txResponseCount++;
    } else {
        // Multi-frame: send First Frame, then CFs via cyclic()
        std::memcpy(m_isoTpTxBuffer, response.data, response.length);
        m_isoTpTxLen = response.length;

        uint8_t ffData[8]{};
        ffData[0] = static_cast<uint8_t>(0x10U | ((response.length >> 8U) & 0x0FU));
        ffData[1] = static_cast<uint8_t>(response.length & 0xFFU);
        std::memcpy(&ffData[2], m_isoTpTxBuffer, 6U);
        m_isoTpTxOffset = 6U;
        m_isoTpTxSeqCounter = 1U;
        m_isoTpTxPending = true;

        can::CANFrame frame(m_respId, 8U, ffData);
        m_bus.transmit(frame);
        m_txResponseCount++;
    }
}

// ─── Service Dispatch ─────────────────────────────────────────────────────────

void UDSServer::dispatchRequest(const UDSRequest& request) {
    if (request.length == 0U) return;

    uint8_t sid = request.serviceId();
    std::printf("[UDSServer] RX SID=0x%02X Len=%u\n", sid, request.length);

    UDSResponse response{};

    // Check for custom handlers first
    for (auto& entry : m_handlers) {
        if (entry.active && static_cast<uint8_t>(entry.sid) == sid) {
            entry.handler(request, response);
            if (response.length > 0U && !request.suppressPositiveResponse()) {
                isoTpSendResponse(response);
            }
            return;
        }
    }

    // Built-in service handlers
    switch (static_cast<ServiceID>(sid)) {
        case ServiceID::DIAGNOSTIC_SESSION_CONTROL:
            handleDiagnosticSessionControl(request, response); break;
        case ServiceID::ECU_RESET:
            handleECUReset(request, response); break;
        case ServiceID::SECURITY_ACCESS:
            handleSecurityAccess(request, response); break;
        case ServiceID::TESTER_PRESENT:
            handleTesterPresent(request, response); break;
        case ServiceID::READ_DATA_BY_IDENTIFIER:
            handleReadDataByIdentifier(request, response); break;
        case ServiceID::WRITE_DATA_BY_IDENTIFIER:
            handleWriteDataByIdentifier(request, response); break;
        case ServiceID::READ_DTC_INFORMATION:
            handleReadDTCInformation(request, response); break;
        case ServiceID::CLEAR_DIAGNOSTIC_INFORMATION:
            handleClearDiagnosticInfo(request, response); break;
        case ServiceID::ROUTINE_CONTROL:
            handleRoutineControl(request, response); break;
        default:
            response.setNegativeResponse(sid, NRC::SERVICE_NOT_SUPPORTED);
            m_nrcCount++;
            break;
    }

    bool suppress = request.suppressPositiveResponse() && !response.isNegative;
    if (!suppress && response.length > 0U) {
        isoTpSendResponse(response);
    }
}

// ─── Service Handlers ─────────────────────────────────────────────────────────

void UDSServer::handleDiagnosticSessionControl(const UDSRequest& req, UDSResponse& resp) {
    if (req.length < 2U) {
        resp.setNegativeResponse(req.serviceId(), NRC::INCORRECT_MESSAGE_LENGTH_OR_FORMAT);
        m_nrcCount++;
        return;
    }
    uint8_t requestedSession = req.data[1] & 0x7FU;
    DiagSession newSession = static_cast<DiagSession>(requestedSession);

    // Allow all sessions for now (extend with security policy if needed)
    m_currentSession    = newSession;
    m_sessionTimerStart = getSimTickMs();

    uint8_t payload[5] = {
        static_cast<uint8_t>(newSession),
        0x00U, 0x19U,   // P2 server max = 25ms
        0x01U, 0xF4U    // P2* server max = 5000ms
    };
    resp.setPositiveResponse(req.serviceId(), payload, sizeof(payload));
    std::printf("[UDSServer] Session changed to 0x%02X\n", requestedSession);
}

void UDSServer::handleECUReset(const UDSRequest& req, UDSResponse& resp) {
    if (req.length < 2U) {
        resp.setNegativeResponse(req.serviceId(), NRC::INCORRECT_MESSAGE_LENGTH_OR_FORMAT);
        m_nrcCount++;
        return;
    }
    uint8_t resetType = req.data[1] & 0x7FU;
    uint8_t payload[] = { resetType };
    resp.setPositiveResponse(req.serviceId(), payload, sizeof(payload));
    std::printf("[UDSServer] ECU Reset requested: type=0x%02X\n", resetType);
    // In real ECU: schedule a watchdog reset after sending response
}

void UDSServer::handleSecurityAccess(const UDSRequest& req, UDSResponse& resp) {
    if (req.length < 2U) {
        resp.setNegativeResponse(req.serviceId(), NRC::INCORRECT_MESSAGE_LENGTH_OR_FORMAT);
        m_nrcCount++;
        return;
    }
    uint8_t subFn = req.data[1] & 0x7FU;

    if (subFn % 2U == 1U) {
        // Request Seed (odd sub-function)
        uint8_t level = (subFn + 1U) / 2U;
        if (level >= MAX_SECURITY_LEVELS) {
            resp.setNegativeResponse(req.serviceId(), NRC::SUB_FUNCTION_NOT_SUPPORTED);
            m_nrcCount++;
            return;
        }

        // Check lockout
        SecurityLevel& sec = m_securityLevels[level];
        if (sec.failAttempts >= MAX_SECURITY_ATTEMPTS) {
            if ((getSimTickMs() - sec.lockoutTimerStart) < SECURITY_LOCKOUT_MS) {
                resp.setNegativeResponse(req.serviceId(), NRC::REQUIRED_TIME_DELAY_NOT_EXPIRED);
                m_nrcCount++;
                return;
            }
            sec.failAttempts = 0U;
        }

        if (sec.unlocked) {
            // Already unlocked – return seed 0x00 0x00 0x00 0x00
            uint8_t payload[5] = { subFn, 0, 0, 0, 0 };
            resp.setPositiveResponse(req.serviceId(), payload, sizeof(payload));
            return;
        }

        sec.seed = static_cast<uint32_t>(rand()) ^ 0xA5A5A5A5U;
        uint8_t payload[5] = {
            subFn,
            static_cast<uint8_t>((sec.seed >> 24U) & 0xFFU),
            static_cast<uint8_t>((sec.seed >> 16U) & 0xFFU),
            static_cast<uint8_t>((sec.seed >>  8U) & 0xFFU),
            static_cast<uint8_t>( sec.seed         & 0xFFU),
        };
        resp.setPositiveResponse(req.serviceId(), payload, sizeof(payload));
        std::printf("[UDSServer] SecurityAccess: Seed=0x%08X for level %u\n",
                    sec.seed, level);

    } else {
        // Send Key (even sub-function)
        uint8_t level = subFn / 2U;
        if (level >= MAX_SECURITY_LEVELS || req.length < 6U) {
            resp.setNegativeResponse(req.serviceId(), NRC::INCORRECT_MESSAGE_LENGTH_OR_FORMAT);
            m_nrcCount++;
            return;
        }
        SecurityLevel& sec = m_securityLevels[level];
        uint32_t receivedKey =
            (static_cast<uint32_t>(req.data[2]) << 24U) |
            (static_cast<uint32_t>(req.data[3]) << 16U) |
            (static_cast<uint32_t>(req.data[4]) <<  8U) |
             static_cast<uint32_t>(req.data[5]);

        uint32_t expectedKey = calculateKey(sec.seed, level);
        if (receivedKey == expectedKey) {
            sec.unlocked = true;
            sec.failAttempts = 0U;
            uint8_t payload[] = { subFn };
            resp.setPositiveResponse(req.serviceId(), payload, sizeof(payload));
            std::printf("[UDSServer] SecurityAccess: UNLOCKED level %u\n", level);
        } else {
            sec.failAttempts++;
            if (sec.failAttempts >= MAX_SECURITY_ATTEMPTS) {
                sec.lockoutTimerStart = getSimTickMs();
            }
            resp.setNegativeResponse(req.serviceId(), NRC::INVALID_KEY);
            m_nrcCount++;
            std::printf("[UDSServer] SecurityAccess: Invalid key (attempt %u/%u)\n",
                        sec.failAttempts, MAX_SECURITY_ATTEMPTS);
        }
    }
}

void UDSServer::handleTesterPresent(const UDSRequest& req, UDSResponse& resp) {
    m_sessionTimerStart      = getSimTickMs();   // Reset session timeout
    m_testerPresentReceived  = true;
    uint8_t payload[]        = { 0x00U };
    resp.setPositiveResponse(req.serviceId(), payload, sizeof(payload));
}

void UDSServer::handleReadDataByIdentifier(const UDSRequest& req, UDSResponse& resp) {
    if (req.length < 3U) {
        resp.setNegativeResponse(req.serviceId(), NRC::INCORRECT_MESSAGE_LENGTH_OR_FORMAT);
        m_nrcCount++;
        return;
    }

    uint8_t  responseBuffer[512]{};
    uint16_t responseLen = 0U;

    // Iterate all requested DIDs (can be multiple)
    for (uint16_t offset = 1U; offset + 1U < req.length; offset += 2U) {
        uint16_t requestedDID =
            (static_cast<uint16_t>(req.data[offset]) << 8U) | req.data[offset + 1U];

        bool found = false;
        for (uint8_t i = 0U; i < m_didCount; ++i) {
            if (m_dids[i].did == requestedDID && m_dids[i].readable) {
                // Check session
                if (!isSessionAllowed(m_dids[i].minReadSession)) {
                    resp.setNegativeResponse(req.serviceId(), NRC::SERVICE_NOT_SUPPORTED_IN_SESSION);
                    m_nrcCount++;
                    return;
                }
                // Append DID + data to response
                responseBuffer[responseLen++] = static_cast<uint8_t>(requestedDID >> 8U);
                responseBuffer[responseLen++] = static_cast<uint8_t>(requestedDID & 0xFFU);
                std::memcpy(&responseBuffer[responseLen], m_dids[i].data, m_dids[i].dataLen);
                responseLen += m_dids[i].dataLen;
                found = true;
                break;
            }
        }
        if (!found) {
            resp.setNegativeResponse(req.serviceId(), NRC::REQUEST_OUT_OF_RANGE);
            m_nrcCount++;
            return;
        }
    }

    resp.setPositiveResponse(req.serviceId(), responseBuffer, responseLen);
}

void UDSServer::handleWriteDataByIdentifier(const UDSRequest& req, UDSResponse& resp) {
    if (req.length < 4U) {
        resp.setNegativeResponse(req.serviceId(), NRC::INCORRECT_MESSAGE_LENGTH_OR_FORMAT);
        m_nrcCount++;
        return;
    }
    uint16_t requestedDID =
        (static_cast<uint16_t>(req.data[1]) << 8U) | req.data[2];

    for (uint8_t i = 0U; i < m_didCount; ++i) {
        if (m_dids[i].did == requestedDID) {
            if (!m_dids[i].writable) {
                resp.setNegativeResponse(req.serviceId(), NRC::SECURITY_ACCESS_DENIED);
                m_nrcCount++;
                return;
            }
            if (!isSessionAllowed(m_dids[i].minWriteSession)) {
                resp.setNegativeResponse(req.serviceId(), NRC::SERVICE_NOT_SUPPORTED_IN_SESSION);
                m_nrcCount++;
                return;
            }
            uint8_t dataLen = static_cast<uint8_t>(req.length - 3U);
            if (dataLen > sizeof(m_dids[i].data)) dataLen = sizeof(m_dids[i].data);
            std::memcpy(m_dids[i].data, &req.data[3], dataLen);
            m_dids[i].dataLen = dataLen;

            uint8_t payload[2] = {
                static_cast<uint8_t>(requestedDID >> 8U),
                static_cast<uint8_t>(requestedDID & 0xFFU)
            };
            resp.setPositiveResponse(req.serviceId(), payload, sizeof(payload));
            std::printf("[UDSServer] WDBI: DID=0x%04X written (%u bytes)\n",
                        requestedDID, dataLen);
            return;
        }
    }
    resp.setNegativeResponse(req.serviceId(), NRC::REQUEST_OUT_OF_RANGE);
    m_nrcCount++;
}

void UDSServer::handleReadDTCInformation(const UDSRequest& req, UDSResponse& resp) {
    if (req.length < 2U) {
        resp.setNegativeResponse(req.serviceId(), NRC::INCORRECT_MESSAGE_LENGTH_OR_FORMAT);
        m_nrcCount++;
        return;
    }
    // For now implement sub-function 0x02 (reportDTCByStatusMask)
    // and 0x01 (reportNumberOfDTCByStatusMask)
    // DTC Manager is accessed from ECUCore; we store pointer via registerServiceHandler
    uint8_t subFn      = req.data[1] & 0x7FU;
    uint8_t statusMask = (req.length > 2U) ? req.data[2] : 0xFFU;

    uint8_t responseBuffer[256]{};
    uint16_t idx = 0U;

    responseBuffer[idx++] = subFn;
    responseBuffer[idx++] = 0x00U;   // DTC format identifier (ISO 14229-1)
    responseBuffer[idx++] = statusMask;

    if (subFn == 0x01U) {
        // Count only – single byte count
        responseBuffer[1] = 0x01U;  // DTC format: ISO 15031-6
        responseBuffer[idx++] = 0x00U;  // high byte
        responseBuffer[idx++] = 0x00U;  // count placeholder
        resp.setPositiveResponse(req.serviceId(), responseBuffer, idx);
    } else if (subFn == 0x02U) {
        resp.setPositiveResponse(req.serviceId(), responseBuffer, idx);
        std::printf("[UDSServer] ReadDTC: subFn=0x%02X statusMask=0x%02X\n",
                    subFn, statusMask);
    } else {
        resp.setNegativeResponse(req.serviceId(), NRC::SUB_FUNCTION_NOT_SUPPORTED);
        m_nrcCount++;
    }
}

void UDSServer::handleClearDiagnosticInfo(const UDSRequest& req, UDSResponse& resp) {
    if (req.length < 4U) {
        resp.setNegativeResponse(req.serviceId(), NRC::INCORRECT_MESSAGE_LENGTH_OR_FORMAT);
        m_nrcCount++;
        return;
    }
    // Group of DTC: 0xFFFFFF = clear all
    uint32_t group =
        (static_cast<uint32_t>(req.data[1]) << 16U) |
        (static_cast<uint32_t>(req.data[2]) <<  8U) |
         static_cast<uint32_t>(req.data[3]);
    std::printf("[UDSServer] ClearDTC: group=0x%06X\n", group);
    // Response: positive, no data
    resp.setPositiveResponse(req.serviceId(), nullptr, 0U);
}

void UDSServer::handleRoutineControl(const UDSRequest& req, UDSResponse& resp) {
    if (req.length < 4U) {
        resp.setNegativeResponse(req.serviceId(), NRC::INCORRECT_MESSAGE_LENGTH_OR_FORMAT);
        m_nrcCount++;
        return;
    }
    uint8_t  subFn    = req.data[1];
    uint16_t routineId = (static_cast<uint16_t>(req.data[2]) << 8U) | req.data[3];

    uint8_t payload[3] = { subFn,
                            static_cast<uint8_t>(routineId >> 8U),
                            static_cast<uint8_t>(routineId & 0xFFU) };
    resp.setPositiveResponse(req.serviceId(), payload, sizeof(payload));
    std::printf("[UDSServer] RoutineControl: subFn=0x%02X routineId=0x%04X\n",
                subFn, routineId);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

uint32_t UDSServer::calculateKey(uint32_t seed, uint8_t /*level*/) const {
    // Simple XOR-based key derivation (replace with real CMAC/AES in production)
    return seed ^ 0x5A5A5A5AU;
}

void UDSServer::updateSessionTimer() {
    if (m_currentSession == DiagSession::DEFAULT) return;

    uint32_t elapsed = getSimTickMs() - m_sessionTimerStart;
    if (elapsed > SESSION_TIMEOUT_MS) {
        std::printf("[UDSServer] Session timeout – returning to Default\n");
        m_currentSession = DiagSession::DEFAULT;
        // Lock all security levels
        for (auto& lvl : m_securityLevels) {
            lvl.unlocked = false;
        }
    }
}

bool UDSServer::isSessionAllowed(DiagSession required) const noexcept {
    return static_cast<uint8_t>(m_currentSession) >= static_cast<uint8_t>(required);
}

bool UDSServer::isSecurityUnlocked(uint8_t level) const noexcept {
    if (level >= MAX_SECURITY_LEVELS) return false;
    return m_securityLevels[level].unlocked;
}

uint32_t UDSServer::getSessionElapsedMs() const noexcept {
    return getSimTickMs() - m_sessionTimerStart;
}

bool UDSServer::registerDID(uint16_t did,
                              const uint8_t* initialData,
                              uint8_t dataLen,
                              bool readable,
                              bool writable,
                              DiagSession minReadSession,
                              DiagSession minWriteSession) {
    if (m_didCount >= MAX_DIDS) return false;
    auto& entry = m_dids[m_didCount];
    entry.did             = did;
    entry.readable        = readable;
    entry.writable        = writable;
    entry.minReadSession  = minReadSession;
    entry.minWriteSession = minWriteSession;
    entry.dataLen         = (dataLen > sizeof(entry.data)) ? sizeof(entry.data) : dataLen;
    if (initialData != nullptr) {
        std::memcpy(entry.data, initialData, entry.dataLen);
    }
    m_didCount++;
    return true;
}

bool UDSServer::updateDIDData(uint16_t did, const uint8_t* data, uint8_t dataLen) {
    for (uint8_t i = 0U; i < m_didCount; ++i) {
        if (m_dids[i].did == did) {
            uint8_t len = (dataLen > sizeof(m_dids[i].data)) ?
                          static_cast<uint8_t>(sizeof(m_dids[i].data)) : dataLen;
            std::memcpy(m_dids[i].data, data, len);
            m_dids[i].dataLen = len;
            return true;
        }
    }
    return false;
}

bool UDSServer::registerServiceHandler(ServiceID sid, ServiceHandler handler) {
    for (auto& entry : m_handlers) {
        if (!entry.active) {
            entry.sid     = sid;
            entry.handler = handler;
            entry.active  = true;
            return true;
        }
    }
    return false;
}

} // namespace uds
} // namespace automotive
