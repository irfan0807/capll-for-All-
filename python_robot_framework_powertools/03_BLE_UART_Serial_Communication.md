# 03 — BLE, UART & Serial Communication

> **Topic**: Bluetooth Low Energy (GAP/GATT), bleak library, pyserial, protocol testing, real-time validation  
> **Role relevance**: Core domain — power tools communicate over BLE and UART  
> **Outcome**: Implement robust BLE and serial communication test libraries from scratch

---

## 1. Bluetooth Low Energy (BLE) Architecture

```
BLE Protocol Stack:
──────────────────────────────────────────────────────────────────────────
Application (Python / Robot Framework)
    │
    │  GATT API (read char, write char, notify)
    ▼
┌───────────────────────────────────────────────────────────────────────┐
│                   GATT — Generic Attribute Profile                    │
│  Defines how data is organized: Services → Characteristics → Descriptors │
├───────────────────────────────────────────────────────────────────────┤
│                   ATT — Attribute Protocol                             │
│  Client-server model for reading/writing attributes (UUIDs)           │
├───────────────────────────────────────────────────────────────────────┤
│                   L2CAP — Logical Link Control                        │
│  Multiplexing, segmentation/reassembly of packets                     │
├───────────────────────────────────────────────────────────────────────┤
│                   HCI — Host Controller Interface                      │
│  Boundary between software (Host) and hardware (Controller)           │
├───────────────────────────────────────────────────────────────────────┤
│          Link Layer — Advertising, Scanning, Connection management     │
├───────────────────────────────────────────────────────────────────────┤
│          Physical Layer — 2.4 GHz radio, 1 Mbps / 2 Mbps LE          │
└───────────────────────────────────────────────────────────────────────┘

Key roles:
  Central:    Initiates connections, reads/writes characteristics (= your PC/phone)
  Peripheral: Advertises, accepts connections, hosts GATT server (= your power tool)
```

### GAP — Generic Access Profile
```
GAP controls device discovery and connection:
──────────────────────────────────────────────────────────────────────────
Advertising:    Peripheral broadcasts packets every 20ms–10s
                Contains: Device name, service UUIDs, manufacturer data

Scanning:       Central listens on channels 37, 38, 39
                Active scan: sends scan request for more info

Connection:     Central sends connect request with:
                  Connection interval: 7.5ms–4s
                  Slave latency: 0–499 events (peripheral can skip)
                  Supervision timeout: 100ms–32s

States:  Standby → Advertising ←→ Scanning → Connecting → Connected
──────────────────────────────────────────────────────────────────────────
```

### GATT — Generic Attribute Profile
```
GATT data hierarchy (power tool example):
──────────────────────────────────────────────────────────────────────────
Device
├── Service: Device Information (UUID: 0x180A)
│   ├── Characteristic: Manufacturer Name (0x2A29)  [Read]
│   ├── Characteristic: Model Number     (0x2A24)  [Read]
│   ├── Characteristic: Firmware Rev     (0x2A26)  [Read]
│   └── Characteristic: Serial Number   (0x2A25)  [Read]
│
├── Service: Battery (UUID: 0x180F)
│   └── Characteristic: Battery Level   (0x2A19)  [Read, Notify]
│         └── Descriptor: CCCD (0x2902)            [Read, Write]
│
└── Service: PowerTool Measurement (UUID: 0xFF00 custom)
    ├── Characteristic: Voltage Data     (0xFF01)  [Read, Notify]
    ├── Characteristic: Current Data     (0xFF02)  [Read, Notify]
    ├── Characteristic: Temperature      (0xFF03)  [Read, Notify]
    └── Characteristic: Control Command  (0xFF10)  [Write, WriteNoResp]
──────────────────────────────────────────────────────────────────────────

Properties:
  Read:         Central reads current value
  Write:        Central writes, peripheral acknowledges
  WriteNoResp:  Central writes, no acknowledgement (faster, no guarantee)
  Notify:       Peripheral pushes updates to central (no ACK)
  Indicate:     Like Notify but with acknowledgement from central
```

---

## 2. BLE Testing with bleak

