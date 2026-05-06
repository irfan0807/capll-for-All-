"""
tests/system/test_adas_bsd.py

System test for the Blind Spot Detection (BSD) feature.
Uses the hw_test_framework TestCase base class.

Prerequisite:
  - ECU running BSD firmware on CAN bus
  - vcan0 up or physical CAN hardware connected
  - pytest --hw flag used to enable hardware tests

Run:
    pytest tests/system/test_adas_bsd.py -v --hw
"""

from __future__ import annotations

import sys
import os
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../python"))

from hw_test_framework.adapters.can_adapter import CanAdapter, CanFrame, BITRATE_500K
from hw_test_framework.adapters.uds_adapter import IsoTpConfig, UdsAdapter, UdsSession
from hw_test_framework.framework.test_case import TestCase, TestStatus
from hw_test_framework.framework.test_runner import RunConfig, TestRunner


# ─── Pytest option ────────────────────────────────────────────────────────────

def pytest_addoption(parser):
    parser.addoption("--hw", action="store_true", default=False,
                     help="Enable hardware-in-the-loop system tests")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--hw"):
        skip = pytest.mark.skip(reason="Pass --hw to run hardware system tests")
        for item in items:
            item.add_marker(skip)


# ─── Signal helpers ───────────────────────────────────────────────────────────

BSD_WARNING_ID    = 0x3A0
BSD_RADAR_LEFT_ID = 0x3B0
VEH_SPEED_ID      = 0x200

def _make_speed_frame(speed_kmh: int) -> CanFrame:
    """Encode vehicle speed into CAN frame 0x200."""
    raw = int(speed_kmh * 10)           # resolution 0.1 km/h
    return CanFrame(id=VEH_SPEED_ID, data=bytes([
        raw & 0xFF, (raw >> 8) & 0xFF, 0, 0, 0, 0, 0, 0
    ]))

def _make_radar_frame(distance_cm: int, relative_speed_kmh: float) -> CanFrame:
    """Encode radar target at given distance (cm) and relative speed."""
    dist_raw  = distance_cm & 0xFFFF
    speed_raw = int(relative_speed_kmh * 10 + 0x8000) & 0xFFFF
    return CanFrame(id=BSD_RADAR_LEFT_ID, data=bytes([
        0x01,                            # target valid
        dist_raw & 0xFF,
        (dist_raw >> 8) & 0xFF,
        speed_raw & 0xFF,
        (speed_raw >> 8) & 0xFF,
        0, 0, 0,
    ]))

def _wait_for_warning(can: CanAdapter, timeout_ms: int = 300) -> bool:
    """Poll BSD warning frame until bit 0 of byte 0 is set, or timeout."""
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        frame = can.receive(timeout_ms=20)
        if frame and frame.id == BSD_WARNING_ID and (frame.data[0] & 0x01):
            return True
    return False


# ─── Test cases ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def hw_can():
    can = CanAdapter(device_uri="vcan0", bitrate=BITRATE_500K)
    can.open()
    yield can
    can.close()


@pytest.fixture(scope="module")
def hw_uds(hw_can):
    cfg = IsoTpConfig(tx_id=0x7DF, rx_id=0x7E8, timeout_ms=2000)
    adapter = UdsAdapter(hw_can, cfg)
    adapter.open()
    yield adapter
    adapter.close()


