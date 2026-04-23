// ─────────────────────────────────────────────────────────────────────────────
//  DoIP Decoder Tests  –  STAR Case 16: Security/robustness / fuzz-style tests
// ─────────────────────────────────────────────────────────────────────────────
#include <gtest/gtest.h>
#include "doip_decoder.h"
#include <vector>
#include <cstring>

// ─── Build a valid DoIP frame helper ─────────────────────────

static std::vector<uint8_t> BuildDoIPFrame(uint8_t payload_type,
                                            const std::vector<uint8_t>& payload) {
    std::vector<uint8_t> frame;
    frame.push_back(DoIPDecoder::DOIP_VERSION);           // version
    frame.push_back(DoIPDecoder::DOIP_INVERSE_VERSION);   // ~version
    frame.push_back(payload_type);                        // payload type (high)
    frame.push_back(0x00);                                // payload type (low, unused)
    uint32_t len = static_cast<uint32_t>(payload.size());
    frame.push_back((len >> 24) & 0xFF);
    frame.push_back((len >> 16) & 0xFF);
    frame.push_back((len >>  8) & 0xFF);
    frame.push_back( len        & 0xFF);
    frame.insert(frame.end(), payload.begin(), payload.end());
    return frame;
}

// ─── Valid frame tests ────────────────────────────────────────

TEST(DoIPDecoderTest, ValidFrameDecodesCorrectly) {
    auto frame = BuildDoIPFrame(0x05, { 0xAA, 0xBB, 0xCC });
    DoIPDecoder decoder;
    auto result = decoder.Decode(frame.data(), frame.size());

    EXPECT_TRUE(result.valid);
    EXPECT_EQ(result.payload_type, 0x05);
    ASSERT_EQ(result.payload.size(), 3u);
    EXPECT_EQ(result.payload[0], 0xAA);
    EXPECT_EQ(result.payload[1], 0xBB);
    EXPECT_EQ(result.payload[2], 0xCC);
}

TEST(DoIPDecoderTest, ValidFrameWithEmptyPayload) {
    auto frame = BuildDoIPFrame(0x01, {});
    DoIPDecoder decoder;
    auto result = decoder.Decode(frame.data(), frame.size());

    EXPECT_TRUE(result.valid);
    EXPECT_EQ(result.payload.size(), 0u);
}

// ─── Malformed frame tests (must not crash) ───────────────────

TEST(DoIPDecoderTest, NullPointerDoesNotCrash) {
    DoIPDecoder decoder;
    auto result = decoder.Decode(nullptr, 100);
    EXPECT_FALSE(result.valid);
}

TEST(DoIPDecoderTest, ZeroSizeDoesNotCrash) {
    uint8_t dummy[16] = {};
    DoIPDecoder decoder;
    auto result = decoder.Decode(dummy, 0);
    EXPECT_FALSE(result.valid);
}

TEST(DoIPDecoderTest, TooShortForHeader) {
    uint8_t data[4] = { 0x02, 0xFD, 0x00, 0x00 };  // only 4 bytes, need 8
    DoIPDecoder decoder;
    auto result = decoder.Decode(data, 4);
    EXPECT_FALSE(result.valid);
}

TEST(DoIPDecoderTest, WrongVersionRejected) {
    auto frame = BuildDoIPFrame(0x01, { 0x00 });
    frame[0] = 0x01;   // corrupt version byte
    DoIPDecoder decoder;
    auto result = decoder.Decode(frame.data(), frame.size());
    EXPECT_FALSE(result.valid);
}

TEST(DoIPDecoderTest, MalformedPayloadLength_TooLarge_DoesNotOverread) {
    // Construct a frame claiming payload_length = 0xFFFFFFFF but actual data is tiny
    uint8_t frame[12] = {
        DoIPDecoder::DOIP_VERSION,
        DoIPDecoder::DOIP_INVERSE_VERSION,
        0x01, 0x00,          // payload_type
        0xFF, 0xFF, 0xFF, 0xFF,  // payload_length = 4GB (!)
        0xAA, 0xBB, 0xCC, 0xDD  // only 4 actual bytes of "payload"
    };
    DoIPDecoder decoder;
    // Must not crash, must not access memory beyond frame[11]
    auto result = decoder.Decode(frame, sizeof(frame));
    EXPECT_FALSE(result.valid);  // length lies → reject
}

// ─── Fuzz-style: random-ish byte patterns must not crash ─────

TEST(DoIPDecoderFuzzTest, AllZeroesDoesNotCrash) {
    uint8_t data[64] = {};
    DoIPDecoder decoder;
    EXPECT_NO_FATAL_FAILURE(decoder.Decode(data, sizeof(data)));
}

TEST(DoIPDecoderFuzzTest, AllFFsDoesNotCrash) {
    uint8_t data[64];
    std::memset(data, 0xFF, sizeof(data));
    DoIPDecoder decoder;
    EXPECT_NO_FATAL_FAILURE(decoder.Decode(data, sizeof(data)));
}

TEST(DoIPDecoderFuzzTest, AlternatingPatternDoesNotCrash) {
    uint8_t data[32];
    for (size_t i = 0; i < sizeof(data); ++i)
        data[i] = (i % 2 == 0) ? 0xAA : 0x55;
    DoIPDecoder decoder;
    EXPECT_NO_FATAL_FAILURE(decoder.Decode(data, sizeof(data)));
}
