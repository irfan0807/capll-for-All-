# Test Methodology

## Principles

1. **Requirement traceability** — every `TestCase` carries a `requirement` field that maps directly to a functional requirement ID.
2. **Structured steps** — all test actions are wrapped in `self.step()` context managers so failures are pinpointed at the step level, not just the test level.
3. **Independent teardown** — `teardown()` always runs regardless of whether the test passed or failed, so the hardware is always left in a known state.
4. **Backend agnosticism** — the same test code runs against real hardware, virtual CAN (`vcan0`), and the loopback stub, selected by configuration rather than `if/else` in test code.
5. **Zero-assert-on-green** — steps that pass do not clutter logs; only failures produce diagnostics output.

---

## Naming convention

| Field | Convention | Example |
|-------|-----------|---------|
| `test_id` | `TC-<FEATURE>-<SEQ>` | `TC-BSD-001` |
| `feature`  | Feature abbreviation | `BSD`, `AEB`, `ACC` |
| `requirement` | Requirement system ID | `REQ-BSD-001` |
| `priority` | P1 (blocking) → P3 (informational) | `P1` |
| `tags` | snake_case, no spaces | `["smoke", "bsd", "regression"]` |

---

## Test lifecycle

```
run()
 │
 ├── setup()
 │     ├── Open CAN/UDS adapters
 │     ├── Enter required UDS session
 │     ├── Clear DTCs
 │     └── Set ECU to known precondition (speed, gear, mode)
 │
 ├── test_body()
 │     ├── step(1, "Inject stimulus")
 │     │     └── Transmit CAN frame / write DID / trigger I/O
 │     ├── step(2, "Verify response within timing requirement")
 │     │     └── Poll CAN bus or read DID; call assert_*
 │     └── step(3, "Verify no side-effects")
 │           └── assert_dtcs_clear / assert_equal signal values
 │
 └── teardown()
       ├── Send "clear-stimulus" frame
       ├── Return to default UDS session
       └── Close adapters
```

---

## Assertion selection guide

| Scenario | Assertion |
|----------|-----------|
| Boolean condition | `assert_true(condition)` |
| Exact value | `assert_equal(actual, expected)` |
| Numeric range | `assert_in_range(v, lo, hi)` |
| Tolerance/accuracy | `assert_within(actual, expected, ±tol)` |
| Response time | `assert_latency(measured_ms, max_ms)` |
| DTC state | `assert_dtcs_clear(dtcs)` |
| Negative (must not happen) | `assert_false(condition)` |

---

## Step design guidelines

- **One action per step** — each step should do one thing; makes failures precise.
- **Number steps sequentially** — `step(1, ...)`, `step(2, ...)`, …
- **Include timing in step descriptions** — e.g. `"BSD warns within 300 ms"`.
- **Steps after a FAIL still run** — the `_StepContext` suppresses `AssertionError`
  so subsequent steps are always executed (useful for collecting more evidence).
  The final test status is still FAIL.

---

## Timing verification

For latency requirements (e.g. "BSD warning within 300 ms"):

```python
import time

def wait_for_warning(can, timeout_ms=300):
    t0 = time.monotonic()
    while (time.monotonic() - t0) * 1000 < timeout_ms:
        frame = can.receive(timeout_ms=10)
        if frame and frame.id == BSD_WARNING_ID and frame.data[0] & 0x01:
            return True
    return False

# In test_body:
t_start = time.monotonic()
activated = wait_for_warning(self.can, timeout_ms=300)
latency = (time.monotonic() - t_start) * 1000

self.assert_true(activated, f"Warning not raised in 300 ms")
self.assert_latency(latency, 300.0, "stimulus→warning")
```

---

## Security access (UDS 0x27)

```python
def seed_to_key(seed: bytes) -> bytes:
    # Replace with your OEM-specific algorithm
    return bytes(b ^ 0xFF for b in seed)

resp = self.uds.security_access(level=0x01, seed_to_key_fn=seed_to_key)
self.assert_true(resp.positive, f"Security access failed: NRC {resp.nrc}")
```

---

## Running a release gate

```python
from hw_test_framework.framework.test_runner import TestRunner, RunConfig
from hw_test_framework.observability import TestMetricsCollector, DiagnosticsCollector
from hw_test_framework.reporting import write_junit, write_html

metrics  = TestMetricsCollector()
diag     = DiagnosticsCollector(can=my_can, uds=my_uds)
runner   = TestRunner(RunConfig(
    parallel=False,
    retry_on_fail=True,
    max_retries=1,
    stop_on_first_fail=False,
    verbose=True,
))
runner.add_hook(metrics.on_result)
runner.add_hook(diag.on_result)

suite = runner.run_suite("Release Gate", [
    *BSD_TESTS,
    *AEB_TESTS,
    *ACC_TESTS,
])
metrics.finalise()

write_junit([suite], "reports/release_gate.xml")
write_html([suite],  "reports/release_gate.html", title="Release Gate v2.5.0")
diag.save_all("reports/diagnostics.jsonl")

if not suite.all_passed:
    raise SystemExit(1)
```

---

## Test pyramid

```
        ▲
       / \       System tests (--hw flag)
      /   \      Real hardware, full feature validation
     /─────\
    /       \    Integration tests (vcan0)
   /         \   ISO-TP sessions, DTC management
  /───────────\
 /             \ Unit tests (loopback stub)
/               \ Framework core, adapters, filters
─────────────────
```

| Layer | Hardware needed | Run time | Count |
|-------|----------------|----------|-------|
| Unit  | None (loopback) | < 5 s | ~50 |
| Integration | vcan0 | < 60 s | ~20 |
| System | Real ECU | 5–30 min | ~30 |
