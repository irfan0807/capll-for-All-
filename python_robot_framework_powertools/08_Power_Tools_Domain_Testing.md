# 08 — Power Tools Domain Testing

> **Topic**: Power tool product architecture, BLE-connected tools, measuring instrument validation, real-time testing  
> **Role relevance**: Domain expertise required to design meaningful tests for physical products with firmware + connectivity  
> **Outcome**: Test connected power tools end-to-end — from BLE measurement accuracy to mobile app integration and production validation

---

## 1. Power Tool Product Categories

```
Product Taxonomy:
──────────────────────────────────────────────────────────────────────────
Cordless Power Tools (motors, high current)
  ├── Drills / Impact Drivers      (motor control, torque feedback)
  ├── Circular Saws / Reciprocating Saws (blade speed, overload detect)
  ├── Angle Grinders               (RPM stability, thermal protection)
  └── Screwdrivers                 (torque limiter, clutch setting)

Measuring / Diagnostic Tools
  ├── Laser Distance Meters        (time-of-flight, accuracy ±1.5mm)
  ├── Digital Multimeters          (voltage, current, resistance, diode)
  ├── Thermal Imaging Cameras      (FLIR sensor, temperature accuracy)
  ├── Tiling Lasers / Level Tools  (self-leveling, angle accuracy)
  └── Clamp Meters / Energy Loggers (AC/DC current, power factor)

Smart / Connected Tools
  ├── BLE-connected (bleak, GATT)  (this course focus)
  ├── USB-connected (HID/CDC)      (direct data stream)
  └── Cloud-connected (via app)    (data upload, firmware OTA)

Key Firmware Functions to Test:
  - Measurement acquisition (ADC, sensor driver)
  - BLE GATT server (characteristic read/notify)
  - Safety shutdown (overvoltage, overcurrent, overheat)
  - Firmware update (OTA, UART bootloader)
  - NVM storage (calibration, settings, measurement history)
──────────────────────────────────────────────────────────────────────────
```

---

## 2. Smart Tool System Architecture

```
BLE Smart Tool — Full System:
──────────────────────────────────────────────────────────────────────────

  Physical Layer (Hardware)
    │
    ├── Sensors: ADC, MEMS, IR, Laser, Thermistor
    ├── MCU: ARM Cortex-M4, runs FreeRTOS
    ├── BLE SoC: nRF52840 (integrated BLE 5.2)
    ├── Battery: 18V Li-Ion pack, 2-3Ah
    └── Display: E-ink or small OLED (if present)
    │
    ▼
  Firmware (Embedded C / C++)
    ├── Measurement Task (100Hz)      → ADC read, filter, calibrate
    ├── BLE Task (event-driven)       → GATT server, notify, command handler
    ├── Safety Monitor (10Hz)         → Overvoltage, overtemp, overcurrent
    ├── NVM Manager                   → Save/load calibration, history
    └── OTA Manager                   → Receive firmware chunks, verify, boot
    │
    ▼
  BLE GATT Profile (over-the-air interface)
    ├── Service: Device Information   → FW version, serial, model
    ├── Service: Battery              → Level%, charging status
    ├── Service: Measurement          → Voltage, current, temp (notify)
    ├── Service: Control              → Mode, range, trigger (write)
    └── Service: Diagnostics          → Fault codes, self-test (read/write)
    │
    ▼
  Mobile App / Test Framework (this course = test side)
    ├── bleak BLE client              → Connects, reads, writes, subscribes
    ├── pytest / Robot Framework      → Automates test scenarios
    └── Jenkins / Azure DevOps        → CI/CD pipeline

  Cloud (for production use, not usually tested by embedded team)
    ├── AWS IoT / Azure IoT Hub       → Telemetry ingestion
    ├── OTA delivery service          → Push FW updates
    └── Data dashboard                → User measurement history
──────────────────────────────────────────────────────────────────────────
```

---

## 3. Measuring Tool Validation

### Accuracy Testing — Laser Distance Meter

