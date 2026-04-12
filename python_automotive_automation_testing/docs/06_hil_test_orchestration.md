# Section 06: HIL Test Orchestration

## Goal
Automate hardware-in-the-loop startup checks using instrument-control style workflow.

## Script
`python_automotive_automation_testing/scripts/06_hil_test_orchestration.py`

## What It Covers
- Power supply setup and control
- Inrush current threshold check
- Boot-time check
- Heartbeat timing validation

## Run
```bash
python3 python_automotive_automation_testing/scripts/06_hil_test_orchestration.py
```

## Extend for Real Projects
- Replace mocks with SCPI instrument libraries.
- Add relay/IO control for ignition and load simulation.
- Capture waveforms and attach artifacts to reports.
