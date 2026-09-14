# ADAS AEB Validation Framework

A production-style Python + Pytest + python-can + cantools framework for
validating an Autonomous Emergency Braking (AEB) feature over CAN, built
end-to-end and runnable with **no hardware** (python-can's `virtual`
interface). Point `CanInterface` at `socketcan` / `vector` / `kvaser` /
`ixxat` / a dSPACE breakout instead, and every layer above it (API,
validation, tests) is unchanged.

## What it demonstrates

- Python injects sensor stimuli (TTC, object distance, relative speed,
  validity) as CAN frames encoded from a DBC.
- A simulated ECU (a genuinely separate CAN node, `AebEcuSimulator`) decodes
  them, runs a real decision cascade (IDLE → WARNING → PARTIAL_BRAKE →
  FULL_BRAKE, plus FAULT), and transmits `AEB_Status` feedback frames with
  realistic processing latency.
- A background listener/notifier thread filters, decodes (via `cantools`),
  and stores every signal with wall-clock + monotonic timestamps.
- Tests synchronize on the decoded signal store (condition-variable based
  blocking waits) instead of `sleep()`-and-hope, then validate state
  transitions, timing budgets, and PASS/FAIL outcomes.

## Architecture

```
dbc/aeb_system.dbc          AEB_SensorInput / AEB_Status / VehicleDynamics

src/
  can_comm/
    can_interface.py        python-can Bus wrapper (send + connect/disconnect)
    can_listener.py         Background Notifier -> filter -> DBC decode -> store
    signal_store.py         Thread-safe signal store + condition-variable waits
  dbc_layer/
    dbc_decoder.py           cantools wrapper: encode/decode by message name
  simulation/
    sensor_sim.py            Injects AEB_SensorInput (+ fault-injection helpers)
    vehicle_sim.py           Injects VehicleDynamics (host speed/yaw)
    ecu_sim.py                The simulated ECU: decision cascade + FAULT handling
  adas_api/
    aeb_api.py                Feature-level test API (what tests actually call)
  validation/
    state_machine.py          Legal AEB_State transition graph + violation checks
    timing_validator.py       Named timing requirements vs. measured latency
    assertions.py              PASS/FAIL assertion helpers with rich logging
  utils/
    logger.py                  Timestamped run log (reports/logs/)

tests/
  conftest.py                 Fixtures: isolated bus -> listener -> ECU -> API
  test_aeb_functional.py       Positive end-to-end cascade tests
  test_aeb_boundary.py         Parameterized TTC + speed-envelope boundary tests
  test_aeb_negative.py         Invalid/implausible input must NOT trigger braking
  test_aeb_fault_injection.py  Sensor dropout, plausibility faults, ECU offline,
                                fault recovery, full-sequence legality check
```

Each test gets its own uniquely-named virtual CAN channel (see `can_channel`
fixture) for full isolation, and its own ECU instance — no state leaks
between test cases, and the suite is safe to run under `pytest-xdist`.

## Setup

```bash
pip install -r requirements.txt
```

## Running

```bash
# Full suite (HTML + Allure results are generated automatically, see pytest.ini)
pytest

# One category
pytest -m functional
pytest -m boundary
pytest -m negative
pytest -m fault_injection

# A single test, verbose
pytest -v tests/test_aeb_fault_injection.py::test_sensor_dropout_triggers_timeout_fault
```

Reports land in:
- `reports/html/report.html` — self-contained pytest-html report
- `reports/allure-results/` — raw Allure results; render with
  `allure serve reports/allure-results` (or `allure generate` for a static
  site) if the Allure CLI is installed
- `reports/logs/aeb_validation_<timestamp>.log` — full timestamped CAN +
  assertion trace for the run, independent of pytest's own output

## Decision thresholds (illustrative)

| TTC              | State          |
|------------------|----------------|
| > 2500 ms        | IDLE           |
| ≤ 2500 ms        | WARNING        |
| ≤ 1500 ms        | PARTIAL_BRAKE  |
| ≤ 700 ms         | FULL_BRAKE     |

AEB is only active for host speed in **5–160 kph**; outside that envelope,
or with `ObjectValid = 0`, the ECU stays IDLE regardless of TTC. A stale
sensor input (> 500 ms without a fresh frame) or an injected plausibility
fault escalates to `FAULT` with a `FaultCode`. See
`src/simulation/ecu_sim.py::EcuThresholds` — in a real project these values
trace back to the requirements/functional-safety spec rather than being
hardcoded like this.

## Extending to real hardware / a real ECU

1. Swap `CanInterface(interface="virtual", ...)` for `interface="socketcan"`
   (Linux SocketCAN), `"vector"`, `"kvaser"`, `"ixxat"`, `"pcan"`, etc. —
   whatever python-can supports for your bench/dSPACE setup.
2. Delete/ignore `src/simulation/ecu_sim.py` — that module *is* the thing
   under test in a real setup; a physical ECU replaces it.
3. Everything above the CAN layer (`adas_api`, `validation`, `tests`) is
   unchanged, because it only ever talks to the DBC-decoded signal store and
   the feature API, never to raw CAN frames or a specific interface.
4. Update `dbc/aeb_system.dbc` to the vehicle's real DBC revision.
