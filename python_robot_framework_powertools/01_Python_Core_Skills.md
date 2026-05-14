# 01 — Python Core Skills for Test Automation

> **Topic**: Python stdlib, multithreading, file I/O, OOP, OS interaction, subprocess  
> **Role relevance**: Foundation for all test framework work — every script, library, and tool builds on these  
> **Outcome**: Write clean, efficient, maintainable Python for automation engineering

---

## 1. Python Standard Library Overview

```
Key standard library modules for test automation:
──────────────────────────────────────────────────────────────────────────
Category        Module(s)              Use Case
──────────────────────────────────────────────────────────────────────────
Threading       threading              Concurrent tasks (read BLE + send UART)
                concurrent.futures     Thread/process pools, futures
                queue                  Thread-safe data passing

File / Path     pathlib                Path manipulation (modern, OOP)
                os, os.path            Directory traversal, env vars
                shutil                 Copy, move, delete files/dirs
                tempfile               Temp dirs for test artifacts

Text / Data     json                   Config files, API responses
                csv                   Test data, measurement logs
                yaml (PyYAML)         Config files (pip install pyyaml)
                re                    Pattern matching in logs/output
                struct                Binary protocol parsing (UART frames)

Time            time                  Timestamps, sleep
                datetime              Log timestamps, duration
                timeit                Micro-benchmark test code

Network / IPC   socket                Raw TCP/UDP (can talk to test servers)
                subprocess            Launch tools, capture output

Logging         logging               Production-quality test logs
                logging.handlers      RotatingFileHandler for CI logs

Testing         unittest              Built-in test framework (RF uses it)
                unittest.mock         Mock hardware, fake BLE responses
──────────────────────────────────────────────────────────────────────────
```

---

## 2. Object-Oriented Design for Automation

Good OOP design makes frameworks maintainable and extensible:

### Class Structure for Device Interface
```python
"""
device_interface.py — Base class pattern for a testable device.
Single Responsibility: each class does one thing.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Value object — holds device identity, no behavior."""
    name:           str
    mac_address:    str
    firmware_ver:   str
    hardware_rev:   str
    serial_number:  str


class DeviceConnectionError(Exception):
    """Raised when connection to device cannot be established."""

class DeviceCommandError(Exception):
    """Raised when device returns unexpected response to a command."""


class BaseDevice(ABC):
    """
    Abstract base class for any testable device.
    All concrete device classes must implement these methods.
    """

    def __init__(self, device_id: str):
        self.device_id   = device_id
        self.connected   = False
        self._info: Optional[DeviceInfo] = None
        self.log = logging.getLogger(self.__class__.__name__)

    # ── Abstract interface (must implement) ───────────────────────────────
    @abstractmethod
    def connect(self) -> None:
        """Establish communication channel with device."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close communication channel cleanly."""

    @abstractmethod
    def send_command(self, cmd: bytes) -> bytes:
        """Send raw command bytes, return response bytes."""

    @abstractmethod
    def read_measurement(self) -> dict:
        """Read the current measurement from the device."""

    # ── Concrete helpers (shared by all subclasses) ────────────────────────
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False   # Don't suppress exceptions

    @property
    def info(self) -> Optional[DeviceInfo]:
        return self._info

    def require_connected(self):
        """Guard method — call at start of any method needing connection."""
        if not self.connected:
            raise DeviceConnectionError(
                f"{self.device_id} is not connected. Call connect() first."
            )

    def __repr__(self) -> str:
        status = "connected" if self.connected else "disconnected"
        return f"{self.__class__.__name__}(id={self.device_id!r}, {status})"
```

