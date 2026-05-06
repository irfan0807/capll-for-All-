"""
hw_test_framework/framework/test_case.py

Base class for all hardware/software validation test cases.
Provides structured lifecycle, step tracking, assertion helpers,
and automatic result capturing for the reporting layer.
"""

from __future__ import annotations

import functools
import inspect
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


# ─── Result types ─────────────────────────────────────────────────────────────

class TestStatus(Enum):
    NOT_RUN  = auto()
    PASS     = auto()
    FAIL     = auto()
    ERROR    = auto()
    SKIP     = auto()
    BLOCKED  = auto()


@dataclass
class StepResult:
    step_number: int
    description: str
    status: TestStatus
    expected: Any = None
    actual: Any = None
    message: str = ""
    elapsed_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class TestResult:
    test_id: str
    test_name: str
    status: TestStatus = TestStatus.NOT_RUN
    steps: List[StepResult] = field(default_factory=list)
    duration_ms: float = 0.0
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    error_message: str = ""
    tb: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == TestStatus.PASS

    @property
    def failed(self) -> bool:
        return self.status in (TestStatus.FAIL, TestStatus.ERROR)

    def summary(self) -> str:
        icon = {"PASS": "✓", "FAIL": "✗", "ERROR": "!", "SKIP": "~", "NOT_RUN": "?",
                "BLOCKED": "B"}.get(self.status.name, "?")
        return (f"[{icon}] {self.test_id}: {self.test_name} "
                f"({self.status.name}) {self.duration_ms:.0f} ms")


# ─── Assertion helpers ────────────────────────────────────────────────────────

class AssertionError(Exception):  # noqa: A001
    """Test assertion failure."""

    def __init__(self, message: str, expected: Any = None, actual: Any = None) -> None:
        super().__init__(message)
        self.expected = expected
        self.actual   = actual


# ─── TestCase base class ──────────────────────────────────────────────────────

