# 04 — Pytest Advanced for Device Testing

> **Topic**: Fixtures (scopes, factories, yield), parametrize, markers, plugins, coverage, REST API testing  
> **Role relevance**: Primary Python test framework alongside Robot Framework  
> **Outcome**: Write professional pytest suites for device testing, integration testing, and REST API validation

---

## 1. Pytest Architecture Overview

```
pytest execution flow:
──────────────────────────────────────────────────────────────────────────
Collection:   pytest discovers test_*.py files, Test* classes, test_* functions
              Applies markers, fixtures, and parametrize decorators

Setup:        Fixtures with yield are set up in dependency order
              session → package → module → class → function scope

Execution:    Runs each test, capturing stdout/stderr/logs
              Records pass/fail/skip/error per test item

Teardown:     Yields resume; fixtures torn down in reverse order
              Even if test fails (teardown always runs)

Reporting:    Console output, JUnit XML, HTML report (pytest-html)
──────────────────────────────────────────────────────────────────────────
```

---

## 2. Fixtures — The Core of pytest

### Fixture Scopes
```
Fixture scope determines setup/teardown frequency:
──────────────────────────────────────────────────────────────────────────
scope="session"    Once per entire test run
                   Use for: BLE adapter init, SSH connections to servers

scope="package"    Once per test package (directory)
                   Use for: Loading a test data set

scope="module"     Once per test file
                   Use for: Opening serial port (tests in same file share it)

scope="class"      Once per Test class
                   Use for: Pairing BLE device (all class tests share pair)

scope="function"   Default — once per test function
                   Use for: Resetting device state, clearing buffers
──────────────────────────────────────────────────────────────────────────
```

### conftest.py — Full Device Test Setup
```python
"""
conftest.py — Complete fixtures for power tool device testing.
Place in the tests/ root; sub-directories inherit all fixtures.
"""
import pytest
import yaml
import logging
from pathlib import Path
from unittest.mock import MagicMock

from uart_protocol import UARTProtocolClient
from ble_client import PowerToolBLEClientSync


# ── Configuration ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def config() -> dict:
    """Load device configuration once for the entire session."""
    cfg_path = Path(__file__).parent / "config" / "device_config.yaml"
    with cfg_path.open() as f:
        return yaml.safe_load(f)


# ── UART Device ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def uart_device(config):
    """
    Open UART port for all tests in a module.
    Yields connected client; closes port after module completes.
    """
    client = UARTProtocolClient(
        port=config["uart"]["port"],
        baud=config["uart"]["baud_rate"],
    )
    client.open()
    yield client
    client.close()


@pytest.fixture(scope="function")
def uart_clean_state(uart_device):
    """
    Per-test: flush UART buffers and reset device to known state.
    Ensures each test starts clean.
    """
    uart_device.send_receive(0xFF, b"\x00")   # soft reset command
    import time; time.sleep(0.2)              # wait for reset complete
    yield uart_device
    # Teardown: flush any remaining data
    with uart_device._rx_q.mutex:
        uart_device._rx_q.queue.clear()


# ── BLE Device ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="class")
def ble_device(config):
    """
    Connect to BLE device once per test class.
    All tests in the class share the same connection.
    """
    client = PowerToolBLEClientSync(
        device_name=config["ble"]["device_name"]
    )
    client.__enter__()
    yield client
    client.__exit__(None, None, None)


# ── Factory Fixture ────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def make_measurement_verifier():
    """
    Factory fixture: returns a function that creates measurement verifiers.
    Tests call make_measurement_verifier(tolerance=0.05) to get a verifier.
    """
    def _factory(tolerance: float = 0.05):
        class MeasurementVerifier:
            def __init__(self, tol):
                self.tolerance = tol

            def verify(self, actual: float, expected: float,
                       label: str = "value") -> None:
                if expected == 0:
                    err = abs(actual - expected)
                    assert err < 0.001, \
                        f"{label}: expected ~0, got {actual}"
                else:
                    rel_err = abs(actual - expected) / abs(expected)
                    assert rel_err <= self.tolerance, (
                        f"{label}: {actual:.4f} vs expected {expected:.4f} "
                        f"(error {rel_err*100:.2f}% > {self.tolerance*100:.0f}%)"
                    )
        return MeasurementVerifier(tolerance)
    return _factory


# ── Temp Directory for Test Artifacts ─────────────────────────────────────────

@pytest.fixture(scope="function")
def test_artifacts_dir(tmp_path):
    """Provide a temporary directory for logs, screenshots, etc."""
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    yield artifacts
    # pytest keeps tmp_path for 3 runs by default (configurable)


# ── Mock Device (for CI without hardware) ─────────────────────────────────────

@pytest.fixture
def mock_uart_device():
    """
    Mock UART device for unit tests and CI pipelines without hardware.
    Returns pre-programmed responses.
    """
    mock = MagicMock(spec=UARTProtocolClient)
    mock.read_all_measurements.return_value = {
        "voltage_v":     12.05,
        "current_a":     1.50,
        "temperature_c": 28.3,
    }
    return mock
```