```python
"""
laser_distance_tests.py — Accuracy validation for laser distance meter.

Test method:
  - Use certified calibration bar (known distances: 1m, 2m, 5m, 10m, 20m)
  - Each measurement averaged over N readings
  - Compare to certified reference (traceable to national standard)
"""
import pytest
import statistics


ACCURACY_SPEC = {
    "range_m":       (0.05, 30.0),       # measurement range
    "accuracy_mm":   1.5,                 # ±1.5mm absolute
    "accuracy_pct":  0.05,                # ±0.05% of reading (whichever greater)
    "repeatability_mm": 0.5,             # max std dev over 10 readings
    "min_samples":   10,                  # readings per reference point
}

REFERENCE_DISTANCES_M = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]


@pytest.mark.accuracy
@pytest.mark.parametrize("ref_dist_m", REFERENCE_DISTANCES_M,
                          ids=[f"{d}m" for d in REFERENCE_DISTANCES_M])
def test_laser_distance_accuracy(ref_dist_m, ble_device):
    """
    Validate absolute accuracy at each reference distance.
    Device must be placed at certified calibration bar position.
    """
    readings = []
    for _ in range(ACCURACY_SPEC["min_samples"]):
        ble_device.motor.trigger_measurement()    # simulate trigger press
        import time; time.sleep(0.2)
        val = ble_device.measurement.read_distance_m()
        readings.append(val)

    mean  = statistics.mean(readings)
    stdev = statistics.stdev(readings)

    # Check repeatability
    assert stdev * 1000 <= ACCURACY_SPEC["repeatability_mm"], \
        f"Repeatability {stdev*1000:.3f}mm > {ACCURACY_SPEC['repeatability_mm']}mm at {ref_dist_m}m"

    # Check accuracy — spec says ±1.5mm OR ±0.05%, whichever greater
    allowed_mm = max(
        ACCURACY_SPEC["accuracy_mm"],
        ref_dist_m * 1000 * ACCURACY_SPEC["accuracy_pct"] / 100
    )
    error_mm = abs(mean - ref_dist_m) * 1000
    assert error_mm <= allowed_mm, \
        f"Accuracy {error_mm:.3f}mm > allowed {allowed_mm:.3f}mm at {ref_dist_m}m"


@pytest.mark.accuracy
def test_laser_min_max_range(ble_device):
    """Verify device measures at minimum (50cm) and maximum (30m) spec range."""
    for ref_dist_m in [0.5, 30.0]:
        ble_device.motor.trigger_measurement()
        import time; time.sleep(0.2)
        reading = ble_device.measurement.read_distance_m()

        assert 0.05 < reading < 31.0, \
            f"Out-of-range reading {reading}m at reference {ref_dist_m}m"
```

### Digital Multimeter Validation

```python
"""
multimeter_tests.py — Accuracy tests for BLE-connected digital multimeter.

Test equipment required:
  - Calibration source (Fluke 5522A or similar) for DC/AC voltage, current
  - Precision resistor decade box for resistance
  - Reference thermometer for temperature
"""
import pytest
from dataclasses import dataclass

@dataclass
class MeterTestPoint:
    mode: str          # DC_VOLTAGE, AC_VOLTAGE, DC_CURRENT, RESISTANCE
    range: str         # AUTO or specific range string
    reference: float   # True value from calibration source
    tolerance_pct: float
    tolerance_abs: float  # Absolute tolerance (for near-zero readings)


VOLTAGE_TEST_POINTS = [
    MeterTestPoint("DC_VOLTAGE", "AUTO", 1.000,  0.5, 0.001),
    MeterTestPoint("DC_VOLTAGE", "AUTO", 10.000, 0.5, 0.001),
    MeterTestPoint("DC_VOLTAGE", "AUTO", 100.00, 0.5, 0.01),
    MeterTestPoint("DC_VOLTAGE", "AUTO", -10.00, 0.5, 0.001),
    MeterTestPoint("DC_VOLTAGE", "AUTO", 0.001,  0.5, 0.0001),  # Near zero
]

RESISTANCE_TEST_POINTS = [
    MeterTestPoint("RESISTANCE", "AUTO", 100.0,    0.5, 0.1),
    MeterTestPoint("RESISTANCE", "AUTO", 10000.0,  0.5, 1.0),
    MeterTestPoint("RESISTANCE", "AUTO", 1000000.0, 1.0, 100.0),
]


@pytest.mark.parametrize("tp", VOLTAGE_TEST_POINTS,
                          ids=[f"DC_{tp.reference}V" for tp in VOLTAGE_TEST_POINTS])
def test_dc_voltage_accuracy(tp, ble_device):
    """Validate DC voltage accuracy across the measurement range."""
    ble_device.measurement.set_mode(tp.mode)
    import time; time.sleep(0.1)

    reading = ble_device.measurement.read_voltage()

    # Tolerance: spec% OR absolute, whichever greater
    tolerance = max(abs(tp.reference) * tp.tolerance_pct / 100,
                    tp.tolerance_abs)
    error = abs(reading - tp.reference)

    assert error <= tolerance, (
        f"DC voltage accuracy fail at {tp.reference}V: "
        f"read={reading:.6f}V, error={error:.6f}V, tolerance={tolerance:.6f}V"
    )
```

