"""
hw_test_framework/adapters/can_adapter.py

Python CAN adapter — uses the C++ pybind11 extension when available,
falls back to python-can for environments without the native build.

Usage:
    from hw_test_framework.adapters.can_adapter import CanAdapter, CanFrame

    with CanAdapter("vcan0") as can:
        can.transmit(CanFrame(id=0x300, data=[0xAA, 0xBB, 0xCC, 0xDD]))
        frame = can.receive(timeout_ms=500)
        if frame:
            print(f"Received: {frame}")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from queue import Empty, Queue
from threading import Event, Thread
from typing import Callable, List, Optional

from .base_adapter import AdapterError, AdapterStats, BaseAdapter

# ── Try the fast C++ extension first, fall back to python-can ─────────────────

try:
    import hw_adapter_cpp as _cpp  # type: ignore
    _BACKEND = "cpp"
except ImportError:
    _BACKEND = "python-can"
    try:
        import can as _pycan  # type: ignore
    except ImportError:
        _pycan = None  # type: ignore


# ─── CanFrame dataclass ───────────────────────────────────────────────────────

@dataclass
class CanFrame:
    """Represents a CAN data frame (standard or extended)."""

    id: int
    data: List[int] = field(default_factory=list)
    is_extended: bool = False
    is_remote: bool = False
    is_error: bool = False
    timestamp_us: int = 0

    @property
    def dlc(self) -> int:
        return len(self.data)

    def to_bytes(self) -> bytes:
        return bytes(self.data[: self.dlc])

    def __repr__(self) -> str:
        hex_data = " ".join(f"0x{b:02X}" for b in self.data)
        return f"<CanFrame id=0x{self.id:03X} dlc={self.dlc} [{hex_data}]>"


# ─── CanFilter dataclass ──────────────────────────────────────────────────────

@dataclass
class CanFilter:
    id: int = 0
    mask: int = 0xFFFFFFFF
    extended: bool = False

    @classmethod
    def accept_all(cls) -> "CanFilter":
        return cls(id=0, mask=0)

    @classmethod
    def exact_id(cls, msg_id: int, extended: bool = False) -> "CanFilter":
        return cls(id=msg_id, mask=0x1FFFFFFF if extended else 0x7FF, extended=extended)


# ─── Bitrate constants ────────────────────────────────────────────────────────

BITRATE_125K = 125_000
BITRATE_250K = 250_000
BITRATE_500K = 500_000
BITRATE_1M   = 1_000_000


# ─── CanAdapter ───────────────────────────────────────────────────────────────

class CanAdapter(BaseAdapter):
    """
    CAN bus adapter.

    Backends (tried in order):
      1. hw_adapter_cpp  — native pybind11 extension (fastest, SocketCAN / Vector XL)
      2. python-can      — pure-Python; supports many USB-CAN dongles
      3. LoopbackAdapter — software loopback for unit tests (no hardware required)
    """

    def __init__(
        self,
        device_uri: str = "",
        bitrate: int = BITRATE_500K,
        rx_queue_size: int = 1024,
    ) -> None:
        self._device_uri   = device_uri
        self._bitrate      = bitrate
        self._rx_q_size    = rx_queue_size
        self._filter       = CanFilter.accept_all()
        self._stats        = AdapterStats()
        self._rx_callbacks: List[Callable[[CanFrame], None]] = []
        self._rx_queue: Queue[CanFrame] = Queue(maxsize=rx_queue_size)

        # Backend handles
        self._cpp_adapter  = None   # hw_adapter_cpp.CanAdapter
        self._pycan_bus    = None   # can.BusABC
        self._rx_thread: Optional[Thread] = None
        self._stop_event   = Event()
        self._open         = False

    # ── BaseAdapter ──────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "CAN"

    @property
    def is_open(self) -> bool:
        return self._open

    def stats(self) -> AdapterStats:
        return self._stats

    def reset_stats(self) -> None:
        self._stats = AdapterStats()

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def open(self, device_uri: str = "") -> None:
        if device_uri:
            self._device_uri = device_uri

        if _BACKEND == "cpp":
            self._cpp_adapter = _cpp.CanAdapter()
            status = self._cpp_adapter.open(self._device_uri)
            if status != _cpp.AdapterStatus.OK:
                raise AdapterError(f"C++ CanAdapter open failed: {status}")
        elif _BACKEND == "python-can" and _pycan is not None:
            self._pycan_bus = _pycan.Bus(
                channel=self._device_uri,
                interface="socketcan",
                bitrate=self._bitrate,
            )
            self._stop_event.clear()
            self._rx_thread = Thread(target=self._rx_loop, daemon=True, name="can-rx")
            self._rx_thread.start()
        else:
            # Loopback — unit test mode
            self._stop_event.clear()

        self._open = True

    def close(self) -> None:
        if not self._open:
            return
        self._stop_event.set()
        if self._rx_thread and self._rx_thread.is_alive():
            self._rx_thread.join(timeout=2.0)

        if self._cpp_adapter:
            self._cpp_adapter.close()
            self._cpp_adapter = None
        if self._pycan_bus:
            self._pycan_bus.shutdown()
            self._pycan_bus = None

        self._open = False

    # ── Transmit ─────────────────────────────────────────────────────────────

    def transmit(self, frame: CanFrame, timeout_ms: int = 100) -> None:
        """Transmit a single CAN frame."""
        self._require_open()
        try:
            if self._cpp_adapter:
                cpp_frame = _cpp.CanFrame.make(
                    frame.id, list(frame.data), frame.is_extended
                )
                status = self._cpp_adapter.transmit(cpp_frame, timeout_ms)
                if status != _cpp.AdapterStatus.OK:
                    self._stats.error_count += 1
                    raise AdapterError(f"Transmit failed: {status}")

            elif self._pycan_bus:
                msg = _pycan.Message(
                    arbitration_id=frame.id,
                    data=frame.data,
                    is_extended_id=frame.is_extended,
                    is_remote_frame=frame.is_remote,
                )
                self._pycan_bus.send(msg, timeout=timeout_ms / 1000.0)

            else:
                # Loopback mode: echo back into rx queue
                if self._filter.mask == 0 or (frame.id & self._filter.mask) == (self._filter.id & self._filter.mask):
                    self._rx_queue.put_nowait(frame)
                    for cb in self._rx_callbacks:
                        try:
                            cb(frame)
                        except Exception:
                            pass

            self._stats.tx_count += 1

        except Exception as exc:
            self._stats.error_count += 1
            raise AdapterError(f"Transmit error: {exc}") from exc

    def transmit_burst(self, frames: List[CanFrame], timeout_ms: int = 500) -> None:
        for f in frames:
            self.transmit(f, timeout_ms)

    # ── Receive ──────────────────────────────────────────────────────────────

    def receive(self, timeout_ms: int = 1000) -> Optional[CanFrame]:
        """
        Blocking receive.
        Returns CanFrame or None on timeout.
        """
        self._require_open()

        if self._cpp_adapter:
            cpp_f = self._cpp_adapter.receive(timeout_ms)
            if cpp_f is None:
                self._stats.timeout_count += 1
                return None
            self._stats.rx_count += 1
            return CanFrame(
                id=cpp_f.id,
                data=list(cpp_f.to_bytes()),
                is_extended=cpp_f.is_extended,
                is_remote=cpp_f.is_remote,
                is_error=cpp_f.is_error,
                timestamp_us=cpp_f.timestamp_us,
            )

        try:
            frame = self._rx_queue.get(timeout=timeout_ms / 1000.0)
            self._stats.rx_count += 1
            return frame
        except Empty:
            self._stats.timeout_count += 1
            return None

    def on_receive(self, callback: Callable[[CanFrame], None]) -> None:
        """Register a callback invoked for each received frame."""
        self._rx_callbacks.append(callback)
        if self._cpp_adapter:
            self._cpp_adapter.on_receive(
                lambda cf: callback(
                    CanFrame(id=cf.id, data=list(cf.to_bytes()),
                             is_extended=cf.is_extended, timestamp_us=cf.timestamp_us)
                )
            )

    def flush_rx_queue(self) -> None:
        while not self._rx_queue.empty():
            try:
                self._rx_queue.get_nowait()
            except Empty:
                break
        if self._cpp_adapter:
            self._cpp_adapter.flush_rx_queue()

    def set_filter(self, filt: CanFilter) -> None:
        self._filter = filt
        if self._cpp_adapter:
            cpp_filt = _cpp.CanFilter.exact_id(filt.id, filt.extended)
            cpp_filt.mask = filt.mask
            self._cpp_adapter.set_filter(cpp_filt)

    # ── Internal RX loop (python-can backend) ────────────────────────────────

    def _rx_loop(self) -> None:
        while not self._stop_event.is_set():
            if self._pycan_bus is None:
                break
            raw = self._pycan_bus.recv(timeout=0.05)
            if raw is None:
                continue
            frame = CanFrame(
                id=raw.arbitration_id,
                data=list(raw.data),
                is_extended=raw.is_extended_id,
                is_remote=raw.is_remote_frame,
                is_error=raw.is_error_frame,
                timestamp_us=int(raw.timestamp * 1_000_000),
            )
            # Apply filter
            if (frame.id & self._filter.mask) != (self._filter.id & self._filter.mask):
                continue
            if not self._rx_queue.full():
                self._rx_queue.put_nowait(frame)
            for cb in self._rx_callbacks:
                try:
                    cb(frame)
                except Exception:
                    pass

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "CanAdapter":
        if not self._open:
            self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