### Concrete Implementations
```python
"""
uart_device.py — Concrete UART device implementation.
"""
import serial
import time
from device_interface import BaseDevice, DeviceInfo, DeviceCommandError

class UARTDevice(BaseDevice):
    """
    Device communicating over UART / serial port.
    Example: Power tool with RS-232 debug interface.
    """

    DEFAULT_BAUD   = 115200
    RESPONSE_TIMEOUT = 2.0     # seconds
    FRAME_END      = b'\r\n'

    def __init__(self, device_id: str, port: str,
                 baud_rate: int = DEFAULT_BAUD):
        super().__init__(device_id)
        self.port      = port
        self.baud_rate = baud_rate
        self._serial: serial.Serial | None = None

    def connect(self) -> None:
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.RESPONSE_TIMEOUT,
            )
            self.connected = True
            self.log.info("Connected to %s at %d baud", self.port, self.baud_rate)
            self._info = self._read_device_info()
        except serial.SerialException as e:
            raise DeviceConnectionError(f"Cannot open {self.port}: {e}") from e

    def disconnect(self) -> None:
        if self._serial and self._serial.is_open:
            self._serial.close()
        self.connected = False
        self.log.info("Disconnected from %s", self.port)

    def send_command(self, cmd: bytes) -> bytes:
        self.require_connected()
        self._serial.reset_input_buffer()
        self._serial.write(cmd + self.FRAME_END)
        self._serial.flush()

        response = self._serial.read_until(self.FRAME_END)
        if not response:
            raise DeviceCommandError(
                f"No response to command {cmd!r} within {self.RESPONSE_TIMEOUT}s"
            )
        return response.strip()

    def read_measurement(self) -> dict:
        raw = self.send_command(b"READ_MEAS")
        # Example response: b"VOLT=12.34,CURR=1.56,TEMP=28.5"
        fields = {}
        for part in raw.decode().split(","):
            key, val = part.split("=")
            fields[key.strip()] = float(val.strip())
        return fields

    def _read_device_info(self) -> DeviceInfo:
        info_raw = self.send_command(b"GET_INFO").decode()
        # Example: "NAME=ToolX,MAC=AA:BB:CC:DD:EE:FF,FW=2.1.0,HW=Rev3,SN=12345"
        parts = dict(p.split("=") for p in info_raw.split(","))
        return DeviceInfo(
            name=parts["NAME"], mac_address=parts["MAC"],
            firmware_ver=parts["FW"], hardware_rev=parts["HW"],
            serial_number=parts["SN"],
        )
```

---

## 3. Multithreading for Test Automation

Concurrent operations are common in device testing: listening for notifications while sending commands.

### Threading Patterns
```python
"""
threading_patterns.py — Common patterns for concurrent device testing.
"""
import threading
import queue
import time
from typing import Callable

# ── Pattern 1: Producer-Consumer (device → log consumer) ─────────────────────
class DeviceLogMonitor:
    """
    Continuously reads device log in background thread.
    Test thread queries for specific log entries.
    """

    def __init__(self, device):
        self._device    = device
        self._queue     = queue.Queue(maxsize=1000)
        self._stop_evt  = threading.Event()
        self._thread    = threading.Thread(
            target=self._read_loop, name="LogMonitor", daemon=True
        )

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_evt.set()
        self._thread.join(timeout=2.0)

    def _read_loop(self):
        while not self._stop_evt.is_set():
            try:
                line = self._device.read_log_line(timeout=0.1)
                if line:
                    self._queue.put_nowait(line)
            except Exception:
                pass

    def wait_for_message(self, keyword: str, timeout: float = 5.0) -> str:
        """
        Block until a log line containing keyword is seen,
        or raise TimeoutError.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                line = self._queue.get(timeout=min(0.1, remaining))
                if keyword in line:
                    return line
            except queue.Empty:
                continue
        raise TimeoutError(
            f"Message containing {keyword!r} not seen within {timeout}s"
        )

    def drain(self) -> list[str]:
        """Get all accumulated log lines."""
        lines = []
        while not self._queue.empty():
            try:
                lines.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return lines


# ── Pattern 2: Thread pool for parallel device operations ──────────────────────
from concurrent.futures import ThreadPoolExecutor, as_completed

def test_multiple_devices_parallel(devices: list, test_fn: Callable) -> dict:
    """
    Run the same test function on multiple devices simultaneously.
    Returns {device_id: result_or_exception} dict.
    """
    results = {}
    with ThreadPoolExecutor(max_workers=len(devices)) as executor:
        future_to_device = {
            executor.submit(test_fn, dev): dev.device_id
            for dev in devices
        }
        for future in as_completed(future_to_device, timeout=60):
            dev_id = future_to_device[future]
            try:
                results[dev_id] = future.result()
            except Exception as e:
                results[dev_id] = e
    return results


# ── Pattern 3: Event-based synchronization ─────────────────────────────────────
class CommandResponseSynchronizer:
    """
    Coordinate: send command on thread A, wait for async response on thread B.
    Common for BLE where command and notification arrive on different events.
    """

    def __init__(self, timeout: float = 5.0):
        self._timeout  = timeout
        self._event    = threading.Event()
        self._response = None

    def notify(self, response):
        """Call this from the notification/callback thread."""
        self._response = response
        self._event.set()

    def wait(self):
        """Call this from the test thread after sending command."""
        if not self._event.wait(timeout=self._timeout):
            raise TimeoutError(f"No response within {self._timeout}s")
        return self._response
```