```python
"""
ble_client.py — Production BLE client for power tool testing.
Uses bleak: cross-platform async BLE library.

Install: pip install bleak
"""
import asyncio
import logging
import struct
import time
from typing import Optional, Callable
from dataclasses import dataclass, field
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

logger = logging.getLogger(__name__)

# ── Service and Characteristic UUIDs (power tool example) ─────────────────
SERVICE_DEVICE_INFO   = "0000180A-0000-1000-8000-00805F9B34FB"
CHAR_FW_REVISION      = "00002A26-0000-1000-8000-00805F9B34FB"
CHAR_MODEL_NUMBER     = "00002A24-0000-1000-8000-00805F9B34FB"
CHAR_SERIAL_NUMBER    = "00002A25-0000-1000-8000-00805F9B34FB"

SERVICE_BATTERY       = "0000180F-0000-1000-8000-00805F9B34FB"
CHAR_BATTERY_LEVEL    = "00002A19-0000-1000-8000-00805F9B34FB"

SERVICE_MEASUREMENT   = "0000FF00-0000-1000-8000-00805F9B34FB"
CHAR_VOLTAGE          = "0000FF01-0000-1000-8000-00805F9B34FB"
CHAR_CURRENT          = "0000FF02-0000-1000-8000-00805F9B34FB"
CHAR_TEMPERATURE      = "0000FF03-0000-1000-8000-00805F9B34FB"
CHAR_CONTROL          = "0000FF10-0000-1000-8000-00805F9B34FB"


@dataclass
class MeasurementSample:
    timestamp:      float
    voltage_v:      float
    current_a:      float
    temperature_c:  float

    @property
    def power_w(self) -> float:
        return self.voltage_v * self.current_a


@dataclass
class NotificationBuffer:
    """Thread-safe accumulator for BLE notifications."""
    samples: list[MeasurementSample] = field(default_factory=list)
    _lock: object = field(default_factory=asyncio.Lock, repr=False)

    async def add(self, sample: MeasurementSample):
        async with self._lock:
            self.samples.append(sample)

    async def drain(self) -> list[MeasurementSample]:
        async with self._lock:
            items = self.samples.copy()
            self.samples.clear()
            return items


class PowerToolBLEClient:
    """
    Async BLE client for Power Tool testing.
    Handles scanning, connection, GATT read/write, and notifications.
    """

    SCAN_TIMEOUT    = 10.0   # s
    CONNECT_TIMEOUT = 15.0   # s

    def __init__(self, device_name: str):
        self.device_name = device_name
        self._device: Optional[BLEDevice] = None
        self._client: Optional[BleakClient] = None
        self._notifications = NotificationBuffer()
        self._notification_callbacks: dict[str, list[Callable]] = {}

    # ── Discovery ─────────────────────────────────────────────────────────

    async def scan(self, timeout: float = None) -> bool:
        """Scan for device by name. Returns True if found."""
        timeout = timeout or self.SCAN_TIMEOUT
        logger.info("Scanning for %r (%.1fs)...", self.device_name, timeout)

        devices = await BleakScanner.discover(timeout=timeout)
        self._device = next(
            (d for d in devices if d.name == self.device_name), None
        )

        if self._device:
            logger.info("Found: %s  address=%s  RSSI=%s dBm",
                        self._device.name,
                        self._device.address,
                        self._device.rssi)
            return True

        logger.warning("Device %r not found. Seen: %s",
                       self.device_name, [d.name for d in devices])
        return False

    # ── Connection ─────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Scan and connect. Raises if device not found or connect fails."""
        if not self._device:
            if not await self.scan():
                raise RuntimeError(
                    f"Cannot connect: device {self.device_name!r} not found"
                )

        self._client = BleakClient(
            self._device.address,
            timeout=self.CONNECT_TIMEOUT,
            disconnected_callback=self._on_disconnected,
        )
        await self._client.connect()
        logger.info("Connected to %s (%s)",
                    self.device_name, self._device.address)

    async def disconnect(self) -> None:
        """Gracefully disconnect."""
        if self._client and self._client.is_connected:
            await self._client.disconnect()
            logger.info("Disconnected from %s", self.device_name)

    def _on_disconnected(self, client: BleakClient):
        logger.warning("Device %s disconnected unexpectedly", self.device_name)

    @property
    def is_connected(self) -> bool:
        return bool(self._client and self._client.is_connected)

    # ── GATT Operations ────────────────────────────────────────────────────

    async def read_firmware_version(self) -> str:
        self._check_connected()
        raw = await self._client.read_gatt_char(CHAR_FW_REVISION)
        return raw.decode("utf-8").strip()

    async def read_battery_level(self) -> int:
        """Return battery level 0–100 %."""
        self._check_connected()
        raw = await self._client.read_gatt_char(CHAR_BATTERY_LEVEL)
        return raw[0]   # Single byte, 0–100

    async def read_voltage(self) -> float:
        """Read voltage in Volts. Encoded as uint16 in mV."""
        self._check_connected()
        raw = await self._client.read_gatt_char(CHAR_VOLTAGE)
        mv = struct.unpack("<H", raw)[0]
        return mv / 1000.0

    async def read_current(self) -> float:
        """Read current in Amperes. Encoded as int16 in mA."""
        self._check_connected()
        raw = await self._client.read_gatt_char(CHAR_CURRENT)
        ma = struct.unpack("<h", raw)[0]   # signed
        return ma / 1000.0

    async def write_control_command(self, cmd_id: int,
                                    payload: bytes = b"") -> None:
        """Write a control command to the tool."""
        self._check_connected()
        frame = bytes([cmd_id]) + payload
        await self._client.write_gatt_char(
            CHAR_CONTROL, frame, response=True
        )
        logger.debug("Control command 0x%02X sent (%d bytes)",
                     cmd_id, len(frame))

    # ── Notifications ──────────────────────────────────────────────────────

    async def start_measurement_notifications(self) -> None:
        """Subscribe to all measurement notifications."""
        self._check_connected()

        async def voltage_handler(sender, data):
            mv = struct.unpack("<H", data)[0]
            logger.debug("Voltage notification: %d mV", mv)

        async def current_handler(sender, data):
            ma = struct.unpack("<h", data)[0]
            logger.debug("Current notification: %d mA", ma)

        await self._client.start_notify(CHAR_VOLTAGE, voltage_handler)
        await self._client.start_notify(CHAR_CURRENT, current_handler)
        logger.info("Measurement notifications started")

    async def collect_samples(self, duration_s: float,
                              interval_s: float = 0.1) -> list[MeasurementSample]:
        """Collect measurement samples over a period by polling."""
        self._check_connected()
        samples = []
        end_time = time.monotonic() + duration_s

        while time.monotonic() < end_time:
            voltage = await self.read_voltage()
            current = await self.read_current()
            raw_t   = await self._client.read_gatt_char(CHAR_TEMPERATURE)
            temp_dc = struct.unpack("<h", raw_t)[0]

            samples.append(MeasurementSample(
                timestamp=time.monotonic(),
                voltage_v=voltage,
                current_a=current,
                temperature_c=temp_dc / 10.0,
            ))
            await asyncio.sleep(interval_s)

        logger.info("Collected %d samples over %.1fs", len(samples), duration_s)
        return samples

    def _check_connected(self):
        if not self.is_connected:
            raise RuntimeError("Not connected. Call connect() first.")


# ── Sync wrapper for use in Robot Framework / pytest ──────────────────────────
class PowerToolBLEClientSync:
    """
    Synchronous wrapper around PowerToolBLEClient.
    Use this in RF keyword libraries and pytest tests.
    """

    def __init__(self, device_name: str):
        self._async = PowerToolBLEClient(device_name)
        self._loop  = asyncio.new_event_loop()

    def __enter__(self):
        self._loop.run_until_complete(self._async.connect())
        return self

    def __exit__(self, *args):
        self._loop.run_until_complete(self._async.disconnect())
        self._loop.close()

    def read_voltage(self) -> float:
        return self._loop.run_until_complete(self._async.read_voltage())

    def read_battery_level(self) -> int:
        return self._loop.run_until_complete(self._async.read_battery_level())

    def collect_samples(self, duration_s: float) -> list[MeasurementSample]:
        return self._loop.run_until_complete(
            self._async.collect_samples(duration_s)
        )
```

