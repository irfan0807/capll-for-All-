#pragma once
#include <gmock/gmock.h>
#include "bms_controller.h"

class MockBmsSensor : public IBmsSensor {
public:
    MOCK_METHOD(float, GetCellVoltage,  (), (const, override));
    MOCK_METHOD(float, GetTemperature,  (), (const, override));
    MOCK_METHOD(float, GetCurrentAmps,  (), (const, override));
    MOCK_METHOD(bool,  IsFaultActive,   (), (const, override));
};

class MockBmsComms : public IBmsComms {
public:
    MOCK_METHOD(void, SendStateMessage, (uint8_t state_id),   (override));
    MOCK_METHOD(void, SendFaultMessage, (uint8_t fault_code), (override));
};
