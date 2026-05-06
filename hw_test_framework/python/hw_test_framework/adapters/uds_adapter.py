"""
hw_test_framework/adapters/uds_adapter.py

Python UDS adapter — delegates to hw_adapter_cpp when available,
pure-Python ISO-TP + UDS implementation otherwise.

Usage:
    from hw_test_framework.adapters.can_adapter import CanAdapter
    from hw_test_framework.adapters.uds_adapter import UdsAdapter, UdsSession

    with CanAdapter("vcan0") as can:
        uds = UdsAdapter(can, tx_id=0x7E0, rx_id=0x7E8)
        uds.open()
        uds.open_session(UdsSession.EXTENDED)
        resp = uds.read_did(0xF189)
        print(f"SW version: {resp.payload.hex()}")
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, List, Optional

from .base_adapter import AdapterError, AdapterStats, BaseAdapter
from .can_adapter import CanAdapter, CanFrame

try:
    import hw_adapter_cpp as _cpp  # type: ignore
    _BACKEND = "cpp"
except ImportError:
    _BACKEND = "python"


# ─── UDS constants ────────────────────────────────────────────────────────────

class UdsService(IntEnum):
    DiagnosticSessionControl   = 0x10
    ECUReset                   = 0x11
    ClearDiagnosticInfo        = 0x14
    ReadDTCInformation         = 0x19
    ReadDataByIdentifier       = 0x22
    ReadMemoryByAddress        = 0x23
    SecurityAccess             = 0x27
    CommunicationControl       = 0x28
    WriteDataByIdentifier      = 0x2E
    InputOutputControlByID     = 0x2F
    RoutineControl             = 0x31
    RequestDownload            = 0x34
    TransferData               = 0x36
    RequestTransferExit        = 0x37


class UdsSession(IntEnum):
    DEFAULT     = 0x01
    PROGRAMMING = 0x02
    EXTENDED    = 0x03


class UdsNrc(IntEnum):
    ServiceNotSupported          = 0x11
    SubFunctionNotSupported      = 0x12
    IncorrectMessageLength       = 0x13
    ConditionsNotCorrect         = 0x22
    RequestSequenceError         = 0x24
    RequestOutOfRange            = 0x31
    SecurityAccessDenied         = 0x33
    InvalidKey                   = 0x35
    ExceedNumberOfAttempts       = 0x36
    ResponsePending              = 0x78
    ServiceNotSupportedInSession = 0x7F

    @classmethod
    def describe(cls, code: int) -> str:
        try:
            return cls(code).name
        except ValueError:
            return f"0x{code:02X}"


# ─── UdsResponse ─────────────────────────────────────────────────────────────

@dataclass
class UdsResponse:
    positive: bool = False
    service_id: int = 0
    nrc: Optional[UdsNrc] = None
    payload: bytes = b""
    elapsed_us: int = 0

    @property
    def ok(self) -> bool:
        return self.positive

    def u8_at(self, offset: int) -> int:
        return self.payload[offset]

    def u16_at(self, offset: int) -> int:
        return struct.unpack_from(">H", self.payload, offset)[0]

    def u32_at(self, offset: int) -> int:
        return struct.unpack_from(">I", self.payload, offset)[0]

    def __repr__(self) -> str:
        if self.positive:
            return f"<UdsResponse POSITIVE svc=0x{self.service_id:02X} len={len(self.payload)}>"
        return f"<UdsResponse NEGATIVE nrc={UdsNrc.describe(self.nrc or 0)}>"


# ─── DtcRecord ────────────────────────────────────────────────────────────────

@dataclass
class DtcRecord:
    dtc_number: int = 0
    status_byte: int = 0

    @property
    def confirmed(self) -> bool:
        return bool(self.status_byte & 0x08)

    @property
    def pending(self) -> bool:
        return bool(self.status_byte & 0x01)

    @property
    def test_failed(self) -> bool:
        return bool(self.status_byte & 0x04)

    def hex(self) -> str:
        return f"{self.dtc_number:06X}"

    def __repr__(self) -> str:
        return (f"<DtcRecord {self.hex()} confirmed={self.confirmed} "
                f"pending={self.pending} status=0x{self.status_byte:02X}>")


# ─── IsoTpConfig ──────────────────────────────────────────────────────────────

@dataclass
class IsoTpConfig:
    tx_id: int = 0x7E0
    rx_id: int = 0x7E8
    extended_ids: bool = False
    block_size: int = 0
    st_min_ms: int = 0
    timeout_ms: int = 1000
    timeout_ext_ms: int = 5000


# ─── Pure-Python ISO-TP transport ────────────────────────────────────────────

class _IsoTpTransport:
    """Minimal ISO 15765-2 transport layer — used when C++ backend is unavailable."""

    def __init__(self, can: CanAdapter, cfg: IsoTpConfig) -> None:
        self._can = can
        self._cfg = cfg

    def send(self, data: bytes) -> None:
        if len(data) <= 7:
            frame_data = [len(data)] + list(data)
            frame_data += [0xCC] * (8 - len(frame_data))
            self._can.transmit(CanFrame(id=self._cfg.tx_id, data=frame_data[:8]))
            return

        # First frame
        total = len(data)
        ff_data = [0x10 | ((total >> 8) & 0x0F), total & 0xFF] + list(data[:6])
        self._can.transmit(CanFrame(id=self._cfg.tx_id, data=ff_data))

        # Wait for FC
        fc = self._can.receive(timeout_ms=self._cfg.timeout_ms)
        if fc is None or fc.data[0] != 0x30:
            raise AdapterError("ISO-TP: no flow control received")

        # Consecutive frames
        offset = 6
        sn = 1
        while offset < total:
            chunk = data[offset: offset + 7]
            cf_data = [0x20 | (sn & 0x0F)] + list(chunk)
            cf_data += [0xCC] * (8 - len(cf_data))
            self._can.transmit(CanFrame(id=self._cfg.tx_id, data=cf_data[:8]))
            offset += 7
            sn += 1
            if self._cfg.st_min_ms:
                time.sleep(self._cfg.st_min_ms / 1000.0)

    def receive(self) -> bytes:
        deadline = time.monotonic() + self._cfg.timeout_ms / 1000.0

        def wait_frame() -> Optional[CanFrame]:
            remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
            frame = self._can.receive(timeout_ms=remaining_ms)
            while frame and frame.id != self._cfg.rx_id:
                remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
                frame = self._can.receive(timeout_ms=remaining_ms)
            return frame

        first = wait_frame()
        if first is None:
            raise AdapterError("ISO-TP: no response (timeout)")

        pci_type = (first.data[0] >> 4) & 0x0F

        if pci_type == 0:
            length = first.data[0] & 0x0F
            return bytes(first.data[1: 1 + length])

        if pci_type == 1:
            total = ((first.data[0] & 0x0F) << 8) | first.data[1]
            result = bytearray(first.data[2:8])

            # Send flow control
            fc = CanFrame(id=self._cfg.tx_id,
                          data=[0x30, self._cfg.block_size, self._cfg.st_min_ms, 0, 0, 0, 0, 0])
            self._can.transmit(fc)

            expected_sn = 1
            while len(result) < total:
                cf = wait_frame()
                if cf is None:
                    raise AdapterError("ISO-TP: consecutive frame timeout")
                if (cf.data[0] >> 4) != 2:
                    raise AdapterError("ISO-TP: unexpected PCI type")
                if (cf.data[0] & 0x0F) != (expected_sn & 0x0F):
                    raise AdapterError("ISO-TP: sequence number mismatch")
                chunk = min(7, total - len(result))
                result.extend(cf.data[1: 1 + chunk])
                expected_sn += 1

            return bytes(result)

        raise AdapterError(f"ISO-TP: unexpected first-frame PCI type 0x{pci_type:X}")


# ─── UdsAdapter ───────────────────────────────────────────────────────────────

class UdsAdapter(BaseAdapter):
    """
    ISO 14229 UDS adapter.

    Layers:
      Physical/Data link: CanAdapter
      Transport:          ISO 15765-2 (handled by C++ extension or _IsoTpTransport)
      Application:        ISO 14229 service encoding/decoding (this class)
    """

    def __init__(self, can: CanAdapter, config: Optional[IsoTpConfig] = None) -> None:
        self._can    = can
        self._config = config or IsoTpConfig()
        self._stats  = AdapterStats()
        self._open   = False

        # Backend
        self._cpp_uds  = None
        self._transport: Optional[_IsoTpTransport] = None

    @property
    def name(self) -> str:
        return "UDS"

    @property
    def is_open(self) -> bool:
        return self._open

    def stats(self) -> AdapterStats:
        return self._stats

    def reset_stats(self) -> None:
        self._stats = AdapterStats()

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def open(self, device_uri: str = "") -> None:
        if not self._can.is_open:
            raise AdapterError("CanAdapter must be open before UdsAdapter.open()")

        if _BACKEND == "cpp":
            # Use C++ extension if available
            # Wrap python CanAdapter into shared_ptr — not possible across Python boundary
            # so fall through to Python transport even if cpp module is present
            pass

        self._transport = _IsoTpTransport(self._can, self._config)
        self._open = True

    def close(self) -> None:
        self._open = False
        if self._cpp_uds:
            self._cpp_uds.close()
            self._cpp_uds = None

    def configure(self, config: IsoTpConfig) -> None:
        self._config = config
        if self._transport:
            self._transport._cfg = config

    # ── Core request/response ────────────────────────────────────────────────

    def send_raw(self, request: bytes) -> UdsResponse:
        """Send raw UDS bytes and return the decoded response."""
        self._require_open()
        t0 = time.monotonic()

        try:
            self._can.flush_rx_queue()
            self._transport.send(request)
            self._stats.tx_count += 1
        except Exception as exc:
            self._stats.error_count += 1
            raise AdapterError(f"UDS send failed: {exc}") from exc

        # Handle 0x78 ResponsePending (re-receive with extended timeout)
        saved_timeout = self._config.timeout_ms
        for _ in range(10):
            try:
                raw = self._transport.receive()
            except AdapterError:
                self._stats.timeout_count += 1
                return UdsResponse(positive=False, elapsed_us=self._elapsed_us(t0))

            if raw[0] == 0x7F:
                if len(raw) >= 3 and raw[2] == 0x78:
                    self._config.timeout_ms = self._config.timeout_ext_ms
                    continue
                nrc_byte = raw[2] if len(raw) >= 3 else 0x11
                self._stats.error_count += 1
                return UdsResponse(
                    positive=False,
                    service_id=raw[1] if len(raw) > 1 else 0,
                    nrc=UdsNrc(nrc_byte) if nrc_byte in UdsNrc._value2member_map_ else None,
                    elapsed_us=self._elapsed_us(t0),
                )
            else:
                self._stats.rx_count += 1
                self._config.timeout_ms = saved_timeout
                return UdsResponse(
                    positive=True,
                    service_id=raw[0],
                    payload=raw[1:],
                    elapsed_us=self._elapsed_us(t0),
                )

        self._stats.timeout_count += 1
        return UdsResponse(positive=False, elapsed_us=self._elapsed_us(t0))

    @staticmethod
    def _elapsed_us(t0: float) -> int:
        return int((time.monotonic() - t0) * 1_000_000)

    # ── Session management ───────────────────────────────────────────────────

    def open_session(self, session: UdsSession = UdsSession.EXTENDED) -> UdsResponse:
        return self.send_raw(bytes([UdsService.DiagnosticSessionControl, int(session)]))

    def tester_present(self, suppress: bool = True) -> UdsResponse:
        return self.send_raw(bytes([UdsService.DiagnosticSessionControl,
                                    0x80 if suppress else 0x00]))

    def ecu_reset(self, reset_type: int = 0x01) -> UdsResponse:
        return self.send_raw(bytes([UdsService.ECUReset, reset_type]))

    # ── Security access ──────────────────────────────────────────────────────

    def security_access(
        self,
        level: int,
        seed_to_key_fn: Callable[[bytes], bytes],
    ) -> UdsResponse:
        """Perform 2-step seed+key security access."""
        seed_resp = self.send_raw(bytes([UdsService.SecurityAccess, level]))
        if not seed_resp.ok:
            return seed_resp
        key = seed_to_key_fn(seed_resp.payload)
        return self.send_raw(bytes([UdsService.SecurityAccess, level + 1]) + key)

    # ── Data services ────────────────────────────────────────────────────────

    def read_did(self, did: int) -> UdsResponse:
        return self.send_raw(bytes([UdsService.ReadDataByIdentifier,
                                    (did >> 8) & 0xFF, did & 0xFF]))

    def write_did(self, did: int, data: bytes) -> UdsResponse:
        return self.send_raw(bytes([UdsService.WriteDataByIdentifier,
                                    (did >> 8) & 0xFF, did & 0xFF]) + data)

    def read_memory(self, address: int, length: int) -> UdsResponse:
        return self.send_raw(bytes([
            UdsService.ReadMemoryByAddress,
            0x14,
            (address >> 24) & 0xFF, (address >> 16) & 0xFF,
            (address >>  8) & 0xFF,  address        & 0xFF,
            length,
        ]))

    def io_control(self, did: int, control_param: int, data: bytes = b"") -> UdsResponse:
        return self.send_raw(bytes([
            UdsService.InputOutputControlByID,
            (did >> 8) & 0xFF, did & 0xFF, control_param,
        ]) + data)

    # ── DTC services ─────────────────────────────────────────────────────────

    def read_dtcs(self, status_mask: int = 0x0F) -> List[DtcRecord]:
        resp = self.send_raw(bytes([UdsService.ReadDTCInformation, 0x02, status_mask]))
        records: List[DtcRecord] = []
        if not resp.ok or len(resp.payload) < 1:
            return records
        i = 1  # skip status_availability_mask byte
        while i + 3 <= len(resp.payload):
            dtc_num = (resp.payload[i] << 16) | (resp.payload[i + 1] << 8) | resp.payload[i + 2]
            status  = resp.payload[i + 3]
            records.append(DtcRecord(dtc_number=dtc_num, status_byte=status))
            i += 4
        return records

    def clear_dtcs(self, group: int = 0xFFFFFF) -> UdsResponse:
        return self.send_raw(bytes([
            UdsService.ClearDiagnosticInfo,
            (group >> 16) & 0xFF, (group >> 8) & 0xFF, group & 0xFF,
        ]))

    def read_dtc_snapshot(self, dtc_number: int, record: int = 0x01) -> UdsResponse:
        return self.send_raw(bytes([
            UdsService.ReadDTCInformation, 0x04,
            (dtc_number >> 16) & 0xFF, (dtc_number >> 8) & 0xFF, dtc_number & 0xFF,
            record,
        ]))

    # ── Routine control ──────────────────────────────────────────────────────

    def start_routine(self, routine_id: int, params: bytes = b"") -> UdsResponse:
        return self.send_raw(bytes([
            UdsService.RoutineControl, 0x01,
            (routine_id >> 8) & 0xFF, routine_id & 0xFF,
        ]) + params)

    def stop_routine(self, routine_id: int) -> UdsResponse:
        return self.send_raw(bytes([
            UdsService.RoutineControl, 0x02,
            (routine_id >> 8) & 0xFF, routine_id & 0xFF,
        ]))

    def routine_results(self, routine_id: int) -> UdsResponse:
        return self.send_raw(bytes([
            UdsService.RoutineControl, 0x03,
            (routine_id >> 8) & 0xFF, routine_id & 0xFF,
        ]))
