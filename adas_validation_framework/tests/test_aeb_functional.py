"""
Functional (positive) AEB tests.

Each test: inject a sensor stimulus over CAN -> ECU processes it and
transmits AEB_Status back -> framework's background listener decodes it
into the signal store -> test blocks on the expected state -> timing and
sequence are validated.
"""
from __future__ import annotations

import pytest

from src.simulation.ecu_sim import AebState
from src.validation.assertions import assert_no_fault, assert_signal_reached, assert_timing

pytestmark = pytest.mark.functional


class TestAebClosingObjectEscalation:
    """End-to-end demonstration: a single closing object scenario walking
    through the full WARNING -> PARTIAL_BRAKE -> FULL_BRAKE cascade."""

    def test_warning_on_approaching_object(self, aeb_api):
        send_ts = aeb_api.inject_closing_object(ttc_ms=2000, distance_cm=4000)
        sample = aeb_api.wait_for_state(AebState.WARNING, timeout_s=1.0)
        assert_signal_reached(sample, int(AebState.WARNING), "AEB_State")
        assert_timing(aeb_api.measure_response_time("warning_response", send_ts, AebState.WARNING))
        assert_no_fault(aeb_api.current_fault_code())

    def test_partial_brake_on_shorter_ttc(self, aeb_api):
        send_ts = aeb_api.inject_closing_object(ttc_ms=1000, distance_cm=1500)
        sample = aeb_api.wait_for_state(AebState.PARTIAL_BRAKE, timeout_s=1.0)
        assert_signal_reached(sample, int(AebState.PARTIAL_BRAKE), "AEB_State")
        assert_timing(aeb_api.measure_response_time("partial_brake_response", send_ts, AebState.PARTIAL_BRAKE))
        assert aeb_api.current_brake_pressure() == pytest.approx(30.0, abs=0.5)

    def test_full_brake_on_imminent_collision(self, aeb_api):
        send_ts = aeb_api.inject_closing_object(ttc_ms=300, distance_cm=400)
        sample = aeb_api.wait_for_state(AebState.FULL_BRAKE, timeout_s=1.0)
        assert_signal_reached(sample, int(AebState.FULL_BRAKE), "AEB_State")
        assert_timing(aeb_api.measure_response_time("full_brake_response", send_ts, AebState.FULL_BRAKE))
        assert aeb_api.current_brake_pressure() == pytest.approx(80.0, abs=0.5)

    def test_full_cascade_sequence_is_monotonic(self, aeb_api):
        """Drive TTC down in steps and confirm the ECU escalates through
        every intermediate state rather than skipping stages."""
        observed_states = []

        for ttc in (2200, 1200, 500):
            aeb_api.inject_closing_object(ttc_ms=ttc, distance_cm=ttc * 2)
            expected = {
                2200: AebState.WARNING,
                1200: AebState.PARTIAL_BRAKE,
                500: AebState.FULL_BRAKE,
            }[ttc]
            sample = aeb_api.wait_for_state(expected, timeout_s=1.0)
            assert_signal_reached(sample, int(expected), f"AEB_State (TTC={ttc}ms)")
            observed_states.append(aeb_api.current_state())

        assert observed_states == [AebState.WARNING, AebState.PARTIAL_BRAKE, AebState.FULL_BRAKE]


class TestAebRecovery:
    def test_state_returns_to_idle_when_object_clears(self, aeb_api):
        aeb_api.inject_closing_object(ttc_ms=1000, distance_cm=1500)
        assert_signal_reached(
            aeb_api.wait_for_state(AebState.PARTIAL_BRAKE, timeout_s=1.0),
            int(AebState.PARTIAL_BRAKE), "AEB_State",
        )

        aeb_api.inject_invalid_object()  # object no longer detected
        sample = aeb_api.wait_for_state(AebState.IDLE, timeout_s=1.0)
        assert_signal_reached(sample, int(AebState.IDLE), "AEB_State")
        assert aeb_api.current_brake_pressure() == pytest.approx(0.0, abs=0.5)