---

## 3. Parametrize — Data-Driven Testing

```python
"""
test_measurement_accuracy.py — Parametrized accuracy tests.
"""
import pytest

# ── Simple parametrize ────────────────────────────────────────────────────────
@pytest.mark.parametrize("ref_voltage, tolerance", [
    (0.0,   0.001),   # Zero: absolute tolerance
    (3.3,   0.05),    # 3.3V logic rail
    (5.0,   0.05),    # USB
    (12.0,  0.05),    # Automotive
    (24.0,  0.05),    # Industrial
    (36.0,  0.05),    # Li-ion pack
])
def test_voltage_accuracy(uart_clean_state, ref_voltage, tolerance,
                          make_measurement_verifier):
    """Voltage measurement within tolerance at each reference level."""
    verifier = make_measurement_verifier(tolerance)

    # Apply reference voltage via bench supply (or HIL injection)
    uart_clean_state.send_receive(0x30, bytes([int(ref_voltage * 10)]))

    result = uart_clean_state.read_all_measurements()
    verifier.verify(result["voltage_v"], ref_voltage, label="Voltage")


# ── Parametrize with IDs ────────────────────────────────────────────────────
@pytest.mark.parametrize("mode,mode_name,expected_rate_hz", [
    (0, "idle",        0),
    (1, "slow",        1),
    (2, "normal",     10),
    (3, "fast",       50),
    (4, "burst",     100),
], ids=["idle", "1Hz", "10Hz", "50Hz", "100Hz"])
def test_notification_rate_by_mode(uart_clean_state, mode, mode_name,
                                   expected_rate_hz):
    """Each measurement mode produces the correct notification rate."""
    uart_clean_state.set_measurement_mode(mode)

    if expected_rate_hz == 0:
        import time; time.sleep(1)
        assert True   # Just verify no crash in idle mode
        return

    samples = uart_clean_state.collect_timed_samples(duration_s=2.0)
    actual_hz = len(samples) / 2.0
    tolerance = 0.20   # ±20%

    assert abs(actual_hz - expected_rate_hz) / expected_rate_hz <= tolerance, \
        f"Mode {mode_name}: {actual_hz:.1f} Hz vs expected {expected_rate_hz} Hz"


# ── Indirect parametrize (pass to fixture) ────────────────────────────────────
@pytest.fixture
def device_at_voltage(request, uart_clean_state):
    """Fixture that sets device voltage from parameter."""
    voltage = request.param
    uart_clean_state.send_receive(0x30, bytes([int(voltage * 10)]))
    yield uart_clean_state, voltage

@pytest.mark.parametrize("device_at_voltage", [5.0, 12.0, 24.0],
                         indirect=True)
def test_device_stable_at_voltage(device_at_voltage):
    """Device stays stable for 5 seconds at each supply voltage."""
    import time
    device, voltage = device_at_voltage
    start = time.monotonic()
    while time.monotonic() - start < 5.0:
        m = device.read_all_measurements()
        assert abs(m["voltage_v"] - voltage) / voltage < 0.10, \
            f"Voltage instability at {voltage}V: read {m['voltage_v']:.3f}V"
        time.sleep(0.5)
```

