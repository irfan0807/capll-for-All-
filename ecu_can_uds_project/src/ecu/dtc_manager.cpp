#include "../../include/ecu/dtc_manager.hpp"
#include <cstring>
#include <cstdio>

namespace automotive {
namespace ecu {

DTCManager::DTCManager() {
    std::memset(m_records, 0, sizeof(m_records));
    std::memset(m_failCountThisCycle, 0, sizeof(m_failCountThisCycle));
    m_dtcCount = 0U;
}

void DTCManager::setDTC(uint32_t code,
                          DTCSeverity severity,
                          const DTCSnapshot* snapshot) {
    if (code == 0U) return;

    DTCRecord* rec = findOrCreateSlot(code);
    if (rec == nullptr) {
        std::printf("[DTCManager] WARNING: DTC storage full! Cannot set 0x%06X\n", code);
        return;
    }

    rec->code     = code;
    rec->severity = severity;
    rec->active   = true;
    rec->occurrenceCounter++;

    // Update status byte
    rec->statusByte |= DTCStatusBit::TEST_FAILED;
    rec->statusByte |= DTCStatusBit::TEST_FAILED_THIS_CYCLE;
    rec->statusByte |= DTCStatusBit::PENDING;
    rec->statusByte |= DTCStatusBit::FAILED_SINCE_CLEAR;
    rec->statusByte &= ~DTCStatusBit::NOT_COMPLETED_THIS_CYCLE;

    // Promote to confirmed after 2 consecutive failures
    uint8_t idx = static_cast<uint8_t>(rec - m_records);
    m_failCountThisCycle[idx]++;
    if (m_failCountThisCycle[idx] >= 2U) {
        rec->statusByte |= DTCStatusBit::CONFIRMED;
        rec->statusByte |= DTCStatusBit::WARNING_INDICATOR;
    }

    // Capture snapshot if provided and not already stored
    if (snapshot != nullptr && rec->snapshot.valid == 0U) {
        rec->snapshot = *snapshot;
        rec->snapshot.valid = 1U;
    }

    std::printf("[DTCManager] DTC SET: 0x%06X  Status=0x%02X  Count=%u\n",
                code, rec->statusByte, rec->occurrenceCounter);
}

void DTCManager::clearDTCFailed(uint32_t code) {
    DTCRecord* rec = findDTC(code);
    if (rec == nullptr) return;

    rec->statusByte &= ~DTCStatusBit::TEST_FAILED;
    rec->statusByte &= ~DTCStatusBit::TEST_FAILED_THIS_CYCLE;
    // Keep CONFIRMED and PENDING bits until drive cycle processing
}

void DTCManager::clearAllDTCs() {
    for (uint8_t i = 0U; i < MAX_DTC_RECORDS; ++i) {
        m_records[i] = DTCRecord{};
        m_failCountThisCycle[i] = 0U;
    }
    m_dtcCount = 0U;
    std::printf("[DTCManager] All DTCs cleared\n");
}

uint8_t DTCManager::getDTCStatus(uint32_t code) const {
    const DTCRecord* rec = findDTC(code);
    return (rec != nullptr) ? rec->statusByte : 0x00U;
}

bool DTCManager::isDTCActive(uint32_t code) const {
    const DTCRecord* rec = findDTC(code);
    return (rec != nullptr) && (rec->statusByte & DTCStatusBit::TEST_FAILED) != 0U;
}

bool DTCManager::isDTCConfirmed(uint32_t code) const {
    const DTCRecord* rec = findDTC(code);
    return (rec != nullptr) && (rec->statusByte & DTCStatusBit::CONFIRMED) != 0U;
}

uint8_t DTCManager::getDTCsByStatusMask(uint8_t statusMask,
                                          uint32_t* outCodes,
                                          uint8_t*  outStatus,
                                          uint8_t   maxRecords) const {
    uint8_t count = 0U;
    for (uint8_t i = 0U; i < MAX_DTC_RECORDS && count < maxRecords; ++i) {
        if (!m_records[i].active) continue;
        if ((m_records[i].statusByte & statusMask) != 0U) {
            if (outCodes  != nullptr) outCodes[count]  = m_records[i].code;
            if (outStatus != nullptr) outStatus[count] = m_records[i].statusByte;
            count++;
        }
    }
    return count;
}

uint8_t DTCManager::countDTCsByStatusMask(uint8_t statusMask) const {
    uint8_t count = 0U;
    for (uint8_t i = 0U; i < MAX_DTC_RECORDS; ++i) {
        if (m_records[i].active &&
            (m_records[i].statusByte & statusMask) != 0U) {
            count++;
        }
    }
    return count;
}

bool DTCManager::getDTCSnapshot(uint32_t code, DTCSnapshot& outSnapshot) const {
    const DTCRecord* rec = findDTC(code);
    if (rec != nullptr && rec->snapshot.valid != 0U) {
        outSnapshot = rec->snapshot;
        return true;
    }
    return false;
}

void DTCManager::processDriveCycle(bool cycleCompleted) {
    for (uint8_t i = 0U; i < MAX_DTC_RECORDS; ++i) {
        if (!m_records[i].active) continue;

        DTCRecord& rec = m_records[i];

        if (cycleCompleted) {
            // Clear "this cycle" bits
            rec.statusByte &= ~DTCStatusBit::TEST_FAILED_THIS_CYCLE;
            rec.statusByte &= ~DTCStatusBit::NOT_COMPLETED_THIS_CYCLE;
            rec.statusByte |=  DTCStatusBit::NOT_COMPLETED_SINCE_CLEAR;

            // If not failed this cycle, clear pending bit
            if ((rec.statusByte & DTCStatusBit::TEST_FAILED) == 0U) {
                rec.statusByte &= ~DTCStatusBit::PENDING;
                m_failCountThisCycle[i] = 0U;
            }
        }
    }
}

// ─── Private helpers ──────────────────────────────────────────────────────────

DTCRecord* DTCManager::findDTC(uint32_t code) {
    for (uint8_t i = 0U; i < MAX_DTC_RECORDS; ++i) {
        if (m_records[i].active && m_records[i].code == code) {
            return &m_records[i];
        }
    }
    return nullptr;
}

const DTCRecord* DTCManager::findDTC(uint32_t code) const {
    for (uint8_t i = 0U; i < MAX_DTC_RECORDS; ++i) {
        if (m_records[i].active && m_records[i].code == code) {
            return &m_records[i];
        }
    }
    return nullptr;
}

DTCRecord* DTCManager::findOrCreateSlot(uint32_t code) {
    // Check if already exists
    DTCRecord* existing = findDTC(code);
    if (existing != nullptr) return existing;

    // Find free slot
    for (uint8_t i = 0U; i < MAX_DTC_RECORDS; ++i) {
        if (!m_records[i].active) {
            m_dtcCount++;
            return &m_records[i];
        }
    }
    return nullptr;
}

} // namespace ecu
} // namespace automotive
