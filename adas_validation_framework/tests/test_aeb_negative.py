"""
Negative AEB tests.

These assert absence of a reaction, which is a fundamentally different shape
of check than the positive tests: there's no event to synchronize on, so
each test waits out a full ECU cycle window and then asserts the *lack* of
escalation, rather than asserting a signal was reached.
"""
from __future__ import annotations

import pytest

from src.simulation.ecu_sim import AebState
from src.simulation.sensor_sim import SensorFrame
from src.validation.assertions import assert_signal_reached

pytestmark = pytest.mark.negative

NON_IDLE_STATES = {AebState.WARNING, AebState.PARTIAL_BRAKE, AebState.FULL_BRAKE}


def test_invalid_object_does_not_trigger_braking(aeb_api):
    """ObjectValid=0 must be ignored regardless of how alarming the TTC/
    distance payload looks -- guards against phantom braking on a sensor
    blind/no-detection frame."""
    aeb_api.sensor.send(SensorFrame(ttc_ms=100, distance_cm=100, rel_speed_kph=-60.0, valid=False))
    aeb_api.wait_for_any_state(NON_IDLE_STATES, timeout_s=0.3)
    assert aeb_api.current_state() == AebState.IDLE, (
        f"AEB reacted to an invalid (unconfirmed) object: state={aeb_api.current_state()}"
    )


@pytest.mark.parametrize(
    "ttc_ms, distance_cm",
    [
        pytest.param(5000, 8000, id="far_object_no_reaction"),
        pytest.param(65535, 65535, id="max_ttc_sensor_value_no_reaction"),
    ],
)
def test_distant_object_does_not_trigger_braking(aeb_api, ttc_ms, distance_cm):
    aeb_api.inject_closing_object(ttc_ms=ttc_ms, distance_cm=distance_cm)
    aeb_api.wait_for_any_state(NON_IDLE_STATES, timeout_s=0.3)
    assert aeb_api.current_state() == AebState.IDLE


def test_stationary_host_suppresses_aeb(aeb_api):
    aeb_api.set_host_speed(0.0)
    aeb_api.inject_closing_object(ttc_ms=200, distance_cm=300)
    aeb_api.wait_for_any_state(NON_IDLE_STATES, timeout_s=0.3)
    assert aeb_api.current_state() == AebState.IDLE, "AEB must not engage while host vehicle is stationary"


def test_fault_injected_frame_does_not_command_full_brake(aeb_api):
    """A frame with the fault-inject bit set must route to FAULT, not to a
    braking state -- a plausibility-faulted sensor must never be trusted
    enough to command actuation."""
    send_ts = aeb_api.inject_fault()
    sample = aeb_api.wait_for_state(AebState.FAULT, timeout_s=1.0)
    assert_signal_reached(sample, int(AebState.FAULT), "AEB_State")
    assert aeb_api.current_state() != AebState.FULL_BRAKE
    assert aeb_api.current_state() != AebState.PARTIAL_BRAKE
    assert aeb_api.current_brake_pressure() == pytest.approx(0.0, abs=0.5)