---

## 4. Markers

```python
# pytest.ini (or pyproject.toml)
# [tool.pytest.ini_options]
# markers =
#   smoke: Quick sanity checks, run in < 5 minutes
#   regression: Full regression suite
#   hardware: Requires physical hardware (skip in CI)
#   ble: BLE-specific tests
#   uart: UART-specific tests
#   accuracy: Measurement accuracy tests
#   slow: Tests > 2 minutes each
#   flaky: Known intermittent tests (investigate separately)

import pytest

@pytest.mark.smoke
@pytest.mark.ble
def test_ble_device_discoverable():
    """Fast smoke test — run on every commit."""
    ...

@pytest.mark.regression
@pytest.mark.accuracy
@pytest.mark.parametrize("voltage", [5.0, 12.0, 24.0])
def test_voltage_accuracy_regression(voltage):
    ...

@pytest.mark.hardware
def test_physical_button_press():
    """Requires physical test jig — skip in simulated CI."""
    ...

@pytest.mark.slow
def test_24h_soak_stability():
    """24-hour endurance test — run weekly only."""
    ...
```

### Running with Markers
```bash
# Only smoke tests
pytest -m smoke tests/

# Regression without slow tests
pytest -m "regression and not slow" tests/

# All BLE tests
pytest -m ble tests/

# Skip hardware tests (CI without bench)
pytest -m "not hardware" tests/

# Run by keyword match
pytest -k "voltage or current" tests/
```

---

## 5. Useful Pytest Plugins

```
Plugin ecosystem for device testing:
──────────────────────────────────────────────────────────────────────────
pytest-html          Generate self-contained HTML report
                     pip install pytest-html
                     Usage: --html=report.html --self-contained-html

pytest-xdist         Parallel test execution
                     pip install pytest-xdist
                     Usage: -n 4 (4 parallel workers)

pytest-cov           Code coverage measurement
                     pip install pytest-cov
                     Usage: --cov=src --cov-report=html

pytest-asyncio       async test functions and fixtures
                     pip install pytest-asyncio
                     Usage: @pytest.mark.asyncio

pytest-rerunfailures Retry flaky tests
                     pip install pytest-rerunfailures
                     Usage: --reruns 3 --reruns-delay 2

pytest-timeout       Per-test timeout
                     pip install pytest-timeout
                     Usage: --timeout=30 or @pytest.mark.timeout(30)

pytest-benchmark     Measure execution time
                     pip install pytest-benchmark
                     Usage: def test_speed(benchmark): benchmark(fn)

pytest-mock          Convenient mocker fixture
                     pip install pytest-mock
                     Usage: def test_x(mocker): mocker.patch(...)
──────────────────────────────────────────────────────────────────────────
```

---

## 6. Code Coverage

```bash
# Run tests with coverage
pytest --cov=libraries --cov=src \
       --cov-report=html:reports/coverage \
       --cov-report=term-missing \
       --cov-fail-under=80 \
       tests/

# Show missing lines in terminal
pytest --cov=libraries --cov-report=term-missing tests/

# Coverage HTML report
open reports/coverage/index.html
```

```python
# .coveragerc or pyproject.toml
# [coverage:run]
# source = libraries, src
# omit = tests/*, */migrations/*, setup.py
#
# [coverage:report]
# fail_under = 80
# show_missing = true
# exclude_lines =
#     pragma: no cover
#     def __repr__
#     raise NotImplementedError
```

---

## 7. REST API Testing with pytest

