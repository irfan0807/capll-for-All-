// ─────────────────────────────────────────────────────────────────────────────
//  CAN Packer Tests  –  Parameterized pack/unpack round-trip tests
// ─────────────────────────────────────────────────────────────────────────────
#include <gtest/gtest.h>
#include "can_packer.h"
#include <cstring>

struct CanPackTestCase {
    std::string  label;
    CanSignalDef sig;
    int64_t      value;
};

class CanPackerRoundTripTest : public ::testing::TestWithParam<CanPackTestCase> {};

TEST_P(CanPackerRoundTripTest, PackThenUnpackRecoveryIdentical) {
    const auto& p = GetParam();
    uint8_t frame[8] = {};
    CanPacker::Pack(frame, p.sig, p.value);
    const int64_t recovered = CanPacker::Unpack(frame, p.sig);
    EXPECT_EQ(recovered, p.value)
        << "Round-trip failed for signal: " << p.label
        << "  packed value=" << p.value << "  recovered=" << recovered;
}

INSTANTIATE_TEST_SUITE_P(
    SignalVariety,
    CanPackerRoundTripTest,
    ::testing::Values(
        // 8-bit unsigned, Intel, byte-aligned
        CanPackTestCase{ "u8_intel_aligned",   {0, 8, true,  false}, 0xAB     },
        // 16-bit unsigned, Intel
        CanPackTestCase{ "u16_intel",          {0,16, true,  false}, 0x1234   },
        // 1-bit signal (flag)
        CanPackTestCase{ "u1_flag_bit3",       {3, 1, true,  false}, 1        },
        // 12-bit unsigned, Intel
        CanPackTestCase{ "u12_intel",          {4,12, true,  false}, 0xFFF    },
        // 8-bit signed, positive
        CanPackTestCase{ "s8_intel_positive",  {8, 8, true,  true},  120      },
        // 8-bit signed, negative
        CanPackTestCase{ "s8_intel_negative",  {8, 8, true,  true}, -50       },
        // 32-bit unsigned, Intel
        CanPackTestCase{ "u32_intel",          {0,32, true,  false}, 0xDEADBEEF },
        // Zero value
        CanPackTestCase{ "zero_value",         {0, 8, true,  false}, 0        },
        // Max 8-bit value
        CanPackTestCase{ "u8_max",             {0, 8, true,  false}, 255      }
    ),
    [](const ::testing::TestParamInfo<CanPackTestCase>& info) {
        return info.param.label;
    }
);

// ─────────────────────────────────────────────────────────────
//  Frame isolation: packing one signal must not corrupt adjacent bits
// ─────────────────────────────────────────────────────────────
TEST(CanPackerIsolationTest, PackingDoesNotCorruptAdjacentBits) {
    uint8_t frame[8] = { 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF };
    CanSignalDef sig{ 8, 8, true, false };  // byte 1, 8 bits, Intel
    CanPacker::Pack(frame, sig, 0x00);
    EXPECT_EQ(frame[0], 0xFF);  // byte 0 must be untouched
    EXPECT_EQ(frame[1], 0x00);  // byte 1 written
    EXPECT_EQ(frame[2], 0xFF);  // byte 2 must be untouched
}

TEST(CanPackerIsolationTest, UnpackFromPreloadedFrame) {
    uint8_t frame[8] = { 0x00, 0x42, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
    CanSignalDef sig{ 8, 8, true, false };  // byte 1
    EXPECT_EQ(CanPacker::Unpack(frame, sig), 0x42);
}
