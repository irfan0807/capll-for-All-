# Section 03: UDS Diagnostics Automation

## Goal
Automate service-level UDS testing with positive and negative response validation.

## Script
`python_automotive_automation_testing/scripts/03_uds_diagnostics_automation.py`

## What It Covers
- Session control (`0x10`)
- DID read (`0x22`)
- Security access seed/key (`0x27`)
- DID write (`0x2E`)
- Negative response handling (NRC checks)

## Run
```bash
python3 python_automotive_automation_testing/scripts/03_uds_diagnostics_automation.py
```

## Extend for Real Projects
- Replace mock ECU with UDS over CAN/DoIP stack.
- Add routine control (`0x31`) and DTC services (`0x19`).
- Integrate timing constraints (`P2`, `P2*`) and retries.