---

## 3. UART / Serial Communication

```python
"""
uart_protocol.py — UART communication with binary framing protocol.
"""
import serial
import struct
import time
import threading
import queue
import logging
from contextlib import contextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Protocol constants ─────────────────────────────────────────────────────
SOF      = 0xAA   # Start of Frame
EOF      = 0x55   # End of Frame
MAX_PAYLOAD = 255

# Command IDs
CMD_GET_INFO     = 0x01
CMD_READ_VOLT    = 0x10
CMD_READ_CURR    = 0x11
CMD_READ_TEMP    = 0x12
CMD_READ_ALL     = 0x1F
CMD_SET_MODE     = 0x20
CMD_RESET        = 0xFF

# Response codes
RESP_OK          = 0x00
RESP_ERROR       = 0x01
RESP_NOT_READY   = 0x02


@dataclass
class Frame:
    """Represents a complete UART protocol frame."""
    cmd_id:   int
    payload:  bytes = b""

    def to_bytes(self) -> bytes:
        """Serialize frame to bytes."""
        # Header: SOF, CMD_ID, LENGTH
        header = struct.pack("BBB", SOF, self.cmd_id, len(self.payload))
        body   = header + self.payload
        csum   = 0
        for b in body[1:]:   # XOR from cmd_id onwards
            csum ^= b
        return body + bytes([csum, EOF])

    @classmethod
    def from_bytes(cls, data: bytes) -> "Frame":
        """Parse raw bytes into Frame. Raises ValueError on invalid frame."""
        if len(data) < 5:
            raise ValueError(f"Frame too short: {len(data)} bytes")
        if data[0] != SOF:
            raise ValueError(f"Invalid SOF: 0x{data[0]:02X}")
        if data[-1] != EOF:
            raise ValueError(f"Invalid EOF: 0x{data[-1]:02X}")

        cmd_id  = data[1]
        length  = data[2]
        payload = data[3:3+length]

        # Verify checksum
        expected = 0
        for b in data[1:3+length]:
            expected ^= b
        actual = data[3+length]
        if expected != actual:
            raise ValueError(
                f"Checksum error: expected 0x{expected:02X}, got 0x{actual:02X}"
            )
        return cls(cmd_id=cmd_id, payload=payload)


class UARTProtocolClient:
    """
    UART communication client with:
    - Framed binary protocol (SOF/EOF + checksum)
    - Background receive thread
    - Thread-safe request-response matching
    - Retry on timeout
    """

    DEFAULT_BAUD    = 115200
    DEFAULT_TIMEOUT = 3.0    # seconds per transaction
    MAX_RETRIES     = 3

    def __init__(self, port: str, baud: int = DEFAULT_BAUD):
        self.port   = port
        self.baud   = baud
        self._ser:  serial.Serial | None = None
        self._rx_q  = queue.Queue()
        self._stop  = threading.Event()
        self._rx_thread: threading.Thread | None = None

    def open(self) -> None:
        """Open serial port and start background receive thread."""
        self._ser = serial.Serial(
            port=self.port, baudrate=self.baud,
            bytesize=8, parity="N", stopbits=1,
            timeout=0.1,   # short timeout for non-blocking read
        )
        self._stop.clear()
        self._rx_thread = threading.Thread(
            target=self._receive_loop, name="UART-RX", daemon=True
        )
        self._rx_thread.start()
        logger.info("UART open: %s @ %d", self.port, self.baud)

    def close(self) -> None:
        """Stop receive thread and close port."""
        self._stop.set()
        if self._rx_thread:
            self._rx_thread.join(timeout=2.0)
        if self._ser and self._ser.is_open:
            self._ser.close()
        logger.info("UART closed: %s", self.port)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    def send_receive(self, cmd_id: int, payload: bytes = b"",
                     timeout: float = DEFAULT_TIMEOUT) -> Frame:
        """
        Send command and wait for matching response.
        Retries up to MAX_RETRIES on timeout.
        """
        frame = Frame(cmd_id, payload)
        tx_bytes = frame.to_bytes()

        for attempt in range(1, self.MAX_RETRIES + 1):
            # Flush stale data
            with self._rx_q.mutex:
                self._rx_q.queue.clear()

            self._ser.write(tx_bytes)
            self._ser.flush()
            logger.debug("TX [%d/%d]: %s", attempt, self.MAX_RETRIES,
                         tx_bytes.hex())

            try:
                response: Frame = self._rx_q.get(timeout=timeout)
                logger.debug("RX: cmd=0x%02X payload=%s",
                             response.cmd_id, response.payload.hex())
                return response
            except queue.Empty:
                logger.warning("Timeout on attempt %d/%d",
                               attempt, self.MAX_RETRIES)

        raise TimeoutError(
            f"No response to cmd 0x{cmd_id:02X} after "
            f"{self.MAX_RETRIES} attempts ({timeout}s each)"
        )

    def _receive_loop(self) -> None:
        """Background thread: read bytes, parse frames, push to queue."""
        buf = bytearray()
        while not self._stop.is_set():
            chunk = self._ser.read(64)
            if not chunk:
                continue
            buf.extend(chunk)
            # Try to extract complete frames
            while True:
                sof_idx = buf.find(SOF)
                if sof_idx == -1:
                    buf.clear()
                    break
                if sof_idx > 0:
                    buf = buf[sof_idx:]   # discard garbage before SOF
                if len(buf) < 5:
                    break                 # wait for more data
                length = buf[2]
                frame_len = 5 + length   # SOF + CMD + LEN + payload + CSUM + EOF
                if len(buf) < frame_len:
                    break                 # incomplete frame
                frame_bytes = bytes(buf[:frame_len])
                buf = buf[frame_len:]
                try:
                    frame = Frame.from_bytes(frame_bytes)
                    self._rx_q.put_nowait(frame)
                except ValueError as e:
                    logger.warning("Bad frame: %s", e)

    # ── High-level device operations ────────────────────────────────────────

    def read_all_measurements(self) -> dict:
        """Read voltage, current, temperature in one command."""
        resp = self.send_receive(CMD_READ_ALL)
        if resp.payload[0] != RESP_OK:
            raise RuntimeError(
                f"Device error 0x{resp.payload[0]:02X} on READ_ALL"
            )
        # Payload: [status, volt_lo, volt_hi, curr_lo, curr_hi, temp_lo, temp_hi]
        _, volt_mv, curr_ma, temp_dc = struct.unpack("<BHHH", resp.payload)
        return {
            "voltage_v":    volt_mv / 1000.0,
            "current_a":    curr_ma / 1000.0,
            "temperature_c": temp_dc / 10.0,
        }

    def set_measurement_mode(self, mode: int) -> None:
        """Set device measurement mode (0=idle, 1=continuous, 2=triggered)."""
        resp = self.send_receive(CMD_SET_MODE, bytes([mode]))
        if resp.payload[0] != RESP_OK:
            raise RuntimeError(f"Set mode failed: 0x{resp.payload[0]:02X}")
        logger.info("Measurement mode set to %d", mode)
```

