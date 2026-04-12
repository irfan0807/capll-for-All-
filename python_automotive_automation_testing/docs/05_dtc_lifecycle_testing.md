# Section 05: DTC Lifecycle Testing

## Goal
Automate validation of DTC state transitions from pending to confirmed and clear/heal behavior.

## Script
`python_automotive_automation_testing/scripts/05_dtc_lifecycle_testing.py`

## What It Covers
- Fault detection counting
- Pending and confirmed bit transitions
- Healing/pass-cycle behavior
- Manual clear workflow

## Run
```bash
python3 python_automotive_automation_testing/scripts/05_dtc_lifecycle_testing.py
```

## Extend for Real Projects
- Map status bits to ISO 14229/OBD requirements.
- Add ignition-cycle simulation and freeze-frame checks.
- Validate DTC persistence across ECU resets.
