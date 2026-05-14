# 02 — Robot Framework Fundamentals

> **Topic**: RF architecture, test suites, keyword libraries, resource files, variables, listeners  
> **Role relevance**: Primary test automation tool for power tools validation  
> **Outcome**: Write professional Robot Framework test suites and custom Python keyword libraries

---

## 1. Robot Framework Architecture

```
Robot Framework Architecture:
──────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────────┐
│                        Test Suite Files (.robot)                        │
│   Settings │ Variables │ Test Cases │ Keywords                          │
└─────────────────────────────────────────────────────────────────────────┘
                               │ uses
┌─────────────────────────────────────────────────────────────────────────┐
│                         Resource Files (.resource)                      │
│   Reusable keywords, variables, library imports                         │
└─────────────────────────────────────────────────────────────────────────┘
                               │ imports
┌──────────────────┬────────────────────────┬───────────────────────────┐
│  Built-in Libs   │  External Libs          │  Custom Python Libraries  │
│  BuiltIn         │  SeleniumLibrary        │  BLELibrary               │
│  OperatingSystem │  RequestsLibrary        │  UARTLibrary              │
│  Collections     │  pabot (parallel)       │  PowerToolLibrary         │
│  String          │  SSHLibrary             │  MeasurementLibrary       │
│  Process         │                         │                           │
└──────────────────┴────────────────────────┴───────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────────────┐
│                        Test Runner (robot)                              │
│   Execution, result collection, report/log generation                   │
└─────────────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────────────┐
│                   Output: output.xml, log.html, report.html             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Project Structure

```
power_tool_tests/
├── tests/
│   ├── 01_connection/
│   │   ├── ble_connection.robot
│   │   └── uart_connection.robot
│   ├── 02_measurement/
│   │   ├── voltage_accuracy.robot
│   │   └── current_accuracy.robot
│   ├── 03_communication/
│   │   ├── ble_notifications.robot
│   │   └── command_response.robot
│   └── 04_regression/
│       └── full_regression.robot
│
├── resources/
│   ├── common.resource           ← Shared keywords and imports
│   ├── ble_keywords.resource     ← BLE-specific keywords
│   ├── uart_keywords.resource    ← UART-specific keywords
│   └── variables.resource        ← Test variables
│
├── libraries/
│   ├── BLELibrary.py             ← Custom BLE keyword library
│   ├── UARTLibrary.py            ← Custom UART keyword library
│   └── MeasurementLibrary.py     ← Measurement validation library
│
├── testdata/
│   ├── device_config.yaml        ← Device configuration
│   └── measurement_tolerances.json
│
├── results/                      ← Generated reports
└── robot.yaml                    ← pabot / execution config
```

---

## 3. Test Suite Anatomy

### Basic Test Suite
```robotframework
*** Settings ***
Documentation    BLE connection and basic communication tests for PowerTool X1
...              Tests verify device discovery, pairing, and GATT service access.

Library          ../libraries/BLELibrary.py
Library          ../libraries/MeasurementLibrary.py
Library          BuiltIn
Library          Collections

Resource         ../resources/common.resource
Resource         ../resources/ble_keywords.resource

Suite Setup      Initialize BLE Test Environment
Suite Teardown   Cleanup BLE Test Environment

Test Setup       Reset Device State
Test Teardown    Log Device Status On Failure

*** Variables ***
${DEVICE_NAME}        PowerTool-X1
${BLE_TIMEOUT}        10
${MEASUREMENT_TOL}    0.05      # 5% tolerance


*** Test Cases ***
TC-BLE-001: Device Discoverable After Power On
    [Documentation]    Device must be discoverable within 5 seconds of power-on.
    [Tags]             smoke    ble    connection
    Power On Device
    ${discovered}=    Scan For BLE Device    ${DEVICE_NAME}    timeout=5
    Should Be True    ${discovered}    msg=Device not discovered within 5 seconds

TC-BLE-002: Successful GATT Connection
    [Documentation]    Verify GATT connection establishes and services are readable.
    [Tags]             smoke    ble    connection
    Power On Device
    Connect To BLE Device    ${DEVICE_NAME}    timeout=${BLE_TIMEOUT}
    ${services}=    Get GATT Services
    Should Contain    ${services}    0000180A-0000-1000-8000-00805F9B34FB
    ...    msg=Device Information Service (0x180A) not found
    [Teardown]    Disconnect From BLE Device

