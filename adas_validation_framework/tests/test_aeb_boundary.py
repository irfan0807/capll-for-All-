"""
Parameterized positive / negative / boundary AEB tests.

Boundary values are picked exactly on and either side of the ECU decision
thresholds (see EcuThresholds in src/simulation/ecu_sim.py) -- this is the
classic boundary-value-analysis technique applied to a CAN-based decision
cascade instead of a plain function call.
"""
from __future__ import annotations

import pytest

from src.simulation.ecu_sim import AebState
from src.validation.assertions import assert_signal_reached

pytestmark = pytest.mark.boundary


# (ttc_ms, expected_state, test_id) -- thresholds are 2500 / 1500 / 700
BOUNDARY_CASES = [
    # -- above WARNING threshold: no reaction --
    pytest.param(2501, AebState.IDLE, id="ttc_2501ms_just_above_warning_threshold_no_reaction"),
    pytest.param(5000, AebState.IDLE, id="ttc_5000ms_far_object_no_reaction"),
    # -- WARNING boundary --
    pytest.param(2500, AebState.WARNING, id="ttc_2500ms_exact_warning_threshold"),
    pytest.param(2000, AebState.WARNING, id="ttc_2000ms_mid_warning_band"),
    pytest.param(1501, AebState.WARNING, id="ttc_1501ms_just_above_partial_brake_threshold"),
    # -- PARTIAL_BRAKE boundary --
    pytest.param(1500, AebState.PARTIAL_BRAKE, id="ttc_1500ms_exact_partial_brake_threshold"),
    pytest.param(1000, AebState.PARTIAL_BRAKE, id="ttc_1000ms_mid_partial_brake_band"),
    pytest.param(701, AebState.PARTIAL_BRAKE, id="ttc_701ms_just_above_full_brake_threshold"),
    # -- FULL_BRAKE boundary --
    pytest.param(700, AebState.FULL_BRAKE, id="ttc_700ms_exact_full_brake_threshold"),
    pytest.param(300, AebState.FULL_BRAKE, id="ttc_300ms_deep_full_brake_band"),
    pytest.param(1, AebState.FULL_BRAKE, id="ttc_1ms_near_zero_imminent_collision"),
]


@pytest.mark.parametrize("ttc_ms, expected_state", BOUNDARY_CASES)
def test_ttc_threshold_boundaries(aeb_api, ttc_ms, expected_state):
    aeb_api.inject_closing_object(ttc_ms=ttc_ms, distance_cm=max(50, ttc_ms))
    timeout = 1.0 if expected_state != AebState.IDLE else 0.3
    if expected_state == AebState.IDLE:
        # There's no positive event to wait for -- give the ECU a full cycle
        # then assert it did NOT escalate.
        aeb_api.wait_for_any_state({AebState.WARNING, AebState.PARTIAL_BRAKE, AebState.FULL_BRAKE}, timeout_s=timeout)
        assert aeb_api.current_state() == AebState.IDLE, (
            f"Expected IDLE for TTC={ttc_ms}ms but ECU escalated to {aeb_api.current_state()}"
        )
    else:
        sample = aeb_api.wait_for_state(expected_state, timeout_s=timeout)
        assert_signal_reached(sample, int(expected_state), f"AEB_State (TTC={ttc_ms}ms)")


# (speed_kph, description) -- operational envelope is 5..160 kph
SPEED_ENVELOPE_CASES = [
    pytest.param(0.0, id="speed_0kph_stationary_suppressed"),
    pytest.param(4.9, id="speed_4p9kph_just_below_min_envelope"),
    pytest.param(161.0, id="speed_161kph_just_above_max_envelope"),
    pytest.param(300.0, id="speed_300kph_implausible_suppressed"),
]


@pytest.mark.parametrize("speed_kph", SPEED_ENVELOPE_CASES)
def test_aeb_suppressed_outside_speed_envelope(aeb_api, speed_kph):
    """A closing object that would normally trigger FULL_BRAKE must be
    ignored outside the ECU's operational speed envelope."""
    aeb_api.set_host_speed(speed_kph)
    aeb_api.inject_closing_object(ttc_ms=300, distance_cm=400)
    aeb_api.wait_for_any_state({AebState.WARNING, AebState.PARTIAL_BRAKE, AebState.FULL_BRAKE}, timeout_s=0.3)
    assert aeb_api.current_state() == AebState.IDLE, (
        f"AEB should be suppressed at {speed_kph}kph but state is {aeb_api.current_state()}"
    )


@pytest.mark.parametrize("speed_kph", [5.0, 80.0, 160.0])
def test_aeb_active_at_speed_envelope_boundaries(aeb_api, speed_kph):
    """Exact envelope boundary values (5.0 / 160.0) must still allow AEB
    to engage."""
    aeb_api.set_host_speed(speed_kph)
    send_ts = aeb_api.inject_closing_object(ttc_ms=300, distance_cm=400)
    sample = aeb_api.wait_for_state(AebState.FULL_BRAKE, timeout_s=1.0)
    assert_signal_reached(sample, int(AebState.FULL_BRAKE), f"AEB_State at boundary speed={speed_kph}kph")
