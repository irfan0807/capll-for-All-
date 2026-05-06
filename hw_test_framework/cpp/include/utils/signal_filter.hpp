#pragma once
/**
 * signal_filter.hpp
 * Lightweight, header-only signal filtering utilities for sensor data.
 * Used in performance-critical paths — no heap allocation in hot loops.
 */

#include <array>
#include <cmath>
#include <cstddef>
#include <numeric>
#include <stdexcept>
#include <type_traits>

namespace hw_adapter {

// ─── ExponentialMovingAverage ─────────────────────────────────────────────────

/**
 * EMA filter: y[n] = alpha * x[n] + (1 - alpha) * y[n-1]
 * alpha = 1.0 → no smoothing (pass-through)
 * alpha → 0.0 → very heavy smoothing
 */
template <typename T = double>
class ExponentialMovingAverage {
    static_assert(std::is_floating_point_v<T>, "EMA requires a floating-point type");
public:
    explicit ExponentialMovingAverage(T alpha = T(0.1)) : alpha_(alpha) {}

    T update(T sample) noexcept {
        if (!initialised_) { value_ = sample; initialised_ = true; }
        else                { value_ = alpha_ * sample + (T(1) - alpha_) * value_; }
        return value_;
    }

    T value()  const noexcept { return value_; }
    void reset()     noexcept { initialised_ = false; value_ = T(0); }
    void setAlpha(T a) noexcept { alpha_ = a; }

private:
    T    alpha_;
    T    value_       = T(0);
    bool initialised_ = false;
};

// ─── MovingAverageFilter ──────────────────────────────────────────────────────

/**
 * Fixed-window moving average (simple mean over the last N samples).
 * N is a compile-time constant — no heap allocation.
 */
template <typename T = double, size_t N = 8>
class MovingAverageFilter {
    static_assert(N > 0, "Window size must be > 0");
public:
    T update(T sample) noexcept {
        buf_[head_] = sample;
        head_ = (head_ + 1) % N;
        if (count_ < N) ++count_;
        return mean();
    }

    T mean() const noexcept {
        if (count_ == 0) return T(0);
        T sum = T(0);
        for (size_t i = 0; i < count_; ++i)
            sum += buf_[(head_ + N - count_ + i) % N];
        return sum / static_cast<T>(count_);
    }

    void reset() noexcept { head_ = 0; count_ = 0; buf_.fill(T(0)); }
    size_t windowSize() const noexcept { return N; }
    size_t count()      const noexcept { return count_; }

private:
    std::array<T, N> buf_   = {};
    size_t           head_  = 0;
    size_t           count_ = 0;
};

// ─── MedianFilter ─────────────────────────────────────────────────────────────

/**
 * Sliding median filter — effective for spike/glitch rejection.
 * Insertion sort kept O(N) since N is typically small (≤ 16).
 */
template <typename T = double, size_t N = 5>
class MedianFilter {
    static_assert(N % 2 == 1, "Median window size should be odd");
public:
    T update(T sample) noexcept {
        buf_[head_] = sample;
        head_ = (head_ + 1) % N;
        if (count_ < N) ++count_;
        return median();
    }

    T median() const noexcept {
        if (count_ == 0) return T(0);
        std::array<T, N> sorted;
        size_t n = count_;
        for (size_t i = 0; i < n; ++i)
            sorted[i] = buf_[(head_ + N - n + i) % N];
        // insertion sort
        for (size_t i = 1; i < n; ++i) {
            T key = sorted[i];
            int j = static_cast<int>(i) - 1;
            while (j >= 0 && sorted[j] > key) { sorted[j + 1] = sorted[j]; --j; }
            sorted[j + 1] = key;
        }
        return sorted[n / 2];
    }

    void reset() noexcept { head_ = 0; count_ = 0; buf_.fill(T(0)); }

private:
    std::array<T, N> buf_   = {};
    size_t           head_  = 0;
    size_t           count_ = 0;
};

// ─── RateOfChangeGuard ────────────────────────────────────────────────────────

/**
 * Rejects samples where the rate of change exceeds max_delta per call.
 * Returns the previous accepted value when a sample is rejected.
 */
template <typename T = double>
class RateOfChangeGuard {
public:
    explicit RateOfChangeGuard(T max_delta) : max_delta_(max_delta) {}

    T update(T sample) noexcept {
        if (!initialised_) { last_ = sample; initialised_ = true; return sample; }
        T delta = sample - last_;
        if (delta < -max_delta_) delta = -max_delta_;
        if (delta >  max_delta_) delta =  max_delta_;
        last_ += delta;
        return last_;
    }

    bool wasLimited() const noexcept { return limited_; }
    T value()         const noexcept { return last_; }
    void reset()            noexcept { initialised_ = false; limited_ = false; }

private:
    T    max_delta_;
    T    last_        = T(0);
    bool initialised_ = false;
    bool limited_     = false;
};

} // namespace hw_adapter