TC-BLE-003: Firmware Version Readable
    [Documentation]    Firmware version characteristic must return valid semver string.
    [Tags]             regression    ble    metadata
    Power On Device
    Connect To BLE Device    ${DEVICE_NAME}    timeout=${BLE_TIMEOUT}
    ${fw_ver}=    Read Characteristic    service=0x180A    char=0x2A26
    Should Match Regexp    ${fw_ver}    ^\\d+\\.\\d+\\.\\d+$
    ...    msg=Firmware version ${fw_ver} is not valid semver format
    Log    Firmware version: ${fw_ver}    level=INFO
    [Teardown]    Disconnect From BLE Device

TC-BLE-004: Voltage Measurement Within Tolerance
    [Documentation]    Voltage reading via BLE must match reference within 5%.
    [Tags]             regression    measurement    accuracy
    ${ref_voltage}=    Set Variable    12.0    # Reference voltage from bench supply
    Power On Device
    Connect To BLE Device    ${DEVICE_NAME}    timeout=${BLE_TIMEOUT}
    Apply Reference Voltage    ${ref_voltage}
    ${measured}=    Read Voltage Measurement
    Verify Within Tolerance
    ...    actual=${measured}
    ...    expected=${ref_voltage}
    ...    tolerance=${MEASUREMENT_TOL}
    [Teardown]    Disconnect From BLE Device


*** Keywords ***
Initialize BLE Test Environment
    [Documentation]    One-time setup: initialize BLE adapter, configure device config.
    Load Device Configuration    testdata/device_config.yaml
    Initialize BLE Adapter
    Log    BLE test environment initialized    level=INFO

Cleanup BLE Test Environment
    [Documentation]    One-time teardown: release BLE adapter.
    Release BLE Adapter
    Log    BLE test environment cleaned up    level=INFO

Reset Device State
    [Documentation]    Per-test setup: ensure device is in known state.
    Disconnect All BLE Devices
    Wait For Device Ready    timeout=3

Log Device Status On Failure
    [Documentation]    Per-test teardown: capture state on failure for debugging.
    Run Keyword If Test Failed    Capture Device Debug Log
    Run Keyword If Test Failed    Save Screenshot To Results
```

### Data-Driven Test
```robotframework
*** Settings ***
Library    ../libraries/MeasurementLibrary.py
Library    ../libraries/BLELibrary.py

*** Variables ***
${TOL}    0.05

*** Test Cases ***
Voltage Accuracy At Multiple Levels
    [Documentation]    Parameterized: verify accuracy at multiple voltages.
    [Tags]             regression    measurement    datadriven
    [Template]         Verify Voltage Accuracy
    #  Reference(V)    Description
    0.0                Zero voltage
    3.3                Logic supply (3.3V)
    5.0                USB supply (5V)
    12.0               Automotive supply (12V)
    24.0               Industrial supply (24V)
    36.0               Li-ion pack (36V)

Current Accuracy At Multiple Levels
    [Template]         Verify Current Accuracy
    #  Reference(A)    Description
    0.0                Zero current (open circuit)
    0.5                Light load
    2.0                Medium load
    5.0                Full load
    10.0               Peak current


*** Keywords ***
Verify Voltage Accuracy
    [Arguments]    ${ref_v}    ${description}
    [Documentation]    Set reference voltage, read device, check tolerance.
    Apply Reference Voltage    ${ref_v}
    ${measured}=    Read Voltage Measurement
    Verify Within Tolerance    ${measured}    ${ref_v}    ${TOL}
    Log    ${description}: ref=${ref_v}V measured=${measured}V ✓

Verify Current Accuracy
    [Arguments]    ${ref_a}    ${description}
    Apply Reference Current    ${ref_a}
    ${measured}=    Read Current Measurement
    Verify Within Tolerance    ${measured}    ${ref_a}    ${TOL}
```

---

## 4. Resource Files

Resource files collect reusable keywords across multiple suites:

```robotframework
# resources/common.resource
*** Settings ***
Library    BuiltIn
Library    OperatingSystem
Library    Collections
Library    String

