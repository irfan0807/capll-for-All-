# Section 11: Performance, Stress, and Soak Testing

## Goal
Automate long-run network performance validation using latency/drop KPIs.

## Script
`python_automotive_automation_testing/scripts/11_performance_stress_soak.py`

## What It Covers
- Synthetic high-volume traffic simulation
- Drop-rate computation
- P95/P99/max latency analysis
- Jitter and mean-latency thresholds

## Run
```bash
python3 python_automotive_automation_testing/scripts/11_performance_stress_soak.py
```

## Extend for Real Projects
- Run against real captures from endurance benches.
- Add per-channel/channel-load distributions.
- Trend KPI drift over nightly CI runs.
