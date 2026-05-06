"""
tests/integration/test_uds_session.py

Integration tests for UDS session management.
Requires a virtual CAN interface (vcan0) or a hardware CAN bus.

Run with:
    pytest tests/integration/test_uds_session.py -v --interface vcan0

Skip automatically if vcan0 is not available.
"""

import sys
import os
import subprocess
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../python"))

from hw_test_framework.adapters.can_adapter import CanAdapter, BITRATE_500K
from hw_test_framework.adapters.uds_adapter import (
    IsoTpConfig,
    UdsAdapter,
    UdsSession,
    UdsNrc,
)


def _vcan_available() -> bool:
    """Return True if vcan0 is present and UP."""
    try:
        result = subprocess.run(
            ["ip", "link", "show", "vcan0"],
            capture_output=True, text=True, timeout=2,
        )
        return "UP" in result.stdout
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _vcan_available(),
    reason="vcan0 not available — skipping integration tests",
)


@pytest.fixture(scope="module")
def can():
    a = CanAdapter(device_uri="vcan0", bitrate=BITRATE_500K)
    a.open()
    yield a
    a.close()


@pytest.fixture(scope="module")
def uds(can):
    cfg = IsoTpConfig(tx_id=0x7DF, rx_id=0x7E8, timeout_ms=1000)
    a = UdsAdapter(can, cfg)
    a.open()
    yield a
    a.close()


class TestSessionTransitions:
    def test_default_session_from_boot(self, uds):
        resp = uds.open_session(UdsSession.DEFAULT)
        assert resp.positive, f"Default session failed: NRC={resp.nrc}"

    def test_enter_extended_diagnostic_session(self, uds):
        resp = uds.open_session(UdsSession.EXTENDED)
        assert resp.positive, f"Extended session failed: NRC={resp.nrc}"

    def test_return_to_default_from_extended(self, uds):
        uds.open_session(UdsSession.EXTENDED)
        resp = uds.open_session(UdsSession.DEFAULT)
        assert resp.positive

    def test_programming_session_requires_correct_conditions(self, uds):
        resp = uds.open_session(UdsSession.PROGRAMMING)
        if not resp.positive:
            assert resp.nrc in (
                UdsNrc.ConditionsNotCorrect,
                UdsNrc.RequestSequenceError,
            ), f"Unexpected NRC: {resp.nrc}"


class TestReadDataByIdentifier:
    def test_read_vin(self, uds):
        resp = uds.read_did(0xF190)
        assert resp.positive, f"Read VIN failed: NRC={resp.nrc}"
        assert len(resp.payload) >= 17, "VIN should be 17 bytes"

    def test_read_ecuid(self, uds):
        resp = uds.read_did(0xF18C)
        assert resp.positive

    def test_read_nonexistent_did_nrc(self, uds):
        resp = uds.read_did(0x0001)
        if not resp.positive:
            assert resp.nrc in (
                UdsNrc.RequestOutOfRange,
                UdsNrc.ConditionsNotCorrect,
            )


class TestDtcManagement:
    def test_read_dtcs_no_exception(self, uds):
        dtcs = uds.read_dtcs(status_mask=0x0F)
        assert isinstance(dtcs, list)

    def test_clear_and_reread(self, uds):
        uds.clear_dtcs(group=0xFFFFFF)
        dtcs = uds.read_dtcs(status_mask=0x08)  # confirmedDTC mask
        confirmed = [d for d in dtcs if d.confirmed]
        assert len(confirmed) == 0, (
            f"Expected no confirmed DTCs after clear, got: "
            f"{[d.hex() for d in confirmed]}"
        )


class TestEcuReset:
    def test_soft_reset(self, uds):
        resp = uds.ecu_reset(reset_type=0x03)  # soft reset
        assert resp.positive or resp.nrc == UdsNrc.ConditionsNotCorrect
