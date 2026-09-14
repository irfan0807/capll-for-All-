"""
Assertion helpers.

Thin wrappers around plain `assert` that (a) log the PASS/FAIL verdict so it
shows up in the run log / HTML report regardless of pytest's own output, and
(b) produce failure messages with the actual measured data inline, which is
what makes a failing ADAS test triageable at 2am without re-running it.
"""
from __future__ import annotations

from typing import Optional

from src.utils.logger import get_logger
from src.validation.state_machine import StateMachineValidator
from src.validation.timing_validator import TimingResult

log = get_logger("assertions")


def assert_signal_reached(sample, expected_value, signal_label: str) -> None:
    if sample is None:
        log.error("FAIL: %s never reached expected value %r (timed out)", signal_label, expected_value)
        raise AssertionError(f"{signal_label} did not reach {expected_value!r} before timeout")
    log.info("PASS: %s reached %r at t=%.3f (monotonic)", signal_label, sample.value, sample.monotonic)


def assert_timing(result: TimingResult) -> None:
    if not result.passed:
        log.error("FAIL: %s", result)
        raise AssertionError(str(result))
    log.info("PASS: %s", result)


def assert_state_sequence_valid(validator: StateMachineValidator) -> None:
    violations = validator.violations()
    if violations:
        detail = "; ".join(str(v) for v in violations)
        log.error("FAIL: illegal AEB state transition(s): %s", detail)
        raise AssertionError(f"Illegal AEB state transition(s): {detail}")
    log.info("PASS: state sequence valid: %s", " -> ".join(validator.sequence_names()))


def assert_no_fault(fault_code: int, context: str = "") -> None:
    if fault_code != 0:
        log.error("FAIL: unexpected fault code %d %s", fault_code, context)
        raise AssertionError(f"Unexpected fault code {fault_code} {context}".strip())
    log.info("PASS: no fault present %s", context)


def assert_fault_code(actual: int, expected: int, context: str = "") -> None:
    if actual != expected:
        log.error("FAIL: expected fault code %d, got %d %s", expected, actual, context)
        raise AssertionError(f"Expected fault code {expected}, got {actual} {context}".strip())
    log.info("PASS: fault code matches expected %d %s", expected, context)