class TestCase:
    """
    Base class for a single hardware/software validation test case.

    Subclass and implement:
      - setup()         → prepare hardware state, open adapters, inject preconditions
      - test_body()     → exercise the feature; use self.step() and self.assert_*()
      - teardown()      → restore default state, close adapters

    Example:
        class BsdWarningTest(TestCase):
            test_id   = "TC-BSD-001"
            test_name = "BSD Left Warning at 280 cm, 80 km/h"

            def setup(self):
                self.can.transmit(CanFrame(0x200, [0xD0, 0x1F, 0, 0, 0, 0, 0, 0]))
                time.sleep(0.5)

            def test_body(self):
                with self.step(1, "Inject left radar target at 280 cm"):
                    self.can.transmit(CanFrame(0x3B0, [0x01, 0x18, 0xFF, 0x7F, ...]))

                with self.step(2, "Verify BSD_Left_WarningActive within 300 ms"):
                    result = wait_signal(self.can, 0x3A0, mask=0x01, timeout_ms=300)
                    self.assert_true(result, "BSD warning not activated in 300 ms")
    """

    # Subclass must override
    test_id:   str = "TC-UNSET"
    test_name: str = "Unnamed Test"

    # Optional metadata
    feature:     str = ""
    requirement: str = ""
    author:      str = ""
    priority:    str = "P3"
    tags:        List[str] = []

    def __init__(self) -> None:
        self._result  = TestResult(test_id=self.test_id, test_name=self.test_name)
        self._step_n  = 0
        self._current_step: Optional[StepResult] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def setup(self) -> None:
        """Prepare preconditions — override in subclass."""

    def test_body(self) -> None:
        """Implement the test — override in subclass. REQUIRED."""
        raise NotImplementedError(f"{type(self).__name__} must implement test_body()")

    def teardown(self) -> None:
        """Restore default state — override in subclass."""

    # ── Execution ─────────────────────────────────────────────────────────────

    def run(self) -> TestResult:
        """Execute the full test lifecycle and return a TestResult."""
        self._result.start_time = time.time()
        self._result.status     = TestStatus.NOT_RUN

        try:
            self.setup()
        except Exception as exc:
            self._result.status        = TestStatus.ERROR
            self._result.error_message = f"setup() failed: {exc}"
            self._result.tb            = traceback.format_exc()
            self._finalise()
            return self._result

        try:
            self.test_body()
            # If we reach here without any FAIL step, it's a PASS
            if self._result.status == TestStatus.NOT_RUN:
                self._result.status = TestStatus.PASS
        except _SkipSignal:
            # status and error_message already set inside skip()
            pass
        except AssertionError as exc:
            self._result.status        = TestStatus.FAIL
            self._result.error_message = str(exc)
        except Exception as exc:
            self._result.status        = TestStatus.ERROR
            self._result.error_message = f"Unexpected error: {exc}"
            self._result.tb            = traceback.format_exc()
        finally:
            try:
                self.teardown()
            except Exception as exc:
                # Teardown failure appended to error — does not override test result
                self._result.error_message += f" | teardown() error: {exc}"

        self._finalise()
        return self._result

    def _finalise(self) -> None:
        self._result.end_time    = time.time()
        self._result.duration_ms = (self._result.end_time - self._result.start_time) * 1000

    # ── Step context manager ──────────────────────────────────────────────────

    class _StepContext:
        def __init__(self, tc: "TestCase", n: int, description: str) -> None:
            self._tc  = tc
            self._n   = n
            self._desc = description
            self._t0  = 0.0

        def __enter__(self) -> "_StepContext":
            self._t0 = time.monotonic()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
            elapsed = (time.monotonic() - self._t0) * 1000
            if exc_type is None:
                status = TestStatus.PASS
                msg    = ""
            elif issubclass(exc_type, AssertionError):
                status = TestStatus.FAIL
                msg    = str(exc_val)
                self._tc._result.status = TestStatus.FAIL
            else:
                # Let other exceptions propagate
                return False

            sr = StepResult(
                step_number=self._n,
                description=self._desc,
                status=status,
                message=msg,
                elapsed_ms=elapsed,
            )
            self._tc._result.steps.append(sr)
            return status == TestStatus.FAIL  # suppress AssertionError to continue

    def step(self, number: int, description: str) -> "_StepContext":
        """Context manager to define a named test step."""
        return self._StepContext(self, number, description)

    # ── Assertion helpers ─────────────────────────────────────────────────────

    def assert_true(self, condition: bool, msg: str = "") -> None:
        if not condition:
            raise AssertionError(msg or "Expected True, got False")

    def assert_false(self, condition: bool, msg: str = "") -> None:
        if condition:
            raise AssertionError(msg or "Expected False, got True")

    def assert_equal(self, actual: Any, expected: Any, msg: str = "") -> None:
        if actual != expected:
            raise AssertionError(
                msg or f"Expected {expected!r}, got {actual!r}",
                expected=expected, actual=actual,
            )

    def assert_not_equal(self, actual: Any, expected: Any, msg: str = "") -> None:
        if actual == expected:
            raise AssertionError(
                msg or f"Expected != {expected!r}, got {actual!r}")

    def assert_in_range(
        self, actual: float, lo: float, hi: float, msg: str = ""
    ) -> None:
        if not (lo <= actual <= hi):
            raise AssertionError(
                msg or f"Expected {actual} in [{lo}, {hi}]",
                expected=f"[{lo}, {hi}]", actual=actual,
            )

    def assert_within(
        self, actual: float, expected: float, tolerance: float, msg: str = ""
    ) -> None:
        if abs(actual - expected) > tolerance:
            raise AssertionError(
                msg or f"|{actual} - {expected}| = {abs(actual - expected):.3f} > {tolerance}",
                expected=expected, actual=actual,
            )

    def assert_latency(
        self, actual_ms: float, max_ms: float, label: str = ""
    ) -> None:
        """Assert that a measured latency is within the requirement."""
        if actual_ms > max_ms:
            raise AssertionError(
                f"Latency violation {label}: {actual_ms:.1f} ms > {max_ms} ms limit",
                expected=f"≤ {max_ms} ms", actual=f"{actual_ms:.1f} ms",
            )

    def assert_dtcs_clear(self, dtcs: list, msg: str = "") -> None:
        confirmed = [d for d in dtcs if d.confirmed]
        if confirmed:
            codes = ", ".join(d.hex() for d in confirmed)
            raise AssertionError(
                msg or f"Unexpected confirmed DTCs: {codes}")

    def skip(self, reason: str = "") -> None:
        """Mark this test as skipped and stop execution."""
        self._result.status        = TestStatus.SKIP
        self._result.error_message = reason
        raise _SkipSignal(reason)


class _SkipSignal(Exception):
    """Internal: signals that a test was skipped."""
