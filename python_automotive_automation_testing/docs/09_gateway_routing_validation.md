# Section 09: Gateway Routing Validation

## Goal
Automate validation of gateway routing from in-vehicle bus frames to backbone/network packets.

## Script
`python_automotive_automation_testing/scripts/09_gateway_routing_validation.py`

## What It Covers
- Route table behavior
- Unmapped message drop logic
- End-to-end routing latency checks
- Payload integrity checks

## Run
```bash
python3 python_automotive_automation_testing/scripts/09_gateway_routing_validation.py
```

## Extend for Real Projects
- Add VLAN/QoS and SOME/IP signal checks.
- Validate load behavior with burst traffic.
- Add route failover and degradation tests.
