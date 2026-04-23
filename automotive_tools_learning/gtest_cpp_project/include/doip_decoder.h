#pragma once
#include <cstdint>
#include <vector>

// ─────────────────────────────────────────────────────────────
//  DoIPDecoder  –  minimal DoIP packet decoder
//  Must NOT crash or corrupt memory for ANY input
// ─────────────────────────────────────────────────────────────
struct DoIPResult {
    bool    valid;
    uint8_t payload_type;
    std::vector<uint8_t> payload;
};

class DoIPDecoder {
public:
    // Header: [2B version][2B payload_type][4B payload_length][Payload...]
    static constexpr uint8_t  DOIP_VERSION        = 0x02;
    static constexpr uint8_t  DOIP_INVERSE_VERSION = 0xFD;
    static constexpr size_t   HEADER_SIZE          = 8;

    DoIPResult Decode(const uint8_t* data, size_t size);
};
