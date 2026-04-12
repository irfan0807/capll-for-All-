# Section 10: ECU Power Mode State Machine

## Goal
Automate ECU power state transition validation for ignition/off/sleep/wakeup paths.

## Script
`python_automotive_automation_testing/scripts/10_power_mode_state_machine.py`

## What It Covers
- Nominal startup and shutdown transitions
- Invalid transition rejection
- Wakeup from sleep path validation

## Run
```bash
python3 python_automotive_automation_testing/scripts/10_power_mode_state_machine.py
```

## Extend for Real Projects
- Add wake sources (CAN, LIN, door, network).
- Validate power current in each state.
- Add fault-injection during crank/run transitions.