class BsdLeftWarning280cm80kmh(TestCase):
    """BSD shall activate left warning within 300 ms when a target
    appears at ≤ 280 cm at vehicle speed ≥ 60 km/h."""

    test_id     = "TC-BSD-SYS-001"
    test_name   = "BSD Left Warning: target at 280 cm, ego 80 km/h"
    feature     = "BSD"
    requirement = "REQ-BSD-001"
    priority    = "P1"
    tags        = ["system", "bsd", "smoke"]

    def __init__(self, can: CanAdapter, uds: UdsAdapter) -> None:
        super().__init__()
        self.can = can
        self.uds = uds

    def setup(self):
        self.uds.open_session(UdsSession.DEFAULT)
        self.uds.clear_dtcs(group=0xFFFFFF)
        # Set ego speed 80 km/h
        self.can.transmit(_make_speed_frame(80))
        time.sleep(0.3)

    def test_body(self):
        with self.step(1, "Inject left radar target at 280 cm, -5 km/h relative"):
            self.can.transmit(_make_radar_frame(distance_cm=280, relative_speed_kmh=-5.0))

        with self.step(2, "BSD Left Warning activates within 300 ms"):
            activated = _wait_for_warning(self.can, timeout_ms=300)
            self.assert_true(activated, "BSD Left Warning did not activate within 300 ms")

        with self.step(3, "No DTCs raised"):
            dtcs = self.uds.read_dtcs(status_mask=0x08)
            self.assert_dtcs_clear(dtcs)

    def teardown(self):
        # Send clear-target frame (all zeros = no target)
        self.can.transmit(CanFrame(id=BSD_RADAR_LEFT_ID, data=bytes(8)))
        time.sleep(0.1)


class BsdNoWarningBeyond350cm(TestCase):
    """BSD shall NOT activate a warning when target is > 350 cm (beyond zone)."""

    test_id     = "TC-BSD-SYS-002"
    test_name   = "BSD No Warning: target beyond 350 cm"
    feature     = "BSD"
    requirement = "REQ-BSD-003"
    priority    = "P2"
    tags        = ["system", "bsd"]

    def __init__(self, can: CanAdapter) -> None:
        super().__init__()
        self.can = can

    def setup(self):
        self.can.transmit(_make_speed_frame(80))
        time.sleep(0.3)

    def test_body(self):
        with self.step(1, "Inject left radar target at 400 cm (beyond zone)"):
            self.can.transmit(_make_radar_frame(distance_cm=400, relative_speed_kmh=-5.0))

        with self.step(2, "BSD Left Warning must NOT activate within 500 ms"):
            false_positive = _wait_for_warning(self.can, timeout_ms=500)
            self.assert_false(false_positive, "BSD false positive: warning activated at 400 cm")

    def teardown(self):
        self.can.transmit(CanFrame(id=BSD_RADAR_LEFT_ID, data=bytes(8)))


class BsdNoWarningBelowSpeedThreshold(TestCase):
    """BSD is inactive below 30 km/h."""

    test_id     = "TC-BSD-SYS-003"
    test_name   = "BSD Inactive: ego speed 20 km/h (below threshold)"
    feature     = "BSD"
    requirement = "REQ-BSD-005"
    priority    = "P2"
    tags        = ["system", "bsd"]

    def __init__(self, can: CanAdapter) -> None:
        super().__init__()
        self.can = can

    def setup(self):
        self.can.transmit(_make_speed_frame(20))  # below 30 km/h threshold
        time.sleep(0.3)

    def test_body(self):
        with self.step(1, "Inject radar target at 200 cm at 20 km/h"):
            self.can.transmit(_make_radar_frame(distance_cm=200, relative_speed_kmh=-5.0))

        with self.step(2, "BSD must NOT warn below speed threshold"):
            false_positive = _wait_for_warning(self.can, timeout_ms=500)
            self.assert_false(false_positive, "BSD activated below speed threshold")

    def teardown(self):
        self.can.transmit(CanFrame(id=BSD_RADAR_LEFT_ID, data=bytes(8)))


# ─── pytest-based runner ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def bsd_suite_result(hw_can, hw_uds):
    runner = TestRunner(RunConfig(verbose=True))
    result = runner.run_suite("BSD System Tests", [
        lambda: BsdLeftWarning280cm80kmh(hw_can, hw_uds),
        lambda: BsdNoWarningBeyond350cm(hw_can),
        lambda: BsdNoWarningBelowSpeedThreshold(hw_can),
    ])
    return result


def test_bsd_suite_all_pass(bsd_suite_result):
    assert bsd_suite_result.all_passed, (
        f"BSD suite had failures:\n"
        + "\n".join(r.summary() for r in bsd_suite_result.results if r.failed)
    )
