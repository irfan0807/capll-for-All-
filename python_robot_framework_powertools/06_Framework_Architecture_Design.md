# 06 — Framework Architecture Design

> **Topic**: OOP patterns, keyword-driven, data-driven, hybrid frameworks, modularity, library design  
> **Role relevance**: Design maintainable frameworks that junior engineers can extend without breaking things  
> **Outcome**: Build a production-quality test framework that scales from 50 to 5000 test cases

---

## 1. Why Framework Architecture Matters

```
Framework design principles impact:
──────────────────────────────────────────────────────────────────────────
Bad framework (monolithic)          Good framework (layered)
──────────────────────────────────────────────────────────────────────────
Copy-paste test code                Reusable keyword library
Hardcoded device ports              Configuration-driven (YAML)
No separation of concerns           Clear layer boundaries
Test failure = debug the framework  Test failure = debug the DUT
Adding new test = 4 hours           Adding new test = 20 minutes
New engineer can't contribute       Junior can add tests in day 1
──────────────────────────────────────────────────────────────────────────
```

---

## 2. Layered Framework Architecture

```
PowerTool Test Framework Layers:
──────────────────────────────────────────────────────────────────────────
Layer 4: Test Layer
  test_ble_connection.robot      ← What to test (business logic)
  test_measurement_accuracy.py  ← Uses keywords/fixtures, no HW details
  test_uart_commands.robot

Layer 3: Keyword / Fixture Layer
  BLEKeywords.resource          ← Domain keywords: "Read Battery Level"
  UARTKeywords.resource         ← "Send Command And Verify Response"
  MeasurementKeywords.resource  ← "Verify Voltage Within Tolerance"
  conftest.py                   ← pytest fixtures: ble_device, uart_device

Layer 2: Library Layer
  BLELibrary.py                 ← Connects, reads, writes, notifies
  UARTLibrary.py                ← Serial framing, send_receive, retries
  MeasurementLibrary.py         ← Math: tolerance checks, statistics
  DeviceFlasher.py              ← Flash firmware, verify

Layer 1: Hardware Abstraction Layer (HAL)
  serial_adapter.py             ← Wraps pyserial (swap for mock easily)
  ble_adapter.py                ← Wraps bleak (swap for mock easily)
  power_supply.py               ← Controls bench power supply
  relay_board.py                ← Controls physical relays (reset device)

Layer 0: Infrastructure
  Configuration (YAML)
  Logging
  Reporting
  CI (Jenkins / Azure DevOps)
──────────────────────────────────────────────────────────────────────────
```

---

## 3. Design Patterns Used in Test Frameworks

### Pattern 1: Page Object → Device Object Model
```python
"""
device_model.py — Device Object Model (DOM) pattern.
Adapted from Page Object Model (used in web testing).
Each 'page' becomes a device 'feature area'.
"""

class PowerToolDevice:
    """
    Top-level device class — composes feature areas.
    Test code interacts with this, not raw libraries.
    """

    def __init__(self, ble_client, uart_client):
        # Compose feature modules (Facade pattern)
        self.battery     = BatteryFeature(ble_client)
        self.measurement = MeasurementFeature(ble_client, uart_client)
        self.motor       = MotorFeature(uart_client)
        self.diagnostics = DiagnosticsFeature(uart_client)
        self.firmware    = FirmwareFeature(uart_client)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class BatteryFeature:
    """All battery-related operations."""

    def __init__(self, ble_client):
        self._ble = ble_client

    def get_level(self) -> int:
        """Return battery level 0–100%."""
        return self._ble.read_battery_level()

    def is_low(self, threshold: int = 20) -> bool:
        return self.get_level() < threshold

    def is_charging(self) -> bool:
        status = self._ble.read_characteristic("0xFF04")
        return bool(int(status) & 0x01)


class MeasurementFeature:
    """Voltage/current/temperature measurement operations."""

    VOLTAGE_CHANNEL_UUID = "0xFF01"
    CURRENT_CHANNEL_UUID = "0xFF02"
    TEMP_UUID            = "0xFF03"

    def __init__(self, ble_client, uart_client):
        self._ble  = ble_client
        self._uart = uart_client

    def read_voltage(self) -> float:
        return self._ble.read_voltage()

    def read_current(self) -> float:
        return self._ble.read_current()

    def collect_samples(self, duration_s: float,
                        interval_s: float = 0.1) -> list[dict]:
        """Collect {voltage, current, temperature} samples over time."""
        return self._ble.collect_samples(duration_s, interval_s)

    def set_mode(self, mode: str) -> None:
        mode_map = {"idle": 0, "slow": 1, "normal": 2, "fast": 3}
        code = mode_map.get(mode.lower())
        if code is None:
            raise ValueError(f"Unknown mode {mode!r}. Valid: {list(mode_map)}")
        self._uart.set_measurement_mode(code)


class DiagnosticsFeature:
    """Device diagnostics, self-test, error codes."""

    CMD_GET_FAULTS = 0x50
    CMD_CLEAR_FAULTS = 0x51
    CMD_SELF_TEST  = 0x52

    def __init__(self, uart_client):
        self._uart = uart_client

    def get_active_faults(self) -> list[int]:
        """Return list of active fault codes."""
        resp = self._uart.send_receive(self.CMD_GET_FAULTS)
        if not resp.payload:
            return []
        count = resp.payload[0]
        return list(resp.payload[1:1+count])

    def clear_faults(self) -> None:
        self._uart.send_receive(self.CMD_CLEAR_FAULTS)

    def run_self_test(self) -> dict:
        """Run built-in self-test. Returns {passed: bool, details: str}."""
        resp = self._uart.send_receive(self.CMD_SELF_TEST)
        passed  = resp.payload[0] == 0
        details = resp.payload[1:].decode("utf-8", errors="replace")
        return {"passed": passed, "details": details}
```

