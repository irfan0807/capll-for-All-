#include "bms_controller.h"

BmsController::BmsController(IBmsSensor& sensor, IBmsComms& comms)
    : sensor_(sensor), comms_(comms) {}

void BmsController::Update() {
    const float voltage = sensor_.GetCellVoltage();
    const float temp    = sensor_.GetTemperature();
    const bool  fault   = sensor_.IsFaultActive();

    if (fault || temp > OVER_TEMP_THRESHOLD_C) {
        state_ = BmsState::FAULT;
        comms_.SendFaultMessage(0x01);
        return;
    }
    if (voltage < MIN_VOLTAGE_V) {
        state_ = BmsState::SHUTDOWN;
        comms_.SendStateMessage(static_cast<uint8_t>(BmsState::SHUTDOWN));
        return;
    }
    if (voltage >= CHARGE_CUTOFF_VOLTAGE_V) {
        state_ = BmsState::IDLE;
    } else {
        state_ = BmsState::CHARGING;
    }
    comms_.SendStateMessage(static_cast<uint8_t>(state_));
}

ChargingState BmsController::GetChargingState() const {
    const float voltage = sensor_.GetCellVoltage();
    if (voltage >= CHARGE_CUTOFF_VOLTAGE_V)
        return ChargingState::TERMINATE;
    if (state_ == BmsState::CHARGING)
        return ChargingState::CHARGING;
    return ChargingState::STANDBY;
}