---

## 4. BLE Notification Testing Patterns

```python
"""
ble_notification_test.py — Test BLE notifications under various conditions.
"""
import asyncio
import pytest
import time
from ble_client import PowerToolBLEClient, MeasurementSample

@pytest.mark.asyncio
async def test_notifications_received_at_correct_rate(ble_client):
    """
    BLE notifications must arrive at 10 Hz ±20%.
    """
    received_timestamps = []

    async def capture_notification(sender, data):
        received_timestamps.append(time.monotonic())

    await ble_client._client.start_notify(
        "0000FF01-0000-1000-8000-00805F9B34FB",  # Voltage char
        capture_notification
    )

    # Wait 3 seconds, expect ~30 notifications at 10 Hz
    await asyncio.sleep(3.0)
    await ble_client._client.stop_notify(
        "0000FF01-0000-1000-8000-00805F9B34FB"
    )

    assert len(received_timestamps) >= 5, \
        f"Too few notifications: {len(received_timestamps)}"

    # Calculate inter-notification intervals
    intervals = [
        received_timestamps[i+1] - received_timestamps[i]
        for i in range(len(received_timestamps) - 1)
    ]
    avg_interval = sum(intervals) / len(intervals)
    expected_interval = 0.1  # 10 Hz = 100ms
    tolerance = 0.20          # ±20%

    assert abs(avg_interval - expected_interval) / expected_interval <= tolerance, \
        f"Notification rate {1/avg_interval:.1f} Hz, expected 10 Hz"


async def test_no_notification_loss_under_load(ble_client):
    """
    Enable notifications on all 3 measurement characteristics simultaneously.
    Verify no packets are dropped over 10 seconds.
    """
    counts = {"voltage": 0, "current": 0, "temperature": 0}

    async def v_handler(s, d): counts["voltage"]     += 1
    async def c_handler(s, d): counts["current"]     += 1
    async def t_handler(s, d): counts["temperature"] += 1

    await ble_client._client.start_notify("0000FF01-0000-1000-8000-00805F9B34FB", v_handler)
    await ble_client._client.start_notify("0000FF02-0000-1000-8000-00805F9B34FB", c_handler)
    await ble_client._client.start_notify("0000FF03-0000-1000-8000-00805F9B34FB", t_handler)

    await asyncio.sleep(10.0)   # collect for 10 seconds

    # At 10 Hz × 10 s = expect 100 per channel, allow 5% loss
    for channel, count in counts.items():
        assert count >= 95, \
            f"Notification loss on {channel}: got {count}/100 expected"
```

