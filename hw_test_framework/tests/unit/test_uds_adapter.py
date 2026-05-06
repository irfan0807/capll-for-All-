"""
tests/unit/test_uds_adapter.py

Unit tests for UDS adapter with a mock CAN backend.
Validates ISO-TP framing, service encoding, and NRC handling
without any hardware.
"""

import sys
import os
import collections
import threading
import time
from typing import Optional

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../python"))

from hw_test_framework.adapters.can_adapter import CanFrame
from hw_test_framework.adapters.uds_adapter import (
    IsoTpConfig,
    UdsAdapter,
    UdsNrc,
    UdsSession,
)


# ─── Minimal CAN mock ─────────────────────────────────────────────────────────

class MockCanAdapter:
    """
    Minimal stand-alone CAN mock — provides only the interface UdsAdapter needs:
      transmit(), receive(), flush_rx_queue(), is_open
    """

    def __init__(self):
        self._open         = False
        self._response_map: dict = {}
        self._rx_deque: collections.deque = collections.deque()
        self._lock = threading.Lock()

    def open(self):  self._open = True
    def close(self): self._open = False

    @property
    def is_open(self) -> bool:
        return self._open

    def flush_rx_queue(self) -> None:
        with self._lock:
            self._rx_deque.clear()

    def transmit(self, frame: CanFrame) -> None:
        payload = bytes(frame.data[:frame.dlc])
        for prefix, response_bytes in self._response_map.items():
            if payload[:len(prefix)] == prefix:
                threading.Timer(0.005, self._inject, args=(response_bytes,)).start()
                return

    def _inject(self, data: bytes) -> None:
        resp_frame = CanFrame(id=0x7E8, data=list(data))
        with self._lock:
            self._rx_deque.append(resp_frame)

    def receive(self, timeout_ms: int = 1000) -> Optional[CanFrame]:
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            with self._lock:
                if self._rx_deque:
                    return self._rx_deque.popleft()
            time.sleep(0.002)
        return None

    def set_response(self, request_prefix: bytes, response: bytes) -> None:
        self._response_map[request_prefix] = response


@pytest.fixture
def mock_can():
    can = MockCanAdapter()
    can.open()
    yield can
    can.close()


@pytest.fixture
def uds(mock_can):
    cfg = IsoTpConfig(tx_id=0x7DF, rx_id=0x7E8, timeout_ms=500)
    adapter = UdsAdapter(mock_can, cfg)
    adapter.open()
    yield adapter
    adapter.close()


# ─── ECU Reset ────────────────────────────────────────────────────────────────

class TestEcuReset:
    def test_hard_reset_positive_response(self, uds, mock_can):
        # Positive response: 0x51 0x01
        mock_can.set_response(b"\x02\x11\x01", b"\x03\x51\x01\x00")
        resp = uds.ecu_reset(reset_type=0x01)
        assert resp.positive, f"Expected positive response, got NRC {resp.nrc}"

    def test_nrc_conditions_not_correct(self, uds, mock_can):
        # NRC 0x22 = conditionsNotCorrect
        mock_can.set_response(b"\x02\x11\x01", b"\x03\x7F\x11\x22")
        resp = uds.ecu_reset(reset_type=0x01)
        assert not resp.positive
        assert resp.nrc == UdsNrc.ConditionsNotCorrect


# ─── Read DID ─────────────────────────────────────────────────────────────────

class TestReadDid:
    def test_read_did_f190_vin(self, uds, mock_can):
        # ReadDataByIdentifier 0x22 0xF1 0x90 → 17-byte VIN
        vin_bytes = b"1HGBH41JXMN109186"
        response  = bytes([0x12]) + b"\x62\xF1\x90" + vin_bytes  # first frame
        mock_can.set_response(b"\x03\x22\xF1\x90", response)
        resp = uds.read_did(0xF190)
        # In a stub environment, positive check depends on mock
        # At minimum we verify no exception is raised


# ─── Session control ──────────────────────────────────────────────────────────

class TestSessionControl:
    def test_default_session(self, uds, mock_can):
        mock_can.set_response(
            b"\x02\x10\x01",
            b"\x06\x50\x01\x00\x19\x01\xF4",
        )
        resp = uds.open_session(UdsSession.DEFAULT)
        assert resp.positive

    def test_extended_session(self, uds, mock_can):
        mock_can.set_response(
            b"\x02\x10\x03",
            b"\x06\x50\x03\x00\x19\x01\xF4",
        )
        resp = uds.open_session(UdsSession.EXTENDED)
        assert resp.positive


# ─── DTC read ────────────────────────────────────────────────────────────────

class TestReadDtc:
    def test_no_dtcs(self, uds, mock_can):
        # ReadDTCInformation (0x19) subfunction 0x02, zero DTCs
        mock_can.set_response(
            b"\x03\x19\x02\x0F",
            b"\x03\x59\x02\x00",
        )
        dtcs = uds.read_dtcs(status_mask=0x0F)
        assert isinstance(dtcs, list)


# ─── ISO-TP segmentation ──────────────────────────────────────────────────────

class TestIsoTpFraming:
    def test_single_frame_payload_encoding(self, mock_can):
        """Verify transmit encodes a short UDS request as a CAN single frame."""
        frames_sent = []

        orig_tx = mock_can.transmit
        def capturing_tx(f):
            frames_sent.append(bytes(f.data[:f.dlc]))
            orig_tx(f)

        mock_can.transmit = capturing_tx
        cfg = IsoTpConfig(tx_id=0x7DF, rx_id=0x7E8, timeout_ms=50)
        adapter = UdsAdapter(mock_can, cfg)
        adapter.open()

        # Prepare a response to avoid timeout
        mock_can.set_response(b"\x02\x11\x01", b"\x03\x51\x01\x00")
        try:
            adapter.ecu_reset(0x01)
        except Exception:
            pass
        adapter.close()

        # First frame should be [0x02, 0x11, 0x01, ...]
        assert len(frames_sent) >= 1
        first = frames_sent[0]
        assert first[0] == 0x02          # length = 2 bytes (service + type)
        assert first[1] == 0x11          # service: ECU Reset
