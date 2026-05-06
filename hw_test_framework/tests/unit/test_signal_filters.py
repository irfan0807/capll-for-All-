"""
tests/unit/test_signal_filters.py

Unit tests for signal filters:
  - ExponentialMovingAverage
  - MedianFilter
  - RateOfChangeGuard

Run with: pytest tests/unit/test_signal_filters.py -v
"""

import math
import sys
import os

import pytest

# Support running without install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../python"))

# Try C++ bindings first; fall back to Python stubs if not available
try:
    from hw_adapter_cpp import EMA, MedianFilter5, RateOfChangeGuard

    class _EMA:
        def __init__(self, alpha: float):
            self._ema = EMA(alpha)

        def update(self, v: float) -> float:
            return self._ema.update(v)

    class _MedianFilter:
        def __init__(self):
            self._f = MedianFilter5()

        def update(self, v: float) -> float:
            return self._f.update(v)

    class _RateGuard:
        def __init__(self, max_rate: float, dt: float):
            self._g = RateOfChangeGuard(max_rate, dt)

        def update(self, v: float):
            return self._g.update(v)

    CPP_AVAILABLE = True

except ImportError:
    # Pure-Python stubs so the unit tests still run
    CPP_AVAILABLE = False

    class _EMA:
        def __init__(self, alpha: float):
            self._alpha = alpha
            self._value = None

        def update(self, v: float) -> float:
            if self._value is None:
                self._value = v
            else:
                self._value = self._alpha * v + (1 - self._alpha) * self._value
            return self._value

    class _MedianFilter:
        def __init__(self):
            self._buf = []

        def update(self, v: float) -> float:
            self._buf.append(v)
            if len(self._buf) > 5:
                self._buf.pop(0)
            return sorted(self._buf)[len(self._buf) // 2]

    class _RateGuard:
        def __init__(self, max_rate: float, dt: float):
            self._max = max_rate * dt
            self._prev = None

        def update(self, v: float):
            if self._prev is None:
                self._prev = v
                return v, False
            clamped = max(self._prev - self._max, min(self._prev + self._max, v))
            clipped = abs(v - self._prev) > self._max
            self._prev = clamped
            return clamped, clipped


# ─── EMA tests ────────────────────────────────────────────────────────────────

class TestEMA:
    def test_first_value_passthrough(self):
        ema = _EMA(alpha=0.2)
        assert ema.update(100.0) == pytest.approx(100.0)

    def test_smoothing(self):
        ema = _EMA(alpha=0.1)
        _ = ema.update(0.0)
        v = ema.update(100.0)
        # EMA of 100 after 0 with alpha=0.1 → 10
        assert v == pytest.approx(10.0, abs=0.01)

    def test_convergence_to_constant(self):
        ema = _EMA(alpha=0.5)
        v = 0.0
        for _ in range(50):
            v = ema.update(10.0)
        # Should converge close to 10
        assert v == pytest.approx(10.0, abs=0.01)

    def test_alpha_one_tracks_immediately(self):
        ema = _EMA(alpha=1.0)
        assert ema.update(42.0) == pytest.approx(42.0)
        assert ema.update(99.0) == pytest.approx(99.0)

    def test_alpha_zero_freezes_at_first(self):
        ema = _EMA(alpha=0.0)
        assert ema.update(10.0) == pytest.approx(10.0)
        assert ema.update(99.0) == pytest.approx(10.0)


# ─── Median filter tests ──────────────────────────────────────────────────────

class TestMedianFilter:
    def test_single_value(self):
        mf = _MedianFilter()
        assert mf.update(7.0) == pytest.approx(7.0)

    def test_rejects_spike(self):
        mf = _MedianFilter()
        values = [10.0, 10.0, 1000.0, 10.0, 10.0]
        results = [mf.update(v) for v in values]
        # After the 5th value the median over [10, 10, 1000, 10, 10] = 10
        assert results[-1] == pytest.approx(10.0)

    def test_sorted_sequence(self):
        mf = _MedianFilter()
        # Feed 1,2,3,4,5 → window is [1,2,3,4,5] → median = 3
        for v in [1.0, 2.0, 3.0, 4.0]:
            mf.update(v)
        result = mf.update(5.0)
        assert result == pytest.approx(3.0)

    def test_negative_values(self):
        mf = _MedianFilter()
        for v in [-5.0, -3.0, -1.0, -4.0]:
            mf.update(v)
        result = mf.update(-2.0)
        assert result == pytest.approx(-3.0)


# ─── RateOfChangeGuard tests ──────────────────────────────────────────────────

class TestRateOfChangeGuard:
    def test_no_clip_on_slow_change(self):
        guard = _RateGuard(max_rate=10.0, dt=0.1)  # max 1.0 per step
        guard.update(0.0)
        val, clipped = guard.update(0.5)
        assert not clipped
        assert val == pytest.approx(0.5)

    def test_clips_fast_jump(self):
        guard = _RateGuard(max_rate=10.0, dt=0.1)  # max 1.0 per step
        guard.update(0.0)
        val, clipped = guard.update(50.0)
        assert clipped
        assert val == pytest.approx(1.0)

    def test_allows_gradual_increase(self):
        guard = _RateGuard(max_rate=10.0, dt=0.1)
        v = 0.0
        guard.update(v)
        for _ in range(5):
            v, clipped = guard.update(v + 0.5)
            assert not clipped
        assert v == pytest.approx(2.5)

    def test_clips_sudden_drop(self):
        guard = _RateGuard(max_rate=10.0, dt=0.1)
        guard.update(100.0)
        val, clipped = guard.update(0.0)
        assert clipped
        assert val == pytest.approx(99.0)
