"""
hw_test_framework/framework/test_runner.py

Executes test suites, manages parallel/sequential scheduling,
streams results to the observability layer, and aggregates outcomes.
"""

from __future__ import annotations

import concurrent.futures
import logging
import sys
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable, Dict, List, Optional, Sequence, Type

from .test_case import TestCase, TestResult, TestStatus, _SkipSignal

logger = logging.getLogger(__name__)


# ─── Run configuration ────────────────────────────────────────────────────────

@dataclass
class RunConfig:
    """Controls test runner behaviour."""

    # Execution
    parallel:          bool = False       # Run tests concurrently
    max_workers:       int  = 4           # Max threads when parallel=True
    stop_on_first_fail: bool = False      # Abort suite on first FAIL

    # Retry
    retry_on_fail:     bool = False
    max_retries:       int  = 1

    # Filtering
    include_tags:  List[str] = field(default_factory=list)
    exclude_tags:  List[str] = field(default_factory=list)
    include_ids:   List[str] = field(default_factory=list)

    # Timeouts
    test_timeout_s: float = 120.0   # Per-test wall-clock timeout

    # Output
    verbose:       bool = True
    log_to_file:   str  = ""        # Empty = stdout only


# ─── Suite result ─────────────────────────────────────────────────────────────

@dataclass
class SuiteResult:
    suite_name: str
    results: List[TestResult] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0

    @property
    def total(self)   -> int: return len(self.results)
    @property
    def passed(self)  -> int: return sum(1 for r in self.results if r.status == TestStatus.PASS)
    @property
    def failed(self)  -> int: return sum(1 for r in self.results if r.status == TestStatus.FAIL)
    @property
    def errors(self)  -> int: return sum(1 for r in self.results if r.status == TestStatus.ERROR)
    @property
    def skipped(self) -> int: return sum(1 for r in self.results if r.status == TestStatus.SKIP)
    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.errors == 0

    def print_summary(self, stream=sys.stdout) -> None:
        duration_s = self.duration_ms / 1000
        stream.write(f"\n{'─' * 60}\n")
        stream.write(f"Suite: {self.suite_name}\n")
        stream.write(f"{'─' * 60}\n")
        stream.write(f"  Total:   {self.total}\n")
        stream.write(f"  Passed:  {self.passed}\n")
        stream.write(f"  Failed:  {self.failed}\n")
        stream.write(f"  Errors:  {self.errors}\n")
        stream.write(f"  Skipped: {self.skipped}\n")
        stream.write(f"  Duration: {duration_s:.2f} s\n")
        stream.write(f"  Result:  {'PASS' if self.all_passed else 'FAIL'}\n")
        stream.write(f"{'─' * 60}\n\n")


# ─── Event hooks ──────────────────────────────────────────────────────────────

ResultHook = Callable[[TestResult], None]


# ─── TestRunner ───────────────────────────────────────────────────────────────