---

## 4. Real-Time Feature Testing

### BLE Notification Latency
```python
"""
real_time_tests.py — Validate real-time response characteristics.
"""
import asyncio
import time
import statistics
import pytest

LATENCY_SPEC_MS = 150   # Max acceptable trigger-to-notification latency
RATE_SPEC_HZ    = 10.0  # Min acceptable notification rate (normal mode)
RATE_TOL_PCT    = 10.0  # ±10% rate tolerance


@pytest.mark.asyncio
async def test_notification_rate_normal_mode(ble_async_client):
    """Verify BLE notification rate is 10 Hz ±10% in normal mode."""
    timestamps = []
    collected_event = asyncio.Event()
    N = 50  # Collect 50 notifications for accurate rate estimate

    def on_notification(sender, data):
        timestamps.append(time.monotonic())
        if len(timestamps) >= N:
            collected_event.set()

    await ble_async_client.subscribe_voltage_notifications(on_notification)
    await ble_async_client.set_measurement_mode("normal")

    # Wait up to 10 seconds for N notifications
    try:
        await asyncio.wait_for(collected_event.wait(), timeout=10.0)
    except asyncio.TimeoutError:
        pytest.fail(f"Only received {len(timestamps)}/{N} notifications in 10s")

    # Calculate rate from intervals
    intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
    mean_interval_ms = statistics.mean(intervals) * 1000
    actual_rate_hz   = 1000.0 / mean_interval_ms

    expected_min = RATE_SPEC_HZ * (1 - RATE_TOL_PCT / 100)
    expected_max = RATE_SPEC_HZ * (1 + RATE_TOL_PCT / 100)

    assert expected_min <= actual_rate_hz <= expected_max, (
        f"Notification rate {actual_rate_hz:.2f} Hz out of range "
        f"[{expected_min:.1f}, {expected_max:.1f}] Hz. "
        f"Mean interval: {mean_interval_ms:.1f}ms"
    )


@pytest.mark.asyncio
async def test_trigger_to_notification_latency(ble_async_client):
    """
    Measure latency from trigger command to first measurement notification.

    Method: Send trigger command, record t0.
    Next notification received = t1.
    Latency = t1 - t0.
    """
    latencies_ms = []

    for _ in range(10):
        received_event = asyncio.Event()
        receive_time   = [None]

        def on_first_notification(sender, data):
            receive_time[0] = time.monotonic()
            received_event.set()

        await ble_async_client.subscribe_voltage_notifications(on_first_notification)
        await ble_async_client.set_measurement_mode("idle")   # Stop stream
        await asyncio.sleep(0.2)                              # Let it quiet

        t0 = time.monotonic()
        await ble_async_client.set_measurement_mode("normal")  # Start stream

        await asyncio.wait_for(received_event.wait(), timeout=2.0)
        latency_ms = (receive_time[0] - t0) * 1000
        latencies_ms.append(latency_ms)

        await ble_async_client.unsubscribe_voltage_notifications()
        await asyncio.sleep(0.1)

    max_latency = max(latencies_ms)
    p95_latency = sorted(latencies_ms)[int(0.95 * len(latencies_ms))]

    assert max_latency <= LATENCY_SPEC_MS, \
        f"Max latency {max_latency:.1f}ms exceeds {LATENCY_SPEC_MS}ms. " \
        f"All values: {[f'{l:.0f}' for l in latencies_ms]}"
```

