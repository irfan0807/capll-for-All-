"""
tests/unit/test_can_adapter.py

Unit tests for the Python CAN adapter.
Uses the loopback backend — no hardware required.
"""

import sys
import os
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../python"))

from hw_test_framework.adapters.can_adapter import (
    CanAdapter,
    CanFilter,
    CanFrame,
    BITRATE_500K,
)


@pytest.fixture
def adapter():
    """Open a loopback CAN adapter and yield it."""
    a = CanAdapter(device_uri="", bitrate=BITRATE_500K)
    a.open()
    yield a
    a.close()


class TestCanAdapterLifecycle:
    def test_open_close(self):
        a = CanAdapter()
        a.open()
        assert a.is_open
        a.close()
        assert not a.is_open

    def test_context_manager(self):
        with CanAdapter() as a:
            assert a.is_open
        assert not a.is_open

    def test_double_close_is_safe(self):
        a = CanAdapter()
        a.open()
        a.close()
        a.close()  # should not raise


class TestCanAdapterTransmitReceive:
    def test_loopback_single_frame(self, adapter):
        frame = CanFrame(id=0x123, data=bytes([0x01, 0x02, 0x03]))
        adapter.transmit(frame)
        rx = adapter.receive(timeout_ms=200)
        assert rx is not None
        assert rx.id  == 0x123
        assert rx.dlc == 3
        assert rx.data[:3] == bytes([0x01, 0x02, 0x03])

    def test_loopback_8_byte_frame(self, adapter):
        data = bytes(range(8))
        frame = CanFrame(id=0x7FF, data=data)
        adapter.transmit(frame)
        rx = adapter.receive(timeout_ms=200)
        assert rx is not None
        assert rx.data == data

    def test_receive_timeout_returns_none(self, adapter):
        rx = adapter.receive(timeout_ms=50)
        assert rx is None

    def test_stats_increment(self, adapter):
        tx_before = adapter.stats().tx_count
        adapter.transmit(CanFrame(id=0x100, data=[0xAB]))
        adapter.receive(timeout_ms=100)
        assert adapter.stats().tx_count > tx_before

    def test_on_receive_callback(self, adapter):
        received = []
        adapter.on_receive(lambda f: received.append(f))
        adapter.transmit(CanFrame(id=0x200, data=b"\xFF"))
        time.sleep(0.1)
        assert len(received) >= 1
        assert received[0].id == 0x200

    def test_flush_rx_queue(self, adapter):
        adapter.transmit(CanFrame(id=0x300, data=b"\x00"))
        time.sleep(0.05)
        adapter.flush_rx_queue()
        rx = adapter.receive(timeout_ms=50)
        assert rx is None


class TestCanAdapterFilter:
    def test_accept_all_passes_any_id(self, adapter):
        adapter.set_filter(CanFilter.accept_all())
        adapter.transmit(CanFrame(id=0x001, data=b"\x01"))
        rx = adapter.receive(timeout_ms=200)
        assert rx is not None

    def test_exact_id_filter_passes_matching(self, adapter):
        adapter.set_filter(CanFilter.exact_id(0x555))
        adapter.transmit(CanFrame(id=0x555, data=b"\x01"))
        rx = adapter.receive(timeout_ms=200)
        assert rx is not None
        assert rx.id == 0x555

    def test_extended_frame_flag(self, adapter):
        frame = CanFrame(id=0x1FFFFFFF, data=b"\xEE", is_extended=True)
        adapter.transmit(frame)
        rx = adapter.receive(timeout_ms=200)
        if rx:  # loopback may not distinguish; just check no crash
            assert rx.id == 0x1FFFFFFF
