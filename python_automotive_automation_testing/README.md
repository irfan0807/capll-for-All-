# Python Automotive Automation Testing Examples

This package provides section-wise Python script examples for key automotive automation testing topics.

## Structure

- `scripts/`: Runnable Python examples (simulation-first, no hardware dependency)
- `docs/`: One separate document per section with objective, workflow, and run steps

## Sections Covered

1. CAN Signal Validation (`scripts/01_can_signal_validation.py`)
2. LIN Schedule Validation (`scripts/02_lin_schedule_validation.py`)
3. UDS Diagnostics Automation (`scripts/03_uds_diagnostics_automation.py`)
4. OBD-II PID Monitoring (`scripts/04_obd2_pid_monitoring.py`)
5. DTC Lifecycle Testing (`scripts/05_dtc_lifecycle_testing.py`)
6. HIL Test Orchestration (`scripts/06_hil_test_orchestration.py`)
7. ADAS Scenario Validation (`scripts/07_adas_scenario_validation.py`)
8. OTA Update Regression (`scripts/08_ota_update_regression.py`)
9. Gateway Routing Validation (`scripts/09_gateway_routing_validation.py`)
10. ECU Power Mode State Machine (`scripts/10_power_mode_state_machine.py`)
11. Performance, Stress, and Soak Testing (`scripts/11_performance_stress_soak.py`)
12. CI Reporting (JUnit + Markdown) (`scripts/12_ci_reporting_example.py`)

## Quick Start

```bash
cd python_automotive_automation_testing
python3 scripts/01_can_signal_validation.py
python3 scripts/03_uds_diagnostics_automation.py
python3 scripts/12_ci_reporting_example.py
```

## Notes

- These examples are intentionally hardware-agnostic and use simulation/mock objects.
- Replace mock interfaces with real APIs (e.g., Vector, CANoe, python-can, DoIP stacks, lab instruments) in production.