### Pattern 2: Factory for Test Configuration
```python
"""
factory.py — Factory pattern to create device instances from config.
"""
import yaml
from pathlib import Path

class DeviceFactory:
    """
    Creates fully configured device objects from YAML config.
    Tests never instantiate hardware classes directly.
    """

    @classmethod
    def from_config(cls, config_path: str) -> "PowerToolDevice":
        """Create a PowerToolDevice from configuration file."""
        with open(config_path) as f:
            cfg = yaml.safe_load(f)

        # Choose concrete implementations based on config
        if cfg.get("mock_mode"):
            return cls._create_mock(cfg)
        else:
            return cls._create_real(cfg)

    @classmethod
    def _create_real(cls, cfg: dict) -> "PowerToolDevice":
        from ble_client import PowerToolBLEClientSync
        from uart_protocol import UARTProtocolClient

        ble  = PowerToolBLEClientSync(cfg["ble"]["device_name"])
        uart = UARTProtocolClient(cfg["uart"]["port"], cfg["uart"]["baud"])
        ble.__enter__()
        uart.open()
        return PowerToolDevice(ble, uart)

    @classmethod
    def _create_mock(cls, cfg: dict) -> "PowerToolDevice":
        """Return device with mocked hardware for CI without bench."""
        from unittest.mock import MagicMock
        ble  = MagicMock()
        uart = MagicMock()
        ble.read_battery_level.return_value = 85
        ble.read_voltage.return_value       = 12.05
        ble.read_current.return_value       = 1.50
        return PowerToolDevice(ble, uart)
```

### Pattern 3: Strategy for Measurement Protocols
```python
"""
measurement_strategy.py — Strategy pattern for different measurement interfaces.
Switch between BLE, UART, or USB without changing test code.
"""
from abc import ABC, abstractmethod

class MeasurementStrategy(ABC):
    """Abstract: read measurements from any interface."""

    @abstractmethod
    def read_voltage(self) -> float: ...

    @abstractmethod
    def read_current(self) -> float: ...


class BLEMeasurementStrategy(MeasurementStrategy):
    def __init__(self, ble_client):
        self._client = ble_client

    def read_voltage(self) -> float:
        return self._client.read_voltage()

    def read_current(self) -> float:
        return self._client.read_current()


class UARTMeasurementStrategy(MeasurementStrategy):
    def __init__(self, uart_client):
        self._client = uart_client

    def read_voltage(self) -> float:
        m = self._client.read_all_measurements()
        return m["voltage_v"]

    def read_current(self) -> float:
        m = self._client.read_all_measurements()
        return m["current_a"]


class MeasurementVerifier:
    """
    Uses whichever measurement strategy is injected.
    Test code doesn't know or care how measurements are read.
    """

    def __init__(self, strategy: MeasurementStrategy,
                 tolerance: float = 0.05):
        self._strategy  = strategy
        self._tolerance = tolerance

    def verify_voltage(self, expected_v: float) -> None:
        actual = self._strategy.read_voltage()
        err = abs(actual - expected_v) / expected_v if expected_v else abs(actual)
        assert err <= self._tolerance, \
            f"Voltage {actual:.4f}V vs expected {expected_v}V (err {err*100:.2f}%)"
```