---

## 4. File I/O for Test Automation

### Reading & Writing Test Data
```python
"""
file_io_patterns.py — File I/O patterns used in test automation.
"""
import json
import csv
import yaml
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TestDataManager:
    """
    Manage test input data and output artifacts.
    All paths handled via pathlib (cross-platform, safe).
    """

    def __init__(self, base_dir: str):
        self.base     = Path(base_dir)
        self.data_dir = self.base / "test_data"
        self.logs_dir = self.base / "logs"
        self.reports  = self.base / "reports"

        # Ensure directories exist
        for d in [self.data_dir, self.logs_dir, self.reports]:
            d.mkdir(parents=True, exist_ok=True)

    # ── JSON config / expected results ────────────────────────────────────
    def load_config(self, name: str) -> dict:
        path = self.data_dir / f"{name}.json"
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def save_result(self, name: str, data: dict) -> Path:
        path = self.reports / f"{name}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("Saved result to %s", path)
        return path

    # ── CSV measurement logs ───────────────────────────────────────────────
    def write_measurement_log(self, name: str,
                              measurements: list[dict]) -> Path:
        if not measurements:
            return None
        path = self.logs_dir / f"{name}.csv"
        fieldnames = list(measurements[0].keys())
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(measurements)
        logger.info("Written %d rows to %s", len(measurements), path)
        return path

    def read_measurement_log(self, name: str) -> list[dict]:
        path = self.logs_dir / f"{name}.csv"
        with path.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))

    # ── YAML test configuration ────────────────────────────────────────────
    def load_yaml_config(self, name: str) -> dict:
        path = self.data_dir / f"{name}.yaml"
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)

    # ── Log file analysis ──────────────────────────────────────────────────
    def find_errors_in_log(self, log_file: str,
                           pattern: str = "ERROR") -> list[str]:
        """Search a log file for lines matching pattern."""
        import re
        path = self.logs_dir / log_file
        results = []
        regex = re.compile(pattern, re.IGNORECASE)
        with path.open(encoding="utf-8", errors="replace") as f:
            for lineno, line in enumerate(f, start=1):
                if regex.search(line):
                    results.append(f"Line {lineno}: {line.rstrip()}")
        return results
```

---

## 5. subprocess — Launching Tools and Capturing Output

```python
"""
subprocess_patterns.py — Safely run external commands from test scripts.
"""
import subprocess
import shlex
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def run_command(cmd: str | list,
                cwd: str = None,
                timeout: float = 60.0,
                check: bool = True) -> subprocess.CompletedProcess:
    """
    Run a shell command safely (no shell=True injection risk).
    Returns CompletedProcess with stdout, stderr, returncode.
    """
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)   # Split safely, handles quoted strings

    logger.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=timeout,
        check=False,   # We handle errors ourselves
    )

    if result.returncode != 0 and check:
        raise subprocess.CalledProcessError(
            result.returncode, cmd,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result


def flash_firmware(firmware_path: str, port: str) -> bool:
    """Flash firmware using external tool (e.g., bossac, openocd)."""
    firmware = Path(firmware_path)
    if not firmware.exists():
        raise FileNotFoundError(f"Firmware not found: {firmware}")

    result = run_command(
        ["bossac", "--port", port, "--write", str(firmware), "--verify"],
        timeout=120,
        check=False,
    )
    if result.returncode == 0:
        logger.info("Flash succeeded: %s", firmware.name)
        return True
    else:
        logger.error("Flash FAILED:\n%s", result.stderr)
        return False


def run_android_adb(args: list[str], timeout: float = 30.0) -> str:
    """Run adb command and return stdout text."""
    result = run_command(["adb"] + args, timeout=timeout, check=True)
    return result.stdout.strip()
```

