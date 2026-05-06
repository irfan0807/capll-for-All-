"""
tests/unit/test_test_case.py

Unit tests for the TestCase base class and TestRunner.
Validates lifecycle, assertion helpers, step tracking,
skip/error handling, and retry logic.
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../python"))

from hw_test_framework.framework.test_case import (
    AssertionError,
    TestCase,
    TestResult,
    TestStatus,
    _SkipSignal,
)
from hw_test_framework.framework.test_runner import RunConfig, TestRunner


# ─── Minimal test case implementations ───────────────────────────────────────

class PassingTest(TestCase):
    test_id   = "TC-UNIT-001"
    test_name = "Always passing test"
    feature   = "core"
    tags      = ["unit", "smoke"]

    def test_body(self):
        self.assert_true(True, "Should be true")
        self.assert_equal(1 + 1, 2)


class FailingTest(TestCase):
    test_id   = "TC-UNIT-002"
    test_name = "Always failing test"
    feature   = "core"
    tags      = ["unit"]

    def test_body(self):
        self.assert_true(False, "Intentional failure")


class ErrorTest(TestCase):
    test_id   = "TC-UNIT-003"
    test_name = "Raises unexpected exception"
    feature   = "core"

    def test_body(self):
        raise RuntimeError("Unexpected boom")


class SkippedTest(TestCase):
    test_id   = "TC-UNIT-004"
    test_name = "Skipped test"
    feature   = "core"
    tags      = ["unit", "skip-me"]

    def test_body(self):
        self.skip("Not applicable on this platform")
        self.assert_true(False, "Should never reach this")


class SetupFailTest(TestCase):
    test_id   = "TC-UNIT-005"
    test_name = "Setup raises error"

    def setup(self):
        raise EnvironmentError("Hardware not ready")

    def test_body(self):
        pass


class MultiStepTest(TestCase):
    test_id   = "TC-UNIT-006"
    test_name = "Multi-step test"
    feature   = "steps"
    tags      = ["unit"]

    def test_body(self):
        with self.step(1, "Check 1+1=2"):
            self.assert_equal(1 + 1, 2)
        with self.step(2, "Check range [0,100]"):
            self.assert_in_range(50, 0, 100)
        with self.step(3, "Check within tolerance"):
            self.assert_within(9.99, 10.0, 0.05)


# ─── TestCase lifecycle ───────────────────────────────────────────────────────

class TestCaseLifecycle:
    def test_passing_test_returns_pass(self):
        result = PassingTest().run()
        assert result.status == TestStatus.PASS
        assert result.passed
        assert not result.failed

    def test_failing_test_returns_fail(self):
        result = FailingTest().run()
        assert result.status == TestStatus.FAIL
        assert result.failed
        assert "Intentional failure" in result.error_message

    def test_error_test_returns_error(self):
        result = ErrorTest().run()
        assert result.status == TestStatus.ERROR
        assert "Unexpected boom" in result.error_message

    def test_skipped_test_returns_skip(self):
        result = SkippedTest().run()
        assert result.status == TestStatus.SKIP
        assert "Not applicable" in result.error_message

    def test_setup_failure_short_circuits(self):
        result = SetupFailTest().run()
        assert result.status == TestStatus.ERROR
        assert "setup() failed" in result.error_message

    def test_duration_is_positive(self):
        result = PassingTest().run()
        assert result.duration_ms >= 0

    def test_result_summary_contains_id(self):
        result = PassingTest().run()
        assert "TC-UNIT-001" in result.summary()


# ─── Step tracking ────────────────────────────────────────────────────────────

class TestStepTracking:
    def test_all_steps_recorded(self):
        result = MultiStepTest().run()
        assert len(result.steps) == 3

    def test_step_statuses_all_pass(self):
        result = MultiStepTest().run()
        for step in result.steps:
            assert step.status == TestStatus.PASS, f"Step {step.step_number} not PASS"

    def test_step_descriptions_present(self):
        result = MultiStepTest().run()
        descs = [s.description for s in result.steps]
        assert "Check 1+1=2" in descs


# ─── Assertion helpers ────────────────────────────────────────────────────────

class TestAssertions:
    def _tc(self) -> TestCase:
        tc = TestCase.__new__(TestCase)
        tc.__init__()
        return tc

    def test_assert_true_passes(self):
        tc = self._tc()
        tc.assert_true(True)

    def test_assert_true_raises_on_false(self):
        tc = self._tc()
        with pytest.raises(AssertionError):
            tc.assert_true(False, "bad")

    def test_assert_equal_passes(self):
        tc = self._tc()
        tc.assert_equal(42, 42)

    def test_assert_equal_raises_on_mismatch(self):
        tc = self._tc()
        with pytest.raises(AssertionError) as exc_info:
            tc.assert_equal(1, 2)
        assert "Expected 2" in str(exc_info.value)

    def test_assert_in_range_passes(self):
        tc = self._tc()
        tc.assert_in_range(50.0, 0.0, 100.0)

    def test_assert_in_range_fails_below(self):
        tc = self._tc()
        with pytest.raises(AssertionError):
            tc.assert_in_range(-1.0, 0.0, 100.0)

    def test_assert_within_passes(self):
        tc = self._tc()
        tc.assert_within(10.01, 10.0, 0.05)

    def test_assert_within_fails_outside(self):
        tc = self._tc()
        with pytest.raises(AssertionError):
            tc.assert_within(10.1, 10.0, 0.05)

    def test_assert_latency_passes(self):
        tc = self._tc()
        tc.assert_latency(150.0, 200.0, "trigger to warning")

    def test_assert_latency_fails_over_limit(self):
        tc = self._tc()
        with pytest.raises(AssertionError) as exc_info:
            tc.assert_latency(250.0, 200.0, "trigger to warning")
        assert "250" in str(exc_info.value)


# ─── TestRunner ───────────────────────────────────────────────────────────────

class TestRunnerBehaviour:
    def test_run_all_passes(self):
        runner = TestRunner(RunConfig(verbose=False))
        result = runner.run_suite("unit", [PassingTest])
        assert result.all_passed
        assert result.passed == 1
        assert result.total  == 1

    def test_run_failure_captured(self):
        runner = TestRunner(RunConfig(verbose=False))
        result = runner.run_suite("unit", [FailingTest])
        assert not result.all_passed
        assert result.failed == 1

    def test_run_multiple_tests(self):
        runner = TestRunner(RunConfig(verbose=False))
        result = runner.run_suite("unit", [PassingTest, FailingTest, SkippedTest])
        assert result.total   == 3
        assert result.passed  == 1
        assert result.failed  == 1
        assert result.skipped == 1

    def test_hook_is_called_per_result(self):
        hook_calls = []
        runner = TestRunner(RunConfig(verbose=False))
        runner.add_hook(lambda r: hook_calls.append(r.test_id))
        runner.run_suite("unit", [PassingTest, FailingTest])
        assert "TC-UNIT-001" in hook_calls
        assert "TC-UNIT-002" in hook_calls

    def test_tag_filter_include(self):
        cfg    = RunConfig(verbose=False, include_tags=["smoke"])
        runner = TestRunner(cfg)
        result = runner.run_suite("unit", [PassingTest, FailingTest])
        # Only PassingTest has "smoke" tag
        assert result.total == 1
        assert result.passed == 1

    def test_tag_filter_exclude(self):
        cfg    = RunConfig(verbose=False, exclude_tags=["skip-me"])
        runner = TestRunner(cfg)
        result = runner.run_suite("unit", [PassingTest, SkippedTest])
        # SkippedTest excluded
        assert result.total == 1

    def test_id_filter(self):
        cfg    = RunConfig(verbose=False, include_ids=["TC-UNIT-001"])
        runner = TestRunner(cfg)
        result = runner.run_suite("unit", [PassingTest, FailingTest])
        assert result.total == 1
        assert result.passed == 1

    def test_stop_on_first_fail(self):
        cfg    = RunConfig(verbose=False, stop_on_first_fail=True)
        runner = TestRunner(cfg)
        result = runner.run_suite("unit", [FailingTest, PassingTest, PassingTest])
        # Should stop after first failure
        assert result.total < 3

    def test_parallel_execution(self):
        cfg    = RunConfig(verbose=False, parallel=True, max_workers=2)
        runner = TestRunner(cfg)
        result = runner.run_suite("unit", [PassingTest, PassingTest, PassingTest])
        assert result.total  == 3
        assert result.passed == 3

    def test_retry_on_fail(self):
        attempt_counter = []

        class FlakyTest(TestCase):
            test_id   = "TC-UNIT-FLAKY"
            test_name = "Flaky test"
            def test_body(self):
                attempt_counter.append(1)
                if len(attempt_counter) < 3:
                    self.assert_true(False, "not ready yet")

        cfg    = RunConfig(verbose=False, retry_on_fail=True, max_retries=2)
        runner = TestRunner(cfg)
        result = runner.run_suite("unit", [FlakyTest])
        assert result.passed == 1
        assert len(attempt_counter) == 3
