#include "can_packer.h"
#include <cstring>

void CanPacker::Pack(uint8_t (&frame)[8],
                     const CanSignalDef& sig,
                     int64_t value) {
    // Build a 64-bit working word from the frame
    uint64_t word = 0;
    std::memcpy(&word, frame, 8);

    // Mask to signal bit-length
    const uint64_t mask = (sig.length_bits < 64)
                          ? ((uint64_t(1) << sig.length_bits) - 1)
                          : ~uint64_t(0);
    const uint64_t uval = static_cast<uint64_t>(value) & mask;

    if (sig.is_intel) {
        // Intel (little-endian): start_bit is the LSB position in the 64-bit LE word
        word &= ~(mask << sig.start_bit);
        word |=  (uval << sig.start_bit);
    } else {
        // Motorola (big-endian): start_bit is the MSB position
        // Convert from Motorola bit numbering to shift in LE 64-bit word
        uint8_t msb_bit = sig.start_bit;
        uint8_t msb_byte = msb_bit / 8;
        uint8_t msb_bit_in_byte = msb_bit % 8;
        int shift = (int)(msb_byte * 8 + (7 - msb_bit_in_byte)) - (int)(sig.length_bits - 1);
        if (shift < 0) shift = 0;
        word &= ~(mask << shift);
        word |=  (uval << shift);
    }
    std::memcpy(frame, &word, 8);
}

int64_t CanPacker::Unpack(const uint8_t (&frame)[8],
                           const CanSignalDef& sig) {
    uint64_t word = 0;
    std::memcpy(&word, frame, 8);

    const uint64_t mask = (sig.length_bits < 64)
                          ? ((uint64_t(1) << sig.length_bits) - 1)
                          : ~uint64_t(0);
    uint64_t uval = 0;

    if (sig.is_intel) {
        uval = (word >> sig.start_bit) & mask;
    } else {
        uint8_t msb_bit = sig.start_bit;
        uint8_t msb_byte = msb_bit / 8;
        uint8_t msb_bit_in_byte = msb_bit % 8;
        int shift = (int)(msb_byte * 8 + (7 - msb_bit_in_byte)) - (int)(sig.length_bits - 1);
        if (shift < 0) shift = 0;
        uval = (word >> shift) & mask;
    }

    if (sig.is_signed) {
        // Sign extend
        const uint64_t sign_bit = uint64_t(1) << (sig.length_bits - 1);
        if (uval & sign_bit) {
            uval |= ~mask;   // extend sign through upper bits
        }
    }
    return static_cast<int64_t>(uval);
}
