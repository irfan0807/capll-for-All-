// ─────────────────────────────────────────────────────────────────────────────
//  BMS Controller Tests  –  STAR Cases 1–3 from the GTest Learning Guide
// ─────────────────────────────────────────────────────────────────────────────
#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include "bms_controller.h"
#include "mocks/mock_bms.h"

using ::testing::Return;
using ::testing::ReturnRef;
using ::testing::NiceMock;
using ::testing::InSequence;
using ::testing::_;

// ─────────────────────────────────────────────────────────────
//  Fixture: provides mock sensor and comms to every test
// ─────────────────────────────────────────────────────────────
class BmsControllerTest : public ::testing::Test {
protected:
    void SetUp() override {
        // By default: nominal values (no fault)
        ON_CALL(mock_sensor_, GetCellVoltage()).WillByDefault(Return(3.8f));
        ON_CALL(mock_sensor_, GetTemperature()).WillByDefault(Return(25.0f));
        ON_CALL(mock_sensor_, GetCurrentAmps()).WillByDefault(Return(10.0f));
        ON_CALL(mock_sensor_, IsFaultActive()).WillByDefault(Return(false));
        controller_ = std::make_unique<BmsController>(mock_sensor_, mock_comms_);
    }

    NiceMock<MockBmsSensor> mock_sensor_;
    NiceMock<MockBmsComms>  mock_comms_;
    std::unique_ptr<BmsController> controller_;
};

// ─────────────────────────────────────────────────────────────
//  STAR Case 1 – BMS State Machine transitions
// ─────────────────────────────────────────────────────────────

// Normal charging state
TEST_F(BmsControllerTest, StateIsChargingWhenVoltageIsNominal) {
    EXPECT_CALL(mock_sensor_, GetCellVoltage()).WillRepeatedly(Return(3.8f));
    EXPECT_CALL(mock_sensor_, GetTemperature()).WillRepeatedly(Return(25.0f));
    EXPECT_CALL(mock_sensor_, IsFaultActive()).WillRepeatedly(Return(false));
    controller_->Update();
    EXPECT_EQ(controller_->GetState(), BmsState::CHARGING);
}

// Over-temperature → FAULT
TEST_F(BmsControllerTest, TransitionToFaultOnOvertemperature) {
    EXPECT_CALL(mock_sensor_, GetTemperature())
        .WillRepeatedly(Return(65.0f));   // above 60°C threshold
    EXPECT_CALL(mock_sensor_, IsFaultActive()).WillRepeatedly(Return(false));
    EXPECT_CALL(mock_sensor_, GetCellVoltage()).WillRepeatedly(Return(3.8f));
    EXPECT_CALL(mock_comms_, SendFaultMessage(0x01)).Times(1);
    controller_->Update();
    EXPECT_EQ(controller_->GetState(), BmsState::FAULT);
}

// Hardware fault flag → FAULT
TEST_F(BmsControllerTest, TransitionToFaultWhenHardwareFaultActive) {
    EXPECT_CALL(mock_sensor_, IsFaultActive()).WillRepeatedly(Return(true));
    EXPECT_CALL(mock_sensor_, GetCellVoltage()).WillRepeatedly(Return(3.8f));
    EXPECT_CALL(mock_sensor_, GetTemperature()).WillRepeatedly(Return(25.0f));
    EXPECT_CALL(mock_comms_, SendFaultMessage(0x01)).Times(1);
    controller_->Update();
    EXPECT_EQ(controller_->GetState(), BmsState::FAULT);
}

// Voltage exactly at cutoff → IDLE
TEST_F(BmsControllerTest, StateIsIdleAtChargeCutoffVoltage) {
    EXPECT_CALL(mock_sensor_, GetCellVoltage())
        .WillRepeatedly(Return(BmsController::CHARGE_CUTOFF_VOLTAGE_V));
    EXPECT_CALL(mock_sensor_, GetTemperature()).WillRepeatedly(Return(25.0f));
    EXPECT_CALL(mock_sensor_, IsFaultActive()).WillRepeatedly(Return(false));
    controller_->Update();
    EXPECT_EQ(controller_->GetState(), BmsState::IDLE);
}

// Under-voltage → SHUTDOWN
TEST_F(BmsControllerTest, TransitionToShutdownOnUndervoltage) {
    EXPECT_CALL(mock_sensor_, GetCellVoltage())
        .WillRepeatedly(Return(BmsController::MIN_VOLTAGE_V - 0.1f));
    EXPECT_CALL(mock_sensor_, GetTemperature()).WillRepeatedly(Return(25.0f));
    EXPECT_CALL(mock_sensor_, IsFaultActive()).WillRepeatedly(Return(false));
    controller_->Update();
    EXPECT_EQ(controller_->GetState(), BmsState::SHUTDOWN);
}

// State message sent on every update
TEST_F(BmsControllerTest, StateMessageSentOnNominalUpdate) {
    EXPECT_CALL(mock_sensor_, GetCellVoltage()).WillRepeatedly(Return(3.8f));
    EXPECT_CALL(mock_sensor_, GetTemperature()).WillRepeatedly(Return(25.0f));
    EXPECT_CALL(mock_sensor_, IsFaultActive()).WillRepeatedly(Return(false));
    // Must send state message (CHARGING = 1)
    EXPECT_CALL(mock_comms_, SendStateMessage(static_cast<uint8_t>(BmsState::CHARGING))).Times(1);
    controller_->Update();
}

// ─────────────────────────────────────────────────────────────
//  STAR Case 2 – Charging state termination
// ─────────────────────────────────────────────────────────────

TEST_F(BmsControllerTest, ChargeTerminationAtMaxVoltage) {
    EXPECT_CALL(mock_sensor_, GetCellVoltage())
        .WillRepeatedly(Return(BmsController::CHARGE_CUTOFF_VOLTAGE_V));
    EXPECT_EQ(controller_->GetChargingState(), ChargingState::TERMINATE);
}

TEST_F(BmsControllerTest, ChargingStateWhenVoltageIsBelowCutoff) {
    EXPECT_CALL(mock_sensor_, GetCellVoltage()).WillRepeatedly(Return(3.5f));
    EXPECT_CALL(mock_sensor_, GetTemperature()).WillRepeatedly(Return(25.0f));
    EXPECT_CALL(mock_sensor_, IsFaultActive()).WillRepeatedly(Return(false));
    controller_->Update();  // sets internal state to CHARGING
    EXPECT_EQ(controller_->GetChargingState(), ChargingState::CHARGING);
}

// ─────────────────────────────────────────────────────────────
//  STAR Case 3 – Multiple calls (WillOnce sequence)
// ─────────────────────────────────────────────────────────────

TEST_F(BmsControllerTest, SequentialVoltageReadingsDriveCorrectStates) {
    // Simulate 3 consecutive updates: Charging → Charging → IDLE
    EXPECT_CALL(mock_sensor_, GetCellVoltage())
        .WillOnce(Return(3.5f))
        .WillOnce(Return(3.9f))
        .WillOnce(Return(4.2f));
    EXPECT_CALL(mock_sensor_, GetTemperature()).WillRepeatedly(Return(25.0f));
    EXPECT_CALL(mock_sensor_, IsFaultActive()).WillRepeatedly(Return(false));

    controller_->Update();
    EXPECT_EQ(controller_->GetState(), BmsState::CHARGING);

    controller_->Update();
    EXPECT_EQ(controller_->GetState(), BmsState::CHARGING);

    controller_->Update();
    EXPECT_EQ(controller_->GetState(), BmsState::IDLE);
}
