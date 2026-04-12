# Section 01: CAN Signal Validation

## Goal
Automate validation of CAN message timing and decoded signal range checks.

## Script
`python_automotive_automation_testing/scripts/01_can_signal_validation.py`

## What It Covers
- Message cycle-time verification
- Signal decoding (speed, RPM)
- Physical-range plausibility checks
- PASS/FAIL report generation

## Run
```bash
python3 python_automotive_automation_testing/scripts/01_can_signal_validation.py
```

## Extend for Real Projects
- Replace synthetic frames with data from `python-can` or CANoe logs.
- Add database decoding from DBC files.
- Add timeout/error-frame monitoring.
