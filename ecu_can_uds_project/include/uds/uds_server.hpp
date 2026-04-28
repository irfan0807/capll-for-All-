#pragma once

#include "uds_types.hpp"
#include "../can/can_bus.hpp"
#include <array>
#include <cstdint>

namespace automotive {
namespace uds {

/// ISO-TP frame type identifiers
enum class ISOTPFrameType : uint8_t {
    SINGLE_FRAME      = 0x00U,
    FIRST_FRAME       = 0x10U,
    CONSECUTIVE_FRAME = 0x20U,
    FLOW_CONTROL      = 0x30U,
};

/// ISO-TP reassembly state
enum class ISOTPState : uint8_t {
    IDLE,
    RECEIVING_MULTI_FRAME,
    TRANSMITTING_MULTI_FRAME,
};

/**
 * @brief UDS Server implementation (ISO 14229-1)
 *
 * Handles:
 *  - ISO-TP (ISO 15765-2) segmentation / reassembly
 *  - Session management (0x10)
 *  - Security access with seed/key (0x27)
 *  - ECU reset (0x11)
 *  - TesterPresent keep-alive (0x3E)
 *  - ReadDataByIdentifier (0x22)
 *  - WriteDataByIdentifier (0x2E)
 *  - ReadDTCInformation (0x19)
 *  - ClearDiagnosticInformation (0x14)
 *  - RoutineControl (0x31)
 *
 * Binds to a CANBus instance and listens on configurable addresses.
 */
class UDSServer {
public:
    static constexpr uint32_t DEFAULT_TESTER_REQ_ID = 0x7DFU;  ///< functional
    static constexpr uint32_t DEFAULT_ECU_REQ_ID    = 0x7E0U;  ///< physical
    static constexpr uint32_t DEFAULT_ECU_RESP_ID   = 0x7E8U;  ///< response

    static constexpr uint32_t SESSION_TIMEOUT_MS    = 5000U;   ///< P3 timeout
    static constexpr uint32_t SECURITY_LOCKOUT_MS   = 10000U;  ///< After max attempts
    static constexpr uint8_t  MAX_SECURITY_ATTEMPTS = 3U;

    /**
     * @param bus         Reference to the CAN bus to use
     * @param physReqId   Physical request CAN ID (tester → ECU)
     * @param funcReqId   Functional request CAN ID (broadcast)
     * @param respId      Response CAN ID (ECU → tester)
     */
    explicit UDSServer(can::CANBus& bus,
                       uint32_t physReqId = DEFAULT_ECU_REQ_ID,
                       uint32_t funcReqId = DEFAULT_TESTER_REQ_ID,
                       uint32_t respId    = DEFAULT_ECU_RESP_ID);

    ~UDSServer();

    UDSServer(const UDSServer&) = delete;
    UDSServer& operator=(const UDSServer&) = delete;

    // --- Lifecycle ---
    bool initialize();
    void shutdown();

    /**
     * @brief Must be called periodically (e.g., every 1ms) to:
     *        - Process ISO-TP reassembly timeouts
     *        - Update session timeout timer
     *        - Dispatch pending service handlers
     */
    void cyclic();

    // --- Configuration ---
    /**
     * @brief Register a readable/writable DID entry
     */
    bool registerDID(uint16_t did,
                     const uint8_t* initialData,
                     uint8_t dataLen,
                     bool readable,
                     bool writable,
                     DiagSession minReadSession  = DiagSession::DEFAULT,
                     DiagSession minWriteSession = DiagSession::EXTENDED_DIAGNOSTIC);

    /**
     * @brief Update the live data for a DID (called by application layer)
     */
    bool updateDIDData(uint16_t did, const uint8_t* data, uint8_t dataLen);

    /**
     * @brief Register a custom service handler
     */
    bool registerServiceHandler(ServiceID sid, ServiceHandler handler);

    // --- State ---
    DiagSession getCurrentSession() const noexcept { return m_currentSession; }
    bool        isSecurityUnlocked(uint8_t level) const noexcept;
    uint32_t    getSessionElapsedMs() const noexcept;