*** Variables ***
${RESULTS_DIR}    ${CURDIR}/../results
${LOG_LEVEL}      INFO
${RETRY_COUNT}    3
${RETRY_DELAY}    1s

*** Keywords ***
Wait Until Keyword Succeeds With Log
    [Arguments]    ${retries}    ${interval}    ${keyword}    @{args}
    [Documentation]    Retry keyword with logging on each attempt.
    ${result}=    Wait Until Keyword Succeeds
    ...    ${retries}    ${interval}    ${keyword}    @{args}
    [Return]    ${result}

Verify Within Tolerance
    [Arguments]    ${actual}    ${expected}    ${tolerance}
    [Documentation]    Fail if |actual - expected| / expected > tolerance.
    ${diff}=         Evaluate    abs(${actual} - ${expected})
    ${rel_error}=    Evaluate    ${diff} / ${expected} if ${expected} != 0 else ${diff}
    Should Be True   ${rel_error} <= ${tolerance}
    ...    msg=Value ${actual} outside tolerance: expected ${expected} ±${tolerance*100:.1f}%

Create Timestamped Directory
    [Arguments]    ${base}
    ${ts}=         Get Current Date    result_format=%Y%m%d_%H%M%S
    ${dir}=        Set Variable    ${base}/${ts}
    Create Directory    ${dir}
    [Return]    ${dir}

Log Test Boundary
    [Documentation]    Visual separator in log for readability.
    Log    ${'─' * 60}    level=INFO
```

---

## 5. Custom Python Keyword Library

The most powerful RF feature — writing keywords in Python:

```python
"""
libraries/BLELibrary.py — Robot Framework BLE keyword library.
"""
import asyncio
import logging
from typing import Optional
from robot.api import logger as rf_logger
from robot.api.deco import keyword, library

# bleak is the cross-platform BLE library for Python
from bleak import BleakClient, BleakScanner