---

## 5. Device Lifecycle Testing

```python
"""
lifecycle_tests.py — Power on/off sequences, battery states, device restart.
"""
import pytest
import time


class TestDevicePowerCycle:
    """Test device lifecycle state transitions."""

    def test_power_on_initializes_correctly(self, ble_device):
        """After power on, device advertises and accepts connection within spec."""
        # (Hardware fixture already powered on and connected)
        # Verify all expected characteristics are present
        ble_device.battery.get_level()
        ble_device.measurement.read_voltage()
        diagnostics = ble_device.diagnostics.get_active_faults()
        assert diagnostics == [], \
            f"Unexpected faults after clean power on: {diagnostics}"

    def test_self_test_passes_after_cold_start(self, ble_device):
        """Built-in self-test reports all-pass after power cycle."""
        result = ble_device.diagnostics.run_self_test()
        assert result["passed"], \
            f"Self-test failed: {result['details']}"

    def test_measurement_stable_after_warmup(self, ble_device):
        """Measurements are stable within 5 seconds of power on."""
        readings = []
        for _ in range(10):
            readings.append(ble_device.measurement.read_voltage())
            time.sleep(0.5)

        import statistics
        stdev = statistics.stdev(readings)
        assert stdev < 0.05, \
            f"Voltage unstable during warmup: stdev={stdev:.4f}V, readings={readings}"

    def test_reconnect_after_ble_disconnect(self, ble_raw_client, ble_device_addr):
        """Device accepts re-connection within 5 seconds of previous disconnect."""
        import time
        from ble_client import PowerToolBLEClientSync

        # Connect, verify, disconnect
        client1 = PowerToolBLEClientSync(ble_device_addr)
        with client1:
            level = client1.read_battery_level()
            assert 0 <= level <= 100

        # Wait 1 second (simulate app backgrounding)
        time.sleep(1.0)

        # Re-connect — must succeed within 5s
        t0 = time.monotonic()
        client2 = PowerToolBLEClientSync(ble_device_addr)
        with client2:
            level2 = client2.read_battery_level()
            reconnect_time = time.monotonic() - t0
            assert 0 <= level2 <= 100
            assert reconnect_time < 5.0, \
                f"Re-connection took {reconnect_time:.2f}s (max 5.0s)"


class TestBatteryStates:
    """Verify device behavior in different battery states."""

    @pytest.mark.parametrize("level,expected_mode", [
        (100, "full"),
        (50,  "normal"),
        (20,  "low"),
        (10,  "critical"),
    ])
    def test_battery_level_state(self, level, expected_mode, ble_device, mock_battery):
        """Device reports correct operating mode at each battery level."""
        mock_battery.set_level(level)
        reported_mode = ble_device.battery.get_operating_mode()
        assert reported_mode == expected_mode, \
            f"At {level}% battery, expected mode={expected_mode!r}, got={reported_mode!r}"

    def test_low_battery_reduces_notification_rate(self, ble_device, mock_battery):
        """At battery ≤ 20%, notification rate drops to 2 Hz for power saving."""
        mock_battery.set_level(15)  # Set to critical
        time.sleep(0.5)

        timestamps = []
        for _ in range(20):
            timestamps.append(time.monotonic())
            time.sleep(0.05)
            ble_device.measurement.read_voltage()

        # Rate check logic (simplified — real test uses notification timestamps)
        # Actual test would use on_notification callback
```

---

## 6. Firmware Update (OTA) Testing

