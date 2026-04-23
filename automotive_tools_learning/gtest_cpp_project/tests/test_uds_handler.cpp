// ─────────────────────────────────────────────────────────────────────────────
//  UDS Handler Tests  –  Parameterized + negative tests
// ─────────────────────────────────────────────────────────────────────────────
#include <gtest/gtest.h>
#include "uds_handler.h"

// ─────────────────────────────────────────────────────────────
//  Parameterized test for all supported UDS service IDs
// ─────────────────────────────────────────────────────────────
struct UdsServiceParam {
    std::string              label;
    std::vector<uint8_t>     request;
    bool                     expect_positive;
    uint8_t                  expected_first_byte;   // first byte of response data
};

class UdsServiceTest : public ::testing::TestWithParam<UdsServiceParam> {
protected:
    UdsHandler handler_;
};

TEST_P(UdsServiceTest, ServiceRespondsCorrectly) {
    const auto& p    = GetParam();
    auto        resp = handler_.ProcessRequest(p.request);
    EXPECT_EQ(resp.positive, p.expect_positive)
        << "Service 0x" << std::hex << (int)p.request[0]
        << " positivity mismatch for test: " << p.label;
    if (p.expect_positive && !resp.data.empty()) {
        EXPECT_EQ(resp.data[0], p.expected_first_byte)
            << "Response SID byte mismatch for: " << p.label;
    }
}

INSTANTIATE_TEST_SUITE_P(
    AllSupportedServices,
    UdsServiceTest,
    ::testing::Values(
        // DiagnosticSessionControl – session 1
        UdsServiceParam{ "DSC_Default",        {0x10, 0x01}, true,  0x50 },
        // DiagnosticSessionControl – programming session
        UdsServiceParam{ "DSC_Programming",    {0x10, 0x02}, true,  0x50 },
        // DiagnosticSessionControl – extended session
        UdsServiceParam{ "DSC_Extended",       {0x10, 0x03}, true,  0x50 },
        // ECU Reset – hard reset
        UdsServiceParam{ "ECUReset_Hard",      {0x11, 0x01}, true,  0x51 },
        // ECU Reset – soft reset
        UdsServiceParam{ "ECUReset_Soft",      {0x11, 0x03}, true,  0x51 },
        // TesterPresent
        UdsServiceParam{ "TesterPresent",      {0x3E, 0x00}, true,  0x7E },
        // SecurityAccess – request seed
        UdsServiceParam{ "SA_RequestSeed",     {0x27, 0x01}, true,  0x67 },
        // SecurityAccess – send valid key
        UdsServiceParam{ "SA_SendValidKey",    {0x27, 0x02, 0xBE, 0xEF}, true, 0x67 }
    ),
    [](const ::testing::TestParamInfo<UdsServiceParam>& info) {
        return info.param.label;
    }
);

// ─────────────────────────────────────────────────────────────
//  Negative tests – NRC verification
// ─────────────────────────────────────────────────────────────

class UdsNegativeTest : public ::testing::Test {
protected:
    UdsHandler handler_;
};

TEST_F(UdsNegativeTest, EmptyRequestReturnsNRC_13) {
    auto resp = handler_.ProcessRequest({});
    EXPECT_FALSE(resp.positive);
    EXPECT_EQ(resp.nrc, 0x13);  // incorrectMessageLength
}

TEST_F(UdsNegativeTest, UnsupportedServiceReturnsNRC_11) {
    auto resp = handler_.ProcessRequest({ 0xBB });
    EXPECT_FALSE(resp.positive);
    EXPECT_EQ(resp.nrc, 0x11);  // serviceNotSupported
}

TEST_F(UdsNegativeTest, DSC_InvalidSubFunctionReturnNRC_12) {
    auto resp = handler_.ProcessRequest({ 0x10, 0xFF });  // sub-fn 0xFF invalid
    EXPECT_FALSE(resp.positive);
    EXPECT_EQ(resp.nrc, 0x12);  // subFunctionNotSupported
}

TEST_F(UdsNegativeTest, SecurityAccess_WrongKeyReturnsNRC_35) {
    // First request the seed
    handler_.ProcessRequest({ 0x27, 0x01 });
    // Send wrong key
    auto resp = handler_.ProcessRequest({ 0x27, 0x02, 0xDE, 0xAD });
    EXPECT_FALSE(resp.positive);
    EXPECT_EQ(resp.nrc, 0x35);  // invalidKey
}

TEST_F(UdsNegativeTest, WriteDataById_LockedSessionReturnsNRC_33) {
    // No security unlock → should deny write
    auto resp = handler_.ProcessRequest({ 0x2E, 0x01, 0x00, 0xAA });
    EXPECT_FALSE(resp.positive);
    EXPECT_EQ(resp.nrc, 0x33);  // securityAccessDenied
}

TEST_F(UdsNegativeTest, WriteDataById_AfterSecurityUnlockSucceeds) {
    // Unlock security first
    handler_.ProcessRequest({ 0x27, 0x01 });            // request seed
    handler_.ProcessRequest({ 0x27, 0x02, 0xBE, 0xEF }); // send valid key
    auto resp = handler_.ProcessRequest({ 0x2E, 0x01, 0x00, 0xAA });
    EXPECT_TRUE(resp.positive);
}

TEST_F(UdsNegativeTest, ReadDataById_VIN_Succeeds) {
    auto resp = handler_.ProcessRequest({ 0x22, 0xF1, 0x90 });
    EXPECT_TRUE(resp.positive);
    ASSERT_GE(resp.data.size(), 3u);
    EXPECT_EQ(resp.data[0], 0x62);
    EXPECT_EQ(resp.data[1], 0xF1);
    EXPECT_EQ(resp.data[2], 0x90);
}

TEST_F(UdsNegativeTest, ReadDataById_UnknownDID_ReturnsNRC_31) {
    auto resp = handler_.ProcessRequest({ 0x22, 0xAB, 0xCD });
    EXPECT_FALSE(resp.positive);
    EXPECT_EQ(resp.nrc, 0x31);  // requestOutOfRange
}
