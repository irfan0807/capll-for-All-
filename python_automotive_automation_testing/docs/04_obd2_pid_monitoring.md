# Section 04: OBD-II PID Monitoring

## Goal
Automate OBD-II polling and value plausibility checks for emissions/powertrain data.

## Script
`python_automotive_automation_testing/scripts/04_obd2_pid_monitoring.py`

## What It Covers
- Mode 01 PID polling
- RPM/speed/coolant/throttle decoding
- Parameter threshold checks
- Cross-signal plausibility checks

## Run
```bash
python3 python_automotive_automation_testing/scripts/04_obd2_pid_monitoring.py
```

## Extend for Real Projects
- Use ELM327 or OEM diagnostics adapter.
- Add long-running trend analysis and freeze-frame capture.
- Add test hooks for MIL lamp and readiness monitors.