```python
"""
ota_tests.py — Firmware OTA update validation.
"""
import pytest
import time
from pathlib import Path


class TestFirmwareUpdate:
    """Validate OTA firmware update process end-to-end."""

    def test_ota_completes_successfully(self, ble_device,
                                        fw_images, uart_device):
        """OTA update from current to latest FW completes without error."""
        baseline_version = ble_device.firmware.get_version()

        # Initiate OTA update (sends FW image over BLE OTA characteristic)
        ble_device.firmware.start_ota_update(fw_images["latest"])

        # Poll until complete or timeout (max 3 minutes)
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            status = ble_device.firmware.get_ota_status()
            if status["state"] == "completed":
                break
            if status["state"] == "error":
                pytest.fail(f"OTA failed: {status['error_code']}")
            time.sleep(2.0)
        else:
            pytest.fail("OTA timed out after 180 seconds")

        # Device reboots — wait for reconnection
        time.sleep(5.0)
        ble_device.reconnect(timeout_s=30)

        new_version = ble_device.firmware.get_version()
        assert new_version == fw_images["latest"].version, \
            f"After OTA, version={new_version!r}, expected={fw_images['latest'].version!r}"

        # Verify device functional after update
        assert ble_device.diagnostics.run_self_test()["passed"], \
            "Self-test failed after OTA update"

    def test_ota_rollback_on_invalid_image(self, ble_device, fw_images):
        """Invalid FW image (bad CRC) is rejected; device stays on current FW."""
        original_version = ble_device.firmware.get_version()

        result = ble_device.firmware.start_ota_update(fw_images["corrupt"])
        # Expect rejection, not crash
        assert result["accepted"] is False, \
            "Device accepted corrupt firmware image — should have been rejected"

        # Verify version unchanged
        assert ble_device.firmware.get_version() == original_version, \
            "FW version changed after rejected OTA attempt"

    def test_ota_power_cut_recovery(self, ble_device, fw_images, relay):
        """Cut power during OTA at 50% progress — device boots back to old FW."""
        original_version = ble_device.firmware.get_version()
        ble_device.firmware.start_ota_update(fw_images["latest"],
                                              async_mode=True)

        # Wait until ~50% progress, then cut power
        for _ in range(30):
            status = ble_device.firmware.get_ota_status()
            if status["progress_pct"] >= 50:
                break
            time.sleep(1.0)

        relay.cut_power()
        time.sleep(2.0)
        relay.restore_power()
        time.sleep(10.0)

        ble_device.reconnect(timeout_s=30)
        post_version = ble_device.firmware.get_version()

        assert post_version == original_version, \
            f"After power-cut OTA, device on wrong FW: {post_version!r}"
        assert ble_device.diagnostics.run_self_test()["passed"], \
            "Self-test failed after power-cut recovery"
```

---

## 7. Regression Test Strategy

```
Regression Pyramid for Power Tool Testing:
──────────────────────────────────────────────────────────────────────────

              ┌─────────────────────────┐
              │      Full Suite          │  4 hours
              │   250+ test cases        │  All HW required
              │   BLE + UART + OTA       │  Run: nightly
              │   Accuracy + lifecycle   │
              └─────────────────────────┘
         ┌───────────────────────────────────┐
         │        Integration Suite           │  1 hour
         │   100 test cases                   │  1 device bench
         │   BLE measurement accuracy         │  Run: on merge to main
         │   UART command/response             │
         │   OTA happy path                   │
         └───────────────────────────────────┘
    ┌─────────────────────────────────────────────┐
    │             Smoke Suite                      │  5 minutes
    │   20 test cases                              │  Any connected device
    │   BLE connect/disconnect                     │  Run: on every commit
    │   Battery level read                         │
    │   Single voltage/current reading             │
    │   Firmware version check                     │
    │   Basic self-test pass                       │
    └─────────────────────────────────────────────┘
    ┌─────────────────────────────────────────────────────┐
    │          Unit Tests (no hardware)                    │  30 seconds
    │   50+ test cases                                    │  Mock only
    │   Frame parsing, assertions, config loading         │  Run: on every commit
    │   JIRA client, data loaders, strategy patterns      │
    └─────────────────────────────────────────────────────┘
──────────────────────────────────────────────────────────────────────────

pytest markers in pytest.ini:
  [markers]
  smoke:        "5-minute smoke suite — run on every commit"
  integration:  "1-hour integration suite — run on merge"
  regression:   "Full nightly regression suite"
  accuracy:     "Measurement accuracy tests — requires calibrated source"
  ble:          "BLE hardware required"
  uart:         "UART hardware required"
  slow:         "Tests that take > 60 seconds"
  ota:          "Tests that reflash firmware"

CI triggers:
  On commit:   pytest -m "smoke and not hardware"   (mocks only)
  On PR merge: pytest -m "integration" --device-config ci_bench.yaml
  Nightly:     pytest -m "regression" --device-config lab_bench.yaml
```