### Pattern 4: Observer for Test Events
```python
"""
observer.py — Observer pattern for test lifecycle events.
Allows plugging in reporting, database logging, etc.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol
from datetime import datetime

@dataclass
class TestEvent:
    test_name: str
    status:    str          # PASS / FAIL / SKIP
    message:   str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_s: float = 0.0


class TestObserver(ABC):
    """Interface: receive test lifecycle events."""

    @abstractmethod
    def on_test_end(self, event: TestEvent) -> None: ...


class ConsoleObserver(TestObserver):
    def on_test_end(self, event: TestEvent) -> None:
        icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "○"}.get(event.status, "?")
        print(f"  [{icon}] {event.test_name} ({event.duration_s:.2f}s)")


class JiraObserver(TestObserver):
    def __init__(self, jira_client, project_key: str):
        self._jira    = jira_client
        self._project = project_key

    def on_test_end(self, event: TestEvent) -> None:
        if event.status == "FAIL":
            self._jira.create_bug(
                project=self._project,
                summary=f"[AUTO] Test failed: {event.test_name}",
                description=event.message,
            )


class TestEventPublisher:
    """Notify all registered observers of test events."""

    def __init__(self):
        self._observers: list[TestObserver] = []

    def subscribe(self, obs: TestObserver) -> None:
        self._observers.append(obs)

    def publish(self, event: TestEvent) -> None:
        for obs in self._observers:
            try:
                obs.on_test_end(event)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    "Observer %s failed: %s", obs.__class__.__name__, e
                )
```

---

## 4. Keyword-Driven Framework (Robot Framework)

```
Keyword-Driven Architecture:
──────────────────────────────────────────────────────────────────────────
Test:        Connect BLE Device And Read Battery Level
             ↓ calls ↓
Keyword:     Connect To BLE Device    ${DEVICE_NAME}
             Read Battery Level
             Battery Level Should Be Above    20
             ↓ calls ↓
Library:     BLELibrary.connect_to_device(name)  → bleak
             BLELibrary.read_battery_level()      → GATT 0x2A19
             BLELibrary.disconnect()

Advantages:
  - Test is readable by non-programmers
  - Library is reusable across all suites
  - Keyword represents the INTENT, library is the IMPLEMENTATION
  - Change the library (e.g., BLE → USB) without changing the test
──────────────────────────────────────────────────────────────────────────
```

---

## 5. Data-Driven Framework (CSV + pytest)

```python
"""
data_driven_framework.py — Load test cases from CSV, run with pytest.
Engineers add test cases without touching code.
"""
import csv
import pytest
from pathlib import Path


def load_test_cases(csv_path: str) -> list[tuple]:
    """Load test cases from CSV file. Returns list of (id, params) tuples."""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("enabled", "yes").lower() == "yes":
                rows.append(pytest.param(
                    row,
                    id=row.get("test_id", f"TC-{len(rows)+1}"),
                    marks=[
                        getattr(pytest.mark, tag.strip())
                        for tag in row.get("tags", "").split(",")
                        if tag.strip()
                    ],
                ))
    return rows


# Test cases defined in CSV:
# test_id, ref_voltage, tolerance, expected_state, tags, enabled
# TC-VOLT-001, 12.0, 0.05, stable, regression accuracy, yes
# TC-VOLT-002, 5.0,  0.05, stable, regression,         yes
# TC-VOLT-003, 0.0,  0.001, zero,  regression accuracy, yes

TEST_DATA = load_test_cases("testdata/voltage_accuracy_tests.csv")

@pytest.mark.parametrize("tc", TEST_DATA)
def test_voltage_accuracy_from_csv(tc, uart_clean_state, make_measurement_verifier):
    """Data-driven voltage test loaded from CSV."""
    ref_v   = float(tc["ref_voltage"])
    tol     = float(tc["tolerance"])
    verifier = make_measurement_verifier(tolerance=tol)

    uart_clean_state.send_receive(0x30, bytes([int(ref_v * 10)]))
    result = uart_clean_state.read_all_measurements()
    verifier.verify(result["voltage_v"], ref_v, label=tc["test_id"])
```

---

## 6. Framework Self-Test (Eating Your Own Dog Food)