---

## 5. Common BLE and UART Failure Scenarios

```
BLE Failure Analysis:
──────────────────────────────────────────────────────────────────────────
Symptom                     Root Cause              Debug Action
──────────────────────────────────────────────────────────────────────────
Device not found in scan    Not advertising         Power cycle device
                            Name mismatch           Check exact name (case)
                            BLE adapter off         Check adapter state
                            Range too far           Move within 5m
                            Already connected       Disconnect other client

Connection drops randomly   Supervision timeout     Increase timeout param
                            Interference (2.4GHz)   Use 5GHz WiFi if coexist
                            Low battery             Check battery level
                            Firmware bug            Capture HCI log

Characteristic read fails   Wrong UUID              Check with nRF Connect app
                            Missing permissions     Check GATT permission flags
                            Service not ready       Add delay after connect

Notification not received   CCCD not enabled        Verify start_notify called
                            Buffer overflow         Process faster / queue

──────────────────────────────────────────────────────────────────────────
UART Failure Analysis:
──────────────────────────────────────────────────────────────────────────
Symptom                     Root Cause              Debug Action
──────────────────────────────────────────────────────────────────────────
No response                 Wrong baud rate         Try 9600, 38400, 115200
                            Port busy               Kill other processes
                            Cable TX/RX swapped     Swap lines
                            Wrong COM port          List ports: python -m serial.tools.list_ports

Garbage data                Baud mismatch           Match both sides exactly
                            Framing error           Check stop bits, parity
                            Clock drift             Use crystal oscillator

Checksum failures           Noise on cable          Use shielded cable
                            Bit flip                Add retry with timeout

Timeout on send_receive     Device not responding   Check power, reset
                            Processing too slow     Increase timeout
──────────────────────────────────────────────────────────────────────────
```