    // --- Telemetry ---
    uint32_t getRxRequestCount() const noexcept { return m_rxRequestCount; }
    uint32_t getTxResponseCount()const noexcept { return m_txResponseCount; }
    uint32_t getNRCCount()       const noexcept { return m_nrcCount; }

private:
    // ISO-TP layer
    void onCANFrameReceived(const can::CANFrame& frame);
    bool isoTpAssemble(const can::CANFrame& frame, UDSRequest& outRequest);
    void isoTpSendResponse(const UDSResponse& response);
    void isoTpSendFlowControl(uint8_t fcFlag);

    // Service dispatch
    void dispatchRequest(const UDSRequest& request);
    void sendNRC(uint8_t serviceId, NRC nrc, bool suppressOnFunctional = true);

    // Built-in service handlers
    void handleDiagnosticSessionControl(const UDSRequest& req, UDSResponse& resp);
    void handleECUReset               (const UDSRequest& req, UDSResponse& resp);
    void handleSecurityAccess         (const UDSRequest& req, UDSResponse& resp);
    void handleTesterPresent          (const UDSRequest& req, UDSResponse& resp);
    void handleReadDataByIdentifier   (const UDSRequest& req, UDSResponse& resp);
    void handleWriteDataByIdentifier  (const UDSRequest& req, UDSResponse& resp);
    void handleReadDTCInformation     (const UDSRequest& req, UDSResponse& resp);
    void handleClearDiagnosticInfo    (const UDSRequest& req, UDSResponse& resp);
    void handleRoutineControl         (const UDSRequest& req, UDSResponse& resp);

    // Security
    uint32_t calculateKey(uint32_t seed, uint8_t level) const;

    // Session management
    void updateSessionTimer();
    bool isSessionAllowed(DiagSession required) const noexcept;

    // Members
    can::CANBus& m_bus;
    uint32_t m_physReqId;
    uint32_t m_funcReqId;
    uint32_t m_respId;
    bool m_initialized{false};
    int8_t m_rxCallbackHandle{-1};

    DiagSession m_currentSession{DiagSession::DEFAULT};
    uint32_t    m_sessionTimerStart{0U};
    bool        m_testerPresentReceived{false};

    // Security
    static constexpr uint8_t MAX_SECURITY_LEVELS = 4U;
    SecurityLevel m_securityLevels[MAX_SECURITY_LEVELS]{};

    // DID storage
    static constexpr uint8_t MAX_DIDS = 32U;
    DIDEntry m_dids[MAX_DIDS]{};
    uint8_t  m_didCount{0U};

    // Custom service handlers
    static constexpr uint8_t MAX_SERVICE_HANDLERS = 8U;
    struct ServiceHandlerEntry {
        ServiceID      sid{};
        ServiceHandler handler;
        bool           active{false};
    };
    std::array<ServiceHandlerEntry, MAX_SERVICE_HANDLERS> m_handlers{};

    // ISO-TP reassembly
    ISOTPState m_isoTpState{ISOTPState::IDLE};
    uint8_t    m_isoTpRxBuffer[UDS_MAX_PDU_SIZE]{};
    uint16_t   m_isoTpExpectedLen{0U};
    uint16_t   m_isoTpReceivedLen{0U};
    uint8_t    m_isoTpSeqCounter{0U};
    uint32_t   m_isoTpTimerStart{0U};

    // ISO-TP transmit
    uint8_t  m_isoTpTxBuffer[UDS_MAX_PDU_SIZE]{};
    uint16_t m_isoTpTxLen{0U};
    uint16_t m_isoTpTxOffset{0U};
    uint8_t  m_isoTpTxSeqCounter{0U};
    bool     m_isoTpTxPending{false};

    // Counters
    uint32_t m_rxRequestCount{0U};
    uint32_t m_txResponseCount{0U};
    uint32_t m_nrcCount{0U};
};

} // namespace uds
} // namespace automotive
