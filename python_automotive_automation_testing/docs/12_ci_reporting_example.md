# Section 12: CI Reporting Example

## Goal
Automate generation of CI-consumable test reports from Python test execution.

## Script
`python_automotive_automation_testing/scripts/12_ci_reporting_example.py`

## What It Covers
- Execution wrapper for test cases
- JUnit XML report generation
- Markdown summary report generation
- Console PASS/FAIL summary

## Run
```bash
python3 python_automotive_automation_testing/scripts/12_ci_reporting_example.py
```

## Generated Artifacts
- `python_automotive_automation_testing/reports/junit_automotive.xml`
- `python_automotive_automation_testing/reports/summary.md`

## Extend for Real Projects
- Replace lambda tests with real test calls.
- Integrate with `pytest` and CI pipelines.
- Attach CAN logs, screenshots, and waveform artifacts.
