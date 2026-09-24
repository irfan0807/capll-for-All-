"""
CAN bus interface abstraction.

Wraps python-can's Bus object. Defaults to the 'virtual' interface so the
whole framework is runnable end-to-end with no hardware attached (CI, a
laptop, whatever) -- swap `interface`/`channel` to 'socketcan'/'can0',
'vector', 'kvaser', 'ixxat', etc. to point this exact same framework at a
real bench, dSPACE SCALEXIO breakout, or a physical ECU. Nothing above this
layer changes.
"""
from __future__ import annotations

import can

from src.utils.logger import get_logger

log = get_logger("can_interface")


class CanInterface:
    """Owns the physical (or virtual) CAN bus handle."""

    def __init__(
        self,
        channel: str = "aeb_test_bus",
        interface: str = "virtual",
        bitrate: int = 500_000,
        fd: bool = False,
        receive_own_messages: bool = False,
    ):
        self.channel = channel
        self.interface = interface
        self.fd = fd
        self._bus: can.BusABC | None = None
        self._bus_kwargs = dict(
            channel=channel,
            interface=interface,
            bitrate=bitrate,
            receive_own_messages=receive_own_messages,
        )
        if fd:
            self._bus_kwargs["fd"] = True

    def connect(self) -> "CanInterface":
        self._bus = can.interface.Bus(**self._bus_kwargs)
        log.info(
            "CAN bus connected: interface=%s channel=%s fd=%s",
            self.interface, self.channel, self.fd,
        )
        return self

    def disconnect(self) -> None:
        if self._bus is not None:
            self._bus.shutdown()
            log.info("CAN bus disconnected: channel=%s", self.channel)
            self._bus = None

    @property
    def bus(self) -> can.BusABC:
        if self._bus is None:
            raise RuntimeError("CAN bus not connected -- call connect() first")
        return self._bus

    def send(self, arbitration_id: int, data: bytes, is_fd: bool = False, extra_flags: bool = False) -> None:
        msg = can.Message(
            arbitration_id=arbitration_id,
            data=data,
            is_extended_id=False,
            is_fd=is_fd,
            bitrate_switch=is_fd and extra_flags,
        )
        self.bus.send(msg)
        log.debug("TX 0x%03X [%d] %s", arbitration_id, len(data), data.hex(" "))

    def __enter__(self) -> "CanInterface":
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()