```python
"""
test_rest_api.py — REST API testing (e.g., cloud backend for power tool telemetry).
"""
import pytest
import requests
from pydantic import BaseModel, validator
from typing import Optional


# ── Pydantic models for response validation ────────────────────────────────
class DeviceTelemetry(BaseModel):
    device_id:      str
    timestamp:      str
    voltage_v:      float
    current_a:      float
    temperature_c:  float
    battery_pct:    int
    firmware_ver:   str

    @validator("battery_pct")
    def battery_in_range(cls, v):
        assert 0 <= v <= 100, f"Battery {v}% out of range"
        return v

    @validator("voltage_v")
    def voltage_positive(cls, v):
        assert v >= 0, f"Voltage cannot be negative: {v}"
        return v


class APIClient:
    """REST API client for power tool cloud backend."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        })

    def get_device_telemetry(self, device_id: str) -> dict:
        resp = self.session.get(
            f"{self.base_url}/devices/{device_id}/telemetry",
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def post_measurement(self, device_id: str, data: dict) -> dict:
        resp = self.session.post(
            f"{self.base_url}/devices/{device_id}/measurements",
            json=data,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


@pytest.fixture(scope="module")
def api_client(config):
    return APIClient(
        base_url=config["api"]["base_url"],
        api_key=config["api"]["key"],
    )


# ── API Tests ──────────────────────────────────────────────────────────────

def test_telemetry_endpoint_returns_200(api_client, config):
    """GET /devices/{id}/telemetry returns HTTP 200."""
    device_id = config["ble"]["device_id"]
    resp = api_client.session.get(
        f"{api_client.base_url}/devices/{device_id}/telemetry",
        timeout=10,
    )
    assert resp.status_code == 200, \
        f"Expected 200, got {resp.status_code}: {resp.text[:200]}"


def test_telemetry_response_schema(api_client, config):
    """Telemetry response matches expected schema (validated by Pydantic)."""
    data = api_client.get_device_telemetry(config["ble"]["device_id"])
    # Pydantic validates all fields and constraints
    telemetry = DeviceTelemetry(**data)
    assert telemetry.device_id == config["ble"]["device_id"]


def test_post_measurement_returns_created(api_client, config):
    """POST measurement returns 201 Created with created resource."""
    payload = {
        "voltage_v": 12.05,
        "current_a": 1.5,
        "temperature_c": 28.3,
        "battery_pct": 75,
    }
    result = api_client.post_measurement(
        config["ble"]["device_id"], payload
    )
    assert "id" in result, "Response missing 'id' field"
    assert "timestamp" in result, "Response missing 'timestamp' field"


def test_invalid_device_returns_404(api_client):
    """Unknown device ID returns 404."""
    resp = api_client.session.get(
        f"{api_client.base_url}/devices/NONEXISTENT_DEVICE_XYZ/telemetry",
        timeout=10,
    )
    assert resp.status_code == 404, \
        f"Expected 404 for unknown device, got {resp.status_code}"


@pytest.mark.parametrize("missing_field", [
    "voltage_v", "current_a", "temperature_c"
])
def test_measurement_missing_required_field_returns_400(api_client, config,
                                                         missing_field):
    """Missing required measurement field returns 400 Bad Request."""
    payload = {
        "voltage_v": 12.0,
        "current_a": 1.5,
        "temperature_c": 28.0,
        "battery_pct": 80,
    }
    del payload[missing_field]
    resp = api_client.session.post(
        f"{api_client.base_url}/devices/{config['ble']['device_id']}/measurements",
        json=payload,
        timeout=10,
    )
    assert resp.status_code == 400, \
        f"Expected 400 for missing {missing_field}, got {resp.status_code}"
```

---

## 8. Custom Assertions and Helpers

