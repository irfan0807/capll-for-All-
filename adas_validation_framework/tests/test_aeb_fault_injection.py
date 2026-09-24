"""
Fault injection tests.

Covers the failure-mode side of the ADAS V&V matrix: stale/missing sensor
input, plausibility faults, a fully unresponsive ECU node, fault recovery,
and end-to-end legality of the observed state sequence (via
StateMachineValidator) rather than just the final state.
"""
from __future__ import annotations

import time

import pytest

from src.simulation.ecu_sim import AebState, FaultCode
from src.validation.assertions import assert_fault_code, assert_signal_reached, assert_state_sequence_valid
from src.validation.state_machine import StateMachineValidator

pytestmark = pytest.mark.fault_injection


def test_sensor_dropout_triggers_timeout_fault(aeb_api):
    """No sensor frames at all for longer than the ECU's stale-input
    timeout must be detected as a SENSOR_TIMEOUT fault -- this is the classic
    'silent sensor failure' case that's easy to miss in requirements."""
    aeb_api.inject_closing_object(ttc_ms=2000, distance_cm=3000)
    assert_signal_reached(
        aeb_api.wait_for_state(AebState.WARNING, timeout_s=1.0), int(AebState.WARNING), "AEB_State",
    )

    aeb_api.simulate_sensor_dropout(duration_s=0.65)  # > stale_timeout_s (0.50s)

    sample = aeb_api.wait_for_state(AebState.FAULT, timeout_s=1.2)
    assert_signal_reached(sample, int(AebState.FAULT), "AEB_State")
    assert_fault_code(aeb_api.current_fault_code(), int(FaultCode.SENSOR_TIMEOUT), context="after sensor dropout")


def test_plausibility_fault_code_is_reported_correctly(aeb_api):
    aeb_api.inject_fault()
    sample = aeb_api.wait_for_state(AebState.FAULT, timeout_s=1.0)
    assert_signal_reached(sample, int(AebState.FAULT), "AEB_State")
    assert_fault_code(aeb_api.current_fault_code(), int(FaultCode.PLAUSIBILITY_FAULT))


def test_ecu_recovers_from_fault_on_valid_input(aeb_api):
    """After a plausibility fault clears (a subsequent frame arrives without
    the fault bit set and with valid data), the ECU must resume normal
    decisioning rather than latching FAULT forever."""
    aeb_api.inject_fault()
    assert_signal_reached(
        aeb_api.wait_for_state(AebState.FAULT, timeout_s=1.0), int(AebState.FAULT), "AEB_State",
    )

    send_ts = aeb_api.inject_closing_object(ttc_ms=2000, distance_cm=3000)
    sample = aeb_api.wait_for_state(AebState.WARNING, timeout_s=1.0)
    assert_signal_reached(sample, int(AebState.WARNING), "AEB_State (post-fault recovery)")
    assert_fault_code(aeb_api.current_fault_code(), int(FaultCode.NO_FAULT), context="after recovery")


def test_ecu_offline_is_detected_via_heartbeat_timeout(aeb_api, ecu_sim):
    """Simulate a fully unresponsive ECU node (not just a stale signal --
    zero frames at all) and confirm the framework's own heartbeat-liveness
    check flags it, rather than the test just hanging."""
    baseline_rx = aeb_api.status_rx_count()
    assert aeb_api.status_heartbeat_alive(baseline_rx, timeout_s=0.5), "ECU heartbeat should be alive before fault injection"

    ecu_sim.simulate_ecu_offline(True)
    time.sleep(0.1)  # let any in-flight frame land
    rx_before_wait = aeb_api.status_rx_count()

    alive = aeb_api.status_heartbeat_alive(rx_before_wait, timeout_s=0.5)
    assert not alive, "Framework failed to detect an unresponsive ECU node (heartbeat should have timed out)"

    ecu_sim.simulate_ecu_offline(False)
    assert aeb_api.status_heartbeat_alive(aeb_api.status_rx_count(), timeout_s=0.5), "ECU should resume heartbeat after recovery"


def test_full_scenario_state_sequence_is_legal(aeb_api):
    """Drive the ECU through escalation, a fault, and recovery, sampling the
    state at each step, then validate the whole observed sequence against
    the state-machine's legal-transition rules (not just individual states)."""
    validator = StateMachineValidator()
    validator.record(aeb_api.current_state() or AebState.IDLE)

    aeb_api.inject_closing_object(ttc_ms=2000, distance_cm=3000)
    aeb_api.wait_for_state(AebState.WARNING, timeout_s=1.0)
    validator.record(aeb_api.current_state())

    aeb_api.inject_closing_object(ttc_ms=1000, distance_cm=1500)
    aeb_api.wait_for_state(AebState.PARTIAL_BRAKE, timeout_s=1.0)
    validator.record(aeb_api.current_state())

    aeb_api.inject_fault()
    aeb_api.wait_for_state(AebState.FAULT, timeout_s=1.0)
    validator.record(aeb_api.current_state())

    aeb_api.inject_invalid_object()
    aeb_api.wait_for_state(AebState.IDLE, timeout_s=1.0)
    validator.record(aeb_api.current_state())

    assert_state_sequence_valid(validator)