class TestRunner:
    """
    Orchestrates test execution.

    Usage:
        runner = TestRunner(config=RunConfig(verbose=True))
        runner.add_hook(my_metrics_collector)
        result = runner.run_suite("BSD Tests", [BsdWarningTest, BsdFalsePositiveTest])
        assert result.all_passed
    """

    def __init__(self, config: Optional[RunConfig] = None) -> None:
        self._config = config or RunConfig()
        self._hooks: List[ResultHook] = []
        self._lock  = Lock()

        if self._config.log_to_file:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(message)s",
                handlers=[
                    logging.FileHandler(self._config.log_to_file),
                    logging.StreamHandler(sys.stdout),
                ],
            )

    def add_hook(self, hook: ResultHook) -> None:
        """Register a callback invoked after each test completes."""
        self._hooks.append(hook)

    # ── Main entry points ─────────────────────────────────────────────────────

    def run_suite(
        self,
        suite_name: str,
        test_classes: Sequence[Type[TestCase]],
    ) -> SuiteResult:
        """Run a list of TestCase classes and return aggregated results."""
        suite = SuiteResult(suite_name=suite_name, start_time=time.time())
        filtered = self._filter(test_classes)

        logger.info("Starting suite: %s (%d tests)", suite_name, len(filtered))

        if self._config.parallel:
            suite.results = self._run_parallel(filtered, suite)
        else:
            suite.results = self._run_sequential(filtered, suite)

        suite.end_time = time.time()
        if self._config.verbose:
            suite.print_summary()

        return suite

    def run_test(self, test_class: Type[TestCase]) -> TestResult:
        """Run a single test class and return its result."""
        return self._execute_single(test_class())

    # ── Sequential execution ──────────────────────────────────────────────────

    def _run_sequential(
        self,
        classes: List[Type[TestCase]],
        suite: SuiteResult,
    ) -> List[TestResult]:
        results: List[TestResult] = []
        for tc_class in classes:
            result = self._execute_with_retry(tc_class)
            results.append(result)
            self._notify_hooks(result)
            if self._config.verbose:
                self._print_result(result)
            if self._config.stop_on_first_fail and result.failed:
                logger.warning("Stopping suite — first failure: %s", result.test_id)
                break
        return results

    # ── Parallel execution ────────────────────────────────────────────────────

    def _run_parallel(
        self,
        classes: List[Type[TestCase]],
        suite: SuiteResult,
    ) -> List[TestResult]:
        results_map: Dict[str, TestResult] = {}
        abort_flag  = [False]

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self._config.max_workers,
            thread_name_prefix="hw-test",
        ) as pool:
            futures = {
                pool.submit(self._execute_with_retry, tc): tc
                for tc in classes
            }
            for future in concurrent.futures.as_completed(
                futures, timeout=self._config.test_timeout_s * len(classes)
            ):
                try:
                    result = future.result(timeout=self._config.test_timeout_s)
                except concurrent.futures.TimeoutError:
                    tc = futures[future]
                    result = TestResult(
                        test_id=tc.test_id,
                        test_name=tc.test_name,
                        status=TestStatus.ERROR,
                        error_message="Test timed out",
                    )
                except Exception as exc:
                    tc = futures[future]
                    result = TestResult(
                        test_id=tc.test_id,
                        test_name=tc.test_name,
                        status=TestStatus.ERROR,
                        error_message=str(exc),
                    )

                with self._lock:
                    results_map[result.test_id] = result
                    self._notify_hooks(result)
                    if self._config.verbose:
                        self._print_result(result)
                    if self._config.stop_on_first_fail and result.failed:
                        abort_flag[0] = True
                        for f in futures:
                            f.cancel()

        # Preserve original order
        return [results_map[tc.test_id] for tc in classes if tc.test_id in results_map]

    # ── Single test execution ─────────────────────────────────────────────────

    def _execute_with_retry(self, tc_class: Type[TestCase]) -> TestResult:
        retries = self._config.max_retries if self._config.retry_on_fail else 0
        result  = None
        for attempt in range(retries + 1):
            if attempt > 0:
                logger.info("Retrying %s (attempt %d/%d)", tc_class.test_id, attempt + 1, retries + 1)
            result = self._execute_single(tc_class())
            if not result.failed:
                break
            if attempt < retries:
                result.metadata["retry_attempt"] = attempt + 1
        return result

    def _execute_single(self, tc: TestCase) -> TestResult:
        logger.info("Running: %s — %s", tc.test_id, tc.test_name)
        try:
            result = tc.run()
        except _SkipSignal:
            result = tc._result
        except Exception as exc:
            result = TestResult(
                test_id=tc.test_id,
                test_name=tc.test_name,
                status=TestStatus.ERROR,
                error_message=str(exc),
            )
        result.metadata.update({
            "feature":     tc.feature,
            "requirement": tc.requirement,
            "author":      tc.author,
            "priority":    tc.priority,
            "tags":        list(tc.tags),
        })
        return result

    # ── Filtering ─────────────────────────────────────────────────────────────

    def _filter(self, classes: Sequence[Type[TestCase]]) -> List[Type[TestCase]]:
        cfg = self._config
        result = []
        for tc in classes:
            if cfg.include_ids and tc.test_id not in cfg.include_ids:
                continue
            tc_tags = set(tc.tags)
            if cfg.include_tags and not tc_tags.intersection(cfg.include_tags):
                continue
            if cfg.exclude_tags and tc_tags.intersection(cfg.exclude_tags):
                continue
            result.append(tc)
        return result

    # ── Output ────────────────────────────────────────────────────────────────

    def _notify_hooks(self, result: TestResult) -> None:
        for hook in self._hooks:
            try:
                hook(result)
            except Exception as exc:
                logger.warning("Hook error: %s", exc)

    @staticmethod
    def _print_result(result: TestResult) -> None:
        status_icons = {
            TestStatus.PASS:    "\033[92m✓\033[0m",
            TestStatus.FAIL:    "\033[91m✗\033[0m",
            TestStatus.ERROR:   "\033[91m!\033[0m",
            TestStatus.SKIP:    "\033[93m~\033[0m",
            TestStatus.BLOCKED: "\033[90mB\033[0m",
            TestStatus.NOT_RUN: "\033[90m?\033[0m",
        }
        icon = status_icons.get(result.status, "?")
        print(f"  {icon} [{result.test_id}] {result.test_name} ({result.duration_ms:.0f} ms)")
        if result.error_message:
            print(f"      → {result.error_message}")
