#pragma once
#include <cstdint>

// ─────────────────────────────────────────────────────────────
//  IBmsSensor  –  pure interface (depended on by BmsController)
// ─────────────────────────────────────────────────────────────
class IBmsSensor {
public:
    virtual ~IBmsSensor() = default;
    virtual float   GetCellVoltage()    const = 0;
    virtual float   GetTemperature()    const = 0;
    virtual float   GetCurrentAmps()    const = 0;
    virtual bool    IsFaultActive()     const = 0;
};

// ─────────────────────────────────────────────────────────────
//  IBmsComms  –  CAN reporting interface
// ─────────────────────────────────────────────────────────────
class IBmsComms {
public:
    virtual ~IBmsComms() = default;
    virtual void SendStateMessage(uint8_t state_id) = 0;
    virtual void SendFaultMessage(uint8_t fault_code) = 0;
};

// ─────────────────────────────────────────────────────────────
//  BmsState  –  state machine states
// ─────────────────────────────────────────────────────────────
enum class BmsState : uint8_t {
    IDLE       = 0,
    CHARGING   = 1,
    BALANCING  = 2,
    FAULT      = 3,
    SHUTDOWN   = 4
};

enum class ChargingState : uint8_t {
    CHARGING   = 0,
    TERMINATE  = 1,
    STANDBY    = 2
};

// ─────────────────────────────────────────────────────────────
//  BmsController
// ─────────────────────────────────────────────────────────────
class BmsController {
public:
    static constexpr float OVER_TEMP_THRESHOLD_C   = 60.0f;
    static constexpr float CHARGE_CUTOFF_VOLTAGE_V = 4.2f;
    static constexpr float MIN_VOLTAGE_V           = 3.0f;

    explicit BmsController(IBmsSensor& sensor, IBmsComms& comms);

    void         Update();
    BmsState     GetState()          const { return state_; }
    ChargingState GetChargingState() const;

private:
    IBmsSensor&  sensor_;
    IBmsComms&   comms_;
    BmsState     state_{ BmsState::IDLE };
};
