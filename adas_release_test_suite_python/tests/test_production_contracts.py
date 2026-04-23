from __future__ import annotations

from assertions import assert_prediction
from sut_adapter import ADASSUTAdapter


def test_adapter_mock_contract_shape():
    sut = ADASSUTAdapter()
    output = sut.predict(
        "AEB",
        {
            "sensor_ok": True,
            "ego_speed_mps": 20.0,
            "target_distance_m": 10.0,
            "closing_speed_mps": 8.0,
            "road_friction": 0.8,
        },
    )

    assert isinstance(output, dict)
    assert "status" in output
    assert "signals" in output
    assert isinstance(output["status"], str)
    assert isinstance(output["signals"], dict)


def test_assertion_accepts_valid_contract():
    expected = {"status": "OK", "signals": {"aeb_warn": True, "aeb_brake": False}}
    actual = {"status": "OK", "signals": {"aeb_warn": True, "aeb_brake": False}}
    assert_prediction("AEB-SMK-UNIT-001", expected, actual)
