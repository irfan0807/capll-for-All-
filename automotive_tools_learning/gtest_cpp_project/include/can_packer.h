#pragma once
#include <cstdint>
#include <cstring>
#include <vector>

// ─────────────────────────────────────────────────────────────
//  CAN Signal Descriptor
// ─────────────────────────────────────────────────────────────
struct CanSignalDef {
    uint8_t  start_bit;    // LSB position in 64-bit frame
    uint8_t  length_bits;  // 1..64
    bool     is_intel;     // true = little-endian (Intel), false = Motorola
    bool     is_signed;
};

// ─────────────────────────────────────────────────────────────
//  CanPacker  –  pack/unpack raw signal values to/from CAN frames
// ─────────────────────────────────────────────────────────────
class CanPacker {
public:
    // Pack a raw integer value into an 8-byte CAN frame buffer
    static void Pack(uint8_t (&frame)[8],
                     const CanSignalDef& sig,
                     int64_t value);

    // Unpack a raw integer value from an 8-byte CAN frame buffer
    static int64_t Unpack(const uint8_t (&frame)[8],
                           const CanSignalDef& sig);
};