---

## 8. Production Validation Pattern

```python
"""
production_validation.py — Factory floor test sequence for power tools.
Quick go/no-go test: device passes before shipping.
Target time: < 60 seconds per unit.
"""
import time
import json
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ProductionTestResult:
    serial_number:   str
    fw_version:      str
    timestamp:       str
    pass_fail:       str          # PASS / FAIL
    failed_steps:    list[str]
    voltage_v:       float = 0.0
    current_a:       float = 0.0
    battery_level:   int   = 0
    ble_rssi_dbm:    int   = 0
    self_test_pass:  bool  = False


def run_production_test(device_config: dict) -> ProductionTestResult:
    """
    End-to-end production test. Called by factory test runner.
    Returns structured result for serialization to DB / label printer.
    """
    from device_model import PowerToolDevice
    from factory import DeviceFactory

    result = ProductionTestResult(
        serial_number=device_config["serial"],
        fw_version="",
        timestamp=datetime.utcnow().isoformat(),
        pass_fail="FAIL",
        failed_steps=[],
    )

    try:
        with DeviceFactory.from_config(device_config["config_path"]) as device:
            # Step 1: FW version check
            result.fw_version = device.firmware.get_version()
            if result.fw_version != device_config["expected_fw"]:
                result.failed_steps.append(
                    f"FW_VERSION: got {result.fw_version!r}, "
                    f"expected {device_config['expected_fw']!r}"
                )

            # Step 2: Self-test
            st = device.diagnostics.run_self_test()
            result.self_test_pass = st["passed"]
            if not st["passed"]:
                result.failed_steps.append(f"SELF_TEST: {st['details']}")

            # Step 3: Battery level
            result.battery_level = device.battery.get_level()
            if result.battery_level < device_config.get("min_battery_pct", 10):
                result.failed_steps.append(
                    f"BATTERY: {result.battery_level}% < minimum"
                )

            # Step 4: Voltage measurement sanity check
            result.voltage_v = device.measurement.read_voltage()
            expected_v  = device_config.get("ref_voltage_v", 12.0)
            tolerance_v = device_config.get("voltage_tol_v", 0.5)
            if abs(result.voltage_v - expected_v) > tolerance_v:
                result.failed_steps.append(
                    f"VOLTAGE: {result.voltage_v:.3f}V "
                    f"vs expected {expected_v}±{tolerance_v}V"
                )

            # Step 5: No active faults
            faults = device.diagnostics.get_active_faults()
            if faults:
                result.failed_steps.append(f"FAULTS: {faults}")

    except Exception as e:
        result.failed_steps.append(f"EXCEPTION: {type(e).__name__}: {e}")

    result.pass_fail = "PASS" if not result.failed_steps else "FAIL"
    return result


def save_production_result(result: ProductionTestResult,
                            output_path: str) -> None:
    """Append result to JSONL log file for each unit tested."""
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(result)) + "\n")
```

---

## 9. RF Test Suite Example