@library(scope="SUITE")   # One instance per test suite
class BLELibrary:
    """
    Robot Framework keyword library for BLE device testing.

    Provides keywords for scanning, connecting, reading/writing
    GATT characteristics, and receiving BLE notifications.
    """

    ROBOT_LIBRARY_VERSION = "1.0.0"
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self):
        self._client: Optional[BleakClient] = None
        self._loop   = asyncio.new_event_loop()
        self._notifications: list[tuple] = []

    # ── Connection keywords ────────────────────────────────────────────────

    @keyword("Scan For BLE Device")
    def scan_for_device(self, name: str, timeout: float = 10.0) -> bool:
        """
        Scan for a BLE device by name.

        Returns True if found, False if not found within timeout.

        Example:
        | ${found}= | Scan For BLE Device | PowerTool-X1 | timeout=5 |
        """
        rf_logger.info(f"Scanning for BLE device: {name}")
        devices = self._run_async(
            BleakScanner.discover(timeout=timeout)
        )
        found = any(d.name == name for d in devices)
        if found:
            rf_logger.info(f"Found device: {name}")
        else:
            rf_logger.warn(f"Device {name!r} not found in scan")
        return found

    @keyword("Connect To BLE Device")
    def connect_to_device(self, name: str, timeout: float = 10.0) -> None:
        """
        Connect to a BLE device by name.

        Raises exception if device not found or connection fails.

        Example:
        | Connect To BLE Device | PowerTool-X1 | timeout=10 |
        """
        rf_logger.info(f"Connecting to BLE device: {name}")
        devices = self._run_async(BleakScanner.discover(timeout=timeout))
        device = next((d for d in devices if d.name == name), None)

        if not device:
            raise AssertionError(
                f"BLE device {name!r} not found. "
                f"Available: {[d.name for d in devices]}"
            )

        self._client = BleakClient(device.address)
        self._run_async(self._client.connect())
        rf_logger.info(f"Connected to {name} ({device.address})")

    @keyword("Disconnect From BLE Device")
    def disconnect(self) -> None:
        """Disconnect from currently connected BLE device."""
        if self._client and self._client.is_connected:
            self._run_async(self._client.disconnect())
            rf_logger.info("Disconnected from BLE device")
        self._client = None

    # ── GATT keywords ──────────────────────────────────────────────────────

    @keyword("Get GATT Services")
    def get_services(self) -> list[str]:
        """
        Return list of GATT service UUIDs on connected device.

        Example:
        | ${services}= | Get GATT Services |
        | Should Contain | ${services} | 0000180A-0000-1000-8000-00805F9B34FB |
        """
        self._require_connected()
        services = [str(svc.uuid).upper()
                    for svc in self._client.services]
        rf_logger.info(f"Found {len(services)} GATT services")
        return services

    @keyword("Read Characteristic")
    def read_characteristic(self, char_uuid: str) -> str:
        """
        Read a GATT characteristic and return value as string.

        Example:
        | ${fw}= | Read Characteristic | char=0x2A26 |
        """
        self._require_connected()
        # Expand short UUID to full UUID
        full_uuid = self._expand_uuid(char_uuid)
        raw = self._run_async(self._client.read_gatt_char(full_uuid))
        value = raw.decode("utf-8", errors="replace").strip()
        rf_logger.debug(f"Read {char_uuid}: {value!r}")
        return value

    @keyword("Write Characteristic")
    def write_characteristic(self, char_uuid: str, data: str) -> None:
        """
        Write to a GATT characteristic.

        Example:
        | Write Characteristic | char=0xFF01 | data=0100 |
        """
        self._require_connected()
        full_uuid = self._expand_uuid(char_uuid)
        payload = bytes.fromhex(data.replace(" ", ""))
        self._run_async(
            self._client.write_gatt_char(full_uuid, payload, response=True)
        )
        rf_logger.info(f"Wrote {len(payload)} bytes to {char_uuid}")

    @keyword("Subscribe To Notifications")
    def subscribe_notifications(self, char_uuid: str) -> None:
        """Enable BLE notifications for a characteristic."""
        self._require_connected()
        full_uuid = self._expand_uuid(char_uuid)

        def handler(sender, data):
            self._notifications.append((char_uuid, bytes(data)))
            rf_logger.debug(f"Notification from {char_uuid}: {data.hex()}")

        self._run_async(
            self._client.start_notify(full_uuid, handler)
        )
        rf_logger.info(f"Subscribed to notifications on {char_uuid}")

    @keyword("Wait For Notification")
    def wait_for_notification(self, char_uuid: str,
                              timeout: float = 5.0) -> str:
        """
        Wait for a notification on a subscribed characteristic.
        Returns notification data as hex string.
        Raises AssertionError if timeout expires.
        """
        import time
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for i, (uuid, data) in enumerate(self._notifications):
                if uuid == char_uuid:
                    self._notifications.pop(i)
                    return data.hex()
            time.sleep(0.05)
        raise AssertionError(
            f"No notification from {char_uuid} within {timeout}s"
        )

    # ── Internal helpers ───────────────────────────────────────────────────

    def _run_async(self, coro):
        """Run async coroutine in our dedicated event loop."""
        return self._loop.run_until_complete(coro)

    def _require_connected(self):
        if not self._client or not self._client.is_connected:
            raise AssertionError(
                "Not connected to any BLE device. "
                "Call 'Connect To BLE Device' first."
            )

    @staticmethod
    def _expand_uuid(short_uuid: str) -> str:
        """Expand short UUID (0x180A) to full 128-bit UUID."""
        if short_uuid.startswith("0x") or short_uuid.startswith("0X"):
            num = int(short_uuid, 16)
            return f"{num:08X}-0000-1000-8000-00805F9B34FB"
        return short_uuid.upper()

    # ── RF listener methods ────────────────────────────────────────────────
    def close(self):
        """Called when library scope ends — cleanup."""
        self.disconnect()
        self._loop.close()
```

---

## 6. Robot Framework Listeners

Listeners hook into the test execution lifecycle for custom reporting:

```python
"""
listeners/HTMLReportListener.py — Custom test listener that generates
a real-time HTML dashboard during execution.
"""
import json
from pathlib import Path
from datetime import datetime


