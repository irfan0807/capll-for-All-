"""
conftest.py - pytest configuration for infotainment_python_suite
Shared fixtures and session-level setup/teardown.
"""
import pytest
import can

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000


@pytest.fixture(scope="session", autouse=True)
def bus_session():
    """Session-scoped CAN bus fixture. Falls back to vcan0 if PCAN unavailable."""
    try:
        bus = can.interface.Bus(channel=CHANNEL, bustype=BUSTYPE, bitrate=BITRATE)
    except Exception:
        bus = can.interface.Bus(channel='vcan0', bustype='socketcan')
    yield bus
    bus.shutdown()