```python
"""
assertions.py — Domain-specific assertion helpers.
Import in conftest.py or directly in test files.
"""
import statistics

def assert_within_tolerance(actual: float, expected: float,
                             tolerance: float, label: str = "value"):
    """Assert actual is within tolerance% of expected."""
    if expected == 0:
        assert abs(actual) < 1e-9, \
            f"{label}: expected 0, got {actual}"
    else:
        err = abs(actual - expected) / abs(expected)
        assert err <= tolerance, (
            f"{label} out of tolerance:\n"
            f"  Actual:   {actual:.6f}\n"
            f"  Expected: {expected:.6f}\n"
            f"  Error:    {err*100:.3f}% (limit {tolerance*100:.1f}%)"
        )


def assert_measurement_stable(samples: list[float],
                               max_std_dev_pct: float = 1.0,
                               label: str = "signal"):
    """Assert a series of measurements is stable (low standard deviation)."""
    if len(samples) < 3:
        raise ValueError("Need at least 3 samples to check stability")

    mean  = statistics.mean(samples)
    stdev = statistics.stdev(samples)
    std_pct = (stdev / mean * 100) if mean != 0 else stdev * 100

    assert std_pct <= max_std_dev_pct, (
        f"{label} unstable:\n"
        f"  Mean:    {mean:.4f}\n"
        f"  Std dev: {stdev:.4f} ({std_pct:.2f}%)\n"
        f"  Limit:   {max_std_dev_pct:.1f}%\n"
        f"  Samples: {samples}"
    )


def assert_response_time(actual_ms: float, limit_ms: float,
                          operation: str = "operation"):
    """Assert operation completed within time limit."""
    assert actual_ms <= limit_ms, (
        f"{operation} response time {actual_ms:.1f}ms exceeds limit {limit_ms:.0f}ms"
    )


def assert_no_errors_in_log(log_lines: list[str],
                             error_patterns: list[str] = None):
    """Assert no error patterns found in log."""
    patterns = error_patterns or ["ERROR", "FAULT", "CRASH", "ASSERT"]
    found_errors = []
    for line in log_lines:
        if any(p in line.upper() for p in patterns):
            found_errors.append(line)

    assert not found_errors, (
        f"Found {len(found_errors)} errors in log:\n" +
        "\n".join(f"  {e}" for e in found_errors[:10])
    )
```

---

## 9. Interview Q&A

**Q1: What is the difference between `@pytest.fixture(scope="module")` and `scope="function"`? When does it matter?**  
`scope="module"` runs the fixture's setup once when the first test in the module requests it, and tears it down after the last test in that module. `scope="function"` runs setup and teardown around each individual test. For hardware: opening a serial port at `module` scope is far faster than re-opening it 50 times. But you pay for it: if one test corrupts the UART state, all subsequent tests in the module are affected. Solution: add a `function`-scoped "clean state" fixture that flushes buffers/resets state between tests, while keeping the `module`-scoped connection open.

**Q2: How does `yield` in a pytest fixture enable teardown?**  
Everything before `yield` is the setup phase; everything after is the teardown phase. pytest guarantees the teardown runs even if the test or setup raises an exception. For example: `serial_port.open()` before yield, `serial_port.close()` after. Without yield, you'd need `try/finally` everywhere. The yield value (the object placed after `yield`) is what the test receives as the fixture argument.

**Q3: How do you use `pytest.mark.parametrize` to reduce test duplication?**  
Parametrize decorates a test function with a list of argument tuples. pytest generates one test item per tuple, with each combination appearing as a separate result in the report. This is ideal for testing the same behavior at multiple input values (voltages, modes, error codes). I combine it with `ids=` parameter to give each variant a readable name in reports. For fixtures that need to receive the parameter, I use `indirect=True` so the fixture receives `request.param`.

**Q4: When would you use `pytest-xdist` and what are the limitations?**  
`pytest-xdist` distributes test items across multiple parallel workers. I use it to run independent test modules on different hardware benches simultaneously (e.g., 4 tests on 4 devices). Limitations: (1) fixtures must be worker-safe — no global shared state; (2) `scope="session"` fixtures are re-created per worker, so expensive setup is multiplied; (3) test order is not guaranteed; (4) if tests share hardware (same serial port), parallelism causes conflicts. Solution: design tests to be completely independent, use per-worker device assignment in `conftest.py`.

**Q5: How do you validate a REST API response schema in pytest?**  
I use Pydantic models to define the expected schema. The test calls the API, then creates a Pydantic model instance from the response JSON: `DeviceTelemetry(**response.json())`. Pydantic raises a `ValidationError` with detailed messages if any field is missing, wrong type, or fails a validator. This gives much better error messages than manual asserts (`assert "voltage_v" in data` doesn't tell you about wrong types). I also test boundary cases: unknown device → 404, missing fields → 400, and verify the `Content-Type` header is `application/json`.
