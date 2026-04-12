# Section 02: LIN Schedule Validation

## Goal
Validate LIN schedule adherence and frame-level jitter behavior.

## Script
`python_automotive_automation_testing/scripts/02_lin_schedule_validation.py`

## What It Covers
- Configured schedule table vs measured timestamps
- Frame presence checks
- Period and jitter tolerance checks

## Run
```bash
python3 python_automotive_automation_testing/scripts/02_lin_schedule_validation.py
```

## Extend for Real Projects
- Connect to LIN analyzer captures.
- Validate checksum/parity per LIN frame.
- Add slave response timeout and wakeup tests.