class HTMLReportListener:
    """
    RF Listener that writes a live JSON summary updated after each test.
    A CI dashboard polls this file every 30 seconds.

    Usage in robot command:
      robot --listener listeners/HTMLReportListener.py tests/
    """
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, output_path="results/live_status.json"):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(exist_ok=True)
        self.results = []
        self.suite_name = ""
        self.start_time = datetime.now().isoformat()

    def start_suite(self, name, attrs):
        self.suite_name = name

    def end_test(self, name, attrs):
        self.results.append({
            "suite":    self.suite_name,
            "test":     name,
            "status":   attrs["status"],
            "message":  attrs.get("message", ""),
            "elapsed":  attrs["elapsedtime"],
            "tags":     attrs["tags"],
        })
        self._write()

    def _write(self):
        passed  = sum(1 for r in self.results if r["status"] == "PASS")
        failed  = sum(1 for r in self.results if r["status"] == "FAIL")
        summary = {
            "start_time": self.start_time,
            "updated":    datetime.now().isoformat(),
            "total":      len(self.results),
            "passed":     passed,
            "failed":     failed,
            "pass_rate":  f"{passed/len(self.results)*100:.1f}%" if self.results else "0%",
            "tests":      self.results,
        }
        with self.output_path.open("w") as f:
            json.dump(summary, f, indent=2)
```

---

## 7. Running Robot Framework

```bash
# Run all tests
robot tests/

# Run with specific tags
robot --include smoke tests/
robot --include regression --exclude slow tests/

# Run with variables override
robot --variable DEVICE_NAME:PowerTool-Pro tests/

# Run with custom output directory
robot --outputdir results/$(date +%Y%m%d_%H%M%S) tests/

# Run with listener
robot --listener listeners/HTMLReportListener.py tests/

# Run in dry-run mode (syntax check, no execution)
robot --dryrun tests/

# Run specific test suite file
robot tests/02_measurement/voltage_accuracy.robot

# Parallel execution with pabot
pabot --processes 4 tests/

# Generate combined report after pabot
rebot --outputdir results/ results/*/output.xml
```

---

## 8. Interview Q&A

**Q1: What is the difference between a keyword library with `scope=SUITE` vs `scope=GLOBAL`?**  
`scope=SUITE` creates one library instance per test suite — the `__init__` and `close()` run at Suite Setup/Teardown. This is ideal for libraries that hold hardware connections (BLE client, serial port) that should be shared within a suite but reset between suites. `scope=GLOBAL` creates one instance for the entire RF run — used when initialization is very expensive (e.g., flashing firmware) and should only happen once. `scope=TEST` (default) creates a fresh instance per test — safest but slowest; use it when tests must be completely isolated.

**Q2: How do you share variables between test cases in Robot Framework?**  
Three approaches: (1) Suite-level variables defined in `*** Variables ***` — visible to all tests in the suite, read-only by default; (2) `Set Suite Variable` keyword inside a test — sets a variable visible to all subsequent tests in the suite; (3) Resource files with `*** Variables ***` — shared across all suites that import the resource. For test-level isolation, always prefer `*** Variables ***` or function arguments over `Set Suite Variable`, which creates hidden state dependencies between tests.

**Q3: What is a Robot Framework listener and when would you use one?**  
A listener is a Python class with specific method signatures (e.g., `start_suite`, `end_test`, `log_message`) that RF calls at matching points in execution. Use cases: (1) Real-time reporting to a CI dashboard; (2) Automatic screenshot capture on failure; (3) Sending test results to JIRA or TestRail after each test; (4) Custom log filtering (hide sensitive data like passwords from logs). Listeners are registered with `--listener MyListener.py` and require no changes to the test suites.

**Q4: How do you implement retry logic in Robot Framework?**  
Use the built-in `Wait Until Keyword Succeeds` keyword: `Wait Until Keyword Succeeds  5x  2s  Read Measurement`. This retries the keyword up to 5 times with 2-second delay. For more complex retry logic, I wrap it in a custom resource keyword with logging on each attempt. For connection-related retries, I implement retry inside the Python keyword library itself (where I have full control over exception handling), so the RF layer sees a clean pass or fail.

**Q5: How do you handle test dependencies in RF — e.g., test B needs device paired from test A?**  
Best practice: avoid test dependencies entirely. Each test should set up its own preconditions in Test Setup or within the test. If setup is expensive (pairing takes 30 seconds), elevate it to Suite Setup so it runs once for the suite. Use Suite Variables to pass results (e.g., connection handle) from setup to tests. Never use `Set Suite Variable` inside a test to pass state to the next test — that creates ordering dependencies. If ordering is unavoidable, use the `--randomize` option to detect and expose hidden dependencies during development.
