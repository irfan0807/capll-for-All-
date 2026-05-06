"""
hw_test_framework/observability/metrics.py

Instruments the test framework for observability:
  - Counters, gauges, histograms
  - Exported as Prometheus-compatible text or JSON
  - Automatically hooks into TestRunner results
"""

from __future__ import annotations

import json
import statistics
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..framework.test_case import TestResult, TestStatus


# ─── Metric primitives ────────────────────────────────────────────────────────

@dataclass
class Counter:
    name: str
    labels: Dict[str, str] = field(default_factory=dict)
    _value: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def inc(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value += amount

    @property
    def value(self) -> float:
        return self._value

    def reset(self) -> None:
        with self._lock:
            self._value = 0.0


@dataclass
class Gauge:
    name: str
    labels: Dict[str, str] = field(default_factory=dict)
    _value: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def set(self, value: float) -> None:
        with self._lock:
            self._value = value

    def inc(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value -= amount

    @property
    def value(self) -> float:
        return self._value


@dataclass
class Histogram:
    """Tracks distribution of values (durations, latencies, etc.)."""

    name: str
    buckets: List[float] = field(default_factory=lambda: [10, 50, 100, 250, 500, 1000, 5000])
    _observations: List[float] = field(default_factory=list, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def observe(self, value: float) -> None:
        with self._lock:
            self._observations.append(value)

    @property
    def count(self) -> int:
        return len(self._observations)

    @property
    def mean(self) -> float:
        if not self._observations:
            return 0.0
        return statistics.mean(self._observations)

    @property
    def p50(self) -> float:
        return self._percentile(50)

    @property
    def p95(self) -> float:
        return self._percentile(95)

    @property
    def p99(self) -> float:
        return self._percentile(99)

    @property
    def max(self) -> float:
        return max(self._observations) if self._observations else 0.0

    def _percentile(self, pct: float) -> float:
        if not self._observations:
            return 0.0
        sorted_obs = sorted(self._observations)
        idx = int(len(sorted_obs) * pct / 100)
        return sorted_obs[min(idx, len(sorted_obs) - 1)]

    def bucket_counts(self) -> Dict[str, int]:
        result = {}
        for b in self.buckets:
            result[f"le_{b}"] = sum(1 for v in self._observations if v <= b)
        result["le_inf"] = len(self._observations)
        return result

    def to_dict(self) -> dict:
        return {
            "count":  self.count,
            "mean":   round(self.mean, 2),
            "p50":    round(self.p50, 2),
            "p95":    round(self.p95, 2),
            "p99":    round(self.p99, 2),
            "max":    round(self.max, 2),
            "buckets": self.bucket_counts(),
        }


# ─── TestMetricsCollector ─────────────────────────────────────────────────────

class TestMetricsCollector:
    """
    Collects and aggregates metrics from test execution.
    Register as a hook with TestRunner.

    Usage:
        collector = TestMetricsCollector()
        runner.add_hook(collector.on_result)
        suite_result = runner.run_suite(...)
        print(collector.to_json())
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

        # Counters per status
        self.tests_total    = Counter("tests_total")
        self.tests_passed   = Counter("tests_passed")
        self.tests_failed   = Counter("tests_failed")
        self.tests_errored  = Counter("tests_errored")
        self.tests_skipped  = Counter("tests_skipped")

        # Duration histogram (milliseconds)
        self.test_duration_ms = Histogram(
            "test_duration_ms",
            buckets=[10, 50, 100, 250, 500, 1000, 2000, 5000, 10000, 30000],
        )

        # Per-feature counters
        self._feature_counters: Dict[str, Dict[str, Counter]] = defaultdict(
            lambda: {
                "total":  Counter("total"),
                "passed": Counter("passed"),
                "failed": Counter("failed"),
            }
        )

        # Per-priority counters
        self._priority_counters: Dict[str, Counter] = defaultdict(lambda: Counter("count"))

        # Failure reasons
        self._failure_reasons: List[str] = []

        # Timestamps
        self.start_time = time.time()
        self.end_time: Optional[float] = None

    # ── Hook ──────────────────────────────────────────────────────────────────

    def on_result(self, result: TestResult) -> None:
        """Called by TestRunner after each test completes."""
        with self._lock:
            self.tests_total.inc()
            self.test_duration_ms.observe(result.duration_ms)

            if result.status == TestStatus.PASS:
                self.tests_passed.inc()
            elif result.status == TestStatus.FAIL:
                self.tests_failed.inc()
                if result.error_message:
                    self._failure_reasons.append(
                        f"[{result.test_id}] {result.error_message}"
                    )
            elif result.status == TestStatus.ERROR:
                self.tests_errored.inc()
            elif result.status == TestStatus.SKIP:
                self.tests_skipped.inc()

            feature  = result.metadata.get("feature", "unknown")
            priority = result.metadata.get("priority", "P3")

            fc = self._feature_counters[feature]
            fc["total"].inc()
            if result.status == TestStatus.PASS:
                fc["passed"].inc()
            elif result.status in (TestStatus.FAIL, TestStatus.ERROR):
                fc["failed"].inc()

            self._priority_counters[priority].inc()

    def finalise(self) -> None:
        self.end_time = time.time()

    # ── Export ────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        total    = self.tests_total.value
        duration = (self.end_time or time.time()) - self.start_time

        return {
            "summary": {
                "total":    int(total),
                "passed":   int(self.tests_passed.value),
                "failed":   int(self.tests_failed.value),
                "errored":  int(self.tests_errored.value),
                "skipped":  int(self.tests_skipped.value),
                "pass_rate": round(self.tests_passed.value / total * 100, 1) if total else 0.0,
                "duration_s": round(duration, 2),
            },
            "duration_distribution": self.test_duration_ms.to_dict(),
            "by_feature": {
                feat: {
                    "total":   int(cnts["total"].value),
                    "passed":  int(cnts["passed"].value),
                    "failed":  int(cnts["failed"].value),
                    "pass_rate": (
                        round(cnts["passed"].value / cnts["total"].value * 100, 1)
                        if cnts["total"].value else 0.0
                    ),
                }
                for feat, cnts in self._feature_counters.items()
            },
            "by_priority": {
                p: int(c.value)
                for p, c in sorted(self._priority_counters.items())
            },
            "failure_reasons": self._failure_reasons[:20],  # top 20
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_prometheus(self) -> str:
        """Export as Prometheus exposition format."""
        lines = []
        d = self.to_dict()
        s = d["summary"]
        lines += [
            "# HELP hw_test_total Total number of test cases executed",
            "# TYPE hw_test_total counter",
            f"hw_test_total {s['total']}",
            f"hw_test_passed_total {s['passed']}",
            f"hw_test_failed_total {s['failed']}",
            f"hw_test_errored_total {s['errored']}",
            f"hw_test_skipped_total {s['skipped']}",
            f"hw_test_pass_rate {s['pass_rate']}",
            "",
        ]
        hist = self.test_duration_ms
        lines += [
            "# HELP hw_test_duration_ms Test duration distribution",
            "# TYPE hw_test_duration_ms histogram",
        ]
        for bucket_label, count in hist.bucket_counts().items():
            le = bucket_label.replace("le_", "").replace("inf", "+Inf")
            lines.append(f'hw_test_duration_ms_bucket{{le="{le}"}} {count}')
        lines += [
            f"hw_test_duration_ms_count {hist.count}",
            f"hw_test_duration_ms_sum {sum(hist._observations):.2f}",
            "",
        ]
        return "\n".join(lines)
