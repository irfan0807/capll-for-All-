#include "doip_decoder.h"
#include <cstring>

DoIPResult DoIPDecoder::Decode(const uint8_t* data, size_t size) {
    DoIPResult result{ false, 0, {} };

    // Must have at least a complete header
    if (!data || size < HEADER_SIZE) {
        return result;
    }

    // Version check
    if (data[0] != DOIP_VERSION || data[1] != DOIP_INVERSE_VERSION) {
        return result;
    }

    const uint8_t  payload_type   = data[2];
    // Payload length stored big-endian in bytes [4..7]
    const uint32_t payload_length = (static_cast<uint32_t>(data[4]) << 24) |
                                    (static_cast<uint32_t>(data[5]) << 16) |
                                    (static_cast<uint32_t>(data[6]) <<  8) |
                                     static_cast<uint32_t>(data[7]);

    // Guard: payload_length must not exceed available data
    if (payload_length > (size - HEADER_SIZE)) {
        return result;   // malformed — would be a buffer over-read otherwise
    }

    result.valid        = true;
    result.payload_type = payload_type;
    result.payload.assign(data + HEADER_SIZE, data + HEADER_SIZE + payload_length);
    return result;
}