---

## 6. Logging Best Practices

```python
"""
logging_setup.py — Production-quality logging for test automation.
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime


def setup_test_logging(log_dir: str = "logs",
                       log_level: int = logging.DEBUG) -> logging.Logger:
    """
    Configure root logger with:
      - Console: INFO level (human-readable)
      - Rotating file: DEBUG level (full detail for CI)
    """
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file   = log_path / f"test_run_{timestamp}.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Console handler (INFO — clean output)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))

    # Rotating file handler (DEBUG — full detail)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5, encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s [%(filename)s:%(lineno)d]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    root.addHandler(console)
    root.addHandler(file_handler)

    return root
```

---

## 7. Binary Data Parsing with struct

UART protocols often use binary frames that need `struct` for parsing:

```python
"""
binary_protocol.py — Parse binary frames from embedded devices.
"""
import struct
from dataclasses import dataclass

# Example: Power tool status frame
# Byte layout:
#  [0]   : Start byte (0xAA)
#  [1]   : Command ID (uint8)
#  [2-3] : Payload length (uint16 LE)
#  [4-5] : Voltage mV (uint16 LE)
#  [6-7] : Current mA (int16 LE, signed)
#  [8-9] : Temperature centi-°C (int16 LE)
#  [10]  : Status flags (uint8)
#  [11]  : Checksum (XOR of bytes 1–10)

FRAME_FORMAT  = "<BHHhHB"   # little-endian: u8, u16, u16, s16, u16, u8
HEADER_BYTE   = 0xAA
FRAME_SIZE    = 12          # bytes

@dataclass
class ToolStatusFrame:
    command_id:     int
    voltage_mv:     int
    current_ma:     int
    temperature_dc: int     # deci-celsius: 285 = 28.5°C
    flags:          int

    @property
    def voltage_v(self) -> float:
        return self.voltage_mv / 1000.0

    @property
    def current_a(self) -> float:
        return self.current_ma / 1000.0

    @property
    def temperature_c(self) -> float:
        return self.temperature_dc / 10.0

    @property
    def is_charging(self) -> bool:
        return bool(self.flags & 0x01)

    @property
    def motor_running(self) -> bool:
        return bool(self.flags & 0x02)

    @property
    def fault_active(self) -> bool:
        return bool(self.flags & 0x04)


def parse_status_frame(data: bytes) -> ToolStatusFrame:
    """Parse raw bytes into ToolStatusFrame."""
    if len(data) != FRAME_SIZE:
        raise ValueError(f"Expected {FRAME_SIZE} bytes, got {len(data)}")

    if data[0] != HEADER_BYTE:
        raise ValueError(f"Invalid start byte: 0x{data[0]:02X}")

    # Verify checksum (XOR of bytes 1–10)
    expected_csum = 0
    for b in data[1:11]:
        expected_csum ^= b
    if expected_csum != data[11]:
        raise ValueError(
            f"Checksum mismatch: expected 0x{expected_csum:02X}, "
            f"got 0x{data[11]:02X}"
        )

    # Unpack payload (bytes 1–10)
    cmd_id, payload_len, voltage_mv, current_ma, temp_dc, flags = \
        struct.unpack(FRAME_FORMAT, data[1:11])

    return ToolStatusFrame(
        command_id=cmd_id,
        voltage_mv=voltage_mv,
        current_ma=current_ma,
        temperature_dc=temp_dc,
        flags=flags,
    )


def build_command_frame(cmd_id: int, payload: bytes = b"") -> bytes:
    """Build a command frame to send to the device."""
    header = bytes([HEADER_BYTE, cmd_id])
    length = struct.pack("<H", len(payload))
    body   = header + length + payload
    csum   = 0
    for b in body[1:]:
        csum ^= b
    return body + bytes([csum])
```

---

## 8. Mock Objects for Unit Testing Framework Code