```robotframework
*** Settings ***
Documentation    Power Tool BLE Integration — Smoke Suite
Library          BLELibrary
Library          MeasurementLibrary
Resource         keywords/measurement_keywords.resource
Suite Setup      Connect To Power Tool    ${DEVICE_NAME}
Suite Teardown   Disconnect From Power Tool

*** Variables ***
${DEVICE_NAME}      PowerTool-X1
${REF_VOLTAGE}      12.0
${VOLTAGE_TOL}      0.5

*** Test Cases ***
TC-SMOKE-001 BLE Connection Established
    [Tags]    smoke    ble
    Device Should Be Connected
    Battery Level Should Be Valid

TC-SMOKE-002 Firmware Version Matches Expected
    [Tags]    smoke
    ${version}=    Get Firmware Version
    Should Match Regexp    ${version}    ^\\d+\\.\\d+\\.\\d+(-\\S+)?$

TC-SMOKE-003 Self Test Passes
    [Tags]    smoke
    ${result}=    Run Self Test
    Should Be True    ${result}[passed]    Self test failed: ${result}[details]

TC-SMOKE-004 Voltage Reading In Range
    [Tags]    smoke    accuracy
    ${voltage}=    Read Voltage
    Voltage Should Be Within Tolerance    ${voltage}    ${REF_VOLTAGE}    ${VOLTAGE_TOL}

TC-SMOKE-005 No Active Faults After Connect
    [Tags]    smoke
    ${faults}=    Get Active Faults
    Length Should Be    ${faults}    0    Active faults found: ${faults}

*** Keywords ***
Device Should Be Connected
    ${connected}=    Is Connected
    Should Be True    ${connected}    Device not connected

Battery Level Should Be Valid
    ${level}=    Read Battery Level
    Should Be True    0 <= ${level} <= 100    Battery level ${level}% out of range
```

---

## 10. Interview Q&A

**Q1: How do you validate measurement accuracy for a BLE-connected digital multimeter?**  
I use a traceable calibration source (e.g., Fluke 5522A) that generates certified reference values. The test framework puts the meter in each mode (DC voltage, AC current, resistance) and injects reference values from the calibration source. BLE reads the displayed value and compares it to the certified reference. Tolerance is calculated as the greater of absolute spec or percentage spec (e.g., ±1.5mm OR ±0.05%, whichever is larger). Tests cover the full measurement range, boundaries, near-zero, and negative values. Results are logged with uncertainty budget for compliance documentation.

**Q2: What is the difference between smoke, integration, and regression test suites for an embedded product?**  
**Smoke**: 20 tests, 5 minutes, any connected device — verifies the device is basically alive (connects, responds, no faults). Run on every commit. **Integration**: 100 tests, 1 hour — validates feature areas (BLE accuracy, UART protocol, OTA happy path). Run on merge to main. **Regression**: 250+ tests, 4 hours — validates everything including edge cases, lifecycle, accuracy across the full spec range. Run nightly on a dedicated hardware bench. This pyramid ensures fast feedback for developers while guaranteeing thorough coverage before release.

**Q3: How do you test BLE notification latency and rate?**  
For **rate**: subscribe to the notification characteristic, collect 50 timestamps, compute mean interval and convert to Hz, compare to spec. For **latency** (trigger-to-notification): record `t0` just before sending the trigger command, record `t1` when the first notification arrives via callback, latency = `t1 - t0`. Run 10 iterations and check max and p95 against spec. I use `asyncio` with `bleak` for precise timing — synchronous polling with `sleep` introduces artificial latency that masks real behavior.

**Q4: How do you test that a firmware OTA update is robust against power cuts?**  
I use a programmable relay to cut power to the device. The test: (1) Start OTA update; (2) Monitor progress percentage; (3) Cut power at ~50% — mid-transfer; (4) Restore power after 2 seconds; (5) Wait for device to reconnect; (6) Verify device is still on the original FW version (bootloader rolled back). This validates the device's dual-bank flash with CRC verification — a valid anti-brick mechanism. Additional cut points to test: just before commit, just after commit begins, during boot after successful OTA.

**Q5: How do you design a production validation test for a factory floor?**  
Production tests must be fast (< 60s/unit), deterministic, and produce a traceable result. My pattern: (1) Connect via BLE to freshly-assembled unit by serial number; (2) Verify FW version matches production build; (3) Run built-in self-test; (4) Verify measurement reading is within ±spec against known reference; (5) Check no active fault codes; (6) Write PASS/FAIL with all readings to JSONL log and optionally trigger label printer. If any step fails, record which step and the actual value. The log file becomes the manufacturing quality record. I also add a timeout on each step so a hung device doesn't block the production line.