```python
"""
tests/test_framework.py — Unit tests FOR the framework itself.
If framework code breaks, catch it here before it breaks real tests.
"""
import pytest
from unittest.mock import MagicMock, patch
from uart_protocol import Frame, UARTProtocolClient
from assertions import assert_within_tolerance, assert_measurement_stable


class TestFrameParsing:
    """Test binary frame serialization and parsing."""

    def test_roundtrip_empty_payload(self):
        frame = Frame(cmd_id=0x10)
        parsed = Frame.from_bytes(frame.to_bytes())
        assert parsed.cmd_id == 0x10
        assert parsed.payload == b""

    def test_roundtrip_with_payload(self):
        frame = Frame(cmd_id=0x20, payload=bytes([0x01, 0x02, 0x03]))
        parsed = Frame.from_bytes(frame.to_bytes())
        assert parsed.payload == bytes([0x01, 0x02, 0x03])

    def test_bad_checksum_raises(self):
        raw = bytearray(Frame(cmd_id=0x10).to_bytes())
        raw[-2] ^= 0xFF   # Corrupt checksum
        with pytest.raises(ValueError, match="Checksum"):
            Frame.from_bytes(bytes(raw))

    def test_wrong_sof_raises(self):
        raw = bytearray(Frame(cmd_id=0x10).to_bytes())
        raw[0] = 0x00
        with pytest.raises(ValueError, match="SOF"):
            Frame.from_bytes(bytes(raw))


class TestAssertions:
    """Test custom assertion helpers."""

    def test_within_tolerance_passes(self):
        assert_within_tolerance(12.05, 12.0, tolerance=0.05)

    def test_within_tolerance_fails(self):
        with pytest.raises(AssertionError):
            assert_within_tolerance(13.0, 12.0, tolerance=0.05)

    def test_stable_signal_passes(self):
        assert_measurement_stable([12.0, 12.01, 11.99, 12.0], max_std_dev_pct=1.0)

    def test_unstable_signal_fails(self):
        with pytest.raises(AssertionError, match="unstable"):
            assert_measurement_stable([12.0, 15.0, 9.0, 12.0], max_std_dev_pct=1.0)
```

---

## 7. Interview Q&A

**Q1: What design patterns do you use in a test automation framework and why?**  
The most important ones: (1) **Device Object Model** (adapted from Page Object) — encapsulate each feature area (battery, motor, diagnostics) in its own class so test code reads as business logic; (2) **Factory** — create device objects from YAML config so tests don't hardcode hardware details; (3) **Strategy** — swap measurement protocol (BLE vs UART vs USB) without changing tests; (4) **Observer** — decouple test reporting from test logic so I can add JIRA integration without modifying any test. These patterns make the framework easy to extend without breaking existing tests.

**Q2: How do you design a framework so a junior engineer can add a new test case without breaking others?**  
Four rules: (1) Tests must be independent — each test sets up and tears down its own state via fixtures, never relying on previous test results; (2) Configuration is in YAML/CSV, not in code — junior adds a row to a CSV to add a test; (3) Hardware access is always through the Device Object Model, never through raw libraries — if they call `device.measurement.read_voltage()`, the fixture guarantees they get a clean, connected device; (4) Assertions use domain helpers (`assert_within_tolerance`) not raw `assert abs(a-b)/b < 0.05` — readable and consistent.

**Q3: What is the difference between keyword-driven and data-driven testing?**  
**Keyword-driven**: Test logic is expressed as business-readable keywords (`Connect To Device`, `Read Battery Level`, `Battery Should Be Above`). The library provides the implementation. Adding test logic = write new keywords. **Data-driven**: The test logic is fixed; what varies is the input data (reference voltages, tolerances). Adding test coverage = add a row to a CSV or parametrize list. In practice, most frameworks are hybrid: keyword-driven for complex scenarios (BLE pairing flow), data-driven for accuracy tests (check 10 reference voltages).

**Q4: How do you handle hardware abstraction so the same tests run on a real device and a mock?**  
I use a Factory pattern with a configuration flag. The `DeviceFactory.from_config()` reads `mock_mode: true` from the YAML and returns a `MagicMock` pre-programmed with expected responses. The same test code, fixtures, and assertions run unchanged. This means: (1) CI pipelines without hardware run the full test suite against mocks in seconds; (2) Framework code bugs are caught by CI before reaching the hardware lab; (3) Mocks define the API contract that the real hardware must match.

**Q5: How do you maintain a test framework as the device firmware evolves?**  
Three practices: (1) **Semantic versioning for the framework itself** — increment minor version when adding features, patch for fixes; (2) **Backward-compatible library APIs** — add new keyword parameters with default values, never remove existing ones without a deprecation period; (3) **Framework integration tests** (`test_framework.py`) — if firmware changes the UART protocol, the frame parser tests fail immediately, not silently; (4) **Changelog** — every merged framework change documents what tests it affects, so the team knows what to re-validate.