---

## 6. Interview Q&A

**Q1: Explain the difference between BLE Notify and Indicate.**  
Both are server-initiated data pushes (peripheral → central). **Notify**: data is sent and no acknowledgement is required from the central. Faster but no delivery guarantee. **Indicate**: the peripheral waits for an ATT acknowledgement before sending the next indication. Slower but guaranteed delivery. For real-time measurements (10 Hz voltage data), Notify is used because the overhead of waiting for each ACK would limit throughput and add latency. For critical state changes (e.g., "fault detected"), Indicate is preferred to ensure the message is received.

**Q2: What is a CCCD and why must you write to it?**  
CCCD (Client Characteristic Configuration Descriptor, UUID 0x2902) is a per-characteristic, per-connection configuration that the central must write to enable Notify (value 0x0001) or Indicate (value 0x0002). Without writing 0x0001, the peripheral will never send notifications even if the characteristic supports them. This is intentional: notifications are per-connection, not broadcast. In bleak, calling `start_notify(uuid, handler)` automatically writes the CCCD; in raw BLE testing you must write it manually to test CCCD handling.

**Q3: How do you make a UART read non-blocking while still detecting timeouts?**  
Use a background receive thread that reads with a short polling timeout (e.g., `timeout=0.1` on `serial.Serial`) and puts complete frames into a `queue.Queue`. The main test thread calls `queue.get(timeout=3.0)` which blocks for up to 3 seconds and raises `queue.Empty` on timeout. This decouples reading from processing: the thread continuously reads without blocking the test, and the test can specify per-operation timeouts. This also prevents missing data that arrives just before the test starts waiting.

**Q4: Describe how you validate binary protocol framing correctness.**  
I test all frame boundary conditions: (1) valid frame — happy path; (2) too short — less than minimum frame length; (3) wrong SOF byte — random bytes at start; (4) wrong checksum — flip one bit in payload; (5) truncated frame — cut off before EOF; (6) back-to-back frames — verify parser correctly splits two frames; (7) garbage before valid frame — parser should skip to next SOF. These are unit tests on the `Frame.from_bytes()` parser, run with `pytest`, before any hardware is connected.

**Q5: How do you test BLE reconnection behavior after an unexpected disconnect?**  
I automate it by controlling the device power supply (or a relay board) from the test script. Steps: (1) connect and verify GATT operations work; (2) cut power to the device for 2 seconds; (3) restore power; (4) verify the device becomes discoverable within the spec timeout (e.g., 5 seconds); (5) reconnect and verify GATT operations work again; (6) verify all subscribed notifications resume. I test this with various disconnect timings and verify the client side raises a proper `disconnected_callback` rather than hanging.