```python
"""
mock_patterns.py — Using unittest.mock to test automation framework code.
"""
from unittest.mock import MagicMock, patch, PropertyMock
import pytest

from uart_device import UARTDevice


def test_send_command_calls_serial_write():
    """Unit test: send_command() writes correct bytes to serial port."""
    device = UARTDevice("test-device", port="/dev/ttyUSB0")
    device.connected = True   # bypass connection check

    # Create a mock serial port
    mock_serial = MagicMock()
    mock_serial.read_until.return_value = b"OK\r\n"
    device._serial = mock_serial

    result = device.send_command(b"GET_STATUS")

    # Verify write was called with correct data
    mock_serial.write.assert_called_once_with(b"GET_STATUS\r\n")
    assert result == b"OK"


def test_send_command_raises_on_no_response():
    """send_command() raises DeviceCommandError when serial times out."""
    from device_interface import DeviceCommandError

    device = UARTDevice("test-device", port="/dev/ttyUSB0")
    device.connected = True

    mock_serial = MagicMock()
    mock_serial.read_until.return_value = b""   # empty = timeout
    device._serial = mock_serial

    with pytest.raises(DeviceCommandError, match="No response"):
        device.send_command(b"GET_STATUS")


@patch("serial.Serial")
def test_connect_opens_correct_port(mock_serial_cls):
    """connect() opens the specified COM port with correct baud rate."""
    mock_instance = MagicMock()
    mock_serial_cls.return_value = mock_instance
    mock_instance.read_until.return_value = (
        b"NAME=ToolX,MAC=AA:BB:CC:DD:EE:FF,FW=2.1.0,HW=Rev3,SN=12345\r\n"
    )

    device = UARTDevice("d1", port="COM3", baud_rate=115200)
    device.connect()

    mock_serial_cls.assert_called_once()
    call_kwargs = mock_serial_cls.call_args.kwargs
    assert call_kwargs["port"] == "COM3"
    assert call_kwargs["baudrate"] == 115200
    assert device.connected is True
```

---

## 9. Interview Q&A

**Q1: What is the difference between threading and multiprocessing in Python, and when do you use each in automation?**  
Threading uses OS threads sharing the same memory — ideal for I/O-bound tasks (reading BLE notifications, waiting for serial responses) because threads release the GIL during I/O. Multiprocessing uses separate processes with separate memory — ideal for CPU-bound tasks (signal processing, log analysis, running multiple CarMaker instances). In device testing, I use threading for concurrent read/write on a single device and multiprocessing for running tests on multiple independent devices in parallel.

**Q2: Explain the difference between `abstract method` and a normal method in a base class. Why does it matter for framework design?**  
An abstract method (decorated with `@abstractmethod`) has no implementation in the base class and forces every concrete subclass to provide one. If a subclass doesn't implement it, Python raises `TypeError` at instantiation time. This is a compile-time (import-time) contract: if I add a new abstract method to `BaseDevice`, every concrete device class (BLE, UART, USB) immediately gets a type error until it implements the method. This prevents missing implementations from hiding silently.

**Q3: How do you safely parse binary data from an embedded device over UART?**  
I use Python's `struct.unpack()` with the correct format string — specifying endianness (little-endian `<` vs big-endian `>`), signedness, and data types. I validate: (1) frame length is exactly expected, (2) start/end bytes match the protocol spec, (3) checksum matches. I raise a specific exception on validation failure so the test can distinguish a communication error from a DUT functional failure. The `@dataclass` pattern provides typed access to decoded fields with unit conversion properties.

**Q4: Why avoid `shell=True` in subprocess calls?**  
`shell=True` passes the command string through the OS shell, making it vulnerable to shell injection if any part of the command comes from test data or external input. For example: `subprocess.run(f"bossac --port {port}", shell=True)` — if `port` contains `; rm -rf /`, the shell executes it. Using `shell=False` (default) with a list argument means each element is a separate argument, passed directly to `execv()` with no shell interpretation. Always use `shlex.split()` to convert a string to a safe argument list.

**Q5: What is the purpose of `queue.Queue` in a multithreaded test framework?**  
`queue.Queue` is a thread-safe FIFO buffer for passing data between threads. In device testing, the log monitor thread continuously reads from the device and puts lines into a `Queue`. The test thread calls `queue.get(timeout=5.0)` to wait for a specific message. This decouples the reader from the consumer: the reader never blocks waiting for the test to process a message, and the test never misses a message that arrived before it started waiting. Without a queue, you'd need locks and shared lists, which are error-prone.
